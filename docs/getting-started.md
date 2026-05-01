# Getting Started

Glassbox is a local-first CLI agent harness with a live dashboard. It is built around an event-sourced runtime, a terminal-first operator experience, and replayable session history.

## Requirements

- Python 3.14
- [uv](https://docs.astral.sh/uv/)
- Node.js 24 and pnpm through Corepack for v3 SPA development and validation

Installed-package users do not need Node.js or pnpm at runtime. The release
wheel includes the static dashboard assets and the full-screen terminal client.

## Install The Project

From the repository root:

```bash
uv sync
corepack enable
pnpm --dir frontend install --frozen-lockfile
uv run pre-commit install
```

## Check The CLI

```bash
uv run glassbox --help
python -m glassbox --help
```

## First-Run Provider And Profile Setup

Run provider diagnostics before the first live-provider session. Diagnostics are
offline and redacted; they show the selected model source, provider family,
credential posture, advisory canary readiness, and next actions.

```bash
uv run glassbox provider diagnostics --cwd . --model-name openai:gpt-5.4
uv run glassbox provider diagnostics --cwd . --json
```

Use environment variables or `.env` at the selected `--cwd` for provider
credentials. Keep reviewable defaults, never secrets, in `glassbox.profile.json`:

```json
{
  "profile_version": 1,
  "runtime": {
    "model_name": "openai:gpt-5.4",
    "approval_mode": "confirm"
  },
  "verification": {
    "eval_profile": "commit-smoke"
  }
}
```

After the first session starts, the terminal header and command palette show the
paired dashboard URL. Use the local eval profile as the smallest repository
validation check:

```bash
uv run glassbox session chat --cwd .
uv run glassbox eval run --profile commit-smoke --cwd .
```

## Start The First Session

The default conversational entrypoint is `glassbox session chat`. In a supported
interactive terminal, it opens the full-screen Glassbox chat UI.

```bash
uv run glassbox session chat --cwd .
```

Or start with an initial prompt:

```bash
uv run glassbox session chat "Inspect the repository" --cwd .
```

`session chat` starts a new session, keeps the terminal attached to the live event stream, and by default also starts a co-hosted dashboard for the same session. The terminal is the primary chat surface: write prompts in the composer, read assistant output in the transcript, use the action strip for approvals or questions, and open the command palette for dashboard and session handoffs.

The dashboard URL is shown in the terminal header and is available from the command palette. It looks like:

```text
http://127.0.0.1:8765/?session=SESSION_ID
```

Open that URL while the `session chat` process is still running to watch the same session in the browser. The dashboard is paired with terminal chat for deeper inspection; it is not required for ordinary prompting.

If stdin/stdout are redirected, the terminal is too limited, or a CI-like environment is detected, an implicit `session chat` launch falls back to the retained plain line-mode loop. Use `--plain` to request that compatibility mode deliberately, or `--tui` to require the full-screen app and fail if it cannot launch.

## Use The One-Shot CLI

If you want a one-shot command instead of the long-lived terminal chat, use `glassbox session run`.

```bash
uv run glassbox session run "Inspect the repository" --cwd .
```

Glassbox stores runtime state under `.glassbox/` in the selected workspace by default. The SQLite database lives at `.glassbox/glassbox.sqlite3` unless you override it with `--db-path`.

## Basic Commands

```text
glassbox command tree
glassbox observability status [--json]
glassbox performance budgets
glassbox session run [PROMPT]
glassbox session chat [PROMPT]
glassbox session list [--status STATUS] [--limit N] [--json]
glassbox session attach SESSION_ID
glassbox session message SESSION_ID PROMPT
glassbox session cancel SESSION_ID [--turn TURN_ID] [--reason REASON]
glassbox session answer SESSION_ID QUESTION_ID ANSWER
glassbox session approve SESSION_ID APPROVAL_ID
glassbox session deny SESSION_ID APPROVAL_ID
glassbox session resume SESSION_ID
glassbox session fork SESSION_ID [--turn TURN_ID] [--branch-label LABEL] [--prompt PROMPT]
glassbox session status SESSION_ID
glassbox session export SESSION_ID [OUTPUT]
glassbox session import PACKAGE
glassbox replay run SESSION_ID [--json]
glassbox replay bundle export SESSION_ID [OUTPUT]
glassbox replay bundle inspect BUNDLE_PATH [--json]
glassbox replay bundle run BUNDLE_PATH [--json]
glassbox eval run [CASE_ID ...] [--tag TAG] [--json] [--output-dir DIR]
glassbox eval audit [CASE_ID ...] [--profile PROFILE_ID] [--tag TAG] [--json]
glassbox eval profile list [--track deterministic|live-provider-canary] [--json]
glassbox eval profile show PROFILE_ID [--json]
glassbox eval recommend PATH [PATH ...] [--json]
glassbox eval report PROFILE_ID [PROFILE_ID ...] [--tag TAG] [--json] [--output-dir DIR]
glassbox eval case list [--tag TAG] [--json]
glassbox eval case show CASE_ID [--json]
glassbox eval case promote CASE_ID SESSION_ID --title TITLE [...]
glassbox eval case refresh CASE_ID SESSION_ID --reason REASON [...]
glassbox artifacts inspect [--max-age-days DAYS] [--json]
glassbox artifacts prune [--dry-run] [--max-age-days DAYS] [--json]
glassbox backup create [OUTPUT] [--json]
glassbox backup inspect ARCHIVE [--json]
glassbox backup restore ARCHIVE [--force] [--json]
glassbox projection check [SESSION_ID | --all]
glassbox projection rebuild [SESSION_ID | --all]
glassbox provider diagnostics [--model-name MODEL] [--json]
glassbox provider canary run [--scenario SCENARIO] [--output-dir DIR] [--json]
glassbox dashboard serve
glassbox daemon start
glassbox daemon status [--json]
glassbox daemon stop
```

Use the dedicated guides for workflow detail:

- [v2-release-candidate.md](./v2-release-candidate.md)
- [interactive-workflows.md](./interactive-workflows.md)
- [dashboard.md](./dashboard.md)
- [branching.md](./branching.md)
- [replay-evals.md](./replay-evals.md)

## Local Validation

For quick backend iteration, use the marker-filtered fast local pytest loop:

```bash
uv run pytest -m "not daemon and not subprocess and not timeout and not tui and not slow"
```

Baseline validation:

```bash
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run pytest
uv run pre-commit run --all-files
```

The unfiltered `uv run pytest` command is the full-confidence pytest check. It
intentionally includes daemon, subprocess, timeout, TUI, slow, and release-gate
coverage. The marker-filtered command is for local speed, not release
sign-off.

Frontend-only validation:

```bash
pnpm --dir frontend format:check
pnpm --dir frontend lint
pnpm --dir frontend typecheck
pnpm --dir frontend test
pnpm --dir frontend build
pnpm --dir frontend test:e2e
```

Use the frontend-only checks when your change is limited to the SPA, generated frontend API types, or frontend documentation. Use `uv run pre-commit run --all-files` before pushing cross-cutting changes or when backend contracts, generated OpenAPI output, replay/eval behavior, or the production static export path may be affected.

During incremental work, prefer narrower checks for the slice you touched. Examples:

```bash
uv run pytest tests/integration/test_cli_commands.py
uv run pytest tests/integration/test_web_session_snapshot.py
uv run ruff check src/glassbox/cli/__init__.py tests/integration/test_cli_commands.py
uv run ty check src/glassbox/cli/__init__.py
uv run glassbox eval run --tag smoke --cwd .
```

Release-candidate validation adds packaged-dashboard, installed-wheel,
deterministic eval, dependency/toolchain, provider-canary, and manual QA
evidence. Use the v10 release gate and evidence guides when preparing the
current release line:

```bash
uv run python scripts/validate_v10_release_gate.py
```

Manual release notes and screenshots belong under `.glassbox/releases/...` using
the convention in [manual-qa-evidence-v6.md](./manual-qa-evidence-v6.md).

## Where To Go Next

- For the day-to-day full-screen chat workflow, read [interactive-workflows.md](./interactive-workflows.md).
- For the v6 release-candidate operating model and validation path, read [v6-release-candidate.md](./v6-release-candidate.md).
- For the supported v2 operating model and release checklist, read [v2-release-candidate.md](./v2-release-candidate.md).
- For browser usage, read [dashboard.md](./dashboard.md).
- For replay and eval workflows, read [replay-evals.md](./replay-evals.md).
- For provider setup and advisory canaries, read [providers.md](./providers.md).
- For v6 release evidence and installed-package expectations, read [release-packaging.md](./release-packaging.md) and [v6-release-hardening.md](./v6-release-hardening.md).
- For the architecture and persistence contracts, read [architecture.md](./architecture.md) and [database.md](./database.md).
