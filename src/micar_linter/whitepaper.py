"""Input model for crypto-asset white papers."""

from __future__ import annotations

import json
import re
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
    # included, and the text of each section the regime drops, which COMMON.LEI_CHECK_DIGITS reads besides
    # the sections.
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
# split a sentence over paragraphs and a PDF wraps its lines inside a sentence, and into each item of a list
# after a lead-in, up to the item that closes a list whose items end in a semicolon (_regime_pieces).
_NEGATION = re.compile(r"\b(?:not|no|neither|nor|never|without|other than|except|excluding|unlike)\b|n't\b")
_CLAUSE_END = re.compile(r"[.!?;:](?=\s|$)|\b(?:but|however|whereas|although|though|while)\b")
_NEGATION_REACH = 8
_NEGATION_LOOKBACK = 200
# A phrase that holds a negation word but does not negate what follows it (a pseudo-negation, as NegEx and
# pyConTextNLP list "not only" and "not necessarily"): "not limited to", "not be limited to", "not restricted
# to", "not be restricted to", "not exhaustive", "not exclusively", "not only", "not necessarily" (each also
# with "n't") and "without limitation". Matched where a negation word starts. It governs no item of a list
# after it ("The risks include, but are not limited to:"), where it is the only kind of negation in its
# clause (_negated, _continued); elsewhere its negation word negates as any other does.
_PSEUDO_NEGATION = re.compile(
    r"(?:not|n't)\s+(?:(?:be\s+)?(?:limited|restricted)\s+to|exhaustive|exclusively|only|necessarily)\b"
    r"|without\s+limitation\b"
)
# A list item: a bullet or dash, or a list number of one or two digits or a lower-case list letter or roman
# numeral with a full stop or a bracket, before its text.
_LIST_ITEM = re.compile(
    r"(?:[-*\u2013\u2014\u2022\u2023\u2043\u00b7\u25aa\u25cf]|\(?(?:[a-z]|[ivx]{1,4}|\d{1,2})[.)])\s"
)
# The start of a line that is a list item.
_ITEM_LINE = re.compile(rf"\n[ \t]*(?:{_LIST_ITEM.pattern})")
_FIRST_WORD = re.compile(r"[^\W_]+")
# A heading that ends in a negation leads into the line after it; a colon after the negation ends the clause
# there (_CLAUSE_END), so such a heading governs nothing.
_ENDS_IN_NEGATION = re.compile(rf"(?:{_NEGATION.pattern})\W*$")


def _negated(text: str, start: int) -> bool:
    """Whether a negation governs the marker at start of the lower-case text.

    A pseudo-negation ("not limited to") governs no list item after it: where the marker stands in or after a
    line that starts with a list marker (_LIST_ITEM) after the end of the pseudo-negation, its negation word
    is none. That holds only where every negation word of the clause stands in a pseudo-negation that ends
    before such a line. Otherwise each negation word counts, as before #96: beside another one ("The token is
    not, among other things and not limited to these,") and in the marker's own sentence ("including but not
    limited to e-money tokens"), also where a line end splits that sentence."""
    before = text[max(0, start - _NEGATION_LOOKBACK) : start]
    ends = list(_CLAUSE_END.finditer(before))
    clause = before[ends[-1].end() :] if ends else before
    negations = list(_NEGATION.finditer(clause))
    if not negations:
        return False
    if _PSEUDO_NEGATION.match(clause, negations[-1].start()):
        # The start of the last list item line of the clause; a pseudo-negation that ends before it governs
        # nothing, where the clause holds no other negation word.
        item = max((match.start() for match in _ITEM_LINE.finditer(clause)), default=-1)
        if all(
            (pseudo := _PSEUDO_NEGATION.match(clause, match.start())) and pseudo.end() <= item
            for match in negations
        ):
            return False
    return len(clause[negations[-1].end() :].split()) <= _NEGATION_REACH


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


def _joined(lines: list[str]) -> str:
    """Lines as one lower-case text with each run of whitespace as one space."""
    return " ".join(" ".join(lines).lower().split())


def _line_units(suffix: str, extracted: str, headings: tuple[str, ...]) -> list[tuple[str, bool]]:
    """The lines of a DOCX's or PDF's extracted text, each with whether it is read as a heading: a DOCX
    heading paragraph, a PDF heading line or the two or three lines of a wrapped heading, as one unit, and a
    line that the loader did not take for a heading but is shaped like a title (_titled)."""
    lines = extracted.split("\n")
    # A DOCX heading is one paragraph, one line of the extracted text.
    sizes = (1,) if suffix == ".docx" else (1, 2, 3)
    heading_texts = {" ".join(heading.lower().split()) for heading in headings}
    units: list[tuple[str, bool]] = []
    index = 0
    while index < len(lines):
        size = next((k for k in sizes if _joined(lines[index : index + k]) in heading_texts), 0)
        if size:
            units.append(("\n".join(lines[index : index + size]), True))
            index += size
        else:
            units.append((lines[index], _titled(lines[index])))
            index += 1
    return units


