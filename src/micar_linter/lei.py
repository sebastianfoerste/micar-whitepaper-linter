"""Legal Entity Identifier (LEI) checks: format, check digits and consistency.

An LEI is 20 characters (ISO 17442): 18 upper-case letters or digits followed by
two check digits under ISO/IEC 7064 MOD 97-10. The check is offline and never
asks a registry whether an LEI exists or belongs to the named entity, so a pass
says only that the characters are internally consistent.
"""

from __future__ import annotations

import re

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


def find_leis(text: str) -> tuple[str, ...]:
    """LEI-shaped codes in a text, in order of first appearance, without duplicates."""
    found: list[str] = []
    for match in _LEI_SHAPE.finditer(text):
        code = match.group(0)
        if code.isdigit():
            window = text[max(0, match.start() - _LABEL_WINDOW) : match.start()]
            if not _LEI_LABEL.search(window):
                continue
        if code not in found:
            found.append(code)
    return tuple(found)


def leis_by_section(sections: dict[str, str]) -> dict[str, tuple[str, ...]]:
    """LEI-shaped codes per section key, for sections that contain any, in draft order."""
    return {key: codes for key, text in sections.items() if (codes := find_leis(str(text)))}
