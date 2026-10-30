# Analysis plan: detector precision and recall on the v1 pilot

> **DRAFT, not adopted; it reaches `main` as unsigned draft tooling and is adopted there in a separate commit.**
>
> Drafted with AI assistance (Claude) on 2026-10-14 for the reviewer's decision. Bracketed items (`[ ]`, `[SHA]`, `[Decide: ...]`) are open.
>
> **Signing order.**
>
> 1. Merge pull requests #18, #19 and #24 into `main` as unsigned DRAFT tooling. Merging them adopts nothing.
> 2. On `main`, complete Phase 0 steps 0.1 to 0.10 (`analysis-plan.md` section 3). Step 0.11 is steps 3 to 5 below.
> 3. Make ONE adoption commit on `main`. It contains the adopted `codebook.md`, `analysis-plan.md` with the Detector row of its section 2 filled in, and the pending review sheets `human-review-blinded.csv` and `human-review-matrix.csv`, with the DRAFT line of each banner removed and the "Adopted by" line filled in. This commit is the pre-registration and precedes the commit that adds any label.
> 4. Mark the adoption commit with an annotated tag.
> 5. In a follow-up commit, record the adoption commit's SHA and its tag in the study README ("Current status"), never inside the signed files.
>
> Later changes on `main` to the detector's files do not enter the study: every study run uses the detector commit recorded in `analysis-plan.md` section 2, with its `uv.lock`. Make the adoption commit once the pull requests that change the inputs that `analysis-plan.md` section 2 freezes (the findings files, `document-provenance.json`, the review sheets and `codebook.md`) or `analysis-plan.md` are merged or closed: #18, #19 and #24, and any other. A later change to those inputs is a deviation (`analysis-plan.md` section 12).
>
> - Adopted by: [reviewer name], on [YYYY-MM-DD]
> - Pre-registration commit: not recorded in this file (signing order, step 5)
> - Reference standard recorded in `review-protocol.md` (`REVIEWING.md` step 2): [ ] recorded

This plan contains no per-cell or per-document detector outcomes. The reviewer can read it before labelling.

## 1. Question and estimands

**Question.** On the v1 pilot sample, how often is a detector flag a disclosure gap that the reviewer also finds (precision), and how many of the gaps the reviewer finds does the detector flag (recall)?

**Not the question.** Whether any white paper complies with MiCAR, how common gaps are in ESMA's register, or whether any issuer or offeror omitted a required disclosure (`methodology.md`, `limitations.md`). The reference labels measure **presence** of disclosure elements (`codebook.md`, policy P3), not legal sufficiency.

**Unit.** One document-rule cell: the exact source bytes of one document (SHA-256 in `document-provenance.json`) against one of the 15 rules in `STUDY_RULES` (`src/micar_linter/batch.py` at the detector commit recorded in section 2). Ten processed documents give 150 cells.

## 2. Frozen inputs

| Input | Value |
| --- | --- |
| Findings file | `findings-pseudonymous.json`, SHA-256 `3e9c867574a2e38a7ef98a901b6e8480a26a64ecad8790b6956ab1eb7c6825ed`, digest `a0f8a82a135f22738357799c40420a45446b1cef839780859f285d9b958f79c1`, findings schema v1, generated 2026-07-06 |
| Document hashes | `document-provenance.json` (10 documents) |
| Review sheets | `human-review-blinded.csv` and `human-review-matrix.csv`, built from the findings file by `scripts/build_review_matrix.py` with every cell pending; SHA-256 at the pre-registration commit: [SHA-256], [SHA-256]. With a second reviewer, `human-review-second.csv`, built after the first review by `scripts/build_review_matrix.py --second-sheet` with the seed and fraction fixed in section 6 |
| Codebook | `codebook.md` as adopted in the pre-registration commit |
| Detector | `micar-lint-batch` at the detector commit, with its `uv.lock` (see "Detector freeze" below); detector commit: [SHA, see step 0.4 and the detector decision below] |

