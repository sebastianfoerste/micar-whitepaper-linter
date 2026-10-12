"""White papers in the numbered-field layout of Implementing Regulation (EU) 2024/2984."""

from pathlib import Path

import pytest

from micar_linter.cli import main
from micar_linter.linter import lint_whitepaper
from micar_linter.numbered_fields import extract_numbered_fields, is_numbered_layout
from micar_linter.whitepaper import WhitepaperType, load_whitepaper

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "examples" / "numbered-other-draft.xhtml"
# Public register documents fetched by the study scripts. Not committed, so these checks run only where the cache exists.
STUDY_CACHE = ROOT / ".study-cache" / "title-ii-whitepapers"


def _write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "draft.xhtml"
    path.write_text(f"<html><body>{body}</body></html>", encoding="utf-8")
    return path


def test_table_rows_map_to_the_sections_of_the_stated_regime():
    whitepaper = load_whitepaper(SAMPLE, WhitepaperType.OTHER)
    assert whitepaper.type is WhitepaperType.OTHER
    assert whitepaper.section("issuer").startswith("Issuer different from offeror")
    assert "Legal form: Limited liability company" in whitepaper.section("issuer")
    assert whitepaper.section("notification_date") == "Date of notification: 2026-03-02"
    assert "management body" in whitepaper.section("management_statement")
    assert whitepaper.section("language").endswith("white paper: English")
    assert set(whitepaper.sections) >= {"summary", "risk_warning", "project", "risks", "environmental_impact"}


def test_numbered_layout_requires_an_explicit_regime(capsys):
    # The template names every regime ("other than an asset-referenced token"), which misled the wording heuristic.
    with pytest.raises(SystemExit, match="State the regime explicitly"):
        load_whitepaper(SAMPLE)
    assert main([str(SAMPLE), "--type", "other", "--json"]) == 0
    assert '"whitepaper_type": "other"' in capsys.readouterr().out


def test_template_wording_cannot_satisfy_a_rule_for_unanswered_fields():
    report = lint_whitepaper(load_whitepaper(SAMPLE, WhitepaperType.OTHER))
    offeror = next(finding for finding in report.findings if finding.rule.rule_id == "ANNEX_I.A")
    assert offeror.status == "review"
    assert any("legal form" in issue for issue in offeror.issues)
    assert any(warning.startswith("Part A: all 3 numbered fields") for warning in report.warnings)


def test_inline_fields_split_without_following_cross_references(tmp_path: Path):
    path = _write(
        tmp_path,
        "<p>A.1 Name: N/A A.2 Legal form: N/A</p>"
        "<p>B.1 Name: Example AG B.2 Abbreviation: See F.14 B.3 Legal form: Stock corporation</p>"
        "<p><b>C.1 Name:</b> Example Exchange S.A.</p>",
    )
    fields = {field.field_id: field for field in extract_numbered_fields(path)}
    assert set(fields) == {"A.1", "A.2", "B.1", "B.2", "B.3", "C.1"}
    assert (fields["B.2"].label, fields["B.2"].content) == ("Abbreviation", "See F.14")
    assert fields["C.1"].content == "Example Exchange S.A."
    assert not fields["A.2"].answered
    assert is_numbered_layout(list(fields.values()))


def test_leading_fields_of_tables_3_and_4_do_not_collide_with_part_i(tmp_path: Path):
    rows = "".join(
        f"<tr><td>{number}</td><td>{label}</td><td>{content}</td></tr>"
        for number, label, content in [
            ("I.01", "Date of notification", "2026-03-02"),
            ("I.06", "Right of redemption", "Holders can redeem at par at any time."),
            ("A.1", "Statutory name", "Example Issuer AG"),
            ("B.14", "Language or languages of the crypto-asset white paper", "German"),
            ("D.1", "Holder's rights and obligations", "Redemption at market value of the reserve."),
            ("G.1", "Description of the reserve of assets", "Bank deposits and government bonds."),
        ]
    )
    whitepaper = load_whitepaper(_write(tmp_path, f"<table>{rows}</table>"), WhitepaperType.ART)
    assert whitepaper.section("notification_date") == "Date of notification: 2026-03-02"
    assert "risks" not in whitepaper.sections
    assert "redeem at par" in whitepaper.section("summary")
    assert "Bank deposits" in whitepaper.section("reserve_of_assets")
    for part in ("redeem at par", "market value of the reserve", "Bank deposits"):
        assert part in whitepaper.section("redemption")
    assert "German" in whitepaper.section("language")


def test_heading_structured_xhtml_keeps_the_heading_loader():
    whitepaper = load_whitepaper(ROOT / "examples" / "sample-draft.xhtml")
    assert whitepaper.type is WhitepaperType.EMT
    assert whitepaper.metadata["extraction_notes"] == ()


@pytest.mark.skipif(not STUDY_CACHE.is_dir(), reason="local study cache not present")
def test_public_title_ii_documents_yield_their_lettered_parts():
    numbered = 0
    for path in sorted(STUDY_CACHE.glob("*.*html")):
        if not is_numbered_layout(extract_numbered_fields(path)):
            continue
        numbered += 1
        with pytest.raises(SystemExit):
            load_whitepaper(path)
        report = lint_whitepaper(load_whitepaper(path, WhitepaperType.OTHER))
        missing = {finding.rule.rule_id for finding in report.missing}
        assert not missing & {f"ANNEX_I.{part}" for part in "ABCDEFGHI"}, path.name
    assert numbered >= 12
