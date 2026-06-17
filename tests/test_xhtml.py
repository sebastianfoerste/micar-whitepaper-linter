from pathlib import Path

from micar_linter.whitepaper import WhitepaperType, load_whitepaper
from micar_linter.xhtml_parser import load_from_xhtml


def test_load_from_xhtml(tmp_path: Path):
    xhtml_path = tmp_path / "test.xhtml"
    
    # Create a synthetic XHTML content
    xhtml_content = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
   "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
<head>
    <title>MiCAR Whitepaper</title>
</head>
<body>
    <h1>Summary of the offer</h1>
    <p>This is a plain-language summary of the proposed asset offering.</p>
    
    <h2>Information about the Issuer</h2>
    <p>The issuer is EuroStable AG, registered in Frankfurt.</p>
    
    <h2>Risk Factors</h2>
    <p>The principal risks include market price volatility and liquidity risks.</p>
</body>
</html>
"""
    xhtml_path.write_text(xhtml_content, encoding="utf-8")
    
    sections = load_from_xhtml(xhtml_path)
    
    assert "summary" in sections
    assert "issuer" in sections
    assert "risks" in sections
    
    assert "plain-language summary" in sections["summary"]
    assert "EuroStable AG" in sections["issuer"]
    assert "market price volatility" in sections["risks"]

def test_load_whitepaper_xhtml_type_inference(tmp_path: Path):
    xhtml_path = tmp_path / "art-test.xhtml"
    xhtml_content = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<body>
    <h1>Summary</h1>
    <p>This is a summary.</p>
    
    <h2>Stabilisation Mechanism</h2>
    <p>This asset-referenced token is backed by a reserve of assets.</p>
</body>
</html>
"""
    xhtml_path.write_text(xhtml_content, encoding="utf-8")
    
    wp = load_whitepaper(xhtml_path)
    assert wp.title == "Art Test"
    assert wp.type == WhitepaperType.ART
    assert "summary" in wp.sections
    assert "art" in wp.sections
