"""The white paper type a draft declares in the type field of the template (ADR 0009).

Every draft here is synthetic. The known-truth set writes each case in every format whose regime the wording
decides (DOCX, PDF, Markdown, heading-layout XHTML and HTML) and in the numbered-field XHTML layout, and
checks the regime and the note that each one gets.
"""

import json
import time
from html import escape
from pathlib import Path

import docx
import pytest
from test_heading_detection import EVERY_WRITER, TECHNOLOGY

from micar_linter.cli import main
from micar_linter.declared_type import (
    _REASONS as REASONS,
)
from micar_linter.declared_type import (
    CASE,
    CODES,
    HIDDEN,
    MARKDOWN,
    NUMBER,
    OPEN,
    TEXT,
    TYPE_FIELD_NAMES,
    TYPE_FIELDS,
    DeclaredType,
    read_declared_type,
)
from micar_linter.linter import lint_whitepaper
from micar_linter.whitepaper import WhitepaperType, load_whitepaper
from micar_linter.xhtml_parser import document_texts

OTHER, ART, EMT = WhitepaperType.OTHER, WhitepaperType.ART, WhitepaperType.EMT
ROOT = Path(__file__).resolve().parents[1]
NUMBERED_SAMPLE = ROOT / "examples" / "numbered-other-draft.xhtml"

# Wording that the inference reads as each regime.
WORDING = {
    EMT: "The token is an e-money token and holders have a claim on the issuer at par value at any time.",
    ART: "The token is an asset-referenced token backed by a reserve of assets held by a custodian.",
    OTHER: "The token gives access to a service on the ledger and holders have no claim on the issuer.",
}
SUMMARY = "This summary gives the key information on the synthetic token of a fictional issuer."


def _blocks(lines: list[str], wording: WhitepaperType) -> list[tuple[str, str]]:
    return [
        ("heading", "Summary"),
        ("body", SUMMARY),
        ("heading", "Information about the crypto-asset"),
        ("body", WORDING[wording]),
        *(("plain", line) for line in lines),
        ("heading", "Technology"),
        ("body", TECHNOLOGY),
    ]


def test_the_type_fields_come_from_the_template_modules():
    # Item 1 of the register data (classification_data), the field names (template_fields) and the German
    # names and codes (template_types, read from the OJ text on 2026-11-04); nothing is held twice.
    assert TYPE_FIELDS == {OTHER: ("F.4", "OTHR"), ART: ("B.7", "ARTW"), EMT: ("B.4", "EMTW")}
    assert TYPE_FIELD_NAMES == (
        "Type of crypto-asset white paper",
        "Art des Kryptowerte-Whitepapers",
        "Art des Whitepapers",
        "Type of white paper",
    )


