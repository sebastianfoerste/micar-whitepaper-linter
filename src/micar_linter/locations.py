"""Map findings to a line in the source draft, for CI annotations and SARIF.

A finding concerns a section, not a span of words, so the line is where the
section starts: the key inside the JSON ``sections`` object, or the first
XHTML h1 to h6 heading that maps to the section. Other formats, numbered-field
XHTML, saved iXBRL viewer pages (whose white paper sits packed in a script) and
sections without such a heading, including those the XHTML loader found only
under a bold-text heading, fall back to line 1. Only line numbers
are derived from the draft; no draft text is returned.
"""

from __future__ import annotations

import json
from pathlib import Path

from micar_linter.linter import Report

_WHITESPACE = " \t\n\r"


def finding_lines(report: Report, source_path: Path) -> dict[str, int]:
    """Return the 1-based start line for every finding's rule ID."""
    suffix = source_path.suffix.lower()
    lines: dict[str, int] = {}
    if suffix == ".json":
        text = _read_text(source_path)
        offsets = _json_section_offsets(text)
        for finding in report.findings:
            offset = offsets.get(finding.rule.section)
            lines[finding.rule.rule_id] = text.count("\n", 0, offset) + 1 if offset is not None else 1
    elif suffix in (".xhtml", ".html"):
        # A numbered-field layout takes its sections from template fields, not headings,
        # so a title heading must not be mistaken for a section anchor.
        heading_lines = {} if _is_numbered_layout(source_path) else _xhtml_heading_lines(source_path)
        for finding in report.findings:
            lines[finding.rule.rule_id] = heading_lines.get(finding.rule.section, 1)
    else:
        lines = {finding.rule.rule_id: 1 for finding in report.findings}
    return lines


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _json_section_offsets(text: str) -> dict[str, int]:
    """Character offset of each key in the top-level ``sections`` object.

    Mirrors ``sectionSelection`` in the playground: Python's json keeps the last
    duplicate key, so the last occurrence wins. Malformed text yields no offsets.
    """
    try:
        json.loads(text)
        i = _skip(text, 0)
        if text[i] != "{":
            return {}
        sections = [member for member in _members(text, i) if member[0] == "sections"]
        if not sections or text[sections[-1][2]] != "{":
            return {}
        offsets: dict[str, int] = {}
        for key, start, _ in _members(text, sections[-1][2]):
            offsets[key] = start
        return offsets
    except (ValueError, IndexError):
        return {}


def _skip(text: str, i: int) -> int:
    while i < len(text) and text[i] in _WHITESPACE:
        i += 1
    return i


def _string_end(text: str, i: int) -> int:
    i += 1
    while text[i] != '"':
        i += 2 if text[i] == "\\" else 1
    return i + 1


def _value_end(text: str, i: int) -> int:
    if text[i] == '"':
        return _string_end(text, i)
    if text[i] in "{[":
        depth = 0
        while True:
            if text[i] == '"':
                i = _string_end(text, i)
                continue
            if text[i] in "{[":
                depth += 1
            elif text[i] in "}]":
                depth -= 1
                if depth == 0:
                    return i + 1
            i += 1
    while i < len(text) and text[i] not in _WHITESPACE + ",}]":
        i += 1
    return i


def _members(text: str, i: int) -> list[tuple[str, int, int]]:
    """(key, key offset, value offset) for each member of the object at ``i``."""
    members: list[tuple[str, int, int]] = []
    i = _skip(text, i + 1)
    while text[i] == '"':
        key_end = _string_end(text, i)
        value_start = _skip(text, _skip(text, key_end) + 1)
        members.append((json.loads(text[i:key_end]), i, value_start))
        i = _skip(text, _value_end(text, value_start))
        if text[i] == ",":
            i = _skip(text, i + 1)
    return members


def _is_numbered_layout(path: Path) -> bool:
    try:
        from micar_linter.numbered_fields import extract_numbered_fields, is_numbered_layout

        return is_numbered_layout(extract_numbered_fields(path))
    except Exception:
        return False


def _xhtml_heading_lines(path: Path) -> dict[str, int]:
    """First heading line per section key, matched as the heading loader matches it.

    Numbered-field layouts have no section headings, so their findings stay on line 1.
    """
    try:
        from micar_linter.document import match_heading_to_section
        from micar_linter.xhtml_parser import element_text, parse_html

        tree = parse_html(path)
        headings = tree.xpath("//h1 | //h2 | //h3 | //h4 | //h5 | //h6")
    except Exception:
        return {}
    lines: dict[str, int] = {}
    for heading in headings:
        text = element_text(heading)
        if not text or not heading.sourceline:
            continue
        for section_key in match_heading_to_section(text):
            lines.setdefault(section_key, heading.sourceline)
    return lines
