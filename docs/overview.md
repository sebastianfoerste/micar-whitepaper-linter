# Overview

Audience, status and limits, the pilot study and related tools, moved out of the [README](../README.md) word for word. Setup and the GitHub Action are in [SETUP.md](SETUP.md); long-form usage and the full example output are in [DETAILS.md](DETAILS.md).

## Who it's for

- **Lawyers and compliance teams** reviewing a MiCAR white paper draft who want a cited first-pass list of candidate disclosure gaps before the substantive legal review.
- **Teams drafting a white paper in a Git repository** who want every push checked in CI.

Rule sets cover all three white paper regimes under MiCAR (Regulation (EU) 2023/1114): crypto-assets other than ARTs and EMTs (Annex I), asset-referenced tokens (Annex II) and e-money tokens (Annex III). It is a screening tool, not a sign-off: whether a white paper is lawful or complete remains a lawyer's judgment. Not legal advice.

## Status and limits

| Area | State |
| --- | --- |
| Table 2 (crypto-assets other than ART/EMT) | Run against public ESMA-register documents |
| Table 3 / Table 4 (ART / EMT) | Follows the Official Journal text; **not yet run against a real ART or EMT white paper** |
| iXBRL check | Well-formedness, Inline XBRL 1.1 and ESMA MiCA taxonomy namespaces only; never reports Pass; not run for a saved iXBRL viewer page (Missing) |
| Reserve-floor check | Extracts candidates; never returns `PASS` |
| Pilot study | 10 documents, 15 rules each, 21 machine-flagged candidate gaps, **pending human review**; convenience sample, no precision/recall claim |

## Pilot study

A reproducible study over Title II white papers in ESMA's MiCA register publishes document hashes, extraction metadata, limitations and a 150-cell human-review matrix. Flags are unreviewed machine output, not legal findings. Raw white papers are not committed. Start at [findings-summary.md](../studies/2026-07-title-ii-annex-i-whitepaper-study/findings-summary.md).

## Part of the EU regulation as code suite

Deterministic, review-gated tools by [sebastianfoerste](https://github.com/sebastianfoerste):

- [awesome-eu-fintech-regulation](https://github.com/sebastianfoerste/awesome-eu-fintech-regulation): curated EU fintech primary sources and tools
- [contract-review-eval-harness](https://github.com/sebastianfoerste/contract-review-eval-harness)
- [legal-function-operating-system](https://github.com/sebastianfoerste/legal-function-operating-system)
- [eu-ai-act-classifier](https://github.com/sebastianfoerste/eu-ai-act-classifier): AI Act risk tiers with cited obligations
- **micar-whitepaper-linter** (this repo)
- [eu-reg-mcp](https://github.com/sebastianfoerste/eu-reg-mcp): MCP server; exposes a `lint_micar_whitepaper` tool
- [micar-register-observatory](https://github.com/sebastianfoerste/micar-register-observatory)

Also: [micar-whitepaper-template](https://github.com/sebastianfoerste/micar-whitepaper-template), [dpa-and-data-transfer-review](https://github.com/sebastianfoerste/dpa-and-data-transfer-review).
