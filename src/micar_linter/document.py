"""PDF and DOCX document ingestion and section parsing."""

from __future__ import annotations

import math
import re
import statistics
from bisect import bisect_right
from collections import Counter
from collections.abc import Callable, Iterable
from contextlib import suppress
from dataclasses import dataclass, replace
from functools import partial
from itertools import pairwise
from pathlib import Path
from typing import NamedTuple

from micar_linter.placeholders import is_not_applicable, is_placeholder
from micar_linter.rules.annex_i import NOT_APPROVED_STATEMENT_EN

# The start of a redemption pattern: a heading that names a risk, in English or German ("Redemption risk",
# "Rücknahmerisiko", "Risiken beim Rücktausch"), heads a risk and does not open the redemption section, so
# no risk text reaches the redemption check. (?s) reads past a line break inside a DOCX heading.
_NOT_A_RISK = r"(?s)^(?!.*(?:\brisk|risik)).*?"

# Common patterns (in English and German) matching whitepaper section headings.
# Word boundaries are used to avoid false positives.
SECTION_PATTERNS = {
    # The Art. 6(3) / Art. 51(3) statement, labelled as in Implementing Regulation (EU) 2024/2984.
    "not_approved_statement": [
        r"\bstatement\s+in\s+accordance\s+with\s+art(?:icle|\.)\s*(?:6|51)\s*\(3\)",
        r"\berklärung\s+gemäß\s+art(?:ikel|\.)\s*(?:6|51)\s+abs(?:atz|\.)\s*3\b",
    ],
    "summary": [
        r"\bsummary\b",
        r"\bzusammenfassung\w*",
        r"\bplain-language\s+summary\b",
        r"\bkey\s+information\b",
    ],
    "risk_warning": [r"\brisk\s+warning\b", r"\bwarnhinweis\w*", r"\bmandatory\s+warning\b"],
    "management_statement": [
        r"\bmanagement\s+body\b",
        r"\bleitungsorgan\w*",
        r"\bmanagement\s+statement\b",
        r"\bstatement\b.*\bmanagement\b",
        # Field 03 of Table 2 of the Implementing Regulation (EU) 2024/2984 template, "Compliance
        # statement in accordance with Article 6(6)", holds the statement of the management body.
        r"\bcompliance\s+statement\b",
    ],
    "notification_date": [
        r"\bdate\s+of\s+notification\b",
        r"\bnotifizierungsdatum\w*",
        r"\bnotification\s+date\b",
        # The German texts: Art. 6 Abs. 8, Art. 19 Abs. 7 and Art. 51 Abs. 7 MiCAR ask for "das Datum seiner
        # Übermittlung", and field 01 (I.01) of the Implementing Regulation (EU) 2024/2984 template is
        # "Datum der Mitteilung". The compounds "Übermittlungsdatum" and "Mitteilungsdatum" name the same
        # date. Other fields of the template, such as "Art der Übermittlung" and "Methoden der Übermittlung
        # des Werts", do not open this section.
        r"\bdatum\s+der\s+(?:übermittlung|mitteilung|notifizierung)\b",
        r"\b(?:übermittlungs|mitteilungs)datum\w*",
    ],
    # "Plain-language summary" heads the summary; it would otherwise feed the summary to the language check.
    "language": [r"(?<!plain[- ])\blanguage\b", r"\bsprache\w*"],
    "offeror": [r"\bofferor\b", r"\banbieter\w*"],
    "issuer": [r"\bissuer\b", r"\bemittent\w*"],
    "trading_platform_operator": [
        r"\btrading\s+platform\b",
        r"\bhandelsplattform\w*",
        r"\boperator\b.*\btrading\b",
    ],
    "project": [r"\bproject\b", r"\bprojekt\w*", r"\bbusiness\s+model\b", r"\bteam\b"],
    "offer_or_admission": [
        r"\bpublic\s+offer\b",
        r"\bzulassung\w*",
        r"\badmission\s+to\s+trading\b",
        r"\boffer\b.*\badmission\b",
    ],
    "crypto_asset": [
        r"\bcrypto-asset\b",
        # The title of Part F, "Information about the crypto-assets", but not the plural in the titles of
        # Part E ("offer to the public of crypto-assets") and Part G ("attached to the crypto-assets").
        r"\b(?:about|on)\s+the\s+crypto-assets\b(?!-)",
        r"\bcrypto\s+asset\b",
        r"\bcharacteristics\b.*\bcrypto\b",
        r"\binformation\s+about\s+the\s+token\b",
        r"\bthe\s+token\b",
    ],
    "art": [
        r"\basset-referenced\s+token\b",
        r"\bstabilisation\s+mechanism\b",
        r"\breference\s+assets\b",
        r"\binformation\s+about\s+the\s+token\b",
        r"\bthe\s+token\b",
    ],
    "emt": [
        r"\be-money\s+token\b",
        r"\bdenomination\b",
        r"\breferenced\s+currency\b",
        r"\binformation\s+about\s+the\s+token\b",
        r"\bthe\s+token\b",
    ],
    "rights_and_obligations": [
        r"\brights\s+and\s+obligations\b",
        r"\brechte\s+und\s+pflichten\b",
        r"\bholder\s+rights\b",
    ],
    "technology": [
        r"\btechnology\b",
        r"\btechnologie\w*",
        r"\bunderlying\s+technology\b",
        r"\bdlt\b",
        r"\bconsensus\b",
    ],
    "risks": [r"\brisk\s+factors\b", r"\brisikofaktor\w*", r"\brisks\b", r"\brisiken\b"],
    "environmental_impact": [
        r"\benvironmental\b",
        r"\bclimate\b",
        r"\bsustainability\b",
        r"\bumwelt\w*",
        r"\bklima\w*",
    ],
    "reserve_of_assets": [r"\breserve\b.*\bassets\b", r"\breservevermögen\w*", r"\basset\s+reserve\b"],
    "redemption": [
        rf"{_NOT_A_RISK}\bredemption\b",
        rf"{_NOT_A_RISK}\brücknahme\w*",
        rf"{_NOT_A_RISK}\bredemption\s+right\b",
        # The German text of MiCAR calls redemption "Rücktausch": "Recht auf Rücktausch" (Art. 39),
        # "Rücktauschplan" (Art. 47), "Rücktauschbarkeit" (Art. 49) and "dauerhaften Rücktauschrechte"
        # (Anhang II Teil D Nr. 9), as do the labels of Implementing Regulation (EU) 2024/2984 ("Recht auf
        # Rücktausch", "Form des Rücktauschs").
        rf"{_NOT_A_RISK}\brücktausch\w*",
    ],
    "safeguarding": [r"\bsafeguarding\b", r"\babsicherung\w*", r"\bsicherung\w*.*\bgelder\w*"],
}


# Art. 6(3) and Art. 51(3) MiCAR put the statement on the first page without a heading of
# its own, so a paragraph that opens with it is routed by its content. The German opening
# is a routing heuristic only; the rule does not treat it as verified statutory wording.
_STATEMENT_START = re.compile(
    r"^\W*(?:this\s+crypto-asset\s+white\s+paper\s+has\s+not\s+been\s+approved"
    r"|dieses\s+kryptowerte-whitepaper\s+wurde\s+von\s+keiner)\b",
    re.IGNORECASE,
)
# The statement has two sentences: the one opening above, then the one naming who is solely
# responsible for the content. Each is about 20 words in Art. 6(3) and Art. 51(3).
_RESPONSIBILITY = re.compile(r"\b(?:responsib|verantwort)\w*", re.IGNORECASE)
# The responsibility sentence as Art. 6(3) and Art. 51(3) word it: the person it names, then the clause
# "is solely responsible for the content of this crypto-asset white paper". The German pair is a
# routing heuristic, like the German opening.
_RESPONSIBILITY_CLAUSE = re.compile(
    r"\bsolely\s+responsible\s+for\s+the\s+content\b|\balleinige\s+verantwortung\s+für\s+den\s+inhalt\b",
    re.IGNORECASE,
)
_RESPONSIBLE_PERSON = re.compile(
    r"\bthe\s+(?:offeror|issuer|person|operator)\b|\b(?:der|die)\s+(?:anbieter|emittent|betreiber|person)\b",
    re.IGNORECASE,
)
# The words the statutory sentence puts between the person and the clause: "of the crypto-asset is",
# "seeking admission to trading of the crypto-asset is", "of the trading platform of the crypto-asset is",
# "des Kryptowerts trägt die", ", die die Zulassung des Kryptowerts zum Handel beantragt, trägt die" and
# "der Handelsplattform des Kryptowerts trägt die" (Table 2 field 02 and Table 4 field I.02 of Implementing
# Regulation (EU) 2024/2984), with MiCAR's own ", die die Zulassung zum Handel beantragt," (Art. 6 Abs. 3
# UAbs. 2). Drafting variants such as "of the e-money token is" count too. A person named elsewhere, as in
# a part title above a sentence with a subject of its own ("Example AG is solely responsible ..."), is not
# the one the clause makes responsible.
_PERSON_TO_CLAUSE = re.compile(
    r"(?:\s+(?:seeking\s+admission\s+to\s+trading|of\s+the\s+trading\s+platform))?"
    r"(?:\s+of\s+the\s+[\w-]+(?:(?<=-)\s+[\w-]+)?(?:\s+tokens?)?)?\s+is\s+"
    r"|(?:\s+(?:des|der)\s+[\w-]+(?:(?<=-)\s+[\w-]+)?){0,2}"
    r"(?:,\s+die\s+die\s+zulassung(?:\s+des\s+[\w-]+)?\s+zum\s+handel\s+beantragt,)?"
    r"(?:\s+des\s+[\w-]+)?\s+trägt\s+die\s+",
    re.IGNORECASE,
)
# The words that end the clause, "of this crypto-asset white paper" ("dieses Kryptowerte-Whitepapers"), with
# any stop, quote or note mark attached, and however a line break or a hyphen at a line end splits them.
_CLAUSE_WORDS = re.compile(
    r"\s+(?:of\s+this\s+crypto-\s*asset\s+white\s+paper|dieses\s+kryptowerte-\s*whitepapers?)"
    # A letter may not follow ("papers"); a note mark stuck to the word may ("paper2", "paper\u00b2").
    r"(?![^\W\d_\u00b9\u00b2\u00b3\u2070-\u2079])\S*",
    re.IGNORECASE,
)
# Where the clause ends in other words, the rest of its sentence up to the stop.
_CLAUSE_TAIL_MAX_WORDS = 8
# A full stop may sit inside closing quotes, brackets or Markdown emphasis, or before a note mark:
# 'paper.”', 'Whitepapers.“', 'paper.**', 'paper.[^1]', 'paper.¹', and 'Union.1' in extracted PDF text.
# A note mark follows a word, never a field or outline number such as "A.1", "I.03" or "IV.2".
_STATEMENT_SENTENCE_END = re.compile(
    r"[.!?](?:[\"'\u2018\u2019\u201c\u201d\u00ab\u00bb)\]*_]|\[\^\w+\]|[\u00b9\u00b2\u00b3\u2070-\u2079])*"
    r"(?:(?<=[^\W\d_]{2}[.!?])(?<!\b[IVX]{2}[.!?])(?<!\b[IVX]{3}[.!?])(?<!\b[IVX]{4}[.!?])\d{1,2})?(?=\s|$)"
)
_STATEMENT_MAX_LINES = 12
_SENTENCE_MAX_WORDS = 30
_HEADING_MAX_WORDS = 12


def is_statement_start(text: str) -> bool:
    """True where a line or paragraph opens with the Art. 6(3) / Art. 51(3) statement."""
    return bool(_STATEMENT_START.match(text))


# A narrow column, a box or a statement set a line per paragraph can wrap its opening words
# ("This crypto-asset white paper has not been" / "approved by ...") over the next lines.
_STATEMENT_START_LINES = 4


def opens_statement(texts: list[str], index: int) -> bool:
    """True where texts[index] opens the statement, read with the lines its opening words wrap onto."""
    if not re.search(r"\w", texts[index]):
        # A separator line ("---", "* * *") or a bullet above the statement is not part of it.
        return False
    window = "\n".join(texts[index : index + _STATEMENT_START_LINES])
    return is_statement_start(re.sub(r"-[ \t]*\n\s*", "-", window))


def looks_like_heading(text: str) -> bool:
    """True for a Markdown heading, or a short line without closing punctuation that names a section."""
    stripped = text.strip()
    if stripped.startswith("#"):
        return True
    if not stripped or len(stripped.split()) > _HEADING_MAX_WORDS or stripped[-1] in ".,;:!?":
        return False
    return bool(match_heading_to_section(stripped))


