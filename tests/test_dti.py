"""COMMON.DTI_FORMAT: the ISO 24165 Digital Token Identifiers of Art. 3 of Delegated Regulation (EU) 2025/421.

Where a DTI is provided, the white paper is identified by the type 3 DTI of the functionally fungible group
(Art. 3(1)) and each crypto-asset by its own DTI (Art. 3(2)); where none is available, by an identifier
approved by ESMA (Art. 3(3)). Fields F.13/F.14 (Table 2), B.15/B.16 (Table 3) and B.12/B.13 (Table 4) of
Implementing Regulation (EU) 2024/2984 carry the two codes, and its Table 1 gives {DTI} as 9 alphanumerical
characters (both OJ texts read on 2026-11-10). The codes below are synthetic; none is a registered DTI.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from micar_linter.dti import DTI_FIELDS, field_codes, labelled_codes
from micar_linter.linter import lint_whitepaper
from micar_linter.rules import RULESETS
from micar_linter.template_fields import FIELD_NAMES
from micar_linter.whitepaper import WhitepaperType, load_whitepaper

OTHER = WhitepaperType.OTHER
ART = WhitepaperType.ART
EMT = WhitepaperType.EMT
RULE_ID = "COMMON.DTI_FORMAT"

# Synthetic codes of the {DTI} shape.
ASSET = "SYNTHDTI1"
ASSET_2 = "SYNTHDTI2"
GROUP = "SYNTHFFG1"

SECTION = {OTHER: "crypto_asset", ART: "art", EMT: "emt"}
NO_DTI = (
    "No ISO 24165 Digital Token Identifier (DTI) is given. Where no DTI is available, Art. 3(3) of "
    "Delegated Regulation (EU) 2025/421 asks for a digital token identifier approved by ESMA at Union level."
)


def _finding(report):
    return next(finding for finding in report.findings if finding.rule.rule_id == RULE_ID)


def _json(tmp_path: Path, regime: WhitepaperType, text: str | None, language: str | None = None):
    sections = {} if text is None else {SECTION[regime]: text}
    draft: dict[str, object] = {"title": "Synthetic draft", "type": regime.value, "sections": sections}
    if language:
        draft["language"] = language
    path = tmp_path / "draft.json"
    path.write_text(json.dumps(draft), encoding="utf-8")
    return _finding(lint_whitepaper(load_whitepaper(path)))


def _numbered(tmp_path: Path, regime: WhitepaperType, dti: str, ffg: str):
    names = FIELD_NAMES[regime]
    dti_number, ffg_number = DTI_FIELDS[regime]
    rows = [(number, "Synthetic answer of the fictional issuer.") for number in ("A.1", "C.1", "D.1", "E.1")]
    rows += [(dti_number, dti), (ffg_number, ffg)]
    cells = "".join(
        f"<tr><td>{number}</td><td>{names.get(number, '')}</td><td>{text}</td></tr>" for number, text in rows
    )
    path = tmp_path / "draft.xhtml"
    path.write_text(f"<html><body><table>{cells}</table></body></html>", encoding="utf-8")
    return _finding(lint_whitepaper(load_whitepaper(path, regime)))


def test_every_regime_runs_its_own_variant():
    for regime, rules in RULESETS.items():
        variants = [rule for rule in rules if rule.rule_id == RULE_ID]
        assert len(variants) == 1
        assert variants[0].section == SECTION[regime]
        assert "VO (EU) 2025/421" in variants[0].citation


def test_the_fields_are_the_template_fields_that_name_the_codes():
    for regime, (dti_number, ffg_number) in DTI_FIELDS.items():
        assert FIELD_NAMES[regime][dti_number].startswith("Digital token identifier code")
        assert FIELD_NAMES[regime][ffg_number].startswith("Functionally fungible group digital token identifier")


@pytest.mark.parametrize(
    ("answer", "codes", "other"),
    [
        (ASSET, [ASSET], False),
        (f"{ASSET}, {ASSET_2}", [ASSET, ASSET_2], False),
        (f"{ASSET}\n{ASSET_2}", [ASSET, ASSET_2], False),
        (f"DTI: {ASSET}", [ASSET], False),
        ("N/A", [], False),
        ("TBD", [], False),
        ("", [], False),
        ("SYNTHDTI", [], True),  # 8 characters
        ("SYNTHDTI12", [], True),  # 10 characters
        ("SYNTH-DT1", [], True),
        (f"{ASSET} (Ethereum)", [ASSET], True),
    ],
)
def test_field_codes(answer, codes, other):
    assert field_codes(answer) == (codes, other)


def test_labelled_codes_tell_the_group_from_the_asset():
    assert labelled_codes(f"The token has the DTI {ASSET} and the FFG DTI {GROUP}.") == ([ASSET], [GROUP], set())
    assert labelled_codes(
        f"Digital Token Identifier (DTI): {ASSET}. Functionally fungible group (FFG): {GROUP}"
    ) == ([ASSET], [GROUP], set())
    assert labelled_codes("No DTI has been assigned to the token yet.") == ([], [], {"dti"})
    assert labelled_codes("The token runs on a public network.") == ([], [], set())


@pytest.mark.parametrize("regime", [OTHER, ART, EMT])
def test_a_numbered_draft_passes_with_both_codes(tmp_path, regime):
    finding = _numbered(tmp_path, regime, ASSET, GROUP)
    assert (finding.status, finding.issues) == ("pass", ())


@pytest.mark.parametrize("regime", [OTHER, ART, EMT])
def test_empty_fields_go_to_review_not_missing(tmp_path, regime):
    finding = _numbered(tmp_path, regime, "N/A", "")
    assert (finding.status, finding.issues) == ("review", (NO_DTI,))


def test_each_missing_half_is_named(tmp_path):
    no_group = _numbered(tmp_path, OTHER, ASSET, "N/A")
    assert no_group.status == "review"
    assert no_group.issues == (
        "A DTI is given but no DTI of type 3 for the functionally fungible group (FFG DTI); Art. 3(1) of "
        "Delegated Regulation (EU) 2025/421 asks for it where a DTI is provided.",
    )
    no_asset = _numbered(tmp_path, OTHER, "N/A", GROUP)
    assert no_asset.status == "review"
    assert "Art. 3(2)" in no_asset.issues[0]


def test_a_malformed_field_names_the_field_and_quotes_no_draft_text(tmp_path):
    finding = _numbered(tmp_path, OTHER, "SYNTHDTI", GROUP)
    assert finding.status == "review"
    assert finding.issues == (
        f"Field F.13 ({FIELD_NAMES[OTHER]['F.13']}) holds text other than codes of 9 alphanumerical characters "
        "(the {DTI} format of Implementing Regulation (EU) 2024/2984).",
    )
    assert not any("SYNTHDTI" in issue for issue in finding.issues)


def test_more_than_one_group_code_goes_to_review(tmp_path):
    finding = _numbered(tmp_path, ART, ASSET, f"{GROUP}, SYNTHFFG2")
    assert finding.status == "review"
    assert finding.issues[0].startswith("More than one FFG DTI is given")


@pytest.mark.parametrize("regime", [OTHER, ART, EMT])
def test_a_draft_without_field_numbers_is_read_after_the_labels(tmp_path, regime):
    passing = _json(tmp_path, regime, f"The crypto-asset has the DTI {ASSET}; its FFG DTI is {GROUP}.")
    assert (passing.status, passing.issues) == ("pass", ())
    assert _json(tmp_path, regime, "The token runs on a public network.").issues == (NO_DTI,)
    assert _json(tmp_path, regime, None).status == "missing"
    assert _json(tmp_path, regime, "TBD").status == "missing"


def test_prose_after_a_label_goes_to_review(tmp_path):
    finding = _json(tmp_path, OTHER, "No DTI has been assigned to the token yet.")
    assert finding.status == "review"
    assert finding.issues == (
        "A DTI label is not followed by a code of 9 alphanumerical characters "
        "(the {DTI} format of Implementing Regulation (EU) 2024/2984).",
    )


def test_german_drafts_get_german_findings(tmp_path):
    finding = _json(tmp_path, OTHER, "Der Token ist auf einem öffentlichen Netzwerk ausgegeben.", language="de")
    assert finding.status == "review"
    assert finding.issues[0].startswith("Kein Digital Token Identifier (DTI) nach ISO 24165 angegeben.")
    passing = _json(tmp_path, OTHER, f"DTI: {ASSET}. FFG DTI: {GROUP}.", language="de")
    assert passing.status == "pass"
