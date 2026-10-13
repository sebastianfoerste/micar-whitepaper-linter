from micar_linter.review_validation import summarize_rows


def test_summary_excludes_unresolved_labels_from_metrics():
    rows = [
        {"detector_status": "flagged", "human_label": "missing"},
        {"detector_status": "flagged", "human_label": "present"},
        {"detector_status": "not_flagged", "human_label": "missing"},
        {"detector_status": "not_flagged", "human_label": "present"},
        {"detector_status": "flagged", "human_label": "uncertain"},
        {"detector_status": "not_flagged", "human_label": "pending"},
    ]

    summary = summarize_rows(rows)

    assert summary["confusion_matrix"] == {"tp": 1, "fp": 1, "fn": 1, "tn": 1}
    assert summary["metrics"]["precision"] == 0.5
    assert summary["metrics"]["recall"] == 0.5
    assert summary["metrics"]["f1"] == 0.5
    assert summary["rows_pending"] == 1
    assert summary["publication_ready"] is False


def test_all_complete_rows_are_publication_ready():
    summary = summarize_rows(
        [
            {"detector_status": "flagged", "human_label": "missing"},
            {"detector_status": "not_flagged", "human_label": "present"},
        ]
    )

    assert summary["publication_ready"] is True
    assert summary["completion_rate"] == 1.0


def test_review_sheets_use_the_detector_rule_ids():
    # Regression: the sheets carried rule IDs (e.g. ANNEX_I_PART_A_01_LEGAL_FORM) that the
    # detector output no longer used.
    import csv
    import json
    from pathlib import Path

    study = Path(__file__).resolve().parents[1] / "studies" / "2026-07-title-ii-annex-i-whitepaper-study"
    payload = json.loads((study / "findings-pseudonymous.json").read_text(encoding="utf-8"))
    rule_ids = [rule["rule_id"] for rule in payload["rules"]]
    expected = [(doc["study_doc_id"], rule_id) for doc in payload["results"] for rule_id in rule_ids]
    flagged = {(doc["study_doc_id"], f["rule_id"]) for doc in payload["results"] for f in doc["findings"]}

    for name in ("human-review-matrix.csv", "human-review-blinded.csv"):
        with (study / name).open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        assert [(row["study_doc_id"], row["rule_id"]) for row in rows] == expected, name
        if name == "human-review-matrix.csv":
            assert {
                (row["study_doc_id"], row["rule_id"]) for row in rows if row["detector_status"] == "flagged"
            } == flagged
