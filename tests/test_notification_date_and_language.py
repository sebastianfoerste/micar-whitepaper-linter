"""COMMON.NOTIFICATION_DATE and COMMON.LANGUAGE check the answer itself: a calendar date and an official EU
language. Implementing Regulation (EU) 2024/2984 takes the date as YYYY-MM-DD and the language from a closed
list of EU languages, so a correct answer can be one word and a minimum length would hold it at Review."""

from pathlib import Path

import pytest

from micar_linter.document import match_heading_to_section
from micar_linter.linter import EU_LANGUAGES, has_calendar_date, lint_whitepaper, names_eu_language
from micar_linter.rules.base import Finding
from micar_linter.whitepaper import Whitepaper, WhitepaperType, load_whitepaper

ROOT = Path(__file__).resolve().parents[1]
NO_DATE = "No calendar date with day, month and year was found, for example 2026-03-02 or 2 March 2026."
NO_LANGUAGE = "No official EU language was found, for example English or German."


def _finding(rule_id: str, section: str, text: str, language: str = "en") -> Finding:
    whitepaper = Whitepaper(
        title="Quillmoor draft",
        type=WhitepaperType.OTHER,
        sections={section: text},
        metadata={"language": language},
    )
    return next(f for f in lint_whitepaper(whitepaper).findings if f.rule.rule_id == rule_id)


@pytest.mark.parametrize(
    "text",
    [
        "2026-03-02",
        "Date of notification: 2026-03-02",
        "2 February 2026",
        "2nd of March 2026",
        "2 Mar. 2026",
        "March 2, 2026",
        "02.03.2026",
        "2/3/2026",
        "03/31/2026",
        "2. März 2026",
        "Datum der Mitteilung: 1. Juli 2026",
        "The white paper was notified to the competent authority on 2 March 2026.",
    ],
)
def test_a_calendar_date_passes_however_short_the_section(text: str):
    finding = _finding("COMMON.NOTIFICATION_DATE", "notification_date", text)
    assert (finding.status, finding.issues) == ("pass", ())


@pytest.mark.parametrize(
    "text",
    [
        "N/A",
        "Date of notification: TBD",
        "Date of notification: to be inserted on notification.",
        "March 2026",
        "02.03.26",
        "31.02.2026",
        "2026-13-01",
        "v1.2.2026",
        "Synthetic fixture notification date placeholder for reviewer demo only.",
        # The unfilled starter template passed the former check of five words and the term "date".
        "REPLACE: Date of notification to the competent authority (Art. 8 Abs. 1 MiCAR).",
    ],
)
def test_text_without_a_calendar_date_is_under_review(text: str):
    finding = _finding("COMMON.NOTIFICATION_DATE", "notification_date", text)
    assert (finding.status, finding.issues) == ("review", (NO_DATE,))


@pytest.mark.parametrize(
    "text",
    [
        "English",
        "ENGLISH",
        "Language or languages of the crypto-asset white paper: English",
        "English, German",
        "Slovene",
        "This white paper is drawn up in English, a language customary in the sphere of international finance.",
        "Das Whitepaper ist in deutscher Sprache abgefasst.",
        "Sprache: Deutsch",
        "englischsprachig",
        "Franzoesisch",
    ],
)
def test_an_official_eu_language_passes_however_short_the_section(text: str):
    finding = _finding("COMMON.LANGUAGE", "language", text)
    assert (finding.status, finding.issues) == ("pass", ())


@pytest.mark.parametrize(
    "text",
    [
        "N/A",
        "EN",
        "Norwegian",
        "The issuer is incorporated in Germany.",
        "Sitz in Deutschland",
        "The drafting team will polish the text before notification.",
        "This white paper is drawn up in a language customary in the sphere of international finance.",
        "REPLACE: State the language of the white paper (official language of the home Member State).",
    ],
)
def test_text_naming_no_official_eu_language_is_under_review(text: str):
    finding = _finding("COMMON.LANGUAGE", "language", text)
    assert (finding.status, finding.issues) == ("review", (NO_LANGUAGE,))


@pytest.mark.parametrize("rule_id,section", [("COMMON.NOTIFICATION_DATE", "notification_date"), ("COMMON.LANGUAGE", "language")])
@pytest.mark.parametrize(
    "text,issue",
    [
        ("", "Section is empty or absent."),
        ("TBD", "Section holds only placeholder text such as TBD or TBC."),
        ("[●]", "Section holds only placeholder text such as TBD or TBC."),
    ],
)
def test_an_empty_or_placeholder_answer_is_missing(rule_id: str, section: str, text: str, issue: str):
    finding = _finding(rule_id, section, text)
    assert (finding.status, finding.word_count, finding.issues) == ("missing", 0, (issue,))


