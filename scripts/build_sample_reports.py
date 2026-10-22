"""Write the sample text reports in reports/ and the CLI output block of docs/sample-review-bundle.md.

Each is the real stdout of `micar-lint <example>` in the default (English) citation style. Run with
`make sample-reports` or `uv run python scripts/build_sample_reports.py` after changing report text, a
rule or one of the examples below; tests/test_sample_reports.py fails while a committed copy is stale.
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = {
    "reports/sample-art-pass.txt": "examples/art-stablecoin.json",
    "reports/sample-incomplete-blockers.txt": "examples/incomplete.json",
}
BUNDLE_DOC = "docs/sample-review-bundle.md"
BUNDLE_EXAMPLE = "examples/art-stablecoin.json"
# The fenced block under "## CLI Linter Output" holds the full report, uncut. Its opening fence may carry
# an info string (```text). Neither the intro nor the block may run past a heading or another fence, so a
# fence this does not recognise raises instead of matching a later block and rewriting the next sections.
_NO_HEADING_OR_FENCE = r"(?:(?!^#|^```).)*"
CLI_BLOCK = re.compile(
    rf"^## CLI Linter Output\n{_NO_HEADING_OR_FENCE}^```[^\n]*\n({_NO_HEADING_OR_FENCE})^```[ \t]*$",
    re.M | re.S,
)
REPORT_START = "MiCAR Whitepaper Linter - "
TIMEOUT_S = 120


def cli_output(example: str) -> str:
    """Stdout of the CLI on a synthetic draft; `-m micar_linter` is the `micar-lint` entry point."""
    result = subprocess.run(
        [sys.executable, "-m", "micar_linter", example],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=TIMEOUT_S,
    )
    if result.returncode != 0:
        raise RuntimeError(f"micar-lint {example} exited with status {result.returncode}:\n{result.stderr}")
    return result.stdout


def build_reports() -> dict[str, str]:
    return {path: cli_output(example) for path, example in REPORTS.items()}


def splice_cli_block(doc: str, output: str) -> str:
    """`doc` with the report in its fenced block under '## CLI Linter Output' replaced by `output`."""
    block = CLI_BLOCK.search(doc)
    if not block:
        raise RuntimeError(f"{BUNDLE_DOC} has no fenced block under '## CLI Linter Output'")
    if not block.group(1).startswith(REPORT_START):
        raise RuntimeError(f"the '## CLI Linter Output' block in {BUNDLE_DOC} does not start with a report")
    return doc[: block.start(1)] + output + doc[block.end(1) :]


def build_bundle_doc() -> str:
    doc = (ROOT / BUNDLE_DOC).read_text(encoding="utf-8")
    return splice_cli_block(doc, cli_output(BUNDLE_EXAMPLE))


if __name__ == "__main__":
    # Build all three texts before writing, so a failure leaves every file as it was.
    texts = {**build_reports(), BUNDLE_DOC: build_bundle_doc()}
    for path, text in texts.items():
        (ROOT / path).write_text(text, encoding="utf-8")
