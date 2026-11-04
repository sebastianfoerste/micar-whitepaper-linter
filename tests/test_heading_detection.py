"""A DOCX paragraph or PDF line opens a section only if it is shaped like a heading.

A body paragraph with a bold lead-in ("Note: ...") in a DOCX, or a short body line in a PDF, that
mentions "risks" used to open a risks section, so a draft with no risk section passed the ANNEX_I.I
blocker. In a PDF, list items, wrapped lines and lead-ins stay in their section, a line shaped like a
heading but not accepted as one ends the section before it, and a bold or larger font marks a heading.
Heading text is not section body, but regime inference still reads it. The PDFs are real files parsed
by pypdf.
"""

from __future__ import annotations

import textwrap
import threading
import time
import tracemalloc
from html import escape
from pathlib import Path

import docx
import pytest
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from micar_linter.anchors import _xhtml_section_identifiers
from micar_linter.document import (
    _SENTENCE_BREAK,
    _sentence_breaks,
    load_from_docx,
    load_from_markdown,
    load_from_pdf,
    match_heading_to_section,
)
from micar_linter.linter import lint_whitepaper
from micar_linter.locations import _xhtml_heading_lines
from micar_linter.rules.base import Finding, Severity
from micar_linter.whitepaper import (
    _ART_MARKERS,
    WhitepaperType,
    _names_regime,
    _regime_pieces,
    load_whitepaper,
)
from micar_linter.xhtml_parser import load_from_xhtml

# An invented issuer. None of the body text below matches a section pattern except the note.
SUMMARY = (
    "The Quillmoor Utility Token (QMT) gives holders access to a shared ledger service for logistics firms."
)
PROJECT = "Quillmoor Ledger S.A. runs the shared ledger service for logistics firms in three Member States."
# Body text, not a heading: in the DOCX only "Note:" is bold, in the PDF it is one short line.
NOTE = "Note: purchasers bear market, liquidity and technology risks."
RISK_DETAIL = (
    "Holders may sell units only where a market exists, and prices can move sharply within a single day. "
    "Liquidity can disappear when few buyers are active, so holders may be unable to exit at a fair price. "
    "A change in regulatory treatment in any Member State could restrict transfers or require new licences. "
    "Operational failures at the service provider, such as outages or faulty software updates, can delay "
    "transfers for days. Keys held by holders can be lost or stolen, and lost keys cannot be recovered by "
    "anyone. Smart contract defects can freeze balances until a fix is deployed and accepted by the network. "
    "Buyers in the offer bear the risk that the project is delayed or stopped, and the mitigation measures of "
    "the operator shorten outages without preventing them. "
    "Holders should read this document in full and seek independent advice before they buy units. Past "
    "performance of similar services does not indicate future returns, and holders may lose the full amount."
)
TECHNOLOGY = "Transfers settle on a permissioned ledger operated by five validating nodes."


def _draft(*risk_heading: tuple[str, str]) -> list[tuple[str, str]]:
    """(kind, text) blocks; the risk discussion sits under the project unless a risk heading is given."""
    return [
        ("heading", "Summary"),
        ("body", SUMMARY),
        ("heading", "Information about the Project"),
        ("body", PROJECT),
        *risk_heading,
        ("note", NOTE),
        ("body", RISK_DETAIL),
        ("heading", "Underlying Technology"),
        ("body", TECHNOLOGY),
    ]


def _write_docx(path: Path, blocks: list[tuple[str, str]]) -> Path:
    doc = docx.Document()
    for kind, text in blocks:
        if kind == "title":
            doc.add_paragraph(text, style="Title")
        elif kind in ("heading", "large"):
            doc.add_heading(text, level=1)
        elif kind == "subheading":
            doc.add_heading(text, level=2)
        elif kind == "list bullet":
            # Word shows the bullet; the text of the paragraph does not hold it.
            doc.add_paragraph(text, style="List Bullet")
        elif kind in ("bold", "bold body"):
            doc.add_paragraph().add_run(text).bold = True
        elif kind == "outline":
            # A Normal paragraph that Word lists in the navigation pane as a level 1 heading.
            level = OxmlElement("w:outlineLvl")
            level.set(qn("w:val"), "0")
            paragraph = doc.add_paragraph(text)
            paragraph._p.get_or_add_pPr().append(level)
        elif kind == "note":
            label, rest = text.split(" ", 1)
            paragraph = doc.add_paragraph()
            paragraph.add_run(label).bold = True
            paragraph.add_run(f" {rest}")
        elif kind == "numbered":
            # A number typed in plain type, then the title in bold.
            number, title = text.split(" ", 1)
            paragraph = doc.add_paragraph()
            paragraph.add_run(f"{number}\t")
            paragraph.add_run(title).bold = True
        elif kind == "link":
            # A bold title that is also an internal link, so its run sits inside w:hyperlink.
            run = OxmlElement("w:r")
            properties = OxmlElement("w:rPr")
            properties.append(OxmlElement("w:b"))
            run.append(properties)
            run_text = OxmlElement("w:t")
            run_text.text = text
            run.append(run_text)
            link = OxmlElement("w:hyperlink")
            link.set(qn("w:anchor"), "risks")
            link.append(run)
            doc.add_paragraph()._p.append(link)
        else:
            doc.add_paragraph(text)
    doc.save(path)
    return path


# 10 pt Helvetica for body text and plain lines; Helvetica-Bold in 10 pt for "bold" lines and "bold body"
# text, 11 pt for "subheading" lines, 14 pt for "large" ones and 20 pt for a "title". In a DOCX, "large" is
# a Heading 1, "subheading" a Heading 2 and "title" a Title-style paragraph.
PDF_FONTS = {
    "bold": "/F2 10 Tf",
    "bold body": "/F2 10 Tf",
    "subheading": "/F2 11 Tf",
    "large": "/F2 14 Tf",
    "title": "/F2 20 Tf",
}


def _shown(kind: str, line: str, next_line: str) -> str:
    """The content stream operators of one block line; a "space" block only moves 20 pt further down."""
    if kind == "space":
        return "0 -20 Td"
    escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return f"{PDF_FONTS.get(kind, '/F1 10 Tf')} ({escaped}) Tj {next_line}"


def _write_pdf(path: Path, blocks: list[tuple[str, str]], next_line: str = "0 -13 Td") -> Path:
    """A PDF with one text line per block, 13 pt apart, and body text wrapped at 90 characters.

    The lines of a paragraph and the paragraphs follow each other with no space between them, as in a
    draft that sets none, unless a "space" block moves further down. Each line moves to the next with
    next_line: Td, as word processors write, or T* after a TL leading. A "page" block starts a new page.
    """
    pages: list[list[tuple[str, str]]] = [[]]
    for kind, text in blocks:
        if kind == "page":
            pages.append([])
        else:
            wrapped = textwrap.wrap(text, 90) if kind in ("body", "bold body") else [text]
            pages[-1].extend((kind, line) for line in wrapped)
    fonts = b"/Font << /F1 3 0 R /F2 4 0 R >>"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [%s] /Count %d >>"
        % (b" ".join(b"%d 0 R" % (5 + 2 * number) for number in range(len(pages))), len(pages)),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
    ]
    for number, lines in enumerate(pages):
        shown = " ".join(_shown(kind, line, next_line) for kind, line in lines)
        content = f"BT 13 TL 50 770 Td {shown} ET".encode("cp1252")
        objects.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 1000 792] /Resources << %s >> /Contents %d 0 R >>"
            % (fonts, 6 + 2 * number)
        )
        objects.append(b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream")
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, 1):
        offsets.append(len(pdf))
        pdf += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(pdf)
    pdf += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    pdf += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    pdf += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
    path.write_bytes(bytes(pdf))
    return path


WRITERS = {".docx": (_write_docx, load_from_docx), ".pdf": (_write_pdf, load_from_pdf)}


def _risks_finding(path: Path) -> Finding:
    report = lint_whitepaper(load_whitepaper(path, WhitepaperType.OTHER))
    return next(finding for finding in report.findings if finding.rule.rule_id == "ANNEX_I.I")


def _words(text: str) -> str:
    return " ".join(text.split())


def test_docx_bold_lead_in_paragraph_does_not_open_a_risk_section(tmp_path: Path):
    path = _write_docx(tmp_path / "quillmoor.docx", _draft())

    finding = _risks_finding(path)
    assert finding.rule.severity is Severity.BLOCKER
    assert finding.status == "missing"
    sections = load_from_docx(path)
    assert "risks" not in sections
    assert NOTE in sections["project"]


def test_pdf_body_line_mentioning_risks_does_not_open_a_risk_section(tmp_path: Path):
    path = _write_pdf(tmp_path / "quillmoor.pdf", _draft())

    finding = _risks_finding(path)
    assert finding.rule.severity is Severity.BLOCKER
    assert finding.status == "missing"
    sections = load_from_pdf(path)
    assert "risks" not in sections
    assert NOTE in sections["project"]


@pytest.mark.parametrize(
    "kind,heading",
    [("heading", "Risks"), ("bold", "Risk Factors"), ("body", "RISK FACTORS"), ("outline", "Risks")],
)
def test_docx_risk_heading_still_opens_the_risk_section(tmp_path: Path, kind: str, heading: str):
    path = _write_docx(tmp_path / "quillmoor.docx", _draft((kind, heading)))

    assert _words(RISK_DETAIL) in _words(load_from_docx(path)["risks"])
    assert _risks_finding(path).status == "pass"


@pytest.mark.parametrize(
    "heading", ["Risks", "3. Risk Factors", "RISK FACTORS", "Part I: Information on Risks"]
)
def test_pdf_risk_heading_still_opens_the_risk_section(tmp_path: Path, heading: str):
    path = _write_pdf(tmp_path / "quillmoor.pdf", _draft(("heading", heading)))

    assert _words(RISK_DETAIL) in _words(load_from_pdf(path)["risks"])
    assert _risks_finding(path).status == "pass"


@pytest.mark.parametrize("suffix", sorted(WRITERS))
def test_heading_text_is_not_section_body(tmp_path: Path, suffix: str):
    write, load = WRITERS[suffix]
    blocks = [
        ("heading", "Summary"),
        ("body", SUMMARY),
        ("heading", "Risks"),
        ("heading", "Underlying Technology"),
        ("body", TECHNOLOGY),
    ]
    path = write(tmp_path / f"quillmoor{suffix}", blocks)

    # A risks heading with nothing under it leaves the section empty.
    finding = _risks_finding(path)
    assert (finding.status, finding.word_count) == ("missing", 0)
    sections = load(path)
    assert "risks" not in sections
    assert _words(sections["summary"]) == SUMMARY
    assert _words(sections["technology"]) == TECHNOLOGY


# The part titles of Implementing Regulation (EU) 2024/2984 separate the part letter with an en dash.
DASH = chr(0x2013)
# A risk discussion that passes the ANNEX_I.I blocker wherever it is credited to the risks section.
RISK_TEXT = RISK_DETAIL + " Technology failures at the ledger can also stop transfers for days."
THIN_SUMMARY = "This summary gives the key information on the QMT token."


def _findings(
    path: Path, whitepaper_type: WhitepaperType | None = WhitepaperType.OTHER
) -> dict[str, Finding]:
    report = lint_whitepaper(load_whitepaper(path, whitepaper_type))
    return {finding.rule.rule_id: finding for finding in report.findings}


@pytest.mark.parametrize(
    "heading", ["Risk factors", "Beschreibung der wesentlichen Risiken", "5. Risks relating to the token"]
)
def test_pdf_line_rejected_as_a_heading_ends_the_section_before_it(tmp_path: Path, heading: str):
    # Shaped like a heading but not in title case: the risk text below it must not reach the summary.
    blocks = [
        ("heading", "Summary"),
        ("body", THIN_SUMMARY),
        ("heading", heading),
        ("body", RISK_TEXT),
        ("heading", "Underlying Technology"),
        ("body", TECHNOLOGY),
    ]
    path = _write_pdf(tmp_path / "quillmoor.pdf", blocks)

    sections = load_from_pdf(path)
    assert sorted(sections) == ["summary", "technology"]
    assert _words(sections["summary"]) == THIN_SUMMARY
    findings = _findings(path)
    assert findings["COMMON.SUMMARY"].rule.severity is Severity.BLOCKER
    assert (findings["COMMON.SUMMARY"].status, findings["COMMON.SUMMARY"].word_count) == ("review", 10)
    assert findings["ANNEX_I.I"].status == "missing"


@pytest.mark.parametrize("kind", ["bold", "large"])
@pytest.mark.parametrize("heading", ["Risk factors", "5. Risks relating to the token"])
def test_pdf_heading_font_marks_a_sentence_case_heading(tmp_path: Path, kind: str, heading: str):
    blocks = [("large", "Summary"), ("body", SUMMARY), (kind, heading), ("body", RISK_TEXT)]
    path = _write_pdf(tmp_path / "quillmoor.pdf", blocks)

    sections = load_from_pdf(path)
    assert "risks" in sections
    assert _words(sections["risks"]) == _words(RISK_TEXT)
    assert _findings(path)["ANNEX_I.I"].status == "pass"


# Lines in the project section that name risks without being a heading, and whether the risk text after
# them stays in the project section (body) or is credited to no section (the line ends the section).
PROJECT_LINES = {
    "numbered list item": (
        [
            "Key features of the project:",
            "1. Shared ledger for logistics firms",
            "2. Low fees compared with legacy systems",
            "3. Exposure to market, liquidity and technology risks",
        ],
        True,
    ),
    "bullet item": (["Holders should consider:", "• Market and Technology Risks"], True),
    "dash item": (["- Market and Technology Risks"], True),
    "wrapped capitals": (
        [
            "PURCHASERS SHOULD CAREFULLY CONSIDER THE MARKET, LIQUIDITY AND",
            "TECHNOLOGY RISKS DESCRIBED IN THIS DOCUMENT BEFORE THEY BUY ANY UNITS",
            "OF THE TOKEN.",
        ],
        True,
    ),
    "wrapped german nouns": (
        [
            "Quillmoor betreibt den Dienst in drei Mitgliedstaaten. Anleger sollten die",
            "Risiken der Token und der Plattform",
            "beachten, bevor sie Einheiten kaufen.",
        ],
        True,
    ),
    "capitals line running on": (
        ["HOLDERS BEAR TECHNOLOGY RISKS AND", "MAY LOSE THE FULL AMOUNT INVESTED."],
        False,
    ),
    "sentence running on after a german abbreviation": (
        ["Anleger tragen die Risiken", "z. B. Markt- und Liquiditätsrisiken des Tokens."],
        True,
    ),
    "sentence-case lead-in": (["Note on the risks:"], True),
    "title-case lead-in": (["Holders Should Note These Risks:"], False),
    "title-case numbered list": (
        [
            "The project has three features.",
            "1. Shared Ledger.",
            "2. Low Fees.",
            "3. Market and Technology Risks",
        ],
        False,
    ),
}


@pytest.mark.parametrize("case", sorted(PROJECT_LINES))
def test_pdf_list_and_wrapped_lines_open_no_section(tmp_path: Path, case: str):
    lines, stays_in_project = PROJECT_LINES[case]
    blocks = [
        ("heading", "Summary"),
        ("body", SUMMARY),
        ("heading", "Information about the Project"),
        ("body", PROJECT),
        *(("line", line) for line in lines),
        ("body", RISK_TEXT),
        ("heading", "Underlying Technology"),
        ("body", TECHNOLOGY),
    ]
    path = _write_pdf(tmp_path / "quillmoor.pdf", blocks)

    sections = load_from_pdf(path)
    assert sorted(sections) == ["project", "summary", "technology"]
    assert (_words(RISK_TEXT) in _words(sections["project"])) is stays_in_project
    findings = _findings(path)
    assert findings["ANNEX_I.I"].rule.severity is Severity.BLOCKER
    assert findings["ANNEX_I.I"].status == "missing"


# Part titles of the Implementing Regulation as bold Normal paragraphs, each with up to 20 words.
RIGHTS = "Holders have rights and obligations; each holder may exercise rights in court under the terms. " * 6
OFFER = (
    "The offer to the public runs from 2 March 2026 at a price of 1 EUR per token in three Member States. "
    * 4
)
ISSUER = (
    "The issuer is Quillmoor Ledger S.A., registered at 4 Rue Quillmoor, Luxembourg, as a public company. "
    * 3
)
PART_TITLES = {
    "B": (f"Part B {DASH} Information about the issuer, if different from the offeror or person seeking admission "
          "to trading", "issuer", ISSUER, "ANNEX_I.B", "review"),
    "E": (f"Part E {DASH} Information about the offer to the public of crypto-assets or their admission to "
          "trading", "offer_or_admission", OFFER, "ANNEX_I.E", "review"),
    "G": (f"Part G {DASH} Information on the rights and obligations attached to the crypto-assets",
          "rights_and_obligations", RIGHTS, "ANNEX_I.G", "pass"),
}  # fmt: skip


@pytest.mark.parametrize("part", sorted(PART_TITLES))
def test_docx_bold_part_title_of_the_template_is_a_heading(tmp_path: Path, part: str):
    title, key, text, rule_id, status = PART_TITLES[part]
    blocks = [
        ("heading", "Summary"),
        ("body", SUMMARY),
        ("bold", f"Part D {DASH} Information about the crypto-asset project"),
        ("body", PROJECT),
        ("bold", title),
        ("body", text),
        ("bold", f"Part H {DASH} Information on the underlying technology"),
        ("body", TECHNOLOGY),
    ]
    path = _write_docx(tmp_path / "quillmoor.docx", blocks)

    sections = load_from_docx(path)
    assert _words(sections[key]) == _words(text)
    assert _words(sections["project"]) == PROJECT
    findings = _findings(path)
    assert (findings[rule_id].status, findings[rule_id].word_count) == (status, len(text.split()))
    assert findings["ANNEX_I.D"].word_count == len(PROJECT.split())


# The same part titles without the part letter, as many drafts set them: 13 to 16 words, so only their
# bold type (DOCX) or heading font (PDF) marks them as headings.
GERMAN_OFFEROR = (
    "Der Anbieter ist die Quillmoor Ledger S.A. mit Sitz in Luxemburg. Sie ist im Handelsregister unter der "
    "Nummer B 123456 eingetragen und beschäftigt vierzig Mitarbeiter in Luxemburg und Hamburg. "
) * 2
UNNUMBERED_TITLES = {
    "B": ("Information about the issuer, if different from the offeror or person seeking admission to trading",
          ["issuer", "offer_or_admission", "offeror"], ISSUER, "ANNEX_I.B", Severity.MAJOR, "review"),
    "E": ("Information about the offer to the public of crypto-assets or their admission to trading",
          ["offer_or_admission"], OFFER, "ANNEX_I.E", Severity.BLOCKER, "review"),
    "A-de": ("Informationen über den Anbieter oder die Person, die die Zulassung zum Handel beantragt",
             ["offer_or_admission", "offeror"], GERMAN_OFFEROR, "ANNEX_I.A", Severity.BLOCKER, "review"),
}  # fmt: skip


@pytest.mark.parametrize(
    "suffix,kind", [(".docx", "bold"), (".pdf", "large")], ids=["docx-bold", "pdf-14pt-bold"]
)
@pytest.mark.parametrize("part", sorted(UNNUMBERED_TITLES))
def test_unnumbered_part_title_of_up_to_twenty_words_is_a_heading_when_marked(
    tmp_path: Path, suffix: str, kind: str, part: str
):
    title, keys, text, rule_id, severity, status = UNNUMBERED_TITLES[part]
    write, load = WRITERS[suffix]
    blocks = [
        (kind, "Summary"),
        ("body", SUMMARY),
        (kind, "Information about the crypto-asset project"),
        ("body", PROJECT),
        (kind, title),
        ("body", text),
        (kind, "Information on the underlying technology"),
        ("body", TECHNOLOGY),
    ]
    path = write(tmp_path / f"quillmoor{suffix}", blocks)

    sections = load(path)
    assert sorted(sections) == sorted({"summary", "project", "crypto_asset", "technology", *keys})
    for key in keys:
        assert _words(sections[key]) == _words(text)
    # The thin project section keeps its own text and does not pass on the part after it.
    assert _words(sections["project"]) == PROJECT
    findings = _findings(path)
    assert findings["ANNEX_I.D"].rule.severity is Severity.BLOCKER
    assert (findings["ANNEX_I.D"].status, findings["ANNEX_I.D"].word_count) == (
        "review",
        len(PROJECT.split()),
    )
    assert findings[rule_id].rule.severity is severity
    assert (findings[rule_id].status, findings[rule_id].word_count) == (status, len(text.split()))


