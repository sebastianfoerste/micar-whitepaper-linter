"""Markdown renderer for the MiCAR Title II Annex I study."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

TITLE = "MiCAR Title II White Paper Pilot: Machine-Flagged Annex I Candidate Gaps Pending Human Review"
STUDY_NAME = "MiCAR White Paper Study 2026: Annex I Disclosure Patterns in Notified Title II White Papers"
ESMA_MICA_PAGE = (
    "https://www.esma.europa.eu/esmas-activities/digital-finance-and-innovation/"
    "markets-crypto-assets-regulation-mica"
)
ESMA_ARTICLE_6 = "https://www.esma.europa.eu/publications-and-data/interactive-single-rulebook/mica/article-6-content-and-form-crypto-asset"
ESMA_ARTICLE_8 = "https://www.esma.europa.eu/publications-and-data/interactive-single-rulebook/mica/article-8-notification-crypto-asset-white"
ESMA_ARTICLE_109 = "https://www.esma.europa.eu/publications-and-data/interactive-single-rulebook/mica/article-109-register-crypto-asset-white"
ESMA_ANNEX_I = "https://www.esma.europa.eu/publications-and-data/interactive-single-rulebook/mica/disclosure-items-crypto-asset-white-paper"
EUR_LEX_MICAR = "https://eur-lex.europa.eu/eli/reg/2023/1114/oj/eng"
ESMA_PAGE_LAST_CHECKED = "2026-07-06"
ESMA_PAGE_LAST_UPDATE = "3 July 2026"


def render_study_report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    reviewed = summary["documents_reviewed"]
    potential_gaps = summary["potential_gaps"]
    high_confidence = summary["high_confidence_gaps"]
    review_status = payload.get("human_review_status", "pending_review")
    source_manifest = payload.get("source_manifest", {})
    source_detail = _display_source_detail(
        source_manifest.get("register_source_detail", payload.get("manifest_path", ""))
    )
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
            "crypto-asset white-paper text. A candidate flag means that a specified Annex I "
            "or Article 6 element was not found in extracted text. It is not a reviewed legal finding."
        ),
        "",
        (
            "The output is a research artifact. It does not provide legal advice and does not "
            "assess the full legal sufficiency of any white paper. Findings tables use WP-ID "
            "identifiers rather than printing issuer names inline; the source manifest links each "
            "WP-ID to its public ESMA register entry, so findings are traceable to their source "
            "and are not anonymized. Findings are machine-flagged and pending human legal review; "
            "a flag is a candidate gap in extracted text, not a confirmed deficiency by the named "
            "issuer."
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
            "The v1 sample comes from a curated 20-entry candidate manifest derived from public register "
            "data. It uses the first ten eligible candidates, with backfill where a document is "
            "inaccessible or extraction quality is insufficient. This convenience sample is reproducible "
            "but is not random, issuer-deduplicated, stratified, or statistically representative."
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
        (
            f"Current-source check: ESMA's MiCA page was checked on {ESMA_PAGE_LAST_CHECKED} "
            f"and displayed a register last update of {ESMA_PAGE_LAST_UPDATE}. Article 8 states "
            "that competent authorities shall not require prior approval of Title II crypto-asset "
            "white papers before publication. Article 109 states that ESMA's register includes "
            "white papers for crypto-assets other than asset-referenced tokens or e-money tokens."
        ),
        "",
        f"Source manifest: `{source_detail}`",
        f"Source manifest input SHA-256: `{source_manifest.get('register_source_sha256', '')}`",
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
            f"- Machine-flagged candidate gaps: {potential_gaps}",
            f"- High-confidence detector flags: {high_confidence}",
            f"- Human review status: {review_status}",
            "",
            "## Human validation gate",
            "",
            "The 150 document-rule cells are listed in `human-review-matrix.csv`. No precision, recall, "
            "false-positive, or false-negative claim is made until qualified reviewers label every cell "
            "under `review-protocol.md` and `micar-review-summary --require-complete` exits successfully.",
            "",
            "Document byte hashes and extraction metadata are recorded in `document-provenance.json`.",
            "",
            "## Most frequent detector flags",
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
        lines.append("No candidate gaps were flagged.")

    lines.extend(["", "## Excluded documents", ""])
    excluded_documents = payload.get("excluded_documents", [])
    if excluded_documents:
        lines.extend(
            [
                "| Study ID | Reason |",
                "| --- | --- |",
            ]
        )
        for item in excluded_documents:
            lines.append(
                f"| `{item.get('study_doc_id', '')}` | `{item.get('exclusion_reason', '')}` |"
            )
    else:
        lines.append("No documents were excluded in this run.")

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
                "The sample is a small convenience sample with repeated issuers. It is not statistically "
                "representative and must not support prevalence estimates. It tests the review "
                "workflow and detector behavior only."
            ),
            "",
            (
                "Extraction quality can affect results. A field may be present in a source document "
                "but absent from extracted text, present under wording that the current deterministic "
                "pattern does not capture, or outside the v1 rule scope."
            ),
            "",
            "Excluded documents are listed in `findings-pseudonymous.json` with reasons.",
            "",
            "## Reproducibility",
            "",
            "```bash",
            "uv run python -m micar_linter.esma_register \\",
            "  --csv studies/2026-07-title-ii-annex-i-whitepaper-study/sample-manifest.csv \\",
            "  --out studies/2026-07-title-ii-annex-i-whitepaper-study/source-manifest.json",
            "",
            "uv run micar-lint-batch \\",
            "  --manifest studies/2026-07-title-ii-annex-i-whitepaper-study/source-manifest.json \\",
            "  --cache .study-cache/title-ii-whitepapers \\",
            "  --annex annex-i \\",
            "  --out studies/2026-07-title-ii-annex-i-whitepaper-study/findings-pseudonymous.json",
            "",
            "uv run micar-study-report \\",
            "  --findings studies/2026-07-title-ii-annex-i-whitepaper-study/findings-pseudonymous.json \\",
            "  --out studies/2026-07-title-ii-annex-i-whitepaper-study/findings-summary.md",
            "```",
            "",
            "## Sources",
            "",
            f"- ESMA MiCA register page: {ESMA_MICA_PAGE}",
            f"- ESMA Article 6 interactive rulebook: {ESMA_ARTICLE_6}",
            f"- ESMA Article 8 interactive rulebook: {ESMA_ARTICLE_8}",
            f"- ESMA Article 109 interactive rulebook: {ESMA_ARTICLE_109}",
            f"- ESMA Annex I disclosure items: {ESMA_ANNEX_I}",
            f"- EUR-Lex Regulation (EU) 2023/1114: {EUR_LEX_MICAR}",
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


def _display_source_detail(value: Any) -> str:
    text = str(value or "")
    source_pack_marker = "micar_title_ii_whitepaper_20_source_pack"
    if source_pack_marker in text:
        return source_pack_marker + text.split(source_pack_marker, 1)[1]
    return text


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
