# Glassbox Refactor v10 Tasks

For the docs hub and operator guides, start at [README.md](./README.md). This
file is the next behavior-preserving refactor roadmap after
[refactor-v8.md](./refactor-v8.md). It focuses on the code paths that grew after
the post-v8 autonomy decomposition and on second-order modules that are now
large enough to become the next maintenance risk.

## Purpose

This document defines a v10 refactor roadmap for the current Glassbox codebase.

It is written in the same execution style as [refactor-v1.md](./refactor-v1.md)
and [refactor-v8.md](./refactor-v8.md): explicit dependencies, small vertical
slices, concrete deliverables, and validation requirements attached directly to
the work.

This roadmap is not a product-feature roadmap. It exists to keep the current
local-first, event-sourced architecture easy to evolve by:

- breaking apart large second-order modules created by earlier successful
  decomposition work
- keeping public facades stable while moving new behavior into owned modules
- separating route orchestration, runtime query shaping, frontend derivation,
  provider evidence, tool-policy decisions, and schema migration concerns
- preserving current CLI, TUI, dashboard, replay, eval, HTTP, and projection
  behavior unless a later task explicitly changes a contract
- extending architecture guardrails to the areas where complexity is now
  re-accumulating

## Refactor Direction

The v1 and v8 refactor roadmaps completed the first major decomposition passes.
The current repository is substantially healthier than the original monoliths:
runtime autonomy facades, store query facades, TUI facades, replay/eval facades,
dashboard stores, and console entrypoints all delegate to focused modules.

The pressure has moved. Several extracted modules are now doing real work across
too many concerns:

- frontend task-autonomy sections combine queue rendering, plan inspection,
  actions, verification evidence, event analysis, and formatting
- web route modules combine HTTP transport, pagination, validation, action
  execution, artifact shaping, and response building
- runtime task-query modules combine API models, summary shaping, verification
  ledger derivation, repair history, and event conversion
- provider canary and recommendation modules combine data models, execution,
  freshness, evidence loading, ranking, and operator guidance
- tool policy combines path scope, rule matching, autonomy budgets, approval
  messages, and command-risk classification
- SQLite schema migration code is still coherent, but each new projection adds
  more domain-specific table and migration behavior to one module

The v10 refactor thesis is:

- keep `events` as the canonical source of truth
- keep projection tables rebuildable and non-authoritative
- keep generated API types as the frontend response contract
- prefer pure derivation modules for complex frontend and runtime summaries
- keep route handlers thin and move action/query composition behind HTTP-local
  service helpers
- split by ownership and dependency direction, not by line count alone
- extend guardrails only where a failure points to an obvious local repair

## Agent Execution Rules

These rules apply to every task in this file.

1. Respect dependency order. Do not start a task until its dependencies are
   complete unless the task explicitly says it can proceed in parallel.
2. Preserve current behavior by default. Refactor tasks should not intentionally
   change CLI semantics, TUI behavior, dashboard workflows, HTTP payload shapes,
   replay outcomes, eval outcomes, event ordering, or projection behavior unless
   the task explicitly includes that contract change.
3. Treat `events` as the canonical source of truth. Query services, route
   helpers, stores, and UI projections remain derived from canonical events,
   typed API responses, or rebuildable projection tables.
4. Repair architectural duplication before splitting files mechanically. If two
   modules share control flow or data shaping, extract the shared boundary
   first.
5. Prefer extractions with thin compatibility shims over broad rewrites. Keep
   diffs incremental and executable.
6. Keep public facades stable unless a task explicitly changes the import,
   route, API, or component contract.
7. Do not introduce new framework layers unless they remove a real current
   coupling in the codebase.
8. Do not move API calls into React components. Frontend stores own transport;
   components own presentation and local interaction state; pure helper modules
   own derivation and formatting.
9. Do not move HTTP response models or FastAPI dependencies into runtime query
   services. Runtime query services should stay transport-agnostic.
