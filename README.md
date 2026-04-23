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
glassbox chat [PROMPT]
glassbox attach SESSION_ID
glassbox message SESSION_ID PROMPT
glassbox answer SESSION_ID QUESTION_ID ANSWER
glassbox resume SESSION_ID
glassbox status SESSION_ID
glassbox approve SESSION_ID APPROVAL_ID
glassbox deny SESSION_ID APPROVAL_ID
glassbox rebuild [SESSION_ID | --all]
glassbox serve
```

## Interactive Terminal Workflow

Use `glassbox chat` as the default conversational entrypoint. It starts a new
session, keeps a live event subscription open in the terminal, and lets you keep
working in the same shell instead of restarting the CLI for every turn.

By default, `chat` also starts a co-hosted dashboard in the same process. Use
`--no-dashboard` to keep the session terminal-only, or `--dashboard-host` and
`--dashboard-port` to override the dashboard bind target.

```bash
uv run glassbox chat --cwd .
```

Or start with an initial prompt:

```bash
uv run glassbox chat "Inspect the repository" --cwd .
```

Inside an interactive session:

- freeform text sends the next prompt while the session is idle and running
- freeform text answers the pending `ask_user` question when the session is awaiting user input
- `/approve` and `/deny` resolve a pending approval without requiring the approval ID
- `/status`, `/help`, and `/exit` remain available as explicit control commands

The prompt context changes with the session state, so the terminal will tell you
whether it expects a new prompt, an `ask_user` answer, or an approval decision.

### Example: Start And Continue In One Terminal

```bash
uv run glassbox chat "Inspect the repository" --cwd .
```

Then continue in the same terminal session:

```text
prompt> Now summarize the tests.
prompt> /status
prompt> /exit
```

### Example: Reopen An Actionable Session

Use `glassbox attach` when you already have a persisted session ID and want to
continue the operator workflow in a terminal.

```bash
uv run glassbox attach SESSION_ID --cwd .
```

`attach` is for sessions that are actionable from the operator side:

- idle running sessions waiting for the next prompt
- sessions awaiting `ask_user` input
- sessions awaiting approval resolution

Typical attach flow for a paused session:

```bash
uv run glassbox status SESSION_ID --cwd .
uv run glassbox attach SESSION_ID --cwd .
```

If the session is waiting on `ask_user`, the next freeform entry is treated as
the answer. If the session is waiting on approval, freeform text is blocked and
you must use `/approve` or `/deny`.

### Scope Boundary

The interactive terminal UX is intentionally process-local in v1. `chat` owns
the live in-process event stream for the session it started, and `attach` can
reopen a persisted actionable session later, but Glassbox does not yet claim to
stream live terminal output from another already-running process or a daemon-
backed resident agent. For cross-process observation, use the dashboard.

## CLI Primitives

Start a session in the current workspace:

```bash
uv run glassbox run "Inspect the repository" --cwd .
```

Use the one-shot commands when you want scripting, recovery, or explicit state-
driven control instead of a long-lived conversational shell.

Glassbox persists runtime state under `.glassbox/` in the selected workspace by default.
The SQLite database lives at `.glassbox/glassbox.sqlite3` unless you override it with `--db-path`.

Inspect a session from the terminal:

```bash
uv run glassbox status SESSION_ID --cwd .
```

The status view summarizes the current turn, pending approvals, recent tool activity,
recent turn metrics, transcript count, the latest transcript message, and the
next valid operator action for the session's current state.

Resume a persisted session:

```bash
uv run glassbox resume SESSION_ID --cwd .
```

Submit another user prompt into an existing running session:

```bash
uv run glassbox message SESSION_ID "Continue with the next step" --cwd .
```

Answer a pending `ask_user` question for a suspended session:

```bash
uv run glassbox answer SESSION_ID QUESTION_ID "blue" --cwd .
```

When a session pauses for input, the CLI prints a `Question asked (...)` line with
the `QUESTION_ID` you need for the `answer` command.

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

## Multi-Turn Workflow

Prefer `glassbox chat` and `glassbox attach` for human-driven multi-turn work.
Use the lower-level commands below when you need to drive a specific session
state explicitly from scripts, recovery flows, or precise operator steps.

Use the command that matches the session's current actionable state:

- `glassbox chat [PROMPT]` starts a new long-lived terminal session for follow-up prompts without restarting the CLI each turn.
- `glassbox attach SESSION_ID` reopens an actionable persisted session in the interactive terminal workflow.
- `glassbox resume SESSION_ID` replays a persisted session after restart. It does not send a new prompt.
- `glassbox message SESSION_ID PROMPT` sends a fresh user prompt when the session is running and idle.
- `glassbox answer SESSION_ID QUESTION_ID ANSWER` answers a pending `ask_user` question when the session is awaiting user input.
- `glassbox approve SESSION_ID APPROVAL_ID` or `glassbox deny SESSION_ID APPROVAL_ID` resolves a pending approval when the session is awaiting approval.
- `glassbox status SESSION_ID` prints the current session state, any pending approval or question identifiers, and a `Next action:` line that tells you which of the commands above is valid now.

Inside interactive `chat` and `attach` sessions:

- freeform text sends the next prompt when the session is idle and running
- freeform text answers the pending `ask_user` question when the session is awaiting user input
- `/approve` and `/deny` resolve a pending approval without requiring the approval ID
- `/status`, `/help`, and `/exit` remain available as explicit control commands

In the dashboard, the same workflow is split by pane:

- The `Next Action` pane sends a new prompt for an idle running session.
- The `Next Action` pane switches into answer mode when the model is waiting on `ask_user` input.
- The `Pending Approvals` pane remains the only place to resolve approval-gated tool actions.

`resume`, `message`, `answer`, `approve`, and `deny` remain important even with
interactive mode available. They are the low-level primitives for scripting,
recovery after process restart, explicit operator control, and workflows where a
long-lived terminal session is not the right interface.

## Real Provider Setup

Glassbox can run against real OpenAI and Anthropic providers when provider
credentials are available in the runtime environment.

Supported provider-qualified model names for real provider execution are:

- `openai:...`
- `anthropic:...`

If no provider runtime config is present, Glassbox keeps using the deterministic
local executor path for offline development and tests.

Set credentials in your shell environment:

```bash
export OPENAI_API_KEY="..."
uv run glassbox run "Inspect the repository" --cwd . --model-name openai:gpt-5.4
```

Or use Anthropic:

```bash
export ANTHROPIC_API_KEY="..."
uv run glassbox run "Inspect the repository" --cwd . --model-name anthropic:claude-sonnet-4
```

Glassbox also reads an optional `.env` file from the selected runtime workspace
root, which is the path you pass through `--cwd`.

```dotenv
OPENAI_API_KEY=...
OPENAI_BASE_URL=https://api.openai.com/v1
```

Process environment variables override values from `.env`.

More detail, including all supported variables and troubleshooting, is in
[docs/providers.md](docs/providers.md).

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
- Provider setup and secrets: [docs/providers.md](docs/providers.md)
- Tool policy and approvals: [docs/tool-policy.md](docs/tool-policy.md)
- Roadmap and task graph: [docs/tasks.md](docs/tasks.md)
