import csv
import io
import json
import runpy
import sys
from datetime import date
from pathlib import Path

import pytest

from micar_linter.review_validation import (
    SCHEMA_VERSION,
    detector_cells,
    main,
    matrix_mismatches,
    summarize_rows,
)

STUDY = Path(__file__).resolve().parents[1] / "studies" / "2026-07-title-ii-annex-i-whitepaper-study"

# Synthetic reviewer fields for in-memory fixtures. No row below describes a real document.
REVIEWED = {
    "reviewer_id": "reviewer-a",
    "reviewed_at": "2026-10-14",
    "source_pinpoint": "synthetic section 1",
}


def _row(detector_status, human_label, **fields):
    return {"detector_status": detector_status, "human_label": human_label, **fields}


def test_summary_excludes_unresolved_labels_from_metrics():
    rows = [
        {"detector_status": "flagged", "human_label": "missing"},
        {"detector_status": "flagged", "human_label": "present"},
        {"detector_status": "not_flagged", "human_label": "missing"},
        {"detector_status": "not_flagged", "human_label": "present"},
        {"detector_status": "flagged", "human_label": "uncertain"},
        {"detector_status": "not_flagged", "human_label": "pending"},
    ]

    summary = summarize_rows(rows)

    assert summary["confusion_matrix"] == {"tp": 1, "fp": 1, "fn": 1, "tn": 1}
    assert summary["metrics"]["precision"] == 0.5
    assert summary["metrics"]["recall"] == 0.5
    assert summary["metrics"]["f1"] == 0.5
    assert summary["rows_pending"] == 1
    assert summary["publication_ready"] is False


def test_all_complete_rows_are_publication_ready():
    summary = summarize_rows(
        [
            _row("flagged", "missing", **REVIEWED),
            _row("not_flagged", "present", **REVIEWED),
        ]
    )

    assert summary["protocol_gaps"] == []
    assert summary["publication_ready"] is True
    assert summary["completion_rate"] == 1.0


def test_metrics_follow_the_protocol_confusion_matrix():
    rows = [
        _row("flagged", "missing", **REVIEWED),
        _row("flagged", "missing", **REVIEWED),
        _row("flagged", "present", **REVIEWED),
        _row("not_flagged", "missing", **REVIEWED),
        _row("not_flagged", "missing", **REVIEWED),
        _row("not_flagged", "present", **REVIEWED),
        _row("not_flagged", "present", **REVIEWED),
        _row("not_flagged", "extraction_failure", **REVIEWED, review_note="synthetic scan, text layer empty"),
        _row("flagged", "not_applicable", **REVIEWED, review_note="synthetic exemption note"),
    ]

    summary = summarize_rows(rows)

    assert summary["confusion_matrix"] == {"tp": 2, "fp": 1, "fn": 2, "tn": 2}
    assert summary["metrics"] == {"precision": 0.666667, "recall": 0.5, "f1": 0.571429, "evaluable_rows": 7}
    assert summary["label_counts"]["extraction_failure"] == 1
    assert summary["label_counts"]["not_applicable"] == 1
    assert summary["publication_ready"] is True


def test_f1_follows_the_count_formula_when_no_flag_is_confirmed():
    # review-protocol.md does not define F1. The module computes 2tp / (2tp + fp + fn), which is
    # 0 / 2 here, and records the formula in metric_note rather than presenting it as the protocol's.
    summary = summarize_rows(
        [
            _row("flagged", "present", **REVIEWED),
            _row("not_flagged", "missing", **REVIEWED),
        ]
    )

    assert summary["metrics"]["precision"] == 0.0
    assert summary["metrics"]["recall"] == 0.0
    assert summary["metrics"]["f1"] == 0.0
    assert "2tp / (2tp + fp + fn)" in summary["metric_note"]
    assert "does not define F1" in summary["metric_note"]


def test_summary_states_its_schema_and_what_publication_ready_leaves_unchecked():
    summary = summarize_rows([_row("flagged", "missing", **REVIEWED)])

    assert summary["schema_version"] == SCHEMA_VERSION == "micar-study-human-validation.v2"
    assert summary["publication_ready"] is True
    scope = summary["publication_ready_scope"]
    for unchecked in (
        "adjudication (item 3)",
        "(item 5)",
        "(item 6)",
        "ESMA's Title II CSV",
        "not sufficient",
    ):
        assert unchecked in scope


