"""A numbered field that holds only a placeholder keeps its section's checks from passing.

In a numbered-field draft a field answered "TBD" or "[●]" adds the placeholder alone to its section, so
a section with one such field among answered ones used to pass on the other fields (#69, and the summary
case of #70). The rules on that section now report Review and name the field by its number and template
name, without draft text.
"""

from __future__ import annotations

import json
from pathlib import Path

from micar_linter.linter import lint_whitepaper
from micar_linter.numbered_fields import NumberedField, sections_from_numbered_fields
from micar_linter.template_fields import FIELD_NAMES
from micar_linter.whitepaper import WhitepaperType, load_whitepaper

OTHER = WhitepaperType.OTHER
ART = WhitepaperType.ART

ANSWERED_PART_A = [
    ("A.1", "Meadow Labs GmbH (fictional)"),
    ("A.6", "N/A"),
    ("A.8", "+49 69 0000 0000"),
    ("A.9", "contact@meadow-labs.example"),
    ("A.10", "5"),
    ("A.12", "Two fictional managing directors, business address Musterweg 1, 60311 Frankfurt am Main."),
    (
        "A.13",
        "The fictional company develops and operates a marketplace for garden supplies and pays loyalty "
        "rewards to repeat buyers; it has no other business activity.",
    ),
    ("D.1", "Meadow (fictional)"),
    ("E.1", "ATTR"),
]

WARNING_07 = (
    "Warning This summary should be read as an introduction to the crypto-asset white paper. The prospective "
    "holder should base any decision to purchase this crypto-asset on the content of the crypto-asset white "
    "paper as a whole and not on the summary alone. The offer to the public of this crypto-asset does not "
    "constitute an offer or solicitation to purchase financial instruments and any such offer or solicitation "
    "can be made only by means of a prospectus or other offer documents pursuant to the applicable national law. "
    "This crypto-asset white paper does not constitute a prospectus as referred to in Regulation (EU) 2017/1129 "
    "of the European Parliament and of the Council or any other offer document pursuant to Union or national law."
)


def _with(rows: list[tuple[str, str]], field: str, answer: str) -> list[tuple[str, str]]:
    return [(number, answer if number == field else text) for number, text in rows]


def _report(tmp_path: Path, rows: list[tuple[str, str]], whitepaper_type: WhitepaperType = OTHER):
    names = FIELD_NAMES[whitepaper_type]
    cells = "".join(f"<tr><td>{number}</td><td>{names.get(number, '')}</td><td>{text}</td></tr>" for number, text in rows)
    path = tmp_path / "draft.xhtml"
    path.write_text(f"<html><body><table>{cells}</table></body></html>", encoding="utf-8")
    return lint_whitepaper(load_whitepaper(path, whitepaper_type))


def _finding(report, rule_id: str):
    return next(finding for finding in report.findings if finding.rule.rule_id == rule_id)


def test_answered_part_passes(tmp_path: Path):
    assert _finding(_report(tmp_path, ANSWERED_PART_A), "ANNEX_I.A").status == "pass"


def test_placeholder_field_keeps_its_part_from_passing(tmp_path: Path):
    # Issue #69: the response time of Annex I Part A point 6 reads TBD.
    finding = _finding(_report(tmp_path, _with(ANSWERED_PART_A, "A.10", "TBD")), "ANNEX_I.A")
    assert finding.status == "review"
    assert "Field A.10 (Response time (Days)) holds only a placeholder such as TBD." in finding.issues
    # "N/A" is an answer under review elsewhere, not a placeholder.
    assert not any("A.6" in issue for issue in finding.issues)


def test_several_placeholder_fields_are_named_together(tmp_path: Path):
    rows = _with(_with(ANSWERED_PART_A, "A.10", "TBD"), "A.9", "[●]")
    finding = _finding(_report(tmp_path, rows), "ANNEX_I.A")
    assert (
        "Fields A.9 (E-mail address) and A.10 (Response time (Days)) hold only placeholders such as TBD."
        in finding.issues
    )


