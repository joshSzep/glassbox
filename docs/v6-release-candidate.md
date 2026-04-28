# Glassbox v6 Release Candidate

This page is the operator and contributor guide for the Glassbox v6 release
candidate. It names the supported operating model, release validation path,
manual evidence expectations, known residual risks, and non-goals without
requiring readers to inspect the task graph.

## Release Posture

Glassbox v6 hardens the local-first agent workflow around a full-screen terminal
client, paired dashboard, explicit runtime ownership, real cancellation,
deterministic replay/eval evidence, reproducible packages, and retained release
artifacts.

The canonical command inventory is exposed by:

```bash
uv run glassbox command tree
```

The objective release-candidate gate is:

```bash
uv run python scripts/validate_v6_release_gate.py
```

The current candidate evidence path used during Phase 70 is:

```text
.glassbox/releases/gbx-701-automated-gate/
```

That directory contains `summary.json`, `manual-validation.md`, and provider
canary evidence. It is local workspace state and is not committed to git.

## Supported Operating Model

- **Terminal chat**: `glassbox session chat` launches the full-screen TUI by
  default in supported interactive terminals. `--plain` remains the explicit
  compatibility path, and strict `--tui` fails clearly when the TUI cannot run.
- **Dashboard**: `session chat` starts a co-hosted dashboard by default, while
  `glassbox dashboard serve` runs the standalone operator console. Installed
  packages serve the dashboard from packaged static assets without Node.js.
- **Runtime ownership**: a foreground chat process or `glassbox daemon start`
  owns live mutation for one workspace. `glassbox session attach SESSION_ID`
  reconnects to healthy daemon-owned sessions or reopens persisted actionable
  sessions honestly.
- **Cancellation**: `glassbox session cancel SESSION_ID` records cancellation as
  persisted event evidence. Replay and eval treat intentional cancellation as a
  cancellation outcome, not as a generic timeout.
- **Replay/eval**: deterministic eval profiles remain the release authority.
  Advisory live-provider canaries may be retained, but they do not replace
  deterministic signoff.
- **Provider diagnostics**: `glassbox provider diagnostics` reports redacted
  provider runtime configuration. `glassbox provider canary run` records
  advisory canary evidence when credentials are available.
- **Recovery**: observability, projection, artifacts, backup, replay/eval,
  daemon, and installed-dashboard workflows have explicit recovery commands and
  manual evidence.
- **Release evidence**: automated and manual evidence lives under one
  `.glassbox/releases/...` directory per candidate.

## Primary Operator Flows

### Start A Terminal-First Session

```bash
uv run glassbox session chat "Inspect the repository" --cwd .
```

The terminal is the primary conversation surface. Use the dashboard URL from the
TUI header or command palette when you need queue, lineage, evidence, replay, or
runtime details in the browser.

### Reattach Through A Workspace Daemon

```bash
uv run glassbox daemon start --cwd .
uv run glassbox daemon status --cwd . --json
uv run glassbox session attach SESSION_ID --cwd .
uv run glassbox daemon stop --cwd .
```

Daemon ownership prevents conflicting local writers while preserving local-first
state in the workspace.

### Cancel Or Resolve Paused Work

```bash
uv run glassbox session cancel SESSION_ID --reason "operator requested stop" --cwd .
uv run glassbox session answer SESSION_ID QUESTION_ID "answer" --cwd .
uv run glassbox session approve SESSION_ID APPROVAL_ID --cwd .
uv run glassbox session deny SESSION_ID APPROVAL_ID --cwd .
```

Use `glassbox session status SESSION_ID --cwd .` when you need the next valid
operator action before mutating a session.

### Recover Or Audit Workspace State

```bash
uv run glassbox observability status --cwd . --json
uv run glassbox projection check --cwd . --all
uv run glassbox artifacts inspect --cwd . --json
uv run glassbox artifacts prune --cwd . --dry-run --json
uv run glassbox backup create .glassbox/backups/v6-candidate.zip --cwd . --json
```

