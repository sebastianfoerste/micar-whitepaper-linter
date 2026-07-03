"""MiCAR Whitepaper Linter - deterministic first-pass screening for MiCAR white papers."""

__version__ = "0.1.0"

from micar_linter.linter import Linter, lint_whitepaper
from micar_linter.rules.base import Finding, Rule, Severity
from micar_linter.whitepaper import Whitepaper, WhitepaperType

__all__ = [
    "Finding",
    "Linter",
    "Rule",
    "Severity",
    "Whitepaper",
    "WhitepaperType",
    "lint_whitepaper",
]
