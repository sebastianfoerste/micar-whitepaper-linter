"""Data types and code lists of the numbered template fields, by field number.

Read on 2026-11-04 from the English and German Official Journal text of Implementing Regulation (EU)
2024/2984 (OJ L, 2024/2984, 3.12.2024) as the Publications Office Cellar serves it: the legend of Table 1
of its Annex and the column "Form and standards to be used for reporting" of Tables 2, 3 and 4. The
sustainability indicators S.1 to S.16 come from Tables 2 and 3 of the Annex to Delegated Regulation (EU)
2025/422 (OJ L, 2025/422, 31.3.2025), read the same day in English and German. No corrigendum to either act
was searched for.

Only fields with a data type or a closed list are listed. Free text, the predefined texts (fields 02 to 07 of
Table 2, I.02 to I.07 of Tables 3 and 4, which ITS.PREDEFINED_TEXT reads) and the date of notification (field
01 and I.01, which ITS.NOTIFICATION_DATE_FORMAT reads) are not. Fields that combine a code with free text are
left out too: the legal form (an ISO 20275 code, "only applicable" without an LEI), the registered address and
head office (ISO 3166-1 codes and free text), the offer expenses, the referenced assets ({ISIN} where
applicable) and the closed lists of languages, competent authorities and applicable laws, which the OJ text
does not print. The OJ text types field D.2 of Table 3 ("Planned functionalities use") as an ISO 8601 date;
it is listed as printed.

The German text writes the code EROR of the submission type as "ERROR" and codes true and false as "richtig"
and "falsch"; both spellings are accepted. FIELD_NAMES in template_fields.py holds the English field names;
the German names here let a check recognise a German label. Every module that the playground's JSON path
imports may import this one: it uses the standard library only.
"""

from __future__ import annotations

from dataclasses import dataclass

from micar_linter.whitepaper import WhitepaperType

# Data types of Table 1 and of the form column.
DATE = "date"  # {DATEFORMAT}, YYYY-MM-DD
LEI = "lei"  # {LEI}, ISO 17442
DTI = "dti"  # ISO 24165 Digital Token Identifier, 9 characters
CURRENCY = "currency"  # {CURRENCYCODE_3}, ISO 4217
CURRENCY_OR_DTI = "currency_or_dti"  # {CURRENCYCODE_3} or {DTI}
MIC = "mic"  # {MIC}, ISO 10383, 4 characters
DURATION = "duration"  # {DURATION}, a number of days, 3 characters
AMOUNT = "amount"  # Amount in monetary value {DECIMAL-18/3} or Numerical {INTEGER-n}
INTEGER = "integer"  # Numerical {INTEGER-n}
DECIMAL = "decimal"  # Numerical {DECIMAL-18/3}
FLAG = "flag"  # 'true' or 'false'
# Closed lists: the codes the form column prints, and the EU Member States.
CODES = "codes"
MEMBER_STATES = "member_states"

# The kinds ITS.CODE_LISTS checks; ITS.FIELD_FORMATS checks the others.
CODE_LIST_KINDS = frozenset({CODES, MEMBER_STATES})


@dataclass(frozen=True)
class FieldType:
    """A field's data type, its German name as the German OJ text prints it, and its codes (CODES only)."""

    kind: str
    name_de: str
    codes: tuple[str, ...] = ()


