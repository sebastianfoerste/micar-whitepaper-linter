# 0010. A sign-off file for the never-pass gates of `--strict`

Status: Accepted (2026-11-25). The owner chose option 2 on 2026-11-25 (rank 9 and section 6 of the [competitive update](../research/2026-11-competitive-update.md)).

## Context

Two BLOCKER rules never pass for a loaded draft: `COMMON.IXBRL_TAGGING`, because the linter does not validate the iXBRL tags (ADR 0004 keeps it never-pass even with taxonomy assertions), and `ANNEX_II.G.DEPOSIT_FLOOR_REVIEW`, which leaves a reserve floor to a lawyer. `Report.blockers` counts every BLOCKER finding that has not passed, so `--strict` exits 1 for every white paper, the fullest synthetic example included. The starter workflow therefore runs with `strict: 'false'`, and a team that wants a strict CI gate has none that can turn green.

The adaptation plan of October 2026 named a human approval that turns a status green as an anti-pattern and set the principle that a waiver shows `waived`, never `pass`, and keeps the exit code. ADR 0008 confirmed when `--strict` fails. The draft itself cannot be trusted to certify anything: the JSON loader forces `ixbrl_validated` to false, and reviewer fields in a draft are ignored.

## Options

1. **Keep it.** `--strict` stays a permanent "not ready" signal for white papers.
2. **An opt-in sign-off file outside the draft, bound to the file's SHA-256.** A reviewer records that a never-pass gate was checked outside the linter for this exact file. The finding keeps its status; `--strict` stops counting it.
3. **A flag that skips the gates.** No reviewer, no record and no binding to a file version, so a CI job could pass without anyone checking the iXBRL file or the reserve floor.

## Decision

Option 2, decided by the owner on 2026-11-25. It revises the October principle for these two gates only: a waiver still never shows `pass`, but an acknowledged gate no longer fails `--strict`.

- **File.** `--signoff PATH`, JSON with `"schema": "micar-whitepaper-linter.signoff.v1"` and a non-empty `acknowledgements` list. Each entry holds `rule_id` (one of the two gates; any other rule exits 2, so no content finding can be waived), `sha256` (the 64 lower-case hex digits of the linted file), `reviewer` and `note` (non-empty, no placeholder) and `date` (an existing date written YYYY-MM-DD). A file that breaks the schema exits 2 (`signoff.py`).
- **Binding.** An entry applies only where its `sha256` equals the SHA-256 of the file as linted and the report has an open finding of that rule. Otherwise the report adds a warning that it does not apply, and nothing else changes, so any edit to the draft voids every acknowledgement.
- **Effect.** The finding keeps its status (`missing` or `review`). `Report.acknowledged` holds the applied entries and `Report.open_blockers` leaves their rules out; `--strict` reads `open_blockers`. `Report.blockers` and every count built on it stay as they were.
- **Outputs.** The text report adds "(N acknowledged)" to the blocker count, a line under each acknowledged finding with the reviewer, the date and the note, and, when only acknowledged gates remain open, a closing sentence that says so and that the other open items and a lawyer's sign-off still apply. The JSON report adds `acknowledged` (the entries) and `summary.open_blockers`. SARIF marks each acknowledged result with `properties.acknowledged` and lists the rule IDs under the run's `properties.acknowledged`; the job summary marks the rows and the format-gate note and counts them; annotations leave them out. CI outputs name no reviewer and repeat no note, so they stay free of personal data and byte-reproducible. Without `--signoff`, every output is unchanged.
- **Scope.** One white paper file. Directories, several paths, `--compare-review-table-output`, the workspace, collaboration and workflow modes and `--marketing` exit 2 with `--signoff`. The review table, bundle, audit log, coverage, remediation and manifest outputs do not show acknowledgements yet and list the gate as open.

## Consequences

- The exit code of `--strict` changes only when `--signoff` is given, so `@v1` users of the Action see no change until they add it, for example through `extra-args: --signoff signoff.json`. The starter workflow keeps `strict: 'false'`.
- A team keeps the sign-off file next to the draft in its repository and renews each entry after every change to the draft. The file names reviewers, so a team that does not want names in its repository can use a role.
- Wording that describes the gates as never passing stays true: the rule pages of the two gates add that a sign-off file can acknowledge their open finding for one file version.

## Non-negotiables check

- Fail closed: the gates still never pass; only a matching entry from outside the draft, for this file version, keeps `--strict` from counting them, and a content blocker can never be acknowledged.
- No draft self-certification: the draft cannot carry the sign-off, and a JSON draft still cannot set `ixbrl_validated`.
- No model and no network call: the file is read and hashed locally.
- Outputs without draft text: CI outputs add rule IDs and fixed sentences only.
