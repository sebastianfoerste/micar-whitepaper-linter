"""Command-line interface."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from micar_linter import __version__
from micar_linter.artifact_manifest import build_artifact_manifest, render_artifact_manifest
from micar_linter.batch import build_batch_review_pack, render_batch_review_pack
from micar_linter.coverage import build_coverage_matrix, render_coverage_matrix
from micar_linter.legora_workspace import (
    build_change_set,
    build_review_sidecar,
    build_workflow_pack,
    write_legora_bundle,
)
from micar_linter.linter import lint_whitepaper
from micar_linter.remediation import render_remediation_report
from micar_linter.report import render_audit_log, render_coverage_table, render_json, render_text
from micar_linter.review_bundle import write_review_bundle
from micar_linter.review_table import (
    build_review_table,
    build_review_table_comparison,
    render_review_table,
    render_review_table_comparison,
)
from micar_linter.whitepaper import load_whitepaper
from micar_linter.workspace import build_whitepaper_workspace, render_whitepaper_workspace


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
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="Path to one or more local whitepaper draft files.",
    )
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
        "--review-table-output",
        type=Path,
        help="Path to write a JSON review table for rule-by-rule lawyer review.",
    )
    parser.add_argument(
        "--compare-review-table-output",
        type=Path,
        help="Path to write a JSON comparison of multiple local draft review tables.",
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Print a clean, console-formatted coverage summary table to stdout.",
    )
    parser.add_argument(
        "--review-bundle-dir",
        type=Path,
        help="Directory to write the complete review bundle.",
    )
    parser.add_argument(
        "--batch-output",
        type=Path,
        help="Path to write a JSON batch review pack when the input path is a directory.",
    )
    parser.add_argument(
        "--workspace-output",
        type=Path,
        help=("Path to write a local white paper vault, interactive review table and reusable playbook."),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"micar-lint {__version__}",
    )
    parser.add_argument(
        "--legora-bundle-dir",
        type=Path,
        help="Write collaboration sidecar, document change set and supervised workflow pack.",
    )
    parser.add_argument(
        "--workflow-action",
        choices=["validate", "inspect", "run"],
        help="Validate, inspect or run the supervised local white paper workflow.",
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
    paths: list[Path] = args.paths

    if args.workspace_output:
        try:
            workspace = build_whitepaper_workspace(paths)
            args.workspace_output.parent.mkdir(parents=True, exist_ok=True)
            args.workspace_output.write_text(render_whitepaper_workspace(workspace), encoding="utf-8")
        except (OSError, SystemExit, ValueError) as exc:
            print(f"error: cannot write white paper workspace: {exc}", file=sys.stderr)
            return 2
        if args.json:
            print(render_whitepaper_workspace(workspace), end="")
        else:
            print(
                "White paper workspace written to "
                f"{args.workspace_output}. Documents: {workspace['vault']['document_count']}."
            )
        if args.legora_bundle_dir:
            write_legora_bundle(workspace, args.legora_bundle_dir)
        if args.workflow_action:
            sidecar = build_review_sidecar(workspace)
            change_set = build_change_set(workspace)
            workflow = build_workflow_pack(workspace, sidecar, change_set)
            if args.workflow_action == "validate":
                print("workflow.definition.v1 and workflow.run.v1 validated")
            elif args.workflow_action == "inspect":
                print(json.dumps(workflow, indent=2))
            else:
                if not args.legora_bundle_dir:
                    print("error: --workflow-action run requires --legora-bundle-dir", file=sys.stderr)
                    return 2
                print(
                    f"Supervised workflow run status: {workflow['run']['status']}. "
                    "External action remains disabled."
                )
        if args.strict and workspace["review_table"]["summary"]["blockers"]:
            return 1
        return 0

    if args.compare_review_table_output:
        return _run_review_table_comparison(args, paths)

    if len(paths) != 1:
        print(
            "error: multiple draft paths require --compare-review-table-output <path>",
            file=sys.stderr,
        )
        return 2
    args.path = paths[0]

    if args.path.is_dir():
        return _run_batch(args)

    whitepaper = load_whitepaper(args.path)
    if args.lang != "auto":
        whitepaper.metadata["language"] = args.lang

    report = lint_whitepaper(whitepaper)

    if args.coverage and not args.review_bundle_dir:
        print(render_coverage_table(report))
        return 0

    if args.json:
        print(render_json(report))
    else:
        print(render_text(report))

    written_outputs: list[Path] = []

    if args.review_bundle_dir:
        try:
            bundle_paths = write_review_bundle(
                report,
                source_path=args.path,
                directory=args.review_bundle_dir,
            )
        except OSError as exc:
            print(
                f"error: cannot write review bundle to {args.review_bundle_dir}: {exc}",
                file=sys.stderr,
            )
            return 2
        written_outputs.extend(bundle_paths)
        print(f"review-bundle: {args.review_bundle_dir}", file=sys.stderr if args.json else sys.stdout)

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

    if args.review_table_output:
        try:
            args.review_table_output.parent.mkdir(parents=True, exist_ok=True)
            args.review_table_output.write_text(
                render_review_table(build_review_table(report, source_path=args.path)),
                encoding="utf-8",
            )
            written_outputs.append(args.review_table_output)
        except OSError as exc:
            print(
                f"error: cannot write review table to {args.review_table_output}: {exc}",
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


def _run_review_table_comparison(args: argparse.Namespace, paths: list[Path]) -> int:
    if len(paths) < 2:
        print(
            "error: --compare-review-table-output requires at least two local draft paths",
            file=sys.stderr,
        )
        return 2
    directory_inputs = [path for path in paths if path.is_dir()]
    if directory_inputs:
        print(
            "error: comparison input must be local draft files, not directories",
            file=sys.stderr,
        )
        return 2

    try:
        comparison = build_review_table_comparison(paths)
        args.compare_review_table_output.parent.mkdir(parents=True, exist_ok=True)
        args.compare_review_table_output.write_text(
            render_review_table_comparison(comparison),
            encoding="utf-8",
        )
    except (OSError, SystemExit) as exc:
        print(
            f"error: cannot write review table comparison to {args.compare_review_table_output}: {exc}",
            file=sys.stderr,
        )
        return 2

    if args.json:
        print(render_review_table_comparison(comparison), end="")
    else:
        print(
            (
                "Review table comparison written to {path}. "
                "Rule groups: {groups}. Blocker groups: {blockers}."
            ).format(
                path=args.compare_review_table_output,
                groups=comparison["summary"]["rule_groups"],
                blockers=comparison["summary"]["blocker_groups"],
            )
        )

    if args.strict and comparison["summary"]["blocker_groups"]:
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
                "Batch review pack written to {path}. Supported files: {supported}. Blocked files: {blocked}."
            ).format(
                path=args.batch_output,
                supported=pack["summary"]["supported_files"],
                blocked=pack["summary"]["blocked_files"],
            )
        )

    if args.strict and pack["summary"]["blocked_files"]:
        return 1
    return 0
