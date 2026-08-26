#!/usr/bin/env python3
"""Validate the starter template without changing its public interface."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "whitepaper-starter"


def main() -> int:
    required = {
        "README.md",
        "LICENSE",
        "whitepaper.json",
        ".github/workflows/micar-lint.yml",
    }
    missing = sorted(path for path in required if not (TEMPLATE / path).is_file())
    if missing:
        raise SystemExit(f"missing template files: {', '.join(missing)}")

    payload = json.loads((TEMPLATE / "whitepaper.json").read_text(encoding="utf-8"))
    if payload.get("type") not in {"art", "emt", "other"}:
        raise SystemExit("whitepaper.json type must be art, emt or other")
    if not isinstance(payload.get("sections"), dict) or not payload["sections"]:
        raise SystemExit("whitepaper.json must contain disclosure sections")

    workflow = (TEMPLATE / ".github/workflows/micar-lint.yml").read_text(
        encoding="utf-8"
    )
    required_fragments = {
        "uses: sebastianfoerste/micar-whitepaper-linter@v1",
        "whitepaper: whitepaper.json",
        "strict: 'false'",
    }
    absent = sorted(fragment for fragment in required_fragments if fragment not in workflow)
    if absent:
        raise SystemExit(f"template workflow contract changed: {', '.join(absent)}")

    print("whitepaper starter contract passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
