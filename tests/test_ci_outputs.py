import json
import re
from pathlib import Path

from micar_linter.ci_outputs import (
    MAX_ANNOTATIONS,
    render_annotations,
    render_sarif,
    render_summary,
    rule_doc_url,
    sarif_category,
)
from micar_linter.cli import main
from micar_linter.linter import lint_whitepaper
from micar_linter.locations import _json_section_offsets, finding_lines
from micar_linter.whitepaper import WhitepaperType, load_whitepaper

ROOT = Path(__file__).resolve().parents[1]
MARKER = "ZZQ-SYNTHETIC-MARKER"


def _report(path: Path, whitepaper_type: WhitepaperType | None = None):
    return lint_whitepaper(load_whitepaper(path, whitepaper_type))


def _marked_art_draft(tmp_path: Path) -> Path:
    draft = {
        "title": f"{MARKER} title",
        "type": "art",
        "references_official_currency": True,
        "art_significant": False,
        "article_45_7b_required_by_authority": False,
        "sections": {
            "summary": f"{MARKER} summary",
            "issuer": f"{MARKER} issuer",
            "reserve_of_assets": f"{MARKER} keeps 37.5% of the reserve in deposits.",
            # A key no rule reads: the report warning quotes it.
            f"{MARKER} key": "Text under a key that no rule reads.",
        },
    }
    path = tmp_path / "marked.json"
    path.write_text(json.dumps(draft, indent=2), encoding="utf-8")
    return path


def test_sarif_lists_every_rule_and_one_result_per_open_finding():
    path = Path("examples/incomplete.json")
    report = _report(ROOT / path)
    sarif = json.loads(render_sarif(report, path))
    assert sarif["version"] == "2.1.0"
    run = sarif["runs"][0]
    rules = run["tool"]["driver"]["rules"]
    assert [rule["id"] for rule in rules] == [f.rule.rule_id for f in report.findings]
    assert all(rule["helpUri"] == rule_doc_url(rule["id"]) for rule in rules)
    assert len(run["results"]) == len([f for f in report.findings if not f.passed])
    levels = {result["ruleId"]: result["level"] for result in run["results"]}
    severities = {f.rule.rule_id: f.rule.severity.label for f in report.findings}
    for rule_id, level in levels.items():
        assert level == {"BLOCKER": "error", "MAJOR": "warning", "MINOR": "note"}[severities[rule_id]]
    for result in run["results"]:
        location = result["locations"][0]["physicalLocation"]
        assert location["artifactLocation"]["uri"] == "examples/incomplete.json"
        assert location["region"]["startLine"] >= 1
        assert rules[result["ruleIndex"]]["id"] == result["ruleId"]


def test_format_gate_is_tagged_and_kept_out_of_annotations():
    path = Path("examples/incomplete.json")
    report = _report(ROOT / path)
    sarif = json.loads(render_sarif(report, path))
    gate = next(r for r in sarif["runs"][0]["tool"]["driver"]["rules"] if r["id"] == "COMMON.IXBRL_TAGGING")
    assert "format-gate" in gate["properties"]["tags"]
    assert any(r["ruleId"] == "COMMON.IXBRL_TAGGING" for r in sarif["runs"][0]["results"])
    assert "COMMON.IXBRL_TAGGING" not in render_annotations(report, path)
    assert "### Format gate" in render_summary(report, path)


def test_ci_outputs_are_byte_reproducible(tmp_path: Path):
    source = ROOT / "examples" / "incomplete.json"
    first, second = tmp_path / "first", tmp_path / "second"
    for directory in (first, second):
        assert (
            main(
                [
                    str(source),
                    "--sarif-output",
                    str(directory / "out.sarif"),
                    "--summary-output",
                    str(directory / "summary.md"),
                    "--annotations-output",
                    str(directory / "annotations.txt"),
                ]
            )
            == 0
        )
    for name in ("out.sarif", "summary.md", "annotations.txt"):
        assert (first / name).read_bytes() == (second / name).read_bytes()


def test_ci_outputs_never_echo_draft_text(tmp_path: Path):
    path = _marked_art_draft(tmp_path)
    report = _report(path)
    deposit = next(f for f in report.findings if f.rule.rule_id == "ANNEX_II.G.DEPOSIT_FLOOR_REVIEW")
    assert any("37.5%" in issue for issue in deposit.issues)
    assert any(MARKER in warning for warning in report.warnings)
    for output in (
        render_sarif(report, path),
        render_summary(report, path),
        render_annotations(report, path),
    ):
        assert MARKER not in output
        assert "37.5" not in output


