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
