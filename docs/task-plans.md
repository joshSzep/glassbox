# Task Plans

Glassbox v8 introduces task plans as durable runtime state. A task plan is not transcript prose, a dashboard-only checklist, or an eval case. It is an event-sourced object owned by the runtime and linked to the session or turn that produced it when that lineage exists.

## Runtime Boundary

Task plans live in the canonical event stream. The first v8 event payloads cover:

- task creation
- plan proposal and revision
- step start, completion, failure, and skip
- verification start and completion
- pause, resume, cancellation, abandonment, and status changes

The initial model layer is intentionally execution-neutral. It lets Glassbox persist and validate task-plan facts without granting the agent more autonomy yet. Later phases add projections, query services, APIs, background continuation, budgets, verification loops, and dashboard controls on top of these events.

## Projection Boundary

The first task projection tables are:

- `tasks`: one row per durable task plan, including status, blocked reason, current step, source turn, and sequence progress
- `task_steps`: one row per planned step, including plan order, status, summary, failure reason, and blocked reason
- `task_verifications`: one row per verification attempt, including check name, status, summary, artifact pointer, and sequence progress

These tables are derived state. `projection rebuild` must be able to delete and reconstruct them from canonical task-plan events without changing session history.

## CLI Inspection

Phase 82 exposes task plans through read-only CLI commands:

```bash
uv run glassbox task list --cwd .
uv run glassbox task list --session SESSION_ID --cwd .
uv run glassbox task show TASK_ID --cwd .
uv run glassbox task events TASK_ID --cwd .
```

Use `--json` on these commands for scriptable output. These commands inspect projected task state and canonical task events; they do not approve, resume, continue, or mutate task execution.

## HTTP Inspection

The dashboard reads the same task-query layer through typed HTTP routes:

```bash
GET /tasks?session_id=SESSION_ID&cursor=0&limit=100
GET /tasks/TASK_ID
GET /tasks/TASK_ID/steps?cursor=0&limit=100
GET /tasks/TASK_ID/events?cursor=0&limit=100
```

Scoped task list pages and task detail pages include projection health so stale or degraded projections remain visible to operators. These routes are read-only and intentionally do not expose continuation, approval, resume, or cancellation controls.

## Checkpoint Handoff

v10 checkpoints are durable task or session progress records. They are not a
replacement for canonical events, but they give operators the concise "where we
are and what comes next" state needed before reopening a long task.

Use session status for the fastest terminal read:

```bash
uv run glassbox session status SESSION_ID --cwd .
```

When a checkpoint exists, status prints the objective, current phase, last
completed step, next action, blockers, and source event range. The dashboard and
API read the same projection through the session snapshot and checkpoint page:

```bash
GET /sessions/SESSION_ID
GET /sessions/SESSION_ID/checkpoints?cursor=0&limit=100
```

Session exports include a redacted latest checkpoint in the handoff block,
checkpoint-history projection summaries, and canonical checkpoint event
references. Inspect-mode imports replay those checkpoint events into the local
imported session so `task_checkpoints` can rebuild, but the imported session
remains completed and non-resumable until a later v10 task defines custody
transfer.

## Proposal Capture

During a turn, the model may propose durable task state by including one fenced JSON block in its assistant response:

````text
```glassbox-task-plan
{"title":"...","goal":"...","steps":[{"title":"...","description":"..."}]}
```
````

The runtime validates that block with a bounded Pydantic model, creates `TaskCreated` and `TaskPlanProposed` events when it is valid, and leaves normal assistant text untouched. Invalid, ambiguous, or multiple plan blocks are ignored. Captured plans are inspection-only; no step is started or executed by this capture path.

## Handoff And Replay

Session exports include redacted task summaries, step summaries, verification summaries, and canonical task-event references. The references retain enough validated payload data to import task-plan history into a new local session while preserving the import session as completed, inspection-only handoff state.

Replay bundles retain task-plan event metadata and normalize task projections by stable plan content rather than volatile task identifiers. Replay comparison reports `task_plans drift` separately from transcript, tool, approval, question, cancellation, event-family, and final-state drift so eval triage can point operators at plan proposal or task projection evidence directly.

## Relationship To Existing Objects

Task plans differ from existing runtime objects in these ways:

- **Turns** are model-execution units. A task can span multiple turns, and a turn can create or advance a task.
- **Sessions** are workspace-local histories. A task belongs to one session event stream in v8 Phase 82, with later export/import work preserving task context for handoff.
- **Transcript messages** are conversation content. A task plan may be proposed from assistant output, but the structured plan state is not inferred from transcript text during reads.
- **Eval cases** are deterministic regression fixtures. A task can refer to verification or eval evidence, but it is not itself a release-case definition.
- **Dashboard state** is a projection. The browser may render tasks, but it is not the authority for task lifecycle or plan structure.

## Versioning Posture

Task-plan payloads use the existing `EventEnvelope.event_version` field for persisted event compatibility. New optional fields should be added in later versions only when older readers can ignore them or migration code can explain the change. Projection tables introduced after this contract must remain rebuildable from canonical task events.

## Related Files

- [tasks-v8.md](./tasks-v8.md)
- [v8-auditable-autonomy-contract.md](./v8-auditable-autonomy-contract.md)
- [v8-autonomy-baseline-inventory.md](./v8-autonomy-baseline-inventory.md)
- [architecture.md](./architecture.md)
- [database.md](./database.md)
