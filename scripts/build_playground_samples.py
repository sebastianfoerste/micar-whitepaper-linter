"""Bundle the canonical synthetic examples for the static playground."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = {
    "incomplete": "incomplete.json",
    "other": "other-crypto-asset.json",
    "art": "art-stablecoin.json",
    "emt": "emt-token.json",
}


def build_samples() -> str:
    return json.dumps(
        {key: json.loads((ROOT / "examples" / filename).read_text()) for key, filename in SAMPLES.items()},
        indent=2,
        ensure_ascii=False,
    ) + "\n"


if __name__ == "__main__":
    (ROOT / "docs/playground/samples.json").write_text(build_samples(), encoding="utf-8")
