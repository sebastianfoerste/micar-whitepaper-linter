# Reviewer checklist

This file sets out the order of work for labelling the 150 document-rule cells and producing precision and recall. `review-protocol.md` governs; where the two differ, follow the protocol. Run every command from the repository root after `uv sync --extra dev`.

The checklist covers the first review and a single-reviewed result. The protocol's default goes further: a second qualified reviewer independently assesses every flagged cell, every `uncertain`, `extraction_failure` or `not_applicable` cell and at least 20% of randomly selected non-flagged cells, and disagreements are adjudicated ("Second review and adjudication"). Single review is the fallback the protocol allows: "If no second reviewer is available, the report must state that the labels are single-reviewed."

## 0. Before you start

- Do not open `human-review-matrix.csv`, `findings-pseudonymous.json`, `findings-pseudonymous.csv` or `findings-summary.md` until the merge in step 4. They show the detector status of each cell. `findings-summary.md` names five flagged cells in "Examples pending human review". Note which of these files you have already seen, because the report should say so (step 6).
- Edit `human-review-blinded.csv` in a text editor, or save it from a spreadsheet as comma-separated UTF-8. Spreadsheets set to a German locale may save with semicolons or rewrite `2026-10-14` as `14.10.2026`. The merge refuses both.
- During the review, do not run `scripts/fetch_esma_register.py`, `scripts/select_sample.py` or `scripts/run_batch.py`, or the first two commands under "Reproduce the detector output" in this folder's `README.md`. `fetch_esma_register.py`, `select_sample.py` and the `micar_linter.esma_register` command rewrite `source-manifest.json`, and the two scripts also rewrite `sample-manifest.csv`; these files hold the frozen pilot sample. The rewritten `source-manifest.json` also lacks fields the committed file holds, among them `human_review_status` and the per-entry document hashes. `run_batch.py` and the `micar-lint-batch` command rewrite `findings-pseudonymous.json`, from which the review sheets are built, and `findings-pseudonymous.csv`.

## 1. Get the documents and check their bytes

No script in the repository downloads the white papers. If the `.study-cache/title-ii-whitepapers/` folder that the detector processed still exists, use it; the check below shows whether its files still match. If it does not exist, download the ten included documents (WP-001 to WP-005, WP-007 and WP-009 to WP-012) from `whitepaper_url` in `source-manifest.json`. Save each one under `.study-cache/title-ii-whitepapers/` with the `preferred_filename` given in the same entry.

Then check the bytes against `document-provenance.json`:

```bash
uv run python - <<'PY' > .study-cache/expected-sha256.txt
import json
from pathlib import Path

study = Path("studies/2026-07-title-ii-annex-i-whitepaper-study")
entries = json.loads((study / "source-manifest.json").read_text(encoding="utf-8"))["entries"]
names = {entry["study_doc_id"]: entry["preferred_filename"] for entry in entries}
for doc in json.loads((study / "document-provenance.json").read_text(encoding="utf-8"))["documents"]:
    print(f"{doc['document_sha256']}  {names[doc['study_doc_id']]}")
PY
(cd .study-cache/title-ii-whitepapers && shasum -a 256 -c ../expected-sha256.txt)
```

Every line must end in `OK`. A `FAILED` document holds different bytes from the ones the detector processed, so labelling it would not validate the detector's output for that document. The protocol does not cover this case. Either recover the original bytes, or rerun the detector on the new bytes and rebuild the sheets, which makes it a new run with a new findings digest. WP-011 and WP-012 have web-page URLs (`format_hint` "PDF-rendered URL") but were processed as PDFs, so a fresh download may not give the same bytes. That affects 30 of the 150 cells.

## 2. Reference standard: an owner decision before any labelling

