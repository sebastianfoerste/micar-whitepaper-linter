"""Markdown renderer for the MiCAR Title II Annex I study."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

TITLE = (
    "10 Notified MiCAR Title II White Papers Reviewed: Recurring Annex I Disclosure Gaps "
    "Flagged by Deterministic Rules"
)
STUDY_NAME = "MiCAR White Paper Study 2026: Annex I Disclosure Patterns in Notified Title II White Papers"
ESMA_MICA_PAGE = (
    "https://www.esma.europa.eu/esmas-activities/digital-finance-and-innovation/"
    "markets-crypto-assets-regulation-mica"
)
ESMA_ARTICLE_6 = "https://www.esma.europa.eu/publications-and-data/interactive-single-rulebook/mica/article-6-content-and-form-crypto-asset"
ESMA_ARTICLE_8 = "https://www.esma.europa.eu/publications-and-data/interactive-single-rulebook/mica/article-8-notification-crypto-asset-white"
ESMA_ARTICLE_109 = "https://www.esma.europa.eu/publications-and-data/interactive-single-rulebook/mica/article-109-register-crypto-asset-white"


def render_study_report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    reviewed = summary["documents_reviewed"]
    potential_gaps = summary["potential_gaps"]
    high_confidence = summary["high_confidence_gaps"]
    review_status = payload.get("human_review_status", "pending_review")
    example_heading = (
        "Examples with pinpoint references"
        if review_status == "reviewed"
        else "Examples pending human review"
    )

    lines = [
        f"# {TITLE}",
        "",
        f"Study title: **{STUDY_NAME}**",
        "",
        (
            "This study runs deterministic first-pass checks over publicly available Title II "
            "crypto-asset white-paper text. Findings are potential disclosure gaps where a "
            "specified Annex I or Article 6 element was not found in extracted text."
        ),
        "",
        (
            "The output is a research artifact. It does not provide legal advice, does not assess "
            "the full legal sufficiency of any white paper, and does not identify public findings "
            "by issuer name."
        ),
        "",
        "## Sample",
        "",
        f"- Documents reviewed: {reviewed}",
        f"- Target sample size: {payload.get('sample_target', reviewed)}",
        f"- Documents excluded before or during batch processing: {summary['documents_excluded']}",
        "- Scope: Title II crypto-assets other than asset-referenced tokens and e-money tokens.",
        "- Public identifiers: WP-001 style study IDs only.",
        "- Raw white papers: not committed.",
        "",
        "## Methodology",
        "",
        (
            "The sample is drawn from the ESMA Interim MiCA Register Title II source data and the "
            "local source manifest. The default v1 rule uses the first eligible WP-001 to WP-010 "
            "candidate set from the source pack, with candidate backfill if a document is inaccessible "
            "or extraction quality is insufficient."
        ),
        "",
        (
            "Each document is loaded locally from `.study-cache/`. XHTML and HTML are parsed first, "
            "including visible text and available inline XBRL tag names. PDF files are extracted with "
            "`pypdf`. Text files are used only as a fallback. Weak extraction is recorded as an exclusion."
        ),
        "",
        (
            "ESMA states on its MiCA page that the interim register includes five CSV files, with the "
            "Title II white-paper file covering crypto-assets other than asset-referenced tokens and "
            "e-money tokens. ESMA also states that white papers in the register have not been reviewed "
            "or approved by any competent authority."
        ),
        "",
        "## What the linter checks",
        "",
        (
            "The study checks 15 deterministic controls: 12 high-signal Annex I disclosure fields and "
            "3 Article 6 controls."
        ),
        "",
    ]
    for rule in payload["rules"]:
        lines.append(f"- `{rule['rule_id']}`: {rule['label']} ({rule['annex_item']}).")

    lines.extend(
        [
            "",
            "## What it does not check",
            "",
            "- It does not assess Annex II or Annex III white papers.",
            "- It does not assess all Annex I fields.",
            "- It does not decide whether any document is legally sufficient.",
            "- It does not replace lawyer review of the full source document.",
            "- It does not republish raw white-paper files.",
            "",
            "## Aggregate findings",
            "",
            f"- Rules checked per document: {summary['rules_checked_per_document']}",
            f"- Machine-flagged potential disclosure gaps: {potential_gaps}",
            f"- High-confidence potential gaps: {high_confidence}",
            f"- Human review status: {review_status}",
            "",
            "## Most frequent potential gaps",
            "",
        ]
    )

    frequent = summary.get("most_frequent_potential_gaps", [])
    if frequent:
        lines.extend(
            [
                "| Rule ID | Count |",
                "| --- | ---: |",
            ]
        )
        for item in frequent[:10]:
            lines.append(f"| `{item['rule_id']}` | {item['count']} |")
    else:
        lines.append("No potential gaps were flagged.")

    lines.extend(["", f"## {example_heading}", ""])
    examples = _example_findings(payload)
    if examples:
        for result, finding in examples:
            evidence = finding["evidence"]
            matched = evidence.get("matched_text") or "No nearby extracted context was identified."
            lines.extend(
                [
                    f"### {result['study_doc_id']} - `{finding['rule_id']}`",
                    "",
                    f"- Annex item: {finding['annex_item']}",
                    f"- Confidence: {finding['confidence']}",
                    f"- Pinpoint: {evidence.get('page_or_section', 'Extracted text')}",
                    f"- Missing element: {evidence.get('missing_element', '')}",
                    f"- Extracted context: {matched}",
                    f"- Review status: {finding['human_review_status']}",
                    "",
                ]
            )
    else:
        lines.append("No example findings are available in the generated findings file.")

    lines.extend(
        [
            "## Limitations",
            "",
            (
                "The sample is not statistically representative. It is a reproducible pilot sample "
                "intended to test whether deterministic Annex I review produces useful public "
                "research artifacts."
            ),
            "",
            (
                "Extraction quality can affect results. A field may be present in a source document "
                "but absent from extracted text, present under wording that the current deterministic "
                "pattern does not capture, or outside the v1 rule scope."
            ),
            "",
            "Excluded documents are listed in `findings-anonymized.json` with reasons.",
            "",
            "## Reproducibility",
            "",
            "```bash",
            "uv run python -m micar_linter.esma_register \\",
            "  --csv .study-cache/esma-title-ii-register.csv \\",
            "  --out studies/2026-07-title-ii-annex-i-whitepaper-study/source-manifest.json",
            "",
            "uv run micar-lint-batch \\",
            "  --manifest studies/2026-07-title-ii-annex-i-whitepaper-study/source-manifest.json \\",
            "  --cache .study-cache/title-ii-whitepapers \\",
            "  --annex annex-i \\",
            "  --out studies/2026-07-title-ii-annex-i-whitepaper-study/findings-anonymized.json",
            "",
            "uv run micar-study-report \\",
            "  --findings studies/2026-07-title-ii-annex-i-whitepaper-study/findings-anonymized.json \\",
            "  --out studies/2026-07-title-ii-annex-i-whitepaper-study/findings-summary.md",
            "```",
            "",
            "## Sources",
            "",
            f"- ESMA MiCA register page: {ESMA_MICA_PAGE}",
            f"- ESMA Article 6 interactive rulebook: {ESMA_ARTICLE_6}",
            f"- ESMA Article 8 interactive rulebook: {ESMA_ARTICLE_8}",
            f"- ESMA Article 109 interactive rulebook: {ESMA_ARTICLE_109}",
            "",
            f"Findings digest: `{payload.get('digest', '')}`",
            "",
        ]
    )
    return "\n".join(lines)


def _example_findings(payload: dict[str, Any]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    examples: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for result in payload.get("results", []):
        high = [finding for finding in result.get("findings", []) if finding.get("confidence") == "high"]
        selected = high or result.get("findings", [])
        if selected:
            examples.append((result, selected[0]))
        if len(examples) >= 5:
            break
    return examples


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render the MiCAR Title II Annex I study report.")
    parser.add_argument("--findings", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = json.loads(args.findings.read_text(encoding="utf-8"))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render_study_report(payload), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
