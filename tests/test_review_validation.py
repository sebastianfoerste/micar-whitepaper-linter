import csv
import hashlib
import io
import json
import runpy
import sys
from datetime import date
from pathlib import Path

import pytest

from micar_linter.review_validation import (
    AGREEMENT_CATEGORIES,
    ALLOWED_LABELS,
    BOOTSTRAP_REPLICATES,
    BOOTSTRAP_SEED,
    EXCLUDED_LABELS,
    NOTE_REQUIRED_LABELS,
    SCHEMA_VERSION,
    AnalysisContext,
    detector_cells,
    internal_detail,
    load_analysis_context,
    main,
    matrix_mismatches,
    plan_phrase,
    plan_status,
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


# Analyses of the draft analysis plan (--analyses), ported from the earlier summary rewrite as
# additions. Every document, rule, reviewer and label below is synthetic and exists only in memory
# or under tmp_path; tests/test_study_consistency.py reads the committed study files.
ANALYSIS_RULES = [f"SYNTHETIC_RULE_{index:02d}" for index in range(1, 6)]
FLAG, NO_FLAG = "flagged", "not_flagged"
# A synthetic five-rule document: one TP, one FP, one FN and two TN.
MIXED = [
    (FLAG, "missing"),
    (FLAG, "present"),
    (NO_FLAG, "missing"),
    (NO_FLAG, "present"),
    (NO_FLAG, "present"),
]
TODAY = date(2026, 10, 30)


def _analysis_row(doc, rule, status, label, note=""):
    return {
        "study_doc_id": doc,
        "document_hash_sha256": hashlib.sha256(doc.encode()).hexdigest(),
        "rule_id": rule,
        "detector_status": status,
        "human_label": label,
        "review_note": note,
    }


def _document(doc, labels, note=""):
    """One synthetic document: (detector_status, human_label) for each rule."""
    return [
        _analysis_row(doc, rule, status, label, note)
        for rule, (status, label) in zip(ANALYSIS_RULES, labels, strict=True)
    ]


def _analyses(rows, replicates=300, **context):
    return summarize_rows(rows, analyses=AnalysisContext(replicates=replicates, **context))


def test_analyses_add_keys_after_the_summary_and_change_none():
    rows = _document("SYN-001", MIXED) + _document("SYN-002", [(FLAG, "pending"), *MIXED[1:]])
    plain = summarize_rows(rows)
    summary = _analyses(iter(rows))

    assert list(summary)[: len(plain)] == list(plain)
    assert {key: summary[key] for key in plain} == plain
    assert list(summary)[len(plain) :] == ["detector", "settings", "exclusions", "analyses", "agreement"]
    assert summary["schema_version"] == SCHEMA_VERSION
    assert set(EXCLUDED_LABELS) == NOTE_REQUIRED_LABELS
    assert set(AGREEMENT_CATEGORIES) == ALLOWED_LABELS - {"pending"}


def test_analyses_exclude_unresolved_labels_from_metrics():
    rows = _document(
        "SYN-001",
        [
            (FLAG, "missing"),
            (FLAG, "present"),
            (NO_FLAG, "missing"),
            (NO_FLAG, "present"),
            (FLAG, "uncertain"),
        ],
    )
    rows.append(_analysis_row("SYN-001", "SYNTHETIC_RULE_06", NO_FLAG, "pending"))

    summary = _analyses(rows)
    primary = summary["analyses"]["primary"]

    assert primary["confusion_matrix"] == summary["confusion_matrix"] == {"tp": 1, "fp": 1, "fn": 1, "tn": 1}
    assert primary["metrics"]["precision"]["estimate"] == 0.5
    assert primary["metrics"]["recall"]["estimate"] == 0.5
    assert primary["metrics"]["specificity"]["estimate"] == 0.5
    assert primary["metrics"]["f1"]["estimate"] == summary["metrics"]["f1"] == 0.5
    assert (primary["evaluable_cells"], primary["excluded_cells"], primary["pending_cells"]) == (4, 1, 1)
    assert summary["publication_ready"] is False


def test_primary_exclusions_come_only_from_the_command_line():
    rows = (
        _document("SYN-001", MIXED)
        + _document("SYN-007", [(FLAG, "missing")] * 5)
        + _document("SYN-002", MIXED)
    )
    # By default nothing is excluded: the primary set is S1.
    default = _analyses(rows)
    assert default["analyses"]["primary"]["documents"] == default["analyses"]["S1"]["documents"]
    assert default["exclusions"]["primary"] == []
    assert default["settings"]["primary_exclusions"] == []

    summary = _analyses(rows, primary_exclusions=("SYN-007",))
    analyses = summary["analyses"]
    assert analyses["primary"]["documents"] == ["SYN-001", "SYN-002"]
    assert analyses["S1"]["documents"] == ["SYN-001", "SYN-002", "SYN-007"]
    assert analyses["primary"]["confusion_matrix"] == {"tp": 2, "fp": 2, "fn": 2, "tn": 4}
    assert analyses["S1"]["confusion_matrix"] == {"tp": 7, "fp": 2, "fn": 2, "tn": 4}
    (excluded,) = summary["exclusions"]["primary"]
    assert excluded["study_doc_id"] == "SYN-007"
    # Complete: the excluded document's share of the flags, which the analysis plan asks for.
    assert (excluded["detector_flags"], excluded["detector_flags_total"]) == (5, 9)
    assert summary["settings"]["primary_exclusions"] == ["SYN-007"]
    # Per-rule counts for the primary set only, in matrix order. S1 differs from it by one
    # document, so a second per-rule table would give that document's cells; it goes to --internal-out.
    assert "per_rule" not in analyses["S1"]
    assert [item["rule_id"] for item in analyses["primary"]["per_rule"]] == ANALYSIS_RULES
    assert analyses["primary"]["per_rule"][0] == {
        "rule_id": "SYNTHETIC_RULE_01",
        "cells": 2,
        "label_counts": {
            "extraction_failure": 0,
            "missing": 2,
            "not_applicable": 0,
            "pending": 0,
            "present": 0,
            "uncertain": 0,
        },
        "tp": 2,
        "fp": 0,
        "fn": 0,
        "tn": 0,
    }
    with pytest.raises(ValueError, match="--primary-exclude SYN-009: not a document of the matrix"):
        _analyses(rows, primary_exclusions=("SYN-009",))


def test_no_detector_outcome_while_any_cell_is_pending():
    rows = _document("SYN-001", MIXED) + _document("SYN-007", [(FLAG, "pending")] * 5)
    context = AnalysisContext(replicates=300, primary_exclusions=("SYN-007",))
    summary = summarize_rows(rows, analyses=context)
    (excluded,) = summary["exclusions"]["primary"]
    assert excluded["detector_flags"] is None
    assert excluded["detector_flags_total"] is None
    assert "withheld while any cell is pending" in excluded["detector_flags_reason"]
    detail = internal_detail(rows, context)
    by_doc = {item["study_doc_id"]: item for item in detail["documents"]}
    assert by_doc["SYN-007"]["detector_flags"] is None
    assert by_doc["SYN-001"]["detector_flags"] == 2
    assert detail["S1_per_rule"]["documents"] == ["SYN-001", "SYN-007"]
    assert [item["rule_id"] for item in detail["S1_per_rule"]["per_rule"]] == ANALYSIS_RULES


def test_undefined_reasons_do_not_read_like_findings_while_cells_are_pending():
    pending = _analyses(
        _document("SYN-001", [(FLAG, "pending"), (NO_FLAG, "pending")] + [(NO_FLAG, "present")] * 3)
    )
    metrics = pending["analyses"]["primary"]["metrics"]
    recall = metrics["recall"]["undefined_reason"]
    assert recall == "TP + FN = 0 so far: no cell is labelled missing yet (2 of 5 cells in this set pending)"
    assert "identified no gap" not in json.dumps(pending)
    assert metrics["recall"]["document_cluster_bootstrap"]["undefined_reason"] == (
        f"point estimate undefined ({recall}); not resampled"
    )
    assert metrics["f1"]["undefined_reason"] == "precision and recall undefined, so F1 is null (metric_note)"
    # Complete, and the reviewer found no gap: now the reason may say so.
    complete = _analyses(_document("SYN-001", [(NO_FLAG, "present")] * 5))["analyses"]["primary"]["metrics"]
    assert complete["recall"]["undefined_reason"] == (
        "TP + FN = 0: no cell is labelled missing (the reviewer identified no gap)"
    )


def test_analyses_f1_follows_the_summary_rule():
    # [hand] TP = 0, FP = 1, FN = 1: precision 0/1 and recall 0/1 are defined, so F1 is 0/2 = 0.
    zero = _analyses(
        _document(
            "SYN-001",
            [
                (FLAG, "present"),
                (NO_FLAG, "missing"),
                (NO_FLAG, "present"),
                (NO_FLAG, "present"),
                (NO_FLAG, "present"),
            ],
        )
    )
    f1 = zero["analyses"]["primary"]["metrics"]["f1"]
    assert (f1["estimate"], f1["numerator"], f1["denominator"], f1["undefined_reason"]) == (0.0, 0, 2, None)
    assert zero["metrics"]["f1"] == 0.0
    # TP = FP = 0 and FN = 1: precision is null, so F1 is null too (METRIC_NOTE), not 0.
    no_flags = _analyses(_document("SYN-001", [(NO_FLAG, "missing")] + [(NO_FLAG, "present")] * 4))
    metrics = no_flags["analyses"]["primary"]["metrics"]
    assert metrics["precision"]["estimate"] is None
    assert metrics["f1"]["estimate"] is None
    assert metrics["f1"]["undefined_reason"] == "precision undefined, so F1 is null (metric_note)"
    assert no_flags["metrics"]["f1"] is None
    # [hand] TP = 2, FP = 1, FN = 3: 4 / 8 = 0.5, the harmonic mean of 2/3 and 2/5.
    rows = _document(
        "SYN-001",
        [(FLAG, "missing"), (FLAG, "missing"), (FLAG, "present"), (NO_FLAG, "missing"), (NO_FLAG, "missing")],
    )
    rows += _document("SYN-002", [(NO_FLAG, "missing")] + [(NO_FLAG, "present")] * 4)
    assert _analyses(rows)["analyses"]["primary"]["metrics"]["f1"]["estimate"] == 0.5


BANNER_DRAFT = """# Analysis plan

> **DRAFT, not adopted; it reaches `main` as unsigned draft tooling and is adopted there in a separate commit.**
>
> - Adopted by: [reviewer name], on [YYYY-MM-DD]
> - Pre-registration commit: not recorded in this file (signing order, step 5)
"""


def test_plan_status_is_read_from_the_banner():
    draft = plan_status(BANNER_DRAFT)
    assert (draft["status"], draft["adopted_on"], draft["preregistration_commit"]) == ("draft", None, None)
    adopted_text = (
        "# Analysis plan\n\n> - Adopted by: A. Reviewer, on 2026-11-02\n"
        "> - Pre-registration commit: not recorded in this file (signing order, step 5)\n"
    )
    adopted = plan_status(adopted_text)
    assert (adopted["status"], adopted["adopted_on"], adopted["preregistration_commit"]) == (
        "adopted",
        "2026-11-02",
        None,
    )
    assert plan_phrase(adopted) == (
        "adopted on 2026-11-02; pre-registration commit: see the study README (signing order, step 5)"
    )
    # A SHA on that line is still read, although the signing order records it outside the plan.
    named = plan_status(
        adopted_text.replace("not recorded in this file (signing order, step 5)", "`ABC1234`")
    )
    assert named["preregistration_commit"] == "abc1234"
    contradictory = plan_status(
        BANNER_DRAFT.replace("[reviewer name], on [YYYY-MM-DD]", "A. Reviewer, on 2026-11-02")
    )
    assert contradictory["status"] == "unknown"
    assert "is filled in" in contradictory["reason"]
    assert plan_status("# Analysis plan\n")["status"] == "unknown"
    assert plan_status(None)["reason"] == "no analysis plan was given (--analysis-plan)"

    # The status reaches the summary's definitions and the exclusion ground; nothing is hard-coded.
    rows = _document("SYN-001", MIXED) + _document("SYN-007", MIXED)
    for plan, definitions, ground in (
        (draft, "(DRAFT, not adopted)", "(DRAFT, not adopted)"),
        (named, "(adopted on 2026-11-02; pre-registration commit abc1234)", "(adopted on 2026-11-02)"),
        (
            plan_status(None),
            "(adoption status unknown: no analysis plan was given (--analysis-plan))",
            "(adoption status unknown)",
        ),
    ):
        summary = _analyses(rows, plan=plan, primary_exclusions=("SYN-007",))
        assert summary["settings"]["definitions"] == f"analysis-plan.md sections 7 to 10 {definitions}"
        assert summary["settings"]["analysis_plan"] == plan
        assert summary["exclusions"]["primary"][0]["ground"] == (
            f"named with --primary-exclude; the exclusion rule is analysis-plan.md section 5 {ground}"
        )


def test_calibration_document_is_excluded_from_every_set():
    rows = (
        _document("SYN-001", MIXED)
        + _document("SYN-012", MIXED, note="calibration")
        + _document("SYN-007", MIXED)
        + _document("SYN-004", MIXED)
    )
    summary = _analyses(rows, primary_exclusions=("SYN-007",))
    assert summary["exclusions"]["calibration_document"]["study_doc_id"] == "SYN-012"
    assert "--internal-out" in summary["exclusions"]["calibration_document"]["note"]
    assert summary["analyses"]["primary"]["documents"] == ["SYN-001", "SYN-004"]
    assert summary["analyses"]["S1"]["documents"] == ["SYN-001", "SYN-004", "SYN-007"]
    assert summary["analyses"]["primary"]["cells"] == 10
    # The calibration document cannot also be a primary exclusion.
    assert _analyses(rows, primary_exclusions=("SYN-012",))["exclusions"]["primary"] == []


def test_ambiguous_calibration_marking_stops_the_run():
    partial = _document("SYN-001", MIXED)
    partial[0]["review_note"] = "Calibration: P1 applied"
    with pytest.raises(ValueError, match="some but not all cells"):
        _analyses(partial + _document("SYN-002", MIXED))
    # The word inside another word does not count.
    other = _document("SYN-001", MIXED)
    other[0]["review_note"] = "recalibration-free note"
    assert _analyses(other)["exclusions"]["calibration_document"]["study_doc_id"] is None
    two = _document("SYN-001", MIXED, note="calibration") + _document("SYN-002", MIXED, note="calibration")
    with pytest.raises(ValueError, match="more than one document"):
        _analyses(two)


def test_uncertain_bounds_s3_and_s4():
    rows = _document(
        "SYN-001",
        [
            (FLAG, "uncertain"),
            (FLAG, "missing"),
            (NO_FLAG, "uncertain"),
            (NO_FLAG, "present"),
            (NO_FLAG, "present"),
        ],
    )
    analyses = _analyses(rows)["analyses"]
    assert analyses["primary"]["confusion_matrix"] == {"tp": 1, "fp": 0, "fn": 0, "tn": 2}
    assert analyses["S3"]["uncertain_counted_as"] == "missing"
    assert analyses["S3"]["confusion_matrix"] == {"tp": 2, "fp": 0, "fn": 1, "tn": 2}
    assert analyses["S4"]["confusion_matrix"] == {"tp": 1, "fp": 1, "fn": 0, "tn": 3}
    assert analyses["S5"]["computed"] is False
    assert analyses["S5"]["undefined_reason"]


def test_zero_denominators_are_null_with_a_reason_never_nan():
    # Only true negatives: precision and recall are 0/0.
    summary = _analyses(_document("SYN-001", [(NO_FLAG, "present")] * 5))
    precision = summary["analyses"]["primary"]["metrics"]["precision"]
    assert precision["estimate"] is None
    assert precision["undefined_reason"].startswith("TP + FP = 0")
    assert precision["wilson"] == {
        "lower": None,
        "upper": None,
        "undefined_reason": precision["undefined_reason"],
    }
    assert precision["clopper_pearson"]["lower"] is None
    assert precision["document_cluster_bootstrap"]["lower"] is None
    assert precision["headline"]["method"] is None
    assert summary["analyses"]["primary"]["metrics"]["f1"]["estimate"] is None
    json.dumps(summary, allow_nan=False)  # raises if any NaN slipped in
    empty = _analyses([])
    assert empty["rows_total"] == 0
    assert empty["analyses"]["primary"]["cells"] == 0
    json.dumps(empty, allow_nan=False)


def test_headline_falls_back_to_wilson_when_replicates_are_dropped():
    # Ten documents; only SYN-001 has flagged cells. A replicate misses it with probability
    # (9/10)^10 = 0.35, above the draft 10% limit, so Wilson is the headline.
    rows = _document("SYN-001", MIXED)
    for number in range(2, 11):
        rows += _document(
            f"SYN-{number:03d}",
            [
                (NO_FLAG, "present"),
                (NO_FLAG, "missing"),
                (NO_FLAG, "present"),
                (NO_FLAG, "present"),
                (NO_FLAG, "present"),
            ],
        )
    metrics = _analyses(rows, replicates=2000)["analyses"]["primary"]["metrics"]
    precision = metrics["precision"]
    assert precision["document_cluster_bootstrap"]["exceeds_dropped_limit"] is True
    assert precision["headline"]["method"] == "wilson"
    assert "more than 10%" in precision["headline"]["reason"]
    # Recall has a denominator in every document: nothing is dropped, and the wider interval wins.
    recall = metrics["recall"]
    assert recall["document_cluster_bootstrap"]["dropped"] == 0
    wilson = recall["wilson"]["upper"] - recall["wilson"]["lower"]
    bootstrap = recall["document_cluster_bootstrap"]["upper"] - recall["document_cluster_bootstrap"]["lower"]
    expected = "document_cluster_bootstrap" if round(bootstrap, 6) > round(wilson, 6) else "wilson"
    assert recall["headline"]["method"] == expected


def test_settings_record_the_pre_registered_parameters():
    settings = summarize_rows(_document("SYN-001", MIXED), analyses=AnalysisContext())["settings"]
    assert settings["bootstrap"]["replicates"] == BOOTSTRAP_REPLICATES == 10_000
    assert settings["bootstrap"]["seed"] == BOOTSTRAP_SEED == 20261014
    assert settings["wilson_z"] == 1.959964
    assert settings["confidence_level"] == 0.95
    assert settings["max_dropped_fraction"] == 0.1
    assert settings["primary_exclusions"] == []
    assert "null when precision or recall is null" in settings["f1"]


def test_offeror_sensitivity_analyses(tmp_path):
    rows = []
    for doc in ("SYN-001", "SYN-003", "SYN-004", "SYN-005", "SYN-011", "SYN-012"):
        rows += _document(doc, MIXED)
    offerors = {
        "SYN-001": ("Example Offeror One GmbH", ""),
        "SYN-003": ("Example Offeror Two S.A.", ""),
        "SYN-004": ("Example  offeror two s.a.", ""),  # spacing and case are normalised
        "SYN-005": ("Example Offeror Two S.A.", ""),
        "SYN-011": ("Example Offeror Three AG", ""),
        "SYN-012": ("Example Offeror Three AG", ""),
    }
    analyses = _analyses(rows, offerors=offerors, offerors_reason=None)["analyses"]
    assert analyses["S2a"]["offeror_clusters"] == 3
    assert analyses["S2a"]["metrics"]["precision"]["offeror_cluster_bootstrap"]["clusters"] == 3
    assert analyses["S2b"]["documents"] == ["SYN-001", "SYN-003", "SYN-011"]

    unknown = _analyses(rows)["analyses"]
    assert "metrics" not in unknown["S2a"]
    assert (
        unknown["S2b"]["undefined_reason"]
        == "no source manifest was given (--manifest), so the offerors are unknown"
    )

    with pytest.raises(ValueError, match="not in the source manifest"):
        _analyses(rows, offerors={"SYN-001": ("A", "")}, offerors_reason=None)
    wrong_hash = {doc: (name, "0" * 64) for doc, (name, _) in offerors.items()}
    with pytest.raises(ValueError, match="differs from the source manifest"):
        _analyses(rows, offerors=wrong_hash, offerors_reason=None)

    # load_analysis_context reads the offerors from a manifest's entries.
    findings = tmp_path / "findings.json"
    findings.write_text(json.dumps({"generated_at": "2026-07-06T00:00:00+00:00"}), encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    entries = [{"study_doc_id": doc, "offeror_or_issuer": name} for doc, (name, _) in offerors.items()]
    manifest.write_text(json.dumps({"entries": entries}), encoding="utf-8")
    context = load_analysis_context(findings, manifest=manifest, replicates=300)
    assert summarize_rows(rows, analyses=context)["analyses"]["S2a"]["offeror_clusters"] == 3


def test_detector_identity_comes_from_the_findings_file_or_the_analysis_plan(tmp_path):
    findings = {"schema": "synthetic.v1", "digest": "d" * 64, "generated_at": "2026-07-06T00:00:00+00:00"}
    path = tmp_path / "findings.json"
    path.write_text(json.dumps(findings), encoding="utf-8")
    detector = load_analysis_context(path).detector
    assert detector["findings_file"] == "findings.json"
    assert detector["findings_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert (detector["findings_schema"], detector["findings_digest"]) == ("synthetic.v1", "d" * 64)
    assert detector["commit"] is None
    assert "no analysis plan was given (--analysis-plan)" in detector["commit_status"]

    plan = tmp_path / "analysis-plan.md"
    plan.write_text("| Detector | code; detector commit: [SHA, see step 0.4] |\n", encoding="utf-8")
    assert load_analysis_context(path, analysis_plan=plan).detector["commit"] is None
    plan.write_text("| Detector | code; detector commit: `abc1234` |\n", encoding="utf-8")
    detector = load_analysis_context(path, analysis_plan=plan).detector
    assert detector["commit"] == "abc1234"
    assert detector["commit_source"] == "analysis-plan.md, section 2, Detector row"

    path.write_text(json.dumps({**findings, "detector_commit": "fedcba9876"}), encoding="utf-8")
    assert load_analysis_context(path, analysis_plan=plan).detector["commit"] == "fedcba9876"


def _reviewed(label, reviewer="reviewer-a", when="2026-10-14"):
    return {
        "human_label": label,
        "reviewer_id": reviewer,
        "reviewed_at": when,
        "source_pinpoint": "synthetic section 1",
        "review_note": "" if label == "present" else "synthetic note",
    }


def _fill(path, cells):
    """Write values into the rows of a sheet the builder wrote, by cell."""
    rows = _read_sheet(path)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({**row, **cells.get((row["study_doc_id"], row["rule_id"]), {})})
    path.write_text(buffer.getvalue(), encoding="utf-8")


def _two_reviews(tmp_path, *, merge_first=False):
    """A synthetic study with a complete first review and a second review that differs on one cell."""
    study = _synthetic_study(tmp_path)
    builder = _builder()

    def run(*args):
        return builder["main"](list(args), study_dir=study, today=TODAY)

    assert run() == 0
    first = {key: _reviewed("present") for key in SYNTHETIC_KEYS}
    first[SYNTHETIC_KEYS[0]] = _reviewed("missing")
    _fill(study / "human-review-blinded.csv", first)
    if merge_first:
        assert run("--merge-blinded") == 0
    assert run("--second-sheet", "--second-all") == 0
    second = {
        key: {**cell, "reviewer_id": "reviewer-b", "reviewed_at": "2026-10-21"} for key, cell in first.items()
    }
    second[SYNTHETIC_KEYS[0]] = _reviewed("present", "reviewer-b", "2026-10-21")
    _fill(study / "human-review-second.csv", second)
    return study, run


def _agreement(study, *, adjudication=True):
    path = study / "human-review-adjudication.csv"
    context = load_analysis_context(
        study / "findings-pseudonymous.json",
        second_review=study / "human-review-second.csv",
        adjudication=path if adjudication and path.exists() else None,
        replicates=50,
    )
    matrix = _read_sheet(study / "human-review-matrix.csv")
    return summarize_rows(matrix, today=TODAY, analyses=context)["agreement"]


DECIDED = {
    "final_label": "missing",
    "adjudicated_by": "reviewer-a+reviewer-b",
    "adjudicated_at": "2026-10-25",
    "adjudication_reason": "synthetic reason",
}


def test_agreement_compares_the_two_reviews_after_the_adjudicated_merge(tmp_path):
    study, run = _two_reviews(tmp_path)
    assert _agreement(study, adjudication=False)["status"] == "awaiting_merge"
    assert _analyses(_document("SYN-001", MIXED))["agreement"]["status"] == "not_given"

    assert run("--disagreements") == 0
    _fill(study / "human-review-adjudication.csv", {SYNTHETIC_KEYS[0]: DECIDED})
    assert run("--merge-blinded") == 0
    agreement = _agreement(study)

    assert agreement["status"] == "computed"
    assert (agreement["second_review_file"], agreement["adjudication_file"]) == (
        "human-review-second.csv",
        "human-review-adjudication.csv",
    )
    assert agreement["cells_double_reviewed"] == 4
    assert (agreement["scope"]["cells"], agreement["scope"]["flagged_cells"]) == (4, 1)
    (pair,) = agreement["pairs"]
    assert (pair["first_reviewers"], pair["second_reviewers"]) == (["reviewer-a"], ["reviewer-b"])
    # The first review of the adjudicated cell comes from the adjudication file, not the matrix.
    assert (pair["cells"], pair["disagreements"]) == (4, 1)
    assert pair["all_labels"]["raw_agreement"] == 0.75
    assert pair["present_missing"]["cells"] == 4
    assert agreement["adjudication"] == {
        "status": "complete",
        "disagreements": 1,
        "adjudicated": 1,
        "reason": None,
    }

    # The matrix holds an adjudicated cell, so the summary needs the file the merge used.
    with pytest.raises(
        ValueError, match="the matrix holds an adjudicated cell, but no adjudication file was given"
    ):
        _agreement(study, adjudication=False)


def test_adjudication_state_follows_the_decisions(tmp_path):
    # The first review was merged before the second sheet was built, so the matrix holds it.
    study, run = _two_reviews(tmp_path, merge_first=True)
    agreement = _agreement(study)
    assert agreement["status"] == "computed"
    assert agreement["pairs"][0]["disagreements"] == 1
    assert agreement["adjudication"]["status"] == "not_given"

    assert run("--disagreements") == 0
    state = _agreement(study)["adjudication"]
    assert (state["status"], state["disagreements"], state["adjudicated"]) == ("pending", 1, 0)

    _fill(study / "human-review-adjudication.csv", {SYNTHETIC_KEYS[0]: DECIDED})
    state = _agreement(study)["adjudication"]
    assert state["status"] == "not_merged"
    assert "--merge-blinded" in state["reason"]

    _fill(
        study / "human-review-adjudication.csv",
        {SYNTHETIC_KEYS[0]: {**DECIDED, "adjudicated_by": "reviewer-a"}},
    )
    with pytest.raises(ValueError, match="names only one of the two reviewers"):
        _agreement(study)


def test_agreement_waits_for_a_complete_second_review_and_refuses_an_invalid_one(tmp_path):
    study, _run = _two_reviews(tmp_path, merge_first=True)
    second = study / "human-review-second.csv"
    _fill(second, {SYNTHETIC_KEYS[1]: {"human_label": "pending", "reviewer_id": "", "reviewed_at": ""}})
    agreement = _agreement(study)
    assert agreement["status"] == "incomplete"
    assert "1 of 4 second-review cells are still pending" in agreement["reason"]
    assert agreement["pairs"] == []

    _fill(second, {SYNTHETIC_KEYS[1]: _reviewed("present", "reviewer-a", "2026-10-21")})
    with pytest.raises(ValueError, match="also made the first review of this cell"):
        _agreement(study)

    rows = _read_sheet(second)
    rows[1]["study_doc_id"] = "SYN-009"
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    second.write_text(buffer.getvalue(), encoding="utf-8")
    with pytest.raises(ValueError, match="SYN-009 SYNTHETIC_RULE_B is not a cell of the matrix"):
        _agreement(study)


def test_analyses_command_writes_the_internal_file_and_nothing_on_error(tmp_path, capsys):
    study = _synthetic_study(tmp_path)
    assert _builder()["main"]([], study_dir=study) == 0
    matrix, findings = study / "human-review-matrix.csv", study / "findings-pseudonymous.json"
    out, internal = tmp_path / "out" / "summary.json", tmp_path / "out" / "human-review-internal.json"
    args = ["--matrix", str(matrix), "--out", str(out), "--findings", str(findings)]

    assert main(args, today=TODAY) == 0
    plain = json.loads(out.read_text(encoding="utf-8"))
    assert "analyses" not in plain

    assert (
        main([*args, "--analyses", "--replicates", "50", "--internal-out", str(internal)], today=TODAY) == 0
    )
    summary = json.loads(out.read_text(encoding="utf-8"))
    assert {key: summary[key] for key in plain} == plain
    assert summary["detector"]["findings_file"] == "findings-pseudonymous.json"
    assert summary["settings"]["bootstrap"]["replicates"] == 50
    assert "per_rule" not in summary["analyses"]["S1"]
    detail = json.loads(internal.read_text(encoding="utf-8"))
    assert [item["study_doc_id"] for item in detail["documents"]] == ["SYN-001", "SYN-002"]
    assert detail["offerors"] is None
    assert main([*args, "--analyses", "--require-complete"], today=TODAY) == 2

    out.unlink()
    internal.unlink()
    capsys.readouterr()
    assert main([*args, "--analyses", "--primary-exclude", "SYN-009", "--internal-out", str(internal)]) == 1
    assert "the analyses stopped; nothing written: --primary-exclude SYN-009" in capsys.readouterr().err
    assert not out.exists()
    assert not internal.exists()


@pytest.mark.parametrize(
    "extra",
    [
        ["--analyses"],
        ["--manifest", "manifest.json"],
        ["--primary-exclude", "SYN-001"],
        ["--seed", "1"],
        ["--findings", "findings.json", "--internal-out", "internal.json"],
        ["--findings", "findings.json", "--analyses", "--adjudication", "adjudication.csv"],
        ["--findings", "findings.json", "--analyses", "--replicates", "0"],
    ],
)
def test_analysis_options_need_analyses_and_findings(tmp_path, extra):
    with pytest.raises(SystemExit) as exited:
        main(["--matrix", str(tmp_path / "matrix.csv"), "--out", str(tmp_path / "summary.json"), *extra])
    assert exited.value.code == 2
    assert not (tmp_path / "summary.json").exists()
