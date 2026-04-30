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

Compaction does not delete, rewrite, or replace canonical events. Refresh and
invalidation append `ContextCompactionFreshnessChanged` instead of mutating or
removing the original artifact. The projection keeps the current freshness,
freshness reason, and superseding compaction id when a newer artifact replaces
an older one.

## Creating And Inspecting Evidence

`GBX-1031` adds a deterministic local compaction path. It summarizes persisted
session events into the v1 artifact schema, writes a managed
`.context-compaction.json` artifact, and appends `ContextCompactionCreated`.
This path is intentionally provider-free so replay and tests can exercise
compaction provenance without live model drift.

```bash
uv run glassbox session compact SESSION_ID --cwd .
uv run glassbox session compactions SESSION_ID --cwd .
uv run glassbox session compaction-refresh SESSION_ID COMPACTION_ID --yes --cwd .
uv run glassbox session compaction-invalidate SESSION_ID COMPACTION_ID \
  --reason "summary missed the latest checkpoint" --yes --cwd .
uv run glassbox session status SESSION_ID --cwd .
uv run glassbox replay bundle inspect PATH
```

For release review, verify that a compaction names the source event range,
contains at least one source reference, and stores its payload as a managed
artifact. A compaction without source references is invalid.

Refresh is the repair path for superseded summaries. It creates a replacement
artifact over the current material source range and marks the previous
compaction stale with a pointer to the replacement. Invalidation is the repair
path for summaries that should remain audit evidence but must not feed prompt
context. Both mutating CLI actions require `--yes`; the HTTP API mirrors that
with `confirmed=true`.

## Prompt Context

`GBX-1032` feeds only fresh compaction summaries into turn context. Prompt text
labels the compaction scope, source event range, artifact id, freshness, and
limitations. Stale compactions remain inspectable through events and the
projection, but they are counted as excluded instead of silently entering active
model context. Recent transcript, checkpoint, workspace memory, repository
context, and artifact-backed failure summaries remain separate context sources.

`GBX-1033` adds conservative freshness rules during runtime-context assembly.
An otherwise fresh compaction is treated as stale when material session events,
new checkpoints, verification evidence, or tool/artifact evidence appear after
its source event range. The dashboard runtime pane lists stale compaction cues
with the reason and source range so an operator can refresh or invalidate before
starting a future turn.
