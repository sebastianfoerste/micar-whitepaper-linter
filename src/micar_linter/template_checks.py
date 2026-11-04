"""Field-level checks of the numbered templates: predefined texts, data types, code lists and the
sustainability indicators of Delegated Regulation (EU) 2025/422.

The checks read the answers of a numbered-field draft (metadata key numbered_fields, with each field's label
under numbered_field_labels) and return issues; linter.py turns them into findings. They read the text a
reader sees. An Inline XBRL document can show a tagged value in another form than the value it reports (a
transformation turns "2 March 2026" into 2026-03-02), so a format issue here asks a reviewer to confirm the
tagged value; the checks do not read the tags. No issue quotes text from the draft.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from collections.abc import Mapping
from datetime import date
from decimal import Decimal, InvalidOperation
from functools import cache

from micar_linter.lei import has_valid_check_digits
from micar_linter.placeholders import is_not_applicable, is_placeholder
from micar_linter.predefined_texts import (
    HEADINGS,
    PREDEFINED_TEXTS,
    UTILITY_FIELD,
    UTILITY_FLAG_FIELDS,
    UTILITY_STATEMENT,
)
from micar_linter.template_fields import FIELD_NAMES
from micar_linter.template_types import (
    AMOUNT,
    CODE_LIST_KINDS,
    CODES,
    CURRENCY,
    CURRENCY_OR_DTI,
    DATE,
    DECIMAL,
    DTI,
    DURATION,
    ENERGY_KWH,
    ENERGY_THRESHOLD_KWH,
    FIELD_TYPES,
    FLAG,
    INTEGER,
    ISO_4217,
    LEI,
    MANDATORY_INDICATORS,
    MEMBER_STATES,
    MEMBER_STATES_BY_CODE,
    MIC,
    PERCENTAGE,
    QUANTITY,
    SUPPLEMENTARY_INDICATORS,
    SUSTAINABILITY_FIELDS,
    FieldType,
)
from micar_linter.whitepaper import WhitepaperType

# --- Reading answers -------------------------------------------------------------------------------------

_UMLAUTS = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})
_INVISIBLE = re.compile(r"[\u00ad\u200b\u200c\u200d\u2060\ufeff]")


def _words(text: str) -> list[str]:
    """The words of a text in lower case, with umlauts written out and every other character a separator."""
    text = _INVISIBLE.sub("", unicodedata.normalize("NFKC", text)).casefold().translate(_UMLAUTS)
    return re.findall(r"[^\W_]+", text)


def _stems(text: str) -> Counter[str]:
    return Counter(word.rstrip("s") for word in _words(text))


def label_fits(label: str, names: tuple[str, ...]) -> bool:
    """True if a field has no label of its own, or its label is one of the names in other words: three in five
    of the longer one's words are shared."""
    if not label.strip():
        return True
    have = _stems(label)
    for name in names:
        want = _stems(name)
        if (have & want).total() >= 0.6 * max(have.total(), want.total()):
            return True
    return False


@cache
def _name_start(name: str) -> re.Pattern[str]:
    words = re.findall(r"[^\W_]+", name)
    body = r"[\W_]*".join(map(re.escape, words))
    return re.compile(r"^\W*" + body + r"(?![^\W_])[\s:.\-\u2013\u2014|]*", re.I)


def strip_name(answer: str, names: tuple[str, ...]) -> str:
    """The answer without a field name it starts with, as where a label runs into the answer in German."""
    answer = answer.strip()
    for name in sorted(names, key=len, reverse=True):
        if match := _name_start(name).match(answer):
            return answer[match.end() :].strip()
    return answer


_QUOTES = "'\"\u2018\u2019\u201a\u201c\u201d\u201e\u00ab\u00bb"


def _bare(answer: str) -> str:
    """The answer without surrounding quotation marks and a final full stop."""
    return answer.strip().strip(_QUOTES).strip().rstrip(".").strip().strip(_QUOTES).strip()


def _blank(answer: str) -> bool:
    return not answer.strip() or is_placeholder(answer)


# --- Predefined texts ------------------------------------------------------------------------------------


def _squeezed(text: str) -> str:
    return "".join(_words(text))


