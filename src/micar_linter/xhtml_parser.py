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

from micar_linter.document import (
    _below_opener,
    _opening_level,
    _opening_number,
    _outline_number,
    _template_kind,
    _within_rights,
    match_heading_to_section,
    opens_statement,
    paragraph_statement_extent,
)

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
# The most characters _FIELD_NUMBER matches ("AB.12."). A word longer than that is no field number.
_FIELD_NUMBER_CHARS = 6
_LABEL_START = re.compile(r"[^\W\d_]|[-\u2013\u2014]")
# A word broken after its hyphen, such as "crypto-" before a <br>.
_BROKEN_AFTER_HYPHEN = re.compile(r"[^\W\d_]-\s*$")
# Stands in the text flow for a <br>, a line break inside a block.
_LINE_BREAK = object()
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
) -> Iterator[str | etree._Element | object | None]:
    """Text nodes in document order, None where a block element breaks the line, _LINE_BREAK for a
    <br>, and each element for which ``stop`` is true in place of its content."""
    if stop is not None and stop(element):
        yield element
        return
    # A comment or processing instruction shows no text; its tail belongs to the parent.
    if not isinstance(element.tag, str):
        return
    tag = element.tag.rsplit("}", 1)[-1].lower()
    if tag == "br":
        yield _LINE_BREAK
        return
    block = tag in _BLOCK_TAGS
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
    """Whether the text node ``piece`` continues the word that ``text`` ends with.

    Only the last _FIELD_NUMBER_CHARS + 1 characters of ``text`` are read: a word that fills them is longer
    than any field number. So the time does not grow with the length of the word, which a run of inline
    elements can make as long as the document (`<span>LEI</span>` repeated).
    """
    if not text or text[-1].isspace() or piece[:1].isspace():
        return False
    word = text[-(_FIELD_NUMBER_CHARS + 1) :].rsplit(None, 1)[-1]
    return not (_LABEL_START.match(piece) and _FIELD_NUMBER.fullmatch(word))


def text_fragments(
    elements: Iterable[etree._Element], stop: Callable[[etree._Element], bool] | None = None
) -> Iterator[str | etree._Element]:
    """Yield the text under the elements in document order, in fragments with collapsed whitespace.

    Text nodes that meet inside a word make one fragment, so an empty spacer span inside a word
    ("Financ<span class="_ _0"></span>ial", as pdf2htmlEX and similar PDF conversions write it)
    leaves the word whole. Whitespace, a block element, <br> and the gap after a field number end
    a fragment. A word broken after its hyphen at a <br> ("crypto-" / "asset") is joined with its
    hyphen, as at a line end in a PDF, DOCX or Markdown draft. An element for which ``stop`` is true
    is yielded in place of its content.
    """
    fragment = ""
    rejoin = False
    pieces = (piece for element in elements for piece in _text_flow(element, stop))
    # The closing None flushes the last fragment.
    for piece in chain(pieces, [None]):
        if piece is _LINE_BREAK and _BROKEN_AFTER_HYPHEN.search(fragment):
            rejoin = True
            continue
        if rejoin and isinstance(piece, str):
            # Whitespace around the <br> is source layout; the word goes on with the next text.
            if piece.strip():
                fragment, rejoin = fragment.rstrip() + piece.lstrip(), False
            continue
        rejoin = False
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


# Elements whose text a browser does not show on the page.
_UNSHOWN_TAGS = {"head", "script", "style", "template"}


def _unshown(element: etree._Element) -> bool:
    return isinstance(element.tag, str) and element.tag.rsplit("}", 1)[-1].lower() in _UNSHOWN_TAGS


def document_text(source: Path | bytes) -> str:
    """Every text of an XHTML or HTML document that the HTML parser keeps, outside its head, scripts, styles
    and templates, a line per block element and <br>, with each run of whitespace as one space.

    Unlike the section loader, this reads every element: table cells, definition lists, spans, sections
    and hidden iXBRL facts included, and text that CSS hides. The parser drops CDATA sections and leaves an
    entity that the document declares in its own DTD unexpanded, so neither is read. Text nodes join as
    text_fragments joins them: inside a word they run on, and a field number ("A.1") stays apart from the
    label after it.
    """
    return document_texts(source)[0]


