"""PDF and DOCX document ingestion and section parsing."""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from functools import partial
from pathlib import Path

from micar_linter.placeholders import is_not_applicable, is_placeholder

# Common patterns (in English and German) matching whitepaper section headings.
# Word boundaries are used to avoid false positives.
SECTION_PATTERNS = {
    "summary": [
        r"\bsummary\b",
        r"\bzusammenfassung\w*",
        r"\bplain-language\s+summary\b",
        r"\bkey\s+information\b",
    ],
    "risk_warning": [r"\brisk\s+warning\b", r"\bwarnhinweis\w*", r"\bmandatory\s+warning\b"],
    "management_statement": [
        r"\bmanagement\s+body\b",
        r"\bleitungsorgan\w*",
        r"\bmanagement\s+statement\b",
        r"\bstatement\b.*\bmanagement\b",
    ],
    "notification_date": [
        r"\bdate\s+of\s+notification\b",
        r"\bnotifizierungsdatum\w*",
        r"\bnotification\s+date\b",
    ],
    "language": [r"\blanguage\b", r"\bsprache\w*"],
    "offeror": [r"\bofferor\b", r"\banbieter\w*"],
    "issuer": [r"\bissuer\b", r"\bemittent\w*"],
    "trading_platform_operator": [
        r"\btrading\s+platform\b",
        r"\bhandelsplattform\w*",
        r"\boperator\b.*\btrading\b",
    ],
    "project": [r"\bproject\b", r"\bprojekt\w*", r"\bbusiness\s+model\b", r"\bteam\b"],
    "offer_or_admission": [
        r"\bpublic\s+offer\b",
        r"\bzulassung\w*",
        r"\badmission\s+to\s+trading\b",
        r"\boffer\b.*\badmission\b",
    ],
    "crypto_asset": [
        r"\bcrypto-asset\b",
        r"\bcrypto\s+asset\b",
        r"\bcharacteristics\b.*\bcrypto\b",
        r"\binformation\s+about\s+the\s+token\b",
        r"\bthe\s+token\b",
    ],
    "art": [
        r"\basset-referenced\s+token\b",
        r"\bstabilisation\s+mechanism\b",
        r"\breference\s+assets\b",
        r"\binformation\s+about\s+the\s+token\b",
        r"\bthe\s+token\b",
    ],
    "emt": [
        r"\be-money\s+token\b",
        r"\bdenomination\b",
        r"\breferenced\s+currency\b",
        r"\binformation\s+about\s+the\s+token\b",
        r"\bthe\s+token\b",
    ],
    "rights_and_obligations": [
        r"\brights\s+and\s+obligations\b",
        r"\brechte\s+und\s+pflichten\b",
        r"\bholder\s+rights\b",
    ],
    "technology": [
        r"\btechnology\b",
        r"\btechnologie\w*",
        r"\bunderlying\s+technology\b",
        r"\bdlt\b",
        r"\bconsensus\b",
    ],
    "risks": [r"\brisk\s+factors\b", r"\brisikofaktor\w*", r"\brisks\b", r"\brisiken\b"],
    "environmental_impact": [
        r"\benvironmental\b",
        r"\bclimate\b",
        r"\bsustainability\b",
        r"\bumwelt\w*",
        r"\bklima\w*",
    ],
    "reserve_of_assets": [r"\breserve\b.*\bassets\b", r"\breservevermögen\w*", r"\basset\s+reserve\b"],
    "redemption": [r"\bredemption\b", r"\brücknahme\w*", r"\bredemption\s+right\b"],
    "safeguarding": [r"\bsafeguarding\b", r"\babsicherung\w*", r"\bsicherung\w*.*\bgelder\w*"],
}


def match_heading_to_section(heading: str) -> list[str]:
    """Matches a heading line to a list of known ruleset section keys."""
    normalized = heading.lower()
    matched = []
    for key, patterns in SECTION_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, normalized):
                matched.append(key)
                break
    return matched


