# Methodology

## Scope

The study covers MiCAR Title II white papers for crypto-assets other than asset-referenced tokens and e-money tokens. It maps the v1 checks to MiCAR Article 6 and Annex I.

ART and EMT white papers are out of scope because they require Annex II and Annex III logic.

## Source Basis

The study uses ESMA's interim MiCA register source data for Title II white papers and a local source pack of 20 candidate entries. Raw white-paper files are downloaded locally into `.study-cache/` and are not committed.

Each source row is normalized into `source-manifest.json` and receives a SHA-256 hash over the canonical normalized row.

The source manifest also records a SHA-256 hash of the source CSV or JSON used to build the manifest. This lets a reader distinguish the frozen pilot sample from later versions of ESMA's live Title II CSV.

Current-source check: ESMA's MiCA page was checked on 2026-07-06. The page displayed a register last update of 3 July 2026, listed the Title II white-paper CSV first among the five interim register files, and stated that registered white papers have not been reviewed or approved by any competent authority.

## Sampling

The v1 sample starts from the first 10 candidate entries in the local 20-entry source pack. In the committed run, `WP-006` and `WP-008` were excluded because the source URLs could not be fetched into the local cache, so `WP-011` and `WP-012` backfilled the reviewed sample.

Eligibility criteria:

1. Title II / non-ART / non-EMT scope.
2. Accessible white-paper URL.
3. Not marked as out-of-date or superseded.
4. Parseable as XHTML, HTML, PDF, or TXT with acceptable extraction quality.

The workflow can also run a seeded random sample with seed `20260702`.

The sample is not statistically representative. It is a reproducible pilot sample intended to test whether deterministic Annex I review produces useful public research artifacts. Excluded documents are listed with reasons, including inaccessible URL, out-of-date version, unsupported file type, or insufficient text extraction quality.

## Extraction

XHTML and HTML are parsed first. The loader extracts visible text, section text where headings can be mapped, and inline XBRL tag names or labels where present.

PDF extraction uses `pypdf`. If text extraction is weak, the document is excluded and the reason is recorded.

TXT is a fallback only.

## Rules

The v1 study checks 15 deterministic controls:

- Annex I, Part A, item 2: legal form.
- Annex I, Part A, item 3: registered address or head office.
- Annex I, Part A, item 4: registration date.
- Annex I, Part A, item 5: LEI or other identifier.
- Annex I, Part A, item 6: contact telephone number and email.
- Annex I, Part A, item 6: response period for investor contact.
- Annex I, Part A, item 8: management body identity and functions.
- Annex I, Part A, item 10: financial condition.
- Annex I, Part D, item 1: crypto-asset name and abbreviation.
- Annex I, Part D, item 3: persons involved in implementation of the crypto-asset project.
- Annex I, Part E, item 18: potential conflicts of interest.
- Annex I, Part F, item 2: crypto-asset characteristics and functionality.
- Article 6(5): mandatory warning statements.
- Article 6(6): management body statement.
- Article 6(7): summary.

Findings are machine-flagged potential disclosure gaps where the relevant item was not found in extracted text.

## Review Status

Committed findings default to `pending_review`. Sebastian must classify each finding before any public legal conclusion is made.
