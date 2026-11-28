# Competitive update and feature candidates (November 2026)

> **Run.** Research ran on 2026-11-25 and updates the [October landscape](2026-10-competitive-landscape.md). Unlike the October run, this session reached ESMA, EBA, the FCA, the CSSF, the FMA, GitHub and most vendor sites, so most October facts tagged **Claimed** could be read at source. EUR-Lex itself answered HTTP 202 with an empty body; the MiCAR text was read in the Official Journal XHTML that the Publications Office Cellar serves for CELEX 32023R1114.
>
> **Upload log.** No file was uploaded to any checker. No sign-ups, trials, forms or vendor contact.
>
> **Scope note.** Statements about named products are limited to what the cited source shows on the access date. Solidcheck, Witness Compliance, easyMiCA, Workiva and Whitepaper Grey were not re-checked. This document is not a review of any vendor and not legal advice.

Evidence tags as in October: **Observed** (read at source in this run), **Claimed** (press or listing only), **Inferred** (own reasoning). Access date 2026-11-25 throughout.

## 1. Conclusion

The format and completeness layer of a white paper is converging on ESMA's own validation, which ESMA says already covers "a substantial part" of the completeness and format checks. The content layer has no reviewer at all: Title II white papers are not approved, and ESMA links the missing "duly notified" criteria to low-quality information. The two companion documents of every Title II notification, the marketing communications and the explanation under Art. 8(4) MiCAR, have no published checker either. The linter's next features should therefore extend its cited, deterministic content checks to those companion documents, and add ESMA's structural filing checks under the existing format gate.

## 2. What changed since October

| Product | October | November finding | Tag |
|---|---|---|---|
| PwC Legal and Auditchain, START on Pacioli.ai | Snippets only | June 2026 flyer read: template workflows for EMTs, ARTs and other crypto-assets; real-time validation against "the full MiCAR ITS rulebook"; "gaps, inconsistencies, and non-compliant language" flagged; external Pacioli.ai Validating Node with audit trail; export to iXBRL, .xls, .pdf and .html; role-based access and version control; one dedicated instance per client (12 May 2026 article). Rule logic still unpublished | Observed |
| Bluprynt MiCA Checker | Existence unknown | Free web tool: PDF or DOCX upload, red, yellow or green per field, scope MiCA Art. 4 and 5, docs say documents "are processed locally and are not stored on servers", API planned | Observed (GitBook docs) |
| MiCA Crypto Alliance | No white paper tracker found | A White Paper Tracker is now listed ("Track and compare MiCA white papers"), next to drafting, review and audit services with "XBRL-ready formatting" | Observed |
| Crypto Risk Metrics | Snippet only | Free checker against the "MiCA White Paper Taxonomy 2025", accepts .html, .xhtml or .xml, asks for name, e-mail and consent; XBRL transposition service for lawyers and CASPs. Check logic unpublished | Observed |
| DataTracks Rainbow | Snippet only | Cloud XHTML and iXBRL generation, states "more than 1,000+ validation checks" (tagging, taxonomy, structure, filing integrity), prompts for missing data points, collaborative review with track changes, PDFs in several languages | Observed (vendor page) |
| CoreFiling | Snippet only | Word, InDesign or PDF converted to iXBRL, then "validation against the MiCA filing rules"; no check count; quote or demo only | Observed |
| NorthPoint MiCA marketing check | Not found | New: free check of marketing copy (URL or pasted text) running 5 of 40 rules (risk warnings, guaranteed returns, superlatives, identifiability, past performance), citing MiCA Art. 7 and 66, pass or fail; calls itself a heuristic screen; sells a 40-rule skill pack for Claude, Cursor and other AI tools | Observed |
| Compliora AI | Not found | AI regulatory assessment with a PDF report "from €49"; MiCA iXBRL blog post of 20 May 2026 | Observed |
| MiCA Compliance Scanner | Not found | Listed in search results; the URL returns 404 | Observed |
| Eunice | Snippet only | AI library of 1,000+ pre-filled white papers "already 50% complete", multi-agent validation, optional CMS legal review (FF News, 6 March 2025) | Claimed |
| TokenEx.Legal | Snippet only | AI assistant for drafting MiCA white papers (Product Hunt, 12 May 2025) | Claimed |
| Arelle | No MiCA plugin, issue #1898 open | Unchanged: #1898 open with no pull request; `arelle/plugin/validate` still has no MiCA plugin | Observed |
| WhitePaperXBRL | 488 hand-coded checks | Unchanged: README states 257 existence and 224 value assertions, 6 LEI checks, 1 duplicate check; inputs PDF, DOCX, ODT, RTF; live demo on Vercel; 0 stars | Observed |
| ToolOracle MiCAOracle | 18 unpublished checks | Unchanged | Observed |