def test_metrics_stay_null_without_a_denominator():
    summary = summarize_rows([_row("not_flagged", "present", **REVIEWED)])

    assert summary["metrics"] == {"precision": None, "recall": None, "f1": None, "evaluable_rows": 1}


def test_labelled_rows_without_protocol_fields_block_publication():
    rows = [
        _row("flagged", "missing", study_doc_id="SYN-001", rule_id="SYNTHETIC_RULE"),
        _row(
            "not_flagged",
            "present",
            reviewer_id="reviewer-a",
            reviewed_at="14.10.2026",
            source_pinpoint="p. 3",
        ),
        _row("not_flagged", "uncertain", reviewer_id="reviewer-a", reviewed_at="2026-10-14"),
        _row(
            "flagged",
            "missing",
            reviewer_id="reviewer-a",
            reviewed_at="2026-10-14",
            review_note="inspected all",
        ),
    ]

    summary = summarize_rows(rows)

    assert summary["rows_pending"] == 0
    assert summary["publication_ready"] is False
    assert summary["rows_with_protocol_gaps"] == 3
    gaps = {gap["row"]: gap for gap in summary["protocol_gaps"]}
    assert gaps[2]["study_doc_id"] == "SYN-001"
    assert gaps[2]["problems"] == [
        "reviewer_id is empty",
        "reviewed_at is not a date in the form YYYY-MM-DD, such as 2026-10-14",
        "'missing' needs a source_pinpoint or a review_note",
    ]
    assert gaps[3]["problems"] == ["reviewed_at is not a date in the form YYYY-MM-DD, such as 2026-10-14"]
    assert gaps[4]["problems"] == ["'uncertain' needs a review_note explaining it"]
    # The gaps do not change the arithmetic; they only block publication.
    assert summary["confusion_matrix"] == {"tp": 2, "fp": 0, "fn": 0, "tn": 1}


def test_present_needs_a_pinpoint_while_missing_accepts_a_note():
    # The 'present' label definition asks for a recorded pinpoint; gate item 2 lets an
    # explanation stand in only where no pinpoint can show an absence.
    rows = [
        _row(
            "not_flagged", "present", reviewer_id="reviewer-a", reviewed_at="2026-10-14", review_note="looked"
        ),
        _row(
            "flagged",
            "missing",
            reviewer_id="reviewer-a",
            reviewed_at="2026-10-14",
            review_note="searched every section of the synthetic document",
        ),
    ]

    summary = summarize_rows(rows)

    assert [(gap["row"], gap["problems"]) for gap in summary["protocol_gaps"]] == [
        (2, ["'present' needs a source_pinpoint"])
    ]
    assert summary["publication_ready"] is False


@pytest.mark.parametrize(
    "value",
    [
        "14.10.2026",
        "2026-10-14 10:00",
        "2026-10-14T10:00",
        "2026-287",
        "20261014",
        "2026-02-30",
        "\uff12\uff10\uff12\uff16-10-14",
    ],
)
def test_review_date_must_be_a_yyyy_mm_dd_calendar_date(value):
    summary = summarize_rows(
        [_row("flagged", "missing", **{**REVIEWED, "reviewed_at": value})], today=date(2026, 10, 14)
    )

    assert summary["protocol_gaps"][0]["problems"] == [
        "reviewed_at is not a date in the form YYYY-MM-DD, such as 2026-10-14"
    ]


def test_review_date_lies_between_the_detector_run_and_today():
    dates = ["2026-07-05", "2026-07-06", "2026-07-07", "2026-10-13", "2026-10-14", "2026-10-15", "2099-01-01"]
    rows = [_row("flagged", "missing", **{**REVIEWED, "reviewed_at": value}) for value in dates]

    summary = summarize_rows(rows, today=date(2026, 10, 14), not_before=date(2026, 7, 6))

    assert [(gap["row"], gap["problems"]) for gap in summary["protocol_gaps"]] == [
        (2, ["reviewed_at 2026-07-05 is earlier than the detector run (2026-07-06)"]),
        (7, ["reviewed_at 2026-10-15 is later than today (2026-10-14)"]),
        (8, ["reviewed_at 2099-01-01 is later than today (2026-10-14)"]),
    ]


