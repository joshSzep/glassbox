# Glassbox v10 Release Candidate

This page is the operator and contributor guide for the Glassbox v10
release-candidate track. It names the supported long-running-task operating
model, validation path, evidence expectations, non-goals, residual risks, and
release decision without requiring readers to inspect the task graph.

## Release Posture

Glassbox v10 extends the v9 public baseline with long-running-task reliability.
The release track emphasizes durable recovery boundaries, typed checkpoints,
artifact-backed context compaction, resumable tool attempts, long-run cockpit
state, time-aware budgets, incremental verification, provider recovery posture,
and deterministic release evidence for interruption and recovery.

The primary product shape is:

- terminal chat remains the primary operator surface
- the dashboard is the paired cockpit for long-running heartbeat, recovery,
  checkpoint, compaction, attempt, verification, budget, and provider cues
- SQLite canonical events remain the source of truth
- one local mutation owner controls a workspace at a time
- checkpoints, compactions, tool attempts, provider recovery, verification, and
  task evidence are visible as local workspace state
- deterministic replay and eval evidence remain release authority
- provider diagnostics, canaries, and recommendations remain advisory unless a
  future policy promotes a repeatable fixture-backed scenario
- v10 is local long-running agent work, not hosted orchestration

Use these discovery commands:

```bash
uv run glassbox command guide
uv run glassbox command tree
```

The v10 automated release-candidate gate is:

```bash
uv run python scripts/validate_v10_release_gate.py
```

For focused local iteration, contributors may use the fast pytest slice:

```bash
uv run pytest -m "not daemon and not subprocess and not timeout and not tui and not slow"
```

That fast slice is not release authority. The v10 release gate keeps the
unfiltered full pytest stage and adds a focused process-boundary marker stage
for daemon, subprocess, timeout, and TUI coverage.

The retained evidence directory used for the current release-candidate pass is:

```text
.glassbox/releases/gbx-1093-v10-release-candidate/
```

The v10 eval artifacts for that candidate are retained under:

```text
.glassbox/evals/gbx-1093-v10-release-candidate/
```

Focused dogfooding evidence is summarized in
[v10-dogfooding-summary.md](./v10-dogfooding-summary.md). Local `.glassbox/`
evidence is workspace state and is not committed to git.

## Supported Operating Model

- **Durable checkpoints**: task checkpoints carry objective, phase, completed
  step, next action, blockers, verification posture, recovery guidance, budget
  posture, touched files, and source event range.
- **Artifact-backed compaction**: `glassbox session compact` records scoped
  compactions with source sequence ranges, freshness, limitations, source
  artifact references, and operator-readable summaries.
- **Resumable attempts**: tool attempts retain status, heartbeat, partial
  output posture, retry guidance, safe-to-retry classification, and recovery
  actions beside the existing tool-call record.
- **Long-run cockpit**: terminal and dashboard summaries surface heartbeat,
  stuck state, latest checkpoint, compaction freshness, attempt posture,
  verification staleness, provider recovery, and concrete next actions.
- **Time-aware budgets**: v10 budget posture includes wall-clock,
  unattended-duration, checkpoint interval, retry delay, quiet-window, and
  checkpoint-approval constraints.
- **Incremental verification**: verification evidence records last-known-good
  commands, stale workspace posture, failure summaries, and follow-up actions.
- **Provider recovery**: provider recommendations include failure posture,
  recommended action, budget impact, and advisory next actions without making
  live-provider behavior release authority.
- **Release evidence**: deterministic evals, package validation, installed
  smoke, dogfooding summaries, and residual-risk acceptance are retained under
  documented local evidence directories.

## Primary Operator Flows

### Start Or Resume Work

```bash
uv run glassbox readiness check --cwd .
uv run glassbox session chat --cwd .
uv run glassbox session attach SESSION_ID --cwd .
uv run glassbox dashboard serve --cwd .
```

Use `--autonomy-mode manual` for no autonomous continuation, `guided` or
`inspect` for read-only help, `edit-safe` for bounded local writes,
`test-driven` for verification-heavy work, and `release-candidate` for
conservative release validation.

### Inspect Long-Running State

```bash
uv run glassbox session status SESSION_ID --cwd .
uv run glassbox task list --cwd . --json
uv run glassbox task show TASK_ID --cwd . --json
uv run glassbox session compactions SESSION_ID --cwd . --json
uv run glassbox session tool-attempts SESSION_ID --cwd . --json
```

