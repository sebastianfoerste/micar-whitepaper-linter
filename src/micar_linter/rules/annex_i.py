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

# Art. 6(3) MiCAR prescribes this first-page statement word for word. "Offeror" is
# replaced by "person seeking admission to trading" or "operator of the trading
# platform" where that person drew up the white paper, so the English check takes the
# part of the sentence common to all three. The linter cannot see page placement.
# The German wording was read from secondary reproductions of the official text; the
# check stops before the variable subject of the second sentence.
NOT_APPROVED_STATEMENT_EN = (
    "this crypto-asset white paper has not been approved by any competent authority "
    "in any member state of the european union"
)
NOT_APPROVED_STATEMENT_DE = (
    "dieses kryptowerte-whitepaper wurde von keiner zuständigen behörde eines "
    "mitgliedstaats der europäischen union genehmigt"
)
SOLE_RESPONSIBILITY_DE = "trägt die alleinige verantwortung für den inhalt dieses kryptowerte-whitepapers"

ANNEX_I_RULES: tuple[Rule, ...] = (
    Rule(
        rule_id="ANNEX_I.NOT_APPROVED_STATEMENT",
        citation="Art. 6 Abs. 3 MiCAR",
        section="not_approved_statement",
        label="First-page statement that no competent authority has approved the white paper",
        required_terms=(
            NOT_APPROVED_STATEMENT_EN,
            "of the crypto-asset is solely responsible for the content of this crypto-asset white paper",
        ),
        required_terms_de=(NOT_APPROVED_STATEMENT_DE, SOLE_RESPONSIBILITY_DE),
        min_words=0,
        severity=Severity.BLOCKER,
    ),
    Rule(
        rule_id="ANNEX_I.A",
        citation="Anhang I Teil A MiCAR",
        section="offeror",
        label="Information about the offeror or person seeking admission to trading",
        required_terms=("name", "legal form", "registered", "address"),
        required_terms_de=("name", "rechtsform", "eingetragen", "anschrift"),
        min_words=50,
        severity=Severity.BLOCKER,
    ),
    Rule(
        rule_id="ANNEX_I.B",
        citation="Anhang I Teil B MiCAR",
        section="issuer",
        label="Information about the issuer, if different from the offeror or person seeking admission",
        required_terms=("issuer", "registered", "address"),
        required_terms_de=("emittent", "eingetragen", "anschrift"),
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
    Rule(
        rule_id="ANNEX_I.D",
        citation="Anhang I Teil D MiCAR",
        section="project",
        label="Information about the crypto-asset project",
        required_terms=("project", "purpose", "business model", "team"),
        required_terms_de=("projekt", "zweck", "geschäftsmodell", "team"),
        min_words=80,
        severity=Severity.BLOCKER,
    ),
    Rule(
        rule_id="ANNEX_I.E",
        citation="Anhang I Teil E MiCAR",
        section="offer_or_admission",
        label="Information about the offer to the public or admission to trading",
        required_terms=("offer", "price", "subscription", "target", "jurisdictions"),
        required_terms_de=("angebot", "preis", "zeichnung", "ziel", "jurisdiktionen"),
        min_words=60,
        severity=Severity.BLOCKER,
    ),
    Rule(
        rule_id="ANNEX_I.F",
        citation="Anhang I Teil F MiCAR",
        section="crypto_asset",
        label="Information about the crypto-asset (type, characteristics, functionality)",
        required_terms=("crypto-asset", "supply", "transfer", "functionality"),
        required_terms_de=("kryptowertpapier", "angebot", "übertragung", "funktionsweise"),
        min_words=60,
        severity=Severity.BLOCKER,
    ),
    Rule(
        rule_id="ANNEX_I.G",
        citation="Anhang I Teil G MiCAR",
        section="rights_and_obligations",
        label="Rights and obligations attached to the crypto-asset",
        required_terms=("rights", "obligations", "holder", "enforce"),
        required_terms_de=("rechte", "pflichten", "inhaber", "durchsetzen"),
        min_words=60,
        severity=Severity.BLOCKER,
    ),
    Rule(
        rule_id="ANNEX_I.H",
        citation="Anhang I Teil H MiCAR",
        section="technology",
        label="Information on the underlying technology",
        required_terms=("protocol", "consensus", "smart contract", "audit"),
        required_terms_de=("protokoll", "konsens", "smart contract", "prüfung"),
        min_words=60,
        severity=Severity.BLOCKER,
    ),
    Rule(
        rule_id="ANNEX_I.I",
        citation="Anhang I Teil I MiCAR",
        section="risks",
        label="Risk factors (market, project, technology, mitigation measures)",
        required_terms=("market", "technology", "regulatory", "liquidity", "operational"),
        required_terms_de=("markt", "technologie", "regulatorisch", "liquidität", "operativ"),
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
        required_terms=("consensus", "energy", "climate", "environmental"),
        required_terms_de=("konsens", "energie", "klima", "umwelt"),
        min_words=80,
        severity=Severity.MAJOR,
    ),
)