@cache
def _sentence_pattern(sentence: str) -> re.Pattern[str]:
    """A pattern over squeezed text for one template sentence: "[...]" optional, "{a|b}" alternatives."""
    parts = []
    for piece in re.split(r"(\[[^\]]*\]|\{[^}]*\})", sentence):
        if piece.startswith("["):
            parts.append(f"(?:{re.escape(_squeezed(piece[1:-1]))})?")
        elif piece.startswith("{"):
            parts.append("(?:" + "|".join(re.escape(_squeezed(alt)) for alt in piece[1:-1].split("|")) + ")")
        else:
            parts.append(re.escape(_squeezed(piece)))
    return re.compile("".join(parts))


def _matched(answer: str, sentences: tuple[str, ...]) -> tuple[list[int], str]:
    """The indexes of the sentences found in the answer, and the squeezed answer without them."""
    text = _squeezed(answer)
    found = []
    for index, sentence in enumerate(sentences):
        pattern = _sentence_pattern(sentence)
        if pattern.search(text):
            found.append(index)
            text = pattern.sub("", text)
    for heading in HEADINGS:
        text = _sentence_pattern(heading).sub("", text)
    return found, text


# Extra characters a predefined text may carry besides its sentences and headings, such as a field label
# that the loader could not split off; more counts as added text.
_EXTRA_CHARACTERS = 20


def _start(sentence: str) -> str:
    """The first words of a template sentence, with the optional words left out and the first alternative."""
    text = re.sub(r"\[[^\]]*\]", "", sentence)
    text = re.sub(r"\{([^|}]*)[^}]*\}", r"\1", text)
    words = text.split()
    return " ".join(words[:10]) + (" ..." if len(words) > 10 else "")


def _field_name(number: str, regime: WhitepaperType, is_de: bool) -> str:
    """How a finding names a field: by number in German, with the template's English name in English."""
    if is_de:
        return number
    name = FIELD_NAMES[regime].get(number) or SUSTAINABILITY_FIELDS.get(number, ("",))[0]
    return f"{number} ({name})" if name else number


def _text_issue(
    number: str,
    answer: str,
    texts: tuple[tuple[str, ...], tuple[str, ...]],
    free: bool,
    regime: WhitepaperType,
    is_de: bool,
) -> str | None:
    """The issue of a field whose answer must hold a predefined text, or None."""
    name = _field_name(number, regime, is_de)
    results = [_matched(answer, sentences) for sentences in texts]
    # Compare with the wording that matches more sentences; on a tie, the draft's language.
    order = (1, 0) if is_de else (0, 1)
    best = max(order, key=lambda language: len(results[language][0]))
    found, rest = results[best]
    sentences = texts[best]
    missing = [index for index in range(len(sentences)) if index not in found]
    if missing:
        starts = "; ".join(f"\u201c{_start(sentences[index])}\u201d" for index in missing)
        count = f"{len(missing)}/{len(sentences)}"
        if is_de:
            return (
                f"Feld {name} gibt den vorgegebenen Text nicht wieder; nicht gefunden oder anders gefasst "
                f"({count} Sätzen): {starts}."
            )
        return (
            f"Field {name} does not hold the predefined text; not found or worded otherwise ({count} "
            f"sentences): {starts}."
        )
    if not free and len(rest) > _EXTRA_CHARACTERS:
        if is_de:
            return f"Feld {name} enthält neben dem vorgegebenen Text weiteren Text."
        return (
            f"Field {name} holds text besides the predefined text, which the template does not provide for."
        )
    return None


_TRUE = re.compile(r"^(?:true|richtig)\b", re.I)
_FALSE = re.compile(r"^(?:false|falsch)\b", re.I)


def _is_flag(answer: str, pattern: re.Pattern[str]) -> bool:
    return bool(pattern.match(_bare(answer)))


