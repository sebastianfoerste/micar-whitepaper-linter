# Setup & Run Guide: MiCAR Whitepaper Linter

## Try it now

- **In the browser, nothing leaves the page:** [live playground](https://sebastianfoerste.github.io/micar-whitepaper-linter/playground/) (Pyodide).
- **GitHub Action:** add `sebastianfoerste/micar-whitepaper-linter@v1` to a workflow in the repository that holds your draft. See [GitHub Action](#github-action) for the snippet and a starter repo; [DETAILS.md](DETAILS.md#github-action) lists every input.
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
Clone the repository and install the `dev` extra, which adds DOCX support and the test and lint tools (pytest, ruff); PDF support is in the base install:
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

- A JSON draft states its regime in its `type` field (a draft without one is linted as other, with no warning), and `--type` does not change it. For any other format, the linter infers the regime from English phrases (anywhere in a PDF; in a DOCX in the text of the paragraphs of its body, headings and runs marked hidden included, which holds only the runs and hyperlinks that stand directly in a paragraph, so not in a table, a text box, a header or footer, or text inside a tracked insertion, move or deletion, a content control, a smart tag, a simple field or custom XML; in Markdown and heading-layout XHTML or HTML only in section text, not in headings) ("asset-referenced", "stabilisation mechanism" or "reserve of assets" for an ART, then "e-money token", "referenced currency" or "safeguarding of funds" for an EMT, otherwise other), so a German ART or EMT draft is linted as other. A phrase does not count where a negation stands before it in the same clause, at most eight words away ("not an asset-referenced token", "neither ... nor an e-money token", "other than asset-referenced tokens", "no reserve of assets"); the negation word of a pseudo-negation ("not limited to", "not be limited to", "not restricted to", "not exhaustive", "not exclusively", "not only", "not necessarily", each also with "n't", and "without limitation") negates nothing, so it governs neither a phrase after it nor the items of a list ("The issuer holds, without limitation, a reserve of assets", and "The risks include, but are not limited to:" / "- the reserve of assets may lose value;", load as an ART); a clause also ends at a heading of a DOCX or PDF, or at the end of a section, so a heading is judged on its own words, and in a DOCX or PDF after a paragraph or line shaped like a title (at most twelve words, each other than a short connective written with a capital letter, and no sentence punctuation: "No Investor Compensation") unless it ends in a negation, and before a paragraph or line that starts a new sentence, with a capital letter or a digit or with a word that holds a capital letter ("100% of the reserve of assets …", "xStable's reserve …"). It runs on into a paragraph or line that starts otherwise, so a negation reaches a phrase in the next paragraph of a sentence split over DOCX paragraphs, and in a DOCX or PDF a negated lead-in governs each item of the list after it whose marker is a bullet, a dash, or a list number or a lower-case list letter with a bracket ("-", "•", "1)", "(a)"), also where the items end in a semicolon ("the token is not" / "- an asset-referenced token;" / "- an e-money token." loads as other from a DOCX or PDF); an item that starts a new sentence follows the lead-in only where the lead-in ends in a colon or a negation. In Markdown and heading-layout XHTML or HTML a section is one text, so a clause also ends at a colon at the end of a line, and runs on over line ends and paragraphs. A negation in other words, or more than eight words before the phrase, is not seen; the full stop after a list number or letter ("1.", "a.") ends the clause as any full stop does, so a list numbered so after a negated lead-in sets the regime in every format, as in 1.2.1, and in Markdown, XHTML or HTML so does the example list above (as an EMT: its semicolon ends the clause); in any format a line without a marker after one that ends in "; or" or "; and" (a Word list numbered by its style) is not governed, and an item that a PDF reads as a heading is judged on its own words; in a DOCX or PDF an item leads no list of its own, so the items of a list inside a negated item ("(a) the token is neither" / "(i) an asset-referenced token, nor") continue the lead-in of the outer list, and a negation that is not about the items governs them too ("There is no guarantee that:", "The following risks are not covered by any compensation scheme:" or "Holders bear these risks, with no compensation scheme:" / "- the reserve of assets may lose value;" loads as other); after such a list, where its lead-in ends in a colon or a negation, a line that starts with a bullet, a dash, or a list number or a lower-case list letter with a bracket is read as one of its items unless the loader takes it for a heading or it is shaped like a title, or the list is closed (it has two or more items, each item before the last ends in a semicolon, "; and" and "; or" included, and the last in a full stop) and the line's text after its marker is shaped like a heading (it starts with a capital letter and is a short label of at most twelve words with no full stop, semicolon, comma or exclamation mark at its end and no sentence break inside, such as "(c) Reserve of assets"), which is then judged on its own words in any font, also where the list goes on ("(a) a financial instrument;" / "(b) a deposit." / "(c) An e-money token" after a negated lead-in loads as an EMT); after a list that is not closed so, it is read as an item: with a lower-case list letter, a dash or a bullet ("(c) Reserve of Assets", "c) Reserve of Assets", "- Reserve of Assets") in a PDF whatever its font, and in a DOCX unless it has a Heading style or an outline level or, with a list letter, all its letters are set in bold; with a list number, in sentence case ("3) Reserve of assets") in a DOCX paragraph that is not a heading and in a PDF where the loader does not take it for a heading (as after the items "1)" and "2)" in the body font), and in a PDF in any case where pypdf runs it together with the line below it; in Markdown, XHTML or HTML a negation in a paragraph that ends without a mark that ends the clause reaches a phrase at most eight words after it in the next paragraphs of its section, list items included; a sentence that names a regime without calling the token one ("MiCAR distinguishes asset-referenced tokens, e-money tokens and other crypto-assets") sets it, also after a pseudo-negation ("The platform lists crypto-assets including but not limited to e-money tokens." loads as an EMT); a sentence that a PDF wraps before a capitalised word, a number or a name ("is not an" / "Asset-Referenced Token", "is not backed by" / "100% of the reserve of assets") loses its negation, a negated sentence whose wrapped first line is shaped like a title governs the next line only when it ends in a negation, and a lead-in that the loader of a DOCX or PDF takes for a heading (in a DOCX a Heading style or an outline level, or a short label set entirely in bold or with no lower-case letter) governs the lines after it only when it ends in a negation with no colon after it ("The token is not:" governs nothing, as the colon ends its clause). `--type other|art|emt` overrides it, and the numbered-field XHTML or HTML layout requires it.
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
  --audit-log /tmp/micar-incomplete-audit.md \
  --remediation-output /tmp/micar-incomplete-remediation.json \
  --manifest-output /tmp/micar-incomplete-manifest.json
```
`reports/` holds committed sample reports, so write your own outputs elsewhere. [API.md](API.md) lists every output flag, including the CI outputs (SARIF, job summary, annotations), the coverage matrix, the review table and the directory batch pack.

---

## Browser workbench (local preview)

The repository includes a browser workbench in `docs/playground/`. It runs the linter's rules client-side via Pyodide on JSON and XHTML or HTML drafts; PDF, DOCX and Markdown drafts, review bundles and CI outputs need the CLI. Nothing you paste leaves the page.

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

Findings and their citations appear in the job log. With `strict: 'true'` (the default) the job fails while BLOCKER-severity findings are open; `strict: 'false'` is report mode, which only lists them. The iXBRL format check (`COMMON.IXBRL_TAGGING`) is a BLOCKER that never passes for a loaded draft (a JSON, DOCX, PDF or Markdown draft cannot meet it, and an XHTML or HTML draft gets Review at best because tag completeness is not checked), so a strict job fails on every draft. Starter repo: [micar-whitepaper-template](https://github.com/sebastianfoerste/micar-whitepaper-template), which ships this step for its `whitepaper.json` in report mode; set `strict` to `'true'` in its `.github/workflows/micar-lint.yml` to fail on open BLOCKERs. Details in [docs/DETAILS.md](DETAILS.md#github-action).