# Headings in a 14 pt bold heading font that wrap onto a second line, as LibreOffice and Chrome export the
# long part titles: (first line, second line, sections, section text, rule, status of that rule).
WRAPPED_HEADINGS = {
    "numbered, lower case": (
        "5. Information about the offer to the public of crypto-assets or their",
        "admission to trading",
        ["offer_or_admission"], OFFER, "ANNEX_I.E", "review",
    ),
    "unnumbered, lower case": (
        "Information about the offer to the public of crypto-assets or their",
        "admission to trading",
        ["offer_or_admission"], OFFER, "ANNEX_I.E", "review",
    ),
    "title case, hyphen": (
        "7. Information on the Rights and Obligations Attached to the Crypto-",
        "Assets",
        ["rights_and_obligations"], RIGHTS, "ANNEX_I.G", "pass",
    ),
    "title case, capital": (
        f"Part B {DASH} Information About the Issuer, If Different From the Offeror or Person",
        "Seeking Admission to Trading",
        ["issuer", "offer_or_admission", "offeror"], ISSUER, "ANNEX_I.B", "review",
    ),
    "german": (
        "6. Informationen über den Anbieter oder die Person, die die Zulassung zum",
        "Handel beantragt",
        ["offer_or_admission", "offeror"], GERMAN_OFFEROR, "ANNEX_I.A", "review",
    ),
}  # fmt: skip


@pytest.mark.parametrize("next_line", ["0 -13 Td", "T*"])
@pytest.mark.parametrize("case", sorted(WRAPPED_HEADINGS))
def test_pdf_heading_wrapped_onto_two_lines_in_the_heading_font_is_one_heading(
    tmp_path: Path, case: str, next_line: str
):
    first, second, keys, text, rule_id, status = WRAPPED_HEADINGS[case]
    blocks = [
        ("large", "Summary"),
        ("body", SUMMARY),
        ("large", "4. Information about the crypto-asset project"),
        ("body", PROJECT),
        ("large", first),
        ("large", second),
        ("body", text),
        ("large", "8. Information on the underlying technology"),
        ("body", TECHNOLOGY),
    ]
    # pypdf misreports the heights of lines laid out with T*, so there the font alone joins the lines.
    path = _write_pdf(tmp_path / "quillmoor.pdf", blocks, next_line)

    sections = load_from_pdf(path)
    assert sorted(sections) == sorted({"summary", "project", "crypto_asset", "technology", *keys})
    for key in keys:
        assert _words(sections[key]) == _words(text)
    # The thin project section before the wrapped heading does not pass on the part under it.
    assert _words(sections["project"]) == PROJECT
    findings = _findings(path)
    assert findings["ANNEX_I.D"].rule.severity is Severity.BLOCKER
    assert (findings["ANNEX_I.D"].status, findings["ANNEX_I.D"].word_count) == (
        "review",
        len(PROJECT.split()),
    )
    assert (findings[rule_id].status, findings[rule_id].word_count) == (status, len(text.split()))


def test_pdf_headings_one_paragraph_apart_in_the_heading_font_stay_two_headings(tmp_path: Path):
    # A heading with nothing under it, then the next heading: the space between paragraphs keeps them
    # apart, so the risks section stays empty instead of passing on the text under the next heading
    # (risk-like text here, so that a merged heading would pass ANNEX_I.I).
    blocks = [
        ("large", "Summary"),
        ("body", SUMMARY),
        ("large", "Risk Factors"),
        ("space", ""),
        ("large", "Information on the Underlying Technology"),
        ("body", RISK_TEXT),
    ]
    path = _write_pdf(tmp_path / "quillmoor.pdf", blocks)

    sections = load_from_pdf(path)
    assert sorted(sections) == ["summary", "technology"]
    assert _words(sections["technology"]) == _words(RISK_TEXT)
    findings = _findings(path)
    assert findings["ANNEX_I.I"].rule.severity is Severity.BLOCKER
    assert findings["ANNEX_I.I"].status == "missing"


@pytest.mark.parametrize("next_line", ["0 -13 Td", "T*"])
def test_pdf_short_heading_one_line_above_the_next_heading_stays_a_heading(tmp_path: Path, next_line: str):
    # As above, but with no space between the paragraphs, and in a PDF laid out with T*, where the font
    # alone decides: "Risk Factors" neither runs on nor fills the column, so it is not joined with the
    # heading below it.
    blocks = [
        ("large", "Summary"),
        ("body", SUMMARY),
        ("large", "Risk Factors"),
        ("large", "Information on the Underlying Technology"),
        ("body", RISK_TEXT),
    ]
    path = _write_pdf(tmp_path / "quillmoor.pdf", blocks, next_line)

    sections = load_from_pdf(path)
    assert sorted(sections) == ["summary", "technology"]
    assert _words(sections["technology"]) == _words(RISK_TEXT)
    findings = _findings(path)
    assert findings["ANNEX_I.I"].rule.severity is Severity.BLOCKER
    assert findings["ANNEX_I.I"].status == "missing"


def test_pdf_short_heading_over_a_lower_case_line_in_its_font_stays_a_heading(tmp_path: Path):
    # A heading that wraps after a short first line, as in a narrow column. "Risk Factors" neither runs on
    # nor fills the column, so it is not joined with "and Mitigation Measures"; it does not start a
    # paragraph either, which fills the column. So it opens the risks, and the risk text below does not
    # pass the thin technology section before it.
    blocks = [
        ("large", "Summary"),
        ("body", SUMMARY),
        ("large", "Information on the Underlying Technology"),
        ("body", THIN_TECHNOLOGY),
        ("large", "Risk Factors"),
        ("large", "and Mitigation Measures"),
        ("body", RISK_TEXT),
    ]
    path = _write_pdf(tmp_path / "quillmoor.pdf", blocks)

    sections = load_from_pdf(path)
    assert sorted(sections) == ["risks", "summary", "technology"]
    assert _words(sections["technology"]) == _words(THIN_TECHNOLOGY)
    assert _words(RISK_TEXT) in _words(sections["risks"])
    findings = _findings(path)
    assert findings["ANNEX_I.H"].rule.severity is Severity.BLOCKER
    assert (findings["ANNEX_I.H"].status, findings["ANNEX_I.H"].word_count) == (
        "review",
        len(THIN_TECHNOLOGY.split()),
    )
    assert findings["ANNEX_I.I"].status == "pass"


# The opening statements of a white paper, set under bold headings in the body size. The summary alone is
# too thin to pass COMMON.SUMMARY.
KEY_SUMMARY = (
    "This summary gives the key information about the Quillmoor Utility Token (QMT) in plain language. The "
    "token gives holders access to a shared ledger service for logistics firms. Holders should read the "
    "whole white paper before they buy units."
)
WARNING = (
    "This crypto-asset white paper has not been reviewed or approved by any competent authority in any "
    "Member State of the European Union. The offeror of the crypto-asset is solely responsible for the "
    "content of this crypto-asset white paper. The crypto-asset may lose its value in part or in full, may "
    "not always be transferable and may not be liquid."
)
STATEMENT = (
    "The management body of Quillmoor Ledger S.A. confirms that this crypto-asset white paper complies "
    "with Title II of Regulation (EU) 2023/1114 and that, to the best of its knowledge, the information "
    "presented is fair, clear and not misleading and that the white paper makes no omission likely to "
    "affect its import."
)


@pytest.mark.parametrize("suffix", sorted(WRITERS))
@pytest.mark.parametrize("bold_statement", [False, True], ids=["bold-warning", "bold-warning-and-statement"])
def test_heading_over_a_bold_paragraph_with_no_space_between_stays_a_heading(
    tmp_path: Path, suffix: str, bold_statement: bool
):
    # With no space between paragraphs, the bold headings sit one line spacing above and below the bold
    # risk warning. They are not joined with it: each heading opens its own section and the bold paragraph
    # is the body of its heading, so the thin summary does not pass on the statements after it.
    write, load = WRITERS[suffix]
    blocks = [
        ("bold", "Summary"),
        ("body", KEY_SUMMARY),
        ("bold", "Risk warning"),
        ("bold body", WARNING),
        ("bold", "Statement by the management body"),
        ("bold body" if bold_statement else "body", STATEMENT),
        ("bold", "Information on risks"),
        ("body", RISK_TEXT),
    ]
    path = write(tmp_path / f"quillmoor{suffix}", blocks)

    sections = load(path)
    assert sorted(sections) == ["management_statement", "risk_warning", "risks", "summary"]
    assert _words(sections["summary"]) == KEY_SUMMARY
    assert _words(sections["risk_warning"]) == _words(WARNING)
    assert _words(sections["management_statement"]) == _words(STATEMENT)
    findings = _findings(path)
    for rule_id, text in [
        ("COMMON.SUMMARY", KEY_SUMMARY),
        ("COMMON.RISK_WARNING", WARNING),
        ("COMMON.MANAGEMENT_STATEMENT", STATEMENT),
    ]:
        assert findings[rule_id].rule.severity is Severity.BLOCKER
        assert findings[rule_id].word_count == len(text.split())
    assert findings["COMMON.SUMMARY"].status == "review"
    assert findings["COMMON.MANAGEMENT_STATEMENT"].status == "pass"
    assert findings["ANNEX_I.I"].status == "pass"


# A risk section written as a list whose items start in lower case.
RISK_ITEMS = [
    "a) Market risk: prices can move sharply within a single day and holders may lose the full amount.",
    "b) Liquidity risk: liquidity can disappear when few buyers are active, so holders may be unable to exit.",
    "c) Regulatory risk: a change in regulatory treatment in any Member State could restrict transfers.",
    "d) Operational risk: outages or faulty software updates at the service provider can delay transfers.",
    "e) Software risk: code defects can freeze balances until a fix is deployed and accepted.",
    "f) Custody risk: keys held by holders can be lost or stolen, and lost keys cannot be recovered by anyone.",
]
THIN_TECHNOLOGY = (
    "Transfers settle on a permissioned ledger with a Byzantine fault tolerant consensus protocol. Smart "
    "contracts implement the unit register, and an independent firm audits the code once a year."
)


@pytest.mark.parametrize(
    "kind,technology,heading",
    [
        ("large", "4. Underlying Technology", "Risk Factors"),
        ("large", "4. Technologie", "5. Risiken"),
        # Without a heading font the shape decides, and a list item after a line does not make it body text.
        ("heading", "Underlying Technology", "Risk Factors"),
    ],
    ids=["14pt-bold", "14pt-bold-german", "body-font"],
)
def test_pdf_heading_before_a_lower_case_list_item_is_a_heading(
    tmp_path: Path, kind: str, technology: str, heading: str
):
    blocks = [
        (kind, "Summary"),
        ("body", SUMMARY),
        (kind, technology),
        ("body", THIN_TECHNOLOGY),
        (kind, heading),
        *(("line", item) for item in RISK_ITEMS),
    ]
    path = _write_pdf(tmp_path / "quillmoor.pdf", blocks)

    sections = load_from_pdf(path)
    assert sorted(sections) == ["risks", "summary", "technology"]
    assert _words(sections["technology"]) == _words(THIN_TECHNOLOGY)
    assert _words(sections["risks"]) == _words(" ".join(RISK_ITEMS))
    findings = _findings(path)
    # The thin technology section does not pass on the risk list, and the risk section is not missing.
    assert findings["ANNEX_I.H"].rule.severity is Severity.BLOCKER
    assert (findings["ANNEX_I.H"].status, findings["ANNEX_I.H"].word_count) == (
        "review",
        len(THIN_TECHNOLOGY.split()),
    )
    assert findings["ANNEX_I.I"].rule.severity is Severity.BLOCKER
    assert findings["ANNEX_I.I"].status != "missing"


def test_pdf_line_running_on_into_a_lower_case_line_is_read_with_it_by_shape(tmp_path: Path):
    # Without a heading font: "or" runs on into "their admission to trading", and the two lines together
    # are the numbered template title of Part E.
    blocks = [
        ("heading", "Summary"),
        ("body", SUMMARY),
        ("line", f"Part D {DASH} Information about the crypto-asset project"),
        ("body", PROJECT),
        ("line", f"Part E {DASH} Information about the offer to the public of crypto-assets or"),
        ("line", "their admission to trading"),
        ("body", OFFER),
    ]
    path = _write_pdf(tmp_path / "quillmoor.pdf", blocks)

    sections = load_from_pdf(path)
    assert sorted(sections) == ["crypto_asset", "offer_or_admission", "project", "summary"]
    assert _words(sections["offer_or_admission"]) == _words(OFFER)
    findings = _findings(path)
    assert (findings["ANNEX_I.D"].status, findings["ANNEX_I.D"].word_count) == (
        "review",
        len(PROJECT.split()),
    )
    assert findings["ANNEX_I.E"].rule.severity is Severity.BLOCKER
    assert (findings["ANNEX_I.E"].status, findings["ANNEX_I.E"].word_count) == ("review", len(OFFER.split()))


def test_pdf_part_title_of_twenty_words_and_a_dash_is_a_heading(tmp_path: Path):
    part_j = (
        f"Part J {DASH} Information on the sustainability indicators in relation to adverse impact on the climate "
        "and other environment-related adverse impacts"
    )
    environment = (
        "The consensus mechanism uses little energy, so climate and environmental impacts are low. " * 8
    )
    blocks = [
        ("heading", f"Part I {DASH} Information on risks"),
        ("body", RISK_TEXT),
        ("heading", part_j),
        ("body", environment),
    ]
    path = _write_pdf(tmp_path / "quillmoor.pdf", blocks)

    sections = load_from_pdf(path)
    assert sorted(sections) == ["environmental_impact", "risks"]
    assert _words(sections["risks"]) == _words(RISK_TEXT)
    findings = _findings(path)
    assert (findings["ANNEX_I.I"].status, findings["ANNEX_I.J"].status) == ("pass", "pass")


@pytest.mark.parametrize("suffix", sorted(WRITERS))
def test_regime_is_inferred_from_heading_text(tmp_path: Path, suffix: str):
    write, _ = WRITERS[suffix]
    blocks = [
        ("heading", "Summary"),
        ("body", "The QAR token is described here in plain language for retail holders."),
        ("heading", "Reserve of Assets"),
        ("body", "The reserve is held at two credit institutions in cash and bonds."),
        ("heading", "Redemption"),
        ("body", "Holders may redeem at any time."),
    ]
    path = write(tmp_path / f"quillmoor{suffix}", blocks)

    # Only the headings name the regime; with no stated regime the draft is still read as an ART.
    whitepaper = load_whitepaper(path)
    assert whitepaper.type is WhitepaperType.ART
    assert sorted(whitepaper.sections) == ["redemption", "reserve_of_assets", "summary"]
    findings = _findings(path, None)
    assert findings["ANNEX_II.I"].rule.severity is Severity.BLOCKER
    assert findings["ANNEX_II.I"].status == "review"
    assert findings["ANNEX_II.G.COMPOSITION_DISCLOSURE"].status == "review"


@pytest.mark.parametrize("suffix", sorted(WRITERS))
def test_regime_is_inferred_from_text_in_no_section(tmp_path: Path, suffix: str):
    # Only the introduction before the first heading names the regime, and it belongs to no section.
    write, _ = WRITERS[suffix]
    blocks = [
        (
            "body",
            "This white paper describes the QAR, an asset-referenced token issued by Quillmoor Ledger S.A.",
        ),
        ("heading", "Summary"),
        ("body", "The QAR token is described here in plain language for retail holders."),
        ("heading", "Redemption"),
        ("body", "Holders may redeem at any time."),
    ]
    path = write(tmp_path / f"quillmoor{suffix}", blocks)

    whitepaper = load_whitepaper(path)
    assert whitepaper.type is WhitepaperType.ART
    assert sorted(whitepaper.sections) == ["redemption", "summary"]
    # The Annex II BLOCKERs run: the redemption check reviews its thin section.
    findings = _findings(path, None)
    assert findings["ANNEX_II.I"].rule.severity is Severity.BLOCKER
    assert (findings["ANNEX_II.I"].status, findings["ANNEX_II.I"].word_count) == ("review", 6)


@pytest.mark.parametrize("suffix", sorted(WRITERS))
@pytest.mark.parametrize(
    "introduction",
    [
        "Synthetic MeadowPoints white paper. This crypto-asset is not an asset-referenced token and not an "
        "e-money token.",
        "MeadowPoints is neither an asset-referenced token nor an e-money token, and it has no reserve of assets.",
        "This white paper is drawn up under Title II of Regulation (EU) 2023/1114, for crypto-assets other than "
        "asset-referenced tokens or e-money tokens.",
    ],
)
def test_a_negated_regime_marker_does_not_switch_the_regime(tmp_path: Path, suffix: str, introduction: str):
    # An Annex I white paper says in its introduction what its token is not. Read as a marker, the negated
    # phrase made the draft an ART: the Annex I rules did not run and the crypto-asset section was dropped.
    write, _ = WRITERS[suffix]
    blocks = [
        ("body", introduction),
        ("heading", "Information about the Offeror"),
        ("body", "Meadow Labs GmbH, a fictional company, offers the MeadowPoints loyalty token to the public."),
        ("heading", "Information about the Crypto-Asset"),
        ("body", "MeadowPoints is a fictional loyalty token with a fixed supply of ten million units."),
        ("heading", "Risk Factors"),
        ("body", "Holders may lose the full amount, and the token may not always be transferable."),
    ]
    path = write(tmp_path / f"meadowpoints{suffix}", blocks)

    whitepaper = load_whitepaper(path)
    assert whitepaper.type is WhitepaperType.OTHER
    assert sorted(whitepaper.sections) == ["crypto_asset", "offeror", "risks"]
    findings = _findings(path, None)
    assert "ANNEX_I.I" in findings and "ANNEX_II.A" not in findings


@pytest.mark.parametrize("suffix", sorted(WRITERS))
def test_a_negation_before_a_heading_does_not_reach_the_heading(tmp_path: Path, suffix: str):
    # The risk paragraph ends in a negation and no full stop, and the next line is the heading that alone
    # names the regime. A heading is judged on its own words, so the draft is still read as an ART.
    write, _ = WRITERS[suffix]
    blocks = [
        ("heading", "Information about the Issuer"),
        ("body", "Synthetic Issuer AG, a fictional company, issues the token."),
        ("heading", "Risk Factors"),
        ("body", "Holders should note that the token is not covered by any investor compensation scheme"),
        ("heading", "Reserve of Assets"),
        ("body", "The reserve is held in cash and short-term government bonds."),
    ]
    path = write(tmp_path / f"synthetic{suffix}", blocks)

    whitepaper = load_whitepaper(path)
    assert whitepaper.type is WhitepaperType.ART
    assert sorted(whitepaper.sections) == ["issuer", "reserve_of_assets", "risks"]
    findings = _findings(path, None)
    assert "ANNEX_II.G.COMPOSITION_DISCLOSURE" in findings and "ANNEX_I.I" not in findings


@pytest.mark.parametrize("suffix", sorted(WRITERS))
def test_a_negation_reaches_across_paragraphs_between_two_headings(tmp_path: Path, suffix: str):
    # A DOCX may split one sentence over paragraphs with no colon. Between two headings the paragraphs are
    # one piece, so the negation in the first still governs the markers in the next; read paragraph by
    # paragraph, the draft loaded as an ART and the Annex I rules did not run.
    write, _ = WRITERS[suffix]
    blocks = [
        ("body", "The token described here is neither"),
        ("body", "an asset-referenced token nor"),
        ("body", "an e-money token"),
        ("heading", "Information about the Offeror"),
        ("body", "Meadow Labs GmbH, a fictional company, offers the MeadowPoints loyalty token to the public."),
        ("heading", "Risk Factors"),
        ("body", "Holders may lose the full amount, and the token may not always be transferable."),
    ]
    path = write(tmp_path / f"meadowpoints{suffix}", blocks)
    assert load_whitepaper(path).type is WhitepaperType.OTHER


def test_a_negation_at_the_end_of_a_markdown_section_does_not_reach_the_next(tmp_path: Path):
    # Markdown headings are not read for the regime, so the reserve section's own text names it.
    path = tmp_path / "synthetic.md"
    path.write_text(
        "# Risk Factors\n\nHolders should note that the token is not covered by any compensation scheme\n\n"
        "# Reserve of Assets\n\nReserve of assets: cash and short-term government bonds.\n",
        encoding="utf-8",
    )
    assert load_whitepaper(path).type is WhitepaperType.ART


_SST_ISSUER = [
    ("heading", "Information about the Issuer"),
    (
        "body",
        "Synthetic Issuer AG, a fictional company, issues the Synthetic Stable Token (SST) to the public in the Union.",
    ),
]