Of the products above, only WhitePaperXBRL documents its rules (October landscape, A.3), and none publishes executed examples per rule. None of the pages describes a check of marketing communications against the white paper (Art. 7(1)(c) MiCAR) or a check of the Art. 8(4) explanation (Inferred from the pages read).

## 3. Regulatory and supervisory signals

- **ESMA response to the MiCA review** (30 September 2026, ESMA75-113276571-1721). Section 4.1: the five-working-day deadline for the register makes a review of each white paper impractical, and missing criteria for "duly notified" may lead to low-quality information. ESMA recommends clarifying those criteria and centralising Title II notification at ESMA, building on the register's technical validation. Section 3.5: ESMA has observed "extensive and disputable marketing activities" and asks for bans of certain practices and obligations for influencers (Observed).
- **ESMA Q&A 2845** (12 May 2026): a modified white paper triggered by a significant new factor must be machine-readable even where the original predates 23 December 2025. The entry into application of Implementing Regulation (EU) 2024/2984 is not itself a significant new factor (Observed).
- **Legacy tokens.** Art. 143(2)(b) MiCAR: trading platform operators ensure by 31 December 2027 that a white paper is drawn up, notified and published under Art. 6, 8 and 9 and updated under Art. 12 for crypto-assets admitted to trading before 30 December 2024. Art. 143(2)(a) applies Art. 7 and 9 to their marketing communications published after 30 December 2024 (Observed, OJ).
- **Notification packages.** The FMA's guide (September 2025, version 1.0) lists the white paper, the marketing communications and the explanation under Art. 8(4) as uploads, and modified marketing communications for a modification. The CSSF (page updated 3 August 2026) takes Title II notifications through eDesk, the iXBRL file zipped and the Art. 8(4) explanation as a PDF annex (Observed).
- **ESAs' joint guidelines under Art. 97(1)** (final report of 10 December 2024). Annex A is a field-by-field template for the Art. 8(4) explanation: who issues it, the white paper by its notification date, the applicable law, the purported classification, why the asset is a crypto-asset, why it is no ART and no EMT, and why it falls under none of the exclusions of Art. 2(4) (financial instrument, deposit, funds, insurance and pension products and the others listed) (Observed).
- **ESMA MiCA White Paper Reporting Manual v1.0** (July 2025). It names 21 violation codes. 19 concern the markup: `periodWithTimeContent`, `periodWithTimeZone`, `segmentUsed`, `multipleIdentifiers`, two `inconsistentDuplicate…FactInInlineXbrlDocument` codes, `improperApplicationOfEscapeAttribute`, `transformableElementIncludedInHiddenSection`, `factInHiddenSectionNotInReport`, `htmlOrXmlBaseUsed`, `executableCodePresent`, four MIME type and image codes, `undefinedLanguageForTextFact`, `taggedTextFactOnlyInLanguagesOtherThanLanguageOfAReport`, `targetAttributeUsedForMiCAContents` and `externalCssFile`. Two concern the taxonomy's formula assertions, at ERROR and WARNING severity. Guidance 1.1.2 requires each language version to be a separate iXBRL file with consistent content, tagged with the same elements. ESMA's taxonomy page still lists only the 2025 taxonomy, the validation rules workbook `mica_taxonomy_formulas_202507.xlsx` and manual v1.0 (Observed).
- **Deadlines in MiCAR.** Art. 8(5) and Art. 51(11): notification at least 20 working days before publication (Title II and EMT white papers). Art. 12(2): a modified Title II white paper at least seven working days before publication, with the reasons (Observed, OJ).
- **United Kingdom.** The FCA's admissions and disclosures rules (PS26/9) require a qualifying cryptoasset disclosure document (QCDD) for admissions to UK platforms. The FCA's regime page gives 25 October 2027 for the full scope of regulated activities, after an application window from 30 September 2026 to 28 February 2027 (Observed, FCA page).

## 4. Feature candidates

