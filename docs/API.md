# API & CLI Reference

The package exposes a Python CLI, `micar-lint`, and a small programmatic API around `load_whitepaper`, `lint_whitepaper`, and report renderers.

## CLI

```bash
micar-lint <file_path> [options]
```

Supported options:

- `--json`: print the validation report as JSON.
- `--strict`: exit with status `1` when blocker findings are open.
- `--lang en|de|auto`: force rule matching language. Defaults to `auto`.
- `--audit-log <path>`: write a markdown compliance review log.
- `--remediation-output <path>`: write `micar-whitepaper-linter.remediation-report.v1`.
- `--manifest-output <path>`: write `micar-whitepaper-linter.artifact-manifest.v1`.
- `--version`: print the package version.

Input format is detected from the file extension by `load_whitepaper`. JSON, XHTML and DOCX are supported when the required optional parser dependencies are installed.

## Reviewer Artifacts

```bash
uv run micar-lint examples/incomplete.json \
  --audit-log reports/incomplete-audit.md \
  --remediation-output reports/incomplete-remediation.json \
  --manifest-output reports/incomplete-manifest.json
```

The manifest records source and output SHA-256 digests, missing output warnings, blocker rule IDs, and export eligibility metadata. It is an integrity aid for local review. It is not a filing approval, legal opinion, or external publication authority.

## Python API

```python
from pathlib import Path

from micar_linter.linter import lint_whitepaper
from micar_linter.report import render_json, render_text
from micar_linter.whitepaper import load_whitepaper

whitepaper = load_whitepaper(Path("examples/art-stablecoin.json"))
report = lint_whitepaper(whitepaper)

print(render_text(report))
print(render_json(report))
```

Use `micar_linter.artifact_manifest.build_artifact_manifest` and `micar_linter.remediation.build_remediation_report` when a workflow needs machine-checkable provenance or remediation metadata.
