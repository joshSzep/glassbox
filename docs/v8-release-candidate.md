# Glassbox v8 Release Candidate

This page is the operator and contributor guide for the Glassbox v8 release-candidate track. It names the supported operating model, validation path, evidence expectations, non-goals, residual risks, and current go/no-go decision without requiring readers to inspect the task graph.

## Release Posture

Glassbox v8 promotes autonomy from prompt convention into durable, inspectable runtime state. The release track adds task plans, autonomy budgets, background jobs, workspace memory, repository intelligence, verify-repair loops, branch-search comparison, provider recommendations, and dashboard autonomy controls while preserving the local-first product boundary.

The primary product shape remains:

- terminal chat is the primary operator surface
- the dashboard is the paired autonomy and evidence console
- SQLite canonical events remain the source of truth
- one local mutation owner controls a workspace at a time
- autonomy is bounded by typed budgets, policy, cancellation, verification evidence, and durable stop reasons
- workspace memory and repository index data remain local, provenance-aware, and rebuildable
- deterministic replay and eval evidence remain release authority
- provider canaries and provider recommendations remain advisory unless a future policy promotes a specific scenario

The canonical command inventory is exposed by:

```bash
uv run glassbox command tree
```

The v8 automated release-candidate gate is:

```bash
uv run python scripts/validate_v8_release_gate.py
```

The retained evidence directory used for the current automated release pass is:

```text
.glassbox/releases/20260429T180807Z-v8-gate/
```

That directory contains the non-dry-run v8 gate `summary.json`. The v8 autonomy eval artifacts for that candidate are retained under:

```text
.glassbox/evals/20260429T180807Z-v8-gate/
```

Focused manual evidence remains recorded in [manual-v8-release-validation.md](./manual-v8-release-validation.md), with local recovery, package, provider, and dashboard notes retained from the `GBX-894` pass. Local `.glassbox/` evidence is workspace state and is not committed to git.

## Supported Operating Model

- **Terminal chat**: `glassbox session chat` launches the full-screen TUI in supported interactive terminals. `--plain` remains the explicit compatibility path for unsupported terminals, redirected streams, and CI-like environments.
- **Task plans**: task proposal, step, continuation, verification, blocked, and budget evidence are durable runtime objects exposed through CLI, web, replay, and eval paths.
- **Autonomy budgets**: autonomy modes define bounded steps, tools, writes, commands, verification attempts, branch attempts, wall-clock time, artifact bytes, and allowed risk buckets.
- **Background jobs**: daemon-owned jobs can continue bounded work, run read-only maintenance, retry or abandon failed jobs, cancel work, and recover stale ownership with explicit evidence.
- **Workspace memory**: memory entries and candidates carry provenance, freshness, confirmation, invalidation, pruning, import/export, redaction, and prompt-use evidence.
- **Repository intelligence**: the repository index is local, rebuildable, freshness-aware, searchable, and separate from hidden provider memory.
- **Verify-repair loops**: verification loops record selected checks, command or eval evidence, failure categories, bounded repair attempts, and stop reasons.
- **Branch search**: branch-search workflows compare bounded local candidate strategies and retain selection, review, rejection, and verification evidence without automatically mutating parent history.
- **Dashboard autonomy console**: the dashboard surfaces task queues, plan inspection, budget controls, background jobs, memory/index inspectors, branch comparison, evidence panes, and why-this-action cues.
- **Provider evidence**: provider diagnostics, canaries, and recommendations help operators choose a model posture, but remain advisory beside deterministic eval and package evidence.
- **Recovery**: observability, projection, artifact, backup, daemon, job, memory, index, eval, and package workflows have explicit recovery commands and retained review evidence.
- **Release evidence**: automated and manual evidence should live under one `.glassbox/releases/...` directory per candidate where practical, with large eval artifacts under `.glassbox/evals/...`.

## Primary Operator Flows

### Start A Bounded Session

```bash
uv run glassbox session chat \
  "Plan and verify the requested change" \
  --cwd . \
  --autonomy-mode guided
```

Use `--autonomy-mode manual` for no autonomous continuation, `guided` or `inspect` for read-only help, `edit-safe` for bounded local writes, `test-driven` for verification-heavy work, and `release-candidate` for conservative release validation. The dashboard URL from the terminal header opens the paired autonomy console.

### Inspect Task Plans And Budgets

```bash
uv run glassbox task list --cwd . --json
uv run glassbox task show TASK_ID --cwd .
uv run glassbox autonomy profile list --cwd .
uv run glassbox autonomy profile show release-candidate --cwd .
```

Use task events and budget posture before continuing, retrying, or canceling autonomous work.

### Continue Or Stop Background Work

```bash
uv run glassbox daemon start --cwd .
uv run glassbox task continue TASK_ID --cwd . --verify-repair
uv run glassbox job list --cwd . --json
uv run glassbox job cancel JOB_ID --cwd . --reason "operator requested stop"
uv run glassbox daemon stop --cwd .
```

Background continuation is opt-in and remains interruptible through job and daemon controls.

### Curate Memory And Repository Intelligence