10. Every refactor task automatically includes:
   - automated tests for moved or extracted behavior where practical
   - `ruff` formatting and lint compliance for touched Python code
   - `ty` typecheck compliance for touched Python code
   - focused `pytest` coverage for touched runtime, store, CLI, web, replay,
     eval, provider, tool-policy, and projection behavior
   - frontend lint, typecheck, tests, and build when the task touches dashboard
     code, generated API types, packaged static assets, or route assumptions
   - documentation updates when public module boundaries, architecture
     references, import surfaces, API payloads, command behavior, or
     operator-visible outputs change materially

## Completion Contract For Any Task

A task is complete only when all of the following are true:

- the implementation exists in the intended module boundary
- automated tests covering the touched behavior exist and pass
- lint, formatting, and type checks pass for the touched slice
- compatibility shims, if any, are justified explicitly or tracked by a
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
    core/
    runtime/
    store/
    tools/
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
pnpm --dir frontend test -- task-autonomy-console.test.tsx
pnpm --dir frontend typecheck
```

## Current State

The v1 and v8 roadmaps completed the broad first-generation module splits. The
current codebase has strong seams for:

- shared live-turn and replay model-loop execution
- runtime-context derivation shared by turn building and session queries
- split runtime bootstrap over storage, provider wiring, and service assembly
- split replay/eval orchestration and reporting facades
- split SQLite store internals and repository adapter families
- split background jobs, workspace memory capture, observability, repository
  indexing, TUI state/widgets, dashboard stores, and primary console entrypoints
- architecture guardrails for many public facades and dependency-direction
  boundaries

The next pressure points are second-order. They are not the original public
facades, but the modules that accumulated rich domain behavior underneath those
facades:

- `frontend/components/console/task-autonomy-sections.tsx`
- `frontend/components/console/verification-cues.tsx`
- `frontend/components/console/session-inspector/panes/compare-pane.tsx`
- `frontend/components/console/workspace-console.tsx`
- `src/glassbox/web/routes/sessions.py`
- `src/glassbox/web/routes/tasks.py`
- `src/glassbox/runtime/task_queries.py`
- `src/glassbox/runtime/provider_canary.py`
- `src/glassbox/runtime/provider_recommendations.py`
- `src/glassbox/tools/policy.py`
- `src/glassbox/store/sqlite_schema.py`
- `src/glassbox/core/events.py`
- `src/glassbox/core/models.py`

Large core model and event modules are not automatically bad. They should be
split only when a domain expansion would otherwise make review, ownership, or
event registration harder. The highest-priority v10 work is in mixed
coordinator and derivation modules where behavior, formatting, transport, and
state shaping are currently close together.

## Milestone Map

The intended v10 refactor milestone order is:

1. v10 boundary refresh and guardrails
2. frontend console second-order decomposition
3. web route and runtime query decomposition
4. provider and tool-policy decomposition
5. store schema and core-domain boundary planning
6. documentation and validation closeout

Each phase below corresponds to one concrete refactor milestone.

## Task Graph

---

## Phase 60: V10 Boundary Refresh

### GBX-R300: Define V10 Second-Order Refactor Boundary Map

- Status: `DONE`
- Depends on: `GBX-R251`
- Goal: update the refactor boundary map for the current post-v8 shape before
  moving code again
- Deliverables:
  - update [refactor-boundaries.md](./refactor-boundaries.md) with target
    boundaries for task-autonomy sections, verification cues, compare analysis,
    workspace-console routing, web route helpers, runtime task queries,
    provider evidence, tool policy, SQLite schema domains, and core event/model
    expansion
  - identify which large files are model-heavy and acceptable versus mixed
    responsibility modules that should be split
  - explicit non-goals so v10 refactor work does not become new task,
    dashboard, provider, or policy behavior
  - notes on which public facades should remain stable and which internal
    modules should become the new ownership targets
- Implementation notes:
  - ground the boundary map in current code paths and tests
  - keep current route payloads, component entrypoints, command output, and
    projection semantics stable
  - do not make line count alone the reason for a split
- Tests and validation included in task:
  - docs review against current `runtime`, `web`, `tools`, `store`, `core`, and
    `frontend` implementation
  - manual verification that later tasks in this file map cleanly onto the
    updated boundary map
- Done when:
  - the repo has a code-aligned v10 boundary map that later tasks can follow
    without reopening architectural scope repeatedly
- Completed notes:
  - [refactor-boundaries.md](./refactor-boundaries.md) now includes v10 target
    ownership for frontend task autonomy, verification cues, compare analysis,
    workspace-console routing, session/task route helpers, runtime task query
    helpers, provider canary/recommendation boundaries, tool-policy helpers,
    SQLite schema domains, and core event/model expansion strategy.
  - The map distinguishes model-heavy core files from mixed coordinator modules
    and keeps v10 work explicitly behavior-preserving.

### GBX-R301: Extend Architecture Guardrails For V10 Pressure Points

- Status: `DONE`
- Depends on: `GBX-R300`
- Goal: prevent the current second-order modules from growing into new hidden
  monoliths after they are split
- Deliverables:
  - guardrails in
    [test_architecture_guardrails.py](../tests/unit/test_architecture_guardrails.py)
    for v10 facades and extracted ownership modules
  - frontend size or import checks for task-autonomy sections, verification
    cues, compare panes, and workspace-console routing boundaries where
    practical
  - Python size or import checks for web route helpers, task query modules,
    provider modules, and tool-policy boundaries where practical
  - clear failure messages that name the intended destination module
- Implementation notes:
  - avoid brittle caps on generated files, model-only files, and intentionally
    broad public contracts
  - prefer dependency-direction and facade-thinness checks over arbitrary
    complexity metrics
  - make every guardrail failure locally repairable
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_architecture_guardrails.py`
  - focused tests proving new guardrail messages are actionable
