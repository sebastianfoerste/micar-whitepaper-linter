"""The Annex points of MiCAR that the numbered template fields carry, and the check of those fields.

ADR 0005 keys a point rule to one point of Annex I, II or III (ANNEX_I.A.P2 for Annex I Part A point 2) and
checks, in a white paper drawn up in the numbered-field layout of Implementing Regulation (EU) 2024/2984, the
fields of Table 2, 3 or 4 of its Annex that carry the point. POINTS below holds the mapping, rules/points.py
builds one Rule per point from it and linter.py runs point_issues for each. ANNEX_I.A.P6 and ANNEX_III.A.P6,
the contact details, keep their own check (contact.py) and are not listed here.

Checked against the OJ on 2026-11-04: every point text against the English and German Official Journal text of
Regulation (EU) 2023/1114 (OJ L 150, 9.6.2023), Annexes I to III, and every field number, field name and
condition against the English and German Official Journal text of Implementing Regulation (EU) 2024/2984 (OJ
L, 2024/2984, 3.12.2024), Tables 2 to 4 of its Annex, both as the Publications Office Cellar served them. No
amendment or corrigendum was searched for.

A point lists its fields. A field applies under the template's own conditions, read from the column "Content
to be reported":

- NO_LEI: "only applicable if an LEI is not provided in field ..." (Table 2 A.2 to A.4, A.7, A.11, B.3 to B.5,
  B.8, B.9, C.2 to C.4, C.8; Table 3 A.3 to A.5, A.9; Table 4 A.3 to A.5, A.12). An LEI counts as provided
  when the field holds an LEI-shaped code with valid check digits.
- NO_DTI: "only if a DTI is not provided in field ..." (Table 2 D.2, D.3, F.7, H.1 by F.13; Table 3 B.1, B.2,
  E.1 by B.15; Table 4 B.1, B.2 by B.12 and E.1 by B.13). Table 4 E.1 names field B.13, the functionally
  fungible group DTI, in English and German, while B.1 and B.2 name B.12, the DTI; the check follows the OJ.
- FLAG: only if a true/false field is true (field 09 by 05, E.7 by E.6, E.21 and E.22 by E.20, G.8 by G.6,
  G.13 by G.12, G.15 by G.14, G.17 by G.16, H.7 by H.6, H.9 by H.8 of Table 2, and the same fields of Tables 3
  and 4), or false (G.10 by G.9 of Table 2, D.9 by D.8 of Table 3: "where an admission to trading is not
  sought"). Field 05 is false when it reads false or not applicable, its form column's "'false' - Not
  applicable", and true when it reads true or holds the utility-token statement. C.5 of Table 3 may read NTAV
  (not applicable), which counts as not true.
- CODE: only if a code field gives a code (Table 2 E.26, "in the case of offers to the public", by OTPC in
  E.1; Table 3 A.18, "if not exempted from authorisation", by NOEX in A.17).
- ANSWERED: only if a field holds an answer other than "not applicable".

Some conditions come from the Annex point and not from the field's own text; they are marked annex=True and a
finding says "the Annex point" rather than "the template": Annex I Part B applies only "if different from the
offeror" (field B.1 of Table 2, for every Part B field and for I.2, the issuer's risks); Part C applies only
"in cases where [the operator] draws up the crypto-asset white paper", which the template has no field for, so
the other Part C fields apply once C.1 names the operator; Part D point 4 and Part G point 4 apply to utility
tokens (D.7 by D.6, G.7 by G.6); point 4 of Part E asks for the issue price "in an official currency or any
other crypto-assets" (E.9 once E.8 gives a price); Annex II Part A point 11 asks for the authorisation only of
an issuer not exempted under Article 17, and for credit institutions for the competent authority (A.19 by NOEX
and A.20 by EX17 in A.17 of Table 3), and Annex III Part A point 13 only of an issuer not exempted under
Article 48(4) and (5) (A.25 and A.26 by A.24 of Table 4, which the template sets for A.25 only); the
description of a connection with the entity running the DLT (Table 3 A.24, Table 4 A.20) applies once the
indication of such a connection (A.23, A.19) is true.

A field whose content reads "where applicable", "if any", "if relevant", "where different", "when available"
or "potential" takes "not applicable" (N/A, none, a dash) as an answer (optional=True); every other field that
applies goes to review when it is marked not applicable. Fields of an alternative pass when one of them holds
an answer: the LEI or the national identifier of point 5, and the financial condition over three years or
since registration (Table 2 A.16 and A.17, Table 3 A.14 and A.15, Table 4 A.22 and A.23); the template's own
wording of the flag between them ("Newly established": "whether ... has been established for the past three
years") reads both ways, so the check does not choose by it. In point 4 of Annex I Part E the issue price
(E.8) and the method by which it will be determined (E.11) are alternatives too.

Fields that carry no Annex point, or only part of one that another field carries, are left out: the summary
and statements (00 to 10 of Table 2 except 09, I.00 to I.08 of Tables 3 and 4), the other persons drawing up
the white paper or offering the token (Table 2 C.13 and C.14, Table 3 Part AA, Table 4 A.27 to A.29), the
identifiers of a CASP, a trading platform or a custodian, which the points ask for by name only (Table 2 E.31
and E.34, Table 3 C.22, C.25 and G.8, Table 4 C.4), and the sustainability fields (Table 2 J.1, Table 3 H.1,
Table 4 G.1). The register data of Table 2 Part F (Table 3 and Table 4 Part B), which Annex I Part F point 2
(Annexes II and III Part B point 2) asks for as "the data necessary for classification of the crypto-asset
white paper in the register", are listed with that point.

The checks see whether a field holds an answer, not whether the answer is correct or complete; formats and
code lists are checked by ITS.FIELD_FORMATS and ITS.CODE_LISTS. No issue quotes text from the draft. Every
module that the playground's JSON path imports may import this one: it uses the standard library and modules
that do.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from micar_linter.placeholders import is_not_applicable, is_placeholder
from micar_linter.template_checks import field_codes, field_flag, field_holds
from micar_linter.template_fields import FIELD_NAMES
from micar_linter.template_types import DTI, LEI, TABLE_NUMBERS
from micar_linter.whitepaper import WhitepaperType

NO_LEI = "no_lei"
NO_DTI = "no_dti"
FLAG = "flag"
CODE = "code"
ANSWERED = "answered"


@dataclass(frozen=True)
class Condition:
    """A field applies only while its condition holds: kind, the field it reads and, for FLAG and CODE, the
    value it asks for ("true", "false" or a code). annex marks a condition taken from the Annex point."""

    kind: str
    field: str
    value: str = ""
    annex: bool = False


@dataclass(frozen=True)
class PointField:
    number: str
    conditions: tuple[Condition, ...] = ()
    optional: bool = False


@dataclass(frozen=True)
class Alternative:
    """Fields of which one answer is enough."""

    fields: tuple[PointField, ...]


Item = PointField | Alternative


@dataclass(frozen=True)
class Point:
    annex: str  # "I", "II" or "III"
    part: str
    number: int
    label: str
    items: tuple[Item, ...]

    @property
    def rule_id(self) -> str:
        return f"ANNEX_{self.annex}.{self.part}.P{self.number}"

    @property
    def fields(self) -> tuple[PointField, ...]:
        found: list[PointField] = []
        for item in self.items:
            found.extend(item.fields if isinstance(item, Alternative) else (item,))
        return tuple(found)


def _f(number: str, *conditions: Condition, optional: bool = False) -> PointField:
    return PointField(number, conditions, optional)


def _alt(*fields: PointField) -> Alternative:
    return Alternative(fields)


def _lei(field: str) -> Condition:
    return Condition(NO_LEI, field)


def _dti(field: str) -> Condition:
    return Condition(NO_DTI, field)


def _true(field: str, *, annex: bool = False) -> Condition:
    return Condition(FLAG, field, "true", annex)


def _false(field: str, *, annex: bool = False) -> Condition:
    return Condition(FLAG, field, "false", annex)


def _code(field: str, code: str, *, annex: bool = False) -> Condition:
    return Condition(CODE, field, code, annex)


def _answered(field: str) -> Condition:
    return Condition(ANSWERED, field, annex=True)


def _points(annex: str, part: str, *entries: tuple[int, str, tuple[Item, ...]]) -> tuple[Point, ...]:
    return tuple(Point(annex, part, number, label, items) for number, label, items in entries)


# --- Annex I and Table 2 ------------------------------------------------------------------------------------

_A6 = _lei("A.6")
_B1 = _true("B.1", annex=True)
_B7 = _lei("B.7")
_C1 = _answered("C.1")
_C6 = _lei("C.6")
_F13 = _dti("F.13")

_ANNEX_I = (
    *_points(
        "I",
        "A",
        (1, "Name of the offeror or person seeking admission to trading", (_f("A.1"),)),
        (2, "Legal form of the offeror or person seeking admission to trading", (_f("A.2", _A6),)),
        (
            3,
            "Registered address and head office, where different, of the offeror or person seeking admission "
            "to trading",
            (_f("A.3", _A6), _f("A.4", _A6, optional=True)),
        ),
        (4, "Date of registration of the offeror or person seeking admission to trading", (_f("A.5"),)),
        (
            5,
            "Legal entity identifier or another identifier required by national law of the offeror or person "
            "seeking admission to trading",
            (_alt(_f("A.6"), _f("A.7", _A6)),),
        ),
        (7, "Name of the parent company, where applicable", (_f("A.11", _A6, optional=True),)),
        (
            8,
            "Identity, business addresses and functions of the members of the management body of the offeror "
            "or person seeking admission to trading",
            (_f("A.12"),),
        ),
        (
            9,
            "Business or professional activity of the offeror or person seeking admission to trading and, "
            "where applicable, of its parent company",
            (_f("A.13"), _f("A.14", optional=True)),
        ),
        (
            10,
            "Financial condition of the offeror or person seeking admission to trading over the past three "
            "years or since its registration",
            (_f("A.15"), _alt(_f("A.16"), _f("A.17"))),
        ),
    ),
    *_points(
        "I",
        "B",
        (1, "Name of the issuer, if different from the offeror", (_f("B.2", _B1),)),
        (2, "Legal form of the issuer", (_f("B.3", _B1, _B7),)),
        (
            3,
            "Registered address and head office, where different, of the issuer",
            (_f("B.4", _B1, _B7), _f("B.5", _B1, _B7, optional=True)),
        ),
        (4, "Date of registration of the issuer", (_f("B.6", _B1),)),
        (
            5,
            "Legal entity identifier or another identifier required by national law of the issuer",
            (_alt(_f("B.7", _B1), _f("B.8", _B1, _B7)),),
        ),
        (6, "Name of the issuer's parent company, where applicable", (_f("B.9", _B1, _B7, optional=True),)),
        (
            7,
            "Identity, business addresses and functions of the members of the issuer's management body",
            (_f("B.10", _B1),),
        ),
        (
            8,
            "Business or professional activity of the issuer and, where applicable, of its parent company",
            (_f("B.11", _B1), _f("B.12", _B1, optional=True)),
        ),
    ),
    *_points(
        "I",
        "C",
        (
            1,
            "Name of the operator of the trading platform, where it draws up the white paper",
            (_f("C.1", optional=True),),
        ),
        (2, "Legal form of the operator of the trading platform", (_f("C.2", _C1, _C6),)),
        (
            3,
            "Registered address and head office, where different, of the operator of the trading platform",
            (_f("C.3", _C1, _C6), _f("C.4", _C1, _C6, optional=True)),
        ),
        (4, "Date of registration of the operator of the trading platform", (_f("C.5", _C1),)),
        (
            5,
            "Legal entity identifier or another identifier required by national law of the operator of the "
            "trading platform",
            (_alt(_f("C.6", _C1), _f("C.7", _C1)),),
        ),
        (
            6,
            "Name of the operator's parent company, where applicable",
            (_f("C.8", _C1, _C6, optional=True),),
        ),
        (7, "Reason why the operator drew up the white paper", (_f("C.9", _C1),)),
        (
            8,
            "Identity, business addresses and functions of the members of the operator's management body",
            (_f("C.10", _C1),),
        ),
        (
            9,
            "Business or professional activity of the operator and, where applicable, of its parent company",
            (_f("C.11", _C1), _f("C.12", _C1, optional=True)),
        ),
    ),
    *_points(
        "I",
        "D",
        (
            1,
            "Name of the crypto-asset project and of the crypto-assets, if different, and abbreviation or "
            "ticker handler",
            (_f("D.1", optional=True), _f("D.2", _F13, optional=True), _f("D.3", _F13)),
        ),
        (2, "Brief description of the crypto-asset project", (_f("D.4"),)),
        (
            3,
            "Details of the natural or legal persons involved in the implementation of the project",
            (_f("D.5"),),
        ),
        (
            4,
            "Key features of the goods or services to be developed, where the project concerns utility "
            "tokens",
            (_f("D.6"), _f("D.7", _true("D.6", annex=True))),
        ),
        (
            5,
            "Past and future milestones of the project and, where applicable, resources already allocated",
            (_f("D.8"), _f("D.9", optional=True)),
        ),
        (
            6,
            "Planned use of any funds or other crypto-assets collected, where applicable",
            (_f("D.10", optional=True),),
        ),
    ),
    *_points(
        "I",
        "E",
        (
            1,
            "Whether the white paper concerns an offer to the public or an admission to trading",
            (_f("E.1"),),
        ),
        (2, "Reasons for the offer to the public or for seeking admission to trading", (_f("E.2"),)),
        (
            3,
            "Amount to be raised, minimum and maximum subscription goals, and whether and how "
            "oversubscriptions are accepted and allocated",
            (
                _f("E.3", optional=True),
                _f("E.4", optional=True),
                _f("E.5", optional=True),
                _f("E.6"),
                _f("E.7", _true("E.6")),
            ),
        ),
        (
            4,
            "Issue price, any subscription fee or the method by which the offer price will be determined",
            (_alt(_f("E.8"), _f("E.11")), _f("E.9", _answered("E.8")), _f("E.10", optional=True)),
        ),
        (
            5,
            "Total number of crypto-assets to be offered or admitted to trading, where applicable",
            (_f("E.12", optional=True),),
        ),
        (
            6,
            "Prospective holders targeted and any restriction on the type of holders",
            (_f("E.13"), _f("E.14", optional=True)),
        ),
        (
            7,
            "Notice of reimbursement, refund mechanism and expected timeline of refunds",
            (_f("E.15"), _f("E.16"), _f("E.17")),
        ),
        (
            8,
            "Phases of the offer and any discounted purchase price for early purchasers",
            (_f("E.18"), _f("E.19", optional=True)),
        ),
        (
            9,
            "Subscription period of a time-limited offer",
            (_f("E.20"), _f("E.21", _true("E.20")), _f("E.22", _true("E.20"))),
        ),
        (10, "Arrangements to safeguard funds or other crypto-assets under Article 10", (_f("E.23"),)),
        (
            11,
            "Methods of payment and methods of transferring the value to purchasers entitled to "
            "reimbursement",
            (_f("E.24"), _f("E.25")),
        ),
        (
            12,
            "Right of withdrawal under Article 13, in the case of offers to the public",
            (_f("E.26", _code("E.1", "OTPC")),),
        ),
        (
            13,
            "Manner and time schedule of transferring the purchased crypto-assets to the holders",
            (_f("E.27"), _f("E.28")),
        ),
        (14, "Technical requirements the purchaser must fulfil to hold the crypto-assets", (_f("E.29"),)),
        (
            15,
            "Crypto-asset service provider placing the crypto-assets and the form of placement, where "
            "applicable",
            (_f("E.30", optional=True), _f("E.32", optional=True)),
        ),
        (
            16,
            "Trading platform where admission is sought, how investors access it and the costs involved, "
            "where "
            "applicable",
            (_f("E.33", optional=True), _f("E.35", optional=True), _f("E.36", optional=True)),
        ),
        (17, "Expenses related to the offer to the public", (_f("E.37"),)),
        (
            18,
            "Potential conflicts of interest of the persons involved in the offer or admission",
            (_f("E.38", optional=True),),
        ),
        (19, "Law applicable to the offer to the public and the competent court", (_f("E.39"), _f("E.40"))),
    ),
    *_points(
        "I",
        "F",
        (1, "Type of crypto-asset offered or admitted to trading", (_f("F.1"),)),
        (
            2,
            "Characteristics, register data, functionality and when the functionalities are planned to apply",
            (
                _f("F.6"),
                _f("F.2"),
                _f("F.3"),
                _f("F.4"),
                _f("F.5"),
                _f("F.7", _F13),
                _f("F.8"),
                _f("F.9"),
                _f("F.10"),
                _f("F.11", optional=True),
                _f("F.12"),
                _f("F.13", optional=True),
                _f("F.14", optional=True),
                _f("F.15"),
                _f("F.16"),
                _f("F.17"),
                _f("F.18"),
                _f("F.19", optional=True),
            ),
        ),
    ),
    *_points(
        "I",
        "G",
        (
            1,
            "Rights and obligations of the purchaser and the procedure and conditions for exercising them",
            (_f("G.1", optional=True), _f("G.2")),
        ),
        (2, "Conditions under which the rights and obligations may be modified", (_f("G.3"),)),
        (
            3,
            "Future offers of crypto-assets by the issuer and the number of crypto-assets it retains, where "
            "applicable",
            (_f("G.4", optional=True), _f("G.5", optional=True)),
        ),
        (
            4,
            "Quality and quantity of the goods or services to which utility tokens give access",
            (_f("G.6"), _f("G.7", _true("G.6", annex=True)), _f("09", _true("05"))),
        ),
        (5, "How utility tokens can be redeemed for the goods or services", (_f("G.8", _true("G.6")),)),
        (
            6,
            "How and where the crypto-assets can be bought or sold after the offer, where admission to "
            "trading "
            "is not sought",
            (_f("G.9"), _f("G.10", _false("G.9"))),
        ),
        (7, "Restrictions on the transferability of the crypto-assets", (_f("G.11", optional=True),)),
        (
            8,
            "Functioning of protocols that increase or decrease the supply in response to demand",
            (_f("G.12"), _f("G.13", _true("G.12"))),
        ),
        (
            9,
            "Protection schemes protecting the value of the crypto-assets and compensation schemes, where "
            "applicable",
            (_f("G.14"), _f("G.15", _true("G.14")), _f("G.16"), _f("G.17", _true("G.16"))),
        ),
        (10, "Law applicable to the crypto-assets and the competent court", (_f("G.18"), _f("G.19"))),
    ),
    *_points(
        "I",
        "H",
        (
            1,
            "Technology used, including the distributed ledger technology, protocols and technical standards",
            (_f("H.1", _F13), _f("H.2"), _f("H.3")),
        ),
        (2, "Consensus mechanism, where applicable", (_f("H.4", optional=True),)),
        (3, "Incentive mechanisms to secure transactions and any fees applicable", (_f("H.5"),)),
        (
            4,
            "Functioning of a distributed ledger operated by the issuer, the offeror or a third party on "
            "their "
            "behalf",
            (_f("H.6"), _f("H.7", _true("H.6"))),
        ),
        (
            5,
            "Outcome of an audit of the technology used, if one was conducted",
            (_f("H.8"), _f("H.9", _true("H.8"))),
        ),
    ),
    *_points(
        "I",
        "I",
        (1, "Risks associated with the offer to the public or the admission to trading", (_f("I.1"),)),
        (2, "Risks associated with the issuer, if different from the offeror", (_f("I.2", _B1),)),
        (3, "Risks associated with the crypto-assets", (_f("I.3"),)),
        (4, "Risks associated with project implementation", (_f("I.4"),)),
        (
            5,
            "Risks associated with the technology used and any mitigation measures",
            (_f("I.5"), _f("I.6", optional=True)),
        ),
    ),
)

# --- Annex II and Table 3 -----------------------------------------------------------------------------------

_T3_A7 = _lei("A.7")
_B15 = _dti("B.15")

_ANNEX_II = (
    *_points(
        "II",
        "A",
        (1, "Name of the issuer of the asset-referenced token", (_f("A.1"), _f("A.2", optional=True))),
        (2, "Legal form of the issuer", (_f("A.3", _T3_A7),)),
        (
            3,
            "Registered address and head office, where different, of the issuer",
            (_f("A.4", _T3_A7), _f("A.5", _T3_A7, optional=True)),
        ),
        (4, "Date of registration of the issuer", (_f("A.6"),)),
        (
            5,
            "Legal entity identifier or another identifier required by national law of the issuer",
            (_alt(_f("A.7"), _f("A.8")),),
        ),
        (6, "Identity of the parent company, where applicable", (_f("A.9", _T3_A7, optional=True),)),
        (
            7,
            "Identity, business addresses and functions of the members of the issuer's management body",
            (_f("A.10"),),
        ),
        (
            8,
            "Business or professional activity of the issuer and, where applicable, of its parent company",
            (_f("A.11"), _f("A.12", optional=True)),
        ),
        (
            9,
            "Financial condition of the issuer over the past three years or since its registration",
            (_f("A.13"), _alt(_f("A.14"), _f("A.15"))),
        ),
        (10, "Detailed description of the issuer's governance arrangements", (_f("A.16"),)),
        (
            11,
            "Authorisation as an issuer of an asset-referenced token and the competent authority, unless "
            "exempted under Article 17",
            (
                _f("A.17"),
                _f("A.18", _code("A.17", "NOEX")),
                _f("A.19", _code("A.17", "NOEX", annex=True)),
                _f("A.20", _code("A.17", "EX17", annex=True)),
            ),
        ),
        (
            12,
            "Other crypto-assets the issuer issues or other activities related to them, and any connection "
            "with the entity running the distributed ledger",
            (_f("A.21"), _f("A.22"), _f("A.23"), _f("A.24", _true("A.23", annex=True))),
        ),
    ),
    *_points(
        "II",
        "B",
        (
            1,
            "Name and abbreviation or ticker handler of the asset-referenced token",
            (_f("B.1", _B15), _f("B.2", _B15)),
        ),
        (
            2,
            "Characteristics of the asset-referenced token, including the data for classifying the white "
            "paper "
            "in the register",
            (
                _f("B.9"),
                _f("B.7"),
                _f("B.8"),
                _f("B.10"),
                _f("B.11"),
                _f("B.12"),
                _f("B.13", optional=True),
                _f("B.14"),
                _f("B.15", optional=True),
                _f("B.16", optional=True),
                _f("B.17"),
                _f("B.18"),
                _f("B.19"),
                _f("B.20", optional=True),
            ),
        ),
        (
            3,
            "Details of the natural or legal persons involved in the operationalisation of the token",
            (_f("B.3"),),
        ),
        (
            4,
            "Role, responsibilities and accountability of third-party entities under Article 34(5)(h)",
            (_f("B.4", optional=True),),
        ),
        (
            5,
            "Plans for the asset-referenced token, including past and future milestones and resources "
            "already "
            "allocated",
            (_f("B.5"), _f("B.6", optional=True)),
        ),
    ),
    *_points(
        "II",
        "C",
        (
            1,
            "Whether the white paper concerns an offer to the public or an admission to trading",
            (_f("C.1"),),
        ),
        (
            2,
            "Amount to be raised, minimum and maximum subscription goals, and whether and how "
            "oversubscriptions are accepted and allocated",
            (
                _f("C.2", optional=True),
                _f("C.3", optional=True),
                _f("C.4", optional=True),
                _f("C.5"),
                _f("C.6", _true("C.5")),
            ),
        ),
        (
            3,
            "Total number of units to be offered or admitted to trading, where applicable",
            (_f("C.7", optional=True),),
        ),
        (
            4,
            "Prospective holders targeted and any restriction on the type of holders",
            (_f("C.8"), _f("C.9", optional=True)),
        ),
        (
            5,
            "Notice of reimbursement, expected timeline of refunds and consequences of exceeding the maximum "
            "subscription goal",
            (_f("C.10"), _f("C.11"), _f("C.12")),
        ),
        (
            6,
            "Phases of the offer and any discounted purchase price for early purchasers",
            (_f("C.13"), _f("C.14", optional=True)),
        ),
        (
            7,
            "Subscription period of a time-limited offer",
            (_f("C.15"), _f("C.16", _true("C.15")), _f("C.17", _true("C.15"))),
        ),
        (8, "Methods of payment to purchase and to redeem the asset-referenced token", (_f("C.18"),)),
        (9, "Method and time schedule of transferring the purchased token to the holders", (_f("C.19"),)),
        (10, "Technical requirements the purchaser must fulfil to hold the token", (_f("C.20"),)),
        (
            11,
            "Crypto-asset service provider placing the tokens and the form of placement, where applicable",
            (_f("C.21", optional=True), _f("C.23", optional=True)),
        ),
        (
            12,
            "Trading platform where admission is sought, how investors access it and the costs involved, "
            "where "
            "applicable",
            (_f("C.24", optional=True), _f("C.26", optional=True), _f("C.27", optional=True)),
        ),
        (13, "Expenses related to the offer to the public", (_f("C.28"),)),
        (
            14,
            "Potential conflicts of interest of the persons involved in the offer or admission",
            (_f("C.29", optional=True),),
        ),
        (15, "Law applicable to the offer to the public and the competent court", (_f("C.30"), _f("C.31"))),
    ),
    *_points(
        "II",
        "D",
        (
            1,
            "Characteristics and functionality of the token and when the functionalities are planned to "
            "apply",
            (_f("D.1"), _f("D.2")),
        ),
        (
            2,
            "Rights and obligations of the purchaser and the procedure and conditions for exercising them",
            (_f("D.3", optional=True), _f("D.4")),
        ),
        (3, "Conditions under which the rights and obligations may be modified", (_f("D.5"),)),
        (
            4,
            "Future offers of the token by the issuer and the number of units it retains, where applicable",
            (_f("D.6", optional=True), _f("D.7", optional=True)),
        ),
        (
            5,
            "How and where the token can be bought or sold after the offer, where admission to trading is "
            "not "
            "sought",
            (_f("D.8"), _f("D.9", _false("D.8"))),
        ),
        (6, "Restrictions on the transferability of the token", (_f("D.10", optional=True),)),
        (
            7,
            "Functioning of protocols that increase or decrease the supply in response to demand",
            (_f("D.11"), _f("D.12", _true("D.11"))),
        ),
        (
            8,
            "Protection schemes protecting the value of the token and compensation schemes, where applicable",
            (_f("D.13"), _f("D.14", _true("D.13")), _f("D.15"), _f("D.16", _true("D.15"))),
        ),
        (
            9,
            "Nature and enforceability of rights, including permanent rights of redemption and claims "
            "against "
            "the issuer",
            (_f("D.17"),),
        ),
        (
            10,
            "Claim the token represents: referenced assets and proportions, relation to the reserve and "
            "valuation of the claim",
            (_f("D.18"), _f("D.19"), _f("D.20"), _f("D.21"), _f("D.22", optional=True)),
        ),
        (
            11,
            "Arrangements to ensure the liquidity of the token and the entities in charge, where applicable",
            (_f("D.23", optional=True), _f("D.24", optional=True)),
        ),
        (
            12,
            "Contact details for complaints, complaints-handling procedures and any dispute resolution "
            "mechanism",
            (_f("D.25"), _f("D.26"), _f("D.27", optional=True)),
        ),
        (
            13,
            "Rights of the holders when the issuer cannot fulfil its obligations, including in insolvency",
            (_f("D.28"),),
        ),
        (14, "Rights in the implementation of the recovery plan", (_f("D.29"),)),
        (15, "Rights in the implementation of the redemption plan", (_f("D.30"),)),
        (
            16,
            "How the token is redeemed, and whether the holder can choose the form of redemption, the form "
            "of "
            "transference or the currency",
            (_f("D.31"), _f("D.32"), _f("D.33"), _f("D.34"), _f("D.35")),
        ),
        (
            17,
            "Law applicable to the asset-referenced token and the competent court",
            (_f("D.36"), _f("D.37")),
        ),
    ),
    *_points(
        "II",
        "E",
        (
            1,
            "Technology used, including the distributed ledger technology, protocols and technical standards",
            (_f("E.1", _B15), _f("E.2"), _f("E.3", optional=True)),
        ),
        (2, "Consensus mechanism, where applicable", (_f("E.4", optional=True),)),
        (3, "Incentive mechanisms to secure transactions and any fees applicable", (_f("E.5"),)),
        (
            4,
            "Functioning of a distributed ledger operated by the issuer or a third party on its behalf",
            (_f("E.6"), _f("E.7", _true("E.6"))),
        ),
        (
            5,
            "Outcome of an audit of the technology used, if one was conducted",
            (_f("E.8"), _f("E.9", _true("E.8"))),
        ),
    ),
    *_points(
        "II",
        "F",
        (
            1,
            "Risks related to the reserve of assets when the issuer cannot fulfil its obligations",
            (_f("F.1"),),
        ),
        (2, "Risks associated with the issuer", (_f("F.2"),)),
        (3, "Risks associated with the offer to the public or the admission to trading", (_f("F.3"),)),
        (
            4,
            "Risks associated with the token, in particular with regard to the assets referenced",
            (_f("F.4"),),
        ),
        (5, "Risks associated with the operationalisation of the token project", (_f("F.5"),)),
        (
            6,
            "Risks associated with the technology used and any mitigation measures",
            (_f("F.6"), _f("F.7", optional=True)),
        ),
    ),
    *_points(
        "II",
        "G",
        (1, "Mechanism aligning the value of the reserve of assets with the claim", (_f("G.1"),)),
        (2, "Reserve of assets and its composition", (_f("G.2"),)),
        (3, "Mechanisms through which the tokens are issued and redeemed", (_f("G.3"),)),
        (
            4,
            "Whether part of the reserve assets is invested and, where applicable, the investment policy",
            (_f("G.4"), _f("G.5", _true("G.4"))),
        ),
        (
            5,
            "Custody arrangements for the reserve assets, including segregation, and the custodians",
            (_f("G.6"), _f("G.7")),
        ),
    ),
)

# --- Annex III and Table 4 ----------------------------------------------------------------------------------

_T4_A7 = _lei("A.7")
_B12 = _dti("B.12")

_ANNEX_III = (
    *_points(
        "III",
        "A",
        (1, "Name of the issuer of the e-money token", (_f("A.1"), _f("A.2", optional=True))),
        (2, "Legal form of the issuer", (_f("A.3", _T4_A7),)),
        (
            3,
            "Registered address and head office, where different, of the issuer",
            (_f("A.4", _T4_A7), _f("A.5", _T4_A7, optional=True)),
        ),
        (4, "Date of registration of the issuer", (_f("A.6"),)),
        (
            5,
            "Legal entity identifier or another identifier required by national law of the issuer",
            (_alt(_f("A.7"), _f("A.8")),),
        ),
        (7, "Identity of the parent company, where applicable", (_f("A.12", _T4_A7, optional=True),)),
        (
            8,
            "Identity, business address and functions of the members of the issuer's management body",
            (_f("A.13"),),
        ),
        (
            9,
            "Business or professional activity of the issuer and, where applicable, of its parent company",
            (_f("A.14"), _f("A.15", optional=True)),
        ),
        (10, "Potential conflicts of interest", (_f("A.16", optional=True),)),
        (
            11,
            "Other crypto-assets the issuer issues or other activities related to them, and any connection "
            "with the entity running the distributed ledger",
            (_f("A.17"), _f("A.18"), _f("A.19"), _f("A.20", _true("A.19", annex=True))),
        ),
        (
            12,
            "Financial condition of the issuer over the past three years or since its registration",
            (_f("A.21"), _alt(_f("A.22"), _f("A.23"))),
        ),
        (
            13,
            "Authorisation as an issuer of an e-money token and the competent authority, unless exempted "
            "under "
            "Article 48(4) and (5)",
            (_f("A.24"), _f("A.25", _false("A.24")), _f("A.26", _false("A.24", annex=True))),
        ),
    ),
    *_points(
        "III",
        "B",
        (1, "Name and abbreviation of the e-money token", (_f("B.1", _B12), _f("B.2", _B12))),
        (
            2,
            "Characteristics of the e-money token, including the data for classifying the white paper in the "
            "register",
            (
                _f("B.6"),
                _f("B.4"),
                _f("B.5"),
                _f("B.7"),
                _f("B.8"),
                _f("B.9"),
                _f("B.10", optional=True),
                _f("B.11"),
                _f("B.12", optional=True),
                _f("B.13", optional=True),
                _f("B.14"),
                _f("B.15"),
                _f("B.16"),
                _f("B.17", optional=True),
            ),
        ),
        (
            3,
            "Details of the natural or legal persons involved in the design and development",
            (_f("B.3"),),
        ),
    ),
    *_points(
        "III",
        "C",
        (
            1,
            "Whether the white paper concerns an offer to the public or an admission to trading",
            (_f("C.1"),),
        ),
        (
            2,
            "Total number of units to be offered or admitted to trading, where applicable",
            (_f("C.2", optional=True),),
        ),
        (
            3,
            "Trading platforms where admission to trading is sought, where applicable",
            (_f("C.3", optional=True),),
        ),
        (4, "Law applicable to the offer to the public and the competent court", (_f("C.5"), _f("C.6"))),
    ),
    *_points(
        "III",
        "D",
        (
            1,
            "Rights and obligations of the holder, including redemption at par value, and the procedure and "
            "conditions for exercising them",
            (_f("D.1"),),
        ),
        (2, "Conditions under which the rights and obligations may be modified", (_f("D.2"),)),
        (
            3,
            "Rights of the holders when the issuer cannot fulfil its obligations, including in insolvency",
            (_f("D.3"),),
        ),
        (4, "Rights in the implementation of the recovery plan", (_f("D.4"),)),
        (5, "Rights in the implementation of the redemption plan", (_f("D.5"),)),
        (
            6,
            "Contact details for complaints, complaints-handling procedures and any dispute resolution "
            "mechanism",
            (_f("D.6"), _f("D.7"), _f("D.8", optional=True)),
        ),
        (
            7,
            "Protection schemes protecting the value of the token and compensation schemes, where applicable",
            (_f("D.9"), _f("D.10", _true("D.9")), _f("D.11"), _f("D.12", _true("D.11"))),
        ),
        (8, "Law applicable to the e-money token and the competent court", (_f("D.13"), _f("D.14"))),
    ),
    *_points(
        "III",
        "E",
        (
            1,
            "Technology used, including the distributed ledger technology, protocols and technical standards",
            (_f("E.1", _dti("B.13")), _f("E.2"), _f("E.3", optional=True)),
        ),
        (2, "Technical requirements the purchaser must fulfil to gain control over the token", (_f("E.4"),)),
        (3, "Consensus mechanism, where applicable", (_f("E.5", optional=True),)),
        (4, "Incentive mechanisms to secure transactions and any fees applicable", (_f("E.6"),)),
        (
            5,
            "Functioning of a distributed ledger operated by the issuer or a third party on its behalf",
            (_f("E.7"), _f("E.8", _true("E.7"))),
        ),
        (
            6,
            "Outcome of an audit of the technology used, if one was conducted",
            (_f("E.9"), _f("E.10", _true("E.9"))),
        ),
    ),
    *_points(
        "III",
        "F",
        (1, "Risks associated with the issuer of the e-money token", (_f("F.1"),)),
        (2, "Risks associated with the e-money token", (_f("F.2"),)),
        (
            3,
            "Risks associated with the technology used and any mitigation measures",
            (_f("F.3"), _f("F.4", optional=True)),
        ),
    ),
)

ANNEX_REGIMES = {"I": WhitepaperType.OTHER, "II": WhitepaperType.ART, "III": WhitepaperType.EMT}
POINTS: dict[WhitepaperType, tuple[Point, ...]] = {
    WhitepaperType.OTHER: _ANNEX_I,
    WhitepaperType.ART: _ANNEX_II,
    WhitepaperType.EMT: _ANNEX_III,
}
POINTS_BY_RULE: dict[str, Point] = {point.rule_id: point for points in POINTS.values() for point in points}


# --- Reading the fields -------------------------------------------------------------------------------------

EMPTY = "empty"
PLACEHOLDER = "placeholder"
NOT_APPLICABLE = "not_applicable"
ANSWER = "answer"


def field_state(answer: str) -> str:
    """Whether a field is empty, holds only placeholders, is marked not applicable or holds an answer. A field
    that occurs more than once gives one answer per line; it holds an answer when one line does."""
    lines = [line.strip() for line in answer.split("\n") if line.strip()]
    if not lines:
        return EMPTY
    real = [line for line in lines if not is_placeholder(line)]
    if not real:
        return PLACEHOLDER
    if all(is_not_applicable(line) for line in real):
        return NOT_APPLICABLE
    return ANSWER


def _condition_state(condition: Condition, answers: Mapping[str, str], regime: WhitepaperType) -> bool | None:
    """True while the condition holds, False when it relieves the field, None when the draft does not say."""
    answer = str(answers.get(condition.field, ""))
    if condition.kind in (NO_LEI, NO_DTI):
        kind = LEI if condition.kind == NO_LEI else DTI
        return not field_holds(condition.field, kind, answer, regime)
    if condition.kind == FLAG:
        flag = field_flag(condition.field, answer, regime)
        if flag is None:
            return None
        return flag == (condition.value == "true")
    if condition.kind == CODE:
        codes = field_codes(condition.field, answer, regime)
        if not codes:
            return None
        return condition.value in codes
    state = field_state(answer)
    return True if state == ANSWER else False if state == NOT_APPLICABLE else None


def _name(number: str, regime: WhitepaperType, is_de: bool) -> str:
    """How a finding names a field: by number in German, with the template's English name in English."""
    name = FIELD_NAMES[regime].get(number)
    return number if is_de or not name else f"{number} ({name})"