The protocol gives reviewers both "the applicable Article 6 or Annex I requirement" and "the rule label and missing-element description" ("Materials"), and tells them to "Apply the rule to the source" ("First review", step 3). This checklist reads the protocol as leaving open which of the two decides a label where they differ: "Apply the rule" can be read as choosing the rule's missing element, but the requirement is also among the materials. For 12 of the 15 rules they do differ: the provision asks for more than the rule's missing element, or for something else (last column of the table in step 3).

A synthetic example shows the effect. A white paper states that the crypto-asset may lose its value and is covered by neither investor compensation nor deposit guarantee schemes, but says nothing about transferability or liquidity. Measured against the missing element of `ARTICLE_6_05_MANDATORY_WARNINGS`, the cell is `present`. Measured against Article 6(5), it is `missing`; if the detector did not flag it, the cell then counts as a false negative, although the detector was never specified to look for those two statements.

Before anyone labels a cell, the owner chooses one reference standard and records it in `review-protocol.md`:

- the rule's missing-element description: the metrics then measure the detector against what it was specified to find;
- the provision as a whole: the metrics then measure the detector against the legal requirement, and a rule that asks for less than its provision will show false negatives by design.

Do not start labelling until the choice is recorded. The report states which standard the metrics use (step 6).

## 3. First review (blinded)

Work through `human-review-blinded.csv` under "First review" in the protocol. Each row needs:

| Column | Content |
| --- | --- |
| `human_label` | `present`, `missing`, `uncertain`, `extraction_failure` or `not_applicable` |
| `reviewer_id` | your reviewer identifier |
| `reviewed_at` | review date as `YYYY-MM-DD`, not before the detector run on 2026-07-06 and not after the day you enter it. The protocol asks for an "ISO 8601 review date" ("First review", step 6); the scripts accept only this calendar form. |
| `source_pinpoint` | for `present` or `missing`: page, section, Inline XBRL fact or another stable pinpoint ("First review", step 5). For `missing`, the section where the element would be expected, or the sections you searched. |
| `review_note` | required for `uncertain`, `extraction_failure` and `not_applicable` ("First review", step 7). |

The protocol treats pinpoints in three ways. First review step 5 asks for a pinpoint for both `present` and `missing`. Publication gate item 2 accepts "a source pinpoint or explanation" for both, and `methodology.md` "a source pinpoint or explanatory note". The definition of `present` includes "a recorded pinpoint". The merge and the summary refuse a `present` cell without a pinpoint and a `missing` cell with neither a pinpoint nor a note. They therefore accept a `missing` cell with only a note, which step 5 does not. Record a pinpoint wherever you can.

Apply the reference standard recorded under step 2, not the detector's pattern. The legal text is Regulation (EU) 2023/1114 (MiCAR), ELI http://data.europa.eu/eli/reg/2023/1114/oj. The protocol gives reviewers the rule label and missing-element description. They are copied below from the `rules` list in `findings-pseudonymous.json`, because that file also shows the detector results. That list gives only "Article 6" for the last three rules; the Item column adds the paragraph. The last column compares each missing element with the text of the provision and is not part of the rules list. It was checked against the Official Journal text at the ELI above, not against a consolidated version; before labelling, check on EUR-Lex whether a later amendment changes Article 6 or Annex I.

