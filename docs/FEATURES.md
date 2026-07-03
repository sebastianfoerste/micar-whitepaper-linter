# Features Guide: MiCAR Whitepaper Linter

This document details the functional features implemented in the MiCAR Whitepaper Linter.

---

## 1. Multiple Document Input Formats
- **Description**: Parses white papers saved as JSON structures, DOCX files, or tagged Inline XBRL XHTML.
- **Related Files**:
  - [src/micar_linter/document.py](file:///Users/sebastian/Developer/micar-whitepaper-linter/src/micar_linter/document.py)
  - [src/micar_linter/xhtml_parser.py](file:///Users/sebastian/Developer/micar-whitepaper-linter/src/micar_linter/xhtml_parser.py)
- **Status**: Fully Implemented.

## 2. Regime-Specific Annex Audits
- **Description**: Applies validation checkers based on whether the token is a standard utility token (Annex I), stablecoin (Annex II), or e-money token (Annex III).
- **Related Files**:
  - [src/micar_linter/rules/annex_i.py](file:///Users/sebastian/Developer/micar-whitepaper-linter/src/micar_linter/rules/annex_i.py)
  - [src/micar_linter/rules/annex_ii.py](file:///Users/sebastian/Developer/micar-whitepaper-linter/src/micar_linter/rules/annex_ii.py)
  - [src/micar_linter/rules/annex_iii.py](file:///Users/sebastian/Developer/micar-whitepaper-linter/src/micar_linter/rules/annex_iii.py)
- **Status**: Fully Implemented.

## 3. Finding Severity Mapping
- **Description**: Classifies findings into distinct severity levels:
  - **Blocker**: Severe omissions causing immediate regulatory rejection.
  - **Major**: Core missing disclosures.
  - **Minor**: Non-binding suggestions.
  - **Pass**: Standard compliant parameters met.
- **Related Files**:
  - [src/micar_linter/rules/base.py](file:///Users/sebastian/Developer/micar-whitepaper-linter/src/micar_linter/rules/base.py)
- **Status**: Fully Implemented.

## 4. Multi-Format Report Exporter
- **Description**: Formats logs as markdown reports or raw JSON structures.
- **Related Files**:
  - [src/micar_linter/report.py](file:///Users/sebastian/Developer/micar-whitepaper-linter/src/micar_linter/report.py)
- **Status**: Fully Implemented.

## 5. Review Table Export
- **Description**: Adds rule-by-rule review rows with citations, blocker status, remediation, reviewer decisions and export eligibility.
- **Related Files**:
  - `src/micar_linter/review_table.py`
  - `src/micar_linter/cli.py`
  - `tests/test_review_table.py`
- **Status**: Fully Implemented. The output includes review economics, local source coverage, review cells, suggested-edit metadata, review bundle exports, `review-table.md` and blocked filing gates.
