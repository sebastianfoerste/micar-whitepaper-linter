import re
from pathlib import Path

import pytest

from micar_linter.rules import RULESETS
from micar_linter.rules.base import Rule


def test_rulesets_compile_patterns():
    for _wp_type, rules in RULESETS.items():
        assert len(rules) > 0
        for rule in rules:
            assert isinstance(rule, Rule)
            assert rule.rule_id
            assert rule.citation
            assert rule.section

            for pattern in rule.required_patterns:
                try:
                    re.compile(pattern)
                except re.error as exc:
                    pytest.fail(
                        f"Invalid required_pattern '{pattern}' in rule {rule.rule_id}: {exc}"
                    )

            for pattern in rule.prohibited_patterns:
                try:
                    re.compile(pattern)
                except re.error as exc:
                    pytest.fail(
                        f"Invalid prohibited_pattern '{pattern}' in rule {rule.rule_id}: {exc}"
                    )


def test_every_rule_carries_a_pinpoint_citation():
    for _wp_type, rules in RULESETS.items():
        for rule in rules:
            assert rule.citation.strip(), rule.rule_id
            assert any(token in rule.citation for token in ("Art.", "Anhang"))


def test_project_metadata_points_to_current_repository():
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert "github.com/sebastianfoerste/micar-whitepaper-linter" in pyproject
    assert "github.com/sebastianforste/micar-whitepaper-linter" not in pyproject
