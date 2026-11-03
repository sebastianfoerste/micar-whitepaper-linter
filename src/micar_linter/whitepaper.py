"""Input model for crypto-asset white papers."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Any


class WhitepaperType(StrEnum):
    """The three MiCAR white paper regimes.

    OTHER:  Art. 6 i.V.m. Anhang I MiCAR (crypto-assets other than ARTs and EMTs).
    ART:    Art. 19 i.V.m. Anhang II MiCAR (asset-referenced tokens).
    EMT:    Art. 51 i.V.m. Anhang III MiCAR (e-money tokens).
    """

    OTHER = "other"
    ART = "art"
    EMT = "emt"


@dataclass(frozen=True)
class Whitepaper:
    """A parsed white paper draft."""

    title: str
    type: WhitepaperType
    sections: dict[str, str]
    metadata: dict[str, Any]

    def section(self, key: str) -> str:
        value = self.sections.get(key, "")
        return value if isinstance(value, str) else str(value)

    @property
    def language(self) -> str:
        """Detect draft language (en or de).

        Checks metadata first (allows CLI/config override), then falls back to heuristics.
        """
        meta_lang = self.metadata.get("language")
        if meta_lang in ("en", "de"):
            return meta_lang
        # Every rule asks for the language, so the count is kept per section text.
        return _detected_language(tuple(self.sections.values()))


_GERMAN_WORDS = frozenset({"der", "die", "das", "und", "ist", "mit", "von", "eine", "oder"})
_ENGLISH_WORDS = frozenset({"the", "and", "is", "of", "with", "for", "that", "this", "or"})


@lru_cache(maxsize=8)
def _detected_language(texts: tuple[str, ...]) -> str:
    """de where the section texts hold more common German words than common English ones, en otherwise."""
    words = [w.strip(".,;:?!()[]{}") for w in " ".join(texts).lower().split()]
    de_count = sum(1 for w in words if w in _GERMAN_WORDS)
    en_count = sum(1 for w in words if w in _ENGLISH_WORDS)
    return "de" if de_count > en_count else "en"


def load_whitepaper(path: Path, whitepaper_type: WhitepaperType | None = None) -> Whitepaper:
    """Load and validate a white paper JSON, PDF, DOCX, Markdown, or XHTML file.

    whitepaper_type states the regime for document formats. A JSON draft carries its own "type".
    """
    suffix = path.suffix.lower()

    if suffix == ".json":
        return _load_json(path)
    if suffix in (".pdf", ".docx", ".xhtml", ".html", ".md"):
        return _load_document(path, suffix, whitepaper_type)
    raise SystemExit(f"Unsupported file format '{suffix}'. Expected: .json, .pdf, .docx, .xhtml, .html, .md")


_RESERVED_METADATA_KEYS = (
    # Set only by the document loaders: anchors and the iXBRL message read it, and anchors parse the file.
    "source_file",
    "ixbrl_validated",
    "ixbrl_issues",
    "extraction_notes",
    # Set by the XHTML loader for a saved iXBRL viewer page; the iXBRL message reads it.
    "script_packed_source",
    # Set by the XHTML loader for a numbered-field draft: the fields of each section that hold only a
    # placeholder, which the shared checks name, and the answer of every field, which the point rules read.
    "placeholder_fields",
    "numbered_fields",
    # Set by the document loaders: the whole text of the file, headings, tables and text in no section
    # included, which COMMON.LEI_CHECK_DIGITS reads besides the sections.
    "document_text",
    "reserve_characterisation_reviewed_by",
    "reserve_characterisation_reviewed_on",
)


def _section_text(value: Any) -> str:
    """The text of a JSON section value: a string as it is; a list as its items and an object as its entries
    ("key: value"), one per line, nested ones too; any other value as Python writes it ("123", "True").

    Python's representation of a list or an object ("['...', '...']") quoted each string with escapes, so a
    zero-width space or a line end inside it became the letters "\\u200b" or "\\n" next to the text around it.
    """
    if isinstance(value, str):
        return value
    if not isinstance(value, list | dict):
        return str(value)
    lines: list[str] = []
    # The values still to write, last first, each with the key it stands under (or "").
    pending: list[tuple[str, Any]] = [("", value)]
    while pending:
        key, item = pending.pop()
        if isinstance(item, list | dict):
            if key:
                lines.append(f"{key}:")
            children = item.items() if isinstance(item, dict) else (("", child) for child in item)
            pending.extend(reversed([(str(name), child) for name, child in children]))
        else:
            text = item if isinstance(item, str) else str(item)
            lines.append(f"{key}: {text}" if key else text)
    return "\n".join(lines)


def _load_json(path: Path) -> Whitepaper:
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except FileNotFoundError as exc:
        raise SystemExit(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise SystemExit("Whitepaper JSON must be an object.")
    if not isinstance(data.get("sections"), dict):
        raise SystemExit("Whitepaper JSON must contain a 'sections' object.")

    type_str = str(data.get("type", "other")).lower()
    try:
        wp_type = WhitepaperType(type_str)
    except ValueError as exc:
        raise SystemExit(
            f"Unknown whitepaper type '{type_str}'. Expected one of: "
            + ", ".join(t.value for t in WhitepaperType)
        ) from exc

    sections = {str(k): _section_text(v) for k, v in data["sections"].items()}
    metadata = {
        k: v
        for k, v in data.items()
        if k not in ("title", "type", "sections") and k not in _RESERVED_METADATA_KEYS
    }
    # A JSON draft is never the notification format, so iXBRL cannot have been validated.
    metadata["ixbrl_validated"] = False

    return Whitepaper(
        title=str(data.get("title", "Untitled white paper")),
        type=wp_type,
        sections=sections,
        metadata=metadata,
    )


VIEWER_PAGE_NOTE = (
    "This file is a saved iXBRL viewer page. The checks read the white paper text packed inside it, "
    "as the viewer renders it, and that rendering can differ from the XHTML document itself. "
    "Its iXBRL format was not checked."
)
VIEWER_EMPTY_NOTE = (
    "No section heading or numbered field was found in the white paper this page carries, "
    "so the content checks find no section text to read."
)


def _unpack_viewer_page(path: Path) -> bytes:
    """Return the markup a saved iXBRL viewer page writes into itself, or stop with the reason."""
    from micar_linter.xhtml_parser import (
        MAX_UNPACKED_BYTES,
        PackedPageTooLarge,
        SeveralPackedDocuments,
        is_script_packed,
        unpack_script_payload,
    )

    try:
        document = unpack_script_payload(path)
    except PackedPageTooLarge:
        raise SystemExit(
            f"{path.name} is a saved iXBRL viewer page whose packed white paper unpacks to more than "
            f"{MAX_UNPACKED_BYTES // (1024 * 1024)} MB, the limit for unpacking. Check the white paper's own "
            "XHTML file instead; for a published white paper, that is the file in the ESMA register."
        ) from None
    except SeveralPackedDocuments:
        raise SystemExit(
            f"{path.name} is a saved iXBRL viewer page that packs more than one document, so which one is "
            "the white paper is unclear. Check the white paper's own XHTML file instead; for a published "
            "white paper, that is the file in the ESMA register."
        ) from None
    if document is None or is_script_packed(document):
        raise SystemExit(
            f"{path.name} holds no white paper text that can be read: its content is packed inside a script, "
            "as in a saved iXBRL viewer page, in a form that cannot be unpacked. Check the white paper's own "
            "XHTML file instead; for a published white paper, that is the file in the ESMA register."
        )
    return document


# English phrases that name the regime of a draft that states none.
_ART_MARKERS = ("asset-referenced", "stabilisation mechanism", "reserve of assets")
_EMT_MARKERS = ("e-money token", "referenced currency", "safeguarding of funds")
# A white paper for another crypto-asset often says what its token is not: "not an asset-referenced token",
# "neither an asset-referenced token nor an e-money token", "crypto-assets other than asset-referenced tokens
# or e-money tokens" (the title of Title II MiCAR), "has no reserve of assets". A marker counts only where no
# negation stands before it in its clause, at most _NEGATION_REACH words away. A clause ends at a sentence
# mark, a colon inside a line or a word that turns the sentence ("but", "however"), and at the edge of a
# heading or a section. In a DOCX or PDF it also ends at a paragraph or line end before a line that starts a
# new sentence (with a capital letter or a digit, or with a name such as "xStable"), and after a line shaped
# like a title ("No Investor Compensation"); it runs on into a line that starts otherwise, since a DOCX may
# split a sentence over paragraphs and a PDF wraps its lines inside a sentence. In a DOCX, a PDF and a
# Markdown section that holds a list, the items of a list continue its lead-in (_line_pieces).
_NEGATION = re.compile(r"\b(?:not|no|neither|nor|never|without|other than|except|excluding|unlike)\b|n't\b")
_CLAUSE_END = re.compile(r"[.!?;:](?=\s|$)|\b(?:but|however|whereas|although|though|while)\b")
_NEGATION_REACH = 8
_NEGATION_LOOKBACK = 200
# A list item: a bullet or dash, or a list letter or number in lower case, before its text.
_LIST_ITEM = re.compile(
    r"(?:[-*\u2013\u2014\u2022\u2023\u2043\u00b7\u25aa\u25cf]|\(?(?:[a-z]|[ivx]{1,4}|\d{1,2})[.)])\s"
)
# The number or letter of a list marker, so that "(1)" and "(2)" are written alike.
_LIST_STYLE = re.compile(r"[0-9a-z]+")
# The end of a line that ends in a semicolon, perhaps with "or", "and" or "nor" after it: an item of a list.
_ITEM_END = re.compile(r";\s*(?:(?:or|and|nor)\s*)?$")
# The end of a line that ends as an item of a list ends: _ITEM_END, or a comma with "or", "and" or "nor"
# after it ("an asset-referenced token, or").
_ITEM_TAIL = re.compile(r";\s*(?:(?:or|and|nor)\s*)?$|,\s*(?:or|and|nor)\s*$", re.IGNORECASE)
_FIRST_WORD = re.compile(r"[^\W_]+")
_WORD = re.compile(r"[^\W_]+(?:['\u2019-][^\W_]+)*")
# Any marker of either regime.
_MARKER = re.compile("|".join(re.escape(marker) for marker in (*_ART_MARKERS, *_EMT_MARKERS)))
# A heading that ends in a negation, perhaps with a colon after it, leads into the line after it.
_ENDS_IN_NEGATION = re.compile(rf"(?:{_NEGATION.pattern})\W*$")
# Words that start a noun of a negation's own ("not covered by any compensation scheme"), and the
# negations that are such words themselves ("with no compensation scheme").
_DETERMINERS = frozenset({"a", "an", "any", "the"})
_DETERMINING_NEGATIONS = frozenset({"no", "without"})
# The kinds of line that regime inference reads (_line_units): body text, a heading, which is judged on its
# own words, and a heading by its shape alone that may be a list item (_guessed).
_BODY_LINE, _HEADING_LINE, _GUESSED = "body", "heading", "guessed"


def _negated(text: str, start: int) -> bool:
    """Whether a negation governs the marker at start of the lower-case text."""
    before = text[max(0, start - _NEGATION_LOOKBACK) : start]
    ends = list(_CLAUSE_END.finditer(before))
    clause = before[ends[-1].end() :] if ends else before
    negations = list(_NEGATION.finditer(clause))
    return bool(negations) and len(clause[negations[-1].end() :].split()) <= _NEGATION_REACH


def _names_regime(pieces: list[tuple[str, int]], markers: tuple[str, ...]) -> bool:
    """Whether one of the lower-case pieces holds, from its offset on, one of the markers with no negation
    before it. The text before the offset is the clause a piece continues."""
    for text, offset in pieces:
        for marker in markers:
            start = text.find(marker, offset)
            while start != -1:
                if not _negated(text, start):
                    return True
                start = text.find(marker, start + 1)
    return False


def _marked(text: str) -> bool:
    """Whether a lower-case text holds a marker of either regime. Only a piece whose own text holds one can
    name a regime, so no other piece is kept, and a text without one is not read line by line."""
    return _MARKER.search(text) is not None


def _joined(lines: list[str]) -> str:
    """Lines as one lower-case text with each run of whitespace as one space."""
    return " ".join(" ".join(lines).lower().split())


def _line_units(
    suffix: str, extracted: str, headings: tuple[str, ...], marked: tuple[str, ...] = ()
) -> list[tuple[str, str]]:
    """The lines of a DOCX's or PDF's extracted text, each with its kind (_line_kind for a line that is no
    heading of the loader). A DOCX heading paragraph is a heading, and so is a PDF heading line, or the two
    or three lines of a wrapped heading as one unit, that is set in a heading font (marked). A PDF heading
    in the body font, which the PDF reads as a heading by its shape alone, is body text where it ends as an
    item of a list ends (_ITEM_TAIL: "(EU) 2023/1114; or", a wrapped line of an item), and a guess where it
    may be a list item (_guessed)."""
    lines = extracted.split("\n")
    # A DOCX heading is one paragraph, one line of the extracted text.
    sizes = (1,) if suffix == ".docx" else (1, 2, 3)
    heading_texts = {" ".join(heading.lower().split()) for heading in headings}
    marked_texts = {" ".join(heading.lower().split()) for heading in marked}
    units: list[tuple[str, str]] = []
    index = 0
    while index < len(lines):
        size = next((k for k in sizes if _joined(lines[index : index + k]) in heading_texts), 0)
        if size:
            text = "\n".join(lines[index : index + size])
            if suffix == ".docx" or _joined(lines[index : index + size]) in marked_texts:
                kind = _HEADING_LINE
            elif _ITEM_TAIL.search(text):
                kind = _BODY_LINE
            else:
                kind = _GUESSED if _guessed(text) else _HEADING_LINE
            units.append((text, kind))
            index += size
        else:
            units.append((lines[index], _line_kind(lines[index])))
            index += 1
    return units


def _line_kind(line: str) -> str:
    """The kind of a line that the loader did not read as a heading: a heading where it is shaped like a
    title (_titled) and does not end as an item of a list ends ("Regulation (EU) 2023/1114; or" is a wrapped
    line of an item, "1. An Asset-Referenced Token; or" an item), body text otherwise."""
    return _HEADING_LINE if not _ITEM_TAIL.search(line) and _titled(line) else _BODY_LINE


def _titled(text: str) -> bool:
    """Whether a line is shaped like a title: a short label without sentence punctuation (at most twelve
    words) in which every word other than a short connective starts with a capital letter, such as a
    heading set in the body font of a PDF ("No Investor Compensation")."""
    from micar_linter.document import _BULLET, _is_label, _is_title_like

    text = text.strip()
    # A line that starts with a letter in lower case or a bullet is no title (the cheap tests first: most
    # lines of a list start so).
    return not text[:1].islower() and not _BULLET.match(text) and _is_title_like(text) and _is_label(text)


def _guessed(text: str) -> bool:
    """Whether a heading read by its shape alone may be a list item: it is one by its marker (_LIST_ITEM),
    and its words after the marker are not shaped like a title ("1. An asset-referenced token"). "3.
    Reserve of Assets" and "c) Reserve of Assets" are no guess: shaped like a title, they are headings."""
    from micar_linter.document import _is_title_like

    text = text.strip()
    item = _LIST_ITEM.match(text)
    return item is not None and not _is_title_like(text[item.end() :])


