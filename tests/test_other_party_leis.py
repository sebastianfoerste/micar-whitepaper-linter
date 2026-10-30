"""LEIs that the template of Implementing Regulation (EU) 2024/2984 asks for persons other than the parties.

Table 2 asks for the LEI of the crypto-asset service provider in charge of the placing (field E.31), Table 3
for that provider's LEI (C.22), the custodian's (G.8) and those of persons other than the issuer that offer
the token, seek its admission to trading or draw up the white paper (Part AA), and Table 4 for the LEI of
such a person (A.27). Every name and LEI here is fictional; the LEIs are synthetic with computed check digits.
"""

from pathlib import Path

import pytest

from micar_linter.lei import check_digits_for
from micar_linter.linter import Linter, lint_whitepaper
from micar_linter.numbered_fields import extract_numbered_fields
from micar_linter.rules.common import COMMON_RULES
from micar_linter.template_fields import FIELD_NAMES
from micar_linter.whitepaper import Whitepaper, WhitepaperType, load_whitepaper


def _lei(base: str) -> str:
    return base + check_digits_for(base)


ISSUER_LEI = _lei("9999SYNTH0000ZZQ21")
CASP_LEI = _lei("9999SYNTH0000ZZQ22")
CUSTODIAN_LEI = _lei("9999SYNTH0000ZZQ23")
OTHER_PERSON_LEI = _lei("9999SYNTH0000ZZQ24")
DRAFTER_LEI = _lei("9999SYNTH0000ZZQ25")
CONSISTENCY = next(rule for rule in COMMON_RULES if rule.rule_id == "COMMON.LEI_CONSISTENCY")

# Field names of Part AA of Table 3, and German field names of Tables 2, 3 and 4, as the Official Journal
# prints them (OJ L, 2024/2984, 3.12.2024).
AA_1 = (
    "Persons other than the issuer offering to the public or seeking admission to trading of the asset "
    "referenced token according to Article 19(1), second subparagraph, of Regulation (EU) 2023/1114"
)
AA_3 = (
    "Other persons drawing up the crypto-asset white paper according to Article 19(1), second "
    "subparagraph, of Regulation (EU) 2023/1114"
)
DE_E_30 = "Name des Anbieters von Kryptowerte-Dienstleistungen"
DE_E_31 = "CASP-Kennung"
DE_A_27 = (
    "Gemäß Artikel 51 Absatz 1 Unterabsatz 2 der Verordnung (EU) 2023/1114 Personen, die den E-Geld-Token "
    "öffentlich anbieten oder dessen Zulassung zum Handel beantragen, sofern sie nicht mit dem Emittenten "
    "identisch sind"
)


def _xhtml(tmp_path: Path, rows: list[tuple[str, str, str]]) -> Path:
    cells = "".join(f"<tr><td>{n}</td><td>{label}</td><td>{answer}</td></tr>" for n, label, answer in rows)
    path = tmp_path / "draft.xhtml"
    path.write_text(f"<html><body><table>{cells}</table></body></html>", encoding="utf-8")
    return path


def _rows(whitepaper_type: WhitepaperType, answers: list[tuple[str, str]]) -> list[tuple[str, str, str]]:
    names = FIELD_NAMES[whitepaper_type]
    return [(number, names[number], answer) for number, answer in answers]


def _consistency(path: Path, whitepaper_type: WhitepaperType):
    report = lint_whitepaper(load_whitepaper(path, whitepaper_type))
    return next(f for f in report.findings if f.rule.rule_id == "COMMON.LEI_CONSISTENCY")


def _prose(sections: dict[str, str]):
    whitepaper = Whitepaper(title="Synthetic", type=WhitepaperType.OTHER, sections=sections, metadata={})
    return Linter((CONSISTENCY,)).lint(whitepaper)[0]


def test_casp_identifier_of_table_2_is_not_an_inconsistent_lei(tmp_path: Path):
    rows = _rows(
        WhitepaperType.OTHER,
        [
            ("A.1", "Meadow Labs GmbH (fictional)"),
            ("A.6", ISSUER_LEI),
            ("D.1", "Meadow (fictional)"),
            ("E.1", "OTPC"),
            ("E.30", "Synthetic Placement CASP S.A. (fictional)"),
            ("E.31", CASP_LEI),
        ],
    )
    finding = _consistency(_xhtml(tmp_path, rows), WhitepaperType.OTHER)
    assert finding.status == "pass", finding.issues


