# Getting Started

Glassbox is a local-first CLI agent harness with a live dashboard. It is built around an event-sourced runtime, a terminal-first operator experience, and replayable session history.

## Requirements

- Python 3.14
- [uv](https://docs.astral.sh/uv/)

## Install The Project

From the repository root:

```bash
uv sync
uv run pre-commit install
```

## Check The CLI

```bash
uv run glassbox --help
python -m glassbox --help
```

## Start The First Session

The default conversational entrypoint is `glassbox chat`.

```bash
uv run glassbox chat --cwd .
```

Or start with an initial prompt:

```bash
uv run glassbox chat "Inspect the repository" --cwd .
```

`chat` starts a new session, keeps the terminal attached to the live event stream, and by default also starts a co-hosted dashboard for the same session.

When dashboard startup succeeds, `chat` prints a URL like:

```text
http://127.0.0.1:8765/?session=SESSION_ID
```

Open that URL while the `chat` process is still running to watch the same session in the browser.

## Use The One-Shot CLI

If you want a one-shot command instead of the long-lived interactive shell, use `glassbox run`.

```bash
uv run glassbox run "Inspect the repository" --cwd .
```

Glassbox stores runtime state under `.glassbox/` in the selected workspace by default. The SQLite database lives at `.glassbox/glassbox.sqlite3` unless you override it with `--db-path`.

## Basic Commands

```text
glassbox run [PROMPT]
glassbox chat [PROMPT]
glassbox session attach SESSION_ID
glassbox session message SESSION_ID PROMPT
glassbox session answer SESSION_ID QUESTION_ID ANSWER
glassbox session resume SESSION_ID
glassbox session fork SESSION_ID [--turn TURN_ID] [--branch-label LABEL] [--prompt PROMPT]
glassbox session status SESSION_ID
glassbox replay run SESSION_ID [--json]
glassbox replay run --bundle BUNDLE_PATH [--json]
glassbox replay export SESSION_ID [OUTPUT]
glassbox eval run [CASE_ID ...] [--tag TAG] [--json] [--output-dir DIR]
glassbox eval audit [CASE_ID ...] [--profile PROFILE_ID] [--tag TAG] [--json]
glassbox eval profiles [--track deterministic|live-provider-canary] [--json]
glassbox eval report PROFILE_ID [PROFILE_ID ...] [--tag TAG] [--json] [--output-dir DIR]
glassbox eval promote SESSION_ID CASE_ID --title TITLE [...]
glassbox eval refresh CASE_ID SESSION_ID --reason REASON [...]
glassbox session approve SESSION_ID APPROVAL_ID
glassbox session deny SESSION_ID APPROVAL_ID
glassbox projection check [SESSION_ID | --all]
glassbox projection rebuild [SESSION_ID | --all]
glassbox serve
```

Use the dedicated guides for workflow detail:

- [interactive-workflows.md](./interactive-workflows.md)
- [dashboard.md](./dashboard.md)
- [branching.md](./branching.md)
- [replay-evals.md](./replay-evals.md)

## Local Validation

Baseline validation:

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
uv run glassbox eval run --tag smoke --cwd .
```

## Where To Go Next

- For the day-to-day operator shell, read [interactive-workflows.md](./interactive-workflows.md).
- For browser usage, read [dashboard.md](./dashboard.md).
- For replay and eval workflows, read [replay-evals.md](./replay-evals.md).
- For the architecture and persistence contracts, read [architecture.md](./architecture.md) and [database.md](./database.md).
