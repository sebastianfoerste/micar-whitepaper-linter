"""XHTML text extraction and section mapping."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Iterator
from itertools import chain
from pathlib import Path

from lxml import etree

from micar_linter.document import match_heading_to_section

# Elements a browser lays out on lines of their own, and <br>. Text runs on across every other
# element (span, a, b, i, ix:nonNumeric, ix:continuation and the like) without a space.
_BLOCK_TAGS = {
    "address", "article", "aside", "blockquote", "body", "br", "caption", "center", "dd", "details",
    "dialog", "dir", "div", "dl", "dt", "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2",
    "h3", "h4", "h5", "h6", "header", "hgroup", "hr", "html", "legend", "li", "main", "menu", "nav", "ol",
    "p", "pre", "search", "section", "summary", "table", "tbody", "td", "tfoot", "th", "thead", "tr", "ul",
}
# A field number of Implementing Regulation (EU) 2024/2984 ("A.1", "I.01", "05"), as numbered_fields
# reads it. A spacer can be the only gap between such a number and its label, so the number never
# runs on into a letter.
_FIELD_NUMBER = re.compile(r"(?:[A-Z]{1,2}\.\d{1,2}|\d{2})[.:)]?")


def _text_flow(
    element: etree._Element, stop: Callable[[etree._Element], bool] | None
) -> Iterator[str | etree._Element | None]:
    """Text nodes in document order, None where a block element or <br> breaks the line, and
    each element for which ``stop`` is true in place of its content."""
    if stop is not None and stop(element):
        yield element
        return
    # A comment or processing instruction shows no text; its tail belongs to the parent.
    if not isinstance(element.tag, str):
        return
    block = element.tag.rsplit("}", 1)[-1].lower() in _BLOCK_TAGS
    if block:
        yield None
    if element.text:
        yield element.text
    for child in element:
        yield from _text_flow(child, stop)
        if child.tail:
            yield child.tail
    if block:
        yield None


def _inside_word(text: str, piece: str) -> bool:
    """Whether the text node ``piece`` continues the word that ``text`` ends with."""
    if not text or text[-1].isspace() or piece[:1].isspace():
        return False
    return not (piece[:1].isalpha() and _FIELD_NUMBER.fullmatch(text.rsplit(None, 1)[-1]))


def text_fragments(
    elements: Iterable[etree._Element], stop: Callable[[etree._Element], bool] | None = None
) -> Iterator[str | etree._Element]:
    """Yield the text under the elements in document order, in fragments with collapsed whitespace.

    Text nodes that meet inside a word make one fragment, so an empty spacer span inside a word
    ("Financ<span class="_ _0"></span>ial", as pdf2htmlEX and similar PDF conversions write it)
    leaves the word whole. Whitespace, a block element, <br> and the gap after a field number end
    a fragment. An element for which ``stop`` is true is yielded in place of its content.
    """
    fragment = ""
    pieces = (piece for element in elements for piece in _text_flow(element, stop))
    # The closing None flushes the last fragment.
    for piece in chain(pieces, [None]):
        if isinstance(piece, str) and _inside_word(fragment, piece):
            fragment += piece
            continue
        if text := " ".join(fragment.split()):
            yield text
        fragment = piece if isinstance(piece, str) else ""
        if isinstance(piece, etree._Element):
            yield piece


def element_text(*elements: etree._Element) -> str:
    """The text of the elements on one line, joined as text_fragments joins it."""
    return " ".join(fragment for fragment in text_fragments(elements) if isinstance(fragment, str))


def _is_fully_bold(elem: etree._Element, text: str) -> bool:
    """True if the element is a b/strong, or its whole text sits inside b/strong children."""
    if elem.tag in ("b", "strong"):
        return True
    if elem.tag not in ("p", "li", "div"):
        return False
    # A <br> between bold runs breaks the line here as it does in the element's own text.
    return element_text(*elem.xpath("./b | ./strong | ./br")) == text


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
        text = element_text(elem)
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
