"""Document loading for the Title II Annex I study."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from micar_linter.document import match_heading_to_section

MIN_TEXT_WORDS = 80


@dataclass(frozen=True)
class LoadedDocument:
    path: Path
    text: str
    sections: dict[str, str]
    format: str
    pages: int | None
    source_hash_sha256: str
    text_extraction: str
    warnings: list[str] = field(default_factory=list)
    ixbrl_tags: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "format": self.format,
            "pages": self.pages,
            "source_hash_sha256": self.source_hash_sha256,
            "text_extraction": self.text_extraction,
            "warnings": self.warnings,
            "ixbrl_tags": self.ixbrl_tags,
            "labels": self.labels,
        }


def load_document(path: Path) -> LoadedDocument:
    """Load XHTML/HTML, PDF, or TXT and classify extraction quality."""
    if not path.exists():
        raise FileNotFoundError(path)

    suffix = path.suffix.lower()
    if suffix in {".xhtml", ".html", ".htm"}:
        return _load_html(path)
    if suffix == ".pdf":
        return _load_pdf(path)
    if suffix == ".txt":
        return _load_txt(path)
    raise ValueError(f"Unsupported document type for study loader: {suffix}")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_html(path: Path) -> LoadedDocument:
    from lxml import etree

    raw = path.read_bytes()
    warnings: list[str] = []
    try:
        parser = etree.XMLParser(
            recover=True,
            huge_tree=True,
            resolve_entities=False,
            no_network=True,
        )
        tree = etree.fromstring(raw, parser=parser)
    except Exception:
        parser = etree.HTMLParser(encoding="utf-8")
        tree = etree.parse(str(path), parser=parser).getroot()
        warnings.append("parsed_with_html_recovery")

    _remove_non_visible_elements(tree)
    text_parts = [_normalize_text(text) for text in tree.xpath("//text()[normalize-space()]")]
    text = _normalize_text(" ".join(part for part in text_parts if part))
    sections = _sections_from_html_tree(tree)
    ixbrl_tags = _ixbrl_tag_names(tree)
    labels = _html_labels(tree)
    extraction, extraction_warnings = _quality(text)
    warnings.extend(extraction_warnings)

    return LoadedDocument(
        path=path,
        text=text,
        sections=sections,
        format="xhtml" if path.suffix.lower() == ".xhtml" else "html",
        pages=None,
        source_hash_sha256=file_sha256(path),
        text_extraction=extraction,
        warnings=warnings,
        ixbrl_tags=ixbrl_tags,
        labels=labels,
    )


def _load_pdf(path: Path) -> LoadedDocument:
    try:
        import pypdf
    except ImportError as exc:
        raise SystemExit("PDF support requires pypdf. Install the project runtime dependencies.") from exc

    warnings: list[str] = []
    try:
        reader = pypdf.PdfReader(path)
    except Exception as exc:
        return LoadedDocument(
            path=path,
            text="",
            sections={},
            format="pdf",
            pages=None,
            source_hash_sha256=file_sha256(path),
            text_extraction="failed",
            warnings=[f"pdf_open_failed:{type(exc).__name__}"],
        )

    page_text: list[str] = []
    pages_with_text = 0
    for page in reader.pages:
        try:
            extracted = page.extract_text() or ""
        except Exception as exc:
            warnings.append(f"pdf_page_extract_failed:{type(exc).__name__}")
            extracted = ""
        if extracted.strip():
            pages_with_text += 1
            page_text.append(extracted)

    text = _normalize_text("\n".join(page_text))
    sections = _sections_from_lines(text.splitlines())
    extraction, extraction_warnings = _quality(text)
    warnings.extend(extraction_warnings)
    if reader.pages and pages_with_text == 0:
        extraction = "failed"
        warnings.append("pdf_no_extractable_text")
    elif pages_with_text < max(1, len(reader.pages) // 3):
        extraction = "weak"
        warnings.append("pdf_text_on_few_pages")

    return LoadedDocument(
        path=path,
        text=text,
        sections=sections,
        format="pdf",
        pages=len(reader.pages),
        source_hash_sha256=file_sha256(path),
        text_extraction=extraction,
        warnings=warnings,
    )


def _load_txt(path: Path) -> LoadedDocument:
    text = path.read_text(encoding="utf-8", errors="replace")
    normalized = _normalize_text(text)
    sections = _sections_from_lines(text.splitlines())
    extraction, warnings = _quality(normalized)
    return LoadedDocument(
        path=path,
        text=normalized,
        sections=sections,
        format="txt",
        pages=None,
        source_hash_sha256=file_sha256(path),
        text_extraction=extraction,
        warnings=warnings,
    )


def _remove_non_visible_elements(tree: Any) -> None:
    query = ".//*[local-name()='script' or local-name()='style' or local-name()='noscript']"
    for element in tree.xpath(query):
        parent = element.getparent()
        if parent is not None:
            parent.remove(element)


def _sections_from_html_tree(tree: Any) -> dict[str, str]:
    elements = tree.xpath(
        ".//*[local-name()='h1' or local-name()='h2' or local-name()='h3' or local-name()='h4' "
        "or local-name()='h5' or local-name()='h6' or local-name()='p' or local-name()='li' "
        "or local-name()='td' or local-name()='th' or local-name()='div']"
    )
    sections: dict[str, list[str]] = {}
    current_keys: list[str] = []
    for element in elements:
        text = _normalize_text(" ".join(element.itertext()))
        if not text:
            continue
        local_name = str(element.tag).split("}", 1)[-1].lower()
        if local_name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            current_keys = match_heading_to_section(text)
            continue
        if current_keys:
            for key in current_keys:
                sections.setdefault(key, []).append(text)
    return {key: "\n".join(values) for key, values in sections.items()}


def _sections_from_lines(lines: list[str]) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current_keys: list[str] = []
    for line in lines:
        text = _normalize_text(line)
        if not text:
            continue
        matched = match_heading_to_section(text)
        if matched and len(text) < 140:
            current_keys = matched
            continue
        if current_keys:
            for key in current_keys:
                sections.setdefault(key, []).append(text)
    return {key: "\n".join(values) for key, values in sections.items()}


def _ixbrl_tag_names(tree: Any) -> list[str]:
    tags: set[str] = set()
    for element in tree.xpath(".//*[@name]"):
        local_name = str(element.tag).split("}", 1)[-1].lower()
        if local_name in {"nonnumeric", "nonfraction", "tuple"} or "ix" in str(element.tag).lower():
            value = element.get("name")
            if value:
                tags.add(str(value))
    return sorted(tags)


def _html_labels(tree: Any) -> list[str]:
    labels: set[str] = set()
    for element in tree.xpath(".//*[@aria-label or @title or @name]"):
        for attribute in ("aria-label", "title", "name"):
            value = element.get(attribute)
            if value:
                labels.add(_normalize_text(value))
    return sorted(label for label in labels if label)


def _quality(text: str) -> tuple[str, list[str]]:
    word_count = len(re.findall(r"\b\w+\b", text))
    if word_count == 0:
        return "failed", ["no_extractable_text"]
    if word_count < MIN_TEXT_WORDS:
        return "weak", [f"low_word_count:{word_count}"]
    return "ok", []


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
