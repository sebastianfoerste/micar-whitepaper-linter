from micar_linter.linter import Linter
from micar_linter.rules.common import COMMON_RULES
from micar_linter.whitepaper import Whitepaper, WhitepaperType


def test_german_language_auto_detection():
    # Simple German sample
    wp_de = Whitepaper(
        title="Test WP DE",
        type=WhitepaperType.OTHER,
        sections={
            "summary": "Dies ist die Zusammenfassung des Projekts. Es enthält wesentliche Informationen.",
            "risk_warning": "Das ist ein Warnhinweis bezüglich des Risikos eines Wertverlusts.",
        },
        metadata={},
    )
    assert wp_de.language == "de"

    # Simple English sample
    wp_en = Whitepaper(
        title="Test WP EN",
        type=WhitepaperType.OTHER,
        sections={
            "summary": "This is the summary of the project. It contains key information.",
            "risk_warning": "This is a warning warning about the risk of value loss.",
        },
        metadata={},
    )
    assert wp_en.language == "en"


def test_german_draft_linting():
    # A complete German draft should pass the common rules checks using German terms
    wp_de = Whitepaper(
        title="Deutscher Entwurf",
        type=WhitepaperType.OTHER,
        sections={
            "summary": (
                # The warning of Art. 6(7) MiCAR, second subparagraph, as field 07 of Table 2 of Implementing
                # Regulation (EU) 2024/2984 prints it in German.
                "Warnhinweis: Diese Zusammenfassung ist als Einführung in das Kryptowerte-Whitepaper zu lesen. "
                "Der potenzielle Inhaber sollte jede Entscheidung über den Kauf des Kryptowerts auf der Grundlage "
                "des Inhalts des gesamten Kryptowerte-Whitepapers und nicht allein auf der Grundlage der "
                "Zusammenfassung treffen. Das öffentliche Angebot dieses Kryptowerts stellt kein Angebot und keine "
                "Aufforderung zum Kauf von Finanzinstrumenten dar und ein solches Angebot oder eine solche "
                "Aufforderung kann nur mittels eines Prospekts oder anderer im geltenden nationalen Recht "
                "vorgesehener Angebotsunterlagen erfolgen. Dieses Kryptowerte-Whitepaper stellt keinen Prospekt im "
                "Sinne der Verordnung (EU) 2017/1129 des Europäischen Parlaments und des Rates und kein anderes "
                "Angebotsdokument im Sinne von Unionsrecht oder nationalem Recht dar. "
                "Diese Zusammenfassung bietet wesentliche Informationen für alle potenziellen "
                "Anleger und Erwerber dieses neuartigen Krypto-Assets. Die hier bereitgestellten "
                "Details dienen dazu, ein grundlegendes Verständnis des Projekts und der damit "
                "verbundenen Risiken zu ermöglichen. Alle Leser werden dringend gebeten, dieses "
                "Dokument vor einer Anlageentscheidung sorgfältig und vollständig durchzulesen, "
                "um die angebotenen Dienstleistungen und Bedingungen vollumfänglich zu verstehen. "
                "Die wichtigsten Informationen sind in diesem Text einfach und übersichtlich "
                "zusammengefasst, damit sie leicht erfasst werden können. Daher ist diese Zusammenfassung "
                "beziehungsweise Plain-Language Summary für alle Beteiligten des Krypto-Assets ein "
                "hervorragender Einstiegspunkt, der die wesentlichen Aspekte vollumfänglich abdeckt."
            ),
            "risk_warning": (
                "Warnhinweis: Der Kryptowert kann seinen Wert ganz oder teilweise verlieren. Der "
                "Kryptowert ist möglicherweise nicht immer übertragbar und möglicherweise nicht liquide. "
                "Er fällt nicht unter die Systeme für die Entschädigung der Anleger gemäß der Richtlinie "
                "97/9/EG und nicht unter die Einlagensicherungssysteme gemäß der Richtlinie 2014/49/EU."
            ),
            "management_statement": (
                "Das Leitungsorgan bestätigt hiermit ausdrücklich, dass dieser vorliegende Entwurf des "
                "Krypto-Wertpapier-Informationsblatts vollumfänglich Titel II der Verordnung (EU) 2023/1114 "
                "entspricht und "
                "inhaltlich vollständig, redlich, eindeutig sowie nicht irreführend gestaltet ist. "
                "Alle wesentlichen Angaben wurden nach bestem Wissen und Gewissen sorgfältig "
                "geprüft, detailliert verifiziert und freigegeben."
            ),
            "notification_date": "Datum der Notifizierung ist heute am 29. Mai 2026.",
            "language": "Die offizielle Sprache dieses Dokuments ist Deutsch, wie gesetzlich vorgesehen.",
        },
        metadata={},
    )

    findings = Linter(COMMON_RULES).lint(wp_de)

    for f in findings:
        if f.rule.rule_id in (
            "COMMON.SUMMARY",
            "COMMON.RISK_WARNING",
            "COMMON.MANAGEMENT_STATEMENT",
            "COMMON.NOTIFICATION_DATE",
            "COMMON.LANGUAGE",
        ):
            assert f.passed, f"Rule {f.rule.rule_id} failed: {f.issues}"
