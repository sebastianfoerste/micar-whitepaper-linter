"""White papers in the numbered-field layout of Implementing Regulation (EU) 2024/2984."""

from pathlib import Path

import pytest

from micar_linter.cli import main
from micar_linter.linter import lint_whitepaper
from micar_linter.numbered_fields import (
    MERGED_LABELS_NOTE,
    NumberedField,
    extract_numbered_fields,
    is_numbered_layout,
    sections_from_numbered_fields,
)
from micar_linter.template_fields import FIELD_NAMES
from micar_linter.whitepaper import WhitepaperType, load_whitepaper

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "examples" / "numbered-other-draft.xhtml"
# Public register documents fetched by the study scripts. Not committed, so these checks run only where the cache exists.
STUDY_CACHE = ROOT / ".study-cache" / "title-ii-whitepapers"


def _write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "draft.xhtml"
    path.write_text(f"<html><body>{body}</body></html>", encoding="utf-8")
    return path


def test_table_rows_map_to_the_sections_of_the_stated_regime():
    whitepaper = load_whitepaper(SAMPLE, WhitepaperType.OTHER)
    assert whitepaper.type is WhitepaperType.OTHER
    assert whitepaper.section("issuer").startswith("Issuer different from offeror")
    assert "Legal form: Limited liability company" in whitepaper.section("issuer")
    assert whitepaper.section("notification_date") == "Date of notification: 2026-03-02"
    assert "management body" in whitepaper.section("management_statement")
    assert whitepaper.section("language").endswith("white paper: English")
    assert set(whitepaper.sections) >= {"summary", "risk_warning", "project", "risks", "environmental_impact"}


def test_numbered_layout_requires_an_explicit_regime(capsys):
    # The template names every regime ("other than an asset-referenced token"), which misled the wording heuristic.
    with pytest.raises(SystemExit, match="State the regime explicitly"):
        load_whitepaper(SAMPLE)
    assert main([str(SAMPLE), "--type", "other", "--json"]) == 0
    assert '"whitepaper_type": "other"' in capsys.readouterr().out


def test_template_wording_cannot_satisfy_a_rule_for_unanswered_fields():
    report = lint_whitepaper(load_whitepaper(SAMPLE, WhitepaperType.OTHER))
    offeror = next(finding for finding in report.findings if finding.rule.rule_id == "ANNEX_I.A")
    assert offeror.status == "review"
    assert any("legal form" in issue for issue in offeror.issues)
    assert any(warning.startswith("Part A: all 3 numbered fields") for warning in report.warnings)


def test_inline_fields_split_without_following_cross_references(tmp_path: Path):
    path = _write(
        tmp_path,
        "<p>A.1 Name: N/A A.2 Legal form: N/A</p>"
        "<p>B.1 Name: Example AG B.2 Abbreviation: See F.14 B.3 Legal form: Stock corporation</p>"
        "<p><b>C.1 Name:</b> Example Exchange S.A.</p>",
    )
    fields = {field.field_id: field for field in extract_numbered_fields(path)}
    assert set(fields) == {"A.1", "A.2", "B.1", "B.2", "B.3", "C.1"}
    assert (fields["B.2"].label, fields["B.2"].content) == ("Abbreviation", "See F.14")
    assert fields["C.1"].content == "Example Exchange S.A."
    assert not fields["A.2"].answered
    assert is_numbered_layout(list(fields.values()))