Run rebuild, restore, and non-dry-run prune only after the read-only command
output matches the intended recovery action.

### Verify A Release Candidate

```bash
uv run python scripts/validate_v6_release_gate.py \
  --evidence-dir .glassbox/releases/v6-rc-candidate
```

Optional provider canaries:

```bash
uv run glassbox provider canary run \
  --cwd . \
  --output-dir .glassbox/releases/v6-rc-candidate/provider-canary \
  --json
```

## Release-Readiness Checklist

Before treating a build as the v6 release candidate, complete this list:

- `uv run glassbox command tree` matches the documented command surface.
- `uv run python scripts/validate_v6_release_gate.py` passes and writes
  `summary.json`.
- `manual-validation.md` exists in the same evidence directory as the automated
  summary.
- Terminal review evidence covers `120x36`, `100x30`, `80x24`, and `60x20`.
- Dashboard review evidence covers desktop, tablet, mobile, keyboard workflows,
  and the screenshot archive.
- Recovery review evidence covers observability, projections, artifacts,
  backups, replay/eval, daemon recovery, and installed dashboard smoke.
- Provider canaries either run with retained redacted evidence or are explicitly
  skipped with a credential or policy reason.
- Package artifacts include the static dashboard, runtime modules, `textual`
  dependency metadata, and the `glassbox` console script.
- Residual risks are named, mitigated, and accepted in the release decision.

## Current Evidence Summary

Phase 70 retained evidence currently shows:

- automated v6 gate: passed
- full Python tests: `755 passed`
- deterministic eval smoke: passed with advisory drift retained for advisory
  cases only
- frontend lint, typecheck, tests, API generation, API freshness, build, and
  static asset validation: passed
- package build and package contents validation: passed
- installed terminal, daemon, eval, and dashboard smoke: passed
- manual terminal, dashboard, and recovery evidence: passed with no blocking
  issue recorded
- provider canary: OpenAI `streaming-text` advisory scenario passed with
  redacted retained evidence

## Known Residual Risks

- Provider-specific cancellation may not stop remote computation immediately
  even when local cancellation state is recorded correctly.
- Live-provider canaries are advisory and scenario-limited.
- Terminal and dashboard accessibility claims are limited to reviewed workflows;
  v6 does not claim broad assistive-technology certification.
- Installed-package smoke is intentionally short and does not exercise every
  dashboard scenario.
- Plain fallback remains necessary for unsupported terminals, redirected
  streams, and CI-like environments.

## Deliberate Non-Goals

v6 does not introduce a hosted control plane, remote multi-user orchestration,
browser-native code editing, plugin marketplaces, cloud authority for session
ownership, replacement of deterministic evals with live-provider canaries, or
removal of plain fallback.

## Release Decision

The final go/no-go decision is recorded by `GBX-704` in this guide after the
automated and manual evidence is reviewed. Until that update lands, this guide
describes the supported v6 candidate posture and validation path, not a final
release approval.

## Guide Map

- [getting-started.md](./getting-started.md): installation, first session, and
  validation basics
- [interactive-workflows.md](./interactive-workflows.md): terminal chat, attach,
  cancellation, approvals, questions, and fallback behavior
- [dashboard.md](./dashboard.md): co-hosted and standalone dashboard operation
- [persistent-runtime.md](./persistent-runtime.md): daemon ownership and stale
  owner recovery
- [replay-evals.md](./replay-evals.md): replay, eval, deterministic report, and
  advisory canary tracks
- [providers.md](./providers.md): provider credentials, diagnostics, and canaries
- [release-packaging.md](./release-packaging.md): package build, static assets,
  and installed smoke
- [v6-release-gate.md](./v6-release-gate.md): objective release-candidate gate
  and pass/fail policy
- [manual-qa-evidence-v6.md](./manual-qa-evidence-v6.md): manual evidence archive
  and redaction rules
