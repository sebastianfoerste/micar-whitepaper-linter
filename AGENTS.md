# Agent Guide: MiCAR Whitepaper Linter

Welcome, AI Agent! This guide details conventions, directory mapping, and rules safety for the `micar-whitepaper-linter` workspace.

---

## 1. Project Purpose
The MiCAR Whitepaper Linter is a deterministic Python package that screens draft crypto-asset white papers under the Markets in Crypto-Assets Regulation (MiCAR - Regulation (EU) 2023/1114). It flags candidate disclosure gaps against Annexes I, II and III, each with a citation. It is first-pass tooling for lawyer review: it does not decide whether a white paper is compliant, and its output says it is not legal advice. It runs as a CLI (`micar-lint`), as a GitHub Action (`action.yml`) and in a browser playground (`docs/playground/`, on Pyodide).

---

## 2. Directory Layout
- `src/micar_linter/`: Core source package.
  - `rules/`: Rule definitions. `annex_i.py`, `annex_ii.py` and `annex_iii.py` hold the Annex I, II and III rules. `common.py` holds the rules every white paper type runs (summary, risk warning, management statement, notification date, language, the iXBRL format gate and the LEI checks). `base.py` defines `Severity`, `Rule` and `Finding`. `__init__.py` builds `RULESETS`: the common rules plus Annex I for `other`, Annex II for `art` and Annex III for `emt`.
  - `linter.py`: `Linter`, `Report` and `lint_whitepaper`, plus the logic of the rules that are not generic checks.
  - `whitepaper.py`: the `Whitepaper` input model, the `WhitepaperType` regimes and `load_whitepaper`, which dispatches by file suffix.
  - `document.py`: PDF, DOCX and Markdown section extraction, and the heading-to-section matching the loaders share.
  - `xhtml_parser.py`: XHTML text extraction and heading-based section mapping. `numbered_fields.py` handles white papers in the numbered-field layout of Implementing Regulation (EU) 2024/2984.
  - `ixbrl.py`: Inline XBRL format checks (the iXBRL 1.1 namespace and facts tagged with the ESMA MiCA taxonomy). It does not check tag completeness.
  - `lei.py`: LEI format, check digits and party sections, used by the two LEI rules.
  - `report.py`: Renders a `Report` as text, JSON, a Markdown audit log or a coverage table. Other outputs have their own modules: `ci_outputs.py` (SARIF, job summary, annotations), `review_table.py`, `review_bundle.py`, `remediation.py`, `coverage.py` and `artifact_manifest.py`.
- `tests/`: Pytest tests (`test_*.py`) and Node tests for the playground (`tests/playground/*.test.mjs`). Pytest does not run the Node tests; `make playground-check` does.
- `examples/`: Synthetic inputs with fictional issuers (JSON, XHTML, DOCX). They contain no real issuer data.
  - `art-stablecoin.json`, `emt-token.json` and `other-crypto-asset.json` are full drafts with fictional `SYNTH` LEIs. Each still has open blockers, the iXBRL format gate among them, so `--strict` exits 1.
  - `incomplete.json` is deliberately incomplete.
  - `numbered-other-draft.xhtml` uses the numbered-field layout and needs `--type other`.
  - `review-bundle/` is a committed sample output (see section 6).
- `docs/`: The GitHub Pages root: landing page, `playground/`, generated `rules/`, `adr/` (architecture decisions) and `research/`.
- `scripts/`: Generators and checks. `templates/whitepaper-starter/`: source of the starter template. `action.yml`: the GitHub Action.

---

## 3. Important Development Commands
Ensure you run commands using `uv` or inside your virtual environment. `make check` needs Python 3.13 or later and Node.js 22 or later.
- `make check`: Run ruff, pytest, the CLI smoke run and the review-bundle build (through `uv run --extra dev`), then the playground checks (`node --check`, `node --test`) and the starter-template check (with the system `python3`).
- `uv run micar-lint <file>`: Run linter against a document. XHTML in the numbered-field layout needs `--type other|art|emt`. DOCX needs the `docx` extra, e.g. `uv run --extra docx micar-lint draft.docx`.
- `uv run --extra dev pytest`: Run test suite with dev tooling available.
- `uv run --extra dev ruff check src tests`: Lint code with dev tooling available.

---

## 4. Coding Conventions
- **Regulatory Rules**: centralize all rules in [src/micar_linter/rules/](src/micar_linter/rules/). Each rule is an instance of the frozen `Rule` dataclass in `rules/base.py`; there is no `BaseRule` class to inherit from. `Linter` in `linter.py` applies the generic checks (listed terms, required and prohibited patterns, minimum words, with German variants for German drafts), and dispatches by rule ID the rules that need their own logic.
- **Rules with their own logic**: besides the dispatch in `linter.py`, add the rule ID to the special-case sets and examples in `scripts/build_rule_docs.py`. If its issue messages can quote draft text, add it to `DRAFT_ECHO_RULES` in `ci_outputs.py`, so SARIF, the job summary and annotations never repeat the draft.
- **Fail Closed**: Compliance checks must fail closed on missing sections. `COMMON.IXBRL_TAGGING` and `ANNEX_II.G.DEPOSIT_FLOOR_REVIEW` never return pass.
- **Stable rule IDs**: add new rule IDs, never rename existing ones. They key SARIF results, the rule-page URLs and review bundles.
- **Report language is load-bearing** (CONTRIBUTING.md): the blocker and lawyer sign-off wording is tested. Never describe a pass as compliance.
- **Synthetic data only**: no real white paper, issuer, IBAN or wallet content anywhere in the repository (CONTRIBUTING.md).

---

## 5. Files to Protect
Do not casually modify:
- `src/micar_linter/rules/base.py`: Core rule data types (`Severity`, the frozen `Rule` dataclass, `Finding`) that the whole package imports.
- `pyproject.toml` and `uv.lock`: Build and lock configs. CI installs with `uv sync --locked`.

---

## 6. Generated and Committed Outputs
Do not edit these by hand. Regenerate them after the change that affects them:
- `docs/rules/*.html`: run `uv run python scripts/build_rule_docs.py` after any rule change. `tests/test_rule_docs.py` fails on stale pages and lints every example on them.
- `docs/playground/micar_whitepaper_linter-<version>-py3-none-any.whl`: after any change under `src/`, delete the wheel and run `uv build --wheel -o docs/playground/`. `tests/test_playground_wheel.py` checks that it matches the source, the project version and `docs/playground/index.html`. A local, untracked `docs/playground/.gitignore` containing `*` hides new files in that folder from `git status`; use `git add -f` for a wheel with a new name.
- `docs/playground/samples.json` and `docs/playground/sample-numbered.xhtml`: run `make playground-samples` after editing the examples they are built from.
- `examples/review-bundle/` and `reports/sample-*.txt`: committed sample outputs that tests read. No make target regenerates them.
- The version appears in `pyproject.toml`, `src/micar_linter/__init__.py`, `CITATION.cff`, the playground wheel's filename and `docs/playground/index.html`.

---

## 7. Git and Branching Rules
Do not merge feature branches into `main`, `master` or `develop`, and do not push to those remote branches, unless the user approved it in the current session or the change goes up as a pull request for review. These branches deploy; an unreviewed merge cannot be recalled.

Before proposing a merge or push, run `make check` on the feature branch. It runs ruff, the pytest suite (which asserts several of the `*.v1` output schema identifiers), the CLI smoke run, the review bundle, the playground checks and the starter-template contract. CI runs only on pushes and pull requests to `main`, so on a feature branch `make check` is the only gate. The project has no database, so there are no migrations to validate.
