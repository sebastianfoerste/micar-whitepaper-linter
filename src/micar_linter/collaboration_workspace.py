"""Collaboration sidecars, MiCAR redlines and reusable review workflows."""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
import os
import tempfile
import zipfile
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from lxml import etree

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NSMAP = {"w": W_NS}
# Paragraph content skipped without ending a match: deleted or moved-away text, properties and range markers.
# A drawing, including its hidden mc:Fallback copy, ends a match; paragraphs inside mc:Fallback are never
# candidates (see render_tracked_docx).
_SKIPPED = {
    f"{{{W_NS}}}{name}"
    for name in [
        "del",
        "moveFrom",
        "pPr",
        "sdtPr",
        "sdtEndPr",
        "smartTagPr",
        "customXmlPr",
        "proofErr",
        "bookmarkStart",
        "bookmarkEnd",
        "commentRangeStart",
        "commentRangeEnd",
        "permStart",
        "permEnd",
        "moveFromRangeStart",
        "moveFromRangeEnd",
        "moveToRangeStart",
        "moveToRangeEnd",
    ]
}
# Containers a match runs through: pending insertions and moves, smart tags, custom XML and hyperlinks. A
# match must start and end in the same custom XML element, or outside any, so it keeps its extent; for
# hyperlinks see _links_kept.
_TRANSPARENT = {f"{{{W_NS}}}{name}" for name in ["ins", "moveTo", "smartTag", "customXml", "hyperlink"]}
# Containers a match may lie inside but not cross, so a content control keeps its value. Other paragraph
# content (an equation or a simple field, for example) ends a match.
_CONTAINERS = {f"{{{W_NS}}}{name}" for name in ["sdt", "sdtContent", "dir", "bdo"]}
# Run content a match may span. Other run content (tabs, breaks, field characters, drawings) ends a match,
# as do hidden runs, regenerated text and this export's own insertions.
_SPANNABLE = {
    f"{{{W_NS}}}{name}"
    for name in ("rPr", "t", "lastRenderedPageBreak", "softHyphen", "commentReference", "annotationRef")
}
_LIVE_TEXT = ".//w:t[not(ancestor::w:del) and not(ancestor::w:moveFrom)]/text()"


def _reproducible_timestamp() -> str:
    raw_epoch = os.environ.get("SOURCE_DATE_EPOCH", "0")
    try:
        timestamp = datetime.fromtimestamp(int(raw_epoch), UTC)
    except (ValueError, OverflowError, OSError) as error:
        raise ValueError("SOURCE_DATE_EPOCH must be a valid integer Unix timestamp") from error
    return timestamp.replace(microsecond=0).isoformat().replace("+00:00", "Z")


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


