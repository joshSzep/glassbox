# Glassbox Refactor Boundaries

For the docs hub and operator guides, start at [README.md](./README.md). This note defines the target architectural boundaries for the v1 refactor roadmap in [refactor-v1.md](./refactor-v1.md), the post-v8 follow-on roadmap in [refactor-v8.md](./refactor-v8.md), and the second-order v10 roadmap in [refactor-v10.md](./refactor-v10.md).

## Purpose

This document is the architecture source of truth for the refactor roadmap.

It exists to answer one question before code moves begin:

What are the intended module boundaries for the current Glassbox implementation, and what kinds of changes are explicitly out of scope for the first refactor pass?

This note is intentionally code-aligned. It describes the current implementation shape and the target decomposition boundaries for refactor work already captured in [refactor-v1.md](./refactor-v1.md), [refactor-v8.md](./refactor-v8.md), and [refactor-v10.md](./refactor-v10.md). It does not define a new product architecture.

## Implementation Status

The post-v8 boundary map is implemented as of Phase 55 of
[refactor-v8.md](./refactor-v8.md). Runtime autonomy, store projection reads and
repository adapters, TUI state/widgets/app coordination, dashboard stores,
autonomy console sections, and session-inspector diagnostic panes now follow the
module boundaries described here.

The remaining compatibility modules named in this document are stable import
facades. They preserve public call sites while delegating to owned
implementation modules; they are not license for new behavior to accumulate in
the facade.

The v10 boundary refresh is the active next step. It does not reopen the v1 or
v8 decomposition decisions; it identifies the second-order modules that grew
after those splits and defines the target owners for the next behavior-preserving
extractions.

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
- change task-autonomy, verification, compare, provider, tool-policy, HTTP,
  projection, or core event/model behavior while performing v10 refactor-only
  movement

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

The v10 pressure points are the second-order modules underneath those improved
facades:

- `frontend/components/console/task-autonomy-sections.tsx` mixes task queue
  rendering, plan inspection, action controls, verification posture, evidence
  summaries, event analysis, and formatting helpers
- `frontend/components/console/verification-cues.tsx` mixes cue derivation for
  policies, evals, replay drift, provider evidence, release evidence,
  artifacts, and path overlap with visual rendering
- `frontend/components/console/session-inspector/panes/compare-pane.tsx` mixes
  session comparison derivation with pane rendering
- `frontend/components/console/workspace-console.tsx` mixes route
  synchronization, surface selection, load/reset orchestration, action binding,
  and surface composition
- `src/glassbox/web/routes/sessions.py` and `src/glassbox/web/routes/tasks.py`
  mix FastAPI declarations with HTTP-local query composition, action
  orchestration, pagination, and serialization helpers
- `src/glassbox/runtime/task_queries.py` mixes transport-agnostic query models,
  summary/detail shaping, verification ledger interpretation, repair-history
  wording, and event conversion
- `src/glassbox/runtime/provider_canary.py` is now a thin compatibility facade;
  provider-canary scenarios, live execution, retained evidence reads,
  freshness checks, report writing, and outcome counting live in focused
  `provider_canary_*` helper modules
- `src/glassbox/runtime/provider_recommendations.py` is now a recommendation
  orchestration facade; recommendation models and capability, risk, credential,
  failure, budget, and next-action scoring live in focused
  `provider_recommendation_*` helper modules
- `src/glassbox/tools/policy.py` mixes path-scope evaluation, rule matching,
  autonomy budget permits, approval message construction, and command-risk
  heuristics
- `src/glassbox/store/sqlite_schema.py` mixes baseline schema/migration running
  with domain-specific projection table and migration definitions
- `src/glassbox/core/events.py` and `src/glassbox/core/models.py` are large
  model-heavy core modules. They are acceptable as broad public import surfaces
  until a domain expansion would otherwise make event registration, review, or
  ownership unsafe.

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

#### V10 Runtime Query And Provider Sub-Boundaries

- `task_queries.py` should keep `TaskQueryService` as the repository-backed,
  read-only orchestration facade. Query view models, task summary/detail
  assembly, verification ledger interpretation, and repair-history derivation
  should live in focused transport-agnostic runtime helpers.
- Task query helpers may depend on core events/models and service repository
  contracts. They should not import FastAPI, web response models, frontend
  types, CLI formatting, or concrete store implementations.
- Provider canary code now keeps `runtime/provider_canary.py` as the stable
  public facade while `provider_canary_scenarios.py`,
  `provider_canary_execution.py`, `provider_canary_evidence.py`,
  `provider_canary_reporting.py`, and `provider_canary_models.py` own
  deterministic scenario definitions, opt-in live execution, stored evidence
  loading/freshness checks, report persistence/outcome counting, and retained
  evidence models.
