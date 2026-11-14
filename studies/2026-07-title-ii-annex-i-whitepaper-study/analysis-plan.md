# Analysis plan: detector precision and recall on the v1 pilot

> **DRAFT, not adopted; it reaches `main` as unsigned draft tooling and is adopted there in a separate commit.**
>
> Drafted with AI assistance (Claude) on 2026-10-14 for the reviewer's decision. Its `[Decide: ...]` boxes were decided on 10 November 2026 on the owner's instruction to settle the open points on the drafter's recommendation (AI-assisted); each decision says so where it stands. The owner has not reviewed these points individually; they become final only with the owner's adoption commit (step 3 below). Bracketed items that remain (`[ ]`, `[SHA-256]`, `[file]`, `[reviewer name]`, `[YYYY-MM-DD]`, `[Reviewer confirms.]` and the placeholders of the wording templates in section 11) are open.
>
> **Signing order.**
>
> 1. Merge pull requests #18, #19 and #24 into `main` as unsigned DRAFT tooling. Merging them adopts nothing.
> 2. On `main`, complete Phase 0 steps 0.1 to 0.10 (`analysis-plan.md` section 3). Step 0.11 is steps 3 to 5 below.
> 3. Make ONE adoption commit on `main`. It contains the adopted `codebook.md` and `analysis-plan.md` and the pending review sheets `human-review-blinded.csv` and `human-review-matrix.csv`, with the DRAFT line of each banner removed and the "Adopted by" line filled in. This commit is the pre-registration and precedes the commit that adds any label.
> 4. Mark the adoption commit with an annotated tag.
> 5. In a follow-up commit, record the adoption commit's SHA and its tag in the study README ("Current status"), never inside the signed files.
>
> Later changes on `main` to the detector's files do not enter the study: it measures the committed findings file exactly as committed (`analysis-plan.md` section 2, detector decision). Make the adoption commit once the pull requests that change the inputs that `analysis-plan.md` section 2 freezes (the findings files, `document-provenance.json`, the review sheets and `codebook.md`) or `analysis-plan.md` are merged or closed: #18, #19 and #24, and any other. A later change to those inputs is a deviation (`analysis-plan.md` section 12).
>
> - Adopted by: [reviewer name], on [YYYY-MM-DD]
> - Pre-registration commit: not recorded in this file (signing order, step 5)
> - Reference standard recorded in `review-protocol.md` (`REVIEWING.md` step 2): [ ] recorded

This plan contains no per-cell or per-document detector outcomes. The reviewer can read it before labelling.

## 1. Question and estimands

**Question.** On the v1 pilot sample, how often is a detector flag a disclosure gap that the reviewer also finds (precision), and how many of the gaps the reviewer finds does the detector flag (recall)?

**Not the question.** Whether any white paper complies with MiCAR, how common gaps are in ESMA's register, or whether any issuer or offeror omitted a required disclosure (`methodology.md`, `limitations.md`). The reference labels measure **presence** of disclosure elements (`codebook.md`, policy P3), not legal sufficiency.

**Unit.** One document-rule cell: the exact source bytes of one document (SHA-256 in `document-provenance.json`) against one of the 15 rules of the findings file's `rules` list (`STUDY_RULES` in `src/micar_linter/batch.py`; section 2). Ten processed documents give 150 cells.

## 2. Frozen inputs

| Input | Value |
| --- | --- |
| Findings file | `findings-pseudonymous.json`, SHA-256 `3e9c867574a2e38a7ef98a901b6e8480a26a64ecad8790b6956ab1eb7c6825ed`, digest `a0f8a82a135f22738357799c40420a45446b1cef839780859f285d9b958f79c1`, findings schema v1, generated 2026-07-06 |
| Document hashes | `document-provenance.json` (10 documents) |
| Review sheets | `human-review-blinded.csv` and `human-review-matrix.csv`, built from the findings file by `scripts/build_review_matrix.py` with every cell pending; SHA-256 at the pre-registration commit: [SHA-256], [SHA-256]. With a second reviewer, `human-review-second.csv`, built after the first review by `scripts/build_review_matrix.py --second-sheet`, with `--second-all` under rule (a) of section 6 or with the seed and fraction of its rule (b) |
| Codebook | `codebook.md` as adopted in the pre-registration commit |
| Detector | The pilot detector as of July 2026 (`micar-lint-batch` with the 15 rules of `STUDY_RULES`), measured through its output in the Findings file above, exactly as committed (see "Detector freeze" and the detector decision below); detector commit: not recorded. The findings name no commit. `8f37b7c` (13 July 2026) is the earliest public commit whose `STUDY_RULES` metadata equals the findings' `rules` list, a reconstruction that no re-run has tested (step 0.4) |

