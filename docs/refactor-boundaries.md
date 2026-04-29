# Glassbox Refactor Boundaries

For the docs hub and operator guides, start at [README.md](./README.md). This note defines the target architectural boundaries for the v1 refactor roadmap in [refactor-v1.md](./refactor-v1.md) and the post-v8 follow-on roadmap in [refactor-v8.md](./refactor-v8.md).

## Purpose

This document is the architecture source of truth for the refactor roadmap.

It exists to answer one question before code moves begin:

What are the intended module boundaries for the current Glassbox implementation, and what kinds of changes are explicitly out of scope for the first refactor pass?

This note is intentionally code-aligned. It describes the current implementation shape and the target decomposition boundaries for refactor work already captured in [refactor-v1.md](./refactor-v1.md) and [refactor-v8.md](./refactor-v8.md). It does not define a new product architecture.

## Scope

This refactor pass is about implementation structure, not product behavior.

The goals are:

- reduce oversized source files with mixed responsibilities
- remove architectural duplication where the same control flow or state shaping exists in multiple places
- make dependency direction between subsystems explicit
- preserve current operator-visible behavior unless a later task says otherwise

The non-goals are:

- redesign the event model
- replace the current single-process runtime model
- introduce a new UI framework for the dashboard
- rewrite the store, runtime, or CLI from scratch
- change replay result taxonomy, snapshot payloads, or command semantics as part of refactor-only work
- add new autonomy behaviors, background job kinds, provider checks, repository
  indexing semantics, workspace-memory capture rules, TUI workflows, or
  dashboard workflows while performing post-v8 refactor-only tasks

## Behavior-Preservation Contract

Unless a later task explicitly changes a contract, refactor work should preserve:

- current CLI command semantics and exit-code behavior
- current session snapshot and session-index HTTP payload shapes
- current event ordering for turn execution and turn resumption flows
- current replay result taxonomy and mismatch classification semantics
- current dashboard reducer state shape and observable interaction semantics
- current repository and service contracts used by runtime bootstrap, tests, and route handlers

That does not prevent internal renaming, extraction, or compatibility shims. It does mean internal movement is not a license to make incidental behavior changes.

## Current Pressure Points

The existing architecture is coherent, but several files are carrying too many responsibilities at once.

The main pressure points are:

- `src/glassbox/runtime/turn_engine.py`: turn lifecycle, model loop, tool execution, suspension and resumption, artifact hooks, and event emission
- `src/glassbox/runtime/replay.py`: replay bundle models, bundle I/O, replay execution, normalization, mismatch collection, and triage
- `src/glassbox/store/sqlite.py`: schema bootstrap, event-store operations, projection application, lineage helpers, and rebuild logic
- `src/glassbox/cli/__init__.py`: parser construction, command dispatch, command execution, interactive session control, and report formatting
- `src/glassbox/runtime/context_builder.py`: snapshot building, working-set heuristics, and prompt formatting
- `src/glassbox/web/routes/sessions.py`: HTTP transport, session query composition, snapshot shaping, and next-action summary logic
- `src/glassbox/web/static/state.js`, `render.js`, and `dashboard.js`: reducer logic, rendering, transport, and DOM orchestration pressed into a few large files

Some files are large because they hold many data models or helper variants. That alone is not enough reason to split them. The refactor should focus first on files that mix distinct responsibilities or duplicate logic already living elsewhere.

The post-v8 pressure points are concentrated in newer autonomy-era surfaces:

- `src/glassbox/runtime/background_jobs.py` mixes worker-loop coordination,
  stale-claim recovery, read-only maintenance jobs, mutating task
  continuations, and progress/failure event recording
- `src/glassbox/runtime/workspace_memory_capture.py` mixes capture service
  commits, candidate extraction, model-assisted suggestion parsing, filtering,
  dedupe, staleness checks, and redaction
- `src/glassbox/runtime/observability.py` mixes workspace report aggregation
  with domain-specific collectors for runtime transport, projections,
  artifacts, verification, background jobs, task autonomy, memory, repository
  index, branch search, and provider posture
- `src/glassbox/runtime/repository_index.py` mixes public index read/write
  helpers, filesystem scanning, entity extraction, dependency/script parsing,
  and search helpers
- `src/glassbox/store/sqlite_queries.py` is a broad read-model adapter over
  projections for transcript, runtime notes, approvals, metrics, budgets,
  tasks, branch search, and workspace memory adjacency
