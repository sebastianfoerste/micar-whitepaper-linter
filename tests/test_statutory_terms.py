"""Sections written in the wording of MiCAR, its Annexes and the templates meet the listed terms.

Each text below follows the Official Journal wording or the template of Implementing Regulation (EU)
2024/2984 for the item a rule checks. The issuers are fictional.
"""

from __future__ import annotations

import pytest

from micar_linter.linter import lint_whitepaper
from micar_linter.rules.base import Finding
from micar_linter.whitepaper import Whitepaper, WhitepaperType

FILLER_EN = " This synthetic sentence adds length only." * 12
FILLER_DE = " Dieser synthetische Satz dient nur der Länge." * 12


def _finding(
    whitepaper_type: WhitepaperType, rule_id: str, section: str, text: str, lang: str = "en"
) -> Finding:
    whitepaper = Whitepaper(
        title="Synthetic draft",
        type=whitepaper_type,
        sections={section: text + (FILLER_DE if lang == "de" else FILLER_EN)},
        metadata={"language": lang},
    )
    return next(f for f in lint_whitepaper(whitepaper).findings if f.rule.rule_id == rule_id)


# Party sections that give an LEI and, as recital 2 of Implementing Regulation 2024/2984 allows, leave
# out the legal form and the registered address.
PARTY_EN = (
    "Example Issuer AG, the issuer and offeror named in this white paper, is identified by its legal "
    "entity identifier. The members of its management body, with their business address and functions, "
    "are listed in the table below."
)
PARTY_DE = (
    "Die Example Issuer AG ist Emittent und Anbieter; ihr Name und ihre Unternehmenskennung stehen in "
    "diesem Whitepaper. Die Mitglieder des Leitungsorgans sind mit Geschäftsanschrift und Funktion in "
    "der Tabelle unten aufgeführt."
)


@pytest.mark.parametrize(
    ("whitepaper_type", "rule_id", "section"),
    [
        (WhitepaperType.OTHER, "ANNEX_I.A", "offeror"),
        (WhitepaperType.OTHER, "ANNEX_I.B", "issuer"),
        (WhitepaperType.ART, "ANNEX_II.A", "issuer"),
        (WhitepaperType.EMT, "ANNEX_III.A", "issuer"),
    ],
)
@pytest.mark.parametrize(("text", "lang"), [(PARTY_EN, "en"), (PARTY_DE, "de")])
def test_party_sections_that_give_an_lei_need_no_legal_form_or_registered_address(
    whitepaper_type, rule_id, section, text, lang
):
    assert _finding(whitepaper_type, rule_id, section, text, lang).status == "pass"


def test_emt_issuer_section_need_not_name_both_institution_types():
    # Art. 48(1)(a): authorised "as a credit institution or as an electronic money institution".
    text = PARTY_EN + " The issuer is authorised as an electronic money institution."
    assert _finding(WhitepaperType.EMT, "ANNEX_III.A", "issuer", text).status == "pass"


# The predefined German compliance statement of the templates (Table 2 field 03, Tables 3 and 4 field I.03).
TEMPLATE_STATEMENT_DE = (
    "Dieses Kryptowerte-Whitepaper erfüllt Titel {} der Verordnung (EU) 2023/1114 des Europäischen "
    "Parlaments und des Rates und es wird bestätigt, dass die in ihm enthaltenen Informationen nach "
    "bestem Wissen des Leitungsorgans redlich, eindeutig und nicht irreführend sind und dass das "
    "Kryptowerte-Whitepaper keine Auslassungen aufweist, die seine Aussagekraft beeinträchtigen könnten."
)


@pytest.mark.parametrize(
    ("whitepaper_type", "title"),
    [(WhitepaperType.OTHER, "II"), (WhitepaperType.ART, "III"), (WhitepaperType.EMT, "IV")],
)
def test_german_template_statement_meets_the_management_statement_terms(whitepaper_type, title):
    text = TEMPLATE_STATEMENT_DE.format(title)
    finding = _finding(whitepaper_type, "COMMON.MANAGEMENT_STATEMENT", "management_statement", text, "de")
    assert finding.status == "pass"


