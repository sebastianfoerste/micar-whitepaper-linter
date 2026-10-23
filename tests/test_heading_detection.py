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
from pathlib import Path

import docx
import pytest
from docx.enum.style import WD_STYLE_TYPE
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


# 10 pt Helvetica for body text and plain lines, 10 pt Helvetica-Bold for "bold" lines, 14 pt for "large" ones.
PDF_FONTS = {"bold": "/F2 10 Tf", "large": "/F2 14 Tf"}


def _shown(kind: str, line: str, next_line: str) -> str:
    """The content stream operators of one block line; a "space" block only moves 20 pt further down."""
    if kind == "space":
        return "0 -20 Td"
    escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return f"{PDF_FONTS.get(kind, '/F1 10 Tf')} ({escaped}) Tj {next_line}"


def _write_pdf(path: Path, blocks: list[tuple[str, str]], next_line: str = "0 -13 Td") -> Path:
    """A one-page PDF with one text line per block, 13 pt apart, and body text wrapped at 90 characters.

    Each line moves to the next with next_line: Td, as word processors write, or T* after a TL leading.
    """
    lines = [
        (kind, line)
        for kind, text in blocks
        for line in (textwrap.wrap(text, 90) if kind == "body" else [text])
    ]
    shown = " ".join(_shown(kind, line, next_line) for kind, line in lines)
    content = f"BT 13 TL 50 770 Td {shown} ET".encode("cp1252")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 1000 792] "
        b"/Resources << /Font << /F1 4 0 R /F2 6 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
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
RIGHTS = "Holders have rights and obligations; each holder may enforce rights in court under the terms. " * 6
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
