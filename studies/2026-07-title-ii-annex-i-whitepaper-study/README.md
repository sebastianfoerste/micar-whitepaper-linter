# MiCAR White Paper Study 2026: Annex I Disclosure Patterns in Notified Title II White Papers

This directory contains a reproducible pilot over public Title II crypto-asset white papers listed in ESMA's MiCAR register.

The study is deliberately narrow. It covers crypto-assets other than asset-referenced tokens and e-money tokens and applies 15 deterministic Article 6 and Annex I controls. A detector flag means only that the specified element was not found in extracted text. It is not a reviewed legal finding and does not establish non-compliance.

Raw white papers are not committed. Downloaded source files belong under `.study-cache/title-ii-whitepapers/`.

## Current status

- Documents processed: 10.
- Document-rule cells: 150.
- Machine-flagged candidate gaps: 21.
- Human-review status: `pending_review`.
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
- `analysis-plan.md`: DRAFT, not adopted. Pre-registered metrics, exclusions, intervals and reporting rules.
- `findings-summary.md`: rendered pilot report.
- `methodology.md`: source, sampling, extraction, rule, and metric methodology.
- `limitations.md`: limitations and prohibited inferences.

WP identifiers are pseudonymous labels. They are not anonymisation: `source-manifest.json` maps each identifier to a public issuer and white-paper URL.

## Reproduce the detector output

```bash
uv run python -m micar_linter.esma_register \
  --csv studies/2026-07-title-ii-annex-i-whitepaper-study/sample-manifest.csv \
  --out studies/2026-07-title-ii-annex-i-whitepaper-study/source-manifest.json

uv run micar-lint-batch \
  --manifest studies/2026-07-title-ii-annex-i-whitepaper-study/source-manifest.json \
  --cache .study-cache/title-ii-whitepapers \
  --annex annex-i \
  --out studies/2026-07-title-ii-annex-i-whitepaper-study/findings-pseudonymous.json

uv run micar-study-report \
  --findings studies/2026-07-title-ii-annex-i-whitepaper-study/findings-pseudonymous.json \
  --out studies/2026-07-title-ii-annex-i-whitepaper-study/findings-summary.md
```

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

A reviewer can enter labels in the CSV directly, or in a workbook generated from it. The workbook commands need the optional `review` extra (openpyxl):

```bash
uv run --extra review micar-review-workbook \
  --study-dir studies/2026-07-title-ii-annex-i-whitepaper-study \
  --reviewer r1
```

This writes `human-review-r1.xlsx` into the study directory (`--out` writes it elsewhere). Workbook row N is line N of the CSV, in the sheet's recorded order. The workbook carries no detector outcome, and it never fills a label: values come from the reviewer's own CSV, so a new sheet gives a workbook with every label pending. Only the review columns can be edited:

- `human_label`: dropdown of the codebook's labels;
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

The import validates every row:

- the label is one of the codebook's labels;
- `reviewer_id` is the sheet's reviewer;
- `reviewed_at` is an ISO 8601 date (`YYYY-MM-DD`), not before the findings were generated and not after today;
- `present` and `missing` carry a `source_pinpoint`;
- `not_applicable`, `uncertain` and `extraction_failure` carry a `review_note`.

It writes nothing and lists the offending rows when it refuses:

- exit 1: a cell is pending or invalid;
- exit 3: the workbook's cells or row order differ from the generated sheet, or the findings file or the sheets no longer match `human-review-sheets.json`;
- exit 5: the CSV already holds different labels. `--replace` overwrites them.

Commit each reviewer's labelled sheet on its own, before the merge.

## Validate against human labels

Only after every reviewer's labels are committed are the final labels merged into `human-review-matrix.csv` with the detector outcomes:

```bash
uv run micar-review-merge matrix \
  --study-dir studies/2026-07-title-ii-annex-i-whitepaper-study
```

The merge validates the sheet of every reviewer recorded in `human-review-sheets.json` in the same way, and refuses (exit 1) while any is pending or invalid. It then writes the final labels into the matrix, rewrites `human-review-summary.json` with `micar-review-summary --require-complete`, and checks that the summary, the sheets and the generation record agree. It does not need openpyxl. It refuses (exit 5) to replace different labels already in the matrix unless `--replace` is given.

With a second reviewer, the merge first compares the sheets. Cells with the same label from both reviewers take that label, with `reviewer_id` `r1+r2`. If any labels differ, the merge writes those cells to `human-review-disagreements.csv` (git-ignored; reviewer columns, no detector outcome) and exits 4 without writing the matrix. Then:

1. Copy the report to `human-review-adjudication.csv`.
2. For every row, fill `final_label`, `adjudicated_by`, `adjudicated_at`, `adjudication_reason`, and `final_pinpoint` where the final label is `present` or `missing`. `adjudicated_by` is both reviewers by consensus (`r1+r2`) or a third person (for example `r3`). One of the two reviewers alone is refused (`analysis-plan.md`, section 6).
3. Run the merge again with `--adjudication studies/2026-07-title-ii-annex-i-whitepaper-study/human-review-adjudication.csv`.
4. Commit the adjudication file with the merged matrix.

The adjudication file is refused (exit 4) while a row is pending or invalid, or when it is stale because a sheet changed after the report was copied.

The merge needs every recorded reviewer's sheet to be complete. It does not yet support a second review of only the minimum subset in `review-protocol.md`.

To recompute the summary from the matrix alone:

```bash
uv run micar-review-summary \
  --matrix studies/2026-07-title-ii-annex-i-whitepaper-study/human-review-matrix.csv \
  --out studies/2026-07-title-ii-annex-i-whitepaper-study/human-review-summary.json \
  --require-complete
```

The command exits with status 2 while any row remains pending. Metrics exclude uncertain, extraction-failure, and not-applicable labels.

The committed detector outputs are deterministic research artifacts. They are not legal advice.
