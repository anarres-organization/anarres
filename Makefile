PYTHON ?= uv run python
CARGO ?= cargo
PYTHONPATH := packages/core/src:packages/environments/src:packages/evaluation/src:packages/finance/src:packages/legal/src:packages/vulnerability/src
UV_CACHE_DIR ?= .uv-cache
export PYTHONPATH
export UV_CACHE_DIR

.PHONY: setup format lint test rust-format rust-lint rust-test schemas hygiene prose check study-check study-check-extended materials-check release-smoke adapter-smoke benchmark example docs docs-serve clean

setup:
	uv sync --all-packages --dev
	$(CARGO) fetch --locked

format:
	uv run ruff format .
	uv run ruff check --fix .
	$(CARGO) fmt --all

lint:
	uv run ruff format --check .
	uv run ruff check .

rust-format:
	$(CARGO) fmt --all -- --check

rust-lint:
	$(CARGO) clippy --workspace --all-targets -- -D warnings

rust-test:
	$(CARGO) test --workspace

test:
	$(CARGO) build --quiet -p anarres-cli
	$(PYTHON) -m unittest discover -s packages/core/tests -p 'test_*.py'
	$(PYTHON) -m unittest discover -s packages/environments/tests -p 'test_*.py'
	$(PYTHON) -m unittest discover -s packages/evaluation/tests -p 'test_*.py'
	$(PYTHON) -m unittest discover -s packages/finance/tests -p 'test_*.py'
	$(PYTHON) -m unittest discover -s packages/legal/tests -p 'test_*.py'
	$(PYTHON) -m unittest discover -s packages/vulnerability/tests -p 'test_*.py'
	$(PYTHON) -m unittest discover -s tests/integration -p 'test_*.py'

schemas:
	$(PYTHON) tools/validate_schemas.py

hygiene:
	$(PYTHON) tools/check_repo_hygiene.py

prose:
	$(PYTHON) tools/check_prose_style.py

check: lint rust-format rust-lint test rust-test schemas hygiene prose

study-check:
	$(PYTHON) tools/check_study_reproduction.py

study-check-extended:
	$(PYTHON) tools/check_study_reproduction.py --extended

materials-check:
	uv run --group materials-test pytest -q experiments/ai-for-science/materials-science

release-smoke:
	$(CARGO) build --release --locked -p anarres-cli
	$(PYTHON) tools/smoke_cli_release.py --binary target/release/anarres --max-startup-ms 50

adapter-smoke:
	$(PYTHON) tools/smoke_adapter_installation.py --binary target/release/anarres

benchmark:
	mkdir -p target/benchmarks
	$(PYTHON) tools/benchmark_cli.py --binary target/release/anarres --output target/benchmarks/cli.json

example:
	mkdir -p .anarres/example
	$(CARGO) run --quiet -p anarres-cli -- measure examples/environment-processing/probe.json --output .anarres/example/environment.json --force
	@echo "Wrote .anarres/example/environment.json"

docs:
	uv run --group docs mkdocs build --strict

docs-serve:
	uv run --group docs mkdocs serve

clean:
	find . -type d -name __pycache__ -prune -exec rm -r {} +
	rm -rf .pytest_cache .ruff_cache .anarres target
