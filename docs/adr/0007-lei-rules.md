# 0007. LEI check-digit and consistency rules

Status: Accepted (2026-10-21)

## Context

White papers identify their parties by Legal Entity Identifier. The repo's study maps the LEI to Annex I, Part A (`ANNEX_I_PART_A_05_LEI_OR_IDENTIFIER` in `batch.py`). A mistyped LEI is a common, mechanical error that a deterministic check can catch. WhitePaperXBRL checks LEI check digits and optionally asks GLEIF, but treats a failed lookup as valid (Observed in its docs); that fails open. EUR-Lex was unreachable, so no new citation could be verified.

## Options

1. One rule, check digits only.
2. Two rules: check digits, and consistency between the party sections and the rest of the draft.
3. Option 2 plus a GLEIF registry lookup.

## Decision

Option 2, offline.

- **`COMMON.LEI_CHECK_DIGITS`** (MAJOR) reads every section for 20-character codes: 18 upper-case letters or digits, then two digits. A purely numeric run counts only right after an LEI label, with at most two short words between them. Statuses:
  - Missing: no code is found anywhere (fail closed).
  - Review: any code fails ISO/IEC 7064 MOD 97-10.
  - Pass: every code is well formed.
- **`COMMON.LEI_CONSISTENCY`** (MAJOR) looks only at codes with valid check digits, so a single typo is reported once. Statuses:
  - Missing: no party section (`issuer`, `offeror`, `trading_platform_operator`) has a valid LEI.
  - Review: a valid LEI outside the party sections appears in none of them, or `issuer` names more than one LEI.
  - Pass: otherwise.
- **Citation.** `Anhang I Teil A, Anhang II Teil A, Anhang III Teil A MiCAR`. This joins the Part-level citations the party rules already carry; no new pinpoint is added. The point that names the LEI is unverified, and each rule page says so.
- **Anchoring.** Both rules anchor to the `issuer` section for line mapping and the review table.
- **CI outputs.** Issue text quotes the LEI, so both rules are in `DRAFT_ECHO_RULES` and the summary, annotations and SARIF use the fixed sentence instead.
- **Network.** No registry lookup: a pass means the characters are consistent, not that the LEI exists or belongs to the named entity.

## Consequences

- Each regime gains two rules, and every existing report gains two findings. The synthetic examples have no LEI, so they show both rules as Missing.
- Rule IDs are new; no existing ID, status, severity or exit code changes. `--strict` is unaffected, because neither rule is a BLOCKER.

## Non-negotiables check

- Fails closed when there is no LEI.
- Deterministic, with no model and no network.
- Test LEIs are synthetic with computed check digits; no real identifier appears in the repo.
- No citation pinpoint added; the legal basis is marked as pending owner verification.
- Needs owner decision: the severity (MAJOR) and the point-level citation.
