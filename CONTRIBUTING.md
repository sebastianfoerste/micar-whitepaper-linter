# Contributing

This is a personal portfolio project. External contributions are not accepted at this time.

If you are evaluating the repository, please read the [Reviewer Checklist](README.md#reviewer-checklist) in the README.

## Running the Tests

```bash
# Install environment (uv required)
uv sync --extra dev

# Run the full proof gate (ruff + pytest + smoke command)
make check

# Run pytest directly
uv run --extra dev pytest
```

## Safe Development Conventions

1. **No real white paper content.** Use the bundled synthetic fixture files in `examples/`. Do not add real issuer or token names, real IBAN or wallet addresses, or real regulatory correspondence.
2. **Report language is load-bearing.** The blocker message and lawyer sign-off section in `src/micar_linter/report.py` are tested. Do not weaken the "not package-ready" language or the "lawyer has signed off" requirement.
3. **Coverage matrix is documented.** The linter covers Annexes I/II/III. Document any new rule's article reference accurately.
4. **Test before commit.** Run `make check` before staging any change. The language regression test must pass.

## Coding Agents

See `AGENTS.md` for guidelines on how future coding agents should work on this repository.
