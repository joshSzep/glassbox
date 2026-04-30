# Glassbox v9 Release Candidate

This page is the operator and contributor guide for the Glassbox v9
release-candidate track. It names the supported operating model, validation
path, evidence expectations, non-goals, residual risks, and release decision
without requiring readers to inspect the task graph.

## Release Posture

Glassbox v9 turns the v8 auditable-autonomy release candidate into a clearer
public baseline for local engineering work. The release track emphasizes
first-run readiness, daily workflow discovery, dashboard cockpit priority,
provider evidence freshness, promoted deterministic autonomy evals, package
smoke, recovery guidance, and dogfooding disposition.

The primary product shape is:

- terminal chat is the primary operator surface
- the dashboard is the paired cockpit for attention, evidence, recovery, and
  decisions
- SQLite canonical events remain the source of truth
- one local mutation owner controls a workspace at a time
- sessions, tasks, evidence, memory, branches, and verification are the public
  product model
- workspace memory and repository index data remain local, provenance-aware,
  and rebuildable
- deterministic replay and eval evidence remain release authority
- provider diagnostics, canaries, and recommendations remain advisory unless a
  future policy explicitly promotes a repeatable live-provider scenario

Use these discovery commands:

```bash
uv run glassbox command guide
uv run glassbox command tree
```

The v9 automated release-candidate gate is:

```bash
uv run python scripts/validate_v9_release_gate.py
```

The retained evidence directory used for the current release-candidate pass is:

```text
.glassbox/releases/gbx-993-v9-release-candidate/
```

The v9 eval artifacts for that candidate are retained under:

```text
.glassbox/evals/gbx-993-v9-release-candidate/
```

Focused manual evidence is recorded in
[manual-v9-release-validation.md](./manual-v9-release-validation.md), with local
terminal, dashboard, recovery, package, and provider notes retained from the
`GBX-992` pass. Local `.glassbox/` evidence is workspace state and is not
committed to git.

## Supported Operating Model

- **First-run readiness**: `glassbox readiness check --cwd .` verifies local
  workspace state, database bootstrap, dashboard assets, provider posture,
  repository index freshness, tool policy, and next actions.
- **Daily command discovery**: `glassbox command guide` groups common work into
  start, inspect, unblock, verify, recover, and release-evidence workflows.
- **Terminal chat**: `glassbox session chat` starts the default operator loop
  with compact startup context and dashboard handoff. `--plain` remains the
  compatibility path.
- **Dashboard cockpit**: the workspace overview prioritizes approvals,
  questions, failures, projection/runtime issues, provider posture, stale
  repository intelligence, and recovery cues without hiding deeper queues.
- **Task and verification evidence**: task plans, stop reasons, budget posture,
  verification attempts, artifacts, and command evidence remain inspectable.
- **Memory and repository intelligence**: memory entries and repository index
  state are local, reviewable, invalidatable, and rebuildable.
- **Branch search**: bounded candidate comparisons retain selection,
  review-needed, rejection, and evidence without automatically mutating parent
  history.
- **Provider posture**: provider diagnostics, retained canary freshness, and
  workflow recommendations are visible and redacted, but advisory.
- **Release evidence**: deterministic evals, package validation, installed
  smoke, manual evidence, and residual-risk acceptance are retained under
  documented local evidence directories.

## Primary Operator Flows

### Start Work

```bash
uv run glassbox readiness check --cwd .
uv run glassbox session chat --cwd .
uv run glassbox dashboard serve --cwd .
```

Use `--autonomy-mode manual` for no autonomous continuation, `guided` or
`inspect` for read-only help, `edit-safe` for bounded local writes,
`test-driven` for verification-heavy work, and `release-candidate` for
conservative release validation.

### Inspect And Unblock

```bash
uv run glassbox session list --cwd .
uv run glassbox task list --cwd .
uv run glassbox session answer SESSION_ID QUESTION_ID ANSWER --cwd .
uv run glassbox session approve SESSION_ID APPROVAL_ID --cwd .
uv run glassbox session cancel SESSION_ID --cwd .
```

Use the dashboard cockpit when several sessions, tasks, provider cues, recovery
cues, or verification states compete for attention.

### Verify Work

```bash
uv run glassbox eval recommend PATH --cwd .
uv run glassbox eval run --profile commit-smoke --cwd .
uv run glassbox eval report commit-smoke push-confirmation release-candidate --cwd .
```

The stable v8 autonomy cases for budget exhaustion, verification success,
verification failure, and branch-search comparison are now part of blocking
release-candidate deterministic evidence.

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

Before treating a build as the v9 release candidate, complete this list:

- `uv run glassbox command tree` and `uv run glassbox command guide` match the
  documented command surface.
- First-run readiness runs and reports clear next actions.
- `uv run python scripts/validate_v9_release_gate.py` passes and writes
  `summary.json`.
- Manual validation exists in the same evidence directory as the automated
  summary where practical.
- The deterministic `release-candidate` eval profile passes and includes the
  promoted stable autonomy cases.
- Advisory autonomy and provider cases keep explicit non-blocking status and
  reasons.
- Dashboard cockpit evidence covers attention summary, task evidence
  drill-down, recovery cues, provider cues, keyboard, and mobile workflows or
  records explicit non-claims.
- Terminal review evidence covers first-run chat startup, dashboard handoff,
  approvals/questions, cancellation, daemon attach, long output, and fallback or
  records explicit non-claims.
- Recovery review evidence covers observability, daemon, jobs, projections,
  artifacts, stale repository index, provider evidence, package, and eval
  workflows.
- Package artifacts include static dashboard assets, generated API files, v9
  docs, eval profiles, release scripts, and installed smoke support.
- Dogfooding findings have dispositions as fixes, docs, tests/evals, accepted
  risks, or post-v9 tasks.
