.PHONY: help install install-dev clean test lint format run

help:
	@echo "Available targets:"
	@echo "  install       - Install Python dependencies using UV"
	@echo "  install-dev   - Install Python and Node.js dependencies"
	@echo "  clean         - Remove build artifacts and caches"
	@echo "  test          - Run tests"
	@echo "  lint          - Run linters"
	@echo "  format        - Format code"
	@echo "  run           - Run the main application"

all: install-dev test lint

install:
	uv sync

install-dev:
	uv sync --all-extras
	-npm install

clean:
	rm -rf __pycache__ .pytest_cache .ruff_cache
	rm -rf build dist *.egg-info
	rm -rf .venv
	rm -rf node_modules
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

run:
	uv run python -m conestoga.main

# Build documentation and diagrams
build: mermaid-svg index docs stage

# DOCX Generation
docs:
	python3 scripts/convert_docs_to_docx_with_versioning.py

# Stage Artifacts
stage:
	uv build
	python3 scripts/stage_build_artifacts.py

# Repository search index
index:
	python3 scripts/build_repo_index.py

# Mermaid diagram generation
mermaid-svg:
	python3 scripts/convert_mermaid_to_svg.py

# Repository validation
validate:
	./scripts/validate_repo.sh

