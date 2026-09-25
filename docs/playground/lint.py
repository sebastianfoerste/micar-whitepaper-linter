"""Browser bridge. Use the CLI's loader so untrusted metadata stays untrusted."""

import json
from pathlib import Path

from micar_linter.linter import lint_whitepaper
from micar_linter.report import render_json, render_text
from micar_linter.whitepaper import load_whitepaper


def lint_draft(draft_text: str) -> str:
    path = Path("/tmp/micar-playground-draft.json")
    try:
        path.write_text(draft_text, encoding="utf-8")
        report = lint_whitepaper(load_whitepaper(path))
        return json.dumps({"report": json.loads(render_json(report)), "text": render_text(report)})
    finally:
        path.unlink(missing_ok=True)
