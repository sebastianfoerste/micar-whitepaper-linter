"""ANNEX_I.A.P6 and ANNEX_III.A.P6: the contact details of Annex I and Annex III Part A point 6 MiCAR (#68).

Point 6 asks for a contact telephone number, an e-mail address and the period of days within which an
investor will receive an answer. Fields A.8 to A.10 of Table 2 and A.9 to A.11 of Table 4 of Implementing
Regulation (EU) 2024/2984 carry them. ANNEX_I.A and ANNEX_III.A passed drafts without any of them.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from micar_linter.contact import has_email_address, has_period_in_days, has_telephone_number
from micar_linter.linter import lint_whitepaper
from micar_linter.numbered_fields import NumberedField, field_answers
from micar_linter.rules import RULESETS
from micar_linter.template_fields import FIELD_NAMES
from micar_linter.whitepaper import WhitepaperType, load_whitepaper

OTHER = WhitepaperType.OTHER
EMT = WhitepaperType.EMT

# The reproductions of #68.
OFFEROR = (
    "Name: Meadow Labs GmbH (fictional). Registered address and head office: Musterweg 1, 60311 Frankfurt am "
    "Main, Germany. The members of the management body are two fictional managing directors with the business "
    "address Musterweg 1, 60311 Frankfurt am Main. The company develops a marketplace for garden supplies, pays "
    "loyalty rewards to repeat buyers and has no parent company."
)
ISSUER = (
    "Name of the issuer: Meadow Pay GmbH (fictional), an electronic money institution authorised in Germany. "
    "Registered address and head office: Musterweg 1, 60311 Frankfurt am Main, Germany. The members of the "
    "management body are two fictional managing directors with the business address Musterweg 1, 60311 Frankfurt "
    "am Main. The issuer issues electronic money, runs payment accounts for small businesses and has no parent "
    "company. The issuer does not issue other crypto-assets and has no other activity related to crypto-assets, "
    "and no conflict of interest is known to the management body at the date of notification."
)
CONTACT = (
    " Investors can reach the company at +49 69 0000 0000 or contact@meadow.example and receive an answer within "
    "five business days."
)
NO_PHONE = (
    "No telephone number was found. A number counts with its country code (+49 ...) or its area code (069 ...), "
    "or after a label such as Tel. or Phone."
)
NO_EMAIL = "No e-mail address was found."
NO_DAYS = "No period in days was found, for example 5 business days."


def _json_report(tmp_path: Path, whitepaper_type: WhitepaperType, sections: dict, **metadata: object):
    path = tmp_path / "draft.json"
    draft = {"title": "Synthetic draft", "type": whitepaper_type.value, "sections": sections, **metadata}
    path.write_text(json.dumps(draft), encoding="utf-8")
    return lint_whitepaper(load_whitepaper(path))


def _numbered_report(tmp_path: Path, rows: list[tuple[str, str]], whitepaper_type: WhitepaperType = OTHER):
    names = FIELD_NAMES[whitepaper_type]
    cells = "".join(f"<tr><td>{number}</td><td>{names.get(number, '')}</td><td>{text}</td></tr>" for number, text in rows)
    path = tmp_path / "draft.xhtml"
    path.write_text(f"<html><body><table>{cells}</table></body></html>", encoding="utf-8")
    return lint_whitepaper(load_whitepaper(path, whitepaper_type))


def _finding(report, rule_id: str):
    return next(finding for finding in report.findings if finding.rule.rule_id == rule_id)


def test_the_point_rules_run_for_annex_i_and_iii_only():
    ids = {regime: {rule.rule_id for rule in rules} for regime, rules in RULESETS.items()}
    assert "ANNEX_I.A.P6" in ids[OTHER]
    assert "ANNEX_III.A.P6" in ids[EMT]
    # Annex II Part A has no such point.
    assert not any(rule_id.endswith(".P6") for rule_id in ids[WhitepaperType.ART])


@pytest.mark.parametrize(
    ("whitepaper_type", "section", "text", "part_rule", "point_rule"),
    [
        (OTHER, "offeror", OFFEROR, "ANNEX_I.A", "ANNEX_I.A.P6"),
        (EMT, "issuer", ISSUER, "ANNEX_III.A", "ANNEX_III.A.P6"),
    ],
)
def test_the_issue_reproductions_go_to_review(tmp_path, whitepaper_type, section, text, part_rule, point_rule):
    report = _json_report(tmp_path, whitepaper_type, {section: text})
    # The Part rule stays as it is (ADR 0005); the point rule reports the three items.
    assert _finding(report, part_rule).status == "pass"
    finding = _finding(report, point_rule)
    assert finding.status == "review"
    assert finding.issues == (NO_PHONE, NO_EMAIL, NO_DAYS)
    assert _finding(_json_report(tmp_path, whitepaper_type, {section: text + CONTACT}), point_rule).status == "pass"


def test_each_missing_item_is_named(tmp_path):
    text = f"{OFFEROR} Telephone: +49 69 0000 0000. E-mail: contact@meadow.example."
    finding = _finding(_json_report(tmp_path, OTHER, {"offeror": text}), "ANNEX_I.A.P6")
    assert finding.status == "review"
    assert finding.issues == (NO_DAYS,)


def test_an_absent_or_placeholder_section_is_missing(tmp_path):
    assert _finding(_json_report(tmp_path, OTHER, {}), "ANNEX_I.A.P6").status == "missing"
    assert _finding(_json_report(tmp_path, EMT, {"issuer": "TBD"}), "ANNEX_III.A.P6").status == "missing"


def test_the_template_labels_count_in_a_draft_without_field_numbers(tmp_path):
    text = "Contact telephone number: +49 69 0000 0000\nE-mail address: contact@meadow.example\nResponse time (Days): 5"
    assert _finding(_json_report(tmp_path, OTHER, {"offeror": text}), "ANNEX_I.A.P6").status == "pass"


def test_a_german_draft_is_searched_in_german(tmp_path):
    text = (
        "Wiesen Pay GmbH (fiktiv). Telefon: 069 0000 0000. E-Mail: kontakt@wiesen.example. Anleger erhalten "
        "innerhalb von fünf Werktagen eine Antwort."
    )
    assert _finding(_json_report(tmp_path, EMT, {"issuer": text}, language="de"), "ANNEX_III.A.P6").status == "pass"
    finding = _finding(
        _json_report(tmp_path, EMT, {"issuer": "Wiesen Pay GmbH (fiktiv)."}, language="de"), "ANNEX_III.A.P6"
    )
    assert finding.issues[1:] == ("Keine E-Mail-Adresse gefunden.", "Keine Frist in Tagen gefunden, etwa 5 Werktage.")


def test_a_json_draft_cannot_supply_numbered_fields(tmp_path):
    report = _json_report(
        tmp_path, OTHER, {"offeror": OFFEROR}, numbered_fields={"A.8": "+49 69 0000 0000", "A.9": "a@b.example"}
    )
    assert _finding(report, "ANNEX_I.A.P6").issues == (NO_PHONE, NO_EMAIL, NO_DAYS)


TABLE_2 = [
    ("A.1", "Meadow Labs GmbH (fictional)"),
    ("A.8", "+49 69 0000 0000"),
    ("A.9", "contact@meadow.example"),
    ("A.10", "5"),
    ("D.1", "Meadow (fictional)"),
    ("E.1", "ATTR"),
]


def _with(rows: list[tuple[str, str]], field: str, answer: str | None) -> list[tuple[str, str]]:
    if answer is None:
        return [(number, text) for number, text in rows if number != field]
    return [(number, answer if number == field else text) for number, text in rows]


def test_answered_contact_fields_pass(tmp_path):
    assert _finding(_numbered_report(tmp_path, TABLE_2), "ANNEX_I.A.P6").status == "pass"


@pytest.mark.parametrize(
    ("field", "answer", "issue"),
    [
        ("A.10", "TBD", "Field A.10 (Response time (Days)) holds only a placeholder such as TBD."),
        ("A.10", None, "Field A.10 (Response time (Days)) is empty or not in the draft."),
        ("A.10", "24 hours", "Field A.10 (Response time (Days)) gives no number of days."),
        (
            "A.9",
            "N/A",
            "Field A.9 (E-mail address) is marked not applicable; point 6 asks for the e-mail address without a "
            "condition.",
        ),
        ("A.9", "See our website.", "Field A.9 (E-mail address) gives no e-mail address."),
        ("A.8", "Contact form only", "Field A.8 (Contact telephone number) gives no telephone number."),
        ("A.8", "Fax: +49 69 0000 0001", "Field A.8 (Contact telephone number) gives no telephone number."),
        ("A.8", "2026-03-02", "Field A.8 (Contact telephone number) gives no telephone number."),
    ],
)
def test_each_field_is_checked_for_its_item(tmp_path, field, answer, issue):
    finding = _finding(_numbered_report(tmp_path, _with(TABLE_2, field, answer)), "ANNEX_I.A.P6")
    assert finding.status == "review"
    assert finding.issues == (issue,)


def test_a_number_of_days_counts_in_the_response_time_field(tmp_path):
    for answer in ("5 business days", "within 10 days", "up to 3", "fünf Werktage"):
        assert _finding(_numbered_report(tmp_path, _with(TABLE_2, "A.10", answer)), "ANNEX_I.A.P6").status == "pass"


def test_contact_details_in_another_field_do_not_count(tmp_path):
    rows = [*_with(_with(_with(TABLE_2, "A.8", None), "A.9", None), "A.10", None), ("A.13", OFFEROR + CONTACT)]
    finding = _finding(_numbered_report(tmp_path, rows), "ANNEX_I.A.P6")
    assert finding.status == "missing"
    assert len(finding.issues) == 3


def test_a_part_of_placeholders_and_na_is_reviewed_not_missing(tmp_path):
    rows = _with(_with(_with(TABLE_2, "A.8", "TBD"), "A.9", "[●]"), "A.10", "N/A")
    assert _finding(_numbered_report(tmp_path, rows), "ANNEX_I.A.P6").status == "review"
    rows = _with(_with(_with(TABLE_2, "A.8", "TBD"), "A.9", "[●]"), "A.10", "TBC")
    assert _finding(_numbered_report(tmp_path, rows), "ANNEX_I.A.P6").status == "missing"


def test_a_label_run_into_its_answer_is_split_off(tmp_path):
    names = FIELD_NAMES[OTHER]
    cells = "".join(
        f"<tr><td>{number}</td><td>{names[number]} {text}</td></tr>"
        for number, text in (("A.8", "N/A"), ("A.9", "contact@meadow.example"), ("A.10", "5"))
    )
    cells += "<tr><td>A.1</td><td>Meadow Labs GmbH</td></tr><tr><td>D.1</td><td>Meadow</td></tr>"
    cells += "<tr><td>E.1</td><td>ATTR</td></tr>"
    path = tmp_path / "merged.xhtml"
    path.write_text(f"<html><body><table>{cells}</table></body></html>", encoding="utf-8")
    finding = _finding(lint_whitepaper(load_whitepaper(path, OTHER)), "ANNEX_I.A.P6")
    # The template's name does not make "N/A" read as a telephone number.
    assert finding.issues == (
        "Field A.8 (Contact telephone number) is marked not applicable; point 6 asks for the telephone number "
        "without a condition.",
    )


def test_table_4_numbers_the_contact_fields_a_9_to_a_11(tmp_path):
    rows = [
        ("A.1", "Meadow Pay GmbH (fictional)"),
        ("A.9", "+49 69 0000 0000"),
        ("A.10", "contact@meadow-pay.example"),
        ("A.11", "3"),
        ("B.1", "Meadow EUR (fictional)"),
        ("C.1", "Offer to the public in Germany (fictional)."),
    ]
    assert _finding(_numbered_report(tmp_path, rows, EMT), "ANNEX_III.A.P6").status == "pass"
    finding = _finding(_numbered_report(tmp_path, _with(rows, "A.11", "TBD"), EMT), "ANNEX_III.A.P6")
    assert finding.issues == ("Field A.11 (Response time (days)) holds only a placeholder such as TBD.",)


def test_german_findings_name_the_field_by_its_number(tmp_path):
    rows = [
        *_with(TABLE_2, "A.9", "siehe Website"),
        (
            "A.12",
            "Die Gesellschaft hat zwei fiktive Geschäftsführer mit der Geschäftsanschrift Musterweg 1, 60311 "
            "Frankfurt am Main, die die Gesellschaft gemeinsam vertreten und die Geschäfte der Gesellschaft führen.",
        ),
    ]
    finding = _finding(_numbered_report(tmp_path, rows), "ANNEX_I.A.P6")
    assert finding.issues == ("Feld A.9 enthält keine E-Mail-Adresse.",)


def test_field_answers_keys_fields_as_the_table_prints_them():
    fields = [
        NumberedField("04", "", "Warning"),
        NumberedField("A.9", "", "Contact telephone number +49 69 0000 0000"),
        NumberedField("A.11", "Response time (days)", "3"),
        NumberedField("A.11", "Response time (days)", "business days"),
        NumberedField("A.12", "Parent company", ""),
    ]
    assert field_answers(fields, EMT) == {
        "I.04": "Warning",
        "A.9": "+49 69 0000 0000",
        "A.11": "3\nbusiness days",
        "A.12": "",
    }


@pytest.mark.parametrize(
    "text",
    [
        "+49 69 0000 0000",
        "0049 69 0000 0000",
        "+49 (0)69 0000-0000",
        "069 0000 0000",
        "(069) 0000-0000",
        "069/00000000",
        "Tel.: 06900000000",
        "Telephone: (212) 555-0100",
        "Telefonnummer zur Kontaktaufnahme: 030 0000000",
    ],
)
def test_telephone_numbers_are_recognised(text):
    assert has_telephone_number(text)


@pytest.mark.parametrize(
    "text",
    [
        "Registered on 01.01.2020.",
        "01/02/2026 to 31/12/2026",
        "Musterweg 1, 01067 Dresden",
        "IBAN DE89 3704 0044 0532 0130 00",
        "LEI 9999SYNTHMESHCMP0151",
        "HRB 012345",
        "Fax: +49 69 0000 0001",
        "via that telephone number or email address",
        "share capital of EUR 25,000",
        "version 0.9.1",
    ],
)
def test_other_numbers_are_not_telephone_numbers(text):
    assert not has_telephone_number(text)


def test_e_mail_addresses_are_recognised():
    assert has_email_address("E-Mail: kontakt@müller.example.")
    assert has_email_address("info@sub.example.co.uk")
    assert not has_email_address("contact [at] meadow.example")
    assert not has_email_address("an email address")


@pytest.mark.parametrize(
    ("text", "found"),
    [
        ("within 5 business days", True),
        ("five (5) working days", True),
        ("a 10-day period", True),
        ("innerhalb von fünf Werktagen", True),
        ("binnen 3 Arbeitstagen", True),
        ("innerhalb eines Werktages", True),
        ("Reaktionszeit (Tage): 5", True),
        ("within 48 hours", False),
        ("within one week", False),
        ("on Monday", False),
        ("am Dienstag", False),
        ("in einem angemessenen Zeitraum", False),
    ],
)
def test_periods_in_days_are_recognised(text, found):
    assert has_period_in_days(text) is found


def test_a_response_time_field_counts_a_number_alone():
    assert has_period_in_days("5", labelled=True)
    assert has_period_in_days("up to 10", labelled=True)
    assert not has_period_in_days("24 hours", labelled=True)
    # "einem" is an article here, not a number.
    assert not has_period_in_days("in einem angemessenen Zeitraum", labelled=True)
    assert not has_period_in_days("promptly", labelled=True)