def update_cell(
    sidecar: dict[str, Any],
    target_id: str,
    actor: str,
    expected_revision: int,
    now: datetime,
    *,
    assignee: str | None = None,
    comment: str | None = None,
    decision: str | None = None,
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
    if decision is not None and decision not in {"approved", "changes_requested", "rejected"}:
        raise ValueError("invalid review decision")
    if comment is not None and not comment.strip():
        raise ValueError("comment body is required")
    cell["revision"] += 1
    if assignee is not None:
        cell["reviewer"] = assignee
    if decision is not None:
        cell["decision"] = decision
    if comment is not None:
        cell["comments"].append(
            {
                "id": f"comment:{cell['revision']}",
                "author": actor,
                "body": comment.strip(),
                "created_at": now.isoformat(),
                "status": "open",
            }
        )
    result["activity"].append(
        {
            "event": "review_cell_updated",
            "target_id": target_id,
            "actor": actor,
            "occurred_at": now.isoformat(),
            "revision": cell["revision"],
        }
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
        "source_digests": {
            item["document_id"]: item["source_sha256"] for item in workspace["vault"]["documents"]
        },
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
        item["decision"] in {"accepted", "rejected"} for item in result["changes"]
    )
    return result


def _revision(tag: str, ids: Iterator[int], author: str, date: str) -> etree._Element:
    return etree.Element(
        f"{{{W_NS}}}{tag}",
        {f"{{{W_NS}}}id": str(next(ids)), f"{{{W_NS}}}author": author, f"{{{W_NS}}}date": date},
    )


def _text_element(tag: str, text: str) -> etree._Element:
    element = etree.Element(f"{{{W_NS}}}{tag}")
    element.text = text
    element.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    return element


def _sibling_run(run: etree._Element, ids: Iterator[int]) -> etree._Element:
    sibling = etree.Element(run.tag, dict(run.attrib))
    properties = run.find("w:rPr", NSMAP)
    if properties is not None:
        properties = copy.deepcopy(properties)
        for change in properties.iter(f"{{{W_NS}}}rPrChange"):
            change.set(f"{{{W_NS}}}id", str(next(ids)))
        sibling.append(properties)
    return sibling


def _regenerated_text(body: etree._Element) -> set[etree._Element]:
    """``w:t`` nodes Word manages itself: complex field results and the text of content controls that are
    bound to a data store, show their placeholder, or hold a date, list or checkbox value. A simple field
    (``w:fldSimple``) needs no entry, because _text_segments ends a match at it without entering it.

    Word and LibreOffice regenerate or reset that text, so a redline placed there is lost or misread.
    """
    managed = " or ".join(
        f"local-name()='{name}'"
        for name in ("dataBinding", "showingPlcHdr", "date", "dropDownList", "comboBox", "checkbox")
    )
    query = f".//w:sdt[w:sdtPr/*[{managed}]]/w:sdtContent//w:t"
    inside = set(body.xpath(query, namespaces=NSMAP))
    depth = 0
    for element in body.iter(f"{{{W_NS}}}fldChar", f"{{{W_NS}}}t"):
        if element.tag == f"{{{W_NS}}}t":
            if depth:
                inside.add(element)
        elif element.get(f"{{{W_NS}}}fldCharType") == "begin":
            depth += 1
        elif element.get(f"{{{W_NS}}}fldCharType") == "end":
            depth = max(depth - 1, 0)
    return inside


def _hidden(element: etree._Element) -> bool:
    vanish = element.find("w:rPr/w:vanish", NSMAP) if element.tag == f"{{{W_NS}}}r" else None
    return vanish is not None and vanish.get(f"{{{W_NS}}}val", "true") not in {"0", "false", "off"}


def _text_segments(
    element: etree._Element, excluded: set[etree._Element], segments: list[list[etree._Element]]
) -> list[list[etree._Element]]:
    """Group the live ``w:t`` nodes of a paragraph into stretches that a match may span."""
    for child in element:
        if child.tag in _SKIPPED:
            continue
        if child in excluded or _hidden(child):
            segments.append([])
        elif child.tag == f"{{{W_NS}}}r":
            for item in child:
                if item.tag == f"{{{W_NS}}}t" and item not in excluded:
                    segments[-1].append(item)
                elif item.tag not in _SPANNABLE or item.tag == f"{{{W_NS}}}t":
                    segments.append([])
        elif child.tag in _TRANSPARENT:
            _text_segments(child, excluded, segments)
        elif child.tag in _CONTAINERS:
            segments.append([])
            _text_segments(child, excluded, segments)
            segments.append([])
        else:
            segments.append([])
    return segments


def _covered(nodes: list[etree._Element], start: int, end: int) -> list[tuple[etree._Element, int, int]]:
    """The nodes that ``[start, end)`` of their joined text covers, with the covered slice of each."""
    covered = []
    offset = 0
    for node in nodes:
        length = len(node.text or "")
        overlap_start, overlap_end = max(start, offset), min(end, offset + length)
        if overlap_start < overlap_end:
            covered.append((node, overlap_start - offset, overlap_end - offset))
        offset += length
    return covered


def _bounds(node: etree._Element) -> tuple[etree._Element | None, etree._Element | None]:
    """The nearest hyperlink and custom XML element around ``node`` within its paragraph."""
    link = tagged = None
    for ancestor in node.iterancestors():
        if ancestor.tag == f"{{{W_NS}}}p":
            break
        if ancestor.tag == f"{{{W_NS}}}hyperlink" and link is None:
            link = ancestor
        elif ancestor.tag == f"{{{W_NS}}}customXml" and tagged is None:
            tagged = ancestor
    return link, tagged


def _external(link: etree._Element | None) -> bool:
    return link is not None and link.get(f"{{{R_NS}}}id") is not None


def _whole_plain(link: etree._Element, covered: list[tuple[etree._Element, int, int]]) -> bool:
    """Whether the match covers all of ``link``'s content, and that content is plain text."""
    runs = link.xpath(".//w:r[not(ancestor::w:del) and not(ancestor::w:moveFrom)]", namespaces=NSMAP)
    if not all(child.tag in _SPANNABLE for run in runs for child in run):
        return False
    full = {node for node, start, end in covered if start == 0 and end == len(node.text or "")}
    return all(node in full or not node.text for run in runs for node in run.iterchildren(f"{{{W_NS}}}t"))


def _links_kept(
    first_link: etree._Element | None,
    last_link: etree._Element | None,
    covered: list[tuple[etree._Element, int, int]],
) -> bool:
    """Whether redlining the match leaves every hyperlink it touches with the right extent and target.

    A match inside an internal link stays there. A match that only partly covers a link at either end would
    move the link's edge, and new text inside a link to an external target would inherit the old target. A
    link the match covers wholly, holding plain text, is fine: it is deleted and the replacement follows it.
    """
    if first_link is last_link and not _external(first_link):
        return True
    return all(link is None or _whole_plain(link, covered) for link in (first_link, last_link))


def _find_match(
    paragraph: etree._Element, original: str, excluded: set[etree._Element]
) -> tuple[list[etree._Element], int] | None:
    for nodes in _text_segments(paragraph, excluded, [[]]):
        text = "".join(node.text or "" for node in nodes)
        start = text.find(original)
        while start >= 0:
            covered = _covered(nodes, start, start + len(original))
            (first_link, first_tagged), (last_link, last_tagged) = (
                _bounds(covered[0][0]),
                _bounds(covered[-1][0]),
            )
            if first_tagged is last_tagged and _links_kept(first_link, last_link, covered):
                return nodes, start
            start = text.find(original, start + 1)
    return None


def _isolate(item: etree._Element, ids: Iterator[int]) -> etree._Element:
    """Move the rest of the run of ``item`` into sibling runs; return the run, now holding only ``item``."""
    run = item.getparent()
    content = [child for child in run if child.tag != f"{{{W_NS}}}rPr"]
    position = content.index(item)
    if content[:position]:
        before = _sibling_run(run, ids)
        before.extend(content[:position])
        run.addprevious(before)
    if content[position + 1 :]:
        after = _sibling_run(run, ids)
        after.extend(content[position + 1 :])
        run.addnext(after)
    return run


def _isolate_text(node: etree._Element, start: int, end: int, ids: Iterator[int]) -> etree._Element:
    """Split the run of ``node`` so that a run of its own holds ``node.text[start:end]``; return that run."""
    run = _isolate(node, ids)
    text = node.text or ""
    if text[:start]:
        prefix = _sibling_run(run, ids)
        prefix.append(_text_element("t", text[:start]))
        run.addprevious(prefix)
    if text[end:]:
        suffix = _sibling_run(run, ids)
        suffix.append(_text_element("t", text[end:]))
        run.addnext(suffix)
    node.text = text[start:end]
    node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    return run


def _redline_match(
    nodes: list[etree._Element],
    match_start: int,
    original: str,
    proposed: str,
    ids: Iterator[int],
    author: str,
    date: str,
    excluded: set[etree._Element],
) -> None:
    """Track the deletion of ``original`` at ``match_start`` in ``nodes`` and the insertion of ``proposed``.

    Text before and after the match, the paragraph properties and the run formatting stay as they are,
    so rejecting the change in Word restores the paragraph.
    """
    matched = _covered(nodes, match_start, match_start + len(original))
    first, last = matched[0][0], matched[-1][0]
    soft_hyphens, inside = [], False
    for element in next(first.iterancestors(f"{{{W_NS}}}p")).iter(f"{{{W_NS}}}t", f"{{{W_NS}}}softHyphen"):
        if element is last:
            break
        if element is first:
            inside = True
        elif (
            inside
            and element.tag == f"{{{W_NS}}}softHyphen"
            and not any(ancestor.tag in _SKIPPED for ancestor in element.iterancestors())
        ):
            soft_hyphens.append(element)
    deleted_runs = []
    for node, start, end in matched:
        deleted_runs.append(_isolate_text(node, start, end, ids))
        node.tag = f"{{{W_NS}}}delText"
    for run in [_isolate(hyphen, ids) for hyphen in soft_hyphens] + deleted_runs:
        anchor = _revision("del", ids, author, date)
        run.addprevious(anchor)
        anchor.append(run)
    # A link the match covers wholly is deleted with it, and the replacement goes after the link without the
    # link's look, so it neither extends the link nor keeps its target. A match inside an internal link stays
    # inside it.
    first_link, last_link = _bounds(first)[0], _bounds(last)[0]
    inside_link = first_link is not None and first_link is last_link and not _external(first_link)
    if last_link is not None and not inside_link:
        anchor = last_link
    while anchor.getparent().tag in {f"{{{W_NS}}}ins", f"{{{W_NS}}}moveTo"}:
        outer = anchor.getparent()
        following = list(anchor.itersiblings())
        if following:
            rest = etree.Element(outer.tag, dict(outer.attrib))
            rest.set(f"{{{W_NS}}}id", str(next(ids)))
            rest.extend(following)
            outer.addnext(rest)
        anchor = outer
    inserted = _revision("ins", ids, author, date)
    # The replacement takes the formatting of the first replaced character, as Word does when text is typed
    # over a selection.
    inserted_run = _sibling_run(deleted_runs[0], ids)
    if first_link is not None and not inside_link:
        for look in inserted_run.xpath("w:rPr/w:rStyle | w:rPr/w:color | w:rPr/w:u", namespaces=NSMAP):
            look.getparent().remove(look)
    inserted_run.append(_text_element("t", proposed))
    inserted.append(inserted_run)
    anchor.addnext(inserted)
    excluded.add(inserted)


def render_tracked_docx(
    source: Path, output: Path, change_set: dict[str, Any], author: str = "MiCAR reviewer"
) -> Path:
    if source.resolve() == output.resolve():
        raise ValueError("redline output must not overwrite the source document")
    if not change_set.get("export_allowed"):
        raise ValueError("tracked DOCX export requires every change to be decided")
    expected_digests = set(change_set.get("source_digests", {}).values())
    if expected_digests and hashlib.sha256(source.read_bytes()).hexdigest() not in expected_digests:
        raise ValueError("source DOCX digest does not match the reviewed workspace")
    change_timestamp = _reproducible_timestamp()
    with tempfile.TemporaryDirectory() as temp_dir:
        extracted = Path(temp_dir)
        with zipfile.ZipFile(source) as package:
            package.extractall(extracted)
        document_path = extracted / "word" / "document.xml"
        parser = etree.XMLParser(resolve_entities=False, no_network=True)
        tree = etree.parse(str(document_path), parser=parser)
        body = tree.find("w:body", NSMAP)
        if body is None:
            raise ValueError("DOCX is missing word/document.xml body")
        section = body.find("w:sectPr", NSMAP)
        used_ids = [
            int(value)
            for value in tree.xpath("//@w:id", namespaces=NSMAP)
            if value.isascii() and value.isdigit()
        ]
        ids = itertools.count(max(used_ids, default=0) + 1)
        excluded = _regenerated_text(body)
        paragraphs = ".//w:p[not(ancestor::mc:Fallback)]"
        namespaces = {**NSMAP, "mc": MC_NS}
        for change in (item for item in change_set["changes"] if item["decision"] == "accepted"):
            original = change["original_text"]
            proposed = change.get("proposed_text") or ""
            match = next(
                (
                    found
                    for candidate in (body.xpath(paragraphs, namespaces=namespaces) if original else [])
                    if original in "".join(candidate.xpath(_LIVE_TEXT, namespaces=namespaces))
                    and (found := _find_match(candidate, original, excluded))
                ),
                None,
            )
            if match is not None:
                _redline_match(*match, original, proposed, ids, author, change_timestamp, excluded)
                continue
            deletion = _revision("del", ids, author, change_timestamp)
            deleted_run = etree.SubElement(deletion, f"{{{W_NS}}}r")
            etree.SubElement(deleted_run, f"{{{W_NS}}}delText").text = original or "Missing disclosure"
            insertion = _revision("ins", ids, author, change_timestamp)
            inserted_run = etree.SubElement(insertion, f"{{{W_NS}}}r")
            etree.SubElement(inserted_run, f"{{{W_NS}}}t").text = proposed
            excluded.add(insertion)
            paragraph = etree.Element(f"{{{W_NS}}}p")
            paragraph.extend([deletion, insertion])
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
            "source_policy": "approved workspace documents and pinned MiCAR citations only",
            "permitted_roles": ["legal_reviewer", "approver"],
            "input_schema": "micar.whitepaper.workspace.v1",
            "artifact_contracts": ["review.collaboration.v1", "document.change-set.v1"],
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
        "definition_snapshot": definitions[0],
        "inputs": {
            "workspace_digest": hashlib.sha256(
                json.dumps(
                    {item["document_id"]: item["source_sha256"] for item in workspace["vault"]["documents"]},
                    sort_keys=True,
                ).encode()
            ).hexdigest()
        },
        "source_refs": sorted({row["citation"] for row in workspace["review_table"]["rows"]}),
        "decisions": [cell["decision"] for cell in sidecar["cells"]],
        "audit": list(sidecar["activity"]),
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


def write_collaboration_bundle(workspace: dict[str, Any], output_dir: Path) -> list[Path]:
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
