# Glassbox v16 Operator Flow Audit

For the docs hub and operator guides, start at [README.md](./README.md). This
audit records the current next-action, readiness, verification, recovery, and
evidence-support surfaces before v16 operator flow compression work. It follows
the boundary in the
[v16 operator flow compression contract](./v16-operator-flow-compression-contract.md)
and the task graph in [tasks-v16.md](./tasks-v16.md).

The audit is intentionally descriptive. It does not introduce a new operator
queue, evidence graph, verification plan lifecycle, or dashboard behavior.

## Audit Method

This pass reviewed current source modules, command-guide output, API response
models, dashboard components, and existing docs for places that emit:

- next actions or safe next actions
- readiness, handoff, verification, or recovery posture
- blocker, stale, degraded, manual-only, advisory, skipped, or accepted-risk
  language
- provenance, evidence, limitation, or non-claim language
- queue membership, priority, or attention routing

Command-guide evidence came from `uv run glassbox command guide --json`, which
currently exposes workflow sections for start, inspection, unblock, long-run
recovery, compaction, tool attempts, checkpoint inspection, verification
recommendations, provider posture, knowledge freshness, branch-search review,
review loop, workspace recovery, and release evidence.

## Current Priority Vocabulary

| Surface | Current labels | Shape | Disposition |
| --- | --- | --- | --- |
| Session aggregate queue | `approvals`, `questions`, `failures`, `degraded`, `active`, `action-needed`, `historical` | Typed runtime/API/frontend fields | Unify now |
| Session priority buckets | `approvals`, `questions`, `failures`, `degraded`, `provider_recovery`, `recovery`, `stuck`, `stale`, `running`, `idle_running`, `historical` | Runtime strings in session aggregation | Unify now |
| Task status | task plan statuses plus blocked reason and `next_action_summary` | Typed task state plus prose action | Unify now |
| Changeset verification readiness | `passed`, `failed`, `missing`, `stale`, `accepted_with_risk`, and not-applicable states from core enums | Typed readiness model plus prose safe actions | Unify now |
| Commit and handoff readiness | ready, blocked, stale, accepted-risk style states from changeset readiness and handoff signals | Typed models plus safe action strings | Unify now |
| Observability | `ok`, `stale`, `unavailable`, `degraded`, failed/stale job counts, storage warning, provider freshness | Typed section reports with local next-action lists | Unify now |
| Repository intelligence | `fresh`, `stale`, `missing`, `degraded`, `conflicting`, `partial`; severity `advisory`, `warning`, `blocking` | Typed freshness cues | Preserve and align |
| Knowledge posture | cue-driven inspection commands and freshness posture | Typed cues plus command strings | Preserve and align |
| Command guide | workflow section names and command purpose prose | Static structured data | Preserve local copy |
| Dashboard workspace overview | queue tabs and workspace attention levels | Frontend labels derived from API aggregate | Unify now after backend queue contract |

## Surface Inventory

### Session Status And Aggregate

Source: `src/glassbox/runtime/session_query_models.py`,
`src/glassbox/runtime/session_query_helpers.py`,
`src/glassbox/runtime/operator_session_queries.py`,
`src/glassbox/web/session_api_aggregate.py`, and
`frontend/components/console/workspace-overview/queue-descriptors.ts`.

Current behavior:

- `SessionSummaryView` exposes `next_action_summary` as a single prose string.
- `next_action_summary()` derives local action copy from projection health,
  turn recovery, budget posture, pending questions, pending approvals, running
  state, failure state, completion, and cancellation.
- `OperatorSessionSummaryView` adds queue memberships, priority bucket,
  priority rank, action-needed booleans, live-actionable booleans, and
  historical flags.
- `SessionAggregateView` and `SessionAggregateResponse` expose session queue
  counts, projection-health counts, runtime summary, provider evidence,
  repository intelligence, knowledge posture, and prioritized sessions.
- The dashboard queue descriptors mirror the current session queues and are
  session-row oriented.

Gaps:

- The queue is session-centered, not a workspace-wide item model. Failed jobs,
  stale repository intelligence, unresolved review feedback, stale changeset
  inventory, verification gaps, memory conflicts, projection drift, and
  artifact pressure appear indirectly or in separate panels.
