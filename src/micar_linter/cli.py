"""Command-line interface."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from micar_linter import __version__
from micar_linter.linter import lint_whitepaper
from micar_linter.report import render_audit_log, render_json, render_text
from micar_linter.whitepaper import load_whitepaper


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="micar-lint",
        description=(
            "Deterministic first-pass linter for MiCAR crypto-asset white paper drafts. "
            "Reads a JSON draft, applies the rule set keyed to the whitepaper type "
            "(other / ART / EMT), and prints a structured review report with pinpoint "
            "citations to MiCAR articles and annexes. Not legal advice."
        ),
    )
    parser.add_argument("path", type=Path, help="Path to a whitepaper draft file.")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of text.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with status 1 if any BLOCKER-severity finding is open.",
    )
    parser.add_argument(
        "--lang",
        choices=["en", "de", "auto"],
        default="auto",
        help="Force a specific document language for rule matching (default: auto).",
    )
    parser.add_argument(
        "--audit-log",
        type=Path,
        help="Path to write a compliance audit log markdown file.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"micar-lint {__version__}",
    )
    return parser


def calculate_sha256(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return "unknown"


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    whitepaper = load_whitepaper(args.path)
    if args.lang != "auto":
        whitepaper.metadata["language"] = args.lang

    report = lint_whitepaper(whitepaper)

    if args.json:
        print(render_json(report))
    else:
        print(render_text(report))

    if args.audit_log:
        sha256 = calculate_sha256(args.path)
        log_content = render_audit_log(report, str(args.path), sha256)
        try:
            args.audit_log.parent.mkdir(parents=True, exist_ok=True)
            args.audit_log.write_text(log_content, encoding="utf-8")
        except Exception as exc:
            print(f"Error writing audit log to {args.audit_log}: {exc}")

    if args.strict and report.blockers:
        return 1
    return 0
