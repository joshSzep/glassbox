# Glassbox Refactor v8 Tasks

For the docs hub and operator guides, start at [README.md](./README.md). This
file is the post-v8 refactor task graph for the autonomy-era implementation
surfaces that grew after the original [refactor-v1.md](./refactor-v1.md)
roadmap closed.

## Purpose

This document defines a behavior-preserving refactor roadmap for the current
post-v8 Glassbox codebase.

It is written in the same execution style as [refactor-v1.md](./refactor-v1.md)
and the main task graph documents: explicit dependencies, small vertical
slices, concrete deliverables, and quality requirements attached directly to the
work.

This roadmap is not a product-feature roadmap. It exists to keep the v8
auditable-autonomy implementation easy to evolve by:

- reducing newly oversized source files
- clarifying module boundaries around background jobs, workspace memory,
  repository intelligence, observability, terminal UI state, and dashboard
  stores
- preserving the event-sourced source-of-truth model while improving
  maintainability
- extending the original refactor guardrails to the post-v8 growth areas

The original refactor roadmap completed through `GBX-R191`. This document starts
a new follow-on queue rather than rewriting that history.

## Refactor Direction

The current architecture is coherent and the original v1 decomposition largely
held. The pressure now sits in newer v8-era surfaces that accumulated broad
coordination responsibilities while autonomy, background jobs, workspace memory,
repository intelligence, provider diagnostics, and richer dashboard controls
landed.

This refactor plan should optimize for eight outcomes:

- explicit post-v8 boundary documentation before moving code
- stronger guardrails for the autonomy-era modules
- smaller runtime modules for background work, memory capture, observability,
  provider evidence, and repository indexing
- clearer store query boundaries by projection domain
- thinner repository adapters that preserve stable service contracts
- smaller terminal UI modules with separated state models, reducers, selectors,
  and widgets
- dashboard stores split by domain while preserving exported factory
  compatibility
- component splits for large autonomy-console views without changing API or
  workflow behavior

The refactor thesis is:

- keep `events` as the canonical source of truth
- preserve existing CLI, TUI, dashboard, replay, eval, and HTTP behavior unless
  a task explicitly says otherwise
- prefer extraction and redirection over rewrites
- add characterization coverage before moving behavior that is easy to regress
- improve architectural seams before optimizing file size mechanically

## Agent Execution Rules

These rules apply to every task in this file.

1. Respect dependency order. Do not start a task until its dependencies are
   complete unless the task explicitly says it can proceed in parallel.
2. Preserve current behavior by default. Refactor tasks should not intentionally
   change CLI semantics, TUI behavior, snapshot payloads, API payloads, replay
   outcomes, eval outcomes, or dashboard workflows unless the task explicitly
   includes that contract change.
3. Treat `events` as the canonical source of truth. New helpers, query services,
   dashboard stores, and UI projections remain derived from canonical events,
   typed API responses, or rebuildable projection tables.
4. Repair architectural duplication before splitting files mechanically. If two
   modules share control flow or data shaping, extract the shared boundary
   first.
5. Prefer extractions with thin compatibility shims over broad rewrites. Keep
   diffs incremental and executable.
6. Do not introduce new framework layers unless they remove a real current
   coupling in the codebase.
7. Keep public facades stable unless a task explicitly changes the import or API
   contract.
8. Every refactor task automatically includes:
   - automated tests for the moved or extracted behavior where practical
   - `ruff` formatting and lint compliance for touched Python code
   - `ty` typecheck compliance for touched Python code
   - focused `pytest` coverage for touched runtime, store, CLI, TUI, web,
     replay, eval, daemon, memory, index, task, provider, and observability
     behavior
   - frontend lint, typecheck, tests, and build when the task touches dashboard
     code, generated API types, or packaged static assets
   - documentation updates when public module boundaries, architecture
     references, import surfaces, or operator-visible behavior change materially

## Completion Contract For Any Task

A task is complete only when all of the following are true:

- the implementation exists in the intended module boundary
- automated tests covering the touched behavior exist and pass
- lint, formatting, and type checks pass for the touched slice
- compatibility shims, if any, are either justified explicitly or tracked by a
  follow-up task in this file
