# Setup & Run Guide: MiCAR Whitepaper Linter

## Try it now

- **In the browser, nothing leaves the page:** [live playground](https://sebastianfoerste.github.io/micar-whitepaper-linter/playground/) (Pyodide).
- **GitHub Action:** add `sebastianfoerste/micar-whitepaper-linter@v1` to a workflow in the repository that holds your draft. See [GitHub Action](#github-action) for the snippet, its inputs and a starter repo.
- **Local CLI:** follow the [Quick start](#quick-start) below. The core linter runs locally and does not require external LLM or network processing.

---

## Quick start

Follow these steps to set up the white paper linter locally.

### Prerequisites
1. **Python (>= 3.13)**: The project uses Python 3.13 dependencies.
2. **[uv](https://docs.astral.sh/uv/)**: Recommended for fast dependency synchronization, and needed for every `uvx`, `uv run` and `make` command on this page. The pip commands work without it.
3. **make** (optional): The clone route uses it for `make install` and `make demo`; each has a no-make command below.

### From PyPI
The package is published on PyPI as [`micar-whitepaper-linter`](https://pypi.org/project/micar-whitepaper-linter/). One command, no install (needs uv):
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
To try unreleased changes from `main` without a clone:
```bash
uvx --from git+https://github.com/sebastianfoerste/micar-whitepaper-linter micar-lint your-draft.json
```

### From source
Clone the repository and install the `dev` extra, which includes DOCX and PDF support:
```bash
git clone https://github.com/sebastianfoerste/micar-whitepaper-linter.git && cd micar-whitepaper-linter
make install   # uv sync --extra dev
```
Without make:
```bash
uv sync --extra dev
```
Or sync the python virtual environment with all extras (`docx`, `pdf` and `dev`):
```bash
uv sync --all-extras
```
Or use pip to install the package in editable mode, with the `docx` and `pdf` extras:
```bash
pip install -e ".[all]"
```
Then lint the demo draft:
```bash
make demo      # lint examples/incomplete.json, a synthetic ART draft with open blockers
```
Without make, the [Parse a JSON Draft](#parse-a-json-draft) command below prints the same report.

### Running the Linter

Run the tool using the CLI command `micar-lint`. To check your own draft, pass its path to the command for your install route:

- after `pip install`: `micar-lint <path>`
- without installing: `uvx micar-whitepaper-linter <path>`
- from a clone: `uv run micar-lint <path>`

On the first two routes, DOCX needs the `docx` extra ([From PyPI](#from-pypi)).

- A JSON draft states its regime in its `type` field, and `--type` does not change it. For any other format, the linter infers the regime from the text and `--type other|art|emt` overrides it; the numbered-field XHTML or HTML layout requires it.
- `--strict` exits with status 1 while any BLOCKER finding is open. For a directory, it also exits 1 when a file could not be linted or no file was linted.
- `--json` prints machine-readable JSON instead of text.

The examples below lint the sample drafts in `examples/` from a clone.

#### Parse a JSON Draft
```bash
uv run micar-lint examples/incomplete.json
```

#### Parse an Inline XBRL XHTML Draft
```bash
uv run micar-lint examples/sample-draft.xhtml
```

#### Parse a DOCX draft
```bash
uv run micar-lint examples/sample-draft.docx
```

#### Write reviewer artifacts
```bash
uv run micar-lint examples/incomplete.json --review-bundle-dir /tmp/micar-incomplete-review-bundle
```
This also writes a review bundle to `/tmp/micar-incomplete-review-bundle`: compliance and remediation checklists, a coverage matrix, a review table, a reviewer sign-off record and an artifact manifest. Or write single artifacts:
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

Findings and their citations appear in the job log. With `strict: 'true'` (the default) the job fails while BLOCKER-severity findings are open; `strict: 'false'` is report mode, which only lists them. Starter repo: [micar-whitepaper-template](https://github.com/sebastianfoerste/micar-whitepaper-template), which ships this step for its `whitepaper.json` in report mode; set `strict` to `'true'` in its `.github/workflows/micar-lint.yml` to fail on open BLOCKERs. Details in [docs/DETAILS.md](DETAILS.md#github-action).
