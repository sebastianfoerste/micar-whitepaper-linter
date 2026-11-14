# Codebook: human review of the 150 document-rule cells

> **DRAFT, not adopted; it reaches `main` as unsigned draft tooling and is adopted there in a separate commit.**
>
> Drafted with AI assistance (Claude) on 2026-10-14 for the reviewer's decision. No lawyer has reviewed this draft. Until the reviewer adopts it, it states options and recommended defaults, not rules. The legal readings of sections 1 and 5 and the LEI decision were settled under the owner's instruction of 10 November 2026, on the Official Journal text read on EUR-Lex on 14 November 2026 (section 1). The owner has not reviewed them individually; they become final only with the owner's adoption commit (step 3 below).
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
> - Policy decisions recorded in section 6: [ ] all decided
> - LEI decision in section 5 (documents that give a valid LEI, cards 5.1 and 5.2): decided under the owner's instruction of 10 November 2026 (box after card 5.2); the adoption commit adopts it

## 1. Status of the legal text

The requirement descriptions below follow MiCAR (Regulation (EU) 2023/1114) Article 6 and Annex I **as encoded in this repository**:

- the rule IDs, Annex labels and element descriptions in the `rules` list of `findings-pseudonymous.json`, which the study measures as committed and which equals `STUDY_RULES` in `src/micar_linter/batch.py` (`analysis-plan.md` section 2);
- the Article 6 citations in `src/micar_linter/rules/common.py`;
- the Article 6(3), 6(5), 6(6) and 6(7) statement fields of the synthetic template example `examples/numbered-other-draft.xhtml`.

The study measures only the frozen batch study detector (`analysis-plan.md` section 2), not the rule engine that the CLI runs. The CLI's point rules `ANNEX_I.A.P6` and `ANNEX_III.A.P6`, which check the Part A item 6 contact details that cards 5.5 and 5.6 also cover, are outside it.

This codebook's own readings were first drafted without the Official Journal text, because EUR-Lex and ESMA could not be reached. The table in `REVIEWING.md` step 3 (lines 64 to 80), which compares each rule's missing element with the text of its provision, was checked against the Official Journal text at the ELI of Regulation (EU) 2023/1114, not against a consolidated version (`REVIEWING.md` line 62). Where that table answers a reading, the card cites the table's line under **Checked**.

The readings that the table does not answer were settled under the owner's instruction of 10 November 2026, on the Official Journal text read on EUR-Lex on 14 November 2026: Regulation (EU) 2023/1114 (CELEX 32023R1114, OJ L 150, 9.6.2023), Article 6 and Annex I, and Commission Implementing Regulation (EU) 2024/2984 (CELEX 32024R2984, OJ L, 2024/2984, 3.12.2024), its recitals and Table 2 of its Annex, both retrieved by CELEX number from the Publications Office's Cellar, which EUR-Lex serves. Article 6 and Annex I read the same in the consolidated version of 9 January 2024 (CELEX 02023R1114-20240109, the latest consolidated version on 14 November 2026), and the English corrigendum of 2 May 2024 (OJ L, 2024/90275) does not touch them. The card quotes the passage under **Checked against the Official Journal**. The owner has not reviewed these readings individually; they become final with the owner's adoption commit (banner, step 3). One marker flags what the reviewer must still settle before adoption:

- **[Legal judgment]**: the cell cannot be labelled consistently without a policy choice. Section 6 lists the options and a recommended default.

The review sheets carry no rule label and no requirement text. `REVIEWING.md` step 3 gives each rule's label and missing element and how its provision differs from that element. `review-protocol.md` governs, then `REVIEWING.md` (its line 3), then this codebook.

## 2. What the reviewer decides

One cell is one question: **do the exact source bytes with the recorded SHA-256 contain the disclosure element that the rule names?**

- The unit is the cached document whose hash matches `document-provenance.json`. Run `micar-study-verify-cache` or the check in `REVIEWING.md` step 1 first; do not label a document whose bytes do not verify.
- The question is **presence** of a responsive disclosure, not its legal sufficiency or accuracy (policy P3).
- What must be present is set by the reference standard that the owner records in `review-protocol.md` before labelling (`REVIEWING.md` step 2): the rule's missing element (the missing-element standard) or the provision as a whole (the provision standard). That choice is separate from P3, and the cards below follow the recorded standard. Where the other standard would give a different label, say so in `review_note` (`REVIEWING.md` line 82).
- The reviewer reads the source document itself (rendered XHTML or HTML, or the PDF), not the text the detector extracted.
- The reviewer answers without seeing the detector's result. During labelling, work only in `human-review-blinded.csv` with this codebook, `review-protocol.md`, `REVIEWING.md` and the source document. Do not open `human-review-matrix.csv`, `findings-pseudonymous.json`, `findings-pseudonymous.csv`, `findings-summary.md` or any playground output for these documents.
- This codebook contains no detector patterns and no detector outcomes. The reviewer wrote the detector, so blinding is partial; the analysis plan discloses this.

