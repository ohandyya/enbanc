.PHONY: help lint fix format format-check check typecheck typecheck-watch test check-all \
        hooks

.DEFAULT_GOAL := help

help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ {printf "  %-14s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

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

test: ## Run the test suite (verbose: per-test names/results)
	uv run pytest -v

# `test` is deliberately not a prerequisite yet: there is no tests/ directory, and pytest exits
# non-zero when it collects nothing, which would make the repo's own gate fail on a clean clone.
# Add it back here the moment the first test lands.
check-all: lint format-check typecheck ## Run every gate: ruff lint, ruff format, pyright
