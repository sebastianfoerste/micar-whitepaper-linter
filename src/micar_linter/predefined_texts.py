"""The predefined texts of the templates in Implementing Regulation (EU) 2024/2984, in English and German.

Read on 2026-11-04 from the English and German Official Journal text (OJ L, 2024/2984, 3.12.2024) as the
Publications Office Cellar serves it: fields 02 to 07 of Table 2, I.02 to I.04 and I.06 of Table 3 and I.02 to
I.05 and I.07 of Table 4, whose form column reads "Predefined alphanumerical text" ("Vorgegebener
alphanumerischer Text"). Fields I.06 of Table 3 and I.07 of Table 4 add free text after the predefined
sentence. Field 05 of Table 2 is "'true' - Yes, 'false' - Not applicable; if Yes, predefined alphanumerical
text"; the German text codes the two values "richtig" and "falsch".

Each text is a list of sentences, compared one by one. The words are compared without case, punctuation,
quotation marks, hyphens and spacing, with ä, ö, ü and ß read as ae, oe, ue and ss, so "crypto-asset",
"crypto asset" and "crypto \u2013asset" read the same, and so do "Kryptowerte-Whitepaper" and
"Kryptowerte Whitepaper".
Square brackets mark words a draft may leave out, braces alternatives separated by "|". The optional and
alternative words cover only what does not change the statement:

- the full title of a cited act ("of the European Parliament and of the Council"), which the tables print
  and MiCAR does not;
- "this" or "the" before "crypto-asset white paper", where Table 2 and Tables 3 and 4 differ;
- "that" before "any such offer" (Table 4 prints it, Tables 2 and 3 do not) and the two German wordings
  of the summary warning, which differ between the tables;
- the name of the token in the summary warning (crypto-asset, asset-referenced token or e-money token);
- the misspelling "asset-refenced token" in the second sentence of I.02 of Table 3, beside the correct word;
- "complete" ("vollständig") in I.03 of Table 4: Art. 51(5) MiCAR has the management body confirm that the
  information is "complete, fair, clear and not misleading", and the template leaves out "complete".

Field 02 of Table 2 has three wordings, one for the offeror, one for the person seeking admission to trading
and one for the operator of the trading platform; any one of them counts.
"""

from __future__ import annotations

from micar_linter.whitepaper import WhitepaperType