def statement_extent(lines: list[str], start: int, is_heading: Callable[[int], bool] | None = None) -> int:
    """Index after the last line of the statement that opens at lines[start].

    A wrapped statement in a PDF or a hard-wrapped Markdown file spans several lines, and
    its continuation lines often contain words such as "crypto-asset" or "offeror" that the
    heading heuristics would otherwise read as new section headings. The statement ends
    with its opening sentence, or with the next sentence where that one is short and says
    who is responsible. It never runs past a heading, so an incomplete or reworded
    statement cannot swallow the sections that follow it. It takes whole lines: text after
    the statement in its last line stays with it.

    is_heading(index) reports a heading the loader reads from the layout, such as a DOCX
    paragraph in a Heading style or a PDF line in a heading font. A statement may be set
    apart in bold, capitals or a larger font, so the lines of the statutory responsibility
    sentence, from the person it names to the end of the clause, are recognised by their
    words and never read as a heading, whatever their layout or spacing.
    """
    window = lines[start : start + _STATEMENT_MAX_LINES]
    text = " ".join(window)
    line_ends: list[int] = []
    offset = 0
    for line in window:
        line_ends.append(offset + len(line))
        offset += len(line) + 1

    def line_at(position: int) -> int:
        return next(i for i, line_end in enumerate(line_ends) if line_end >= position)

    def marked(i: int) -> bool:
        return window[i].lstrip().startswith("#") or (is_heading is not None and is_heading(start + i))

    own: range = range(0)
    # Whether the responsibility sentence holds every statutory word, so the statement is whole at its end.
    complete = False
    clause = _RESPONSIBILITY_CLAUSE.search(text)
    if clause:
        persons = [
            person
            for person in _RESPONSIBLE_PERSON.finditer(text, 0, clause.start())
            if _PERSON_TO_CLAUSE.fullmatch(text, person.end(), clause.start())
        ]
        own_end = line_at(clause.end())
        words = _CLAUSE_WORDS.match(text, clause.end())
        tail = _STATEMENT_SENTENCE_END.search(text, clause.end())
        if words:
            # The statutory words, however they are set, with or without the stop.
            own_end, complete = line_at(words.end()), True
        elif tail and len(text[clause.end() : tail.end()].split()) <= _CLAUSE_TAIL_MAX_WORDS:
            # The rest of the sentence ("of this crypto-asset white paper."), but never a line that opens a
            # heading or a numbered label: a sentence that has lost its stop ends before it.
            own_end = next(
                (
                    i - 1
                    for i in range(own_end + 1, line_at(tail.end()) + 1)
                    if marked(i) or _NUMBERING.match(window[i].lstrip())
                ),
                line_at(tail.end()),
            )
        own = range(line_at((persons[-1] if persons else clause).start() + 1), own_end + 1)

    def firm_heading(i: int) -> bool:
        return i not in own and marked(i)

    # Continuation lines of the opening sentence never name a section, so a line that ends
    # inside it and looks like a heading means the sentence was cut short. The line where
    # the sentence ends may already start the next one ("Union. The offeror"), so it is
    # not read as a heading.
    first = _STATEMENT_SENTENCE_END.search(text)
    first_end = first.end() if first else len(text) + 1
    for i in range(1, len(window)):
        if line_ends[i] < first_end and i not in own and (looks_like_heading(window[i]) or firm_heading(i)):
            return start + i
    last = line_at(first_end) if first else None
    # A responsibility sentence with every statutory word, right after the opening one, ends the statement
    # with the line of its last word, whatever follows it there or after it: no stop, a heading, a label, a
    # note or a run-on.
    if (
        complete
        and (last is None or own.start <= last + 1)
        and not any(firm_heading(i) for i in range(1, own.start))
    ):
        return start + own.stop
    if first is None or last is None:
        return start + 1

    # The responsibility sentence of a narrow PDF column can look like a heading
    # ("The offeror of the crypto-asset is solely"), so only firm headings end it early.
    second = _STATEMENT_SENTENCE_END.search(text, first_end)
    if second is None:
        return start + last + 1
    sentence = text[first_end : second.end()]
    if len(sentence.split()) > _SENTENCE_MAX_WORDS or not _RESPONSIBILITY.search(sentence):
        return start + last + 1
    closing = line_at(second.end())
    heading = next((i for i in range(last + 1, closing + 1) if firm_heading(i)), None)
    if heading is not None:
        # A responsibility sentence that has lost its stop ends with its own lines, before the heading.
        return start + (
            own.stop if own and own.start <= last + 1 and last < own.stop <= heading else last + 1
        )
    return start + closing + 1


def paragraph_statement_extent(
    paragraphs: list[str], start: int, is_heading: Callable[[int], bool] | None = None
) -> int:
    """statement_extent for a loader that reads paragraphs (DOCX, XHTML) rather than wrapped lines.

    An opening paragraph without a full stop was cut off, unless the paragraphs after it carry on the
    English opening sentence word for word, as a statement set a line per paragraph does. So the paragraph
    after a cut-off opening is not taken in, whatever its first sentence.
    """
    end = statement_extent(paragraphs, start, is_heading)
    for index in range(start + 1, end):
        if _STATEMENT_SENTENCE_END.search(" ".join(paragraphs[start:index])):
            break
        joined = re.sub(r"-[ \t]*\n\s*", "-", "\n".join(paragraphs[start : index + 1]))
        joined = re.sub(r"^\W+", "", " ".join(joined.split()).lower())
        if not (NOT_APPROVED_STATEMENT_EN.startswith(joined) or joined.startswith(NOT_APPROVED_STATEMENT_EN)):
            return index
    return end


def match_heading_to_section(heading: str) -> list[str]:
    """Matches a heading line to a list of known ruleset section keys."""
    normalized = heading.lower()
    matched = []
    for key, patterns in SECTION_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, normalized):
                matched.append(key)
                break
    return matched


# Formatting alone does not make a heading: a body sentence that mentions a section word
# ("Note: purchasers bear market, liquidity and technology risks.") must not open that section.
_MAX_HEADING_WORDS = 12
# A label that its numbering or its font marks as a heading may run longer: the part titles of the
# Implementing Regulation (EU) 2024/2984 template have up to 20 words, with or without the part letter
# ("Information about the offer to the public of crypto-assets or their admission to trading").
_MAX_MARKED_HEADING_WORDS = 20
# A question mark may end a heading ("Risks: What Could Go Wrong?"); these marks end a sentence or a phrase.
_SENTENCE_END = re.compile(r"[.!;,]$")
# A word of four or more letters, a full stop and a capitalised word: "Risks. Holders may lose ...".
# "A.1 Name", "5.2 Risks" and "Ledger S.A. Risks" have no such word.
_SENTENCE_BREAK = re.compile(r"([^\W\d_]{4,})[.!?]\s+([^\W\d_])")
# The same, from the first letter of a word only (see _sentence_breaks).
_WORD_SENTENCE_BREAK = re.compile(rf"(?<![^\W\d_]){_SENTENCE_BREAK.pattern}")
# Abbreviations that keep their full stop inside a heading: "5. Risks (incl. Liquidity Risks)",
# "Quillmoor Corp. Risk Factors", "Risiken bzgl. des Tokens".
_ABBREVIATIONS = frozenset(
    {
        "abschn", "abzgl", "approx", "assoc", "buchst", "bzgl", "corp", "dept", "einschl", "evtl", "excl", "incl",
        "inkl", "insb", "intl", "mgmt", "resp", "sect", "unterabs", "ziff", "zzgl",
    }
)  # fmt: skip
# A list item starts with a bullet (• ● ▪ ■ ◦ ○ ‣ ► ▸ ·), an asterisk, a hyphen, an en or em dash, or a
# symbol-font glyph that PDF text extraction maps to the private use area.
_BULLET = re.compile(
    r"^[*\-\u00b7\u2013\u2014\u2022\u2023\u25a0\u25aa\u25b8\u25ba\u25cb\u25cf\u25e6\uf000-\uf0ff]"
)
# The numbering of the Implementing Regulation (EU) 2024/2984 template: "Part I", "Teil I", the field
# numbers "A.1" and "I.01", and the fields 00 to 10 of the summary table ("01 Date of notification").
_TEMPLATE_NUMBERING = (
    r"(?:Part|PART|Teil|TEIL)\s+(?:[A-Z]|[IVX]{1,5}|\d{1,2})[.:)]?|[A-Z]\.\d{1,2}(?:\.\d{1,2})*\.?|0\d|10"
)
# Outline numbering, which headings and list items share: "1.", "5.2", "1)", "I.", "IV.", "A.".
_OUTLINE_NUMBERING = r"\d{1,2}(?:\.\d{1,2})*[.)]|\d{1,2}(?:\.\d{1,2})+|[A-Z]\.|[IVX]{1,5}\."
_NUMBERING = re.compile(rf"^(?:(?P<template>{_TEMPLATE_NUMBERING})|{_OUTLINE_NUMBERING})\s+")
# Words a title-case heading leaves in lower case: "Information about the Issuer", "Rechte und Pflichten".
# None of them ends a sentence or a heading ("... crypto-assets or their" runs on to "admission to trading").
_MINOR_WORD = re.compile(
    r"a|about|against|among|an|and|as|at|between|by|for|from|in|into|its|of|on|or|over|per|than|the|their|to"
    r"|under|via|with|within|without|am|auf|aus|bei|bzw|das|dem|den|der|des|die|ein|eine|einer|eines|für|im"
    r"|mit|nach|oder|sowie|über|und|von|vom|zu|zum|zur"
)
# Dashes and quotation marks around heading words: en dash, em dash, curly single and double quotes.
_DASHES = "-\u2013\u2014"
_QUOTES = "\"'\u2018\u2019\u201c\u201d"


@dataclass(frozen=True)
class DocumentSections:
    """The section texts of a DOCX or PDF draft and, apart from them, the text of its headings, its
    extracted text and the whole text of its file.

    Heading text is not section body, and some text sits in no section (before the first heading, or
    after a line that ends a section). Regime inference reads the extracted text (text): a heading such
    as "Reserve of Assets" may be the only place that names the regime. COMMON.LEI_CHECK_DIGITS reads
    the whole text of the file (document_text): for a PDF that is the extracted text, for a DOCX every w:t
    of the body and of the headers and footers (_docx_texts: the paragraphs of tables and text boxes, tracked
    insertions, content controls, text moved away under tracked changes and any w:t inside a tracked
    deletion included). The sections and the extracted text of a DOCX hold only the runs and hyperlinks
    directly in a body paragraph (python-docx's paragraph text). It also reads the same text without what a
    reader cannot see (shown_text: _docx_texts for a DOCX, _pdf_lines for a PDF), which is empty where it
    equals document_text.
    """

    sections: dict[str, str]
    headings: tuple[str, ...]
    text: str = ""
    document_text: str = ""
    shown_text: str = ""


def _words(text: str) -> list[str]:
    """The words of a line; a lone dash ("Part G \u2013 Information ...") is not a word."""
    return [word for word in text.split() if word.strip(_DASHES)]


def _max_words(text: str, marked: bool = False) -> int:
    """The word limit of a heading: 20 when it is numbered or marked (entirely bold or in capitals in a
    DOCX, set in a heading font in a PDF), 12 otherwise."""
    return _MAX_MARKED_HEADING_WORDS if marked or _NUMBERING.match(text) else _MAX_HEADING_WORDS


def _sentence_breaks(text: str) -> list[tuple[str, str]]:
    """_SENTENCE_BREAK.findall(text), in time linear in the length of text.

    findall tries a match at every letter of a word, and each try reads the word to its end before it
    fails, so a long run of letters took time in the square of its length (a line of 40 000 letters took
    18 s). A match runs to the end of the word it starts in, so a later letter of a word can start one only
    where the word's first letter can: the search starts at the first letter of a word only, except right
    after a match, which ends with the first letter of the next word, so findall goes on inside that word.
    """
    breaks: list[tuple[str, str]] = []
    position = 0
    while True:
        found = (_SENTENCE_BREAK.match(text, position) if position else None) or _WORD_SENTENCE_BREAK.search(
            text, position
        )
        if found is None:
            return breaks
        breaks.append((found.group(1), found.group(2)))
        position = found.end()


def _has_sentence_break(text: str) -> bool:
    return any(
        letter.isupper() and word.lower() not in _ABBREVIATIONS for word, letter in _sentence_breaks(text)
    )


def _is_label(text: str, max_words: int = _MAX_HEADING_WORDS) -> bool:
    """A short label rather than a sentence or a list item: few words, no sentence punctuation after a
    word and no leading bullet."""
    return (
        len(_words(text)) <= max_words
        and not _SENTENCE_END.search(text)
        and not _has_sentence_break(text)
        and not _BULLET.match(text)
    )


def _is_title_like(text: str) -> bool:
    """All capitals, or every word other than a short connective or an abbreviation starts with a capital."""
    words = [word.strip(f"()[]{_QUOTES},:;") for word in text.split()]
    words = [word for word in words if word[:1].isalpha()]
    if not words or not words[0][0].isupper():
        return False
    return all(
        not word.islower() or _MINOR_WORD.fullmatch(word) or word.rstrip(".") in _ABBREVIATIONS
        for word in words[1:]
    )


