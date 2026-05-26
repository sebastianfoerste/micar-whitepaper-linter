"""XHTML text extraction and section mapping."""

from __future__ import annotations

import re
from pathlib import Path
from lxml import etree
from micar_linter.document import match_heading_to_section


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
    elements = tree.xpath("//h1 | //h2 | //h3 | //h4 | //h5 | //h6 | //p | //li | //div[not(div or p)]")

    for elem in elements:
        text = "".join(elem.itertext()).strip()
        text = re.sub(r"\s+", " ", text)
        if not text:
            continue

        is_heading = False
        if elem.tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            is_heading = True
        elif elem.tag in ("b", "strong") and len(text) < 120:
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
