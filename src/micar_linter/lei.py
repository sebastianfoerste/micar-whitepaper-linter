"""Legal Entity Identifier (LEI) checks: format, check digits and consistency.

An LEI is 20 characters (ISO 17442): 18 upper-case letters or digits followed by
two check digits under ISO/IEC 7064 MOD 97-10. The check is offline and never
asks a registry whether an LEI exists or belongs to the named entity, so a pass
says only that the characters are internally consistent.

A party section, and any text that names an LEI label or holds an LEI-shaped code
with a letter, reads LEIs (reads_leis). There every LEI-like code counts, wherever it
stands: one run of 18 to 22 letters and digits, or groups that a space, a hyphen or a
line end join and that hold at least 18 (lei_like_codes). One that is not LEI-shaped
as written is malformed (malformed_leis). The reading is one pass over the text, with
no rescans.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from functools import lru_cache

# 18 alphanumerics and 2 digits, not part of a longer code.
_LEI_SHAPE = re.compile(r"(?<![A-Z0-9])[A-Z0-9]{18}[0-9]{2}(?![A-Z0-9])")

# An LEI label, in any case: "LEI" or "LEIs" as a word ("LEI-Nr.", "LEI code"), "legal entity identifier(s)"
# or "legal entity ID", and "Rechtsträgerkennung(en)" (also "Rechtstraegerkennung"). A hyphen, a soft hyphen
# or a line end may stand between any two letters of the long labels, as a PDF or a word processor breaks a
# word ("Rechtsträger-\nkennung", "identi-\nfier"), and any spaces, hyphens or line ends between their words.
_HYPHENS = "-\u00ad\u2010\u2011"
_BREAK = rf"(?:[{_HYPHENS}]?[^\S\n]*\n[^\S\n]*|[{_HYPHENS}])?"
_GAP = rf"[{_HYPHENS}\s]+"


def _breakable(*letters: str) -> str:
    return _BREAK.join(letters)


_LABEL = re.compile(
    r"\bLEIs?\b"
    rf"|\b{_breakable(*'legal')}{_GAP}{_breakable(*'entity')}{_GAP}{_breakable(*'id')}"
    rf"|\b{_breakable(*'rechtstr', '(?:ä|ae)', *'gerkennung')}",
    re.IGNORECASE,
)
# A group is a run of ASCII letters and digits. An LEI-like code is one group of _MIN_LENGTH to _MAX_LENGTH
# characters, or a run of groups joined by _joins that together hold at least _MIN_LENGTH. A group of letters
# only that holds a lower-case letter is a word, not a code: "Aktiengesellschaft" or "aufsichtsrechtlichen"
# is 18 to 22 letters long. "LEI" and "LEIs" are labels, not codes.
_GROUP = re.compile(r"[A-Za-z0-9]+")
# Characters that text copied from a web page or a PDF may carry inside a code without showing them.
_INVISIBLE = "\u200b\u200c\u200d\u2060\ufeff"
_MIN_LENGTH = 18
_MAX_LENGTH = 22
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


def _joins(gap: str) -> bool:
    """Whether the characters between two groups join them into one code: one to three spaces, invisible
    characters, hyphens or line ends, with at most one hyphen and one line end ("9999 SYNT", "9999-SYNT", a
    PDF line end inside a code, "9999SYNTH00-" at a line end)."""
    return (
        len(gap) <= 3
        and all(char.isspace() or char in _HYPHENS or char in _INVISIBLE for char in gap)
        and gap.count("\n") <= 1
        and sum(char in _HYPHENS for char in gap) <= 1
    )


def _kind(group: str) -> str:
    """'long' for a group of _MIN_LENGTH characters or more, 'label' for LEI or LEIs, 'digit' for a group with
    a digit, 'capitals' for letters with no lower-case letter, 'word' for letters with a lower-case letter."""
    if len(group) >= _MIN_LENGTH:
        return "long"
    if group.lower() in ("lei", "leis"):
        return "label"
    if any(char.isdigit() for char in group):
        return "digit"
    return "word" if any(char.islower() for char in group) else "capitals"


def lei_like_codes(text: str) -> tuple[tuple[int, int, bool], ...]:
    """The spans of the LEI-like codes in a text, in order, each with whether it is one group.

    One group counts if it has _MIN_LENGTH to _MAX_LENGTH characters and holds a digit or no lower-case
    letter. A longer group (a contract address, a hash) does not, and stands alone. Groups joined by _joins
    count together if they hold at least _MIN_LENGTH characters and a digit, or all have the same length
    ("XXXX XXXX XXXX XXXX XXXX"). A word joins only next to a group of its length with a digit, as in a code
    in lower case split into groups ("9999 synt h000 0zzq 0263"). The text is read once, group by group.
    """
    groups = [(match.start(), match.end(), match.group(0)) for match in _GROUP.finditer(text)]
    kinds = [_kind(group) for _, _, group in groups]
    # joined[i]: the characters between group i - 1 and group i may join them. A longer gap is not read.
    joined = [False] + [
        groups[i][0] - groups[i - 1][1] <= 3 and _joins(text[groups[i - 1][1] : groups[i][0]])
        for i in range(1, len(groups))
    ]

    def beside_digit_group(i: int) -> bool:
        size = len(groups[i][2])
        before = joined[i] and kinds[i - 1] == "digit" and len(groups[i - 1][2]) == size
        after = (
            i + 1 < len(groups)
            and joined[i + 1]
            and kinds[i + 1] == "digit"
            and len(groups[i + 1][2]) == size
        )
        return before or after

    joinable = [
        kind in ("digit", "capitals") or (kind == "word" and beside_digit_group(i))
        for i, kind in enumerate(kinds)
    ]
    codes: list[tuple[int, int, bool]] = []
    run: list[int] = []

    def close_run() -> None:
        if len(run) > 1:
            sizes = {len(groups[i][2]) for i in run}
            if sum(len(groups[i][2]) for i in run) >= _MIN_LENGTH and (
                any(kinds[i] == "digit" for i in run) or len(sizes) == 1
            ):
                codes.append((groups[run[0]][0], groups[run[-1]][1], False))
        run.clear()

    for i, (start, end, group) in enumerate(groups):
        if run and not (joinable[i] and joined[i]):
            close_run()
        if joinable[i]:
            run.append(i)
        elif (
            kinds[i] == "long"
            and len(group) <= _MAX_LENGTH
            and (any(char.isdigit() for char in group) or not any(char.islower() for char in group))
        ):
            codes.append((start, end, True))
    close_run()
    return tuple(codes)


def reads_leis(text: str, party: bool = False) -> bool:
    """Whether a text reads LEIs: it is a party section (party), names an LEI label, or holds an LEI-shaped
    code with a letter."""
    return _scan(text, party)[0]


@lru_cache(maxsize=64)
def _scan(text: str, party: bool) -> tuple[bool, tuple[str, ...]]:
    """Whether the text reads LEIs, and its malformed codes (malformed_leis)."""
    reads = (
        party
        or bool(_LABEL.search(text))
        or any(not match.group(0).isdigit() for match in _LEI_SHAPE.finditer(text))
    )
    if not reads:
        return False, ()
    malformed: dict[str, None] = {}
    for start, end, single in lei_like_codes(text):
        code = text[start:end]
        if single and _LEI_SHAPE.fullmatch(code):
            continue
        quoted = " ".join(code.translate(_SHOWN_AS_SPACE).split())
        if len(quoted) > _QUOTE_LENGTH:
            quoted = quoted[:_QUOTE_LENGTH] + "\u2026"
        malformed[quoted] = None
    return True, tuple(malformed)


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

    That is a code of 18, 19, 21 or 22 characters, one in lower case or with a letter where a check digit
    belongs, or one split into groups by spaces, hyphens or a line end. COMMON.LEI_CHECK_DIGITS sends such a
    code to Review, so that a typo next to a valid LEI cannot pass. An LEI-shaped code is left to find_leis,
    whose check digits are checked.
    """
    return _scan(text, party)[1]


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


def leis_by_section(sections: dict[str, str]) -> dict[str, tuple[str, ...]]:
    """LEI-shaped codes per section key, for sections that contain any, in draft order."""
    return {
        key: codes for key, text in sections.items() if (codes := find_leis(str(text), key in PARTY_SECTIONS))
    }


def malformed_leis_by_section(sections: dict[str, str]) -> dict[str, tuple[str, ...]]:
    """Malformed LEI-like codes (malformed_leis) per section key, for sections that contain any."""
    return {
        key: codes
        for key, text in sections.items()
        if (codes := malformed_leis(str(text), key in PARTY_SECTIONS))
    }
