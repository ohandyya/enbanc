.PHONY: help lint fix format format-check check typecheck typecheck-watch test check-all \
        hooks unit-tests contract-tests integration-tests e2e-tests

.DEFAULT_GOAL := help

help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z0-9_-]+:.*##/ {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

hooks: ## Install the git pre-commit hook (run once per clone)
	uv run pre-commit install

lint: ## Check code for lint errors
	uv run ruff check .

fix: ## Check code for lint errors and auto-fix what's fixable
	uv run ruff check --fix .

format: ## Reformat code in place
	uv run ruff format .

format-check: ## Check code formatting without writing changes (CI-safe)
	uv run ruff format --check .

check: lint format-check ## Run lint and format-check together

typecheck: ## Check code for type errors
	uv run pyright

typecheck-watch: ## Re-run pyright on file changes
	uv run pyright --watch

# The tiers. A test's tier is the directory it lives in, so these select by path rather
# than by marker — see docs/design/testing.md and docs/decisions/0031-tests-are-tiered.md.
# unit and contract are offline and enforced; integration and e2e reach real providers,
# read keys from .env, and skip when those are absent.

unit-tests: ## Run the unit tier: enbanc's own behaviour, offline
	uv run pytest -v tests/unit

contract-tests: ## Run the contract tier: what execution.md claims about pydantic-ai
	uv run pytest -v tests/contract

integration-tests: ## Run the integration tier: real Tavily, real provider (costs money)
	uv run pytest -v tests/integration

e2e-tests: ## Run the e2e tier: api.md's example end to end (costs money)
	uv run pytest -v tests/e2e

# The offline gate. check-all and CI run this, so neither ever needs a provider key.
test: ## Run every offline test: the unit and contract tiers
	uv run pytest -v tests/unit tests/contract

check-all: lint format-check typecheck test ## Run every gate: ruff lint, ruff format, pyright, pytest
