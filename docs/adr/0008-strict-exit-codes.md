# 0008. Exit codes of `--coverage --strict` and strict directory runs

Status: Accepted (2026-11-10). Proposed on 2026-11-02 because the behaviour below was built and released without an owner decision. On 2026-11-10 the owner delegated the decision, and option 1 was taken for all three changes.

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

`--coverage` with `--review-bundle-dir` never took the early return and is unchanged. In the GitHub Action, `strict: 'true'` with `--coverage` in `extra-args`, or a directory input that holds a numbered-field draft or no supported draft, now fails the job; the starter template sets `strict: 'false'`.

## Options

1. **Confirm.** Keep the behaviour of 1.2.0: `--coverage` changes only what is printed, and a strict directory run fails on a file that could not be linted and on a run that linted nothing. This ADR becomes Accepted, and `CHANGELOG.md` keeps the entries under 1.2.0.
2. **Revert both.** `--coverage` returns 0 before the output files and `--strict` again, and a strict directory run exits 0 on a failed file or an empty run. This reopens the gap that let `--coverage` in the Action's `extra-args` turn off the strict gate and the CI outputs, and lets "nothing was checked" pass a strict gate.
3. **Revert in part.** For example, keep the `--coverage` fix, whose exit code changes only when `--strict` is also given, and revert the directory exit codes, or the other way round.

## Decision

Option 1, for each of the three changes: `--coverage --strict`, a strict directory run with a file that could not be linted, and a strict directory run that linted no file. Decided on 2026-11-10 under the owner's delegation.

Reasons:

- `--strict` is the gate a CI job relies on. It has to fail when blockers are open, when a file given to it could not be linted and when nothing was linted. The earlier codes let a run pass that gate with open BLOCKER findings (`--coverage --strict`), with a file it could not lint, or with no file linted at all, and `--coverage` in the Action's `extra-args` also dropped the CI output files.
- Releases 1.2.0 and 1.2.1 already behave this way, and `@v1` users of the Action run them. A revert would be a second exit-code change for those users within the same major version, this time in the fail-open direction.
- Without `--strict` no exit code changed: those runs exit 0 as before.

## Consequences

- No code changes. The tests in `tests/test_fail_closed_fixes.py` (`test_coverage_keeps_strict_and_output_files`, `test_batch_counts_files_it_could_not_lint_and_strict_fails_on_them`, `test_strict_batch_fails_when_no_file_was_linted`) keep pinning the three exit codes, and `docs/API.md` already describes them.
- `CHANGELOG.md` keeps the entries under 1.2.0 "Fixed". The commands in section 3 of `AGENTS.md` and item 11 of "Needs owner decision" in `docs/research/adaptation-plan.md` now point to this decision.
- Changing any of the three later would need a new record: it would be an exit-code change for `@v1` users.

## Non-negotiables check

- Exit codes: this record confirms the released codes and changes none.
- Fail closed: option 1 keeps the strict gate closed when output files are requested with `--coverage` and when a directory run checked nothing; options 2 and 3 would have opened it again in the cases they revert.
- No model and no network in the checking path; synthetic examples only.
