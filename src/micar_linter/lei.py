"""Legal Entity Identifier (LEI) checks: format, check digits and consistency.

An LEI is 20 characters (ISO 17442): 18 upper-case letters or digits followed by
two check digits under ISO/IEC 7064 MOD 97-10. The check is offline and never
asks a registry whether an LEI exists or belongs to the named entity, so a pass
says only that the characters are internally consistent. A code that an LEI label introduces but
that does not have that shape is malformed (malformed_leis).
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from functools import lru_cache

# 18 alphanumerics and 2 digits, not part of a longer code.
_LEI_SHAPE = re.compile(r"(?<![A-Z0-9])[A-Z0-9]{18}[0-9]{2}(?![A-Z0-9])")
# A purely numeric 20-digit run (an account or reference number) counts only right after an LEI
# label, with at most two short words between them ("LEI: ...", "the LEI is ...", "LEI code ..."), or as
# the code an LEI label introduces (_labelled_codes below).
_LEI_LABEL = re.compile(
    r"\b(?:LEI|legal\s+entity\s+identifier|Rechtstr(?:ä|ae)gerkennung)\W*(?:[^\W\d_]{1,12}\W+){0,2}$",
    re.IGNORECASE,
)
_LABEL_WINDOW = 60

# An LEI label introduces a code: the acronym in capitals (lower-case "lei" is a Romanian word, the plural of
# the currency "leu") or the English or German name in any case, whose words a PDF may wrap onto two lines.
# The code is the first run of letters and digits that holds a digit and, with any groups that follow it after
# a single space or hyphen, has at least _MIN_CODE_LENGTH of them. At most _MAX_LABEL_WORDS other words may
# stand between label and code ("The LEI of the offeror is ...", "Legal Entity Identifier (LEI), synthetic and
# not registered, is ..."), with no sentence end; the full stop of "e.g." or "i.e.", and of "No." or "Nr."
# before a word with a digit ("LEI No. ..."), ends no sentence. A shorter number on the way, such as a
# year or "ISO 17442", counts as one of those words. The search runs on over line ends, since a PDF wraps its
# lines inside a sentence, but not into a line that starts a field of the numbered layout ("Contact telephone
# number: ...", "A.8 ...") or a list item, so the next field is never read as the code of a label answered in
# words. A further code joined to a labelled code, or to an LEI-shaped code that holds a letter, by a comma,
# "and", "or", "und" or "oder" is read too ("LEIs: ... and ...").
_LABEL = re.compile(r"\bLEIs?\b|(?i:\blegal\s+entity\s+identifiers?\b|\bRechtstr(?:ä|ae)gerkennung(?:en)?\b)")
_WORD = re.compile(r"[^\W_]+")
_GAP_SENTENCE_END = re.compile(r"[.!?;](?=\s)")
# The full stop of an abbreviation, always ("e.g.") or before a word with a digit ("No. 9999 ...").
_ABBREVIATION = re.compile(r"(?<![^\W_])(?:e\.g|i\.e)\.\Z", re.IGNORECASE)
_NUMBER_ABBREVIATION = re.compile(r"(?<![^\W_])(?:No|Nos|Nr|Nrn)\.\Z", re.IGNORECASE)
_DIGIT_WORD = re.compile(r"\s+[^\W_]*\d")
# The start of a line that opens a field or a list item: a field number of Implementing Regulation (EU)
# 2024/2984 ("A.8", "08") before a capital, a label of up to twelve words of letters in front of a colon
# ("Contact telephone number:"), or a bullet.
_FIELD_WORD = r"(?:[^\W\d_]|[-'\u2019()/])+"
_FIELD_LINE = re.compile(
    r"\s*(?:(?:[A-Z]\.\d{1,2}(?:\.\d{1,2})*\.?|0\d|10)[^\S\n]+[A-ZÄÖÜ]"
    rf"|[A-ZÄÖÜ]{_FIELD_WORD}?(?:[^\S\n]+{_FIELD_WORD}){{0,11}}:(?!\S)"
    r"|[*\u00b7\u2013\u2014\u2022\u25aa\u25cf\u25e6-][^\S\n])"
)
# A group that continues a code after a single space or hyphen: one with a digit, or capitals only, as in
# "9999 SYNT H000 0ZZQ 0263". Joining stops at _MAX_CODE_SPAN characters, well past the 24 of an LEI in
# groups of four, so a long run of such groups costs no more than one code.
_CODE_GROUP = re.compile(r"[ -](?:[A-Za-z0-9]*[0-9][A-Za-z0-9]*|[A-Z]+)(?![^\W_])")
_MAX_CODE_SPAN = 32
_JOINER = re.compile(r"[^\S\n]*,\s*(?:(?:and|or|und|oder)\s+)?|\s+(?:and|or|und|oder)\s+")
_MAX_LABEL_WORDS = 6
_MIN_CODE_LENGTH = 10

# Sections that name the parties to the white paper.
PARTY_SECTIONS = ("issuer", "offeror", "trading_platform_operator")

# The template of Implementing Regulation (EU) 2024/2984 also asks for the LEI of persons other than the
# parties: the crypto-asset service provider in charge of the placing (Table 2 field E.31, Table 3 C.22,
# "CASP identifier" or "CASP-Kennung"), the custodian of the reserve assets (Table 3 G.8, "Custodian service
# providers" or "Verwahrer"), and persons other than the issuer who offer the token, seek its admission to
# trading or draw up the white paper (Table 3 AA.1 and AA.3, Table 4 A.27). These are the roles' words in the
# English and German field names, and as a draft writes them in prose.
_OTHER_PERSON = re.compile(
    r"\bCASP\b|\bcrypto-asset service provider|\bKryptowerte-Dienstleist|\bcustod(?:ian|y)|\bverwahr"
    r"|\bother than the issuer\b|\bother persons? drawing up\b"
    r"|\bnicht mit dem Emittenten identisch|\bandere Personen, die das Kryptowerte-Whitepaper\b",
    re.IGNORECASE,
)
# A sentence ends at a full stop, question mark, exclamation mark or semicolon before a capital letter, so
# "Example CASP S.A., LEI ..." and "the custodian under Art. 37 MiCAR" stay one sentence. A line ends a field
# of the numbered layout.
_SENTENCE_END = re.compile(r"[.!?;](?=\s+[A-ZÄÖÜ])|\n")


def has_valid_check_digits(lei: str) -> bool:
    """ISO/IEC 7064 MOD 97-10: letters A..Z become 10..35 and the number mod 97 must be 1."""
    if not re.fullmatch(r"[A-Z0-9]{18}[0-9]{2}", lei):
        return False
    return int("".join(str(int(char, 36)) for char in lei)) % 97 == 1


def check_digits_for(base: str) -> str:
    """The two check digits that complete an 18-character base (used for synthetic fixtures)."""
    if not re.fullmatch(r"[A-Z0-9]{18}", base):
        raise ValueError("an LEI base is 18 upper-case letters or digits")
    remainder = int("".join(str(int(char, 36)) for char in base + "00")) % 97
    return f"{98 - remainder:02d}"


def _code_span(text: str, word: re.Match[str]) -> tuple[int, int] | None:
    """The span of the code that starts at a word, or None if the word does not start one."""
    token = word.group(0)
    if not (token.isascii() and any(char.isdigit() for char in token)):
        return None
    # A well-formed LEI stands alone, so the name of a legal form after it ("... 0166 AG") is not joined.
    if _LEI_SHAPE.fullmatch(token):
        return word.span()
    end = word.end()
    while end - word.start() < _MAX_CODE_SPAN and (group := _CODE_GROUP.match(text, end)):
        end = group.end()
    if sum(char.isalnum() for char in text[word.start() : end]) < _MIN_CODE_LENGTH:
        return None
    return word.start(), end


def _ends_reach(text: str, start: int, end: int) -> bool:
    """Whether the text between two words ends a label's reach: a sentence end other than the full stop of
    an abbreviation, or a line end before a line that opens a field or a list item."""
    for mark in _GAP_SENTENCE_END.finditer(text, start, end):
        if mark.group(0) != ".":
            return True
        window = max(0, mark.start() - 5)
        if _ABBREVIATION.search(text, window, mark.end()):
            continue
        if _NUMBER_ABBREVIATION.search(text, window, mark.end()) and _DIGIT_WORD.match(text, mark.end()):
            continue
        return True
    line_end = text.find("\n", start, end)
    while line_end != -1:
        if _FIELD_LINE.match(text, line_end + 1):
            return True
        line_end = text.find("\n", line_end + 1, end)
    return False


def _first_code(text: str, start: int) -> tuple[int, int] | None:
    """The span of the code that the label ending at start introduces, if any."""
    position = start
    for words, word in enumerate(_WORD.finditer(text, start)):
        if words > _MAX_LABEL_WORDS or _ends_reach(text, position, word.start()):
            return None
        span = _code_span(text, word)
        if span is not None:
            return span
        position = word.end()
    return None


@lru_cache(maxsize=64)
def _labelled_codes(text: str) -> tuple[tuple[int, int], ...]:
    """The spans of the codes that LEI labels introduce, and of the codes joined to them or to an LEI-shaped
    code with a letter, in order, without duplicates."""
    starts = {span for label in _LABEL.finditer(text) if (span := _first_code(text, label.end()))}
    starts.update(match.span() for match in _LEI_SHAPE.finditer(text) if not match.group(0).isdigit())
    spans: dict[tuple[int, int], None] = {}
    for span in sorted(starts):
        if span in spans:
            continue
        spans[span] = None
        # Each code's joined codes are read once: a code seen before has had its own read.
        while (joiner := _JOINER.match(text, span[1])) and (word := _WORD.match(text, joiner.end())):
            joined = _code_span(text, word)
            if joined is None or joined in spans:
                break
            spans[joined] = None
            span = joined
    return tuple(sorted(spans))


def _lei_matches(text: str) -> Iterator[re.Match[str]]:
    """Every LEI-shaped code in a text, in order; a purely numeric one only after an LEI label."""
    labelled = set(_labelled_codes(text))
    for match in _LEI_SHAPE.finditer(text):
        if match.group(0).isdigit() and match.span() not in labelled:
            window = text[max(0, match.start() - _LABEL_WINDOW) : match.start()]
            if not _LEI_LABEL.search(window):
                continue
        yield match


def find_leis(text: str) -> tuple[str, ...]:
    """LEI-shaped codes in a text, in order of first appearance, without duplicates."""
    return tuple(dict.fromkeys(match.group(0) for match in _lei_matches(text)))


def malformed_leis(text: str) -> tuple[str, ...]:
    """Codes that an LEI label introduces but that are not LEI-shaped, as written, without duplicates.

    That is a code of the wrong length, in lower case, with a letter where a check digit belongs, or split
    into groups by spaces or hyphens. COMMON.LEI_CHECK_DIGITS sends such a code to Review, so that a typo
    next to a valid LEI cannot pass.
    """
    codes = (text[start:end] for start, end in _labelled_codes(text))
    return tuple(dict.fromkeys(code for code in codes if not _LEI_SHAPE.fullmatch(code)))


def other_person_leis(text: str) -> tuple[str, ...]:
    """LEI-shaped codes that the text gives for a person other than the parties, without duplicates.

    That is the provider in charge of the placing, a custodian, or a person other than the issuer who
    offers the token, seeks its admission to trading or draws up the white paper. The role must be named
    before the code in its own sentence or line, with no other code in between: a template label ("CASP
    identifier: ...") or a sentence such as "The crypto-asset service provider in charge of the placing has
    the LEI ...". A role named in an earlier sentence does not carry over.
    """
    found: list[str] = []
    start = 0
    for match in _lei_matches(text):
        context = _last_sentence(text[start : match.start()])
        if _OTHER_PERSON.search(context) and match.group(0) not in found:
            found.append(match.group(0))
        start = match.end()
    return tuple(found)


def _last_sentence(text: str) -> str:
    """The text after the last sentence or line end."""
    ends = list(_SENTENCE_END.finditer(text))
    return text[ends[-1].end() :] if ends else text


def leis_by_section(sections: dict[str, str]) -> dict[str, tuple[str, ...]]:
    """LEI-shaped codes per section key, for sections that contain any, in draft order."""
    return {key: codes for key, text in sections.items() if (codes := find_leis(str(text)))}


def malformed_leis_by_section(sections: dict[str, str]) -> dict[str, tuple[str, ...]]:
    """Malformed labelled codes (malformed_leis) per section key, for sections that contain any."""
    return {key: codes for key, text in sections.items() if (codes := malformed_leis(str(text)))}
