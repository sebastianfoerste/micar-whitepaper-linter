"""Marketing communications for crypto-assets other than ARTs and EMTs (Art. 7 MiCAR).

A marketing communication is the second kind of document the linter reads (ADR 0009). Its loader puts the
whole text a reader sees into one section, `marketing_communication`, which every rule below reads;
MARKETING.CONSISTENCY also reads the white paper given with it and does not run without one. Art. 29 MiCAR
(asset-referenced tokens) and Art. 53 MiCAR (e-money tokens) set requirements of their own, which these rules
do not cover.

The wording of Art. 7(1) MiCAR, and of the statement of point (e) with its second subparagraph, was read in
the Official Journal text in English and German (OJ L 150, 9.6.2023, CELEX 32023R1114) as the Publications
Office Cellar served it on 2026-11-25. The linter cannot see placement, prominence or layout.
"""

from __future__ import annotations

from micar_linter.rules.base import Rule, Severity

MARKETING_SECTION = "marketing_communication"

# Art. 7(1)(e), first subparagraph: the statement, word for word. Its second sentence names the offeror; where
# the person seeking admission to trading or the operator of the trading platform prepared the communication,
# the second subparagraph puts that person in place of "offeror", so the check takes the part of the second
# sentence common to all three and linter.py checks the person before it.
NOT_REVIEWED_STATEMENT_EN = (
    "this crypto-asset marketing communication has not been reviewed or approved by any competent authority "
    "in any member state of the european union"
)
RESPONSIBILITY_CLAUSE_EN = (
    "of the crypto-asset is solely responsible for the content of this crypto-asset marketing communication"
)
NOT_REVIEWED_STATEMENT_DE = (
    "diese kryptowert-marketingmitteilung wurde von keiner zuständigen behörde eines mitgliedstaats der "
    "europäischen union geprüft oder genehmigt"
)
RESPONSIBILITY_CLAUSE_DE = (
    "trägt die alleinige verantwortung für den inhalt dieser kryptowert-marketingmitteilung"
)

# Art. 7(1)(b): wording that can make the information unfair, unclear or misleading. Each pattern has one
# named group, which the finding reports with underscores read as spaces, never the matched text. A negation
# right before the claim ("no guaranteed returns", "not risk-free", "has not been reviewed or approved by")
# does not count; one further back in the sentence is not recognised, so such a sentence goes to review.
GUARANTEED_RETURN_EN = (
    r"(?P<guaranteed_return>(?<!\bnot )(?<!\bno )(?<!\bnever )(?<!\bwithout )(?<!\bnot a )(?<!\bnot an )"
    r"\bguarantee(?:d|s)?\s+(?:(?:a|an|the)\s+)?(?:\w+\s+){0,2}?"
    r"(?:returns?|profits?|yields?|income|gains?|interest|payouts?|rewards?)\b"
    r"|\b(?:returns?|profits?|yields?|income|gains?|payouts?|rewards?)\s+(?:is|are|will\s+be)\s+guaranteed\b)"
)
NO_RISK_EN = (
    r"(?P<no_risk>(?<!\bnot )(?<!\bnever )\b(?:risk[- ]free|riskless|zero[- ]risk|no[- ]risk)\b"
    r"(?![- ](?:warnings?|disclosures?|statements?)\b)"
    r"|(?<!\bnot )\bwithout\s+(?:any\s+)?risks?\b)"
)
RISING_PRICE_EN = (
    r"(?P<rising_price>\b(?:price|value|worth)\s+(?:of\s+(?:[\w$-]+\s+){1,3})?"
    r"(?:will|is\s+going\s+to|is\s+set\s+to|is\s+expected\s+to)\s+(?:\w+\s+)?"
    r"(?:rise|increase|grow|climb|double|triple|multiply|skyrocket|soar|go\s+up)\b"
    r"|\bwill\s+(?:rise|increase|grow|climb|soar|skyrocket)\s+in\s+(?:value|price)\b"
    r"|\bto\s+the\s+moon\b|\b\d+\s*x\s+(?:returns?|gains?|profits?)\b)"
)
APPROVAL_CLAIM_EN = (
    r"(?P<approval_claim>(?<!\bnot )(?<!\bnot been )(?<!\bnever been )(?<!\bor )(?<!\bnor )"
    r"\b(?:approved|endorsed|certified|vetted|sanctioned)\s+by\s+(?:(?:the|a|an|any)\s+)?"
    r"(?:bafin|esma|eba|ecb|sec|fca|amf|cssf|consob|cnmv|cysec|mfsa|afm|central\s+bank|"
    r"competent\s+authorit(?:y|ies)|financial\s+(?:regulator|supervisor|authority)|regulators?|supervisors?)\b"
    r"|\bmicar?[- ](?:approved|certified)\b|\bapproved\s+under\s+micar?\b)"
)
GUARANTEED_RETURN_DE = (
    r"(?P<garantierte_rendite>(?<!\bkeine )(?<!\bnicht )(?<!\bohne )(?<!\bkeinen )"
    r"\bgarantiert(?:e|en|er|es)?\s+(?:\w+\s+){0,2}?"
    r"(?:renditen?|gewinnen?|gewinne?|erträgen?|ertrag|zinsen|ausschüttungen?|auszahlungen?|belohnungen?)\b"
    r"|\b(?:renditen?|gewinne?|erträge|ertrag|zinsen|auszahlungen?)\s+(?:ist|sind|wird|werden)\s+garantiert\b)"
)
NO_RISK_DE = (
    r"(?P<kein_risiko>(?<!\bnicht )\b(?:risikofrei\w*|risikolos\w*|null\s+risiko)\b"
    r"|(?<!\bnicht )\bohne\s+(?:jedes\s+|jegliches\s+)?risiko\b|\bkein(?:erlei)?\s+risiko\b)"
)
RISING_PRICE_DE = (
    r"(?P<steigender_kurs>\b(?:preis|kurs|wert)\s+(?:\w+\s+){0,3}?wird\s+(?:\w+\s+){0,2}?"
    r"(?:steigen|zulegen|wachsen|sich\s+verdoppeln|explodieren)\b"
    r"|\bwird\s+(?:\w+\s+){0,2}?im\s+(?:wert|preis|kurs)\s+steigen\b|\bto\s+the\s+moon\b)"
)
APPROVAL_CLAIM_DE = (
    r"(?P<behauptete_genehmigung>\b(?:von|durch)\s+(?:(?:der|die|einer)\s+)?"
    r"(?:bafin|esma|eba|ezb|zuständigen\s+behörde|aufsicht(?:sbehörde)?|finanzaufsicht)\s+(?:\w+\s+){0,2}?"
    r"(?:genehmigt|gebilligt|zertifiziert)\b|\bmicar?-(?:genehmigt|zertifiziert)\b)"
)