## 3. Labels

Use exactly one label per cell. The definitions refine `review-protocol.md` (Labels table) and do not replace it.

| Label | Use when | Required fields |
| --- | --- | --- |
| `present` | The source bytes contain a disclosure that responds to the element, for the person the rule names. | `source_pinpoint`; `review_note` when a policy from section 6 decided the label. |
| `missing` | The reviewer inspected the parts of the source where the element belongs, and searched the whole document, and did not find it. Also used when only part of a multi-part element is given (the note names the missing part). | `source_pinpoint` stating where the element was expected and what was searched (`review-protocol.md`, "First review" step 5); `review_note` for partial disclosures. The merge and `micar-review-summary` also accept a `missing` cell with a note and no pinpoint (`REVIEWING.md` line 60), so they do not catch a missing pinpoint; record one wherever you can. |
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
  - XHTML or HTML in the template layout of Implementing Regulation (EU) 2024/2984: the field as printed, with its heading, for example `Part A, field A.2 "Legal form"`. Template field numbers (A.1, A.2, ...) are not Annex I item numbers, and authors number fields differently (`src/micar_linter/numbered_fields.py:5`). Cite the field as printed.
  - Inline XBRL: the concept name of the fact, if used.
  - PDF: `p. N` using the page index the PDF viewer shows (first page = 1), plus the section heading.
  - For `missing`: the part and fields inspected and the search terms used, for example `Part A fields A.1 to A.12; searched "phone", "tel", "+"`.
- `review_note`: free text. Cite the policy number when a policy decided the label (for example `P1`).

## 4. Which person the Part A items refer to

The Part A items concern **the offeror or the person seeking admission to trading**. Some white papers are drawn up by the operator of a trading platform, whose details then appear in Part C (`src/micar_linter/rules/annex_i.py`, rules ANNEX_I.A, ANNEX_I.B and ANNEX_I.C at lines 72, 99 and 110; the comment at lines 66 to 70 says why they do not ask for the legal form or the registered address: a white paper that gives an LEI need not state them; see the box after 5.2). Whether the operator's details answer the Part A items is policy P2 **[Legal judgment]**. Information about a different issuer (Part B) does not answer a Part A item.

## 5. Rule cards

Each card gives the element, what counts as `present` and `missing`, and the policies that may decide the cell. The order follows `STUDY_RULES`, as do each document's rows in `human-review-blinded.csv`.

### 5.1 `ANNEX_I_PART_A_02_LEGAL_FORM`: Legal form (Annex I, Part A, item 2)

- **Element:** the legal form of the offeror or person seeking admission to trading.
- **present:** a legal form is stated for that person, for example a company type under a named national law. A legal-form designation that is part of the registered name (such as "GmbH" or "S.A.") counts if policy P10 is adopted.
- **missing:** no legal form for that person; the field is empty or reads "N/A" (P1).
- **Policies:** P1, P2, P10.

### 5.2 `ANNEX_I_PART_A_03_REGISTERED_ADDRESS`: Registered address or head office (Annex I, Part A, item 3)

- **Element:** the registered address (registered office or seat) of that person.
- **present:** an address that identifies the registered office: street and number (or equivalent), postcode, city and country.
- **missing:** no address. A city or country alone: P11.
- **Checked (`REVIEWING.md` line 67):** item 3 reads "Registered address and head office, where different", so it asks for both where they differ. Under the missing-element standard, label on the registered address or head office; under the provision standard, the table's last column applies. If the document indicates a different head office without giving it, say so in the note.
- **Policies:** P1, P2, P11.

