# Codebook: human review of the 150 document-rule cells

> **DRAFT, not adopted; it reaches `main` as unsigned draft tooling and is adopted there in a separate commit.**
>
> Drafted with AI assistance (Claude) on 2026-10-14 for the reviewer's decision. No lawyer has reviewed this draft. Until the reviewer adopts it, it states options and recommended defaults, not rules.
>
> **Signing order.**
>
> 1. Merge pull requests #18, #19 and #24 into `main` as unsigned DRAFT tooling. Merging them adopts nothing.
> 2. On `main`, complete Phase 0 (steps 0.1 to 0.10, `analysis-plan.md` section 3).
> 3. Make ONE adoption commit on `main`. It contains the adopted `codebook.md`, `analysis-plan.md` with the Detector row of its section 2 filled in, and the pending review sheets, with the DRAFT line of each banner removed and the "Adopted by" line filled in. This commit is the pre-registration and precedes the commit that adds any label.
> 4. Mark the adoption commit with an annotated tag.
> 5. Record the adoption commit's SHA in a follow-up commit or in the study README, never inside the signed files.
>
> The adoption commit is made on `main` after everything the study needs from `main` has been merged, so that no later merge changes the files that `analysis-plan.md` section 2 freezes between the pre-registration commit and the results.
>
> - Adopted by: [reviewer name], on [YYYY-MM-DD]
> - Pre-registration commit: not recorded in this file (signing order, step 5)
> - Policy decisions recorded in section 6: [ ] all decided

## 1. Status of the legal text

The requirement descriptions below follow MiCAR (Regulation (EU) 2023/1114) Article 6 and Annex I **as encoded in this repository**:

- the rule IDs, Annex labels and element descriptions in `STUDY_RULES` (`src/micar_linter/batch.py` at the detector commit recorded in `analysis-plan.md` section 2);
- the Article 6 citations in `src/micar_linter/rules/common.py`;
- the Article 6(3), 6(5), 6(6) and 6(7) statement fields of the synthetic template example `examples/numbered-other-draft.xhtml`.

They were **not checked against the Official Journal text** while drafting, because EUR-Lex and ESMA could not be reached. Two markers flag what the reviewer must settle before adoption:

- **[OJ check]**: the draft gives a reading of the legal text that is not encoded in the repository. Verify it against the Official Journal text of Regulation (EU) 2023/1114 and correct the codebook (and, if needed, `REVIEW_REQUIREMENTS` in `src/micar_linter/review_sheets.py`, then regenerate the sheets).
- **[Legal judgment]**: the cell cannot be labelled consistently without a policy choice. Section 6 lists the options and a recommended default.

The `requirement` column of the review sheets repeats the element description for each rule. This codebook governs where the two differ.

## 2. What the reviewer decides

One cell is one question: **do the exact source bytes with the recorded SHA-256 contain the disclosure element that the rule names?**

- The unit is the cached document whose hash matches `document-provenance.json`. Run `micar-study-verify-cache` first; do not label a document whose bytes do not verify.
- The question is **presence** of a responsive disclosure, not its legal sufficiency or accuracy (policy P3).
- The reviewer reads the source document itself (rendered XHTML or HTML, or the PDF), not the text the detector extracted.
- The reviewer answers without seeing the detector's result. During labelling, work only in your own sheet (`human-review-r1.csv`) with this codebook, `review-protocol.md` and the source document. Do not open `human-review-matrix.csv`, `findings-pseudonymous.json`, `findings-pseudonymous.csv`, `findings-summary.md` or any playground output for these documents.
- This codebook contains no detector patterns and no detector outcomes. The reviewer wrote the detector, so blinding is partial; the analysis plan discloses this.

## 3. Labels

Use exactly one label per cell. The definitions refine `review-protocol.md` (Labels table) and do not replace it.

