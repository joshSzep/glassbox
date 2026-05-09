# Background Job Ownership And Recovery Contract

Glassbox background jobs are opt-in local work items that a workspace daemon may execute while preserving the same event-sourced authority model used by sessions, tasks, approvals, and budget posture.

The contract in this document defines the durable shape before daemon execution is introduced. It is intentionally local-first: canonical events are the source of truth, projections are rebuildable, and process-local memory is never treated as durable job state.

## Goals

- Let the workspace daemon run bounded local work without creating a second mutation owner.
- Make queued, running, paused, failed, cancelled, stale, and recovered jobs inspectable from events and projections.
- Keep read-only maintenance, derived-index work, and mutating task continuation separate in policy and observability.
- Preserve explicit operator opt-in until release evidence proves the background path is safe.

## Non-Goals

- Remote workers.
- Distributed queues.
- Cloud scheduling.
- Cross-workspace orchestration.
- Running background task continuation without explicit autonomy mode and budget evidence.
- Treating daemon memory, terminal state, or dashboard state as durable job truth.

## Authority And Ownership

A workspace may have one mutation owner at a time. When the daemon owns the workspace, it may claim eligible jobs and append canonical job events. Foreground terminals and dashboard actions remain clients of that owner rather than competing writers.

Background job events are append-only evidence. A queue projection may make jobs fast to list, claim, and inspect, but projections do not own the state. Rebuild must recover the same job queue from canonical events.

A job claim is a leased ownership assertion, not a permanent lock. The daemon records a claim token, worker id, attempt number, and lease expiry. Heartbeats extend the lease and provide operator-visible progress. If the process exits or metadata becomes stale, recovery is recorded with a durable reason before the job is made eligible again or marked stale.

## Job Classes

Glassbox uses three coarse authority classes:

- `read_only_maintenance`: local inspection or health checks that do not mutate sessions, tasks, workspace files, or provider state.
- `derived_index`: rebuildable derived data such as repository indexes, recommendation caches, or projection-derived summaries.
- `mutating_continuation`: explicit task/session continuation that may append session, task, approval, budget, or tool events.

Read-only and derived-index jobs are the first eligible daemon execution targets. Mutating continuation jobs require explicit autonomy mode, budget posture, and stop conditions before they may run.

## Lifecycle States

- `queued`: created and waiting for an eligible owner.
- `claimed`: leased by a worker but not yet started.
- `running`: actively executing and expected to heartbeat.
- `paused`: stopped at a durable boundary such as approval required, policy block, budget exhaustion, verification failure, or ambiguous plan.
- `completed`: finished successfully with a summary and optional artifact evidence.
- `failed`: ended unsuccessfully with a failure class, retryability flag, and attempt number.
- `cancellation_requested`: an operator or runtime requested cancellation; the owner must acknowledge at a safe boundary.
- `cancelled`: stopped because cancellation was acknowledged.
- `stale`: the recorded owner lease or metadata is no longer trustworthy and recovery is required.
- `abandoned`: terminal operator triage state for a job that should not be retried.

## Canonical Events

GBX-840 introduces the canonical event vocabulary. Later storage and daemon tasks project and execute these events.

- `BackgroundJobCreated`: records job id, authority class, job type, title, requester, typed payload, priority, optional task id, and optional parent job id.
- `BackgroundJobClaimed`: records worker id, claim token, attempt, and lease expiry.
- `BackgroundJobStarted`: records the worker and claim token that began execution.
- `BackgroundJobHeartbeat`: records active lease extension, state, and optional progress message.
- `BackgroundJobProgressRecorded`: records operator-facing progress text and optional completed/total units.
- `BackgroundJobPaused`: records an autonomy escalation reason and optional detail.
- `BackgroundJobCompleted`: records completion summary and optional artifact id.
- `BackgroundJobFailed`: records failure kind, message, retryability, attempt, and optional next retry time.
- Failed daemon jobs may also reference a retained session artifact containing
	the failure traceback or tool output that made triage useful.
- `BackgroundJobCancellationRequested`: records cancellation intent and reason.
- `BackgroundJobCancelled`: records cancellation acknowledgement and final reason.
- `BackgroundJobRecoveryRecorded`: records stale-owner, daemon-restart, duplicate-claim, projection-rebuild, or operator-requested recovery evidence.
- `BackgroundJobRetryRequested`: records the operator or runtime decision to return a failed or stale job to the queued state.
- `BackgroundJobRetryExhausted`: records the retry budget and reason when a retry request would exceed the explicit budget.
- `BackgroundJobAbandoned`: records who abandoned the job and why.

## Queueing And Claiming

A job is eligible for claim when it is queued, not cancelled, not completed, not paused, and has no unexpired active claim. Claiming must be atomic at the repository boundary in GBX-841 so two daemon loops cannot both own the same job.

A duplicate claim must not silently win. It should leave recovery or conflict evidence that names the observed worker ids and claim tokens. If the old claim is stale, recovery is recorded before a new claim starts.

## Cancellation, Pause, Resume, And Retry

Cancellation is request/acknowledge. `BackgroundJobCancellationRequested` makes intent visible immediately; the owner records `BackgroundJobCancelled` only after reaching a safe boundary.

Pause is for durable stops that may be resumed without losing evidence. Mutating jobs pause on approval required, pending user question, policy block, budget exhaustion, verification failure, provider unavailable, daemon unavailable, ambiguous plan, or manual pause.

