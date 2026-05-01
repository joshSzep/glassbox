# Workspace Knowledge Posture

Workspace knowledge posture is the v11 operator model for deciding whether
local context is trustworthy enough to continue work.

The posture is derived from existing local evidence. It does not create a new
knowledge store and it is not authoritative over canonical events.

## Status Categories

- `fresh`: local evidence is present and current enough for ordinary use
- `stale`: evidence exists but should be refreshed or reviewed before relying on
  it
- `missing`: no local evidence has been retained yet
- `invalidated`: the source was explicitly rejected or made non-authoritative
- `degraded`: a projection, verification, or active-session expectation is in a
  failure posture
- `advisory`: evidence is useful but must not become release authority, such as
  provider canary evidence
- `historical-only`: absence is expected for imported or older inspection state

## Sources

| Cue | Authoritative Source | Safe Inspection |
| --- | --- | --- |
| Workspace memory | `WorkspaceMemory*` events and the workspace-memory projection | `glassbox memory list --cwd .` |
| Repository index | rebuildable `.glassbox/repository-index.json` artifact | `glassbox repo index status --cwd .` |
| Checkpoints | `TaskCheckpointCreated` events and `task_checkpoints` projection | `glassbox session status SESSION_ID --cwd .` |
| Context compactions | compaction events, projection rows, and retained artifacts | `glassbox session compactions SESSION_ID --cwd .` |
| Verification | retained `.glassbox/evals/**/summary.json` artifacts | `glassbox eval audit --cwd .` |
| Provider evidence | retained provider-canary summary artifacts | `glassbox provider canary evidence --cwd .` |

The aggregate posture ranks `degraded` ahead of `stale`, `invalidated`,
`missing`, `advisory`, and `historical-only`. This makes active recovery gaps
more visible than normal absence or optional provider confidence.

## Implementation Boundary

`glassbox.runtime.knowledge_posture` remains the stable facade for API,
dashboard, CLI, observability, and handoff callers. Source reads live in
`knowledge_posture_sources.py`; cue shaping lives in
`knowledge_posture_cues.py`; bounded provenance, safe inspection commands,
aggregate ranking, and public posture models live in focused
`knowledge_posture_*` helpers. These helpers still derive from existing events,
projections, and retained artifacts only.

## Operator Use

Use knowledge posture as an inspection summary before continuation, handoff, or
release review. If a cue is stale or degraded, inspect the source command first,
then refresh derived evidence deliberately. Provider posture remains advisory;
deterministic replay, eval, package, and release-gate evidence remain release
authority.

## Surfaces

`glassbox observability status --cwd .` prints the overall knowledge posture and
the highest-signal cues next to runtime, projection, artifact, verification, and
provider health. `--json` includes a `knowledge_posture` object with the same
cue list, safe inspection commands, and bounded provenance references.

The dashboard workspace overview rail shows the aggregate posture as a compact
cue. Live blockers, approvals, questions, failed sessions, and degraded
projections still keep priority; knowledge posture is a trust signal operators
can inspect before relying on local context for continuation.

## Provenance Drill-Down

Each cue can include a `provenance` list. These references name local evidence
without duplicating raw artifact contents:

- memory cues include memory IDs, source session IDs, source sequences, and
  artifact IDs when the memory was artifact-backed
- repository-index cues include the retained index path, freshness, and build
  timestamp when available
- checkpoint and compaction cues include session IDs, task IDs, artifact IDs,
  source event ranges, last projected sequence, and freshness
- verification cues include the retained eval summary path and profile ID
- provider evidence cues include retained summary path, freshness policy state,
  provider, model, and generation timestamp

For a stale repository cue, inspect the path and freshness first:

```bash
uv run glassbox observability status --cwd . --json
uv run glassbox repo index status --cwd . --json
```

For stale compaction or missing checkpoint provenance, use the referenced
session ID and source event range to inspect the session before mutating state:

```bash
uv run glassbox session status SESSION_ID --cwd .
uv run glassbox session compactions SESSION_ID --cwd .
```
