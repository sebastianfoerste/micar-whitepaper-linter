# MiCAR Whitepaper Linter

[![CI](https://github.com/sebastianfoerste/micar-whitepaper-linter/actions/workflows/ci.yml/badge.svg)](https://github.com/sebastianfoerste/micar-whitepaper-linter/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/sebastianfoerste/micar-whitepaper-linter/blob/main/LICENSE)
[![Python >=3.13](https://img.shields.io/badge/python-%3E%3D3.13-blue.svg)](https://github.com/sebastianfoerste/micar-whitepaper-linter/blob/main/pyproject.toml)

**Flag missing and thin disclosures in draft MiCAR white papers before substantive legal review, using deterministic Annex I, II and III checks with pinpoint citations.**

A deterministic Python linter for draft white papers under MiCAR (Regulation (EU) 2023/1114). It checks Annex I, II and III sections for presence, length and keywords, accepts JSON, XHTML or HTML (incl. numbered-field iXBRL layouts), DOCX, PDF and Markdown, and runs as a CLI, [a GitHub Action](https://github.com/sebastianfoerste/micar-whitepaper-linter/blob/main/docs/SETUP.md#github-action), or [in your browser](https://sebastianfoerste.github.io/micar-whitepaper-linter/playground/) (JSON, (X)HTML).

> Review-gated first-pass tooling. It flags candidate gaps for a lawyer; it does not decide whether a white paper is lawful or complete. **Not legal advice.** Bundled examples are synthetic.

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

**From a clone** (requires Python 3.13+, uv and make):

```bash
make install   # uv sync --extra dev
make demo      # lint examples/incomplete.json, a synthetic ART draft with open blockers
```

DOCX, review bundles and options: [full quick start](https://github.com/sebastianfoerste/micar-whitepaper-linter/blob/main/docs/SETUP.md#quick-start).

## Example output

Real output of `uv run micar-lint examples/incomplete.json` (a synthetic, incomplete ART draft), first two findings only:

```text
MiCAR Whitepaper Linter - Incomplete Synthetic EuroStable ART Draft
Whitepaper type: ART
==============================================================================
Pass: 1  |  Review: 11  |  Missing: 8  |  Blockers: 15

[REVIEW] [BLOCKER] COMMON.SUMMARY  Plain-language summary
           Cite:  Art. 6(7), Art. 19(6), Art. 51(6) MiCAR
           Text:  https://eur-lex.europa.eu/eli/reg/2023/1114/oj/eng
           Section: 'summary'  (4 words)
           -  Section is thin: 4 words, expected at least 80.
           -  Missing review terms: summary, key information.

[MISS  ] [BLOCKER] COMMON.RISK_WARNING  Mandatory risk warning statement
           Cite:  Art. 6(5), Art. 19(4), Art. 51(4) MiCAR
           Text:  https://eur-lex.europa.eu/eli/reg/2023/1114/oj/eng
           Section: 'risk_warning'  (0 words)
           -  Section is empty or absent.
...
```

## Links

- [Browser playground](https://sebastianfoerste.github.io/micar-whitepaper-linter/playground/) and [screenshot of the full example output](https://github.com/sebastianfoerste/micar-whitepaper-linter/blob/main/docs/demo.png) ([text](https://github.com/sebastianfoerste/micar-whitepaper-linter/blob/main/docs/demo.txt))
- [Full usage, features, reviewer route, redline bundles](https://github.com/sebastianfoerste/micar-whitepaper-linter/blob/main/docs/DETAILS.md) · [Setup](https://github.com/sebastianfoerste/micar-whitepaper-linter/blob/main/docs/SETUP.md) · [Features](https://github.com/sebastianfoerste/micar-whitepaper-linter/blob/main/docs/FEATURES.md) · [Architecture](https://github.com/sebastianfoerste/micar-whitepaper-linter/blob/main/docs/ARCHITECTURE.md) · [Rule extension guide](https://github.com/sebastianfoerste/micar-whitepaper-linter/blob/main/docs/rule-extension-guide.md) · [Sample review bundle](https://github.com/sebastianfoerste/micar-whitepaper-linter/blob/main/docs/sample-review-bundle.md) · [Launch readiness](https://github.com/sebastianfoerste/micar-whitepaper-linter/blob/main/docs/launch-readiness.md)
- [Study protocol](https://github.com/sebastianfoerste/micar-whitepaper-linter/blob/main/studies/2026-07-title-ii-annex-i-whitepaper-study/review-protocol.md) · [Contributing](https://github.com/sebastianfoerste/micar-whitepaper-linter/blob/main/CONTRIBUTING.md) · [Security](https://github.com/sebastianfoerste/micar-whitepaper-linter/blob/main/SECURITY.md) · [Privacy](https://github.com/sebastianfoerste/micar-whitepaper-linter/blob/main/PRIVACY.md)
- [Overview](https://github.com/sebastianfoerste/micar-whitepaper-linter/blob/main/docs/overview.md): audience, limits, pilot study, related tools
