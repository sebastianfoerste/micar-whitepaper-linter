"""Legal Entity Identifier (LEI) checks: format, check digits and consistency.

An LEI is 20 characters (ISO 17442): 18 upper-case letters or digits followed by
two check digits under ISO/IEC 7064 MOD 97-10. The check is offline and never
asks a registry whether an LEI exists or belongs to the named entity, so a pass
says only that the characters are internally consistent.

A party section, and any text that names an LEI label or holds an LEI-shaped code
with a letter, reads LEIs (reads_leis). A draft with one such section or such text
reads LEIs in all its text (draft_reads_leis): every section, and the text of a
document file outside its sections. Each text is read as written and, where markup or
a character reference changes it, as a Markdown or HTML renderer shows it (_shown).
There every LEI-like code counts, wherever it stands: one run of 16 to 24 letters and
digits (or a longer one with "LEI" or a word glued to such a code), groups that a
space, a hyphen, a dash, an invisible character or a line end join and that hold at
least 16, or two pieces of a code that a table cell wraps onto the next line of a
label line (_codes). One that is not LEI-shaped as written is malformed
(malformed_leis). Each reading is one pass over the text, with no rescans.
"""

from __future__ import annotations

import html
import re
import unicodedata
from collections.abc import Iterator, Mapping
from functools import cache, lru_cache
from heapq import merge
from itertools import accumulate, compress, repeat
from typing import NamedTuple

# 18 alphanumerics and 2 digits, not part of a longer code.
_LEI_SHAPE = re.compile(r"(?<![A-Z0-9])[A-Z0-9]{18}[0-9]{2}(?![A-Z0-9])")

# An LEI label, in any case: "LEI" or "LEIs" as a word ("LEI-Nr.", "LEI code"), "legal entity identifier(s)"
# or "legal entity ID", and "Rechtsträgerkennung(en)" (also "Rechtstraegerkennung", and with the umlaut
# decomposed into "a" and U+0308, as text copied from some PDFs holds it). A hyphen, a dash, a soft hyphen or
# a line end may stand between any two letters of the long labels, as a PDF or a word processor breaks a
# word ("Rechtsträger-\nkennung", "identi-\nfier"), and any spaces, hyphens or line ends between their words.
_LABEL_WORDS = (
    r"\bLEIs?\b"
    r"|\b{legal}{gap}{entity}{gap}{id}"
    r"|\b{rechtstraeger}"
)
# Characters that join groups as a hyphen does, besides dash punctuation (Unicode category Pd: the
# hyphen-minus, hyphen, non-breaking hyphen, figure dash, en and em dashes, horizontal bar, two-em dash,
# small em dash, small and full-width hyphen-minus and the other dashes): the soft hyphen, the minus sign,
# the hyphen bullet and the middle dots (U+00B7, the hyphenation point U+2027, the katakana middle dots
# U+30FB and U+FF65).
_OTHER_HYPHENS = "\u00ad\u2212\u2043\u00b7\u2027\u30fb\uff65"
# Planes 0, 1 and 14 hold every mark, format character and dash that Unicode assigns.
_PLANES = ((0, 0x20000), (0xE0000, 0xE1000))


class _Characters(NamedTuple):
    """The character classes of the reading, from the Unicode database of the Python that runs it."""

    # Dash punctuation and _OTHER_HYPHENS.
    hyphens: frozenset[str]
    # Format characters (Unicode category Cf: zero-width spaces and joiners, left-to-right and right-to-left
    # marks, bidirectional embeddings and isolates, invisible operators, the soft hyphen, the Mongolian vowel
    # separator, the Arabic letter mark, the byte-order mark), control characters other than whitespace, and
    # the marks outside the Basic Multilingual Plane, which text copied from a web page or a PDF may carry
    # inside a code without showing them. dropped removes them, shown_as_space turns each into a space.
    dropped: dict[int, None]
    shown_as_space: dict[int, str]
    # A group is a run of letters and digits in any script, with any marks of the Basic Multilingual Plane
    # among them (Unicode category M: combining accents, variation selectors), so a look-alike such as a
    # Cyrillic S (U+0405), a full-width digit or an "S" with a combining accent stays inside the code it
    # stands in instead of splitting it. (A regular expression class with characters beyond that plane is
    # read range by range, several times slower.)
    split: re.Pattern[str]
    label: re.Pattern[str]