@pytest.mark.parametrize("suffix", sorted(WRITERS))
@pytest.mark.parametrize(
    ("blocks", "regime"),
    [
        # A list item without a full stop, then a paragraph or line that starts a new sentence: the negation
        # of the first does not reach the marker in the second.
        (
            [
                *_SST_ISSUER,
                ("heading", "Risk Factors"),
                ("body", "Holders have no claim against the custodian"),
                ("body", "The reserve of assets may lose value in a market stress event and be insufficient"),
            ],
            WhitepaperType.ART,
        ),
        (
            [
                *_SST_ISSUER,
                ("heading", "Risk Factors"),
                ("body", "Holders are not covered by deposit guarantee schemes"),
                ("body", "The e-money token may be redeemed at par only on a business day in the Union"),
            ],
            WhitepaperType.EMT,
        ),
        # The same with a plain-style "Reserve of Assets" paragraph, which is no heading.
        (
            [
                *_SST_ISSUER,
                ("heading", "Risk Factors"),
                ("body", "Holders should note that the token is not covered by any investor compensation scheme"),
                ("body", "Reserve of Assets"),
                ("body", "The reserve is held in cash and short-term government bonds."),
            ],
            WhitepaperType.ART,
        ),
        # Cover lines.
        (
            [
                ("body", "Synthetic Euro Token, not approved by any competent authority"),
                ("body", "E-money token issued by Synthetic Bank AG"),
                *_SST_ISSUER,
            ],
            WhitepaperType.EMT,
        ),
        # A negated lead-in governs each dash, bullet or bracket item of the list after it, also where the items
        # end in a semicolon, and also where a PDF reads the lead-in as a heading that ends in a negation.
        (
            [
                ("body", "For the purposes of MiCAR the token is not"),
                ("body", "- an asset-referenced token;"),
                ("body", "- an e-money token."),
                *_SST_ISSUER,
            ],
            WhitepaperType.OTHER,
        ),
        # The same list without dashes: a line after one that ends in a semicolon continues the lead-in.
        (
            [
                ("body", "For the purposes of MiCAR the token is not"),
                ("body", "an asset-referenced token;"),
                ("body", "an e-money token."),
                *_SST_ISSUER,
            ],
            WhitepaperType.OTHER,
        ),
        # A dash item that starts a new sentence after a line that ends in neither a colon nor a negation.
        (
            [
                *_SST_ISSUER,
                ("heading", "Risk Factors"),
                ("body", "Holders have no claim against the custodian"),
                ("body", "- The reserve of assets may lose value in a market stress event"),
            ],
            WhitepaperType.ART,
        ),
        # A colon at the end of a lead-in introduces the lines after it.
        (
            [
                ("body", "The token is neither:"),
                ("body", "an asset-referenced token, nor"),
                ("body", "an e-money token."),
                *_SST_ISSUER,
            ],
            WhitepaperType.OTHER,
        ),
    ],
    ids=[
        "no claim, then reserve of assets",
        "not covered, then e-money token",
        "plain Reserve of Assets paragraph",
        "cover lines",
        "negated lead-in, then a dash list",
        "negated lead-in, then items ending in a semicolon",
        "capitalised dash item after a line without a colon",
        "neither with a colon",
    ],
)
def test_a_negation_reaches_the_lines_that_continue_its_sentence_only(
    tmp_path: Path, suffix: str, blocks: list[tuple[str, str]], regime: WhitepaperType
):
    # Between two headings a negation reaches a paragraph or line that continues its sentence (one that
    # starts in lower case, or a list item after a lead-in that ends without a full stop), but not one that
    # starts a new sentence with a capital letter.
    write, _ = WRITERS[suffix]
    assert load_whitepaper(write(tmp_path / f"synthetic{suffix}", blocks)).type is regime


@pytest.mark.parametrize("suffix", sorted(WRITERS))
@pytest.mark.parametrize(
    ("blocks", "regime"),
    [
        # Round 3 of the follow-up verification: a line that starts with a digit or with a name in lower case
        # starts a new sentence too, so the negation of the line before does not reach it.
        (
            [
                *_SST_ISSUER,
                ("heading", "Risk Factors"),
                ("body", "Holders have no claim against the custodian"),
                ("body", "100% of the reserve of assets is held in cash and short-term government bonds."),
            ],
            WhitepaperType.ART,
        ),
        (
            [
                *_SST_ISSUER,
                ("heading", "Risk Factors"),
                ("body", "Holders should note that the token is not covered by any compensation scheme"),
                ("body", "xStable's reserve of assets is held in cash."),
            ],
            WhitepaperType.ART,
        ),
        (
            [
                *_SST_ISSUER,
                ("heading", "Risk Factors"),
                ("body", "Holders are not covered by deposit guarantee schemes"),
                ("body", "1 e-money token is redeemable at par."),
            ],
            WhitepaperType.EMT,
        ),
        # A heading that the PDF sets in the body font is no heading of the loader, but a line shaped like a
        # title is judged on its own words, so its negation does not reach the next line.
        (
            [*_SST_ISSUER, ("heading", "No Investor Compensation"), ("body", "the reserve of assets is held in cash.")],
            WhitepaperType.ART,
        ),
        # Controls: a title-like line that ends in a negation still leads into the next line, and a title
        # shaped like a negated marker is negated.
        (
            [*_SST_ISSUER, ("body", "The Synthetic Token Is Not"), ("body", "an asset-referenced token.")],
            WhitepaperType.OTHER,
        ),
        ([*_SST_ISSUER, ("body", "No Reserve of Assets"), ("body", "The token is a utility token.")], WhitepaperType.OTHER),
    ],
    ids=[
        "no claim, then a line that starts with a digit",
        "not covered, then a name in lower case",
        "deposit guarantee, then a number",
        "title in the body font",
        "title ending in a negation",
        "negated title",
    ],
)
def test_a_line_that_starts_a_sentence_otherwise_than_with_a_capital_ends_the_negation(
    tmp_path: Path, suffix: str, blocks: list[tuple[str, str]], regime: WhitepaperType
):
    # A genuine ART or EMT draft whose only marker sat in such a line loaded as other (main: art or emt).
    write, _ = WRITERS[suffix]
    assert load_whitepaper(write(tmp_path / f"synthetic{suffix}", blocks)).type is regime


@pytest.mark.parametrize(
    "field,answer,key",
    [
        (
            "01 Date of notification",
            "2 March 2026, the date of notification to the BaFin.",
            "notification_date",
        ),
        (
            "08 Characteristics of the crypto-asset",
            "QMT is a utility token on a permissioned ledger.",
            "crypto_asset",
        ),
    ],
    ids=["01", "08"],
)
def test_pdf_two_digit_summary_field_opens_its_section(tmp_path: Path, field: str, answer: str, key: str):
    blocks = [
        ("heading", "Summary"),
        ("body", SUMMARY),
        ("line", field),
        ("line", answer),
        ("heading", f"Part I {DASH} Information on risks"),
        ("body", RISK_TEXT),
    ]
    path = _write_pdf(tmp_path / "quillmoor.pdf", blocks)

    sections = load_from_pdf(path)
    assert sorted(sections) == sorted(["risks", "summary", key])
    assert sections[key] == answer
    assert _words(sections["summary"]) == SUMMARY
    findings = _findings(path)
    assert findings["COMMON.NOTIFICATION_DATE"].status == (
        "pass" if key == "notification_date" else "missing"
    )
    assert findings["ANNEX_I.I"].status == "pass"


@pytest.mark.parametrize("kind", ["numbered", "link"])
def test_docx_bold_heading_with_a_plain_number_or_a_link_is_a_heading(tmp_path: Path, kind: str):
    heading = "5. Risk Factors" if kind == "numbered" else "Risk Factors"
    blocks = [("heading", "Summary"), ("body", SUMMARY), (kind, heading), ("body", RISK_TEXT)]
    path = _write_docx(tmp_path / "quillmoor.docx", blocks)

    sections = load_from_docx(path)
    assert sorted(sections) == ["risks", "summary"]
    assert _findings(path)["ANNEX_I.I"].status == "pass"


@pytest.mark.parametrize("suffix,kind", [(".docx", "bold"), (".pdf", "line")], ids=["docx-bold", "pdf-line"])
@pytest.mark.parametrize(
    "heading",
    ["5. Risks (incl. Liquidity Risks)", "Quillmoor Corp. Risk Factors", "Risiken bzgl. des Tokens"],
)
def test_abbreviation_in_a_heading_is_not_a_sentence_break(
    tmp_path: Path, suffix: str, kind: str, heading: str
):
    write, load = WRITERS[suffix]
    path = write(
        tmp_path / f"quillmoor{suffix}",
        [("heading", "Summary"), ("body", SUMMARY), (kind, heading), ("body", RISK_TEXT)],
    )

    assert sorted(load(path)) == ["risks", "summary"]
    assert _findings(path)["ANNEX_I.I"].status == "pass"


# Part F: its official title names the crypto-assets in the plural. The plural in the titles of Part E
# and Part G does not make them crypto-asset sections.
CRYPTO_ASSETS = (
    "The QMT units are utility tokens on a permissioned ledger. Each unit entitles its holder to record one "
    "hundred transfers. The units are fungible and transferable between onboarded holders. "
) * 3


@pytest.mark.parametrize("suffix", sorted(WRITERS))
def test_part_f_title_with_crypto_assets_in_the_plural_opens_its_section(tmp_path: Path, suffix: str):
    write, load = WRITERS[suffix]
    blocks = [
        ("large", "Summary"),
        ("body", SUMMARY),
        (
            "large",
            f"Part E {DASH} Information about the offer to the public of crypto-assets or their admission",
        ),
        ("body", OFFER),
        ("large", f"Part F {DASH} Information about the crypto-assets"),
        ("body", CRYPTO_ASSETS),
        ("large", f"Part G {DASH} Information on the rights and obligations attached to the crypto-assets"),
        ("body", RIGHTS),
    ]
    path = write(tmp_path / f"quillmoor{suffix}", blocks)

    sections = load(path)
    assert sorted(sections) == ["crypto_asset", "offer_or_admission", "rights_and_obligations", "summary"]
    assert _words(sections["crypto_asset"]) == _words(CRYPTO_ASSETS)
    assert _words(sections["offer_or_admission"]) == _words(OFFER)
    findings = _findings(path)
    assert findings["ANNEX_I.E"].rule.severity is Severity.BLOCKER
    assert (findings["ANNEX_I.E"].status, findings["ANNEX_I.E"].word_count) == ("review", len(OFFER.split()))
    assert findings["ANNEX_I.F"].rule.severity is Severity.BLOCKER
    assert findings["ANNEX_I.F"].word_count == len(CRYPTO_ASSETS.split())


THIN_RISKS = "Holders may lose the full amount they paid for their units."


@pytest.mark.parametrize("suffix", sorted(WRITERS))
@pytest.mark.parametrize(
    "heading", ["Glossary", f"Part K {DASH} Glossary"], ids=["heading-font", "template-part"]
)
def test_heading_that_names_no_section_ends_the_section_before_it(tmp_path: Path, suffix: str, heading: str):
    # The text under "Glossary" reads like risk text, so it would pass ANNEX_I.I if it joined the risks.
    write, load = WRITERS[suffix]
    blocks = [
        ("large", "Summary"),
        ("body", SUMMARY),
        ("large", "Risk Factors"),
        ("body", THIN_RISKS),
        ("large", heading),
        ("body", RISK_TEXT),
    ]
    path = write(tmp_path / f"quillmoor{suffix}", blocks)

    sections = load(path)
    assert sorted(sections) == ["risks", "summary"]
    assert _words(sections["risks"]) == THIN_RISKS
    findings = _findings(path)
    assert findings["ANNEX_I.I"].rule.severity is Severity.BLOCKER
    assert (findings["ANNEX_I.I"].status, findings["ANNEX_I.I"].word_count) == ("review", 11)


@pytest.mark.parametrize("suffix", sorted(WRITERS))
def test_sub_heading_that_names_no_section_stays_in_its_section(tmp_path: Path, suffix: str):
    # A smaller heading font (PDF) or a Heading 2 (DOCX) under "Risk Factors" is part of the risks.
    write, load = WRITERS[suffix]
    blocks = [
        ("large", "Summary"),
        ("body", SUMMARY),
        ("large", "Risk Factors"),
        ("body", THIN_RISKS),
        ("subheading", "Market Volatility"),
        ("body", RISK_TEXT),
        ("large", "Glossary"),
        ("body", TECHNOLOGY),
    ]
    path = write(tmp_path / f"quillmoor{suffix}", blocks)

    sections = load(path)
    assert sorted(sections) == ["risks", "summary"]
    assert _words(RISK_TEXT) in _words(sections["risks"])
    assert TECHNOLOGY not in _words(sections["risks"])
    assert _findings(path)["ANNEX_I.I"].status == "pass"


# A risk section split into one paragraph per risk, under labels that name no section. Together the
# paragraphs pass ANNEX_I.I; the first alone does not.
RISK_PARTS = [
    (
        "Market risk",
        "Holders may sell units only where a market exists, and prices can move sharply within a single day. "
        "Past performance of similar services does not indicate future returns, and holders may lose the full "
        "amount. Holders should read this document in full and seek independent advice before they buy units.",
    ),
    (
        "Liquidity risk",
        "Liquidity can disappear when few buyers are active after the offer, so holders may be unable to exit "
        "at a fair price.",
    ),
    (
        "Regulatory risk",
        "A change in regulatory treatment in any Member State could restrict transfers or require new licences.",
    ),
    (
        "Operational risk",
        "Operational failures at the service provider, such as outages or faulty software updates, can delay "
        "transfers for days and set the project back. Keys held by holders can be lost or stolen, and lost keys "
        "cannot be recovered.",
    ),
    (
        "Smart contract risk",
        "Smart contract defects can freeze balances until a fix is deployed and accepted by the network. "
        "Technology failures at the ledger can also stop transfers for days; the mitigation measures of the "
        "operator shorten such outages without preventing them.",
    ),
]
GERMAN_RISK_LABELS = [
    "Marktrisiko",
    "Liquiditätsrisiko",
    "Regulatorisches Risiko",
    "Operationelles Risiko",
    "Smart-Contract-Risiko",
]
# The risk headings: the heading that opens the section and the labels of its paragraphs.
RISK_HEADINGS = {
    "numbered": (
        "12. Information on risks",
        [f"12.{n} {label}" for n, (label, _) in enumerate(RISK_PARTS, 1)],
    ),
    "unnumbered": ("Information on risks", [label for label, _ in RISK_PARTS]),
    "german": (
        "12. Informationen über die Risiken",
        [f"12.{n} {label}" for n, label in enumerate(GERMAN_RISK_LABELS, 1)],
    ),
}


def _risk_blocks(kind: str, opener: str, labels: list[str]) -> list[tuple[str, str]]:
    """A summary, the risk heading and the risk paragraphs under their labels, every heading in kind,
    then a "Glossary" in the larger heading font."""
    blocks = [(kind, "Summary"), ("body", SUMMARY), (kind, opener)]
    for label, (_, text) in zip(labels, RISK_PARTS, strict=True):
        blocks += [(kind, label), ("body", text)]
    return [*blocks, ("large", "Glossary"), ("body", TECHNOLOGY)]


def _assert_risk_parts_pass(path: Path, sections: dict[str, str]) -> None:
    """Every risk paragraph is in the risk section, the glossary text is not, and ANNEX_I.I passes."""
    assert sorted(sections) == ["risks", "summary"]
    risks = _words(sections["risks"])
    assert all(_words(text) in risks for _, text in RISK_PARTS)
    assert TECHNOLOGY not in risks
    findings = _findings(path)
    assert findings["ANNEX_I.I"].rule.severity is Severity.BLOCKER
    assert findings["ANNEX_I.I"].status == "pass"


@pytest.mark.parametrize("suffix", sorted(WRITERS))
@pytest.mark.parametrize("case", sorted(RISK_HEADINGS))
def test_bold_label_under_a_bold_heading_stays_in_its_section(tmp_path: Path, suffix: str, case: str):
    # "12.1 Market risk" or "Market risk" in bold under a bold "12. Information on risks": a bold DOCX
    # label and a PDF line in bold at the body size are sub-headings, not the next section.
    write, load = WRITERS[suffix]
    opener, labels = RISK_HEADINGS[case]
    path = write(tmp_path / f"quillmoor{suffix}", _risk_blocks("bold", opener, labels))

    _assert_risk_parts_pass(path, load(path))


@pytest.mark.parametrize("suffix", sorted(WRITERS))
@pytest.mark.parametrize("case", sorted(RISK_HEADINGS))
def test_heading_numbered_below_or_naming_one_risk_stays_in_the_risk_section(
    tmp_path: Path, suffix: str, case: str
):
    # The labels have the Heading 1 style or the 14 pt heading font of the risk heading, the same rank.
    # "12.1" extends the number of "12.", and "Market risk" names one risk, so each stays in the risks.
    write, load = WRITERS[suffix]
    opener, labels = RISK_HEADINGS[case]
    path = write(tmp_path / f"quillmoor{suffix}", _risk_blocks("large", opener, labels))

    _assert_risk_parts_pass(path, load(path))


@pytest.mark.parametrize("suffix", sorted(WRITERS))
def test_cover_title_that_names_a_section_sets_no_heading_level(tmp_path: Path, suffix: str):
    # A large cover title that names the crypto-asset section opens it in a PDF (a DOCX skips the Title
    # style). The headings after it keep their own level, so "Glossary" in the font of "Risk Factors"
    # still ends the risks, in the PDF as in the DOCX.
    write, load = WRITERS[suffix]
    blocks = [
        ("title", "Crypto-Asset White Paper for the Quillmoor Utility Token"),
        ("space", ""),
        ("large", "Summary"),
        ("body", SUMMARY),
        ("large", "Risk Factors"),
        ("body", THIN_RISKS),
        ("large", "Glossary"),
        ("body", RISK_TEXT),
    ]
    path = write(tmp_path / f"quillmoor{suffix}", blocks)

    sections = load(path)
    assert _words(sections["risks"]) == THIN_RISKS
    findings = _findings(path)
    assert findings["ANNEX_I.I"].rule.severity is Severity.BLOCKER
    assert (findings["ANNEX_I.I"].status, findings["ANNEX_I.I"].word_count) == ("review", 11)


# Rows of the summary table of Implementing Regulation (EU) 2024/2984 as pypdf reads them: the field
# number, the label and a one-line answer on one line, or a wrapped label followed by its answer.
SUMMARY_TABLE = [
    "01 Date of notification 2 February 2026",
    "02 Statement in accordance",
    "with Article 6(3) of",
    "Regulation (EU) 2023/1114",
    "This crypto-asset white paper has not been approved by any competent authority in any Member State.",
    "04 Statement in accordance",
    "with Article 6(5) of",
    "Regulation (EU) 2023/1114",
    "The crypto-asset may lose its value in part or in full and may not always be transferable.",
    "08 Characteristics of the crypto-",
    "asset",
    "The QMT units are utility tokens that give access to the shared ledger service.",
]


def test_pdf_summary_table_field_that_names_no_section_ends_the_field_before_it(tmp_path: Path):
    blocks = [
        ("large", "Summary"),
        *(("line", line) for line in SUMMARY_TABLE),
        ("large", f"Part A {DASH} Information about the offeror or the person seeking admission to trading"),
        ("line", "A.1 Name Quillmoor Ledger S.A."),
        ("line", "A.2 Legal form Societe anonyme"),
        ("line", "A.3 Registered address 12 Rue de la Gare, L-1611 Luxembourg"),
        ("large", f"Part I {DASH} Information on risks"),
        ("body", RISK_TEXT),
    ]
    path = _write_pdf(tmp_path / "quillmoor.pdf", blocks)

    sections = load_from_pdf(path)
    # The answer on the field line stays usable; the statements of fields 02 and 04 are no answer to it.
    assert sections["notification_date"] == "2 February 2026"
    assert sections["crypto_asset"] == SUMMARY_TABLE[-1]
    # The numbered fields of Part A belong to Part A.
    assert "A.3 Registered address 12 Rue de la Gare" in sections["offeror"]
    findings = _findings(path)
    assert findings["COMMON.NOTIFICATION_DATE"].rule.severity is Severity.MAJOR
    # The three words are a calendar date, which is all the field asks for.
    assert (findings["COMMON.NOTIFICATION_DATE"].status, findings["COMMON.NOTIFICATION_DATE"].word_count) == (
        "pass",
        3,
    )
    assert findings["ANNEX_I.A"].rule.severity is Severity.BLOCKER
    assert findings["ANNEX_I.A"].status != "missing"
    assert findings["ANNEX_I.I"].status == "pass"


