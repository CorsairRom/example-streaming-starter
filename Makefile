SHELL := /bin/bash
HOST ?= 127.0.0.1
PORT ?= 8000

.PHONY: help install run dev test lint format check db-reset clean

help: ## Show available targets
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Create the virtualenv and install dependencies
	uv sync

run: ## Start the API without reload
	uv run uvicorn app.main:app --app-dir src --host $(HOST) --port $(PORT)

dev: ## Start the API with auto-reload
	uv run uvicorn app.main:app --app-dir src --host $(HOST) --port $(PORT) --reload

test: ## Run the test suite
	uv run pytest

lint: ## Check formatting and lint rules
	uv run ruff format --check .
	uv run ruff check .

format: ## Format the code and apply safe fixes
	uv run ruff format .
	uv run ruff check --fix .

check: lint test ## Lint plus tests, the same thing CI should run

db-reset: ## Delete the local SQLite database (API keys included)
	rm -f data/app.db

clean: ## Remove virtualenv, caches and local data
	rm -rf .venv .pytest_cache .ruff_cache data
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