_TABLE_2: dict[str, FieldType] = {
    "A.5": FieldType(DATE, "Registrierungsdatum"),
    "A.6": FieldType(LEI, "Rechtsträgerkennung"),
    "A.10": FieldType(DURATION, "Reaktionszeit (Tage)"),
    "A.15": FieldType(FLAG, "Neu gegründet"),
    "B.1": FieldType(
        FLAG,
        ("Von dem Anbieter oder der Person, die die Zulassung zum Handel beantragt, abweichender Emittent"),
    ),
    "B.6": FieldType(DATE, "Registrierungsdatum"),
    "B.7": FieldType(LEI, "Rechtsträgerkennung"),
    "C.5": FieldType(DATE, "Registrierungsdatum"),
    "C.6": FieldType(LEI, "Rechtsträgerkennung"),
    "D.6": FieldType(FLAG, "Utility-Token-Einstufung"),
    "E.1": FieldType(CODES, "Öffentliches Angebot oder Zulassung zum Handel", ("OTPC", "ATTR")),
    "E.3": FieldType(AMOUNT, "Ziel der Mittelbeschaffung"),
    "E.4": FieldType(AMOUNT, "Mindestziele für die Zeichnung"),
    "E.5": FieldType(AMOUNT, "Höchstziele für die Zeichnung"),
    "E.6": FieldType(FLAG, "Überzeichnungsakzeptanz"),
    "E.8": FieldType(AMOUNT, "Ausgabepreis"),
    "E.9": FieldType(
        CURRENCY_OR_DTI,
        ("Amtliche Währung oder andere Kryptowerte, die den Ausgabepreis bestimmen"),
    ),
    "E.10": FieldType(AMOUNT, "Zeichnungsgebühr"),
    "E.12": FieldType(INTEGER, "Gesamtzahl der angebotenen/gehandelten Kryptowerte"),
    "E.13": FieldType(CODES, "Zielgruppe potenzieller Inhaber", ("RETL", "PROF", "ALL")),
    "E.20": FieldType(FLAG, "Befristetes Angebot"),
    "E.21": FieldType(DATE, "Zeichnungsfrist Beginn"),
    "E.22": FieldType(DATE, "Ende der Zeichnungsfrist"),
    "E.28": FieldType(DATE, "Zeitplan für die Übertragung"),
    "E.31": FieldType(LEI, "CASP-Kennung"),
    "E.32": FieldType(CODES, "Art der Platzierung", ("WITH", "WOUT", "NTAV")),
    "E.34": FieldType(MIC, "Handelsplattformen Marktidentifikationscode (MIC)"),
    "F.4": FieldType(CODES, "Art des Kryptowerte-Whitepapers", ("OTHR",)),
    "F.5": FieldType(CODES, "Die Art der Übermittlung", ("NEWT", "MODI", "EROR", "CORR", "ERROR")),
    "F.9": FieldType(DATE, "Beginn des öffentlichen Angebots oder der Zulassung zum Handel"),
    "F.10": FieldType(DATE, "Datum der Veröffentlichung"),
    "F.13": FieldType(
        DTI,
        (
            "Code für den Digital Token-Identifikator, der verwendet wird, um den Kryptowert oder "
            "die verschiedenen einzelnen Kryptowerte, auf die sich das Whitepaper bezieht, "
            "eindeutig zu identifizieren, sofern verfügbar"
        ),
    ),
    "F.14": FieldType(
        DTI,
        ("Digital Token-Identifikator für die funktional fungible Gruppe, sofern verfügbar"),
    ),
    "F.15": FieldType(FLAG, "Kennzeichnung zur Freiwilligkeit der Datenangabe"),
    "F.16": FieldType(FLAG, "Kennzeichnung personenbezogener Daten"),
    "F.17": FieldType(FLAG, "LEI-Berechtigung"),
    "F.18": FieldType(MEMBER_STATES, "Herkunftsmitgliedstaat"),
    "F.19": FieldType(MEMBER_STATES, "Aufnahmemitgliedstaaten"),
    "G.5": FieldType(INTEGER, "Vom Emittenten selbst behaltene Kryptowerte"),
    "G.6": FieldType(FLAG, "Utility-Token-Einstufung"),
    "G.9": FieldType(FLAG, "Nicht-Handelsantrag"),
    "G.12": FieldType(FLAG, "Protokolle für Angebotsanpassung"),
    "G.14": FieldType(FLAG, "Sicherungssysteme für Token-Wert"),
    "G.16": FieldType(FLAG, "Entschädigungssysteme"),
    "H.6": FieldType(FLAG, "Einsatz von Distributed-Ledger-Technologie"),
    "H.8": FieldType(FLAG, "Prüfung"),
}
_TABLE_3: dict[str, FieldType] = {
    "A.6": FieldType(DATE, "Registrierungsdatum"),
    "A.7": FieldType(LEI, "Rechtsträgerkennung"),
    "A.13": FieldType(FLAG, "Neu gegründet"),
    "A.17": FieldType(CODES, "Befreiung von der Zulassungspflicht", ("NOEX", "EX17", "EX16")),
    "A.21": FieldType(FLAG, "Emission anderer Kryptowerte"),
    "A.22": FieldType(FLAG, "Tätigkeiten im Zusammenhang mit anderen Kryptowerten"),
    "A.23": FieldType(FLAG, "Verbindung zwischen dem Emittenten und dem Unternehmen, das die DLT betreibt"),
    "AA.1": FieldType(
        LEI,
        (
            "Gemäß Artikel 19 Absatz 1 Unterabsatz 2 der Verordnung (EU) 2023/1114 Personen, die "
            "den vermögenswertereferenzierten Token öffentlich anbieten oder dessen Zulassung zum "
            "Handel beantragen, sofern sie nicht mit dem Emittenten identisch sind"
        ),
    ),
    "AA.3": FieldType(
        LEI,
        (
            "Andere Personen, die das Kryptowerte-Whitepaper gemäß Artikel 19 Absatz 1 Unterabsatz "
            "2 der Verordnung (EU) 2023/1114 erstellen"
        ),
    ),
    "B.7": FieldType(CODES, "Art des Kryptowerte-Whitepapers", ("ARTW",)),
    "B.8": FieldType(CODES, "Die Art der Übermittlung", ("NEWT", "MODI", "EROR", "CORR", "ERROR")),
    "B.11": FieldType(DATE, "Beginn des öffentlichen Angebots oder der Zulassung zum Handel"),
    "B.12": FieldType(DATE, "Datum der Veröffentlichung"),
    "B.15": FieldType(
        DTI,
        (
            "Code für den Digital Token-Identifikator, der verwendet wird, um den Kryptowert oder "
            "die verschiedenen einzelnen Kryptowerte, auf die sich das Whitepaper bezieht, "
            "eindeutig zu identifizieren, sofern verfügbar"
        ),
    ),
    "B.16": FieldType(
        DTI,
        ("Digital Token-Identifikator für die funktional fungible Gruppe, sofern verfügbar"),
    ),
    "B.17": FieldType(FLAG, "Kennzeichnung personenbezogener Daten"),
    "B.18": FieldType(FLAG, "LEI-Berechtigung"),
    "B.19": FieldType(MEMBER_STATES, "Herkunftsmitgliedstaat"),
    "B.20": FieldType(MEMBER_STATES, "Aufnahmemitgliedstaaten"),
    "C.1": FieldType(CODES, "Öffentliches Angebot oder Zulassung zum Handel", ("OTPC", "ATTR")),
    "C.2": FieldType(AMOUNT, "Ziel der Mittelbeschaffung"),
    "C.3": FieldType(AMOUNT, "Mindestziele für die Zeichnung"),
    "C.4": FieldType(AMOUNT, "Höchstziele für die Zeichnung"),
    "C.5": FieldType(CODES, "Überzeichnungsakzeptanz", ("true", "false", "NTAV")),
    "C.7": FieldType(DECIMAL, "Angebots-/Handelsmenge des Tokens"),
    "C.8": FieldType(CODES, "Zielgruppe potenzieller Inhaber", ("RETL", "PROF")),
    "C.15": FieldType(FLAG, "Befristetes Angebot"),
    "C.16": FieldType(DATE, "Beginn der Zeichnungsfrist"),
    "C.17": FieldType(DATE, "Ende der Zeichnungsfrist"),
    "C.22": FieldType(LEI, "CASP-Kennung"),
    "C.23": FieldType(CODES, "Art der Platzierung", ("WITH", "WOUT", "NTAV")),
    "C.25": FieldType(MIC, "Marktidentifikationscode (MIC) der Handelsplattformen"),
    "D.2": FieldType(DATE, "Geplante Nutzung der Funktionen"),
    "D.7": FieldType(INTEGER, "Vom Emittenten selbst behaltene Anteile"),
    "D.8": FieldType(FLAG, "Nicht-Handelsantrag"),
    "D.11": FieldType(FLAG, "Protokolle für Angebotsanpassung"),
    "D.13": FieldType(FLAG, "Sicherungssysteme für Token-Wert"),
    "D.15": FieldType(FLAG, "Entschädigungssysteme"),
    "D.32": FieldType(FLAG, "Wahlmöglichkeiten bei der Form des Rücktauschs"),
    "D.33": FieldType(FLAG, "Wahlmöglichkeiten bei der Form der Übertragung"),
    "D.35": FieldType(CURRENCY, "Währung des Rücktauschs"),
    "E.6": FieldType(FLAG, "Einsatz von Distributed-Ledger-Technologie"),
    "E.8": FieldType(FLAG, "Prüfung"),
    "G.4": FieldType(FLAG, "Anlage von Vermögenswertreserven"),
    "G.8": FieldType(LEI, "Verwahrer"),
}
_TABLE_4: dict[str, FieldType] = {
    "A.6": FieldType(DATE, "Registrierungsdatum"),
    "A.7": FieldType(LEI, "Rechtsträgerkennung"),
    "A.11": FieldType(DURATION, "Reaktionszeit (Tage)"),
    "A.17": FieldType(FLAG, "Emission anderer Kryptowerte"),
    "A.18": FieldType(FLAG, "Tätigkeiten im Zusammenhang mit anderen Kryptowerten"),
    "A.19": FieldType(FLAG, "Verbindung zwischen dem Emittenten und dem Unternehmen, das die DLT betreibt"),
    "A.21": FieldType(FLAG, "Neu gegründet"),
    "A.24": FieldType(FLAG, "Befreiung von der Zulassungspflicht"),
    "A.27": FieldType(
        LEI,
        (
            "Gemäß Artikel 51 Absatz 1 Unterabsatz 2 der Verordnung (EU) 2023/1114 Personen, die "
            "den E-Geld-Token öffentlich anbieten oder dessen Zulassung zum Handel beantragen, "
            "sofern sie nicht mit dem Emittenten identisch sind"
        ),
    ),
    "B.4": FieldType(CODES, "Art des Whitepapers", ("EMTW",)),
    "B.5": FieldType(CODES, "Die Art der Übermittlung", ("NEWT", "MODI", "EROR", "CORR", "ERROR")),
    "B.8": FieldType(DATE, "Beginn des öffentlichen Angebots oder der Zulassung zum Handel"),
    "B.9": FieldType(DATE, "Datum der Veröffentlichung"),
    "B.12": FieldType(
        DTI,
        (
            "Code für den Digital Token-Identifikator, der verwendet wird, um den Kryptowert oder "
            "die verschiedenen einzelnen Kryptowerte, auf die sich das Whitepaper bezieht, "
            "eindeutig zu identifizieren, sofern verfügbar"
        ),
    ),
    "B.13": FieldType(
        DTI,
        ("Digital Token-Identifikator für die funktional fungible Gruppe, sofern verfügbar"),
    ),
    "B.14": FieldType(FLAG, "Kennzeichnung personenbezogener Daten"),
    "B.15": FieldType(FLAG, "LEI-Berechtigung"),
    "B.16": FieldType(MEMBER_STATES, "Herkunftsmitgliedstaat"),
    "B.17": FieldType(MEMBER_STATES, "Aufnahmemitgliedstaaten"),
    "C.1": FieldType(CODES, "Öffentliches Angebot oder Handel", ("OTPC", "ATTR")),
    "C.2": FieldType(DECIMAL, "Anzahl der Anteile"),
    "C.4": FieldType(MIC, "Marktidentifikationscode (MIC) der Handelsplattformen"),
    "D.9": FieldType(FLAG, "Sicherungssysteme für Token-Wert"),
    "D.11": FieldType(FLAG, "Entschädigungssysteme"),
    "E.7": FieldType(FLAG, "Einsatz von Distributed-Ledger-Technologie"),
    "E.9": FieldType(FLAG, "Prüfung"),
}