- docs are updated if the refactor changes documented architecture, import
  surfaces, API payloads, command behavior, or operator-visible outputs
- the refactor does not weaken the local-first, event-sourced, replay-aware
  architecture described in [architecture.md](./architecture.md)

## Suggested Status Markers

If an agent updates this document later, use one of these markers next to task
IDs:

- `TODO`
- `IN_PROGRESS`
- `BLOCKED`
- `DONE`

## Expected Repository Targets

These are the main implementation areas referenced below:

```text
src/glassbox/
    cli/tui/
    core/
    runtime/
    store/
    web/
frontend/
tests/
docs/
```

## Recommended Validation Commands

Use the narrowest viable validation after each task, but the baseline validation
pattern for completed work should be:

```bash
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run pytest
pnpm --dir frontend lint
pnpm --dir frontend typecheck
pnpm --dir frontend test
pnpm --dir frontend build
```

During incremental refactor work, use narrower commands when possible:

```bash
uv run pytest tests/unit/test_specific_module.py
uv run pytest tests/integration/test_specific_flow.py
uv run ruff check src/glassbox/path.py tests/path_test.py
uv run ty check src/glassbox/path.py
pnpm --dir frontend test -- dashboard-stores.test.ts
pnpm --dir frontend typecheck
```

## Current State

The original refactor-v1 roadmap completed its initial boundary repair and
follow-on phases. The codebase now has strong first-generation seams for:

- shared live-turn and replay model-loop execution
- runtime session-query shaping shared by CLI and web consumers
- split SQLite internals behind stable repository adapters
- split CLI parser, command, runtime runner, and formatter modules
- split replay and eval facades
- static-exported Next.js dashboard served by FastAPI
- lightweight architecture guardrails for the original refactor-sensitive seams

The post-v8 pressure points are different. They are concentrated in autonomy-era
coordinators and UI modules that grew after those original guardrails were
written:

- `src/glassbox/runtime/background_jobs.py`
- `src/glassbox/runtime/workspace_memory_capture.py`
- `src/glassbox/runtime/observability.py`
- `src/glassbox/runtime/repository_index.py`
- `src/glassbox/store/sqlite_queries.py`
- `src/glassbox/store/repositories.py`
- `src/glassbox/cli/tui/conversation.py`
- `src/glassbox/cli/tui/widgets.py`
- `frontend/stores/dashboard-stores.ts`
- large autonomy dashboard components under `frontend/components/console/`

The tasks below should keep operator-visible behavior stable while moving those
surfaces toward clearer ownership.

## Milestone Map

The intended post-v8 refactor milestone order is:

1. post-v8 boundary refresh and guardrails
2. runtime autonomy decomposition
3. store and query boundary cleanup
4. terminal UI decomposition
5. frontend store and autonomy-console decomposition
6. documentation and closeout

Each phase below corresponds to one concrete refactor milestone.

## Task Graph

---

## Phase 50: Post-v8 Boundary Refresh

### GBX-R200: Define Post-v8 Refactor Boundary Map

- Status: `DONE`
- Depends on: `GBX-R191`
- Goal: update the refactor boundary map for autonomy-era runtime, store, TUI,
  and dashboard surfaces before moving code
- Deliverables:
  - update [refactor-boundaries.md](./refactor-boundaries.md) with target
    boundaries for background jobs, workspace memory capture, observability,
    repository intelligence, provider evidence, TUI state/rendering, and
    dashboard stores
  - identify which large files are legitimately model-heavy versus mixed
    responsibility coordinators
  - dependency-direction rules for post-v8 modules that should stay free of
    raw store, HTTP, frontend, or runtime orchestration concerns
  - explicit non-goals so behavior-preserving refactor work does not become new
    autonomy feature work
- Implementation notes:
  - ground the boundary map in the current implementation, not aspirational
    platform design
  - preserve the event-sourced, local-first architecture as the source of truth
  - keep current public facades stable unless a follow-on task says otherwise
- Tests and validation included in task:
  - docs review against the current implementation in `runtime`, `store`,
    `cli/tui`, `web`, and `frontend`
  - manual verification that later tasks in this file map cleanly onto the
    updated boundary map
