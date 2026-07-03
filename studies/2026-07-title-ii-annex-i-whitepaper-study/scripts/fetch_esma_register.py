#!/usr/bin/env python3
"""Fetch or normalize the ESMA Title II register into the study manifest."""

from __future__ import annotations

from pathlib import Path

from micar_linter.esma_register import OFFICIAL_TITLE_II_CSV, main

STUDY_DIR = Path(__file__).resolve().parents[1]


if __name__ == "__main__":
    raise SystemExit(
        main(
            [
                "--csv",
                OFFICIAL_TITLE_II_CSV,
                "--out",
                str(STUDY_DIR / "source-manifest.json"),
                "--sample-csv",
                str(STUDY_DIR / "sample-manifest.csv"),
            ]
        )
    )
