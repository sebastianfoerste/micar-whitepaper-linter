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
- `human-review-summary.json`: current completion and validation metrics; it remains publication-blocking while rows are pending.
- `review-protocol.md`: label definitions, review procedure, adjudication, and publication gate.
- `findings-summary.md`: rendered pilot report.
- `methodology.md`: source, sampling, extraction, rule, and metric methodology.
- `limitations.md`: limitations and prohibited inferences.

WP identifiers are pseudonymous labels. They are not anonymisation: `source-manifest.json` maps each identifier to a public issuer and white-paper URL.

## Reproduce the detector output

Write to a scratch folder and compare with the committed files, which a re-run must not overwrite by accident. The committed findings are the machine output of the run on 2026-07-06, and the summary is rendered from them. A re-run always differs in `generated_at`, `digest`, `language_policy`, `source_manifest.register_source_detail` and each finding's `human_review_note`, because that wording and the curated manifest have changed since; its summary differs in the "Source manifest" and "Findings digest" lines with them. Its flags, the evidence's `matched_text` and each document's `extraction_metadata` may differ too, because the document loaders have changed since (`page_or_section` is the rule's fixed section hint).

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

The scripts in `scripts/` write to the committed files: `run_batch.py` to the findings, `render_report.py` to `findings-summary.md`, and `fetch_esma_register.py` (from the live ESMA register) and `select_sample.py` to `source-manifest.json` and `sample-manifest.csv`. Do not run `fetch_esma_register.py` or `select_sample.py`: they replace the curated manifest. Run `run_batch.py` only with the full cache in place, and `render_report.py` only to refresh the summary on purpose. A refresh can put committed files out of step that no script rebuilds. One that changes the flags affects the detector columns of `human-review-matrix.csv` and the candidate-gap figures in `docs/overview.md` and this README. One that changes the documents processed, or their bytes, also affects the figures in `docs/playground/index.html` and `docs/DETAILS.md`, the sample description in `methodology.md` and `limitations.md`, the inclusion and hash fields of `source-manifest.json` and the inclusion columns of `sample-manifest.csv`, the `study_doc_id` and `document_hash_sha256` columns of `human-review-blinded.csv` and `human-review-matrix.csv`, and the hashes in `document-provenance.json`. One that changes a document's extraction affects its `extraction_metadata` in `document-provenance.json`.

## Validate against human labels

Complete `human-review-matrix.csv` under `review-protocol.md`, then run:

```bash
uv run micar-review-summary \
  --matrix studies/2026-07-title-ii-annex-i-whitepaper-study/human-review-matrix.csv \
  --out /tmp/micar-study/human-review-summary.json \
  --require-complete
```

Copy the output over `human-review-summary.json` only once the command exits 0. Then update the reviewed count (`basis-reviewed`) in `docs/playground/index.html`, which `tests/playground/model.test.mjs` checks against `rows_completed`.

The command writes its output before it checks completeness, so pointed at the committed `human-review-summary.json` it would overwrite it even while rows are pending; it then exits with status 2. Metrics exclude uncertain, extraction-failure, and not-applicable labels.

The committed detector outputs are deterministic research artifacts. They are not legal advice.