# Part titles of Table 2 as the Official Journal prints them, in English and German. Only the English
# title of Part B has fewer than 20 words; every German title starts with "Teil".
PART_TITLES = {
    "en-B": "Part B - Information about the issuer, if different from the offeror or person seeking admission "
    "to trading",
    "en-C": "Part C- Information about the operator of the trading platform in cases where it draws up the "
    "crypto-asset white paper and information about other persons drawing the crypto-asset white paper "
    "pursuant to Article 6(1), second subparagraph, of Regulation (EU) 2023/1114",
    "en-J": "Part J \u2013 Information on the sustainability indicators in relation to adverse impact on the "
    "climate and other environment-related adverse impacts",
    "de-B": "Teil B \u2013 Informationen über den Emittenten, wenn es sich hierbei nicht um den Anbieter oder "
    "die Person handelt, die die Zulassung zum Handel beantragt",
    "de-C": "Teil C \u2013 Informationen über den Betreiber der Handelsplattform in Fällen, in denen er das "
    "Kryptowerte-Whitepaper erstellt, und Informationen über andere Personen, die das "
    "Kryptowerte-Whitepaper gemäß Artikel 6 Absatz 1 Unterabsatz 2 der Verordnung (EU) 2023/1114 erstellen",
    "de-D": "Teil D \u2013 Informationen über das Kryptowert-Projekt",
    "de-J": "Teil J \u2013 Informationen zu den Nachhaltigkeitsindikatoren in Bezug auf nachteilige "
    "Auswirkungen auf das Klima und andere umweltbezogene nachteilige Auswirkungen",
}


@pytest.mark.parametrize("key", sorted(PART_TITLES))
def test_part_title_between_paragraph_fields_ends_the_field_before_it(tmp_path: Path, key: str):
    # A part title is no answer: the field before it keeps "N/A", so the template's wording cannot
    # count toward a check, whatever the length or language of the title.
    path = _write(
        tmp_path,
        "<p>A.1 Name: Quillmoor Ledger S.A.</p><p>A.2 Legal form: N/A</p>"
        f"<h2>{PART_TITLES[key]}</h2>"
        "<p>B.1 Name: Quillmoor Issuer AG</p>",
    )
    fields = {field.field_id: field for field in extract_numbered_fields(path)}
    assert fields["A.2"].content == "N/A"
    assert not fields["A.2"].answered


@pytest.mark.parametrize(
    "text",
    [
        "A. The offeror runs the shared ledger service for logistics firms in three Member States and has "
        "done so since the ledger went live in the spring of last year.",
        "Teile der Erlöse fließen in den Betrieb des gemeinsamen Ledgers.",
    ],
)
def test_long_or_ordinary_paragraph_after_a_field_stays_in_it(tmp_path: Path, text: str):
    # Only a part title leaves its field: a long paragraph that starts with a letter and a full stop,
    # and a sentence that starts with "Teile", belong to the field before them.
    path = _write(tmp_path, f"<p>A.13 Business activity: Ledger services.</p><p>{text}</p>")
    fields = {field.field_id: field for field in extract_numbered_fields(path)}
    assert fields["A.13"].content == f"Ledger services. {text}"


def test_leading_fields_of_tables_3_and_4_do_not_collide_with_part_i(tmp_path: Path):
    rows = "".join(
        f"<tr><td>{number}</td><td>{label}</td><td>{content}</td></tr>"
        for number, label, content in [
            ("I.01", "Date of notification", "2026-03-02"),
            ("I.06", "Right of redemption", "Holders can redeem at par at any time."),
            ("A.1", "Statutory name", "Example Issuer AG"),
            ("B.14", "Language or languages of the crypto-asset white paper", "German"),
            ("D.1", "Holder's rights and obligations", "Redemption at market value of the reserve."),
            ("G.1", "Description of the reserve of assets", "Bank deposits and government bonds."),
        ]
    )
    whitepaper = load_whitepaper(_write(tmp_path, f"<table>{rows}</table>"), WhitepaperType.ART)
    assert whitepaper.section("notification_date") == "Date of notification: 2026-03-02"
    assert "risks" not in whitepaper.sections
    assert "redeem at par" in whitepaper.section("summary")
    assert "Bank deposits" in whitepaper.section("reserve_of_assets")
    for part in ("redeem at par", "market value of the reserve", "Bank deposits"):
        assert part in whitepaper.section("redemption")
    assert "German" in whitepaper.section("language")


