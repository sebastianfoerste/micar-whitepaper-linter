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
            "Anhang II Teil D Nr. 9, 15 und 16, Teil G Nr. 3 i.V.m. Art. 39 MiCAR",
            "Annex II, Part D, points 9, 15 and 16, Part G, point 3 in conjunction with Art. 39 MiCAR",
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
