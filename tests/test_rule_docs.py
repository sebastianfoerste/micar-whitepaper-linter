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
    for rule in BUILD["all_rules"]():
        assert (ROOT / "docs" / "rules" / f"{rule.rule_id}.html").is_file()
        # A rule that runs with other settings for some regimes has examples for each variant.
        for variant, regimes in BUILD["variants"](rule.rule_id):
            examples = BUILD["examples"](variant, regimes[0])
            assert examples
            for example in examples:
                assert BUILD["lint_example"](variant, example) == example.expected, (rule.rule_id, example.title)


def test_never_pass_rules_publish_no_passing_example():
    for rule in BUILD["all_rules"]():
        for variant, regimes in BUILD["variants"](rule.rule_id):
            statuses = {e.expected for e in BUILD["examples"](variant, regimes[0])}
            if rule.rule_id in BUILD["NEVER_PASS"]:
                assert "pass" not in statuses
            else:
                assert {"missing", "pass"} <= statuses


def test_sarif_help_uri_base_matches_the_pages_location():
    assert RULE_DOCS_BASE.endswith("/micar-whitepaper-linter/rules/")


# Regression: the pages of the two rules whose citation was corrected said the citation was the
# rule's own, unchanged, and not re-verified.
def test_pages_of_corrected_citations_say_where_they_were_read():
    pages = BUILD["build_pages"]()
    for rule_id in ("ANNEX_II.G.VALUATION_AUDIT", "ANNEX_II.I"):
        page = pages[f"{rule_id}.html"]
        assert "own, unchanged" not in page, rule_id
        assert "against the Official Journal text" in page, rule_id
