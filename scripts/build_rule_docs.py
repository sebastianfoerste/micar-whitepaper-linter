#!/usr/bin/env python3
# ruff: noqa: E501  (HTML templates keep one element per line)
"""Generate one static page per rule in docs/rules/ from the Rule objects.

Every example on a page is a synthetic draft that is linted while the page is
built; the build stops if a result differs from the status the page states.
tests/test_rule_docs.py regenerates the pages and fails when the committed
copy is stale. Run: uv run python scripts/build_rule_docs.py
"""

from __future__ import annotations

import html
import json
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from micar_linter import __version__, citations
from micar_linter.contact import CONTACT_FIELDS
from micar_linter.lei import check_digits_for
from micar_linter.linter import CONTACT_POINT_RULE_IDS, EU_LANGUAGES, NOT_APPROVED_STATEMENT_RULE_IDS, Linter
from micar_linter.rules import RULESETS
from micar_linter.rules.base import Rule
from micar_linter.template_fields import FIELD_NAMES
from micar_linter.whitepaper import _RESERVED_METADATA_KEYS, Whitepaper, WhitepaperType

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "rules"
REPO = "https://github.com/sebastianfoerste/micar-whitepaper-linter"

REGIME_NAMES = {
    WhitepaperType.OTHER: "Annex I · other crypto-assets",
    WhitepaperType.ART: "Annex II · asset-referenced tokens",
    WhitepaperType.EMT: "Annex III · e-money tokens",
}
SOURCE_MODULES = {
    "COMMON": "common.py",
    "ANNEX_I": "annex_i.py",
    "ANNEX_II": "annex_ii.py",
    "ANNEX_III": "annex_iii.py",
}
# Citations have not been re-read against the Official Journal since these pages were introduced,
# except those of the rules in OJ_CHECKED.
VERIFICATION_NOTE = (
    "Not re-verified since these pages were introduced (2026-10-20): EUR-Lex was unreachable from the "
    "build environment. The citation is the rule's own, unchanged."
)


def _oj_checked(provisions: str, also: str = "") -> str:
    return (
        "Checked on 2026-10-27 against the Official Journal text in English and German (OJ L 150, 9.6.2023) "
        f"and the consolidated version of 9 January 2024{also}. No amendment and no English or German "
        f"corrigendum changes {provisions}."
    )