**Detector freeze.** The study detector is the detector commit recorded in section 2 with its `uv.lock`: every module that `micar-lint-batch` imports at that commit. On `main` at `d662f25` these include `src/micar_linter/batch.py` (`STUDY_RULES`, lines 42 to 287, 15 rules, and the study path from `build_study_findings` and `_process_study_entry`, lines 355 and 514), `src/micar_linter/document_loader.py` (which imports `sections_from_lines` from `document.py`, and `element_text` and `mark_spacer_gaps` from `xhtml_parser.py` inside its functions), `src/micar_linter/xhtml_parser.py` and `src/micar_linter/document.py`, with `placeholders.py` and, since #17, `rules/annex_i.py` (for `NOT_APPROVED_STATEMENT_EN`), which `document.py` imports; importing `rules/annex_i.py` loads the whole `rules` package. `batch.py` also imports `linter.py` and `whitepaper.py` at module level, for `build_batch_review_pack` only, and `linter.py` imports `contact.py`, new with #79. Freezing the whole detector commit with its `uv.lock` covers all of them. At `8f37b7c`, `placeholders.py` does not exist and `document_loader.py` does not import `xhtml_parser.py`. Between the pre-registration commit and the computation of results, no other version of these files may enter the analysis: every study run of `micar-lint-batch` uses that commit and its `uv.lock`, whatever has changed on `main` since. `findings-pseudonymous.json` and `findings-pseudonymous.csv` are not edited.

`STUDY_RULES` is unchanged in releases 1.2.0 and 1.2.1. Commits on `main` after v1.2.1 changed HTML and XHTML text extraction in `document_loader.py` and `xhtml_parser.py`, and the notification-date and language heading patterns in `document.py`, which `document_loader.py` uses, so a re-run at the current `main` can flag cells differently from the committed findings. Later merges changed `document.py` and `xhtml_parser.py` again: #17 (`dde59ef`: the routing of the Article 6(3) statement, and from `cdf7f8f` the joining of a word hyphenated at a `<br>`), #73 (`63fc170`, "Rücktausch" headings) and #74 (`237993a`, `e80920c`, redemption headings). #64 (`ea01146`) added German not-applicable answers ("entfällt", "nicht anwendbar", "keine" and others) to `placeholders.py`, whose `is_not_applicable` `document.py` uses in heading detection. After `9dc43c8`, #78 (`ea1d90c`), #79 (`76d1a5e`), #81 (`952d6a9`) and #82 (`d662f25`) changed `linter.py`, and #78 and #79 also `whitepaper.py` and the `rules` package: #79 added the point rule `ANNEX_I.A.P6` to `rules/annex_i.py`, and the new `contact.py`. None of these four changed `batch.py`, `document_loader.py`, `document.py`, `xhtml_parser.py` or `placeholders.py`. Open pull request #77 changes `document.py` and `xhtml_parser.py` once more.

**Against `8f37b7c`.** `STUDY_RULES` holds the same 15 rules with the same field values at both commits; one `missing_element` is only reformatted. `batch.py` differs in its output text (such as `human_review_note`), `_portable_path` and `failed_files`. `placeholders.py` does not exist at `8f37b7c`. `uv.lock` differs only in its format revision and the project version (0.1.0 at `8f37b7c`, 1.2.1 on `main`); lxml 6.1.1 and pypdf 6.12.2 are the same.

