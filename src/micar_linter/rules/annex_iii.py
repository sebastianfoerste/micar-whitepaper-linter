"""Annex III MiCAR - e-money tokens (EMTs).

Reference: Anhang III VO (EU) 2023/1114 i.V.m. Art. 51 MiCAR.

EMT issuance is reserved for credit institutions and electronic money
institutions (Art. 48(1) MiCAR), save for the issuers and tokens exempted
under Art. 48(4) and (5), which still draw up a white paper (Art. 48(7)).
The white paper describes the issuer and its authorisation or exemption, the
redemption right at par value (Art. 49(4) MiCAR) and the rights of holders,
including in insolvency. Art. 54 MiCAR governs the investment of the funds
received; no Annex III item asks the white paper to describe their
safeguarding.

Scaffold note: rules below cover each Part of Annex III at the Part level.
Point-level extensions are the practitioner's contribution.
"""

from __future__ import annotations

from micar_linter.rules.base import Rule, Severity

ANNEX_III_RULES: tuple[Rule, ...] = (
    # An issuer is a credit institution or an electronic money institution, or exempt under
    # Art. 48 Abs. 4 or 5 MiCAR, so the rule names no institution type. A white paper that gives an
    # LEI need not state the legal form or the registered address (recital 2 and Anhang Tabelle 4
    # Teil A VO (EU) 2024/2984).
    Rule(
        rule_id="ANNEX_III.A",
        citation="Anhang III Teil A MiCAR",
        section="issuer",
        label="Information about the issuer of the EMT (authorisation or exemption, management body)",
        required_terms=("issuer", "address", "management body"),
        required_terms_de=("emittent", "anschrift", "leitungsorgan"),
        min_words=80,
        severity=Severity.BLOCKER,
    ),
    Rule(
        rule_id="ANNEX_III.B",
        citation="Anhang III Teil B MiCAR",
        section="emt",
        label="Information about the e-money token (referenced currency, denomination)",
        required_terms=("e-money token", "referenced", "official currency", "denomination"),
        # German MiCAR says "amtliche Währung".
        required_terms_de=("e-geld-token", "referenziert", "amtliche währung", "stückelung"),
        min_words=60,
        severity=Severity.BLOCKER,
    ),
    # Anhang III Teil C has four items: offer or admission to trading, number of units, trading
    # platforms, and the applicable law and competent court.
    Rule(
        rule_id="ANNEX_III.C",
        citation="Anhang III Teil C MiCAR",
        section="offer_or_admission",
        label="Information about the offer to the public of the EMT or its admission to trading",
        required_terms=("offer", "court"),
        required_terms_de=("angebot", "gericht"),
        min_words=60,
        severity=Severity.BLOCKER,
    ),
    # Anhang III Teil D Nr. 1 and Art. 49 Abs. 4 MiCAR: redemption at par value ("zum Nennwert");
    # MiCAR's German word for redemption is "Rücktausch". Teil D Nr. 6 asks for complaints handling.
    # The interest prohibition of Art. 50 Abs. 1 is no item the white paper must state.
    Rule(
        rule_id="ANNEX_III.D",
        citation="Anhang III Teil D i.V.m. Art. 49 Abs. 4 MiCAR",
        section="rights_and_obligations",
        label="Rights and obligations of holders (redemption at par value, complaints handling)",
        required_terms=("rights", "redemption", "at par", "complaints", "holder"),
        required_terms_de=("rechte", "rücktausch", "nennwert", "beschwerden", "inhaber"),
        min_words=80,
        severity=Severity.BLOCKER,
    ),
    Rule(
        rule_id="ANNEX_III.E",
        citation="Anhang III Teil E MiCAR",
        section="technology",
        label="Information on the underlying technology (DLT, custody, key management)",
        required_terms=("protocol", "consensus", "custody", "key management"),
        required_terms_de=("protokoll", "konsens", "verwahrung", "schlüsselverwaltung"),
        min_words=60,
        severity=Severity.BLOCKER,
    ),
    Rule(
        rule_id="ANNEX_III.F",
        citation="Anhang III Teil F MiCAR",
        section="risks",
        label="Risk factors specific to EMTs (safeguarding, redemption, operational)",
        required_terms=(
            "market",
            "credit",
            "liquidity",
            "operational",
            "redemption",
            "safeguarding",
        ),
        required_terms_de=(
            "markt",
            "kredit",
            "liquidität",
            "operativ",
            "rücknahme",
            "absicherung",
        ),
        min_words=120,
        severity=Severity.BLOCKER,
    ),
    Rule(
        rule_id="ANNEX_III.G",
        citation=(
            "Art. 51 Abs. 1 Buchst. g MiCAR i.V.m. Art. 4 VO (EU) 2025/422; "
            "Anhang Tabelle 4 Teil G VO (EU) 2024/2984"
        ),
        section="environmental_impact",
        label="Principal adverse environmental and climate-related impact of the consensus mechanism",
        required_terms=("consensus", "energy", "climate", "environment"),
        required_terms_de=("konsens", "energie", "klima", "umwelt"),
        min_words=80,
        severity=Severity.MAJOR,
    ),
    # No Annex III item and no field of Anhang Tabelle 4 VO (EU) 2024/2984 asks the white paper to
    # describe the safeguarding of the funds received, so the rule is a prompt for review with MAJOR
    # severity. Art. 54 MiCAR covers funds safeguarded under Art. 7 Abs. 1 EMD2, which addresses
    # electronic money institutions; Anhang III Teil D Nr. 3 asks for the holders' rights in
    # insolvency. The German stem "sicher" also matches "sichere Aktiva" (Art. 54 Buchst. b).
    Rule(
        rule_id="ANNEX_III.SAFEGUARDING",
        citation="Art. 54 MiCAR i.V.m. Art. 7 EMD2 (Richtlinie 2009/110/EG); Anhang III Teil D Nr. 3 MiCAR",
        section="safeguarding",
        label="Safeguarding of funds received against EMT issuance (review prompt; no Annex III item)",
        required_terms=("safeguard", "separate", "credit institution", "insolvency"),
        required_terms_de=("sicher", "gesondert", "kreditinstitut", "insolvenz"),
        min_words=60,
        severity=Severity.MAJOR,
    ),
)