def _utility_issues(
    answers: Mapping[str, str], labels: Mapping[str, str], regime: WhitepaperType, is_de: bool
) -> tuple[list[str], bool]:
    """Field 05 of Table 2: false, or true with the utility-token statement. Returns the issues and whether
    the field holds an answer."""
    answer = str(answers.get(UTILITY_FIELD, "")).strip()
    name = _field_name(UTILITY_FIELD, regime, is_de)
    has_statement = _text_issue(UTILITY_FIELD, answer, UTILITY_STATEMENT, True, regime, is_de) is None
    flagged = [
        number
        for number in UTILITY_FLAG_FIELDS
        if _is_flag(str(answers.get(number, "")), _TRUE)
        and label_fits(labels.get(number, ""), (FIELD_NAMES[regime][number], "Utility-Token-Einstufung"))
    ]
    issues: list[str] = []
    if _blank(answer):
        issues.append(
            f"Feld {name} ist leer oder enthält nur einen Platzhalter; die Vorlage verlangt richtig "
            "oder falsch."
            if is_de
            else f"Field {name} is empty or holds only a placeholder; the template asks for true or false."
        )
        return issues, False
    is_false = _is_flag(answer, _FALSE) and not has_statement
    if has_statement:
        pass
    elif _is_flag(answer, _TRUE):
        issues.append(
            f"Feld {name} ist richtig (true), enthält aber nicht den vorgegebenen Text zum Utility-Token "
            "(Art. 6 Abs. 5 Buchst. d MiCAR)."
            if is_de
            else f"Field {name} is true but does not hold the predefined utility-token statement "
            "(Art. 6(5), point (d), MiCAR)."
        )
    elif not is_false:
        issues.append(
            f"Feld {name} enthält weder falsch (false) noch den vorgegebenen Text zum Utility-Token; die "
            "Vorlage kennt nur richtig mit diesem Text oder falsch."
            if is_de
            else f"Field {name} holds neither false nor the predefined utility-token statement; the template "
            "provides only for true with that statement, or false."
        )
    if is_false and flagged:
        fields = ", ".join(flagged)
        issues.append(
            f"Feld {fields} stuft den Token als Utility-Token ein, Feld {name} enthält aber nicht den Text "
            "zum Utility-Token."
            if is_de
            else f"Field {fields} classifies the token as a utility token, but field {name} does not hold "
            "the utility-token statement."
        )
    return issues, True


def predefined_text_issues(
    answers: Mapping[str, str], labels: Mapping[str, str], regime: WhitepaperType, is_de: bool
) -> tuple[list[str], bool]:
    """The issues of the predefined-text fields of the regime's table, and whether any of them holds an answer
    (not empty and not only a placeholder)."""
    issues: list[str] = []
    answered = False
    for number, (english, german, free) in PREDEFINED_TEXTS[regime].items():
        if number == "06" and regime is WhitepaperType.OTHER:
            # Field 05, the utility-token switch, sits between 04 and 06.
            utility, has_answer = _utility_issues(answers, labels, regime, is_de)
            issues.extend(utility)
            answered = answered or has_answer
        answer = str(answers.get(number, "")).strip()
        name = _field_name(number, regime, is_de)
        if _blank(answer):
            issues.append(
                f"Feld {name} ist leer, fehlt oder enthält nur einen Platzhalter."
                if is_de
                else f"Field {name} is empty, not in the draft or holds only a placeholder."
            )
            continue
        answered = True
        if is_not_applicable(answer):
            issues.append(
                f"Feld {name} ist als nicht anwendbar markiert; die Vorlage gibt den Text ohne Bedingung vor."
                if is_de
                else f"Field {name} is marked not applicable; the template prescribes its text without "
                "a condition."
            )
            continue
        if issue := _text_issue(number, answer, (english, german), free, regime, is_de):
            issues.append(issue)
    return issues, answered


# --- Data types and code lists ---------------------------------------------------------------------------

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def is_iso_date(text: str) -> bool:
    """True if the text is exactly a calendar date written YYYY-MM-DD."""
    text = _bare(text)
    if not _ISO_DATE.match(text):
        return False
    try:
        date.fromisoformat(text)
    except ValueError:
        return False
    return True


def iso_dates_in(text: str) -> list[date]:
    """The calendar dates written YYYY-MM-DD anywhere in the text."""
    found = []
    for match in re.finditer(r"(?<![\d-])\d{4}-\d{2}-\d{2}(?![\d-])", text):
        try:
            found.append(date.fromisoformat(match.group()))
        except ValueError:
            continue
    return found


# A number as a draft writes it: digits with commas, full stops or spaces between groups.
_NUMBER_TOKEN = re.compile(r"(?<![\w.,])[+-]?\d(?:[\d.,]|[ \u00a0\u202f'](?=\d{3}(?!\d)))*(?<![.,])")


