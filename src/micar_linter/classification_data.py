"""The data for classifying a white paper in the ESMA register: Delegated Regulation (EU) 2025/421.

Article 109(8) MiCAR has ESMA draft regulatory technical standards on the data necessary for the
classification of crypto-asset white papers in its register. Delegated Regulation (EU) 2025/421 (OJ L,
2025/421, 24.3.2025), which applies from 23 December 2025, lists those data in its Annex (items 1 to 29) and
adds two conditions: an LEI must be valid and issued under a Local Operating Unit of the GLEIF system and
included in the GLEIF database (Art. 2), and the white paper must carry the ISO 24165 digital token identifier
of type 3 of its group of crypto-assets and an identifier of each crypto-asset where the DTI is provided, or
else an identifier approved by ESMA at Union level (Art. 3). Art. 1(3) lets the data be given in the white
paper itself, in the format of Implementing Regulation (EU) 2024/2984; Annex I Part F point 2 (Annexes II and
III Part B point 2) MiCAR asks for them there, and the templates carry them as fields F.4 to F.19 of Table 2,
B.7 to B.20 of Table 3 and B.4 to B.17 of Table 4, with the issuer's identity in Parts A and B.

Checked against the OJ on 2026-11-04: the Articles and every item of the Annex against the English and German
Official Journal text of Delegated Regulation (EU) 2025/421, and every field number, name and condition
against the English and German Official Journal text of Implementing Regulation (EU) 2024/2984 (OJ L,
2024/2984, 3.12.2024), both as the Publications Office Cellar served them. No amendment or corrigendum was
searched for.

ITEMS maps each item of the Annex to the template fields of Tables 2, 3 and 4. Items 23, 24 and 26 (record
identifier, data file reference, version) are assigned by the competent authority that sends the data, and
items 18 and 19 (dates of authorisation and of its withdrawal, "where applicable") have no field: Table 3 A.18
and Table 4 A.25 describe the authorisation in free text. Item 21, the date and time of the latest
notification, is carried by field 01 of Table 2 (I.01 of Tables 3 and 4) as a date only, which
ITS.NOTIFICATION_DATE_FORMAT checks. Template fields without an item of the Annex: the characteristics (F.6,
B.9, B.6), the voluntary data flag (F.15, Table 2 only, Art. 4(8) MiCAR) and the LEI eligibility (F.17, B.18,
B.15).

classification_issues checks presence and the conditions of the Delegated Regulation only. The form of each
field (dates, LEI with check digits, DTI, MIC, true or false) is ITS.FIELD_FORMATS', and the codes (white
paper type, submission type, Member States) are ITS.CODE_LISTS'; COMMON.LANGUAGE looks for an official EU
language. Inclusion of an LEI in the GLEIF database (Art. 2(b)) cannot be checked offline and is not: no
registry is queried. No issue quotes text from the draft. Every module that the playground's JSON path imports
may import this one: it uses the standard library and modules that do.

The English and German texts differ in two items: item 17 reads "where applicable" in English and "sofern
verfügbar" in German, and item 20 has no condition in English and "gegebenenfalls" in German. The check
follows the English text and the template, which give the publication date without a condition.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from micar_linter.point_fields import ANSWER, EMPTY, NOT_APPLICABLE, PLACEHOLDER, field_state
from micar_linter.template_checks import field_codes, field_flag, field_holds
from micar_linter.template_fields import FIELD_NAMES
from micar_linter.template_types import LEI
from micar_linter.whitepaper import WhitepaperType

OTHER, ART, EMT = WhitepaperType.OTHER, WhitepaperType.ART, WhitepaperType.EMT


@dataclass(frozen=True)
class Item:
    """An item of the Annex: its number, English and German name, whether the Annex gives it "where
    available" (or "where applicable"), and how each table carries it (a text for the rule page; "" where it
    does not)."""

    number: int
    name: str
    name_de: str
    optional: bool
    carried: Mapping[WhitepaperType, str]


def _all(other: str, art: str, emt: str) -> dict[WhitepaperType, str]:
    return {OTHER: other, ART: art, EMT: emt}


_NONE = _all("", "", "")
ITEMS: tuple[Item, ...] = (
    Item(
        1,
        "Type of crypto-asset white paper",
        "Art des Kryptowerte-Whitepapers",
        False,
        _all("F.4", "B.7", "B.4"),
    ),
    Item(
        2,
        "Name of the issuer",
        "Name des Emittenten",
        False,
        _all("A.1, or B.2 where field B.1 says the issuer is not the offeror", "A.1", "A.1"),
    ),
    Item(
        3,
        "Legal form of the issuer",
        "Rechtsform des Emittenten",
        False,
        _all("A.2 (B.3), or the LEI in A.6 (B.7)", "A.3, or the LEI in A.7", "A.3, or the LEI in A.7"),
    ),
    Item(
        4,
        "Legal entity identifier of the issuer, where available",
        "Rechtsträgerkennung des Emittenten, sofern verfügbar",
        True,
        _all("A.6 (B.7)", "A.7", "A.7"),
    ),
    Item(
        5,
        "Other identifier of the issuer required pursuant to applicable national law, where available",
        "Sonstige nach geltendem nationalem Recht erforderliche Kennung des Emittenten, sofern verfügbar",
        True,
        _all("A.7 (B.8)", "A.8", "A.8"),
    ),
    Item(
        6,
        "Legal entity identifier of the entity that drew up the crypto-asset white paper, where available",
        "Rechtsträgerkennung des Unternehmens, das das Kryptowerte-Whitepaper erstellt hat, sofern verfügbar",
        True,
        _all("A.6, or C.6 for the operator of a trading platform", "A.7, or AA.3", "A.7"),
    ),
    Item(
        7,
        "Other identifier of the entity that drew up the crypto-asset white paper required pursuant to "
        "applicable "
        "national law, where available",
        "Sonstige nach geltendem nationalem Recht erforderliche Kennung des Unternehmens, das das "
        "Kryptowerte-Whitepaper erstellt hat, sofern verfügbar",
        True,
        _all("A.7, or C.7", "A.8, or AA.3.1", "A.8"),
    ),
    Item(
        8,
        "Identifier of operator of the trading platform",
        "Kennung des Betreibers der Handelsplattform",
        False,
        _all("E.34, where E.1 gives ATTR", "C.25, where C.1 gives ATTR", "C.4, where C.1 gives ATTR"),
    ),
    Item(
        9,
        "Commercial name or trading name of the issuer, where available",
        "Handelsname oder Firmenname des Emittenten, sofern verfügbar",
        True,
        _all("F.7", "A.2", "A.2"),
    ),
    Item(
        10,
        "Physical address of the issuer",
        "Anschrift des Emittenten",
        False,
        _all("A.3 (B.4), or the LEI in A.6 (B.7)", "A.4, or the LEI in A.7", "A.4, or the LEI in A.7"),
    ),
    Item(
        11,
        "Telephone number of the issuer, where available",
        "Telefonnummer des Emittenten, sofern verfügbar",
        True,
        _all("A.8 (the offeror's)", "", "A.9"),
    ),
    Item(
        12,
        "Email of the issuer, where available",
        "E-Mail-Adresse des Emittenten, sofern verfügbar",
        True,
        _all("A.9 (the offeror's)", "", "A.10"),
    ),
    Item(13, "Website of the issuer", "Website des Emittenten", False, _all("F.8", "B.10", "B.7")),
    Item(14, "Home Member State", "Herkunftsmitgliedstaat", False, _all("F.18", "B.19", "B.16")),
    Item(15, "Host Member States", "Aufnahmemitgliedstaaten", False, _all("F.19", "B.20", "B.17")),
    Item(
        16,
        "Starting date of offer to the public or admission to trading",
        "Startdatum des öffentlichen Angebots oder der Zulassung zum Handel",
        False,
        _all("F.9", "B.11", "B.8"),
    ),
    Item(
        17,
        "Any other services provided by the issuer",
        "Sonstige vom Emittenten erbrachte Dienstleistungen",
        True,
        _all("F.11", "B.13", "B.10"),
    ),
    Item(
        18,
        "The date of authorisation, where applicable",
        "Gegebenenfalls das Datum der Zulassung",
        True,
        _all(
            "",
            "no date field; A.18 describes the authorisation",
            "no date field; A.25 describes the authorisation",
        ),
    ),
    Item(
        19,
        "The date of withdrawal of authorisation, where applicable",
        "Gegebenenfalls das Datum des Entzugs der Zulassung",
        True,
        _NONE,
    ),
    Item(20, "Publication date", "Veröffentlichungsdatum", False, _all("F.10", "B.12", "B.9")),
    Item(
        21,
        "Date and time of notification",
        "Datum und Uhrzeit der Übermittlung",
        False,
        _all("01, as a date", "I.01, as a date", "I.01, as a date"),
    ),
    Item(
        22,
        "Language or languages of the crypto-asset white paper",
        "Sprache oder Sprachen des Kryptowerte-Whitepapers",
        False,
        _all("F.12", "B.14", "B.11"),
    ),
    Item(23, "Record identifier", "Datensatzbezeichner", False, _NONE),
    Item(24, "Data file reference", "Dateikurzname", False, _NONE),
    Item(25, "The type of submission", "Die Art der Übermittlung", False, _all("F.5", "B.8", "B.5")),
    Item(26, "Version", "Version", False, _NONE),
    Item(
        27,
        "Digital Token Identifier of the crypto-asset or of each crypto-asset, where available",
        "Digital Token Identifier des Kryptowerts oder der einzelnen Kryptowerte, sofern verfügbar",
        True,
        _all("F.13", "B.15", "B.12"),
    ),
    Item(
        28,
        "Functionally Fungible Group Digital Token Identifier, where available",
        "Functionally Fungible Group Digital Token Identifier, sofern verfügbar",
        True,
        _all("F.14", "B.16", "B.13"),
    ),
    Item(
        29, "Personal data flag", "Kennzeichnung personenbezogener Daten", False, _all("F.16", "B.17", "B.14")
    ),
)
ITEMS_BY_NUMBER = {item.number: item for item in ITEMS}
# Items the sending competent authority assigns; the white paper does not carry them.
AUTHORITY_ITEMS = (23, 24, 26)
# Template fields of the register block that carry no item of the Annex.
UNMAPPED_FIELDS: dict[WhitepaperType, tuple[str, ...]] = {
    OTHER: ("F.6", "F.15", "F.17"),
    ART: ("B.9", "B.18"),
    EMT: ("B.6", "B.15"),
}


@dataclass(frozen=True)
class Issuer:
    """The fields of the issuer's identity: name, legal form, registered address and LEI."""

    name: str
    legal_form: str
    address: str
    lei: str


