# v6 Release Hardening Contract

This document defines the v6 release-hardening contract for Glassbox. It turns the completed v2 runtime, v3 SPA migration, v4 operator-console UX, and v5 full-screen terminal client into one release-candidate readiness model.

For the implementation task graph, use [tasks-v6.md](./tasks-v6.md). For the objective release-candidate gate, use [v6-release-gate.md](./v6-release-gate.md). For the current terminal gate that v6 builds on, use [v5-terminal-release-gate.md](./v5-terminal-release-gate.md). For package build details, use [release-packaging.md](./release-packaging.md).

## Scope

v6 is a hardening milestone, not a product-surface expansion milestone.

The release is ready only when Glassbox can prove that the existing local-first agent workflow behaves dependably across terminal chat, dashboard inspection, daemon ownership, replay/eval verification, packaging, and recovery workflows.

The v6 scope is:

- real backend cancellation for active model and tool work
- stronger live transport, reconnect, and daemon lifecycle behavior
- one automated release gate with retained local evidence
- advisory live-provider canaries that do not replace deterministic replay/eval
- reproducible package validation and clean installed-wheel smoke
- manual terminal, dashboard, recovery, and accessibility evidence
- public release-candidate documentation with explicit residual risks

The v6 scope is not:

- a hosted control plane
- remote multi-user orchestration
- a plugin marketplace
- browser-native code editing
- cloud authority for session ownership
- replacement of deterministic evals with live-provider checks
- removal of plain fallback before an equally reliable unsupported-terminal path exists

## Supported Workflow Set

The supported v6 operating model keeps the established Glassbox roles intact.

- The TUI remains the primary interactive chat surface for supported terminals.
- Plain mode remains the compatibility and fallback path for unsupported terminals, redirected streams, and debugging.
- The dashboard remains the paired operator console for queue triage, lineage, runtime context, tool evidence, replay/eval cues, and deeper inspection.
- A foreground `session chat` process or workspace daemon remains the live mutation owner for one workspace runtime.
- The SQLite event log remains canonical; projections, dashboards, terminal state, release evidence, and eval reports are derived evidence.
- Replay/eval remains deterministic by default and keeps release-blocking behavior separate from live-provider advisory canaries.

## Evidence Classes

v6 separates release evidence into four classes so contributors can tell what is blocking, advisory, manual, or retained for audit.

### Automated Blocking Evidence

Automated blocking evidence must pass before a v6 release candidate can be marked ready.

- Python format, lint, and typecheck
- focused cancellation, transport, daemon, TUI, dashboard, packaging, replay, and eval tests
- full Python test suite
- deterministic eval smoke
- frontend lint, typecheck, unit tests, and production build
- wheel and sdist build
- installed-wheel smoke for terminal, dashboard, daemon, and command inventory paths covered by the v6 gate

### Manual Blocking Evidence

Manual blocking evidence covers workflows that automated tests cannot prove safely or meaningfully.

- terminal visual and keyboard review at representative sizes
- dashboard responsive and keyboard review at representative viewports
- installed dashboard smoke from a clean package
- daemon lifecycle smoke
- recovery and maintenance smoke for projections, artifacts, backups, observability, replay, and eval reports
- accessibility notes with explicit claims and non-claims

### Advisory Evidence

Advisory evidence improves confidence but does not fail the default release gate unless a later task explicitly promotes it.

- live-provider canary runs when credentials are available
- dependency freshness review findings that are not release blockers
- performance notes that stay within documented budgets
- low-risk manual UX observations with accepted follow-up tasks

### Retained Evidence

Retained evidence is the local record of what was run and what should be inspected next.

- release gate summary JSON
- command logs or stage summaries
- eval summary artifacts
- package build artifact references
- installed smoke logs
- manual QA manifests, screenshots, transcripts, and redacted notes
- skipped provider-canary reasons
- residual risk register

## Mapping From v5 Known Gaps

The v5 terminal release gate accepted several non-blocking gaps. v6 resolves or reclassifies each one explicitly.

