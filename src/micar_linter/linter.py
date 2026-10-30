"""Core lint engine."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date

from micar_linter.anchors import SourceAnchor, build_source_anchors
from micar_linter.lei import PARTY_SECTIONS, has_valid_check_digits, leis_by_section, other_person_leis
from micar_linter.placeholders import is_placeholder
from micar_linter.rules import RULESETS
from micar_linter.rules.base import Finding, Rule, Severity
from micar_linter.template_fields import FIELD_NAMES
from micar_linter.whitepaper import Whitepaper, WhitepaperType


@dataclass(frozen=True)
class Report:
    """The result of linting a white paper."""

    title: str
    whitepaper_type: WhitepaperType
    findings: tuple[Finding, ...]
    warnings: tuple[str, ...] = field(default_factory=tuple)
    source_anchors: dict[str, SourceAnchor] = field(default_factory=dict)

    @property
    def passed(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.status == "pass")

    @property
    def needs_review(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.status == "review")

    @property
    def missing(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.status == "missing")

    @property
    def blockers(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if not f.passed and f.rule.severity is Severity.BLOCKER)

    @property
    def is_clean(self) -> bool:
        return all(f.passed for f in self.findings)


class Linter:
    """Applies a MiCAR rule set to a parsed white paper."""

    def __init__(self, rules: tuple[Rule, ...]) -> None:
        self.rules = rules

    def lint(self, whitepaper: Whitepaper) -> tuple[Finding, ...]:
        return tuple(self._apply(rule, whitepaper) for rule in self.rules)

    @staticmethod
    def _apply(rule: Rule, whitepaper: Whitepaper) -> Finding:
        if rule.rule_id == "COMMON.IXBRL_TAGGING":
            return _ixbrl_finding(rule, whitepaper)

        if rule.rule_id == "ANNEX_II.G.DEPOSIT_FLOOR_REVIEW":
            return _deposit_floor_finding(rule, whitepaper)

        if rule.rule_id in NOT_APPROVED_STATEMENT_RULE_IDS:
            statement = _not_approved_statement_finding(rule, whitepaper)
            if statement is not None:
                return statement

        if rule.rule_id == "COMMON.LEI_CHECK_DIGITS":
            return _lei_check_digits_finding(rule, whitepaper)

        if rule.rule_id == "COMMON.LEI_CONSISTENCY":
            return _lei_consistency_finding(rule, whitepaper)

        if rule.rule_id == "COMMON.NOTIFICATION_DATE":
            return _notification_date_finding(rule, whitepaper)

        if rule.rule_id == "COMMON.LANGUAGE":
            return _language_finding(rule, whitepaper)

        is_de = whitepaper.language == "de"

        text = whitepaper.section(rule.section)
        word_count = _count_words(text)

        absent = _absent(text, is_de)
        if absent:
            return Finding(rule=rule, status="missing", word_count=0, issues=(absent,))

        issues: list[str] = []
        # PDF, Markdown and DOCX loaders keep line breaks, so a statutory sentence that wraps
        # across lines must still match a single-line term.
        text = _collapse_whitespace(text)
        normalized = text.lower()

        if word_count < rule.min_words:
            if is_de:
                issues.append(
                    f"Abschnitt ist zu kurz: {word_count} Wörter, mindestens {rule.min_words} erwartet."
                )
            else:
                issues.append(f"Section is thin: {word_count} words, expected at least {rule.min_words}.")

        # Bilingual required terms
        req_terms = rule.required_terms_de if (is_de and rule.required_terms_de) else rule.required_terms
        missing_terms = [term for term in req_terms if term.lower() not in normalized]

        # Bilingual required regex patterns. A pattern with a named group stands for a listed term
        # that a plain substring would find inside other words ("fee" in "feedback"): when it does not
        # match, the group's name, with underscores read as spaces, is reported with the missing terms.
        req_patterns = (
            rule.required_patterns_de if (is_de and rule.required_patterns_de) else rule.required_patterns
        )
        pattern_issues: list[str] = []
        for pattern in req_patterns:
            try:
                compiled = re.compile(pattern, re.IGNORECASE)
            except re.error as exc:
                msg = (
                    f"Ungültiges gefordertes Regex-Muster '{pattern}': {exc}"
                    if is_de
                    else f"Invalid required pattern regex '{pattern}': {exc}"
                )
                pattern_issues.append(msg)
                continue
            if not compiled.search(text):
                names = [name.replace("_", " ") for name in compiled.groupindex]
                if names:
                    missing_terms.extend(names)
                    continue
                msg = (
                    f"Fehlendes gefordertes Muster: '{pattern}'."
                    if is_de
                    else f"Missing required pattern: '{pattern}'."
                )
                pattern_issues.append(msg)

        if missing_terms:
            prefix = "Fehlende Begriffe: " if is_de else "Missing review terms: "
            issues.append(prefix + ", ".join(missing_terms) + ".")
        issues.extend(pattern_issues)

        # Bilingual prohibited regex patterns. A pattern with a named group stands for wording that turns a
        # required statement around; the finding reports the group's name, with underscores read as spaces,
        # and never the matched draft text.
        proh_patterns = (
            rule.prohibited_patterns_de
            if (is_de and rule.prohibited_patterns_de)
            else rule.prohibited_patterns
        )
        for pattern in proh_patterns:
            try:
                compiled = re.compile(pattern, re.IGNORECASE)
            except re.error as exc:
                msg = (
                    f"Ungültiges unzulässiges Regex-Muster '{pattern}': {exc}"
                    if is_de
                    else f"Invalid prohibited pattern regex '{pattern}': {exc}"
                )
                issues.append(msg)
                continue
            found = compiled.search(text)
            if found:
                names = [
                    name.replace("_", " ") for name, value in found.groupdict().items() if value is not None
                ]
                if names:
                    msg = (
                        f"Unzulässige Formulierung gefunden: {', '.join(names)}."
                        if is_de
                        else f"Prohibited wording found: {', '.join(names)}."
                    )
                else:
                    msg = (
                        f"Unzulässiger Inhalt gefunden: '{pattern}'."
                        if is_de
                        else f"Prohibited content matched: '{pattern}'."
                    )
                issues.append(msg)

        issues.extend(_rule_specific_issues(rule, normalized, is_de))
        issues.extend(_placeholder_field_issues(rule, whitepaper, is_de))

        status = "review" if issues else "pass"
        return Finding(rule=rule, status=status, word_count=word_count, issues=tuple(issues))


def lint_whitepaper(whitepaper: Whitepaper) -> Report:
    """Convenience entry point: pick the right ruleset and lint."""
    rules = RULESETS[whitepaper.type]
    findings = Linter(rules).lint(whitepaper)

    # Check for unrecognized/misspelled sections. The LEI rules read every party section in every regime: an
    # ART white paper names the persons other than the issuer who offer the token in its offeror section.
    valid_sections = {rule.section for rule in rules} | set(PARTY_SECTIONS)
    warnings: list[str] = list(whitepaper.metadata.get("extraction_notes", ()))
    for section_name in whitepaper.sections:
        if section_name not in valid_sections:
            warnings.append(
                f"Unrecognized section key '{section_name}' in draft sections. "
                "Ensure it matches required section keys."
            )

    return Report(
        title=whitepaper.title,
        whitepaper_type=whitepaper.type,
        findings=findings,
        warnings=tuple(warnings),
        source_anchors=build_source_anchors(whitepaper, findings),
    )


def _count_words(text: str) -> int:
    return sum(1 for word in text.split() if word.strip())


_LINE_END_HYPHEN = re.compile(r"-[ \t]*(?:\r\n|\r|\n)\s*")
_WHITESPACE_RUN = re.compile(r"\s+")


def _collapse_whitespace(text: str) -> str:
    """Join a hyphenated compound broken at a line end, then collapse every whitespace run."""
    return _WHITESPACE_RUN.sub(" ", _LINE_END_HYPHEN.sub("-", text)).strip()


# Art. 6(3) and Art. 51(3) MiCAR prescribe the first-page statement word for word. The
# English wording was checked against the EUR-Lex text of Art. 6(3) and 51(3) MiCAR as
# mirrored in legalize-dev/legalize-eu (CELEX 32023R1114). The German wording has not been
# checked against the German Official Journal text, so a German draft is referred to review
# and never passes.
NOT_APPROVED_STATEMENT_RULE_IDS = frozenset(
    {"ANNEX_I.NOT_APPROVED_STATEMENT", "ANNEX_III.NOT_APPROVED_STATEMENT"}
)
_BOOLEAN_FIELD_VALUES = frozenset({"true", "false", "yes", "no", "ja", "nein"})


def _not_approved_statement_finding(rule: Rule, whitepaper: Whitepaper) -> Finding | None:
    """Return the finding where the generic term check would mislead, otherwise None."""
    is_de = whitepaper.language == "de"
    text = whitepaper.section(rule.section)
    # Empty and placeholder-only text go to the shared checks, which report them missing.
    if not text.strip() or is_placeholder(text):
        return None
    words = _count_words(text)
    emt = rule.rule_id.startswith("ANNEX_III.")
    article_de = "Art. 51 Abs. 3" if emt else "Art. 6 Abs. 3"
    article_en = "Art. 51(3)" if emt else "Art. 6(3)"
    if _collapse_whitespace(text).lower().strip(" .'\"") in _BOOLEAN_FIELD_VALUES:
        msg = (
            f"Das Feld enthält nur einen Ja/Nein-Wert, nicht den Wortlaut nach {article_de} MiCAR. "
            "Wortlaut und Platzierung auf der ersten Seite manuell prüfen."
            if is_de
            else f"The field holds only a yes/no value, not the {article_en} MiCAR wording. "
            "Check the wording and its first-page placement manually."
        )
        return Finding(rule=rule, status="review", word_count=words, issues=(msg,))
    if is_de:
        msg = (
            f"Der deutsche Wortlaut der Erklärung nach {article_de} MiCAR ist in diesem Linter "
            "noch nicht gegen die deutsche Fassung im Amtsblatt geprüft. Wortlaut und "
            "Platzierung auf der ersten Seite manuell mit dem Amtsblatt abgleichen."
        )
        return Finding(rule=rule, status="review", word_count=words, issues=(msg,))
    return None


# Art. 6(3), second subparagraph, MiCAR: the statement names the offeror, the person seeking
# admission to trading or the operator of the trading platform (Table 2 field 02 of
# Implementing Regulation (EU) 2024/2984 prints all three sentences).
_TITLE_II_RESPONSIBILITY_CLAUSE = "of the crypto-asset is solely responsible"
_TITLE_II_RESPONSIBLE_PERSON = re.compile(
    r"\b(?:offeror|person seeking admission to trading|operator of the trading platform) "
    + _TITLE_II_RESPONSIBILITY_CLAUSE
)


def _rule_specific_issues(rule: Rule, normalized: str, is_de: bool) -> list[str]:
    """Issues a rule needs beyond its terms and patterns; normalized is lowercase, one line."""
    if rule.rule_id == "ANNEX_I.NOT_APPROVED_STATEMENT" and not is_de:
        names_clause = _TITLE_II_RESPONSIBILITY_CLAUSE in normalized
        if names_clause and not _TITLE_II_RESPONSIBLE_PERSON.search(normalized):
            return [
                "Art. 6(3) MiCAR names the offeror, the person seeking admission to trading or the "
                "operator of the trading platform as solely responsible; the statement names "
                "someone else."
            ]
    return []


def _placeholder_field_issues(rule: Rule, whitepaper: Whitepaper, is_de: bool) -> list[str]:
    """Name the numbered fields of the rule's section that hold only a placeholder.

    The loader adds such a field's placeholder without its label, so the section's other fields
    could otherwise satisfy the rule on their own. The issue names each field by its number and,
    in English, the template's name for it, never by text from the draft.
    """
    numbers = whitepaper.metadata.get("placeholder_fields", {}).get(rule.section, ())
    if not numbers:
        return []
    if is_de:
        if len(numbers) == 1:
            return [f"Feld {numbers[0]} enthält nur einen Platzhalter wie TBD."]
        return [f"Felder {_listed(numbers, 'und')} enthalten nur Platzhalter wie TBD."]
    names = FIELD_NAMES[whitepaper.type]
    fields = [f"{number} ({names[number]})" if number in names else number for number in numbers]
    if len(fields) == 1:
        return [f"Field {fields[0]} holds only a placeholder such as TBD."]
    return [f"Fields {_listed(fields, 'and')} hold only placeholders such as TBD."]


def _listed(items: list[str] | tuple[str, ...], conjunction: str) -> str:
    """'A', 'A and B', 'A, B and C'."""
    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])} {conjunction} {items[-1]}"


def _absent(text: str, is_de: bool) -> str | None:
    """The issue that makes a section Missing (empty, or placeholders such as TBD only), else None."""
    if not text.strip():
        return "Abschnitt ist leer oder fehlt." if is_de else "Section is empty or absent."
    if is_placeholder(text):
        return (
            "Abschnitt enthält nur Platzhalter wie TBD oder TBC."
            if is_de
            else "Section holds only placeholder text such as TBD or TBC."
        )
    return None


_PERCENTAGE_PATTERN = re.compile(r"(?<![\d.,])(\d{1,3}(?:[.,]\d+)?)\s*%(?!\d)")


def _percentage_candidates(text: str) -> tuple[str, ...]:
    """Return unique percentage strings without interpreting their meaning."""
    candidates: list[str] = []
    for match in _PERCENTAGE_PATTERN.finditer(text):
        candidate = f"{match.group(1)}%"
        if candidate not in candidates:
            candidates.append(candidate)
    return tuple(candidates)


def _ixbrl_finding(rule: Rule, whitepaper: Whitepaper) -> Finding:
    """Format compliance fails closed.

    Only a source that actually went through iXBRL validation can pass. A draft
    format (JSON, DOCX, PDF, Markdown) cannot satisfy the notification format, so
    it leaves the blocker open instead of reporting a pass it has not evidenced.
    A saved iXBRL viewer page is not validated either: its text is a viewer's
    rendering of the document.
    """
    is_de = whitepaper.language == "de"
    metadata = whitepaper.metadata
    if not bool(metadata.get("ixbrl_validated", False)):
        source_file = str(metadata.get("source_file", ""))
        if metadata.get("script_packed_source"):
            msg = (
                "Gespeicherte iXBRL-Viewer-Seite: Die inhaltlichen Prüfungen beruhen auf dem Text, wie der "
                "Viewer ihn darstellt. Diese Darstellung ist nicht das XHTML-Dokument selbst. "
                "Die Inline-XBRL-Prüfung wurde daher nicht ausgeführt; "
                "die Formatkonformität ist nicht nachgewiesen."
                if is_de
                else "Saved iXBRL viewer page: the content checks read the text as the viewer renders it. "
                "That rendering is not the XHTML document itself, so Inline XBRL validation did not run; "
                "format compliance is unverified."
            )
        elif source_file.lower().endswith((".xhtml", ".html")):
            msg = (
                "Inline-XBRL-Prüfung wurde für diese XHTML-Quelle nicht ausgeführt; "
                "die Formatkonformität ist nicht nachgewiesen."
                if is_de
                else "Inline XBRL validation did not run for this XHTML source; "
                "format compliance is unverified."
            )
        else:
            msg = (
                "Entwurfsformat: Die Notifizierung verlangt XHTML mit Inline-XBRL-Tagging. "
                "Dieses Format kann die Anforderung nicht erfuellen; die inhaltlichen "
                "Pruefungen gelten weiterhin."
                if is_de
                else "Draft format: notification requires XHTML with Inline XBRL tagging. "
                "This format cannot satisfy that requirement; the content checks still apply."
            )
        return Finding(rule=rule, status="missing", word_count=0, issues=(msg,))

    issues = tuple(metadata.get("ixbrl_issues", ()))
    if issues:
        return Finding(rule=rule, status="review", word_count=0, issues=issues)
    return Finding(rule=rule, status="pass", word_count=0, issues=())


def _deposit_floor_finding(rule: Rule, whitepaper: Whitepaper) -> Finding:
    """The substantive deposit floor is fact-dependent, so it never auto-passes.

    Art. 36(4)(d) MiCAR sets the 30 % candidate floor. Art. 45(7)(b) sets the
    60 % candidate floor for significant ARTs. Both figures bind EBA's
    regulatory technical standards, not the issuer directly. A non-significant
    ART reaches the 60 % figure only where the competent authority extends
    Art. 45(3) to it under Art. 35(4); Art. 45(7)(b) then specifies the content
    of that Art. 45(3) policy (EBA/RTS/2024/10, final report para. 23). Draft
    text and metadata cannot establish legal compliance, so any disclosed
    percentage remains subject to lawyer review.
    """
    is_de = whitepaper.language == "de"
    metadata = whitepaper.metadata
    significant = metadata.get("art_significant")
    references_currency = metadata.get("references_official_currency")
    authority_requires_45_7b = metadata.get("article_45_7b_required_by_authority")
    text = whitepaper.section(rule.section)
    words = _count_words(text)

    unknown: list[str] = []
    if not isinstance(references_currency, bool):
        unknown.append("references_official_currency")
    if not isinstance(significant, bool):
        unknown.append("art_significant")
    if unknown:
        msg = (
            "Entwurfsangabe zur rechtlichen Einordnung fehlt oder ist ungueltig ("
            + ", ".join(unknown)
            + "); die anwendbare Mindestquote kann nicht bestimmt werden. Die "
            "Angabe bleibt bis zur Bestaetigung durch einen Juristen offen."
            if is_de
            else "Draft characterisation assertion missing or invalid ("
            + ", ".join(unknown)
            + "); the applicable minimum share cannot be determined. The assertion "
            "remains pending lawyer confirmation."
        )
        return Finding(rule=rule, status="review", word_count=words, issues=(msg,))

    if not references_currency:
        msg = (
            "Die Entwurfsangabe lautet, dass der Token nicht auf eine amtliche "
            "Waehrung referenziert. Anwendbarkeit und rechtliche Einordnung muessen "
            "durch einen Juristen bestaetigt werden."
            if is_de
            else "The draft asserts that the token does not reference an official "
            "currency. Applicability and legal characterisation require lawyer "
            "confirmation."
        )
        return Finding(rule=rule, status="review", word_count=words, issues=(msg,))

    if significant:
        threshold = 60
        basis = "Art. 45 Abs. 7 Buchst. b MiCAR" if is_de else "Art. 45(7)(b) MiCAR"
    else:
        if not isinstance(authority_requires_45_7b, bool):
            msg = (
                "Die Entwurfsangabe article_45_7b_required_by_authority fehlt oder "
                "ist ungueltig. Bei einem nicht signifikanten ART ist durch einen "
                "Juristen zu pruefen, ob die zustaendige Behoerde nach Art. 35 Abs. 4 "
                "MiCAR die Einhaltung von Art. 45 Abs. 3 angeordnet hat; erst dann "
                "greift die Mindestquote nach Art. 45 Abs. 7 Buchst. b."
                if is_de
                else "Draft characterisation assertion "
                "article_45_7b_required_by_authority is missing or invalid. For a "
                "non-significant ART, a lawyer must confirm whether the competent "
                "authority has extended Art. 45(3) to the issuer under Art. 35(4) "
                "MiCAR; only then does the Art. 45(7)(b) floor apply."
            )
            return Finding(rule=rule, status="review", word_count=words, issues=(msg,))
        if authority_requires_45_7b:
            threshold = 60
            basis = (
                "Art. 35 Abs. 4 i.V.m. Art. 45 Abs. 3 und Abs. 7 Buchst. b MiCAR"
                if is_de
                else "Arts. 35(4), 45(3) and 45(7)(b) MiCAR"
            )
        else:
            threshold = 30
            basis = "Art. 36 Abs. 4 Buchst. d MiCAR" if is_de else "Art. 36(4)(d) MiCAR"

    candidates = _percentage_candidates(text)
    if candidates:
        listed = ", ".join(candidates)
        msg = (
            f"Prozentangabe(n) im Entwurf erkannt: {listed}. Die Entwurfsangaben "
            f"weisen auf eine Mindestquote von {threshold} % ({basis}) hin. Ein Jurist "
            "muss Anwendbarkeit, Aussagekontext und Erfuellung bestaetigen."
            if is_de
            else f"Draft percentage candidate(s) detected: {listed}. The draft "
            f"characterisation indicates a {threshold}% candidate floor ({basis}). "
            "A lawyer must confirm applicability, statement context, and compliance."
        )
        return Finding(rule=rule, status="review", word_count=words, issues=(msg,))

    msg = (
        f"Keine Prozentangabe zur Einlagenquote erkannt. Die Entwurfsangaben weisen "
        f"auf eine Mindestquote von {threshold} % ({basis}) hin. Juristische Pruefung "
        "der Anwendbarkeit bleibt erforderlich."
        if is_de
        else "No deposit-share percentage was detected. The draft characterisation "
        f"indicates a {threshold}% candidate floor ({basis}). Lawyer confirmation "
        "of applicability remains required."
    )
    return Finding(rule=rule, status="missing", word_count=words, issues=(msg,))


def _other_identifier_note(is_de: bool) -> str:
    return (
        "Nr. 5 der Teile A bis C von Anhang I und von Teil A der Anhänge II und III lässt statt der LEI eine "
        "andere nach geltendem nationalem Recht erforderliche Kennung zu. Ob der Entwurf für jeden "
        "Beteiligten eine dieser Kennungen angibt, ist von Hand zu prüfen."
        if is_de
        else "Point 5 of Annex I Parts A to C and of Annex II and III Part A allows another identifier "
        "required pursuant to applicable national law in place of the LEI. Whether the draft gives one of "
        "them for each party needs checking by hand."
    )


def _no_lei_finding(rule: Rule, whitepaper: Whitepaper, msg: str) -> Finding:
    """Fails closed without an LEI: Missing when no party section has text, Review when one has.

    Point 5 of each party Part allows another identifier required pursuant to applicable national law
    in place of the LEI, and VO (EU) 2024/2984 asks for the LEI "where available", so a party section
    without one goes to a reviewer instead of counting as absent.
    """
    texts = ((whitepaper.sections.get(section) or "").strip() for section in PARTY_SECTIONS)
    if not any(text and not is_placeholder(text) for text in texts):
        return Finding(rule=rule, status="missing", word_count=0, issues=(msg,))
    note = _other_identifier_note(whitepaper.language == "de")
    return Finding(rule=rule, status="review", word_count=0, issues=(msg, note))


def _lei_check_digits_finding(rule: Rule, whitepaper: Whitepaper) -> Finding:
    """Fails closed: a draft without any LEI cannot show valid check digits."""
    is_de = whitepaper.language == "de"
    found = leis_by_section(whitepaper.sections)
    if not found:
        msg = (
            "Im Entwurf wurde keine Rechtsträgerkennung (LEI, 20 Zeichen nach ISO 17442) gefunden; "
            "die Prüfziffern konnten nicht geprüft werden."
            if is_de
            else "No Legal Entity Identifier (20 characters, ISO 17442) was found in the draft, "
            "so its check digits could not be checked."
        )
        return _no_lei_finding(rule, whitepaper, msg)
    issues = []
    for section, codes in found.items():
        for code in codes:
            if not has_valid_check_digits(code):
                issues.append(
                    f"LEI '{code}' im Abschnitt '{section}' hat ungültige Prüfziffern "
                    "(ISO/IEC 7064 MOD 97-10)."
                    if is_de
                    else f"LEI '{code}' in section '{section}' fails the ISO/IEC 7064 MOD 97-10 check digits."
                )
    return Finding(rule=rule, status="review" if issues else "pass", word_count=0, issues=tuple(issues))


def _lei_consistency_finding(rule: Rule, whitepaper: Whitepaper) -> Finding:
    """Every valid LEI in the draft must belong to a party section; the issuer states one LEI.

    An LEI that the draft gives for a person other than the parties (other_person_leis: the provider in
    charge of the placing, a custodian, a person other than the issuer) is neither compared with the party
    sections nor counted as an issuer LEI. Fails closed when no party section carries a valid LEI (see
    _no_lei_finding). Invalid codes are left to COMMON.LEI_CHECK_DIGITS so that one typo is not reported
    twice.
    """
    is_de = whitepaper.language == "de"
    valid = {
        section: tuple(code for code in codes if has_valid_check_digits(code))
        for section, codes in leis_by_section(whitepaper.sections).items()
    }
    valid = {section: codes for section, codes in valid.items() if codes}
    party_codes = {code for section in PARTY_SECTIONS for code in valid.get(section, ())}
    if not party_codes:
        msg = (
            "Keine gültige LEI in den Abschnitten issuer, offeror oder trading_platform_operator; "
            "die Übereinstimmung kann nicht geprüft werden."
            if is_de
            else "No valid LEI was found in the issuer, offeror or trading_platform_operator sections, "
            "so consistency cannot be checked."
        )
        return _no_lei_finding(rule, whitepaper, msg)
    others = {code for text in whitepaper.sections.values() for code in other_person_leis(str(text))}
    issues = []
    issuer_codes = [code for code in valid.get("issuer", ()) if code not in others]
    if len(issuer_codes) > 1:
        issues.append(
            f"Der Abschnitt 'issuer' nennt {len(issuer_codes)} verschiedene LEIs; ein Emittent hat eine LEI."
            if is_de
            else f"Section 'issuer' names {len(issuer_codes)} different LEIs; an issuer has one LEI."
        )
    for section, codes in valid.items():
        if section in PARTY_SECTIONS:
            continue
        for code in codes:
            if code not in party_codes and code not in others:
                issues.append(
                    f"LEI '{code}' im Abschnitt '{section}' erscheint in keinem Abschnitt zu den Beteiligten."
                    if is_de
                    else f"LEI '{code}' in section '{section}' appears in no party section "
                    "(issuer, offeror, trading_platform_operator)."
                )
    return Finding(rule=rule, status="review" if issues else "pass", word_count=0, issues=tuple(issues))


# Since 23 December 2025, Implementing Regulation (EU) 2024/2984 has white papers report the date of
# notification as YYYY-MM-DD (field 01 of Table 2, I.01 of Tables 3 and 4). Drafts also write 02.03.2026,
# 2 March 2026 or 2. März 2026.
_MONTH_NAMES: dict[int, tuple[str, ...]] = {
    1: ("january", "januar", "jänner", "jan", "jän"),
    2: ("february", "februar", "feber", "feb"),
    3: ("march", "märz", "maerz", "mar", "mär", "mrz"),
    4: ("april", "apr"),
    5: ("may", "mai"),
    6: ("june", "juni", "jun"),
    7: ("july", "juli", "jul"),
    8: ("august", "aug"),
    9: ("september", "sept", "sep"),
    10: ("october", "oktober", "oct", "okt"),
    11: ("november", "nov"),
    12: ("december", "dezember", "dec", "dez"),
}
_MONTHS = {name: number for number, names in _MONTH_NAMES.items() for name in names}
_MONTH = "(?P<name>" + "|".join(sorted(_MONTHS, key=len, reverse=True)) + r")\.?"
_YEAR = r"(?P<year>(?:19|20)\d{2})(?!\d)"
_ISO_DATE = re.compile(
    r"(?<![\w.])(?P<year>(?:19|20)\d{2})(?P<sep>[-/])(?P<month>\d{1,2})(?P=sep)(?P<day>\d{1,2})(?!\d)"
)
_NUMERIC_DATE = re.compile(r"(?<![\w./-])(?P<day>\d{1,2})(?P<sep>[./-])(?P<month>\d{1,2})(?P=sep)" + _YEAR)
_WRITTEN_DATES = (
    # 2 March 2026, 2nd of March 2026, 2. März 2026, 2 Mar. 2026
    re.compile(
        r"(?<![\w.])(?P<day>\d{1,2})(?:st|nd|rd|th)?\.?\s*(?:of\s+)?" + _MONTH + r",?\s+" + _YEAR, re.I
    ),
    # March 2, 2026
    re.compile(r"\b" + _MONTH + r"\s+(?P<day>\d{1,2})(?:st|nd|rd|th)?,?\s+" + _YEAR, re.I),
)


def has_calendar_date(text: str) -> bool:
    """True if the text names a day, month and year that exist: 2026-03-02, 02.03.2026 or 2 March 2026.

    A numeric date reads day first, and month first where only that order exists (03/31/2026). A month
    without a day ("March 2026") or a two-digit year ("02.03.26") is no calendar date.
    """
    candidates = [(int(m["year"]), int(m["month"]), int(m["day"])) for m in _ISO_DATE.finditer(text)]
    for m in _NUMERIC_DATE.finditer(text):
        day, month, year = int(m["day"]), int(m["month"]), int(m["year"])
        candidates += [(year, month, day), (year, day, month)]
    for pattern in _WRITTEN_DATES:
        candidates += [
            (int(m["year"]), _MONTHS[m["name"].lower()], int(m["day"])) for m in pattern.finditer(text)
        ]
    return any(_exists(*candidate) for candidate in candidates)


def _exists(year: int, month: int, day: int) -> bool:
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True


# The official languages of the Union, by English and German name, as Art. 1 of Council Regulation No 1
# lists them. The template of Implementing Regulation (EU) 2024/2984 has each language of the white paper
# reported from a closed list of EU languages, which it does not spell out.
EU_LANGUAGES: tuple[tuple[str, str], ...] = (
    ("Bulgarian", "Bulgarisch"),
    ("Croatian", "Kroatisch"),
    ("Czech", "Tschechisch"),
    ("Danish", "Dänisch"),
    ("Dutch", "Niederländisch"),
    ("English", "Englisch"),
    ("Estonian", "Estnisch"),
    ("Finnish", "Finnisch"),
    ("French", "Französisch"),
    ("German", "Deutsch"),
    ("Greek", "Griechisch"),
    ("Hungarian", "Ungarisch"),
    ("Irish", "Irisch"),
    ("Italian", "Italienisch"),
    ("Latvian", "Lettisch"),
    ("Lithuanian", "Litauisch"),
    ("Maltese", "Maltesisch"),
    ("Polish", "Polnisch"),
    ("Portuguese", "Portugiesisch"),
    ("Romanian", "Rumänisch"),
    ("Slovak", "Slowakisch"),
    ("Slovenian", "Slowenisch"),
    ("Spanish", "Spanisch"),
    ("Swedish", "Schwedisch"),
)
# An English name counts as written or in capitals, so the verb "polish" is no language; "Slovene" is the
# other English name of Slovenian. A German name counts in any case, inflected or with "-sprachig"
# ("in deutscher Sprache", "englischsprachig") and with ae or oe for ä or ö ("Franzoesisch").
_ENGLISH_NAMES = [name for english, _ in EU_LANGUAGES for name in (english, english.upper())] + [
    "Slovene",
    "SLOVENE",
]
_GERMAN_NAMES = sorted(
    {
        spelling
        for _, german in EU_LANGUAGES
        for spelling in (german.lower(), german.lower().replace("ä", "ae").replace("ö", "oe"))
    }
)
_EU_LANGUAGE = re.compile(
    r"\b(?:" + "|".join(_ENGLISH_NAMES) + r")\b"
    r"|(?i:\b(?:" + "|".join(_GERMAN_NAMES) + r")(?:e|em|en|er|es|sprachig\w*)?\b)"
)


def names_eu_language(text: str) -> bool:
    """True if the text names an official language of the Union in English or German: "English", "Deutsch"."""
    return bool(_EU_LANGUAGE.search(text))


def _notification_date_finding(rule: Rule, whitepaper: Whitepaper) -> Finding:
    """Passes on a calendar date, however short the section: "Date of notification: 2026-03-02"."""
    return _answer_finding(
        rule,
        whitepaper,
        has_calendar_date,
        english="No calendar date with day, month and year was found, "
        "for example 2026-03-02 or 2 March 2026.",
        german="Kein Kalenderdatum mit Tag, Monat und Jahr gefunden, etwa 2026-03-02 oder 2. März 2026.",
    )


def _language_finding(rule: Rule, whitepaper: Whitepaper) -> Finding:
    """Passes when an official EU language is named: "Language or languages of the white paper: English"."""
    return _answer_finding(
        rule,
        whitepaper,
        names_eu_language,
        english="No official EU language was found, for example English or German.",
        german="Keine Amtssprache der EU gefunden, etwa Englisch oder Deutsch.",
    )


def _answer_finding(
    rule: Rule, whitepaper: Whitepaper, answers: Callable[[str], bool], *, english: str, german: str
) -> Finding:
    """A field answered by a value, such as a date or a language, passes on that value at any length.

    Empty and placeholder-only sections are Missing, as on the generic checks. A minimum length would hold
    a correct one-word answer at Review, and listed terms would match the template's own label.
    """
    is_de = whitepaper.language == "de"
    text = whitepaper.section(rule.section)
    absent = _absent(text, is_de)
    if absent:
        return Finding(rule=rule, status="missing", word_count=0, issues=(absent,))
    status = "pass" if answers(text) else "review"
    issues = () if status == "pass" else (german if is_de else english,)
    return Finding(rule=rule, status=status, word_count=_count_words(text), issues=issues)
