"""One-command MiCAR white paper review bundle exports."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from micar_linter.artifact_manifest import (
    build_artifact_manifest,
    file_sha256,
    render_artifact_manifest,
)
from micar_linter.coverage import build_coverage_matrix, render_coverage_matrix
from micar_linter.linter import Report
from micar_linter.remediation import render_remediation_report
from micar_linter.report import render_audit_log
from micar_linter.review_table import build_review_table, render_review_table, render_review_table_markdown

REVIEW_BUNDLE_SCHEMA = "micar-whitepaper-linter.review-bundle.v1"


def write_review_bundle(
    report: Report,
    *,
    source_path: Path,
    directory: Path,
    generated_at: datetime | None = None,
) -> list[Path]:
    timestamp = generated_at or datetime.now(UTC)
    directory.mkdir(parents=True, exist_ok=True)

    compliance_path = directory / "compliance-checklist.md"
    remediation_path = directory / "remediation-checklist.json"
    coverage_path = directory / "coverage-matrix.json"
    review_table_path = directory / "review-table.json"
    review_table_markdown_path = directory / "review-table.md"
    signoff_path = directory / "reviewer-signoff.md"
    manifest_path = directory / "manifest.json"

    compliance_path.write_text(
        render_audit_log(report, str(source_path), file_sha256(source_path)),
        encoding="utf-8",
    )
    remediation_path.write_text(render_remediation_report(report), encoding="utf-8")
    coverage_path.write_text(
        render_coverage_matrix(build_coverage_matrix(report, generated_at=timestamp)),
        encoding="utf-8",
    )
    review_table = build_review_table(report, source_path=source_path, generated_at=timestamp)
    review_table_path.write_text(render_review_table(review_table), encoding="utf-8")
    review_table_markdown_path.write_text(render_review_table_markdown(review_table), encoding="utf-8")
    signoff_path.write_text(render_signoff_page(report, timestamp), encoding="utf-8")

    outputs = [
        compliance_path,
        remediation_path,
        coverage_path,
        review_table_path,
        review_table_markdown_path,
        signoff_path,
    ]
    manifest = build_artifact_manifest(
        report,
        source_path=source_path,
        output_paths=outputs,
        generated_at=timestamp,
    )
    manifest["bundle_schema"] = REVIEW_BUNDLE_SCHEMA
    manifest_path.write_text(render_artifact_manifest(manifest), encoding="utf-8")

    return [*outputs, manifest_path]


def render_signoff_page(report: Report, generated_at: datetime | None = None) -> str:
    timestamp = generated_at or datetime.now(UTC)
    blockers = [finding.rule.rule_id for finding in report.blockers]
    status = "Blocked" if blockers else "Review required"

    lines = [
        "# MiCAR White Paper Reviewer Sign-off",
        "",
        "This page is a draft review record for a qualified lawyer.",
        "It does not certify a white paper, approve a notification or replace legal review.",
        "",
        f"- Document title: {report.title}",
        f"- White paper type: {report.whitepaper_type.value}",
        f"- Generated at: {timestamp.isoformat()}",
        f"- Automated status: {status}",
        f"- Open blocker count: {len(blockers)}",
        "",
        "## Required Review Steps",
        "",
        "- Confirm the white paper type and applicable MiCAR annex.",
        "- Review every BLOCKER and MAJOR finding against the source draft.",
        "- Confirm source anchors, remediation notes and coverage matrix rows.",
        "- Approve any external review, notification or filing step separately.",
        "",
        "## Blockers",
        "",
    ]
    if blockers:
        lines.extend(f"- {rule_id}" for rule_id in blockers)
    else:
        lines.append("- No blocker rule IDs remain open in the automated report.")
    lines.extend(
        [
            "",
            "## Lawyer Sign-off",
            "",
            "Reviewer Name:  __________________________________",
            "",
            "Date of Review: __________________________________",
            "",
            "Signature:      __________________________________",
            "",
        ]
    )
    return "\n".join(lines)


__all__ = ["REVIEW_BUNDLE_SCHEMA", "render_signoff_page", "write_review_bundle"]
