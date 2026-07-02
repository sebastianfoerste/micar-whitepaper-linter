import json
from pathlib import Path

from micar_linter.linter import lint_whitepaper
from micar_linter.review_table import (
    REVIEW_TABLE_COMPARISON_SCHEMA,
    REVIEW_TABLE_SCHEMA,
    build_review_table,
    build_review_table_comparison,
    render_review_table,
    render_review_table_comparison,
)
from micar_linter.whitepaper import load_whitepaper


def test_review_table_projects_rule_findings_into_review_rows(tmp_path: Path):
    draft_path = tmp_path / "draft.json"
    draft_path.write_text(
        """{
            "title": "Review Table Token",
            "type": "other",
            "sections": {
                "summary": "Short"
            }
        }""",
        encoding="utf-8",
    )
    report = lint_whitepaper(load_whitepaper(draft_path))

    table = build_review_table(report, source_path=draft_path)
    rendered = json.loads(render_review_table(table))
    blocker_rows = [row for row in rendered["rows"] if row["blocker"]]

    assert rendered["schema"] == REVIEW_TABLE_SCHEMA
    assert rendered["source"]["sha256"]
    assert rendered["summary"]["export_gate"] == "blocked"
    assert rendered["review_table_economics"]["schema"] == (
        "micar-whitepaper-linter.review-table-economics.v1"
    )
    assert rendered["review_table_economics"]["row_count"] == rendered["summary"]["total"]
    assert rendered["review_table_economics"]["estimated_cell_tasks"] == (
        rendered["summary"]["total"] * rendered["review_table_economics"]["column_count"]
    )
    assert rendered["review_table_economics"]["llm_route"] == "none"
    assert rendered["control_profile"]["schema"] == "micar-whitepaper-linter.review-control-profile.v1"
    assert rendered["control_profile"]["external_action_allowed"] is False
    assert rendered["control_profile"]["workflow_routes"][-1]["status"] == "blocked"
    assert rendered["prompt_improvement"]["schema"] == "micar-whitepaper-linter.remediation-prompt-pack.v1"
    assert "Review gate: draft only" in rendered["prompt_improvement"]["suggested_prompt"]
    assert rendered["playbook_profile"]["schema"] == "micar-linter.playbook-review.v1"
    assert rendered["playbook_profile"]["legoraIntegration"] == "none"
    assert rendered["playbook_profile"]["externalActionAllowed"] is False
    assert rendered["playbook_profile"]["tabularReview"]["externalActionAllowed"] is False
    assert rendered["playbook_profile"]["trustedSources"]["sourceMode"] == "local_draft_and_rule_catalog"
    assert rendered["playbook_profile"]["portalRoom"]["externalGuestAccessAllowed"] is False
    assert rendered["playbook_profile"]["securityGovernance"]["approvalGate"] == (
        "required_for_external_filing_or_publication"
    )
    assert "no Legora integration or dependency" in rendered["playbook_profile"]["reviewNotice"]
    assert blocker_rows
    assert blocker_rows[0]["source_anchor"]
    assert blocker_rows[0]["reviewer_decision"] == "remediation_required"
    assert blocker_rows[0]["citation_coverage"] == "anchor_and_citation"


def test_review_table_comparison_groups_multiple_local_drafts(tmp_path: Path):
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text(
        """{
            "title": "Review Table Token",
            "type": "other",
            "sections": {
                "summary": "Short"
            }
        }""",
        encoding="utf-8",
    )
    second.write_text(
        """{
            "title": "Review Table Token",
            "type": "other",
            "sections": {
                "summary": "This summary provides key information about the token and its offer."
            }
        }""",
        encoding="utf-8",
    )

    comparison = json.loads(render_review_table_comparison(build_review_table_comparison([first, second])))
    first_group = comparison["groups"][0]

    assert comparison["schema"] == REVIEW_TABLE_COMPARISON_SCHEMA
    assert comparison["source_count"] == 2
    assert comparison["external_action_allowed"] is False
    assert comparison["summary"]["rule_groups"] > 0
    assert comparison["summary"]["export_gate"] == "blocked"
    assert len(first_group["drafts"]) == 2
    assert {
        "status",
        "blocker",
        "word_count",
        "source_anchor",
        "remediation",
        "reviewer_decision",
    } <= set(first_group["drafts"][0])
    assert first_group["source_hashes"][0]
