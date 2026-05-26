"""Input model for crypto-asset white papers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any


class WhitepaperType(StrEnum):
    """The three MiCAR white paper regimes.

    OTHER:  Art. 6 i.V.m. Anhang I MiCAR (crypto-assets other than ARTs and EMTs).
    ART:    Art. 19 i.V.m. Anhang II MiCAR (asset-referenced tokens).
    EMT:    Art. 51 i.V.m. Anhang III MiCAR (e-money tokens).
    """

    OTHER = "other"
    ART = "art"
    EMT = "emt"


@dataclass(frozen=True)
class Whitepaper:
    """A parsed white paper draft."""

    title: str
    type: WhitepaperType
    sections: dict[str, str]
    metadata: dict[str, Any]

    def section(self, key: str) -> str:
        value = self.sections.get(key, "")
        return value if isinstance(value, str) else str(value)


def load_whitepaper(path: Path) -> Whitepaper:
    """Load and validate a white paper JSON, PDF, DOCX, or XHTML file."""
    suffix = path.suffix.lower()

    if suffix == ".json":
        return _load_json(path)
    if suffix in (".pdf", ".docx", ".xhtml", ".html"):
        return _load_document(path, suffix)
    raise SystemExit(f"Unsupported file format '{suffix}'. Expected: .json, .pdf, .docx, .xhtml, .html")


def _load_json(path: Path) -> Whitepaper:
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except FileNotFoundError as exc:
        raise SystemExit(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise SystemExit("Whitepaper JSON must be an object.")
    if not isinstance(data.get("sections"), dict):
        raise SystemExit("Whitepaper JSON must contain a 'sections' object.")

    type_str = str(data.get("type", "other")).lower()
    try:
        wp_type = WhitepaperType(type_str)
    except ValueError as exc:
        raise SystemExit(
            f"Unknown whitepaper type '{type_str}'. Expected one of: "
            + ", ".join(t.value for t in WhitepaperType)
        ) from exc

    sections = {
        str(k): (v if isinstance(v, str) else str(v))
        for k, v in data["sections"].items()
    }
    metadata = {k: v for k, v in data.items() if k not in ("title", "type", "sections")}

    return Whitepaper(
        title=str(data.get("title", "Untitled white paper")),
        type=wp_type,
        sections=sections,
        metadata=metadata,
    )


def _load_document(path: Path, suffix: str) -> Whitepaper:
    if not path.exists():
        raise SystemExit(f"File not found: {path}")

    ixbrl_issues = []
    try:
        if suffix == ".pdf":
            from micar_linter.document import load_from_pdf

            sections = load_from_pdf(path)
        elif suffix == ".docx":
            from micar_linter.document import load_from_docx

            sections = load_from_docx(path)
        else:
            from micar_linter.xhtml_parser import load_from_xhtml
            from micar_linter.ixbrl import validate_ixbrl

            sections = load_from_xhtml(path)
            ixbrl_issues = validate_ixbrl(path)
    except SystemExit:
        raise
    except Exception as exc:
        raise SystemExit(f"Error reading document {path}: {exc}") from exc

    full_text = "\n".join(sections.values()).lower()
    art_markers = ("asset-referenced", "stabilisation mechanism", "reserve of assets")
    emt_markers = ("e-money token", "referenced currency", "safeguarding of funds")
    if any(marker in full_text for marker in art_markers):
        wp_type = WhitepaperType.ART
    elif any(marker in full_text for marker in emt_markers):
        wp_type = WhitepaperType.EMT
    else:
        wp_type = WhitepaperType.OTHER

    if wp_type is WhitepaperType.ART:
        sections.pop("emt", None)
        sections.pop("crypto_asset", None)
    elif wp_type is WhitepaperType.EMT:
        sections.pop("art", None)
        sections.pop("crypto_asset", None)
    else:
        sections.pop("art", None)
        sections.pop("emt", None)

    title = path.stem.replace("-", " ").replace("_", " ").title()
    metadata = {"source_file": str(path)}
    if ixbrl_issues:
        metadata["ixbrl_issues"] = tuple(ixbrl_issues)

    return Whitepaper(
        title=title,
        type=wp_type,
        sections=sections,
        metadata=metadata,
    )