def _emt_table(tmp_path: Path, rows: list[tuple[str, ...]]) -> Path:
    cells = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    return _write(tmp_path, f"<table>{cells}</table>")


_EMT_BASE = [
    ("I.01", "Date of notification", "2026-03-02"),
    ("A.1", "Statutory name", "Example E-Money Institution SAS"),
    ("C.1", "Public offering or admission to trading", "Offer to the public."),
    ("F.1", "Risks", "Holders bear the risk of a failure of the issuer."),
]


def test_language_field_whose_label_shares_the_answer_cell(tmp_path: Path):
    # Some white papers set "B.11" in one cell and the label with its answer in the next.
    path = _emt_table(tmp_path, [*_EMT_BASE, ("B.11", "Language or languages of the white paper English")])
    whitepaper = load_whitepaper(path, WhitepaperType.EMT)
    assert whitepaper.section("language").endswith("English")
    report = lint_whitepaper(whitepaper)
    assert not any("labelled as the language" in warning for warning in report.warnings)


def test_unlabelled_field_mentioning_a_language_is_not_the_language_field(tmp_path: Path):
    path = _emt_table(
        tmp_path, [*_EMT_BASE, ("E.1", "Smart contracts are written in a programming language.")]
    )
    assert "language" not in load_whitepaper(path, WhitepaperType.EMT).sections


def test_emt_safeguarding_reads_the_fields_that_describe_it(tmp_path: Path):
    funds = (
        "Funds received in exchange for the tokens are safeguarded in segregated accounts "
        "at a credit institution, protected in the insolvency of the issuer."
    )
    path = _emt_table(tmp_path, [*_EMT_BASE, ("D.3", "Rights of holders", funds)])
    whitepaper = load_whitepaper(path, WhitepaperType.EMT)
    assert "segregated accounts" in whitepaper.section("safeguarding")
    report = lint_whitepaper(whitepaper)
    finding = next(f for f in report.findings if f.rule.rule_id == "ANNEX_III.SAFEGUARDING")
    assert finding.status != "missing"
    assert any(warning.endswith("mention it: D.3.") for warning in report.warnings)


def test_emt_safeguarding_stays_missing_when_no_field_describes_it(tmp_path: Path):
    whitepaper = load_whitepaper(_emt_table(tmp_path, _EMT_BASE), WhitepaperType.EMT)
    assert "safeguarding" not in whitepaper.sections
    report = lint_whitepaper(whitepaper)
    finding = next(f for f in report.findings if f.rule.rule_id == "ANNEX_III.SAFEGUARDING")
    assert finding.status == "missing"
    assert any("no answered field mentions safeguarding" in warning for warning in report.warnings)


