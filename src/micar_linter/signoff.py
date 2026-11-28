"""An opt-in sign-off file that acknowledges the never-pass gates for one version of a draft (ADR 0010).

Two rules never pass for a loaded draft: COMMON.IXBRL_TAGGING, because the linter cannot validate the
iXBRL tags, and ANNEX_II.G.DEPOSIT_FLOOR_REVIEW, because a reserve floor needs a lawyer. Without this file,
`--strict` exits 1 for every white paper. The file lives outside the draft, so a draft cannot acknowledge
itself, and each entry names the SHA-256 of the exact file it was given for, so any change to the draft voids
it. An acknowledged finding keeps its status (review or missing); `--strict` no longer counts it, and the
outputs say it is acknowledged, never that it passed.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from micar_linter.placeholders import is_placeholder

SIGNOFF_SCHEMA = "micar-whitepaper-linter.signoff.v1"
ACKNOWLEDGEABLE_RULES = frozenset({"COMMON.IXBRL_TAGGING", "ANNEX_II.G.DEPOSIT_FLOOR_REVIEW"})
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class SignoffError(ValueError):
    """The sign-off file cannot be read or does not follow the schema."""


@dataclass(frozen=True)
class Acknowledgement:
    """One reviewer's acknowledgement of a never-pass gate for one version of a draft."""

    rule_id: str
    sha256: str
    reviewer: str
    date: str
    note: str

    def to_json(self) -> dict[str, str]:
        return {
            "rule_id": self.rule_id,
            "sha256": self.sha256,
            "reviewer": self.reviewer,
            "date": self.date,
            "note": self.note,
        }


def load_signoff(path: Path) -> tuple[Acknowledgement, ...]:
    """Read and validate a sign-off file; raise SignoffError with the reason where it breaks the schema."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SignoffError("file not found") from exc
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SignoffError(f"not readable as JSON: {exc}") from exc
    if not isinstance(data, dict) or data.get("schema") != SIGNOFF_SCHEMA:
        raise SignoffError(f'it must be a JSON object with "schema": "{SIGNOFF_SCHEMA}"')
    entries = data.get("acknowledgements")
    if not isinstance(entries, list) or not entries:
        raise SignoffError('"acknowledgements" must be a non-empty list')
    return tuple(_acknowledgement(entry, index) for index, entry in enumerate(entries, 1))


def _acknowledgement(entry: Any, index: int) -> Acknowledgement:
    where = f"acknowledgement {index}"
    if not isinstance(entry, dict):
        raise SignoffError(f"{where} must be an object")
    rule_id = entry.get("rule_id")
    if rule_id not in ACKNOWLEDGEABLE_RULES:
        raise SignoffError(
            f"{where}: rule_id must be one of the never-pass gates "
            f"({', '.join(sorted(ACKNOWLEDGEABLE_RULES))}); other findings cannot be acknowledged"
        )
    sha256 = entry.get("sha256")
    if not isinstance(sha256, str) or not _SHA256.match(sha256):
        raise SignoffError(f"{where}: sha256 must be the 64 lower-case hex digits of the file's SHA-256")
    reviewer, note, day = entry.get("reviewer"), entry.get("note"), entry.get("date")
    for name, value in (("reviewer", reviewer), ("note", note)):
        if not isinstance(value, str) or not value.strip() or is_placeholder(value):
            raise SignoffError(f"{where}: {name} must be a non-empty text other than a placeholder")
    if not isinstance(day, str) or not _ISO_DATE.match(day):
        raise SignoffError(f"{where}: date must be a date written YYYY-MM-DD")
    try:
        date.fromisoformat(day)
    except ValueError as exc:
        raise SignoffError(f"{where}: date {day} does not exist") from exc
    return Acknowledgement(rule_id, sha256, reviewer.strip(), day, note.strip())


def apply_signoff(
    acknowledgements: tuple[Acknowledgement, ...], sha256: str, open_rule_ids: set[str]
) -> tuple[tuple[Acknowledgement, ...], tuple[str, ...]]:
    """The acknowledgements that apply to this file version and an open finding, and a warning for each
    other one."""
    applied: list[Acknowledgement] = []
    warnings: list[str] = []
    for ack in acknowledgements:
        if ack.sha256 != sha256:
            warnings.append(
                f"The sign-off for {ack.rule_id} names another version of the file "
                f"(SHA-256 {ack.sha256[:12]}..., "
                f"this file {sha256[:12]}...), so it does not apply."
            )
        elif ack.rule_id not in open_rule_ids:
            warnings.append(
                f"The sign-off for {ack.rule_id} has no open finding in this report, so it does not apply."
            )
        elif ack.rule_id not in {a.rule_id for a in applied}:
            applied.append(ack)
    return tuple(applied), tuple(warnings)
