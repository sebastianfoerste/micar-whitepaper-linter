"""Annex II MiCAR - asset-referenced tokens (ARTs).

Reference: Anhang II VO (EU) 2023/1114 i.V.m. Art. 19 MiCAR.

ART white papers carry a heavier disclosure load than Annex I: reserve of
assets, redemption rights, governance arrangements, and bank-style risk
information are mandatory. The reserve composition rule (Art. 36 MiCAR) is
typically where draft white papers fail in practice.

Scaffold note: this ruleset hits each Part of Annex II at the Part level. The
practitioner extends with the point-level checks that reflect the firm's
internal interpretation of BaFin and EBA guidance.
"""

from __future__ import annotations

from micar_linter.rules.base import Rule, Severity

ANNEX_II_RULES: tuple[Rule, ...] = (
    Rule(
        rule_id="ANNEX_II.A",
        citation="Anhang II Teil A MiCAR",
        section="issuer",
        label="Information about the issuer of the ART (legal form, governance, prudential profile)",
        required_terms=("issuer", "legal form", "registered", "address", "management body"),
        required_terms_de=("emittent", "rechtsform", "eingetragen", "anschrift", "leitungsorgan"),
        min_words=80,
        severity=Severity.BLOCKER,
    ),
    Rule(
        rule_id="ANNEX_II.B",
        citation="Anhang II Teil B MiCAR",
        section="art",
        label="Information about the asset-referenced token (reference assets, stabilisation mechanism)",
        required_terms=("asset-referenced", "reference assets", "stabilisation", "basket"),
        required_terms_de=("vermögenswertreferenziert", "referenzwerte", "stabilisierung", "korb"),
        min_words=80,
        severity=Severity.BLOCKER,
    ),
    Rule(
        rule_id="ANNEX_II.C",
        citation="Anhang II Teil C MiCAR",
        section="offer_or_admission",
        label="Information about the offer to the public of the ART or its admission to trading",
        required_terms=("offer", "issuance", "subscription", "target market", "jurisdictions"),
        required_terms_de=("angebot", "emission", "zeichnung", "zielmarkt", "jurisdiktionen"),
        min_words=60,
        severity=Severity.BLOCKER,
    ),
    Rule(
        rule_id="ANNEX_II.D",
        citation="Anhang II Teil D i.V.m. Art. 39 MiCAR",
        section="rights_and_obligations",
        label="Rights and obligations of holders (redemption right at par, complaints handling)",
        required_terms=("rights", "redemption", "at par", "complaints", "holder"),
        required_terms_de=("rechte", "rückzahlung", "zu par", "beschwerden", "inhaber"),
        min_words=80,
        severity=Severity.BLOCKER,
    ),
    Rule(
        rule_id="ANNEX_II.E",
        citation="Anhang II Teil E MiCAR",
        section="technology",
        label="Information on the underlying technology (DLT, custody architecture, key management)",
        required_terms=("protocol", "consensus", "custody", "key management", "audit"),
        required_terms_de=("protokoll", "konsens", "verwahrung", "schlüsselverwaltung", "prüfung"),
        min_words=70,
        severity=Severity.BLOCKER,
    ),
    Rule(
        rule_id="ANNEX_II.F",
        citation="Anhang II Teil F MiCAR",
        section="risks",
        label="Risk factors specific to ARTs (de-pegging, reserve impairment, redemption suspension)",
        required_terms=(
            "market",
            "credit",
            "liquidity",
            "operational",
            "de-peg",
            "redemption",
            "reserve",
        ),
        required_terms_de=(
            "markt",
            "kredit",
            "liquidität",
            "operativ",
            "de-peg",
            "rücknahme",
            "reserve",
        ),
        min_words=150,
        severity=Severity.BLOCKER,
    ),
    Rule(
        rule_id="ANNEX_II.G.COMPOSITION",
        citation="Anhang II Teil G i.V.m. Art. 36 Abs. 1 MiCAR",
        section="reserve_of_assets",
        label="Reserve composition and investment limits (Art. 36(1) MiCAR / EBA RTS)",
        required_terms=("reserve", "composition", "deposit", "concentration"),
        required_terms_de=("reserve", "zusammensetzung", "einlagen", "konzentration"),
        required_patterns=(r"(30\s*%|thirty\s*percent)",),
        required_patterns_de=(r"(30\s*%|dreißig\s*prozent)",),
        min_words=60,
        severity=Severity.BLOCKER,
    ),
    Rule(
        rule_id="ANNEX_II.G.CUSTODY",
        citation="Anhang II Teil G i.V.m. Art. 36 Abs. 2, Art. 37 MiCAR",
        section="reserve_of_assets",
        label="Custody policy and custodian selection (Art. 36(2) MiCAR)",
        required_terms=("custody", "custodian", "segregation", "insolvency"),
        required_terms_de=("verwahrung", "verwahrstelle", "trennung", "insolvenz"),
        min_words=60,
        severity=Severity.BLOCKER,
    ),
    Rule(
        rule_id="ANNEX_II.G.VALUATION_AUDIT",
        citation="Anhang II Teil G i.V.m. Art. 36 Abs. 3 MiCAR",
        section="reserve_of_assets",
        label="Valuation procedure and audit frequency (Art. 36(3) MiCAR)",
        required_terms=("valuation", "audit"),
        required_terms_de=("bewertung", "prüfung"),
        min_words=50,
        severity=Severity.BLOCKER,
    ),
    Rule(
        rule_id="ANNEX_II.H",
        citation="Anhang II Teil H i.V.m. ESMA RTS on sustainability indicators",
        section="environmental_impact",
        label="Principal adverse environmental and climate-related impact of the consensus mechanism",
        required_terms=("consensus", "energy", "climate", "environmental"),
        required_terms_de=("konsens", "energie", "klima", "umwelt"),
        min_words=80,
        severity=Severity.MAJOR,
    ),
    Rule(
        rule_id="ANNEX_II.I",
        citation="Anhang II Teil I i.V.m. Art. 39 MiCAR",
        section="redemption",
        label="Redemption rights and procedure (timing, fees, suspension conditions)",
        required_terms=("redemption", "at par", "procedure", "timing", "fees", "suspension"),
        required_terms_de=("rücknahme", "zu par", "verfahren", "zeitplan", "gebühren", "aussetzung"),
        min_words=100,
        severity=Severity.BLOCKER,
    ),
)