Ranked by impact, evidence and effort as in the [adaptation plan](adaptation-plan.md), then adjusted where reuse of existing code changes the effort. Effort: S, M, L. Every candidate keeps the non-negotiables: no model and no network call in the checking path, outputs without draft text, fail closed, a pass never described as compliance.

| Rank | Candidate | Basis | Evidence | Effort | Notes |
|---|---|---|---|---|---|
| 1 | **Marketing communications checks** | Art. 7(1)(a) to (e), 7(2) MiCAR; Art. 29 and 53 later | Observed | M | Fixed statement of Art. 7(1)(e) in its three addressee forms, English and German (reuse the matcher of `ANNEX_I.NOT_APPROVED_STATEMENT`); website, telephone and e-mail of 7(1)(d) (reuse `contact.py`); labelled as marketing (a); consistency with a given white paper (c): token name and ticker, party names, LEI, DTI, dates, prices, amounts; a marketing date before the white paper's publication date (7(2)); a Review-only list of claims of guaranteed returns or of approval. Art. 143(2)(a) extends it to legacy tokens. The fixed statement exists only in Art. 7, so the ART and EMT variants need their own reading. Needs an ADR for a second document kind and a new rule namespace |
| 2 | **Art. 8(4) explanation checks** | Art. 8(4) MiCAR; ESAs guidelines, Annex A | Observed | M | Each Annex A field answered (placeholders count as missing); every Art. 2(4) exclusion addressed; the explanation's white paper date equals the notification date; names and LEIs equal the white paper's parties; the purported classification fits the white paper type. No competitor found. Same ADR as rank 1; the guidelines need a citation entry in `citations.py`, which today lists acts only |
| 3 | **ESMA filing checks under the format gate** | Reporting Manual v1.0, section 2 | Observed | M | The 19 markup codes as issues of `COMMON.IXBRL_TAGGING`, named by ESMA's code, so users can match them with ESMA's and vendors' messages. The gate stays never-pass, as decided on 2026-11-10 for Arelle assertions. lxml only, so the checks also run in the playground; the hidden-section code needs the taxonomy's element types. Arelle (ADR 0004) stays the route for the two formula codes |
| 4 | **Modified white paper comparison** | Art. 12(2), (4), (6), (7) MiCAR; Q&A 2845 | Observed | M | A `--previous` draft: lists changed fields and sections for the lawyer, checks the submission type (Table 2 F.5, Table 3 B.8, Table 4 B.5: MODI, EROR or CORR), the order of information (12(4)), stated reasons (12(2), (6)), the time stamp (12(7)), unchanged predefined texts, and warns where Q&A 2845 requires the machine-readable format. Whether a change is significant stays the lawyer's call |
| 5 | **Portfolio mode for trading platforms** | Art. 143(2)(b) MiCAR | Observed (law), Inferred (demand) | M | On a directory run: the operator's own data compared across all its white papers (operator section, LEI, contact details, predefined texts), two files for one DTI, open blockers by rule across files. Builds on `--batch-output` |
| 6 | **Future value assertions and absolute claims** | Art. 6(2) and (4) MiCAR | Observed (law), Observed (START flags "non-compliant language") | S | Review only, all sections, named groups and negation handling as in `COMMON.RISK_WARNING`, exempting the loss-of-value statement of Art. 6(5). False positives keep the severity at MAJOR or MINOR |
| 7 | **Notification deadlines** | Art. 8(5), 51(11) MiCAR | Observed | S | At least 20 working days between notification date and publication date (Table 2 fields 01 and F.10, Table 4 I.01 and B.9). Counts weekdays; public holidays are not counted, so a short margin gives Review |
| 8 | **Language-version parity** | Reporting Manual, Guidance 1.1.2 | Observed | S | Two numbered-field files of one white paper answer the same fields with identical codes, dates, amounts, LEIs and DTIs |
| 9 | **Strict mode with acknowledged gates** | ADR 0008; Fail Closed | Inferred (code) | M | `COMMON.IXBRL_TAGGING` never passes, so `--strict` exits 1 for every draft and the starter workflow runs with `strict: 'false'`. Option: an opt-in ledger outside the draft, bound to the file's hash, records who checked the iXBRL file or the deposit floor; strict then passes when every open blocker is an acknowledged never-pass gate for that exact file; outputs show "acknowledged", never "pass". Changes a principle of the adaptation plan, so it needs an owner decision and an ADR |
| 10 | **Citation watch** | Maintenance | Inferred | S | Scheduled workflow outside the checking path: Cellar for new amendments or corrigenda of the acts in `ACT_URLS`, ESMA's taxonomy page for a new taxonomy or manual; opens an issue. Automates the manual checks recorded in `CHANGELOG.md`. Pinned actions, zizmor and actionlint as for other workflows |
| 11 | **Tag-versus-text consistency** | Art. 6(10) MiCAR; Reporting Manual | Inferred (no tool found), Observed (PwC client alert, May 2026: errors in machine-readable data may give rise to civil liability) | L | Compares each tagged fact with the visible answer of its field; the field checks read only visible text today. Needs a concept-to-field map built from the taxonomy package |
| 12 | **Word drafts in the browser, then a Word add-in** | Workflow | Inferred; START and DataTracks sell collaborative drafting (Observed) | M, then L | Browser DOCX import is specified as H5 in the adaptation plan. A Word add-in would run the same Pyodide engine inside Word, without upload |
| 13 | **UK QCDD rule set** | FCA PS26/9 | Observed (FCA page) | L | A second jurisdiction before 25 October 2027. Needs a reading of the FCA rule text and its own namespace |

