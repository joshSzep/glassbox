# Workspace Memory Contract

Glassbox workspace memory is a local, event-sourced record of facts an operator has chosen to preserve for one repository or workspace. It is meant to reduce repeated rediscovery while keeping every remembered item inspectable, attributable, exportable, and replay-aware.

Workspace memory is not a hidden model feature. It is not cloud memory, cross-repository sync, provider-side personalization, or vector-store authority. Memory entries only become operationally meaningful when canonical events and projections can explain where they came from, when they were confirmed, when they were used, and why they became stale or invalid.

## Scope And Non-Goals

Workspace memory is scoped to the local workspace by default. User-global preferences, organization-wide memory, and cross-repo synchronization require separate contracts. Later tasks may add import/export and candidate extraction, but GBX-850 defines only the vocabulary and canonical event shape.

Non-goals:

- cloud-hosted memory
- provider-managed hidden memory
- cross-repository automatic sync
- embedding or vector retrieval authority
- automatic persistence of model claims without review
- replacing session events, artifacts, docs, evals, or source files as sources of truth

## Entry Types

Memory entries use explicit categories so operators can audit what kind of knowledge is being carried forward:

- `fact`: stable workspace-local fact, such as a service boundary or retained artifact location
- `convention`: local coding, test, release, or documentation convention
- `command`: command that has been verified in this workspace
- `failure_pattern`: repeated failure mode and known recovery path
- `architecture_note`: durable design or ownership observation
- `user_preference`: operator preference that applies to this workspace only
- `task_outcome`: durable result of a completed task or validation pass

## States And Freshness

Memory entries start as event-backed entries and may be projected into these states:

- `active`: eligible for inspection and, in later tasks, prompt context
- `stale`: still inspectable but not eligible for prompt use unless explicitly requested
- `invalidated`: contradicted by newer evidence or operator decision
- `imported`: brought in through an explicit import path and requiring review posture
- `pruned`: removed from active projections while canonical source events remain

Freshness is determined from event evidence, confirmation time, source links, and invalidation events. Staleness must be visible in CLI/API surfaces before any prompt use is allowed.

## Provenance

Every memory entry requires inspectable provenance. Valid source classes are:

- `operator`: explicit operator input
- `session_event`: a canonical session event and sequence
- `task`: a durable task plan or step
- `artifact`: a retained artifact
- `tool_result`: a tool call result
- `runtime_note`: a runtime note promoted by the operator
- `import`: explicit import bundle or file

A memory entry should link to the strongest available source. Session-event provenance requires both `session_id` and `source_sequence`; task, artifact, and tool-result provenance require their corresponding IDs.

## Confirmation And Invalidation

Confirmation is explicit evidence that an operator or trusted workflow reviewed the memory. Confirmation does not erase provenance; it adds confidence and a reviewer.

Operator-confirmed capture can happen from direct notes or generated candidates. Candidates are deterministic suggestions from explicit local signals such as runtime notes and task outcomes. They are not persisted as memory until an operator confirms them; explicit rejection is recorded as review evidence so the same candidate does not keep reappearing.

Invalidation is also explicit. Invalidated memory must record who invalidated it and why. Invalidated entries remain explainable for replay and audit, but later context builders must not include them silently.

Updates should preserve lineage. If an update changes meaning substantially, implementations should prefer invalidating the old entry and creating a new one with linked provenance rather than mutating away history.

## Prompt Use And Replay

Memory may influence model turns only when use is recorded. `WorkspaceMemoryUsedInContext` records the memory ID, turn ID, prompt section, state at use, and reason. This gives replay enough evidence to explain context influence and report drift if memory availability changes.

Prompt fragments should remain separated from repository context, runtime notes, task plans, and transcript content. Future context builders should enforce count, freshness, and byte budgets rather than flattening memory into invisible prompt text.

## Export, Import, And Redaction

Exports must include memory content, state, provenance, confirmation metadata, invalidation metadata, tags, and redaction flags. Secrets and credentials must be redacted before export; redacted imports should remain marked as imported or require confirmation before active prompt use.

Imports append `WorkspaceMemoryImported` events instead of directly writing projections. Imported entries must retain their import source and should not silently override active local entries.

## Pruning

Pruning removes entries from active projections or marks them as pruned, but it must not delete canonical memory events. Prune commands should support dry-run output and name why each entry is eligible.

## Relationship To Existing Context

Workspace memory complements, but does not replace, the bounded runtime context described in [runtime-context.md](./runtime-context.md). It should support team workflows described in [team-workflows.md](./team-workflows.md) by making local conventions and repeated outcomes inspectable. Session export behavior must preserve the source events needed to explain memory provenance and prompt use.

## Canonical Events

GBX-850 introduces these canonical event payloads:

- `WorkspaceMemoryCreated`
- `WorkspaceMemoryConfirmed`
- `WorkspaceMemoryUpdated`
- `WorkspaceMemoryInvalidated`
- `WorkspaceMemoryImported`
- `WorkspaceMemoryUsedInContext`
- `WorkspaceMemoryPruned`

Projection, CLI, API, import/export, and prompt-use behavior are implemented in later Phase 85 tasks.
