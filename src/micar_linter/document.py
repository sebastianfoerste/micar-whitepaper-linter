"""PDF and DOCX document ingestion and section parsing."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

# Common patterns (in English and German) matching whitepaper section headings.
# Word boundaries are used to avoid false positives.
SECTION_PATTERNS = {
    # The Art. 6(3) / Art. 51(3) statement, labelled as in Implementing Regulation (EU) 2024/2984.
    "not_approved_statement": [
        r"\bstatement\s+in\s+accordance\s+with\s+art(?:icle|\.)\s*(?:6|51)\s*\(3\)",
        r"\berklärung\s+gemäß\s+art(?:ikel|\.)\s*(?:6|51)\s+abs(?:atz|\.)\s*3\b",
    ],
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
    "redemption": [r"\bredemption\b", r"\brücknahme\w*", r"\brücktausch\w*", r"\bredemption\s+right\b"],
    "safeguarding": [r"\bsafeguarding\b", r"\babsicherung\w*", r"\bsicherung\w*.*\bgelder\w*"],
}


# Art. 6(3) and Art. 51(3) MiCAR put the statement on the first page without a heading of
# its own, so a paragraph that opens with it is routed by its content. The German opening
# is a routing heuristic only; the rule does not treat it as verified statutory wording.
_STATEMENT_START = re.compile(
    r"^\W*(?:this\s+crypto-asset\s+white\s+paper\s+has\s+not\s+been\s+approved"
    r"|dieses\s+kryptowerte-whitepaper\s+wurde\s+von\s+keiner)\b",
    re.IGNORECASE,
)
# The statement has two sentences: the one opening above, then the one naming who is solely
# responsible for the content. Each is about 20 words in Art. 6(3) and Art. 51(3).
_RESPONSIBILITY = re.compile(r"\b(?:responsib|verantwort)\w*", re.IGNORECASE)
_SENTENCE_END = re.compile(r"[.!?](?=\s|$)")
_STATEMENT_MAX_LINES = 12
_SENTENCE_MAX_WORDS = 30
_HEADING_MAX_WORDS = 12


def is_statement_start(text: str) -> bool:
    """True where a line or paragraph opens with the Art. 6(3) / Art. 51(3) statement."""
    return bool(_STATEMENT_START.match(text))


def looks_like_heading(text: str) -> bool:
    """True for a Markdown heading, or a short line without closing punctuation that names a section."""
    stripped = text.strip()
    if stripped.startswith("#"):
        return True
    if not stripped or len(stripped.split()) > _HEADING_MAX_WORDS or stripped[-1] in ".,;:!?":
        return False
    return bool(match_heading_to_section(stripped))


def statement_extent(lines: list[str], start: int, is_heading: Callable[[int], bool] | None = None) -> int:
    """Index after the last line of the statement that opens at lines[start].

    A wrapped statement in a PDF or a hard-wrapped Markdown file spans several lines, and
    its continuation lines often contain words such as "crypto-asset" or "offeror" that the
    heading heuristics would otherwise read as new section headings. The statement ends
    with its opening sentence, or with the next sentence where that one is short and says
    who is responsible. It never runs past a heading, so an incomplete or reworded
    statement cannot swallow the sections that follow it.

    is_heading(index) reports a heading the loader knows for certain, such as a DOCX
    paragraph in a Heading style.
    """
    window = lines[start : start + _STATEMENT_MAX_LINES]
    text = " ".join(window)
    line_ends: list[int] = []
    offset = 0
    for line in window:
        line_ends.append(offset + len(line))
        offset += len(line) + 1

    def firm_heading(i: int) -> bool:
        return window[i].lstrip().startswith("#") or (is_heading is not None and is_heading(start + i))

    def line_at(position: int) -> int:
        return next(i for i, line_end in enumerate(line_ends) if line_end >= position)

    # Continuation lines of the opening sentence never name a section, so a line that ends
    # inside it and looks like a heading means the sentence was cut short. The line where
    # the sentence ends may already start the next one ("Union. The offeror"), so it is
    # not read as a heading.
    first = _SENTENCE_END.search(text)
    first_end = first.end() if first else len(text) + 1
    for i in range(1, len(window)):
        if line_ends[i] < first_end and (looks_like_heading(window[i]) or firm_heading(i)):
            return start + i
    if first is None:
        return start + 1
    last = line_at(first_end)

    # The responsibility sentence of a narrow PDF column can look like a heading
    # ("The offeror of the crypto-asset is solely"), so only firm headings end it early.
    second = _SENTENCE_END.search(text, first_end)
    if second is None:
        return start + last + 1
    sentence = text[first_end : second.end()]
    if len(sentence.split()) > _SENTENCE_MAX_WORDS or not _RESPONSIBILITY.search(sentence):
        return start + last + 1
    closing = line_at(second.end())
    if any(firm_heading(i) for i in range(last + 1, closing + 1)):
        return start + last + 1
    return start + closing + 1


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


def load_from_docx(path: Path) -> dict[str, str]:
    """Parse a DOCX file and group text paragraphs under identified section headings."""
    try:
        import docx
    except ImportError as exc:
        raise SystemExit(
            "DOCX support requires the optional 'docx' extra: pip install micar-whitepaper-linter[docx]"
        ) from exc

    doc = docx.Document(path)
    sections: dict[str, list[str]] = {}
    current_keys = []
    paragraphs = [(para, para.text.strip()) for para in doc.paragraphs if para.text.strip()]
    texts = [text for _, text in paragraphs]
    statement_end = 0

    for index, (para, text) in enumerate(paragraphs):
        if index < statement_end or is_statement_start(text):
            if index >= statement_end:
                statement_end = statement_extent(
                    texts, index, lambda i: paragraphs[i][0].style.name.startswith("Heading")
                )
            sections.setdefault("not_approved_statement", []).append(text)
            continue

        is_heading = (
            para.style.name.startswith("Heading")
            or (any(run.bold for run in para.runs) and len(text) < 120)
            or (text.isupper() and len(text) < 120)
        )

        if is_heading:
            matched_keys = match_heading_to_section(text)
            if matched_keys:
                current_keys = matched_keys

        if current_keys:
            for k in current_keys:
                sections.setdefault(k, []).append(text)

    return {k: "\n".join(v) for k, v in sections.items()}


def load_from_pdf(path: Path) -> dict[str, str]:
    """Parse a PDF file and extract text grouped under identified section headings."""
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
    lines = [line.strip() for line in full_text_lines if line.strip()]
    statement_end = 0

    for index, line_clean in enumerate(lines):
        if index < statement_end or is_statement_start(line_clean):
            if index >= statement_end:
                statement_end = statement_extent(lines, index)
            sections.setdefault("not_approved_statement", []).append(line_clean)
            continue

        # Heuristics for PDF line headings
        is_heading = False
        if len(line_clean) < 120:
            matched_keys = match_heading_to_section(line_clean)
            if matched_keys:
                is_heading = True

        if is_heading:
            matched_keys = match_heading_to_section(line_clean)
            if matched_keys:
                current_keys = matched_keys

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
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    statement_end = 0

    for index, line_clean in enumerate(lines):
        if index < statement_end or is_statement_start(line_clean):
            if index >= statement_end:
                statement_end = statement_extent(lines, index)
            sections.setdefault("not_approved_statement", []).append(line_clean)
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
