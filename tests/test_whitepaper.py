from pathlib import Path

import pytest

from micar_linter.whitepaper import WhitepaperType, load_whitepaper


def test_load_whitepaper_valid(tmp_path: Path):
    json_content = """{
        "title": "Test Token",
        "type": "emt",
        "sections": {
            "summary": "This is a summary of the token.",
            "issuer": "Issuer info here."
        },
        "extra_meta": "some_value"
    }"""
    file_path = tmp_path / "valid.json"
    file_path.write_text(json_content, encoding="utf-8")
    
    wp = load_whitepaper(file_path)
    assert wp.title == "Test Token"
    assert wp.type == WhitepaperType.EMT
    assert wp.section("summary") == "This is a summary of the token."
    assert wp.metadata == {"extra_meta": "some_value"}


def test_load_whitepaper_invalid_json(tmp_path: Path):
    file_path = tmp_path / "invalid.json"
    file_path.write_text("{invalid", encoding="utf-8")
    
    with pytest.raises(SystemExit) as excinfo:
        load_whitepaper(file_path)
    assert "Invalid JSON" in str(excinfo.value)


def test_load_whitepaper_missing_sections(tmp_path: Path):
    file_path = tmp_path / "missing_sections.json"
    file_path.write_text('{"title": "Test"}', encoding="utf-8")
    
    with pytest.raises(SystemExit) as excinfo:
        load_whitepaper(file_path)
    assert "must contain a 'sections' object" in str(excinfo.value)


def test_load_whitepaper_invalid_type(tmp_path: Path):
    file_path = tmp_path / "invalid_type.json"
    file_path.write_text('{"title": "Test", "type": "bad_type", "sections": {}}', encoding="utf-8")
    
    with pytest.raises(SystemExit) as excinfo:
        load_whitepaper(file_path)
    assert "Unknown whitepaper type" in str(excinfo.value)