@dataclass(frozen=True)
class Layout:
    """Where a table carries the items the check reads."""

    # Items given without "where available", each in one field: (item, field).
    fields: tuple[tuple[int, str], ...]
    issuer: Issuer
    # Table 2 only: the issuer's fields where it is not the offeror (B.1 true).
    other_issuer: Issuer | None
    offer_field: str  # E.1 or C.1: OTPC or ATTR
    mic_field: str  # item 8
    dti_field: str  # item 27
    ffg_field: str  # item 28
    lei_fields: tuple[str, ...]  # every LEI field of the table, for the note on Art. 2(b)


LAYOUTS: dict[WhitepaperType, Layout] = {
    OTHER: Layout(
        fields=(
            (1, "F.4"),
            (25, "F.5"),
            (13, "F.8"),
            (16, "F.9"),
            (20, "F.10"),
            (22, "F.12"),
            (29, "F.16"),
            (14, "F.18"),
            (15, "F.19"),
        ),
        issuer=Issuer("A.1", "A.2", "A.3", "A.6"),
        other_issuer=Issuer("B.2", "B.3", "B.4", "B.7"),
        offer_field="E.1",
        mic_field="E.34",
        dti_field="F.13",
        ffg_field="F.14",
        lei_fields=("A.6", "B.7", "C.6", "E.31"),
    ),
    ART: Layout(
        fields=(
            (1, "B.7"),
            (25, "B.8"),
            (13, "B.10"),
            (16, "B.11"),
            (20, "B.12"),
            (22, "B.14"),
            (29, "B.17"),
            (14, "B.19"),
            (15, "B.20"),
        ),
        issuer=Issuer("A.1", "A.3", "A.4", "A.7"),
        other_issuer=None,
        offer_field="C.1",
        mic_field="C.25",
        dti_field="B.15",
        ffg_field="B.16",
        lei_fields=("A.7", "AA.1", "AA.3", "C.22", "G.8"),
    ),
    EMT: Layout(
        fields=(
            (1, "B.4"),
            (25, "B.5"),
            (13, "B.7"),
            (16, "B.8"),
            (20, "B.9"),
            (22, "B.11"),
            (29, "B.14"),
            (14, "B.16"),
            (15, "B.17"),
        ),
        issuer=Issuer("A.1", "A.3", "A.4", "A.7"),
        other_issuer=None,
        offer_field="C.1",
        mic_field="C.4",
        dti_field="B.12",
        ffg_field="B.13",
        lei_fields=("A.7", "A.27"),
    ),
}
HOST_ITEM = 15
ACT_EN = "Delegated Regulation (EU) 2025/421"
ACT_DE = "VO (EU) 2025/421"


