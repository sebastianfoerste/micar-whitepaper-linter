"""Core rule, finding, and severity primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class Severity(IntEnum):
    """Three-tier severity tied to the consequence under MiCAR.

    Severity belongs to the rule, not to the finding: it says what is at stake
    if the check fails, so a BLOCKER rule can give a "review" finding and a
    MAJOR rule a "missing" one.

    BLOCKER: the rule covers a requirement without which the white paper cannot
             be notified or submitted for approval (Art. 8(1), 16(2) second
             subpara., 17(1)(a), 18(2)(k), 51(11) MiCAR), so an open finding
             should hold the draft back until it is cured.
    MAJOR:   the rule covers a disclosure that, if materially incomplete, is
             likely to mislead under Art. 6(2) / 19(2) / 51(2) MiCAR.
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
    section:             section key the generic checks read, as in the `sections` of a JSON
                         draft (COMMON.IXBRL_TAGGING reads no section; the LEI rules read every one).
    label:               human-readable description of the disclosure requirement.
    required_terms:      lowercase substrings that must appear in the section text (legacy).
    required_patterns:   regex patterns that must be matched in the section text.
    prohibited_patterns: regex patterns that must NOT be matched in the section text.
    min_words:           minimum word count below which the section is considered thin.
    severity:            the rule's severity, carried by every finding of the rule.
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
