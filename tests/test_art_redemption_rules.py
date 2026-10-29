"""ART redemption and valuation rules follow Art. 39 MiCAR and Annex II Part D.

Redemption "at par" is the e-money token rule (Art. 49(4) MiCAR). An ART issuer
redeems by paying funds, other than electronic money, equivalent to the market value of
the referenced assets or by delivering those assets (Art. 39(2) MiCAR). Art. 36(3) is
the operational segregation of the reserve, not its valuation. The terms of
`ANNEX_II.D`, `ANNEX_II.I` and `ANNEX_II.G.VALUATION_AUDIT` are tested in
`tests/test_rules.py`, `tests/test_rule_items.py` and `tests/test_term_patterns.py`.
"""

import json
from pathlib import Path

from micar_linter.linter import lint_whitepaper
from micar_linter.rules import RULESETS
from micar_linter.whitepaper import WhitepaperType, load_whitepaper

ROOT = Path(__file__).resolve().parents[1]


def _rule(rule_id: str):
    for rules in RULESETS.values():
        for rule in rules:
            if rule.rule_id == rule_id:
                return rule
    raise AssertionError(f"{rule_id} not found")


def test_no_art_rule_requires_redemption_at_par():
    for rule in RULESETS[WhitepaperType.ART]:
        terms = " | ".join((*rule.required_terms, *rule.required_terms_de)).lower()
        assert "at par" not in terms and "zu par" not in terms, rule.rule_id
        assert "at par" not in rule.label.lower(), rule.rule_id


def test_emt_rights_rule_keeps_redemption_at_par():
    rule = _rule("ANNEX_III.D")
    assert "at par" in rule.required_terms
    assert "Art. 49 Abs. 4" in rule.citation


def test_no_art_rule_cites_operational_segregation_for_valuation():
    # Regression: Art. 36(3) MiCAR (operational segregation) was cited for valuation and audit.
    rule = _rule("ANNEX_II.G.VALUATION_AUDIT")
    assert "Abs. 3" not in rule.citation and "36(3)" not in rule.label


def test_art_example_passes_the_redemption_rules():
    report = lint_whitepaper(load_whitepaper(ROOT / "examples" / "art-stablecoin.json"))
    indexed = {f.rule.rule_id: f for f in report.findings}
    for rule_id in ("ANNEX_II.D", "ANNEX_II.I", "ANNEX_II.G.VALUATION_AUDIT"):
        assert indexed[rule_id].status == "pass", (rule_id, indexed[rule_id].issues)


def test_starter_template_cites_the_art_provisions_for_its_art_type():
    # Regression: the "art" starter cited Title II provisions (Art. 6, Art. 8(1)) and
    # asked for "the redemption right at par under Art. 39".
    starter = json.loads(
        (ROOT / "templates" / "whitepaper-starter" / "whitepaper.json").read_text(encoding="utf-8")
    )
    assert starter["type"] == "art"
    text = " ".join(starter["sections"].values())
    assert "at par" not in text
    assert "Art. 6 Abs." not in text and "Art. 8 Abs." not in text
    assert "market value of the referenced assets" in starter["sections"]["redemption"]
