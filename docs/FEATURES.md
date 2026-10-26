# Features Guide: MiCAR Whitepaper Linter

This document details the functional features implemented in the MiCAR Whitepaper Linter.

---

## 1. Multiple Document Input Formats
- **Description**: Reads white papers saved as JSON, XHTML or HTML (including Inline XBRL and the numbered-field layout of Implementing Regulation (EU) 2024/2984), DOCX, PDF or Markdown.
- **Related Files**:
  - [src/micar_linter/document.py](../src/micar_linter/document.py)
  - [src/micar_linter/xhtml_parser.py](../src/micar_linter/xhtml_parser.py)
- **Status**: Fully Implemented.

## 2. Regime-Specific Annex Audits
- **Description**: Applies the rules for the regime of the crypto-asset: other crypto-assets (Annex I), asset-referenced tokens (Annex II) or e-money tokens (Annex III), each with the rules every regime shares (`common.py`).
- **Related Files**:
  - [src/micar_linter/rules/annex_i.py](../src/micar_linter/rules/annex_i.py)
  - [src/micar_linter/rules/annex_ii.py](../src/micar_linter/rules/annex_ii.py)
  - [src/micar_linter/rules/annex_iii.py](../src/micar_linter/rules/annex_iii.py)
- **Status**: Fully Implemented.

## 3. Finding Severity Mapping
- **Description**: Each rule has one of three severities, and each finding one of three statuses. Severity belongs to the rule, not to the finding: a BLOCKER finding can be `review` and a MAJOR finding `missing`.
  - **Blocker**: the rule covers a disclosure the white paper cannot be notified or submitted for approval without. Every BLOCKER finding that has not passed counts as a blocker and makes `--strict` exit 1. The draft should not enter an external review or filing workflow until the blockers are cured and a lawyer has signed off.
  - **Major**: the rule covers a disclosure that, if incomplete, is likely to mislead or need substantive review.
  - **Minor**: a drafting gap to cure before publication; it does not gate notification.
  - **Statuses**: `missing` (the section is empty, absent or holds only placeholders), `review` (present but thin, without a listed term, or otherwise flagged) or `pass`. On the generic checks a pass means the listed terms appear and the section is long enough; `COMMON.IXBRL_TAGGING` and `ANNEX_II.G.DEPOSIT_FLOOR_REVIEW` never pass. A pass is not a compliance opinion.
- **Related Files**:
  - [src/micar_linter/rules/base.py](../src/micar_linter/rules/base.py)
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
