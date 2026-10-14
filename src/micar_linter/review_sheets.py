"""Generate the blinded human-review sheets and the adjudication matrix for the Title II study.

Every sheet is rebuilt from the committed findings file. Rule IDs, Annex labels and rule
labels come from ``STUDY_RULES`` in ``micar_linter.batch``, so the review sheets cannot drift
from the detector's canonical rule set.

Two kinds of file are written:

- one blinded sheet per reviewer (``human-review-<reviewer_id>.csv``). It carries no detector
  outcome, and its rows are shuffled within each document by a recorded seed;
- the matrix (``human-review-matrix.csv``) in canonical order, with the detector outcomes, for
  adjudication and metric calculation after the independent labels are recorded.

Every human-review field is written as ``pending`` or blank. The generator never fills a label.

Once reviewers start labelling, the generated columns (cell identity and, in the matrix, the
detector outcome) and the row order stay fixed, while the review columns fill up. The check and
the writer therefore compare only the generated columns:

- ``--check`` passes for a sheet with labels as long as its generated columns and row order match
  the generator and its review columns are well formed;
- a sheet that holds review content is kept as it is when its generated columns already match,
  and the run is refused (exit 3) when they would change, unless ``--force`` is given.

Reviewers and the seed already recorded in ``human-review-sheets.json`` are kept on every run, so
``--reviewer r2`` adds a second reviewer without dropping ``r1``.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from micar_linter.batch import STUDY_RULES, StudyRule
from micar_linter.review_validation import ALLOWED_LABELS

SHEETS_SCHEMA = "micar-study-review-sheets.v1"
DEFAULT_SEED = 20261014
DEFAULT_REVIEWERS: tuple[str, ...] = ("r1",)
MATRIX_FILENAME = "human-review-matrix.csv"
SHEETS_RECORD_FILENAME = "human-review-sheets.json"
PENDING_LABEL = "pending"

REVIEW_FIELDS: tuple[str, ...] = (
    "human_label",
    "reviewer_id",
    "reviewed_at",
    "source_pinpoint",
    "review_note",
)
DETECTOR_FIELDS: tuple[str, ...] = ("detector_status", "detector_confidence", "detector_context")
CELL_FIELDS: tuple[str, ...] = (
    "study_doc_id",
    "document_hash_sha256",
    "rule_id",
    "annex_item",
    "rule_label",
    "requirement",
)
BLINDED_FIELDS: tuple[str, ...] = CELL_FIELDS + REVIEW_FIELDS
MATRIX_FIELDS: tuple[str, ...] = CELL_FIELDS + DETECTOR_FIELDS + REVIEW_FIELDS

# The element each cell asks about, in neutral wording for the reviewer. The wording follows
# MiCAR Article 6 and Annex I as encoded in this repository (STUDY_RULES, rules/common.py and
# the Article 6 statement fields of examples/numbered-other-draft.xhtml). It has not been
# checked against the Official Journal text; codebook.md carries the decision rules and the
# items the reviewer verifies before adopting the codebook. The wording describes the legal
# element only and says nothing about how the detector searches for it.
REVIEW_REQUIREMENTS: dict[str, str] = {
    "ANNEX_I_PART_A_02_LEGAL_FORM": ("Legal form of the offeror or person seeking admission to trading."),
    "ANNEX_I_PART_A_03_REGISTERED_ADDRESS": (
        "Registered address of the offeror or person seeking admission to trading; for the head "
        "office, see codebook 5.2."
    ),
    "ANNEX_I_PART_A_04_REGISTRATION_DATE": (
        "Date of registration (incorporation or establishment) of the offeror or person seeking "
        "admission to trading."
    ),
    "ANNEX_I_PART_A_05_LEI_OR_IDENTIFIER": (
        "Legal entity identifier (LEI) or another identifier of the offeror or person seeking "
        "admission to trading."
    ),
    "ANNEX_I_PART_A_06_CONTACT_PHONE_EMAIL": (
        "Both a contact telephone number and an email address of the offeror or person seeking "
        "admission to trading."
    ),
    "ANNEX_I_PART_A_06_CONTACT_RESPONSE_PERIOD": (
        "Period of days within which an investor contacting the offeror or person seeking "
        "admission to trading will receive an answer."
    ),
    "ANNEX_I_PART_A_08_MANAGEMENT_BODY": (
        "Identity and functions of the members of the management body of the offeror or person "
        "seeking admission to trading."
    ),
    "ANNEX_I_PART_E_18_CONFLICTS_OF_INTEREST": (
        "Disclosure of conflicts of interest relating to the offer to the public or the admission to trading."
    ),
    "ANNEX_I_PART_A_10_FINANCIAL_CONDITION": (
        "Financial condition of the offeror or person seeking admission to trading."
    ),
    "ANNEX_I_PART_D_01_ASSET_NAME_ABBREVIATION": ("Name of the crypto-asset and its abbreviation or ticker."),
    "ANNEX_I_PART_D_03_IMPLEMENTATION_PERSONS": (
        "Natural or legal persons involved in the implementation of the crypto-asset project."
    ),
    "ANNEX_I_PART_F_02_CHARACTERISTICS_FUNCTIONALITY": (
        "Characteristics and functionality of the crypto-asset."
    ),
    "ARTICLE_6_05_MANDATORY_WARNINGS": (
        "Art. 6(5) statements: (a) may lose its value in part or in full; (b) may not always be "
        "transferable; (c) may not be liquid; (d) where relevant, see codebook; (e) not covered by "
        "investor compensation schemes under Directive 97/9/EC; (f) not covered by deposit "
        "guarantee schemes under Directive 2014/49/EU."
    ),
    "ARTICLE_6_06_MANAGEMENT_BODY_STATEMENT": (
        "Art. 6(6) statement of the management body that the white paper complies with Title II "
        "and that, to the best of its knowledge, the information is fair, clear and not "
        "misleading and the white paper makes no omission likely to affect its import."
    ),
    "ARTICLE_6_07_SUMMARY": (
        "Art. 6(7) summary giving key information about the offer to the public or the admission "
        "to trading; see codebook for the summary warning."
    ),
}

ROW_ORDER_POLICY = (
    "Documents appear in the order of the findings file. Within each document, rows are sorted "
    "by the SHA-256 hex digest of '<seed>|<reviewer_id>|<study_doc_id>|<rule_id>'. The order "
    "depends only on those four values, never on detector output. The matrix keeps the "
    "canonical STUDY_RULES order."
)
REQUIREMENT_TEXT_STATUS = (
    "Draft wording derived from MiCAR Article 6 and Annex I as encoded in this repository; "
    "not verified against the Official Journal text. codebook.md governs."
)

_REVIEWER_ID = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")
_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")


class ReviewContentError(RuntimeError):
    """Raised when a target sheet already holds review content."""


def build_cells(
    findings: Mapping[str, Any],
    rules: Sequence[StudyRule] = STUDY_RULES,
) -> list[dict[str, str]]:
    """Return one cell per processed document and canonical rule, in canonical order."""
    canonical = {rule.rule_id: rule for rule in rules}
    _check_findings_rules(findings, canonical)

    cells: list[dict[str, str]] = []
    seen_documents: set[str] = set()
    for result in findings.get("results", []):
        doc_id = str(result.get("study_doc_id", "")).strip()
        doc_hash = str(result.get("document_hash_sha256", "")).strip().lower()
        if not doc_id:
            raise ValueError("findings result without study_doc_id")
        if doc_id in seen_documents:
            raise ValueError(f"{doc_id}: duplicate result in findings file")
        seen_documents.add(doc_id)
        if not _SHA256_HEX.match(doc_hash):
            raise ValueError(f"{doc_id}: document_hash_sha256 is not a SHA-256 hex digest")
        rules_checked = result.get("rules_checked")
        if rules_checked is not None and int(rules_checked) != len(rules):
            raise ValueError(
                f"{doc_id}: findings checked {rules_checked} rules, STUDY_RULES has {len(rules)}"
            )

        flagged: dict[str, Mapping[str, Any]] = {}
        for finding in result.get("findings", []):
            rule_id = str(finding.get("rule_id", ""))
            if rule_id not in canonical:
                raise ValueError(f"{doc_id}: finding for unknown rule {rule_id!r}")
            if rule_id in flagged:
                raise ValueError(f"{doc_id}: duplicate finding for {rule_id}")
            if finding.get("annex_item") != canonical[rule_id].annex_item:
                raise ValueError(
                    f"{doc_id}: finding annex_item {finding.get('annex_item')!r} differs from "
                    f"STUDY_RULES {canonical[rule_id].annex_item!r} for {rule_id}"
                )
            flagged[rule_id] = finding

        for rule in rules:
            finding = flagged.get(rule.rule_id)
            evidence = finding.get("evidence", {}) if finding else {}
            cells.append(
                {
                    "study_doc_id": doc_id,
                    "document_hash_sha256": doc_hash,
                    "rule_id": rule.rule_id,
                    "annex_item": rule.annex_item,
                    "rule_label": rule.label,
                    "requirement": requirement_for(rule.rule_id),
                    "detector_status": "flagged" if finding else "not_flagged",
                    "detector_confidence": str(finding.get("confidence", "")) if finding else "",
                    "detector_context": str(evidence.get("matched_text", "")) if finding else "",
                }
            )
    if not cells:
        raise ValueError("findings file contains no processed documents")
    return cells


def requirement_for(rule_id: str) -> str:
    try:
        return REVIEW_REQUIREMENTS[rule_id]
    except KeyError as exc:
        raise ValueError(f"no review requirement text for {rule_id}") from exc


def blinded_rows(cells: Sequence[Mapping[str, str]], reviewer_id: str, seed: int) -> list[dict[str, str]]:
    """Rows for one reviewer: no detector fields, shuffled within each document."""
    _check_reviewer_id(reviewer_id)
    by_document: dict[str, list[Mapping[str, str]]] = {}
    for cell in cells:
        by_document.setdefault(cell["study_doc_id"], []).append(cell)

    rows: list[dict[str, str]] = []
    for doc_id, doc_cells in by_document.items():
        ordered = sorted(doc_cells, key=lambda cell: order_key(seed, reviewer_id, doc_id, cell["rule_id"]))
        for cell in ordered:
            row = {field: cell[field] for field in CELL_FIELDS}
            row.update(_empty_review_fields())
            rows.append(row)
    return rows


def matrix_rows(cells: Sequence[Mapping[str, str]]) -> list[dict[str, str]]:
    """Rows for the adjudication matrix in canonical order, with detector outcomes."""
    rows: list[dict[str, str]] = []
    for cell in cells:
        row = {field: cell[field] for field in CELL_FIELDS + DETECTOR_FIELDS}
        row.update(_empty_review_fields())
        rows.append(row)
    return rows


def order_key(seed: int, reviewer_id: str, doc_id: str, rule_id: str) -> str:
    return hashlib.sha256(f"{seed}|{reviewer_id}|{doc_id}|{rule_id}".encode()).hexdigest()


def render_csv(rows: Iterable[Mapping[str, str]], fields: Sequence[str]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(fields), lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field, "") for field in fields})
    return buffer.getvalue()


def sheet_filename(reviewer_id: str) -> str:
    _check_reviewer_id(reviewer_id)
    return f"human-review-{reviewer_id}.csv"


def build_review_sheets(
    findings: Mapping[str, Any],
    *,
    findings_sha256: str,
    findings_name: str = "findings-pseudonymous.json",
    reviewers: Sequence[str] = DEFAULT_REVIEWERS,
    seed: int = DEFAULT_SEED,
) -> dict[str, str]:
    """Return ``{filename: content}`` for every sheet, the matrix and the generation record."""
    reviewer_ids = list(dict.fromkeys(reviewers))
    if not reviewer_ids:
        raise ValueError("at least one reviewer id is required")
    for reviewer_id in reviewer_ids:
        _check_reviewer_id(reviewer_id)

    cells = build_cells(findings)
    outputs: dict[str, str] = {}
    for reviewer_id in reviewer_ids:
        rows = blinded_rows(cells, reviewer_id, seed)
        outputs[sheet_filename(reviewer_id)] = render_csv(rows, BLINDED_FIELDS)
    outputs[MATRIX_FILENAME] = render_csv(matrix_rows(cells), MATRIX_FIELDS)

    documents = list(dict.fromkeys(cell["study_doc_id"] for cell in cells))
    record = {
        "schema_version": SHEETS_SCHEMA,
        "generator": "micar-review-sheets",
        "findings_file": findings_name,
        "findings_sha256": findings_sha256,
        "findings_schema": findings.get("schema", ""),
        "findings_digest": findings.get("digest", ""),
        "rule_source": "micar_linter.batch.STUDY_RULES",
        "rules": [
            {"rule_id": rule.rule_id, "annex_item": rule.annex_item, "rule_label": rule.label}
            for rule in STUDY_RULES
        ],
        "documents": documents,
        "rows_per_sheet": len(cells),
        "seed": seed,
        "row_order": ROW_ORDER_POLICY,
        "requirement_text_status": REQUIREMENT_TEXT_STATUS,
        "blinded_columns": list(BLINDED_FIELDS),
        "matrix_columns": list(MATRIX_FIELDS),
        "initial_review_state": "every human_label is 'pending'; every other review field is blank",
        "sheet_sha256_policy": (
            "Each sha256 below is the hash of the file as generated, with every label pending. "
            "Once labels are entered, a sheet differs from it in the review columns only; "
            "'micar-review-sheets --check' verifies the other columns and the row order."
        ),
        "sheets": [
            {
                "reviewer_id": reviewer_id,
                "file": sheet_filename(reviewer_id),
                "sha256": _sha256_text(outputs[sheet_filename(reviewer_id)]),
            }
            for reviewer_id in reviewer_ids
        ],
        "matrix": {"file": MATRIX_FILENAME, "sha256": _sha256_text(outputs[MATRIX_FILENAME])},
    }
    outputs[SHEETS_RECORD_FILENAME] = json.dumps(record, indent=2, ensure_ascii=False) + "\n"
    return outputs


def generate_review_sheets(
    findings_path: Path,
    *,
    reviewers: Sequence[str] = DEFAULT_REVIEWERS,
    seed: int = DEFAULT_SEED,
) -> dict[str, str]:
    raw = findings_path.read_bytes()
    findings = json.loads(raw.decode("utf-8"))
    return build_review_sheets(
        findings,
        findings_sha256=hashlib.sha256(raw).hexdigest(),
        findings_name=findings_path.name,
        reviewers=reviewers,
        seed=seed,
    )


def review_content_rows(path: Path) -> list[int]:
    """Return the data-row numbers (header = row 1) of rows that hold any review content."""
    if not path.exists() or path.suffix != ".csv":
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        found: list[int] = []
        for row_number, row in enumerate(reader, start=2):
            label = (row.get("human_label") or "").strip()
            others = [(row.get(field) or "").strip() for field in REVIEW_FIELDS if field != "human_label"]
            if label not in ("", PENDING_LABEL) or any(others):
                found.append(row_number)
        return found


def generated_columns(fieldnames: Sequence[str]) -> list[str]:
    """The columns the generator owns: every column except the human-review fields."""
    return [field for field in fieldnames if field not in REVIEW_FIELDS]


def structure_problems(expected: str, actual: str, *, validate_review: bool = True) -> list[str]:
    """Compare a sheet on disk with generated content, ignoring the human-review columns.

    The header, the number of rows, the row order and every generated column must match. With
    ``validate_review`` the review columns are checked instead of compared: ``human_label`` must
    be an allowed label or blank, and a pending (or blank) label must not carry a reviewer, date,
    pinpoint or note.
    """
    expected_reader = csv.DictReader(io.StringIO(expected))
    actual_reader = csv.DictReader(io.StringIO(actual))
    expected_rows = list(expected_reader)
    actual_rows = list(actual_reader)
    expected_header = list(expected_reader.fieldnames or [])
    actual_header = list(actual_reader.fieldnames or [])
    if actual_header != expected_header:
        return [f"header is {actual_header}, expected {expected_header}"]
    if len(actual_rows) != len(expected_rows):
        return [f"{len(actual_rows)} data rows, expected {len(expected_rows)}"]

    problems: list[str] = []
    columns = generated_columns(expected_header)
    for row_number, (want, got) in enumerate(zip(expected_rows, actual_rows, strict=True), start=2):
        changed = [column for column in columns if (got.get(column) or "") != (want.get(column) or "")]
        if changed:
            problems.append(f"row {row_number}: {', '.join(changed)} do not match the generator")
        if validate_review:
            problems.extend(f"row {row_number}: {problem}" for problem in _review_field_problems(got))
    return problems


def write_review_sheets(outputs: Mapping[str, str], out_dir: Path, *, force: bool = False) -> list[Path]:
    """Write the generated files and return the paths written.

    A CSV that already holds review content is kept unchanged when its generated columns and row
    order already match; if they would change, nothing is written and ``ReviewContentError`` is
    raised, unless ``force`` is true.
    """
    targets = [out_dir / name for name in outputs]
    keep: set[Path] = set()
    blocked: dict[str, list[int]] = {}
    for path in targets:
        rows = review_content_rows(path)
        if not rows or force:
            continue
        if structure_problems(outputs[path.name], path.read_text(encoding="utf-8"), validate_review=False):
            blocked[str(path)] = rows
        else:
            keep.add(path)
    if blocked:
        details = "; ".join(f"{path} (rows {_compact(rows)})" for path, rows in blocked.items())
        raise ReviewContentError(
            "refusing to change the generated columns or row order of sheets that already hold "
            f"review content: {details}. Use --force only if those labels are preserved elsewhere."
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for path in targets:
        if path in keep:
            continue
        path.write_text(outputs[path.name], encoding="utf-8", newline="")
        written.append(path)
    return written


def check_review_sheets(outputs: Mapping[str, str], out_dir: Path) -> list[str]:
    """Return one message per problem; an empty list means the files on disk match.

    CSV sheets are compared on their generated columns and row order only, so labels entered by
    a reviewer do not make a sheet out of date (see ``structure_problems``). The generation
    record is compared byte for byte.
    """
    problems: list[str] = []
    for name, content in outputs.items():
        path = out_dir / name
        if not path.exists():
            problems.append(f"{name}: missing")
            continue
        actual = path.read_text(encoding="utf-8")
        if name.endswith(".csv"):
            problems.extend(f"{name}: {problem}" for problem in structure_problems(content, actual))
        elif actual != content:
            problems.append(f"{name}: differs from the generated content")
    return problems


def read_sheets_record(out_dir: Path) -> dict[str, Any] | None:
    """Return the committed generation record in ``out_dir``, or None if there is none."""
    path = out_dir / SHEETS_RECORD_FILENAME
    if not path.exists():
        return None
    record = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(record, dict) or not isinstance(record.get("sheets", []), list):
        raise ValueError(f"{path}: not a review-sheets generation record")
    return record


def resolve_run(
    record: Mapping[str, Any] | None,
    requested_reviewers: Sequence[str] | None,
    requested_seed: int | None,
) -> tuple[list[str], int]:
    """Reviewers and seed for a run: the recorded ones, plus any requested reviewers.

    Reviewers already recorded keep their sheets, so adding a reviewer never drops another
    reviewer's entry from the generation record. An explicit seed overrides the recorded seed.
    """
    recorded = [str(sheet.get("reviewer_id", "")) for sheet in (record or {}).get("sheets", [])]
    reviewers = list(dict.fromkeys([*recorded, *(requested_reviewers or [])])) or list(DEFAULT_REVIEWERS)
    if requested_seed is not None:
        seed = requested_seed
    elif record is not None and "seed" in record:
        seed = int(record["seed"])
    else:
        seed = DEFAULT_SEED
    return reviewers, seed


def _check_findings_rules(findings: Mapping[str, Any], canonical: Mapping[str, StudyRule]) -> None:
    for item in findings.get("rules", []):
        rule_id = item.get("rule_id")
        if rule_id not in canonical:
            raise ValueError(f"findings rules array names {rule_id!r}, which is not in STUDY_RULES")
        if item.get("annex_item") != canonical[rule_id].annex_item:
            raise ValueError(
                f"findings rules array gives {item.get('annex_item')!r} for {rule_id}; "
                f"STUDY_RULES gives {canonical[rule_id].annex_item!r}"
            )


def _check_reviewer_id(reviewer_id: str) -> None:
    if not _REVIEWER_ID.match(reviewer_id):
        raise ValueError(
            f"reviewer id {reviewer_id!r} must start with a lowercase letter and use only "
            "lowercase letters, digits, '-' or '_' (for example r1)"
        )


def _review_field_problems(row: Mapping[str, str]) -> list[str]:
    label = (row.get("human_label") or "").strip()
    if label and label not in ALLOWED_LABELS:
        return [f"human_label {label!r} is not one of {sorted(ALLOWED_LABELS)}"]
    if label in ("", PENDING_LABEL):
        filled = [field for field in REVIEW_FIELDS[1:] if (row.get(field) or "").strip()]
        if filled:
            return [f"{', '.join(filled)} filled while human_label is pending"]
    return []


def _empty_review_fields() -> dict[str, str]:
    fields = {field: "" for field in REVIEW_FIELDS}
    fields["human_label"] = PENDING_LABEL
    return fields


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _compact(numbers: Sequence[int], limit: int = 5) -> str:
    shown = ", ".join(str(number) for number in numbers[:limit])
    return shown if len(numbers) <= limit else f"{shown} and {len(numbers) - limit} more"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="micar-review-sheets",
        description=(
            "Regenerate the blinded per-reviewer review sheets and the adjudication matrix "
            "from a study findings file. Every label is written as pending."
        ),
    )
    parser.add_argument("--findings", required=True, type=Path, help="findings-pseudonymous.json")
    parser.add_argument("--out-dir", required=True, type=Path, help="study directory to write into")
    parser.add_argument(
        "--reviewer",
        action="append",
        dest="reviewers",
        help=(
            f"reviewer id to add; repeat for several. Reviewers recorded in {SHEETS_RECORD_FILENAME} "
            "are always kept (default when nothing is recorded: r1)"
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help=f"row-order seed (default: the recorded seed, else {DEFAULT_SEED})",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "write nothing; exit 1 if a committed file differs from the generator. Sheets are "
            "compared on their generated columns and row order, so entered labels pass"
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite sheets even if they already hold review content (the labels are lost)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        reviewers, seed = resolve_run(read_sheets_record(args.out_dir), args.reviewers, args.seed)
        outputs = generate_review_sheets(args.findings, reviewers=reviewers, seed=seed)
    except (OSError, ValueError) as exc:
        print(f"micar-review-sheets: {exc}", file=sys.stderr)
        return 2

    if args.check:
        problems = check_review_sheets(outputs, args.out_dir)
        if problems:
            print("Out of date or invalid:\n  " + "\n  ".join(problems), file=sys.stderr)
            return 1
        print(
            f"Review sheets match {args.findings.name} (reviewers {', '.join(reviewers)}; seed {seed}).",
            file=sys.stderr,
        )
        return 0

    try:
        written = write_review_sheets(outputs, args.out_dir, force=args.force)
    except ReviewContentError as exc:
        print(f"micar-review-sheets: {exc}", file=sys.stderr)
        return 3
    kept = [name for name in outputs if args.out_dir / name not in written]
    rows = json.loads(outputs[SHEETS_RECORD_FILENAME])["rows_per_sheet"]
    message = (
        f"Wrote {', '.join(path.name for path in written)} ({rows} rows per sheet; new sheets have "
        f"every label pending; reviewers {', '.join(reviewers)}; seed {seed})."
    )
    if kept:
        message += f" Kept unchanged, because they hold review content: {', '.join(kept)}."
    print(message, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
