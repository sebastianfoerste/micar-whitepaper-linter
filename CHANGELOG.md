# Changelog

This file starts with 1.2.0. Earlier releases are recorded only as git tags (v0.1.0, v1.0.0, v1.1.0, v1.1.1); up to v1.1.1 the package metadata still read 0.1.0 or 0.2.0. From 1.2.0 the package version and the release tag match.

## [1.2.0] - unreleased

Citations and statements below were checked against the EUR-Lex texts of Regulation (EU) 2023/1114 (CELEX 32023R1114) and Implementing Regulation (EU) 2024/2984 (CELEX 32024R2984), as mirrored in legalize-dev/legalize-eu.

### Fixed

- `ANNEX_II.D` and `ANNEX_II.I` no longer require redemption "at par" for asset-referenced tokens. At par is the e-money token rule (Art. 49(4) MiCAR). An ART issuer redeems by paying funds equivalent to the market value of the referenced assets or by delivering those assets (Art. 39(2) MiCAR), and `ANNEX_II.I` accepts either basis. `ANNEX_II.D` asks for the permanent right of redemption, its treatment in insolvency and complaints handling (Annex II Part D, points 9, 12 and 13).
- `ANNEX_II.G.VALUATION_AUDIT` cited Art. 36(3) MiCAR, which is operational segregation. It now cites Art. 36(7), (9), (11) and (12). Its label says that only the keywords are checked, and that requiring the word "audit" is an internal interpretation and not an Annex II item: Annex II Part G and Part G of Table 3 of Implementing Regulation (EU) 2024/2984 list no audit, Art. 36(9) requires the audit and Art. 30(2) the publication of the audit report. Whether a missing audit description should stay a BLOCKER is left to lawyer review. The custody label cites Art. 37 MiCAR.
- `ANNEX_II.I` cites Annex II Part C point 8, Part D points 9, 14, 15 and 16, Part G point 3, Art. 39(2) and (3) and Art. 46 MiCAR.
- German ART checks use "Rücktausch" and "Marktwert". These terms were checked against German Art. 39 text reproduced in web search results, not against the German Official Journal.
- Term and pattern matching collapses whitespace, so a required phrase that wraps across lines in a PDF, Markdown or DOCX draft still matches.
- The starter template (`templates/whitepaper-starter`) cites the ART provisions for its `art` type and no longer asks for redemption at par.

### Added

- `ANNEX_I.NOT_APPROVED_STATEMENT` (Art. 6(3) MiCAR) and `ANNEX_III.NOT_APPROVED_STATEMENT` (Art. 51(3) MiCAR) check the English first-page statement that no competent authority has approved the white paper, and fail closed when it is absent. A statement without a heading is routed by its content. First-page placement is not checked. German drafts are referred to review until the German wording is checked against the Official Journal. The ART ruleset has no such rule because Art. 19 MiCAR prescribes no such statement (Table 3 field I.02 of Implementing Regulation (EU) 2024/2984 holds the Art. 19(4) warning instead). The white paper of an authorised ART issuer is deemed approved (Art. 21(1) MiCAR) and that of a credit institution is approved (Art. 17(1)(a)), but an issuer exempt under Art. 16(2) only notifies it.
- `studies/2026-07-title-ii-annex-i-whitepaper-study/scripts/build_review_matrix.py` builds the human-review sheets from the detector output.

### Changed

- The human-review sheets of the Title II study use the detector's current rule IDs. None of the 150 cells has been reviewed.
- README and docs describe the checks as keyword, minimum-length and structure checks and no longer call them audits or a pass compliance. The README image is a rendering of the real `make demo` output.
- The playground wheel is rebuilt as `micar_whitepaper_linter-1.2.0-py3-none-any.whl`.
