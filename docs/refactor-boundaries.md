# Glassbox Refactor Boundaries

For the docs hub and operator guides, start at [README.md](./README.md). This note defines the target architectural boundaries for the v1 refactor roadmap in [refactor-v1.md](./refactor-v1.md).

## Purpose

This document is the architecture source of truth for the refactor roadmap.

It exists to answer one question before code moves begin:

What are the intended module boundaries for the current Glassbox implementation, and what kinds of changes are explicitly out of scope for the first refactor pass?

This note is intentionally code-aligned. It describes the current implementation shape and the target decomposition boundaries for refactor work already captured in [refactor-v1.md](./refactor-v1.md). It does not define a new product architecture.

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
- the SQLite store now uses internal `_sqlite_schema.py`, `_sqlite_sessions.py`, `_sqlite_events.py`, `_sqlite_projections.py`, `_sqlite_queries.py`, and `_sqlite_fork.py` modules behind the stable `store/sqlite.py` facade
- `store/__init__.py` should stay limited to repository adapters, bootstrap helpers, and shared artifact models; raw SQLite and artifact helper imports should come from `store.sqlite` or `store.artifacts`

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

#### Target Web Frontend Sub-Boundaries

- reducer and snapshot-normalization logic should stay pure
- pane rendering should stay pure and be grouped by UI responsibility
- fetch/SSE transport and DOM-binding logic should live outside pure reducers and renderers
- the detailed target browser-module map now lives in [dashboard-frontend-boundaries.md](./dashboard-frontend-boundaries.md)
- `state.js` should split behind a stable facade into snapshot hydration, session/stream state, browser submission state, and incremental event-reduction helpers
- `render.js` should split behind a stable facade into session discovery, selected-session summary/lineage, transcript/live activity, operator actions, and operational diagnostics pane families
- `approval-actions.js` and `interaction-actions.js` should remain the focused POST transport modules, while `dashboard.js` remains the only browser shell that touches DOM, URL/history, and SSE lifecycle concerns
- the reducer split now keeps `src/glassbox/web/static/state.js` as the public facade while moving base state to `state-core.js`, snapshot shaping to `state-snapshot.js`, session/stream transitions to `state-stream.js`, browser submission-state helpers to `state-interaction.js`, and incremental event reduction to `state-events.js`
- the renderer split now keeps `src/glassbox/web/static/render.js` as the public facade while moving shared HTML helpers to `render-utils.js`, session-discovery and selected-session summary panes to `render-session-panes.js`, transcript/live-activity panes to `render-activity-panes.js`, operator-action panes to `render-action-panes.js`, and diagnostics panes to `render-diagnostics-panes.js`
- the dashboard app-entry split now keeps `src/glassbox/web/static/dashboard.js` as the public facade while moving snapshot/index fetches and SSE setup to `dashboard-transport.js`, stateful browser orchestration to `dashboard-controller.js`, and DOM rendering plus event binding to `dashboard-dom.js`

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

## Boundary Guardrails

The refactor roadmap now has lightweight enforcement for the most important boundaries above.

The guardrails are intentionally narrow:

- `tests/unit/test_architecture_guardrails.py` enforces dependency direction for `store`, `services`, CLI command modules, and web route modules
- the store and services packages are guarded against importing outward into `runtime`, `cli`, or `web`
- CLI command modules and web route modules are guarded against reaching into raw SQLite helpers instead of using repository, service, or query seams
- thin public facades are kept reviewable with soft size caps and explicit delegate-module checks for `runtime/__init__.py`, `store/sqlite.py`, `runtime/eval_summary.py`, `runtime/replay.py`, and the browser entry facades in `web/static/`
- those guardrails intentionally protect the public runtime entry surfaces around bootstrap, replay, and eval without turning internal coordinator modules such as `turn_engine.py` or `replay_orchestrator.py` into brittle size-capped policy targets

If a guardrail fails, the default repair should be to move new behavior into the owning split module or add one focused neighbor module, not to widen a facade or cross a subsystem boundary.

## Acceptable Temporary Compatibility Shims

The following temporary compatibility patterns are acceptable during this refactor pass:

- `__init__.py` re-exports that preserve stable import paths while internals move behind them
- thin forwarding wrappers that preserve repository adapter behavior while internal store modules split
- thin adapter layers that keep existing route or CLI call sites working while shared query services are introduced
- module-local helper imports retained temporarily while large files are being extracted incrementally

These shims are acceptable only if they are clearly transitional and do not reintroduce the same architectural ambiguity the refactor is trying to remove.

## Shims That Must Not Become Permanent

The following patterns are not acceptable as stable endpoints:

- a new grab-bag helper module that simply becomes the next monolith
- broad runtime package re-exports that hide ownership of replay, context, query, and bootstrap code behind one import surface
- route modules that keep business logic inline after a shared query service exists
- CLI command handlers that continue to duplicate session-summary or next-action shaping once shared query paths land
- replay code that keeps a second copy of live model-loop behavior after the shared execution boundary exists

## Task Mapping

This boundary note is the source of truth for the early refactor tasks in [refactor-v1.md](./refactor-v1.md).

The intended mapping is:

- `GBX-R101`: shared model-loop boundary for live turns and replay
- `GBX-R102`: shared session snapshot and query service in `src/glassbox/runtime/session_queries.py`
- `GBX-R103`: store-internal split under stable repository adapters via the `_sqlite_*.py` internal modules behind `store/sqlite.py`
- `GBX-R104`: export-surface tightening and dependency-direction cleanup

Later tasks should follow this boundary map rather than redefining subsystem ownership case by case.

## How To Use This Note

Before starting a refactor task:

- confirm the target boundary exists in this note
- decide whether the task is boundary repair or a downstream file split
- preserve behavior first, then remove temporary shims once the new boundary is exercised and covered

If a later task reveals that one of these boundaries is wrong, update this note and the relevant roadmap task together rather than letting code and docs drift.
