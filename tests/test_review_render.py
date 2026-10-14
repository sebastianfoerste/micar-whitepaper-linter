"""micar-review-render. The summaries here are built from synthetic labels in memory or under
tmp_path; the committed summary is checked in test_study_consistency.py."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from micar_linter import review_render
from micar_linter.review_render import (
    EXIT_MISMATCH,
    EXIT_OK,
    EXIT_REFUSED,
    EXIT_USAGE,
    RenderRefused,
    check_file,
    refusal_reasons,
    render,
)
from micar_linter.review_validation import StudyContext, summarize_rows

RULES = [f"RULE_{index:02d}" for index in range(1, 16)]
DOCS = ["WP-001", "WP-002", "WP-003", "WP-004", "WP-005", "WP-007", "WP-009", "WP-010", "WP-011", "WP-012"]
DETECTOR = {
    "findings_file": "findings.json",
    "findings_sha256": "f" * 64,
    "findings_schema": "synthetic.v1",
    "findings_digest": "d" * 64,
    "findings_generated_at": "2026-07-06T00:00:00+00:00",
    "commit": "abc1234",
    "commit_source": "analysis-plan.md, section 2, Detector row",
    "commit_status": "named in analysis-plan.md (step 0.4)",
}
FORBIDDEN = re.compile(r"validat|accura", re.IGNORECASE)


def _rows(gaps_per_document: int = 2, *, pending: int = 0, note: str = "") -> list[dict[str, str]]:
    """Synthetic labels: per document, the first rules are flagged; labels vary by position."""
    rows = []
    for d, doc in enumerate(DOCS):
        for r, rule in enumerate(RULES):
            flagged = r < 2
            if r < gaps_per_document:
                label = "missing" if (d + r) % 3 else "present"
            elif r == 14 and d % 4 == 0:
                label = "uncertain"
            elif r == 13 and not flagged and d % 3 == 0:
                label = "missing"
            else:
                label = "present"
            rows.append(
                {
                    "study_doc_id": doc,
                    "rule_id": rule,
                    "detector_status": "flagged" if flagged else "not_flagged",
                    "human_label": label,
                    "review_note": note if doc == "WP-012" else "",
                }
            )
    for row in rows[:pending]:
        row["human_label"] = "pending"
    return rows


def _summary(rows=None, *, reviewers=("r1",), detector=DETECTOR, agreement=None) -> dict:
    rows = rows if rows is not None else _rows()
    # Every reviewer gave the final labels; a test that needs disagreement sets ``agreement``.
    labels = {(row["study_doc_id"], row["rule_id"]): row["human_label"] for row in rows}
    context = StudyContext(
        reviewers=reviewers, detector=detector, sheet_labels=dict.fromkeys(reviewers, labels)
    )
    summary = summarize_rows(rows, context, replicates=400)
    if agreement is not None:
        summary["agreement"] = agreement
    return json.loads(json.dumps(summary))


def test_refuses_while_any_cell_is_pending(tmp_path: Path, capsys):
    summary = _summary(_rows(pending=3))
    reasons = refusal_reasons(summary)
    assert any("3 of 150 cells are pending" in reason for reason in reasons)
    with pytest.raises(RenderRefused):
        render(summary)
    path = tmp_path / "summary.json"
    path.write_text(json.dumps(summary), encoding="utf-8")
    out = tmp_path / "rendered.md"
    assert review_render.main(["--summary", str(path), "--out", str(out)]) == EXIT_REFUSED
    assert "nothing was rendered" in capsys.readouterr().err
    assert not out.exists()


def test_refuses_other_schemas_and_missing_detector_commit(tmp_path: Path):
    path = tmp_path / "summary.json"
    path.write_text(json.dumps({"schema_version": "micar-study-human-validation.v1"}), encoding="utf-8")
    assert review_render.main(["--summary", str(path)]) == EXIT_USAGE
    no_commit = _summary(detector={**DETECTOR, "commit": None, "commit_status": "not recorded"})
    assert any("detector commit is not recorded" in reason for reason in refusal_reasons(no_commit))
    three = _summary(reviewers=("r1", "r2", "r3"))
    assert any("3 reviewers" in reason for reason in refusal_reasons(three))


def _expected_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def test_renders_only_numbers_from_the_summary():
    summary = _summary()
    texts = render(summary)
    primary = summary["analyses"]["primary"]
    precision, recall = primary["metrics"]["precision"], primary["metrics"]["recall"]
    paragraph = texts["study"].splitlines()[1]
    assert paragraph.startswith(
        f"Precision {_expected_pct(precision['estimate'])} (95% CI "
        f"{_expected_pct(precision['headline']['lower'])} to {_expected_pct(precision['headline']['upper'])}, "
        f"{precision['headline']['label']}) and recall {_expected_pct(recall['estimate'])}"
    )
    assert (
        f"on {primary['evaluable_cells']} evaluable of 150 document-rule cells (10 public white papers "
        "from ESMA's interim register \N{MULTIPLICATION SIGN} 15 rules; WP-007 excluded from the primary analysis"
    ) in paragraph
    assert (
        f"; {primary['excluded_cells']} excluded as uncertain, not applicable or extraction failure)"
        in paragraph
    )
    assert "against the tool author's partially blinded labels, single-reviewed. In-sample pilot" in paragraph
    assert texts["profile"] == (
        f"In-sample pilot on 10 public ESMA-register white papers: precision {_expected_pct(precision['estimate'])}, "
        f"recall {_expected_pct(recall['estimate'])} against my own partially blinded, single-reviewed labels "
        f"([study]({review_render.STUDY_URL}))."
    )
    assert texts["cv"].startswith(
        "I measured my MiCAR white-paper linter against my own partially blinded, single-reviewed legal "
        "review of 10 public white papers from ESMA's register: in-sample precision"
    )
    # Every percentage in the output is one the summary implies.
    allowed = set()
    for block in summary["analyses"].values():
        for metric in (block.get("metrics") or {}).values():
            for value in metric.values():
                if isinstance(value, float):
                    allowed.add(_expected_pct(value))
                if isinstance(value, dict):
                    allowed.update(
                        _expected_pct(v)
                        for k, v in value.items()
                        if k in ("lower", "upper") and v is not None
                    )
    for text in texts.values():
        assert set(re.findall(r"\d+\.\d%", text)) <= allowed
        assert not FORBIDDEN.search(text)
    assert "S1, full set with WP-007" in texts["study"]
    assert "WP-007: 15 cells and 2 of the detector's flags" in texts["study"]
    assert "Detector: commit abc1234" in texts["study"]


def test_recall_is_also_a_count_below_ten_gaps():
    texts = render(_summary(_rows(gaps_per_document=1)))
    summary = _summary(_rows(gaps_per_document=1))
    counts = summary["analyses"]["primary"]["confusion_matrix"]
    assert counts["tp"] + counts["fn"] < 10
    phrase = f"{counts['tp']} of {counts['tp'] + counts['fn']} reviewer-identified gaps"
    assert all(phrase in text for text in texts.values())


def test_not_in_sample_drops_the_qualifier_only_when_asked():
    texts = render(_summary(), in_sample=False)
    assert "In-sample" not in texts["study"].splitlines()[1]
    assert texts["profile"].startswith("Pilot on 10 public")
    assert "register: precision" in texts["cv"]
    assert "not-in-sample" in texts["study"].splitlines()[0]


def test_calibration_document_is_named():
    texts = render(_summary(_rows(note="calibration")))
    assert "WP-012 used as the calibration document and excluded from every metric" in texts["study"]


def test_two_reviewers():
    pair = {
        "reviewers": ["r1", "r2"],
        "cells": 150,
        "disagreements": 4,
        "all_labels": {
            "cells": 150,
            "raw_agreement": 0.973333,
            "cohen_kappa": 0.912345,
            "pabak": 0.966667,
            "gwet_ac1": 0.96,
        },
        "present_missing": {"cells": 140, "cohen_kappa": 0.95},
    }
    agreement = {"status": "computed", "pairs": [pair]}
    texts = render(_summary(reviewers=("r1", "r2"), agreement=agreement))
    assert "against two lawyers' labels, Cohen's κ = 0.91, adjudicated." in texts["study"]
    assert "my own and a second lawyer's labels (κ = 0.91)" in texts["profile"]
    assert "single-reviewed" not in texts["cv"]
    assert texts["cv"].endswith("; second-reviewer agreement κ = 0.91.")
    no_kappa = _summary(
        reviewers=("r1", "r2"), agreement={"status": "incomplete", "reason": "r2 pending", "pairs": []}
    )
    assert any("second reviewer's agreement" in reason for reason in refusal_reasons(no_kappa))


def test_check_file(tmp_path: Path):
    summary = _summary()
    block = render(summary)["study"]
    readme = f"# Study\n\nIntro.\n\n{block}\nMore text.\n"
    assert check_file(summary, "# Study\nNo results yet.\n")[0] == EXIT_OK
    assert check_file(summary, readme)[0] == EXIT_OK
    tampered = readme.replace("Precision ", "Precision 9", 1)
    assert check_file(summary, tampered)[0] == EXIT_MISMATCH
    assert check_file(_summary(_rows(pending=1)), readme)[0] == EXIT_REFUSED
    assert (
        check_file(summary, "<!-- micar-review-render:begin study-results in-sample -->\n")[0] == EXIT_USAGE
    )
    assert check_file(summary, readme + readme)[0] == EXIT_USAGE
    # The mode recorded in the marker decides the qualifier.
    other = render(summary, in_sample=False)["study"]
    assert check_file(summary, other)[0] == EXIT_OK

    path, target = tmp_path / "summary.json", tmp_path / "README.md"
    path.write_text(json.dumps(summary), encoding="utf-8")
    target.write_text(readme, encoding="utf-8")
    assert review_render.main(["--summary", str(path), "--check", str(target)]) == EXIT_OK
    target.write_text(tampered, encoding="utf-8")
    assert review_render.main(["--summary", str(path), "--check", str(target)]) == EXIT_MISMATCH


def test_cli_writes_the_rendering(tmp_path: Path, capsys):
    path, out = tmp_path / "summary.json", tmp_path / "rendered.md"
    path.write_text(json.dumps(_summary()), encoding="utf-8")
    assert review_render.main(["--summary", str(path), "--out", str(out)]) == EXIT_OK
    text = out.read_text(encoding="utf-8")
    assert "## Profile README line" in text
    assert "## CV or application sentence" in text
    assert "step 0.2" in capsys.readouterr().err