def test_casp_identifier_under_its_german_name_is_not_an_inconsistent_lei(tmp_path: Path):
    rows = [
        ("A.1", "Name", "Wiesen Labs GmbH (fiktiv)"),
        ("A.6", "Rechtsträgerkennung", ISSUER_LEI),
        ("D.1", "Name des Kryptowert-Projekts", "Wiese (fiktiv)"),
        ("E.1", "Öffentliches Angebot oder Zulassung zum Handel", "OTPC"),
        ("E.30", DE_E_30, "Beispiel Platzierung AG (fiktiv)"),
        ("E.31", DE_E_31, CASP_LEI),
    ]
    finding = _consistency(_xhtml(tmp_path, rows), WhitepaperType.OTHER)
    assert finding.status == "pass", finding.issues


def test_casp_and_custodian_identifiers_of_table_3_are_not_inconsistent_leis(tmp_path: Path):
    rows = _rows(
        WhitepaperType.ART,
        [
            ("A.1", "EuroStable AG (fictional)"),
            ("A.7", ISSUER_LEI),
            ("B.9", "A fictional token that references a basket of euro deposits and bonds."),
            ("C.21", "Synthetic Placement CASP S.A. (fictional)"),
            ("C.22", CASP_LEI),
            ("G.7", "Synthetic Custody Bank AG (fictional)"),
            ("G.8", CUSTODIAN_LEI),
        ],
    )
    finding = _consistency(_xhtml(tmp_path, rows), WhitepaperType.ART)
    assert finding.status == "pass", finding.issues


def test_lei_of_a_person_other_than_the_emt_issuer_is_not_a_second_issuer_lei(tmp_path: Path):
    # Table 4 sets the persons other than the issuer in Part A, so their LEI lands in the issuer section.
    for label in (FIELD_NAMES[WhitepaperType.EMT]["A.27"], DE_A_27):
        rows = [
            *_rows(WhitepaperType.EMT, [("A.1", "PayEUR EMI GmbH (fictional)"), ("A.7", ISSUER_LEI)]),
            ("A.27", label, OTHER_PERSON_LEI),
            *_rows(WhitepaperType.EMT, [("B.6", "A fictional e-money token."), ("C.1", "OTPC")]),
        ]
        finding = _consistency(_xhtml(tmp_path, rows), WhitepaperType.EMT)
        assert finding.status == "pass", (label[:20], finding.issues)


def test_casp_named_in_the_same_sentence_as_its_lei_in_prose():
    sections = {
        "issuer": f"Synthetic Issuer AG (fictional), LEI {ISSUER_LEI}.",
        "offer_or_admission": (
            f"The crypto-asset service provider in charge of the placing, Example CASP S.A., has the LEI {CASP_LEI}."
        ),
    }
    assert _prose(sections).status == "pass"
    german = {
        "issuer": f"Beispiel Emittent AG (fiktiv), LEI {ISSUER_LEI}.",
        "offer_or_admission": (
            "Der mit der Platzierung beauftragte Anbieter von Kryptowerte-Dienstleistungen hat die "
            f"Rechtsträgerkennung {CASP_LEI}."
        ),
    }
    assert _prose(german).status == "pass"
    # A citation such as "Art. 36" inside the sentence does not end it.
    cited = {
        "issuer": f"Synthetic Issuer AG (fictional), LEI {ISSUER_LEI}.",
        "reserve_of_assets": f"The custodian under Art. 37 MiCAR, Example Bank AG, has the LEI {CUSTODIAN_LEI}.",
    }
    assert _prose(cited).status == "pass"


@pytest.mark.parametrize(
    "summary",
    [
        f"The LEI is {CASP_LEI}.",
        # The role ends with its sentence: the next sentence's LEI is not the provider's.
        f"Example CASP S.A. acts as crypto-asset service provider for the placing. The issuer's LEI is {CASP_LEI}.",
    ],
)
def test_an_lei_not_given_as_another_persons_is_still_compared_with_the_parties(summary: str):
    finding = _prose({"issuer": f"Synthetic Issuer AG, LEI {ISSUER_LEI}.", "summary": summary})
    assert finding.status == "review"
    assert CASP_LEI in finding.issues[0]


def test_two_issuer_leis_without_a_named_role_are_still_reported():
    finding = _prose({"issuer": f"Synthetic Issuer AG, LEI {ISSUER_LEI} or {OTHER_PERSON_LEI}."})
    assert finding.status == "review"


