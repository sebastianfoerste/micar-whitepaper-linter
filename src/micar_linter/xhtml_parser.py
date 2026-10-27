"""XHTML text extraction, section mapping and the unpacking of saved iXBRL viewer pages."""

from __future__ import annotations

import base64
import binascii
import io
import re
import zlib
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


def _parse(source: Path | bytes, huge_tree: bool = False) -> etree._ElementTree:
    document = io.BytesIO(source) if isinstance(source, bytes) else str(source)
    return etree.parse(document, etree.HTMLParser(encoding="utf-8", huge_tree=huge_tree))


def _is_fully_bold(elem: etree._Element, text: str) -> bool:
    """True if the element is a b/strong, or its whole text sits inside b/strong children."""
    if elem.tag in ("b", "strong"):
        return True
    if elem.tag not in ("p", "li", "div"):
        return False
    bold = "".join("".join(b.itertext()) for b in elem.xpath("./b | ./strong"))
    return re.sub(r"\s+", " ", bold).strip() == text


def is_script_packed(source: Path | bytes) -> bool:
    """True if the page shows next to no text but carries a script large enough to hold a document."""
    # Without huge_tree, libxml2 drops a text node above about 10 million characters, script content included.
    root = _parse(source, huge_tree=True).getroot()
    if root is None:
        return False
    if not any(len("".join(script.itertext())) > SCRIPT_PAYLOAD_CHARS for script in root.iter("script")):
        return False
    visible = root.xpath(
        "//text()[not(ancestor::head or ancestor::script or ancestor::style"
        " or ancestor::noscript or ancestor::template)]"
    )
    return len(" ".join(visible).split()) < MAX_PACKED_PAGE_WORDS


def unpack_script_payload(source: Path | bytes, limit: int = MAX_UNPACKED_BYTES) -> bytes | None:
    """Return the markup a script-packed page carries as a base64 string, or None if it carries none.

    Raises PackedPageTooLarge when that markup exceeds limit. Inflation stops one byte past the
    limit, so a compressed payload cannot expand without bound.
    """
    root = _parse(source, huge_tree=True).getroot()
    if root is None:
        return None
    for script in root.iter("script"):
        # A JSON string may escape "/" as "\/".
        text = "".join(script.itertext()).replace("\\/", "/")
        candidates = [match.group(2) for match in _BASE64_LITERAL.finditer(text)]
        bare = "".join(text.split())
        if _BASE64_TEXT.fullmatch(bare):
            candidates.append(bare)
        for literal in candidates:
            document = _decode_payload(literal, limit)
            if document is not None:
                return document
    return None


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
        return _checked(data, True, limit)
    try:
        return _inflate(data, -zlib.MAX_WBITS, limit)
    except zlib.error:
        return None


def _inflate(data: bytes, wbits: int, limit: int) -> bytes | None:
    inflater = zlib.decompressobj(wbits)
    document = inflater.decompress(data, limit + 1)
    return _checked(document, inflater.eof, limit)


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
        tree = _parse(source)
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
