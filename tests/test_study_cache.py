from __future__ import annotations

import hashlib
import json
import socket
from pathlib import Path

import pytest

from micar_linter.study_cache import (
    EXIT_MISMATCH,
    EXIT_MISSING,
    EXIT_OK,
    exit_status,
    main,
    render_text,
    verify_study_cache,
)

STUDY = Path(__file__).resolve().parents[1] / "studies" / "2026-07-title-ii-annex-i-whitepaper-study"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _study(tmp_path: Path, documents: dict[str, bytes], extra_entries: tuple[str, ...] = ()) -> Path:
    """Write a synthetic provenance file and manifest that record the given bytes."""
    study = tmp_path / "study"
    study.mkdir()
    entries = [
        {"study_doc_id": doc_id, "preferred_filename": f"{doc_id}_synthetic.html", "included": True}
        for doc_id in [*documents, *extra_entries]
    ]
    (study / "source-manifest.json").write_text(json.dumps({"entries": entries}), encoding="utf-8")
    provenance = {
        "manifest_path": "source-manifest.json",
        "documents": [
            {"study_doc_id": doc_id, "document_sha256": _sha(data)} for doc_id, data in documents.items()
        ],
    }
    path = study / "document-provenance.json"
    path.write_text(json.dumps(provenance), encoding="utf-8")
    return path


@pytest.fixture
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args, **kwargs):
        raise AssertionError("the cache verifier must not open network connections")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)


def test_reports_ok_mismatch_and_missing_offline(tmp_path: Path, no_network: None):
    provenance = _study(tmp_path, {"WP-001": b"one", "WP-002": b"two", "WP-003": b"three"})
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "WP-001_synthetic.html").write_bytes(b"one")
    (cache / "WP-002_synthetic.html").write_bytes(b"two, edited")

    report = verify_study_cache(provenance, cache)
    statuses = {item["study_doc_id"]: item["status"] for item in report["documents"]}

    assert statuses == {"WP-001": "ok", "WP-002": "mismatch", "WP-003": "missing"}
    assert report["counts"] == {"ok": 1, "mismatch": 1, "missing": 1}
    assert report["all_verified"] is False
    assert exit_status(report) == EXIT_MISMATCH
    mismatch = report["documents"][1]
    assert mismatch["actual_sha256"] == _sha(b"two, edited")
    assert mismatch["expected_sha256"] == _sha(b"two")
    assert "WP-002  mismatch" in render_text(report)


def test_all_ok_exits_zero(tmp_path: Path, no_network: None, capsys: pytest.CaptureFixture[str]):
    provenance = _study(tmp_path, {"WP-001": b"one", "WP-002": b"two"})
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "WP-001_synthetic.html").write_bytes(b"one")
    (cache / "WP-002_synthetic.html").write_bytes(b"two")
    json_out = tmp_path / "report.json"

    code = main(["--provenance", str(provenance), "--cache", str(cache), "--json-out", str(json_out)])

    assert code == EXIT_OK
    assert "ok 2, mismatch 0, missing 0" in capsys.readouterr().out
    assert json.loads(json_out.read_text(encoding="utf-8"))["all_verified"] is True


def test_missing_only_exits_three(tmp_path: Path, no_network: None):
    provenance = _study(tmp_path, {"WP-001": b"one"})

    assert main(["--provenance", str(provenance), "--cache", str(tmp_path / "absent")]) == EXIT_MISSING


def test_points_to_recorded_bytes_stored_under_another_name(tmp_path: Path, no_network: None):
    provenance = _study(tmp_path, {"WP-001": b"one"})
    cache = tmp_path / "cache"
    (cache / "renamed").mkdir(parents=True)
    (cache / "renamed" / "download.html").write_bytes(b"one")

    report = verify_study_cache(provenance, cache)

    assert report["documents"][0]["status"] == "missing"
    assert report["documents"][0]["expected_bytes_found_at"] == ["renamed/download.html"]


def test_lists_candidates_without_a_recorded_hash(tmp_path: Path, no_network: None):
    provenance = _study(tmp_path, {"WP-001": b"one"}, extra_entries=("WP-013", "WP-014"))
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "WP-001_synthetic.html").write_bytes(b"one")
    (cache / "WP-013_synthetic.html").write_bytes(b"calibration")

    report = verify_study_cache(provenance, cache, include_candidates=True)

    assert exit_status(report) == EXIT_OK
    assert report["candidates"] == [
        {
            "study_doc_id": "WP-013",
            "status": "cached_no_hash",
            "sha256": _sha(b"calibration"),
            "file": "WP-013_synthetic.html",
        },
        {"study_doc_id": "WP-014", "status": "not_cached", "sha256": "", "file": ""},
    ]


def test_committed_provenance_is_readable_without_a_cache(tmp_path: Path, no_network: None):
    report = verify_study_cache(STUDY / "document-provenance.json", tmp_path / "no-cache")

    assert len(report["documents"]) == 10
    assert report["counts"]["missing"] == 10
    assert exit_status(report) == EXIT_MISSING


def test_bad_provenance_is_a_usage_error(tmp_path: Path):
    path = tmp_path / "document-provenance.json"
    path.write_text(json.dumps({"documents": []}), encoding="utf-8")

    assert main(["--provenance", str(path)]) == 2
