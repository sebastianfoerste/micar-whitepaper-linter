"""ISO 24165 Digital Token Identifiers (DTI) in a white paper, read offline for COMMON.DTI_FORMAT.

Art. 3 of Delegated Regulation (EU) 2025/421, which applies from 23 December 2025: where the ISO 24165
DTI is provided, the white paper is identified with a valid identifier of type 3 of the group of
crypto-assets it relates to (the functionally fungible group DTI, FFG DTI), and each crypto-asset with a
valid identifier of its own; where no DTI is available, with a digital token identifier approved by ESMA
at Union level. The template of Implementing Regulation (EU) 2024/2984 carries the two codes in fields
F.13 and F.14 of Table 2, B.15 and B.16 of Table 3 and B.12 and B.13 of Table 4, each "where available",
and Table 1 of its Annex gives the {DTI} format as 9 alphanumerical characters (both OJ texts read on
2026-11-10).

The check is offline, as the LEI checks are (ADR 0007): a code of the right shape need not be registered
with the Digital Token Identifier Foundation or belong to the token. ISO 24165 itself was not read, so no
check character is computed and no character set narrower than the Annex's is assumed.

This module is on the playground's JSON path (docs/playground/lint.py): it imports no third-party package.
"""

from __future__ import annotations

import re

from micar_linter.placeholders import is_not_applicable, is_placeholder
from micar_linter.whitepaper import WhitepaperType

# The template fields of the DTI and the FFG DTI, by regime.
DTI_FIELDS: dict[WhitepaperType, tuple[str, str]] = {
    WhitepaperType.OTHER: ("F.13", "F.14"),
    WhitepaperType.ART: ("B.15", "B.16"),
    WhitepaperType.EMT: ("B.12", "B.13"),
}

# {DTI} in Table 1 of the Annex to Implementing Regulation (EU) 2024/2984.
DTI_CODE = re.compile(r"[A-Za-z0-9]{9}")

# Words a field answer may carry besides its codes: the label of the standard and of the code kind.
_LABEL_WORDS = frozenset({"dti", "dtis", "ffg", "iso", "24165", "code", "codes"})
_SEPARATORS = re.compile(r"[\s,;/|]+")
_TRIM = "():.[]"

# A label in a draft without field numbers. The FFG label is tried first, as it contains the DTI label.
_FFG_LABEL = (
    r"(?:FFG[\s-]*DTIs?"
    r"|functionally[\s-]+fungible[\s-]+group(?:[\s-]+digital[\s-]+token[\s-]+identifiers?)?(?:[\s-]*\(FFG(?:[\s-]*DTI)?\))?)"
)
_DTI_LABEL = r"(?:digital[\s-]+token[\s-]+identifiers?(?:[\s-]*\(DTIs?\))?|DTIs?)"
_LABELLED = re.compile(
    rf"(?<![\w-])(?:(?P<ffg>{_FFG_LABEL})|(?P<dti>{_DTI_LABEL}))(?![\w-])"
    r"(?:\s*\(ISO\s*24165\))?(?:\s+codes?)?(?:\s+(?:is|are|ist|lautet|lauten))?\s*[:=]?\s*"
    r"(?P<code>[^\s,;()]*)",
    re.IGNORECASE,
)


def field_codes(answer: str) -> tuple[list[str], bool]:
    """The codes of a DTI field's answer, and whether it holds anything else besides label words.

    An empty answer, a placeholder or "N/A" holds no code and nothing else. Codes may be separated by
    spaces, line breaks, commas, semicolons, slashes or bars; a word that is no code of the {DTI} format
    counts as anything else, so a field that names the network beside its code goes to review.
    """
    answer = answer.strip()
    if not answer or is_placeholder(answer) or is_not_applicable(answer):
        return [], False
    codes: list[str] = []
    other = False
    for token in _SEPARATORS.split(answer):
        token = token.strip(_TRIM)
        if not token or token.lower() in _LABEL_WORDS:
            continue
        if DTI_CODE.fullmatch(token):
            codes.append(token)
        else:
            other = True
    return codes, other


def labelled_codes(text: str) -> tuple[list[str], list[str], set[str]]:
    """The DTI and FFG DTI codes a section gives after a label, and the label kinds not followed by one.

    Returns (dti codes, ffg codes, kinds) where kinds holds "dti" or "ffg" for every label whose next
    word is no code of the {DTI} format. Prose that names a DTI ("no DTI has been assigned") counts as
    such a label, so it sends the rule to review rather than to pass.
    """
    dti: list[str] = []
    ffg: list[str] = []
    unfollowed: set[str] = set()
    for match in _LABELLED.finditer(text):
        kind = "ffg" if match.group("ffg") else "dti"
        code = match.group("code").strip(_TRIM)
        if DTI_CODE.fullmatch(code):
            (ffg if kind == "ffg" else dti).append(code)
        else:
            unfollowed.add(kind)
    return dti, ffg, unfollowed
