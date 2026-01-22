# Conestoga

An Oregon Trail-inspired journey simulation with **Gemini 3 API** dynamic events, built with modern Python tooling.

## 🎮 Playable Game

A pygame-based prototype demonstrating structured Gemini 3 integration with validation pipelines and fallback behavior.

**Requirements:**
- Gemini 3 API (`gemini-3-flash-preview` or `gemini-3-pro-preview`)
- Python 3.12+
- GEMINI_API_KEY environment variable (optional - fallback mode available)

**Quick Start:**
```bash
uv sync
export GEMINI_API_KEY='your-key-here'  # Optional
conestoga
```

See [docs/QUICKSTART.md](docs/QUICKSTART.md) for detailed instructions and controls.

## Features

- **Gemini 3 API Integration**: Dynamic event generation using exclusively Gemini 3 models (preview APIs supported)
- **Structured Event Generation**: Schema-validated JSON outputs for deterministic gameplay
- **Deterministic Simulation**: Authoritative game state with invariant enforcement
- **Validation Pipeline**: Schema validation, item catalog checks, and safety filters with automatic fallback
- **UV Package Management**: Modern Python package manager for fast, reliable dependency resolution
- **Ontology Management**: RDF and OWL tools for semantic web applications (in `src/conestoga/`)
- **GCP Integration**: Google Cloud Storage client library
- **Environment Management**: Python-dotenv for configuration
- **Development Tools**: Makefile for common tasks

## Prerequisites

- Python 3.12+
- Gemini 3 API key (get one at [Google AI Studio](https://aistudio.google.com/))
- UV package manager (recommended)
- Node.js (for npm packages, optional)
- 1Password CLI (optional, for secrets management)
- GCP CLI (optional, for Google Cloud operations)

## Installation

### 1. Install UV

```bash
pip install uv
```

### 2. Install Dependencies

Using the Makefile:

```bash
make install-dev
```

Or manually:

```bash
# Install Python dependencies
uv sync

# Install Node.js dependencies
npm install
```

### 3. Configure Environment

Copy the example environment file and configure your settings:

```bash
cp .env.example .env
# Edit .env with your configuration
```

## Available Make Targets

- `make install` - Install Python dependencies using UV
- `make install-dev` - Install both Python and Node.js dependencies
- `make clean` - Remove build artifacts and caches
- `make test` - Run tests
- `make lint` - Run linters
- `make format` - Format code
- `make run` - Run the main application

## Python Dependencies

### Core Dependencies
- **python-dotenv**: Environment variable management
- **rdflib**: RDF library for working with semantic web data
- **owlrl**: OWL-RL and RDFS reasoning
- **google-cloud-storage**: Google Cloud Storage client

## Node.js Dependencies

### Development Tools
- **@gotalabs/cc-sdd**: Schema-driven development tools (install from GitHub)

## GCP Setup

To use Google Cloud Platform features:

1. Install the GCP CLI:
   ```bash
   # Follow instructions at https://cloud.google.com/sdk/docs/install
   ```

2. Authenticate:
   ```bash
   gcloud auth application-default login
   ```

3. Set your project:
   ```bash
   gcloud config set project YOUR_PROJECT_ID
   ```

4. Configure environment variables in `.env`:
   ```
   GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
   GCP_PROJECT_ID=your-project-id
   GCS_BUCKET_NAME=your-bucket-name
   ```

## 1Password Setup

For secrets management with 1Password:

1. Install 1Password CLI:
   ```bash
   # Follow instructions at https://developer.1password.com/docs/cli/get-started
   ```

2. Configure environment variables in `.env`:
   ```
   OP_SERVICE_ACCOUNT_TOKEN=your-token
   # OR
   OP_CONNECT_HOST=your-host
   OP_CONNECT_TOKEN=your-token
   ```

## Ontology Management

This project includes tools for working with RDF and OWL ontologies:

- **rdflib**: Parse, manipulate, and serialize RDF graphs
- **owlrl**: Perform OWL-RL and RDFS reasoning

Example usage:

```python
from rdflib import Graph
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create an RDF graph
g = Graph()
g.parse("your-ontology.ttl", format="turtle")

# Query the graph
for s, p, o in g:
    print(f"{s} {p} {o}")
```

## Development

### Running the Application

```bash
make run
# or
uv run python main.py
```

### Code Formatting

```bash
make format
```

### Linting

```bash
make lint
```

### Testing

```bash
make test
```

#### UI headless mode
- CI defaults to headless Pygame (`UI_HEADLESS=1` or `CI=1`). To force a visible window locally, run with `UI_HEADLESS=0`.

## Project Structure

```
conestoga/
├── .env.example        # Environment variable template
├── .gitignore          # Git ignore rules
├── .python-version     # Python version specification
├── Makefile            # Development task automation
├── main.py             # Main application entry point
├── package.json        # Node.js dependencies
├── pyproject.toml      # Python project configuration
├── uv.lock             # UV dependency lock file
└── README.md           # This file
```

## License

See LICENSE file for details.