# German drafts head the date of notification in the words of the German texts: Art. 6 Abs. 8, Art. 19
# Abs. 7 and Art. 51 Abs. 7 MiCAR ask for "das Datum seiner Übermittlung", and the Implementing Regulation
# (EU) 2024/2984 template labels field 01 (I.01 for ARTs and EMTs) "Datum der Mitteilung". "Datum der
# Notifizierung" spells out "Notifizierungsdatum", and "Übermittlungsdatum" and "Mitteilungsdatum" are the
# terms of the two texts as compounds.
GERMAN_NOTIFICATION_HEADINGS = [
    "Datum der Übermittlung",
    "Datum der Mitteilung",
    "Datum der Notifizierung",
    "Übermittlungsdatum",
    "Mitteilungsdatum",
]
# Labels of other fields of the German template that name an "Übermittlung" or a "Datum": the type of
# submission (F.5, B.8 and B.5), the methods of transferring value on reimbursement (E.25) and the
# publication date (F.10, B.12 and B.9).
GERMAN_OTHER_LABELS = [
    "Art der Übermittlung",
    "F.5 Die Art der Übermittlung",
    "E.25 Methoden der Übermittlung des Werts bei einer Rückerstattung",
    "F.10 Datum der Veröffentlichung",
]
GERMAN_SUMMARY = (
    "Der Quillmoor Utility Token (QMT) gibt seinen Inhabern Zugang zu einem gemeinsamen Ledger für "
    "Logistikunternehmen."
)
GERMAN_NOTIFICATION = (
    "Das Whitepaper wurde der BaFin am 2. März 2026 übermittelt, und dieses Datum gilt als Tag der "
    "Mitteilung."
)
GERMAN_TECHNOLOGY = "Übertragungen werden auf einem Ledger mit fünf validierenden Knoten abgewickelt."


@pytest.mark.parametrize(
    "heading",
    [
        *GERMAN_NOTIFICATION_HEADINGS,
        "DATUM DER ÜBERMITTLUNG",
        "Datum der Übermittlung des Kryptowerte-Whitepapers",
        "01 Datum der Mitteilung",
        "I.01 Datum der Mitteilung",
    ],
)
def test_german_notification_date_heading_names_the_notification_date(heading: str):
    assert match_heading_to_section(heading) == ["notification_date"]


# Marketing communications ("Marketingmitteilungen", Art. 7 MiCAR) are no notification, and the word
# boundary keeps "Mitteilungsdatum" from matching inside a longer word.
@pytest.mark.parametrize(
    "label", [*GERMAN_OTHER_LABELS, "Datum der Marketingmitteilung", "Marketingmitteilungsdatum"]
)
def test_other_german_template_label_does_not_name_the_notification_date(label: str):
    assert "notification_date" not in match_heading_to_section(label)


def _write_markdown(path: Path, blocks: list[tuple[str, str]]) -> Path:
    """A Markdown draft: each heading block a level 2 heading, each other block a paragraph."""
    markdown = "\n\n".join(f"## {text}" if kind == "heading" else text for kind, text in blocks)
    path.write_text(f"{markdown}\n", encoding="utf-8")
    return path


def _write_xhtml(path: Path, blocks: list[tuple[str, str]]) -> Path:
    """An XHTML draft with one element per line from line 4: each heading or large block an h2 and each
    subheading block an h3, whose id is "heading-" and its number, counted from 1, each other block a
    paragraph."""
    elements = []
    headings = 0
    for kind, text in blocks:
        if kind in ("heading", "large", "subheading"):
            headings += 1
            tag = "h3" if kind == "subheading" else "h2"
            elements.append(f'<{tag} id="heading-{headings}">{escape(text)}</{tag}>')
        else:
            elements.append(f"<p>{escape(text)}</p>")
    body = "\n".join(elements)
    path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<html xmlns="http://www.w3.org/1999/xhtml" lang="de">\n<body>\n{body}\n</body>\n</html>\n',
        encoding="utf-8",
    )
    return path


# WRITERS, and Markdown and heading-based XHTML, which share the heading patterns.
ALL_WRITERS = {
    **WRITERS,
    ".md": (_write_markdown, load_from_markdown),
    ".xhtml": (_write_xhtml, load_from_xhtml),
}


def _german_draft(heading: str, text: str, summary: str = GERMAN_SUMMARY) -> list[tuple[str, str]]:
    """A German draft: a summary, text under heading, and a technology section that ends it."""
    return [
        ("heading", "Zusammenfassung"),
        ("body", summary),
        ("heading", heading),
        ("body", text),
        ("heading", "Technologie"),
        ("body", GERMAN_TECHNOLOGY),
    ]


@pytest.mark.parametrize("suffix", sorted(ALL_WRITERS))
@pytest.mark.parametrize("heading", GERMAN_NOTIFICATION_HEADINGS)
def test_german_notification_date_heading_opens_its_section(tmp_path: Path, suffix: str, heading: str):
    write, load = ALL_WRITERS[suffix]
    path = write(tmp_path / f"quillmoor{suffix}", _german_draft(heading, GERMAN_NOTIFICATION))

    sections = load(path)
    assert sorted(sections) == ["notification_date", "summary", "technology"]
    assert _words(sections["notification_date"]) == GERMAN_NOTIFICATION
    assert _words(sections["summary"]) == GERMAN_SUMMARY
    finding = _findings(path)["COMMON.NOTIFICATION_DATE"]
    assert finding.rule.severity is Severity.MAJOR
    assert (finding.status, finding.word_count) == ("pass", len(GERMAN_NOTIFICATION.split()))


@pytest.mark.parametrize("suffix", sorted(ALL_WRITERS))
def test_other_german_template_labels_open_no_notification_date_section(tmp_path: Path, suffix: str):
    # The type of submission ("Neu" for a new white paper), the methods of transferring value and the
    # publication date are not the date of notification, so the check still reports it missing.
    write, load = ALL_WRITERS[suffix]
    blocks = [
        ("heading", "Zusammenfassung"),
        ("body", GERMAN_SUMMARY),
        ("heading", "Art der Übermittlung"),
        ("body", "Neu"),
        ("heading", "Methoden der Übermittlung des Werts bei einer Rückerstattung"),
        ("body", "Die Rückerstattung erfolgt durch Überweisung auf das Konto des Käufers."),
        ("heading", "Datum der Veröffentlichung"),
        ("body", "Das Whitepaper wird am 16. März 2026 veröffentlicht."),
        ("heading", "Technologie"),
        ("body", GERMAN_TECHNOLOGY),
    ]
    path = write(tmp_path / f"quillmoor{suffix}", blocks)

    assert "notification_date" not in load(path)
    finding = _findings(path)["COMMON.NOTIFICATION_DATE"]
    assert (finding.status, finding.word_count) == ("missing", 0)


def test_pdf_german_summary_table_row_gives_its_answer_to_the_notification_date(tmp_path: Path):
    # Field 01 of the German summary table as pypdf reads it, with the answer on the label line. Field 02
    # opens the first-page statement's section, so it ends field 01 and its statement is no answer to it.
    blocks = [
        ("large", "Zusammenfassung"),
        ("line", "01 Datum der Mitteilung 2026-03-02"),
        ("line", "02 Erklärung gemäß Artikel 6 Absatz 3 der Verordnung (EU) 2023/1114"),
        (
            "line",
            "Dieses Kryptowerte-Whitepaper wurde von keiner zuständigen Behörde eines Mitgliedstaats der "
            "Europäischen Union genehmigt.",
        ),
    ]
    path = _write_pdf(tmp_path / "quillmoor.pdf", blocks)

    sections = load_from_pdf(path)
    assert sections["notification_date"] == "2026-03-02"
    assert "Dieses Kryptowerte-Whitepaper" in sections["not_approved_statement"]
    assert sections.keys() == {"notification_date", "not_approved_statement"}
    finding = _findings(path)["COMMON.NOTIFICATION_DATE"]
    assert finding.rule.severity is Severity.MAJOR
    # The answer is a calendar date, which is all the field asks for.
    assert (finding.status, finding.word_count) == ("pass", 1)


def test_xhtml_german_notification_date_heading_anchors_its_findings(tmp_path: Path):
    # Finding anchors and SARIF lines read the heading as the loader does: the second heading, on line 6.
    path = _write_xhtml(
        tmp_path / "quillmoor.xhtml", _german_draft("Datum der Mitteilung", GERMAN_NOTIFICATION)
    )

    assert _xhtml_section_identifiers(path)["notification_date"] == "xhtml:heading-2"
    assert _xhtml_heading_lines(path)["notification_date"] == 6


# German drafts call the redemption "Rücktausch", as the German text of MiCAR does: "Recht auf Rücktausch"
# (Art. 39), "Rücktauschplan" (Art. 47) and "dauerhaften Rücktauschrechte" (Anhang II Teil D Nr. 9).
# Implementing Regulation (EU) 2024/2984 labels field I.06 of the ART summary "Recht auf Rücktausch" and
# field D.31 "Form des Rücktauschs".
GERMAN_REDEMPTION_HEADINGS = ["Rücktausch", "Recht auf Rücktausch", "Dauerhafte Rücktauschrechte"]
GERMAN_ART_SUMMARY = (
    "Der QAR-Token der Quillmoor Ledger S.A. ist ein vermögenswertereferenzierter Token, der sich auf einen "
    "Korb aus Euro-Einlagen und Anleihen bezieht."
)
# Art. 39 Abs. 1 and 2 MiCAR: redemption at all times, here by paying the market value of the referenced
# assets. At 31 words (REDEMPTION, its English counterpart, has 22) the section is too thin for ANNEX_II.I
# (100 words), so the check reviews it whatever its terms.
GERMAN_REDEMPTION = (
    "Die Inhaber des QAR-Token können jederzeit den Rücktausch bei der Quillmoor Ledger S.A. verlangen. Der "
    "Emittent zahlt einen Geldbetrag in Höhe des Marktwerts der Vermögenswerte, auf die der Token Bezug nimmt."
)
ART_SUMMARY = (
    "The QAR token of Quillmoor Ledger S.A. is an asset-referenced token that references a basket of euro "
    "deposits and bonds."
)
REDEMPTION = (
    "Holders of the QAR token may redeem it at any time for funds equal to the market value of the "
    "referenced assets."
)


@pytest.mark.parametrize(
    "heading",
    [
        *GERMAN_REDEMPTION_HEADINGS,
        "RÜCKTAUSCH",
        "Rücktauschrechte",
        "Rücktausch des Token",
        "Rücktauschplan",
        "I.06 Recht auf Rücktausch",
        "D.31 Form des Rücktauschs",
        # A DOCX heading with a line break in it.
        "Recht auf\nRücktausch",
        "Rücknahme der Token",
        "Right of redemption",
        "Redemption rights",
        "D.30 Rights in redemption plan implementation",
    ],
)
def test_redemption_heading_names_the_redemption(heading: str):
    assert match_heading_to_section(heading) == ["redemption"]


# A heading that also names a risk heads a risk, in English as in German: it opens no redemption section, so
# the redemption section takes no risk text from the risks.
@pytest.mark.parametrize(
    "heading,keys",
    [
        ("Rücktauschrisiko", []),
        ("Risiko der Aussetzung des Rücktauschs", []),
        ("Liquiditätsrisiken der dauerhaften Rücktauschrechte", []),
        ("Risiken im Zusammenhang mit dem Rücktausch", ["risks"]),
        ("Rücknahmerisiko", []),
        ("Redemption risk", []),
        ("Risk of a suspended redemption", []),
        ("Risks relating to redemption", ["risks"]),
    ],
)
def test_risk_heading_that_names_the_redemption_does_not_name_it(heading: str, keys: list[str]):
    assert match_heading_to_section(heading) == keys


@pytest.mark.parametrize("suffix", sorted(ALL_WRITERS))
@pytest.mark.parametrize("heading", GERMAN_REDEMPTION_HEADINGS)
def test_german_redemption_heading_opens_its_section(tmp_path: Path, suffix: str, heading: str):
    write, load = ALL_WRITERS[suffix]
    path = write(
        tmp_path / f"quillmoor{suffix}", _german_draft(heading, GERMAN_REDEMPTION, GERMAN_ART_SUMMARY)
    )

    sections = load(path)
    assert sorted(sections) == ["redemption", "summary", "technology"]
    assert _words(sections["redemption"]) == GERMAN_REDEMPTION
    finding = _findings(path, WhitepaperType.ART)["ANNEX_II.I"]
    assert finding.rule.severity is Severity.BLOCKER
    assert (finding.status, finding.word_count) == ("review", len(GERMAN_REDEMPTION.split()))


GERMAN_RIGHTS = (
    "Die Inhaber können ihre Ansprüche aus den Bedingungen des QAR-Token vor den Gerichten in Luxemburg "
    "geltend machen."
)


@pytest.mark.parametrize("suffix", sorted(ALL_WRITERS))
def test_german_rights_heading_that_names_the_redemption_opens_both_sections(tmp_path: Path, suffix: str):
    # A heading names every section whose pattern it matches, so the rights section keeps its heading and
    # the redemption check reads the same chapter.
    heading = "Rechte und Pflichten, Rücktausch"
    rights = f"{GERMAN_RIGHTS} {GERMAN_REDEMPTION}"
    write, load = ALL_WRITERS[suffix]
    path = write(tmp_path / f"quillmoor{suffix}", _german_draft(heading, rights, GERMAN_ART_SUMMARY))

    assert match_heading_to_section(heading) == ["rights_and_obligations", "redemption"]
    sections = load(path)
    assert sorted(sections) == ["redemption", "rights_and_obligations", "summary", "technology"]
    assert _words(sections["rights_and_obligations"]) == _words(sections["redemption"]) == rights
    findings = _findings(path, WhitepaperType.ART)
    for rule_id in ("ANNEX_II.D", "ANNEX_II.I"):
        assert findings[rule_id].rule.severity is Severity.BLOCKER
        assert findings[rule_id].word_count == len(rights.split())


GERMAN_COMPLAINTS = (
    "Beschwerden richten die Inhaber an die Beschwerdestelle der Quillmoor Ledger S.A., die binnen zehn "
    "Werktagen antwortet."
)
HOLDER_RIGHTS = (
    "Holders may enforce their claims under the terms of the QAR token before the courts of Luxembourg."
)
COMPLAINTS = (
    "Holders send complaints to the complaints office of Quillmoor Ledger S.A., which replies within ten "
    "working days."
)
# A rights chapter in three parts with the redemption heading second, between a summary and a technology
# section: (the summary blocks, the chapter headings, the texts under them, the technology blocks). The
# second and third headings rank below the first: by a smaller heading font, a Heading 2 or an h3
# (subheading blocks), or by the number "7.2" under "7.".
GERMAN_FRAME = ([("large", "Zusammenfassung"), ("body", GERMAN_ART_SUMMARY)], [("body", GERMAN_TECHNOLOGY)])
RIGHTS_CHAPTERS = {
    "de": (
        GERMAN_FRAME[0],
        [
            ("large", "Rechte und Pflichten"),
            ("subheading", "Rücktausch"),
            ("subheading", "Beschwerdeverfahren"),
        ],
        [GERMAN_RIGHTS, GERMAN_REDEMPTION, GERMAN_COMPLAINTS],
        [("large", "Technologie"), *GERMAN_FRAME[1]],
    ),
    "en": (
        [("large", "Summary"), ("body", ART_SUMMARY)],
        [
            ("large", "Rights and Obligations"),
            ("subheading", "Redemption"),
            ("subheading", "Complaints Handling"),
        ],
        [HOLDER_RIGHTS, REDEMPTION, COMPLAINTS],
        [("large", "Technology"), ("body", TECHNOLOGY)],
    ),
    "de-numbered": (
        GERMAN_FRAME[0],
        [
            ("large", "7. Rechte und Pflichten"),
            ("large", "7.2 Rücktausch"),
            ("large", "7.3 Beschwerdeverfahren"),
        ],
        [GERMAN_RIGHTS, GERMAN_REDEMPTION, GERMAN_COMPLAINTS],
        [("large", "8. Technologie"), *GERMAN_FRAME[1]],
    ),
}
# Markdown is left out: there every heading ends the section before it.
SUB_HEADING_WRITERS = {suffix: ALL_WRITERS[suffix] for suffix in (".docx", ".pdf", ".xhtml")}


def _rights_chapter(case: str, redemption_kind: str | None = None) -> tuple[list[tuple[str, str]], list[str]]:
    """The blocks of a draft with the rights chapter of case, and the texts of the chapter. redemption_kind
    replaces the kind of the redemption heading."""
    before, headings, texts, after = RIGHTS_CHAPTERS[case]
    if redemption_kind:
        headings = [headings[0], (redemption_kind, headings[1][1]), headings[2]]
    chapter = [
        block for heading, text in zip(headings, texts, strict=True) for block in (heading, ("body", text))
    ]
    return [*before, *chapter, *after], texts


@pytest.mark.parametrize("suffix", sorted(SUB_HEADING_WRITERS))
@pytest.mark.parametrize("case", sorted(RIGHTS_CHAPTERS))
def test_redemption_sub_heading_keeps_the_rights_section_open(tmp_path: Path, suffix: str, case: str):
    # The redemption heading ranks below the rights heading, so the rights section reads the whole chapter,
    # as Part D does in the numbered-field layout, and the redemption section reads it from the redemption
    # heading to its end.
    write, load = SUB_HEADING_WRITERS[suffix]
    blocks, (rights, redemption, complaints) = _rights_chapter(case)
    path = write(tmp_path / f"quillmoor{suffix}", blocks)

    sections = load(path)
    assert sorted(sections) == ["redemption", "rights_and_obligations", "summary", "technology"]
    rights_section, redemption_section = (
        _words(sections[key]) for key in ("rights_and_obligations", "redemption")
    )
    assert all(_words(text) in rights_section for text in (rights, redemption, complaints))
    assert all(_words(text) in redemption_section for text in (redemption, complaints))
    assert _words(rights) not in redemption_section
    findings = _findings(path, WhitepaperType.ART)
    assert findings["ANNEX_II.D"].rule.severity is Severity.BLOCKER
    assert findings["ANNEX_II.D"].word_count == len(rights_section.split())
    assert findings["ANNEX_II.I"].word_count == len(redemption_section.split())


@pytest.mark.parametrize("suffix", sorted(SUB_HEADING_WRITERS))
@pytest.mark.parametrize("case", ["de", "en"])
def test_redemption_heading_at_the_level_of_the_rights_heading_opens_the_redemption_alone(
    tmp_path: Path, suffix: str, case: str
):
    # A redemption heading of the rank of the rights heading opens its own chapter, and the complaints
    # heading below it belongs to that chapter.
    write, load = SUB_HEADING_WRITERS[suffix]
    blocks, (rights, redemption, complaints) = _rights_chapter(case, redemption_kind="large")
    path = write(tmp_path / f"quillmoor{suffix}", blocks)

    sections = load(path)
    assert _words(sections["rights_and_obligations"]) == _words(rights)
    assert all(_words(text) in _words(sections["redemption"]) for text in (redemption, complaints))


# Part D of the ART template as pypdf reads it, with the part titles in a heading font: (the summary
# blocks, the part D title, fields D.28, D.30 and D.36, their answers, the part E title and its text). The
# German D.28 names no section, so the redemption field sits under the part title; the English D.28 names
# the rights, so the redemption field sits under D.28.
TEMPLATE_PART_D = {
    "de": (
        GERMAN_FRAME[0],
        f"Teil D {DASH} Informationen über die mit dem vermögenswertereferenzierten Token verbundenen Rechte und "
        "Pflichten",
        [
            "D.28 Rechte der Inhaber bei Zahlungsausfall oder Insolvenz",
            "D.30 Rechte bei der Durchführung des Rücktauschplans",
            "D.36 Geltendes Recht",
        ],
        [
            "Bei einer Insolvenz der Quillmoor Ledger S.A. behalten die Inhaber ihre Ansprüche.",
            "Nach dem Rücktauschplan erhalten die Inhaber ihren Anteil am Erlös im Verhältnis ihrer Bestände.",
            "Für den QAR-Token gilt luxemburgisches Recht.",
        ],
        [("large", f"Teil E {DASH} Informationen über die zugrunde liegende Technologie"), *GERMAN_FRAME[1]],
    ),
    "en": (
        [("large", "Summary"), ("body", ART_SUMMARY)],
        f"Part D {DASH} Information about the rights and obligations attached to the asset-referenced token",
        [
            "D.28 Holder rights in default or insolvency",
            "D.30 Rights in redemption plan implementation",
            "D.36 Applicable law",
        ],
        [
            "Holders keep their claims against Quillmoor Ledger S.A. in an insolvency of the company.",
            "Under the redemption plan, holders receive their share of the proceeds in proportion to their holdings.",
            "Luxembourg law applies to the QAR token.",
        ],
        [("large", f"Part E {DASH} Information on the underlying technology"), ("body", TECHNOLOGY)],
    ),
}


@pytest.mark.parametrize("case", sorted(TEMPLATE_PART_D))
def test_pdf_redemption_field_of_the_rights_part_keeps_the_rights_section_open(tmp_path: Path, case: str):
    # A field of the template belongs to its part, so the fields after D.30 stay in the rights section.
    before, part_d, fields, answers, after = TEMPLATE_PART_D[case]
    chapter = [
        block
        for field, answer in zip(fields, answers, strict=True)
        for block in (("line", field), ("line", answer))
    ]
    path = _write_pdf(tmp_path / "quillmoor.pdf", [*before, ("large", part_d), *chapter, *after])

    sections = load_from_pdf(path)
    rights, redemption = (_words(sections[key]) for key in ("rights_and_obligations", "redemption"))
    assert all(answer in rights for answer in answers)
    assert answers[1] in redemption and answers[2] in redemption
    assert answers[0] not in redemption
    assert _words(sections["technology"]) == _words(after[-1][1])


