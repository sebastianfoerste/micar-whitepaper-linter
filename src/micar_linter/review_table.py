"""Review table export for MiCAR white paper rule findings."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from micar_linter.artifact_manifest import file_sha256
from micar_linter.linter import Report, lint_whitepaper
from micar_linter.rules.base import Finding, Severity
from micar_linter.whitepaper import load_whitepaper

REVIEW_TABLE_SCHEMA = "micar-whitepaper-linter.review-table"
REVIEW_TABLE_COMPARISON_SCHEMA = "micar-whitepaper-linter.review-table-comparison"


def _reproducible_timestamp(generated_at: datetime | None) -> datetime:
    if generated_at is not None:
        return generated_at
    raw_epoch = os.environ.get("SOURCE_DATE_EPOCH", "0")
    try:
        return datetime.fromtimestamp(int(raw_epoch), UTC)
    except (ValueError, OverflowError, OSError) as error:
        raise ValueError("SOURCE_DATE_EPOCH must be a valid integer Unix timestamp") from error


def build_review_table(
    report: Report,
    *,
    source_path: Path | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    timestamp = _reproducible_timestamp(generated_at)
    rows = [_review_row(report, finding) for finding in report.findings]
    blocker_rows = [row for row in rows if row["blocker"]]

    payload: dict[str, Any] = {
        "schema": REVIEW_TABLE_SCHEMA,
        "generated_at": timestamp.isoformat(),
        "title": report.title,
        "whitepaper_type": report.whitepaper_type.value,
        "source": {
            "path": str(source_path) if source_path else None,
            "sha256": file_sha256(source_path) if source_path else None,
        },
        "summary": {
            "total": len(rows),
            "pass": len(report.passed),
            "review": len(report.needs_review),
            "missing": len(report.missing),
            "blockers": len(blocker_rows),
            "export_gate": "blocked" if blocker_rows else "review_required",
        },
        "delivery_block": _delivery_block(blocker_rows),
        "editor_draft_package": _editor_draft_package(rows, blocker_rows),
        "review_table_economics": _review_table_economics(rows),
        "control_profile": _control_profile(report, rows, blocker_rows),
        "prompt_improvement": _prompt_improvement(report, rows, blocker_rows),
        "rows": rows,
        "warnings": list(report.warnings),
        "review_notice": (
            "Review table rows are deterministic linter outputs. "
            "Reviewer decisions remain pending until a qualified lawyer signs off."
        ),
    }
    payload["digest"] = _digest(payload)
    return payload


def render_review_table(table: dict[str, Any]) -> str:
    return json.dumps(table, indent=2, ensure_ascii=False) + "\n"


def build_review_table_comparison(
    source_paths: list[Path],
    *,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    timestamp = _reproducible_timestamp(generated_at)
    tables = [
        build_review_table(
            lint_whitepaper(load_whitepaper(path)),
            source_path=path,
            generated_at=timestamp,
        )
        for path in source_paths
    ]
    grouped: dict[str, dict[str, Any]] = {}
    for table in tables:
        source = table["source"]
        for row in table["rows"]:
            group = grouped.setdefault(
                row["rule_id"],
                {
                    "rule_id": row["rule_id"],
                    "citation": row["citation"],
                    "section": row["section"],
                    "label": row["label"],
                    "drafts": [],
                },
            )
            group["drafts"].append(
                {
                    "source_sha256": source["sha256"],
                    "source_path": source["path"],
                    "status": row["status"],
                    "blocker": row["blocker"],
                    "word_count": row["word_count"],
                    "source_anchor": row["source_anchor"],
                    "anchor_verified": row["anchor_verified"],
                    "remediation": row["remediation"],
                    "reviewer_decision": row["reviewer_decision"],
                    "draft_cells": row["review_cells"],
                }
            )

    groups = [_comparison_group(group) for group in grouped.values()]
    blocker_groups = [group for group in groups if any(draft["blocker"] for draft in group["drafts"])]
    payload: dict[str, Any] = {
        "schema": REVIEW_TABLE_COMPARISON_SCHEMA,
        "generated_at": timestamp.isoformat(),
        "source_count": len(tables),
        "sources": [
            {
                "path": table["source"]["path"],
                "sha256": table["source"]["sha256"],
                "title": table["title"],
                "whitepaper_type": table["whitepaper_type"],
                "row_count": table["summary"]["total"],
                "blockers": table["summary"]["blockers"],
            }
            for table in tables
        ],
        "summary": {
            "rule_groups": len(groups),
            "blocker_groups": len(blocker_groups),
            "status_changed_groups": sum(1 for group in groups if group["status_changed"]),
            "reviewer_decision_changed_groups": sum(
                1 for group in groups if group["reviewer_decision_changed"]
            ),
            "export_gate": "blocked" if blocker_groups else "review_required",
        },
        "groups": sorted(groups, key=lambda group: group["rule_id"]),
        "external_action_allowed": False,
        "review_gate": (
            "Comparison export is local and deterministic. A qualified lawyer must "
            "review changes before external use."
        ),
    }
    payload["digest"] = _digest(payload)
    return payload


def render_review_table_comparison(comparison: dict[str, Any]) -> str:
    return json.dumps(comparison, indent=2, ensure_ascii=False) + "\n"


def render_review_table_markdown(table: dict[str, Any]) -> str:
    lines = [
        "# MiCAR White Paper Review Table",
        "",
        "Local draft and rule-catalog evidence only.",
        (
            "This markdown table is a local review artifact. It does not approve filing, "
            "publication or notification."
        ),
        "",
        f"- Title: {table['title']}",
        f"- White paper type: {table['whitepaper_type']}",
        f"- Export gate: {table['summary']['export_gate']}",
        f"- External action allowed: {table['delivery_block']['external_action_allowed']}",
        "",
        "| Rule ID | Citation | Status | Blocker | Reviewer decision | Anchor verified |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in table["rows"]:
        lines.append(
            (
                "| {rule_id} | {citation} | {status} | {blocker} | "
                "{reviewer_decision} | {anchor_verified} |"
            ).format(
                rule_id=row["rule_id"],
                citation=row["citation"],
                status=row["status"],
                blocker="yes" if row["blocker"] else "no",
                reviewer_decision=row["reviewer_decision"],
                anchor_verified="yes" if row["anchor_verified"] else "no",
            )
        )
    lines.extend(
        [
            "",
            "## Review Gate",
            "",
            table["delivery_block"]["review_gate"],
            "",
        ]
    )
    return "\n".join(lines)


def _comparison_group(group: dict[str, Any]) -> dict[str, Any]:
    drafts = group["drafts"]
    statuses = {draft["status"] for draft in drafts}
    blocker_states = {draft["blocker"] for draft in drafts}
    reviewer_decisions = {draft["reviewer_decision"] for draft in drafts}
    return {
        **group,
        "source_hashes": [draft["source_sha256"] for draft in drafts],
        "status_changed": len(statuses) > 1,
        "blocker_changed": len(blocker_states) > 1,
        "reviewer_decision_changed": len(reviewer_decisions) > 1,
    }


def _review_table_economics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    column_count = 12
    return {
        "schema": "micar-whitepaper-linter.review-table-economics.v1",
        "row_count": len(rows),
        "column_count": column_count,
        "estimated_cell_tasks": len(rows) * column_count,
        "route": "deterministic_cli",
        "max_vault_documents": 100_000,
        "reset_strategy": (
            "Each rule row and generated review column is evaluated from deterministic "
            "parser output and the local rule catalog."
        ),
        "llm_route": "none",
    }


def _review_row(report: Report, finding: Finding) -> dict[str, Any]:
    source_anchor = (
        report.source_anchors[finding.rule.rule_id].to_json()
        if finding.rule.rule_id in report.source_anchors
        else None
    )
    blocker = (finding.rule.severity is Severity.BLOCKER) and not finding.passed
    row = {
        "row_id": _row_id(report, finding),
        "rule_id": finding.rule.rule_id,
        "citation": finding.rule.citation,
        "section": finding.rule.section,
        "label": finding.rule.label,
        "severity": finding.rule.severity.label,
        "status": finding.status,
        "blocker": blocker,
        "word_count": finding.word_count,
        "issues": list(finding.issues),
        "remediation": _remediation(finding),
        "reviewer_decision": _reviewer_decision(finding),
        "verification_state": _verification_state(finding),
        "source_anchor": source_anchor,
        "anchor_verified": bool(source_anchor),
        "citation_coverage": "anchor_and_citation" if source_anchor else "citation_only",
        "export_gate": "blocked" if blocker else "review_required",
        "playbook": _row_playbook(report, finding, blocker),
        "word_suggested_edit": _word_suggested_edit(finding, blocker),
        "delivery_block": _row_delivery_block(blocker),
    }
    row["review_cells"] = _review_cells(row)
    return row


def _delivery_block(blocker_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": "micar-whitepaper-linter.delivery-block.v1",
        "status": "blocked" if blocker_rows else "review_required",
        "blocked_rule_ids": [row["rule_id"] for row in blocker_rows],
        "external_action_allowed": False,
        "review_gate": (
            "External filing, publication and notification are blocked until a qualified lawyer signs off "
            "and the deterministic CLI has been rerun against the remediated local draft."
        ),
    }


def _editor_draft_package(rows: list[dict[str, Any]], blocker_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": "micar-whitepaper-linter.editor-draft-package.v1",
        "status": "draft_only",
        "suggested_edit_count": sum(1 for row in rows if row["word_suggested_edit"]["action"] != "none"),
        "blocker_count": len(blocker_rows),
        "formats": ["json", "markdown"],
        "external_action_allowed": False,
        "review_gate": "Suggested edits are local drafting aids and require lawyer review.",
    }


def _row_playbook(report: Report, finding: Finding, blocker: bool) -> dict[str, Any]:
    return {
        "id": f"{report.whitepaper_type.value}-{finding.rule.section}".lower().replace(" ", "-"),
        "skill": "rule-review-playbook",
        "rule_scope": [finding.rule.rule_id],
        "citation": finding.rule.citation,
        "severity": finding.rule.severity.label,
        "review_gate": "Qualified lawyer review required before external use.",
        "priority": "blocker" if blocker else "standard_review",
        "external_action_allowed": False,
    }


def _row_delivery_block(blocker: bool) -> dict[str, Any]:
    return {
        "status": "blocked" if blocker else "review_required",
        "external_action_allowed": False,
        "review_gate": (
            "Lawyer sign-off and deterministic rerun required before external filing or publication."
        ),
    }


def _word_suggested_edit(finding: Finding, blocker: bool) -> dict[str, Any]:
    if finding.passed:
        action = "none"
        instruction = "No suggested edit. Preserve disclosure under lawyer review."
    elif finding.status == "missing":
        action = "insert_section"
        instruction = f"Add disclosure for {finding.rule.label} and cite {finding.rule.citation}."
    else:
        action = "revise_clause" if not blocker else "insert_required_disclosure"
        instruction = _remediation(finding)
    return {
        "schema": "micar-whitepaper-linter.word-suggested-edit.v1",
        "action": action,
        "instruction": instruction,
        "target_section": finding.rule.section,
        "draft_only": True,
        "external_action_allowed": False,
    }


def _review_cells(row: dict[str, Any]) -> list[dict[str, Any]]:
    columns = [
        ("rule_id", "Rule ID"),
        ("citation", "Citation"),
        ("section", "Section"),
        ("status", "Status"),
        ("blocker", "Blocker"),
        ("word_count", "Word count"),
        ("remediation", "Remediation"),
        ("reviewer_decision", "Reviewer decision"),
        ("verification_state", "Verification"),
        ("source_anchor", "Source anchor"),
        ("citation_coverage", "Citation coverage"),
        ("export_gate", "Export gate"),
    ]
    cells = []
    for column_id, label in columns:
        value = row[column_id]
        if isinstance(value, dict):
            rendered_value = value.get("stable_anchor_id", "anchor")
        elif isinstance(value, bool):
            rendered_value = "true" if value else "false"
        else:
            rendered_value = str(value)
        status = "blocked" if row["blocker"] and column_id in {"blocker", "export_gate"} else "needs_review"
        if row["status"] == "pass" and column_id not in {"reviewer_decision", "export_gate"}:
            status = "complete"
        cells.append(
            {
                "column_id": column_id,
                "label": label,
                "value": rendered_value,
                "status": status,
                "review_gate": "Qualified lawyer review required before external use.",
                "external_action_allowed": False,
            }
        )
    return cells


def _control_profile(
    report: Report,
    rows: list[dict[str, Any]],
    blocker_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    anchor_rows = sum(1 for row in rows if row["source_anchor"])
    open_rows = [row for row in rows if row["reviewer_decision"] != "pending_lawyer_confirmation"]
    return {
        "schema": "micar-whitepaper-linter.review-control-profile.v1",
        "mode": "deterministic_cli",
        "external_action_allowed": False,
        "route_summary": (
            "Rule evaluation, coverage, remediation and review-table export are deterministic. "
            "No LLM route or external delivery route is present."
        ),
        "context_window_strategy": (
            f"{len(rows)} rule row(s), each evaluated against deterministic parser output and "
            "the local rule catalog."
        ),
        "source_connectors": [
            {
                "key": "draft-whitepaper",
                "label": "Draft white paper",
                "status": "enabled",
                "scope": report.title,
                "gate": "Local file only. Source hash is included when a path is provided.",
            },
            {
                "key": "rule-catalog",
                "label": "MiCAR rule catalog",
                "status": "enabled",
                "scope": f"{len(rows)} rule row(s) across {report.whitepaper_type.value}.",
                "gate": "Rules are deterministic and versioned in source control.",
            },
            {
                "key": "source-anchors",
                "label": "Source anchors",
                "status": "enabled" if anchor_rows == len(rows) and rows else "review_required",
                "scope": f"{anchor_rows}/{len(rows)} row(s) include source anchors.",
                "gate": "Citation and source anchor coverage must be checked by the reviewer.",
            },
            {
                "key": "notification-workflow",
                "label": "Notification workflow",
                "status": "blocked",
                "scope": "BaFin or exchange-facing submission steps are outside the CLI.",
                "gate": "External filing requires separate lawyer approval.",
            },
        ],
        "workflow_routes": [
            {
                "key": "rule-evaluation",
                "label": "Rule evaluation",
                "status": "ready",
                "route": "deterministic_local",
                "gate": "Automated pass does not equal legal sign-off.",
            },
            {
                "key": "remediation",
                "label": "Remediation drafting",
                "status": "blocked" if blocker_rows else "review_required",
                "route": "deterministic_local",
                "gate": "Blockers must be cured before notification or publication reliance.",
            },
            {
                "key": "review-table-export",
                "label": "Review table export",
                "status": "review_required" if open_rows else "ready",
                "route": "deterministic_local",
                "gate": "Reviewer decisions remain pending in the exported table.",
            },
            {
                "key": "external-filing",
                "label": "External filing",
                "status": "blocked",
                "route": "external_action",
                "gate": "No external filing or delivery route is implemented.",
            },
        ],
    }


def _prompt_improvement(
    report: Report,
    rows: list[dict[str, Any]],
    blocker_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    blocker_rule_ids = [row["rule_id"] for row in blocker_rows[:6]]
    missing_rule_ids = [row["rule_id"] for row in rows if row["status"] == "missing"][:6]
    blocker_rules = ", ".join(blocker_rule_ids) if blocker_rule_ids else "none in this table"
    missing_rules = ", ".join(missing_rule_ids) if missing_rule_ids else "none in this table"
    source_anchor_count = sum(1 for row in rows if row["source_anchor"])
    return {
        "schema": "micar-whitepaper-linter.remediation-prompt-pack.v1",
        "objective": "Turn deterministic rule findings into reviewer-controlled remediation instructions.",
        "actor": "MiCAR white paper reviewer",
        "jurisdiction": "EU MiCAR white paper disclosure review",
        "source_hierarchy": [
            "local white paper draft",
            "deterministic rule catalog",
            "source anchors",
            "reviewer decision",
        ],
        "required_inputs": [
            "white paper type",
            "rule id and MiCAR citation",
            "section label",
            "finding status, blocker flag and issues",
            "source anchor and draft hash when available",
        ],
        "output_format": [
            "rule-specific remediation",
            "missing evidence list",
            "source anchor to verify",
            "reviewer decision field",
            "external filing gate",
        ],
        "review_gate": "Draft remediation only. The linter never files, notifies or publishes.",
        "failure_conditions": [
            "Do not invent facts or source anchors.",
            "Do not mark a blocker cured before the deterministic linter is rerun.",
            "Do not describe a notification, publication or exchange submission as approved.",
        ],
        "suggested_prompt": "\n".join(
            [
                "Role: MiCAR white paper reviewer.",
                f"Objective: remediate deterministic findings for {report.title}.",
                f"White paper type: {report.whitepaper_type.value}.",
                f"Open blockers: {blocker_rules}.",
                f"Missing rules: {missing_rules}.",
                f"Source anchors: {source_anchor_count}/{len(rows)} rule row(s).",
                "Output: remediation by rule id, source anchor to verify, reviewer decision and filing gate.",
                "Review gate: draft only. Rerun the deterministic CLI before relying on any cure.",
            ]
        ),
    }



def _row_id(report: Report, finding: Finding) -> str:
    seed = f"{report.title}:{report.whitepaper_type.value}:{finding.rule.rule_id}:{finding.rule.section}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return f"review-row-{digest[:16]}"


def _reviewer_decision(finding: Finding) -> str:
    if finding.passed:
        return "pending_lawyer_confirmation"
    if finding.rule.severity is Severity.BLOCKER:
        return "remediation_required"
    if finding.status == "missing":
        return "remediation_required"
    return "lawyer_review_required"


def _verification_state(finding: Finding) -> str:
    if finding.passed:
        return "auto_passed"
    if finding.status == "missing":
        return "missing_evidence"
    return "needs_verification"


def _remediation(finding: Finding) -> str:
    if finding.status == "pass":
        return "Keep disclosure under lawyer review before external use."
    if finding.status == "missing":
        return "Add the missing disclosure section and rerun the linter."
    if finding.rule.severity is Severity.BLOCKER:
        return "Cure blocker before any notification workflow continues."
    return "Strengthen the disclosure before sign-off."


def _digest(payload: dict[str, Any]) -> str:
    unsigned = {key: value for key, value in payload.items() if key != "digest"}
    encoded = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
    "REVIEW_TABLE_COMPARISON_SCHEMA",
    "REVIEW_TABLE_SCHEMA",
    "build_review_table",
    "build_review_table_comparison",
    "render_review_table",
    "render_review_table_comparison",
    "render_review_table_markdown",
]