def test_art_section_needs_no_basket_and_takes_either_german_spelling():
    # Art. 3(1)(6): an ART may reference "another value or right or a combination thereof".
    english = (
        "The asset-referenced token references a single value, the price of one gram of gold. Its reference "
        "assets and its stabilisation mechanism are described below."
    )
    assert _finding(WhitepaperType.ART, "ANNEX_II.B", "art", english).status == "pass"
    for adjective in ("vermögenswertereferenzierte", "vermögenswertreferenzierte"):
        german = (
            f"Der {adjective} Token bezieht sich auf einen einzigen Wert, den Preis eines Gramms Gold. Die "
            "Referenzwerte und der Mechanismus zur Stabilisierung sind unten beschrieben."
        )
        assert _finding(WhitepaperType.ART, "ANNEX_II.B", "art", german, "de").status == "pass"


def test_emt_offer_section_follows_annex_iii_part_c():
    english = (
        "This crypto-asset white paper concerns an offer to the public of the e-money token. The total "
        "number of units offered and the trading platforms where admission to trading is sought are set "
        "out below. The law applicable to the offer is German law, and the competent court is in Berlin."
    )
    german = (
        "Dieses Kryptowerte-Whitepaper betrifft ein öffentliches Angebot des E-Geld-Token. Für das "
        "öffentliche Angebot gilt deutsches Recht, und das zuständige Gericht ist in Berlin."
    )
    assert _finding(WhitepaperType.EMT, "ANNEX_III.C", "offer_or_admission", english).status == "pass"
    assert _finding(WhitepaperType.EMT, "ANNEX_III.C", "offer_or_admission", german, "de").status == "pass"


def test_emt_rights_section_follows_annex_iii_part_d_and_article_49_4():
    english = (
        "The holder of the e-money token has the right of redemption at par value at any time. The rights "
        "of holders and the complaints-handling procedure are described below."
    )
    german = (
        "Der Inhaber des E-Geld-Token hat das Recht auf Rücktausch zum Nennwert, jederzeit. Die Rechte der "
        "Inhaber und das Verfahren für Beschwerden sind unten beschrieben."
    )
    finding = _finding(WhitepaperType.EMT, "ANNEX_III.D", "rights_and_obligations", english)
    assert finding.status == "pass"
    assert (
        _finding(WhitepaperType.EMT, "ANNEX_III.D", "rights_and_obligations", german, "de").status == "pass"
    )


def test_german_crypto_asset_section_uses_kryptowert():
    german = (
        "Der Kryptowert wird öffentlich angeboten. Das Angebot, die Übertragung und die Funktionsweise des "
        "Kryptowerts sind unten beschrieben."
    )
    assert _finding(WhitepaperType.OTHER, "ANNEX_I.F", "crypto_asset", german, "de").status == "pass"


def test_german_emt_section_says_amtliche_waehrung():
    german = (
        "Der E-Geld-Token ist auf eine amtliche Währung referenziert. Die Stückelung ist unten beschrieben."
    )
    assert _finding(WhitepaperType.EMT, "ANNEX_III.B", "emt", german, "de").status == "pass"


@pytest.mark.parametrize(
    ("whitepaper_type", "rule_id"),
    [
        (WhitepaperType.OTHER, "ANNEX_I.J"),
        (WhitepaperType.ART, "ANNEX_II.H"),
        (WhitepaperType.EMT, "ANNEX_III.G"),
    ],
)
def test_sustainability_sections_in_the_delegated_regulation_wording(whitepaper_type, rule_id):
    # Delegated Regulation (EU) 2025/422 speaks of "climate and other environment-related adverse impacts".
    text = (
        "The consensus mechanism and its energy use are described below, with the principal adverse impacts "
        "on the climate and other environment-related adverse impacts."
    )
    assert _finding(whitepaper_type, rule_id, "environmental_impact", text).status == "pass"
