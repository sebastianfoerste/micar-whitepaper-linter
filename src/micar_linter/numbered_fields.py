"""Section extraction for white papers laid out as the numbered fields of
Implementing Regulation (EU) 2024/2984 ("A.1 Name", "A.2 Legal form", ...).

Notified white papers follow that template rather than prose headings, so the
heading-based loader finds little in them. Field numbers vary between authors;
only the part letter is treated as reliable.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from lxml import etree

from micar_linter.placeholders import is_not_applicable, is_placeholder
from micar_linter.whitepaper import WhitepaperType
from micar_linter.xhtml_parser import element_text, text_fragments

# A layout counts as numbered once fields from this many distinct parts carry content.
MIN_PARTS = 3

_FIELD_ID = re.compile(
    r"^(?:(?P<part>[A-Z]{1,2})\.(?P<number>\d{1,2})|(?P<summary>\d{2}))(?![\d.]*\d)[.:)]?(?:\s+(?P<rest>.*))?$",
    re.S,
)
_PART_HEADING = re.compile(r"^(?:part\s+[A-Z]\b|[A-Z]\.\s+\S)", re.I)
# Some authors run several fields together in one paragraph ("A.1 Name: N/A A.2 Legal form: N/A").
# The colon requirement keeps cross-references such as "see F.14" from opening a field.
_INLINE_FIELD = re.compile(r"(?<=\s)(?=[A-Z]\.\d{1,2}\s+(?:(?![A-Z]\.\d)[^:]){1,120}:)")
# nav and footer hold site chrome when a white paper is published as a web page.
_SKIPPED_TAGS = {"head", "script", "style", "noscript", "ix:header", "nav", "footer"}

# Part letter -> section keys, from Tables 2, 3 and 4 of the Annex to Implementing
# Regulation (EU) 2024/2984 (OJ text read on 2026-10-09). Fields S.1 to S.36 are the
# sustainability indicators of Delegated Regulation (EU) 2025/422.
# Table 2 has been run against real white papers. Tables 3 and 4 follow the OJ text only.
_PART_SECTIONS: dict[WhitepaperType, dict[str, tuple[str, ...]]] = {
    WhitepaperType.OTHER: {
        "A": ("offeror",),
        "B": ("issuer",),
        "C": ("trading_platform_operator",),
        "D": ("project",),
        "E": ("offer_or_admission",),
        "F": ("crypto_asset",),
        "G": ("rights_and_obligations",),
        "H": ("technology",),
        "I": ("risks",),
        "J": ("environmental_impact",),
        "S": ("environmental_impact",),
    },
    WhitepaperType.ART: {
        "A": ("issuer",),
        "B": ("art",),
        "C": ("offer_or_admission",),
        # ANNEX_II.I reads the redemption items of Part D and Part G.
        "D": ("rights_and_obligations", "redemption"),
        "E": ("technology",),
        "F": ("risks",),
        "G": ("reserve_of_assets", "redemption"),
        "H": ("environmental_impact",),
        "S": ("environmental_impact",),
    },
    WhitepaperType.EMT: {
        "A": ("issuer",),
        "B": ("emt",),
        "C": ("offer_or_admission",),
        "D": ("rights_and_obligations",),
        "E": ("technology",),
        "F": ("risks",),
        "G": ("environmental_impact",),
        "S": ("environmental_impact",),
    },
}

# Leading fields -> section key. Table 2 numbers them 00 to 10; Tables 3 and 4 print
# I.00 to I.07 and I.00 to I.08, which _field_id reduces to the two digits.
_SUMMARY_SECTIONS: dict[WhitepaperType, dict[str, tuple[str, ...]]] = {
    WhitepaperType.OTHER: {
        "01": ("notification_date",),
        "03": ("management_statement",),
        "04": ("risk_warning",),
        "05": ("risk_warning",),
        "06": ("risk_warning",),
        "07": ("summary",),
        "08": ("summary",),
        "09": ("summary",),
        "10": ("summary",),
    },
    WhitepaperType.ART: {
        "01": ("notification_date",),
        "02": ("risk_warning",),
        "03": ("management_statement",),
        "04": ("summary",),
        "05": ("summary",),
        "06": ("summary", "redemption"),
        "07": ("summary",),
    },
    WhitepaperType.EMT: {
        "01": ("notification_date",),
        "03": ("management_statement",),
        "04": ("risk_warning",),
        "05": ("summary",),
        "06": ("summary",),
        "07": ("summary",),
        "08": ("summary",),
    },
}

# The language field sits at F.12, B.14 or B.11 depending on the table, and authors
# renumber, so it is found by its label ("Language or languages of the ... white paper").
_LANGUAGE_LABEL = re.compile(r"\blanguages?\b", re.I)


@dataclass(frozen=True)
class NumberedField:
    field_id: str
    label: str
    content: str

    @property
    def part(self) -> str:
        return self.field_id.split(".")[0]

    @property
    def placeholder(self) -> bool:
        """The content is a placeholder such as "TBD", "TBC", "[●]" or "to be confirmed"."""
        return is_placeholder(self.content)

    @property
    def answered(self) -> bool:
        return not (is_not_applicable(self.content) or self.placeholder)


def _tag(element: etree._Element) -> str:
    return element.tag.lower() if isinstance(element.tag, str) else ""


def _table_field(row: etree._Element) -> NumberedField | None:
    cells = [element_text(cell) for cell in row.xpath("./td | ./th")]
    if len(cells) < 2:
        return None
    match = _FIELD_ID.match(cells[0])
    if not match or match.group("rest"):
        return None
    label = cells[1] if len(cells) > 2 else ""
    return NumberedField(_field_id(match), label, cells[-1])


def _field_id(match: re.Match[str]) -> str:
    if match.group("summary"):
        return match.group("summary")
    number = match.group("number")
    # "I.01" is a leading field of Table 3 or 4; "I.1" is a risk field of Table 2.
    if match.group("part") == "I" and len(number) == 2 and number.startswith("0"):
        return number
    return f"{match.group('part')}.{int(number)}"


def _text_nodes(
    element: etree._Element, table_rows: dict[etree._Element, NumberedField]
) -> Iterator[str | NumberedField]:
    """Yield text fragments in document order, with each table field row as one item.

    Fragments break where text_fragments breaks them, so a word that a PDF conversion split with an
    empty spacer span comes out whole.
    """
    for node in text_fragments([element], lambda child: child in table_rows or _tag(child) in _SKIPPED_TAGS):
        if isinstance(node, str):
            yield from _INLINE_FIELD.split(node)
        elif node in table_rows:
            yield table_rows[node]


def extract_numbered_fields(path: Path) -> list[NumberedField]:
    """Read the numbered fields of a white paper, merging repeated field numbers."""
    tree = etree.parse(str(path), etree.HTMLParser(encoding="utf-8"))
    root = tree.getroot()
    if root is None:
        return []
    table_rows = {row: field for row in root.iter("tr") if (field := _table_field(row))}

    labels: dict[str, str] = {}
    contents: dict[str, list[str]] = {}
    current: str | None = None
    for node in _text_nodes(root, table_rows):
        if isinstance(node, NumberedField):
            labels.setdefault(node.field_id, node.label)
            contents.setdefault(node.field_id, []).append(node.content)
            current = None
            continue
        node = node.strip()
        match = _FIELD_ID.match(node)
        if match:
            current = _field_id(match)
            # "A.1 Name: Example AG" carries its answer after the colon; otherwise the node is a label.
            label, _, inline = (match.group("rest") or "").partition(":")
            if label.strip():
                labels.setdefault(current, label.strip())
            contents.setdefault(current, [])
            if inline.strip():
                contents[current].append(inline.strip())
        elif current and not (_PART_HEADING.match(node) and len(node.split()) < 20):
            contents[current].append(node)

    return [
        NumberedField(field_id, labels.get(field_id, ""), " ".join(parts))
        for field_id, parts in contents.items()
    ]


def is_numbered_layout(fields: list[NumberedField]) -> bool:
    return (
        len({field.part for field in fields if "." in field.field_id and field.content.strip()}) >= MIN_PARTS
    )


def sections_from_numbered_fields(
    fields: list[NumberedField], whitepaper_type: WhitepaperType
) -> tuple[dict[str, str], tuple[str, ...]]:
    """Map numbered fields to section texts and extraction notes.

    An answered field contributes "label: answer". A field answered "N/A" contributes
    "N/A" and a placeholder field ("TBD", "[●]") its placeholder, both without the label,
    so a part of unanswered fields cannot satisfy a rule through the wording of the
    template alone. In a part with no answered field, the "N/A" fields contribute nothing
    when another field holds a placeholder, so a part of placeholders and "N/A" reads as
    placeholders only and is reported missing.
    """
    parts = _PART_SECTIONS[whitepaper_type]
    summary = _SUMMARY_SECTIONS[whitepaper_type]
    lettered = [field for field in fields if field.part in parts and field.content.strip()]
    answered_parts = {field.part for field in lettered if field.answered}
    placeholder_parts = {field.part for field in lettered if field.placeholder} - answered_parts

    sections: dict[str, list[str]] = {}
    for field in fields:
        keys = parts.get(field.part) or summary.get(field.field_id, ())
        if not keys or not field.content.strip():
            continue
        # A placeholder language field still names the language field, so its check reports the placeholder.
        if (
            field.part in parts
            and (field.answered or field.placeholder)
            and _LANGUAGE_LABEL.search(field.label)
        ):
            keys = (*keys, "language")
        if field.placeholder:
            line = field.content
        elif not field.answered:
            if field.part in placeholder_parts:
                continue
            line = "N/A"
        elif field.label:
            line = f"{field.label}: {field.content}"
        else:
            line = field.content
        for key in keys:
            sections.setdefault(key, []).append(line)

    notes = []
    if not any(field.field_id in summary and field.content.strip() for field in fields):
        notes.append(
            "No leading numbered fields were found. The summary, statements, warning and notification date "
            "may sit under other headings; those checks report Missing because of the layout."
        )
    if "language" not in sections:
        notes.append(
            "No answered field labelled as the language of the white paper was found; "
            "the language check reports Missing because of the layout."
        )
    if whitepaper_type is WhitepaperType.EMT:
        notes.append(
            "The template has no numbered field for the safeguarding of funds; "
            "that check reports Missing because of the layout."
        )
    for part in sorted({field.part for field in lettered}):
        in_part = [field for field in lettered if field.part == part]
        if not any(field.answered or field.placeholder for field in in_part):
            notes.append(
                f"Part {part}: all {len(in_part)} numbered fields are marked not applicable. "
                "Confirm that the part does not apply."
            )
    return {key: "\n".join(lines) for key, lines in sections.items()}, tuple(notes)