def _character_class(characters: list[str]) -> str:
    """The body of a regular expression character class that matches the characters, as ranges."""
    codes = sorted(map(ord, characters))
    ranges: list[tuple[int, int]] = []
    start = previous = codes[0]
    for code in codes[1:]:
        if code != previous + 1:
            ranges.append((start, previous))
            start = code
        previous = code
    ranges.append((start, previous))
    return "".join(
        re.escape(chr(first)) if first == last else f"{re.escape(chr(first))}-{re.escape(chr(last))}"
        for first, last in ranges
    )


@cache
def _characters() -> _Characters:
    """The character classes, built once on first use."""
    marks: list[str] = []
    invisible: list[str] = []
    hyphens = list(_OTHER_HYPHENS)
    category = unicodedata.category
    for start, end in _PLANES:
        for code in range(start, end):
            char = chr(code)
            kind = category(char)
            if kind[0] == "M" and code < 0x10000:
                marks.append(char)
            elif kind[0] == "M" or kind == "Cf" or (kind == "Cc" and not char.isspace()):
                invisible.append(char)
            elif kind == "Pd":
                hyphens.append(char)
    dashes = _character_class(hyphens)
    # Between two letters of a long label: a line end, with or without a hyphen or dash before it, or one
    # hyphen or dash.
    letter_break = rf"(?:[{dashes}]?[^\S\n]*\n[^\S\n]*|[{dashes}])?"
    label = _LABEL_WORDS.format(
        legal=letter_break.join("legal"),
        entity=letter_break.join("entity"),
        id=letter_break.join("id"),
        rechtstraeger=letter_break.join([*"rechtstr", "(?:\u00e4|a\u0308|ae)", *"gerkennung"]),
        gap=rf"[{dashes}\s]+",
    )
    return _Characters(
        hyphens=frozenset(hyphens),
        dropped=dict.fromkeys(map(ord, invisible)),
        shown_as_space=dict.fromkeys(map(ord, invisible), " "),
        split=re.compile(rf"((?:[^\W_]|[{_character_class(marks)}])+)"),
        label=re.compile(label, re.IGNORECASE),
    )


# What a Markdown or HTML renderer does not show, or shows as another character: an HTML tag, a character
# reference ("&nbsp;", "&#160;", "&shy;", "&#8203;"), and a run of underscores at the edge of a word
# (emphasis; one inside a word, as in snake_case, is shown). A block tag and <br> show as a line end, any
# other tag as nothing. _shown removes HTML comments first and _HIDDEN_MARKUP last.
_MARKUP = re.compile(
    r"<(?P<tag>/?[A-Za-z][A-Za-z0-9-]*)(?:\s[^<>]*+)?/?>"
    r"|(?P<reference>&(?:#[0-9]{1,7}|#[xX][0-9a-fA-F]{1,6}|[A-Za-z][A-Za-z0-9]{1,31});)"
    r"|_+"
)
# Markup a renderer never shows: a backslash before punctuation or a line end (an escape or a hard line
# break), a link target ("](#x)", "][ref]"), a bracket, and a run of asterisks, backticks or tildes (emphasis,
# a code span, strikethrough).
_HIDDEN_MARKUP = re.compile(r"\\(?=[!-/:-@\[-`{-~\n])|\]\([^()\s\]]*+\)|\]\[[^\[\]\s]*+\]|!?\[|\]|[*`~]+")
# The characters that start markup; a text without them is shown as written.
_MARKUP_START = re.compile(r"[<&\\\[\]*`~_]")
_BLOCK_TAGS = frozenset(
    {
        "address", "article", "aside", "blockquote", "br", "caption", "dd", "details", "div", "dl", "dt",
        "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6", "header",
        "hr", "li", "main", "nav", "ol", "p", "pre", "section", "summary", "table", "tbody", "td", "tfoot",
        "th", "thead", "tr", "ul",
    }
)  # fmt: skip


def _shown_markup(match: re.Match[str]) -> str:
    if tag := match.group("tag"):
        return "\n" if tag.lstrip("/").lower() in _BLOCK_TAGS else ""
    if reference := match.group("reference"):
        return html.unescape(reference)
    # Underscores between two letters or digits are part of the word.
    text, start, end = match.string, match.start(), match.end()
    inside = (
        start
        and end < len(text)
        and _WORD_CHARACTER.match(text, start - 1)
        and _WORD_CHARACTER.match(text, end)
    )
    return match.group() if inside else ""