def test_spacer_spans_inside_words_leave_the_words_whole(tmp_path: Path):
    # The layout of pdf2htmlEX: pages of absolutely placed lines, with empty spacer spans inside words.
    path = _write(
        tmp_path,
        '<div class="pf" data-page-no="1"><div class="pc">'
        '<div class="t">04<span class="_ _2"></span>Statement in accor<span class="_ _0"></span>dance with Article 51(4)</div>'
        '<div class="t"><ix:nonNumeric name="mica:RiskWarning" contextRef="c1" continuedAt="k1">'
        'The e-money token is not covered by the inves<span class="_ _1"></span>tor compen<span class="_ _0"></span>sation '
        'schemes under Directive 97/9/EC or by the depo<span class="_ _0"></span>sit guaran<span class="_ _0"></span>tee '
        "schemes</ix:nonNumeric></div>"
        '</div></div><div class="pf" data-page-no="2"><div class="pc">'
        '<div class="t"><ix:continuation id="k1">under Direc<span class="_ _0"></span>tive 2014/49/EU.</ix:continuation></div>'
        '<div class="t">A.1 Na<span class="_ _0"></span>me</div>'
        '<div class="t"><ix:nonNumeric name="mica:IssuerName" contextRef="c1">'
        'Example Money Financ<span class="_ _0"></span>ial Europe SAS</ix:nonNumeric></div>'
        '<div class="t">B.1<span class="_ _2"></span>Name of the e-money token</div>'
        '<div class="t">Exam<span class="_ _1"></span>ple Euro Token</div>'
        '<div class="t">F.1<span class="_ _2"> </span>Description of the ri<span class="_ _0"></span>sks</div>'
        '<div class="t">Holders face li<span class="_ _0"></span>quidity and market ri<span class="_ _0"></span>sks.</div>'
        "</div></div>",
    )
    fields = {field.field_id: field for field in extract_numbered_fields(path)}
    # A spacer with no space in it still keeps "04" and "B.1" apart from their labels.
    assert set(fields) == {"04", "A.1", "B.1", "F.1"}
    assert fields["04"].content.startswith("Statement in accordance with Article 51(4) ")
    assert fields["04"].content.endswith(
        "not covered by the investor compensation schemes under Directive 97/9/EC "
        "or by the deposit guarantee schemes under Directive 2014/49/EU."
    )
    assert (fields["A.1"].label, fields["A.1"].content) == ("Name", "Example Money Financial Europe SAS")
    assert fields["B.1"].content.endswith("Example Euro Token")
    assert fields["F.1"].content.endswith("Holders face liquidity and market risks.")

    report = lint_whitepaper(load_whitepaper(path, WhitepaperType.EMT))
    warning = next(finding for finding in report.findings if finding.rule.rule_id == "COMMON.RISK_WARNING")
    assert not any(issue.startswith("Missing review terms") for issue in warning.issues)


def test_spacer_widths_in_the_css_separate_words_and_kerning_does_not(tmp_path: Path):
    # Converters in the style of pdf2htmlEX can leave a gap between words as an empty spacer;
    # its CSS width, here 14.6px against a 32px font, marks it as one.
    path = _write(
        tmp_path,
        "<style>._0{margin-left:-1.1px;}._1{width:1.2px;}._2{width:14.6px;}.fs0{font-size:32px;}</style>"
        '<div class="pf"><div class="pc">'
        '<div class="t fs0">A.2<span class="_ _1"></span>\u2013 Legal form</div>'
        '<div class="t fs0">Simplified joint<span class="_ _2"></span>stock comp<span class="_ _0"></span>any</div>'
        '<div class="t fs0">B.2<span class="_ _2"></span>Name of the e-money token</div>'
        "</div></div>",
    )
    fields = {field.field_id: field for field in extract_numbered_fields(path)}
    assert set(fields) == {"A.2", "B.2"}
    assert fields["A.2"].content.endswith("Simplified joint stock company")
    assert fields["B.2"].content == "Name of the e-money token"


def test_table_cells_keep_their_paragraphs_apart(tmp_path: Path):
    row = "<tr><td>A.1</td><td>Name</td><td><p>Example AG.</p><p>Formerly Sample<br/>GmbH.</p></td></tr>"
    (field,) = extract_numbered_fields(_write(tmp_path, f"<table>{row}</table>"))
    assert field.content == "Example AG. Formerly Sample GmbH."


def test_labels_that_run_into_the_answers_are_reported(tmp_path: Path):
    # A rendering converted from PDF puts each field number in its own text run, so the label joins the answer.
    rows = "".join(
        f"<div><span>{part}.{number}</span></div><div><span>Field {part}{number} label "
        f"{'N/A' if part == 'C' else 'answer for the fictional issuer'}</span></div>"
        for part in "ABCDE"
        for number in range(1, 5)
    )
    whitepaper = load_whitepaper(_write(tmp_path, rows), WhitepaperType.OTHER)

    assert whitepaper.metadata["extraction_notes"][0] == MERGED_LABELS_NOTE
    # The risk the note names: the "N/A" field reads as answered, label included.
    assert "Field C1 label N/A" in whitepaper.sections["trading_platform_operator"]


