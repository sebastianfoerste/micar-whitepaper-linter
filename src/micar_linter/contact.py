"""The contact details of Annex I and Annex III Part A point 6 MiCAR.

Point 6 asks for a contact telephone number, an e-mail address and "the period of days within which an
investor contacting [the offeror, the person seeking admission to trading or the issuer] via that telephone
number or email address will receive an answer". Fields A.8 to A.10 of Table 2 and A.9 to A.11 of Table 4 of
Implementing Regulation (EU) 2024/2984 carry the three items, and the response time is a {DURATION}, "a
duration of time expressed as number of days" (OJ text read on 2026-10-30). The checks recognise the shape of
each item. They cannot tell whose number or address it is, or whether it works.
"""

from __future__ import annotations

import re

from micar_linter.whitepaper import WhitepaperType

# The template fields that carry point 6: telephone number, e-mail address, response time in days.
CONTACT_FIELDS: dict[WhitepaperType, tuple[str, str, str]] = {
    WhitepaperType.OTHER: ("A.8", "A.9", "A.10"),
    WhitepaperType.EMT: ("A.9", "A.10", "A.11"),
}

_EMAIL = re.compile(r"(?<![\w.%+-])[\w.%+-]+@[\w-]+(?:\.[\w-]+)*\.[^\W\d_]{2,}\b")

# A number that starts with a country code ("+49 69 ...", "0049 69 ...") or an area code ("069 ...", "(069)
# ..."). The lookbehinds keep it from starting inside a word, a code or a run of digit groups such as an IBAN.
_NUMBER_CANDIDATE = re.compile(r"(?<![\w+.,/()-])(?<!\d )(?:\+|\(?0)[\d\s()./-]*\d")
# Any number of six digits or more directly after a label: "Tel.: (212) 555-0100", "Telefon 069 1234567".
_LABELLED_NUMBER = re.compile(
    r"\b(?:tel(?:ephone|efon)?|phone|telefonnummer|hotline|mobil(?:e)?)\b\.?"
    r"(?:\s*(?:number|nummer|no\.|nr\.))?(?:\s+zur\s+kontaktaufnahme)?[\s:.]*(?P<number>[+(]?\d[\d\s()./-]*\d)",
    re.I,
)
# Any run of digits and separators, read in the answer to a telephone field.
_DIGIT_RUN = re.compile(r"[+(]?\d[\d\s()./-]*\d")
_DATE_START = re.compile(r"^\(?(?:\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{4}-\d{1,2}-\d{1,2})(?!\d)")
_FAX = re.compile(r"fax\W*$", re.I)

_NUMBER_EN = (
    r"(?:\d{1,3}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen"
    r"|sixteen|seventeen|eighteen|nineteen|twenty|thirty)"
)
_NUMBER_DE = (
    r"(?:\d{1,3}|ein(?:e[mnrs]?)?|zwei|drei|vier|f(?:ü|ue)nf|sechs|sieben|acht|neun|zehn|elf|zw(?:ö|oe)lf"
    r"|dreizehn|vierzehn|f(?:ü|ue)nfzehn|sechzehn|siebzehn|achtzehn|neunzehn|zwanzig|drei(?:ß|ss)ig)"
)
# "5 days", "five (5) business days", "a 10-day period"; "5 Werktage", "innerhalb von fünf Arbeitstagen".
_DAYS = re.compile(
    rf"\b{_NUMBER_EN}(?:\s*\(\s*{_NUMBER_EN}\s*\))?[\s-]*(?:(?:business|working|calendar|bank(?:ing)?)[\s-]+)?"
    r"days?\b"
    rf"|\b{_NUMBER_DE}(?:\s*\(\s*{_NUMBER_DE}\s*\))?[\s-]*"
    r"(?:werk|arbeits|gesch(?:ä|ae)fts|bank(?:arbeits)?|kalender)?tag(?:e|en|es|s)?\b",
    re.I,
)
# The template's own label before its answer: "Response time (Days): 5", "Reaktionszeit (Tage) 5".
_DAYS_LABEL = re.compile(
    rf"\b(?:response\s+time|reaktionszeit)\s*\(\s*(?:days|tage)\s*\)\s*[:\-\u2013]?\s*(?:{_NUMBER_EN}|{_NUMBER_DE})\b",
    re.I,
)
# A number standing alone, without "one" and "ein", which also read as a pronoun and an article ("in einem
# angemessenen Zeitraum").
_BARE_NUMBER = re.compile(
    r"\b(?:\d{1,3}|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen"
    r"|sixteen|seventeen|eighteen|nineteen|twenty|thirty|zwei|drei|vier|f(?:ü|ue)nf|sechs|sieben|acht|neun"
    r"|zehn|elf|zw(?:ö|oe)lf|dreizehn|vierzehn|f(?:ü|ue)nfzehn|sechzehn|siebzehn|achtzehn|neunzehn|zwanzig"
    r"|drei(?:ß|ss)ig)\b",
    re.I,
)
_OTHER_UNIT = re.compile(
    r"\b(?:hours?|weeks?|months?|years?|stunden?|wochen?|monate?n?|monats|jahre?n?|jahres)\b", re.I
)


def has_email_address(text: str) -> bool:
    """True if the text holds an e-mail address: "contact@example.eu"."""
    return bool(_EMAIL.search(text))


def has_telephone_number(text: str, *, labelled: bool = False) -> bool:
    """True if the text holds a telephone number.

    A number counts with its country code ("+49 69 1234 5678", "0049 69 ..."), with its area code and its
    digits in groups ("069 1234 5678", "(069) 1234-5678"), or after a label such as "Tel." or "Phone" with at
    least six digits. labelled reads the whole text as the answer to a telephone field, so any number of six
    digits or more counts. A fax number and a date do not count.
    """
    if labelled:
        return any(
            sum(char.isdigit() for char in match.group()) >= 6 and not _fax_or_date(text, match)
            for match in _DIGIT_RUN.finditer(text)
        )
    for match in _LABELLED_NUMBER.finditer(text):
        number = match.group("number")
        if 6 <= sum(char.isdigit() for char in number) <= 15 and not _DATE_START.match(number):
            return True
    for match in _NUMBER_CANDIDATE.finditer(text):
        number = match.group()
        if _fax_or_date(text, match):
            continue
        digits = sum(char.isdigit() for char in number)
        if number.startswith("+"):
            if 7 <= digits <= 15:
                return True
        elif number.startswith("00"):
            if 9 <= digits <= 15:
                return True
        elif 7 <= digits <= 13 and re.search(r"\d[\s()/-]+\d|\)", number):
            return True
    return False


def _fax_or_date(text: str, match: re.Match[str]) -> bool:
    """The number follows "Fax" or "Telefax", or reads as a date: "02.03.2026", "2026-03-02"."""
    before = text[max(0, match.start() - 12) : match.start()]
    return bool(_FAX.search(before) or _DATE_START.match(match.group()))


def has_period_in_days(text: str, *, labelled: bool = False) -> bool:
    """True if the text gives a period in days: "5 business days", "fünf Werktage", "Response time (Days): 5".

    labelled reads the whole text as the answer to a response time field, which the template counts in
    days, so a number that names no other unit of time counts too: "5", "up to 10". A period in hours or
    weeks does not count.
    """
    if _DAYS.search(text) or _DAYS_LABEL.search(text):
        return True
    return labelled and bool(_BARE_NUMBER.search(text)) and not _OTHER_UNIT.search(text)
