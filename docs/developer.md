# Conestoga Developer Guide

## Setup

### Prerequisites

- Python 3.12+
- `uv` (Universal Python Packaging) - Recommended
  - Install: `curl -LsSf https://astral.sh/uv/install.sh | sh`

### Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/energration/conestoga.git
    cd conestoga
    ```

2. Install dependencies:

    ```bash
    uv sync
    # Or classic pip: pip install -r requirements.txt (if generated)
    ```

3. Set up environment variables:
    - Create `.env` from `.env.example`.
    - Add your `GEMINI_API_KEY` (Get one from Google AI Studio).

## Project Structure

- `src/conestoga/`: Main application source code.
  - `game/`: Core game logic (`runner.py`, `state.py`, `ui.py`).
  - `events.py`: Event definitions and schemas.
  - `gemini_gateway.py`: Interface to Gemini API.
- `tests/`: Pytest suite.
- `assets/`: Images, audio, and data files.
- `scripts/`: Utility scripts for devops and verification.
- `.kiro/`: Kiro Spec-Driven Development artifacts.

## Development Workflow

1. **Run the Game**:

    ```bash
    uv run python -m conestoga.main
    ```

2. **Run Tests**:

    ```bash
    uv run pytest
    ```

3. **Linting**:

    ```bash
    uv run ruff check .
    uv run ruff format .
    ```

## Contribution Guidelines

1. **Spec-Driven**: Use `.kiro` specs for major features. Start with a Spec Design compatible with Kiro tools.
2. **Pull Requests**:
    - Create a feature branch.
    - Ensure all tests pass.
    - Include updated documentation if necessary.
3. **Code Style**: Follow PEP 8 (enforced by `ruff`).
