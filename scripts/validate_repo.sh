#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export ROOT_DIR

echo "== Repo validation =="

echo "Ensuring dependencies via uv..."
uv sync --all-extras

if [[ ! -d "${ROOT_DIR}/.venv" ]]; then
  echo "Error: expected ${ROOT_DIR}/.venv after deps sync." >&2
  exit 1
fi

source "${ROOT_DIR}/.venv/bin/activate"

echo "Running lint check..."
uv run ruff check .

echo "Running type check..."
# Check if pyright is installed/configured, or use mypy if preferred.
# Providing a polite check.
if uv run pyright --version >/dev/null 2>&1; then
    uv run pyright
else
    echo "Skipping pyright (not found/configured)."
fi

echo "Running deterministic unit tests..."
uv run pytest

echo "Repo validation: OK"