def test_fields_with_their_own_label_raise_no_merged_label_note():
    whitepaper = load_whitepaper(SAMPLE, WhitepaperType.OTHER)
    assert MERGED_LABELS_NOTE not in whitepaper.metadata["extraction_notes"]


def test_merged_label_note_needs_four_in_five_unlabelled_fields(tmp_path: Path):
    # Eleven of fourteen lettered fields keep the label in the answer cell: just under four in five.
    path = _emt_table(tmp_path, [*_EMT_BASE, *((f"B.{n}", f"Field B{n} label N/A") for n in range(1, 12))])
    whitepaper = load_whitepaper(path, WhitepaperType.EMT)
    assert MERGED_LABELS_NOTE not in whitepaper.metadata["extraction_notes"]


def test_label_sharing_the_answer_cell_raises_the_merged_label_note(tmp_path: Path):
    # Twelve of fifteen lettered fields keep the label in the answer cell.
    path = _emt_table(tmp_path, [*_EMT_BASE, *((f"B.{n}", f"Field B{n} label N/A") for n in range(1, 13))])
    whitepaper = load_whitepaper(path, WhitepaperType.EMT)
    assert whitepaper.metadata["extraction_notes"][0] == MERGED_LABELS_NOTE


# Fictional answers in the numbering of Table 2; each label is the template's field name for that number.
_TABLE_2_ANSWERS = [
    ("01", "2026-03-02"),
    *((f"A.{number}", "N/A") for number in range(1, 18)),
    ("B.1", "TRUE"),
    ("B.2", "Example Issuer AG (fictional)"),
    ("B.3", "TBD"),
    ("B.4", "Musterweg 1, 10115 Berlin, Germany"),
    ("D.1", "Example Project"),
    ("D.4", "The fictional project builds a marketplace for garden supplies and rewards repeat buyers."),
    ("F.12", "English"),
    ("I.1", "The price can fall to zero, and a holder may be unable to sell the token."),
]


def _labelled(answers: list[tuple[str, str]], whitepaper_type: WhitepaperType) -> list[tuple[str, str, str]]:
    return [(number, FIELD_NAMES[whitepaper_type][number], answer) for number, answer in answers]


def _three_columns(rows: list[tuple[str, str, str]]) -> str:
    cells = "".join(f"<tr><td>{n}</td><td>{label}</td><td>{answer}</td></tr>" for n, label, answer in rows)
    return f"<table>{cells}</table>"


def _label_in_answer_cell(rows: list[tuple[str, str, str]]) -> str:
    cells = "".join(f"<tr><td>{n}</td><td>{label} {answer}</td></tr>" for n, label, answer in rows)
    return f"<table>{cells}</table>"


def _split_word(label: str) -> str:
    # pdf2htmlEX writes kerning as an empty span inside a word, which splits it in the extracted text.
    word = max(label.split(), key=len)
    return label.replace(word, f'{word[:3]}<span class="_ _0"></span>{word[3:]}', 1)


def _converted_from_pdf(rows: list[tuple[str, str, str]], first_copies: dict[str, str] | None = None) -> str:
    # Field number, label and answer in separate text runs; the label follows a dash and is printed twice,
    # the first time in the wording first_copies gives for the field number.
    first = first_copies or {}
    lines = "".join(
        f'<div class="t">{n}</div><div class="t">\u2013 {_split_word(first.get(n, label))}</div>'
        f'<div class="t">{_split_word(label)}</div><div class="t">{a}</div>'
        for n, label, a in rows
    )
    return f'<div class="pf"><div class="pc">{lines}</div></div>'