**Detector decision (owner).** [Decide:

- (A) **Freeze.** Name `8f37b7c` (13 July 2026), the earliest public commit matching the committed findings: its `STUDY_RULES` metadata equals the `rules` list of `findings-pseudonymous.json`, while earlier public commits, the last of them `44aa613` (11 July), use the earlier rule IDs. `8f37b7c` is dated a week after the findings (`generated_at` 2026-07-06), so it is not the commit that generated them but a reconstruction of that detector. Re-run `micar-lint-batch` at it on the verified cache in step 0.4 and compare `results[]`; name it in the Detector row only if the re-run reproduces them, and say with the results that the detector commit is a reconstruction. All public wording says "pilot detector as of July 2026". [Decide, if the re-run does not reproduce `results[]`: (B), or another commit whose re-run does.]
- (B) **Regenerate.** Re-run at a tagged release before any labelling, rebuild the sheets with `scripts/build_review_matrix.py` (all cells are pending), update the Findings file row of the table above and every committed file that such a refresh puts out of step, as the study README ("Reproduce the detector output") and `AGENTS.md` section 6 list them: among them `findings-summary.md`, `human-review-summary.json`, the candidate-gap figure in the study README's "Current status", the basis figures of the playground (`docs/playground/index.html`), the pilot figures in `docs/overview.md`, `REVIEWING.md` (the table in its step 3 and the figures it states, such as "30 of the 150 cells" in step 1 and the 21 flagged and 26 of the 129 non-flagged cells under "Time estimate") and the `extraction_metadata` in `document-provenance.json`, and, if the documents processed change, `docs/DETAILS.md`, `methodology.md`, `limitations.md`, `source-manifest.json` and `sample-manifest.csv`. Call the result study v1.1, as step 0.1 does.

(B) is required if any cached file fails verification in step 0.1.]

## 3. Prerequisites before labelling (Phase 0)

| # | Step | Owner | Status |
| --- | --- | --- | --- |
| 0.1 | Locate the original cache and run `uv run micar-study-verify-cache --provenance studies/2026-07-title-ii-annex-i-whitepaper-study/document-provenance.json --cache .study-cache/title-ii-whitepapers --include-candidates`. It must exit 0; the check in `REVIEWING.md` step 1 is the same comparison with `shasum`. If any document is missing or differs, re-fetch, re-run `micar-lint-batch`, rebuild the sheets with `scripts/build_review_matrix.py`, and label the result study v1.1. Do not label bytes the detector did not see. | Reviewer | [ ] |
| 0.2 | Reconcile the 10 entries against ESMA's current Title II register CSV, as `methodology.md` requires; record the CSV URL, retrieval date and SHA-256. Check whether `https://www.esma.europa.eu/sites/default/files/2024-12/OTHER.csv` still resolves. | Reviewer | [ ] |
| 0.3 | Explain the input-manifest mismatch. `findings-summary.md:28` and the findings file name `micar_title_ii_whitepaper_20_source_pack/source-manifest.json` as input; `source-manifest.json` names `sample-manifest.csv`. Both record input SHA-256 `518e1069...`, while the committed `sample-manifest.csv` hashes to `6e0e6171...` and has 10 rows against 20 manifest entries. | Reviewer | [ ] |
| 0.4 | Reconcile the detector commit. The findings file (generated 2026-07-06) does not record the commit that generated it. The profile repository's claim ledger names linter `57d0e94` as the frozen rule engine for this review ([ledger line 74 at profile commit `01bec48`](https://github.com/sebastianfoerste/sebastianfoerste/blob/01bec486b13abac8f77b92944225e6fbb3fffbff/docs/portfolio-claim-ledger.md#L74)). [Decide: keep this link to the removed ledger, or replace it with: `57d0e94` (v1.1.0) was earlier recorded as the frozen engine.] The same ledger's rows 7, 9 and 10 date `57d0e94` as linter main on 2026-09-19, after the findings run and after release v1.0.0 (2026-07-17, ledger line 16), so `57d0e94` is not the commit that generated the findings. The drafting clone was shallow (HEAD `db939d8`). A full clone on 2026-10-28 shows that `57d0e94` is tag v1.1.0 and that `8f37b7c` is the earliest public commit whose `STUDY_RULES` metadata equals the findings' `rules` list (section 2, detector decision). `8f37b7c` is dated a week after the findings, and no earlier public commit carries their rule IDs, so no public commit is known to have generated them; a re-run shows only whether a commit reproduces them. Re-run `micar-lint-batch` on the verified cache at the commit to be named and compare `results[]` with the committed file: document hashes, and per document the flagged rule IDs, confidence and evidence. The top-level digest cannot match on a re-run, because it covers `generated_at` (`_digest` in `batch.py`), and the committed file's `language_policy` and `human_review_note` texts differ from what the current code writes. | Reviewer | [ ] |
| 0.5 | Confirm whether any study rule was written or changed after viewing these documents. If yes, or if this cannot be ruled out, the results are described as **in-sample**. | Reviewer | [ ] |
| 0.6 | Record the reference standard in `review-protocol.md`: the rules' missing-element descriptions or the provisions as a whole (`REVIEWING.md` step 2). The codebook's cards and policies P3 and P4 follow that record. | Owner | [ ] |
| 0.7 | Decide the codebook policies P1 to P17 (`codebook.md`, section 6), including the rule-card judgments P11 to P17, and the LEI decision in `codebook.md` section 5, and complete against the Official Journal text the [OJ check] items that the table in `REVIEWING.md` step 3 does not close (`codebook.md` section 1). | Reviewer | [ ] |
| 0.8 | Confirm or reject the WP-007 exclusion rule and its stated ground (section 5), including whether it rests on eligibility criterion 4 or on the unit definition. | Reviewer | [ ] |
| 0.9 | Decide between single review by the tool author, disclosed, and a second reviewer (section 6). For a second reviewer: recruit and name them and record their study ID before the pre-registration commit, and fix in section 6 which cells they assess and, for a subset, the seed and fraction of `scripts/build_review_matrix.py --second-sheet`. The second sheet can be built only after the first review, because it includes the cells the first reviewer labelled `uncertain`, `extraction_failure` or `not_applicable`. | Reviewer | [ ] |
| 0.10 | Label the calibration document (section 4), outside the committed review sheets, and finalise the codebook. | Reviewer | [ ] |
| 0.11 | On `main`, make the one adoption commit of the signing order (banner): the adopted codebook, this plan with the Detector row filled in, and the pending sheets; tag it and record its SHA outside the signed files. | Reviewer | [ ] |