def read_number(token: str) -> tuple[Decimal | None, str | None]:
    """The value of a number token and why its form departs from the template's decimal, if it does.

    The template's decimal has a full stop as decimal separator. Commas, spaces or apostrophes between groups
    of three digits before a full stop pass, as a rendering may set them. A comma before the decimals, or full
    stops between groups of three digits, is the German form; the value is read but the form is reported.
    """
    text = re.sub(r"[ \u00a0\u202f']", " ", token)
    sign = "-" if text.startswith("-") else ""
    body = text.lstrip("+-")
    if re.fullmatch(r"\d+(?:\.\d+)?", body):
        plain, problem = body, None
    elif re.fullmatch(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?", body) or re.fullmatch(
        r"\d{1,3}(?: \d{3})+(?:\.\d+)?", body
    ):
        plain, problem = body.replace(",", "").replace(" ", ""), None
    elif re.fullmatch(r"\d{1,3}(?:[. ]\d{3})+(?:,\d+)?", body) or re.fullmatch(r"\d+,\d+", body):
        plain = body.replace(".", "").replace(" ", "").replace(",", ".")
        problem = "comma"
    else:
        return None, "unreadable"
    try:
        return Decimal(sign + plain), problem
    except InvalidOperation:
        return None, "unreadable"


def _digits(value: Decimal) -> tuple[int, int]:
    """The digits in total and the fraction digits of a value as written, without leading zeros."""
    _, digits, exponent = value.as_tuple()
    fraction = -exponent if isinstance(exponent, int) and exponent < 0 else 0
    whole = len(digits) - fraction
    significant_whole = len("".join(map(str, digits[:whole])).lstrip("0")) if whole > 0 else 0
    return significant_whole + fraction, fraction


_CURRENCY_SYMBOLS = "€$£¥"
_UNIT_WORDS = 2


def _number_issue(answer: str, total: int, fraction: int, *, integer: bool, currency: bool) -> str | None:
    """Why the answer is not one number of the given size, or None. Up to two words besides the number (a
    unit such as "tokens") and, for an amount, a currency code or sign pass."""
    numbers = _NUMBER_TOKEN.findall(answer)
    if not numbers:
        return "no_number"
    if len(numbers) > 1:
        return "several"
    value, problem = read_number(numbers[0])
    if value is None:
        return "unreadable"
    if problem:
        return problem
    rest = _NUMBER_TOKEN.sub(" ", answer)
    words = [word for word in re.findall(r"[^\W\d_]+", rest) if not (currency and word.upper() in ISO_4217)]
    if len(words) > _UNIT_WORDS:
        return "text"
    digits, decimals = _digits(value)
    if integer and decimals:
        return "fraction"
    if digits > total or decimals > fraction:
        return "size"
    if currency is False and any(sign in rest for sign in _CURRENCY_SYMBOLS):
        return "text"
    return None


_NUMBER_REASONS = {
    "no_number": ("no number was found", "keine Zahl gefunden"),
    "several": ("it holds more than one number", "es enthält mehr als eine Zahl"),
    "unreadable": ("the number cannot be read", "die Zahl ist nicht lesbar"),
    "comma": (
        "the decimal separator is a comma or full stops separate the thousands; the template's decimal "
        "separator is a full stop",
        "Dezimaltrennzeichen ist ein Komma oder Punkte trennen die Tausender; die Vorlage verlangt einen "
        "Punkt als Dezimaltrennzeichen",
    ),
    "text": ("it holds text besides the number", "es enthält neben der Zahl weiteren Text"),
    "fraction": ("it has decimals", "es hat Nachkommastellen"),
    "size": ("it has more digits than the type allows", "es hat mehr Stellen, als der Typ erlaubt"),
}

_DURATION = re.compile(r"^\d{1,3}(?:\s*(?:calendar\s+)?days?|\s*(?:kalender)?tag(?:e|en)?)?$", re.I)
_FLAG = re.compile(r"^(?:true|false|richtig|falsch)(?:\s*[-\u2013\u2014:(].*)?$", re.I | re.S)
# A code of 18 to 22 letters and digits with at least one digit: an LEI, or a code meant as one.
_LEI_LIKE = re.compile(r"(?<![A-Za-z0-9])(?=[A-Za-z]*\d)[A-Za-z0-9]{18,22}(?![A-Za-z0-9])")
_LEI = re.compile(r"^[A-Z0-9]{18}[0-9]{2}$")
_DTI = re.compile(r"^[A-Za-z0-9]{9}$")
_MIC = re.compile(r"^[A-Z0-9]{4}$")
_ITEM_SEPARATOR = re.compile(r"\s*(?:[,;/&\n]|\band\b|\bund\b|\bor\b|\boder\b)\s*", re.I)
_LABEL_WORDS = re.compile(r"^(?:(?:ffg\s+)?dti|code|mic|iso\s*\d+)\b\s*[:\-]?\s*", re.I)
_ALL_STATES = re.compile(
    r"^(?:all\b.*\bmember\s+states?\b|all\s+(?:eu|eea)\b.*|alle\b.*\bmitgliedstaaten\b|(?:eu|ewr|eea)-?weit)",
    re.I,
)


