"""Summarize human validation of the MiCAR white-paper study detector.

``micar-review-summary`` reads the adjudication matrix (the final labels next to the detector
outcomes) and writes ``human-review-summary.json`` in schema v2. The definitions follow the
study's analysis plan (``analysis-plan.md``, sections 7 to 10); the summary records whether the
plan's banner still marks it as a draft or names its adoption (``settings.analysis_plan``):

- analysis sets: the primary set (every processed document except WP-007 and an in-sample
  calibration document) and the full set S1 (with WP-007);
- per set: label counts, TP, FP, FN and TN, precision, recall and specificity, each with a Wilson
  and a Clopper-Pearson interval, a seeded document-cluster bootstrap and the headline interval,
  and F1; per-rule counts for the primary set only;
- sensitivity analyses S2 (offeror-cluster bootstrap, and one document per offeror), S3 and S4
  (``uncertain`` counted as ``missing``, then as ``present``); S5 is recorded as not computed;
- agreement between reviewers when two or more are recorded;
- the detector identity: the findings file's hash, schema, digest and date, and the generating
  commit once ``analysis-plan.md`` names it (step 0.4).

The study directory (default: the matrix's directory) supplies the context:
``human-review-sheets.json`` and the reviewers' sheets, the findings file it names,
``source-manifest.json`` and ``analysis-plan.md``. A context file that is absent leaves the parts
that need it undefined, with the reason; one that contradicts the matrix stops the run.

The per-document and per-offeror count tables, and S1's per-rule table, go only to
``--internal-out``, because the analysis plan keeps per-document counts unpublished (section 10);
git ignores ``human-review-internal*.json`` under ``studies/``. S1's per-rule table is withheld
because S1 and the primary set differ only by WP-007: two per-rule tables would give WP-007's
label and detector outcome for every rule. The sets the plan asks to publish still imply some
document-level counts: S1 minus the primary set gives WP-007's counts, the primary set minus
S2(b) the pooled counts of the documents S2(b) drops, and the top-level label counts minus S1's
the label counts of an in-sample calibration document. While any cell is pending, the summary
carries no detector outcome beyond what the labelled cells imply, so it stays blind for a
reviewer who opens it.

The tool never fills, infers or changes a label.

Exit status: 0 written; 2 written, but ``--require-complete`` was given and a row is pending;
1 input error, nothing written.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from itertools import combinations
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

# The label vocabulary, in the order of the labels table in section 3 of the study codebook. The
# review workbook offers the labels in this order. Tests check the codebook and the Labels table of
# review-protocol.md against it. ALLOWED_LABELS is derived from it, so the vocabulary is defined once.
LABEL_ORDER: tuple[str, ...] = (
    "present",
    "missing",
    "not_applicable",
    "uncertain",
    "extraction_failure",
    "pending",
)
ALLOWED_LABELS = set(LABEL_ORDER)
PENDING_LABEL = "pending"
# The review field that each final label must carry: a source pinpoint for present and missing
# (review-protocol.md, First review, step 5), and an explanation in review_note for the other
# labels (step 7; codebook section 3, "Required fields").
LABEL_REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "present": ("source_pinpoint",),
    "missing": ("source_pinpoint",),
    "not_applicable": ("review_note",),
    "uncertain": ("review_note",),
    "extraction_failure": ("review_note",),
}
EVALUABLE_LABELS = {"present", "missing"}
EXCLUDED_LABELS: tuple[str, ...] = ("not_applicable", "uncertain", "extraction_failure")
ALLOWED_DETECTOR_STATUSES = {"flagged", "not_flagged"}

SUMMARY_SCHEMA = "micar-study-human-validation.v2"
INTERNAL_SCHEMA = "micar-study-human-validation-internal.v1"
# Defined here as well as in review_sheets, which imports this module.
SHEETS_RECORD_FILENAME = "human-review-sheets.json"
SOURCE_MANIFEST_FILENAME = "source-manifest.json"
ANALYSIS_PLAN_FILENAME = "analysis-plan.md"

# analysis-plan.md section 5 (draft): WP-007 is excluded from the primary analysis; S1 includes it.
PRIMARY_EXCLUSIONS: tuple[str, ...] = ("WP-007",)
# analysis-plan.md section 9: B = 10,000 replicates, seed 20261014; and the draft "[10]%" limit
# above which the bootstrap interval is reported as unstable and the Wilson interval is the headline.
BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEED = 20261014
MAX_DROPPED_FRACTION = 0.10
DIGITS = 6
# Agreement over all labels uses the five final labels as categories; over present and missing,
# only those two.
AGREEMENT_CATEGORIES: tuple[str, ...] = tuple(label for label in LABEL_ORDER if label != PENDING_LABEL)
EVALUABLE_CATEGORIES: tuple[str, ...] = ("present", "missing")

# analysis-plan.md section 4: an in-sample calibration document's cells "carry the note
# `calibration`". A document is the calibration document when every one of its cells' notes
# contains the word.
_CALIBRATION_NOTE = re.compile(r"(?<![\w-])calibration(?![\w-])", re.IGNORECASE)
# The Detector row of analysis-plan.md section 2 ends "generating commit: [SHA, see step 0.4]"
# until the reviewer names the commit.
_PLAN_COMMIT = re.compile(
    r"^\|\s*Detector\s*\|.*?generating commit:\s*`?(?P<sha>[0-9a-f]{7,40})`?(?![0-9a-zA-Z])",
    re.MULTILINE,
)
_DOC_NUMBER = re.compile(r"(\d+)")
# The banner of analysis-plan.md: "> **DRAFT, not adopted; ...**" until adoption, then
# "> - Adopted by: <name>, on <YYYY-MM-DD>" and "> - Pre-registration commit: <SHA>".
_PLAN_DRAFT = re.compile(r"^>\s*\*\*DRAFT, not adopted\b", re.MULTILINE)
_PLAN_ADOPTED = re.compile(
    r"^>\s*-\s*Adopted by:\s*(?P<who>[^\n]*?),\s*on\s*(?P<date>[^\s]+)\s*$", re.MULTILINE
)
_PLAN_PREREGISTRATION = re.compile(
    r"^>\s*-\s*Pre-registration commit:\s*`?(?P<sha>[^`\s]+)`?\s*$", re.MULTILINE
)

METRIC_NOTE = (
    "Precision, recall and specificity use only the human labels 'present' and 'missing'. Uncertain, "
    "extraction-failure, not-applicable and pending cells are counted and excluded. Definitions: "
    "analysis-plan.md, sections 7 to 10; settings.analysis_plan records whether the plan is adopted."
)
F1_DEFINITION = (
    "2TP / (2TP + FP + FN), which equals the harmonic mean of precision and recall where both are "
    "defined and positive; undefined only when 2TP + FP + FN = 0"
)
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


@dataclass(frozen=True)
class Cell:
    """One document-rule cell of the matrix."""

    doc: str
    rule: str
    doc_hash: str
    flagged: bool
    label: str
    note: str


@dataclass(frozen=True)
class StudyContext:
    """What the summary reads from the study directory besides the matrix."""

    reviewers: tuple[str, ...] | None = None
    reviewers_reason: str | None = "no study directory was read"
    sheet_labels: Mapping[str, Mapping[tuple[str, str], str]] = field(default_factory=dict)
    detector: Mapping[str, Any] = field(default_factory=lambda: _detector_identity())
    offerors: Mapping[str, tuple[str, str]] | None = None
    offerors_reason: str | None = "no study directory was read"
    plan: Mapping[str, Any] = field(default_factory=lambda: plan_status(None))


def parse_rows(rows: Iterable[Mapping[str, str]]) -> list[Cell]:
    """Read matrix rows into cells. Blank rows are skipped; a blank label counts as pending."""
    cells: list[Cell] = []
    seen: set[tuple[str, str]] = set()
    for row_number, row in enumerate(rows, start=2):
        if not any(_text(value) for value in row.values()):
            continue
        detector_status = _text(row.get("detector_status"))
        human_label = _text(row.get("human_label")) or PENDING_LABEL
        if detector_status not in ALLOWED_DETECTOR_STATUSES:
            raise ValueError(f"row {row_number}: unsupported detector_status {detector_status!r}")
        if human_label not in ALLOWED_LABELS:
            raise ValueError(f"row {row_number}: unsupported human_label {human_label!r}")
        doc, rule = _text(row.get("study_doc_id")), _text(row.get("rule_id"))
        if not doc or not rule:
            raise ValueError(f"row {row_number}: study_doc_id and rule_id are required")
        if (doc, rule) in seen:
            raise ValueError(f"row {row_number}: duplicate cell {doc}, {rule}")
        seen.add((doc, rule))
        cells.append(
            Cell(
                doc=doc,
                rule=rule,
                doc_hash=_text(row.get("document_hash_sha256")).lower(),
                flagged=detector_status == "flagged",
                label=human_label,
                note=_text(row.get("review_note")),
            )
        )
    return cells


def summarize_rows(
    rows: Iterable[Mapping[str, str]],
    context: StudyContext | None = None,
    *,
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    """Return the v2 summary without treating unresolved rows as labels."""
    context = context or StudyContext()
    cells = parse_rows(rows)
    _, label_counts = tally(cells)
    total = len(cells)
    completed = total - label_counts[PENDING_LABEL]
    complete = total > 0 and label_counts[PENDING_LABEL] == 0
    documents = sorted_documents(cells)
    calibration, excluded, full, primary = analysis_sets(cells)
    offerors, offerors_reason = _offeror_map(context, cells)
    bootstrap = {"replicates": replicates, "seed": seed}

    analyses: dict[str, Any] = {
        "primary": analysis_block(
            "Primary: every processed document except WP-007 (analysis-plan.md section 5) and an "
            "in-sample calibration document.",
            primary,
            per_rule=True,
            **bootstrap,
        ),
        # No per-rule table for S1: it differs from the primary set only by WP-007, so the two
        # tables together would give WP-007's label and detector outcome per rule. S1's per-rule
        # table goes to --internal-out.
        "S1": analysis_block(
            "S1, full set: every processed document, including WP-007, except an in-sample "
            "calibration document.",
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
            "S5: the stricter readings recorded in notes under codebook.md P4 and the [OJ check] items."
        ),
        "computed": False,
        "undefined_reason": (
            "neither the codebook nor the analysis plan defines a machine-readable form for the "
            "stricter readings recorded in review notes, so the tool cannot apply them"
        ),
    }

    return {
        "schema_version": SUMMARY_SCHEMA,
        "rows_total": total,
        "rows_completed": completed,
        "rows_pending": label_counts[PENDING_LABEL],
        "completion_rate": _ratio(completed, total),
        "label_counts": label_counts,
        "publication_ready": complete,
        "documents_total": len(documents),
        "rules_per_document": len({cell.rule for cell in cells}),
        "reviewers": list(context.reviewers) if context.reviewers is not None else None,
        "metric_note": METRIC_NOTE,
        "detector": dict(context.detector),
        "settings": _settings(replicates, seed, context.plan),
        "exclusions": {
            "primary": [
                _excluded_document(doc, cells, complete=complete, plan=context.plan) for doc in excluded
            ],
            "calibration_document": _calibration_record(calibration, cells),
        },
        "analyses": analyses,
        "agreement": _agreement(context, full),
    }


def tally(cells: Sequence[Cell], uncertain_as: str | None = None) -> tuple[Counts, dict[str, int]]:
    """Confusion counts and label counts; ``uncertain_as`` recodes 'uncertain' (S3 and S4)."""
    label_counts = {label: 0 for label in LABEL_ORDER}
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
    """Counts, point estimates, intervals and the headline interval for one analysis set."""
    documents = sorted_documents(cells)
    counts, label_counts = tally(cells, uncertain_as)
    pending = label_counts[PENDING_LABEL]
    clusters = [tally(_cells_of(cells, [doc]), uncertain_as)[0] for doc in documents]
    resampled = cluster_bootstrap(
        clusters, replicates=replicates, seed=seed, pending=pending, cells=len(cells)
    )
    block: dict[str, Any] = {
        "description": description,
        "documents": documents,
        "cells": len(cells),
    }
    if uncertain_as:
        block["uncertain_counted_as"] = uncertain_as
    block.update(
        {
            "label_counts": label_counts,
            "evaluable_cells": counts.tp + counts.fp + counts.fn + counts.tn,
            "excluded_cells": sum(label_counts[label] for label in EXCLUDED_LABELS),
            "pending_cells": pending,
            "confusion_matrix": counts.as_dict(),
            "metrics": _metrics(
                counts, resampled, "document_cluster_bootstrap", pending=pending, cells=len(cells)
            ),
        }
    )
    if per_rule:
        block["per_rule"] = _per_rule(cells)
    return block


def analysis_sets(cells: Sequence[Cell]) -> tuple[str | None, list[str], list[Cell], list[Cell]]:
    """The calibration document, the primary exclusions, and the cells of S1 and of the primary set."""
    calibration = calibration_document(cells)
    documents = sorted_documents(cells)
    excluded = [doc for doc in PRIMARY_EXCLUSIONS if doc in documents and doc != calibration]
    full = [cell for cell in cells if cell.doc != calibration]
    primary = [cell for cell in full if cell.doc not in excluded]
    return calibration, excluded, full, primary


def calibration_document(cells: Sequence[Cell]) -> str | None:
    """The in-sample calibration document: every one of its cells' notes says 'calibration'.

    A document with the word in some but not all of its notes, or more than one such document,
    stops the run, because the primary set would then be ambiguous.
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


