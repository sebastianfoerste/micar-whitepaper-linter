"""Validate reviewer labels and merge them into the Title II study's adjudication matrix.

``micar-review-merge`` has three subcommands:

- ``check``: validate one reviewer's sheet (the CSV, or a workbook from ``micar-review-workbook``)
  and report progress. It writes nothing.
- ``import``: read a reviewer's filled workbook, validate every row and write the labels into the
  reviewer's blinded sheet, ``human-review-<reviewer_id>.csv``. The labelled sheet is then committed
  on its own, before any merge with detector outcomes (review-protocol.md).
- ``matrix``: validate the sheet of every reviewer recorded in ``human-review-sheets.json``. With
  two or more reviewers, compare the labels, write a disagreement report and require an
  adjudication file for every disagreement. Then write the final labels into
  ``human-review-matrix.csv`` next to the detector outcomes, rewrite ``human-review-summary.json``
  with ``micar-review-summary --require-complete``, and re-check that the summary, the sheets and
  the generation record are consistent.

Every step refuses while any cell is pending or invalid and lists the offending rows. A row is
valid when its label is in the vocabulary of ``review_validation.LABEL_ORDER``, its reviewer_id is
the sheet's reviewer, its reviewed_at is an ISO 8601 date (YYYY-MM-DD) between the date the findings
were generated and today, and it carries the field its label requires
(``review_validation.LABEL_REQUIRED_FIELDS``: a pinpoint for present and missing, a note for the
other labels).

Cell identity and row order are checked against the generator, not trusted from the input: the
findings file must hash to the value recorded in ``human-review-sheets.json``, the regenerated
pending sheets must hash to the recorded sheet hashes, and every sheet, workbook and adjudication
file must carry the same cells in the same order.

The tool never fills, infers or changes a label. Final labels come from the reviewers' sheets or,
for a disagreement, from the adjudication file.

Exit status: 0 success; 1 refused because cells are pending or invalid; 2 usage or input error;
3 cell identity or row order differs from the generated sheets, or the study files are
inconsistent; 4 reviewers disagree and the adjudication file is missing, stale, pending or invalid;
5 the target file already holds different review content (``--replace`` overwrites it).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from micar_linter import review_validation
from micar_linter.review_sheets import (
    _REVIEWER_ID,
    BLINDED_FIELDS,
    CELL_FIELDS,
    MATRIX_FIELDS,
    MATRIX_FILENAME,
    REVIEW_FIELDS,
    SHEETS_RECORD_FILENAME,
    build_review_sheets,
    check_review_sheets,
    read_sheets_record,
    render_csv,
    review_content_rows,
    sheet_filename,
    structure_problems,
)
from micar_linter.review_validation import (
    ALLOWED_LABELS,
    LABEL_ORDER,
    LABEL_REQUIRED_FIELDS,
    PENDING_LABEL,
    summarize_rows,
)

SUMMARY_FILENAME = "human-review-summary.json"
DISAGREEMENTS_FILENAME = "human-review-disagreements.csv"
ADJUDICATION_FIELDS: tuple[str, ...] = (
    "final_label",
    "adjudicated_by",
    "adjudicated_at",
    "final_pinpoint",
    "adjudication_reason",
)
# The adjudication column that carries a field LABEL_REQUIRED_FIELDS asks for.
ADJUDICATION_EQUIVALENT = {"source_pinpoint": "final_pinpoint", "review_note": "adjudication_reason"}
REVIEWER_COLUMN_SUFFIXES: tuple[str, ...] = ("label", "reviewed_at", "pinpoint", "note")

EXIT_OK = 0
EXIT_REFUSED = 1
EXIT_USAGE = 2
EXIT_IDENTITY = 3
EXIT_ADJUDICATION = 4
EXIT_OVERWRITE = 5

_ISO_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


class MergeRefused(Exception):
    """A step refused to run; ``exit_code`` is the CLI exit status and ``details`` the offending rows."""

    def __init__(self, exit_code: int, message: str, details: Sequence[str] = ()) -> None:
        super().__init__(message)
        self.exit_code = exit_code
        self.details = list(details)


@dataclass(frozen=True)
class Study:
    """A study directory whose sheets the generator still reproduces as recorded."""

    directory: Path
    reviewers: tuple[str, ...]
    seed: int
    findings_sha256: str
    outputs: Mapping[str, str]
    earliest_review_date: date

    def sheet_path(self, reviewer_id: str) -> Path:
        return self.directory / sheet_filename(reviewer_id)

    def expected_sheet(self, reviewer_id: str) -> str:
        """The reviewer's sheet as generated, with every label pending."""
        if reviewer_id not in self.reviewers:
            recorded = ", ".join(self.reviewers)
            raise MergeRefused(
                EXIT_USAGE,
                f"no sheet is recorded for reviewer {reviewer_id!r} (recorded: {recorded}); "
                f"add one with micar-review-sheets --reviewer {reviewer_id}",
            )
        return self.outputs[sheet_filename(reviewer_id)]

    @property
    def matrix_path(self) -> Path:
        return self.directory / MATRIX_FILENAME

    @property
    def summary_path(self) -> Path:
        return self.directory / SUMMARY_FILENAME


