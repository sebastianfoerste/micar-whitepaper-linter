"""The browser playground ships a prebuilt wheel. Nothing rebuilds it automatically,
so a linter change can silently leave the published page running old rules."""

from __future__ import annotations

import tomllib
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAYGROUND = REPO_ROOT / "docs" / "playground"
SRC = REPO_ROOT / "src"


def _wheel() -> Path:
    wheels = sorted(PLAYGROUND.glob("*.whl"))
    assert len(wheels) == 1, f"expected exactly one playground wheel, found {[w.name for w in wheels]}"
    return wheels[0]


def _project_version() -> str:
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return data["project"]["version"]


def test_wheel_filename_matches_project_version() -> None:
    assert _wheel().name == f"micar_whitepaper_linter-{_project_version()}-py3-none-any.whl"


def test_playground_html_references_the_shipped_wheel() -> None:
    html = (PLAYGROUND / "index.html").read_text(encoding="utf-8")
    assert _wheel().name in html, "index.html points at a wheel that is not in docs/playground"


def test_wheel_contents_match_the_source_tree() -> None:
    stale: list[str] = []
    with zipfile.ZipFile(_wheel()) as zf:
        packaged = [n for n in zf.namelist() if n.startswith("micar_linter/") and n.endswith(".py")]
        assert packaged, "wheel contains no micar_linter sources"
        for name in packaged:
            source = SRC / name
            if not source.exists():
                stale.append(f"{name}: in wheel, missing from src/")
            elif zf.read(name) != source.read_bytes():
                stale.append(f"{name}: differs from src/")
        for source in sorted(SRC.rglob("*.py")):
            name = source.relative_to(SRC).as_posix()
            if name not in packaged:
                stale.append(f"{name}: in src/, missing from wheel")
    if stale:
        pytest.fail(
            "docs/playground wheel is stale; rebuild it with "
            "`uv build --wheel -o docs/playground/` and delete the superseded wheel.\n  "
            + "\n  ".join(stale)
        )
