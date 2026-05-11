# Unified Operator Queue Contract

The v16 operator queue is a shared vocabulary for local attention needs. It is
derived guidance, not hidden automation. Queue items can recommend inspection,
approval, review, verification, refresh, recovery, or maintenance actions, but
they do not grant permission to mutate the workspace or publish results.

## Item Vocabulary

Each queue item uses `OperatorQueueItem` from `glassbox.core`:

- `family`: separates work-blocking, review-blocking, verification-blocking,
  maintenance, advisory, and informational items.
- `state`: describes current posture: action needed, blocked, active, stale,
  degraded, ready, watching, or historical.
- `priority` and `severity`: reuse the v16 next-action priority and severity
  vocabulary so queue sorting and next actions agree.
- `target`: names the local object that needs attention, such as a session,
  task, changeset, review-feedback item, verification, repository intelligence,
  memory entry, background job, artifact, provider, projection, or release gate.
- `owner_surface` and `owner_label`: tell the UI or CLI where the operator can
  understand the item without guessing which subsystem produced it.
- `safe_next_action`: carries the typed advisory action. Its target must match
  the queue item target.
- `evidence_summary`: names support, missing evidence, stale evidence, optional
  evidence graph IDs, claim IDs, and limitation counts without returning raw
  artifacts.
- `dedupe_key`: lets aggregators merge items that point at the same underlying
  problem.
- `dismissal_policy`: says whether the item can be hidden temporarily, hidden
  for the session, or only cleared by a canonical operator decision event.

## Families

`work_blocking` items stop current agent progress, such as pending approvals,
unanswered questions, stuck turns, failed turns, blocked tasks, or provider
configuration failures.

`review_blocking` items stop review handoff, such as unresolved review feedback,
missing response-linked fixup evidence, accepted risks, stale changeset
inventory, or handoff readiness blockers.

`verification_blocking` items stop confidence claims, such as failed checks,
missing release-gate evidence, stale verification ledgers, or skipped checks
that are required by the current profile.

`maintenance` items describe operational upkeep, such as stale repository
intelligence, stale context compactions, failed background jobs, projection
drift, artifact pressure, backup gaps, or daemon health problems.

`advisory` items are useful but not blocking by themselves, such as optional
repository intelligence absence, browser evidence suggestions, manual evidence
limitations, or provider canary warnings that do not affect the active task.

`informational` items help explain state without asking for action, such as
historical sessions, completed handoffs, retained evidence packages, or
recently refreshed intelligence.

## Dedupe Rules

Queue aggregators should produce deterministic IDs and dedupe keys:

- Use `target` for one visible item per local target when domain details do not
  matter.
- Use `family_target` when one target may have separate work, review,
  verification, and maintenance needs.
- Use `evidence_fingerprint` when the same missing or stale evidence appears
  through several surfaces.
- Use `workspace_singleton` for workspace-wide health items such as daemon,
  backup, artifact pressure, provider posture, or repository intelligence.

When deduping, keep the highest priority, the highest severity, the most recent
`updated_at`, and the richest evidence summary. Preserve domain-specific
meaning in `family`, `state`, and `owner_label` instead of collapsing everything
into a generic warning.

## Dismissal Semantics

Queue items are derived from local evidence unless a canonical event records an
operator decision. Dismissal policy controls only presentation:

- `not_dismissible`: always show while the evidence still exists.
- `dismissible_until_changed`: hide until the target evidence changes.
- `dismissible_for_session`: hide for the current local session only.
- `canonical_decision_required`: clear only after an approval, answer,
  risk-acceptance, archive, resolve, retry, abandon, refresh, or equivalent
  domain event records the decision.

Optional repository intelligence absence must not block normal chat. It should
use maintenance or advisory families unless a later release contract explicitly
requires it for the requested workflow.

## Runtime Aggregation

`glassbox.runtime.operator_queue.build_operator_queue` derives the first runtime
queue from existing aggregate session evidence and workspace runtime health.
The initial producer covers pending approvals, pending questions, failed
sessions, degraded session projections, stale or stuck long-running sessions,
active turns, and failed or retryable background jobs. Later v16 slices extend
the same contract to changesets, review feedback, verification ledgers,
repository intelligence, memory posture, artifact pressure, provider posture,
release gates, and dashboard/TUI presentation without changing item semantics.

Runtime sorting is deterministic:

1. priority
2. severity
3. action-needed posture
4. stale posture
5. newest update time
6. target kind and target ID
7. item ID

Aggregators dedupe by `dedupe_key.key` and keep the strongest item according to
that same ordering. This lets several projections point at the same problem
without multiplying rows or erasing the domain-specific owner label.