**Detector freeze.** The study detector is the pilot detector as of July 2026, and the study measures it only through its committed output: `findings-pseudonymous.json` and `findings-pseudonymous.csv`, exactly as committed, never edited and never regenerated (detector decision below). The detector's code is every module that `micar-lint-batch` imports. On `main` at `c0befc2` these include `src/micar_linter/batch.py` (`STUDY_RULES`, lines 43 to 288, 15 rules, and the study path from `build_study_findings` and `_process_study_entry`, lines 356 and 515), `src/micar_linter/document_loader.py` (which imports `sections_from_lines` from `document.py`, and `element_text` and `mark_spacer_gaps` from `xhtml_parser.py` inside its functions), `src/micar_linter/xhtml_parser.py` and `src/micar_linter/document.py`, with `placeholders.py` and, since #17, `rules/annex_i.py` (for `NOT_APPROVED_STATEMENT_EN`, and since #103 also `NOT_APPROVED_STATEMENT_DE`), which `document.py` imports; importing `rules/annex_i.py` loads the whole `rules` package. `batch.py` also imports `linter.py` and `whitepaper.py` at module level, for `build_batch_review_pack` only, and `linter.py` imports `contact.py`, new with #79, and `template_checks.py`, `template_types.py`, `point_fields.py`, `classification_data.py` and `rules/points.py`, new with #98. At `8f37b7c`, `placeholders.py` does not exist and `document_loader.py` does not import `xhtml_parser.py`. Between the pre-registration commit and the computation of results, no detector output other than the committed findings enters the analysis, whatever has changed on `main` since.

`STUDY_RULES` is unchanged in releases 1.2.0 and 1.2.1. Commits on `main` after v1.2.1 changed HTML and XHTML text extraction in `document_loader.py` and `xhtml_parser.py`, and the notification-date and language heading patterns in `document.py`, which `document_loader.py` uses, so a re-run at the current `main` can flag cells differently from the committed findings. Later merges changed `document.py` and `xhtml_parser.py` again: #17 (`dde59ef`: the routing of the Article 6(3) statement, and from `cdf7f8f` the joining of a word hyphenated at a `<br>`), #73 (`63fc170`, "Rücktausch" headings) and #74 (`237993a`, `e80920c`, redemption headings). #64 (`ea01146`) added German not-applicable answers ("entfällt", "nicht anwendbar", "keine" and others) to `placeholders.py`, whose `is_not_applicable` `document.py` uses in heading detection. After `9dc43c8`, #78 (`ea1d90c`), #79 (`76d1a5e`), #81 (`952d6a9`) and #82 (`d662f25`) changed `linter.py`, and #78 and #79 also `whitepaper.py`, `numbered_fields.py` and the `rules` package: #79 added the point rule `ANNEX_I.A.P6` to `rules/annex_i.py`, and the new `contact.py`. None of these four changed `batch.py`, `document_loader.py`, `document.py`, `xhtml_parser.py` or `placeholders.py`. #85 (`f9cd466`) changed only a comment in `ixbrl.py`, and #90 (`c7c99cf`) only comments and docstrings in `linter.py`, `contact.py`, `numbered_fields.py` and `rules/base.py`; `whitepaper.py` imports `ixbrl.py` and `numbered_fields.py` inside a function. After `c7c99cf`, #91 (`168037f`), #77 (`6f32439`), #92 (`4a3deb7`), #93 (`8de9a24`), #97 (`2c47ee6`), #99 (`8c77980`), #100 (`11dbab5`) and #103 (`ab29114`) changed `document.py` again, #91, #77 and #97 also `xhtml_parser.py`, and #100 also `batch.py` (a run that processes no document writes nothing and exits 1) and `placeholders.py` (`is_template_note`); `STUDY_RULES` and `document_loader.py` are unchanged. Every merge after `c7c99cf` except #94 and #101 changed a module that `micar-lint-batch` imports; #106 (`c0befc2`, release 1.3.0) changed only the version in `__init__.py`, which loads with every module of the package, and the project version in `uv.lock`.

**Against `8f37b7c`.** `STUDY_RULES` holds the same 15 rules with the same field values at both commits; one `missing_element` is only reformatted. `batch.py` differs in its output text (such as `human_review_note`), `_portable_path` and `failed_files`, and since #100 in `main_study_batch`, which writes nothing and exits 1 when no document was processed. `placeholders.py` does not exist at `8f37b7c`. `uv.lock` differs only in its format revision and the project version (0.1.0 at `8f37b7c`, 1.3.0 on `main` at `c0befc2`); lxml 6.1.1 and pypdf 6.12.2 are the same. Since #86, Dependabot proposes weekly `uv.lock` updates on `main`. They do not enter the study, which runs no detector.

