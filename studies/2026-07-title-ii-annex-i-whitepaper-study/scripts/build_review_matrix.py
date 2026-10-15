#!/usr/bin/env python3
"""Build the human-review sheets from the committed detector output.

One row per included document and study rule, in the order of findings-pseudonymous.json.
Rule IDs and annex items come from that file, so the sheets cannot drift from the
detector again. Reviewer cells already filled in either sheet are carried over by
(study_doc_id, rule_id); a filled cell whose key no longer exists, or two filled rows
with the same key, stop the build instead of being dropped.

With --merge-blinded, the reviewer cells of the completed blinded sheet are also copied
into the matrix, which is the step review-protocol.md takes after the independent labels
are recorded. It stops while any blinded cell is pending or lacks a field that publication
gate item 2 or First review steps 6 and 7 of review-protocol.md require, when a review
date lies after today or before the detector run, and when the matrix already holds a
different value for a cell, rather than choosing between them. The merge imports
micar_linter, so run it with `uv run python`. On any refusal nothing is written.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections.abc import Iterable
from datetime import date
from pathlib import Path

STUDY_DIR = Path(__file__).resolve().parents[1]
FINDINGS_NAME = "findings-pseudonymous.json"
MATRIX_NAME = "human-review-matrix.csv"
BLINDED_NAME = "human-review-blinded.csv"

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


def _label(row: dict[str, str]) -> str:
    return (row.get("human_label") or "pending").strip() or "pending"


def _is_filled(row: dict[str, str]) -> bool:
    return _label(row) != "pending" or any((row.get(field) or "").strip() for field in REVIEW_FIELDS[1:])


def _filled_cells(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    if not path.exists():
        return {}
    # utf-8-sig drops the byte-order mark some spreadsheet programs add when saving CSV.
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return filled_cells_from(handle, path.name)


def filled_cells_from(handle: Iterable[str], name: str) -> dict[tuple[str, str], dict[str, str]]:
    reader = csv.DictReader(handle)
    columns = reader.fieldnames or []
    missing = [field for field in ("study_doc_id", "rule_id", *REVIEW_FIELDS) if field not in columns]
    if missing:
        raise ValueError(f"{name} lacks the columns {', '.join(missing)}; save it as comma-separated UTF-8")
    cells: dict[tuple[str, str], dict[str, str]] = {}
    duplicates: list[tuple[str, str]] = []
    for row in reader:
        if not _is_filled(row):
            continue
        key = (row["study_doc_id"], row["rule_id"])
        if key in cells and key not in duplicates:
            duplicates.append(key)
        cells[key] = {field: row.get(field) or "" for field in REVIEW_FIELDS}
    if duplicates:
        listed = ", ".join(f"{doc} {rule}" for doc, rule in duplicates)
        raise ValueError(f"{name} has more than one filled row for: {listed}; keep one row per cell")
    return cells


def merge_blinded_cells(
    keys: Iterable[tuple[str, str]],
    matrix_cells: dict[tuple[str, str], dict[str, str]],
    blinded_cells: dict[tuple[str, str], dict[str, str]],
    *,
    today: date | None = None,
    not_before: date | None = None,
) -> dict[tuple[str, str], dict[str, str]]:
    """Return the matrix reviewer cells with the blinded first-review cells copied in."""
    # Imported here so the plain rebuild still runs without the package; the merge needs `uv run`.
    from micar_linter.review_validation import ALLOWED_LABELS, protocol_problems

    keys = list(keys)
    pending = [key for key in keys if _label(blinded_cells.get(key, {})) == "pending"]
    if pending:
        raise ValueError(
            f"{len(pending)} of {len(keys)} blinded cells are still pending; "
            "finish the first review before merging"
        )
    problems = []
    for key in keys:
        label = _label(blinded_cells[key])
        found = (
            protocol_problems(blinded_cells[key], label, today=today, not_before=not_before)
            if label in ALLOWED_LABELS
            else [f"unsupported human_label {label!r}"]
        )
        problems.extend(f"{key[0]} {key[1]}: {problem}" for problem in found)
    if problems:
        raise ValueError("fix these cells in the blinded sheet first:\n  " + "\n  ".join(problems))
    conflicts = [key for key in keys if key in matrix_cells and matrix_cells[key] != blinded_cells[key]]
    if conflicts:
        listed = ", ".join(f"{doc} {rule}" for doc, rule in conflicts)
        raise ValueError(f"the matrix already holds different reviewer values for: {listed}")
    return {**matrix_cells, **blinded_cells}


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


def main(argv: list[str] | None = None, study_dir: Path = STUDY_DIR, *, today: date | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--merge-blinded",
        action="store_true",
        help="copy the reviewer cells of the completed blinded sheet into the matrix",
    )
    args = parser.parse_args(argv)
    matrix_path = study_dir / MATRIX_NAME
    blinded_path = study_dir / BLINDED_NAME
    payload = json.loads((study_dir / FINDINGS_NAME).read_text(encoding="utf-8"))
    rows = build_rows(payload)
    keys = {(row["study_doc_id"], row["rule_id"]) for row in rows}

    try:
        matrix_cells = _filled_cells(matrix_path)
        blinded_cells = _filled_cells(blinded_path)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    orphaned = sorted((set(matrix_cells) | set(blinded_cells)) - keys)
    if orphaned:
        print("filled reviewer cells have no current document-rule key:", file=sys.stderr)
        for study_doc_id, rule_id in orphaned:
            print(f"  {study_doc_id} {rule_id}", file=sys.stderr)
        return 1
    if args.merge_blinded:
        try:
            # The run date bounds every review date; a findings file without one stops the merge.
            from micar_linter.review_validation import detector_run_date

            matrix_cells = merge_blinded_cells(
                [(row["study_doc_id"], row["rule_id"]) for row in rows],
                matrix_cells,
                blinded_cells,
                today=today or date.today(),
                not_before=detector_run_date(payload),
            )
        except ModuleNotFoundError as exc:
            if exc.name != "micar_linter" and not (exc.name or "").startswith("micar_linter."):
                raise
            print(
                "merge stopped: the merge needs the micar_linter package. Run it from the repository "
                "root with `uv run python studies/2026-07-title-ii-annex-i-whitepaper-study/scripts/"
                "build_review_matrix.py --merge-blinded`.",
                file=sys.stderr,
            )
            return 1
        except ValueError as exc:
            print(f"merge stopped: {exc}", file=sys.stderr)
            return 1

    matrix_rows = [{**row, **matrix_cells.get((row["study_doc_id"], row["rule_id"]), {})} for row in rows]
    blinded_rows = [{**row, **blinded_cells.get((row["study_doc_id"], row["rule_id"]), {})} for row in rows]
    _write(matrix_path, MATRIX_FIELDS, matrix_rows)
    _write(blinded_path, BLINDED_FIELDS, blinded_rows)
    merged = "; merged the blinded labels into the matrix" if args.merge_blinded else ""
    print(
        f"wrote {len(rows)} rows; carried over {len(matrix_cells)} matrix and "
        f"{len(blinded_cells)} blinded reviewer cells{merged}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
