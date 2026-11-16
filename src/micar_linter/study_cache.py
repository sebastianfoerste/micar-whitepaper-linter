"""Verify locally cached study white papers against the SHA-256 values in document-provenance.json.

The check is offline: it reads local files only and never opens a network connection. Each
processed document is resolved in the cache exactly as ``micar-lint-batch`` resolves it
(``local_path``, then ``preferred_filename`` from the source manifest, then the first file named
``<study_doc_id>*``), so a pass means that the batch would read the recorded bytes.

Exit status: 0 when every document is ``ok``; 1 when any document is ``mismatch``; 3 when none
mismatches but at least one is ``missing``; 2 for usage or input errors.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from micar_linter.artifact_manifest import file_sha256
from micar_linter.batch import _resolve_cached_document

CACHE_REPORT_SCHEMA = "micar-study-cache-verification.v1"
DEFAULT_CACHE_DIR = Path(".study-cache/title-ii-whitepapers")
EXIT_OK = 0
EXIT_MISMATCH = 1
EXIT_USAGE = 2
EXIT_MISSING = 3


def verify_study_cache(
    provenance_path: Path,
    cache_dir: Path,
    *,
    manifest_path: Path | None = None,
    include_candidates: bool = False,
) -> dict[str, Any]:
    """Return a verification report for every document recorded in the provenance file."""
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    documents = provenance.get("documents")
    if not isinstance(documents, list) or not documents:
        raise ValueError(f"{provenance_path.name} has no documents array")

    manifest_file = manifest_path or _default_manifest(provenance, provenance_path)
    entries = _manifest_entries(manifest_file)
    hash_index: dict[str, list[str]] | None = None

    results: list[dict[str, Any]] = []
    for document in documents:
        doc_id = str(document.get("study_doc_id", "")).strip()
        expected = str(document.get("document_sha256", "")).strip().lower()
        if not doc_id or len(expected) != 64:
            raise ValueError(f"provenance entry {doc_id or '?'} lacks a study_doc_id or SHA-256")
        entry = entries.get(doc_id, {"study_doc_id": doc_id})
        path = _resolve_cached_document(entry, cache_dir) if cache_dir.is_dir() else None
        actual = file_sha256(path) if path else ""
        status = "missing" if path is None else ("ok" if actual == expected else "mismatch")
        item: dict[str, Any] = {
            "study_doc_id": doc_id,
            "status": status,
            "expected_sha256": expected,
            "actual_sha256": actual,
            "file": _display_path(path, cache_dir),
        }
        if status != "ok":
            if hash_index is None:
                hash_index = _hash_index(cache_dir)
            item["expected_bytes_found_at"] = hash_index.get(expected, [])
        results.append(item)

    report: dict[str, Any] = {
        "schema_version": CACHE_REPORT_SCHEMA,
        "provenance_file": provenance_path.name,
        "manifest_file": manifest_file.name if manifest_file else "",
        "cache_dir": str(cache_dir),
        "cache_dir_exists": cache_dir.is_dir(),
        "counts": {
            status: sum(1 for item in results if item["status"] == status)
            for status in ("ok", "mismatch", "missing")
        },
        "documents": results,
    }
    report["all_verified"] = report["counts"]["ok"] == len(results)
    if include_candidates:
        recorded = {item["study_doc_id"] for item in results}
        report["candidates"] = [
            _candidate(entry, cache_dir) for doc_id, entry in entries.items() if doc_id not in recorded
        ]
    return report


def exit_status(report: Mapping[str, Any]) -> int:
    counts = report["counts"]
    if counts["mismatch"]:
        return EXIT_MISMATCH
    if counts["missing"]:
        return EXIT_MISSING
    return EXIT_OK


def render_text(report: Mapping[str, Any]) -> str:
    lines = [
        f"Cache: {report['cache_dir']}" + ("" if report["cache_dir_exists"] else " (directory not found)"),
        f"Reference: {report['provenance_file']}",
        "",
    ]
    for item in report["documents"]:
        actual = item["actual_sha256"][:12] or "-"
        line = (
            f"{item['study_doc_id']}  {item['status']:<8}  expected {item['expected_sha256'][:12]}  "
            f"actual {actual:<12}  {item['file'] or '-'}"
        )
        found = item.get("expected_bytes_found_at")
        if found:
            line += f"  (recorded bytes found at: {', '.join(found)})"
        lines.append(line)
    counts = report["counts"]
    lines.extend(
        [
            "",
            f"ok {counts['ok']}, mismatch {counts['mismatch']}, missing {counts['missing']} "
            f"of {len(report['documents'])} recorded documents.",
        ]
    )
    candidates = report.get("candidates")
    if candidates is not None:
        lines.extend(["", "Manifest entries without a recorded hash (not verified):"])
        if not candidates:
            lines.append("none")
        for item in candidates:
            sha = item["sha256"][:12] or "-"
            lines.append(
                f"{item['study_doc_id']}  {item['status']:<14}  sha256 {sha:<12}  {item['file'] or '-'}"
            )
    return "\n".join(lines) + "\n"


def _default_manifest(provenance: Mapping[str, Any], provenance_path: Path) -> Path | None:
    name = str(provenance.get("manifest_path", "")).strip()
    if not name:
        return None
    candidate = provenance_path.parent / name
    return candidate if candidate.exists() else None


def _manifest_entries(manifest_path: Path | None) -> dict[str, dict[str, Any]]:
    if manifest_path is None:
        return {}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest.get("entries", [])
    if not isinstance(entries, list):
        raise ValueError(f"{manifest_path.name} entries is not a list")
    return {str(entry.get("study_doc_id", "")): entry for entry in entries if entry.get("study_doc_id")}


def _candidate(entry: Mapping[str, Any], cache_dir: Path) -> dict[str, Any]:
    path = _resolve_cached_document(dict(entry), cache_dir) if cache_dir.is_dir() else None
    return {
        "study_doc_id": entry.get("study_doc_id", ""),
        "status": "cached_no_hash" if path else "not_cached",
        "sha256": file_sha256(path) if path else "",
        "file": _display_path(path, cache_dir),
    }


def _hash_index(cache_dir: Path) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    if not cache_dir.is_dir():
        return index
    for path in sorted(item for item in cache_dir.rglob("*") if item.is_file()):
        index.setdefault(file_sha256(path), []).append(_display_path(path, cache_dir))
    return index


def _display_path(path: Path | None, cache_dir: Path) -> str:
    if path is None:
        return ""
    try:
        return str(path.resolve().relative_to(cache_dir.resolve()))
    except ValueError:
        return path.name


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="micar-study-verify-cache",
        description=(
            "Offline check of cached study white papers against the SHA-256 values in "
            "document-provenance.json. Exit 0 all ok, 1 any mismatch, 3 any missing."
        ),
    )
    parser.add_argument("--provenance", required=True, type=Path, help="document-provenance.json")
    parser.add_argument(
        "--cache",
        type=Path,
        default=DEFAULT_CACHE_DIR,
        help=f"cache directory (default {DEFAULT_CACHE_DIR})",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="source manifest for file names (default: manifest_path in the provenance file)",
    )
    parser.add_argument(
        "--include-candidates",
        action="store_true",
        help="also list manifest entries without a recorded hash, such as WP-013 to WP-020",
    )
    parser.add_argument("--json-out", type=Path, help="also write the report as JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = verify_study_cache(
            args.provenance,
            args.cache,
            manifest_path=args.manifest,
            include_candidates=args.include_candidates,
        )
    except (OSError, ValueError) as exc:
        print(f"micar-study-verify-cache: {exc}", file=sys.stderr)
        return EXIT_USAGE
    sys.stdout.write(render_text(report))
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return exit_status(report)


if __name__ == "__main__":
    raise SystemExit(main())