- Done when:
  - the repo has a code-aligned post-v8 refactor boundary map that later tasks
    can follow without reopening architectural scope repeatedly

### GBX-R201: Extend Architecture Guardrails For Post-v8 Growth Areas

- Status: `DONE`
- Depends on: `GBX-R200`
- Goal: prevent the autonomy-era modules from re-accumulating the coupling that
  the original refactor pass removed elsewhere
- Deliverables:
  - extended guardrails in
    [test_architecture_guardrails.py](../tests/unit/test_architecture_guardrails.py)
  - facade or size checks for new public post-v8 boundaries where practical
  - import-direction checks that keep store, route, TUI, and frontend state
    boundaries honest
  - clear guardrail messages that tell future agents where new behavior should
    move instead of merely failing on size
- Implementation notes:
  - avoid brittle caps on legitimate model-only files
  - prefer guardrails around dependency direction, facade thinness, and known
    domain boundaries
  - keep frontend guardrails focused on source-owned boundaries rather than
    generated API types
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_architecture_guardrails.py`
  - focused checks proving the new guardrails fail with useful messages when
    boundaries are violated
- Done when:
  - post-v8 refactor-sensitive boundaries have lightweight enforcement similar
    to the completed v1 facades

---

## Phase 51: Runtime Autonomy Decomposition

### GBX-R210: Split Background Job Worker By Ownership Concern

- Status: `DONE`
- Depends on: `GBX-R200`
- Goal: reduce
  [background_jobs.py](../src/glassbox/runtime/background_jobs.py) to worker
  coordination by extracting lease/recovery, read-only job handlers, mutating
  continuation handlers, and failure/progress recording
- Deliverables:
  - lease, cancellation, and stale-claim recovery helpers in an owned runtime
    module
  - read-only maintenance job handlers separated from mutating task continuation
    handlers
  - shared progress, completion, and failure recording helpers
  - compatibility imports or a stable public runner surface for daemon callers
- Implementation notes:
  - preserve current job event ordering and background job state transitions
  - keep mutating continuation behavior visibly separate from read-only
    maintenance behavior
  - do not change job type strings, CLI output, or projection behavior as part
    of this refactor
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_background_job_runner.py`
  - `uv run pytest tests/integration/test_background_jobs.py`
  - `uv run pytest tests/integration/test_daemon_runtime.py`
  - `uv run pytest tests/integration/test_observability_status.py`
- Done when:
  - background job coordination remains behavior-compatible while job-specific
    execution logic lives in explicit owned modules
- Completed:
  - `background_jobs.py` now stays focused on worker-loop coordination and the
    stable public runner surface
  - lease recovery/cancellation handling lives in
    `runtime/background_job_lifecycle.py`
  - read-only maintenance and derived-index handlers live in
    `runtime/background_job_handlers.py`
  - mutating task continuation handling lives in
    `runtime/background_task_continuation.py`
  - progress and failure event recording lives in
    `runtime/background_job_records.py`

### GBX-R211: Split Workspace Memory Capture Into Extraction, Redaction, And Commit Layers

- Status: `DONE`
- Depends on: `GBX-R200`
- Goal: reduce
  [workspace_memory_capture.py](../src/glassbox/runtime/workspace_memory_capture.py)
  by separating candidate extraction, model-assisted suggestions, redaction,
  candidate filtering, and event commit behavior
- Deliverables:
  - extraction helpers for runtime notes, task outcomes, stable commands,
    repeated failures, confirmed fixes, and model-assisted suggestions
  - redaction helpers with focused coverage for sensitive text handling
  - candidate filtering, dedupe, staleness, and usefulness helpers in a small
    pure module
  - service methods that stay focused on repository validation and event commit