TEMPLATES = ", and against the templates of Implementing Regulation (EU) 2024/2984"
SUSTAINABILITY = (
    ", and against Delegated Regulation (EU) 2025/422 and the templates of Implementing Regulation (EU) 2024/2984"
)
OJ_CHECKED = {
    "COMMON.RISK_WARNING": _oj_checked("Art. 6(5), Art. 19(4) or Art. 51(4)"),
    "COMMON.MANAGEMENT_STATEMENT": _oj_checked("Art. 6(6), Art. 19(5), Art. 51(5) or the templates", TEMPLATES),
    "ANNEX_I.A": _oj_checked("Annex I Part A or the templates", TEMPLATES),
    "ANNEX_I.B": _oj_checked("Annex I Part B or the templates", TEMPLATES),
    "ANNEX_I.D": _oj_checked("Annex I Part D or the templates", TEMPLATES),
    "ANNEX_I.E": _oj_checked("Annex I Part E or the templates", TEMPLATES),
    "ANNEX_I.F": _oj_checked("Annex I Part F or the templates", TEMPLATES),
    "ANNEX_I.G": _oj_checked("Annex I Part G or the templates", TEMPLATES),
    "ANNEX_I.H": _oj_checked("Annex I Part H or the templates", TEMPLATES),
    "ANNEX_I.I": _oj_checked("Annex I Part I or the templates", TEMPLATES),
    "ANNEX_I.J": _oj_checked(
        "Art. 6(1), first subparagraph, point (j), Art. 4 of Delegated Regulation (EU) 2025/422 or the templates",
        SUSTAINABILITY,
    ),
    "ANNEX_II.A": _oj_checked("Annex II Part A or the templates", TEMPLATES),
    "ANNEX_II.B": _oj_checked("Annex II Part B or the templates", TEMPLATES),
    "ANNEX_II.C": _oj_checked("Annex II Part C or the templates", TEMPLATES),
    "ANNEX_II.E": _oj_checked("Annex II Part E or the templates", TEMPLATES),
    "ANNEX_II.F": _oj_checked("Annex II Part F or the templates", TEMPLATES),
    "ANNEX_II.G.COMPOSITION_DISCLOSURE": _oj_checked("Annex II Part G or the templates", TEMPLATES),
    "ANNEX_II.H": _oj_checked(
        "Art. 19(1), first subparagraph, point (h), Art. 4 of Delegated Regulation (EU) 2025/422 or the "
        "templates",
        SUSTAINABILITY,
    ),
    "ANNEX_III.A": _oj_checked("Art. 48, Annex III Part A or the templates", TEMPLATES),
    "ANNEX_III.B": _oj_checked("Annex III Part B or the templates", TEMPLATES),
    "ANNEX_III.C": _oj_checked("Annex III Part C"),
    "ANNEX_III.D": _oj_checked("Annex III Part D or Art. 49(4)"),
    "ANNEX_III.E": _oj_checked("Annex III Part E or the templates", TEMPLATES),
    "ANNEX_III.F": _oj_checked("Annex III Part F or the templates", TEMPLATES),
    "ANNEX_III.G": _oj_checked(
        "Art. 51(1), point (g), Art. 4 of Delegated Regulation (EU) 2025/422 or the templates", SUSTAINABILITY
    ),
    "COMMON.NOTIFICATION_DATE": (
        "Checked on 2026-10-27 against the Official Journal text in English and German (OJ L 150, 9.6.2023) "
        "and the consolidated version of 9 January 2024. No amendment and no English or German corrigendum "
        "changes Art. 6(8), Art. 19(7) or Art. 51(7). The date format was read in the English and German text "
        "of Implementing Regulation (EU) 2024/2984, which has no amendment or corrigendum."
    ),
    "COMMON.LANGUAGE": (
        "Checked on 2026-10-27 against the Official Journal text in English and German (OJ L 150, 9.6.2023) "
        "and the consolidated version of 9 January 2024. No amendment and no English or German corrigendum "
        "changes Art. 6(9), Art. 19(8) or Art. 51(8). The list of languages is Art. 1 of Council Regulation "
        "No 1 in its consolidated version of 1 July 2013."
    ),
    "ANNEX_II.D": (
        "Checked on 2026-10-27 against the Official Journal text in English and German (OJ L 150, 9.6.2023) "
        "and the consolidated version of 9 January 2024. No amendment and no English or German corrigendum "
        "changes Annex II Part D or Art. 39."
    ),
    "ANNEX_II.I": (
        "Checked on 2026-10-27 against the Official Journal text in English and German (OJ L 150, 9.6.2023) "
        "and the consolidated version of 9 January 2024. No amendment and no English or German corrigendum "
        "changes Annex II Parts D and G, Art. 39, Art. 46 or Art. 49(4), which the note on par value cites."
    ),
    "ANNEX_II.G.VALUATION_AUDIT": (
        "Checked on 2026-10-27 against the Official Journal text in English and German (OJ L 150, 9.6.2023) "
        "and the consolidated version of 9 January 2024, and against the templates of Implementing Regulation "
        "(EU) 2024/2984. No amendment and no English or German corrigendum changes Annex II Part D or the "
        "templates."
    ),
    "ANNEX_III.SAFEGUARDING": (
        "Checked on 2026-10-27 against the Official Journal text in English and German (OJ L 150, 9.6.2023) "
        "and the consolidated version of 9 January 2024, and against Article 7 of Directive 2009/110/EC in its "
        "consolidated version of 13 January 2018. No amendment and no English or German corrigendum changes "
        "Art. 54 or Annex III Part D."
    ),
    "COMMON.SUMMARY": (
        "Checked on 2026-10-30 against the Official Journal text in English and German (OJ L 150, 9.6.2023), the "
        "consolidated version of 9 January 2024, which differs there only in a footnote number, and the predefined "
        "warnings of field 07 of Table 2, I.04 of Table 3 and I.05 of Table 4 of Implementing Regulation (EU) "
        "2024/2984, as the Publications Office served them that day. No amendment and no English or German "
        "corrigendum changes Art. 6(7), Art. 19(6), Art. 51(6) or those fields. The redemption statements of the "
        "third subparagraph of Art. 19(6) and Art. 51(6) and of fields I.06 of Table 3 and I.07 of Table 4 were "
        "read on 2026-10-31 in the same English and German Official Journal texts, as the Publications Office "
        "served them that day."
    ),
    "ANNEX_I.A.P6": (
        "Checked on 2026-10-30 against the Official Journal text in English and German (OJ L 150, 9.6.2023), the "
        "consolidated version of 9 January 2024 and Table 2 of Implementing Regulation (EU) 2024/2984, whose "
        "fields A.8 to A.10 carry the point without a condition, as the Publications Office served them that day. "
        "No amendment and no English or German corrigendum changes Annex I Part A point 6 or the template."
    ),
    "ANNEX_III.A.P6": (
        "Checked on 2026-10-30 against the Official Journal text in English and German (OJ L 150, 9.6.2023), the "
        "consolidated version of 9 January 2024 and Table 4 of Implementing Regulation (EU) 2024/2984, whose "
        "fields A.9 to A.11 carry the point without a condition, as the Publications Office served them that day. "
        "No amendment and no English or German corrigendum changes Annex III Part A point 6 or the template."
    ),
}
# Rules that pass when the section holds a value of the right kind, a date, a language or contact details, at
# any length (linter.py).
ANSWER_CHECKS = {
    "COMMON.NOTIFICATION_DATE": "a calendar date",
    "COMMON.LANGUAGE": "an official EU language",
    **dict.fromkeys(CONTACT_POINT_RULE_IDS, "a telephone number, an e-mail address and a period in days"),
}
# The template fields of each point rule, by the table its regime uses (contact.py).
POINT_TABLES = {WhitepaperType.OTHER: 2, WhitepaperType.EMT: 4}
FILLER = "This synthetic sentence only adds length and states no fact about any issuer or token."
# A sentence that turns the scheme statement of the risk warning around, for the rule's examples.
TURNED_AROUND = "Investor compensation schemes and deposit guarantee schemes cover the crypto-asset."
# The predefined warning of field 07 of Table 2 of Implementing Regulation (EU) 2024/2984, which does not count
# toward the minimum of COMMON.SUMMARY (linter.py).
SUMMARY_WARNING = (
    "Warning This summary should be read as an introduction to the crypto-asset white paper. The prospective "
    "holder should base any decision to purchase this crypto-asset on the content of the crypto-asset white paper "
    "as a whole and not on the summary alone. The offer to the public of this crypto-asset does not constitute an "
    "offer or solicitation to purchase financial instruments and any such offer or solicitation can be made only "
    "by means of a prospectus or other offer documents pursuant to the applicable national law. This crypto-asset "
    "white paper does not constitute a prospectus as referred to in Regulation (EU) 2017/1129 of the European "
    "Parliament and of the Council or any other offer document pursuant to Union or national law."
)
# The warnings of field I.04 of Table 3 and I.05 of Table 4 differ from field 07 in the token named and, for an
# e-money token, in "and that any such offer".
SUMMARY_WARNING_ART = SUMMARY_WARNING.replace("purchase this crypto-asset on", "purchase this asset-referenced token on")
SUMMARY_WARNING_EMT = SUMMARY_WARNING.replace("purchase this crypto-asset on", "purchase this e-money token on").replace(
    "instruments and any such", "instruments and that any such"
)
# Field 07 of Table 2 in German.
SUMMARY_WARNING_DE = (
    "Warnhinweis: Diese Zusammenfassung ist als Einführung in das Kryptowerte-Whitepaper zu lesen. Der potenzielle "
    "Inhaber sollte jede Entscheidung über den Kauf des Kryptowerts auf der Grundlage des Inhalts des gesamten "
    "Kryptowerte-Whitepapers und nicht allein auf der Grundlage der Zusammenfassung treffen. Das öffentliche Angebot "
    "dieses Kryptowerts stellt kein Angebot und keine Aufforderung zum Kauf von Finanzinstrumenten dar und ein "
    "solches Angebot oder eine solche Aufforderung kann nur mittels eines Prospekts oder anderer im geltenden "
    "nationalen Recht vorgesehener Angebotsunterlagen erfolgen. Dieses Kryptowerte-Whitepaper stellt keinen Prospekt "
    "im Sinne der Verordnung (EU) 2017/1129 des Europäischen Parlaments und des Rates und kein anderes "
    "Angebotsdokument im Sinne von Unionsrecht oder nationalem Recht dar."
)
# The warning's four points in other words, which the check does not recognise.
SUMMARY_WARNING_PARAPHRASED = (
    "Read this summary only as an introduction to the white paper and base any purchase on the white paper as a "
    "whole. Nothing here offers financial instruments, and the white paper is no prospectus under Union or national "
    "law."
)
# The redemption statements of field I.06 of Table 3 and I.07 of Table 4 (Art. 19(6) and Art. 51(6), third
# subparagraph), each with a sentence on the conditions.
ART_REDEMPTION = (
    "The holders of asset-referenced tokens have a right of redemption at any time. The conditions for redemption "
    "are described in the redemption section of this white paper."
)
EMT_REDEMPTION = (
    "The holders of this e-money token have a right of redemption at any time and at par value. The conditions for "
    "redemption are described in the redemption section of this white paper."
)
FILLER_DE = "Dieser synthetische Satz dient nur der Länge und trifft keine Aussage über einen Emittenten oder Token."
FORMAT_GATE = {"COMMON.IXBRL_TAGGING"}
LEI_RULES = {"COMMON.LEI_CHECK_DIGITS", "COMMON.LEI_CONSISTENCY"}
# Synthetic LEIs: an obviously fictitious 18-character base completed with computed check digits.
SYNTHETIC_LEI = "9999SYNTH0000ZZQ01" + check_digits_for("9999SYNTH0000ZZQ01")
OTHER_SYNTHETIC_LEI = "9999SYNTH0000ZZQ02" + check_digits_for("9999SYNTH0000ZZQ02")
BROKEN_LEI = SYNTHETIC_LEI[:-2] + f"{(int(SYNTHETIC_LEI[-2:]) + 1) % 100:02d}"
LEI_VERIFICATION_NOTE = (
    "Checked on 2026-10-27 against the Official Journal text in English and German: point 5 of Annex I "
    "Parts A, B and C and of Annex II and III Part A names the legal entity identifier or another identifier "
    "required pursuant to applicable national law, and Art. 2(1)(b) and (c) of Implementing Regulation (EU) "
    "2024/2984 ask for the LEI where available."
)
# The first-page statement rules were added after the other pages, with their wording checked.
STATEMENT_VERIFICATION_NOTE = (
    "The citation and the English wording the rule checks were read in the EUR-Lex text of Art. 6(3) and "
    "Art. 51(3) MiCAR as mirrored in legalize-dev/legalize-eu (CELEX 32023R1114), not on EUR-Lex itself, "
    "which was unreachable from the build environment. The German wording has not been checked."
)


def verification_note(rule_id: str) -> str:
    """Which reading of the Regulation the rule's citation rests on."""
    if rule_id in OJ_CHECKED:
        return OJ_CHECKED[rule_id]
    if rule_id in NOT_APPROVED_STATEMENT_RULE_IDS:
        return STATEMENT_VERIFICATION_NOTE
    return VERIFICATION_NOTE


