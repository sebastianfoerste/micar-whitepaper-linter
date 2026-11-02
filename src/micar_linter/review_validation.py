"""Summarize human validation of the MiCAR white-paper study detector."""

from __future__ import annotations

import argparse
import csv
import dataclasses
import hashlib
import json
import math
import re
import sys
from collections.abc import Collection, Iterable, Mapping, Sequence
from datetime import date
from fractions import Fraction
from pathlib import Path
from typing import Any

from micar_linter.review_metrics import (
    BOOTSTRAP_QUANTILE_METHOD,
    CONFIDENCE_LEVEL,
    PROPORTIONS,
    WILSON_Z,
    Counts,
    agreement,
    clopper_pearson_interval,
    cluster_bootstrap,
    interval_dict,
    rounded,
    undefined_reason,
    wilson_interval,
)

SCHEMA_VERSION = "micar-study-human-validation.v2"
ALLOWED_LABELS = {
    "pending",
    "present",
    "missing",
    "uncertain",
    "extraction_failure",
    "not_applicable",
}
EVALUABLE_LABELS = {"present", "missing"}
NOTE_REQUIRED_LABELS = {"uncertain", "extraction_failure", "not_applicable"}
ALLOWED_DETECTOR_STATUSES = {"flagged", "not_flagged"}
# The calendar form the reviewer checklist asks for. ASCII digits only, so that a date typed with
# other digit forms, a time or an ordinal or week date is refused rather than read loosely.
_REVIEW_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
METRIC_NOTE = (
    "Precision is tp / (tp + fp), recall is tp / (tp + fn) and F1 is 2tp / (2tp + fp + fn), counted over "
    "human labels 'present' and 'missing' only. Uncertain, extraction-failure, not-applicable, and pending "
    "rows are excluded. A metric with a zero denominator is null. review-protocol.md does not define F1: "
    "this module computes it from the counts, so it is null when precision or recall is null and 0.0 when "
    "both are defined and tp is 0."
)
PUBLICATION_READY_SCOPE = (
    "publication_ready covers items 1, 2 and 4 of the publication gate in review-protocol.md: no row is "
    "pending, every labelled row has the fields that gate item 2 and First review steps 6 and 7 require "
    "(a 'present' cell needs a source pinpoint), and the summary command can exit 0. It does not check "
    "the pinpoint that First review step 5 also asks for a 'missing' cell, adjudication (item 3), the "
    "limitations stated in the report (item 5), the separate legal review of any statement about a named "
    "issuer (item 6), or the reconciliation against ESMA's Title II CSV that methodology.md requires before "
    "a reviewed publication. Only with --findings does the command check that the matrix holds exactly the "
    "detector's cells and that no review date precedes the detector run. True is necessary for "
    "publication, not sufficient."
)
# Second review and adjudication ("Second review and adjudication" in review-protocol.md). The study's
# scripts/build_review_matrix.py reads and writes the sheets; the rules for them live here, where ruff
# and the tests cover them. The protocol asks for "at least 20%" of the non-flagged cells.
SECOND_REVIEW_MIN_FRACTION = Fraction(1, 5)
CELL_FIELDS = ("study_doc_id", "document_hash_sha256", "rule_id", "annex_item")
# The columns of each review in the adjudication file, with the sheet column each one copies.
_REVIEW_COLUMNS = (
    ("label", "human_label"),
    ("reviewer_id", "reviewer_id"),
    ("reviewed_at", "reviewed_at"),
    ("pinpoint", "source_pinpoint"),
    ("note", "review_note"),
)
ADJUDICATION_FIELDS = (
    "final_label",
    "adjudicated_by",
    "adjudicated_at",
    "final_pinpoint",
    "adjudication_reason",
)
DISAGREEMENT_FIELDS = (
    *CELL_FIELDS,
    *(f"{review}_{suffix}" for review in ("first", "second") for suffix, _ in _REVIEW_COLUMNS),
    *ADJUDICATION_FIELDS,
)
_FIXED_DISAGREEMENT_FIELDS = tuple(field for field in DISAGREEMENT_FIELDS if field not in ADJUDICATION_FIELDS)


def summarize_rows(
    rows: Iterable[Mapping[str, str]],
    *,
    today: date | None = None,
    not_before: date | None = None,
    analyses: AnalysisContext | None = None,
) -> dict[str, Any]:
    """Return confusion-matrix metrics without treating unresolved rows as labels.

    `today` and `not_before` bound `reviewed_at` where given. Neither defaults to a value, so the
    function does not read the clock; the command passes the current date and, with --findings,
    the detector run date.

    With `analyses` (the command's --analyses), the summary also holds the analyses of the study's
    draft analysis plan under the keys detector, settings, exclusions, analyses and agreement,
    after the keys above, which stay the same (analysis_summary). Without it, nothing changes.
    """
    if analyses is not None:
        rows = list(rows)
    counts = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    label_counts = {label: 0 for label in sorted(ALLOWED_LABELS)}
    protocol_gaps: list[dict[str, Any]] = []
    reviewers: set[str] = set()
    rows_with_reviewer = 0
    total = 0

    for row_number, row in enumerate(rows, start=2):
        if not any((value or "").strip() for value in row.values()):
            continue
        total += 1
        detector_status = _text(row, "detector_status")
        human_label = _text(row, "human_label") or "pending"

        if detector_status not in ALLOWED_DETECTOR_STATUSES:
            raise ValueError(f"row {row_number}: unsupported detector_status {detector_status!r}")
        if human_label not in ALLOWED_LABELS:
            raise ValueError(f"row {row_number}: unsupported human_label {human_label!r}")

        label_counts[human_label] += 1
        if human_label == "pending":
            continue
        if _text(row, "reviewer_id"):
            reviewers.add(_text(row, "reviewer_id"))
            rows_with_reviewer += 1
        problems = protocol_problems(row, human_label, today=today, not_before=not_before)
        if problems:
            protocol_gaps.append(
                {
                    "row": row_number,
                    "study_doc_id": _text(row, "study_doc_id"),
                    "rule_id": _text(row, "rule_id"),
                    "problems": problems,
                }
            )
        if human_label not in EVALUABLE_LABELS:
            continue

        predicted_missing = detector_status == "flagged"
        actually_missing = human_label == "missing"
        if predicted_missing and actually_missing:
            counts["tp"] += 1
        elif predicted_missing and not actually_missing:
            counts["fp"] += 1
        elif not predicted_missing and actually_missing:
            counts["fn"] += 1
        else:
            counts["tn"] += 1

    precision = _ratio(counts["tp"], counts["tp"] + counts["fp"])
    recall = _ratio(counts["tp"], counts["tp"] + counts["fn"])
    # F1 from the counts, so it is not built from rounded precision and recall. The protocol does
    # not define F1; METRIC_NOTE records this formula and its zero case for readers of the summary.
    f1 = (
        None
        if precision is None or recall is None
        else _ratio(2 * counts["tp"], 2 * counts["tp"] + counts["fp"] + counts["fn"])
    )
    completed = total - label_counts["pending"]

    summary = {
        "schema_version": SCHEMA_VERSION,
        "rows_total": total,
        "rows_completed": completed,
        "rows_pending": label_counts["pending"],
        "completion_rate": _ratio(completed, total),
        "label_counts": label_counts,
        "confusion_matrix": counts,
        "metrics": {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "evaluable_rows": sum(counts.values()),
        },
        "rows_with_protocol_gaps": len(protocol_gaps),
        "protocol_gaps": protocol_gaps,
        "reviewers_recorded": len(reviewers),
        "review_disclosure": review_disclosure(completed, rows_with_reviewer, len(reviewers)),
        "publication_ready": total > 0 and label_counts["pending"] == 0 and not protocol_gaps,
        "publication_ready_scope": PUBLICATION_READY_SCOPE,
        "metric_note": METRIC_NOTE,
    }
    if analyses is not None:
        summary.update(analysis_summary(rows, analyses, today=today, not_before=not_before))
    return summary


def review_disclosure(rows_completed: int, rows_with_reviewer: int, reviewers: int) -> str:
    """Say what the matrix can show about review depth, which is never more than one review per row."""
    if rows_completed == 0:
        return "No row has a final label yet."
    identifiers = "identifier" if reviewers == 1 else "identifiers"
    if rows_with_reviewer == rows_completed:
        recorded = f"Each of the {rows_completed} labelled rows records one reviewer and one final label"
    else:
        verb = "records" if rows_with_reviewer == 1 else "record"
        recorded = (
            f"Each of the {rows_completed} labelled rows records one final label and at most one reviewer; "
            f"{rows_with_reviewer} of them {verb} a reviewer"
        )
    return (
        f"{recorded}; the rows carry {reviewers} distinct reviewer {identifiers}. The matrix has no field "
        "for a second review or adjudication, so this count does not show that any row was reviewed "
        "twice. Unless a separate record of second review and adjudication exists, the report must state "
        "that the labels are single-reviewed."
    )