def _name(number: str, regime: WhitepaperType, is_de: bool) -> str:
    """How a finding names a field: by number in German, with the template's English name in English."""
    name = FIELD_NAMES[regime].get(number)
    return number if is_de or not name else f"{number} ({name})"


def _item(number: int, is_de: bool) -> str:
    """The item as a finding names it: in German with its name, since the field is named by number only."""
    if is_de:
        return f"Nr. {number} des Anhangs der {ACT_DE} ({ITEMS_BY_NUMBER[number].name_de})"
    return f"item {number} of the Annex to {ACT_EN}"


def _absence(field: str, state: str, item: int, regime: WhitepaperType, is_de: bool) -> str | None:
    """The issue of a field that carries an item given without "where available", or None if answered."""
    name = _name(field, regime, is_de)
    where = _item(item, is_de)
    if state == EMPTY:
        return (
            f"Feld {name} ist leer oder fehlt; es trägt {where}."
            if is_de
            else (f"Field {name} is empty or not in the draft; it carries {where}.")
        )
    if state == PLACEHOLDER:
        return (
            f"Feld {name} enthält nur einen Platzhalter wie TBD; es trägt {where}."
            if is_de
            else (f"Field {name} holds only a placeholder such as TBD; it carries {where}.")
        )
    if state == NOT_APPLICABLE:
        if item == HOST_ITEM:
            return (
                f"Feld {name} ist als nicht anwendbar markiert; {where} steht ohne „sofern verfügbar“. Wird "
                "der "
                "Kryptowert in keinem Aufnahmemitgliedstaat angeboten, bestätigt das die Prüfung."
                if is_de
                else f"Field {name} is marked not applicable; {where} is listed without “where available”. "
                "Where "
                "the crypto-asset is offered in no host Member State, a reviewer confirms that."
            )
        return (
            f"Feld {name} ist als nicht anwendbar markiert; {where} steht ohne „sofern verfügbar“."
            if is_de
            else f"Field {name} is marked not applicable; {where} is listed without “where available”."
        )
    return None


