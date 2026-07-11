# Human-review protocol

## Objective

Create a defensible reference label for every document-rule cell without converting detector output into a legal conclusion by default.

## Materials

Reviewers work in `human-review-blinded.csv`. Detector outcomes are merged into `human-review-matrix.csv` only after the independent labels are recorded.

Reviewers receive:

- the exact source document identified by `document_sha256`;
- the applicable Article 6 or Annex I requirement;
- the rule label and missing-element description;
- a blinded review sheet that does not reveal `detector_status` or detector confidence.

The source URL and issuer mapping remain in `source-manifest.json`. Reviewers verify that the source bytes match `document-provenance.json`.

## Labels

Use exactly one final label:

| Label | Meaning |
| --- | --- |
| `present` | The required element is present in the reviewed source, with a recorded pinpoint. |
| `missing` | The reviewer inspected the relevant source and did not find the required element. |
| `uncertain` | The legal requirement, source wording, or factual application is genuinely ambiguous. |
| `extraction_failure` | The source may contain the element, but the available rendering or extraction cannot support a reliable decision. |
| `not_applicable` | The reviewer concludes that the control does not apply to this document and records why. |
| `pending` | Review has not been completed. |

A blank label is treated as `pending`.

## First review

For each cell:

1. Confirm the document hash.
2. Read the relevant source section and surrounding context.
3. Apply the rule to the source, without looking at the detector status.
4. Enter the label.
5. For `present` or `missing`, record a page, section, Inline XBRL fact, or other stable pinpoint.
6. Record the reviewer identifier and ISO 8601 review date.
7. Explain uncertainty, extraction failure, or non-applicability in `review_note`.

## Second review and adjudication

A second qualified reviewer independently assesses:

- every detector-flagged cell;
- every `uncertain`, `extraction_failure`, or `not_applicable` cell;
- at least 20% of randomly selected non-flagged cells.

The two reviews are compared only after both are complete. Any disagreement is adjudicated by a qualified reviewer who records the final `human_label` and reasoning. If no second reviewer is available, the report must state that the labels are single-reviewed.

## Metric calculation

Only final `present` and `missing` labels enter the confusion matrix:

| Detector | Human label | Classification |
| --- | --- | --- |
| flagged | missing | true positive |
| flagged | present | false positive |
| not_flagged | missing | false negative |
| not_flagged | present | true negative |

`uncertain`, `extraction_failure`, `not_applicable`, and `pending` are counted and excluded from precision, recall, and F1.

Run:

```bash
uv run micar-review-summary \
  --matrix studies/2026-07-title-ii-annex-i-whitepaper-study/human-review-matrix.csv \
  --out studies/2026-07-title-ii-annex-i-whitepaper-study/human-review-summary.json \
  --require-complete
```

## Publication gate

No reviewed legal finding or detector-performance claim may be published unless:

1. every matrix row has a non-pending final label;
2. every present or missing label has a source pinpoint or explanation;
3. disagreements have been adjudicated;
4. the summary command exits successfully;
5. the report states the sampling and extraction limitations;
6. any statement about a named issuer receives a separate qualified legal review.

Completing the gate supports reporting detector validation on this sample. It does not make the sample representative of the ESMA register.
