"""Metadata-only source anchors for findings and remediation items."""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from micar_linter.document import match_heading_to_section
from micar_linter.rules.base import Finding
from micar_linter.whitepaper import Whitepaper


@dataclass(frozen=True)
class SourceAnchor:
    section_key: str
    parser_source_type: str
    stable_anchor_id: str
    section_length: int

    def to_json(self) -> dict[str, int | str]:
        return asdict(self)


def build_source_anchors(whitepaper: Whitepaper, findings: tuple[Finding, ...]) -> dict[str, SourceAnchor]:
    source_file = str(whitepaper.metadata.get("source_file", ""))
    source_type = _source_type(source_file)
    xhtml_ids = _xhtml_section_identifiers(Path(source_file)) if source_type in {"xhtml", "html"} else {}

    anchors: dict[str, SourceAnchor] = {}
    for finding in findings:
        section_key = finding.rule.section
        section_text = whitepaper.section(section_key)
        detected_id = xhtml_ids.get(section_key)
        stable_anchor_id = detected_id or _stable_anchor_id(
            source_type=source_type,
            section_key=section_key,
            rule_id=finding.rule.rule_id,
            section_length=len(section_text),
        )
        anchors[finding.rule.rule_id] = SourceAnchor(
            section_key=section_key,
            parser_source_type=source_type,
            stable_anchor_id=stable_anchor_id,
            section_length=len(section_text),
        )
    return anchors


def _source_type(source_file: str) -> str:
    suffix = Path(source_file).suffix.lower().lstrip(".")
    return suffix or "json"


def _stable_anchor_id(*, source_type: str, section_key: str, rule_id: str, section_length: int) -> str:
    anchor_seed = f"{source_type}:{section_key}:{rule_id}:{section_length}"
    digest = hashlib.sha256(anchor_seed.encode()).hexdigest()
    return f"{source_type}:{section_key}:{digest[:16]}"


def _xhtml_section_identifiers(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        from lxml import etree

        parser = etree.HTMLParser(encoding="utf-8")
        tree = etree.parse(str(path), parser=parser)
        elements = tree.xpath("//h1 | //h2 | //h3 | //h4 | //h5 | //h6")
    except Exception:
        return {}

    identifiers: dict[str, str] = {}
    for elem in elements:
        text = re.sub(r"\s+", " ", "".join(elem.itertext()).strip())
        if not text:
            continue
        element_id = elem.get("id") or elem.get("{http://www.w3.org/XML/1998/namespace}id")
        if not element_id:
            continue
        for section_key in match_heading_to_section(text):
            identifiers.setdefault(section_key, f"xhtml:{_safe_id(element_id)}")
    return identifiers


def _safe_id(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_.:-]+", "-", value.strip())
    return normalized.strip("-") or "section"