# Formatting alone does not make a heading: a body sentence that mentions a section word
# ("Note: purchasers bear market, liquidity and technology risks.") must not open that section.
_MAX_HEADING_WORDS = 12
# Numbered part titles of the Implementing Regulation (EU) 2024/2984 template run longer
# ("Part E: Information about the offer to the public of crypto-assets or their admission to trading").
_MAX_NUMBERED_HEADING_WORDS = 20
# A question mark may end a heading ("Risks: What Could Go Wrong?"); these marks end a sentence or a phrase.
_SENTENCE_END = re.compile(r"[.!;,]$")
# A word of four or more letters, a full stop and a capitalised word: "Risks. Holders may lose ...".
# "A.1 Name", "5.2 Risks" and "Ledger S.A. Risks" have no such word.
_SENTENCE_BREAK = re.compile(r"([^\W\d_]{4,})[.!?]\s+([^\W\d_])")
# Abbreviations that keep their full stop inside a heading: "5. Risks (incl. Liquidity Risks)",
# "Quillmoor Corp. Risk Factors", "Risiken bzgl. des Tokens".
_ABBREVIATIONS = frozenset(
    {
        "abschn", "abzgl", "approx", "assoc", "buchst", "bzgl", "corp", "dept", "einschl", "evtl", "excl", "incl",
        "inkl", "insb", "intl", "mgmt", "resp", "sect", "unterabs", "ziff", "zzgl",
    }
)  # fmt: skip
# A list item starts with a bullet (• ● ▪ ■ ◦ ○ ‣ ► ▸ ·), an asterisk, a hyphen, an en or em dash, or a
# symbol-font glyph that PDF text extraction maps to the private use area.
_BULLET = re.compile(
    r"^[*\-\u00b7\u2013\u2014\u2022\u2023\u25a0\u25aa\u25b8\u25ba\u25cb\u25cf\u25e6\uf000-\uf0ff]"
)
# The numbering of the Implementing Regulation (EU) 2024/2984 template: "Part I", "Teil I", the field
# numbers "A.1" and "I.01", and the fields 00 to 10 of the summary table ("01 Date of notification").
_TEMPLATE_NUMBERING = (
    r"(?:Part|PART|Teil|TEIL)\s+(?:[A-Z]|[IVX]{1,5}|\d{1,2})[.:)]?|[A-Z]\.\d{1,2}(?:\.\d{1,2})*\.?|0\d|10"
)
# Outline numbering, which headings and list items share: "1.", "5.2", "1)", "I.", "IV.", "A.".
_OUTLINE_NUMBERING = r"\d{1,2}(?:\.\d{1,2})*[.)]|\d{1,2}(?:\.\d{1,2})+|[A-Z]\.|[IVX]{1,5}\."
_NUMBERING = re.compile(rf"^(?:(?P<template>{_TEMPLATE_NUMBERING})|{_OUTLINE_NUMBERING})\s+")
# Words a title-case heading leaves in lower case: "Information about the Issuer", "Rechte und Pflichten".
_MINOR_WORD = re.compile(
    r"a|about|against|among|an|and|as|at|between|by|for|from|in|into|of|on|or|over|per|than|the|to|under|via"
    r"|with|within|without|am|auf|aus|bei|bzw|das|dem|den|der|des|die|ein|eine|einer|eines|für|im|mit|nach"
    r"|oder|sowie|über|und|von|vom|zu|zum|zur"
)
# Dashes and quotation marks around heading words: en dash, em dash, curly single and double quotes.
_DASHES = "-\u2013\u2014"
_QUOTES = "\"'\u2018\u2019\u201c\u201d"


@dataclass(frozen=True)
class DocumentSections:
    """The section texts of a DOCX or PDF draft and, apart from them, the text of its headings.

    Heading text is not section body, but regime inference reads it: a heading such as
    "Reserve of Assets" may be the only place that names the regime.
    """

    sections: dict[str, str]
    headings: tuple[str, ...]