FIELD_TYPES: dict[WhitepaperType, dict[str, FieldType]] = {
    WhitepaperType.OTHER: _TABLE_2,
    WhitepaperType.ART: _TABLE_3,
    WhitepaperType.EMT: _TABLE_4,
}

# The table each regime uses.
TABLE_NUMBERS = {WhitepaperType.OTHER: 2, WhitepaperType.ART: 3, WhitepaperType.EMT: 4}

# The date of notification, "YYYY-MM-DD" in the form column of each table.
NOTIFICATION_DATE_FIELDS = {
    WhitepaperType.OTHER: "01",
    WhitepaperType.ART: "I.01",
    WhitepaperType.EMT: "I.01",
}
NOTIFICATION_DATE_NAMES = ("Date of notification", "Datum der Mitteilung")

# Delegated Regulation (EU) 2025/422, Annex: Table 2 (mandatory, S.1 to S.9) and Table 3 (supplementary,
# S.10 to S.16, required where S.8 exceeds 500 000 kWh, Art. 4(2)). Kinds: free text, a date, an amount in kWh
# {DECIMAL-18/5}, a percentage {DECIMAL-11/10} and an amount in another unit {DECIMAL-18/5}.
TEXT = "text"
ENERGY_KWH = "energy_kwh"
PERCENTAGE = "percentage"
QUANTITY = "quantity"