## 4. Calibration document

Calibration fixes the codebook's wording against a real document before the 150 cells are labelled. Its labels never enter any metric.

- **Default:** one document from WP-013 to WP-020, which are outside the v1 sample. Take the first of them, in the order below, whose bytes are cached, and record its file name and SHA-256 here: [file], [SHA-256]. The order is the ascending SHA-256 of `20261014|calibration|<study_doc_id>`: **WP-015, WP-017, WP-014, WP-016, WP-018, WP-020, WP-013, WP-019.** `source-manifest.json` describes all eight as hosted white-paper articles in HTML, so check that the cached bytes are a white paper before using one. `micar-study-verify-cache --include-candidates` lists which of them are cached.
- **Fallback, if none of WP-013 to WP-020 is cached:** calibrate on one in-sample document and **exclude it from every metric**. Choose it by the same rule over the in-sample documents other than WP-007: **WP-012, WP-004, WP-010, WP-001, WP-009, WP-003, WP-002, WP-011, WP-005** (take the first). Its 15 cells are labelled like any other, carry the note `calibration`, and are reported separately. Step 0.10 comes before the adoption commit, which holds only pending sheets (signing order, step 3), so these labels cannot be in `human-review-blinded.csv` at that commit. [Decide: where they are kept until the adoption commit, and how, and with which date, they enter the sheet after it.]
- **Document counts under the fallback.** With WP-007 excluded from the primary analysis (section 5), the primary analysis then has **8 documents (120 cells)**, and the sensitivity analysis that includes WP-007 has **9 documents (135 cells)**. The study plan's decision 13 says "report N = 9 documents"; that figure matches the WP-007-inclusive analysis only. [Reviewer confirms.]
- **Alternative for the reviewer to consider:** calibrate on WP-007, which is excluded from the primary analysis anyway. This keeps the primary analysis at 9 documents, but WP-007 is a poor calibration document (section 5) and would drop out of the sensitivity analysis. [ ] adopt / [ ] reject.

