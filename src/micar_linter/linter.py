"""Core lint engine."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

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

        text = whitepaper.section(rule.section)
        word_count = _count_words(text)

        if not text.strip():
            return Finding(
                rule=rule,
                status="missing",
                word_count=0,
                issues=("Section is empty or absent.",),
            )

        issues: list[str] = []
        normalized = text.lower()

        if word_count < rule.min_words:
            issues.append(
                f"Section is thin: {word_count} words, expected at least {rule.min_words}."
            )

        # Legacy required terms
        missing_terms = [
            term for term in rule.required_terms if term.lower() not in normalized
        ]
        if missing_terms:
            issues.append("Missing review terms: " + ", ".join(missing_terms) + ".")

        # Advanced required regex patterns
        for pattern in rule.required_patterns:
            try:
                compiled = re.compile(pattern, re.IGNORECASE)
            except re.error as exc:
                issues.append(f"Invalid required pattern regex '{pattern}': {exc}")
                continue
            if not compiled.search(text):
                issues.append(f"Missing required pattern: '{pattern}'.")

        # Prohibited regex patterns
        for pattern in rule.prohibited_patterns:
            try:
                compiled = re.compile(pattern, re.IGNORECASE)
            except re.error as exc:
                issues.append(f"Invalid prohibited pattern regex '{pattern}': {exc}")
                continue
            if compiled.search(text):
                issues.append(f"Prohibited content matched: '{pattern}'.")

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
    )


def _count_words(text: str) -> int:
    return sum(1 for word in text.split() if word.strip())