def protocol_problems(
    row: Mapping[str, str],
    human_label: str,
    *,
    today: date | None = None,
    not_before: date | None = None,
) -> list[str]:
    """Return the fields this labelled row lacks; the comment below names the protocol text behind each."""
    problems = []
    if not _text(row, "reviewer_id"):
        problems.append("reviewer_id is empty")
    date_problem = _review_date_problem(_text(row, "reviewed_at"), today, not_before)
    if date_problem:
        problems.append(date_problem)
    # The protocol is not uniform here. First review step 5 asks for a pinpoint for 'present' and
    # 'missing'; publication gate item 2 (and methodology.md) accept a pinpoint or an explanation for
    # both; the 'present' label definition requires a recorded pinpoint. This check follows the label
    # definition for 'present' and gate item 2 for 'missing', whose absence a pinpoint cannot show.
    if human_label == "present" and not _text(row, "source_pinpoint"):
        problems.append("'present' needs a source_pinpoint")
    if human_label == "missing" and not (_text(row, "source_pinpoint") or _text(row, "review_note")):
        problems.append("'missing' needs a source_pinpoint or a review_note")
    if human_label in NOTE_REQUIRED_LABELS and not _text(row, "review_note"):
        problems.append(f"'{human_label}' needs a review_note explaining it")
    return problems


def _review_date_problem(value: str, today: date | None, not_before: date | None) -> str | None:
    try:
        reviewed = date.fromisoformat(value) if _REVIEW_DATE.fullmatch(value) else None
    except ValueError:
        reviewed = None
    if reviewed is None:
        return "reviewed_at is not a date in the form YYYY-MM-DD, such as 2026-10-14"
    if today is not None and reviewed > today:
        return f"reviewed_at {value} is later than today ({today.isoformat()})"
    if not_before is not None and reviewed < not_before:
        return f"reviewed_at {value} is earlier than the detector run ({not_before.isoformat()})"
    return None


def detector_run_date(findings: Mapping[str, Any]) -> date:
    """Return the calendar date of the detector run, which no review date can precede."""
    if not isinstance(findings, Mapping):
        raise ValueError("the findings file does not hold a JSON object")
    value = str(findings.get("generated_at") or "")
    if not _REVIEW_DATE.fullmatch(value[:10]):
        raise ValueError(f"generated_at {value!r} does not start with a YYYY-MM-DD date")
    return date.fromisoformat(value[:10])


def detector_cells(findings: Mapping[str, Any]) -> dict[tuple[str, str], str]:
    """Return the detector status of each document-rule cell, as the review-sheet builder sets it."""
    try:
        rule_ids = [rule["rule_id"] for rule in findings["rules"]]
        cells: dict[tuple[str, str], str] = {}
        for document in findings["results"]:
            flagged = {finding["rule_id"] for finding in document["findings"]}
            for rule_id in rule_ids:
                status = "flagged" if rule_id in flagged else "not_flagged"
                cells[(document["study_doc_id"], rule_id)] = status
    except (KeyError, TypeError) as exc:
        raise ValueError(f"the findings file lacks the rules or results it needs ({exc!r})") from exc
    return cells


def matrix_mismatches(
    rows: Iterable[Mapping[str, str]], expected: Mapping[tuple[str, str], str]
) -> list[str]:
    """Return each way the matrix cells differ from the detector cells in the findings."""
    seen: set[tuple[str, str]] = set()
    problems: list[str] = []
    for row in rows:
        if not any((value or "").strip() for value in row.values()):
            continue
        key = (_text(row, "study_doc_id"), _text(row, "rule_id"))
        cell = f"{key[0]} {key[1]}"
        status = _text(row, "detector_status")
        if key in seen:
            problems.append(f"{cell}: more than one row")
        elif key not in expected:
            problems.append(f"{cell}: not a cell of the findings")
        elif status != expected[key]:
            problems.append(f"{cell}: detector_status {status!r}, the findings give {expected[key]!r}")
        seen.add(key)
    problems.extend(
        f"{doc} {rule}: missing from the matrix" for doc, rule in expected if (doc, rule) not in seen
    )
    return problems


def second_review_selection(
    keys: Sequence[tuple[str, str]],
    flagged: Collection[tuple[str, str]],
    first_labels: Mapping[tuple[str, str], str],
    *,
    seed: int,
    fraction: Fraction = SECOND_REVIEW_MIN_FRACTION,
) -> list[tuple[str, str]]:
    """Return the cells of a second review of the protocol's subset, in the order of `keys`.

    The subset is every flagged cell, every cell the first review labelled uncertain,
    extraction_failure or not_applicable, and ceil(fraction x non-flagged cells) non-flagged cells
    drawn at random. The draw ranks the non-flagged cells by the SHA-256 of
    "<seed>|second-review|<study_doc_id>|<rule_id>" and takes the lowest. It depends only on the
    seed, the fraction and the cells, not on any label or random number generator, so anyone can
    repeat it.
    """
    fraction = Fraction(fraction)
    if not SECOND_REVIEW_MIN_FRACTION <= fraction <= 1:
        raise ValueError(f"the fraction must lie between 0.2 and 1, not {float(fraction)}")
    non_flagged = [key for key in keys if key not in flagged]
    ranked = sorted(non_flagged, key=lambda key: (_selection_rank(seed, key), key))
    drawn = set(ranked[: math.ceil(fraction * len(non_flagged))])
    return [
        key for key in keys if key in flagged or key in drawn or first_labels.get(key) in NOTE_REQUIRED_LABELS
    ]


def _selection_rank(seed: int, key: tuple[str, str]) -> str:
    return hashlib.sha256(f"{seed}|second-review|{key[0]}|{key[1]}".encode()).hexdigest()


def second_review_problems(
    keys: Sequence[tuple[str, str]],
    flagged: Collection[tuple[str, str]],
    first_cells: Mapping[tuple[str, str], Mapping[str, str]],
    second_cells: Mapping[tuple[str, str], Mapping[str, str]],
    *,
    today: date | None = None,
    not_before: date | None = None,
) -> list[str]:
    """Return why the second sheet cannot yet be compared with the completed first review.

    `second_cells` holds every row of the second sheet, pending or not. The sheet must hold the
    cells that review-protocol.md has a second reviewer assess, each labelled with the fields that
    protocol_problems requires, by a reviewer other than the first reviewer of that cell.
    """
    known = set(keys)
    problems = [
        f"{doc} {rule}: not a cell of the findings" for doc, rule in second_cells if (doc, rule) not in known
    ]
    required = [
        key
        for key in keys
        if key in flagged or (_text(first_cells.get(key, {}), "human_label") in NOTE_REQUIRED_LABELS)
    ]
    absent = [f"{doc} {rule}" for doc, rule in required if (doc, rule) not in second_cells]
    if absent:
        problems.append(
            "the second sheet lacks cells that the protocol has the second reviewer assess (flagged, or "
            "labelled uncertain, extraction_failure or not_applicable in the first review): "
            + ", ".join(absent)
        )
    non_flagged = [key for key in keys if key not in flagged]
    held = sum(1 for key in non_flagged if key in second_cells)
    needed = math.ceil(SECOND_REVIEW_MIN_FRACTION * len(non_flagged))
    if held < needed:
        problems.append(
            f"the second sheet holds {held} of the {len(non_flagged)} non-flagged cells; the protocol "
            f"asks for at least 20%, that is {needed}"
        )
    pending = [
        cell for cell in second_cells.values() if (_text(cell, "human_label") or "pending") == "pending"
    ]
    if pending:
        problems.append(f"{len(pending)} of {len(second_cells)} second-review cells are still pending")
        return problems
    for key, cell in second_cells.items():
        label = _text(cell, "human_label")
        found = (
            protocol_problems(cell, label, today=today, not_before=not_before)
            if label in ALLOWED_LABELS
            else [f"unsupported human_label {label!r}"]
        )
        first_reviewer = _text(first_cells.get(key, {}), "reviewer_id")
        if first_reviewer and _text(cell, "reviewer_id") == first_reviewer:
            found.append(f"reviewer_id {first_reviewer!r} also made the first review of this cell")
        problems.extend(f"{key[0]} {key[1]}: {problem}" for problem in found)
    return problems


def latest_review_date(*sheets: Mapping[tuple[str, str], Mapping[str, str]]) -> date | None:
    """Return the latest review date in the sheets, the earliest date an adjudication may carry."""
    dates = []
    for sheet in sheets:
        for cell in sheet.values():
            value = _text(cell, "reviewed_at")
            if _review_date_problem(value, None, None) is None:
                dates.append(date.fromisoformat(value))
    return max(dates, default=None)


def disagreement_rows(
    cells: Iterable[Mapping[str, str]],
    first_cells: Mapping[tuple[str, str], Mapping[str, str]],
    second_cells: Mapping[tuple[str, str], Mapping[str, str]],
) -> list[dict[str, str]]:
    """Return a row of the adjudication file for each cell whose two labels differ, in cell order.

    Each row holds the cell, both reviews and empty adjudication fields with final_label pending.
    It holds no detector field, so the adjudicator does not see the detector status.
    """
    rows = []
    for cell in cells:
        key = (_text(cell, "study_doc_id"), _text(cell, "rule_id"))
        if key not in second_cells:
            continue
        reviews = (("first", first_cells.get(key, {})), ("second", second_cells[key]))
        if _text(reviews[0][1], "human_label") == _text(reviews[1][1], "human_label"):
            continue
        row = {field: _text(cell, field) for field in CELL_FIELDS}
        for review, values in reviews:
            row.update({f"{review}_{suffix}": _text(values, field) for suffix, field in _REVIEW_COLUMNS})
        row.update({field: "" for field in ADJUDICATION_FIELDS})
        row["final_label"] = "pending"
        rows.append(row)
    return rows