STATEMENT_APPROVAL = (
    "This crypto-asset white paper has not been approved by any competent authority in any Member State of "
    "the European Union."
)
NEVER_PASS = {"COMMON.IXBRL_TAGGING", "ANNEX_II.G.DEPOSIT_FLOOR_REVIEW"}
UNTESTED_REGIMES = {
    "ANNEX_II": "The Annex II rules have not yet been run against a real ART white paper.",
    "ANNEX_III": "The Annex III rules have not yet been run against a real EMT white paper.",
}
# Why a rule runs with other terms or another minimum for some regimes. The build stops when a rule
# ID has more than one Rule in RULESETS and no note here.
VARIANT_NOTES = {
    "COMMON.RISK_WARNING": (
        "Art. 6(5) and Art. 19(4) MiCAR require a statement that the crypto-asset may lose its value in part "
        "or in full, may not always be transferable and may not be liquid, and that investor compensation "
        "and deposit guarantee schemes do not cover it; the listed terms come from that wording. Art. 51(4) "
        "asks an e-money token white paper only for the two scheme warnings, so EMT drafts are checked for "
        "those, and only wording that turns them around sends an EMT warning to review. The utility-token "
        "statement of Art. 6(5)(d) applies to utility tokens only and is not checked."
    ),
}


@dataclass(frozen=True)
class Example:
    title: str
    expected: str
    draft: dict
    note: str


def regimes_by_rule() -> dict[str, list[WhitepaperType]]:
    found: dict[str, list[WhitepaperType]] = {}
    for regime, rules in RULESETS.items():
        for rule in rules:
            found.setdefault(rule.rule_id, []).append(regime)
    return found


def all_rules() -> list[Rule]:
    seen: dict[str, Rule] = {}
    for rules in RULESETS.values():
        for rule in rules:
            seen.setdefault(rule.rule_id, rule)
    return list(seen.values())


def variants(rule_id: str) -> list[tuple[Rule, list[WhitepaperType]]]:
    """The distinct Rule objects that carry one ID, each with the regimes that run it."""
    found: dict[Rule, list[WhitepaperType]] = {}
    for regime, rules in RULESETS.items():
        for rule in rules:
            if rule.rule_id == rule_id:
                found.setdefault(rule, []).append(regime)
    return list(found.items())


def _annexes(regimes: list[WhitepaperType]) -> str:
    return ", ".join(REGIME_NAMES[regime].split(" · ")[0] for regime in regimes)


def _named(patterns: tuple[str, ...]) -> list[tuple[str, str]]:
    """The listed terms written as patterns (rules/terms.py): each named group's name and its pattern."""
    return [
        (name.replace("_", " "), pattern) for pattern in patterns for name in re.compile(pattern).groupindex
    ]


def _listed(rule: Rule) -> list[str]:
    """The English terms a passing example names; each pattern matches its own name (tests/test_rules.py)."""
    return [*rule.required_terms, *(name for name, _ in _named(rule.required_patterns))]


def _passing_text(rule: Rule) -> str:
    listed = _listed(rule)
    sentence = "Synthetic example naming " + ", ".join(listed) + "." if listed else ""
    words = sentence.split()
    while len(words) < rule.min_words:
        words += FILLER.split()
    return " ".join(words)


def _draft(rule: Rule, regime: WhitepaperType, text: str, **metadata: object) -> dict:
    draft: dict = {"title": "Synthetic rule example", "type": regime.value}
    draft.update(metadata)
    draft["sections"] = {rule.section: text}
    return draft


def _responsibility(person: str) -> str:
    return f"The {person} of the crypto-asset is solely responsible for the content of this crypto-asset white paper."


def examples(rule: Rule, regime: WhitepaperType) -> list[Example]:
    if rule.rule_id == "COMMON.IXBRL_TAGGING":
        return [
            Example(
                "Any JSON draft",
                "missing",
                {"title": "Synthetic rule example", "type": regime.value, "sections": {}},
                "A JSON, DOCX, PDF or Markdown draft cannot carry Inline XBRL, so the blocker stays open. "
                "An XHTML file is checked for the Inline XBRL 1.1 and ESMA MiCA taxonomy namespaces and "
                "then shows Review, because tag completeness needs a taxonomy validator. A saved iXBRL viewer "
                "page stays Missing: its text is unpacked for the content checks, and its format is not checked.",
            )
        ]
    if rule.rule_id in LEI_RULES:
        base = {"title": "Synthetic rule example", "type": regime.value}
        issuer = f"Synthetic Issuer AG, a fictional company. LEI: {SYNTHETIC_LEI}."
        if rule.rule_id == "COMMON.LEI_CHECK_DIGITS":
            return [
                Example(
                    "No LEI and no party section",
                    "missing",
                    {**base, "sections": {"summary": "Synthetic summary of a fictional token."}},
                    "Without an LEI there are no check digits to verify, and no party section says who the "
                    "parties are, so the rule fails closed.",
                ),
                Example(
                    "Party section without an LEI",
                    "review",
                    {**base, "sections": {"issuer": "Synthetic Issuer AG."}},
                    "Point 5 of each party Part allows another identifier required pursuant to applicable "
                    "national law in place of the LEI, so a reviewer checks which one the draft gives.",
                ),
                Example(
                    "Check digits do not match",
                    "review",
                    {**base, "sections": {"issuer": f"Synthetic Issuer AG. LEI: {BROKEN_LEI}."}},
                    "The last two digits do not satisfy ISO/IEC 7064 MOD 97-10, which usually means a typo.",
                ),
                Example(
                    "Check digits match",
                    "pass",
                    {**base, "sections": {"issuer": issuer}},
                    "The code is well formed. The check does not ask a registry whether the LEI exists or "
                    "belongs to the named entity.",
                ),
            ]
        return [
            Example(
                "No party section",
                "missing",
                {**base, "sections": {"summary": f"LEI {SYNTHETIC_LEI}."}},
                "The draft has no issuer, offeror or trading platform operator section to compare the LEI with.",
            ),
            Example(
                "No LEI in a party section",
                "review",
                {**base, "sections": {"issuer": "Synthetic Issuer AG.", "summary": f"LEI {SYNTHETIC_LEI}."}},
                "The issuer section carries no valid LEI. It may give another identifier required pursuant to "
                "applicable national law, which a reviewer checks.",
            ),
            Example(
                "LEI outside the party sections",
                "review",
                {
                    **base,
                    "sections": {"issuer": issuer, "summary": f"The issuer's LEI is {OTHER_SYNTHETIC_LEI}."},
                },
                "The summary names a valid LEI that no party section states.",
            ),
            Example(
                "Same LEI throughout",
                "pass",
                {**base, "sections": {"issuer": issuer, "summary": f"The issuer's LEI is {SYNTHETIC_LEI}."}},
                "Every valid LEI in the draft matches a party section, and the issuer states one.",
            ),
            Example(
                "LEI of the provider in charge of the placing",
                "pass",
                {
                    **base,
                    "sections": {
                        "issuer": issuer,
                        "offer_or_admission": f"CASP identifier: {OTHER_SYNTHETIC_LEI}",
                    },
                },
                "Field E.31 of Table 2 asks for the LEI of the crypto-asset service provider in charge of the "
                "placing. Its label names the role, so the code is not compared with the party sections.",
            ),
        ]
    if rule.rule_id in NOT_APPROVED_STATEMENT_RULE_IDS:
        emt = regime is WhitepaperType.EMT
        named, other = ("issuer", "offeror") if emt else ("offeror", "issuer")
        return [
            Example(
                "Statement absent",
                "missing",
                {"title": "Synthetic rule example", "type": regime.value, "sections": {}},
                "The section key is missing or empty.",
            ),
            Example(
                "Statement names someone else",
                "review",
                _draft(rule, regime, f"{STATEMENT_APPROVAL} {_responsibility(other)}"),
                "Art. 51(3) MiCAR names the issuer, so the responsibility sentence is not found."
                if emt
                else "Art. 6(3) MiCAR names the offeror, the person seeking admission to trading or the operator "
                "of the trading platform; this statement names the issuer.",
            ),
            Example(
                "German draft",
                "review",
                _draft(
                    rule,
                    regime,
                    "Synthetischer deutscher Beispieltext. Er gibt nicht den Wortlaut des Amtsblatts wieder.",
                    language="de",
                ),
                "The German wording has not been checked against the German Official Journal, so a German "
                "statement goes to review whatever it says.",
            ),
            Example(
                "Statement in the checked wording",
                "pass",
                _draft(rule, regime, f"{STATEMENT_APPROVAL} {_responsibility(named)}"),
                "Both sentences in the English wording the rule checks. A pass says the words matched; the check "
                "cannot see whether the statement is on the first page.",
            ),
        ]
    if rule.rule_id in ANSWER_CHECKS:
        absent = [
            Example(
                "Section absent",
                "missing",
                {"title": "Synthetic rule example", "type": regime.value, "sections": {}},
                "The section key is missing or empty.",
            ),
            Example(
                "Placeholder",
                "missing",
                _draft(rule, regime, "TBD"),
                "A placeholder alone is no answer, so the section counts as missing.",
            ),
        ]
        if rule.rule_id in CONTACT_POINT_RULE_IDS:
            return [*absent, *_contact_examples(rule, regime)]
        if rule.rule_id == "COMMON.NOTIFICATION_DATE":
            return [
                *absent,
                Example(
                    "Month without a day",
                    "review",
                    _draft(rule, regime, "Notified in March 2026."),
                    "A month and a year name no calendar date.",
                ),
                Example(
                    "Date in the template format",
                    "pass",
                    _draft(rule, regime, "Date of notification: 2026-03-02"),
                    "Since 23 December 2025 the template of Implementing Regulation (EU) 2024/2984 has the "
                    "date reported as YYYY-MM-DD (field 01 of Table 2, I.01 of Tables 3 and 4). Four words "
                    "suffice. The check does not confirm that the date is the date of notification.",
                ),
            ]
        return [
            *absent,
            Example(
                "No language named",
                "review",
                _draft(
                    rule,
                    regime,
                    "This white paper is drawn up in a language customary in the sphere of international finance.",
                ),
                "The sentence repeats the wording of the requirement and names no language.",
            ),
            Example(
                "Answer to the template field",
                "pass",
                _draft(rule, regime, "Language or languages of the crypto-asset white paper: English"),
                "Since 23 December 2025 the template of Implementing Regulation (EU) 2024/2984 asks for the "
                "language or languages of the white paper, from a closed list of EU languages. The check does "
                "not decide whether the language meets the home or host Member State requirement.",
            ),
        ]
    if rule.rule_id == "ANNEX_II.G.DEPOSIT_FLOOR_REVIEW":
        flags = {
            "references_official_currency": True,
            "art_significant": False,
            "article_45_7b_required_by_authority": False,
        }
        return [
            Example(
                "Characterisation not stated",
                "review",
                _draft(rule, regime, "The reserve is held in deposits."),
                "The draft does not state the three characterisation flags, so no candidate floor applies yet.",
            ),
            Example(
                "Flags stated, no percentage",
                "missing",
                _draft(rule, regime, "The reserve is held in deposits.", **flags),
                "The flags point to a candidate floor, but the section states no deposit share.",
            ),
            Example(
                "Flags stated, percentage present",
                "review",
                _draft(rule, regime, "The issuer keeps 40% of the reserve in deposits.", **flags),
                "A percentage is detected and listed for a lawyer. The check never decides whether it meets "
                "a floor.",
            ),
        ]
    if rule.rule_id == "COMMON.SUMMARY":
        return _summary_examples(rule)
    result = [
        Example(
            "Section absent",
            "missing",
            {"title": "Synthetic rule example", "type": regime.value, "sections": {}},
            "The section key is missing or empty.",
        ),
    ]
    thin = " ".join(_listed(rule)) or "Short."
    if len(thin.split()) < rule.min_words:
        result.append(
            Example(
                "Thin section",
                "review",
                _draft(rule, regime, thin),
                f"Every listed term appears, but the section is shorter than {rule.min_words} words.",
            )
        )
    if rule.rule_id == "ANNEX_II.I":
        result.append(
            Example(
                "Redemption at par",
                "review",
                _draft(rule, regime, _passing_text(rule) + " Holders redeem at par."),
                "Every listed term appears and the section is long enough. It mentions par value, and "
                "redemption at par value is the e-money token rule of Art. 49(4) MiCAR; an ART issuer redeems "
                "by paying funds, other than electronic money, equivalent to the market value of the "
                "referenced assets, or by delivering those assets (Art. 39(2) MiCAR).",
            )
        )
        reserve = " Reserve bills are bought at a discount and redeemed at par."
        result.append(
            Example(
                "Reserve asset at par",
                "review",
                _draft(rule, regime, _passing_text(rule) + reserve),
                "The note also follows where par value describes the reserve of assets. The check reads the "
                "words and leaves it to the reviewer whether the token's redemption depends on par value.",
            )
        )
    result.append(
        Example(
            "Section that matches",
            "pass",
            _draft(rule, regime, _passing_text(rule)),
            "This text passes and shows what the check measures: listed terms and length. It is not "
            "model disclosure wording and does not meet MiCAR.",
        )
    )
    if _named(rule.prohibited_patterns):
        result.append(
            Example(
                "Statement turned around",
                "review",
                _draft(rule, regime, f"{_passing_text(rule)} {TURNED_AROUND}"),
                "Every listed term appears, but the text says that the schemes cover the crypto-asset, the "
                "opposite of the required statement, so a reviewer checks it.",
            )
        )
    return result


