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
# The fenced block under "## CLI Linter Output" holds the full report, uncut.
CLI_BLOCK = re.compile(r"^## CLI Linter Output\n.*?^```\n(.*?)^```$", re.M | re.S)
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


def build_bundle_doc() -> str:
    doc = (ROOT / BUNDLE_DOC).read_text(encoding="utf-8")
    block = CLI_BLOCK.search(doc)
    if not block:
        raise RuntimeError(f"{BUNDLE_DOC} has no fenced block under '## CLI Linter Output'")
    return doc[: block.start(1)] + cli_output(BUNDLE_EXAMPLE) + doc[block.end(1) :]


if __name__ == "__main__":
    for path, text in build_reports().items():
        (ROOT / path).write_text(text, encoding="utf-8")
    (ROOT / BUNDLE_DOC).write_text(build_bundle_doc(), encoding="utf-8")
