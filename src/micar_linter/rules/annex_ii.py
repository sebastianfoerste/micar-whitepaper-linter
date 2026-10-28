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
        # Legal form and registered address are not asked for: a white paper that gives an LEI
        # need not state them (recital 2 and Anhang Tabelle 3 Teil A VO (EU) 2024/2984).
        required_terms=("issuer", "address", "management body"),
        required_terms_de=("emittent", "anschrift", "leitungsorgan"),
        min_words=80,
        severity=Severity.BLOCKER,
    ),
    # An ART may reference a single value (Art. 3 Abs. 1 Nr. 6 MiCAR), so no basket is asked for.
    # German MiCAR spells the adjective "vermögenswertereferenziert" and "vermögenswertreferenziert";
    # the stem "referenziert" matches both.
    Rule(
        rule_id="ANNEX_II.B",
        citation="Anhang II Teil B MiCAR",
        section="art",
        label="Information about the asset-referenced token (reference assets, stabilisation mechanism)",
        required_terms=("asset-referenced", "reference assets", "stabilisation"),
        required_terms_de=("referenziert", "referenzwerte", "stabilisierung"),
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
    # Anhang II Teil D Nr. 9 and Art. 39 Abs. 1 MiCAR give ART holders a permanent right of
    # redemption ("dauerhafte Rücktauschrechte"). Redemption at par value is the e-money token rule
    # of Art. 49 Abs. 4 and appears nowhere in Art. 39 or Annex II.
    Rule(
        rule_id="ANNEX_II.D",
        citation="Anhang II Teil D i.V.m. Art. 39 MiCAR",
        section="rights_and_obligations",
        label="Rights and obligations of holders (permanent right of redemption, complaints handling)",
        required_terms=("rights", "redemption", "permanent", "complaints", "holder"),
        required_terms_de=("rechte", "rücktausch", "dauerhaft", "beschwerden", "inhaber"),
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
        rule_id="ANNEX_II.G.COMPOSITION_DISCLOSURE",
        citation="Anhang II Teil G i.V.m. Art. 36 MiCAR",
        section="reserve_of_assets",
        label="Reserve composition disclosure (Annex II Part G)",
        required_terms=("reserve", "composition", "deposit", "concentration"),
        required_terms_de=("reserve", "zusammensetzung", "einlagen", "konzentration"),
        min_words=60,
        severity=Severity.BLOCKER,
    ),
    Rule(
        # Disclosure completeness and substantive reserve compliance are separate
        # questions. This rule surfaces candidate floors for lawyer review and never
        # concludes compliance from draft-controlled text or metadata.
        # Art. 45(7)(b) binds EBA's RTS, not the issuer. A non-significant ART
        # reaches the 60 % figure only through Art. 35(4) extending Art. 45(3)
        # (EBA/RTS/2024/10, final report para. 23), so Art. 45(3) is the hinge.
        rule_id="ANNEX_II.G.DEPOSIT_FLOOR_REVIEW",
        citation=(
            "Anhang II Teil G i.V.m. Art. 35 Abs. 4, Art. 36 Abs. 4 Buchst. d, "
            "Art. 45 Abs. 3 und Art. 45 Abs. 7 Buchst. b MiCAR"
        ),
        section="reserve_of_assets",
        label=(
            "Candidate deposit floor for the reserve (30 % under Art. 36(4)(d); "
            "60 % under Art. 45(7)(b) for significant ARTs, or for non-significant "
            "ARTs via Arts. 35(4) and 45(3) MiCAR) - lawyer review required"
        ),
        min_words=0,
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
        citation=(
            "Art. 19 Abs. 1 UAbs. 1 Buchst. h MiCAR i.V.m. Art. 4 VO (EU) 2025/422; "
            "Anhang Tabelle 3 Teil H VO (EU) 2024/2984"
        ),
        section="environmental_impact",
        label="Principal adverse environmental and climate-related impact of the consensus mechanism",
        required_terms=("consensus", "energy", "climate", "environment"),
        required_terms_de=("konsens", "energie", "klima", "umwelt"),
        min_words=80,
        severity=Severity.MAJOR,
    ),
    # Art. 39 Abs. 2 MiCAR: redemption in funds at the market value of the referenced assets, or by
    # delivering them, under a policy that sets the periods and timeframes. Art. 39 Abs. 3: no fee,
    # without prejudice to Art. 46, whose recovery plan must include liquidity fees on redemptions and
    # suspension of redemptions among its options (Abs. 1 UAbs. 3 Buchst. a and c); the competent
    # authority may suspend redemption (Abs. 4). Anhang II Teil D Nr. 14 covers the holders' rights
    # under the recovery plan.
    Rule(
        rule_id="ANNEX_II.I",
        citation=(
            "Anhang II Teil D Nr. 9, 14, 15 und 16, Teil G Nr. 3 i.V.m. Art. 39, "
            "Art. 46 Abs. 1 UAbs. 3 Buchst. c und Art. 46 Abs. 4 MiCAR"
        ),
        section="redemption",
        label="Redemption rights and procedure (timing, fees, suspension conditions)",
        required_terms=("redemption", "market value", "procedure", "timeframe", "fee", "suspension"),
        required_terms_de=("rücktausch", "marktwert", "verfahren", "zeitrahmen", "gebühr", "aussetzung"),
        min_words=100,
        severity=Severity.BLOCKER,
    ),
)
