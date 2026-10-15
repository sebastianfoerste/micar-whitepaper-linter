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
- `findings-summary.md`: rendered pilot report.
- `methodology.md`: source, sampling, extraction, rule, and metric methodology.
- `limitations.md`: limitations and prohibited inferences.

WP identifiers are pseudonymous labels. They are not anonymisation: `source-manifest.json` maps each identifier to a public issuer and white-paper URL.

## Reproduce the detector output

The first two commands rewrite `source-manifest.json`, which holds the frozen pilot sample, and `findings-pseudonymous.json` and `findings-pseudonymous.csv`, which hold the detector output under review. Do not run them during a review.

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

Compute the metrics with:

```bash
uv run micar-review-summary \
  --matrix studies/2026-07-title-ii-annex-i-whitepaper-study/human-review-matrix.csv \
  --out studies/2026-07-title-ii-annex-i-whitepaper-study/human-review-summary.json \
  --findings studies/2026-07-title-ii-annex-i-whitepaper-study/findings-pseudonymous.json \
  --require-complete
```

The command exits with status 2 while any row remains pending, or a labelled row lacks a field that publication gate item 2 or "First review" steps 6 and 7 of `review-protocol.md` require, or has a review date after today or, with `--findings`, before the detector run. With `--findings` it exits with status 1 and writes nothing if the matrix does not hold exactly the detector's cells and detector statuses. Exit status 0 covers publication gate items 1, 2 and 4 only and is necessary for publication, not sufficient (`REVIEWING.md`, step 5). Metrics exclude uncertain, extraction-failure, and not-applicable labels.

The committed detector outputs are deterministic research artifacts. They are not legal advice.
