from __future__ import annotations

import copy
import csv
import hashlib
import io
import json
from pathlib import Path

import pytest

from micar_linter.batch import STUDY_RULES
from micar_linter.review_sheets import (
    BLINDED_FIELDS,
    DEFAULT_SEED,
    DETECTOR_FIELDS,
    MATRIX_FIELDS,
    REVIEW_FIELDS,
    REVIEW_REQUIREMENTS,
    SHEETS_RECORD_FILENAME,
    ReviewContentError,
    build_review_sheets,
    check_review_sheets,
    main,
    read_sheets_record,
    resolve_run,
    write_review_sheets,
)
from micar_linter.review_validation import summarize_rows

STUDY = Path(__file__).resolve().parents[1] / "studies" / "2026-07-title-ii-annex-i-whitepaper-study"
FINDINGS = STUDY / "findings-pseudonymous.json"
CANONICAL = {rule.rule_id: rule for rule in STUDY_RULES}


def _findings() -> dict:
    return json.loads(FINDINGS.read_text(encoding="utf-8"))


def _outputs(findings: dict | None = None, **kwargs) -> dict[str, str]:
    return build_review_sheets(findings or _findings(), findings_sha256="0" * 64, **kwargs)


def _rows(text: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(text)))


def _header(text: str) -> list[str]:
    return text.splitlines()[0].split(",")


def _label_one_cell(sheet: Path, row_index: int = 0) -> None:
    """Fill one cell the way a reviewer would; the generated columns stay untouched."""
    text = sheet.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    rows[row_index].update(
        human_label="present",
        reviewer_id="r1",
        reviewed_at="2026-10-20",
        source_pinpoint="p. 3",
        review_note="test",
    )
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=reader.fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    sheet.write_text(buffer.getvalue(), encoding="utf-8")


def test_committed_sheets_match_the_generator_on_their_generated_columns():
    # Reviewers and seed come from the committed record, and the comparison ignores the review
    # columns, so this test stays green once labels are committed.
    reviewers, seed = resolve_run(read_sheets_record(STUDY), None, None)
    outputs = build_review_sheets(
        _findings(),
        findings_sha256=hashlib.sha256(FINDINGS.read_bytes()).hexdigest(),
        reviewers=reviewers,
        seed=seed,
    )

    assert check_review_sheets(outputs, STUDY) == []
    assert main(["--findings", str(FINDINGS), "--out-dir", str(STUDY), "--check"]) == 0
    assert not (STUDY / "human-review-blinded.csv").exists()


def test_generator_output_is_deterministic(tmp_path: Path):
    assert _outputs() == _outputs()
    args = ["--findings", str(FINDINGS), "--out-dir", str(tmp_path)]
    assert main(args) == 0
    first = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    for path in tmp_path.iterdir():
        path.unlink()
    assert main(args) == 0
    assert {path.name: path.read_bytes() for path in tmp_path.iterdir()} == first


def test_check_passes_with_labels_and_fails_on_structural_changes(tmp_path: Path):
    assert main(["--findings", str(FINDINGS), "--out-dir", str(tmp_path)]) == 0
    args = ["--findings", str(FINDINGS), "--out-dir", str(tmp_path), "--check"]
    _label_one_cell(tmp_path / "human-review-r1.csv")
    _label_one_cell(tmp_path / "human-review-matrix.csv", row_index=4)
    assert main(args) == 0
    with (tmp_path / "human-review-matrix.csv").open(newline="", encoding="utf-8") as handle:
        assert summarize_rows(csv.DictReader(handle))["rows_completed"] == 1

    original = (tmp_path / "human-review-r1.csv").read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)
    broken_cases = {
        "row order": "".join([lines[0], lines[2], lines[1], *lines[3:]]),
        "unknown label": original.replace(",present,", ",presnt,", 1),
        "pending with a pinpoint": original.replace(",pending,,,,", ",pending,,,p. 9,", 1),
        "missing row": "".join(lines[:-1]),
    }
    for case, content in broken_cases.items():
        (tmp_path / "human-review-r1.csv").write_text(content, encoding="utf-8")
        assert main(args) == 1, case
    (tmp_path / "human-review-r1.csv").write_text(original, encoding="utf-8")
    assert main(args) == 0

    matrix = tmp_path / "human-review-matrix.csv"
    matrix_text = matrix.read_text(encoding="utf-8")
    matrix.write_text(matrix_text.replace(",not_flagged,", ",flagged,", 1), encoding="utf-8")
    assert main(args) == 1


