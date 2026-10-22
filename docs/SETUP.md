# Setup & Run Guide: MiCAR Whitepaper Linter

Follow these steps to set up the white paper linter locally.

---

## Prerequisites
1. **Python (>= 3.13)**: The project uses Python 3.13 dependencies.
2. **uv**: Recommended for fast dependency synchronization.

---

## Installation

### From PyPI
The package is published on PyPI as [`micar-whitepaper-linter`](https://pypi.org/project/micar-whitepaper-linter/). It installs the `micar-lint` command, also available as `micar-whitepaper-linter`:
```bash
pip install micar-whitepaper-linter
micar-lint your-draft.json
```
Add the `docx` extra to read DOCX drafts:
```bash
pip install 'micar-whitepaper-linter[docx]'
```
Or run it without installing, using uv:
```bash
uvx micar-whitepaper-linter your-draft.json
uvx --python 3.13 --from 'micar-whitepaper-linter[docx]' micar-lint your-draft.docx
```

### From source
Sync the python virtual environment (incorporates `docx` and `pdf` extras):
```bash
uv sync --all-extras
```
Or use pip to install the package in editable mode:
```bash
pip install -e ".[all]"
```
To try unreleased changes from `main` without a clone:
```bash
uvx --from git+https://github.com/sebastianfoerste/micar-whitepaper-linter micar-lint your-draft.json
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
