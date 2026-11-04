# Testing & Verification: MiCAR Whitepaper Linter

The testing suite verifies rules logic, document parsers, and CLI options.

Develop with `make check` (ruff, pytest, CLI smoke, review bundle, playground and template checks).

The full `make check` gate also requires Node.js 22 or later for the browser's dependency-free JavaScript tests. Run `make playground-check` for those checks alone. The Python bridge tests compare browser JSON/text payloads with CLI output for all bundled examples, retain the review gates, and verify draft cleanup after failure.

The playground examples are generated from `examples/`. After changing a canonical example, run `make playground-samples`; the Python suite rejects stale bundled examples. The prebuilt Python wheel has a separate source-parity test. The sample reports in `reports/` and the CLI output in `docs/sample-review-bundle.md` are real CLI output in the default English citation style: after changing report text, a rule, `examples/art-stablecoin.json` or `examples/incomplete.json`, run `make sample-reports`; the Python suite rejects stale copies. No script regenerates the example output blocks in `README.md` and `docs/DETAILS.md`: after a report change, update them by hand; `tests/test_readme.py` rejects a block that is not the start of the real CLI output. The README screenshot is captured from the CLI: after changing report text, `examples/incomplete.json` or `scripts/render_demo.py`, run `make demo-image`, which needs headless Chrome or Chromium (`make demo-image CHROME=/path/to/chromium`), and commit `docs/demo.txt` and `docs/demo.png`.

For browser checks, serve `docs/` over HTTP and open `/playground/`. Exercise each example, search and status filters, section navigation, malformed JSON, edits during/after a run, import and export, and runtime failure/retry. Check both the two-column desktop view and the stacked mobile view. Use synthetic data only.

---

## Testing Tools

1. **Unit Tests**: Powered by `pytest` (configured in [pyproject.toml](../pyproject.toml)).
2. **Formatting & Linting**: Handled by `ruff`.

---

## How to Run Tests

### 0. Run The Local Proof Gate
Runs ruff, pytest, a JSON CLI smoke check against the ART example, and the review bundle, playground and template checks:
```bash
make check
```

### 1. Run Python Test Suite
Runs the complete pytest suite:
```bash
uv run --extra dev pytest
```

### 2. Run Formatting Checks
```bash
uv run --extra dev ruff check src tests scripts
```

---