| Label | Use when | Required fields |
| --- | --- | --- |
| `present` | The source bytes contain a disclosure that responds to the element, for the person the rule names. | `source_pinpoint`; `review_note` when a policy from section 6 decided the label. |
| `missing` | The reviewer inspected the parts of the source where the element belongs, and searched the whole document, and did not find it. Also used when only part of a multi-part element is given (the note names the missing part). | `source_pinpoint` stating where the element was expected and what was searched; `review_note` for partial disclosures. |
| `not_applicable` | The reviewer concludes that the rule does not apply to this document at all. Rare; a sub-statement that does not apply (such as Art. 6(5)(d) outside utility tokens) does not make the whole cell `not_applicable`. | `review_note` with the reason. |
| `uncertain` | The legal requirement or the source wording is genuinely ambiguous, so that two reasonable readings lead to different labels. Not a substitute for finishing the search. | `review_note` stating both readings. |
| `extraction_failure` | The bytes cannot support a reliable decision for this element: the file does not render, pages or sections are unreadable, or the capture is evidently not the complete white paper and the element is not in the capture (policy P8). | `review_note` describing the defect. |
| `pending` | Not yet reviewed. A blank label counts as pending. | None. |

Only `present` and `missing` enter precision and recall. The other labels are counted and reported.

**Order of decisions for each cell:**

1. Hash verified for this document? If not, stop and leave the document pending.
2. Can the relevant part of the source be read? If not, `extraction_failure`.
3. Does the rule apply to this document? If the reviewer concludes it does not, `not_applicable` with reasons.
4. Is the element there for the right person? `present` or `missing`.
5. Only if step 4 has two defensible answers: `uncertain`, with both readings.

**Field conventions:**

- `reviewer_id`: the reviewer's study ID, for example `r1`.
- `reviewed_at`: ISO 8601 date, `YYYY-MM-DD`.
- `source_pinpoint`:
  - XHTML or HTML in the template layout of Implementing Regulation (EU) 2024/2984: the field as printed, with its heading, for example `Part A, field A.2 "Legal form"`. Template field numbers (A.1, A.2, ...) are not Annex I item numbers, and authors number fields differently (`src/micar_linter/numbered_fields.py:4-6`). Cite the field as printed.
  - Inline XBRL: the concept name of the fact, if used.
  - PDF: `p. N` using the page index the PDF viewer shows (first page = 1), plus the section heading.
  - For `missing`: the part and fields inspected and the search terms used, for example `Part A fields A.1 to A.12; searched "phone", "tel", "+"`.
- `review_note`: free text. Cite the policy number when a policy decided the label (for example `P1`).

## 4. Which person the Part A items refer to

The Part A items concern **the offeror or the person seeking admission to trading**. Some white papers are drawn up by the operator of a trading platform, whose details then appear in Part C (`src/micar_linter/rules/annex_i.py`, rules ANNEX_I.A to ANNEX_I.C). Whether the operator's details answer the Part A items is policy P2 **[Legal judgment]**. Information about a different issuer (Part B) does not answer a Part A item.

## 5. Rule cards

Each card gives the element, what counts as `present` and `missing`, and the policies that may decide the cell. The order follows `STUDY_RULES`; the review sheet shuffles it.

### 5.1 `ANNEX_I_PART_A_02_LEGAL_FORM`: Legal form (Annex I, Part A, item 2)

- **Element:** the legal form of the offeror or person seeking admission to trading.
- **present:** a legal form is stated for that person, for example a company type under a named national law. A legal-form designation that is part of the registered name (such as "GmbH" or "S.A.") counts if policy P10 is adopted.
- **missing:** no legal form for that person; the field is empty or reads "N/A" (P1).
- **Policies:** P1, P2, P10.

### 5.2 `ANNEX_I_PART_A_03_REGISTERED_ADDRESS`: Registered address or head office (Annex I, Part A, item 3)

- **Element:** the registered address (registered office or seat) of that person.
- **present:** an address that identifies the registered office: street and number (or equivalent), postcode, city and country.
- **missing:** no address. A city or country alone: P11.
- **[OJ check]:** the drafting reading is that item 3 asks for the registered address and, where different, the head office. Recommended: label on the registered address; if the document indicates a different head office without giving it, say so in the note.
- **Policies:** P1, P2, P11.