> **Documents that give a valid LEI (5.1 and 5.2).** The repository holds three readings:
>
> - The CLI's party rules: since #51 (merged through #62), the comment at `src/micar_linter/rules/annex_i.py` lines 66 to 70 reads recital 2 of Implementing Regulation (EU) 2024/2984 as letting a white paper that gives an LEI leave out the legal form and the registered address, so ANNEX_I.A and ANNEX_I.B no longer ask for them.
> - The CLI's LEI rules: `_no_lei_finding` in `src/micar_linter/linter.py` (lines 640 to 652) sends a draft with no LEI to check to Review when a party section has text other than placeholders, because point 5 of each party Part allows another identifier required pursuant to applicable national law.
> - The study: the `REVIEWING.md` table finds "No difference" between the legal-form rule and Annex I, Part A, item 2 of MiCAR (line 66), and `STUDY_RULES` in `src/micar_linter/batch.py` still checks the legal form.
>
> **Decision.** The study does not follow the CLI's reading. Under either reference standard, a valid LEI makes a 5.1 or 5.2 cell neither `present` nor `not_applicable`: label the legal form and the registered address on what the source bytes state (P8). Where the bytes give an LEI of that person but no legal form (5.1) or no registered address (5.2), label the cell `missing` and write in `review_note` "LEI given", the LEI and the white paper's date of notification, so that a sensitivity analysis can count these cells as `not_applicable` (`analysis-plan.md` section 10, S5). The decision presupposes option (a) of P3 and of P8 (section 6), the recommended defaults; if the reviewer chooses otherwise there, the decision is reopened before adoption (`analysis-plan.md` step 0.7).
>
> **Checked against the Official Journal.** Annex I, Part A of Regulation (EU) 2023/1114 lists "2. Legal form;", "3. Registered address and head office, where different;" and "5. Legal entity identifier or another identifier required pursuant to applicable national law;" with no exception for a document that gives an LEI. The exception is in Implementing Regulation (EU) 2024/2984, which lays down the forms, formats and templates of Article 6(11) MiCAR and applies from 23 December 2025 (its Article 4). Its recital 2 reads: "where a valid legal entity identifier code is provided in the crypto-asset white paper, it should not be required for the crypto-asset white paper to contain the information that is retrievable from that legal entity identifier. That concerns the following information: legal form, registered address and head office (where different) and identity of the parent company of the issuer." Table 2 marks field A.2 "Legal form" as "Only applicable if a (LEI) is not provided in field A.6", and fields A.3 "Registered address" and A.4 "Head office" in the same way. Information retrievable from the LEI record lies outside the hashed bytes, which alone count (P8), and the study measures presence, not legal sufficiency (P3). Whether a document could rely on its LEI at its date of notification is a question of sufficiency; the note keeps it open for the sensitivity analysis. The study detector's legal-form check and the table's "No difference" (line 66) follow Annex I.
>
> Settled under the owner's instruction of 10 November 2026 (open points to be decided on the drafter's recommendation; AI-assisted), on the Official Journal text read on EUR-Lex on 14 November 2026. The owner has not reviewed this point individually; it becomes final with the owner's adoption commit (banner, step 3).

### 5.3 `ANNEX_I_PART_A_04_REGISTRATION_DATE`: Registration date (Annex I, Part A, item 4)

- **Element:** the date of registration (incorporation or establishment) of that person.
- **present:** a stated date of registration, incorporation or establishment. A year alone: P12.
- **missing:** no date; a date that refers to something else (the white paper, the token launch, a licence) does not count.
- **Checked (`REVIEWING.md` line 68):** item 4 names only the "Date of the registration", while the rule's missing element also accepts a date of incorporation or establishment. Under the missing-element standard, any of the three dates counts; under the provision standard, the table's last column applies. Record in the note which date the document gives.
- **Checked against the Official Journal:** Annex I, Part A, item 4 reads "Date of the registration;", and field A.5 of Table 2 of Implementing Regulation (EU) 2024/2984 asks for the "Registration date", "Date of the registration". The reading above stands.
- **Policies:** P1, P2, P7, P12.

### 5.4 `ANNEX_I_PART_A_05_LEI_OR_IDENTIFIER`: LEI or other identifier (Annex I, Part A, item 5)

