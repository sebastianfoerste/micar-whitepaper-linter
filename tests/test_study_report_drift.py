from __future__ import annotations

import json
from pathlib import Path

from micar_linter.study_report import render_study_report

STUDY_DIR = Path(__file__).resolve().parents[1] / "studies" / "2026-07-title-ii-annex-i-whitepaper-study"


def test_committed_findings_summary_matches_renderer() -> None:
    payload = json.loads((STUDY_DIR / "findings-pseudonymous.json").read_text(encoding="utf-8"))
    committed = (STUDY_DIR / "findings-summary.md").read_text(encoding="utf-8")

    assert committed == render_study_report(payload), (
        "findings-summary.md is out of date; regenerate it with "
        "`uv run micar-study-report --findings "
        "studies/2026-07-title-ii-annex-i-whitepaper-study/findings-pseudonymous.json "
        "--out studies/2026-07-title-ii-annex-i-whitepaper-study/findings-summary.md`"
    )
