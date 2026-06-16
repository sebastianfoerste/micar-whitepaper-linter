"""Remediation report generation for open MiCAR white paper lint findings."""

from __future__ import annotations

import json
from typing import Any

from micar_linter.linter import Report
from micar_linter.rules.base import Finding, Severity

REMEDIATION_SCHEMA = "micar-whitepaper-linter.remediation-report.v1"


def _owner_role(finding: Finding) -> str:
    if finding.rule.severity is Severity.BLOCKER:
        return "Responsible lawyer"
    if finding.rule.severity is Severity.MAJOR:
        return "Compliance reviewer"
    return "Draft owner"


def _next_action(finding: Finding) -> str:
    if finding.status == "missing":
        return "Add the missing disclosure section and rerun the linter."
    if finding.rule.severity is Severity.BLOCKER:
        return "Cure the blocker before any notification workflow continues."
    return "Review and strengthen the disclosure before sign-off."


def _item(finding: Finding) -> dict[str, Any]:
    return {
        "rule_id": finding.rule.rule_id,
        "citation": finding.rule.citation,
        "section": finding.rule.section,
        "label": finding.rule.label,
        "severity": finding.rule.severity.label,
        "status": finding.status,
        "owner_role": _owner_role(finding),
        "missing_evidence": finding.status == "missing",
        "issues": list(finding.issues),
        "next_action": _next_action(finding),
    }


def build_remediation_report(report: Report) -> dict[str, Any]:
    open_findings = [finding for finding in report.findings if not finding.passed]
    blockers = [finding for finding in open_findings if finding.rule.severity is Severity.BLOCKER]
    status = "BLOCKED" if blockers else "REVIEW_REQUIRED" if open_findings else "READY"

    return {
        "schema": REMEDIATION_SCHEMA,
        "title": report.title,
        "whitepaper_type": report.whitepaper_type.value,
        "status": status,
        "summary": {
            "open_items": len(open_findings),
            "blockers": len(blockers),
            "review_items": len(report.needs_review),
            "missing_sections": len(report.missing),
        },
        "items": [
            {
                **_item(finding),
                "source_anchor": (
                    report.source_anchors[finding.rule.rule_id].to_json()
                    if finding.rule.rule_id in report.source_anchors
                    else None
                ),
            }
            for finding in open_findings
        ],
        "warnings": list(report.warnings),
    }


def render_remediation_report(report: Report) -> str:
    return json.dumps(build_remediation_report(report), indent=2, ensure_ascii=False) + "\n"