def _titled(text: str) -> bool:
    """Whether a line is shaped like a title: a short label without sentence punctuation (at most twelve
    words) in which every word other than a short connective starts with a capital letter, such as a
    heading set in the body font of a PDF ("No Investor Compensation")."""
    from micar_linter.document import _is_label, _is_title_like

    return _is_label(text.strip()) and _is_title_like(text.strip())


def _starts_sentence(text: str) -> bool:
    """Whether a line starts a new sentence: its first word starts with a capital letter or a digit
    ("100% of the reserve ...", "1 e-money token ..."), or holds a capital letter, as a name such as
    "xStable" does. A line that starts with a word in lower case ("an e-money token") continues the line
    before it."""
    first = _FIRST_WORD.search(text)
    if first is None:
        return False
    word = first.group()
    return not word[0].islower() or any(char.isupper() for char in word)


def _continued(previous: tuple[str, str, bool] | None) -> str:
    """The clause that a line continues after the previous line (its own clause, text and whether it is a
    heading), in lower case and at most _NEGATION_LOOKBACK characters.

    A heading is judged on its own words, so nothing continues it unless it ends in a negation ("For the
    purposes of MiCAR the token is not", which a PDF may read as a heading). A line that ends in a
    semicolon is an item of a list, and the next line continues the clause that it continued. A colon at
    the end of a line introduces the line after it, so it ends no clause there, unless each negation word of
    that clause stands in a pseudo-negation: such a lead-in governs no line of its list, whether or not the
    line has a list marker (a Word list style shows one that the text does not hold).
    """
    if previous is None:
        return ""
    clause, text, heading = previous
    if heading:
        return text[-_NEGATION_LOOKBACK:] if _ENDS_IN_NEGATION.search(text) else ""
    text = text.rstrip()
    if text.endswith(";"):
        return clause
    continued = f"{clause}\n{text.removesuffix(':')}"[-_NEGATION_LOOKBACK:]
    if text.endswith(":") and _only_pseudo_negations(continued):
        return ""
    return continued


def _only_pseudo_negations(text: str) -> bool:
    """Whether the last clause of the lower-case text holds a negation word and each stands in a
    pseudo-negation."""
    ends = list(_CLAUSE_END.finditer(text))
    negations = list(_NEGATION.finditer(text, ends[-1].end() if ends else 0))
    return bool(negations) and all(_PSEUDO_NEGATION.match(text, match.start()) for match in negations)