def _load(tmp_path: Path, name: str, body: str, whitepaper_type: WhitepaperType):
    path = tmp_path / f"{name}.xhtml"
    style = "<head><style>._0{margin-left:-1.1px;}</style></head>"
    path.write_text(f"<html>{style}<body>{body}</body></html>", encoding="utf-8")
    return load_whitepaper(path, whitepaper_type)


@pytest.mark.parametrize("layout", [_label_in_answer_cell, _converted_from_pdf])
def test_template_labels_split_off_give_the_sections_of_a_labelled_table(tmp_path: Path, layout):
    rows = _labelled(_TABLE_2_ANSWERS, WhitepaperType.OTHER)
    labelled = _load(tmp_path, "labelled", _three_columns(rows), WhitepaperType.OTHER)
    merged = _load(tmp_path, "merged", layout(rows), WhitepaperType.OTHER)

    assert merged.sections == labelled.sections
    assert merged.metadata["extraction_notes"] == labelled.metadata["extraction_notes"]
    statuses = [(f.rule.rule_id, f.status) for f in lint_whitepaper(merged).findings]
    assert statuses == [(f.rule.rule_id, f.status) for f in lint_whitepaper(labelled).findings]
    name = FIELD_NAMES[WhitepaperType.OTHER]["B.2"]
    assert f"\n{name}: Example Issuer AG (fictional)\nTBD\n" in merged.section("issuer")


@pytest.mark.parametrize("layout", [_label_in_answer_cell, _converted_from_pdf])
def test_part_answered_only_not_applicable_cannot_pass_on_template_wording(tmp_path: Path, layout):
    # With its labels, Part A would hold every review term of ANNEX_I.A and more than its 50 words.
    rows = _labelled(_TABLE_2_ANSWERS, WhitepaperType.OTHER)
    whitepaper = _load(tmp_path, "merged", layout(rows), WhitepaperType.OTHER)

    assert set(whitepaper.section("offeror").split("\n")) == {"N/A"}
    report = lint_whitepaper(whitepaper)
    assert next(f for f in report.findings if f.rule.rule_id == "ANNEX_I.A").status == "review"
    note = "Part A: all 17 numbered fields are marked not applicable. Confirm that the part does not apply."
    assert note in report.warnings
    assert not any("separate label" in warning for warning in report.warnings)


def test_fields_holding_only_their_names_are_unanswered(tmp_path: Path):
    # A blank template: the names of Part A alone would hold every review term of ANNEX_I.A.
    rows = [(number, label, "") for number, label, _ in _labelled(_TABLE_2_ANSWERS, WhitepaperType.OTHER)]
    whitepaper = _load(tmp_path, "blank", _label_in_answer_cell(rows), WhitepaperType.OTHER)

    assert whitepaper.sections == {}
    report = lint_whitepaper(whitepaper)
    assert {f.status for f in report.findings if f.rule.rule_id.startswith("ANNEX_I.")} == {"missing"}
    assert not any(warning.startswith("No leading numbered fields") for warning in report.warnings)


def test_emt_label_in_the_answer_cell_is_split_off(tmp_path: Path):
    answers = [("I.01", "2026-03-02"), ("A.1", "Example E-Money Institution SAS (fictional)"), ("A.3", "N/A")]
    answers += [("B.1", "Example Euro Token"), ("B.11", "English"), ("C.1", "TBD"), ("F.1", "N/A")]
    rows = _labelled(answers, WhitepaperType.EMT)
    whitepaper = _load(tmp_path, "emt", _label_in_answer_cell(rows), WhitepaperType.EMT)

    names = FIELD_NAMES[WhitepaperType.EMT]
    assert whitepaper.section("issuer") == f"{names['A.1']}: Example E-Money Institution SAS (fictional)\nN/A"
    assert whitepaper.section("language") == f"{names['B.11']}: English"
    assert whitepaper.section("offer_or_admission") == "TBD"
    assert whitepaper.section("risks") == "N/A"
    labelled = _load(tmp_path, "labelled", _three_columns(rows), WhitepaperType.EMT)
    assert whitepaper.metadata["extraction_notes"] == labelled.metadata["extraction_notes"]


