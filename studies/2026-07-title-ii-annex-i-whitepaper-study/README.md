# MiCAR White Paper Study 2026: Annex I Disclosure Patterns in Notified Title II White Papers

This directory contains a reproducible pilot over public Title II crypto-asset white papers listed in ESMA's MiCAR register.

The study is deliberately narrow. It covers crypto-assets other than asset-referenced tokens and e-money tokens and applies 15 deterministic Article 6 and Annex I controls. A detector flag means only that the specified element was not found in extracted text. It is not a reviewed legal finding and does not establish non-compliance.

Raw white papers are not committed. Downloaded source files belong under `.study-cache/title-ii-whitepapers/`.

## Current status

- Documents processed: 10.
- Document-rule cells: 150.
- Machine-flagged candidate gaps: 21.
- Human-review status: `pending_review`.
- Pre-registration: not yet made. `codebook.md` and `analysis-plan.md` are unsigned drafts; their signing order says how they are adopted on `main`. Once they are, this line records the adoption commit's SHA and its tag.
- Prevalence, precision, recall, and issuer-compliance conclusions: not yet supportable.

## Files

- `source-manifest.json`: public source metadata, issuer mapping, register-row hashes, inclusion status, and document-hash references.
- `sample-manifest.csv`: compact view of the committed v1 convenience sample.
- `document-provenance.json`: exact source-byte hashes and extraction metadata for processed documents.
- `findings-pseudonymous.json`: machine-generated candidate flags keyed by WP identifier.
- `findings-pseudonymous.csv`: flat candidate-flag table.
- `human-review-r1.csv`: blinded sheet for reviewer `r1`. It omits detector outcomes, adds the rule label and requirement for each cell, and shuffles rows within each document by a recorded seed. A second reviewer gets `human-review-r2.csv`.
- `human-review-matrix.csv`: all 150 document-rule cells with detector status, for adjudication and metric calculation after the independent labels are recorded. Reviewers do not open it while labelling.
- `human-review-sheets.json`: generation record for the sheets and the matrix: findings hash, rule source, seed, row-order policy and file hashes.
- `human-review-adjudication.csv`: only with a second reviewer. For every cell on which the reviewers disagree, the final label, who adjudicated, the date and the reasoning.
- `human-review-summary.json`: current completion and validation metrics; it remains publication-blocking while rows are pending.
- `review-protocol.md`: label definitions, review procedure, adjudication, and publication gate.
- `codebook.md`: DRAFT, not adopted. Per-rule decision rules and open codebook policies for the reviewer.
- `analysis-plan.md`: DRAFT, not adopted. Metrics, exclusions, intervals, reporting rules and the detector freeze, to be pre-registered in one adoption commit on `main`.
- `findings-summary.md`: rendered pilot report.
- `methodology.md`: source, sampling, extraction, rule, and metric methodology.
- `limitations.md`: limitations and prohibited inferences.

WP identifiers are pseudonymous labels. They are not anonymisation: `source-manifest.json` maps each identifier to a public issuer and white-paper URL.

## Reproduce the detector output

Write to a scratch folder and compare with the committed files, which a re-run must not overwrite by accident. The committed findings are the machine output of the run on 2026-07-06, and the summary is rendered from them. A re-run always differs in `generated_at`, `digest`, `language_policy`, `source_manifest.register_source_detail` and each finding's `human_review_note`, because that wording and the curated manifest have changed since; its summary differs in the "Source manifest" and "Findings digest" lines with them. Its flags and their `confidence`, the evidence's `matched_text` and each document's `extraction_metadata` may differ too, because the document loaders have changed since (`page_or_section` is the rule's fixed section hint).

```bash
mkdir -p /tmp/micar-study

uv run micar-lint-batch \
  --manifest studies/2026-07-title-ii-annex-i-whitepaper-study/source-manifest.json \
  --cache .study-cache/title-ii-whitepapers \
  --annex annex-i \
  --out /tmp/micar-study/findings-pseudonymous.json

uv run micar-study-report \
  --findings /tmp/micar-study/findings-pseudonymous.json \
  --out /tmp/micar-study/findings-summary.md
```