def _words(text: str) -> list[str]:
    """The words of a line; a lone dash ("Part G \u2013 Information ...") is not a word."""
    return [word for word in text.split() if word.strip(_DASHES)]


def _max_words(text: str) -> int:
    return _MAX_NUMBERED_HEADING_WORDS if _NUMBERING.match(text) else _MAX_HEADING_WORDS


def _has_sentence_break(text: str) -> bool:
    return any(
        letter.isupper() and word.lower() not in _ABBREVIATIONS
        for word, letter in _SENTENCE_BREAK.findall(text)
    )


def _is_label(text: str, max_words: int = _MAX_HEADING_WORDS) -> bool:
    """A short label rather than a sentence or a list item: few words, no sentence punctuation after a
    word and no leading bullet."""
    return (
        len(_words(text)) <= max_words
        and not _SENTENCE_END.search(text)
        and not _has_sentence_break(text)
        and not _BULLET.match(text)
    )


def _is_title_like(text: str) -> bool:
    """All capitals, or every word other than a short connective or an abbreviation starts with a capital."""
    words = [word.strip(f"()[]{_QUOTES},:;") for word in text.split()]
    words = [word for word in words if word[:1].isalpha()]
    if not words or not words[0][0].isupper():
        return False
    return all(
        not word.islower() or _MINOR_WORD.fullmatch(word) or word.rstrip(".") in _ABBREVIATIONS
        for word in words[1:]
    )


def _ends_sentence(line: str) -> bool:
    return bool(re.search(r"[.!?][\"')\]\u2019\u201d]*$", line))


def _runs_on(line: str) -> bool:
    """The sentence runs on into the next line: the line ends with a comma, a hyphenated word part or a
    connective such as "and", "the" or "die"."""
    if re.search(r"(?:,|\w-)$", line):
        return True
    last = line.split()[-1]
    return len(last) > 1 and (last.islower() or line.isupper()) and bool(_MINOR_WORD.fullmatch(last.lower()))


@dataclass(frozen=True)
class _Line:
    """A non-empty text line and, where the PDF reports it, the font its letters are set in."""

    text: str
    size: float | None = None  # the size of its smallest letter, in points
    bold: bool = False  # every letter is set in a bold face


_HEADING, _BODY, _BREAK = "heading", "body", "break"