- Named accessibility pairings and non-claims are recorded.
- Residual risks are named, mitigated, and accepted in the release decision.

## Current Evidence Summary

The current retained v9 evidence shows:

- non-dry-run v9 gate: passed for `GBX-993`, with `63` passed stages and one
  explicit advisory skip recorded at
  `.glassbox/releases/gbx-993-v9-release-candidate/summary.json`
- v9 gate dry run: passed during `GBX-991`
- package contents validation: wheel and sdist include v9 docs, generated API
  files, release scripts, evals, and dashboard static assets
- installed-wheel smoke: passed in the final `GBX-993` gate, including
  readiness, command guide, provider diagnostics, dashboard static routes,
  daemon lifecycle, eval profile listing, `release-candidate` profile
  inspection, and deterministic eval smoke
- promoted release-candidate eval profile: `8/8` cases passed in the final
  `GBX-993` gate under
  `.glassbox/evals/gbx-993-v9-release-candidate/promoted-autonomy/`
- release eval report: `commit-smoke`, `push-confirmation`, and
  `release-candidate` profiles passed in the final `GBX-993` gate under
  `.glassbox/evals/gbx-993-v9-release-candidate/release-signoff/`
- manual validation: `GBX-992` found no deterministic blocker, but retained
  residual risks for browser-rendered dashboard evidence, full-screen TUI
  recording, stale repository index, and partial live-provider canary coverage
- provider evidence: fresh and advisory, with `streaming-text` covered and
  missing-scenario guidance for release-candidate work
- dogfooding: findings are triaged in
  [v9-dogfooding-summary.md](./v9-dogfooding-summary.md)

## Known Residual Risks

- Browser-rendered dashboard keyboard and mobile evidence was blocked in the
  `GBX-992` environment by Next watcher `EMFILE` and Chromium sandbox
  permission failure. Component tests passed, but browser/manual evidence should
  be rerun in an environment that can launch Chromium.
- Screen-reader pairings were not executed. Accessibility claims remain limited
  to named automated component evidence, prior retained dashboard evidence, and
  terminal plain-mode review; no broad assistive-technology certification is
  claimed.
- Full-screen TUI was not manually recorded in `GBX-992`; automated TUI tests
  and installed smoke remain the evidence for this candidate.
- Repository index state is stale after v9 docs and gate changes. The index is
  rebuildable with `glassbox repo index build --cwd .`, and stale status is an
  operator cue rather than hidden prompt memory.
- Provider evidence is fresh but partial for release-candidate work; retained
  live canary evidence covers `streaming-text` only. Provider advice remains
  advisory.
- Plain fallback remains necessary for unsupported terminals, redirected
  streams, and CI-like environments.

## Deliberate Non-Goals

v9 does not introduce a hosted control plane, cloud authority for workspace
ownership, remote multi-user orchestration, simultaneous multi-writer mutation,
distributed worker fleets, plugin marketplaces, browser-native code editing as
a replacement for local tools, remote policy enforcement, hidden provider-side
memory, uninspectable vector-store authority, automatic background mutation
without explicit budget and policy, automatic merging of branch-search
candidates, replacement of deterministic evals with live-provider canaries, or
removal of the plain terminal fallback.

Multiple local observers, clearer local autonomy, stronger release contracts,
and better operator experience are in scope. Multiple concurrent mutation
owners and cloud authority are not.

## Release Decision

Decision: GO for v9 release candidate publication.

Decision date: 2026-04-30.

Candidate build reviewed: `GBX-993` release-candidate working tree with final
v9 gate evidence retained locally.

Retained evidence:

```text
.glassbox/releases/gbx-993-v9-release-candidate/
.glassbox/evals/gbx-993-v9-release-candidate/
```

Final pass/fail state:

| Area | State | Evidence |
| --- | --- | --- |
| Automated v9 gate | passed | `.glassbox/releases/gbx-993-v9-release-candidate/summary.json` |
| Deterministic eval release report | passed | `.glassbox/evals/gbx-993-v9-release-candidate/release-signoff/` |
| Promoted autonomy eval profile | passed | `.glassbox/evals/gbx-993-v9-release-candidate/promoted-autonomy/` |
| Manual validation | passed focused review | [manual-v9-release-validation.md](./manual-v9-release-validation.md) |
| Provider posture | advisory and partial | [providers.md](./providers.md) and `GBX-992` provider evidence |
| Package smoke | passed | [release-packaging.md](./release-packaging.md) and `.glassbox/releases/gbx-993-v9-release-candidate/summary.json` |
| Dogfooding disposition | passed triage | [v9-dogfooding-summary.md](./v9-dogfooding-summary.md) |
| Residual risk review | accepted | known residual risks listed above |

No deterministic blocker remains open for v9 release-candidate publication.
The accepted residual risks stay bounded to the advisory provider, browser,
screen-reader, full-screen TUI, stale-index, and plain-fallback limits named
above.

## Related Files

- [v9-public-baseline.md](./v9-public-baseline.md)
- [v9-release-gate.md](./v9-release-gate.md)
- [manual-v9-release-validation.md](./manual-v9-release-validation.md)
- [manual-qa-evidence-v9.md](./manual-qa-evidence-v9.md)
- [v9-eval-promotion-plan.md](./v9-eval-promotion-plan.md)
- [v9-dogfooding-summary.md](./v9-dogfooding-summary.md)
- [dashboard-cockpit-contract.md](./dashboard-cockpit-contract.md)
- [daily-workflow-quickstart.md](./daily-workflow-quickstart.md)
- [providers.md](./providers.md)
- [release-packaging.md](./release-packaging.md)
- [replay-evals.md](./replay-evals.md)
- [tasks-v9.md](./tasks-v9.md)