def test_summary_does_not_read_the_clock_without_today():
    # The same rows give the same result on any machine: summarize_rows reads no clock, and only
    # the command supplies today's date.
    rows = [_row("flagged", "missing", **{**REVIEWED, "reviewed_at": "2099-01-01"})]

    assert summarize_rows(rows)["protocol_gaps"] == []
    assert summarize_rows(rows, today=date(2026, 10, 14))["protocol_gaps"][0]["problems"] == [
        "reviewed_at 2099-01-01 is later than today (2026-10-14)"
    ]


def test_pending_rows_need_no_reviewer_fields():
    summary = summarize_rows([_row("flagged", ""), _row("not_flagged", "pending")])

    assert summary["label_counts"]["pending"] == 2
    assert summary["protocol_gaps"] == []
    assert summary["publication_ready"] is False


def test_summary_carries_the_single_review_disclosure():
    # Two reviewer identifiers on two different rows: still one review per row.
    summary = summarize_rows(
        [
            _row("flagged", "missing", **REVIEWED),
            _row("not_flagged", "present", **{**REVIEWED, "reviewer_id": "reviewer-b"}),
        ]
    )

    assert summary["reviewers_recorded"] == 2
    disclosure = summary["review_disclosure"]
    assert disclosure.startswith("Each of the 2 labelled rows records one reviewer and one final label")
    assert "2 distinct reviewer identifiers" in disclosure
    assert "does not show that any row was reviewed twice" in disclosure
    assert "single-reviewed" in disclosure


def test_disclosure_does_not_claim_a_reviewer_for_a_row_without_one():
    # Two labelled rows, one without reviewer_id, must not be described as each recording a
    # reviewer, and the count of one takes a singular verb.
    summary = summarize_rows(
        [
            _row("flagged", "missing", **REVIEWED),
            _row("not_flagged", "present", **{**REVIEWED, "reviewer_id": ""}),
        ]
    )

    disclosure = summary["review_disclosure"]
    assert "records one reviewer and one final label" not in disclosure
    assert disclosure.startswith(
        "Each of the 2 labelled rows records one final label and at most one reviewer; "
        "1 of them records a reviewer; the rows carry 1 distinct reviewer identifier."
    )
    assert summary["publication_ready"] is False


def test_disclosure_claims_no_review_while_every_row_is_pending():
    summary = summarize_rows([_row("flagged", "pending"), _row("not_flagged", "")])

    assert summary["reviewers_recorded"] == 0
    assert summary["review_disclosure"] == "No row has a final label yet."


def test_unknown_labels_fail_closed():
    with pytest.raises(ValueError, match="unsupported human_label 'Present'"):
        summarize_rows([_row("flagged", "Present", **REVIEWED)])


def test_require_complete_exits_2_on_an_all_pending_matrix(tmp_path, capsys):
    matrix = tmp_path / "matrix.csv"
    matrix.write_text(
        "study_doc_id,rule_id,detector_status,human_label\nSYN-001,SYNTHETIC_RULE,flagged,pending\n",
        encoding="utf-8",
    )
    out = tmp_path / "summary.json"

    assert main(["--matrix", str(matrix), "--out", str(out), "--require-complete"]) == 2

    summary = json.loads(out.read_text(encoding="utf-8"))
    assert summary["metrics"]["precision"] is None
    assert summary["metrics"]["recall"] is None
    assert (
        "not publication-ready: 1 pending row, 0 labelled rows with protocol gaps" in capsys.readouterr().err
    )


def test_summary_reads_a_matrix_saved_with_a_byte_order_mark(tmp_path, capsys):
    # A byte-order mark from a spreadsheet save must not hide study_doc_id in the gap report.
    matrix = tmp_path / "matrix.csv"
    matrix.write_bytes(
        "\ufeffstudy_doc_id,rule_id,detector_status,human_label\r\n"
        "SYN-001,SYNTHETIC_RULE,flagged,missing\r\n".encode("utf-8")
    )
    out = tmp_path / "summary.json"

    assert main(["--matrix", str(matrix), "--out", str(out), "--require-complete"]) == 2

    err = capsys.readouterr().err
    assert "not publication-ready: 0 pending rows, 1 labelled row with protocol gaps" in err
    assert "row 2 SYN-001 SYNTHETIC_RULE: reviewer_id is empty" in err


# A synthetic detector output with one flagged cell, the cell _write_matrix writes.
ONE_CELL_FINDINGS = {
    "generated_at": "2026-07-06T07:00:00+00:00",
    "rules": [{"rule_id": "SYNTHETIC_RULE"}],
    "results": [{"study_doc_id": "SYN-001", "findings": [{"rule_id": "SYNTHETIC_RULE"}]}],
}