- Done when:
  - v10 refactor-sensitive boundaries have lightweight enforcement before code
    starts moving in bulk
- Completed notes:
  - Added v10 guardrails for pre-split growth in the known frontend, web,
    runtime, provider, tool-policy, and SQLite schema pressure-point modules.
  - Added import-direction checks that keep v10 runtime/provider/tool/schema
    helpers away from transport, raw-store, and backend/frontend seams where
    applicable.
  - Added focused assertions that guardrail messages name the intended repair
    boundary.

---

## Phase 61: Frontend Console Second-Order Decomposition

### GBX-R310: Split Task Autonomy Sections Into Queue, Inspector, Action, And Evidence Modules

- Status: `DONE`
- Depends on: `GBX-R300`
- Goal: reduce
  [task-autonomy-sections.tsx](../frontend/components/console/task-autonomy-sections.tsx)
  by separating task queue rendering, plan inspection, task action controls,
  verification summaries, evidence drilldown, and formatting helpers
- Deliverables:
  - queue filter/navigation and table sections in a task-queue-owned module
  - task plan inspector and detail layout in a task-inspector-owned module
  - pause, resume, continue, cancel, approval, background-job, and budget
    controls in a task-actions module
  - verification posture, last-known-good, repair history, and "why this
    action" evidence in a task-evidence module
  - pure formatting and event-summary helpers in a non-React helper module
  - stable exports from `task-autonomy-sections.tsx` during migration where
    existing tests or components rely on them
- Implementation notes:
  - keep API calls in `task-store.ts`; do not move transport into components
  - preserve current copy, loading states, action affordances, and responsive
    layout unless a later task explicitly changes UX
  - keep event-derived evidence pure and separately testable
  - avoid creating one new "shared" module that simply becomes the old file
    with a different name
- Tests and validation included in task:
  - `pnpm --dir frontend test -- task-autonomy-console.test.tsx`
  - focused tests for task evidence derivation and queue filtering
  - `pnpm --dir frontend typecheck`
  - `pnpm --dir frontend lint`
- Done when:
  - the task autonomy UI remains behavior-compatible while queue, inspector,
    actions, and evidence are independently owned
- Completed notes:
  - `task-autonomy-sections.tsx` is now a compatibility facade over
    `task-autonomy/queue.tsx`, `inspector.tsx`, `actions.tsx`, `evidence.tsx`,
    `format.ts`, and `types.ts`.
  - Queue filtering/summary helpers and evidence-row derivation are covered by
    focused non-rendering tests in addition to the existing console rendering
    coverage.
  - Architecture guardrails now cap the facade and new owned task-autonomy
    modules separately.

### GBX-R311: Extract Verification Cue And Compare Analysis Derivation From Rendering

