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
from dataclasses import dataclass
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
    """Whether the match covers all of ``link``'s content, and that content is plain text.

    A link that wraps a content control, custom XML or a bidi element does not qualify: the replacement goes
    after the link and would leave that element empty.
    """
    if link.xpath(".//w:sdt | .//w:customXml | .//w:dir | .//w:bdo", namespaces=NSMAP):
        return False
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
    # over a selection, without another author's pending formatting revision.
    inserted_run = _sibling_run(deleted_runs[0], ids)
    dropped = "w:rPr/w:rPrChange"
    if first_link is not None and not inside_link:
        dropped += " | w:rPr/w:rStyle | w:rPr/w:color | w:rPr/w:u"
    for prop in inserted_run.xpath(dropped, namespaces=NSMAP):
        prop.getparent().remove(prop)
    inserted_run.append(_text_element("t", proposed))
    inserted.append(inserted_run)
    anchor.addnext(inserted)
    excluded.add(inserted)


def _contents_styles(styles_path: Path, parser: etree.XMLParser) -> set[str]:
    """Ids of the table-of-contents paragraph styles: Word's built-in ids, and any style named "toc 1" to
    "toc 9" or "contents 1" to "contents 9", whatever id the document language gives it."""
    levels = range(1, 10)
    ids = {f"TOC{level}" for level in levels}
    if not styles_path.exists():
        return ids
    names = {f"{prefix} {level}" for prefix in ("toc", "contents") for level in levels}
    return ids | {
        style.get(f"{{{W_NS}}}styleId")
        for style in etree.parse(str(styles_path), parser=parser).xpath(
            "w:style[@w:type='paragraph']", namespaces=NSMAP
        )
        if style.xpath("string(w:name/@w:val)", namespaces=NSMAP).lower() in names
    }


@dataclass(frozen=True)
class TrackedDocxExport:
    """What export_tracked_docx wrote: the output path and the ids of the accepted changes it placed in the
    document, appended at its end because their original text was not found, or left out because they belong
    to another document of the change set. A change without an id is named by its position, "changes[3]"."""

    path: Path
    placed: tuple[str, ...]
    unplaced: tuple[str, ...]
    skipped: tuple[str, ...]


def render_tracked_docx(
    source: Path, output: Path, change_set: dict[str, Any], author: str = "MiCAR reviewer"
) -> Path:
    """Write the tracked DOCX and return its path; export_tracked_docx also reports the changes not placed."""
    return export_tracked_docx(source, output, change_set, author).path


