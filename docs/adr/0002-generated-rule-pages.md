# 0002. Generated rule pages with executed examples

Status: Accepted (2026-10-20)

## Context

Findings cite a provision but the rule logic was only readable in Python. The strongest rule-doc pattern seen is ESLint's: every doc example is linted in CI (`tools/check-rule-examples.js`, Observed). Ruff checks that headings exist; DQC and Spectral keep tests apart from docs (Observed).

## Options

1. Hand-written Markdown per rule.
2. Pages generated from the `Rule` objects, with examples that are only rendered.
3. Pages generated from the `Rule` objects, with examples linted at build time and in tests, and a staleness test.

## Decision

Option 3. `scripts/build_rule_docs.py` writes static HTML to `docs/rules/` (Pages root, no build step). Each page states the citation in English and canonical form, the regimes, severity, section key, listed terms, the status logic, synthetic examples, limitations and the source module. The generator stops if an example's linted status differs from the stated one; `tests/test_rule_docs.py` repeats that check and compares committed pages with regenerated ones. The passing example is filler text that names the listed terms, to show that a pass is lexical. Never-pass rules have no passing example. Citations were not re-verified (EUR-Lex unreachable) and each page says so.

## Consequences

- Changing a rule needs `uv run python scripts/build_rule_docs.py`; the test says so when pages are stale.
- Pages go public on merge, as the rest of `docs/`.
- `helpUri` in SARIF and the links in the summary, annotations and playground cards point at these pages.

## Non-negotiables check

Synthetic examples only; no real white paper text. No legal citation added or changed. No compliance claim: pages say a pass means a check matched. No runtime network calls; pages load one stylesheet and one small script from the same origin.