## 5. Eligibility and the WP-007 rule

**Rule.** WP-007 is excluded from the primary analysis under eligibility criterion 4, "Parseable XHTML, HTML, PDF, or text with acceptable extraction quality" (`methodology.md:43`).

**Ground.** The sampling notes suggest that the captured bytes may be a documentation landing page rather than the complete white paper:

- `sample-manifest.csv` gives WP-007's format as "HTML documentation page";
- `source-manifest.json` (retrieved 2026-07-03T07:15 UTC, before the batch run) notes for WP-007: "Docs page; may link PDF or require rendered-site extraction."

Whether the bytes contain the complete white paper is uncertain until the reviewer reads them.

**Recorded at batch processing** (`document-provenance.json`, processed 2026-07-03T07:30 UTC), and **not** a ground for the exclusion:

- WP-007's text extraction is recorded as `ok`, with no warnings and 27 labels found.
- WP-007 records 0 Inline XBRL tags, but so do 8 of the 10 documents (WP-003, WP-004, WP-005, WP-007 and the PDFs WP-009 to WP-012), so this does not set WP-007 apart.

The extraction record therefore shows no measured extraction defect. The exclusion rests on the doubt about what was captured, not on extraction quality as measured. **[Reviewer decision]:** whether criterion 4 covers this case, or whether the exclusion should instead rest on the unit definition in section 1 (the hashed bytes must be the complete white paper). The reviewer settles this at step 0.8, before the pre-registration commit; if neither ground is adopted, the exclusion is dropped and the full set becomes the primary analysis.

**Disclosure.** This rule is fixed after the detector output was produced and published. It is therefore reported as a post-hoc exclusion, and the sensitivity analysis that includes WP-007 (S1) is reported next to the primary result with equal prominence. The results report also states how many of the detector's flags fall in WP-007, taken from the findings file after labelling.

**Handling.** WP-007's 15 cells are labelled like any other, under `codebook.md` policy P8; no label is pre-filled. The capture problem is reported as a pipeline finding.

## 6. Reviewers and blinding

- **Default design: single review by the tool's author, disclosed.** `review-protocol.md` ("Second review and adjudication") requires the report to state that the labels are single-reviewed if no second reviewer is available. Every reported figure says so.
- **Partial blinding.** The reviewer wrote the detector and has had access to the published flag counts and examples in `findings-summary.md`. The review sheet (`human-review-blinded.csv`) hides detector outcomes; its rows follow the findings order, the same `STUDY_RULES` order for every document, which does not depend on the detector's result. Blinding is still partial and is disclosed as such.
- **Procedure.** The reviewer labels only `human-review-blinded.csv`, following `REVIEWING.md` and using `codebook.md`, `review-protocol.md` and the source documents. During labelling the reviewer does not open `human-review-matrix.csv`, `findings-pseudonymous.*`, `findings-summary.md` or playground output for these documents. The finished labels are committed on their own, before the merge with detector outcomes (`scripts/build_review_matrix.py --merge-blinded`, `REVIEWING.md` step 4), so that the commit order shows labels before merge.
- **Optional second reviewer.** A qualified lawyer. `review-protocol.md` ("Second review and adjudication") has a second reviewer assess every flagged cell, every `uncertain`, `extraction_failure` or `not_applicable` cell and at least 20% of randomly selected non-flagged cells; `REVIEWING.md` ("Time estimate") counts at least 47 such cells here. Once the first review is complete, `scripts/build_review_matrix.py --second-sheet` (`REVIEWING.md` step 3a) writes these cells to `human-review-second.csv`. Its random part takes the share `--fraction` of the non-flagged cells with the lowest SHA-256 of `<seed>|second-review|<study_doc_id>|<rule_id>`, so it depends on no label and can be repeated. `--second-all` selects all 150 cells for a full second review. The second reviewer labels only that sheet and does not open `human-review-blinded.csv`. [Decide: full second review or the protocol's subset. For the subset, fix the seed and the fraction here before the pre-registration commit and run the command with them. This draft proposes seed `20261014` and fraction 0.2, the command's defaults, which draw 26 of the 129 non-flagged cells.] No AI system acts as a reviewer or adjudicator, and no AI pass counts as human review.
- **Adjudication.** `review-protocol.md` has disagreements adjudicated by "a qualified reviewer", who records the final label and the reasoning. `scripts/build_review_matrix.py --disagreements` lists them in `human-review-adjudication.csv`, without detector columns, and the merge writes the adjudicated labels into the matrix with a note naming both reviews' labels. [Decide: who adjudicates. This draft recommends consensus with written reasons, or a third person, so that the first reviewer does not adjudicate alone. The command accepts these two and refuses one of the two reviewers alone.]

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