_DTI_CODE = re.compile(r"(?<![A-Za-z0-9])(?=[A-Za-z]*\d)[A-Za-z0-9]{9}(?![A-Za-z0-9])")


def _dti_codes(answer: str) -> set[str]:
    return {code.upper() for code in _DTI_CODE.findall(answer)}


def _identifier_issues(
    answers: Mapping[str, str], layout: Layout, regime: WhitepaperType, is_de: bool
) -> list[str]:
    """Art. 3: with a DTI, the group identifier of type 3 and an identifier of each crypto-asset; without one,
    an identifier approved by ESMA. A field holding an answer counts as giving a code;
    ITS.FIELD_FORMATS checks its form."""
    dti, ffg = (str(answers.get(field, "")) for field in (layout.dti_field, layout.ffg_field))
    has_dti, has_ffg = field_state(dti) == ANSWER, field_state(ffg) == ANSWER
    # The template's names of these fields run to a sentence; a finding uses short ones.
    dti_name = f"{layout.dti_field} (digital token identifier)"
    ffg_name = f"{layout.ffg_field} (functionally fungible group DTI)"
    if has_dti and not has_ffg:
        return [
            f"Feld {layout.dti_field} gibt einen Digital Token Identifier an, Feld {layout.ffg_field} aber "
            "keinen "
            f"für die funktional fungible Gruppe; Art. 3 Abs. 1 {ACT_DE} verlangt dann eine gültige Kennung "
            "des "
            "Typs 3 für die Gruppe von Kryptowerten, auf die sich das Whitepaper bezieht."
            if is_de
            else f"Field {dti_name} gives a digital token identifier, but field {ffg_name} gives none; Art. "
            "3(1) of "
            f"{ACT_EN} then asks for the white paper to be identified with a valid identifier of type 3 for "
            "its "
            "group of crypto-assets."
        ]
    if has_ffg and not has_dti:
        return [
            f"Feld {layout.ffg_field} gibt einen Digital Token Identifier der funktional fungiblen Gruppe "
            "an, Feld "
            f"{layout.dti_field} aber keinen für den Kryptowert selbst; Art. 3 Abs. 2 {ACT_DE} verlangt dann "
            "für jeden Kryptowert eine eigene gültige Kennung."
            if is_de
            else f"Field {ffg_name} gives the identifier of the functionally fungible group, but field "
            f"{dti_name} "
            f"gives none for the crypto-asset itself; Art. 3(2) of {ACT_EN} then asks for each crypto-asset "
            "to be "
            "identified individually with a valid identifier."
        ]
    if has_dti and has_ffg:
        if _dti_codes(dti) & _dti_codes(ffg):
            return [
                f"Die Felder {layout.dti_field} und {layout.ffg_field} geben denselben Code an; die Kennung "
                "des "
                f"Typs 3 für die Gruppe (Art. 3 Abs. 1 {ACT_DE}) und die Kennung jedes Kryptowerts (Art. 3 "
                "Abs. 2) "
                "sind verschiedene Digital Token Identifier."
                if is_de
                else f"Fields {dti_name} and {ffg_name} give the same code; the type 3 identifier of the "
                "group "
                f"(Art. 3(1) of {ACT_EN}) and the identifier of each crypto-asset (Art. 3(2)) are different "
                "digital token identifiers."
            ]
        return []
    return [
        f"Weder Feld {layout.dti_field} noch Feld {layout.ffg_field} gibt einen Digital Token Identifier "
        "nach ISO "
        f"24165 an. Ist er nicht verfügbar, verlangt Art. 3 Abs. 3 {ACT_DE}, die Kryptowerte anhand eines "
        "von der "
        "ESMA auf Unionsebene genehmigten Digital Token Identifier auszuweisen; die Vorlage hat dafür kein "
        "Feld, "
        "daher bestätigt die Prüfung, wie das Whitepaper dem nachkommt."
        if is_de
        else f"Neither field {dti_name} nor field {ffg_name} gives an ISO 24165 digital token identifier. "
        "Where it is "
        f"not available, Art. 3(3) of {ACT_EN} asks for the crypto-assets to be identified by a digital "
        "token "
        "identifier approved by ESMA at Union level; the template has no field for it, so a reviewer "
        "confirms how "
        "the white paper meets this."
    ]