def document_texts(source: Path | bytes) -> tuple[str, str]:
    """document_text, and the same text as a browser shows it (_shown_flow), or "" where the two are the
    same. The document is parsed once for the two and walked twice.

    The text as shown only ever adds issues. Where reading it fails for any reason, it is "", so the file is
    read as it would be without it."""
    root = parse_html(source).getroot()
    if root is None:
        return "", ""
    text = _flow_lines(_text_flow(root, _unshown))
    try:
        shown = _flow_lines(_shown_flow(root, False))
    except Exception:
        return text, ""
    return text, shown if shown != text else ""


# The tokens of a style attribute as CSS reads them: a comment, which runs to "*/" or to the end; a
# string, which runs to its closing quote, a line end or the end; an escape; whitespace; a delimiter; or a
# run of other characters. Each token starts where the one before ends, so the attribute is read once.
_CSS_TOKEN = re.compile(
    r"""(?P<comment>/\*.*?(?:\*/|\Z))
    |(?P<string>"(?:[^"\\\n]|\\.)*(?:"|(?=\n)|\Z)|'(?:[^'\\\n]|\\.)*(?:'|(?=\n)|\Z))
    |(?P<escape>\\(?:(?P<hex>[0-9a-fA-F]{1,6})(?:\r\n|[ \t\n\r\f])?|.|\Z))
    |(?P<space>[ \t\n\r\f]+)
    |(?P<delim>[;:!(){}\[\]])
    |(?P<other>[^/"'\\;:!(){}\[\] \t\n\r\f]+|/)""",
    re.DOTALL | re.VERBOSE,
)
_CSS_WIDE = {"inherit", "initial", "unset", "revert", "revert-layer"}
# The values of display that CSS Display Level 3 defines, with the legacy and prefixed ones browsers
# accept, and those of visibility and content-visibility. A browser drops a declaration with another value.
_DISPLAY_OUTSIDE = {"block", "inline", "run-in"}
_DISPLAY_INSIDE = {"flow", "flow-root", "table", "flex", "grid", "ruby", "math"}
_DISPLAY_ONE = _DISPLAY_OUTSIDE | _DISPLAY_INSIDE | _CSS_WIDE | {
    "list-item", "contents", "none", "inline-block", "inline-table", "inline-flex", "inline-grid",
    "table-row-group", "table-header-group", "table-footer-group", "table-row", "table-cell",
    "table-column-group", "table-column", "table-caption", "ruby-base", "ruby-text", "ruby-base-container",
    "ruby-text-container", "-webkit-box", "-webkit-inline-box", "-webkit-flex", "-webkit-inline-flex",
    "-moz-box", "-moz-inline-box", "-ms-flexbox", "-ms-inline-flexbox", "-ms-grid", "-ms-inline-grid",
}
_STYLE_VALUES = {
    "visibility": {"visible", "hidden", "collapse"} | _CSS_WIDE,
    "content-visibility": {"visible", "auto", "hidden"} | _CSS_WIDE,
}


def _valid_display(keywords: list[str]) -> bool:
    """Whether the keywords are a value of display: one keyword, or an outer display, an inner display and
    list-item, each at most once, list-item only with flow or flow-root inside."""
    if len(keywords) == 1:
        return keywords[0] in _DISPLAY_ONE
    outside = [k for k in keywords if k in _DISPLAY_OUTSIDE]
    inside = [k for k in keywords if k in _DISPLAY_INSIDE]
    items = [k for k in keywords if k == "list-item"]
    return (
        len(outside) <= 1
        and len(inside) <= 1
        and len(items) <= 1
        and len(outside) + len(inside) + len(items) == len(keywords)
        and (not items or inside in ([], ["flow"], ["flow-root"]))
    )


