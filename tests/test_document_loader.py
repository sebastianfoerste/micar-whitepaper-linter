from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from micar_linter.document_loader import load_document


def test_load_document_xhtml_extracts_visible_text_and_ixbrl_tags(tmp_path: Path):
    path = tmp_path / "wp.xhtml"
    repeated = " ".join(["This visible disclosure sentence contains useful MiCAR text."] * 20)
    path.write_text(
        f"""<html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL">
  <head><title>Hidden title</title><script>secret()</script></head>
  <body>
    <h1 id="summary">Summary</h1>
    <p>{repeated}</p>
    <ix:nonNumeric name="mica:IssuerLegalName" contextRef="c">Example GmbH</ix:nonNumeric>
  </body>
</html>""",
        encoding="utf-8",
    )

    loaded = load_document(path)

    assert loaded.format == "xhtml"
    assert loaded.text_extraction == "ok"
    assert "visible disclosure sentence" in loaded.text
    assert "secret()" not in loaded.text
    assert "summary" in loaded.sections
    assert "mica:IssuerLegalName" in loaded.ixbrl_tags
    assert len(loaded.source_hash_sha256) == 64


def test_load_document_xhtml_joins_words_that_spacer_spans_split(tmp_path: Path):
    path = tmp_path / "wp.xhtml"
    path.write_text(
        '<html xmlns="http://www.w3.org/1999/xhtml"><body><div class="pc">'
        '<div class="t">A.1<span class="_ _2"></span>Name</div>'
        '<div class="t">Example Money Financ<span class="_ _0"></span>ial Europe SAS</div>'
        "<h2>Information about the<br/>issuer</h2><p>Example Money is an e-money institution.</p>"
        "</div></body></html>",
        encoding="utf-8",
    )

    loaded = load_document(path)

    assert "A.1 Name Example Money Financial Europe SAS Information about the issuer" in loaded.text
    assert loaded.sections["issuer"] == "Example Money is an e-money institution."


@patch("pypdf.PdfReader")
def test_load_document_pdf_records_weak_extraction(mock_reader_cls, tmp_path: Path):
    path = tmp_path / "weak.pdf"
    path.write_bytes(b"%PDF-1.4")
    page = MagicMock()
    page.extract_text.return_value = "Short text."
    reader = MagicMock()
    reader.pages = [page]
    mock_reader_cls.return_value = reader

    loaded = load_document(path)

    assert loaded.format == "pdf"
    assert loaded.pages == 1
    assert loaded.text_extraction == "weak"
    assert any(warning.startswith("low_word_count:") for warning in loaded.warnings)


def test_load_document_txt_fallback(tmp_path: Path):
    path = tmp_path / "wp.txt"
    path.write_text(" ".join(["Summary text for a public white paper."] * 20), encoding="utf-8")

    loaded = load_document(path)

    assert loaded.format == "txt"
    assert loaded.text_extraction == "ok"
    assert loaded.pages is None


def test_study_sections_use_the_shape_rule_of_micar_lint(tmp_path: Path):
    path = tmp_path / "wp.txt"
    lines = [
        "Summary",
        "The Quillmoor Utility Token gives holders access to a shared ledger service.",
        "Information about the Project",
        "Quillmoor Ledger S.A. runs the shared ledger service in three Member States.",
        "Note: purchasers bear market, liquidity and technology risks.",
        "Holders may lose the full amount and should read this document in full.",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")

    sections = load_document(path).sections

    # The note is body text of the project section, not a risks heading.
    assert sorted(sections) == ["project", "summary"]
    assert "Note: purchasers bear" in sections["project"]


@patch("pypdf.PdfReader")
def test_study_pdf_sections_are_read_line_by_line(mock_reader_cls, tmp_path: Path):
    path = tmp_path / "wp.pdf"
    path.write_bytes(b"%PDF-1.4")
    page = MagicMock()
    page.extract_text.return_value = (
        "Summary\nThe token gives access to a ledger.\nRisk Factors\nHolders may lose money."
    )
    reader = MagicMock()
    reader.pages = [page]
    mock_reader_cls.return_value = reader

    sections = load_document(path).sections

    assert sections == {"summary": "The token gives access to a ledger.", "risks": "Holders may lose money."}
