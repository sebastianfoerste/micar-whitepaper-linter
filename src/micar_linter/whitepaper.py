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

    @property
    def language(self) -> str:
        """Detect draft language (en or de).

        Checks metadata first (allows CLI/config override), then falls back to heuristics.
        """
        meta_lang = self.metadata.get("language")
        if meta_lang in ("en", "de"):
            return meta_lang

        full_text = " ".join(self.sections.values()).lower()
        german_words = {"der", "die", "das", "und", "ist", "mit", "von", "eine", "oder"}
        english_words = {"the", "and", "is", "of", "with", "for", "that", "this", "or"}

        words = [w.strip(".,;:?!()[]{}") for w in full_text.split()]
        de_count = sum(1 for w in words if w in german_words)
        en_count = sum(1 for w in words if w in english_words)

        return "de" if de_count > en_count else "en"


def load_whitepaper(path: Path, whitepaper_type: WhitepaperType | None = None) -> Whitepaper:
    """Load and validate a white paper JSON, PDF, DOCX, Markdown, or XHTML file.

    whitepaper_type states the regime for document formats. A JSON draft carries its own "type".
    """
    suffix = path.suffix.lower()

    if suffix == ".json":
        return _load_json(path)
    if suffix in (".pdf", ".docx", ".xhtml", ".html", ".md"):
        return _load_document(path, suffix, whitepaper_type)
    raise SystemExit(f"Unsupported file format '{suffix}'. Expected: .json, .pdf, .docx, .xhtml, .html, .md")


_RESERVED_METADATA_KEYS = (
    # Set only by the document loaders: anchors and the iXBRL message read it, and anchors parse the file.
    "source_file",
    "ixbrl_validated",
    "ixbrl_issues",
    "extraction_notes",
    # Set by the XHTML loader for a saved iXBRL viewer page; the iXBRL message reads it.
    "script_packed_source",
    # Set by the XHTML loader for a numbered-field draft: the fields of each section that hold only a
    # placeholder, which the shared checks name, and the answer of every field, which the point rules read.
    "placeholder_fields",
    "numbered_fields",
    "reserve_characterisation_reviewed_by",
    "reserve_characterisation_reviewed_on",
)


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

    sections = {str(k): (v if isinstance(v, str) else str(v)) for k, v in data["sections"].items()}
    metadata = {
        k: v
        for k, v in data.items()
        if k not in ("title", "type", "sections") and k not in _RESERVED_METADATA_KEYS
    }
    # A JSON draft is never the notification format, so iXBRL cannot have been validated.
    metadata["ixbrl_validated"] = False

    return Whitepaper(
        title=str(data.get("title", "Untitled white paper")),
        type=wp_type,
        sections=sections,
        metadata=metadata,
    )


VIEWER_PAGE_NOTE = (
    "This file is a saved iXBRL viewer page. The checks read the white paper text packed inside it, "
    "as the viewer renders it, and that rendering can differ from the XHTML document itself. "
    "Its iXBRL format was not checked."
)
VIEWER_EMPTY_NOTE = (
    "No section heading or numbered field was found in the white paper this page carries, "
    "so the content checks find no section text to read."
)


def _unpack_viewer_page(path: Path) -> bytes:
    """Return the markup a saved iXBRL viewer page writes into itself, or stop with the reason."""
    from micar_linter.xhtml_parser import (
        MAX_UNPACKED_BYTES,
        PackedPageTooLarge,
        SeveralPackedDocuments,
        is_script_packed,
        unpack_script_payload,
    )

    try:
        document = unpack_script_payload(path)
    except PackedPageTooLarge:
        raise SystemExit(
            f"{path.name} is a saved iXBRL viewer page whose packed white paper unpacks to more than "
            f"{MAX_UNPACKED_BYTES // (1024 * 1024)} MB, the limit for unpacking. Check the white paper's own "
            "XHTML file instead; for a published white paper, that is the file in the ESMA register."
        ) from None
    except SeveralPackedDocuments:
        raise SystemExit(
            f"{path.name} is a saved iXBRL viewer page that packs more than one document, so which one is "
            "the white paper is unclear. Check the white paper's own XHTML file instead; for a published "
            "white paper, that is the file in the ESMA register."
        ) from None
    if document is None or is_script_packed(document):
        raise SystemExit(
            f"{path.name} holds no white paper text that can be read: its content is packed inside a script, "
            "as in a saved iXBRL viewer page, in a form that cannot be unpacked. Check the white paper's own "
            "XHTML file instead; for a published white paper, that is the file in the ESMA register."
        )
    return document