_ACT_EN = "[ of the European Parliament and of the Council]"
_ACT_DE = "[ des Europäischen Parlaments und des Rates]"
_APPROVAL_EN = (
    "This crypto-asset white paper has not been approved by any competent authority in any Member State "
    "of the European Union."
)
_APPROVAL_DE = (
    "Dieses Kryptowerte-Whitepaper wurde von keiner zuständigen Behörde eines Mitgliedstaats der "
    "Europäischen Union genehmigt."
)
_SCHEMES_EN = (
    f"is not covered by the investor compensation schemes under Directive 97/9/EC{_ACT_EN} or the "
    f"deposit guarantee schemes under Directive 2014/49/EU{_ACT_EN}."
)
_SCHEMES_DE = (
    f"fällt nicht unter die Systeme für die Entschädigung der Anleger gemäß der Richtlinie "
    f"97/9/EG{_ACT_DE} oder die Einlagensicherungssysteme gemäß der Richtlinie "
    f"2014/49/EU{_ACT_DE}."
)
_LOSS_EN = "may lose its value in part or in full, may not always be transferable and may not be liquid."
_LOSS_DE = (
    "kann seinen Wert ganz oder teilweise verlieren, ist möglicherweise nicht immer übertragbar "
    "und ist möglicherweise nicht liquide."
)
_TOKEN_EN = "{crypto-asset|asset-referenced token|e-money token}"
_TOKEN_DE = "{Kryptowerts|vermögenswertereferenzierten Token|E-Geld-Token}"
_SUMMARY_WARNING_EN = (
    "This summary should be read as an introduction to the crypto-asset white paper.",
    f"The prospective holder should base any decision to purchase this {_TOKEN_EN} on the content of the "
    "crypto-asset white paper as a whole and not on the summary alone.",
    f"The offer to the public of this {_TOKEN_EN} does not constitute an offer or solicitation to purchase "
    "financial instruments and[ that] any such offer or solicitation can be made only by means of a "
    "prospectus or other offer documents pursuant to the applicable national law.",
    f"This crypto-asset white paper does not constitute a prospectus as referred to in Regulation "
    f"(EU) 2017/1129{_ACT_EN} or any other offer document pursuant to Union or national law.",
)
_SUMMARY_WARNING_DE = (
    "Diese Zusammenfassung ist als Einführung in das Kryptowerte-Whitepaper zu lesen.",
    "{Der potenzielle Inhaber sollte jede Entscheidung über den Kauf|Potenzielle Inhaber sollten ihre "
    f"Entscheidung zum Kauf}} {{des|dieses}} {_TOKEN_DE} auf der Grundlage des Inhalts des gesamten "
    "Kryptowerte-Whitepapers und nicht allein auf der Grundlage der Zusammenfassung treffen.",
    f"Das öffentliche Angebot {{dieses|des}} {_TOKEN_DE} stellt kein Angebot und keine "
    "Aufforderung zum Kauf von Finanzinstrumenten dar und ein solches Angebot oder eine solche "
    "Aufforderung kann nur mittels eines Prospekts oder anderer {im geltenden nationalen Recht "
    "vorgesehener Angebotsunterlagen|Angebotsunterlagen gemäß den nationalen Rechtsvorschriften} erfolgen.",
    f"Dieses Kryptowerte-Whitepaper stellt keinen Prospekt im Sinne der Verordnung (EU) 2017/1129{_ACT_DE} "
    "und kein anderes Angebotsdokument im Sinne von Unionsrecht oder nationalem Recht dar.",
)


def _compliance_en(title: str, complete: bool = False) -> tuple[str, ...]:
    return (
        f"This crypto-asset white paper complies with Title {title} of Regulation (EU) 2023/1114{_ACT_EN} "
        "and to the best of the knowledge of the management body, the information presented in {this|the} "
        f"crypto-asset white paper is {'[complete, ]' if complete else ''}fair, clear and not misleading and"
        "[ that] the crypto-asset white paper makes no omission likely to affect its import.",
    )


def _compliance_de(title: str, complete: bool = False) -> tuple[str, ...]:
    return (
        f"Dieses Kryptowerte-Whitepaper erfüllt Titel {title} der Verordnung (EU) 2023/1114{_ACT_DE} und es "
        "wird bestätigt, dass die in ihm enthaltenen Informationen nach bestem Wissen des Leitungsorgans "
        f"{'[vollständig, ]' if complete else ''}redlich, eindeutig und nicht irreführend sind und dass "
        "{das|dieses} Kryptowerte-Whitepaper keine Auslassungen aufweist, die seine Aussagekraft "
        "beeinträchtigen könnten.",
    )


# The utility-token statement of field 05 of Table 2 (Art. 6(5), point (d), MiCAR).
UTILITY_FIELD = "05"
UTILITY_STATEMENT = (
    (
        "The utility token referred to in this[ crypto-asset] white paper may not be exchangeable "
        "against the good or service promised in this[ crypto-asset] white paper, especially in "
        "the case of a failure or discontinuation of the crypto-asset project.",
    ),
    (
        "Der in diesem Whitepaper genannte Utility-Token kann, insbesondere im Fall eines "
        "Ausfalls oder der Einstellung des Kryptowert-Projekts, möglicherweise nicht gegen die im "
        "Kryptowerte-Whitepaper zugesagte Ware oder Dienstleistung getauscht werden.",
    ),
)
# The fields of Table 2 that classify the token as a utility token ("Utility Token Classification").
UTILITY_FLAG_FIELDS = ("D.6", "G.6")


