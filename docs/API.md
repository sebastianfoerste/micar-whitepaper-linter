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
- `--review-table-output <path>`: write the review table, including playbook review data.
- `--compare-review-table-output <path>`: compare multiple local draft review tables by rule id and source hash.
- `--review-bundle-dir <path>`: write checklist, remediation, coverage, review table, sign-off and manifest files.
- `--manifest-output <path>`: write `micar-whitepaper-linter.artifact-manifest.v1`.
- `--version`: print the package version.

Input format is detected from the file extension by `load_whitepaper`. JSON, XHTML and DOCX are supported when the required optional parser dependencies are installed.

### Reserve-floor characterisation

For ART JSON drafts, the reserve-floor check reads three nullable, draft-supplied assertions:

- `references_official_currency`
- `art_significant`
- `article_45_7b_required_by_authority`

Each value must be a JSON boolean. Missing, null or malformed values produce `REVIEW`. The third assertion is used only for a non-significant ART that references an official currency. A determined candidate threshold with no percentage evidence produces `MISSING`; any extracted percentage produces `REVIEW`. The check never returns `PASS` and never decides whether the draft meets a threshold.

The reserved fields `reserve_characterisation_reviewed_by` and `reserve_characterisation_reviewed_on` are ignored. Draft input cannot supply trusted reviewer identity or approval. Generated reports label all characterisation fields as draft assertions pending lawyer confirmation.

## Reviewer Artifacts

```bash
uv run micar-lint examples/incomplete.json \
  --audit-log reports/incomplete-audit.md \
  --remediation-output reports/incomplete-remediation.json \
  --review-table-output reports/incomplete-review-table.json \
  --manifest-output reports/incomplete-manifest.json
```

The review table projects rule findings into rows with blocker status, remediation, citation, source anchor, reviewer decision state, export gate, review cells, playbook metadata and Word-style suggested-edit metadata. Review bundles include `review-table.md` alongside JSON outputs, and artifact manifests record each output role. The manifest records source and output SHA-256 digests, missing output warnings, blocker rule IDs and export eligibility metadata. It is an integrity aid for local review. It is not a filing approval, legal opinion, or external publication authority.

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

Use `micar_linter.artifact_manifest.build_artifact_manifest`, `micar_linter.remediation.build_remediation_report` and `micar_linter.review_table.build_review_table` when a workflow needs machine-checkable provenance, remediation metadata or rule-by-rule review rows.
