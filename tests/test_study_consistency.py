"""The committed Title II study files agree with each other, whatever the labelling progress.

JSON is compared as parsed values, never as bytes, so ``0`` and ``0.0`` count as equal. The
renderer (micar-review-render) must refuse while the committed summary is incomplete, and any
figure the study documents quote must equal the JSON it comes from.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from micar_linter import review_render
from micar_linter.review_render import EXIT_OK, EXIT_REFUSED, check_file, refusal_reasons
from micar_linter.review_validation import (
    BOOTSTRAP_REPLICATES,
    BOOTSTRAP_SEED,
    PRIMARY_EXCLUSIONS,
    read_matrix,
    summarize_matrix,
    summary_json,
)

REPO = Path(__file__).resolve().parents[1]
STUDY = REPO / "studies" / "2026-07-title-ii-annex-i-whitepaper-study"
SUMMARY = STUDY / "human-review-summary.json"
MATRIX = STUDY / "human-review-matrix.csv"
FINDINGS = STUDY / "findings-pseudonymous.json"
# Documents in which the study quotes figures.
QUOTING_DOCUMENTS = ("README.md", "findings-summary.md", "limitations.md", "methodology.md")
_PERCENT_CLAIM = re.compile(r"\b(precision|recall)\b[^.\n|]{0,40}?\d+(?:\.\d+)?\s?%", re.IGNORECASE)


def _committed() -> dict:
    return json.loads(SUMMARY.read_text(encoding="utf-8"))


def _findings() -> dict:
    return json.loads(FINDINGS.read_text(encoding="utf-8"))


def _text(name: str) -> str:
    return (STUDY / name).read_text(encoding="utf-8")


def _number(pattern: str, text: str) -> int:
    match = re.search(pattern, text)
    assert match, f"pattern {pattern!r} not found"
    return int(match.group(1))


def test_committed_summary_matches_the_committed_matrix():
    recomputed = summarize_matrix(MATRIX, STUDY)
    assert _committed() == recomputed, (
        "human-review-summary.json is out of date; rerun micar-review-summary (study README, "
        "'Validate against human labels') after changing the matrix, the reviewers or analysis-plan.md"
    )
    # What the writer would produce parses to the same values.
    assert json.loads(summary_json(recomputed)) == _committed()


def test_the_comparison_is_on_parsed_values():
    text = SUMMARY.read_text(encoding="utf-8")
    # Spell every whole-number float as an integer ("0.0" becomes "0"): the bytes differ, the values do not.
    respelled, replaced = re.subn(r"(?<=[:\s\[])(-?\d+)\.0(?=[,\s\]}])", r"\1", text)
    assert replaced, "the summary has no whole-number float to respell"
    assert respelled != text
    assert json.loads(respelled) == summarize_matrix(MATRIX, STUDY)


def test_summary_counts_equal_the_matrix_and_the_sheets_record():
    committed = _committed()
    rows = read_matrix(MATRIX)
    labels = [(row["human_label"] or "pending").strip() or "pending" for row in rows]
    assert committed["rows_total"] == len(rows) == 150
    assert committed["rows_pending"] == labels.count("pending")
    assert committed["rows_completed"] == len(rows) - labels.count("pending")
    assert committed["publication_ready"] is (labels.count("pending") == 0)
    assert committed["documents_total"] == len({row["study_doc_id"] for row in rows}) == 10
    assert committed["rules_per_document"] == len({row["rule_id"] for row in rows}) == 15

    record = json.loads(_text("human-review-sheets.json"))
    detector = committed["detector"]
    assert detector["findings_file"] == record["findings_file"] == FINDINGS.name
    assert (
        detector["findings_sha256"]
        == record["findings_sha256"]
        == hashlib.sha256(FINDINGS.read_bytes()).hexdigest()
    )
    assert detector["findings_digest"] == record["findings_digest"] == _findings()["digest"]
    assert detector["findings_generated_at"] == _findings()["generated_at"]
    assert committed["reviewers"] == [sheet["reviewer_id"] for sheet in record["sheets"]]


def test_renderer_refuses_while_the_committed_summary_is_incomplete(tmp_path: Path):
    committed = _committed()
    reasons = refusal_reasons(committed)
    if committed["rows_pending"] or not committed["publication_ready"]:
        assert reasons
        out = tmp_path / "rendered.md"
        assert review_render.main(["--summary", str(SUMMARY), "--out", str(out)]) == EXIT_REFUSED
        assert not out.exists()
    if committed["detector"]["commit"] is None:
        assert any("detector commit is not recorded" in reason for reason in reasons)


@pytest.mark.parametrize("name", QUOTING_DOCUMENTS)
def test_study_documents_quote_no_figure_the_summary_does_not_back(name: str):
    text = _text(name)
    # A rendered results block must equal a fresh rendering of the committed summary; without a
    # block the check passes.
    status, message = check_file(_committed(), text)
    assert status == EXIT_OK, message
    # Outside rendered blocks, no precision or recall percentage is typed by hand.
    outside = re.sub(
        r"<!-- micar-review-render:begin.*?<!-- micar-review-render:end study-results -->",
        "",
        text,
        flags=re.S,
    )
    assert not _PERCENT_CLAIM.search(outside), _PERCENT_CLAIM.search(outside)


def test_status_figures_in_the_study_documents_equal_the_json():
    committed, findings = _committed(), _findings()
    summary = findings["summary"]
    processed = summary.get("documents_processed", summary.get("documents_reviewed"))
    flagged = sum(row["detector_status"] == "flagged" for row in read_matrix(MATRIX))

    readme = _text("README.md")
    assert _number(r"Documents processed: (\d+)", readme) == committed["documents_total"] == processed
    assert _number(r"Document-rule cells: (\d+)", readme) == committed["rows_total"]
    assert _number(r"Machine-flagged candidate gaps: (\d+)", readme) == summary["potential_gaps"] == flagged
    status = re.search(r"Human-review status: `(\w+)`", readme).group(1)
    assert (status == "pending_review") is (not committed["publication_ready"])

    report = _text("findings-summary.md")
    assert _number(r"Documents processed: (\d+)", report) == committed["documents_total"]
    assert _number(r"Reviewers label the (\d+) document-rule cells", report) == committed["rows_total"]

    limitations = _text("limitations.md")
    pending_claim = re.search(r"All (\d+) document-rule cells remain pending", limitations)
    if pending_claim:
        assert int(pending_claim.group(1)) == committed["rows_total"] == committed["rows_pending"]
    else:
        assert committed["rows_pending"] < committed["rows_total"]


# The analysis plan's parameters as this test reads them. Square brackets mark open draft values
# ("[10]%"); they are optional so that the test keeps reading the plan after adoption removes them.
PLAN_PATTERNS = {
    "bootstrap": (r"B = ([\d,]+) replicates; seed `?(\d+)`?", "B and the seed (section 9)"),
    "z": (r"z = \[?(\d\.\d+)\]?", "the Wilson z (section 9)"),
    "dropped": (r"more than \[?(\d+)\]?% of bootstrap replicates", "the dropped-replicate limit (section 9)"),
    "frozen": (
        r"\| Findings file \| `findings-pseudonymous.json`, SHA-256 `([0-9a-f]{64})`, digest `([0-9a-f]{64})`",
        "the frozen findings file (section 2)",
    ),
    "primary": (
        r"^\| Primary \|[^\n]*?\| \[?(\d+)\]?(?: \(\[?(\d+)\]? under the fallback\))? \|",
        "the primary set's cells (section 7)",
    ),
    "full": (
        r"^\| Full \|[^\n]*?\| \[?(\d+)\]?(?: \(\[?(\d+)\]? under the fallback\))? \|",
        "the full set's cells (section 7)",
    ),
}


def _plan_match(plan: str, key: str) -> re.Match:
    pattern, what = PLAN_PATTERNS[key]
    match = re.search(pattern, plan, re.MULTILINE)
    assert match is not None, (
        f"analysis-plan.md no longer states {what} in a form this test reads ({pattern!r}). If the "
        "adopted plan changed the value, update the constants in review_validation.py, rerun "
        "micar-review-summary, and update PLAN_PATTERNS."
    )
    return match


def test_analysis_plan_parameters_equal_the_summary():
    plan = _text("analysis-plan.md")
    committed = _committed()
    settings = committed["settings"]

    bootstrap = _plan_match(plan, "bootstrap")
    assert (
        int(bootstrap.group(1).replace(",", ""))
        == settings["bootstrap"]["replicates"]
        == BOOTSTRAP_REPLICATES
    )
    assert int(bootstrap.group(2)) == settings["bootstrap"]["seed"] == BOOTSTRAP_SEED
    assert float(_plan_match(plan, "z").group(1)) == settings["wilson_z"]
    assert int(_plan_match(plan, "dropped").group(1)) / 100 == settings["max_dropped_fraction"]
    assert "WP-007 is excluded from the primary analysis" in plan
    assert settings["primary_exclusions"] == list(PRIMARY_EXCLUSIONS) == ["WP-007"]

    frozen = _plan_match(plan, "frozen")
    assert frozen.group(1) == committed["detector"]["findings_sha256"]
    assert frozen.group(2) == committed["detector"]["findings_digest"]

    # Section 7: primary 135 cells and full 150, or 120 and 135 under the calibration fallback.
    fallback = committed["exclusions"]["calibration_document"]["study_doc_id"] is not None
    for key, analysis in (("primary", "primary"), ("full", "S1")):
        match = _plan_match(plan, key)
        expected = match.group(2) if fallback else match.group(1)
        assert expected is not None, (
            f"a calibration document is in use, but section 7 gives no fallback cell count for the {key} set"
        )
        assert committed["analyses"][analysis]["cells"] == int(expected)


def test_plan_patterns_read_the_adopted_wording():
    # Adoption removes the brackets around open draft values; the patterns must still match.
    plan = _text("analysis-plan.md")
    adopted = plan.replace("more than [10]%", "more than 10%")
    assert int(_plan_match(adopted, "dropped").group(1)) == int(_plan_match(plan, "dropped").group(1))
    # A section 7 row without the fallback note still gives the default count.
    row = "| Primary | the 10 processed documents without WP-007 | 135 | Headline precision and recall |"
    assert _plan_match(row, "primary").groups() == ("135", None)


def test_internal_detail_stays_out_of_git():
    gitignore = (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "studies/**/human-review-internal*.json" in gitignore

    # The committed summary carries label and confusion counts per rule and per analysis set, never
    # per document (analysis-plan.md section 10), and no offeror names.
    def walk(value):
        if isinstance(value, dict):
            if "study_doc_id" in value:
                assert not {"label_counts", "tp", "fp", "fn", "tn"} & set(value), value
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(_committed())
    manifest = json.loads(_text("source-manifest.json"))
    committed = json.dumps(_committed(), ensure_ascii=False).casefold()
    for entry in manifest["entries"]:
        assert entry["offeror_or_issuer"].casefold() not in committed


def test_no_two_published_per_rule_tables_reveal_one_document():
    # Two per-rule tables over document sets that differ by one document give that document's
    # label and detector outcome for every rule (S1 and the primary set differ only by WP-007).
    # The summary publishes per-rule counts for one set; any further per-rule table must differ
    # from every other by more than one document.
    tables = []

    def walk(value):
        if isinstance(value, dict):
            if "per_rule" in value:
                assert "documents" in value, "a per-rule table must name its document set"
                tables.append(frozenset(value["documents"]))
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(_committed())
    assert len(tables) == 1, f"{len(tables)} published per-rule tables; the summary publishes one"
    for index, first in enumerate(tables):
        for second in tables[index + 1 :]:
            assert len(first ^ second) > 1, sorted(first ^ second)
    assert "per_rule" not in _committed()["analyses"]["S1"]


def test_recorded_plan_status_matches_the_banner():
    plan = _text("analysis-plan.md")
    recorded = _committed()["settings"]["analysis_plan"]
    if re.search(r"^>\s*\*\*DRAFT, not adopted", plan, re.MULTILINE):
        assert recorded["status"] == "draft"
        assert "(DRAFT, not adopted)" in _committed()["settings"]["definitions"]
    else:
        assert recorded["status"] == "adopted", (
            "analysis-plan.md no longer says DRAFT; fill its 'Adopted by' line and rerun micar-review-summary"
        )
        assert recorded["adopted_on"] in _committed()["settings"]["definitions"]
