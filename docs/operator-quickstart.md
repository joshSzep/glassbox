# Operator Quickstart

This guide is the short daily path for a new Glassbox operator. It assumes a
local checkout and keeps release-candidate evidence out of the first-run flow.

## 1. Install

From the repository root:

```bash
uv sync
uv run pre-commit install
```

Check that the CLI is available:

```bash
uv run glassbox --help
uv run glassbox command tree
uv run glassbox command guide
```

Run the first-run readiness check before starting a session:

```bash
uv run glassbox readiness check --cwd .
```

The readiness report checks runtime imports, workspace and `.glassbox/`
writability, SQLite bootstrap, workspace profile defaults, provider posture,
packaged dashboard assets, repository index freshness, eval profile
availability, package/build posture, and tool policy. Warnings include concrete
remediation commands, and missing provider credentials do not block
deterministic local smoke. For shared team defaults, use the manual,
test-driven, release-candidate, offline deterministic, or conservative
provider-backed templates in [workspace-profiles.md](./workspace-profiles.md).

## 2. Configure An Optional Provider

Glassbox can run deterministic local checks without live provider credentials.
For provider-backed sessions, set credentials in the shell or a local `.env`
file at the workspace root, then run diagnostics:

```bash
uv run glassbox provider diagnostics --cwd .
```

Provider diagnostics are redacted and advisory. Missing credentials should not
block replay, eval, docs work, or package smoke.

## 3. Start Chat

Start the terminal-first workflow:

```bash
uv run glassbox session chat --cwd .
```

Or start with a prompt:

```bash
uv run glassbox session chat "Inspect the repository and summarize the test layout." --cwd .
```

The terminal session is the primary operator surface. It shows the active
workspace, model posture, pending questions, pending approvals, cancellation
state, and the paired dashboard URL when the dashboard is available. On startup,
`session chat` prints a compact summary with the model, approval behavior,
autonomy budget, workspace, database path, dashboard posture, provider posture,
and a couple of first-prompt ideas when you did not pass an initial prompt.

## 4. Inspect The Dashboard

`session chat` prints a local dashboard URL shaped like:

```text
http://127.0.0.1:8765/?session=SESSION_ID
```

Open it while the session is running to inspect the transcript, pending
actions, task state, evidence, memory, repository index posture, branch-search
results, and recovery cues. The dashboard is a cockpit for inspection and
decisions; the terminal remains the simplest place to converse.

## 5. Approve, Deny, Or Answer

When Glassbox needs operator input, use the terminal action UI or explicit CLI
commands:

```bash
uv run glassbox session status SESSION_ID
uv run glassbox session answer SESSION_ID QUESTION_ID "Use the smaller scope."
uv run glassbox session approve SESSION_ID APPROVAL_ID
uv run glassbox session deny SESSION_ID APPROVAL_ID
```

Approvals are explicit local decisions. Denials and answers become part of the
session evidence.

## 6. Verify Work

Use the narrowest useful check for the change:

```bash
uv run glassbox eval recommend PATH
uv run glassbox eval run --profile commit-smoke --cwd .
uv run pytest tests/unit/test_specific_module.py
uv run ruff check src/glassbox/path.py tests/path_test.py
```

For dashboard or generated API changes, use the frontend checks documented in
[frontend-development.md](./frontend-development.md). For release-candidate
evidence, switch to [replay-evals.md](./replay-evals.md) and the Release
Evidence section in [README.md](./README.md).

## 7. Continue Or Recover

Use these commands when ordinary work needs inspection or recovery:

```bash
uv run glassbox observability status --cwd .
uv run glassbox daemon status --cwd .
uv run glassbox task list --cwd .
uv run glassbox job list --cwd .
uv run glassbox repo index status --cwd .
uv run glassbox artifacts inspect --cwd .
uv run glassbox projection check --all --cwd .
```

If state looks stale or degraded, start with read-only status commands before
running mutating recovery commands.

When the surface area feels broad, use the workflow guide instead of guessing:

```bash
uv run glassbox command guide
uv run glassbox command guide --json
```

The guide groups the daily inspection and recovery paths for long-run recovery,
compaction, tool attempts, checkpoint inspection, verification recommendations,
provider posture, knowledge freshness, branch-search review, workspace
recovery, and release evidence.

## Next Guides

- [interactive-workflows.md](./interactive-workflows.md) for terminal chat,
  attach, actions, cancellation, and session control
- [dashboard.md](./dashboard.md) for dashboard inspection
- [tool-policy.md](./tool-policy.md) for approval and command policy
- [verification-loops.md](./verification-loops.md) for verify-repair behavior
- [replay-evals.md](./replay-evals.md) for replay and eval evidence
