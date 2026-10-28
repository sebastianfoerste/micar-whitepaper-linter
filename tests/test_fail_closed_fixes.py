"""Fail-closed fixes: --coverage, draft-supplied source_file, batch lint failures and DOCX in the Action."""

import json
import re
import shutil
from pathlib import Path

from micar_linter.batch import build_batch_review_pack
from micar_linter.cli import main
from micar_linter.linter import lint_whitepaper
from micar_linter.whitepaper import load_whitepaper

ROOT = Path(__file__).resolve().parents[1]
INCOMPLETE = ROOT / "examples" / "incomplete.json"


def test_coverage_keeps_strict_and_output_files(tmp_path: Path, capsys):
    sarif = tmp_path / "out.sarif"
    audit = tmp_path / "audit.md"
    status = main(
        [str(INCOMPLETE), "--coverage", "--strict", "--sarif-output", str(sarif), "--audit-log", str(audit)]
    )
    assert status == 1
    assert "Coverage Matrix" in capsys.readouterr().out
    assert json.loads(sarif.read_text(encoding="utf-8"))["version"] == "2.1.0"
    assert audit.exists()


def test_coverage_without_strict_still_exits_zero(capsys):
    assert main([str(INCOMPLETE), "--coverage"]) == 0
    out = capsys.readouterr().out
    assert "Coverage Matrix" in out
    assert "First-pass screening" not in out


def test_draft_cannot_set_source_file(tmp_path: Path):
    xhtml = ROOT / "examples" / "sample-draft.xhtml"
    draft = {"title": "t", "type": "other", "source_file": str(xhtml), "sections": {}}
    path = tmp_path / "draft.json"
    path.write_text(json.dumps(draft), encoding="utf-8")
    whitepaper = load_whitepaper(path)
    assert "source_file" not in whitepaper.metadata
    report = lint_whitepaper(whitepaper)
    assert {anchor.parser_source_type for anchor in report.source_anchors.values()} == {"json"}
    ixbrl = next(f for f in report.findings if f.rule.rule_id == "COMMON.IXBRL_TAGGING")
    assert ixbrl.status == "missing"
    assert ixbrl.issues[0].startswith("Draft format:")


def test_batch_counts_files_it_could_not_lint_and_strict_fails_on_them(tmp_path: Path, capsys):
    source = tmp_path / "drafts"
    source.mkdir()
    shutil.copy(ROOT / "examples" / "numbered-other-draft.xhtml", source / "numbered.xhtml")
    pack = build_batch_review_pack(source)
    assert pack["summary"]["supported_files"] == 0
    assert pack["summary"]["failed_files"] == 1
    assert any(warning.startswith("lint-failed:") for warning in pack["warnings"])

    out = tmp_path / "pack.json"
    assert main([str(source), "--batch-output", str(out)]) == 0
    assert "Failed files: 1." in capsys.readouterr().out
    assert main([str(source), "--batch-output", str(out), "--strict"]) == 1


def test_strict_batch_fails_when_no_file_was_linted(tmp_path: Path, capsys):
    source = tmp_path / "drafts"
    source.mkdir()
    out = tmp_path / "pack.json"
    assert main([str(source), "--batch-output", str(out), "--strict"]) == 1
    (source / "notes.txt").write_text("not a draft", encoding="utf-8")
    assert main([str(source), "--batch-output", str(out), "--strict"]) == 1
    assert main([str(source), "--batch-output", str(out)]) == 0
    assert (
        capsys.readouterr()
        .out.splitlines()[-1]
        .endswith("Supported files: 0. Blocked files: 0. Failed files: 0.")
    )
    summary = json.loads(out.read_text(encoding="utf-8"))["summary"]
    assert (summary["supported_files"], summary["unsupported_files"]) == (0, 1)


def test_batch_without_failures_reports_zero_failed_files(tmp_path: Path):
    source = tmp_path / "drafts"
    source.mkdir()
    shutil.copy(INCOMPLETE, source / "draft.json")
    assert build_batch_review_pack(source)["summary"]["failed_files"] == 0


def test_action_installs_the_docx_extra():
    action = (ROOT / "action.yml").read_text(encoding="utf-8")
    assert re.search(r'uvx [^\n]*--from "\$\{GITHUB_ACTION_PATH\}\[docx\]" micar-lint', action)
