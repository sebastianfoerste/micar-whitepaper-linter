"""Core rule, finding, and severity primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class Severity(IntEnum):
    """Three-tier severity tied to the consequence under MiCAR.

    BLOCKER: required disclosure is absent. The white paper cannot be notified
             under Art. 8 / Art. 17 / Art. 49 MiCAR until this is cured.
    MAJOR:   required disclosure is present but materially incomplete or
             likely to mislead under Art. 6(1) / 19(1) / 51(1) MiCAR.
    MINOR:   drafting gap that should be cured before publication but does
             not gate notification.
    """

    BLOCKER = 3
    MAJOR = 2
    MINOR = 1

    @property
    def label(self) -> str:
        return self.name


@dataclass(frozen=True)
class Rule:
    """One Annex-level disclosure requirement.

    rule_id:             stable identifier, e.g. 'ANNEX_II.A.1'.
    citation:            pinpoint citation in canonical legal form.
    section:             JSON section key the rule reads.
    label:               human-readable description of the disclosure requirement.
    required_terms:      lowercase substrings that must appear in the section text (legacy).
    required_patterns:   regex patterns that must be matched in the section text.
    prohibited_patterns: regex patterns that must NOT be matched in the section text.
    min_words:           minimum word count below which the section is considered thin.
    severity:            default severity if the rule fails.
    """

    rule_id: str
    citation: str
    section: str
    label: str
    required_terms: tuple[str, ...] = ()
    required_terms_de: tuple[str, ...] = ()
    required_patterns: tuple[str, ...] = ()
    required_patterns_de: tuple[str, ...] = ()
    prohibited_patterns: tuple[str, ...] = ()
    prohibited_patterns_de: tuple[str, ...] = ()
    min_words: int = 30
    severity: Severity = Severity.MAJOR


@dataclass(frozen=True)
class Finding:
    """One result of applying a rule to a white paper section."""

    rule: Rule
    status: str  # "pass" | "review" | "missing"
    word_count: int
    issues: tuple[str, ...] = field(default_factory=tuple)

    @property
    def passed(self) -> bool:
        return self.status == "pass"