def _css_words(tokens: list[tuple[str, str]]) -> list[str] | None:
    """The words of a declaration's name or value, ASCII letters in lower case, or None where it holds a
    string or a delimiter. Whitespace and comments part words; an escaped character never does."""
    words: list[str] = []
    word = ""
    for kind, text in tokens:
        if kind in ("string", "delim"):
            return None
        if kind in ("space", "comment"):
            if word:
                words.append(word)
            word = ""
        else:
            word += text
    if word:
        words.append(word)
    return [word.lower() if word.isascii() else word for word in words]


def _declarations(style: str) -> dict[str, str]:
    """The display, visibility and content-visibility that a style attribute sets, as a browser reads it:
    a declaration whose value is invalid is dropped, the last valid one counts, and one marked !important
    wins over those without the mark. Comments, strings and escapes are read as CSS reads them: an escape
    stands for its character, which then is no delimiter. Unlike a browser, this also drops a value that
    holds a function, so a custom property given through var() is not applied (a limit, ADR 0007)."""
    found: dict[str, tuple[str, bool]] = {}
    declaration: list[tuple[str, str]] = []
    depth = 0

    def read() -> None:
        colon = next((i for i, token in enumerate(declaration) if token == ("delim", ":")), None)
        if colon is None:
            return
        names = _css_words(declaration[:colon])
        if names not in (["display"], ["visibility"], ["content-visibility"]):
            return
        name = names[0]
        value = declaration[colon + 1 :]
        important = False
        marks = [i for i, token in enumerate(value) if token == ("delim", "!")]
        if marks:
            if len(marks) > 1 or _css_words(value[marks[0] + 1 :]) != ["important"]:
                return
            value, important = value[: marks[0]], True
        keywords = _css_words(value)
        if not keywords:
            return
        if name == "display":
            if not _valid_display(keywords):
                return
        elif len(keywords) > 1 or keywords[0] not in _STYLE_VALUES[name]:
            return
        if important or not found.get(name, ("", False))[1]:
            found[name] = (" ".join(keywords), important)

    for match in _CSS_TOKEN.finditer(style):
        kind, text = match.lastgroup or "other", match.group()
        if kind == "escape":
            code = match.group("hex")
            number = int(code, 16) if code is not None else -1
            if code is None:
                text = text[1:] or "\ufffd"
            elif 0 < number <= 0x10FFFF and not 0xD800 <= number <= 0xDFFF:
                text = chr(number)
            else:
                text = "\ufffd"
            kind = "other"
        elif kind == "delim":
            if text in "([{":
                depth += 1
            elif text in ")]}":
                depth = max(depth - 1, 0)
            elif text == ";" and not depth:
                read()
                declaration.clear()
                continue
        declaration.append((kind, text))
    read()
    return {name: value for name, (value, _) in found.items()}


def _inline_style(element: etree._Element) -> dict[str, str]:
    """The display, visibility and content-visibility that an element's style attribute sets."""
    style = element.get("style")
    return _declarations(style) if style else {}


# Elements that the HTML user agent style sheet sets to display:none, which a display that the style
# attribute sets undoes, as it undoes the hidden attribute (and <dialog>, while it has no open attribute).
_UA_HIDDEN_TAGS = {
    "area", "base", "basefont", "datalist", "link", "meta", "noembed", "noframes", "param", "rp", "title",
}
# Elements whose content the reading leaves out, whatever their style: <noscript>, which the user agent
# style sheet hides with !important where scripts run, and the content of replaced elements, which a browser
# shows only as fallback content (an <object> without a resource it can show, a <canvas> where scripts are
# off); there it is a false Review, which fails safe.
_UNRENDERED_CONTENT_TAGS = {"noscript", "iframe", "canvas", "object", "video", "audio", "embed"}
# SVG elements that are not rendered where they stand, in lower case as the HTML parser reads them.
_SVG_UNRENDERED_TAGS = {
    "desc", "title", "metadata", "defs", "symbol", "clippath", "mask", "pattern", "marker", "lineargradient",
    "radialgradient", "filter", "style", "script",
}


def _local_name(element: etree._Element) -> str:
    return element.tag.rsplit("}", 1)[-1].lower() if isinstance(element.tag, str) else ""


