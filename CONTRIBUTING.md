# Contributing to Synapse

Thanks for your interest in contributing! This guide will help you get set up and make your first contribution.

## Development setup

```bash
# Clone the repo
git clone https://github.com/alexjsmith0115/synapse.git
cd synapse

# Create a virtual environment and install
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running tests

```bash
# Unit tests (no external dependencies)
pytest tests/unit/ -v

# Integration tests (requires Docker + Memgraph)
docker compose up -d
pytest tests/integration/ -v -m integration
```

Unit tests should always pass before submitting a PR. Integration tests require Docker and a running Memgraph instance.

## Making changes

1. Fork the repo and create a branch from `main`
2. Make your changes
3. Add or update tests for your changes
4. Run `pytest tests/unit/ -v` and ensure all tests pass
5. Commit with a clear message describing *why*, not just *what*
6. Open a pull request against `main`

## Code style

- Python 3.11+ with type annotations on all function signatures
- Double quotes for strings
- 4-space indentation
- `from __future__ import annotations` in every source file
- Comments explain *why*, not *what* — keep them sparse
- Classes and functions should be small with a single responsibility

## Project structure

- `src/synapse/` — main application code
- `src/solidlsp/` — LSP process management library
- `tests/unit/` — unit tests (no external dependencies)
- `tests/integration/` — integration tests (require Docker + Memgraph)

## Reporting bugs

Open an issue using the **Bug Report** template. Include reproduction steps, expected vs actual behavior, and your environment details.

## Suggesting features

Open an issue using the **Feature Request** template. Describe the problem you're solving and your proposed approach.