def test_placeholder_characteristics_keep_the_summary_open(tmp_path: Path):
    # Issue #70: the predefined warning of field 07 and the key information of field 10 alone passed.
    rows = [
        ("07", WARNING_07),
        ("08", "TBD"),
        ("10", "Admission to trading on a fictional trading platform."),
        ("A.1", "Meadow Labs GmbH (fictional)"),
        ("D.1", "Meadow (fictional)"),
        ("E.1", "ATTR"),
    ]
    finding = _finding(_report(tmp_path, rows), "COMMON.SUMMARY")
    assert finding.status == "review"
    assert "Field 08 (Characteristics of the crypto-asset) holds only a placeholder such as TBD." in finding.issues


def test_leading_field_of_table_3_is_named_as_the_table_prints_it(tmp_path: Path):
    warning = WARNING_07.replace("this crypto-asset", "this asset-referenced token")
    rows = [
        ("I.04", warning),
        ("I.05", "TBC"),
        ("I.06", "Holders may redeem the token at any time at the market value of the reserve assets."),
        ("I.07", "Offer to the public of a fictional asset-referenced token in Germany."),
        ("A.1", "Meadow Reserve AG (fictional)"),
        ("B.1", "MRT (fictional)"),
        ("C.1", "Offer to the public in Germany (fictional)."),
    ]
    finding = _finding(_report(tmp_path, rows, ART), "COMMON.SUMMARY")
    assert "Field I.05 (Characteristics of the crypto-asset) holds only a placeholder such as TBD." in finding.issues


def test_german_draft_names_the_field_in_german(tmp_path: Path):
    rows = [
        ("A.1", "Wiesen Labs GmbH (fiktiv)"),
        ("A.8", "+49 69 0000 0000"),
        ("A.9", "kontakt@wiesen-labs.example"),
        ("A.10", "TBD"),
        (
            "A.12",
            "Die Gesellschaft hat zwei fiktive Geschäftsführer mit der Geschäftsanschrift Musterweg 1, 60311 "
            "Frankfurt am Main, die die Gesellschaft gemeinsam vertreten und die Geschäfte der Gesellschaft "
            "führen.",
        ),
        (
            "A.13",
            "Die fiktive Gesellschaft entwickelt und betreibt einen Marktplatz für Gartenbedarf und zahlt "
            "Treueprämien an wiederkehrende Käufer; sie hat keine andere Geschäftstätigkeit und keine "
            "Muttergesellschaft, und sie ist mit keinem anderen Unternehmen verbunden.",
        ),
        ("D.1", "Wiese (fiktiv)"),
        ("E.1", "ATTR"),
    ]
    finding = _finding(_report(tmp_path, rows), "ANNEX_I.A")
    assert finding.status == "review"
    assert "Feld A.10 enthält nur einen Platzhalter wie TBD." in finding.issues


def test_a_json_draft_cannot_set_the_placeholder_fields(tmp_path: Path):
    offeror = (
        "Name: Meadow Labs GmbH (fictional). Registered address and head office: Musterweg 1, 60311 Frankfurt am "
        "Main, Germany. The members of the management body are two fictional managing directors with the "
        "business address Musterweg 1, 60311 Frankfurt am Main. The company develops a marketplace for garden "
        "supplies, pays loyalty rewards to repeat buyers and has no parent company."
    )
    draft = {
        "title": "Synthetic draft",
        "type": "other",
        "sections": {"offeror": offeror},
        "placeholder_fields": {"offeror": ["A.10"]},
    }
    path = tmp_path / "draft.json"
    path.write_text(json.dumps(draft), encoding="utf-8")
    whitepaper = load_whitepaper(path)
    assert "placeholder_fields" not in whitepaper.metadata
    assert _finding(lint_whitepaper(whitepaper), "ANNEX_I.A").status == "pass"


def test_the_loader_lists_placeholder_fields_by_section():
    fields = [
        NumberedField("A.1", "Name", "Meadow Labs GmbH (fictional)"),
        NumberedField("A.6", "Legal entity identifier", "N/A"),
        NumberedField("A.10", "Response time (Days)", "TBD"),
        # A label run into its placeholder answer is split off first.
        NumberedField("A.11", "", "Parent company TBC"),
    ]
    _, _, placeholders = sections_from_numbered_fields(fields, OTHER)
    assert placeholders == {"offeror": ("A.10", "A.11")}
