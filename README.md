# MiCAR Whitepaper Linter

[![CI](https://github.com/sebastianfoerste/micar-whitepaper-linter/actions/workflows/ci.yml/badge.svg)](https://github.com/sebastianfoerste/micar-whitepaper-linter/actions/workflows/ci.yml)

The MiCAR Whitepaper Linter is a deterministic Python tool for reviewing draft crypto-asset white papers under MiCAR. It maps Annex requirements into code check classes and produces cited review artifacts over synthetic examples.

![Linter output: pass/review/missing findings with pinpoint MiCAR citations](docs/demo.svg)

## Real-world study: MiCAR Title II white papers

This repository now includes a reproducible pilot study over publicly available Title II crypto-asset white papers listed in ESMA's MiCA register.

The study runs deterministic Annex I checks over a reproducible convenience sample and publishes machine-flagged candidate gaps, exact document hashes, extraction metadata, limitations, and a 150-cell human-review matrix. The candidate flags are not reviewed legal findings.

Read the study report and validation protocol:

- `studies/2026-07-title-ii-annex-i-whitepaper-study/findings-summary.md`
- `studies/2026-07-title-ii-annex-i-whitepaper-study/review-protocol.md`
- `studies/2026-07-title-ii-annex-i-whitepaper-study/human-review-matrix.csv`

Raw white papers are not committed. Study outputs are deterministic first-pass research artifacts and are not legal advice.

## Run it

```bash
make install
make test
make demo
```

Generate a review bundle from synthetic data:

```bash
uv run --extra dev python -m micar_linter examples/incomplete.json --review-bundle-dir /tmp/micar-incomplete-review-bundle
```

## Core features

- Deterministic regulatory audits for MiCAR Annex I, II and III.
- JSON, XHTML and DOCX parsing.
- Rules-as-code severity engine.
- JSON reports for automated checks.
- Local artifact manifests and remediation reports.
- Coverage matrices, review tables and batch packs.
- Review table export: adds rule-by-rule rows with blocker status, citations, remediation, reviewer decision state and bundle export eligibility.

## Verified behavior

MiCAR white-paper requirements can be encoded as deterministic, cited and testable rules. Annex selection is explicit, rule IDs are stable, unmatched disclosure patterns produce cited candidate flags, severity is tested, and JSON outputs can be used by review workflows without hiding the legal basis.

The tool preserves legal judgment. It flags candidate disclosure gaps and produces draft review artifacts. It does not decide whether a white paper is lawful or complete.

## Tech stack

Python, Hatchling, uv and pytest.

## Verification checklist

- Run `make check`.
- Run `uv run micar-lint examples/art-stablecoin.json`.
- Run `uv run micar-lint examples/incomplete.json`.
- Generate a review bundle from a synthetic example.
- Confirm fixture labels are synthetic.
- Confirm report output states that the tool is not legal advice.