- `next_action_summary` is prose-only and has no typed target, evidence
  reference, safety class, confidence, missing evidence, stale evidence, or
  limitation fields.
- Priority buckets include recovery and provider-recovery states that are not
  available as first-class queue families.

Disposition: unify now. The existing session queue is the strongest baseline
for `GBX-1620`, but v16 should generalize it into queue items rather than only
session rows.

### Task Detail And Task Queue

Source: `src/glassbox/runtime/task_query_models.py`,
`src/glassbox/runtime/task_query_assembly.py`,
`src/glassbox/cli/task_commands.py`, `src/glassbox/web/task_api.py`, and
`frontend/stores/task-store.ts`.

Current behavior:

- `TaskSummaryView` has typed task status, blocked reason, current step, step
  count, and `next_action_summary`.
- `next_action_summary(record)` maps task state to prose such as blocked,
  review proposed plan, continue current step, resume or cancel, historical
  task, inspect failure evidence, or inspect task.
- `TaskDetailView` exposes steps, verification rows, verification summary,
  drift assessment, last-known-good evidence, and repair history.
- The dashboard task store has a task queue filter independent of the session
  aggregate queue.

Gaps:

- Task next actions are prose-only and do not cite the step, verification
  ledger row, checkpoint, budget posture, or recovery evidence that caused the
  action.
- Task queue filters are not aligned with session aggregate queue families.
- Repair history and last-known-good evidence are typed, but not connected to
  an evidence graph or shared next-action model.

Disposition: unify now for typed next actions; preserve task-specific repair
detail.

### Changesets, Review Feedback, And Local Review Loop

Source: `src/glassbox/runtime/changesets.py`,
`src/glassbox/runtime/changeset_detail.py`,
`src/glassbox/runtime/review_response_status.py`,
`src/glassbox/runtime/review_response_models.py`,
`src/glassbox/cli/changeset_command_formatters.py`,
`src/glassbox/web/routes/changesets.py`, and
`frontend/components/console/changeset-console.tsx`.

Current behavior:

- Changeset detail includes source records, inventory status, verification
  posture, command evidence, review briefs, manual evidence, review feedback,
  response summaries, readiness decisions, limitations, and safe next actions.
- Review feedback status derives stale response posture, blockers, accepted
  risks, verification-safe next actions, and non-approval claims.
- CLI changeset output prints safe next actions, stale verification guidance,
  response blockers, limitations, and handoff blockers.
- Web routes expose create, show, feedback, fixup, manual evidence,
  browser/accessibility evidence, refresh, verification-plan preview, commit
  readiness, and handoff readiness.

Gaps:

- Changeset safe actions are lists of strings, often domain-useful but not
  typed with target, priority, evidence references, stale inputs, or safety
  class.
- Review feedback, fixup inventory, verification posture, manual evidence,
  command evidence, commit readiness, and handoff readiness are adjacent but
  not connected through one claim-support graph.
- Dashboard actions are workflow-specific and useful, but there is no unified
  operator queue item that says why a changeset needs review, verification,
  refresh, feedback resolution, handoff inspection, or accepted-risk review.

Disposition: unify now for next actions and evidence graph links; preserve
changeset-specific copy and non-publication warnings.

### Handoff And Commit Readiness

Source: `src/glassbox/runtime/commit_readiness.py`,
`src/glassbox/runtime/commit_readiness_signals.py`,
`src/glassbox/runtime/handoff_readiness.py`,
`src/glassbox/runtime/handoff_readiness_signals.py`, and
`src/glassbox/runtime/handoff_readiness_evidence.py`.

Current behavior:

- Commit readiness is read-only and advisory. It combines changeset detail,
  verification preview, review response summary, manual evidence, readiness
  records, git status, workspace diff, and staged diff.
- Handoff readiness is also advisory. It combines changeset, inventory,
  verification plan preview, review briefs, review response summary, manual
  evidence, readiness, and commit readiness.
- Both models expose state, reason, blockers, safe next actions, evidence
  references, signals, and non-claims.

Gaps:

- Signals are typed locally, but their support relationships are not exposed as
  graph edges for "this blocker is supported by this inventory, feedback,
  manual evidence, or command evidence."