- Implementation notes:
  - preserve the review-gated memory posture: extraction proposes candidates,
    it does not silently create durable memory
  - preserve candidate IDs and redaction behavior unless a task explicitly
    changes that contract
  - keep model-assisted suggestions review-only and confidence-gated
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_workspace_memory_capture.py`
  - `uv run pytest tests/integration/test_cli_memory_commands.py`
  - `uv run pytest tests/integration/test_web_memory_routes.py`
  - `uv run pytest tests/integration/test_background_job_runner.py`
- Done when:
  - workspace memory capture has explicit extraction, redaction, filtering, and
    commit boundaries without changing operator-visible memory workflows
- Completed:
  - `workspace_memory_capture.py` remains the public service and repository
    protocol facade
  - candidate models, IDs, usefulness, dedupe, and staleness filtering live in
    `runtime/workspace_memory_candidates.py`
  - runtime-note, task-outcome, stable-command, repeated-failure,
    confirmed-fix, and model-assisted extraction live in
    `runtime/workspace_memory_extraction.py`
  - sensitive text handling lives in `runtime/workspace_memory_redaction.py`
  - confirmation, merge, rejection, and operator-memory event construction
    lives in `runtime/workspace_memory_commits.py`

### GBX-R212: Split Observability Collectors From Report Aggregation

- Status: `DONE`
- Depends on: `GBX-R200`
- Goal: reduce [observability.py](../src/glassbox/runtime/observability.py) by
  extracting domain collectors while preserving the public workspace report
  shape
- Deliverables:
  - collector modules for runtime/event transport, projections, artifacts,
    verification, background jobs, task autonomy, workspace memory, repository
    index, branch search, and provider canary posture
  - `build_workspace_observability_report` kept as the aggregation facade
  - stable JSON and text output behavior through existing CLI formatters
- Implementation notes:
  - keep observability read-only and scriptable
  - do not introduce mutations or repair actions into report-building code
  - preserve `next_actions` wording where tests and docs rely on it
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_observability_status.py`
  - `uv run pytest tests/unit/test_release_candidate_docs.py`
  - focused unit coverage for extracted collectors where practical
- Done when:
  - observability report assembly is still one coherent public API, but each
    health domain has a small owned collector
- Completed:
  - `observability.py` now aggregates and re-exports the stable public report
    API
  - shared report models live in `runtime/observability_models.py`
  - runtime/event transport, projection, artifact, background-job, task
    autonomy, workspace-memory, repository-index, branch-search, and
    verification collectors live in focused `runtime/observability_*`
    modules
  - provider canary evidence remains loaded through the existing provider
    canary read model and is included by the aggregation facade

### GBX-R213: Split Repository Index Builder Into Discovery, Extraction, And Search Modules

- Status: `DONE`
- Depends on: `GBX-R200`
- Goal: reduce
  [repository_index.py](../src/glassbox/runtime/repository_index.py) by
  separating file discovery, entry extraction, persistence, freshness checking,
  and search
- Deliverables:
  - deterministic file discovery and exclusion helpers
  - source entry extraction helpers for project markers, docs, evals, source
    files, modules, symbols, tests, commands, and dependencies
  - persistence and freshness helpers that preserve the current on-disk artifact
    format
  - search helpers that keep the current matching semantics stable
- Implementation notes:
  - preserve entry IDs, builder version behavior, freshness semantics, and
    artifact path conventions unless a task explicitly changes them
  - keep this local and deterministic; do not introduce embeddings, external
    indexes, or network access
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_repository_index.py`
  - `uv run pytest tests/integration/test_cli_repository_commands.py`
  - `uv run pytest tests/integration/test_web_repository_index_routes.py`
  - `uv run pytest tests/integration/test_background_job_runner.py`
- Done when:
  - repository intelligence remains behavior-compatible while the builder,
    persistence, freshness, and search concerns are independently owned
- Completed:
  - `repository_index.py` remains the stable build/read/search facade
  - deterministic file discovery, exclusions, index path constants, and source
    digests live in `runtime/repository_index_discovery.py`
  - project marker, docs, eval, source, module, symbol, test, command, and
    dependency entry extraction lives in
    `runtime/repository_index_extraction.py`
  - artifact persistence and freshness loading live in
    `runtime/repository_index_persistence.py`
  - search matching and entry lookup live in
    `runtime/repository_index_search.py`

---

## Phase 52: Store And Query Boundary Cleanup

### GBX-R220: Split SQLite Projection Queries By Domain

- Status: `DONE`
- Depends on: `GBX-R200`
- Goal: reduce [sqlite_queries.py](../src/glassbox/store/sqlite_queries.py) by
  splitting read-only projection queries into domain-specific modules
- Deliverables:
  - domain modules for transcript and tool/approval reads
  - domain modules for task, budget, branch-search, runtime-note, and metric
    reads
  - stable repository adapter methods that preserve current callers
  - compatibility forwarding where needed during migration
- Implementation notes:
  - keep all query helpers read-only
  - preserve ordering, pagination, enum conversion, and lineage behavior
  - avoid exposing raw query modules to CLI or web routes
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_sqlite_session_store.py`
  - `uv run pytest tests/integration/test_sqlite_projections.py`
  - `uv run pytest tests/integration/test_projection_rebuild.py`
  - `uv run pytest tests/integration/test_web_session_pagination.py`
  - focused query tests for each moved domain
