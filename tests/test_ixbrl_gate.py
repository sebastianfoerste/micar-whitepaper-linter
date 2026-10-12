"""The iXBRL format gate must fail closed.

A blocker-severity rule may only report `pass` when the document actually went
through Inline XBRL validation. Draft formats leave the blocker open.
"""

from pathlib import Path

import pytest

from micar_linter.linter import Linter
from micar_linter.rules import RULESETS
from micar_linter.whitepaper import load_whitepaper

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"

VALID_IXBRL = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"
      xmlns:ix="http://www.xbrl.org/2013/inlineXBRL"
      xmlns:mica="http://example.org/mica">
  <body>
    <p><ix:nonNumeric name="mica:IssuerLegalName">Example Issuer SA</ix:nonNumeric></p>
    <p><ix:nonNumeric name="mica:WhitepaperTitle">Example</ix:nonNumeric></p>
    <p><ix:nonNumeric name="mica:CryptoAssetSymbol">EXA</ix:nonNumeric></p>
    <p><ix:nonNumeric name="mica:CryptoAssetType">other</ix:nonNumeric></p>
    <p><ix:nonNumeric name="mica:ConsensusMechanism">PoS</ix:nonNumeric></p>
    <p><ix:nonNumeric name="mica:RiskWarningStatement">Risk warning.</ix:nonNumeric></p>
    <p><ix:nonNumeric name="mica:ManagementBodyDeclaration">Declaration.</ix:nonNumeric></p>
  </body>
</html>
"""

NO_NAMESPACE = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><body><p>No iXBRL here.</p></body></html>
"""

MISSING_TAGS = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"
      xmlns:ix="http://www.xbrl.org/2013/inlineXBRL"
      xmlns:mica="http://example.org/mica">
  <body><p><ix:nonNumeric name="mica:IssuerLegalName">Only one tag</ix:nonNumeric></p></body>
</html>
"""

MALFORMED = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><body><p>unclosed
"""


def _ixbrl_finding(path: Path):
    whitepaper = load_whitepaper(path)
    linter = Linter(RULESETS[whitepaper.type])
    for finding in linter.lint(whitepaper):
        if finding.rule.rule_id == "COMMON.IXBRL_TAGGING":
            return finding
    raise AssertionError("COMMON.IXBRL_TAGGING was not applied")


def _write(tmp_path: Path, name: str, body: str) -> Path:
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    return path


def test_valid_ixbrl_xhtml_passes(tmp_path: Path):
    finding = _ixbrl_finding(_write(tmp_path, "ok.xhtml", VALID_IXBRL))
    assert finding.status == "pass"
    assert finding.issues == ()


@pytest.mark.parametrize(
    "name,body",
    [
        ("no-namespace.xhtml", NO_NAMESPACE),
        ("missing-tags.xhtml", MISSING_TAGS),
        ("malformed.xhtml", MALFORMED),
    ],
)
def test_defective_xhtml_never_passes(tmp_path: Path, name: str, body: str):
    finding = _ixbrl_finding(_write(tmp_path, name, body))
    assert finding.status != "pass"
    assert finding.issues


@pytest.mark.parametrize("sample", ["incomplete.json", "art-stablecoin.json", "emt-token.json"])
def test_json_draft_leaves_the_blocker_open(sample: str):
    finding = _ixbrl_finding(EXAMPLES / sample)
    assert finding.status == "missing"
    assert finding.rule.severity.name == "BLOCKER"


def test_docx_draft_leaves_the_blocker_open():
    finding = _ixbrl_finding(EXAMPLES / "sample-draft.docx")
    assert finding.status == "missing"


def test_json_cannot_forge_a_validated_marker(tmp_path: Path):
    forged = tmp_path / "forged.json"
    forged.write_text(
        '{"title": "Forged", "type": "other", "sections": {"summary": "x"},'
        ' "ixbrl_validated": true, "ixbrl_issues": []}',
        encoding="utf-8",
    )
    whitepaper = load_whitepaper(forged)
    assert whitepaper.metadata["ixbrl_validated"] is False
    assert _ixbrl_finding(forged).status == "missing"


def test_draft_format_still_receives_content_findings():
    """The format blocker must not suppress the rest of the analysis."""
    whitepaper = load_whitepaper(EXAMPLES / "art-stablecoin.json")
    findings = Linter(RULESETS[whitepaper.type]).lint(whitepaper)
    non_format = [f for f in findings if f.rule.rule_id != "COMMON.IXBRL_TAGGING"]
    assert len(non_format) > 5
    assert any(f.status == "pass" for f in non_format)
