"""The first-page statement that no competent authority has approved the white paper.

The English fixture text is the statement as Art. 6(3) and Art. 51(3) MiCAR word it,
and as Table 2 field 02 and Table 4 field I.02 of the Annex to Implementing Regulation
(EU) 2024/2984 print it ("Predefined alphanumerical text"). Source read: the EUR-Lex
texts CELEX 32023R1114 and 32024R2984 as mirrored in legalize-dev/legalize-eu. Art. 19 MiCAR
prescribes no such statement for an ART white paper (Table 3 field I.02 of 2024/2984
holds the Art. 19(4) warning instead), so the ART ruleset carries no such rule. That is
not because every ART white paper is approved: that of an authorised issuer is deemed
approved (Art. 21(1)) and that of a credit institution is approved (Art. 17(1)(a)), but an
issuer exempt under Art. 16(2) only notifies it.

The German wording has not been checked against the German Official Journal text. German
drafts are therefore referred to review and never pass; the German sentence below is only
a routing fixture, not a statement of the statutory wording.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import docx
import pytest

from micar_linter.linter import Linter, lint_whitepaper
from micar_linter.rules import RULESETS
from micar_linter.rules.base import Severity
from micar_linter.whitepaper import Whitepaper, WhitepaperType, load_whitepaper

ROOT = Path(__file__).resolve().parents[1]
TITLE_II = "ANNEX_I.NOT_APPROVED_STATEMENT"
EMT = "ANNEX_III.NOT_APPROVED_STATEMENT"

APPROVAL = (
    "This crypto-asset white paper has not been approved by any competent authority "
    "in any Member State of the European Union."
)


def _statement(subject: str) -> str:
    return (
        f"{APPROVAL} {subject} of the crypto-asset is solely responsible for the content "
        "of this crypto-asset white paper."
    )


def _finding(wp_type: WhitepaperType, rule_id: str, sections: dict[str, str], **metadata):
    whitepaper = Whitepaper(title="Statement test", type=wp_type, sections=sections, metadata=metadata)
    for finding in Linter(RULESETS[wp_type]).lint(whitepaper):
        if finding.rule.rule_id == rule_id:
            return finding
    raise AssertionError(f"{rule_id} was not applied")


@pytest.mark.parametrize(
    "subject",
    ["The offeror", "The person seeking admission to trading", "The operator of the trading platform"],
)
def test_title_ii_statement_passes_for_each_person_art_6_3_names(subject: str):
    finding = _finding(WhitepaperType.OTHER, TITLE_II, {"not_approved_statement": _statement(subject)})
    assert finding.status == "pass", finding.issues
    assert finding.rule.citation == "Art. 6 Abs. 3 MiCAR"


def test_emt_statement_passes_when_it_names_the_issuer():
    finding = _finding(WhitepaperType.EMT, EMT, {"not_approved_statement": _statement("The issuer")})
    assert finding.status == "pass", finding.issues
    assert finding.rule.citation == "Art. 51 Abs. 3 MiCAR"


def test_emt_statement_naming_the_offeror_is_referred_to_review():
    finding = _finding(WhitepaperType.EMT, EMT, {"not_approved_statement": _statement("The offeror")})
    assert finding.status == "review"
    assert any("the issuer of the crypto-asset is solely responsible" in issue for issue in finding.issues)


@pytest.mark.parametrize("wp_type, rule_id", [(WhitepaperType.OTHER, TITLE_II), (WhitepaperType.EMT, EMT)])
def test_absent_statement_fails_closed_as_a_blocker(wp_type: WhitepaperType, rule_id: str):
    finding = _finding(wp_type, rule_id, {"summary": "A summary without the statement."})
    assert finding.status == "missing"
    assert finding.rule.severity is Severity.BLOCKER


@pytest.mark.parametrize("wp_type, rule_id", [(WhitepaperType.OTHER, TITLE_II), (WhitepaperType.EMT, EMT)])
def test_paraphrased_statement_is_referred_to_review(wp_type: WhitepaperType, rule_id: str):
    paraphrase = (
        "No supervisor has reviewed this document. The issuer of the crypto-asset is solely "
        "responsible for the content of this crypto-asset white paper."
    )
    finding = _finding(wp_type, rule_id, {"not_approved_statement": paraphrase})
    assert finding.status == "review"
    assert any("has not been approved by any competent authority" in issue for issue in finding.issues)


def test_art_ruleset_has_no_not_approved_statement():
    art_rules = {rule.rule_id for rule in RULESETS[WhitepaperType.ART]}
    assert not {rule_id for rule_id in art_rules if rule_id.endswith("NOT_APPROVED_STATEMENT")}
    assert TITLE_II in {rule.rule_id for rule in RULESETS[WhitepaperType.OTHER]}
    assert EMT in {rule.rule_id for rule in RULESETS[WhitepaperType.EMT]}


GERMAN_ROUTING_FIXTURE = (
    "Dieses Kryptowerte-Whitepaper wurde von keiner zuständigen Behörde eines Mitgliedstaats "
    "der Europäischen Union genehmigt. Der Anbieter des Kryptowerts trägt die alleinige "
    "Verantwortung für den Inhalt dieses Kryptowerte-Whitepapers."
)


@pytest.mark.parametrize("wp_type, rule_id", [(WhitepaperType.OTHER, TITLE_II), (WhitepaperType.EMT, EMT)])
def test_german_statement_is_referred_to_review_until_the_wording_is_verified(
    wp_type: WhitepaperType, rule_id: str
):
    finding = _finding(wp_type, rule_id, {"not_approved_statement": GERMAN_ROUTING_FIXTURE}, language="de")
    assert finding.status == "review"
    assert finding.rule.severity is Severity.BLOCKER
    assert any("nicht gegen die deutsche Fassung im Amtsblatt geprüft" in issue for issue in finding.issues)


def test_absent_german_statement_still_fails_closed():
    finding = _finding(WhitepaperType.OTHER, TITLE_II, {"summary": "Zusammenfassung."}, language="de")
    assert finding.status == "missing"


@pytest.mark.parametrize("value", ["true", "TRUE", "false", "Yes"])
def test_a_yes_no_field_value_is_not_read_as_the_statement(value: str):
    finding = _finding(WhitepaperType.EMT, EMT, {"not_approved_statement": value})
    assert finding.status == "review"
    assert any("yes/no value" in issue for issue in finding.issues)


def test_rule_labels_say_that_page_placement_is_not_checked():
    for wp_type, rule_id in [(WhitepaperType.OTHER, TITLE_II), (WhitepaperType.EMT, EMT)]:
        rule = next(r for r in RULESETS[wp_type] if r.rule_id == rule_id)
        assert "first-page placement not checked" in rule.label


@pytest.mark.parametrize("filename", ["other-crypto-asset.json", "emt-token.json"])
def test_canonical_examples_carry_the_statement(filename: str):
    report = lint_whitepaper(load_whitepaper(ROOT / "examples" / filename))
    statement = next(f for f in report.findings if f.rule.rule_id.endswith("NOT_APPROVED_STATEMENT"))
    assert statement.status == "pass", statement.issues


def test_numbered_field_02_feeds_the_title_ii_check():
    whitepaper = load_whitepaper(ROOT / "examples" / "numbered-other-draft.xhtml", WhitepaperType.OTHER)
    assert whitepaper.section("not_approved_statement").startswith(
        "Statement in accordance with Article 6(3) of Regulation (EU) 2023/1114:"
    )
    report = lint_whitepaper(whitepaper)
    statement = next(f for f in report.findings if f.rule.rule_id == TITLE_II)
    assert statement.status == "pass", statement.issues


def test_numbered_field_i_02_feeds_the_emt_check(tmp_path: Path):
    rows = "".join(
        f"<tr><td>{number}</td><td>{label}</td><td>{content}</td></tr>"
        for number, label, content in [
            ("I.01", "Date of notification", "2026-03-02"),
            (
                "I.02",
                "Statement in accordance with Article 51(3) of Regulation (EU) 2023/1114",
                _statement("The issuer"),
            ),
            ("A.1", "Statutory name", "Example EMI GmbH"),
            ("B.1", "Name of the e-money token", "Example EUR"),
            ("D.1", "Holder's rights and obligations", "Redemption at any time and at par value."),
        ]
    )
    path = tmp_path / "emt.xhtml"
    path.write_text(f"<html><body><table>{rows}</table></body></html>", encoding="utf-8")
    whitepaper = load_whitepaper(path, WhitepaperType.EMT)
    assert APPROVAL in whitepaper.section("not_approved_statement")
    statement = next(f for f in lint_whitepaper(whitepaper).findings if f.rule.rule_id == EMT)
    assert statement.status == "pass", statement.issues


def test_numbered_art_field_i_02_stays_the_risk_warning(tmp_path: Path):
    rows = "".join(
        f"<tr><td>{number}</td><td>{label}</td><td>{content}</td></tr>"
        for number, label, content in [
            ("I.02", "Statement in accordance with Article 19(4)", "The token may lose its value."),
            ("A.1", "Statutory name", "Example Issuer AG"),
            ("B.1", "Name", "Example ART"),
            ("G.1", "Description of the reserve of assets", "Bank deposits."),
        ]
    )
    path = tmp_path / "art.xhtml"
    path.write_text(f"<html><body><table>{rows}</table></body></html>", encoding="utf-8")
    whitepaper = load_whitepaper(path, WhitepaperType.ART)
    assert "not_approved_statement" not in whitepaper.sections
    assert "may lose its value" in whitepaper.section("risk_warning")


def test_statement_heading_routes_prose_drafts(tmp_path: Path):
    path = tmp_path / "draft.md"
    path.write_text(
        "# Statement in accordance with Article 6(3) of Regulation (EU) 2023/1114\n"
        f"{_statement('The offeror')}\n\n# Summary\nKey information.\n",
        encoding="utf-8",
    )
    whitepaper = load_whitepaper(path, WhitepaperType.OTHER)
    assert APPROVAL in whitepaper.section("not_approved_statement")
    assert "not been approved" not in whitepaper.section("summary")


# Regression: the loaders keep line breaks, and Art. 6(3) gives the statement no heading.
WRAPPED_STATEMENT = """This crypto-asset white paper has not been approved by any competent
authority in any Member State of the European Union. The offeror of the crypto-asset
is solely responsible for the content of this crypto-asset white paper."""


def _statement_from_markdown(tmp_path: Path, content: str) -> str:
    path = tmp_path / "draft.md"
    path.write_text(content, encoding="utf-8")
    whitepaper = load_whitepaper(path, WhitepaperType.OTHER)
    statement = next(f for f in lint_whitepaper(whitepaper).findings if f.rule.rule_id == TITLE_II)
    return statement


def test_hard_wrapped_markdown_statement_passes(tmp_path: Path):
    content = (
        "# Statement in accordance with Article 6(3) of Regulation (EU) 2023/1114\n"
        f"{WRAPPED_STATEMENT}\n\n# Summary\nKey information.\n"
    )
    statement = _statement_from_markdown(tmp_path, content)
    assert statement.status == "pass", statement.issues


def test_heading_less_first_paragraph_is_routed_to_the_statement(tmp_path: Path):
    content = f"{WRAPPED_STATEMENT}\n\n# Summary\nKey information about the offer.\n"
    statement = _statement_from_markdown(tmp_path, content)
    assert statement.status == "pass", statement.issues


def test_statement_under_an_unrelated_heading_is_routed_by_content(tmp_path: Path):
    content = f"# Important notice\n{WRAPPED_STATEMENT}\n\n# Summary\nKey information.\n"
    statement = _statement_from_markdown(tmp_path, content)
    assert statement.status == "pass", statement.issues


@pytest.mark.parametrize(
    "heading",
    [
        "Statement in accordance with Art. 6(3) of Regulation (EU) 2023/1114",
        "Erklärung gemäß Artikel 6 Absatz 3 der Verordnung (EU) 2023/1114",
    ],
)
def test_abbreviated_and_german_headings_route_to_the_statement(tmp_path: Path, heading: str):
    path = tmp_path / "draft.md"
    path.write_text(f"# {heading}\nStatement text.\n", encoding="utf-8")
    whitepaper = load_whitepaper(path, WhitepaperType.OTHER)
    assert whitepaper.section("not_approved_statement") == "Statement text."


def test_german_first_paragraph_is_routed_and_referred_to_review(tmp_path: Path):
    path = tmp_path / "entwurf.md"
    path.write_text(
        f"{GERMAN_ROUTING_FIXTURE}\n\n# Zusammenfassung\nDie wesentlichen Informationen.\n", encoding="utf-8"
    )
    whitepaper = load_whitepaper(path, WhitepaperType.OTHER)
    statement = next(f for f in lint_whitepaper(whitepaper).findings if f.rule.rule_id == TITLE_II)
    assert statement.status == "review"
    assert statement.word_count > 0


@patch("pypdf.PdfReader")
def test_wrapped_pdf_statement_passes(mock_reader_cls, tmp_path: Path):
    # The continuation lines contain "crypto-asset" and "offeror", which the PDF heading
    # heuristic would otherwise read as new section headings.
    page = MagicMock()
    page.extract_text.return_value = (
        "Example Token White Paper\n"
        "This crypto-asset white paper has not been approved by any competent authority in any\n"
        "Member State of the European Union. The offeror of the crypto-asset is solely\n"
        "responsible for the content of this crypto-\n"
        "asset white paper.\n"
        "Summary\n"
        "Key information about the offer.\n"
    )
    mock_reader_cls.return_value = MagicMock(pages=[page])
    path = tmp_path / "draft.pdf"
    path.write_bytes(b"%PDF-1.4")
    whitepaper = load_whitepaper(path, WhitepaperType.OTHER)
    statement = next(f for f in lint_whitepaper(whitepaper).findings if f.rule.rule_id == TITLE_II)
    assert statement.status == "pass", statement.issues
    assert "not been approved" not in whitepaper.section("summary")


def test_docx_statement_paragraph_without_heading_passes(tmp_path: Path):
    path = tmp_path / "draft.docx"
    document = docx.Document()
    document.add_paragraph(_statement("The offeror"))
    document.add_heading("Summary", level=1)
    document.add_paragraph("Key information about the offer.")
    document.save(path)
    whitepaper = load_whitepaper(path, WhitepaperType.OTHER)
    statement = next(f for f in lint_whitepaper(whitepaper).findings if f.rule.rule_id == TITLE_II)
    assert statement.status == "pass", statement.issues


def test_xhtml_statement_paragraph_without_heading_is_routed(tmp_path: Path):
    path = tmp_path / "draft.xhtml"
    path.write_text(
        "<html><body><p>"
        + _statement("The offeror")
        + "</p><h1>Summary</h1><p>Key information.</p></body></html>",
        encoding="utf-8",
    )
    whitepaper = load_whitepaper(path, WhitepaperType.OTHER)
    assert APPROVAL in whitepaper.section("not_approved_statement")
    assert "not been approved" not in whitepaper.section("summary")


# Regression: an incomplete statement swallowed the sections that followed it, so a draft
# that has a summary and a risk warning got MISSING blockers for both.
SUMMARY_BODY = " ".join(["The summary gives key information about the offer and the token."] * 15)
RISK_BODY = "The crypto-asset may lose its value in part or in full."


def _sections_after_incomplete_statement(whitepaper):
    findings = {f.rule.rule_id: f for f in lint_whitepaper(whitepaper).findings}
    assert findings["COMMON.SUMMARY"].status == "pass", findings["COMMON.SUMMARY"].issues
    assert findings["COMMON.RISK_WARNING"].status != "missing"
    assert findings[TITLE_II].status == "review"
    assert "key information" not in whitepaper.section("not_approved_statement")


def test_incomplete_docx_statement_does_not_swallow_the_next_sections(tmp_path: Path):
    path = tmp_path / "draft.docx"
    document = docx.Document()
    document.add_paragraph(APPROVAL)
    document.add_heading("Summary", level=1)
    document.add_paragraph(SUMMARY_BODY)
    document.add_heading("Risk warning", level=1)
    document.add_paragraph(RISK_BODY)
    document.save(path)
    _sections_after_incomplete_statement(load_whitepaper(path, WhitepaperType.OTHER))


def test_docx_heading_ends_the_statement_even_before_a_responsibility_sentence(tmp_path: Path):
    path = tmp_path / "draft.docx"
    document = docx.Document()
    document.add_paragraph(APPROVAL)
    document.add_heading("Summary", level=1)
    document.add_paragraph("The issuer is responsible for the token. " + SUMMARY_BODY)
    document.save(path)
    whitepaper = load_whitepaper(path, WhitepaperType.OTHER)
    assert whitepaper.section("not_approved_statement") == APPROVAL
    assert whitepaper.section("summary").startswith("Summary")


def test_incomplete_markdown_statement_does_not_swallow_the_next_sections(tmp_path: Path):
    path = tmp_path / "draft.md"
    path.write_text(
        f"{APPROVAL}\n\nSummary\n{SUMMARY_BODY}\n\n# Summary\n{SUMMARY_BODY}\n\n# Risk warning\n{RISK_BODY}\n",
        encoding="utf-8",
    )
    whitepaper = load_whitepaper(path, WhitepaperType.OTHER)
    assert whitepaper.section("not_approved_statement") == APPROVAL
    _sections_after_incomplete_statement(whitepaper)


def _pdf_whitepaper(mock_reader_cls, tmp_path: Path, text: str):
    page = MagicMock()
    page.extract_text.return_value = text
    mock_reader_cls.return_value = MagicMock(pages=[page])
    path = tmp_path / "draft.pdf"
    path.write_bytes(b"%PDF-1.4")
    return load_whitepaper(path, WhitepaperType.OTHER)


@patch("pypdf.PdfReader")
def test_incomplete_pdf_statement_does_not_swallow_the_next_sections(mock_reader_cls, tmp_path: Path):
    whitepaper = _pdf_whitepaper(
        mock_reader_cls,
        tmp_path,
        "This crypto-asset white paper has not been approved by any competent authority in any\n"
        "Member State of the European Union.\n"
        f"Summary\n{SUMMARY_BODY}\nRisk warning\n{RISK_BODY}\n",
    )
    _sections_after_incomplete_statement(whitepaper)


@patch("pypdf.PdfReader")
def test_pdf_statement_cut_off_mid_sentence_ends_at_the_heading(mock_reader_cls, tmp_path: Path):
    whitepaper = _pdf_whitepaper(
        mock_reader_cls,
        tmp_path,
        "This crypto-asset white paper has not been approved\n"
        f"Summary\n{SUMMARY_BODY}\nRisk warning\n{RISK_BODY}\n",
    )
    assert (
        whitepaper.section("not_approved_statement") == "This crypto-asset white paper has not been approved"
    )
    _sections_after_incomplete_statement(whitepaper)


@patch("pypdf.PdfReader")
def test_statement_wrapped_in_a_narrow_pdf_column_passes(mock_reader_cls, tmp_path: Path):
    # "State of the European Union. The offeror" and "of the crypto-asset is solely
    # responsible" are short and name sections, so a heading check alone would cut the
    # statement off.
    whitepaper = _pdf_whitepaper(
        mock_reader_cls,
        tmp_path,
        "This crypto-asset white paper has not been approved\n"
        "by any competent authority in any Member\n"
        "State of the European Union. The offeror\n"
        "of the crypto-asset is solely responsible\n"
        "for the content of this crypto-asset\n"
        "white paper.\n"
        f"Summary\n{SUMMARY_BODY}\n",
    )
    statement = next(f for f in lint_whitepaper(whitepaper).findings if f.rule.rule_id == TITLE_II)
    assert statement.status == "pass", statement.issues
    assert whitepaper.section("summary").startswith("Summary")
