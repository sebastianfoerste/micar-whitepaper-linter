# API & CLI Reference

The package exposes a Python CLI, `micar-lint`, and a small programmatic API around `load_whitepaper`, `lint_whitepaper`, and report renderers.

Install it from PyPI with `pip install micar-whitepaper-linter`. The import package is `micar_linter`; the CLI is also available as `micar-whitepaper-linter`.

## CLI

```bash
micar-lint <file_path> [options]
```

Supported options:

- `--json`: print the validation report as JSON.
- `--citation-style en|de`: citation style in the text report, English EU style (`Art. 6(7) MiCAR`, default) or the canonical German form (`Art. 6 Abs. 7 MiCAR`). JSON output always carries both.
- `--type other|art|emt`: regime of a single PDF, DOCX, Markdown or XHTML draft. Required for XHTML in the numbered-field layout, whose regime is never inferred. A JSON draft states its own `type`.
- `--strict`: exit with status `1` when blocker findings are open. For a directory, also when a file could not be linted.
- `--lang en|de|auto`: force rule matching language. Defaults to `auto`.
- `--audit-log <path>`: write a markdown compliance review log.
- `--remediation-output <path>`: write `micar-whitepaper-linter.remediation-report.v1`.
- `--coverage-output <path>`: write a JSON disclosure coverage matrix.
- `--coverage`: print a coverage table to stdout instead of the report. Output files and `--strict` still apply.
- `--review-table-output <path>`: write the review table, including playbook review data.
- `--compare-review-table-output <path>`: compare multiple local draft review tables by rule id and source hash.
- `--review-bundle-dir <path>`: write checklist, remediation, coverage, review table, sign-off and manifest files.
- `--manifest-output <path>`: write `micar-whitepaper-linter.artifact-manifest.v1`.
- `--sarif-output <path>`: write a SARIF 2.1.0 log of open findings for code scanning (see below).
- `--summary-output <path>`: write a Markdown table of open findings, e.g. for `$GITHUB_STEP_SUMMARY`.
- `--annotations-output <path>`: write GitHub workflow annotation commands for up to 10 open findings.
- `--batch-output <path>`: required when the input path is a directory; writes a JSON batch review pack. Its summary counts `supported_files` and `blocked_files`, and in `failed_files` the files that could not be linted, such as numbered-field XHTML, whose regime a directory run cannot take from `--type`.
- `--workspace-output <path>`: write a local white paper vault, interactive review table and reusable playbook.
- `--collaboration-bundle-dir <path>`: write the collaboration sidecar, document change set and supervised workflow pack.
- `--workflow-action validate|inspect|run`: validate, inspect or run the supervised local workflow (`run` needs `--collaboration-bundle-dir`).
- `--version`: print the package version.

### CI outputs

`--sarif-output`, `--summary-output` and `--annotations-output` render the same report for CI. They contain rule IDs, statuses, severities, English citations, line numbers and links to the [rule pages](https://sebastianfoerste.github.io/micar-whitepaper-linter/rules/), never draft text: the issue messages of `COMMON.IXBRL_TAGGING` and `ANNEX_II.G.DEPOSIT_FLOOR_REVIEW`, which can quote the draft, are replaced by a fixed sentence, and the summary names the file path instead of the draft title. Each output is byte-reproducible (no timestamps). SARIF lists every rule run and one result per open finding; levels follow severity (BLOCKER `error`, MAJOR `warning`, MINOR `note`). They change no status, severity or exit code. The text and JSON reports on stdout are unchanged and still include draft content such as the title. Design notes: [ADR 0001](adr/0001-ci-outputs-sarif-mapping.md).

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
