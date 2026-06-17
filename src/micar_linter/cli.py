"""Command-line interface."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from micar_linter import __version__
from micar_linter.artifact_manifest import build_artifact_manifest, render_artifact_manifest
from micar_linter.batch import build_batch_review_pack, render_batch_review_pack
from micar_linter.coverage import build_coverage_matrix, render_coverage_matrix
from micar_linter.linter import lint_whitepaper
from micar_linter.remediation import render_remediation_report
from micar_linter.report import render_audit_log, render_coverage_table, render_json, render_text
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
        "--manifest-output",
        type=Path,
        help="Path to write a local artifact integrity manifest JSON file.",
    )
    parser.add_argument(
        "--remediation-output",
        type=Path,
        help="Path to write a JSON remediation report for open lint findings.",
    )
    parser.add_argument(
        "--coverage-output",
        type=Path,
        help="Path to write a JSON disclosure coverage matrix.",
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Print a clean, console-formatted coverage summary table to stdout.",
    )
    parser.add_argument(
        "--batch-output",
        type=Path,
        help="Path to write a JSON batch review pack when the input path is a directory.",
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

    if args.path.is_dir():
        return _run_batch(args)

    whitepaper = load_whitepaper(args.path)
    if args.lang != "auto":
        whitepaper.metadata["language"] = args.lang

    report = lint_whitepaper(whitepaper)

    if args.coverage:
        print(render_coverage_table(report))
        return 0

    if args.json:
        print(render_json(report))
    else:
        print(render_text(report))

    written_outputs: list[Path] = []

    if args.audit_log:
        sha256 = calculate_sha256(args.path)
        log_content = render_audit_log(report, str(args.path), sha256)
        try:
            args.audit_log.parent.mkdir(parents=True, exist_ok=True)
            args.audit_log.write_text(log_content, encoding="utf-8")
            written_outputs.append(args.audit_log)
        except OSError as exc:
            print(f"error: cannot write audit log to {args.audit_log}: {exc}", file=sys.stderr)
            return 2

    if args.remediation_output:
        try:
            args.remediation_output.parent.mkdir(parents=True, exist_ok=True)
            args.remediation_output.write_text(render_remediation_report(report), encoding="utf-8")
            written_outputs.append(args.remediation_output)
        except OSError as exc:
            print(
                f"error: cannot write remediation report to {args.remediation_output}: {exc}",
                file=sys.stderr,
            )
            return 2

    if args.coverage_output:
        try:
            args.coverage_output.parent.mkdir(parents=True, exist_ok=True)
            args.coverage_output.write_text(
                render_coverage_matrix(build_coverage_matrix(report)),
                encoding="utf-8",
            )
            written_outputs.append(args.coverage_output)
        except OSError as exc:
            print(
                f"error: cannot write coverage matrix to {args.coverage_output}: {exc}",
                file=sys.stderr,
            )
            return 2

    if args.manifest_output:
        manifest = build_artifact_manifest(
            report,
            source_path=args.path,
            output_paths=written_outputs,
        )
        try:
            args.manifest_output.parent.mkdir(parents=True, exist_ok=True)
            args.manifest_output.write_text(render_artifact_manifest(manifest), encoding="utf-8")
        except OSError as exc:
            print(
                f"error: cannot write artifact manifest to {args.manifest_output}: {exc}",
                file=sys.stderr,
            )
            return 2

    if args.strict and report.blockers:
        return 1
    return 0


def _run_batch(args: argparse.Namespace) -> int:
    if not args.batch_output:
        print("error: directory input requires --batch-output <path>", file=sys.stderr)
        return 2

    pack = build_batch_review_pack(args.path)
    try:
        args.batch_output.parent.mkdir(parents=True, exist_ok=True)
        args.batch_output.write_text(render_batch_review_pack(pack), encoding="utf-8")
    except OSError as exc:
        print(f"error: cannot write batch review pack to {args.batch_output}: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(render_batch_review_pack(pack), end="")
    else:
        print(
            (
                "Batch review pack written to {path}. "
                "Supported files: {supported}. Blocked files: {blocked}."
            ).format(
                path=args.batch_output,
                supported=pack["summary"]["supported_files"],
                blocked=pack["summary"]["blocked_files"],
            )
        )

    if args.strict and pack["summary"]["blocked_files"]:
        return 1
    return 0