- Safe next actions are string lists. They should become typed records while
  retaining compact human output.

Disposition: unify now for claim support and typed next actions; preserve
readiness-specific signal semantics.

### Verification Readiness And Verification Recommendations

Source: `src/glassbox/runtime/changeset_verification_readiness.py`,
`src/glassbox/runtime/changeset_verification_preview.py`,
`src/glassbox/runtime/eval_recommendations.py`,
`src/glassbox/runtime/eval_recommendation_models.py`,
`src/glassbox/runtime/eval_recommendation_output.py`,
`src/glassbox/cli/replay_eval_commands.py`, and
`src/glassbox/cli/changeset_commands.py`.

Current behavior:

- Changeset verification readiness derives requirements from change inventory,
  inventory freshness, task verification ledger, eval recommendations,
  workspace profile, and retained command evidence.
- The model exposes requirement state, command, changed paths, verification ID,
  artifact ID, blocking flag, evidence summary, safe next actions, aggregate
  counts, and non-claims.
- Verification preview expands eval recommendations, recipes, path targets,
  profiles, release surfaces, stale evidence previews, retained artifacts, and
  manual or skipped advisory evidence limitations.
- `eval recommend` and `repo recommend` guide operators to likely checks, with
  `eval recommend --execute` as an explicit execution path outside changeset
  verification-plan preview.

Gaps:

- The current changeset verification plan is a preview, not a persisted plan
  lifecycle with selected, skipped, running, passed, failed, stale,
  superseded, accepted-risk, manual-only, and blocked states.
- Safe next actions and recommended targets lack shared next-action identity
  and evidence graph references.
- Manual, skipped, browser, accessibility, provider, and stale evidence are
  visible, but their claim-support relationships are not queryable.

Disposition: unify now for v16 verification plan lifecycle; preserve current
preview as a non-mutating baseline.

### Repository Intelligence And Path-To-Verification Guidance

Source: `src/glassbox/runtime/repository_intelligence_freshness.py`,
`src/glassbox/runtime/repository_intelligence_queries.py`,
`src/glassbox/runtime/eval_recommendation_repository_intelligence.py`,
`src/glassbox/web/repository_intelligence_api.py`,
`src/glassbox/web/repository_index_routes.py`, and
`frontend/components/console/knowledge-autonomy-console.tsx`.

Current behavior:

- Repository intelligence freshness cues are typed with source, state, reason,
  severity, detail, safe next actions, and limitations.
- Repository index routes expose safe next actions on status and refresh
  paths.
- Path-to-verification guidance uses repository intelligence for command
  recipes, path ownership, package boundaries, release surfaces, confidence,
  warnings, and stale intelligence limitations.
- Dashboard knowledge panels show repository overview, freshness, path
  inspection, recipes, and repository-memory posture.

Gaps:

- Repository intelligence cues already resemble v16 maintenance/knowledge
  queue items, but they are not ranked against sessions, changesets, tasks,
  jobs, artifacts, or verification gaps.
- Freshness cues cite source classes but do not become evidence graph nodes
  supporting or limiting downstream recommendations.
- Missing repository intelligence is advisory by default and must stay that
  way, except where a narrower surface explicitly treats stale inputs as a
  local readiness blocker.

Disposition: preserve and align. Use the existing cue schema as input to queue
and evidence graph models.

### Memory And Knowledge Posture

Source: `src/glassbox/runtime/knowledge_posture.py`,
`src/glassbox/runtime/knowledge_posture_models.py`,
`src/glassbox/runtime/knowledge_posture_guidance.py`,
`src/glassbox/runtime/workspace_memory_capture.py`,
`src/glassbox/cli/memory_commands.py`, and `frontend/stores/knowledge-store.ts`.

Current behavior:

- Knowledge posture converts memory, repository index, checkpoint, compaction,
  verification, and provider evidence into cues and safe inspection commands.
- Workspace memory tracks active, stale, imported, invalidated, pruned,
  redacted, and conflict states.
- Guidance helpers return inspection commands for memory list, repository
  status, session status, compactions, eval audit, and provider canary
  evidence.

Gaps:

- Knowledge posture has cue and inspection-command structure, but it is not
  deduped into the session aggregate queue or changeset guidance.
- Memory conflicts and stale memory-derived repository guidance are not ranked
  beside other operator work.
- Confirmed-memory provenance and prompt-use records are not represented in a
  graph that can explain why memory did or did not shape a recommendation.

Disposition: preserve and align; queue memory conflicts and stale prompt-use
posture as maintenance/advisory items.

### Observability, Daemon Jobs, Recovery, Artifacts, Backups, And Projections

Source: `src/glassbox/runtime/observability_models.py`,
`src/glassbox/runtime/observability.py`,
`src/glassbox/runtime/background_jobs.py`,
`src/glassbox/runtime/tool_attempt_recovery_models.py`,
`src/glassbox/store/artifact_retention.py`,
`src/glassbox/store/workspace_backup.py`,
`src/glassbox/cli/job_commands.py`,
`src/glassbox/cli/observability_commands.py`, and
`src/glassbox/cli/backup_commands.py`.

Current behavior:

- Observability report sections expose next actions for runtime, event
  transport, projections, artifacts, verification, background jobs, task
  autonomy, memory, repository index, repository intelligence, branch search,
  and provider canary evidence.
- Background jobs track pending, running, stale, failed, retryable, and
  abandoned counts with retry commands available from job CLI surfaces.
- Session status exposes checkpoint absence and turn recovery posture with
  next actions.
- Command guide recovery sections recommend safe inspection before resume,
  retry, abandon, rebuild, prune, or backup operations.

Gaps:

- Maintenance and recovery state is typed in separate reports, but not ranked
  beside user-facing work.
- Artifact pressure, backup posture, projection drift, stale daemon ownership,
  and failed jobs are mostly expert surfaces or dashboard side panels.
- Recovery next actions cite commands, but not a shared safety class or claim
  support relationship.

Disposition: unify now as maintenance queue input; preserve command-guide safe
inspection wording.

### Branch Search

Source: `src/glassbox/runtime/branch_decision_support.py`,
`src/glassbox/runtime/branch_decision_evidence.py`,
`src/glassbox/runtime/branch_decision_risk.py`,
`src/glassbox/runtime/observability_branch_search.py`,
`src/glassbox/cli/branch_search_commands.py`, and
`frontend/components/console/branch-search-console.tsx`.

Current behavior:

- Branch-search surfaces track candidate status, verification posture,
  retained evidence, risk posture, selected/rejected/needs-review state, and
  safe next actions during adoption preview.
- Observability counts active, completed, abandoned, needs-review, failed
  verification, and selected branch searches.

Gaps:

- Branch-search needs-review and failed-verification states do not feed the
  existing session queue.
- Candidate evidence is domain-specific and useful, but it is not represented
  as evidence graph support for adoption, rejection, or changeset creation.

Disposition: preserve local copy for branch-specific comparison; add queue and
evidence graph integration after shared models exist.

### Dashboard Overview And Console Panels

Source: `frontend/components/console/workspace-overview.tsx`,
`frontend/components/console/workspace-overview/workspace-attention-summary.tsx`,
`frontend/components/console/workspace-overview/queue-navigation.tsx`,
`frontend/components/console/session-inspector.tsx`,
`frontend/components/console/task-autonomy-console.tsx`,
`frontend/components/console/changeset-console.tsx`,
`frontend/components/console/knowledge-autonomy-console.tsx`, and
`frontend/state/workspace-attention.ts`.

Current behavior:

- Workspace overview shows a server-prioritized session queue, workspace
  attention summary, runtime state rail, recovery cues, knowledge/autonomy
  panels, and session rows.
- Changeset, task autonomy, branch search, verification cues, and knowledge
  panels expose their own local action states and evidence summaries.
- Frontend stores normalize provider evidence, repository intelligence,
  knowledge posture, queue counts, and selected queue.

Gaps:

- Dashboard attention is not one queue across sessions, changesets, tasks,
  verification, repository intelligence, memory, jobs, artifacts, and
  maintenance.
- Evidence is shown as local panel content rather than claim-support
  neighborhoods.
- Queue labels are frontend mirrors of current session aggregate queues, so
  adding workspace-wide item families requires backend type changes first.

