"""COMMON.SUMMARY does not count the predefined warning toward its 80 words (#70).

The template of Implementing Regulation (EU) 2024/2984 gives the warning of Art. 6(7), 19(6) and 51(6) MiCAR,
second subparagraph, as predefined text of about 120 words (field 07 of Table 2, I.04 of Table 3, I.05 of
Table 4), so a summary of the warning and a line of key information met the minimum length.
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

# Field 07 of Table 2 as the Official Journal prints it, with an en dash in one "crypto-asset".
WARNING_07 = (
    "Warning This summary should be read as an introduction to the crypto-asset white paper. The prospective holder "
    "should base any decision to purchase this crypto \N{EN DASH}asset on the content of the crypto-asset white paper as a "
    "whole and not on the summary alone. The offer to the public of this crypto-asset does not constitute an offer "
    "or solicitation to purchase financial instruments and any such offer or solicitation can be made only by means "
    "of a prospectus or other offer documents pursuant to the applicable national law. This crypto-asset white paper "
    "does not constitute a prospectus as referred to in Regulation (EU) 2017/1129 of the European Parliament and of "
    "the Council or any other offer document pursuant to Union or national law."
)
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


def _summary(text: str, whitepaper_type: WhitepaperType = OTHER, language: str | None = None):
    rule = next(rule for rule in RULESETS[whitepaper_type] if rule.rule_id == "COMMON.SUMMARY")
    metadata = {"language": language} if language else {}
    whitepaper = Whitepaper(title="Synthetic", type=whitepaper_type, sections={"summary": text}, metadata=metadata)
    return Linter((rule,)).lint(whitepaper)[0]


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
    ("whitepaper_type", "warning"), [(OTHER, WARNING_07), (ART, WARNING_I04), (EMT, WARNING_I05)]
)
def test_the_template_warning_does_not_count(whitepaper_type: WhitepaperType, warning: str):
    finding = _summary(f"{warning} {KEY_INFORMATION}", whitepaper_type)
    assert finding.status == "review"
    assert finding.issues == ("Section is thin: 14 words besides the predefined warning, expected at least 80.",)
    assert _summary(f"{warning} {KEY_INFORMATION} {OWN_WORDS * 5}", whitepaper_type).status == "pass"


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
    paraphrase = (
        "Read this summary only as an introduction to the white paper, and base any purchase on the white paper as "
        "a whole. Nothing here offers financial instruments, and the white paper is no prospectus."
    )
    finding = _summary(f"{paraphrase} {KEY_INFORMATION}")
    assert finding.issues == ("Section is thin: 48 words, expected at least 80.",)


def test_a_summary_without_the_warning_keeps_its_message():
    finding = _summary(KEY_INFORMATION)
    assert finding.issues == ("Section is thin: 14 words, expected at least 80.",)
