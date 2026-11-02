"""The committed Title II study files agree with each other, whatever the labelling progress.

The committed ``human-review-summary.json`` stays as it is until ``micar-review-summary`` exits 0
(review-protocol.md), so it is checked only against the matrix's counts. The analyses of
``--analyses`` are computed here in memory from the committed matrix, findings, manifest and
analysis plan, never written, and checked against the plan's text and the publication limits of
its section 10.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

from micar_linter.review_metrics import WILSON_Z
from micar_linter.review_validation import (
    BOOTSTRAP_REPLICATES,
    BOOTSTRAP_SEED,
    MAX_DROPPED_FRACTION,
    load_analysis_context,
    plan_status,
    summarize_rows,
)

REPO = Path(__file__).resolve().parents[1]
STUDY = REPO / "studies" / "2026-07-title-ii-annex-i-whitepaper-study"
SUMMARY = STUDY / "human-review-summary.json"
MATRIX = STUDY / "human-review-matrix.csv"
FINDINGS = STUDY / "findings-pseudonymous.json"
PLAN = STUDY / "analysis-plan.md"
# The primary exclusion that analysis-plan.md section 5 states; the command takes it only as
# --primary-exclude, so the test names it here and checks the plan still says so.
PLAN_EXCLUSION = "WP-007"
# Documents in which the study quotes figures.
QUOTING_DOCUMENTS = ("README.md", "findings-summary.md", "limitations.md", "methodology.md", "REVIEWING.md")
_PERCENT_CLAIM = re.compile(r"\b(precision|recall)\b[^.\n|]{0,40}?\d+(?:\.\d+)?\s?%", re.IGNORECASE)


def _committed() -> dict:
    return json.loads(SUMMARY.read_text(encoding="utf-8"))


def _findings() -> dict:
    return json.loads(FINDINGS.read_text(encoding="utf-8"))


def _text(name: str) -> str:
    return (STUDY / name).read_text(encoding="utf-8")


def _matrix() -> list[dict[str, str]]:
    with MATRIX.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _analysed() -> dict:
    """The summary with --analyses over the committed study files, as the study README runs it."""
    context = load_analysis_context(
        FINDINGS,
        manifest=STUDY / "source-manifest.json",
        analysis_plan=PLAN,
        primary_exclude=(PLAN_EXCLUSION,),
        replicates=200,
    )
    return summarize_rows(_matrix(), analyses=context)


def _number(pattern: str, text: str) -> int:
    match = re.search(pattern, text)
    assert match, f"pattern {pattern!r} not found"
    return int(match.group(1))


def test_committed_summary_counts_equal_the_matrix():
    committed = _committed()
    rows = _matrix()
    labels = [(row["human_label"] or "pending").strip() or "pending" for row in rows]
    assert committed["rows_total"] == len(rows) == 150
    assert committed["rows_pending"] == labels.count("pending")
    assert committed["rows_completed"] == len(rows) - labels.count("pending")
    if labels.count("pending"):
        assert committed["publication_ready"] is False
    assert len({row["study_doc_id"] for row in rows}) == 10
    assert len({row["rule_id"] for row in rows}) == 15


def test_analyses_of_the_committed_files_identify_the_detector_and_the_plan():
    analysed = _analysed()
    findings = _findings()
    detector = analysed["detector"]
    assert detector["findings_file"] == FINDINGS.name
    assert detector["findings_sha256"] == hashlib.sha256(FINDINGS.read_bytes()).hexdigest()
    assert detector["findings_digest"] == findings["digest"]
    assert detector["findings_generated_at"] == findings["generated_at"]
    # The analyses of the committed matrix change none of the summary's own keys.
    plain = summarize_rows(_matrix())
    assert {key: analysed[key] for key in plain} == plain


def test_status_figures_in_the_study_documents_equal_the_json():
    committed, findings = _committed(), _findings()
    summary = findings["summary"]
    processed = summary.get("documents_processed", summary.get("documents_reviewed"))
    rows = _matrix()
    documents = len({row["study_doc_id"] for row in rows})
    flagged = sum(row["detector_status"] == "flagged" for row in rows)

    readme = _text("README.md")
    assert _number(r"Documents processed: (\d+)", readme) == documents == processed
    assert _number(r"Document-rule cells: (\d+)", readme) == committed["rows_total"]
    assert _number(r"Machine-flagged candidate gaps: (\d+)", readme) == summary["potential_gaps"] == flagged
    status = re.search(r"Human-review status: `(\w+)`", readme).group(1)
    assert (status == "pending_review") is (not committed["publication_ready"])

    report = _text("findings-summary.md")
    # micar-study-report writes "Documents reviewed" from the v1 findings' documents_reviewed.
    assert _number(r"Documents (?:processed|reviewed): (\d+)", report) == documents
    assert _number(r"Reviewers label the (\d+) document-rule cells", report) == committed["rows_total"]

    limitations = _text("limitations.md")
    pending_claim = re.search(r"All (\d+) document-rule cells remain pending", limitations)
    if pending_claim:
        assert int(pending_claim.group(1)) == committed["rows_total"] == committed["rows_pending"]
    else:
        assert committed["rows_pending"] < committed["rows_total"]


def test_study_documents_type_no_precision_or_recall_figure():
    # Figures come from the summary's JSON output; no precision or recall percentage is typed by hand.
    for name in QUOTING_DOCUMENTS:
        match = _PERCENT_CLAIM.search(_text(name))
        assert match is None, (name, match.group(0))


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
        "adopted plan changed the value, update the constants in review_validation.py and PLAN_PATTERNS."
    )
    return match


def test_analysis_plan_parameters_equal_the_code():
    plan = PLAN.read_text(encoding="utf-8")
    analysed = _analysed()

    bootstrap = _plan_match(plan, "bootstrap")
    assert int(bootstrap.group(1).replace(",", "")) == BOOTSTRAP_REPLICATES
    assert int(bootstrap.group(2)) == BOOTSTRAP_SEED
    assert float(_plan_match(plan, "z").group(1)) == WILSON_Z == analysed["settings"]["wilson_z"]
    assert int(_plan_match(plan, "dropped").group(1)) / 100 == MAX_DROPPED_FRACTION
    assert f"{PLAN_EXCLUSION} is excluded from the primary analysis" in plan
    assert analysed["settings"]["primary_exclusions"] == [PLAN_EXCLUSION]

    frozen = _plan_match(plan, "frozen")
    assert frozen.group(1) == analysed["detector"]["findings_sha256"]
    assert frozen.group(2) == analysed["detector"]["findings_digest"]

    # Section 7: primary 135 cells and full 150, or 120 and 135 under the calibration fallback.
    fallback = analysed["exclusions"]["calibration_document"]["study_doc_id"] is not None
    for key, analysis in (("primary", "primary"), ("full", "S1")):
        match = _plan_match(plan, key)
        expected = match.group(2) if fallback else match.group(1)
        assert expected is not None, (
            f"a calibration document is in use, but section 7 gives no fallback cell count for the {key} set"
        )
        assert analysed["analyses"][analysis]["cells"] == int(expected)


def test_plan_patterns_read_the_adopted_wording():
    # Adoption removes the brackets around open draft values; the patterns must still match.
    plan = PLAN.read_text(encoding="utf-8")
    adopted = plan.replace("more than [10]%", "more than 10%")
    assert int(_plan_match(adopted, "dropped").group(1)) == int(_plan_match(plan, "dropped").group(1))
    # A section 7 row without the fallback note still gives the default count.
    row = "| Primary | the 10 processed documents without WP-007 | 135 | Headline precision and recall |"
    assert _plan_match(row, "primary").groups() == ("135", None)


def test_internal_detail_stays_out_of_git_and_out_of_the_summary():
    gitignore = (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "studies/**/human-review-internal*.json" in gitignore

    # The summary carries label and confusion counts per rule and per analysis set, never per
    # document (analysis-plan.md section 10), and no offeror names.
    def walk(value):
        if isinstance(value, dict):
            if "study_doc_id" in value:
                assert not {"label_counts", "tp", "fp", "fn", "tn"} & set(value), value
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    analysed = _analysed()
    walk(analysed)
    manifest = json.loads(_text("source-manifest.json"))
    text = json.dumps(analysed, ensure_ascii=False).casefold()
    for entry in manifest["entries"]:
        assert entry["offeror_or_issuer"].casefold() not in text


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

    analysed = _analysed()
    walk(analysed)
    assert len(tables) == 1, f"{len(tables)} published per-rule tables; the summary publishes one"
    for index, first in enumerate(tables):
        for second in tables[index + 1 :]:
            assert len(first ^ second) > 1, sorted(first ^ second)
    assert "per_rule" not in analysed["analyses"]["S1"]


def test_recorded_plan_status_matches_the_banner():
    plan = PLAN.read_text(encoding="utf-8")
    recorded = plan_status(plan)
    if re.search(r"^>\s*\*\*DRAFT, not adopted", plan, re.MULTILINE):
        assert recorded["status"] == "draft"
        assert "(DRAFT, not adopted)" in _analysed()["settings"]["definitions"]
    else:
        assert recorded["status"] == "adopted", (
            "analysis-plan.md no longer says DRAFT; fill its 'Adopted by' line with a reviewer and an ISO date"
        )
        assert recorded["adopted_on"] in _analysed()["settings"]["definitions"]
