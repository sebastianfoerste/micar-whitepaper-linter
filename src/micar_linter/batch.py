"""Directory batch review packs and Title II study batch execution."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from micar_linter.artifact_manifest import build_artifact_manifest, file_sha256
from micar_linter.document_loader import LoadedDocument, load_document
from micar_linter.linter import lint_whitepaper
from micar_linter.whitepaper import load_whitepaper

BATCH_SCHEMA = "micar-whitepaper-linter.batch-review-pack.v1"
STUDY_FINDINGS_SCHEMA = "micar-whitepaper-linter.title-ii-annex-i-study-findings.v1"
SUPPORTED_SUFFIXES = {".json", ".pdf", ".docx", ".xhtml", ".html", ".md"}
STUDY_SUPPORTED_SUFFIXES = {".xhtml", ".html", ".htm", ".pdf", ".txt"}
DEFAULT_STUDY_SAMPLE_SIZE = 10


@dataclass(frozen=True)
class StudyRule:
    rule_id: str
    annex_item: str
    label: str
    missing_element: str
    required_patterns: tuple[str, ...]
    context_patterns: tuple[str, ...]
    section_hint: str
    match_policy: str = "any"
    confidence_if_context: str = "high"
    confidence_without_context: str = "medium"


STUDY_RULES: tuple[StudyRule, ...] = (
    StudyRule(
        rule_id="ANNEX_I_PART_A_01_LEGAL_FORM",
        annex_item="Annex I, Part A",
        label="Legal form",
        missing_element="legal form of the offeror or person seeking admission to trading",
        required_patterns=(
            r"\blegal form\b",
            r"\bprivate limited\b",
            r"\blimited liability\b",
            r"\bGmbH\b",
            r"\bS\.?A\.?\b",
            r"\bLtd\.?\b",
            r"\bInc\.?\b",
            r"\bfoundation\b",
            r"\bassociation\b",
        ),
        context_patterns=(r"\bofferor\b", r"\bissuer\b", r"\bcompany\b"),
        section_hint="Offeror information",
    ),
    StudyRule(
        rule_id="ANNEX_I_PART_A_02_REGISTERED_ADDRESS",
        annex_item="Annex I, Part A",
        label="Registered address or head office",
        missing_element="registered address or head office",
        required_patterns=(
            r"\bregistered (address|office|seat)\b",
            r"\bhead office\b",
            r"\bregistered at\b",
            r"\bprincipal office\b",
            r"\baddress\b",
        ),
        context_patterns=(r"\bofferor\b", r"\bissuer\b", r"\bcompany\b"),
        section_hint="Offeror information",
    ),
    StudyRule(
        rule_id="ANNEX_I_PART_A_03_REGISTRATION_DATE",
        annex_item="Annex I, Part A",
        label="Registration date",
        missing_element="date of registration, incorporation, or establishment",
        required_patterns=(
            r"\bregistration date\b",
            r"\bdate of registration\b",
            r"\bregistered on\b",
            r"\bincorporated on\b",
            r"\bdate of incorporation\b",
            r"\bestablished on\b",
        ),
        context_patterns=(r"\bregistration\b", r"\bincorporat", r"\bestablished\b"),
        section_hint="Offeror information",
    ),
    StudyRule(
        rule_id="ANNEX_I_PART_A_04_LEI_OR_IDENTIFIER",
        annex_item="Annex I, Part A",
        label="LEI or other identifier",
        missing_element="legal entity identifier or other identifier",
        required_patterns=(
            r"\bLEI\b",
            r"\blegal entity identifier\b",
            r"\bregistration number\b",
            r"\bcompany number\b",
            r"\bcorporate number\b",
            r"\bDTI\b",
            r"\bdigital token identifier\b",
        ),
        context_patterns=(r"\bidentifier\b", r"\bregistration\b", r"\bcompany\b"),
        section_hint="Offeror information",
    ),
    StudyRule(
        rule_id="ANNEX_I_PART_A_05_CONTACT_PHONE_EMAIL",
        annex_item="Annex I, Part A",
        label="Contact telephone number and email",
        missing_element="both contact telephone number and email address",
        required_patterns=(
            r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}",
            r"(\+\d{1,3}[\s().-]*)?(?:\d[\s().-]*){7,}",
        ),
        context_patterns=(r"\bcontact\b", r"\bemail\b", r"\btelephone\b", r"\bphone\b"),
        section_hint="Contact information",
        match_policy="all",
    ),
    StudyRule(
        rule_id="ANNEX_I_PART_A_06_CONTACT_RESPONSE_PERIOD",
        annex_item="Annex I, Part A, item 6",
        label="Response period for investor contact",
        missing_element="period of days within which an investor will receive an answer",
        required_patterns=(
            r"\bresponse period\b",
            r"\brespond within\b",
            r"\breply within\b",
            r"\banswer within\b",
            r"\bwithin \d{1,3} (business )?days\b",
            r"\b\d{1,3} (business )?days within which\b",
            r"\bresponse time\s*\(days\)\s*\d{1,3}\b",
            r"\bresponse time.{0,40}\d{1,3}\s*(calendar |business )?days\b",
            r"\brespond.{0,80}within \d{1,3} (calendar |business )?days\b",
            r"\bwithin \d{1,3} (calendar |business )?days.{0,80}(respond|reply|answer)\b",
        ),
        context_patterns=(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}", r"\bcontact\b", r"\binvestor\b"),
        section_hint="Contact information",
    ),
    StudyRule(
        rule_id="ANNEX_I_PART_A_07_MANAGEMENT_BODY",
        annex_item="Annex I, Part A",
        label="Management body identity and functions",
        missing_element="identity and functions of the management body",
        required_patterns=(
            r"\bmanagement body\b",
            r"\bboard of directors\b",
            r"\bdirectors?\b",
            r"\bmanaging director\b",
            r"\bfunction(s)?\b",
        ),
        context_patterns=(r"\bmanagement\b", r"\bdirector\b", r"\bgovernance\b"),
        section_hint="Management body",
    ),
    StudyRule(
        rule_id="ANNEX_I_PART_A_08_CONFLICTS_OF_INTEREST",
        annex_item="Annex I, Part A",
        label="Conflicts of interest",
        missing_element="conflicts of interest disclosure",
        required_patterns=(
            r"\bconflicts? of interest\b",
            r"\bconflict policy\b",
            r"\bno conflicts?\b",
            r"\bpotential conflict\b",
        ),
        context_patterns=(r"\bconflict\b",),
        section_hint="Conflicts of interest",
    ),
    StudyRule(
        rule_id="ANNEX_I_PART_A_09_FINANCIAL_CONDITION",
        annex_item="Annex I, Part A",
        label="Financial condition",
        missing_element="financial condition disclosure",
        required_patterns=(
            r"\bfinancial condition\b",
            r"\bfinancial information\b",
            r"\bfinancial statements?\b",
            r"\baudited accounts?\b",
            r"\bbalance sheet\b",
            r"\bsolvency\b",
        ),
        context_patterns=(
            r"\bfinancial condition\b",
            r"\bfinancial information\b",
            r"\bfinancial statements?\b",
            r"\baudited accounts?\b",
            r"\bannual accounts?\b",
            r"\bsolvency\b",
        ),
        section_hint="Financial condition",
    ),
    StudyRule(
        rule_id="ANNEX_I_PART_B_01_ASSET_NAME_ABBREVIATION",
        annex_item="Annex I, Part B",
        label="Crypto-asset name and abbreviation",
        missing_element="crypto-asset name and abbreviation",
        required_patterns=(
            r"\bcrypto-asset name\b",
            r"\basset name\b",
            r"\babbreviation\b",
            r"\bticker\b",
            r"\bsymbol\b",
            r"\([A-Z$][A-Z0-9$.-]{1,12}\)",
        ),
        context_patterns=(r"\bcrypto-asset\b", r"\btoken\b", r"\bsymbol\b"),
        section_hint="Crypto-asset information",
    ),
    StudyRule(
        rule_id="ANNEX_I_PART_B_02_DESIGN_DEVELOPMENT_PERSONS",
        annex_item="Annex I, Part B",
        label="Persons involved in design and development",
        missing_element="persons involved in design and development",
        required_patterns=(
            r"\bdesign and development\b",
            r"\bpersons? involved\b",
            r"\bdeveloped by\b",
            r"\bdeveloper(s)?\b",
            r"\bdevelopment team\b",
            r"\bdesigned by\b",
        ),
        context_patterns=(r"\bdesign\b", r"\bdevelopment\b", r"\bdeveloper\b"),
        section_hint="Design and development",
    ),
    StudyRule(
        rule_id="ANNEX_I_PART_B_03_UTILITY_CHARACTERISTICS",
        annex_item="Annex I, Part B",
        label="Utility and characteristics",
        missing_element="utility, characteristics, or functionality of the crypto-asset",
        required_patterns=(
            r"\butility\b",
            r"\bcharacteristics?\b",
            r"\bfunctionality\b",
            r"\bfeatures?\b",
            r"\buse case\b",
            r"\bintended use\b",
        ),
        context_patterns=(r"\bcrypto-asset\b", r"\btoken\b", r"\buse\b"),
        section_hint="Utility and characteristics",
    ),
    StudyRule(
        rule_id="ARTICLE_6_05_MANDATORY_WARNINGS",
        annex_item="Article 6",
        label="Mandatory warning statements",
        missing_element="loss-of-value and protection or compensation warning statements",
        required_patterns=(
            r"\b(risk|risks)\b",
            r"\b(loss|lose|losing|lost)\b.{0,80}\b(value|all|entire)\b|\b(value|all|entire)\b.{0,80}\b(loss|lose|losing|lost)\b",
            (
                r"\bnot (covered|protected)\b|\bno (deposit guarantee|investor compensation|compensation)\b|"
                r"\binvestor compensation\b"
            ),
        ),
        context_patterns=(r"\brisk warning\b", r"\bwarning\b", r"\binvestor\b"),
        section_hint="Mandatory warnings",
        match_policy="all",
    ),
    StudyRule(
        rule_id="ARTICLE_6_06_MANAGEMENT_BODY_STATEMENT",
        annex_item="Article 6",
        label="Management body statement",
        missing_element=(
            "management body statement that the white paper complies and is fair, clear and not misleading"
        ),
        required_patterns=(
            r"\bmanagement body\b",
            r"\bcomplies\b|\bcompliant with\b",
            r"\bfair\b",
            r"\bclear\b",
            r"\bnot misleading\b",
        ),
        context_patterns=(r"\bmanagement body\b", r"\bstatement\b", r"\bnot misleading\b"),
        section_hint="Management body statement",
        match_policy="all",
    ),
    StudyRule(
        rule_id="ARTICLE_6_07_SUMMARY",
        annex_item="Article 6",
        label="Summary",
        missing_element="summary of the crypto-asset white paper",
        required_patterns=(r"\bsummary\b", r"\bkey information\b|\bplain-language summary\b"),
        context_patterns=(r"\bsummary\b", r"\bkey information\b"),
        section_hint="Summary",
    ),
)


def build_batch_review_pack(root: Path, generated_at: datetime | None = None) -> dict[str, Any]:
    timestamp = generated_at or datetime.now(UTC)
    files: list[dict[str, Any]] = []
    warnings: list[str] = []

    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            warnings.append(f"unsupported-file:{path}")
            continue
        try:
            whitepaper = load_whitepaper(path)
            report = lint_whitepaper(whitepaper)
            manifest = build_artifact_manifest(report, source_path=path, output_paths=[])
            blocker_rule_ids = [finding.rule.rule_id for finding in report.blockers]
            files.append(
                {
                    "path": str(path),
                    "source_hash": file_sha256(path),
                    "whitepaper_type": report.whitepaper_type.value,
                    "summary_counts": {
                        "pass": len(report.passed),
                        "review": len(report.needs_review),
                        "missing": len(report.missing),
                        "blockers": len(report.blockers),
                        "total": len(report.findings),
                    },
                    "blocker_rule_ids": blocker_rule_ids,
                    "manifest_digest": manifest["overall_digest"],
                    "per_file_eligibility": {
                        "machine_export_ready": not blocker_rule_ids,
                        "review_required": True,
                    },
                }
            )
        except SystemExit as exc:
            warnings.append(f"lint-failed:{path}:{exc}")

    payload = {
        "schema": BATCH_SCHEMA,
        "generated_at": timestamp.isoformat(),
        "root": str(root),
        "summary": {
            "supported_files": len(files),
            "unsupported_files": len(
                [warning for warning in warnings if warning.startswith("unsupported-file:")]
            ),
            "blocked_files": len([item for item in files if item["blocker_rule_ids"]]),
        },
        "files": files,
        "warnings": warnings,
        "review_notice": (
            "Batch review packs contain file metadata, hashes, counts, blockers, and manifest digests only. "
            "Human legal review remains mandatory before external use."
        ),
    }
    payload["digest"] = _digest(payload)
    return payload


def render_batch_review_pack(pack: dict[str, Any]) -> str:
    return json.dumps(pack, indent=2, ensure_ascii=False) + "\n"


def build_study_findings(
    manifest_path: Path,
    cache_dir: Path,
    *,
    annex: str = "annex-i",
    generated_at: datetime | None = None,
    sample_size: int = DEFAULT_STUDY_SAMPLE_SIZE,
) -> dict[str, Any]:
    """Run the Title II Annex I study rules over cached public white papers."""
    if annex != "annex-i":
        raise SystemExit("This study runner supports only --annex annex-i.")

    timestamp = generated_at or datetime.now(UTC)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest.get("entries", [])
    if not isinstance(entries, list):
        raise SystemExit("Study manifest must contain an entries array.")

    processed: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = [
        _manifest_excluded(entry)
        for entry in entries
        if not entry.get("included")
        and entry.get("exclusion_reason")
        and entry.get("exclusion_reason") != "outside_v1_sample_candidate"
    ]

    included_entries = [entry for entry in entries if entry.get("included")]
    candidate_entries = [
        entry
        for entry in entries
        if not entry.get("included") and entry.get("exclusion_reason") == "outside_v1_sample_candidate"
    ]

    for entry in included_entries + candidate_entries:
        if len(processed) >= sample_size:
            break
        result = _process_study_entry(entry, cache_dir)
        if result["status"] == "included":
            processed.append(result["result"])
        else:
            excluded.append(result["excluded"])

    payload: dict[str, Any] = {
        "schema": STUDY_FINDINGS_SCHEMA,
        "study_id": manifest.get("study_id", "2026-07-title-ii-annex-i"),
        "generated_at": timestamp.isoformat(),
        "manifest_path": _portable_path(manifest_path),
        "cache_dir": _portable_path(cache_dir),
        "scope": manifest.get("scope", "Title II crypto-assets other than ARTs or EMTs"),
        "annex": "Annex I",
        "sample_target": sample_size,
        "sample_size": len(processed),
        "human_review_status": _aggregate_human_review_status(processed),
        "language_policy": (
            "Rows are machine-generated detector outputs. A flag means that the specified element "
            "was not found in extracted text. It is not a reviewed legal finding, legal advice, "
            "or a statement that an issuer failed to comply with MiCAR."
        ),
        "rules": [_study_rule_metadata(rule) for rule in STUDY_RULES],
        "summary": _study_summary(processed, excluded),
        "results": processed,
        "excluded_documents": excluded,
    }
    payload["digest"] = _digest(payload)
    return payload


def render_study_findings_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def write_study_findings_csv(payload: dict[str, Any], out: Path) -> None:
    fields = [
        "study_doc_id",
        "document_hash_sha256",
        "format",
        "annex",
        "rule_id",
        "annex_item",
        "finding_type",
        "confidence",
        "page_or_section",
        "missing_element",
        "matched_text",
        "human_review_status",
        "human_review_note",
    ]
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for result in payload["results"]:
            for finding in result["findings"]:
                writer.writerow(
                    {
                        "study_doc_id": result["study_doc_id"],
                        "document_hash_sha256": result["document_hash_sha256"],
                        "format": result["format"],
                        "annex": result["annex"],
                        "rule_id": finding["rule_id"],
                        "annex_item": finding["annex_item"],
                        "finding_type": finding["finding_type"],
                        "confidence": finding["confidence"],
                        "page_or_section": finding["evidence"]["page_or_section"],
                        "missing_element": finding["evidence"]["missing_element"],
                        "matched_text": finding["evidence"]["matched_text"],
                        "human_review_status": finding["human_review_status"],
                        "human_review_note": finding["human_review_note"],
                    }
                )


def _process_study_entry(entry: dict[str, Any], cache_dir: Path) -> dict[str, Any]:
    doc_id = str(entry.get("study_doc_id", ""))
    path = _resolve_cached_document(entry, cache_dir)
    if path is None:
        return {
            "status": "excluded",
            "excluded": _excluded(doc_id, "cached_document_not_found", entry),
        }
    if path.suffix.lower() not in STUDY_SUPPORTED_SUFFIXES:
        return {
            "status": "excluded",
            "excluded": _excluded(doc_id, f"unsupported_file_type:{path.suffix.lower()}", entry),
        }

    try:
        document = load_document(path)
    except Exception as exc:
        return {
            "status": "excluded",
            "excluded": _excluded(doc_id, f"document_load_failed:{type(exc).__name__}", entry),
        }

    if document.text_extraction != "ok":
        return {
            "status": "excluded",
            "excluded": _excluded(
                doc_id,
                f"insufficient_text_extraction:{document.text_extraction}",
                entry,
                document,
            ),
        }

    findings = [_study_finding(rule, document, entry) for rule in STUDY_RULES]
    open_findings = [finding for finding in findings if finding is not None]
    high_confidence = [finding for finding in open_findings if finding["confidence"] == "high"]

    return {
        "status": "included",
        "result": {
            "study_doc_id": doc_id,
            "document_hash_sha256": document.source_hash_sha256,
            "register_row_hash_sha256": entry.get("register_row_hash_sha256", ""),
            "format": document.format,
            "annex": "Annex I",
            "rules_checked": len(STUDY_RULES),
            "potential_gaps": len(open_findings),
            "high_confidence_gaps": len(high_confidence),
            "text_extraction": document.text_extraction,
            "extraction_metadata": {
                "format": document.format,
                "pages": document.pages,
                "warnings": document.warnings,
                "ixbrl_tag_count": len(document.ixbrl_tags),
                "label_count": len(document.labels),
            },
            "human_review_status": "pending_review",
            "findings": open_findings,
        },
    }


def _study_finding(
    rule: StudyRule,
    document: LoadedDocument,
    entry: dict[str, Any],
) -> dict[str, Any] | None:
    text = _study_search_text(document)
    if _rule_matches(rule, text):
        return None

    context = _find_context(text, rule.context_patterns)
    confidence = rule.confidence_if_context if context else rule.confidence_without_context
    return {
        "rule_id": rule.rule_id,
        "annex_item": rule.annex_item,
        "label": rule.label,
        "finding_type": "potential_disclosure_gap",
        "confidence": confidence,
        "machine_flagged": True,
        "evidence": {
            "page_or_section": _best_section(rule, document),
            "matched_text": _redact_snippet(context, entry),
            "missing_element": rule.missing_element,
        },
        "human_review_status": "pending_review",
        "human_review_note": "Pending qualified human legal review.",
    }


def _rule_matches(rule: StudyRule, text: str) -> bool:
    matches = [bool(re.search(pattern, text, flags=re.IGNORECASE)) for pattern in rule.required_patterns]
    if rule.match_policy == "all":
        return all(matches)
    return any(matches)


def _study_search_text(document: LoadedDocument) -> str:
    return " ".join(
        [
            document.text,
            " ".join(document.sections.values()),
            " ".join(document.ixbrl_tags),
            " ".join(document.labels),
        ]
    )


def _find_context(text: str, patterns: tuple[str, ...]) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            start = max(0, match.start() - 110)
            end = min(len(text), match.end() + 110)
            return re.sub(r"\s+", " ", text[start:end]).strip()
    return ""


def _best_section(rule: StudyRule, document: LoadedDocument) -> str:
    section_aliases = {
        "Summary": "summary",
        "Mandatory warnings": "risk_warning",
        "Management body statement": "management_statement",
        "Management body": "issuer",
        "Offeror information": "offeror",
        "Crypto-asset information": "crypto_asset",
        "Utility and characteristics": "crypto_asset",
    }
    section_key = section_aliases.get(rule.section_hint)
    if section_key and section_key in document.sections:
        return rule.section_hint
    return rule.section_hint or "Extracted text"


def _redact_snippet(text: str, entry: dict[str, Any]) -> str:
    if not text:
        return ""
    redacted = text[:260]
    redacted = re.sub(r"https?://\S+", "[URL]", redacted)
    redacted = re.sub(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}", "[EMAIL]", redacted)
    redacted = re.sub(r"\$[A-Z0-9]{2,12}\b", "[SYMBOL]", redacted)
    redacted = re.sub(r"(\+\d{1,3}[\s().-]*)?(?:\d[\s().-]*){7,}", "[PHONE]", redacted)
    for key, replacement in (
        ("offeror_or_issuer", "[ISSUER]"),
        ("casp_name", "[CASP]"),
        ("crypto_asset", "[CRYPTO_ASSET]"),
        ("ticker_or_identifier", "[IDENTIFIER]"),
    ):
        value = str(entry.get(key, "")).strip()
        if value:
            redacted = _redact_value(redacted, value, replacement)
    redacted = _redact_company_like_names(redacted)
    return redacted.strip()


def _redact_value(text: str, value: str, replacement: str) -> str:
    redacted = re.sub(re.escape(value), replacement, text, flags=re.IGNORECASE)
    for part in re.split(r"[^A-Za-z0-9]+", value):
        normalized = part.strip()
        if len(normalized) < 3 or normalized.lower() in _REDACTION_STOPWORDS:
            continue
        redacted = re.sub(rf"\b{re.escape(normalized)}\b", replacement, redacted, flags=re.IGNORECASE)
    return redacted


def _redact_company_like_names(text: str) -> str:
    suffixes = r"(?:AG|GmbH|S\.?A\.?|Ltd\.?|Limited|Inc\.?|LLC|Foundation|Association)"
    pattern = rf"\b(?:[A-Z][A-Za-z0-9&.'-]*\s+){{1,6}}{suffixes}\b"
    redacted = re.sub(pattern, "[ENTITY]", text)
    redacted = re.sub(r"\b[A-Z][A-Za-z0-9&.'-]{2,}\s+Token\b", "[CRYPTO_ASSET]", redacted)
    return re.sub(r"\b[A-Z][A-Za-z0-9&.'-]{2,}\s+Chain\b", "[NETWORK]", redacted)


_REDACTION_STOPWORDS = {
    "ag",
    "bvi",
    "company",
    "foundation",
    "gmbh",
    "inc",
    "limited",
    "llc",
    "ltd",
    "reserve",
    "sarl",
    "token",
}


def _resolve_cached_document(entry: dict[str, Any], cache_dir: Path) -> Path | None:
    explicit = str(entry.get("local_path", "")).strip()
    if explicit and Path(explicit).exists():
        return Path(explicit)

    preferred = str(entry.get("preferred_filename", "")).strip()
    if preferred:
        candidate = cache_dir / preferred
        if candidate.exists():
            return candidate

    doc_id = str(entry.get("study_doc_id", "")).strip()
    matches = sorted(
        path
        for path in cache_dir.glob(f"{doc_id}*")
        if path.is_file() and path.suffix.lower() in STUDY_SUPPORTED_SUFFIXES
    )
    return matches[0] if matches else None


def _excluded(
    doc_id: str,
    reason: str,
    entry: dict[str, Any],
    document: LoadedDocument | None = None,
) -> dict[str, Any]:
    payload = {
        "study_doc_id": doc_id,
        "register_row_hash_sha256": entry.get("register_row_hash_sha256", ""),
        "exclusion_reason": reason,
        "whitepaper_url_hash_sha256": _url_hash(str(entry.get("whitepaper_url", ""))),
    }
    if document:
        payload["document_hash_sha256"] = document.source_hash_sha256
        payload["format"] = document.format
        payload["text_extraction"] = document.text_extraction
        payload["warnings"] = document.warnings
    return payload


def _manifest_excluded(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "study_doc_id": entry.get("study_doc_id", ""),
        "register_row_hash_sha256": entry.get("register_row_hash_sha256", ""),
        "exclusion_reason": entry.get("exclusion_reason", "excluded_before_batch"),
        "whitepaper_url_hash_sha256": _url_hash(str(entry.get("whitepaper_url", ""))),
    }


def _url_hash(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest() if url else ""


def _study_rule_metadata(rule: StudyRule) -> dict[str, str]:
    return {
        "rule_id": rule.rule_id,
        "annex_item": rule.annex_item,
        "label": rule.label,
        "missing_element": rule.missing_element,
    }


def _study_summary(results: list[dict[str, Any]], excluded: list[dict[str, Any]]) -> dict[str, Any]:
    total_gaps = sum(int(result["potential_gaps"]) for result in results)
    high_gaps = sum(int(result["high_confidence_gaps"]) for result in results)
    by_rule: dict[str, int] = {}
    for result in results:
        for finding in result["findings"]:
            by_rule[finding["rule_id"]] = by_rule.get(finding["rule_id"], 0) + 1
    return {
        "documents_reviewed": len(results),
        "documents_excluded": len(excluded),
        "rules_checked_per_document": len(STUDY_RULES),
        "potential_gaps": total_gaps,
        "high_confidence_gaps": high_gaps,
        "most_frequent_potential_gaps": [
            {"rule_id": rule_id, "count": count}
            for rule_id, count in sorted(by_rule.items(), key=lambda item: (-item[1], item[0]))
        ],
    }


def _aggregate_human_review_status(results: list[dict[str, Any]]) -> str:
    statuses = {result.get("human_review_status", "pending_review") for result in results}
    return "reviewed" if statuses == {"reviewed"} else "pending_review"


def _portable_path(path: Path) -> str:
    """Return a stable relative locator without leaking a local home-directory path."""
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return path.name


def _digest(payload: dict[str, Any]) -> str:
    unsigned = {key: value for key, value in payload.items() if key != "digest"}
    encoded = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_study_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="micar-lint-batch",
        description="Run deterministic Title II Annex I study checks over cached public white papers.",
    )
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--cache", required=True, type=Path)
    parser.add_argument("--annex", default="annex-i")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--sample-size", type=int, default=DEFAULT_STUDY_SAMPLE_SIZE)
    return parser


def main_study_batch(argv: list[str] | None = None) -> int:
    args = build_study_parser().parse_args(argv)
    payload = build_study_findings(
        args.manifest,
        args.cache,
        annex=args.annex,
        sample_size=args.sample_size,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render_study_findings_json(payload), encoding="utf-8")
    csv_path = args.out.with_suffix(".csv")
    write_study_findings_csv(payload, csv_path)
    print(
        (
            "Study findings written to {json_path} and {csv_path}. "
            "Documents processed: {docs}. Candidate flags: {gaps}."
        ).format(
            json_path=args.out,
            csv_path=csv_path,
            docs=payload["summary"]["documents_reviewed"],
            gaps=payload["summary"]["potential_gaps"],
        ),
        file=sys.stderr,
    )
    return 0