def _items(answer: str) -> list[str]:
    return [item for item in (_bare(part) for part in _ITEM_SEPARATOR.split(answer)) if item]


@cache
def _state_names() -> frozenset[str]:
    names = {" ".join(_words(name)) for names in MEMBER_STATES_BY_CODE.values() for name in names}
    return frozenset(names | {" ".join(_words(name.removeprefix("The "))) for name in names})


def _state_ok(item: str) -> bool:
    if item.upper() in MEMBER_STATES_BY_CODE and item.isupper():
        return True
    words = _words(item)
    if words and words[0] == "the":
        words = words[1:]
    return " ".join(words) in _state_names()


def _code_head(answer: str) -> list[str]:
    """The codes an answer opens with, before a description: "ATTR - admission to trading" gives ["ATTR"]."""
    head = re.split(r"\s[-\u2013\u2014]\s|\s?[:(\u2013\u2014]", _bare(answer), maxsplit=1)[0]
    return _items(head)


def type_issue(field: FieldType, answer: str) -> str | None:
    """Why an answer is not of the field's type, as a reason code, or None. The answer is neither empty nor
    a placeholder nor marked not applicable."""
    kind = field.kind
    bare = _bare(answer)
    if kind == DATE:
        return None if is_iso_date(bare) else "date"
    if kind == FLAG:
        return None if _FLAG.match(bare) else "flag"
    if kind == DURATION:
        return None if _DURATION.match(bare) else "duration"
    if kind == LEI:
        codes = _LEI_LIKE.findall(answer)
        if not codes:
            return "lei_none"
        if any(not _LEI.match(code) for code in codes):
            return "lei_malformed"
        if any(not has_valid_check_digits(code) for code in codes):
            return "lei_check_digits"
        return None
    if kind == DTI:
        items = _items(_LABEL_WORDS.sub("", bare))
        return None if items and all(_DTI.match(item) for item in items) else "dti"
    if kind == CURRENCY:
        items = _items(bare)
        return None if items and all(item in ISO_4217 for item in items) else "currency"
    if kind == CURRENCY_OR_DTI:
        items = _items(bare)
        return (
            None
            if items and all(item in ISO_4217 or _DTI.match(item) for item in items)
            else "currency_or_dti"
        )
    if kind == MIC:
        items = _items(_LABEL_WORDS.sub("", bare))
        return None if items and all(_MIC.match(item) for item in items) else "mic"
    if kind in (AMOUNT, INTEGER, DECIMAL):
        return _number_issue(answer, 18, 3, integer=kind == INTEGER, currency=kind == AMOUNT)
    if kind == CODES:
        allowed = {code.upper() for code in field.codes}
        if {"TRUE", "FALSE"} <= allowed:
            allowed |= {"RICHTIG", "FALSCH"}
        items = _code_head(answer)
        return None if items and all(item.upper() in allowed for item in items) else "codes"
    if kind == MEMBER_STATES:
        if _ALL_STATES.match(bare):
            return None
        items = _items(bare)
        return None if items and all(_state_ok(item) for item in items) else "member_states"
    return None