SUSTAINABILITY_FIELDS: dict[str, tuple[str, str, str]] = {
    "S.1": ("Name", "Bezeichnung", TEXT),
    "S.2": ("Relevant legal entity identifier", "Relevante Rechtsträgerkennung", TEXT),
    "S.3": ("Name of the crypto-asset", "Bezeichnung des Kryptowerts", TEXT),
    "S.4": ("Consensus Mechanism", "Konsensmechanismus", TEXT),
    "S.5": ("Incentive Mechanisms and Applicable Fees", "Anreizmechanismen und Gebühren", TEXT),
    "S.6": (
        "Beginning of the period to which the disclosed information relates",
        "Beginn des Zeitraums, auf den sich die offengelegten Informationen beziehen",
        DATE,
    ),
    "S.7": (
        "End of the period to which the disclosed information relates",
        "Ende des Zeitraums, auf den sich die offengelegten Informationen beziehen",
        DATE,
    ),
    "S.8": ("Energy consumption", "Energieverbrauch", ENERGY_KWH),
    "S.9": (
        "Energy consumption sources and methodologies",
        "Quellen und Methoden für den Energieverbrauch",
        TEXT,
    ),
    "S.10": ("Renewable energy consumption", "Verbrauch erneuerbarer Energien", PERCENTAGE),
    "S.11": ("Energy intensity", "Energieintensität", QUANTITY),
    "S.12": (
        "Scope 1 DLT GHG emissions \u2013 Controlled",
        "Scope-1-DLT-Treibhausgasemissionen \u2014 Kontrolliert",
        QUANTITY,
    ),
    "S.13": (
        "Scope 2 DLT GHG emissions \u2013 Purchased",
        "Scope-2-DLT-Treibhausgasemissionen \u2014 Zugekauft",
        QUANTITY,
    ),
    "S.14": ("GHG intensity", "THG-Intensität", QUANTITY),
    "S.15": ("Key energy sources and methodologies", "Wichtigste energiebezogene Quellen und Methoden", TEXT),
    "S.16": ("Key GHG sources and methodologies", "Wichtigste THG-Quellen und -Methoden", TEXT),
}
MANDATORY_INDICATORS = tuple(f"S.{n}" for n in range(1, 10))
SUPPLEMENTARY_INDICATORS = tuple(f"S.{n}" for n in range(10, 17))
# Art. 4(2) VO (EU) 2025/422: Table 3 is required where the yearly energy consumption in S.8 "exceeds 500 000
# kilowatt-hours" ("500 000 Kilowattstunden überschreitet").
ENERGY_THRESHOLD_KWH = 500_000

