import json
from pathlib import Path

import pytest

from micar_linter.cli import build_parser, main


def test_cli_parser_help():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--help"])


def test_cli_main_success(tmp_path: Path):
    json_content = """{
        "title": "Clean Token",
        "type": "other",
        "sections": {
            "summary": "This summary provides key information about the token that has key information and is detailed enough.",
            "risk_warning": "This is a mandatory risk warning value loss warning details.",
            "management_statement": "The management body confirms this complies and is fair and clear and not misleading.",
            "notification_date": "Date is today.",
            "language": "Written in English language.",
            "offeror": "Offeror name is Test Ltd, legal form stock corp, registered office Berlin address.",
            "project": "This project purpose is business model and team detail is clear.",
            "offer_or_admission": "This public offer price and subscription target jurisdictions.",
            "crypto_asset": "The crypto-asset supply and transfer details and functionality description.",
            "rights_and_obligations": "The rights and obligations of holder to enforce claims.",
            "technology": "This protocol consensus smart contract security audit.",
            "risks": "The market risk and technology risk and regulatory risk and liquidity risk and operational risk factor.",
            "environmental_impact": "This consensus energy climate environmental impact statement."
        }
    }"""
    file_path = tmp_path / "other.json"
    file_path.write_text(json_content, encoding="utf-8")

    # Run in normal mode
    status = main([str(file_path)])
    assert status == 0

    # Run in strict mode
    status_strict = main([str(file_path), "--strict"])
    assert status_strict == 1


def test_cli_main_strict_blocker(tmp_path: Path):
    # Missing offeror which is a blocker
    json_content = """{
        "title": "Bad Token",
        "type": "other",
        "sections": {
            "summary": "Short",
            "risk_warning": "Short",
            "management_statement": "Short",
            "notification_date": "Short",
            "language": "Short"
        }
    }"""
    file_path = tmp_path / "bad.json"
    file_path.write_text(json_content, encoding="utf-8")

    # Strict mode should exit with status 1 due to blockers
    status = main([str(file_path), "--strict"])
    assert status == 1


def test_cli_main_json_format(tmp_path: Path, capsys):
    json_content = """{
        "title": "Clean Token",
        "type": "other",
        "sections": {
            "summary": "This summary provides key information about the token that has key information and is detailed enough."
        }
    }"""
    file_path = tmp_path / "json_test.json"
    file_path.write_text(json_content, encoding="utf-8")

    status = main([str(file_path), "--json"])
    assert status == 0

    captured = capsys.readouterr()
    report_data = json.loads(captured.out)
    assert report_data["title"] == "Clean Token"
    assert "findings" in report_data


def test_cli_audit_log_and_lang(tmp_path: Path):
    json_content = """{
        "title": "German Token",
        "type": "other",
        "sections": {
            "summary": "Dies ist die Zusammenfassung des Projekts. Sie enthält wesentliche Informationen.",
            "risk_warning": "Das ist ein Warnhinweis bezüglich des Risikos eines Wertverlusts."
        }
    }"""
    file_path = tmp_path / "german.json"
    file_path.write_text(json_content, encoding="utf-8")

    audit_log_path = tmp_path / "audit_log.md"

    status = main([str(file_path), "--lang", "de", "--audit-log", str(audit_log_path)])
    assert status == 0

    assert audit_log_path.exists()
    log_text = audit_log_path.read_text(encoding="utf-8")
    assert "# MiCAR Whitepaper Compliance Review Log" in log_text
    assert "German Token" in log_text
    assert "SHA-256 Checksum" in log_text
    assert "COMMON.SUMMARY" in log_text