# The words of each condition, in English and German: what holds, what relieves the field, what is unknown.
def _holds(condition: Condition, is_de: bool) -> str:
    field, value = condition.field, condition.value
    if condition.kind == NO_LEI:
        return f"Feld {field} keine gültige LEI angibt" if is_de else f"field {field} gives no valid LEI"
    if condition.kind == NO_DTI:
        return f"Feld {field} keinen gültigen DTI angibt" if is_de else f"field {field} gives no valid DTI"
    if condition.kind == FLAG:
        german = "richtig (true)" if value == "true" else "falsch (false)"
        return f"Feld {field} {german} ist" if is_de else f"field {field} is {value}"
    if condition.kind == CODE:
        return f"Feld {field} {value} angibt" if is_de else f"field {field} gives {value}"
    return f"Feld {field} eine Angabe enthält" if is_de else f"field {field} holds an answer"


def _relieves(condition: Condition, is_de: bool) -> str:
    field, value = condition.field, condition.value
    if condition.kind == NO_LEI:
        return f"Feld {field} gibt eine LEI an" if is_de else f"field {field} gives an LEI"
    if condition.kind == NO_DTI:
        return f"Feld {field} gibt einen DTI an" if is_de else f"field {field} gives a DTI"
    if condition.kind == FLAG:
        if is_de:
            return f"Feld {field} ist {'nicht richtig (true)' if value == 'true' else 'richtig (true)'}"
        return f"field {field} is {'not true' if value == 'true' else 'true'}"
    if condition.kind == CODE:
        return f"Feld {field} gibt einen anderen Code an" if is_de else f"field {field} gives another code"
    return (
        f"Feld {field} ist als nicht anwendbar markiert"
        if is_de
        else f"field {field} is marked not applicable"
    )


