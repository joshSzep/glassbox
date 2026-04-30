# Context Compactions

v10 treats context compaction as evidence, not cleanup. A compaction is an
artifact-backed summary of a bounded event range that an operator can inspect
and trace back to canonical session evidence.

`ContextCompactionCreated` records the durable event boundary: compaction id,
scope, source event range, artifact id, freshness, related task/turn/checkpoint
ids, source artifacts, limitations, and compact counts for decisions,
unresolved questions, and accepted risks. The `context_compactions` projection
is rebuildable from those events and supports newest-first history queries by
session or task.

The artifact payload uses schema version `1` and artifact kind
`context_compaction_v1`. It includes:

- transcript and task source ranges when those scopes are present
- decisions, unresolved questions, assumptions, verification state, failures,
  accepted risks, touched files, and limitations
- mandatory `source_references` for events, transcript items, task state,
  verification output, checkpoints, tools, or artifacts
- source references on each compacted assertion so summary text can be audited

Compaction does not delete, rewrite, or replace canonical events. When a later
task adds creation commands, refresh, invalidation, and prompt integration, the
artifact and projection described here remain the inspection contract.

## Creating And Inspecting Evidence

`GBX-1031` adds a deterministic local compaction path. It summarizes persisted
session events into the v1 artifact schema, writes a managed
`.context-compaction.json` artifact, and appends `ContextCompactionCreated`.
This path is intentionally provider-free so replay and tests can exercise
compaction provenance without live model drift.

```bash
uv run glassbox session compact SESSION_ID --cwd .
uv run glassbox session compactions SESSION_ID --cwd .
uv run glassbox session status SESSION_ID --cwd .
uv run glassbox replay bundle inspect PATH
```

For release review, verify that a compaction names the source event range,
contains at least one source reference, and stores its payload as a managed
artifact. A compaction without source references is invalid.
