# Runtime Context

Glassbox enriches live turns with bounded typed runtime context. This is explicit runtime state assembled before a model call, not hidden provider-side memory.

Today the operator-visible layers are:

- repository context
- runtime notes
- working set
- artifact-backed context

## Repository Context

Repository context is a deterministic top-level summary of the selected workspace.

It includes bounded signals such as:

- workspace name
- high-signal paths like `README.md`, `src/`, `tests/`, `docs/`, and `evals/`
- bounded top-level directories and files
- coarse project markers

This is an orientation layer, not a full repository index.

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

- `glassbox status SESSION_ID --cwd .`
- the dashboard selected-session summary
- `GET /sessions/{session_id}`
- replay artifacts and exported replay bundles
- eval artifacts and suite summaries when context-sensitive cases drift

Read those summaries with this mental model:

- repository summaries are bounded orientation hints
- runtime notes are session state only when they were explicitly persisted
- working-set items are prioritized summaries, not hidden truth
- artifact-backed summaries are explicit derived state with freshness semantics

## Resume, Replay, Eval, And Branch Behavior

- `resume` recomputes repository context, reloads runtime notes, rebuilds the working set, and reloads artifact-backed summaries when available
- `fork` imports active parent runtime notes as inherited notes and rebuilds replay-safe working-set context for the child session
- `replay` records per-source enriched-context metadata and can report source-level drift
- `replay-export` and `eval` preserve inherited notes, lineage, and artifact-backed dependencies in portable form

## Troubleshooting

- If repository detail looks smaller than expected, remember the summary is bounded to top-level signals.
- If a historical session only shows minimal repository detail, the recorded `cwd` may no longer exist on disk.
- If replay reports `manifest drift`, inspect the richer runtime context first.
- If replay reports `recorded enriched context source drifted: ...`, treat that as a context contract change rather than generic transcript noise.
- If an artifact-backed summary is missing from a later turn, check freshness and whether the underlying artifact is still present.

## Scope Limits

Glassbox still does not do any of the following:

- hidden long-term memory outside the event-sourced runtime
- broad autonomous repository indexing or background crawling
- opaque provider-specific prompt augmentation that cannot be inspected or replayed
- vector-store retrieval treated as a silent second source of truth
- unbounded project summarization detached from explicit runtime events or artifacts

## Related Guides

- [interactive-workflows.md](./interactive-workflows.md)
- [replay-evals.md](./replay-evals.md)
- [architecture.md](./architecture.md)
