"""Placeholder text that a draft leaves where an answer is still to come."""

from __future__ import annotations

import re

# Draft markers in any case. Brackets and dots are punctuation, so "[TBD]" and "t.b.d." reduce to the token.
_PLACEHOLDER = re.compile(
    # "TBA", "TBC", "TBD", "t.b.d.", "T. B. C."
    r"\bt\.?\s?b\.?\s?[acd]\b"
    r"|\bto\s+be\s+(?:announced|advised|confirmed|determined|provided)\b"
    # The "[●]" or "[•]" blank of legal drafts, an ellipsis ("[...]", "[…]") and "XX", "XXXX".
    r"|[●•…]|\.{3}|\bx{2,}\b"
    # "[insert date]", "[Insert name of the issuer]".
    r"|\[\s*insert\b[^\]]*\]"
    # German drafts: "noch offen", "folgt", "wird nachgereicht", "N.N.".
    r"|\bnoch\s+offen\b|\bfolgt\b|\bwird\s+nachgereicht\b|\bn\.\s?n\.",
    re.I,
)
# "N/A", "n. a.", "not applicable", "none", "nil" or a dash: the field is marked as not applying. German
# drafts write "entfällt", "nicht anwendbar", "nicht zutreffend", "keine" or "keine Angabe" ("k. A.").
_NOT_APPLICABLE = re.compile(
    r"^(?:n\s*/?\s*a|n\.\s?a|not\s+applicable|none|nil|[-\u2013\u2014]+"
    r"|entf(?:ä|ae)llt|nicht\s+(?:anwendbar|zutreffend)|keine(?:\s+angaben?)?|k\.\s?a)?\.?$",
    re.I,
)


def is_placeholder(text: str) -> bool:
    """True if the text holds a placeholder and nothing else but punctuation: "TBD.", "[●]", "TBC / TBA".

    A short real answer is not one: "TBC Bank", "XXL Logistics", "Date of notification: TBD" keep words.
    """
    return bool(_PLACEHOLDER.search(text)) and not re.search(r"\w", _PLACEHOLDER.sub("", text))


def is_not_applicable(text: str) -> bool:
    """True if the text is empty or says only that the item does not apply: "N/A", "none", "-", "entfällt"."""
    return bool(_NOT_APPLICABLE.match(text.strip()))
