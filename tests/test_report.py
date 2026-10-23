"""Report language is load-bearing (see CONTRIBUTING.md). Render real reports and check that the
"not package-ready" blocker message and the lawyer sign-off section appear exactly when report.py
promises them: the text report keeps the blocker message while any finding is open, the audit log
while any BLOCKER finding is open, and the audit log always ends with the lawyer sign-off section.
The audit log says that all automated checks passed only when every finding passes; while a MAJOR or
MINOR finding is open and no BLOCKER is, it says how many findings are open, by severity."""

import re
from pathlib import Path

import pytest

from micar_linter.cli import main
from micar_linter.linter import Report
from micar_linter.report import _TITLE_BAR, render_audit_log, render_text
from micar_linter.rules import RULESETS
from micar_linter.rules.base import Finding, Severity
from micar_linter.whitepaper import WhitepaperType

ROOT = Path(__file__).resolve().parents[1]
INCOMPLETE = ROOT / "examples/incomplete.json"

NOT_PACKAGE_READY = "not package-ready"
TEXT_BLOCKER = "First-pass screening only. The draft is not package-ready."
# The notification and approval provisions in each citation style, then the clause they gate.
TEXT_FILING = {
    "en": "(Art. 8(1), Art. 16(2), second subparagraph, Art. 17(1), point (a), Art. 18(2), point (k), "
    "Art. 51(11) MiCAR) should not enter an external review or filing workflow",
    "de": "(Art. 8 Abs. 1, Art. 16 Abs. 2 UAbs. 2, Art. 17 Abs. 1 Buchst. a, Art. 18 Abs. 2 Buchst. k, "
    "Art. 51 Abs. 11 MiCAR) should not enter an external review or filing workflow",
}
TEXT_SIGN_OFF = "until BLOCKER items are cured and a lawyer has signed off."
TEXT_NOTIFICATION = "The white paper notification or submission for approval"
TEXT_CLEAN = "All required disclosures present. Lawyer review still required."
NOT_LEGAL_ADVICE = "This tool is not legal advice."
LOG_BLOCKER = (
    "> **BLOCKER issues are currently open.** The draft is not package-ready for an external review "
    "or filing workflow until the gaps are cured and a lawyer has signed off."
)
LOG_CLEAN = "> All automated checks passed. Substantive lawyer review is still required."
LOG_OPEN_ONE_MAJOR = (
    "> **1 finding is still open (1 MAJOR) and no BLOCKER finding is open.** The draft still needs the open "
    "finding resolved or reviewed, and substantive lawyer review is still required."
)
LOG_OPEN_ONE_MINOR = (
    "> **1 finding is still open (1 MINOR) and no BLOCKER finding is open.** The draft still needs the open "
    "finding resolved or reviewed, and substantive lawyer review is still required."
)
LOG_OPEN_TWO_MAJOR = (
    "> **2 findings are still open (2 MAJOR) and no BLOCKER finding is open.** The draft still needs the "
    "open findings resolved or reviewed, and substantive lawyer review is still required."
)
LOG_OPEN_MAJOR_AND_MINOR = (
    "> **3 findings are still open (2 MAJOR, 1 MINOR) and no BLOCKER finding is open.** The draft still needs "
    "the open findings resolved or reviewed, and substantive lawyer review is still required."
)
SIGN_OFF_HEADING = "## Lawyer Sign-off"
SIGN_OFF_TEXT = (
    "The reviewing lawyer must sign below only after reviewing the automated findings, "
    "the source draft and any filing decision independently."
)
SIGN_OFF_FIELDS = ("Reviewer Name:", "Date of Review:", "Signature:")


