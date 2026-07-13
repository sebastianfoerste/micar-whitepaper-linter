from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

from micar_linter.batch import (
    build_study_findings,
    render_study_findings_json,
    write_study_findings_csv,
)
from micar_linter.study_report import render_study_report


def _manifest(tmp_path: Path) -> Path:
    manifest_path = tmp_path / "source-manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "study_id": "2026-07-title-ii-annex-i",
                "scope": "Title II crypto-assets other than ARTs or EMTs",
                "register_source_detail": "fixture-source.csv",
                "register_source_sha256": "d" * 64,
                "entries": [
                    {
                        "study_doc_id": "WP-001",
                        "asset_type": "Title II",
                        "offeror_or_issuer": "Example Issuer Ltd",
                        "crypto_asset": "Example Token",
                        "ticker_or_identifier": "EXT",
                        "whitepaper_url": "https://example.test/wp-001.html",
                        "preferred_filename": "WP-001_example.html",
                        "register_row_hash_sha256": "a" * 64,
                        "included": True,
                        "exclusion_reason": None,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return manifest_path


def _cached_html(cache: Path) -> None:
    cache.mkdir()
    body = " ".join(
        [
            "Summary key information for holders of Example Token with risks and value loss warning.",
            "Contact: research@example.test for investor questions.",
            "The token utility and characteristics are described for transfer and use.",
        ]
        * 35
    )
    (cache / "WP-001_example.html").write_text(
        f"""<html>
  <body>
    <h1>Summary</h1>
    <p>{body}</p>
  </body>
</html>""",
        encoding="utf-8",
    )


def test_study_batch_outputs_anonymized_pending_review_findings(tmp_path: Path):
    manifest_path = _manifest(tmp_path)
    cache = tmp_path / "cache"
    _cached_html(cache)

    payload = build_study_findings(
        manifest_path,
        cache,
        generated_at=datetime(2026, 7, 2, tzinfo=UTC),
    )
    rendered = render_study_findings_json(payload)

    assert payload["schema"] == "micar-whitepaper-linter.title-ii-annex-i-study-findings.v1"
    assert payload["summary"]["documents_reviewed"] == 1
    assert payload["source_manifest"]["register_source_sha256"] == "d" * 64
    assert payload["results"][0]["study_doc_id"] == "WP-001"
    assert payload["results"][0]["human_review_status"] == "pending_review"
    assert payload["results"][0]["rules_checked"] == 15
    assert payload["results"][0]["potential_gaps"] > 0
    assert "research@example.test" not in rendered
    assert "Example Issuer Ltd" not in rendered
    assert "Example Token" not in rendered
    assert "[EMAIL]" in rendered
    assert not re.search(r"violation|illegal|breach|non-compliant", rendered, flags=re.IGNORECASE)


def test_study_batch_writes_flat_csv(tmp_path: Path):
    manifest_path = _manifest(tmp_path)
    cache = tmp_path / "cache"
    _cached_html(cache)
    payload = build_study_findings(manifest_path, cache)
    csv_path = tmp_path / "findings-anonymized.csv"

    write_study_findings_csv(payload, csv_path)
    csv_text = csv_path.read_text(encoding="utf-8")

    assert "study_doc_id,record_type,document_status,document_hash_sha256" in csv_text
    assert "WP-001" in csv_text
    assert "pending_review" in csv_text


def test_study_batch_carries_manifest_exclusions(tmp_path: Path):
    manifest_path = tmp_path / "source-manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "study_id": "2026-07-title-ii-annex-i",
                "scope": "Title II crypto-assets other than ARTs or EMTs",
                "entries": [
                    {
                        "study_doc_id": "WP-001",
                        "asset_type": "Title II",
                        "whitepaper_url": "https://example.test/missing.pdf",
                        "preferred_filename": "missing.pdf",
                        "register_row_hash_sha256": "c" * 64,
                        "included": False,
                        "exclusion_reason": "cached_document_not_found",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    cache = tmp_path / "cache"
    cache.mkdir()

    payload = build_study_findings(manifest_path, cache)

    assert payload["summary"]["documents_excluded"] == 1
    assert payload["excluded_documents"][0]["study_doc_id"] == "WP-001"
    assert payload["excluded_documents"][0]["exclusion_reason"] == "cached_document_not_found"

    csv_path = tmp_path / "findings-anonymized.csv"
    write_study_findings_csv(payload, csv_path)
    csv_text = csv_path.read_text(encoding="utf-8")

    assert "exclusion,excluded" in csv_text
    assert "cached_document_not_found" in csv_text


def test_study_report_contains_required_sections_and_pending_review(tmp_path: Path):
    manifest_path = _manifest(tmp_path)
    cache = tmp_path / "cache"
    _cached_html(cache)
    payload = build_study_findings(manifest_path, cache)

    report = render_study_report(payload)

    assert "# 10 Notified MiCAR Title II White Papers Reviewed" in report
    for heading in (
        "## Sample",
        "## Methodology",
        "## What the linter checks",
        "## What it does not check",
        "## Aggregate findings",
        "## Most frequent potential gaps",
        "## Excluded documents",
        "## Examples pending human review",
        "## Limitations",
        "## Reproducibility",
    ):
        assert heading in report
    assert "Human review status: pending_review" in report
    assert "Source manifest input SHA-256" in report


def test_study_rules_accept_response_time_and_ticker_title(tmp_path: Path):
    manifest_path = tmp_path / "source-manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "study_id": "2026-07-title-ii-annex-i",
                "scope": "Title II crypto-assets other than ARTs or EMTs",
                "entries": [
                    {
                        "study_doc_id": "WP-001",
                        "asset_type": "Title II",
                        "offeror_or_issuer": "Named Parent Limited",
                        "crypto_asset": "Example Token",
                        "ticker_or_identifier": "EXT",
                        "whitepaper_url": "https://example.test/wp.html",
                        "preferred_filename": "WP-001.html",
                        "register_row_hash_sha256": "b" * 64,
                        "included": True,
                        "exclusion_reason": None,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    cache = tmp_path / "cache"
    cache.mkdir()
    text = " ".join(
        [
            "Example Token ($EXT) crypto-asset white paper.",
            "A.10 Response time (Days) Response time: 7 days.",
            "Named Parent Limited is mentioned near the source text.",
            "Contact: help@example.test +49 3012345678.",
            "Conflicts of interest are governed by a conflict policy.",
        ]
        * 30
    )
    (cache / "WP-001.html").write_text(f"<html><body><p>{text}</p></body></html>", encoding="utf-8")

    payload = build_study_findings(manifest_path, cache)
    finding_ids = {
        finding["rule_id"]
        for result in payload["results"]
        for finding in result["findings"]
    }
    rendered = render_study_findings_json(payload)

    assert "ANNEX_I_PART_A_06_CONTACT_RESPONSE_PERIOD" not in finding_ids
    assert "ANNEX_I_PART_D_01_ASSET_NAME_ABBREVIATION" not in finding_ids
    assert "Named Parent Limited" not in rendered
