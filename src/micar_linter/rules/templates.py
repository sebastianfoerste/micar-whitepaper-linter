"""Field-level checks against the templates of Implementing Regulation (EU) 2024/2984 (ITS) and the
sustainability indicators of Delegated Regulation (EU) 2025/422 (RTS).

These rules check the numbered fields of a white paper drawn up in the template of Table 2, 3 or 4 of the
ITS Annex, not an Annex point of MiCAR, so their IDs name the act instead of an Annex Part: the ITS.* and
RTS.* namespaces sit beside the COMMON.* and ANNEX_*.* rules and cannot collide with them, with the point
rules of ADR 0005 (ANNEX_I.A.P6) or with the study's IDs (batch.py). Every regime runs them; the table
follows from the regime.

A draft without field numbers (JSON, PDF, DOCX, Markdown and heading-based XHTML) cannot show the fields, so
these rules report Missing where the section they are anchored to is absent and Review otherwise, with a note
that the field-level check needs the numbered-field layout; ITS.NOTIFICATION_DATE_FORMAT instead reads the
notification_date section for a date written YYYY-MM-DD. linter.py dispatches all five by rule ID; the field
data sit in template_types.py and predefined_texts.py, the checks in template_checks.py.
"""

from __future__ import annotations

from micar_linter.rules.base import Rule, Severity

TEMPLATE_RULES: tuple[Rule, ...] = (
    # Since 23 December 2025 the date of notification is reported as YYYY-MM-DD (form column of field 01 of
    # Table 2 and I.01 of Tables 3 and 4). COMMON.NOTIFICATION_DATE accepts any calendar date; this rule asks
    # for the template's form.
    Rule(
        rule_id="ITS.NOTIFICATION_DATE_FORMAT",
        citation="Anhang Tabelle 2 Feld 01, Tabelle 3 Feld I.01, Tabelle 4 Feld I.01 VO (EU) 2024/2984",
        section="notification_date",
        label="Date of notification written as YYYY-MM-DD, the template's format",
        min_words=0,
        severity=Severity.BLOCKER,
    ),
    # The fields whose form column reads "Predefined alphanumerical text" (predefined_texts.py).
    Rule(
        rule_id="ITS.PREDEFINED_TEXT",
        citation=(
            "Anhang Tabelle 2 Felder 02 bis 07, Tabelle 3 Felder I.02 bis I.04 und I.06, "
            "Tabelle 4 Felder I.02 bis I.05 und I.07 VO (EU) 2024/2984"
        ),
        section="management_statement",
        label=(
            "Predefined texts of the template (statements, warnings, right of redemption) in the template's "
            "English or German wording"
        ),
        min_words=0,
        severity=Severity.BLOCKER,
    ),
    # Table 1 of the ITS Annex defines the data types; the form column of Tables 2 to 4 assigns them.
    Rule(
        rule_id="ITS.FIELD_FORMATS",
        citation="Anhang Tabellen 1 bis 4 VO (EU) 2024/2984",
        section="offer_or_admission",
        label=(
            "Data formats of the template's typed fields (dates, LEI, DTI, currency and market codes, "
            "numbers, days, true or false)"
        ),
        min_words=0,
        severity=Severity.BLOCKER,
    ),
    Rule(
        rule_id="ITS.CODE_LISTS",
        citation="Anhang Tabellen 2 bis 4 VO (EU) 2024/2984",
        section="offer_or_admission",
        label=(
            "Codes of the template's closed lists (offer or admission, holders, placement, white paper and "
            "submission type, exemption, Member States)"
        ),
        min_words=0,
        severity=Severity.MAJOR,
    ),
    # Art. 4(1): the indicators of Table 2 (S.1 to S.9) in every white paper; Art. 4(2): those of Table 3
    # (S.10 to S.16) where S.8 exceeds 500 000 kWh.
    Rule(
        rule_id="RTS.SUSTAINABILITY_INDICATORS",
        citation="Art. 4 Abs. 1 und 2 i.V.m. Anhang Tabellen 2 und 3 VO (EU) 2025/422",
        section="environmental_impact",
        label=(
            "Sustainability indicators S.1 to S.9, and S.10 to S.16 above 500 000 kWh, in the format of "
            "Delegated Regulation (EU) 2025/422"
        ),
        min_words=0,
        severity=Severity.BLOCKER,
    ),
)