- Status: `DONE`
- Depends on: `GBX-R300`
- Goal: reduce
  [verification-cues.tsx](../frontend/components/console/verification-cues.tsx)
  and
  [compare-pane.tsx](../frontend/components/console/session-inspector/panes/compare-pane.tsx)
  by moving evidence and comparison analysis into pure helper modules
- Deliverables:
  - pure verification cue derivation for policy, eval coverage, replay drift,
    provider evidence, release evidence, artifact grouping, and path overlap
  - pure session comparison derivation for branch metadata, transcript
    divergence, tool activity, policy outcome, runtime projection facts, and
    string-set comparison
  - rendering components that consume typed analysis results rather than
    recomputing them inline
  - focused unit tests for derivation helpers without React rendering
- Implementation notes:
  - preserve current visual layout and labels unless a later task explicitly
    changes them
  - keep generated API response types as the input boundary
  - keep browser-only state out of pure derivation modules
- Tests and validation included in task:
  - `pnpm --dir frontend test -- verification-cues.test.ts`
  - `pnpm --dir frontend test -- session-inspector.test.ts`
  - focused helper tests for cue and compare derivation
  - `pnpm --dir frontend typecheck`
  - `pnpm --dir frontend lint`
- Done when:
  - verification and compare rendering is thin over pure, covered analysis
    helpers
- Completed notes:
  - Verification cue grouping, policy/eval/replay/provider/release cue
    derivation, artifact classification, and path-overlap logic now live in
    `verification-cues-analysis.ts`.
  - Session comparison summary, branch/runtime/tool/policy facts, transcript
    divergence, and string-set comparison now live in
    `session-inspector/panes/compare-analysis.ts`.
  - Added non-rendering tests for verification analysis and compare derivation,
    while preserving the existing rendering coverage.

### GBX-R312: Extract Workspace Console Routing And Action Binding

- Status: `DONE`
- Depends on: `GBX-R310`, `GBX-R311`
- Goal: reduce
  [workspace-console.tsx](../frontend/components/console/workspace-console.tsx)
  by moving route synchronization, surface selection, store reset/load
  orchestration, and action binding into focused hooks or helpers
- Deliverables:
  - a routing hook that owns URL parsing, popstate handling, route updates, and
    per-surface load/reset behavior
  - action binding helpers for task, knowledge, branch-search, and session
    actions where that reduces repeated inline closures
  - `WorkspaceConsole` reduced to store construction, state selection, and
    surface composition
- Implementation notes:
  - preserve direct session deep links, task routes, memory/repository routes,
    branch routes, compare routes, and back/forward navigation behavior
  - do not hide store factories behind a global singleton
  - keep confirmation prompts at the action boundary, not inside pure routing
    helpers
- Tests and validation included in task:
  - `pnpm --dir frontend test -- app-route.test.ts`
  - `pnpm --dir frontend test -- workspace-overview.test.ts`
  - `pnpm --dir frontend test -- operator-actions.component.test.tsx`
  - `pnpm --dir frontend typecheck`
  - `pnpm --dir frontend lint`
- Done when:
  - workspace-console route orchestration is explicit, testable, and no longer
    interleaved with JSX composition
- Completed notes:
  - Route parsing, popstate synchronization, surface load/reset orchestration,
    navigation, and selected-session refresh now live in
    `workspace-console/routing.ts`.
  - Task, knowledge, branch-search, session-inspector, and overview action
    callbacks now live in `workspace-console/actions.ts`.
  - `workspace-console.tsx` now constructs stores, selects state, and composes
    the active surface.

---

## Phase 62: Web Route And Runtime Query Decomposition

### GBX-R320: Split Session And Task Route Files Into Query, Action, And Serialization Helpers

- Status: `DONE`
- Depends on: `GBX-R300`
- Goal: reduce
  [web/routes/sessions.py](../src/glassbox/web/routes/sessions.py) and
  [web/routes/tasks.py](../src/glassbox/web/routes/tasks.py) by moving HTTP-local
  query composition, mutation action orchestration, pagination, and artifact
  serialization into owned modules