# Known truth: the lines of a type field and what the draft declares (None: no type, the wording decides)
# with the reason it declares none ("" where it holds no type field, or a table of contents only). In the
# drafts the next field of the template follows these lines (SUBMISSION).
CASES: dict[str, tuple[list[str], WhitepaperType | None, str]] = {
    "number name code": (["F.4 Type of crypto-asset white paper OTHR"], OTHER, ""),
    "name of table 4 on F.4": (["F.4 Type of white paper OTHR"], OTHER, ""),
    "capitals": (["F.4 TYPE OF WHITE PAPER OTHR"], OTHER, ""),
    "colon after the name": (["F.4 Type of white paper: OTHR"], OTHER, ""),
    "colon after the number": (["F.4: Type of crypto-asset white paper", "OTHR"], OTHER, ""),
    "dashes": (["F.4 - Type of crypto-asset white paper - OTHR"], OTHER, ""),
    "code on the next line": (["F.4 Type of white paper", "OTHR"], OTHER, ""),
    "number on the line before": (["F.4", "Type of crypto-asset white paper", "OTHR"], OTHER, ""),
    "ART": (["B.7 Type of crypto-asset white paper ARTW"], ART, ""),
    "EMT": (["B.4 Type of white paper EMTW"], EMT, ""),
    "EMT with the name of table 2": (["B.4 Type of crypto-asset white paper", "EMTW"], EMT, ""),
    "no number": (["Type of white paper: EMTW"], EMT, ""),
    "no number, two lines": (["Type of crypto-asset white paper", "ARTW"], ART, ""),
    "German": (["F.4 Art des Kryptowerte-Whitepapers OTHR"], OTHER, ""),
    "German EMT": (["B.4 Art des Whitepapers", "EMTW"], EMT, ""),
    "quoted": (["F.4 Type of crypto-asset white paper: \u2018OTHR\u2019"], OTHER, ""),
    "full stop": (["F.4 Type of white paper: OTHR."], OTHER, ""),
    "leading zero": (["F.04 Type of white paper OTHR"], OTHER, ""),
    "list mark": (["- F.4 Type of white paper: OTHR"], OTHER, ""),
    "next field on the line": (["F.4 Type of white paper OTHR F.5 The type of submission NEWT"], OTHER, ""),
    "twice the same": (["F.4 Type of white paper OTHR", "F.4 Type of crypto-asset white paper: OTHR"], OTHER, ""),
    # A table of contents is no type field, before the field or alone.
    "contents": (["F.3 Planned application of functionalities 19", "F.4 Type of white paper 19"], None, ""),
    "contents with dot leaders": (["F.4 Type of white paper ........ 19"], None, ""),
    "contents, page on the next line": (["F.4 Type of white paper", "19"], None, ""),
    "contents, then the field": (["F.4 Type of white paper 19", "F.4 Type of white paper", "OTHR"], OTHER, ""),
    "contents without pages": (["F.4 Type of white paper", "F.5 The type of submission"], None, ""),
    "contents without pages on one line": (["F.4 Type of white paper F.5 The type of submission"], None, ""),
    "contents without pages, then the field": (
        ["F.4 Type of crypto-asset white paper", "F.5 Type of submission", "F.4 Type of crypto-asset white paper", "OTHR"],
        OTHER,
        "",
    ),
    # Two different codes.
    "two fields": (["F.4 Type of crypto-asset white paper OTHR", "B.7 Type of crypto-asset white paper ARTW"], None, CODES),
    "two fields without numbers": (
        ["Type of white paper: OTHR", "F.5 The type of submission NEWT", "Type of white paper: EMTW"],
        None,
        CODES,
    ),
    "two codes in one answer": (["F.4 Type of white paper OTHR or ARTW"], None, CODES),
    "the list of codes": (["Type of crypto-asset white paper \u2018ARTW\u2019 \u2018EMTW\u2019 \u2018OTHR\u2019"], None, CODES),
    # A code under the number of another field: the field numbers collide across the tables.
    "OTHR under B.7": (["B.7 Type of crypto-asset white paper OTHR"], None, NUMBER),
    "EMTW under F.4": (["F.4 Type of white paper EMTW"], None, NUMBER),
    "ARTW under B.4": (["B.4 Type of white paper ARTW"], None, NUMBER),
    "OTHR under F.5": (["F.5 Type of white paper OTHR"], None, NUMBER),
    # Lower case.
    "lower case": (["F.4 Type of white paper othr"], None, CASE),
    "mixed case": (["F.4 Type of white paper Othr"], None, CASE),
    # Other text in the answer.
    "gloss": (["F.4 Type of white paper OTHR - other crypto-assets"], None, TEXT),
    "gloss in brackets": (["F.4 Type of white paper", "OTHR (Other crypto-asset token white paper)."], None, TEXT),
    "code in a sentence": (["F.4 Type of crypto-asset white paper", "The white paper type is OTHR."], None, TEXT),
    "label words only": (["F.4 Type of crypto-asset white paper", "Other crypto-asset token white paper"], None, TEXT),
    "negated code": (["F.4 Type of white paper not ARTW"], None, TEXT),
    "code inside a word": (["F.4 Type of white paper OTHRX"], None, TEXT),
    "code after letters": (["F.4 Type of white paper XOTHR"], None, TEXT),
    "code with a digit": (["F.4 Type of white paper OTHR2"], None, TEXT),
    "code with a hyphen": (["F.4 Type of white paper OTHR-2"], None, TEXT),
    "submission code": (["F.4 Type of white paper NEWT"], None, TEXT),
    "name twice": (["F.4 Type of white paper Type of crypto-asset white paper OTHR"], None, TEXT),
    "a later field on the line": (["F.4 Type of white paper OTHR F.6 Crypto-asset characteristics"], None, TEXT),
    # The field goes on after the code.
    "gloss on the next line": (["F.4 Type of white paper", "OTHR", "Other crypto-asset token white paper"], None, OPEN),
    "text after a one-line field": (["F.4 Type of white paper OTHR", "(other crypto-assets)"], None, OPEN),
    "text after the field without a number": (["Type of white paper: EMTW", "The token is an e-money token."], None, OPEN),
    "a later field instead of an answer": (["F.4 Type of white paper", "F.6 Crypto-asset characteristics"], None, TEXT),
    "content column reprinted": (
        ["B.4", "Type of white paper", "The type of white paper notified.", "EMTW", "EMTW"],
        None,
        TEXT,
    ),
    # No type field: the name does not start the line, or another field's name stands under the number.
    "name inside a sentence": (["The field Type of white paper OTHR applies to other crypto-assets."], None, ""),
    "number and name inside a sentence": (["Under field F.4 Type of white paper ARTW is not used."], None, ""),
    "code after the name in prose": (["Issuers of such tokens enter EMTW in the field Type of white paper."], None, ""),
    "list number before the name": (["4. Type of white paper", "OTHR"], None, ""),
    "F.4 of table 3": (["F.4 Token-related risks", "OTHR"], None, ""),
    "B.7 of table 4": (["B.7 Website of the issuer", "ARTW"], None, ""),
    "B.7 of table 2": (["B.7 Legal entity identifier", "ARTW"], None, ""),
    "B.4 of table 3": (["B.4 Third-party roles", "EMTW"], None, ""),
    "B.4 of table 2": (["B.4 Registered address", "EMTW"], None, ""),
    # Pinned limits: a name that does not start its line, or that a line end splits, is no type field.
    "field in the middle of a line": (["Part F F.4 Type of white paper OTHR"], None, ""),
    "name wrapped over two lines": (["B.4 Type of white", "paper", "EMTW"], None, ""),
    "submission field only": (["F.5 The type of submission NEWT"], None, ""),
    "code alone": (["OTHR"], None, ""),
    "no field": ([], None, ""),
}