Disposition: unify after `GBX-1622`; preserve existing panels as domain detail
views.

### TUI And Plain Interactive Review

Source: `src/glassbox/cli/tui/commands.py`,
`src/glassbox/cli/tui/review_commands.py`,
`src/glassbox/cli/interactive_review_commands.py`, and
`src/glassbox/cli/interactive_review_guidance.py`.

Current behavior:

- Plain interactive review commands expose `/review` entry points for
  changeset creation, refresh, verification preview, feedback, fixup,
  evidence, brief, and handoff readiness.
- TUI command modules provide command parsing and review command integration
  around existing CLI/runtime behavior.

Gaps:

- There is no TUI-wide operator queue or evidence graph inspection entry point.
- Plain interactive review is changeset-centered, not workspace attention
  centered.

Disposition: preserve current `/review` flow; add queue, evidence graph, and
verification plan entry points after backend/API models land.

### Command Guide

Source: `src/glassbox/cli/command_guide_data.py`,
`src/glassbox/cli/command_guide_workflows.py`, and live output from
`uv run glassbox command guide --json`.

Current behavior:

- Command guide already groups commands around workflows: start work, inspect
  state, unblock work, long-run recovery, compaction, tool attempts,
  checkpoint inspection, verification recommendations, provider posture,
  knowledge freshness, branch-search review, review-loop maturity, workspace
  recovery, and release evidence.
- Purpose copy consistently reinforces inspection before mutation and
  non-publication boundaries for changesets, handoff, provider evidence, and
  release evidence.

Gaps:

- Workflow group constants exist, but the CLI currently exposes only the full
  guide and does not filter by workflow.
- Command guide purposes are static prose. Queue items cannot point to stable
  command-guide entries yet.

Disposition: preserve local copy; later queue actions should reference command
guide sections or command recipes rather than duplicate long help text.

## Duplicated Derivation To Address

- Session aggregate and dashboard workspace attention both rank session
  attention, while observability separately ranks runtime, projections, jobs,
  artifacts, verification, memory, repository intelligence, branch search, and
  provider evidence.
- Changeset detail, verification preview, commit readiness, handoff readiness,
  review response status, and review briefs each derive safe next actions from
  overlapping changeset evidence.
- Knowledge posture and repository intelligence freshness both emit safe
  inspection commands for stale or missing repository knowledge.
- Command guide, CLI human output, frontend action labels, and API `next_actions`
  copy repeat similar safe commands without shared identity.
- Task repair history, tool-attempt recovery, checkpoint absence, and turn
  recovery each explain recovery posture without one evidence graph vocabulary.

## Disposition Summary

| Disposition | Surfaces |
| --- | --- |
| Unify now | Session aggregate queue, task next actions, changeset safe actions, verification readiness, commit/handoff readiness, observability next actions, dashboard workspace attention |
| Preserve local copy | Command guide workflow descriptions, branch-search candidate comparison language, changeset non-publication warnings, handoff non-claims, provider advisory evidence copy |
| Document only | Existing command-guide lack of workflow filtering; current dashboard panel separation before backend queue item models exist |
| Accepted risk | Older sessions may lack newer verification, manual evidence, repository intelligence, or recovery events; v16 should expose sparse and missing evidence rather than backfill false support |
| Not v16 | Hosted review queues, remote indexing, external vector authority, automatic PR publication, automatic staging/committing/pushing/merging/deploying/publishing |

## Implementation Notes For Follow-On Tasks

- `GBX-1610` should start with typed next-action records that can wrap current
  string fields without breaking existing CLI/API output.
- `GBX-1611` should model claim support as derived relationships over existing
  events, projections, artifacts, and response models rather than adding a new
  source of truth.
- `GBX-1620` should generalize the current session aggregate queue into item
  records with family, target, priority, stale state, safe action, evidence
  summary, limitations, and dismissal semantics.
- `GBX-1630` should preserve the current verification preview as planning
  input while adding explicit lifecycle states for selected, skipped, running,
  passed, failed, stale, superseded, accepted-risk, manual-only, and blocked
  checks.
- Frontend work should wait for generated API types from backend queue and
  evidence graph responses, then reuse existing dashboard panels as target
  detail views.
