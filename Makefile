# =============================================================================
# AdsPower Bot Engine - Makefile
# =============================================================================
# Usage: make <target>
# =============================================================================

.PHONY: help install install-dev test test-fast test-cov lint format clean

# Default target
help:
	@echo "AdsPower Bot Engine - Available Commands"
	@echo "========================================="
	@echo ""
	@echo "Setup:"
	@echo "  make install       Install production dependencies"
	@echo "  make install-dev   Install development dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  make test          Run all tests"
	@echo "  make test-fast     Run tests (skip slow/integration)"
	@echo "  make test-cov      Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint          Run linter (ruff)"
	@echo "  make format        Format code (black)"
	@echo "  make check         Run all checks (lint + format check)"
	@echo ""
	@echo "Running:"
	@echo "  make api           Start API server"
	@echo "  make dashboard     Start dashboard"
	@echo "  make all           Start all services"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean         Remove generated files"

# =============================================================================
# Setup
# =============================================================================

install:
	pip install -r requirements.txt
	playwright install chromium

install-dev:
	pip install -r requirements-dev.txt
	playwright install chromium

# =============================================================================
# Testing
# =============================================================================

test:
	pytest tests/ -v --tb=short

test-fast:
	pytest tests/ -v --tb=short -m "not slow and not integration"

test-cov:
	pytest tests/ -v --tb=short --cov=src --cov-report=html --cov-report=term-missing
	@echo "Coverage report generated in htmlcov/"

test-integration:
	pytest tests/ -v --tb=short -m "integration"

# =============================================================================
# Code Quality
# =============================================================================

lint:
	ruff check src/ tests/

lint-fix:
	ruff check src/ tests/ --fix

format:
	black src/ tests/

format-check:
	black --check --diff src/ tests/

check: lint format-check
	@echo "All checks passed!"

typecheck:
	mypy src/ --ignore-missing-imports

# =============================================================================
# Running Services
# =============================================================================

api:
	python -m src.api.server

dashboard:
	cd dashboard && npm run dev

all:
	./scripts/start_all.sh

# =============================================================================
# Cleanup
# =============================================================================

clean:
	rm -rf __pycache__ .pytest_cache .coverage htmlcov/ .ruff_cache
	rm -rf src/__pycache__ tests/__pycache__
	rm -rf src/**/__pycache__
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

clean-all: clean
	rm -rf venv/ node_modules/ dashboard/node_modules/ dashboard/dist/
	rm -rf data/*.db logs/*.log