# A risk section whose paragraphs sit under headings that each name one risk.
GERMAN_RISK_PARTS = [
    (
        "Marktrisiko",
        "Der Marktpreis des QAR-Token kann vom Wert der Referenzwerte abweichen, und Inhaber können beim "
        "Verkauf Verluste erleiden.",
    ),
    (None, "Verzögert sich der Rücktausch, erhalten die Inhaber ihr Geld später als erwartet."),
    (
        "Liquiditätsrisiko",
        "Bei wenigen Käufern kann die Liquidität des QAR-Token ausbleiben, sodass Inhaber nicht zu einem "
        "fairen Preis verkaufen können.",
    ),
]


@pytest.mark.parametrize("suffix", sorted(WRITERS))
@pytest.mark.parametrize(
    "heading",
    [
        "Rücktauschrisiko",
        "Risiko der Aussetzung des Rücktauschs",
        "Risiken im Zusammenhang mit dem Rücktausch",
        "Rücknahmerisiko",
    ],
)
def test_german_risk_sub_heading_that_names_the_redemption_stays_in_the_risks(
    tmp_path: Path, suffix: str, heading: str
):
    # The second risk heading names the redemption. Its paragraph and the one after it stay in the risks
    # (a PDF keeps a bold label that names no section as text of its section), and the redemption section
    # holds only the chapter under "Rücktausch".
    write, load = WRITERS[suffix]
    blocks = [("large", "Zusammenfassung"), ("body", GERMAN_ART_SUMMARY), ("large", "Risikofaktoren")]
    for label, text in GERMAN_RISK_PARTS:
        blocks += [("subheading", label or heading), ("body", text)]
    blocks += [("large", "Rücktausch"), ("body", GERMAN_REDEMPTION)]
    path = write(tmp_path / f"quillmoor{suffix}", blocks)

    sections = load(path)
    assert sorted(sections) == ["redemption", "risks", "summary"]
    risks = _words(sections["risks"])
    assert all(_words(text) in risks for _, text in GERMAN_RISK_PARTS)
    assert _words(sections["redemption"]) == GERMAN_REDEMPTION
    findings = _findings(path, WhitepaperType.ART)
    assert findings["ANNEX_II.I"].rule.severity is Severity.BLOCKER
    assert (findings["ANNEX_II.I"].status, findings["ANNEX_II.I"].word_count) == (
        "review",
        len(GERMAN_REDEMPTION.split()),
    )


REDEMPTION_RISK = "If the redemption is delayed, holders receive their money later than expected."


@pytest.mark.parametrize("suffix", sorted(WRITERS))
@pytest.mark.parametrize(
    "heading", ["Redemption risk", "Risk of a suspended redemption", "Risks relating to redemption"]
)
def test_risk_sub_heading_that_names_the_redemption_stays_in_the_risks(
    tmp_path: Path, suffix: str, heading: str
):
    # The English counterpart of the test above: the paragraph under the second risk heading and the one
    # after it stay in the risks, and the redemption section holds only the chapter under "Redemption".
    write, load = WRITERS[suffix]
    parts = [RISK_PARTS[0], (heading, REDEMPTION_RISK), RISK_PARTS[1]]
    blocks = [("large", "Summary"), ("body", ART_SUMMARY), ("large", "Risk Factors")]
    for label, text in parts:
        blocks += [("subheading", label), ("body", text)]
    blocks += [("large", "Redemption"), ("body", REDEMPTION)]
    path = write(tmp_path / f"quillmoor{suffix}", blocks)

    sections = load(path)
    assert sorted(sections) == ["redemption", "risks", "summary"]
    risks = _words(sections["risks"])
    assert all(_words(text) in risks for _, text in parts)
    assert _words(sections["redemption"]) == REDEMPTION
    finding = _findings(path, WhitepaperType.ART)["ANNEX_II.I"]
    assert (finding.status, finding.word_count) == ("review", len(REDEMPTION.split()))


def test_xhtml_german_redemption_heading_anchors_its_findings(tmp_path: Path):
    # Finding anchors and SARIF lines read the headings as the loader does: the risk heading before the
    # chapter names the risks only, so the redemption findings point at "Rücktausch", the third heading,
    # on line 8.
    blocks = [
        ("heading", "Zusammenfassung"),
        ("body", GERMAN_ART_SUMMARY),
        ("heading", "Risiken im Zusammenhang mit dem Rücktausch"),
        ("body", GERMAN_RISK_PARTS[1][1]),
        ("heading", "Rücktausch"),
        ("body", GERMAN_REDEMPTION),
    ]
    path = _write_xhtml(tmp_path / "quillmoor.xhtml", blocks)

    identifiers = _xhtml_section_identifiers(path)
    assert (identifiers["risks"], identifiers["redemption"]) == ("xhtml:heading-2", "xhtml:heading-3")
    assert _xhtml_heading_lines(path)["redemption"] == 8


@pytest.mark.parametrize("answer", ["N/A", "n/a", "entfällt", "nicht anwendbar", "k. A."])
def test_pdf_numbered_heading_after_a_not_applicable_answer_opens_its_section(tmp_path: Path, answer: str):
    # An answer that says the item does not apply, in English or German, continues no sentence, so the
    # heading above it stays a heading even in lower case, and the numbered heading after it opens the
    # technology section instead of only ending the risks.
    blocks = [
        ("heading", "Zusammenfassung"),
        ("body", GERMAN_SUMMARY),
        ("heading", "5. Risikofaktoren"),
        ("line", answer),
        ("heading", "6. Technologie"),
        ("body", GERMAN_TECHNOLOGY),
    ]
    sections = load_from_pdf(_write_pdf(tmp_path / "quillmoor.pdf", blocks))

    assert sorted(sections) == ["risks", "summary", "technology"]
    assert sections["risks"] == answer
    assert _words(sections["technology"]) == GERMAN_TECHNOLOGY


# The answer to field 03 of the 2024/2984 summary, in the wording of the template.
COMPLIANCE = (
    "This crypto-asset white paper complies with Title II of Regulation (EU) 2023/1114 and, to the best of "
    "the knowledge of the management body, the information presented in the crypto-asset white paper is "
    "fair, clear and not misleading and the crypto-asset white paper makes no omission likely to affect "
    "its import."
)


@pytest.mark.parametrize("suffix,kind", [(".docx", "bold"), (".pdf", "line")], ids=["docx-bold", "pdf-line"])
def test_compliance_statement_field_of_the_summary_opens_the_management_statement(
    tmp_path: Path, suffix: str, kind: str
):
    # Field 03 "Compliance statement in accordance with Article 6(6)" holds the statement of the
    # management body, so its answer is the management statement and passes its check.
    write, load = WRITERS[suffix]
    blocks = [
        ("large", "Summary"),
        ("body", KEY_SUMMARY),
        (kind, "03 Compliance statement in accordance with Article 6(6) of Regulation (EU) 2023/1114"),
        ("body", COMPLIANCE),
        (kind, "04 Statement in accordance with Article 6(5) of Regulation (EU) 2023/1114"),
        (
            "body",
            "The crypto-asset may lose its value in part or in full and may not always be transferable.",
        ),
        ("large", f"Part I {DASH} Information on risks"),
        ("body", RISK_TEXT),
    ]
    path = write(tmp_path / f"quillmoor{suffix}", blocks)

    sections = load(path)
    assert sorted(sections) == ["management_statement", "risks", "summary"]
    # The PDF writer may wrap "crypto-asset" at its hyphen, so compare the parts of the statement.
    statement = _words(sections["management_statement"])
    assert "complies with Title II of Regulation (EU) 2023/1114" in statement
    assert "fair, clear and not misleading" in statement
    assert _words(sections["summary"]) == KEY_SUMMARY
    findings = _findings(path)
    assert findings["COMMON.MANAGEMENT_STATEMENT"].rule.severity is Severity.BLOCKER
    assert findings["COMMON.MANAGEMENT_STATEMENT"].status == "pass"


# A technology section that passes ANNEX_I.H only as a whole: the first half names the protocol and the
# consensus, the second half the smart contracts and the audit.
TECHNOLOGY_FIRST = (
    "Transfers settle on a permissioned ledger based on a Byzantine fault tolerant consensus protocol run "
    "by five validating nodes. Each node is operated by a different partner firm in a different Member State."
)
TECHNOLOGY_SECOND = (
    "Smart contracts implement the unit register and the fee settlement. The source code is audited once a "
    "year by an independent firm, and the audit reports are published on the website."
)
RUNNING_HEADER = f"Quillmoor Utility Token (QMT) {DASH} Crypto-Asset White Paper"


@pytest.mark.parametrize("kind", ["large", "heading"], ids=["14pt-bold", "body-font"])
def test_pdf_running_page_header_that_names_a_section_is_body_text(tmp_path: Path, kind: str):
    # The header names the crypto-asset section on every page; it must not open that section and take
    # the technology text that runs on to the next page.
    blocks = [
        ("line", RUNNING_HEADER),
        (kind, "Summary"),
        ("body", SUMMARY),
        (kind, "Information on the Underlying Technology"),
        ("body", TECHNOLOGY_FIRST),
        ("page", ""),
        ("line", RUNNING_HEADER),
        ("body", TECHNOLOGY_SECOND),
        (kind, "Risk Factors"),
        ("body", RISK_TEXT),
    ]
    path = _write_pdf(tmp_path / "quillmoor.pdf", blocks)

    sections = load_from_pdf(path)
    assert sorted(sections) == ["risks", "summary", "technology"]
    assert _words(TECHNOLOGY_SECOND) in _words(sections["technology"])
    findings = _findings(path)
    assert findings["ANNEX_I.F"].rule.severity is Severity.BLOCKER
    assert findings["ANNEX_I.F"].status == "missing"
    assert findings["ANNEX_I.H"].rule.severity is Severity.BLOCKER
    assert findings["ANNEX_I.H"].status == "pass"


def test_pdf_body_font_line_is_no_heading_where_headings_have_a_heading_font(tmp_path: Path):
    # The draft sets its headings in 14 pt bold, so the title-case line "Technology Roadmap" in the body
    # font is no heading: the roadmap must not pass the thin technology section.
    blocks = [
        ("large", "Summary"),
        ("body", SUMMARY),
        ("large", "Information about the Project"),
        ("body", PROJECT),
        ("line", "Technology Roadmap"),
        ("body", f"{TECHNOLOGY_FIRST} {TECHNOLOGY_SECOND}"),
        ("large", "Information on the Underlying Technology"),
        ("body", THIN_TECHNOLOGY),
    ]
    path = _write_pdf(tmp_path / "quillmoor.pdf", blocks)

    sections = load_from_pdf(path)
    assert sorted(sections) == ["project", "summary", "technology"]
    assert _words(sections["project"]) == PROJECT
    assert _words(sections["technology"]) == _words(THIN_TECHNOLOGY)
    findings = _findings(path)
    assert findings["ANNEX_I.H"].rule.severity is Severity.BLOCKER
    assert (findings["ANNEX_I.H"].status, findings["ANNEX_I.H"].word_count) == (
        "review",
        len(THIN_TECHNOLOGY.split()),
    )


def test_docx_style_based_on_itself_through_a_cycle_loads(tmp_path: Path):
    doc = docx.Document()
    loop_a = doc.styles.add_style("Loop A", WD_STYLE_TYPE.PARAGRAPH)
    loop_b = doc.styles.add_style("Loop B", WD_STYLE_TYPE.PARAGRAPH)
    loop_a.base_style = loop_b
    loop_b.base_style = loop_a
    doc.add_heading("Summary", level=1)
    doc.add_paragraph(SUMMARY, style="Loop A")
    path = tmp_path / "quillmoor.docx"
    doc.save(path)

    # A daemon thread, so a loader that never returns fails the test instead of hanging the run.
    loaded: dict[str, str] = {}
    worker = threading.Thread(target=lambda: loaded.update(load_from_docx(path)), daemon=True)
    worker.start()
    worker.join(timeout=10)
    assert not worker.is_alive(), "load_from_docx did not return for a cyclic style chain"
    assert loaded == {"summary": SUMMARY}


def test_docx_styles_based_on_a_numbering_style_load(tmp_path: Path):
    # python-docx gives a numbering (list) style neither a base style nor a font.
    doc = docx.Document()
    numbering = doc.styles.add_style("Quillmoor List", WD_STYLE_TYPE.LIST)
    body = doc.styles.add_style("Quillmoor Body", WD_STYLE_TYPE.PARAGRAPH)
    body.base_style = numbering
    strong = doc.styles.add_style("Quillmoor Strong", WD_STYLE_TYPE.CHARACTER)
    strong.base_style = numbering
    doc.add_heading("Summary", level=1)
    doc.add_paragraph(SUMMARY, style="Quillmoor Body")
    doc.add_paragraph(style="Quillmoor Body").add_run("Risk Factors", style="Quillmoor Strong").bold = True
    doc.add_paragraph(RISK_TEXT, style="Quillmoor Body")
    path = tmp_path / "quillmoor.docx"
    doc.save(path)

    sections = load_from_docx(path)
    assert sorted(sections) == ["risks", "summary"]
    assert _words(sections["risks"]) == _words(RISK_TEXT)
    findings = _findings(path)
    assert findings["ANNEX_I.I"].rule.severity is Severity.BLOCKER
    assert findings["ANNEX_I.I"].status == "pass"


# Round 5 of the follow-up verification.
LIST_WRITERS = {suffix: ALL_WRITERS[suffix][0] for suffix in (".docx", ".md", ".pdf")}
_CRYPTO_ASSET = ("heading", "Information about the Crypto-Asset")
_MEADOW_OFFEROR = [
    ("heading", "Information about the Offeror"),
    ("body", "Meadow Labs GmbH, a fictional company, offers the MeadowPoints loyalty token to the public."),
    ("heading", "Risk Factors"),
    ("body", "Holders may lose the full amount, and the token may not always be transferable."),
]


@pytest.mark.parametrize("suffix", sorted(LIST_WRITERS))
def test_a_long_word_is_read_in_linear_time(tmp_path: Path, suffix: str):
    # Whether a line is shaped like a title looked for a sentence break with a pattern that read a run of
    # letters again from each of its letters, so a line of 40 000 letters took 18 s in a DOCX and a PDF (one
    # line, unwrapped); it takes a few hundredths of a second now. Markdown, whose sections regime inference
    # reads as one text each, is checked too.
    blocks = [_CRYPTO_ASSET, ("plain", "- a"), ("plain", "a" * 40_000), *_MEADOW_OFFEROR]
    path = LIST_WRITERS[suffix](tmp_path / f"letters{suffix}", blocks)
    start = time.perf_counter()
    load_whitepaper(path)
    assert time.perf_counter() - start < 3


@pytest.mark.parametrize(
    "text",
    [
        "Risks. Holders may lose",
        "Corp. Holders. More risks",
        "Xcorp. Abc",
        "abcdefgh. Ijklmno. Pqrs! Tu",
        "Quillmoor Corp. Risk Factors",
        "A.1 Name. Risks",
        "a" * 5_000 + ". Holders",
        "abcd. " + "a" * 5_000 + ". Bcde",
    ],
)
def test_sentence_breaks_are_those_of_the_pattern(text: str):
    # The linear reading finds the matches that findall finds, also inside the word after a match.
    assert _sentence_breaks(text) == _SENTENCE_BREAK.findall(text)


@pytest.mark.parametrize("suffix", sorted(LIST_WRITERS))
def test_a_given_regime_is_not_inferred(tmp_path: Path, suffix: str, monkeypatch: pytest.MonkeyPatch):
    # The text was read for the regime also where --type gave it, so a slow shape of that reading slowed
    # `--type other` runs too; the reading is skipped now, and the result is the same.
    import micar_linter.whitepaper as whitepaper

    statement = "For the purposes of MiCAR the token is not an asset-referenced token and not an e-money token."
    blocks = [_CRYPTO_ASSET, ("body", statement), *_MEADOW_OFFEROR]
    path = LIST_WRITERS[suffix](tmp_path / f"meadowpoints{suffix}", blocks)
    inferred = load_whitepaper(path)

    def unread(*args: object) -> list[tuple[str, int]]:
        raise AssertionError("the regime was inferred although it was given")

    monkeypatch.setattr(whitepaper, "_regime_pieces", unread)
    given = load_whitepaper(path, WhitepaperType.OTHER)
    assert given.type is inferred.type is WhitepaperType.OTHER
    assert given.sections == inferred.sections


@pytest.mark.parametrize("suffix", sorted(LIST_WRITERS))
def test_a_given_regime_is_not_inferred_from_a_list(tmp_path: Path, suffix: str, monkeypatch: pytest.MonkeyPatch):
    # The list that test_a_given_regime_is_not_inferred used before the list reading was backed out: a DOCX or
    # PDF reads it as other and Markdown as an EMT (as the "semicolon" case of
    # test_the_documented_limits_of_the_regime_reading shows with a shorter lead-in). A given regime is not
    # inferred, so the text is not read for it, and it holds where the inference would differ.
    import micar_linter.whitepaper as whitepaper

    blocks = [_CRYPTO_ASSET, *_lines(_LEAD_IN, "- an asset-referenced token;", "- an e-money token."), *_MEADOW_OFFEROR]
    path = LIST_WRITERS[suffix](tmp_path / f"meadowpoints{suffix}", blocks)
    inferred = load_whitepaper(path)

    def unread(*args: object) -> list[tuple[str, int]]:
        raise AssertionError("the regime was inferred although it was given")

    monkeypatch.setattr(whitepaper, "_regime_pieces", unread)
    given = load_whitepaper(path, WhitepaperType.OTHER)
    assert given.type is WhitepaperType.OTHER
    if suffix == ".md":
        # An EMT draft has no Annex I crypto-asset section; the given regime keeps it.
        assert inferred.type is WhitepaperType.EMT
        assert "crypto_asset" in given.sections and "crypto_asset" not in inferred.sections
    else:
        assert inferred.type is WhitepaperType.OTHER
        assert given.sections == inferred.sections


# The list cases of Rounds 4 and 5 that the regime reading meets without the list reading those rounds
# added, which was backed out after the verification of the merged changes, and the limits of that reading.
_LEAD_IN = "For the purposes of MiCAR the token is not"


def _lines(*lines: str) -> list[tuple[str, str]]:
    return [("body", line) for line in lines]


# The markers whose items a negated lead-in governs in a DOCX or PDF.
LIST_MARKERS = [
    ("-", "-"),
    ("*", "*"),
    ("•", "•"),
    ("1)", "2)"),
    ("(1)", "(2)"),
    ("a)", "b)"),
    ("(a)", "(b)"),
    ("(i)", "(ii)"),
]
NEGATED_LEAD_INS = [
    ("not, semicolon or", "For the purposes of MiCAR the token is not", "; or", False),
    # A PDF reads this lead-in, and a first item numbered "1)" or "(1)", as headings.
    ("not, capitals", "For the purposes of MiCAR the token is not", "; or", True),
    ("neither, capitals", "For the purposes of MiCAR the token is neither", "", True),
    ("neither with a colon", "The token is neither:", "", False),
    ("not with a colon, and", "The token is not:", ", and", True),
]


def _governed(suffix: str, lead: str, first: str) -> bool:
    """Whether the regime reading governs the items of the list in the marker test below."""
    if suffix == ".md":
        return lead == "neither, capitals"
    if suffix == ".pdf" and first in ("1)", "(1)"):
        return lead not in ("not, capitals", "neither, capitals")
    return True


@pytest.mark.parametrize(
    ("suffix", "first", "second", "lead_in", "between", "capitals"),
    [
        pytest.param(suffix, first, second, lead_in, between, capitals, id=f"{lead}-{first}-{suffix}")
        for lead, lead_in, between, capitals in NEGATED_LEAD_INS
        for first, second in LIST_MARKERS
        for suffix in sorted(LIST_WRITERS)
        if _governed(suffix, lead, first)
    ],
)
def test_a_negated_lead_in_governs_every_item_of_the_list_after_it(
    tmp_path: Path, suffix: str, first: str, second: str, lead_in: str, between: str, capitals: bool
):
    # In a DOCX or PDF each item of a list continues the lead-in before it, so a negated lead-in governs
    # every item whose marker is a bullet or dash or a list number or letter with a bracket, also where the
    # items end in a semicolon, and where they start with a capital letter after a lead-in that ends in a
    # colon or a negation. Not checked, as the CHANGELOG states
    # (test_the_documented_limits_of_the_regime_reading): a list numbered or lettered with a full stop ("1.", "a.", "i."), whose full stop ends the clause as any
    # full stop does; in a PDF, an item numbered "1)" or "(1)" in capitals after a lead-in without a colon,
    # which the PDF reads as a heading and judges on its own words; and in Markdown, which reads a section as
    # one text, a list after a lead-in that ends in a colon or whose first item ends in a semicolon, where
    # the colon or the semicolon ends the clause. So in Markdown only the "neither" list is checked.
    article = "An" if capitals else "an"
    blocks = [
        _CRYPTO_ASSET,
        ("body", lead_in),
        ("body", f"{first} {article} asset-referenced token{between}"),
        ("body", f"{second} {article} e-money token."),
        *_MEADOW_OFFEROR,
    ]
    path = LIST_WRITERS[suffix](tmp_path / f"meadowpoints{suffix}", blocks)
    assert load_whitepaper(path).type is WhitepaperType.OTHER


