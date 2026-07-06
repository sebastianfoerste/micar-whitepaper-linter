# 10 Notified MiCAR Title II White Papers Reviewed: Recurring Annex I Disclosure Gaps Flagged by Deterministic Rules

Study title: **MiCAR White Paper Study 2026: Annex I Disclosure Patterns in Notified Title II White Papers**

This study runs deterministic first-pass checks over publicly available Title II crypto-asset white-paper text. Findings are potential disclosure gaps where a specified Annex I or Article 6 element was not found in extracted text.

The output is a research artifact. It does not provide legal advice and does not assess the full legal sufficiency of any white paper. Findings tables use WP-ID identifiers rather than printing issuer names inline; the source manifest links each WP-ID to its public ESMA register entry, so findings are traceable to their source and are not anonymized. Findings are machine-flagged and pending human legal review; a flag is a candidate gap in extracted text, not a confirmed deficiency by the named issuer.

## Sample

- Documents reviewed: 10
- Target sample size: 10
- Documents excluded before or during batch processing: 2
- Scope: Title II crypto-assets other than asset-referenced tokens and e-money tokens.
- Public identifiers: WP-001 style study IDs only.
- Raw white papers: not committed.

## Methodology

The sample is drawn from the ESMA Interim MiCA Register Title II source data and the local source manifest. The default v1 rule uses the first eligible WP-001 to WP-010 candidate set from the source pack, with candidate backfill if a document is inaccessible or extraction quality is insufficient.

Each document is loaded locally from `.study-cache/`. XHTML and HTML are parsed first, including visible text and available inline XBRL tag names. PDF files are extracted with `pypdf`. Text files are used only as a fallback. Weak extraction is recorded as an exclusion.

ESMA states on its MiCA page that the interim register includes five CSV files, with the Title II white-paper file covering crypto-assets other than asset-referenced tokens and e-money tokens. ESMA also states that white papers in the register have not been reviewed or approved by any competent authority.

## What the linter checks

The study checks 15 deterministic controls: 12 high-signal Annex I disclosure fields and 3 Article 6 controls.

- `ANNEX_I_PART_A_01_LEGAL_FORM`: Legal form (Annex I, Part A).
- `ANNEX_I_PART_A_02_REGISTERED_ADDRESS`: Registered address or head office (Annex I, Part A).
- `ANNEX_I_PART_A_03_REGISTRATION_DATE`: Registration date (Annex I, Part A).
- `ANNEX_I_PART_A_04_LEI_OR_IDENTIFIER`: LEI or other identifier (Annex I, Part A).
- `ANNEX_I_PART_A_05_CONTACT_PHONE_EMAIL`: Contact telephone number and email (Annex I, Part A).
- `ANNEX_I_PART_A_06_CONTACT_RESPONSE_PERIOD`: Response period for investor contact (Annex I, Part A, item 6).
- `ANNEX_I_PART_A_07_MANAGEMENT_BODY`: Management body identity and functions (Annex I, Part A).
- `ANNEX_I_PART_A_08_CONFLICTS_OF_INTEREST`: Conflicts of interest (Annex I, Part A).
- `ANNEX_I_PART_A_09_FINANCIAL_CONDITION`: Financial condition (Annex I, Part A).
- `ANNEX_I_PART_B_01_ASSET_NAME_ABBREVIATION`: Crypto-asset name and abbreviation (Annex I, Part B).
- `ANNEX_I_PART_B_02_DESIGN_DEVELOPMENT_PERSONS`: Persons involved in design and development (Annex I, Part B).
- `ANNEX_I_PART_B_03_UTILITY_CHARACTERISTICS`: Utility and characteristics (Annex I, Part B).
- `ARTICLE_6_05_MANDATORY_WARNINGS`: Mandatory warning statements (Article 6).
- `ARTICLE_6_06_MANAGEMENT_BODY_STATEMENT`: Management body statement (Article 6).
- `ARTICLE_6_07_SUMMARY`: Summary (Article 6).

## What it does not check

- It does not assess Annex II or Annex III white papers.
- It does not assess all Annex I fields.
- It does not decide whether any document is legally sufficient.
- It does not replace lawyer review of the full source document.
- It does not republish raw white-paper files.

## Aggregate findings

- Rules checked per document: 15
- Machine-flagged potential disclosure gaps: 21
- High-confidence potential gaps: 9
- Human review status: pending_review

## Most frequent potential gaps

| Rule ID | Count |
| --- | ---: |
| `ANNEX_I_PART_A_06_CONTACT_RESPONSE_PERIOD` | 4 |
| `ANNEX_I_PART_A_05_CONTACT_PHONE_EMAIL` | 3 |
| `ANNEX_I_PART_A_08_CONFLICTS_OF_INTEREST` | 3 |
| `ANNEX_I_PART_A_09_FINANCIAL_CONDITION` | 2 |
| `ANNEX_I_PART_A_02_REGISTERED_ADDRESS` | 1 |
| `ANNEX_I_PART_A_03_REGISTRATION_DATE` | 1 |
| `ANNEX_I_PART_A_04_LEI_OR_IDENTIFIER` | 1 |
| `ANNEX_I_PART_A_07_MANAGEMENT_BODY` | 1 |
| `ANNEX_I_PART_B_02_DESIGN_DEVELOPMENT_PERSONS` | 1 |
| `ANNEX_I_PART_B_03_UTILITY_CHARACTERISTICS` | 1 |