Resume appends a new claim/start sequence rather than relying on old process state.
Retry is explicit: `glassbox job retry JOB_ID` may return failed or stale jobs to
`queued` until the retry budget is exhausted, at which point
`BackgroundJobRetryExhausted` preserves the triage evidence. Read-only and
derived-index failures may be marked retryable by the daemon. Mutating
continuation failures are not automatically retryable; operators must provide an
explicit retry command and budget so continuation restarts happen only from the
event-safe queued boundary.

Abandonment is terminal operator triage. `glassbox job abandon JOB_ID --reason
...` records `BackgroundJobAbandoned` when a job is obsolete, unsafe to retry, or
superseded by newer work.

## Stale-Owner Recovery

Daemon status may report a stale owner when metadata exists but the recorded process is gone or unreachable. Background jobs use the same principle: if a claim expires or the owner metadata is stale, the next daemon recovery pass records `BackgroundJobRecoveryRecorded` before changing the projected job state.

Recovery must be deterministic from canonical events. Projection rebuild must not invent new recoveries; it should reproduce the last recorded recovery state.

## Observability

Operator surfaces should eventually expose:

- pending, claimed, running, paused, failed, cancelled, stale, and completed counts
- current job id, job type, authority class, attempt, worker id, and lease expiry
- last heartbeat and progress message
- last failure kind and retryability
- failed, retryable, and abandoned counts
- cancellation requests awaiting acknowledgement
- recovery events and stale-owner reasons

## Read-Only Daemon Jobs

The v8 daemon worker may execute only read-only maintenance and derived-index jobs.
It must skip mutating continuation jobs until explicit task continuation support is
enabled. The first supported job types are intentionally bounded:

- `projection-health-refresh`: inspects retained session projection health and
	records a completion summary.
- `artifact-pressure-scan`: inspects managed artifact retention pressure without
	pruning files.
- `provider-evidence-freshness-scan`: loads retained provider canary evidence and
	records the latest status.
- `repository-index-refresh`: rebuilds the local repository intelligence index
  as managed `.glassbox` derived state.
- `repository-intelligence-refresh`: rebuilds the repository intelligence index
  and workspace topology together, records progress after each derived artifact,
  and retains a session-scoped summary artifact that explicitly states no source
  files or policy files were mutated.
- `workspace-memory-candidate-scan`: scans retained session evidence for
  review-gated workspace memory candidates without activating unconfirmed facts.

The daemon claims queued eligible jobs with a short lease, records a heartbeat,
records progress, and then records completion or failure. Cancellation requests are
acknowledged with `BackgroundJobCancelled`; expired active claims are recovered as
`stale` with `BackgroundJobRecoveryRecorded` so operators can inspect them before
retry support lands.

Troubleshooting commands:

- `glassbox observability status --json` shows pending, running, stale, failed,
	retryable, abandoned, and latest failed background job state.
- `glassbox daemon status --cwd . --json` is the first safe check when queued,
	running, or stale jobs do not move; it reports not-running, running,
	stale-owner, and unreachable-health recovery guidance without mutating owner
	metadata.
- `glassbox repo refresh --background --session SESSION_ID --cwd .` queues a
  safe daemon refresh for derived repository intelligence.
- `glassbox job retry JOB_ID --reason ...` requeues a failed or stale job until
	the retry budget is exhausted.
- `glassbox job abandon JOB_ID --reason ...` records terminal operator triage.
- `glassbox job list --state stale` shows jobs recovered from expired claims.
- `glassbox job show JOB_ID` shows worker claim, heartbeat, failure, and recovery
	details plus state-specific next actions for retry, abandon, cancel, or daemon
	inspection.
- `glassbox daemon stop` cleanly stops the worker together with the runtime owner.

## Task Continuation Jobs

Task continuation jobs are explicit opt-in mutating jobs scheduled with
`glassbox task continue TASK_ID`. The scheduler enqueues a
`mutating_continuation` job of type `task-continuation-step` and records the
task id both in the typed job field and payload for portability.

The daemon executes at most one pending task step per job. It records
`TaskStepStarted`, submits one bounded continuation prompt through the normal
session service and turn engine, then records `TaskStepCompleted` and completes
the task when no pending steps remain. Continuation stops cleanly and records a
`TaskPaused` boundary when the session is awaiting approval, awaiting user input,
cancelled, failed, or lacks an explicit non-manual autonomy budget.

Continuation jobs do not bypass policy, approval, user-question, or budget
contracts. They use the same foreground session service path as operator-submitted
messages, so pending approvals and questions remain durable stop conditions.

## Test Matrix

GBX-841 and later execution tasks should cover:

- daemon restart with a claimed job and expired lease
- stale owner metadata before claim
- duplicate job claim attempt while the lease is active
- cancellation request before start
- cancellation request while running
- pause on approval required
- pause on budget exhaustion
- read-only job completion
- read-only job failure with retryable evidence
- projection rebuild from canonical job events
- recovery event replay without duplicate recovery creation

## Related Guides

- [persistent-runtime.md](./persistent-runtime.md)
- [background-autonomy-release-smoke-v8.md](./background-autonomy-release-smoke-v8.md)
- [daemon-release-smoke-v6.md](./daemon-release-smoke-v6.md)
- [tasks-v8.md](./tasks-v8.md)
