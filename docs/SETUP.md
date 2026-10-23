# Setup & Run Guide: MiCAR Whitepaper Linter

## Try it now

- **In the browser, nothing leaves the page:** [live playground](https://sebastianfoerste.github.io/micar-whitepaper-linter/playground/) (Pyodide).
- **GitHub Action:** add `sebastianfoerste/micar-whitepaper-linter@v1` to a workflow in the repository that holds your draft. Findings and their citations appear in the job log, and by default (`strict: 'true'`) the job fails while BLOCKER-severity findings are open. See [GitHub Action](#github-action) for the snippet and inputs, or start from the [micar-whitepaper-template](https://github.com/sebastianfoerste/micar-whitepaper-template) repo, which ships the workflow preconfigured.
- **Local CLI:** follow the [Quick start](#quick-start) below. The core linter runs locally and does not require external LLM or network processing.

---

## Quick start

Follow these steps to set up the white paper linter locally.

### Prerequisites
1. **Python (>= 3.13)**: The project uses Python 3.13 dependencies.
2. **[uv](https://docs.astral.sh/uv/)**: Recommended for fast dependency synchronization. The `uvx` commands and the clone route need it.
3. **make**: The clone route uses it for `make install` and `make demo`.

### From PyPI
The package is published on PyPI as [`micar-whitepaper-linter`](https://pypi.org/project/micar-whitepaper-linter/) (Python 3.13+). One command, no install (needs uv):
```bash
uvx micar-whitepaper-linter your-draft.json
```
Or install the `micar-lint` command, also available as `micar-whitepaper-linter`:
```bash
pip install micar-whitepaper-linter
micar-lint your-draft.json
```
DOCX drafts need the `docx` extra. Add it to the pip install:
```bash
pip install 'micar-whitepaper-linter[docx]'
```
Or run it without installing, using uv:
```bash
uvx --python 3.13 --from 'micar-whitepaper-linter[docx]' micar-lint your-draft.docx
```

### From source
**From a clone** of this repository (requires Python 3.13+, uv and make):
```bash
make install   # uv sync --extra dev
make demo      # lint examples/incomplete.json, a synthetic ART draft with open blockers
uv run micar-lint examples/incomplete.json --review-bundle-dir /tmp/micar-incomplete-review-bundle
```
The last command also writes a review bundle to `/tmp/micar-incomplete-review-bundle`: compliance and remediation checklists, a coverage matrix, a review table, a reviewer sign-off record and an artifact manifest.

Without make, sync the python virtual environment with every extra (incorporates `docx` and `pdf` extras):
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

### Check your own draft
To check your own draft, pass its path to `uv run micar-lint` instead of an example file:

- A JSON draft states its regime in its `type` field. For an XHTML or DOCX draft, add `--type other|art|emt`; the numbered-field XHTML layout requires it.
- `--strict` exits with status 1 while any BLOCKER finding is open.
- `--json` prints machine-readable JSON instead of text.

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

---

## Browser workbench (local preview)

The repository includes a browser workbench in `docs/playground/`. The full linter runs client-side via Pyodide. Nothing you paste leaves the page.

For local preview, run `python3 -m http.server 8765 --bind 127.0.0.1 --directory docs` and open `http://127.0.0.1:8765/playground/`. The first runtime load needs an internet connection. The app does not persist drafts in browser storage.

Details in [docs/DETAILS.md](DETAILS.md#browser-workbench).

---

## GitHub Action

```yaml
- uses: actions/checkout@v4
- uses: sebastianfoerste/micar-whitepaper-linter@v1
  with:
    whitepaper: drafts/whitepaper.json
    strict: 'true'
```

The job fails while BLOCKER findings are open. Starter repo with this preconfigured: [micar-whitepaper-template](https://github.com/sebastianfoerste/micar-whitepaper-template). Details in [docs/DETAILS.md](DETAILS.md#github-action).
