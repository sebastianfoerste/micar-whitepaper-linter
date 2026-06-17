UV ?= uv

.PHONY: check lint test smoke review-bundle

check: lint test smoke review-bundle

lint:
	$(UV) run --extra dev ruff check src tests

test:
	$(UV) run --extra dev pytest -q

smoke:
	$(UV) run --extra dev python -m micar_linter examples/art-stablecoin.json --json > /tmp/micar-linter-smoke.json

review-bundle:
	mkdir -p dist/review-bundle
	$(UV) run --extra dev python -m micar_linter examples/art-stablecoin.json \
		--audit-log dist/review-bundle/compliance-checklist.md \
		--remediation-output dist/review-bundle/remediation-checklist.json \
		--coverage-output dist/review-bundle/coverage-matrix.json \
		--manifest-output dist/review-bundle/manifest.json