def _load_document(path: Path, suffix: str, whitepaper_type: WhitepaperType | None) -> Whitepaper:
    if not path.exists():
        raise SystemExit(f"File not found: {path}")

    ixbrl_issues = []
    ixbrl_validated = False
    script_packed = False
    extraction_notes: tuple[str, ...] = ()
    placeholder_fields: dict[str, tuple[str, ...]] = {}
    numbered_fields: dict[str, str] | None = None
    extracted = ""
    try:
        if suffix == ".pdf":
            from micar_linter.document import parse_pdf

            parsed = parse_pdf(path)
            sections, extracted = parsed.sections, parsed.text
        elif suffix == ".docx":
            from micar_linter.document import parse_docx

            parsed = parse_docx(path)
            sections, extracted = parsed.sections, parsed.text
        elif suffix == ".md":
            from micar_linter.document import load_from_markdown

            sections = load_from_markdown(path)
        else:
            from micar_linter.ixbrl import validate_ixbrl
            from micar_linter.numbered_fields import (
                extract_numbered_fields,
                field_answers,
                is_numbered_layout,
                sections_from_numbered_fields,
            )
            from micar_linter.xhtml_parser import is_script_packed, load_from_xhtml

            script_packed = is_script_packed(path)
            source = _unpack_viewer_page(path) if script_packed else path
            fields = extract_numbered_fields(source)
            if is_numbered_layout(fields):
                # The template wording names every regime ("not an asset-referenced token"),
                # so the regime of a numbered white paper is never inferred from its text.
                if whitepaper_type is None:
                    subject = f"The white paper packed in {path.name}" if script_packed else path.name
                    raise SystemExit(
                        f"{subject} uses the numbered fields of Implementing Regulation (EU) 2024/2984. "
                        "State the regime explicitly: other, art or emt."
                    )
                sections, extraction_notes, placeholder_fields = sections_from_numbered_fields(
                    fields, whitepaper_type
                )
                numbered_fields = field_answers(fields, whitepaper_type)
            else:
                sections = load_from_xhtml(source)
            if script_packed:
                # A viewer's rendering is not the XHTML document itself, so validate_ixbrl does not run.
                # The first-page statement is found by its wording, not by a heading or field.
                found = sections.keys() - {"not_approved_statement"}
                viewer_notes = (VIEWER_PAGE_NOTE, VIEWER_EMPTY_NOTE) if not found else (VIEWER_PAGE_NOTE,)
                extraction_notes = (*viewer_notes, *extraction_notes)
            else:
                ixbrl_issues = validate_ixbrl(path)
                ixbrl_validated = True
    except SystemExit:
        raise
    except Exception as exc:
        raise SystemExit(f"Error reading document {path}: {exc}") from exc

    # The regime of a PDF or DOCX is inferred from its whole text: a heading ("Reserve of Assets"), which is
    # not section body, or text in no section may be all that names it.
    full_text = (extracted or "\n".join(sections.values())).lower()
    art_markers = ("asset-referenced", "stabilisation mechanism", "reserve of assets")
    emt_markers = ("e-money token", "referenced currency", "safeguarding of funds")
    if whitepaper_type is not None:
        wp_type = whitepaper_type
    elif any(marker in full_text for marker in art_markers):
        wp_type = WhitepaperType.ART
    elif any(marker in full_text for marker in emt_markers):
        wp_type = WhitepaperType.EMT
    else:
        wp_type = WhitepaperType.OTHER

    if wp_type is WhitepaperType.ART:
        sections.pop("emt", None)
        sections.pop("crypto_asset", None)
        # Art. 19 MiCAR prescribes no first-page statement, so no ART rule reads one.
        sections.pop("not_approved_statement", None)
    elif wp_type is WhitepaperType.EMT:
        sections.pop("art", None)
        sections.pop("crypto_asset", None)
    else:
        sections.pop("art", None)
        sections.pop("emt", None)

    title = path.stem.replace("-", " ").replace("_", " ").title()
    metadata = {
        "source_file": str(path),
        "ixbrl_validated": ixbrl_validated,
        "ixbrl_issues": tuple(ixbrl_issues),
        "extraction_notes": extraction_notes,
        "script_packed_source": script_packed,
        "placeholder_fields": placeholder_fields,
    }
    # Only a numbered-field draft carries the key, so a point rule can tell which layout it reads.
    if numbered_fields is not None:
        metadata["numbered_fields"] = numbered_fields

    return Whitepaper(
        title=title,
        type=wp_type,
        sections=sections,
        metadata=metadata,
    )