- Provider recommendations now keep `runtime/provider_recommendations.py` as the
  stable public facade while `provider_recommendation_models.py`,
  `provider_recommendation_capability.py`, `provider_recommendation_risk.py`,
  `provider_recommendation_credentials.py`,
  `provider_recommendation_failures.py`, and
  `provider_recommendation_actions.py` own output contracts, capability fit,
  risk posture, credential readiness, failure posture, budget impact, and
  next-step guidance. Scoring helpers should continue to accept diagnostics,
  canary evidence, and recovery records as explicit inputs.
- Provider modules should not hide global evidence reads inside scoring helpers
  or let observability formatting leak into canary execution.

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

#### V10 SQLite Schema Sub-Boundaries

- `sqlite_schema.py` should keep the public bootstrap and migration runner
  surface: `SCHEMA_VERSION`, `MIGRATIONS`, `BOOTSTRAP_STATEMENTS`,
  `open_database`, and `initialize_database`.
- Domain-specific table statements and migration helpers should move behind an
  explicit, ordered registry grouped by projection family: tasks, verification
  ledger, checkpoints, compactions, tool attempts, background jobs, branch
  search, workspace memory, provider recovery, and long-run state.
- Schema helpers must remain idempotent and deterministic. They should not
  import runtime services, route serializers, CLI formatters, or frontend
  state, and they must not change table names, column names, indexes, or schema
  version during pure movement.

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
- the session route transport split keeps `src/glassbox/web/session_api.py` as
  the stable compatibility import surface while request/response model families
  and serializers live in focused `session_api_*` modules for common detail
  pages, actions, selected-session snapshots, operator aggregates, and builders
- v10 session-route helpers should own HTTP-local query composition for
  aggregate, snapshot, transcript, event log, tool calls, metrics,
  checkpoints, compactions, artifacts, and runtime summary reads while route
  modules remain the FastAPI declaration and dependency boundary
- v10 session-route action helpers should own message submission, answer
  submission, cancellation, forks, tool-attempt retry/abandon, and compaction
  refresh/invalidation orchestration while preserving current status codes and
  validation behavior
- v10 task-route helpers should own HTTP-local list/detail/steps/events and
  background-job adjacency queries plus plan approval, continuation, continuation
  windows, pause windows, pause/resume/cancel, and budget-adjustment actions
- web response models and Pydantic serializers belong in web API modules, not
  in runtime query services

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
- autonomy console components keep stable public entrypoints while task,
  knowledge, branch-search, and verification-cue presentation sections live in
  focused `*-sections.tsx` modules. These section modules own list/detail,
  evidence, action-control, and formatting UI while preserving current routes,
  API calls, and workflow behavior
- the v10 task-autonomy section split should move queue filtering/navigation and
  table rendering into task-queue-owned modules, plan inspection/detail layout
  into task-inspector modules, pause/resume/continue/cancel/approval/background
  job/budget controls into task-actions modules, verification posture and
  evidence drilldown into task-evidence modules, and event/format helpers into
  pure non-React modules
- the task-autonomy split now keeps
  `frontend/components/console/task-autonomy-sections.tsx` as a compatibility
  facade over `task-autonomy/queue.tsx`, `inspector.tsx`, `actions.tsx`,
  `evidence.tsx`, and pure helper modules in `format.ts` and `types.ts`
- verification cue rendering should consume typed pure derivation results for
  policy, eval coverage, replay drift, provider evidence, release evidence,
  artifact grouping, and path overlap rather than recomputing cue facts inline
- session compare panes should consume pure comparison analysis for branch
  metadata, transcript divergence, tool activity, policy outcomes, runtime
  projection facts, and string-set comparisons
- the verification/compare split now keeps
  `frontend/components/console/verification-cues.tsx` and
  `session-inspector/panes/compare-pane.tsx` as renderers over pure analysis
  helpers in `verification-cues-analysis.ts` and
  `session-inspector/panes/compare-analysis.ts`
- `workspace-console.tsx` should remain the surface composition owner while
  route synchronization, popstate handling, per-surface load/reset behavior, and
  repeated action binding move into focused hooks/helpers
- the workspace-console split now keeps
  `frontend/components/console/workspace-console.tsx` as the store/state
  selection and surface composition owner, with URL synchronization and
  per-surface load/reset behavior in `workspace-console/routing.ts` and repeated
  action bindings in `workspace-console/actions.ts`
- session-inspector diagnostic panes keep `diagnostics-panes.tsx` as a stable
  export facade while runtime context, metrics, event/projection evidence, and
  shared diagnostic pagination live in focused pane modules under
  `frontend/components/console/session-inspector/panes/`
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

### Tools

The `tools` package should own tool implementations and policy decisions at the
command/tool boundary.

Its stable responsibilities are:

- tool registration and execution wrappers
- command/read/patch/workflow tool behavior
- policy decisions for approval, denial, and autonomy permits
- traceable policy reasons and approval messages

The `tools` package should not own runtime task orchestration, route
serialization, or CLI presentation.

#### V10 Tool Policy Sub-Boundaries

- `tools/policy.py` should keep `ToolPolicyEngine`, `ToolPolicyContext`, and
  public decision ergonomics stable while delegating specialized behavior.
