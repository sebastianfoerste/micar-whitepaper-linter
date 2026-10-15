from __future__ import annotations

import io
from datetime import UTC, datetime
from pathlib import Path

import pytest

from micar_linter import esma_register
from micar_linter.esma_register import build_source_manifest


def test_esma_register_normalizes_official_other_csv(tmp_path: Path):
    csv_path = tmp_path / "OTHER.csv"
    csv_path.write_text(
        "\n".join(
            [
                "ae_competentAuthority,ae_homeMemberState,ae_lei_name,ae_lei,ae_lei_cou_code,"
                "ae_lei_name_casp,ae_lei_casp,ae_offerCode_cou,ae_DTI_FFG,ae_DTI,wp_url,"
                "wp_comments,wp_lastupdate",
                "Federal Financial Supervisory Authority (BaFin),DE,Example GmbH,LEI123,DE,"
                ",,,FFG123,DTI456,https://example.test/wp.xhtml,,02/07/2026",
            ]
        ),
        encoding="utf-8",
    )

    manifest = build_source_manifest(
        csv_path,
        retrieved_at=datetime(2026, 7, 2, tzinfo=UTC),
    )
    entry = manifest["entries"][0]

    assert manifest["study_id"] == "2026-07-title-ii-annex-i"
    assert manifest["register_source_detail"] == "OTHER.csv"
    assert manifest["identifier_policy"].startswith("WP identifiers are pseudonymous")
    assert len(manifest["register_source_sha256"]) == 64
    assert entry["study_doc_id"] == "WP-001"
    assert entry["asset_type"] == "Title II"
    assert entry["home_member_state"] == "DE"
    assert entry["competent_authority"] == "Federal Financial Supervisory Authority (BaFin)"
    assert entry["whitepaper_url"] == "https://example.test/wp.xhtml"
    assert entry["included"] is True
    assert len(entry["register_row_hash_sha256"]) == 64


def test_esma_register_normalizes_bare_official_urls(tmp_path: Path):
    csv_path = tmp_path / "OTHER.csv"
    csv_path.write_text(
        "\n".join(
            [
                "ae_competentAuthority,ae_homeMemberState,ae_lei_name,ae_lei,ae_lei_cou_code,"
                "ae_lei_name_casp,ae_lei_casp,ae_offerCode_cou,ae_DTI_FFG,ae_DTI,wp_url,"
                "wp_comments,wp_lastupdate",
                "Austrian Financial Market Authority (FMA),AT,Example GmbH,LEI123,AT,"
                ",,,FFG123,DTI456,WWW.EXAMPLE.AT/path,,03/07/2026",
            ]
        ),
        encoding="utf-8",
    )

    manifest = build_source_manifest(csv_path, retrieved_at=datetime(2026, 7, 6, tzinfo=UTC))
    entry = manifest["entries"][0]

    assert entry["whitepaper_url"] == "https://WWW.EXAMPLE.AT/path"
    assert entry["landing_page_url"] == "https://WWW.EXAMPLE.AT/path"


def test_source_pack_selection_is_first_ten_and_stable(tmp_path: Path):
    csv_path = tmp_path / "sample-manifest.csv"
    rows = [
        "study_doc_id,asset_type,home_member_state,competent_authority,whitepaper_url,"
        "preferred_filename,format_hint,register_row_hash_sha256"
    ]
    for index in range(1, 13):
        rows.append(
            f"WP-{index:03d},Title II / crypto-assets other than ARTs or EMTs,DE,BaFin,"
            f"https://example.test/wp-{index}.html,WP-{index:03d}.html,HTML,"
        )
    csv_path.write_text("\n".join(rows), encoding="utf-8")

    first = build_source_manifest(csv_path, retrieved_at=datetime(2026, 7, 2, tzinfo=UTC))
    second = build_source_manifest(csv_path, retrieved_at=datetime(2026, 7, 2, tzinfo=UTC))

    included = [entry["study_doc_id"] for entry in first["entries"] if entry["included"]]
    excluded = [entry for entry in first["entries"] if not entry["included"]]

    assert included == [f"WP-{index:03d}" for index in range(1, 11)]
    assert excluded[0]["study_doc_id"] == "WP-011"
    assert excluded[0]["exclusion_reason"] == "outside_v1_sample_candidate"
    assert first["entries"][0]["register_row_hash_sha256"] == second["entries"][0]["register_row_hash_sha256"]


def test_register_marks_outdated_rows_excluded(tmp_path: Path):
    csv_path = tmp_path / "sample-manifest.csv"
    csv_path.write_text(
        "\n".join(
            [
                "study_doc_id,asset_type,whitepaper_url,notes",
                "WP-001,Title II / crypto-assets other than ARTs or EMTs,https://example.test/wp.html,"
                "superseded by newer filing",
            ]
        ),
        encoding="utf-8",
    )

    manifest = build_source_manifest(csv_path, retrieved_at=datetime(2026, 7, 2, tzinfo=UTC))

    assert manifest["entries"][0]["included"] is False
    assert manifest["entries"][0]["exclusion_reason"] == "out_of_date_or_superseded"


@pytest.mark.parametrize(
    "url",
    [
        "http://www.esma.europa.eu/x.csv",
        "https://evil.example/x.csv",
        "https://esma.europa.eu.evil.example/x.csv",
        "https://notesma.europa.eu/x.csv",
        "https://user:pw@www.esma.europa.eu/x.csv",
    ],
)
def test_register_url_rejected_outside_https_esma(url):
    with pytest.raises(SystemExit):
        esma_register.build_source_manifest(url)


def test_register_url_allows_esma_hosts():
    for url in ("https://www.esma.europa.eu/a.csv", "https://esma.europa.eu/a.csv"):
        esma_register._validate_esma_url(url)


class _FakeOpener:
    def __init__(self, payload: bytes):
        self.payload = payload

    def open(self, req, timeout=None):
        return io.BytesIO(self.payload)


def test_register_fetch_enforces_size_cap(monkeypatch):
    monkeypatch.setattr(
        esma_register.urllib.request, "build_opener", lambda *a: _FakeOpener(b"x" * 11)
    )
    with pytest.raises(SystemExit):
        esma_register._fetch_esma_url("https://www.esma.europa.eu/a.csv", max_bytes=10)
    assert esma_register._fetch_esma_url("https://www.esma.europa.eu/a.csv", max_bytes=11) == b"x" * 11


def test_register_redirect_to_other_host_rejected():
    handler = esma_register._EsmaRedirectHandler()
    req = esma_register.urllib.request.Request("https://www.esma.europa.eu/a.csv")
    with pytest.raises(SystemExit):
        handler.redirect_request(req, None, 302, "Found", {}, "https://evil.example/a.csv")