def export_tracked_docx(
    source: Path, output: Path, change_set: dict[str, Any], author: str = "MiCAR reviewer"
) -> TrackedDocxExport:
    """Write a copy of the source DOCX with the accepted changes of the change set as tracked revisions.

    A change whose original text is found in the document is written in place as a tracked deletion and
    insertion. One that is not found is appended at the end of the body as a tracked insertion alone, with
    no deletion of text the document never held (#61), and its id is reported as unplaced. With a change set
    that names its documents (`source_digests`), only the changes whose `document_id` maps to the source's
    digest apply, besides changes without a `document_id`; the others are reported as skipped (#60).
    """
    if source.resolve() == output.resolve():
        raise ValueError("redline output must not overwrite the source document")
    if not change_set.get("export_allowed"):
        raise ValueError("tracked DOCX export requires every change to be decided")
    source_digests: dict[str, str] = change_set.get("source_digests") or {}
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if source_digests and digest not in set(source_digests.values()):
        raise ValueError("source DOCX digest does not match the reviewed workspace")
    document_ids = {document_id for document_id, value in source_digests.items() if value == digest}
    placed: list[str] = []
    unplaced: list[str] = []
    skipped: list[str] = []
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
        namespaces = {**NSMAP, "mc": MC_NS}
        # A table of contents that is not a field repeats the headings as plain text: try its paragraphs last,
        # so a change to a heading reaches the heading.
        candidates = body.xpath(".//w:p[not(ancestor::mc:Fallback)]", namespaces=namespaces)
        contents_styles = _contents_styles(extracted / "word" / "styles.xml", parser)
        contents = {
            paragraph
            for paragraph in candidates
            if paragraph.xpath("string(w:pPr/w:pStyle/@w:val)", namespaces=NSMAP) in contents_styles
            or paragraph.xpath(
                "ancestor::w:sdt[w:sdtPr/w:docPartObj/w:docPartGallery/@w:val='Table of Contents']",
                namespaces=NSMAP,
            )
        }
        candidates = [p for p in candidates if p not in contents] + [p for p in candidates if p in contents]
        for index, change in enumerate(change_set["changes"]):
            if change["decision"] != "accepted":
                continue
            change_id = str(change.get("id") or f"changes[{index}]")
            document_id = change.get("document_id")
            if source_digests and document_id is not None and document_id not in document_ids:
                skipped.append(change_id)
                continue
            original = change.get("original_text") or ""
            proposed = change.get("proposed_text") or ""
            match = next(
                (
                    found
                    for candidate in (candidates if original else [])
                    if original in "".join(candidate.xpath(_LIVE_TEXT, namespaces=namespaces))
                    and (found := _find_match(candidate, original, excluded))
                ),
                None,
            )
            if match is not None:
                _redline_match(*match, original, proposed, ids, author, change_timestamp, excluded)
                placed.append(change_id)
                continue
            # The original text is not in the document (for a change set built from a draft, it is the rule
            # label, #59), so the proposed text is appended as an insertion that Reject All removes whole.
            insertion = _revision("ins", ids, author, change_timestamp)
            inserted_run = etree.SubElement(insertion, f"{{{W_NS}}}r")
            etree.SubElement(inserted_run, f"{{{W_NS}}}t").text = proposed
            excluded.add(insertion)
            paragraph = etree.Element(f"{{{W_NS}}}p")
            paragraph.append(insertion)
            body.insert(body.index(section) if section is not None else len(body), paragraph)
            unplaced.append(change_id)
        tree.write(str(document_path), xml_declaration=True, encoding="UTF-8", standalone=True)
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as target:
            for path in sorted(extracted.rglob("*")):
                if path.is_file():
                    target.write(path, path.relative_to(extracted))
    return TrackedDocxExport(output, tuple(placed), tuple(unplaced), tuple(skipped))


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


_DEFINITION_SCHEMA = "workflow.definition.v1"
_RUN_SCHEMA = "workflow.run.v1"
_DEFINITION_STATUSES = {"active", "draft", "retired"}
_RUN_STATUSES = {"blocked", "review_required"}
# The decision of a review cell: "pending" from build_review_sidecar, the others from update_cell.
_CELL_DECISIONS = {"pending", "approved", "changes_requested", "rejected"}
_DIGEST = 64


def _is_string_list(value: Any, non_empty: bool = False) -> bool:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return False
    return bool(value) or not non_empty


def _definition_problems(definition: Any) -> list[str]:
    if not isinstance(definition, dict):
        return ["expected an object"]
    problems = []
    if definition.get("schema") != _DEFINITION_SCHEMA:
        problems.append(f"schema is not {_DEFINITION_SCHEMA}")
    if not isinstance(definition.get("id"), str) or not definition["id"]:
        problems.append("id is missing or empty")
    if not isinstance(definition.get("version"), int) or definition["version"] < 1:
        problems.append("version is not a positive integer")
    if definition.get("status") not in _DEFINITION_STATUSES:
        problems.append("status is not one of " + ", ".join(sorted(_DEFINITION_STATUSES)))
    for key in ("source_policy", "input_schema"):
        if not isinstance(definition.get(key), str) or not definition[key]:
            problems.append(f"{key} is missing or empty")
    for key in ("permitted_roles", "artifact_contracts", "steps"):
        if not _is_string_list(definition.get(key), non_empty=True):
            problems.append(f"{key} is not a non-empty list of strings")
    if "export_gate" not in (definition.get("steps") or []):
        problems.append("steps do not end in the export gate")
    if definition.get("external_action_allowed") is not False:
        problems.append("external_action_allowed is not false")
    return problems