`micar-lint-batch` needs the source files under `.study-cache/title-ii-whitepapers/`. Without them it excludes every document as `cached_document_not_found` and still exits 0. If only some are missing, it excludes each missing one and tries the candidate entries `WP-013` to `WP-020` in order in its place, excluding each candidate that is not cached either, so it can process other documents, or fewer than 10. A cached document that fails to load or to extract text is replaced the same way, so even a full cache does not guarantee the same documents. Before comparing, check that the run processed the same documents as the committed file: 10 documents processed, the same `study_doc_id` values and the same `document_hash_sha256` values (recorded as `document_sha256` in `document-provenance.json`). A white paper downloaded again with different bytes can change the flags on its own.

`source-manifest.json` and `document-provenance.json` are curated and are not regenerated. `python -m micar_linter.esma_register` cannot reproduce the manifest: it drops entries and provenance fields. To inspect its normalisation, write to the scratch folder:

```bash
uv run python -m micar_linter.esma_register \
  --csv studies/2026-07-title-ii-annex-i-whitepaper-study/sample-manifest.csv \
  --out /tmp/micar-study/source-manifest.json
```

The scripts in `scripts/` write to the committed files: `run_batch.py` to the findings, `render_report.py` to `findings-summary.md`, and `fetch_esma_register.py` (from the live ESMA register) and `select_sample.py` to `source-manifest.json` and `sample-manifest.csv`. Do not run `fetch_esma_register.py` or `select_sample.py`: they replace the curated manifest. Run `run_batch.py` only with the full cache in place, and `render_report.py` only to refresh the summary on purpose. A refresh can put committed files out of step. `micar-review-sheets` rebuilds the review sheets and the matrix from the findings (see "Prepare the human review"); no script rebuilds the other files. One that changes the flags, or a flag's `confidence` or `matched_text`, affects the detector columns of `human-review-matrix.csv` (`detector_status`, `detector_confidence`, `detector_context`); one that changes the flags also affects the candidate-gap figures in `docs/overview.md` and this README. One that changes the number of documents processed affects the document and cell counts in this README ("Current status", the file list and the "10 documents processed" check above), `docs/overview.md`, `docs/playground/index.html`, `docs/DETAILS.md`, `methodology.md` and `limitations.md`, the number of rows in `human-review-r1.csv` and `human-review-matrix.csv` (and so `rows_total` in `human-review-summary.json`), and the 150 cells that `study_report.py` writes into `findings-summary.md` as fixed text. One that changes the documents processed, or their bytes, affects the sample description in `methodology.md` and `limitations.md`, the inclusion, `detected_format` and `document_hash_sha256` fields of `source-manifest.json`, the rows of `sample-manifest.csv` (it lists only the included entries), the `study_doc_id` and `document_hash_sha256` columns of `human-review-r1.csv` and `human-review-matrix.csv`, and the `documents` and `excluded_documents` entries of `document-provenance.json`. One that changes a document's extraction affects its `extraction_metadata` in `document-provenance.json`.

## Prepare the human review

Check that the cached source bytes are the bytes the detector processed. The check runs offline and exits non-zero if any document is missing (3) or differs (1):

```bash
uv run micar-study-verify-cache \
  --provenance studies/2026-07-title-ii-annex-i-whitepaper-study/document-provenance.json \
  --cache .study-cache/title-ii-whitepapers \
  --include-candidates
```

Regenerate the blinded sheets and the matrix from the findings file. Rule IDs and Annex labels come from `STUDY_RULES`; every new sheet has every label `pending`. Reviewers and the seed recorded in `human-review-sheets.json` are always kept, so pass `--reviewer r2` to add a second reviewer. A sheet that already holds review content is kept unchanged; if its cells or row order would change, the command refuses (exit 3). `--check` confirms that the committed files match the generator, comparing every column except the review fields, so it still passes once labels are entered:

