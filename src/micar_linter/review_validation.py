"""Summarize human validation of the MiCAR white-paper study detector."""

from __future__ import annotations

import argparse
import csv
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
) -> dict[str, Any]:
    """Return confusion-matrix metrics without treating unresolved rows as labels.

    `today` and `not_before` bound `reviewed_at` where given. Neither defaults to a value, so the
    function does not read the clock; the command passes the current date and, with --findings,
    the detector run date.
    """
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

    return {
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
    labels = f"first: {_text(row, 'first_label')}, second: {_text(row, 'second_label')}"
    return {
        "human_label": _text(row, "final_label"),
        "reviewer_id": "+".join(part.strip() for part in _text(row, "adjudicated_by").split("+")),
        "reviewed_at": _text(row, "adjudicated_at"),
        "source_pinpoint": _text(row, "final_pinpoint"),
        "review_note": f"Adjudicated ({labels}): {_text(row, 'adjudication_reason')}",
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
    return parser


def main(argv: list[str] | None = None, *, today: date | None = None) -> int:
    args = build_parser().parse_args(argv)
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
    summary = summarize_rows(rows, today=today or date.today(), not_before=not_before)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
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