@dataclass
class SheetReport:
    """Validation result for one reviewer's rows."""

    source: str
    reviewer_id: str
    rows: list[dict[str, str]]
    pending: list[int] = field(default_factory=list)
    invalid: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.rows)

    @property
    def complete(self) -> bool:
        return not self.pending and not self.invalid

    def problem_lines(self) -> list[str]:
        lines = [f"{self.source}: {problem}" for problem in self.invalid]
        if self.pending:
            lines.append(f"{self.source}: {len(self.pending)} pending, rows {_ranges(self.pending)}")
        return lines


def load_study(directory: Path, findings_path: Path | None = None) -> Study:
    """Load a study directory and confirm that the generator reproduces its recorded sheets."""
    try:
        record = read_sheets_record(directory)
    except (OSError, ValueError) as exc:
        raise MergeRefused(EXIT_USAGE, f"cannot read {SHEETS_RECORD_FILENAME}: {exc}") from exc
    if record is None:
        raise MergeRefused(
            EXIT_USAGE,
            f"{directory}: no {SHEETS_RECORD_FILENAME}; generate the sheets with micar-review-sheets",
        )
    findings_path = findings_path or directory / str(record.get("findings_file") or "")
    try:
        raw = findings_path.read_bytes()
        findings = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError) as exc:
        raise MergeRefused(EXIT_USAGE, f"cannot read the findings file {findings_path}: {exc}") from exc

    findings_sha256 = hashlib.sha256(raw).hexdigest()
    if findings_sha256 != record.get("findings_sha256"):
        raise MergeRefused(
            EXIT_IDENTITY,
            f"{findings_path.name} hashes to {findings_sha256}, but {SHEETS_RECORD_FILENAME} records "
            f"{record.get('findings_sha256')}: the sheets were generated from a different findings file",
        )
    reviewers = tuple(str(sheet.get("reviewer_id", "")) for sheet in record.get("sheets", []))
    seed = int(record.get("seed", 0))
    try:
        outputs = build_review_sheets(
            findings,
            findings_sha256=findings_sha256,
            findings_name=findings_path.name,
            reviewers=reviewers,
            seed=seed,
        )
    except ValueError as exc:
        raise MergeRefused(EXIT_IDENTITY, f"cannot regenerate the review sheets: {exc}") from exc

    problems: list[str] = []
    recorded_files = [(sheet.get("file"), sheet.get("sha256")) for sheet in record.get("sheets", [])]
    recorded_files.append((record.get("matrix", {}).get("file"), record.get("matrix", {}).get("sha256")))
    for name, sha256 in recorded_files:
        if name not in outputs:
            problems.append(f"{SHEETS_RECORD_FILENAME} lists {name!r}, which the generator does not produce")
        elif _sha256_text(outputs[name]) != sha256:
            problems.append(f"the generator no longer reproduces {name} as recorded (sha256 {sha256})")
    record_path = directory / SHEETS_RECORD_FILENAME
    if not problems and record_path.read_text(encoding="utf-8") != outputs[SHEETS_RECORD_FILENAME]:
        problems.append(
            f"{SHEETS_RECORD_FILENAME} differs from the generator; run micar-review-sheets --check"
        )
    if problems:
        raise MergeRefused(EXIT_IDENTITY, "the study files are inconsistent with the generator", problems)

    return Study(
        directory=directory,
        reviewers=reviewers,
        seed=seed,
        findings_sha256=findings_sha256,
        outputs=outputs,
        earliest_review_date=_findings_date(findings),
    )


