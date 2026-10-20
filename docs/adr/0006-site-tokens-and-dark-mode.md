# 0006. Shared site tokens and dark mode without storage

Status: Accepted (2026-10-20)

## Context

The playground used nine colour tokens and about thirty hard-coded colours, light only. The landing page and rule pages need the same look. Ruff's playground offers a theme switch but persists it in `localStorage` (Observed); this repo promises not to persist state in the browser.

## Options

1. Dark mode via `prefers-color-scheme` only.
2. A toggle that persists the choice.
3. `prefers-color-scheme` plus a page-session toggle that sets `<html data-theme>` and writes nothing.

## Decision

Option 3. Every colour in `docs/playground/styles.css` is a token, with a dark set under `@media (prefers-color-scheme: dark) :root:not([data-theme="light"])` and `:root[data-theme="dark"]`. `docs/assets/site.css` holds the same tokens and a type scale for the landing and rule pages. `docs/assets/theme.js` wires any `[data-theme-toggle]` button: constant label, `aria-pressed` state, no storage or cookies; a reload follows the system setting.

## Consequences

The playground and static pages share a palette but keep separate stylesheets (the playground's layout is its own). Status colours keep text labels, so colour is never the only signal.

## Non-negotiables check

No storage, cookies, telemetry or network calls. axe (WCAG 2.2 AA tags): no violations in either theme at 1440 and 390 px.