def _ends_sentence(line: str) -> bool:
    return bool(re.search(r"[.!?][\"')\]\u2019\u201d]*$", line))


def _runs_on(line: str) -> bool:
    """The sentence runs on into the next line: the line ends with a comma, a hyphenated word part or a
    connective such as "and", "the" or "die"."""
    if re.search(r"(?:,|\w-)$", line):
        return True
    last = line.split()[-1]
    return len(last) > 1 and (last.islower() or line.isupper()) and bool(_MINOR_WORD.fullmatch(last.lower()))


def _heading_shaped(text: str, marked: bool = False) -> bool:
    """A label within the word limit whose first letter after any numbering is a capital."""
    numbering = _NUMBERING.match(text)
    title = text[numbering.end() :] if numbering else text
    return _is_label(text, _max_words(text, marked)) and next((c for c in title if c.isalpha()), "").isupper()


def _template_kind(text: str) -> str | None:
    """How the template numbers a line: "part" for a part title ("Part F"), "field" for a field of a part
    ("F.1") and "summary" for a field of the summary table ("01"); None for other lines."""
    numbering = _NUMBERING.match(text)
    number = numbering.group("template") if numbering else None
    if number is None:
        return None
    if number[:4].lower() in ("part", "teil"):
        return "part"
    return "field" if "." in number else "summary"


def _outline_number(text: str) -> str | None:
    """The outline number a heading starts with, without its closing mark: "12" in "12. Information on
    risks" and "12.1" in "12.1 Market risk". None for other headings."""
    numbering = _NUMBERING.match(text)
    number = numbering.group().strip().rstrip(".)") if numbering else ""
    return number if re.fullmatch(r"\d{1,2}(?:\.\d{1,2})*", number) else None


def _numbered_below(number: str | None, opener_number: str | None) -> bool:
    """Whether a heading number extends the number of the heading that opened the section, as "12.1"
    and "12.1.3" extend "12"."""
    return number is not None and opener_number is not None and number.startswith(f"{opener_number}.")


# A heading that names one risk ("Market risk", "Smart contract risk", "Marktrisiko") rather than the
# risk section; the risk warning is a section of its own.
_ONE_RISK = re.compile(r"\brisk\b(?!\s+warning)|risiko\b", re.IGNORECASE)


def _sub_heading(text: str, number: str | None, opener_number: str | None, keys: list[str]) -> bool:
    """Whether the number or the words of a heading that names no section place it under the heading
    that opened the current section, whose keys are keys: "12.1" under "12.", or a heading that names
    one risk in the risk section."""
    return _numbered_below(number, opener_number) or ("risks" in keys and bool(_ONE_RISK.search(text)))


def _ends_section(
    kind: str | None,
    level: float | None,
    opener: str | None,
    section_level: float | None,
    *,
    label: bool = False,
    sub_heading: bool = False,
) -> bool:
    """Whether a heading that names no section ends the current section.

    kind is the template numbering of the heading (see _template_kind) and opener that of the heading
    that opened the current section. level and section_level rank the heading and the heading that
    opened the section: a larger value is a lower level (a smaller PDF font, a deeper DOCX outline level).
    label tells whether only bold type or capitals mark the heading: a DOCX paragraph without a Heading
    style or an outline level, or a PDF line in bold at the size of the body text. sub_heading tells
    whether its number or its words place it under the heading that opened the section (see _sub_heading).

    A part title always ends the section, and a field of a part never does, as it belongs to its part.
    A field of the summary table ends the section of the summary field before it. A label and a heading
    that its number or words place under the heading that opened the section stay in the section, as
    "Market risk" and "12.1 Market risk" do under "12. Information on risks". Any other heading, one with
    a Heading style, an outline level or a larger font, ends the section unless it ranks below the
    heading that opened it.
    """
    if kind == "part":
        return True
    if kind == "field":
        return False
    if kind == "summary":
        return opener == "summary"
    if label or sub_heading:
        return False
    return level is None or section_level is None or level <= section_level


def _opening_level(level: float | None, section_level: float | None, in_section: bool) -> float | None:
    """The level of the section a heading that names a section opens. in_section tells whether the
    heading names a section that is open: such a sub-heading ("Market Risks" under "Risk Factors") keeps
    the level of the heading that opened it. A heading that names another section has its own level, so
    a large cover title that names a section ("Crypto-Asset White Paper") sets no level for the headings
    after it."""
    if in_section and section_level is not None and (level is None or level > section_level):
        return section_level
    return level


def _opening_number(number: str | None, opener_number: str | None) -> str | None:
    """The outline number of the section a heading opens or ends: a heading numbered below the heading
    that opened the current section ("12.2 Technology risks" under "12.") keeps that heading's number."""
    return opener_number if _numbered_below(number, opener_number) else number


def _below_opener(
    kind: str | None,
    level: float | None,
    number: str | None,
    opener: str | None,
    section_level: float | None,
    opener_number: str | None,
) -> bool:
    """Whether a heading ranks below the heading that opened the current section: a field of the template
    in a section that a part or another field opened, a number that extends the opener's ("12.1" under
    "12."), or a lower level (a smaller heading font, a deeper outline level). The arguments are those of
    _ends_section, with the outline numbers of the heading and of the opener."""
    return (
        (kind == "field" and opener in ("part", "field"))
        or _numbered_below(number, opener_number)
        or (level is not None and section_level is not None and level > section_level)
    )


def _within_rights(keys: list[str], current_keys: list[str], below: bool) -> bool:
    """Whether a heading that names the redemption alone sits within the open rights section, below the
    heading that opened it (see _below_opener). The rights section then stays open with its level and
    opener, and its text from that heading on counts for the redemption too, as Part D of an ART white
    paper does in the numbered-field layout: Annex II Part D No. 9 and Annex III Part D No. 1 list the
    right of redemption among the rights of the holders."""
    return below and keys == ["redemption"] and "rights_and_obligations" in current_keys


def _field_answer(text: str, keys: list[str]) -> str:
    """The answer after the label of a numbered field on the same line, as pypdf reads a row of the
    summary table: "2 February 2026" in "01 Date of notification 2 February 2026"."""
    if _template_kind(text) not in ("field", "summary"):
        return ""
    ends = [
        match.end()
        for key in keys
        for pattern in SECTION_PATTERNS[key]
        if (match := re.search(pattern, text, re.IGNORECASE))
    ]
    return text[max(ends) :].strip() if ends else ""


@dataclass(frozen=True)
class _Line:
    """A non-empty text line and, where the PDF reports them, the font its letters are set in and where
    it sits on its page."""

    text: str
    size: float | None = None  # the size of its smallest letter, in points
    bold: bool = False  # every letter is set in a bold face
    page: int | None = None  # the page it is on, counted from 0
    y: float | None = None  # the height of its (last) baseline above the foot of the page, in points


_HEADING, _BODY, _BREAK = "heading", "body", "break"
# A list item in lower case after a heading: "a) Market risk", "(b) Liquidity risk", "iv. Custody risk".
# German abbreviations of single letters ("z. B.", "u. a.", "d. h.") continue a sentence instead.
_LIST_MARKER = re.compile(r"^\(?(?:[a-z]|[ivx]{1,4})[.)]\s(?![^\W\d_]\.)")


def _line_role(
    line: str,
    previous: str | None,
    previous_role: str | None,
    following: str | None,
    *,
    started: bool,
    styled: bool,
    previous_styled: bool,
    by_font: bool = False,
    paragraph: bool = False,
) -> str:
    """The role of a line that names a section: a heading, body text, or a break that ends the section.

    previous and following are the neighbouring lines (None at either end), previous_role is the role of
    previous, started tells whether a heading or break came before, and styled and previous_styled whether
    the line and the one before are set larger or bolder than the body text. by_font tells whether the
    draft sets its headings in a heading font and the font of this line is known. paragraph tells whether
    the line is the first line of a paragraph set in its font (see _starts_paragraph).
    """
    if not _heading_shaped(line, styled) or paragraph:
        return _BODY
    numbering = _NUMBERING.match(line)
    title = line[numbering.end() :] if numbering else line
    # The template's own part and field labels, sentence case included ("Part I: Information on risks").
    if numbering and numbering.group("template"):
        return _HEADING
    # A heading font marks a heading, whatever the lines around it, except in a numbered list set in that
    # font: after a numbered body line in a heading font, a numbered line is the next list item, or the
    # heading after an empty section, so it ends the section.
    if styled:
        if numbering and previous_role == _BODY and previous_styled and _NUMBERING.match(previous):
            return _BREAK
        return _HEADING
    title_like = _is_title_like(title)
    # A line ending with a colon is a lead-in, not a heading. In sentence case it stays in the current
    # section; in title case it may also be a heading written with a colon ("Risk Factors:"), so it ends
    # the section rather than handing that section to the one before.
    if line.endswith(":"):
        return _BREAK if title_like else _BODY
    # Running text stays in the current section: the line a lead-in introduces, and a line that a
    # sentence runs on into or out of. A list item in lower case ("a) Market risk") may follow a heading,
    # and so may an answer that the item does not apply ("n/a", "entfällt").
    if previous is not None and previous.endswith(":"):
        return _BODY
    continued = (
        following is not None
        and following[:1].islower()
        and not _LIST_MARKER.match(following)
        and not is_not_applicable(following)
    )
    if (previous_role == _BODY and _runs_on(previous)) or continued:
        return _BODY
    # A line that runs on into the next one is no heading, but it may be the first line of a wrapped
    # heading as well as of a paragraph, so it ends the section.
    if _runs_on(line):
        return _BREAK
    # In a capitals paragraph, a line after a long or unfinished capitals line is a wrapped line of it; a
    # long capitals line over more capitals may start one, or be a long title over one, so it ends the section.
    if line.isupper():
        if (
            previous_role == _BODY
            and previous.isupper()
            and not _ends_sentence(previous)
            and (len(_words(previous)) >= 8 or _runs_on(previous))
        ):
            return _BODY
        if following is not None and following.isupper() and len(_words(line)) >= 8:
            # Under a heading it starts the paragraph of that heading.
            return _BREAK if previous_role == _BODY else _BODY
    # After a numbered body line, a numbered line is the next list item. In title case it may also be the
    # heading after an empty section, so it ends the section.
    if numbering and previous_role == _BODY and _NUMBERING.match(previous):
        return _BREAK if title_like else _BODY
    finished = (
        not started
        or previous_role != _BODY
        or _ends_sentence(previous)
        or is_placeholder(previous)
        or is_not_applicable(previous)
    )
    if title_like and (not numbering or finished):
        # Where the draft sets its headings in a heading font, a line in the body font is no heading.
        return _BREAK if by_font else _HEADING
    # Shaped like a heading but in sentence case ("Risk factors"), or numbered after an unfinished line:
    # the text below is credited to no section rather than to the section before.
    return _BREAK


def _font(line: _Line) -> tuple[float, bool] | None:
    """The size, to a tenth of a point, and the weight of a line's font."""
    return None if line.size is None else (round(line.size, 1), line.bold)


def _body_font(lines: list[_Line]) -> tuple[float, bool] | None:
    """The font size and weight that most letters are set in."""
    letters: Counter[tuple[float, bool]] = Counter()
    for line in lines:
        font = _font(line)
        if font is not None:
            letters[font] += sum(char.isalpha() for char in line.text)
    return letters.most_common(1)[0][0] if letters else None


def _larger(line: _Line, body_font: tuple[float, bool] | None) -> bool:
    """Set at least 15 % larger than the body text."""
    return line.size is not None and body_font is not None and line.size >= body_font[0] * 1.15


def _styled(line: _Line, body_font: tuple[float, bool] | None) -> bool:
    """Set at least 15 % larger than the body text, or in bold where the body text is not."""
    if line.size is None or body_font is None:
        return False
    size, bold = body_font
    return _larger(line, body_font) or (line.bold and not bold and line.size >= size * 0.95)


# Wrapped lines of one paragraph sit at most this many times their font size apart. A heading right
# after another is set further down, by the space between paragraphs.
_LINE_SPACING = 1.75


def _joined(first: str, second: str) -> str:
    """Two lines of a wrapped heading as one line: "crypto-" and "assets" make "crypto-assets"."""
    return first + second if re.search(r"[^\W\d_]-$", first) else f"{first} {second}"


def _heights_hold(lines: list[_Line], body_font: tuple[float, bool] | None) -> bool:
    """Whether the heights pypdf reports place the lines where they are printed.

    The lines of a body paragraph sit 1 to 2.5 times their font size apart. pypdf scales the leading of
    the T* operator by the font size, so in a PDF laid out with T* the lines seem many times further apart.
    """
    gaps = [
        first.y - line.y
        for first, line in pairwise(lines)
        if first.page == line.page
        and first.y is not None
        and line.y is not None
        and first.y > line.y
        and _font(first) == _font(line) == body_font
    ]
    return body_font is None or not gaps or statistics.median(gaps) <= 2.5 * body_font[0]