**Detector decision: freeze.** The study measures `findings-pseudonymous.json` (generated 2026-07-06) exactly as committed, with `findings-pseudonymous.csv`. No step of this study runs `micar-lint-batch` or `scripts/run_batch.py`, and none regenerates the findings or the review sheets. The commit that generated the findings is not recorded, so the Detector row names none. `8f37b7c` (13 July 2026) is the earliest public commit whose `STUDY_RULES` metadata equals the `rules` list of the findings, while earlier public commits, the last of them `44aa613` (11 July), use the earlier rule IDs; it is dated a week after the findings, so it is at most a reconstruction of that detector, and no re-run has tested it. All public wording says "pilot detector as of July 2026" and names no commit (section 11). The changes that `main` made to the detector's files after 2026-07-06 (table below) are out of scope; every result states them as a limitation: the measured detector is not the detector on `main`. A re-run of the detector on the owner's cache, at `8f37b7c` or at any later commit, would be a separate, versioned study (v1.1) with its own findings file, review sheets, codebook and plan; it is not part of this study. A cached document that fails verification in step 0.1 is not labelled in this study.

Decided on 10 November 2026 on the owner's instruction to settle the open points on the drafter's recommendation (AI-assisted). The owner has not reviewed this point individually; it becomes final with the owner's adoption commit (banner, step 3).

**Limitation: merges into `main` after 2026-07-06 that changed the detector's files.** `git log --first-parent --since=2026-07-06 main` on `batch.py`, `document_loader.py`, `document.py`, `placeholders.py` and `xhtml_parser.py` (under `src/micar_linter/`) gives 23 merges up to `c0befc2`. None of them is in the measured detector's output. Other merges changed only other modules that `micar-lint-batch` loads, among them #98 (the seven modules new since `c7c99cf`), #102 (`ixbrl.py`) and #106 (the version in `__init__.py`).

| Merge | Date | Files | What changed |
| --- | --- | --- | --- |
| #6 (`0419a56`, with `8f37b7c`) | 2026-07-13 | `batch.py` | `STUDY_RULES` rule IDs renamed to the IDs the findings carry; `_portable_path`; output texts |
| #5 (`c902707`) | 2026-07-13 | `batch.py`, `document_loader.py` | portable manifest and cache paths; new disclaimer and `human_review_note` texts; XML parsing without entity resolution or network access |
| #20 (`1da1e28`) | 2026-10-15 | `xhtml_parser.py` | bold runs that fill a whole block read as headings |
| #27 (`0ee2db7`) | 2026-10-16 | `batch.py`, `document.py` | one `missing_element` reformatted only; English citations with EUR-Lex links |
| #34 (`a0150b8`) | 2026-10-23 | `document.py`, `document_loader.py`, `placeholders.py` (new) | DOCX and PDF heading detection; placeholder answers |
| #30 (`9d34dcb`) | 2026-10-26 | `batch.py` | `failed_files` count in the batch output |
| #39 (`4466462`) | 2026-10-27 | `xhtml_parser.py` | saved iXBRL viewer pages read |
| #41 (`99cb845`) | 2026-10-27 | `document_loader.py`, `xhtml_parser.py` | words kept whole across spacer spans, text broken at blocks, spacer widths from CSS |
| #42 (`16ea1b4`) | 2026-10-27 | `xhtml_parser.py` | text in nested blocks read once in the heading loader |
| #54 (`4be5e32`) | 2026-10-28 | `document.py` | notification date and language checked on the answer itself |
| #58 (`6df1d72`) | 2026-10-28 | `document.py` | German notification-date headings and compounds |
| #64 (`ea01146`) | 2026-10-29 | `document.py`, `placeholders.py` | German not-applicable answers ("entfällt" and others) |
| #73 (`c152f15`) | 2026-10-29 | `document.py` | German "Rücktausch" headings open the redemption section |
| #17 (`dde59ef`) | 2026-10-29 | `document.py`, `xhtml_parser.py` | routing of the Article 6(3) first-page statement; a word hyphenated at a `<br>` joined |
| #74 (`06518f3`) | 2026-10-29 | `document.py`, `xhtml_parser.py` | redemption headings: risk headings stay with the risks, the rights section stays open under a redemption sub-heading |
| #91 (`168037f`) | 2026-11-03 | `document.py`, `xhtml_parser.py` | regime reading of wrapped and nested list items; linear-time reading of long inline runs and long words; every LEI-like code read in all text |
| #77 (`6f32439`) | 2026-11-03 | `document.py`, `xhtml_parser.py` | first-page statement lines kept whole; text after the statement kept in its section |
| #92 (`4a3deb7`) | 2026-11-04 | `document.py` | revert of #91's regime list-item change |
| #93 (`8de9a24`) | 2026-11-04 | `document.py` | hidden-text and regime limits stated and pinned |
| #97 (`2c47ee6`) | 2026-11-04 | `document.py`, `xhtml_parser.py` | text "as shown" for `COMMON.LEI_CHECK_DIGITS`; crash and quadratic-path fixes |
| #99 (`8c77980`) | 2026-11-07 | `document.py` | shown reading of PDF form matrices and `/VE` arrays; fallbacks on unreadable resources |
| #100 (`11dbab5`) | 2026-11-10 | `batch.py`, `document.py`, `placeholders.py` | a run that processes no document writes nothing and exits 1; part titles; `is_template_note` |
| #103 (`ab29114`) | 2026-11-11 | `document.py` | German first-page statement in its Official Journal wording |