def _shown_flow(
    element: etree._Element, invisible: bool, svg: bool = False
) -> Iterator[str | etree._Element | object | None]:
    """_text_flow without what a browser does not show by the document's own markup.

    Left out with all their content and line breaks: the head, scripts, styles and templates; <noscript>
    and the content of <iframe>, <canvas>, <object>, <video>, <audio> and <embed>; inside an <svg>, the
    elements an SVG drawing does not render where they stand (_SVG_UNRENDERED_TAGS); an element that its
    style attribute sets to display:none or, inside an <svg>, whose display attribute is none where the
    style attribute sets no display; and, where neither sets a display, an element with the hidden
    attribute (other than until-found), one of _UA_HIDDEN_TAGS and a <dialog> without the open attribute.
    Of a <details> without the open attribute only the first <summary> child is read. The content of an
    element whose style attribute sets content-visibility:hidden, or that carries hidden="until-found"
    where the style attribute sets no content-visibility, is left out. The text of an element that its
    style attribute sets to visibility:hidden or collapse (inside an <svg>, its visibility attribute where
    the style attribute sets none), or that inherits that visibility from an ancestor without setting
    visibility:visible itself, keeps its place on the line, so it stands as a space; the line breaks of its
    elements stay. The style attribute is read as _declarations reads it; revert and revert-layer count as
    no value, initial as visible and, like unset and inherit, as a display other than none. Style sheets
    (<style>, linked CSS and their classes), every other property (opacity, colour, font size, position,
    clipping, transforms) and scripts are not read."""
    tag = _local_name(element)
    if not tag or tag in _UNSHOWN_TAGS or tag in _UNRENDERED_CONTENT_TAGS:
        return
    if svg and tag in _SVG_UNRENDERED_TAGS:
        return
    style = _inline_style(element)
    display = style.get("display")
    if display in ("revert", "revert-layer"):
        display = None
    if display is None and svg:
        attribute = (element.get("display") or "").strip().lower()
        display = attribute if attribute in _DISPLAY_ONE - _CSS_WIDE else None
    hidden = element.get("hidden")
    until_found = hidden is not None and hidden.lower() == "until-found"
    if display == "none" or (
        display is None
        and (
            (hidden is not None and not until_found)
            or tag in _UA_HIDDEN_TAGS
            or (tag == "dialog" and element.get("open") is None)
        )
    ):
        return
    if tag == "br":
        yield _LINE_BREAK
        return
    visibility = style.get("visibility")
    if visibility is None and svg:
        visibility = (element.get("visibility") or "").strip().lower()
    if visibility in ("hidden", "collapse"):
        invisible = True
    elif visibility in ("visible", "initial"):
        invisible = False
    content_visibility = style.get("content-visibility")
    if content_visibility in (None, "revert", "revert-layer"):
        skip_content = until_found
    else:
        skip_content = content_visibility == "hidden"
    svg = (svg or tag == "svg") and tag != "foreignobject"
    block = tag in _BLOCK_TAGS
    if block:
        yield None
    if skip_content:
        pass
    elif tag == "details" and element.get("open") is None:
        summary = next((child for child in element if _local_name(child) == "summary"), None)
        if summary is not None:
            yield from _shown_flow(summary, invisible, svg)
    else:
        if element.text:
            yield " " if invisible else element.text
        for child in element:
            yield from _shown_flow(child, invisible, svg)
            if child.tail:
                yield " " if invisible else child.tail
    if block:
        yield None


def _flow_lines(flow: Iterable[str | etree._Element | object | None]) -> str:
    """The text of a flow, a line per block element and <br>, joined as document_text describes."""
    lines: list[str] = []
    line: list[str] = []
    # The last character of the line and the end of the text after its last whitespace, as far back as
    # _inside_word reads, so that a long word is not copied for every piece of it.
    last = word = ""
    for piece in flow:
        if isinstance(piece, str):
            if not piece:
                continue
            joins = bool(last) and not last.isspace() and not piece[0].isspace()
            if joins and not _inside_word(word, piece):
                line.append(" ")
                joins = False
            line.append(piece)
            last = piece[-1]
            tail = "" if last.isspace() else piece.rsplit(None, 1)[-1]
            word = (word + tail if joins and tail == piece else tail)[-(_FIELD_NUMBER_CHARS + 1) :]
        elif piece is None or piece is _LINE_BREAK:
            if text := " ".join("".join(line).split()):
                lines.append(text)
            line, last, word = [], "", ""
    if text := " ".join("".join(line).split()):
        lines.append(text)
    return "\n".join(lines)