- Deliverables:
  - session route query helpers for aggregate, snapshot, transcript, event log,
    tool calls, metrics, checkpoints, compactions, artifacts, and runtime
    summary reads
  - session route action helpers for messages, answers, cancellation, forks,
    tool-attempt retry/abandon, and compaction refresh/invalidation
  - task route query helpers for task list, task detail, steps, events, and
    background job adjacency
  - task route action helpers for plan approval, continuation, continuation
    windows, pause windows, pause/resume/cancel, and budget adjustment
  - route modules that remain the FastAPI declaration surface and dependency
    boundary
- Implementation notes:
  - keep Pydantic response models in web API modules, not runtime modules
  - keep runtime query services transport-agnostic
  - preserve status codes, validation errors, pagination defaults, and response
    payload shapes
  - do not import concrete store implementations into routes or route helpers
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_web_session_snapshot.py`
  - `uv run pytest tests/integration/test_web_session_pagination.py`
  - `uv run pytest tests/integration/test_web_session_interaction.py`
  - `uv run pytest tests/integration/test_web_task_routes.py`
  - `uv run pytest tests/integration/test_web_approval_resolution.py`
  - `uv run pytest tests/integration/test_openapi_schema.py`
- Done when:
  - route modules are thin HTTP surfaces over owned query/action helpers with no
    payload or behavior drift
- Completed notes:
  - `web/routes/sessions.py` and `web/routes/tasks.py` now remain FastAPI
    declaration surfaces over HTTP-local helper modules.
  - Session aggregate, snapshot, transcript, event-log, tool-call, metrics,
    checkpoint, compaction, artifact, and runtime-summary reads now live in
    `session_route_queries.py`; session mutations live in
    `session_route_actions.py`.
  - Task list/detail/step/event reads now live in `task_route_queries.py`;
    task plan approval, continuation, continuation-window, pause-window,
    pause/resume/cancel, and budget mutations live in `task_route_actions.py`.
  - Shared route pagination response construction lives in `pagination.py`.

### GBX-R321: Split Runtime Task Query Models, Verification, And Repair-History Derivation

- Status: `DONE`
- Depends on: `GBX-R300`
- Goal: reduce
  [task_queries.py](../src/glassbox/runtime/task_queries.py) by separating
  transport-agnostic task query models, summary/detail shaping, verification
  ledger derivation, and repair-history derivation
- Deliverables:
  - task query view models in `runtime/task_query_models.py` or equivalent
  - task summary/detail assembly helpers that stay separate from verification
    evidence rules
  - verification ledger summary, last-known-good, and repeated-failure helpers
    in a focused module
  - repair-history helpers in a focused module
  - `TaskQueryService` kept as the small repository-backed orchestration layer
- Implementation notes:
  - keep the service read-only
  - preserve ordering, pagination, current-step selection, verification
    posture, repair-history wording, and event payload exposure
  - avoid importing web response models or frontend concepts into runtime
    query helpers
- Tests and validation included in task:
  - focused unit coverage for task query verification and repair derivation
  - `uv run pytest tests/integration/test_web_task_routes.py`
  - `uv run pytest tests/integration/test_cli_task_commands.py`
  - `uv run pytest tests/integration/test_background_autonomy_smoke.py`
  - `uv run ty check src/glassbox/runtime/task_queries.py`
- Done when:
  - task query behavior remains stable while verification and repair-history
    decisions are independently testable
- Completed notes:
  - `runtime/task_queries.py` now keeps `TaskQueryService` as the small
    repository-backed read facade and compatibility import surface.
  - Transport-agnostic task query view models and the repository protocol now
    live in `task_query_models.py`.
  - Record-to-view assembly lives in `task_query_assembly.py`; verification
    ledger and last-known-good evidence derivation live in
    `task_query_verification.py`; repair-history status and retry-edge
    derivation live in `task_query_repair.py`.
  - Added focused unit coverage for last-known-good evidence, repaired retry
    edges, and repeated failure signature counting.

### GBX-R322: Split Session API Response Models By Surface

- Status: `DONE`
- Depends on: `GBX-R320`
- Goal: reduce [session_api.py](../src/glassbox/web/session_api.py) by grouping
  response models and builders by selected-session snapshot, session aggregate,
  detail pages, actions, artifacts, and diagnostics
- Deliverables:
  - response model modules grouped by API surface where practical
  - builder functions colocated with the response model families they construct
  - compatibility exports from `session_api.py` if existing route imports need
    a stable transition path
  - unchanged generated OpenAPI schema except for ordering differences accepted
    by existing schema tests
- Implementation notes:
  - do not move runtime query models into web API modules
  - preserve response field names, optionality, aliases, and examples
  - avoid over-splitting tiny model groups that are usually reviewed together
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_openapi_schema.py`
  - `uv run pytest tests/integration/test_web_session_snapshot.py`
  - `pnpm --dir frontend run api:generate`
  - `pnpm --dir frontend test -- generated-api-types.test.ts`
