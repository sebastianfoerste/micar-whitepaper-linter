"""The first-page statement that no competent authority has approved the white paper.

The English fixture text is the statement as Art. 6(3) and Art. 51(3) MiCAR word it,
and as Table 2 field 02 and Table 4 field I.02 of the Annex to Implementing Regulation
(EU) 2024/2984 print it. An ART white paper is approved (Art. 17(1), 21(1) MiCAR), so
Art. 19 MiCAR has no such statement and the ART ruleset carries no such rule.
"""

from pathlib import Path

import pytest

from micar_linter.linter import Linter, lint_whitepaper
from micar_linter.rules import RULESETS
from micar_linter.rules.base import Severity
from micar_linter.whitepaper import Whitepaper, WhitepaperType, load_whitepaper

ROOT = Path(__file__).resolve().parents[1]
TITLE_II = "ANNEX_I.NOT_APPROVED_STATEMENT"
EMT = "ANNEX_III.NOT_APPROVED_STATEMENT"

APPROVAL = (
    "This crypto-asset white paper has not been approved by any competent authority "
    "in any Member State of the European Union."
)


def _statement(subject: str) -> str:
    return (
        f"{APPROVAL} {subject} of the crypto-asset is solely responsible for the content "
        "of this crypto-asset white paper."
    )


def _finding(wp_type: WhitepaperType, rule_id: str, sections: dict[str, str], **metadata):
    whitepaper = Whitepaper(title="Statement test", type=wp_type, sections=sections, metadata=metadata)
    for finding in Linter(RULESETS[wp_type]).lint(whitepaper):
        if finding.rule.rule_id == rule_id:
            return finding
    raise AssertionError(f"{rule_id} was not applied")


@pytest.mark.parametrize(
    "subject",
    ["The offeror", "The person seeking admission to trading", "The operator of the trading platform"],
)
def test_title_ii_statement_passes_for_each_person_art_6_3_names(subject: str):
    finding = _finding(WhitepaperType.OTHER, TITLE_II, {"not_approved_statement": _statement(subject)})
    assert finding.status == "pass", finding.issues
    assert finding.rule.citation == "Art. 6 Abs. 3 MiCAR"


def test_emt_statement_passes_when_it_names_the_issuer():
    finding = _finding(WhitepaperType.EMT, EMT, {"not_approved_statement": _statement("The issuer")})
    assert finding.status == "pass", finding.issues
    assert finding.rule.citation == "Art. 51 Abs. 3 MiCAR"


def test_emt_statement_naming_the_offeror_is_referred_to_review():
    finding = _finding(WhitepaperType.EMT, EMT, {"not_approved_statement": _statement("The offeror")})
    assert finding.status == "review"
    assert any("the issuer of the crypto-asset is solely responsible" in issue for issue in finding.issues)


@pytest.mark.parametrize("wp_type, rule_id", [(WhitepaperType.OTHER, TITLE_II), (WhitepaperType.EMT, EMT)])
def test_absent_statement_fails_closed_as_a_blocker(wp_type: WhitepaperType, rule_id: str):
    finding = _finding(wp_type, rule_id, {"summary": "A summary without the statement."})
    assert finding.status == "missing"
    assert finding.rule.severity is Severity.BLOCKER


@pytest.mark.parametrize("wp_type, rule_id", [(WhitepaperType.OTHER, TITLE_II), (WhitepaperType.EMT, EMT)])
def test_paraphrased_statement_is_referred_to_review(wp_type: WhitepaperType, rule_id: str):
    paraphrase = (
        "No supervisor has reviewed this document. The issuer of the crypto-asset is solely "
        "responsible for the content of this crypto-asset white paper."
    )
    finding = _finding(wp_type, rule_id, {"not_approved_statement": paraphrase})
    assert finding.status == "review"
    assert any("has not been approved by any competent authority" in issue for issue in finding.issues)


def test_art_ruleset_has_no_not_approved_statement():
    art_rules = {rule.rule_id for rule in RULESETS[WhitepaperType.ART]}
    assert not {rule_id for rule_id in art_rules if rule_id.endswith("NOT_APPROVED_STATEMENT")}
    assert TITLE_II in {rule.rule_id for rule in RULESETS[WhitepaperType.OTHER]}
    assert EMT in {rule.rule_id for rule in RULESETS[WhitepaperType.EMT]}