def _expected(field: FieldType, is_de: bool) -> str:
    kind = field.kind
    english, german = {
        DATE: ("a date in the format YYYY-MM-DD", "ein Datum im Format JJJJ-MM-TT"),
        FLAG: ("true or false", "richtig oder falsch (true oder false)"),
        DURATION: ("a number of days of up to three digits", "eine Anzahl von Tagen mit bis zu drei Ziffern"),
        LEI: (
            "an LEI of 20 characters with valid check digits (ISO 17442)",
            "eine LEI aus 20 Zeichen mit gültigen Prüfziffern (ISO 17442)",
        ),
        DTI: (
            "a digital token identifier of nine letters or digits (ISO 24165)",
            "einen Digital Token Identifier aus neun Buchstaben oder Ziffern (ISO 24165)",
        ),
        CURRENCY: ("an ISO 4217 currency code such as EUR", "einen Währungscode nach ISO 4217 wie EUR"),
        CURRENCY_OR_DTI: (
            "an ISO 4217 currency code or a digital token identifier (ISO 24165)",
            "einen Währungscode nach ISO 4217 oder einen Digital Token Identifier (ISO 24165)",
        ),
        MIC: (
            "a market identifier code of four capital letters or digits (ISO 10383)",
            "einen Marktidentifikationscode aus vier Großbuchstaben oder Ziffern (ISO 10383)",
        ),
        AMOUNT: (
            "an amount of up to 18 digits with up to 3 decimals (DECIMAL-18/3) or a whole number",
            "einen Betrag mit bis zu 18 Stellen und bis zu 3 Nachkommastellen (DECIMAL-18/3) oder eine "
            "ganze Zahl",
        ),
        INTEGER: ("a whole number (INTEGER-n)", "eine ganze Zahl (INTEGER-n)"),
        DECIMAL: (
            "a number of up to 18 digits with up to 3 decimals (DECIMAL-18/3)",
            "eine Zahl mit bis zu 18 Stellen und bis zu 3 Nachkommastellen (DECIMAL-18/3)",
        ),
        MEMBER_STATES: (
            "EU Member States by name or two-letter code",
            "EU-Mitgliedstaaten mit Namen oder zweistelligem Code",
        ),
    }.get(kind, ("", ""))
    if kind == CODES:
        listed = ", ".join(code for code in field.codes if code not in ("ERROR",))
        english, german = (
            f"a code of the template's list ({listed})",
            f"einen Code der Liste der Vorlage ({listed})",
        )
    return german if is_de else english


_LEI_REASONS = {
    "lei_none": ("no LEI-shaped code was found", "kein Code in LEI-Form gefunden"),
    "lei_malformed": (
        "a code is not 18 capital letters or digits followed by two check digits",
        "ein Code besteht nicht aus 18 Großbuchstaben oder Ziffern und zwei Prüfziffern",
    ),
    "lei_check_digits": (
        "a code fails the ISO/IEC 7064 MOD 97-10 check digits",
        "ein Code hat ungültige Prüfziffern (ISO/IEC 7064 MOD 97-10)",
    ),
}


def field_type_issues(
    answers: Mapping[str, str],
    labels: Mapping[str, str],
    regime: WhitepaperType,
    is_de: bool,
    *,
    code_lists: bool,
) -> tuple[list[str], int]:
    """The issues of the typed fields of the regime's table, either the code lists or the other data types,
    and how many such fields the draft carries under their number and template name.

    A field whose label is not the template's name for its number is skipped: the draft numbers its fields
    otherwise. A field that is empty, holds only a placeholder or is marked not applicable is not checked;
    the other checks report a missing answer.
    """
    names = FIELD_NAMES[regime]
    issues: list[str] = []
    present = 0
    for number, field in FIELD_TYPES[regime].items():
        if (field.kind in CODE_LIST_KINDS) is not code_lists or number not in answers:
            continue
        own_names = (names.get(number, ""), field.name_de)
        if not label_fits(labels.get(number, ""), own_names):
            continue
        present += 1
        for line in str(answers[number]).split("\n"):
            answer = strip_name(line, own_names)
            if _blank(answer) or is_not_applicable(answer):
                continue
            reason = type_issue(field, answer)
            if reason is None:
                continue
            name = _field_name(number, regime, is_de)
            expected = _expected(field, is_de)
            detail = _NUMBER_REASONS.get(reason) or _LEI_REASONS.get(reason)
            suffix = f": {detail[1] if is_de else detail[0]}" if detail else ""
            issues.append(
                f"Feld {name} entspricht nicht dem Typ der Vorlage, die {expected} verlangt{suffix}."
                if is_de
                else f"Field {name} does not hold {expected}{suffix}."
            )
            break
    return issues, present


# --- Sustainability indicators (Delegated Regulation (EU) 2025/422) ----------------------------------------

_KWH_UNITS = {
    "wh": Decimal("0.001"),
    "kwh": Decimal(1),
    "mwh": Decimal(1000),
    "gwh": Decimal(1000000),
    "twh": Decimal(1000000000),
}
_UNIT = re.compile(
    r"\b(?P<unit>[kmgt]?wh|kilowatt[\s-]*hours?|kilowattstunden?|megawatt[\s-]*hours?|megawattstunden?"
    r"|gigawatt[\s-]*hours?|gigawattstunden?)\b",
    re.I,
)
_PER_YEAR = re.compile(
    r"(?:\s*(?:/|per|pro|je)\s*(?:calendar\s+|kalender)?(?:year|yr|jahr)"
    r"|\s*p\.?\s?a\.?|\s*jährlich|\s*annually)",
    re.I,
)