| Rule ID | Item | Label | Missing element | How the provision differs from the missing element |
| --- | --- | --- | --- | --- |
| `ANNEX_I_PART_A_02_LEGAL_FORM` | Annex I, Part A, item 2 | Legal form | legal form of the offeror or person seeking admission to trading | No difference |
| `ANNEX_I_PART_A_03_REGISTERED_ADDRESS` | Annex I, Part A, item 3 | Registered address or head office | registered address or head office | "Registered address and head office, where different": both, where they differ |
| `ANNEX_I_PART_A_04_REGISTRATION_DATE` | Annex I, Part A, item 4 | Registration date | date of registration, incorporation, or establishment | The item names only the "Date of the registration"; the rule also accepts a date of incorporation or establishment |
| `ANNEX_I_PART_A_05_LEI_OR_IDENTIFIER` | Annex I, Part A, item 5 | LEI or other identifier | legal entity identifier or other identifier | The other identifier must be one "required pursuant to applicable national law" |
| `ANNEX_I_PART_A_06_CONTACT_PHONE_EMAIL` | Annex I, Part A, item 6 | Contact telephone number and email | both contact telephone number and email address | No difference |
| `ANNEX_I_PART_A_06_CONTACT_RESPONSE_PERIOD` | Annex I, Part A, item 6 | Response period for investor contact | period of days within which an investor will receive an answer | No difference |
| `ANNEX_I_PART_A_08_MANAGEMENT_BODY` | Annex I, Part A, item 8 | Management body identity and functions | identity and functions of the management body | Also the "business addresses" of the members of the management body |
| `ANNEX_I_PART_E_18_CONFLICTS_OF_INTEREST` | Annex I, Part E, item 18 | Conflicts of interest | conflicts of interest disclosure | Names whose conflicts: "Potential conflicts of interest of the persons involved in the offer to the public or admission to trading, arising in relation to the offer or admission to trading" |
| `ANNEX_I_PART_A_10_FINANCIAL_CONDITION` | Annex I, Part A, item 10 | Financial condition | financial condition disclosure | The financial condition over the past three years, or since the date of registration where the offeror or person has not been established for the past three years. It is assessed on a fair review of the development and performance of the business and of its position "for each year and interim period for which historical financial information is required, including the causes of material changes". The review is "a balanced and comprehensive analysis", consistent with the size and complexity of the business |
| `ANNEX_I_PART_D_01_ASSET_NAME_ABBREVIATION` | Annex I, Part D, item 1 | Crypto-asset name and abbreviation | crypto-asset name and abbreviation | Also the name of the crypto-asset project. The item adds "if different from the name of the offeror or person seeking admission to trading" and reads "abbreviation or ticker handler" |
| `ANNEX_I_PART_D_03_IMPLEMENTATION_PERSONS` | Annex I, Part D, item 3 | Persons involved in crypto-asset project implementation | natural or legal persons involved in implementation of the crypto-asset project | "Details of all" such persons, "including business addresses or domicile of the company", such as advisors, development team and crypto-asset service providers |
| `ANNEX_I_PART_F_02_CHARACTERISTICS_FUNCTIONALITY` | Annex I, Part F, item 2 | Characteristics and functionality | characteristics or functionality of the crypto-asset | Characteristics and functionality, including the data necessary for classifying the white paper in the register under Article 109 and when the functionalities are planned to apply |
| `ARTICLE_6_05_MANDATORY_WARNINGS` | Article 6(5) | Mandatory warning statements | loss-of-value and protection or compensation warning statements | One clear and unambiguous statement covering six points: the crypto-asset may lose its value in part or in full, may not always be transferable and may not be liquid; where the offer concerns a utility token, it may not be exchangeable against the promised good or service; and it is covered by neither investor compensation schemes (Directive 97/9/EC) nor deposit guarantee schemes (Directive 2014/49/EU) |
| `ARTICLE_6_06_MANAGEMENT_BODY_STATEMENT` | Article 6(6) | Management body statement | management body statement that the white paper complies and is fair, clear and not misleading | Compliance "with this Title"; also that the white paper "makes no omission likely to affect its import"; the statement follows the Article 6(3) statement |
| `ARTICLE_6_07_SUMMARY` | Article 6(7) | Summary | summary of the crypto-asset white paper | Placed after the Article 6(6) statement, in "brief and non-technical language", with a warning covering points (a) to (d) of the second subparagraph |

For a rule with a difference, label against the standard recorded under step 2. Where the other standard would give a different label, say so in `review_note`, for example "against Art. 6(5) as a whole: missing, no liquidity statement found".

## 4. Merge the labels into the matrix

```bash
uv run python studies/2026-07-title-ii-annex-i-whitepaper-study/scripts/build_review_matrix.py --merge-blinded
```

