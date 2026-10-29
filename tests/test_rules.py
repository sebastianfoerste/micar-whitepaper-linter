import re
from pathlib import Path

import pytest

from micar_linter.linter import Linter, lint_whitepaper
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
# The statements of Art. 6(5)(a) to (c), (e) and (f) MiCAR in the Regulation's English wording, and in
# German in one sentence.
OTHER_WARNING = (
    "The crypto-asset may lose its value in part or in full. The crypto-asset may not always be "
    "transferable. The crypto-asset may not be liquid. The crypto-asset is not covered by the investor "
    "compensation schemes under Directive 97/9/EC. The crypto-asset is not covered by the deposit "
    "guarantee schemes under Directive 2014/49/EU."
)
OTHER_WARNING_DE = (
    "Der Kryptowert kann seinen Wert ganz oder teilweise verlieren, ist möglicherweise nicht immer "
    "übertragbar, möglicherweise nicht liquide und fällt weder unter Anlegerentschädigungssysteme noch "
    "unter Einlagensicherungssysteme."
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

            for pattern in (*rule.required_patterns, *rule.required_patterns_de):
                try:
                    compiled = re.compile(pattern, re.IGNORECASE)
                except re.error as exc:
                    pytest.fail(f"Invalid required_pattern '{pattern}' in rule {rule.rule_id}: {exc}")
                # A named group stands for a listed term: the rule pages build their passing example
                # from the name, so the pattern must match it (rules/terms.py).
                for name in compiled.groupindex:
                    assert compiled.search(name.replace("_", " ")), (rule.rule_id, pattern)

            # Without German patterns, a German draft would be checked against the English ones.
            if rule.required_patterns and rule.required_terms_de:
                assert rule.required_patterns_de, rule.rule_id

            for pattern in (*rule.prohibited_patterns, *rule.prohibited_patterns_de):
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


def test_other_and_art_risk_warnings_check_the_statements_of_articles_6_5_and_19_4():
    art_warning = OTHER_WARNING.replace("crypto-asset", "asset-referenced token")
    assert _risk_warning(WhitepaperType.OTHER, OTHER_WARNING).status == "pass"
    assert _risk_warning(WhitepaperType.ART, art_warning).status == "pass"
    assert _risk_warning(WhitepaperType.OTHER, OTHER_WARNING_DE, language="de").status == "pass"
    # The old terms "risk", "value" and "loss" let a warning without the two scheme statements pass.
    for whitepaper_type in (WhitepaperType.OTHER, WhitepaperType.ART):
        finding = _risk_warning(whitepaper_type, LOSS_OF_VALUE_WARNING)
        assert finding.issues == ("Missing review terms: investor compensation, deposit guarantee.",)


def test_other_regimes_ask_for_more_than_the_emt_warnings():
    for whitepaper_type in (WhitepaperType.OTHER, WhitepaperType.ART):
        finding = _risk_warning(whitepaper_type, EMT_WARNING)
        assert finding.status == "review"
        assert any(issue.startswith("Missing review terms") for issue in finding.issues)


def _art_issues(rule_id: str, text: str, **metadata: str) -> tuple[str, ...]:
    rule = next(rule for rule in RULESETS[WhitepaperType.ART] if rule.rule_id == rule_id)
    whitepaper = Whitepaper(
        title="Synthetic draft", type=WhitepaperType.ART, sections={rule.section: text}, metadata=metadata
    )
    return Linter((rule,)).lint(whitepaper)[0].issues


def test_art_redemption_rules_ask_for_the_content_of_article_39():
    # Art. 39 MiCAR and Annex II Part D: a permanent right of redemption, in funds other than electronic
    # money at the market value of the referenced assets, without a fee; Art. 46: suspension under the
    # recovery plan.
    texts = {
        ("ANNEX_II.D", "en"): (
            "The holder has a permanent right of redemption against the issuer and further rights under "
            "the terms, and may file complaints under the issuer's complaints-handling procedure."
        ),
        ("ANNEX_II.I", "en"): (
            "The issuer redeems in funds at the market value of the referenced assets. The procedure and "
            "the timeframe follow the redemption policy. Redemption is not subject to a fee, and a "
            "suspension is possible only under Art. 46 MiCAR."
        ),
        ("ANNEX_II.D", "de"): (
            "Der Inhaber hat dauerhafte Rücktauschrechte gegenüber dem Emittenten und weitere Rechte; "
            "Beschwerden richtet er an das Beschwerdeverfahren des Emittenten."
        ),
        ("ANNEX_II.I", "de"): (
            "Der Rücktausch erfolgt zum Marktwert der Vermögenswerte. Verfahren und Zeitrahmen regelt die "
            "Rücktauschstrategie. Der Rücktausch ist nicht gebührenpflichtig; eine Aussetzung ist nur "
            "nach Artikel 46 möglich."
        ),
    }
    for (rule_id, language), text in texts.items():
        issues = _art_issues(rule_id, text, language=language)
        assert not any(issue.startswith(("Missing review terms", "Fehlende Begriffe")) for issue in issues)
    # Redemption at par value is the e-money token rule of Art. 49(4); it does not stand in for an ART.
    issues = _art_issues("ANNEX_II.D", "The holder has rights of redemption at par and may file complaints.")
    assert "Missing review terms: permanent." in issues
    issues = _art_issues(
        "ANNEX_II.I",
        "The issuer redeems at par. The procedure and the timeframe follow the redemption policy. Redemption "
        "is not subject to a fee, and a suspension is possible only under Art. 46 MiCAR.",
    )
    assert "Missing review terms: market value." in issues
    issues = _art_issues(
        "ANNEX_II.I",
        "Der Rücktausch erfolgt zu par. Verfahren und Zeitrahmen regelt die Rücktauschstrategie. Der "
        "Rücktausch ist gebührenfrei; eine Aussetzung ist nur nach Artikel 46 möglich.",
        language="de",
    )
    assert "Fehlende Begriffe: marktwert." in issues


def test_project_metadata_points_to_current_repository():
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert "github.com/sebastianfoerste/micar-whitepaper-linter" in pyproject
    assert "github.com/sebastianforste/micar-whitepaper-linter" not in pyproject
