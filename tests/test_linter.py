from micar_linter.linter import Linter, lint_whitepaper
from micar_linter.rules.base import Rule, Severity
from micar_linter.whitepaper import Whitepaper, WhitepaperType


def test_linter_basic_checks():
    rules = (
        Rule(
            rule_id="TEST.1",
            citation="Test Cite",
            section="summary",
            label="Test Rule",
            required_terms=("key", "info"),
            min_words=5,
            severity=Severity.BLOCKER,
        ),
    )
    wp = Whitepaper(
        title="Test WP",
        type=WhitepaperType.OTHER,
        sections={
            "summary": "This is some key info content that is long enough.",
        },
        metadata={},
    )
    findings = Linter(rules).lint(wp)
    assert len(findings) == 1
    assert findings[0].passed
    assert findings[0].word_count == 10


def test_linter_missing_section():
    rules = (
        Rule(
            rule_id="TEST.1",
            citation="Test Cite",
            section="absent_section",
            label="Test Rule",
            required_terms=("key",),
            min_words=5,
            severity=Severity.BLOCKER,
        ),
    )
    wp = Whitepaper(
        title="Test WP",
        type=WhitepaperType.OTHER,
        sections={
            "summary": "This is some key info.",
        },
        metadata={},
    )
    findings = Linter(rules).lint(wp)
    assert len(findings) == 1
    assert findings[0].status == "missing"
    assert "Section is empty or absent." in findings[0].issues


def test_linter_thin_section():
    rules = (
        Rule(
            rule_id="TEST.1",
            citation="Test Cite",
            section="summary",
            label="Test Rule",
            required_terms=("key",),
            min_words=100,
            severity=Severity.BLOCKER,
        ),
    )
    wp = Whitepaper(
        title="Test WP",
        type=WhitepaperType.OTHER,
        sections={
            "summary": "This is key.",
        },
        metadata={},
    )
    findings = Linter(rules).lint(wp)
    assert len(findings) == 1
    assert findings[0].status == "review"
    assert "Section is thin: 3 words, expected at least 100." in findings[0].issues


def test_linter_required_patterns():
    rules = (
        Rule(
            rule_id="TEST.REGEX",
            citation="Test Cite",
            section="summary",
            label="Test Regex Rule",
            required_patterns=(r"redemp(tion)?", r"holder\s+rights"),
            min_words=5,
            severity=Severity.MAJOR,
        ),
    )
    # Success case
    wp_pass = Whitepaper(
        title="Test WP",
        type=WhitepaperType.OTHER,
        sections={
            "summary": "This section covers the redemption right of holders and holder rights.",
        },
        metadata={},
    )
    findings_pass = Linter(rules).lint(wp_pass)
    assert findings_pass[0].passed

    # Missing pattern case
    wp_fail = Whitepaper(
        title="Test WP",
        type=WhitepaperType.OTHER,
        sections={
            "summary": "This section has holder rights but no payout.",
        },
        metadata={},
    )
    findings_fail = Linter(rules).lint(wp_fail)
    assert not findings_fail[0].passed
    assert "Missing required pattern: 'redemp(tion)?'." in findings_fail[0].issues


def test_linter_prohibited_patterns():
    rules = (
        Rule(
            rule_id="TEST.PROHIBITED",
            citation="Test Cite",
            section="summary",
            label="Test Prohibited Rule",
            prohibited_patterns=(r"risk-free", r"guaranteed\s+profit"),
            min_words=5,
            severity=Severity.BLOCKER,
        ),
    )
    
    # Has prohibited word
    wp_fail = Whitepaper(
        title="Test WP",
        type=WhitepaperType.OTHER,
        sections={
            "summary": "This investment is completely risk-free and offers high gains.",
        },
        metadata={},
    )
    findings_fail = Linter(rules).lint(wp_fail)
    assert not findings_fail[0].passed
    assert "Prohibited content matched: 'risk-free'." in findings_fail[0].issues

    # Clean
    wp_pass = Whitepaper(
        title="Test WP",
        type=WhitepaperType.OTHER,
        sections={
            "summary": "This investment carries significant risks of loss.",
        },
        metadata={},
    )
    findings_pass = Linter(rules).lint(wp_pass)
    assert findings_pass[0].passed


def test_linter_warnings_on_unrecognized_sections():
    # Only checks "summary" section
    wp = Whitepaper(
        title="Test WP",
        type=WhitepaperType.OTHER,
        sections={
            "summary": "This summary covers key information about the other assets.",
            "misspelled_offeror": "Offeror seat is in Berlin.",
        },
        metadata={},
    )
    
    report = lint_whitepaper(wp)
    # The linter check should identify that misspelled_offeror is not in the ruleset
    assert len(report.warnings) > 0
    assert any("misspelled_offeror" in w for w in report.warnings)


def test_severity_ranking_is_stable():
    assert Severity.BLOCKER.value > Severity.MAJOR.value > Severity.MINOR.value
    assert [severity.label for severity in Severity] == ["BLOCKER", "MAJOR", "MINOR"]
    assert [severity.label for severity in sorted(Severity, key=lambda item: item.value)] == [
        "MINOR",
        "MAJOR",
        "BLOCKER",
    ]
