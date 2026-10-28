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

## Validate against human labels

Start labelling the 150 cells only after the adoption commit on `main` that adopts `codebook.md` and `analysis-plan.md` with the pending sheets (`analysis-plan.md`, step 0.10). It follows the signing order in their banners: the study tooling is merged into `main` as unsigned draft tooling first, and Phase 0 is done on `main`. The calibration document is labelled before that commit, in Phase 0 (step 0.9), outside the committed sheets (`analysis-plan.md` section 4).

Each reviewer labels only their own blinded sheet (`human-review-r1.csv`, and `human-review-r2.csv` for a second reviewer) under `review-protocol.md` and `codebook.md`. While labelling, reviewers do not open `human-review-matrix.csv`, `findings-pseudonymous.*` or `findings-summary.md`. Each reviewer's labels are committed on their own. Only then are the final labels merged into `human-review-matrix.csv` with the detector outcomes. Then run:

```bash
uv run micar-review-summary \
  --matrix studies/2026-07-title-ii-annex-i-whitepaper-study/human-review-matrix.csv \
  --out /tmp/micar-study/human-review-summary.json \
  --require-complete
```

Copy the output over `human-review-summary.json` only once the command exits 0. Then update the reviewed count (`basis-reviewed`) in `docs/playground/index.html`, which `tests/playground/model.test.mjs` checks against `rows_completed`.

The command writes its output before it checks completeness, so pointed at the committed `human-review-summary.json` it would overwrite it even while rows are pending; it then exits with status 2. Metrics exclude uncertain, extraction-failure, and not-applicable labels.

The committed detector outputs are deterministic research artifacts. They are not legal advice.
