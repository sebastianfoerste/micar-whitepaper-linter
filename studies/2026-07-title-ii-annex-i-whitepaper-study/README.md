# MiCAR White Paper Study 2026: Annex I Disclosure Patterns in Notified Title II White Papers

This folder contains a reproducible pilot study over publicly available Title II crypto-asset white papers listed in ESMA's MiCA register.

The study is deliberately narrow. It covers crypto-assets other than asset-referenced tokens and e-money tokens, mapped to MiCAR Article 6 and Annex I. It does not cover Annex II or Annex III white papers.

Raw white papers are not committed. Store downloaded source documents under `.study-cache/title-ii-whitepapers/`.

## Files

- `source-manifest.json`: normalized source metadata, register row hashes, and sample inclusion status.
- `sample-manifest.csv`: compact CSV view of the included v1 sample.
- `findings-anonymized.json`: machine-flagged potential disclosure gaps keyed by WP-ID study identifiers. The IDs are pseudonymous labels, not anonymization: `sample-manifest.csv` maps each WP-ID to its public ESMA register entry.
- `findings-anonymized.csv`: flat finding-level CSV for review.
- `findings-summary.md`: rendered public study report.
- `methodology.md`: sampling, extraction, and rule methodology.
- `limitations.md`: limitations and review boundaries.

## Reproduce

```bash
uv run python -m micar_linter.esma_register \
  --csv .study-cache/esma-title-ii-register.csv \
  --out studies/2026-07-title-ii-annex-i-whitepaper-study/source-manifest.json

uv run micar-lint-batch \
  --manifest studies/2026-07-title-ii-annex-i-whitepaper-study/source-manifest.json \
  --cache .study-cache/title-ii-whitepapers \
  --annex annex-i \
  --out studies/2026-07-title-ii-annex-i-whitepaper-study/findings-anonymized.json

uv run micar-study-report \
  --findings studies/2026-07-title-ii-annex-i-whitepaper-study/findings-anonymized.json \
  --out studies/2026-07-title-ii-annex-i-whitepaper-study/findings-summary.md
```

The committed findings are deterministic first-pass research artifacts. They are not legal advice.
