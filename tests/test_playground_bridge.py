"""Exercise the actual browser bridge against the same Python rules as the CLI."""

import json
import runpy
from pathlib import Path

import pytest

from micar_linter.linter import lint_whitepaper
from micar_linter.report import render_json, render_text
from micar_linter.whitepaper import load_whitepaper

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def bridge(tmp_path, monkeypatch):
    lint = runpy.run_path(str(ROOT / "docs/playground/lint.py"))["lint_draft"]
    path = tmp_path / "draft.json"
    monkeypatch.setitem(lint.__globals__, "Path", lambda _: path)
    return lint, path


@pytest.mark.parametrize("filename", ["incomplete.json", "art-stablecoin.json", "other-crypto-asset.json", "emt-token.json"])
def test_browser_reports_match_cli_reports(bridge, filename):
    lint, path = bridge
    source = ROOT / "examples" / filename
    result = json.loads(lint(source.read_text()))
    expected = lint_whitepaper(load_whitepaper(source))
    assert result["report"] == json.loads(render_json(expected))
    assert result["text"] == render_text(expected)
    assert not path.exists()


def test_browser_retains_lawyer_review_and_ignores_draft_authored_validation(bridge):
    lint, _ = bridge
    draft = json.loads((ROOT / "examples/art-stablecoin.json").read_text())
    draft.update(ixbrl_validated=True, reserve_characterisation_reviewed_by="Self-certified")
    findings = json.loads(lint(json.dumps(draft)))["report"]["findings"]
    indexed = {finding["rule_id"]: finding for finding in findings}
    assert indexed["COMMON.IXBRL_TAGGING"]["status"] != "pass"
    assert indexed["ANNEX_II.G.DEPOSIT_FLOOR_REVIEW"]["status"] == "review"


def test_browser_cleans_up_draft_after_parser_failure(bridge):
    lint, path = bridge
    with pytest.raises(SystemExit):
        lint('{"sections": null}')
    assert not path.exists()


def test_bundled_samples_match_canonical_examples():
    builder = runpy.run_path(str(ROOT / "scripts/build_playground_samples.py"))
    assert (ROOT / "docs/playground/samples.json").read_text() == builder["build_samples"]()
