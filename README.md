# MiCAR Whitepaper Linter

Deterministic first-pass linter for MiCAR crypto-asset white paper drafts. Reads a JSON draft, applies the rule set keyed to the white paper regime (Annex I / II / III), and emits a structured report with pinpoint citations to the Regulation.

This is not legal advice. It is a screening tool that a practising lawyer supervises.

## Problem

MiCAR Art. 6 (other crypto-assets), Art. 19 (asset-referenced tokens), and Art. 51 (e-money tokens) each prescribe a different disclosure regime, each tied to its own Annex. Drafting reviews catch the same structural gaps over and over — missing reserve composition under Art. 36 MiCAR, missing redemption procedure under Art. 39 MiCAR, missing safeguarding statement under Art. 54 MiCAR. Doing that read-through manually on every draft is wasteful and inconsistent across reviewers.

## What I built

A Python package that:

- detects the whitepaper regime from the draft itself (`other` / `art` / `emt`),
- applies the rule set keyed to the relevant Annex of MiCAR,
- ranks findings by severity (BLOCKER for items that gate notification under Art. 8 / 17 / 49 MiCAR, MAJOR for material incompleteness, MINOR for drafting hygiene), and
- emits either a human-readable report with pinpoint citations or machine-readable JSON for downstream pipelines.

## Architecture

```
Input: JSON whitepaper draft
        |
        v
┌─────────────────────────────────┐
│       Regime Detector           │
│  (other / art / emt)            │
│  reads: regime, issuer, token   │
└────────────┬────────────────────┘
             │
             v
┌─────────────────────────────────┐
│       Rule Engine               │
│  Annex I / II / III rule set    │
│  rule_id, section, severity     │
└────────────┬────────────────────┘
             │
             v
┌─────────────────────────────────┐
│       Report Generator          │
│  BLOCKER / MAJOR / MINOR        │
│  pinpoint citation to MiCAR Art │
│  human-readable + JSON output   │
└─────────────────────────────────┘
             │
             v
 Output: structured report
   → reviewer reads BLOCKER items
   → lawyer signs off or rejects
   → downstream pipeline (JSON)
```

Each rule carries a stable `rule_id`, a citation in canonical legal form (`Anhang II Teil G i.V.m. Art. 36 MiCAR`), the section key it reads, and a severity. The rule sets are the contribution of a practising lawyer; the engine is generic.

## Status

Alpha. The Annex I / II / III scaffolds are in place at the Part level and cover the disclosure architecture end-to-end. Point-level granularity (e.g. `Annex II, Part G, point 5`) and substantive interpretive thresholds are tracked in the issues — those are the items that need a practising MiCAR lawyer's judgement rather than a check-the-box pass.

## Stack

Python 3.11+, zero core runtime dependencies, hatchling build, pytest, ruff, GitHub Actions CI. Optional extras `[docx]` (python-docx) and `[pdf]` (pypdf) unlock DOCX and PDF whitepaper ingestion.

## How to run

```bash
git clone https://github.com/sebastianforste/micar-whitepaper-linter.git
cd micar-whitepaper-linter
python3 -m micar_linter examples/art-stablecoin.json
python3 -m micar_linter examples/incomplete.json --strict
```

No install needed for the JSON workflow: the core package has zero runtime dependencies and runs straight from source via `python3 -m micar_linter`. To install as a CLI named `micar-lint`, run `pip install -e .` and you can drop the `python3 -m`. For PDF or DOCX ingestion run `pip install -e ".[all]"`.

JSON output for pipelines:

```bash
python3 -m micar_linter examples/emt-token.json --json
```

Strict mode returns exit code 1 if any BLOCKER finding is open — wire it into a pre-notification check.

## Sample output

`reports/sample-art-pass.txt` and `reports/sample-incomplete-blockers.txt` are committed so a reviewer sees the tool working without installing anything. Excerpt of the incomplete-draft report:

```
MiCAR Whitepaper Linter — Incomplete EuroStable ART Draft
Whitepaper type: ART
==============================================================================
Pass: 0  |  Review: 10  |  Missing: 4  |  Blockers: 11

[MISS  ] [BLOCKER] COMMON.RISK_WARNING  Mandatory risk warning statement
           Cite:  Art. 6 Abs. 5, Art. 19 Abs. 5, Art. 51 Abs. 5 MiCAR
           Section: 'risk_warning'  (0 words)
           -  Section is empty or absent.

[REVIEW] [BLOCKER] ANNEX_II.G  Reserve of assets (composition, custody, segregation, valuation, audit)
           Cite:  Anhang II Teil G i.V.m. Art. 36 MiCAR
           Section: 'reserve_of_assets'  (3 words)
           -  Section is thin: 3 words, expected at least 150.
           -  Missing review terms: composition, segregation, custodian, valuation, audit.
```

## Input format

A whitepaper draft is one JSON file with a top-level `type` (`other` / `art` / `emt`), a `title`, and a `sections` object whose keys match the rule `section` identifiers. See [`examples/`](examples/) for one fixture per regime.

## Layout

```
src/micar_linter/
  rules/
    common.py       # Art. 6(5)-(7), 19(5)-(7), 51(5)-(7) MiCAR — every regime
    annex_i.py      # Anhang I — Art. 6 MiCAR — crypto-assets other than ARTs/EMTs
    annex_ii.py     # Anhang II — Art. 19 MiCAR — asset-referenced tokens
    annex_iii.py    # Anhang III — Art. 51 MiCAR — e-money tokens
    base.py         # Rule, Finding, Severity
  linter.py         # rule engine
  report.py         # text + JSON rendering
  cli.py            # argparse CLI
examples/           # one fixture per regime + one incomplete draft
reports/            # committed sample outputs
tests/              # pytest smoke tests
```

## Roadmap

See open issues. Headline items: point-level Annex II rules for reserve composition under Art. 36 MiCAR, German-language draft support, ESMA Q&A enrichment, and a reviewer audit log.

## License

MIT. The legal classifications encoded in this repository reflect the author's reading of MiCAR and are not legal advice. A practising lawyer must supervise every white paper review.
