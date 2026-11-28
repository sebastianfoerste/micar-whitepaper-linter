"""The opt-in sign-off file for the never-pass gates of --strict (signoff.py, ADR 0010)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from micar_linter.cli import main
from micar_linter.linter import lint_whitepaper
from micar_linter.signoff import ACKNOWLEDGEABLE_RULES, SIGNOFF_SCHEMA
from micar_linter.whitepaper import load_whitepaper

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
FILLER = " This synthetic sentence only adds length and states no fact about any issuer or token."


def gate_only_draft(tmp_path: Path) -> Path:
    """The synthetic Title II example, lengthened where it is thin, so the iXBRL gate is its only open blocker."""
    draft = json.loads((EXAMPLES / "other-crypto-asset.json").read_text(encoding="utf-8"))
    sections = draft["sections"]
    sections["summary"] += FILLER * 2
    sections["risks"] += FILLER * 4
    sections["offeror"] += " The name of the offeror is MeshCompute Labs UG (haftungsbeschränkt)."
    path = tmp_path / "draft.json"
    path.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")
    blockers = {f.rule.rule_id for f in lint_whitepaper(load_whitepaper(path)).blockers}
    assert blockers == {"COMMON.IXBRL_TAGGING"}
    return path


def signoff(tmp_path: Path, draft: Path, *rule_ids: str, sha256: str | None = None, **overrides) -> Path:
    digest = sha256 or hashlib.sha256(draft.read_bytes()).hexdigest()
    entries = [
        {
            "rule_id": rule_id,
            "sha256": digest,
            "reviewer": "Synthetic Reviewer",
            "date": "2026-11-25",
            "note": "Synthetic note: validated with a taxonomy validator outside the linter.",
            **overrides,
        }
        for rule_id in rule_ids
    ]
    path = tmp_path / "signoff.json"
    path.write_text(json.dumps({"schema": SIGNOFF_SCHEMA, "acknowledgements": entries}), encoding="utf-8")
    return path


def test_only_the_never_pass_gates_can_be_acknowledged():
    assert {"COMMON.IXBRL_TAGGING", "ANNEX_II.G.DEPOSIT_FLOOR_REVIEW"} == ACKNOWLEDGEABLE_RULES


def test_acknowledged_gate_lets_strict_pass_and_keeps_the_finding_open(tmp_path: Path, capsys):
    draft = gate_only_draft(tmp_path)
    assert main([str(draft), "--strict"]) == 1
    capsys.readouterr()
    sign = signoff(tmp_path, draft, "COMMON.IXBRL_TAGGING")
    assert main([str(draft), "--strict", "--signoff", str(sign)]) == 0
    out = capsys.readouterr().out
    assert "Blockers: 1 (1 acknowledged)" in out
    assert "[MISS  ] [BLOCKER] COMMON.IXBRL_TAGGING" in out
    assert "Acknowledged for this file version by Synthetic Reviewer on 2026-11-25 (sign-off file)" in out
    assert "never-pass gates that the sign-off file acknowledges for this file version" in out
    assert out.rstrip().endswith("This tool is not legal advice.")


def test_json_report_lists_acknowledgements_without_changing_statuses(tmp_path: Path, capsys):
    draft = gate_only_draft(tmp_path)
    sign = signoff(tmp_path, draft, "COMMON.IXBRL_TAGGING")
    assert main([str(draft), "--json", "--signoff", str(sign)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert [a["rule_id"] for a in report["acknowledged"]] == ["COMMON.IXBRL_TAGGING"]
    assert report["summary"]["blockers"] == 1
    assert report["summary"]["open_blockers"] == 0
    gate = next(f for f in report["findings"] if f["rule_id"] == "COMMON.IXBRL_TAGGING")
    assert gate["status"] == "missing"


def test_a_changed_file_voids_the_signoff(tmp_path: Path, capsys):
    draft = gate_only_draft(tmp_path)
    sign = signoff(tmp_path, draft, "COMMON.IXBRL_TAGGING")
    draft.write_text(draft.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    assert main([str(draft), "--strict", "--signoff", str(sign)]) == 1
    out = capsys.readouterr().out
    assert "names another version of the file" in out
    assert "acknowledged)" not in out


def test_signoff_for_a_gate_without_an_open_finding_does_not_apply(tmp_path: Path, capsys):
    draft = gate_only_draft(tmp_path)
    sign = signoff(tmp_path, draft, "ANNEX_II.G.DEPOSIT_FLOOR_REVIEW")
    assert main([str(draft), "--strict", "--signoff", str(sign)]) == 1
    assert "has no open finding in this report" in capsys.readouterr().out


def test_a_content_blocker_keeps_strict_failing(tmp_path: Path):
    draft = tmp_path / "art.json"
    draft.write_bytes((EXAMPLES / "art-stablecoin.json").read_bytes())
    sign = signoff(tmp_path, draft, "COMMON.IXBRL_TAGGING", "ANNEX_II.G.DEPOSIT_FLOOR_REVIEW")
    # ANNEX_II.G.CUSTODY stays open, and no sign-off can acknowledge it.
    assert main([str(draft), "--strict", "--signoff", str(sign)]) == 1


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ({"acknowledgements": []}, '"schema"'),
        ({"schema": SIGNOFF_SCHEMA, "acknowledgements": []}, "non-empty list"),
        ({"schema": SIGNOFF_SCHEMA, "acknowledgements": ["x"]}, "must be an object"),
    ],
)
def test_malformed_signoff_files_exit_2(tmp_path: Path, capsys, content, message):
    draft = gate_only_draft(tmp_path)
    sign = tmp_path / "bad.json"
    sign.write_text(json.dumps(content), encoding="utf-8")
    assert main([str(draft), "--strict", "--signoff", str(sign)]) == 2
    assert message in capsys.readouterr().err


@pytest.mark.parametrize(
    ("rule_ids", "overrides", "message"),
    [
        (("COMMON.SUMMARY",), {}, "other findings cannot be acknowledged"),
        (("COMMON.IXBRL_TAGGING",), {"reviewer": "TBD"}, "reviewer must be"),
        (("COMMON.IXBRL_TAGGING",), {"note": " "}, "note must be"),
        (("COMMON.IXBRL_TAGGING",), {"date": "25.11.2026"}, "YYYY-MM-DD"),
        (("COMMON.IXBRL_TAGGING",), {"date": "2026-02-30"}, "does not exist"),
    ],
)
def test_invalid_acknowledgements_exit_2(tmp_path: Path, capsys, rule_ids, overrides, message):
    draft = gate_only_draft(tmp_path)
    sign = signoff(tmp_path, draft, *rule_ids, **overrides)
    assert main([str(draft), "--strict", "--signoff", str(sign)]) == 2
    assert message in capsys.readouterr().err


def test_upper_case_digest_is_refused(tmp_path: Path, capsys):
    draft = gate_only_draft(tmp_path)
    digest = hashlib.sha256(draft.read_bytes()).hexdigest().upper()
    sign = signoff(tmp_path, draft, "COMMON.IXBRL_TAGGING", sha256=digest)
    assert main([str(draft), "--signoff", str(sign)]) == 2
    assert "64 lower-case hex digits" in capsys.readouterr().err


def test_signoff_needs_a_single_white_paper_file(tmp_path: Path, capsys):
    draft = gate_only_draft(tmp_path)
    sign = signoff(tmp_path, draft, "COMMON.IXBRL_TAGGING")
    assert main([str(tmp_path), "--batch-output", str(tmp_path / "b.json"), "--signoff", str(sign)]) == 2
    assert "single white paper file" in capsys.readouterr().err
    marketing = [str(EXAMPLES / "marketing-other.md"), "--marketing", "--signoff", str(sign)]
    assert main(marketing) == 2
    assert "single white paper file" in capsys.readouterr().err


def test_ci_outputs_mark_acknowledged_gates_without_reviewer_data(tmp_path: Path):
    draft = tmp_path / "art.json"
    draft.write_bytes((EXAMPLES / "art-stablecoin.json").read_bytes())
    sign = signoff(tmp_path, draft, "COMMON.IXBRL_TAGGING", "ANNEX_II.G.DEPOSIT_FLOOR_REVIEW")
    sarif, summary, notes = tmp_path / "r.sarif", tmp_path / "s.md", tmp_path / "a.txt"
    args = [str(draft), "--signoff", str(sign), "--sarif-output", str(sarif), "--summary-output", str(summary)]
    assert main([*args, "--annotations-output", str(notes)]) == 0
    log = json.loads(sarif.read_text(encoding="utf-8"))
    run = log["runs"][0]
    assert run["properties"]["acknowledged"] == ["ANNEX_II.G.DEPOSIT_FLOOR_REVIEW", "COMMON.IXBRL_TAGGING"]
    acknowledged = {r["ruleId"] for r in run["results"] if r["properties"].get("acknowledged")}
    assert acknowledged == {"ANNEX_II.G.DEPOSIT_FLOOR_REVIEW", "COMMON.IXBRL_TAGGING"}
    text = summary.read_text(encoding="utf-8")
    assert "(2 acknowledged by the sign-off file)" in text
    assert "review, acknowledged" in text
    assert "ANNEX_II.G.DEPOSIT_FLOOR_REVIEW" not in notes.read_text(encoding="utf-8")
    for path in (sarif, summary, notes):
        content = path.read_text(encoding="utf-8")
        assert "Synthetic Reviewer" not in content
        assert "Synthetic note" not in content


def test_reports_without_signoff_carry_no_acknowledgement_keys(tmp_path: Path, capsys):
    draft = gate_only_draft(tmp_path)
    assert main([str(draft), "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert "acknowledged" not in report
    assert "open_blockers" not in report["summary"]