def test_strict_exit_code_is_unchanged_by_ci_outputs(tmp_path: Path):
    source = str(ROOT / "examples" / "art-stablecoin.json")
    assert main([source, "--strict"]) == 1
    assert main([source, "--strict", "--sarif-output", str(tmp_path / "out.sarif")]) == 1
    assert main([source, "--sarif-output", str(tmp_path / "out.sarif")]) == 0


def test_annotations_are_capped_and_escaped(tmp_path: Path):
    directory = tmp_path / "a,b:c"
    directory.mkdir()
    path = directory / "draft.json"
    path.write_text(json.dumps({"title": "t", "type": "art", "sections": {}}), encoding="utf-8")
    report = _report(path)
    lines = render_annotations(report, path).splitlines()
    commands = [line for line in lines if line.startswith("::")]
    assert len(commands) == MAX_ANNOTATIONS
    assert lines[-1].endswith("more open findings are listed in the job summary and the report.")
    assert all("a%2Cb%3Ac" in line for line in commands)
    assert all(re.match(r"::(error|warning|notice) file=", line) for line in commands)


def test_json_section_lines_follow_the_last_duplicate_key():
    text = '{\n "sections": {\n  "summary": "a",\n  "risks": "b",\n  "summary": "c"\n },\n "title": "x"\n}'
    offsets = _json_section_offsets(text)
    assert text.count("\n", 0, offsets["summary"]) + 1 == 5
    assert text.count("\n", 0, offsets["risks"]) + 1 == 4
    assert _json_section_offsets("{ not json") == {}
    assert _json_section_offsets('{"sections": "text"}') == {}


def test_absent_sections_fall_back_to_line_one(tmp_path: Path):
    path = tmp_path / "empty.json"
    path.write_text('{\n"title": "t",\n"type": "other",\n"sections": {}\n}', encoding="utf-8")
    sarif = json.loads(render_sarif(_report(path), path))
    assert {
        r["locations"][0]["physicalLocation"]["region"]["startLine"] for r in sarif["runs"][0]["results"]
    } == {1}


def test_xhtml_findings_point_at_their_heading_lines():
    path = Path("examples/sample-draft.xhtml")
    report = _report(ROOT / path, WhitepaperType.OTHER)
    sarif = json.loads(render_sarif(report, ROOT / path))
    lines = {
        r["ruleId"]: r["locations"][0]["physicalLocation"]["region"]["startLine"]
        for r in sarif["runs"][0]["results"]
    }
    source = (ROOT / path).read_text(encoding="utf-8").splitlines()
    assert lines["COMMON.SUMMARY"] > 1
    assert "Summary" in source[lines["COMMON.SUMMARY"] - 1]


def test_action_pins_every_dependency_by_sha():
    action = (ROOT / "action.yml").read_text(encoding="utf-8")
    uses = re.findall(r"uses:\s*(\S+)", action)
    assert uses
    assert all(re.search(r"@[0-9a-f]{40}$", ref) for ref in uses), uses
    assert "--sarif-output" in action and "GITHUB_STEP_SUMMARY" in action


def test_sarif_category_differs_per_draft_path(tmp_path: Path):
    first, second = tmp_path / "a" / "draft.json", tmp_path / "b" / "draft.json"
    for path in (first, second):
        path.parent.mkdir()
        path.write_text(json.dumps({"title": "t", "type": "other", "sections": {}}), encoding="utf-8")
    ids = {
        json.loads(render_sarif(_report(p), p))["runs"][0]["automationDetails"]["id"] for p in (first, second)
    }
    assert len(ids) == 2
    assert all(i.startswith("micar-lint/") for i in ids)


def test_numbered_field_xhtml_findings_stay_on_line_one():
    path = ROOT / "examples" / "numbered-other-draft.xhtml"
    report = _report(path, WhitepaperType.OTHER)
    assert set(finding_lines(report, path).values()) == {1}


def test_format_gate_help_names_no_section():
    path = Path("examples/incomplete.json")
    rules = json.loads(render_sarif(_report(ROOT / path), path))["runs"][0]["tool"]["driver"]["rules"]
    gate = next(r for r in rules if r["id"] == "COMMON.IXBRL_TAGGING")
    assert "ixbrl_tagging" not in json.dumps(gate)
    assert "no section is read" in gate["help"]["text"]
    summary = next(r for r in rules if r["id"] == "COMMON.SUMMARY")
    assert "section 'summary'" in summary["help"]["text"]


def test_sarif_category_differs_per_regime_and_ignores_path_spelling():
    path = ROOT / "examples" / "numbered-other-draft.xhtml"
    ids = {
        json.loads(render_sarif(_report(path, regime), path))["runs"][0]["automationDetails"]["id"]
        for regime in (WhitepaperType.OTHER, WhitepaperType.ART)
    }
    assert len(ids) == 2
    assert sarif_category(Path("drafts/../draft.json"), "other") == sarif_category(
        Path("draft.json"), "other"
    )
