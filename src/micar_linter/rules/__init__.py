"""Rule sets keyed to MiCAR Annex I, II, and III."""

from micar_linter.rules.annex_i import ANNEX_I_RULES
from micar_linter.rules.annex_ii import ANNEX_II_RULES
from micar_linter.rules.annex_iii import ANNEX_III_RULES
from micar_linter.rules.base import Finding, Rule, Severity
from micar_linter.rules.common import (
    COMMON_RULES,
    DTI_RULE_ART,
    DTI_RULE_EMT,
    DTI_RULE_OTHER,
    EMT_COMMON_RULES,
)
from micar_linter.whitepaper import WhitepaperType

# COMMON.DTI_FORMAT reads a different part per regime, so each regime gets its own variant after the
# common rules.
RULESETS: dict[WhitepaperType, tuple[Rule, ...]] = {
    WhitepaperType.OTHER: (*COMMON_RULES, DTI_RULE_OTHER, *ANNEX_I_RULES),
    WhitepaperType.ART: (*COMMON_RULES, DTI_RULE_ART, *ANNEX_II_RULES),
    WhitepaperType.EMT: (*EMT_COMMON_RULES, DTI_RULE_EMT, *ANNEX_III_RULES),
}

__all__ = [
    "ANNEX_II_RULES",
    "ANNEX_III_RULES",
    "ANNEX_I_RULES",
    "COMMON_RULES",
    "EMT_COMMON_RULES",
    "Finding",
    "RULESETS",
    "Rule",
    "Severity",
]