@pytest.mark.parametrize("suffix", [".docx", ".pdf"])
def test_a_dash_list_after_a_negated_lead_in_keeps_an_annex_i_draft(tmp_path: Path, suffix: str):
    # The example in docs/SETUP.md: in a DOCX or PDF the lead-in governs both items, so the draft is linted
    # as other and the Annex I rules run. Not checked: Markdown, XHTML and HTML, where the semicolon after
    # the first item ends the clause and the draft loads as an EMT, and a list numbered with a full stop,
    # which loads as an ART in every format (test_the_documented_limits_of_the_regime_reading).
    lines = ["the token is not", "- an asset-referenced token;", "- an e-money token."]
    blocks = [("body", line) for line in lines]
    path = LIST_WRITERS[suffix](tmp_path / f"meadowpoints{suffix}", [*blocks, *_MEADOW_OFFEROR])
    assert load_whitepaper(path).type is WhitepaperType.OTHER
    findings = _findings(path, None)
    assert "ANNEX_I.I" in findings and "ANNEX_II.A" not in findings


@pytest.mark.parametrize("suffix", sorted(LIST_WRITERS))
@pytest.mark.parametrize(
    ("blocks", "regime"),
    [
        # A sentence after a negated list that names the regime counts, with or without a full stop after the
        # last item. In a DOCX or PDF it starts a new sentence (with a capital letter, or with a name that
        # holds one), which ends the clause; in Markdown, which reads a section as one text, the colon after
        # the lead-in, a full stop or the reach of eight words ends it.
        (
            [
                _CRYPTO_ASSET,
                ("body", "The token is not:"),
                ("body", "1. an e-money token;"),
                ("body", "2. a deposit."),
                ("body", "The SST is an asset-referenced token."),
                *_SST_ISSUER,
            ],
            WhitepaperType.ART,
        ),
        (
            [
                _CRYPTO_ASSET,
                ("body", "The token is not:"),
                ("body", "- an e-money token;"),
                ("body", "- a deposit"),
                ("body", "The SST is an asset-referenced token"),
                *_SST_ISSUER,
            ],
            WhitepaperType.ART,
        ),
        (
            [
                _CRYPTO_ASSET,
                ("body", "The token is not"),
                ("body", "(a) an e-money token, or"),
                ("body", "(b) a deposit"),
                ("body", "xStable's reserve of assets is held in cash."),
                *_SST_ISSUER,
            ],
            WhitepaperType.ART,
        ),
        # A list after a lead-in without a negation names the regime.
        ([_CRYPTO_ASSET, ("body", "The token is:"), ("body", "1. an asset-referenced token"), *_SST_ISSUER], WhitepaperType.ART),
        (
            [
                _CRYPTO_ASSET,
                ("body", "The token is:"),
                ("body", "1. An asset-referenced token;"),
                ("body", "2. Not an e-money token."),
                *_SST_ISSUER,
            ],
            WhitepaperType.ART,
        ),
        # A numbered heading after a line that ends in a negation is judged on its own words in a DOCX or PDF,
        # with or without a numbered list after it; in Markdown, where it is a line of the section, the full
        # stop after its number ends the clause.
        (
            [
                *_SST_ISSUER,
                ("heading", "Risk Factors"),
                ("body", "Holders have no deposit protection and no"),
                ("numbered", "5. Stabilisation Mechanism"),
                ("body", "The reserve is held in cash."),
            ],
            WhitepaperType.ART,
        ),
        (
            [
                *_SST_ISSUER,
                ("heading", "Risk Factors"),
                ("body", "Holders have no deposit protection and no"),
                ("numbered", "5. Reserve of Assets"),
                ("body", "1. The reserve is held in cash;"),
                ("body", "2. The reserve is held in bonds."),
            ],
            WhitepaperType.ART,
        ),
    ],
    ids=[
        "sentence after the list",
        "sentence after an item without a full stop",
        "name after the list",
        "positive lead-in",
        "positive lead-in with a colon",
        "numbered heading after a negation",
        "numbered heading before a numbered list",
    ],
)
def test_a_list_after_a_lead_in_reaches_no_further_than_its_items(
    tmp_path: Path, suffix: str, blocks: list[tuple[str, str]], regime: WhitepaperType
):
    path = LIST_WRITERS[suffix](tmp_path / f"synthetic{suffix}", blocks)
    assert load_whitepaper(path).type is regime


@pytest.mark.parametrize("suffix", [".docx"])
def test_a_long_item_keeps_its_lead_in(tmp_path: Path, suffix: str):
    # A DOCX paragraph is one line however long, so a long item keeps the lead-in. Not checked: a PDF wraps
    # the item at 90 characters, before "Crypto-Assets Regulation; or", and that line, which starts with a
    # capital letter, starts a new sentence and ends the list, so the PDF loads as an ART (a sentence that a
    # PDF wraps before a capitalised word loses its negation, as docs/SETUP.md states); in Markdown the
    # semicolon ends the clause.
    lines = [
        _LEAD_IN,
        "- an e-money token within the meaning of Article 3(1), point (7), of the Markets in Crypto-Assets "
        "Regulation; or",
        "- an asset-referenced token.",
    ]
    blocks = [_CRYPTO_ASSET, *_lines(*lines), *_MEADOW_OFFEROR]
    assert load_whitepaper(LIST_WRITERS[suffix](tmp_path / f"meadowpoints{suffix}", blocks)).type is WhitepaperType.OTHER


@pytest.mark.parametrize(
    ("suffix", "lines", "regime"),
    [
        pytest.param(
            ".md",
            [
                "The issuer confirms that:",
                "(a) the token is neither",
                "(i) an asset-referenced token, nor",
                "(ii) an e-money token; and",
                "(b) the token is transferable.",
            ],
            WhitepaperType.OTHER,
            id="(a) then (i)-.md",
        ),
        *(
            pytest.param(
                suffix,
                [
                    "The issuer confirms that:",
                    "1. the token is not:",
                    "a) an e-money token; or",
                    "b) a deposit;",
                    "2. the token is an asset-referenced token.",
                ],
                WhitepaperType.ART,
                id=f"back to the outer list-{suffix}",
            )
            for suffix in sorted(LIST_WRITERS)
        ),
    ],
)
def test_a_negated_item_governs_the_list_inside_it(
    tmp_path: Path, suffix: str, lines: list[str], regime: WhitepaperType
):
    # In Markdown, which reads a section as one text, "neither" and "nor" govern the phrases of the inner
    # list within eight words, so the first draft is other there. An item after the inner list that names
    # the regime counts in every format. Not checked: in a DOCX or PDF an item leads no list of its own, so
    # the items of an inner list continue the lead-in of the outer list ("The issuer confirms that:") and
    # the first draft, and the same list under "1. the token is not:", load as an ART there, as in 1.2.1
    # (test_the_documented_limits_of_the_regime_reading); in Markdown the colon after "the token is not"
    # ends the clause.
    blocks = [_CRYPTO_ASSET, *_lines(*lines), *(_MEADOW_OFFEROR if regime is WhitepaperType.OTHER else _SST_ISSUER)]
    assert load_whitepaper(LIST_WRITERS[suffix](tmp_path / f"synthetic{suffix}", blocks)).type is regime


@pytest.mark.parametrize("suffix", [".docx", ".md"])
@pytest.mark.parametrize("marker", ["(1)", "1)"])
def test_a_list_of_one_capitalised_item_after_a_negated_lead_in(tmp_path: Path, suffix: str, marker: str):
    # A lead-in that ends in a negation governs an item that starts with a capital letter: in a DOCX the item
    # continues the lead-in, and Markdown reads the section as one text. Not checked: a PDF reads the item as
    # a heading, which is judged on its own words, and the full stop after "1." ends the clause in every
    # format, so those drafts load as an ART (test_the_documented_limits_of_the_regime_reading).
    blocks = [_CRYPTO_ASSET, *_lines(_LEAD_IN, f"{marker} An asset-referenced token"), *_MEADOW_OFFEROR]
    assert load_whitepaper(LIST_WRITERS[suffix](tmp_path / f"meadowpoints{suffix}", blocks)).type is WhitepaperType.OTHER


def _covered_by(kind: str, heading: str, items: tuple[str, str] = ("1.", "2.")) -> list[tuple[str, str]]:
    return [
        *_SST_ISSUER,
        ("heading", "2. Risk Factors"),
        *_lines(
            "Holders should note that the token is not covered by:",
            f"{items[0]} any investor compensation scheme;",
            f"{items[1]} any deposit guarantee scheme.",
        ),
        (kind, heading),
        ("body", "The reserve is held in cash and short-term government bonds."),
    ]


_NUMBERED_HEADINGS = [
    ("Heading 1", _covered_by("heading", "3. Reserve of Assets")),
    ("Heading 2", _covered_by("subheading", "3. Reserve of Assets")),
    ("bold numbered", _covered_by("numbered", "3. Stabilisation Mechanism")),
    ("14 pt (3)", _covered_by("large", "(3) Reserve of Assets", ("(1)", "(2)"))),
    ("c) after b)", _covered_by("heading", "c) Reserve of Assets", ("a)", "b)"))),
    ("4. after 2.", _covered_by("heading", "4. Reserve of Assets")),
    ("14 pt (3) in sentence case", _covered_by("large", "(3) Reserve of assets", ("(1)", "(2)"))),
    ("body 3. in sentence case", _covered_by("body", "3. Reserve of assets")),
    (
        "heading 1. before 2.",
        [
            *_SST_ISSUER,
            ("heading", "Risk Factors"),
            ("body", "Holders have no deposit protection and no"),
            ("heading", "1. Reserve of Assets"),
            ("body", "2. the reserve is held in cash."),
        ],
    ),
]


@pytest.mark.parametrize(
    ("suffix", "blocks"),
    [
        pytest.param(suffix, blocks, id=f"{name}-{suffix}")
        for name, blocks in _NUMBERED_HEADINGS
        for suffix in sorted(LIST_WRITERS)
        if (name, suffix) != ("c) after b)", ".pdf")
    ],
)
def test_a_numbered_heading_after_a_negated_list_is_judged_on_its_own_words(
    tmp_path: Path, suffix: str, blocks: list[tuple[str, str]]
):
    # In a DOCX or PDF a heading after a negated list is judged on its own words where the loader takes it
    # for a heading (a DOCX heading or bold numbered title, a PDF line in a heading font or shaped like a
    # title), and the full stop after "3." ends the clause of a line that is none, so each draft is an ART.
    # Markdown reads no heading text for the regime, so there the numbered heading is a plain line, and the
    # colon after the lead-in ends the clause. Not checked: "c) Reserve of Assets" in the body font of a
    # PDF, which is read as an item of the list (test_the_documented_limits_of_the_regime_reading).
    if suffix == ".md":
        blocks = [*blocks[:-2], ("body", blocks[-2][1]), blocks[-1]]
    assert load_whitepaper(LIST_WRITERS[suffix](tmp_path / f"synthetic{suffix}", blocks)).type is WhitepaperType.ART


@pytest.mark.parametrize("suffix", [".md"])
@pytest.mark.parametrize(
    ("first", "second"),
    [("1.", "2."), ("a.", "b."), ("i.", "ii."), ("(a)", "(b)"), ("-", "-")],
    ids=["1.", "a.", "i.", "(a)", "-"],
)
@pytest.mark.parametrize("article", ["The", "the"])
def test_a_lead_in_that_negates_words_of_its_own_governs_no_item(
    tmp_path: Path, suffix: str, first: str, second: str, article: str
):
    # The negation of the lead-in is about the compensation scheme, not the risks listed after it, so the
    # items name the regime. Markdown reads a section as one text, where the colon after the lead-in ends
    # the clause, so there each draft is an ART. Not checked: in a DOCX or PDF a negation at the end of a
    # lead-in reaches the items of the dash, bullet or bracket list after it whatever it is about, so the
    # "(a)" and dash lists load as other there (test_the_documented_limits_of_the_regime_reading).
    blocks = [
        *_SST_ISSUER,
        ("heading", "Risk Factors"),
        *_lines(
            "The following risks are not covered by any compensation scheme:",
            f"{first} {article} reserve of assets may lose value;",
            f"{second} {article} custodian may fail.",
        ),
    ]
    assert load_whitepaper(LIST_WRITERS[suffix](tmp_path / f"synthetic{suffix}", blocks)).type is WhitepaperType.ART
    blocks = [
        *_SST_ISSUER,
        ("heading", "Risk Factors"),
        *_lines(
            "Holders bear these risks, with no compensation scheme:",
            "- the reserve of assets may lose value;",
            "- the stabilisation mechanism may fail.",
        ),
    ]
    assert load_whitepaper(LIST_WRITERS[suffix](tmp_path / f"holders{suffix}", blocks)).type is WhitepaperType.ART


@pytest.mark.parametrize("suffix", [".docx", ".pdf"])
@pytest.mark.parametrize(
    "lead_in",
    [
        "The token is not one of the following:",
        "The token does not fall within the definition of:",
        "The token is not considered to be:",
        "The token is not, within the meaning of MiCAR,",
        "Holders have no",
        "Holders should note that the token is not covered by:",
    ],
)
def test_a_lead_in_whose_negation_is_open_governs_its_items(tmp_path: Path, suffix: str, lead_in: str):
    # In a DOCX or PDF a negated lead-in governs the dash items after it, also where it ends in a colon, a
    # comma or a word that needs an object ("Holders have no"), so each draft is other. Not checked:
    # Markdown, which reads a section as one text, where the colon after the lead-in or the semicolon after
    # the first item ends the clause, so these drafts load as an ART or an EMT there
    # (test_the_documented_limits_of_the_regime_reading).
    blocks = [_CRYPTO_ASSET, *_lines(lead_in, "- an asset-referenced token;", "- an e-money token."), *_MEADOW_OFFEROR]
    assert load_whitepaper(LIST_WRITERS[suffix](tmp_path / f"meadowpoints{suffix}", blocks)).type is WhitepaperType.OTHER


def _write_html(path: Path, blocks: list[tuple[str, str]]) -> Path:
    """An HTML draft without an XML declaration: each heading block an h2, each other block a paragraph."""
    elements = "\n".join(
        f"<h2>{escape(text)}</h2>" if kind == "heading" else f"<p>{escape(text)}</p>" for kind, text in blocks
    )
    path.write_text(f'<!DOCTYPE html>\n<html lang="en">\n<body>\n{elements}\n</body>\n</html>\n', encoding="utf-8")
    return path


# Every format whose regime is inferred: DOCX, PDF, Markdown, and heading-layout XHTML and HTML.
EVERY_WRITER = {**{suffix: writer for suffix, (writer, _) in ALL_WRITERS.items()}, ".html": _write_html}
_PSEUDO_NEGATION_LEAD_INS = [
    "The risks include, but are not limited to:",
    "The risks include, but aren't limited to:",
    "The risks shall include but shall not be limited to the following:",
    "Risks include, but are not restricted to:",
    "Risks include, without limitation:",
    "Without limitation, the risks include:",
    "The following list of risks is not exhaustive:",
    "The risks include, among others, but not exclusively:",
    "The risks include, among others, but not only:",
]


@pytest.mark.parametrize("suffix", sorted(EVERY_WRITER))
@pytest.mark.parametrize("markers", [("-", "-"), ("(a)", "(b)"), ("1)", "2)")], ids=["-", "(a)", "1)"])
@pytest.mark.parametrize("lead_in", _PSEUDO_NEGATION_LEAD_INS)
def test_a_pseudo_negation_governs_no_item_of_the_list_after_it(
    tmp_path: Path, suffix: str, markers: tuple[str, str], lead_in: str
):
    # A pseudo-negation ("not limited to", "not restricted to", "not exhaustive", "not exclusively", "not only",
    # "without limitation") holds a negation word but negates nothing, so the risk list of an ART draft names its
    # regime in every format. Before, a DOCX or PDF read the items as negated by the lead-in and the draft as other.
    first, second = markers
    blocks = [
        *_SST_ISSUER,
        ("heading", "Risk Factors"),
        *_lines(lead_in, f"{first} the reserve of assets may lose value;", f"{second} the custodian may fail."),
    ]
    assert load_whitepaper(EVERY_WRITER[suffix](tmp_path / f"synthetic{suffix}", blocks)).type is WhitepaperType.ART


# Drafts for another crypto-asset that name a regime phrase after a pseudo-negation in a sentence of their own.
_PSEUDO_NEGATION_SENTENCES = {
    "including but not limited to": "The platform lists crypto-assets including but not limited to e-money tokens.",
    "not necessarily": "MeadowPoints is not necessarily an e-money token.",
    "without limitation after a negation": (
        "The token is not an asset-referenced token within the meaning of MiCAR or, without limitation, an e-money "
        "token."
    ),
    "not exclusively or partly": "MeadowPoints does not exclusively or partly reference a reserve of assets.",
    "not be restricted to": "Its use shall not be restricted to holders of the e-money token.",
    "not be limited to": "Its use shall not be limited to holders of an asset-referenced token.",
    "not only": "MeadowPoints is not only no asset-referenced token but also no e-money token.",
    "not only, alone": "MeadowPoints does not only differ from an e-money token in who issues it.",
}


@pytest.mark.parametrize("suffix", sorted(EVERY_WRITER))
@pytest.mark.parametrize(
    "sentence", list(_PSEUDO_NEGATION_SENTENCES.values()), ids=list(_PSEUDO_NEGATION_SENTENCES)
)
def test_a_pseudo_negation_negates_a_phrase_outside_a_list_as_any_negation_does(
    tmp_path: Path, suffix: str, sentence: str
):
    # A pseudo-negation governs no item of a list after it, but in a sentence its negation word governs the phrase
    # at most eight words after it as any negation word does, as before #96, so each Annex I draft is other. At
    # 0e24058 the negation word inside a pseudo-negation was none anywhere, and each of these drafts but one was an
    # EMT or ART there: in "not only" the word "no" negates each phrase as well, so that draft was other at 0e24058
    # too and guards nothing about pseudo-negations; "not only, alone" is the case that does.
    blocks = [_CRYPTO_ASSET, ("body", sentence), *_MEADOW_OFFEROR]
    assert load_whitepaper(EVERY_WRITER[suffix](tmp_path / f"meadowpoints{suffix}", blocks)).type is WhitepaperType.OTHER


# A sentence that a DOCX splits over two paragraphs, a PDF over two lines and Markdown over two paragraphs.
_SPLIT_PSEUDO_NEGATION_SENTENCES = [
    ("The platform supports crypto-assets including, but not limited", "to, Bitcoin and e-money tokens."),
    ("Rewards may be paid in, without limitation,", "asset-referenced tokens held by the offeror."),
    ("MeadowPoints can be exchanged for crypto-assets, including but not limited to", "e-money tokens and Ether."),
]


@pytest.mark.parametrize("suffix", sorted(EVERY_WRITER))
@pytest.mark.parametrize(
    "lines", _SPLIT_PSEUDO_NEGATION_SENTENCES, ids=[first.split(",")[0] for first, _ in _SPLIT_PSEUDO_NEGATION_SENTENCES]
)
def test_a_pseudo_negation_negates_the_rest_of_a_sentence_split_over_lines(
    tmp_path: Path, suffix: str, lines: tuple[str, str]
):
    # The line after the pseudo-negation is no list item, so the sentence reads as it did before #96.
    blocks = [_CRYPTO_ASSET, *_lines(*lines), *_MEADOW_OFFEROR]
    assert load_whitepaper(EVERY_WRITER[suffix](tmp_path / f"meadowpoints{suffix}", blocks)).type is WhitepaperType.OTHER


@pytest.mark.parametrize("suffix", sorted(WRITERS))
@pytest.mark.parametrize("lead_in", _PSEUDO_NEGATION_LEAD_INS)
@pytest.mark.parametrize("kind", ["list bullet", "body"], ids=["Word list style", "no marker"])
def test_a_pseudo_negation_lead_in_with_a_colon_governs_no_item_without_a_marker(
    tmp_path: Path, suffix: str, lead_in: str, kind: str
):
    # Word's list styles show a marker that the text of the paragraph does not hold, and a PDF may set its items
    # without one; after a lead-in that ends in a colon (each of these does) such items are read on their own too.
    blocks = [
        *_SST_ISSUER,
        ("heading", "Risk Factors"),
        ("body", lead_in),
        (kind, "the reserve of assets may lose value;"),
        (kind, "the custodian may fail."),
    ]
    assert load_whitepaper(WRITERS[suffix][0](tmp_path / f"synthetic{suffix}", blocks)).type is WhitepaperType.ART


