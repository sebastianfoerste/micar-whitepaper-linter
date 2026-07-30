from copy import deepcopy

import pytest

from micar_linter.rule_provenance import (
    OFFICIAL_SOURCES,
    _validate,
    build_rule_change_impact,
    build_rule_provenance_manifest,
)


def test_every_ruleset_entry_is_bound_to_an_official_source():
    manifest = build_rule_provenance_manifest()
    coverage = manifest["coverage"]

    assert manifest["schema"] == "micar-whitepaper-linter.rule-provenance.v1"
    assert coverage["ruleset_entries"] > 0
    assert coverage["mapped_entries"] == coverage["ruleset_entries"]
    assert coverage["unmapped_entries"] == 0
    assert manifest["unmapped"] == []
    assert all(entry["source_id"] in OFFICIAL_SOURCES for entry in manifest["entries"])
    assert all(len(entry["rule_sha256"]) == 64 for entry in manifest["entries"])
    assert len(manifest["overall_digest"]) == 64
    assert manifest["external_actions_allowed"] is False


def test_ixbrl_rule_uses_the_implementing_regulation():
    manifest = build_rule_provenance_manifest()
    ixbrl_entries = [
        entry
        for entry in manifest["entries"]
        if entry["rule_id"] == "COMMON.IXBRL_TAGGING"
    ]

    assert len(ixbrl_entries) == 3
    assert {entry["source_id"] for entry in ixbrl_entries} == {"EU-2024-2984"}


def test_manifest_is_deterministic():
    assert build_rule_provenance_manifest() == build_rule_provenance_manifest()


def test_validation_fails_closed_on_unmapped_rule():
    manifest = deepcopy(build_rule_provenance_manifest())
    manifest["coverage"]["unmapped_entries"] = 1
    manifest["unmapped"] = ["other:EXAMPLE.UNMAPPED"]

    with pytest.raises(ValueError, match="unmapped rules"):
        _validate(manifest)


def test_rule_change_impact_is_stable_for_identical_ledgers():
    manifest = build_rule_provenance_manifest()

    impact = build_rule_change_impact(manifest, manifest)

    assert impact["status"] == "STABLE"
    assert impact["summary"]["added"] == 0
    assert impact["summary"]["removed"] == 0
    assert impact["summary"]["changed"] == 0
    assert len(impact["impact_sha256"]) == 64


def test_rule_change_impact_blocks_changed_blocker_rule():
    previous = build_rule_provenance_manifest()
    current = deepcopy(previous)
    blocker = next(
        entry for entry in current["entries"] if entry["severity"] == "BLOCKER"
    )
    blocker["citation"] = blocker["citation"] + " (review candidate)"
    blocker["rule_sha256"] = "0" * 64

    impact = build_rule_change_impact(previous, current)

    assert impact["status"] == "BLOCKED_PENDING_LEGAL_REVIEW"
    assert impact["summary"]["blocker_rules_touched"] is True
    assert impact["summary"]["source_mapping_changed"] is True
    assert impact["changed"][0]["rule_id"] == blocker["rule_id"]
    assert impact["external_actions_allowed"] is False
