"""Field-level checks on a draft without field numbers (owner decision 1A of 2026-11-10, ADR 0005).

The point rules built from POINTS and the field-only template rules do not run on a JSON, PDF, DOCX, Markdown or
heading-based XHTML draft. The report carries one note instead, and no output shows those rules open or passed.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from micar_linter.ci_outputs import build_sarif, render_annotations, render_summary
from micar_linter.coverage import build_coverage_matrix
from micar_linter.linter import FIELD_ONLY_RULE_IDS, FIELD_TEMPLATE_RULE_IDS, lint_whitepaper, not_run_note
from micar_linter.remediation import build_remediation_report
from micar_linter.report import render_audit_log, render_json, render_text
from micar_linter.review_bundle import write_review_bundle
from micar_linter.review_table import build_review_table, render_review_table_markdown
from micar_linter.rules import RULESETS
from micar_linter.rules.points import POINT_RULE_IDS
from micar_linter.whitepaper import WhitepaperType, load_whitepaper

ROOT = Path(__file__).resolve().parents[1]
INCOMPLETE = ROOT / "examples/incomplete.json"
ART = ROOT / "examples/art-stablecoin.json"
NUMBERED = ROOT / "examples/numbered-other-draft.xhtml"
EN_START = (
    "Field-level checks of the templates of Implementing Regulation (EU) 2024/2984 and Delegated Regulations (EU) "
    "2025/421 and 2025/422 run only on drafts in the numbered-field layout (XHTML)."
)
DE_START = (
    "Die Prüfungen auf Feldebene nach den Vorlagen der Durchführungsverordnung (EU) 2024/2984 und der Delegierten "
    "Verordnungen (EU) 2025/421 und 2025/422 laufen nur bei Entwürfen im Layout mit nummerierten Feldern (XHTML)."
)


def _skipped(regime: WhitepaperType) -> set[str]:
    return {rule.rule_id for rule in RULESETS[regime] if rule.rule_id in FIELD_ONLY_RULE_IDS}


def test_the_field_only_rules_are_the_point_rules_and_five_template_rules():
    assert FIELD_ONLY_RULE_IDS == POINT_RULE_IDS | FIELD_TEMPLATE_RULE_IDS
    assert {"ANNEX_I.A.P6", "ANNEX_III.A.P6", "ITS.NOTIFICATION_DATE_FORMAT"}.isdisjoint(FIELD_ONLY_RULE_IDS)


def test_a_json_draft_gets_one_note_and_no_finding_of_those_rules():
    report = lint_whitepaper(load_whitepaper(INCOMPLETE))
    skipped = _skipped(WhitepaperType.ART)
    assert {rule.rule_id for rule in report.not_run} == skipped
    assert not skipped & {finding.rule.rule_id for finding in report.findings}
    notes = [warning for warning in report.warnings if warning.startswith(EN_START)]
    assert notes == [
        EN_START + " This draft has no field numbers, so 65 point checks and 5 template checks did not run. They are "
        "left out of this report and count neither as passed nor as open; check the white paper in the "
        "numbered-field layout to run them."
    ]
    # Every other rule of the regime still runs.
    assert len(report.findings) + len(report.not_run) == len(RULESETS[WhitepaperType.ART])
    assert len(report.blockers) == 16
    assert len(lint_whitepaper(load_whitepaper(ART)).blockers) == 3


def test_a_german_draft_gets_the_note_in_german(tmp_path):
    draft = json.loads(INCOMPLETE.read_text(encoding="utf-8"))
    draft["language"] = "de"
    path = tmp_path / "entwurf.json"
    path.write_text(json.dumps(draft), encoding="utf-8")
    report = lint_whitepaper(load_whitepaper(path))
    notes = [warning for warning in report.warnings if "Feldebene" in warning]
    assert notes == [
        DE_START + " Dieser Entwurf hat keine Feldnummern, daher liefen 65 Prüfungen von Anhangspunkten und 5 "
        "Vorlagenprüfungen nicht. Sie fehlen in diesem Bericht und zählen weder als bestanden noch als offen; prüfen "
        "Sie das Whitepaper im Layout mit nummerierten Feldern, um sie auszuführen."
    ]
    assert not any(warning.startswith(EN_START) for warning in report.warnings)


def test_the_note_counts_in_the_singular():
    rule = next(rule for rule in RULESETS[WhitepaperType.OTHER] if rule.rule_id == "ANNEX_I.A.P1")
    template = next(rule for rule in RULESETS[WhitepaperType.OTHER] if rule.rule_id == "ITS.CODE_LISTS")
    assert "so 1 point check and 1 template check did not run" in not_run_note((rule, template), False)
    assert "daher liefen 1 Prüfung von Anhangspunkten und 1 Vorlagenprüfung nicht" in not_run_note(
        (rule, template), True
    )


def test_a_numbered_field_draft_runs_every_rule_without_the_note():
    report = lint_whitepaper(load_whitepaper(NUMBERED, WhitepaperType.OTHER))
    assert report.not_run == ()
    assert _skipped(WhitepaperType.OTHER) <= {finding.rule.rule_id for finding in report.findings}
    assert len(report.findings) == len(RULESETS[WhitepaperType.OTHER])
    assert not any(warning.startswith(EN_START) for warning in report.warnings)
    assert json.loads(render_json(report))["not_run"] == []


def _ids_in(text: str, skipped: set[str]) -> set[str]:
    return {rule_id for rule_id in skipped if re.search(rf"(?<![\w.]){re.escape(rule_id)}(?![\w.])", text)}


def test_no_output_shows_a_rule_that_did_not_run(tmp_path):
    report = lint_whitepaper(load_whitepaper(INCOMPLETE))
    skipped = _skipped(WhitepaperType.ART)

    # Text report and audit log: no line for a skipped rule; the note is listed.
    text = render_text(report)
    assert not _ids_in(text, skipped)
    assert EN_START in text
    log = render_audit_log(report, str(INCOMPLETE), "0" * 64)
    assert not _ids_in(log, skipped)
    assert EN_START in log

    # JSON report: no finding, named under not_run, counted in no summary figure.
    payload = json.loads(render_json(report))
    assert not skipped & {finding["rule_id"] for finding in payload["findings"]}
    assert set(payload["not_run"]) == skipped
    assert payload["summary"]["total"] == len(report.findings)

    # SARIF: not among the rules or results; named in the run properties only.
    sarif = build_sarif(report, INCOMPLETE)
    run = sarif["runs"][0]
    assert not skipped & {rule["id"] for rule in run["tool"]["driver"]["rules"]}
    assert not skipped & {result["ruleId"] for result in run["results"]}
    assert set(run["properties"]["not_run"]) == skipped

    # Job summary and annotations: counted in one fixed sentence, never listed or passed.
    summary = render_summary(report, INCOMPLETE)
    assert not _ids_in(summary, skipped)
    assert "70 field-level checks did not run" in summary
    assert render_summary(report, INCOMPLETE) == summary
    assert not _ids_in(render_annotations(report, INCOMPLETE), skipped)

    # Coverage table, remediation and review table: no row; the note travels in their warnings.
    coverage = build_coverage_matrix(report)
    assert not skipped & {row["rule_id"] for row in coverage["coverage"]}
    assert set(coverage["not_run"]) == skipped
    remediation = build_remediation_report(report)
    assert not _ids_in(json.dumps(remediation), skipped)
    assert any(warning.startswith(EN_START) for warning in remediation["warnings"])
    table = build_review_table(report, source_path=INCOMPLETE)
    assert not skipped & {row["rule_id"] for row in table["rows"]}
    assert not _ids_in(render_review_table_markdown(table), skipped)

    # Review bundle: no file names a skipped rule except where it lists the rules that did not run.
    bundle = tmp_path / "bundle"
    write_review_bundle(report, source_path=INCOMPLETE, directory=bundle)
    for path in bundle.iterdir():
        content = path.read_text(encoding="utf-8")
        if path.name == "coverage-matrix.json":
            content = json.dumps({k: v for k, v in json.loads(content).items() if k != "not_run"})
        assert not _ids_in(content, skipped), path.name