def _starts_sentence(text: str) -> bool:
    """Whether a line starts a new sentence: its first word starts with a capital letter or a digit
    ("100% of the reserve ...", "1 e-money token ..."), or holds a capital letter, as a name such as
    "xStable" does. A line that starts with a word in lower case ("an e-money token") continues the line
    before it."""
    first = _FIRST_WORD.search(text)
    if first is None:
        return False
    word = first.group()
    # A word all in lower case holds no capital letter, so the letters are looked at one by one only where
    # it is not.
    return not word[0].islower() or (not word.islower() and any(char.isupper() for char in word))


def _continued(previous: tuple[str, str, bool] | None) -> str:
    """The clause that a line continues after the previous line (its own clause, text and whether it is a
    heading), in lower case and at most _NEGATION_LOOKBACK characters.

    A heading is judged on its own words, so nothing continues it unless it ends in a negation ("For the
    purposes of MiCAR the token is not", which a PDF may read as a heading). A line that ends in a
    semicolon, perhaps with "or", "and" or "nor" after it ("an asset-referenced token; or"), is an item of a
    list, and the next line continues the clause that it continued. A colon at the end of a line introduces
    the line after it, so it ends no clause there.
    """
    if previous is None:
        return ""
    clause, text, heading = previous
    if heading:
        return text[-_NEGATION_LOOKBACK:] if _ENDS_IN_NEGATION.search(text) else ""
    text = text.rstrip()
    if _ITEM_END.search(text):
        return clause
    return f"{clause}\n{text.removesuffix(':')}"[-_NEGATION_LOOKBACK:]