## 3. Prerequisites before labelling (Phase 0)

| # | Step | Owner | Status |
| --- | --- | --- | --- |
| 0.1 | Locate the original cache and run `uv run micar-study-verify-cache --provenance studies/2026-07-title-ii-annex-i-whitepaper-study/document-provenance.json --cache .study-cache/title-ii-whitepapers --include-candidates`. It must exit 0; the check in `REVIEWING.md` step 1 is the same comparison with `shasum`. If any document is missing or differs and its original bytes cannot be recovered, this study does not label it: a re-fetch and a re-run of the detector would be the separate, versioned study v1.1 (section 2, detector decision). Do not label bytes the detector did not see. | Reviewer | [ ] |
| 0.2 | Reconcile the 10 entries against ESMA's current Title II register CSV, as `methodology.md` requires; record the CSV URL, retrieval date and SHA-256. Check whether `https://www.esma.europa.eu/sites/default/files/2024-12/OTHER.csv` still resolves. | Reviewer | [ ] |
| 0.3 | Explain the input-manifest mismatch. `findings-summary.md:28` and the findings file name `micar_title_ii_whitepaper_20_source_pack/source-manifest.json` as input; `source-manifest.json` names `sample-manifest.csv`. Both record input SHA-256 `518e1069...`, while the committed `sample-manifest.csv` hashes to `6e0e6171...` and has 10 rows against 20 manifest entries. | Reviewer | [ ] |
| 0.4 | Confirm the detector record of section 2 (decided: freeze). The findings file (generated 2026-07-06) does not record the commit that generated it. The profile repository's claim ledger names linter `57d0e94` as the frozen rule engine for this review ([ledger line 74 at profile commit `01bec48`](https://github.com/sebastianfoerste/sebastianfoerste/blob/01bec486b13abac8f77b92944225e6fbb3fffbff/docs/portfolio-claim-ledger.md#L74)). The ledger was later removed from the profile repository (`2cf6f87`); the link stays, because it is pinned to `01bec48`, which the profile repository's `main` still contains. The same ledger's rows 7, 9 and 10 date `57d0e94` as linter main on 2026-09-19, after the findings run and after release v1.0.0 (2026-07-17, ledger line 16), so `57d0e94` is not the commit that generated the findings. The drafting clone was shallow (HEAD `db939d8`). A full clone on 2026-10-28 shows that `57d0e94` is tag v1.1.0 and that `8f37b7c` is the earliest public commit whose `STUDY_RULES` metadata equals the findings' `rules` list (section 2, detector decision). `8f37b7c` is dated a week after the findings, and no earlier public commit carries their rule IDs, so no public commit is known to have generated them. The study does not re-run the detector to test a commit: it measures the committed findings as they are, the Detector row names no commit, and `8f37b7c` is named only as a reconstruction (section 2). | Reviewer | [ ] |
| 0.5 | Confirm whether any study rule was written or changed after viewing these documents. If yes, or if this cannot be ruled out, the results are described as **in-sample**. | Reviewer | [ ] |
| 0.6 | Record the reference standard in `review-protocol.md`: the rules' missing-element descriptions or the provisions as a whole (`REVIEWING.md` step 2). The codebook's cards and policies P3 and P4 follow that record. | Owner | [ ] |
| 0.7 | Decide the codebook policies P1 to P17 (`codebook.md`, section 6), including the rule-card judgments P11 to P17. The LEI decision (`codebook.md` section 5, box after card 5.2) and the readings that the table in `REVIEWING.md` step 3 does not close were settled on the Official Journal text read on EUR-Lex on 14 November 2026 (`codebook.md` section 1); confirm them. | Reviewer | [ ] |
| 0.8 | Confirm the WP-007 exclusion rule (decided: section 5, under eligibility criterion 4, with the sensitivity analysis S1 that includes WP-007). | Reviewer | [ ] |
| 0.9 | Find a second qualified reviewer for the ranked rule of section 6 (decided). Name them and record their study ID before they start, and before the pre-registration commit where possible; the rule of section 6 then sets which cells they assess and how `scripts/build_review_matrix.py --second-sheet` runs (`--second-all` under rule (a), `--seed` and `--fraction` under rule (b)). The second sheet can be built only after the first review, because it includes the cells the first reviewer labelled `uncertain`, `extraction_failure` or `not_applicable`. | Reviewer | [ ] |
| 0.10 | Label the calibration document (section 4), outside the committed review sheets, and finalise the codebook. | Reviewer | [ ] |
| 0.11 | On `main`, make the one adoption commit of the signing order (banner): the adopted codebook, this plan and the pending sheets; tag it and record its SHA outside the signed files. | Reviewer | [ ] |