def _regime_pieces(
    suffix: str, sections: dict[str, str], extracted: str, headings: tuple[str, ...]
) -> list[tuple[str, int]]:
    """The pieces of a draft's text, in lower case, each with the offset where its own text starts after the
    clause it continues.

    In a DOCX or PDF each line is a piece (a heading of two or three PDF lines is one). A heading, and a line
    shaped like a title, is judged on its own words: no clause runs into it, and none runs on from it unless
    it ends in a negation with no colon after it. A line that starts with a capital letter or a digit, or with
    a word that holds a capital letter, starts a new sentence (_starts_sentence). A list item continues the
    lead-in before its list, so a negated lead-in governs each item marked with a bullet or dash of
    _LIST_ITEM, or with a list number of one or two digits or a lower-case list letter or roman numeral and a
    bracket ("1)", "(a)", "(iv)"), also where the items end in a semicolon; an item that starts a new sentence
    does so only after a lead-in that ends in a colon or a negation. The full stop after a list number or
    letter ("1.", "a.") ends the clause as any full stop does, so a lead-in governs no item marked so. An item
    continues the lead-in of its list, not the item before it, so the items of a list inside an item continue
    the outer lead-in. A list whose items end in a semicolon ("; and" and "; or" included) ends at the item
    that ends in a full stop: after it, a line with a list marker whose text is shaped like a heading
    (document._heading_shaped: a short label that starts with a capital letter, such as "(c) Reserve of
    assets") is read as a heading, so the lead-in governs it no more. Any other line continues the line before
    it, as a DOCX may split a sentence over paragraphs ("... is neither" / "an asset-referenced token nor" /
    ...) and a PDF wraps its lines. In the other formats each section is a piece.
    """
    if not extracted:
        return [(text.lower(), 0) for text in sections.values()]
    pieces: list[tuple[str, int]] = []
    previous: tuple[str, str, bool] | None = None
    # The clause the items of the current list continue, that of their lead-in, and whether the lead-in
    # ends in a colon or a negation, so that it governs an item that starts with a capital letter too.
    lead: str | None = None
    lead_opens = False
    # How the last item of the current list ends so far ("semicolon", "full stop" or ""), how many items the
    # list has, and whether each item before the last ends in a semicolon.
    ending, items, semicolons = "", 0, True
    for text, heading in _line_units(suffix, extracted, headings):
        item = _LIST_ITEM.match(text.lstrip())
        closed = items >= 2 and semicolons and ending == "full stop"
        if item and lead is not None and closed and _heading_shaped(text.lstrip()[item.end() :]):
            heading = True
        if heading:
            clause, lead = "", None
        elif item:
            if lead is None:
                lead = _continued(previous)
                lead_opens = previous is not None and bool(
                    previous[1].rstrip().endswith(":") or _ENDS_IN_NEGATION.search(previous[1])
                )
            clause = lead if lead_opens or not _starts_sentence(text.lstrip()[item.end() :]) else ""
        elif _starts_sentence(text):
            clause, lead = "", None
        else:
            clause = _continued(previous)
        low = text.lower()
        pieces.append((f"{clause}\n{low}", len(clause) + 1) if clause else (low, 0))
        previous = (clause, low, heading)
        if lead is None:
            ending, items, semicolons = "", 0, True
        elif item:
            semicolons = semicolons and (items == 0 or ending == "semicolon")
            ending, items = _ending(low), items + 1
        elif items:
            # A line that continues the item, as a PDF wraps it.
            ending = _ending(low)
    return pieces


# The end of a list item that another item follows: a semicolon, also before "and" or "or".
_SEMICOLON_END = re.compile(r";(?:\s+(?:and|or))?$")


def _ending(text: str) -> str:
    """How a line of a list item ends: "semicolon" (also "; and", "; or"), "full stop" or ""."""
    text = text.rstrip()
    if _SEMICOLON_END.search(text):
        return "semicolon"
    return "full stop" if text.endswith(".") else ""


def _heading_shaped(text: str) -> bool:
    """Whether the text of a list item after its marker is shaped like a heading (document._heading_shaped:
    a short label that starts with a capital letter)."""
    from micar_linter.document import _heading_shaped as heading_shaped

    return heading_shaped(text.strip())


# The sections of the other regimes, which the document loader drops once the regime is known.
_DROPPED_SECTIONS = {
    WhitepaperType.ART: ("emt", "crypto_asset", "not_approved_statement"),
    WhitepaperType.EMT: ("art", "crypto_asset"),
    WhitepaperType.OTHER: ("art", "emt"),
}


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
    # The whole text of the file (and below, the text of the sections the regime drops), which
    # COMMON.LEI_CHECK_DIGITS reads besides the sections.
    document_text = ""
    try:
        if suffix == ".pdf":
            from micar_linter.document import parse_pdf

            parsed = parse_pdf(path)
            sections, extracted, headings = parsed.sections, parsed.text, parsed.headings
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

    # The regime of a PDF or DOCX is inferred from its extracted text (for a DOCX the runs and hyperlinks
    # directly in the paragraphs of its body): a heading ("Reserve of Assets"), which is not section body, or
    # text in no section may be all that names it. A negated marker does not count. A given regime is not
    # inferred, so the text is not read for it.
    if whitepaper_type is not None:
        wp_type = whitepaper_type
    else:
        pieces = _regime_pieces(suffix, sections, extracted, headings)
        if _names_regime(pieces, _ART_MARKERS):
            wp_type = WhitepaperType.ART
        elif _names_regime(pieces, _EMT_MARKERS):
            wp_type = WhitepaperType.EMT
        else:
            wp_type = WhitepaperType.OTHER

    # The sections of the other regimes are dropped. Art. 19 MiCAR prescribes no first-page statement, so
    # no ART rule reads one. COMMON.LEI_CHECK_DIGITS still reads the text of each dropped section, after
    # the text of the file and a blank line apart from it: the text of the file holds text moved away,
    # deleted or hidden that can complete a code the section shows malformed, so a code that only a dropped
    # section shows malformed would pass, and a change of the regime could make such a draft pass.
    dropped = [str(sections.pop(key)) for key in _DROPPED_SECTIONS[wp_type] if key in sections]
    if dropped:
        document_text = "\n\n".join((document_text, *dropped))

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
