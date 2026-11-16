"""Second review and adjudication of the Title II study's human review.

Every cell, reviewer and date below is synthetic. No test reads or writes the committed sheets;
the command-line tests build a synthetic study under tmp_path.
"""

import csv
import hashlib
import io
import json
import runpy
import sys
from datetime import date
from fractions import Fraction
from pathlib import Path

import pytest

from micar_linter.review_validation import (
    ALLOWED_LABELS,
    DISAGREEMENT_FIELDS,
    adjudicated_cells,
    carry_adjudications,
    disagreement_rows,
    latest_review_date,
    second_review_problems,
    second_review_selection,
    summarize_rows,
)

STUDY = Path(__file__).resolve().parents[1] / "studies" / "2026-07-title-ii-annex-i-whitepaper-study"
RUN = date(2026, 7, 6)
TODAY = date(2026, 10, 30)


def _keys(documents, rules):
    return [
        (f"SYN-{doc:03d}", f"SYNTHETIC_RULE_{rule:02d}")
        for doc in range(1, documents + 1)
        for rule in range(1, rules + 1)
    ]


def _cell(label, reviewer="reviewer-a", when="2026-10-14", pinpoint="synthetic section 1", note=""):
    return {
        "human_label": label,
        "reviewer_id": reviewer,
        "reviewed_at": when,
        "source_pinpoint": pinpoint,
        "review_note": note,
    }


def _rank(seed, key):
    return hashlib.sha256(f"{seed}|second-review|{key[0]}|{key[1]}".encode()).hexdigest()


def test_selection_takes_the_flagged_and_noted_cells_and_a_fifth_of_the_rest_by_hash():
    # The shape of the study: 150 cells, 21 flagged, so 26 of the 129 non-flagged cells are drawn.
    keys = _keys(10, 15)
    flagged = set(keys[::7][:21])
    non_flagged = [key for key in keys if key not in flagged]
    drawn = sorted(non_flagged, key=lambda key: _rank(20261014, key))[:26]

    selected = second_review_selection(keys, flagged, {}, seed=20261014)

    assert set(selected) == flagged | set(drawn)
    assert len(selected) == 47
    assert selected == [key for key in keys if key in set(selected)]

    # A first-review label that needs a note adds its cell; no other label moves the draw.
    noted = [key for key in non_flagged if key not in set(selected)][:3]
    labels = {key: "present" for key in keys}
    labels.update(zip(noted, ("uncertain", "extraction_failure", "not_applicable"), strict=True))
    assert set(second_review_selection(keys, flagged, labels, seed=20261014)) == set(selected) | set(noted)

    assert second_review_selection(keys, flagged, {}, seed=1) != selected
    assert len(second_review_selection(keys, flagged, {}, seed=1, fraction=Fraction(1, 4))) == 21 + 33
    assert second_review_selection(keys, flagged, {}, seed=1, fraction=1) == keys
    with pytest.raises(ValueError, match=r"between 0\.2 and 1"):
        second_review_selection(keys, flagged, {}, seed=1, fraction=Fraction(1, 10))


def test_second_sheet_must_hold_the_protocol_cells_and_be_complete():
    keys = _keys(2, 5)
    flagged = {keys[0], keys[6]}
    first = {key: _cell("present") for key in keys}
    first[keys[3]] = _cell("uncertain", pinpoint="", note="synthetic: two readings")

    problems = second_review_problems(
        keys, flagged, first, {keys[0]: _cell("pending", "", "", "")}, today=TODAY, not_before=RUN
    )
    assert problems == [
        "the second sheet lacks cells that the protocol has the second reviewer assess (flagged, or "
        "labelled uncertain, extraction_failure or not_applicable in the first review): "
        "SYN-001 SYNTHETIC_RULE_04, SYN-002 SYNTHETIC_RULE_02",
        "the second sheet holds 0 of the 8 non-flagged cells; the protocol asks for at least 20%, that is 2",
        "1 of 1 second-review cells are still pending",
    ]

    second = {key: _cell("present", "reviewer-b") for key in (keys[0], keys[1], keys[3], keys[6])}
    second[keys[3]] = _cell("uncertain", "reviewer-b", pinpoint="", note="synthetic: two readings")
    assert second_review_problems(keys, flagged, first, second, today=TODAY, not_before=RUN) == []

    second[keys[0]] = _cell("present", "reviewer-a")
    second[keys[1]] = _cell("present", "reviewer-b", pinpoint="")
    second[keys[6]] = _cell("missing", "reviewer-b", when="2026-07-05")
    second[("SYN-009", "SYNTHETIC_RULE_01")] = _cell("present", "reviewer-b")
    assert second_review_problems(keys, flagged, first, second, today=TODAY, not_before=RUN) == [
        "SYN-009 SYNTHETIC_RULE_01: not a cell of the findings",
        "SYN-001 SYNTHETIC_RULE_01: reviewer_id 'reviewer-a' also made the first review of this cell",
        "SYN-001 SYNTHETIC_RULE_02: 'present' needs a source_pinpoint",
        "SYN-002 SYNTHETIC_RULE_02: reviewed_at 2026-07-05 is earlier than the detector run (2026-07-06)",
    ]


