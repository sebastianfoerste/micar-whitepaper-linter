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
        metadata={}
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
        metadata={}
    )
    assert wp_en.language == "en"


def test_german_draft_linting():
    # A complete German draft should pass the common rules checks using German terms
    wp_de = Whitepaper(
        title="Deutscher Entwurf",
        type=WhitepaperType.OTHER,
        sections={
            "summary": (
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
                "Warnhinweis: Der Erwerb dieses Krypto-Assets ist mit dem Risiko eines vollständigen "
                "Wertverlusts oder Verlusts des eingesetzten Kapitals verbunden. Es wird keine "
                "Gewährleistung für Gewinne oder Erträge gegeben, und die vergangene Entwicklung "
                "ist kein Indikator für zukünftige Ergebnisse. Bitte handeln Sie vorsichtig."
            ),
            "management_statement": (
                "Das Leitungsorgan bestätigt hiermit ausdrücklich, dass dieser vorliegende Entwurf des "
                "Krypto-Wertpapier-Informationsblatts vollumfänglich den gesetzlichen Vorgaben entspricht und "
                "inhaltlich vollständig, redlich, eindeutig sowie nicht irreführend gestaltet ist. "
                "Alle wesentlichen Angaben wurden nach bestem Wissen und Gewissen sorgfältig "
                "geprüft, detailliert verifiziert und freigegeben."
            ),
            "notification_date": "Datum der Notifizierung ist heute am 29. Mai 2026.",
            "language": "Die offizielle Sprache dieses Dokuments ist Deutsch, wie gesetzlich vorgesehen.",
        },
        metadata={}
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