def read_sheet(study: Study, reviewer_id: str) -> tuple[str, list[dict[str, str]]]:
    """Return the text and rows of a reviewer's CSV sheet after checking its cells and row order."""
    expected = study.expected_sheet(reviewer_id)
    path = study.sheet_path(reviewer_id)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise MergeRefused(EXIT_USAGE, f"cannot read {path}: {exc}") from exc
    problems = structure_problems(expected, text, validate_review=False)
    if problems:
        raise MergeRefused(
            EXIT_IDENTITY,
            f"{path.name}: cell identity or row order differs from the generated sheet",
            [f"{path.name}: {problem}" for problem in problems],
        )
    return text, csv_rows(text)


def validate_rows(
    rows: Sequence[Mapping[str, str]],
    reviewer_id: str,
    *,
    source: str,
    earliest: date,
    today: date,
) -> SheetReport:
    """Validate every row of one reviewer's sheet. Row numbers count the header as row 1."""
    report = SheetReport(source=source, reviewer_id=reviewer_id, rows=[dict(row) for row in rows])
    for number, row in enumerate(rows, start=2):
        where = f"row {number} ({row.get('study_doc_id', '')}, {row.get('rule_id', '')})"
        label = _value(row, "human_label") or PENDING_LABEL
        if label not in ALLOWED_LABELS:
            report.invalid.append(f"{where}: human_label {label!r} is not one of {', '.join(LABEL_ORDER)}")
            continue
        if label == PENDING_LABEL:
            report.pending.append(number)
            continue
        problems: list[str] = []
        reviewer = _value(row, "reviewer_id")
        if reviewer != reviewer_id:
            problems.append(
                "reviewer_id is blank"
                if not reviewer
                else f"reviewer_id {reviewer!r} is not this sheet's reviewer {reviewer_id!r}"
            )
        problems.extend(
            date_problems(
                "reviewed_at",
                _value(row, "reviewed_at"),
                earliest=earliest,
                earliest_reason="the date the findings were generated",
                today=today,
            )
        )
        problems.extend(
            f"{name} is required for {label!r}"
            for name in LABEL_REQUIRED_FIELDS[label]
            if not _value(row, name)
        )
        report.invalid.extend(f"{where}: {problem}" for problem in problems)
    return report


def date_problems(name: str, value: str, *, earliest: date, earliest_reason: str, today: date) -> list[str]:
    """Problems with an ISO 8601 calendar date (YYYY-MM-DD) that must lie between two dates."""
    if not value:
        return [f"{name} is blank"]
    if not _ISO_DATE.fullmatch(value):
        return [f"{name} {value!r} is not an ISO 8601 date (YYYY-MM-DD)"]
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return [f"{name} {value!r} is not a calendar date (YYYY-MM-DD)"]
    if parsed < earliest:
        return [f"{name} {value} is before {earliest.isoformat()}, {earliest_reason}"]
    if parsed > today:
        return [f"{name} {value} is after today ({today.isoformat()})"]
    return []


