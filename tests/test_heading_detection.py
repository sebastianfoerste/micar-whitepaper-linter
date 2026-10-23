"""A DOCX paragraph or PDF line opens a section only if it is shaped like a heading.

A body paragraph with a bold lead-in ("Note: ...") in a DOCX, or a short body line in a PDF, that
mentions "risks" used to open a risks section, so a draft with no risk section passed the ANNEX_I.I
blocker. Heading text is not section body either. The PDFs are real files parsed by pypdf.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import docx
import pytest
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from micar_linter.document import load_from_docx, load_from_pdf
from micar_linter.linter import lint_whitepaper
from micar_linter.rules.base import Finding, Severity
from micar_linter.whitepaper import WhitepaperType, load_whitepaper

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
        if kind == "heading":
            doc.add_heading(text, level=1)
        elif kind == "bold":
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
        else:
            doc.add_paragraph(text)
    doc.save(path)
    return path


def _write_pdf(path: Path, blocks: list[tuple[str, str]]) -> Path:
    """A one-page PDF in Helvetica with one text line per heading or note and body text wrapped at 90."""
    lines = [
        line for kind, text in blocks for line in (textwrap.wrap(text, 90) if kind == "body" else [text])
    ]
    escaped = (line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") for line in lines)
    content = (
        "BT /F1 10 Tf 13 TL 50 770 Td " + " ".join(f"({line}) Tj T*" for line in escaped) + " ET"
    ).encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> "
        b"/Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
    ]
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