def _shown(text: str) -> str:
    """The text as a Markdown or HTML renderer shows it: HTML comments (each "<!--" up to the next "-->"),
    tags and the other markup of _MARKUP and _HIDDEN_MARKUP removed, character references replaced by the
    characters they name. The reading reads a text as written and, where it differs, as shown, so markup or
    a reference inside a code cannot split it ("9999&nbsp;SYNT&nbsp;...", "9999SYNTH**0000ZZQ026**",
    "9999SYNTH<!-- -->0000ZZQ026")."""
    if _MARKUP_START.search(text) is None:
        return text
    if "<!--" in text:
        kept: list[str] = []
        position = 0
        while (start := text.find("<!--", position)) != -1:
            end = text.find("-->", start + 4)
            if end == -1:
                break
            kept.append(text[position:start])
            position = end + 3
        kept.append(text[position:])
        text = "".join(kept)
    if "<" in text or "&" in text or "_" in text:
        text = _MARKUP.sub(_shown_markup, text)
    return _HIDDEN_MARKUP.sub("", text)


_DIGIT = re.compile(r"\d")
_WORD_CHARACTER = re.compile(r"[^\W_]")
# A run of letters at the start or the end of a group, a word glued to a code.
_LEADING_WORD = re.compile(r"[^\W\d_]+")
_TRAILING_WORD = re.compile(r"[^\W\d_]+$")
# An LEI that has lost or gained up to four characters.
_MIN_LENGTH = 16
_MAX_LENGTH = 24
# A malformed code is quoted with each run of spaces, invisible characters or line ends as one space, and cut
# after this many characters.
_QUOTE_LENGTH = 40

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


@lru_cache(maxsize=4096)
def _joins(gap: str) -> bool:
    """Whether the characters between two groups join them into one code: any number of invisible
    characters, and up to three spaces, hyphens, dashes or line ends, with at most one hyphen or dash and one
    line end ("9999 SYNT", "9999-SYNT", "9999 \u2013 SYNT", a PDF line end inside a code, "9999SYNTH00-" at
    a line end, "9999SYNTH\u200e0000")."""
    characters = _characters()
    shown = gap.translate(characters.dropped)
    return (
        len(shown) <= 3
        and all(char.isspace() or char in characters.hyphens for char in shown)
        and shown.count("\n") <= 1
        and sum(char in characters.hyphens for char in shown) <= 1
    )


def _long_gap_joins(gap: str) -> bool:
    """_joins for a gap of more than three characters, which joins only if invisible characters make up the
    rest; the gap is looked at once."""
    shown = gap.translate(_characters().dropped)
    return len(shown) <= 3 and _joins(shown)


# The kinds of group (_kind).
_CODE, _NOT_A_CODE, _LABEL_GROUP, _DIGITS, _MIXED, _CAPITALS, _WORD = range(7)


def _glued(group: str) -> bool:
    """Whether a group of more than _MAX_LENGTH characters is a code of _MIN_LENGTH to _MAX_LENGTH characters
    with a digit and with a word glued before or after it ("Kennung9999SYNTH0000ZZQ026", "...0263GmbH"): the
    group without its leading letters, or without those up to the last lower-case one ("KennungSYNTH..."),
    without its trailing letters, or without both."""
    starts = {0}
    if lead := _LEADING_WORD.match(group):
        starts.add(lead.end())
        lower = [index for index, char in enumerate(lead.group()) if char.islower()]
        if lower:
            starts.add(lower[-1] + 1)
    ends = {len(group)}
    if trail := _TRAILING_WORD.search(group):
        ends.add(trail.start())
    return any(
        _MIN_LENGTH <= end - start <= _MAX_LENGTH and _DIGIT.search(group, start, end) is not None
        for start in starts
        for end in ends
    )


