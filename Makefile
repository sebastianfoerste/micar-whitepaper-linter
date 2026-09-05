UV ?= uv

.PHONY: check install demo lint test smoke review-bundle rule-proof rule-proof-check rule-impact

check: lint test smoke review-bundle rule-proof-check

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

rule-proof:
	$(UV) run --extra dev micar-rule-proof --output docs/rule-provenance.json

rule-proof-check:
	$(UV) run --extra dev micar-rule-proof --check docs/rule-provenance.json

rule-impact:
	$(UV) run --extra dev micar-rule-proof --impact-against docs/rule-provenance.json