def internal_detail(rows: Iterable[Mapping[str, str]], context: StudyContext | None = None) -> dict[str, Any]:
    """Per-document, per-offeror and S1 per-rule counts for internal quality checks; never published."""
    context = context or StudyContext()
    cells = parse_rows(rows)
    offerors, offerors_reason = _offeror_map(context, cells)
    documents = sorted_documents(cells)
    calibration, _, full, _ = analysis_sets(cells)
    detail: dict[str, Any] = {
        "schema_version": INTERNAL_SCHEMA,
        "notice": (
            "Internal quality check (analysis-plan.md section 10). Per-document and per-offeror "
            "counts are not published, or only without WP identifiers, unless the conflicts check "
            "and the legal review under review-protocol.md are complete and the reviewer decides "
            "otherwise. S1's per-rule counts are kept here because, next to the published per-rule "
            "counts of the primary set, they would give WP-007's label and detector outcome per "
            "rule. Do not commit this file."
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


def load_context(study_dir: Path) -> StudyContext:
    """Read the reviewers' sheets, the detector identity and the offeror mapping of a study."""
    record_path = study_dir / SHEETS_RECORD_FILENAME
    reviewers: tuple[str, ...] | None = None
    reviewers_reason: str | None = None
    sheet_labels: dict[str, dict[tuple[str, str], str]] = {}
    findings: Mapping[str, Any] | None = None
    if record_path.exists():
        record = json.loads(record_path.read_text(encoding="utf-8"))
        if not isinstance(record, dict):
            raise ValueError(f"{SHEETS_RECORD_FILENAME} is not a generation record")
        sheets = record.get("sheets") or []
        reviewers = tuple(str(sheet.get("reviewer_id", "")) for sheet in sheets)
        for sheet in sheets:
            sheet_labels[str(sheet.get("reviewer_id", ""))] = _sheet_labels(
                study_dir / str(sheet.get("file"))
            )
        findings_name = str(record.get("findings_file") or "")
        raw = (study_dir / findings_name).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != record.get("findings_sha256"):
            raise ValueError(
                f"{findings_name} hashes to {digest}, but {SHEETS_RECORD_FILENAME} records "
                f"{record.get('findings_sha256')}"
            )
        findings = json.loads(raw.decode("utf-8"))
        detector = _detector_identity(findings_name, digest, findings, study_dir)
    else:
        reviewers_reason = f"no {SHEETS_RECORD_FILENAME} in the study directory"
        detector = _detector_identity(reason=f"no {SHEETS_RECORD_FILENAME} in the study directory")

    offerors: dict[str, tuple[str, str]] | None = None
    offerors_reason: str | None = None
    manifest_path = study_dir / SOURCE_MANIFEST_FILENAME
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        offerors = {
            str(entry.get("study_doc_id", "")): (
                _text(entry.get("offeror_or_issuer")),
                _text(entry.get("document_hash_sha256")).lower(),
            )
            for entry in manifest.get("entries", [])
        }
    else:
        offerors_reason = f"no {SOURCE_MANIFEST_FILENAME} in the study directory, so offerors are unknown"
    plan_path = study_dir / ANALYSIS_PLAN_FILENAME
    plan = (
        plan_status(plan_path.read_text(encoding="utf-8"))
        if plan_path.exists()
        else plan_status(None, f"no {ANALYSIS_PLAN_FILENAME} in the study directory")
    )
    return StudyContext(
        reviewers=reviewers,
        reviewers_reason=reviewers_reason,
        sheet_labels=sheet_labels,
        detector=detector,
        offerors=offerors,
        offerors_reason=offerors_reason,
        plan=plan,
    )


def plan_status(text: str | None, reason: str = "no study directory was read") -> dict[str, Any]:
    """Whether ``analysis-plan.md`` is still a draft or names its adoption, read from its banner.

    ``draft`` while the banner says "DRAFT, not adopted" and the "Adopted by" line is still a
    placeholder; ``adopted`` once the banner is gone and that line names a reviewer and an ISO date,
    with the pre-registration commit when the banner names one; otherwise ``unknown`` with the reason.
    """
    record: dict[str, Any] = {
        "file": ANALYSIS_PLAN_FILENAME,
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
    banner = f"the banner of {ANALYSIS_PLAN_FILENAME} says 'DRAFT, not adopted'"
    if draft and not filled:
        return {**record, "status": "draft", "reason": banner}
    if draft:
        return {**record, "reason": f"{banner}, but its 'Adopted by' line is filled in"}
    if not filled:
        return {
            **record,
            "reason": (
                f"{ANALYSIS_PLAN_FILENAME} has neither the 'DRAFT, not adopted' banner nor an 'Adopted by' "
                "line with a reviewer and an ISO date"
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
        named = f"pre-registration commit {commit}" if commit else "pre-registration commit not yet named"
        return f"adopted on {plan['adopted_on']}; {named}"
    return "adoption status unknown" if short else f"adoption status unknown: {plan.get('reason')}"


def read_matrix(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def summarize_matrix(matrix: Path, study_dir: Path | None = None) -> dict[str, Any]:
    """The summary of a matrix file, with the context of its study directory."""
    return summarize_rows(read_matrix(matrix), load_context(study_dir or matrix.parent))


def summary_json(summary: Mapping[str, Any]) -> str:
    """The summary as written to disk. NaN cannot occur; ``allow_nan=False`` enforces it."""
    return json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False) + "\n"


def _metrics(
    counts: Counts,
    resampled: Mapping[str, Mapping[str, Any]],
    bootstrap_key: str,
    *,
    pending: int = 0,
    cells: int | None = None,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for proportion in PROPORTIONS:
        reason = undefined_reason(proportion, counts, pending=pending, cells=cells)
        numerator, denominator = proportion.numerator(counts), proportion.denominator(counts)
        wilson = interval_dict(wilson_interval(numerator, denominator), reason, DIGITS)
        bootstrap = _bootstrap_record(resampled[proportion.name])
        metrics[proportion.name] = {
            "estimate": None if reason else round(numerator / denominator, DIGITS),
            "numerator": numerator,
            "denominator": denominator,
            "undefined_reason": reason,
            "wilson": wilson,
            "clopper_pearson": interval_dict(
                clopper_pearson_interval(numerator, denominator), reason, DIGITS
            ),
            bootstrap_key: bootstrap,
            "headline": _headline(wilson, bootstrap),
        }
    metrics["f1"] = _f1(counts, pending=pending, cells=cells)
    return metrics


def _f1(counts: Counts, *, pending: int = 0, cells: int | None = None) -> dict[str, Any]:
    """F1 in its closed form (``F1_DEFINITION``): undefined only when its denominator is 0."""
    numerator, denominator = 2 * counts.tp, 2 * counts.tp + counts.fp + counts.fn
    reason = None
    if denominator == 0 and pending:
        of_cells = f" of {cells}" if cells is not None else ""
        reason = (
            "2TP + FP + FN = 0 so far: no cell is labelled missing and no detector-flagged cell is "
            f"labelled present yet ({pending}{of_cells} cells in this set pending)"
        )
    elif denominator == 0:
        reason = (
            "2TP + FP + FN = 0: no cell is labelled missing and no detector-flagged cell is labelled present"
        )
    return {
        "estimate": None if reason else round(numerator / denominator, DIGITS),
        "numerator": numerator,
        "denominator": denominator,
        "undefined_reason": reason,
    }


def _bootstrap_record(result: Mapping[str, Any]) -> dict[str, Any]:
    record = rounded(result, DIGITS)
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
    wilson_width = round(wilson["upper"] - wilson["lower"], DIGITS)
    bootstrap_width = round(bootstrap["upper"] - bootstrap["lower"], DIGITS)
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
        pending = label_counts[PENDING_LABEL]
        record["detector_flags"] = None if pending else sum(cell.flagged for cell in cells)
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
    pending = label_counts[PENDING_LABEL]
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
            else round(proportion.numerator(counts) / proportion.denominator(counts), DIGITS),
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


def _offeror_map(context: StudyContext, cells: Sequence[Cell]) -> tuple[dict[str, str] | None, str | None]:
    """Normalised offeror per document, checked against the matrix's document hashes."""
    if context.offerors is None:
        return None, context.offerors_reason
    mapping: dict[str, str] = {}
    hashes = {cell.doc: cell.doc_hash for cell in cells}
    for doc in sorted_documents(cells):
        if doc not in context.offerors:
            raise ValueError(f"{doc} is in the matrix but not in {SOURCE_MANIFEST_FILENAME}")
        offeror, manifest_hash = context.offerors[doc]
        if not offeror:
            raise ValueError(f"{doc}: offeror_or_issuer is blank in {SOURCE_MANIFEST_FILENAME}")
        if manifest_hash and hashes[doc] and manifest_hash != hashes[doc]:
            raise ValueError(
                f"{doc}: the matrix's document hash {hashes[doc]} differs from {SOURCE_MANIFEST_FILENAME} "
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


def _agreement(context: StudyContext, full: Sequence[Cell]) -> dict[str, Any]:
    reviewers = context.reviewers
    base: dict[str, Any] = {
        "reviewers": list(reviewers) if reviewers is not None else None,
        "double_reviewed": bool(reviewers) and len(reviewers) >= 2,
    }
    if reviewers is None:
        return {**base, "status": "unknown", "reason": context.reviewers_reason, "pairs": []}
    if len(reviewers) < 2:
        return {
            **base,
            "status": "single_reviewer",
            "reason": (
                f"one reviewer ({', '.join(reviewers) or 'none'}) is recorded in {SHEETS_RECORD_FILENAME}: "
                "the labels are single-reviewed and no agreement is computed"
            ),
            "pairs": [],
        }
    keys = [(cell.doc, cell.rule) for cell in full]
    if any(cell.label == PENDING_LABEL for cell in full):
        # The reviews are compared only after both are complete and merged (review-protocol.md),
        # so the summary does not change while labelled sheets are committed before the merge.
        return {
            **base,
            "status": "awaiting_merge",
            "reason": "computed once the merged matrix has no pending cell",
            "pairs": [],
        }
    for reviewer in reviewers:
        missing = [key for key in keys if key not in context.sheet_labels.get(reviewer, {})]
        if missing:
            raise ValueError(
                f"human-review-{reviewer}.csv lacks {len(missing)} matrix cells, for example {missing[0]}"
            )
    pending = {
        reviewer: sum(context.sheet_labels[reviewer][key] == PENDING_LABEL for key in keys)
        for reviewer in reviewers
    }
    scope = {
        "set": "S1, the full set: every processed document except an in-sample calibration document",
        "documents": sorted_documents(full),
        "cells": len(keys),
    }
    if any(pending.values()):
        open_cells = ", ".join(f"{reviewer} {count}" for reviewer, count in pending.items() if count)
        return {
            **base,
            **scope,
            "status": "incomplete",
            "reason": (
                f"agreement is computed once every reviewer's sheet is complete; pending cells: {open_cells}"
            ),
            "pairs": [],
        }
    pairs = []
    for first, second in combinations(reviewers, 2):
        labels = [(context.sheet_labels[first][key], context.sheet_labels[second][key]) for key in keys]
        evaluable = [pair for pair in labels if pair[0] in EVALUABLE_LABELS and pair[1] in EVALUABLE_LABELS]
        pairs.append(
            {
                "reviewers": [first, second],
                "cells": len(labels),
                "disagreements": sum(a != b for a, b in labels),
                "all_labels": rounded(agreement(labels, AGREEMENT_CATEGORIES), DIGITS),
                "present_missing": {
                    "scope": "cells that both reviewers labelled present or missing",
                    **rounded(agreement(evaluable, EVALUABLE_CATEGORIES), DIGITS),
                },
            }
        )
    return {**base, **scope, "status": "computed", "reason": None, "pairs": pairs}


def _settings(replicates: int, seed: int, plan: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "definitions": f"analysis-plan.md sections 7 to 10 ({plan_phrase(plan)})",
        "analysis_plan": dict(plan),
        "evaluable_labels": sorted(EVALUABLE_LABELS, key=LABEL_ORDER.index),
        "excluded_labels": list(EXCLUDED_LABELS),
        "confidence_level": CONFIDENCE_LEVEL,
        "wilson_z": WILSON_Z,
        "clopper_pearson": "exact binomial tails, 0.025 in each tail",
        "f1": F1_DEFINITION,
        "bootstrap": {
            "replicates": replicates,
            "seed": seed,
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
        "max_dropped_fraction_status": "draft value '[10]%' of analysis-plan.md section 9",
        "headline_rule": HEADLINE_RULE,
        "primary_exclusions": list(PRIMARY_EXCLUSIONS),
        "calibration_rule": (
            "an in-sample calibration document is the document whose every cell carries the note "
            "'calibration' (analysis-plan.md section 4); it is excluded from every analysis set"
        ),
        "sensitivity_base": "S2 to S4 vary the primary set",
        "per_rule_published_for": (
            "the primary set only; S1's per-rule counts go to --internal-out, because S1 differs from "
            "the primary set only by WP-007"
        ),
    }


def _excluded_document(
    doc: str, cells: Sequence[Cell], *, complete: bool, plan: Mapping[str, Any]
) -> dict[str, Any]:
    """An excluded document's cells and, once labelling is complete, its share of the detector's flags.

    ``detector_flags_total`` counts the flags in every cell of the matrix, so the report can say
    "11 of the detector's 21 flags" (analysis-plan.md section 5).
    """
    own = _cells_of(cells, [doc])
    return {
        "study_doc_id": doc,
        "ground": f"analysis-plan.md section 5 ({plan_phrase(plan, short=True)})",
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


def _detector_identity(
    findings_name: str | None = None,
    findings_sha256: str | None = None,
    findings: Mapping[str, Any] | None = None,
    study_dir: Path | None = None,
    *,
    reason: str = "no study directory was read",
) -> dict[str, Any]:
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
        {
            "findings_schema": findings.get("schema"),
            "findings_digest": findings.get("digest"),
            "findings_generated_at": findings.get("generated_at"),
        }
    )
    recorded = _text(findings.get("detector_commit")).lower()
    if re.fullmatch(r"[0-9a-f]{7,40}", recorded):
        identity.update(
            commit=recorded,
            commit_source=f"{findings_name}, detector_commit",
            commit_status="recorded in the findings file",
        )
        return identity
    plan_path = (study_dir or Path()) / ANALYSIS_PLAN_FILENAME
    if not plan_path.exists():
        identity["commit_status"] = (
            f"not recorded: {findings_name} names no detector commit, and the study directory has no "
            f"{ANALYSIS_PLAN_FILENAME}"
        )
        return identity
    match = _PLAN_COMMIT.search(plan_path.read_text(encoding="utf-8"))
    if match is None:
        identity["commit_status"] = (
            f"not recorded: {findings_name} names no detector commit, and the Detector row of "
            f"{ANALYSIS_PLAN_FILENAME} section 2 names no generating commit yet (step 0.4)"
        )
        return identity
    identity.update(
        commit=match.group("sha"),
        commit_source=f"{ANALYSIS_PLAN_FILENAME}, section 2, Detector row",
        commit_status=f"named in {ANALYSIS_PLAN_FILENAME} (step 0.4)",
    )
    return identity


def _sheet_labels(path: Path) -> dict[tuple[str, str], str]:
    labels: dict[tuple[str, str], str] = {}
    for row_number, row in enumerate(read_matrix(path), start=2):
        label = _text(row.get("human_label")) or PENDING_LABEL
        if label not in ALLOWED_LABELS:
            raise ValueError(f"{path.name} row {row_number}: unsupported human_label {label!r}")
        labels[(_text(row.get("study_doc_id")), _text(row.get("rule_id")))] = label
    return labels


def _cells_of(cells: Sequence[Cell], documents: Sequence[str]) -> list[Cell]:
    wanted = set(documents)
    return [cell for cell in cells if cell.doc in wanted]


def _doc_sort_key(doc: str) -> tuple[float, str]:
    match = _DOC_NUMBER.search(doc)
    return (int(match.group(1)) if match else math.inf, doc)


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _ratio(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else round(numerator / denominator, DIGITS)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="micar-review-summary",
        description=(
            "Summarize a MiCAR human-review matrix: completion, precision and recall with Wilson, "
            "Clopper-Pearson and seeded cluster-bootstrap intervals, sensitivity analyses and "
            "reviewer agreement, as defined in the study's analysis plan."
        ),
    )
    parser.add_argument("--matrix", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument(
        "--study-dir",
        type=Path,
        default=None,
        help="study directory with the sheets, findings file and manifests (default: the matrix's directory)",
    )
    parser.add_argument(
        "--internal-out",
        type=Path,
        default=None,
        help=(
            "also write per-document and per-offeror counts here, for internal checks only; name it "
            "human-review-internal.json under studies/ so that git ignores it"
        ),
    )
    parser.add_argument("--require-complete", action="store_true", help="exit 2 while any row is pending")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        rows = read_matrix(args.matrix)
        context = load_context(args.study_dir or args.matrix.parent)
        summary = summarize_rows(rows, context)
        internal = internal_detail(rows, context) if args.internal_out else None
    except (OSError, ValueError) as exc:
        print(f"micar-review-summary: {exc}", file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(summary_json(summary), encoding="utf-8")
    if internal is not None:
        args.internal_out.parent.mkdir(parents=True, exist_ok=True)
        args.internal_out.write_text(summary_json(internal), encoding="utf-8")
    if args.require_complete and not summary["publication_ready"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
