"""Section extraction for white papers laid out as the numbered fields of
Implementing Regulation (EU) 2024/2984 ("A.1 Name", "A.2 Legal form", ...).

Notified white papers follow that template rather than prose headings, so the
heading-based loader finds little in them. Field numbers vary between authors;
only the part letter is treated as reliable.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from functools import cache
from itertools import islice
from pathlib import Path

from lxml import etree

from micar_linter.placeholders import is_not_applicable, is_placeholder
from micar_linter.template_fields import FIELD_NAMES
from micar_linter.whitepaper import WhitepaperType
from micar_linter.xhtml_parser import element_text, parse_html, text_fragments

# A layout counts as numbered once fields from this many distinct parts carry content.
MIN_PARTS = 3

_FIELD_ID = re.compile(
    r"^(?:(?P<part>[A-Z]{1,2})\.(?P<number>\d{1,2})|(?P<summary>\d{2}))(?![\d.]*\d)[.:)]?(?:\s+(?P<rest>.*))?$",
    re.S,
)
# A part title of the template, whatever its length ("Part C- Information about the operator of the trading
# platform ..." runs to 40 words), also in German ("Teil B \u2013 Informationen über den Emittenten, ...").
# Table 3 prints Part AA without "Part" ("AA- information on other persons ...", "AA \u2013 Gemäß Artikel 19
# ..."), so that form needs the first word of the title: "AA-rated bonds" is body text.
_PART_TITLE = re.compile(
    r"^(?:(?:part|teil)\s+(?:[A-Z]|(?-i:AA))\s*[.:)\u2013\u2014-]\s*\S"
    r"|(?-i:AA)\s*[.:)\u2013\u2014-]\s*(?:information|gemäß))",
    re.I,
)
# A short line that opens a part without a dash ("Part B", "Part AA", "B. Issuer"); a longer line that starts
# with a letter and a full stop is body text.
_PART_HEADING = re.compile(r"^(?:(?:part|teil)\s+(?:[A-Z]|(?-i:AA))\b|[A-Z]\.\s+\S)", re.I)
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
        # Part AA names the persons other than the issuer who offer the token, seek its admission to trading
        # or draw up the white paper (Art. 19(1), second subparagraph, MiCAR), as the offeror section does.
        "AA": ("offeror",),
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
# I.00 to I.07 and I.00 to I.08, which _field_id reduces to the two digits. Field 02 of
# Table 2 and I.02 of Table 4 hold the Art. 6(3) and Art. 51(3) statement; I.02 of
# Table 3 is the Art. 19(4) warning, because Art. 19 MiCAR prescribes no such statement.
_SUMMARY_SECTIONS: dict[WhitepaperType, dict[str, tuple[str, ...]]] = {
    WhitepaperType.OTHER: {
        "01": ("notification_date",),
        "02": ("not_approved_statement",),
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
        "02": ("not_approved_statement",),
        "03": ("management_statement",),
        "04": ("risk_warning",),
        "05": ("summary",),
        "06": ("summary",),
        "07": ("summary",),
        "08": ("summary",),
    },
}

# The language field sits at F.12, B.14 or B.11 depending on the table, and authors
# renumber, so it is found by its label ("Language or languages of the ... white paper",
# in the German text "Sprache oder Sprachen des Kryptowerte-Whitepapers" or "... des Whitepaper").
_LANGUAGE_LABEL = re.compile(r"\blanguages?\b|\bsprachen?\b", re.I)
# Where the label shares a cell or paragraph with its answer, the field has no separate label and its
# content opens with the template label ("Language or languages of the white paper English", "Sprache
# oder Sprachen des Whitepaper Deutsch").
_LANGUAGE_CONTENT = re.compile(
    r"^\W*(?:languages?(?:\s+or\s+languages)?\s+of\s+the\s+(?:crypto-?\s*assets?\s+)?white\s+paper"
    r"|sprachen?(?:\s+oder\s+sprachen)?\s+des\s+(?:kryptowerte-?\s*)?whitepapers?)\b",
    re.I,
)
# Table 4 has no field for the safeguarding of funds received (Art. 54 MiCAR), so for an EMT the
# safeguarding section collects the answered lettered fields that describe it, also in the words of
# Art. 54: "separate accounts", "besichert", "gesonderten Konten".
_SAFEGUARDING_TEXT = re.compile(
    r"\bsafeguard\w*|\bsegregat\w*|\bseparate\s+(?:\w+\s+)?accounts?\b|\babsicherung\w*|\bbesichert\w*"
    r"|\bgesondert\w*\s+\w*kont(?:o|os|en)\b|\bsicherung\w*.*\bgelder\w*",
    re.I,
)


def _is_language_field(field: NumberedField) -> bool:
    if field.label:
        return bool(_LANGUAGE_LABEL.search(field.label))
    return bool(_LANGUAGE_CONTENT.match(field.content))


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


def _is_part_heading(text: str) -> bool:
    """A part title, or a line of under 20 words that opens a part: neither belongs to the field before it."""
    return bool(_PART_TITLE.match(text)) or (bool(_PART_HEADING.match(text)) and len(text.split()) < 20)


def extract_numbered_fields(source: Path | bytes) -> list[NumberedField]:
    """Read the numbered fields of a white paper, merging repeated field numbers.

    source is the file, or markup unpacked from a saved iXBRL viewer page.
    """
    tree = parse_html(source)
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
        elif current and not _is_part_heading(node):
            contents[current].append(node)

    return [
        NumberedField(field_id, labels.get(field_id, ""), " ".join(parts))
        for field_id, parts in contents.items()
    ]


# Before a label: spaces, a colon, a dash or a bullet. Between a label and its answer the same, but a dash
# or bullet only before more text: a lone dash answers "not applicable" and a lone bullet is a placeholder.
_LEAD = re.compile(r"^[\s:|\-\u2013\u2014\u2022\u00b7]+")
_JOINT = re.compile(r"^(?:[\s:|)\]]|[-\u2013\u2014\u2022\u00b7](?=\s))+")
# Text that goes on from a field name with "of", "'s" or the like makes a longer label than the
# template's ("Name of the token N/A"), so the field keeps its text.
_NAME_GOES_ON = re.compile(r"(?:of|for|and|or)\b|['\u2019]s\b")
# The CoreFiling rendering prints a field's name twice and can word one copy differently
# ("Financial condition over the past three years Financial condition for the past three years").
# Words before a name count as another wording of it when three in five of them are its words; words
# after a name, which no second name bounds, when three in four are.
_VARIANT_WORDS = 30
_VARIANT_SHARE = 0.6
_OTHER_WORDING_SHARE = 0.75
# An acronym in brackets after a name ("Distributed ledger technology (DLT)").
_ACRONYM = re.compile(r"\(([A-Z]{2,6})\)")
_LISTED_FIELDS = 10


@cache
def _name_pattern(name: str) -> re.Pattern[str]:
    """Match a template field name at the start of a text, in any case and spacing.

    A PDF conversion can split a word with an empty span ("accor dance"), so a word may hold gaps;
    between words any spacing or punctuation passes ("E-mail", "Email", "6(5)").
    """
    words = re.findall(r"[^\W_]+", name)
    body = r"[\W_]*".join(r"\s*".join(map(re.escape, word)) for word in words)
    tail = r"(?:\s*\))?" if name.endswith(")") else ""
    return re.compile(rf"{body}{tail}(?![^\W_])", re.I)


@cache
def _field_names() -> tuple[str, ...]:
    # The names of all three tables: a white paper can print a name in another table's wording.
    return tuple(dict.fromkeys(name for table in FIELD_NAMES.values() for name in table.values()))


def _leading_name(text: str) -> tuple[str, int] | None:
    """The longest template field name the text starts with, and where it ends in the text."""
    found = None
    for name in _field_names():
        if name[0].lower() != text[:1].lower():
            continue
        if (match := _name_pattern(name).match(text)) and (found is None or match.end() > found[1]):
            found = (name, match.end())
    return found


def _stems(text: str) -> Counter[str]:
    return Counter(stem for word in re.findall(r"[^\W_]+", text.lower()) if (stem := word.rstrip("s")))


def _name_after_variant(text: str) -> tuple[str, int] | None:
    """A template field name that follows another wording of itself, and where it ends in the text."""
    for word in islice(re.finditer(r"\S+", text), 1, _VARIANT_WORDS + 1):
        found = _leading_name(text[word.start() :])
        if found is None:
            continue
        before, name = _stems(text[: word.start()]), _stems(found[0])
        if (before & name).total() >= _VARIANT_SHARE * max(before.total(), name.total()):
            return found[0], word.start() + found[1]
    return None


def _other_wording_end(text: str, name: str) -> int | None:
    """Where another wording of the name ends, if the text starts with one: the closest of the
    text's first words, up to two more than the name has."""
    target = _stems(name)
    best, end = 0.0, None
    for word in islice(re.finditer(r"\S+", text), target.total() + 2):
        start = _stems(text[: word.end()])
        share = (start & target).total() / max(start.total(), target.total())
        if share > best:
            best, end = share, word.end()
    return end if best >= _OTHER_WORDING_SHARE else None


