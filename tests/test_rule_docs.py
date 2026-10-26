"""The rule pages in docs/rules/ are generated; they must match the rule set."""

import runpy
from pathlib import Path

from micar_linter.ci_outputs import RULE_DOCS_BASE

ROOT = Path(__file__).resolve().parents[1]
BUILD = runpy.run_path(str(ROOT / "scripts" / "build_rule_docs.py"))


def test_committed_rule_pages_are_current():
    pages = BUILD["build_pages"]()
    committed = {path.name for path in (ROOT / "docs" / "rules").glob("*.html")}
    assert committed == set(pages), "run: uv run python scripts/build_rule_docs.py"
    for name, text in pages.items():
        assert (ROOT / "docs" / "rules" / name).read_text(encoding="utf-8") == text, (
            f"docs/rules/{name} is stale; run: uv run python scripts/build_rule_docs.py"
        )


def test_every_rule_has_a_page_and_tested_examples():
    regimes = BUILD["regimes_by_rule"]()
    for rule in BUILD["all_rules"]():
        assert (ROOT / "docs" / "rules" / f"{rule.rule_id}.html").is_file()
        examples = BUILD["examples"](rule, regimes[rule.rule_id][0])
        assert examples
        for example in examples:
            assert BUILD["lint_example"](rule, example) == example.expected, (rule.rule_id, example.title)


def test_never_pass_rules_publish_no_passing_example():
    regimes = BUILD["regimes_by_rule"]()
    for rule in BUILD["all_rules"]():
        statuses = {e.expected for e in BUILD["examples"](rule, regimes[rule.rule_id][0])}
        if rule.rule_id in BUILD["NEVER_PASS"]:
            assert "pass" not in statuses
        else:
            assert {"missing", "pass"} <= statuses


def test_sarif_help_uri_base_matches_the_pages_location():
    assert RULE_DOCS_BASE.endswith("/micar-whitepaper-linter/rules/")
