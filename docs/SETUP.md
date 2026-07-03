# Setup & Run Guide: MiCAR Whitepaper Linter

Follow these steps to set up the white paper linter locally.

---

## Prerequisites
1. **Python (>= 3.13)**: The project uses Python 3.13 dependencies.
2. **uv**: Recommended for fast dependency synchronization.

---

## Installation

### 1. Synchronize Dependencies
Sync the python virtual environment (incorporates `docx` and `pdf` extras):
```bash
uv sync --all-extras
```
Or use pip to install the package in editable mode:
```bash
pip install -e ".[all]"
```

---

## Running the Linter

Run the tool using the CLI command `micar-lint`:

### Parse a JSON Draft
```bash
uv run micar-lint examples/incomplete.json
```

### Parse an Inline XBRL XHTML Draft
```bash
uv run micar-lint examples/sample-draft.xhtml
```

### Parse a DOCX draft
```bash
uv run micar-lint examples/sample-draft.docx
```

### Write reviewer artifacts
```bash
uv run micar-lint examples/incomplete.json \
  --audit-log reports/incomplete-audit.md \
  --remediation-output reports/incomplete-remediation.json \
  --manifest-output reports/incomplete-manifest.json
```