- Done when:
  - session API response models are easier to navigate without changing the
    contract consumed by the frontend
- Completed notes:
  - `session_api.py` now remains a compatibility facade that re-exports the
    stable response models and builder functions used by routes and tests.
  - Shared detail-page and diagnostic models live in `session_api_common.py`;
    action request/response models live in `session_api_actions.py`;
    selected-session snapshot and summary models live in
    `session_api_snapshot.py`; operator aggregate models live in
    `session_api_aggregate.py`; serializers live in `session_api_builders.py`.
  - Regenerated API artifacts were unchanged, preserving the frontend OpenAPI
    contract.

---

## Phase 63: Provider And Tool-Policy Decomposition

### GBX-R330: Split Provider Canary Execution From Evidence Loading And Freshness

- Status: `DONE`
- Depends on: `GBX-R300`
- Goal: reduce
  [provider_canary.py](../src/glassbox/runtime/provider_canary.py) by separating
  scenario definitions, canary execution, evidence loading, freshness checks,
  summary writing, and evidence status derivation
- Deliverables:
  - scenario definitions and selection helpers in a provider-canary scenarios
    module
  - live canary execution in an execution module
  - evidence path discovery, loading, legacy/invalid fallback, and freshness
    checks in a read-model module
  - summary writing and outcome counting in a persistence/report helper module
  - stable public functions for CLI and observability callers
