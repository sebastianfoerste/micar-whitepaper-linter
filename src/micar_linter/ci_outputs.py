"""CI outputs: SARIF 2.1.0, a Markdown job summary and GitHub annotations.

These outputs carry rule metadata, statuses, citations and line numbers only.
They never echo draft text: CI logs, summaries and code-scanning alerts can be
more widely visible than the draft itself. Findings whose issue messages quote
the draft (extracted percentages, parser errors) get a fixed message instead.

Every output is byte-reproducible: no timestamps, a fixed order, and paths as
given on the command line. Statuses, severities and exit codes are unchanged;
the outputs only place the report's findings.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from micar_linter import __version__, citations
from micar_linter.linter import Report
from micar_linter.locations import finding_lines
from micar_linter.rules.base import Finding, Severity

RULE_DOCS_BASE = "https://sebastianfoerste.github.io/micar-whitepaper-linter/rules/"
INFORMATION_URI = "https://github.com/sebastianfoerste/micar-whitepaper-linter"
SARIF_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
MAX_ANNOTATIONS = 10

# This blocker stays open for every draft until an iXBRL validation runs, so it is
# reported in SARIF and the summary but does not take an annotation slot.
FORMAT_GATE_RULES = frozenset({"COMMON.IXBRL_TAGGING"})
# Issue messages of these rules can quote draft content.
DRAFT_ECHO_RULES = frozenset({"COMMON.IXBRL_TAGGING", "ANNEX_II.G.DEPOSIT_FLOOR_REVIEW"})
_FIXED_ISSUE = "Details are in the full lint report; this output does not repeat draft content."

_SARIF_LEVEL = {Severity.BLOCKER: "error", Severity.MAJOR: "warning", Severity.MINOR: "note"}
_ANNOTATION_LEVEL = {Severity.BLOCKER: "error", Severity.MAJOR: "warning", Severity.MINOR: "notice"}
_STATUS_ORDER = {"missing": 0, "review": 1, "pass": 2}


def rule_doc_url(rule_id: str) -> str:
    return f"{RULE_DOCS_BASE}{rule_id}.html"


def draft_free_issues(finding: Finding) -> tuple[str, ...]:
    if finding.rule.rule_id in DRAFT_ECHO_RULES:
        return (_FIXED_ISSUE,)
    return finding.issues


def open_findings(report: Report) -> list[Finding]:
    """Open findings, blockers first, then missing before review, in rule order."""
    indexed = [(index, f) for index, f in enumerate(report.findings) if not f.passed]
    indexed.sort(key=lambda item: (-item[1].rule.severity, _STATUS_ORDER[item[1].status], item[0]))
    return [finding for _, finding in indexed]


def build_sarif(report: Report, source_path: Path) -> dict:
    uri = source_path.as_posix()
    lines = finding_lines(report, source_path)
    rules = []
    for finding in report.findings:
        rule = finding.rule
        tags = ["micar", report.whitepaper_type.value, rule.severity.label.lower()]
        if rule.rule_id in FORMAT_GATE_RULES:
            tags.append("format-gate")
        rules.append(
            {
                "id": rule.rule_id,
                "name": rule.rule_id,
                "shortDescription": {"text": rule.label},
                "fullDescription": {"text": f"{rule.label}. {citations.to_english(rule.citation)}."},
                "helpUri": rule_doc_url(rule.rule_id),
                "help": {
                    "text": (
                        f"{citations.to_english(rule.citation)}. First-pass check on section "
                        f"'{rule.section}'. Not legal advice. Rule page: {rule_doc_url(rule.rule_id)}"
                    )
                },
                "defaultConfiguration": {"level": _SARIF_LEVEL[rule.severity]},
                "properties": {
                    "citation": rule.citation,
                    "citation_en": citations.to_english(rule.citation),
                    "severity": rule.severity.label,
                    "section": rule.section,
                    "tags": tags,
                },
            }
        )
    rule_index = {finding.rule.rule_id: index for index, finding in enumerate(report.findings)}

    results = []
    for finding in open_findings(report):
        rule = finding.rule
        message = f"{finding.status.upper()}: {rule.label}. " + " ".join(draft_free_issues(finding))
        results.append(
            {
                "ruleId": rule.rule_id,
                "ruleIndex": rule_index[rule.rule_id],
                "level": _SARIF_LEVEL[rule.severity],
                "message": {"text": message.strip()},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": uri},
                            "region": {"startLine": lines.get(rule.rule_id, 1)},
                        }
                    }
                ],
                "partialFingerprints": {
                    "micarRuleSection/v1": hashlib.sha256(
                        f"{uri}\n{rule.rule_id}\n{rule.section}".encode()
                    ).hexdigest()
                },
                "properties": {"status": finding.status, "severity": rule.severity.label},
            }
        )

    return {
        "$schema": SARIF_SCHEMA,
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "micar-whitepaper-linter",
                        "version": __version__,
                        "semanticVersion": __version__,
                        "informationUri": INFORMATION_URI,
                        "rules": rules,
                    }
                },
                "automationDetails": {"id": f"micar-lint/{report.whitepaper_type.value}/"},
                "results": results,
                "properties": {
                    "whitepaper_type": report.whitepaper_type.value,
                    "summary": _summary_counts(report),
                    "notice": "First-pass screening. Not legal advice. A pass means a check matched.",
                },
            }
        ],
    }


def render_sarif(report: Report, source_path: Path) -> str:
    return json.dumps(build_sarif(report, source_path), indent=2, ensure_ascii=False) + "\n"


def render_summary(report: Report, source_path: Path) -> str:
    """A Markdown job summary. The draft title is draft text, so the file path names it."""
    lines_by_rule = finding_lines(report, source_path)
    path = source_path.as_posix()
    counts = _summary_counts(report)
    out = [
        f"## MiCAR white paper lint: `{_cell(path)}`",
        "",
        (
            f"Regime: **{report.whitepaper_type.value.upper()}** · {counts['total']} checks · "
            f"open blockers: **{counts['blockers']}** · missing: {counts['missing']} · "
            f"review: {counts['review']} · pass: {counts['pass']}"
        ),
        "",
        "> First-pass screening, not legal advice. Counts are rule matches, not a compliance opinion. "
        "A pass means a check matched; substantive lawyer review is always required.",
        "",
    ]
    findings = [f for f in open_findings(report) if f.rule.rule_id not in FORMAT_GATE_RULES]
    if findings:
        out += [
            "| Rule | Status | Severity | Citation | Location | Rule page |",
            "|---|---|---|---|---|---|",
        ]
        for finding in findings:
            rule = finding.rule
            out.append(
                f"| `{rule.rule_id}` | {finding.status} | {rule.severity.label} | "
                f"{_cell(citations.to_english(rule.citation))} | "
                f"`{_cell(path)}:{lines_by_rule.get(rule.rule_id, 1)}` | "
                f"[{rule.rule_id}]({rule_doc_url(rule.rule_id)}) |"
            )
    else:
        out.append("No open content findings. The format gate below and lawyer review still apply.")
    gate = [f for f in report.findings if f.rule.rule_id in FORMAT_GATE_RULES and not f.passed]
    if gate:
        out += ["", "### Format gate", ""]
        for finding in gate:
            out.append(
                f"`{finding.rule.rule_id}` is {finding.status} ({finding.rule.severity.label}). "
                "This tool checks the file format and taxonomy namespace only, "
                "so this blocker never passes here; "
                "tag completeness needs a taxonomy validator. "
                f"[Rule page]({rule_doc_url(finding.rule.rule_id)})"
            )
    passed = [f.rule.rule_id for f in report.findings if f.passed]
    if passed:
        out += [
            "",
            f"<details><summary>Checks that matched ({len(passed)})</summary>",
            "",
            ", ".join(f"`{rule_id}`" for rule_id in passed),
            "",
            "</details>",
        ]
    return "\n".join(out) + "\n"


def render_annotations(report: Report, source_path: Path, limit: int = MAX_ANNOTATIONS) -> str:
    """GitHub workflow commands for the first ``limit`` open content findings."""
    lines_by_rule = finding_lines(report, source_path)
    path = source_path.as_posix()
    findings = [f for f in open_findings(report) if f.rule.rule_id not in FORMAT_GATE_RULES]
    out = []
    for finding in findings[:limit]:
        rule = finding.rule
        properties = ",".join(
            [
                f"file={_property(path)}",
                f"line={lines_by_rule.get(rule.rule_id, 1)}",
                f"title={_property(f'{rule.rule_id} ({finding.status})')}",
            ]
        )
        message = (
            f"{rule.label}. {citations.to_english(rule.citation)}. "
            f"First-pass check, not legal advice. {rule_doc_url(rule.rule_id)}"
        )
        out.append(f"::{_ANNOTATION_LEVEL[rule.severity]} {properties}::{_data(message)}")
    if len(findings) > limit:
        out.append(
            f"{len(findings) - limit} more open findings are listed in the job summary and the report."
        )
    return "\n".join(out) + ("\n" if out else "")


def _summary_counts(report: Report) -> dict[str, int]:
    return {
        "pass": len(report.passed),
        "review": len(report.needs_review),
        "missing": len(report.missing),
        "blockers": len(report.blockers),
        "total": len(report.findings),
    }


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("`", "'").replace("\n", " ")


def _data(text: str) -> str:
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _property(text: str) -> str:
    return _data(text).replace(":", "%3A").replace(",", "%2C")
