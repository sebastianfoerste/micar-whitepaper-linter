"""Directory batch review pack generation."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from micar_linter.artifact_manifest import build_artifact_manifest, file_sha256
from micar_linter.linter import lint_whitepaper
from micar_linter.whitepaper import load_whitepaper

BATCH_SCHEMA = "micar-whitepaper-linter.batch-review-pack.v1"
SUPPORTED_SUFFIXES = {".json", ".pdf", ".docx", ".xhtml", ".html", ".md"}


def build_batch_review_pack(root: Path, generated_at: datetime | None = None) -> dict[str, Any]:
    timestamp = generated_at or datetime.now(UTC)
    files: list[dict[str, Any]] = []
    warnings: list[str] = []

    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            warnings.append(f"unsupported-file:{path}")
            continue
        try:
            whitepaper = load_whitepaper(path)
            report = lint_whitepaper(whitepaper)
            manifest = build_artifact_manifest(report, source_path=path, output_paths=[])
            blocker_rule_ids = [finding.rule.rule_id for finding in report.blockers]
            files.append(
                {
                    "path": str(path),
                    "source_hash": file_sha256(path),
                    "whitepaper_type": report.whitepaper_type.value,
                    "summary_counts": {
                        "pass": len(report.passed),
                        "review": len(report.needs_review),
                        "missing": len(report.missing),
                        "blockers": len(report.blockers),
                        "total": len(report.findings),
                    },
                    "blocker_rule_ids": blocker_rule_ids,
                    "manifest_digest": manifest["overall_digest"],
                    "per_file_eligibility": {
                        "machine_export_ready": not blocker_rule_ids,
                        "review_required": True,
                    },
                }
            )
        except SystemExit as exc:
            warnings.append(f"lint-failed:{path}:{exc}")

    payload = {
        "schema": BATCH_SCHEMA,
        "generated_at": timestamp.isoformat(),
        "root": str(root),
        "summary": {
            "supported_files": len(files),
            "unsupported_files": len(
                [warning for warning in warnings if warning.startswith("unsupported-file:")]
            ),
            "blocked_files": len([item for item in files if item["blocker_rule_ids"]]),
        },
        "files": files,
        "warnings": warnings,
        "review_notice": (
            "Batch review packs contain file metadata, hashes, counts, blockers, and manifest digests only. "
            "Human legal review remains mandatory before external use."
        ),
    }
    payload["digest"] = _digest(payload)
    return payload


def render_batch_review_pack(pack: dict[str, Any]) -> str:
    return json.dumps(pack, indent=2, ensure_ascii=False) + "\n"


def _digest(payload: dict[str, Any]) -> str:
    unsigned = {key: value for key, value in payload.items() if key != "digest"}
    encoded = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