def load_from_xhtml(source: Path | bytes) -> dict[str, str]:
    """Parse an XHTML file, or markup unpacked from one, and extract sections mapped by headings.

    A heading that names a section opens it, and a heading that names none leaves the current section
    open. A sub-heading that names the redemption alone keeps the rights section open (see
    _within_rights in document.py).
    """
    try:
        tree = parse_html(source)
    except Exception as exc:
        raise ValueError(f"Failed to parse HTML/XHTML: {exc}") from exc

    sections: dict[str, list[str]] = {}
    current_keys: list[str] = []
    # The template numbering, the outline number and the level of the heading that opened the current
    # section (see blocks below).
    opener: str | None = None
    opener_number: str | None = None
    section_level: float | None = None

    # Select headings, paragraphs, list items, and leaf divs in document order
    elements = tree.xpath(
        "//h1 | //h2 | //h3 | //h4 | //h5 | //h6 | //p | //li | //div[not(div or p)]"
        # Standalone bold runs not nested in another selected block
        "| //b[not(ancestor::*[self::h1 or self::h2 or self::h3 or self::h4 or self::h5 or self::h6"
        " or self::p or self::li or self::div or self::b or self::strong])]"
        "| //strong[not(ancestor::*[self::h1 or self::h2 or self::h3 or self::h4 or self::h5 or self::h6"
        " or self::p or self::li or self::div or self::b or self::strong])]"
    )

    # Each non-empty block: its own text, whether it is a heading tag, whether it is entirely bold, and its
    # level as a heading: 1 to 6 for h1 to h6, and 7 for a standalone bold run, which ranks below them.
    selected = set(elements)
    blocks: list[tuple[str, bool, bool, int]] = []
    for elem in elements:
        text = _own_text(elem, selected)
        if text:
            is_tag_heading = elem.tag in ("h1", "h2", "h3", "h4", "h5", "h6")
            level = int(elem.tag[1]) if is_tag_heading else 7
            blocks.append((text, is_tag_heading, _is_fully_bold(elem, text), level))
    texts = [text for text, *_ in blocks]
    statement_end = 0

    for index, (text, is_tag_heading, is_bold, level) in enumerate(blocks):
        is_bold_heading = len(text) < 120 and is_bold
        if index < statement_end or opens_statement(texts, index):
            # The Art. 6(3) / 51(3) statement carries no heading of its own, and its sentences may sit
            # in separate blocks. After a bold first block, a bold label is a heading only where it names
            # a section, as a statement may be set in bold a sentence per paragraph.
            if index >= statement_end:
                statement_end = paragraph_statement_extent(
                    texts,
                    index,
                    lambda i, bold=is_bold: (
                        blocks[i][1]
                        or (
                            blocks[i][2]
                            and len(texts[i]) < 120
                            and (not bold or bool(match_heading_to_section(texts[i])))
                        )
                    ),
                )
            sections.setdefault("not_approved_statement", []).append(text)
            continue

        if is_tag_heading or is_bold_heading:
            matched_keys = match_heading_to_section(text)
            kind, number = _template_kind(text), _outline_number(text)
            if _within_rights(
                matched_keys,
                current_keys,
                _below_opener(kind, level, number, opener, section_level, opener_number),
            ):
                current_keys = [*current_keys, *(key for key in matched_keys if key not in current_keys)]
            elif matched_keys:
                in_section = bool(set(matched_keys) & set(current_keys))
                section_level = _opening_level(level, section_level, in_section)
                current_keys = matched_keys
                opener, opener_number = kind, _opening_number(number, opener_number)
        else:
            if current_keys:
                for k in current_keys:
                    sections.setdefault(k, []).append(text)

    return {k: "\n".join(v) for k, v in sections.items()}