# The field after the type field in each table, which ends it.
SUBMISSION = {
    OTHER: "F.5 The type of submission NEWT",
    ART: "B.8 The type of submission NEWT",
    EMT: "B.5 The type of submission NEWT",
}


def _wording(declared: WhitepaperType | None) -> WhitepaperType:
    # Wording that names another regime than the declared one, so the declaration must win.
    return OTHER if declared is EMT else EMT


@pytest.mark.parametrize("suffix", sorted(EVERY_WRITER))
@pytest.mark.parametrize("case", CASES)
def test_known_truth(tmp_path: Path, suffix: str, case: str):
    lines, declared, problem = CASES[case]
    wording = _wording(declared)
    lines = [*lines, SUBMISSION[declared or OTHER]]
    path = EVERY_WRITER[suffix](tmp_path / f"draft{suffix}", _blocks(lines, wording))
    whitepaper = load_whitepaper(path)
    notes = whitepaper.metadata["extraction_notes"]
    type_notes = [note for note in notes if "type field of the template" in note]
    if declared is not None:
        assert whitepaper.type is declared
        assert len(type_notes) == 1
        assert f"so the checks ran under the declared type ({declared.value})." in type_notes[0]
        assert type_notes[0].endswith(f"({wording.value}); check which regime applies.")
    else:
        assert whitepaper.type is wording
        if problem:
            assert len(type_notes) == 1
            assert "declares no type" in type_notes[0]
            assert REASONS[problem] in type_notes[0]
            assert type_notes[0].endswith("The regime was inferred from the wording of the draft instead.")
        else:
            assert type_notes == []


