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
from micar_linter.rules.terms import TITLE_DE

# Wording that turns a required statement of the risk warning into its opposite: the listed terms appear,
# but the text says that the crypto-asset cannot lose its value, is always transferable or liquid, or is
# covered by investor compensation or deposit guarantee schemes. Each pattern has one named group, which a
# finding reports by name. The statements themselves do not match: "may not always be transferable",
# "is not covered by", "neither ... nor ... cover", "nicht immer übertragbar", "fällt nicht unter", and a
# sentence that says no one can guarantee the value holds.
_CANNOT_LOSE_EN = (
    r"(?P<it_cannot_lose_its_value>(?:^|(?<=[.!?;:]))"
    r"(?![^.!?;:]*\b(?:no|not|cannot|without)\s+(?:\w+\s+){0,2}?(?:guarantee|assur|warrant|promise))"
    r"[^.!?;:]*?\b(?:cannot|can\s?not|can['\u2019]t|will\s+not|won['\u2019]t|will\s+never|never|does\s+not|doesn['\u2019]t"
    r"|is\s+not\s+able\s+to)\s+(?:\w+\s+){0,2}?los(?:e|es|ing)\b)"
)
_ALWAYS_TRANSFERABLE_EN = (
    r"(?P<it_is_always_transferable>(?<!not )\balways\s+(?:be\s+)?(?:freely\s+)?transfer(?:able|red)\b"
    r"|(?<!not )(?<!not be )(?<!not be freely )\btransferable\s+at\s+(?:all|any)\s+times?\b)"
)
_ALWAYS_LIQUID_EN = (
    r"(?P<it_is_always_liquid>(?<!not )\balways\s+(?:be\s+)?liquid\b"
    r"|(?<!not )(?<!not be )\bliquid\s+at\s+all\s+times\b)"
)
_SCHEMES_COVER_EN = (
    r"(?P<a_compensation_or_guarantee_scheme_covers_it>"
    r"\b(?:is|are)\s+(?:fully\s+|also\s+)?(?:covered|protected)\s+by\s+(?:the\s+|an?\s+|any\s+)?(?:\w+\s+)?"
    r"(?:investor\s+compensation|deposit\s+guarantee)"
    r"|(?<!nor )(?<!nor the )(?<!neither )(?<!neither the )"
    r"\b(?:investor\s+compensation|deposit\s+guarantee)\s+"
    r"schemes?\s+(?:fully\s+|also\s+)?(?:cover|covers|protect|protects)\b)"
)
_CANNOT_LOSE_DE = (
    r"(?P<er_kann_seinen_Wert_nicht_verlieren>"
    r"\b(?:kann|können|wird|werden)\s+(?:(?:seinen|ihren|den)\s+Wert\s+)?"
    r"(?:nicht|niemals|nie)\s+(?:(?:ganz\s+oder\s+teilweise|teilweise\s+oder\s+ganz)\s+)?verlier\w*"
    r"|\bverlier\w*\s+(?:(?:seinen|ihren|den)\s+Wert\s+)?(?:nicht|niemals|nie)\b)"
)
_ALWAYS_TRANSFERABLE_DE = (
    r"(?P<er_ist_stets_übertragbar>(?<!nicht )\b(?:stets|immer|jederzeit)\s+(?:frei\s+)?übertragbar\w*)"
)
_ALWAYS_LIQUID_DE = r"(?P<er_ist_stets_liquide>(?<!nicht )\b(?:stets|immer|jederzeit)\s+liquid\w*)"
# The German Regulation and template say "Systeme für die Entschädigung der Anleger"; drafts also write
# "Anlegerentschädigungssysteme".
_SCHEME_DE = (
    r"(?:System(?:en?)?\s+(?:für\s+die|zur)\s+Entschädigung\s+der\s+Anleger|Anlegerentschädigungs\w*"
    r"|Entschädigungssystem\w*|Einlagensicherungs\w*)"
)
_SCHEMES_COVER_DE = (
    r"(?P<ein_Entschädigungssystem_oder_Einlagensicherungssystem_deckt_ihn>"
    r"\bfäll\w*\s+(?:vollständig\s+|auch\s+)?unter\s+(?:die\s+|das\s+|den\s+|ein\w*\s+)?" + _SCHEME_DE
    + r"|(?<!nicht )(?<!weder )(?<!noch )\bunter\s+(?:die\s+|das\s+|den\s+|ein\w*\s+)?" + _SCHEME_DE
    + r"(?:\s+[^\s.;!?]+){0,10}?\s+fäll\w*"
    r"|\b(?:ist|sind|wird|werden)\s+(?:vollständig\s+|auch\s+)?(?:durch|von)\s+"
    r"(?:den\s+|die\s+|das\s+|dem\s+|einem?\s+)?" + _SCHEME_DE + ")"
)

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
        prohibited_patterns=(_CANNOT_LOSE_EN, _ALWAYS_TRANSFERABLE_EN, _ALWAYS_LIQUID_EN, _SCHEMES_COVER_EN),
        prohibited_patterns_de=(
            _CANNOT_LOSE_DE,
            _ALWAYS_TRANSFERABLE_DE,
            _ALWAYS_LIQUID_DE,
            _SCHEMES_COVER_DE,
        ),
        min_words=20,
        severity=Severity.BLOCKER,
    ),
    Rule(
        rule_id="COMMON.MANAGEMENT_STATEMENT",
        citation="Art. 6 Abs. 6, Art. 19 Abs. 5, Art. 51 Abs. 5 MiCAR",
        section="management_statement",
        label="Statement by the management body on completeness, fairness, and clarity",
        required_terms=("management body", "complies", "fair", "clear", "not misleading"),
        # The German paragraphs use three verbs ("Rechnung trägt", "entspricht", "erfüllt"), and the
        # predefined statement of the templates in VO (EU) 2024/2984 says "erfüllt"; all name the Title
        # ("diesem Titel", "Titel II"), which the pattern tells apart from the white paper's own title.
        required_terms_de=("leitungsorgan", "redlich", "eindeutig", "nicht irreführend"),
        required_patterns_de=(TITLE_DE,),
        min_words=40,
        severity=Severity.BLOCKER,
    ),
    # The date of notification and the language are short answers: since 23 December 2025, Implementing
    # Regulation (EU) 2024/2984 has the white paper report the date as YYYY-MM-DD and each language from a
    # closed list of EU languages. A correct answer can be a single word, so linter.py checks for a calendar
    # date and for a language name instead of listed terms and a minimum length.
    Rule(
        rule_id="COMMON.NOTIFICATION_DATE",
        citation="Art. 6 Abs. 8, Art. 19 Abs. 7, Art. 51 Abs. 7 MiCAR",
        section="notification_date",
        label="Date of notification to the competent authority",
        min_words=0,
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
        min_words=0,
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
    # Point 5 of each party Part names the LEI or another identifier required pursuant to applicable
    # national law, and Art. 2 Abs. 1 Buchst. b and c VO (EU) 2024/2984 ask for the LEI where available.
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
        prohibited_patterns=(_SCHEMES_COVER_EN,),
        prohibited_patterns_de=(_SCHEMES_COVER_DE,),
    )
    if rule.rule_id == "COMMON.RISK_WARNING"
    else rule
    for rule in COMMON_RULES
)
