# Limitations and prohibited inferences

This is a deterministic first-pass pilot over extracted public text. It does not provide legal advice and does not determine whether any white paper complies with MiCAR.

## Sampling

The sample contains ten processed documents selected by convenience from a curated 20-entry source pack. It is not random, issuer-deduplicated, stratified, or representative. Several documents share an issuer. The observed flag counts cannot be extrapolated to the ESMA register.

## Source provenance

The v1 source pack must be reconciled against a dated official ESMA Title II CSV before any reviewed publication. A register-row hash identifies normalized metadata; it is not a hash of the white-paper document. Exact processed-byte hashes are recorded separately in `document-provenance.json`.

Raw source files are not committed. Remote sources may change or disappear, which limits later reproduction unless the same bytes can be obtained lawfully.

## Extraction

A disclosure may be present in the source but absent from extracted text. Rendered HTML, scanned PDFs, unusual character encodings, tables, and Inline XBRL markup can affect extraction. Extraction failure must not be classified as substantive absence.

## Rule coverage

The detector checks 15 selected Article 6 and Annex I controls. It does not check every Annex I item, semantic completeness, internal consistency, fair-clear-not-misleading presentation, all language requirements, or every applicable exemption.

ART and EMT white papers are outside scope.

## Detector validity

Pattern confidence is not legal confidence. A high-confidence detector flag means that configured context was found while the required pattern was not. It does not mean that a qualified reviewer has confirmed a legal omission.

All 150 document-rule cells remain pending human validation. Precision, recall, false-positive, and false-negative rates are currently unknown.

## Identifiability

WP identifiers are pseudonymous labels, not anonymisation. The public source manifest maps each identifier to issuer names and public URLs. This is intentional for source traceability and must be stated whenever results are shared.

## Publication boundary

Until the human-review matrix is complete and adjudicated, the following claims are prohibited:

- that a named issuer omitted a legally required disclosure;
- that a white paper is unlawful, deficient, or non-compliant;
- that the detector has a measured accuracy rate;
- that the flag frequency represents the wider MiCAR register;
- that notification implies regulatory approval.

ESMA states that registered white papers have not been reviewed or approved by a competent authority. Detector output does not change that status and is not a substitute for legal review.