def _part_aa_rows() -> list[tuple[str, str, str]]:
    names = FIELD_NAMES[WhitepaperType.ART]
    return [
        *_rows(WhitepaperType.ART, [("A.1", "EuroStable AG (fictional)"), ("A.7", ISSUER_LEI)]),
        ("AA.1", names["AA.1"], OTHER_PERSON_LEI),
        ("AA.2", names["AA.2"], "The fictional distributor offers the token to its own customers."),
        ("AA.3", names["AA.3"], DRAFTER_LEI),
        ("AA.4", names["AA.4"], "A fictional law firm drew up the white paper for the issuer."),
        *_rows(WhitepaperType.ART, [("B.9", "A fictional token."), ("C.1", "OTPC")]),
    ]


def test_table_3_part_aa_fills_the_offeror_section(tmp_path: Path):
    whitepaper = load_whitepaper(_xhtml(tmp_path, _part_aa_rows()), WhitepaperType.ART)
    offeror = whitepaper.section("offeror")
    assert OTHER_PERSON_LEI in offeror and DRAFTER_LEI in offeror
    assert "The fictional distributor offers the token" in offeror
    assert OTHER_PERSON_LEI not in whitepaper.section("issuer")


def test_table_3_part_aa_is_a_recognised_section_with_consistent_leis(tmp_path: Path):
    report = lint_whitepaper(load_whitepaper(_xhtml(tmp_path, _part_aa_rows()), WhitepaperType.ART))
    assert not any("'offeror'" in warning for warning in report.warnings), report.warnings
    finding = next(f for f in report.findings if f.rule.rule_id == "COMMON.LEI_CONSISTENCY")
    assert finding.status == "pass", finding.issues


def test_part_aa_field_names_come_from_table_3():
    names = FIELD_NAMES[WhitepaperType.ART]
    assert names["AA.1"] == AA_1
    assert names["AA.3"] == AA_3
    assert {"AA.1", "AA.2", "AA.3", "AA.4"} <= set(names)


def test_part_aa_label_run_into_its_answer_is_split_off(tmp_path: Path):
    # A two-column row sets the field name in the answer cell, as a rendering converted from PDF does.
    cells = "".join(
        f"<tr><td>{n}</td><td>{text}</td></tr>"
        for n, text in [
            ("A.1", "Statutory name EuroStable AG (fictional)"),
            ("A.7", f"Legal entity identifier {ISSUER_LEI}"),
            ("AA.1", f"{AA_1} {OTHER_PERSON_LEI}"),
            ("B.9", "Crypto-asset characteristics A fictional token."),
            ("C.1", "Public offering or admission to trading OTPC"),
        ]
    )
    path = tmp_path / "two-columns.xhtml"
    path.write_text(f"<html><body><table>{cells}</table></body></html>", encoding="utf-8")
    whitepaper = load_whitepaper(path, WhitepaperType.ART)
    assert whitepaper.section("offeror") == f"{AA_1}: {OTHER_PERSON_LEI}"


@pytest.mark.parametrize(
    "title",
    [
        # As the Official Journal prints the title of Part AA of Table 3, in English and in German.
        "AA- information on other persons offering to the public or seeking admission to trading of "
        "asset-referenced tokens other than the issuer and on other persons drawing up the crypto-asset white "
        "paper in accordance with Article 19(1), second subparagraph, of Regulation (EU) 2023/1114",
        "AA \u2013 Gemäß Artikel 19 Absatz 1 Unterabsatz 2 der Verordnung (EU) 2023/1114 Informationen über "
        "andere Personen als den Emittenten, die vermögenswertereferenzierte Token öffentlich anbieten oder ihre "
        "Zulassung zum Handel beantragen, und über andere Personen, die das Kryptowerte-Whitepaper erstellen",
        "Part AA - Information on other persons offering the token",
    ],
)
def test_part_aa_title_ends_the_field_before_it(tmp_path: Path, title: str):
    path = tmp_path / "paragraphs.xhtml"
    path.write_text(
        "<html><body><p>A.23 Connection between the issuer and the entity running the DLT: N/A</p>"
        f"<h2>{title}</h2><p>AA.2 Reason: The fictional distributor offers the token.</p></body></html>",
        encoding="utf-8",
    )
    fields = {field.field_id: field for field in extract_numbered_fields(path)}
    assert fields["A.23"].content == "N/A"
    assert not fields["A.23"].answered
