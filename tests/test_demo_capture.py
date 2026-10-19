import runpy
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STALE = "docs/demo.png is stale; rerun `uv run python scripts/render_demo.py` and commit both files"


def test_demo_capture_matches_current_cli_output():
    renderer = runpy.run_path(str(ROOT / "scripts/render_demo.py"))
    captured = (ROOT / "docs/demo.txt").read_text(encoding="utf-8")
    assert captured == renderer["capture"](), STALE

    # The PNG header holds width and height; the height follows the captured line count.
    png = (ROOT / "docs/demo.png").read_bytes()
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", png[16:24]) == renderer["page_size"](captured), STALE