def test_cli_manifest_output_tracks_source_and_audit_log(tmp_path: Path):
    json_content = """{
        "title": "Manifest Token",
        "type": "other",
        "sections": {
            "summary": "This summary provides key information about the token and its offer."
        }
    }"""
    file_path = tmp_path / "manifest.json"
    file_path.write_text(json_content, encoding="utf-8")
    audit_log_path = tmp_path / "audit_log.md"
    manifest_path = tmp_path / "manifest-output.json"

    status = main(
        [
            str(file_path),
            "--audit-log",
            str(audit_log_path),
            "--manifest-output",
            str(manifest_path),
        ]
    )

    assert status == 0
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema"] == "micar-whitepaper-linter.artifact-manifest.v1"
    assert manifest["source"]["sha256"]
    assert manifest["outputs"][0]["path"] == str(audit_log_path)
    assert manifest["export_eligibility"]["review_required"] is True
    assert len(manifest["overall_digest"]) == 64


def test_cli_remediation_output_is_manifest_tracked(tmp_path: Path):
    json_content = """{
        "title": "Remediation Token",
        "type": "other",
        "sections": {
            "summary": "Short"
        }
    }"""
    file_path = tmp_path / "remediation.json"
    file_path.write_text(json_content, encoding="utf-8")
    remediation_path = tmp_path / "remediation-output.json"
    manifest_path = tmp_path / "manifest-output.json"

    status = main(
        [
            str(file_path),
            "--remediation-output",
            str(remediation_path),
            "--manifest-output",
            str(manifest_path),
        ]
    )

    assert status == 0
    remediation = json.loads(remediation_path.read_text(encoding="utf-8"))
    assert remediation["schema"] == "micar-whitepaper-linter.remediation-report.v1"
    assert remediation["status"] == "BLOCKED"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["outputs"][0]["path"] == str(remediation_path)
    assert manifest["export_eligibility"]["machine_export_ready"] is False


def test_cli_review_table_output_is_manifest_tracked(tmp_path: Path):
    json_content = """{
        "title": "Review Table Token",
        "type": "other",
        "sections": {
            "summary": "Short"
        }
    }"""
    file_path = tmp_path / "review-table.json"
    file_path.write_text(json_content, encoding="utf-8")
    review_table_path = tmp_path / "review-table-output.json"
    manifest_path = tmp_path / "manifest-output.json"

    status = main(
        [
            str(file_path),
            "--review-table-output",
            str(review_table_path),
            "--manifest-output",
            str(manifest_path),
        ]
    )

    assert status == 0
    review_table = json.loads(review_table_path.read_text(encoding="utf-8"))
    assert review_table["schema"] == "micar-whitepaper-linter.review-table"
    assert review_table["summary"]["export_gate"] == "blocked"
    assert review_table["review_table_economics"]["llm_route"] == "none"
    assert review_table["rows"][0]["source_anchor"]

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["outputs"][0]["path"] == str(review_table_path)
    assert manifest["export_eligibility"]["machine_export_ready"] is False


def test_cli_review_table_comparison_output(tmp_path: Path, capsys):
    first = tmp_path / "draft-a.json"
    second = tmp_path / "draft-b.json"
    comparison_path = tmp_path / "review-table-comparison.json"
    first.write_text(
        """{
            "title": "Comparison Token",
            "type": "other",
            "sections": {
                "summary": "Short"
            }
        }""",
        encoding="utf-8",
    )
    second.write_text(
        """{
            "title": "Comparison Token",
            "type": "other",
            "sections": {
                "summary": "This summary provides key information about the token and its offer."
            }
        }""",
        encoding="utf-8",
    )

    status = main(
        [
            str(first),
            str(second),
            "--compare-review-table-output",
            str(comparison_path),
        ]
    )

    assert status == 0
    captured = capsys.readouterr()
    assert "Review table comparison written" in captured.out
    comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    assert comparison["schema"] == "micar-whitepaper-linter.review-table-comparison"
    assert comparison["source_count"] == 2
    assert comparison["external_action_allowed"] is False
    assert comparison["groups"][0]["drafts"][0]["source_anchor"]


def test_cli_multiple_paths_require_comparison_output(tmp_path: Path, capsys):
    first = tmp_path / "draft-a.json"
    second = tmp_path / "draft-b.json"
    first.write_text('{"title":"A","type":"other","sections":{"summary":"Short"}}', encoding="utf-8")
    second.write_text('{"title":"B","type":"other","sections":{"summary":"Short"}}', encoding="utf-8")

    status = main([str(first), str(second)])

    assert status == 2
    captured = capsys.readouterr()
    assert "multiple draft paths require --compare-review-table-output" in captured.err