The decisions in steps 0.1, 0.4, 0.7, 0.8 and 0.9 were made on 10 November 2026 on the owner's instruction to settle the open points on the drafter's recommendation (AI-assisted). The owner has not reviewed them individually; they become final with the owner's adoption commit (banner, step 3), and the owner still carries out every step of this table.

## 4. Calibration document

Calibration fixes the codebook's wording against a real document before the 150 cells are labelled. Its labels never enter any metric.

- **Default:** one document from WP-013 to WP-020, which are outside the v1 sample. Take the first of them, in the order below, whose bytes are cached, and record its file name and SHA-256 here: [file], [SHA-256]. The order is the ascending SHA-256 of `20261014|calibration|<study_doc_id>`: **WP-015, WP-017, WP-014, WP-016, WP-018, WP-020, WP-013, WP-019.** `source-manifest.json` describes all eight as hosted white-paper articles in HTML, so check that the cached bytes are a white paper before using one. `micar-study-verify-cache --include-candidates` lists which of them are cached.
- **Fallback, if none of WP-013 to WP-020 is cached:** calibrate on one in-sample document and **exclude it from every metric**. Choose it by the same rule over the in-sample documents other than WP-007: **WP-012, WP-004, WP-010, WP-001, WP-009, WP-003, WP-002, WP-011, WP-005** (take the first). Its 15 cells are labelled like any other, carry the note `calibration`, and are reported separately. Step 0.10 comes before the adoption commit, which holds only pending sheets (signing order, step 3), so these labels cannot be in `human-review-blinded.csv` at that commit. Decided: until the adoption commit they are kept outside the repository, in a copy of that document's 15 rows of `human-review-blinded.csv`. After the adoption commit they enter `human-review-blinded.csv` unchanged, in a commit of their own and before any other label, each with the date on which it was made as `reviewed_at` and the note `calibration`; the report says that these labels predate the pre-registration.
- **Document counts under the fallback.** With WP-007 excluded from the primary analysis (section 5), the primary analysis then has **8 documents (120 cells)**, and the sensitivity analysis that includes WP-007 has **9 documents (135 cells)**. The study plan's decision 13 says "report N = 9 documents"; that figure matches the WP-007-inclusive analysis only. [Reviewer confirms.]
- **Alternative considered:** calibrate on WP-007, which is excluded from the primary analysis anyway. This keeps the primary analysis at 9 documents, but WP-007 is a poor calibration document (section 5) and would drop out of the sensitivity analysis. Rejected: section 5 keeps WP-007 in the sensitivity analysis S1.