def _write_matrix(path, reviewed_at):
    path.write_text(
        "study_doc_id,rule_id,detector_status,human_label,reviewer_id,reviewed_at,source_pinpoint\n"
        f"SYN-001,SYNTHETIC_RULE,flagged,missing,reviewer-a,{reviewed_at},synthetic section 1\n",
        encoding="utf-8",
    )


def test_summary_command_checks_the_detector_run_date_with_findings(tmp_path, capsys):
    # A correction made in the matrix after the merge is checked only here, so with --findings the
    # command must refuse a review date before the detector run.
    matrix = tmp_path / "matrix.csv"
    _write_matrix(matrix, "2020-01-01")
    findings = tmp_path / "findings.json"
    findings.write_text(json.dumps(ONE_CELL_FINDINGS), encoding="utf-8")
    out = tmp_path / "summary.json"
    args = ["--matrix", str(matrix), "--out", str(out), "--require-complete"]

    assert main(args, today=date(2026, 10, 14)) == 0
    assert main([*args, "--findings", str(findings)], today=date(2026, 10, 14)) == 2

    assert "reviewed_at 2020-01-01 is earlier than the detector run (2026-07-06)" in capsys.readouterr().err
    assert json.loads(out.read_text(encoding="utf-8"))["publication_ready"] is False


def test_summary_command_refuses_findings_without_a_run_date(tmp_path, capsys):
    matrix = tmp_path / "matrix.csv"
    _write_matrix(matrix, "2026-10-14")
    findings = tmp_path / "findings.json"
    findings.write_text(json.dumps({**ONE_CELL_FINDINGS, "generated_at": ""}), encoding="utf-8")
    out = tmp_path / "summary.json"

    assert main(["--matrix", str(matrix), "--out", str(out), "--findings", str(findings)]) == 1

    err = capsys.readouterr().err
    assert f"cannot read {findings}: generated_at '' does not start with a YYYY-MM-DD date" in err
    assert not out.exists()


def test_summary_command_refuses_a_matrix_that_does_not_match_the_findings(tmp_path, capsys):
    # A matrix filtered or edited in a spreadsheet would give metrics over the wrong cells.
    matrix = tmp_path / "matrix.csv"
    matrix.write_text(
        "study_doc_id,rule_id,detector_status,human_label\n"
        "SYN-001,SYNTHETIC_RULE_A,not_flagged,pending\n"
        "SYN-001,SYNTHETIC_RULE_A,not_flagged,pending\n"
        "SYN-002,SYNTHETIC_RULE_A,not_flagged,pending\n"
        "SYN-003,SYNTHETIC_RULE_A,not_flagged,pending\n",
        encoding="utf-8",
    )
    findings = tmp_path / "findings.json"
    findings.write_text(json.dumps(SYNTHETIC_FINDINGS), encoding="utf-8")
    out = tmp_path / "summary.json"

    assert main(["--matrix", str(matrix), "--out", str(out), "--findings", str(findings)]) == 1

    err = capsys.readouterr().err
    assert "the matrix does not match" in err
    for problem in (
        "SYN-001 SYNTHETIC_RULE_A: detector_status 'not_flagged', the findings give 'flagged'",
        "SYN-001 SYNTHETIC_RULE_A: more than one row",
        "SYN-003 SYNTHETIC_RULE_A: not a cell of the findings",
        "SYN-001 SYNTHETIC_RULE_B: missing from the matrix",
        "SYN-002 SYNTHETIC_RULE_B: missing from the matrix",
    ):
        assert f"  {problem}\n" in err
    assert "SYN-002 SYNTHETIC_RULE_A" not in err
    assert not out.exists()


def _builder():
    return runpy.run_path(str(STUDY / "scripts" / "build_review_matrix.py"))


def _cell(label, **fields):
    return {
        "human_label": label,
        "reviewer_id": "",
        "reviewed_at": "",
        "source_pinpoint": "",
        "review_note": "",
        **fields,
    }