- **Element:** the legal entity identifier (LEI) of that person, or another identifier of that person.
- **present:** a 20-character LEI (ISO 17442) attributed to that person, or another identifier of the legal person, such as a company-register number, that the recorded standard accepts (see **Checked** and P13).
- **missing:** no identifier of the person. An identifier of the **token** (DTI, ISIN, contract address) does not count (P5).
- **Checked (`REVIEWING.md` line 69):** the other identifier must be one "required pursuant to applicable national law". Under the missing-element standard, another identifier of the person counts, and P13 decides which; under the provision standard, the table's last column applies: only an identifier that the person's applicable national law requires counts, which the reviewer establishes per document, and P13 does not apply.
- **Checked against the Official Journal:** Annex I, Part A, item 5 reads "Legal entity identifier or another identifier required pursuant to applicable national law;". Table 2 of Implementing Regulation (EU) 2024/2984 asks in field A.6 for the LEI "when available" and in field A.7 for "Another identifier required pursuant to applicable national law", a field that "only applies to entities for which a national identifier is required in accordance with applicable national law". The reading above stands: P13 applies only under the missing-element standard.
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
- **Checked (`REVIEWING.md` line 72):** item 8 also asks for the "business addresses" of the members of the management body. Under the missing-element standard, business addresses are not required for `present`; under the provision standard, the table's last column applies. Record their absence in the note either way, so that the other standard can be applied in a sensitivity analysis.
- **Policies:** P1, P2.

### 5.8 `ANNEX_I_PART_E_18_CONFLICTS_OF_INTEREST`: Conflicts of interest (Annex I, Part E, item 18)

- **Element:** disclosure of conflicts of interest relating to the offer to the public or the admission to trading.
- **present:** the document addresses potential conflicts of interest in relation to this offer or admission: it describes them, or explains how they are managed. An explicit statement that no conflicts have been identified: P15.
- **missing:** the document does not address conflicts of interest for this offer or admission.
- **Generic reference only:** a reference to a conflicts policy that is not tied to this offer or admission: P15.
- **Checked (`REVIEWING.md` line 73):** Annex I, Part E, item 18 asks for "Potential conflicts of interest of the persons involved in the offer to the public or admission to trading, arising in relation to the offer or admission to trading". Under the missing-element standard, a conflicts-of-interest disclosure for this offer or admission decides the label; under the provision standard, the table's last column applies, and the conflicts must be those of the persons involved in the offer or admission. Record in the note whose conflicts the disclosure covers. The review sheets name Part E, item 18, as `STUDY_RULES` does.
- **Checked against the Official Journal:** the quotation above is the wording of Annex I, Part E, item 18, and field E.38 "Conflicts of interest" of Table 2 of Implementing Regulation (EU) 2024/2984 repeats it. The reading above stands.
- **Policies:** P1, P3, P15.

### 5.9 `ANNEX_I_PART_A_10_FINANCIAL_CONDITION`: Financial condition (Annex I, Part A, item 10)

- **Element:** the financial condition of that person.
- **present:** the document describes that person's financial condition in its own text: figures from financial statements, or a narrative on financial position, results or solvency.
- **missing:** nothing on financial condition, or a bare "N/A" (P1). Only a reference to accounts published elsewhere: P16.
- **Checked (`REVIEWING.md` line 74):** the item covers the past three years or, where the person has not been established for the past three years, the period since the date of registration, assessed on a fair review of the development and performance of the business and of its position, which is to be "a balanced and comprehensive analysis". Under the missing-element standard, a description of the financial condition decides the label; under the provision standard, the table's last column applies. Record in the note which period the disclosure covers.
- **Policies:** P1, P2, P7, P16.

### 5.10 `ANNEX_I_PART_D_01_ASSET_NAME_ABBREVIATION`: Crypto-asset name and abbreviation (Annex I, Part D, item 1)

- **Element:** the name of the crypto-asset and its abbreviation or ticker.
- **present:** both the name and an abbreviation or ticker.
- **missing:** either is absent (the note names which).
- **Checked (`REVIEWING.md` line 75):** item 1 also covers the name of the crypto-asset project, adds "if different from the name of the offeror or person seeking admission to trading" and reads "abbreviation or ticker handler". Under the missing-element standard, label on the crypto-asset name and abbreviation; under the provision standard, the table's last column applies.
- **Policies:** P1.

### 5.11 `ANNEX_I_PART_D_03_IMPLEMENTATION_PERSONS`: Persons involved in implementation (Annex I, Part D, item 3)

- **Element:** the natural or legal persons involved in the implementation of the crypto-asset project.
- **present:** at least one identified person (name, or name and role) involved in implementing the project, such as the developing entity or team.
- **missing:** no identified person. A statement such as "developed by an open community" with no identified person: P17.
- **Checked (`REVIEWING.md` line 76):** item 3 asks for "Details of all" such persons, "including business addresses or domicile of the company", such as advisors, the development team and crypto-asset service providers. Under the missing-element standard, neither the full list nor addresses are required for `present`; under the provision standard, the table's last column applies. Record gaps in the note.
- **Policies:** P1, P6, P17.

