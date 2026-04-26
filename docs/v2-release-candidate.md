# Glassbox v2 Release Candidate

This page is the operator and contributor summary for the Glassbox v2 release
candidate. It does not replace the detailed workflow guides; it names the
supported operating model, the validation path, and the boundaries that remain
deliberately out of scope for this milestone.

## Release Posture

Glassbox v2 is a local-first CLI agent harness with a live dashboard, a
workspace-scoped runtime owner, an event-sourced SQLite store, rebuildable
projections, replay-backed eval workflows, and portable session handoff.

The package entrypoint is `glassbox = "glassbox.cli:main"` from
[pyproject.toml](../pyproject.toml). The canonical command inventory is exposed
by:

```bash
uv run glassbox command tree
```

The release candidate keeps the v1 baseline intact while making long-lived local
use more deliberate: sessions are still event-sourced, replay remains
deterministic, and runtime ownership is explicit rather than inferred from a
terminal process.

## Supported Operating Model

- **Runtime ownership**: `glassbox session chat` owns a live session in the
  foreground; `glassbox daemon start` owns one workspace runtime in the
  background; `glassbox daemon status --json` is the scriptable discovery
  surface.
- **Operator console**: the dashboard root uses aggregate session data for
  priority queues, runtime health, projection health, and recent actionable
  sessions while direct `?session=...` links continue to open one session.
- **Recovery**: canonical events remain the source of truth. Use
  `glassbox projection check --all`, `glassbox projection rebuild --all`,
  `glassbox artifacts inspect`, and `glassbox backup create` for local recovery
  and audit workflows.
- **Policy and tools**: approval posture and richer tool policy stay local and
  inspectable through repository configuration and persisted policy outcomes.
- **Replay and eval**: `glassbox replay ...`, `glassbox eval run`,
  `glassbox eval recommend`, and `glassbox eval report` are the supported
  contributor workflows for deterministic regression evidence and release
  signoff artifacts.
- **Team handoff**: `glassbox session export` and `glassbox session import`
  create inspection-oriented portable packages without turning Glassbox into a
  remote multi-user service.
- **Observability**: `glassbox observability status --json` joins runtime
  health, event-stream reconnect/drop counters, projection lag, and retained
  eval summaries into one next-action report.
- **Performance budgets**: `glassbox performance budgets` prints explicit
  larger-session expectations and mitigation guidance.

## Primary Operator Flows

### Start And Inspect A Live Session

```bash
uv run glassbox session chat "Inspect the repository" --cwd .
uv run glassbox session status SESSION_ID --cwd .
```

The chat command starts a terminal-attached session and, by default, a co-hosted
dashboard. The status command reads persisted projections and summarizes current
turn state, pending approvals or questions, recent metrics, and next actions.

### Run A Persistent Workspace Runtime

```bash
uv run glassbox daemon start --cwd .
uv run glassbox daemon status --cwd . --json
uv run glassbox session attach SESSION_ID --cwd .
uv run glassbox daemon stop --cwd .
```

The daemon is the live mutation owner for the workspace. Local mutating commands
must respect that boundary instead of creating a second writer.

### Recover Or Audit Workspace State

```bash
uv run glassbox observability status --cwd . --json
uv run glassbox projection check --all --cwd .
uv run glassbox artifacts inspect --cwd . --json
uv run glassbox backup create .glassbox/backups/release-candidate.zip --cwd .
```

Use observability first when the question is broad: what is unhealthy, what
verification ran, and what should be inspected next? Use projection, artifact,
and backup commands for focused recovery or retention work.

### Verify A Change

```bash
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run pytest
uv run glassbox eval run --profile commit-smoke --cwd .
uv run glassbox eval recommend src/glassbox/runtime/observability.py --cwd .
```

For release evidence, use deterministic profiles and retained reports:

```bash
uv run glassbox eval report commit-smoke push-confirmation release-candidate \
  --output-dir .glassbox/evals/release-signoff \
  --cwd .
```

## Release-Readiness Checklist

Before treating a build as a Glassbox v2 release candidate, complete this list:

- `uv run glassbox command tree` matches the command inventory in
  [getting-started.md](./getting-started.md).
- `uv run glassbox observability status --json` returns runtime, projection,
  event transport, and verification sections with actionable next steps.
- `uv run glassbox performance budgets` prints explicit larger-session budgets.
- `uv run ruff format --check .`, `uv run ruff check .`, `uv run ty check`, and
  `uv run pytest` pass.
- `uv run pre-commit run --all-files` passes, including replay-backed evals.
- `uv run glassbox eval report ...` writes release-signoff artifacts for the
  selected deterministic profiles.
- Manual dashboard smoke: start `session chat`, open the printed dashboard URL,
  confirm the session inspector loads, then confirm the root dashboard lists the
  session in the appropriate queue.
- Manual daemon smoke: start the daemon, run `daemon status --json`, attach to an
  actionable session, and stop the daemon cleanly.
- Manual recovery smoke: run `projection check --all`, `artifacts inspect`, and a
  dry-run artifact prune before creating any backup artifact intended for
  retention.
- Docs hub links in [docs/README.md](./README.md) and the root
  [README.md](../README.md) point operators to the current v2 guides.

## Deliberate Non-Goals

The v2 release candidate does not introduce a hosted control plane, remote
multi-tenant orchestration, browser-native code editing, plugin marketplaces, or
blocking live-provider canaries. Those choices keep the release local-first,
inspectable, and deterministic where release evidence needs to be deterministic.

## Guide Map

- [getting-started.md](./getting-started.md): installation, command inventory,
  and validation basics
- [interactive-workflows.md](./interactive-workflows.md): terminal session flow
  and live versus historical attach semantics
- [persistent-runtime.md](./persistent-runtime.md): daemon operation and stale
  owner recovery
- [dashboard.md](./dashboard.md) and [operator-console.md](./operator-console.md):
  browser dashboard and v2 console model
- [database.md](./database.md): event store, projection rebuilds, artifacts, and
  workspace backup semantics
- [tool-policy.md](./tool-policy.md): approval and tool-governance model
- [replay-evals.md](./replay-evals.md): replay, eval, recommendation, and release
  signoff workflows
- [team-workflows.md](./team-workflows.md): local-first handoff and operator
  identity semantics
