"""Annex I MiCAR - crypto-assets other than ARTs and EMTs.

Reference: Anhang I VO (EU) 2023/1114 i.V.m. Art. 6 MiCAR.

Annex I is structured as Parts A through I. Each Part bundles point-level
disclosure requirements. The rules below are scaffolded at the Part level;
point-level granularity (e.g. Annex I, Part D, point 5) is left as a
deliberate extension point - those interpretive calls are the practising
lawyer's contribution and are tracked in the project issues.

ANNEX_I.J covers the sustainability disclosure under Art. 6(1), first
subparagraph, point (j) MiCAR, which the template in Implementing Regulation
(EU) 2024/2984 places in Part J.
"""

from __future__ import annotations

from micar_linter.rules.base import Rule, Severity

ANNEX_I_RULES: tuple[Rule, ...] = (
    # A white paper that gives an LEI need not state the legal form or the registered address
    # (recital 2 and Anhang Tabelle 2 Teil A to C VO (EU) 2024/2984), so the party rules do not
    # ask for them. Every party Part asks for the business addresses of the management body.
    Rule(
        rule_id="ANNEX_I.A",
        citation="Anhang I Teil A MiCAR",
        section="offeror",
        label="Information about the offeror or person seeking admission to trading",
        required_terms=("name", "address"),
        required_terms_de=("name", "anschrift"),
        min_words=50,
        severity=Severity.BLOCKER,
    ),
    Rule(
        rule_id="ANNEX_I.B",
        citation="Anhang I Teil B MiCAR",
        section="issuer",
        label="Information about the issuer, if different from the offeror or person seeking admission",
        required_terms=("issuer", "address"),
        required_terms_de=("emittent", "anschrift"),
        min_words=40,
    ),
    Rule(
        rule_id="ANNEX_I.C",
        citation="Anhang I Teil C MiCAR",
        section="trading_platform_operator",
        label="Information about the operator of the trading platform, where applicable",
        required_terms=("trading platform", "operator"),
        required_terms_de=("handelsplattform", "betreiber"),
        min_words=20,
        severity=Severity.MINOR,
    ),
    # Anhang I Teil D Nr. 5 asks for the past and future milestones of the project ("Projekt-Etappen").
    Rule(
        rule_id="ANNEX_I.D",
        citation="Anhang I Teil D MiCAR",
        section="project",
        label="Information about the crypto-asset project",
        required_terms=("project", "milestones"),
        required_terms_de=("projekt", "etappen"),
        min_words=80,
        severity=Severity.BLOCKER,
    ),
    # Anhang I Teil E Nr. 19: the law applicable to the offer and the competent court ("Gericht").
    Rule(
        rule_id="ANNEX_I.E",
        citation="Anhang I Teil E MiCAR",
        section="offer_or_admission",
        label="Information about the offer to the public or admission to trading",
        required_terms=("offer", "price", "subscription", "target", "court"),
        required_terms_de=("angebot", "preis", "zeichnung", "ziel", "gericht"),
        min_words=60,
        severity=Severity.BLOCKER,
    ),
    # Anhang I Teil F Nr. 2: the characteristics and functionality ("Merkmale ... und Funktionen").
    # Supply protocols and transfer restrictions are items of Teil G (Nr. 7 and 8).
    Rule(
        rule_id="ANNEX_I.F",
        citation="Anhang I Teil F MiCAR",
        section="crypto_asset",
        label="Information about the crypto-asset (type, characteristics, functionality)",
        required_terms=("characteristics", "functionality"),
        required_terms_de=("merkmale", "funktion"),
        min_words=60,
        severity=Severity.BLOCKER,
    ),
    # Anhang I Teil G Nr. 1: the procedure and conditions for the exercise of the rights ("Ausübung");
    # Nr. 10: the applicable law and the competent court.
    Rule(
        rule_id="ANNEX_I.G",
        citation="Anhang I Teil G MiCAR",
        section="rights_and_obligations",
        label="Rights and obligations attached to the crypto-asset",
        required_terms=("rights", "obligations", "exercise", "court"),
        required_terms_de=("rechte", "pflichten", "ausübung", "gericht"),
        min_words=60,
        severity=Severity.BLOCKER,
    ),
    # Anhang I Teil H Nr. 1 names the distributed ledger technology, protocols and technical standards; a
    # token can run without smart contracts.
    Rule(
        rule_id="ANNEX_I.H",
        citation="Anhang I Teil H MiCAR",
        section="technology",
        label="Information on the underlying technology",
        required_terms=("protocol", "consensus", "ledger", "audit"),
        required_terms_de=("protokoll", "konsens", "ledger", "prüfung"),
        min_words=60,
        severity=Severity.BLOCKER,
    ),
    # Anhang I Teil I groups the risks by source: the offer, the issuer, the crypto-assets, project
    # implementation ("Projektdurchführung") and the technology with mitigation measures ("Risikominderung").
    Rule(
        rule_id="ANNEX_I.I",
        citation="Anhang I Teil I MiCAR",
        section="risks",
        label=(
            "Risk factors (offer, issuer, crypto-assets, project implementation, technology, "
            "mitigation measures)"
        ),
        required_terms=("offer", "project", "technology", "mitigation"),
        required_terms_de=("angebot", "projekt", "technologie", "minderung"),
        min_words=120,
        severity=Severity.BLOCKER,
    ),
    Rule(
        rule_id="ANNEX_I.J",
        citation=(
            "Art. 6 Abs. 1 UAbs. 1 Buchst. j MiCAR i.V.m. Art. 4 VO (EU) 2025/422; "
            "Anhang Tabelle 2 Teil J VO (EU) 2024/2984"
        ),
        section="environmental_impact",
        label="Principal adverse environmental and climate-related impact of the consensus mechanism",
        required_terms=("consensus", "energy", "climate", "environment"),
        required_terms_de=("konsens", "energie", "klima", "umwelt"),
        min_words=80,
        severity=Severity.MAJOR,
    ),
)
