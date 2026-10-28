"""micar-review-summary (schema v2). Every label here is synthetic and exists only in memory or
under tmp_path; the committed study files are checked in test_study_consistency.py."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from micar_linter import review_validation
from micar_linter.review_validation import (
    SUMMARY_SCHEMA,
    StudyContext,
    internal_detail,
    load_context,
    plan_phrase,
    plan_status,
    summarize_rows,
    summary_json,
)

RULES = [f"RULE_{index:02d}" for index in range(1, 6)]


def _row(doc: str, rule: str, status: str, label: str, note: str = "") -> dict[str, str]:
    return {
        "study_doc_id": doc,
        "document_hash_sha256": hashlib.sha256(doc.encode()).hexdigest(),
        "rule_id": rule,
        "detector_status": status,
        "human_label": label,
        "review_note": note,
    }


def _document(doc: str, labels: list[tuple[str, str]], note: str = "") -> list[dict[str, str]]:
    """One synthetic document: (detector_status, human_label) per rule."""
    return [_row(doc, rule, status, label, note) for rule, (status, label) in zip(RULES, labels, strict=True)]


F, N = "flagged", "not_flagged"
# A synthetic five-rule document: one TP, one FP, one FN, two TN.
MIXED = [(F, "missing"), (F, "present"), (N, "missing"), (N, "present"), (N, "present")]


def _summary(rows, context=None, replicates=300):
    return summarize_rows(rows, context, replicates=replicates)


def test_summary_excludes_unresolved_labels_from_metrics():
    rows = _document(
        "WP-001", [(F, "missing"), (F, "present"), (N, "missing"), (N, "present"), (F, "uncertain")]
    )
    rows.append(_row("WP-001", "RULE_06", N, "pending"))

    summary = _summary(rows)
    primary = summary["analyses"]["primary"]

    assert summary["schema_version"] == SUMMARY_SCHEMA
    assert primary["confusion_matrix"] == {"tp": 1, "fp": 1, "fn": 1, "tn": 1}
    assert primary["metrics"]["precision"]["estimate"] == 0.5
    assert primary["metrics"]["recall"]["estimate"] == 0.5
    assert primary["metrics"]["f1"]["estimate"] == 0.5
    assert (primary["evaluable_cells"], primary["excluded_cells"], primary["pending_cells"]) == (4, 1, 1)
    assert summary["rows_pending"] == 1
    assert summary["publication_ready"] is False


def test_all_complete_rows_are_publication_ready():
    summary = _summary(_document("WP-001", MIXED))
    assert summary["publication_ready"] is True
    assert summary["completion_rate"] == 1.0
    assert summary["documents_total"] == 1
    assert summary["rules_per_document"] == 5


def test_primary_excludes_wp007_and_s1_includes_it():
    rows = _document("WP-001", MIXED) + _document("WP-007", [(F, "missing")] * 5) + _document("WP-002", MIXED)
    summary = _summary(rows)
    analyses = summary["analyses"]

    assert analyses["primary"]["documents"] == ["WP-001", "WP-002"]
    assert analyses["S1"]["documents"] == ["WP-001", "WP-002", "WP-007"]
    assert analyses["primary"]["confusion_matrix"] == {"tp": 2, "fp": 2, "fn": 2, "tn": 4}
    assert analyses["S1"]["confusion_matrix"] == {"tp": 7, "fp": 2, "fn": 2, "tn": 4}
    excluded = summary["exclusions"]["primary"]
    assert [item["study_doc_id"] for item in excluded] == ["WP-007"]
    # Complete: the WP-007 flag count that the analysis plan asks for is reported, with the total.
    assert excluded[0]["detector_flags"] == 5
    assert excluded[0]["detector_flags_total"] == 9
    # Per-rule counts for the primary set only, in matrix order. S1 differs from it only by
    # WP-007, so a second per-rule table would give WP-007's cells; it goes to --internal-out.
    assert "per_rule" not in analyses["S1"]
    assert [item["rule_id"] for item in analyses["primary"]["per_rule"]] == RULES
    assert analyses["primary"]["per_rule"][0] == {
        "rule_id": "RULE_01",
        "cells": 2,
        "label_counts": {
            "present": 0,
            "missing": 2,
            "not_applicable": 0,
            "uncertain": 0,
            "extraction_failure": 0,
            "pending": 0,
        },
        "tp": 2,
        "fp": 0,
        "fn": 0,
        "tn": 0,
    }


def test_no_detector_outcome_while_any_cell_is_pending():
    rows = _document("WP-001", MIXED) + _document("WP-007", [(F, "pending")] * 5)
    summary = _summary(rows)
    excluded = summary["exclusions"]["primary"][0]
    assert excluded["detector_flags"] is None
    assert "withheld while any cell is pending" in excluded["detector_flags_reason"]
    assert excluded["detector_flags_total"] is None
    detail = internal_detail(rows)
    by_doc = {item["study_doc_id"]: item for item in detail["documents"]}
    assert by_doc["WP-007"]["detector_flags"] is None
    assert by_doc["WP-001"]["detector_flags"] == 2
    assert detail["S1_per_rule"]["documents"] == ["WP-001", "WP-007"]
    assert [item["rule_id"] for item in detail["S1_per_rule"]["per_rule"]] == RULES


def test_undefined_reasons_do_not_read_like_findings_while_cells_are_pending():
    pending = _summary(_document("WP-001", [(F, "pending"), (N, "pending")] + [(N, "present")] * 3))
    metrics = pending["analyses"]["primary"]["metrics"]
    recall = metrics["recall"]["undefined_reason"]
    assert recall == "TP + FN = 0 so far: no cell is labelled missing yet (2 of 5 cells in this set pending)"
    assert "identified no gap" not in json.dumps(pending)
    assert metrics["recall"]["document_cluster_bootstrap"]["undefined_reason"] == (
        f"point estimate undefined ({recall}); not resampled"
    )
    assert metrics["f1"]["undefined_reason"].startswith("2TP + FP + FN = 0 so far")
    # Complete, and the reviewer found no gap: now the reason may say so.
    complete = _summary(_document("WP-001", [(N, "present")] * 5))["analyses"]["primary"]["metrics"]
    assert complete["recall"]["undefined_reason"] == (
        "TP + FN = 0: no cell is labelled missing (the reviewer identified no gap)"
    )


def test_f1_is_undefined_only_when_its_denominator_is_zero():
    # [hand] F1 = 2TP / (2TP + FP + FN). TP = 0 with FP = 1 and FN = 1: 0 / 2 = 0, although
    # precision and recall are both 0 and their harmonic mean is 0/0.
    zero = _summary(_document("WP-001", [(F, "present"), (N, "missing"), (N, "present"), (N, "present"), (N, "present")]))
    f1 = zero["analyses"]["primary"]["metrics"]["f1"]
    assert (f1["estimate"], f1["numerator"], f1["denominator"], f1["undefined_reason"]) == (0.0, 0, 2, None)
    # TP = FP = 0 and FN = 1: precision is undefined, F1 is 0 / 1 = 0.
    no_flags = _summary(_document("WP-001", [(N, "missing")] + [(N, "present")] * 4))
    metrics = no_flags["analyses"]["primary"]["metrics"]
    assert metrics["precision"]["estimate"] is None
    assert metrics["f1"]["estimate"] == 0.0
    # [hand] TP = 2, FP = 1, FN = 3: 4 / 8 = 0.5, the harmonic mean of 2/3 and 2/5.
    rows = _document("WP-001", [(F, "missing"), (F, "missing"), (F, "present"), (N, "missing"), (N, "missing")])
    rows += _document("WP-002", [(N, "missing"), (N, "present"), (N, "present"), (N, "present"), (N, "present")])
    assert _summary(rows)["analyses"]["primary"]["metrics"]["f1"]["estimate"] == 0.5


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
        "adopted on 2026-11-02; pre-registration commit not named in the plan (signing order, step 5)"
    )
    # A SHA on that line is still read, although the signing order records it outside the plan.
    named = plan_status(
        adopted_text.replace("not recorded in this file (signing order, step 5)", "`ABC1234`")
    )
    assert named["preregistration_commit"] == "abc1234"
    contradictory = plan_status(BANNER_DRAFT.replace("[reviewer name], on [YYYY-MM-DD]", "A. Reviewer, on 2026-11-02"))
    assert contradictory["status"] == "unknown"
    assert "is filled in" in contradictory["reason"]
    assert plan_status("# Analysis plan\n")["status"] == "unknown"
    assert plan_status(None)["reason"] == "no study directory was read"

    # The status reaches the summary's definitions and the WP-007 ground; nothing is hard-coded.
    rows = _document("WP-001", MIXED) + _document("WP-007", MIXED)
    for plan, definitions, ground in (
        (draft, "(DRAFT, not adopted)", "(DRAFT, not adopted)"),
        (named, "(adopted on 2026-11-02; pre-registration commit abc1234)", "(adopted on 2026-11-02)"),
        (plan_status(None), "(adoption status unknown: no study directory was read)", "(adoption status unknown)"),
    ):
        summary = _summary(rows, StudyContext(plan=plan))
        assert summary["settings"]["definitions"] == f"analysis-plan.md sections 7 to 10 {definitions}"
        assert summary["settings"]["analysis_plan"] == plan
        assert summary["exclusions"]["primary"][0]["ground"] == f"analysis-plan.md section 5 {ground}"
        assert "DRAFT" not in summary["metric_note"]


def test_calibration_document_is_excluded_from_every_set():
    rows = (
        _document("WP-001", MIXED)
        + _document("WP-012", MIXED, note="calibration")
        + _document("WP-007", MIXED)
        + _document("WP-004", MIXED)
    )
    summary = _summary(rows)
    assert summary["exclusions"]["calibration_document"]["study_doc_id"] == "WP-012"
    assert "--internal-out" in summary["exclusions"]["calibration_document"]["note"]
    assert summary["analyses"]["primary"]["documents"] == ["WP-001", "WP-004"]
    assert summary["analyses"]["S1"]["documents"] == ["WP-001", "WP-004", "WP-007"]
    assert summary["analyses"]["primary"]["cells"] == 10


def test_ambiguous_calibration_marking_stops_the_run():
    partial = _document("WP-001", MIXED)
    partial[0]["review_note"] = "Calibration: P1 applied"
    with pytest.raises(ValueError, match="some but not all cells"):
        _summary(partial + _document("WP-002", MIXED))
    # The word inside another word does not count.
    other = _document("WP-001", MIXED)
    other[0]["review_note"] = "recalibration-free note"
    assert _summary(other)["exclusions"]["calibration_document"]["study_doc_id"] is None
    two = _document("WP-001", MIXED, note="calibration") + _document("WP-002", MIXED, note="calibration")
    with pytest.raises(ValueError, match="more than one document"):
        _summary(two)


def test_uncertain_bounds_s3_and_s4():
    rows = _document(
        "WP-001", [(F, "uncertain"), (F, "missing"), (N, "uncertain"), (N, "present"), (N, "present")]
    )
    analyses = _summary(rows)["analyses"]
    assert analyses["primary"]["confusion_matrix"] == {"tp": 1, "fp": 0, "fn": 0, "tn": 2}
    assert analyses["S3"]["uncertain_counted_as"] == "missing"
    assert analyses["S3"]["confusion_matrix"] == {"tp": 2, "fp": 0, "fn": 1, "tn": 2}
    assert analyses["S4"]["confusion_matrix"] == {"tp": 1, "fp": 1, "fn": 0, "tn": 3}
    assert analyses["S5"]["computed"] is False
    assert analyses["S5"]["undefined_reason"]


def test_zero_denominators_are_null_with_a_reason_never_nan():
    # Only true negatives: precision and recall are 0/0.
    rows = _document("WP-001", [(N, "present")] * 5)
    summary = _summary(rows)
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
    summary_json(summary)  # allow_nan=False: raises if any NaN slipped in
    # An empty matrix.
    empty = _summary([])
    assert empty["rows_total"] == 0
    assert empty["completion_rate"] is None
    assert empty["publication_ready"] is False
    summary_json(empty)


def test_headline_falls_back_to_wilson_when_replicates_are_dropped():
    # Nine documents; only WP-001 has flagged cells. A replicate misses it with probability
    # (8/9)^9 = 0.35, above the draft 10% limit, so Wilson is the headline.
    rows = _document("WP-001", MIXED)
    for number in range(2, 11):
        if number != 7:
            rows += _document(
                f"WP-{number:03d}",
                [(N, "present"), (N, "missing"), (N, "present"), (N, "present"), (N, "present")],
            )
    precision = _summary(rows, replicates=2000)["analyses"]["primary"]["metrics"]["precision"]
    assert precision["document_cluster_bootstrap"]["exceeds_dropped_limit"] is True
    assert precision["headline"]["method"] == "wilson"
    assert "more than 10%" in precision["headline"]["reason"]
    # Recall has a denominator in every document: nothing is dropped, and the wider interval wins.
    recall = _summary(rows, replicates=2000)["analyses"]["primary"]["metrics"]["recall"]
    assert recall["document_cluster_bootstrap"]["dropped"] == 0
    wilson = recall["wilson"]["upper"] - recall["wilson"]["lower"]
    bootstrap = recall["document_cluster_bootstrap"]["upper"] - recall["document_cluster_bootstrap"]["lower"]
    expected = "document_cluster_bootstrap" if round(bootstrap, 6) > round(wilson, 6) else "wilson"
    assert recall["headline"]["method"] == expected


def test_settings_record_the_pre_registered_parameters():
    settings = summarize_rows(_document("WP-001", MIXED))["settings"]
    assert settings["bootstrap"]["replicates"] == 10_000
    assert settings["bootstrap"]["seed"] == 20261014
    assert settings["wilson_z"] == 1.959964
    assert settings["confidence_level"] == 0.95
    assert settings["max_dropped_fraction"] == 0.1
    assert settings["primary_exclusions"] == ["WP-007"]


def test_offeror_sensitivity_analyses():
    rows = []
    for doc in ("WP-001", "WP-003", "WP-004", "WP-005", "WP-011", "WP-012"):
        rows += _document(doc, MIXED)
    offerors = {
        "WP-001": ("Example Offeror One GmbH", ""),
        "WP-003": ("Example Offeror Two S.A.", ""),
        "WP-004": ("Example  offeror two s.a.", ""),  # spacing and case are normalised
        "WP-005": ("Example Offeror Two S.A.", ""),
        "WP-011": ("Example Offeror Three AG", ""),
        "WP-012": ("Example Offeror Three AG", ""),
    }
    analyses = _summary(rows, StudyContext(offerors=offerors))["analyses"]
    assert analyses["S2a"]["offeror_clusters"] == 3
    assert analyses["S2a"]["metrics"]["precision"]["offeror_cluster_bootstrap"]["clusters"] == 3
    assert analyses["S2b"]["documents"] == ["WP-001", "WP-003", "WP-011"]

    unknown = _summary(rows)["analyses"]
    assert "metrics" not in unknown["S2a"]
    assert unknown["S2b"]["undefined_reason"] == "no study directory was read"

    with pytest.raises(ValueError, match=r"not in source-manifest\.json"):
        _summary(rows, StudyContext(offerors={"WP-001": ("A", "")}))
    wrong_hash = {doc: (name, "0" * 64) for doc, (name, _) in offerors.items()}
    with pytest.raises(ValueError, match=r"differs from source-manifest\.json"):
        _summary(rows, StudyContext(offerors=wrong_hash))


def _study_dir(tmp_path: Path, reviewers: dict[str, list[dict[str, str]]], findings: dict) -> Path:
    """A synthetic study directory with a generation record, sheets and a findings file."""
    raw = json.dumps(findings).encode()
    (tmp_path / "findings.json").write_bytes(raw)
    sheets = []
    for reviewer, rows in reviewers.items():
        name = f"human-review-{reviewer}.csv"
        header = "study_doc_id,rule_id,human_label\n"
        body = "".join(f"{row['study_doc_id']},{row['rule_id']},{row['human_label']}\n" for row in rows)
        (tmp_path / name).write_text(header + body, encoding="utf-8")
        sheets.append({"reviewer_id": reviewer, "file": name})
    record = {
        "findings_file": "findings.json",
        "findings_sha256": hashlib.sha256(raw).hexdigest(),
        "sheets": sheets,
    }
    (tmp_path / "human-review-sheets.json").write_text(json.dumps(record), encoding="utf-8")
    return tmp_path


FINDINGS = {"schema": "synthetic.v1", "digest": "d" * 64, "generated_at": "2026-07-06T00:00:00+00:00"}


def test_detector_identity_comes_from_the_findings_file_or_the_analysis_plan(tmp_path: Path):
    rows = _document("WP-001", MIXED)
    study = _study_dir(tmp_path, {"r1": rows}, FINDINGS)
    detector = _summary(rows, load_context(study))["detector"]
    assert detector["findings_file"] == "findings.json"
    assert detector["findings_digest"] == "d" * 64
    assert detector["commit"] is None
    assert "no analysis-plan.md" in detector["commit_status"]

    plan = study / "analysis-plan.md"
    plan.write_text("| Detector | code; generating commit: [SHA, see step 0.4] |\n", encoding="utf-8")
    assert _summary(rows, load_context(study))["detector"]["commit"] is None
    plan.write_text("| Detector | code; generating commit: `abc1234` |\n", encoding="utf-8")
    detector = _summary(rows, load_context(study))["detector"]
    assert detector["commit"] == "abc1234"
    assert detector["commit_source"] == "analysis-plan.md, section 2, Detector row"

    study = _study_dir(tmp_path, {"r1": rows}, {**FINDINGS, "detector_commit": "fedcba9876"})
    assert _summary(rows, load_context(study))["detector"]["commit"] == "fedcba9876"

    (study / "findings.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="hashes to"):
        load_context(study)


def test_agreement_with_two_reviewers(tmp_path: Path):
    final = _document("WP-001", MIXED) + _document("WP-002", MIXED)
    second = [dict(row) for row in final]
    second[0]["human_label"] = "present"  # one synthetic disagreement
    study = _study_dir(tmp_path, {"r1": final, "r2": second}, FINDINGS)
    agreement = _summary(final, load_context(study))["agreement"]
    assert agreement["status"] == "computed"
    assert agreement["double_reviewed"] is True
    (pair,) = agreement["pairs"]
    assert pair["reviewers"] == ["r1", "r2"]
    assert pair["cells"] == 10
    assert pair["disagreements"] == 1
    assert pair["all_labels"]["raw_agreement"] == 0.9
    assert pair["present_missing"]["cells"] == 10

    second[1]["human_label"] = "pending"
    study = _study_dir(tmp_path, {"r1": final, "r2": second}, FINDINGS)
    incomplete = _summary(final, load_context(study))["agreement"]
    assert incomplete["status"] == "incomplete"
    assert incomplete["pairs"] == []
    assert "r2 1" in incomplete["reason"]

    # Before the merge the matrix is pending: nothing is compared, whatever the sheets hold, so
    # committing a labelled sheet leaves the summary unchanged.
    pending_matrix = [{**row, "human_label": "pending"} for row in final]
    awaiting = _summary(pending_matrix, load_context(study))["agreement"]
    assert awaiting["status"] == "awaiting_merge"
    assert awaiting["pairs"] == []

    single = _summary(final, load_context(_study_dir(tmp_path, {"r1": final}, FINDINGS)))["agreement"]
    assert single["status"] == "single_reviewer"
    assert single["double_reviewed"] is False


def test_cli_exit_codes_and_internal_output(tmp_path: Path, capsys):
    matrix = tmp_path / "matrix.csv"
    rows = _document("WP-001", MIXED) + _document("WP-002", [(F, "pending"), *MIXED[1:]])
    header = list(rows[0])
    matrix.write_text(
        ",".join(header) + "\n" + "".join(",".join(row[name] for name in header) + "\n" for row in rows),
        encoding="utf-8",
    )
    out, internal = tmp_path / "summary.json", tmp_path / "human-review-internal.json"
    args = ["--matrix", str(matrix), "--out", str(out)]
    assert review_validation.main([*args, "--internal-out", str(internal)]) == 0
    assert review_validation.main([*args, "--require-complete"]) == 2
    summary = json.loads(out.read_text(encoding="utf-8"))
    assert summary["rows_pending"] == 1
    assert "WP-001" not in json.dumps(summary["analyses"]["primary"]["per_rule"])
    assert "per_rule" not in summary["analyses"]["S1"]
    detail = json.loads(internal.read_text(encoding="utf-8"))
    assert [item["study_doc_id"] for item in detail["documents"]] == ["WP-001", "WP-002"]
    assert detail["S1_per_rule"]["documents"] == ["WP-001", "WP-002"]
    assert detail["offerors"] is None

    matrix.write_text(matrix.read_text(encoding="utf-8").replace("pending", "maybe"), encoding="utf-8")
    out.unlink()
    assert review_validation.main(args) == 1
    assert "unsupported human_label 'maybe'" in capsys.readouterr().err
    assert not out.exists()