def _report(
    *open_rules: str,
    status: str = "review",
    missing: tuple[str, ...] = (),
    whitepaper_type: WhitepaperType = WhitepaperType.ART,
) -> Report:
    """A synthetic report built from a real rule set, ART unless another type is given: every rule
    passes except `open_rules`, which get `status`, and `missing`, which are missing."""
    statuses = dict.fromkeys(open_rules, status) | dict.fromkeys(missing, "missing")
    findings = tuple(
        Finding(rule=rule, status=statuses.get(rule.rule_id, "pass"), word_count=100)
        for rule in RULESETS[whitepaper_type]
    )
    return Report(title="Synthetic Token", whitepaper_type=whitepaper_type, findings=findings)


def _rule_ids(severity: Severity, whitepaper_type: WhitepaperType = WhitepaperType.ART) -> list[str]:
    return [rule.rule_id for rule in RULESETS[whitepaper_type] if rule.severity is severity]


def _first_rule(severity: Severity, whitepaper_type: WhitepaperType = WhitepaperType.ART) -> str:
    return _rule_ids(severity, whitepaper_type)[0]


def _log_alert(log: str) -> str:
    """The audit log's alert, whole: its blockquote lines, the only lines of the log that start with '>'."""
    return "\n".join(line for line in log.splitlines() if line.startswith(">"))


# The ART rule set has no MINOR rule, so the MINOR states use the OTHER rule set, which has all three.
LOG_STATES = {
    "clean": (_report(), "> [!NOTE]\n" + LOG_CLEAN),
    "minor-only": (
        _report(_first_rule(Severity.MINOR, WhitepaperType.OTHER), whitepaper_type=WhitepaperType.OTHER),
        "> [!WARNING]\n" + LOG_OPEN_ONE_MINOR,
    ),
    "major-open": (_report(_first_rule(Severity.MAJOR)), "> [!WARNING]\n" + LOG_OPEN_ONE_MAJOR),
    "major-review-and-major-missing": (
        _report(_rule_ids(Severity.MAJOR)[0], missing=(_rule_ids(Severity.MAJOR)[1],)),
        "> [!WARNING]\n" + LOG_OPEN_TWO_MAJOR,
    ),
    "major-and-minor-open": (
        _report(
            *_rule_ids(Severity.MAJOR, WhitepaperType.OTHER)[:2],
            _first_rule(Severity.MINOR, WhitepaperType.OTHER),
            whitepaper_type=WhitepaperType.OTHER,
        ),
        "> [!WARNING]\n" + LOG_OPEN_MAJOR_AND_MINOR,
    ),
    "blocker-open": (
        _report(_first_rule(Severity.BLOCKER), _first_rule(Severity.MAJOR)),
        "> [!WARNING]\n" + LOG_BLOCKER,
    ),
}
# One open finding of every severity a real rule set has, in each open status.
OPEN_CASES = [
    (whitepaper_type, severity, status)
    for whitepaper_type in RULESETS
    for severity in Severity
    if _rule_ids(severity, whitepaper_type)
    for status in ("review", "missing")
]


def _text_blocker_sentence(style: str) -> str:
    """The text report's closing warning while any finding is open, whole, so no qualifier can slip in."""
    return f"{TEXT_BLOCKER} {TEXT_NOTIFICATION} {TEXT_FILING[style]} {TEXT_SIGN_OFF}"


def _assert_sign_off_section_closes(log: str) -> None:
    lines = log.splitlines()
    assert lines.count(SIGN_OFF_HEADING) == 1, f"expected the line '{SIGN_OFF_HEADING}' exactly once"
    section = lines[lines.index(SIGN_OFF_HEADING) + 1 :]
    assert not [line for line in section if line.startswith("#")], "the lawyer sign-off section must be last"
    assert SIGN_OFF_TEXT in "\n".join(section)
    for field in SIGN_OFF_FIELDS:
        assert [line for line in section if re.fullmatch(rf"{re.escape(field)} +_+", line)], (
            f"the lawyer sign-off section has no '{field}' line to fill in"
        )


