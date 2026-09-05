"""Core lint engine."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from micar_linter.anchors import SourceAnchor, build_source_anchors
from micar_linter.rules import RULESETS
from micar_linter.rules.base import Finding, Rule, Severity
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

        is_de = whitepaper.language == "de"

        text = whitepaper.section(rule.section)
        word_count = _count_words(text)

        if not text.strip():
            msg = "Abschnitt ist leer oder fehlt." if is_de else "Section is empty or absent."
            return Finding(
                rule=rule,
                status="missing",
                word_count=0,
                issues=(msg,),
            )

        issues: list[str] = []
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
        if missing_terms:
            prefix = "Fehlende Begriffe: " if is_de else "Missing review terms: "
            issues.append(prefix + ", ".join(missing_terms) + ".")

        # Bilingual required regex patterns
        req_patterns = (
            rule.required_patterns_de if (is_de and rule.required_patterns_de) else rule.required_patterns
        )
        for pattern in req_patterns:
            try:
                compiled = re.compile(pattern, re.IGNORECASE)
            except re.error as exc:
                msg = (
                    f"Ungültiges gefordertes Regex-Muster '{pattern}': {exc}"
                    if is_de
                    else f"Invalid required pattern regex '{pattern}': {exc}"
                )
                issues.append(msg)
                continue
            if not compiled.search(text):
                msg = (
                    f"Fehlendes gefordertes Muster: '{pattern}'."
                    if is_de
                    else f"Missing required pattern: '{pattern}'."
                )
                issues.append(msg)

        # Bilingual prohibited regex patterns
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
            if compiled.search(text):
                msg = (
                    f"Unzulässiger Inhalt gefunden: '{pattern}'."
                    if is_de
                    else f"Prohibited content matched: '{pattern}'."
                )
                issues.append(msg)

        status = "review" if issues else "pass"
        return Finding(rule=rule, status=status, word_count=word_count, issues=tuple(issues))


def lint_whitepaper(whitepaper: Whitepaper) -> Report:
    """Convenience entry point: pick the right ruleset and lint."""
    rules = RULESETS[whitepaper.type]
    findings = Linter(rules).lint(whitepaper)

    # Check for unrecognized/misspelled sections
    valid_sections = {rule.section for rule in rules}
    warnings: list[str] = []
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
    """
    is_de = whitepaper.language == "de"
    metadata = whitepaper.metadata
    if not bool(metadata.get("ixbrl_validated", False)):
        source_file = str(metadata.get("source_file", ""))
        if source_file.lower().endswith((".xhtml", ".html")):
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