def _summary_examples(rule: Rule) -> list[Example]:
    """COMMON.SUMMARY: the listed terms and length, the warning's four points and the redemption statement."""
    other, art, emt = WhitepaperType.OTHER, WhitepaperType.ART, WhitepaperType.EMT
    thin = " ".join(_listed(rule))
    body = _passing_text(rule)
    german = "Diese Zusammenfassung nennt wesentliche Informationen zu dem Angebot. " + " ".join([FILLER_DE] * 5)
    return [
        Example(
            "Section absent",
            "missing",
            {"title": "Synthetic rule example", "type": other.value, "sections": {}},
            "The section key is missing or empty.",
        ),
        Example(
            "Thin section",
            "review",
            _draft(rule, other, thin),
            "Every listed term appears, but the section is shorter than 80 words and holds no warning.",
        ),
        Example(
            "Predefined warning and a short summary",
            "review",
            _draft(rule, other, f"{SUMMARY_WARNING} {thin}"),
            "The section has more than 80 words, but the predefined warning of the template does not count "
            "toward them, so the summary itself is thin.",
        ),
        Example(
            "Summary without the warning",
            "review",
            _draft(rule, other, body),
            "Every listed term appears and the section is long enough, but the warning of Art. 6(7), second "
            "subparagraph, is not found. The finding names the four points.",
        ),
        Example(
            "Warning in other words",
            "review",
            _draft(rule, other, f"{SUMMARY_WARNING_PARAPHRASED} {body}"),
            "The paraphrase states the four points in its own words. Only the template's wording is recognised, "
            "so the finding names all four points for the reviewer; the paraphrase counts toward the 80 words.",
        ),
        Example(
            "Warning and summary (other crypto-asset)",
            "pass",
            _draft(rule, other, f"{SUMMARY_WARNING} {body}"),
            "The template's warning (field 07 of Table 2) and 80 own words naming the listed terms. A pass means "
            "the check matched, nothing more; the text is not model disclosure wording.",
        ),
        Example(
            "ART summary without the redemption statement",
            "review",
            _draft(rule, art, f"{SUMMARY_WARNING_ART} {body}"),
            "Art. 19(6), third subparagraph, has the summary state that the holders have a right of redemption at "
            "any time, and the conditions for redemption. No sentence names redemption together with “at any "
            "time”.",
        ),
        Example(
            "ART summary with the redemption statement",
            "pass",
            _draft(rule, art, f"{SUMMARY_WARNING_ART} {body} {ART_REDEMPTION}"),
            "The warning of field I.04 of Table 3 and the redemption statement of field I.06. The conditions for "
            "redemption are not checked.",
        ),
        Example(
            "EMT summary without par value",
            "review",
            _draft(
                rule,
                emt,
                f"{SUMMARY_WARNING_EMT} {body} The holders of this e-money token have a right of redemption at any "
                "time.",
            ),
            "Art. 51(6), third subparagraph, has the summary state that the holders have a right of redemption at "
            "any time and at par value; par value is not named.",
        ),
        Example(
            "EMT summary with the redemption statement",
            "pass",
            _draft(rule, emt, f"{SUMMARY_WARNING_EMT} {body} {EMT_REDEMPTION}"),
            "The warning of field I.05 of Table 4 and the redemption statement of field I.07.",
        ),
        Example(
            "German draft with the template warning",
            "pass",
            _draft(rule, other, f"{SUMMARY_WARNING_DE} {german}", language="de"),
            "The German warning of field 07 of Table 2, the German listed terms and 80 own words. The warning is "
            "left out of the count in German too.",
        ),
    ]