def carry_adjudications(
    current: Sequence[Mapping[str, str]], existing: Iterable[Mapping[str, str]]
) -> list[dict[str, str]]:
    """Return the current disagreement rows with the decisions already entered in `existing`.

    A decided row must still match a current row in every review column. If the sheets changed
    after it was decided, or two decided rows name one cell, it is reported, never dropped or
    overwritten. The report names the columns that differ, so a column a spreadsheet rewrote (a
    date saved as 14.10.2026) can be restored by hand.
    """
    rows = {(row["study_doc_id"], row["rule_id"]): dict(row) for row in current}
    carried: set[tuple[str, str]] = set()
    problems = []
    for row in existing:
        if not _adjudication_entered(row):
            continue
        key = (_text(row, "study_doc_id"), _text(row, "rule_id"))
        target = rows.get(key)
        if key in carried:
            problems.append(f"{key[0]} {key[1]}: more than one adjudicated row")
        elif target is None:
            problems.append(
                f"{key[0]} {key[1]}: adjudicated, but the two sheets no longer list it as a disagreement; "
                "restore the row as --disagreements wrote it, or empty its adjudication columns"
            )
        elif changed := [f for f in _FIXED_DISAGREEMENT_FIELDS if _text(row, f) != target[f]]:
            problems.append(
                f"{key[0]} {key[1]}: adjudicated, but these columns no longer match the two sheets: "
                f"{', '.join(changed)}; restore them as --disagreements wrote them, or empty the "
                "adjudication columns to adjudicate the cell again"
            )
        else:
            target.update({field: row.get(field) or "" for field in ADJUDICATION_FIELDS})
            carried.add(key)
    if problems:
        raise ValueError(
            "the adjudication file holds decisions the two sheets no longer support; nothing written:\n  "
            + "\n  ".join(problems)
        )
    return list(rows.values())


def adjudicated_cells(
    expected: Sequence[Mapping[str, str]],
    columns: Sequence[str],
    rows: Sequence[Mapping[str, str]],
    *,
    today: date | None = None,
    not_before: date | None = None,
) -> dict[tuple[str, str], dict[str, str]]:
    """Return the final reviewer cells of the adjudicated disagreements, or raise ValueError.

    `expected` holds the current disagreement rows (disagreement_rows); `columns` and `rows` are
    the adjudication file. The file must hold the same cells in the same order, with the review
    columns unchanged. Each row needs a final label other than pending; the adjudicator, either
    both reviewers by consensus ("a+b") or a person who made neither review; a date in the form
    YYYY-MM-DD no earlier than `not_before` (the latest review date: the protocol compares the
    reviews only after both are complete) and no later than `today`; the reasoning; and, for a
    'present' label, a final pinpoint, as protocol_problems requires of every 'present' cell.
    """
    if list(columns) != list(DISAGREEMENT_FIELDS):
        raise ValueError(
            "the adjudication file does not have the columns that --disagreements writes; "
            "save it as comma-separated UTF-8 without adding, removing or renaming columns"
        )
    if len(rows) != len(expected):
        raise ValueError(
            f"the adjudication file has {len(rows)} rows, but the two reviews now differ in "
            f"{len(expected)} cells; run --disagreements again"
        )
    problems = []
    pending = 0
    cells: dict[tuple[str, str], dict[str, str]] = {}
    for want, got in zip(expected, rows, strict=True):
        cell = f"{want['study_doc_id']} {want['rule_id']}"
        changed = [field for field in _FIXED_DISAGREEMENT_FIELDS if _text(got, field) != want[field]]
        if changed:
            listed = ", ".join(changed)
            problems.append(f"{cell}: {listed} differ from the two reviews; run --disagreements again")
            continue
        label = _text(got, "final_label") or "pending"
        if label == "pending":
            pending += 1
            continue
        found = [] if label in ALLOWED_LABELS else [f"unsupported final_label {label!r}"]
        reviewers = (want["first_reviewer_id"], want["second_reviewer_id"])
        found.extend(_adjudicator_problems(_text(got, "adjudicated_by"), reviewers))
        date_problem = _review_date_problem(_text(got, "adjudicated_at"), today, None)
        if date_problem:
            found.append(date_problem.replace("reviewed_at", "adjudicated_at", 1))
        elif not_before is not None and date.fromisoformat(_text(got, "adjudicated_at")) < not_before:
            found.append(
                f"adjudicated_at {_text(got, 'adjudicated_at')} is earlier than the latest review date "
                f"in the two sheets ({not_before.isoformat()})"
            )
        if not _text(got, "adjudication_reason"):
            found.append("adjudication_reason is empty")
        if label == "present" and not _text(got, "final_pinpoint"):
            found.append("'present' needs a final_pinpoint")
        problems.extend(f"{cell}: {problem}" for problem in found)
        cells[(want["study_doc_id"], want["rule_id"])] = adjudicated_cell(got)
    if pending:
        problems.append(f"{pending} of {len(expected)} disagreements are still pending")
    if problems:
        raise ValueError("the adjudication file is not complete:\n  " + "\n  ".join(problems))
    return cells


def adjudicated_cell(row: Mapping[str, str]) -> dict[str, str]:
    """Return the reviewer fields that an adjudicated row puts into the matrix."""
    return {
        "human_label": _text(row, "final_label"),
        "reviewer_id": "+".join(part.strip() for part in _text(row, "adjudicated_by").split("+")),
        "reviewed_at": _text(row, "adjudicated_at"),
        "source_pinpoint": _text(row, "final_pinpoint"),
        "review_note": f"{_adjudicated_labels(row)}: {_text(row, 'adjudication_reason')}",
    }


def _adjudicator_problems(value: str, reviewers: Sequence[str]) -> list[str]:
    if not value:
        return ["adjudicated_by is empty"]
    people = [part.strip() for part in value.split("+")]
    if not all(people):
        return [
            f"adjudicated_by {value!r}: join two reviewer identifiers with '+', as in reviewer-a+reviewer-b"
        ]
    named, original = set(people), set(reviewers)
    if named <= original and named != original:
        return [
            f"adjudicated_by {value!r} names only one of the two reviewers of this cell; record both "
            f"({'+'.join(reviewers)}) for a consensus, or a person who made neither review"
        ]
    return []


def _adjudication_entered(row: Mapping[str, str]) -> bool:
    return (_text(row, "final_label") or "pending") != "pending" or any(
        _text(row, field) for field in ADJUDICATION_FIELDS[1:]
    )


def _text(row: Mapping[str, str], field: str) -> str:
    return (row.get(field) or "").strip()


