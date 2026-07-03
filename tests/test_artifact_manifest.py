from datetime import UTC, datetime
from pathlib import Path

from micar_linter.artifact_manifest import MANIFEST_SCHEMA, build_artifact_manifest
from micar_linter.linter import Report, lint_whitepaper
from micar_linter.whitepaper import Whitepaper, WhitepaperType


def test_artifact_manifest_reports_missing_outputs_and_export_blockers(tmp_path: Path):
    source_path = tmp_path / "incomplete.json"
    source_path.write_text('{"title":"Incomplete","type":"other","sections":{"summary":"Short"}}', encoding="utf-8")
    missing_output = tmp_path / "missing-report.md"
    report = lint_whitepaper(
        Whitepaper(
            title="Incomplete",
            type=WhitepaperType.OTHER,
            sections={"summary": "Short"},
            metadata={},
        )
    )

    manifest = build_artifact_manifest(
        report,
        source_path=source_path,
        output_paths=[missing_output],
        generated_at=datetime(2026, 6, 13, 9, 0, tzinfo=UTC),
    )

    assert manifest["schema"] == MANIFEST_SCHEMA
    assert manifest["outputs"] == []
    assert manifest["warnings"] == [f"output-missing:{missing_output}"]
    assert manifest["export_eligibility"]["machine_export_ready"] is False
    assert manifest["export_eligibility"]["blocked_by"]
    assert len(manifest["overall_digest"]) == 64


def test_artifact_manifest_marks_clean_report_review_required(tmp_path: Path):
    source_path = tmp_path / "clean.json"
    source_path.write_text('{"title":"Clean","type":"other","sections":{}}', encoding="utf-8")
    report = Report(
        title="Clean",
        whitepaper_type=WhitepaperType.OTHER,
        findings=(),
    )

    manifest = build_artifact_manifest(
        report,
        source_path=source_path,
        generated_at=datetime(2026, 6, 13, 9, 0, tzinfo=UTC),
    )

    assert manifest["export_eligibility"] == {
        "machine_export_ready": True,
        "blocked_by": [],
        "review_required": True,
        "notice": "Automated linter output requires substantive lawyer review before external use.",
    }
