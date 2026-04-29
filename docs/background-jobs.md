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
- `BackgroundJobCancellationRequested`: records cancellation intent and reason.
- `BackgroundJobCancelled`: records cancellation acknowledgement and final reason.
- `BackgroundJobRecoveryRecorded`: records stale-owner, daemon-restart, duplicate-claim, projection-rebuild, or operator-requested recovery evidence.

## Queueing And Claiming

A job is eligible for claim when it is queued, not cancelled, not completed, not paused, and has no unexpired active claim. Claiming must be atomic at the repository boundary in GBX-841 so two daemon loops cannot both own the same job.

A duplicate claim must not silently win. It should leave recovery or conflict evidence that names the observed worker ids and claim tokens. If the old claim is stale, recovery is recorded before a new claim starts.

## Cancellation, Pause, Resume, And Retry

Cancellation is request/acknowledge. `BackgroundJobCancellationRequested` makes intent visible immediately; the owner records `BackgroundJobCancelled` only after reaching a safe boundary.

Pause is for durable stops that may be resumed without losing evidence. Mutating jobs pause on approval required, pending user question, policy block, budget exhaustion, verification failure, provider unavailable, daemon unavailable, ambiguous plan, or manual pause.

Resume should append a new claim/start sequence rather than relying on old process state. Retry policies are defined in GBX-844. Until then, retryable failures are evidence only.

## Stale-Owner Recovery

Daemon status may report a stale owner when metadata exists but the recorded process is gone or unreachable. Background jobs use the same principle: if a claim expires or the owner metadata is stale, the next daemon recovery pass records `BackgroundJobRecoveryRecorded` before changing the projected job state.

Recovery must be deterministic from canonical events. Projection rebuild must not invent new recoveries; it should reproduce the last recorded recovery state.

## Observability

Operator surfaces should eventually expose:

- pending, claimed, running, paused, failed, cancelled, stale, and completed counts
- current job id, job type, authority class, attempt, worker id, and lease expiry
- last heartbeat and progress message
- last failure kind and retryability
- cancellation requests awaiting acknowledgement
- recovery events and stale-owner reasons

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
- [daemon-release-smoke-v6.md](./daemon-release-smoke-v6.md)
- [tasks-v8.md](./tasks-v8.md)