The merge copies the reviewer columns into `human-review-matrix.csv`. It stops, and writes nothing, while any blinded cell is pending, has an unsupported label, lacks a field that publication gate item 2 or "First review" steps 6 and 7 require, has a date that is not `YYYY-MM-DD` or lies after today or before the detector run on 2026-07-06, appears in more than one filled row, or differs from a value the matrix already holds. Fix what it lists in the blinded sheet and run it again. Plain `python3` cannot import `micar_linter`; the merge then stops and gives the `uv run` command.

After the merge the matrix shows the detector status, so a label changed after that point is no longer blind. Make any such correction in `human-review-matrix.csv`, not in the blinded sheet, and record it in the cell's `review_note` and in the report. A further merge refuses every cell where the blinded sheet and the matrix differ. Such a correction is checked only by the summary in step 5, which checks the earliest permitted date only when given `--findings`.

## 5. Metrics

```bash
uv run micar-review-summary \
  --matrix studies/2026-07-title-ii-annex-i-whitepaper-study/human-review-matrix.csv \
  --out studies/2026-07-title-ii-annex-i-whitepaper-study/human-review-summary.json \
  --findings studies/2026-07-title-ii-annex-i-whitepaper-study/findings-pseudonymous.json \
  --require-complete
```

Exit status 0 means no row is pending and every labelled row has the fields that publication gate item 2 and "First review" steps 6 and 7 require, with a review date in the form `YYYY-MM-DD` that is no later than today. A `missing` cell with a note but no pinpoint passes (step 3). `--findings` adds two checks: the matrix must hold exactly the 150 cells of `findings-pseudonymous.json` with their detector status, or the command exits 1 and writes nothing; and no review date may precede the detector run (the date of `generated_at`, 2026-07-06). The command in `review-protocol.md` has no `--findings`, so it makes neither check. Exit status 0 covers publication gate items 1, 2 and 4. No script checks item 3 (adjudication), item 5 (limitations in the report), item 6 (legal review of statements about a named issuer) or the ESMA reconciliation that `methodology.md` requires. Exit status 0 is therefore necessary for publication, not sufficient. Exit status 2 prints what is missing. `human-review-summary.json` then holds:

- the confusion matrix (`tp` flagged and missing, `fp` flagged and present, `fn` not flagged and missing, `tn` not flagged and present);
- precision `tp / (tp + fp)`, recall `tp / (tp + fn)` and F1 `2tp / (2tp + fp + fn)`. The protocol does not define F1; `metric_note` records the formula;
- the counts of `uncertain`, `extraction_failure` and `not_applicable`, which are excluded from the metrics;
- `reviewers_recorded`, the number of distinct reviewer identifiers across labelled cells (not the number of reviews per cell), and `review_disclosure`;
- `publication_ready_scope`, which states what `publication_ready` does not check.

The committed `human-review-summary.json` is still schema v1 and lacks the last two items and the protocol-gap fields; the command above regenerates it. The precision denominator is at most 21, the number of flagged cells. The recall denominator is the number of cells labelled `missing` and is unknown until the review is complete. The protocol specifies no confidence interval. If you want one, add the method to the protocol before computing the metrics.

## 6. Report

`micar-study-report` renders `findings-summary.md` from `findings-pseudonymous.json` alone. It does not read `human-review-summary.json`, and its "Human validation gate" paragraph is fixed text. The heading "Examples pending human review" stays unless `human_review_status` in `findings-pseudonymous.json` reads `reviewed`; the next render then heads the same examples "Examples with pinpoint references". Those pinpoints are the detector's, and each example still shows its own `human_review_status` from the findings file, not the reviewer's label. The metrics paragraph therefore has to be written by hand. If you add it to `findings-summary.md`, the next render overwrites it.

