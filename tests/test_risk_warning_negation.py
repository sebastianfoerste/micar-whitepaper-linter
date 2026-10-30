"""COMMON.RISK_WARNING does not pass a warning that states the opposite of a required statement (#71).

Art. 6(5), points (a) to (c), (e) and (f), and Art. 19(4) MiCAR require a clear and unambiguous statement
that the crypto-asset may lose its value, may not always be transferable and may not be liquid, and that
investor compensation and deposit guarantee schemes do not cover it; Art. 51(4) requires the warning on
the two schemes for e-money tokens. A text that turns a statement around contains the same words.
"""

from __future__ import annotations

import pytest

from micar_linter.linter import Linter
from micar_linter.rules import RULESETS
from micar_linter.whitepaper import Whitepaper, WhitepaperType

LOSS = "Prohibited wording found: it cannot lose its value."
TRANSFER = "Prohibited wording found: it is always transferable."
LIQUID = "Prohibited wording found: it is always liquid."
SCHEMES = "Prohibited wording found: a compensation or guarantee scheme covers it."
VERLUST = "Unzulässige Formulierung gefunden: er kann seinen Wert nicht verlieren."
UEBERTRAGBAR = "Unzulässige Formulierung gefunden: er ist stets übertragbar."
LIQUIDE = "Unzulässige Formulierung gefunden: er ist stets liquide."
SYSTEME = "Unzulässige Formulierung gefunden: ein Entschädigungssystem oder Einlagensicherungssystem deckt ihn."

# The statements as Art. 6(5) MiCAR words them, and as fields 04 and 06 of Table 2 of Implementing
# Regulation (EU) 2024/2984 print them.
MICAR_EN = (
    "The crypto-asset may lose its value in part or in full. The crypto-asset may not always be transferable. "
    "The crypto-asset may not be liquid. The crypto-asset is not covered by the investor compensation schemes "
    "under Directive 97/9/EC. The crypto-asset is not covered by the deposit guarantee schemes under Directive "
    "2014/49/EU."
)
TEMPLATE_EN = (
    "The crypto-asset referred to in this crypto-asset white paper may lose its value in part or in full, may "
    "not always be transferable and may not be liquid. The crypto-asset referred to in this white paper is not "
    "covered by the investor compensation schemes under Directive 97/9/EC of the European Parliament and of the "
    "Council or the deposit guarantee schemes under Directive 2014/49/EU of the European Parliament and of the "
    "Council."
)
# Fields 04 and 06 of Table 2 in the German Official Journal text.
TEMPLATE_DE = (
    "Der in diesem Kryptowerte-Whitepaper genannte Kryptowert kann seinen Wert ganz oder teilweise verlieren, "
    "ist möglicherweise nicht immer übertragbar und ist möglicherweise nicht liquide. Der in diesem Whitepaper "
    "genannte Kryptowert fällt nicht unter die Systeme für die Entschädigung der Anleger gemäß der Richtlinie "
    "97/9/EG des Europäischen Parlaments und des Rates oder die Einlagensicherungssysteme gemäß der Richtlinie "
    "2014/49/EU des Europäischen Parlaments und des Rates."
)


def _finding(text: str, whitepaper_type: WhitepaperType = WhitepaperType.OTHER, language: str | None = None):
    rule = next(rule for rule in RULESETS[whitepaper_type] if rule.rule_id == "COMMON.RISK_WARNING")
    metadata = {"language": language} if language else {}
    whitepaper = Whitepaper(title="Synthetic", type=whitepaper_type, sections={"risk_warning": text}, metadata=metadata)
    return Linter((rule,)).lint(whitepaper)[0]


def test_the_issue_text_goes_to_review():
    # The reproduction of #71.
    text = (
        "The crypto-asset cannot lose its value in part or in full, is always transferable and is always liquid. "
        "Investor compensation schemes and deposit guarantee schemes cover the crypto-asset in full."
    )
    finding = _finding(text)
    assert finding.status == "review"
    assert [issue for issue in finding.issues if issue.startswith("Prohibited")] == [LOSS, TRANSFER, LIQUID, SCHEMES]


@pytest.mark.parametrize(
    ("sentence", "issue"),
    [
        ("The crypto-asset will never lose its value.", LOSS),
        ("The crypto-asset does not lose its value in any market.", LOSS),
        ("Holders can't lose the value of the token.", LOSS),
        ("The crypto-asset will not lose its value.", LOSS),
        ("The token can always be transferred.", TRANSFER),
        ("The crypto-asset is transferable at all times.", TRANSFER),
        ("The crypto-asset will always be liquid.", LIQUID),
        ("The crypto-asset is liquid at all times.", LIQUID),
        ("The crypto-asset is covered by the investor compensation schemes under Directive 97/9/EC.", SCHEMES),
        ("The crypto-asset is fully protected by the deposit guarantee schemes.", SCHEMES),
        ("Deposit guarantee schemes cover the crypto-asset.", SCHEMES),
    ],
)
def test_a_statement_turned_around_goes_to_review(sentence: str, issue: str):
    finding = _finding(f"{MICAR_EN} {sentence}")
    assert finding.status == "review"
    assert issue in finding.issues


