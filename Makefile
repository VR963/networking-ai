.PHONY: help install install-dev test test-cov lint format type-check clean build docs

help:
	@echo "Networking AI - Development Commands"
	@echo ""
	@echo "Available commands:"
	@echo "  make install       Install production dependencies"
	@echo "  make install-dev   Install development dependencies"
	@echo "  make test          Run tests"
	@echo "  make test-cov      Run tests with coverage report"
	@echo "  make lint          Check code style with ruff"
	@echo "  make format        Format code with black"
	@echo "  make type-check    Run type checking with mypy"
	@echo "  make check         Run all checks (format, lint, type-check, test)"
	@echo "  make clean         Remove build artifacts and cache files"
	@echo "  make build         Build distribution packages"
	@echo "  make docs          Generate documentation"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt
	pre-commit install

test:
	pytest

test-cov:
	pytest --cov=networking_ai --cov-report=html --cov-report=term

lint:
	ruff check src/ tests/

format:
	black src/ tests/
	ruff check --fix src/ tests/

type-check:
	mypy src/

check: format lint type-check test
	@echo "All checks passed!"

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean
	python -m build

docs:
	@echo "Documentation generation coming soon..."