def _unit_factor(unit: str) -> Decimal:
    unit = unit.lower()
    if unit.startswith(("kilo", "kwh")):
        return Decimal(1)
    if unit.startswith(("mega", "mwh")):
        return Decimal(1000)
    if unit.startswith(("giga", "gwh")):
        return Decimal(1000000)
    return _KWH_UNITS.get(unit, Decimal(1))


def energy_kwh(answer: str) -> tuple[Decimal | None, list[str]]:
    """The energy consumption of field S.8 in kWh, and the reason codes where its form departs from "Amount in
    kilowatt-hours (kWh) {DECIMAL-18/5}"."""
    numbers = _NUMBER_TOKEN.findall(answer)
    if not numbers:
        return None, ["no_number"]
    if len(numbers) > 1:
        return None, ["several"]
    value, problem = read_number(numbers[0])
    if value is None:
        return None, ["unreadable"]
    reasons = [problem] if problem else []
    units = _UNIT.findall(answer)
    factor = Decimal(1)
    if units:
        factor = _unit_factor(units[0])
        if units[0].lower() not in ("kwh",) and not units[0].lower().startswith("kilowatt"):
            reasons.append("unit")
    rest = _PER_YEAR.sub(" ", _UNIT.sub(" ", _NUMBER_TOKEN.sub(" ", answer)))
    if re.search(r"[^\W\d_]", rest):
        reasons.append("text")
    digits, decimals = _digits(value)
    if digits > 18 or decimals > 5:
        reasons.append("size")
    return value * factor, reasons


_ENERGY_REASONS = {
    **_NUMBER_REASONS,
    "unit": ("it is not given in kWh", "die Angabe ist nicht in kWh"),
    "text": (
        "it holds text besides the amount and its unit",
        "es enthält neben Menge und Einheit weiteren Text",
    ),
}


def _indicator_answer(answers: Mapping[str, str], number: str) -> str:
    english, german, _ = SUSTAINABILITY_FIELDS[number]
    return strip_name(str(answers.get(number, "")), (english, german))


def _indicator_name(number: str, is_de: bool) -> str:
    return number if is_de else f"{number} ({SUSTAINABILITY_FIELDS[number][0]})"


def _presence_issue(number: str, answer: str, is_de: bool, basis_en: str, basis_de: str) -> str | None:
    name = _indicator_name(number, is_de)
    if not answer.strip():
        return f"Feld {name} ist leer oder fehlt." if is_de else f"Field {name} is empty or not in the draft."
    if is_placeholder(answer):
        return (
            f"Feld {name} enthält nur einen Platzhalter wie TBD."
            if is_de
            else f"Field {name} holds only a placeholder such as TBD."
        )
    if is_not_applicable(answer):
        return (
            f"Feld {name} ist als nicht anwendbar markiert; {basis_de} verlangt die Angabe."
            if is_de
            else f"Field {name} is marked not applicable; {basis_en} asks for it."
        )
    return None


def _format_issue(number: str, answer: str, is_de: bool) -> str | None:
    """The format issue of an answered indicator S.6, S.7 or S.10 to S.14."""
    kind = SUSTAINABILITY_FIELDS[number][2]
    name = _indicator_name(number, is_de)
    if kind == DATE:
        if is_iso_date(answer):
            return None
        return (
            f"Feld {name} enthält kein Datum im Format JJJJ-MM-TT ({{DATEFORMAT}})."
            if is_de
            else f"Field {name} does not hold a date in the format YYYY-MM-DD ({{DATEFORMAT}})."
        )
    if kind == PERCENTAGE:
        reason = _number_issue(answer.replace("%", " "), 11, 10, integer=False, currency=False)
        expected = ("a percentage {DECIMAL-11/10}", "keinen Prozentsatz {DEZIMALWERT-11/10}")
    elif kind == QUANTITY:
        reason = _number_issue(answer, 18, 5, integer=False, currency=False)
        expected = ("an amount {DECIMAL-18/5}", "keine Menge {DEZIMALWERT-18/5}")
        if reason == "text" and len(re.findall(r"[^\W\d_]+", answer)) <= 5:
            # The unit may take several words: "kg CO2e per transaction".
            reason = None
    else:
        return None
    if reason is None:
        return None
    detail = _NUMBER_REASONS[reason]
    if is_de:
        return f"Feld {name} enthält {expected[1]}: {detail[1]}."
    return f"Field {name} does not hold {expected[0]}: {detail[0]}."


