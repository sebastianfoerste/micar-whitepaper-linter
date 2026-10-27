"""Exercise the actual browser bridge against the same Python rules as the CLI."""

import base64
import gzip
import json
import runpy
from pathlib import Path

import pytest

from micar_linter.linter import lint_whitepaper
from micar_linter.report import render_json, render_text
from micar_linter.whitepaper import VIEWER_PAGE_NOTE, WhitepaperType, load_whitepaper

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def bridge(tmp_path, monkeypatch):
    lint = runpy.run_path(str(ROOT / "docs/playground/lint.py"))["lint_draft"]
    workdir = tmp_path / "work"
    monkeypatch.setitem(lint.__globals__, "WORKDIR", workdir)
    return lint, workdir


@pytest.mark.parametrize(
    "filename", ["incomplete.json", "art-stablecoin.json", "other-crypto-asset.json", "emt-token.json"]
)
def test_browser_reports_match_cli_reports(bridge, filename):
    lint, workdir = bridge
    source = ROOT / "examples" / filename
    result = json.loads(lint(source.read_text()))
    expected = lint_whitepaper(load_whitepaper(source))
    assert result["report"] == json.loads(render_json(expected))
    assert result["text"] == render_text(expected)
    assert not list(workdir.iterdir())


def test_browser_xhtml_report_matches_cli_report_for_the_stated_regime(bridge):
    lint, workdir = bridge
    source = ROOT / "examples" / "numbered-other-draft.xhtml"
    result = json.loads(lint(source.read_text(), "xhtml", "other", "../../numbered-other-draft.xhtml"))
    expected = lint_whitepaper(load_whitepaper(source, WhitepaperType.OTHER))
    assert result["report"] == json.loads(render_json(expected))
    assert result["report"]["title"] == "Numbered Other Draft"
    assert not list(workdir.iterdir())


def test_browser_never_infers_the_regime_of_an_xhtml_draft(bridge):
    lint, _ = bridge
    source = ROOT / "examples" / "numbered-other-draft.xhtml"
    with pytest.raises(ValueError):
        lint(source.read_text(), "xhtml", "", "draft.xhtml")


def test_browser_retains_lawyer_review_and_ignores_draft_authored_validation(bridge):
    lint, _ = bridge
    draft = json.loads((ROOT / "examples/art-stablecoin.json").read_text())
    draft.update(ixbrl_validated=True, reserve_characterisation_reviewed_by="Self-certified")
    findings = json.loads(lint(json.dumps(draft)))["report"]["findings"]
    indexed = {finding["rule_id"]: finding for finding in findings}
    assert indexed["COMMON.IXBRL_TAGGING"]["status"] != "pass"
    assert indexed["ANNEX_II.G.DEPOSIT_FLOOR_REVIEW"]["status"] == "review"


def test_browser_cleans_up_draft_after_parser_failure(bridge):
    lint, workdir = bridge
    assert "sections" in json.loads(lint('{"sections": null}'))["error"]
    assert not list(workdir.iterdir())


def _viewer_page(payload: bytes) -> str:
    # A saved iXBRL viewer page writes its packed white paper into itself when a browser runs the script.
    literal = base64.b64encode(payload).decode()
    return (
        f'<html><body><div>Loading document...</div><script>const b64 = "{literal}";'
        f" /* {'viewer runtime ' * 800}*/</script></body></html>"
    )


def test_browser_explains_a_viewer_page_it_cannot_unpack(bridge):
    lint, workdir = bridge
    error = json.loads(lint(_viewer_page(bytes(15_000)), "xhtml", "emt", "example-viewer.html"))["error"]
    assert error.startswith("example-viewer.html holds no white paper text that can be read")
    assert not list(workdir.iterdir())


@pytest.mark.parametrize(
    ("imported", "named"),
    [("example-viewer.HTML", "example-viewer.HTML"), ("example-viewer.htm", "example-viewer.html")],
)
def test_browser_names_an_html_import_as_imported(bridge, imported, named):
    lint, workdir = bridge
    error = json.loads(lint(_viewer_page(bytes(15_000)), "xhtml", "emt", imported))["error"]
    assert error.startswith(f"{named} holds no white paper text")
    assert not list(workdir.iterdir())


def test_browser_unpacks_a_viewer_page_like_the_cli(bridge, tmp_path):
    lint, workdir = bridge
    page = _viewer_page(gzip.compress((ROOT / "examples" / "numbered-other-draft.xhtml").read_bytes()))
    result = json.loads(lint(page, "xhtml", "other", "example-viewer.html"))
    source = tmp_path / "example-viewer.html"
    source.write_text(page, encoding="utf-8")
    expected = lint_whitepaper(load_whitepaper(source, WhitepaperType.OTHER))
    assert result["report"] == json.loads(render_json(expected))
    assert result["report"]["warnings"][0] == VIEWER_PAGE_NOTE
    assert str(workdir) not in json.dumps(result)
    assert not list(workdir.iterdir())


def test_browser_refuses_a_viewer_page_over_the_unpacking_limit(bridge):
    lint, workdir = bridge
    markup = b"<html><body><p>" + b" " * (8 * 1024 * 1024) + b"</p></body></html>"
    error = json.loads(lint(_viewer_page(gzip.compress(markup)), "xhtml", "other", "example-viewer.html"))["error"]
    assert error.startswith("example-viewer.html is a saved iXBRL viewer page")
    assert "more than 8 MB" in error
    assert "Traceback" not in error and str(workdir) not in error
    assert not list(workdir.iterdir())


def test_bundled_samples_match_canonical_examples():
    builder = runpy.run_path(str(ROOT / "scripts/build_playground_samples.py"))
    assert (ROOT / "docs/playground/samples.json").read_text() == builder["build_samples"]()
    assert (ROOT / "docs/playground/sample-numbered.xhtml").read_text() == builder["build_xhtml_sample"]()
