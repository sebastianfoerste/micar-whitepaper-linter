#!/usr/bin/env python3
"""Render the study Markdown report from anonymized findings."""

from __future__ import annotations

from pathlib import Path

from micar_linter.study_report import main

STUDY_DIR = Path(__file__).resolve().parents[1]


if __name__ == "__main__":
    raise SystemExit(
        main(
            [
                "--findings",
                str(STUDY_DIR / "findings-anonymized.json"),
                "--out",
                str(STUDY_DIR / "findings-summary.md"),
            ]
        )
    )
