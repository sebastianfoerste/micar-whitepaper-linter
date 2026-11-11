"""RTS.CLASSIFICATION_DATA: the register data of Delegated Regulation (EU) 2025/421 (classification_data.py).

The rule reads the numbered fields of Tables 2, 3 and 4 of Implementing Regulation (EU) 2024/2984 that carry
the items of the Annex to the Delegated Regulation, and the conditions of its Art. 2 (LEI) and Art. 3 (DTI).
Every fixture is synthetic; the issuers do not exist.
"""

from __future__ import annotations

import json
import socket
from pathlib import Path

import pytest

from micar_linter.classification_data import (
    AUTHORITY_ITEMS,
    ITEMS,
    ITEMS_BY_NUMBER,
    LAYOUTS,
    UNMAPPED_FIELDS,
    classification_issues,
)
from micar_linter.lei import check_digits_for
from micar_linter.linter import TEMPLATE_RULE_CHECKS, lint_whitepaper
from micar_linter.rules import RULESETS
from micar_linter.rules.base import Severity
from micar_linter.template_fields import FIELD_NAMES
from micar_linter.template_types import CODE_LIST_KINDS, FIELD_TYPES
from micar_linter.whitepaper import WhitepaperType, load_whitepaper

OTHER, ART, EMT = WhitepaperType.OTHER, WhitepaperType.ART, WhitepaperType.EMT
RULE_ID = "RTS.CLASSIFICATION_DATA"
LEI = "9999SYNTH0000ZZQ01" + check_digits_for("9999SYNTH0000ZZQ01")
BROKEN_LEI = LEI[:-2] + f"{(int(LEI[-2:]) + 1) % 100:02d}"
DTI, FFG = "S9NTH0DT1", "S9NTH0FG2"
TYPE_CODES = {OTHER: "OTHR", ART: "ARTW", EMT: "EMTW"}
# A marker that no finding may quote.
MARKER = "Zyxwvut"
GLEIF = "GLEIF database"


def _complete(regime: WhitepaperType) -> dict[str, str]:
    """A register block in which every item is answered, with the issuer's LEI and both identifiers."""
    layout = LAYOUTS[regime]
    values = {
        1: TYPE_CODES[regime],
        25: "NEWT",
        13: f"https://{MARKER.lower()}.example",
        16: "2026-04-01",
        20: "2026-03-20",
        22: "English",
        29: "false",
        14: "Germany",
        15: "Austria and France",
    }
    answers = {
        layout.issuer.name: f"{MARKER} Labs GmbH (fictional)",
        layout.issuer.lei: LEI,
        layout.offer_field: "OTPC",
        layout.dti_field: DTI,
        layout.ffg_field: FFG,
    }
    if layout.other_issuer is not None:
        answers["B.1"] = "false"
    answers.update({field: values[item] for item, field in layout.fields})
    return answers


def _check(answers: dict[str, str], regime: WhitepaperType, *, de: bool = False) -> tuple[str, tuple[str, ...]]:
    return classification_issues(answers, regime, de)


def _with(answers: dict[str, str], **changes: str | None) -> dict[str, str]:
    """The answers with fields changed (F_4="N/A" sets F.4) or removed (None)."""
    result = dict(answers)
    for key, value in changes.items():
        field = key.replace("_", ".")
        if value is None:
            result.pop(field, None)
        else:
            result[field] = value
    return result


def _rule(regime: WhitepaperType):
    return next(rule for rule in RULESETS[regime] if rule.rule_id == RULE_ID)


# --- The rule set ----------------------------------------------------------------------------------------


def test_every_regime_runs_the_rule_once_as_a_blocker_on_its_own_section():
    sections = {OTHER: "crypto_asset", ART: "art", EMT: "emt"}
    for regime in WhitepaperType:
        ids = [rule.rule_id for rule in RULESETS[regime]]
        assert ids.count(RULE_ID) == 1
        rule = _rule(regime)
        assert rule.severity is Severity.BLOCKER
        assert rule.section == sections[regime]
        assert rule.citation == "Art. 2 und 3 i.V.m. Anhang VO (EU) 2025/421"
    assert RULE_ID in TEMPLATE_RULE_CHECKS


# --- The mapping -----------------------------------------------------------------------------------------