def test_cli_review_bundle_writes_one_command_review_pack(tmp_path: Path):
    json_content = """{
        "title": "Bundle Token",
        "type": "other",
        "sections": {
            "summary": "Short"
        }
    }"""
    file_path = tmp_path / "bundle.json"
    bundle_dir = tmp_path / "review-bundle"
    file_path.write_text(json_content, encoding="utf-8")

    status = main([str(file_path), "--review-bundle-dir", str(bundle_dir)])

    assert status == 0
    assert (bundle_dir / "compliance-checklist.md").exists()
    assert (bundle_dir / "remediation-checklist.json").exists()
    assert (bundle_dir / "coverage-matrix.json").exists()
    assert (bundle_dir / "review-table.json").exists()
    assert (bundle_dir / "review-table.md").exists()
    assert (bundle_dir / "reviewer-signoff.md").exists()
    manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    coverage = json.loads((bundle_dir / "coverage-matrix.json").read_text(encoding="utf-8"))
    review_table = json.loads((bundle_dir / "review-table.json").read_text(encoding="utf-8"))

    assert manifest["bundle_schema"] == "micar-whitepaper-linter.review-bundle.v1"
    assert manifest["export_eligibility"]["review_required"] is True
    assert len(manifest["outputs"]) == 6
    assert "review_table_markdown" in {output["role"] for output in manifest["outputs"]}
    assert coverage["coverage"][0]["source_anchor"]
    assert review_table["review_table_economics"]["estimated_cell_tasks"] > 0
    assert review_table["rows"][0]["source_anchor"]
    assert "MiCAR White Paper Review Table" in (bundle_dir / "review-table.md").read_text(encoding="utf-8")
    assert "Lawyer Sign-off" in (bundle_dir / "reviewer-signoff.md").read_text(encoding="utf-8")


def test_cli_audit_log_write_failure_is_visible(tmp_path: Path, capsys):
    json_content = """{
        "title": "Audit Failure Token",
        "type": "other",
        "sections": {
            "summary": "This summary provides key information about the token."
        }
    }"""
    file_path = tmp_path / "draft.json"
    file_path.write_text(json_content, encoding="utf-8")

    status = main([str(file_path), "--audit-log", str(tmp_path)])

    assert status == 2
    captured = capsys.readouterr()
    assert "error: cannot write audit log" in captured.err


def test_cli_report_language_keeps_blockers_review_gated(tmp_path: Path, capsys):
    json_content = """{
        "title": "Review Gate Token",
        "type": "other",
        "sections": {
            "summary": "Short"
        }
    }"""
    file_path = tmp_path / "review-gate.json"
    file_path.write_text(json_content, encoding="utf-8")

    status = main([str(file_path)])

    assert status == 0
    captured = capsys.readouterr()
    assert "not package-ready" in captured.out
    assert "external review or filing workflow" in captured.out
    assert "lawyer has signed off" in captured.out
    assert "client-ready" not in captured.out
    assert "cannot proceed" not in captured.out


def test_cli_coverage(tmp_path: Path, capsys):
    json_content = """{
        "title": "Coverage Test Token",
        "type": "other",
        "sections": {
            "summary": "This summary provides key information about the token."
        }
    }"""
    file_path = tmp_path / "coverage_test.json"
    file_path.write_text(json_content, encoding="utf-8")

    status = main([str(file_path), "--coverage"])
    assert status == 0

    captured = capsys.readouterr()
    assert "MiCAR Whitepaper Coverage Matrix - Coverage Test Token" in captured.out
    assert "Whitepaper type: OTHER" in captured.out
    assert "COMMON.SUMMARY" in captured.out


# The workspace, collaboration-bundle and workflow modes, and the output-file error paths.

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
INCOMPLETE = EXAMPLES / "incomplete.json"


