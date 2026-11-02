"""Legal Entity Identifier (LEI) checks: format, check digits and consistency.

An LEI is 20 characters (ISO 17442): 18 upper-case letters or digits followed by
two check digits under ISO/IEC 7064 MOD 97-10. The check is offline and never
asks a registry whether an LEI exists or belongs to the named entity, so a pass
says only that the characters are internally consistent.

A party section, and any text that names an LEI label or holds an LEI-shaped code
with a letter, reads LEIs (reads_leis). A draft with one such section or such text
reads LEIs in all its text (draft_reads_leis): every section, and the text of a
document file outside its sections. There every LEI-like code counts, wherever it
stands: one run of 16 to 24 letters and digits, or groups that a space, a hyphen, a
dash or a line end join and that hold at least 16 (lei_like_codes). One that is not
LEI-shaped as written is malformed (malformed_leis). The reading is one pass over the
text, with no rescans.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from functools import lru_cache
from itertools import accumulate, compress

# 18 alphanumerics and 2 digits, not part of a longer code.
_LEI_SHAPE = re.compile(r"(?<![A-Z0-9])[A-Z0-9]{18}[0-9]{2}(?![A-Z0-9])")

# An LEI label, in any case: "LEI" or "LEIs" as a word ("LEI-Nr.", "LEI code"), "legal entity identifier(s)"
# or "legal entity ID", and "Rechtsträgerkennung(en)" (also "Rechtstraegerkennung", and with the umlaut
# decomposed into "a" and U+0308, as text copied from some PDFs holds it). A hyphen, a dash, a soft hyphen or
# a line end may stand between any two letters of the long labels, as a PDF or a word processor breaks a
# word ("Rechtsträger-\nkennung", "identi-\nfier"), and any spaces, hyphens or line ends between their words.
_HYPHENS = "-\u00ad\u2010\u2011\u2012\u2013\u2014\u2015\u2212\ufe58\ufe63\uff0d"
_BREAK = rf"(?:[{_HYPHENS}]?[^\S\n]*\n[^\S\n]*|[{_HYPHENS}])?"
_GAP = rf"[{_HYPHENS}\s]+"


def _breakable(*letters: str) -> str:
    return _BREAK.join(letters)


_LABEL = re.compile(
    r"\bLEIs?\b"
    rf"|\b{_breakable(*'legal')}{_GAP}{_breakable(*'entity')}{_GAP}{_breakable(*'id')}"
    rf"|\b{_breakable(*'rechtstr', '(?:ä|a\u0308|ae)', *'gerkennung')}",
    re.IGNORECASE,
)
# A group is a run of letters and digits in any script, with any combining marks among them, so a look-alike
# such as a Cyrillic S (U+0405), a full-width digit or an "S" with a combining accent stays inside the code it
# stands in instead of splitting it. An LEI-like code is one group of _MIN_LENGTH to _MAX_LENGTH characters,
# or a run of groups joined by _joins that together hold at least _MIN_LENGTH. A group of letters only that
# holds a lower-case letter or a letter outside ASCII is a word, not a code: "Aktiengesellschaft",
# "aufsichtsrechtlichen" or "RECHTSTRÄGERKENNUNG" is 16 to 24 letters long, and an LEI has only ASCII letters
# and two check digits. "LEI" and "LEIs" are labels, not codes.
_COMBINING = "\u0300-\u036f\u1ab0-\u1aff\u1dc0-\u1dff\u20d0-\u20ff\ufe20-\ufe2f"
_SPLIT = re.compile(rf"((?:[^\W_]|[{_COMBINING}])+)")
_DIGIT = re.compile(r"\d")
# Characters that text copied from a web page or a PDF may carry inside a code without showing them.
_INVISIBLE = "\u200b\u200c\u200d\u2060\ufeff"
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


_SHOWN_AS_SPACE = str.maketrans(dict.fromkeys(_INVISIBLE, " "))


@lru_cache(maxsize=4096)
def _joins(gap: str) -> bool:
    """Whether the characters between two groups join them into one code: one to three spaces, invisible
    characters, hyphens, dashes or line ends, with at most one hyphen or dash and one line end ("9999 SYNT",
    "9999-SYNT", "9999 \u2013 SYNT", a PDF line end inside a code, "9999SYNTH00-" at a line end)."""
    return (
        len(gap) <= 3
        and all(char.isspace() or char in _HYPHENS or char in _INVISIBLE for char in gap)
        and gap.count("\n") <= 1
        and sum(char in _HYPHENS for char in gap) <= 1
    )


# The kinds of group (_kind).
_CODE, _NOT_A_CODE, _LABEL_GROUP, _DIGITS, _CAPITALS, _WORD = range(6)


@lru_cache(maxsize=65536)
def _kind(group: str) -> int:
    """_CODE for a group of _MIN_LENGTH characters or more that is an LEI-like code on its own, _NOT_A_CODE
    for a longer group that is not, _LABEL_GROUP for LEI or LEIs, _DIGITS for a group with a digit,
    _CAPITALS for ASCII letters without a lower-case letter and _WORD for other letters.

    A long group of at most _MAX_LENGTH characters is a code if it holds a digit or is in ASCII capitals.
    One of up to four more is a code if it starts with a glued "LEI" and holds a digit
    ("LEI9999SYNTH..."). A longer one (a contract address, a hash) is not, and a long word is not.
    """
    size = len(group)
    digit = _DIGIT.search(group) is not None
    if size >= _MIN_LENGTH:
        if size <= _MAX_LENGTH:
            code = digit or (group.isascii() and group.isupper())
        else:
            code = digit and size <= _MAX_LENGTH + 4 and group[:3].lower() == "lei"
        return _CODE if code else _NOT_A_CODE
    if size <= 4 and group.lower() in ("lei", "leis"):
        return _LABEL_GROUP
    if digit:
        return _DIGITS
    return _CAPITALS if group.isascii() and group.isupper() else _WORD


def lei_like_codes(text: str) -> tuple[tuple[int, int, bool], ...]:
    """The spans of the LEI-like codes in a text, in order, each with whether it is one group.

    One group counts if _kind finds it a code. Groups joined by _joins count together if they hold at least
    _MIN_LENGTH characters and a digit, or all have the same length ("XXXX XXXX XXXX XXXX XXXX"); a group
    of _MIN_LENGTH characters or more stands alone. A word joins only next to a group of its length with a
    digit, as in a code in lower case split into groups ("9999 synt h000 0zzq 0263"). The text is split
    into groups once, and only groups that can be part of a code are looked at again.
    """
    # parts alternates the text between groups and the groups: gap, group, gap, ..., group, gap.
    parts = _SPLIT.split(text)
    groups = parts[1::2]
    if not groups:
        return ()
    ends = list(accumulate(map(len, parts)))
    kinds = list(map(_kind, groups))
    # joins[i]: the characters between group i and group i + 1 may join them. A longer gap is not read.
    joins = [len(gap) <= 3 and _joins(gap) for gap in parts[2:-1:2]]
    joinable = [kind in (_DIGITS, _CAPITALS) for kind in kinds]
    count = len(groups)
    for i in compress(range(count), [kind == _DIGITS for kind in kinds]):
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
            digit = digit or kinds[i] == _DIGITS
            same = same and size == len(groups[first])
        else:
            close_run()
            first = last = i
            total = size
            digit = kinds[i] == _DIGITS
            same = True
    close_run()
    return tuple(codes)


def reads_leis(text: str, party: bool = False) -> bool:
    """Whether a text reads LEIs: it is a party section (party), names an LEI label, or holds an LEI-shaped
    code with a letter."""
    return party or _scan(text)[0]


@lru_cache(maxsize=64)
def _scan(text: str) -> tuple[bool, tuple[str, ...]]:
    """Whether the text names an LEI label or holds an LEI-shaped code with a letter, and the LEI-like codes
    in it that are not LEI-shaped (malformed_leis), each quoted once."""
    names = bool(_LABEL.search(text)) or any(
        not match.group(0).isdigit() for match in _LEI_SHAPE.finditer(text)
    )
    malformed: dict[str, None] = {}
    for start, end, single in lei_like_codes(text):
        code = text[start:end]
        if single and _LEI_SHAPE.fullmatch(code):
            continue
        quoted = " ".join(code.translate(_SHOWN_AS_SPACE).split())
        if len(quoted) > _QUOTE_LENGTH:
            quoted = quoted[:_QUOTE_LENGTH] + "\u2026"
        malformed[quoted] = None
    return names, tuple(malformed)


def _lei_matches(text: str, party: bool = False) -> Iterator[re.Match[str]]:
    """Every LEI-shaped code in a text, in order; a purely numeric one only in a text that reads LEIs."""
    reads = reads_leis(text, party)
    for match in _LEI_SHAPE.finditer(text):
        if reads or not match.group(0).isdigit():
            yield match


def find_leis(text: str, party: bool = False) -> tuple[str, ...]:
    """LEI-shaped codes in a text, in order of first appearance, without duplicates."""
    return tuple(dict.fromkeys(match.group(0) for match in _lei_matches(text, party)))


def malformed_leis(text: str, party: bool = False) -> tuple[str, ...]:
    """The LEI-like codes of a text that reads LEIs and are not LEI-shaped as written, without duplicates.

    That is a code of 16 to 19 or 21 to 24 characters, one in lower case, with a letter where a check digit
    belongs or with a character outside ASCII, one glued to a leading "LEI", or one split into groups by
    spaces, hyphens, dashes or a line end. COMMON.LEI_CHECK_DIGITS sends such a code to Review, so that a
    typo next to a valid LEI cannot pass. An LEI-shaped code is left to find_leis, whose check digits are
    checked.
    """
    return _scan(text)[1] if reads_leis(text, party) else ()


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


def leis_by_section(sections: Mapping[str, str], everywhere: bool = False) -> dict[str, tuple[str, ...]]:
    """LEI-shaped codes per section key, for sections that contain any, in draft order. With everywhere,
    every section is read as one that reads LEIs, so a purely numeric code counts in each."""
    return {
        key: codes
        for key, text in sections.items()
        if (codes := find_leis(str(text), everywhere or key in PARTY_SECTIONS))
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
    heading or joins lines differently, is listed too."""
    if not document_text:
        return (), ()
    texts = [str(text) for text in sections.values()]
    inside = {code for text in texts for code in find_leis(text, True)}
    quoted = {code for text in texts for code in malformed_leis(text, True)}
    return (
        tuple(code for code in find_leis(document_text, True) if code not in inside),
        tuple(code for code in malformed_leis(document_text, True) if code not in quoted),
    )