## Examples pending human review

### WP-002 - `ANNEX_I_PART_B_02_DESIGN_DEVELOPMENT_PERSONS`

- Annex item: Annex I, Part B
- Confidence: high
- Pinpoint: Design and development
- Missing element: persons involved in design and development
- Extracted context: ken sale rounds. Funds are held in multi-signature wallets and allocated as follows: 35% Product and Protocol Development, 35% Liquidity and Market-Making, 30% Operations, Legal, and Compliance. The company has no outstanding debt
- Review status: pending_review

### WP-003 - `ANNEX_I_PART_A_05_CONTACT_PHONE_EMAIL`

- Annex item: Annex I, Part A
- Confidence: high
- Pinpoint: Contact information
- Missing element: both contact telephone number and email address
- Extracted context: A A.6 Legal entity identifier N/A A.7 Another identifier required pursuant to applicable national law N/A A.8 Contact telephone number N/A A.9 E-mail address N/A A.10 Response time (Days) N/A A.11 Parent company N/A A.12 Member
- Review status: pending_review

### WP-004 - `ANNEX_I_PART_A_05_CONTACT_PHONE_EMAIL`

- Annex item: Annex I, Part A
- Confidence: high
- Pinpoint: Contact information
- Missing element: both contact telephone number and email address
- Extracted context: A A.6 Legal entity identifier N/A A.7 Another identifier required pursuant to applicable national law N/A A.8 Contact telephone number N/A A.9 E-mail address N/A A.10 Response time (Days) N/A A.11 Parent company N/A A.12 Member
- Review status: pending_review

### WP-005 - `ANNEX_I_PART_A_05_CONTACT_PHONE_EMAIL`

- Annex item: Annex I, Part A
- Confidence: high
- Pinpoint: Contact information
- Missing element: both contact telephone number and email address
- Extracted context: A A.6 Legal entity identifier N/A A.7 Another identifier required pursuant to applicable national law N/A A.8 Contact telephone number N/A A.9 E-mail address N/A A.10 Response time (Days) N/A A.11 Parent company N/A A.12 Member
- Review status: pending_review

### WP-007 - `ANNEX_I_PART_A_06_CONTACT_RESPONSE_PERIOD`

- Annex item: Annex I, Part A, item 6
- Confidence: high
- Pinpoint: Contact information
- Missing element: period of days within which an investor will receive an answer
- Extracted context: n. 583KB [PHONE]_[CRYPTO_ASSET]_Whitepaper_ATTR_V1_PDF.pdf PDF Download Open [ISSUER] Finance | MiCAR Whitepaper Contact [EMAIL] Scope Admission to trading only; no public offer. Key Risks The crypto-asset may lose value in part or in ful
- Review status: pending_review

## Limitations

The sample is not statistically representative. It is a reproducible pilot sample intended to test whether deterministic Annex I review produces useful public research artifacts.

Extraction quality can affect results. A field may be present in a source document but absent from extracted text, present under wording that the current deterministic pattern does not capture, or outside the v1 rule scope.

Excluded documents are listed in `findings-anonymized.json` with reasons.

## Reproducibility

```bash
uv run python -m micar_linter.esma_register \
  --csv .study-cache/esma-title-ii-register.csv \
  --out studies/2026-07-title-ii-annex-i-whitepaper-study/source-manifest.json

uv run micar-lint-batch \
  --manifest studies/2026-07-title-ii-annex-i-whitepaper-study/source-manifest.json \
  --cache .study-cache/title-ii-whitepapers \
  --annex annex-i \
  --out studies/2026-07-title-ii-annex-i-whitepaper-study/findings-anonymized.json

uv run micar-study-report \
  --findings studies/2026-07-title-ii-annex-i-whitepaper-study/findings-anonymized.json \
  --out studies/2026-07-title-ii-annex-i-whitepaper-study/findings-summary.md
```

## Sources

- ESMA MiCA register page: https://www.esma.europa.eu/esmas-activities/digital-finance-and-innovation/markets-crypto-assets-regulation-mica
- ESMA Article 6 interactive rulebook: https://www.esma.europa.eu/publications-and-data/interactive-single-rulebook/mica/article-6-content-and-form-crypto-asset
- ESMA Article 8 interactive rulebook: https://www.esma.europa.eu/publications-and-data/interactive-single-rulebook/mica/article-8-notification-crypto-asset-white
- ESMA Article 109 interactive rulebook: https://www.esma.europa.eu/publications-and-data/interactive-single-rulebook/mica/article-109-register-crypto-asset-white

Findings digest: `6966455c1a7fef214b85ebdb6076eb9845d412ca6a530a29b1b0db192650cafd`
