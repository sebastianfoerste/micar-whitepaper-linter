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


def test_committed_sheets_equal_generator_output():
    outputs = build_review_sheets(
        _findings(),
        findings_sha256=hashlib.sha256(FINDINGS.read_bytes()).hexdigest(),
    )

    assert check_review_sheets(outputs, STUDY) == []
    assert not (STUDY / "human-review-blinded.csv").exists()


def test_generator_output_is_deterministic():
    assert _outputs() == _outputs()
    assert main(["--findings", str(FINDINGS), "--out-dir", str(STUDY), "--check"]) == 0


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


def test_committed_summary_matches_the_committed_matrix():
    with (STUDY / "human-review-matrix.csv").open(newline="", encoding="utf-8") as handle:
        recomputed = summarize_rows(csv.DictReader(handle))
    committed = json.loads((STUDY / "human-review-summary.json").read_text(encoding="utf-8"))

    assert committed == recomputed
    assert committed["rows_total"] == 150
    assert committed["rows_completed"] == 0
    assert committed["publication_ready"] is False


def test_refuses_to_overwrite_review_content(tmp_path: Path):
    outputs = _outputs()
    write_review_sheets(outputs, tmp_path)
    sheet = tmp_path / "human-review-r1.csv"
    sheet.write_text(sheet.read_text(encoding="utf-8").replace(",pending,", ",present,", 1), encoding="utf-8")

    with pytest.raises(ReviewContentError):
        write_review_sheets(outputs, tmp_path)
    assert main(["--findings", str(FINDINGS), "--out-dir", str(tmp_path)]) == 3
    assert ",present," in sheet.read_text(encoding="utf-8")

    assert main(["--findings", str(FINDINGS), "--out-dir", str(tmp_path), "--force"]) == 0
    assert ",present," not in sheet.read_text(encoding="utf-8")


def test_refuses_to_overwrite_a_filled_note(tmp_path: Path):
    outputs = _outputs()
    write_review_sheets(outputs, tmp_path)
    matrix = tmp_path / "human-review-matrix.csv"
    lines = matrix.read_text(encoding="utf-8").splitlines(keepends=True)
    lines[1] = lines[1].rstrip("\n") + "note\n"
    matrix.write_text("".join(lines), encoding="utf-8")

    with pytest.raises(ReviewContentError):
        write_review_sheets(outputs, tmp_path)


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