LAYOUTS = {
    "one line": lambda number, name, code: [f"{number} {name} {code}"],
    "colon": lambda number, name, code: [f"{number} {name}: {code}"],
    "next line": lambda number, name, code: [f"{number} {name}", code],
    "number line before": lambda number, name, code: [number, name, code],
    "no number": lambda number, name, code: [f"{name}: {code}"],
}


@pytest.mark.parametrize("suffix", sorted(EVERY_WRITER))
@pytest.mark.parametrize("regime", list(WhitepaperType))
@pytest.mark.parametrize("name", TYPE_FIELD_NAMES)
@pytest.mark.parametrize("layout", LAYOUTS)
def test_every_name_code_and_layout_declares(
    tmp_path: Path, suffix: str, regime: WhitepaperType, name: str, layout: str
):
    # Any of the four names counts on the type field of any table; the code and its number decide.
    number, code = TYPE_FIELDS[regime]
    lines = [*LAYOUTS[layout](number, name, code), SUBMISSION[regime]]
    path = EVERY_WRITER[suffix](tmp_path / f"draft{suffix}", _blocks(lines, _wording(regime)))
    assert load_whitepaper(path).type is regime


@pytest.mark.parametrize("suffix", sorted(EVERY_WRITER))
def test_zero_width_characters_in_a_type_field_are_not_read(tmp_path: Path, suffix: str):
    if suffix == ".pdf":
        pytest.skip("Helvetica in WinAnsiEncoding has no zero-width space")
    line = "F.4​ Type of white­ paper​ OTHR"
    path = EVERY_WRITER[suffix](tmp_path / f"draft{suffix}", _blocks([line, SUBMISSION[OTHER]], EMT))
    assert load_whitepaper(path).type is OTHER


@pytest.mark.parametrize("suffix", sorted(EVERY_WRITER))
def test_a_type_field_that_a_heading_follows_declares_nothing(tmp_path: Path, suffix: str):
    # The heading after the field starts no other field, so the answer may go on under it.
    path = EVERY_WRITER[suffix](tmp_path / f"draft{suffix}", _blocks(["F.4 Type of white paper OTHR"], EMT))
    whitepaper = load_whitepaper(path)
    assert whitepaper.type is EMT
    assert any(REASONS[OPEN] in note for note in whitepaper.metadata["extraction_notes"])


def test_a_type_field_at_the_end_of_the_text_declares(tmp_path: Path):
    path = tmp_path / "draft.md"
    path.write_text(f"## Summary\n\n{SUMMARY}\n\n{WORDING[EMT]}\n\nType of white paper: OTHR\n", encoding="utf-8")
    assert load_whitepaper(path).type is OTHER


DECLARING = {
    OTHER: ["F.4 Type of crypto-asset white paper OTHR", SUBMISSION[OTHER]],
    ART: ["B.7 Type of crypto-asset white paper ARTW", SUBMISSION[ART]],
    EMT: ["B.4 Type of white paper EMTW", SUBMISSION[EMT]],
}


def _findings(whitepaper):
    report = lint_whitepaper(whitepaper)
    return report, [(f.rule.rule_id, f.status, f.word_count, f.issues) for f in report.findings]


@pytest.mark.parametrize("suffix", sorted(EVERY_WRITER))
@pytest.mark.parametrize("declared", list(WhitepaperType))
@pytest.mark.parametrize("wording", list(WhitepaperType))
def test_a_declared_type_checks_exactly_as_the_same_type_stated(
    tmp_path: Path, suffix: str, declared: WhitepaperType, wording: WhitepaperType
):
    # Fail closed: the declaration chooses the rule set and nothing else. Every finding, the sections and the
    # other notes are those of --type with the declared type; only the note on the declared type is added.
    path = EVERY_WRITER[suffix](tmp_path / f"draft{suffix}", _blocks(DECLARING[declared], wording))
    read, stated = load_whitepaper(path), load_whitepaper(path, declared)
    assert read.type is stated.type is declared
    assert read.sections == stated.sections
    report, findings = _findings(read)
    stated_report, stated_findings = _findings(stated)
    assert findings == stated_findings
    added = [warning for warning in report.warnings if warning not in stated_report.warnings]
    assert len(added) == 1 and len(report.warnings) == len(stated_report.warnings) + 1
    assert "No regime was stated, so the checks ran under the declared type" in added[0]
    # The note says where the wording reads otherwise.
    assert ("check which regime applies" in added[0]) is (wording is not declared)