def _line_role(
    line: str,
    previous: str | None,
    previous_role: str | None,
    following: str | None,
    *,
    started: bool,
    styled: bool,
    previous_styled: bool,
) -> str:
    """The role of a line that names a section: a heading, body text, or a break that ends the section.

    previous and following are the neighbouring lines (None at either end), previous_role is the role of
    previous, started tells whether a heading or break came before, and styled and previous_styled whether
    the line and the one before are set larger or bolder than the body text.
    """
    numbering = _NUMBERING.match(line)
    title = line[numbering.end() :] if numbering else line
    if not _is_label(line, _max_words(line)) or not next((c for c in title if c.isalpha()), "").isupper():
        return _BODY
    # The template's own part and field labels, sentence case included ("Part I: Information on risks").
    if numbering and numbering.group("template"):
        return _HEADING
    title_like = _is_title_like(title)
    # A line ending with a colon is a lead-in, not a heading. In sentence case it stays in the current
    # section; in title case or a heading font it may also be a heading written with a colon ("Risk
    # Factors:"), so it ends the section rather than handing that section to the one before.
    if line.endswith(":"):
        return _BREAK if title_like or styled else _BODY
    # Running text stays in the current section: the line a lead-in introduces, and a line that a
    # sentence runs on into or out of.
    if previous is not None and previous.endswith(":"):
        return _BODY
    if (previous_role == _BODY and _runs_on(previous)) or (following is not None and following[:1].islower()):
        return _BODY
    # A line that runs on into the next one is no heading, but it may be the first line of a wrapped
    # heading as well as of a paragraph, so it ends the section.
    if _runs_on(line):
        return _BREAK
    # In a capitals paragraph, a line after a long or unfinished capitals line is a wrapped line of it; a
    # long capitals line over more capitals may start one, or be a long title over one, so it ends the section.
    if line.isupper():
        if (
            previous_role == _BODY
            and previous.isupper()
            and not _ends_sentence(previous)
            and (len(_words(previous)) >= 8 or _runs_on(previous))
        ):
            return _BODY
        if following is not None and following.isupper() and len(_words(line)) >= 8:
            # Under a heading it starts the paragraph of that heading.
            return _BREAK if previous_role == _BODY else _BODY
    # After a numbered body line, a numbered line is the next list item. In title case, or in the same
    # heading font as that line, it may also be the heading after an empty section, so it ends the
    # section; a font that sets it apart from that line makes it a heading.
    if numbering and previous_role == _BODY and _NUMBERING.match(previous):
        if styled and not previous_styled:
            return _HEADING
        return _BREAK if title_like or styled else _BODY
    if styled:
        return _HEADING
    finished = (
        not started
        or previous_role != _BODY
        or _ends_sentence(previous)
        or is_placeholder(previous)
        or is_not_applicable(previous)
    )
    if title_like and (not numbering or finished):
        return _HEADING
    # Shaped like a heading but in sentence case ("Risk factors"), or numbered after an unfinished line:
    # the text below is credited to no section rather than to the section before.
    return _BREAK


def _body_font(lines: list[_Line]) -> tuple[float, bool] | None:
    """The font size and weight that most letters are set in."""
    letters: Counter[tuple[float, bool]] = Counter()
    for line in lines:
        if line.size is not None:
            letters[(round(line.size, 1), line.bold)] += sum(char.isalpha() for char in line.text)
    return letters.most_common(1)[0][0] if letters else None


def _styled(line: _Line, body_font: tuple[float, bool] | None) -> bool:
    """Set at least 15 % larger than the body text, or in bold where the body text is not."""
    if line.size is None or body_font is None:
        return False
    size, bold = body_font
    return line.size >= size * 1.15 or (line.bold and not bold and line.size >= size * 0.95)


def _line_sections(lines: list[_Line]) -> DocumentSections:
    body_font = _body_font(lines)
    styled = [_styled(line, body_font) for line in lines]
    sections: dict[str, list[str]] = {}
    headings: list[str] = []
    current_keys: list[str] = []
    previous: str | None = None
    previous_role: str | None = None
    for index, line in enumerate(lines):
        keys = match_heading_to_section(line.text)
        role = _BODY
        if keys:
            following = lines[index + 1].text if index + 1 < len(lines) else None
            role = _line_role(
                line.text,
                previous,
                previous_role,
                following,
                started=bool(headings),
                styled=styled[index],
                previous_styled=index > 0 and styled[index - 1],
            )
        if role == _BODY:
            for key in current_keys:
                sections.setdefault(key, []).append(line.text)
        else:
            headings.append(line.text)
            current_keys = keys if role == _HEADING else []
        previous, previous_role = line.text, role
    return DocumentSections({k: "\n".join(v) for k, v in sections.items()}, tuple(headings))


def sections_from_lines(lines: Iterable[str]) -> dict[str, str]:
    """Group plain text lines, such as the extracted text of a PDF, under the section headings among them.

    Without font information a heading is recognised by its shape alone (see _line_role).
    """
    return _line_sections([_Line(line.strip()) for line in lines if line.strip()]).sections


def _style_chain(style):
    """The style and the styles it is based on, stopping where a malformed document loops back.

    A numbering (list) style has no base style in python-docx, so the chain ends there.
    """
    seen = set()
    while style is not None and style.element not in seen:
        seen.add(style.element)
        yield style
        style = getattr(style, "base_style", None)


