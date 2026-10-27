"""XHTML text extraction, section mapping and the unpacking of saved iXBRL viewer pages."""

from __future__ import annotations

import base64
import binascii
import io
import re
import zlib
from collections.abc import Callable, Iterable, Iterator
from itertools import chain
from pathlib import Path

from lxml import etree

from micar_linter.document import match_heading_to_section

# A saved iXBRL viewer page packs the white paper into a script and writes it into the page
# only when a browser runs that script, so the file itself shows next to no text.
SCRIPT_PAYLOAD_CHARS = 10_000
MAX_PACKED_PAGE_WORDS = 50
# The packed document is read up to the size the playground accepts for an XHTML file.
MAX_UNPACKED_BYTES = 8 * 1024 * 1024
# A string literal of base64, or a data: URI of base64, long enough to hold a document.
_BASE64_LITERAL = re.compile(r"""(["'`])(?:data:[^,"'`]{0,100};base64,)?([A-Za-z0-9+/]{1024,}={0,2})\1""")
# A data script whose whole content is base64, without quotes.
_BASE64_TEXT = re.compile(r"[A-Za-z0-9+/]{1024,}={0,2}")


class PackedPageTooLarge(ValueError):
    """The document packed into a page unpacks to more than the limit."""


class SeveralPackedDocuments(ValueError):
    """The page packs more than one document, so which one is the white paper is unclear."""


def _parse(source: Path | bytes, huge_tree: bool = False) -> etree._ElementTree:
    document = io.BytesIO(source) if isinstance(source, bytes) else str(source)
    return etree.parse(document, etree.HTMLParser(encoding="utf-8", huge_tree=huge_tree))


# Elements a browser lays out on lines of their own, and <br>. Text runs on across every other
# element (span, a, b, i, ix:nonNumeric, ix:continuation and the like) without a space.
_BLOCK_TAGS = {
    "address", "article", "aside", "blockquote", "body", "br", "caption", "center", "dd", "details",
    "dialog", "dir", "div", "dl", "dt", "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2",
    "h3", "h4", "h5", "h6", "header", "hgroup", "hr", "html", "legend", "li", "main", "menu", "nav", "ol",
    "p", "pre", "search", "section", "summary", "table", "tbody", "td", "tfoot", "th", "thead", "tr", "ul",
}
# A field number of Implementing Regulation (EU) 2024/2984 ("A.1", "I.01", "05"), as numbered_fields
# reads it. A spacer can be the only gap between such a number and its label or the dash before the
# label, so the number never runs on into a letter or a dash.
_FIELD_NUMBER = re.compile(r"(?:[A-Z]{1,2}\.\d{1,2}|\d{2})[.:)]?")
_LABEL_START = re.compile(r"[^\W\d_]|[-\u2013\u2014]")
# pdf2htmlEX writes a shift inside a line as a span of class "_ _N" whose CSS rule moves the next
# glyph: "._N{width:7.6px;}", or "._N{margin-left:-1.1px;}" for kerning. It writes a space into a
# shift of an eighth of an em or more, its threshold for a gap between words; converters in its
# style leave that span empty too.
_WORD_GAP_EM = 0.125
_CSS_LENGTH = re.compile(r"\.(_[0-9a-z]+|fs[0-9a-z]+)\{(?:[^}]*;)?\s*(?:width|font-size):([\d.]+)px")


def mark_spacer_gaps(root: etree._Element) -> None:
    """Write a space into each empty pdf2htmlEX spacer that the page's CSS makes a gap between words."""
    lengths: dict[str, float] = {}
    for style in root.iter("{*}style"):
        for name, value in _CSS_LENGTH.findall(style.text or ""):
            lengths.setdefault(name, float(value))
    if not lengths:
        return
    for span in root.iter("{*}span"):
        classes = (span.get("class") or "").split()
        if "_" not in classes or span.text or len(span):
            continue
        width = next((lengths[name] for name in classes if name in lengths), 0.0)
        size = next(
            (
                lengths[name]
                for node in (span, *span.iterancestors())
                for name in (node.get("class") or "").split()
                if name.startswith("fs") and name in lengths
            ),
            None,
        )
        if size and width >= _WORD_GAP_EM * size:
            span.text = " "


def parse_html(source: Path | bytes) -> etree._ElementTree:
    """Parse an HTML or XHTML file, or markup unpacked from one, with the word gaps of its spacers marked."""
    tree = _parse(source)
    if (root := tree.getroot()) is not None:
        mark_spacer_gaps(root)
    return tree


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
    return not (_LABEL_START.match(piece) and _FIELD_NUMBER.fullmatch(text.rsplit(None, 1)[-1]))


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


def element_text(*elements: etree._Element, stop: Callable[[etree._Element], bool] | None = None) -> str:
    """The text of the elements on one line, joined as text_fragments joins it, without the text of
    any element for which ``stop`` is true."""
    return " ".join(fragment for fragment in text_fragments(elements, stop) if isinstance(fragment, str))


