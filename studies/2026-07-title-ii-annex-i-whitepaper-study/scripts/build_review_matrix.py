#!/usr/bin/env python3
"""Build the human-review sheets from the committed detector output.

One row per included document and study rule, in the order of findings-pseudonymous.json.
Rule IDs and annex items come from that file, so the sheets cannot drift from the
detector again. Reviewer cells already filled in either sheet are carried over by
(study_doc_id, rule_id); a filled cell whose key no longer exists stops the build
instead of being dropped.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

STUDY_DIR = Path(__file__).resolve().parents[1]
FINDINGS = STUDY_DIR / "findings-pseudonymous.json"
MATRIX = STUDY_DIR / "human-review-matrix.csv"
BLINDED = STUDY_DIR / "human-review-blinded.csv"

REVIEW_FIELDS = ("human_label", "reviewer_id", "reviewed_at", "source_pinpoint", "review_note")
MATRIX_FIELDS = (
    "study_doc_id",
    "document_hash_sha256",
    "rule_id",
    "annex_item",
    "detector_status",
    "detector_confidence",
    "detector_context",
    *REVIEW_FIELDS,
)
BLINDED_FIELDS = ("study_doc_id", "document_hash_sha256", "rule_id", "annex_item", *REVIEW_FIELDS)


def _is_filled(row: dict[str, str]) -> bool:
    label = (row.get("human_label") or "pending").strip() or "pending"
    return label != "pending" or any((row.get(field) or "").strip() for field in REVIEW_FIELDS[1:])


def _filled_cells(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as handle:
        return {
            (row["study_doc_id"], row["rule_id"]): {field: row.get(field) or "" for field in REVIEW_FIELDS}
            for row in csv.DictReader(handle)
            if _is_filled(row)
        }


def build_rows(payload: dict) -> list[dict[str, str]]:
    rules = payload["rules"]
    rows: list[dict[str, str]] = []
    for document in payload["results"]:
        flagged = {finding["rule_id"]: finding for finding in document["findings"]}
        for rule in rules:
            finding = flagged.get(rule["rule_id"])
            rows.append(
                {
                    "study_doc_id": document["study_doc_id"],
                    "document_hash_sha256": document["document_hash_sha256"],
                    "rule_id": rule["rule_id"],
                    "annex_item": rule["annex_item"],
                    "detector_status": "flagged" if finding else "not_flagged",
                    "detector_confidence": finding["confidence"] if finding else "",
                    "detector_context": finding["evidence"]["matched_text"] if finding else "",
                    "human_label": "pending",
                    "reviewer_id": "",
                    "reviewed_at": "",
                    "source_pinpoint": "",
                    "review_note": "",
                }
            )
    return rows


def _write(path: Path, fields: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    payload = json.loads(FINDINGS.read_text(encoding="utf-8"))
    rows = build_rows(payload)
    keys = {(row["study_doc_id"], row["rule_id"]) for row in rows}

    matrix_cells = _filled_cells(MATRIX)
    blinded_cells = _filled_cells(BLINDED)
    orphaned = sorted((set(matrix_cells) | set(blinded_cells)) - keys)
    if orphaned:
        print("filled reviewer cells have no current document-rule key:", file=sys.stderr)
        for study_doc_id, rule_id in orphaned:
            print(f"  {study_doc_id} {rule_id}", file=sys.stderr)
        return 1

    matrix_rows = [{**row, **matrix_cells.get((row["study_doc_id"], row["rule_id"]), {})} for row in rows]
    blinded_rows = [{**row, **blinded_cells.get((row["study_doc_id"], row["rule_id"]), {})} for row in rows]
    _write(MATRIX, MATRIX_FIELDS, matrix_rows)
    _write(BLINDED, BLINDED_FIELDS, blinded_rows)
    print(
        f"wrote {len(rows)} rows; carried over {len(matrix_cells)} matrix and "
        f"{len(blinded_cells)} blinded reviewer cells"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