- `src/glassbox/store/repositories.py` is a large adapter surface; most of its
  size is legitimate contract coverage, but it should not keep accumulating
  domain-specific query shaping inline
- `src/glassbox/cli/tui/conversation.py` mixes model types, event reduction,
  selectors, and text transformation helpers for terminal state
- `src/glassbox/cli/tui/widgets.py` mixes Textual widget classes, pure render
  functions, transcript block formatting, composer behavior, command palette
  behavior, and details rendering
- `frontend/stores/dashboard-stores.ts` mixes dashboard, session, task,
  knowledge, branch-search, stream, pagination, and action-state stores behind
  one compatibility module
- `frontend/components/console/task-autonomy-console.tsx`,
  `knowledge-autonomy-console.tsx`, and `branch-search-console.tsx` are mixed
  responsibility components that combine data presentation, local view state,
  filtering, evidence summaries, action controls, and formatting helpers

Large files that are primarily model-heavy and should not be split just for
line count include core event/model/type modules, generated frontend API types,
and facade modules whose public contract is intentionally broad but already
delegates behavior to owned implementation modules. Large files that are mixed
coordinators should be split along ownership boundaries when their roadmap task
arrives, not by mechanical line slicing.

## Target Boundary Map

### Runtime

The `runtime` package should own orchestration and runtime-specific query composition.

Its stable responsibilities are:

- session lifecycle coordination
- turn coordination
- context assembly
- replay execution and eval orchestration
- runtime-scoped query and snapshot shaping
- runtime bootstrap and dependency wiring

The `runtime` package should not become a catch-all for transport formatting, raw storage internals, or browser-specific response shaping.

#### Target Runtime Sub-Boundaries

- `supervisor` owns session lifecycle and delegates turn execution
- `turn_engine` owns turn-level coordination, but not every detail of model looping or resumption mechanics
- shared model-loop logic should be reusable by live turn execution and replay
- the shared model-loop boundary currently lives in `src/glassbox/runtime/model_loop.py` and is consumed by `turn_engine.py` plus replay runtime wiring
- turn preparation, suspended-turn reconstruction, turn event recording, and tool execution side effects now live in `src/glassbox/runtime/turn_preparation.py`, `turn_resumption.py`, `turn_event_recorder.py`, and `turn_tool_executor.py`, leaving `turn_engine.py` focused on session-facing turn coordination and failure handling
- context-building logic should separate structured snapshot derivation, working-set derivation, and prompt rendering
- the shared context assembly boundary now uses `src/glassbox/runtime/context_snapshots.py`, `context_working_set.py`, and `context_formatting.py`, with `context_builder.py` reduced to typed models plus `TurnContextBuilder` assembly
- runtime query code should provide session summaries and snapshots to both CLI and web consumers without embedding HTTP concerns
- the shared session-query boundary now lives in `src/glassbox/runtime/session_queries.py` and is consumed by CLI status reporting plus web session routes
- bootstrap should wire public collaborators together, not hide ownership behind broad transitive re-exports
- the bootstrap split now keeps `src/glassbox/runtime/bootstrap.py` as the public entry facade while moving storage-path and SQLite initialization to `bootstrap_storage.py`, provider wiring to `bootstrap_provider.py`, and `RuntimeContext` assembly to `bootstrap_assembly.py`
- `runtime/__init__.py` should stay a small public surface for bootstrap, event-bus, and runtime-context types; replay, supervisor, turn-engine, and context-builder imports should come from explicit submodules

#### Post-v8 Runtime Autonomy Sub-Boundaries

- `background_jobs` should own the public worker-loop entry points and worker
  tick summary, then delegate lease/recovery behavior, read-only maintenance
  handlers, mutating task-continuation handlers, and progress/failure event
  recording to focused runtime modules
- the background-job worker split now keeps
  `src/glassbox/runtime/background_jobs.py` as the stable public runner facade,
  with lease/cancellation/recovery helpers in `background_job_lifecycle.py`,
  read-only maintenance handlers in `background_job_handlers.py`, mutating task
  continuation in `background_task_continuation.py`, and progress/failure event
  recording in `background_job_records.py`
- background-job maintenance handlers should remain read-only except for
  explicit job progress/completion/failure events; task continuation handlers
  are the only post-v8 background path expected to mutate task/session state
- `workspace_memory_capture` should keep the public capture service and
  repository protocol stable while candidate extraction, model-assisted
  suggestions, redaction, filtering/dedupe/staleness, and commit construction
  move into pure helper modules
