"""Point rules (ADR 0005): one rule per Annex point that the numbered template fields carry.

The points and their fields sit in point_fields.py; this module builds one Rule per point, citing the point
("Anhang I Teil A Nr. 2 MiCAR"), reading the section of its Part and carrying the severity of its Part rule
(missing mandatory content is a BLOCKER where the Part rule is one; Annex I Part B is MAJOR and Part C MINOR).
with_points places each point rule after the rules of its Part, in the order of the points, so a report lists
ANNEX_I.A, then ANNEX_I.A.P1 to ANNEX_I.A.P10 (with ANNEX_I.A.P6, the contact details, which keeps its own
check in contact.py). linter.py checks the fields of a numbered-field draft; in any other draft the rule is
Missing where its section is absent and Review otherwise, with a note that the point check needs the
numbered-field layout.
"""

from __future__ import annotations

import re

from micar_linter.point_fields import POINTS, Point
from micar_linter.rules.base import Rule, Severity
from micar_linter.whitepaper import WhitepaperType

# The section and severity of each Part's point rules: those of the Part rule (rules/annex_*.py). Annex II has
# no Part G rule; its four ANNEX_II.G.* topic rules read reserve_of_assets as BLOCKER.
PART_SETTINGS: dict[tuple[str, str], tuple[str, Severity]] = {
    ("I", "A"): ("offeror", Severity.BLOCKER),
    ("I", "B"): ("issuer", Severity.MAJOR),
    ("I", "C"): ("trading_platform_operator", Severity.MINOR),
    ("I", "D"): ("project", Severity.BLOCKER),
    ("I", "E"): ("offer_or_admission", Severity.BLOCKER),
    ("I", "F"): ("crypto_asset", Severity.BLOCKER),
    ("I", "G"): ("rights_and_obligations", Severity.BLOCKER),
    ("I", "H"): ("technology", Severity.BLOCKER),
    ("I", "I"): ("risks", Severity.BLOCKER),
    ("II", "A"): ("issuer", Severity.BLOCKER),
    ("II", "B"): ("art", Severity.BLOCKER),
    ("II", "C"): ("offer_or_admission", Severity.BLOCKER),
    ("II", "D"): ("rights_and_obligations", Severity.BLOCKER),
    ("II", "E"): ("technology", Severity.BLOCKER),
    ("II", "F"): ("risks", Severity.BLOCKER),
    ("II", "G"): ("reserve_of_assets", Severity.BLOCKER),
    ("III", "A"): ("issuer", Severity.BLOCKER),
    ("III", "B"): ("emt", Severity.BLOCKER),
    ("III", "C"): ("offer_or_admission", Severity.BLOCKER),
    ("III", "D"): ("rights_and_obligations", Severity.BLOCKER),
    ("III", "E"): ("technology", Severity.BLOCKER),
    ("III", "F"): ("risks", Severity.BLOCKER),
}


def point_rule(point: Point) -> Rule:
    section, severity = PART_SETTINGS[(point.annex, point.part)]
    return Rule(
        rule_id=point.rule_id,
        citation=f"Anhang {point.annex} Teil {point.part} Nr. {point.number} MiCAR",
        section=section,
        label=point.label,
        min_words=0,
        severity=severity,
    )


POINT_RULES: dict[WhitepaperType, tuple[Rule, ...]] = {
    regime: tuple(map(point_rule, points)) for regime, points in POINTS.items()
}
POINT_RULE_IDS = frozenset(rule.rule_id for rules in POINT_RULES.values() for rule in rules)

_POINT_ID = re.compile(r"^(ANNEX_[IV]+\.[A-Z])\.P(\d+)$")


def with_points(rules: tuple[Rule, ...], regime: WhitepaperType) -> tuple[Rule, ...]:
    """The Annex rules with the regime's point rules (and the point rules already among them, such as
    ANNEX_I.A.P6) placed after the last rule of their Part, ordered by point number."""
    points: dict[str, list[Rule]] = {}
    others: list[Rule] = []
    for rule in (*rules, *POINT_RULES[regime]):
        if match := _POINT_ID.match(rule.rule_id):
            points.setdefault(match.group(1), []).append(rule)
        else:
            others.append(rule)
    last: dict[str, int] = {}
    for index, rule in enumerate(others):
        part = ".".join(rule.rule_id.split(".")[:2])
        last[part] = index
    placed: list[Rule] = []
    for index, rule in enumerate(others):
        placed.append(rule)
        part = ".".join(rule.rule_id.split(".")[:2])
        if last.get(part) == index and part in points:
            placed.extend(sorted(points.pop(part), key=lambda r: int(_POINT_ID.match(r.rule_id).group(2))))
    if points:
        raise ValueError(f"point rules without a Part rule: {sorted(points)}")
    return tuple(placed)