The decisions of this section (where the fallback's labels are kept, and the rejected alternative) were made on 10 November 2026 on the owner's instruction to settle the open points on the drafter's recommendation (AI-assisted). The owner has not reviewed them individually; they become final with the owner's adoption commit (banner, step 3).

## 5. Eligibility and the WP-007 rule

**Rule.** WP-007 is excluded from the primary analysis under eligibility criterion 4, "Parseable XHTML, HTML, PDF, or text with acceptable extraction quality" (`methodology.md:43`).

**Ground.** The sampling notes suggest that the captured bytes may be a documentation landing page rather than the complete white paper:

- `sample-manifest.csv` gives WP-007's format as "HTML documentation page";
- `source-manifest.json` (retrieved 2026-07-03T07:15 UTC, before the batch run) notes for WP-007: "Docs page; may link PDF or require rendered-site extraction."

Whether the bytes contain the complete white paper is uncertain until the reviewer reads them.

**Recorded at batch processing** (`document-provenance.json`, processed 2026-07-03T07:30 UTC), and **not** a ground for the exclusion:

- WP-007's text extraction is recorded as `ok`, with no warnings and 27 labels found.
- WP-007 records 0 Inline XBRL tags, but so do 8 of the 10 documents (WP-003, WP-004, WP-005, WP-007 and the PDFs WP-009 to WP-012), so this does not set WP-007 apart.

The extraction record therefore shows no measured extraction defect. The exclusion rests on the doubt about what was captured, not on extraction quality as measured. **Decision:** the exclusion stands, under eligibility criterion 4 as stated in the rule above: a capture that may be a landing page instead of the white paper is not text of acceptable extraction quality for this study, whatever the extractor recorded. The unit definition in section 1 is not used as a ground. WP-007 is excluded from the primary analysis and included in the sensitivity analysis S1 (section 7). Decided on 10 November 2026 on the owner's instruction to settle the open points on the drafter's recommendation (AI-assisted). The owner has not reviewed this point individually; it becomes final with the owner's adoption commit (banner, step 3).

**Disclosure.** This rule is fixed after the detector output was produced and published. It is therefore reported as a post-hoc exclusion, and the sensitivity analysis that includes WP-007 (S1) is reported next to the primary result with equal prominence. The results report also states how many of the detector's flags fall in WP-007, taken from the findings file after labelling.

**Handling.** WP-007's 15 cells are labelled like any other, under `codebook.md` policy P8; no label is pre-filled. The capture problem is reported as a pipeline finding.

## 6. Reviewers and blinding

- **Design: a ranked rule (decided).** The tool's author makes the first review. A second review follows the first rule that the available reviewers allow:
  - (a) a full second review of all 150 cells whenever a second qualified reviewer is available. This is the pre-registered design;
  - (b) if the second reviewer can review only part, the protocol's subset (below), with a share of 0.2 of the non-flagged cells and a seed that nobody knows in advance;
  - (c) with no second reviewer, single review by the tool's author, disclosed: `review-protocol.md` ("Second review and adjudication") requires the report to state that the labels are single-reviewed if no second reviewer is available. Every reported figure says so.

  The report states which rule applied and why. Decided on 10 November 2026 on the owner's instruction to settle the open points on the drafter's recommendation (AI-assisted), with the adjudication rule below. The owner has not reviewed these points individually; they become final with the owner's adoption commit (banner, step 3).
- **Partial blinding.** The reviewer wrote the detector and has had access to the published flag counts and examples in `findings-summary.md`. The review sheet (`human-review-blinded.csv`) hides detector outcomes; its rows follow the findings order, the same `STUDY_RULES` order for every document, which does not depend on the detector's result. Blinding is still partial and is disclosed as such.
- **Procedure.** The reviewer labels only `human-review-blinded.csv`, following `REVIEWING.md` and using `codebook.md`, `review-protocol.md` and the source documents. During labelling the reviewer does not open `human-review-matrix.csv`, `findings-pseudonymous.*`, `findings-summary.md` or playground output for these documents. The finished labels are committed on their own, before the merge with detector outcomes (`scripts/build_review_matrix.py --merge-blinded`, `REVIEWING.md` step 4), so that the commit order shows labels before merge.
- **Second reviewer.** A qualified lawyer. `review-protocol.md` ("Second review and adjudication") has a second reviewer assess every flagged cell, every `uncertain`, `extraction_failure` or `not_applicable` cell and at least 20% of randomly selected non-flagged cells; `REVIEWING.md` ("Time estimate") counts at least 47 such cells here. Once the first review is complete, `scripts/build_review_matrix.py --second-sheet` (`REVIEWING.md` step 3a) writes the cells to review to `human-review-second.csv`: under rule (a) all 150, with `--second-all`; under rule (b) the protocol's cells, whose random part takes the share `--fraction` of the non-flagged cells with the lowest SHA-256 of `<seed>|second-review|<study_doc_id>|<rule_id>`, so it depends on no label and can be repeated. Under rule (b) the command runs with `--fraction 0.2`, which draws 26 of the 129 non-flagged cells, and with `--seed` set to the integer value of the first 8 hex digits of the commit that records the completed first review, which nobody knows before that commit exists: `python3 -c 'import sys; print(int(sys.argv[1][:8], 16))' "$(git rev-parse <commit>)"`. The command's default seed, `20261014`, is not the plan's seed. The merge checks only that the sheet holds the protocol's cells and at least 20% of the non-flagged cells, not that they are this draw, so the report states the commit, the seed and the fraction, with which anyone can recompute it. The subset holds all 21 flagged cells, so the second reviewer knows that it is enriched for flagged cells; the report discloses this partial unblinding. The second reviewer labels only that sheet and does not open `human-review-blinded.csv`. No AI system acts as a reviewer or adjudicator, and no AI pass counts as human review.
- **Adjudication.** `review-protocol.md` has disagreements adjudicated by "a qualified reviewer", who records the final label and the reasoning. `scripts/build_review_matrix.py --disagreements` lists them in `human-review-adjudication.csv`, without detector columns, and the merge writes the adjudicated labels into the matrix with a note naming both reviews' labels. Decided: the two reviewers adjudicate together by consensus, with written reasons, or a person who made neither review adjudicates; neither reviewer adjudicates alone, so that the first reviewer, who wrote the detector, does not settle a disagreement alone. The command accepts these two and refuses one of the two reviewers alone. `review-protocol.md` stays as it is; its "a qualified reviewer" covers both.

## 7. Analysis sets

| Set | Documents | Cells | Use |
| --- | --- | --- | --- |
| Primary | the 10 processed documents without WP-007, and without an in-sample calibration document if one is used | 135 (120 under the fallback) | Headline precision and recall |
| Full | all 10 processed documents, without an in-sample calibration document if one is used | 150 (135 under the fallback) | Sensitivity analysis S1 |

Within a set, **evaluable cells** are those labelled `present` or `missing`. Every report states N evaluable and the count of each excluded label (`uncertain`, `not_applicable`, `extraction_failure`).

## 8. Primary metrics

From the final labels and the detector status (`review-protocol.md`, Metric calculation; `src/micar_linter/review_validation.py`):

- TP: flagged and `missing`; FP: flagged and `present`; FN: not flagged and `missing`; TN: not flagged and `present`.
- **Precision** = TP / (TP + FP). **Recall** = TP / (TP + FN).
- Reported with TP, FP, FN, TN and N evaluable. F1 and specificity are secondary. Accuracy is not reported as a headline, because true negatives would dominate it.
- A metric whose denominator is 0 is reported as undefined, not as 0% or 100%.
- F1 is 2TP / (2TP + FP + FN), as `METRIC_NOTE` in `src/micar_linter/review_validation.py` defines it: undefined whenever precision or recall is undefined, and 0 when both are defined and TP is 0.
- If TP + FN is below 10, recall is also stated as "X of Y reviewer-identified gaps".

## 9. Intervals

All intervals are two-sided 95%.

1. **Wilson score interval** for each proportion (z = 1.959964), labelled "assumes independent cells".
2. **Clopper-Pearson exact interval**, reported alongside.
3. **Document-cluster percentile bootstrap.** Resample the documents of the analysis set with replacement (as many draws as documents), pool the cells of the drawn documents, and recompute the metric; B = 10,000 replicates; seed `20261014`. Replicates with a zero denominator are dropped and their number is reported. With 8 to 10 clusters this interval is unstable; the report says so.

**Headline interval:** whichever of the Wilson interval and the document-cluster bootstrap interval has the greater width (upper bound minus lower bound), named in the text ("document-clustered" or "Wilson"). If more than 10% of bootstrap replicates are dropped for a zero denominator, the Wilson interval is the headline and the bootstrap interval is reported as unstable. This section names the interval method; `review-protocol.md` names none and stays as it is. The 10% limit was decided on 10 November 2026 on the owner's instruction to settle the open points on the drafter's recommendation (AI-assisted). The owner has not reviewed this point individually; it becomes final with the owner's adoption commit (banner, step 3).

## 10. Secondary and sensitivity analyses

- Per-rule and per-document counts of TP, FP, FN, TN and excluded labels. No per-rule precision or recall is headlined, because each rule has at most 10 cells.
- Per-document and per-offeror counts (including the per-offeror detail of S2) are computed for internal quality checks and are not reported as figures. They can be derived from the label files, which section 11 publishes with the result, and so only after the conflicts check and the legal review under `review-protocol.md` ("Publication gate", item 6) are complete.
- **S1:** the full set, including WP-007.
- **S2:** one document per offeror. WP-003, WP-004 and WP-005 share one offeror, and WP-011 and WP-012 share one (`source-manifest.json`, `offeror_or_issuer`). Report (a) an offeror-cluster bootstrap with the settings of section 9 and (b) the deterministic variant that keeps the lowest-numbered document per offeror.
- **S3 and S4:** `uncertain` counted as `missing`, then as `present`, to bound the result.
- **S5:** the labels under the other reference standard that reviewers record in `review_note` (`REVIEWING.md` line 82; for example the business addresses under Part A item 8, or the Art. 6(6) statement that the white paper makes no omission likely to affect its import), and the stricter readings recorded in notes under `codebook.md` P4, where the notes allow it; and the cells of cards 5.1 and 5.2 whose note reads "LEI given", counted as `not_applicable` (`codebook.md`, box after card 5.2).
- **Inter-rater agreement, if double-reviewed:** raw agreement; Cohen's kappa on present/missing and on all labels; PABAK or Gwet's AC1. State which cells were double-reviewed: under the protocol's subset (section 6) they include every flagged cell and every cell the first reviewer labelled `uncertain`, `extraction_failure` or `not_applicable`, so agreement on them does not describe the 150 cells.
- Results are computed by tooling from the committed label files and copied from its JSON output; no figure is computed by hand. On `main`, `micar-review-summary` computes the confusion matrix, precision, recall and F1 (`human-review-summary.json`), but not the intervals of section 9 or the analyses of this section.

## 11. Reporting rules

- **Aggregate figures.** Report aggregate metrics; the text of the result reports no figure per cell, per document or per offeror. WP identifiers are pseudonymous, not anonymous: `source-manifest.json` maps them to named entities and URLs. The study plan's decision 15 (no publication of per-cell, issuer-identifiable labels) is replaced by the next bullet, and the report says so.
- **Labels file and the public repository.** This repository is public, so pushing a completed `human-review-blinded.csv` or `human-review-second.csv`, the adjudication file `human-review-adjudication.csv`, or `human-review-matrix.csv` after the merge, publishes per-cell labels. Decided: the cell labels, pinpoints and reviewer pseudonyms of all three sheets (`human-review-blinded.csv`, `human-review-second.csv` and `human-review-adjudication.csv`) and of the matrix are published with the result, which comes only after the checks of the next bullet; until then the labels are committed locally and not pushed. The free-text notes (`review_note`, and `adjudication_reason` in the adjudication file) are reviewed for quoted document text before they are published. Decided on 10 November 2026 on the owner's instruction to settle the open points on the drafter's recommendation (AI-assisted), with the wording options adopted below. The owner has not reviewed these points individually; they become final with the owner's adoption commit (banner, step 3).
- **Before any statement about a named issuer or offeror:** a conflicts check covering both the persons who drew up the papers and the token issuers named in them, and the separate qualified legal review that `review-protocol.md` ("Publication gate", item 6) requires.
- **Never** describe the result as "accuracy", "validated", a detection rate for MiCAR violations, a compliance rate or a prevalence estimate. This section governs public wording: the closing sentence of `review-protocol.md` ("Publication gate": "supports reporting detector validation") and the study README heading "Validate against human labels" describe the procedure, not a result.
- **Disclosures with every figure:** reviewer = tool author; partial blinding; single-reviewed, or which cells a second reviewer reviewed (section 6, rules (a) to (c); under rule (b) the subset holds every flagged cell); in-sample (unless step 0.5 rules it out); convenience sample of 10 documents; the measured detector is the pilot detector as of July 2026, measured through its committed findings, not the detector on `main` (section 2, detector decision and limitation).

- **Name the measured component.** Every figure is about the linter's batch study detector as of July 2026 (15 Annex I and Article 6 checks, measured through its committed findings; section 2), not the rule engine that the CLI and the GitHub Action run. The wording says "pilot detector as of July 2026" and names no commit. Never "validated".

**Wording templates** (from the study plan, section 3.4, with the options decided on 10 November 2026 on the owner's instruction (AI-assisted), final with the adoption commit; fill only from the computed JSON):

- Study summary: "Pilot batch study detector as of July 2026 (15 Annex I and Article 6 checks): precision X% (95% CI a to b, document-clustered) and recall Y% (c to d) on N evaluable of the 135 primary-analysis cells (150 document-rule cells from 10 public white papers from ESMA's interim register × 15 rules, less WP-007's 15 cells, excluded from the primary analysis under a rule fixed before labelling but after the detector output (post-hoc; see S1); M excluded as uncertain, not applicable or extraction failure), against [labels as section 6 applied: (a) the tool author's partially blinded labels and a second lawyer's labels on all 150 cells, Cohen's κ = k, disagreements adjudicated | (b) the tool author's partially blinded labels, second-reviewed on S cells that include every flagged cell, Cohen's κ = k on those cells, disagreements adjudicated | (c) the tool author's partially blinded labels, single-reviewed]. [In-sample] pilot on a convenience sample; not a prevalence or compliance finding."
  - Adopted: the study plan's wording "excluded ... as pre-registered" is replaced, because section 5 discloses the exclusion as post-hoc and "as pre-registered" alone suggests the rule came before the detector output.
  - Adopted: the primary set has 135 cells (120 under the calibration fallback), not 150; under the fallback, the parenthesis also subtracts the calibration document's 15 cells.
  - "from ESMA's interim register" holds only after step 0.2.
  - If TP + FN is below 10, state recall as "X of Y reviewer-identified gaps".
- Profile README line: "[In-sample] pilot of my MiCAR linter's batch study detector as of July 2026 (15 Annex I and Article 6 checks) on 10 public ESMA-register white papers (one excluded, see study): precision X%, recall Y% against my own partially blinded, single-reviewed labels ([study](https://github.com/sebastianfoerste/micar-whitepaper-linter/tree/main/studies/2026-07-title-ii-annex-i-whitepaper-study))." Under rule (a) of section 6, replace the label description with "my own and a second lawyer's labels (κ = k)"; under rule (b), with "my own labels, partly second-reviewed by a second lawyer (κ = k)".
  - Drop "[In-sample]" only if step 0.5 rules it out.
  - "ESMA-register" holds only after step 0.2.
  - Adopted: "(one excluded, see study)", because the headline figures come from 9 documents (8 under the calibration fallback), not 10. It adds two words to the profile README's word budget.
- CV or application sentence: "I measured the batch study detector as of July 2026 of my MiCAR white-paper linter (15 Annex I and Article 6 checks) against my own partially blinded, single-reviewed presence review of 10 public white papers from ESMA's register (one excluded, see study): [in-sample] precision X% (95% CI a to b), recall Y% (c to d) on N of the 135 primary-analysis cells[; second-reviewer agreement κ = k]." Never "validated". Under rules (a) and (b) of section 6, replace "single-reviewed" as in the profile README line.
  - Drop "[in-sample]" only if step 0.5 rules it out.
  - The 150-versus-135 note of the study summary applies.
  - "from ESMA's register" holds only after step 0.2.
  - Adopted: "presence review" in place of "legal review", which can be read as a review of legal sufficiency, while the labels record presence only (`codebook.md`, P3).

## 12. Deviations

Any change after the pre-registration commit is logged here with date, change, reason and whether any label had been seen, and is reported with the results.

| Date | Deviation | Reason | Labels seen? |
| --- | --- | --- | --- |
| | | | |