def _disputed():
    """Two cells reviewed twice; the second differs from the first, on purpose, on one of them."""
    keys = _keys(1, 2)
    cells = [
        {
            "study_doc_id": doc,
            "document_hash_sha256": "0" * 64,
            "rule_id": rule,
            "annex_item": "Synthetic item",
            "detector_status": "flagged",
            "detector_context": "synthetic context",
        }
        for doc, rule in keys
    ]
    first = {keys[0]: _cell("missing", note="synthetic: searched sections 1 to 3"), keys[1]: _cell("present")}
    second = {
        keys[0]: _cell("present", "reviewer-b", "2026-10-20", "synthetic section 2"),
        keys[1]: _cell("present", "reviewer-b", "2026-10-21"),
    }
    return keys, cells, first, second


def test_disagreements_list_both_reviews_and_no_detector_field():
    _, cells, first, second = _disputed()

    rows = disagreement_rows(cells, first, second)

    assert len(rows) == 1
    assert tuple(rows[0]) == DISAGREEMENT_FIELDS
    assert rows[0]["study_doc_id"] == "SYN-001" and rows[0]["rule_id"] == "SYNTHETIC_RULE_01"
    assert (rows[0]["first_label"], rows[0]["second_label"]) == ("missing", "present")
    assert rows[0]["first_note"] == "synthetic: searched sections 1 to 3"
    assert rows[0]["second_pinpoint"] == "synthetic section 2"
    assert rows[0]["final_label"] == "pending" and rows[0]["adjudication_reason"] == ""
    assert not any(field.startswith("detector") for field in DISAGREEMENT_FIELDS)
    assert latest_review_date(first, second) == date(2026, 10, 21)


def _decided(row, by="reviewer-a+reviewer-b", when="2026-10-25", label="present", pinpoint="synthetic p. 2"):
    return {
        **row,
        "final_label": label,
        "adjudicated_by": by,
        "adjudicated_at": when,
        "final_pinpoint": pinpoint,
        "adjudication_reason": "synthetic reason",
    }


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"final_label": "pending"}, "1 of 1 disagreements are still pending"),
        ({"final_label": "Present"}, "unsupported final_label 'Present'"),
        ({"adjudicated_by": "reviewer-a"}, "names only one of the two reviewers of this cell"),
        ({"adjudicated_by": "reviewer-b"}, "names only one of the two reviewers of this cell"),
        ({"adjudicated_by": "reviewer-a+"}, "join two reviewer identifiers with '+'"),
        ({"adjudicated_by": ""}, "adjudicated_by is empty"),
        (
            {"adjudicated_at": "2026-10-20"},
            "earlier than the latest review date in the two sheets (2026-10-21)",
        ),
        ({"adjudicated_at": "2026-10-31"}, "adjudicated_at 2026-10-31 is later than today (2026-10-30)"),
        ({"adjudicated_at": "25.10.2026"}, "adjudicated_at is not a date in the form YYYY-MM-DD"),
        ({"adjudication_reason": " "}, "adjudication_reason is empty"),
        ({"final_pinpoint": ""}, "'present' needs a final_pinpoint"),
        ({"second_label": "missing"}, "second_label differ from the two reviews; run --disagreements again"),
    ],
)
def test_adjudication_refuses_an_incomplete_or_stale_decision(change, message):
    _, cells, first, second = _disputed()
    expected = disagreement_rows(cells, first, second)

    with pytest.raises(ValueError, match="the adjudication file is not complete") as refused:
        adjudicated_cells(
            expected,
            DISAGREEMENT_FIELDS,
            [{**_decided(expected[0]), **change}],
            today=TODAY,
            not_before=latest_review_date(first, second),
        )
    assert message in str(refused.value)


