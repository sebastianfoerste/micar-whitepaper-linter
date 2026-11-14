from __future__ import annotations

import json
import re

import pytest

from micar_linter import citations
from micar_linter.rules import RULESETS, annex_i, annex_ii, annex_iii, common, templates


def _all_citations() -> set[str]:
    found = set()
    for module in (annex_i, annex_ii, annex_iii, common, templates):
        for value in vars(module).values():
            if isinstance(value, dict):
                value = tuple(value.values())
            if isinstance(value, (list, tuple)):
                found.update(r.citation for r in value if hasattr(r, "citation"))
    # The rule sets also hold the point rules and the per-regime rules (rules/points.py, CLASSIFICATION_RULES).
    found.update(rule.citation for rules in RULESETS.values() for rule in rules)
    return found


@pytest.mark.parametrize(
    ("german", "english"),
    [
        ("Art. 6 Abs. 7, Art. 19 Abs. 6, Art. 51 Abs. 6 MiCAR", "Art. 6(7), Art. 19(6), Art. 51(6) MiCAR"),
        ("Anhang I Teil A MiCAR", "Annex I, Part A MiCAR"),
        (
            "Anhang II Teil C Nr. 8, Teil D Nr. 9, 14, 15 und 16, Teil G Nr. 3 i.V.m. Art. 39 Abs. 2 und 3, Art. 46 MiCAR",
            "Annex II, Part C, point 8, Part D, points 9, 14, 15 and 16, Part G, point 3 "
            "in conjunction with Art. 39(2) and (3), Art. 46 MiCAR",
        ),
        (
            "Anhang II Teil G i.V.m. Art. 36 Abs. 7, 9, 11 und 12 MiCAR",
            "Annex II, Part G in conjunction with Art. 36(7), (9), (11) and (12) MiCAR",
        ),
        (
            "Anhang II Teil G i.V.m. Art. 35 Abs. 4, Art. 36 Abs. 4 Buchst. d, Art. 45 Abs. 3 und Art. 45 Abs. 7 Buchst. b MiCAR",
            "Annex II, Part G in conjunction with Art. 35(4), Art. 36(4), point (d), Art. 45(3) "
            "and Art. 45(7), point (b) MiCAR",
        ),
        (
            "Art. 19 Abs. 1 UAbs. 1 Buchst. h MiCAR i.V.m. Art. 4 VO (EU) 2025/422",
            "Art. 19(1), first subparagraph, point (h) MiCAR in conjunction with Art. 4 Regulation (EU) 2025/422",
        ),
        (
            "Art. 54 MiCAR i.V.m. Art. 7 EMD2 (Richtlinie 2009/110/EG)",
            "Art. 54 MiCAR in conjunction with Art. 7 EMD2 (Directive 2009/110/EC)",
        ),
        ("Anhang II Teil D Nr. 10 Buchst. c MiCAR", "Annex II, Part D, point 10(c) MiCAR"),
        (
            "Anhang Tabelle 2 Felder 02 bis 07, Tabelle 3 Felder I.02 bis I.04 und I.06, Tabelle 4 Felder I.02 bis "
            "I.05 und I.07 VO (EU) 2024/2984",
            "Annex, Table 2, fields 02 to 07, Table 3, fields I.02 to I.04 and I.06, Table 4, fields I.02 to I.05 "
            "and I.07 Regulation (EU) 2024/2984",
        ),
        (
            "Anhang Tabelle 2 Feld 01, Tabelle 3 Feld I.01, Tabelle 4 Feld I.01 VO (EU) 2024/2984",
            "Annex, Table 2, field 01, Table 3, field I.01, Table 4, field I.01 Regulation (EU) 2024/2984",
        ),
        ("Anhang Tabellen 1 bis 4 VO (EU) 2024/2984", "Annex, Tables 1 to 4 Regulation (EU) 2024/2984"),
        (
            "Art. 4 Abs. 1 und 2 i.V.m. Anhang Tabellen 2 und 3 VO (EU) 2025/422",
            "Art. 4(1) and (2) in conjunction with Annex, Tables 2 and 3 Regulation (EU) 2025/422",
        ),
        (
            "Art. 2 und 3 i.V.m. Anhang VO (EU) 2025/421",
            "Art. 2 and 3 in conjunction with Annex to Regulation (EU) 2025/421",
        ),
    ],
)
def test_known_conversions(german: str, english: str) -> None:
    assert citations.to_english(german) == english