def test_first_copy_of_a_name_in_other_words_is_split_off(tmp_path: Path):
    # The CoreFiling rendering can word the first copy of a field name differently from the second.
    answers = [
        ("I.01", "2026-03-02"),
        ("A.1", "Example E-Money Institution SAS (fictional)"),
        ("A.22", "N/A"),
        ("B.6", "A fictional token redeemable at par in euro."),
        ("C.3", "Example Exchange (fictional)"),
        ("F.1", "N/A"),
    ]
    rows = _labelled(answers, WhitepaperType.EMT)
    names = FIELD_NAMES[WhitepaperType.EMT]
    first_copies = {
        "A.22": names["A.22"].replace("for the", "over the"),
        "B.6": names["B.6"].replace("Crypto-asset", "Crypto-assets"),
        "C.3": names["C.3"].removesuffix(" name"),
    }
    assert all(first_copies[number] != names[number] for number in first_copies)
    merged = _load(tmp_path, "merged", _converted_from_pdf(rows, first_copies), WhitepaperType.EMT)
    labelled = _load(tmp_path, "labelled", _three_columns(rows), WhitepaperType.EMT)

    assert merged.sections == labelled.sections
    assert merged.metadata["extraction_notes"] == labelled.metadata["extraction_notes"]
    assert merged.section("issuer").endswith("\nN/A")


@pytest.mark.parametrize(
    ("label", "content", "line"),
    [
        # A dash or bullet joins a label to its answer; on its own it answers "not applicable" or holds a place.
        ("", "Head office \u2013 N/A", "N/A"),
        ("", "Head office \u2013", "N/A"),
        ("", "Registration date \u2022", "\u2022"),
        ("", "Email address TBC", "TBC"),
        ("", "Response time (days): 10", "Response time (Days): 10"),
        ("", "LEGAL FORM Stock corporation", "Legal form: Stock corporation"),
        # The longest field name wins, so "business activity" does not read as the answer of "Parent company".
        ("", "Parent company business activity N/A", "N/A"),
        # A label cut off inside a word takes the rest of the name from the content.
        ("Le", "gal form Stock corporation", "Legal form: Stock corporation"),
        # A label repeated in its answer cell is split off again.
        ("Legal form", "Legal form N/A", "N/A"),
        ("\u2013 Legal form", "Stock corporation", "Legal form: Stock corporation"),
        # A rendering can word the first copy of a name differently.
        (
            "",
            "Financial condition over the past three years Financial condition for the past three years N/A",
            "N/A",
        ),
        (
            "",
            "Trading platforms Trading platforms name Example Exchange",
            "Trading platforms name: Example Exchange",
        ),
        # The second copy can be the one in other words.
        (
            "",
            "Financial condition for the past three years Financial condition over the past three years N/A",
            "N/A",
        ),
        # Here the second copy is the name Table 2 uses for the field of Table 4.
        (
            "",
            "Another identifier required pursuant to applicable law "
            "Another identifier required pursuant to applicable national law N/A",
            "N/A",
        ),
        # An acronym in brackets for the name, and a name of another table.
        ("", "Distributed ledger technology (DLT) N/A", "N/A"),
        ("", "Token-related risks TBD", "TBD"),
        # Words before a name that are not another wording of it keep the field's text.
        ("", "Holding structure Parent company N/A", "Holding structure Parent company N/A"),
        # Words after a name that only share some of its words stay in the answer.
        (
            "",
            "Issuer-related risks Risks related to the issuer include insolvency",
            "Issuer-related risks: Risks related to the issuer include insolvency",
        ),
        # A label of its own that is not a field name stays as written.
        ("Name of the project", "Meadow", "Name of the project: Meadow"),
        # Text that goes on from a field name, or holds none, keeps its wording.
        ("", "Name of the token N/A", "Name of the token N/A"),
        ("", "Parent company's business activity N/A", "Parent company's business activity N/A"),
        ("", "Namely issued in 2026", "Namely issued in 2026"),
        ("", "Example Issuer AG", "Example Issuer AG"),
        # A field that holds only its label has no answer.
        ("", "Legal form", None),
    ],
)
def test_template_field_name_is_split_off_a_field(label: str, content: str, line: str | None):
    sections, _ = sections_from_numbered_fields([NumberedField("A.4", label, content)], WhitepaperType.OTHER)
    assert sections.get("offeror") == line