def test_the_annex_has_29_items_and_the_layouts_name_template_fields():
    assert [item.number for item in ITEMS] == list(range(1, 30))
    assert AUTHORITY_ITEMS == (23, 24, 26)
    for regime, layout in LAYOUTS.items():
        names = FIELD_NAMES[regime]
        fields = [field for _, field in layout.fields]
        fields += [layout.issuer.name, layout.issuer.legal_form, layout.issuer.address, layout.issuer.lei]
        fields += [layout.offer_field, layout.mic_field, layout.dti_field, layout.ffg_field]
        for field in fields:
            assert field in names, (regime, field)
        for item, field in layout.fields:
            # The table on the rule page names the same field the check reads.
            assert ITEMS_BY_NUMBER[item].carried[regime] == field, (regime, item)
            assert not ITEMS_BY_NUMBER[item].optional
        for field in UNMAPPED_FIELDS[regime]:
            assert field in names


@pytest.mark.parametrize(
    ("regime", "item", "name"),
    [
        (OTHER, 1, "Type of crypto-asset white paper"),
        (OTHER, 29, "Personal data flag"),
        (OTHER, 14, "Home Member State"),
        (ART, 29, "Personal data flag"),
        (ART, 22, "Language or languages of the crypto-asset white paper"),
        (ART, 13, "Website of the issuer"),
        (EMT, 1, "Type of white paper"),
        (EMT, 29, "Personal data flag"),
        (EMT, 15, "Host Member States"),
    ],
)
def test_each_item_sits_in_the_field_the_template_names_for_it(regime, item, name):
    field = dict((number, field) for number, field in LAYOUTS[regime].fields)[item]
    assert FIELD_NAMES[regime][field] == name


def test_the_where_available_items_are_optional_and_the_others_not():
    optional = {item.number for item in ITEMS if item.optional}
    assert optional == {4, 5, 6, 7, 9, 11, 12, 17, 18, 19, 27, 28}


def test_typed_register_fields_are_left_to_the_its_rules():
    # The forms and codes of the register block are ITS.FIELD_FORMATS' and ITS.CODE_LISTS'.
    for regime, layout in LAYOUTS.items():
        types = FIELD_TYPES[regime]
        for item, field in layout.fields:
            if item in (1, 25, 14, 15):
                assert types[field].kind in CODE_LIST_KINDS, (regime, field)
            elif item in (16, 20, 29):
                assert field in types and types[field].kind not in CODE_LIST_KINDS, (regime, field)
        assert layout.dti_field in types and layout.ffg_field in types


# --- Numbered-field drafts -------------------------------------------------------------------------------


@pytest.mark.parametrize("regime", list(WhitepaperType))
def test_a_complete_register_block_passes_with_the_gleif_note(regime):
    status, issues = _check(_complete(regime), regime)
    assert status == "pass", issues
    assert len(issues) == 1 and GLEIF in issues[0]
    assert all(MARKER not in issue for issue in issues)


@pytest.mark.parametrize("regime", list(WhitepaperType))
def test_a_blank_register_block_is_missing(regime):
    answers = {field: "TBD" for field in _complete(regime)}
    status, issues = _check(answers, regime)
    assert status == "missing"
    assert issues


@pytest.mark.parametrize("regime", list(WhitepaperType))
@pytest.mark.parametrize("item", [1, 13, 14, 15, 16, 20, 22, 25, 29])
@pytest.mark.parametrize("answer", ["", "TBD", "N/A", None])
def test_each_mandatory_field_is_required(regime, item, answer):
    field = dict((number, field) for number, field in LAYOUTS[regime].fields)[item]
    answers = _with(_complete(regime), **{field.replace(".", "_"): answer})
    status, issues = _check(answers, regime)
    assert status == "review"
    assert any(issue.startswith(f"Field {field} (") and f"item {item} of the Annex" in issue for issue in issues)


def test_the_host_member_state_marked_not_applicable_asks_a_reviewer():
    status, issues = _check(_with(_complete(OTHER), F_19="N/A"), OTHER)
    assert status == "review"
    assert "offered in no host Member State, a reviewer confirms that" in issues[0]


@pytest.mark.parametrize(("regime", "field"), [(OTHER, "F.11"), (ART, "B.13"), (EMT, "B.10")])
def test_other_services_given_where_applicable_may_be_not_applicable(regime, field):
    status, _ = _check(_with(_complete(regime), **{field.replace(".", "_"): "N/A"}), regime)
    assert status == "pass"


@pytest.mark.parametrize("regime", list(WhitepaperType))
def test_without_an_lei_the_legal_form_and_address_are_required(regime):
    issuer = LAYOUTS[regime].issuer
    answers = _with(_complete(regime), **{issuer.lei.replace(".", "_"): None})
    status, issues = _check(answers, regime)
    assert status == "review"
    assert any(f"Field {issuer.legal_form} " in issue and "item 3 " in issue for issue in issues)
    assert any(f"Field {issuer.address} " in issue and "item 10 " in issue for issue in issues)
    assert not any(GLEIF in issue for issue in issues)
    answers = _with(answers, **{issuer.legal_form.replace(".", "_"): "GmbH", issuer.address.replace(".", "_"): "DE"})
    assert _check(answers, regime)[0] == "pass"