def _contact_examples(rule: Rule, regime: WhitepaperType) -> list[Example]:
    """Point 6 in a draft without field numbers: the section is searched for the three items."""
    person = "issuer" if regime is WhitepaperType.EMT else "offeror"
    german = "emittent" if regime is WhitepaperType.EMT else "anbieter"
    phone, email = "+49 30 0000 0000", f"contact@{person}.example"
    names = FIELD_NAMES[regime]
    phone_field, email_field, days_field = (names[number] for number in CONTACT_FIELDS[regime])
    company = f"Synthetic {person.capitalize()} GmbH, a fictional company."
    return [
        Example(
            "No contact details",
            "review",
            _draft(rule, regime, f"{company} The members of its management body are two fictional managing directors."),
            f"The section names the {person} and its management body and gives no telephone number, e-mail address "
            "or response time.",
        ),
        Example(
            "No response time",
            "review",
            _draft(rule, regime, f"{company} Telephone: {phone}. E-mail: {email}."),
            "The period of days within which an investor will receive an answer is missing.",
        ),
        Example(
            "Answers under the template's field names",
            "pass",
            _draft(rule, regime, f"{phone_field}: {phone}. {email_field}: {email}. {days_field}: 5"),
            f"Each item has the shape the check looks for. A pass does not show that the number or the address works "
            f"or belongs to the {person}.",
        ),
        Example(
            "German draft",
            "pass",
            _draft(
                rule,
                regime,
                f"Telefonnummer zur Kontaktaufnahme: {phone}. E-Mail-Adresse: kontakt@{german}.example. Anleger "
                "erhalten innerhalb von fünf Werktagen eine Antwort.",
                language="de",
            ),
            "The period counts in German words too, here five working days written out.",
        ),
    ]


def lint_example(rule: Rule, example: Example) -> str:
    draft = example.draft
    # The same filter as the JSON loader: a draft cannot set the reserved keys.
    metadata = {
        k: v
        for k, v in draft.items()
        if k not in ("title", "type", "sections") and k not in _RESERVED_METADATA_KEYS
    }
    metadata["ixbrl_validated"] = False
    whitepaper = Whitepaper(
        title=draft["title"],
        type=WhitepaperType(draft["type"]),
        sections=dict(draft["sections"]),
        metadata=metadata,
    )
    return Linter((rule,)).lint(whitepaper)[0].status


def _e(text: object) -> str:
    return html.escape(str(text), quote=True)


def _page(title: str, description: str, body: str, *, root: str = "../") -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{_e(description)}">
<title>{_e(title)}</title>
<link rel="stylesheet" href="{root}assets/site.css">
</head>
<body>
<a class="skip-link" href="#main">Skip to content</a>
<header class="site-header">
  <a class="brand" href="{root}"><span class="brand-mark" aria-hidden="true">M</span><span>MiCAR <strong>Whitepaper Linter</strong></span></a>
  <nav aria-label="Site"><a href="{root}">Overview</a><a href="{root}rules/">Rules</a><a href="{root}playground/">Playground</a><a href="{REPO}">Source</a></nav>