def sustainability_issues(answers: Mapping[str, str], is_de: bool) -> tuple[list[str], bool]:
    """The issues of the indicators S.1 to S.16, and whether any of S.1 to S.9 holds an answer.

    S.1 to S.9 are mandatory (Art. 4(1) and Table 2 of the Annex to Delegated Regulation (EU) 2025/422).
    S.10 to S.16 are required where S.8 exceeds 500 000 kWh (Art. 4(2) and Table 3); below that they are
    optional, and their form is checked wherever they are answered.
    """
    issues: list[str] = []
    answered = False
    basis_en, basis_de = "Art. 4(1) of Delegated Regulation (EU) 2025/422", "Art. 4 Abs. 1 VO (EU) 2025/422"
    for number in MANDATORY_INDICATORS:
        answer = _indicator_answer(answers, number)
        presence = _presence_issue(number, answer, is_de, basis_en, basis_de)
        if presence:
            issues.append(presence)
            if answer.strip() and not is_placeholder(answer):
                answered = True
            continue
        answered = True
        if issue := _format_issue(number, answer, is_de):
            issues.append(issue)
    start, end = (_indicator_answer(answers, number) for number in ("S.6", "S.7"))
    if (
        is_iso_date(start)
        and is_iso_date(end)
        and date.fromisoformat(_bare(start)) > date.fromisoformat(_bare(end))
    ):
        issues.append(
            "Der Beginn des Zeitraums (S.6) liegt nach seinem Ende (S.7)."
            if is_de
            else "The beginning of the period (S.6) is later than its end (S.7)."
        )

    energy = _indicator_answer(answers, "S.8")
    kwh: Decimal | None = None
    if not _presence_issue("S.8", energy, is_de, basis_en, basis_de):
        kwh, reasons = energy_kwh(energy)
        if reasons:
            name = _indicator_name("S.8", is_de)
            details = "; ".join(_ENERGY_REASONS[reason][1 if is_de else 0] for reason in reasons)
            issues.append(
                f"Feld {name} enthält keine Menge in Kilowattstunden (kWh) {{DEZIMALWERT-18/5}}: {details}."
                if is_de
                else f"Field {name} does not hold an amount in kilowatt-hours (kWh) {{DECIMAL-18/5}}: "
                f"{details}."
            )

    supplementary = {number: _indicator_answer(answers, number) for number in SUPPLEMENTARY_INDICATORS}
    basis_en, basis_de = "Art. 4(2) of Delegated Regulation (EU) 2025/422", "Art. 4 Abs. 2 VO (EU) 2025/422"
    if kwh is not None and kwh > ENERGY_THRESHOLD_KWH:
        for number, answer in supplementary.items():
            if presence := _presence_issue(number, answer, is_de, basis_en, basis_de):
                issues.append(presence)
    elif kwh is None and any(
        _presence_issue(number, a, is_de, "", "") for number, a in supplementary.items()
    ):
        issues.append(
            "Ob die Felder S.10 bis S.16 anzugeben sind (Energieverbrauch über 500 000 kWh, Art. 4 Abs. 2 "
            "VO (EU) 2025/422), lässt sich nicht bestimmen, weil Feld S.8 keine lesbare Menge enthält."
            if is_de
            else "Whether fields S.10 to S.16 are required (energy consumption above 500 000 kWh, Art. 4(2) "
            "of Delegated Regulation (EU) 2025/422) cannot be decided, because field S.8 holds no readable "
            "amount."
        )
    for number, answer in supplementary.items():
        answered_here = answer.strip() and not is_placeholder(answer) and not is_not_applicable(answer)
        if answered_here and (issue := _format_issue(number, answer, is_de)):
            issues.append(issue)
    return issues, answered


# Which kinds a regime's table types, for the rule pages.
def typed_fields(regime: WhitepaperType, code_lists: bool) -> dict[str, FieldType]:
    return {
        number: field
        for number, field in FIELD_TYPES[regime].items()
        if (field.kind in CODE_LIST_KINDS) is code_lists
    }


__all__ = [
    "CODES",
    "ENERGY_KWH",
    "energy_kwh",
    "field_type_issues",
    "is_iso_date",
    "iso_dates_in",
    "label_fits",
    "predefined_text_issues",
    "read_number",
    "strip_name",
    "sustainability_issues",
    "type_issue",
    "typed_fields",
]
