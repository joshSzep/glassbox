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
- context-building logic should separate structured snapshot derivation, working-set derivation, and prompt rendering
- runtime query code should provide session summaries and snapshots to both CLI and web consumers without embedding HTTP concerns
- bootstrap should wire public collaborators together, not hide ownership behind broad transitive re-exports

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

#### Target Web Frontend Sub-Boundaries

- reducer and snapshot-normalization logic should stay pure
- pane rendering should stay pure and be grouped by UI responsibility
- fetch/SSE transport and DOM-binding logic should live outside pure reducers and renderers

### Replay And Eval

Replay and eval logic lives in `runtime`, but it should maintain its own internal boundaries.

Its stable responsibilities are:

- replay bundle loading and export
- deterministic runtime playback
- normalized-state comparison and mismatch collection
- replay triage and eval summary/report generation

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
- `GBX-R102`: shared session snapshot and query service
- `GBX-R103`: store-internal split under stable repository adapters
- `GBX-R104`: export-surface tightening and dependency-direction cleanup

Later tasks should follow this boundary map rather than redefining subsystem ownership case by case.

## How To Use This Note

Before starting a refactor task:

- confirm the target boundary exists in this note
- decide whether the task is boundary repair or a downstream file split
- preserve behavior first, then remove temporary shims once the new boundary is exercised and covered

If a later task reveals that one of these boundaries is wrong, update this note and the relevant roadmap task together rather than letting code and docs drift.