- Done when:
  - projection read helpers are owned by domain and repository behavior remains
    unchanged

### GBX-R221: Thin The SQLite Repository Adapter With Domain Delegates

- Status: `DONE`
- Depends on: `GBX-R220`
- Goal: reduce [repositories.py](../src/glassbox/store/repositories.py) while
  keeping `SQLiteSessionRepository` as the stable public adapter
- Deliverables:
  - internal delegate helpers or composed domain adapters for sessions, events,
    projections, tasks, background jobs, memory, branch search, and artifacts
  - stable `services/contracts.py` protocol compatibility
  - no CLI or web imports of concrete delegate internals
- Implementation notes:
  - do not break existing repository construction in runtime bootstrap
  - keep `SQLiteSessionRepository` easy to instantiate in tests
  - avoid creating a new grab-bag delegate that simply moves the monolith
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_service_contracts.py`
  - `uv run pytest tests/integration/test_sqlite_session_store.py`
  - `uv run pytest tests/integration/test_background_jobs.py`
  - `uv run pytest tests/integration/test_workspace_backup.py`
  - `uv run pytest tests/unit/test_architecture_guardrails.py`
- Done when:
  - repository adapter behavior remains stable while domain-heavy forwarding
    logic is easier to navigate and extend

---

## Phase 53: Terminal UI Decomposition

### GBX-R230: Split TUI Conversation Models From Event Reducers

- Status: `DONE`
- Depends on: `GBX-R200`
- Goal: reduce
  [conversation.py](../src/glassbox/cli/tui/conversation.py) by separating
  terminal state models, snapshot hydration, event reducers, action derivation,
  and display selectors
- Deliverables:
  - state model module for terminal conversation dataclasses and enums
  - snapshot hydration module for initial dashboard snapshots
  - event reducer module for applying canonical event envelopes
  - selector module for header display, mode labels, terminal action state, and
    stream status derivation
  - compatibility exports where needed by existing tests and widgets
- Implementation notes:
  - keep reducer functions pure
  - preserve current terminal state shapes unless a task explicitly changes them
  - avoid importing Textual widget code into reducer or selector modules
  - completed split keeps `conversation.py` as a compatibility facade over
    `conversation_models.py`, `conversation_hydration.py`,
    `conversation_reducer.py`, and `conversation_selectors.py`
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_cli_tui_conversation.py`
  - `uv run pytest tests/unit/test_cli_tui_workflows.py`
  - `uv run pytest tests/unit/tui_workflow_scenarios.py`
- Done when:
  - terminal conversation state and event reduction are modular without changing
    TUI behavior

### GBX-R231: Split TUI Widgets By Pane Family

- Status: `DONE`
- Depends on: `GBX-R230`
- Goal: reduce [widgets.py](../src/glassbox/cli/tui/widgets.py) by separating
  header, transcript, details, composer, action strip, and command palette
  widget families
- Deliverables:
  - widget modules grouped by pane or interaction family
  - pure render helpers kept separate from Textual widget lifecycle concerns
  - stable imports through `cli/tui/widgets.py` during migration if needed