```bash
uv run glassbox memory candidates --cwd .
uv run glassbox memory confirm MEMORY_ID --cwd . --reason "still accurate"
uv run glassbox memory invalidate MEMORY_ID --cwd . --reason "stale"
uv run glassbox repo index build --cwd . --json
uv run glassbox repo index search "runtime autonomy" --cwd .
```

Memory and index entries should not materially affect prompts without provenance, freshness posture, and usage evidence.

### Verify, Repair, And Compare Strategies

```bash
uv run glassbox eval recommend --cwd .
uv run glassbox task continue TASK_ID --cwd . --verify-repair
uv run glassbox branch-search start TASK_ID --cwd .
uv run glassbox branch-search show SEARCH_ID --cwd .
uv run glassbox branch-search select SEARCH_ID CANDIDATE_ID --cwd . --reason "best verified outcome"
```

Verification and branch-search workflows stop on policy blocks, exhausted budgets, failed verification, cancellation, provider unavailability, or ambiguity.

### Inspect Provider Readiness

```bash
uv run glassbox provider diagnostics --cwd . --json
uv run glassbox provider recommend \
  --task-kind release \
  --autonomy-mode release-candidate \
  --model-name openai:gpt-5.4 \
  --cwd . \
  --json
```

Run advisory provider canaries only in a credentialed release environment:

```bash
uv run python scripts/validate_v8_release_gate.py \
  --include-provider-canaries \
  --evidence-dir .glassbox/releases/v8-rc-candidate
```

Provider evidence is useful for operational confidence, but deterministic eval and package evidence remain the release authority.

### Recover Or Audit Workspace State

```bash
uv run glassbox observability status --cwd . --json
uv run glassbox projection check --cwd . --all
uv run glassbox artifacts inspect --cwd . --json
uv run glassbox artifacts prune --cwd . --dry-run --json
uv run glassbox backup create .glassbox/backups/v8-candidate.zip --cwd . --json
```

Run rebuild, restore, retry, abandon, and non-dry-run prune only after the read-only command output matches the intended recovery action.

### Verify A Release Candidate

```bash
uv run python scripts/validate_v8_release_gate.py \
  --evidence-dir .glassbox/releases/v8-rc-candidate
```

Use `--dry-run` only to preview the gate or record a planned-stage summary. A dry run is not a release pass.

## Release-Readiness Checklist

Before treating a build as the v8 release candidate, complete this list:

- `uv run glassbox command tree` matches the documented command surface.
- `uv run python scripts/validate_v8_release_gate.py` passes and writes `summary.json`.
- Manual validation exists in the same evidence directory as the automated summary where practical.
- The deterministic `release-candidate` eval profile passes.
- The v8 autonomy advisory eval suite runs and any advisory gaps are recorded.
- Task-plan events, projections, CLI queries, web APIs, export/import, and replay behavior have focused automated coverage.
- Autonomy mode and budget behavior has policy, CLI, web, replay, eval, and dashboard evidence.
- Background daemon job execution has deterministic smoke evidence for read-only jobs, continuation jobs, cancellation, failure, retry, and stale-owner recovery.
- Workspace memory and repository index behavior have provenance, freshness, invalidation, redaction, context-use, and replay-drift evidence.
- Verify-repair loops and branch-search workflows have deterministic local fixtures and retained artifacts.
- Provider diagnostics and provider canaries either run with retained redacted evidence or record explicit skip reasons.
- Dashboard autonomy console evidence covers task queue, plan inspector, budget controls, memory/index inspectors, branch comparison, evidence pane, mobile, and keyboard workflows.
- Terminal review evidence covers task planning, background continuation cues, approvals/questions, cancellation, daemon attach, long output, and fallback.
- Recovery review evidence covers observability, projections, artifacts, backups, daemon, jobs, memory, index, eval, and installed dashboard workflows.
- Package artifacts include static dashboard assets, v8 docs, eval profiles, task/autonomy/job/memory/index modules, release scripts, and source-builder guidance.
- Named accessibility pairings are recorded before making stronger accessibility claims.
- Residual risks are named, mitigated, and accepted in the release decision.

## Current Evidence Summary

The current retained v8 evidence shows:

- full non-dry-run v8 gate: passed and wrote `.glassbox/releases/20260429T180807Z-v8-gate/summary.json`
- automated gate stages: `53` passed, `0` failed
- advisory provider canaries: skipped by default, with explicit non-blocking policy
- deterministic release report: `commit-smoke`, `push-confirmation`, and `release-candidate` passed with `0` failures
- v8 autonomy advisory eval: `8` cases passed with `0` failures, retained under `.glassbox/evals/20260429T180807Z-v8-gate/autonomy-advisory/`
- eval coverage audit: covered `20/20` audited capabilities with `0` uncovered
- background autonomy smoke: six scenarios passed, including completion, cancellation, failure retry/abandon, stale-owner cleanup, task continuation budget pause, and retained projection snapshot
- full Python test suite: `937` tests passed during the gate
- frontend release checks: lint, typecheck, `105` Vitest tests, generated API freshness, production build, and static asset validation passed
- package contents validation: rebuilt wheel and sdist include v8 modules, docs, evals, generated API files, scripts, and static dashboard assets
- installed-wheel smoke: terminal help, command tree, plain fallback, autonomy profiles, task/memory/index/job/branch-search commands, daemon lifecycle, eval profiles, and deterministic eval smoke passed
- manual validation: `GBX-894` found no manual blocker, but retained residual risks for Playwright rerun environment limits, screen-reader non-claims, advisory provider confidence, and final gate dependency; the final gate dependency is resolved by this pass

