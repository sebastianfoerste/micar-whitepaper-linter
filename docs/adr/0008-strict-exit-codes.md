# 0008. Exit codes of `--coverage --strict` and strict directory runs

Status: Proposed (2026-11-02). **Needs owner decision: confirm or revert.** The behaviour described below is built and released; it was never decided by the owner as an exit-code change.

## Context

Any change to a severity, a status or an exit code is an owner decision. Two commits changed exit codes without one:

- 06d0f46 (2026-10-25, "fix: keep --coverage, batch runs and the Action fail-closed"): `--coverage` without `--review-bundle-dir` printed its table and returned 0 before the output files were written and before `--strict` was applied. It now replaces only the printed report. The same commit added `failed_files` to the directory batch summary and made `--strict` exit 1 when a file could not be linted.
- 85d81d8 (2026-10-25, "fix: fail a strict directory run that linted no file"): `--strict` on a directory exits 1 when no file was linted.

Both reached `main` with PR #30 (merged 2026-10-26) and are in releases 1.2.0 and 1.2.1, so `@v1` users of the Action run them. `CHANGELOG.md` lists them under 1.2.0 "Fixed". No ADR records them, and the "Needs owner decision" list in `docs/research/adaptation-plan.md` did not name them. The post-verification audit of 2026-11-02 found the record missing. The changes move in the fail-closed direction, but a `--strict` run in CI can now fail where it passed before.

Measured with `python -m micar_linter` on the source before 06d0f46 and on `main` at c7c99cf (`examples/incomplete.json` has open BLOCKER findings; the numbered-field draft is `examples/numbered-other-draft.xhtml`, which a directory run cannot lint because it needs `--type`):

| Run | Before 06d0f46 (package 0.2.1, Action 1.1.1 and earlier) | 1.2.0, 1.2.1 and `main` |
|---|---|---|
| `incomplete.json --coverage --strict --sarif-output r.sarif` | exit 0, no output file written | exit 1, `r.sarif` written |
| `incomplete.json --coverage --sarif-output r.sarif` | exit 0, no output file written | exit 0, `r.sarif` written |
| `incomplete.json --strict --sarif-output r.sarif` | exit 1, `r.sarif` written | unchanged |
| Directory holding only numbered-field XHTML, `--batch-output b.json --strict` | exit 0 (the file was in no count) | exit 1 (`failed_files: 1`) |
| Empty directory, `--batch-output b.json --strict` | exit 0 | exit 1 |
| Either directory without `--strict` | exit 0 | unchanged |

Since ADR 0009 (2026-11-11), a numbered-field draft that declares its type in the type field of the template (F.4 OTHR, B.7 ARTW, B.4 EMTW) is linted without `--type`, also in a directory run, so it no longer counts in `failed_files`; the rows above concern a numbered-field draft without such a field, as `examples/numbered-other-draft.xhtml` is, and their exit codes are unchanged.

`--coverage` with `--review-bundle-dir` never took the early return and is unchanged. In the GitHub Action, `strict: 'true'` with `--coverage` in `extra-args`, or a directory input that holds a numbered-field draft or no supported draft, now fails the job; the starter template sets `strict: 'false'`.

## Options

1. **Confirm.** Keep the behaviour of 1.2.0: `--coverage` changes only what is printed, and a strict directory run fails on a file that could not be linted and on a run that linted nothing. This ADR becomes Accepted, and `CHANGELOG.md` keeps the entries under 1.2.0.
2. **Revert both.** `--coverage` returns 0 before the output files and `--strict` again, and a strict directory run exits 0 on a failed file or an empty run. This reopens the gap that let `--coverage` in the Action's `extra-args` turn off the strict gate and the CI outputs, and lets "nothing was checked" pass a strict gate.
3. **Revert in part.** For example, keep the `--coverage` fix, whose exit code changes only when `--strict` is also given, and revert the directory exit codes, or the other way round.

## Decision

None yet. The code keeps the released behaviour of option 1 until the owner decides; nothing here approves it. The owner confirms or reverts each of the three changes: `--coverage --strict`, a strict directory run with a file that could not be linted, and a strict directory run that linted no file.

## Consequences

- If confirmed: change this record's status to Accepted with the date; no code changes.
- If reverted, in whole or in part: change `main` and `_run_batch` in `src/micar_linter/cli.py`, the tests that pin the current codes in `tests/test_fail_closed_fixes.py` (`test_coverage_keeps_strict_and_output_files`, `test_batch_counts_files_it_could_not_lint_and_strict_fails_on_them`, `test_strict_batch_fails_when_no_file_was_linted`), the `--strict` and `--coverage` help texts, `docs/API.md`, `docs/SETUP.md`, the commands in section 3 of `AGENTS.md`, `CHANGELOG.md` and the playground wheel. A revert is itself an exit-code change for 1.2.x users.

## Non-negotiables check

- Exit codes: this record asks for the owner's decision and changes none.
- Fail closed: option 1 keeps the strict gate closed when output files are requested with `--coverage` and when a directory run checked nothing; options 2 and 3 open it again in the cases they revert.
- No model and no network in the checking path; synthetic examples only.
