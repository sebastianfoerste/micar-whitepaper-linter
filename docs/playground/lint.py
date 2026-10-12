"""Browser bridge. Use the CLI's loader so untrusted metadata stays untrusted."""

import json
import re
from pathlib import Path

from micar_linter.linter import lint_whitepaper
from micar_linter.report import render_json, render_text
from micar_linter.whitepaper import WhitepaperType, load_whitepaper

WORKDIR = Path("/tmp/micar-playground")
SUFFIXES = {"json": ".json", "xhtml": ".xhtml"}


def lint_draft(draft_text: str, draft_format: str = "json", regime: str = "", name: str = "") -> str:
    # The loader titles a document after its file name, so keep the imported name without its path.
    stem = re.sub(r"[^\w .-]", "_", Path(name).stem).strip(" .") or "whitepaper-draft"
    path = WORKDIR / f"{stem}{SUFFIXES[draft_format]}"
    try:
        WORKDIR.mkdir(parents=True, exist_ok=True)
        path.write_text(draft_text, encoding="utf-8")
        whitepaper = load_whitepaper(path, WhitepaperType(regime) if draft_format == "xhtml" else None)
        report = lint_whitepaper(whitepaper)
        return json.dumps({"report": json.loads(render_json(report)), "text": render_text(report)})
    except SystemExit as exc:
        # Loader refusals are written for the user ("State the regime explicitly"); tracebacks never leave the worker.
        return json.dumps({"error": str(exc).replace(f"{WORKDIR}/", "")})
    finally:
        path.unlink(missing_ok=True)