def _opens(previous: tuple[str, str, bool] | None) -> bool:
    """Whether the previous line (its clause, text and whether it is a heading) leads into a list: it ends
    in a colon or a negation."""
    return previous is not None and bool(
        previous[1].rstrip().endswith(":") or _ENDS_IN_NEGATION.search(previous[1])
    )


def _settled(lead: str) -> bool:
    """Whether the last negation of a lead-in's clause negates words of its own, so that it is not about the
    items after it: "no" or "without" with a word after it ("Holders bear these risks, with no compensation
    scheme:"), or another negation with "a", "an", "any" or "the" and a word after that ("The following
    risks are not covered by any compensation scheme:").

    A lead-in still leads into its items where it ends in a negation or a connective ("..., the token is
    not covered by:", "... within the definition of:"), names "the following" after its negation ("... is
    not one of the following:"), or goes on after its negation between commas ("... is not, within the
    meaning of MiCAR,").
    """
    from micar_linter.document import _MINOR_WORD

    ends = list(_CLAUSE_END.finditer(lead))
    clause = lead[ends[-1].end() :] if ends else lead
    negations = list(_NEGATION.finditer(clause))
    if not negations:
        return False
    tail = clause[negations[-1].end() :]
    words = _WORD.findall(tail)
    if (
        not words
        or tail.lstrip().startswith(",")
        or {"following", "follows"} & set(words)
        or _MINOR_WORD.fullmatch(words[-1])
    ):
        return False
    return negations[-1].group() in _DETERMINING_NEGATIONS or any(word in _DETERMINERS for word in words[:-1])


