"""Disclosure coverage matrix export."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from micar_linter.linter import Report
from micar_linter.rules.base import Finding, Severity

COVERAGE_SCHEMA = "micar-whitepaper-linter.coverage-matrix.v1"


def build_coverage_matrix(report: Report, generated_at: datetime | None = None) -> dict[str, Any]:
    timestamp = generated_at or datetime.now(UTC)
    rows = [_coverage_row(report, finding) for finding in report.findings]
    blockers = [row["rule_id"] for row in rows if row["blocker"]]

    payload = {
        "schema": COVERAGE_SCHEMA,
        "generated_at": timestamp.isoformat(),
        "title": report.title,
        "whitepaper_type": report.whitepaper_type.value,
        "summary": {
            "total": len(rows),
            "pass": len(report.passed),
            "review": len(report.needs_review),
            "missing": len(report.missing),
            "blockers": len(blockers),
        },
        "coverage": rows,
        "blockers": blockers,
        "warnings": list(report.warnings),
        "review_notice": (
            "Coverage matrix is a deterministic disclosure checklist. "
            "It is not legal advice, a signature, a notification, or filing approval."
        ),
    }
    payload["digest"] = _digest(payload)
    return payload


def render_coverage_matrix(matrix: dict[str, Any]) -> str:
    return json.dumps(matrix, indent=2, ensure_ascii=False) + "\n"


def _coverage_row(report: Report, finding: Finding) -> dict[str, Any]:
    return {
        "rule_id": finding.rule.rule_id,
        "annex": _annex(finding.rule.rule_id),
        "section": finding.rule.section,
        "citation": finding.rule.citation,
        "severity": finding.rule.severity.label,
        "status": finding.status,
        "word_count": finding.word_count,
        "blocker": (finding.rule.severity is Severity.BLOCKER) and not finding.passed,
        "next_action": _next_action(finding),
        "source_anchor": (
            report.source_anchors[finding.rule.rule_id].to_json()
            if finding.rule.rule_id in report.source_anchors
            else None
        ),
    }


def _annex(rule_id: str) -> str:
    parts = rule_id.split(".")
    return parts[0] if parts else "UNKNOWN"


def _next_action(finding: Finding) -> str:
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