_BESIDE_PSEUDO_NEGATIONS = {
    "after without limitation": ["Without limitation, the token is not an asset-referenced token or an e-money token."],
    "after not limited to": [
        "The token is not limited to one network and is not an asset-referenced token or an e-money token."
    ],
    "after not only": [
        "The token is not only a loyalty token and is not an asset-referenced token or an e-money token."
    ],
    "lead-in": ["The token is not, without limitation,", "- an asset-referenced token;", "- an e-money token."],
    # The "not" of "not limited to" counts here, as the first "not" is more than eight words before the phrase.
    "lead-in, far": [
        "The token is not, among other things and not limited to these,",
        "- an asset-referenced token;",
        "- an e-money token.",
    ],
    "colon lead-in": ["There is no guarantee and no limit, not limited to these:", "the reserve of assets;", "a deposit."],
}


@pytest.mark.parametrize(
    ("suffix", "lines"),
    [
        pytest.param(suffix, lines, id=f"{name}-{suffix}")
        for name, lines in _BESIDE_PSEUDO_NEGATIONS.items()
        for suffix in sorted(EVERY_WRITER)
        if not name.startswith(("lead-in", "colon")) or suffix in (".docx", ".pdf")
    ],
)
def test_a_negation_beside_a_pseudo_negation_still_negates(tmp_path: Path, suffix: str, lines: list[str]):
    # Only the negation word inside a pseudo-negation is no negation; another negation in the clause still governs
    # the phrase, so each Annex I draft is other. The lead-in is checked in a DOCX or PDF, where its list items
    # continue it; Markdown, XHTML and HTML end its clause at the first item's semicolon.
    blocks = [_CRYPTO_ASSET, *_lines(*lines), *_MEADOW_OFFEROR]
    assert load_whitepaper(EVERY_WRITER[suffix](tmp_path / f"meadowpoints{suffix}", blocks)).type is WhitepaperType.OTHER


# Lead-ins that hold a negation before a pseudo-negation that "but" sets apart from it, with the two items of the
# list after each.
_REAL_NEGATIONS_BEFORE_A_PSEUDO_NEGATION = {
    "including but not limited to": "The token does not qualify as any of the following, including but not limited to:",
    "including, but not limited to": "The token is not any of the following, including, but not limited to:",
    "including but not restricted to": "The token does not fall into any category, including but not restricted to:",
    "not, and shall not be": (
        "MeadowPoints is not, and shall not be treated as, any instrument including, but not limited to:"
    ),
    "no colon": "MeadowPoints does not qualify as a crypto-asset of the kinds below, including but not limited to",
    "no claims": "Holders have no claims, including but not limited to:",
    # The full stop of "Art." inside the line ends no lead-in.
    "Art.": "The token is not, within the meaning of Art. 3(1) MiCAR, any of the following, including but not limited to:",
}
_TOKEN_ITEMS = ("an asset-referenced token;", "an e-money token.")
_CLAIM_ITEMS = ("a claim on a reserve of assets;", "redemption at par in a referenced currency.")


@pytest.mark.parametrize("suffix", sorted(WRITERS))
@pytest.mark.parametrize(
    ("kind", "markers"),
    [("body", ("-", "-")), ("body", ("(a)", "(b)")), ("body", ("1)", "2)")), ("list bullet", ("", ""))],
    ids=["-", "(a)", "1)", "Word list style"],
)
@pytest.mark.parametrize(
    "lead_in",
    list(_REAL_NEGATIONS_BEFORE_A_PSEUDO_NEGATION.values()),
    ids=list(_REAL_NEGATIONS_BEFORE_A_PSEUDO_NEGATION),
)
def test_a_pseudo_negation_leaves_a_negation_of_its_lead_in_to_govern_the_list(
    tmp_path: Path, suffix: str, kind: str, markers: tuple[str, str], lead_in: str
):
    # "but" ends the clause, but not the lead-in: a negation before it in the lead-in still governs the list, so the
    # "not" of the pseudo-negation negates as before #96, and each Annex I draft is other in a DOCX or PDF, as on
    # 4a3deb7. At d979243 the pseudo-negation counted as none, as it was the only negation word of its clause, and
    # the items were read on their own: the draft was an ART.
    texts = _CLAIM_ITEMS if lead_in.startswith("Holders") else _TOKEN_ITEMS
    items = [(kind, f"{marker} {text}".strip()) for marker, text in zip(markers, texts, strict=True)]
    blocks = [_CRYPTO_ASSET, ("body", lead_in), *items, *_MEADOW_OFFEROR]
    path = WRITERS[suffix][0](tmp_path / f"meadowpoints{suffix}", blocks)
    assert load_whitepaper(path).type is WhitepaperType.OTHER


# The markers of a list closed by a full stop and of the heading after it, which takes the next marker.
_CLOSED_LIST_MARKERS = [
    ("(a)", "(b)", "(c)"),
    ("a)", "b)", "c)"),
    ("-", "-", "-"),
    ("•", "•", "•"),
    ("1)", "2)", "3)"),
    ("(1)", "(2)", "(3)"),
    ("(i)", "(ii)", "(iii)"),
]


@pytest.mark.parametrize("suffix", sorted(WRITERS))
@pytest.mark.parametrize("kind", ["plain", "bold", "large"])
@pytest.mark.parametrize("markers", _CLOSED_LIST_MARKERS, ids=[markers[0] for markers in _CLOSED_LIST_MARKERS])
@pytest.mark.parametrize("closing", [";", "; and"])
@pytest.mark.parametrize("title", ["Reserve of Assets", "Reserve of assets", "Stabilisation mechanism of the token"])
def test_a_heading_after_a_list_that_a_full_stop_closes_keeps_its_own_reading(
    tmp_path: Path, suffix: str, kind: str, markers: tuple[str, str, str], closing: str, title: str
):
    # After a list whose items end in a semicolon and whose last item ends in a full stop, a line with the next
    # marker of the list whose text reads as a heading is judged on its own words, in each of these fonts (a PDF
    # line that pypdf runs into the next is a documented limit). Before, a DOCX or PDF read "(c) Reserve of
    # Assets" as the next item, which the negated lead-in governed, and the ART draft as other.
    first, second, third = markers
    blocks = [
        *_SST_ISSUER,
        *_lines(
            "Holders should note that the token is not covered by:",
            f"{first} any investor compensation scheme{closing}",
            f"{second} any deposit guarantee scheme.",
        ),
        (kind, f"{third} {title}"),
        ("body", "The reserve is held in cash and short-term government bonds."),
    ]
    assert load_whitepaper(WRITERS[suffix][0](tmp_path / f"synthetic{suffix}", blocks)).type is WhitepaperType.ART


_NOT_QUALIFIED = "The token does not qualify as:"
# Lists that no full stop closes as above, or a line after the closing item that is no heading, so the lead-in
# governs each item: each Annex I draft is other in a DOCX or PDF.
_LISTS_THAT_GO_ON = {
    "items without a semicolon": [_NOT_QUALIFIED, "(a) A financial instrument", "(b) A deposit", "(c) An E-Money Token"],
    "inner list closed": [
        _NOT_QUALIFIED,
        "(a) a financial instrument, in particular:",
        "(i) a transferable security;",
        "(ii) a unit in a collective investment undertaking.",
        "(b) An E-Money Token",
    ],
    "lower-case item after the closing item": [
        _NOT_QUALIFIED,
        "(a) a financial instrument;",
        "(b) a deposit.",
        "(c) an e-money token",
    ],
    "sentence after the closing item": [
        _NOT_QUALIFIED,
        "(a) a financial instrument;",
        "(b) a deposit.",
        "(c) An e-money token within the meaning of MiCAR.",
    ],
    "closing item": [_NOT_QUALIFIED, "(a) a financial instrument;", "(b) a deposit; or", "(c) An E-Money Token."],
    "new lead-in": [
        _NOT_QUALIFIED,
        "(a) a financial instrument;",
        "(b) a deposit.",
        "It is also not:",
        "(a) An E-Money Token",
        "(b) A Structured Deposit",
    ],
    # A line that reads as a heading after a list that one condition of a closed list leaves open.
    "one item, then a label": [_NOT_QUALIFIED, "(a) a deposit.", "(b) E-Money Token"],
    "items ending in a comma, then a label": [
        _NOT_QUALIFIED,
        "(a) a financial instrument,",
        "(b) a deposit.",
        "(c) E-Money Token",
    ],
    "last item without a full stop, then a label": [
        _NOT_QUALIFIED,
        "(a) a financial instrument;",
        "(b) a deposit",
        "(c) E-Money Token",
    ],
    # A line after the closing item whose first word is "An".
    "An after the closing item": [_NOT_QUALIFIED, "(a) a financial instrument;", "(b) a deposit.", "(c) An E-Money Token"],
}


@pytest.mark.parametrize("suffix", sorted(WRITERS))
@pytest.mark.parametrize("lines", list(_LISTS_THAT_GO_ON.values()), ids=list(_LISTS_THAT_GO_ON))
def test_a_negated_lead_in_still_governs_the_items_of_a_list_that_goes_on(
    tmp_path: Path, suffix: str, lines: list[str]
):
    # The first six cases pass with or without the closed-list reading of #96 (their last line ends in a full stop,
    # has no capital letter, starts with "An" or follows a new lead-in), so they guard only that the lead-in
    # governs such lines. Each of the last four fails under a reading that drops one condition of a closed list
    # (at least two items, a semicolon at the end of each item before the last, a full stop at the end of the
    # last) or the rule that a line whose first word is "A" or "An" reads as an item.
    blocks = [_CRYPTO_ASSET, *_lines(*lines), *_MEADOW_OFFEROR]
    assert load_whitepaper(WRITERS[suffix][0](tmp_path / f"meadowpoints{suffix}", blocks)).type is WhitepaperType.OTHER


# Lists that are not closed: the last item does not end in a full stop, or the list has one item, or an item
# before the last does not end in a semicolon. Each line after them stays an item that the lead-in governs.
_LISTS_NOT_CLOSED = {
    "last item without a full stop": [_NOT_QUALIFIED, "(a) a financial instrument;", "(b) a deposit", "(c) E-money token"],
    "one item": [_NOT_QUALIFIED, "(a) a deposit.", "(b) E-money token"],
    "items with full stops": [_NOT_QUALIFIED, "(a) a financial instrument.", "(b) a deposit.", "(c) E-money token"],
}


@pytest.mark.parametrize("suffix", sorted(WRITERS))
@pytest.mark.parametrize("lines", list(_LISTS_NOT_CLOSED.values()), ids=list(_LISTS_NOT_CLOSED))
def test_a_list_is_closed_only_by_a_full_stop_after_one_or_more_items_ending_in_a_semicolon(
    tmp_path: Path, suffix: str, lines: list[str]
):
    # Each condition of a closed list: two or more items, each item before the last ending in a semicolon, and
    # the last in a full stop. Without one of them "(c) E-money token" is the next item, and the draft is other.
    blocks = [_CRYPTO_ASSET, *_lines(*lines), *_MEADOW_OFFEROR]
    assert load_whitepaper(WRITERS[suffix][0](tmp_path / f"meadowpoints{suffix}", blocks)).type is WhitepaperType.OTHER


# Lines after a closed list that do not read as a heading: the text after the marker starts with "A" or "An",
# with no capital letter (a digit, an outline number, a quotation mark), or ends in a colon.
_ITEMS_AFTER_A_CLOSED_LIST = {
    "an": ["(c) An e-money token"],
    "a": ["(c) A Reserve of Assets"],
    "digit": ["(c) 2024 Reserve of Assets"],
    "outline number": ["(c) 3.1 Reserve of Assets"],
    "quotation mark": ["(c) \u201cReserve of Assets\u201d"],
    "colon": ["(c) E-money tokens, namely:", "(i) those issued by a credit institution."],
}


@pytest.mark.parametrize("suffix", sorted(WRITERS))
@pytest.mark.parametrize("tail", list(_ITEMS_AFTER_A_CLOSED_LIST.values()), ids=list(_ITEMS_AFTER_A_CLOSED_LIST))
def test_a_line_after_a_closed_list_that_reads_as_an_item_stays_governed(
    tmp_path: Path, suffix: str, tail: list[str]
):
    # At 0e24058 each of these lines counted as shaped like a heading (document._heading_shaped needs only the
    # first letter after any numbering to be a capital, and allows 20 words after an outline number), so it was
    # judged on its own words and the Annex I draft was an EMT or an ART.
    blocks = [
        _CRYPTO_ASSET,
        *_lines(_NOT_QUALIFIED, "(a) a financial instrument;", "(b) a deposit.", *tail),
        *_MEADOW_OFFEROR,
    ]
    assert load_whitepaper(WRITERS[suffix][0](tmp_path / f"meadowpoints{suffix}", blocks)).type is WhitepaperType.OTHER


# A line that reads as a heading after a closed list, then more items of the list.
_ITEMS_AFTER_A_HEADING = {
    "list-intro": ["(c) Any Other Category", "(i) an e-money token;", "(ii) an asset-referenced token."],
    "next letter": ["(c) Other Instruments", "(d) an e-money token."],
    "next letter, art": ["(c) Other Instruments", "(d) an asset-referenced token;", "(e) a deposit."],
}


@pytest.mark.parametrize("suffix", sorted(WRITERS))
@pytest.mark.parametrize("lead_in", [_NOT_QUALIFIED, "The token is not:"])
@pytest.mark.parametrize("tail", list(_ITEMS_AFTER_A_HEADING.values()), ids=list(_ITEMS_AFTER_A_HEADING))
def test_the_items_after_a_heading_in_a_closed_list_still_follow_the_lead_in(
    tmp_path: Path, suffix: str, lead_in: str, tail: list[str]
):
    # The line that reads as a heading is judged on its own words; the items after it still continue the lead-in,
    # as before #96. At 0e24058 the heading ended the list, and the lower-case items after it were read on their
    # own, so the Annex I draft was an EMT or an ART.
    blocks = [
        _CRYPTO_ASSET,
        *_lines(lead_in, "(a) a financial instrument;", "(b) a deposit.", *tail),
        *_MEADOW_OFFEROR,
    ]
    assert load_whitepaper(WRITERS[suffix][0](tmp_path / f"meadowpoints{suffix}", blocks)).type is WhitepaperType.OTHER


def test_a_list_closed_by_a_full_stop_is_read_in_linear_time():
    # The reading of a DOCX's or PDF's lines keeps only how the last item of a list ends and whether each item
    # before it ends in a semicolon, so 5,000 closed lists with a heading after each and one list of 20,000
    # items take a fraction of a second; a reading that went over the earlier items again at each item took
    # time in the square of the list's length.
    lines: list[str] = []
    for _ in range(5000):
        lines += ["The token is not covered by:", "(a) any compensation scheme;", "(b) any insurance.", "(c) Reserve of Assets"]
    lines += ["The token is not covered by:", *("- a scheme;" for _ in range(20_000)), "- a deposit."]
    start = time.perf_counter()
    pieces = _regime_pieces(".pdf", {}, "\n".join(lines), ())
    assert time.perf_counter() - start < 3
    assert len(pieces) == len(lines)
    assert _names_regime(pieces, _ART_MARKERS)


def test_a_long_markdown_list_is_read_in_little_memory(tmp_path: Path):
    # Markdown reads a section as one text, so 200 kB of two-letter list lines take about 2 MB at their peak
    # (the line-by-line reading that Round 4 added and Round 5 trimmed took 46 MB, then 2 MB).
    path = tmp_path / "lines.md"
    path.write_text(
        "# Information about the Crypto-Asset\n\nThe token is not:\n- a\n" + "a\n" * 100_000 + "an e-money token\n",
        encoding="utf-8",
    )
    tracemalloc.start()
    try:
        load_whitepaper(path)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert peak < 25 * path.stat().st_size


def test_a_long_list_is_read_in_linear_time(tmp_path: Path):
    # The list reading that the follow-up verification found quadratic kept a stack of open lists, so a
    # Markdown section of 16 000 lines "1. a:" took about a minute to load; a section is read as one text
    # again, in a few hundredths of a second.
    path = tmp_path / "items.md"
    path.write_text(
        "# Information about the Crypto-Asset\n\n" + "1. a:\n" * 16_000 + "The token is an e-money token.\n",
        encoding="utf-8",
    )
    start = time.perf_counter()
    whitepaper = load_whitepaper(path)
    assert time.perf_counter() - start < 3
    assert whitepaper.type is WhitepaperType.EMT


def _regimes(docx_and_pdf: WhitepaperType, markup: WhitepaperType) -> dict[str, WhitepaperType]:
    """The regime of a draft from a DOCX and a PDF, and from Markdown and XHTML."""
    return {".docx": docx_and_pdf, ".pdf": docx_and_pdf, ".md": markup, ".xhtml": markup}


ART, EMT, OTHER = WhitepaperType.ART, WhitepaperType.EMT, WhitepaperType.OTHER
_ART_INTRODUCTION = "The Synthetic Stable Token is an asset-referenced token."
_STATEMENT = (
    "This crypto-asset white paper has not been approved by any competent authority in any Member State of the "
    "European Union."
)


