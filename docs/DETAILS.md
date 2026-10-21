# Detailed usage and reference

Long-form detail moved out of the README. Everything here was in the previous README.

## Browser workbench

The full linter runs client-side via Pyodide. Nothing you paste leaves the page.

The browser workbench accepts JSON drafts up to 1 MB and XHTML white papers up to 4 MB, includes synthetic examples for all three regimes, and presents searchable findings with citations and section navigation. Download the current report as JSON or text, or save a copy of the draft. Editing a checked draft marks the previous results as stale and disables report export until the checks run again. Python runs in a web worker so the editor stays responsive.

For local preview, run `python3 -m http.server 8765 --bind 127.0.0.1 --directory docs` and open `http://127.0.0.1:8765/playground/`. The first runtime load needs an internet connection. The app does not persist drafts in browser storage.

## Real-world study: MiCAR Title II white papers

This repository includes a reproducible pilot study over publicly available Title II crypto-asset white papers listed in ESMA's MiCA register.

The study runs deterministic Annex I checks over a reproducible convenience sample and publishes machine-flagged candidate gaps, exact document hashes, extraction metadata, limitations, and a 150-cell human-review matrix. The candidate flags are not reviewed legal findings.

- [`findings-summary.md`](../studies/2026-07-title-ii-annex-i-whitepaper-study/findings-summary.md)
- [`review-protocol.md`](../studies/2026-07-title-ii-annex-i-whitepaper-study/review-protocol.md)
- [`human-review-matrix.csv`](../studies/2026-07-title-ii-annex-i-whitepaper-study/human-review-matrix.csv)

Raw white papers are not committed. Study outputs are deterministic first-pass research artifacts and are not legal advice.

## Commands

```bash
make install
make test
make demo
make check      # lint, tests and the sample CLI smoke check
```

Generate a review bundle from synthetic data:

```bash
uv run --extra dev python -m micar_linter examples/incomplete.json --review-bundle-dir /tmp/micar-incomplete-review-bundle
```

Check an XHTML white paper in the numbered-field layout of Implementing Regulation (EU) 2024/2984 ("A.1 Name", "A.2 Legal form"). State the regime, because it is not inferred from the text of such a file:

```bash
uv run micar-lint examples/numbered-other-draft.xhtml --type other
```

## Coverage caveats

The Table 2 mapping (crypto-assets other than ARTs and EMTs) has been run against public register documents. The Table 3 and Table 4 mappings follow the Official Journal text and have not yet been run against a real ART or EMT white paper. The iXBRL check tests well-formedness, the Inline XBRL 1.1 namespace and the ESMA MiCA taxonomy namespace. It does not evaluate the taxonomy's existence and value assertions, so it never reports Pass.

## GitHub Action

```yaml
jobs:
  micar-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: sebastianfoerste/micar-whitepaper-linter@v1
        with:
          whitepaper: drafts/whitepaper.json
          strict: 'true'
```

Inputs:

| Input | Default | Effect |
|---|---|---|
| `whitepaper` | required | Path to a JSON, XHTML or DOCX draft |
| `strict` | `true` | Fail the job while BLOCKER findings are open |
| `extra-args` | `''` | More CLI arguments, e.g. `--json`, `--type art` |
| `summary` | `true` | Append a table of open findings to the job summary: rule, status, severity, citation, `file:line`, rule page |
| `annotations` | `true` | Annotate up to 10 open findings on the draft file (open blockers first) |
| `upload-sarif` | `false` | Upload a SARIF log to GitHub code scanning |

Output: `sarif-file`, the path of the SARIF log, for other uploaders such as reviewdog.

The job fails while BLOCKER-severity findings are open. A failing job means open blockers to review, not a legal conclusion. The summary, annotations and SARIF log carry rule IDs, statuses, citations and line numbers, never draft text or the draft title, and they change no status or exit code. The job log still prints the full text report, which includes the draft title and quoted figures such as reserve percentages; treat the log as being as sensitive as the draft. The `summary`, `annotations` and `upload-sarif` inputs and the `sarif-file` output ship with the next `v1` release. The iXBRL format check (`COMMON.IXBRL_TAGGING`) never passes, so it is listed in its own summary section and not annotated.

Line numbers point at the section key in a JSON draft or the matching heading in an XHTML draft; numbered-field XHTML, DOCX and absent sections point at line 1.

Code scanning needs extra permissions and works on public repositories, or private ones with GitHub Code Security. Uploads from fork pull requests fail with the default read-only token:

```yaml
permissions:
  contents: read
  security-events: write
steps:
  - uses: actions/checkout@v4
  - uses: sebastianfoerste/micar-whitepaper-linter@v1
    with:
      whitepaper: drafts/whitepaper.json
      upload-sarif: 'true'
```

Fastest start: the [micar-whitepaper-template](https://github.com/sebastianfoerste/micar-whitepaper-template) repo ships this workflow preconfigured — click **Use this template**.

The canonical template source lives at `templates/whitepaper-starter` in this repository. The public template repository remains the release surface. Run `make template-check` to validate its JSON and workflow contract, then `make template-export` to prepare a local path-export branch for human review. The export command never pushes.

## Reviewer route

For a short proof review:

1. Read `docs/launch-readiness.md`.
2. Read `docs/sample-review-bundle.md`.
3. Read `studies/2026-07-title-ii-annex-i-whitepaper-study/findings-summary.md`.
4. Inspect `src/micar_linter/rules/`.
5. Run `make check`.

This route keeps the human-review boundary visible while showing the deterministic rules, synthetic examples, and 2026 study methodology.

## Features

- Deterministic regulatory audits for MiCAR Annex I, II and III.
- JSON, XHTML and DOCX parsing.
- Rules-as-code severity engine.
- JSON reports for automated checks.
- Local artifact manifests and remediation reports.
- Coverage matrices, review tables and batch packs.
- Review table export: rule-by-rule rows with blocker status, citations, remediation, reviewer decision state and bundle export eligibility.
- Workspace export: `--workspace-output <path>` writes a local batch vault, conditional review table and reusable review playbook. Open blockers keep filing and external-review readiness disabled.

See also [FEATURES.md](FEATURES.md), [SETUP.md](SETUP.md), [ARCHITECTURE.md](ARCHITECTURE.md).

## Verified behaviour

MiCAR white-paper requirements can be encoded as deterministic, cited and testable rules. Annex selection is explicit, rule IDs are stable, unmatched disclosure patterns produce cited candidate flags, severity is tested, and JSON outputs can be used by review workflows without hiding the legal basis.

The tool preserves legal judgment. It flags candidate disclosure gaps and produces draft review artifacts. It does not decide whether a white paper is lawful or complete.

The reserve-floor check extracts percentage candidates and identifies the potentially applicable threshold under Articles 35(4), 36(4)(d), 45(3) and 45(7)(b) MiCAR from draft characterisation fields. It never returns `PASS`: applicability and any legal conclusion remain subject to lawyer confirmation.

## Tech stack

Python, Hatchling, uv and pytest.

## Verification checklist

- Run `make check`.
- Run `uv run micar-lint examples/art-stablecoin.json`.
- Run `uv run micar-lint examples/incomplete.json`.
- Generate a review bundle from a synthetic example.
- Confirm fixture labels are synthetic.
- Confirm report output states that the tool is not legal advice.

## Collaborative redline bundle

Run `micar-lint <draft> --workspace-output workspace.json --collaboration-bundle-dir review/` to generate a digest-bound collaboration sidecar, MiCAR playbook change set and supervised workflow pack. Accepted changes can be rendered as genuine OOXML tracked insertions and deletions in a copied DOCX. The source draft is never overwritten.
