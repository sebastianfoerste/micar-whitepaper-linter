# Codex Worldclass Implementation Prompt

You are Codex working in the repository: /Users/sebastian/Developer/micar-whitepaper-linter

The app is a deterministic Python CLI that checks draft MiCAR crypto-asset white papers against annex-specific disclosure rules and emits review artifacts.

Current problems: the CLI is strong, but the review bundle needs better sample outputs, more visual documentation and consistently cautious legal wording. The target state is a credible regulation-as-code package for first-pass lawyer review.

Inspect first:
- `README.md`
- `pyproject.toml`
- `Makefile`
- `src/micar_linter/`
- `tests/`
- `examples/`
- `reports/`
- `docs/WORLDCLASS_PRODUCT_PLAN.md`

Implement focused improvements:
- Add sample review bundle docs using synthetic examples.
- Add tests for any changed report wording or output schema.
- Improve coverage matrix and remediation documentation.
- Keep blocker language framed as package-readiness and lawyer-review gating.

Do not change:
- Rule IDs or severity semantics without migration notes and tests.
- Legal citations without verifying against current primary text.
- Any wording that implies filing approval, legal advice or regulatory certainty.
- Any sample that looks like a real issuer or client.

Run checks:
- `make check`

Update documentation:
- `README.md`
- `docs/rule-extension-guide.md` if rules change
- sample report docs if generated

Final report:
- Summarize files changed.
- State test results.
- Identify remaining rule-coverage and legal-source risks.
- Do not invent legal claims, issuer facts, credentials, benchmarks or regulatory conclusions.
