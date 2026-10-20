# 0004. Arelle as an optional CLI extra for taxonomy assertions

Status: Proposed

## Context

Tag completeness is defined by the existence and value assertions of the ESMA MiCA taxonomy's formula linkbase, which this repo does not evaluate. Arelle (Apache-2.0) supports offline runs (`--internetConnectivity offline`, `--packages`, `--formula run`) (Observed in source). It has no MiCA plugin and issue #1898 for the MiCA reporting-manual rules is open (Observed). `arelle-release` 2.46.1 is a 6.1 MB pure-Python wheel but requires `lxml!=6.0.0`; Pyodide 0.28.2 ships only lxml 6.0.0 (Observed), so it cannot run in the playground as pinned.

## Options

1. Do nothing; keep pointing users to a taxonomy validator.
2. An optional `arelle` extra, CLI-only: `micar-lint draft.xhtml --taxonomy-package PATH` runs the assertions offline against a package the user downloads. The repo never commits a taxonomy.
3. Re-implement assertions in Python (as WhitePaperXBRL does in TypeScript, Observed).

## Decision (proposed)

Option 2, subject to the owner's decisions:
- `COMMON.IXBRL_TAGGING` stays never-pass. Assertion failures are listed as its issues, or as new rule IDs with their own statuses; a clean assertion run is still not a pass of the format gate.
- A new extra changes `pyproject.toml` and `uv.lock` and needs this ADR accepted first.

## Consequences

Heavier install for users who opt in; filing-rule (reporting manual) checks are still absent because Arelle has none for MiCA.

## Non-negotiables check

No network at run time (offline flag). No change to the never-pass rule. Locked dependencies changed only after acceptance.
