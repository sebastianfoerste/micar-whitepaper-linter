"""Collaboration sidecars, MiCAR redlines and reusable review workflows."""

from __future__ import annotations

import json
import tempfile
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from lxml import etree

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NSMAP = {"w": W_NS}


def build_review_sidecar(workspace: dict[str, Any]) -> dict[str, Any]:
    documents = {item["document_id"]: item["source_sha256"] for item in workspace["vault"]["documents"]}
    cells = []
    for row in workspace["review_table"]["rows"]:
        for column in ("status", "remediation", "decision"):
            cells.append(
                {
                    "target_id": f"cell:{row['row_id']}:{column}",
                    "document_id": row["document_id"],
                    "row_id": row["row_id"],
                    "column_id": column,
                    "revision": 1,
                    "reviewer": None,
                    "decision": "pending",
                    "lock": None,
                    "comments": [],
                }
            )
    return {
        "schema": "review.collaboration.v1",
        "document_digests": documents,
        "cells": cells,
        "activity": [],
        "stale": False,
        "external_action_allowed": False,
    }


def reconcile_sidecar(sidecar: dict[str, Any], workspace: dict[str, Any]) -> dict[str, Any]:
    current = {item["document_id"]: item["source_sha256"] for item in workspace["vault"]["documents"]}
    result = json.loads(json.dumps(sidecar))
    result["stale"] = result.get("document_digests") != current
    if result["stale"]:
        result["activity"].append(
            {"event": "source_digest_changed", "occurred_at": datetime(2026, 7, 13, tzinfo=UTC).isoformat()}
        )
    return result


def lock_cell(
    sidecar: dict[str, Any], target_id: str, actor: str, expected_revision: int, now: datetime
) -> dict[str, Any]:
    result = json.loads(json.dumps(sidecar))
    cell = next((item for item in result["cells"] if item["target_id"] == target_id), None)
    if cell is None:
        raise ValueError(f"unknown review cell: {target_id}")
    if cell["revision"] != expected_revision:
        raise ValueError("409 Conflict: stale review cell revision")
    lock = cell.get("lock")
    if lock and datetime.fromisoformat(lock["expires_at"]) > now and lock["actor"] != actor:
        raise ValueError(f"409 Conflict: review cell is locked by {lock['actor']}")
    cell["revision"] += 1
    cell["lock"] = {"actor": actor, "expires_at": (now + timedelta(minutes=15)).isoformat()}
    result["activity"].append(
        {"event": "locked", "target_id": target_id, "actor": actor, "occurred_at": now.isoformat()}
    )
    return result


def build_change_set(workspace: dict[str, Any]) -> dict[str, Any]:
    changes = []
    for row in workspace["review_table"]["rows"]:
        if row["status"] == "PASS":
            continue
        changes.append(
            {
                "id": f"change:{row['row_id']}",
                "document_id": row["document_id"],
                "locator": row["rule_id"],
                "original_text": row["extracted_value"],
                "proposed_text": row["remediation"]
                or "Add the required MiCAR disclosure with verified support.",
                "rationale": f"Review against {row['citation']}",
                "source_refs": [row["citation"], row["source_anchor"]],
                "decision": "pending",
            }
        )
    return {
        "schema": "document.change-set.v1",
        "playbook_version": 1,
        "changes": changes,
        "source_preserved": True,
        "export_allowed": False,
    }


def decide_change(change_set: dict[str, Any], change_id: str, decision: str) -> dict[str, Any]:
    if decision not in {"accepted", "rejected"}:
        raise ValueError("decision must be accepted or rejected")
    result = json.loads(json.dumps(change_set))
    change = next((item for item in result["changes"] if item["id"] == change_id), None)
    if change is None:
        raise ValueError(f"unknown change: {change_id}")
    change["decision"] = decision
    result["export_allowed"] = bool(result["changes"]) and all(
        item["decision"] == "accepted" for item in result["changes"]
    )
    return result


