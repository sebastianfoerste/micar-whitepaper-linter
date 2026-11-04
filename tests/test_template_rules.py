"""The template rules: ITS.NOTIFICATION_DATE_FORMAT, ITS.PREDEFINED_TEXT, ITS.FIELD_FORMATS, ITS.CODE_LISTS and
RTS.SUSTAINABILITY_INDICATORS (rules/templates.py).

They read the numbered fields of Tables 2, 3 and 4 of Implementing Regulation (EU) 2024/2984 and the indicators
S.1 to S.16 of Delegated Regulation (EU) 2025/422. Every fixture is synthetic; the issuers do not exist.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from micar_linter.lei import check_digits_for
from micar_linter.linter import lint_whitepaper
from micar_linter.predefined_texts import PREDEFINED_TEXTS
from micar_linter.rules import RULESETS
from micar_linter.rules.base import Severity
from micar_linter.template_checks import energy_kwh, is_iso_date, label_fits, read_number, strip_name
from micar_linter.template_fields import FIELD_NAMES
from micar_linter.template_types import FIELD_TYPES, SUSTAINABILITY_FIELDS
from micar_linter.whitepaper import WhitepaperType, load_whitepaper

OTHER, ART, EMT = WhitepaperType.OTHER, WhitepaperType.ART, WhitepaperType.EMT
LEI = "9999SYNTH0000ZZQ01" + check_digits_for("9999SYNTH0000ZZQ01")
BROKEN_LEI = LEI[:-2] + f"{(int(LEI[-2:]) + 1) % 100:02d}"
TEMPLATE_RULE_IDS = (
    "ITS.NOTIFICATION_DATE_FORMAT",
    "ITS.PREDEFINED_TEXT",
    "ITS.FIELD_FORMATS",
    "ITS.CODE_LISTS",
    "RTS.SUSTAINABILITY_INDICATORS",
)

# The predefined texts in the template's English wording (Implementing Regulation (EU) 2024/2984).
APPROVAL = (
    "This crypto-asset white paper has not been approved by any competent authority in any Member State of the "
    "European Union."
)
SCHEMES = (
    "is not covered by the investor compensation schemes under Directive 97/9/EC of the European Parliament and "
    "of the Council or the deposit guarantee schemes under Directive 2014/49/EU of the European Parliament and of "
    "the Council."
)
LOSS = "may lose its value in part or in full, may not always be transferable and may not be liquid."


def _compliance(title: str, complete: str = "") -> str:
    return (
        f"This crypto-asset white paper complies with Title {title} of Regulation (EU) 2023/1114 of the European "
        "Parliament and of the Council and, to the best of the knowledge of the management body, the information "
        f"presented in the crypto-asset white paper is {complete}fair, clear and not misleading and the "
        "crypto-asset white paper makes no omission likely to affect its import."
    )


def _warning(token: str) -> str:
    return (
        "Warning\nThis summary should be read as an introduction to the crypto-asset white paper. The prospective "
        f"holder should base any decision to purchase this {token} on the content of the crypto-asset white paper "
        "as a whole and not on the summary alone. The offer to the public of this crypto-asset does not constitute "
        "an offer or solicitation to purchase financial instruments and any such offer or solicitation can be made "
        "only by means of a prospectus or other offer documents pursuant to the applicable national law. This "
        "crypto-asset white paper does not constitute a prospectus as referred to in Regulation (EU) 2017/1129 of "
        "the European Parliament and of the Council or any other offer document pursuant to Union or national law."
    )


UTILITY = (
    "The utility token referred to in this white paper may not be exchangeable against the good or service "
    "promised in this white paper, especially in the case of a failure or discontinuation of the crypto-asset "
    "project."
)
TABLE_2_TEXTS = [
    ("01", "2026-03-02"),
    ("02", f"{APPROVAL} The offeror of the crypto-asset is solely responsible for the content of this crypto-asset "
     "white paper."),
    ("03", _compliance("II")),
    ("04", f"The crypto-asset referred to in this crypto-asset white paper {LOSS}"),
    ("05", "false"),
    ("06", f"The crypto-asset referred to in this white paper {SCHEMES}"),
    ("07", _warning("crypto \u2013asset")),
]
TABLE_3_TEXTS = [
    ("I.01", "2026-03-02"),
    ("I.02", f"The asset-referenced token referred to in this crypto-asset white paper {LOSS} The asset-refenced "
     f"token referred to in this crypto-asset white paper {SCHEMES}"),
    ("I.03", _compliance("III")),
    ("I.04", _warning("asset-referenced token")),
    ("I.06", "The holders of asset-referenced tokens have a right of redemption at any time. Holders redeem through "
     "the fictional issuer's website on any business day."),
]
TABLE_4_TEXTS = [
    ("I.01", "2026-03-02"),
    ("I.02", f"{APPROVAL} The issuer of the crypto-asset is solely responsible for the content of this crypto-asset "
     "white paper."),
    ("I.03", _compliance("IV", "complete, ")),
    ("I.04", f"This e-money token {SCHEMES}"),
    ("I.05", _warning("e-money token")),
    ("I.07", "The holders of this e-money token have a right of redemption at any time and at par value."),
]

# The German wording of Table 2.
TABLE_2_GERMAN = [
    ("01", "2026-03-02"),
    ("02", "„Dieses Kryptowerte-Whitepaper wurde von keiner zuständigen Behörde eines Mitgliedstaats der "
     "Europäischen Union genehmigt. Der Anbieter des Kryptowerts trägt die alleinige Verantwortung für den Inhalt "
     "dieses Kryptowerte-Whitepapers.“"),
    ("03", "Dieses Kryptowerte-Whitepaper erfüllt Titel II der Verordnung (EU) 2023/1114 des Europäischen "
     "Parlaments und des Rates und es wird bestätigt, dass die in ihm enthaltenen Informationen nach bestem Wissen "
     "des Leitungsorgans redlich, eindeutig und nicht irreführend sind und dass das Kryptowerte-Whitepaper keine "
     "Auslassungen aufweist, die seine Aussagekraft beeinträchtigen könnten."),
    ("04", "Der in diesem Kryptowerte-Whitepaper genannte Kryptowert kann seinen Wert ganz oder teilweise "
     "verlieren, ist möglicherweise nicht immer übertragbar und ist möglicherweise nicht liquide."),
    ("05", "falsch"),
    ("06", "Der in diesem Whitepaper genannte Kryptowert fällt nicht unter die Systeme für die Entschädigung der "
     "Anleger gemäß der Richtlinie 97/9/EG des Europäischen Parlaments und des Rates oder die "
     "Einlagensicherungssysteme gemäß der Richtlinie 2014/49/EU des Europäischen Parlaments und des Rates."),
    ("07", "Warnhinweis: Diese Zusammenfassung ist als Einführung in das Kryptowerte-Whitepaper zu lesen. Der "
     "potenzielle Inhaber sollte jede Entscheidung über den Kauf des Kryptowerts auf der Grundlage des Inhalts des "
     "gesamten Kryptowerte-Whitepapers und nicht allein auf der Grundlage der Zusammenfassung treffen. Das "
     "öffentliche Angebot dieses Kryptowerts stellt kein Angebot und keine Aufforderung zum Kauf von "
     "Finanzinstrumenten dar und ein solches Angebot oder eine solche Aufforderung kann nur mittels eines "
     "Prospekts oder anderer im geltenden nationalen Recht vorgesehener Angebotsunterlagen erfolgen. Dieses "
     "Kryptowerte-Whitepaper stellt keinen Prospekt im Sinne der Verordnung (EU) 2017/1129 des Europäischen "
     "Parlaments und des Rates und kein anderes Angebotsdokument im Sinne von Unionsrecht oder nationalem Recht "
     "dar."),
]

# Lettered fields that make the layout a numbered one (three parts with content), with typed answers.
TABLE_2_TYPED = [
    ("A.1", "Meadow Labs GmbH (fictional)"),
    ("A.5", "2021-04-01"),
    ("A.6", LEI),
    ("A.10", "5"),
    ("B.1", "false"),
    ("E.1", "ATTR"),
    ("E.3", "5000000"),
    ("E.9", "EUR"),
    ("E.13", "RETL"),
    ("E.34", "XSYN"),
    ("F.4", "OTHR"),
    ("F.5", "NEWT"),
    ("F.13", "S9NTH0DT1"),
    ("F.18", "Germany"),
    ("F.19", "Austria, France and Italy"),
]
TABLE_3_TYPED = [
    ("A.1", "Meadow Reserve GmbH (fictional)"),
    ("A.7", LEI),
    ("A.17", "NOEX"),
    ("B.7", "ARTW"),
    ("B.8", "NEWT"),
    ("C.1", "OTPC"),
    ("C.5", "NTAV"),
    ("C.7", "1000000.5"),
    ("D.35", "EUR"),
]
TABLE_4_TYPED = [
    ("A.1", "Meadow Pay GmbH (fictional)"),
    ("A.7", LEI),
    ("A.11", "5 days"),
    ("B.4", "EMTW"),
    ("B.5", "NEWT"),
    ("C.1", "OTPC"),
    ("C.2", "1000000"),
]

INDICATORS = [
    ("S.1", "Meadow Labs GmbH (fictional)"),
    ("S.2", LEI),
    ("S.3", "MeadowPoints"),
    ("S.4", "Proof of stake, see field H.4."),
    ("S.5", "Validators receive staking rewards, see field H.5."),
    ("S.6", "2025-01-01"),
    ("S.7", "2025-12-31"),
    ("S.8", "1234.56789 kWh"),
    ("S.9", "Estimate based on the number of validator nodes and a public model of their power draw."),
]
SUPPLEMENTARY = [
    ("S.10", "45.5"),
    ("S.11", "0.0012 kWh"),
    ("S.12", "0"),
    ("S.13", "312.5 tCO2e"),
    ("S.14", "0.4 kg CO2e per transaction"),
    ("S.15", "Grid mix of the countries where validators run, from a public dataset."),
    ("S.16", "Location-based method with public emission factors."),
]


def _label(number: str, whitepaper_type: WhitepaperType, german: bool) -> str:
    if number in SUSTAINABILITY_FIELDS:
        return SUSTAINABILITY_FIELDS[number][1 if german else 0]
    if german and number in FIELD_TYPES[whitepaper_type]:
        return FIELD_TYPES[whitepaper_type][number].name_de
    return FIELD_NAMES[whitepaper_type].get(number, "")


def _numbered(
    tmp_path: Path,
    rows: list[tuple[str, str]],
    whitepaper_type: WhitepaperType = OTHER,
    *,
    german: bool = False,
    labels: dict[str, str] | None = None,
):
    labels = labels or {}
    cells = "".join(
        f"<tr><td>{number}</td><td>{labels.get(number, _label(number, whitepaper_type, german))}</td>"
        f"<td>{text}</td></tr>"
        for number, text in rows
    )
    path = tmp_path / "draft.xhtml"
    path.write_text(f"<html><body><table>{cells}</table></body></html>", encoding="utf-8")
    return lint_whitepaper(load_whitepaper(path, whitepaper_type))


def _json(tmp_path: Path, whitepaper_type: WhitepaperType, sections: dict, **metadata: object):
    path = tmp_path / "draft.json"
    draft = {"title": "Synthetic draft", "type": whitepaper_type.value, "sections": sections, **metadata}
    path.write_text(json.dumps(draft), encoding="utf-8")
    return lint_whitepaper(load_whitepaper(path))


def _finding(report, rule_id: str):
    return next(finding for finding in report.findings if finding.rule.rule_id == rule_id)


def _with(rows: list[tuple[str, str]], field: str, answer: str | None) -> list[tuple[str, str]]:
    if answer is None:
        return [(number, text) for number, text in rows if number != field]
    if all(number != field for number, _ in rows):
        return [*rows, (field, answer)]
    return [(number, answer if number == field else text) for number, text in rows]


TABLES = {
    OTHER: TABLE_2_TEXTS + TABLE_2_TYPED + INDICATORS,
    ART: TABLE_3_TEXTS + TABLE_3_TYPED + INDICATORS,
    EMT: TABLE_4_TEXTS + TABLE_4_TYPED + INDICATORS,
}


# --- The rule set ------------------------------------------------------------------------------------------


def test_every_regime_runs_the_template_rules_with_stable_ids():
    for regime in WhitepaperType:
        ids = [rule.rule_id for rule in RULESETS[regime]]
        assert all(ids.count(rule_id) == 1 for rule_id in TEMPLATE_RULE_IDS), regime
    severities = {rule.rule_id: rule.severity for rule in RULESETS[OTHER] if rule.rule_id in TEMPLATE_RULE_IDS}
    assert severities["ITS.CODE_LISTS"] is Severity.MAJOR
    assert {severities[rule_id] for rule_id in TEMPLATE_RULE_IDS if rule_id != "ITS.CODE_LISTS"} == {
        Severity.BLOCKER
    }


def test_the_template_rule_ids_do_not_collide_with_other_rules():
    for regime in WhitepaperType:
        # RTS.CLASSIFICATION_DATA has its own tests (test_classification_data.py).
        own = (*TEMPLATE_RULE_IDS, "RTS.CLASSIFICATION_DATA")
        others = [rule.rule_id for rule in RULESETS[regime] if rule.rule_id not in own]
        assert not any(rule_id.startswith(("ITS.", "RTS.")) for rule_id in others)


@pytest.mark.parametrize("regime", list(WhitepaperType))
def test_a_complete_template_draft_passes_every_template_rule(tmp_path, regime):
    report = _numbered(tmp_path, TABLES[regime], regime)
    for rule_id in TEMPLATE_RULE_IDS:
        finding = _finding(report, rule_id)
        assert finding.status == "pass", (rule_id, finding.issues)


@pytest.mark.parametrize("regime", list(WhitepaperType))
def test_numbered_draft_without_template_fields_is_missing(tmp_path, regime):
    rows = [("A.1", "Synthetic GmbH (fictional)"), ("B.2", "Synthetic token"), ("C.3", "Synthetic text")]
    report = _numbered(tmp_path, rows, regime, labels={"A.1": "Name", "B.2": "Other", "C.3": "Other"})
    for rule_id in TEMPLATE_RULE_IDS:
        assert _finding(report, rule_id).status == "missing", rule_id


# --- Drafts without field numbers --------------------------------------------------------------------------


@pytest.mark.parametrize("regime", list(WhitepaperType))
def test_json_draft_goes_to_review_with_a_note_and_never_passes(tmp_path, regime):
    sections = {
        "management_statement": "Synthetic statement.",
        "offer_or_admission": "Synthetic offer.",
        "environmental_impact": "Synthetic impact.",
    }
    report = _json(tmp_path, regime, sections)
    for rule_id in ("ITS.PREDEFINED_TEXT", "ITS.FIELD_FORMATS", "ITS.CODE_LISTS", "RTS.SUSTAINABILITY_INDICATORS"):
        finding = _finding(report, rule_id)
        assert finding.status == "review", rule_id
        assert "numbered-field layout" in finding.issues[0]


def test_json_draft_without_the_sections_is_missing(tmp_path):
    report = _json(tmp_path, OTHER, {"project": "Synthetic project."})
    for rule_id in ("ITS.PREDEFINED_TEXT", "ITS.FIELD_FORMATS", "ITS.CODE_LISTS", "RTS.SUSTAINABILITY_INDICATORS"):
        assert _finding(report, rule_id).status == "missing", rule_id


def test_german_json_draft_gets_the_note_in_german(tmp_path):
    report = _json(tmp_path, OTHER, {"environmental_impact": "Der Konsens ist ein Beispiel."}, language="de")
    issue = _finding(report, "RTS.SUSTAINABILITY_INDICATORS").issues[0]
    assert issue.startswith("Dieser Entwurf hat keine Feldnummern")


def test_a_json_draft_cannot_bring_its_own_field_answers(tmp_path):
    answers = {"01": "2026-03-02", "S.1": "Synthetic"}
    report = _json(
        tmp_path,
        OTHER,
        {"environmental_impact": "Synthetic impact."},
        numbered_fields=answers,
        numbered_field_labels={"S.1": "Name"},
    )
    assert _finding(report, "RTS.SUSTAINABILITY_INDICATORS").status == "review"


# --- ITS.NOTIFICATION_DATE_FORMAT --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("answer", "status"),
    [
        ("2026-03-02", "pass"),
        ("\u20182026-03-02\u2019.", "pass"),
        ("02.03.2026", "review"),
        ("2 March 2026", "review"),
        ("2026-02-30", "review"),
        ("2026-03-02 (planned)", "review"),
        ("N/A", "review"),
        ("TBD", "missing"),
        (None, "missing"),
    ],
)
def test_notification_date_field_is_exactly_yyyy_mm_dd(tmp_path, answer, status):
    for regime, rows in ((OTHER, TABLE_2_TYPED), (ART, TABLE_3_TYPED), (EMT, TABLE_4_TYPED)):
        number = "01" if regime is OTHER else "I.01"
        report = _numbered(tmp_path, _with([(number, "x"), *rows], number, answer), regime)
        assert _finding(report, "ITS.NOTIFICATION_DATE_FORMAT").status == status, (regime, answer)


def test_notification_date_label_in_the_answer_is_split_off(tmp_path):
    rows = [("01", "Datum der Mitteilung 2026-03-02"), *TABLE_2_TYPED]
    report = _numbered(tmp_path, rows, labels={"01": ""})
    assert _finding(report, "ITS.NOTIFICATION_DATE_FORMAT").status == "pass"


def test_notification_date_issue_names_the_field(tmp_path):
    report = _numbered(tmp_path, [("I.01", "March 2026"), *TABLE_4_TYPED], EMT)
    assert _finding(report, "ITS.NOTIFICATION_DATE_FORMAT").issues == (
        "Field I.01 (Date of notification) does not hold exactly one valid date written YYYY-MM-DD (for example "
        "2026-03-02).",
    )


@pytest.mark.parametrize(
    ("text", "status"),
    [
        ("Date of notification: 2026-03-02", "pass"),
        ("Notified on 2 March 2026.", "review"),
        ("02.03.2026", "review"),
        ("TBD", "missing"),
        ("", "missing"),
    ],
)
def test_notification_date_section_of_a_draft_without_field_numbers(tmp_path, text, status):
    report = _json(tmp_path, OTHER, {"notification_date": text})
    assert _finding(report, "ITS.NOTIFICATION_DATE_FORMAT").status == status


def test_notification_date_review_in_german(tmp_path):
    report = _json(tmp_path, OTHER, {"notification_date": "Mitteilung am 02.03.2026"}, language="de")
    assert _finding(report, "ITS.NOTIFICATION_DATE_FORMAT").issues[0].startswith(
        "Der Abschnitt enthält kein gültiges Datum in der Form JJJJ-MM-TT"
    )


# --- ITS.PREDEFINED_TEXT -----------------------------------------------------------------------------------


def _predefined(tmp_path, rows, regime=OTHER, **kwargs):
    typed = {OTHER: TABLE_2_TYPED, ART: TABLE_3_TYPED, EMT: TABLE_4_TYPED}[regime]
    return _finding(_numbered(tmp_path, [*rows, *typed], regime, **kwargs), "ITS.PREDEFINED_TEXT")


def test_predefined_texts_of_table_2_in_german_pass(tmp_path):
    finding = _predefined(tmp_path, TABLE_2_GERMAN, german=True)
    assert finding.status == "pass", finding.issues


@pytest.mark.parametrize(
    "person",
    [
        "The person seeking admission to trading of the crypto-asset",
        "The operator of the trading platform of the crypto-asset",
    ],
)
def test_field_02_takes_each_of_its_three_wordings(tmp_path, person):
    statement = f"{APPROVAL} {person} is solely responsible for the content of this crypto-asset white paper."
    assert _predefined(tmp_path, _with(TABLE_2_TEXTS, "02", statement)).status == "pass"


def test_obvious_variants_pass(tmp_path):
    rows = _with(
        TABLE_2_TEXTS,
        "06",
        "“The Crypto Asset referred to in this white paper is not covered by the investor compensation schemes "
        "under Directive 97/9/EC or the deposit guarantee schemes under Directive 2014/49/EU.”",
    )
    rows = _with(rows, "03", _compliance("II").replace(" of the European Parliament and of the Council", ""))
    assert _predefined(tmp_path, rows).status == "pass"


@pytest.mark.parametrize(
    ("field", "answer", "issue"),
    [
        (
            "02",
            f"{APPROVAL} The issuer of the crypto-asset is solely responsible for the content of this crypto-asset "
            "white paper.",
            "Field 02 (Statement in accordance with Article 6(3) of Regulation (EU) 2023/1114) does not hold the "
            "predefined text; not found or worded otherwise (1/2 sentences): “The offeror of the crypto-asset is "
            "solely responsible for the ...”.",
        ),
        (
            "03",
            _compliance("III"),
            "Field 03 (Compliance statement in accordance with Article 6(6) of Regulation (EU) 2023/1114) does not "
            "hold the predefined text; not found or worded otherwise (1/1 sentences): “This crypto-asset white "
            "paper complies with Title II of Regulation ...”.",
        ),
        (
            "04",
            f"The crypto-asset referred to in this crypto-asset white paper {LOSS} The issuer expects it to rise.",
            "Field 04 (Statement in accordance with Article 6(5), points (a), (b), (c), of Regulation (EU) "
            "2023/1114) holds text besides the predefined text, which the template does not provide for.",
        ),
        (
            "06",
            "N/A",
            "Field 06 (Statement in accordance with Article 6(5), points (e) and (f), of Regulation (EU) 2023/1114) "
            "is marked not applicable; the template prescribes its text without a condition.",
        ),
        (
            "07",
            "TBD",
            "Field 07 (Warning in accordance with Article 6(7), second subparagraph, of Regulation (EU) 2023/1114) "
            "is empty, not in the draft or holds only a placeholder.",
        ),
    ],
)
def test_predefined_text_deviations_go_to_review(tmp_path, field, answer, issue):
    finding = _predefined(tmp_path, _with(TABLE_2_TEXTS, field, answer))
    assert finding.status == "review"
    assert issue in finding.issues


def test_alternatives_are_shown_in_full_where_a_sentence_is_missing(tmp_path):
    # The issue quotes the template, never the draft.
    finding = _predefined(tmp_path, _with(TABLE_2_TEXTS, "02", "Synthetic Secret Wording."))
    assert all("Synthetic Secret" not in issue for issue in finding.issues)


@pytest.mark.parametrize(
    ("answer", "status"),
    [
        ("false", "pass"),
        ("FALSE", "pass"),
        (f"true {UTILITY}", "pass"),
        (UTILITY, "pass"),
        ("true", "review"),
        ("N/A", "review"),
        ("Not a utility token.", "review"),
        (None, "review"),
    ],
)
def test_field_05_is_false_or_true_with_the_utility_statement(tmp_path, answer, status):
    assert _predefined(tmp_path, _with(TABLE_2_TEXTS, "05", answer)).status == status


def test_utility_token_classification_needs_the_statement_in_field_05(tmp_path):
    finding = _predefined(tmp_path, [*TABLE_2_TEXTS, ("D.6", "true")])
    assert finding.status == "review"
    assert finding.issues == (
        "Field D.6 classifies the token as a utility token, but field 05 (Statement in accordance with Article "
        "6(5), point (d), of Regulation (EU) 2023/1114) does not hold the utility-token statement.",
    )
    assert _predefined(tmp_path, [*_with(TABLE_2_TEXTS, "05", f"true {UTILITY}"), ("D.6", "true")]).status == "pass"


def test_german_deviation_is_reported_in_german(tmp_path):
    finding = _predefined(tmp_path, _with(TABLE_2_GERMAN, "04", "Der Kryptowert ist sicher."), german=True)
    assert finding.status == "review"
    assert finding.issues[0].startswith("Feld 04 gibt den vorgegebenen Text nicht wieder")


def test_table_3_uses_title_iii_and_the_redemption_sentence(tmp_path):
    assert _predefined(tmp_path, _with(TABLE_3_TEXTS, "I.03", _compliance("II")), ART).status == "review"
    no_redemption = _with(TABLE_3_TEXTS, "I.06", "Holders redeem on any business day.")
    assert _predefined(tmp_path, no_redemption, ART).status == "review"
    # The misspelling "refenced" of the template and the correct word both pass.
    corrected = [(n, t.replace("refenced", "referenced")) for n, t in TABLE_3_TEXTS]
    assert _predefined(tmp_path, corrected, ART).status == "pass"


def test_table_4_accepts_complete_that_art_51_5_requires(tmp_path):
    without = _with(TABLE_4_TEXTS, "I.03", _compliance("IV"))
    assert _predefined(tmp_path, without, EMT).status == "pass"
    assert _predefined(tmp_path, TABLE_4_TEXTS, EMT).status == "pass"


def test_table_4_redemption_at_par_value(tmp_path):
    rows = _with(TABLE_4_TEXTS, "I.07", "The holders of this e-money token have a right of redemption at any time.")
    finding = _predefined(tmp_path, rows, EMT)
    assert finding.status == "review"
    assert finding.issues[0].startswith("Field I.07 (Right of redemption) does not hold the predefined text")


def test_every_regime_has_predefined_fields_in_its_table():
    for regime, fields in PREDEFINED_TEXTS.items():
        assert set(fields) <= set(FIELD_NAMES[regime]), regime


# --- ITS.FIELD_FORMATS -------------------------------------------------------------------------------------


def _formats(tmp_path, rows, regime=OTHER, **kwargs):
    return _finding(_numbered(tmp_path, rows, regime, **kwargs), "ITS.FIELD_FORMATS")


@pytest.mark.parametrize(
    ("field", "answer", "status"),
    [
        ("A.5", "2021-04-01", "pass"),
        ("A.5", "1 April 2021", "review"),
        ("A.6", LEI, "pass"),
        ("A.6", f"LEI: {LEI}", "pass"),
        ("A.6", BROKEN_LEI, "review"),
        ("A.6", LEI.lower(), "review"),
        ("A.6", "Meadow Labs GmbH", "review"),
        ("A.10", "5", "pass"),
        ("A.10", "10 days", "pass"),
        ("A.10", "5 business days", "review"),
        ("A.10", "1000", "review"),
        ("B.1", "TRUE", "pass"),
        ("B.1", "true \u2013 Yes", "pass"),
        ("B.1", "Yes", "review"),
        ("E.3", "EUR 5,000,000.50", "pass"),
        ("E.3", "5 000 000", "pass"),
        ("E.3", "5.000.000,00", "review"),
        ("E.3", "about five million euros", "review"),
        ("E.3", "1 to 2 million", "review"),
        ("E.3", "1.2345", "review"),
        ("E.9", "EUR", "pass"),
        ("E.9", "S9NTH0DT1", "pass"),
        ("E.9", "Euro", "review"),
        ("E.12", "10,000,000 tokens", "pass"),
        ("E.12", "10000000.5", "review"),
        ("E.34", "XSYN", "pass"),
        ("E.34", "XSYN, YSYN", "pass"),
        ("E.34", "Synthetic Exchange", "review"),
        ("F.13", "S9NTH0DT1", "pass"),
        ("F.13", "DTI: S9NTH0DT1", "pass"),
        ("F.13", "applied for", "review"),
        ("F.13", "N/A", "pass"),
        ("F.13", "TBD", "pass"),
    ],
)
def test_typed_fields_of_table_2(tmp_path, field, answer, status):
    finding = _formats(tmp_path, _with(TABLE_2_TYPED, field, answer))
    assert finding.status == status, (field, answer, finding.issues)


def test_format_issue_names_the_field_and_the_type_but_not_the_answer(tmp_path):
    finding = _formats(tmp_path, _with(TABLE_2_TYPED, "E.3", "5.000.000,00"))
    assert finding.issues == (
        "Field E.3 (Fundraising target) does not hold an amount of up to 18 digits with up to 3 decimals "
        "(DECIMAL-18/3) or a whole number: the decimal separator is a comma or full stops separate the thousands; "
        "the template's decimal separator is a full stop.",
    )


def test_german_labels_are_recognised_and_issues_are_german(tmp_path):
    rows = [
        *TABLE_2_GERMAN,
        *_with(TABLE_2_TYPED, "A.5", "01.04.2021"),
    ]
    finding = _formats(tmp_path, rows, german=True)
    assert finding.status == "review"
    assert finding.issues == ("Feld A.5 entspricht nicht dem Typ der Vorlage, die ein Datum im Format JJJJ-MM-TT verlangt.",)


def test_a_field_under_another_label_is_not_checked_against_the_template_type(tmp_path):
    # The draft numbers its fields otherwise: its A.5 is not the registration date.
    rows = _with(TABLE_2_TYPED, "A.5", "Founded in spring")
    assert _formats(tmp_path, rows, labels={"A.5": "Company history"}).status == "pass"
    assert _formats(tmp_path, rows).status == "review"


@pytest.mark.parametrize(
    ("regime", "rows", "field", "answer"),
    [
        (ART, TABLE_3_TYPED, "C.7", "1.000.000,5"),
        (ART, TABLE_3_TYPED, "D.35", "Euro"),
        (ART, TABLE_3_TYPED, "A.7", BROKEN_LEI),
        (EMT, TABLE_4_TYPED, "C.2", "one million"),
        (EMT, TABLE_4_TYPED, "A.11", "within a week"),
    ],
)
def test_typed_fields_of_tables_3_and_4(tmp_path, regime, rows, field, answer):
    assert _formats(tmp_path, rows, regime).status == "pass"
    assert _formats(tmp_path, _with(rows, field, answer), regime).status == "review"


# --- ITS.CODE_LISTS ----------------------------------------------------------------------------------------


def _codes(tmp_path, rows, regime=OTHER, **kwargs):
    return _finding(_numbered(tmp_path, rows, regime, **kwargs), "ITS.CODE_LISTS")


@pytest.mark.parametrize(
    ("field", "answer", "status"),
    [
        ("E.1", "ATTR - admission to trading", "pass"),
        ("E.1", "OTPC, ATTR", "pass"),
        ("E.1", "Admission to trading", "review"),
        ("E.13", "ALL", "pass"),
        ("E.13", "retail investors", "review"),
        ("E.32", "NTAV", "pass"),
        ("F.4", "ARTW", "review"),
        ("F.5", "ERROR", "pass"),
        ("F.5", "New", "review"),
        ("F.18", "DE", "pass"),
        ("F.18", "Deutschland", "pass"),
        ("F.18", "Switzerland", "review"),
        ("F.19", "All EU Member States", "pass"),
        ("F.19", "the Netherlands; EL; Österreich", "pass"),
        ("F.19", "Germany and the United Kingdom", "review"),
    ],
)
def test_code_lists_of_table_2(tmp_path, field, answer, status):
    finding = _codes(tmp_path, _with(TABLE_2_TYPED, field, answer))
    assert finding.status == status, (field, answer, finding.issues)


def test_code_list_issue_lists_the_codes(tmp_path):
    finding = _codes(tmp_path, _with(TABLE_2_TYPED, "E.13", "retail investors"))
    assert finding.issues == (
        "Field E.13 (Targeted holders) does not hold a code of the template's list (RETL, PROF, ALL).",
    )


@pytest.mark.parametrize(
    ("regime", "rows", "field", "answer", "status"),
    [
        (ART, TABLE_3_TYPED, "C.8", "ALL", "review"),
        (ART, TABLE_3_TYPED, "C.5", "richtig", "pass"),
        (ART, TABLE_3_TYPED, "A.17", "EX18", "review"),
        (ART, TABLE_3_TYPED, "B.7", "OTHR", "review"),
        (EMT, TABLE_4_TYPED, "B.4", "EMTW", "pass"),
        (EMT, TABLE_4_TYPED, "B.4", "ARTW", "review"),
        (EMT, TABLE_4_TYPED, "C.1", "Offer to the public", "review"),
    ],
)
def test_code_lists_of_tables_3_and_4(tmp_path, regime, rows, field, answer, status):
    assert _codes(tmp_path, _with(rows, field, answer), regime).status == status


# --- RTS.SUSTAINABILITY_INDICATORS -------------------------------------------------------------------------


def _indicators(tmp_path, rows, regime=OTHER, **kwargs):
    typed = {OTHER: TABLE_2_TYPED, ART: TABLE_3_TYPED, EMT: TABLE_4_TYPED}[regime]
    return _finding(_numbered(tmp_path, [*typed, *rows], regime, **kwargs), "RTS.SUSTAINABILITY_INDICATORS")


@pytest.mark.parametrize("regime", list(WhitepaperType))
def test_mandatory_indicators_pass_in_every_regime(tmp_path, regime):
    assert _indicators(tmp_path, INDICATORS, regime).status == "pass"


def test_german_indicators_pass_and_report_in_german(tmp_path):
    rows = [*TABLE_2_GERMAN, *_with(INDICATORS, "S.3", "N/A")]
    finding = _finding(_numbered(tmp_path, [*TABLE_2_TYPED, *rows], german=True), "RTS.SUSTAINABILITY_INDICATORS")
    assert finding.issues == (
        "Feld S.3 ist als nicht anwendbar markiert; Art. 4 Abs. 1 VO (EU) 2025/422 verlangt die Angabe.",
    )


@pytest.mark.parametrize(
    ("field", "answer", "issue"),
    [
        ("S.1", None, "Field S.1 (Name) is empty or not in the draft."),
        ("S.9", "TBD", "Field S.9 (Energy consumption sources and methodologies) holds only a placeholder such as TBD."),
        (
            "S.6",
            "01.01.2025",
            "Field S.6 (Beginning of the period to which the disclosed information relates) does not hold a date in "
            "the format YYYY-MM-DD ({DATEFORMAT}).",
        ),
        ("S.6", "2026-01-01", "The beginning of the period (S.6) is later than its end (S.7)."),
        (
            "S.8",
            "1.234,5 kWh",
            "Field S.8 (Energy consumption) does not hold an amount in kilowatt-hours (kWh) {DECIMAL-18/5}: the "
            "decimal separator is a comma or full stops separate the thousands; the template's decimal separator is "
            "a full stop.",
        ),
        (
            "S.8",
            "2 MWh",
            "Field S.8 (Energy consumption) does not hold an amount in kilowatt-hours (kWh) {DECIMAL-18/5}: it is "
            "not given in kWh.",
        ),
        (
            "S.8",
            "1234.123456 kWh",
            "Field S.8 (Energy consumption) does not hold an amount in kilowatt-hours (kWh) {DECIMAL-18/5}: it has "
            "more digits than the type allows.",
        ),
    ],
)
def test_indicator_issues(tmp_path, field, answer, issue):
    finding = _indicators(tmp_path, _with(INDICATORS, field, answer))
    assert finding.status == "review"
    assert issue in finding.issues, finding.issues


@pytest.mark.parametrize("answer", ["1234.5 kWh per year", "1,234.5 kWh/year", "1234.5", "1234.5 kilowatt-hours"])
def test_energy_consumption_forms_that_pass(tmp_path, answer):
    assert _indicators(tmp_path, _with(INDICATORS, "S.8", answer)).status == "pass"


def test_supplementary_indicators_above_500_000_kwh(tmp_path):
    above = _with(INDICATORS, "S.8", "500000.1 kWh")
    finding = _indicators(tmp_path, above)
    assert finding.status == "review"
    assert [issue.split(" ")[1] for issue in finding.issues] == [f"S.{n}" for n in range(10, 17)]
    assert _indicators(tmp_path, [*above, *SUPPLEMENTARY]).status == "pass"
    # "exceeds 500 000 kilowatt-hours": exactly 500 000 does not.
    assert _indicators(tmp_path, _with(INDICATORS, "S.8", "500000 kWh")).status == "pass"
    # 600 MWh are 600 000 kWh: the unit is reported, and Table 3 is required.
    finding = _indicators(tmp_path, _with(INDICATORS, "S.8", "600 MWh"))
    assert any(issue.startswith("Field S.10 ") for issue in finding.issues)


def test_supplementary_indicators_cannot_be_decided_without_a_readable_amount(tmp_path):
    finding = _indicators(tmp_path, _with(INDICATORS, "S.8", "about one gigawatt-hour"))
    assert any("cannot be decided" in issue for issue in finding.issues)


def test_supplementary_indicator_formats_are_checked_when_given(tmp_path):
    finding = _indicators(tmp_path, [*INDICATORS, *_with(SUPPLEMENTARY, "S.10", "about half")])
    assert finding.issues == (
        "Field S.10 (Renewable energy consumption) does not hold a percentage {DECIMAL-11/10}: no number was "
        "found.",
    )
    assert _indicators(tmp_path, [*INDICATORS, *_with(SUPPLEMENTARY, "S.10", "45.5 %")]).status == "pass"


def test_indicators_all_unanswered_are_missing(tmp_path):
    rows = [(number, "TBD") for number, _ in INDICATORS]
    assert _indicators(tmp_path, rows).status == "missing"


# --- Helpers -----------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("token", "value", "problem"),
    [
        ("1234.5", Decimal("1234.5"), None),
        ("1,234,567.25", Decimal("1234567.25"), None),
        ("1 234 567", Decimal("1234567"), None),
        ("1.234.567", Decimal("1234567"), "comma"),
        ("12,5", Decimal("12.5"), "comma"),
        ("-3", Decimal("-3"), None),
    ],
)
def test_read_number(token, value, problem):
    assert read_number(token) == (value, problem)


def test_energy_in_kwh():
    assert energy_kwh("2 GWh") == (Decimal(2000000), ["unit"])
    assert energy_kwh("1500 kWh p.a.") == (Decimal(1500), [])


def test_iso_date_and_labels():
    assert is_iso_date("2026-03-02") and not is_iso_date("2026-3-2")
    assert label_fits("", ("Registration date",))
    assert label_fits("Type of white paper", ("Type of crypto-asset white paper",))
    assert not label_fits("Crypto-asset project description", ("Crypto-assets name",))
    assert strip_name("Registrierungsdatum: 2021-04-01", ("Registration date", "Registrierungsdatum")) == "2021-04-01"
