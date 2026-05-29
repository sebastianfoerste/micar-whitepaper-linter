"""Annex III MiCAR — e-money tokens (EMTs).

Reference: Anhang III VO (EU) 2023/1114 i.V.m. Art. 51 MiCAR.

EMT issuance is reserved for credit institutions or authorised e-money
institutions (Art. 48(1) MiCAR). The white paper must describe the e-money
licensing chain, the par-value redemption right (Art. 49(3) MiCAR), and the
safeguarding arrangements under the EMD2 regime (referenced via Art. 54
MiCAR).

Scaffold note: rules below cover each Part of Annex III at the Part level.
Point-level extensions are the practitioner's contribution.
"""

from __future__ import annotations

from micar_linter.rules.base import Rule, Severity

ANNEX_III_RULES: tuple[Rule, ...] = (
    Rule(
        rule_id="ANNEX_III.A",
        citation="Anhang III Teil A MiCAR",
        section="issuer",
        label="Information about the issuer of the EMT (credit institution or e-money institution)",
        required_terms=(
            "issuer",
            "credit institution",
            "e-money institution",
            "registered",
            "address",
        ),
        required_terms_de=(
            "emittent",
            "kreditinstitut",
            "e-geld-institut",
            "eingetragen",
            "anschrift",
        ),
        min_words=80,
        severity=Severity.BLOCKER,
    ),
    Rule(
        rule_id="ANNEX_III.B",
        citation="Anhang III Teil B MiCAR",
        section="emt",
        label="Information about the e-money token (referenced currency, denomination)",
        required_terms=("e-money token", "referenced", "official currency", "denomination"),
        required_terms_de=("e-geld-token", "referenziert", "offizielle währung", "stückelung"),
        min_words=60,
        severity=Severity.BLOCKER,
    ),
    Rule(
        rule_id="ANNEX_III.C",
        citation="Anhang III Teil C MiCAR",
        section="offer_or_admission",
        label="Information about the offer to the public of the EMT or its admission to trading",
        required_terms=("offer", "issuance", "subscription", "target market"),
        required_terms_de=("angebot", "emission", "zeichnung", "zielmarkt"),
        min_words=60,
        severity=Severity.BLOCKER,
    ),
    Rule(
        rule_id="ANNEX_III.D",
        citation="Anhang III Teil D i.V.m. Art. 49 Abs. 3 MiCAR",
        section="rights_and_obligations",
        label="Rights and obligations of holders (redemption at par value, no interest)",
        required_terms=("rights", "redemption", "at par", "no interest", "holder"),
        required_terms_de=("rechte", "rückzahlung", "zu par", "keine zinsen", "inhaber"),
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
        citation="Anhang III Teil G i.V.m. ESMA RTS on sustainability indicators",
        section="environmental_impact",
        label="Principal adverse environmental and climate-related impact of the consensus mechanism",
        required_terms=("consensus", "energy", "climate", "environmental"),
        required_terms_de=("konsens", "energie", "klima", "umwelt"),
        min_words=80,
        severity=Severity.MAJOR,
    ),
    Rule(
        rule_id="ANNEX_III.SAFEGUARDING",
        citation="Art. 54 MiCAR i.V.m. Art. 7 EMD2 (Richtlinie 2009/110/EG)",
        section="safeguarding",
        label="Safeguarding of funds received against EMT issuance",
        required_terms=("safeguarding", "segregated", "credit institution", "insolvency"),
        required_terms_de=("absicherung", "getrennt", "kreditinstitut", "insolvenz"),
        min_words=60,
        severity=Severity.BLOCKER,
    ),
)
