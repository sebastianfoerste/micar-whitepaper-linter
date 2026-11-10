"""The point rules of ADR 0005 (rules/points.py, point_fields.py): one rule per Annex point that the numbered
fields of Tables 2 to 4 of Implementing Regulation (EU) 2024/2984 carry, with the template's conditions."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from micar_linter.lei import check_digits_for
from micar_linter.linter import CONTACT_POINT_RULE_IDS, Linter, lint_whitepaper
from micar_linter.point_fields import (
    ANNEX_REGIMES,
    ANSWERED,
    CODE,
    FLAG,
    NO_DTI,
    NO_LEI,
    POINTS,
    POINTS_BY_RULE,
    Alternative,
    field_state,
)
from micar_linter.rules import RULESETS
from micar_linter.rules.points import PART_SETTINGS, POINT_RULE_IDS, POINT_RULES
from micar_linter.template_fields import FIELD_NAMES
from micar_linter.template_types import CODES, DTI, FIELD_TYPES, LEI
from micar_linter.template_types import FLAG as FLAG_KIND
from micar_linter.whitepaper import Whitepaper, WhitepaperType, load_whitepaper

OTHER, ART, EMT = WhitepaperType.OTHER, WhitepaperType.ART, WhitepaperType.EMT
LEI_CODE = "9999SYNTH0000ZZQ01" + check_digits_for("9999SYNTH0000ZZQ01")
BROKEN_LEI = LEI_CODE[:-2] + f"{(int(LEI_CODE[-2:]) + 1) % 100:02d}"
DTI_CODE = "SYNTH0001"

# The points of each Annex Part, as the Official Journal text numbers them (read on 2026-11-04).
OJ_POINTS = {
    "I": {"A": 10, "B": 8, "C": 9, "D": 6, "E": 19, "F": 2, "G": 10, "H": 5, "I": 5},
    "II": {"A": 12, "B": 5, "C": 15, "D": 17, "E": 5, "F": 6, "G": 5},
    "III": {"A": 13, "B": 3, "C": 4, "D": 8, "E": 6, "F": 3},
}


def _rule(rule_id: str):
    point = POINTS_BY_RULE[rule_id]
    regime = ANNEX_REGIMES[point.annex]
    return next(rule for rule in RULESETS[regime] if rule.rule_id == rule_id), regime


def _lint(rule_id: str, answers: dict[str, str], language: str = "en"):
    rule, regime = _rule(rule_id)
    metadata = {"numbered_fields": answers, "numbered_field_labels": {}, "language": language}
    whitepaper = Whitepaper(title="Synthetic draft", type=regime, sections={}, metadata=metadata)
    return Linter((rule,)).lint(whitepaper)[0]


def _json(rule_id: str, sections: dict[str, str], language: str = "en"):
    rule, regime = _rule(rule_id)
    whitepaper = Whitepaper(title="Synthetic draft", type=regime, sections=sections, metadata={"language": language})
    return Linter((rule,)).lint(whitepaper)


# --- The rule set ---------------------------------------------------------------------------------------------


def test_every_annex_point_but_the_contact_details_has_a_point_rule():
    for annex, parts in OJ_POINTS.items():
        regime = ANNEX_REGIMES[annex]
        ids = {rule.rule_id for rule in RULESETS[regime]}
        for part, count in parts.items():
            for number in range(1, count + 1):
                assert f"ANNEX_{annex}.{part}.P{number}" in ids, (annex, part, number)
            assert f"ANNEX_{annex}.{part}.P{count + 1}" not in ids
    assert len(POINT_RULE_IDS) == 73 + 65 + 36
    assert not POINT_RULE_IDS & CONTACT_POINT_RULE_IDS


def test_point_rules_cite_their_point_and_follow_their_part_rule():
    for regime, rules in POINT_RULES.items():
        part_rules = {rule.rule_id: rule for rule in RULESETS[regime]}
        for rule in rules:
            point = POINTS_BY_RULE[rule.rule_id]
            assert rule.citation == f"Anhang {point.annex} Teil {point.part} Nr. {point.number} MiCAR"
            section, severity = PART_SETTINGS[(point.annex, point.part)]
            assert (rule.section, rule.severity) == (section, severity)
            part_rule = part_rules.get(f"ANNEX_{point.annex}.{point.part}")
            if part_rule is not None:
                assert (part_rule.section, part_rule.severity) == (section, severity), rule.rule_id
            else:
                # Annex II Part G has topic rules instead of a Part rule.
                topics = [r for r in RULESETS[regime] if r.rule_id.startswith("ANNEX_II.G.") and r.section == section]
                assert {r.severity for r in topics} == {severity}


def test_point_rules_follow_the_rules_of_their_part_in_point_order():
    ids = [rule.rule_id for rule in RULESETS[OTHER]]
    start = ids.index("ANNEX_I.A")
    assert ids[start : start + 11] == ["ANNEX_I.A", *(f"ANNEX_I.A.P{n}" for n in range(1, 11))]
    art = [rule.rule_id for rule in RULESETS[ART]]
    assert art.index("ANNEX_II.G.P1") > art.index("ANNEX_II.G.VALUATION_AUDIT")
    assert art.index("ANNEX_II.G.P5") < art.index("ANNEX_II.H")


def test_every_mapped_field_and_condition_is_in_its_table():
    for regime, points in POINTS.items():
        for point in points:
            for field in point.fields:
                assert field.number in FIELD_NAMES[regime] or field.number == "09", (point.rule_id, field.number)
                for condition in field.conditions:
                    kind = FIELD_TYPES[regime].get(condition.field)
                    if condition.kind == NO_LEI:
                        assert kind is not None and kind.kind == LEI
                    elif condition.kind == NO_DTI:
                        assert kind is not None and kind.kind == DTI
                    elif condition.kind == CODE:
                        assert kind is not None and condition.value in kind.codes
                    elif condition.kind == FLAG and condition.field != "05":
                        assert kind is not None and kind.kind in (FLAG_KIND, CODES)
                    else:
                        assert condition.kind in (FLAG, ANSWERED)


def test_every_field_the_template_conditions_is_mapped_with_its_condition():
    # The conditions the task and ADR 0005 name, as the Official Journal states them.
    expected = {
        OTHER: {
            "A.2": "A.6", "A.3": "A.6", "A.4": "A.6", "A.7": "A.6", "A.11": "A.6", "B.3": "B.7", "B.4": "B.7",
            "B.5": "B.7", "B.8": "B.7", "B.9": "B.7", "C.2": "C.6", "C.3": "C.6", "C.4": "C.6", "C.8": "C.6",
            "D.2": "F.13", "D.3": "F.13", "F.7": "F.13", "H.1": "F.13", "09": "05", "E.7": "E.6", "E.21": "E.20",
            "E.22": "E.20", "G.8": "G.6", "G.10": "G.9", "G.13": "G.12", "G.15": "G.14", "G.17": "G.16",
            "H.7": "H.6", "H.9": "H.8", "E.26": "E.1",
        },
        ART: {
            "A.3": "A.7", "A.4": "A.7", "A.5": "A.7", "A.9": "A.7", "B.1": "B.15", "B.2": "B.15", "E.1": "B.15",
            "A.18": "A.17", "C.6": "C.5", "C.16": "C.15", "C.17": "C.15", "D.9": "D.8", "D.12": "D.11",
            "D.14": "D.13", "D.16": "D.15", "E.7": "E.6", "E.9": "E.8", "G.5": "G.4",
        },
        EMT: {
            "A.3": "A.7", "A.4": "A.7", "A.5": "A.7", "A.12": "A.7", "B.1": "B.12", "B.2": "B.12", "E.1": "B.13",
            "A.25": "A.24", "D.10": "D.9", "D.12": "D.11", "E.8": "E.7", "E.10": "E.9",
        },
    }
    for regime, fields in expected.items():
        mapped = {field.number: field for point in POINTS[regime] for field in point.fields}
        for number, controller in fields.items():
            conditions = [c for c in mapped[number].conditions if not c.annex]
            assert [c.field for c in conditions] == [controller], (regime, number)


# --- Drafts without field numbers -----------------------------------------------------------------------------


def test_a_draft_without_field_numbers_does_not_run_a_point_rule():
    # Owner decision of 2026-11-10 (ADR 0005): no finding, whatever the section holds.
    for sections in ({}, {"offeror": "TBD"}, {"offeror": "Synthetic GmbH, a fictional company."}):
        assert _json("ANNEX_I.A.P2", sections) == ()
    rule, regime = _rule("ANNEX_I.A.P2")
    whitepaper = Whitepaper(title="Synthetic draft", type=regime, sections={}, metadata={})
    assert Linter((rule,)).not_run(whitepaper) == (rule,)
    with pytest.raises(ValueError):
        Linter._apply(rule, whitepaper)


def test_no_point_rule_but_the_contact_rules_runs_on_a_json_draft(tmp_path):
    for regime in (OTHER, ART, EMT):
        sections = {rule.section: "Synthetic section text." for rule in POINT_RULES[regime]}
        path = tmp_path / f"{regime.value}.json"
        path.write_text(json.dumps({"title": "Synthetic", "type": regime.value, "sections": sections}), "utf-8")
        report = lint_whitepaper(load_whitepaper(path))
        assert not {f.rule.rule_id for f in report.findings} & POINT_RULE_IDS
        assert {rule.rule_id for rule in report.not_run} >= {rule.rule_id for rule in POINT_RULES[regime]}
        contact = {"ANNEX_I.A.P6", "ANNEX_III.A.P6"} & {rule.rule_id for rule in RULESETS[regime]}
        assert contact <= {f.rule.rule_id for f in report.findings}
        points = len(POINT_RULES[regime])
        note = next(warning for warning in report.warnings if warning.startswith("Field-level checks"))
        assert f"so {points} point checks and " in note


# --- Field states ---------------------------------------------------------------------------------------------


def test_field_states():
    assert field_state("") == "empty"
    assert field_state("TBD\n[●]") == "placeholder"
    assert field_state("N/A\nTBD") == "not_applicable"
    assert field_state("N/A\nSynthetic GmbH") == "answer"


def test_unconditional_field_empty_placeholder_or_not_applicable():
    assert _lint("ANNEX_I.A.P1", {"A.1": "Synthetic GmbH"}).status == "pass"
    missing = _lint("ANNEX_I.A.P1", {})
    assert missing.status == "missing"
    assert missing.issues == ("Field A.1 (Name) is empty or not in the draft.",)
    assert _lint("ANNEX_I.A.P1", {"A.1": "TBD"}).issues == ("Field A.1 (Name) holds only a placeholder such as TBD.",)
    review = _lint("ANNEX_I.A.P1", {"A.1": "N/A"})
    assert review.status == "review"
    assert review.issues == ("Field A.1 (Name) is marked not applicable; the template asks for it without a condition.",)


def test_one_blank_field_of_several_is_review_and_all_blank_is_missing():
    answers = {"E.39": "Synthetic law", "E.40": "TBD"}
    assert _lint("ANNEX_I.E.P19", answers).status == "review"
    assert _lint("ANNEX_I.E.P19", {"E.39": "TBD", "E.40": ""}).status == "missing"
    assert _lint("ANNEX_I.E.P19", {"E.39": "Synthetic law", "E.40": "Synthetic court"}).status == "pass"


def test_where_applicable_fields_take_not_applicable_but_not_an_empty_field():
    assert _lint("ANNEX_I.E.P5", {"E.12": "N/A"}).status == "pass"
    assert _lint("ANNEX_I.E.P5", {"E.12": "none"}).status == "pass"
    empty = _lint("ANNEX_I.E.P5", {})
    assert empty.status == "missing"
    assert empty.issues == (
        "Field E.12 (Total number of offered/traded crypto-assets) is empty or not in the draft; where the item does "
        "not apply, the field should say so.",
    )
    assert _lint("ANNEX_I.A.P9", {"A.13": "Synthetic activity", "A.14": "N/A"}).status == "pass"
    assert _lint("ANNEX_I.A.P9", {"A.13": "Synthetic activity"}).status == "review"


def test_alternatives_pass_on_one_answer():
    assert _lint("ANNEX_I.A.P5", {"A.6": LEI_CODE}).status == "pass"
    assert _lint("ANNEX_I.A.P5", {"A.6": "N/A", "A.7": "HRB 0000 (synthetic)"}).status == "pass"
    review = _lint("ANNEX_I.A.P5", {"A.6": "N/A", "A.7": "N/A"})
    assert review.status == "review"
    assert review.issues[0] == (
        "None of fields A.6 (Legal entity identifier) and A.7 (Another identifier required pursuant to applicable "
        "national law) holds an answer; point 5 asks for at least one of them."
    )
    assert _lint("ANNEX_I.A.P5", {}).status == "missing"
    # The financial condition: over three years or since registration, whichever applies.
    for answers in ({"A.15": "true", "A.16": "Synthetic"}, {"A.15": "false", "A.17": "Synthetic"}):
        assert _lint("ANNEX_I.A.P10", answers).status == "pass"
        assert _lint("ANNEX_II.A.P9", {"A.13": answers["A.15"], "A.14": "Synthetic"}).status == "pass"
        assert _lint("ANNEX_III.A.P12", {"A.21": answers["A.15"], "A.23": "Synthetic"}).status == "pass"
    assert _lint("ANNEX_I.A.P10", {"A.15": "true", "A.16": "N/A", "A.17": "N/A"}).status == "review"
    # The issue price or the method by which it is determined.
    assert _lint("ANNEX_I.E.P4", {"E.8": "N/A", "E.11": "Synthetic auction", "E.10": "N/A"}).status == "pass"


# --- Conditions: LEI ------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("rule_id", "field", "lei_field"),
    [("ANNEX_I.A.P2", "A.2", "A.6"), ("ANNEX_II.A.P2", "A.3", "A.7"), ("ANNEX_III.A.P7", "A.12", "A.7")],
)
def test_a_valid_lei_relieves_the_fields_filled_only_without_one(rule_id, field, lei_field):
    finding = _lint(rule_id, {lei_field: LEI_CODE})
    assert finding.status == "pass"
    name = FIELD_NAMES[ANNEX_REGIMES[POINTS_BY_RULE[rule_id].annex]][field]
    assert finding.issues == (
        f"Field {field} ({name}) is not required: field {lei_field} gives an LEI; the template asks for it only if "
        f"field {lei_field} gives no valid LEI.",
    )
    # Without an LEI, or with one whose check digits fail, the field applies.
    for lei in ("", "N/A", BROKEN_LEI):
        finding = _lint(rule_id, {lei_field: lei})
        assert finding.status == "missing"
        assert finding.issues[0].endswith(f"Required because field {lei_field} gives no valid LEI.")


def test_lei_condition_in_german():
    finding = _lint("ANNEX_I.A.P2", {"A.6": LEI_CODE}, language="de")
    assert finding.issues == (
        "Feld A.2 ist nicht verlangt: Feld A.6 gibt eine LEI an; die Vorlage verlangt es nur, wenn Feld A.6 keine "
        "gültige LEI angibt.",
    )
    assert _lint("ANNEX_I.A.P2", {"A.6": "N/A", "A.2": "N/A"}, language="de").issues == (
        "Feld A.2 ist als nicht anwendbar markiert. Verlangt, weil Feld A.6 keine gültige LEI angibt.",
    )


# --- Conditions: DTI ------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("rule_id", "dti_field", "fields"),
    [
        ("ANNEX_I.D.P1", "F.13", {"D.1": "Synthetic project"}),
        ("ANNEX_II.B.P1", "B.15", {}),
        ("ANNEX_III.B.P1", "B.12", {}),
    ],
)
def test_a_dti_relieves_the_name_and_abbreviation(rule_id, dti_field, fields):
    assert _lint(rule_id, {**fields, dti_field: DTI_CODE}).status == "pass"
    assert _lint(rule_id, {**fields, dti_field: "N/A"}).status in ("missing", "review")
    assert _lint(rule_id, {**fields, dti_field: "not a DTI"}).status in ("missing", "review")


def test_table_4_field_e1_follows_the_official_journal_and_reads_b13():
    answers = {"E.2": "Synthetic protocols", "E.3": "N/A"}
    assert _lint("ANNEX_III.E.P1", {**answers, "B.13": DTI_CODE}).status == "pass"
    finding = _lint("ANNEX_III.E.P1", {**answers, "B.12": DTI_CODE})
    assert finding.status == "review"
    assert finding.issues == (
        "Field E.1 (Distributed ledger technology) is empty or not in the draft. Required because field B.13 gives "
        "no valid DTI.",
    )


# --- Conditions: true/false flags -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("rule_id", "flag", "field"),
    [("ANNEX_I.G.P8", "G.12", "G.13"), ("ANNEX_II.D.P7", "D.11", "D.12"), ("ANNEX_III.E.P5", "E.7", "E.8")],
)
def test_a_field_that_applies_only_if_a_flag_is_true(rule_id, flag, field):
    assert _lint(rule_id, {flag: "false"}).status == "pass"
    assert _lint(rule_id, {flag: "falsch"}).status == "pass"
    assert _lint(rule_id, {flag: "No"}).status == "pass"
    assert _lint(rule_id, {flag: "true", field: "Synthetic description"}).status == "pass"
    review = _lint(rule_id, {flag: "true \u2013 Yes", field: "N/A"})
    assert review.status == "review"
    assert review.issues[0].endswith(f"is marked not applicable. Required because field {flag} is true.")
    # A flag that gives neither true nor false leaves the field applying.
    unknown = _lint(rule_id, {flag: "maybe"})
    assert unknown.status == "review"
    assert unknown.issues[-1].endswith(f"Checked as required: field {flag} gives neither true nor false.")


@pytest.mark.parametrize(
    ("rule_id", "flag", "field"),
    [("ANNEX_I.G.P6", "G.9", "G.10"), ("ANNEX_II.D.P5", "D.8", "D.9"), ("ANNEX_III.A.P13", "A.24", "A.25")],
)
def test_a_field_that_applies_only_if_a_flag_is_false(rule_id, flag, field):
    relieved = _lint(rule_id, {flag: "true"})
    assert relieved.status == "pass"
    assert any(issue.startswith(f"Field {field} ") and "is not required" in issue for issue in relieved.issues)
    finding = _lint(rule_id, {flag: "false"})
    assert finding.status == "review"
    assert any(issue.startswith(f"Field {field} ") for issue in finding.issues)


def test_field_09_applies_only_if_field_05_is_true():
    base = {"G.6": "false"}
    assert _lint("ANNEX_I.G.P4", {**base, "05": "false"}).status == "pass"
    # Field 05 reads "'false' - Not applicable".
    assert _lint("ANNEX_I.G.P4", {**base, "05": "N/A"}).status == "pass"
    for switch in (
        "true",
        "The utility token referred to in this white paper may not be exchangeable against the good or service "
        "promised in this white paper, especially in the case of a failure or discontinuation of the crypto-asset "
        "project.",
    ):
        finding = _lint("ANNEX_I.G.P4", {**base, "05": switch})
        assert finding.status == "review"
        assert finding.issues[0] == "Field 09 is empty or not in the draft. Required because field 05 is true."
        assert _lint("ANNEX_I.G.P4", {**base, "05": switch, "09": "Synthetic goods"}).status == "pass"


def test_utility_token_fields_follow_the_classification():
    # G.8 by G.6 (the template), G.7 by G.6 and D.7 by D.6 (the Annex point).
    relieved = _lint("ANNEX_I.G.P5", {"G.6": "false"})
    assert relieved.issues == (
        "Field G.8 (Utility tokens redemption) is not required: field G.6 is not true; the template asks for it "
        "only if field G.6 is true.",
    )
    annex = _lint("ANNEX_I.D.P4", {"D.6": "false"})
    assert annex.status == "pass"
    assert "the condition comes from the Annex point, which asks for it only if field D.6 is true" in annex.issues[0]


def test_part_b_of_annex_i_applies_only_to_an_issuer_other_than_the_offeror():
    for rule_id in (f"ANNEX_I.B.P{n}" for n in range(1, 9)):
        finding = _lint(rule_id, {"B.1": "false"})
        assert finding.status == "pass", rule_id
        assert all("field B.1 is not true" in issue for issue in finding.issues)
    assert _lint("ANNEX_I.I.P2", {"B.1": "false"}).status == "pass"
    assert _lint("ANNEX_I.B.P1", {"B.1": "true"}).status == "missing"
    assert _lint("ANNEX_I.B.P1", {}).issues == (
        "Field B.2 (Name) is empty or not in the draft. Checked as required: field B.1 gives neither true nor false "
        "(a condition from the Annex point).",
    )


def test_a_condition_inferred_from_the_annex_point_says_so():
    # Owner decision 2A of 2026-11-10 (ADR 0005): a condition the template does not set stays, and every finding
    # and note that rests on it names the Annex point as its source, in English and in German.
    required = _lint("ANNEX_I.B.P1", {"B.1": "true"})
    assert required.issues == (
        "Field B.2 (Name) is empty or not in the draft. Required because field B.1 is true (a condition from the "
        "Annex point).",
    )
    german = _lint("ANNEX_I.B.P1", {"B.1": "true"}, language="de")
    assert german.issues == (
        "Feld B.2 ist leer oder fehlt. Verlangt, weil Feld B.1 richtig (true) ist (Bedingung aus dem "
        "Anhangspunkt).",
    )
    relieved = _lint("ANNEX_I.D.P4", {"D.6": "false"}, language="de")
    assert "die Bedingung stammt aus dem Anhangspunkt, der es nur verlangt, wenn" in relieved.issues[0]
    unknown = _lint("ANNEX_I.D.P4", {}, language="de")
    assert any("(Bedingung aus dem Anhangspunkt)" in issue for issue in unknown.issues)
    # A condition the template sets names the template.
    template = _lint("ANNEX_I.G.P5", {"G.6": "false"}, language="de")
    assert "die Vorlage verlangt es nur, wenn" in template.issues[0]
    assert "Anhangspunkt" not in template.issues[0]
    assert "Annex point" not in _lint("ANNEX_I.E.P9", {"E.20": "true"}).issues[0]


def test_ntav_relieves_the_oversubscription_allocation():
    answers = {"C.2": "N/A", "C.3": "N/A", "C.4": "N/A"}
    assert _lint("ANNEX_II.C.P2", {**answers, "C.5": "NTAV"}).status == "pass"
    assert _lint("ANNEX_II.C.P2", {**answers, "C.5": "true"}).status == "review"


def test_time_limited_offer_and_its_subscription_period():
    assert _lint("ANNEX_I.E.P9", {"E.20": "false"}).status == "pass"
    finding = _lint("ANNEX_I.E.P9", {"E.20": "true", "E.21": "2026-03-02"})
    assert finding.status == "review"
    assert finding.issues == (
        "Field E.22 (Subscription period end) is empty or not in the draft. Required because field E.20 is true.",
    )
    assert _lint("ANNEX_II.C.P7", {"C.15": "false"}).status == "pass"


# --- Conditions: codes and answers ----------------------------------------------------------------------------


def test_right_of_withdrawal_applies_to_offers_to_the_public():
    assert _lint("ANNEX_I.E.P12", {"E.1": "ATTR"}).status == "pass"
    assert _lint("ANNEX_I.E.P12", {"E.1": "OTPC"}).status == "missing"
    assert _lint("ANNEX_I.E.P12", {"E.1": "OTPC - offer to the public", "E.26": "Synthetic"}).status == "pass"
    unknown = _lint("ANNEX_I.E.P12", {"E.1": "TBD"})
    assert unknown.issues == (
        "Field E.26 (Right of withdrawal) is empty or not in the draft. Checked as required: field E.1 gives none of "
        "the template's codes.",
    )


def test_authorisation_fields_follow_the_exemption_code():
    exempt = _lint("ANNEX_II.A.P11", {"A.17": "EX16"})
    assert exempt.status == "pass"
    assert len(exempt.issues) == 3
    credit = _lint("ANNEX_II.A.P11", {"A.17": "EX17"})
    assert credit.status == "review"
    assert credit.issues[0].startswith("Field A.20 (Competent authority for credit institutions) is empty")
    authorised = {"A.17": "NOEX", "A.18": "Synthetic authorisation", "A.19": "Synthetic authority"}
    assert _lint("ANNEX_II.A.P11", authorised).status == "pass"
    # Annex III: A.25 by the template, A.26 by the Annex point.
    assert _lint("ANNEX_III.A.P13", {"A.24": "true"}).status == "pass"
    assert _lint("ANNEX_III.A.P13", {"A.24": "false", "A.25": "Synthetic", "A.26": "Synthetic"}).status == "pass"


def test_part_c_of_annex_i_applies_once_c1_names_the_operator():
    for number in range(2, 10):
        assert _lint(f"ANNEX_I.C.P{number}", {"C.1": "N/A"}).status == "pass"
        assert _lint(f"ANNEX_I.C.P{number}", {"C.1": "Synthetic Exchange GmbH"}).status in ("missing", "review")
    assert _lint("ANNEX_I.C.P1", {"C.1": "N/A"}).status == "pass"
    assert _lint("ANNEX_I.C.P1", {}).status == "missing"
    # The issue price currency applies once E.8 gives a price.
    finding = _lint("ANNEX_I.E.P4", {"E.8": "N/A", "E.11": "Synthetic", "E.10": "N/A"})
    assert finding.status == "pass"
    assert finding.issues[0].startswith("Field E.9 (Official currency or any other crypto-assets determining the issue price) is not required: field E.8 is marked not applicable;")


# --- End to end -----------------------------------------------------------------------------------------------


def _numbered(tmp_path: Path, rows: list[tuple[str, str]], regime: WhitepaperType):
    names = FIELD_NAMES[regime]
    cells = "".join(f"<tr><td>{number}</td><td>{names.get(number, '')}</td><td>{text}</td></tr>" for number, text in rows)
    path = tmp_path / "draft.xhtml"
    path.write_text(f"<html><body><table>{cells}</table></body></html>", encoding="utf-8")
    return {f.rule.rule_id: f for f in lint_whitepaper(load_whitepaper(path, regime)).findings}


def test_numbered_xhtml_drafts_of_each_table(tmp_path):
    other = _numbered(
        tmp_path,
        [("A.1", "Meadow Labs GmbH (fictional)"), ("A.6", LEI_CODE), ("A.2", "N/A"), ("B.1", "false"), ("D.1", "x")],
        OTHER,
    )
    assert other["ANNEX_I.A.P1"].status == "pass"
    assert other["ANNEX_I.A.P2"].status == "pass"
    assert other["ANNEX_I.B.P3"].status == "pass"
    assert other["ANNEX_I.A.P4"].status == "missing"
    art = _numbered(tmp_path, [("A.1", "Meadow Reserve SA (fictional)"), ("A.7", LEI_CODE), ("B.1", "x"), ("C.1", "OTPC")], ART)
    assert art["ANNEX_II.A.P5"].status == "pass"
    assert art["ANNEX_II.A.P3"].status == "pass"
    emt = _numbered(tmp_path, [("A.1", "Meadow Pay GmbH (fictional)"), ("B.12", DTI_CODE), ("C.1", "OTPC")], EMT)
    assert emt["ANNEX_III.B.P1"].status == "pass"
    assert emt["ANNEX_III.C.P1"].status == "pass"


def test_the_numbered_example_draft(tmp_path):
    root = Path(__file__).resolve().parents[1]
    report = lint_whitepaper(load_whitepaper(root / "examples" / "numbered-other-draft.xhtml", OTHER))
    findings = {f.rule.rule_id: f for f in report.findings if f.rule.rule_id in POINT_RULE_IDS}
    assert len(findings) == 73
    assert {f.status for f in findings.values()} <= {"pass", "review", "missing"}
    # No finding quotes the draft: issues name fields and conditions only.
    for finding in findings.values():
        for issue in finding.issues:
            assert re.match(r"^(Field|None of fields|This draft)", issue), issue


def test_point_definitions_have_unique_fields_per_point():
    for points in POINTS.values():
        for point in points:
            numbers = [field.number for field in point.fields]
            assert len(numbers) == len(set(numbers)), point.rule_id
            for item in point.items:
                if isinstance(item, Alternative):
                    assert len(item.fields) == 2
