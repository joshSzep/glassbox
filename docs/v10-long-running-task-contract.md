# Glassbox v10 Long-Running Task Contract

This page defines the v10 product contract for making long-running local agent
work survivable. It is the operator and contributor guide for what
"long-running task capable" means before the implementation details are spread
across checkpoint, compaction, tool-attempt, cockpit, budget, verification, and
provider-recovery tasks.

v10 starts from the v9 public baseline in
[v9-release-candidate.md](./v9-release-candidate.md). The current supported
baseline remains v9 until the v10 release-candidate gate and manual evidence are
published.

## Scope

Glassbox v10 is about durable progress through longer local work. A run should
remain inspectable and recoverable when a process exits, an event stream drops,
a provider call fails, a command runs for a long time, context becomes too large
to review directly, or verification needs to happen before the final answer.

The v10 scope is:

- durable long-run lifecycle state derived from canonical events
- typed task checkpoints with last completed step, next action, blockers,
  verification posture, and recovery guidance
- artifact-backed context compactions with source ranges, provenance,
  staleness posture, and limitations
- durable tool attempt records with heartbeats, partial-output artifacts,
  retry posture, and safe-to-resume classification
- cockpit surfaces that show heartbeat, stuck state, checkpoint, compaction,
  budget, verification, provider recovery, and next actions
- time-aware budgets and checkpoint approvals for bounded continuation
- incremental verification ledgers and last-known-good evidence
- explicit provider failure recovery and fallback recommendations
- deterministic replay/eval evidence for interruption, recovery, compaction,
  checkpoint, and long-run cockpit behavior

The contract does not make every long task automatic. It makes long work
observable, bounded, interruptible, and recoverable enough that an operator can
decide whether continuing is safe.

## Non-Goals

v10 does not introduce a hosted control plane, cloud authority for workspace
ownership, remote worker fleets, simultaneous multi-writer mutation,
provider-side hidden memory, multi-day unattended mutation, automatic merging,
or replacement of deterministic replay/eval authority with live-provider
canaries.

Provider diagnostics, canaries, and recommendations remain advisory unless a
future task promotes a narrow deterministic or repeatable contract with an
explicit failure policy.

Plain terminal fallback remains part of the product. Long-run cockpit polish
may improve the full-screen terminal and dashboard, but unsupported terminals,
redirected streams, and CI-like environments must still have readable command
paths.

## Product Model

The v10 long-run model is a set of durable, inspectable records rather than
private process memory:

| Model | Contract |
| --- | --- |
| Event | Canonical source of truth for lifecycle, checkpoint, compaction, attempt, verification, recovery, approval, and cancellation evidence. |
| Checkpoint | Typed statement of current objective, completed step, next intended action, blockers, verification posture, budget posture, and safe recovery guidance. |
| Compaction | Managed artifact that summarizes transcript, task, file, or verification context with source event ranges, source artifacts, provenance, freshness, and limitations. |
| Attempt | Durable record for model calls and tools, including status, heartbeat, partial output, retry posture, and safe-to-resume classification. |
| Heartbeat | Operator-visible progress evidence for long-running turns, background jobs, and tool attempts. |
| Verification | Incremental ledger of checks, last-known-good state, stale evidence, repair attempts, and remaining risk. |
| Recovery | Explicit next action when work is paused, stale, failed, partially resumed, unsafe to retry, or requires operator approval. |

These records must be reconstructable from canonical events, typed API
responses, retained artifacts, or documented rebuildable projections.

## Canonical Event Vocabulary

`GBX-1010` adds the first v10 event vocabulary without changing runtime
behavior yet:

- `LongRunPhaseChanged`: records phase entry, heartbeat, exit, or blocked state
  for preparing, model call, tool execution, checkpointing, compaction,
  verification, recovery, pause, completion, or failure.
- `TaskCheckpointCreated`: records objective, completed step, next action,
  blockers, verification posture, budget posture, artifact link, and recovery
  guidance.
- `ContextCompactionCreated`: records compaction scope, source event range,
  artifact, freshness, limitations, and related checkpoint/task/turn.
- `ToolAttemptHeartbeat`: records tool-attempt progress, status, output
  artifact, retry posture, and related turn/tool/task identifiers.
- `RecoveryDecisionRecorded`: records whether interrupted work should resume,
  retry, fork, wait for the operator, abandon, or be treated as non-resumable.
- `ResumeOutcomeRecorded`: records whether a resume attempt succeeded, failed,
  or was rejected because the checkpoint was stale or non-resumable.

SQLite stores task, checkpoint, compaction, tool-attempt, and recovery-decision
correlation columns on canonical events and rebuilds a `long_run_events`
projection from those events. Replay normalization includes these long-run event
families so future deterministic cases can compare the durable lifecycle record
without treating projections as authority.

## Supported Workflow Set

The v10 release candidate should support these operator workflows:

- start a long task from `glassbox session chat --cwd .` or daemon-backed
  session commands
- inspect active and historical long-run state from terminal status output and
  the dashboard cockpit
