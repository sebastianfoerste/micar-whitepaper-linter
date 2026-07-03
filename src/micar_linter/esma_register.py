"""ESMA MiCA Title II register normalization for the Annex I study."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
import urllib.request
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import Any

STUDY_ID = "2026-07-title-ii-annex-i"
REGISTER_SOURCE = "ESMA Interim MiCA Register"
TITLE_II_SCOPE = "Title II crypto-assets other than asset-referenced tokens and e-money tokens"
OFFICIAL_TITLE_II_CSV = "https://www.esma.europa.eu/sites/default/files/2024-12/OTHER.csv"
ESMA_MICA_PAGE = (
    "https://www.esma.europa.eu/esmas-activities/digital-finance-and-innovation/"
    "markets-crypto-assets-regulation-mica"
)
DEFAULT_SAMPLE_SIZE = 10
DEFAULT_RANDOM_SEED = 20260702
USER_AGENT = "Mozilla/5.0 (compatible; MiCAR-Annex-I-Study/0.1; research)"


def build_source_manifest(
    source: str | Path,
    *,
    sample_size: int = DEFAULT_SAMPLE_SIZE,
    sample_method: str = "first",
    random_seed: int = DEFAULT_RANDOM_SEED,
    retrieved_at: datetime | None = None,
) -> dict[str, Any]:
    """Read a CSV, JSON manifest, or URL and return a study source manifest."""
    timestamp = retrieved_at or datetime.now(UTC)
    rows, source_label = _load_source_rows(source)
    entries = [_normalize_row(row, index + 1) for index, row in enumerate(rows)]
    selected_ids = _select_entry_ids(entries, sample_size=sample_size, method=sample_method, seed=random_seed)

    for entry in entries:
        if entry["study_doc_id"] in selected_ids:
            entry["included"] = True
            entry["exclusion_reason"] = None
        elif entry["_eligible"]:
            entry["included"] = False
            entry["exclusion_reason"] = "outside_v1_sample_candidate"
        else:
            entry["included"] = False
            entry["exclusion_reason"] = entry["_eligibility_reason"]
        del entry["_eligible"]
        del entry["_eligibility_reason"]

    return {
        "study_id": STUDY_ID,
        "retrieved_at": timestamp.isoformat(),
        "register_source": REGISTER_SOURCE,
        "register_source_detail": source_label,
        "official_esma_title_ii_csv": OFFICIAL_TITLE_II_CSV,
        "esma_mica_page": ESMA_MICA_PAGE,
        "scope": TITLE_II_SCOPE,
        "sample_method": sample_method,
        "sample_size": sample_size,
        "random_seed": random_seed if sample_method == "random" else None,
        "raw_files_included": False,
        "raw_file_policy": (
            "Raw white papers are not committed. Fetch locally into .study-cache/ and commit only "
            "metadata, hashes, anonymized findings, methodology, limitations, and rendered reports."
        ),
        "entries": entries,
    }


def render_manifest(manifest: dict[str, Any]) -> str:
    return json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"


def write_sample_manifest_csv(manifest: dict[str, Any], out: Path) -> None:
    """Write a compact CSV containing the included v1 sample."""
    out.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "study_doc_id",
        "asset_type",
        "home_member_state",
        "competent_authority",
        "last_update",
        "format_hint",
        "whitepaper_url",
        "preferred_filename",
        "included",
        "exclusion_reason",
        "register_row_hash_sha256",
    ]
    rows = [entry for entry in manifest["entries"] if entry.get("included")]
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for entry in rows:
            writer.writerow({field: entry.get(field, "") for field in fields})


def _load_source_rows(source: str | Path) -> tuple[list[dict[str, Any]], str]:
    source_text = str(source)
    if source_text.startswith(("http://", "https://")):
        req = urllib.request.Request(source_text, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=30) as response:
            text = response.read().decode("utf-8-sig")
        return list(csv.DictReader(StringIO(text))), source_text

    path = Path(source)
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        rows = data.get("entries")
        if not isinstance(rows, list):
            raise SystemExit(f"JSON manifest must contain an entries array: {path}")
        return [dict(row) for row in rows], str(path)

    text = path.read_text(encoding="utf-8-sig")
    return list(csv.DictReader(StringIO(text))), str(path)


def _normalize_row(row: dict[str, Any], index: int) -> dict[str, Any]:
    entry = (
        _normalize_official_row(row, index)
        if "wp_url" in row
        else _normalize_source_pack_row(row, index)
    )

    entry["register_row_hash_sha256"] = str(
        row.get("register_row_hash_sha256") or _row_hash(entry)
    )
    eligible, reason = _eligibility(entry)
    entry["_eligible"] = eligible
    entry["_eligibility_reason"] = reason
    return entry


def _normalize_official_row(row: dict[str, Any], index: int) -> dict[str, Any]:
    doc_id = f"WP-{index:03d}"
    whitepaper_url = _clean(row.get("wp_url"))
    return {
        "study_doc_id": doc_id,
        "asset_type": "Title II",
        "home_member_state": _clean(row.get("ae_homeMemberState")),
        "competent_authority": _clean(row.get("ae_competentAuthority")),
        "offeror_or_issuer": _clean(row.get("ae_lei_name")),
        "lei": _clean(row.get("ae_lei")),
        "lei_country": _clean(row.get("ae_lei_cou_code")),
        "casp_name": _clean(row.get("ae_lei_name_casp")),
        "casp_lei": _clean(row.get("ae_lei_casp")),
        "offer_countries": _clean(row.get("ae_offerCode_cou")),
        "crypto_asset": "",
        "ticker_or_identifier": _join_clean(row.get("ae_DTI_FFG"), row.get("ae_DTI")),
        "dti_functionally_fungible_group": _clean(row.get("ae_DTI_FFG")),
        "dti": _clean(row.get("ae_DTI")),
        "whitepaper_url": whitepaper_url,
        "landing_page_url": whitepaper_url,
        "preferred_filename": _preferred_filename(doc_id, whitepaper_url),
        "last_update": _clean(row.get("wp_lastupdate")),
        "format_hint": _format_hint(whitepaper_url),
        "register_comments": _clean(row.get("wp_comments")),
    }


def _normalize_source_pack_row(row: dict[str, Any], index: int) -> dict[str, Any]:
    doc_id = _clean(row.get("study_doc_id")) or f"WP-{index:03d}"
    whitepaper_url = _clean(row.get("whitepaper_url"))
    return {
        "study_doc_id": doc_id,
        "asset_type": _clean(row.get("asset_type")) or "Title II",
        "home_member_state": _clean(row.get("home_member_state")),
        "competent_authority": _clean(row.get("competent_authority")),
        "offeror_or_issuer": _clean(row.get("offeror_or_issuer")),
        "lei": _clean(row.get("lei")),
        "lei_country": _clean(row.get("lei_country")),
        "casp_name": _clean(row.get("casp_name")),
        "casp_lei": _clean(row.get("casp_lei")),
        "offer_countries": _clean(row.get("offer_countries")),
        "crypto_asset": _clean(row.get("crypto_asset")),
        "ticker_or_identifier": _clean(row.get("ticker_or_identifier")),
        "dti_functionally_fungible_group": _clean(row.get("dti_functionally_fungible_group")),
        "dti": _clean(row.get("dti")),
        "whitepaper_url": whitepaper_url,
        "landing_page_url": _clean(row.get("landing_page_url")) or whitepaper_url,
        "preferred_filename": _clean(row.get("preferred_filename"))
        or _preferred_filename(doc_id, whitepaper_url),
        "last_update": _clean(row.get("last_update")),
        "format_hint": _clean(row.get("format_hint")) or _format_hint(whitepaper_url),
        "register_comments": _clean(row.get("register_comments") or row.get("notes")),
        "source_register_view": _clean(row.get("source_register_view")),
    }


def _select_entry_ids(
    entries: list[dict[str, Any]],
    *,
    sample_size: int,
    method: str,
    seed: int,
) -> set[str]:
    eligible = [entry for entry in entries if entry["_eligible"]]
    if method == "first":
        selected = eligible[:sample_size]
    elif method == "random":
        selected = list(eligible)
        random.Random(seed).shuffle(selected)
        selected = selected[:sample_size]
    else:
        raise SystemExit("sample method must be 'first' or 'random'")
    return {entry["study_doc_id"] for entry in selected}


def _eligibility(entry: dict[str, Any]) -> tuple[bool, str | None]:
    if "title ii" not in entry["asset_type"].lower() and entry["asset_type"].lower() != "title ii":
        return False, "outside_title_ii_scope"
    if not entry["whitepaper_url"]:
        return False, "missing_whitepaper_url"
    comments = " ".join(
        str(entry.get(key, "")) for key in ("register_comments", "format_hint", "whitepaper_url")
    ).lower()
    if any(token in comments for token in ("out-of-date", "outdated", "superseded", "withdrawn")):
        return False, "out_of_date_or_superseded"
    return True, None


def _row_hash(entry: dict[str, Any]) -> str:
    hashable = {
        key: value
        for key, value in entry.items()
        if key
        not in {
            "study_doc_id",
            "included",
            "exclusion_reason",
            "_eligible",
            "_eligibility_reason",
        }
    }
    encoded = json.dumps(hashable, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _preferred_filename(doc_id: str, url: str) -> str:
    suffix = Path(url.split("?", 1)[0]).suffix.lower()
    if suffix not in {".xhtml", ".html", ".pdf", ".txt"}:
        suffix = ".html"
    return f"{doc_id.lower()}_whitepaper{suffix}"


def _format_hint(url: str) -> str:
    suffix = Path(url.split("?", 1)[0]).suffix.lower()
    if suffix == ".pdf":
        return "PDF"
    if suffix == ".xhtml":
        return "XHTML"
    if suffix == ".txt":
        return "Text"
    return "HTML"


def _join_clean(*values: Any) -> str:
    return " / ".join(value for value in (_clean(item) for item in values) if value)


def _clean(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"\s+", " ", text)
    return text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Normalize ESMA MiCA Title II register data into a reproducible study manifest."
    )
    parser.add_argument("--csv", required=True, help="Local CSV/JSON source path or HTTPS URL.")
    parser.add_argument("--out", required=True, type=Path, help="Path to write source-manifest.json.")
    parser.add_argument("--sample-size", type=int, default=DEFAULT_SAMPLE_SIZE)
    parser.add_argument("--sample-method", choices=["first", "random"], default="first")
    parser.add_argument("--random-seed", type=int, default=DEFAULT_RANDOM_SEED)
    parser.add_argument("--sample-csv", type=Path, help="Optional path to write included sample CSV.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manifest = build_source_manifest(
        args.csv,
        sample_size=args.sample_size,
        sample_method=args.sample_method,
        random_seed=args.random_seed,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render_manifest(manifest), encoding="utf-8")
    if args.sample_csv:
        write_sample_manifest_csv(manifest, args.sample_csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