_GLEIF_NOTE = (
    f"Art. 2 of {ACT_EN} asks for each LEI to be valid, issued under a Local Operating Unit of the Global "
    "LEI System "
    "and included in the GLEIF database. The linter works offline: it checks the LEI's form and check digits "
    "(ITS.FIELD_FORMATS) and queries no registry, so a reviewer confirms that the LEI is listed and current.",
    f"Art. 2 {ACT_DE} verlangt, dass jede LEI gültig ist, von einer lokalen operativen Stelle des globalen "
    "LEI-Systems "
    "ausgestellt wurde und in der GLEIF-Datenbank aufgelistet ist. Der Linter arbeitet offline: Er prüft "
    "Form und "
    "Prüfziffern der LEI (ITS.FIELD_FORMATS) und fragt kein Register ab; dass die LEI aufgelistet und "
    "aktuell ist, "
    "bestätigt die Prüfung.",
)


def classification_issues(
    answers: Mapping[str, str], regime: WhitepaperType, is_de: bool
) -> tuple[str, tuple[str, ...]]:
    """Check the register data of a numbered-field draft: (status, issues).

    Missing when every field that carries an item given without "where available" is empty or holds only a
    placeholder; Review when one of them is empty, a placeholder or marked not applicable, when admission to
    trading is sought without a market identifier code (item 8), or when the identifiers do not meet Art. 3;
    Pass otherwise. Where a field gives an LEI, a note says that its inclusion in the GLEIF database (Art.
    2(b)) is not checked.
    """
    layout = LAYOUTS[regime]
    problems: list[str] = []
    applying = 0
    blank = 0

    def require(field: str, item: int) -> None:
        nonlocal applying, blank
        state = field_state(str(answers.get(field, "")))
        applying += 1
        if state in (EMPTY, PLACEHOLDER):
            blank += 1
        if issue := _absence(field, state, item, regime, is_de):
            problems.append(issue)

    issuer = layout.issuer
    if layout.other_issuer is not None:
        differs = field_flag("B.1", str(answers.get("B.1", "")), regime)
        named = field_state(str(answers.get(layout.other_issuer.name, ""))) == ANSWER
        if differs or (differs is None and named):
            issuer = layout.other_issuer
    require(issuer.name, 2)
    if not field_holds(issuer.lei, LEI, str(answers.get(issuer.lei, "")), regime):
        # Without an LEI the template asks for the legal form and the registered address; an LEI carries both.
        require(issuer.legal_form, 3)
        require(issuer.address, 10)
    for item, field in layout.fields:
        require(field, item)

    if "ATTR" in field_codes(layout.offer_field, str(answers.get(layout.offer_field, "")), regime):
        state = field_state(str(answers.get(layout.mic_field, "")))
        if state != ANSWER:
            offer, mic = (_name(field, regime, is_de) for field in (layout.offer_field, layout.mic_field))
            problems.append(
                f"Feld {layout.offer_field} nennt die Zulassung zum Handel (ATTR), Feld {layout.mic_field} "
                "gibt "
                f"aber keinen Marktidentifikationscode an; {_item(8, True)} verlangt den Segment-MIC der "
                "Handelsplattform, sofern verfügbar, ansonsten den Operating MIC."
                if is_de
                else f"Field {offer} seeks admission to trading (ATTR), but field {mic} gives no market "
                "identifier "
                f"code; {_item(8, False)} asks for the segment MIC of the trading platform where available, "
                "otherwise its operating MIC."
            )

    problems.extend(_identifier_issues(answers, layout, regime, is_de))

    notes: list[str] = []
    if any(field_holds(field, LEI, str(answers.get(field, "")), regime) for field in layout.lei_fields):
        notes.append(_GLEIF_NOTE[1 if is_de else 0])
    status = "missing" if applying and blank == applying else "review" if problems else "pass"
    return status, (*problems, *notes)


__all__ = [
    "AUTHORITY_ITEMS",
    "ITEMS",
    "ITEMS_BY_NUMBER",
    "LAYOUTS",
    "UNMAPPED_FIELDS",
    "Item",
    "classification_issues",
]
