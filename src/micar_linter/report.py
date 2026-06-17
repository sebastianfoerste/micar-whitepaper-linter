"""Report rendering - plain text and JSON."""

from __future__ import annotations

import json

from micar_linter.linter import Report

_STATUS_ICON = {"pass": "PASS  ", "review": "REVIEW", "missing": "MISS  "}
_TITLE_BAR = "=" * 78


def render_text(report: Report) -> str:
    lines: list[str] = []
    lines.append(f"MiCAR Whitepaper Linter - {report.title}")
    lines.append(f"Whitepaper type: {report.whitepaper_type.value.upper()}")
    lines.append(_TITLE_BAR)
    lines.append(
        "Pass: {p}  |  Review: {r}  |  Missing: {m}  |  Blockers: {b}".format(
            p=len(report.passed),
            r=len(report.needs_review),
            m=len(report.missing),
            b=len(report.blockers),
        )
    )
    lines.append("")

    for finding in report.findings:
        rule = finding.rule
        icon = _STATUS_ICON[finding.status]
        sev = rule.severity.label
        lines.append(f"[{icon}] [{sev:7}] {rule.rule_id}  {rule.label}")
        lines.append(f"           Cite:  {rule.citation}")
        lines.append(f"           Section: '{rule.section}'  ({finding.word_count} words)")
        for issue in finding.issues:
            lines.append(f"           -  {issue}")
        lines.append("")

    if report.warnings:
        lines.append("Warnings:")
        for warning in report.warnings:
            lines.append(f"  -  {warning}")
        lines.append("")

    lines.append(_TITLE_BAR)
    if report.is_clean:
        lines.append("All required disclosures present. Lawyer review still required.")
    else:
        lines.append(
            "First-pass screening only. The draft is not package-ready. The "
            "MiCAR notification under Art. 8 / 17 / 49 MiCAR should not enter an external review "
            "or filing workflow until BLOCKER items are cured and a lawyer has signed off."
        )
    lines.append("This tool is not legal advice.")
    return "\n".join(lines)


def render_json(report: Report) -> str:
    payload = {
        "title": report.title,
        "whitepaper_type": report.whitepaper_type.value,
        "summary": {
            "pass": len(report.passed),
            "review": len(report.needs_review),
            "missing": len(report.missing),
            "blockers": len(report.blockers),
            "total": len(report.findings),
        },
        "warnings": list(report.warnings),
        "findings": [
            {
                "rule_id": f.rule.rule_id,
                "citation": f.rule.citation,
                "section": f.rule.section,
                "label": f.rule.label,
                "severity": f.rule.severity.label,
                "status": f.status,
                "word_count": f.word_count,
                "issues": list(f.issues),
                "source_anchor": (
                    report.source_anchors[f.rule.rule_id].to_json()
                    if f.rule.rule_id in report.source_anchors
                    else None
                ),
            }
            for f in report.findings
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def render_audit_log(report: Report, source_file: str, sha256: str) -> str:
    import datetime

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = []
    lines.append("# MiCAR Whitepaper Compliance Review Log")
    lines.append("")
    lines.append(f"- **Document Title**: {report.title}")
    lines.append(f"- **Regime/Type**: {report.whitepaper_type.value.upper()}")
    lines.append(f"- **Source File**: {source_file}")
    lines.append(f"- **SHA-256 Checksum**: `{sha256}`")
    lines.append(f"- **Review Timestamp**: {now_str}")
    lines.append("")
    lines.append("## Rule Compliance Checklist")
    lines.append("")
    lines.append("| Rule ID | Citation | Description | Severity | Status | Reviewer Checked |")
    lines.append("|---|---|---|---|---|---|")

    for f in report.findings:
        status_box = "[x]" if f.status == "pass" else "[ ]"
        lines.append(
            f"| `{f.rule.rule_id}` | {f.rule.citation} | {f.rule.label} | "
            f"{f.rule.severity.label} | **{f.status.upper()}** | {status_box} |"
        )
    lines.append("")
    lines.append("## Summary of Findings")
    lines.append("")
    lines.append(f"- **Passed Checks**: {len(report.passed)}")
    lines.append(f"- **Under Review**: {len(report.needs_review)}")
    lines.append(f"- **Missing Sections**: {len(report.missing)}")
    lines.append(f"- **BLOCKER Issues**: {len(report.blockers)}")
    lines.append("")

    if report.blockers:
        lines.append("> [!WARNING]")
        lines.append(
            "> **BLOCKER issues are currently open.** The draft is not package-ready "
            "for an external review or filing workflow until the gaps are cured "
            "and a lawyer has signed off."
        )
        lines.append("")
    else:
        lines.append("> [!NOTE]")
        lines.append("> All automated checks passed. Substantive lawyer review is still required.")
        lines.append("")

    lines.append("## Lawyer Sign-off")
    lines.append("")
    lines.append(
        "This document is an automated disclosure checklist. "
        "The reviewing lawyer must sign below only after reviewing the automated findings, "
        "the source draft and any filing decision independently."
    )
    lines.append("")
    lines.append("```")
    lines.append("Reviewer Name:  __________________________________")
    lines.append("Date of Review: __________________________________")
    lines.append("Signature:      __________________________________")
    lines.append("```")

    return "\n".join(lines)


def render_coverage_table(report: Report) -> str:
    lines = []
    lines.append(f"MiCAR Whitepaper Coverage Matrix - {report.title}")
    lines.append(f"Whitepaper type: {report.whitepaper_type.value.upper()}")
    lines.append("=" * 78)
    lines.append(f"| {'Rule ID':<20} | {'Citation':<15} | {'Severity':<8} | {'Status':<7} |")
    lines.append("|" + "-" * 22 + "|" + "-" * 17 + "|" + "-" * 10 + "|" + "-" * 9 + "|")
    for finding in report.findings:
        rule_id = finding.rule.rule_id
        citation = finding.rule.citation
        severity = finding.rule.severity.label
        status = finding.status.upper()
        lines.append(
            f"| {rule_id:<20} | {citation:<15} | {severity:<8} | {status:<7} |"
        )
    lines.append("=" * 78)
    lines.append(
        "Pass: {p}  |  Review: {r}  |  Missing: {m}  |  Blockers: {b}".format(
            p=len(report.passed),
            r=len(report.needs_review),
            m=len(report.missing),
            b=len(report.blockers),
        )
    )
    return "\n".join(lines)
