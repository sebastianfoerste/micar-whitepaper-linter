# MiCAR Whitepaper Linter

[![CI](https://github.com/sebastianfoerste/micar-whitepaper-linter/actions/workflows/ci.yml/badge.svg)](https://github.com/sebastianfoerste/micar-whitepaper-linter/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python >=3.13](https://img.shields.io/badge/python-%3E%3D3.13-blue.svg)](pyproject.toml)

**Flag missing and thin disclosures in draft MiCAR white papers before substantive legal review, using deterministic Annex I, II and III checks with pinpoint citations.**

A deterministic Python linter for draft white papers under MiCAR (Regulation (EU) 2023/1114). It checks Annex I, II and III requirements as code, accepts JSON, XHTML (incl. numbered-field iXBRL layouts) and DOCX, and runs as a CLI, a GitHub Action, or in your browser.

> Review-gated first-pass tooling. It flags candidate gaps for a lawyer; it does not decide whether a white paper is lawful or complete. **Not legal advice.** Bundled examples are synthetic.

<!--
  Screenshot/GIF placeholder — to be added.
  Replace the note below with a screenshot or GIF of a real run (for example `make demo`
  in a terminal, or a GitHub Action job log), stored under docs/ with descriptive alt text.
-->
> **Screenshot/GIF placeholder — to be added**

## Who it's for

- **Lawyers and compliance teams** reviewing a MiCAR white paper draft who want a cited first-pass list of candidate disclosure gaps before the substantive legal review.
- **Teams drafting a white paper in a Git repository** who want every push checked in CI.

Rule sets cover all three white paper regimes under MiCAR (Regulation (EU) 2023/1114): crypto-assets other than ARTs and EMTs (Annex I), asset-referenced tokens (Annex II) and e-money tokens (Annex III). It is a screening tool, not a sign-off: whether a white paper is lawful or complete remains a lawyer's judgment. Not legal advice.

## Try it now

- **In the browser, nothing leaves the page:** [live playground](https://sebastianfoerste.github.io/micar-whitepaper-linter/playground/) (Pyodide).
- **GitHub Action:** add `sebastianfoerste/micar-whitepaper-linter@v1` to a workflow in the repository that holds your draft. Findings and their citations appear in the job log, and by default (`strict: 'true'`) the job fails while BLOCKER-severity findings are open. See [GitHub Action](#github-action) for the snippet and inputs, or start from the [micar-whitepaper-template](https://github.com/sebastianfoerste/micar-whitepaper-template) repo, which ships the workflow preconfigured.
- **Local CLI:** follow the [Quick start](#quick-start) below. The core linter runs locally and does not require external LLM or network processing.

## Quick start

**From [PyPI](https://pypi.org/project/micar-whitepaper-linter/)** (Python 3.13+). One command, no install (needs [uv](https://docs.astral.sh/uv/)):

```bash
uvx micar-whitepaper-linter your-draft.json
```

Or install the `micar-lint` command:

```bash
pip install micar-whitepaper-linter
micar-lint your-draft.json
```

DOCX drafts need the `docx` extra: `pip install 'micar-whitepaper-linter[docx]'` or `uvx --from 'micar-whitepaper-linter[docx]' micar-lint your-draft.docx`.

**From a clone** of this repository (requires Python 3.13+, uv and make):

```bash
make install   # uv sync --extra dev
make demo      # lint examples/incomplete.json, a synthetic ART draft with open blockers
uv run micar-lint examples/incomplete.json --review-bundle-dir /tmp/micar-incomplete-review-bundle
```

The last command also writes a review bundle to `/tmp/micar-incomplete-review-bundle`: compliance and remediation checklists, a coverage matrix, a review table, a reviewer sign-off record and an artifact manifest.

To check your own draft, pass its path to `uv run micar-lint` instead of an example file:

- A JSON draft states its regime in its `type` field. For an XHTML or DOCX draft, add `--type other|art|emt`; the numbered-field XHTML layout requires it.
- `--strict` exits with status 1 while any BLOCKER finding is open.
- `--json` prints machine-readable JSON instead of text.

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

## Browser workbench (local preview)

The repository includes a browser workbench in `docs/playground/`. The full linter runs client-side via Pyodide. Nothing you paste leaves the page.

For local preview, run `python3 -m http.server 8765 --bind 127.0.0.1 --directory docs` and open `http://127.0.0.1:8765/playground/`. The first runtime load needs an internet connection. The app does not persist drafts in browser storage.

Details in [docs/DETAILS.md](docs/DETAILS.md#browser-workbench).

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
