UV ?= uv

.PHONY: check lint test smoke

check: lint test smoke

lint:
	$(UV) run --extra dev ruff check src tests

test:
	$(UV) run --extra dev pytest -q

smoke:
	$(UV) run --extra dev python -m micar_linter examples/art-stablecoin.json --json > /tmp/micar-linter-smoke.json