def _lead(previous: tuple[str, str, bool] | None) -> str:
    """The clause the items of a list continue after the line before the list (see _continued): none where
    the lead-in's negation is not about them (_settled)."""
    lead = _continued(previous)
    return "" if _settled(lead) else lead


@lru_cache(maxsize=1024)
def _marker(item: str) -> tuple[str, frozenset[int] | None]:
    """A list item's marker (_LIST_ITEM) as its style, its number or letter written "#" so that "(1)" and
    "(2)" are written alike, and the places in a list it can stand for: a number's value, a letter's place
    in the alphabet and, for a Roman numeral, its value ("i" is the ninth letter or 1); None for a bullet or
    dash."""
    item = item.strip()
    style, marker = _LIST_STYLE.sub("#", item), item.strip("().")
    if marker.isdigit():
        return style, frozenset({int(marker)})
    if not marker.isalpha():
        return style, None
    values = {ord(marker) - ord("a") + 1} if len(marker) == 1 else set()
    if set(marker) <= set("ivx"):
        # A numeral before a larger one counts against it ("iv" is 4, "ix" 9).
        numerals = [{"i": 1, "v": 5, "x": 10}[char] for char in marker]
        values.add(sum(-n if n < max(numerals[i + 1 :], default=0) else n for i, n in enumerate(numerals)))
    return style, frozenset(values)