def _answer_after(rest: str, name: str) -> str:
    """The text after a field name without the further copies of the name, in its own words or
    others, or the acronym of the name in brackets."""
    answer = _JOINT.sub("", rest)
    while True:
        acronym = _ACRONYM.match(answer)
        initials = "".join(word[0] for word in re.findall(r"[^\W_]+", name)).upper()
        if acronym and initials.endswith(acronym.group(1)):
            end = acronym.end()
        elif match := _name_pattern(name).match(answer):
            end = match.end()
        elif not (end := _other_wording_end(answer, name)):
            return answer
        answer = _JOINT.sub("", answer[end:])


def _with_template_label(field: NumberedField) -> NumberedField:
    """Split the template's field name off the start of the field's text.

    A field without a label of its own takes the name its content starts with: "Legal form Legal
    form N/A" after a dash gives the label "Legal form" and the answer "N/A", also where a PDF
    conversion split a word, printed the name twice or worded one copy differently, or where an
    acronym in brackets follows the name. A label cut off inside a word takes the rest of the name
    from the content. A field keeps its text when no name fits, when a name covers only the start of
    its label, or when the text after the name goes on with "of" and the like.
    """
    label = _LEAD.sub("", field.label).rstrip(" .:")
    text = _LEAD.sub("", f"{label} {field.content}" if label else field.content)
    for find in (_leading_name, _name_after_variant):
        found = find(text)
        if found is None or found[1] < len(label):
            continue
        name, end = found
        answer = _answer_after(text[end:], name)
        if _NAME_GOES_ON.match(answer) and not (is_not_applicable(answer) or is_placeholder(answer)):
            continue
        new_label = name if not label or end > len(label) else label
        if (new_label, answer) == (field.label, field.content):
            return field
        return NumberedField(field.field_id, new_label, answer)
    return field