def test_an_lei_with_wrong_check_digits_does_not_stand_for_the_legal_form():
    # ITS.FIELD_FORMATS reports the check digits; this rule asks for the fields the LEI would have carried.
    status, issues = _check(_with(_complete(OTHER), A_6=BROKEN_LEI), OTHER)
    assert status == "review"
    assert any(issue.startswith("Field A.2 ") for issue in issues)
    assert not any("check digit" in issue for issue in issues)


def test_table_2_reads_the_issuer_from_part_b_where_it_is_not_the_offeror():
    answers = _with(_complete(OTHER), B_1="true")
    status, issues = _check(answers, OTHER)
    assert status == "review"
    assert any(issue.startswith("Field B.2 (Name)") for issue in issues)
    assert any(issue.startswith("Field B.3 ") for issue in issues)
    answers = _with(answers, B_2="Fictional Issuer AG", B_7=LEI)
    assert _check(answers, OTHER)[0] == "pass"
    # Where B.1 says neither, a name in B.2 makes Part B the issuer's.
    answers = _with(_complete(OTHER), B_1=None, B_2="Fictional Issuer AG")
    status, issues = _check(answers, OTHER)
    assert any(issue.startswith("Field B.3 ") for issue in issues)


@pytest.mark.parametrize("regime", list(WhitepaperType))
def test_admission_to_trading_needs_a_market_identifier_code(regime):
    layout = LAYOUTS[regime]
    answers = _with(_complete(regime), **{layout.offer_field.replace(".", "_"): "ATTR"})
    status, issues = _check(answers, regime)
    assert status == "review"
    assert any(f"field {layout.mic_field} (" in issue and "item 8 " in issue for issue in issues)
    answers = _with(answers, **{layout.mic_field.replace(".", "_"): "XSYN"})
    assert _check(answers, regime)[0] == "pass"
    # An offer to the public alone needs no MIC.
    assert _check(_with(_complete(regime), **{layout.mic_field.replace(".", "_"): "N/A"}), regime)[0] == "pass"


@pytest.mark.parametrize("regime", list(WhitepaperType))
def test_a_dti_needs_the_group_identifier_art_3_1(regime):
    layout = LAYOUTS[regime]
    status, issues = _check(_with(_complete(regime), **{layout.ffg_field.replace(".", "_"): "N/A"}), regime)
    assert status == "review"
    assert any("Art. 3(1)" in issue for issue in issues)


@pytest.mark.parametrize("regime", list(WhitepaperType))
def test_a_group_identifier_needs_the_dti_of_each_crypto_asset_art_3_2(regime):
    layout = LAYOUTS[regime]
    status, issues = _check(_with(_complete(regime), **{layout.dti_field.replace(".", "_"): None}), regime)
    assert status == "review"
    assert any("Art. 3(2)" in issue for issue in issues)


def test_the_same_code_as_dti_and_group_identifier_goes_to_review():
    status, issues = _check(_with(_complete(OTHER), F_14=f"FFG DTI: {DTI.lower()}"), OTHER)
    assert status == "review"
    assert any("give the same code" in issue for issue in issues)


@pytest.mark.parametrize("regime", list(WhitepaperType))
def test_without_any_dti_art_3_3_asks_for_an_esma_approved_identifier(regime):
    layout = LAYOUTS[regime]
    answers = _with(
        _complete(regime), **{layout.dti_field.replace(".", "_"): "N/A", layout.ffg_field.replace(".", "_"): ""}
    )
    status, issues = _check(answers, regime)
    assert status == "review"
    assert any("Art. 3(3)" in issue and "approved by ESMA at Union level" in issue for issue in issues)


def test_a_malformed_dti_is_left_to_the_format_check():
    # The form of F.13 is ITS.FIELD_FORMATS'; this rule counts the answer as given.
    status, issues = _check(_with(_complete(OTHER), F_13="DTI pending registration"), OTHER)
    assert status == "pass", issues


def test_a_malformed_date_or_code_is_not_reported_twice():
    answers = _with(_complete(OTHER), F_9="1 April 2026", F_5="new")
    status, issues = _check(answers, OTHER)
    assert status == "pass", issues


# --- German findings -------------------------------------------------------------------------------------