def test_cli_workspace_output_writes_the_workspace(tmp_path: Path, capsys):
    out = tmp_path / "review" / "workspace.json"
    assert main([str(INCOMPLETE), "--workspace-output", str(out)]) == 0
    captured = capsys.readouterr()
    assert captured.out.startswith(f"White paper workspace written to {out}. Documents: 1.")
    workspace = json.loads(out.read_text(encoding="utf-8"))
    assert workspace["schema"] == "micar-whitepaper-linter.workspace.v1"
    assert workspace["vault"]["document_count"] == 1
    assert workspace["external_action_allowed"] is False


def test_cli_workspace_output_json_prints_the_workspace(tmp_path: Path, capsys):
    out = tmp_path / "workspace.json"
    assert main([str(INCOMPLETE), "--workspace-output", str(out), "--json"]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed == json.loads(out.read_text(encoding="utf-8"))


def test_cli_workspace_strict_exits_one_on_open_blockers(tmp_path: Path):
    out = tmp_path / "workspace.json"
    assert main([str(INCOMPLETE), "--workspace-output", str(out), "--strict"]) == 1
    assert json.loads(out.read_text(encoding="utf-8"))["review_table"]["summary"]["blockers"] > 0


def test_cli_workspace_write_failure_is_visible(tmp_path: Path, capsys):
    assert main([str(INCOMPLETE), "--workspace-output", str(tmp_path)]) == 2
    assert "error: cannot write white paper workspace" in capsys.readouterr().err


def test_cli_workspace_mode_reports_a_draft_it_cannot_load(tmp_path: Path, capsys):
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    assert main([str(broken), "--workspace-output", str(tmp_path / "workspace.json")]) == 2
    assert "error: cannot write white paper workspace" in capsys.readouterr().err


def test_cli_collaboration_bundle_writes_the_three_files(tmp_path: Path, capsys):
    bundle = tmp_path / "review"
    assert main([str(INCOMPLETE), "--collaboration-bundle-dir", str(bundle)]) == 0
    assert sorted(path.name for path in bundle.iterdir()) == [
        "document-change-set.json",
        "review-sidecar.json",
        "workflow-pack.json",
    ]
    pack = json.loads((bundle / "workflow-pack.json").read_text(encoding="utf-8"))
    assert pack["run"]["schema"] == "workflow.run.v1"
    assert pack["run"]["external_action_allowed"] is False
    assert capsys.readouterr().out == ""


def test_cli_workflow_validate_checks_the_pack(capsys):
    assert main([str(INCOMPLETE), "--workflow-action", "validate"]) == 0
    out = capsys.readouterr().out
    assert out.startswith(
        "workflow.definition.v1 and workflow.run.v1 validated: 1 definition(s); run status blocked; export blocked ("
    )
    assert out.rstrip().endswith("pending review cells); external action disabled.")


def test_cli_workflow_validate_fails_on_an_invalid_pack(monkeypatch, capsys):
    from micar_linter import cli

    monkeypatch.setattr(cli, "build_workflow_pack", lambda *args: {"definitions": [], "run": {}})
    assert main([str(INCOMPLETE), "--workflow-action", "validate"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("error: workflow pack failed validation:\n  - definitions: expected a non-empty list\n")


def test_cli_workflow_inspect_prints_the_pack(capsys):
    from micar_linter.collaboration_workspace import validate_workflow_pack

    assert main([str(INCOMPLETE), "--workflow-action", "inspect"]) == 0
    pack = json.loads(capsys.readouterr().out)
    assert pack["definitions"][0]["schema"] == "workflow.definition.v1"
    assert validate_workflow_pack(pack) == []


def test_cli_workflow_run_requires_a_bundle_dir(capsys):
    assert main([str(INCOMPLETE), "--workflow-action", "run"]) == 2
    assert "error: --workflow-action run requires --collaboration-bundle-dir" in capsys.readouterr().err


def test_cli_workflow_run_with_a_bundle_dir(tmp_path: Path, capsys):
    bundle = tmp_path / "review"
    assert main([str(INCOMPLETE), "--workflow-action", "run", "--collaboration-bundle-dir", str(bundle)]) == 0
    assert capsys.readouterr().out == (
        "Supervised workflow run status: blocked. External action remains disabled.\n"
    )
    assert (bundle / "workflow-pack.json").is_file()


@pytest.mark.parametrize(
    ("flag", "name"),
    [
        ("--remediation-output", "remediation report"),
        ("--coverage-output", "coverage matrix"),
        ("--review-table-output", "review table"),
        ("--sarif-output", "SARIF log"),
        ("--summary-output", "summary"),
        ("--annotations-output", "annotations"),
        ("--manifest-output", "artifact manifest"),
    ],
)
def test_cli_output_file_write_failures_are_visible(flag: str, name: str, tmp_path: Path, capsys):
    # A directory in place of the output file cannot be written.
    assert main([str(INCOMPLETE), flag, str(tmp_path)]) == 2
    captured = capsys.readouterr()
    assert f"error: cannot write {name} to {tmp_path}:" in captured.err
    assert captured.out.startswith("MiCAR Whitepaper Linter - ")


def test_cli_review_bundle_write_failure_is_visible(tmp_path: Path, capsys):
    occupied = tmp_path / "bundle"
    occupied.write_text("not a directory", encoding="utf-8")
    assert main([str(INCOMPLETE), "--review-bundle-dir", str(occupied)]) == 2
    assert f"error: cannot write review bundle to {occupied}:" in capsys.readouterr().err


def _draft_directory(tmp_path: Path) -> Path:
    directory = tmp_path / "drafts"
    directory.mkdir()
    for name in ("incomplete.json", "art-stablecoin.json"):
        (directory / name).write_text((EXAMPLES / name).read_text(encoding="utf-8"), encoding="utf-8")
    return directory


def test_cli_batch_requires_an_output_path(tmp_path: Path, capsys):
    assert main([str(_draft_directory(tmp_path))]) == 2
    assert "error: directory input requires --batch-output <path>" in capsys.readouterr().err


def test_cli_batch_writes_the_pack_and_strict_fails_closed(tmp_path: Path, capsys):
    directory = _draft_directory(tmp_path)
    out = tmp_path / "packs" / "batch.json"
    assert main([str(directory), "--batch-output", str(out)]) == 0
    assert capsys.readouterr().out.startswith(
        f"Batch review pack written to {out}. Supported files: 2. Blocked files: 2. Failed files: 0."
    )
    pack = json.loads(out.read_text(encoding="utf-8"))
    assert pack["summary"]["supported_files"] == 2
    assert main([str(directory), "--batch-output", str(out), "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == json.loads(out.read_text(encoding="utf-8"))
    assert main([str(directory), "--batch-output", str(out), "--strict"]) == 1


def test_cli_batch_write_failure_is_visible(tmp_path: Path, capsys):
    assert main([str(_draft_directory(tmp_path)), "--batch-output", str(tmp_path)]) == 2
    assert f"error: cannot write batch review pack to {tmp_path}:" in capsys.readouterr().err


def test_cli_comparison_rejects_directories_and_reports_write_failures(tmp_path: Path, capsys):
    directory = _draft_directory(tmp_path)
    drafts = [str(directory / "incomplete.json"), str(directory / "art-stablecoin.json")]
    out = tmp_path / "comparison.json"
    assert main([str(directory), drafts[0], "--compare-review-table-output", str(out)]) == 2
    assert "error: comparison input must be local draft files, not directories" in capsys.readouterr().err
    assert main([*drafts, "--compare-review-table-output", str(tmp_path)]) == 2
    assert f"error: cannot write review table comparison to {tmp_path}:" in capsys.readouterr().err
    assert main([*drafts, "--compare-review-table-output", str(out), "--json"]) == 0
    comparison = json.loads(capsys.readouterr().out)
    assert comparison == json.loads(out.read_text(encoding="utf-8"))
    assert comparison["summary"]["blocker_groups"] > 0
    assert main([*drafts, "--compare-review-table-output", str(out), "--strict"]) == 1
