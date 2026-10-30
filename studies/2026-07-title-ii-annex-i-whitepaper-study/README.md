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
- `human-review-blinded.csv`: detector-hidden sheet for independent first review.
- `human-review-matrix.csv`: all 150 document-rule cells with detector status for adjudication and metric calculation.
- `human-review-summary.json`: completion and validation metrics written by `micar-review-summary`; it remains publication-blocking while rows are pending. The committed copy predates the protocol-gap, review-disclosure and publication-scope fields of schema v2, which the command below adds when it regenerates the file.
- `review-protocol.md`: label definitions, review procedure, adjudication, and publication gate.
- `REVIEWING.md`: reviewer checklist with the reference-standard decision the owner must record before labelling, the commands in order, the disclosures for the report, and a time estimate.
- `codebook.md`: DRAFT, not adopted. Per-rule decision rules and open codebook policies for the reviewer; `review-protocol.md` and `REVIEWING.md` take precedence over it.
- `analysis-plan.md`: DRAFT, not adopted. Metrics, exclusions, intervals, reporting rules and the detector freeze, to be pre-registered in one adoption commit on `main`, as the signing order in its banner and the codebook's describes.
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

The scripts in `scripts/` write to the committed files: `run_batch.py` to the findings, `render_report.py` to `findings-summary.md`, and `fetch_esma_register.py` (from the live ESMA register) and `select_sample.py` to `source-manifest.json` and `sample-manifest.csv`. Do not run `fetch_esma_register.py` or `select_sample.py`: they replace the curated manifest. Run `run_batch.py` only with the full cache in place, and `render_report.py` only to refresh the summary on purpose. A refresh can put committed files out of step. `scripts/build_review_matrix.py` (below) rebuilds the two review sheets from the new findings, keeping filled reviewer cells; no script rebuilds the rest. One that changes the flags, or a flag's `confidence` or `matched_text`, affects the detector columns of `human-review-matrix.csv` (`detector_status`, `detector_confidence`, `detector_context`); one that changes the flags also affects the candidate-gap figures in `docs/overview.md` and this README. One that changes the number of documents processed affects the document and cell counts in this README ("Current status", the file list and the "10 documents processed" check above), `docs/overview.md`, `docs/playground/index.html`, `docs/DETAILS.md`, `methodology.md` and `limitations.md`, and the number of rows in `human-review-blinded.csv` and `human-review-matrix.csv` (and so `rows_total` in `human-review-summary.json`). One that changes the documents processed, or their bytes, affects the sample description in `methodology.md` and `limitations.md`, the inclusion, `detected_format` and `document_hash_sha256` fields of `source-manifest.json`, the rows of `sample-manifest.csv` (it lists only the included entries), the `study_doc_id` and `document_hash_sha256` columns of `human-review-blinded.csv` and `human-review-matrix.csv`, and the `documents` and `excluded_documents` entries of `document-provenance.json`. One that changes a document's extraction affects its `extraction_metadata` in `document-provenance.json`.

## Check the cached documents

`micar-study-verify-cache` checks offline that the cached source files are the bytes recorded in `document-provenance.json`, the same comparison as the `shasum` check in `REVIEWING.md` step 1. It finds each document in the cache as `micar-lint-batch` does, prints one line per document and exits 0 when every document matches, 1 when one differs and 3 when none differs but one is missing. For a document that differs or is missing, it names any cached file that holds the recorded bytes under another name. It writes nothing unless given `--json-out`. `--include-candidates` also lists the manifest entries without a recorded hash, such as the candidate entries `WP-013` to `WP-020`, and whether each is cached:

```bash
uv run micar-study-verify-cache \
  --provenance studies/2026-07-title-ii-annex-i-whitepaper-study/document-provenance.json \
  --cache .study-cache/title-ii-whitepapers \
  --include-candidates
```

## Validate against human labels

The two review sheets are built from `findings-pseudonymous.json`, so their rule IDs match the detector output. Rebuild them after a detector run with:

```bash
python3 studies/2026-07-title-ii-annex-i-whitepaper-study/scripts/build_review_matrix.py
```

The script carries over reviewer cells that are already filled and stops if a filled cell no longer matches a document-rule pair or two filled rows share one. As of this commit no cell has been reviewed.

Before any labelling, the owner records in `review-protocol.md` whether labels are measured against the rules' missing-element descriptions or against the provisions as a whole (`REVIEWING.md`, step 2). Then label `human-review-blinded.csv` under `review-protocol.md` and merge the labels into `human-review-matrix.csv`:

```bash
uv run python studies/2026-07-title-ii-annex-i-whitepaper-study/scripts/build_review_matrix.py --merge-blinded
```