- Implementation notes:
  - preserve keyboard, focus, scrolling, markdown rendering, and feedback
    behavior
  - keep layout-sensitive helpers covered before moving them
  - do not change the TUI visual contract as part of this refactor
  - completed split keeps `widgets.py` as a compatibility facade over
    `widget_header.py`, `widget_transcript.py`, `widget_details.py`,
    `widget_composer.py`, `widget_action.py`, `widget_palette.py`, and shared
    `widget_formatting.py` helpers
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_cli_tui_widgets.py`
  - `uv run pytest tests/unit/test_cli_tui_app.py`
  - `uv run pytest tests/unit/test_cli_tui_workflows.py`
  - `uv run pytest tests/integration/test_cli_tui_launch_smoke.py`
- Done when:
  - terminal widgets are organized by UI family and existing TUI workflows remain
    regression-covered

### GBX-R232: Thin TUI App Coordination Around State And Widget Boundaries

- Status: `DONE`
- Depends on: `GBX-R230`, `GBX-R231`
- Goal: reduce coordination pressure in
  [app.py](../src/glassbox/cli/tui/app.py) by routing state updates and widget
  refreshes through the newly split TUI boundaries
- Deliverables:
  - small app-level helpers for stream lifecycle, action feedback, command
    dispatch, and widget refresh
  - clear ownership between Textual app lifecycle and pure conversation state
  - preserved public factory functions for TUI creation
- Implementation notes:
  - do not change launch/fallback semantics
  - keep interactive client behavior unchanged
  - preserve test-driver ergonomics for unit tests
  - completed split keeps `app.py` as the Textual lifecycle owner while routing
    stream handling, widget refresh, command dispatch, feedback mapping, and
    artifact path resolution through focused `app_*` helpers
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_cli_tui_app.py`
  - `uv run pytest tests/unit/test_cli_interactive_launch.py`
  - `uv run pytest tests/integration/test_cli_interactive_commands.py`
  - `uv run pytest tests/integration/test_cli_tui_launch_smoke.py`
- Done when:
  - the TUI app remains the lifecycle owner while pure state, rendering, and
    command logic live behind focused boundaries

---

## Phase 54: Frontend Store And Autonomy-Console Decomposition

### GBX-R240: Split Dashboard Stores By Domain

- Status: `DONE`
- Depends on: `GBX-R200`
- Goal: reduce
  [dashboard-stores.ts](../frontend/stores/dashboard-stores.ts) by moving
  console, session, task, knowledge, and branch-search stores into domain-owned
  modules
- Deliverables:
  - `console-store`, `session-store`, `task-store`, `knowledge-store`, and
    `branch-search-store` modules or equivalent domain files
  - shared async action helpers for request IDs, pending/succeeded/failed
    action states, and error normalization
  - stable exports from `frontend/stores/dashboard-stores.ts` for existing
    call sites and tests
  - unchanged Zustand store behavior and API client contracts
- Implementation notes:
  - preserve factory names and exported types where practical
  - keep generated API types as the source for response contracts
  - do not introduce a new frontend state library
  - completed split keeps `frontend/stores/dashboard-stores.ts` as the
    compatibility facade while domain factories and state types live in
    `console-store.ts`, `session-store.ts`, `task-store.ts`,
    `knowledge-store.ts`, and `branch-search-store.ts`; shared request tracking,
    async action status helpers, and error normalization live in
    `store-actions.ts`
- Tests and validation included in task:
  - `pnpm --dir frontend test -- dashboard-stores.test.ts`
  - `pnpm --dir frontend typecheck`
  - `pnpm --dir frontend lint`
  - focused tests for stale request suppression, stream lifecycle, and domain
    actions
  - verified with `pnpm --dir frontend test -- dashboard-stores.test.ts`,
    `pnpm --dir frontend typecheck`, and `pnpm --dir frontend lint`
- Done when:
  - dashboard state coordination is split by domain while exported compatibility
    and behavior remain stable

### GBX-R241: Split Large Autonomy Console Components

- Status: `TODO`
- Depends on: `GBX-R240`
- Goal: reduce large dashboard autonomy components into smaller view sections
  while preserving the operator-console workflow
- Deliverables:
  - section components for task autonomy queue, task detail, task actions, and
    verification evidence
  - section components for workspace memory list/detail/actions and repository
    index status/search/actions
  - section components for verification/provider cues where current files mix
    formatting and layout
  - component tests updated to use the new owned sections
