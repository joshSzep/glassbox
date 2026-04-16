# Glassbox

Glassbox is a local-first CLI agent harness with a live dashboard.

This repository is being built incrementally from the architecture and task documents in [docs/architecture.md](docs/architecture.md), [docs/database.md](docs/database.md), and [docs/tasks.md](docs/tasks.md).

## Current State

The project is at the initial Python package scaffold stage.

## Development

Install the project with `uv sync`, then run the package entrypoint with `uv run glassbox`.

Install git hooks with `uv run pre-commit install`.

## Local Validation

Run the baseline local validation sequence with:

```bash
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run pytest
uv run pre-commit run --all-files
```

For a narrow test execution path during iteration, use:

```bash
uv run pytest tests/test_import_smoke.py
```
