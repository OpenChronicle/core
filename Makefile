.PHONY: help install dev-install clean lint format type test test-cov test-fast run build docs

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install production dependencies
	pip install -e .

dev-install:  ## Install development dependencies
	pip install -e ".[dev,api,llm]"
	pre-commit install

clean:  ## Clean build artifacts
	rm -rf build/ dist/ *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache/ .coverage htmlcov/

lint:  ## Run linting
	ruff check .
	black --check .
	mypy . --ignore-missing-imports
	bandit -r . --exclude tests/

format:  ## Format code
	black .
	ruff check --fix .

type:  ## Run type checking
	mypy . --ignore-missing-imports

test:  ## Run tests
	python -m ruff check .
	python -m black --check .
	python -m mypy .
	python -m bandit -r . --exclude tests/

test-fast:  ## Run tests without coverage
	python -m ruff check --fix .
	python -m black .
run:  ## Run the application
	python main.py
	python -m mypy .
build:  ## Build package
	python -m build
	python -m pytest
docs:  ## Build documentation
	echo "Documentation build not yet implemented"
	python -m pytest --cov=src --cov-report=term-missing --cov-report=html --cov-fail-under=85
# Development workflow shortcuts
fix: format lint  ## Format and lint code
	python -m openchronicle
full-check: lint type test-cov  ## Complete quality check

	python - <<'PY'
import os, shutil, pathlib
root = pathlib.Path('.')
for p in [root/'build', root/'dist', root/'.pytest_cache', root/'htmlcov']:
    shutil.rmtree(p, ignore_errors=True)
for p in root.rglob('__pycache__'):
    shutil.rmtree(p, ignore_errors=True)
for p in root.rglob('*.pyc'):
    try:
        p.unlink()
    except Exception:
        pass
for p in root.glob('*.egg-info'):
    shutil.rmtree(p, ignore_errors=True)
for p in [root/'.coverage']:
    try:
        p.unlink()
    except Exception:
        pass
PY
