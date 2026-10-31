"""COMMON.SUMMARY checks the predefined warning and the redemption statement of the summary.

The template of Implementing Regulation (EU) 2024/2984 gives the warning of Art. 6(7), 19(6) and 51(6) MiCAR,
second subparagraph, as predefined text of about 120 words (field 07 of Table 2, I.04 of Table 3, I.05 of
Table 4), so a summary of the warning and a line of key information met the minimum length (#70): the warning
does not count toward the 80 words. A summary without the warning's four points goes to review, as does an ART
or EMT summary without the statement of the right of redemption at any time (EMT: and at par value) of the third
subparagraph of Art. 19(6) and 51(6) (fields I.06 of Table 3 and I.07 of Table 4).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from micar_linter.linter import Linter, lint_whitepaper
from micar_linter.rules import RULESETS
from micar_linter.template_fields import FIELD_NAMES
from micar_linter.whitepaper import Whitepaper, WhitepaperType, load_whitepaper

OTHER = WhitepaperType.OTHER
ART = WhitepaperType.ART
EMT = WhitepaperType.EMT

# Field 07 of Table 2 as the Official Journal prints it, with an en dash in one "crypto-asset", one sentence per
# point (a) to (d) of Art. 6(7), second subparagraph.
POINTS_07 = (
    "This summary should be read as an introduction to the crypto-asset white paper.",
    "The prospective holder should base any decision to purchase this crypto \N{EN DASH}asset on the content of the "
    "crypto-asset white paper as a whole and not on the summary alone.",
    "The offer to the public of this crypto-asset does not constitute an offer or solicitation to purchase financial "
    "instruments and any such offer or solicitation can be made only by means of a prospectus or other offer documents "
    "pursuant to the applicable national law.",
    "This crypto-asset white paper does not constitute a prospectus as referred to in Regulation (EU) 2017/1129 of the "
    "European Parliament and of the Council or any other offer document pursuant to Union or national law.",
)
WARNING_07 = "Warning " + " ".join(POINTS_07)
WARNING_I04 = WARNING_07.replace("this crypto \N{EN DASH}asset on", "this asset-referenced token on")
WARNING_I05 = WARNING_07.replace("this crypto \N{EN DASH}asset on", "this e-money token on").replace(
    "instruments and any such", "instruments and that any such"
)
WARNUNG_07 = (
    "Warnhinweis: Diese Zusammenfassung ist als Einführung in das Kryptowerte-Whitepaper zu lesen. Der potenzielle "
    "Inhaber sollte jede Entscheidung über den Kauf des Kryptowerts auf der Grundlage des Inhalts des gesamten "
    "Kryptowerte-Whitepapers und nicht allein auf der Grundlage der Zusammenfassung treffen. Das öffentliche Angebot "
    "dieses Kryptowerts stellt kein Angebot und keine Aufforderung zum Kauf von Finanzinstrumenten dar und ein "
    "solches Angebot oder eine solche Aufforderung kann nur mittels eines Prospekts oder anderer im geltenden "
    "nationalen Recht vorgesehener Angebotsunterlagen erfolgen. Dieses Kryptowerte-Whitepaper stellt keinen Prospekt "
    "im Sinne der Verordnung (EU) 2017/1129 des Europäischen Parlaments und des Rates und kein anderes "
    "Angebotsdokument im Sinne von Unionsrecht oder nationalem Recht dar."
)
WARNUNG_I04 = WARNUNG_07.replace("über den Kauf des Kryptowerts", "über den Kauf dieses vermögenswertereferenzierten Token")
WARNUNG_I05 = WARNUNG_07.replace(
    "Der potenzielle Inhaber sollte jede Entscheidung über den Kauf des Kryptowerts",
    "Potenzielle Inhaber sollten ihre Entscheidung zum Kauf des E-Geld-Token",
).replace(
    "anderer im geltenden nationalen Recht vorgesehener Angebotsunterlagen",
    "anderer Angebotsunterlagen gemäß den nationalen Rechtsvorschriften",
)
KEY_INFORMATION = "The summary gives the key information: admission to trading on a fictional trading platform."
OWN_WORDS = (
    "The fictional token gives repeat buyers loyalty points that they redeem for garden supplies on the fictional "
    "marketplace of the offeror. "
)
WESENTLICHE_INFORMATIONEN = "Die Zusammenfassung enthält wesentliche Informationen über das Angebot."
EIGENE_WORTE = (
    "Der fiktive Token gibt wiederkehrenden Käufern Treuepunkte, die sie auf dem fiktiven Marktplatz des Anbieters "
    "gegen Gartenbedarf eintauschen. "
)
# The redemption statements of field I.06 of Table 3 and I.07 of Table 4, each with a line on the conditions.
REDEMPTION_ART = (
    "The holders of asset-referenced tokens have a right of redemption at any time. The conditions for redemption "
    "are set out in the redemption section."
)
REDEMPTION_EMT = (
    "The holders of this e-money token have a right of redemption at any time and at par value. The conditions for "
    "redemption are set out in the redemption section."
)
RÜCKTAUSCH_ART = (
    "Die Inhaber vermögenswertereferenzierter Token haben jederzeit ein Recht auf Rücktausch. Die Bedingungen für "
    "den Rücktausch nennt der Abschnitt zum Rücktausch."
)
RÜCKTAUSCH_EMT = (
    "Die Inhaber dieses E-Geld-Token haben jederzeit ein Recht auf Rücktausch zum Nennwert. Die Bedingungen für den "
    "Rücktausch nennt der Abschnitt zum Rücktausch."
)
# The issue lines, pinned: the report is the lawyer's reading of the check.
POINT_TAGS = (
    "point (a) introduction",
    "point (b) decision on the whole white paper",
    "point (c) no offer of financial instruments",
    "point (d) no prospectus",
)
ARTICLES = {OTHER: "Art. 6(7)", ART: "Art. 19(6)", EMT: "Art. 51(6)"}


def warning_issue(whitepaper_type: WhitepaperType, *points: str) -> str:
    return (
        f"Warning of {ARTICLES[whitepaper_type]} MiCAR, second subparagraph, not found in the template's wording: "
        + "; ".join(points or POINT_TAGS)
        + "."
    )


REDEMPTION_ISSUE_ART = (
    "Right of redemption at any time (Art. 19(6), third subparagraph, MiCAR) not found: no sentence names "
    "redemption together with 'at any time'."
)
REDEMPTION_ISSUE_EMT = (
    "Right of redemption at any time and at par value (Art. 51(6), third subparagraph, MiCAR) not found: no "
    "sentence names redemption together with 'at any time'."
)
PAR_VALUE_ISSUE_EMT = (
    "Right of redemption at any time and at par value (Art. 51(6), third subparagraph, MiCAR) not found: par value "
    "is not named."
)


def _summary(
    text: str,
    whitepaper_type: WhitepaperType = OTHER,
    language: str | None = None,
    fields: dict[str, str] | None = None,
):
    """The COMMON.SUMMARY finding for a summary section; `fields` makes the draft a numbered-field one."""
    rule = next(rule for rule in RULESETS[whitepaper_type] if rule.rule_id == "COMMON.SUMMARY")
    metadata: dict[str, object] = {"language": language} if language else {}
    if fields is not None:
        metadata["numbered_fields"] = fields
    whitepaper = Whitepaper(title="Synthetic", type=whitepaper_type, sections={"summary": text}, metadata=metadata)
    return Linter((rule,)).lint(whitepaper)[0]


# Three lettered parts with an answer, so that the loader takes the draft for the numbered-field layout.
LETTERED_ROWS = {
    OTHER: [("A.1", "Meadow Labs GmbH (fictional)"), ("D.1", "Meadow (fictional)"), ("E.1", "ATTR")],
    ART: [("A.1", "Synthetic Issuer AG (fictional)"), ("B.1", "Synthetic ART (fictional)"), ("C.1", "OTPL")],
    EMT: [("A.1", "Synthetic Issuer AG (fictional)"), ("B.1", "Synthetic EMT (fictional)"), ("C.1", "OTPL")],
}


def _numbered_draft(tmp_path: Path, whitepaper_type: WhitepaperType, rows: list[tuple[str, str]]) -> Path:
    names = FIELD_NAMES[whitepaper_type]
    rows = [*rows, *LETTERED_ROWS[whitepaper_type]]
    cells = "".join(f"<tr><td>{number}</td><td>{names.get(number, '')}</td><td>{text}</td></tr>" for number, text in rows)
    path = tmp_path / "draft.xhtml"
    path.write_text(f"<html><body><table>{cells}</table></body></html>", encoding="utf-8")
    return path


def _summary_of(path: Path, whitepaper_type: WhitepaperType):
    report = lint_whitepaper(load_whitepaper(path, whitepaper_type))
    return next(f for f in report.findings if f.rule.rule_id == "COMMON.SUMMARY")


def test_the_issue_reproduction_goes_to_review(tmp_path: Path):
    names = FIELD_NAMES[OTHER]
    rows = [
        ("07", WARNING_07),
        ("08", "TBD"),
        ("10", "Admission to trading on a fictional trading platform."),
        ("A.1", "Meadow Labs GmbH (fictional)"),
        ("D.1", "Meadow (fictional)"),
        ("E.1", "ATTR"),
    ]
    cells = "".join(f"<tr><td>{number}</td><td>{names.get(number, '')}</td><td>{text}</td></tr>" for number, text in rows)
    path = tmp_path / "draft.xhtml"
    path.write_text(f"<html><body><table>{cells}</table></body></html>", encoding="utf-8")
    finding = next(f for f in lint_whitepaper(load_whitepaper(path, OTHER)).findings if f.rule.rule_id == "COMMON.SUMMARY")
    assert finding.status == "review"
    # Field 07 leaves out its label too: "TBD" and the line of field 10 remain.
    assert "Section is thin: 21 words besides the predefined warning, expected at least 80." in finding.issues
    # The report still gives the section's own length.
    assert finding.word_count > 150


def test_a_numbered_summary_passes_on_its_own_words(tmp_path: Path):
    names = FIELD_NAMES[OTHER]
    rows = [
        ("07", WARNING_07),
        ("08", OWN_WORDS * 4),
        ("10", "Admission to trading on a fictional trading platform."),
        ("A.1", "Meadow Labs GmbH (fictional)"),
        ("D.1", "Meadow (fictional)"),
        ("E.1", "ATTR"),
    ]
    cells = "".join(f"<tr><td>{number}</td><td>{names.get(number, '')}</td><td>{text}</td></tr>" for number, text in rows)
    path = tmp_path / "draft.xhtml"
    path.write_text(f"<html><body><table>{cells}</table></body></html>", encoding="utf-8")
    finding = next(f for f in lint_whitepaper(load_whitepaper(path, OTHER)).findings if f.rule.rule_id == "COMMON.SUMMARY")
    assert finding.status == "pass", finding.issues


@pytest.mark.parametrize(
    ("whitepaper_type", "warning", "redemption"),
    [(OTHER, WARNING_07, ""), (ART, WARNING_I04, REDEMPTION_ART), (EMT, WARNING_I05, REDEMPTION_EMT)],
)
def test_the_template_warning_does_not_count(whitepaper_type: WhitepaperType, warning: str, redemption: str):
    # The redemption statement counts like any other sentence; only the warning is left out.
    finding = _summary(f"{warning} {KEY_INFORMATION} {redemption}", whitepaper_type)
    assert finding.status == "review"
    counted = 14 + len(redemption.split())
    assert finding.issues == (
        f"Section is thin: {counted} words besides the predefined warning, expected at least 80.",
    )
    assert _summary(f"{warning} {KEY_INFORMATION} {OWN_WORDS * 5} {redemption}", whitepaper_type).status == "pass"


@pytest.mark.parametrize(
    ("whitepaper_type", "warning"), [(OTHER, WARNUNG_07), (ART, WARNUNG_I04), (EMT, WARNUNG_I05)]
)
def test_the_german_template_warning_does_not_count(whitepaper_type: WhitepaperType, warning: str):
    text = f"{warning} Die Zusammenfassung enthält die wesentlichen Informationen über das Angebot."
    finding = _summary(text, whitepaper_type, language="de")
    assert finding.status == "review"
    assert "Abschnitt ist zu kurz: 9 Wörter ohne den vorgegebenen Warnhinweis, mindestens 80 erwartet." in (
        finding.issues
    )


def test_the_warning_still_names_the_summary():
    # The listed term "summary" may come from the warning itself; only the length leaves it out.
    text = WARNING_07 + " " + "Key information: " + OWN_WORDS * 5
    assert _summary(text).status == "pass"


def test_a_warning_in_other_words_still_counts():
    # The paraphrase counts toward the length, and the warning is reported as not found in the template's wording.
    paraphrase = (
        "Read this summary only as an introduction to the white paper, and base any purchase on the white paper as "
        "a whole. Nothing here offers financial instruments, and the white paper is no prospectus."
    )
    finding = _summary(f"{paraphrase} {KEY_INFORMATION}")
    assert finding.issues == ("Section is thin: 48 words, expected at least 80.", warning_issue(OTHER))
    assert _summary(f"{paraphrase} {KEY_INFORMATION} {OWN_WORDS * 5}").issues == (warning_issue(OTHER),)


def test_a_summary_without_the_warning_keeps_its_message():
    finding = _summary(KEY_INFORMATION)
    assert finding.status == "review"
    assert finding.issues == ("Section is thin: 14 words, expected at least 80.", warning_issue(OTHER))


# The warning of Art. 6(7), 19(6) and 51(6) MiCAR, second subparagraph, points (a) to (d).


@pytest.mark.parametrize(
    ("whitepaper_type", "warning", "redemption"),
    [(OTHER, WARNING_07, ""), (ART, WARNING_I04, REDEMPTION_ART), (EMT, WARNING_I05, REDEMPTION_EMT)],
)
def test_the_template_warning_and_the_redemption_statement_pass(
    whitepaper_type: WhitepaperType, warning: str, redemption: str
):
    finding = _summary(f"{warning} {KEY_INFORMATION} {OWN_WORDS * 5} {redemption}", whitepaper_type)
    assert finding.status == "pass", finding.issues
    assert finding.issues == ()


@pytest.mark.parametrize(
    ("whitepaper_type", "warnung", "rücktausch"),
    [(OTHER, WARNUNG_07, ""), (ART, WARNUNG_I04, RÜCKTAUSCH_ART), (EMT, WARNUNG_I05, RÜCKTAUSCH_EMT)],
)
def test_the_german_template_warning_and_redemption_statement_pass(
    whitepaper_type: WhitepaperType, warnung: str, rücktausch: str
):
    text = f"{warnung} {WESENTLICHE_INFORMATIONEN} {EIGENE_WORTE * 5} {rücktausch}"
    finding = _summary(text, whitepaper_type, language="de")
    assert finding.status == "pass", finding.issues


def test_the_english_warning_passes_in_a_german_draft():
    # Either language's template wording counts, whatever the draft's language.
    text = f"{WARNING_07} {WESENTLICHE_INFORMATIONEN} {EIGENE_WORTE * 5}"
    assert _summary(text, language="de").status == "pass"


@pytest.mark.parametrize(("index", "tag"), list(enumerate(POINT_TAGS)))
def test_each_missing_point_is_named(index: int, tag: str):
    points = [point for position, point in enumerate(POINTS_07) if position != index]
    finding = _summary(f"Warning {' '.join(points)} {KEY_INFORMATION} {OWN_WORDS * 5}")
    assert finding.status == "review"
    assert finding.issues == (warning_issue(OTHER, tag),)


def test_two_missing_points_are_both_named():
    finding = _summary(f"Warning {POINTS_07[0]} {POINTS_07[2]} {KEY_INFORMATION} {OWN_WORDS * 5}")
    assert finding.issues == (warning_issue(OTHER, POINT_TAGS[1], POINT_TAGS[3]),)


def test_a_missing_german_point_is_named_in_german():
    # Point (c) of the German warning of field 07 is left out.
    sentences = WARNUNG_07.split(". ")
    assert len(sentences) == 4 and sentences[2].startswith("Das öffentliche Angebot")
    text = ". ".join(sentences[:2] + sentences[3:]) + f" {WESENTLICHE_INFORMATIONEN} {EIGENE_WORTE * 5}"
    finding = _summary(text, language="de")
    assert finding.issues == (
        "Warnhinweis nach Art. 6 Abs. 7 Unterabs. 2 MiCAR nicht im Wortlaut der Vorlage gefunden: "
        "Buchst. c kein Angebot von Finanzinstrumenten.",
    )


def test_the_regulation_openings_count_as_the_template_wording():
    # Art. 6(7) says "it should be read" and "the crypto-asset white paper"; the template says "this".
    text = (
        "The summary should be read as an introduction to the crypto-asset white paper. "
        "Prospective holders should base any decision to purchase the crypto-asset on the content of the "
        "crypto-asset white paper as a whole and not on the summary alone. "
        + POINTS_07[2]
        + " The crypto-asset white paper does not constitute a prospectus as referred to in Regulation (EU) "
        "2017/1129 or any other offer document pursuant to Union or national law. "
        f"{KEY_INFORMATION} {OWN_WORDS * 5}"
    )
    assert _summary(text).status == "pass"


def test_the_regime_names_its_article():
    assert warning_issue(ART) in _summary(f"{KEY_INFORMATION} {OWN_WORDS * 5} {REDEMPTION_ART}", ART).issues
    assert warning_issue(EMT) in _summary(f"{KEY_INFORMATION} {OWN_WORDS * 5} {REDEMPTION_EMT}", EMT).issues


# The redemption statement of Art. 19(6) and Art. 51(6) MiCAR, third subparagraph.


def test_an_art_summary_without_at_any_time_goes_to_review():
    base = f"{WARNING_I04} {KEY_INFORMATION} {OWN_WORDS * 5}"
    finding = _summary(f"{base} Holders have a permanent right of redemption against the issuer.", ART)
    assert finding.status == "review"
    assert finding.issues == (REDEMPTION_ISSUE_ART,)
    assert _summary(base, ART).issues == (REDEMPTION_ISSUE_ART,)


@pytest.mark.parametrize(
    "statement",
    [
        REDEMPTION_ART,
        "Holders may redeem their tokens at any time against the issuer.",
        "At all times the holders have a right of redemption against the issuer.",
        "The tokens are redeemable at any time.",
    ],
)
def test_an_art_redemption_statement_in_one_sentence_passes(statement: str):
    finding = _summary(f"{WARNING_I04} {KEY_INFORMATION} {OWN_WORDS * 5} {statement}", ART)
    assert finding.status == "pass", finding.issues


def test_redemption_and_at_any_time_in_separate_sentences_go_to_review():
    text = f"{WARNING_I04} {KEY_INFORMATION} {OWN_WORDS * 5} Holders have a right of redemption. They may act at any time."
    assert _summary(text, ART).issues == (REDEMPTION_ISSUE_ART,)


def test_an_emt_summary_without_par_value_goes_to_review():
    base = f"{WARNING_I05} {KEY_INFORMATION} {OWN_WORDS * 5}"
    finding = _summary(f"{base} The holders of this e-money token have a right of redemption at any time.", EMT)
    assert finding.status == "review"
    assert finding.issues == (PAR_VALUE_ISSUE_EMT,)
    assert _summary(base, EMT).issues == (REDEMPTION_ISSUE_EMT,)


@pytest.mark.parametrize(
    "statement",
    [REDEMPTION_EMT, "Holders may redeem the token at any time, at par value.", "Redeemable at any time at par."],
)
def test_an_emt_redemption_statement_passes(statement: str):
    finding = _summary(f"{WARNING_I05} {KEY_INFORMATION} {OWN_WORDS * 5} {statement}", EMT)
    assert finding.status == "pass", finding.issues


def test_the_other_regime_is_never_asked_for_a_redemption_statement():
    assert _summary(f"{WARNING_07} {KEY_INFORMATION} {OWN_WORDS * 5}").status == "pass"
    assert not any("redemption" in issue for issue in _summary(KEY_INFORMATION).issues)


def test_a_german_art_summary_without_jederzeit_goes_to_review():
    base = f"{WARNUNG_I04} {WESENTLICHE_INFORMATIONEN} {EIGENE_WORTE * 5}"
    finding = _summary(f"{base} Die Inhaber haben ein dauerhaftes Recht auf Rücktausch.", ART, language="de")
    assert finding.issues == (
        "Jederzeitiges Recht auf Rücktausch (Art. 19 Abs. 6 Unterabs. 3 MiCAR) nicht gefunden: kein Satz nennt den "
        "Rücktausch zusammen mit „jederzeit“.",
    )
    finding = _summary(f"{base} Die Inhaber können die Token jederzeit zurücktauschen.", EMT, language="de")
    assert finding.issues == (
        "Jederzeitiges Recht auf Rücktausch zum Nennwert (Art. 51 Abs. 6 Unterabs. 3 MiCAR) nicht gefunden: der "
        "Nennwert wird nicht genannt.",
    )


# Numbered-field drafts are read by the fields that carry the statements.


def test_a_placeholder_warning_field_is_named(tmp_path: Path):
    path = _numbered_draft(tmp_path, OTHER, [("07", "TBD"), ("08", OWN_WORDS * 5), ("10", KEY_INFORMATION)])
    finding = _summary_of(path, OTHER)
    assert finding.status == "review"
    assert (
        "Warning of Art. 6(7) MiCAR, second subparagraph, not found: field 07 (Warning in accordance with Article "
        "6(7), second subparagraph, of Regulation (EU) 2023/1114) holds only a placeholder such as TBD."
    ) in finding.issues
    assert not any("redemption" in issue for issue in finding.issues)


def test_an_art_numbered_draft_is_read_by_its_fields(tmp_path: Path):
    rows = [("I.04", WARNING_I04), ("I.05", OWN_WORDS * 5), ("I.06", REDEMPTION_ART), ("I.07", KEY_INFORMATION)]
    assert _summary_of(_numbered_draft(tmp_path, ART, rows), ART).status == "pass"
    rows = [("I.04", "[●]"), ("I.05", OWN_WORDS * 5), ("I.06", "TBC"), ("I.07", KEY_INFORMATION)]
    finding = _summary_of(_numbered_draft(tmp_path, ART, rows), ART)
    assert finding.status == "review"
    assert (
        "Warning of Art. 19(6) MiCAR, second subparagraph, not found: field I.04 (Warning in accordance with "
        "Article 19(6), second subparagraph, of Regulation (EU) 2023/1114) holds only a placeholder such as TBD."
    ) in finding.issues
    assert (
        "Right of redemption at any time (Art. 19(6), third subparagraph, MiCAR) not found: field I.06 (Right of "
        "redemption) holds only a placeholder such as TBD."
    ) in finding.issues


def test_an_emt_numbered_draft_is_read_by_its_fields(tmp_path: Path):
    rows = [("I.05", WARNING_I05), ("I.06", OWN_WORDS * 5), ("I.07", REDEMPTION_EMT), ("I.08", KEY_INFORMATION)]
    assert _summary_of(_numbered_draft(tmp_path, EMT, rows), EMT).status == "pass"
    # Field I.05 is not in the draft, and I.07 holds a placeholder.
    rows = [("I.06", OWN_WORDS * 5), ("I.07", "TBD"), ("I.08", KEY_INFORMATION)]
    finding = _summary_of(_numbered_draft(tmp_path, EMT, rows), EMT)
    assert finding.status == "review"
    assert (
        "Warning of Art. 51(6) MiCAR, second subparagraph, not found: field I.05 (Warning in accordance with "
        "Article 51(6), second subparagraph of Regulation (EU) 2023/1114) is empty or not in the draft."
    ) in finding.issues
    assert (
        "Right of redemption at any time and at par value (Art. 51(6), third subparagraph, MiCAR) not found: field "
        "I.07 (Right of redemption) holds only a placeholder such as TBD."
    ) in finding.issues


def test_a_numbered_field_is_read_alone():
    # The warning sits in field 08, not in field 07, so field 07 is reported empty; the section text is not searched.
    fields = {"07": "", "08": f"{WARNING_I04} {OWN_WORDS * 5}", "10": KEY_INFORMATION}
    finding = _summary(f"{WARNING_07} {OWN_WORDS * 5} {KEY_INFORMATION}", fields=fields)
    assert finding.issues == (
        "Warning of Art. 6(7) MiCAR, second subparagraph, not found: field 07 (Warning in accordance with Article "
        "6(7), second subparagraph, of Regulation (EU) 2023/1114) is empty or not in the draft.",
    )
    # An answered field that lacks par value is read for the EMT statement.
    fields = {"I.05": WARNING_I05, "I.07": "Holders may redeem at any time.", "I.08": KEY_INFORMATION}
    finding = _summary(f"{WARNING_I05} {OWN_WORDS * 5} {KEY_INFORMATION} Holders may redeem at any time.", EMT, fields=fields)
    assert finding.issues == (PAR_VALUE_ISSUE_EMT,)


def test_german_numbered_fields_are_named_by_number():
    fields = {"I.04": "TBD", "I.05": EIGENE_WORTE * 5, "I.06": "", "I.07": WESENTLICHE_INFORMATIONEN}
    finding = _summary(f"TBD {EIGENE_WORTE * 5} {WESENTLICHE_INFORMATIONEN}", ART, language="de", fields=fields)
    assert finding.issues == (
        "Warnhinweis nach Art. 19 Abs. 6 Unterabs. 2 MiCAR nicht gefunden: Feld I.04 enthält nur einen Platzhalter "
        "wie TBD.",
        "Jederzeitiges Recht auf Rücktausch (Art. 19 Abs. 6 Unterabs. 3 MiCAR) nicht gefunden: Feld I.06 ist leer "
        "oder fehlt.",
    )


def test_an_empty_or_placeholder_summary_stays_missing():
    assert _summary("").status == "missing"
    assert _summary("TBD", ART).status == "missing"
    assert not any("Warning" in issue for issue in _summary("TBD", ART).issues)