# The first line of a heading that wraps without running on ("... From the Offeror or Person" over
# "Seeking Admission to Trading") fills most of the column: at least this share of a full line of body
# text, in characters scaled by the font sizes.
_FULL_LINE_SHARE = 0.6


def _full_line(lines: list[_Line], body_font: tuple[float, bool] | None) -> float | None:
    """The number of characters on a full line of body text: the upper quartile of the lengths of the
    lines in the body font, as the last line of a paragraph is shorter."""
    lengths = [len(line.text) for line in lines if body_font is not None and _font(line) == body_font]
    return statistics.quantiles(lengths, n=4)[2] if len(lengths) >= 2 else None


def _fills_line(line: _Line, full_line: float | None, body_font: tuple[float, bool] | None) -> bool:
    """Whether a line fills most of the column: at least 60 % of the characters of a full line of body
    text, scaled by the body size over the size of the line, as a larger font fits fewer on a line."""
    if line.size is None or full_line is None or body_font is None:
        return False
    return len(line.text) >= _FULL_LINE_SHARE * full_line * body_font[0] / line.size


def _next_line(first: _Line, line: _Line, heights: bool) -> bool:
    """Whether line can go on with the text of first: on the same page, not numbered, not a list item,
    and set one line spacing below first where the heights hold."""
    if (
        first.page != line.page
        or _NUMBERING.match(line.text)
        or _BULLET.match(line.text)
        or _LIST_MARKER.match(line.text)
    ):
        return False
    return not (
        heights
        and first.y is not None
        and line.y is not None
        and line.size is not None
        and not 0 < first.y - line.y <= _LINE_SPACING * line.size
    )


def _wraps(first: _Line, line: _Line, first_styled: bool, styled: bool, heights: bool, fills: bool) -> bool:
    """Whether line is the next line of the heading or label that first starts.

    A line in the same heading font, set one line spacing below (where the heights hold), is the next
    line of a wrapped heading where first does not end a sentence, the two lines together are still
    shaped like a heading, and first runs on or fills most of the column (fills, see _fills_line). Where
    a draft sets no space between paragraphs, a short heading is one line spacing above the paragraph or
    the heading after it, and these start something new. A line in the body font is the next line only
    where first runs on, line starts in lower case and the two lines together are a label that names a
    section ("08 Characteristics of the crypto-" and "asset"). A numbered line, a list item, and a line on
    another page or further down start something new.
    """
    if not _next_line(first, line, heights):
        return False
    joined = _joined(first.text, line.text)
    if first_styled or styled:
        return (
            first_styled
            and styled
            and _font(first) == _font(line)
            and not _ends_sentence(first.text)
            and _heading_shaped(joined, True)
            and (_runs_on(first.text) or fills)
        )
    return (
        _runs_on(first.text)
        and line.text[:1].islower()
        and _is_label(joined, _max_words(joined))
        and bool(match_heading_to_section(joined))
    )


def _starts_paragraph(line: _Line, following: _Line | None, fills: bool, heights: bool) -> bool:
    """Whether a line is the first line of a paragraph set in its font: it fills most of the column
    (fills, see _fills_line), and the line after it is in the same font, goes on with its text (see
    _next_line) and starts in lower case, as a sentence does that runs on ("... approved by any
    competent" over "authority in any Member State ..."). The lines of a heading that wraps are already
    joined into one (see _wraps), and a short heading over a lower-case line ("Risk Factors" over "and
    Mitigation Measures") does not fill the column, so it stays a heading."""
    return (
        fills
        and following is not None
        and _font(line) == _font(following)
        and following.text[:1].islower()
        and _next_line(line, following, heights)
    )


def _page_text(text: str) -> str:
    """The text of a line with its numbers left out, to compare page headers and footers across pages."""
    return " ".join(re.sub(r"\d+", " ", text).casefold().split())


def _running(lines: list[_Line]) -> list[bool]:
    """Whether each line is a running page header or footer: among the first or last two lines of its
    page, and with the same text, numbers aside, among the first or last two lines of another page."""
    pages: dict[int, list[int]] = {}
    for index, line in enumerate(lines):
        if line.page is not None:
            pages.setdefault(line.page, []).append(index)
    edges = {index for indices in pages.values() for index in (*indices[:2], *indices[-2:])}
    edge_pages: dict[str, set[int | None]] = {}
    for index in edges:
        edge_pages.setdefault(_page_text(lines[index].text), set()).add(lines[index].page)
    return [index in edges and len(edge_pages[_page_text(line.text)]) > 1 for index, line in enumerate(lines)]


def _merge_wrapped(
    lines: list[_Line], styled: list[bool], running: list[bool], fills: list[bool], heights: bool
) -> tuple[list[_Line], list[bool], list[bool], list[bool]]:
    """The lines with the lines of each wrapped heading merged into one, and whether each is styled, a
    running page header or footer, and ends with a line that fills most of the column (fills, see
    _fills_line). A running line is never merged."""
    merged: list[_Line] = []
    merged_styled: list[bool] = []
    merged_running: list[bool] = []
    # Whether the last line merged into each line fills most of the column.
    merged_fills: list[bool] = []
    for line, line_styled, line_running, line_fills in zip(lines, styled, running, fills, strict=True):
        if (
            merged
            and not line_running
            and not merged_running[-1]
            and _wraps(merged[-1], line, merged_styled[-1], line_styled, heights, merged_fills[-1])
        ):
            first = merged[-1]
            size = None if first.size is None or line.size is None else min(first.size, line.size)
            text = _joined(first.text, line.text)
            merged[-1] = _Line(text, size, first.bold and line.bold, line.page, line.y)
            merged_fills[-1] = line_fills
        else:
            merged.append(line)
            merged_styled.append(line_styled)
            merged_running.append(line_running)
            merged_fills.append(line_fills)
    return merged, merged_styled, merged_running, merged_fills


# The statement's first words as the answer of field 02 (Table 2) or I.02 (Table 4) of 2024/2984, where pypdf
# reads the field number, the label and the start of the answer as one line.
_STATEMENT_ANSWER = re.compile(
    r"\b(?:this\s+crypto-asset\s+white\s+paper|dieses\s+kryptowerte-whitepaper)\b", re.IGNORECASE
)


def _split_statement_fields(
    lines: list[_Line], styled: list[bool], running: list[bool], fills: list[bool]
) -> tuple[list[_Line], list[bool], list[bool], list[bool], set[int]]:
    """Split a summary-table line whose answer is the statement, such as "02 Statement in accordance with
    Article 6(3) of Regulation (EU) 2023/1114 This crypto-asset white paper has not been", into its label
    and the statement's first line. The statement is then routed as one that starts a line of its own,
    and its words ("crypto-asset") do not add a section to the label. Returns the lines, their flags and
    the indices of the statement lines split off."""
    result: tuple[list[_Line], list[bool], list[bool], list[bool]] = ([], [], [], [])
    starts: set[int] = set()
    for line, *flags in zip(lines, styled, running, fills, strict=True):
        answer = _STATEMENT_ANSWER.search(line.text)
        label = line.text[: answer.start()].rstrip() if answer else ""
        parts = [line]
        if (
            answer
            and _template_kind(line.text) in ("field", "summary")
            and "not_approved_statement" in match_heading_to_section(label)
        ):
            parts = [replace(line, text=label), replace(line, text=line.text[answer.start() :])]
            starts.add(len(result[0]) + 1)
        for part in parts:
            for values, value in zip(result, (part, *flags), strict=True):
                values.append(value)
    return (*result, starts)


def _line_sections(lines: list[_Line], statement: bool = False) -> DocumentSections:
    """The sections of a draft read line by line. With statement, the Art. 6(3) / Art. 51(3) statement is
    routed by its content to not_approved_statement (see statement_extent), as in the other loaders."""
    text = "\n".join(line.text for line in lines)
    body_font = _body_font(lines)
    styled = [_styled(line, body_font) for line in lines]
    full_line = _full_line(lines, body_font)
    fills = [_fills_line(line, full_line, body_font) for line in lines]
    heights = _heights_hold(lines, body_font)
    lines, styled, running, fills = _merge_wrapped(lines, styled, _running(lines), fills, heights)
    # The draft sets its headings in a heading font if at least two lines in one name a section.
    by_font = (
        sum(
            1
            for line, line_styled, line_running in zip(lines, styled, running, strict=True)
            if line_styled
            and not line_running
            and _heading_shaped(line.text, True)
            and match_heading_to_section(line.text)
        )
        >= 2
    )
    # Split after the heading-font count, which a statement in a heading font must not tip.
    statement_starts: set[int] = set()
    if statement:
        lines, styled, running, fills, statement_starts = _split_statement_fields(
            lines, styled, running, fills
        )
    # A running page header or footer is body text that is not read as context for the lines around it.
    content = [index for index, line_running in enumerate(running) if not line_running]
    following_index = dict(pairwise(content))
    sections: dict[str, list[str]] = {}
    headings: list[str] = []
    current_keys: list[str] = []
    # The template numbering, the outline number and the level of the heading that opened the current
    # section.
    opener: str | None = None
    opener_number: str | None = None
    section_level: float | None = None
    previous: str | None = None
    previous_role: str | None = None
    previous_styled = False
    line_texts = [line.text for line in lines]
    statement_end = 0
    statement_role = _BODY
    # The first and last two lines of each page, where a page header or footer sits (see _running).
    page_lines: dict[int, list[int]] = {}
    for position, page_line in enumerate(lines):
        if page_line.page is not None:
            page_lines.setdefault(page_line.page, []).append(position)
    page_edges = {i for indices in page_lines.values() for i in (*indices[:2], *indices[-2:])}
    line_counts = Counter(_page_text(page_line.text) for page_line in lines)

    def statement_heading(index: int, statement_line: _Line) -> bool:
        # A heading inside the statement's lines (see statement_extent): a template part or field title,
        # or a line shaped like a heading in a heading font other than the statement's own, since a
        # statement may be set in bold. Where the statement runs over a page break, a line at the edge
        # of the next page may be a page header that names the current part ("Part A ..."), not running
        # because it changes from page to page: one in the body font, one set smaller than the
        # statement, or one that repeats another line of the draft, as a header repeats its heading.
        line = lines[index]
        statement_font = _font(statement_line)
        if running[index]:
            return False
        later_page = line.page != statement_line.page
        smaller = (
            later_page
            and line.size is not None
            and statement_font is not None
            and round(line.size, 1) < statement_font[0]
        )
        page_header = (
            index in page_edges
            and later_page
            and (not styled[index] or line_counts[_page_text(line.text)] > 1)
        )
        if _template_kind(line.text) and _heading_shaped(line.text, styled[index]):
            return not (smaller or page_header)
        return (
            styled[index]
            and _font(line) != statement_font
            and _heading_shaped(line.text, True)
            and not page_header
        )

    for index, line in enumerate(lines):
        if statement and (
            index < statement_end or index in statement_starts or opens_statement(line_texts, index)
        ):
            if index >= statement_end:
                statement_end = statement_extent(
                    line_texts, index, partial(statement_heading, statement_line=line)
                )
                # A statement cut off before its first full stop ends at a line read as a heading, which
                # does not continue its sentence ("approved by the"). A statement that ends with a full
                # sentence may share its last line with the next sentence, which runs on as body text.
                cut = not _STATEMENT_SENTENCE_END.search(" ".join(line_texts[index:statement_end]))
                statement_role = _BREAK if cut else _BODY
            sections.setdefault("not_approved_statement", []).append(line.text)
            previous, previous_role, previous_styled = line.text, statement_role, styled[index]
            continue
        if running[index]:
            for key in current_keys:
                sections.setdefault(key, []).append(line.text)
            continue
        keys = match_heading_to_section(line.text)
        kind = _template_kind(line.text)
        number = _outline_number(line.text)
        # A larger heading font is a higher level.
        level = -round(line.size, 1) if styled[index] and line.size is not None else None
        following = lines[following_index[index]] if index in following_index else None
        # The first line of a paragraph set in a heading font, such as a bold risk warning, is body text.
        paragraph = styled[index] and _starts_paragraph(line, following, fills[index], heights)
        role = _BODY
        if keys:
            role = _line_role(
                line.text,
                previous,
                previous_role,
                following.text if following else None,
                started=bool(headings),
                styled=styled[index],
                previous_styled=previous_styled,
                by_font=by_font and line.size is not None,
                paragraph=paragraph,
            )
        elif (
            (styled[index] or kind)
            and not paragraph
            and _heading_shaped(line.text, styled[index])
            and _ends_section(
                kind,
                level,
                opener,
                section_level,
                label=styled[index] and not _larger(line, body_font),
                sub_heading=_sub_heading(line.text, number, opener_number, current_keys),
            )
        ):
            # A heading that names no section, such as "Glossary" in a larger heading font.
            role = _BREAK
        if role == _BODY:
            for key in current_keys:
                sections.setdefault(key, []).append(line.text)
        else:
            headings.append(line.text)
            below = _below_opener(kind, level, number, opener, section_level, opener_number)
            if role == _HEADING and _within_rights(keys, current_keys, below):
                current_keys = [*current_keys, *(key for key in keys if key not in current_keys)]
            elif role == _HEADING:
                section_level = _opening_level(level, section_level, bool(set(keys) & set(current_keys)))
                current_keys = keys
                opener, opener_number = kind, _opening_number(number, opener_number)
            else:
                section_level = level
                current_keys = []
                opener, opener_number = kind, _opening_number(number, opener_number)
            answer = _field_answer(line.text, keys) if role == _HEADING else ""
            for key in current_keys if answer else ():
                sections.setdefault(key, []).append(answer)
        previous, previous_role, previous_styled = line.text, role, styled[index]
    return DocumentSections({k: "\n".join(v) for k, v in sections.items()}, tuple(headings), text, text)