def _outline_level(ppr) -> int | None:
    """The w:outlineLvl of a paragraph or style: 0 to 8 are heading levels 1 to 9, 9 is body text."""
    from docx.oxml.ns import qn

    level = ppr.find(qn("w:outlineLvl")) if ppr is not None else None
    value = level.get(qn("w:val")) if level is not None else None
    return int(value) if value is not None and value.isdigit() else None


def _docx_style_heading(paragraph) -> bool:
    """A Heading style or an outline level, set on the paragraph or on the style it is based on."""
    level = _outline_level(paragraph._p.pPr)
    if level is not None:
        return level < 9
    for style in _style_chain(paragraph.style):
        if (style.name or "").startswith("Heading"):
            return True
        level = _outline_level(style.element.pPr)
        if level is not None:
            return level < 9
    return False


def _style_bold(style) -> bool | None:
    """The bold setting of the first style in the chain that sets one; a numbering style has no font."""
    fonts = (getattr(s, "font", None) for s in _style_chain(style))
    return next((font.bold for font in fonts if font is not None and font.bold is not None), None)


def _run_bold(run, paragraph_bold: bool) -> bool:
    """Direct formatting first, then the character style, then the paragraph style."""
    for bold in (run.bold, _style_bold(run.style)):
        if bold is not None:
            return bold
    return paragraph_bold


def _docx_fully_bold(paragraph) -> bool:
    """True if every letter after a leading number sits in a bold run, hyperlinks included, not just a
    bold lead-in label. A number typed in plain type before a bold title ("5." then "Risk Factors") counts."""
    from docx.text.hyperlink import Hyperlink

    paragraph_bold = bool(_style_bold(paragraph.style))
    runs = [
        run
        for item in paragraph.iter_inner_content()
        for run in (item.runs if isinstance(item, Hyperlink) else (item,))
    ]
    bold_letters: list[bool] = []
    for run in runs:
        letters = sum(char.isalpha() for char in run.text)
        if letters:
            bold_letters += [_run_bold(run, paragraph_bold)] * letters
    numbering = _NUMBERING.match(paragraph.text.lstrip())
    bold_letters = bold_letters[sum(char.isalpha() for char in numbering.group()) if numbering else 0 :]
    return bool(bold_letters) and all(bold_letters)


def _docx_label_heading(paragraph, text: str) -> bool:
    """A short label (up to 120 characters, or 200 when numbered) that is entirely bold or in capitals."""
    max_words = _max_words(text)
    return (
        len(text) < 10 * max_words
        and _is_label(text, max_words)
        and (text.isupper() or _docx_fully_bold(paragraph))
    )


def parse_docx(path: Path) -> DocumentSections:
    """Parse a DOCX file and group text paragraphs under identified section headings.

    A heading has a Heading style or an outline level, or is a short label that is entirely bold
    or in capitals. Heading text is not section body.
    """
    try:
        import docx
    except ImportError as exc:
        raise SystemExit(
            "DOCX support requires the optional 'docx' extra: pip install micar-whitepaper-linter[docx]"
        ) from exc

    doc = docx.Document(path)
    sections: dict[str, list[str]] = {}
    headings: list[str] = []
    current_keys: list[str] = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        # The Title style names the white paper, not one of its sections.
        if para.style is not None and para.style.name == "Title":
            continue

        if _docx_style_heading(para) or _docx_label_heading(para, text):
            headings.append(text)
            current_keys = match_heading_to_section(text) or current_keys
            continue

        for k in current_keys:
            sections.setdefault(k, []).append(text)

    return DocumentSections({k: "\n".join(v) for k, v in sections.items()}, tuple(headings))


def load_from_docx(path: Path) -> dict[str, str]:
    return parse_docx(path).sections


_BOLD_FACE = re.compile(r"bold|black|heavy|demi", re.I)


def _resolved(value):
    return value.get_object() if hasattr(value, "get_object") else value