def check_sheet(
    study: Study,
    reviewer_id: str,
    *,
    workbook: Path | None = None,
    today: date | None = None,
) -> SheetReport:
    """Validate a reviewer's CSV sheet, or their workbook if one is given. Writes nothing."""
    today = today or _today()
    if workbook is not None:
        from micar_linter.review_workbook import read_workbook

        rows = read_workbook(workbook, study, reviewer_id)
        source = workbook.name
    else:
        _, rows = read_sheet(study, reviewer_id)
        source = sheet_filename(reviewer_id)
    return validate_rows(rows, reviewer_id, source=source, earliest=study.earliest_review_date, today=today)


def import_workbook(
    study: Study,
    reviewer_id: str,
    workbook: Path,
    *,
    replace: bool = False,
    today: date | None = None,
) -> tuple[Path, SheetReport]:
    """Write a reviewer's fully labelled workbook into their blinded CSV sheet."""
    expected = study.expected_sheet(reviewer_id)
    current_text, _ = read_sheet(study, reviewer_id)
    report = check_sheet(study, reviewer_id, workbook=workbook, today=today)
    if not report.complete:
        raise MergeRefused(
            EXIT_REFUSED,
            f"{workbook.name}: {len(report.pending)} pending and {len(report.invalid)} invalid of "
            f"{report.total} cells; nothing was written",
            report.problem_lines(),
        )

    labelled = []
    for generated, entered in zip(csv_rows(expected), report.rows, strict=True):
        row = dict(generated)
        row.update({name: _value(entered, name) for name in REVIEW_FIELDS})
        labelled.append(row)
    new_text = render_csv(labelled, BLINDED_FIELDS)
    _assert_consistent(expected, new_text, sheet_filename(reviewer_id))

    path = study.sheet_path(reviewer_id)
    _refuse_overwrite(path, current_text, new_text, replace=replace)
    if current_text != new_text:
        path.write_text(new_text, encoding="utf-8", newline="")
    return path, report


@dataclass
class MergeResult:
    matrix_path: Path
    summary_path: Path
    summary: dict[str, Any]
    reviewers: tuple[str, ...]
    disagreements: int
    disagreements_path: Path | None


