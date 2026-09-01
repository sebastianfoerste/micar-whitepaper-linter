"""Reserve disclosure and the substantive deposit floor are separate questions.

Disclosure completeness is checked against Annex II Part G. The minimum deposit
share under Art. 36(4)(d) MiCAR depends on facts the text does not establish, so
it may never be concluded automatically.
"""

import json
from pathlib import Path

import pytest

from micar_linter.linter import Linter
from micar_linter.rules import RULESETS
from micar_linter.whitepaper import load_whitepaper

DISCLOSURE = "ANNEX_II.G.COMPOSITION_DISCLOSURE"
FLOOR = "ANNEX_II.G.DEPOSIT_FLOOR_REVIEW"

RESERVE_TEXT = (
    "The reserve of assets is segregated and its composition is described in full. "
    "The reserve is held as deposits with credit institutions, with concentration "
    "limits applied per counterparty. At least 30% of the reserve is held as "
    "deposits. Valuation is performed daily and audited semi-annually. "
    "Custody arrangements provide for segregation and insolvency protection of the "
    "reserve assets held by the appointed custodian."
)

RESERVE_TEXT_60 = RESERVE_TEXT.replace("At least 30%", "At least 60%")


def _art(tmp_path: Path, reserve_text: str, **metadata) -> Path:
    payload = {
        "title": "Test ART",
        "type": "art",
        "sections": {
            "reserve_of_assets": reserve_text,
            "summary": "An asset-referenced token with a stabilisation mechanism.",
        },
    }
    payload.update(metadata)
    path = tmp_path / "art.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _finding(path: Path, rule_id: str):
    whitepaper = load_whitepaper(path)
    for finding in Linter(RULESETS[whitepaper.type]).lint(whitepaper):
        if finding.rule.rule_id == rule_id:
            return finding
    raise AssertionError(f"{rule_id} was not applied")


def test_both_rules_exist_and_are_separate():
    rules = {r.rule_id for ruleset in RULESETS.values() for r in ruleset}
    assert DISCLOSURE in rules
    assert FLOOR in rules
    assert "ANNEX_II.G.COMPOSITION" not in rules
    assert "ANNEX_II.G.CUSTODY" in rules


def test_disclosure_rule_does_not_demand_a_percentage(tmp_path: Path):
    """Disclosure completeness must not hinge on a hard-coded threshold."""
    text = RESERVE_TEXT.replace(
        "At least 30% of the reserve is held as deposits. ",
        "A share of the reserve is held as deposits with authorised credit "
        "institutions in accordance with the reserve policy. ",
    )
    finding = _finding(_art(tmp_path, text), DISCLOSURE)
    assert finding.status == "pass"


def test_unknown_characterisation_yields_review_not_pass(tmp_path: Path):
    finding = _finding(_art(tmp_path, RESERVE_TEXT), FLOOR)
    assert finding.status == "review"
    assert "references_official_currency" in finding.issues[0]
    assert "art_significant" in finding.issues[0]


def test_partial_characterisation_still_yields_review(tmp_path: Path):
    finding = _finding(
        _art(tmp_path, RESERVE_TEXT, references_official_currency=True), FLOOR
    )
    assert finding.status == "review"
    assert "art_significant" in finding.issues[0]


def test_non_significant_art_uses_the_thirty_percent_floor(tmp_path: Path):
    path = _art(
        tmp_path, RESERVE_TEXT, references_official_currency=True, art_significant=False
    )
    assert _finding(path, FLOOR).status == "pass"


def test_significant_art_requires_the_sixty_percent_floor(tmp_path: Path):
    """A significant ART disclosing only 30% must not pass."""
    path = _art(
        tmp_path, RESERVE_TEXT, references_official_currency=True, art_significant=True
    )
    finding = _finding(path, FLOOR)
    assert finding.status == "missing"
    assert "60%" in finding.issues[0]


def test_significant_art_passes_when_it_discloses_sixty(tmp_path: Path):
    path = _art(
        tmp_path,
        RESERVE_TEXT_60,
        references_official_currency=True,
        art_significant=True,
    )
    assert _finding(path, FLOOR).status == "pass"


def test_non_currency_referencing_art_is_referred_to_review(tmp_path: Path):
    path = _art(
        tmp_path, RESERVE_TEXT, references_official_currency=False, art_significant=False
    )
    finding = _finding(path, FLOOR)
    assert finding.status == "review"
    assert "official currency" in finding.issues[0]


@pytest.mark.parametrize("significant", [True, False])
def test_floor_is_blocker_severity(tmp_path: Path, significant: bool):
    path = _art(
        tmp_path,
        RESERVE_TEXT,
        references_official_currency=True,
        art_significant=significant,
    )
    assert _finding(path, FLOOR).rule.severity.name == "BLOCKER"
