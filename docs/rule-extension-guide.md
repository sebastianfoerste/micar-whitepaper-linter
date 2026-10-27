# How to Extend the Rule Set

The linter treats MiCAR disclosure requirements as deterministic rules. Add rules narrowly and keep every rule reviewable by a lawyer.

## Rule Shape

Each rule is a `Rule` in `src/micar_linter/rules/`.

Required fields:

1. `rule_id`: Stable identifier, for example `ANNEX_II.G.CUSTODY`. Its first part must be `COMMON`, `ANNEX_I`, `ANNEX_II` or `ANNEX_III` (the rule-page build looks the source module up by it in `SOURCE_MODULES`).
2. `citation`: Pinpoint citation to Regulation (EU) 2023/1114 or a documented technical standard, in the canonical German form (`Art. 6 Abs. 7 MiCAR`). The text report (by default) and the CI outputs show the English form; the JSON report and the SARIF rule properties carry both (`citation` and `citation_en`); the rule pages show the English form with the canonical form beside it; and the other outputs (audit log, coverage, remediation, review table, review bundle) and the playground's findings list show the German form.
3. `section`: the section key the generic checks read, as in the `sections` of a JSON draft (`COMMON.IXBRL_TAGGING` reads no section, and the two LEI rules read every section).
4. `label`: Human-readable description of the disclosure requirement.
5. `severity`: `BLOCKER`, `MAJOR` or `MINOR`.
6. `min_words` (default 30, for drafts in both languages), required terms, required patterns or prohibited patterns. The three lists each have an optional German variant (`required_terms_de`, `required_patterns_de`, `prohibited_patterns_de`); without one, a German draft is checked against the English list.

## Severity Contract

Use the existing severity contract. Severity belongs to the rule: it says what is at stake if the check fails, not whether the section is there, so a BLOCKER rule can give a `review` finding and a MAJOR rule a `missing` one. Which tier a rule gets is a judgement recorded per rule; the environmental-impact rules, for example, cite mandatory content but are MAJOR.

1. `BLOCKER`: an open finding should keep the white paper from notification or submission for approval until it is cured or resolved in lawyer review, and makes `--strict` exit 1. The two BLOCKER rules that never pass (the iXBRL format check and the ART deposit-floor review) stay open in every report, so they always need lawyer review.
2. `MAJOR`: the disclosure, if incomplete, is likely to mislead or need substantive review.
3. `MINOR`: a drafting gap that should be cured before publication but does not gate notification, such as a disclosure that applies only in some cases (`ANNEX_I.C`, the trading platform operator, where applicable).

The order is tested in `tests/test_linter.py`. Do not change it without updating that test and explaining the legal consequence.

## Extension Steps

1. Add the rule to `common.py` if every regime needs it, or to the annex module of its regime: `annex_i.py`, `annex_ii.py` or `annex_iii.py`. Rule IDs are stable: add new ones, never rename existing ones.
2. Keep the citation precise and stable. A newly cited act needs an entry in `ACT_URLS` in `citations.py`, and an English name in `to_english()` unless it is a `VO (EU)` regulation or already English.
3. Use deterministic terms or regex patterns before adding any parser complexity. A rule that reads a new section key also needs a heading pattern in `SECTION_PATTERNS` (`document.py`) and, for numbered-field XHTML, a mapping in `numbered_fields.py`. A generic rule that relies on `required_patterns`, or has no listed terms and `min_words=0`, also needs its own branch in `examples()` in `scripts/build_rule_docs.py`, or the rule-page build stops.
4. A rule that needs its own logic is dispatched by rule ID in `linter.py` and special-cased in `scripts/build_rule_docs.py`, and may need entries in `ci_outputs.py`. `AGENTS.md` (section 4) lists every place.
5. Add or update a synthetic example that exercises the rule, and a test proving the finding is cited and has the intended severity.
6. Regenerate the rule pages (`uv run python scripts/build_rule_docs.py`) and rebuild the playground wheel (delete it, then `uv build --wheel -o docs/playground/`). If you edited an example the playground samples are built from, run `make playground-samples`. If the rule changes the output of the examples, refresh the sample outputs too (`AGENTS.md`, section 6).
7. Record the change under "Unreleased" in `CHANGELOG.md`.
8. Run `make check`.

## Review Note

Rules are screening controls. They are not legal advice. Ambiguous or fact-dependent cases should produce `review` findings rather than pretending to decide legal sufficiency. Severity follows what the rule covers, not how certain the check is: the fact-dependent deposit-floor check is a BLOCKER that never passes.
