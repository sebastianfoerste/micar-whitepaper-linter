# MiCAR Whitepaper Linter

[![CI](https://github.com/sebastianfoerste/micar-whitepaper-linter/actions/workflows/ci.yml/badge.svg)](https://github.com/sebastianfoerste/micar-whitepaper-linter/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/sebastianfoerste/micar-whitepaper-linter/blob/main/LICENSE)
[![Python >=3.13](https://img.shields.io/badge/python-%3E%3D3.13-blue.svg)](https://github.com/sebastianfoerste/micar-whitepaper-linter/blob/main/pyproject.toml)

**Flags missing and thin disclosures in draft MiCAR white papers before legal review, with cited Annex I to III checks.**

A deterministic Python linter for draft MiCAR (Regulation (EU) 2023/1114) white papers. It checks required sections for presence, length and keywords, reads JSON, XHTML/HTML (also numbered-field iXBRL), DOCX, PDF and Markdown, and runs as a CLI, [GitHub Action](https://github.com/sebastianfoerste/micar-whitepaper-linter/blob/main/docs/SETUP.md#github-action) or [in the browser](https://sebastianfoerste.github.io/micar-whitepaper-linter/playground/) (JSON, XHTML).

> First-pass tooling for lawyer review: it flags candidate gaps, not whether a white paper is lawful or complete. **Not legal advice.** Examples are synthetic.

## Quick start

**From [PyPI](https://pypi.org/project/micar-whitepaper-linter/)** (Python 3.13+), without installing (needs [uv](https://docs.astral.sh/uv/)):

```bash
uvx micar-whitepaper-linter your-draft.json
```

Or install it:

```bash
pip install micar-whitepaper-linter
micar-lint your-draft.json
```

**From a clone** (uv and make):

```bash
make install
make demo
```

DOCX and options: [full quick start](https://github.com/sebastianfoerste/micar-whitepaper-linter/blob/main/docs/SETUP.md#quick-start).

## Example output

`uv run micar-lint examples/incomplete.json` (synthetic, incomplete ART draft), first two findings only:

```text
MiCAR Whitepaper Linter - Incomplete Synthetic EuroStable ART Draft
Whitepaper type: ART
==============================================================================
Pass: 1  |  Review: 13  |  Missing: 6  |  Blockers: 15

[REVIEW] [BLOCKER] COMMON.SUMMARY  Plain-language summary
           Cite:  Art. 6(7), Art. 19(6), Art. 51(6) MiCAR
           Text:  https://eur-lex.europa.eu/eli/reg/2023/1114/oj/eng
           Section: 'summary'  (4 words)
           -  Section is thin: 4 words, expected at least 80.
           -  Missing review terms: summary, key information.
           -  Warning of Art. 19(6) MiCAR, second subparagraph, not found in the template's wording: point (a) introduction; point (b) decision on the whole white paper; point (c) no offer of financial instruments; point (d) no prospectus.
           -  Right of redemption at any time (Art. 19(6), third subparagraph, MiCAR) not found: no sentence names redemption together with 'at any time'.

[MISS  ] [BLOCKER] COMMON.RISK_WARNING  Mandatory risk warning statement
           Cite:  Art. 6(5), Art. 19(4), Art. 51(4) MiCAR
           Text:  https://eur-lex.europa.eu/eli/reg/2023/1114/oj/eng
           Section: 'risk_warning'  (0 words)
           -  Section is empty or absent.
...
```

## Links

- [Browser playground](https://sebastianfoerste.github.io/micar-whitepaper-linter/playground/) · [full example output](https://github.com/sebastianfoerste/micar-whitepaper-linter/blob/main/docs/demo.png) ([text](https://github.com/sebastianfoerste/micar-whitepaper-linter/blob/main/docs/demo.txt))
- [Usage and features](https://github.com/sebastianfoerste/micar-whitepaper-linter/blob/main/docs/DETAILS.md) · [Setup](https://github.com/sebastianfoerste/micar-whitepaper-linter/blob/main/docs/SETUP.md) · [Features](https://github.com/sebastianfoerste/micar-whitepaper-linter/blob/main/docs/FEATURES.md) · [Architecture](https://github.com/sebastianfoerste/micar-whitepaper-linter/blob/main/docs/ARCHITECTURE.md) · [Rule guide](https://github.com/sebastianfoerste/micar-whitepaper-linter/blob/main/docs/rule-extension-guide.md) · [Sample bundle](https://github.com/sebastianfoerste/micar-whitepaper-linter/blob/main/docs/sample-review-bundle.md) · [Launch readiness](https://github.com/sebastianfoerste/micar-whitepaper-linter/blob/main/docs/launch-readiness.md)
- [Study protocol](https://github.com/sebastianfoerste/micar-whitepaper-linter/blob/main/studies/2026-07-title-ii-annex-i-whitepaper-study/review-protocol.md) · [Contributing](https://github.com/sebastianfoerste/micar-whitepaper-linter/blob/main/CONTRIBUTING.md) · [Security](https://github.com/sebastianfoerste/micar-whitepaper-linter/blob/main/SECURITY.md) · [Privacy](https://github.com/sebastianfoerste/micar-whitepaper-linter/blob/main/PRIVACY.md)
- [Overview](https://github.com/sebastianfoerste/micar-whitepaper-linter/blob/main/docs/overview.md): audience, limits