def _follows(item: tuple[str, frozenset[int] | None], before: tuple[str, frozenset[int] | None]) -> bool:
    """Whether a list item's marker (_marker) comes right after the marker of the item before it in one
    list: the two are written alike ("(2)" after "(1)", not "2." after "(1)"), and are the same bullet or
    dash, or the number or letter of the one is one more than that of the other ("b." after "a.", "ii."
    after "i.")."""
    if item[0] != before[0]:
        return False
    values, previous = item[1], before[1]
    return values is None or previous is None or any(value - 1 in previous for value in values)


def _item_text(text: str, item: re.Match[str]) -> str:
    """A list item's line without the full stop after its list letter or number ("1." reads as "1"), which
    would end the clause of the lead-in as a full stop does."""
    text = text.lstrip()
    marker = item.group().rstrip()
    return marker.removesuffix(".") + text[len(marker) :]


def _piece(clause: str, text: str) -> tuple[str, int]:
    """A piece of lower-case text after the clause it continues, with the offset where its own text starts."""
    return (f"{clause}\n{text}", len(clause) + 1) if clause else (text, 0)


@dataclass(slots=True)
class _List:
    """A list that _line_pieces reads: the clause its items continue (_lead), whether its lead-in ends in a
    colon or a negation, so that it governs an item that starts with a capital letter too, the marker of its
    last item, and whether one of its lines ends in a semicolon (_ITEM_END)."""

    lead: str
    opens: bool
    last: tuple[str, frozenset[int] | None]
    semicolons: bool = False


def _innermost(item: tuple[str, frozenset[int] | None], lists: list[_List]) -> int | None:
    """The place in lists, innermost first, of the list whose last item the item comes right after."""
    for depth in range(len(lists) - 1, -1, -1):
        if _follows(item, lists[depth].last):
            return depth
    return None


