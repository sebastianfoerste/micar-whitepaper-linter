"""Readable English citations and EUR-Lex links for rule citations.

Rules keep their canonical German citation (``Rule.citation``). This module
renders the same reference in English EU drafting style, for example
``Art. 6 Abs. 7 MiCAR`` becomes ``Art. 6(7) MiCAR`` and ``Anhang I Teil A``
becomes ``Annex I, Part A``. The conversion is a fixed term mapping with no
legal interpretation; ``tests/test_citations.py`` pins it for every rule.

Links point to the cited act on EUR-Lex (act level, English), not to a
specific article: article anchors are only added once verified.
"""

from __future__ import annotations

import re

# Act-level ELI links for every act the rules cite.
ACT_URLS: dict[str, str] = {
    "MiCAR": "https://eur-lex.europa.eu/eli/reg/2023/1114/oj/eng",
    "VO (EU) 2024/2984": "https://eur-lex.europa.eu/eli/reg_impl/2024/2984/oj/eng",
    "VO (EU) 2025/422": "https://eur-lex.europa.eu/eli/reg_del/2025/422/oj/eng",
    "Richtlinie 2009/110/EG": "https://eur-lex.europa.eu/eli/dir/2009/110/oj/eng",
}

_ORDINALS = {"1": "first", "2": "second", "3": "third", "4": "fourth"}


def _points(match: re.Match[str]) -> str:
    numbers = match.group(1).replace(" und ", " and ")
    word = "points" if ("," in numbers or " and " in numbers) else "point"
    return f", {word} {numbers}"


def to_english(citation: str) -> str:
    """Render a canonical German citation in English EU drafting style."""
    text = citation
    # Art. 6 Abs. 7 -> Art. 6(7)
    text = re.sub(r"Art\. (\d+[a-z]?) Abs\. (\d+[a-z]?)", r"Art. \1(\2)", text)
    # UAbs. 1 -> , first subparagraph
    text = re.sub(
        r" UAbs\. (\d)",
        lambda m: f", {_ORDINALS.get(m.group(1), m.group(1) + 'th')} subparagraph",
        text,
    )
    # Buchst. d -> , point (d)
    text = re.sub(r" Buchst\. ([a-z])", r", point (\1)", text)
    # Nr. 9, 15 und 16 -> , points 9, 15 and 16
    text = re.sub(r" Nr\. (\d+(?:(?:, | und )\d+)*)", _points, text)
    # Nr. 10 Buchst. c -> point 10(c)
    text = re.sub(r"point (\d+), point \(([a-z])\)", r"point \1(\2)", text)
    # Anhang Tabelle 3 Teil H -> Annex, Table 3, Part H
    text = re.sub(r"Anhang Tabelle (\d+)", r"Annex, Table \1", text)
    text = re.sub(r"Anhang ([IVX]+)", r"Annex \1", text)
    text = re.sub(r",? Teil ([A-Z])", r", Part \1", text)
    text = text.replace(" i.V.m. ", " in conjunction with ")
    text = text.replace("VO (EU)", "Regulation (EU)")
    text = text.replace("Richtlinie 2009/110/EG", "Directive 2009/110/EC")
    text = text.replace(" und ", " and ")
    return text


def render(citation: str, style: str = "en") -> str:
    return citation if style == "de" else to_english(citation)


def source_urls(citation: str) -> list[str]:
    """EUR-Lex links for the acts named in a citation, in order of appearance."""
    found = sorted((citation.find(name), url) for name, url in ACT_URLS.items() if name in citation)
    return [url for _, url in found]
