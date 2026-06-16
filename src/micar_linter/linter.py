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
            source_file = str(whitepaper.metadata.get("source_file", ""))
            if source_file.lower().endswith((".xhtml", ".html")):
                tag_issues = whitepaper.metadata.get("ixbrl_issues", ())
                if tag_issues:
                    return Finding(
                        rule=rule,
                        status="review",
                        word_count=0,
                        issues=tuple(tag_issues),
                    )
            return Finding(
                rule=rule,
                status="pass",
                word_count=0,
                issues=(),
            )

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
