"""ART redemption and valuation rules follow Art. 39 MiCAR and Annex II Part D.

Redemption "at par" is the e-money token rule (Art. 49(4) MiCAR). An ART issuer
redeems by paying funds, other than electronic money, equivalent to the market value of
the referenced assets or by delivering those assets (Art. 39(2) MiCAR). Art. 36(3) is
the operational segregation of the reserve, not its valuation. The terms of
`ANNEX_II.D`, `ANNEX_II.I` and `ANNEX_II.G.VALUATION_AUDIT` are tested in
`tests/test_rules.py`, `tests/test_rule_items.py` and `tests/test_term_patterns.py`.
An ART redemption section that mentions par value goes to review with a note.
"""

import json
from pathlib import Path

import pytest

from micar_linter.linter import Linter, lint_whitepaper
from micar_linter.rules import RULESETS
from micar_linter.whitepaper import Whitepaper, WhitepaperType, load_whitepaper

ROOT = Path(__file__).resolve().parents[1]


def _rule(rule_id: str):
    for rules in RULESETS.values():
        for rule in rules:
            if rule.rule_id == rule_id:
                return rule
    raise AssertionError(f"{rule_id} not found")


def test_no_art_rule_requires_redemption_at_par():
    for rule in RULESETS[WhitepaperType.ART]:
        terms = " | ".join((*rule.required_terms, *rule.required_terms_de)).lower()
        assert "at par" not in terms and "zu par" not in terms, rule.rule_id
        assert "at par" not in rule.label.lower(), rule.rule_id


def test_emt_rights_rule_keeps_redemption_at_par():
    rule = _rule("ANNEX_III.D")
    assert "at par" in rule.required_terms
    assert "Art. 49 Abs. 4" in rule.citation


def test_no_art_rule_cites_operational_segregation_for_valuation():
    # Regression: Art. 36(3) MiCAR (operational segregation) was cited for valuation and audit.
    rule = _rule("ANNEX_II.G.VALUATION_AUDIT")
    assert "Abs. 3" not in rule.citation and "36(3)" not in rule.label


def test_art_example_passes_the_redemption_rules():
    report = lint_whitepaper(load_whitepaper(ROOT / "examples" / "art-stablecoin.json"))
    indexed = {f.rule.rule_id: f for f in report.findings}
    for rule_id in ("ANNEX_II.D", "ANNEX_II.I", "ANNEX_II.G.VALUATION_AUDIT"):
        assert indexed[rule_id].status == "pass", (rule_id, indexed[rule_id].issues)


def test_starter_template_cites_the_art_provisions_for_its_art_type():
    # Regression: the "art" starter cited Title II provisions (Art. 6, Art. 8(1)) and
    # asked for "the redemption right at par under Art. 39".
    starter = json.loads(
        (ROOT / "templates" / "whitepaper-starter" / "whitepaper.json").read_text(encoding="utf-8")
    )
    assert starter["type"] == "art"
    text = " ".join(starter["sections"].values())
    assert "at par" not in text
    assert "Art. 6 Abs." not in text and "Art. 8 Abs." not in text
    assert "market value of the referenced assets" in starter["sections"]["redemption"]


ART_REDEMPTION_EN = json.loads((ROOT / "examples" / "art-stablecoin.json").read_text(encoding="utf-8"))[
    "sections"
]["redemption"]
ART_REDEMPTION_DE = (
    "Der Inhaber kann das dauerhafte Recht auf Rücktausch jederzeit gegenüber dem Emittenten ausüben. Der "
    "Emittent zahlt einen dem Marktwert der Vermögenswerte, auf die der Token Bezug nimmt, entsprechenden "
    "Geldbetrag in Euro, bei dem es sich nicht um elektronisches Geld handelt. Das Verfahren verlangt einen "
    "Antrag über das Portal des Emittenten nach abgeschlossener Identitätsprüfung. Der Zeitrahmen für die "
    "Abwicklung beträgt einen Geschäftstag ab Eingang eines vollständigen Antrags. Die Auszahlung erfolgt "
    "per Überweisung auf das geprüfte Bankkonto des Inhabers. Für den Rücktausch fällt keine Gebühr an "
    "(Artikel 39 Absatz 3). Nur der Sanierungsplan nach Artikel 46 kann Liquiditätsgebühren, Begrenzungen "
    "der täglichen Rücktauschmenge oder eine Aussetzung des Rücktauschs vorsehen, und die zuständige Behörde "
    "kann den Rücktausch nach Artikel 46 Absatz 4 vorübergehend aussetzen; jede Aussetzung wird auf dem "
    "Portal des Emittenten veröffentlicht."
)


