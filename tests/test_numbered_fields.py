"""White papers in the numbered-field layout of Implementing Regulation (EU) 2024/2984."""

from pathlib import Path

import pytest

from micar_linter.cli import main
from micar_linter.linter import lint_whitepaper
from micar_linter.numbered_fields import MERGED_LABELS_NOTE, extract_numbered_fields, is_numbered_layout
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


def _emt_table(tmp_path: Path, rows: list[tuple[str, ...]]) -> Path:
    cells = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    return _write(tmp_path, f"<table>{cells}</table>")


_EMT_BASE = [
    ("I.01", "Date of notification", "2026-03-02"),
    ("A.1", "Statutory name", "Example E-Money Institution SAS"),
    ("C.1", "Public offering or admission to trading", "Offer to the public."),
    ("F.1", "Risks", "Holders bear the risk of a failure of the issuer."),
]


def test_language_field_whose_label_shares_the_answer_cell(tmp_path: Path):
    # Some white papers set "B.11" in one cell and the label with its answer in the next.
    path = _emt_table(tmp_path, [*_EMT_BASE, ("B.11", "Language or languages of the white paper English")])
    whitepaper = load_whitepaper(path, WhitepaperType.EMT)
    assert whitepaper.section("language").endswith("English")
    report = lint_whitepaper(whitepaper)
    assert not any("labelled as the language" in warning for warning in report.warnings)


def test_unlabelled_field_mentioning_a_language_is_not_the_language_field(tmp_path: Path):
    path = _emt_table(
        tmp_path, [*_EMT_BASE, ("E.1", "Smart contracts are written in a programming language.")]
    )
    assert "language" not in load_whitepaper(path, WhitepaperType.EMT).sections


def test_emt_safeguarding_reads_the_fields_that_describe_it(tmp_path: Path):
    funds = (
        "Funds received in exchange for the tokens are safeguarded in segregated accounts "
        "at a credit institution, protected in the insolvency of the issuer."
    )
    path = _emt_table(tmp_path, [*_EMT_BASE, ("D.3", "Rights of holders", funds)])
    whitepaper = load_whitepaper(path, WhitepaperType.EMT)
    assert "segregated accounts" in whitepaper.section("safeguarding")
    report = lint_whitepaper(whitepaper)
    finding = next(f for f in report.findings if f.rule.rule_id == "ANNEX_III.SAFEGUARDING")
    assert finding.status != "missing"
    assert any(warning.endswith("mention it: D.3.") for warning in report.warnings)


def test_emt_safeguarding_stays_missing_when_no_field_describes_it(tmp_path: Path):
    whitepaper = load_whitepaper(_emt_table(tmp_path, _EMT_BASE), WhitepaperType.EMT)
    assert "safeguarding" not in whitepaper.sections
    report = lint_whitepaper(whitepaper)
    finding = next(f for f in report.findings if f.rule.rule_id == "ANNEX_III.SAFEGUARDING")
    assert finding.status == "missing"
    assert any("no answered field mentions safeguarding" in warning for warning in report.warnings)


def test_labels_that_run_into_the_answers_are_reported(tmp_path: Path):
    # A rendering converted from PDF puts each field number in its own text run, so the label joins the answer.
    rows = "".join(
        f"<div><span>{part}.{number}</span></div><div><span>Field {part}{number} label "
        f"{'N/A' if part == 'C' else 'answer for the fictional issuer'}</span></div>"
        for part in "ABCDE"
        for number in range(1, 5)
    )
    whitepaper = load_whitepaper(_write(tmp_path, rows), WhitepaperType.OTHER)

    assert whitepaper.metadata["extraction_notes"][0] == MERGED_LABELS_NOTE
    # The risk the note names: the "N/A" field reads as answered, label included.
    assert "Field C1 label N/A" in whitepaper.sections["trading_platform_operator"]


def test_fields_with_their_own_label_raise_no_merged_label_note():
    whitepaper = load_whitepaper(SAMPLE, WhitepaperType.OTHER)
    assert MERGED_LABELS_NOTE not in whitepaper.metadata["extraction_notes"]


def test_merged_label_note_needs_four_in_five_unlabelled_fields(tmp_path: Path):
    # Eleven of fourteen lettered fields keep the label in the answer cell: just under four in five.
    path = _emt_table(tmp_path, [*_EMT_BASE, *((f"B.{n}", f"Field B{n} label N/A") for n in range(1, 12))])
    whitepaper = load_whitepaper(path, WhitepaperType.EMT)
    assert MERGED_LABELS_NOTE not in whitepaper.metadata["extraction_notes"]


def test_label_sharing_the_answer_cell_raises_the_merged_label_note(tmp_path: Path):
    # Twelve of fifteen lettered fields keep the label in the answer cell.
    path = _emt_table(tmp_path, [*_EMT_BASE, *((f"B.{n}", f"Field B{n} label N/A") for n in range(1, 13))])
    whitepaper = load_whitepaper(path, WhitepaperType.EMT)
    assert whitepaper.metadata["extraction_notes"][0] == MERGED_LABELS_NOTE


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