- Implementation notes:
  - keep API calls in stores, not components
  - preserve current copy, responsive behavior, action affordances, and loading
    states unless a task explicitly changes them
  - avoid adding decorative layout or a new design language during refactor work
- Tests and validation included in task:
  - `pnpm --dir frontend test -- task-autonomy-console.test.tsx`
  - `pnpm --dir frontend test -- knowledge-autonomy-console.test.tsx`
  - `pnpm --dir frontend test -- verification-cues.test.ts`
  - `pnpm --dir frontend typecheck`
  - `pnpm --dir frontend lint`
- Done when:
  - the autonomy console is easier to maintain without changing operator-visible
    dashboard behavior

### GBX-R242: Split Session Inspector Diagnostic Panes By Evidence Type

- Status: `TODO`
- Depends on: `GBX-R240`
- Goal: reduce the largest session-inspector pane modules by grouping runtime,
  policy, verification, projection, and replay evidence into focused sections
- Deliverables:
  - smaller pane modules under
    `frontend/components/console/session-inspector/panes/`
  - pure formatting helpers where evidence shaping is repeated
  - stable tab and pane composition through the existing inspector entrypoints
- Implementation notes:
  - preserve current tab names, inspector layout, and payload expectations
  - do not move canonical session-state normalization into components
  - keep component tests focused on rendered evidence and action availability
- Tests and validation included in task:
  - `pnpm --dir frontend test -- session-inspector.test.ts`
  - `pnpm --dir frontend test -- session-state.test.ts`
  - `pnpm --dir frontend typecheck`
  - `pnpm --dir frontend lint`
- Done when:
  - session inspector panes remain behavior-compatible while large diagnostic
    surfaces are organized by evidence type

---

## Phase 55: Documentation And Closeout

### GBX-R250: Update Architecture Docs For The Post-v8 Refactor Shape

- Status: `TODO`
- Depends on: `GBX-R210`, `GBX-R211`, `GBX-R212`, `GBX-R213`, `GBX-R220`,
  `GBX-R221`, `GBX-R230`, `GBX-R231`, `GBX-R232`, `GBX-R240`, `GBX-R241`,
  `GBX-R242`
- Goal: align architecture and reference docs with the final post-v8 refactor
  module boundaries
- Deliverables:
  - updates to [architecture.md](./architecture.md) where runtime, store, TUI,
    and dashboard ownership changed materially
  - updates to [database.md](./database.md) if store query or repository
    boundary descriptions changed
  - updates to [refactor-boundaries.md](./refactor-boundaries.md) marking the
    post-v8 boundary map as implemented
  - updates to [README.md](./README.md) or [docs/README.md](./README.md) only if
    the new refactor doc should be linked from the docs hub
- Implementation notes:
  - keep the docs focused on current behavior, not implementation archaeology
  - avoid claiming new product behavior from refactor-only work
  - remove or revise temporary compatibility notes that are no longer true
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_release_candidate_docs.py`
  - doc review against the final implementation
- Done when:
  - docs and code describe the same post-v8 architecture and remaining shims are
    either justified or tracked

### GBX-R251: Close Out Post-v8 Refactor Guardrails And Validation

- Status: `TODO`
- Depends on: `GBX-R250`
- Goal: add final characterization and validation coverage proving the post-v8
  refactor preserved behavior across runtime, store, TUI, and dashboard seams
- Deliverables:
  - final guardrail coverage for new facades and domain boundaries
  - characterization tests for the highest-risk moved behavior where not already
    covered
  - documented validation command set for future post-v8 refactor tasks
- Implementation notes:
  - prefer narrow guardrails that catch real coupling regressions
  - do not freeze implementation details that are intentionally internal and
    low-risk
  - keep compatibility shims only when they serve a real public import or route
    contract
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_architecture_guardrails.py`
  - focused backend and frontend tests for all refactored seams
  - final baseline validation as practical for the touched repository state
- Done when:
  - the post-v8 refactor roadmap can be marked complete with guardrails that
    protect the new module shape from immediate regression