@lru_cache(maxsize=65536)
def _kind(group: str) -> int:
    """_CODE for a group of _MIN_LENGTH characters or more that is an LEI-like code on its own, _NOT_A_CODE
    for a longer group that is not, _LABEL_GROUP for LEI or LEIs, _DIGITS for a group of digits only,
    _MIXED for one with a digit and a letter, _CAPITALS for ASCII letters without a lower-case letter and
    _WORD for other letters.

    A long group of at most _MAX_LENGTH characters is a code if it holds a digit or is in ASCII capitals.
    A longer one is a code if it holds a digit and starts with a glued "LEI" and is at most four characters
    longer ("LEI9999SYNTH..."), or if a word glued before or after it leaves such a code (_glued). Any other
    longer group (a contract address, a hash) is not, and a long word is not.
    """
    size = len(group)
    digit = _DIGIT.search(group) is not None
    if size >= _MIN_LENGTH:
        if size <= _MAX_LENGTH:
            code = digit or (group.isascii() and group.isupper())
        else:
            code = digit and ((size <= _MAX_LENGTH + 4 and group[:3].lower() == "lei") or _glued(group))
        return _CODE if code else _NOT_A_CODE
    if size <= 4 and group.lower() in ("lei", "leis"):
        return _LABEL_GROUP
    if digit:
        return _DIGITS if group.isdigit() else _MIXED
    return _CAPITALS if group.isascii() and group.isupper() else _WORD


def _label_lines(text: str) -> set[int]:
    """The lines of a text (counted from 0) on which an LEI label starts or ends."""
    lines: set[int] = set()
    line = position = 0
    for match in _characters().label.finditer(text):
        line += text.count("\n", position, match.start())
        lines.add(line)
        line += text.count("\n", match.start(), match.end())
        lines.add(line)
        position = match.end()
    return lines


def lei_like_codes(text: str) -> tuple[tuple[int, int, bool], ...]:
    """The spans of the LEI-like codes in a text, in order, each with whether it is one group (_codes)."""
    return _codes(text)[0]


def _codes(
    text: str,
) -> tuple[tuple[tuple[int, int, bool], ...], tuple[tuple[tuple[int, int], tuple[int, int]], ...]]:
    """The LEI-like codes of a text, and the pairs of pieces of a code that a line end and other text split.

    One group counts if _kind finds it a code. Groups joined by _joins count together if they hold at least
    _MIN_LENGTH characters and a digit, or all have the same length ("XXXX XXXX XXXX XXXX XXXX"); a group
    of _MIN_LENGTH characters or more stands alone. A word joins only next to a group of its length with a
    digit, as in a code in lower case split into groups ("9999 synt h000 0zzq 0263").

    A piece is a group of fewer than _MIN_LENGTH characters that holds a letter and a digit. A piece on a line
    that names an LEI label, or on the line before one, and the longest piece on the next line form a pair if
    together they hold at least _MIN_LENGTH characters: a code that a narrow table cell wraps, with the words
    of the next cells between its two pieces ("Offeror LEI 9999SYNTH0000 Synthetic Offeror GmbH" / "ZZQ026
    Frankfurt am Main"). The text is split into groups once, and only groups that can be part of a code are
    looked at again.
    """
    # parts alternates the text between groups and the groups: gap, group, gap, ..., group, gap.
    parts = _characters().split.split(text)
    groups = parts[1::2]
    if not groups:
        return (), ()
    ends = list(accumulate(map(len, parts)))
    kinds = list(map(_kind, groups))
    # joins[i]: the characters between group i and group i + 1 may join them.
    joins = [_joins(gap) if len(gap) <= 3 else _long_gap_joins(gap) for gap in parts[2:-1:2]]
    joinable = [kind in (_DIGITS, _MIXED, _CAPITALS) for kind in kinds]
    count = len(groups)
    for i in compress(range(count), [kind in (_DIGITS, _MIXED) for kind in kinds]):
        size = len(groups[i])
        if i and kinds[i - 1] == _WORD and joins[i - 1] and len(groups[i - 1]) == size:
            joinable[i - 1] = True
        if i + 1 < count and kinds[i + 1] == _WORD and joins[i] and len(groups[i + 1]) == size:
            joinable[i + 1] = True
    codes: list[tuple[int, int, bool]] = []
    # The open run of joined groups: its first and last group, its length, whether a group holds a digit
    # and whether all its groups have the length of the first.
    first = last = -1
    total = 0
    digit = same = False

    def close_run() -> None:
        if last > first and total >= _MIN_LENGTH and (digit or same):
            codes.append((ends[2 * first], ends[2 * last + 1], False))

    looked_at = [flag or kind == _CODE for flag, kind in zip(joinable, kinds, strict=True)]
    for i in compress(range(count), looked_at):
        size = len(groups[i])
        if kinds[i] == _CODE:
            close_run()
            first = last = -1
            codes.append((ends[2 * i], ends[2 * i + 1], True))
        elif last == i - 1 and last >= 0 and joins[last]:
            last = i
            total += size
            digit = digit or kinds[i] in (_DIGITS, _MIXED)
            same = same and size == len(groups[first])
        else:
            close_run()
            first = last = i
            total = size
            digit = kinds[i] in (_DIGITS, _MIXED)
            same = True
    close_run()
    pieces = list(compress(range(count), [kind == _MIXED for kind in kinds]))
    if len(pieces) < 2:
        return tuple(codes), ()
    # lines[i]: the line of group i, which never decreases.
    lines = list(accumulate(map(str.count, parts[0:-1:2], repeat("\n"))))
    if lines[pieces[0]] == lines[pieces[-1]]:
        return tuple(codes), ()
    # The longest piece on each line, and the pieces with a long enough piece on the next line.
    longest: dict[int, int] = {}
    for i in pieces:
        if lines[i] not in longest or len(groups[i]) > len(groups[longest[lines[i]]]):
            longest[lines[i]] = i
    candidates = [
        (i, other)
        for i in pieces
        if (other := longest.get(lines[i] + 1)) is not None
        and len(groups[i]) + len(groups[other]) >= _MIN_LENGTH
    ]
    labels = _label_lines(text) if candidates else set()
    pairs = [
        ((ends[2 * i], ends[2 * i + 1]), (ends[2 * other], ends[2 * other + 1]))
        for i, other in candidates
        if lines[i] in labels or lines[i] + 1 in labels
    ]
    return tuple(codes), tuple(pairs)


