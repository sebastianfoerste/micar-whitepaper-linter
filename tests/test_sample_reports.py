"""The sample reports are real CLI output; nothing regenerates them automatically, so a report or rule
change can silently leave them showing old text or the old citation style. Regenerating them must replace
only the report block of docs/sample-review-bundle.md, never the sections after it."""

import runpy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RERUN = "run `make sample-reports` and commit the result"
OLD_REPORT = "MiCAR Whitepaper Linter - Old\nPass: 1\n"
NEW_REPORT = "MiCAR Whitepaper Linter - New\nPass: 2\n"
# docs/sample-review-bundle.md in miniature: the report block, then sections that must survive the rewrite.
DOC = """## CLI Linter Output

Intro.

{fence}
{report}```

---

## Compliance Coverage Statistics

- **Total Checked Rules**: 18

## Validation and Execution

```
make check
```

```bash
make demo
```
"""


@pytest.fixture(scope="module")
def builder():
    return runpy.run_path(str(ROOT / "scripts/build_sample_reports.py"))


def test_sample_reports_match_current_cli_output(builder):
    for path, expected in builder["build_reports"]().items():
        assert (ROOT / path).read_text(encoding="utf-8") == expected, f"{path} is stale; {RERUN}"


def test_sample_review_bundle_doc_shows_current_cli_output(builder):
    doc = builder["BUNDLE_DOC"]
    assert (ROOT / doc).read_text(encoding="utf-8") == builder["build_bundle_doc"](), (
        f"{doc} is stale; {RERUN}"
    )


@pytest.mark.parametrize("fence", ["```", "```text"])
def test_bundle_doc_rewrite_replaces_only_the_report(builder, fence):
    doc = DOC.format(fence=fence, report=OLD_REPORT)
    assert builder["splice_cli_block"](doc, NEW_REPORT) == DOC.format(fence=fence, report=NEW_REPORT)


@pytest.mark.parametrize(
    ("old", "new"),
    [
        (f"```\n{OLD_REPORT}```\n", f"~~~\n{OLD_REPORT}~~~\n"),
        (f"{OLD_REPORT}```\n", OLD_REPORT),
        (OLD_REPORT, "Pass: 1\n"),
        ("## CLI Linter Output", "## CLI Output"),
    ],
    ids=["tilde-fence", "unclosed-fence", "not-a-report", "no-heading"],
)
def test_bundle_doc_rewrite_refuses_a_block_it_cannot_find(builder, old, new):
    doc = DOC.format(fence="```", report=OLD_REPORT)
    assert doc.count(old) == 1
    with pytest.raises(RuntimeError):
        builder["splice_cli_block"](doc.replace(old, new), NEW_REPORT)