MERGED_LABELS_NOTE = (
    "Most numbered fields in this layout have no separate label, and their text does not start with a "
    "field name of the template, so a label can run into its answer: a field answered only \"N/A\" or "
    "\"TBD\" then reads as answered, and the template's label wording can count toward a check. "
    "Check each Pass against the white paper."
)


def _unlabelled_fields_note(field_ids: list[str]) -> str:
    listed = ", ".join(field_ids[:_LISTED_FIELDS])
    if len(field_ids) > _LISTED_FIELDS:
        listed += f" and {len(field_ids) - _LISTED_FIELDS} more"
    if len(field_ids) == 1:
        subject, fields = f"Field {listed} has no separate label, and its text", "the field"
    else:
        subject, fields = f"Fields {listed} have no separate label, and their text", "those fields"
    return (
        f"{subject} does not start with a field name of the template, so a label can run into the answer: "
        "such a field answered only \"N/A\" or \"TBD\" reads as answered. "
        f"Check {fields} against the white paper."
    )


def labels_run_into_answers(fields: list[NumberedField]) -> bool:
    """True if four in five lettered fields carry no label of their own.

    A rendering converted from PDF can split field number, label and answer into separate text runs,
    and some tables set the label in the answer cell. The label then reads as part of the answer,
    so "Legal form N/A" counts as answered, unless the template's field name is split off first.
    """
    lettered = [field for field in fields if "." in field.field_id and field.content.strip()]
    return bool(lettered) and 5 * sum(not field.label for field in lettered) >= 4 * len(lettered)


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
    placeholders only and is reported missing. A field whose text starts with the template's
    field name has that name split off as its label first, so the safeguards also hold
    where a layout runs labels into answers.
    """
    parts = _PART_SECTIONS[whitepaper_type]
    summary = _SUMMARY_SECTIONS[whitepaper_type]
    # The layout notes read the fields as found: a field holding only its name still counts as present.
    merged_layout = labels_run_into_answers(fields)
    has_leading_fields = any(field.field_id in summary and field.content.strip() for field in fields)
    fields = [_with_template_label(field) for field in fields]
    lettered = [field for field in fields if field.part in parts and field.content.strip()]
    answered_parts = {field.part for field in lettered if field.answered}
    placeholder_parts = {field.part for field in lettered if field.placeholder} - answered_parts

    sections: dict[str, list[str]] = {}
    safeguarding_fields: list[str] = []
    for field in fields:
        keys = parts.get(field.part) or summary.get(field.field_id, ())
        if not keys or not field.content.strip():
            continue
        # A placeholder language field still names the language field, so its check reports the placeholder.
        if field.part in parts and (field.answered or field.placeholder) and _is_language_field(field):
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
        if (
            whitepaper_type is WhitepaperType.EMT
            and field.part in parts
            and field.answered
            and _SAFEGUARDING_TEXT.search(field.content)
        ):
            sections.setdefault("safeguarding", []).append(line)
            safeguarding_fields.append(field.field_id)

    notes = []
    # Where labels run into answers, the fields whose label could not be split off stay at risk.
    unlabelled = [field.field_id for field in lettered if field.answered and not field.label]
    if labels_run_into_answers(fields):
        notes.append(MERGED_LABELS_NOTE)
    elif merged_layout and unlabelled:
        notes.append(_unlabelled_fields_note(unlabelled))
    if not has_leading_fields:
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
        if safeguarding_fields:
            notes.append(
                "The template has no numbered field for the safeguarding of funds; the safeguarding check "
                f"reads the fields that mention it: {', '.join(safeguarding_fields)}."
            )
        else:
            notes.append(
                "The template has no numbered field for the safeguarding of funds, and no answered field "
                "mentions safeguarding or segregated funds; the safeguarding check reports Missing."
            )
    for part in sorted({field.part for field in lettered}):
        in_part = [field for field in lettered if field.part == part]
        if not any(field.answered or field.placeholder for field in in_part):
            notes.append(
                f"Part {part}: all {len(in_part)} numbered fields are marked not applicable. "
                "Confirm that the part does not apply."
            )
    return {key: "\n".join(lines) for key, lines in sections.items()}, tuple(notes)