@pytest.mark.parametrize("stated", list(WhitepaperType))
def test_a_stated_regime_overrides_the_declared_type_with_a_note(tmp_path: Path, stated: WhitepaperType):
    path = EVERY_WRITER[".docx"](tmp_path / "draft.docx", _blocks(DECLARING[OTHER], OTHER))
    whitepaper = load_whitepaper(path, stated)
    assert whitepaper.type is stated
    notes = [note for note in whitepaper.metadata["extraction_notes"] if "type field" in note]
    if stated is OTHER:
        assert notes == []
    else:
        assert notes == [
            "The draft declares its type in the type field of the template of Implementing Regulation (EU) "
            "2024/2984 (F.4 of Table 2): OTHR, a white paper for crypto-assets other than asset-referenced "
            f"tokens and e-money tokens. The regime was stated as {stated.value}, and the checks ran under the "
            "stated regime. Check which regime applies."
        ]


def test_a_stated_regime_gets_no_note_on_a_type_field_that_declares_nothing(tmp_path: Path):
    path = EVERY_WRITER[".md"](tmp_path / "draft.md", _blocks(["F.4 Type of white paper othr", SUBMISSION[OTHER]], EMT))
    assert not [note for note in load_whitepaper(path, ART).metadata["extraction_notes"] if "type field" in note]


def test_the_notes_in_full(tmp_path: Path):
    path = EVERY_WRITER[".md"](tmp_path / "draft.md", _blocks(DECLARING[EMT], ART))
    assert load_whitepaper(path).metadata["extraction_notes"] == (
        "The draft declares its type in the type field of the template of Implementing Regulation (EU) 2024/2984 "
        "(B.4 of Table 4): EMTW, a white paper for an e-money token. No regime was stated, so the checks ran "
        "under the declared type (emt). The wording of the draft reads as a white paper for an asset-referenced "
        "token (art); check which regime applies.",
    )
    path = EVERY_WRITER[".md"](tmp_path / "draft.md", _blocks(["F.4 Type of white paper EMTW", SUBMISSION[OTHER]], OTHER))
    assert load_whitepaper(path).metadata["extraction_notes"] == (
        "The draft holds the type field of the template of Implementing Regulation (EU) 2024/2984, but it "
        "declares no type: a code stands under the number of another field (the template gives F.4 for OTHR, B.7 "
        "for ARTW, B.4 for EMTW). The regime was inferred from the wording of the draft instead.",
    )


# --- Hidden text ----------------------------------------------------------------------------------------


def _docx_with_hidden(path: Path, shown: list[str], hidden: list[str]) -> Path:
    document = docx.Document()
    document.add_heading("Summary", level=1)
    document.add_paragraph(SUMMARY)
    document.add_heading("Information about the crypto-asset", level=1)
    document.add_paragraph(WORDING[EMT])
    for line in shown:
        document.add_paragraph(line)
    for line in hidden:
        document.add_paragraph().add_run(line).font.hidden = True
    document.save(path)
    return path


def _xhtml_with_hidden(path: Path, shown: list[str], hidden: list[str]) -> Path:
    body = "\n".join(
        [f"<h2>Summary</h2><p>{SUMMARY}</p>", f"<h2>Information about the crypto-asset</h2><p>{WORDING[EMT]}</p>"]
        + [f"<p>{escape(line)}</p>" for line in shown]
        + [f'<p style="display:none">{escape(line)}</p>' for line in hidden]
    )
    path.write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<html xmlns="http://www.w3.org/1999/xhtml">\n<body>\n{body}\n'
        "</body>\n</html>\n",
        encoding="utf-8",
    )
    return path