MARKETING_RULES: tuple[Rule, ...] = (
    Rule(
        rule_id="MARKETING.IDENTIFIABLE",
        citation="Art. 7 Abs. 1 Buchst. a MiCAR",
        section=MARKETING_SECTION,
        label="Clearly identifiable as a marketing communication (a label in the title or the opening words)",
        min_words=0,
        severity=Severity.MAJOR,
    ),
    Rule(
        rule_id="MARKETING.MISLEADING_CLAIMS",
        citation="Art. 7 Abs. 1 Buchst. b MiCAR",
        section=MARKETING_SECTION,
        label=(
            "Fair, clear and not misleading: listed claims of guaranteed returns, no risk, rising prices or "
            "approval (wording only)"
        ),
        prohibited_patterns=(GUARANTEED_RETURN_EN, NO_RISK_EN, RISING_PRICE_EN, APPROVAL_CLAIM_EN),
        prohibited_patterns_de=(GUARANTEED_RETURN_DE, NO_RISK_DE, RISING_PRICE_DE, APPROVAL_CLAIM_DE),
        min_words=0,
        severity=Severity.MAJOR,
    ),
    Rule(
        rule_id="MARKETING.CONSISTENCY",
        citation="Art. 7 Abs. 1 Buchst. c MiCAR",
        section=MARKETING_SECTION,
        label=(
            "Consistent with the white paper: identifiers, dates, percentages, amounts and contact details "
            "found in the white paper"
        ),
        min_words=0,
        severity=Severity.MAJOR,
    ),
    Rule(
        rule_id="MARKETING.WHITE_PAPER_AND_CONTACT",
        citation="Art. 7 Abs. 1 Buchst. d MiCAR",
        section=MARKETING_SECTION,
        label=(
            "States that a white paper has been published and gives a website, a telephone number and an "
            "e-mail address"
        ),
        min_words=0,
        severity=Severity.BLOCKER,
    ),
    Rule(
        rule_id="MARKETING.NOT_REVIEWED_STATEMENT",
        citation="Art. 7 Abs. 1 Buchst. e MiCAR",
        section=MARKETING_SECTION,
        label=(
            "Statement that no competent authority has reviewed or approved the communication (wording only)"
        ),
        required_terms=(NOT_REVIEWED_STATEMENT_EN, RESPONSIBILITY_CLAUSE_EN),
        required_terms_de=(NOT_REVIEWED_STATEMENT_DE, RESPONSIBILITY_CLAUSE_DE),
        min_words=0,
        severity=Severity.BLOCKER,
    ),
)

MARKETING_RULE_IDS = frozenset(rule.rule_id for rule in MARKETING_RULES)