- the workspace-memory split now keeps
  `src/glassbox/runtime/workspace_memory_capture.py` as the public service
  facade, with candidate models/filtering in `workspace_memory_candidates.py`,
  extraction in `workspace_memory_extraction.py`, sensitive text redaction in
  `workspace_memory_redaction.py`, and review-gated commit event construction
  in `workspace_memory_commits.py`
- workspace-memory extraction remains review-gated: helpers propose candidates
  and the service records explicit confirmation, merge, rejection, or operator
  memory events
- `observability` should keep `build_workspace_observability_report` as the
  aggregation facade while domain collectors own runtime transport,
  projection, artifact, verification, background job, task autonomy, workspace
  memory, repository index, branch search, and provider-canary posture reads
- the observability split now keeps
  `src/glassbox/runtime/observability.py` as the aggregation and compatibility
  facade, with shared report models in `observability_models.py` and read-only
  domain collectors in focused `observability_*` modules for runtime/event
  transport, projections, artifacts, verification, background jobs, task
  autonomy, workspace memory, repository index, and branch search
- observability collectors must stay read-only and should not depend on CLI
  formatting, HTTP response models, frontend state, or background job repair
  actions
- `repository_index` should keep stable public helpers for building, writing,
  loading, searching, and fetching index entries while filesystem scanning,
  entity extraction, dependency/script extraction, index serialization, and
  search ranking move behind owned helpers
- the repository-index split now keeps
  `src/glassbox/runtime/repository_index.py` as the stable public facade, with
  deterministic discovery and source digests in `repository_index_discovery.py`,
  entry extraction in `repository_index_extraction.py`, persistence/freshness
  checks in `repository_index_persistence.py`, and search/entry lookup in
  `repository_index_search.py`
- repository intelligence remains local-file derived. It should not introduce
  network fetches, generated caches that are not rebuildable, or runtime
  orchestration dependencies as part of refactor-only work
- provider diagnostics and provider canary evidence are runtime read models and
  runtime checks. Diagnostics should stay configuration/readiness oriented;
  canary execution may use runtime bootstrap, but stored evidence loading and
  report aggregation should remain separable from observability formatting

### Store

The `store` package should own canonical persistence and projection application.

Its stable responsibilities are:

- schema and migration/bootstrap concerns
- append-only event-log reads and writes
- projection application and rebuild
- repository adapters over the raw storage helpers
- artifact storage and retrieval
- lineage and fork-point resolution rooted in persisted state

The `store` package should not own runtime orchestration, CLI formatting, or web response shaping.

#### Target Store Sub-Boundaries

- schema/bootstrap code should live separately from query and append logic
- raw event-store operations should be distinct from projection application helpers
- projection application should remain deterministic and rebuildable from `events`
- repository adapters should stay stable while internal storage helpers split underneath them
- the SQLite store now uses internal `sqlite_schema.py`, `sqlite_sessions.py`, `sqlite_events.py`, `sqlite_projections.py`, `sqlite_queries.py`, and `sqlite_fork.py` modules behind the stable `store/sqlite.py` facade
- `store/__init__.py` should stay limited to repository adapters, bootstrap helpers, and shared artifact models; raw SQLite and artifact helper imports should come from `store.sqlite` or `store.artifacts`

#### Post-v8 Store Query Sub-Boundaries

- `sqlite_queries.py` should split by projection domain when it changes:
  transcript/runtime notes, approvals/tools/turn metrics, autonomy budgets,
  task projections, branch-search projections, and any workspace-memory
  adjacency queries should be owned by focused store read modules
- the projection read split now keeps `sqlite_queries.py` as a compatibility
  facade over focused `sqlite_query_*` modules for transcript, runtime notes,
  tools/approvals, turn metrics, autonomy budgets, tasks, and branch search
- query helpers should continue to derive from canonical events and
  deterministic projection tables. They should not call runtime services,
  background workers, provider diagnostics, HTTP serializers, or frontend
  state helpers
- `repositories.py` should remain the stable adapter surface for service
  protocols, but method bodies should be thin pass-throughs to store-owned
  modules once query domains split
- the repository adapter split now keeps `repositories.py` as the stable public
  facade for `SQLiteSessionRepository` and `FilesystemArtifactRepository`, with
  session, event/fork, projection-read, background-job, workspace-memory, task,
  branch-search, and artifact behavior owned by focused `repository_*` modules