def _bold_face(font) -> bool:
    """Bold by name ("Helvetica-Bold", "ABCDEF+Arial-BoldMT") or by a font weight of 600 or more."""
    if font is None:
        return False
    if _BOLD_FACE.search(str(font.get("/BaseFont", ""))):
        return True
    for face in (font, *(_resolved(d) for d in _resolved(font.get("/DescendantFonts")) or ())):
        weight = _resolved((_resolved(face.get("/FontDescriptor")) or {}).get("/FontWeight"))
        if isinstance(weight, int | float) and weight >= 600:
            return True
    return False


def _font_style(cm, tm, font, size) -> tuple[float, bool] | None:
    """The rendered size of a text run (its Tf size scaled by the text and graphics matrices) and its weight."""
    try:
        scale = math.hypot(tm[2] * cm[0] + tm[3] * cm[2], tm[2] * cm[1] + tm[3] * cm[3])
        return abs(float(size)) * scale, _bold_face(font)
    except Exception:
        return None


def _record_run(runs: list[tuple[str, tuple[float, bool] | None]], text, cm, tm, font, size) -> None:
    runs.append((str(text), _font_style(cm, tm, font, size)))


def _pdf_lines(reader) -> list[_Line]:
    """The non-empty text lines of a PDF, with the font of each where pypdf reports it.

    The text visitor of pypdf reports each run of text with its font. Where the runs do not add up to
    the extracted page text (form XObjects, right-to-left text), that page goes by line shape alone.
    """
    lines: list[_Line] = []
    for page in reader.pages:
        runs: list[tuple[str, tuple[float, bool] | None]] = []
        text = page.extract_text(visitor_text=partial(_record_run, runs)) or ""
        styles = (
            [style for run, style in runs for _ in run] if "".join(run for run, _ in runs) == text else []
        )
        end = 0
        for raw in text.splitlines(keepends=True):
            start, end = end, end + len(raw)
            if not raw.strip():
                continue
            letters = [styles[i] for i in range(start, end) if text[i].isalpha()] if styles else []
            if letters and None not in letters:
                lines.append(_Line(raw.strip(), min(s for s, _ in letters), all(b for _, b in letters)))
            else:
                lines.append(_Line(raw.strip()))
    return lines


def parse_pdf(path: Path) -> DocumentSections:
    """Parse a PDF file and extract text grouped under identified section headings.

    A heading is a line that names a section and is set larger or bolder than the body text, or is
    shaped like a heading (see _line_role). A short line that names a section but is not accepted as
    a heading ends the current section. Heading text is not section body.
    """
    try:
        import pypdf
    except ImportError as exc:
        raise SystemExit(
            "PDF support requires the optional 'pdf' extra: pip install micar-whitepaper-linter[pdf]"
        ) from exc

    return _line_sections(_pdf_lines(pypdf.PdfReader(path)))


def load_from_pdf(path: Path) -> dict[str, str]:
    return parse_pdf(path).sections


def load_from_markdown(path: Path) -> dict[str, str]:
    """Parse a Markdown file and extract text grouped under identified section headings."""
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as exc:
        raise SystemExit(f"Error reading Markdown file {path}: {exc}") from exc

    sections: dict[str, list[str]] = {}
    current_keys = []

    for line in content.splitlines():
        line_clean = line.strip()
        if not line_clean:
            continue

        # Detect Markdown headings (e.g. # Heading 1, ## Heading 2)
        heading_match = re.match(r"^#{1,6}\s+(.+)$", line_clean)
        if heading_match:
            heading_text = heading_match.group(1).strip()
            matched_keys = match_heading_to_section(heading_text)
            # Reset current_keys if it's a heading, so we don't leak text into unrelated sections
            current_keys = matched_keys
        else:
            if current_keys:
                for k in current_keys:
                    sections.setdefault(k, []).append(line_clean)

    return {k: "\n".join(v) for k, v in sections.items()}