# ISO 4217 currency codes in use, without the codes for testing (XTS) and for no currency (XXX). The list was
# compiled offline from the codes the ISO 4217 maintenance agency publishes and was not re-read online; a code
# introduced or withdrawn since may be missing or still listed.
_ISO_4217_CODES = """
    AED AFN ALL AMD ANG AOA ARS AUD AWG AZN BAM BBD BDT BGN BHD BIF BMD BND BOB BOV BRL BSD BTN BWP BYN BZD
    CAD CDF CHE CHF CHW CLF CLP CNY COP COU CRC CUP CVE CZK DJF DKK DOP DZD EGP ERN ETB EUR FJD FKP GBP GEL
    GHS GIP GMD GNF GTQ GYD HKD HNL HTG HUF IDR ILS INR IQD IRR ISK JMD JOD JPY KES KGS KHR KMF KPW KRW KWD
    KYD KZT LAK LBP LKR LRD LSL LYD MAD MDL MGA MKD MMK MNT MOP MRU MUR MVR MWK MXN MXV MYR MZN NAD NGN NIO
    NOK NPR NZD OMR PAB PEN PGK PHP PKR PLN PYG QAR RON RSD RUB RWF SAR SBD SCR SDG SEK SGD SHP SLE SOS SRD
    SSP STN SVC SYP SZL THB TJS TMT TND TOP TRY TTD TWD TZS UAH UGX USD USN UYI UYU UYW UZS VED VES VND VUV
    WST XAF XAG XAU XBA XBB XBC XBD XCD XCG XDR XOF XPD XPF XPT XSU XUA YER ZAR ZMW ZWG
"""
ISO_4217 = frozenset(_ISO_4217_CODES.split())