- repository adapters may import store implementation modules and core/service
  contracts. They should not import runtime orchestration modules, web routes,
  CLI modules, or frontend code

### Services

The `services` package should remain the narrow contract layer between orchestration code and concrete persistence or runtime implementations.

Its stable responsibilities are:

- repository protocols
- service protocols
- shared contract surfaces consumed by CLI, runtime, and web wiring

The `services` package should not accumulate concrete behavior merely to avoid imports.

### CLI

The `cli` package should own terminal-facing command parsing, command orchestration, and human-readable presentation.

Its stable responsibilities are:

- argument parsing and top-level command dispatch
- command orchestration over runtime services and query services
- interactive terminal session control
- event-driven terminal rendering
- CLI-specific human-readable and JSON report formatting

The `cli` package should not build its own parallel session-query logic when the runtime can provide the same read model once.

#### Target CLI Sub-Boundaries

- parser construction should be separate from command execution
- one-shot command execution should be separate from long-lived interactive session control
- reporting and formatting should be separate from command flow control
- command handlers should depend on service and query contracts, not on raw SQLite helpers
- the CLI entry split now keeps parser registration and argument helpers in `src/glassbox/cli/parser.py`, top-level dispatch and error handling in `cli/entry.py`, shared runtime/rendering helpers in `cli/runtime_runner.py`, and preserves `glassbox.cli:main` as a thin compatibility wrapper
- workflow-family command handlers now live in `cli/interactive_commands.py`, `session_state_commands.py`, `replay_eval_commands.py`, and `server_commands.py`, with shared path resolution in `cli/path_helpers.py` and direct imports from their owning CLI modules
- long-lived terminal prompt routing, blocked-state messaging, prompt redraw context, and attach-session gating now live in `cli/interactive_session.py`, which owns the interactive input seams directly
- status/runtime-context rendering now lives in `cli/status_formatters.py`, replay/eval report rendering and replay JSON/exit-code helpers live in `cli/replay_eval_formatters.py`, and CLI internals no longer route through `cli/__init__.py` for those helpers

#### Post-v8 TUI Sub-Boundaries

- the TUI conversation split now keeps `cli/tui/conversation.py` as a
  compatibility facade, with state models in `conversation_models.py`, snapshot
  hydration in `conversation_hydration.py`, canonical event reduction in
  `conversation_reducer.py`, and display/action derivation in
  `conversation_selectors.py`
- TUI reducers may depend on core event/model types and CLI-local snapshot
  models, but should not import raw store helpers, runtime workers, HTTP
  routes, or frontend modules
- the TUI widget split now keeps `cli/tui/widgets.py` as a compatibility
  facade over pane-family modules for header/footer, transcript, action strip,
  composer, command palette, and details rendering
- widget classes may depend on terminal state/selectors and Textual/Rich, but
  pure render helpers should remain easy to unit test without starting the TUI
  application
- the TUI app split keeps `cli/tui/app.py` as the Textual lifecycle owner while
  command dispatch, stream lifecycle, widget refresh, feedback mapping, and
  local artifact path resolution live in focused `app_*` helpers

### Web

The `web` package should own HTTP transport and browser assets.

Its stable responsibilities are:

- FastAPI app and route registration
- HTTP request validation and response serialization
- SSE transport
- browser assets, frontend state handling, and DOM orchestration

The `web` package should not own the canonical logic for deriving session summaries, next-action guidance, or runtime-context shapes.

#### Target Web Backend Sub-Boundaries

- routes should focus on HTTP concerns
- shared runtime query code should provide session snapshot composition
- transport-specific response models may wrap query-domain models, but should not redefine the business logic that produces them
- the session route transport split now keeps HTTP request/response models and view serializers in `src/glassbox/web/session_api.py`, leaving `web/routes/sessions.py` focused on parameter validation, service calls, and HTTP error mapping

#### Historical Web Frontend Sub-Boundaries

These sub-boundaries describe the removed no-framework dashboard split. They are
kept only as historical refactor context; current dashboard architecture follows
the Next.js SPA contract in [architecture.md](./architecture.md) and
[tasks-v3.md](./tasks-v3.md).

- reducer and snapshot-normalization logic should stay pure
- pane rendering should stay pure and be grouped by UI responsibility
- fetch/SSE transport and DOM-binding logic should live outside pure reducers and renderers
- the detailed historical browser-module map lives in [dashboard-frontend-boundaries.md](./dashboard-frontend-boundaries.md)
- the former reducer, renderer, transport, and DOM orchestration files were removed in GBX-472 after SPA parity and route flip tasks completed

