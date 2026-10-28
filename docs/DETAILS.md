# Detailed usage and reference

Long-form detail moved out of the README. Everything here was in the previous README.

## Browser workbench

The full linter runs client-side via Pyodide. Nothing you paste leaves the page.

The browser workbench accepts JSON drafts up to 1 MB and XHTML white papers up to 8 MB, includes synthetic examples for all three regimes, and presents searchable findings with citations and section navigation. Download the current report as JSON or text, or save a copy of the draft. Editing a checked draft marks the previous results as stale and disables report export until the checks run again. Python runs in a web worker so the editor stays responsive.

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
make check      # ruff, pytest, CLI smoke, review bundle, playground and template checks
```

Generate a review bundle from synthetic data:

```bash
uv run --extra dev python -m micar_linter examples/incomplete.json --review-bundle-dir /tmp/micar-incomplete-review-bundle
```

Check an XHTML white paper in the numbered-field layout of Implementing Regulation (EU) 2024/2984 ("A.1 Name", "A.2 Legal form"). State the regime, because it is not inferred from the text of such a file:

```bash
uv run micar-lint examples/numbered-other-draft.xhtml --type other
```

A saved iXBRL viewer page packs the white paper into a script and shows it only when a browser runs that script. The linter unpacks it in memory (gzip, zlib, raw deflate or uncompressed, up to 8 MB) and checks the white paper it carries; a page in the numbered-field layout still needs `--type`. Its `COMMON.IXBRL_TAGGING` result stays Missing, because the viewer's rendering is not the XHTML document itself, and its findings point at line 1. A page that cannot be unpacked, unpacks to more than 8 MB, or packs more than one document stops with exit 1 and a message.

## Coverage caveats

The Table 2 mapping (crypto-assets other than ARTs and EMTs) has been run against public register documents. The Table 3 and Table 4 mappings follow the Official Journal text and have not yet been run against a real ART or EMT white paper. The iXBRL check tests well-formedness, the Inline XBRL 1.1 namespace and the ESMA MiCA taxonomy namespace. It does not evaluate the taxonomy's existence and value assertions, so it never reports Pass. For a saved iXBRL viewer page it does not run at all and reports Missing.

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
| `whitepaper` | required | Path to a JSON, XHTML or HTML, DOCX, PDF or Markdown draft (DOCX from v1.2.0) |
| `strict` | `true` | Fail the job while BLOCKER findings are open |
| `extra-args` | `''` | More CLI arguments, e.g. `--json`, `--lang de`, or `--type art` for a draft that is not JSON |
| `summary` | `true` | Append a table of open findings to the job summary: rule, status, severity, citation, `file:line`, rule page |
| `annotations` | `true` | Annotate up to 10 open findings on the draft file (open blockers first) |
| `upload-sarif` | `false` | Upload a SARIF log to GitHub code scanning |

Output: `sarif-file`, the path of the SARIF log, for other uploaders such as reviewdog.

Versions: `@v1` follows the latest 1.x release. From v1.2.0, one tag such as `v1.2.0` marks both the Action and the PyPI package of the same version. The tags `v0.1.0` to `v0.2.1` mark package releases from before that; they are not Action versions, so do not use them in a workflow.

The job fails while BLOCKER-severity findings are open. The iXBRL format check (`COMMON.IXBRL_TAGGING`) is a BLOCKER that never passes for a loaded draft: a JSON, DOCX, PDF or Markdown draft cannot meet it, and an XHTML or HTML draft stays at review because tag completeness is not checked. A strict job therefore fails on every draft; `strict: 'false'` (report mode) lists the findings without failing. A failing job means open blockers to review, or a draft that could not be loaded, not a legal conclusion. The summary, annotations and SARIF log carry rule IDs, statuses, citations and line numbers, never draft text or the draft title, and they change no status or exit code. The job log still prints the full text report, which includes the draft title and quoted figures such as reserve percentages; treat the log as being as sensitive as the draft. The `summary`, `annotations` and `upload-sarif` inputs and the `sarif-file` output need v1.2.0 or later. The iXBRL format check never passes, so it is listed in its own summary section and not annotated.

Line numbers point at the section key in a JSON draft or the first `h1` to `h6` heading that maps to the section in an XHTML or HTML draft; numbered-field XHTML, saved iXBRL viewer pages, DOCX, PDF, Markdown and sections with no matching `h1` to `h6` heading point at line 1.

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

Fastest start: the [micar-whitepaper-template](https://github.com/sebastianfoerste/micar-whitepaper-template) repo ships a preconfigured workflow in report mode (`strict: 'false'`). Click **Use this template**.

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

- Deterministic first-pass checks for MiCAR Annex I, II and III.
- JSON, XHTML or HTML, DOCX, PDF and Markdown parsing.
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

## Example output

Real output of `uv run micar-lint examples/incomplete.json` (a synthetic, deliberately incomplete ART draft), first three findings only:

```text
MiCAR Whitepaper Linter - Incomplete Synthetic EuroStable ART Draft
Whitepaper type: ART
==============================================================================
Pass: 0  |  Review: 14  |  Missing: 6  |  Blockers: 15

[REVIEW] [BLOCKER] COMMON.SUMMARY  Plain-language summary
           Cite:  Art. 6(7), Art. 19(6), Art. 51(6) MiCAR
           Text:  https://eur-lex.europa.eu/eli/reg/2023/1114/oj/eng
           Section: 'summary'  (4 words)
           -  Section is thin: 4 words, expected at least 80.
           -  Missing review terms: summary, key information.

[MISS  ] [BLOCKER] COMMON.RISK_WARNING  Mandatory risk warning statement
           Cite:  Art. 6(5), Art. 19(4), Art. 51(4) MiCAR
           Text:  https://eur-lex.europa.eu/eli/reg/2023/1114/oj/eng
           Section: 'risk_warning'  (0 words)
           -  Section is empty or absent.

[REVIEW] [BLOCKER] COMMON.MANAGEMENT_STATEMENT  Statement by the management body on completeness, fairness, and clarity
           Cite:  Art. 6(6), Art. 19(5), Art. 51(5) MiCAR
           Text:  https://eur-lex.europa.eu/eli/reg/2023/1114/oj/eng
           Section: 'management_statement'  (1 words)
           -  Section is thin: 1 words, expected at least 40.
           -  Missing review terms: management body, complies, fair, clear, not misleading.
...
```

(The `...` marks where the remaining findings and the footer were cut. Citations print in English EU style with a link to the act on EUR-Lex; `--citation-style de` prints the German form, e.g. "Art. 6 Abs. 7 MiCAR". `--json` carries both, plus the links.) XHTML in the numbered-field layout of Implementing Regulation (EU) 2024/2984 works too; state the regime, since it is not inferred:

```bash
uv run micar-lint examples/numbered-other-draft.xhtml --type other
```