def _redemption(text: str, language: str = "en"):
    whitepaper = Whitepaper(
        title="Synthetic draft",
        type=WhitepaperType.ART,
        sections={"redemption": text},
        metadata={"language": language},
    )
    return Linter((_rule("ANNEX_II.I"),)).lint(whitepaper)[0]


def _assert_par_note(finding, language: str = "en") -> None:
    assert finding.status == "review"
    assert len(finding.issues) == 1
    if language == "de":
        assert finding.issues[0].startswith("Der Abschnitt erwähnt den Nennwert.")
        assert "Art. 49 Abs. 4 MiCAR" in finding.issues[0] and "Art. 39 Abs. 2 MiCAR" in finding.issues[0]
    else:
        assert finding.issues[0].startswith("The section mentions par value.")
        assert "Art. 49(4) MiCAR" in finding.issues[0] and "Art. 39(2) MiCAR" in finding.issues[0]


def test_redemption_texts_without_par_value_pass():
    assert _redemption(ART_REDEMPTION_EN).status == "pass"
    assert _redemption(ART_REDEMPTION_DE, "de").status == "pass"


@pytest.mark.parametrize(
    "sentence",
    [
        "Holders redeem at par.",
        "Each token is redeemed at its par value.",
        "The issuer offers par-value redemption on request.",
        "Holders are entitled to at-par redemption in euro.",
        "Tokens are redeemable 1:1 at par value.",
        "Each token is redeemable at par with the euro.",
        "The issuer guarantees that tokens are redeemed at least at par.",
        "Tokens are redeemed at their nominal value.",
        "Tokens are redeemed at nominal.",
        "Redemption takes place at face value.",
        "Each token is redeemable for its face value of EUR 1.00.",
        "Holders redeem **at par**.",
        "Redemption is at _par value_.",
        "Tokens are redeemed at nom-\ninal value in euro.",
        # Words that also name the reserve or the procedure do not excuse the sentence.
        "After the usual security checks, tokens are redeemed at par.",
        "The token is not a bond and is redeemed at par.",
        # A sentence after "at par." that opens with a number, a bracket or an article stays separate.
        "\n1. Each token is redeemed at par.\n2. Requests are processed on business days.",
        "\n(a) Holders redeem at par.\n(b) The reserve is held in bank deposits.",
        "Tokens are redeemed at par. 100 % of the reserve is held in sight deposits.",
        "Tokens are redeemed at par. Article 5 of the terms sets out the procedure.",
        # The check reads the words, so a section that denies redemption at par goes to review too.
        "Tokens are not redeemed at par.",
    ],
)
def test_english_par_value_goes_to_review(sentence: str):
    _assert_par_note(_redemption(f"{ART_REDEMPTION_EN} {sentence}"))


