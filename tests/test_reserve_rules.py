"""Reserve disclosure and the substantive deposit floor are separate questions.

Disclosure completeness is checked against Annex II Part G. The minimum deposit
share under Articles 35(4), 36(4)(d), and 45(7)(b) MiCAR depends on legal facts
that draft text and metadata cannot establish. The substantive rule never passes
automatically.
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


def _floor(tmp_path: Path, text: str = RESERVE_TEXT, **metadata):
    return _finding(_art(tmp_path, text, **metadata), FLOOR)


def test_both_rules_exist_and_are_separate():
    rules = {rule.rule_id for ruleset in RULESETS.values() for rule in ruleset}
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


def test_unknown_characterisation_yields_review(tmp_path: Path):
    finding = _floor(tmp_path)
    assert finding.status == "review"
    assert "references_official_currency" in finding.issues[0]
    assert "art_significant" in finding.issues[0]


def test_partial_characterisation_still_yields_review(tmp_path: Path):
    finding = _floor(tmp_path, references_official_currency=True)
    assert finding.status == "review"
    assert "art_significant" in finding.issues[0]


@pytest.mark.parametrize("references_currency", [True, False])
@pytest.mark.parametrize("significant", [True, False])
@pytest.mark.parametrize("authority_requires_45_7b", [True, False])
def test_every_boolean_characterisation_combination_never_passes(
    tmp_path: Path,
    references_currency: bool,
    significant: bool,
    authority_requires_45_7b: bool,
):
    finding = _floor(
        tmp_path,
        references_official_currency=references_currency,
        art_significant=significant,
        article_45_7b_required_by_authority=authority_requires_45_7b,
    )
    assert finding.status == "review"


@pytest.mark.parametrize("value", [None, 1, "true", {}, [], " "])
@pytest.mark.parametrize("field", ["references_official_currency", "art_significant"])
def test_malformed_primary_characterisation_yields_review(tmp_path: Path, field: str, value: object):
    metadata = {
        "references_official_currency": True,
        "art_significant": True,
        field: value,
    }
    finding = _floor(tmp_path, **metadata)
    assert finding.status == "review"
    assert field in finding.issues[0]


@pytest.mark.parametrize("value", [None, 1, "false", {}, [], " "])
def test_malformed_authority_characterisation_yields_review(tmp_path: Path, value: object):
    finding = _floor(
        tmp_path,
        references_official_currency=True,
        art_significant=False,
        article_45_7b_required_by_authority=value,
    )
    assert finding.status == "review"
    assert "article_45_7b_required_by_authority" in finding.issues[0]


def test_non_significant_art_uses_thirty_percent_candidate_floor(tmp_path: Path):
    finding = _floor(
        tmp_path,
        references_official_currency=True,
        art_significant=False,
        article_45_7b_required_by_authority=False,
    )
    assert finding.status == "review"
    assert "30% candidate floor" in finding.issues[0]
    assert "Art. 36(4)(d)" in finding.issues[0]


def test_authority_required_article_45_uses_sixty_percent_candidate_floor(
    tmp_path: Path,
):
    finding = _floor(
        tmp_path,
        text=RESERVE_TEXT_60,
        references_official_currency=True,
        art_significant=False,
        article_45_7b_required_by_authority=True,
    )
    assert finding.status == "review"
    assert "60% candidate floor" in finding.issues[0]
    assert "Arts. 35(4) and 45(7)(b)" in finding.issues[0]


def test_significant_art_identifies_sixty_percent_candidate_floor(tmp_path: Path):
    finding = _floor(
        tmp_path,
        text=RESERVE_TEXT_60,
        references_official_currency=True,
        art_significant=True,
    )
    assert finding.status == "review"
    assert "60% candidate floor" in finding.issues[0]
    assert "Art. 45(7)(b)" in finding.issues[0]


def test_missing_percentage_is_reported_when_floor_can_be_identified(tmp_path: Path):
    text = RESERVE_TEXT.replace(
        "At least 30% of the reserve is held as deposits. ",
        "A share of the reserve is held as deposits. ",
    )
    finding = _floor(
        tmp_path,
        text=text,
        references_official_currency=True,
        art_significant=False,
        article_45_7b_required_by_authority=False,
    )
    assert finding.status == "missing"
    assert "No deposit-share percentage was detected" in finding.issues[0]
    assert "30% candidate floor" in finding.issues[0]


def test_non_currency_referencing_art_is_referred_to_review(tmp_path: Path):
    finding = _floor(
        tmp_path,
        references_official_currency=False,
        art_significant=False,
    )
    assert finding.status == "review"
    assert "draft asserts" in finding.issues[0]
    assert "lawyer confirmation" in finding.issues[0]


@pytest.mark.parametrize(
    ("percentage", "expected_candidate"),
    [
        ("30%", "30%"),
        ("30 %", "30%"),
        ("30.0%", "30.0%"),
        ("30,0 %", "30,0%"),
        ("40%", "40%"),
        ("70%", "70%"),
    ],
)
def test_percentage_formats_remain_review_candidates(
    tmp_path: Path, percentage: str, expected_candidate: str
):
    text = RESERVE_TEXT.replace("30%", percentage)
    finding = _floor(
        tmp_path,
        text=text,
        references_official_currency=True,
        art_significant=False,
        article_45_7b_required_by_authority=False,
    )
    assert finding.status == "review"
    assert f"detected: {expected_candidate}" in finding.issues[0]


@pytest.mark.parametrize(
    "statement",
    [
        "We do not hold 60% of the reserve as deposits.",
        "The required 30% threshold is not met.",
        "Less than 30% of the reserve is held as deposits.",
        "Up to 60% of the reserve may be held as deposits.",
        "Historically, 60% of the reserve was held as deposits.",
        "The issuer may hold 30% if the policy changes.",
        "Thirty percent of another portfolio equals 30%.",
        "At least 130% is held as deposits.",
        "At least 160% is held as deposits.",
    ],
)
def test_ambiguous_or_noncompliant_statements_never_pass(tmp_path: Path, statement: str):
    finding = _floor(
        tmp_path,
        text=statement,
        references_official_currency=True,
        art_significant=True,
    )
    assert finding.status == "review"


@pytest.mark.parametrize("value", [None, True, 7, {"attacker": True}, [0], "Reviewer"])
def test_draft_supplied_reviewer_provenance_has_no_effect(tmp_path: Path, value: object):
    path = _art(
        tmp_path,
        RESERVE_TEXT_60,
        references_official_currency=True,
        art_significant=True,
        reserve_characterisation_reviewed_by=value,
        reserve_characterisation_reviewed_on=value,
    )
    whitepaper = load_whitepaper(path)
    assert "reserve_characterisation_reviewed_by" not in whitepaper.metadata
    assert "reserve_characterisation_reviewed_on" not in whitepaper.metadata
    assert _finding(path, FLOOR).status == "review"


def test_german_message_identifies_lawyer_review(tmp_path: Path):
    finding = _floor(
        tmp_path,
        text=RESERVE_TEXT_60,
        language="de",
        references_official_currency=True,
        art_significant=True,
    )
    assert finding.status == "review"
    assert "Art. 45 Abs. 7 Buchst. b" in finding.issues[0]
    assert "Jurist" in finding.issues[0]


@pytest.mark.parametrize("significant", [True, False])
def test_floor_is_blocker_severity(tmp_path: Path, significant: bool):
    metadata = {
        "references_official_currency": True,
        "art_significant": significant,
    }
    if not significant:
        metadata["article_45_7b_required_by_authority"] = False
    assert _floor(tmp_path, **metadata).rule.severity.name == "BLOCKER"


def test_generated_sample_artifacts_never_mark_floor_as_pass():
    repository = Path(__file__).resolve().parents[1]
    review_table = json.loads(
        (repository / "examples/review-bundle/review-table.json").read_text(encoding="utf-8")
    )
    floor_row = next(row for row in review_table["rows"] if row["rule_id"] == FLOOR)
    assert floor_row["status"] == "review"

    sample_report = (repository / "reports/sample-art-pass.txt").read_text(encoding="utf-8")
    floor_line = next(line for line in sample_report.splitlines() if FLOOR in line)
    assert floor_line.startswith("[REVIEW]")
