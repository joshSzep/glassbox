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
