#!/usr/bin/env python3
"""Run the local cached white papers through the study batch runner."""

from __future__ import annotations

from pathlib import Path

from micar_linter.batch import main_study_batch

STUDY_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = STUDY_DIR.parents[1]


if __name__ == "__main__":
    raise SystemExit(
        main_study_batch(
            [
                "--manifest",
                str(STUDY_DIR / "source-manifest.json"),
                "--cache",
                str(REPO_ROOT / ".study-cache" / "title-ii-whitepapers"),
                "--annex",
                "annex-i",
                "--out",
                str(STUDY_DIR / "findings-anonymized.json"),
            ]
        )
    )
