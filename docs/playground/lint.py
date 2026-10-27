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
    # An imported .html page keeps its suffix, so messages and source anchors match a CLI run on the
    # same file. The loader does not read .htm, so such a page is read as .html.
    suffix = Path(name).suffix
    if draft_format == "xhtml" and suffix.lower() in (".html", ".htm"):
        suffix = suffix if suffix.lower() == ".html" else ".html"
    else:
        suffix = SUFFIXES[draft_format]
    path = WORKDIR / f"{stem}{suffix}"
    try:
        WORKDIR.mkdir(parents=True, exist_ok=True)
        path.write_text(draft_text, encoding="utf-8")
        whitepaper = load_whitepaper(path, WhitepaperType(regime) if draft_format == "xhtml" else None)
        report = lint_whitepaper(whitepaper)
        return json.dumps({"report": json.loads(render_json(report)), "text": render_text(report)})
    except SystemExit as exc:
        # Loader refusals are written for the user ("State the regime explicitly");
        # tracebacks never leave the worker.
        return json.dumps({"error": str(exc).replace(f"{WORKDIR}/", "")})
    finally:
        path.unlink(missing_ok=True)
