"""Local white paper vault, interactive review table and reusable playbook projection."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from micar_linter.artifact_manifest import file_sha256
from micar_linter.linter import lint_whitepaper
from micar_linter.review_table import build_review_table
from micar_linter.whitepaper import load_whitepaper

SUPPORTED_SUFFIXES = {".json", ".pdf", ".docx", ".xhtml", ".html", ".md"}


def build_whitepaper_workspace(paths: list[Path]) -> dict[str, Any]:
    source_paths = _expand_paths(paths)
    vault = build_whitepaper_vault(source_paths)
    review_table = build_interactive_review_table(vault)
    return {
        "schema": "micar-whitepaper-linter.workspace.v1",
        "vault": vault,
        "review_table": review_table,
        "playbook": build_review_playbook(review_table),
        "draft_only": True,
        "external_action_allowed": False,
    }


def build_whitepaper_vault(paths: list[Path]) -> dict[str, Any]:
    documents = []
    for path in paths:
        whitepaper = load_whitepaper(path)
        report = lint_whitepaper(whitepaper)
        table = build_review_table(report, source_path=path)
        source_sha256 = file_sha256(path)
        documents.append(
            {
                "document_id": source_sha256,
                "title": whitepaper.title,
                "whitepaper_type": whitepaper.type.value,
                "source_path": str(path),
                "source_sha256": source_sha256,
                "review_table": table,
                "blocker_count": table["summary"]["blockers"],
                "access_mode": "local_review",
            }
        )
    return {
        "schema": "micar-whitepaper-linter.whitepaper-vault.v1",
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "document_count": len(documents),
        "documents": documents,
        "source_hashes": [document["source_sha256"] for document in documents],
        "external_action_allowed": False,
    }


def build_interactive_review_table(vault: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for document in vault["documents"]:
        for row in document["review_table"]["rows"]:
            rows.append(
                {
                    "row_id": f"{document['document_id']}:{row['rule_id']}",
                    "document_id": document["document_id"],
                    "document_title": document["title"],
                    "whitepaper_type": document["whitepaper_type"],
                    "rule_id": row["rule_id"],
                    "citation": row["citation"],
                    "status": row["status"],
                    "blocker": row["blocker"],
                    "condition": {
                        "field": "whitepaper_type",
                        "operator": "equals",
                        "value": document["whitepaper_type"],
                        "result": "applied",
                    },
                    "extracted_value": row["label"],
                    "source_anchor": row["source_anchor"],
                    "remediation": row["remediation"],
                    "manual_input": {
                        "reviewer_note": "",
                        "classification": "unreviewed",
                        "decision": "pending",
                    },
                    "review_cells": row["review_cells"],
                }
            )
    return {
        "schema": "micar-whitepaper-linter.interactive-review-table.v1",
        "instructions": (
            "Apply regime-specific MiCAR rules consistently. Preserve source hashes and "
            "record reviewer judgment only in manual-input fields."
        ),
        "columns": [
            "document",
            "whitepaper_type",
            "rule",
            "citation",
            "status",
            "conditional_scope",
            "remediation",
            "reviewer_note",
            "classification",
            "decision",
        ],
        "rows": rows,
        "summary": {
            "rows": len(rows),
            "documents": vault["document_count"],
            "blockers": sum(row["blocker"] for row in rows),
            "pending_manual_decisions": sum(
                row["manual_input"]["decision"] == "pending" for row in rows
            ),
        },
        "external_action_allowed": False,
    }


def build_review_playbook(review_table: dict[str, Any]) -> dict[str, Any]:
    rules: dict[str, dict[str, Any]] = {}
    for row in review_table["rows"]:
        rule = rules.setdefault(
            row["rule_id"],
            {
                "rule_id": row["rule_id"],
                "citation": row["citation"],
                "applies_to": set(),
                "starting_position": "The required disclosure should be present and supported.",
                "fallbacks": [],
                "red_line": "A blocker remains open or the reviewer rejects the disclosure.",
                "review_gate": "Qualified legal review required before filing or publication.",
            },
        )
        rule["applies_to"].add(row["whitepaper_type"])
        if row["remediation"] and row["remediation"] not in rule["fallbacks"]:
            rule["fallbacks"].append(row["remediation"])
    serialized_rules = []
    for rule in sorted(rules.values(), key=lambda item: item["rule_id"]):
        serialized_rules.append(
            {
                **rule,
                "applies_to": sorted(rule["applies_to"]),
                "fallbacks": rule["fallbacks"][:3],
            }
        )
    return {
        "schema": "micar-whitepaper-linter.review-playbook.v1",
        "rules": serialized_rules,
        "rule_count": len(serialized_rules),
        "source": "local deterministic rule catalog and selected draft review tables",
        "review_gate": "A qualified lawyer must approve changes to positions, fallbacks and red lines.",
        "external_action_allowed": False,
    }


def render_whitepaper_workspace(workspace: dict[str, Any]) -> str:
    return json.dumps(workspace, indent=2, ensure_ascii=False) + "\n"


def _expand_paths(paths: list[Path]) -> list[Path]:
    expanded: list[Path] = []
    for path in paths:
        if path.is_dir():
            expanded.extend(
                candidate
                for candidate in sorted(path.iterdir())
                if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_SUFFIXES
            )
        else:
            expanded.append(path)
    if not expanded:
        raise ValueError("The white paper workspace requires at least one supported local document.")
    return expanded