- pause, resume, cancel, approve, deny, answer, or fork work without losing the
  durable explanation of what happened
- review task checkpoints before continuing after interruption or stale owner
  recovery
- review context compactions as artifacts instead of trusting hidden prompt
  state
- inspect tool attempts, partial command output, heartbeat recency, and retry
  safety before rerunning work
- see when verification is fresh, stale, last-known-good, failed, or repaired
- continue work only within explicit time, unattended-duration, checkpoint,
  tool, write, command, branch, artifact, and verification limits
- understand provider failure posture and recommended fallback without treating
  live-provider evidence as release authority
- validate interruption and recovery behavior through replay/eval cases

Existing daily v9 commands remain the discovery baseline:

```bash
uv run glassbox command guide
uv run glassbox command tree
uv run glassbox readiness check --cwd .
uv run glassbox session chat --cwd .
uv run glassbox session status SESSION_ID --cwd .
uv run glassbox session resume SESSION_ID --cwd .
uv run glassbox session cancel SESSION_ID --cwd .
uv run glassbox task list --cwd .
uv run glassbox job list --cwd . --json
uv run glassbox observability status --cwd . --json
uv run glassbox eval run --cwd .
uv run glassbox eval audit --cwd .
```

Future v10 command, API, and dashboard additions should extend this workflow
only when an existing surface cannot make the long-run state or recovery action
clear.

## Evidence Expectations

v10 release evidence is split into blocking deterministic evidence and advisory
operational confidence:

- deterministic replay/eval cases for interruption, restart, checkpoint
  reconstruction, compaction provenance, partial tool output, stale
  verification, budget-window stop reasons, and recovery guidance are blocking
  once promoted into the v10 gate
- CLI, API, and dashboard tests must prove the same durable state is visible
  through operator surfaces
- retained artifacts must include compaction payloads, partial-output evidence,
  verification ledgers, and release summaries when those workflows are tested
- provider recovery evidence is advisory unless a future task explicitly
  changes the policy
- manual evidence should record dashboard and terminal long-run monitoring,
  accessibility pairings, recovery paths, and accepted residual risks

The release-readiness checklist must name these evidence classes separately:

- durable-event lifecycle evidence
- checkpoint model, projection, API, CLI, export, and resume evidence
- compaction artifact, provenance, freshness, and prompt-integration evidence
- resumable-tool attempt, heartbeat, partial-output, retry, and recovery
  evidence
- dashboard and terminal cockpit heartbeat, stuck-state, timeline, and next
  action evidence
- time-window, unattended-duration, checkpoint-approval, and scheduled-stop
  budget evidence
- incremental verification, stale-drift, last-known-good, and repair evidence
- provider failure, model-switch, fallback, and advisory-posture evidence
- replay/eval release evidence that can run without live-provider authority

## v9 Residual-Risk And Dogfooding Mapping

| Input | v10 disposition |
| --- | --- |
| Browser-rendered dashboard keyboard and mobile evidence was blocked in the v9 environment. | Covered by the long-run cockpit work and v10 manual evidence. Until rerun, browser evidence remains a release-candidate evidence gap rather than a runtime authority. |
| Screen-reader pairings were not executed for v9. | Covered by v10 manual validation and accessibility pairings for long-run cockpit surfaces. No broad assistive-technology certification is claimed. |
| Full-screen TUI was not manually recorded for v9. | Covered by terminal cockpit and manual evidence tasks. Plain mode remains the supported fallback. |
| Repository index was stale after v9 docs and gate changes. | Treated as a long-run freshness and verification-drift concern. Rebuildable index state remains acceptable, but stale state must produce clear recovery guidance. |
| Provider canary evidence was fresh but partial for release-candidate work. | Covered by provider failure recovery and fallback recommendations. Provider evidence remains advisory. |
| Plain fallback remains necessary. | Accepted product constraint and explicit compatibility path. |
| Dogfooding found docs-index and workflow-friction gaps. | Feeds the durability audit, compaction provenance, cockpit next-action, and long-run verification tasks. Findings must become fixes, docs, tests/evals, accepted risks, or post-v10 tasks. |

## Pass And Fail Policy

A v10 release candidate can pass only when deterministic blocking stages pass
and every residual risk is documented with scope, mitigation, and owner. Any
failure in promoted replay/eval, checkpoint reconstruction, compaction
provenance, budget stop reason, verification ledger, or recovery guidance
evidence blocks release.

Live-provider failures do not block by default. They must be visible,
redacted, current enough to interpret, and clearly marked advisory.

## Related Files

- [tasks-v10.md](./tasks-v10.md)
- [v9-release-candidate.md](./v9-release-candidate.md)
- [v9-public-baseline.md](./v9-public-baseline.md)
- [dashboard-cockpit-contract.md](./dashboard-cockpit-contract.md)
- [task-plans.md](./task-plans.md)
- [runtime-context.md](./runtime-context.md)
- [background-jobs.md](./background-jobs.md)
- [verification-loops.md](./verification-loops.md)
- [providers.md](./providers.md)
- [replay-evals.md](./replay-evals.md)
