"""Render the Title II study's result sentences from ``human-review-summary.json`` alone.

``micar-review-render`` reads only the summary JSON written by ``micar-review-summary``; no figure
is typed by hand. It renders, in the wording templates of ``analysis-plan.md`` section 11:

- the study results block: the results paragraph, a table of the primary analysis and the
  sensitivity analyses (S1 is reported with equal prominence, analysis-plan.md section 5) and the
  disclosures of section 11;
- the profile README line;
- the CV or application sentence.

It refuses (exit 1) and lists the reasons unless the summary is complete: no cell pending,
``publication_ready`` true (``micar-review-summary --require-complete`` exits 0), precision and
recall defined in the primary set, the detector commit recorded (analysis-plan.md step 0.4), and,
with a second reviewer, their agreement computed. The result is never called "validated" and is
not an accuracy, detection or compliance rate.

The templates say "[In-sample]" unless step 0.5 rules it out; ``--not-in-sample`` drops the word
and is passed only after that step. Preconditions that the summary cannot show, such as the
register reconciliation of step 0.2, are printed as reminders.

``--check FILE`` compares the results block in FILE, between the begin and end markers that the
renderer writes, with a fresh rendering. A file without a block passes; a block fails while the
summary is incomplete or when it differs from the rendering.

Exit status: 0 rendered, or checked and consistent; 1 refused because the summary is incomplete
or lacks a required value; 2 usage or input error; 3 the block in ``--check`` FILE differs from
the rendering.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from micar_linter.review_validation import PENDING_LABEL, PRIMARY_EXCLUSIONS, SUMMARY_SCHEMA

EXIT_OK = 0
EXIT_REFUSED = 1
EXIT_USAGE = 2
EXIT_MISMATCH = 3

STUDY_URL = (
    "https://github.com/sebastianfoerste/micar-whitepaper-linter/tree/main/studies/"
    "2026-07-title-ii-annex-i-whitepaper-study"
)
IN_SAMPLE = "in-sample"
NOT_IN_SAMPLE = "not-in-sample"
BEGIN_MARKER = "<!-- micar-review-render:begin study-results {mode} -->"
END_MARKER = "<!-- micar-review-render:end study-results -->"
_BLOCK = re.compile(
    r"<!-- micar-review-render:begin study-results (?P<mode>in-sample|not-in-sample) -->\n"
    r".*?<!-- micar-review-render:end study-results -->\n?",
    re.DOTALL,
)
_ANY_BEGIN = re.compile(r"<!-- micar-review-render:begin")
# Words the rendered text must never use (analysis-plan.md section 11).
_FORBIDDEN = re.compile(r"\bvalidat|\baccura|\bcompliance rate|\bprevalence estimate", re.IGNORECASE)
TABLE_HEADER = (
    "| Analysis | Documents | Cells | Evaluable | TP | FP | FN | TN | Precision (95% CI) | Recall (95% CI) |"
)
# The study-summary template of analysis-plan.md section 11 joins "10 public white papers" and
# "15 rules" with the multiplication sign.
TIMES = "\N{MULTIPLICATION SIGN}"
# analysis-plan.md section 8: below 10 reviewer-identified gaps, recall is also given as a count.
GAPS_AS_COUNT_BELOW = 10
SENSITIVITY_ROWS: tuple[tuple[str, str], ...] = (
    ("primary", "Primary"),
    ("S1", "S1, full set with WP-007"),
    ("S2b", "S2(b), one document per offeror"),
    ("S3", "S3, uncertain counted as missing"),
    ("S4", "S4, uncertain counted as present"),
)
REMINDERS: tuple[str, ...] = (
    '"from ESMA\'s interim register" holds only after the register reconciliation of '
    "analysis-plan.md step 0.2.",
    'Drop "In-sample" (--not-in-sample) only if analysis-plan.md step 0.5 rules it out.',
    "Publish aggregate figures only, after the conflicts check and the legal review of "
    "review-protocol.md (Publication gate, item 6) and the decision in analysis-plan.md section 11.",
    "The wording follows the draft templates of analysis-plan.md section 11; re-check it against the "
    "adopted plan.",
)


class RenderRefused(Exception):
    """The summary cannot back the result sentences; ``reasons`` lists why."""

    def __init__(self, reasons: Sequence[str], exit_code: int = EXIT_REFUSED) -> None:
        super().__init__("; ".join(reasons))
        self.reasons = list(reasons)
        self.exit_code = exit_code


def refusal_reasons(summary: Mapping[str, Any]) -> list[str]:
    """Every reason why the summary cannot be rendered; an empty list means it can."""
    if summary.get("schema_version") != SUMMARY_SCHEMA:
        return [f"schema_version is {summary.get('schema_version')!r}, expected {SUMMARY_SCHEMA!r}"]
    reasons: list[str] = []
    pending = summary.get("rows_pending")
    labelled_pending = (summary.get("label_counts") or {}).get(PENDING_LABEL)
    if pending != 0 or labelled_pending != 0:
        reasons.append(
            f"{pending} of {summary.get('rows_total')} cells are pending; every cell needs a final label"
        )
    if summary.get("publication_ready") is not True:
        reasons.append("publication_ready is not true: micar-review-summary --require-complete would exit 2")
    analyses = summary.get("analyses") or {}
    for key, block in analyses.items():
        if isinstance(block, Mapping) and block.get("pending_cells"):
            reasons.append(f"analysis {key} has {block['pending_cells']} pending cells")
    primary = analyses.get("primary") or {}
    for name in ("precision", "recall"):
        metric = (primary.get("metrics") or {}).get(name) or {}
        if metric.get("estimate") is None:
            reasons.append(
                f"primary {name} is undefined ({metric.get('undefined_reason')}); the templates of "
                "analysis-plan.md section 11 need a defined value, so the reviewer decides the wording"
            )
        elif (metric.get("headline") or {}).get("lower") is None:
            reasons.append(f"primary {name} has no headline interval")
    detector = summary.get("detector") or {}
    if not detector.get("commit"):
        reasons.append(
            f"the detector commit is not recorded ({detector.get('commit_status')}); name it in "
            "analysis-plan.md section 2 (step 0.4) and rerun micar-review-summary"
        )
    reviewers = summary.get("reviewers")
    if not reviewers:
        reasons.append("the summary records no reviewers (human-review-sheets.json was not read)")
    elif len(reviewers) > 2:
        reasons.append(f"{len(reviewers)} reviewers: the templates cover one or two reviewers")
    elif len(reviewers) == 2:
        pair = _agreement_pair(summary)
        if pair is None or pair["all_labels"].get("cohen_kappa") is None:
            agreement = summary.get("agreement") or {}
            reasons.append(
                "the second reviewer's agreement is not computed or Cohen's kappa is undefined "
                f"({agreement.get('reason') or (pair or {}).get('all_labels', {}).get('undefined_reason')})"
            )
    unexpected = [
        item.get("study_doc_id")
        for item in (summary.get("exclusions") or {}).get("primary", [])
        if item.get("study_doc_id") not in PRIMARY_EXCLUSIONS
    ]
    if unexpected:
        reasons.append(f"primary exclusions {unexpected}: the templates cover only the WP-007 exclusion")
    return reasons


def render(summary: Mapping[str, Any], *, in_sample: bool = True) -> dict[str, str]:
    """``{"study", "profile", "cv"}``: the three texts, or ``RenderRefused``."""
    reasons = refusal_reasons(summary)
    if reasons:
        raise RenderRefused(reasons)
    texts = {
        "study": _study_block(summary, in_sample=in_sample),
        "profile": _profile_line(summary, in_sample=in_sample),
        "cv": _cv_sentence(summary, in_sample=in_sample),
    }
    for name, text in texts.items():
        found = _FORBIDDEN.search(text)
        if found:  # pragma: no cover - a guard against future template edits
            raise RuntimeError(f"the {name} text uses the forbidden wording {found.group(0)!r}")
    return texts


def render_document(summary: Mapping[str, Any], *, in_sample: bool = True, source: str = "") -> str:
    """The full output: the study block, then the profile line and the CV sentence."""
    texts = render(summary, in_sample=in_sample)
    origin = f" from {source}" if source else ""
    return (
        f"<!-- Rendered by micar-review-render{origin}. Do not edit the figures by hand. -->\n\n"
        "## Study results block (paste into the study README or report)\n\n"
        f"{texts['study']}\n"
        "## Profile README line\n\n"
        f"{texts['profile']}\n\n"
        "## CV or application sentence\n\n"
        f"{texts['cv']}\n"
    )


def check_file(summary: Mapping[str, Any], text: str) -> tuple[int, str]:
    """Check the rendered block in ``text`` against the summary; returns (exit code, message)."""
    blocks = list(_BLOCK.finditer(text))
    begins = len(_ANY_BEGIN.findall(text))
    if begins != len(blocks):
        return EXIT_USAGE, "a micar-review-render begin marker has no matching end marker or an unknown mode"
    if not blocks:
        return EXIT_OK, "no rendered results block; nothing to check"
    if len(blocks) > 1:
        return EXIT_USAGE, f"{len(blocks)} rendered results blocks; keep one"
    block = blocks[0]
    try:
        expected = render(summary, in_sample=block.group("mode") == IN_SAMPLE)["study"]
    except RenderRefused as exc:
        return EXIT_REFUSED, "the file carries a results block, but the summary cannot back it: " + "; ".join(
            exc.reasons
        )
    if block.group(0).rstrip("\n") != expected.rstrip("\n"):
        return EXIT_MISMATCH, "the results block differs from a fresh rendering of the summary"
    return EXIT_OK, "the results block matches the summary"


def _study_block(summary: Mapping[str, Any], *, in_sample: bool) -> str:
    primary = summary["analyses"]["primary"]
    lines = [
        BEGIN_MARKER.format(mode=IN_SAMPLE if in_sample else NOT_IN_SAMPLE),
        _study_paragraph(summary, in_sample=in_sample),
        "",
        TABLE_HEADER,
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    analyses = summary["analyses"]
    for key, name in SENSITIVITY_ROWS:
        block = analyses.get(key) or {}
        if "metrics" not in block:
            lines.append(f"| {name} | | | | | | | | not computed: {block.get('undefined_reason')} | |")
            continue
        counts = block["confusion_matrix"]
        lines.append(
            f"| {name} | {len(block['documents'])} | {block['cells']} | {block['evaluable_cells']} | "
            f"{counts['tp']} | {counts['fp']} | {counts['fn']} | {counts['tn']} | "
            f"{_metric_cell(block['metrics']['precision'])} | {_metric_cell(block['metrics']['recall'])} |"
        )
    lines.append("")
    lines.append(_s2a_sentence(analyses.get("S2a") or {}))
    s5 = analyses.get("S5") or {}
    lines.append(f"S5 was not computed: {s5.get('undefined_reason')}.")
    lines.append("")
    lines.append("Disclosures:")
    lines.extend(f"- {item}" for item in _disclosures(summary, primary, in_sample=in_sample))
    lines.append(END_MARKER)
    return "\n".join(lines) + "\n"


def _study_paragraph(summary: Mapping[str, Any], *, in_sample: bool) -> str:
    primary = summary["analyses"]["primary"]
    precision = primary["metrics"]["precision"]
    recall = primary["metrics"]["recall"]
    precision_ci = f"95% CI {_interval(precision['headline'])}, {precision['headline']['label']}"
    recall_ci = _interval(recall["headline"])
    if recall["headline"]["label"] != precision["headline"]["label"]:
        recall_ci += f", {recall['headline']['label']}"
    gaps = _gaps(primary)
    if gaps:
        recall_ci += f"; {gaps}"
    clauses = [
        f"{summary['documents_total']} public white papers from ESMA's interim register {TIMES} "
        f"{summary['rules_per_document']} rules"
    ]
    if _excluded_ids(summary):
        clauses.append(
            "WP-007 excluded from the primary analysis under a rule fixed before labelling but after "
            "the detector output (post-hoc; see S1)"
        )
    calibration = summary["exclusions"]["calibration_document"].get("study_doc_id")
    if calibration:
        clauses.append(f"{calibration} used as the calibration document and excluded from every metric")
    clauses.append(f"{primary['excluded_cells']} excluded as uncertain, not applicable or extraction failure")
    return (
        f"Precision {_pct(precision['estimate'])} ({precision_ci}) and recall {_pct(recall['estimate'])} "
        f"({recall_ci}) on {primary['evaluable_cells']} evaluable of {summary['rows_total']} document-rule "
        f"cells ({'; '.join(clauses)}), against {_labels_phrase(summary)}. "
        f"{'In-sample pilot' if in_sample else 'Pilot'} on a convenience sample; not a prevalence or "
        "compliance finding."
    )


def _profile_line(summary: Mapping[str, Any], *, in_sample: bool) -> str:
    primary = summary["analyses"]["primary"]
    recall = _pct(primary["metrics"]["recall"]["estimate"])
    gaps = _gaps(primary)
    if gaps:
        recall += f" ({gaps})"
    pair = _agreement_pair(summary)
    labels = (
        f"my own and a second lawyer's labels (κ = {_kappa(pair)})"
        if pair
        else "my own partially blinded, single-reviewed labels"
    )
    return (
        f"{'In-sample pilot' if in_sample else 'Pilot'} on {summary['documents_total']} public "
        f"ESMA-register white papers: precision {_pct(primary['metrics']['precision']['estimate'])}, "
        f"recall {recall} against {labels} ([study]({STUDY_URL}))."
    )


def _cv_sentence(summary: Mapping[str, Any], *, in_sample: bool) -> str:
    primary = summary["analyses"]["primary"]
    precision = primary["metrics"]["precision"]
    recall = primary["metrics"]["recall"]
    pair = _agreement_pair(summary)
    review = "partially blinded legal review" if pair else "partially blinded, single-reviewed legal review"
    recall_ci = _interval(recall["headline"])
    gaps = _gaps(primary)
    if gaps:
        recall_ci += f"; {gaps}"
    agreement = f"; second-reviewer agreement κ = {_kappa(pair)}" if pair else ""
    return (
        f"I measured my MiCAR white-paper linter against my own {review} of "
        f"{summary['documents_total']} public white papers from ESMA's register: "
        f"{'in-sample ' if in_sample else ''}precision {_pct(precision['estimate'])} "
        f"(95% CI {_interval(precision['headline'])}), recall {_pct(recall['estimate'])} ({recall_ci}) on "
        f"{primary['evaluable_cells']} of {summary['rows_total']} document-rule cells{agreement}."
    )


def _disclosures(summary: Mapping[str, Any], primary: Mapping[str, Any], *, in_sample: bool) -> list[str]:
    pair = _agreement_pair(summary)
    items: list[str] = []
    if pair:
        everything, evaluable = pair["all_labels"], pair["present_missing"]
        adjudicated = (
            f"{pair['disagreements']} disagreements adjudicated"
            if pair["disagreements"]
            else "no disagreements"
        )
        items.append(
            f"Labels: the tool author's and a second lawyer's ({' and '.join(pair['reviewers'])}), "
            f"reviewed independently; {adjudicated}. Agreement on {everything['cells']} cells: raw "
            f"{_pct(everything['raw_agreement'])}, Cohen's κ = {_number(everything['cohen_kappa'])} "
            f"over all labels, PABAK {_number(everything['pabak'])}, Gwet's AC1 "
            f"{_number(everything['gwet_ac1'])}; on the {evaluable['cells']} cells both labelled present "
            f"or missing, Cohen's κ = {_number(evaluable['cohen_kappa'])}."
        )
    else:
        items.append(
            "Labels: the tool author's, single-reviewed. Blinding is partial: the author wrote the "
            "detector and had access to the published flag counts and examples."
        )
    items.append(
        "In-sample: the analysis plan's step 0.5 did not rule out that study rules were written or "
        "changed after viewing these documents."
        if in_sample
        else "Out of sample: the analysis plan's step 0.5 ruled out that study rules were written or "
        "changed after viewing these documents."
    )
    items.append(
        f"Sample: a convenience sample of {summary['documents_total']} public white papers; not a "
        "prevalence or compliance finding, and no statement about any issuer or offeror."
    )
    for item in summary["exclusions"]["primary"]:
        items.append(
            f"{item['study_doc_id']}: {item['cells']} cells and {item['detector_flags']} of the detector's "
            "flags, excluded from the primary analysis post-hoc; S1 includes it."
        )
    calibration = summary["exclusions"]["calibration_document"]
    if calibration.get("study_doc_id"):
        items.append(
            f"Calibration: {calibration['study_doc_id']} ({calibration['cells']} cells) was used to "
            "calibrate the codebook and enters no metric."
        )
    bootstrap = summary["settings"]["bootstrap"]
    clusters = primary["metrics"]["precision"]["document_cluster_bootstrap"]["clusters"]
    items.append(
        "Intervals: the Wilson and Clopper-Pearson intervals assume independent cells. The "
        f"document-cluster bootstrap (B = {bootstrap['replicates']:,}, seed {bootstrap['seed']}) "
        f"resamples only {clusters} documents and is unstable with so few clusters. The headline "
        "interval is the wider of the two."
    )
    detector = summary["detector"]
    items.append(
        f"Detector: commit {detector['commit']} ({detector['commit_source']}); findings file "
        f"{detector['findings_file']}, SHA-256 {detector['findings_sha256']}, generated "
        f"{str(detector['findings_generated_at'])[:10]}."
    )
    items.append(f"Definitions: {summary['settings']['definitions']}.")
    return items


def _s2a_sentence(block: Mapping[str, Any]) -> str:
    if "metrics" not in block:
        return f"S2(a), the offeror-cluster bootstrap, was not computed: {block.get('undefined_reason')}."
    parts = []
    for name in ("precision", "recall"):
        metric = block["metrics"][name]
        interval = metric["offeror_cluster_bootstrap"]
        if metric["estimate"] is None or interval["lower"] is None:
            parts.append(f"{name} undefined")
        else:
            parts.append(f"{name} {_pct(metric['estimate'])} ({_interval(interval)})")
    return (
        f"S2(a), offeror-cluster bootstrap over the primary set ({block['offeror_clusters']} offerors): "
        f"{', '.join(parts)}."
    )


def _metric_cell(metric: Mapping[str, Any]) -> str:
    if metric["estimate"] is None:
        return f"undefined ({metric['undefined_reason']})"
    headline = metric["headline"]
    return f"{_pct(metric['estimate'])} ({_interval(headline)}, {headline['label']})"


def _gaps(block: Mapping[str, Any]) -> str:
    counts = block["confusion_matrix"]
    gaps = counts["tp"] + counts["fn"]
    if gaps >= GAPS_AS_COUNT_BELOW:
        return ""
    return f"{counts['tp']} of {gaps} reviewer-identified gaps"


def _labels_phrase(summary: Mapping[str, Any]) -> str:
    pair = _agreement_pair(summary)
    if not pair:
        return "the tool author's partially blinded labels, single-reviewed"
    adjudicated = ", adjudicated" if pair["disagreements"] else ""
    return f"two lawyers' labels, Cohen's κ = {_kappa(pair)}{adjudicated}"


def _agreement_pair(summary: Mapping[str, Any]) -> Mapping[str, Any] | None:
    agreement = summary.get("agreement") or {}
    if agreement.get("status") != "computed" or len(agreement.get("pairs") or []) != 1:
        return None
    return agreement["pairs"][0]


def _excluded_ids(summary: Mapping[str, Any]) -> list[str]:
    return [item["study_doc_id"] for item in summary["exclusions"]["primary"]]


def _interval(interval: Mapping[str, Any]) -> str:
    return f"{_pct(interval['lower'])} to {_pct(interval['upper'])}"


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _kappa(pair: Mapping[str, Any]) -> str:
    return _number(pair["all_labels"]["cohen_kappa"])


def _number(value: float | None) -> str:
    return "undefined" if value is None else f"{value:.2f}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="micar-review-render",
        description=(
            "Render the study's results paragraph, profile README line and CV sentence from "
            "human-review-summary.json alone. Refuses while any cell is pending or a required value "
            "is missing."
        ),
    )
    parser.add_argument("--summary", required=True, type=Path, help="human-review-summary.json")
    parser.add_argument("--out", type=Path, default=None, help="write the rendering here (default: stdout)")
    parser.add_argument(
        "--not-in-sample",
        action="store_true",
        help='drop "In-sample"; only if analysis-plan.md step 0.5 ruled out tuning on these documents',
    )
    parser.add_argument(
        "--check",
        type=Path,
        default=None,
        metavar="FILE",
        help="verify the rendered results block in FILE against the summary instead of rendering",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary = json.loads(args.summary.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"micar-review-render: cannot read {args.summary}: {exc}", file=sys.stderr)
        return EXIT_USAGE
    if not isinstance(summary, dict):
        print(f"micar-review-render: {args.summary} is not a summary object", file=sys.stderr)
        return EXIT_USAGE

    if args.check is not None:
        try:
            text = args.check.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"micar-review-render: cannot read {args.check}: {exc}", file=sys.stderr)
            return EXIT_USAGE
        status, message = check_file(summary, text)
        print(f"micar-review-render: {args.check.name}: {message}", file=sys.stderr)
        return status

    if summary.get("schema_version") != SUMMARY_SCHEMA:
        print(f"micar-review-render: {refusal_reasons(summary)[0]}", file=sys.stderr)
        return EXIT_USAGE
    try:
        document = render_document(summary, in_sample=not args.not_in_sample, source=args.summary.name)
    except RenderRefused as exc:
        print("micar-review-render: refused; nothing was rendered:", file=sys.stderr)
        for reason in exc.reasons:
            print(f"  {reason}", file=sys.stderr)
        return exc.exit_code
    if args.out is None:
        sys.stdout.write(document)
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(document, encoding="utf-8")
    print("micar-review-render: reminders before using the text:", file=sys.stderr)
    for reminder in REMINDERS:
        print(f"  {reminder}", file=sys.stderr)
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