def test_adjudication_refuses_a_file_that_does_not_match_the_disagreements():
    _, cells, first, second = _disputed()
    expected = disagreement_rows(cells, first, second)
    decided = _decided(expected[0])

    with pytest.raises(ValueError, match="does not have the columns"):
        adjudicated_cells(expected, [*DISAGREEMENT_FIELDS[:-1]], [decided], today=TODAY)
    with pytest.raises(ValueError, match="has 0 rows, but the two reviews now differ in 1 cells"):
        adjudicated_cells(expected, DISAGREEMENT_FIELDS, [], today=TODAY)
    assert adjudicated_cells([], DISAGREEMENT_FIELDS, [], today=TODAY) == {}


@pytest.mark.parametrize("by", ["reviewer-a+reviewer-b", "reviewer-b + reviewer-a", "reviewer-c"])
def test_adjudication_by_consensus_or_a_third_person_gives_the_final_cell(by):
    keys, cells, first, second = _disputed()
    expected = disagreement_rows(cells, first, second)

    final = adjudicated_cells(
        expected,
        DISAGREEMENT_FIELDS,
        [_decided(expected[0], by=by)],
        today=TODAY,
        not_before=date(2026, 10, 21),
    )

    assert final == {
        keys[0]: {
            "human_label": "present",
            "reviewer_id": by.replace(" ", ""),
            "reviewed_at": "2026-10-25",
            "source_pinpoint": "synthetic p. 2",
            "review_note": "Adjudicated (first: missing, second: present): synthetic reason",
        }
    }


def test_a_missing_label_needs_no_final_pinpoint_as_on_main():
    keys, cells, first, second = _disputed()
    expected = disagreement_rows(cells, first, second)

    final = adjudicated_cells(
        expected, DISAGREEMENT_FIELDS, [_decided(expected[0], label="missing", pinpoint="")], today=TODAY
    )
    assert final[keys[0]]["human_label"] == "missing"


def test_carrying_adjudications_keeps_decisions_and_refuses_stale_ones():
    _, cells, first, second = _disputed()
    expected = disagreement_rows(cells, first, second)
    decided = _decided(expected[0])

    assert carry_adjudications(expected, [decided]) == [decided]
    assert carry_adjudications(expected, [expected[0]]) == expected
    with pytest.raises(
        ValueError,
        match="SYN-001 SYNTHETIC_RULE_01: adjudicated, but these columns no longer match the two "
        "sheets: second_note; restore them",
    ):
        carry_adjudications(expected, [{**decided, "second_note": "synthetic later edit"}])
    with pytest.raises(ValueError, match="more than one adjudicated row"):
        carry_adjudications(expected, [decided, decided])
    with pytest.raises(ValueError, match="no longer list it as a disagreement"):
        carry_adjudications([], [decided])


def test_a_decided_row_a_spreadsheet_rewrote_names_the_column_to_restore():
    # The merge sends a changed review column back to --disagreements, which must then say which
    # column to restore instead of repeating the advice.
    _, cells, first, second = _disputed()
    expected = disagreement_rows(cells, first, second)
    saved = {**_decided(expected[0]), "first_reviewed_at": "14.10.2026"}

    with pytest.raises(ValueError, match="run --disagreements again"):
        adjudicated_cells(expected, DISAGREEMENT_FIELDS, [saved], today=TODAY)
    with pytest.raises(ValueError) as refused:
        carry_adjudications(expected, [saved])
    assert "these columns no longer match the two sheets: first_reviewed_at; restore them" in str(
        refused.value
    )
    assert carry_adjudications(expected, [{**saved, "first_reviewed_at": "2026-10-14"}]) == [
        _decided(expected[0])
    ]


