"""Cross-cutting disclosures that apply to every MiCAR white paper.

Art. 6(2), Art. 19(2) and Art. 51(2) MiCAR each require the white paper to be
fair, clear and not misleading. The risk warning, the management-body statement,
the summary and the date of notification are mandated for all three regimes
(Art. 6(5) to (8), Art. 19(4) to (7), Art. 51(4) to (7) MiCAR).

These checks run before the Annex-specific ruleset.
"""

from __future__ import annotations

from dataclasses import replace

from micar_linter.rules.base import Rule, Severity

COMMON_RULES: tuple[Rule, ...] = (
    Rule(
        rule_id="COMMON.SUMMARY",
        citation="Art. 6 Abs. 7, Art. 19 Abs. 6, Art. 51 Abs. 6 MiCAR",
        section="summary",
        label="Plain-language summary",
        required_terms=("summary", "key information"),
        required_terms_de=("zusammenfassung", "wesentliche informationen"),
        min_words=80,
        severity=Severity.BLOCKER,
    ),
    # Art. 6 Abs. 5 and Art. 19 Abs. 4 MiCAR: the crypto-asset may lose its value, may not always be
    # transferable and may not be liquid, and investor compensation and deposit guarantee schemes do not
    # cover it. The terms come from the Regulation's wording of each statement; in German, "wert" would
    # match every "Kryptowert". The utility-token statement of Art. 6 Abs. 5 Buchst. d applies to
    # utility tokens only and is not checked. In German the statements fit in about 25 words.
    Rule(
        rule_id="COMMON.RISK_WARNING",
        citation="Art. 6 Abs. 5, Art. 19 Abs. 4, Art. 51 Abs. 4 MiCAR",
        section="risk_warning",
        label="Mandatory risk warning statement",
        required_terms=(
            "lose",
            "value",
            "transferable",
            "liquid",
            "investor compensation",
            "deposit guarantee",
        ),
        required_terms_de=("verlier", "übertragbar", "liquid", "entschädigung", "einlagensicherung"),
        min_words=20,
        severity=Severity.BLOCKER,
    ),
    Rule(
        rule_id="COMMON.MANAGEMENT_STATEMENT",
        citation="Art. 6 Abs. 6, Art. 19 Abs. 5, Art. 51 Abs. 5 MiCAR",
        section="management_statement",
        label="Statement by the management body on completeness, fairness, and clarity",
        required_terms=("management body", "complies", "fair", "clear", "not misleading"),
        required_terms_de=("leitungsorgan", "entspricht", "redlich", "eindeutig", "nicht irreführend"),
        min_words=40,
        severity=Severity.BLOCKER,
    ),
    Rule(
        rule_id="COMMON.NOTIFICATION_DATE",
        citation="Art. 6 Abs. 8, Art. 19 Abs. 7, Art. 51 Abs. 7 MiCAR",
        section="notification_date",
        label="Date of notification to the competent authority",
        required_terms=("date",),
        required_terms_de=("datum",),
        min_words=5,
        severity=Severity.MAJOR,
    ),
    Rule(
        rule_id="COMMON.LANGUAGE",
        citation="Art. 6 Abs. 9, Art. 19 Abs. 8, Art. 51 Abs. 8 MiCAR",
        section="language",
        label=(
            "Language of the white paper "
            "(home Member State official language or customary in international finance)"
        ),
        required_terms=("language",),
        required_terms_de=("sprache",),
        min_words=10,
        severity=Severity.MAJOR,
    ),
    Rule(
        rule_id="COMMON.IXBRL_TAGGING",
        citation="Art. 2 VO (EU) 2024/2984",
        section="ixbrl_tagging",
        label="Inline XBRL (iXBRL) compliance and ESMA metadata tagging",
        min_words=0,
        severity=Severity.BLOCKER,
    ),
    # The two LEI rules read every section and check identifiers offline (micar_linter.lei).
    # Point 5 of each party Part names the LEI or another identifier required under national law,
    # and Art. 2 Abs. 1 Buchst. b and c VO (EU) 2024/2984 ask for the LEI where available.
    Rule(
        rule_id="COMMON.LEI_CHECK_DIGITS",
        citation=(
            "Anhang I Teil A Nr. 5, Teil B Nr. 5, Teil C Nr. 5, Anhang II Teil A Nr. 5, "
            "Anhang III Teil A Nr. 5 MiCAR"
        ),
        section="issuer",
        label="Legal Entity Identifier format and check digits (ISO 17442, ISO/IEC 7064 MOD 97-10)",
        min_words=0,
        severity=Severity.MAJOR,
    ),
    Rule(
        rule_id="COMMON.LEI_CONSISTENCY",
        citation=(
            "Anhang I Teil A Nr. 5, Teil B Nr. 5, Teil C Nr. 5, Anhang II Teil A Nr. 5, "
            "Anhang III Teil A Nr. 5 MiCAR"
        ),
        section="issuer",
        label="Legal Entity Identifiers agree across the party sections and the rest of the draft",
        min_words=0,
        severity=Severity.MAJOR,
    ),
)

# Art. 51 Abs. 4 MiCAR asks an e-money token white paper only to warn that investor compensation
# and deposit guarantee schemes do not cover the token. The loss-of-value, transferability and
# liquidity statements of Art. 6 Abs. 5 and Art. 19 Abs. 4 have no counterpart there.
EMT_COMMON_RULES: tuple[Rule, ...] = tuple(
    replace(
        rule,
        required_terms=("investor compensation", "deposit guarantee"),
        required_terms_de=("entschädigung", "einlagensicherung"),
    )
    if rule.rule_id == "COMMON.RISK_WARNING"
    else rule
    for rule in COMMON_RULES
)
