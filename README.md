# Glassbox

<p align="center">
  <img src="glassbox.png" alt="Glassbox" width="640" />
</p>

Glassbox is a local-first CLI agent harness with a live dashboard.

It is built for operator-visible agent workflows: terminal-first sessions, event-sourced runtime state, approval-gated tools, live browser inspection, branchable history, and replay-backed regression contracts.

## Why Glassbox

- local-first runtime state backed by SQLite
- terminal-first operator workflow with a live dashboard
- event-sourced sessions that can be resumed, inspected, and rebuilt
- approval and `ask_user` suspension paths with explicit operator control
- historical branching without mutating parent session history
- replay and eval workflows for portable behavioral regression baselines
- portable session handoff and repository-owned workspace defaults for teams

## Quick Start

Requirements:

- Python 3.14
- [uv](https://docs.astral.sh/uv/)

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

Check whether the workspace is ready for a useful first session:

```bash
uv run glassbox readiness check --cwd .
```

Start the default interactive workflow:

```bash
uv run glassbox session chat --cwd .
```

Or start with an initial prompt:

```bash
uv run glassbox session chat "Inspect the repository" --cwd .
```

By default, `chat` also starts a co-hosted dashboard and prints a session-specific browser URL like:

```text
http://127.0.0.1:8765/?session=SESSION_ID
```

If you want a one-shot command instead of the long-lived interactive shell:

```bash
uv run glassbox session run "Inspect the repository" --cwd .
```

## Core Workflows

Use Glassbox in a few distinct modes:

- interactive terminal work with `chat` and `attach`
- explicit state-driven control with `message`, `answer`, `approve`, `deny`, `resume`, and `status`
- browser-based inspection and action through the dashboard
- historical branching with `fork`
- portable handoff with `session export` and inspection-only `session import`
- repository defaults through `glassbox.profile.json`
- replay and eval verification with `replay run`, `replay bundle export`, and `eval`

Persistence is local to the selected workspace by default. Glassbox stores runtime state under `.glassbox/`, with the SQLite database at `.glassbox/glassbox.sqlite3` unless you override `--db-path`.

Glassbox team workflows remain local-first. A foreground `session chat` process or workspace daemon owns live mutation for one workspace, while session custody and handoff metadata are operator guidance rather than cloud authority or multi-user access control.

## Current Baseline

The current public baseline is v9. It carries forward the v8 release-candidate
decision as a concise product contract for sessions, tasks, evidence, memory,
branches, and verification while keeping provider canaries advisory and
deterministic replay/eval evidence authoritative.

Start with [docs/v9-public-baseline.md](docs/v9-public-baseline.md) for the
supported product model, then use
[docs/operator-quickstart.md](docs/operator-quickstart.md) for the short daily
path from install to chat, dashboard inspection, approvals, and verification.
Version and release-candidate naming policy lives in
[docs/version-release-policy.md](docs/version-release-policy.md).

## Documentation

The root README is the shortest path into the project. The detailed operator,
reference, release-evidence, and implementation-history docs live in
[docs/README.md](docs/README.md).

Start here based on what you need:

- [docs/v9-public-baseline.md](docs/v9-public-baseline.md)
- [docs/operator-quickstart.md](docs/operator-quickstart.md)
- [docs/daily-workflow-quickstart.md](docs/daily-workflow-quickstart.md)
- [docs/getting-started.md](docs/getting-started.md)
- [docs/interactive-workflows.md](docs/interactive-workflows.md)
- [docs/dashboard.md](docs/dashboard.md)
- [docs/branching.md](docs/branching.md)
- [docs/replay-evals.md](docs/replay-evals.md)
- [docs/runtime-context.md](docs/runtime-context.md)
- [docs/team-workflows.md](docs/team-workflows.md)
- [docs/workspace-profiles.md](docs/workspace-profiles.md)
- [docs/providers.md](docs/providers.md)
- [docs/tool-policy.md](docs/tool-policy.md)
- [docs/architecture.md](docs/architecture.md)
- [docs/database.md](docs/database.md)
- [docs/refactor-boundaries.md](docs/refactor-boundaries.md)

Release evidence and milestone history remain available when you need them:

- [docs/v8-release-candidate.md](docs/v8-release-candidate.md)
- [docs/v7-release-candidate.md](docs/v7-release-candidate.md)
- [docs/v6-release-candidate.md](docs/v6-release-candidate.md)
- [docs/v2-release-candidate.md](docs/v2-release-candidate.md)
- [docs/tasks-v9.md](docs/tasks-v9.md)
- [docs/tasks-v8.md](docs/tasks-v8.md)
- [docs/tasks-v7.md](docs/tasks-v7.md)
- [docs/tasks-v6.md](docs/tasks-v6.md)

## Local Validation

Run the baseline local validation sequence with:

```bash
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run pytest
uv run pre-commit run --all-files
```

For replay-backed regression checks, use the focused eval guide in [docs/replay-evals.md](docs/replay-evals.md).
