# Overview

Audience, status and limits, the pilot study and related tools, moved out of the [README](../README.md). Setup and the GitHub Action are in [SETUP.md](SETUP.md); long-form usage and the full example output are in [DETAILS.md](DETAILS.md).

## Who it's for

- **Lawyers and compliance teams** reviewing a MiCAR white paper draft who want a cited first-pass list of candidate disclosure gaps before the substantive legal review.
- **Teams drafting a white paper in a Git repository** who want every push checked in CI.

Rule sets cover all three white paper regimes under MiCAR (Regulation (EU) 2023/1114): crypto-assets other than ARTs and EMTs (Annex I), asset-referenced tokens (Annex II) and e-money tokens (Annex III). It is a screening tool, not a sign-off: whether a white paper is lawful or complete remains a lawyer's judgment. Not legal advice.

## Status and limits

For each disclosure that Annex I, II or III requires, the linter checks that the section exists, meets a minimum length and contains the expected keywords, and it cites the provision. A pass means the section is there, long enough and uses the expected terms; the LEI checks instead pass on LEIs with valid check digits, and, from the next release, the notification-date and language checks on a calendar date and an official EU language. It does not mean the disclosure is accurate, complete or compliant. The English wording of the first-page statement required by Art. 6(3) and Art. 51(3) is matched word for word (ignoring case and line breaks), including which person it names as solely responsible. Whether that statement sits on the first page is not checked.

| Area | State |
| --- | --- |
| Table 2 (crypto-assets other than ART/EMT) | Run against public ESMA-register documents |
| Table 3 / Table 4 (ART / EMT) | Follows the Official Journal text; **not yet run against a real ART or EMT white paper** |
| iXBRL check | Well-formedness, Inline XBRL 1.1 and ESMA MiCA taxonomy namespaces only; never reports Pass; not run for a saved iXBRL viewer page (Missing) |
| Reserve-floor check | Extracts candidates; never returns `PASS` |
| Table of contents, DTI | Not checked: the table of contents that Art. 6(8), Art. 19(7) and Art. 51(7) MiCAR require, and the ISO 24165 Digital Token Identifier of Art. 3 of Delegated Regulation (EU) 2025/421 |
| Pilot study | 10 documents, 15 rules each, 21 machine-flagged candidate gaps, **pending human review**; convenience sample, no precision/recall claim |

## Legal state assumed (checked on 31 October 2026)

