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

Regenerate the blinded sheets and the matrix from the findings file. Rule IDs and Annex labels come from `STUDY_RULES`; every label is written as `pending`. The command refuses to overwrite a sheet that already holds review content. Add `--reviewer r2` for a second reviewer, or `--check` to confirm that the committed files match:

```bash
uv run micar-review-sheets \
  --findings studies/2026-07-title-ii-annex-i-whitepaper-study/findings-pseudonymous.json \
  --out-dir studies/2026-07-title-ii-annex-i-whitepaper-study
```

## Validate against human labels

Each reviewer labels only their own blinded sheet (`human-review-r1.csv`, and `human-review-r2.csv` for a second reviewer) under `review-protocol.md` and `codebook.md`. While labelling, reviewers do not open `human-review-matrix.csv`, `findings-pseudonymous.*` or `findings-summary.md`. Each reviewer's labels are committed on their own. Only then are the final labels merged into `human-review-matrix.csv` with the detector outcomes. Then run:

```bash
uv run micar-review-summary \
  --matrix studies/2026-07-title-ii-annex-i-whitepaper-study/human-review-matrix.csv \
  --out studies/2026-07-title-ii-annex-i-whitepaper-study/human-review-summary.json \
  --require-complete
```

The command exits with status 2 while any row remains pending. Metrics exclude uncertain, extraction-failure, and not-applicable labels.

The committed detector outputs are deterministic research artifacts. They are not legal advice.
