"""Summarize human validation of the MiCAR white-paper study detector."""

from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

ALLOWED_LABELS = {
    "pending",
    "present",
    "missing",
    "uncertain",
    "extraction_failure",
    "not_applicable",
}
EVALUABLE_LABELS = {"present", "missing"}
ALLOWED_DETECTOR_STATUSES = {"flagged", "not_flagged"}


def summarize_rows(rows: Iterable[Mapping[str, str]]) -> dict[str, Any]:
    """Return confusion-matrix metrics without treating unresolved rows as labels."""
    counts = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    label_counts = {label: 0 for label in sorted(ALLOWED_LABELS)}
    total = 0

    for row_number, row in enumerate(rows, start=2):
        total += 1
        detector_status = (row.get("detector_status") or "").strip()
        human_label = (row.get("human_label") or "pending").strip() or "pending"

        if detector_status not in ALLOWED_DETECTOR_STATUSES:
            raise ValueError(f"row {row_number}: unsupported detector_status {detector_status!r}")
        if human_label not in ALLOWED_LABELS:
            raise ValueError(f"row {row_number}: unsupported human_label {human_label!r}")

        label_counts[human_label] += 1
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
    f1 = (
        None
        if precision is None or recall is None or precision + recall == 0
        else 2 * precision * recall / (precision + recall)
    )
    completed = total - label_counts["pending"]

    return {
        "schema_version": "micar-study-human-validation.v1",
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
        "publication_ready": total > 0 and label_counts["pending"] == 0,
        "metric_note": (
            "Precision, recall, and F1 use only human labels 'present' and 'missing'. "
            "Uncertain, extraction-failure, not-applicable, and pending rows are excluded."
        ),
    }


def _ratio(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else round(numerator / denominator, 6)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Summarize a completed MiCAR human-review matrix.")
    parser.add_argument("--matrix", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--require-complete", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    with args.matrix.open(newline="", encoding="utf-8") as handle:
        summary = summarize_rows(csv.DictReader(handle))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.require_complete and not summary["publication_ready"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