The checks encode the legal state below. Every item names the official source that was read on 31 October 2026. An automated session read them; the owner has not yet confirmed this section. The Official Journal texts were read as the Publications Office serves them (EUR-Lex's website answered with a browser challenge that day); the EUR-Lex address of each text is given beside it.

- **MiCAR applies from 30 December 2024** (Art. 149(2) of Regulation (EU) 2023/1114). **Titles III and IV, which hold the ART and EMT white paper rules of Art. 19 and Art. 51, apply from 30 June 2024** (Art. 149(3)). Source: OJ L 150, 9.6.2023, p. 40, <https://publications.europa.eu/resource/cellar/01d55833-0660-11ee-b12e-01aa75ed71a1.0006.03/DOC_1> (EUR-Lex: <https://eur-lex.europa.eu/eli/reg/2023/1114/oj/eng>).
- **Implementing Regulation (EU) 2024/2984 applies from 23 December 2025** (Art. 4): white papers are drawn up in XHTML, marking the template fields with Inline XBRL 1.1 and the elements of the taxonomy (Art. 2). Sources: OJ L, 2024/2984, 3.12.2024, <https://publications.europa.eu/resource/cellar/6e4786f3-b117-11ef-acb1-01aa75ed71a1.0006.03/DOC_1> (EUR-Lex: <https://eur-lex.europa.eu/eli/reg_impl/2024/2984/oj/eng>); ESMA's statement ESMA75-1303207761-6284 of 28 November 2025, which says the ITS applies as of 23 December 2025 and that the XBRL taxonomy was published on ESMA's website on 5 August 2025, <https://www.esma.europa.eu/sites/default/files/2025-11/ESMA75-1303207761-6284_Statement_to_support_the_smooth_implementation_of_MiCA_standards_and_format.pdf>; the taxonomy package "MiCA White Papers Taxonomy 2025", <https://www.esma.europa.eu/sites/default/files/2025-08/mica_taxonomy_2025.zip>, whose `mica_cor.xsd` carries the namespace the iXBRL check expects.
- **Delegated Regulation (EU) 2025/421** (data necessary for the classification of white papers) **applies from 23 December 2025** (Art. 4). Its Art. 3 identifies the white paper and the crypto-assets it relates to with the ISO 24165 Digital Token Identifier where it is provided. The linter does not check the DTI. Source: OJ L, 2025/421, 24.3.2025, <https://publications.europa.eu/resource/cellar/3034df96-0851-11f0-b1a3-01aa75ed71a1.0006.03/DOC_1> (EUR-Lex: <https://eur-lex.europa.eu/eli/reg_del/2025/421/oj/eng>).
- **Transitional rules, context only** (the linter has no rule on either): under Art. 143(2), point (b), MiCAR, operators of trading platforms must ensure by 31 December 2027 that a white paper is drawn up, notified and published for crypto-assets other than ARTs and EMTs that were admitted to trading before 30 December 2024; under Art. 143(3), crypto-asset service providers that provided their services in accordance with applicable law before 30 December 2024 could continue until 1 July 2026 or until an authorisation was granted or refused, whichever was sooner, and Member States could shorten that period. Source: the MiCAR text above.
- **ESMA's register is still the interim MiCA register**: five CSV files, published at weekly intervals, as ESMA's MiCA page showed on 31 October 2026; the page still says the CSV collection serves "until mid-2026 when it will be formally integrated into ESMA's IT systems". Source: <https://www.esma.europa.eu/esmas-activities/digital-finance-and-innovation/markets-crypto-assets-regulation-mica>.
- **Pending, with no change to the white paper rules adopted as of 31 October 2026**: the Commission's report on the application of MiCAR under Art. 140(1), due by 30 June 2027 and possibly accompanied by a legislative proposal (source: the MiCAR text above); its public and targeted consultations on the review of MiCA, open from 20 May 2026 and closed on 30 September 2026 after an extension from 31 August (sources: <https://finance.ec.europa.eu/regulation-and-supervision/consultations-0/targeted-consultation-review-mica-regulation_en>, <https://finance.ec.europa.eu/news/commission-seeks-feedback-functioning-eu-crypto-assets-rules-2026-05-20_en>, <https://ec.europa.eu/newsroom/fisma/items/945754/en>); and the Commission's market integration and supervision package, proposed on 4 December 2025, which would give ESMA direct oversight of significant market infrastructures and crypto service providers (sources: <https://finance.ec.europa.eu/digital-finance/crypto-assets_en>, <https://finance.ec.europa.eu/regulation-and-supervision/savings-and-investments-union/factsheet-breaking-down-barriers-integrate-financial-markets_en>). A check of the white paper rules is due when either is adopted.

## Pilot study

A reproducible study over Title II white papers in ESMA's MiCA register publishes document hashes, extraction metadata, limitations and a 150-cell human-review matrix. No cell has been reviewed yet (0 of 150), so the study reports no precision, recall or prevalence figures. Flags are unreviewed machine output, not legal findings. Raw white papers are not committed. Start at [findings-summary.md](../studies/2026-07-title-ii-annex-i-whitepaper-study/findings-summary.md). Reviewers start at [REVIEWING.md](../studies/2026-07-title-ii-annex-i-whitepaper-study/REVIEWING.md).

## Part of the EU regulation as code suite

Deterministic, review-gated tools by [sebastianfoerste](https://github.com/sebastianfoerste):

- [awesome-eu-fintech-regulation](https://github.com/sebastianfoerste/awesome-eu-fintech-regulation): curated EU fintech primary sources and tools
- [contract-review-eval-harness](https://github.com/sebastianfoerste/contract-review-eval-harness)
- [legal-function-operating-system](https://github.com/sebastianfoerste/legal-function-operating-system)
- [eu-ai-act-classifier](https://github.com/sebastianfoerste/eu-ai-act-classifier): AI Act risk tiers with cited obligations
- **micar-whitepaper-linter** (this repo)
- [eu-reg-mcp](https://github.com/sebastianfoerste/eu-reg-mcp): MCP server; exposes a `lint_micar_whitepaper` tool
- [micar-register-observatory](https://github.com/sebastianfoerste/micar-register-observatory)

Also: [micar-whitepaper-template](https://github.com/sebastianfoerste/micar-whitepaper-template), [dpa-and-data-transfer-review](https://github.com/sebastianfoerste/dpa-and-data-transfer-review).
