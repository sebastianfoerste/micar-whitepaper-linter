# 0005. Point-level rule IDs

Status: Proposed

## Context

Rules work at Annex Part level, with four `ANNEX_II.G.*` topic rules and `ANNEX_II.I` citing points. The study uses separate IDs such as `ANNEX_I_PART_A_02_LEGAL_FORM` (`batch.py`). Filing tools check individual numbered fields of Implementing Regulation (EU) 2024/2984 (WhitePaperXBRL, Observed). Rule IDs are stable and may only be added.

## Options

1. Reuse the study IDs.
2. Dot-separated point IDs under each Part: `ANNEX_I.A.P2` for Annex I, Part A, point 2.
3. Field-number IDs from the template tables: `T2.A.2`.

## Decision (proposed)

Option 2. The `P` prefix cannot collide with the `ANNEX_II.G.<TOPIC>` names (no topic starts with `P` followed by a digit) or with the underscore-separated study IDs. Part-level rules stay as they are. Every new point citation must be verified on EUR-Lex with a retrieval date before it is added; none were added in this run because EUR-Lex was unreachable.

## Consequences

More findings per report; rule pages and SARIF rules grow accordingly (generated, no extra work).

## Non-negotiables check

Existing IDs unchanged; citations verified before use; synthetic fixtures only.