### 5.12 `ANNEX_I_PART_F_02_CHARACTERISTICS_FUNCTIONALITY`: Characteristics and functionality (Annex I, Part F, item 2)

- **Element:** a description of the characteristics and functionality of the crypto-asset.
- **present:** the document describes what the crypto-asset is and what holders can do with it (for example transferability, supply, use in a network or service).
- **missing:** no description beyond the name or type.
- **Checked (`REVIEWING.md` line 77):** item 2 asks for the characteristics and functionality, including the data necessary for classifying the white paper in the register under Article 109 and when the functionalities are planned to apply. Under the missing-element standard, neither the register data nor when the functionalities apply is required for `present`; under the provision standard, the table's last column applies.
- **Policies:** P1, P3.

### 5.13 `ARTICLE_6_05_MANDATORY_WARNINGS`: Mandatory warning statements (Article 6(5))

- **Element:** the Article 6(5) statements, as fields 04 to 06 of Table 2 of Implementing Regulation (EU) 2024/2984 and `examples/numbered-other-draft.xhtml` set them out. Article 6(5) asks for "a clear and unambiguous statement that":
  - (a) "the crypto-asset may lose its value in part or in full";
  - (b) "the crypto-asset may not always be transferable";
  - (c) "the crypto-asset may not be liquid";
  - (d) "where the offer to the public concerns a utility token, that utility token may not be exchangeable against the good or service promised in the crypto-asset white paper, especially in the case of a failure or discontinuation of the crypto-asset project" (`REVIEWING.md` line 78);
  - (e) "the crypto-asset is not covered by the investor compensation schemes under Directive 97/9/EC" (`REVIEWING.md` line 78);
  - (f) "the crypto-asset is not covered by the deposit guarantee schemes under Directive 2014/49/EU".
- **Checked against the Official Journal:** the quotations above are the wording of Article 6(5). The drafting reading of (d), "especially if the project fails or is discontinued", is in the text ("especially in the case of a failure or discontinuation of the crypto-asset project"). The drafting reading of (e), "as applicable", is not: (e) is unconditional, as (f) is. (e) and (f) are separate points of Article 6(5), and nothing in the text lets one of them stand in for the other; field 06 of Table 2 states both in one predefined sentence. Both scheme statements are therefore required, and one of them alone does not answer the protection or compensation statements.
- **present:** under the missing-element standard, the loss-of-value statement (a) and both protection or compensation statements, (e) and (f), appear, in the same substance (paraphrase is fine), as in the synthetic example of `REVIEWING.md` line 39; record in the note which of (b) to (d) are absent. Under the provision standard, every applicable statement appears.
- **missing:** a statement that the recorded standard requires is absent; the note names which.
- Under the provision standard, (d) is decided per document: it is required only where the white paper concerns an offer to the public of a utility token, because Article 6(5)(d) applies "where the offer to the public concerns a utility token". For a white paper that concerns only an admission to trading, or a crypto-asset that is not a utility token, (d) is not required (field 05 of Table 2 then reads "false", for "Not applicable"), and the cell is labelled on (a) to (c), (e) and (f).
- **Checked (`REVIEWING.md` line 78):** Article 6(5) asks for one clear and unambiguous statement covering these points, while the rule's missing element names only the loss-of-value and protection or compensation statements. Under the missing-element standard, label on those; under the provision standard, the table's last column applies.
- **Policies:** P4.

### 5.14 `ARTICLE_6_06_MANAGEMENT_BODY_STATEMENT`: Management body statement (Article 6(6))