def sections_from_lines(lines: Iterable[str]) -> dict[str, str]:
    """Group plain text lines, such as the extracted text of a PDF, under the section headings among them.

    Without font information a heading is recognised by its shape alone (see _line_role).
    """
    return _line_sections([_Line(line.strip()) for line in lines if line.strip()]).sections


def _style_chain(style):
    """The style and the styles it is based on, stopping where a malformed document loops back.

    A numbering (list) style has no base style in python-docx, so the chain ends there.
    """
    seen = set()
    while style is not None and style.element not in seen:
        seen.add(style.element)
        yield style
        style = getattr(style, "base_style", None)


def _outline_level(ppr) -> int | None:
    """The w:outlineLvl of a paragraph or style: 0 to 8 are heading levels 1 to 9, 9 is body text."""
    from docx.oxml.ns import qn

    level = ppr.find(qn("w:outlineLvl")) if ppr is not None else None
    value = level.get(qn("w:val")) if level is not None else None
    return int(value) if value is not None and value.isdigit() else None


# A bold or capitals label without an outline level ranks below the headings of levels 1 to 9 (0 to 8).
_LABEL_LEVEL = 9


def _docx_heading_level(paragraph) -> int | None:
    """The outline level of a heading, 0 for a level 1 heading, from a Heading style or an outline level
    set on the paragraph or on the style it is based on. None for body text."""
    level = _outline_level(paragraph._p.pPr)
    if level is not None:
        return level if level < 9 else None
    for style in _style_chain(paragraph.style):
        name = style.name or ""
        if name.startswith("Heading"):
            number = name.removeprefix("Heading").strip()
            return int(number) - 1 if number.isdigit() and 1 <= int(number) <= 9 else 0
        level = _outline_level(style.element.pPr)
        if level is not None:
            return level if level < 9 else None
    return None


def _style_bold(style) -> bool | None:
    """The bold setting of the first style in the chain that sets one; a numbering style has no font."""
    fonts = (getattr(s, "font", None) for s in _style_chain(style))
    return next((font.bold for font in fonts if font is not None and font.bold is not None), None)


def _run_bold(run, paragraph_bold: bool) -> bool:
    """Direct formatting first, then the character style, then the paragraph style."""
    for bold in (run.bold, _style_bold(run.style)):
        if bold is not None:
            return bold
    return paragraph_bold


def _docx_fully_bold(paragraph) -> bool:
    """True if every letter after a leading number sits in a bold run, hyperlinks included, not just a
    bold lead-in label. A number typed in plain type before a bold title ("5." then "Risk Factors") counts."""
    from docx.text.hyperlink import Hyperlink

    paragraph_bold = bool(_style_bold(paragraph.style))
    runs = [
        run
        for item in paragraph.iter_inner_content()
        for run in (item.runs if isinstance(item, Hyperlink) else (item,))
    ]
    bold_letters: list[bool] = []
    for run in runs:
        letters = sum(char.isalpha() for char in run.text)
        if letters:
            bold_letters += [_run_bold(run, paragraph_bold)] * letters
    numbering = _NUMBERING.match(paragraph.text.lstrip())
    bold_letters = bold_letters[sum(char.isalpha() for char in numbering.group()) if numbering else 0 :]
    return bool(bold_letters) and all(bold_letters)


def _docx_label_heading(paragraph, text: str) -> bool:
    """A label of up to 20 words and under 200 characters that is entirely bold or in capitals."""
    return (
        len(text) < 10 * _MAX_MARKED_HEADING_WORDS
        and _is_label(text, _max_words(text, marked=True))
        and (text.isupper() or _docx_fully_bold(paragraph))
    )


def parse_docx(path: Path) -> DocumentSections:
    """Parse a DOCX file and group text paragraphs under identified section headings.

    A heading has a Heading style or an outline level, or is a short label that is entirely bold
    or in capitals. Heading text is not section body. A heading that names no section ends the
    current section unless it is a sub-heading of the heading that opened it (see _ends_section),
    and a sub-heading that names the redemption alone keeps the rights section open (see _within_rights).
    """
    try:
        import docx
    except ImportError as exc:
        raise SystemExit(
            "DOCX support requires the optional 'docx' extra: pip install micar-whitepaper-linter[docx]"
        ) from exc

    doc = docx.Document(path)
    sections: dict[str, list[str]] = {}
    headings: list[str] = []
    texts: list[str] = []
    current_keys: list[str] = []
    # The template numbering, the outline number and the outline level of the heading that opened the
    # current section.
    opener: str | None = None
    opener_number: str | None = None
    section_level: float | None = None
    paragraphs = [(para, para.text.strip()) for para in doc.paragraphs if para.text.strip()]
    paragraph_texts = [text for _, text in paragraphs]
    statement_end = 0

    for index, (para, text) in enumerate(paragraphs):
        texts.append(text)
        if index < statement_end or opens_statement(paragraph_texts, index):
            if index >= statement_end:
                # A heading as parse_docx reads one below: a Heading style, an outline level, or a label
                # that is entirely bold or in capitals. A label marked as the statement's first paragraph
                # is one of its lines, as a statement may be set in bold or capitals a paragraph per line.
                marks = (text.isupper(), _docx_fully_bold(para))
                statement_end = paragraph_statement_extent(
                    paragraph_texts,
                    index,
                    lambda i, marks=marks: (
                        _docx_heading_level(paragraphs[i][0]) is not None
                        or (
                            _docx_label_heading(*paragraphs[i])
                            and (paragraphs[i][1].isupper(), _docx_fully_bold(paragraphs[i][0])) != marks
                        )
                    ),
                )
            sections.setdefault("not_approved_statement", []).append(text)
            continue

        # The Title style names the white paper, not one of its sections.
        if para.style is not None and para.style.name == "Title":
            continue

        level = _docx_heading_level(para)
        if level is None and _docx_label_heading(para, text):
            level = _LABEL_LEVEL
        if level is None:
            for k in current_keys:
                sections.setdefault(k, []).append(text)
            continue

        headings.append(text)
        keys = match_heading_to_section(text)
        kind = _template_kind(text)
        number = _outline_number(text)
        if _within_rights(
            keys, current_keys, _below_opener(kind, level, number, opener, section_level, opener_number)
        ):
            current_keys = [*current_keys, *(key for key in keys if key not in current_keys)]
        elif keys:
            section_level = _opening_level(level, section_level, bool(set(keys) & set(current_keys)))
            current_keys, opener = keys, kind
            opener_number = _opening_number(number, opener_number)
        elif _ends_section(
            kind,
            level,
            opener,
            section_level,
            label=level == _LABEL_LEVEL,
            sub_heading=_sub_heading(text, number, opener_number, current_keys),
        ):
            current_keys, opener, section_level = [], kind, level
            opener_number = _opening_number(number, opener_number)

    document_text, shown_text = _docx_document_texts(doc)
    return DocumentSections(
        {k: "\n".join(v) for k, v in sections.items()},
        tuple(headings),
        "\n".join(texts),
        document_text,
        shown_text if shown_text != document_text else "",
    )


# A colour channel at least this bright (of 1) is white or nearly so, in a DOCX run colour and a PDF fill or
# stroke colour alike.
_WHITE = 0.95

# What hidden text that still takes up its room on the page leaves in the text as a reader sees it: a zero-width
# space. The LEI reading takes this format character for nothing between two groups, so the groups on either
# side read as a code split into groups ("9999SYNTH 0000ZZQ0263" as the page shows it), not as one code, and gaps
# side by side read as one.
_GAP = "\u200b"
# How a DOCX run is hidden (_DocxLook.run_hidden): not at all, left out of the page (w:vanish), or laid out but
# not seen (white, under 1 pt), which leaves a _GAP.
_LEFT_OUT, _NOT_SEEN = 1, 2


def _white_hex(value: str) -> bool:
    """Whether a DOCX colour value ("FFFFFF", "auto") is white or nearly so: each channel at least _WHITE."""
    if len(value) != 6:
        return False
    try:
        return all(int(value[i : i + 2], 16) >= _WHITE * 255 for i in (0, 2, 4))
    except ValueError:
        return False


# The theme colours of DrawingML (a:clrScheme) by the name WordprocessingML gives them, and the names that
# the document settings map (w:clrSchemeMapping, Word's defaults here) onto those.
_THEME_SLOTS = {
    "dark1": "dk1", "light1": "lt1", "dark2": "dk2", "light2": "lt2", "accent1": "accent1",
    "accent2": "accent2", "accent3": "accent3", "accent4": "accent4", "accent5": "accent5",
    "accent6": "accent6", "hyperlink": "hlink", "followedHyperlink": "folHlink",
}
_THEME_MAPPED = {"background1": "light1", "text1": "dark1", "background2": "light2", "text2": "dark2"}
# Word's default theme where a document has none: its light 1 is white and its dark 1 black.
_DEFAULT_THEME = {"dk1": "000000", "lt1": "FFFFFF"}


def _mixed(value: str, tint: str | None, shade: str | None) -> str:
    """A hex colour with a theme tint (mixed with white: FF keeps it, 00 makes it white) or a theme shade (mixed
    with black: FF keeps it, 00 makes it black) applied, each channel on its own."""
    try:
        channels = [int(value[i : i + 2], 16) for i in (0, 2, 4)]
        if tint is not None:
            share = int(tint, 16) / 255
            channels = [round(255 - (255 - c) * share) for c in channels]
        if shade is not None:
            share = int(shade, 16) / 255
            channels = [round(c * share) for c in channels]
    except ValueError:
        return value
    return "".join(f"{c:02X}" for c in channels)


