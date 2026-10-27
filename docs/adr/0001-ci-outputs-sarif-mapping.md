# 0001. CI outputs: SARIF mapping, summary and annotations

Status: Accepted (2026-10-20)

## Context

The Action printed findings to the job log only. GitHub offers three surfaces: workflow-command annotations (no permissions, work on forks), the step summary (no permissions, 1 MiB per step) and code scanning via SARIF (`security-events: write`, public repositories or GitHub Code Security). Sources: github/docs and reviewdog, read in source on 2026-10-20 (landscape Part B). CI surfaces can be more widely visible than the draft, and the repo promises that statuses fail closed and exit codes do not change silently.

## Options

1. Emit only SARIF and let users upload it.
2. Emit rdjson for reviewdog.
3. Emit SARIF, a Markdown summary and annotation commands from the CLI; the Action wires summary and annotations by default and SARIF upload on opt-in.

## Decision

Option 3.

- **Mapping.** One SARIF `rule` per rule run, with `helpUri` to `docs/rules/<RULE_ID>.html` on the Pages site, both citation forms in `properties`, and tags. One `result` per open finding (`missing` or `review`); passes are counted in `run.properties.summary`, not listed. Level: BLOCKER → `error`, MAJOR → `warning`, MINOR → `note` (annotations: `error`, `warning`, `notice`).
- **Location.** The input path as given. `startLine` is the line of the section key inside the JSON `sections` object (last duplicate wins, as in Python and the playground), or the first XHTML `h1` to `h6` heading that maps to the section. Numbered-field XHTML, saved iXBRL viewer pages, DOCX, PDF, Markdown and sections without such a heading (including those found only under a bold-text heading) use line 1.
- **Category.** `automationDetails.id` is `micar-lint/<first 12 hex of SHA-256 of the normalised path and the regime>/`, so the same file linted under two regimes also gets two categories. codeql-action takes the category from it when present, and accepts one run per category per job, so two drafts in one job need distinct ids. The Action therefore passes no `category` input.
- **Output directory.** The Action writes to a fresh `mktemp -d` directory under `RUNNER_TEMP` per run, so a second use in one job cannot re-report the first run's files.
- **Fingerprint.** `partialFingerprints["micarRuleSection/v1"]` = SHA-256 of path, rule ID and section key, so it carries no text. GitHub documents only `primaryLocationLineHash`, which it computes itself.
- **No draft text.** Messages use rule metadata and issue strings. Issue strings of `COMMON.IXBRL_TAGGING` and `ANNEX_II.G.DEPOSIT_FLOOR_REVIEW` can quote the draft (namespaces, parser errors, percentages) and are replaced by a fixed sentence; so, since ADR 0007, are those of `COMMON.LEI_CHECK_DIGITS` and `COMMON.LEI_CONSISTENCY`, which quote LEIs. The summary names the file path, not the draft title.
- **The always-open format gate.** `COMMON.IXBRL_TAGGING` keeps its status and severity. It is tagged `format-gate` in SARIF, listed in its own summary section, and left out of the 10 annotations so it does not take a slot on every run.
- **Reproducibility.** No timestamps; fixed order (open blockers first, then missing before review, then rule order).
- **Pins.** `astral-sh/setup-uv@d4b2f3b6ecc6e67c4457f6d3e41ec42d3d0fcb86` (v5.4.2, newest v5.x) and `github/codeql-action/upload-sarif@6f2ac81f5cd81fe351a197ba0b00d91d03cd2aee` (v4.39.0), both from `git ls-remote` on 2026-10-20. Amended 2026-10-26 by owner decision: `setup-uv` moves to `1c37ad07a6a961277cf70c0d37d6f313000f5884` (v10.3.0, `git ls-remote` on 2026-10-26), because v5.4.2 runs on Node.js 20 and every run showed GitHub's deprecation warning. v10.3.0 runs on Node.js 24. Its post step fails a passing job when the uv cache directory does not exist, and v5's default cache prune that used to create the directory is off in v10, so the Action sets `enable-cache: 'false'`.
- **Cache.** `uvx --no-cache`: uv keys a path build on `pyproject.toml`, so a moved `v1` tag could otherwise reuse a stale build. `uvx --no-cache` leaves the GitHub Actions cache of `setup-uv` empty, so the Action turns it off (since 2026-10-26).

## Consequences

- Existing `@v1` users get a job summary and up to 10 annotations on the next `v1` move. Exit codes are unchanged.
- SARIF upload fails on fork PRs and on private repositories without Code Security; it is opt-in and documented.
- The annotation caps (10 per level per step) are documented only in a reviewdog issue (Claimed); the summary is the complete list.
- rdjson for reviewdog is not emitted; reviewdog can read SARIF.

- The job log still prints the full text report, including the draft title. Only the summary, annotations and SARIF log are draft-free.

## Non-negotiables check

No status, severity or exit-code change. No draft text in any CI output (tested with a marker string). Outputs byte-reproducible (tested by generating twice). No network calls added to the CLI. Every Action dependency pinned by SHA.