def _wraps(previous: tuple[str, str, bool] | None, text: str) -> bool:
    """Whether a line inside a list that starts as a sentence does ("Regulation (EU) 2023/1114; or",
    "(EU) 2023/1114; or", "Crypto-Assets Regulation; or") is a wrapped line of the item before it: it ends
    as an item ends (_ITEM_TAIL), or the line before it runs on into it (it ends with a comma, a hyphenated
    word part or a connective such as "of" or "in") without ending as an item ends ("; or", ", and")."""
    from micar_linter.document import _runs_on

    if _ITEM_TAIL.search(text):
        return True
    if previous is None or not previous[1].strip() or _ITEM_TAIL.search(previous[1]):
        return False
    return _runs_on(previous[1].rstrip())


def _regime_pieces(
    suffix: str,
    sections: dict[str, str],
    extracted: str,
    headings: tuple[str, ...],
    marked: tuple[str, ...] = (),
) -> list[tuple[str, int]]:
    """The pieces of a draft's text that hold a marker, in lower case, each with the offset where its own
    text starts after the clause it continues.

    In a DOCX or PDF each line is a piece (a heading of two or three PDF lines is one), read as _line_pieces
    reads it; marked are the PDF's headings set in a heading font. In Markdown a section that holds a list
    item is read the same way, each run of its lines between lists as one piece (_markdown_pieces), and any
    other section is one piece. In XHTML and HTML each section is a piece.
    """
    if not extracted:
        if suffix == ".md":
            return [piece for text in sections.values() for piece in _markdown_pieces(text)]
        return [(low, 0) for low in (text.lower() for text in sections.values()) if _marked(low)]
    if not _marked(extracted.lower()):
        return []
    units = _line_units(suffix, extracted, headings, marked)
    return [piece for piece, _ in _line_pieces(units) if piece is not None]


def _line_pieces(units: Iterable[tuple[str, str]]) -> Iterator[tuple[tuple[str, int] | None, bool]]:
    """The piece of each line, given with its kind (_line_units), where its own text holds a marker (None
    otherwise), and whether the line belongs to a list: an item, or a line that continues one.

    A heading is judged on its own words: no clause runs into it, and none runs on from it unless it ends in
    a negation. A line that starts with a capital letter or a digit, or with a word that holds a capital
    letter, starts a new sentence (_starts_sentence).

    A list item (a bullet, a dash, a list letter or number in lower case: _LIST_ITEM) continues the lead-in
    before its list (_lead), so a negated lead-in governs every item, whatever its marker ("-", "*", "1.",
    "1)", "(1)", "a.", "a)", "(a)", "i.", "(i)"; the full stop after a letter or number ends no clause) and
    whatever stands between the items (";", "; or", ", or", "and", nothing). An item that starts a new
    sentence does so only after a lead-in that ends in a colon or a negation. A lead-in whose negation
    negates words of its own ("The following risks are not covered by any compensation scheme:") governs
    no item (_settled).

    An item whose marker does not come right after that of the list's last item (_follows) starts a list
    inside the list where the line before it ends in a colon or a negation: "(a) the token is neither"
    leads into "(i) ..." and "(ii) ...", and "(b)" goes back to the outer list.

    A guess (a heading by its shape alone that may be a list item, _guessed) is an item where the line
    before it ends in a colon or a negation ("For the purposes of MiCAR the token is not" / "1. An
    asset-referenced token"), where the item after it comes right after it, or where it comes right after
    the last item of a list and the line before it does not end a sentence. Any other heading (a DOCX
    heading paragraph, a PDF heading in a heading font, a line shaped like a title such as "3. Reserve of
    Assets") is a heading, also where its number goes on from a list.

    A list ends at a heading, and at a line that is no item and starts a new sentence unless that line is
    a wrapped line of the item before it (_wraps). A list a line of which ends in a semicolon also ends
    with the line that ends a sentence: after "1. ...;" and "2. any deposit guarantee scheme.", "3. Reserve
    of assets" is not governed by the lead-in (a list inside a list ends there alone). A numbered or
    lettered list that a line starting a new sentence ended goes on at its next item ("1. ... of
    Regulation" / "(EU) 2023/1114." / "2. ..."), unless a line that ends in a colon or a negation stands
    right before that item. Any other line continues the line before it, as a DOCX may split a sentence
    over paragraphs ("... is neither" / "an asset-referenced token nor" / ...) and a PDF wraps its lines.
    """
    from micar_linter.document import _ends_sentence

    previous: tuple[str, str, bool] | None = None
    # The lists being read, outermost first, and those that a line starting a new sentence ended.
    lists: list[_List] = []
    ended: list[_List] = []
    units = iter(units)
    unit = next(units, None)
    while unit is not None:
        text, kind = unit
        unit = next(units, None)
        item = _LIST_ITEM.match(text.lstrip())
        marker = _marker(item.group()) if item else None
        heading = kind != _BODY_LINE
        if heading and marker and kind == _GUESSED:
            following = _LIST_ITEM.match(unit[0].lstrip()) if unit is not None else None
            heading = not (
                _opens(previous)
                or (following is not None and _follows(_marker(following.group()), marker))
                or (
                    _innermost(marker, lists) is not None
                    and previous is not None
                    and not _ends_sentence(previous[1].rstrip())
                )
            )
        if heading:
            clause, lists, ended = "", [], []
        elif item and marker:
            depth = _innermost(marker, lists)
            if depth is not None:
                del lists[depth + 1 :]
            elif lists and _opens(previous):
                lists.append(_List(_lead(previous), True, marker))
            elif not lists:
                opens = _opens(previous)
                # A numbered or lettered list that a sentence ended goes on at its next item.
                resumed = None if opens or marker[1] is None else _innermost(marker, ended)
                fresh = [_List(_lead(previous), opens, marker)]
                lists, ended = (fresh if resumed is None else ended[: resumed + 1]), []
            current = lists[-1]
            current.last = marker
            starts = _starts_sentence(text.lstrip()[item.end() :])
            clause = current.lead if current.opens or not starts else ""
            text = _item_text(text, item)
        elif lists and (not _starts_sentence(text) or _wraps(previous, text)):
            clause = _continued(previous)
        elif _starts_sentence(text):
            clause = ""
            if lists:
                lists, ended = [], lists
        else:
            clause = _continued(previous)
        low = text.lower()
        yield (_piece(clause, low) if _marked(low) else None), bool(lists)
        previous = (clause, low, heading)
        if lists and not heading:
            # A list whose items end in a semicolon ends with the line that ends a sentence.
            end = low.rstrip()
            if _ITEM_END.search(end):
                lists[-1].semicolons = True
            elif lists[-1].semicolons and _ends_sentence(end):
                lists.pop()
                ended = []