**Headline interval:** whichever of the Wilson interval and the document-cluster bootstrap interval has the greater width (upper bound minus lower bound), named in the text ("document-clustered" or "Wilson"). If more than [10]% of bootstrap replicates are dropped for a zero denominator, the Wilson interval is the headline and the bootstrap interval is reported as unstable.

## 10. Secondary and sensitivity analyses

- Per-rule and per-document counts of TP, FP, FN, TN and excluded labels. No per-rule precision or recall is headlined, because each rule has at most 10 cells.
- Per-document and per-offeror counts (including the per-offeror detail of S2) are computed for internal quality checks and are not published, or are published only without WP-IDs, unless the conflicts check and the legal review under `review-protocol.md` ("Publication gate", item 6) are complete and the reviewer decides otherwise (section 11).
- **S1:** the full set, including WP-007.
- **S2:** one document per offeror. WP-003, WP-004 and WP-005 share one offeror, and WP-011 and WP-012 share one (`source-manifest.json`, `offeror_or_issuer`). Report (a) an offeror-cluster bootstrap with the settings of section 9 and (b) the deterministic variant that keeps the lowest-numbered document per offeror.
- **S3 and S4:** `uncertain` counted as `missing`, then as `present`, to bound the result.
- **S5:** the labels under the other reference standard that reviewers record in `review_note` (`REVIEWING.md` line 82; for example the business addresses under Part A item 8, or the Art. 6(6) statement that the white paper makes no omission likely to affect its import), and the stricter readings recorded in notes under `codebook.md` P4, where the notes allow it.
- **Inter-rater agreement, if double-reviewed:** raw agreement; Cohen's kappa on present/missing and on all labels; PABAK or Gwet's AC1. State which cells were double-reviewed: under the protocol's subset (section 6) they include every flagged cell and every cell the first reviewer labelled `uncertain`, `extraction_failure` or `not_applicable`, so agreement on them does not describe the 150 cells.
- Results are computed by tooling from the committed label files and copied from its JSON output; no figure is computed by hand. On `main`, `micar-review-summary` computes the confusion matrix, precision, recall and F1 (`human-review-summary.json`), but not the intervals of section 9 or the analyses of this section.

## 11. Reporting rules

- **Aggregate only.** Publish aggregate metrics. Do not publish per-cell, issuer-identifiable labels (study plan, decision 15). WP identifiers are pseudonymous, not anonymous: `source-manifest.json` maps them to named entities and URLs.
- **Labels file and the public repository.** This repository is public, so pushing a completed `human-review-blinded.csv` or `human-review-second.csv`, the adjudication file `human-review-adjudication.csv`, or `human-review-matrix.csv` after the merge, publishes per-cell labels. [Decide: (a) commit the labels locally and publish only their SHA-256 as a timestamped commitment until the checks below are done; or (b) push the labels after those checks.]
- **Before any statement about a named issuer or offeror:** a conflicts check covering both the persons who drew up the papers and the token issuers named in them, and the separate qualified legal review that `review-protocol.md` ("Publication gate", item 6) requires.
- **Never** describe the result as "accuracy", "validated", a detection rate for MiCAR violations, a compliance rate or a prevalence estimate. This section governs public wording: the closing sentence of `review-protocol.md` ("Publication gate": "supports reporting detector validation") and the study README heading "Validate against human labels" describe the procedure, not a result.
- **Disclosures with every figure:** reviewer = tool author; partial blinding; single-reviewed (unless a second reviewer took part); in-sample (unless step 0.5 rules it out); convenience sample of 10 documents.