def _unknown(condition: Condition, is_de: bool) -> str:
    field = condition.field
    if condition.kind == FLAG:
        return (
            f"Feld {field} gibt weder richtig noch falsch an"
            if is_de
            else f"field {field} gives neither true nor false"
        )
    if condition.kind == CODE:
        return (
            f"Feld {field} gibt keinen Code der Vorlage an"
            if is_de
            else f"field {field} gives none of the template's codes"
        )
    return (
        f"Feld {field} ist leer oder enthält nur einen Platzhalter"
        if is_de
        else f"field {field} is empty or holds only a placeholder"
    )


@dataclass
class _Field:
    number: str
    name: str
    state: str
    optional: bool
    holding: list[Condition]
    unknown: list[Condition]


def _source(condition: Condition, is_de: bool) -> str:
    """The marker of a condition inferred from the Annex point (annex=True), which the template does not set
    (owner decision 2A of 2026-11-10, ADR 0005); none for a condition of the template."""
    if not condition.annex:
        return ""
    return " (Bedingung aus dem Anhangspunkt)" if is_de else " (a condition from the Annex point)"


def _clause(field: _Field, is_de: bool) -> str:
    """Why a conditional field is checked: its conditions hold, or the draft does not say. A condition from
    the Annex point says so."""
    parts = []
    if field.holding:
        joined = (
            " und ".join(_holds(c, is_de) + _source(c, is_de) for c in field.holding)
            if is_de
            else " and ".join(_holds(c, is_de) + _source(c, is_de) for c in field.holding)
        )
        parts.append(f" Verlangt, weil {joined}." if is_de else f" Required because {joined}.")
    if field.unknown:
        joined = "; ".join(_unknown(c, is_de) + _source(c, is_de) for c in field.unknown)
        parts.append(f" Als verlangt geprüft: {joined}." if is_de else f" Checked as required: {joined}.")
    return "".join(parts)


