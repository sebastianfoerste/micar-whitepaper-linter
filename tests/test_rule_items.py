"""Rules that check a white paper item other than the one their ID first named.

ANNEX_II.G.VALUATION_AUDIT checks the referenced assets and the valuation item of Annex II Part D
No. 10, and ANNEX_III.SAFEGUARDING is a review prompt, because no Annex III item asks for safeguarding.
The issuers are fictional.
"""

from __future__ import annotations

from micar_linter.linter import lint_whitepaper
from micar_linter.rules.base import Finding, Severity
from micar_linter.whitepaper import Whitepaper, WhitepaperType

FILLER_EN = " This synthetic sentence adds length only." * 12
FILLER_DE = " Dieser synthetische Satz dient nur der Länge." * 12


def _lint(whitepaper_type: WhitepaperType, sections: dict[str, str], lang: str = "en"):
    filler = FILLER_DE if lang == "de" else FILLER_EN
    whitepaper = Whitepaper(
        title="Synthetic draft",
        type=whitepaper_type,
        sections={key: text + filler for key, text in sections.items()},
        metadata={"language": lang},
    )
    return lint_whitepaper(whitepaper)


def _finding(report, rule_id: str) -> Finding:
    return next(f for f in report.findings if f.rule.rule_id == rule_id)


# Annex II Part D No. 10: (a) "the description of each referenced asset" and (c) "a description how a
# fair and transparent valuation of components of the claim is undertaken, which identifies, where
# relevant, independent parties".
CLAIM_VALUATION = (
    "The claim is valued at the market value of the referenced assets. A fair and transparent valuation of "
    "the components of the claim is undertaken daily, and an independent valuation agent reviews it."
)
CLAIM_VALUATION_DE = (
    "Der Anspruch entspricht dem Marktwert der referenzierten Vermögenswerte. Eine redliche und "
    "transparente Bewertung der Bestandteile der Forderung wird täglich vorgenommen; "
    "eine unabhängige Bewertungsstelle prüft sie."
)


def test_valuation_rule_reads_the_valuation_item_of_the_rights_section():
    report = _lint(WhitepaperType.ART, {"rights_and_obligations": CLAIM_VALUATION})
    assert _finding(report, "ANNEX_II.G.VALUATION_AUDIT").status == "pass"
    german = _lint(WhitepaperType.ART, {"rights_and_obligations": CLAIM_VALUATION_DE}, "de")
    assert _finding(german, "ANNEX_II.G.VALUATION_AUDIT").status == "pass"


def test_valuation_rule_asks_for_the_referenced_assets():
    valuation_only = "A fair and transparent valuation of the components of the claim is undertaken daily."
    report = _lint(WhitepaperType.ART, {"rights_and_obligations": valuation_only})
    finding = _finding(report, "ANNEX_II.G.VALUATION_AUDIT")
    assert finding.status == "review"
    assert "Missing review terms: referenced asset." in finding.issues
    # The valuation may be described with the verb ("bewertet"); "Referenzwerte" is no referenced asset.
    german = _lint(
        WhitepaperType.ART,
        {
            "rights_and_obligations": "Die Bestandteile der Forderung und die Referenzwerte werden täglich "
            "redlich bewertet."
        },
        "de",
    )
    assert _finding(german, "ANNEX_II.G.VALUATION_AUDIT").issues == (
        "Fehlende Begriffe: referenzierter vermögenswert.",
    )


def test_valuation_rule_names_the_referenced_assets_in_either_word_order_and_inflection():
    english = "Each of the assets referenced by the token is valued daily at its market price."
    assert _finding(
        _lint(WhitepaperType.ART, {"rights_and_obligations": english}), "ANNEX_II.G.VALUATION_AUDIT"
    ).status == "pass"
    german = "Der referenzierte Vermögenswert ist Gold; seine Bewertung erfolgt täglich."
    assert _finding(
        _lint(WhitepaperType.ART, {"rights_and_obligations": german}, "de"), "ANNEX_II.G.VALUATION_AUDIT"
    ).status == "pass"
    # "Evaluation" is no valuation.
    evaluation = "Each referenced asset is listed below. Complaints are subject to an evaluation."
    finding = _finding(
        _lint(WhitepaperType.ART, {"rights_and_obligations": evaluation}), "ANNEX_II.G.VALUATION_AUDIT"
    )
    assert finding.issues == ("Missing review terms: valuation.",)


def test_valuation_rule_no_longer_reads_the_reserve_section_or_asks_for_an_audit():
    # Annex II Part G has no valuation or audit item; the reserve audit of Art. 36(9) is published
    # under Art. 36(10), outside the white paper.
    reserve = "The reserve is valued daily and audited every six months by an independent auditor."
    report = _lint(WhitepaperType.ART, {"reserve_of_assets": reserve})
    assert _finding(report, "ANNEX_II.G.VALUATION_AUDIT").status == "missing"
    # A rights section that describes the claim and its valuation passes without any audit.
    rights = "The referenced asset is gold. A fair and transparent valuation of the claim is undertaken daily."
    assert "audit" not in rights
    report = _lint(WhitepaperType.ART, {"rights_and_obligations": rights})
    assert _finding(report, "ANNEX_II.G.VALUATION_AUDIT").status == "pass"


# Art. 54 MiCAR and Annex III Part D No. 3, in English and German.
SAFEGUARDED = (
    "The funds received in exchange for the e-money tokens are safeguarded in accordance with Article 7(1) "
    "of Directive 2009/110/EC. At least 30 % of them is always deposited in separate accounts in credit "
    "institutions, and holders keep their claim in the insolvency of the issuer."
)
SAFEGUARDED_DE = (
    "Die im Tausch gegen die E-Geld-Token entgegengenommenen Geldbeträge sind gemäß Artikel 7 Absatz 1 der "
    "Richtlinie 2009/110/EG besichert. Mindestens 30 % sind stets auf gesonderten Konten bei "
    "Kreditinstituten hinterlegt; die Inhaber behalten ihren Anspruch auch bei Insolvenz des Emittenten."
)


def test_safeguarding_prompt_follows_article_54_and_is_no_blocker():
    report = _lint(WhitepaperType.EMT, {"safeguarding": SAFEGUARDED})
    assert _finding(report, "ANNEX_III.SAFEGUARDING").status == "pass"
    german = _lint(WhitepaperType.EMT, {"safeguarding": SAFEGUARDED_DE}, "de")
    assert _finding(german, "ANNEX_III.SAFEGUARDING").status == "pass"
    # No Annex III item asks for the section, so its absence is reported without blocking.
    empty = _lint(WhitepaperType.EMT, {})
    finding = _finding(empty, "ANNEX_III.SAFEGUARDING")
    assert finding.status == "missing"
    assert finding.rule.severity is Severity.MAJOR
    assert finding not in empty.blockers