def _label_table(text, start, end):
    section = text.split(start, 1)[1].split(end, 1)[0]
    return {line.split("|")[1].strip().strip("`") for line in section.splitlines() if line.startswith("| `")}


def test_label_vocabulary_matches_the_codebook_and_the_protocol():
    codebook = (STUDY / "codebook.md").read_text(encoding="utf-8")
    protocol = (STUDY / "review-protocol.md").read_text(encoding="utf-8")

    assert _label_table(codebook, "## 3. Labels", "**Order of decisions") == ALLOWED_LABELS
    assert _label_table(protocol, "## Labels", "## First review") == ALLOWED_LABELS


# The command line, on a synthetic study of three documents and four rules, two cells flagged.
def _findings():
    flagged = {("SYN-001", "SYNTHETIC_RULE_02"), ("SYN-003", "SYNTHETIC_RULE_04")}
    keys = _keys(3, 4)
    return (
        {
            "generated_at": "2026-07-06T07:00:00+00:00",
            "rules": [
                {"rule_id": f"SYNTHETIC_RULE_{rule:02d}", "annex_item": f"Synthetic item {rule}"}
                for rule in range(1, 5)
            ],
            "results": [
                {
                    "study_doc_id": doc,
                    "document_hash_sha256": str(number) * 64,
                    "findings": [
                        {
                            "rule_id": rule,
                            "confidence": "high",
                            "evidence": {"matched_text": "synthetic context"},
                        }
                        for key_doc, rule in keys
                        if key_doc == doc and (key_doc, rule) in flagged
                    ],
                }
                for number, doc in enumerate(("SYN-001", "SYN-002", "SYN-003"), start=1)
            ],
        },
        keys,
        flagged,
    )


def _builder():
    return runpy.run_path(str(STUDY / "scripts" / "build_review_matrix.py"))


def _study(tmp_path):
    findings, keys, flagged = _findings()
    (tmp_path / "findings-pseudonymous.json").write_text(json.dumps(findings), encoding="utf-8")
    builder = _builder()
    assert builder["main"]([], study_dir=tmp_path) == 0
    return builder, keys, flagged


def _read(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _save(path, cells):
    """Fill cells into a sheet as a spreadsheet saves it: byte-order mark and CRLF line ends."""
    rows = _read(path)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), lineterminator="\r\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({**row, **cells.get((row["study_doc_id"], row["rule_id"]), {})})
    path.write_bytes(("\ufeff" + buffer.getvalue()).encode("utf-8"))


def _first_review(tmp_path, keys):
    labels = {key: _cell("present") for key in keys}
    labels[keys[0]] = _cell("uncertain", pinpoint="", note="synthetic: two readings")
    labels[keys[1]] = _cell("missing", note="synthetic: searched sections 1 to 3")
    _save(tmp_path / "human-review-blinded.csv", labels)
    return labels


def _run(builder, tmp_path, *args):
    return builder["main"](list(args), study_dir=tmp_path, today=TODAY)


def _files(tmp_path):
    return {path.name: path.read_bytes() for path in sorted(tmp_path.glob("human-review-*.csv"))}


def test_second_sheet_waits_for_the_first_review_and_hides_the_detector(tmp_path, capsys):
    builder, keys, flagged = _study(tmp_path)

    assert _run(builder, tmp_path, "--second-sheet") == 1
    assert "--second-sheet stopped: 12 of 12 blinded cells are still pending" in capsys.readouterr().err
    assert not (tmp_path / "human-review-second.csv").exists()

    first = _first_review(tmp_path, keys)
    before = _files(tmp_path)
    assert _run(builder, tmp_path, "--second-sheet") == 0

    expected = second_review_selection(
        keys, flagged, {key: cell["human_label"] for key, cell in first.items()}, seed=20261014
    )
    rows = _read(tmp_path / "human-review-second.csv")
    assert [(row["study_doc_id"], row["rule_id"]) for row in rows] == expected
    assert list(rows[0]) == ["study_doc_id", "document_hash_sha256", "rule_id", "annex_item", *first[keys[0]]]
    assert {row["human_label"] for row in rows} == {"pending"}
    out = capsys.readouterr().out
    assert f"with {len(expected)} of 12 cells: the 2 flagged cells, 2 of the 10 non-flagged cells" in out
    assert "seed 20261014 and fraction 0.2" in out
    after = _files(tmp_path)
    assert {name: after[name] for name in before} == before

    sheet = (tmp_path / "human-review-second.csv").read_bytes()
    assert _run(builder, tmp_path, "--second-sheet") == 0
    assert (tmp_path / "human-review-second.csv").read_bytes() == sheet

    _save(tmp_path / "human-review-second.csv", {expected[0]: _cell("present", "reviewer-b")})
    assert _run(builder, tmp_path, "--second-sheet", "--second-all") == 1
    assert "already holds review cells; nothing written" in capsys.readouterr().err

    (tmp_path / "human-review-second.csv").unlink()
    assert _run(builder, tmp_path, "--second-sheet", "--second-all") == 0
    assert len(_read(tmp_path / "human-review-second.csv")) == 12