## Key Test Areas
- **German Language Rules**: Validated in `tests/test_german.py`.
- **iXBRL XHTML Parsing**: Validated in `tests/test_ixbrl.py`.
- **Regime Rules**: Validated in `tests/test_rules.py` (verifies checks for Annex I, II, and III).
- **ART Reserve Floor**: Validated in `tests/test_reserve_rules.py` across draft characterisation combinations, malformed values, percentage formats, misleading contexts and the invariant that the rule never returns `PASS`.
- **Format Parsers**: Validated in `tests/test_markdown.py` and `tests/test_document.py` (DOCX, Markdown). `tests/test_heading_detection.py` builds DOCX files with python-docx and PDF files that pypdf parses, in plain, bold and larger type (14 pt bold headings, one or several pages, laid out with Td or T*), and Markdown and heading-layout XHTML drafts, and checks section keys and BLOCKER statuses: body text mentioning a section word opens no section; list items, wrapped lines and lead-ins stay in their section; a line rejected as a heading ends the section before it; a heading that wraps onto two lines in its heading font is one heading, while two headings a paragraph apart stay two, and so does a short heading one line spacing above the next heading or above a bold paragraph in a draft with no space between paragraphs; a short heading over a lower-case line in its font stays a heading; a heading font wins over a following lower-case list item; marked part titles of up to 20 words without the part letter are headings; the part titles, the plural Part F title and the numbered fields of the Implementing Regulation template are headings; a heading that names no section ends the section before it while a sub-heading does not, such as a smaller heading, a bold label under a bold heading, a heading numbered below the heading that opened the section ("12.1" under "12.") or one that names a single risk ("Market risk"); German headings that name the date of notification or the redemption ("Datum der Mitteilung", "Rücktausch") open their sections; a heading that names a risk and the redemption ("Redemption risk", "Rücktauschrisiko") stays with the risks, and a redemption heading below the rights heading, a redemption field of the template's Part D among them, keeps the rights section open; a cover title that names a section sets no heading level for the headings after it; summary table rows keep their answer, and the "Compliance statement" field opens the management statement; a running page header and a body-font line in a draft with a heading font open no section; heading text is not section body; in a DOCX or PDF the regime is read from headings and from text in no section (in a DOCX only from the runs and hyperlinks that stand directly in the paragraphs of its body, so not from a table, a header or footer, or text inside a tracked insertion or move, a content control, a smart tag or a simple field), in Markdown and XHTML only from section text (also from the text after the first-page statement in the line where it ends in Markdown, not the next line of its paragraph, and in the paragraph where it ends in XHTML and HTML), and not from a negated phrase such as "not an asset-referenced token" (a pseudo-negation such as "not limited to", "without limitation", "not only" or "not necessarily" negates no phrase after it and governs no list item in any format, while a negation beside it still negates), and a negation at the end of the paragraph or section before a heading does not reach the heading, while one in a DOCX or PDF paragraph reaches the next paragraph or line when that continues its sentence (it starts in lower case, or is a list item after a negated lead-in) and not when it starts a new sentence with a capital letter, a digit or a name with a capital letter, or follows a line shaped like a title; in a DOCX or PDF a negated lead-in governs the items of a dash, bullet or bracket list after it, and a sentence after the list that names the regime, or a numbered heading after it, still sets the regime, as does a line shaped like a heading in any font after a list whose items end in a semicolon and whose last item ends in a full stop, while the lead-in still governs the items of a list that goes on (items without a semicolon, an inner list that a full stop closes, a lower-case item or a sentence after the closing item, a list after a new lead-in); the documented limits of the regime reading keep the results that the CHANGELOG and `docs/SETUP.md` state, and a phrase that a line end splits inside one paragraph is found only in XHTML and HTML, with or without a space or line end beside the `<br>`; a long word, a long list and long lists that a full stop closes are read in linear time, a long Markdown list in little memory, and a regime that `--type` gives is not inferred; and DOCX styles that loop or are based on a numbering style load. `tests/test_document_loader.py` checks that study runs use the shape rule of `micar-lint` without font information.
- **LEI Rules**: Validated in `tests/test_lei.py`: check digits, malformed codes next to a valid one, codes that a loader leaves out of the sections, linear-time reading, and documented limits of the reading, among them hidden text: a DOCX run marked hidden; text moved away or a `w:t` inside a tracked deletion, with the code in a body paragraph (Review) or in a table cell, a header, a label paragraph or a tracked insertion (Pass), and deleted text as Word writes it (`w:delText`), which is not read; PDF text in render mode 3 or 7 or white on white; and XHTML and HTML text that CSS or the `hidden` attribute hides, which completes a code, splits it, or in a block of its own leaves it malformed. These keep those cases in step with ADR 0007 and the rule page; the other places the limits name, such as a content control, a field result, a smart tag, a text box or a section the regime drops, are not tested.
- **Placeholders**: Validated in `tests/test_placeholders.py` ("TBD", "TBA", "[●]", "[...]", "[insert date]", "XX", "to be confirmed", "noch offen" and the other markers as a whole section, numbered field or part with "N/A" read as missing; short real answers such as "TBC Freight Lines" do not).
- **Proof Contract**: `tests/test_proof_contract.py` checks that `contracts/micar-whitepaper-linter.proof.v1.json` carries the `micar-whitepaper-linter.proof.v1` schema identifier, names exactly the console scripts in `pyproject.toml` plus `action.yml`, gives `make check` as its verification command and that test as its `contractTest`, and that its output schema occurs in the source. Its other fields are not checked.
- **Reviewer Artifacts**: Validated in `tests/test_artifact_manifest.py`, `tests/test_remediation.py`, and CLI tests for manifest, remediation, audit-log, and write-failure behavior.
