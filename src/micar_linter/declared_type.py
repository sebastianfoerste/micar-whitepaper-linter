"""The white paper type a draft declares in the type field of the template (ADR 0009).

Tables 2, 3 and 4 of the Annex to Implementing Regulation (EU) 2024/2984 each carry one coded field for the
type of the white paper, with one code: F.4 of Table 2 (OTHR), B.7 of Table 3 (ARTW) and B.4 of Table 4
(EMTW). Its number in each table is that of item 1 of classification_data.ITEMS, its English names those of
template_fields.FIELD_NAMES ("Type of crypto-asset white paper", "Type of white paper"), its German names and
its code those of template_types.FIELD_TYPES; this module holds no field number, name or code of its own.

A type field is a line of the draft's text that starts with one of those names, after nothing but a field
number ("F.4", "F.4:", "B.7 -") and the marks of a Markdown heading, quotation, list, table or emphasis, or
whose line before holds a field number alone. Its answer is the rest of the line after the name, or, where
nothing follows the name, the next line that holds text; after a field number, the answer ends before the
number of the next field of the same part ("OTHR F.5 The type of submission NEWT"). The field must end
there: the next field starts on that line, the next line starts with a field number, or the text ends. A
line whose answer is a page number, with or without dot leaders, or that the number of the next field
follows with no answer between, is an entry of a table of contents and no type field.

The draft declares a type where it holds a type field, every type field it holds answers exactly one code
(in capital letters, between quotation marks or with a full stop after it at most) and ends after it, all
those codes are the same, and each field number printed with one is the number of that code's table (F.4 for
OTHR, B.7 for ARTW, B.4 for EMTW). Anything else declares no type (DeclaredType.problems says why). Both the
whole text of the file and the text as a reader sees it must give the same reading, so hidden text never
declares a type; in a Markdown file, which the loader reads as written, a type field declares nothing where
the file holds HTML, an HTML comment or a fenced code block. In a numbered-field draft the field that
ITS.CODE_LISTS reads under the declared table must hold exactly the code too (confirm_numbered).

The text is read once, line by line, so the reading takes time linear in its length. Standard library and
the data modules named above only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from micar_linter.classification_data import ITEMS_BY_NUMBER
from micar_linter.template_fields import FIELD_NAMES
from micar_linter.template_types import FIELD_TYPES
from micar_linter.whitepaper import WhitepaperType

# Per regime: the number of the type field in its table and the table's one code for it.
TYPE_FIELDS: dict[WhitepaperType, tuple[str, str]] = {
    regime: (number, FIELD_TYPES[regime][number].codes[0])
    for regime, number in ITEMS_BY_NUMBER[1].carried.items()
}
REGIME_OF_CODE: dict[str, WhitepaperType] = {code: regime for regime, (_, code) in TYPE_FIELDS.items()}
NUMBER_OF_CODE: dict[str, str] = {code: number for number, code in TYPE_FIELDS.values()}
_TABLES = {WhitepaperType.OTHER: 2, WhitepaperType.ART: 3, WhitepaperType.EMT: 4}
# The English and German names of the type field in the three tables, longest first. Any of them counts in
# any table: published white papers print the name of Table 4 on a Table 2 field ("F.4 Type of white paper").
TYPE_FIELD_NAMES: tuple[str, ...] = tuple(
    sorted(
        {
            name
            for regime, (number, _) in TYPE_FIELDS.items()
            for name in (FIELD_NAMES[regime][number], FIELD_TYPES[regime][number].name_de)
        },
        key=lambda name: (-len(name), name),
    )
)

# Characters that show nothing (soft hyphen, zero-width space and joiners, word joiner, byte order mark), and
# the marks of a Markdown table, emphasis or code span, which stand between a number, a name and an answer.
_INVISIBLE = re.compile("[\u00ad\u200b\u200c\u200d\u2060\ufeff]")
_MARKUP = re.compile(r"[|*`]")
_SPACES = re.compile(r"\s+")
# What may stand at the start of a line before a field number or a name: the marks of a Markdown heading,
# quotation or bulleted list.
_PREFIX = r"[#>+\-\u2013\u2014\u2022\u00b7 ]*"
_NUMBER = r"(?P<part>[A-Z]{1,2})\.(?P<number>\d{1,2})(?![\d.]*\d)[.:)]?"
# Words of a name may be split by spaces or hyphens or run together ("crypto-asset", "crypto asset").
_NAME = "|".join(
    r"[\s\-\u2010\u2011]*".join(map(re.escape, re.findall(r"[^\W_]+", name))) for name in TYPE_FIELD_NAMES
)
_FIELD_LINE = re.compile(
    rf"{_PREFIX}(?:{_NUMBER}(?: ?[-\u2013\u2014:])? )?(?i:{_NAME})(?![^\W_])[\s:\-\u2013\u2014]*(?P<rest>.*)"
)
_NUMBER_LINE = re.compile(rf"{_PREFIX}{_NUMBER}")
# A line that starts another field: a field number first, alone or before a space.
_FIELD_START = re.compile(rf"{_PREFIX}[A-Z]{{1,2}}\.\d{{1,2}}(?![\d.]*\d)[.:)]?(?: |$)")
# A field number at the start of an answer or after a space: where the next field of the same part starts.
_NEXT_NUMBER = re.compile(r"(?<![^ ])(?P<part>[A-Z]{1,2})\.(?P<number>\d{1,2})(?![\d.]*\d)")
# The answer of an entry in a table of contents: a page number, with dot leaders or not.
_PAGE = re.compile(r"[\s.\u2026\u00b7_\-]*\d{1,4}")
_ANY_CODE = re.compile(rf"(?<![^\W_])(?:{'|'.join(map(re.escape, REGIME_OF_CODE))})(?![^\W_])", re.I)
_QUOTES = "'\"\u2018\u2019\u201a\u201c\u201d\u201e\u00ab\u00bb"
# Raw HTML, an HTML comment or a code fence in a Markdown file, where its text as written and as shown differ.
# An autolink ("<https://...>") is no HTML.
_MARKDOWN_HIDING = re.compile(r"<(?![A-Za-z][A-Za-z0-9+.\-]*:)[A-Za-z/!]|^[ \t]*(?:```|~~~)", re.M)

# Why a type field gives no type, in the order the notes name them.
CODES = "codes"  # more than one code, in one answer or across the type fields
NUMBER = "number"  # a code under the field number of another table
CASE = "case"  # the code is not written in capital letters
TEXT = "text"  # the answer is not exactly one code
OPEN = "open"  # the line after the code starts no other field, so the answer may go on
HIDDEN = "hidden"  # the whole text and the text as shown read differently
MARKDOWN = "markdown"  # a Markdown file that can hide text
NUMBERED = "numbered"  # the numbered field as ITS.CODE_LISTS reads it is not exactly the code


@dataclass(frozen=True)
class DeclaredType:
    """What a draft's type fields give: the code they declare, with the field number printed with it ("" where
    none is), or the reasons they declare none. A draft without a type field gives neither."""

    code: str = ""
    number: str = ""
    problems: tuple[str, ...] = field(default=())

    @property
    def type(self) -> WhitepaperType | None:
        """The declared regime, or None."""
        return REGIME_OF_CODE[self.code] if self.code and not self.problems else None

    @property
    def seen(self) -> bool:
        """Whether the draft holds a type field."""
        return bool(self.code or self.problems)


def _lines(text: str) -> list[str]:
    """The lines of the text that hold text, without invisible characters and Markdown table, emphasis and
    code marks, each run of whitespace as one space."""
    lines = (_MARKUP.sub(" ", _INVISIBLE.sub("", line)) for line in text.split("\n"))
    return [line for line in (_SPACES.sub(" ", line).strip() for line in lines) if line]


def _bare(answer: str) -> str:
    """The answer without quotation marks around it and a full stop at its end, as ITS.CODE_LISTS reads it."""
    return answer.strip().strip(_QUOTES).strip().removesuffix(".").strip().strip(_QUOTES).strip()


def _cut(answer: str, part: str, number: int) -> str:
    """The answer before the number of the next field of the same part, where it holds one."""
    for match in _NEXT_NUMBER.finditer(answer):
        if match["part"] == part and int(match["number"]) == number + 1:
            return answer[: match.start()].rstrip()
    return answer


def _field(lines: list[str], index: int) -> tuple[str, str, str] | None:
    """The type field that the line at index opens, as (code, number, problem), or None where the line opens
    none or is an entry of a table of contents (a page number, or the next field's number, as its answer)."""
    match = _FIELD_LINE.fullmatch(lines[index])
    if match is None:
        return None
    part, number = match["part"], match["number"]
    if part is None and index and (above := _NUMBER_LINE.fullmatch(lines[index - 1])):
        part, number = above["part"], above["number"]
    answer, at = match["rest"], index
    if not answer and index + 1 < len(lines):
        answer, at = lines[index + 1], index + 1
    # The field ends after the answer's line where the text ends or the next line starts another field.
    ended = at + 1 == len(lines) or bool(_FIELD_START.match(lines[at + 1]))
    if part is not None:
        cut = _cut(answer, part, int(number))
        if answer and not cut:
            # The next field follows the name with no answer between: an entry of a list of the fields, such
            # as a table of contents without page numbers.
            return None
        # Or the next field starts on the answer's own line.
        ended = ended or cut != answer
        answer = cut
    if _PAGE.fullmatch(answer):
        return None
    printed = f"{part}.{int(number)}" if part is not None else ""
    bare = _bare(answer)
    if bare in REGIME_OF_CODE:
        if printed and printed != NUMBER_OF_CODE[bare]:
            return bare, printed, NUMBER
        return bare, printed, "" if ended else OPEN
    if len({code.upper() for code in _ANY_CODE.findall(answer)}) > 1:
        return "", printed, CODES
    if bare.upper() in REGIME_OF_CODE:
        return "", printed, CASE
    return "", printed, TEXT


def _read(text: str) -> DeclaredType:
    lines = _lines(text)
    codes: list[tuple[str, str]] = []
    problems: list[str] = []
    for index in range(len(lines)):
        found = _field(lines, index)
        if found is None:
            continue
        code, number, problem = found
        if problem:
            problems.append(problem)
        else:
            codes.append((code, number))
    if not problems and len({code for code, _ in codes}) > 1:
        problems.append(CODES)
    if problems:
        return DeclaredType(problems=tuple(dict.fromkeys(problems)))
    if not codes:
        return DeclaredType()
    code = codes[0][0]
    return DeclaredType(code, next((number for _, number in codes if number), ""))


def read_declared_type(text: str, shown_text: str = "", *, markdown: bool = False) -> DeclaredType:
    """The type the draft's text declares.

    shown_text is the same text without what a reader cannot see, or "" where the two are the same (the
    loaders' document_text and shown_text): where the two readings differ, the draft declares no type.
    markdown marks the text of a Markdown file, which no loader reads as shown: where it holds HTML, an HTML
    comment or a fenced code block, a type field in it declares no type."""
    declared = _read(text)
    if not declared.seen:
        return declared
    if markdown and _MARKDOWN_HIDING.search(text):
        return DeclaredType(problems=(MARKDOWN,))
    if shown_text and _read(shown_text) != declared:
        return DeclaredType(problems=(HIDDEN,))
    return declared


def confirm_numbered(declared: DeclaredType, answer: str) -> DeclaredType:
    """The declared type of a numbered-field draft, given the answer of the type field of the declared table
    as the field-level checks read it (numbered_fields.field_answers, one line per occurrence of the field):
    none where a line of it is not exactly the code, so the declaration and ITS.CODE_LISTS read the same
    field."""
    lines = [line for line in answer.split("\n") if line.strip()]
    if declared.type is None or (lines and all(_bare(line) == declared.code for line in lines)):
        return declared
    return DeclaredType(problems=(NUMBERED,))


_FIELD = "the type field of the template of Implementing Regulation (EU) 2024/2984"
_CODE_LIST = ", ".join(REGIME_OF_CODE)
_PAIRS = ", ".join(f"{number} for {code}" for number, code in TYPE_FIELDS.values())
_REASONS = {
    CODES: f"the draft gives more than one of the codes {_CODE_LIST}",
    NUMBER: f"a code stands under the number of another field (the template gives {_PAIRS})",
    CASE: f"the code is not written in capital letters as the template writes it ({_CODE_LIST})",
    TEXT: f"the answer is not exactly one of the codes {_CODE_LIST}, with nothing else",
    OPEN: "the line after the code does not start another field (a field number), so the answer may go on",
    HIDDEN: "the whole text of the file and the text as a reader sees it do not give the same type field",
    MARKDOWN: (
        "the Markdown file holds HTML, an HTML comment or a fenced code block, which can hide text or set it "
        "apart, so its type field is not read"
    ),
    NUMBERED: "the numbered field, as the field-level checks read it, does not hold exactly the code",
}
_MEANING = {
    WhitepaperType.OTHER: (
        "a white paper for crypto-assets other than asset-referenced tokens and e-money tokens"
    ),
    WhitepaperType.ART: "a white paper for an asset-referenced token",
    WhitepaperType.EMT: "a white paper for an e-money token",
}


def problem_sentence(declared: DeclaredType) -> str:
    """Why a draft that holds a type field declares no type, as one sentence; "" where it declares one or
    holds no type field."""
    if not declared.problems:
        return ""
    reasons = "; ".join(_REASONS[problem] for problem in declared.problems)
    return f"The draft holds {_FIELD}, but it declares no type: {reasons}."


def declared_type_notes(
    declared: DeclaredType, stated: WhitepaperType | None, inferred: WhitepaperType | None = None
) -> tuple[str, ...]:
    """The extraction notes on the declared type, given the regime stated with --type (None: none) and the
    regime the wording of the draft reads as (None: not read).

    No note where the draft holds no type field, or where a stated regime is the declared one or the draft
    declares none."""
    if declared.problems:
        if stated is not None:
            return ()
        return (
            f"{problem_sentence(declared)} The regime was inferred from the wording of the draft instead.",
        )
    regime = declared.type
    if regime is None:
        return ()
    number = NUMBER_OF_CODE[declared.code]
    what = (
        f"The draft declares its type in {_FIELD} ({number} of Table {_TABLES[regime]}): {declared.code}, "
        f"{_MEANING[regime]}."
    )
    if stated is None:
        note = f"{what} No regime was stated, so the checks ran under the declared type ({regime.value})."
        if inferred is not None and inferred is not regime:
            note += (
                f" The wording of the draft reads as {_MEANING[inferred]} ({inferred.value}); check which "
                "regime applies."
            )
        return (note,)
    if stated is not regime:
        return (
            f"{what} The regime was stated as {stated.value}, and the checks ran under the stated regime. "
            "Check which regime applies.",
        )
    return ()
