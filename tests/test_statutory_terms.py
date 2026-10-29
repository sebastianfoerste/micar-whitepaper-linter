"""Sections written in the wording of MiCAR, its Annexes and the templates meet the listed terms.

Each text below states the item a rule checks, in the Official Journal wording of MiCAR or of the template
of Implementing Regulation (EU) 2024/2984 where one exists. The issuers and their LEIs are fictional.
"""

from __future__ import annotations

import pytest

from micar_linter.lei import check_digits_for
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


# Party sections that give an LEI and leave out the legal form and the registered address: the templates of
# Implementing Regulation 2024/2984 ask for those fields only where no LEI is provided (see its recital 2).
SYNTHETIC_LEI = "9999SYNTH0000ZZQ01" + check_digits_for("9999SYNTH0000ZZQ01")
PARTY_EN = (
    f"The name of the issuer and offeror is Example Issuer AG; its legal entity identifier is {SYNTHETIC_LEI}. "
    "The members of its management body, with their business address and functions, are listed in the "
    "table below."
)
PARTY_DE = (
    f"Name des Emittenten und Anbieters ist Example Issuer AG; seine Rechtsträgerkennung lautet {SYNTHETIC_LEI}. "
    "Die Mitglieder des Leitungsorgans sind mit Geschäftsanschrift und Funktion in der Tabelle unten "
    "aufgeführt."
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
# Table 2 ends "dass das Kryptowerte-Whitepaper", Tables 3 and 4 "dass dieses Kryptowerte-Whitepaper".
TEMPLATE_STATEMENT_DE = (
    "Dieses Kryptowerte-Whitepaper erfüllt Titel {} der Verordnung (EU) 2023/1114 des Europäischen "
    "Parlaments und des Rates und es wird bestätigt, dass die in ihm enthaltenen Informationen nach "
    "bestem Wissen des Leitungsorgans redlich, eindeutig und nicht irreführend sind und dass {} "
    "Kryptowerte-Whitepaper keine Auslassungen aufweist, die seine Aussagekraft beeinträchtigen könnten."
)


@pytest.mark.parametrize(
    ("whitepaper_type", "title", "article"),
    [
        (WhitepaperType.OTHER, "II", "das"),
        (WhitepaperType.ART, "III", "dieses"),
        (WhitepaperType.EMT, "IV", "dieses"),
    ],
)
def test_german_template_statement_meets_the_management_statement_terms(whitepaper_type, title, article):
    text = TEMPLATE_STATEMENT_DE.format(title, article)
    finding = _finding(whitepaper_type, "COMMON.MANAGEMENT_STATEMENT", "management_statement", text, "de")
    assert finding.status == "pass"


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


# Each Part as the Annex words its items, in English and German. The ART section references a single
# value, as Art. 3(1)(6) allows, and names neither a basket nor a stabilisation mechanism.
TECHNOLOGY_EN = (
    "The distributed ledger technology, the protocols and technical standards used, the consensus mechanism "
    "and the audit outcome of the technology used are described below."
)
TECHNOLOGY_DE = (
    "Die Distributed-Ledger-Technologie, die Protokolle und technischen Standards, der Konsensmechanismus "
    "und das Ergebnis der Prüfung der eingesetzten Technologie sind unten beschrieben."
)
ANNEX_WORDING = [
    (
        WhitepaperType.OTHER,
        "ANNEX_I.D",
        "project",
        "The crypto-asset project, its past and future milestones and the resources allocated to the project "
        "are described below.",
        "Das Kryptowert-Projekt, die bisherigen und künftigen Projekt-Etappen und die dem Projekt "
        "zugewiesenen Ressourcen sind unten beschrieben.",
    ),
    (
        WhitepaperType.OTHER,
        "ANNEX_I.E",
        "offer_or_admission",
        "The offer to the public runs at an issue price of 1 EUR, with minimum and maximum target subscription "
        "goals. The law applicable to the offer is German law, and the competent court is in Berlin.",
        "Das öffentliche Angebot erfolgt zu einem Ausgabepreis von 1 EUR, mit Mindest- und Höchstzielen für "
        "die Zeichnung. Für das öffentliche Angebot gilt deutsches Recht, und das zuständige Gericht ist in "
        "Berlin.",
    ),
    (
        WhitepaperType.OTHER,
        "ANNEX_I.F",
        "crypto_asset",
        "The type of crypto-asset, its characteristics and its functionality are described below.",
        "Die Art des Kryptowerts, seine Merkmale und seine Funktionen sind unten beschrieben.",
    ),
    (
        WhitepaperType.OTHER,
        "ANNEX_I.G",
        "rights_and_obligations",
        "The rights and obligations of the purchaser, and the procedure and conditions for the exercise of "
        "those rights, are described below. The law applicable to the crypto-assets is German law, and the "
        "competent court is in Berlin.",
        "Die Rechte und Pflichten des Käufers und das Verfahren und die Bedingungen für die Ausübung dieser "
        "Rechte sind unten beschrieben. Für die Kryptowerte gilt deutsches Recht, und das zuständige Gericht "
        "ist in Berlin.",
    ),
    (WhitepaperType.OTHER, "ANNEX_I.H", "technology", TECHNOLOGY_EN, TECHNOLOGY_DE),
    (
        WhitepaperType.OTHER,
        "ANNEX_I.I",
        "risks",
        "The risks associated with the offer to the public, the issuer, the crypto-assets, project "
        "implementation and the technology used, with mitigation measures, are described below.",
        "Die mit dem öffentlichen Angebot, dem Emittenten, den Kryptowerten, der Projektdurchführung und der "
        "eingesetzten Technologie verbundenen Risiken sowie Maßnahmen zur Risikominderung sind unten "
        "beschrieben.",
    ),
    (
        WhitepaperType.ART,
        "ANNEX_II.B",
        "art",
        "The asset-referenced token references a single value, the price of one gram of gold. Its "
        "characteristics and the plans for the token, with the past and future milestones, are described "
        "below.",
        "Der vermögenswertereferenzierte Token bezieht sich auf einen einzigen Wert, den Preis eines Gramms "
        "Gold. Seine Merkmale und die Pläne für den Token mit den bisherigen und künftigen Etappen sind unten "
        "beschrieben.",
    ),
    (
        WhitepaperType.ART,
        "ANNEX_II.C",
        "offer_or_admission",
        "This crypto-asset white paper concerns an offer to the public of the asset-referenced token. The "
        "prospective holders targeted by the offer are described below. The law applicable to the offer is "
        "German law, and the competent court is in Berlin.",
        "Dieses Kryptowerte-Whitepaper betrifft ein öffentliches Angebot des vermögenswertereferenzierten "
        "Token. Die potenziellen Inhaber, auf die das Angebot ausgerichtet ist, sind unten beschrieben. Für "
        "das öffentliche Angebot gilt deutsches Recht, und das zuständige Gericht ist in Berlin.",
    ),
    (WhitepaperType.ART, "ANNEX_II.E", "technology", TECHNOLOGY_EN, TECHNOLOGY_DE),
    (
        WhitepaperType.ART,
        "ANNEX_II.F",
        "risks",
        "The risks related to the reserve of assets, the issuer, the offer to the public, the asset-referenced "
        "token, the operationalisation of the project and the technology used, with mitigation measures, are "
        "described below.",
        "Die Risiken im Zusammenhang mit der Vermögenswertreserve, dem Emittenten, dem öffentlichen Angebot, "
        "dem Token, der Operationalisierung des Projekts und der eingesetzten Technologie sowie Maßnahmen zur "
        "Risikominderung sind unten beschrieben.",
    ),
    (
        WhitepaperType.ART,
        "ANNEX_II.G.COMPOSITION_DISCLOSURE",
        "reserve_of_assets",
        "The mechanism aimed at aligning the value of the reserve of assets with the claim, and the reserve "
        "of assets and its composition, are described below.",
        "Der Mechanismus zur Angleichung des Wertes der Vermögenswertreserve an die Ansprüche sowie die "
        "Vermögenswertreserve und ihre Zusammensetzung sind unten beschrieben.",
    ),
    (
        WhitepaperType.EMT,
        "ANNEX_III.B",
        "emt",
        "The e-money token, its characteristics and the persons involved in its design and development are "
        "described below.",
        "Der E-Geld-Token, seine Merkmale und die an Gestaltung und Entwicklung beteiligten Personen sind "
        "unten beschrieben.",
    ),
    (WhitepaperType.EMT, "ANNEX_III.E", "technology", TECHNOLOGY_EN, TECHNOLOGY_DE),
    (
        WhitepaperType.EMT,
        "ANNEX_III.F",
        "risks",
        "The risks associated with the issuer, the e-money token and the technology used, with mitigation "
        "measures, are described below.",
        "Die vom Emittenten ausgehenden, die mit dem E-Geld-Token und die mit der eingesetzten Technologie "
        "verbundenen Risiken sowie Maßnahmen zur Risikominderung sind unten beschrieben.",
    ),
]


@pytest.mark.parametrize(
    ("whitepaper_type", "rule_id", "section", "english", "german"),
    ANNEX_WORDING,
    ids=[rule_id for _, rule_id, *_ in ANNEX_WORDING],
)
def test_sections_in_the_annex_wording_meet_the_terms(whitepaper_type, rule_id, section, english, german):
    # A second filler reaches the 150 words the ART risk rule asks for.
    assert _finding(whitepaper_type, rule_id, section, english + FILLER_EN).status == "pass"
    assert _finding(whitepaper_type, rule_id, section, german + FILLER_DE, "de").status == "pass"


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
