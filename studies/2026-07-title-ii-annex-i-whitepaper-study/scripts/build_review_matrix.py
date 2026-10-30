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

A second review (review-protocol.md, "Second review and adjudication") takes two more steps,
each of which writes only its own file and also needs `uv run python`:

- --second-sheet writes human-review-second.csv once the blinded sheet is complete: every
  flagged cell, every cell the first review labelled uncertain, extraction_failure or
  not_applicable, and a share of the non-flagged cells (--fraction, at least 0.2) drawn by a
  SHA-256 ranking under --seed, all pending and without detector columns. --second-all selects
  every cell. It refuses while the file holds review cells.
- --disagreements writes human-review-adjudication.csv once both sheets are complete: one row
  for each cell whose two labels differ, with both reviews and empty adjudication columns. It
  carries over the decisions already entered and refuses one the two sheets no longer support.

While human-review-second.csv exists, --merge-blinded also requires it complete and, where the
two reviews differ, a complete adjudication file. The matrix then takes the adjudicated label,
adjudicator, date and pinpoint for those cells, with a note naming both reviews' labels, and the
first review for the others. The plain rebuild carries the second sheet's cells over too.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections.abc import Iterable
from datetime import date
from fractions import Fraction
from pathlib import Path

STUDY_DIR = Path(__file__).resolve().parents[1]
FINDINGS_NAME = "findings-pseudonymous.json"
MATRIX_NAME = "human-review-matrix.csv"
BLINDED_NAME = "human-review-blinded.csv"
SECOND_NAME = "human-review-second.csv"
ADJUDICATION_NAME = "human-review-adjudication.csv"
# The seed and the share of non-flagged cells for --second-sheet, as the draft analysis plan
# (section 6) proposes them; the adopted plan fixes both before any label is entered.
DEFAULT_SEED = 20261014
DEFAULT_FRACTION = Fraction(1, 5)

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


def filled_cells_from(
    handle: Iterable[str], name: str, *, pending_too: bool = False
) -> dict[tuple[str, str], dict[str, str]]:
    reader = csv.DictReader(handle)
    columns = reader.fieldnames or []
    missing = [field for field in ("study_doc_id", "rule_id", *REVIEW_FIELDS) if field not in columns]
    if missing:
        raise ValueError(f"{name} lacks the columns {', '.join(missing)}; save it as comma-separated UTF-8")
    cells: dict[tuple[str, str], dict[str, str]] = {}
    duplicates: list[tuple[str, str]] = []
    for row in reader:
        if not (pending_too or _is_filled(row)):
            continue
        key = (row["study_doc_id"], row["rule_id"])
        if key in cells and key not in duplicates:
            duplicates.append(key)
        cells[key] = {field: row.get(field) or "" for field in REVIEW_FIELDS}
    if duplicates:
        listed = ", ".join(f"{doc} {rule}" for doc, rule in duplicates)
        raise ValueError(f"{name} has more than one filled row for: {listed}; keep one row per cell")
    return cells


