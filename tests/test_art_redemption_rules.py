"""ART redemption and reserve-valuation rules follow Art. 36 and Art. 39 MiCAR.

Redemption "at par" is the e-money token rule (Art. 49(4) MiCAR). An ART issuer
redeems by paying funds equivalent to the market value of the referenced assets or by
delivering those assets (Art. 39(2) MiCAR). Valuation of the reserve sits in Art. 36(7),
(11) and (12), the six-monthly independent audit in Art. 36(9); Art. 36(3) is
operational segregation. English fixtures follow the EUR-Lex text (CELEX 32023R1114,
mirrored in legalize-dev/legalize-eu).

The German keywords "Rücktausch" and "Marktwert" follow the German text of Art. 39 MiCAR
as reproduced on springlex.eu and gesetze.legal in web search results; they have not been
checked against the German Official Journal text.
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
    ).replace("Holders cannot choose delivery of the referenced assets instead. ", "")
    finding = _finding("ANNEX_II.I", "redemption", text)
    assert finding.status == "review"
    assert any("market" in issue for issue in finding.issues)


def test_delivery_only_redemption_passes_the_redemption_rule():
    # Art. 39(2) MiCAR, second option: redemption by delivering the referenced assets.
    text = (
        "The redemption right is exercisable against the issuer at any time. Upon request, the issuer "
        "redeems by delivering the assets referenced by the tokens held to a custody account named by "
        "the holder. The procedure requires a redemption request through the issuer's portal and the "
        "timing of settlement is two business days. Redemption is not subject to fees. Liquidity fees "
        "and the suspension of redemptions are available only as recovery options under the recovery "
        "plan, and the competent authority may temporarily suspend redemption. The issuer accepted "
        "payment only in referenced assets and not in funds denominated in an official currency. "
        "Settlement is complete when the referenced assets are credited to the holder's account."
    )
    finding = _finding("ANNEX_II.I", "redemption", text)
    assert finding.status == "pass", finding.issues


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


GERMAN_RIGHTS = (
    "Die Inhaber haben gegenüber dem Emittenten folgende Rechte: ein jederzeitiges Recht auf "
    "Rücktausch, das Recht, Beschwerden über das Beschwerdeverfahren des Emittenten einzureichen, "
    "und Informationen darüber, wie diese Rechte im Fall eines Insolvenzverfahrens behandelt werden. "
) * 3

GERMAN_REDEMPTION = (
    "Auf Verlangen eines Inhabers erfolgt der Rücktausch durch Zahlung eines Geldbetrags, der kein "
    "E-Geld ist und dem Marktwert der Vermögenswerte entspricht, auf die sich die gehaltenen Token "
    "beziehen. Das Verfahren beginnt mit einem Antrag über das Kundenportal des Emittenten. Der "
    "Zeitplan sieht die Abwicklung innerhalb eines Geschäftstages vor. Für den Rücktausch werden "
    "keine Gebühren erhoben. Liquiditätsgebühren und eine Aussetzung des Rücktauschs kommen nur als "
    "Sanierungsmaßnahmen nach dem Sanierungsplan in Betracht; die zuständige Behörde kann den "
    "Rücktausch vorübergehend aussetzen. Der Emittent hat Zahlungen in Euro angenommen und bietet "
    "den Rücktausch stets in Euro an. Die Abwicklung erfolgt per Überweisung auf ein geprüftes Konto "
    "des Inhabers. Weitere Einzelheiten enthält die Rücktauschstrategie des Emittenten."
)


def test_german_rights_section_with_ruecktausch_passes():
    finding = _finding("ANNEX_II.D", "rights_and_obligations", GERMAN_RIGHTS, language="de")
    assert finding.status == "pass", finding.issues


def test_german_redemption_section_with_marktwert_passes():
    finding = _finding("ANNEX_II.I", "redemption", GERMAN_REDEMPTION, language="de")
    assert finding.status == "pass", finding.issues


def test_german_redemption_zu_par_without_marktwert_is_referred_to_review():
    text = GERMAN_REDEMPTION.replace(
        "dem Marktwert der Vermögenswerte entspricht, auf die sich die gehaltenen Token beziehen",
        "zu par erfolgt",
    )
    finding = _finding("ANNEX_II.I", "redemption", text, language="de")
    assert finding.status == "review"
    assert any("marktwert" in issue for issue in finding.issues)


def test_german_art_risks_accept_ruecktausch():
    text = (
        "Es bestehen Markt-, Kredit-, Liquiditäts- und operative Risiken. Der Token kann seine "
        "Bindung verlieren (De-Peg). Ein Rücktausch kann verzögert sein, wenn die Reserve "
        "beeinträchtigt ist. "
    ) * 8
    finding = _finding("ANNEX_II.F", "risks", text, language="de")
    assert finding.status == "pass", finding.issues


def test_no_art_rule_cites_operational_segregation_for_valuation():
    # Regression: Art. 36(3) MiCAR (operational segregation) was cited for valuation and audit.
    rule = _rule("ANNEX_II.G.VALUATION_AUDIT")
    assert "Abs. 3" not in rule.citation and "36(3)" not in rule.label


def test_valuation_audit_label_does_not_claim_the_standards_were_checked():
    # The rule finds the words only. Amortised cost (excluded by Art. 36(12), third
    # subparagraph) and an annual internal audit still pass, so the label must say so.
    text = (
        "The valuation of the reserve uses the amortised cost method. An internal audit of the "
        "reserve takes place annually and its results are reported to the management body. "
    ) * 3
    finding = _finding("ANNEX_II.G.VALUATION_AUDIT", "reserve_of_assets", text)
    assert finding.status == "pass"
    assert "not checked" in finding.rule.label


def test_art_example_passes_the_redemption_rules():
    report = lint_whitepaper(load_whitepaper(ROOT / "examples" / "art-stablecoin.json"))
    indexed = {f.rule.rule_id: f for f in report.findings}
    for rule_id in ("ANNEX_II.D", "ANNEX_II.I", "ANNEX_II.G.VALUATION_AUDIT"):
        assert indexed[rule_id].status == "pass", (rule_id, indexed[rule_id].issues)


def test_starter_template_cites_the_art_provisions_for_its_art_type():
    # Regression: the "art" starter cited Title II provisions (Art. 6, Art. 8(1)) and
    # asked for "the redemption right at par under Art. 39".
    import json

    starter = json.loads((ROOT / "templates" / "whitepaper-starter" / "whitepaper.json").read_text(encoding="utf-8"))
    assert starter["type"] == "art"
    text = " ".join(starter["sections"].values())
    assert "at par" not in text
    assert "Art. 6 Abs." not in text and "Art. 8 Abs." not in text
    assert "Art. 39 Abs. 2" in starter["sections"]["redemption"]
