# Runtime Context

Glassbox enriches live turns with bounded typed runtime context. This is explicit runtime state assembled before a model call, not hidden provider-side memory.

Today the operator-visible layers are:

- repository context
- repository index context
- repository intelligence context
- runtime notes
- confirmed workspace memory context
- working set
- artifact-backed context
- checkpoint resume context
- context compaction context

## Repository Context

Repository context is a deterministic top-level summary of the selected workspace.

It includes bounded signals such as:

- workspace name
- high-signal paths like `README.md`, `src/`, `tests/`, `docs/`, and `evals/`
- bounded top-level directories and files
- coarse project markers

This is an orientation layer, not a full repository index.

## Repository Index Context

Repository index context is a bounded selection from the local repository index
snapshot when that snapshot is fresh. It may include high-signal index entries
such as commands, docs, tests, modules, and symbols with source type and
freshness posture.

The index prompt slice is still narrower than repository intelligence v2: it is
an orientation/search slice, not a full explanation of affected subsystems,
command recipes, likely verification, stale exclusions, or confirmed
conventions.

## Repository Intelligence Context

Repository intelligence context is the v15 contract for giving model turns a
bounded repository-aware summary without hidden retrieval or provider-side
memory. It is separate from repository context, repository index context,
runtime notes, working set, artifact-backed context, and workspace memory
prompt fragments.

The snapshot shape is explicit and replay-visible:

- `status`, `schema_version`, optional source digest, context byte count, and
  budget byte count
- included source summaries with source name, source kind, freshness,
  confidence, provenance, source digest, item count, and limitations
- selected items such as affected subsystems, likely tests, command recipes,
  confirmed conventions, release surfaces, stale-risk notes, and limitations
- excluded sources such as stale memory, stale topology, failed index builds, or
  conflicting metadata that must not silently shape prompts
- additional-item counts, safe next actions, and snapshot-wide limitations

Only bounded summaries may enter this section. Raw repository index artifacts,
raw file contents, raw diffs, raw command logs, and unreviewed memory
candidates are excluded. Stale, missing, degraded, conflicting, or partial
sources are either omitted from active items or carried as clearly labeled
excluded sources with lower confidence and safe inspection or rebuild actions.

Confirmed workspace memory may appear through repository intelligence only when
the underlying memory is active, confirmed, provenance-backed, not stale or
conflicting, and prompt use is recorded through the workspace memory context
use event path. Candidate, rejected, invalidated, imported-unreviewed, pruned,
or redaction-blocked memory remains outside active prompt context by default.

Replay fingerprints repository intelligence as its own enriched-context source.
The fingerprint includes status, schema version, source digest, included and
excluded source summaries, selected items, truncation counts, limitations, and
safe next actions. Replay drift should name `repository_intelligence` rather
than hiding these changes as generic transcript or repository-context drift.

## Runtime Notes

Runtime notes are persisted session-scoped notes with category, message, and inheritance provenance.

They are event-backed and inspectable. They survive resume, replay, export, eval, and branch flows.

## Working Set

The working set is a bounded summary of the current local focus derived from explicit runtime signals such as:

- recent tests
- approvals
- tool activity
- artifacts
- branch lineage

It is a local-focus aid, not a second hidden memory system.

## Artifact-Backed Context

Artifact-backed context carries explicit derived summaries when recomputing them every turn would be too expensive or too unstable.

The current shipped example is a bounded pytest failure digest.

Artifact-backed summaries are included in prompt assembly only while they remain fresh. They remain inspectable even after they stop being current.

## How To Inspect It

You can inspect runtime context through:

- `glassbox session status SESSION_ID --cwd .`
- the dashboard selected-session summary
- `GET /sessions/{session_id}`
- replay artifacts and exported replay bundles
- eval artifacts and suite summaries when context-sensitive cases drift

Read those summaries with this mental model:

- repository summaries are bounded orientation hints
- repository intelligence summaries are bounded advisory hints with freshness,
  confidence, provenance, limitations, exclusions, and replay fingerprints
- runtime notes are session state only when they were explicitly persisted
- workspace memory is review-gated local memory only when confirmed active and
  context-use recording applies
- working-set items are prioritized summaries, not hidden truth
- artifact-backed summaries are explicit derived state with freshness semantics

`glassbox session status` also prints a runtime-context budget line. Treat
`(+N more)` counts as a confidence signal: the context is still deterministic,
but the visible prompt/operator slice is truncated and release review should
prefer context-sensitive replay/eval coverage before accepting drift.

## Resume, Replay, Eval, And Branch Behavior

- `resume` recomputes repository context, reloads runtime notes, rebuilds the working set, reloads artifact-backed summaries when available, carries bounded repository intelligence only when a later integration task provides an eligible snapshot, and classifies the latest checkpoint as checkpoint-derived or replay-derived context with source-event provenance
- checkpoint-derived context is used only when the latest checkpoint covers the current session tail and has no known blockers; stale, blocked, failed, or workspace-drifted checkpoints remain visible but are marked unsafe to trust
- `fork` imports active parent runtime notes as inherited notes and rebuilds replay-safe working-set context for the child session
- `replay` records per-source enriched-context metadata and can report source-level drift
- `replay bundle export` and `eval` preserve inherited notes, lineage, and artifact-backed dependencies in portable form

## Troubleshooting

- If repository detail looks smaller than expected, remember the summary is bounded to top-level signals.
- If a historical session only shows minimal repository detail, the recorded `cwd` may no longer exist on disk.
- If replay reports `manifest drift`, inspect the richer runtime context first.
- If replay reports `recorded enriched context source drifted: ...`, treat that as a context contract change rather than generic transcript noise.
- If replay reports `recorded enriched context source drifted: repository_intelligence`, inspect repository intelligence context sources, excluded stale sources, path-to-verification recommendations, and snapshot freshness before comparing model behavior.
- If the runtime-context budget line shows truncation, inspect whether the hidden count is expected for this workspace or whether context-sensitive tests should be promoted before release sign-off.
- If an artifact-backed summary is missing from a later turn, check freshness and whether the underlying artifact is still present.

## Scope Limits

Glassbox still does not do any of the following:

- hidden long-term memory outside the event-sourced runtime
- broad autonomous repository indexing or background crawling
- opaque provider-specific prompt augmentation that cannot be inspected or replayed
- vector-store retrieval treated as a silent second source of truth
- unbounded project summarization detached from explicit runtime events or artifacts
- repository intelligence prompt fragments that contain raw index artifacts,
  raw file contents, raw command logs, or unconfirmed memory candidates

## Related Guides

- [interactive-workflows.md](./interactive-workflows.md)
- [replay-evals.md](./replay-evals.md)
- [architecture.md](./architecture.md)
