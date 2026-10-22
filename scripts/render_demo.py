"""Render the real demo output to docs/demo.png, with the exact captured text in docs/demo.txt.

Run with `make demo-image` or `uv run python scripts/render_demo.py`. The screenshot needs headless
Chrome or Chromium; set CHROME to its path or name if it is not /usr/bin/google-chrome. Chrome does not
start as root (the default user in many containers) without `--no-sandbox`; run the script as a regular
user, or point CHROME at a wrapper that adds the flag.

Both files are written only after the screenshot succeeds. The PNG carries a tEXt chunk with the sha256
of the page, window size and flags Chrome was given, so tests/test_demo_capture.py detects a stale image
from the current CLI output without Chrome.
"""

import hashlib
import html
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import textwrap
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = "examples/incomplete.json"
COMMAND = f"uv run micar-lint {EXAMPLE}"
COLUMNS = 120
FONT_PX = 13
LINE_PX = 18
PAD_PX = 20
WIDTH_PX = 1000
TIMEOUT_S = 120
CHROME_FLAGS = ("--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
STAMP_KEYWORD = b"micar-demo-input-sha256"


def run(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a command from ROOT with a timeout; a failure raises with its stderr, not just an exit code."""
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=TIMEOUT_S)
    if result.returncode != 0:
        raise RuntimeError(f"{args[0]} exited with status {result.returncode}:\n{result.stderr}")
    return result


def capture() -> str:
    """Stdout of the CLI on the synthetic draft; `-m micar_linter` is the `micar-lint` entry point."""
    return run([sys.executable, "-m", "micar_linter", EXAMPLE]).stdout


def terminal_lines(output: str) -> list[str]:
    # Wrap long lines at word boundaries, continuing 3 columns past their own indent so wrapped
    # issue text stays aligned. The wrap depends only on the text, so the page height is known up front.
    # A no-break space keeps "Art." on the same line as its number.
    lines = [f"$ {COMMAND}"]
    for line in output.splitlines():
        if len(line) <= COLUMNS:
            lines.append(line)
            continue
        indent = " " * (len(line) - len(line.lstrip(" ")) + 3)
        wrapped = textwrap.wrap(
            line.replace("Art. ", "Art.\xa0"), COLUMNS, subsequent_indent=indent, break_on_hyphens=False
        )
        lines.extend(part.replace("\xa0", " ") for part in wrapped or [line])
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


def fingerprint(output: str) -> str:
    """sha256 of everything Chrome is given for `output`: the page, the window size and the flags."""
    rendered = "\n".join([build_html(output), "{}x{}".format(*page_size(output)), *CHROME_FLAGS])
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def png_chunks(png: bytes) -> list[tuple[bytes, bytes]]:
    """(type, data) of every chunk, after checking the signature, the lengths and every CRC."""
    if png[:8] != PNG_SIGNATURE:
        raise ValueError("not a PNG file")
    chunks, pos = [], 8
    while pos + 12 <= len(png):
        (length,) = struct.unpack(">I", png[pos : pos + 4])
        kind, data = png[pos + 4 : pos + 8], png[pos + 8 : pos + 8 + length]
        if png[pos + 8 + length : pos + 12 + length] != struct.pack(">I", zlib.crc32(kind + data)):
            raise ValueError(f"truncated or corrupt PNG chunk {kind!r} at byte {pos}")
        chunks.append((kind, data))
        pos += 12 + length
    if pos != len(png) or not chunks or chunks[0][0] != b"IHDR" or chunks[-1][0] != b"IEND":
        raise ValueError("truncated PNG, or IHDR not first, or IEND not last")
    return chunks


def unfilter(raw: bytes, width: int, height: int, bpp: int) -> list[bytes]:
    """Undo the PNG scanline filters (None, Sub, Up, Average, Paeth) and return the pixel rows."""
    stride, prev, rows = width * bpp, bytearray(width * bpp), []
    if len(raw) != height * (stride + 1):
        raise ValueError("PNG image data does not match the image size")
    for y in range(height):
        start = y * (stride + 1) + 1
        kind, row = raw[start - 1], bytearray(raw[start : start + stride])
        if kind > 4:
            raise ValueError(f"bad PNG filter type {kind} in row {y}")
        if kind == 2:
            row = bytearray((x + b) & 255 for x, b in zip(row, prev, strict=True))
        elif kind:
            for i in range(stride):
                a = row[i - bpp] if i >= bpp else 0
                if kind == 1:
                    row[i] = (row[i] + a) & 255
                elif kind == 3:
                    row[i] = (row[i] + (a + prev[i]) // 2) & 255
                else:
                    b, c = prev[i], prev[i - bpp] if i >= bpp else 0
                    pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                    row[i] = (row[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append(bytes(row))
        prev = row
    return rows


def optimise(png: bytes) -> bytes:
    """The same pixels with unfiltered rows in one IDAT at zlib level 9, about a quarter smaller.

    Only 8-bit, non-interlaced RGB or RGBA (what Chrome writes) is re-encoded; other PNGs pass through.
    """
    chunks = png_chunks(png)
    width, height, depth, colour, _, _, interlace = struct.unpack(">IIBBBBB", chunks[0][1])
    bpp = {2: 3, 6: 4}.get(colour)
    if depth != 8 or interlace or bpp is None:
        return png
    kinds = [kind for kind, _ in chunks]
    first, end = kinds.index(b"IDAT"), len(kinds) - kinds[::-1].index(b"IDAT")
    rows = unfilter(zlib.decompress(b"".join(data for _, data in chunks[first:end])), width, height, bpp)
    compressor = zlib.compressobj(9, zlib.DEFLATED, 15, 9)
    idat = compressor.compress(b"".join(b"\0" + row for row in rows)) + compressor.flush()
    parts = [*chunks[:first], (b"IDAT", idat), *chunks[end:]]
    return PNG_SIGNATURE + b"".join(png_chunk(kind, data) for kind, data in parts)


def stamp(png: bytes, digest: str) -> bytes:
    """Insert a tEXt chunk holding `digest` straight after the IHDR chunk (byte 33)."""
    end = 8 + 12 + len(png_chunks(png)[0][1])
    return png[:end] + png_chunk(b"tEXt", STAMP_KEYWORD + b"\0" + digest.encode("ascii")) + png[end:]


def stamp_of(png: bytes) -> str | None:
    """The digest written by stamp(), or None if the PNG has none."""
    for kind, data in png_chunks(png):
        if kind == b"tEXt" and data.startswith(STAMP_KEYWORD + b"\0"):
            return data[len(STAMP_KEYWORD) + 1 :].decode("ascii")
    return None


def screenshot(chrome: str, page: Path, size: tuple[int, int]) -> bytes:
    """PNG of `page` at `size`, written next to it in its temporary directory."""
    target = page.with_suffix(".png")
    window = "--window-size={},{}".format(*size)
    log = run([chrome, *CHROME_FLAGS, f"--screenshot={target}", window, page.as_uri()]).stderr
    if not target.exists():
        raise RuntimeError(f"{chrome} wrote no screenshot:\n{log}")
    return target.read_bytes()


def main() -> None:
    wanted = os.environ.get("CHROME") or "/usr/bin/google-chrome"
    found = shutil.which(wanted)
    if found is None:
        raise RuntimeError(f"Chrome or Chromium not found at {wanted!r}; set CHROME to its path or name")
    # Absolute, because commands run from ROOT while a relative CHROME was found from the caller's directory.
    chrome = os.path.abspath(found)
    output = capture()
    size = page_size(output)
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "demo.html"
        page.write_text(build_html(output), encoding="utf-8")
        png = stamp(optimise(screenshot(chrome, page, size)), fingerprint(output))
    shot_size = struct.unpack(">II", png[16:24])
    if shot_size != size:
        raise RuntimeError("Chrome returned a {}x{} screenshot instead of {}x{}".format(*shot_size, *size))
    (ROOT / "docs/demo.txt").write_text(output, encoding="utf-8")
    (ROOT / "docs/demo.png").write_bytes(png)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, zlib.error, subprocess.TimeoutExpired) as error:
        sys.exit(f"render_demo: {error}")
