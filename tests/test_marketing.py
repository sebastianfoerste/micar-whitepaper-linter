"""Marketing communications under Art. 7 MiCAR (rules/marketing.py, marketing_checks.py, ADR 0009)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from micar_linter import citations
from micar_linter.ci_outputs import DRAFT_ECHO_RULES, render_sarif, render_summary
from micar_linter.cli import main
from micar_linter.linter import lint_marketing, lint_whitepaper
from micar_linter.report import render_json, render_text
from micar_linter.rules import MARKETING_RULESETS, RULESETS
from micar_linter.rules.marketing import MARKETING_RULES, MARKETING_SECTION
from micar_linter.whitepaper import (
    Whitepaper,
    WhitepaperType,
    load_marketing_communication,
    load_whitepaper,
)

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
WHITE_PAPER = EXAMPLES / "other-crypto-asset.json"
STATEMENT_EN = (
    "This crypto-asset marketing communication has not been reviewed or approved by any competent authority in "
    "any Member State of the European Union. The offeror of the crypto-asset is solely responsible for the "
    "content of this crypto-asset marketing communication."
)
STATEMENT_DE = (
    "Diese Kryptowert-Marketingmitteilung wurde von keiner zuständigen Behörde eines Mitgliedstaats der "
    "Europäischen Union geprüft oder genehmigt. Der Anbieter des Kryptowerts trägt die alleinige Verantwortung "
    "für den Inhalt dieser Kryptowert-Marketingmitteilung."
)
CONTACT_EN = (
    "A crypto-asset white paper has been published at https://meshcompute.example/white-paper. "
    "Telephone +49 30 0000 0000, e-mail contact@meshcompute.example."
)


def communication(
    text: str, *, title: str = "Synthetic draft", reference: str | None = None, language: str | None = None
) -> Whitepaper:
    metadata: dict = {"document_kind": "marketing_communication"}
    if reference is not None:
        metadata["reference_text"] = reference
    if language:
        metadata["language"] = language
    return Whitepaper(
        title=title, type=WhitepaperType.OTHER, sections={MARKETING_SECTION: text}, metadata=metadata
    )


def statuses(document: Whitepaper) -> dict[str, tuple[str, tuple[str, ...]]]:
    return {f.rule.rule_id: (f.status, f.issues) for f in lint_marketing(document).findings}


def test_rule_set_follows_article_7_1_and_keeps_its_own_namespace():
    rules = MARKETING_RULESETS[WhitepaperType.OTHER]
    assert [r.rule_id for r in rules] == [
        "MARKETING.IDENTIFIABLE",
        "MARKETING.MISLEADING_CLAIMS",
        "MARKETING.CONSISTENCY",
        "MARKETING.WHITE_PAPER_AND_CONTACT",
        "MARKETING.NOT_REVIEWED_STATEMENT",
    ]
    white_paper_ids = {r.rule_id for ruleset in RULESETS.values() for r in ruleset}
    assert not white_paper_ids & {r.rule_id for r in rules}
    for rule, letter in zip(rules, "abcde", strict=True):
        assert citations.to_english(rule.citation) == f"Art. 7(1), point ({letter}) MiCAR"
        assert citations.source_urls(rule.citation) == ["https://eur-lex.europa.eu/eli/reg/2023/1114/oj/eng"]
        assert rule.section == MARKETING_SECTION
    severities = {r.rule_id: r.severity.label for r in rules}
    assert (
        severities["MARKETING.WHITE_PAPER_AND_CONTACT"]
        == severities["MARKETING.NOT_REVIEWED_STATEMENT"]
        == "BLOCKER"
    )


def test_claim_patterns_compile_with_one_named_group_each():
    for rule in MARKETING_RULES:
        for pattern in (*rule.prohibited_patterns, *rule.prohibited_patterns_de):
            assert len(re.compile(pattern, re.IGNORECASE).groupindex) == 1


def test_consistent_example_passes_every_rule_and_strict_exits_zero(capsys):
    assert (
        main(
            [
                str(EXAMPLES / "marketing-other.md"),
                "--marketing",
                "--whitepaper",
                str(WHITE_PAPER),
                "--strict",
            ]
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "Pass: 5  |  Review: 0  |  Missing: 0  |  Blockers: 0" in out
    assert "Document: marketing communication" in out
    assert "All checked items present. Lawyer review still required." in out
    assert out.rstrip().endswith("This tool is not legal advice.")


def test_incomplete_example_keeps_blockers_open(capsys):
    assert (
        main(
            [
                str(EXAMPLES / "marketing-incomplete.md"),
                "--marketing",
                "--whitepaper",
                str(WHITE_PAPER),
                "--strict",
            ]
        )
        == 1
    )
    out = capsys.readouterr().out
    assert "Blockers: 2" in out
    assert "should not be disseminated" in out


@pytest.mark.parametrize(
    "person",
    ["offeror", "person seeking admission to trading", "operator of the trading platform"],
)
def test_statement_accepts_each_person_of_the_second_subparagraph(person):
    text = STATEMENT_EN.replace("offeror", person)
    status, issues = statuses(communication(text))["MARKETING.NOT_REVIEWED_STATEMENT"]
    assert (status, issues) == ("pass", ())


def test_statement_names_another_person_for_review():
    text = STATEMENT_EN.replace("The offeror", "Example Promotions Ltd as distributor")
    status, issues = statuses(communication(text))["MARKETING.NOT_REVIEWED_STATEMENT"]
    assert status == "review"
    assert "directly before" in issues[0]


def test_statement_with_white_paper_wording_goes_to_review():
    text = (
        "This crypto-asset white paper has not been approved by any competent authority in any Member State of "
        "the European Union. The offeror of the crypto-asset is solely responsible for the content of this "
        "crypto-asset white paper."
    )
    status, issues = statuses(communication(text))["MARKETING.NOT_REVIEWED_STATEMENT"]
    assert status == "review"
    assert len(issues) == 2


def test_german_statement_passes_in_a_german_draft():
    text = (
        "Werbung für den synthetischen Token. Das ist ein Beispiel und die Angaben sind erfunden. "
        + STATEMENT_DE
    )
    found = statuses(communication(text))
    assert found["MARKETING.NOT_REVIEWED_STATEMENT"] == ("pass", ())
    assert found["MARKETING.IDENTIFIABLE"] == ("pass", ())


def test_statement_split_by_line_ends_and_soft_hyphens_still_matches():
    text = STATEMENT_EN.replace("competent authority", "compe­tent\nauthority").replace(
        " European", "\n European"
    )
    assert statuses(communication(text))["MARKETING.NOT_REVIEWED_STATEMENT"][0] == "pass"


@pytest.mark.parametrize("text", ["", "   ", "TBD", "[●]"])
def test_empty_or_placeholder_communication_is_missing_for_every_rule(text):
    found = statuses(communication(text, reference=""))
    assert {status for status, _ in found.values()} == {"missing"}


def test_white_paper_and_contact_names_each_absent_item():
    status, issues = statuses(communication("Marketing communication. " + STATEMENT_EN))[
        "MARKETING.WHITE_PAPER_AND_CONTACT"
    ]
    assert status == "review"
    for item in ("white paper has been published", "website address", "telephone number", "e-mail address"):
        assert item in issues[0]
    status, issues = statuses(communication(CONTACT_EN))["MARKETING.WHITE_PAPER_AND_CONTACT"]
    assert (status, issues) == ("pass", ())


def test_white_paper_and_contact_reads_german_statement():
    text = (
        "Werbung. Das Kryptowerte-Whitepaper wurde auf https://meshcompute.example veröffentlicht. "
        "Telefon +49 30 0000 0000, E-Mail contact@meshcompute.example. Der Token ist ein Beispiel."
    )
    assert statuses(communication(text))["MARKETING.WHITE_PAPER_AND_CONTACT"] == ("pass", ())


def test_identifiable_needs_a_label_in_the_title_or_the_opening():
    body = " ".join(["Synthetic sentence about a fictional token offer."] * 10)
    assert statuses(communication(body))["MARKETING.IDENTIFIABLE"][0] == "review"
    assert (
        statuses(communication(body, title="Advertisement: token offer"))["MARKETING.IDENTIFIABLE"][0]
        == "pass"
    )
    assert statuses(communication("Marketing communication. " + body))["MARKETING.IDENTIFIABLE"][0] == "pass"
    # A label after the opening words, such as the statement at the end, does not make the text identifiable.
    assert statuses(communication(body + " " + STATEMENT_EN))["MARKETING.IDENTIFIABLE"][0] == "review"


@pytest.mark.parametrize(
    ("text", "name"),
    [
        ("Enjoy guaranteed returns on every token.", "guaranteed return"),
        ("A risk-free way to take part.", "no risk"),
        ("The price will rise after the listing.", "rising price"),
        ("The token was approved by BaFin.", "approval claim"),
        ("Garantierte Renditen für alle Inhaber.", "garantierte rendite"),
        ("Risikolos dabei sein.", "kein risiko"),
        ("Der Kurs wird steigen.", "steigender kurs"),
        ("Von der BaFin genehmigt.", "behauptete genehmigung"),
    ],
)
def test_listed_claims_go_to_review_by_name(text, name):
    status, issues = statuses(communication(text))["MARKETING.MISLEADING_CLAIMS"]
    assert status == "review"
    assert name in issues[0]
    # The finding names the claim, never the draft's wording.
    assert text not in issues[0]


@pytest.mark.parametrize(
    "text",
    [
        "There are no guaranteed returns. Returns are not guaranteed.",
        "The token is not risk-free. Read the risk warning.",
        "The price may rise or fall.",
        STATEMENT_EN,
        "Es gibt keine garantierten Renditen; der Token ist nicht risikofrei. " + STATEMENT_DE,
    ],
)
def test_negated_claims_and_the_statement_itself_pass(text):
    assert statuses(communication(text))["MARKETING.MISLEADING_CLAIMS"] == ("pass", ())


def test_consistency_does_not_run_without_a_white_paper():
    report = lint_marketing(communication(CONTACT_EN))
    assert [r.rule_id for r in report.not_run] == ["MARKETING.CONSISTENCY"]
    assert "MARKETING.CONSISTENCY" not in {f.rule.rule_id for f in report.findings}
    assert report.warnings[-1].startswith("No white paper was given (--whitepaper)")
    german = lint_marketing(communication("Werbung. " + STATEMENT_DE))
    assert german.warnings[-1].startswith("Es wurde kein Kryptowerte-Whitepaper angegeben")


def test_consistency_passes_when_every_value_is_in_the_white_paper():
    reference = (
        "Offeror LEI 9999SYNTHMESHCMP0151, DTI SYNTH0001. Contact contact@meshcompute.example or "
        "+49 30 0000 0000. Notified on 2026-03-02. Price EUR 1,000,000 in total; bonus 5 %."
    )
    text = (
        "LEI 9999SYNTHMESHCMP0151 and token SYNTH0001. See https://www.meshcompute.example/offer, write to "
        "contact@meshcompute.example or call 0049 30 0000 0000. Notified 02.03.2026 (2 March 2026). "
        "EUR 1 million offered, 5% bonus."
    )
    assert statuses(communication(text, reference=reference))["MARKETING.CONSISTENCY"] == ("pass", ())


def test_consistency_lists_values_the_white_paper_lacks():
    reference = (
        "Offeror LEI 9999SYNTHMESHCMP0151. Contact contact@meshcompute.example. Notified on 2026-03-02."
    )
    text = (
        "Bonus 20 % until 2026-04-01. Price USD 0.10 per token. Visit https://other-launch.example. "
        "Call +44 20 0000 0000 or write to sales@other-launch.example. Token SYNTH0002."
    )
    status, issues = statuses(communication(text, reference=reference))["MARKETING.CONSISTENCY"]
    assert status == "review"
    for value in (
        "percentage 20 %",
        "date 2026-04-01",
        "amount USD 0.1",
        "web address other-launch.example",
        "telephone number +442000000000",
        "e-mail address sales@other-launch.example",
        "token identifier SYNTH0002",
    ):
        assert value in issues[0]


def test_consistency_counts_values_beyond_ten():
    text = " ".join(f"{n} %" for n in range(11, 25))
    status, issues = statuses(communication(text, reference="No figures."))["MARKETING.CONSISTENCY"]
    assert status == "review"
    assert "4 more" in issues[0]


def test_json_communication_loads_text_and_ignores_reserved_keys(tmp_path: Path):
    source = tmp_path / "ad.json"
    source.write_text(
        json.dumps(
            {"title": "Synthetic ad", "text": ["Advertisement.", STATEMENT_EN], "reference_text": "x"}
        ),
        encoding="utf-8",
    )
    loaded = load_marketing_communication(source)
    assert loaded.title == "Synthetic ad"
    assert "reference_text" not in loaded.metadata
    assert STATEMENT_EN in loaded.section(MARKETING_SECTION)
    source.write_text(json.dumps({"type": "emt", "text": "x"}), encoding="utf-8")
    with pytest.raises(SystemExit, match="'type' must be 'other'"):
        load_marketing_communication(source)


def test_html_statement_that_a_reader_cannot_see_does_not_count(tmp_path: Path):
    source = tmp_path / "ad.html"
    source.write_text(
        "<html><body><h1>Advertisement</h1><p>Synthetic token offer.</p>"
        f'<p style="display:none">{STATEMENT_EN}</p></body></html>',
        encoding="utf-8",
    )
    found = statuses(load_marketing_communication(source))
    assert found["MARKETING.NOT_REVIEWED_STATEMENT"][0] == "review"
    source.write_text(
        f"<html><body><h1>Advertisement</h1><p>{STATEMENT_EN}</p></body></html>", encoding="utf-8"
    )
    assert statuses(load_marketing_communication(source))["MARKETING.NOT_REVIEWED_STATEMENT"][0] == "pass"


def test_reference_text_includes_every_section_of_the_white_paper():
    reference = load_whitepaper(WHITE_PAPER)
    loaded = load_marketing_communication(EXAMPLES / "marketing-other.md", reference)
    assert "9999SYNTHMESHCMP0151" in loaded.metadata["reference_text"]
    assert "contact@meshcompute.example" in loaded.metadata["reference_text"]


def test_json_report_names_the_document_kind_only_for_marketing():
    report = lint_marketing(
        load_marketing_communication(EXAMPLES / "marketing-other.md", load_whitepaper(WHITE_PAPER))
    )
    assert json.loads(render_json(report))["document_kind"] == "marketing_communication"
    white_paper = json.loads(render_json(lint_whitepaper(load_whitepaper(WHITE_PAPER))))
    assert "document_kind" not in white_paper
    assert "Whitepaper type: OTHER" in render_text(lint_whitepaper(load_whitepaper(WHITE_PAPER)))


@pytest.mark.parametrize(
    ("extra", "message"),
    [
        (["--type", "art"], "Art. 29 and Art. 53 MiCAR are not covered"),
        (["--review-table-output", "t.json"], "does not support --review-table-output"),
        (["--coverage"], "does not support --coverage"),
    ],
)
def test_cli_refuses_what_marketing_mode_does_not_cover(extra, message, capsys):
    assert main([str(EXAMPLES / "marketing-other.md"), "--marketing", *extra]) == 2
    assert message in capsys.readouterr().err


def test_cli_needs_marketing_for_whitepaper_and_one_file(tmp_path: Path, capsys):
    assert main([str(WHITE_PAPER), "--whitepaper", str(WHITE_PAPER)]) == 2
    assert "needs --marketing" in capsys.readouterr().err
    assert main([str(tmp_path), "--marketing"]) == 2
    assert "one marketing communication file" in capsys.readouterr().err


def test_cli_refuses_an_art_white_paper_as_reference(capsys):
    args = [
        str(EXAMPLES / "marketing-other.md"),
        "--marketing",
        "--whitepaper",
        str(EXAMPLES / "art-stablecoin.json"),
    ]
    assert main(args) == 2
    assert "white paper for an ART" in capsys.readouterr().err


def test_cli_json_and_ci_outputs_never_echo_draft_values(tmp_path: Path, capsys):
    marker = "zz-marker-launch.example"
    source = tmp_path / "ad.md"
    source.write_text(
        f"Advertisement. Visit https://{marker} for a 33 % bonus. {STATEMENT_EN}", encoding="utf-8"
    )
    sarif, summary = tmp_path / "out.sarif", tmp_path / "summary.md"
    args = [str(source), "--marketing", "--whitepaper", str(WHITE_PAPER), "--json"]
    assert main([*args, "--sarif-output", str(sarif), "--summary-output", str(summary)]) == 0
    report = json.loads(capsys.readouterr().out)
    consistency = next(f for f in report["findings"] if f["rule_id"] == "MARKETING.CONSISTENCY")
    assert marker in consistency["issues"][0]
    assert "MARKETING.CONSISTENCY" in DRAFT_ECHO_RULES
    for path in (sarif, summary):
        text = path.read_text(encoding="utf-8")
        assert marker not in text
        assert "33 %" not in text
    log = json.loads(sarif.read_text(encoding="utf-8"))
    assert log["runs"][0]["properties"]["document_kind"] == "marketing_communication"
    assert summary.read_text(encoding="utf-8").startswith("## MiCAR marketing communication lint:")


def test_summary_states_that_consistency_did_not_run_without_quoting_the_draft(tmp_path: Path):
    source = tmp_path / "ad.md"
    source.write_text("Advertisement. " + CONTACT_EN + " " + STATEMENT_EN, encoding="utf-8")
    report = lint_marketing(load_marketing_communication(source))
    summary = render_summary(report, source)
    assert "MARKETING.CONSISTENCY did not run" in summary
    assert "No open findings. Lawyer review still applies." in summary
    assert "field-level checks" not in summary
    assert json.loads(render_sarif(report, source))["runs"][0]["properties"]["not_run"] == [
        "MARKETING.CONSISTENCY"
    ]
