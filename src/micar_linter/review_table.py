"""Review table export for MiCAR white paper rule findings."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from micar_linter.artifact_manifest import file_sha256
from micar_linter.linter import Report, lint_whitepaper
from micar_linter.rules.base import Finding, Severity
from micar_linter.whitepaper import load_whitepaper

REVIEW_TABLE_SCHEMA = "micar-whitepaper-linter.review-table.v1"
REVIEW_TABLE_COMPARISON_SCHEMA = "micar-whitepaper-linter.review-table-comparison.v1"
PLAYBOOK_REVIEW_SCHEMA = "micar-linter.playbook-review.v1"


def build_review_table(
    report: Report,
    *,
    source_path: Path | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    timestamp = generated_at or datetime.now(UTC)
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
        "review_table_economics": _review_table_economics(rows),
        "control_profile": _control_profile(report, rows, blocker_rows),
        "prompt_improvement": _prompt_improvement(report, rows, blocker_rows),
        "playbook_profile": _playbook_profile(report, rows, blocker_rows),
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
    timestamp = generated_at or datetime.now(UTC)
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
                    "remediation": row["remediation"],
                    "reviewer_decision": row["reviewer_decision"],
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

    return {
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
        "citation_coverage": "anchor_and_citation" if source_anchor else "citation_only",
        "export_gate": "blocked" if blocker else "review_required",
    }


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


def _playbook_profile(
    report: Report,
    rows: list[dict[str, Any]],
    blocker_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    anchor_count = sum(1 for row in rows if row["source_anchor"])
    coverage = {
        "anchor_and_citation": sum(
            1 for row in rows if row["citation_coverage"] == "anchor_and_citation"
        ),
        "citation_only": sum(1 for row in rows if row["citation_coverage"] == "citation_only"),
    }
    return {
        "schema": PLAYBOOK_REVIEW_SCHEMA,
        "aosLayers": [
            {
                "key": "large_language_models",
                "label": "Large language model routing",
                "status": "blocked",
                "evidence": "The deterministic CLI has no LLM route.",
                "gate": "No external API is called for review-table generation.",
            },
            {
                "key": "agentic_harness",
                "label": "Agentic harness",
                "status": "metadata_only",
                "evidence": "Prompt pack and remediation rows can seed a reviewed drafting workflow.",
                "gate": "The CLI never executes autonomous remediation.",
            },
            {
                "key": "data_integrations",
                "label": "Data and integrations",
                "status": "implemented",
                "evidence": "Local source draft, rule catalog and artifact manifest are linked.",
                "gate": "Local files only. No regulator, exchange or DMS connector is active.",
            },
            {
                "key": "context_knowledge",
                "label": "Context and knowledge",
                "status": "implemented",
                "evidence": f"{anchor_count}/{len(rows)} row(s) include source anchors.",
                "gate": "Source anchors and citations must be reviewed before reliance.",
            },
            {
                "key": "legal_capabilities",
                "label": "Legal capabilities",
                "status": "implemented",
                "evidence": f"{len(rows)} MiCAR rule row(s) across {report.whitepaper_type.value}.",
                "gate": "Blockers require lawyer-reviewed remediation.",
            },
            {
                "key": "products_interfaces",
                "label": "Products and interfaces",
                "status": "implemented",
                "evidence": (
                    "Review table, comparison export, bundle manifest and sign-off "
                    "page are available."
                ),
                "gate": "Exports are local review artifacts.",
            },
            {
                "key": "security_governance",
                "label": "Security and governance",
                "status": "implemented",
                "evidence": "External action is false and source hashes are recorded when available.",
                "gate": "No filing, publication or notification action is implemented.",
            },
        ],
        "agentPlan": {
            "plan": "Select the local draft, white paper type and deterministic rule catalog.",
            "execute": "Run the parser and rules locally to create review rows.",
            "review": "Check blockers, source anchors, remediation and reviewer decisions.",
            "deliver": "Export local JSON or review bundle after lawyer sign-off.",
        },
        "skills": [
            {
                "id": "rule-review-playbook",
                "label": "Rule review playbook",
                "objective": "Project deterministic findings into reviewer-owned rule rows.",
                "outputSchema": ["rule id", "status", "blocker", "source anchor", "reviewer decision"],
                "reviewGate": "Qualified lawyer review required before external use.",
                "externalActionAllowed": False,
            },
            {
                "id": "remediation-playbook",
                "label": "Remediation playbook",
                "objective": "Turn blockers and missing disclosures into draft remediation tasks.",
                "outputSchema": ["rule-specific remediation", "source anchor", "filing gate"],
                "reviewGate": "Rerun the deterministic CLI before relying on any cure.",
                "externalActionAllowed": False,
            },
            {
                "id": "comparison-playbook",
                "label": "Comparison playbook",
                "objective": "Compare multiple local draft review tables by rule id and source hash.",
                "outputSchema": ["status change", "blocker change", "word count", "reviewer decision"],
                "reviewGate": "Comparison remains local and review-gated.",
                "externalActionAllowed": False,
            },
        ],
        "tabularReview": {
            "schema": "micar-whitepaper-linter.review-table-economics.v1",
            "rowCount": len(rows),
            "columnCount": 12,
            "estimatedCellTasks": len(rows) * 12,
            "reviewMode": "review_gated",
            "externalActionAllowed": False,
        },
        "trustedSources": {
            "sourceMode": "local_draft_and_rule_catalog",
            "citationCoverage": coverage,
            "sourceAnchorRows": anchor_count,
            "externalActionAllowed": False,
        },
        "editorDraft": {
            "status": "draft_only",
            "sourceTraceability": "required",
            "approvalRequired": True,
        },
        "wordExportPackage": {
            "status": "review_gated",
            "formats": ["json", "markdown", "artifact-manifest"],
            "externalActionAllowed": False,
        },
        "portalRoom": {
            "accessMode": "local_review_bundle",
            "roleBasedAccess": False,
            "auditTrailRequired": True,
            "externalGuestAccessAllowed": False,
        },
        "monitors": {
            "status": "metadata_only",
            "perimeter": ["local draft", "rule catalog", "source anchors", "review bundle"],
            "deliveryStatus": "blocked_without_review",
        },
        "lists": {
            "status": "implemented",
            "items": [
                {
                    "key": row["rule_id"],
                    "label": row["label"],
                    "owner": "White paper reviewer",
                    "signOffRequired": bool(
                        row["blocker"]
                        or row["reviewer_decision"] != "pending_lawyer_confirmation"
                    ),
                }
                for row in rows[:8]
            ],
        },
        "securityGovernance": {
            "zeroTrust": True,
            "noFoundationModelTraining": True,
            "dataRetention": "local_file_only",
            "auditTrail": "artifact_manifest",
            "approvalGate": "required_for_external_filing_or_publication",
        },
        "blockerRuleIds": [row["rule_id"] for row in blocker_rows],
        "legoraIntegration": "none",
        "externalActionAllowed": False,
        "reviewNotice": (
            "Legora-inspired product pattern, no Legora integration or dependency. "
            "The deterministic CLI remains the system of record."
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
]
