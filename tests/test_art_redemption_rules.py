"""ART redemption rules follow Art. 39 MiCAR.

Redemption "at par" is the e-money token rule (Art. 49(4) MiCAR). An ART issuer
redeems by paying funds equivalent to the market value of the referenced assets or by
delivering those assets (Art. 39(2) MiCAR).
"""

from pathlib import Path

from micar_linter.linter import Linter, lint_whitepaper
from micar_linter.rules import RULESETS
from micar_linter.whitepaper import Whitepaper, WhitepaperType, load_whitepaper

ROOT = Path(__file__).resolve().parents[1]

# Settlement and procedure wording around the Art. 39(2) and (3) and Art. 46 MiCAR elements.
REDEMPTION = (
    "The redemption right is exercisable against the issuer at any time. Upon request, the issuer "
    "redeems by paying an amount in funds, other than electronic money, equivalent to the market "
    "value of the assets referenced by the tokens held. The procedure requires a redemption request "
    "through the issuer's portal and the timing of settlement is one business day. Redemption is not "
    "subject to fees. Liquidity fees and the suspension of redemptions are available only as recovery "
    "options under the recovery plan, and the competent authority may temporarily suspend redemption. "
    "The issuer accepted payment in euro and always offers redemption in euro funds. Holders cannot "
    "choose delivery of the referenced assets instead. Settlement is by bank transfer to a verified "
    "account of the holder."
)


def _rule(rule_id: str):
    for rules in RULESETS.values():
        for rule in rules:
            if rule.rule_id == rule_id:
                return rule
    raise AssertionError(f"{rule_id} not found")


def _finding(rule_id: str, section: str, text: str, **metadata):
    whitepaper = Whitepaper(title="ART test", type=WhitepaperType.ART, sections={section: text}, metadata=metadata)
    return next(f for f in Linter(RULESETS[WhitepaperType.ART]).lint(whitepaper) if f.rule.rule_id == rule_id)


def test_no_art_rule_requires_redemption_at_par():
    for rule in RULESETS[WhitepaperType.ART]:
        terms = " | ".join((*rule.required_terms, *rule.required_terms_de)).lower()
        assert "at par" not in terms and "zu par" not in terms, rule.rule_id
        assert "at par" not in rule.label.lower(), rule.rule_id


def test_emt_rights_rule_keeps_redemption_at_par():
    rule = _rule("ANNEX_III.D")
    assert "at par" in rule.required_terms
    assert "Art. 49 Abs. 4" in rule.citation


def test_market_value_redemption_passes_the_redemption_rule():
    finding = _finding("ANNEX_II.I", "redemption", REDEMPTION)
    assert finding.status == "pass", finding.issues


def test_redemption_at_par_without_market_value_is_referred_to_review():
    text = REDEMPTION.replace(
        "equivalent to the market value of the assets referenced by the tokens held", "at par"
    )
    finding = _finding("ANNEX_II.I", "redemption", text)
    assert finding.status == "review"
    assert any("market value" in issue for issue in finding.issues)


def test_redemption_rule_cites_article_39_2_and_3_and_article_46():
    citation = _rule("ANNEX_II.I").citation
    assert "Art. 39 Abs. 2 und 3" in citation
    assert "Art. 46" in citation


def test_rights_rule_asks_for_treatment_in_insolvency():
    text = (
        "The holder has rights against the issuer, including a permanent right of redemption at all "
        "times and a right to file complaints under the complaints-handling procedure. " * 4
    )
    finding = _finding("ANNEX_II.D", "rights_and_obligations", text)
    assert finding.status == "review"
    assert any("insolvency" in issue for issue in finding.issues)
    passing = _finding(
        "ANNEX_II.D", "rights_and_obligations", text + "Section 11 describes the treatment in insolvency."
    )
    assert passing.status == "pass", passing.issues


def test_german_redemption_rule_uses_ruecktausch_and_marktwert():
    rule = _rule("ANNEX_II.I")
    assert "rücktausch" in rule.required_terms_de
    assert "marktwert" in rule.required_terms_de
    assert "rücktausch" in _rule("ANNEX_II.D").required_terms_de


def test_art_example_passes_the_redemption_rules():
    report = lint_whitepaper(load_whitepaper(ROOT / "examples" / "art-stablecoin.json"))
    indexed = {f.rule.rule_id: f for f in report.findings}
    for rule_id in ("ANNEX_II.D", "ANNEX_II.I"):
        assert indexed[rule_id].status == "pass", (rule_id, indexed[rule_id].issues)