# The EU Member States by ISO 3166-1 alpha-2 code (with EL, the EU's code for Greece) and by English and
# German name. The closed list of the taxonomy is not printed in the OJ text; MiCAR also applies in Iceland,
# Liechtenstein and Norway under the EEA Agreement, so those three count too.
MEMBER_STATES_BY_CODE: dict[str, tuple[str, ...]] = {
    "AT": ("Austria", "Österreich"),
    "BE": ("Belgium", "Belgien"),
    "BG": ("Bulgaria", "Bulgarien"),
    "HR": ("Croatia", "Kroatien"),
    "CY": ("Cyprus", "Zypern"),
    "CZ": ("Czechia", "Czech Republic", "Tschechien", "Tschechische Republik"),
    "DK": ("Denmark", "Dänemark"),
    "EE": ("Estonia", "Estland"),
    "FI": ("Finland", "Finnland"),
    "FR": ("France", "Frankreich"),
    "DE": ("Germany", "Deutschland"),
    "GR": ("Greece", "Griechenland"),
    "EL": ("Greece", "Griechenland"),
    "HU": ("Hungary", "Ungarn"),
    "IE": ("Ireland", "Irland"),
    "IT": ("Italy", "Italien"),
    "LV": ("Latvia", "Lettland"),
    "LT": ("Lithuania", "Litauen"),
    "LU": ("Luxembourg", "Luxemburg"),
    "MT": ("Malta",),
    "NL": ("Netherlands", "The Netherlands", "Niederlande"),
    "PL": ("Poland", "Polen"),
    "PT": ("Portugal",),
    "RO": ("Romania", "Rumänien"),
    "SK": ("Slovakia", "Slowakei"),
    "SI": ("Slovenia", "Slowenien"),
    "ES": ("Spain", "Spanien"),
    "SE": ("Sweden", "Schweden"),
    "IS": ("Iceland", "Island"),
    "LI": ("Liechtenstein",),
    "NO": ("Norway", "Norwegen"),
}