## Known Residual Risks

- Live-provider canaries are skipped by default in the final gate and remain advisory. Provider recommendation evidence for release work can report `risky` and `low` confidence when retained canary evidence is stale, incompatible, or missing.
- Provider-specific remote cancellation may not stop remote computation immediately, even when local cancellation state is recorded correctly.
- Screen-reader pairings were not executed for v8. Accessibility claims remain limited to named Chromium/Playwright keyboard, mobile, role/name, and semantic evidence; no broad assistive-technology certification is claimed.
- The `GBX-894` targeted Playwright rerun was blocked locally by Next.js watcher `EMFILE` before test execution. The release decision relies on the retained `GBX-886` Chromium/Playwright evidence plus the final frontend gate, and a future manual pass should rerun the targeted workflow with a healthier file-descriptor limit or production server path.
- Repository index state can become stale immediately after source or docs changes. The index is rebuildable with `glassbox repo index build --cwd .`, and stale status should be treated as an operator cue rather than hidden prompt memory.
- v8 autonomy eval cases remain advisory when they use deterministic cancelled-fixture shortcuts or cover workflows that are not yet stable enough to block release by themselves.
- Plain fallback remains necessary for unsupported terminals, redirected streams, and CI-like environments.

## Deliberate Non-Goals

v8 does not introduce a hosted control plane, remote multi-user orchestration, cloud authority for session ownership, cloud workers, simultaneous multi-writer mutation, browser-native code editing as a replacement for local tools, plugin marketplaces, remote policy enforcement, hidden provider-side memory, uninspectable vector-store authority, automatic merging of branch-search candidates into parent history, replacement of deterministic evals with live-provider canaries, or removal of the plain terminal fallback.

Multiple local observers and richer local autonomy are in scope. Multiple concurrent mutation owners and cloud authority are not.

## Release Decision

Decision: GO for v8 release candidate publication.

Decision date: 2026-04-29.

Candidate build reviewed: `GBX-895` release-candidate working tree with final v8 gate evidence.

Retained evidence:

```text
.glassbox/releases/20260429T180807Z-v8-gate/
.glassbox/evals/20260429T180807Z-v8-gate/
```

Final pass/fail state:

| Area | State | Evidence |
| --- | --- | --- |
| Automated v8 gate | passed | `.glassbox/releases/20260429T180807Z-v8-gate/summary.json` records a non-dry-run pass |
| Deterministic eval release report | passed | `.glassbox/evals/20260429T180807Z-v8-gate/release-signoff/` |
| v8 autonomy advisory eval | passed advisory | `.glassbox/evals/20260429T180807Z-v8-gate/autonomy-advisory/` |
| Background autonomy smoke | passed | `.glassbox/releases/20260429T180807Z-v8-gate/background-jobs/summary.json` |
| Manual validation | passed focused review | [manual-v8-release-validation.md](./manual-v8-release-validation.md) |
| Provider canary policy | advisory and skipped by default | final v8 gate summary records explicit non-blocking skip policy |
| Package smoke | passed | final v8 gate installed-wheel smoke and [release-packaging.md](./release-packaging.md) |
| Memory/index posture | passed with stale-index operator cue | final observability output and [recovery-maintenance-review-v8.md](./recovery-maintenance-review-v8.md) |
| Dashboard accessibility review | passed named pairings with non-claims | [dashboard-accessibility-review-v8.md](./dashboard-accessibility-review-v8.md) |
| Residual risk review | accepted for GO decision | known residual risks listed above |

No deterministic blocker remains open. The remaining risks are bounded, documented, and accepted for this release-candidate publication decision.

## Related Files

- [v8-auditable-autonomy-contract.md](./v8-auditable-autonomy-contract.md)
- [v8-autonomy-baseline-inventory.md](./v8-autonomy-baseline-inventory.md)
- [v8-release-gate.md](./v8-release-gate.md)
- [manual-v8-release-validation.md](./manual-v8-release-validation.md)
- [manual-qa-evidence-v8.md](./manual-qa-evidence-v8.md)
- [dashboard-accessibility-review-v8.md](./dashboard-accessibility-review-v8.md)
- [recovery-maintenance-review-v8.md](./recovery-maintenance-review-v8.md)
- [release-packaging.md](./release-packaging.md)
- [task-plans.md](./task-plans.md)
- [workspace-memory.md](./workspace-memory.md)
- [repository-intelligence-index.md](./repository-intelligence-index.md)
- [verification-loops.md](./verification-loops.md)
- [branch-search.md](./branch-search.md)
- [tasks-v8.md](./tasks-v8.md)
