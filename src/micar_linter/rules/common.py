"""Cross-cutting disclosures that apply to every MiCAR white paper.

Art. 6(1), Art. 19(1), and Art. 51(1) MiCAR each require the white paper to be
fair, clear, and not misleading. The summary, the date of notification, the
required risk warning, and the management-body statement are mandated for all
three regimes (Art. 6(5)-(6), Art. 19(5)-(6), Art. 51(5)-(6) MiCAR).

These checks run before the Annex-specific ruleset.
"""

from __future__ import annotations

from micar_linter.rules.base import Rule, Severity

COMMON_RULES: tuple[Rule, ...] = (
    Rule(
        rule_id="COMMON.SUMMARY",
        citation="Art. 6 Abs. 7, Art. 19 Abs. 7, Art. 51 Abs. 7 MiCAR",
        section="summary",
        label="Plain-language summary",
        required_terms=("summary", "key information"),
        required_terms_de=("zusammenfassung", "wesentliche informationen"),
        min_words=80,
        severity=Severity.BLOCKER,
    ),
    Rule(
        rule_id="COMMON.RISK_WARNING",
        citation="Art. 6 Abs. 5, Art. 19 Abs. 5, Art. 51 Abs. 5 MiCAR",
        section="risk_warning",
        label="Mandatory risk warning statement",
        required_terms=("risk", "value", "loss"),
        required_terms_de=("risiko", "wert", "verlust"),
        min_words=40,
        severity=Severity.BLOCKER,
    ),
    Rule(
        rule_id="COMMON.MANAGEMENT_STATEMENT",
        citation="Art. 6 Abs. 6, Art. 19 Abs. 6, Art. 51 Abs. 6 MiCAR",
        section="management_statement",
        label="Statement by the management body on completeness, fairness, and clarity",
        required_terms=("management body", "complies", "fair", "clear", "not misleading"),
        required_terms_de=("leitungsorgan", "entspricht", "redlich", "eindeutig", "nicht irreführend"),
        min_words=40,
        severity=Severity.BLOCKER,
    ),
    Rule(
        rule_id="COMMON.NOTIFICATION_DATE",
        citation="Art. 8 Abs. 1, Art. 17, Art. 49 MiCAR",
        section="notification_date",
        label="Date of notification to the competent authority",
        required_terms=("date",),
        required_terms_de=("datum",),
        min_words=5,
        severity=Severity.MAJOR,
    ),
    Rule(
        rule_id="COMMON.LANGUAGE",
        citation="Art. 6 Abs. 12, Art. 19 Abs. 11, Art. 51 Abs. 10 MiCAR",
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
)