def merge_matrix(
    study: Study,
    *,
    adjudication: Path | None = None,
    disagreements_path: Path | None = None,
    replace: bool = False,
    today: date | None = None,
) -> MergeResult:
    """Merge the final labels into the matrix and rewrite the summary.

    Nothing is written while any reviewer's sheet is pending or invalid. With two or more
    reviewers the disagreement report is written first; the matrix is written only when every
    disagreement is adjudicated.
    """
    today = today or _today()
    reports: dict[str, SheetReport] = {}
    problems: list[str] = []
    for reviewer_id in study.reviewers:
        _, rows = read_sheet(study, reviewer_id)
        report = validate_rows(
            rows,
            reviewer_id,
            source=sheet_filename(reviewer_id),
            earliest=study.earliest_review_date,
            today=today,
        )
        reports[reviewer_id] = report
        problems.extend(report.problem_lines())
    if problems:
        raise MergeRefused(
            EXIT_REFUSED,
            "every reviewer's sheet must be complete and valid before the merge; nothing was written",
            problems,
        )

    expected_matrix = study.outputs[MATRIX_FILENAME]
    try:
        current_matrix = study.matrix_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise MergeRefused(EXIT_USAGE, f"cannot read {study.matrix_path}: {exc}") from exc
    matrix_problems = structure_problems(expected_matrix, current_matrix, validate_review=False)
    if matrix_problems:
        raise MergeRefused(
            EXIT_IDENTITY,
            f"{MATRIX_FILENAME}: cell identity, detector columns or row order differ from the generator",
            [f"{MATRIX_FILENAME}: {problem}" for problem in matrix_problems],
        )

    by_reviewer = {
        reviewer_id: {_key(row): row for row in report.rows} for reviewer_id, report in reports.items()
    }
    cells = csv_rows(expected_matrix)
    finals: dict[tuple[str, str], dict[str, str]] = {}
    disagreements: list[dict[str, str]] = []
    report_path: Path | None = None

    if len(study.reviewers) == 1:
        (only,) = study.reviewers
        for cell in cells:
            finals[_key(cell)] = {name: _value(by_reviewer[only][_key(cell)], name) for name in REVIEW_FIELDS}
    else:
        for cell in cells:
            entries = {reviewer_id: by_reviewer[reviewer_id][_key(cell)] for reviewer_id in study.reviewers}
            if len({_value(entry, "human_label") for entry in entries.values()}) == 1:
                finals[_key(cell)] = _agreed_fields(entries)
            else:
                disagreements.append(_disagreement_row(cell, entries))
        report_text = render_csv(disagreements, disagreement_fields(study.reviewers))
        report_path = disagreements_path or study.directory / DISAGREEMENTS_FILENAME
        report_path.write_text(report_text, encoding="utf-8", newline="")
        latest_review = max(
            date.fromisoformat(_value(row, "reviewed_at"))
            for report in reports.values()
            for row in report.rows
        )
        if disagreements and adjudication is None:
            raise MergeRefused(
                EXIT_ADJUDICATION,
                f"{len(disagreements)} cells have different labels from {' and '.join(study.reviewers)}. "
                f"The disagreement report is {report_path}. Copy it to an adjudication file, fill "
                f"{', '.join(ADJUDICATION_FIELDS)} for every row, and pass it with --adjudication. "
                "The matrix was not written",
                [f"{row['study_doc_id']}, {row['rule_id']}" for row in disagreements],
            )
        if adjudication is not None:
            decided = validate_adjudication(
                adjudication,
                report_text,
                study.reviewers,
                earliest=latest_review,
                today=today,
            )
            for row in disagreements:
                finals[_key(row)] = _adjudicated_fields(decided[_key(row)], study.reviewers)

    merged = []
    for cell in cells:
        row = dict(cell)
        row.update(finals[_key(cell)])
        merged.append(row)
    new_matrix = render_csv(merged, MATRIX_FIELDS)
    _assert_consistent(expected_matrix, new_matrix, MATRIX_FILENAME)
    _refuse_overwrite(study.matrix_path, current_matrix, new_matrix, replace=replace)

    if current_matrix != new_matrix:
        study.matrix_path.write_text(new_matrix, encoding="utf-8", newline="")
    status = review_validation.main(
        ["--matrix", str(study.matrix_path), "--out", str(study.summary_path), "--require-complete"]
    )
    summary = json.loads(study.summary_path.read_text(encoding="utf-8"))
    consistency = check_review_sheets(study.outputs, study.directory)
    with study.matrix_path.open(newline="", encoding="utf-8") as handle:
        if summarize_rows(csv.DictReader(handle)) != summary:
            consistency.append(f"{SUMMARY_FILENAME} does not match {MATRIX_FILENAME}")
    if status != 0:
        consistency.append(f"micar-review-summary --require-complete exited {status}")
    if consistency:
        raise MergeRefused(EXIT_IDENTITY, "the merged study files are inconsistent", consistency)
    return MergeResult(
        matrix_path=study.matrix_path,
        summary_path=study.summary_path,
        summary=summary,
        reviewers=study.reviewers,
        disagreements=len(disagreements),
        disagreements_path=report_path,
    )


def disagreement_fields(reviewers: Sequence[str]) -> list[str]:
    """Columns of the disagreement report and the adjudication file."""
    per_reviewer = [
        f"{reviewer_id}_{suffix}" for reviewer_id in reviewers for suffix in REVIEWER_COLUMN_SUFFIXES
    ]
    return [*CELL_FIELDS, *per_reviewer, *ADJUDICATION_FIELDS]