</header>
<main id="main">
{body}
</main>
<footer><span>MiCAR Whitepaper Linter {_e(__version__)} · MIT licence · First-pass screening, not legal advice.</span><span>Generated from the rule set by <code>scripts/build_rule_docs.py</code>.</span></footer>
</body>
</html>
"""


def _status_badge(status: str) -> str:
    return f'<span class="badge {status}">{_e(status.capitalize())}</span>'


def _terms(terms: tuple[str, ...], patterns: tuple[str, ...] = ()) -> str:
    shown = [f"<code>{_e(t)}</code>" for t in terms]
    shown += [f"<code>{_e(name)}</code> (pattern <code>{_e(pattern)}</code>)" for name, pattern in _named(patterns)]
    return ", ".join(shown) if shown else "none"


def status_logic(rule: Rule) -> str:
    if rule.rule_id == "COMMON.IXBRL_TAGGING":
        return (
            '<ul class="plain"><li><strong>Missing</strong>: the draft is JSON, DOCX, PDF or Markdown, or a saved '
            "iXBRL viewer page. A viewer page packs the white paper into a script; the content checks read the "
            "unpacked text, and the viewer's rendering is not the XHTML document itself.</li>"
            "<li><strong>Review</strong>: the draft is any other XHTML file. The check reports namespace problems "
            "and always adds that tag completeness was not checked.</li><li><strong>Pass</strong>: never. This is "
            "a fail-closed format gate.</li></ul>"
        )
    if rule.rule_id == "COMMON.LEI_CHECK_DIGITS":
        return (
            '<ul class="plain"><li><strong>Missing</strong>: no LEI-shaped code (18 letters or digits and two '
            "check digits) appears in any section, and no section <code>issuer</code>, <code>offeror</code> or "
            "<code>trading_platform_operator</code> has text other than a placeholder. A 20-digit number counts "
            "only next to an LEI label.</li>"
            "<li><strong>Review</strong>: an LEI-shaped code fails the ISO/IEC 7064 MOD 97-10 check digits; or no "
            "LEI-shaped code appears while a party section has text, since point 5 allows another identifier "
            "required pursuant to applicable national law in place of the LEI.</li>"
            "<li><strong>Pass</strong>: every LEI-shaped code has valid check digits. No registry is asked.</li></ul>"
        )
    if rule.rule_id == "COMMON.LEI_CONSISTENCY":
        return (
            '<ul class="plain"><li><strong>Missing</strong>: no section <code>issuer</code>, <code>offeror</code> or '
            "<code>trading_platform_operator</code> has text other than a placeholder.</li>"
            "<li><strong>Review</strong>: a party section has text but no party section carries an LEI with valid "
            "check digits, since point 5 allows another identifier required pursuant to applicable national law "
            "in place of the LEI; a valid LEI in another "
            "section appears in no party section; or the <code>issuer</code> section names more than one valid "
            "LEI. An LEI that the draft gives for a person other than the parties counts for neither: the "
            "crypto-asset service provider in charge of the placing (field E.31 of Table 2, C.22 of Table 3), a "
            "custodian of the reserve assets (G.8 of Table 3), or a person other than the issuer who offers the "
            "token, seeks its admission to trading or draws up the white paper (AA.1 and AA.3 of Table 3, A.27 of "
            "Table 4). The field label, or the sentence that holds the code, names that role before it.</li>"
            "<li><strong>Pass</strong>: none of the above. Codes with invalid check digits are reported by "
            '<a href="COMMON.LEI_CHECK_DIGITS.html">COMMON.LEI_CHECK_DIGITS</a>, not here.</li></ul>'
        )
    if rule.rule_id in CONTACT_POINT_RULE_IDS:
        return _contact_status_logic(rule)
    if rule.rule_id in ANSWER_CHECKS:
        missing = (
            f'<ul class="plain"><li><strong>Missing</strong>: section <code>{_e(rule.section)}</code> is absent '
            "or empty, or holds only placeholder text such as TBD or TBC.</li>"
        )
        if rule.rule_id == "COMMON.NOTIFICATION_DATE":
            return (
                missing + "<li><strong>Review</strong>: the section names no calendar date, that is no day, month "
                "and four-digit year that exist together. A month with its year, a two-digit year and an "
                "impossible date such as 31.02.2026 count as no date.</li>"
                "<li><strong>Pass</strong>: the section names such a date, however short the section. It may read "
                "<code>2026-03-02</code>, <code>02.03.2026</code> or <code>2/3/2026</code>, or write the month in "
                "English or German, as in <code>2 March 2026</code>, <code>March 2, 2026</code> or "
                "<code>2. März 2026</code>. A pass means a date was found, nothing more.</li></ul>"
            )
        names = ", ".join(f"{english} ({german})" for english, german in EU_LANGUAGES)
        return (
            missing + "<li><strong>Review</strong>: the section names none of the 24 official languages of the "
            "EU.</li><li><strong>Pass</strong>: the section names at least one of them by its English or German "
            f"name, however short the section: {_e(names)}. Slovene counts as well. English names count as "
            "written or in capitals. German names count in any case, also inflected or with "
            "<code>-sprachig</code>: <code>in deutscher Sprache</code>, <code>englischsprachig</code>. A pass "
            "means a language name was found, nothing more.</li></ul>"
        )
    if rule.rule_id == "ANNEX_II.G.DEPOSIT_FLOOR_REVIEW":
        return (
            '<ul class="plain"><li><strong>Review</strong>: a characterisation flag '
            "(<code>references_official_currency</code>, <code>art_significant</code>, "
            "<code>article_45_7b_required_by_authority</code>) is missing or not a boolean; the draft states the "
            "token references no official currency; or a percentage is found in the section.</li>"
            "<li><strong>Missing</strong>: the flags determine a candidate floor and the section states no "
            "percentage.</li><li><strong>Pass</strong>: never. Draft flags are assertions pending lawyer "
            "confirmation, not trusted facts.</li></ul>"
        )
    missing = (
        f"<li><strong>Missing</strong>: section <code>{_e(rule.section)}</code> is absent or empty, or holds "
        "only placeholder text such as TBD or TBC.</li>"
    )
    if rule.rule_id in NOT_APPROVED_STATEMENT_RULE_IDS:
        emt = rule.rule_id.startswith("ANNEX_III.")
        roles = "“offeror”, “person seeking admission to trading” or “operator of the trading platform”"
        clause = "“of the crypto-asset is solely responsible”"
        return (
            f'<ul class="plain">{missing}'
            "<li><strong>Review</strong>: the draft is German, because the German wording has not been checked "
            "against the German Official Journal; the section holds only a yes or no value; a listed English "
            "term does not appear"
            + (
                ""
                if emt
                else f"; or {clause} appears without {roles} directly before it, as where the statement names the "
                "issuer or puts the offeror's name in between (“The offeror, Example AG, of the crypto-asset”)"
            )
            + ".</li><li><strong>Pass</strong>: an English draft holds both listed terms"
            + (
                ""
                if emt
                else f", and somewhere in the section {roles} comes directly before {clause}. Another person "
                "named elsewhere in the section is not checked"
            )
            + ". Matching ignores case and reads any run of spaces and line breaks as one space. A compound broken "
            "after its hyphen at a line end keeps the hyphen, so “crypto-” and “asset” on two lines match "
            "“crypto-asset”; a word split only for the line break (“Mem-”, “ber”) does not match and goes to "
            "review. Placement on the first page is not checked.</li></ul>"
        )
    groups = [variant for variant, _ in variants(rule.rule_id)]
    minimum = (
        f"{rule.min_words} words"
        if len({variant.min_words for variant in groups}) == 1
        else "the minimum number of words listed above for the draft's regime"
    )
    terms = (
        "a listed term"
        if len(
            {
                (v.required_terms, v.required_terms_de, v.required_patterns, v.required_patterns_de)
                for v in groups
            }
        )
        == 1
        else "a term listed for the draft's regime"
    )
    review = f"the section has fewer than {minimum}, or {terms} does not appear"
    match = "case-insensitive substring match, with any run of spaces and line breaks read as one space"
    if any(_named(v.required_patterns) or _named(v.required_patterns_de) for v in groups):
        match += "; a term shown with a pattern counts only where the pattern matches, so that a look-alike word does not stand in for it"
    parts = [
        missing,
        f"<li><strong>Review</strong>: {review} ({match}).</li>",
    ]
    unnamed = [pattern for pattern in rule.required_patterns if not re.compile(pattern).groupindex]
    unnamed += [pattern for pattern in rule.prohibited_patterns if not re.compile(pattern).groupindex]
    if unnamed:
        parts.append(
            "<li>Review also follows when a required pattern is absent or a prohibited pattern matches.</li>"
        )
    if any(_named(v.prohibited_patterns) or _named(v.prohibited_patterns_de) for v in groups):
        parts.append(
            "<li>Review also follows when the section uses one of the wordings shown above as sent to review, "
            "each of which turns a required statement around, such as a text saying that the crypto-asset "
            "cannot lose its value. The finding names the wording, not the draft text.</li>"
        )
    parts.append(
        (
            "<li>The predefined warning of Art. 6(7), Art. 19(6) and Art. 51(6), second subparagraph, does not "
            "count toward the minimum. A numbered-field XHTML draft leaves out field 07 of Table 2 (I.04 of Table 3, "
            "I.05 of Table 4) with its label, and any draft leaves out the warning's sentences where they appear in "
            "the template's English or German wording. The finding then gives the words besides the warning.</li>"
            "<li>Review also follows when a point of that warning, (a) to (d), is not found in the template's "
            "English or German wording, whichever language the draft is in; the finding names the points not found. "
            "The patterns also take the Regulation's own openings (“the summary should be read”, “the crypto-asset "
            "white paper does not constitute”) where the template says “this”. A numbered-field XHTML draft is read "
            "by field 07 of Table 2 (I.04 of Table 3, I.05 of Table 4) alone: a field that is empty, absent or holds "
            "only a placeholder such as TBD counts as absent, and the finding names it.</li>"
            "<li>For an asset-referenced or e-money token, Review also follows when no sentence names redemption "
            "(“redemption”, “redeem”, “Rücktausch”) together with “at any time” or “at all times” (“jederzeit”), the "
            "statement of Art. 19(6) and Art. 51(6), third subparagraph, and for an e-money token when par value "
            "(“par value”, “at par”, “Nennwert”) is not named in the text read. A numbered-field XHTML draft is read "
            "by field I.06 of Table 3 or I.07 of Table 4 alone, with the same rule for an empty or placeholder "
            "field. Other crypto-assets are not asked for a redemption statement.</li>"
            if rule.rule_id == "COMMON.SUMMARY"
            else ""
        )
        + "<li>In a numbered-field XHTML draft, Review also follows when a field of the section holds only a "
        "placeholder such as TBD; the finding names the field by its number and, in English, the template's "
        "name.</li>"
    )
    if rule.rule_id == "ANNEX_II.I":
        parts.append(
            "<li>Review also follows when the section mentions par value anywhere: the word “par” (as in “at "
            "par”, “par value” or “at-par”), “face value”, “nominal value”, “nominal amount”, “nominal price” or "
            "“at nominal”, or a form of “Nennwert”, “Nennbetrag”, “Nominalwert”, “Nominalbetrag”, “nominaler "
            "Wert”, “nomineller Wert”, “zum Nominale”, “pari”, “Pariwert”, “Parikurs” or “Parirücktausch”, in "
            "drafts of either language and ignoring case. A soft hyphen, a zero-width character or a hyphen at a "
            "line end inside the word does not hide it. Only uses that never mean par value do not count: “par” "
            "for a paragraph next to an article number (“Art. 39 par. 2”, “par. 2 of Art. 39”), “on par” or “on a "
            "par”, “par for the course”, “par excellence”, “sub-par”, “pari passu”, “rank at par” and “at par "
            "with each other” or “with one another”. The issue says that redemption at par value is the e-money "
            "token rule of Art. 49(4) MiCAR and that an ART issuer redeems by paying funds, other than electronic "
            "money, equivalent to the market value of the referenced assets, or by delivering those assets "
            "(Art. 39(2) MiCAR), and asks the reviewer to check whether the section ties the token's redemption "
            "to par value.</li>"
        )
    parts.append(
        "<li><strong>Pass</strong>: none of the above. A pass means the check matched, nothing more.</li>"
    )
    return '<ul class="plain">' + "".join(parts) + "</ul>"


def _contact_fields(rule: Rule) -> tuple[str, str, str, str]:
    """The three template fields of a point rule and the words that name them with their table."""
    regime = regimes_by_rule()[rule.rule_id][0]
    phone, email, days = CONTACT_FIELDS[regime]
    return phone, email, days, f"fields {phone}, {email} and {days} of Table {POINT_TABLES[regime]}"


def _contact_status_logic(rule: Rule) -> str:
    phone, email, days, fields = _contact_fields(rule)
    section = f"<code>{_e(rule.section)}</code>"
    return (
        f'<ul class="plain"><li><strong>Missing</strong>: in a numbered-field XHTML draft, {fields} are each '
        f"empty, absent or hold only placeholder text such as TBD; in any other draft, section {section} is absent "
        "or empty, or holds only placeholder text.</li>"
        "<li><strong>Review</strong>: in a numbered-field XHTML draft, one of those fields is empty or absent, holds "
        "only a placeholder, is marked not applicable, which the template does not provide for, or gives no "
        f"telephone number ({phone}), no e-mail address ({email}) or no number of days ({days}). In any other "
        f"draft, section {section} gives no telephone number, no e-mail address or no period in days. The finding "
        "names each missing item, and in a numbered-field draft each field by its number and, in English, the "
        "template's name.</li>"
        "<li>A telephone number counts with its country code (<code>+49 ...</code>, <code>0049 ...</code>), with "
        "its area code and its digits in groups (<code>069 1234 5678</code>, <code>(069) 1234-5678</code>), or "
        f"with at least six digits after a label such as Tel., Phone or Telefon; field {phone} is such a label. A "
        "fax number and a date do not count. An e-mail address counts as name, @ and domain. A period counts as a "
        "number of days, in digits or as an English or German word up to thirty (<code>5 business days</code>, "
        "<code>fünf Werktage</code>), or as a number after the template's label (<code>Response time (Days): "
        f"5</code>, <code>Reaktionszeit (Tage): 5</code>). In field {days} a number counts alone, unless the field "
        "names hours, weeks, months or years.</li>"
        "<li><strong>Pass</strong>: all three items are found. A pass means the three shapes were found, nothing "
        "more.</li></ul>"
    )


def rule_page(rule: Rule, regimes: list[WhitepaperType]) -> str:
    family = rule.rule_id.split(".")[0]
    groups = variants(rule.rule_id)
    if len(groups) > 1 and rule.rule_id not in VARIANT_NOTES:
        raise SystemExit(f"{rule.rule_id}: its settings differ by regime; add an entry to VARIANT_NOTES")

    def by_regime(render: Callable[[Rule], str]) -> str:
        rendered = [(render(variant), found) for variant, found in groups]
        if len({text for text, _ in rendered}) == 1:
            return rendered[0][0]
        return "; ".join(f"{text} ({_annexes(found)})" for text, found in rendered)

    variant_note = f"<p>{_e(VARIANT_NOTES[rule.rule_id])}</p>" if len(groups) > 1 else ""
    prohibited = ""
    if any(variant.prohibited_patterns or variant.prohibited_patterns_de for variant, _ in groups):
        prohibited = (
            "<dt>Wording sent to review (English)</dt>"
            f"<dd>{by_regime(lambda r: _terms((), r.prohibited_patterns))}</dd>\n"
            '<dt>Wording sent to review (German)</dt><dd lang="de">'
            f"{by_regime(lambda r: _terms((), r.prohibited_patterns_de))}</dd>\n"
        )
    citation_en = citations.to_english(rule.citation)
    sources = "".join(
        f'<li><a href="{_e(url)}">{_e(url)}</a></li>' for url in citations.source_urls(rule.citation)
    )
    limitations = [
        (
            "Reads no section. It checks the file format, so adding a section to a draft cannot change its status."
            if rule.rule_id in FORMAT_GATE
            else "Reads every section of the draft; findings are anchored to the <code>issuer</code> section."
            if rule.rule_id in LEI_RULES
            else f"Reads one section key, <code>{_e(rule.section)}</code>, and in a numbered-field XHTML draft only "
            f"{_contact_fields(rule)[3]}. Text elsewhere in the draft is not considered."
            if rule.rule_id in CONTACT_POINT_RULE_IDS
            else f"Reads one section key, <code>{_e(rule.section)}</code>. Text elsewhere in the draft is not considered."
        ),
        (
            "Reads draft metadata and percentages only. It does not test accuracy or decide whether a floor is met."
            if rule.rule_id == "ANNEX_II.G.DEPOSIT_FLOOR_REVIEW"
            else "Checks the file format and taxonomy namespace only, not tag completeness."
            if rule.rule_id == "COMMON.IXBRL_TAGGING"
            else "Works offline on the characters of each code. It does not confirm that an LEI is registered, "
            "current or held by the entity the draft names."
            if rule.rule_id in LEI_RULES
            else "Matches the English wording only. It cannot see whether the statement is on the first page, and "
            "it does not check that the person it names is the one responsible for the white paper."
            if rule.rule_id in NOT_APPROVED_STATEMENT_RULE_IDS
            else "Looks for a calendar date only. It does not confirm that the date is the date of notification "
            "or that it is plausible, and it does not check the table of contents that the same provisions "
            "require. Since 23 December 2025 the template of Implementing Regulation (EU) 2024/2984 has the "
            "date reported as YYYY-MM-DD; the check accepts the other formats above as well and does not test that form."
            if rule.rule_id == "COMMON.NOTIFICATION_DATE"
            else "Looks for a language name only. The cited paragraphs require the white paper to be drawn up in "
            "an official language of the home Member State or in a language customary in the sphere of "
            "international finance, and likewise for a host Member State where the crypto-asset is also "
            "offered. They do not require the white paper to name its language; since 23 December 2025 the "
            "template of Implementing Regulation (EU) 2024/2984 asks for it (field F.12 of Table 2, B.14 of "
            "Table 3, B.11 of Table 4). The check cannot tell which language the white paper is drawn up in, "
            "or whether that language meets the requirement. Language codes such as EN and names in other "
            "languages, such as français, do not count."
            if rule.rule_id == "COMMON.LANGUAGE"
            else "Recognises the shape of each item. It cannot tell whose number or address it is or whether it "
            "works, so in a draft without field numbers any telephone number, e-mail address and period in days in "
            "the section count, a management body member's too, and the period need not be the response time. A "
            "number without its country code, a grouped area code or a label, an e-mail address written with (at) "
            "and a period in hours or weeks do not count."
            if rule.rule_id in CONTACT_POINT_RULE_IDS
            else "Matches words and counts length. It does not test accuracy, consistency with other sections or "
            "the point-level items of the cited Part."
        ),
        "Status and severity are fixed by the rule. A draft cannot waive or downgrade them.",
    ]
    if family in UNTESTED_REGIMES:
        limitations.append(UNTESTED_REGIMES[family])
    if rule.rule_id == "COMMON.LEI_CHECK_DIGITS":
        limitations.append(
            "Does not recognise the other identifiers that point 5 allows in place of the LEI, so a draft "
            "without any LEI goes to review once a party section has text. Once the draft gives one LEI, a "
            "party section without an LEI of its own does not change the result."
        )
    if rule.rule_id == "COMMON.LEI_CONSISTENCY":
        limitations.append(
            "Does not recognise the other identifiers that point 5 allows in place of the LEI, so a draft "
            "whose party sections carry no valid LEI goes to review. Once one party section carries a valid "
            "LEI, another party section without an LEI does not change the result."
        )
        limitations.append(
            "Knows a person other than the parties only from the words before the code in its sentence or "
            "field label (CASP, crypto-asset service provider, custodian, other than the issuer, other persons "
            "drawing up, and the German Kryptowerte-Dienstleistungen, Verwahrer, nicht mit dem Emittenten "
            "identisch). A role named in an earlier sentence does not carry over: in \"The custodian is Example "
            "Bank AG. Its LEI is ...\" the code is still compared with the party sections."
        )
    if rule.rule_id in CONTACT_POINT_RULE_IDS:
        limitations.append(
            "A numbered-field XHTML draft is read by the template's field numbers. Contact details in another field "
            "do not count, and a draft that numbers these fields otherwise goes to review."
        )
    if rule.rule_id == "COMMON.SUMMARY":
        limitations.append(
            "Recognises the warning only in the template's English or German wording, with the Regulation's own "
            "openings. A warning in other words counts toward the 80 words and goes to review, as does a point "
            "split across sentences. The check cannot see whether the summary follows the statement of the "
            "management body, as the cited paragraphs require."
        )
        limitations.append(
            "Reads the redemption statement from one sentence that names redemption and “at any time” (for an "
            "e-money token, par value anywhere in the text read). The conditions for redemption, which the same "
            "sentence of the Regulation requires the summary to state, are not checked, and nor is whether the "
            "statement is true. In a numbered-field XHTML draft a warning or redemption statement outside its "
            "template field is not seen."
        )
    if rule.rule_id == "COMMON.RISK_WARNING":
        limitations.append(
            "Recognises a statement turned around only in the wordings shown above, in English and German. A "
            "contradiction worded otherwise still passes, and so does one in another section."
        )
    if rule.rule_id in NOT_APPROVED_STATEMENT_RULE_IDS:
        emt = rule.rule_id.startswith("ANNEX_III.")
        field = "I.02" if emt else "02"
        limitations.append(
            "PDF, DOCX, Markdown and heading-based XHTML drafts fill the section from a heading such as “Statement "
            f"in accordance with Article {'51' if emt else '6'}(3)”, the label of field {field} of Table "
            f"{'4' if emt else '2'} of Implementing Regulation (EU) 2024/2984, where the label is set as one (a "
            "Markdown “#” heading, an XHTML h1 to h6 or bold label, a DOCX heading or bold or capitals label, a PDF "
            "heading or field line), or, without one, from a line or paragraph that opens with the statement's "
            f"first words. Numbered-field XHTML fills it from field {field}. Table cells are not read in DOCX, nor "
            "in heading-based XHTML where the text sits directly in a td or th element rather than in a p, div, li "
            "or bold element inside it, so a statement kept only there is reported missing."
        )
        limitations.append(
            "A German draft never passes: the German wording has not been checked against the German Official "
            "Journal."
        )
    if rule.rule_id == "ANNEX_II.I":
        limitations.append(
            "The note on par value reads the words alone. It also follows where par value "
            "describes the reserve of assets, issuance or the cover of the reserve, where the section says that "
            "the token is not redeemed at par, and in idioms such as “take at face value”; the reviewer decides "
            "whether the token's redemption depends on par value. Other words for the same basis, such as "
            "“1:1”, “dollar for dollar” or “at parity”, are not found. Text that the loader does not put into "
            "the redemption section is not read: a heading, and a table in a DOCX or heading-based XHTML draft."
        )
    if rule.rule_id in NEVER_PASS:
        limitations.append("This rule never reports Pass.")
    example_html = []
    for variant, found in groups:
        suffix = f" ({_annexes(found)})" if len(groups) > 1 else ""
        for example in examples(variant, found[0]):
            title = example.title + suffix
            actual = lint_example(variant, example)
            if actual != example.expected:
                raise SystemExit(
                    f"{rule.rule_id}: example '{title}' gives {actual}, page states {example.expected}"
                )
            example_html.append(
                f'<div class="example"><div class="example-head">{_status_badge(example.expected)}'
                f'<strong>{_e(title)}</strong></div><p class="small muted">{_e(example.note)}</p>'
                f"<pre><code>{_e(json.dumps(example.draft, indent=2, ensure_ascii=False))}</code></pre></div>"
            )
    body = f"""<p class="eyebrow">Rule · {_e(rule.severity.label)}</p>
