# Testing & Verification: MiCAR Whitepaper Linter

The testing suite verifies rules logic, document parsers, and CLI options.

The full `make check` gate also requires Node.js 22 or later for the browser's dependency-free JavaScript tests. Run `make playground-check` for those checks alone. The Python bridge tests compare browser JSON/text payloads with CLI output for all bundled examples, retain the review gates, and verify draft cleanup after failure.

The playground examples are generated from `examples/`. After changing a canonical example, run `make playground-samples`; the Python suite rejects stale bundled examples. The prebuilt Python wheel has a separate source-parity test.

For browser checks, serve `docs/` over HTTP and open `/playground/`. Exercise each example, search and status filters, section navigation, malformed JSON, edits during/after a run, import and export, and runtime failure/retry. Check both the two-column desktop view and the stacked mobile view. Use synthetic data only.

---

## Testing Tools

1. **Unit Tests**: Powered by `pytest` (configured in [pyproject.toml](file:///Users/sebastian/Developer/micar-whitepaper-linter/pyproject.toml)).
2. **Formatting & Linting**: Handled by `ruff`.

---

## How to Run Tests

### 0. Run The Local Proof Gate
Runs lint, tests, and a JSON CLI smoke check against the ART example:
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
uv run --extra dev ruff check src tests
```

---

## Key Test Areas
- **German Language Rules**: Validated in `tests/test_german.py`.
- **iXBRL XHTML Parsing**: Validated in `tests/test_ixbrl.py`.
- **Regime Rules**: Validated in `tests/test_rules.py` (verifies checks for Annex I, II, and III).
- **ART Reserve Floor**: Validated in `tests/test_reserve_rules.py` across draft characterisation combinations, malformed values, percentage formats, misleading contexts and the invariant that the rule never returns `PASS`.
- **Format Parsers**: Validated in `tests/test_markdown.py` and `tests/test_document.py` (DOCX, Markdown).
- **Reviewer Artifacts**: Validated in `tests/test_artifact_manifest.py`, `tests/test_remediation.py`, and CLI tests for manifest, remediation, audit-log, and write-failure behavior.