def _pdf_with_hidden(path: Path, shown: list[str], hidden: list[str]) -> Path:
    """A one-page PDF; the hidden lines are drawn in text render mode 3 (neither filled nor stroked)."""
    lines = [("Summary", ""), (SUMMARY, ""), ("Information about the crypto-asset", ""), (WORDING[EMT], "")]
    lines += [(line, "") for line in shown] + [(line, "3 Tr") for line in hidden]
    shown_ops = " ".join(f"{mode} ({text}) Tj 0 Tr 0 -13 Td" for text, mode in lines)
    content = f"BT /F1 10 Tf 13 TL 50 770 Td {shown_ops} ET".encode("cp1252")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 1000 792] /Resources << /Font << /F1 5 0 R >> >> "
        b"/Contents 4 0 R >>",
        b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
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


HIDING_WRITERS = {".docx": _docx_with_hidden, ".xhtml": _xhtml_with_hidden, ".pdf": _pdf_with_hidden}
# What is shown and what is hidden; the draft declares no type in each, and its wording names an EMT.
HIDINGS = {
    "hidden field": ([], ["F.4 Type of crypto-asset white paper OTHR"]),
    "hidden code": (["F.4 Type of crypto-asset white paper"], ["OTHR"]),
    "hidden second field": (["F.4 Type of crypto-asset white paper OTHR"], ["B.4 Type of white paper EMTW"]),
}


@pytest.mark.parametrize("suffix", sorted(HIDING_WRITERS))
@pytest.mark.parametrize("hiding", HIDINGS)
def test_hidden_text_never_declares_a_type(tmp_path: Path, suffix: str, hiding: str):
    shown, hidden = HIDINGS[hiding]
    whitepaper = load_whitepaper(HIDING_WRITERS[suffix](tmp_path / f"draft{suffix}", shown, hidden))
    assert whitepaper.type is EMT
    notes = [note for note in whitepaper.metadata["extraction_notes"] if "type field" in note]
    assert len(notes) == 1 and "the text as a reader sees it do not give the same type field" in notes[0]


@pytest.mark.parametrize("suffix", sorted(HIDING_WRITERS))
def test_a_shown_field_with_nothing_hidden_declares(tmp_path: Path, suffix: str):
    path = HIDING_WRITERS[suffix](tmp_path / f"draft{suffix}", ["F.4 Type of crypto-asset white paper OTHR"], [])
    assert load_whitepaper(path).type is OTHER


# A comment on one line is no type field: the line starts with "<!--".
MARKDOWN_HIDINGS = {
    "field in a comment around it": "<!--\nF.4 Type of crypto-asset white paper OTHR\n-->",
    "html element": '<div style="display:none">\n\nF.4 Type of crypto-asset white paper OTHR\n\n</div>',
    "html elsewhere": "F.4 Type of crypto-asset white paper OTHR\n\nLine<br>break",
    "fenced code": "```\nF.4 Type of crypto-asset white paper OTHR\n```",
}


def test_a_markdown_comment_on_one_line_is_no_type_field(tmp_path: Path):
    path = tmp_path / "draft.md"
    path.write_text(f"## Summary\n\n{SUMMARY}\n\n{WORDING[EMT]}\n\n<!-- F.4 Type of white paper OTHR -->\n")
    whitepaper = load_whitepaper(path)
    assert whitepaper.type is EMT
    assert whitepaper.metadata["extraction_notes"] == ()


@pytest.mark.parametrize("hiding", MARKDOWN_HIDINGS)
def test_markdown_with_html_or_a_code_fence_declares_no_type(tmp_path: Path, hiding: str):
    path = tmp_path / "draft.md"
    path.write_text(f"## Summary\n\n{SUMMARY}\n\n{WORDING[EMT]}\n\n{MARKDOWN_HIDINGS[hiding]}\n", encoding="utf-8")
    whitepaper = load_whitepaper(path)
    assert whitepaper.type is EMT
    assert read_declared_type(path.read_text(encoding="utf-8"), markdown=True).problems == (MARKDOWN,)
    assert any("holds HTML, an HTML comment or a fenced code block" in note for note in (
        whitepaper.metadata["extraction_notes"]
    ))