def _field_issue(field: _Field, is_de: bool) -> str | None:
    name, clause = field.name, _clause(field, is_de)
    if field.state == EMPTY:
        if field.optional:
            return (
                f"Feld {name} ist leer oder fehlt; trifft die Angabe nicht zu, sollte das Feld dies angeben."
                f"{clause}"
                if is_de
                else f"Field {name} is empty or not in the draft; where the item does not apply, the field "
                f"should say so.{clause}"
            )
        return (
            f"Feld {name} ist leer oder fehlt.{clause}"
            if is_de
            else f"Field {name} is empty or not in the draft.{clause}"
        )
    if field.state == PLACEHOLDER:
        return (
            f"Feld {name} enthält nur einen Platzhalter wie TBD.{clause}"
            if is_de
            else f"Field {name} holds only a placeholder such as TBD.{clause}"
        )
    if field.state == NOT_APPLICABLE and not field.optional:
        if not field.holding and not field.unknown:
            return (
                f"Feld {name} ist als nicht anwendbar markiert; die Vorlage verlangt es ohne Bedingung."
                if is_de
                else f"Field {name} is marked not applicable; the template asks for it without a condition."
            )
        return (
            f"Feld {name} ist als nicht anwendbar markiert.{clause}"
            if is_de
            else f"Field {name} is marked not applicable.{clause}"
        )
    return None