def test_merge_copies_completed_blinded_labels_into_the_matrix_rows():
    builder = _builder()
    keys = [("SYN-001", "SYNTHETIC_RULE_A"), ("SYN-001", "SYNTHETIC_RULE_B"), ("SYN-002", "SYNTHETIC_RULE_A")]
    detector = {keys[0]: "flagged", keys[1]: "not_flagged", keys[2]: "flagged"}
    blinded = {
        keys[0]: _cell("missing", **REVIEWED),
        keys[1]: _cell("missing", **REVIEWED),
        keys[2]: _cell("present", **REVIEWED),
    }

    merged = builder["merge_blinded_cells"](keys, {}, blinded)
    matrix_rows = [{"detector_status": detector[key], **merged[key]} for key in keys]
    summary = summarize_rows(matrix_rows)

    assert merged == blinded
    assert summary["confusion_matrix"] == {"tp": 1, "fp": 1, "fn": 1, "tn": 0}
    assert summary["publication_ready"] is True


def test_merge_refuses_while_blinded_cells_are_pending():
    builder = _builder()
    keys = [("SYN-001", "SYNTHETIC_RULE_A"), ("SYN-001", "SYNTHETIC_RULE_B")]

    with pytest.raises(ValueError, match="1 of 2 blinded cells are still pending"):
        builder["merge_blinded_cells"](keys, {}, {keys[0]: _cell("present", **REVIEWED)})


def test_merge_refuses_blinded_cells_that_miss_protocol_fields():
    # Gaps are caught before the merge, so they are fixed in the blinded sheet and never
    # need an edit to the unblinded matrix.
    builder = _builder()
    keys = [("SYN-001", "SYNTHETIC_RULE_A"), ("SYN-001", "SYNTHETIC_RULE_B")]
    blinded = {
        keys[0]: _cell("missing", reviewer_id="reviewer-a", reviewed_at="2026-10-14"),
        keys[1]: _cell("Present", **REVIEWED),
    }

    with pytest.raises(ValueError) as refused:
        builder["merge_blinded_cells"](keys, {}, blinded)
    message = str(refused.value)
    assert "SYN-001 SYNTHETIC_RULE_A: 'missing' needs a source_pinpoint or a review_note" in message
    assert "SYN-001 SYNTHETIC_RULE_B: unsupported human_label 'Present'" in message


def test_merge_refuses_to_overwrite_a_different_matrix_value():
    builder = _builder()
    key = ("SYN-001", "SYNTHETIC_RULE_A")
    blinded = {key: _cell("missing", **REVIEWED)}
    adjudicated = {key: _cell("present", **REVIEWED, review_note="synthetic adjudication")}

    with pytest.raises(ValueError, match="different reviewer values for: SYN-001 SYNTHETIC_RULE_A"):
        builder["merge_blinded_cells"]([key], adjudicated, blinded)
    assert builder["merge_blinded_cells"]([key], dict(blinded), blinded) == blinded


def test_merge_refuses_a_review_date_before_the_detector_run():
    builder = _builder()
    key = ("SYN-001", "SYNTHETIC_RULE_A")
    blinded = {key: _cell("missing", **{**REVIEWED, "reviewed_at": "2026-07-05"})}

    with pytest.raises(ValueError, match=r"earlier than the detector run \(2026-07-06\)"):
        builder["merge_blinded_cells"](
            [key], {}, blinded, today=date(2026, 10, 14), not_before=date(2026, 7, 6)
        )


def test_sheet_reader_rejects_a_semicolon_separated_save():
    builder = _builder()
    sheet = io.StringIO(
        "study_doc_id;rule_id;human_label;reviewer_id;reviewed_at;source_pinpoint;review_note\n"
        "SYN-001;SYNTHETIC_RULE_A;present;reviewer-a;2026-10-14;p. 1;\n"
    )

    with pytest.raises(ValueError, match="save it as comma-separated UTF-8"):
        builder["filled_cells_from"](sheet, "blinded.csv")


def test_sheet_reader_refuses_two_filled_rows_for_one_cell():
    # A spreadsheet edit can duplicate a row; keeping the last one would drop a label silently.
    builder = _builder()
    sheet = io.StringIO(
        "study_doc_id,rule_id,human_label,reviewer_id,reviewed_at,source_pinpoint,review_note\n"
        "SYN-001,SYNTHETIC_RULE_A,present,reviewer-a,2026-10-14,p. 1,\n"
        "SYN-001,SYNTHETIC_RULE_A,missing,reviewer-a,2026-10-14,p. 2,\n"
        "SYN-001,SYNTHETIC_RULE_B,pending,,,,\n"
        "SYN-001,SYNTHETIC_RULE_B,pending,,,,\n"
    )

    with pytest.raises(ValueError, match="more than one filled row for: SYN-001 SYNTHETIC_RULE_A;"):
        builder["filled_cells_from"](sheet, "blinded.csv")


