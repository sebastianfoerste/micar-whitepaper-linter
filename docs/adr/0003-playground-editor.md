# 0003. Playground editor and section highlighting

Status: Proposed

## Context

"Inspect section" selects the section text in a plain `<textarea>`. Ruff's playground uses a full editor (Monaco) with diagnostics inline (Observed) but also autosaves to `localStorage` and stores share links (Observed), which this repo must not do.

## Options

1. Keep the textarea; draw a highlight overlay behind it at the `sectionSelection` span (mirror element, as `wrappedOffset` already does).
2. Vendor CodeMirror 6 as one same-origin ES module under `docs/playground/vendor/` (no CDN, no `+esm`, no bundler in the repo), with decorations for section spans.
3. Monaco: rejected (size, worker setup, CDN expectations).

## Decision (proposed)

Start with option 1. Move to option 2 only if the overlay cannot stay aligned for 1 MB drafts at 390 px. Quick-fixes are structural only (for example, insert a missing section key as `""`), labelled with Ruff-style safety ("safe": changes structure only), and never generate disclosure text.

## Consequences

Option 1 adds no dependency. Option 2 adds a vendored file and a `THIRD_PARTY_NOTICES.md` entry (CodeMirror is MIT).

## Non-negotiables check

No storage, no share links, no generated disclosure text, no model. The playground stays build-free.