@pytest.mark.parametrize(
    "args",
    [
        ["--seed", "1"],
        ["--second-all"],
        ["--second-sheet", "--second-all", "--seed", "1"],
        ["--second-sheet", "--fraction", "0.1"],
    ],
)
def test_second_sheet_options_need_the_second_sheet(tmp_path, args):
    builder = _study(tmp_path)[0]
    with pytest.raises(SystemExit) as exited:
        _run(builder, tmp_path, *args)
    assert exited.value.code == 2


def _second_review(tmp_path, first, disputed):
    """The second reviewer agrees with the first everywhere except on the `disputed` cells."""
    cells = {}
    for row in _read(tmp_path / "human-review-second.csv"):
        key = (row["study_doc_id"], row["rule_id"])
        label = first[key]["human_label"]
        if key in disputed:
            label = "present" if label != "present" else "missing"
        cells[key] = _cell(
            label, "reviewer-b", "2026-10-21", note="synthetic note" if label != "present" else ""
        )
    _save(tmp_path / "human-review-second.csv", cells)


def test_merge_with_a_second_review_takes_the_adjudicated_labels(tmp_path, capsys):
    builder, keys, flagged = _study(tmp_path)
    first = _first_review(tmp_path, keys)
    assert _run(builder, tmp_path, "--second-sheet") == 0

    before = _files(tmp_path)
    assert _run(builder, tmp_path, "--merge-blinded") == 1
    assert "merge stopped: fix these in human-review-second.csv first" in capsys.readouterr().err
    assert _run(builder, tmp_path, "--disagreements") == 1
    assert "second-review cells are still pending" in capsys.readouterr().err
    assert _files(tmp_path) == before

    disputed = [keys[1], ("SYN-003", "SYNTHETIC_RULE_04")]
    assert set(disputed) == flagged
    _second_review(tmp_path, first, disputed)
    before = _files(tmp_path)
    assert _run(builder, tmp_path, "--merge-blinded") == 1
    assert "the two reviews differ in 2 cells; write human-review-adjudication.csv" in capsys.readouterr().err
    assert _files(tmp_path) == before

    assert _run(builder, tmp_path, "--disagreements") == 0
    assert "differ in 2 of" in capsys.readouterr().out
    adjudication = _read(tmp_path / "human-review-adjudication.csv")
    assert [(row["study_doc_id"], row["rule_id"]) for row in adjudication] == [
        key for key in keys if key in disputed
    ]
    assert tuple(adjudication[0]) == DISAGREEMENT_FIELDS
    assert {row["final_label"] for row in adjudication} == {"pending"}

    before = _files(tmp_path)
    assert _run(builder, tmp_path, "--merge-blinded") == 1
    assert "2 of 2 disagreements are still pending" in capsys.readouterr().err
    assert _files(tmp_path) == before

    def adjudicate(by):
        _save(
            tmp_path / "human-review-adjudication.csv",
            {
                (row["study_doc_id"], row["rule_id"]): _decided(row, by=by)
                for row in _read(tmp_path / "human-review-adjudication.csv")
            },
        )

    adjudicate("reviewer-a")
    before = _files(tmp_path)
    assert _run(builder, tmp_path, "--merge-blinded") == 1
    assert "names only one of the two reviewers of this cell" in capsys.readouterr().err
    assert _files(tmp_path) == before

    adjudicate("reviewer-a+reviewer-b")
    assert _run(builder, tmp_path, "--merge-blinded") == 0
    assert "2 of them as adjudicated" in capsys.readouterr().out
    matrix = {
        (row["study_doc_id"], row["rule_id"]): row for row in _read(tmp_path / "human-review-matrix.csv")
    }
    for key, row in matrix.items():
        if key in disputed:
            assert row["human_label"] == "present"
            assert (row["reviewer_id"], row["reviewed_at"]) == ("reviewer-a+reviewer-b", "2026-10-25")
            assert row["review_note"] == (
                f"Adjudicated (first: {first[key]['human_label']}, second: "
                f"{'present' if first[key]['human_label'] != 'present' else 'missing'}): synthetic reason"
            )
        else:
            assert {name: row[name] for name in first[key]} == first[key]
    assert summarize_rows(matrix.values(), today=TODAY, not_before=RUN)["publication_ready"] is True
    # The blinded sheet keeps the first review; only the matrix holds the adjudicated labels.
    assert {
        (row["study_doc_id"], row["rule_id"]): row["human_label"]
        for row in _read(tmp_path / "human-review-blinded.csv")
    } == {key: cell["human_label"] for key, cell in first.items()}

    # A further --disagreements run keeps the decisions; it only rewrites the spreadsheet save.
    assert _run(builder, tmp_path, "--disagreements") == 0
    assert "2 already adjudicated" in capsys.readouterr().out
    merged = _files(tmp_path)
    assert _run(builder, tmp_path, "--merge-blinded") == 0
    assert _run(builder, tmp_path, "--disagreements") == 0
    assert _run(builder, tmp_path) == 0
    assert _files(tmp_path) == merged

    _second_review(tmp_path, first, disputed[:1])
    edited = _files(tmp_path)
    assert _run(builder, tmp_path, "--disagreements") == 1
    assert "adjudicated, but the two sheets no longer list it as a disagreement" in capsys.readouterr().err
    assert _files(tmp_path) == edited