def _markdown_pieces(section: str) -> list[tuple[str, int]]:
    """The pieces of a Markdown section's text that hold a marker, in lower case, each with the offset where
    its own text starts after the clause it continues.

    A section without a list item is one piece, so a clause runs on over its line ends. In a section with
    one, each line of a list (an item, or a line that continues one) is a piece as _line_pieces reads the
    lines of a DOCX, a line shaped like a title (_titled) as a heading, so a negated lead-in governs every
    item and its reach ends where the list ends; each run of lines between lists is one piece, as a section
    without a list is.
    """
    low = section.lower()
    if not _marked(low):
        return []
    lines = section.split("\n")
    if not any(_LIST_ITEM.match(line.lstrip()) for line in lines):
        return [(low, 0)]
    pieces: list[tuple[str, int]] = []
    run: list[str] = []
    read = _line_pieces((line, _line_kind(line)) for line in lines)
    for line, (piece, listed) in zip(lines, read, strict=True):
        if not listed:
            run.append(line)
            continue
        if run:
            low = "\n".join(run).lower()
            if _marked(low):
                pieces.append((low, 0))
            run = []
        if piece is not None:
            pieces.append(piece)
    if run:
        low = "\n".join(run).lower()
        if _marked(low):
            pieces.append((low, 0))
    return pieces