#### Current Next.js Dashboard Sub-Boundaries

- `frontend/stores/dashboard-stores.ts` is now a compatibility facade that
  re-exports console, session, task, knowledge, and branch-search store
  factories and public state types from their domain modules. Existing call
  sites can keep the stable import path until they intentionally move to domain
  modules
- dashboard store domains are split into session summary/detail streaming,
  task queue/detail/action state, workspace memory/repository inspector state,
  branch-search list/detail/action state, and shared request/action/load-state
  helpers in `frontend/stores/store-actions.ts`
- dashboard stores should depend on generated API client types, route-state
  helpers, stream transport helpers, and pure frontend store utilities. They
  should not import React components or server-only modules
- autonomy console components should split large task, knowledge, and branch
  search views into focused list, detail, evidence, action-control, and
  formatting modules while preserving current routes, API calls, and workflow
  behavior
- frontend components should consume store state and generated API types, not
  duplicate backend event derivation rules that already exist in runtime/store
  read models

### Replay And Eval

Replay and eval logic lives in `runtime`, but it should maintain its own internal boundaries.

Its stable responsibilities are:

- replay bundle loading and export
- deterministic runtime playback
- normalized-state comparison and mismatch collection
- replay triage and eval summary/report generation

Its internal ownership should stay explicit:

- replay manifest models, builders, and artifact loading should live separately from replay execution flow
- enriched-context fingerprinting and normalization helpers should be reusable by live capture and replay comparison without being hidden inside the recorder
- the live replay recorder should stay focused on capture-time orchestration, artifact writes, and event linkage rather than owning manifest semantics
- the replay capture split now uses `src/glassbox/runtime/replay_manifests.py`, `replay_fingerprints.py`, and a smaller `replay_capture.py` recorder module
- the replay runner split now keeps `src/glassbox/runtime/replay.py` as the stable facade while moving bundle loading and export to `replay_bundle_io.py`, execution coordination and failure mapping to `replay_orchestrator.py`, isolated deterministic execution to `replay_execution.py`, normalized-state comparison to `replay_compare.py`, and outcome classification to `replay_triage.py`
- eval-suite input discovery and output-directory selection now live in `src/glassbox/runtime/eval_inputs.py` so suite execution, summary loading, and CLI report flows share one typed input boundary
- the eval reporting split now keeps `src/glassbox/runtime/eval_summary.py` as the stable facade while moving suite payload and job-summary construction to `eval_summary_suite.py`, release-signoff aggregation to `eval_summary_release.py`, annotation helpers to `eval_summary_annotations.py`, and shared report models to `eval_summary_models.py`

The replay and eval stack should not maintain a bespoke copy of live model-loop behavior when a shared execution boundary can serve both paths.

## Dependency Direction Rules

The intended dependency direction for this refactor pass is:

- `core` defines shared domain types and event models
- `services` defines contracts over repository and service boundaries
- `store` implements persistence and repository adapters using `core` and `services`
- `runtime` orchestrates behavior using `core`, `services`, and repository/service implementations
- `cli` depends on `runtime`, `services`, and CLI-local presentation modules
- `web` depends on `runtime`, `services`, and web-local transport or browser modules

The practical rules are:

- `cli` must not depend directly on raw `store/sqlite.py` helpers
- `web` route modules must not become the canonical place for session-query logic
- `store` must not depend on `runtime`, `cli`, or `web`
- `services` must remain concrete-implementation free
- `runtime` may depend on `store` implementations in bootstrap code, but orchestration logic should prefer service or repository contracts where practical
- package-root imports should not be used as a convenience layer when they hide ownership of replay, turn execution, context building, or raw persistence helpers
- post-v8 runtime collector, repository-index, and memory-extraction helpers
  must not import web routes, CLI/TUI widgets, frontend code, or raw SQLite
  helpers directly
- post-v8 store read modules must stay below runtime and transport layers:
  they may shape projection records, but runtime query services and web routes
  own operator-facing summaries and response models
- TUI state and render modules must not import raw store modules or runtime
  background-job orchestration. They should consume events, snapshots, and
  CLI-local state only
- frontend stores must not import React components, Next.js server modules, or
  backend source files. Components should not become store-factory modules

## Boundary Guardrails

The refactor roadmap now has lightweight enforcement for the most important boundaries above.

