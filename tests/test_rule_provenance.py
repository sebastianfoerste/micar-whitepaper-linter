from copy import deepcopy

import pytest

from micar_linter.rule_provenance import (
    OFFICIAL_SOURCES,
    _validate,
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
