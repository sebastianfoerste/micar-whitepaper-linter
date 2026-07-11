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
