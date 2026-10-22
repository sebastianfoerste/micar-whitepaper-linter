# Agent Guide: MiCAR Whitepaper Linter

Welcome, AI Agent! This guide details conventions, directory mapping, and rules safety for the `micar-whitepaper-linter` workspace.

---

## 1. Project Purpose
The MiCAR Whitepaper Linter is a deterministic Python tool and command-line package designed to validate draft crypto-asset white papers under the Markets in Crypto-Assets Regulation (MiCAR - Regulation (EU) 2023/1114).

---

## 2. Directory Layout
- `src/micar_linter/`: Core source package.
  - `rules/`: Checklist files mapping Annex I, II, and III.
  - `ixbrl.py` & `xhtml_parser.py`: iXBRL tag extraction.
  - `document.py` & `whitepaper.py`: Logical structure models.
  - `report.py`: Compile final logs.
- `tests/`: Pytest tests files.
- `examples/`: Synthetic example drafts, complete and incomplete. They contain no real issuer data.

---

## 3. Important Development Commands
Ensure you run commands using `uv` or inside your virtual environment:
- `make check`: Run lint, tests, and the sample CLI smoke check with dev tooling.
- `uv run micar-lint <file>`: Run linter against a document.
- `uv run --extra dev pytest`: Run test suite with dev tooling available.
- `uv run --extra dev ruff check src tests`: Lint code with dev tooling available.

---

## 4. Coding Conventions
- **Regulatory Rules**: centralize all rules in [src/micar_linter/rules/](src/micar_linter/rules/). Each rule is an instance of the frozen `Rule` dataclass in `rules/base.py`; there is no `BaseRule` class to inherit from. `Linter` in `linter.py` applies the generic checks (listed terms, patterns, minimum words), and dispatches by rule ID the rules that need their own logic.
- **Fail Closed**: Compliance checks must fail closed on missing sections.

---

## 5. Files to Protect
Do not casually modify:
- `src/micar_linter/rules/base.py`: Core rule validator interface.
- `pyproject.toml` and `uv.lock`: Build and lock configs.

---

## 6. Git and Branching Rules
Do not merge feature branches into `main`, `master` or `develop`, and do not push to those remote branches, unless the user approved it in the current session or the change goes up as a pull request for review. These branches deploy; an unreviewed merge cannot be recalled.

Before proposing a merge or push, run `make check` on the feature branch. It runs ruff, the pytest suite (which also asserts the `*.v1` output schema identifiers), the CLI smoke run, the review bundle, the playground checks and the starter-template contract. The project has no database, so there are no migrations to validate.