def test_markdown_table_emphasis_and_autolinks_still_declare(tmp_path: Path):
    path = tmp_path / "draft.md"
    path.write_text(
        f"## Summary\n\n{SUMMARY}\n\n{WORDING[EMT]}\n\n| No | Field | Content |\n|---|---|---|\n"
        "| F.4 | Type of crypto-asset white paper | OTHR |\n\n**F.5: The type of submission**\n\n`NEWT`\n\n"
        "See <https://example.org/register>.\n",
        encoding="utf-8",
    )
    assert load_whitepaper(path).type is OTHER


# --- Numbered-field XHTML ---------------------------------------------------------------------------------


def _numbered_other(tmp_path: Path, rows: str) -> Path:
    path = tmp_path / "numbered.xhtml"
    text = NUMBERED_SAMPLE.read_text(encoding="utf-8")
    path.write_text(text.replace("<tr><td>F.6</td>", f"{rows}\n<tr><td>F.6</td>", 1), encoding="utf-8")
    return path


NUMBERED_ROWS = {
    "table row": ("<tr><td>F.4</td><td>Type of crypto-asset white paper</td><td>OTHR</td></tr>", OTHER, ""),
    "name of table 4": ("<tr><td>F.4</td><td>Type of white paper</td><td>OTHR</td></tr>", OTHER, ""),
    "German": ("<tr><td>F.4</td><td>Art des Kryptowerte-Whitepapers</td><td>OTHR</td></tr>", OTHER, ""),
    "number and name in one cell": ("<tr><td>F.4 Type of crypto-asset white paper</td><td>OTHR</td></tr>", OTHER, ""),
    "lower case": ("<tr><td>F.4</td><td>Type of crypto-asset white paper</td><td>othr</td></tr>", None, CASE),
    "code of table 4": ("<tr><td>F.4</td><td>Type of crypto-asset white paper</td><td>EMTW</td></tr>", None, NUMBER),
    "two codes": ("<tr><td>F.4</td><td>Type of crypto-asset white paper</td><td>OTHR ARTW</td></tr>", None, CODES),
    "gloss": ("<tr><td>F.4</td><td>Type of crypto-asset white paper</td><td>OTHR (other)</td></tr>", None, TEXT),
    "hidden row": (
        '<tr style="display:none"><td>F.4</td><td>Type of crypto-asset white paper</td><td>OTHR</td></tr>',
        None,
        HIDDEN,
    ),
    "content column": (
        "<tr><td>F.4</td><td>Type of crypto-asset white paper</td><td>The type of white paper notified</td>"
        "<td>OTHR</td></tr>",
        None,
        TEXT,
    ),
}


@pytest.mark.parametrize("row", NUMBERED_ROWS)
def test_a_numbered_field_draft_is_linted_under_its_declared_type(tmp_path: Path, row: str):
    markup, declared, problem = NUMBERED_ROWS[row]
    path = _numbered_other(tmp_path, markup)
    if declared is None:
        with pytest.raises(SystemExit) as raised:
            load_whitepaper(path)
        message = str(raised.value)
        assert "State the regime explicitly: other, art or emt. The draft holds the type field" in message
        assert message.endswith(f"declares no type: {REASONS[problem]}.")
        return
    whitepaper = load_whitepaper(path)
    assert whitepaper.type is declared
    stated = load_whitepaper(path, declared)
    assert _findings(whitepaper)[1] == _findings(stated)[1]
    assert whitepaper.metadata["numbered_fields"] == stated.metadata["numbered_fields"]
    # The template wording names every regime, so the wording of a numbered draft is not read for one.
    (note,) = [note for note in whitepaper.metadata["extraction_notes"] if "type field" in note]
    assert note.endswith("No regime was stated, so the checks ran under the declared type (other).")
    # ITS.CODE_LISTS reads the same field under Table 2 and finds the code.
    code_lists = next(f for f in lint_whitepaper(whitepaper).findings if f.rule.rule_id == "ITS.CODE_LISTS")
    assert not any("F.4" in issue for issue in code_lists.issues)


