"""Placeholder text that a draft leaves where an answer is still to come."""

from __future__ import annotations

import re

# "TBD", "TBC", "to be confirmed" and "to be determined" in any case, and the "[●]" or "[•]" blank of
# legal drafts (the brackets are punctuation, so the bullet alone is the token).
_PLACEHOLDER = re.compile(r"\b(?:tbd|tbc|to\s+be\s+(?:confirmed|determined))\b|[●•]", re.I)


def is_placeholder(text: str) -> bool:
    """True if the text holds a placeholder and nothing else but punctuation: "TBD.", "[●]", "TBC / TBD"."""
    return bool(_PLACEHOLDER.search(text)) and not re.search(r"\w", _PLACEHOLDER.sub("", text))