- **Element:** a statement of the management body of the offeror, the person seeking admission to trading or the operator of the trading platform, confirming that (i) the white paper complies with Title II of MiCAR and (ii) to the best of the management body's knowledge, the information presented is fair, clear and not misleading, and (iii) the white paper makes no omission likely to affect its import (wording as in `examples/numbered-other-draft.xhtml`, field 03).
- **present / missing:** depends on P4 (under the missing-element standard, recommended: `present` if (i) and (ii) appear in a statement attributed to the management body; record whether (iii) appears).
- **Checked (`REVIEWING.md` line 79):** the statement confirms compliance "with this Title" and that the white paper "makes no omission likely to affect its import", and it follows the Article 6(3) statement. Under the provision standard, the table's last column applies.
- **Checked against the Official Journal:** Article 6(6) reads: "The crypto-asset white paper shall contain a statement from the management body of the offeror, the person seeking admission to trading or the operator of the trading platform." The statement may come from the management body of any of the three. Article 6(6) does not tie it to the person that drew up the white paper, which under Article 6(1), second subparagraph, may be another person ("In cases where the crypto-asset white paper is not drawn up by the persons referred to in the first subparagraph, points (a), (b) and (c), ..."). Under either reference standard:
  - a statement attributed to the management body of the offeror, the person seeking admission to trading or the operator counts, whichever of them drew up the white paper;
  - a statement attributed to "the management body" without naming a person, as in the predefined text of field 03 of Table 2 of Implementing Regulation (EU) 2024/2984 ("to the best of the knowledge of the management body"), counts as that of the person the white paper presents as offeror, person seeking admission to trading or operator;
  - a statement given only for another person, such as a person that drew up the white paper under Article 6(1), second subparagraph, is not the Article 6(6) statement: label the cell `missing` and say in the note whose statement it is.

  Record in the note whose management body the statement names, if any. Policy P2 no longer decides this card, because Article 6(6) names the operator.
- **Policies:** P4.

### 5.15 `ARTICLE_6_07_SUMMARY`: Summary (Article 6(7))

- **Element:** a summary that gives key information about the offer to the public or the admission to trading in brief, non-technical language.
- **present / missing:** depends on P4 (under the missing-element standard, recommended: `present` if the document contains a section identified as a summary that gives such key information; record in the note whether the summary warning appears).
- **Summary warning:** the repository's template example (field 07, "Warning in accordance with Article 6(7), second subparagraph") states that the summary should be read as an introduction, that a purchase decision should rest on the white paper as a whole, and that the offer or admission is not an offer or solicitation to purchase financial instruments. **Checked (`REVIEWING.md` line 80):** the summary is placed after the Article 6(6) statement, in "brief and non-technical language", with a warning covering points (a) to (d) of the second subparagraph of Article 6(7); under the provision standard, the table's last column applies.
- **Checked against the Official Journal:** the second subparagraph of Article 6(7) reads: "The summary shall contain a warning that:
  - (a) it should be read as an introduction to the crypto-asset white paper;
  - (b) the prospective holder should base any decision to purchase the crypto-asset on the content of the crypto-asset white paper as a whole and not on the summary alone;
  - (c) the offer to the public of the crypto-asset does not constitute an offer or solicitation to purchase financial instruments and that any such offer or solicitation can be made only by means of a prospectus or other offer documents pursuant to the applicable national law;
  - (d) the crypto-asset white paper does not constitute a prospectus as referred to in Regulation (EU) 2017/1129 of the European Parliament and of the Council or any other offer document pursuant to Union or national law."

  The predefined text of field 07 of Table 2 of Implementing Regulation (EU) 2024/2984 states all four points. The repository's template example states (a), (b) and the first half of (c) only: it lacks "any such offer or solicitation can be made only by means of a prospectus or other offer documents pursuant to the applicable national law" and point (d). Compare a document's warning with the four points, not with the example. Where the recorded standard or P4 asks for the complete warning, it is these four points; record in the note which of them are absent.
- **Policies:** P4.

## 6. Open codebook policies

Each policy needs a decision before adoption. Tick one option per row and keep the reason in the decision column. P1 to P10 apply across rules; P11 to P17 are the rule-card judgments referred to in section 5. The recommended defaults are the drafter's suggestion; they keep the measurement to **presence** and avoid deciding legal sufficiency.