Use the dashboard cockpit when several sessions, tasks, attempts, stale
verification cues, provider cues, or recovery states compete for attention.

### Compact And Recover Context

```bash
uv run glassbox session compact SESSION_ID \
  --scope transcript \
  --source-start-sequence START \
  --source-end-sequence END \
  --cwd . \
  --json
```

Compactions are evidence, not cleanup. Keep the source range, limitations, and
freshness posture visible before relying on a compacted context.

### Verify Work

```bash
uv run glassbox eval recommend PATH --cwd .
uv run glassbox eval run --profile commit-smoke --cwd .
uv run glassbox eval run --profile release-candidate --cwd .
uv run glassbox eval report commit-smoke push-confirmation release-candidate --cwd .
```

The release-candidate profile includes compact deterministic v10 fixtures for
checkpoint-backed incomplete-turn recovery, compaction provenance and stale
exclusion, tool-attempt partial-output recovery, stale verification review, and
long-run cockpit summaries.

### Inspect Provider Readiness

```bash
uv run glassbox provider diagnostics --cwd . --json
uv run glassbox provider canary evidence --cwd . --json
uv run glassbox provider recommend \
  --task-kind release \
  --autonomy-mode release-candidate \
  --cwd . \
  --json
```

Provider evidence improves operational confidence. It does not replace
deterministic replay/eval release authority.

### Recover Workspace State

```bash
uv run glassbox observability status --cwd . --json
uv run glassbox projection check --all --cwd .
uv run glassbox artifacts inspect --cwd . --json
uv run glassbox repo index status --cwd . --json
uv run glassbox daemon status --cwd . --json
uv run glassbox job list --cwd . --json
```

Run mutating recovery commands only after the read-only output matches the
intended recovery action.

## Release-Readiness Checklist

Before treating a build as the v10 release candidate, complete this list:

- `uv run glassbox command tree` and workflow-oriented command discovery match
  the documented command surface.
- First-run readiness runs and reports clear next actions.
- `uv run python scripts/validate_v10_release_gate.py` passes and writes
  `summary.json`.
- The deterministic `release-candidate` eval profile passes with checkpoint,
  compaction, tool-attempt, stale-verification, and cockpit fixtures.
- Checkpoint evidence is visible for new task-aware long-running work, or
  checkpoint absence is named as a historical-session limitation.
- Compaction evidence records source ranges, freshness, limitations, and
  provenance to events and artifacts.
- Tool-attempt recovery evidence records partial-output posture, retry
  guidance, and safe-to-resume behavior.
- Incremental verification records last-known-good evidence and stale
  verification warnings when the workspace changes.
- Dashboard cockpit evidence covers long-run summary, checkpoint, compaction,
  attempt, verification, budget, provider, and recovery cues through
  deterministic replay or retained manual evidence.
- Provider diagnostics, recommendations, and canary evidence remain advisory
  with explicit freshness, missing-scenario, and next-action posture.
- Package artifacts include static dashboard assets, generated API files, v10
  docs, eval profiles, release scripts, and installed smoke support.
- Dogfooding findings have dispositions as fixes, docs, tests/evals, accepted
  risks, or post-v10 tasks.
- Accessibility pairings and non-claims are recorded; broad assistive
  technology certification is not implied by this candidate.
- Residual risks are named, mitigated, and accepted in the release decision.

## Current Evidence Summary

The current retained v10 evidence shows:

- non-dry-run v10 gate: passed for `GBX-1093`, with the final stage counts
  retained at `.glassbox/releases/gbx-1093-v10-release-candidate/summary.json`
- v10 gate dry run: passed during `GBX-1091`
- package contents validation: wheel and sdist include v10 docs, generated API
  files, release scripts, evals, and dashboard static assets
- installed-wheel smoke: passed in the final v10 gate, including readiness,
  command guide, provider diagnostics, dashboard static routes, daemon
  lifecycle, eval profile listing, `release-candidate` profile inspection, and
  deterministic eval smoke
- release-candidate eval profile: `13/13` cases passed during the v10 gate,
  including checkpoint, compaction, tool-attempt, stale-verification, and
  cockpit fixtures
- release eval report: `commit-smoke`, `push-confirmation`, and
  `release-candidate` profiles passed in the v10 gate under
  `.glassbox/evals/gbx-1093-v10-release-candidate/v10-release-signoff/`
- dogfooding: findings are triaged in
  [v10-dogfooding-summary.md](./v10-dogfooding-summary.md)
- provider evidence: fresh and advisory, with live canary coverage still
  partial and deterministic replay/eval evidence remaining authoritative

