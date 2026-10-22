from __future__ import annotations

import json
import re

import pytest

from micar_linter import citations
from micar_linter.rules import annex_i, annex_ii, annex_iii, common


def _all_citations() -> set[str]:
    found = set()
    for module in (annex_i, annex_ii, annex_iii, common):
        for value in vars(module).values():
            if isinstance(value, (list, tuple)):
                found.update(r.citation for r in value if hasattr(r, "citation"))
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
    ],
)
def test_known_conversions(german: str, english: str) -> None:
    assert citations.to_english(german) == english


def _rule_citation(rule_id: str) -> str:
    for module in (annex_i, annex_ii, annex_iii, common):
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
        (
            "ANNEX_II.G.VALUATION_AUDIT",
            "Annex II, Part G in conjunction with Art. 36(7), (9), (11) and (12) MiCAR",
        ),
        (
            "ANNEX_II.I",
            "Annex II, Part C, point 8, Part D, points 9, 14, 15 and 16, Part G, point 3 "
            "in conjunction with Art. 39(2) and (3), Art. 46 MiCAR",
        ),
    ],
)
def test_corrected_rule_citations_render_in_english(rule_id: str, english: str) -> None:
    assert citations.to_english(_rule_citation(rule_id)) == english


@pytest.mark.parametrize("citation", sorted(_all_citations()))
def test_every_rule_citation_converts_cleanly(citation: str) -> None:
    english = citations.to_english(citation)
    # No German drafting terms left, no doubled punctuation.
    for term in ("Abs.", "UAbs.", "Buchst.", "Anhang", "Teil ", "Nr.", "i.V.m.", " VO ", " und "):
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
    main(["--citation-style", "de", "examples/incomplete.json"])
    assert "Art. 6 Abs. 7" in capsys.readouterr().out
    main(["--json", "examples/incomplete.json"])
    finding = json.loads(capsys.readouterr().out)["findings"][0]
    assert finding["citation"].startswith("Art. 6 Abs. 7")
    assert finding["citation_en"].startswith("Art. 6(7)")
    assert finding["sources"] == [citations.ACT_URLS["MiCAR"]]