The guardrails are intentionally narrow:

- `tests/unit/test_architecture_guardrails.py` enforces dependency direction for `store`, `services`, CLI command modules, and web route modules
- the store and services packages are guarded against importing outward into `runtime`, `cli`, or `web`
- CLI command modules and web route modules are guarded against reaching into raw SQLite helpers instead of using repository, service, or query seams
- thin public facades are kept reviewable with soft size caps and explicit delegate-module checks for `runtime/__init__.py`, `store/sqlite.py`, `runtime/eval_summary.py`, `runtime/replay.py`, and the browser entry facades in `web/static/`
- those guardrails intentionally protect the public runtime entry surfaces around bootstrap, replay, and eval without turning internal coordinator modules such as `turn_engine.py` or `replay_orchestrator.py` into brittle size-capped policy targets
- post-v8 guardrails extend the same idea to autonomy-era areas: the current
  background-job, workspace-memory, observability, repository-index, and
  provider-evidence modules are checked against transport/UI/raw-store imports,
  TUI modules are checked against raw store and runtime worker imports,
  frontend stores are checked against component/server/backend imports, and
  `frontend/stores/dashboard-stores.ts` is kept reviewable as the
  compatibility facade over the source-owned domain store modules

If a guardrail fails, the default repair should be to move new behavior into the owning split module or add one focused neighbor module, not to widen a facade or cross a subsystem boundary.

## Acceptable Temporary Compatibility Shims

The following temporary compatibility patterns are acceptable during this refactor pass:

- `__init__.py` re-exports that preserve stable import paths while internals move behind them
- thin forwarding wrappers that preserve repository adapter behavior while internal store modules split
- thin adapter layers that keep existing route or CLI call sites working while shared query services are introduced
- module-local helper imports retained temporarily while large files are being extracted incrementally
- `frontend/stores/dashboard-stores.ts` re-exporting domain store factories
  while call sites move gradually
- TUI modules re-exporting terminal state, selectors, or render helpers while
  widget imports are updated in narrow follow-on tasks
- runtime autonomy facade modules preserving public worker, memory-capture,
  observability, repository-index, and provider evidence entry points while
  implementation details move into owned neighbors

These shims are acceptable only if they are clearly transitional and do not reintroduce the same architectural ambiguity the refactor is trying to remove.

## Shims That Must Not Become Permanent

The following patterns are not acceptable as stable endpoints:

- a new grab-bag helper module that simply becomes the next monolith
- broad runtime package re-exports that hide ownership of replay, context, query, and bootstrap code behind one import surface
- route modules that keep business logic inline after a shared query service exists
- CLI command handlers that continue to duplicate session-summary or next-action shaping once shared query paths land
- replay code that keeps a second copy of live model-loop behavior after the shared execution boundary exists
- background-job maintenance modules that mutate task/session state outside the
  explicit continuation path
- workspace-memory extraction helpers that create durable memory without the
  existing review/confirmation event path
- observability collectors that start repairing state, enqueueing jobs, or
  owning CLI/HTTP/frontend presentation
- repository-index helpers that depend on runtime session orchestration or
  non-local external data sources for refactor-only work
- frontend store modules that import React components or backend Python source

## Task Mapping

This boundary note is the source of truth for the early refactor tasks in [refactor-v1.md](./refactor-v1.md) and the post-v8 boundary-refresh tasks in [refactor-v8.md](./refactor-v8.md).

The intended mapping is:

- `GBX-R101`: shared model-loop boundary for live turns and replay
- `GBX-R102`: shared session snapshot and query service in `src/glassbox/runtime/session_queries.py`
- `GBX-R103`: store-internal split under stable repository adapters via the `sqlite_*.py` internal modules behind `store/sqlite.py`
- `GBX-R104`: export-surface tightening and dependency-direction cleanup
- `GBX-R200`: post-v8 boundary map for autonomy-era runtime, store, TUI, and
  dashboard surfaces
- `GBX-R201`: guardrails for post-v8 dependency direction, facade thinness,
  and frontend store/component boundaries

Later tasks should follow this boundary map rather than redefining subsystem ownership case by case.

## How To Use This Note

Before starting a refactor task:

- confirm the target boundary exists in this note
- decide whether the task is boundary repair or a downstream file split
- preserve behavior first, then remove temporary shims once the new boundary is exercised and covered

If a later task reveals that one of these boundaries is wrong, update this note and the relevant roadmap task together rather than letting code and docs drift.