class _DocxLook:
    """Whether a DOCX run can be seen.

    A run is hidden where w:vanish is on, where its font is under 1 pt or its characters are scaled to under
    1 pt wide (w:sz under 2 half-points, or w:sz times the character scale w:w under 2 half-points at 100 %;
    10 pt where no w:sz is set), or where its colour is white or nearly so (w:color, each channel at least
    _WHITE) and no background sits behind it: a highlight (w:highlight other than none and white), run
    shading or the shading of the table cell it stands in (w:shd: the fill of clear and patterned shading,
    the colour of solid shading, automatic standing for black there; nil, no fill and white or nearly white
    are no background), or, in a nested table, the shading of the cell around. A colour, fill or pattern
    colour that names a theme colour (w:themeColor, w:themeFill, with its tint or shade, see _mixed) takes
    it from the document's theme (light 1 is white and dark 1 black without one; a comment or processing
    instruction in its colour scheme is passed over). A run hidden by w:vanish is left out of the page; one
    too small or white is laid out but not seen, so it leaves a gap where it stands (_GAP).

    Each property counts as set on the run, else in its character style, else in its paragraph's style (the
    default paragraph style for a paragraph without one), else in the run properties of the table style of
    the table it stands in (the default table style for a table without one), else in the document
    defaults, each style with the styles it is based on. The table style counts after the paragraph style as
    well, and the run is hidden if either order hides it. w:vanish set in any style or in the defaults
    hides the run unless the run sets it off itself: Word toggles it, so a style that sets it off does not
    show the run, and two styles that set it on show it in Word but not here. A cell's shading is its own
    w:shd, else that of its table style; only a cell that has neither (no w:shd at all) shows the shading of
    the cell around a nested table, so a nested cell's own fill, white or nil included, is its background.
    The shading of a paragraph or a table, conditional table formatting (w:tblStylePr) and the page colour
    are not looked at, so white text there counts as hidden."""

    def __init__(self, doc) -> None:
        from docx.oxml.ns import qn

        self._qn = qn
        self._tags = {
            qn("w:vanish"): "vanish",
            qn("w:sz"): "size",
            qn("w:w"): "scale",
            qn("w:color"): "color",
            qn("w:highlight"): "highlight",
            qn("w:shd"): "shading",
        }
        self._theme = self._theme_colours(doc)
        styles = doc.styles.element
        # Each style's run properties, the style it is based on and, for a table style, its cell shading.
        self._styles: dict[str, tuple[dict[str, object], str | None, bool | None]] = {}
        self._default: dict[str, str | None] = {"paragraph": None, "table": None}
        for style in styles.iterchildren(qn("w:style")):
            style_id = style.get(qn("w:styleId"))
            if style_id is None:
                continue
            based_on = style.find(qn("w:basedOn"))
            shading = style.find(f"{qn('w:tcPr')}/{qn('w:shd')}")
            self._styles[style_id] = (
                self._properties(style.find(qn("w:rPr"))),
                based_on.get(qn("w:val")) if based_on is not None else None,
                self._background(shading) if shading is not None else None,
            )
            kind = style.get(qn("w:type"))
            # The last default style of a type is the default, as the standard has it.
            if kind in self._default and style.get(qn("w:default")) in ("1", "true", "on"):
                self._default[kind] = style_id
        defaults = styles.find(f"{qn('w:docDefaults')}/{qn('w:rPrDefault')}/{qn('w:rPr')}")
        self._defaults = self._properties(defaults)
        self._resolved: dict[str | None, tuple[dict[str, object], bool, bool | None]] = {None: ({}, False, None)}
        self._hidden: dict[tuple[object, ...], int] = {}

    def _theme_colours(self, doc) -> dict[str, str]:
        """The theme colours of a document by the names WordprocessingML gives them, as hex."""
        from docx.opc.constants import RELATIONSHIP_TYPE
        from docx.oxml import parse_xml

        colours = dict(_DEFAULT_THEME)
        try:
            scheme = parse_xml(doc.part.part_related_by(RELATIONSHIP_TYPE.THEME).blob).find(
                ".//{http://schemas.openxmlformats.org/drawingml/2006/main}clrScheme"
            )
        except Exception:
            scheme = None
        for slot in scheme if scheme is not None else ():
            # A comment or a processing instruction in the scheme is no colour.
            if not isinstance(slot.tag, str):
                continue
            name = slot.tag.rsplit("}", 1)[-1]
            for colour in slot:
                if not isinstance(colour.tag, str):
                    continue
                kind = colour.tag.rsplit("}", 1)[-1]
                value = colour.get("val") if kind == "srgbClr" else colour.get("lastClr") if kind == "sysClr" else None
                if kind == "sysClr" and value is None:
                    value = {"window": "FFFFFF", "windowText": "000000"}.get(colour.get("val", ""))
                if value is not None:
                    colours[name] = value
        mapping = dict(_THEME_MAPPED)
        with suppress(Exception):
            element = doc.settings.element.find(self._qn("w:clrSchemeMapping"))
            if element is not None:
                for name in mapping:
                    key = {"background1": "bg1", "text1": "t1", "background2": "bg2", "text2": "t2"}[name]
                    if (target := element.get(self._qn(f"w:{key}"))) in _THEME_SLOTS:
                        mapping[name] = target
        named = {name: colours[slot] for name, slot in _THEME_SLOTS.items() if slot in colours}
        named |= {name: named[target] for name, target in mapping.items() if target in named}
        return named

    def _colour(self, element, value: str, theme: str, tint: str, shade: str) -> str:
        """The colour an element's attributes give: the theme colour where one is named, else the value."""
        qn = self._qn
        if (name := element.get(qn(theme))) is not None and name in self._theme:
            return _mixed(self._theme[name], element.get(qn(tint)), element.get(qn(shade)))
        return element.get(qn(value), "")

    def _background(self, shading) -> bool:
        """Whether a w:shd puts a background behind text that is neither missing nor white (see the class)."""
        pattern = shading.get(self._qn("w:val"), "")
        if pattern == "nil":
            return False
        if pattern == "solid":
            colour = self._colour(shading, "w:color", "w:themeColor", "w:themeTint", "w:themeShade")
            return colour in ("", "auto") or not _white_hex(colour)
        fill = self._colour(shading, "w:fill", "w:themeFill", "w:themeFillTint", "w:themeFillShade")
        return fill not in ("", "auto") and not _white_hex(fill)

    def _properties(self, run_properties) -> dict[str, object]:
        """The properties of a w:rPr that can hide a run."""
        found: dict[str, object] = {}
        if run_properties is None:
            return found
        val = self._qn("w:val")
        for child in run_properties:
            name = self._tags.get(child.tag)
            if name == "vanish":
                found[name] = child.get(val, "true").lower() not in ("0", "false", "off")
            elif name in ("size", "scale"):
                with suppress(ValueError):
                    found[name] = int(child.get(val, "").removesuffix("%"))
            elif name == "color":
                found[name] = self._colour(child, "w:val", "w:themeColor", "w:themeTint", "w:themeShade")
            elif name == "highlight":
                found[name] = child.get(val, "none") not in ("none", "white")
            elif name == "shading":
                found[name] = self._background(child)
        return found

    def _style(self, style_id: str | None) -> tuple[dict[str, object], bool, bool | None]:
        """The run properties of a style and the styles it is based on (the style's own first, the chain
        stopping before a style it has passed), whether any of them sets w:vanish on, and the cell shading of
        the nearest that sets one.

        Every style on the chain is resolved once: the chain is walked up to a style resolved before, and
        resolved back down from there, so a long chain of styles each based on the one before takes linear
        time. A chain that comes back to a style on it (a cycle) is walked round twice from its end, so that
        each style of the cycle gets the walk that starts at it."""
        chain: list[str] = []
        position: dict[str, int] = {}
        current = style_id
        while current not in self._resolved and current not in position and current in self._styles:
            position[current] = len(chain)
            chain.append(current)
            current = self._styles[current][1]
        start = position.get(current, len(chain))
        resolved = self._resolved.get(current, ({}, False, None)) if start == len(chain) else ({}, False, None)
        for name in reversed(chain + chain[start:]):
            properties, _, shading = self._styles[name]
            resolved = (
                {**resolved[0], **properties},
                resolved[1] or bool(properties.get("vanish")),
                shading if shading is not None else resolved[2],
            )
            self._resolved[name] = resolved
        return self._resolved.setdefault(style_id, resolved)

    def paragraph_style(self, paragraph) -> str | None:
        """The style of a w:p: its w:pStyle, or the default paragraph style."""
        qn = self._qn
        style = paragraph.find(f"{qn('w:pPr')}/{qn('w:pStyle')}")
        return style.get(qn("w:val")) if style is not None else self._default["paragraph"]

    def table_style(self, table) -> str | None:
        """The style of a w:tbl: its w:tblStyle, or the default table style."""
        qn = self._qn
        style = table.find(f"{qn('w:tblPr')}/{qn('w:tblStyle')}")
        return style.get(qn("w:val")) if style is not None else self._default["table"]

    def cell_background(self, cell, table_style: str | None, around: bool) -> bool:
        """Whether a w:tc has a background behind its text (see the class); around is that of the cell around a
        nested table, which counts only where the cell and its table style set no shading."""
        qn = self._qn
        shading = cell.find(f"{qn('w:tcPr')}/{qn('w:shd')}")
        own = self._background(shading) if shading is not None else self._style(table_style)[2]
        return around if own is None else own

    def run_hidden(self, run, paragraph_style: str | None, table_style: str | None, background: bool) -> int:
        """Whether a w:r is hidden (see the class), in a paragraph of the style, in a table of the style or none,
        on a cell background or not: 0 where it is shown, _LEFT_OUT for w:vanish, else _NOT_SEEN."""
        qn = self._qn
        run_properties = run.find(qn("w:rPr"))
        character = run_properties.find(qn("w:rStyle")) if run_properties is not None else None
        character_style = character.get(qn("w:val")) if character is not None else None
        direct = self._properties(run_properties)
        key = (character_style, paragraph_style, table_style, background, *sorted(direct.items()))
        if (hidden := self._hidden.get(key)) is None:
            paragraph, paragraph_vanish, _ = self._style(paragraph_style)
            character_properties, character_vanish, _ = self._style(character_style)
            table, table_vanish, _ = self._style(table_style)
            if "vanish" in direct:
                vanish = bool(direct["vanish"])
            else:
                vanish = bool(self._defaults.get("vanish")) or paragraph_vanish or character_vanish or table_vanish
            if vanish:
                hidden = _LEFT_OUT
            elif any(
                self._unseen({**self._defaults, **first, **second, **character_properties, **direct}, background)
                for first, second in ((table, paragraph), (paragraph, table))
            ):
                hidden = _NOT_SEEN
            else:
                hidden = 0
            self._hidden[key] = hidden
        return hidden

    @staticmethod
    def _unseen(properties: dict[str, object], background: bool) -> bool:
        """Whether merged run properties make a run too small or white on no background."""
        size = properties.get("size", 20)
        scale = properties.get("scale", 100)
        if isinstance(size, int) and (size < 2 or (isinstance(scale, int) and size * scale < 200)):
            return True
        return (
            _white_hex(str(properties.get("color", "")))
            and not properties.get("highlight")
            and not properties.get("shading")
            and not background
        )

    def mark_hidden(self, paragraph) -> bool:
        """Whether the mark of a w:p is deleted, moved away or hidden (w:vanish on the mark itself), so that
        Word runs the paragraph on into the next one."""
        qn = self._qn
        mark = paragraph.find(f"{qn('w:pPr')}/{qn('w:rPr')}")
        if mark is None:
            return False
        if mark.find(qn("w:del")) is not None or mark.find(qn("w:moveFrom")) is not None:
            return True
        return bool(self._properties(mark).get("vanish"))


class _PlainLook:
    """A _DocxLook that finds every run shown, for a document whose look cannot be read (_docx_document_texts)."""

    def paragraph_style(self, paragraph) -> None:
        return None

    def table_style(self, table) -> None:
        return None

    def cell_background(self, cell, table_style: str | None, around: bool) -> bool:
        return False

    def run_hidden(self, run, paragraph_style: str | None, table_style: str | None, background: bool) -> int:
        return 0

    def mark_hidden(self, paragraph) -> bool:
        return False


def _docx_texts(element, look: _DocxLook | _PlainLook) -> tuple[str, str]:
    """The text of an element, a paragraph per line, and the same text as Word shows it with every tracked
    change accepted.

    The first is every w:t (tracked insertions, hyperlinks, content controls and the paragraphs of tables and
    text boxes included), tabs, line breaks and non-breaking hyphens. Deleted text as Word writes it
    (w:delText) and field codes are not read. Text moved away under tracked changes (a w:t inside w:moveFrom)
    and a w:t inside w:del, which Word does not show as the accepted text, are read too.

    The second leaves out what the first reads inside a w:del or a w:moveFrom and in a run that _DocxLook
    finds hidden (with everything in it, such as a text box), and runs a paragraph whose mark is deleted,
    moved away or hidden on into the next. A run that is laid out but not seen (_NOT_SEEN) leaves a _GAP in
    place of its text, as it still takes up its room on the line. What stays joins as Word shows it, so a code
    split between a run and a content control, a tracked insertion, a field result or a smart tag reads as
    one."""
    from docx.oxml.ns import qn
    from lxml import etree

    text, tab, breaks, hyphen, paragraph, run, removal, table, cell = (
        qn("w:t"),
        qn("w:tab"),
        (qn("w:br"), qn("w:cr")),
        qn("w:noBreakHyphen"),
        qn("w:p"),
        qn("w:r"),
        (qn("w:del"), qn("w:moveFrom")),
        qn("w:tbl"),
        qn("w:tc"),
    )
    parts: list[str] = []
    shown: list[str] = []
    # The open w:del and w:moveFrom elements and hidden runs, the style of each open paragraph and table,
    # whether each open cell has a background and whether each open run is hidden. gap: the open hidden run
    # that hides the rest is laid out but not seen, and has left no _GAP yet.
    unseen = 0
    gap = False
    styles: list[str | None] = []
    tables: list[str | None] = []
    backgrounds: list[bool] = []
    runs: list[bool] = []
    for event, node in etree.iterwalk(element, events=("start", "end")):
        tag = node.tag
        if event == "end":
            if tag == paragraph:
                styles.pop()
                parts.append("\n")
                if not unseen and not look.mark_hidden(node):
                    shown.append("\n")
            elif tag == run:
                unseen -= runs.pop()
                gap = gap and bool(unseen)
            elif tag in removal:
                unseen -= 1
            elif tag == table:
                tables.pop()
            elif tag == cell:
                backgrounds.pop()
            continue
        if tag == paragraph:
            styles.append(look.paragraph_style(node))
            continue
        if tag == table:
            tables.append(look.table_style(node))
            continue
        if tag == cell:
            around = bool(backgrounds) and backgrounds[-1]
            backgrounds.append(look.cell_background(node, tables[-1] if tables else None, around))
            continue
        if tag == run:
            hidden = 0 if unseen else look.run_hidden(
                node,
                styles[-1] if styles else None,
                tables[-1] if tables else None,
                bool(backgrounds) and backgrounds[-1],
            )
            runs.append(bool(hidden))
            unseen += bool(hidden)
            gap = gap or hidden == _NOT_SEEN
            continue
        if tag in removal:
            unseen += 1
            continue
        if tag == text:
            piece = node.text or ""
        elif tag == tab:
            piece = "\t"
        elif tag in breaks:
            piece = "\n"
        elif tag == hyphen:
            piece = "-"
        else:
            continue
        parts.append(piece)
        if not unseen:
            shown.append(piece)
        elif gap and piece:
            shown.append(_GAP)
            gap = False
    return "".join(parts), "".join(shown)