| # | Question | Options | Recommended default | Decision |
| --- | --- | --- | --- | --- |
| P1 | A template field is present but reads "N/A", "not applicable", "none", or is empty. | (a) `missing`, unless the element appears elsewhere for the right person; (b) `not_applicable` whenever the paper marks the field N/A; (c) `present` because the field was addressed. | (a). A heading or field label without a value never makes a cell `present`. Use `not_applicable` only under step 3 of section 3, with the reviewer's own reasons. **[Legal judgment]** | [ ] |
| P2 | The white paper is drawn up by the operator of a trading platform, and its details appear in Part C while Part A reads "N/A". | (a) the operator's details in Part C answer the Part A items (`present`, pinpoint to Part C, note `P2`); (b) Part A must be completed for an offeror or person seeking admission to trading; operator details do not count (`missing`); (c) `not_applicable` where no person other than the operator seeks admission. | (a) for the presence measurement, with the note recording that the details are the operator's. Whether the operator is "the person seeking admission to trading" in these cases is a legal question. **[Legal judgment]** | [ ] |
| P3 | Presence versus adequacy. | (a) label presence of a responsive disclosure; (b) label legal sufficiency. | (a). The detector claims no more than presence; (b) would turn the study into a compliance assessment, which `limitations.md` rules out. P3 does not choose between the rule's missing element and the provision as a whole: that is the reference standard recorded in `review-protocol.md` (`REVIEWING.md` step 2), and presence is measured against it. | [ ] |
| P4 | Completeness thresholds for Art. 6(5), 6(6) and 6(7). | 6(5): (a) all applicable statements; (b) the loss-of-value statement and the protection or compensation statements that the rule's missing element names (`REVIEWING.md` line 39), which are both scheme statements, (e) and (f) (card 5.13: one of them alone is not enough); or (c) the loss-of-value statement alone. 6(6): (a) (i) and (ii), or (b) (i), (ii) and (iii). 6(7): (a) a recognisable summary, or (b) a summary plus the complete warning, points (a) to (d) of the second subparagraph of Article 6(7) (card 5.15). | Under the missing-element standard: 6(5) (b), noting the absent statements; 6(6) (a), noting (iii); 6(7) (a), noting the warning. Under the provision standard, the last column of the `REVIEWING.md` table applies (lines 78 to 80): 6(5) (a), 6(6) (b) and 6(7) (b). The notes allow the stricter readings to be run as a sensitivity analysis. P4 applies within the reference standard recorded in `review-protocol.md` (`REVIEWING.md` step 2); where the two conflict, the recorded standard governs. **[Legal judgment]** | [ ] |
| P5 | A Digital Token Identifier (DTI) or other token identifier is given, but no identifier of the legal person. | (a) does not satisfy Part A item 5; (b) satisfies it. | (a). A DTI identifies the token, not the offeror or person seeking admission to trading. **[Legal judgment]** | [ ] |
| P6 | WP-001 concerns a crypto-asset (named in `source-manifest.json`) for which it is arguable whether there is an identifiable issuer. | (a) label WP-001 like any other document, on presence; (b) mark its cells `not_applicable`. | (a). The paper was notified and registered, and the study measures disclosure presence in registered documents. Marking cells `not_applicable` would be a policy choice, not a legal consequence: ESMA Q&A 2552 is reported by secondary sources to address crypto-assets without an identifiable issuer, but its text was not opened for this draft. **[Legal judgment]** | [ ] |
| P7 | Financial condition and registration date for recently established persons. | (a) `present` if the document states the financial condition for the period since registration, or states that no financial history exists because the person was recently established; (b) only full three-year information counts. | (a), with the note recording the period covered. A bare "N/A" without explanation is `missing` (P1). **[Legal judgment]** | [ ] |
| P8 | Content outside the hashed bytes: linked documents, other language versions, a landing page that links to the white paper. | (a) only the hashed bytes count; elements outside them are `extraction_failure` where the capture is evidently not the complete white paper, otherwise `missing`; (b) the reviewer may follow links. | (a). Following links would label bytes the detector never saw. Extraction failure must not be classified as substantive absence (`limitations.md:21`). | [ ] |
| P9 | When to use `uncertain`. | (a) only for genuine ambiguity, with both readings in the note; (b) whenever the reviewer is unsure. | (a). The analysis reports `uncertain` counted as `missing` and as `present` (analysis plan, sensitivity analyses). | [ ] |
| P10 | A legal-form designation appears only within the registered name (for example "Example GmbH"). | (a) `present`; (b) `missing` unless the legal form is stated separately. | (a), if the designation unambiguously denotes a legal form, with the pinpoint to where the name appears. **[Legal judgment]** | [ ] |
| P11 | Address precision (5.2): only a city, or only a country, is given for the registered address. | (a) `missing`, with a note quoting what is given; (b) `present`; (c) `uncertain`. | (a). A city or country alone does not identify the registered office. **[Legal judgment]** | [ ] |
| P12 | Date precision (5.3): only a year, or a month and year, of registration is given. | (a) `present`, with the note recording the precision given; (b) `missing` unless a full date is given. | (a). A year is a responsive, if imprecise, disclosure; the note keeps the stricter reading available for a sensitivity analysis. **[Legal judgment]** | [ ] |
| P13 | Which identifier counts (5.4) when no LEI is given, under the missing-element standard. | (a) any official register number of the person, such as a company-register number; (b) only an identifier required by the person's national law, which the reviewer establishes per document. | (a), with the note naming the register. Under the provision standard P13 does not apply: only an identifier "required pursuant to applicable national law" counts (see the Checked note in 5.4, `REVIEWING.md` line 69, and the Official Journal check there). **[Legal judgment]** | [ ] |
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
| 2026-10-28 | Signing order in the banner (adoption on `main` after the tooling is merged); open LEI decision for 5.1 and 5.2, with its own banner checkbox. | Main merged into the draft; open pull request #51. | Before |
| 2026-10-30 | Rebuilt on the review workflow of #17: reviewers label `human-review-blinded.csv`, rows keep the `STUDY_RULES` order, the reference standard follows the record of `REVIEWING.md` step 2 in `review-protocol.md`, the [OJ check] items that the `REVIEWING.md` table answers cite it, the LEI box cites the three readings in the repository, and the tools' acceptance of a `missing` cell with a note is stated. | Owner's decision to keep `human-review-blinded.csv`, `REVIEWING.md` and `scripts/build_review_matrix.py` as the labelling path. | Before |
| 2026-10-30 | Cards 5.3, 5.4, 5.8 and 5.13 and policies P4 and P13 give the label under each reference standard; card 5.3 cites `REVIEWING.md` line 68; the repository line citations follow `main` at `d662f25`. | Review of the rebuild: some cards still settled the reference standard themselves. | Before |
| 2026-11-02 | The repository line citations follow `main` at `c7c99cf`: `_no_lei_finding` at `linter.py` lines 577 to 589 (before: 576 to 587) and the sentence on field numbers at `numbered_fields.py:5` (before: the module docstring at lines 4 to 6); the other line citations are unchanged. The LEI box states the condition of `_no_lei_finding` as its docstring does: Review when a party section has text other than placeholders. | #90 (`c7c99cf`) edited comments and docstrings in `linter.py` and `numbered_fields.py`, and the docstring of `_no_lei_finding` now states that condition. | Before |
| 2026-11-12 | The repository line citations follow `main` at `ab29114`: the rules ANNEX_I.A, ANNEX_I.B and ANNEX_I.C at `annex_i.py` lines 72, 99 and 110 and the comment at lines 66 to 70 (before: 60, 87, 98 and 54 to 58), and `_no_lei_finding` at `linter.py` lines 640 to 652 (before: 577 to 589). The cited code and comment are unchanged; `numbered_fields.py:5`, `limitations.md:21` and the `REVIEWING.md` line citations still hold. | Main merged into the draft at `ab29114` (#91 to #103); #98 and #103 added lines above the cited rules, and #91, #97, #98, #100 and #103 above `_no_lei_finding`. | Before |
| 2026-11-14 | The repository line citations follow `main` at `c0befc2` and are unchanged: every cited line was checked again in the merged tree. | Main merged into the draft at `c0befc2` (#106, release 1.3.0), which changed no cited file and, in `src/`, only the version in `__init__.py`. | Before |
| 2026-11-14 | The `[OJ check]` items and the LEI box are settled on the Official Journal text, read on EUR-Lex on 14 November 2026 (section 1): cards 5.3, 5.4 with P13 and 5.8 are confirmed; card 5.13 quotes Article 6(5), keeps (d)'s "especially in the case of a failure or discontinuation of the crypto-asset project", drops "as applicable" from (e) and requires both scheme statements (P4 option (b)); card 5.14 names the three management bodies of Article 6(6) and no longer cites P2; card 5.15 and P4 list the four points of the Article 6(7) warning; the LEI box decides that a valid LEI does not change the label of 5.1 or 5.2. Section 1 says that the study measures only the frozen batch detector, not the CLI's point rules `ANNEX_I.A.P6` and `ANNEX_III.A.P6`, and takes the rule descriptions from the findings' `rules` list. | Owner's instruction of 10 November 2026 to settle the open points on the drafter's recommendation (AI-assisted); not reviewed by the owner point by point. | Before |
| 2026-11-14 | Card 5.13 states both conditions of Article 6(5)(d): under the provision standard, (d) is required only where the white paper concerns an offer to the public of a utility token. The LEI box says that it presupposes option (a) of P3 and of P8. | Review of the round of 14 November 2026: the card named only the utility-token condition, and the box rested on two open policies without saying so. | Before |