def test_german_findings_name_the_field_by_number_and_the_item_by_name():
    answers = _with(_complete(OTHER), F_16="", A_6=None, F_14=None)
    status, issues = _check(answers, OTHER, de=True)
    assert status == "review"
    assert (
        "Feld F.16 ist leer oder fehlt; es trägt Nr. 29 des Anhangs der VO (EU) 2025/421 (Kennzeichnung "
        "personenbezogener Daten)." in issues
    )
    assert any(issue.startswith("Feld A.2 ist leer") and "(Rechtsform des Emittenten)" in issue for issue in issues)
    assert any("Art. 3 Abs. 1 VO (EU) 2025/421" in issue for issue in issues)


def test_german_findings_cover_every_condition():
    answers = _with(_complete(ART), C_1="ATTR", B_15="N/A", B_16="N/A", B_20="nicht anwendbar")
    status, issues = _check(answers, ART, de=True)
    assert status == "review"
    text = " ".join(issues)
    assert "Feld C.1 nennt die Zulassung zum Handel (ATTR), Feld C.25 gibt aber keinen" in text
    assert "Art. 3 Abs. 3 VO (EU) 2025/421" in text
    assert "Aufnahmemitgliedstaat angeboten, bestätigt das die Prüfung" in text
    assert "GLEIF-Datenbank" in text
    assert not any(issue.startswith(("Field", "Neither", "Art. 2 of")) for issue in issues)


# --- Through the loaders ---------------------------------------------------------------------------------


def _xhtml(tmp_path: Path, answers: dict[str, str], regime: WhitepaperType):
    names = FIELD_NAMES[regime]
    cells = "".join(
        f"<tr><td>{number}</td><td>{names.get(number, '')}</td><td>{text}</td></tr>" for number, text in answers.items()
    )
    path = tmp_path / "draft.xhtml"
    path.write_text(f"<html><body><table>{cells}</table></body></html>", encoding="utf-8")
    report = lint_whitepaper(load_whitepaper(path, regime))
    return next(finding for finding in report.findings if finding.rule.rule_id == RULE_ID)


@pytest.mark.parametrize("regime", list(WhitepaperType))
def test_a_numbered_xhtml_draft_is_checked_field_by_field(tmp_path, regime):
    finding = _xhtml(tmp_path, _complete(regime), regime)
    assert finding.status == "pass", finding.issues
    layout = LAYOUTS[regime]
    finding = _xhtml(tmp_path, _with(_complete(regime), **{layout.fields[-1][1].replace(".", "_"): "TBD"}), regime)
    assert finding.status == "review"


def test_the_check_queries_no_network(tmp_path, monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("network access")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    assert _xhtml(tmp_path, _complete(OTHER), OTHER).status == "pass"


def _json(tmp_path: Path, regime: WhitepaperType, sections: dict[str, str], **metadata: object):
    path = tmp_path / "draft.json"
    draft = {"title": "Synthetic draft", "type": regime.value, "sections": sections, **metadata}
    path.write_text(json.dumps(draft), encoding="utf-8")
    return lint_whitepaper(load_whitepaper(path))


@pytest.mark.parametrize("regime", list(WhitepaperType))
def test_a_draft_without_field_numbers_does_not_run_the_check(tmp_path, regime):
    # Owner decision of 2026-11-10 (ADR 0005): no finding, so the rule is neither open nor passed.
    for sections in ({_rule(regime).section: "Synthetic characteristics and register data."}, {"risks": "Text."}):
        report = _json(tmp_path, regime, sections)
        assert RULE_ID not in {finding.rule.rule_id for finding in report.findings}
        assert RULE_ID in {rule.rule_id for rule in report.not_run}
        assert any("Delegated Regulations (EU) 2025/421 and 2025/422" in warning for warning in report.warnings)


def test_a_german_draft_without_field_numbers_gets_the_german_note(tmp_path):
    report = _json(tmp_path, OTHER, {"crypto_asset": "Text."}, language="de")
    assert RULE_ID not in {finding.rule.rule_id for finding in report.findings}
    assert any("Delegierten Verordnungen (EU) 2025/421 und 2025/422" in warning for warning in report.warnings)


def test_a_json_draft_cannot_supply_numbered_fields(tmp_path):
    # numbered_fields is reserved for the XHTML loader, so a JSON draft cannot pass the field check by itself.
    report = _json(tmp_path, OTHER, {"crypto_asset": "Synthetic text."}, numbered_fields=_complete(OTHER))
    assert RULE_ID in {rule.rule_id for rule in report.not_run}
    assert not any(f.rule.rule_id == RULE_ID for f in report.findings)