def _docx_document_texts(doc) -> tuple[str, str]:
    """The whole text of a DOCX, and the same text as Word shows it (_docx_texts): its body, then the headers
    and footers that each section defines.

    The text as Word shows it only ever adds issues. Where reading it fails for any reason, the whole text is
    read alone (with _PlainLook) and returned as both, so the file is read as it would be without it."""
    try:
        return _docx_document_texts_by(doc, _DocxLook(doc))
    except Exception:
        text, _ = _docx_document_texts_by(doc, _PlainLook())
        return text, text


def _docx_document_texts_by(doc, look: _DocxLook | _PlainLook) -> tuple[str, str]:
    """_docx_document_texts with the look given."""
    texts = [_docx_texts(doc.element.body, look)]
    for section in doc.sections:
        for part in (
            section.header,
            section.first_page_header,
            section.even_page_header,
            section.footer,
            section.first_page_footer,
            section.even_page_footer,
        ):
            # A part linked to the previous section's has no definition of its own.
            if not part.is_linked_to_previous:
                texts.append(_docx_texts(part._element, look))
    return "\n".join(text for text, _ in texts), "\n".join(shown for _, shown in texts)


def load_from_docx(path: Path) -> dict[str, str]:
    return parse_docx(path).sections


_BOLD_FACE = re.compile(r"bold|black|heavy|demi", re.I)


def _resolved(value):
    return value.get_object() if hasattr(value, "get_object") else value


def _bold_face(font) -> bool:
    """Bold by name ("Helvetica-Bold", "ABCDEF+Arial-BoldMT") or by a font weight of 600 or more."""
    if font is None:
        return False
    if _BOLD_FACE.search(str(font.get("/BaseFont", ""))):
        return True
    for face in (font, *(_resolved(d) for d in _resolved(font.get("/DescendantFonts")) or ())):
        weight = _resolved((_resolved(face.get("/FontDescriptor")) or {}).get("/FontWeight"))
        if isinstance(weight, int | float) and weight >= 600:
            return True
    return False


_RunStyle = tuple[float, bool, float]


def _font_style(cm, tm, font, size) -> _RunStyle | None:
    """The rendered size of a text run (its Tf size scaled by the text and graphics matrices), its weight
    and the height of its baseline on the page."""
    try:
        scale = math.hypot(tm[2] * cm[0] + tm[3] * cm[2], tm[2] * cm[1] + tm[3] * cm[3])
        y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
        return abs(float(size)) * scale, _bold_face(font), float(y)
    except Exception:
        return None


def _record_run(runs: list[tuple[str, _RunStyle | None]], text, cm, tm, font, size) -> None:
    runs.append((str(text), _font_style(cm, tm, font, size)))


_IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
# The text-showing operators, and the index of the string or array operand each shows.
_SHOWS_TEXT = {b"Tj": 0, b"TJ": 0, b"'": 0, b'"': 2}
# The device colour spaces, by the number of components that sets a colour in each.
_DEVICE_SPACES = {"/DeviceGray": 1, "/DeviceRGB": 3, "/DeviceCMYK": 4}


def _multiply(first, second) -> tuple[float, ...]:
    """The product of two PDF matrices [a b c d e f], first then second."""
    a, b, c, d, e, f = first
    g, h, i, j, k, m = second
    return (a * g + b * i, a * h + b * j, c * g + d * i, c * h + d * j, e * g + f * i + k, e * h + f * j + m)


def _ink_white(space: str, components: tuple[float, ...]) -> bool:
    """Whether a colour in a device colour space is white or nearly so: each grey or RGB component at least
    _WHITE, each CMYK component at most 1 - _WHITE. A colour in any other space is not."""
    if _DEVICE_SPACES.get(space) != len(components):
        return False
    if space == "/DeviceCMYK":
        return all(value <= 1 - _WHITE for value in components)
    return all(value >= _WHITE for value in components)


def _device_space(value) -> str:
    """The device colour space a colour space stands for: a device space itself, an ICC-based space by its
    number of components (/N), a calibrated grey or RGB space as /DeviceGray or /DeviceRGB; the family name of
    any other space."""
    value = _resolved(value)
    if isinstance(value, list) and value:
        family = str(_resolved(value[0]))
        if family == "/ICCBased" and len(value) > 1:
            components = _resolved(_resolved(value[1]).get("/N"))
            return {1: "/DeviceGray", 3: "/DeviceRGB", 4: "/DeviceCMYK"}.get(components, family)
        return {"/CalGray": "/DeviceGray", "/CalRGB": "/DeviceRGB"}.get(family, family)
    return str(value)


def _reference(value) -> tuple[int, int] | None:
    """The object number and generation of an indirect reference, or of the object it was read from."""
    reference = value if hasattr(value, "idnum") else getattr(value, "indirect_reference", None)
    return (reference.idnum, reference.generation) if hasattr(reference, "idnum") else None


class _OptionalContent:
    """Which optional content (layers) the default configuration of a PDF shows: an optional content group
    (/OCG) is off where the configuration's /OFF array names it, or where its /BaseState is /OFF and its /ON
    array does not name it; a membership dictionary (/OCMD) is shown as its visibility expression (/VE: /And,
    /Or, /Not) or else its policy (/P: /AllOn, /AnyOn by default, /AnyOff, /AllOff) over its groups (/OCGs)
    says. Anything else, and an expression nested deeper than _OC_DEPTH or read through more than
    _OC_BUDGET times, counts as shown. Each group, membership dictionary, /OCGs array (with its policy) and
    /VE expression is read once (_once), and each array inside a /VE expression once for each depth it is
    reached at (_sub_expression), also where many membership dictionaries share it, so content that names the
    same ones again and again takes linear time."""

    _OC_DEPTH = 32
    # The most groups and operators one membership dictionary is read through, so that expressions that share
    # arrays cannot take exponential time; beyond it the content counts as shown.
    _OC_BUDGET = 10_000

    def __init__(self, reader) -> None:
        self._budget = 0
        self._off: set[tuple[int, int]] = set()
        self._on: set[tuple[int, int]] = set()
        self._base_off = False
        # What has been read (_once), by what was read and how, with the object read, so that the identity of
        # a direct object stays its own.
        self._read: dict[tuple[object, str], tuple[object, bool]] = {}
        # The expressions read (_sub_expression), by what was read and the depth, with their operands read in
        # full so far.
        self._arrays: dict[tuple[object, int], tuple[object, list[int], list[bool], list[bool]]] = {}
        with suppress(Exception):
            config = _resolved(_resolved(_resolved(reader.trailer["/Root"]).get("/OCProperties")).get("/D"))
            self._base_off = str(config.get("/BaseState", "/ON")) == "/OFF"
            for key, found in (("/OFF", self._off), ("/ON", self._on)):
                for group in _resolved(config.get(key)) or ():
                    if (reference := _reference(group)) is not None:
                        found.add(reference)

    def shown(self, value, depth: int = 0) -> bool:
        """Whether content marked with this optional content group or membership dictionary is shown."""
        self._budget = self._OC_BUDGET
        try:
            return self._once(value, "", lambda target: self._shown_as(target, depth))
        except Exception:
            return True

    def _once(self, value, how: str, read: Callable[[object], bool]) -> bool:
        """read(value), read once for each object (an indirect object by its object number, a direct one by
        its identity) and how."""
        target = _resolved(value)
        reference = _reference(value)
        key = (reference if reference is not None else id(target), how)
        if key not in self._read:
            self._read[key] = (target, read(value))
        return self._read[key][1]

    def _group_shown(self, value) -> bool:
        reference = _reference(value)
        if reference is None:
            return True
        return reference not in self._off and (not self._base_off or reference in self._on)

    def _shown_as(self, value, depth: int) -> bool:
        target = _resolved(value)
        kind = str(target.get("/Type", "")) if hasattr(target, "get") else ""
        if kind != "/OCMD":
            return self._group_shown(value) if kind == "/OCG" else True
        if target.get("/VE") is not None:
            # Read from depth + 1 with the whole budget each time, so it reads the same each time.
            return self._once(target.get("/VE"), "/VE", lambda expression: self._expression(expression, depth + 1))
        policy = str(target.get("/P", "/AnyOn"))
        return self._once(target.get("/OCGs"), policy, lambda groups: self._policy(groups, policy))

    def _policy(self, value, policy: str) -> bool:
        groups = _resolved(value)
        groups = list(groups) if isinstance(groups, list) else [] if groups is None else [groups]
        states = [self._group_shown(group) for group in groups if _resolved(group) is not None]
        if not states:
            return True
        if policy == "/AllOn":
            return all(states)
        if policy == "/AnyOff":
            return not all(states)
        if policy == "/AllOff":
            return not any(states)
        return any(states)

    def _expression(self, value, depth: int) -> bool:
        """A visibility expression read from this depth, each group and operator it reads through taking one
        from the budget. An expression (an array) is read once for each depth (_sub_expression)."""
        self._budget -= 1
        if depth > self._OC_DEPTH or self._budget < 0:
            return True
        expression = _resolved(value)
        if not isinstance(expression, list):
            return self._group_shown(value)
        if not expression:
            return True
        return self._sub_expression(value, expression, depth)

    def _sub_expression(self, value, expression: list, depth: int) -> bool:
        """What an expression's operator (/Not, /And, /Or; any other counts as shown) gives for its operands,
        read in order, each taking from the budget what it takes; once the budget is spent, every operand
        left counts as shown, as reading it would give.

        An expression is read once for each depth (also where many membership dictionaries share it, as
        [/And 8 0 R] with 8 0 R a long array): the operands read in full are kept, in order, with the budget
        each took and the value of the operator so far, and a later reading takes as many of them as the
        budget left holds (a binary search) and reads on from there. So each operand is read in full once for
        each depth; beyond that, a reading reads in each array at most the one operand in which the budget
        runs out; and an expression reads as a reading from scratch would."""
        reference = _reference(value)
        key = (reference if reference is not None else id(expression), depth)
        if key not in self._arrays:
            # The expression (so that the identity of a direct one stays its own), the budget its first n
            # operands took, whether all and whether any of them are shown, and whether the first is.
            self._arrays[key] = (expression, [0], [True], [False])
        _, took, every, some = self._arrays[key]
        count = len(expression) - 1
        read = bisect_right(took, self._budget) - 1
        self._budget -= took[read]
        all_shown, any_shown = every[read], some[read]
        first = some[1] if read else True
        while read < count and self._budget >= 0:
            before = self._budget
            shown = self._expression(expression[read + 1], depth + 1)
            if read == len(took) - 1 and self._budget >= 0:
                took.append(took[-1] + before - self._budget)
                every.append(every[-1] and shown)
                some.append(some[-1] or shown)
            all_shown, any_shown = all_shown and shown, any_shown or shown
            first = shown if read == 0 else first
            read += 1
        operator = str(_resolved(expression[0]))
        if operator == "/Not":
            return not first if count else True
        if operator == "/And":
            return all_shown
        if operator == "/Or":
            return any_shown or read < count if count else True
        return True


class _Ink(NamedTuple):
    """The part of a PDF graphics state that decides whether text can be seen."""

    mode: int = 0
    size: float = 0.0
    scale: float = 1.0
    fill_space: str = "/DeviceGray"
    fill: tuple[float, ...] = (0.0,)
    stroke_space: str = "/DeviceGray"
    stroke: tuple[float, ...] = (0.0,)
    ctm: tuple[float, ...] = _IDENTITY


