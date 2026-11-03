"""Listed terms that a plain substring would also find inside other words (rules/terms.py).

Each case pairs a section that uses only a look-alike word, which leaves the term missing, with one that
uses the term itself. The issuers are fictional.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from micar_linter.linter import Linter, lint_whitepaper
from micar_linter.rules import RULESETS
from micar_linter.rules.base import Finding
from micar_linter.whitepaper import Whitepaper, WhitepaperType, load_whitepaper


def _finding(whitepaper_type: WhitepaperType, rule_id: str, text: str, lang: str = "en") -> Finding:
    rule = next(rule for rule in RULESETS[whitepaper_type] if rule.rule_id == rule_id)
    whitepaper = Whitepaper(
        title="Synthetic draft",
        type=whitepaper_type,
        sections={rule.section: text},
        metadata={"language": lang},
    )
    return Linter((rule,)).lint(whitepaper)[0]


def _missing(finding: Finding) -> list[str]:
    prefixes = ("Missing review terms: ", "Fehlende Begriffe: ")
    for issue in finding.issues:
        for prefix in prefixes:
            if issue.startswith(prefix):
                return issue.removeprefix(prefix).removesuffix(".").split(", ")
    return []


CASES = [
    # (regime, rule, language, term, look-alike text, text with the term)
    (
        WhitepaperType.ART,
        "ANNEX_II.I",
        "en",
        "fee",
        "Holders send feedback on the redemption price feed to the issuer.",
        "Redemption is not subject to a fee.",
    ),
    (
        WhitepaperType.ART,
        "ANNEX_II.I",
        "de",
        "gebühr",
        "Die Interessen der Inhaber werden beim Rücktausch gebührend berücksichtigt.",
        "Für den Rücktausch fällt keine Gebühr an.",
    ),
    (
        WhitepaperType.ART,
        "ANNEX_II.I",
        "de",
        "aussetzung",
        "Die Voraussetzungen des Rücktauschs regelt die Rücktauschstrategie.",
        "Eine Aussetzung des Rücktauschs ist nur nach Artikel 46 möglich.",
    ),
    (
        WhitepaperType.ART,
        "ANNEX_II.D",
        "en",
        "permanent",
        "Tokens returned to the issuer are permanently burned.",
        "Holders have a permanent right of redemption.",
    ),
    (
        # "At all times" also describes the reserve, the policy and complaints, so it does not count.
        WhitepaperType.ART,
        "ANNEX_II.D",
        "en",
        "permanent",
        "Redemption is available only on the last business day of each calendar quarter. The reserve of assets "
        "shall at all times be sufficient to meet redemption requests, and holders may at all times submit "
        "complaints about redemption requests.",
        "Holders have a permanent right of redemption against the issuer.",
    ),
    (
        WhitepaperType.ART,
        "ANNEX_II.D",
        "de",
        "dauerhaft",
        "Beschwerden können auf einem dauerhaften Datenträger eingereicht werden.",
        "Die Inhaber haben dauerhafte Rücktauschrechte.",
    ),
    (
        WhitepaperType.ART,
        "ANNEX_II.D",
        "de",
        "dauerhaft",
        "Ein Rücktausch ist nur am letzten Geschäftstag jedes Quartals möglich. Die Vermögenswertreserve muss "
        "jederzeit ausreichen, um Rücktauschanträge zu erfüllen.",
        "Das Recht auf Rücktausch ist dauerhaft.",
    ),
    (
        WhitepaperType.ART,
        "ANNEX_II.I",
        "de",
        "aussetzung",
        "Die Vorraussetzungen des Rücktauschs regelt die Rücktauschstrategie.",
        "Eine vorübergehende Aussetzung des Rücktauschs ist nur nach Artikel 46 möglich.",
    ),
    (
        WhitepaperType.ART,
        "ANNEX_II.I",
        "de",
        "aussetzung",
        "Der Rücktausch erfolgt binnen fünf Geschäftstagen, vorausgesetzt, dass der Inhaber identifiziert ist. "
        "Bis zur Auszahlung sind die Inhaber dem Risiko ausgesetzt, dass der Marktwert sinkt.",
        "Die Aussetzung des Rücktauschs regelt Artikel 46.",
    ),
    (
        WhitepaperType.ART,
        "ANNEX_II.G.VALUATION_AUDIT",
        "en",
        "valuation",
        "Each referenced asset is listed below. Holders of our valued community bear the risk of a devaluation "
        "of the euro.",
        "Each referenced asset is valued daily at its market price.",
    ),
    (
        WhitepaperType.ART,
        "ANNEX_II.G.VALUATION_AUDIT",
        "en",
        "referenced asset",
        "The asset referenced token gives a claim whose components are valued daily.",
        "The assets referenced by the token are valued daily.",
    ),
    (
        WhitepaperType.ART,
        "ANNEX_II.G.VALUATION_AUDIT",
        "de",
        "referenzierter vermögenswert",
        "Die Referenzwerte des vermögenswertereferenzierten Token werden täglich bewertet.",
        "Die Vermögenswerte, auf die sich der Token bezieht, werden täglich bewertet.",
    ),
    (
        WhitepaperType.ART,
        "ANNEX_II.G.VALUATION_AUDIT",
        "de",
        "referenzierter vermögenswert",
        "Die Vermögenswertreserve, auf die sich der Anspruch der Inhaber im Insolvenzfall bezieht, wird täglich "
        "bewertet.",
        "Jeder Vermögenswert, auf den der Token Bezug nimmt, wird täglich bewertet.",
    ),
    (
        WhitepaperType.ART,
        "ANNEX_II.C",
        "de",
        "gericht",
        "Die potenziellen Inhaber, auf die das öffentliche Angebot ausgerichtet ist, sind unten genannt.",
        "Zuständig ist das Landgericht Berlin.",
    ),
    (
        WhitepaperType.OTHER,
        "ANNEX_I.E",
        "de",
        "gericht",
        "Das Angebot ist an Anleger in Deutschland gerichtet.",
        "Das zuständige Gericht ist in Berlin.",
    ),
    (
        WhitepaperType.OTHER,
        "ANNEX_I.G",
        "de",
        "gericht",
        "Für die Ausübung der Rechte ist ein Kundenkonto eingerichtet.",
        "Für Streitigkeiten sind die Gerichte in Berlin zuständig.",
    ),
    (
        WhitepaperType.EMT,
        "ANNEX_III.C",
        "de",
        "gericht",
        "Das Angebot ist an Verbraucher gerichtet.",
        "Das zuständige Gericht ist in Berlin.",
    ),
    (
        WhitepaperType.OTHER,
        "ANNEX_I.I",
        "en",
        "offer or admission to trading",
        "The issuer, if different from the offeror, carries its own risks.",
        "The crypto-assets are admitted to trading; the risks of the admission to trading are set out below.",
    ),
    (
        WhitepaperType.OTHER,
        "ANNEX_I.I",
        "en",
        "offer or admission to trading",
        "The token price depends on offer and demand.",
        "The risks of the admission of the crypto-assets to trading are set out below.",
    ),
    (
        WhitepaperType.ART,
        "ANNEX_II.F",
        "de",
        "angebot oder zulassung zum handel",
        "Der Preis hängt von Angebot und Nachfrage ab.",
        "Die mit der Zulassung der Token zum Handel verbundenen Risiken sind unten beschrieben.",
    ),
    (
        WhitepaperType.OTHER,
        "ANNEX_I.A",
        "en",
        "address",
        "Example Offeror GmbH. E-mail address: contact@offeror.example.",
        "The business address of each member of the management body is Example Street 1, Berlin.",
    ),
    (
        WhitepaperType.OTHER,
        "ANNEX_I.A",
        "en",
        "address",
        "This section addresses the offeror. The smart contract address is listed in Part H.",
        "The addresses of the members of the management body are listed below.",
    ),
    (
        WhitepaperType.EMT,
        "ANNEX_III.A",
        "de",
        "anschrift",
        "Example Issuer AG. E-Mail-Anschrift: kontakt@issuer.example.",
        "Die Geschäftsanschrift der Mitglieder des Leitungsorgans ist Beispielstraße 1, Berlin.",
    ),
    (
        WhitepaperType.OTHER,
        "COMMON.MANAGEMENT_STATEMENT",
        "de",
        "titel ii iii oder iv",
        "Das Leitungsorgan erklärt zum Kryptowerte-Whitepaper mit dem Titel „Example Token“, dass es "
        "redlich, eindeutig und nicht irreführend ist.",
        "Dieses Kryptowerte-Whitepaper erfüllt Titel II der Verordnung (EU) 2023/1114.",
    ),
]


@pytest.mark.parametrize(
    ("whitepaper_type", "rule_id", "lang", "term", "look_alike", "with_term"),
    CASES,
    ids=[f"{rule_id}-{lang}-{term}-{index}" for index, (_, rule_id, lang, term, *_) in enumerate(CASES)],
)
def test_look_alike_words_do_not_stand_in_for_the_term(
    whitepaper_type, rule_id, lang, term, look_alike, with_term
):
    assert term in _missing(_finding(whitepaper_type, rule_id, look_alike, lang))
    assert term not in _missing(_finding(whitepaper_type, rule_id, with_term, lang))


@pytest.mark.parametrize("whitepaper_type", ["art", "emt", "other"])
def test_untouched_starter_template_passes_no_rule(tmp_path: Path, whitepaper_type: str):
    # The linter does not treat "REPLACE:" text as a placeholder, so each placeholder stays below its
    # rule's minimum length or leaves out one of its terms (templates/whitepaper-starter/README.md), whichever
    # "type" the user sets: an e-money token's risk warning needs only the two scheme terms.
    template = json.loads(Path("templates/whitepaper-starter/whitepaper.json").read_text(encoding="utf-8"))
    path = tmp_path / "whitepaper.json"
    path.write_text(json.dumps({**template, "type": whitepaper_type}), encoding="utf-8")
    report = lint_whitepaper(load_whitepaper(path))
    assert [finding.rule.rule_id for finding in report.findings if finding.status == "pass"] == []


@pytest.mark.parametrize(
    ("whitepaper_type", "rule_id", "text"),
    [
        (
            WhitepaperType.OTHER,
            "ANNEX_I.I",
            "The risks of the offer to the public, of the project and of the technology used are described "
            "below.",
        ),
        (
            WhitepaperType.ART,
            "ANNEX_II.F",
            "The risks of the reserve of assets, of the issuer, of the offer to the public and of the "
            "technology used are described below.",
        ),
        (
            WhitepaperType.EMT,
            "ANNEX_III.F",
            "The risks associated with the issuer and with the technology used are described below.",
        ),
    ],
)
def test_risk_sections_need_no_mitigation_measures(whitepaper_type, rule_id, text):
    # Annex I Part I No. 5, Annex II Part F No. 6 and Annex III Part F No. 3 ask for mitigation measures
    # "if any".
    assert _missing(_finding(whitepaper_type, rule_id, text)) == []