def test_a_numbered_field_draft_that_the_field_level_reading_splits_otherwise_declares_nothing(tmp_path: Path):
    # The text gives "F.4 / Type of crypto-asset white paper / OTHR", but the field occurs twice in the table, the
    # second time with other text, so the answer ITS.CODE_LISTS reads is not exactly the code.
    path = _numbered_other(
        tmp_path,
        "<tr><td>F.4</td><td>Type of crypto-asset white paper</td><td>OTHR</td></tr>\n"
        "<tr><td>F.4</td><td>Notes</td><td>see above</td></tr>",
    )
    with pytest.raises(SystemExit, match="as the field-level checks read it, does not hold exactly the code"):
        load_whitepaper(path)
    assert read_declared_type(*document_texts(path)) == DeclaredType("OTHR", "F.4")


def test_a_numbered_field_draft_without_a_type_field_still_needs_the_regime(capsys):
    with pytest.raises(SystemExit) as raised:
        load_whitepaper(NUMBERED_SAMPLE)
    assert str(raised.value) == (
        "numbered-other-draft.xhtml uses the numbered fields of Implementing Regulation (EU) 2024/2984. "
        "State the regime explicitly: other, art or emt."
    )


def _numbered_table(path: Path, rows: list[tuple[str, str, str]]) -> Path:
    body = "".join(f"<tr><td>{number}</td><td>{escape(name)}</td><td>{escape(answer)}</td></tr>" for number, name, answer in rows)
    path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<html xmlns="http://www.w3.org/1999/xhtml">\n<body>\n'
        f"<table>{body}</table>\n</body>\n</html>\n",
        encoding="utf-8",
    )
    return path


@pytest.mark.parametrize("regime", [ART, EMT])
def test_a_numbered_art_or_emt_draft_declares_its_type(tmp_path: Path, regime: WhitepaperType):
    number, code = TYPE_FIELDS[regime]
    rows = [
        ("A.1", "Name", "Synthetic Issuer SA"),
        ("B.1", "Issuer different from offeror", "false"),
        (number, "Type of crypto-asset white paper" if regime is ART else "Type of white paper", code),
        ("C.1", "Name", "Synthetic Platform SA"),
        ("D.1", "Name of the token", "Synthetic Token"),
    ]
    path = _numbered_table(tmp_path / "numbered.xhtml", rows)
    whitepaper = load_whitepaper(path)
    assert whitepaper.type is regime
    assert _findings(whitepaper)[1] == _findings(load_whitepaper(path, regime))[1]
    assert main([str(path), "--json"]) == 0


def test_a_directory_lints_a_numbered_draft_that_declares_its_type(tmp_path: Path, capsys):
    folder = tmp_path / "drafts"
    folder.mkdir()
    _numbered_other(folder, "<tr><td>F.4</td><td>Type of crypto-asset white paper</td><td>OTHR</td></tr>")
    output = tmp_path / "batch.json"
    main([str(folder), "--batch-output", str(output)])
    pack = json.loads(output.read_text(encoding="utf-8"))
    assert pack["summary"]["failed_files"] == 0 and pack["summary"]["supported_files"] == 1
    assert pack["files"][0]["whitepaper_type"] == "other"
    assert pack["warnings"] == []


# --- Time ---------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "unit",
    [
        "F.4 Type of white paper\n",
        "Type of white paper OTHR F.3 F.3 F.3 F.3\n",
        "F.4\nType of crypto-asset white paper\n",
        "Type of white paper " + "x " * 5_000 + "\n",
    ],
    ids=["names", "numbers on the line", "number lines", "long answers"],
)
def test_reading_the_type_field_takes_linear_time(unit: str):
    text = unit * (400_000 // len(unit) + 1)
    start = time.perf_counter()
    read_declared_type(text, text.replace("Type", "Typ"))
    assert time.perf_counter() - start < 3