def validate_adjudication(
    path: Path,
    report_text: str,
    reviewers: Sequence[str],
    *,
    earliest: date,
    today: date,
) -> dict[tuple[str, str], dict[str, str]]:
    """Return the adjudicated rows keyed by cell, or raise ``MergeRefused`` (exit 4).

    The file must list exactly the cells of the current disagreement report, in its order and
    with its reviewer columns unchanged. Each row needs a final label other than pending, who
    adjudicated (all original reviewers by consensus, such as ``r1+r2``, or a person who was not
    one of them; never one original reviewer alone), an ISO date no earlier than the latest
    review date, the reasoning, and the field its final label requires.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise MergeRefused(EXIT_USAGE, f"cannot read the adjudication file {path}: {exc}") from exc
    expected_reader = csv.DictReader(io.StringIO(report_text))
    expected_rows = list(expected_reader)
    actual_reader = csv.DictReader(io.StringIO(text))
    actual_rows = list(actual_reader)
    name = path.name
    if list(actual_reader.fieldnames or []) != list(expected_reader.fieldnames or []):
        raise MergeRefused(
            EXIT_ADJUDICATION,
            f"{name}: header is {actual_reader.fieldnames}, expected {expected_reader.fieldnames}",
        )
    if len(actual_rows) != len(expected_rows):
        raise MergeRefused(
            EXIT_ADJUDICATION,
            f"{name}: {len(actual_rows)} rows, but the current disagreement report has {len(expected_rows)}; "
            "the sheets changed since it was copied, or rows were added or removed",
        )

    problems: list[str] = []
    pending: list[int] = []
    decided: dict[tuple[str, str], dict[str, str]] = {}
    fixed = [column for column in expected_reader.fieldnames or [] if column not in ADJUDICATION_FIELDS]
    for number, (want, got) in enumerate(zip(expected_rows, actual_rows, strict=True), start=2):
        where = f"{name}: row {number} ({got.get('study_doc_id', '')}, {got.get('rule_id', '')})"
        changed = [column for column in fixed if (got.get(column) or "") != (want.get(column) or "")]
        if changed:
            problems.append(f"{where}: {', '.join(changed)} differ from the current disagreement report")
            continue
        label = _value(got, "final_label") or PENDING_LABEL
        if label == PENDING_LABEL:
            pending.append(number)
            continue
        if label not in ALLOWED_LABELS:
            problems.append(f"{where}: final_label {label!r} is not one of {', '.join(LABEL_ORDER[:-1])}")
            continue
        row_problems = _adjudicator_problems(_value(got, "adjudicated_by"), reviewers)
        row_problems.extend(
            date_problems(
                "adjudicated_at",
                _value(got, "adjudicated_at"),
                earliest=earliest,
                earliest_reason="the latest review date in the sheets",
                today=today,
            )
        )
        required = {
            "adjudication_reason",
            *(ADJUDICATION_EQUIVALENT[f] for f in LABEL_REQUIRED_FIELDS[label]),
        }
        row_problems.extend(
            f"{column} is required for {label!r}"
            for column in ADJUDICATION_FIELDS
            if column in required and not _value(got, column)
        )
        problems.extend(f"{where}: {problem}" for problem in row_problems)
        decided[_key(got)] = got
    if pending:
        problems.append(f"{name}: {len(pending)} pending, rows {_ranges(pending)}")
    if problems:
        raise MergeRefused(
            EXIT_ADJUDICATION,
            f"{name}: adjudication incomplete or invalid; the matrix was not written",
            problems,
        )
    return decided


def _adjudicator_problems(value: str, reviewers: Sequence[str]) -> list[str]:
    if not value:
        return ["adjudicated_by is blank"]
    people = [part.strip() for part in value.split("+")]
    bad = [person for person in people if not _REVIEWER_ID.match(person)]
    if bad:
        return [f"adjudicated_by {value!r}: use study IDs joined by '+', for example r1+r2 or r3"]
    original = set(reviewers)
    named = set(people)
    if named <= original and named != original:
        return [
            f"adjudicated_by {value!r} names only some of the original reviewers; adjudicate by "
            f"consensus of all of them ({'+'.join(reviewers)}) or with a person who was not a reviewer"
        ]
    return []


def _agreed_fields(entries: Mapping[str, Mapping[str, str]]) -> dict[str, str]:
    first = next(iter(entries.values()))
    return {
        "human_label": _value(first, "human_label"),
        "reviewer_id": "+".join(entries),
        "reviewed_at": max(_value(entry, "reviewed_at") for entry in entries.values()),
        "source_pinpoint": _combined(
            {rid: _value(entry, "source_pinpoint") for rid, entry in entries.items()}
        ),
        "review_note": _combined({rid: _value(entry, "review_note") for rid, entry in entries.items()}),
    }


def _adjudicated_fields(row: Mapping[str, str], reviewers: Sequence[str]) -> dict[str, str]:
    labels = ", ".join(f"{reviewer_id}: {_value(row, f'{reviewer_id}_label')}" for reviewer_id in reviewers)
    return {
        "human_label": _value(row, "final_label"),
        "reviewer_id": "+".join(part.strip() for part in _value(row, "adjudicated_by").split("+")),
        "reviewed_at": _value(row, "adjudicated_at"),
        "source_pinpoint": _value(row, "final_pinpoint"),
        "review_note": f"Adjudicated ({labels}): {_value(row, 'adjudication_reason')}",
    }


def _disagreement_row(cell: Mapping[str, str], entries: Mapping[str, Mapping[str, str]]) -> dict[str, str]:
    row = {name: cell[name] for name in CELL_FIELDS}
    for reviewer_id, entry in entries.items():
        row[f"{reviewer_id}_label"] = _value(entry, "human_label")
        row[f"{reviewer_id}_reviewed_at"] = _value(entry, "reviewed_at")
        row[f"{reviewer_id}_pinpoint"] = _value(entry, "source_pinpoint")
        row[f"{reviewer_id}_note"] = _value(entry, "review_note")
    row.update({name: "" for name in ADJUDICATION_FIELDS})
    row["final_label"] = PENDING_LABEL
    return row


def _combined(values: Mapping[str, str]) -> str:
    distinct = list(dict.fromkeys(value for value in values.values() if value))
    if len(distinct) <= 1:
        return distinct[0] if distinct else ""
    return " | ".join(f"{reviewer_id}: {value}" for reviewer_id, value in values.items() if value)


def _refuse_overwrite(path: Path, current: str, new: str, *, replace: bool) -> None:
    if current == new or replace or not review_content_rows(path):
        return
    raise MergeRefused(
        EXIT_OVERWRITE,
        f"{path.name} already holds review content that differs from the new labels; nothing was "
        "written. Pass --replace to overwrite it (its committed version stays in git history)",
    )


def _assert_consistent(expected: str, new_text: str, name: str) -> None:
    problems = structure_problems(expected, new_text)
    if problems:
        raise MergeRefused(EXIT_IDENTITY, f"{name}: the merged content fails the sheet check", problems)


def _today() -> date:
    return date.today()


def _findings_date(findings: Mapping[str, Any]) -> date:
    try:
        return date.fromisoformat(str(findings.get("generated_at", ""))[:10])
    except ValueError:
        return date.min


def csv_rows(text: str) -> list[dict[str, str]]:
    """Parse CSV text into rows of strings (missing values become empty strings)."""
    return [{key: value or "" for key, value in row.items()} for row in csv.DictReader(io.StringIO(text))]


def _key(row: Mapping[str, str]) -> tuple[str, str]:
    return (row["study_doc_id"], row["rule_id"])


def _value(row: Mapping[str, str], name: str) -> str:
    return (row.get(name) or "").strip()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _ranges(numbers: Sequence[int]) -> str:
    """``[2, 3, 4, 7]`` -> ``"2-4, 7"``."""
    parts: list[str] = []
    start = previous = None
    for number in sorted(numbers):
        if start is None:
            start = previous = number
        elif number == previous + 1:
            previous = number
        else:
            parts.append(str(start) if start == previous else f"{start}-{previous}")
            start = previous = number
    if start is not None:
        parts.append(str(start) if start == previous else f"{start}-{previous}")
    return ", ".join(parts)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="micar-review-merge",
        description=(
            "Validate reviewer labels, import a filled review workbook into the reviewer's blinded "
            "sheet, and merge the final labels into the adjudication matrix. Refuses while any "
            "cell is pending or invalid."
        ),
    )
    commands = parser.add_subparsers(dest="command", required=True)

    def add_study(sub: argparse.ArgumentParser) -> None:
        sub.add_argument("--study-dir", required=True, type=Path, help="study directory with the sheets")
        sub.add_argument(
            "--findings",
            type=Path,
            default=None,
            help="findings file (default: the one named in human-review-sheets.json)",
        )

    check = commands.add_parser("check", help="validate one reviewer's sheet or workbook; writes nothing")
    add_study(check)
    check.add_argument("--reviewer", required=True, help="reviewer id, for example r1")
    check.add_argument("--workbook", type=Path, default=None, help="check this workbook instead of the CSV")

    imp = commands.add_parser("import", help="write a fully labelled workbook into the reviewer's CSV sheet")
    add_study(imp)
    imp.add_argument("--reviewer", required=True, help="reviewer id, for example r1")
    imp.add_argument("--workbook", required=True, type=Path, help="the reviewer's filled .xlsx workbook")
    imp.add_argument("--replace", action="store_true", help="overwrite labels already in the CSV sheet")

    matrix = commands.add_parser(
        "matrix", help="merge the final labels into the matrix and rewrite the summary"
    )
    add_study(matrix)
    matrix.add_argument(
        "--adjudication",
        type=Path,
        default=None,
        help="adjudication file for the cells on which reviewers disagree (two or more reviewers)",
    )
    matrix.add_argument(
        "--disagreements",
        type=Path,
        default=None,
        help=f"where to write the disagreement report (default: <study-dir>/{DISAGREEMENTS_FILENAME})",
    )
    matrix.add_argument("--replace", action="store_true", help="overwrite labels already in the matrix")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        study = load_study(args.study_dir, args.findings)
        if args.command == "check":
            report = check_sheet(study, args.reviewer, workbook=args.workbook)
            labelled = report.total - len(report.pending)
            print(
                f"{report.source}: {labelled} of {report.total} cells labelled, "
                f"{len(report.pending)} pending, {len(report.invalid)} invalid.",
                file=sys.stderr,
            )
            _print_details(report.problem_lines())
            return EXIT_OK if report.complete else EXIT_REFUSED
        if args.command == "import":
            path, report = import_workbook(study, args.reviewer, args.workbook, replace=args.replace)
            print(
                f"Wrote {path}: {report.total} cells labelled by {args.reviewer} "
                f"({_label_counts(report.rows)}). Commit this sheet on its own before running "
                "`micar-review-merge matrix`.",
                file=sys.stderr,
            )
            return EXIT_OK
        result = merge_matrix(
            study,
            adjudication=args.adjudication,
            disagreements_path=args.disagreements,
            replace=args.replace,
        )
    except MergeRefused as exc:
        print(f"micar-review-merge: {exc}", file=sys.stderr)
        _print_details(exc.details)
        return exc.exit_code
    except OSError as exc:
        print(f"micar-review-merge: {exc}", file=sys.stderr)
        return EXIT_USAGE

    message = (
        f"Wrote {result.matrix_path.name} and {result.summary_path.name} from the labels of "
        f"{' and '.join(result.reviewers)}: {result.summary['rows_completed']} of "
        f"{result.summary['rows_total']} cells final"
    )
    if result.disagreements_path is not None:
        message += f"; {result.disagreements} disagreements, report in {result.disagreements_path.name}"
    print(message + ". The summary, sheets and generation record are consistent.", file=sys.stderr)
    return EXIT_OK


def _label_counts(rows: Sequence[Mapping[str, str]]) -> str:
    counts = {label: 0 for label in LABEL_ORDER}
    for row in rows:
        counts[_value(row, "human_label") or PENDING_LABEL] += 1
    return ", ".join(f"{label} {count}" for label, count in counts.items() if count)


def _print_details(lines: Sequence[str]) -> None:
    for line in lines:
        print(f"  {line}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