def _ratio(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else round(numerator / denominator, 6)


def _count(number: int, noun: str) -> str:
    return f"{number} {noun}" if number == 1 else f"{number} {noun}s"


# Analyses of the study's draft analysis plan (analysis-plan.md, sections 7 to 10). summarize_rows
# computes them only when given `analyses` (the command's --analyses) and then adds the keys
# detector, settings, exclusions, analyses and agreement after its other keys, which stay the same:
#
# - analysis sets: the primary set (every document of the matrix except those named with
#   --primary-exclude and an in-sample calibration document) and the full set S1;
# - per set: label counts, TP, FP, FN and TN, precision, recall and specificity, each with a Wilson
#   and a Clopper-Pearson interval, a seeded document-cluster bootstrap and the headline interval,
#   and F1 as METRIC_NOTE defines it; per-rule counts for the primary set only;
# - sensitivity analyses S2 (offeror-cluster bootstrap, and one document per offeror), S3 and S4
#   ('uncertain' counted as 'missing', then as 'present'); S5 is recorded as not computed;
# - agreement between the first review and the second review of human-review-second.csv, and the
#   state of their adjudication (publication gate item 3);
# - the detector identity: the findings file's hash, schema, digest and date, and the detector
#   commit once the findings file or the Detector row of analysis-plan.md names it (step 0.4).
#
# The per-document and per-offeror counts, and S1's per-rule table, go only to internal_detail
# (--internal-out), because the plan keeps per-document counts unpublished (section 10); git
# ignores human-review-internal*.json under studies/. While any cell is pending, the analyses carry
# no detector outcome beyond what the labelled cells imply. No function here fills, infers or
# changes a label.
INTERNAL_SCHEMA_VERSION = "micar-study-human-validation-internal.v1"
ANALYSIS_PLAN_FILENAME = "analysis-plan.md"
# analysis-plan.md section 9: B = 10,000 replicates and seed 20261014, and the draft "[10]%" limit
# above which the bootstrap interval is reported as unstable and the Wilson interval is the headline.
BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEED = 20261014
MAX_DROPPED_FRACTION = 0.10
_DIGITS = 6
EVALUABLE_CATEGORIES = ("present", "missing")
EXCLUDED_LABELS = ("not_applicable", "uncertain", "extraction_failure")
# Agreement over all labels uses the five final labels as categories; over present and missing, those two.
AGREEMENT_CATEGORIES = (*EVALUABLE_CATEGORIES, *EXCLUDED_LABELS)
F1_RULE = "2TP / (2TP + FP + FN), null when precision or recall is null, as metric_note states"
HEADLINE_RULE = (
    "The headline interval is the wider of the Wilson interval and the document-cluster bootstrap "
    "interval (upper minus lower bound, rounded to six decimals; the Wilson interval on a tie). If "
    "more than the maximum fraction of bootstrap replicates is dropped for a zero denominator, or the "
    "bootstrap is undefined, the Wilson interval is the headline (analysis-plan.md section 9)."
)
BLIND_WHILE_PENDING = (
    "withheld while any cell is pending: analysis-plan.md section 5 takes this count from the "
    "findings file after labelling, and the summary carries no detector outcome while labelling is open"
)
# analysis-plan.md section 4: an in-sample calibration document's cells "carry the note
# `calibration`". A document is the calibration document when every one of its cells' notes has it.
_CALIBRATION_NOTE = re.compile(r"(?<![\w-])calibration(?![\w-])", re.IGNORECASE)
# The Detector row of analysis-plan.md section 2 ends "detector commit: [SHA, see step 0.4 ...]"
# until the reviewer names the commit.
_PLAN_COMMIT = re.compile(
    r"^\|\s*Detector\s*\|.*?detector commit:\s*`?(?P<sha>[0-9a-f]{7,40})`?(?![0-9a-zA-Z])",
    re.MULTILINE,
)
# The banner of analysis-plan.md: "> **DRAFT, not adopted; ...**" until adoption, then
# "> - Adopted by: <name>, on <YYYY-MM-DD>". The signing order records the adoption commit's SHA
# outside the signed files, so "> - Pre-registration commit:" normally names none; a SHA there is
# still read.
_PLAN_DRAFT = re.compile(r"^>\s*\*\*DRAFT, not adopted\b", re.MULTILINE)
_PLAN_ADOPTED = re.compile(
    r"^>\s*-\s*Adopted by:\s*(?P<who>[^\n]*?),\s*on\s*(?P<date>[^\s]+)\s*$", re.MULTILINE
)
_PLAN_PREREGISTRATION = re.compile(
    r"^>\s*-\s*Pre-registration commit:\s*`?(?P<sha>[^`\s]+)`?\s*$", re.MULTILINE
)
_DOC_NUMBER = re.compile(r"(\d+)")
# The start of the note that build_review_matrix.py --merge-blinded writes into an adjudicated
# matrix cell (adjudicated_cell).
_ADJUDICATED_NOTE = "Adjudicated (first: "
_REVIEW_FIELDS = tuple(field for _, field in _REVIEW_COLUMNS)


@dataclasses.dataclass(frozen=True)
class Cell:
    """One document-rule cell of the matrix, as the analyses read it."""

    doc: str
    rule: str
    doc_hash: str
    flagged: bool
    label: str
    note: str


@dataclasses.dataclass(frozen=True)
class SecondReview:
    """The second reviewer's sheet and, once written, the adjudication file (build_review_matrix.py)."""

    sheet: str
    rows: tuple[Mapping[str, str], ...]
    adjudication: str | None = None
    adjudication_columns: tuple[str, ...] = ()
    adjudication_rows: tuple[Mapping[str, str], ...] = ()


@dataclasses.dataclass(frozen=True)
class AnalysisContext:
    """What the analyses read besides the matrix. load_analysis_context fills it from the files."""

    detector: Mapping[str, Any] = dataclasses.field(default_factory=lambda: detector_identity())
    offerors: Mapping[str, tuple[str, str]] | None = None
    offerors_reason: str | None = "no source manifest was given (--manifest), so the offerors are unknown"
    plan: Mapping[str, Any] = dataclasses.field(default_factory=lambda: plan_status(None))
    primary_exclusions: tuple[str, ...] = ()
    second_review: SecondReview | None = None
    replicates: int = BOOTSTRAP_REPLICATES
    seed: int = BOOTSTRAP_SEED


def load_analysis_context(
    findings_path: Path,
    *,
    manifest: Path | None = None,
    analysis_plan: Path | None = None,
    primary_exclude: Sequence[str] = (),
    second_review: Path | None = None,
    adjudication: Path | None = None,
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
) -> AnalysisContext:
    """Read the files that the analyses use. None of them is written."""
    raw = findings_path.read_bytes()
    findings = json.loads(raw.decode("utf-8"))
    if not isinstance(findings, Mapping):
        raise ValueError(f"{findings_path.name} does not hold a JSON object")
    plan_text = None if analysis_plan is None else analysis_plan.read_text(encoding="utf-8")
    plan_name = ANALYSIS_PLAN_FILENAME if analysis_plan is None else analysis_plan.name
    offerors = None
    offerors_reason = AnalysisContext.offerors_reason
    if manifest is not None:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        entries = data.get("entries") if isinstance(data, Mapping) else None
        if not isinstance(entries, list):
            raise ValueError(f"{manifest.name} holds no list of entries")
        offerors = {
            _clean(entry.get("study_doc_id")): (
                _clean(entry.get("offeror_or_issuer")),
                _clean(entry.get("document_hash_sha256")).lower(),
            )
            for entry in entries
            if isinstance(entry, Mapping)
        }
        offerors_reason = None
    second = None
    if second_review is not None:
        columns, rows = _read_sheet(second_review)
        missing = [field for field in ("study_doc_id", "rule_id", *_REVIEW_FIELDS) if field not in columns]
        if missing:
            raise ValueError(
                f"{second_review.name} lacks the columns {', '.join(missing)}; "
                "save it as comma-separated UTF-8"
            )
        adjudication_columns, adjudication_rows = (
            ([], []) if adjudication is None else _read_sheet(adjudication)
        )
        second = SecondReview(
            sheet=second_review.name,
            rows=tuple(rows),
            adjudication=None if adjudication is None else adjudication.name,
            adjudication_columns=tuple(adjudication_columns),
            adjudication_rows=tuple(adjudication_rows),
        )
    return AnalysisContext(
        detector=detector_identity(
            findings_path.name, hashlib.sha256(raw).hexdigest(), findings, plan_text, plan_name=plan_name
        ),
        offerors=offerors,
        offerors_reason=offerors_reason,
        plan=plan_status(plan_text, name=plan_name),
        primary_exclusions=tuple(dict.fromkeys(primary_exclude)),
        second_review=second,
        replicates=replicates,
        seed=seed,
    )


def parse_rows(rows: Iterable[Mapping[str, str]]) -> list[Cell]:
    """Read matrix rows into cells. Blank rows are skipped; a blank label counts as pending."""
    cells: list[Cell] = []
    seen: set[tuple[str, str]] = set()
    for row_number, row in enumerate(rows, start=2):
        if not any((value or "").strip() for value in row.values()):
            continue
        detector_status = _text(row, "detector_status")
        human_label = _text(row, "human_label") or "pending"
        if detector_status not in ALLOWED_DETECTOR_STATUSES:
            raise ValueError(f"row {row_number}: unsupported detector_status {detector_status!r}")
        if human_label not in ALLOWED_LABELS:
            raise ValueError(f"row {row_number}: unsupported human_label {human_label!r}")
        doc, rule = _text(row, "study_doc_id"), _text(row, "rule_id")
        if not doc or not rule:
            raise ValueError(f"row {row_number}: the analyses need study_doc_id and rule_id")
        if (doc, rule) in seen:
            raise ValueError(f"row {row_number}: more than one row for {doc} {rule}")
        seen.add((doc, rule))
        cells.append(
            Cell(
                doc=doc,
                rule=rule,
                doc_hash=_text(row, "document_hash_sha256").lower(),
                flagged=detector_status == "flagged",
                label=human_label,
                note=_text(row, "review_note"),
            )
        )
    return cells


def analysis_summary(
    rows: Sequence[Mapping[str, str]],
    context: AnalysisContext,
    *,
    today: date | None = None,
    not_before: date | None = None,
) -> dict[str, Any]:
    """Return the keys that --analyses adds to the summary, in the order they are added."""
    cells = parse_rows(rows)
    complete = bool(cells) and all(cell.label != "pending" for cell in cells)
    calibration, excluded, full, primary = analysis_sets(cells, context.primary_exclusions)
    offerors, offerors_reason = _offeror_map(context, cells)
    bootstrap = {"replicates": context.replicates, "seed": context.seed}
    named = ", ".join(excluded) or "none"
    analyses: dict[str, Any] = {
        "primary": analysis_block(
            f"Primary: every document of the matrix except the primary exclusions ({named}; "
            "--primary-exclude, analysis-plan.md section 5) and an in-sample calibration document.",
            primary,
            per_rule=True,
            **bootstrap,
        ),
        # No per-rule table for S1: next to the primary set's table it would give the label and
        # detector outcome per rule of a single excluded document. It goes to --internal-out.
        "S1": analysis_block(
            "S1, full set: every document of the matrix, the primary exclusions included, except an "
            "in-sample calibration document.",
            full,
            **bootstrap,
        ),
    }
    analyses.update(_offeror_analyses(primary, offerors, offerors_reason, **bootstrap))
    analyses["S3"] = analysis_block(
        "S3: the primary set with 'uncertain' counted as 'missing'.",
        primary,
        uncertain_as="missing",
        **bootstrap,
    )
    analyses["S4"] = analysis_block(
        "S4: the primary set with 'uncertain' counted as 'present'.",
        primary,
        uncertain_as="present",
        **bootstrap,
    )
    analyses["S5"] = {
        "description": (
            "S5: the labels under the other reference standard and the stricter readings that reviewers "
            "record in review_note (analysis-plan.md section 10)."
        ),
        "computed": False,
        "undefined_reason": (
            "neither the codebook nor the analysis plan defines a machine-readable form for readings "
            "recorded in review notes, so the tool cannot apply them"
        ),
    }
    return {
        "detector": dict(context.detector),
        "settings": _settings(context),
        "exclusions": {
            "primary": [
                _excluded_document(doc, cells, complete=complete, plan=context.plan) for doc in excluded
            ],
            "calibration_document": _calibration_record(calibration, cells),
        },
        "analyses": analyses,
        "agreement": second_review_agreement(
            rows, cells, context.second_review, calibration=calibration, today=today, not_before=not_before
        ),
    }


def internal_detail(rows: Iterable[Mapping[str, str]], context: AnalysisContext) -> dict[str, Any]:
    """Per-document, per-offeror and S1 per-rule counts for internal quality checks; never published."""
    cells = parse_rows(rows)
    offerors, offerors_reason = _offeror_map(context, cells)
    documents = sorted_documents(cells)
    calibration, _, full, _ = analysis_sets(cells, context.primary_exclusions)
    detail: dict[str, Any] = {
        "schema_version": INTERNAL_SCHEMA_VERSION,
        "notice": (
            "Internal quality check (analysis-plan.md section 10). Per-document and per-offeror counts "
            "are not published, or only without WP identifiers, unless the conflicts check and the legal "
            "review under review-protocol.md are complete and the reviewer decides otherwise. S1's "
            "per-rule counts are kept here because, next to the published per-rule counts of the primary "
            "set, they would give the label and detector outcome per rule of an excluded document. Do not "
            "commit this file."
        ),
        "calibration_document": calibration,
        "documents": [_count_record(_cells_of(cells, [doc]), {"study_doc_id": doc}) for doc in documents],
        "S1_per_rule": {"documents": sorted_documents(full), "per_rule": _per_rule(full)},
    }
    if offerors is None:
        detail["offerors"] = None
        detail["offerors_undefined_reason"] = offerors_reason
    else:
        detail["offerors"] = [
            _count_record(_cells_of(cells, group), {"cluster": f"O{index}", "documents": group})
            for index, group in enumerate(_offeror_groups(documents, offerors), start=1)
        ]
    return detail


def tally(cells: Sequence[Cell], uncertain_as: str | None = None) -> tuple[Counts, dict[str, int]]:
    """Confusion counts and label counts; `uncertain_as` recodes 'uncertain' (S3 and S4)."""
    label_counts = {label: 0 for label in sorted(ALLOWED_LABELS)}
    tp = fp = fn = tn = 0
    for cell in cells:
        label = uncertain_as if uncertain_as and cell.label == "uncertain" else cell.label
        label_counts[label] += 1
        if label not in EVALUABLE_LABELS:
            continue
        missing = label == "missing"
        if cell.flagged and missing:
            tp += 1
        elif cell.flagged:
            fp += 1
        elif missing:
            fn += 1
        else:
            tn += 1
    return Counts(tp, fp, fn, tn), label_counts


def analysis_block(
    description: str,
    cells: Sequence[Cell],
    *,
    uncertain_as: str | None = None,
    per_rule: bool = False,
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    """Counts, point estimates, intervals and the headline interval of one analysis set."""
    documents = sorted_documents(cells)
    counts, label_counts = tally(cells, uncertain_as)
    pending = label_counts["pending"]
    clusters = [tally(_cells_of(cells, [doc]), uncertain_as)[0] for doc in documents]
    resampled = cluster_bootstrap(
        clusters, replicates=replicates, seed=seed, pending=pending, cells=len(cells)
    )
    block: dict[str, Any] = {"description": description, "documents": documents, "cells": len(cells)}
    if uncertain_as:
        block["uncertain_counted_as"] = uncertain_as
    block.update(
        {
            "label_counts": label_counts,
            "evaluable_cells": counts.tp + counts.fp + counts.fn + counts.tn,
            "excluded_cells": sum(label_counts[label] for label in EXCLUDED_LABELS),
            "pending_cells": pending,
            "confusion_matrix": counts.as_dict(),
            "metrics": _metrics(counts, resampled, pending=pending, cells=len(cells)),
        }
    )
    if per_rule:
        block["per_rule"] = _per_rule(cells)
    return block


def analysis_sets(
    cells: Sequence[Cell], exclusions: Sequence[str] = ()
) -> tuple[str | None, list[str], list[Cell], list[Cell]]:
    """The calibration document, the primary exclusions, and the cells of S1 and of the primary set."""
    calibration = calibration_document(cells)
    documents = sorted_documents(cells)
    unknown = [doc for doc in exclusions if doc not in documents]
    if unknown:
        raise ValueError(f"--primary-exclude {', '.join(unknown)}: not a document of the matrix")
    excluded = [doc for doc in exclusions if doc != calibration]
    full = [cell for cell in cells if cell.doc != calibration]
    primary = [cell for cell in full if cell.doc not in excluded]
    return calibration, excluded, full, primary


def calibration_document(cells: Sequence[Cell]) -> str | None:
    """The in-sample calibration document: every one of its cells' notes says 'calibration'.

    A document with the word in some but not all of its notes, or more than one such document,
    stops the run, because the analysis sets would then be ambiguous.
    """
    marks: dict[str, list[bool]] = {}
    for cell in cells:
        marks.setdefault(cell.doc, []).append(bool(_CALIBRATION_NOTE.search(cell.note)))
    partial = [doc for doc, found in marks.items() if any(found) and not all(found)]
    if partial:
        raise ValueError(
            f"{', '.join(partial)}: the note 'calibration' appears on some but not all cells. "
            "analysis-plan.md section 4 marks every cell of the calibration document with it; "
            "remove the word from other notes or add it to every cell of that document"
        )
    marked = [doc for doc, found in marks.items() if all(found)]
    if len(marked) > 1:
        raise ValueError(f"{', '.join(marked)}: more than one document is marked 'calibration'")
    return marked[0] if marked else None


def sorted_documents(cells: Iterable[Cell]) -> list[str]:
    """Distinct document IDs in ascending WP number."""
    return sorted({cell.doc for cell in cells}, key=_doc_sort_key)


def plan_status(
    text: str | None,
    reason: str = "no analysis plan was given (--analysis-plan)",
    *,
    name: str = ANALYSIS_PLAN_FILENAME,
) -> dict[str, Any]:
    """Whether the analysis plan is still a draft or names its adoption, read from its banner.

    `draft` while the banner says "DRAFT, not adopted" and the "Adopted by" line is still a
    placeholder; `adopted` once the banner is gone and that line names a reviewer and an ISO date,
    with the pre-registration commit when the banner names one; otherwise `unknown` with the reason.
    """
    record: dict[str, Any] = {
        "file": name,
        "status": "unknown",
        "adopted_on": None,
        "preregistration_commit": None,
        "reason": reason,
    }
    if text is None:
        return record
    draft = bool(_PLAN_DRAFT.search(text))
    adopted = _PLAN_ADOPTED.search(text)
    filled = (
        adopted is not None
        and adopted.group("who").strip() != ""
        and "[" not in adopted.group("who")
        and re.fullmatch(r"\d{4}-\d{2}-\d{2}", adopted.group("date")) is not None
    )
    banner = f"the banner of {name} says 'DRAFT, not adopted'"
    if draft and not filled:
        return {**record, "status": "draft", "reason": banner}
    if draft:
        return {**record, "reason": f"{banner}, but its 'Adopted by' line is filled in"}
    if not filled or adopted is None:
        return {
            **record,
            "reason": (
                f"{name} has neither the 'DRAFT, not adopted' banner nor an 'Adopted by' line with a "
                "reviewer and an ISO date"
            ),
        }
    commit = _PLAN_PREREGISTRATION.search(text)
    sha = commit.group("sha").lower() if commit else ""
    return {
        **record,
        "status": "adopted",
        "adopted_on": adopted.group("date"),
        "preregistration_commit": sha if re.fullmatch(r"[0-9a-f]{7,40}", sha) else None,
        "reason": None,
    }


def plan_phrase(plan: Mapping[str, Any], *, short: bool = False) -> str:
    """The plan's status in words, for the summary's definitions and exclusion grounds."""
    status = plan.get("status")
    if status == "draft":
        return "DRAFT, not adopted"
    if status == "adopted":
        if short:
            return f"adopted on {plan['adopted_on']}"
        commit = plan.get("preregistration_commit")
        named = (
            f"pre-registration commit {commit}"
            if commit
            else "pre-registration commit: see the study README (signing order, step 5)"
        )
        return f"adopted on {plan['adopted_on']}; {named}"
    return "adoption status unknown" if short else f"adoption status unknown: {plan.get('reason')}"


def detector_identity(
    findings_name: str | None = None,
    findings_sha256: str | None = None,
    findings: Mapping[str, Any] | None = None,
    plan_text: str | None = None,
    *,
    plan_name: str = ANALYSIS_PLAN_FILENAME,
    reason: str = "no findings file was read",
) -> dict[str, Any]:
    """The findings file's identity and the detector commit, from the findings or the plan's Detector row."""
    identity: dict[str, Any] = {
        "findings_file": findings_name,
        "findings_sha256": findings_sha256,
        "findings_schema": None,
        "findings_digest": None,
        "findings_generated_at": None,
        "commit": None,
        "commit_source": None,
        "commit_status": f"unknown: {reason}",
    }
    if findings is None:
        return identity
    identity.update(
        findings_schema=findings.get("schema"),
        findings_digest=findings.get("digest"),
        findings_generated_at=findings.get("generated_at"),
    )
    recorded = _clean(findings.get("detector_commit")).lower()
    if re.fullmatch(r"[0-9a-f]{7,40}", recorded):
        identity.update(
            commit=recorded,
            commit_source=f"{findings_name}, detector_commit",
            commit_status="recorded in the findings file",
        )
        return identity
    if plan_text is None:
        identity["commit_status"] = (
            f"not recorded: {findings_name} names no detector commit, and no analysis plan was given "
            "(--analysis-plan)"
        )
        return identity
    match = _PLAN_COMMIT.search(plan_text)
    if match is None:
        identity["commit_status"] = (
            f"not recorded: {findings_name} names no detector commit, and the Detector row of "
            f"{plan_name} section 2 names no detector commit yet (step 0.4)"
        )
        return identity
    identity.update(
        commit=match.group("sha"),
        commit_source=f"{plan_name}, section 2, Detector row",
        commit_status=f"named in {plan_name} (step 0.4)",
    )
    return identity


def second_review_agreement(
    rows: Sequence[Mapping[str, str]],
    cells: Sequence[Cell],
    second: SecondReview | None,
    *,
    calibration: str | None = None,
    today: date | None = None,
    not_before: date | None = None,
) -> dict[str, Any]:
    """Agreement between the first and the second review, and the state of their adjudication.

    The first review of a cell is its matrix row, except where the matrix holds the adjudicated
    cell that build_review_matrix.py --merge-blinded wrote; the adjudication file keeps the first
    review of those cells. The reviews are compared once the matrix and the second sheet have no
    pending cell, as review-protocol.md compares them only after both are complete. A second sheet
    or an adjudication file that contradicts the matrix stops the run, as the merge would.
    """
    record: dict[str, Any] = {
        "status": "not_given",
        "reason": (
            "no second-review sheet was given (--second-review); without a record of second review and "
            "adjudication, the report states that the labels are single-reviewed (review_disclosure)"
        ),
        "second_review_file": None,
        "adjudication_file": None,
        "cells_double_reviewed": None,
        "scope": None,
        "pairs": [],
        "adjudication": None,
    }
    if second is None:
        return record
    matrix = {
        (_text(row, "study_doc_id"), _text(row, "rule_id")): row
        for row in rows
        if any((value or "").strip() for value in row.values())
    }
    second_cells = _second_sheet_cells(second, matrix)
    adjudication = _adjudication_index(second, second_cells)
    first_cells, merged, corrected = _first_review(matrix, adjudication, second.adjudication)
    keys = [(cell.doc, cell.rule) for cell in cells]
    flagged = {(cell.doc, cell.rule) for cell in cells if cell.flagged}
    record.update(
        second_review_file=second.sheet,
        adjudication_file=second.adjudication,
        cells_double_reviewed=len(second_cells),
    )
    if any(cell.label == "pending" for cell in cells):
        return {
            **record,
            "status": "awaiting_merge",
            "reason": (
                "the reviews are compared once the matrix has no pending cell, after both reviews are "
                "complete and merged (review-protocol.md)"
            ),
        }
    problems = second_review_problems(
        keys, flagged, first_cells, second_cells, today=today, not_before=not_before
    )
    if any((_text(cell, "human_label") or "pending") == "pending" for cell in second_cells.values()):
        return {**record, "status": "incomplete", "reason": "; ".join(problems)}
    if problems:
        raise ValueError(f"{second.sheet} is not a complete second review:\n  " + "\n  ".join(problems))
    compared = [key for key in keys if key in second_cells and key[0] != calibration]
    labels = [
        (_text(first_cells[key], "human_label"), _text(second_cells[key], "human_label")) for key in compared
    ]
    evaluable = [pair for pair in labels if pair[0] in EVALUABLE_LABELS and pair[1] in EVALUABLE_LABELS]
    flagged_compared = sum(key in flagged for key in compared)
    return {
        **record,
        "status": "computed",
        "reason": None,
        "scope": {
            "cells": len(compared),
            "flagged_cells": flagged_compared,
            "non_flagged_cells": len(compared) - flagged_compared,
            "description": (
                "the cells of the second-review sheet, without an in-sample calibration document. Under the "
                "protocol's subset they are every flagged cell, every cell the first review labelled "
                "uncertain, extraction_failure or not_applicable, and a draw of the non-flagged cells, so "
                "agreement on them does not describe every cell (analysis-plan.md section 10)"
            ),
        },
        "pairs": [
            {
                "first_reviewers": sorted(
                    {_text(first_cells[key], "reviewer_id") for key in compared} - {""}
                ),
                "second_reviewers": sorted(
                    {_text(second_cells[key], "reviewer_id") for key in compared} - {""}
                ),
                "cells": len(labels),
                "disagreements": sum(first != second_label for first, second_label in labels),
                "all_labels": rounded(agreement(labels, AGREEMENT_CATEGORIES), _DIGITS),
                "present_missing": {
                    "scope": "cells that both reviews labelled present or missing",
                    **rounded(agreement(evaluable, EVALUABLE_CATEGORIES), _DIGITS),
                },
            }
        ],
        "adjudication": {
            **_adjudication_state(
                list(matrix.values()), first_cells, second_cells, second, merged, today=today
            ),
            # Adjudicated cells changed in the matrix after the merge (REVIEWING.md step 4).
            "corrected_after_merge": len(corrected),
        },
    }


def _second_sheet_cells(
    second: SecondReview, matrix: Mapping[tuple[str, str], Mapping[str, str]]
) -> dict[tuple[str, str], dict[str, str]]:
    cells: dict[tuple[str, str], dict[str, str]] = {}
    for row in second.rows:
        if not any((value or "").strip() for value in row.values()):
            continue
        key = (_text(row, "study_doc_id"), _text(row, "rule_id"))
        if key not in matrix:
            raise ValueError(f"{second.sheet}: {key[0]} {key[1]} is not a cell of the matrix")
        if key in cells:
            raise ValueError(f"{second.sheet}: more than one row for {key[0]} {key[1]}")
        cells[key] = {field: row.get(field) or "" for field in _REVIEW_FIELDS}
    return cells


def _adjudication_index(
    second: SecondReview, second_cells: Mapping[tuple[str, str], Mapping[str, str]]
) -> dict[tuple[str, str], Mapping[str, str]]:
    if second.adjudication is None:
        return {}
    if list(second.adjudication_columns) != list(DISAGREEMENT_FIELDS):
        raise ValueError(
            f"{second.adjudication} does not have the columns that --disagreements writes; save it as "
            "comma-separated UTF-8 without adding, removing or renaming columns"
        )
    index: dict[tuple[str, str], Mapping[str, str]] = {}
    for row in second.adjudication_rows:
        key = (_text(row, "study_doc_id"), _text(row, "rule_id"))
        if key not in second_cells:
            raise ValueError(f"{second.adjudication}: {key[0]} {key[1]} is not a cell of {second.sheet}")
        if key in index:
            raise ValueError(f"{second.adjudication}: more than one row for {key[0]} {key[1]}")
        index[key] = row
    return index


def _first_review(
    matrix: Mapping[tuple[str, str], Mapping[str, str]],
    adjudication: Mapping[tuple[str, str], Mapping[str, str]],
    adjudication_name: str | None,
) -> tuple[dict[tuple[str, str], dict[str, str]], set[tuple[str, str]], set[tuple[str, str]]]:
    """The first review of every cell, the cells adjudicated in the matrix, and those corrected since.

    A matrix cell that still starts with the note the merge wrote for a decided adjudication row,
    but differs from that row's adjudicated cell, was corrected after the merge (REVIEWING.md
    step 4); its first review comes from the adjudication file, as for an uncorrected one.
    """
    first: dict[tuple[str, str], dict[str, str]] = {}
    merged: set[tuple[str, str]] = set()
    corrected: set[tuple[str, str]] = set()
    for key, row in matrix.items():
        review = {field: _text(row, field) for field in _REVIEW_FIELDS}
        decided = adjudication.get(key)
        if decided is not None and (_text(decided, "final_label") or "pending") == "pending":
            decided = None
        if decided is not None and (
            review == adjudicated_cell(decided)
            or review["review_note"].startswith(_adjudicated_labels(decided))
        ):
            first[key] = {field: _text(decided, f"first_{suffix}") for suffix, field in _REVIEW_COLUMNS}
            merged.add(key)
            if review != adjudicated_cell(decided):
                corrected.add(key)
            continue
        if review["review_note"].startswith(_ADJUDICATED_NOTE):
            if decided is not None:
                where = (
                    f"its note does not start with {_adjudicated_labels(decided)!r}, which the merge "
                    f"writes for the decided row in {adjudication_name}"
                )
            elif adjudication_name:
                where = f"{adjudication_name} has no decided row for it"
            else:
                where = "no adjudication file was given (--adjudication)"
            raise ValueError(
                f"{key[0]} {key[1]}: the matrix holds an adjudicated cell, but {where}; pass the "
                "adjudication file that the merge used"
            )
        first[key] = review
    return first, merged, corrected


def _adjudicated_labels(row: Mapping[str, str]) -> str:
    """The start of the note that adjudicated_cell writes for a row: both reviews' labels."""
    return f"{_ADJUDICATED_NOTE}{_text(row, 'first_label')}, second: {_text(row, 'second_label')})"


def _adjudication_state(
    rows: Sequence[Mapping[str, str]],
    first_cells: Mapping[tuple[str, str], Mapping[str, str]],
    second_cells: Mapping[tuple[str, str], Mapping[str, str]],
    second: SecondReview,
    merged: set[tuple[str, str]],
    *,
    today: date | None,
) -> dict[str, Any]:
    """Publication gate item 3: whether every disagreement is adjudicated and in the matrix."""
    expected = disagreement_rows(rows, first_cells, second_cells)
    total = len(expected)
    decided = 0
    if second.adjudication is not None:
        # Raises on a decision that the two reviews no longer support, as --disagreements does.
        carried = carry_adjudications(expected, second.adjudication_rows)
        decided = sum(1 for row in carried if (_text(row, "final_label") or "pending") != "pending")
    if total == 0:
        return {
            "status": "not_needed",
            "disagreements": 0,
            "adjudicated": 0,
            "reason": "the two reviews give every double-reviewed cell the same label",
        }
    if second.adjudication is None:
        return {
            "status": "not_given",
            "disagreements": total,
            "adjudicated": None,
            "reason": (
                f"the reviews differ in {_count(total, 'cell')}, and no adjudication file was given "
                "(--adjudication)"
            ),
        }
    if decided < total:
        return {
            "status": "pending",
            "disagreements": total,
            "adjudicated": decided,
            "reason": f"{total - decided} of {total} disagreements are not adjudicated yet",
        }
    final = adjudicated_cells(
        expected,
        second.adjudication_columns,
        second.adjudication_rows,
        today=today,
        not_before=latest_review_date(first_cells, second_cells),
    )
    unmerged = [key for key in final if key not in merged]
    if unmerged:
        return {
            "status": "not_merged",
            "disagreements": total,
            "adjudicated": total,
            "reason": (
                f"{_count(len(unmerged), 'adjudicated label')} {'is' if len(unmerged) == 1 else 'are'} "
                "not in the matrix yet. scripts/build_review_matrix.py --merge-blinded writes adjudicated "
                "labels into the matrix, but it refuses a cell that an earlier merge already filled with "
                "the first review until that cell is set back to pending, with empty reviewer fields, in "
                "human-review-matrix.csv"
            ),
        }
    return {"status": "complete", "disagreements": total, "adjudicated": total, "reason": None}


def _metrics(
    counts: Counts, resampled: Mapping[str, Mapping[str, Any]], *, pending: int = 0, cells: int | None = None
) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for proportion in PROPORTIONS:
        reason = undefined_reason(proportion, counts, pending=pending, cells=cells)
        numerator, denominator = proportion.numerator(counts), proportion.denominator(counts)
        wilson = interval_dict(wilson_interval(numerator, denominator), reason, _DIGITS)
        bootstrap = _bootstrap_record(resampled[proportion.name])
        metrics[proportion.name] = {
            "estimate": None if reason else round(numerator / denominator, _DIGITS),
            "numerator": numerator,
            "denominator": denominator,
            "undefined_reason": reason,
            "wilson": wilson,
            "clopper_pearson": interval_dict(
                clopper_pearson_interval(numerator, denominator), reason, _DIGITS
            ),
            "document_cluster_bootstrap": bootstrap,
            "headline": _headline(wilson, bootstrap),
        }
    metrics["f1"] = _f1(counts, metrics)
    return metrics


def _f1(counts: Counts, metrics: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """F1 as the summary's top-level metrics compute it (METRIC_NOTE)."""
    numerator, denominator = 2 * counts.tp, 2 * counts.tp + counts.fp + counts.fn
    undefined = [name for name in ("precision", "recall") if metrics[name]["estimate"] is None]
    reason = f"{' and '.join(undefined)} undefined, so F1 is null (metric_note)" if undefined else None
    return {
        "estimate": None if reason else _ratio(numerator, denominator),
        "numerator": numerator,
        "denominator": denominator,
        "undefined_reason": reason,
    }


def _bootstrap_record(result: Mapping[str, Any]) -> dict[str, Any]:
    record = rounded(result, _DIGITS)
    fraction = result.get("dropped_fraction")
    record["exceeds_dropped_limit"] = None if fraction is None else fraction > MAX_DROPPED_FRACTION
    return record


def _headline(wilson: Mapping[str, Any], bootstrap: Mapping[str, Any]) -> dict[str, Any]:
    if wilson["lower"] is None:
        return {
            "method": None,
            "label": None,
            "lower": None,
            "upper": None,
            "reason": wilson["undefined_reason"],
        }

    def use_wilson(reason: str) -> dict[str, Any]:
        return {
            "method": "wilson",
            "label": "Wilson",
            "lower": wilson["lower"],
            "upper": wilson["upper"],
            "reason": reason,
        }

    if bootstrap["lower"] is None:
        return use_wilson(f"the document-cluster bootstrap is undefined: {bootstrap['undefined_reason']}")
    if bootstrap["exceeds_dropped_limit"]:
        return use_wilson(
            f"more than {MAX_DROPPED_FRACTION:.0%} of bootstrap replicates were dropped for a zero "
            "denominator, so the bootstrap interval is reported as unstable"
        )
    wilson_width = round(wilson["upper"] - wilson["lower"], _DIGITS)
    bootstrap_width = round(bootstrap["upper"] - bootstrap["lower"], _DIGITS)
    if bootstrap_width > wilson_width:
        return {
            "method": "document_cluster_bootstrap",
            "label": "document-clustered",
            "lower": bootstrap["lower"],
            "upper": bootstrap["upper"],
            "reason": "the document-cluster bootstrap interval is wider than the Wilson interval",
        }
    return use_wilson("the Wilson interval is at least as wide as the document-cluster bootstrap interval")


def _per_rule(cells: Sequence[Cell]) -> list[dict[str, Any]]:
    rules = list(dict.fromkeys(cell.rule for cell in cells))
    return [_count_record([cell for cell in cells if cell.rule == rule], {"rule_id": rule}) for rule in rules]


def _count_record(cells: Sequence[Cell], identity: Mapping[str, Any]) -> dict[str, Any]:
    counts, label_counts = tally(cells)
    record = {**identity, "cells": len(cells), "label_counts": label_counts, **counts.as_dict()}
    if "rule_id" not in identity:
        record["detector_flags"] = None if label_counts["pending"] else sum(cell.flagged for cell in cells)
    return record


def _offeror_analyses(
    primary: Sequence[Cell],
    offerors: Mapping[str, str] | None,
    reason: str | None,
    *,
    replicates: int,
    seed: int,
) -> dict[str, Any]:
    descriptions = {
        "S2a": (
            "S2(a): offeror-cluster percentile bootstrap over the primary set; the documents of one "
            "offeror (source-manifest.json, offeror_or_issuer) are resampled together."
        ),
        "S2b": "S2(b): the primary set with only the lowest-numbered document of each offeror.",
    }
    if offerors is None:
        return {key: {"description": text, "undefined_reason": reason} for key, text in descriptions.items()}
    documents = sorted_documents(primary)
    groups = _offeror_groups(documents, offerors)
    counts, label_counts = tally(primary)
    pending = label_counts["pending"]
    clusters = [tally(_cells_of(primary, group))[0] for group in groups]
    resampled = cluster_bootstrap(
        clusters, replicates=replicates, seed=seed, pending=pending, cells=len(primary)
    )
    s2a_metrics = {}
    for proportion in PROPORTIONS:
        point = undefined_reason(proportion, counts, pending=pending, cells=len(primary))
        s2a_metrics[proportion.name] = {
            "estimate": None
            if point
            else round(proportion.numerator(counts) / proportion.denominator(counts), _DIGITS),
            "undefined_reason": point,
            "offeror_cluster_bootstrap": _bootstrap_record(resampled[proportion.name]),
        }
    kept = [group[0] for group in groups]
    return {
        "S2a": {
            "description": descriptions["S2a"],
            "documents": documents,
            "cells": len(primary),
            "offeror_clusters": len(groups),
            "metrics": s2a_metrics,
        },
        "S2b": analysis_block(
            descriptions["S2b"], _cells_of(primary, kept), replicates=replicates, seed=seed
        ),
    }


def _offeror_map(context: AnalysisContext, cells: Sequence[Cell]) -> tuple[dict[str, str] | None, str | None]:
    """The normalised offeror of each document, checked against the matrix's document hashes."""
    if context.offerors is None:
        return None, context.offerors_reason
    mapping: dict[str, str] = {}
    hashes = {cell.doc: cell.doc_hash for cell in cells}
    for doc in sorted_documents(cells):
        if doc not in context.offerors:
            raise ValueError(f"{doc} is in the matrix but not in the source manifest")
        offeror, manifest_hash = context.offerors[doc]
        if not offeror:
            raise ValueError(f"{doc}: offeror_or_issuer is blank in the source manifest")
        if manifest_hash and hashes[doc] and manifest_hash != hashes[doc]:
            raise ValueError(
                f"{doc}: the matrix's document hash {hashes[doc]} differs from the source manifest's "
                f"({manifest_hash})"
            )
        mapping[doc] = " ".join(offeror.split()).casefold()
    return mapping, None


def _offeror_groups(documents: Sequence[str], offerors: Mapping[str, str]) -> list[list[str]]:
    """Documents grouped by offeror; groups and their members in ascending WP number."""
    groups: dict[str, list[str]] = {}
    for doc in sorted(documents, key=_doc_sort_key):
        groups.setdefault(offerors[doc], []).append(doc)
    return list(groups.values())


def _settings(context: AnalysisContext) -> dict[str, Any]:
    return {
        "definitions": f"analysis-plan.md sections 7 to 10 ({plan_phrase(context.plan)})",
        "analysis_plan": dict(context.plan),
        "evaluable_labels": list(EVALUABLE_CATEGORIES),
        "excluded_labels": list(EXCLUDED_LABELS),
        "confidence_level": CONFIDENCE_LEVEL,
        "wilson_z": WILSON_Z,
        "clopper_pearson": "exact binomial tails, 0.025 in each tail",
        "f1": F1_RULE,
        "bootstrap": {
            "replicates": context.replicates,
            "seed": context.seed,
            "resampling": (
                "percentile bootstrap: each replicate draws as many clusters (documents, or offerors in "
                "S2a) as the set has, with replacement, by random.Random(seed).randrange, and pools their "
                "cells; clusters in ascending order of their lowest WP number; a new generator with the "
                "same seed for every bootstrap"
            ),
            "quantiles": BOOTSTRAP_QUANTILE_METHOD,
            "zero_denominator": "replicates with a zero denominator are dropped and counted per proportion",
        },
        "max_dropped_fraction": MAX_DROPPED_FRACTION,
        "headline_rule": HEADLINE_RULE,
        "primary_exclusions": list(context.primary_exclusions),
        "calibration_rule": (
            "an in-sample calibration document is the document whose every cell carries the note "
            "'calibration' (analysis-plan.md section 4); it is excluded from every analysis set"
        ),
        "sensitivity_base": "S2 to S4 vary the primary set",
        "per_rule_published_for": (
            "the primary set only; S1's per-rule counts go to --internal-out, because S1 and the primary "
            "set can differ by a single document"
        ),
    }


def _excluded_document(
    doc: str, cells: Sequence[Cell], *, complete: bool, plan: Mapping[str, Any]
) -> dict[str, Any]:
    """An excluded document's cells and, once labelling is complete, its share of the detector's flags.

    `detector_flags_total` counts the flags in every cell of the matrix, so the report can say how
    many of the detector's flags fall in the excluded document (analysis-plan.md section 5).
    """
    own = _cells_of(cells, [doc])
    return {
        "study_doc_id": doc,
        "ground": (
            "named with --primary-exclude; the exclusion rule is analysis-plan.md section 5 "
            f"({plan_phrase(plan, short=True)})"
        ),
        "cells": len(own),
        "detector_flags": sum(cell.flagged for cell in own) if complete else None,
        "detector_flags_total": sum(cell.flagged for cell in cells) if complete else None,
        "detector_flags_reason": None if complete else BLIND_WHILE_PENDING,
    }


def _calibration_record(calibration: str | None, cells: Sequence[Cell]) -> dict[str, Any]:
    if calibration is None:
        return {"study_doc_id": None, "cells": 0, "note": "no document is marked 'calibration'"}
    return {
        "study_doc_id": calibration,
        "cells": len(_cells_of(cells, [calibration])),
        "note": (
            "excluded from every analysis set (analysis-plan.md section 4). Section 4 asks for its labels "
            "to be reported separately, while section 10 keeps per-document counts unpublished: its "
            "counts are only in the --internal-out file until the reviewer decides"
        ),
    }


def _cells_of(cells: Sequence[Cell], documents: Sequence[str]) -> list[Cell]:
    wanted = set(documents)
    return [cell for cell in cells if cell.doc in wanted]


def _doc_sort_key(doc: str) -> tuple[float, str]:
    match = _DOC_NUMBER.search(doc)
    return (int(match.group(1)) if match else math.inf, doc)


def _clean(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _read_sheet(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    # utf-8-sig drops the byte-order mark some spreadsheet programs add, as the sheet builder does.
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Summarize a completed MiCAR human-review matrix.")
    parser.add_argument("--matrix", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument(
        "--findings",
        type=Path,
        help="detector output: the matrix must hold exactly its cells and detector statuses, and no "
        "reviewed_at may precede its generated_at date; without it neither is checked",
    )
    group = parser.add_argument_group(
        "analyses of the study's draft analysis plan (sections 7 to 10)",
        "Added to the summary after its other keys, which stay the same. Every option below needs "
        "--analyses, and --analyses needs --findings.",
    )
    group.add_argument(
        "--analyses",
        action="store_true",
        help="also write precision, recall and specificity with Wilson, Clopper-Pearson and "
        "document-cluster bootstrap intervals, the sensitivity analyses and reviewer agreement",
    )
    group.add_argument("--manifest", type=Path, help="source-manifest.json: the offerors for S2")
    group.add_argument(
        "--analysis-plan",
        type=Path,
        help="analysis-plan.md: its adoption status and the detector commit of its Detector row",
    )
    group.add_argument(
        "--primary-exclude",
        action="append",
        default=[],
        metavar="STUDY_DOC_ID",
        help="leave this document out of the primary set but not S1; repeat for more (default: none)",
    )
    group.add_argument(
        "--second-review", type=Path, help="human-review-second.csv: for the agreement of the two reviews"
    )
    group.add_argument(
        "--adjudication",
        type=Path,
        help="human-review-adjudication.csv, with --second-review: for the state of adjudication",
    )
    group.add_argument(
        "--internal-out",
        type=Path,
        help="also write the per-document and per-offeror counts here, for internal checks only; name it "
        "human-review-internal.json under studies/ so that git ignores it",
    )
    group.add_argument(
        "--replicates", type=int, help=f"bootstrap replicates (default {BOOTSTRAP_REPLICATES})"
    )
    group.add_argument("--seed", type=int, help=f"bootstrap seed (default {BOOTSTRAP_SEED})")
    return parser


def _check_analysis_options(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    options = {
        "--manifest": args.manifest,
        "--analysis-plan": args.analysis_plan,
        "--primary-exclude": args.primary_exclude or None,
        "--second-review": args.second_review,
        "--adjudication": args.adjudication,
        "--internal-out": args.internal_out,
        "--replicates": args.replicates,
        "--seed": args.seed,
    }
    given = [flag for flag, value in options.items() if value is not None]
    if given and not args.analyses:
        parser.error(f"{', '.join(given)} {'applies' if len(given) == 1 else 'apply'} only with --analyses")
    if args.analyses and args.findings is None:
        parser.error("--analyses needs --findings, which gives the detector identity and run date")
    if args.adjudication is not None and args.second_review is None:
        parser.error("--adjudication needs --second-review")
    if args.replicates is not None and args.replicates < 1:
        parser.error("--replicates must be at least 1")


def main(argv: list[str] | None = None, *, today: date | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _check_analysis_options(parser, args)
    not_before = None
    expected = None
    if args.findings is not None:
        try:
            findings = json.loads(args.findings.read_text(encoding="utf-8"))
            not_before = detector_run_date(findings)
            expected = detector_cells(findings)
        except (OSError, ValueError) as exc:
            print(f"cannot read {args.findings}: {exc}", file=sys.stderr)
            return 1
    # utf-8-sig drops the byte-order mark some spreadsheet programs add, as the sheet builder does.
    with args.matrix.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if expected is not None:
        mismatches = matrix_mismatches(rows, expected)
        if mismatches:
            print(f"the matrix does not match {args.findings}; nothing written:", file=sys.stderr)
            for mismatch in mismatches:
                print(f"  {mismatch}", file=sys.stderr)
            return 1
    internal = None
    if args.analyses:
        # Everything is read and computed before anything is written, so an error writes nothing.
        try:
            context = load_analysis_context(
                args.findings,
                manifest=args.manifest,
                analysis_plan=args.analysis_plan,
                primary_exclude=args.primary_exclude,
                second_review=args.second_review,
                adjudication=args.adjudication,
                replicates=BOOTSTRAP_REPLICATES if args.replicates is None else args.replicates,
                seed=BOOTSTRAP_SEED if args.seed is None else args.seed,
            )
            summary = summarize_rows(
                rows, today=today or date.today(), not_before=not_before, analyses=context
            )
            internal = internal_detail(rows, context) if args.internal_out is not None else None
        except (OSError, ValueError) as exc:
            print(f"the analyses stopped; nothing written: {exc}", file=sys.stderr)
            return 1
    else:
        summary = summarize_rows(rows, today=today or date.today(), not_before=not_before)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if internal is not None:
        args.internal_out.parent.mkdir(parents=True, exist_ok=True)
        args.internal_out.write_text(
            json.dumps(internal, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    if args.require_complete and not summary["publication_ready"]:
        print(
            f"not publication-ready: {_count(summary['rows_pending'], 'pending row')}, "
            f"{_count(summary['rows_with_protocol_gaps'], 'labelled row')} with protocol gaps",
            file=sys.stderr,
        )
        for gap in summary["protocol_gaps"]:
            print(
                f"  row {gap['row']} {gap['study_doc_id']} {gap['rule_id']}: {'; '.join(gap['problems'])}",
                file=sys.stderr,
            )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
