"""Artifact manifest rendering for linter exports."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from micar_linter.linter import Report

MANIFEST_SCHEMA = "micar-whitepaper-linter.artifact-manifest.v1"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_artifact_manifest(
    report: Report,
    *,
    source_path: Path,
    output_paths: list[Path] | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    timestamp = generated_at or datetime.now(UTC)
    outputs = output_paths or []
    missing_outputs = [path for path in outputs if not path.exists()]
    output_entries = [
        {
            "path": str(path),
            "sha256": file_sha256(path),
            "role": _output_role(path),
        }
        for path in outputs
        if path.exists()
    ]
    blocker_rule_ids = [finding.rule.rule_id for finding in report.blockers]
    warnings = [f"output-missing:{path}" for path in missing_outputs]

    payload = {
        "schema": MANIFEST_SCHEMA,
        "generated_at": timestamp.isoformat(),
        "source": {
            "path": str(source_path),
            "sha256": file_sha256(source_path),
        },
        "report": {
            "title": report.title,
            "whitepaper_type": report.whitepaper_type.value,
            "passed": len(report.passed),
            "review": len(report.needs_review),
            "missing": len(report.missing),
            "blockers": len(report.blockers),
            "blocker_rule_ids": blocker_rule_ids,
        },
        "outputs": output_entries,
        "warnings": warnings,
        "export_eligibility": {
            "machine_export_ready": not blocker_rule_ids,
            "blocked_by": blocker_rule_ids,
            "review_required": True,
            "notice": "Automated linter output requires substantive lawyer review before external use.",
        },
        "review_notice": (
            "Manifest proves local artifact integrity only. "
            "It is not a legal opinion, signature, notification, or filing approval."
        ),
    }
    payload["overall_digest"] = _overall_digest(payload)
    return payload


def render_artifact_manifest(manifest: dict[str, Any]) -> str:
    return json.dumps(manifest, indent=2, ensure_ascii=False)


def _output_role(path: Path) -> str:
    name = path.name
    if name == "compliance-checklist.md":
        return "compliance_checklist"
    if name == "remediation-checklist.json":
        return "remediation_checklist"
    if name == "coverage-matrix.json":
        return "coverage_matrix"
    if name == "review-table.json":
        return "review_table_json"
    if name == "review-table.md":
        return "review_table_markdown"
    if name == "reviewer-signoff.md":
        return "lawyer_signoff"
    return "supporting_artifact"


def _overall_digest(payload: dict[str, Any]) -> str:
    digest_payload = {key: value for key, value in payload.items() if key != "overall_digest"}
    encoded = json.dumps(digest_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