<h1>{_e(rule.rule_id)}</h1>
<p class="lede">{_e(rule.label)}</p>
<div class="panel"><dl class="facts">
<dt>Citation</dt><dd>{_e(citation_en)}</dd>
<dt>Canonical form</dt><dd lang="de">{_e(rule.citation)}</dd>
<dt>Runs for</dt><dd>{_e("; ".join(REGIME_NAMES[r] for r in regimes))}</dd>
<dt>Severity if open</dt><dd>{_e(rule.severity.label)}</dd>
<dt>Section key</dt><dd>{"none: checks the file format" if rule.rule_id in FORMAT_GATE else "all sections; anchored to <code>issuer</code>" if rule.rule_id in LEI_RULES else f"<code>{_e(rule.section)}</code>"}</dd>
<dt>Minimum words</dt><dd>{f"none: checks for {ANSWER_CHECKS[rule.rule_id]}" if rule.rule_id in ANSWER_CHECKS else by_regime(lambda r: str(r.min_words))}</dd>
<dt>Listed terms (English)</dt><dd>{by_regime(lambda r: _terms(r.required_terms, r.required_patterns))}</dd>
<dt>Listed terms (German)</dt><dd lang="de">{by_regime(lambda r: _terms(r.required_terms_de, r.required_patterns_de))}</dd>
{prohibited}<dt>Package version</dt><dd>{_e(__version__)}, built from source that may include unreleased changes</dd>
<dt>Source</dt><dd><a href="{REPO}/blob/main/src/micar_linter/rules/{SOURCE_MODULES[family]}">rules/{SOURCE_MODULES[family]}</a></dd>
</dl></div>
<h2>How the status is set</h2>
{status_logic(rule)}{variant_note}
<h2>Legal basis</h2>
<p>{_e(citation_en)}</p>
<ul class="plain">{sources}</ul>
<p class="callout">{_e(LEI_VERIFICATION_NOTE if rule.rule_id in LEI_RULES else verification_note(rule.rule_id))}</p>
<h2>Synthetic examples</h2>
<p class="small muted">Each example is linted when this page is generated. The build fails if a result differs.</p>
{"".join(example_html)}
<h2>Limitations</h2>
<ul class="plain">{"".join(f"<li>{item}</li>" for item in limitations)}</ul>
<p class="small muted">Disagree with this rule, or missing one? <a href="{REPO}/issues/new?template=rule-proposal.yml">Propose a rule change</a>.</p>
"""
    return _page(f"{rule.rule_id}: MiCAR Whitepaper Linter rule", f"{rule.label}. {citation_en}.", body)


def index_page(rules: list[Rule], regimes: dict[str, list[WhitepaperType]]) -> str:
    sections = []
    for regime, name in REGIME_NAMES.items():
        rows = "".join(
            f'<tr><td><a href="{_e(rule.rule_id)}.html"><code>{_e(rule.rule_id)}</code></a></td>'
            f"<td>{_e(rule.label)}</td><td>{_e(rule.severity.label)}</td>"
            f"<td>{_e(citations.to_english(rule.citation))}</td></tr>"
            for rule in RULESETS[regime]
        )
        sections.append(
            f'<h2>{_e(name)} <span class="muted small">({len(RULESETS[regime])} rules)</span></h2>'
            '<div class="table-wrap"><table><thead><tr><th scope="col">Rule</th><th scope="col">Checks for</th>'
            f'<th scope="col">Severity</th><th scope="col">Citation</th></tr></thead><tbody>{rows}</tbody></table></div>'
        )
    body = f"""<p class="eyebrow">Rule reference</p>
<h1>Rules</h1>
<p class="lede">{len(rules)} deterministic checks, generated from the rule set of package version {_e(__version__)}, built from source that may include unreleased changes. Each page
states the citation, how the status is set, synthetic examples that are tested on every build, and the limits of the
check.</p>
<p class="callout">A pass means a check matched. It is not a compliance opinion. Not legal advice.</p>
{"".join(sections)}
"""
    return _page(
        "Rules: MiCAR Whitepaper Linter", "Reference pages for every MiCAR Whitepaper Linter rule.", body
    )


def build_pages() -> dict[str, str]:
    regimes = regimes_by_rule()
    rules = all_rules()
    pages = {f"{rule.rule_id}.html": rule_page(rule, regimes[rule.rule_id]) for rule in rules}
    pages["index.html"] = index_page(rules, regimes)
    return dict(sorted(pages.items()))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    pages = build_pages()
    for stale in OUT.glob("*.html"):
        if stale.name not in pages:
            stale.unlink()
    for name, text in pages.items():
        (OUT / name).write_text(text, encoding="utf-8")
    print(f"wrote {len(pages)} pages to {OUT.relative_to(ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
