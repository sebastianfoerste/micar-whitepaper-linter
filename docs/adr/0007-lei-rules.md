# 0007. LEI check-digit and consistency rules

Status: Accepted (2026-10-21). Amended on 2026-10-27, after the owner's decisions on the rule terms review: point 5 citation, and Review for a party section without an LEI. Amended on 2026-10-29: the LEI of a person other than the parties counts toward neither Review condition of `COMMON.LEI_CONSISTENCY`. Amended on 2026-11-02, after an audit, its review and a second verification: in a section that reads LEIs, every LEI-like code that is not LEI-shaped sends `COMMON.LEI_CHECK_DIGITS` to Review, wherever it stands, so a malformed LEI next to a valid one no longer passes in the shapes listed below. The amendment first read only the code that a label introduced; the verification found list, bullet and line-wrap shapes that this reading missed, and a quadratic path, so the reading was replaced by the one described here.

## Context

White papers identify their parties by Legal Entity Identifier. The repo's study maps the LEI to Annex I, Part A (`ANNEX_I_PART_A_05_LEI_OR_IDENTIFIER` in `batch.py`). A mistyped LEI is a common, mechanical error that a deterministic check can catch. WhitePaperXBRL checks LEI check digits and optionally asks GLEIF, but treats a failed lookup as valid (Observed in its docs); that fails open. EUR-Lex was unreachable, so no new citation could be verified.

## Options

1. One rule, check digits only.
2. Two rules: check digits, and consistency between the party sections and the rest of the draft.
3. Option 2 plus a GLEIF registry lookup.

## Decision

Option 2, offline.

- **`COMMON.LEI_CHECK_DIGITS`** (MAJOR) reads the text of every section (`lei.py`):
  - **LEI-shaped codes.** A run of 20 characters, 18 upper-case letters or digits and then two digits, that is not part of a longer run of capitals and digits. One with a letter counts in every section; a purely numeric one only in a section that reads LEIs. Each has its check digits checked (`lei.find_leis`).
  - **Sections that read LEIs** (`lei.reads_leis`): the party sections (`issuer`, `offeror`, `trading_platform_operator`), and any section that names an LEI label or holds an LEI-shaped code with a letter. The label is LEI or LEIs as a word ("LEI-Nr.", "LEI code"), legal entity identifier(s) or legal entity ID, or Rechtsträgerkennung(en) (also Rechtstraegerkennung), in any case. Any spaces, hyphens or line ends may stand between the words of the long labels, and a hyphen, a soft hyphen or a line end (with or without a hyphen) between any two of their letters, as a PDF or a word processor breaks a word ("Rechtsträger-\nkennung").
  - **LEI-like codes** (`lei.lei_like_codes`). In a section that reads LEIs, every LEI-like code counts, wherever it stands: before or after a label, in a list joined by any words or marks, after a bullet, a field label or a role ("Offeror: …"), or on a later line. The text is split into groups, the runs of ASCII letters and digits. An LEI-like code is:
    - one group of 18 to 22 characters that holds a digit or no lower-case letter; or
    - groups joined by one to three spaces, invisible characters (a zero-width space, joiner or no-break mark), hyphens or line ends (at most one hyphen and one line end) that together hold at least 18 characters and a digit, or whose groups all have the same length ("XXXX XXXX XXXX XXXX XXXX"). A group of 18 or more characters, and "LEI" or "LEIs" in any case, do not join. A group of letters only that holds a lower-case letter is a word, and joins only beside a group of the same length that holds a digit, as in a code in lower case split into groups ("9999 synt h000 0zzq 0263").

    One that is not LEI-shaped as written is malformed (`lei.malformed_leis`): it has 18, 19, 21 or 22 characters, is in lower case, has a letter where a check digit belongs, or is split into groups. The issue quotes it with each run of spaces, invisible characters or line ends as one space, cut after 40 characters, so neighbouring groups that joined it ("CODE 9999 SYNT H000 0ZZQ 0263 HRB 12345") are quoted with it.
  - **Where this departs from the reading recommended by the verification** (every case-insensitive run of 18 to 22 letters and digits, or spaced groups that join to that length, in a section with a label), and why:
    - A run of letters only that holds a lower-case letter is a word, not a code. `examples/art-stablecoin.json` names "Aktiengesellschaft" (18 letters) in its labelled issuer section, so the recommended reading sends that example to Review; German legal prose is full of such words ("Handelsregisternummer", "aufsichtsrechtlichen").
    - A word joins groups only beside a group of its length with a digit. If every word joined, prose such as "with a fictional registered seat and business address at Example Street 22" in the labelled offeror section of `examples/other-crypto-asset.json` would be one code and send that example to Review; if every word of up to four letters joined, "was founded in 2019 and has its seat in Berlin" would read "in 2019 and has its seat in" as a code of 21 characters.
    - A run of groups in capitals without a digit counts only if all its groups have the same length, so a heading in capitals ("INFORMATION ABOUT THE OFFEROR") is no code.
    - Groups count from 18 characters with no upper bound, so a spaced code with its neighbours ("LEI CODE 9999 SYNT …") is read; one group of more than 22 characters (a contract address, a hash) is not.
    - Party sections and sections with an LEI-shaped code read LEIs without a label. In a DOCX, a paragraph "LEI:" in capitals or bold is a heading and not section text, so its section holds no label; and a code next to an unlabelled LEI ("… 9999SYNTH0000ZZQ0263 and 9999SYNTH0000ZZQ026") was read by the first amendment and still is.
  - **Limits: a malformed code that is not seen**, so the rule can still pass:
    - Text outside sections: a heading, and text in no section, are not read. In a PDF, a line such as "Offeror: …" that names a section is a heading, and a code on it is not seen.
    - A section that is not a party section, names no LEI label and holds no LEI-shaped code with a letter.
    - A code that is no LEI-like code: one group of fewer than 18 or more than 22 characters (a code that has lost or gained three or more characters), also right after a label, where the first reading of this amendment sent any code of ten or more letters and digits to Review (and with it a date-time or telephone number in that place); groups that together hold fewer than 18; one group of letters only with a lower-case letter; groups split by other characters (full stops, slashes), by more than three characters, or by two hyphens or two line ends (a blank line); a code split into groups where a group of letters only with a lower-case letter stands beside no group of its length with a digit; groups in capitals without a digit and of different lengths.
  - **False Reviews**, which fail safe: every LEI-like code in a section that reads LEIs counts, so an IBAN ("DE00 0000 0000 0000 0000 00"), a long number in groups, a placeholder such as "XXXXXXXXXXXXXXXXXXXX", an address or a heading in capitals with a digit in it, or a word of 18 to 22 capitals gives Review; a 20-digit account number there has its check digits checked.

  Statuses:
  - Missing: no LEI-shaped code is found anywhere and no party section has text other than a placeholder (fail closed). A malformed code is named in the issues and does not change this status.
  - Review: any LEI-shaped code fails ISO/IEC 7064 MOD 97-10, an LEI-like code is malformed, or no LEI-shaped code is found while a party section has text. Point 5 of each party Part allows another identifier required pursuant to applicable national law in place of the LEI, and the rule cannot recognise one.
  - Pass: every LEI-shaped code has valid check digits and no LEI-like code is malformed.