def test_adding_a_second_reviewer_keeps_the_first(tmp_path: Path):
    base = ["--findings", str(FINDINGS), "--out-dir", str(tmp_path)]
    assert main(base) == 0
    first_record = json.loads((tmp_path / SHEETS_RECORD_FILENAME).read_text(encoding="utf-8"))
    _label_one_cell(tmp_path / "human-review-r1.csv")
    labelled = (tmp_path / "human-review-r1.csv").read_text(encoding="utf-8")

    for reviewers in (["--reviewer", "r2"], ["--reviewer", "r1", "--reviewer", "r2"]):
        assert main([*base, *reviewers]) == 0
        assert (tmp_path / "human-review-r1.csv").read_text(encoding="utf-8") == labelled
        record = json.loads((tmp_path / SHEETS_RECORD_FILENAME).read_text(encoding="utf-8"))
        assert [sheet["reviewer_id"] for sheet in record["sheets"]] == ["r1", "r2"]
        assert record["sheets"][0] == first_record["sheets"][0]
        assert {row["human_label"] for row in _rows((tmp_path / "human-review-r2.csv").read_text())} == {
            "pending"
        }
        assert main([*base, "--check"]) == 0


def test_resolve_run_keeps_recorded_reviewers_and_seed():
    record = {"seed": 7, "sheets": [{"reviewer_id": "r1"}, {"reviewer_id": "r2"}]}

    assert resolve_run(None, None, None) == (["r1"], DEFAULT_SEED)
    assert resolve_run(record, None, None) == (["r1", "r2"], 7)
    assert resolve_run(record, ["r3", "r1"], None) == (["r1", "r2", "r3"], 7)
    assert resolve_run(record, None, 9) == (["r1", "r2"], 9)


def test_every_sheet_has_150_pending_rows():
    outputs = _outputs()
    for name in ("human-review-r1.csv", "human-review-matrix.csv"):
        rows = _rows(outputs[name])
        assert len(rows) == 150
        assert {row["human_label"] for row in rows} == {"pending"}
        for field in REVIEW_FIELDS[1:]:
            assert {row[field] for row in rows} == {""}


def test_annex_labels_and_rule_ids_are_canonical():
    for name in ("human-review-r1.csv", "human-review-matrix.csv"):
        rows = _rows(_outputs()[name])
        for row in rows:
            rule = CANONICAL[row["rule_id"]]
            assert row["annex_item"] == rule.annex_item
            assert row["rule_label"] == rule.label
            assert row["requirement"] == REVIEW_REQUIREMENTS[row["rule_id"]]
        by_rule = {row["rule_id"]: row["annex_item"] for row in rows}
        assert by_rule["ANNEX_I_PART_E_18_CONFLICTS_OF_INTEREST"] == "Annex I, Part E, item 18"
        assert by_rule["ANNEX_I_PART_D_01_ASSET_NAME_ABBREVIATION"] == "Annex I, Part D, item 1"
        assert by_rule["ANNEX_I_PART_D_03_IMPLEMENTATION_PERSONS"] == "Annex I, Part D, item 3"
        assert by_rule["ANNEX_I_PART_F_02_CHARACTERISTICS_FUNCTIONALITY"] == "Annex I, Part F, item 2"
        assert not any("Part B" in row["annex_item"] for row in rows)


def test_requirement_text_covers_exactly_the_study_rules():
    assert set(REVIEW_REQUIREMENTS) == set(CANONICAL)
    assert all(text.strip() and text.isascii() for text in REVIEW_REQUIREMENTS.values())


def test_blinded_sheet_has_no_detector_columns_or_context():
    outputs = _outputs()
    blinded = outputs["human-review-r1.csv"]

    assert _header(blinded) == list(BLINDED_FIELDS)
    assert not any("detector" in column or "confidence" in column for column in _header(blinded))
    contexts = {
        row["detector_context"]
        for row in _rows(outputs["human-review-matrix.csv"])
        if row["detector_context"]
    }
    assert contexts
    assert not any(context in blinded for context in contexts)
    for marker in ("not_flagged", "flagged"):
        assert marker not in blinded


def test_blinded_sheet_is_identical_whatever_the_detector_found():
    findings = _findings()
    no_flags = copy.deepcopy(findings)
    for result in no_flags["results"]:
        result["findings"] = []

    assert _outputs(findings)["human-review-r1.csv"] == _outputs(no_flags)["human-review-r1.csv"]
    assert _outputs(findings)["human-review-matrix.csv"] != _outputs(no_flags)["human-review-matrix.csv"]


def test_rows_are_shuffled_within_each_document_only():
    findings = _findings()
    document_order = [result["study_doc_id"] for result in findings["results"]]
    rule_order = [rule.rule_id for rule in STUDY_RULES]
    rows = _rows(_outputs(findings)["human-review-r1.csv"])

    blocks = [rows[index : index + len(rule_order)] for index in range(0, len(rows), len(rule_order))]
    assert [block[0]["study_doc_id"] for block in blocks] == document_order
    for block in blocks:
        assert len({row["study_doc_id"] for row in block}) == 1
        assert sorted(row["rule_id"] for row in block) == sorted(rule_order)
    assert any([row["rule_id"] for row in block] != rule_order for block in blocks)

    matrix = _rows(_outputs(findings)["human-review-matrix.csv"])
    assert [row["rule_id"] for row in matrix[: len(rule_order)]] == rule_order


