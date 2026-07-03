# How to Extend the Rule Set

The linter treats MiCAR disclosure requirements as deterministic rules. Add rules narrowly and keep every rule reviewable by a lawyer.

## Rule Shape

Each rule is a `Rule` in `src/micar_linter/rules/`.

Required fields:

1. `rule_id`: Stable identifier, for example `ANNEX_II.G.CUSTODY`.
2. `citation`: Pinpoint citation to Regulation (EU) 2023/1114 or a documented technical standard.
3. `section`: JSON section key read by the rule.
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

1. Add the rule to the correct annex module: `annex_i.py`, `annex_ii.py` or `annex_iii.py`.
2. Keep the citation precise and stable.
3. Use deterministic terms or regex patterns before adding any parser complexity.
4. Add or update a synthetic example that exercises the rule.
5. Add a test proving the finding is cited and has the intended severity.
6. Run `make check`.

## Review Note

Rules are screening controls. They are not legal advice. Ambiguous or fact-dependent cases should produce `MAJOR` review findings rather than pretending to decide legal sufficiency.
