import json

from micar_linter.linter import Report, lint_whitepaper
from micar_linter.remediation import REMEDIATION_SCHEMA, build_remediation_report
from micar_linter.whitepaper import Whitepaper, WhitepaperType


def test_remediation_report_groups_open_findings_by_action():
    whitepaper = Whitepaper(
        title="Incomplete Token",
        type=WhitepaperType.OTHER,
        sections={
            "summary": "Short summary.",
            "risk_warning": "",
        },
        metadata={},
    )
    report = lint_whitepaper(whitepaper)
    remediation = build_remediation_report(report)

    assert remediation["schema"] == REMEDIATION_SCHEMA
    assert remediation["status"] == "BLOCKED"
    assert remediation["summary"]["open_items"] > 0
    assert remediation["summary"]["blockers"] > 0
    assert any(item["missing_evidence"] for item in remediation["items"])
    assert all(item["next_action"] for item in remediation["items"])


def test_remediation_report_is_ready_for_clean_draft():
    report = Report(
        title="Clean Token",
        whitepaper_type=WhitepaperType.OTHER,
        findings=(),
    )
    remediation = build_remediation_report(report)

    assert remediation["status"] == "READY"
    assert remediation["items"] == []
    assert json.dumps(remediation)