@pytest.mark.parametrize("suffix", sorted(ALL_WRITERS))
@pytest.mark.parametrize(
    ("blocks", "regimes"),
    [
        # A list numbered or lettered with a full stop: the full stop ends the clause, as in 1.2.1.
        (
            [
                _CRYPTO_ASSET,
                *_lines(_LEAD_IN, "1. an asset-referenced token; or", "2. an e-money token."),
                *_MEADOW_OFFEROR,
            ],
            _regimes(ART, ART),
        ),
        # The example in docs/SETUP.md. Markdown and XHTML read a section as one text, where the semicolon
        # ends the clause.
        (
            [
                _CRYPTO_ASSET,
                *_lines("the token is not", "- an asset-referenced token;", "- an e-money token."),
                *_MEADOW_OFFEROR,
            ],
            _regimes(OTHER, EMT),
        ),
        # A line without a marker after one that ends in "; or", as a Word list numbered by its style is
        # extracted.
        (
            [
                _CRYPTO_ASSET,
                *_lines(_LEAD_IN, "an asset-referenced token; or", "an e-money token."),
                *_MEADOW_OFFEROR,
            ],
            _regimes(EMT, EMT),
        ),
        # A negation that is not about the items governs them in a DOCX or PDF; a pseudo-negation such as "but
        # are not limited to" governs nothing (test_a_pseudo_negation_governs_no_item_of_the_list_after_it).
        (
            [
                *_SST_ISSUER,
                ("heading", "Risk Factors"),
                *_lines(
                    "There is no guarantee that:",
                    "- the reserve of assets may lose value;",
                    "- the custodian may fail.",
                ),
            ],
            _regimes(OTHER, ART),
        ),
        # A line after the list that starts with a list letter is read as an item in a DOCX or PDF, where no
        # item closes the list with a full stop after items that end in a semicolon.
        (
            [
                *_SST_ISSUER,
                *_lines(
                    "Holders should note that the token is not covered by:",
                    "(a) any investor compensation scheme;",
                    "(b) any deposit guarantee scheme;",
                ),
                ("plain", "(c) Reserve of Assets"),
                ("body", "The reserve is held in cash and short-term government bonds."),
            ],
            _regimes(OTHER, ART),
        ),
        # So is a line after the list that starts with a list number in sentence case, in a DOCX paragraph
        # that is no heading and in the body font of a PDF after items numbered "1)" and "2)".
        (
            [
                *_SST_ISSUER,
                *_lines(
                    "Holders should note that the token is not covered by:",
                    "1) any investor compensation scheme;",
                    "2) any deposit guarantee scheme;",
                ),
                ("plain", "3) Reserve of assets"),
                ("body", "The reserve is held in cash and short-term government bonds."),
            ],
            _regimes(OTHER, ART),
        ),
        # After a list whose items end in a semicolon and whose last item ends in a full stop, such a line
        # shaped like a heading is judged on its own words
        # (test_a_heading_after_a_list_that_a_full_stop_closes_keeps_its_own_reading).
        (
            [
                *_SST_ISSUER,
                *_lines(
                    "Holders should note that the token is not covered by:",
                    "(a) any investor compensation scheme;",
                    "(b) any deposit guarantee scheme.",
                ),
                ("plain", "(c) Reserve of Assets"),
                ("body", "The reserve is held in cash and short-term government bonds."),
            ],
            _regimes(ART, ART),
        ),
        # So is one more item that reads as a heading after such a list, whose last item but one ends in a full
        # stop: the lead-in does not govern that line in a DOCX or PDF. "(c) An e-money token" reads as an item
        # (test_a_line_after_a_closed_list_that_reads_as_an_item_stays_governed).
        (
            [
                _CRYPTO_ASSET,
                *_lines(_NOT_QUALIFIED, "(a) a financial instrument;", "(b) a deposit.", "(c) E-money token"),
                *_MEADOW_OFFEROR,
            ],
            _regimes(EMT, EMT),
        ),
        # In a PDF, pypdf runs a line set in 20 pt only 13 pt above the next line into that line ("(c) Reserve of
        # AssetsThe reserve is held ..."), which is then no label and is read as the next item of the list.
        (
            [
                *_SST_ISSUER,
                *_lines(
                    "Holders should note that the token is not covered by:",
                    "(a) any investor compensation scheme;",
                    "(b) any deposit guarantee scheme.",
                ),
                ("title", "(c) Reserve of Assets"),
                ("body", "The reserve is held in cash and short-term government bonds."),
            ],
            {".docx": ART, ".pdf": OTHER, ".md": ART, ".xhtml": ART},
        ),
        # Where the line below ends without a full stop, the joined line ("(c) Reserve of AssetsHeld in cash and
        # short-term government bonds") still reads as a heading and is judged on its own words.
        (
            [
                *_SST_ISSUER,
                *_lines(
                    "Holders should note that the token is not covered by:",
                    "(a) any investor compensation scheme;",
                    "(b) any deposit guarantee scheme.",
                ),
                ("title", "(c) Reserve of Assets"),
                ("body", "Held in cash and short-term government bonds"),
            ],
            _regimes(ART, ART),
        ),
        # A paragraph that ends in a negation and no full stop reaches the next paragraph of its section in
        # Markdown and XHTML.
        (
            [
                *_SST_ISSUER,
                ("heading", "Risk Factors"),
                *_lines(
                    "Holders have no claim against the custodian",
                    "The reserve of assets may lose value in a market stress event",
                ),
            ],
            _regimes(ART, OTHER),
        ),
        # There a negation also reaches over a list item into the paragraph after it.
        (
            [
                _CRYPTO_ASSET,
                *_lines("MeadowPoints is not", "(1) an asset-referenced token", "xStable's reserve of assets is held in cash."),
                *_MEADOW_OFFEROR,
            ],
            _regimes(ART, OTHER),
        ),
        # An item that a PDF reads as a heading is judged on its own words.
        (
            [_CRYPTO_ASSET, *_lines(_LEAD_IN, "(1) An asset-referenced token"), *_MEADOW_OFFEROR],
            {**_regimes(OTHER, OTHER), ".pdf": ART},
        ),
        # A sentence that names a regime without calling the token one sets it, as in 1.2.1.
        (
            [
                _CRYPTO_ASSET,
                *_lines(
                    "MiCAR distinguishes asset-referenced tokens, e-money tokens and other crypto-assets.",
                    "MeadowPoints is a crypto-asset of the third kind.",
                ),
                *_MEADOW_OFFEROR,
            ],
            _regimes(ART, ART),
        ),
        # Outside a list a pseudo-negation negates the phrase after it as any negation word does, so a draft for
        # another crypto-asset that lists e-money tokens so is other, as before #96, and so is an ART draft that
        # names its reserve so (in 1.2.1 both name their regime).
        (
            [
                _CRYPTO_ASSET,
                *_lines("The platform lists crypto-assets including but not limited to e-money tokens."),
                *_MEADOW_OFFEROR,
            ],
            _regimes(OTHER, OTHER),
        ),
        (
            [
                *_SST_ISSUER,
                ("heading", "Risk Factors"),
                ("body", "The issuer holds, without limitation, a reserve of assets in cash and bonds."),
            ],
            _regimes(OTHER, OTHER),
        ),
        # The other three sentences of test_a_pseudo_negation_does_not_negate_the_phrase_after_it (5b8043d), which
        # name the regime of the ART or EMT draft in 1.2.1 and at 5b8043d.
        (
            [
                *_SST_ISSUER,
                ("heading", "Risk Factors"),
                ("body", "The token is not only an asset-referenced token: it also gives access to a loyalty scheme."),
            ],
            _regimes(OTHER, OTHER),
        ),
        (
            [
                *_SST_ISSUER,
                ("heading", "Risk Factors"),
                ("body", "Holders are not necessarily repaid from the reserve of assets in full."),
            ],
            _regimes(OTHER, OTHER),
        ),
        (
            [
                *_SST_ISSUER,
                ("heading", "Risk Factors"),
                ("body", "Its use is not restricted to holders of the e-money token."),
            ],
            _regimes(OTHER, OTHER),
        ),
        # A list item after a pseudo-negation is read on its own, so a draft for another crypto-asset whose risk
        # list names a regime phrase is an EMT, as in 1.2.1 (a Markdown or XHTML clause ends at the colon).
        (
            [
                _CRYPTO_ASSET,
                ("body", "MeadowPoints is a utility token."),
                ("heading", "Risk Factors"),
                *_lines(
                    "The risks include, but are not limited to:",
                    "- reclassification as an e-money token;",
                    "- loss of the private key.",
                ),
                *_MEADOW_OFFEROR[:2],
            ],
            _regimes(EMT, EMT),
        ),
        # In a DOCX or PDF an item leads no list of its own: the items of the inner list continue the lead-in
        # of the outer one, as in 1.2.1.
        (
            [
                _CRYPTO_ASSET,
                *_lines(
                    "The issuer confirms that:",
                    "(a) the token is neither",
                    "(i) an asset-referenced token, nor",
                    "(ii) an e-money token; and",
                    "(b) the token is transferable.",
                ),
                *_MEADOW_OFFEROR,
            ],
            _regimes(ART, OTHER),
        ),
        # In Markdown and XHTML a lead-in that ends in a colon ends its clause at the colon, so the list after
        # it sets the regime there; a DOCX or PDF reads its items as other.
        (
            [
                _CRYPTO_ASSET,
                *_lines("The token is not:", "- an asset-referenced token", "- an e-money token"),
                *_MEADOW_OFFEROR,
            ],
            _regimes(OTHER, ART),
        ),
        # An introduction that calls the token an asset-referenced token makes the draft an ART in a DOCX or PDF
        # wherever the inference reads it (in a DOCX a paragraph of its body); Markdown and XHTML read only section
        # text, so not under a first heading that names no section, as in 1.2.1.
        (
            [
                ("heading", "Introduction"),
                ("body", "The Synthetic Stable Token is an asset-referenced token."),
                *_SST_ISSUER,
            ],
            _regimes(ART, OTHER),
        ),
        # The same introduction under a heading that names a section is read in every format.
        (
            [
                ("heading", "Summary"),
                ("body", "The Synthetic Stable Token is an asset-referenced token."),
                *_SST_ISSUER,
            ],
            _regimes(ART, ART),
        ),
        # After a section, XHTML leaves it open under a heading that names none, so the introduction is read as
        # its text there; Markdown ends the section at every heading.
        (
            [
                ("heading", "Summary"),
                ("body", "The Synthetic Stable Token gives holders a claim on the issuer."),
                ("heading", "Background"),
                ("body", "The Synthetic Stable Token is an asset-referenced token."),
                *_SST_ISSUER,
            ],
            {**_regimes(ART, ART), ".md": OTHER},
        ),
        # Before any heading, Markdown and XHTML read no introduction; a DOCX or PDF does, as in 1.2.1.
        ([("body", _ART_INTRODUCTION), *_SST_ISSUER], _regimes(ART, OTHER)),
        # After the first-page statement in the line (Markdown) or paragraph (XHTML) where the statement ends,
        # which now joins the statement's own section, every format reads it (1.2.1 read it only from a DOCX or
        # PDF); test_the_text_after_the_statement_is_read_only_where_the_statement_ends reads the next line.
        ([("body", f"{_STATEMENT} {_ART_INTRODUCTION}"), *_SST_ISSUER], _regimes(ART, ART)),
        # Before the statement in its line or paragraph, which the statement then does not open, Markdown and
        # XHTML do not read it, as in 1.2.1.
        ([("body", f"{_ART_INTRODUCTION} {_STATEMENT}"), *_SST_ISSUER], _regimes(ART, OTHER)),
        # A negation before the phrase in its clause makes the introduction other (in 1.2.1 an ART).
        (
            [
                ("heading", "Summary"),
                ("body", "The Synthetic Stable Token is not an e-money token and is therefore an asset-referenced token."),
                *_SST_ISSUER,
            ],
            _regimes(OTHER, OTHER),
        ),
        # A phrase split over two paragraphs (in a PDF two lines) is not found in any format, as in 1.2.1;
        # test_a_phrase_that_a_line_end_splits_inside_a_paragraph reads one paragraph.
        (
            [
                ("heading", "Summary"),
                ("plain", "The Synthetic Stable Token is an asset-"),
                ("plain", "referenced token."),
                *_SST_ISSUER,
            ],
            _regimes(OTHER, OTHER),
        ),
        # A lead-in that the loader reads as a heading and that ends in a negation and a colon governs nothing:
        # the colon ends its clause. Markdown and XHTML end the clause at a colon at the end of a line.
        (
            [
                _CRYPTO_ASSET,
                ("bold", "The token is not:"),
                *_lines("- an asset-referenced token;", "- an e-money token."),
                *_MEADOW_OFFEROR,
            ],
            _regimes(ART, ART),
        ),
        # Without the colon, such a lead-in governs the items after it in a DOCX or PDF (docs/SETUP.md); Markdown
        # and XHTML end the clause at the first item's semicolon.
        (
            [
                _CRYPTO_ASSET,
                ("bold", "The token is not"),
                *_lines("- an asset-referenced token;", "- an e-money token."),
                *_MEADOW_OFFEROR,
            ],
            _regimes(OTHER, EMT),
        ),
        # Upper-case list letters are no list items: each starts a new sentence (Markdown and XHTML end the
        # clause at the semicolon instead).
        (
            [
                _CRYPTO_ASSET,
                *_lines(_LEAD_IN, "(A) an asset-referenced token; or", "(B) an e-money token."),
                *_MEADOW_OFFEROR,
            ],
            _regimes(ART, EMT),
        ),
    ],
    ids=[
        "full stop",
        "semicolon",
        "no marker",
        "risk list",
        "line after the list",
        "numbered line after the list",
        "line after a closed list",
        "item after a closed list",
        "line run together after a closed list",
        "label run together after a closed list",
        "paragraphs",
        "over a list item",
        "item read as a heading",
        "category",
        "phrase after a pseudo-negation",
        "reserve after a pseudo-negation",
        "asset-referenced token after not only",
        "reserve after not necessarily",
        "e-money token after not restricted to",
        "item after a pseudo-negation",
        "inner list",
        "colon lead-in",
        "introduction under no section",
        "introduction in a section",
        "introduction after a section",
        "introduction before any heading",
        "introduction with the statement",
        "introduction before the statement",
        "negated introduction",
        "phrase split over two paragraphs",
        "heading lead-in with a colon",
        "heading lead-in without a colon",
        "upper-case list letters",
    ],
)
def test_the_documented_limits_of_the_regime_reading(
    tmp_path: Path, suffix: str, blocks: list[tuple[str, str]], regimes: dict[str, WhitepaperType]
):
    # The CHANGELOG and docs/SETUP.md name these limits; this test keeps the docs and the code in step.
    path = ALL_WRITERS[suffix][0](tmp_path / f"synthetic{suffix}", blocks)
    assert load_whitepaper(path).type is regimes[suffix]


_INTRODUCTION_RUN = f'<w:r><w:t xml:space="preserve">{_ART_INTRODUCTION}</w:t></w:r>'
_REVISION = 'w:id="1" w:author="Synthetic Reviewer"'
# The introduction inside a body paragraph ("Note: ..."), as a run of its own or inside another element.
_INLINE_INTRODUCTIONS = {
    "hyperlink": f'<w:hyperlink w:anchor="introduction">{_INTRODUCTION_RUN}</w:hyperlink>',
    "run marked hidden": f'<w:r><w:rPr><w:vanish/></w:rPr><w:t xml:space="preserve">{_ART_INTRODUCTION}</w:t></w:r>',
    "tracked insertion": f"<w:ins {_REVISION}>{_INTRODUCTION_RUN}</w:ins>",
    "moved here": f"<w:moveTo {_REVISION}>{_INTRODUCTION_RUN}</w:moveTo>",
    "content control": f"<w:sdt><w:sdtPr/><w:sdtContent>{_INTRODUCTION_RUN}</w:sdtContent></w:sdt>",
    "smart tag": f'<w:smartTag w:uri="urn:synthetic" w:element="note">{_INTRODUCTION_RUN}</w:smartTag>',
    "simple field": f'<w:fldSimple w:instr=" DOCPROPERTY Introduction ">{_INTRODUCTION_RUN}</w:fldSimple>',
}


@pytest.mark.parametrize(
    ("placement", "regime"),
    [
        ("body", ART),
        ("table", OTHER),
        ("header", OTHER),
        ("tracked insertion", OTHER),
        ("hyperlink", ART),
        ("run marked hidden", ART),
        ("footer", OTHER),
        ("moved here", OTHER),
        ("content control", OTHER),
        ("smart tag", OTHER),
        ("simple field", OTHER),
    ],
)
def test_a_docx_introduction_is_read_for_the_regime_only_in_a_paragraph_of_its_body(
    tmp_path: Path, placement: str, regime: WhitepaperType
):
    # The regime of a DOCX is read from the runs and hyperlinks that stand directly in the paragraphs of its body
    # (python-docx's paragraph text), runs marked hidden included, not from its tables, headers or footers, nor from
    # text inside a tracked insertion or move, a content control, a smart tag or a simple field, as in 1.2.1
    # (CHANGELOG, docs/SETUP.md).
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls

    document = docx.Document()
    if placement == "body":
        document.add_paragraph(_ART_INTRODUCTION)
    elif placement == "table":
        document.add_table(rows=1, cols=1).cell(0, 0).text = _ART_INTRODUCTION
    elif placement == "header":
        document.sections[0].header.paragraphs[0].text = _ART_INTRODUCTION
    elif placement == "footer":
        document.sections[0].footer.paragraphs[0].text = _ART_INTRODUCTION
    else:
        paragraph = document.add_paragraph("Note: ")
        for element in parse_xml(f"<w:x {nsdecls('w')}>{_INLINE_INTRODUCTIONS[placement]}</w:x>"):
            paragraph._p.append(element)
    for kind, text in _SST_ISSUER:
        if kind == "heading":
            document.add_heading(text, level=1)
        else:
            document.add_paragraph(text)
    path = tmp_path / "introduction.docx"
    document.save(path)
    assert load_whitepaper(path).type is regime


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("The Synthetic Stable Token is an asset-", "referenced token."),
        ("The Synthetic Stable Token is backed by a reserve of", "assets held in cash."),
    ],
    ids=["after a hyphen", "between words"],
)
@pytest.mark.parametrize(
    ("suffix", "regime"), [(".docx", OTHER), (".md", OTHER), (".xhtml", ART), (".html", ART)]
)
def test_a_phrase_that_a_line_end_splits_inside_a_paragraph(
    tmp_path: Path, first: str, second: str, suffix: str, regime: WhitepaperType
):
    # A line break inside a DOCX paragraph and a line end inside a Markdown paragraph keep the two parts of a phrase
    # apart, as in 1.2.1; a <br> inside an XHTML or HTML paragraph reads as a space, or joins a word broken after its
    # hyphen, so the phrase is found there (CHANGELOG). 1.2.1 ran the text on either side of the <br> together with
    # nothing between them: with this markup it found only "asset-" / "referenced token";
    # test_a_phrase_that_a_br_splits_is_found_whatever_the_whitespace_beside_it varies the whitespace.
    path = tmp_path / f"split{suffix}"
    issuer = _SST_ISSUER[1][1]
    if suffix == ".docx":
        document = docx.Document()
        document.add_heading("Summary", level=1)
        run = document.add_paragraph().add_run(first)
        run.add_break()
        run.add_text(second)
        document.add_heading("Information about the Issuer", level=1)
        document.add_paragraph(issuer)
        document.save(path)
    elif suffix == ".md":
        path.write_text(f"## Summary\n\n{first}\n{second}\n\n## Information about the Issuer\n\n{issuer}\n", encoding="utf-8")
    else:
        path.write_text(
            f"<html><body><h2>Summary</h2><p>{first}<br/>{second}</p>"
            f"<h2>Information about the Issuer</h2><p>{issuer}</p></body></html>",
            encoding="utf-8",
        )
    assert load_whitepaper(path).type is regime


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("The Synthetic Stable Token is an asset-", "referenced token."),
        ("The Synthetic Stable Token is backed by a reserve of", "assets held in cash."),
    ],
    ids=["after a hyphen", "between words"],
)
@pytest.mark.parametrize(
    "shape",
    ["{}<br/>{}", "{}<br/>\n{}", "{} <br/>{}", "{}\n<br/>{}"],
    ids=["none", "line end after", "space before", "line end before"],
)
@pytest.mark.parametrize("suffix", [".xhtml", ".html"])
def test_a_phrase_that_a_br_splits_is_found_whatever_the_whitespace_beside_it(
    tmp_path: Path, first: str, second: str, shape: str, suffix: str
):
    # The phrase is found with or without a space or line end beside the <br> (CHANGELOG). 1.2.1 ran the text on
    # either side of the <br> together with nothing between them, so it found "reserve of" / "assets" only with
    # whitespace beside the <br> and "asset-" / "referenced token" only with none.
    path = tmp_path / f"split{suffix}"
    path.write_text(
        f"<html><body><h2>Summary</h2><p>{shape.format(first, second)}</p>"
        f"<h2>Information about the Issuer</h2><p>{_SST_ISSUER[1][1]}</p></body></html>",
        encoding="utf-8",
    )
    assert load_whitepaper(path).type is ART


_STATEMENT_FIRST_LINE = "This crypto-asset white paper has not been approved by any competent authority in any Member State"
_STATEMENT_LAST_LINE = "of the European Union."


@pytest.mark.parametrize(
    ("suffix", "statement", "regime"),
    [
        # Markdown reads the text after the statement in the line where the statement ends, also where the
        # statement wraps over lines, and not the next line of the same paragraph.
        (".md", f"{_STATEMENT} {_ART_INTRODUCTION}", ART),
        (".md", f"{_STATEMENT_FIRST_LINE}\n{_STATEMENT_LAST_LINE} {_ART_INTRODUCTION}", ART),
        (".md", f"{_STATEMENT}\n{_ART_INTRODUCTION}", OTHER),
        (".md", f"{_STATEMENT_FIRST_LINE}\n{_STATEMENT_LAST_LINE}\n{_ART_INTRODUCTION}", OTHER),
        # XHTML and HTML read it in the paragraph where the statement ends, after a <br> too, and not in the next
        # paragraph.
        (".xhtml", f"<p>{_STATEMENT} {_ART_INTRODUCTION}</p>", ART),
        (".xhtml", f"<p>{_STATEMENT}<br/>{_ART_INTRODUCTION}</p>", ART),
        (".xhtml", f"<p>{_STATEMENT_FIRST_LINE}</p><p>{_STATEMENT_LAST_LINE} {_ART_INTRODUCTION}</p>", ART),
        (".xhtml", f"<p>{_STATEMENT}</p><p>{_ART_INTRODUCTION}</p>", OTHER),
        (".html", f"<p>{_STATEMENT}<br/>{_ART_INTRODUCTION}</p>", ART),
        (".html", f"<p>{_STATEMENT}</p><p>{_ART_INTRODUCTION}</p>", OTHER),
    ],
    ids=[
        "markdown same line",
        "markdown wrapped statement, its last line",
        "markdown next line",
        "markdown wrapped statement, next line",
        "xhtml same paragraph",
        "xhtml after a br",
        "xhtml statement over two paragraphs, its last paragraph",
        "xhtml next paragraph",
        "html after a br",
        "html next paragraph",
    ],
)
def test_the_text_after_the_statement_is_read_only_where_the_statement_ends(
    tmp_path: Path, suffix: str, statement: str, regime: WhitepaperType
):
    # Before any heading, Markdown, XHTML and HTML read an introduction only after the first-page statement in its
    # last line (Markdown) or paragraph (XHTML, HTML), which joins the statement's own section (CHANGELOG); in
    # 1.2.1 all of these were other.
    path = tmp_path / f"statement{suffix}"
    issuer_heading, issuer = _SST_ISSUER[0][1], _SST_ISSUER[1][1]
    if suffix == ".md":
        path.write_text(f"{statement}\n\n## {issuer_heading}\n\n{issuer}\n", encoding="utf-8")
    else:
        path.write_text(
            f"<html><body>{statement}<h2>{issuer_heading}</h2><p>{issuer}</p></body></html>", encoding="utf-8"
        )
    assert load_whitepaper(path).type is regime
