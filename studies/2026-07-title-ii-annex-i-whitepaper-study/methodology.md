# Methodology

## Research question

The v1 pilot asks whether deterministic, source-cited checks can produce reviewable candidate flags for selected MiCAR Article 6 and Annex I disclosures.

It does not estimate the prevalence of legally deficient white papers and does not assess issuer compliance.

## Scope and legal basis

The study covers Title II white papers for crypto-assets other than asset-referenced tokens and e-money tokens. It applies 15 controls drawn from MiCAR Article 6 and Annex I.

ART and EMT white papers require different Annex logic and are outside scope. The study also does not test full Inline XBRL conformance under Commission Implementing Regulation (EU) 2024/2984.

## Source basis and provenance

The candidate documents originate from public MiCAR register data. The committed v1 run used a curated 20-entry candidate manifest. Before any reviewed publication, each included entry must be reconciled against ESMA's official Title II CSV:

`https://www.esma.europa.eu/sites/default/files/2024-12/OTHER.csv`

The repository records two different hashes and does not treat them as interchangeable:

- `register_row_hash_sha256`: SHA-256 over the canonical normalized register row.
- `document_sha256`: SHA-256 over the exact source bytes processed by the detector.

Document hashes and extraction metadata are collected in `document-provenance.json`. Raw white-paper files remain outside Git in `.study-cache/`.

WP identifiers are pseudonymous labels. Because the source manifest contains public issuer names and URLs, the dataset is not anonymous.

## Sampling

The committed v1 run uses the first ten eligible candidates from the curated source pack. `WP-006` and `WP-008` were excluded because the source files were unavailable in the local cache; `WP-011` and `WP-012` backfilled the sample.

Eligibility criteria:

1. Title II scope.
2. A public white-paper URL.
3. Not marked as out of date or superseded.
4. Parseable XHTML, HTML, PDF, or text with acceptable extraction quality.

This is a convenience sample. It is not random, issuer-deduplicated, stratified, or statistically representative. It includes repeated issuers. No prevalence estimate may be derived from it.

The code supports seeded random selection using seed `20260702`, but a random draw from a curated 20-entry pack would still not be population-representative.

## Extraction

XHTML and HTML processing extracts visible text, mapped sections where available, and Inline XBRL tag names or labels. PDF extraction uses `pypdf`. Plain text is a fallback.

A source is excluded where text extraction is insufficient for meaningful detector operation. Extraction failure is distinct from substantive absence of a disclosure.

## Detector rules

The v1 detector checks:

- legal form;
- registered address or head office;
- registration date;
- LEI or another identifier;
- telephone number and email;
- investor-contact response period;
- management-body identity and functions;
- conflicts of interest;
- financial condition;
- crypto-asset name and abbreviation;
- persons involved in design and development;
- utility and characteristics;
- mandatory warnings;
- management-body statement;
- summary.

A `flagged` cell means that the configured text or tag patterns did not find the specified element. A `not_flagged` cell means only that the detector found a matching pattern. Neither status is a legal conclusion.

## Human validation

The unit of validation is one document-rule cell. Ten documents multiplied by 15 rules yields 150 cells in `human-review-matrix.csv`.

Reviewers inspect the source document independently of the detector outcome and apply one final label:

- `present`;
- `missing`;
- `uncertain`;
- `extraction_failure`;
- `not_applicable`;
- `pending`.

Every `present` or `missing` label requires a source pinpoint or explanatory note. All detector flags, all uncertain rows, and a sample of non-flagged rows should receive a second review. Disagreements are adjudicated before the final `human_label` is entered.

The full protocol is in `review-protocol.md`.

## Metrics and publication gate

For evaluable labels:

- true positive: detector flagged, human label missing;
- false positive: detector flagged, human label present;
- false negative: detector did not flag, human label missing;
- true negative: detector did not flag, human label present.

Precision, recall, and F1 exclude uncertain, extraction-failure, not-applicable, and pending rows. No metric is publication-ready while any row remains pending.

`micar-review-summary --require-complete` exits with status 2 until the matrix is complete.

## Next population study

A prevalence study should use at least the following safeguards:

1. draw from a dated official ESMA register snapshot;
2. deduplicate by issuer and closely related white-paper family;
3. stratify by home Member State and actual fetched document format;
4. publish the random seed and inclusion flow;
5. preserve document and extraction hashes;
6. complete double review and adjudication before reporting legal findings;
7. report confidence intervals and cluster repeated issuers where relevant.

The committed v1 pilot does not satisfy those conditions and must not be described as a population study.