def test_seed_and_reviewer_change_the_order_and_are_recorded():
    base = _outputs()["human-review-r1.csv"]
    other_seed = _outputs(seed=DEFAULT_SEED + 1)["human-review-r1.csv"]
    two = _outputs(reviewers=["r1", "r2"])

    assert other_seed != base
    assert sorted(other_seed.splitlines()) == sorted(base.splitlines())
    assert two["human-review-r1.csv"] == base
    assert two["human-review-r2.csv"] != base
    record = json.loads(two[SHEETS_RECORD_FILENAME])
    assert record["seed"] == DEFAULT_SEED
    assert [sheet["file"] for sheet in record["sheets"]] == ["human-review-r1.csv", "human-review-r2.csv"]
    assert record["rows_per_sheet"] == 150


def test_matrix_carries_the_detector_outcomes_of_the_findings_file():
    findings = _findings()
    flagged = {
        (result["study_doc_id"], finding["rule_id"]): finding["confidence"]
        for result in findings["results"]
        for finding in result["findings"]
    }
    rows = _rows(_outputs(findings)["human-review-matrix.csv"])

    assert _header(_outputs(findings)["human-review-matrix.csv"]) == list(MATRIX_FIELDS)
    assert set(DETECTOR_FIELDS) <= set(MATRIX_FIELDS)
    assert sum(row["detector_status"] == "flagged" for row in rows) == len(flagged)
    for row in rows:
        key = (row["study_doc_id"], row["rule_id"])
        assert row["detector_status"] == ("flagged" if key in flagged else "not_flagged")
        assert row["detector_confidence"] == flagged.get(key, "")


def test_keeps_labelled_sheets_and_refuses_to_reshape_them(tmp_path: Path):
    outputs = _outputs()
    write_review_sheets(outputs, tmp_path)
    sheet = tmp_path / "human-review-r1.csv"
    _label_one_cell(sheet)

    # Same cells and row order: the labelled sheet is kept, the rest is rewritten.
    written = write_review_sheets(outputs, tmp_path)
    assert sheet not in written
    assert ",present," in sheet.read_text(encoding="utf-8")

    # A new seed would reorder the labelled sheet: refused, nothing written.
    reordered = _outputs(seed=DEFAULT_SEED + 1)
    with pytest.raises(ReviewContentError):
        write_review_sheets(reordered, tmp_path)
    args = ["--findings", str(FINDINGS), "--out-dir", str(tmp_path), "--seed", str(DEFAULT_SEED + 1)]
    assert main(args) == 3
    assert ",present," in sheet.read_text(encoding="utf-8")

    assert main([*args, "--force"]) == 0
    assert ",present," not in sheet.read_text(encoding="utf-8")


def test_refuses_to_change_detector_columns_of_a_matrix_with_notes(tmp_path: Path):
    findings = _findings()
    write_review_sheets(_outputs(findings), tmp_path)
    matrix = tmp_path / "human-review-matrix.csv"
    lines = matrix.read_text(encoding="utf-8").splitlines(keepends=True)
    lines[1] = lines[1].rstrip("\n") + "note\n"
    matrix.write_text("".join(lines), encoding="utf-8")

    no_flags = copy.deepcopy(findings)
    for result in no_flags["results"]:
        result["findings"] = []
    with pytest.raises(ReviewContentError):
        write_review_sheets(_outputs(no_flags), tmp_path)
    assert matrix.read_text(encoding="utf-8").splitlines()[1].endswith("note")


def test_cli_writes_then_checks_clean(tmp_path: Path):
    args = ["--findings", str(FINDINGS), "--out-dir", str(tmp_path)]
    assert main([*args, "--check"]) == 1
    assert main(args) == 0
    assert main([*args, "--check"]) == 0
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "human-review-matrix.csv",
        "human-review-r1.csv",
        SHEETS_RECORD_FILENAME,
    ]


def test_rejects_findings_that_disagree_with_study_rules():
    findings = _findings()
    unknown = copy.deepcopy(findings)
    unknown["results"][1]["findings"][0]["rule_id"] = "ANNEX_I_PART_B_01_ASSET_NAME_ABBREVIATION"
    wrong_part = copy.deepcopy(findings)
    wrong_part["rules"][7]["annex_item"] = "Annex I, Part A"
    wrong_count = copy.deepcopy(findings)
    wrong_count["results"][0]["rules_checked"] = 12

    for broken in (unknown, wrong_part, wrong_count):
        with pytest.raises(ValueError):
            _outputs(broken)


def test_rejects_unsafe_reviewer_ids():
    for reviewer in ("", "R1", "../r1", "r1.csv"):
        with pytest.raises(ValueError):
            _outputs(reviewers=[reviewer])