```bash
uv run micar-review-sheets \
  --findings studies/2026-07-title-ii-annex-i-whitepaper-study/findings-pseudonymous.json \
  --out-dir studies/2026-07-title-ii-annex-i-whitepaper-study
```

## Label the cells

Each reviewer labels only their own blinded sheet (`human-review-r1.csv`, and `human-review-r2.csv` for a second reviewer) under `review-protocol.md` and `codebook.md`. While labelling, reviewers do not open `human-review-matrix.csv`, `findings-pseudonymous.*` or `findings-summary.md`.

Start labelling the 150 cells only after the adoption commit on `main` that adopts `codebook.md` and `analysis-plan.md` with the pending sheets (`analysis-plan.md`, step 0.10). It follows the signing order in their banners: the study tooling (#18, #19 and #24) is merged into `main` as unsigned draft tooling first, and Phase 0 is done on `main`. The calibration document is labelled before that commit, in Phase 0 (step 0.9), outside the committed sheets (`analysis-plan.md` section 4). From the adoption commit on, pass the adoption date recorded in `codebook.md` as `--not-before YYYY-MM-DD` to `micar-review-workbook` and to every `micar-review-merge` command below, so that a label dated before the pre-registration is refused. Without it, the earliest accepted date is the day the findings were generated (2026-07-06).

A reviewer can enter labels in the CSV directly, or in a workbook generated from it. The workbook commands need the optional `review` extra (openpyxl):

```bash
uv run --extra review micar-review-workbook \
  --study-dir studies/2026-07-title-ii-annex-i-whitepaper-study \
  --reviewer r1
```

This writes `human-review-r1.xlsx` into the study directory (`--out` writes it elsewhere). Workbook row N holds the CSV's record N, in the sheet's recorded order (row 1 is the header in both). The workbook carries no detector outcome, and it never fills a label: values come from the reviewer's own CSV, so a new sheet gives a workbook with every label pending. Only the review columns can be edited:

- `human_label`: dropdown of the labels of `review-protocol.md` (refined in `codebook.md`, section 3). Typed labels must be lower case, exactly as listed;
- `reviewer_id`: only the reviewer's own ID;
- `reviewed_at`: only a date;
- `source_pinpoint` and `review_note`: free text.

The other columns and the row order are locked. The sheet protection has no password: it prevents accidental edits only, so the import re-checks everything. Git ignores `*.xlsx` under `studies/`; do not commit the workbook. The command refuses to overwrite an existing workbook (exit 5) unless `--force` is given.

Check progress at any time without writing anything (exit 1 while any cell is pending or invalid):

```bash
uv run --extra review micar-review-merge check \
  --study-dir studies/2026-07-title-ii-annex-i-whitepaper-study \
  --reviewer r1 \
  --workbook studies/2026-07-title-ii-annex-i-whitepaper-study/human-review-r1.xlsx
```

Without `--workbook`, the check reads the CSV sheet. When every cell is labelled, import the workbook into the CSV sheet:

```bash
uv run --extra review micar-review-merge import \
  --study-dir studies/2026-07-title-ii-annex-i-whitepaper-study \
  --reviewer r1 \
  --workbook studies/2026-07-title-ii-annex-i-whitepaper-study/human-review-r1.xlsx
```

A reviewer who started in the CSV can generate the workbook from it and continue there. The workbook records which CSV it was generated from, so the import replaces that CSV's values without `--replace`. If the CSV already holds review content and changed after the workbook was generated, the import refuses, because it would discard those changes.

The import validates every row:

- the label is one of the labels of `review-protocol.md` (refined in `codebook.md`, section 3);
- `reviewer_id` is the sheet's reviewer;
- `reviewed_at` is an ISO 8601 date (`YYYY-MM-DD`), not before the findings were generated (or the `--not-before` date) and not after today;
- `present` and `missing` carry a `source_pinpoint`;
- `not_applicable`, `uncertain` and `extraction_failure` carry a `review_note`.

It writes nothing and lists the offending rows when it refuses:

- exit 1: a cell is pending or invalid;
- exit 2: a usage or input error, for example openpyxl is not installed or `--not-before` is before the findings date;
- exit 3: the workbook's cells or row order differ from the generated sheet, the workbook was generated for another reviewer or sheet, or the findings file or the sheets no longer match `human-review-sheets.json`;
- exit 5: the CSV already holds different labels and changed after the workbook was generated. `--replace` overwrites them.

Commit each reviewer's labelled sheet on its own, before the merge. This repository is public. Do not push labelled sheets, the adjudication file or the merged matrix until `analysis-plan.md` section 11 is decided and the conflicts check and the legal review under `review-protocol.md` (Publication gate, item 6) are done.

## Validate against human labels

Only after every reviewer's labels are committed are the final labels merged into `human-review-matrix.csv` with the detector outcomes:

```bash
uv run micar-review-merge matrix \
  --study-dir studies/2026-07-title-ii-annex-i-whitepaper-study
```

The merge validates the sheet of every reviewer recorded in `human-review-sheets.json` in the same way, and refuses (exit 1) while any is pending or invalid. It then writes the final labels into the matrix, rewrites `human-review-summary.json` with `micar-review-summary --require-complete`, and checks that the summary, the sheets and the generation record agree. It does not need openpyxl. It refuses (exit 5) to replace different labels already in the matrix unless `--replace` is given. It does not touch `docs/playground/index.html`: after the merge, update the reviewed count (`basis-reviewed`) there, which `tests/playground/model.test.mjs` checks against `rows_completed`.

With a second reviewer, the merge first compares the sheets. Cells with the same label from both reviewers take that label, with `reviewer_id` `r1+r2`. If any labels differ, the merge writes those cells to `human-review-disagreements.csv` (git-ignored; reviewer columns, no detector outcome) and exits 4 without writing the matrix. Then:

1. Copy the report to `human-review-adjudication.csv`. Edit it in a text editor, or in LibreOffice with a comma separator and the columns imported as text; a spreadsheet that saves semicolons or reformats dates makes the merge refuse the file.
2. For every row, fill `final_label`, `adjudicated_by`, `adjudicated_at`, `adjudication_reason`, and `final_pinpoint` where the final label is `present` or `missing`. `adjudicated_by` is both reviewers by consensus (`r1+r2`) or a third person (for example `r3`); one of the two reviewers alone is refused. These are the two routes of the draft `analysis-plan.md`, section 6, which is not yet adopted.
3. Run the merge again with `--adjudication studies/2026-07-title-ii-annex-i-whitepaper-study/human-review-adjudication.csv`.
4. Commit the adjudication file with the merged matrix. This repository is public. Do not push labelled sheets, the adjudication file or the merged matrix until `analysis-plan.md` section 11 is decided and the conflicts check and the legal review under `review-protocol.md` (Publication gate, item 6) are done.

The adjudication file is refused (exit 4) while a row is pending or invalid, or when it is stale because a sheet changed after the report was copied.

The merge needs every recorded reviewer's sheet to be complete. It does not yet support a second review of only the minimum subset in `review-protocol.md`.

To recompute the summary from the matrix alone:

```bash
uv run micar-review-summary \
  --matrix studies/2026-07-title-ii-annex-i-whitepaper-study/human-review-matrix.csv \
  --out /tmp/micar-study/human-review-summary.json \
  --require-complete
```

Copy the output over `human-review-summary.json` only once the command exits 0. Then update the reviewed count (`basis-reviewed`) in `docs/playground/index.html`, which `tests/playground/model.test.mjs` checks against `rows_completed`.

The command writes its output before it checks completeness, so pointed at the committed `human-review-summary.json` it would overwrite it even while rows are pending; it then exits with status 2. Metrics exclude uncertain, extraction-failure, and not-applicable labels.

The committed detector outputs are deterministic research artifacts. They are not legal advice.
