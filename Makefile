PYTHON ?= uv run python
PYTHONPATH := packages/core/src:packages/environments/src:packages/evaluation/src
UV_CACHE_DIR ?= .uv-cache
export PYTHONPATH
export UV_CACHE_DIR

.PHONY: setup format lint test schemas hygiene check example clean

setup:
	uv sync --all-packages --dev

format:
	uv run ruff format .
	uv run ruff check --fix .

lint:
	uv run ruff format --check .
	uv run ruff check .

test:
	$(PYTHON) -m unittest discover -s packages/core/tests -p 'test_*.py'
	$(PYTHON) -m unittest discover -s packages/environments/tests -p 'test_*.py'
	$(PYTHON) -m unittest discover -s packages/evaluation/tests -p 'test_*.py'
	$(PYTHON) -m unittest discover -s tests/integration -p 'test_*.py'

schemas:
	$(PYTHON) tools/validate_schemas.py

hygiene:
	$(PYTHON) tools/check_repo_hygiene.py

check: lint test schemas hygiene

example:
	mkdir -p .anarres/example
	$(PYTHON) -m anarres.environments.cli probe examples/environment-processing/probe.json --output .anarres/example/environment.json
	@echo "Wrote .anarres/example/environment.json"

clean:
	find . -type d -name __pycache__ -prune -exec rm -r {} +
	rm -rf .pytest_cache .ruff_cache .anarres