def _load_document(path: Path, suffix: str, whitepaper_type: WhitepaperType | None) -> Whitepaper:
    if not path.exists():
        raise SystemExit(f"File not found: {path}")

    ixbrl_issues = []
    ixbrl_validated = False
    script_packed = False
    extraction_notes: tuple[str, ...] = ()
    placeholder_fields: dict[str, tuple[str, ...]] = {}
    numbered_fields: dict[str, str] | None = None
    extracted = ""
    headings: tuple[str, ...] = ()
    marked_headings: tuple[str, ...] = ()
    # The whole text of the file, which COMMON.LEI_CHECK_DIGITS reads besides the sections.
    document_text = ""
    try:
        if suffix == ".pdf":
            from micar_linter.document import parse_pdf

            parsed = parse_pdf(path)
            sections, extracted, headings = parsed.sections, parsed.text, parsed.headings
            marked_headings = parsed.marked_headings
            document_text = parsed.document_text
        elif suffix == ".docx":
            from micar_linter.document import parse_docx

            parsed = parse_docx(path)
            sections, extracted, headings = parsed.sections, parsed.text, parsed.headings
            document_text = parsed.document_text
        elif suffix == ".md":
            from micar_linter.document import load_from_markdown

            sections = load_from_markdown(path)
            document_text = path.read_text(encoding="utf-8")
        else:
            from micar_linter.ixbrl import validate_ixbrl
            from micar_linter.numbered_fields import (
                extract_numbered_fields,
                field_answers,
                is_numbered_layout,
                sections_from_numbered_fields,
            )
            from micar_linter.xhtml_parser import document_text as xhtml_document_text
            from micar_linter.xhtml_parser import is_script_packed, load_from_xhtml

            script_packed = is_script_packed(path)
            source = _unpack_viewer_page(path) if script_packed else path
            document_text = xhtml_document_text(source)
            fields = extract_numbered_fields(source)
            if is_numbered_layout(fields):
                # The template wording names every regime ("not an asset-referenced token"),
                # so the regime of a numbered white paper is never inferred from its text.
                if whitepaper_type is None:
                    subject = f"The white paper packed in {path.name}" if script_packed else path.name
                    raise SystemExit(
                        f"{subject} uses the numbered fields of Implementing Regulation (EU) 2024/2984. "
                        "State the regime explicitly: other, art or emt."
                    )
                sections, extraction_notes, placeholder_fields = sections_from_numbered_fields(
                    fields, whitepaper_type
                )
                numbered_fields = field_answers(fields, whitepaper_type)
            else:
                sections = load_from_xhtml(source)
            if script_packed:
                # A viewer's rendering is not the XHTML document itself, so validate_ixbrl does not run.
                # The first-page statement is found by its wording, not by a heading or field.
                found = sections.keys() - {"not_approved_statement"}
                viewer_notes = (VIEWER_PAGE_NOTE, VIEWER_EMPTY_NOTE) if not found else (VIEWER_PAGE_NOTE,)
                extraction_notes = (*viewer_notes, *extraction_notes)
            else:
                ixbrl_issues = validate_ixbrl(path)
                ixbrl_validated = True
    except SystemExit:
        raise
    except Exception as exc:
        raise SystemExit(f"Error reading document {path}: {exc}") from exc

    # The regime of a PDF or DOCX is inferred from its whole text: a heading ("Reserve of Assets"), which is
    # not section body, or text in no section may be all that names it. A negated marker does not count. A
    # given regime is not inferred, so the text is not read for it.
    if whitepaper_type is not None:
        wp_type = whitepaper_type
    else:
        pieces = _regime_pieces(suffix, sections, extracted, headings, marked_headings)
        if _names_regime(pieces, _ART_MARKERS):
            wp_type = WhitepaperType.ART
        elif _names_regime(pieces, _EMT_MARKERS):
            wp_type = WhitepaperType.EMT
        else:
            wp_type = WhitepaperType.OTHER

    if wp_type is WhitepaperType.ART:
        sections.pop("emt", None)
        sections.pop("crypto_asset", None)
        # Art. 19 MiCAR prescribes no first-page statement, so no ART rule reads one.
        sections.pop("not_approved_statement", None)
    elif wp_type is WhitepaperType.EMT:
        sections.pop("art", None)
        sections.pop("crypto_asset", None)
    else:
        sections.pop("art", None)
        sections.pop("emt", None)

    title = path.stem.replace("-", " ").replace("_", " ").title()
    metadata = {
        "source_file": str(path),
        "ixbrl_validated": ixbrl_validated,
        "ixbrl_issues": tuple(ixbrl_issues),
        "extraction_notes": extraction_notes,
        "script_packed_source": script_packed,
        "placeholder_fields": placeholder_fields,
        "document_text": document_text,
    }
    # Only a numbered-field draft carries the key, so a point rule can tell which layout it reads.
    if numbered_fields is not None:
        metadata["numbered_fields"] = numbered_fields

    return Whitepaper(
        title=title,
        type=wp_type,
        sections=sections,
        metadata=metadata,
    )
