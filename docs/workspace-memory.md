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
- `repository_intelligence`: a retained repository intelligence snapshot or
  derived repository intelligence record
- `import`: explicit import bundle or file

A memory entry should link to the strongest available source. Session-event provenance requires both `session_id` and `source_sequence`; task, artifact, and tool-result provenance require their corresponding IDs. Repository-intelligence provenance requires a source label such as a command recipe, package, generated path, or release surface, plus freshness and snapshot metadata in the note field.

## Confirmation And Invalidation

Confirmation is explicit evidence that an operator or trusted workflow reviewed the memory. Confirmation does not erase provenance; it adds confidence and a reviewer.

Operator-confirmed capture can happen from direct notes or generated candidates. Candidates are deterministic suggestions from explicit local signals such as runtime notes and task outcomes. They are not persisted as memory until an operator confirms them; explicit rejection is recorded as review evidence so the same candidate does not keep reappearing.

Long-running tasks add more review-only candidate sources. Glassbox may propose
memory from durable checkpoints, fresh compactions, last-known-good verification
records, verified commands, repeated verification failures, and accepted
residual risks. These candidates keep provenance back to the source event
sequence and artifact link when one exists. Stale or invalidated compactions do
not produce active candidates by default, and redaction runs before candidates
appear in CLI/API/dashboard review surfaces.

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

## Repository Intelligence Integration

Repository intelligence may use workspace memory only as review-gated local
evidence. Confirmed active entries can enrich repository-intelligence snapshots,
path-to-verification recommendations, dashboard cues, and bounded turn context
when the consumer can cite the memory ID, kind, state, confirmation metadata,
source label, freshness posture, confidence, and limitations.

Eligible memory-derived repository intelligence includes:

- repository facts about local structure, retained artifacts, package quirks, or
  generated-output conventions
- conventions for coding, testing, docs, release, review, or handoff workflows
- verified commands and command recipes that remain advisory until explicitly
  executed
- repeated failure patterns and recovery notes with redaction applied before
  display or export
- architecture notes, owner hints, subsystem notes, and task outcomes that help
  explain why a path matters

Ineligible memory must stay out of repository-intelligence snapshots,
recommendations, and prompt context by default:

- generated candidates that have not been confirmed
- rejected candidates
- stale, invalidated, or pruned entries
- imported entries that have not passed the local review posture
- entries whose provenance cannot be resolved to a canonical event, artifact,
  task, tool result, runtime note, or explicit operator source
- sensitive entries that redaction policy marks unsafe for the target surface

Memory-derived intelligence does not override stronger deterministic source
metadata. If a confirmed convention conflicts with current manifests, source
roots, topology, command evidence, dependency metadata, or release-surface
records, consumers should lower confidence, name the conflict, and suggest
inspection or memory review instead of silently trusting the remembered fact.

Model-assisted suggestions, command-derived candidates, topology-derived
candidates, release-outcome candidates, and failure-pattern candidates remain
review-only until confirmed through the workspace memory flow. Repository
intelligence can show these as memory candidates in review surfaces, but it must
not treat them as active facts, owner assignments, command approvals, release
evidence, or prompt context.

Fresh repository-intelligence snapshots may also propose review-only candidates
for stable command recipes, package conventions, generated-output conventions,
and release-sensitive path notes. Stale snapshots, failed snapshots, missing
snapshots, and low-confidence repository intelligence do not produce active
candidates by default.

Repository intelligence rebuilds may also retain confirmed active memory as
snapshot `memory_references`. These references include memory IDs,
confirmation metadata, tags, redaction posture, provenance, confidence, and
limitations, but they do not flatten memory into hidden repository facts.
Snapshots exclude stale, invalidated, imported-unreviewed, rejected, pruned, and
unconfirmed memory by default.

When memory-derived repository intelligence influences a model turn, the context
builder must record `WorkspaceMemoryUsedInContext` for each included memory ID
and retain enough context snapshot metadata for replay to distinguish behavior
drift from memory availability or freshness drift.

Non-goals for this integration are automatic memory capture, automatic memory
confirmation, cross-repository memory sync, provider-side memory, hidden vector
retrieval authority, automatic owner assignment, command execution approval, or
release authority.

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
