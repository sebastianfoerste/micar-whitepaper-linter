# Testing & Verification: MiCAR Whitepaper Linter

The testing suite verifies rules logic, document parsers, and CLI options.

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
- **Format Parsers**: Validated in `tests/test_markdown.py` and `tests/test_document.py` (DOCX, Markdown).
- **Reviewer Artifacts**: Validated in `tests/test_artifact_manifest.py`, `tests/test_remediation.py`, and CLI tests for manifest, remediation, audit-log, and write-failure behavior.
