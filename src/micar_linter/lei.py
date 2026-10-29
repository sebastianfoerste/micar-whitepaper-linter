"""Legal Entity Identifier (LEI) checks: format, check digits and consistency.

An LEI is 20 characters (ISO 17442): 18 upper-case letters or digits followed by
two check digits under ISO/IEC 7064 MOD 97-10. The check is offline and never
asks a registry whether an LEI exists or belongs to the named entity, so a pass
says only that the characters are internally consistent.
"""

from __future__ import annotations

import re
from collections.abc import Iterator

# 18 alphanumerics and 2 digits, not part of a longer code.
_LEI_SHAPE = re.compile(r"(?<![A-Z0-9])[A-Z0-9]{18}[0-9]{2}(?![A-Z0-9])")
# A purely numeric 20-digit run (an account or reference number) counts only right after an LEI
# label, with at most two short words between them ("LEI: ...", "the LEI is ...", "LEI code ...").
_LEI_LABEL = re.compile(
    r"\b(?:LEI|legal entity identifier|Rechtstr(?:ä|ae)gerkennung)\W*(?:[^\W\d_]{1,12}\W+){0,2}$",
    re.IGNORECASE,
)
_LABEL_WINDOW = 60

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


def _lei_matches(text: str) -> Iterator[re.Match[str]]:
    """Every LEI-shaped code in a text, in order; a purely numeric one only after an LEI label."""
    for match in _LEI_SHAPE.finditer(text):
        if match.group(0).isdigit():
            window = text[max(0, match.start() - _LABEL_WINDOW) : match.start()]
            if not _LEI_LABEL.search(window):
                continue
        yield match


def find_leis(text: str) -> tuple[str, ...]:
    """LEI-shaped codes in a text, in order of first appearance, without duplicates."""
    return tuple(dict.fromkeys(match.group(0) for match in _lei_matches(text)))


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