def test_german_drafts_get_german_issues():
    date = _finding("COMMON.NOTIFICATION_DATE", "notification_date", "Datum der Mitteilung: folgt bald", "de")
    language = _finding("COMMON.LANGUAGE", "language", "Sprache: siehe Teil F", "de")
    assert date.issues == ("Kein Kalenderdatum mit Tag, Monat und Jahr gefunden, etwa 2026-03-02 oder 2. März 2026.",)
    assert language.issues == ("Keine Amtssprache der EU gefunden, etwa Englisch oder Deutsch.",)


def test_every_official_language_counts_by_its_english_and_german_name():
    # Art. 1 of Council Regulation No 1 names 24 official languages of the Union.
    assert len(EU_LANGUAGES) == 24
    for english, german in EU_LANGUAGES:
        assert names_eu_language(english), english
        assert names_eu_language(german), german
        assert names_eu_language(f"in {german.lower()}er Sprache"), german


def test_recognisers_find_the_value_inside_a_sentence():
    assert has_calendar_date("Notified to BaFin on 1 July 2026, as stated on the cover page.")
    assert not has_calendar_date("Notified to BaFin in July 2026.")
    assert names_eu_language("Drawn up in Dutch and French.")
    assert not names_eu_language("Drawn up in Dutchman's prose.")


def _numbered(tmp_path: Path, date: str, language: str) -> Path:
    rows = [
        ("01", "Date of notification", date),
        ("A.1", "Name", "Quillmoor Ledger S.A."),
        ("B.1", "Name", "Quillmoor Ledger S.A."),
        ("F.12", "Language or languages of the crypto-asset white paper", language),
        ("I.1", "Risks", "Holders may lose the full amount."),
    ]
    cells = "".join(f"<tr><td>{number}</td><td>{label}</td><td>{answer}</td></tr>" for number, label, answer in rows)
    path = tmp_path / "draft.xhtml"
    path.write_text(f"<html><body><table>{cells}</table></body></html>", encoding="utf-8")
    return path


def _findings(path: Path) -> dict[str, Finding]:
    report = lint_whitepaper(load_whitepaper(path, WhitepaperType.OTHER))
    return {f.rule.rule_id: f for f in report.findings}


def test_numbered_example_answers_pass_both_checks():
    findings = _findings(ROOT / "examples" / "numbered-other-draft.xhtml")
    # "Date of notification: 2026-03-02" and "Language or languages of the crypto-asset white paper: English".
    assert (findings["COMMON.NOTIFICATION_DATE"].status, findings["COMMON.NOTIFICATION_DATE"].word_count) == ("pass", 4)
    assert (findings["COMMON.LANGUAGE"].status, findings["COMMON.LANGUAGE"].word_count) == ("pass", 9)


@pytest.mark.parametrize(
    "date,language,expected",
    [
        ("2026-03-02", "German", ("pass", "pass")),
        ("N/A", "English", ("review", "pass")),
        ("TBD", "TBD", ("missing", "missing")),
        ("2026-03-02", "N/A", ("pass", "missing")),
    ],
)
def test_numbered_fields_pass_only_with_an_answer(tmp_path: Path, date: str, language: str, expected: tuple[str, str]):
    findings = _findings(_numbered(tmp_path, date, language))
    assert (findings["COMMON.NOTIFICATION_DATE"].status, findings["COMMON.LANGUAGE"].status) == expected


@pytest.mark.parametrize("heading", ["Plain-Language Summary", "Summary in plain language", "PLAIN LANGUAGE SUMMARY"])
def test_a_plain_language_summary_heading_opens_only_the_summary(heading: str):
    assert match_heading_to_section(heading) == ["summary"]


@pytest.mark.parametrize("heading", ["Language", "Language of the white paper", "Sprache"])
def test_a_language_heading_still_opens_the_language_section(heading: str):
    assert match_heading_to_section(heading) == ["language"]


def test_the_language_check_reads_the_language_paragraph_and_not_the_summary():
    # sample-draft.docx opens with "Plain-Language Summary" and later has a "Language" heading.
    whitepaper = load_whitepaper(ROOT / "examples" / "sample-draft.docx", WhitepaperType.OTHER)
    assert whitepaper.section("language") == (
        "This white paper is drawn up in English, a language customary in international finance."
    )
    assert "summary" in whitepaper.sections
