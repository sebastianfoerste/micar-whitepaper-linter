#!/usr/bin/env python3
"""Normalize a local candidate CSV into the study sample manifest."""

from __future__ import annotations

import argparse
from pathlib import Path

from micar_linter.esma_register import main

STUDY_DIR = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default=str(STUDY_DIR / "sample-manifest.csv"))
    parser.add_argument("--sample-method", choices=["first", "random"], default="first")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(
        main(
            [
                "--csv",
                args.csv,
                "--out",
                str(STUDY_DIR / "source-manifest.json"),
                "--sample-csv",
                str(STUDY_DIR / "sample-manifest.csv"),
                "--sample-method",
                args.sample_method,
            ]
        )
    )