# Field number -> (English sentences, German sentences, free text may follow).
PREDEFINED_TEXTS: dict[WhitepaperType, dict[str, tuple[tuple[str, ...], tuple[str, ...], bool]]] = {
    WhitepaperType.OTHER: {
        "02": (
            (
                _APPROVAL_EN,
                "The {offeror|person seeking admission to trading|operator of the trading "
                "platform} of the crypto-asset is solely responsible for the content of this "
                "crypto-asset white paper.",
            ),
            (
                _APPROVAL_DE,
                "{Der Anbieter des Kryptowerts|Die Person, die die Zulassung des Kryptowerts zum "
                "Handel beantragt,|Der Betreiber der Handelsplattform des Kryptowerts} trägt die "
                "alleinige Verantwortung für den Inhalt dieses Kryptowerte-Whitepapers.",
            ),
            False,
        ),
        "03": (_compliance_en("II"), _compliance_de("II"), False),
        "04": (
            (f"The crypto-asset referred to in this crypto-asset white paper {_LOSS_EN}",),
            (f"Der in diesem Kryptowerte-Whitepaper genannte Kryptowert {_LOSS_DE}",),
            False,
        ),
        "06": (
            (f"The crypto-asset referred to in this[ crypto-asset] white paper {_SCHEMES_EN}",),
            (f"Der in diesem[ Kryptowerte-]Whitepaper genannte Kryptowert {_SCHEMES_DE}",),
            False,
        ),
        "07": (_SUMMARY_WARNING_EN, _SUMMARY_WARNING_DE, False),
    },
    WhitepaperType.ART: {
        "I.02": (
            (
                f"The asset-referenced token referred to in this crypto-asset white paper "
                f"{_LOSS_EN}",
                "The asset-{referenced|refenced} token referred to in this crypto-asset white paper "
                f"{_SCHEMES_EN}",
            ),
            (
                f"Der in diesem Kryptowerte-Whitepaper genannte vermögenswertereferenzierte Token "
                f"{_LOSS_DE}",
                f"Der in diesem Kryptowerte-Whitepaper genannte vermögenswertereferenzierte Token "
                f"{_SCHEMES_DE}",
            ),
            False,
        ),
        "I.03": (_compliance_en("III"), _compliance_de("III"), False),
        "I.04": (_SUMMARY_WARNING_EN, _SUMMARY_WARNING_DE, False),
        "I.06": (
            ("The holders of asset-referenced tokens have a right of redemption at any time.",),
            ("Die Inhaber vermögenswertereferenzierter Token haben jederzeit ein Recht auf Rücktausch.",),
            True,
        ),
    },
    WhitepaperType.EMT: {
        "I.02": (
            (
                _APPROVAL_EN,
                "The issuer of the crypto-asset is solely responsible for the content of this "
                "crypto-asset white paper.",
            ),
            (
                _APPROVAL_DE,
                "Der Emittent des Kryptowerts trägt die alleinige Verantwortung für den Inhalt "
                "dieses Kryptowerte-Whitepapers.",
            ),
            False,
        ),
        "I.03": (_compliance_en("IV", complete=True), _compliance_de("IV", complete=True), False),
        "I.04": ((f"This e-money token {_SCHEMES_EN}",), (f"Dieser E-Geld-Token {_SCHEMES_DE}",), False),
        "I.05": (_SUMMARY_WARNING_EN, _SUMMARY_WARNING_DE, False),
        "I.07": (
            ("The holders of this e-money token have a right of redemption at any time and at par value.",),
            ("Die Inhaber dieses E-Geld-Token haben jederzeit ein Recht auf Rücktausch zum Nennwert.",),
            True,
        ),
    },
}

# Headings a draft may set before a predefined text: the "Warning" of the summary warning and the three
# "Regarding ..." lines of field 02 of Table 2, which the template prints above each wording.
HEADINGS = (
    "{Warning|Warnhinweis}",
    "{Regarding offerors|Regarding the persons seeking admission to trading|Regarding the "
    "operators of trading platforms|In Bezug auf die Anbieter|In Bezug auf die Personen, die die "
    "Zulassung zum Handel beantragen|In Bezug auf die Betreiber von Handelsplattformen}",
)
