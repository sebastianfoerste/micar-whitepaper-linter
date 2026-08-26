UV ?= uv

.PHONY: check install demo lint test smoke review-bundle template-check template-export

check: lint test smoke review-bundle template-check

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

template-check:
	python3 scripts/check_whitepaper_starter.py

template-export:
	scripts/export-whitepaper-starter.sh
