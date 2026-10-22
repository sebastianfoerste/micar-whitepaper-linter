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
# A code fence, also one opened on a list item line; a backtick fence's info string holds no backtick.
FENCE = re.compile(r"[ \t]*(?:(?:[-*+]|\d{1,9}[.)])[ \t]+)?(`{3,}(?=[^`]*$)|~{3,})")
LINKS = (
    re.compile(r"\]\(\s*<?([^)\s>]+)"),  # [text](target) and ![alt](target)
    re.compile(r"^ {0,3}\[(?!\^)[^\]]+\]:[ \t]*\n?[ \t]*<?([^\s>]+)", re.M),  # [label]: target
    re.compile(r"<a\s(?:[^>]*?\s)?href\s*=\s*[\"']?([^\"'\s>]+)", re.I),
    re.compile(r"<img\s(?:[^>]*?\s)?src\s*=\s*[\"']?([^\"'\s>]+)", re.I),
    re.compile(r"<([A-Za-z][A-Za-z0-9+.-]{1,31}:[^\s<>]*)>"),  # <https://...> autolinks
)
ATX_HEADING = re.compile(r" {0,3}#{1,6}(?:[ \t]+(.*?))??(?:[ \t]+#+)?[ \t]*$")
SETEXT_UNDERLINE = re.compile(r" {0,3}(?:=+|-+)[ \t]*$")
THEMATIC_BREAK = re.compile(r" {0,3}([-*_])(?:[ \t]*\1){2,}[ \t]*$")
# Lines that cannot start a paragraph, so never become a Setext heading: list items, quotes, tables.
NOT_PARAGRAPH = re.compile(r" {0,3}(?:[-*+][ \t]|\d{1,9}[.)][ \t]|>|\|)")


def _prose_lines(text: str) -> list[str]:
    """The lines of a Markdown file with fenced code blocks (``` or ~~~) blanked out."""
    lines: list[str] = []
    fence = ""
    for line in text.splitlines():
        marker = FENCE.match(line)
        if fence:
            if marker and marker.group(1).startswith(fence) and not line[marker.end() :].strip():
                fence = ""
            line = ""
        elif marker:
            fence, line = marker.group(1), ""
        lines.append(line)
    return lines


def _link_targets(text: str) -> list[str]:
    prose = "\n".join(_prose_lines(text))
    return [target for pattern in LINKS for target in pattern.findall(prose)]


def _heading_anchors(path: Path) -> set[str]:
    """GitHub heading slugs of the ATX (`## x`, `## x ##`) and Setext (`x` over `===` or `---`) headings."""
    anchors: set[str] = set()
    paragraph: list[str] = []  # the open paragraph, which a Setext underline turns into a heading
    in_block = False  # inside a list item, quote, table or indented code, whose lines start no paragraph
    for line in _prose_lines(path.read_text(encoding="utf-8")):
        atx = ATX_HEADING.match(line)
        if paragraph and SETEXT_UNDERLINE.match(line):
            heading = "\n".join(paragraph)  # GitHub drops the line break from the slug
        elif atx:
            heading = atx.group(1) or ""
        else:
            if not line.strip() or THEMATIC_BREAK.match(line):
                paragraph, in_block = [], False
            elif NOT_PARAGRAPH.match(line) or (not paragraph and line.startswith(("    ", "\t"))):
                paragraph, in_block = [], True
            elif not in_block:
                paragraph.append(line.strip())
            continue
        paragraph, in_block = [], False
        text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading)
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


def _example_block(text: str) -> tuple[str, list[str]]:
    """The intro between the "## Example output" heading and its ```text block, and the block's lines."""
    section = text.split("## Example output", 1)[1]
    block = re.search(r"```text\n(.*?)\n```", section, re.S)
    assert block, "Example output section has no ```text block"
    intro = section[: block.start()]
    assert not re.search(r"^#", intro, re.M), "the ```text block is not in the Example output section"
    return intro, block.group(1).splitlines()


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
    intro, shown = _example_block((ROOT / doc).read_text(encoding="utf-8"))
    assert main([str(ROOT / "examples/incomplete.json")]) == 0
    real = capsys.readouterr().out.splitlines()

    # The block may end with a single `...` line marking the cut; every line before it is verbatim output.
    if shown[-1] == CUT:
        shown = shown[:-1]
        assert len(shown) < len(real), f"{doc} marks a cut but shows the whole output"
    assert real[: len(shown)] == shown, f"{doc} example output is not the first lines of the real CLI output"

    count = len([line for line in shown if line.startswith("[")])
    label = f"first {NUMBER_WORDS.get(count, count)} findings only"
    assert label in intro, f"{doc} shows {count} findings but the text above the block does not say '{label}'"
