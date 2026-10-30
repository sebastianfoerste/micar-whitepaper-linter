# Features Guide: MiCAR Whitepaper Linter

This document details the functional features implemented in the MiCAR Whitepaper Linter.

---

## 1. Multiple Document Input Formats
- **Description**: Reads white papers saved as JSON, XHTML or HTML (including Inline XBRL and the numbered-field layout of Implementing Regulation (EU) 2024/2984), DOCX, PDF or Markdown.
- **Related Files**:
  - [src/micar_linter/whitepaper.py](../src/micar_linter/whitepaper.py)
  - [src/micar_linter/document.py](../src/micar_linter/document.py)
  - [src/micar_linter/xhtml_parser.py](../src/micar_linter/xhtml_parser.py)
  - [src/micar_linter/numbered_fields.py](../src/micar_linter/numbered_fields.py)
- **Status**: Fully Implemented.

## 2. Regime-Specific Annex Checks
- **Description**: Applies the rules for the regime of the crypto-asset: other crypto-assets (Annex I), asset-referenced tokens (Annex II) or e-money tokens (Annex III), each with the common rules of `common.py`. E-money tokens run `EMT_COMMON_RULES`, whose `COMMON.RISK_WARNING` checks the two warnings of Art. 51(4) MiCAR under the same rule ID.
- **Related Files**:
  - [src/micar_linter/rules/common.py](../src/micar_linter/rules/common.py)
  - [src/micar_linter/rules/annex_i.py](../src/micar_linter/rules/annex_i.py)
  - [src/micar_linter/rules/annex_ii.py](../src/micar_linter/rules/annex_ii.py)
  - [src/micar_linter/rules/annex_iii.py](../src/micar_linter/rules/annex_iii.py)
- **Status**: Fully Implemented.

## 3. Finding Severity Mapping
- **Description**: Each rule has one of three severities, and each finding one of three statuses. Severity belongs to the rule, not to the finding: a BLOCKER finding can be `review` and a MAJOR finding `missing`.
  - **Blocker**: an open finding should keep the white paper from notification or submission for approval until it is cured. Every BLOCKER finding that has not passed counts as a blocker and makes `--strict` exit 1. The draft should not enter an external review or filing workflow until the blockers are cured and a lawyer has signed off. Two BLOCKER rules never pass for a loaded draft and stay open in every CLI, Action and playground report that runs them: `COMMON.IXBRL_TAGGING` in every regime and `ANNEX_II.G.DEPOSIT_FLOOR_REVIEW` in ART reports.
  - **Major**: the rule covers a disclosure that, if incomplete, is likely to mislead or need substantive review.
  - **Minor**: a drafting gap to cure before publication; it does not gate notification.
  - **Statuses**: `missing`, `review` (present but thin, without a listed term, or otherwise flagged) or `pass`. On the generic checks, `missing` means the section is empty, absent or holds only placeholders. The rules with their own logic can also return `missing` when the section has text: `COMMON.IXBRL_TAGGING` for every draft that is not XHTML or HTML, and for a saved iXBRL viewer page; `ANNEX_II.G.DEPOSIT_FLOOR_REVIEW` when the draft's reserve characterisation determines a candidate floor and the section states no percentage; and the point rules `ANNEX_I.A.P6` and `ANNEX_III.A.P6` in a numbered-field draft when none of their three template fields holds an answer. They return `review` while one of those fields is empty, holds a placeholder or "N/A", or gives no telephone number, e-mail address or number of days, and in any other draft while the section lacks one of the three. With that characterisation missing or invalid, or with the token stated not to reference an official currency, the deposit-floor rule returns `review`, even for an empty section. The two LEI rules return `missing` only when no issuer, offeror or trading platform operator section has text. When a party section has text but the draft gives no LEI (for `COMMON.LEI_CONSISTENCY`, no valid LEI in a party section), they return `review`, because point 5 of each party Part allows another identifier required pursuant to applicable national law in place of the LEI; once the draft gives an LEI, a party section without one does not change the result. On the generic checks a pass means the listed terms appear, any required patterns match and no prohibited pattern does, the section is long enough and, in a numbered-field draft, no field of the section holds only a placeholder. The notification-date and language checks pass when the section names a calendar date or an official EU language, however short it is, and the point rules when they find all three contact details. `ANNEX_II.G.DEPOSIT_FLOOR_REVIEW` never passes, and `COMMON.IXBRL_TAGGING` never passes for a loaded draft. A pass is not a compliance opinion.
- **Related Files**:
  - [src/micar_linter/rules/base.py](../src/micar_linter/rules/base.py)
  - [src/micar_linter/linter.py](../src/micar_linter/linter.py)
- **Status**: Fully Implemented.

## 4. Multi-Format Report Exporter
- **Description**: Renders the report as text, JSON, a Markdown audit log or a coverage table, and writes SARIF, a job summary and workflow annotations for CI (`ci_outputs.py`).
- **Related Files**:
  - [src/micar_linter/report.py](../src/micar_linter/report.py)
  - [src/micar_linter/ci_outputs.py](../src/micar_linter/ci_outputs.py)
- **Status**: Fully Implemented.

## 5. Review Table Export
- **Description**: Adds rule-by-rule review rows with citations, blocker status, remediation, reviewer decisions and export eligibility.
- **Related Files**:
  - `src/micar_linter/review_table.py`
  - `src/micar_linter/cli.py`
  - `tests/test_review_table.py`
- **Status**: Fully Implemented. The output includes review economics, local source coverage, review cells, suggested-edit metadata, review bundle exports, `review-table.md` and blocked filing gates.

## 6. Fail-closed ART reserve-floor review

- **Description**: Extracts bounded percentage candidates from the reserve disclosure and identifies a candidate threshold under Articles 35(4), 36(4)(d), 45(3) and 45(7)(b) MiCAR. The rule always retains lawyer review and has no automatic `PASS` path.
- **Related Files**:
  - `src/micar_linter/linter.py`
  - `src/micar_linter/rules/annex_ii.py`
  - `tests/test_reserve_rules.py`
- **Status**: Fully implemented as a fail-closed review gate. Draft reviewer-name and reviewer-date fields are ignored.