@pytest.mark.parametrize("style", TEXT_FILING)
def test_text_report_with_open_blockers_is_not_package_ready(capsys, style):
    assert main([str(INCOMPLETE), "--citation-style", style]) == 0
    out = capsys.readouterr().out
    assert out.count(_TITLE_BAR) == 2, "the text report has a title bar and a footer bar"
    _, footer = out.rsplit(_TITLE_BAR, 1)

    assert _text_blocker_sentence(style) in footer
    assert TEXT_CLEAN not in out
    assert out.rstrip("\n").endswith(NOT_LEGAL_ADVICE)


def test_text_report_keeps_the_blocker_message_while_a_non_blocker_finding_is_open():
    report = _report(_first_rule(Severity.MAJOR))
    assert not report.blockers and not report.is_clean

    text = render_text(report)

    assert _text_blocker_sentence("en") in text
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


@pytest.mark.parametrize("open_rules", [(), (_first_rule(Severity.MAJOR),)], ids=["clean", "major-open"])
def test_audit_log_without_blockers_drops_the_blocker_warning_but_keeps_the_sign_off_section(open_rules):
    report = _report(*open_rules)
    assert not report.blockers

    log = render_audit_log(report, "synthetic.json", "0" * 64)

    assert NOT_PACKAGE_READY not in log
    assert "BLOCKER issues are currently open" not in log
    _assert_sign_off_section_closes(log)


def test_clean_audit_log_notes_that_lawyer_review_is_still_required():
    log = render_audit_log(_report(), "synthetic.json", "0" * 64)
    assert LOG_CLEAN in log


@pytest.mark.parametrize("state", LOG_STATES)
def test_audit_log_note_matches_the_state_of_the_report(state):
    report, alert = LOG_STATES[state]

    log = render_audit_log(report, "synthetic.json", "0" * 64)

    assert _log_alert(log) == alert
    assert log.index(alert) < log.index(SIGN_OFF_HEADING)
    _assert_sign_off_section_closes(log)


@pytest.mark.parametrize("style", TEXT_FILING)
@pytest.mark.parametrize("state", LOG_STATES)
def test_audit_log_and_bundle_checklist_carry_the_same_note_in_both_citation_styles(
    monkeypatch, tmp_path, state, style
):
    """The audit log prose is English in both citation styles; the review bundle checklist is the same log."""
    report, alert = LOG_STATES[state]
    monkeypatch.setattr("micar_linter.cli.lint_whitepaper", lambda whitepaper: report)
    log_path, bundle = tmp_path / "audit.md", tmp_path / "bundle"

    argv = [str(INCOMPLETE), "--citation-style", style, "--audit-log", str(log_path)]
    assert main([*argv, "--review-bundle-dir", str(bundle)]) == 0

    for path in (log_path, bundle / "compliance-checklist.md"):
        log = path.read_text(encoding="utf-8")
        assert _log_alert(log) == alert
        _assert_sign_off_section_closes(log)


def test_open_cases_cover_every_severity():
    assert {severity for _, severity, _ in OPEN_CASES} == set(Severity)


@pytest.mark.parametrize(
    ("whitepaper_type", "severity", "status"),
    OPEN_CASES,
    ids=[f"{t.value}-{severity.label}-{status}" for t, severity, status in OPEN_CASES],
)
def test_audit_log_never_says_all_checks_passed_while_a_finding_is_open(whitepaper_type, severity, status):
    report = _report(_first_rule(severity, whitepaper_type), status=status, whitepaper_type=whitepaper_type)
    assert not report.is_clean

    log = render_audit_log(report, "synthetic.json", "0" * 64)

    assert LOG_CLEAN not in log
    assert "checks passed" not in log.lower()
    if severity is Severity.BLOCKER:
        assert _log_alert(log) == "> [!WARNING]\n" + LOG_BLOCKER
    else:
        assert _log_alert(log) == "> [!WARNING]\n" + (
            f"> **1 finding is still open (1 {severity.label}) and no BLOCKER finding is open.** The draft still "
            "needs the open finding resolved or reviewed, and substantive lawyer review is still required."
        )
    _assert_sign_off_section_closes(log)
