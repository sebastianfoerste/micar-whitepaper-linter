import re
from pathlib import Path

import pytest

from micar_linter.linter import lint_whitepaper
from micar_linter.rules import RULESETS
from micar_linter.rules.base import Finding, Rule
from micar_linter.whitepaper import Whitepaper, WhitepaperType

# The two warnings of Art. 51(4) MiCAR in one sentence, in the Regulation's English and German wording.
EMT_WARNING = (
    "The e-money token is not covered by the investor compensation schemes under Directive 97/9/EC "
    "or by the deposit guarantee schemes under Directive 2014/49/EU."
)
EMT_WARNING_DE = (
    "Der E-Geld-Token fällt nicht unter die Systeme für die Entschädigung der Anleger gemäß der "
    "Richtlinie 97/9/EG und nicht unter die Einlagensicherungssysteme gemäß der Richtlinie 2014/49/EU."
)
LOSS_OF_VALUE_WARNING = (
    "The token may lose its value in part or in full, may not always be transferable and may not be "
    "liquid. The risk of loss rests with the holder, who should not commit funds that cannot be lost."
)


def test_rulesets_compile_patterns():
    for _wp_type, rules in RULESETS.items():
        assert len(rules) > 0
        for rule in rules:
            assert isinstance(rule, Rule)
            assert rule.rule_id
            assert rule.citation
            assert rule.section

            for pattern in rule.required_patterns:
                try:
                    re.compile(pattern)
                except re.error as exc:
                    pytest.fail(f"Invalid required_pattern '{pattern}' in rule {rule.rule_id}: {exc}")

            for pattern in rule.prohibited_patterns:
                try:
                    re.compile(pattern)
                except re.error as exc:
                    pytest.fail(f"Invalid prohibited_pattern '{pattern}' in rule {rule.rule_id}: {exc}")


def test_every_rule_carries_a_pinpoint_citation():
    for _wp_type, rules in RULESETS.items():
        for rule in rules:
            assert rule.citation.strip(), rule.rule_id
            assert any(token in rule.citation for token in ("Art.", "Anhang"))


def _risk_warning(whitepaper_type: WhitepaperType, text: str, **metadata: str) -> Finding:
    whitepaper = Whitepaper(
        title="Synthetic draft", type=whitepaper_type, sections={"risk_warning": text}, metadata=metadata
    )
    return next(f for f in lint_whitepaper(whitepaper).findings if f.rule.rule_id == "COMMON.RISK_WARNING")


def test_emt_risk_warning_checks_the_two_warnings_of_article_51_4():
    assert _risk_warning(WhitepaperType.EMT, EMT_WARNING).status == "pass"
    assert _risk_warning(WhitepaperType.EMT, EMT_WARNING_DE, language="de").status == "pass"
    # The loss-of-value statement of Art. 6(5) and 19(4) does not stand in for the two warnings.
    finding = _risk_warning(WhitepaperType.EMT, LOSS_OF_VALUE_WARNING)
    assert finding.issues == ("Missing review terms: investor compensation, deposit guarantee.",)


def test_other_regimes_ask_for_more_than_the_emt_warnings():
    for whitepaper_type in (WhitepaperType.OTHER, WhitepaperType.ART):
        finding = _risk_warning(whitepaper_type, EMT_WARNING)
        assert finding.status == "review"
        assert any(issue.startswith("Missing review terms") for issue in finding.issues)


def test_project_metadata_points_to_current_repository():
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert "github.com/sebastianfoerste/micar-whitepaper-linter" in pyproject
    assert "github.com/sebastianforste/micar-whitepaper-linter" not in pyproject