- Path-scope behavior belongs in path-policy helpers: path normalization,
  workspace containment, extension matching, and path argument extraction.
- Manifest rule matching and outcome resolution belong in policy-rule helpers.
- Autonomy budget/risk permit logic belongs in autonomy-policy helpers.
- Default and autonomy approval message construction belongs in message helpers.
- Destructive-command and command-text heuristics belong in command-risk
  helpers.
- Policy helpers may depend on policy config/models and standard-library path
  or shell parsing. They should not import runtime services, web routes, CLI
  formatters, store implementations, or frontend code.

### Core Events And Models

The `core` package owns shared domain identifiers, event payloads, models, and
cross-subsystem types.

Large core event and model files are model-heavy public infrastructure. They
should not be split for cosmetic line-count reasons. A future split is
appropriate only when a domain expansion would make event registration,
discriminated-union maintenance, or review ownership error-prone.

#### V10 Core Domain Strategy

- `glassbox.core.events` and `glassbox.core.models` should remain stable public
  import surfaces even if domain modules are introduced underneath them.
- Candidate future event/model domains are sessions, turns, tools, tasks,
  branch search, background jobs, workspace memory, repository index, provider
  recovery, verification, and compaction.
- Event payload registration must stay explicit and deterministic. If payloads
  move into domain modules, the discriminated union and serialization tests
  should continue to prove that canonical event names and payload shapes are
  unchanged.
- Core modules should not import runtime, store, CLI, web, frontend, or provider
  execution code. They may define shared models consumed by those layers.

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
- v10 frontend derivation helpers should be pure and browser-state free; store
  modules own transport, components own presentation and local interaction
  state
- web route helpers may own HTTP-local orchestration and serialization, but
  runtime task/session query services must remain transport-agnostic
- runtime provider scoring and canary evidence helpers must not import CLI,
  web, store implementations, or frontend modules
- tool-policy helper modules must not import runtime orchestration, web routes,
  CLI formatters, store implementations, or frontend modules
- SQLite schema domain helpers must stay below runtime and transport layers and
  must not perform dynamic discovery that hides migration order

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
  public runtime autonomy facades are kept reviewable with explicit delegate
  import and size checks, TUI modules are checked against raw store and runtime
  worker imports,
  frontend stores are checked against component/server/backend imports, and
  `frontend/stores/dashboard-stores.ts` is kept reviewable as the
  compatibility facade over the source-owned domain store modules
- the largest frontend console entrypoints are kept reviewable as facades over
  domain section modules, including task autonomy, knowledge autonomy, branch
  search, and session-inspector diagnostics
- v10 guardrails in `tests/unit/test_architecture_guardrails.py` now keep the
  second-order pressure-point files and completed split helpers reviewable and
  block transport/raw-store/backend imports across task-autonomy sections,
  verification cue derivation, compare analysis, workspace-console routing,
  runtime task query helpers, provider canary/recommendation helpers,
  tool-policy helpers, and SQLite schema helpers

If a guardrail fails, the default repair should be to move new behavior into the owning split module or add one focused neighbor module, not to widen a facade or cross a subsystem boundary.

## Stable Compatibility Facades

The following compatibility patterns are acceptable in the completed refactor
shape:

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
- `task-autonomy-sections.tsx`, `verification-cues.tsx`, `compare-pane.tsx`,
  `workspace-console.tsx`, `web/routes/sessions.py`, `web/routes/tasks.py`,
  `runtime/task_queries.py`, `runtime/provider_canary.py`,
  `runtime/provider_recommendations.py`, `tools/policy.py`, and
  `store/sqlite_schema.py` may keep compatibility exports or thin wrappers only
  when existing imports or route declarations require a stable transition path

These facades are acceptable only while they stay thin, reviewable, and oriented
around stable public imports. New behavior should move into the owning domain
module first, with the facade forwarding or re-exporting only when compatibility
requires it.

## Patterns That Must Not Become Permanent

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
- React components that duplicate API/store transport behavior instead of
  consuming store state
- runtime query helpers that import web response models or frontend concepts
- provider scoring helpers that read hidden global diagnostics/evidence
- SQLite schema helpers that discover migrations dynamically or change ordered
  migration semantics during refactor-only movement
- core event/model splits that destabilize public import surfaces without a
  domain expansion and serialization coverage

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
- `GBX-R300`: v10 second-order boundary map for task autonomy, verification,
  compare analysis, workspace-console routing, web route helpers, runtime task
  queries, provider evidence/recommendations, tool policy, SQLite schema
  domains, and core event/model expansion
- `GBX-R301`: v10 guardrails for the second-order pressure points before bulk
  movement begins

Later tasks should follow this boundary map rather than redefining subsystem ownership case by case.

## How To Use This Note

Before starting a refactor task:

- confirm the target boundary exists in this note
- decide whether the task is boundary repair or a downstream file split
- preserve behavior first, then remove temporary shims once the new boundary is exercised and covered

If a later task reveals that one of these boundaries is wrong, update this note and the relevant roadmap task together rather than letting code and docs drift.
