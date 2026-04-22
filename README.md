# Glassbox

Glassbox is a local-first CLI agent harness with a live dashboard.

This repository is being built incrementally from the architecture and task documents in [docs/architecture.md](docs/architecture.md), [docs/database.md](docs/database.md), and [docs/tasks.md](docs/tasks.md).

Glassbox currently provides:

- a persisted event-sourced runtime backed by SQLite
- a terminal-first CLI for running, resuming, inspecting, and recovering sessions
- a FastAPI dashboard with session snapshot and event stream endpoints
- approval, resume, replay, and projection rebuild workflows

## Requirements

- Python 3.14
- [uv](https://docs.astral.sh/uv/)

## Getting Started

Install the project and development tooling:

```bash
uv sync
uv run pre-commit install
```

Check that the CLI is available:

```bash
uv run glassbox --help
python -m glassbox --help
```

The current command surface is:

```text
glassbox run [PROMPT]
glassbox resume SESSION_ID
glassbox status SESSION_ID
glassbox approve SESSION_ID APPROVAL_ID
glassbox deny SESSION_ID APPROVAL_ID
glassbox rebuild [SESSION_ID | --all]
glassbox serve
```

## Basic CLI Usage

Start a session in the current workspace:

```bash
uv run glassbox run "Inspect the repository" --cwd .
```

Glassbox persists runtime state under `.glassbox/` in the selected workspace by default.
The SQLite database lives at `.glassbox/glassbox.sqlite3` unless you override it with `--db-path`.

Inspect a session from the terminal:

```bash
uv run glassbox status SESSION_ID --cwd .
```

The status view summarizes the current turn, pending approvals, recent tool activity,
recent turn metrics, transcript count, and the latest transcript message.

Resume a persisted session:

```bash
uv run glassbox resume SESSION_ID --cwd .
```

Resolve a pending approval:

```bash
uv run glassbox approve SESSION_ID APPROVAL_ID --cwd .
uv run glassbox deny SESSION_ID APPROVAL_ID --cwd .
```

Rebuild derived projections from canonical events:

```bash
uv run glassbox rebuild SESSION_ID --cwd .
uv run glassbox rebuild --all --cwd .
```

## Dashboard

Start the dashboard server:

```bash
uv run glassbox serve --cwd . --host 127.0.0.1 --port 8765
```

The command prints the dashboard URL before it blocks on the running server.

Open the dashboard shell in a browser with the target session ID:

```text
http://127.0.0.1:8765/?session=SESSION_ID
```

The dashboard reads a session snapshot from `GET /sessions/{session_id}` and then
subscribes to the live SSE stream at `GET /sessions/{session_id}/events`.

## Local Validation

Run the baseline local validation sequence with:

```bash
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run pytest
uv run pre-commit run --all-files
```

During incremental work, prefer narrower checks for the slice you touched. Examples:

```bash
uv run pytest tests/integration/test_cli_commands.py
uv run pytest tests/integration/test_web_session_snapshot.py
uv run ruff check src/glassbox/cli/__init__.py tests/integration/test_cli_commands.py
uv run ty check src/glassbox/cli/__init__.py
uv run pytest tests/test_import_smoke.py
```

## Reference Docs

- Architecture: [docs/architecture.md](docs/architecture.md)
- Database design: [docs/database.md](docs/database.md)
- Tool policy and approvals: [docs/tool-policy.md](docs/tool-policy.md)
- Roadmap and task graph: [docs/tasks.md](docs/tasks.md)
