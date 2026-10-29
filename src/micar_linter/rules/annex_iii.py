"""Annex III MiCAR - e-money tokens (EMTs).

Reference: Anhang III VO (EU) 2023/1114 i.V.m. Art. 51 MiCAR.

Only the issuer of an EMT may offer it to the public or seek its admission
to trading in the Union, and only if it is authorised as a credit institution
or an electronic money institution and has notified and published a white
paper under Art. 51; other persons may do so with the issuer's written
consent and must comply with Arts. 50 and 53 (Art. 48(1) MiCAR). The issuers
and tokens exempted under Art. 48(4) and (5) still draw up and notify a white
paper (Art. 48(7)).
The white paper describes the issuer and its authorisation or exemption, the
redemption right at par value (Art. 49(4) MiCAR) and the rights of holders,
including in insolvency. Art. 54 MiCAR governs the investment of the funds
received; no Annex III item asks the white paper to describe their
safeguarding.

Scaffold note: rules below cover each Part of Annex III at the Part level.
Point-level extensions are the practitioner's contribution.
"""

from __future__ import annotations

from micar_linter.rules.annex_i import NOT_APPROVED_STATEMENT_EN, NOT_APPROVED_STATEMENT_LABEL
from micar_linter.rules.base import Rule, Severity
from micar_linter.rules.terms import ADDRESS_DE, ADDRESS_EN, COURT_DE

ANNEX_III_RULES: tuple[Rule, ...] = (
    Rule(
        # Art. 51(3) MiCAR: the same first-page statement, naming the issuer. Art. 19 MiCAR
        # prescribes no such statement for an ART white paper, so Annex II has no
        # counterpart: Table 3 field I.02 of Implementing Regulation (EU) 2024/2984 holds
        # the Art. 19(4) warning instead. Approval is not the reason: the white paper of an
        # authorised issuer is deemed approved (Art. 21(1)) and that of a credit institution
        # is approved (Art. 17(1)(a)), but an issuer exempt under Art. 16(2) only notifies it.
        rule_id="ANNEX_III.NOT_APPROVED_STATEMENT",
        citation="Art. 51 Abs. 3 MiCAR",
        section="not_approved_statement",
        label=NOT_APPROVED_STATEMENT_LABEL,
        required_terms=(
            NOT_APPROVED_STATEMENT_EN,
            "the issuer of the crypto-asset is solely responsible for the content of this "
            "crypto-asset white paper",
        ),
        min_words=0,
        severity=Severity.BLOCKER,
    ),
    # An issuer is a credit institution or an electronic money institution, or exempt under
    # Art. 48 Abs. 4 or 5 MiCAR, so the rule names no institution type. A white paper that gives an
    # LEI need not state the legal form or the registered address (recital 2 and Anhang Tabelle 4
    # Teil A VO (EU) 2024/2984). The address term looks for the business addresses of the management
    # body, not the e-mail address.
    Rule(
        rule_id="ANNEX_III.A",
        citation="Anhang III Teil A MiCAR",
        section="issuer",
        label="Information about the issuer of the EMT (authorisation or exemption, management body)",
        required_terms=("issuer", "management body"),
        required_terms_de=("emittent", "leitungsorgan"),
        required_patterns=(ADDRESS_EN,),
        required_patterns_de=(ADDRESS_DE,),
        min_words=80,
        severity=Severity.BLOCKER,
    ),
    # Anhang III Teil B asks for the name, the characteristics ("Merkmale") and the persons involved.
    # Referencing one official currency is the definition in Art. 3 Abs. 1 Nr. 7 MiCAR; no Part B item
    # asks for it or for a denomination.
    Rule(
        rule_id="ANNEX_III.B",
        citation="Anhang III Teil B MiCAR",
        section="emt",
        label="Information about the e-money token (name, characteristics, persons involved)",
        required_terms=("e-money token", "characteristics"),
        required_terms_de=("e-geld-token", "merkmale"),
        min_words=60,
        severity=Severity.BLOCKER,
    ),
    # Anhang III Teil C has four items: offer or admission to trading, number of units, trading
    # platforms, and the applicable law and competent court ("Gericht", not "gerichtet").
    Rule(
        rule_id="ANNEX_III.C",
        citation="Anhang III Teil C MiCAR",
        section="offer_or_admission",
        label="Information about the offer to the public of the EMT or its admission to trading",
        required_terms=("offer", "court"),
        required_terms_de=("angebot",),
        required_patterns_de=(COURT_DE,),
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
    # Anhang III Teil E covers the distributed ledger technology and protocols, the purchaser's technical
    # requirements, the consensus mechanism, incentives and fees, a ledger operated by the issuer and the
    # audit outcome; no item asks for the custody of keys.
    Rule(
        rule_id="ANNEX_III.E",
        citation="Anhang III Teil E MiCAR",
        section="technology",
        label="Information on the underlying technology (DLT, protocols, consensus mechanism, audit outcome)",
        required_terms=("ledger", "protocol", "consensus", "audit"),
        required_terms_de=("ledger", "protokoll", "konsens", "prüfung"),
        min_words=60,
        severity=Severity.BLOCKER,
    ),
    # Anhang III Teil F has three items: the risks of the issuer, of the e-money token, and of the
    # technology. It asks for mitigation measures only "if any" ("gegebenenfalls"), so the rule does not
    # ask for them.
    Rule(
        rule_id="ANNEX_III.F",
        citation="Anhang III Teil F MiCAR",
        section="risks",
        label="Risk factors (issuer, e-money token, technology and any mitigation measures)",
        required_terms=("issuer", "technology"),
        required_terms_de=("emittent", "technologie"),
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
        label=(
            "Safeguarding of funds received against EMT issuance "
            "(review prompt; no Annex III item asks for safeguarding)"
        ),
        required_terms=("safeguard", "separate", "credit institution", "insolvency"),
        required_terms_de=("sicher", "gesondert", "kreditinstitut", "insolvenz"),
        min_words=60,
        severity=Severity.MAJOR,
    ),
)
