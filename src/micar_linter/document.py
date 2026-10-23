"""PDF and DOCX document ingestion and section parsing."""

from __future__ import annotations

import re
from pathlib import Path

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
_SENTENCE_END = re.compile(r"[.!?;,]$")
# A full stop after a word, followed by more text: "Risks. Holders may lose ..." ("A.1 Name" and "5.2 Risks" pass).
_SENTENCE_BREAK = re.compile(r"[^\W\d_]{4,}[.!?]\s+\S")
# "1. Risks", "5.2 Risks", "1) Risks", "A.1 Name", "I. Risks", "IV. Risks", "Part I: Risks", "Teil I Risiken".
_NUMBERING = re.compile(
    r"^(?:\d{1,2}(?:\.\d{1,2})*[.)]|\d{1,2}(?:\.\d{1,2})+|[A-Z]\.\d{1,2}(?:\.\d{1,2})*\.?|[A-Z]\.|[IVX]{1,5}\."
    r"|(?:Part|PART|Teil|TEIL)\s+(?:[A-Z]|[IVX]{1,5}|\d{1,2})[.:)]?)\s+"
)
# Words a title-case heading leaves in lower case: "Information about the Issuer", "Rechte und Pflichten".
_MINOR_WORD = re.compile(
    r"a|about|against|among|an|and|as|at|between|by|for|from|in|into|of|on|or|over|per|than|the|to|under|via"
    r"|with|within|without|am|auf|aus|bei|bzw|das|dem|den|der|des|die|ein|eine|einer|eines|für|im|mit|nach"
    r"|oder|sowie|über|und|von|vom|zu|zum|zur"
)
# Dashes and quotation marks around heading words: en dash, em dash, curly single and double quotes.
_DASHES = "-\u2013\u2014"
_QUOTES = "\"'\u2018\u2019\u201c\u201d"


def _is_label(text: str, max_words: int = _MAX_HEADING_WORDS) -> bool:
    """A short label rather than a sentence: few words and no sentence punctuation after a word."""
    return (
        len(text.split()) <= max_words and not _SENTENCE_END.search(text) and not _SENTENCE_BREAK.search(text)
    )


def _is_title_like(text: str) -> bool:
    """All capitals, or every word other than a short connective starts with a capital."""
    words = [word.strip(f"()[]{_QUOTES},:;") for word in text.split()]
    words = [word for word in words if word[:1].isalpha()]
    if not words or not words[0][0].isupper():
        return False
    return all(not word.islower() or _MINOR_WORD.fullmatch(word) for word in words[1:])


def _is_pdf_heading(line: str) -> bool:
    """A PDF line is a heading only if shaped like one: numbered with a capital after the number,
    or in title case or capitals; a wrapped body line mentioning a section word is neither."""
    numbering = _NUMBERING.match(line)
    if numbering:
        title = line[numbering.end() :].lstrip(f"{_DASHES}:. ")
        return title[:1].isupper() and _is_label(line, _MAX_NUMBERED_HEADING_WORDS)
    return _is_title_like(line) and _is_label(line)


def _style_chain(style):
    while style is not None:
        yield style
        style = style.base_style


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
    return next((s.font.bold for s in _style_chain(style) if s.font.bold is not None), None)


def _run_bold(run, paragraph_bold: bool) -> bool:
    """Direct formatting first, then the character style, then the paragraph style."""
    for bold in (run.bold, _style_bold(run.style)):
        if bold is not None:
            return bold
    return paragraph_bold


def _docx_fully_bold(paragraph) -> bool:
    """True if every non-whitespace character sits in a bold run, not just a bold lead-in label."""
    paragraph_bold = bool(_style_bold(paragraph.style))
    bold = "".join(run.text for run in paragraph.runs if _run_bold(run, paragraph_bold))
    return bool(bold.strip()) and re.sub(r"\s+", "", bold) == re.sub(r"\s+", "", paragraph.text)


def load_from_docx(path: Path) -> dict[str, str]:
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
    current_keys = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        # The Title style names the white paper, not one of its sections.
        if para.style is not None and para.style.name == "Title":
            continue

        is_heading = _docx_style_heading(para) or (
            len(text) < 120 and _is_label(text) and (text.isupper() or _docx_fully_bold(para))
        )

        if is_heading:
            matched_keys = match_heading_to_section(text)
            if matched_keys:
                current_keys = matched_keys
            continue

        if current_keys:
            for k in current_keys:
                sections.setdefault(k, []).append(text)

    return {k: "\n".join(v) for k, v in sections.items()}


def load_from_pdf(path: Path) -> dict[str, str]:
    """Parse a PDF file and extract text grouped under identified section headings.

    PDF text carries no styles, so a heading is a line that names a section and is shaped like a
    heading (see _is_pdf_heading). Heading text is not section body.
    """
    try:
        import pypdf
    except ImportError as exc:
        raise SystemExit(
            "PDF support requires the optional 'pdf' extra: pip install micar-whitepaper-linter[pdf]"
        ) from exc

    reader = pypdf.PdfReader(path)
    full_text_lines = []

    for page in reader.pages:
        text = page.extract_text()
        if text:
            full_text_lines.extend(text.splitlines())

    sections: dict[str, list[str]] = {}
    current_keys = []

    for line in full_text_lines:
        line_clean = line.strip()
        if not line_clean:
            continue

        matched_keys = match_heading_to_section(line_clean)
        if matched_keys and _is_pdf_heading(line_clean):
            current_keys = matched_keys
            continue

        if current_keys:
            for k in current_keys:
                sections.setdefault(k, []).append(line_clean)

    return {k: "\n".join(v) for k, v in sections.items()}


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
