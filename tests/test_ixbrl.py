from pathlib import Path

from micar_linter.ixbrl import validate_ixbrl
from micar_linter.whitepaper import WhitepaperType, load_whitepaper
from micar_linter.xhtml_parser import load_from_xhtml


def test_ixbrl_malformed_xml(tmp_path: Path):
    file_path = tmp_path / "bad.xhtml"
    file_path.write_text("<html><p>No closing tag", encoding="utf-8")
    
    issues = validate_ixbrl(file_path)
    assert len(issues) == 1
    assert "not well-formed XML" in issues[0]


def test_ixbrl_missing_namespace(tmp_path: Path):
    file_path = tmp_path / "missing_ns.xhtml"
    file_path.write_text("<html><body><p>Hello</p></body></html>", encoding="utf-8")
    
    issues = validate_ixbrl(file_path)
    assert len(issues) == 1
    assert "Missing Inline XBRL (iXBRL) namespace" in issues[0]


def test_ixbrl_valid_and_missing_tags(tmp_path: Path):
    # Missing all tags
    file_path = tmp_path / "missing_tags.xhtml"
    content_missing = """<html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL">
    <body>
        <p>No tags here.</p>
    </body>
    </html>"""
    file_path.write_text(content_missing, encoding="utf-8")
    
    issues = validate_ixbrl(file_path)
    assert len(issues) > 1
    # Check that it complains about missing mandatory tags
    assert any("mica:IssuerLegalName" in iss for iss in issues)
    assert any("mica:RiskWarningStatement" in iss for iss in issues)

    # Valid tags present
    valid_file_path = tmp_path / "valid_tags.xhtml"
    content_valid = """<html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL" xmlns:mica="http://xbrl.esma.europa.eu/mica">
    <body>
        <ix:nonNumeric name="mica:IssuerLegalName" contextRef="c">PayEUR EMI GmbH</ix:nonNumeric>
        <ix:nonNumeric name="mica:WhitepaperTitle" contextRef="c">PayEUR White Paper</ix:nonNumeric>
        <ix:nonNumeric name="mica:CryptoAssetSymbol" contextRef="c">PEUR</ix:nonNumeric>
        <ix:nonNumeric name="mica:CryptoAssetType" contextRef="c">EMT</ix:nonNumeric>
        <ix:nonNumeric name="mica:ConsensusMechanism" contextRef="c">PoA</ix:nonNumeric>
        <ix:nonNumeric name="mica:RiskWarningStatement" contextRef="c">Warning statement value loss warning details.</ix:nonNumeric>
        <ix:nonNumeric name="mica:ManagementBodyDeclaration" contextRef="c">Management confirms completeness, fairness and clarity.</ix:nonNumeric>
    </body>
    </html>"""
    valid_file_path.write_text(content_valid, encoding="utf-8")
    
    issues_valid = validate_ixbrl(valid_file_path)
    assert len(issues_valid) == 0


def test_load_from_xhtml(tmp_path: Path):
    file_path = tmp_path / "doc.xhtml"
    html_content = """<html>
    <body>
        <h1>Plain-Language Summary</h1>
        <p>This is the plain-language summary of the PayEUR e-money token.</p>
        
        <h2>Information about the Issuer</h2>
        <p>PayEUR EMI GmbH is an authorised e-money institution. Registered seat is in Frankfurt.</p>
    </body>
    </html>"""
    file_path.write_text(html_content, encoding="utf-8")
    
    sections = load_from_xhtml(file_path)
    assert "summary" in sections
    assert "issuer" in sections
    assert "This is the plain-language summary" in sections["summary"]
    assert "Frankfurt" in sections["issuer"]


def test_load_whitepaper_xhtml_with_tagging_check(tmp_path: Path):
    file_path = tmp_path / "wp.xhtml"
    # Tagging missing (should flag ixbrl issues in whitepaper metadata)
    html_content = """<html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL">
    <body>
        <h1>Plain-Language Summary</h1>
        <p>This summary covers key information about the token and is detailed enough.</p>
    </body>
    </html>"""
    file_path.write_text(html_content, encoding="utf-8")
    
    wp = load_whitepaper(file_path)
    assert wp.title == "Wp"
    assert wp.type == WhitepaperType.OTHER
    assert "ixbrl_issues" in wp.metadata
    assert len(wp.metadata["ixbrl_issues"]) > 0
