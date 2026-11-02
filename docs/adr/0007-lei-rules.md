# 0007. LEI check-digit and consistency rules

Status: Accepted (2026-10-21). Amended on 2026-10-27, after the owner's decisions on the rule terms review: point 5 citation, and Review for a party section without an LEI. Amended on 2026-10-29: the LEI of a person other than the parties counts toward neither Review condition of `COMMON.LEI_CONSISTENCY`. Amended on 2026-11-02, after an audit and its review: a code that an LEI label introduces but that is not LEI-shaped sends `COMMON.LEI_CHECK_DIGITS` to Review, so a malformed LEI next to a valid one no longer passes, also after an abbreviation ("LEI No."), in a list ("LEIs: … and …") or across a PDF line wrap.

## Context

White papers identify their parties by Legal Entity Identifier. The repo's study maps the LEI to Annex I, Part A (`ANNEX_I_PART_A_05_LEI_OR_IDENTIFIER` in `batch.py`). A mistyped LEI is a common, mechanical error that a deterministic check can catch. WhitePaperXBRL checks LEI check digits and optionally asks GLEIF, but treats a failed lookup as valid (Observed in its docs); that fails open. EUR-Lex was unreachable, so no new citation could be verified.

## Options

1. One rule, check digits only.
2. Two rules: check digits, and consistency between the party sections and the rest of the draft.
3. Option 2 plus a GLEIF registry lookup.

## Decision

Option 2, offline.

- **`COMMON.LEI_CHECK_DIGITS`** (MAJOR) reads every section for 20-character codes: 18 upper-case letters or digits, then two digits. A purely numeric run counts only right after an LEI label, with at most two short words between them, or as a code that an LEI label introduces (`lei.malformed_leis` and `lei.find_leis` share that reading):
  - The label is LEI or LEIs in capitals, or legal entity identifier(s) or Rechtsträgerkennung(en) in any case, with any spacing or line break between the words.
  - The code is the first run of letters and digits after the label that holds a digit and, with the groups that follow it after a single space or hyphen, has at least ten letters and digits (joining stops once the code reaches 32 characters). At most six other words stand between label and code, with no sentence end (a full stop, question or exclamation mark or semicolon before a space). The full stop of "e.g." or "i.e.", and of "No.", "Nos.", "Nr." or "Nrn." before a word with a digit ("LEI No. …", "LEI-Nr. …"), ends no sentence.
  - A code joined by a comma, "and", "or", "und" or "oder" to such a code, or to an LEI-shaped code that holds a letter, is read too ("LEIs: … and …", "The LEIs of the offeror and the operator are … and …").
  - The search runs on over line ends, since a PDF wraps its lines inside the label or before the code, but not into a line that starts a field of the numbered layout (a label of letters before a colon, such as "Contact telephone number:", or a field number such as "A.8" before a capital) or a list item.

  A labelled code that is not LEI-shaped is malformed: of the wrong length, in lower case, with a letter where a check digit belongs, or split into groups. A date-time or telephone number of ten or more letters and digits in the code's place reads as malformed too, which gives Review. Statuses:
  - Missing: no LEI-shaped code is found anywhere and no party section has text other than a placeholder (fail closed). A malformed code is named in the issues and does not change this status.
  - Review: any code fails ISO/IEC 7064 MOD 97-10, a labelled code is malformed, or no code is found while a party section has text. Point 5 of each party Part allows another identifier required pursuant to applicable national law in place of the LEI, and the rule cannot recognise one.
  - Pass: every LEI-shaped code has valid check digits and no labelled code is malformed.
- **`COMMON.LEI_CONSISTENCY`** (MAJOR) looks only at codes with valid check digits, so a single typo, or a malformed code, is reported once, by `COMMON.LEI_CHECK_DIGITS`. Statuses:
  - Missing: no party section (`issuer`, `offeror`, `trading_platform_operator`) has text other than a placeholder.
  - Review: a party section has text but none has a valid LEI; a valid LEI outside the party sections appears in none of them; or `issuer` names more than one LEI.
  - Neither of the last two counts an LEI that the draft gives for a person other than the parties, which the template of Implementing Regulation (EU) 2024/2984 asks for: the crypto-asset service provider in charge of the placing (Table 2 field E.31, Table 3 C.22), a custodian of the reserve assets (Table 3 G.8), and a person other than the issuer who offers the token, seeks its admission to trading or draws up the white paper (Table 3 AA.1 and AA.3, Table 4 A.27). The field label or the sentence that holds the code must name the role before it (`lei.other_person_leis`).
  - Pass: otherwise.
- **Citation.** `Anhang I Teil A Nr. 5, Teil B Nr. 5, Teil C Nr. 5, Anhang II Teil A Nr. 5, Anhang III Teil A Nr. 5 MiCAR`, checked against the Official Journal on 2026-10-27. Point 5 of each party Part names the LEI or another identifier required pursuant to applicable national law, and Art. 2(1)(b) and (c) of Implementing Regulation (EU) 2024/2984 ask for the LEI where available. Releases 1.2.0 and 1.2.1 cite Part A of each Annex without a point, although Annex I Part A covers the offeror, and report Missing where the amended rules report Review. The amendment reached `main` on 2026-10-29, after 1.2.1.
- **Anchoring.** Both rules anchor to the `issuer` section for line mapping, the SARIF log and the review table. The playground names "every section" in its place and offers no "Inspect section" button for them (`ALL_SECTION_RULES` in `docs/playground/model.mjs`).
- **CI outputs.** Issue text quotes the LEI, so both rules are in `DRAFT_ECHO_RULES` and the SARIF log uses the fixed sentence instead; the job summary and annotations print no issue text.
- **Network.** No registry lookup: a pass means the characters are consistent, not that the LEI exists or belongs to the named entity.

## Consequences

- Each regime gains two rules, and every existing report gains two findings. The three full synthetic examples carry a fictional LEI with computed check digits and pass both rules; `examples/incomplete.json` has none and shows both as Review, because its issuer section has text.
- Rule IDs are new; no existing ID, status, severity or exit code changes. `--strict` is unaffected, because neither rule is a BLOCKER.
- The 2026-11-02 amendment changes no rule ID, severity or exit code and adds no status: a draft that gives a malformed LEI after a label next to a valid LEI moves from Pass to Review on `COMMON.LEI_CHECK_DIGITS`, and a 20-digit number up to six words after an LEI label has its check digits checked. The scan is linear in the length of the text, and its result is kept for the last 64 texts read, so the two rules do not repeat it for the same section text.

## Non-negotiables check

- Fails closed when there is no LEI, and a malformed labelled LEI never ends in Pass.
- Deterministic, with no model and no network.
- Test LEIs are synthetic with computed check digits; no real identifier appears in the repo.
- The point 5 pinpoint was added on 2026-10-27 after the Official Journal check.
- Severity: MAJOR for both rules, confirmed by the owner on 2026-10-22.
- Owner decision of 2026-10-27: a party section without an LEI goes to Review, not Missing.