| v5 known gap | v6 task path | v6 expectation |
| --- | --- | --- |
| Backend cancellation of in-flight model/tool turns is not implemented | `GBX-650` through `GBX-655` | Cancellation becomes a real backend behavior with persisted outcomes and daemon/attach coverage. |
| Terminal visual review is manual | `GBX-690`, `GBX-691`, `GBX-700`, `GBX-702` | Manual review remains valid, but evidence has a defined archive, checklist, and release decision policy. |
| Real provider behavior needs manual validation | `GBX-670` through `GBX-672`, `GBX-700`, `GBX-702` | Provider canaries become advisory, structured, skippable when credentials are unavailable, and retained when run. |
| Full-screen support depends on terminal capabilities | `GBX-691`, `GBX-694`, `GBX-700` | Supported terminal and fallback behavior are reviewed, documented, and treated as release posture rather than surprise behavior. |
| Screen-reader review remains manual | `GBX-690` through `GBX-692`, `GBX-700`, `GBX-702` | Accessibility claims are tied to reviewed evidence and any unreviewed support remains an explicit non-claim. |

## Release-Readiness Checklist

Before marking a v6 release candidate ready, all of the following must be true:

- `uv run python scripts/validate_v6_release_gate.py` passes.
- The gate writes a retained release evidence summary.
- Backend cancellation has deterministic runtime, tool, API, TUI, dashboard, daemon, replay, and eval coverage as defined by the completed v6 cancellation tasks.
- Live transport and daemon ownership tests cover reconnect, dropped live events, stale owner recovery, and mutation conflicts.
- Frontend generated API types and static assets are fresh for the package build.
- Wheel and sdist contents are inspected automatically.
- Installed-wheel smoke proves terminal help, plain fallback, dashboard serving, daemon command paths, and command inventory work without an editable checkout.
- Deterministic eval smoke and release-report expectations are aligned with the documented profiles.
- Dependency and toolchain freshness has been reviewed against `pyproject.toml`, `uv.lock`, `frontend/package.json`, and `frontend/pnpm-lock.yaml`.
- Manual terminal, dashboard, recovery, and accessibility evidence exists for the release candidate.
- Provider canaries either ran and retained advisory evidence or were explicitly skipped with a credential-unavailable reason.
- The residual risk register contains only accepted non-blocking risks.
- Operator docs describe the supported v6 behavior without requiring users to inspect task docs.

## Residual Risk Register

The v6 release candidate may carry residual risks only when they are explicit and accepted.

Use this shape for every residual risk:

- **Risk**: concise user-facing or release-facing risk.
- **Evidence**: automated, manual, advisory, or skipped evidence that supports the decision.
- **Impact**: what could go wrong for an operator.
- **Mitigation**: command, workflow, fallback, or follow-up task.
- **Decision**: accepted for v6, blocking v6, or deferred pending more evidence.

Initial expected residual-risk candidates are:

- provider-specific cancellation may not stop remote computation immediately even when local session state records cancellation correctly
- live-provider canaries may be skipped in contributor environments without credentials
- terminal and dashboard accessibility claims remain limited to reviewed workflows
- installed-package smoke should remain short and may not exercise every dashboard state
- broad performance canaries stay advisory unless a documented budget is violated

## Pass And Fail Policy

The default v6 pass/fail policy is conservative.

- Deterministic gate failure blocks the release candidate.
- Package build or installed smoke failure blocks the release candidate.
- Cancellation contract failure blocks the release candidate once cancellation tasks are marked complete.
- Daemon lifecycle failure blocks the release candidate when it affects supported daemon operation.
- Provider canary skip does not block when credentials are unavailable and the skip is retained as evidence.
- Provider canary failure is advisory by default, but the release decision must explain the impact and next action.
- Manual accessibility or UX findings block only when they affect a supported primary workflow or contradict a public claim.
- Residual risks are allowed only when they are named, mitigated, and accepted in the release decision.

## Related Files

- [tasks-v6.md](./tasks-v6.md)
- [v6-release-gate.md](./v6-release-gate.md)
- [v6-release-inventory.md](./v6-release-inventory.md)
- [v6-release-evidence.md](./v6-release-evidence.md)
- [v5-terminal-release-gate.md](./v5-terminal-release-gate.md)
- [release-packaging.md](./release-packaging.md)
- [v2-release-candidate.md](./v2-release-candidate.md)
- [replay-evals.md](./replay-evals.md)
- [providers.md](./providers.md)
