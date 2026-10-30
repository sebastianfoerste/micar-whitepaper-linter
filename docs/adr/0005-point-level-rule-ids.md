# 0005. Point-level rule IDs

Status: Proposed. The owner chose the option below on 2026-10-28. The first point rules, `ANNEX_I.A.P6` and `ANNEX_III.A.P6`, were built on 2026-10-30.

## Context

Rules work at Annex Part level, with four `ANNEX_II.G.*` topic rules. In releases 1.2.0 and 1.2.1 only `ANNEX_II.I` cites Annex points. Since 2026-10-29, `main` also has `ANNEX_II.G.COMPOSITION_DISCLOSURE` (Annex II Part G points 1 and 2), `ANNEX_II.G.VALUATION_AUDIT` (Annex II Part D point 10), `ANNEX_III.SAFEGUARDING` (Annex III Part D point 3) and the two LEI rules (point 5 of each party Part) citing points. Each of these still checks whole sections, not numbered fields. The study uses separate IDs such as `ANNEX_I_PART_A_02_LEGAL_FORM` (`batch.py`). Filing tools check individual numbered fields of Implementing Regulation (EU) 2024/2984 (WhitePaperXBRL, Observed). Rule IDs are stable and may only be added.

Since 23 December 2025 (Art. 4 of that Regulation) a white paper follows Table 2, 3 or 4 of its Annex. The tables carry the Annex points as numbered fields, and some fields apply only under a condition the Annex point does not state. In Table 2, legal form, registered address, head office and parent company (A.2 to A.4, A.11) are filled in only if field A.6 gives no LEI (recital 2), and the crypto-asset's name, abbreviation and DLT (D.2, D.3, H.1) only if field F.13 gives no DTI (recital 4). Tables 3 and 4 have conditions of the same kind. A Part-level rule cannot see them. In releases 1.2.0 and 1.2.1, on a Table 2 draft with an LEI in A.6 and A.2 to A.4 marked N/A, `ANNEX_I.A` reports a BLOCKER at Review ("Missing review terms: legal form, registered"). Since 2026-10-29 the party rules on `main` no longer ask for the legal form or the registered address. `ANNEX_I.A` therefore passes that draft once Part A names a postal address elsewhere, such as the business addresses of the management body in A.12. It passes the same way when A.6 gives no LEI and A.2 to A.4 are N/A, and only the LEI rules then show Review. In both versions, a Part A whose response time (A.10) reads TBD passes it.

## Options

1. Reuse the study IDs.
2. Dot-separated point IDs under each Part: `ANNEX_I.A.P2` for Annex I, Part A, point 2.
3. Field-number IDs from the template tables: `T2.A.2`.

## Decision

Option 2, checked against the template fields. The owner chose it on 2026-10-28.

- Each new rule is keyed to one Annex point (`ANNEX_I.A.P2`) and cites that point, so the legal benchmark stays Art. 6(1), 19(1) or 51(1) MiCAR with the Annex. The `P` prefix cannot collide with the `ANNEX_II.G.<TOPIC>` names (no topic starts with `P` followed by a digit) or with the underscore-separated study IDs.
- For each regime the rule names the field or fields of Table 2, 3 or 4 that carry the point and checks those fields in a numbered-field draft.
- The rule applies the template's own conditions. A field that applies only if no LEI or DTI is given, or only if a flag is true, is not reported missing when the draft gives the LEI or DTI or the flag is false, and the finding names the condition.
- Part-level rules stay as they are.
- Every point citation and field mapping is checked against the Official Journal text, with the retrieval date, before it is added. Where EUR-Lex refuses automated retrieval, the Publications Office Cellar serves the same text (`https://publications.europa.eu/resource/celex/32023R1114` and `.../32024R2984` with the header `Accept: application/xhtml+xml`).

How a point rule reads a draft without the numbered-field layout (JSON, DOCX, PDF, Markdown, and XHTML or HTML in the heading layout), where no field numbers exist, was settled by the owner on 2026-10-29 for the first point rules, `ANNEX_I.A.P6` and `ANNEX_III.A.P6` (#68): in a numbered-field draft the rule checks fields A.8 to A.10 of Table 2 (A.9 to A.11 of Table 4); in a draft without field numbers it searches the offeror or issuer section for an e-mail address, a telephone number and a period in days. The loader keeps the answer of every numbered field under the reserved metadata key `numbered_fields`, so later point rules can read their fields the same way. The template sets no condition on these three fields, so an "N/A" answer goes to review.

## Consequences

More findings per report. SARIF rules grow with the rule set without extra work. Rule pages are generated too, but a point rule that checks numbered fields and applies the template's conditions needs its own logic in `linter.py`. It therefore also needs its own examples (with a `missing` and a `pass` case), status logic and limitations in `scripts/build_rule_docs.py`. Each point rule needs a field mapping for every regime it applies to and fixtures for each template condition.

## Non-negotiables check

Existing IDs unchanged; citations verified before use; synthetic fixtures only.