## Known Residual Risks

- Full-session compaction over very large source ranges can surface a raw
  source-reference cap validation error. Operators should compact bounded
  ranges until a follow-up adds friendlier guidance or a CLI guard.
- Historical or imported sessions may show no latest checkpoint. Checkpoint
  absence is visible, but operators may need to infer whether that is expected
  for pre-checkpoint-era sessions.
- Live dashboard monitoring was not manually exercised in the GBX-1092
  dogfooding passes. Deterministic cockpit replay and component coverage remain
  the retained release evidence for these surfaces.
- Provider evidence is fresh but partial for release-candidate work; retained
  live canary evidence covers only part of the desired long-running provider
  matrix. Provider advice remains advisory.
- `glassbox eval recommend` does not yet confidently route release-gate scripts
  or release-candidate docs to the v10 release checks. Operators should run the
  release gate manually for those paths.
- Screen-reader pairings were not executed for v10. Accessibility claims remain
  limited to retained automated component evidence and prior terminal/dashboard
  review; no broad assistive-technology certification is claimed.
- Long-running work remains bounded local continuation, not indefinite
  unattended operation. Operators should keep budgets, checkpoints, approvals,
  and recovery cues in the loop.

## Deliberate Non-Goals

v10 does not introduce a hosted control plane, cloud authority for workspace
ownership, remote multi-user orchestration, simultaneous multi-writer mutation,
distributed worker fleets, hidden provider-side memory, uninspectable
provider-side task state, automatic background mutation without explicit
budgets, automatic recovery from every live-provider failure, automatic merging
of branch-search candidates, replacement of deterministic evals with live
provider canaries, or removal of the plain terminal fallback.

Longer local work, clearer recovery posture, stronger compaction provenance,
and better operator inspection are in scope. Indefinite autonomy and cloud
orchestration are not.

## Release Decision

Decision: GO for v10 release candidate publication.

Decision date: 2026-04-30.

Candidate build reviewed: `GBX-1093` release-candidate working tree with final
v10 gate evidence retained locally.

Retained evidence:

```text
.glassbox/releases/gbx-1093-v10-release-candidate/
.glassbox/evals/gbx-1093-v10-release-candidate/
```

Final pass/fail state:

| Area | State | Evidence |
| --- | --- | --- |
| Automated v10 gate | passed | `.glassbox/releases/gbx-1093-v10-release-candidate/summary.json` |
| Deterministic eval release report | passed | `.glassbox/evals/gbx-1093-v10-release-candidate/v10-release-signoff/` |
| Long-run release profile | passed | `.glassbox/evals/gbx-1093-v10-release-candidate/long-run-release/` |
| Checkpoint/compaction smoke | passed | `.glassbox/evals/gbx-1093-v10-release-candidate/checkpoint-compaction-smoke/` |
| Tool-attempt recovery smoke | passed | `.glassbox/evals/gbx-1093-v10-release-candidate/tool-attempt-recovery-smoke/` |
| Long-run cockpit smoke | passed | `.glassbox/evals/gbx-1093-v10-release-candidate/long-run-cockpit-smoke/` |
| Provider posture | advisory and partial | [providers.md](./providers.md) and v10 gate provider recommendation |
| Package smoke | passed | [release-packaging.md](./release-packaging.md) and v10 gate installed smoke |
| Dogfooding disposition | passed triage | [v10-dogfooding-summary.md](./v10-dogfooding-summary.md) |
| Residual risk review | accepted | known residual risks listed above |

No deterministic blocker remains open for v10 release-candidate publication.
The accepted residual risks stay bounded to the compaction guidance,
historical-checkpoint, live-dashboard, provider, eval-recommendation,
accessibility, and bounded-autonomy limits named above.

## Related Files

- [v10-long-running-task-contract.md](./v10-long-running-task-contract.md)
- [v10-durability-audit.md](./v10-durability-audit.md)
- [v10-release-gate.md](./v10-release-gate.md)
- [v10-dogfooding-summary.md](./v10-dogfooding-summary.md)
- [long-run-cockpit-contract.md](./long-run-cockpit-contract.md)
- [context-compactions.md](./context-compactions.md)
- [tool-attempts.md](./tool-attempts.md)
- [verification-loops.md](./verification-loops.md)
- [providers.md](./providers.md)
- [release-packaging.md](./release-packaging.md)
- [replay-evals.md](./replay-evals.md)
- [tasks-v10.md](./tasks-v10.md)
