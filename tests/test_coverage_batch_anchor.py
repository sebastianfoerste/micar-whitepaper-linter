import json
from pathlib import Path

from micar_linter.cli import main
from micar_linter.linter import lint_whitepaper
from micar_linter.report import render_json
from micar_linter.whitepaper import load_whitepaper


def _draft_json(title: str = "Coverage Token") -> str:
    return json.dumps(
        {
            "title": title,
            "type": "other",
            "sections": {
                "summary": "CONFIDENTIAL DRAFT WORDING SHOULD NOT LEAK. This summary provides key information.",
                "risk_warning": "Risk warning text.",
            },
        }
    )


def test_cli_coverage_output_is_manifest_tracked_without_raw_snippets(tmp_path: Path):
    source = tmp_path / "coverage.json"
    source.write_text(_draft_json(), encoding="utf-8")
    coverage_path = tmp_path / "coverage-output.json"
    manifest_path = tmp_path / "manifest-output.json"

    status = main(
        [
            str(source),
            "--coverage-output",
            str(coverage_path),
            "--manifest-output",
            str(manifest_path),
        ]
    )

    assert status == 0
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    coverage_json = json.dumps(coverage)
    assert coverage["schema"] == "micar-whitepaper-linter.coverage-matrix.v1"
    assert coverage["coverage"][0]["source_anchor"]["parser_source_type"] == "json"
    assert len(coverage["digest"]) == 64
    assert "CONFIDENTIAL DRAFT WORDING SHOULD NOT LEAK" not in coverage_json

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert str(coverage_path) in [item["path"] for item in manifest["outputs"]]


def test_directory_batch_mode_writes_review_pack_and_unsupported_warnings(tmp_path: Path):
    source_dir = tmp_path / "batch"
    source_dir.mkdir()
    (source_dir / "a.json").write_text(_draft_json("Batch Token A"), encoding="utf-8")
    (source_dir / "notes.txt").write_text("unsupported confidential notes", encoding="utf-8")
    batch_path = tmp_path / "batch-output.json"

    status = main([str(source_dir), "--batch-output", str(batch_path)])

    assert status == 0
    pack = json.loads(batch_path.read_text(encoding="utf-8"))
    pack_json = json.dumps(pack)
    assert pack["schema"] == "micar-whitepaper-linter.batch-review-pack.v1"
    assert pack["summary"]["supported_files"] == 1
    assert pack["summary"]["unsupported_files"] == 1
    assert len(pack["files"][0]["source_hash"]) == 64
    assert len(pack["files"][0]["manifest_digest"]) == 64
    assert "unsupported-file:" in pack["warnings"][0]
    assert "CONFIDENTIAL DRAFT WORDING SHOULD NOT LEAK" not in pack_json
    assert "unsupported confidential notes" not in pack_json


def test_directory_input_requires_batch_output(tmp_path: Path, capsys):
    status = main([str(tmp_path)])

    assert status == 2
    captured = capsys.readouterr()
    assert "directory input requires --batch-output" in captured.err


def test_xhtml_source_anchor_prefers_section_identifier(tmp_path: Path):
    source = tmp_path / "sample.xhtml"
    source.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
  <body>
    <h1 id="plain-summary">Summary</h1>
    <p>CONFIDENTIAL XHTML WORDING SHOULD NOT LEAK. This summary provides key information about the token.</p>
  </body>
</html>
""",
        encoding="utf-8",
    )

    report = lint_whitepaper(load_whitepaper(source))
    payload = json.loads(render_json(report))
    summary = next(item for item in payload["findings"] if item["rule_id"] == "COMMON.SUMMARY")
    payload_json = json.dumps(payload)

    assert summary["source_anchor"]["parser_source_type"] == "xhtml"
    assert summary["source_anchor"]["stable_anchor_id"] == "xhtml:plain-summary"
    assert "CONFIDENTIAL XHTML WORDING SHOULD NOT LEAK" not in payload_json