def _sheet_cells(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    """Return every row of a sheet that holds only some cells, such as the second sheet, by cell."""
    if not path.exists():
        return {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return filled_cells_from(handle, path.name, pending_too=True)


def _adjudication_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def merge_blinded_cells(
    keys: Iterable[tuple[str, str]],
    matrix_cells: dict[tuple[str, str], dict[str, str]],
    blinded_cells: dict[tuple[str, str], dict[str, str]],
    *,
    today: date | None = None,
    not_before: date | None = None,
    adjudicated: dict[tuple[str, str], dict[str, str]] | None = None,
) -> dict[tuple[str, str], dict[str, str]]:
    """Return the matrix reviewer cells with the blinded first-review cells copied in.

    `adjudicated` holds the final cells of a second review's adjudicated disagreements (checked by
    review_validation.adjudicated_cells); they replace the first review's cells before the
    comparison with the matrix, so a repeated merge finds the same values and passes.
    """
    keys = list(keys)
    check_first_review(keys, blinded_cells, today=today, not_before=not_before)
    final = {**blinded_cells, **(adjudicated or {})}
    conflicts = [key for key in keys if key in matrix_cells and matrix_cells[key] != final[key]]
    if conflicts:
        listed = ", ".join(f"{doc} {rule}" for doc, rule in conflicts)
        raise ValueError(f"the matrix already holds different reviewer values for: {listed}")
    return {**matrix_cells, **final}


def check_first_review(
    keys: list[tuple[str, str]],
    blinded_cells: dict[tuple[str, str], dict[str, str]],
    *,
    today: date | None = None,
    not_before: date | None = None,
) -> None:
    """Raise ValueError while a blinded cell is pending or lacks a field the protocol requires."""
    # Imported here so the plain rebuild still runs without the package; the merge needs `uv run`.
    from micar_linter.review_validation import ALLOWED_LABELS, protocol_problems

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


def second_review_cells(
    rows: list[dict[str, str]],
    blinded_cells: dict[tuple[str, str], dict[str, str]],
    second_cells: dict[tuple[str, str], dict[str, str]],
    *,
    today: date,
    not_before: date,
) -> list[dict[str, str]]:
    """Return the current disagreement rows once both reviews are complete; raise ValueError if not."""
    from micar_linter.review_validation import disagreement_rows, second_review_problems

    keys = [(row["study_doc_id"], row["rule_id"]) for row in rows]
    check_first_review(keys, blinded_cells, today=today, not_before=not_before)
    flagged = {(row["study_doc_id"], row["rule_id"]) for row in rows if row["detector_status"] == "flagged"}
    problems = second_review_problems(
        keys, flagged, blinded_cells, second_cells, today=today, not_before=not_before
    )
    if problems:
        raise ValueError(f"fix these in {SECOND_NAME} first:\n  " + "\n  ".join(problems))
    return disagreement_rows(rows, blinded_cells, second_cells)


def adjudicated_final_cells(
    path: Path,
    disagreements: list[dict[str, str]],
    blinded_cells: dict[tuple[str, str], dict[str, str]],
    second_cells: dict[tuple[str, str], dict[str, str]],
    *,
    today: date,
) -> dict[tuple[str, str], dict[str, str]]:
    """Return the adjudicated cells from the adjudication file; raise ValueError if it is not complete."""
    from micar_linter.review_validation import adjudicated_cells, latest_review_date

    if not path.exists():
        if not disagreements:
            return {}
        raise ValueError(
            f"the two reviews differ in {len(disagreements)} cells; write {path.name} with "
            "--disagreements and have every disagreement adjudicated first"
        )
    columns, rows = _adjudication_rows(path)
    return adjudicated_cells(
        disagreements,
        columns,
        rows,
        today=today,
        not_before=latest_review_date(blinded_cells, second_cells),
    )


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
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--merge-blinded",
        action="store_true",
        help="copy the reviewer cells of the completed blinded sheet into the matrix",
    )
    mode.add_argument(
        "--second-sheet",
        action="store_true",
        help=f"write {SECOND_NAME} for a second reviewer once the blinded sheet is complete",
    )
    mode.add_argument(
        "--disagreements",
        action="store_true",
        help=f"write {ADJUDICATION_NAME}, the cells where the two completed reviews differ",
    )
    parser.add_argument("--second-all", action="store_true", help="with --second-sheet: select every cell")
    parser.add_argument(
        "--seed", type=int, help=f"with --second-sheet: seed of the random draw (default {DEFAULT_SEED})"
    )
    parser.add_argument(
        "--fraction",
        type=Fraction,
        help="with --second-sheet: share of the non-flagged cells to draw, from 0.2 to 1 (default 0.2)",
    )
    args = parser.parse_args(argv)
    drawing = args.seed is not None or args.fraction is not None
    if (args.second_all or drawing) and not args.second_sheet:
        parser.error("--second-all, --seed and --fraction apply only with --second-sheet")
    if args.second_all and drawing:
        parser.error("--second-all selects every cell; it takes no --seed or --fraction")
    if args.fraction is not None and not Fraction(1, 5) <= args.fraction <= 1:
        parser.error("--fraction must lie between 0.2 and 1; the protocol asks for at least 20%")
    matrix_path = study_dir / MATRIX_NAME
    blinded_path = study_dir / BLINDED_NAME
    second_path = study_dir / SECOND_NAME
    payload = json.loads((study_dir / FINDINGS_NAME).read_text(encoding="utf-8"))
    rows = build_rows(payload)
    keys = {(row["study_doc_id"], row["rule_id"]) for row in rows}

    try:
        matrix_cells = _filled_cells(matrix_path)
        blinded_cells = _filled_cells(blinded_path)
        second_cells = _sheet_cells(second_path)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    second_filled = {key: cell for key, cell in second_cells.items() if _is_filled(cell)}
    orphaned = sorted((set(matrix_cells) | set(blinded_cells) | set(second_filled)) - keys)
    if orphaned:
        print("filled reviewer cells have no current document-rule key:", file=sys.stderr)
        for study_doc_id, rule_id in orphaned:
            print(f"  {study_doc_id} {rule_id}", file=sys.stderr)
        return 1
    if args.second_sheet or args.disagreements:
        flag = "--second-sheet" if args.second_sheet else "--disagreements"
        try:
            if args.second_sheet:
                return write_second_sheet(study_dir, rows, payload, blinded_cells, second_filled, args, today)
            return write_disagreements(study_dir, rows, payload, blinded_cells, second_cells, today)
        except ModuleNotFoundError as exc:
            if exc.name != "micar_linter" and not (exc.name or "").startswith("micar_linter."):
                raise
            print(
                f"{flag} stopped: it needs the micar_linter package. Run it from the repository root "
                "with `uv run python studies/2026-07-title-ii-annex-i-whitepaper-study/scripts/"
                f"build_review_matrix.py {flag}`.",
                file=sys.stderr,
            )
            return 1
        except ValueError as exc:
            print(f"{flag} stopped: {exc}", file=sys.stderr)
            return 1
    adjudicated_count = None
    if args.merge_blinded:
        try:
            # The run date bounds every review date; a findings file without one stops the merge.
            from micar_linter.review_validation import detector_run_date

            run_date = detector_run_date(payload)
            ordered = [(row["study_doc_id"], row["rule_id"]) for row in rows]
            adjudicated = None
            if second_path.exists():
                # While the second sheet exists, the merge waits for the second review and the
                # adjudication of every disagreement, so the matrix gets the final labels once.
                disagreements = second_review_cells(
                    rows, blinded_cells, second_cells, today=today or date.today(), not_before=run_date
                )
                adjudicated = adjudicated_final_cells(
                    study_dir / ADJUDICATION_NAME,
                    disagreements,
                    blinded_cells,
                    second_cells,
                    today=today or date.today(),
                )
                adjudicated_count = len(adjudicated)
            matrix_cells = merge_blinded_cells(
                ordered,
                matrix_cells,
                blinded_cells,
                today=today or date.today(),
                not_before=run_date,
                adjudicated=adjudicated,
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
    second = ""
    if second_path.exists():
        # The second sheet keeps its own cells; a pending cell that no longer exists is dropped.
        second_rows = [
            {**row, **second_filled.get((row["study_doc_id"], row["rule_id"]), {})}
            for row in rows
            if (row["study_doc_id"], row["rule_id"]) in second_cells
        ]
        _write(second_path, BLINDED_FIELDS, second_rows)
        second = f" and {len(second_filled)} second-review"
    merged = "; merged the blinded labels into the matrix" if args.merge_blinded else ""
    if adjudicated_count is not None:
        merged += f", {adjudicated_count} of them as adjudicated"
    print(
        f"wrote {len(rows)} rows; carried over {len(matrix_cells)} matrix and "
        f"{len(blinded_cells)} blinded{second} reviewer cells{merged}"
    )
    return 0


def write_second_sheet(
    study_dir: Path,
    rows: list[dict[str, str]],
    payload: dict,
    blinded_cells: dict[tuple[str, str], dict[str, str]],
    second_filled: dict[tuple[str, str], dict[str, str]],
    args: argparse.Namespace,
    today: date | None,
) -> int:
    """Write the second reviewer's sheet from the completed first review."""
    from micar_linter.review_validation import detector_run_date, second_review_selection

    if second_filled:
        raise ValueError(
            f"{SECOND_NAME} already holds review cells; nothing written. "
            "It is built once, before the second review starts"
        )
    keys = [(row["study_doc_id"], row["rule_id"]) for row in rows]
    check_first_review(
        keys, blinded_cells, today=today or date.today(), not_before=detector_run_date(payload)
    )
    flagged = {(row["study_doc_id"], row["rule_id"]) for row in rows if row["detector_status"] == "flagged"}
    if args.second_all:
        selected = set(keys)
        described = f"all {len(keys)} cells, for a full second review"
    else:
        seed = DEFAULT_SEED if args.seed is None else args.seed
        fraction = DEFAULT_FRACTION if args.fraction is None else args.fraction
        first_labels = {key: _label(cell) for key, cell in blinded_cells.items()}
        selected = set(second_review_selection(keys, flagged, first_labels, seed=seed, fraction=fraction))
        non_flagged = len(keys) - len(flagged)
        drawn = math.ceil(fraction * non_flagged)
        described = (
            f"{len(selected)} of {len(keys)} cells: the {len(flagged)} flagged cells, {drawn} of the "
            f"{non_flagged} non-flagged cells drawn with seed {seed} and fraction {float(fraction):g}, and "
            f"{len(selected) - len(flagged) - drawn} more that the first review labelled uncertain, "
            "extraction_failure or not_applicable"
        )
    second_rows = [row for row in rows if (row["study_doc_id"], row["rule_id"]) in selected]
    _write(study_dir / SECOND_NAME, BLINDED_FIELDS, second_rows)
    print(f"wrote {SECOND_NAME} with {described}; every cell is pending")
    return 0


def write_disagreements(
    study_dir: Path,
    rows: list[dict[str, str]],
    payload: dict,
    blinded_cells: dict[tuple[str, str], dict[str, str]],
    second_cells: dict[tuple[str, str], dict[str, str]],
    today: date | None,
) -> int:
    """Write the adjudication file: the cells where the two completed reviews differ."""
    from micar_linter.review_validation import DISAGREEMENT_FIELDS, carry_adjudications, detector_run_date

    if not (study_dir / SECOND_NAME).exists():
        raise ValueError(f"there is no {SECOND_NAME}; build it with --second-sheet first")
    disagreements = second_review_cells(
        rows,
        blinded_cells,
        second_cells,
        today=today or date.today(),
        not_before=detector_run_date(payload),
    )
    path = study_dir / ADJUDICATION_NAME
    existing: list[dict[str, str]] = []
    if path.exists():
        columns, existing = _adjudication_rows(path)
        if columns != list(DISAGREEMENT_FIELDS):
            raise ValueError(
                f"{path.name} does not have the columns this command writes; save it as comma-separated "
                "UTF-8 without adding, removing or renaming columns"
            )
    adjudication_rows = carry_adjudications(disagreements, existing)
    _write(path, DISAGREEMENT_FIELDS, adjudication_rows)
    decided = sum(1 for row in adjudication_rows if (row["final_label"].strip() or "pending") != "pending")
    print(
        f"wrote {path.name}: the two reviews differ in {len(adjudication_rows)} of "
        f"{len(second_cells)} second-reviewed cells; {decided} already adjudicated"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
