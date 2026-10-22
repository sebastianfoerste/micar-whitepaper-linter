"""The README is the PyPI description and the first thing a reviewer reads; keep its sample honest."""

import re
from pathlib import Path

from micar_linter.cli import main

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
CUT = "..."
NUMBER_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}


def _example_block(readme: str) -> list[str]:
    section = readme.split("## Example output", 1)[1]
    block = re.search(r"```text\n(.*?)\n```", section, re.S)
    assert block, "README Example output section has no ```text block"
    return block.group(1).splitlines()


def test_readme_example_output_is_the_start_of_the_real_cli_output(capsys):
    readme = README.read_text(encoding="utf-8")
    shown = _example_block(readme)
    assert main([str(ROOT / "examples/incomplete.json")]) == 0
    real = capsys.readouterr().out.splitlines()

    # The block may end with a single `...` line marking the cut; every line before it is verbatim output.
    if shown[-1] == CUT:
        shown = shown[:-1]
        assert len(shown) < len(real), "README marks a cut but shows the whole output"
    assert real[: len(shown)] == shown, "README example output is not the first lines of the real CLI output"

    findings = [line for line in shown if line.startswith("[")]
    assert f"first {NUMBER_WORDS[len(findings)]} findings only" in readme, (
        f"README shows {len(findings)} findings but labels them differently"
    )
