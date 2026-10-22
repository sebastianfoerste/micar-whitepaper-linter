"""Report language is load-bearing (see CONTRIBUTING.md). Render real reports and check that the
"not package-ready" blocker message and the lawyer sign-off section appear exactly when report.py
promises them: the text report keeps the blocker message while any finding is open, the audit log
while any BLOCKER finding is open, and the audit log always ends with the lawyer sign-off section."""

from pathlib import Path

import pytest

from micar_linter.cli import main
from micar_linter.linter import Report
from micar_linter.report import render_audit_log, render_text
from micar_linter.rules import RULESETS
from micar_linter.rules.base import Finding, Severity
from micar_linter.whitepaper import WhitepaperType

ROOT = Path(__file__).resolve().parents[1]
INCOMPLETE = ROOT / "examples/incomplete.json"

NOT_PACKAGE_READY = "not package-ready"
TEXT_BLOCKER = "First-pass screening only. The draft is not package-ready."
TEXT_SIGN_OFF = "until BLOCKER items are cured and a lawyer has signed off."
TEXT_CLEAN = "All required disclosures present. Lawyer review still required."
NOT_LEGAL_ADVICE = "This tool is not legal advice."
LOG_BLOCKER = (
    "> **BLOCKER issues are currently open.** The draft is not package-ready for an external review "
    "or filing workflow until the gaps are cured and a lawyer has signed off."
)
LOG_CLEAN = "> All automated checks passed. Substantive lawyer review is still required."
SIGN_OFF_HEADING = "## Lawyer Sign-off"
SIGN_OFF_TEXT = (
    "The reviewing lawyer must sign below only after reviewing the automated findings, "
    "the source draft and any filing decision independently."
)
SIGN_OFF_FIELDS = ("Reviewer Name:", "Date of Review:", "Signature:")


def _report(open_rule: str | None = None) -> Report:
    """A synthetic ART report built from the real rule set: every rule passes except `open_rule`."""
    findings = tuple(
        Finding(rule=rule, status="review" if rule.rule_id == open_rule else "pass", word_count=100)
        for rule in RULESETS[WhitepaperType.ART]
    )
    return Report(title="Synthetic Token", whitepaper_type=WhitepaperType.ART, findings=findings)


def _first_rule(severity: Severity) -> str:
    return next(rule.rule_id for rule in RULESETS[WhitepaperType.ART] if rule.severity is severity)


def _assert_sign_off_section_closes(log: str) -> None:
    assert log.count(SIGN_OFF_HEADING) == 1
    section = log.split(SIGN_OFF_HEADING, 1)[1]
    assert "\n## " not in section, "the lawyer sign-off section must be the last section"
    assert SIGN_OFF_TEXT in section
    for field in SIGN_OFF_FIELDS:
        assert field in section


@pytest.mark.parametrize(("style", "filing_citation"), [("en", "Art. 8(1)"), ("de", "Art. 8 Abs. 1")])
def test_text_report_with_open_blockers_is_not_package_ready(capsys, style, filing_citation):
    assert main([str(INCOMPLETE), "--citation-style", style]) == 0
    out = capsys.readouterr().out
    footer = out.split("=" * 78)[-1]

    assert TEXT_BLOCKER in footer
    assert TEXT_SIGN_OFF in footer
    assert filing_citation in footer
    assert TEXT_CLEAN not in out
    assert out.rstrip("\n").endswith(NOT_LEGAL_ADVICE)


def test_text_report_keeps_the_blocker_message_while_a_non_blocker_finding_is_open():
    report = _report(open_rule=_first_rule(Severity.MAJOR))
    assert not report.blockers and not report.is_clean

    text = render_text(report)

    assert TEXT_BLOCKER in text
    assert TEXT_SIGN_OFF in text
    assert TEXT_CLEAN not in text


def test_clean_text_report_drops_the_blocker_message_but_keeps_lawyer_review():
    report = _report()
    assert report.is_clean

    text = render_text(report)

    assert TEXT_CLEAN in text
    assert NOT_PACKAGE_READY not in text
    assert "signed off" not in text
    assert text.endswith(NOT_LEGAL_ADVICE)


def test_audit_log_with_open_blockers_warns_and_ends_with_the_sign_off_section(tmp_path):
    log_path = tmp_path / "audit.md"
    assert main([str(INCOMPLETE), "--audit-log", str(log_path)]) == 0
    log = log_path.read_text(encoding="utf-8")

    assert "> [!WARNING]\n" + LOG_BLOCKER in log
    assert LOG_CLEAN not in log
    assert log.index(LOG_BLOCKER) < log.index(SIGN_OFF_HEADING)
    _assert_sign_off_section_closes(log)


def test_review_bundle_checklist_carries_the_blocker_warning_and_sign_off(tmp_path):
    bundle = tmp_path / "bundle"
    assert main([str(INCOMPLETE), "--review-bundle-dir", str(bundle)]) == 0
    checklist = (bundle / "compliance-checklist.md").read_text(encoding="utf-8")

    assert LOG_BLOCKER in checklist
    _assert_sign_off_section_closes(checklist)


@pytest.mark.parametrize("open_rule", [None, _first_rule(Severity.MAJOR)], ids=["clean", "major-open"])
def test_audit_log_without_blockers_drops_the_warning_but_keeps_the_sign_off_section(open_rule):
    report = _report(open_rule)
    assert not report.blockers

    log = render_audit_log(report, "synthetic.json", "0" * 64)

    assert NOT_PACKAGE_READY not in log
    assert "BLOCKER issues are currently open" not in log
    _assert_sign_off_section_closes(log)


def test_clean_audit_log_notes_that_lawyer_review_is_still_required():
    log = render_audit_log(_report(), "synthetic.json", "0" * 64)
    assert LOG_CLEAN in log
