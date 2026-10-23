"""A placeholder is not an answer. "TBD", "TBA", "[●]", "[...]", "[insert date]", "XX", "to be confirmed",
"noch offen" and the like as the whole content of a numbered field or a section read as missing, not as a
thin answer under review."""

from pathlib import Path

import pytest

from micar_linter.linter import lint_whitepaper
from micar_linter.numbered_fields import extract_numbered_fields
from micar_linter.whitepaper import Whitepaper, WhitepaperType, load_whitepaper

PLACEHOLDERS = [
    "TBD",
    "TBC",
    "[●]",
    "[•]",
    "to be confirmed",
    "To be determined.",
    "tbd.",
    "TBA",
    "t.b.d.",
    "T.B.C.",
    "to be announced",
    "To be advised.",
    "to be provided",
    "[...]",
    "[…]",
    "[insert date]",
    "[Insert name of the issuer]",
    "[XX]",
    "XX",
    "noch offen",
    "Folgt.",
    "wird nachgereicht",
    "N.N.",
]


def _numbered_draft(
    tmp_path: Path, risk_answer: str, second_risk_answer: str | None = None, language: str = "English"
) -> Path:
    """A numbered-field draft for an invented issuer whose Part I risk fields hold the given answers."""
    rows = "".join(
        f"<tr><td>{number}</td><td>{label}</td><td>{content}</td></tr>"
        for number, label, content in [
            ("A.1", "Name", "Quillmoor Ledger S.A."),
            ("D.1", "Crypto-asset project name", "Quillmoor shared ledger"),
            ("F.12", "Language or languages of the crypto-asset white paper", language),
            ("H.1", "Distributed ledger technology", "A permissioned ledger run by five validating nodes."),
            ("I.1", "Offer-related risks", risk_answer),
            (
                "I.2",
                "Technology-related risks",
                risk_answer if second_risk_answer is None else second_risk_answer,
            ),
        ]
    )
    path = tmp_path / "quillmoor.xhtml"
    path.write_text(f"<html><body><table>{rows}</table></body></html>", encoding="utf-8")
    return path


@pytest.mark.parametrize("placeholder", PLACEHOLDERS)
def test_a_numbered_field_holding_a_placeholder_is_unanswered(tmp_path: Path, placeholder: str):
    path = _numbered_draft(tmp_path, placeholder)

    fields = {field.field_id: field for field in extract_numbered_fields(path)}
    assert fields["A.1"].answered
    assert not fields["I.1"].answered
    assert not fields["I.2"].answered

    report = lint_whitepaper(load_whitepaper(path, WhitepaperType.OTHER))
    risks = next(finding for finding in report.findings if finding.rule.rule_id == "ANNEX_I.I")
    assert risks.status == "missing"
    # A placeholder is not a statement that the part does not apply.
    assert not any(warning.startswith("Part I:") for warning in report.warnings)


@pytest.mark.parametrize("text", [*PLACEHOLDERS, "TBD\nTBC", "[TBD]"])
def test_a_section_of_placeholders_is_missing(text: str):
    whitepaper = Whitepaper(
        title="Quillmoor draft", type=WhitepaperType.OTHER, sections={"notification_date": text}, metadata={}
    )
    report = lint_whitepaper(whitepaper)
    finding = next(f for f in report.findings if f.rule.rule_id == "COMMON.NOTIFICATION_DATE")
    assert (finding.status, finding.word_count) == ("missing", 0)


@pytest.mark.parametrize(
    "text",
    [
        "Date of notification: 2 March 2026.",
        "Date of notification: TBD",
        "N/A",
        "The launch date is to be confirmed by the board in 2026.",
        "2 March 2026",
        "English",
        "TBC Freight Lines",
        "XXL Logistics GmbH",
        "Folgt der Satzung der Quillmoor Ledger S.A.",
        "Wird nachgereicht bis 2 March 2026.",
    ],
)
def test_text_around_a_placeholder_is_not_a_placeholder(text: str):
    whitepaper = Whitepaper(
        title="Quillmoor draft", type=WhitepaperType.OTHER, sections={"notification_date": text}, metadata={}
    )
    finding = next(
        f for f in lint_whitepaper(whitepaper).findings if f.rule.rule_id == "COMMON.NOTIFICATION_DATE"
    )
    assert finding.status != "missing"


@pytest.mark.parametrize("answers", [("TBD", "N/A"), ("[●]", "-"), ("N/A", "to be confirmed")])
def test_a_part_of_placeholders_and_not_applicable_fields_is_missing(
    tmp_path: Path, answers: tuple[str, str]
):
    report = lint_whitepaper(load_whitepaper(_numbered_draft(tmp_path, *answers), WhitepaperType.OTHER))

    risks = next(finding for finding in report.findings if finding.rule.rule_id == "ANNEX_I.I")
    assert (risks.status, risks.word_count) == ("missing", 0)
    assert risks.issues == ("Section holds only placeholder text such as TBD or TBC.",)
    assert not any(warning.startswith("Part I:") for warning in report.warnings)


def test_a_placeholder_language_field_reports_the_placeholder(tmp_path: Path):
    path = _numbered_draft(tmp_path, "Holders may lose the full amount.", language="TBD")
    report = lint_whitepaper(load_whitepaper(path, WhitepaperType.OTHER))

    language = next(finding for finding in report.findings if finding.rule.rule_id == "COMMON.LANGUAGE")
    assert (language.status, language.issues) == (
        "missing",
        ("Section holds only placeholder text such as TBD or TBC.",),
    )
    # The field is there but unanswered, so the layout is not blamed.
    assert not any(
        "language check reports Missing because of the layout" in warning for warning in report.warnings
    )