- **Name the measured component.** Every figure is about the linter's batch study detector (15 Annex I and Article 6 checks, commit [SHA]), not the rule engine that the CLI and the GitHub Action run. Under detector decision (A), the wording says "pilot detector as of July 2026". Never "validated".

**Wording templates** (from the study plan, section 3.4; fill only from the computed JSON):

- Study summary: "Batch study detector (15 Annex I and Article 6 checks, commit [SHA]): precision X% (95% CI a to b, document-clustered) and recall Y% (c to d) on N evaluable of 150 document-rule cells (10 public white papers from ESMA's interim register × 15 rules; WP-007 excluded from the primary analysis under a rule fixed before labelling but after the detector output (post-hoc; see S1); M excluded as uncertain, not applicable or extraction failure), against [the tool author's partially blinded labels, single-reviewed | two lawyers' labels, Cohen's κ = k, adjudicated]. [In-sample] pilot on a convenience sample; not a prevalence or compliance finding."
  - The study plan's wording says "excluded ... as pre-registered". This draft replaces it, because section 5 discloses the exclusion as post-hoc and "as pre-registered" alone suggests the rule came before the detector output. [ ] adopt.
  - Drafting note: the primary set has 135 cells (120 under the calibration fallback), not 150. Recommended: "on N evaluable of the 135 primary-analysis cells (150 cells from 10 public white papers × 15 rules, less WP-007's 15 cells, excluded post-hoc; M excluded as ...)". [ ] adopt.
  - "from ESMA's interim register" holds only after step 0.2.
  - If TP + FN is below 10, state recall as "X of Y reviewer-identified gaps".
- Profile README line: "[In-sample] pilot of my MiCAR linter's batch study detector (15 Annex I and Article 6 checks, commit [SHA]) on 10 public ESMA-register white papers: precision X%, recall Y% against my own partially blinded, single-reviewed labels ([study](https://github.com/sebastianfoerste/micar-whitepaper-linter/tree/main/studies/2026-07-title-ii-annex-i-whitepaper-study))." With a second reviewer, replace the label description with "my own and a second lawyer's labels (κ = k)".
  - Drop "[In-sample]" only if step 0.5 rules it out.
  - "ESMA-register" holds only after step 0.2.
  - The headline figures come from 9 documents (8 under the calibration fallback), not 10. Option: "... 10 public ESMA-register white papers (one excluded, see study): ...". It adds two words to the profile README's word budget. [ ] adopt / [ ] reject.
- CV or application sentence: "I measured the batch study detector of my MiCAR white-paper linter (15 Annex I and Article 6 checks, commit [SHA]) against my own partially blinded, single-reviewed legal review of 10 public white papers from ESMA's register: [in-sample] precision X% (95% CI a to b), recall Y% (c to d) on N of 150 document-rule cells[; second-reviewer agreement κ = k]." Never "validated".
  - Drop "[in-sample]" only if step 0.5 rules it out.
  - The same 150-versus-135 note applies, and the same "(one excluded, see study)" option for the 10 papers.
  - "from ESMA's register" holds only after step 0.2.
  - "legal review" can be read as a review of legal sufficiency, while the labels record presence only (`codebook.md`, P3). Option: "presence review" in its place. [ ] adopt / [ ] reject.

## 12. Deviations

Any change after the pre-registration commit is logged here with date, change, reason and whether any label had been seen, and is reported with the results.

| Date | Deviation | Reason | Labels seen? |
| --- | --- | --- | --- |
| | | | |
