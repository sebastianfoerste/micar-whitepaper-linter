# Architecture decision records

| ADR | Title | Status |
|---|---|---|
| [0001](0001-ci-outputs-sarif-mapping.md) | CI outputs: SARIF mapping, summary and annotations | Accepted |
| [0002](0002-generated-rule-pages.md) | Generated rule pages with executed examples | Accepted |
| [0003](0003-playground-editor.md) | Playground editor and section highlighting | Proposed |
| [0004](0004-arelle-optional-extra.md) | Arelle as an optional CLI extra for taxonomy assertions | Proposed |
| [0005](0005-point-level-rule-ids.md) | Point-level rule IDs | Proposed (option chosen 2026-10-28, open point settled 2026-10-29, first rules built 2026-10-30) |
| [0006](0006-shared-site-tokens.md) | Shared site tokens (light theme; dark theme removed 2026-10-21) | Accepted |
| [0007](0007-lei-rules.md) | LEI check-digit and consistency rules | Accepted |
| [0008](0008-strict-exit-codes.md) | Exit codes of `--coverage --strict` and strict directory runs | Proposed (needs owner decision: confirm or revert) |

Each record has Status, Context, Options, Decision, Consequences and a non-negotiables check. "Accepted" records describe code in this repository; "Proposed" records describe nothing built yet, except ADR 0005, whose first point rules (`ANNEX_I.A.P6`, `ANNEX_III.A.P6`) are built, and ADR 0008, which records exit codes that releases 1.2.0 and 1.2.1 already have and that await the owner's decision.
