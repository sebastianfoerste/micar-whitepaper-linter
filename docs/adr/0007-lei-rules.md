# 0007. LEI check-digit and consistency rules

Status: Accepted (2026-10-21). Amended on 2026-10-27, after the owner's decisions on the rule terms review: point 5 citation, and Review for a party section without an LEI.

## Context

White papers identify their parties by Legal Entity Identifier. The repo's study maps the LEI to Annex I, Part A (`ANNEX_I_PART_A_05_LEI_OR_IDENTIFIER` in `batch.py`). A mistyped LEI is a common, mechanical error that a deterministic check can catch. WhitePaperXBRL checks LEI check digits and optionally asks GLEIF, but treats a failed lookup as valid (Observed in its docs); that fails open. EUR-Lex was unreachable, so no new citation could be verified.

## Options

1. One rule, check digits only.
2. Two rules: check digits, and consistency between the party sections and the rest of the draft.
3. Option 2 plus a GLEIF registry lookup.

## Decision

Option 2, offline.

- **`COMMON.LEI_CHECK_DIGITS`** (MAJOR) reads every section for 20-character codes: 18 upper-case letters or digits, then two digits. A purely numeric run counts only right after an LEI label, with at most two short words between them. Statuses:
  - Missing: no code is found anywhere and no party section has text other than a placeholder (fail closed).
  - Review: any code fails ISO/IEC 7064 MOD 97-10, or no code is found while a party section has text. Point 5 of each party Part allows another identifier required under national law in place of the LEI, and the rule cannot recognise one.
  - Pass: every code is well formed.
- **`COMMON.LEI_CONSISTENCY`** (MAJOR) looks only at codes with valid check digits, so a single typo is reported once. Statuses:
  - Missing: no party section (`issuer`, `offeror`, `trading_platform_operator`) has text other than a placeholder.
  - Review: a party section has text but none has a valid LEI; a valid LEI outside the party sections appears in none of them; or `issuer` names more than one LEI.
  - Pass: otherwise.
- **Citation.** `Anhang I Teil A Nr. 5, Teil B Nr. 5, Teil C Nr. 5, Anhang II Teil A Nr. 5, Anhang III Teil A Nr. 5 MiCAR`, checked against the Official Journal on 2026-10-27. Point 5 of each party Part names the LEI or another identifier required under national law, and Art. 2(1)(b) and (c) of Implementing Regulation (EU) 2024/2984 ask for the LEI where available. Before that date the rules cited Part A of each Annex without a point, although Annex I Part A covers the offeror.
- **Anchoring.** Both rules anchor to the `issuer` section for line mapping and the review table.
- **CI outputs.** Issue text quotes the LEI, so both rules are in `DRAFT_ECHO_RULES` and the summary, annotations and SARIF use the fixed sentence instead.
- **Network.** No registry lookup: a pass means the characters are consistent, not that the LEI exists or belongs to the named entity.

## Consequences

- Each regime gains two rules, and every existing report gains two findings. The three full synthetic examples carry a fictional LEI with computed check digits and pass both rules; `examples/incomplete.json` has none and shows both as Review, because its issuer section has text.
- Rule IDs are new; no existing ID, status, severity or exit code changes. `--strict` is unaffected, because neither rule is a BLOCKER.

## Non-negotiables check

- Fails closed when there is no LEI.
- Deterministic, with no model and no network.
- Test LEIs are synthetic with computed check digits; no real identifier appears in the repo.
- The point 5 pinpoint was added on 2026-10-27 after the Official Journal check.
- Severity: MAJOR for both rules, confirmed by the owner on 2026-10-22.
- Owner decision of 2026-10-27: a party section without an LEI goes to Review, not Missing.
