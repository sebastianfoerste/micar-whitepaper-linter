from pathlib import Path

from micar_linter.document import load_from_markdown
from micar_linter.whitepaper import WhitepaperType, load_whitepaper


def test_load_from_markdown(tmp_path: Path):
    md_content = """# Plain-Language Summary
This is a summary of the token project.

## Mandatory Risk Warning
This is the mandatory risk warning statement.

# Underlying Technology
This is technology detail.
"""
    file_path = tmp_path / "wp.md"
    file_path.write_text(md_content, encoding="utf-8")
    
    sections = load_from_markdown(file_path)
    assert "summary" in sections
    assert "risk_warning" in sections
    assert "technology" in sections
    
    assert "This is a summary of the token project." in sections["summary"]
    assert "This is the mandatory risk warning statement." in sections["risk_warning"]
    assert "This is technology detail." in sections["technology"]


def test_load_whitepaper_markdown(tmp_path: Path):
    md_content = """# Plain-Language Summary
This is a summary of the token project. It contains key information about the project.

# Information about the Crypto-Asset Project
This project business model is clear.
"""
    file_path = tmp_path / "other_wp.md"
    file_path.write_text(md_content, encoding="utf-8")
    
    wp = load_whitepaper(file_path)
    assert wp.title == "Other Wp"
    assert wp.type == WhitepaperType.OTHER
    assert "summary" in wp.sections
    assert "project" in wp.sections
