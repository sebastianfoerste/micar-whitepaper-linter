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
from micar_linter.rules.terms import (
    ADDRESS_DE,
    ADDRESS_EN,
    COURT_DE,
    FEE_DE,
    FEE_EN,
    OFFER_DE,
    OFFER_EN,
    PERMANENT_DE,
    PERMANENT_EN,
    REFERENCED_ASSET_DE,
    REFERENCED_ASSET_EN,
    SUSPENSION_DE,
    SUSPENSION_EN,
    VALUATION_DE,
    VALUATION_EN,
)

ANNEX_II_RULES: tuple[Rule, ...] = (
    Rule(
        rule_id="ANNEX_II.A",
        citation="Anhang II Teil A MiCAR",
        section="issuer",
        label="Information about the issuer of the ART (identity, management body, governance arrangements)",
        # Legal form and registered address are not asked for: a white paper that gives an LEI
        # need not state them (recital 2 and Anhang Tabelle 3 Teil A VO (EU) 2024/2984). The address
        # term looks for the business addresses of the management body (Nr. 7), not the e-mail address.
        required_terms=("issuer", "management body"),
        required_terms_de=("emittent", "leitungsorgan"),
        required_patterns=(ADDRESS_EN,),
        required_patterns_de=(ADDRESS_DE,),
        min_words=80,
        severity=Severity.BLOCKER,
    ),
    # Anhang II Teil B asks for the token's characteristics (Nr. 2) and the plans for the token with
    # its past and future milestones ("Etappen", Nr. 5). The referenced assets are an item of Teil D
    # Nr. 10 (ANNEX_II.G.VALUATION_AUDIT), the alignment of the reserve with the claim one of Teil G
    # Nr. 1 (ANNEX_II.G.COMPOSITION_DISCLOSURE).
    Rule(
        rule_id="ANNEX_II.B",
        citation="Anhang II Teil B MiCAR",
        section="art",
        label="Information about the asset-referenced token (characteristics, plans and milestones)",
        required_terms=("characteristics", "milestones"),
        required_terms_de=("merkmale", "etappen"),
        min_words=80,
        severity=Severity.BLOCKER,
    ),
    # Anhang II Teil C Nr. 4: the prospective holders targeted by the offer ("potenziellen Inhaber");
    # Nr. 15: the law applicable to the offer and the competent court ("Gericht", not "ausgerichtet").
    Rule(
        rule_id="ANNEX_II.C",
        citation="Anhang II Teil C MiCAR",
        section="offer_or_admission",
        label="Information about the offer to the public of the ART or its admission to trading",
        required_terms=("offer", "holders", "court"),
        required_terms_de=("angebot", "inhaber"),
        required_patterns_de=(COURT_DE,),
        min_words=60,
        severity=Severity.BLOCKER,
    ),
    # Art. 39 Abs. 1 MiCAR grants ART holders a right of redemption at all times ("jederzeit"), which it
    # calls permanent ("dauerhaften Rücktauschrechte"); Anhang II Teil D Nr. 9 asks the white paper for
    # information on that right. Redemption at par value is the e-money token rule of Art. 49 Abs. 4 and
    # appears nowhere in Art. 39 or Annex II.
    Rule(
        rule_id="ANNEX_II.D",
        citation="Anhang II Teil D i.V.m. Art. 39 MiCAR",
        section="rights_and_obligations",
        label="Rights and obligations of holders (permanent right of redemption, complaints handling)",
        required_terms=("rights", "redemption", "complaints", "holder"),
        required_terms_de=("rechte", "rücktausch", "beschwerden", "inhaber"),
        required_patterns=(PERMANENT_EN,),
        required_patterns_de=(PERMANENT_DE,),
        min_words=80,
        severity=Severity.BLOCKER,
    ),
    # Anhang II Teil E covers the distributed ledger technology and protocols, the consensus mechanism,
    # incentives and fees, a ledger operated by the issuer and the audit outcome; no item asks for the
    # custody of keys.
    Rule(
        rule_id="ANNEX_II.E",
        citation="Anhang II Teil E MiCAR",
        section="technology",
        label="Information on the underlying technology (DLT, protocols, consensus mechanism, audit outcome)",
        required_terms=("ledger", "protocol", "consensus", "audit"),
        required_terms_de=("ledger", "protokoll", "konsens", "prüfung"),
        min_words=70,
        severity=Severity.BLOCKER,
    ),
    # Anhang II Teil F groups the risks by source: the reserve of assets, the issuer, the offer to the public
    # or the admission to trading, the token, its operationalisation and the technology. It asks for
    # mitigation measures only "if any" ("gegebenenfalls"), so the rule does not ask for them.
    Rule(
        rule_id="ANNEX_II.F",
        citation="Anhang II Teil F MiCAR",
        section="risks",
        label=(
            "Risk factors specific to ARTs (reserve of assets, issuer, offer or admission to trading, token, "
            "operationalisation, technology and any mitigation measures)"
        ),
        required_terms=("reserve", "issuer", "technology"),
        required_terms_de=("reserve", "emittent", "technologie"),
        required_patterns=(OFFER_EN,),
        required_patterns_de=(OFFER_DE,),
        min_words=150,
        severity=Severity.BLOCKER,
    ),
    # Anhang II Teil G Nr. 1: the mechanism aimed at aligning the value of the reserve with the claim
    # ("Angleichung"); Nr. 2: the reserve of assets and its composition. No Part G item asks for the
    # minimum deposits of Art. 36 Abs. 4 or the concentration risk of the stabilisation policy
    # (Art. 36 Abs. 8 Buchst. c).
    Rule(
        rule_id="ANNEX_II.G.COMPOSITION_DISCLOSURE",
        citation="Anhang II Teil G Nr. 1 und 2 MiCAR",
        section="reserve_of_assets",
        label="Reserve composition and value alignment mechanism (Annex II Part G Nos. 1 and 2 MiCAR)",
        required_terms=("reserve", "composition", "align"),
        required_terms_de=("reserve", "zusammensetzung", "angleich"),
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
        label="Custody of the reserve assets (Art. 37 MiCAR) and their legal segregation (Art. 36(2) MiCAR)",
        required_terms=("custody", "custodian", "segregation", "insolvency"),
        required_terms_de=("verwahrung", "verwahrstelle", "trennung", "insolvenz"),
        min_words=60,
        severity=Severity.BLOCKER,
    ),
    # Anhang II Teil G has no valuation or audit item. Teil D Nr. 10 describes the claim the token
    # represents: Buchst. a each referenced asset ("jedes referenzierten Vermögenswerts"), Buchst. c how
    # a fair and transparent valuation of the components of the claim is undertaken. The rule therefore
    # reads the rights section. No Annex II item asks for the six-monthly reserve audit of Art. 36
    # Abs. 9. The ID keeps "G" so that SARIF results and rule-page links stay valid.
    Rule(
        rule_id="ANNEX_II.G.VALUATION_AUDIT",
        citation="Anhang II Teil D Nr. 10 MiCAR",
        section="rights_and_obligations",
        label="Referenced assets and valuation of the components of the claim (Annex II Part D No. 10 MiCAR)",
        required_patterns=(REFERENCED_ASSET_EN, VALUATION_EN),
        required_patterns_de=(REFERENCED_ASSET_DE, VALUATION_DE),
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
    # Art. 39 Abs. 2 MiCAR: redemption by paying funds other than electronic money equal to the market value
    # of the referenced assets, or by delivering them, under a policy that sets the periods and timeframes.
    # Art. 39 Abs. 3: no fee, without prejudice to Art. 46, whose recovery plan must include liquidity fees
    # on redemptions and suspension of redemptions among its options (Abs. 1 UAbs. 3 Buchst. a and c); in
    # the circumstances of Abs. 3 the competent authority may temporarily suspend redemption where the
    # suspension is justified having regard to the interests of the holders and financial stability (Abs. 4).
    # Anhang II Teil D Nr. 14 covers the holders' rights under the recovery plan.
    Rule(
        rule_id="ANNEX_II.I",
        citation=(
            "Anhang II Teil D Nr. 9, 14, 15 und 16, Teil G Nr. 3 i.V.m. Art. 39, "
            "Art. 46 Abs. 1 UAbs. 3 Buchst. c und Art. 46 Abs. 4 MiCAR"
        ),
        section="redemption",
        label="Redemption rights and procedure (timing, fees, suspension conditions)",
        required_terms=("redemption", "market value", "procedure", "timeframe"),
        required_terms_de=("rücktausch", "marktwert", "verfahren", "zeitrahmen"),
        required_patterns=(FEE_EN, SUSPENSION_EN),
        required_patterns_de=(FEE_DE, SUSPENSION_DE),
        min_words=100,
        severity=Severity.BLOCKER,
    ),
)