**Evidence before surface.** The template and point rules have not yet been run against a real notified white paper (`CHANGELOG.md`, 1.3.0). iXBRL white papers have been required since 23 December 2025, so ESMA's register now links real ones. A new study arm that runs the field-level rules on them, committing only hashes, metadata and aggregate counts as the Title II study does, would test the 179 field-only rules (`FIELD_ONLY_RULE_IDS` in `linter.py`) before more rules are added. It needs the owner's manifest decisions (AGENTS.md, section 6).

## 5. Not recommended

- **An MCP server.** `eu-reg-mcp`, from the same suite, already offers a `lint_micar_whitepaper` tool (its glama.ai listing, seen in search results). Keeping it in step with the linter's releases is enough.
- **Readiness scores or colour flags without published checks.** MiCAOracle and Bluprynt work this way (Observed). It breaks cited, reviewable findings.
- **Drafting or pre-filling white papers.** Eunice, TokenEx.Legal and START occupy this segment, and generated disclosure text conflicts with the no-model checking path.
- **Register or GLEIF lookups in the checking path.** They break the offline promise (ADR 0007). Register work fits `micar-register-observatory` better.

## 6. Owner decisions of 2026-11-25

- **Validation first:** a local run of the field-only rules on about ten public iXBRL white papers from ESMA's register, with nothing committed and totals reported back.
- **First feature:** marketing communications checks (rank 1), with an ADR for the second document kind.
- **Strict mode:** an opt-in sign-off file outside the draft, bound to the file's hash, so `--strict` can pass on acknowledged never-pass gates (rank 9); outputs show "acknowledged", never "pass". It needs an ADR, because it revises the adaptation plan's rule that a waiver keeps the exit code.
- **This note:** committed with a draft pull request.

## 7. Validation run on real iXBRL white papers (2026-11-25)

A local run, nothing committed: twelve Title II entries of ESMA's interim register (`OTHER.csv`, rows updated in 2026 whose link ends in .xhtml or .html, at most two per filer), linted with `micar-lint --type other --json` at d5489fe. In 2026, 171 register rows link straight to such a file; three filers account for 148 of them.

- **Coverage.** 10 of the 12 links were numbered-field iXBRL files, and all 79 field-level findings appeared for each (790 in all: 659 pass, 97 review, 34 missing). The other 2 were landing pages, where the field rules did not run, as designed.
- **Template rules flag most often:** `ITS.FIELD_FORMATS` on 9 of 10 files, `ITS.CODE_LISTS` and `RTS.SUSTAINABILITY_INDICATORS` on 7, `ITS.PREDEFINED_TEXT` on 6, `ITS.NOTIFICATION_DATE_FORMAT` and `RTS.CLASSIFICATION_DATA` on 5. Most of these flags are false positives with four causes: a rendering that prints each field's data type before the answer ("date", "text", "textBlock", "enumeration", "boolean"; 3 files); labels or "code (description)" text where the template has a code, and display text such as "Yes" for a boolean, while iXBRL keeps the code or the value in the tag, which the checks do not read; a display date written DD.MM.YYYY (1 file); and text merged into an answer (running page headers, the next heading, and in 1 file a balance-sheet row read as field C.1). A few flags look like real defects: a wrong type code, a ticker in a DTI field and a missing functionally fungible group DTI.
- **Point rules** give 0 or 1 prompts on four files and 10 to 19 on six. Most of those come from "N/A" answers in Part A of white papers drawn up by the operator of the trading platform, and in the offer-only fields of Part E (refunds, oversubscription, transfer schedule) of white papers that seek admission to trading only. Whether those points apply to such white papers is a legal reading to settle once and encode as a condition.
- **Language.** One file in Czech: the label-based language check found no language field.
- **Fix proposals** (not built, owner decision): split a leading data-type word off each answer where most fields carry one; accept a code followed by its description; drop running headers and footers repeated on many pages; read the Inline XBRL fact behind each field (its value, enumeration member or transformed date) for the format and code checks, falling back to the visible text (rank 11); settle the Part A and Part E reading for operator-drafted admission white papers.