def _relief_note(name: str, condition: Condition, is_de: bool) -> str:
    """A field its condition relieves; a condition from the Annex point (annex=True) says it comes from
    there."""
    if is_de:
        source = (
            "die Bedingung stammt aus dem Anhangspunkt, der es nur verlangt,"
            if condition.annex
            else "die Vorlage verlangt es nur,"
        )
        relieves, holds = _relieves(condition, True), _holds(condition, True)
        return f"Feld {name} ist nicht verlangt: {relieves}; {source} wenn {holds}."
    source = (
        "the condition comes from the Annex point, which asks for it only"
        if condition.annex
        else "the template asks for it only"
    )
    relieves, holds = _relieves(condition, False), _holds(condition, False)
    return f"Field {name} is not required: {relieves}; {source} if {holds}."


def point_issues(
    point: Point, answers: Mapping[str, str], regime: WhitepaperType, is_de: bool
) -> tuple[str, tuple[str, ...], int]:
    """Check the fields of a point in a numbered-field draft: (status, issues, word count).

    Missing when every field that applies is empty or holds only placeholders; Review when one of them is
    empty, holds only a placeholder, or is marked not applicable without the template allowing it, or when no
    field of an alternative holds an answer; Pass otherwise. A field relieved by its condition is not checked;
    a note names the condition.
    """
    problems: list[str] = []
    notes: list[str] = []
    applying = 0
    blank = 0
    words = 0

    def read(item: PointField) -> _Field | None:
        nonlocal words
        name = _name(item.number, regime, is_de)
        holding: list[Condition] = []
        unknown: list[Condition] = []
        for condition in item.conditions:
            state = _condition_state(condition, answers, regime)
            if state is False:
                notes.append(_relief_note(name, condition, is_de))
                return None
            (holding if state else unknown).append(condition)
        answer = str(answers.get(item.number, ""))
        words += len(answer.split())
        return _Field(item.number, name, field_state(answer), item.optional, holding, unknown)

    for item in point.items:
        if isinstance(item, Alternative):
            members = [field for field in map(read, item.fields) if field is not None]
            if not members:
                continue
            applying += 1
            if any(member.state == ANSWER for member in members):
                continue
            if all(member.state in (EMPTY, PLACEHOLDER) for member in members):
                blank += 1
            names = " und ".join(m.name for m in members) if is_de else " and ".join(m.name for m in members)
            problems.append(
                f"Keines der Felder {names} enthält eine Angabe; Nr. {point.number} verlangt mindestens "
                "eines davon."
                if is_de
                else f"None of fields {names} holds an answer; point {point.number} asks for at least one "
                "of them."
            )
            continue
        field = read(item)
        if field is None:
            continue
        applying += 1
        if field.state in (EMPTY, PLACEHOLDER):
            blank += 1
        if issue := _field_issue(field, is_de):
            problems.append(issue)
    status = "missing" if applying and blank == applying else "review" if problems else "pass"
    return status, (*problems, *notes), words


def _in_table_order(point: Point) -> list[str]:
    """The point's field numbers in the order of the table: 09, then A.1, A.2, ..., A.10."""

    def key(number: str) -> tuple[str, int]:
        part, _, index = number.rpartition(".")
        return part, int(index)

    return sorted((field.number for field in point.fields), key=key)


def fields_text(point: Point, regime: WhitepaperType) -> str:
    """The point's fields as a finding or a rule page names them: "fields A.3 and A.4 of Table 2"."""
    numbers = _in_table_order(point)
    table = TABLE_NUMBERS[regime]
    if len(numbers) == 1:
        return f"field {numbers[0]} of Table {table}"
    return f"fields {', '.join(numbers[:-1])} and {numbers[-1]} of Table {table}"


def fields_text_de(point: Point, regime: WhitepaperType) -> str:
    numbers = _in_table_order(point)
    table = TABLE_NUMBERS[regime]
    if len(numbers) == 1:
        return f"Feld {numbers[0]} der Tabelle {table}"
    return f"Felder {', '.join(numbers[:-1])} und {numbers[-1]} der Tabelle {table}"
