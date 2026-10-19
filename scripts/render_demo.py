"""Render the real demo output to docs/demo.png, with the exact captured text in docs/demo.txt.

Run with `uv run python scripts/render_demo.py`. The screenshot needs headless Chrome or Chromium;
set CHROME to its path if it is not /usr/bin/google-chrome.
"""

import html
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = "examples/incomplete.json"
COMMAND = f"uv run micar-lint {EXAMPLE}"
COLUMNS = 120
FONT_PX = 13
LINE_PX = 18
PAD_PX = 20
WIDTH_PX = 1000


def capture() -> str:
    """Stdout of the CLI on the synthetic draft; `-m micar_linter` is the `micar-lint` entry point."""
    return subprocess.run(
        [sys.executable, "-m", "micar_linter", EXAMPLE],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def terminal_lines(output: str) -> list[str]:
    # Wrap at COLUMNS like a terminal of that width, so the page height is known up front.
    lines = [f"$ {COMMAND}"]
    for line in output.splitlines():
        lines.extend(line[i : i + COLUMNS] for i in range(0, max(len(line), 1), COLUMNS))
    return lines


def page_size(output: str) -> tuple[int, int]:
    return WIDTH_PX, 2 * PAD_PX + LINE_PX * len(terminal_lines(output))


def build_html(output: str) -> str:
    prompt, *rest = (html.escape(line) for line in terminal_lines(output))
    body = "\n".join([f'<span class="prompt">{prompt}</span>', *rest])
    return f"""<!doctype html>
<meta charset="utf-8">
<style>
  html, body {{ margin: 0; background: #0d1117; }}
  pre {{
    margin: 0;
    padding: {PAD_PX}px;
    color: #e6edf3;
    font: {FONT_PX}px/{LINE_PX}px "DejaVu Sans Mono", monospace;
    white-space: pre;
  }}
  .prompt {{ color: #8b949e; }}
</style>
<pre>{body}</pre>
"""


def screenshot(page: Path, target: Path, size: tuple[int, int]) -> None:
    chrome = os.environ.get("CHROME", "/usr/bin/google-chrome")
    subprocess.run(
        [
            chrome,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--force-device-scale-factor=1",
            f"--screenshot={target}",
            "--window-size={},{}".format(*size),
            page.as_uri(),
        ],
        capture_output=True,
        check=True,
        timeout=120,
    )


if __name__ == "__main__":
    output = capture()
    (ROOT / "docs/demo.txt").write_text(output, encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "demo.html"
        page.write_text(build_html(output), encoding="utf-8")
        screenshot(page, ROOT / "docs/demo.png", page_size(output))
