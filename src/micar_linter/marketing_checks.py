"""Text helpers for the marketing communication rules of Art. 7 MiCAR (rules/marketing.py, ADR 0009).

linter.py turns these readings into findings. Each helper reads text only: it cannot see layout, placement or
prominence, and it does not know whose website, number or address a value is.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from micar_linter.lei import has_valid_check_digits

# How many opening words count as the opening of the communication for Art. 7(1)(a).
OPENING_WORDS = 40

# Art. 7(1)(a): a label that marks the text as marketing ("eindeutig als solche erkennbar"). English and
# German labels count in a draft of either language.
_MARKETING_LABEL = re.compile(
    r"\b(?:crypto-asset\s+marketing\s+communication|marketing\s+communication|advertisement|advertising"
    r"|sponsored(?:\s+content)?|paid\s+(?:promotion|partnership)|promotional\s+(?:material|content|communication)"
    r"|kryptowert-marketingmitteilung|marketingmitteilung|werbemitteilung|werbeanzeige|werbung|anzeige"
    r"|gesponsert|bezahlte\s+partnerschaft)\b",
    re.IGNORECASE,
)

# Art. 7(1)(d): a statement that a crypto-asset white paper has been published, in the sentence that names
# it. A full stop followed by more text, as in a web address, does not end the sentence.
_IN_SENTENCE = r"(?:[^.!?\n]|\.(?=\S))"
_PUBLISHED = re.compile(
    rf"\bwhite[ -]?papers?\b{_IN_SENTENCE}{{0,120}}?"
    r"\b(?:has\s+been|have\s+been|was|were|is|are)\s+(?:\w+\s+){0,2}?"
    r"(?:published|made\s+available|available)\b"
    rf"|\bpublished\b{_IN_SENTENCE}{{0,80}}?\bwhite[ -]?papers?\b"
    rf"|whitepapers?\b{_IN_SENTENCE}{{0,120}}?\b(?:wurde|wurden|ist|sind|worden)\b{_IN_SENTENCE}{{0,60}}?"
    r"\bveröffentlicht\b"
    rf"|\bveröffentlicht\w*\b{_IN_SENTENCE}{{0,80}}?whitepapers?\b",
    re.IGNORECASE,
)

# A web address: with a scheme, starting with www., or a bare host followed by a path. A host right after "@"
# is part of an e-mail address and does not count.
_WEB_ADDRESS = re.compile(
    r"(?<![@\w.-])(?:https?://(?P<host1>[\w.-]+\.[a-z]{2,24})\S*"
    r"|(?P<host2>www\.[\w-]+(?:\.[\w-]+)*\.[a-z]{2,24})\b\S*"
    r"|(?P<host3>[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,24})/\S*)",
    re.IGNORECASE,
)
_EMAIL = re.compile(r"(?<![\w.%+-])[\w.%+-]+@[\w-]+(?:\.[\w-]+)*\.[^\W\d_]{2,}\b")
_LEI = re.compile(r"(?<![A-Z0-9])[A-Z0-9]{18}[0-9]{2}(?![A-Z0-9])")
# A digital token identifier: nine capital letters and digits with at least one of each (ISO 24165). The
# check digit is not tested.
_DTI = re.compile(r"(?<![A-Za-z0-9])(?=[A-Z0-9]*\d)(?=[A-Z0-9]*[A-Z])[A-Z0-9]{9}(?![A-Za-z0-9])")
# An international telephone number: + or 00, then at least eight digits in groups.
_PHONE = re.compile(r"(?<![\w+])(?:\+|00)\d[\d\s()./-]{6,}\d")
_PERCENTAGE = re.compile(r"(?<![\d.,])(\d{1,3}(?:[.,]\d+)?)\s*%(?!\d)")

_CURRENCIES = {
    "eur": "EUR",
    "euro": "EUR",
    "euros": "EUR",
    "€": "EUR",
    "usd": "USD",
    "dollar": "USD",
    "dollars": "USD",
    "$": "USD",
    "gbp": "GBP",
    "£": "GBP",
    "chf": "CHF",
    "usdc": "USDC",
    "usdt": "USDT",
}
_MULTIPLIERS = {
    "thousand": Decimal(1_000),
    "k": Decimal(1_000),
    "tsd": Decimal(1_000),
    "million": Decimal(1_000_000),
    "millionen": Decimal(1_000_000),
    "mio": Decimal(1_000_000),
    "m": Decimal(1_000_000),
    "billion": Decimal(1_000_000_000),
    "bn": Decimal(1_000_000_000),
    "mrd": Decimal(1_000_000_000),
    "milliarden": Decimal(1_000_000_000),
}
_NUMBER = r"\d{1,3}(?:[.,' ]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?"
_MULTIPLIER = r"(?:thousand|tsd|millionen|million|mio|milliarden|mrd|billion|bn|k|m)\.?"
_CODE_OR_SYMBOL = r"EUR|USDC|USDT|USD|GBP|CHF|€|\$|£"
_AMOUNT_BEFORE = re.compile(
    rf"(?<![\w$€£])(?P<cur>{_CODE_OR_SYMBOL})\s?(?P<num>{_NUMBER})(?:\s?(?P<mult>{_MULTIPLIER})(?![\w]))?",
    re.IGNORECASE,
)
_AMOUNT_AFTER = re.compile(
    rf"(?<![\w.,])(?P<num>{_NUMBER})\s?(?:(?P<mult>{_MULTIPLIER})\s?)?"
    rf"(?P<cur>{_CODE_OR_SYMBOL}|euros?|dollars?)(?![\w])",
    re.IGNORECASE,
)


def has_marketing_label(title: str, text: str) -> bool:
    """True where the title or the opening words of the text label the communication as marketing."""
    opening = " ".join(text.split()[:OPENING_WORDS])
    return bool(_MARKETING_LABEL.search(title) or _MARKETING_LABEL.search(opening))


def states_white_paper_published(text: str) -> bool:
    """True where a sentence says that a crypto-asset white paper has been published, in English or German."""
    return bool(_PUBLISHED.search(" ".join(text.split())))


def web_hosts(text: str) -> list[str]:
    """The host of every web address in the text, in lower case and without a leading www."""
    hosts = []
    for match in _WEB_ADDRESS.finditer(text):
        host = (match["host1"] or match["host2"] or match["host3"]).lower().rstrip(".")
        hosts.append(host.removeprefix("www."))
    return _unique(hosts)


def email_addresses(text: str) -> list[str]:
    return _unique(match.group(0).lower() for match in _EMAIL.finditer(text))


def valid_leis(text: str) -> list[str]:
    """The LEI-shaped codes with valid check digits (ISO 17442, MOD 97-10)."""
    return _unique(code for code in _LEI.findall(text) if has_valid_check_digits(code))


def token_identifiers(text: str) -> list[str]:
    """Nine-character codes of capital letters and digits, such as a DTI, that are not part of an LEI."""
    return _unique(_DTI.findall(text))


def phone_numbers(text: str) -> list[str]:
    """International telephone numbers as + and digits only."""
    numbers = []
    for match in _PHONE.finditer(text):
        digits = re.sub(r"\D", "", match.group(0))
        if match.group(0).startswith("00"):
            digits = digits[2:]
        if len(digits) >= 8:
            numbers.append("+" + digits)
    return _unique(numbers)


def percentages(text: str) -> list[Decimal]:
    return _unique(Decimal(value.replace(",", ".")) for value in _PERCENTAGE.findall(text))


def amounts(text: str) -> list[tuple[str, Decimal]]:
    """Amounts with a currency code or symbol, as (currency, value); a multiplier such as million applies."""
    found = []
    for pattern in (_AMOUNT_BEFORE, _AMOUNT_AFTER):
        for match in pattern.finditer(text):
            value = _number(match["num"])
            if value is None:
                continue
            multiplier = (match["mult"] or "").lower().rstrip(".")
            value *= _MULTIPLIERS.get(multiplier, Decimal(1))
            found.append((_CURRENCIES[match["cur"].lower()], value.normalize()))
    return _unique(found)


def format_amount(currency: str, value: Decimal) -> str:
    return f"{currency} {value:f}"


def format_percentage(value: Decimal) -> str:
    return f"{value.normalize():f} %"


def _number(text: str) -> Decimal | None:
    """A number as written: a separator before exactly three digits groups thousands, the last other one is
    the decimal separator ("1,000,000", "1.000,50", "0.10", "2,5")."""
    cleaned = text.replace("'", "").replace(" ", "")
    separators = [index for index, char in enumerate(cleaned) if char in ".,"]
    if separators:
        last = separators[-1]
        grouped = len(cleaned) - last - 1 == 3 and all(
            cleaned[index] == cleaned[last] for index in separators
        )
        if grouped:
            cleaned = cleaned.replace(cleaned[last], "")
        else:
            integer = re.sub(r"[.,]", "", cleaned[:last])
            cleaned = f"{integer}.{cleaned[last + 1 :]}"
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _unique(items):
    seen: list = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen
