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

## Operator Use

Use knowledge posture as an inspection summary before continuation, handoff, or
release review. If a cue is stale or degraded, inspect the source command first,
then refresh derived evidence deliberately. Provider posture remains advisory;
deterministic replay, eval, package, and release-gate evidence remain release
authority.