- Implementation notes:
  - preserve canary JSON payload shape, skip reasons, freshness thresholds,
    selected-scenario behavior, and provider identity matching
  - keep live-provider execution opt-in and separate from deterministic eval
    surfaces
  - do not let observability formatting leak into canary execution modules
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_runtime_provider_config.py`
  - focused provider canary evidence/freshness tests
  - `uv run pytest tests/integration/test_provider_mode_runtime.py`
  - `uv run pytest tests/integration/test_observability_status.py`
- Done when:
  - provider canary execution and provider evidence reads can evolve without
    sharing one broad module body
- Completed notes:
  - `runtime/provider_canary.py` now stays a stable compatibility facade for
    CLI, observability, and provider recommendation callers.
  - Retained canary models/constants live in `provider_canary_models.py`;
    scenario selection/metadata lives in `provider_canary_scenarios.py`; live
    opt-in execution lives in `provider_canary_execution.py`; retained evidence
    loading, legacy fallback, identity checks, and freshness derivation live in
    `provider_canary_evidence.py`; summary persistence and outcome counting
    live in `provider_canary_reporting.py`.
  - V10 architecture guardrails now cap the facade and helper modules
    separately and keep provider-canary helpers away from CLI, raw-store, and
    web-layer imports.

### GBX-R331: Split Provider Recommendation Scoring Into Capability, Risk, Credential, And Action Modules

- Status: `DONE`
- Depends on: `GBX-R330`
- Goal: reduce
  [provider_recommendations.py](../src/glassbox/runtime/provider_recommendations.py)
  by extracting the independent scoring dimensions behind provider selection
- Deliverables:
  - shared recommendation models kept stable or moved behind a model module
  - capability-fit helpers for task kinds and workflow scenarios
  - risk-posture helpers for provider/task fit and fallback behavior
  - credential-readiness helpers for config and diagnostic evidence
  - failure-posture and budget-impact helpers
  - action-selection and next-step guidance helpers
- Implementation notes:
  - preserve current recommendation output fields, confidence taxonomy,
    unknowns, and next-step wording where tests rely on them
  - keep diagnostics and canary evidence as inputs, not hidden global reads
  - avoid creating a scoring framework larger than the current problem
- Tests and validation included in task:
  - focused unit coverage for each scoring dimension
  - `uv run pytest tests/unit/test_runtime_provider_config.py`
  - `uv run pytest tests/integration/test_provider_mode_runtime.py`
  - `uv run ty check src/glassbox/runtime/provider_recommendations.py`
- Done when:
  - provider recommendation behavior remains stable while each scoring
    dimension is owned and testable
- Completed notes:
  - `runtime/provider_recommendations.py` now stays the stable public
    recommendation facade and orchestration point.
  - Recommendation contracts live in `provider_recommendation_models.py`;
    workflow scenario selection, retained canary summary loading, relevant
    evidence derivation, required capabilities, and capability fit live in
    `provider_recommendation_capability.py`.
  - Risk posture, posture/confidence, reasons, warnings, and unknowns live in
    `provider_recommendation_risk.py`; credential readiness lives in
    `provider_recommendation_credentials.py`; recovery failure posture and
    budget impact live in `provider_recommendation_failures.py`; action
    selection and next-step guidance live in `provider_recommendation_actions.py`.
  - V10 guardrails now cap the provider recommendation facade and scoring
    helper modules separately and keep the scoring helpers away from CLI,
    raw-store, and web-layer imports.

### GBX-R332: Split Tool Policy Into Path, Rule, Autonomy, Message, And Command-Risk Modules

- Status: `TODO`
- Depends on: `GBX-R300`
- Goal: reduce [tools/policy.py](../src/glassbox/tools/policy.py) by separating
  path-scope evaluation, policy rule matching, autonomy-budget behavior,
  approval message construction, and command-risk classification
- Deliverables:
  - path normalization, workspace containment, extension matching, and path
    argument extraction helpers in a path-policy module
  - policy manifest rule matching and outcome resolution in a rule module
  - autonomy budget/risk permit logic in an autonomy-policy module
  - default and autonomy approval message construction in a message module
  - destructive-command and command-text heuristics in a command-risk module
  - stable `ToolPolicyEngine` public behavior
- Implementation notes:
  - preserve current approval decisions, trace payloads, reason strings, command
    risk behavior, and autonomy-budget semantics unless a later task explicitly
    changes them
  - keep `ToolPolicyContext` and public policy engine ergonomics stable
  - add characterization coverage before moving subtle rule matching behavior
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_tools_policy.py`
  - `uv run pytest tests/integration/test_approval_workflow.py`
  - `uv run pytest tests/integration/test_command_tool.py`
  - `uv run pytest tests/integration/test_workflow_tools.py`
  - `uv run ty check src/glassbox/tools/policy.py`
- Done when:
  - tool-policy decisions remain behavior-compatible while path, rule,
    autonomy, message, and command-risk concerns are independently owned

---

## Phase 64: Store Schema And Core-Domain Boundary Planning

### GBX-R340: Split SQLite Schema Migrations By Projection Domain

- Status: `TODO`
- Depends on: `GBX-R300`
- Goal: reduce [sqlite_schema.py](../src/glassbox/store/sqlite_schema.py) by
  moving domain-specific table shape and migration helpers into schema modules
  owned by projection family
- Deliverables:
  - baseline schema and migration runner kept in `sqlite_schema.py`
  - task, verification-ledger, checkpoint, compaction, tool-attempt,
    background-job, branch-search, workspace-memory, provider-recovery, and
    long-run schema helpers grouped by domain
  - migration registry that remains explicit and ordered
  - stable `SCHEMA_VERSION`, `MIGRATIONS`, `BOOTSTRAP_STATEMENTS`,
    `open_database`, and `initialize_database` public imports