def render_tracked_docx(
    source: Path, output: Path, change_set: dict[str, Any], author: str = "MiCAR reviewer"
) -> Path:
    if source.resolve() == output.resolve():
        raise ValueError("redline output must not overwrite the source document")
    if not change_set.get("export_allowed"):
        raise ValueError("tracked DOCX export requires all changes to be accepted")
    with tempfile.TemporaryDirectory() as temp_dir:
        extracted = Path(temp_dir)
        with zipfile.ZipFile(source) as package:
            package.extractall(extracted)
        document_path = extracted / "word" / "document.xml"
        tree = etree.parse(str(document_path))
        body = tree.find("w:body", NSMAP)
        if body is None:
            raise ValueError("DOCX is missing word/document.xml body")
        section = body.find("w:sectPr", NSMAP)
        for index, change in enumerate(change_set["changes"], start=1):
            paragraph = etree.Element(f"{{{W_NS}}}p")
            deleted = etree.SubElement(
                paragraph,
                f"{{{W_NS}}}del",
                {
                    f"{{{W_NS}}}id": str(index * 2),
                    f"{{{W_NS}}}author": author,
                    f"{{{W_NS}}}date": "2026-07-13T00:00:00Z",
                },
            )
            deleted_run = etree.SubElement(deleted, f"{{{W_NS}}}r")
            etree.SubElement(deleted_run, f"{{{W_NS}}}delText").text = (
                change["original_text"] or "Missing disclosure"
            )
            inserted = etree.SubElement(
                paragraph,
                f"{{{W_NS}}}ins",
                {
                    f"{{{W_NS}}}id": str(index * 2 + 1),
                    f"{{{W_NS}}}author": author,
                    f"{{{W_NS}}}date": "2026-07-13T00:00:00Z",
                },
            )
            inserted_run = etree.SubElement(inserted, f"{{{W_NS}}}r")
            etree.SubElement(inserted_run, f"{{{W_NS}}}t").text = change["proposed_text"]
            body.insert(body.index(section) if section is not None else len(body), paragraph)
        tree.write(str(document_path), xml_declaration=True, encoding="UTF-8", standalone=True)
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as target:
            for path in sorted(extracted.rglob("*")):
                if path.is_file():
                    target.write(path, path.relative_to(extracted))
    return output


def build_workflow_pack(
    workspace: dict[str, Any], sidecar: dict[str, Any], change_set: dict[str, Any]
) -> dict[str, Any]:
    definitions = [
        {
            "schema": "workflow.definition.v1",
            "id": "micar-whitepaper-review",
            "version": 1,
            "status": "active",
            "steps": [
                "lint",
                "triage",
                "citation_verification",
                "remediation",
                "human_review",
                "export_gate",
            ],
            "external_action_allowed": False,
        }
    ]
    blockers = workspace["review_table"]["summary"]["blockers"]
    pending = sum(cell["decision"] == "pending" for cell in sidecar["cells"])
    run = {
        "schema": "workflow.run.v1",
        "id": "run:micar-whitepaper-review:v1",
        "definition_version": 1,
        "status": "blocked" if blockers or pending or sidecar.get("stale") else "review_required",
        "blockers": {
            "lint": blockers,
            "pending_review_cells": pending,
            "stale_sidecar": bool(sidecar.get("stale")),
        },
        "artifacts": ["review-table", "document-change-set"],
        "export_allowed": bool(change_set.get("export_allowed")) and not blockers and not pending,
        "external_action_allowed": False,
    }
    return {"definitions": definitions, "run": run}


def write_legora_bundle(workspace: dict[str, Any], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    sidecar = build_review_sidecar(workspace)
    change_set = build_change_set(workspace)
    workflow = build_workflow_pack(workspace, sidecar, change_set)
    outputs = []
    for name, payload in (
        ("review-sidecar.json", sidecar),
        ("document-change-set.json", change_set),
        ("workflow-pack.json", workflow),
    ):
        path = output_dir / name
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        outputs.append(path)
    return outputs