def test_agreeing_reviews_merge_without_an_adjudication_file(tmp_path):
    builder, keys, _flagged = _study(tmp_path)
    first = _first_review(tmp_path, keys)
    assert _run(builder, tmp_path, "--second-sheet") == 0
    _second_review(tmp_path, first, [])

    assert _run(builder, tmp_path, "--merge-blinded") == 0
    assert not (tmp_path / "human-review-adjudication.csv").exists()
    assert {row["reviewer_id"] for row in _read(tmp_path / "human-review-matrix.csv")} == {"reviewer-a"}


def test_plain_rebuild_stops_on_a_second_review_cell_without_a_current_key(tmp_path, capsys):
    builder, keys, _flagged = _study(tmp_path)
    _first_review(tmp_path, keys)
    assert _run(builder, tmp_path, "--second-sheet", "--second-all") == 0
    path = tmp_path / "human-review-second.csv"
    rows = _read(path)
    rows[-1].update(study_doc_id="SYN-009", **_cell("present", "reviewer-b", "2026-10-21"))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    before = _files(tmp_path)
    capsys.readouterr()

    assert _run(builder, tmp_path) == 1
    assert "filled reviewer cells have no current document-rule key" in capsys.readouterr().err
    assert _files(tmp_path) == before


@pytest.mark.parametrize("flag", ["--second-sheet", "--disagreements"])
def test_second_review_steps_explain_a_run_without_the_package(tmp_path, capsys, monkeypatch, flag):
    builder, keys, _flagged = _study(tmp_path)
    _first_review(tmp_path, keys)
    before = _files(tmp_path)
    capsys.readouterr()
    monkeypatch.setitem(sys.modules, "micar_linter", None)
    monkeypatch.setitem(sys.modules, "micar_linter.review_validation", None)

    assert _run(builder, tmp_path, flag) == 1

    assert _files(tmp_path) == before
    err = capsys.readouterr().err
    assert f"{flag} stopped: it needs the micar_linter package" in err
    assert f"build_review_matrix.py {flag}`" in err