- **`COMMON.LEI_CONSISTENCY`** (MAJOR) looks only at LEI-shaped codes with valid check digits, so a single typo, or a malformed code, is reported once, by `COMMON.LEI_CHECK_DIGITS`; a draft with a malformed LEI next to a valid one can pass this rule by design. Statuses:
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
- The 2026-11-02 amendment changes no rule ID, severity or exit code and adds no status: a draft that gives a malformed LEI-like code in a section that reads LEIs, next to a valid LEI, moves from Pass to Review on `COMMON.LEI_CHECK_DIGITS`, and a 20-digit number in such a section has its check digits checked; the false Reviews above can move a draft from Pass to Review too. The seven drafts in `examples/` give the same `--json` reports as before.
- The reading is one pass: each group is classified once, each gap between two groups is looked at once and only if it is at most three characters long, and the label search reads each run of spaces or line ends once. Its time grows linearly with the length of the text; in the tests, 200 KB of text, including a label followed by 200 000 line ends, is read in well under the 2 s bound (about 0.1 s at most here). The result is kept for the last 64 texts read, so the two rules do not repeat it for the same section text.

## Non-negotiables check

- Fails closed when there is no LEI. An LEI-like code that is not a valid LEI, in a section that reads LEIs, never lets `COMMON.LEI_CHECK_DIGITS` pass; a malformed code that the limits above leave unseen can. `COMMON.LEI_CONSISTENCY` leaves malformed codes to `COMMON.LEI_CHECK_DIGITS` by design.
- Deterministic, with no model and no network.
- Test LEIs are synthetic with computed check digits; no real identifier appears in the repo.
- The point 5 pinpoint was added on 2026-10-27 after the Official Journal check.
- Severity: MAJOR for both rules, confirmed by the owner on 2026-10-22.
- Owner decision of 2026-10-27: a party section without an LEI goes to Review, not Missing.
