"""The README is the PyPI description and the first thing a reviewer reads: keep it short, its links
absolute and resolvable, and its sample output honest. Sections trimmed from it live in docs/."""

import re
from pathlib import Path

import pytest

from micar_linter.cli import main

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
README_MAX_WORDS = 350
# Docs that hold sections moved out of the README; the README must keep linking to them.
README_CONTENT_DOCS = ("docs/SETUP.md", "docs/DETAILS.md", "docs/overview.md", "docs/TESTING.md")
README_DOCS_TARGETS = ("docs/SETUP.md#quick-start", "docs/DETAILS.md", "docs/overview.md")
# PyPI renders the README outside the repository, so repository links must be absolute.
REPO_BLOB = "https://github.com/sebastianfoerste/micar-whitepaper-linter/blob/main/"
URL_SCHEME = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*:")
CUT = "..."
NUMBER_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}


def _link_targets(text: str) -> list[str]:
    return re.findall(r"\]\(\s*<?([^)\s>]+)", text)


def _heading_anchors(path: Path) -> set[str]:
    """GitHub heading slugs, skipping fenced code blocks."""
    anchors: set[str] = set()
    in_fence = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        heading = re.match(r"#{1,6}\s+(.*?)\s*$", line)
        if in_fence or not heading:
            continue
        text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading.group(1))
        slug = re.sub(r"[^\w\- ]", "", text.lower()).replace(" ", "-")
        anchor, suffix = slug, 0
        while anchor in anchors:
            suffix += 1
            anchor = f"{slug}-{suffix}"
        anchors.add(anchor)
    return anchors


def _assert_resolves(path: Path, anchor: str, link: str, source: str) -> None:
    assert path.exists(), f"{source} link target does not exist: {link}"
    if anchor and path.suffix == ".md":
        assert anchor in _heading_anchors(path), f"{source} anchor not found: {link}"


def _example_block(text: str) -> list[str]:
    section = text.split("## Example output", 1)[1]
    block = re.search(r"```text\n(.*?)\n```", section, re.S)
    assert block, "Example output section has no ```text block"
    return block.group(1).splitlines()


def test_readme_stays_within_word_budget():
    words = len(README.read_text(encoding="utf-8").split())
    assert words <= README_MAX_WORDS, f"README has {words} words, budget is {README_MAX_WORDS}"


def test_readme_has_no_relative_links():
    relative = [t for t in _link_targets(README.read_text(encoding="utf-8")) if not URL_SCHEME.match(t)]
    assert not relative, f"README is the PyPI description, use absolute links: {relative}"


def test_readme_repository_links_resolve_locally():
    for link in _link_targets(README.read_text(encoding="utf-8")):
        if link.startswith(REPO_BLOB):
            target, _, anchor = link.removeprefix(REPO_BLOB).partition("#")
            _assert_resolves(ROOT / target, anchor, link, "README")


@pytest.mark.parametrize("target", README_DOCS_TARGETS)
def test_readme_links_the_docs_that_hold_its_moved_sections(target):
    assert f"]({REPO_BLOB}{target})" in README.read_text(encoding="utf-8")


@pytest.mark.parametrize("doc", README_CONTENT_DOCS)
def test_moved_sections_have_working_relative_links(doc):
    path = ROOT / doc
    for link in _link_targets(path.read_text(encoding="utf-8")):
        if URL_SCHEME.match(link):
            continue
        target, _, anchor = link.partition("#")
        _assert_resolves(path.parent / target if target else path, anchor, link, doc)


@pytest.mark.parametrize("doc", ["README.md", "docs/DETAILS.md"])
def test_example_output_is_the_start_of_the_real_cli_output(doc, capsys):
    text = (ROOT / doc).read_text(encoding="utf-8")
    shown = _example_block(text)
    assert main([str(ROOT / "examples/incomplete.json")]) == 0
    real = capsys.readouterr().out.splitlines()

    # The block may end with a single `...` line marking the cut; every line before it is verbatim output.
    if shown[-1] == CUT:
        shown = shown[:-1]
        assert len(shown) < len(real), f"{doc} marks a cut but shows the whole output"
    assert real[: len(shown)] == shown, f"{doc} example output is not the first lines of the real CLI output"

    findings = [line for line in shown if line.startswith("[")]
    assert f"first {NUMBER_WORDS[len(findings)]} findings only" in text, (
        f"{doc} shows {len(findings)} findings but labels them differently"
    )
