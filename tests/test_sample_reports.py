"""The sample reports are real CLI output; nothing regenerates them automatically, so a report or rule
change can silently leave them showing old text or the old citation style."""

import runpy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RERUN = "run `make sample-reports` and commit the result"


@pytest.fixture(scope="module")
def builder():
    return runpy.run_path(str(ROOT / "scripts/build_sample_reports.py"))


def test_sample_reports_match_current_cli_output(builder):
    for path, expected in builder["build_reports"]().items():
        assert (ROOT / path).read_text(encoding="utf-8") == expected, f"{path} is stale; {RERUN}"


def test_sample_review_bundle_doc_shows_current_cli_output(builder):
    doc = builder["BUNDLE_DOC"]
    assert (ROOT / doc).read_text(encoding="utf-8") == builder["build_bundle_doc"](), (
        f"{doc} is stale; {RERUN}"
    )