## Sources

All accessed 2026-11-25.

- MiCAR, Official Journal XHTML via the Publications Office Cellar: http://publications.europa.eu/resource/celex/32023R1114 (Art. 6, 7, 8, 12, 29, 51, 53, 143)
- ESMA response to the EC consultation on the MiCA review, 30 September 2026: https://www.esma.europa.eu/sites/default/files/2026-09/ESMA75-113276571-1721_Response_to_the_EC_consultation_MiCA_regulation_review.pdf
- ESMA press release, 30 September 2026: https://esma.europa.eu/press-news/esma-news/esma-calls-changes-make-mica-clearer-safer-and-ready-emerging-services
- ESMA Q&A 2845: https://www.esma.europa.eu/publications-data/questions-answers/2845
- ESMA MiCA White Paper Reporting Manual v1.0: https://www.esma.europa.eu/sites/default/files/2025-08/mica_taxonomy_reporting_manual_v1.0.pdf
- ESMA MiCA White Paper Taxonomy 2025: https://www.esma.europa.eu/node/220930
- ESMA MiCA page: https://www.esma.europa.eu/esmas-activities/digital-finance-and-innovation/markets-crypto-assets-regulation-mica
- ESAs' final report on guidelines under Art. 97 MiCAR: https://eba.europa.eu/sites/default/files/2024-12/f4d876e5-5351-4314-b45f-ac3cd702f95b/Joint%20ESA%20Final%20Report%20on%20Art%2097%20Guidelines%20MiCAR.pdf
- FMA, Elektronische Übermittlung von Kryptowerte-Whitepaper iSd Titel II MiCAR, version 1.0: https://webhost.fma.gv.at/epass2/documents/Einreichung_Whitepaper_Titel%20II_MiCAR.pdf
- CSSF, white papers: https://www.cssf.lu/en/white-papers/
- FCA, cryptoasset regime policy statements: https://www.fca.org.uk/publications/policy-statements/cryptoasset-regime
- PwC Legal, START flyer (June 2026): https://legal.pwc.de/content/services/pwc-legal-flyer-micar-start-platform-june-2026.pdf; article of 12 May 2026: https://legal.pwc.de/en/news/articles/a-recap-on-micar-white-paper-machine-readability-requirements; client alert (May 2026): https://legal.pwc.de/content/services/regcore-client-alert/micar-white-paper-machine-readability-requirements-may-2026.pdf
- Bluprynt MiCA Checker docs: https://bluprynt.gitbook.io/bluprynt-docs/mica-checker
- MiCA Crypto Alliance: https://www.micacryptoalliance.com/
- Crypto Risk Metrics: https://crypto-risk-metrics.com/products/ and https://crypto-risk-metrics.com/en/mica-xbrl-checker/
- DataTracks: https://datatracks.com/?p=72659
- CoreFiling: https://www.corefiling.com/mica/
- NorthPoint: https://northpoint.fi/check/mica
- Compliora AI blog post: https://regscope-frontend.pages.dev/blog/mica-whitepaper-ixbrl-requirements-2026
- Eunice (FF News): https://ffnews.com/newsarticle/cryptocurrency/eunice-launches-ai-driven-mica-whitepaper-library-for-scalable-crypto-compliance
- TokenEx.Legal (Product Hunt): https://www.producthunt.com/products/tokenex-legal/launches
- Arelle issue #1898 and validation plugins: https://github.com/Arelle/Arelle/issues/1898, https://github.com/Arelle/Arelle/tree/master/arelle/plugin/validate
- WhitePaperXBRL: https://github.com/Loideroi/WhitePaperXBRL
- ToolOracle MiCAOracle: https://github.com/ToolOracle/micaoracle
