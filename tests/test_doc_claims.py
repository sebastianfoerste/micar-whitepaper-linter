"""Public descriptions of the linter claim no more than the rules do.

Half of the rule citations stop at an Annex Part, and every rule checks listed terms, patterns and a minimum
length, a calendar date, a language name, LEI check digits or a file format; none encodes the text of MiCAR.
"""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# The descriptions that README, PyPI, the Action, the CLI help, the playground and the starter template show.
PUBLIC_TEXTS = [
    "README.md",
    "action.yml",
    "src/micar_linter/cli.py",
    "docs/playground/index.html",
    "templates/whitepaper-starter/README.md",
]


@pytest.mark.parametrize("name", PUBLIC_TEXTS)
def test_no_public_description_promises_pinpoint_citations(name: str):
    assert "pinpoint" not in (ROOT / name).read_text(encoding="utf-8").lower()


def test_playground_does_not_say_the_rules_encode_the_text_of_micar():
    page = (ROOT / "docs" / "playground" / "index.html").read_text(encoding="utf-8")
    assert "encode the text of MiCAR" not in page