def reads_leis(text: str, party: bool = False) -> bool:
    """Whether a text reads LEIs: it is a party section (party), names an LEI label, or holds an LEI-shaped
    code with a letter, as written or as shown (_shown)."""
    return party or _scan(text).names


def _quote(code: str) -> str:
    quoted = " ".join(code.translate(_characters().shown_as_space).split())
    return quoted[:_QUOTE_LENGTH] + "\u2026" if len(quoted) > _QUOTE_LENGTH else quoted


def _malformed(text: str) -> Iterator[str]:
    """The LEI-like codes of one reading of a text that are not LEI-shaped, quoted, in order: a pair of
    pieces as both pieces with an ellipsis between them."""
    codes, pairs = _codes(text)
    found = (
        (start, _quote(text[start:end]))
        for start, end, single in codes
        if not (single and _LEI_SHAPE.fullmatch(text[start:end]))
    )
    split = (
        (first[0], f"{_quote(text[first[0] : first[1]])} \u2026 {_quote(text[second[0] : second[1]])}")
        for first, second in pairs
    )
    for _, quoted in merge(found, split, key=lambda entry: entry[0]):
        yield quoted


class _Scan(NamedTuple):
    """What _scan finds in a text."""

    # The text names an LEI label or holds an LEI-shaped code with a letter, as written or as shown.
    names: bool
    # The LEI-like codes that are not LEI-shaped (malformed_leis), each quoted once.
    malformed: tuple[str, ...]
    # The LEI-shaped codes, in order and without duplicates, as written and, where the text differs as
    # shown (_shown), as written and as shown.
    written: tuple[str, ...]
    both: tuple[str, ...]


@lru_cache(maxsize=64)
def _scan(text: str) -> _Scan:
    """Read a text as written and, where it differs, as shown (_shown)."""
    shown = _shown(text)
    readings = (text,) if shown == text else (text, shown)
    names = False
    malformed: dict[str, None] = {}
    shaped: list[tuple[str, ...]] = []
    for reading in readings:
        codes = tuple(dict.fromkeys(match.group(0) for match in _LEI_SHAPE.finditer(reading)))
        shaped.append(codes)
        names = (
            names
            or _characters().label.search(reading) is not None
            or any(not code.isdigit() for code in codes)
        )
        malformed.update(dict.fromkeys(_malformed(reading)))
    return _Scan(
        names, tuple(malformed), shaped[0], tuple(dict.fromkeys(code for codes in shaped for code in codes))
    )


def _lei_matches(text: str, party: bool = False) -> Iterator[re.Match[str]]:
    """Every LEI-shaped code in a text, in order; a purely numeric one only in a text that reads LEIs."""
    reads = reads_leis(text, party)
    for match in _LEI_SHAPE.finditer(text):
        if reads or not match.group(0).isdigit():
            yield match