def _run_problems(run: dict[str, Any], definitions: list[Any]) -> list[str]:
    problems = []
    if run.get("schema") != _RUN_SCHEMA:
        problems.append(f"schema is not {_RUN_SCHEMA}")
    if not isinstance(run.get("id"), str) or not run["id"]:
        problems.append("id is missing or empty")
    version = run.get("definition_version")
    snapshot = run.get("definition_snapshot")
    if not isinstance(version, int):
        problems.append("definition_version is not an integer")
    if not any(
        isinstance(item, dict) and item == snapshot and item.get("version") == version for item in definitions
    ):
        problems.append("definition_snapshot is not one of the definitions at definition_version")
    inputs = run.get("inputs")
    workspace_digest = inputs.get("workspace_digest") if isinstance(inputs, dict) else None
    if not (
        isinstance(workspace_digest, str) and len(workspace_digest) == _DIGEST and _is_hex(workspace_digest)
    ):
        problems.append("inputs.workspace_digest is not a SHA-256 hex digest")
    if not _is_string_list(run.get("source_refs")):
        problems.append("source_refs is not a list of strings")
    decisions = run.get("decisions")
    if not _is_string_list(decisions) or any(item not in _CELL_DECISIONS for item in decisions):
        problems.append("decisions is not a list of review cell decisions")
        decisions = []
    if not isinstance(run.get("audit"), list):
        problems.append("audit is not a list")
    if not _is_string_list(run.get("artifacts"), non_empty=True):
        problems.append("artifacts is not a non-empty list of strings")
    blockers = run.get("blockers")
    if not isinstance(blockers, dict):
        problems.append("blockers is not an object")
        return problems
    lint, pending = blockers.get("lint"), blockers.get("pending_review_cells")
    stale = blockers.get("stale_sidecar")
    counts_valid = all(
        isinstance(value, int) and not isinstance(value, bool) and value >= 0 for value in (lint, pending)
    )
    if not counts_valid:
        problems.append("blockers.lint and blockers.pending_review_cells are not non-negative integers")
    if not isinstance(stale, bool):
        problems.append("blockers.stale_sidecar is not a boolean")
    if counts_valid and pending != decisions.count("pending"):
        problems.append("blockers.pending_review_cells does not count the pending decisions")
    status = run.get("status")
    if status not in _RUN_STATUSES:
        problems.append("status is not one of " + ", ".join(sorted(_RUN_STATUSES)))
    elif counts_valid and isinstance(stale, bool):
        expected = "blocked" if lint or pending or stale else "review_required"
        if status != expected:
            problems.append(f"status {status} does not follow from the blockers ({expected} expected)")
    export_allowed = run.get("export_allowed")
    if not isinstance(export_allowed, bool):
        problems.append("export_allowed is not a boolean")
    elif export_allowed and counts_valid and (lint or pending):
        problems.append("export_allowed is true while lint blockers or pending review cells remain")
    if run.get("external_action_allowed") is not False:
        problems.append("external_action_allowed is not false")
    return problems


def _is_hex(value: str) -> bool:
    return all(character in "0123456789abcdef" for character in value)


def validate_workflow_pack(pack: Any) -> list[str]:
    """The structural problems of a workflow pack from build_workflow_pack, or an empty list when it is sound.

    Checks the schema ids and required keys of every definition and of the run, that no definition or run
    allows an external action, that the run's definition snapshot is one of the definitions, that its status
    follows from its blockers (lint blockers, pending review cells, a stale sidecar), that the pending count
    matches the decisions, and that the export gate stays closed while blockers or pending cells remain. It
    does not decide whether the review is complete.
    """
    if not isinstance(pack, dict):
        return ["workflow pack is not an object"]
    problems: list[str] = []
    definitions = pack.get("definitions")
    if not isinstance(definitions, list) or not definitions:
        problems.append("definitions: expected a non-empty list")
        definitions = []
    for index, definition in enumerate(definitions):
        problems.extend(f"definitions[{index}]: {problem}" for problem in _definition_problems(definition))
    run = pack.get("run")
    if not isinstance(run, dict):
        problems.append("run: expected an object")
    else:
        problems.extend(f"run: {problem}" for problem in _run_problems(run, definitions))
    return problems


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
