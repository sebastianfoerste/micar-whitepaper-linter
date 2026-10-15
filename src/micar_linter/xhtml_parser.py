"""XHTML text extraction and section mapping."""

from __future__ import annotations

import re
from pathlib import Path

from lxml import etree

from micar_linter.document import match_heading_to_section


def _is_fully_bold(elem: etree._Element, text: str) -> bool:
    """True if the element is a b/strong, or its whole text sits inside b/strong children."""
    if elem.tag in ("b", "strong"):
        return True
    if elem.tag not in ("p", "li", "div"):
        return False
    bold = "".join("".join(b.itertext()) for b in elem.xpath("./b | ./strong"))
    return re.sub(r"\s+", " ", bold).strip() == text


def load_from_xhtml(path: Path) -> dict[str, str]:
    """Parse an XHTML file and extract sections mapped by headings."""
    try:
        parser = etree.HTMLParser(encoding="utf-8")
        tree = etree.parse(str(path), parser=parser)
    except Exception as exc:
        raise ValueError(f"Failed to parse HTML/XHTML: {exc}") from exc

    sections: dict[str, list[str]] = {}
    current_keys = []

    # Select headings, paragraphs, list items, and leaf divs in document order
    elements = tree.xpath(
        "//h1 | //h2 | //h3 | //h4 | //h5 | //h6 | //p | //li | //div[not(div or p)]"
        # Standalone bold runs not nested in another selected block
        "| //b[not(ancestor::*[self::h1 or self::h2 or self::h3 or self::h4 or self::h5 or self::h6"
        " or self::p or self::li or self::div or self::b or self::strong])]"
        "| //strong[not(ancestor::*[self::h1 or self::h2 or self::h3 or self::h4 or self::h5 or self::h6"
        " or self::p or self::li or self::div or self::b or self::strong])]"
    )

    for elem in elements:
        text = "".join(elem.itertext()).strip()
        text = re.sub(r"\s+", " ", text)
        if not text:
            continue

        is_heading = False
        is_tag_heading = elem.tag in ("h1", "h2", "h3", "h4", "h5", "h6")
        is_bold_heading = len(text) < 120 and _is_fully_bold(elem, text)
        if is_tag_heading or is_bold_heading:
            is_heading = True

        if is_heading:
            matched_keys = match_heading_to_section(text)
            if matched_keys:
                current_keys = matched_keys
        else:
            if current_keys:
                for k in current_keys:
                    sections.setdefault(k, []).append(text)

    return {k: "\n".join(v) for k, v in sections.items()}