def find_leis(text: str, party: bool = False, shown: bool = False) -> tuple[str, ...]:
    """LEI-shaped codes in a text as written (with shown, also as shown), in order of first appearance,
    without duplicates; a purely numeric one only in a text that reads LEIs."""
    scan = _scan(text)
    reads = party or scan.names
    return tuple(code for code in (scan.both if shown else scan.written) if reads or not code.isdigit())


def malformed_leis(text: str, party: bool = False) -> tuple[str, ...]:
    """The LEI-like codes of a text that reads LEIs and are not LEI-shaped as written, without duplicates,
    read in the text as written and as shown.

    That is a code of 16 to 19 or 21 to 24 characters, one in lower case, with a letter where a check digit
    belongs or with a character outside ASCII, one glued to a leading "LEI" or to a word, one split into
    groups by spaces, hyphens, dashes, invisible characters or a line end, or two pieces of a code that a
    table cell wraps. COMMON.LEI_CHECK_DIGITS sends such a code to Review, so that a typo next to a valid
    LEI cannot pass. An LEI-shaped code is left to find_leis, whose check digits are checked.
    """
    return _scan(text).malformed if reads_leis(text, party) else ()


def other_person_leis(text: str, party: bool = False) -> tuple[str, ...]:
    """LEI-shaped codes that the text gives for a person other than the parties, without duplicates.

    That is the provider in charge of the placing, a custodian, or a person other than the issuer who
    offers the token, seeks its admission to trading or draws up the white paper. The role must be named
    before the code in its own sentence or line, with no other code in between: a template label ("CASP
    identifier: ...") or a sentence such as "The crypto-asset service provider in charge of the placing has
    the LEI ...". A role named in an earlier sentence does not carry over.
    """
    found: list[str] = []
    start = 0
    for match in _lei_matches(text, party):
        context = _last_sentence(text[start : match.start()])
        if _OTHER_PERSON.search(context) and match.group(0) not in found:
            found.append(match.group(0))
        start = match.end()
    return tuple(found)


def _last_sentence(text: str) -> str:
    """The text after the last sentence or line end."""
    ends = list(_SENTENCE_END.finditer(text))
    return text[ends[-1].end() :] if ends else text


def leis_by_section(
    sections: Mapping[str, str], everywhere: bool = False, shown: bool = False
) -> dict[str, tuple[str, ...]]:
    """LEI-shaped codes per section key, for sections that contain any, in draft order. With everywhere,
    every section is read as one that reads LEIs, so a purely numeric code counts in each; with shown, each
    section is read as shown too (find_leis)."""
    return {
        key: codes
        for key, text in sections.items()
        if (codes := find_leis(str(text), everywhere or key in PARTY_SECTIONS, shown))
    }


def malformed_leis_by_section(
    sections: Mapping[str, str], everywhere: bool = False
) -> dict[str, tuple[str, ...]]:
    """Malformed LEI-like codes (malformed_leis) per section key, for sections that contain any. With
    everywhere, every section is read as one that reads LEIs."""
    return {
        key: codes
        for key, text in sections.items()
        if (codes := malformed_leis(str(text), everywhere or key in PARTY_SECTIONS))
    }


def draft_reads_leis(sections: Mapping[str, str], document_text: str = "") -> bool:
    """Whether a draft reads LEIs in all its text: it has a party section, or a section or the text of its
    file names an LEI label or holds an LEI-shaped code with a letter."""
    return reads_leis(document_text) or any(
        reads_leis(str(text), key in PARTY_SECTIONS) for key, text in sections.items()
    )


def codes_outside_sections(
    sections: Mapping[str, str], document_text: str
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """The LEI-shaped codes and the malformed LEI-like codes of a document file's text that no section
    holds, read as a text that reads LEIs: those in a heading, a table, a header or footer, or text in no
    section. A code whose span differs from the one a section quotes, because the section text leaves out a
    heading or joins lines differently, is listed too. The texts are read as written and as shown."""
    if not document_text:
        return (), ()
    texts = [str(text) for text in sections.values()]
    inside = {code for text in texts for code in find_leis(text, True, True)}
    quoted = {code for text in texts for code in malformed_leis(text, True)}
    return (
        tuple(code for code in find_leis(document_text, True, True) if code not in inside),
        tuple(code for code in malformed_leis(document_text, True) if code not in quoted),
    )