> **Documents that give a valid LEI (5.1 and 5.2).** Open draft pull request #51 reads recital 2 of Implementing Regulation (EU) 2024/2984 as allowing a white paper that gives a valid LEI to omit the legal form, registered address, head office and parent company, because they can be retrieved from the LEI. This codebook has no policy for that case. The legal merits of that reading are unverified here: EUR-Lex could not be reached while drafting.
>
> [Decide: present, missing or not_applicable when a valid LEI is given; align with the CLI if #51 is adopted.]

### 5.3 `ANNEX_I_PART_A_04_REGISTRATION_DATE`: Registration date (Annex I, Part A, item 4)

- **Element:** the date of registration (incorporation or establishment) of that person.
- **present:** a stated date of registration or incorporation. A year alone: P12.
- **missing:** no date; a date that refers to something else (the white paper, the token launch, a licence) does not count.
- **Policies:** P1, P2, P7, P12.

### 5.4 `ANNEX_I_PART_A_05_LEI_OR_IDENTIFIER`: LEI or other identifier (Annex I, Part A, item 5)

- **Element:** the legal entity identifier (LEI) of that person, or another identifier of that person.
- **present:** a 20-character LEI (ISO 17442) attributed to that person, or another identifier of the legal person such as a company-register number.
- **missing:** no identifier of the person. An identifier of the **token** (DTI, ISIN, contract address) does not count (P5).
- **[OJ check]:** the drafting reading is "legal entity identifier or another identifier required pursuant to applicable national law". If so, P13 decides whether any company-register number qualifies or only one required by national law.
- **Policies:** P1, P2, P5, P13.

### 5.5 `ANNEX_I_PART_A_06_CONTACT_PHONE_EMAIL`: Contact telephone number and email (Annex I, Part A, item 6)

- **Element:** both a contact telephone number and an email address of that person.
- **present:** a telephone number **and** an email address, both usable for contacting that person.
- **missing:** either one is absent (the note names which), or the field reads "N/A". A web contact form is not an email address.
- **Policies:** P1, P2.

### 5.6 `ANNEX_I_PART_A_06_CONTACT_RESPONSE_PERIOD`: Response period for investor contact (Annex I, Part A, item 6)

- **Element:** the period of days within which an investor contacting that person will receive an answer.
- **present:** a period expressed in days (calendar or business days, for example "within 10 business days").
- **missing:** no period, or a period not in days that cannot be converted. Vague wording such as "promptly" or "as soon as possible": P14.
- **Policies:** P1, P2, P14.

### 5.7 `ANNEX_I_PART_A_08_MANAGEMENT_BODY`: Management body identity and functions (Annex I, Part A, item 8)

- **Element:** the identity and functions of the members of the management body of that person.
- **present:** the members are named and each member's function is stated.
- **missing:** no members named; or names without functions, or functions without names (partial: `missing` with a note).
- **[OJ check]:** the drafting reading is that item 8 also asks for the members' business address. Recommended: business address is not required for `present`; record its absence in the note so that a stricter reading can be applied in a sensitivity analysis.
- **Policies:** P1, P2.

### 5.8 `ANNEX_I_PART_E_18_CONFLICTS_OF_INTEREST`: Conflicts of interest (Annex I, Part E, item 18)

- **Element:** disclosure of conflicts of interest relating to the offer to the public or the admission to trading.
- **present:** the document addresses potential conflicts of interest of the persons involved in the offer or admission: it describes them, or explains how they are managed. An explicit statement that no conflicts have been identified: P15.
- **missing:** the document does not address conflicts of interest for this offer or admission.
- **Generic reference only:** a reference to a conflicts policy that is not tied to this offer or admission: P15.
- **[OJ check]:** the Part letter and item number come from `STUDY_RULES` (Part E, item 18); the earlier review sheets wrongly said Part A. Confirm the item number and wording.
- **Policies:** P1, P3, P15.

### 5.9 `ANNEX_I_PART_A_10_FINANCIAL_CONDITION`: Financial condition (Annex I, Part A, item 10)

- **Element:** the financial condition of that person.
- **present:** the document describes that person's financial condition in its own text: figures from financial statements, or a narrative on financial position, results or solvency.
- **missing:** nothing on financial condition, or a bare "N/A" (P1). Only a reference to accounts published elsewhere: P16.
- **[OJ check]:** the drafting reading is "over the past three years or, where the person has not been established for three years, since the date of its registration". Record in the note which period the disclosure covers.
- **Policies:** P1, P2, P7, P16.

### 5.10 `ANNEX_I_PART_D_01_ASSET_NAME_ABBREVIATION`: Crypto-asset name and abbreviation (Annex I, Part D, item 1)

- **Element:** the name of the crypto-asset and its abbreviation or ticker.
- **present:** both the name and an abbreviation or ticker.
- **missing:** either is absent (the note names which).
- **[OJ check]:** the drafting reading of item 1 also covers the name of the crypto-asset project. Recommended: label on the crypto-asset name and abbreviation only.
- **Policies:** P1.

### 5.11 `ANNEX_I_PART_D_03_IMPLEMENTATION_PERSONS`: Persons involved in implementation (Annex I, Part D, item 3)

- **Element:** the natural or legal persons involved in the implementation of the crypto-asset project.
- **present:** at least one identified person (name, or name and role) involved in implementing the project, such as the developing entity or team.
- **missing:** no identified person. A statement such as "developed by an open community" with no identified person: P17.
- **[OJ check]:** the drafting reading lists advisors, development team and crypto-asset service providers as examples, and asks for business addresses or domicile. Recommended: neither the full list nor addresses are required for `present`; record gaps in the note.
- **Policies:** P1, P6, P17.

### 5.12 `ANNEX_I_PART_F_02_CHARACTERISTICS_FUNCTIONALITY`: Characteristics and functionality (Annex I, Part F, item 2)

- **Element:** a description of the characteristics and functionality of the crypto-asset.
- **present:** the document describes what the crypto-asset is and what holders can do with it (for example transferability, supply, use in a network or service).
- **missing:** no description beyond the name or type.
- **[OJ check]:** the drafting reading also mentions data needed to classify the white paper in the ESMA register and when functionalities will apply. Recommended: not required for `present`.
- **Policies:** P1, P3.

### 5.13 `ARTICLE_6_05_MANDATORY_WARNINGS`: Mandatory warning statements (Article 6(5))

- **Element:** the Article 6(5) statements, as encoded in `examples/numbered-other-draft.xhtml` (fields 04 to 06):
  - (a) the crypto-asset may lose its value in part or in full;
  - (b) it may not always be transferable;
  - (c) it may not be liquid;
  - (d) a statement about utility tokens, where the offer concerns a utility token **[OJ check]**: the drafting reading is that the utility token may not be exchangeable against the good or service promised, especially if the project fails or is discontinued;
  - (e) it is not covered by the investor compensation schemes under Directive 97/9/EC **[OJ check]**: the drafting reading adds "as applicable";
  - (f) it is not covered by the deposit guarantee schemes under Directive 2014/49/EU.
- **present:** every applicable statement appears, in the same substance (paraphrase is fine).
- **missing:** at least one applicable statement is absent; the note names which.
- (d) is decided per document: if the crypto-asset is not a utility token, (d) is not required, and the cell is still labelled on (a) to (c), (e) and (f).
- **Policies:** P4.

### 5.14 `ARTICLE_6_06_MANAGEMENT_BODY_STATEMENT`: Management body statement (Article 6(6))

- **Element:** a statement of the management body confirming that (i) the white paper complies with Title II of MiCAR and (ii) to the best of the management body's knowledge, the information presented is fair, clear and not misleading, and (iii) the white paper makes no omission likely to affect its import (wording as in `examples/numbered-other-draft.xhtml`, field 03).
- **present / missing:** depends on P4 (recommended: `present` if (i) and (ii) appear in a statement attributed to the management body; record whether (iii) appears).
- **[OJ check]:** whose management body (offeror, person seeking admission to trading, or trading-platform operator) and where the statement must sit in the document.
- **Policies:** P2, P4.

### 5.15 `ARTICLE_6_07_SUMMARY`: Summary (Article 6(7))

- **Element:** a summary that gives key information about the offer to the public or the admission to trading in brief, non-technical language.
- **present / missing:** depends on P4 (recommended: `present` if the document contains a section identified as a summary that gives such key information; record in the note whether the summary warning appears).
- **Summary warning:** the repository's template example (field 07, "Warning in accordance with Article 6(7), second subparagraph") states that the summary should be read as an introduction, that a purchase decision should rest on the white paper as a whole, and that the offer or admission is not an offer or solicitation to purchase financial instruments. **[OJ check]**: confirm the full list of required warning elements.
- **Policies:** P4.

## 6. Open codebook policies

Each policy needs a decision before adoption. Tick one option per row and keep the reason in the decision column. P1 to P10 apply across rules; P11 to P17 are the rule-card judgments referred to in section 5. The recommended defaults are the drafter's suggestion; they keep the measurement to **presence** and avoid deciding legal sufficiency.

| # | Question | Options | Recommended default | Decision |
| --- | --- | --- | --- | --- |
| P1 | A template field is present but reads "N/A", "not applicable", "none", or is empty. | (a) `missing`, unless the element appears elsewhere for the right person; (b) `not_applicable` whenever the paper marks the field N/A; (c) `present` because the field was addressed. | (a). A heading or field label without a value never makes a cell `present`. Use `not_applicable` only under step 3 of section 3, with the reviewer's own reasons. **[Legal judgment]** | [ ] |
| P2 | The white paper is drawn up by the operator of a trading platform, and its details appear in Part C while Part A reads "N/A". | (a) the operator's details in Part C answer the Part A items (`present`, pinpoint to Part C, note `P2`); (b) Part A must be completed for an offeror or person seeking admission to trading; operator details do not count (`missing`); (c) `not_applicable` where no person other than the operator seeks admission. | (a) for the presence measurement, with the note recording that the details are the operator's. Whether the operator is "the person seeking admission to trading" in these cases is a legal question. **[Legal judgment]** | [ ] |
| P3 | Presence versus adequacy. | (a) label presence of a responsive disclosure; (b) label legal sufficiency. | (a). The detector claims no more than presence; (b) would turn the study into a compliance assessment, which `limitations.md` rules out. | [ ] |
| P4 | Completeness thresholds for Art. 6(5), 6(6) and 6(7). | 6(5): (a) all applicable statements, or (b) the loss-of-value statement suffices. 6(6): (a) (i) and (ii), or (b) (i), (ii) and (iii). 6(7): (a) a recognisable summary, or (b) a summary plus the complete warning. | 6(5) (a); 6(6) (a), noting (iii); 6(7) (a), noting the warning. The notes allow the stricter readings to be run as a sensitivity analysis. **[Legal judgment]** | [ ] |
| P5 | A Digital Token Identifier (DTI) or other token identifier is given, but no identifier of the legal person. | (a) does not satisfy Part A item 5; (b) satisfies it. | (a). A DTI identifies the token, not the offeror or person seeking admission to trading. **[Legal judgment]** | [ ] |
| P6 | WP-001 concerns a crypto-asset (named in `source-manifest.json`) for which it is arguable whether there is an identifiable issuer. | (a) label WP-001 like any other document, on presence; (b) mark its cells `not_applicable`. | (a). The paper was notified and registered, and the study measures disclosure presence in registered documents. Marking cells `not_applicable` would be a policy choice, not a legal consequence: ESMA Q&A 2552 is reported by secondary sources to address crypto-assets without an identifiable issuer, but its text was not opened for this draft. **[Legal judgment]** | [ ] |
| P7 | Financial condition and registration date for recently established persons. | (a) `present` if the document states the financial condition for the period since registration, or states that no financial history exists because the person was recently established; (b) only full three-year information counts. | (a), with the note recording the period covered. A bare "N/A" without explanation is `missing` (P1). **[Legal judgment]** | [ ] |
| P8 | Content outside the hashed bytes: linked documents, other language versions, a landing page that links to the white paper. | (a) only the hashed bytes count; elements outside them are `extraction_failure` where the capture is evidently not the complete white paper, otherwise `missing`; (b) the reviewer may follow links. | (a). Following links would label bytes the detector never saw. Extraction failure must not be classified as substantive absence (`limitations.md:21`). | [ ] |
| P9 | When to use `uncertain`. | (a) only for genuine ambiguity, with both readings in the note; (b) whenever the reviewer is unsure. | (a). The analysis reports `uncertain` counted as `missing` and as `present` (analysis plan, sensitivity analyses). | [ ] |
| P10 | A legal-form designation appears only within the registered name (for example "Example GmbH"). | (a) `present`; (b) `missing` unless the legal form is stated separately. | (a), if the designation unambiguously denotes a legal form, with the pinpoint to where the name appears. **[Legal judgment]** | [ ] |
| P11 | Address precision (5.2): only a city, or only a country, is given for the registered address. | (a) `missing`, with a note quoting what is given; (b) `present`; (c) `uncertain`. | (a). A city or country alone does not identify the registered office. **[Legal judgment]** | [ ] |
| P12 | Date precision (5.3): only a year, or a month and year, of registration is given. | (a) `present`, with the note recording the precision given; (b) `missing` unless a full date is given. | (a). A year is a responsive, if imprecise, disclosure; the note keeps the stricter reading available for a sensitivity analysis. **[Legal judgment]** | [ ] |
| P13 | Which identifier counts (5.4) when no LEI is given. | (a) any official register number of the person, such as a company-register number; (b) only an identifier required by the person's national law, which the reviewer establishes per document. | (a), with the note naming the register. Linked to the [OJ check] in 5.4. **[Legal judgment]** | [ ] |
| P14 | Vague response period (5.6): "promptly", "as soon as possible" or similar, with no number of days. | (a) `missing`, with a note quoting the wording; (b) `uncertain`; (c) `present`. | (a). The element is a period of days. **[Legal judgment]** | [ ] |
| P15 | Conflicts of interest (5.8): (i) an explicit statement that no conflicts have been identified; (ii) only a generic reference to a conflicts policy, not tied to this offer or admission. | (i): (a) `present`; (b) `missing`. (ii): (a) `uncertain`; (b) `missing`; (c) `present`. | (i) (a): the statement addresses the element for this offer or admission. (ii) (a), with a note quoting the reference. **[Legal judgment]** | [ ] |
| P16 | Financial condition by reference only (5.9): the document refers to financial statements published elsewhere and gives no figures or narrative of its own. | (a) `missing`, with a note; (b) `uncertain`; (c) `present`. | (a). Only the hashed bytes count (P8), and they contain no description of the financial condition. **[Legal judgment]** | [ ] |
| P17 | No identified implementation persons (5.11): the document attributes the project to an "open community" or similar and names no person. | (a) `missing`, with a note quoting the statement; (b) `not_applicable`, together with P6; (c) `uncertain`. | (a), with the note quoting the statement. **[Legal judgment]** | [ ] |

## 7. Calibration

Before adopting this codebook, the reviewer labels one calibration document under the analysis plan (section 4 of `analysis-plan.md`). Calibration may change wording and policy choices in this codebook. Changes after the pre-registration commit are logged in section 8 with date and reason, and are reported as deviations.

## 8. Change log

| Date | Change | Reason | Before or after pre-registration |
| --- | --- | --- | --- |
| 2026-10-14 | First draft. | Phase 0 of the study plan. | Before |
| 2026-10-14 | Rule-card judgments moved into section 6 as P11 to P17; `STUDY_RULES` cited by symbol; section 4 cross-reference corrected; WP-001's crypto-asset no longer named here. | Draft review. | Before |
| 2026-10-28 | Signing order in the banner (adoption on `main` after the tooling is merged); open LEI decision for 5.1 and 5.2. | Main merged into the draft; open pull request #51. | Before |
