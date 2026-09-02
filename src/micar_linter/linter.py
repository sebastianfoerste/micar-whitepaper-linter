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
        return tuple(
            f
            for f in self.findings
            if not f.passed and f.rule.severity is Severity.BLOCKER
        )

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

        is_de = (whitepaper.language == "de")

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
                issues.append(
                    f"Section is thin: {word_count} words, expected at least {rule.min_words}."
                )

        # Bilingual required terms
        req_terms = rule.required_terms_de if (is_de and rule.required_terms_de) else rule.required_terms
        missing_terms = [
            term for term in req_terms if term.lower() not in normalized
        ]
        if missing_terms:
            prefix = "Fehlende Begriffe: " if is_de else "Missing review terms: "
            issues.append(prefix + ", ".join(missing_terms) + ".")

        # Bilingual required regex patterns
        req_patterns = (
            rule.required_patterns_de
            if (is_de and rule.required_patterns_de)
            else rule.required_patterns
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

    Art. 36(4)(d) MiCAR sets a minimum share of the reserve that must be held as
    deposits with credit institutions. Which share applies turns on facts the text
    alone does not establish: whether the token references an official currency and
    whether it has been classified as significant. Absent those characterisations
    the rule reports `review` rather than guessing a threshold.
    """
    is_de = whitepaper.language == "de"
    metadata = whitepaper.metadata
    significant = metadata.get("art_significant")
    references_currency = metadata.get("references_official_currency")

    unknown: list[str] = []
    if not isinstance(references_currency, bool):
        unknown.append("references_official_currency")
    if not isinstance(significant, bool):
        unknown.append("art_significant")
    if unknown:
        msg = (
            "Rechtliche Einordnung fehlt (" + ", ".join(unknown) + "); "
            "die anwendbare Mindestquote kann nicht bestimmt werden. Pruefung durch "
            "einen Juristen erforderlich."
            if is_de
            else "Legal characterisation missing (" + ", ".join(unknown) + "); the "
            "applicable minimum share cannot be determined. Human review required."
        )
        return Finding(rule=rule, status="review", word_count=0, issues=(msg,))

    if not references_currency:
        msg = (
            "Charakterisiert als nicht auf eine amtliche Waehrung referenzierend; "
            "die Mindestquote nach Art. 36 Abs. 4 Buchst. d MiCAR ist zu bestaetigen."
            if is_de
            else "Characterised as not referencing an official currency; the minimum "
            "share under Art. 36(4)(d) MiCAR must be confirmed by a reviewer."
        )
        return Finding(rule=rule, status="review", word_count=0, issues=(msg,))

    threshold = 60 if significant else 30
    text = whitepaper.section(rule.section)
    if re.search(rf"{threshold}\s*%", text):
        return Finding(rule=rule, status="pass", word_count=_count_words(text), issues=())

    msg = (
        f"Erwartete Mindestquote {threshold} % ist im Abschnitt nicht angegeben "
        f"(signifikant={significant})."
        if is_de
        else f"Expected minimum share of {threshold}% is not stated in the section "
        f"(significant={significant})."
    )
    return Finding(rule=rule, status="missing", word_count=_count_words(text), issues=(msg,))
