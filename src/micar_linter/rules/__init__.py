"""Rule sets keyed to MiCAR Annex I, II, and III, each followed by the template rules (rules/templates.py)
and the regime's RTS.CLASSIFICATION_DATA.

The point rules of rules/points.py follow the rules of their Part (with_points).
"""

from micar_linter.rules.annex_i import ANNEX_I_RULES
from micar_linter.rules.annex_ii import ANNEX_II_RULES
from micar_linter.rules.annex_iii import ANNEX_III_RULES
from micar_linter.rules.base import Finding, Rule, Severity
from micar_linter.rules.common import COMMON_RULES, EMT_COMMON_RULES
from micar_linter.rules.marketing import MARKETING_RULES
from micar_linter.rules.points import POINT_RULES, with_points
from micar_linter.rules.templates import CLASSIFICATION_RULES, TEMPLATE_RULES
from micar_linter.whitepaper import WhitepaperType

_ANNEX_RULES: dict[WhitepaperType, tuple[Rule, ...]] = {
    WhitepaperType.OTHER: COMMON_RULES + with_points(ANNEX_I_RULES, WhitepaperType.OTHER),
    WhitepaperType.ART: COMMON_RULES + with_points(ANNEX_II_RULES, WhitepaperType.ART),
    WhitepaperType.EMT: EMT_COMMON_RULES + with_points(ANNEX_III_RULES, WhitepaperType.EMT),
}
RULESETS: dict[WhitepaperType, tuple[Rule, ...]] = {
    regime: rules + TEMPLATE_RULES + (CLASSIFICATION_RULES[regime],) for regime, rules in _ANNEX_RULES.items()
}
# The rules for marketing communications (ADR 0009), a second kind of document: Art. 7 MiCAR for crypto-assets
# other than ARTs and EMTs. Art. 29 (ARTs) and Art. 53 (EMTs) are not covered.
MARKETING_RULESETS: dict[WhitepaperType, tuple[Rule, ...]] = {WhitepaperType.OTHER: MARKETING_RULES}

__all__ = [
    "ANNEX_II_RULES",
    "ANNEX_III_RULES",
    "ANNEX_I_RULES",
    "CLASSIFICATION_RULES",
    "COMMON_RULES",
    "EMT_COMMON_RULES",
    "Finding",
    "MARKETING_RULES",
    "MARKETING_RULESETS",
    "POINT_RULES",
    "RULESETS",
    "TEMPLATE_RULES",
    "Rule",
    "Severity",
]