def test_fields_whose_label_is_not_recognised_are_named(tmp_path: Path):
    # Labels share the answer cell, and three of them are not field names of the template.
    rows = _labelled(_TABLE_2_ANSWERS, WhitepaperType.OTHER)
    rows += [("C.1", "Platform", "Example Exchange S.A. (fictional)"), ("C.2", "Name of the token", "N/A")]
    rows += [("E.1", "Kind of offer", "Admission to trading")]
    whitepaper = _load(tmp_path, "merged", _label_in_answer_cell(rows), WhitepaperType.OTHER)

    notes = whitepaper.metadata["extraction_notes"]
    assert MERGED_LABELS_NOTE not in notes
    assert notes[0].startswith("Fields C.1, C.2, E.1 have no separate label")
    # "N/A" behind a label the template does not have still reads as answered, which the note warns about.
    assert "Name of the token N/A" in whitepaper.section("trading_platform_operator").split("\n")


def test_note_on_a_single_field_left_without_a_label():
    fields = [
        NumberedField("A.1", "", "Name N/A"),
        NumberedField("A.2", "", "Legal form N/A"),
        NumberedField("B.2", "", "Name Example Issuer AG"),
        NumberedField("B.3", "", "Legal form GmbH"),
        NumberedField("C.1", "", "Platform Example Exchange S.A."),
    ]
    _, notes = sections_from_numbered_fields(fields, WhitepaperType.OTHER)
    assert notes[0] == (
        "Field C.1 has no separate label, and its text does not start with a field name of the template, "
        'so a label can run into the answer: such a field answered only "N/A" or "TBD" reads as answered. '
        "Check the field against the white paper."
    )


def test_note_lists_ten_fields_and_counts_the_rest():
    recognised = [NumberedField(f"A.{number}", "", "Name N/A") for number in range(1, 41)]
    unrecognised = [NumberedField(f"D.{number}", "", f"Platform {number}") for number in range(1, 13)]
    _, notes = sections_from_numbered_fields(recognised + unrecognised, WhitepaperType.OTHER)
    listed = ", ".join(f"D.{number}" for number in range(1, 11))
    assert notes[0].startswith(f"Fields {listed} and 2 more have no separate label, and their text does not")


def test_heading_structured_xhtml_keeps_the_heading_loader():
    whitepaper = load_whitepaper(ROOT / "examples" / "sample-draft.xhtml")
    assert whitepaper.type is WhitepaperType.EMT
    assert whitepaper.metadata["extraction_notes"] == ()


@pytest.mark.skipif(not STUDY_CACHE.is_dir(), reason="local study cache not present")
def test_public_title_ii_documents_yield_their_lettered_parts():
    numbered = 0
    for path in sorted(STUDY_CACHE.glob("*.*html")):
        if not is_numbered_layout(extract_numbered_fields(path)):
            continue
        numbered += 1
        with pytest.raises(SystemExit):
            load_whitepaper(path)
        report = lint_whitepaper(load_whitepaper(path, WhitepaperType.OTHER))
        missing = {finding.rule.rule_id for finding in report.missing}
        assert not missing & {f"ANNEX_I.{part}" for part in "ABCDEFGHI"}, path.name
    assert numbered >= 12
