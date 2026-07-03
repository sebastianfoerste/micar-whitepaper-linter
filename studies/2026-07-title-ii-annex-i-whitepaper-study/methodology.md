# Methodology

## Scope

The study covers MiCAR Title II white papers for crypto-assets other than asset-referenced tokens and e-money tokens. It maps the v1 checks to MiCAR Article 6 and Annex I.

ART and EMT white papers are out of scope because they require Annex II and Annex III logic.

## Source Basis

The study uses ESMA's interim MiCA register source data for Title II white papers and a local source pack of 20 candidate entries. Raw white-paper files are downloaded locally into `.study-cache/` and are not committed.

Each source row is normalized into `source-manifest.json` and receives a SHA-256 hash over the canonical normalized row.

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

- Legal form.
- Registered address or head office.
- Registration date.
- LEI or other identifier.
- Contact telephone number and email.
- Response period for investor contact.
- Management body identity and functions.
- Conflicts of interest.
- Financial condition.
- Crypto-asset name and abbreviation.
- Persons involved in design and development.
- Utility and characteristics.
- Mandatory warning statements.
- Management body statement.
- Summary.

Findings are machine-flagged potential disclosure gaps where the relevant item was not found in extracted text.

## Review Status

Committed findings default to `pending_review`. Sebastian must classify each finding before any public legal conclusion is made.