def test_review_sheets_use_the_detector_rule_ids():
    # Regression: the sheets carried rule IDs (e.g. ANNEX_I_PART_A_01_LEGAL_FORM) that the
    # detector output no longer used.
    payload = json.loads((STUDY / "findings-pseudonymous.json").read_text(encoding="utf-8"))
    rule_ids = [rule["rule_id"] for rule in payload["rules"]]
    expected = [(doc["study_doc_id"], rule_id) for doc in payload["results"] for rule_id in rule_ids]
    flagged = {(doc["study_doc_id"], f["rule_id"]) for doc in payload["results"] for f in doc["findings"]}

    for name in ("human-review-matrix.csv", "human-review-blinded.csv"):
        with (STUDY / name).open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        assert [(row["study_doc_id"], row["rule_id"]) for row in rows] == expected, name
        if name == "human-review-matrix.csv":
            assert matrix_mismatches(rows, detector_cells(payload)) == []
            assert {
                (row["study_doc_id"], row["rule_id"]) for row in rows if row["detector_status"] == "flagged"
            } == flagged


# A synthetic detector output for the builder's command-line path. No value describes a real document.
SYNTHETIC_FINDINGS = {
    "generated_at": "2026-07-06T07:00:00+00:00",
    "rules": [
        {"rule_id": "SYNTHETIC_RULE_A", "annex_item": "Synthetic item A"},
        {"rule_id": "SYNTHETIC_RULE_B", "annex_item": "Synthetic item B"},
    ],
    "results": [
        {
            "study_doc_id": "SYN-001",
            "document_hash_sha256": "0" * 64,
            "findings": [
                {
                    "rule_id": "SYNTHETIC_RULE_A",
                    "confidence": "high",
                    "evidence": {"matched_text": "synthetic context"},
                }
            ],
        },
        {"study_doc_id": "SYN-002", "document_hash_sha256": "1" * 64, "findings": []},
    ],
}
SYNTHETIC_KEYS = [
    ("SYN-001", "SYNTHETIC_RULE_A"),
    ("SYN-001", "SYNTHETIC_RULE_B"),
    ("SYN-002", "SYNTHETIC_RULE_A"),
    ("SYN-002", "SYNTHETIC_RULE_B"),
]


def _synthetic_study(tmp_path):
    (tmp_path / "findings-pseudonymous.json").write_text(json.dumps(SYNTHETIC_FINDINGS), encoding="utf-8")
    return tmp_path


def _read_sheet(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _save_blinded_like_a_spreadsheet(study, cells):
    """Write the blinded sheet with a byte-order mark and CRLF line ends."""
    rows = _read_sheet(study / "human-review-blinded.csv")
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), lineterminator="\r\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({**row, **cells.get((row["study_doc_id"], row["rule_id"]), {})})
    (study / "human-review-blinded.csv").write_bytes(("\ufeff" + buffer.getvalue()).encode("utf-8"))


def test_builder_writes_both_sheets_from_the_findings(tmp_path, capsys):
    study = _synthetic_study(tmp_path)

    assert _builder()["main"]([], study_dir=study) == 0

    matrix = _read_sheet(study / "human-review-matrix.csv")
    blinded = _read_sheet(study / "human-review-blinded.csv")
    assert [(row["study_doc_id"], row["rule_id"], row["detector_status"]) for row in matrix] == [
        (*SYNTHETIC_KEYS[0], "flagged"),
        (*SYNTHETIC_KEYS[1], "not_flagged"),
        (*SYNTHETIC_KEYS[2], "not_flagged"),
        (*SYNTHETIC_KEYS[3], "not_flagged"),
    ]
    assert [(row["study_doc_id"], row["rule_id"]) for row in blinded] == SYNTHETIC_KEYS
    assert "detector_status" not in blinded[0] and "detector_context" not in blinded[0]
    assert {row["human_label"] for row in matrix + blinded} == {"pending"}
    assert "wrote 4 rows" in capsys.readouterr().out