- Implementation notes:
  - preserve fresh-database bootstrap behavior and older-workspace migration
    behavior exactly
  - keep migrations idempotent and explicit
  - do not change table names, column names, indexes, or schema version as part
    of pure movement unless a later task explicitly requires it
  - avoid hiding migration order in dynamic discovery
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_sqlite_bootstrap.py`
  - `uv run pytest tests/integration/test_sqlite_event_store.py`
  - `uv run pytest tests/integration/test_sqlite_projections.py`
  - `uv run pytest tests/integration/test_projection_rebuild.py`
  - `uv run pytest tests/unit/test_sqlite_query_boundaries.py`
- Done when:
  - schema bootstrap and migration behavior is unchanged while domain-specific
    projection schema code is easier to review

### GBX-R341: Define Core Event And Model Domain Module Strategy

- Status: `TODO`
- Depends on: `GBX-R300`
- Goal: plan the next safe split for [core/events.py](../src/glassbox/core/events.py)
  and [core/models.py](../src/glassbox/core/models.py) before another major
  event-domain expansion lands
- Deliverables:
  - documented strategy for optional domain modules such as sessions, turns,
    tools, tasks, branch search, background jobs, workspace memory, repository
    index, provider recovery, verification, and compaction
  - compatibility plan for keeping `glassbox.core.events` and
    `glassbox.core.models` as stable public import surfaces
  - explicit discriminated-union registration strategy for event payloads
  - guidance on when not to split model-heavy code
  - no broad event/model code movement unless this task explicitly expands into
    implementation after design review
- Implementation notes:
  - treat core event/model modules as high fan-in infrastructure
  - avoid destabilizing imports for cosmetic file-size reasons
  - any future implementation should be incremental and heavily covered by
    import-smoke, event serialization, projection, replay, and API tests
- Tests and validation included in task:
  - doc review against current core imports and event payload registration
  - optional lightweight guardrail updates if a strategy can be enforced without
    freezing implementation details prematurely
- Done when:
  - the repository has a clear strategy for future core domain splits and can
    avoid ad hoc growth in the next feature cycle

---

## Phase 65: Documentation And Validation Closeout

### GBX-R350: Update Architecture Docs For The V10 Refactor Shape

- Status: `TODO`
- Depends on: `GBX-R310`, `GBX-R311`, `GBX-R312`, `GBX-R320`, `GBX-R321`,
  `GBX-R322`, `GBX-R330`, `GBX-R331`, `GBX-R332`, `GBX-R340`, `GBX-R341`
- Goal: align architecture and boundary docs with the final v10 refactor module
  shape
- Deliverables:
  - updates to [architecture.md](./architecture.md) where route, runtime query,
    provider, tool-policy, store schema, or dashboard ownership changed
    materially
  - updates to [database.md](./database.md) if schema ownership or migration
    descriptions changed
  - updates to [refactor-boundaries.md](./refactor-boundaries.md) marking the
    v10 boundary map as implemented
  - updates to this roadmap with completed notes for each finished task
  - docs hub updates only if the new boundaries should be discoverable from the
    public docs index
- Implementation notes:
  - document architectural ownership and dependency direction, not just file
    moves
  - avoid claiming new product behavior from refactor-only work
  - keep historical v1 and v8 notes intact unless they have become misleading
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_release_candidate_docs.py`
  - doc review against final module layout
- Done when:
  - docs and code describe the same v10 refactor shape and remaining
    compatibility shims are either justified or tracked

### GBX-R351: Close Out V10 Refactor Guardrails And Focused Validation

- Status: `TODO`
- Depends on: `GBX-R350`
- Goal: add final characterization and validation coverage proving the v10
  refactor preserved behavior across frontend, web, runtime, provider, policy,
  and store seams
- Deliverables:
  - final guardrail coverage for new v10 facades and domain boundaries
  - characterization tests for the highest-risk moved behavior where not already
    covered
  - documented validation command set for future second-order refactor tasks
  - explicit list of accepted compatibility shims and intended owners for new
    behavior
- Implementation notes:
  - prefer narrow guardrails that catch real coupling regressions
  - do not freeze low-risk internal helper names
  - keep compatibility shims only when they serve a real public import, route,
    command, or component contract
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_architecture_guardrails.py`
  - focused backend and frontend tests for all refactored seams
  - final baseline validation as practical for the touched repository state
  - `pnpm --dir frontend typecheck`
  - `pnpm --dir frontend lint`
  - `pnpm --dir frontend test`
- Done when:
  - the v10 refactor roadmap can be marked complete with guardrails that protect
    the new module shape from immediate regression
