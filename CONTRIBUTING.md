# Contributing

This is a personal portfolio project. External contributions are not accepted at this time.

If you are evaluating the repository, please read the [Verification checklist](docs/DETAILS.md#verification-checklist) in `docs/DETAILS.md`.

## Running the Tests

```bash
# Install environment (uv required)
uv sync --extra dev

# Run the full proof gate (ruff, pytest, CLI smoke, review bundle, playground and template checks)
make check

# Run pytest directly
uv run --extra dev pytest
```

## Safe Development Conventions

1. **No real white paper content.** Use the bundled synthetic fixture files in `examples/`. Do not add real issuer or token names, real IBAN or wallet addresses, or real regulatory correspondence.
2. **Report language is load-bearing.** `tests/test_report.py` renders real reports from `src/micar_linter/report.py` and checks that the text report shows the "not package-ready" blocker message while any finding is open, that the audit log shows it while any BLOCKER finding is open, that neither shows it otherwise, that the audit log says all automated checks passed only when every finding passes and gives the number of open findings by severity while a MAJOR or MINOR finding is open and no BLOCKER is, and that the audit log always ends with the lawyer sign-off section. Do not weaken the "not package-ready" language or the "lawyer has signed off" requirement.
3. **Coverage matrix is documented.** The linter covers Annexes I/II/III. Document any new rule's article reference accurately, and follow the steps in [docs/rule-extension-guide.md](docs/rule-extension-guide.md); a new rule also reaches the generated rule pages, the playground wheel and the sample outputs.
4. **Test before commit.** Run `make check` before staging any change. The report language tests must pass.

## Coding Agents

See `AGENTS.md` for guidelines on how future coding agents should work on this repository.