def test_delegated_regulation_2025_421_links_to_its_own_act() -> None:
    citation = _rule_citation("RTS.CLASSIFICATION_DATA")
    assert citation in _all_citations()
    url = "https://eur-lex.europa.eu/eli/reg_del/2025/421/oj/eng"
    assert citations.ACT_URLS["VO (EU) 2025/421"] == url
    assert citations.source_urls(citation) == [url]
    # "Anhang VO" is the Annex to the act, not Annex V.
    assert "Annex V" not in citations.to_english(citation)


def _rule_citation(rule_id: str) -> str:
    for rules in RULESETS.values():
        for rule in rules:
            if rule.rule_id == rule_id:
                return rule.citation
    for module in (annex_i, annex_ii, annex_iii, common, templates):
        for value in vars(module).values():
            if isinstance(value, (list, tuple)):
                for rule in value:
                    if getattr(rule, "rule_id", None) == rule_id:
                        return rule.citation
    raise AssertionError(f"no rule {rule_id}")


@pytest.mark.parametrize(
    ("rule_id", "english"),
    [
        ("ANNEX_I.NOT_APPROVED_STATEMENT", "Art. 6(3) MiCAR"),
        ("ANNEX_III.NOT_APPROVED_STATEMENT", "Art. 51(3) MiCAR"),
        ("ANNEX_II.G.VALUATION_AUDIT", "Annex II, Part D, point 10 MiCAR"),
        (
            "ANNEX_II.I",
            "Annex II, Part D, points 9, 14, 15 and 16, Part G, point 3 in conjunction with Art. 39, "
            "Art. 46(1), third subparagraph, point (c) and Art. 46(4) MiCAR",
        ),
    ],
)
def test_corrected_rule_citations_render_in_english(rule_id: str, english: str) -> None:
    assert citations.to_english(_rule_citation(rule_id)) == english


@pytest.mark.parametrize("citation", sorted(_all_citations()))
def test_every_rule_citation_converts_cleanly(citation: str) -> None:
    english = citations.to_english(citation)
    # No German drafting terms left, no doubled punctuation.
    for term in ("Abs.", "UAbs.", "Buchst.", "Anhang", "Teil ", "Nr.", "i.V.m.", " VO ", " und ", "Tabelle", "Feld", " bis "):
        assert term not in english, (term, english)
    assert ",," not in english and ", ," not in english
    # Every article and annex number survives the conversion.
    # (UAbs. 1 becomes "first subparagraph", so its digit is spelled out.)
    expected = re.findall(r"\d+", re.sub(r"UAbs\. \d", "", citation))
    assert expected == re.findall(r"\d+", english)


@pytest.mark.parametrize("citation", sorted(_all_citations()))
def test_every_rule_citation_links_to_its_acts(citation: str) -> None:
    urls = citations.source_urls(citation)
    assert urls, citation
    assert all(u.startswith("https://eur-lex.europa.eu/eli/") for u in urls)
    if "MiCAR" in citation:
        assert citations.ACT_URLS["MiCAR"] in urls


def test_text_report_styles_and_json_fields(capsys: pytest.CaptureFixture[str]) -> None:
    from micar_linter.cli import main

    main(["examples/incomplete.json"])
    text = capsys.readouterr().out
    assert "Cite:  Art. 6(7)" in text and "Text:  https://eur-lex.europa.eu/" in text
    # The blocker footer follows the style too, not only the per-finding citations.
    assert "(Art. 8(1), Art. 16(2), second subparagraph, Art. 17(1), point (a)," in text
    assert "Abs." not in text
    main(["--citation-style", "de", "examples/incomplete.json"])
    text = capsys.readouterr().out
    assert "Art. 6 Abs. 7" in text
    assert "(Art. 8 Abs. 1, Art. 16 Abs. 2 UAbs. 2, Art. 17 Abs. 1 Buchst. a," in text
    main(["--json", "examples/incomplete.json"])
    finding = json.loads(capsys.readouterr().out)["findings"][0]
    assert finding["citation"].startswith("Art. 6 Abs. 7")
    assert finding["citation_en"].startswith("Art. 6(7)")
    assert finding["sources"] == [citations.ACT_URLS["MiCAR"]]
