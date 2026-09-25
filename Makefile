UV ?= uv

.PHONY: check install demo lint test smoke review-bundle playground-check playground-samples

check: lint test smoke review-bundle playground-check

install:
	$(UV) sync --extra dev

demo:
	$(UV) run --extra dev python -m micar_linter examples/incomplete.json

lint:
	$(UV) run --extra dev ruff check src tests

test:
	$(UV) run --extra dev pytest -q

smoke:
	$(UV) run --extra dev python -m micar_linter examples/art-stablecoin.json --json > /tmp/micar-linter-smoke.json

review-bundle:
	$(UV) run --extra dev python -m micar_linter examples/art-stablecoin.json \
		--review-bundle-dir dist/review-bundle

playground-check:
	node --check docs/playground/app.mjs
	node --check docs/playground/runtime.mjs
	node --test tests/playground/*.test.mjs

playground-samples:
	$(UV) run python scripts/build_playground_samples.py
