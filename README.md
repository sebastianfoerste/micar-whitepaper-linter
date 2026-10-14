# MiCAR Whitepaper Linter

**Catch missing MiCAR Annex disclosures in a draft crypto-asset white paper before you notify the regulator, with the article cited for every gap.**

[![CI](https://github.com/sebastianfoerste/micar-whitepaper-linter/actions/workflows/ci.yml/badge.svg)](https://github.com/sebastianfoerste/micar-whitepaper-linter/actions/workflows/ci.yml)

A deterministic Python linter for draft white papers under MiCAR (Regulation (EU) 2023/1114). It checks Annex I, II and III requirements as code, accepts JSON, XHTML (incl. numbered-field iXBRL layouts) and DOCX, and runs as a CLI, a GitHub Action, or in your browser.

> Review-gated first-pass tooling. It flags candidate gaps for a lawyer; it does not decide whether a white paper is lawful or complete. **Not legal advice.** Bundled examples are synthetic.

## Try it

**In the browser, nothing leaves the page:** [live playground](https://sebastianfoerste.github.io/micar-whitepaper-linter/playground/) (Pyodide).

**One command, no install** (needs [uv](https://docs.astral.sh/uv/) and Python 3.13+; I ran this form from the repo's git URL):

```bash
uvx --from git+https://github.com/sebastianfoerste/micar-whitepaper-linter micar-lint your-draft.json
```

PyPI: a `uvx micar-whitepaper-linter` form is coming; the package is not published yet [UNVERIFIED: PyPI name availability not checked].

From a clone:

```bash
make install && make demo
uv run micar-lint examples/incomplete.json
```

## Example output

Real output of `uv run micar-lint examples/incomplete.json` (a synthetic, deliberately incomplete ART draft), first findings only:

```text
MiCAR Whitepaper Linter - Incomplete Synthetic EuroStable ART Draft
Whitepaper type: ART
==============================================================================
Pass: 0  |  Review: 13  |  Missing: 5  |  Blockers: 15

[REVIEW] [BLOCKER] COMMON.SUMMARY  Plain-language summary
           Cite:  Art. 6 Abs. 7, Art. 19 Abs. 6, Art. 51 Abs. 6 MiCAR
           Section: 'summary'  (4 words)
           -  Section is thin: 4 words, expected at least 80.
           -  Missing review terms: summary, key information.

[MISS  ] [BLOCKER] COMMON.RISK_WARNING  Mandatory risk warning statement
           Cite:  Art. 6 Abs. 5, Art. 19 Abs. 4, Art. 51 Abs. 4 MiCAR
           Section: 'risk_warning'  (0 words)
           -  Section is empty or absent.

[MISS  ] [BLOCKER] COMMON.IXBRL_TAGGING  Inline XBRL (iXBRL) compliance and ESMA metadata tagging
           Cite:  Art. 2 VO (EU) 2024/2984
           -  Draft format: notification requires XHTML with Inline XBRL tagging. ...
```

(The third finding is trimmed with `...`; the "Abs." citation style is as the tool prints it.) XHTML in the numbered-field layout of Implementing Regulation (EU) 2024/2984 works too; state the regime, since it is not inferred:

```bash
uv run micar-lint examples/numbered-other-draft.xhtml --type other
```

## GitHub Action

```yaml
- uses: actions/checkout@v4
- uses: sebastianfoerste/micar-whitepaper-linter@v1
  with:
    whitepaper: drafts/whitepaper.json
    strict: 'true'
```

The job fails while BLOCKER findings are open. Starter repo with this preconfigured: [micar-whitepaper-template](https://github.com/sebastianfoerste/micar-whitepaper-template). Details in [docs/DETAILS.md](docs/DETAILS.md#github-action).

## Status and limits

| Area | State |
| --- | --- |
| Table 2 (crypto-assets other than ART/EMT) | Run against public ESMA-register documents |
| Table 3 / Table 4 (ART / EMT) | Follows the Official Journal text; **not yet run against a real ART or EMT white paper** |
| iXBRL check | Well-formedness, Inline XBRL 1.1 and ESMA MiCA taxonomy namespaces only; never reports Pass |
| Reserve-floor check | Extracts candidates; never returns `PASS` |
| Pilot study | 10 documents, 15 rules each, 21 machine-flagged candidate gaps, **pending human review**; convenience sample, no precision/recall claim |

## Pilot study

A reproducible study over Title II white papers in ESMA's MiCA register publishes document hashes, extraction metadata, limitations and a 150-cell human-review matrix. Flags are unreviewed machine output, not legal findings. Raw white papers are not committed. Start at [findings-summary.md](studies/2026-07-title-ii-annex-i-whitepaper-study/findings-summary.md).

## Links

- [Browser playground](https://sebastianfoerste.github.io/micar-whitepaper-linter/playground/) and demo image: [docs/demo.svg](docs/demo.svg)
- [Full usage, features, reviewer route, redline bundles](docs/DETAILS.md) · [Setup](docs/SETUP.md) · [Features](docs/FEATURES.md) · [Architecture](docs/ARCHITECTURE.md) · [Rule extension guide](docs/rule-extension-guide.md) · [Sample review bundle](docs/sample-review-bundle.md) · [Launch readiness](docs/launch-readiness.md)
- [Study protocol](studies/2026-07-title-ii-annex-i-whitepaper-study/review-protocol.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [Privacy](PRIVACY.md)

Develop with `make check` (lint, tests, CLI smoke check).

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