@pytest.mark.parametrize(
    "text",
    [
        MICAR_EN,
        TEMPLATE_EN,
        # The two schemes in one negated sentence, in active voice.
        MICAR_EN.split(" The crypto-asset is not covered")[0]
        + " Neither investor compensation schemes nor deposit guarantee schemes cover the crypto-asset.",
        MICAR_EN.split(" The crypto-asset is not covered")[0]
        + " Neither the investor compensation schemes nor the deposit guarantee schemes cover the crypto-asset.",
        MICAR_EN.split(" The crypto-asset is not covered")[0]
        + " Investor compensation schemes and deposit guarantee schemes do not cover the crypto-asset.",
        # A warning that no one can promise the value holds.
        MICAR_EN + " There is no guarantee that the crypto-asset will not lose its value.",
        MICAR_EN + " The crypto-asset may not be transferable at all times.",
    ],
)
def test_the_required_statements_still_pass(text: str):
    assert _finding(text).status == "pass", _finding(text).issues


@pytest.mark.parametrize(
    ("sentence", "issue"),
    [
        ("Der Kryptowert kann seinen Wert nicht verlieren.", VERLUST),
        ("Der Kryptowert verliert seinen Wert nicht.", VERLUST),
        ("Der Kryptowert ist stets übertragbar.", UEBERTRAGBAR),
        ("Der Kryptowert ist jederzeit liquide.", LIQUIDE),
        ("Der Kryptowert fällt unter die Einlagensicherungssysteme.", SYSTEME),
        ("Der Kryptowert fällt unter die Systeme für die Entschädigung der Anleger.", SYSTEME),
        ("Der Kryptowert ist durch die Systeme für die Entschädigung der Anleger gedeckt.", SYSTEME),
        ("Der Kryptowert ist durch die Anlegerentschädigungssysteme gedeckt.", SYSTEME),
        ("Wir bestätigen, dass der Kryptowert unter die Einlagensicherungssysteme fällt.", SYSTEME),
    ],
)
def test_a_german_statement_turned_around_goes_to_review(sentence: str, issue: str):
    finding = _finding(f"{TEMPLATE_DE} {sentence}", language="de")
    assert finding.status == "review"
    assert issue in finding.issues


@pytest.mark.parametrize(
    "text",
    [
        TEMPLATE_DE,
        # Points (a) to (c), (e) and (f) of Art. 6(5) MiCAR in the German Official Journal text, joined into one
        # sentence, verb last.
        "Das Kryptowerte-Whitepaper enthält die Erklärung, dass der Kryptowert seinen Wert ganz oder teilweise "
        "verlieren können, der Kryptowert möglicherweise nicht immer übertragbar ist, der Kryptowert möglicherweise "
        "nicht liquide ist, der Kryptowert je nach Sachlage nicht unter die Systeme für die Entschädigung der "
        "Anleger gemäß der Richtlinie 97/9/EG des Europäischen Parlaments und des Rates fällt und der Kryptowert "
        "nicht unter die Einlagensicherungssysteme gemäß der Richtlinie 2014/49/EU fällt.",
        TEMPLATE_DE + " Er ist weder durch Anlegerentschädigungssysteme noch durch Einlagensicherungssysteme gedeckt.",
        TEMPLATE_DE + " Er fällt weder unter die Systeme für die Entschädigung der Anleger noch unter die "
        "Einlagensicherungssysteme.",
        TEMPLATE_DE + " Wir bestätigen, dass der Kryptowert weder unter die Systeme für die Entschädigung der Anleger "
        "noch unter die Einlagensicherungssysteme fällt.",
        TEMPLATE_DE + " Inhaber müssen damit rechnen, dass er seinen Wert ganz oder teilweise verlieren kann und "
        "möglicherweise nicht immer übertragbar ist.",
    ],
)
def test_the_german_statements_still_pass(text: str):
    assert _finding(text, language="de").status == "pass", _finding(text, language="de").issues


def test_the_german_e_money_token_warning_is_checked_for_the_schemes():
    # Field I.04 of Table 4 in the German Official Journal text.
    warning = (
        "Dieser E-Geld-Token fällt nicht unter die Systeme für die Entschädigung der Anleger gemäß der Richtlinie "
        "97/9/EG des Europäischen Parlaments und des Rates oder die Einlagensicherungssysteme gemäß der Richtlinie "
        "2014/49/EU des Europäischen Parlaments und des Rates."
    )
    assert _finding(warning, WhitepaperType.EMT, language="de").status == "pass"
    finding = _finding(warning.replace("fällt nicht unter", "fällt unter"), WhitepaperType.EMT, language="de")
    assert finding.status == "review"
    assert SYSTEME in finding.issues


def test_the_e_money_token_warning_is_checked_for_the_schemes():
    warning = (
        "This e-money token is not covered by the investor compensation schemes under Directive 97/9/EC of the "
        "European Parliament and of the Council or the deposit guarantee schemes under Directive 2014/49/EU of the "
        "European Parliament and of the Council."
    )
    assert _finding(warning, WhitepaperType.EMT).status == "pass"
    turned = warning.replace("is not covered", "is covered")
    finding = _finding(turned, WhitepaperType.EMT)
    assert finding.status == "review"
    assert SCHEMES in finding.issues