def _own_text(elem: etree._Element, selected: set[etree._Element]) -> str:
    """The text of a selected element without the selected elements nested in it, which the loader
    reads on their own, so that a list item holding paragraphs counts each paragraph once."""
    return element_text(elem, stop=lambda child: child is not elem and child in selected)


def _is_fully_bold(elem: etree._Element, text: str) -> bool:
    """True if the element is a b/strong, or its whole text sits inside b/strong children."""
    if elem.tag in ("b", "strong"):
        return True
    if elem.tag not in ("p", "li", "div"):
        return False
    # A <br> between bold runs breaks the line here as it does in the element's own text.
    return element_text(*elem.xpath("./b | ./strong | ./br")) == text


def is_script_packed(source: Path | bytes) -> bool:
    """True if the page shows next to no text but carries a script large enough to hold a document."""
    # Without huge_tree, libxml2 drops a text node above about 10 million characters, script content included.
    root = _parse(source, huge_tree=True).getroot()
    if root is None:
        return False
    if not any(len("".join(script.itertext())) > SCRIPT_PAYLOAD_CHARS for script in root.iter("script")):
        return False
    # Text in noscript or template counts as visible: such a page carries its white paper as text.
    visible = root.xpath("//text()[not(ancestor::head or ancestor::script or ancestor::style)]")
    return len(" ".join(visible).split()) < MAX_PACKED_PAGE_WORDS


def unpack_script_payload(source: Path | bytes, limit: int = MAX_UNPACKED_BYTES) -> bytes | None:
    """Return the markup a script-packed page carries as a base64 string, or None if it carries none.

    Raises PackedPageTooLarge when a markup payload exceeds limit, and SeveralPackedDocuments when
    the page packs more than one distinct document. Inflation stops one byte past the limit, so a
    compressed payload cannot expand without bound.
    """
    root = _parse(source, huge_tree=True).getroot()
    if root is None:
        return None
    documents: list[bytes] = []
    for script in root.iter("script"):
        # A JSON string may escape "/" as "\/".
        text = "".join(script.itertext()).replace("\\/", "/")
        candidates = [match.group(2) for match in _BASE64_LITERAL.finditer(text)]
        bare = "".join(text.split())
        if _BASE64_TEXT.fullmatch(bare):
            candidates.append(bare)
        for literal in candidates:
            document = _decode_payload(literal, limit)
            if document is not None and document not in documents:
                documents.append(document)
    if len(documents) > 1:
        raise SeveralPackedDocuments(f"The page packs {len(documents)} documents.")
    return documents[0] if documents else None


def _decode_payload(literal: str, limit: int) -> bytes | None:
    # Browsers decode base64 without its "=" padding, so restore the padding before decoding.
    digits = literal.rstrip("=")
    try:
        data = base64.b64decode(digits + "=" * (-len(digits) % 4), validate=True)
    except (binascii.Error, ValueError):
        return None
    # The payload is gzip or zlib (wbits with 32 added reads either header), the markup itself,
    # or raw deflate, which has no header and is tried last.
    try:
        return _inflate(data, zlib.MAX_WBITS | 32, limit)
    except zlib.error:
        pass
    if _is_markup(data):
        # Uncompressed markup carries no end marker of its own, so it must close the document;
        # the first of several chunks would otherwise pass for the whole white paper.
        return _checked(data, b"</html" in data[-4096:].lower(), limit)
    try:
        return _inflate(data, -zlib.MAX_WBITS, limit)
    except zlib.error:
        return None


def _inflate(data: bytes, wbits: int, limit: int) -> bytes | None:
    document = b""
    while True:
        inflater = zlib.decompressobj(wbits)
        document += inflater.decompress(data, limit + 1 - len(document))
        if len(document) > limit or not inflater.eof:
            return _checked(document, False, limit)
        data = inflater.unused_data
        # A gzip stream may hold several members in a row, and browser inflaters read them all.
        # Other bytes after the stream would be dropped, so the payload does not count as complete.
        if not data.startswith(b"\x1f\x8b"):
            return _checked(document, not data, limit)


def _checked(document: bytes, complete: bool, limit: int) -> bytes | None:
    if not _is_markup(document):
        return None
    if len(document) > limit:
        raise PackedPageTooLarge(f"The packed document exceeds {limit} bytes.")
    # A truncated stream would hide the end of the white paper.
    return document if complete else None


def _is_markup(document: bytes) -> bool:
    head = document[:65536].lstrip(b"\xef\xbb\xbf \t\r\n").lower()
    return head.startswith(b"<") and (b"<html" in head or b"<!doctype html" in head)


def load_from_xhtml(source: Path | bytes) -> dict[str, str]:
    """Parse an XHTML file, or markup unpacked from one, and extract sections mapped by headings."""
    try:
        tree = parse_html(source)
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

    selected = set(elements)
    for elem in elements:
        text = _own_text(elem, selected)
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