These files state the pending status and will be out of date once the review is done: this folder's `README.md` ("Current status" and "As of this commit no cell has been reviewed."), `limitations.md` ("All 150 document-rule cells remain pending"), `findings-summary.md`, the `0.2.2` entry in `CHANGELOG.md` ("None of the 150 cells has been reviewed.") and `docs/playground/index.html` (`basis-reviewed` is 0). `make check` fails on "the evidence note states the committed study figures" until `basis-reviewed` equals `rows_completed`. The `human_review_status` field in `findings-pseudonymous.json` and `findings-pseudonymous.csv` comes from the batch runner and stays `pending_review`. The same field in `document-provenance.json` and `source-manifest.json` is not written by any script in the repository, so it stays `pending_review` unless someone edits it by hand. The owner decides whether to update these fields after the review and records any such edit.

The protocol requires a single-reviewed result to state:

- that the labels are single-reviewed ("Second review and adjudication": "If no second reviewer is available, the report must state that the labels are single-reviewed.");
- the sampling and extraction limitations (publication gate item 5): the sample is a ten-document convenience sample with repeated issuers and supports no prevalence estimate or statement about the ESMA register, and extraction can hide a disclosure that is present (`methodology.md`, `limitations.md`).

This checklist also recommends stating the following. The protocol does not require any of it:

- which reference standard the labels and metrics use (step 2);
- the confusion-matrix counts alongside precision and recall, how many of the 150 cells entered the metrics, and how many were excluded under each label;
- whether the reviewer had seen detector output before labelling, and whether the reviewer wrote or tuned the detector, because both bear on the blinded design;
- whether the included entries have been reconciled against ESMA's official Title II CSV. `methodology.md` requires that reconciliation before any reviewed publication; stating it in the report is this checklist's suggestion.

Make no statement about a named issuer without a separate qualified legal review (publication gate item 6). WP identifiers are pseudonymous, not anonymous.

A template, with the values to be filled in from `human-review-summary.json` and the review record:

> One reviewer labelled all 150 document-rule cells against `<the rules' missing-element descriptions | the provisions as a whole>`. The labels are single-reviewed, with no second review or adjudication. Before labelling, the reviewer `<had not seen any detector output | had seen <files>>` and `<had no part in | wrote or tuned>` the detector. Of the 150 cells, `<evaluable_rows>` were labelled present or missing and entered the metrics; `<n>` uncertain, `<n>` extraction-failure and `<n>` not-applicable cells were excluded. Precision was `<precision>` (`<tp>` of the `<tp + fp>` flagged cells labelled present or missing) and recall was `<recall>` (`<tp>` of `<tp + fn>` cells labelled missing). The figures describe this ten-document convenience sample, which includes repeated issuers, and support no prevalence estimate or statement about the ESMA register. Text extraction can hide a disclosure that is present in the source. The included entries were reconciled against ESMA's official Title II CSV on `<date>`.

## Time estimate

This is an estimate, not a measurement. It assumes ten documents (six HTML or XHTML files and four PDFs of 35 to 41 pages, per `document-provenance.json`) with 15 cells each.

| Step | Estimate |
| --- | --- |
| Get the documents and check their bytes | about 10 minutes with the original cache; 30 to 60 minutes to download, and WP-011 and WP-012 may not match |
| First review of 150 cells | 5 to 10 hours, at 2 to 4 minutes per cell. The six Part A contact and identity fields are quick where a document follows the numbered template. Management body, conflicts, financial condition, persons, characteristics, the warnings, the management body statement and the summary need reading. |
| Merge and metrics | about 10 minutes, plus fixing any cells the merge lists |
| Report and status updates | 1 to 2 hours |

The total comes to about 6 to 13 hours, so a single review takes one to two working days. The owner's choice of reference standard (step 2) comes before this and is not included. A second review under the protocol covers at least 47 cells: all 21 flagged cells, at least 26 of the 129 non-flagged cells (20%), and every `uncertain`, `extraction_failure` or `not_applicable` cell not already among them. At the same rate, 47 cells take the second reviewer about 1.5 to 3 hours, plus adjudication time. The repository has no second blinded sheet, no random-selection script and no adjudication record for that step.