class _PdfInk:
    """Follows the graphics state of a PDF page through pypdf's operator visitors, to tell text that cannot be
    seen: drawn in text render mode 3 or 7 (invisible, or a clipping path only); painted only in white or
    nearly white (each colour the render mode paints: the fill for modes 0 and 4, the stroke for 1 and 5,
    both for 2 and 6; a colour set with g, rg or k and their stroke forms, or with sc or scn in a device
    colour space or one that stands for one, _device_space, named directly or through the /ColorSpace
    resources, see _ink_white); drawn with glyphs under 1 pt high or wide on the page (the Tf size, for the
    width times the horizontal scaling Tz, scaled by the text matrix, the current transformation matrix and
    the matrix of each form XObject it is drawn in; the height measured across the baseline); or inside
    marked content (BDC with the /OC tag) or a form XObject (its /OC entry) whose optional content the
    document's default configuration does not show (_OptionalContent).

    Text that is transparent, under other content, clipped away, off the page, in a pattern or in a colour
    space other than those is not told apart. An operator whose operands this cannot read (a number too large
    for a float among them) changes nothing here; where pypdf itself cannot read it, pypdf stops the
    extraction. A form XObject is drawn with the state saved and restored after it, also where its entries
    cannot be read (a /Matrix without six numbers leaves the matrix as it was), so nothing its content sets
    outlasts it. The visitors never raise: anything else that goes wrong sets failed, and from then on they do
    nothing, so pypdf's own reading goes on as without them. With hide, the text of each text-showing operator
    that cannot be seen is replaced by a _GAP before pypdf reads it (pypdf calls the visitor with the operands
    it then reads, and builds them afresh for each extraction), so the page's text leaves it out but keeps a
    gap where it takes up its room on the page."""

    def __init__(self, resources, hide: bool, optional: _OptionalContent) -> None:
        self.hide = hide
        self.hidden = False
        self.failed = False
        self._optional = optional
        self._state = _Ink()
        self._saved: list[_Ink] = []
        self._resources: list = [resources]
        # The marked content sequences open in the content being read, whether each is optional content
        # that is not shown, and how many of them are not shown.
        self._marked: list[bool] = []
        self._off = 0
        # For each XObject being drawn: the state, the stack, the marked content and the count of sequences
        # not shown to restore after it.
        self._forms: list[tuple[_Ink, list[_Ink], list[bool], int]] = []

    def before(self, operator: bytes, operands: list, cm, tm) -> None:
        if not self.failed:
            try:
                self._before(operator, operands, tm)
            except Exception:
                self.failed = True

    def after(self, operator: bytes, operands: list, cm, tm) -> None:
        if not self.failed:
            try:
                self._after(operator)
            except Exception:
                self.failed = True

    def _before(self, operator: bytes, operands: list, tm) -> None:
        if operator in (b"BDC", b"BMC"):
            off = False
            if operator == b"BDC":
                with suppress(Exception):
                    off = str(operands[0]) == "/OC" and not self._optional.shown(self._marked_content(operands[1]))
            self._marked.append(off)
            self._off += off
            return
        if operator == b"EMC":
            if self._marked:
                self._off -= self._marked.pop()
            return
        state = self._state
        try:
            if operator in _SHOWS_TEXT:
                if self._unseen(tm):
                    self.hidden = True
                    if self.hide:
                        from pypdf.generic import ArrayObject, TextStringObject

                        index = _SHOWS_TEXT[operator]
                        if index < len(operands):
                            gap = TextStringObject(_GAP)
                            operands[index] = ArrayObject([gap]) if operator == b"TJ" else gap
            elif operator == b"q":
                self._saved.append(state)
            elif operator == b"Q":
                if self._saved:
                    self._state = self._saved.pop()
            elif operator == b"cm":
                self._state = state._replace(ctm=_multiply(tuple(map(float, operands[:6])), state.ctm))
            elif operator == b"Tr":
                self._state = state._replace(mode=int(operands[0]))
            elif operator == b"Tf":
                self._state = state._replace(size=float(operands[1]))
            elif operator == b"Tz":
                self._state = state._replace(scale=float(operands[0]) / 100)
            elif operator in (b"g", b"rg", b"k", b"G", b"RG", b"K"):
                space = {1: "/DeviceGray", 3: "/DeviceRGB", 4: "/DeviceCMYK"}[len(operands)]
                self._paint(operator.islower(), space, tuple(map(float, operands)))
            elif operator in (b"cs", b"CS"):
                space = self._space(operands[0])
                initial = (0.0, 0.0, 0.0, 1.0) if space == "/DeviceCMYK" else (0.0,) * _DEVICE_SPACES.get(space, 1)
                self._paint(operator == b"cs", space, initial)
            elif operator in (b"sc", b"scn", b"SC", b"SCN"):
                fills = operator.islower()
                numbers = tuple(float(value) for value in operands if isinstance(value, int | float))
                # A pattern name among the operands paints a pattern, which is not white.
                self._paint(
                    fills,
                    state.fill_space if fills else state.stroke_space,
                    numbers if len(numbers) == len(operands) else (),
                )
            elif operator == b"Do":
                self._enter_form(operands[0])
        except Exception:
            # An operand this cannot read (a number too large for a float, a missing resource) leaves the state
            # as it was: each branch changes it only once it has read all it needs (Do saves the state first,
            # so that it is restored after the XObject, _enter_form).
            pass

    def _after(self, operator: bytes) -> None:
        if operator == b"Do" and self._forms:
            self._state, self._saved, self._marked, self._off = self._forms.pop()
            self._resources.pop()

    def _marked_content(self, properties):
        """The optional content a BDC names: its property list, inline or named in the /Properties resources."""
        if hasattr(properties, "keys"):
            return properties
        resources = _resolved(self._resources[-1]) or {}
        named = _resolved(resources.get("/Properties")) or {}
        return named.raw_get(properties) if hasattr(named, "raw_get") else named.get(properties)

    def _space(self, name) -> str:
        """The colour space a cs or CS operand names (_device_space), through the /ColorSpace resources."""
        name = str(name)
        if name in _DEVICE_SPACES or name == "/Pattern":
            return name
        resources = _resolved(self._resources[-1]) or {}
        spaces = _resolved(resources.get("/ColorSpace")) or {}
        value = spaces.get(name)
        return name if value is None else _device_space(value)

    def _paint(self, fills: bool, space: str, components: tuple[float, ...]) -> None:
        if fills:
            self._state = self._state._replace(fill_space=space, fill=components)
        else:
            self._state = self._state._replace(stroke_space=space, stroke=components)

    def _enter_form(self, name) -> None:
        """Before an XObject: the state is saved first, before anything of the XObject is read, so that after
        it the state is restored whatever its content set, also where its entries cannot be read (an image
        draws no content, and leaves the state as it was). A form's content draws with its own resources and
        matrix, and is not shown where its optional content is not. An entry that cannot be read changes
        nothing for its content: resources that cannot be read are those of the content around it, and a
        matrix without six numbers leaves the matrix as it was."""
        self._forms.append((self._state, self._saved, self._marked, self._off))
        self._saved = []
        self._marked = []
        outer = self._resources[-1]
        self._resources.append(outer)
        resources = _resolved(outer) or {}
        xobject = _resolved(_resolved(resources.get("/XObject")).get(name))
        self._resources[-1] = xobject.get("/Resources") or outer
        off = xobject.get("/OC") is not None and not self._optional.shown(xobject.raw_get("/OC"))
        self._marked = [off]
        self._off += off
        matrix = _resolved(xobject.get("/Matrix")) or _IDENTITY
        # A matrix without six numbers cannot be read, and is not read any further.
        if len(matrix) != len(_IDENTITY):
            raise ValueError("a form matrix holds six numbers")
        self._state = self._state._replace(ctm=_multiply(tuple(map(float, matrix)), self._state.ctm))

    def _unseen(self, tm) -> bool:
        state = self._state
        if self._off or state.mode in (3, 7):
            return True
        a, b, c, d, _, _ = _multiply(tuple(map(float, tm)), state.ctm)
        along = math.hypot(a, b)
        # The glyphs' width along the baseline and their height across it.
        if abs(state.size * state.scale) * along < 1 or abs(state.size) * abs(a * d - b * c) < along:
            return True
        painted = []
        if state.mode in (0, 2, 4, 6):
            painted.append(_ink_white(state.fill_space, state.fill))
        if state.mode in (1, 2, 5, 6):
            painted.append(_ink_white(state.stroke_space, state.stroke))
        return bool(painted) and all(painted)


# Whitespace and gaps at either end of a line.
_LINE_EDGES = re.compile(rf"^[\s{_GAP}]+|[\s{_GAP}]+$")


def _shown_lines(text: str) -> list[str]:
    """The lines of a page's text as shown, without whitespace and gaps (_GAP) at either end; a line of only
    those is left out, as an empty one is."""
    return [line for raw in text.splitlines() if (line := _LINE_EDGES.sub("", raw))]


def _page_resources(page):
    """The resources of a page, its own or those it inherits from the page tree; None where a /Parent is no
    dictionary."""
    node = page
    for _ in range(64):
        if not isinstance(node, dict):
            break
        if "/Resources" in node:
            return node["/Resources"]
        node = _resolved(node.get("/Parent"))
    return None


def _pdf_lines(reader) -> tuple[list[_Line], str]:
    """The non-empty text lines of a PDF, with the font and height of each where pypdf reports them, and the
    same text without what cannot be seen (_PdfInk), or "" where nothing on any page is hidden.

    The text visitor of pypdf reports each run of text with its font and position. Where the runs do not
    add up to the extracted page text (form XObjects, right-to-left text), that page goes by line shape
    alone. A page that draws text that cannot be seen is read a second time, without that text.

    The text without what cannot be seen only ever adds issues. Where reading it fails for any reason (a
    visitor fails, or the second reading raises), it is dropped for the whole file and the pages that follow
    are read without the visitors, so the file is read as it would be without it.
    """
    lines: list[_Line] = []
    shown: list[str] = []
    any_hidden = failed = False
    optional = _OptionalContent(reader)
    for number, page in enumerate(reader.pages):
        runs: list[tuple[str, _RunStyle | None]] = []
        ink = None
        if not failed:
            try:
                ink = _PdfInk(_page_resources(page), False, optional)
            except Exception:
                failed = True
        visitors = {} if ink is None else {"visitor_operand_before": ink.before, "visitor_operand_after": ink.after}
        text = page.extract_text(visitor_text=partial(_record_run, runs), **visitors) or ""
        failed = ink is None or ink.failed
        if not failed and ink is not None:
            try:
                if ink.hidden:
                    any_hidden = True
                    hiding = _PdfInk(_page_resources(page), True, optional)
                    page_shown = (
                        page.extract_text(visitor_operand_before=hiding.before, visitor_operand_after=hiding.after)
                        or ""
                    )
                    failed = hiding.failed
                    shown.extend(_shown_lines(page_shown))
                else:
                    shown.extend(raw.strip() for raw in text.splitlines() if raw.strip())
            except Exception:
                failed = True
        styles = (
            [style for run, style in runs for _ in run] if "".join(run for run, _ in runs) == text else []
        )
        end = 0
        for raw in text.splitlines(keepends=True):
            start, end = end, end + len(raw)
            if not raw.strip():
                continue
            letters = [styles[i] for i in range(start, end) if text[i].isalpha()] if styles else []
            if letters and None not in letters:
                size = min(style[0] for style in letters)
                bold = all(style[1] for style in letters)
                lines.append(_Line(raw.strip(), size, bold, number, letters[0][2]))
            else:
                lines.append(_Line(raw.strip(), page=number))
    return lines, "\n".join(shown) if any_hidden and not failed else ""


def parse_pdf(path: Path) -> DocumentSections:
    """Parse a PDF file and extract text grouped under identified section headings.

    A heading is a line that names a section and is set larger or bolder than the body text, or is
    shaped like a heading (see _line_role); where the draft sets its headings in a heading font, a line
    in the body font is a heading only if numbered as in the template. A short line that names a section
    but is not accepted as a heading ends the current section, and so does a heading that names no
    section unless it is a sub-heading (see _ends_section). A sub-heading that names the redemption alone
    keeps the rights section open (see _within_rights). A running page header or footer is body text.
    Heading text is not section body.
    """
    try:
        import pypdf
    except ImportError as exc:
        raise SystemExit(
            "PDF support requires the optional 'pdf' extra: pip install micar-whitepaper-linter[pdf]"
        ) from exc

    lines, shown_text = _pdf_lines(pypdf.PdfReader(path))
    return replace(_line_sections(lines, statement=True), shown_text=shown_text)


def load_from_pdf(path: Path) -> dict[str, str]:
    return parse_pdf(path).sections


def load_from_markdown(path: Path) -> dict[str, str]:
    """Parse a Markdown file and extract text grouped under identified section headings."""
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as exc:
        raise SystemExit(f"Error reading Markdown file {path}: {exc}") from exc

    sections: dict[str, list[str]] = {}
    current_keys = []
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    statement_end = 0

    for index, line_clean in enumerate(lines):
        if index < statement_end or opens_statement(lines, index):
            if index >= statement_end:
                statement_end = statement_extent(lines, index)
            sections.setdefault("not_approved_statement", []).append(line_clean)
            continue

        # Detect Markdown headings (e.g. # Heading 1, ## Heading 2)
        heading_match = re.match(r"^#{1,6}\s+(.+)$", line_clean)
        if heading_match:
            heading_text = heading_match.group(1).strip()
            matched_keys = match_heading_to_section(heading_text)
            # Reset current_keys if it's a heading, so we don't leak text into unrelated sections
            current_keys = matched_keys
        else:
            if current_keys:
                for k in current_keys:
                    sections.setdefault(k, []).append(line_clean)

    return {k: "\n".join(v) for k, v in sections.items()}
