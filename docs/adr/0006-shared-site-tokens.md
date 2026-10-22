# 0006. Shared site tokens (light theme)

Status: Accepted (2026-10-20); amended 2026-10-21, when the dark theme was removed

## Context

The playground used nine colour tokens and about thirty hard-coded colours. The landing page and rule pages need the same look. A first version of this decision also added a dark theme: `prefers-color-scheme`, plus a page-session toggle that stored nothing. Ruff's playground has a theme switch but persists it in `localStorage` (Observed). On 2026-10-21 the owner swapped the dark theme out for the LEI checks (H11, [ADR 0007](0007-lei-rules.md)), which ranked higher.

## Options

1. Keep hard-coded colours.
2. Colour tokens for every value, light theme only.
3. Tokens plus a dark set and a page-session toggle (built on 2026-10-20, then removed).

## Decision

Option 2. Every colour in `docs/playground/styles.css` is a token. `docs/assets/site.css` holds the same tokens and a type scale for the landing and rule pages. Both declare `color-scheme: light`. A dark set can be added later as one more token block, without touching the rules that use the tokens.

## Consequences

- The playground and the static pages share a palette but keep separate stylesheets, because the playground's layout is its own.
- Status colours keep their text labels, so colour is never the only signal.
- The brand-link accessibility fix (`label-content-name-mismatch`) made alongside the dark theme stays.

## Non-negotiables check

No storage, cookies, telemetry or network calls. axe (WCAG 2.2 AA tags) found no violations at 1440 and 390 px.