def test_german_statement_is_checked_with_the_german_wording():
    german = (
        "Dieses Kryptowerte-Whitepaper wurde von keiner zuständigen Behörde eines Mitgliedstaats "
        "der Europäischen Union genehmigt. Der Anbieter des Kryptowerts trägt die alleinige "
        "Verantwortung für den Inhalt dieses Kryptowerte-Whitepapers."
    )
    finding = _finding(WhitepaperType.OTHER, TITLE_II, {"not_approved_statement": german}, language="de")
    assert finding.status == "pass", finding.issues


@pytest.mark.parametrize("filename", ["other-crypto-asset.json", "emt-token.json"])
def test_canonical_examples_carry_the_statement(filename: str):
    report = lint_whitepaper(load_whitepaper(ROOT / "examples" / filename))
    statement = next(f for f in report.findings if f.rule.rule_id.endswith("NOT_APPROVED_STATEMENT"))
    assert statement.status == "pass", statement.issues


def test_numbered_field_02_feeds_the_title_ii_check():
    whitepaper = load_whitepaper(ROOT / "examples" / "numbered-other-draft.xhtml", WhitepaperType.OTHER)
    assert whitepaper.section("not_approved_statement").startswith(
        "Statement in accordance with Article 6(3) of Regulation (EU) 2023/1114:"
    )
    report = lint_whitepaper(whitepaper)
    statement = next(f for f in report.findings if f.rule.rule_id == TITLE_II)
    assert statement.status == "pass", statement.issues


def test_numbered_field_i_02_feeds_the_emt_check(tmp_path: Path):
    rows = "".join(
        f"<tr><td>{number}</td><td>{label}</td><td>{content}</td></tr>"
        for number, label, content in [
            ("I.01", "Date of notification", "2026-03-02"),
            (
                "I.02",
                "Statement in accordance with Article 51(3) of Regulation (EU) 2023/1114",
                _statement("The issuer"),
            ),
            ("A.1", "Statutory name", "Example EMI GmbH"),
            ("B.1", "Name of the e-money token", "Example EUR"),
            ("D.1", "Holder's rights and obligations", "Redemption at any time and at par value."),
        ]
    )
    path = tmp_path / "emt.xhtml"
    path.write_text(f"<html><body><table>{rows}</table></body></html>", encoding="utf-8")
    whitepaper = load_whitepaper(path, WhitepaperType.EMT)
    assert APPROVAL in whitepaper.section("not_approved_statement")
    statement = next(f for f in lint_whitepaper(whitepaper).findings if f.rule.rule_id == EMT)
    assert statement.status == "pass", statement.issues


def test_numbered_art_field_i_02_stays_the_risk_warning(tmp_path: Path):
    rows = "".join(
        f"<tr><td>{number}</td><td>{label}</td><td>{content}</td></tr>"
        for number, label, content in [
            ("I.02", "Statement in accordance with Article 19(4)", "The token may lose its value."),
            ("A.1", "Statutory name", "Example Issuer AG"),
            ("B.1", "Name", "Example ART"),
            ("G.1", "Description of the reserve of assets", "Bank deposits."),
        ]
    )
    path = tmp_path / "art.xhtml"
    path.write_text(f"<html><body><table>{rows}</table></body></html>", encoding="utf-8")
    whitepaper = load_whitepaper(path, WhitepaperType.ART)
    assert "not_approved_statement" not in whitepaper.sections
    assert "may lose its value" in whitepaper.section("risk_warning")


def test_statement_heading_routes_prose_drafts(tmp_path: Path):
    path = tmp_path / "draft.md"
    path.write_text(
        "# Statement in accordance with Article 6(3) of Regulation (EU) 2023/1114\n"
        f"{_statement('The offeror')}\n\n# Summary\nKey information.\n",
        encoding="utf-8",
    )
    whitepaper = load_whitepaper(path, WhitepaperType.OTHER)
    assert APPROVAL in whitepaper.section("not_approved_statement")
    assert "not been approved" not in whitepaper.section("summary")
