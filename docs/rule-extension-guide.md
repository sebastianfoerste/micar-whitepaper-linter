# How to Extend the Rule Set

The linter treats MiCAR disclosure requirements as deterministic rules. Add rules narrowly and keep every rule reviewable by a lawyer.

## Rule Shape

Each rule is a `Rule` in `src/micar_linter/rules/`.

Required fields:

1. `rule_id`: Stable identifier, for example `ANNEX_II.G.CUSTODY`.
2. `citation`: Pinpoint citation to Regulation (EU) 2023/1114 or a documented technical standard, in the canonical German form (`Art. 6 Abs. 7 MiCAR`); reports convert it to English.
3. `section`: section key read by the rule, as in the `sections` of a JSON draft.
4. `label`: Human-readable description of the disclosure requirement.
5. `severity`: `BLOCKER`, `MAJOR` or `MINOR`.
6. `min_words`, required terms or required patterns.

## Severity Contract

Use the existing severity contract:

1. `BLOCKER`: a mandatory disclosure is absent or the issue blocks notification without remediation.
2. `MAJOR`: disclosure exists but is materially incomplete or likely to require substantive review.
3. `MINOR`: drafting or presentation issue that should be cured before publication.

The ranking is tested in `tests/test_linter.py`. Do not change numeric severity values without updating the tests and explaining the legal consequence.

## Extension Steps

1. Add the rule to `common.py` if every regime needs it, or to the annex module of its regime: `annex_i.py`, `annex_ii.py` or `annex_iii.py`. Rule IDs are stable: add new ones, never rename existing ones.
2. Keep the citation precise and stable. A newly cited act needs an entry in `ACT_URLS` in `citations.py`, and an English name in `to_english()` unless it is a `VO (EU)` regulation or already English.
3. Use deterministic terms or regex patterns before adding any parser complexity. A rule that reads a new section key also needs a heading pattern in `SECTION_PATTERNS` (`document.py`) and, for numbered-field XHTML, a mapping in `numbered_fields.py`.
4. A rule that needs its own logic is dispatched by rule ID in `linter.py` and special-cased in `scripts/build_rule_docs.py`, and may need entries in `ci_outputs.py`. `AGENTS.md` (section 4) lists every place.
5. Add or update a synthetic example that exercises the rule, and a test proving the finding is cited and has the intended severity.
6. Regenerate the rule pages (`uv run python scripts/build_rule_docs.py`) and rebuild the playground wheel. If the rule changes the output of the examples, regenerate the sample outputs too (`AGENTS.md`, section 6).
7. Record the change under "Unreleased" in `CHANGELOG.md`.
8. Run `make check`.

## Review Note

Rules are screening controls. They are not legal advice. Ambiguous or fact-dependent cases should produce `MAJOR` review findings rather than pretending to decide legal sufficiency.