def test_builder_merges_a_blinded_sheet_saved_with_bom_and_crlf(tmp_path):
    study = _synthetic_study(tmp_path)
    builder = _builder()
    assert builder["main"]([], study_dir=study) == 0
    labels = ["missing", "present", "present", "missing"]
    _save_blinded_like_a_spreadsheet(
        study, {key: _cell(label, **REVIEWED) for key, label in zip(SYNTHETIC_KEYS, labels, strict=True)}
    )

    assert builder["main"](["--merge-blinded"], study_dir=study, today=date(2026, 10, 14)) == 0

    matrix = _read_sheet(study / "human-review-matrix.csv")
    assert [row["human_label"] for row in matrix] == labels
    assert {row["reviewer_id"] for row in matrix} == {"reviewer-a"}
    summary = summarize_rows(matrix)
    assert summary["confusion_matrix"] == {"tp": 1, "fp": 0, "fn": 1, "tn": 2}
    assert summary["publication_ready"] is True


def _sheet_bytes(study):
    return {
        name: (study / name).read_bytes() for name in ("human-review-matrix.csv", "human-review-blinded.csv")
    }


def test_builder_writes_nothing_when_the_merge_is_refused(tmp_path, capsys):
    study = _synthetic_study(tmp_path)
    builder = _builder()
    assert builder["main"]([], study_dir=study) == 0
    _save_blinded_like_a_spreadsheet(study, {SYNTHETIC_KEYS[0]: _cell("missing", **REVIEWED)})
    before = _sheet_bytes(study)
    capsys.readouterr()

    assert builder["main"](["--merge-blinded"], study_dir=study, today=date(2026, 10, 14)) == 1

    assert _sheet_bytes(study) == before
    assert "merge stopped: 3 of 4 blinded cells are still pending" in capsys.readouterr().err


def test_builder_refuses_a_review_date_before_the_synthetic_run(tmp_path, capsys):
    study = _synthetic_study(tmp_path)
    builder = _builder()
    assert builder["main"]([], study_dir=study) == 0
    cells = {key: _cell("missing", **REVIEWED) for key in SYNTHETIC_KEYS}
    cells[SYNTHETIC_KEYS[2]] = _cell("missing", **{**REVIEWED, "reviewed_at": "2026-07-05"})
    _save_blinded_like_a_spreadsheet(study, cells)
    before = _sheet_bytes(study)
    capsys.readouterr()

    assert builder["main"](["--merge-blinded"], study_dir=study, today=date(2026, 10, 14)) == 1

    assert _sheet_bytes(study) == before
    err = capsys.readouterr().err
    assert "later than today" not in err
    assert (
        "SYN-002 SYNTHETIC_RULE_A: reviewed_at 2026-07-05 is earlier than the detector run (2026-07-06)"
        in err
    )


def test_builder_merge_refuses_findings_without_a_run_date(tmp_path, capsys):
    # An unreadable generated_at stops the merge rather than dropping the lower bound.
    study = _synthetic_study(tmp_path)
    builder = _builder()
    assert builder["main"]([], study_dir=study) == 0
    (study / "findings-pseudonymous.json").write_text(
        json.dumps({**SYNTHETIC_FINDINGS, "generated_at": "unknown"}), encoding="utf-8"
    )
    _save_blinded_like_a_spreadsheet(study, {key: _cell("missing", **REVIEWED) for key in SYNTHETIC_KEYS})
    before = _sheet_bytes(study)
    capsys.readouterr()

    assert builder["main"](["--merge-blinded"], study_dir=study, today=date(2026, 10, 14)) == 1

    assert _sheet_bytes(study) == before
    assert (
        "merge stopped: generated_at 'unknown' does not start with a YYYY-MM-DD date"
        in capsys.readouterr().err
    )


def test_builder_explains_a_merge_run_without_the_package(tmp_path, capsys, monkeypatch):
    # Plain `python3` has no micar_linter; the merge says how to run it instead of a traceback.
    study = _synthetic_study(tmp_path)
    builder = _builder()
    assert builder["main"]([], study_dir=study) == 0
    before = _sheet_bytes(study)
    capsys.readouterr()
    monkeypatch.setitem(sys.modules, "micar_linter", None)
    monkeypatch.setitem(sys.modules, "micar_linter.review_validation", None)

    assert builder["main"](["--merge-blinded"], study_dir=study) == 1

    assert _sheet_bytes(study) == before
    err = capsys.readouterr().err
    assert "merge stopped: the merge needs the micar_linter package" in err
    assert "uv run python" in err
