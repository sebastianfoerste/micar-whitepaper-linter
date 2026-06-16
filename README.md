# MiCAR Whitepaper Linter

The MiCAR Whitepaper Linter is a deterministic Python tool and command-line application designed to validate draft crypto-asset white papers under the Markets in Crypto-Assets Regulation (MiCAR - Regulation (EU) 2023/1114). It maps Annex requirements (Annex I, II, III) directly into code check classes.

---

## What it does
The linter parses draft white papers represented in JSON, XHTML (Inline XBRL), or DOCX formats, identifies the regulatory token regime (Other Crypto-Asset, ART, EMT), runs rule checklists (risk warnings, reserve policies, redemption access, registry metrics), and prints structured markdown audits or outputs JSON payloads.

---

## Quick Start

Run one synthetic white paper and inspect cited findings:

```bash
uv run --extra dev python -m micar_linter examples/art-stablecoin.json --json
```

For human-readable output:

```bash
uv run --extra dev python -m micar_linter examples/incomplete.json
```

The output is a first-pass rule report with citations, severity, status and review notes. It is not legal advice and does not replace lawyer review.

---

## Core Features
- **Deterministic Regulatory Audits**: Maps statutory rules for Annex I (other crypto-assets), Annex II (Asset-Referenced Tokens), and Annex III (E-Money Tokens).
- **Multiple Document Format Parsers**: Extracts white paper blocks from XHTML (Inline XBRL tags), JSON structures, and DOCX files.
- **Rules-as-Code Engine**: Implements severity scales (Blocker, Major, Minor, Pass) for compliance findings.
- **CI/CD Integrations**: Outputs machine-readable JSON reports suitable for automated pipeline checks.
- **Artifact Manifests & Remediation Reports**: Writes local SHA-256 manifests and structured remediation plans for open findings. Manifests include export eligibility and missing-output warnings, but do not store raw confidential source snippets.
- **Coverage Matrices & Batch Packs**: Writes disclosure coverage matrices, source-anchor metadata, and directory-level batch review packs with hashes, blocker IDs, and manifest digests.

---

## What this proves

This repository shows that MiCAR white-paper requirements can be encoded as deterministic, cited and testable rules. It is a regulation-as-code proof: annex selection is explicit, rule IDs are stable, missing mandatory disclosures produce cited findings, severity is tested, and JSON outputs can be used by review workflows without hiding the legal basis.

The tool deliberately preserves legal judgment. It identifies disclosure gaps and produces draft review artifacts. It does not decide whether a white paper is lawful, complete for filing or commercially acceptable.

---

## Tech Stack
- **Runtime**: Python (>= 3.13)
- **Packaging/Installer**: Hatchling, `uv`
- **Optional File Parsers**: `python-docx` (DOCX), `pypdf` (PDF)
- **Testing**: pytest

---

## Repository Structure
- `src/micar_linter/`: Source modules.
  - `rules/`: Concrete Annex I, II, III check files.
  - `ixbrl.py` & `xhtml_parser.py`: iXBRL XHTML tag compilers.
  - `document.py` & `whitepaper.py`: Logical document abstractions.
  - `report.py`: Compile final audit reports.
  - `cli.py` & `__main__.py`: CLI interface.
- `tests/`: Pytest files checking parser stability.
- `examples/`: Sample compliant and incomplete white papers.
- `reports/`: Text logs of sample run results.

---

## Setup & Running Instructions

### 1. Install Library
Sync dependencies using `uv`:
```bash
uv sync --all-extras
```
Or use pip inside a virtual environment:
```bash
pip install -e ".[all]"
```

### 2. Running the Linter
Run the linter against a document:
```bash
# Run CLI
uv run micar-lint examples/incomplete.json

# Write reviewer artifacts
uv run micar-lint examples/incomplete.json \
  --audit-log reports/incomplete-audit.md \
  --remediation-output reports/incomplete-remediation.json \
  --coverage-output reports/incomplete-coverage.json \
  --manifest-output reports/incomplete-manifest.json

# Batch review a directory
uv run micar-lint examples \
  --batch-output reports/example-batch-pack.json
```

---

## Testing Commands
Run the full local proof gate:
```bash
make check
```

Run the pytest suite directly:
```bash
uv run --extra dev pytest
```

## Extending the rule set

See [How to Extend the Rule Set](docs/rule-extension-guide.md) before adding a new disclosure rule.