With a second reviewer (`REVIEWING.md`, step 3a), two steps come before that merge. Once the blinded sheet is complete, `--second-sheet` writes the second reviewer's sheet, `human-review-second.csv`: every flagged cell, every cell the first review labelled `uncertain`, `extraction_failure` or `not_applicable`, and a share of the non-flagged cells drawn by a SHA-256 ranking under `--seed` and `--fraction` (defaults 20261014 and 0.2), or every cell with `--second-all`. Once both sheets are complete, `--disagreements` writes `human-review-adjudication.csv`, one row for each cell whose two labels differ, without detector columns, for the adjudicator:

```bash
uv run python studies/2026-07-title-ii-annex-i-whitepaper-study/scripts/build_review_matrix.py --second-sheet
uv run python studies/2026-07-title-ii-annex-i-whitepaper-study/scripts/build_review_matrix.py --disagreements
```

While `human-review-second.csv` exists, `--merge-blinded` stops until it is complete and every disagreement is adjudicated, and then writes the adjudicated labels into the matrix; the plain rebuild carries that sheet's cells over as well.

Compute the metrics with:

```bash
uv run micar-review-summary \
  --matrix studies/2026-07-title-ii-annex-i-whitepaper-study/human-review-matrix.csv \
  --out /tmp/micar-study/human-review-summary.json \
  --findings studies/2026-07-title-ii-annex-i-whitepaper-study/findings-pseudonymous.json \
  --require-complete
```

The command exits with status 2 while any row remains pending, or a labelled row lacks a field that publication gate item 2 or "First review" steps 6 and 7 of `review-protocol.md` require, or has a review date after today or, with `--findings`, before the detector run. With `--findings` it exits with status 1 and writes nothing if the matrix does not hold exactly the detector's cells and detector statuses. Exit status 0 covers publication gate items 1, 2 and 4 only and is necessary for publication, not sufficient (`REVIEWING.md`, step 5).

Copy the output over `human-review-summary.json` only once the command exits 0. Then update the reviewed count (`basis-reviewed`) in `docs/playground/index.html`, which `tests/playground/model.test.mjs` checks against `rows_completed`.

The command writes its output before it checks completeness, so pointed at the committed `human-review-summary.json` it would overwrite it even while rows are pending; it then exits with status 2. Metrics exclude uncertain, extraction-failure, and not-applicable labels.

`--analyses`, which needs `--findings`, adds the analyses of the draft `analysis-plan.md` (sections 7 to 10) under the keys `detector`, `settings`, `exclusions`, `analyses` and `agreement`, after the other keys, which stay the same; the exit statuses do not change:

```bash
uv run micar-review-summary \
  --matrix studies/2026-07-title-ii-annex-i-whitepaper-study/human-review-matrix.csv \
  --out /tmp/micar-study/human-review-summary.json \
  --findings studies/2026-07-title-ii-annex-i-whitepaper-study/findings-pseudonymous.json \
  --analyses \
  --manifest studies/2026-07-title-ii-annex-i-whitepaper-study/source-manifest.json \
  --analysis-plan studies/2026-07-title-ii-annex-i-whitepaper-study/analysis-plan.md \
  --primary-exclude WP-007 \
  --internal-out /tmp/micar-study/human-review-internal.json
```

- `analyses`: the primary set, without the documents named by `--primary-exclude` (none by default; section 5 of the plan names WP-007) and without an in-sample calibration document (the one whose every cell carries the note `calibration`), and the full set S1. For each: TP, FP, FN and TN; precision, recall and specificity, each with a Wilson and a Clopper-Pearson interval, a document-cluster bootstrap (10,000 replicates and seed 20261014 unless `--replicates` and `--seed` say otherwise) and the headline interval of section 9; and F1 as `metric_note` defines it. Per-rule counts for the primary set only. The sensitivity analyses S2 (from the offerors in `--manifest`), S3 and S4, and S5, marked as not computed.
- `detector`: the findings file's SHA-256, schema, digest and date, and the detector commit once the findings file or the Detector row of `--analysis-plan` names it. `settings` records the plan's adoption status, read from its banner.
- `agreement`: with `--second-review studies/2026-07-title-ii-annex-i-whitepaper-study/human-review-second.csv` and `--adjudication studies/2026-07-title-ii-annex-i-whitepaper-study/human-review-adjudication.csv`, once the matrix and the second sheet are complete, the two reviews' raw agreement, Cohen's kappa, PABAK and Gwet's AC1, over all labels and over the cells both labelled `present` or `missing`, and whether every disagreement is adjudicated and in the matrix (publication gate item 3).

While cells are pending, each set states how many, and its metrics cover only the labelled cells; the summary gives no detector flag count for an excluded document until every cell is labelled. Per-document and per-offeror counts, and S1's per-rule table, go only to the `--internal-out` file, for internal checks (`analysis-plan.md`, section 10); git ignores files named `human-review-internal*.json` under `studies/`. With `--analyses`, an input error stops the command with status 1 before it writes anything.

The committed detector outputs are deterministic research artifacts. They are not legal advice.
