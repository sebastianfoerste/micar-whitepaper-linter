import runpy
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RERUN = "rerun `make demo-image` (needs Chrome) and commit docs/demo.txt and docs/demo.png"


def test_demo_capture_matches_current_cli_output():
    renderer = runpy.run_path(str(ROOT / "scripts/render_demo.py"))
    output = renderer["capture"]()
    assert (ROOT / "docs/demo.txt").read_text(encoding="utf-8") == output, (
        f"docs/demo.txt no longer matches the CLI output; {RERUN}"
    )

    # The PNG header holds width and height; the height follows the wrapped line count.
    png = (ROOT / "docs/demo.png").read_bytes()
    assert png[:8] == renderer["PNG_SIGNATURE"], "docs/demo.png is not a PNG file"
    stale_png = f"docs/demo.png was not rendered from the current CLI output; {RERUN}"
    assert struct.unpack(">II", png[16:24]) == renderer["page_size"](output), stale_png
    # The PNG is stamped with the sha256 of the page it was rendered from, so any change to the
    # output, even one that keeps the line count, fails here without Chrome.
    assert renderer["stamp_of"](png) == renderer["fingerprint"](output), stale_png