@pytest.mark.parametrize(
    "sentence",
    [
        "Der Rücktausch erfolgt zum Nennwert.",
        "Die Token werden zu ihren Nennbeträgen zurückgetauscht.",
        "Der Rücktausch erfolgt zum Nominalbetrag.",
        "Der Rücktausch erfolgt zum nominellen Wert des Token.",
        "Der Rücktausch erfolgt zu pari.",
        "Der Rücktausch erfolgt zum Pariwert.",
        "Ein Rücktausch unter pari findet nicht statt.",
        "Der Rücktausch erfolgt mindestens zum Nennwert.",
        "Der Inhaber kann sein Guthaben jederzeit zum Nennwert zurücktauschen.",
        "Für den Rücktausch gilt der Nennwert.",
        # Line ends, soft hyphens and zero-width characters inside the word.
        "Der Rücktausch erfolgt jederzeit zum Nenn-\nwert.",
        "Der Rücktausch erfolgt zum Nennbe-\ntrag in Euro.",
        "Der Rücktausch erfolgt zum Nenn\N{HYPHEN}\nwert.",
        "Der Rücktausch erfolgt zum Nenn\N{SOFT HYPHEN}wert.",
        "Der Rücktausch erfolgt zum Nenn\N{SOFT HYPHEN}\nwert.",
        "Der Rücktausch erfolgt zum Nenn\N{ZERO WIDTH SPACE}wert.",
    ],
)
def test_german_par_value_goes_to_review(sentence: str):
    _assert_par_note(_redemption(f"{ART_REDEMPTION_DE} {sentence}", "de"), "de")


@pytest.mark.parametrize(
    ("sentence", "language"),
    [
        ("Treasury bills in the reserve are bought at a discount and redeemed at par.", "en"),
        ("Reserve deposits: at par.", "en"),
        ("Tokens are issued at par; redemption is at the market value of the referenced assets.", "en"),
        ("Bankguthaben der Reserve werden zum Nennwert bewertet.", "de"),
    ],
)
def test_par_value_of_the_reserve_or_issuance_also_goes_to_review(sentence: str, language: str):
    # Which use a par word has is for the reviewer: the note says so instead of guessing from nearby words.
    base = ART_REDEMPTION_DE if language == "de" else ART_REDEMPTION_EN
    finding = _redemption(f"{base} {sentence}", language)
    _assert_par_note(finding, language)
    expected = (
        "Vermögenswertreserve oder die Ausgabe" if language == "de" else "reserve of assets or to issuance"
    )
    assert expected in finding.issues[0]


@pytest.mark.parametrize(
    ("sentence", "language"),
    [
        ("Redemption under Art. 39 par. 2 MiCAR is processed daily.", "en"),
        ("Redemption follows the first par. of Art. 39(2) MiCAR.", "en"),
        ("Settlement within one business day is on a par with market practice.", "en"),
        ("The process is par for the course for regulated issuers.", "en"),
        ("Bank transfer is the settlement method par excellence.", "en"),
        ("Sub-par service by a custodian does not delay redemption.", "en"),
        ("Redemption claims rank pari passu with other unsecured claims.", "en"),
        ("Redemption claims of all holders rank at par with each other in insolvency.", "en"),
        ("Requests go to participating banks; that part of the policy and parity of treatment stay.", "en"),
        ("Für Rücktauschansprüche gilt eine Pari-passu-Klausel.", "de"),
    ],
)
def test_uses_that_never_mean_par_value_pass(sentence: str, language: str):
    base = ART_REDEMPTION_DE if language == "de" else ART_REDEMPTION_EN
    assert _redemption(f"{base} {sentence}", language).status == "pass"


def test_numbered_field_draft_gets_the_note(tmp_path: Path):
    # Each field becomes a line "label: answer", and a short answer often ends without a full stop.
    rows = [
        ("I.01", "Date of notification", "2026-03-02"),
        ("I.06", "Right of redemption", "The holders have a right of redemption at any time."),
        ("A.1", "Name", "Example Reserve AG"),
        ("B.14", "Language or languages of the crypto-asset white paper", "English"),
        ("D.21", "Transparent claim valuation", "Each token is valued at par"),
        (
            "D.22",
            "Other details about the claim the asset referenced token represents over referenced assets",
            "The claim is backed by bank deposits",
        ),
    ]
    cells = "".join(f"<tr><td>{n}</td><td>{label}</td><td>{answer}</td></tr>" for n, label, answer in rows)
    path = tmp_path / "draft.xhtml"
    path.write_text(f"<html><body><table>{cells}</table></body></html>", encoding="utf-8")
    report = lint_whitepaper(load_whitepaper(path, WhitepaperType.ART))
    finding = next(f for f in report.findings if f.rule.rule_id == "ANNEX_II.I")
    assert any(issue.startswith("The section mentions par value.") for issue in finding.issues)
