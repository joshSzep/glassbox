# Glassbox v8 Tasks

For the docs hub and operator guides, start at [README.md](./README.md). This file is the v8 task graph for evolving the v7 release-candidate product from a careful local agent harness into a more agentic local engineering runtime with auditable autonomy.

## Purpose

This document defines Glassbox v8: the auditable-autonomy evolution after the v7 adoption-and-scale milestone in [tasks-v7.md](./tasks-v7.md).

It is written in the same execution style as [tasks-v1.md](./tasks-v1.md), [tasks-v2.md](./tasks-v2.md), [tasks-v3.md](./tasks-v3.md), [tasks-v4.md](./tasks-v4.md), [tasks-v5.md](./tasks-v5.md), [tasks-v6.md](./tasks-v6.md), and [tasks-v7.md](./tasks-v7.md): explicit dependencies, small vertical slices, concrete deliverables, and quality requirements attached directly to the work.

The v2 through v7 work established the durable local runtime, SQLite event store, daemon ownership model, static-exported dashboard, full-screen terminal client, real cancellation, resilient live transport, repository-owned replay and eval contracts, provider diagnostics, advisory canaries, larger-session read paths, policy evidence, and release gates. That foundation is now strong enough that v8 should make the product less conservative without abandoning the reason Glassbox exists: local-first, event-sourced, operator-visible agent work.

The v8 goal is to promote autonomy from an implicit behavior inside one model turn into explicit runtime state. Glassbox should be able to plan work, execute bounded steps, verify results, remember durable local facts, explore alternate branches, and continue in the background when policy allows. Every one of those capabilities should remain inspectable, interruptible, replay-aware, and bounded by local policy.

## Product Direction

The v8 work should optimize for ten outcomes:

- first-class task plans and step execution as durable runtime objects rather than hidden prompt text
- autonomy modes with explicit policy budgets for tool use, writes, commands, verification, runtime, and escalation
- a proactive local daemon worker that can continue opt-in work, maintain derived local intelligence, and stop cleanly when blocked
- inspectable workspace memory that records durable local facts with provenance, freshness, and usage evidence
- a local repository intelligence index for symbols, ownership, commands, tests, docs, and recently active areas
- self-verification loops that can run relevant tests or evals, repair failures, and stop when the configured budget is exhausted
- branch-search workflows that can try multiple local strategies and compare outcomes before an operator chooses a path
- deeper provider capability evidence that helps choose models for workflows without turning live providers into release authority
- a dashboard autonomy console for plans, budgets, task queues, branch comparisons, memory, and why-this-action evidence
- v8 release evidence that proves autonomy is bounded, recoverable, auditable, and useful rather than merely more permissive

The v8 thesis is:

- preserve local-first operation and workspace-owned state
- preserve canonical events as the source of truth
- preserve one mutation owner per workspace unless a future task explicitly defines a stronger local arbitration model
- preserve deterministic replay and eval as release authority
- make autonomy visible, bounded, and configurable instead of hiding it in prompts or process-local state
- let safe local work proceed further before interrupting the operator
- treat background work, memory, and indexing as explicit local runtime products with provenance and cleanup paths
- avoid hosted control planes, remote multi-user orchestration, cloud ownership authority, plugin marketplaces, and opaque provider-side memory in this milestone

## Current Baseline Before V8 Execution

Treat the following as the starting point for every task in this document:

- [v7-release-candidate.md](./v7-release-candidate.md) records a GO decision for the v7 release candidate
- `glassbox session chat` launches the full-screen Textual TUI by default in supported terminals and keeps `--plain` as the explicit compatibility path
- the dashboard is a Next.js static export served by FastAPI and packaged into the Python distribution
- terminal and dashboard clients consume backend snapshots plus `/sessions/{session_id}/events` SSE tails with sequence-based reconnect semantics
- `glassbox daemon start|status|stop` provides workspace-scoped runtime ownership and `session attach` can reconnect to daemon-owned sessions
- cancellation is persisted as event evidence and replay/eval normalize intentional cancellation distinctly from generic failure
- the SQLite store uses canonical events plus rebuildable projections and schema migrations
- replay and eval support repository-owned cases, profiles, coverage audits, impact recommendations, baseline promotion and refresh, and release-signoff reports
- advisory provider diagnostics and canaries exist, with deterministic replay/eval remaining the release authority
- dashboard session reads support pagination, comparison, metrics, runtime context, policy evidence, verification cues, and larger-session inspection affordances
- runtime context already includes bounded repository context, event-backed runtime notes, working-set summaries, and artifact-backed context with replay fingerprints
- tool policy already separates hard invariants, registry risk buckets, workspace policy rules, and session approval mode translation
- v7 release evidence includes deterministic eval expansion, provider capability matrix rows, larger-session scale checks, daemon/live transport reliability checks, dashboard evidence refinement, onboarding, package smoke, and accessibility pairings

## v8 Auditable Autonomy Findings

Treat these findings as evidence that should steer the first implementation slices:

- the runtime is event-sourced and replayable, but autonomous planning is still only implicit in model text and tool calls
- the daemon is a reliable local owner, but it does not yet behave as a proactive local worker
- runtime notes and working-set context are useful, but they are session-scoped and do not yet form a durable workspace memory layer
- repository context is intentionally bounded and shallow; richer repo intelligence still requires repeated ad hoc tool inspection
- approval modes are persisted and surfaced, but the current practical behavior remains too coarse for calibrated autonomy
- eval recommendation explains what to run, but it does not yet power a budgeted verify-repair loop
- branching is strong for historical exploration, but it is not yet used as a strategy-search primitive
- the dashboard is an inspection console, but not yet a control room for plans, budgets, task queues, and autonomous progress
- provider canaries explain some live-provider behavior, but model choice remains mostly manual and provider scenario depth is still narrow
- the release process is mature enough to add autonomy gates that prove boundedness, recoverability, and auditability instead of simply blocking capability expansion

## Agent Execution Rules

These rules apply to every task in this file.

1. Respect dependency order. Do not start a task until its dependencies are complete unless the task explicitly says it can proceed in parallel.
2. Preserve the event-sourced source-of-truth rule. Plans, task steps, background jobs, memory entries, repository index summaries, branch-search attempts, verification loops, and autonomy-budget decisions must be recorded in canonical events or explicitly rebuildable derived state.
3. Preserve local-first operation. Do not introduce a hosted control plane, remote multi-user authority, remote worker fleet, or external service dependency for v8 readiness.
4. Preserve deterministic release blocking. Live-provider canaries stay advisory unless a task explicitly promotes a scenario with stable credentials, repeatability, and failure policy.
5. Keep terminal and dashboard roles coherent. The TUI remains the primary conversational surface; the dashboard becomes the richer autonomy console and evidence surface.
6. Treat autonomy as an inspectable runtime mode, not as a prompt-only convention. If the model can act further without asking, the operator should be able to see why.
7. Prefer explicit budgets over broad permission toggles. Budget fields should be typed, persisted, surfaced, and checked before additional tool use, writes, commands, verification, branch attempts, or background continuation.
8. Keep background work interruptible. Daemon jobs must have cancellation, pause, retry, stale-owner, recovery, and observability paths before they become release-critical.
9. Keep memory and indexing provenance visible. No memory item, code-intelligence summary, or retrieval result should materially affect prompts without a source, freshness posture, and replay/eval story.
10. Keep non-interactive commands scriptable. Task, memory, index, autonomy, replay, eval, provider, projection, backup, daemon, release, and package workflows should remain useful in CI or clean shell environments.
11. If v8 work exposes an API mismatch, fix or document the backend service/API contract before encoding terminal-only or browser-only workarounds.
12. Every implementation task automatically includes:
    - automated tests for new behavior
    - `ruff` formatting and lint compliance for touched Python code
    - `ty` typecheck compliance for touched Python code
    - focused `pytest` coverage for touched runtime, CLI, web, replay, eval, daemon, transport, policy, memory, index, task, and terminal behavior
    - frontend lint, typecheck, tests, and build when the task touches dashboard code, generated API types, or packaged static assets
    - documentation updates when contracts, routes, commands, packaging, provider workflows, release gates, accessibility claims, policy behavior, memory behavior, task behavior, or operator-visible behavior change

## Completion Contract For Any Task

A task is complete only when all of the following are true:

- the implementation exists in the intended module boundary
- automated tests covering the new behavior exist and pass
- Python lint, typecheck, and focused tests pass for touched backend and CLI code
- frontend lint, typecheck, tests, and build pass if the task touches frontend, generated API types, or web dashboard behavior
- deterministic replay/eval behavior remains stable or intentional drift is documented through the eval refresh workflow
- new eval, provider-canary, policy, memory, index, task, autonomy, or release evidence is retained in the documented local path when the task creates such evidence
- new autonomous behavior is bounded by typed policy or budget state rather than hidden prompt convention
- pause, cancellation, retry, and recovery behavior is covered for any new long-running background or autonomous workflow
- the task does not leave placeholder code or hidden follow-up work outside this file
- terminal behavior remains usable in supported TTY and documented fallback contexts
- the dashboard remains usable through the FastAPI-served production build path
- docs are updated if the task changes the operator-visible product, verification posture, release posture, autonomy posture, memory posture, or public claims

## Suggested Status Markers

If an agent updates this document later, use one of these markers next to task IDs:

- `TODO`
- `IN_PROGRESS`
- `BLOCKED`
- `DONE`

## Expected Repository Targets

These are the main implementation areas referenced below:

```text
pyproject.toml
scripts/
src/glassbox/
    cli/
    core/
    runtime/
    tools/
    store/
    web/
frontend/
    api/
    app/
    components/
    generated/
    routing/
    state/
    stores/
    tests/
    e2e/
tests/
    integration/
    unit/
evals/
    bundles/
    cases/
    coverage.json
    impact.json
    profiles.json
docs/
```

New v8 implementation areas should prefer focused modules rather than widening existing facades. Expected new or expanded surfaces may include:

```text
src/glassbox/runtime/tasks.py
src/glassbox/runtime/task_plans.py
src/glassbox/runtime/autonomy.py
src/glassbox/runtime/background_jobs.py
src/glassbox/runtime/workspace_memory.py
src/glassbox/runtime/repository_index.py
src/glassbox/runtime/verification_loops.py
src/glassbox/runtime/branch_search.py
src/glassbox/store/sqlite_projection_tasks.py
src/glassbox/store/sqlite_projection_memory.py
src/glassbox/store/sqlite_projection_repository_index.py
src/glassbox/web/routes/tasks.py
src/glassbox/web/routes/memory.py
src/glassbox/web/routes/repository_index.py
frontend/components/console/task-console/
frontend/components/console/memory-inspector/
frontend/components/console/repository-index/
```

The exact file names may change during implementation, but the ownership boundaries should remain explicit.

## Recommended Validation Commands

Use the narrowest viable validation after each task, but the baseline validation pattern for completed v8 work should include:

```bash
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run pytest
uv run glassbox eval run
uv run glassbox eval audit
uv run glassbox eval report commit-smoke push-confirmation release-candidate --output-dir .glassbox/evals/v8-release-signoff
pnpm --dir frontend lint
pnpm --dir frontend typecheck
pnpm --dir frontend test
pnpm --dir frontend build
uv build --wheel --sdist
uv run python scripts/validate_v7_release_gate.py
```

During incremental implementation, use narrower commands where possible:

```bash
uv run pytest tests/unit/test_core_events.py tests/integration/test_sqlite_event_store.py
uv run pytest tests/unit/test_runtime_task_plans.py tests/integration/test_task_runtime.py
uv run pytest tests/unit/test_runtime_autonomy.py tests/integration/test_autonomy_budget.py
uv run pytest tests/integration/test_daemon_runtime.py tests/unit/test_runtime_transport.py
uv run pytest tests/unit/test_workspace_memory.py tests/integration/test_workspace_memory.py
uv run pytest tests/unit/test_repository_index.py tests/integration/test_repository_index.py
uv run pytest tests/unit/test_verification_loops.py tests/integration/test_verification_loops.py
uv run pytest tests/unit/test_branch_search.py tests/integration/test_branch_search.py
uv run pytest tests/unit/test_tools_policy.py tests/integration/test_command_tool.py
uv run pytest tests/integration/test_web_session_snapshot.py tests/integration/test_web_session_aggregate.py
uv run pytest tests/integration/test_web_tasks.py tests/integration/test_web_memory.py
pnpm --dir frontend test -- dashboard-stores session-inspector sse-client task-console memory-inspector
pnpm --dir frontend test:e2e -- operator-workflows autonomy-workflows
uv run ruff check src/glassbox tests scripts
uv run ty check
```

When a task touches generated frontend API types, packaged dashboard assets, provider canaries, evals, or release gates, also run the relevant smoke or dry-run command:

```bash
pnpm --dir frontend api:generate
pnpm --dir frontend build
uv run glassbox provider diagnostics --cwd . --json
uv run glassbox provider canary run --cwd . --output-dir .glassbox/provider-canary/v8 --json
uv run glassbox eval recommend src/glassbox/runtime/autonomy.py --cwd .
uv run python scripts/validate_package_contents.py
uv run python scripts/validate_v7_release_gate.py --dry-run --evidence-dir .glassbox/releases/v8-gate-dry-run
```

Once `GBX-893` exists, use the v8 gate as the canonical full validation command:

```bash
uv run python scripts/validate_v8_release_gate.py
```

## Milestone Map

The intended v8 milestone order is:

1. v8 auditable-autonomy contract and baseline inventory
2. task-plan event model and runtime query surface
3. autonomy modes, policy budgets, and calibrated approvals
4. proactive daemon worker and background job execution
5. workspace memory and repository intelligence
6. self-verification loops and branch-search workflows
7. tool expansion and provider capability depth
8. dashboard autonomy console
9. v8 eval, release gate, packaging, manual evidence, and release-candidate signoff

## Task Graph

---

## Phase 81: v8 Contract And Baseline Inventory

### GBX-810: Define The v8 Auditable-Autonomy Contract

- Status: `TODO`
- Depends on: `GBX-785`
- Goal: convert the v7 release-candidate decision and post-v7 autonomy direction into one concrete v8 product contract
- Deliverables:
  - documentation update defining v8 scope, non-goals, supported workflow set, autonomy posture, evidence expectations, and release posture
  - explicit mapping from v7 residual risks and post-v7 follow-up backlog into v8 tasks or accepted non-goals
  - explicit rule that v8 does not introduce hosted collaboration, remote ownership authority, cloud workers, browser-native code editing, plugin marketplaces, or opaque provider-side memory
  - definition of auditable autonomy: plan state, budget state, memory state, background work, branch attempts, and verification loops are inspectable and locally bounded
  - release-readiness checklist that names deterministic eval, autonomy budgets, daemon jobs, memory/index provenance, branch search, dashboard control, provider-canary, accessibility, onboarding, packaging, and manual evidence separately
  - risk register shape for accepted v8 residual risks
- Implementation notes:
  - start from [v7-release-candidate.md](./v7-release-candidate.md), [v7-release-gate.md](./v7-release-gate.md), [runtime-context.md](./runtime-context.md), [tool-policy.md](./tool-policy.md), [persistent-runtime.md](./persistent-runtime.md), and this task file
  - keep the contract operator-readable rather than turning it into internal engineering notes only
  - use the phrase `auditable autonomy` for the product posture, not `unrestricted autonomy`
  - make local-first and event-sourced boundaries feel enabling rather than apologetic
- Tests and validation included in task:
  - docs review against implemented command help, v7 release docs, and current release scripts
  - lightweight docs test if a new v8 contract document is added
- Done when:
  - contributors have one code-aligned v8 contract that explains how Glassbox can become more agentic without hiding state or outsourcing authority

### GBX-811: Inventory Agentic Surfaces, Conservative Gates, And Autonomy Gaps

- Status: `TODO`
- Depends on: `GBX-810`
- Goal: establish a code-aligned baseline of current plan-like behavior, daemon capabilities, policy gates, memory/context sources, branch workflows, eval recommendation, dashboard actions, and provider capability depth
- Deliverables:
  - inventory of current turn execution flow, suspension points, approval gates, command gates, cancellation behavior, and policy evidence
  - inventory of daemon ownership, attach behavior, observer support, and potential background-worker seams
  - inventory of runtime notes, working-set context, artifact-backed context, replay fingerprints, and current memory limitations
  - inventory of repository context and code-inspection tools, including what must be re-read every turn today
  - inventory of branching, fork comparison, eval recommendation, eval report, replay drift, and verification flows
  - inventory of dashboard control surfaces and missing autonomy-console affordances
  - inventory of provider diagnostics and canary scenarios that could inform model/workflow selection
  - explicit list of conservative bottlenecks and safe loosening opportunities
- Implementation notes:
  - distinguish hard safety boundaries from product conservatism that can be relaxed through budgets
  - name which gaps need canonical events, which need projections, which need CLI/API surfaces, and which are dashboard-only presentation gaps
  - do not implement new autonomy in this task; this is the audit that feeds later slices
- Tests and validation included in task:
  - docs review against `src/glassbox/runtime/`, `src/glassbox/tools/`, `src/glassbox/web/routes/`, `frontend/components/console/`, `evals/`, and command help
- Done when:
  - v8 implementers know exactly where the system is conservative, which conservative choices remain hard boundaries, and which can be evolved through auditable autonomy

### GBX-812: Update Documentation Discovery For v8

- Status: `TODO`
- Depends on: `GBX-810`, `GBX-811`
- Goal: make the v8 plan, contract, inventory, and later evidence docs discoverable from the documentation hub without requiring users to know the task file name
- Deliverables:
  - docs hub update linking this task graph and any v8 contract or inventory docs
  - root README update only if the public supported operating model changes
  - guide-map additions for v8 task plans, autonomy modes, background jobs, memory, repository intelligence, branch search, dashboard console, provider selection, or release evidence docs as they land
  - docs tests if existing release-candidate documentation guardrails are extended
- Implementation notes:
  - keep task docs separate from operator guides
  - do not overpromise v8 outcomes before implementation tasks are complete
  - make the v8 discovery path clear for both operators and contributors
- Tests and validation included in task:
  - docs link review
  - existing docs tests if present
- Done when:
  - a contributor can discover the v8 plan and autonomy evidence expectations from the docs index

---

## Phase 82: Task-Plan Event Model And Runtime Query Surface

### GBX-820: Define Durable Task, Plan, And Step Event Models

- Status: `TODO`
- Depends on: `GBX-811`
- Goal: make autonomous work a first-class event-sourced runtime object instead of implicit prose inside a model response
- Deliverables:
  - core event payloads for task creation, plan proposal, plan revision, step start, step completion, step failure, step skip, verification start, verification completion, pause, resume, cancellation, and abandonment
  - typed domain models for task IDs, step IDs, plan status, step status, verification status, and blocked reasons
  - event-versioning notes for forward-compatible plan and step payloads
  - tests for event serialization, validation, and stable JSON payload shape
  - architecture docs explaining how task plans differ from turns, sessions, eval cases, and dashboard-only state
- Implementation notes:
  - keep task state separate from transcript text; a model may propose a plan, but the runtime owns the durable plan object
  - task events should reference session ID and optional turn ID when they arise from a live conversation
  - task steps should be small enough to map to one or more explicit runtime actions, not vague multi-hour goals
  - avoid adding a second event log; task events belong in the canonical event stream
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_core_events.py tests/unit/test_core_models.py`
  - focused new task-model tests
- Done when:
  - Glassbox can persist and validate task-plan event payloads without changing turn execution behavior yet

### GBX-821: Add Task Projections, Repository Queries, And Rebuild Semantics

- Status: `TODO`
- Depends on: `GBX-820`
- Goal: make task plans queryable and rebuildable from canonical events
- Deliverables:
  - SQLite projection tables for tasks, task steps, task verification runs, and task budget summary fields where needed
  - projection application logic for every task-plan event from GBX-820
  - repository contract methods for listing tasks, reading one task, reading steps, reading open blocked tasks, and rebuilding task projections
  - projection health support for task projection lag or corruption
  - migration and schema tests for fresh and upgraded workspaces
- Implementation notes:
  - projections are derived state and must remain rebuildable from events
  - preserve existing session projection behavior and avoid coupling task rebuilds to dashboard-only needs
  - prefer small projection rows over storing full nested plan JSON as the only query path
  - include indexes for session, task status, updated time, blocked status, and step order
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_sqlite_bootstrap.py tests/integration/test_sqlite_projections.py tests/integration/test_projection_rebuild.py`
  - focused new task projection tests
- Done when:
  - task plan state can be rebuilt deterministically from canonical events and queried without replaying full sessions for every dashboard view

### GBX-822: Add Task Query Service And CLI Inspection Commands

- Status: `TODO`
- Depends on: `GBX-821`
- Goal: give operators and scripts a read-only way to inspect durable task state before any autonomous execution is introduced
- Deliverables:
  - runtime query models for task summary, task detail, step detail, verification detail, blocked reason, next action, and lineage back to session/turn events
  - CLI commands such as `glassbox task list`, `glassbox task show TASK_ID`, and `glassbox task events TASK_ID`
  - human-readable and JSON output for task summaries and details
  - docs for task inspection commands and expected status meanings
  - tests for CLI output, JSON shape, unknown task IDs, empty task lists, and projection-stale messaging
- Implementation notes:
  - keep this task read-only; mutation commands arrive later
  - reuse runtime query patterns from session summaries rather than making CLI command modules query raw SQLite helpers
  - ensure historical task state remains inspectable after session completion, failure, cancellation, export, import, and projection rebuild
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_architecture_guardrails.py`
  - focused CLI task query tests
- Done when:
  - task-plan state is visible from the terminal in the same spirit as session status and eval reports

### GBX-823: Add Task HTTP APIs And Generated Frontend Types

- Status: `TODO`
- Depends on: `GBX-822`
- Goal: expose durable task state through typed web APIs without making the dashboard derive task meaning from raw event streams
- Deliverables:
  - backend routes for task list, task detail, task step list, and task event-log reads
  - response models that wrap runtime query models without duplicating business logic in route handlers
  - OpenAPI schema updates and generated frontend type updates
  - frontend API client methods for task reads
  - web tests for pagination, ordering, unknown IDs, stale projections, and empty lists
- Implementation notes:
  - keep route modules focused on HTTP validation and error mapping
  - include pagination for task events and step lists from the start
  - do not add dashboard mutation controls yet
  - preserve static dashboard serving and existing session links
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_openapi_schema.py`
  - focused task route tests
  - `pnpm --dir frontend api:generate`
  - `pnpm --dir frontend typecheck`
- Done when:
  - the dashboard can load task-plan state through typed APIs, even before rendering it richly

### GBX-824: Capture Plan Proposals From Model Output Without Executing Them Autonomously

- Status: `TODO`
- Depends on: `GBX-823`
- Goal: let the runtime persist structured plans proposed during a turn while keeping execution manual until autonomy budgets exist
- Deliverables:
  - prompt and adapter contract for the model to propose a bounded plan when useful
  - parser or structured-output path for converting a model plan proposal into task-plan events
  - supervisor or turn-engine seam for recording plan proposals after assistant output without auto-running steps
  - CLI and dashboard inspection of proposed plans as read-only task state
  - replay capture and eval expectations for plan proposal events
- Implementation notes:
  - avoid brittle parsing of arbitrary prose if pydantic-ai can provide a structured output or tool-like plan emission path
  - do not execute proposed steps in this task
  - if a plan cannot be parsed safely, record normal assistant text and skip task creation rather than inventing a plan
  - plans should be useful but concise; keep step count bounded
- Tests and validation included in task:
  - model adapter or prompt tests for plan proposal shape
  - turn-engine tests for recording plan events
  - replay tests if event capture changes
- Done when:
  - Glassbox can persist and inspect a proposed plan as durable state without yet granting the agent more autonomy

### GBX-825: Add Task Export, Import, And Replay Bundle Awareness

- Status: `TODO`
- Depends on: `GBX-824`
- Goal: preserve task-plan context across handoff, import, replay, and eval workflows
- Deliverables:
  - session export fields for task summaries, step summaries, blocked reasons, verification summaries, and task-event references
  - import behavior for task-related historical events that keeps imported sessions inspection-only unless a later task explicitly resumes them
  - replay bundle metadata for task-plan events and plan proposal context
  - replay comparison behavior that reports task-plan drift distinctly from transcript-only drift
  - docs update for task-aware handoff and replay behavior
- Implementation notes:
  - exported task content must be redacted using the same secret-safety posture as session export
  - imported task state should not silently become live mutable autonomous work
  - keep older bundles compatible when task metadata is absent
- Tests and validation included in task:
  - session export/import tests
  - replay bundle inspect/run tests
  - eval drift classification tests if taxonomy changes
- Done when:
  - task-plan state is portable and replay-aware rather than tied only to one local SQLite database

---

## Phase 83: Autonomy Modes, Policy Budgets, And Calibrated Approvals

### GBX-830: Define Autonomy Mode And Budget Contract

- Status: `TODO`
- Depends on: `GBX-820`, `GBX-811`
- Goal: replace broad approval-mode conservatism with typed autonomy modes and explicit local budgets
- Deliverables:
  - docs and typed models for autonomy modes such as `manual`, `guided`, `inspect`, `edit-safe`, `test-driven`, `autonomous-local`, and `release-candidate`
  - budget fields for max steps, max tool calls, max write operations, max command operations, max wall-clock duration, max verification attempts, max branch attempts, max artifact bytes, and allowed risk buckets
  - escalation reasons for approval required, budget exhausted, policy blocked, verification failed, provider unavailable, daemon unavailable, and ambiguous plan
  - workspace profile support for default autonomy mode and default budget presets
  - validation rules for invalid, missing, or contradictory budgets
- Implementation notes:
  - keep existing approval modes backward compatible
  - autonomy mode should not grant permissions by itself; it resolves to budget and policy inputs
  - release-candidate mode should be stricter than development modes, not more permissive
  - document the difference between session approval mode and autonomy mode
- Tests and validation included in task:
  - workspace profile tests
  - model validation tests
  - docs review against [tool-policy.md](./tool-policy.md) and [workspace-profiles.md](./workspace-profiles.md)
- Done when:
  - Glassbox has a typed vocabulary for bounded autonomy that can be shown to operators and used by policy checks

### GBX-831: Add Budget Evaluation Engine And Durable Budget Evidence

- Status: `TODO`
- Depends on: `GBX-830`
- Goal: enforce autonomy budgets during task execution and record why work continued or stopped
- Deliverables:
  - budget evaluation engine that checks step count, tool count, write count, command count, verification count, branch count, duration, and artifact limits
  - canonical events for budget decisions, budget exhaustion, budget override requests, and budget override resolutions
  - projection fields for budget usage and remaining budget by task/session
  - CLI status output for budget posture and next action
  - replay/eval fingerprinting for budget inputs that materially affect behavior
- Implementation notes:
  - budget checks should run before tool execution, before starting a new step, before verification loops, and before branch attempts
  - do not count read-only inspection the same as writes or commands unless the budget says so
  - budget evidence should explain which limit caused a pause
  - keep repeated exhaustion idempotent and avoid spamming event logs
- Tests and validation included in task:
  - budget unit tests
  - integration tests for step/tool/write/command/verification exhaustion
  - replay tests for budget drift reporting
- Done when:
  - autonomous work can continue only while typed local budgets allow it, and every stop is explainable

### GBX-832: Calibrate Approval Modes Instead Of Collapsing Them

- Status: `TODO`
- Depends on: `GBX-831`
- Goal: make `confirm`, `review`, `on-request`, and `never` meaningfully different in the presence of autonomy budgets
- Deliverables:
  - explicit behavior table for existing approval modes under each risk bucket and autonomy mode
  - policy engine updates so `confirm`, `review`, and `on-request` no longer collapse to the same practical gate when budgets and workspace rules permit clearer behavior
  - migration or compatibility note for existing sessions and profiles
  - CLI and dashboard labels that explain the effective approval behavior for a session/task
  - deterministic tests for every mode/risk/budget combination that changes behavior
- Implementation notes:
  - preserve hard invariants such as workspace scope and destructive command blocks
  - avoid surprising existing users; require explicit autonomy mode or profile config before loosening risky behavior
  - `never` should remain a strict blocking mode for risky actions unless a later task redefines it explicitly
  - keep policy decision traces stable and exportable
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_tools_policy.py tests/integration/test_command_tool.py`
  - approval workflow integration tests
  - dashboard policy evidence tests if labels change
- Done when:
  - existing approval modes become useful controls for calibrated autonomy rather than mostly persisted labels

### GBX-833: Add Repository-Owned Safe Autonomy Rules

- Status: `TODO`
- Depends on: `GBX-832`
- Goal: let repositories declare safe local autonomy rules for mature workflows without bypassing hard runtime invariants
- Deliverables:
  - extension to `glassbox.tool-policy.json` or a new typed policy manifest section for autonomy-safe rules
  - selectors for tool name, command prefix, path root, file extension, test path, read-only operation, generated-output path, and maximum timeout
  - rule actions for allow-with-budget, require-approval, deny, and require-verification
  - policy decision traces that name the autonomy rule and budget field that allowed or paused work
  - docs with examples such as auto-running read-only inspections, targeted tests, format checks, or generated snapshot refreshes
- Implementation notes:
  - do not allow arbitrary policy code
  - hard invariants still win over repository rules
  - keep path and command matching normalized and testable
  - avoid repository rules that imply remote credentials or cloud authority
- Tests and validation included in task:
  - policy config parsing tests
  - policy engine tests for rule precedence and trace output
  - replay/eval impact tests if policy fingerprints change
- Done when:
  - teams can loosen Glassbox carefully for local workflows they understand, while keeping decisions visible and replayable

### GBX-834: Add Autonomy Mode CLI And Session Configuration Surfaces

- Status: `TODO`
- Depends on: `GBX-833`
- Goal: make autonomy mode and budget selection available through scriptable session commands
- Deliverables:
  - CLI flags for `session chat`, `session run`, `session message`, `session resume`, and task commands where appropriate
  - profile defaults for autonomy mode and named budget presets
  - `glassbox autonomy profile list|show` or equivalent command for inspecting effective modes and budgets
  - JSON and human output showing effective budget values after CLI/profile/default resolution
  - docs for common modes: manual inspection, test-driven repair, bounded local implementation, release candidate verification
- Implementation notes:
  - explicit CLI flags override workspace profile defaults
  - keep existing commands working without requiring new flags
  - show a concise summary of effective autonomy settings at session start and task start
  - avoid introducing interactive prompts for non-interactive command flows
- Tests and validation included in task:
  - CLI parser tests
  - workspace profile precedence tests
  - interactive launch tests for displayed mode summaries
- Done when:
  - operators can choose bounded autonomy from the CLI without editing internal config files

### GBX-835: Surface Autonomy Budgets In Session Status, Web Snapshots, And Exports

- Status: `TODO`
- Depends on: `GBX-834`
- Goal: make effective autonomy mode, budget use, and budget stops visible everywhere operators already inspect sessions
- Deliverables:
  - session status output for autonomy mode, budget used, budget remaining, last budget decision, and next action
  - snapshot API fields for session/task autonomy posture
  - generated frontend types for autonomy posture
  - session export fields for autonomy mode and budget evidence
  - docs update explaining how to inspect and interpret budget evidence
- Implementation notes:
  - avoid dumping large raw budget histories into every snapshot; include summaries and link to paginated details where needed
  - distinguish policy blocks from budget exhaustion in all operator-facing views
  - preserve backward compatibility for snapshots with no autonomy state
- Tests and validation included in task:
  - status formatter tests
  - web snapshot tests
  - export tests
  - frontend typecheck if generated API changes
- Done when:
  - an operator can tell why Glassbox acted, paused, or stopped without reading raw event JSON

---

## Phase 84: Proactive Daemon Worker And Background Job Execution

### GBX-840: Define Background Job Ownership And Recovery Contract

- Status: `TODO`
- Depends on: `GBX-831`, `GBX-811`
- Goal: define how the workspace daemon can run opt-in background work while preserving single-owner mutation and local-first recovery
- Deliverables:
  - docs defining background job states, ownership, queueing, cancellation, pause, resume, retry, stale-owner recovery, and observability
  - canonical event models for background job creation, claim, start, heartbeat, progress, completion, failure, cancellation, and recovery
  - distinction between mutating jobs, read-only maintenance jobs, and derived-index jobs
  - explicit non-goals for remote workers, distributed queues, cloud scheduling, and cross-workspace orchestration
  - test matrix for daemon restart, stale metadata, duplicate job claim, job cancellation, and projection rebuild
- Implementation notes:
  - the daemon may own background job execution, but canonical events remain the source of truth
  - no background work should rely on process-local memory as durable state
  - keep background work opt-in until release evidence proves safety
- Tests and validation included in task:
  - docs review against daemon, transport, session mutation, and observability code
  - event model tests if job events are added in this task
- Done when:
  - implementers have a precise local-worker contract before adding daemon job execution

### GBX-841: Add Background Job Store, Queue Projection, And CLI Inspection

- Status: `TODO`
- Depends on: `GBX-840`
- Goal: persist and inspect daemon job queues before running autonomous work through them
- Deliverables:
  - job projection tables for pending, running, completed, failed, cancelled, and stale jobs
  - repository methods for enqueue, claim, heartbeat, complete, fail, cancel, list, and show job state
  - `glassbox job list`, `glassbox job show JOB_ID`, and `glassbox job cancel JOB_ID` command surfaces
  - observability status fields for pending jobs, running jobs, stale jobs, and last job failure
  - tests for projection rebuild, stale job detection, idempotent cancellation, and JSON output
- Implementation notes:
  - cancellation command may append a request event; the owning daemon should acknowledge during execution
  - do not run model turns through the queue yet
  - keep job payloads typed and versioned
- Tests and validation included in task:
  - SQLite projection tests
  - CLI job command tests
  - observability tests
- Done when:
  - background jobs are durable, inspectable, and cancellable as data even before the daemon executes them

### GBX-842: Add Daemon Job Runner For Read-Only Maintenance Jobs

- Status: `TODO`
- Depends on: `GBX-841`
- Goal: teach the daemon to execute safe read-only background jobs before introducing autonomous mutation
- Deliverables:
  - daemon loop that claims eligible read-only jobs and records heartbeats/progress/completion/failure
  - first read-only job types such as projection health refresh, artifact pressure scan, provider evidence freshness scan, eval recommendation precompute, or repository index refresh placeholder
  - cancellation handling for long-running read-only jobs
  - tests for daemon restart, stale job recovery, duplicate claim prevention, and clean shutdown
  - docs for read-only daemon jobs and troubleshooting
- Implementation notes:
  - start with read-only or derived-state jobs only
  - keep job execution bounded and timeout-aware
  - avoid running jobs when another workspace owner is active or metadata is stale
  - do not require the daemon for normal foreground sessions
- Tests and validation included in task:
  - daemon runtime integration tests
  - background job unit tests with fake clocks where possible
  - observability status tests
- Done when:
  - the daemon can safely perform useful local maintenance in the background without mutating sessions or files

### GBX-843: Add Task Continuation Jobs For Awaiting-Work Sessions

- Status: `TODO`
- Depends on: `GBX-824`, `GBX-842`, `GBX-835`
- Goal: let the daemon continue an approved task plan while budgets allow, stopping cleanly on approval, question, policy block, budget exhaustion, failure, or cancellation
- Deliverables:
  - job type for continuing a task plan from the next runnable step
  - scheduler path that creates continuation jobs from CLI or dashboard opt-in actions
  - turn-engine integration that runs one bounded step at a time and records task/step events
  - stop conditions for pending approval, pending user question, policy block, budget exhaustion, failed verification, task completion, and operator cancellation
  - status and observability output for current continuation job and blocked reason
- Implementation notes:
  - execute one step per loop boundary so cancellation and budget checks stay responsive
  - do not allow background continuation without explicit autonomy mode and budget state
  - preserve one mutation owner; attached terminals and dashboard actions should route through the daemon when it owns the workspace
  - keep final assistant summaries concise and evidence-backed
- Tests and validation included in task:
  - integration tests for continue-until-blocked behavior
  - cancellation tests for running continuation jobs
  - approval/question pause tests
  - budget exhaustion tests
- Done when:
  - Glassbox can do more local work without constant operator prompting, while still stopping at explicit durable boundaries

### GBX-844: Add Background Job Recovery, Retry, And Failure Triage

- Status: `TODO`
- Depends on: `GBX-843`
- Goal: make failed or interrupted daemon jobs recoverable and explainable rather than mysterious background failures
- Deliverables:
  - retry policy for transient read-only jobs and task continuation jobs
  - explicit retry budget and retry-exhausted events
  - CLI commands to retry failed jobs or abandon them with a reason
  - dashboard and observability cues for failed jobs, retryable jobs, and abandoned jobs
  - retained artifacts for job failures when logs or tool outputs matter
- Implementation notes:
  - retries must not duplicate write side effects; only retry from event-safe boundaries
  - require operator confirmation or explicit budget for retrying mutating steps
  - failure triage should name whether the failure came from policy, budget, provider, tool, daemon, storage, or projection health
- Tests and validation included in task:
  - failed-job and retry integration tests
  - artifact retention tests for job failure artifacts
  - dashboard tests if failure cues are added
- Done when:
  - background autonomy failures leave behind clear evidence and safe next actions

### GBX-845: Add Background Autonomy Release Smoke

- Status: `TODO`
- Depends on: `GBX-844`
- Goal: convert daemon background execution into a repeatable release-smoke surface
- Deliverables:
  - focused smoke command or test suite for daemon read-only jobs, task continuation, cancellation, failure recovery, and stale-owner cleanup
  - retained evidence shape under `.glassbox/releases/.../background-jobs/`
  - release-gate recommendation for v8 background job stage
  - docs explaining which background behaviors are release-bearing and which remain manual/advisory
- Implementation notes:
  - keep smoke deterministic and credential-free
  - prefer fake model executors and generated fixtures
  - avoid sleep-heavy process tests; use explicit readiness and health checks
- Tests and validation included in task:
  - focused daemon/background integration suite
  - dry-run release gate update if scripts change
- Done when:
  - v8 background work is protected by objective smoke evidence instead of manual optimism

---

## Phase 85: Workspace Memory And Repository Intelligence

### GBX-850: Define Workspace Memory Contract

- Status: `TODO`
- Depends on: `GBX-811`, `GBX-830`
- Goal: add durable local workspace memory without introducing hidden long-term autonomous memory or opaque retrieval
- Deliverables:
  - docs defining memory entry types, provenance, freshness, confirmation, invalidation, usage, export, import, and replay behavior
  - typed models for memory facts, conventions, commands, failure patterns, architecture notes, user preferences, and task outcomes
  - canonical events for memory created, confirmed, updated, invalidated, imported, used-in-context, and pruned
  - explicit non-goals for cloud memory, cross-repo memory sync, hidden provider memory, and vector-store authority
  - privacy and redaction rules for memory entries and exports
- Implementation notes:
  - memory entries must be inspectable and attributable to events, artifacts, or explicit operator input
  - memory should be workspace-scoped by default, not user-global
  - memory use in prompts must be recorded so replay can explain context influence
  - avoid embeddings or vector retrieval until a later task defines inspectable semantics
- Tests and validation included in task:
  - model validation tests
  - docs review against [runtime-context.md](./runtime-context.md), [team-workflows.md](./team-workflows.md), and session export behavior
- Done when:
  - Glassbox has a safe vocabulary for remembering local facts without creating invisible prompt magic

### GBX-851: Add Memory Store, Projection, CLI, And Web Read APIs

- Status: `TODO`
- Depends on: `GBX-850`
- Goal: persist and inspect workspace memory entries before using them to influence model turns
- Deliverables:
  - memory projection tables and rebuild logic
  - repository methods for listing, showing, searching, confirming, invalidating, and pruning memory entries
  - CLI commands such as `glassbox memory list`, `glassbox memory show MEMORY_ID`, `glassbox memory confirm`, `glassbox memory invalidate`, and `glassbox memory prune --dry-run`
  - web routes and generated frontend types for memory read and maintenance APIs
  - tests for projection rebuild, import/export redaction, invalidation, and CLI/API output
- Implementation notes:
  - keep memory mutation explicit in this task; automatic extraction arrives later
  - separate active, stale, invalidated, and imported memory states
  - memory pruning must be dry-run friendly and never remove canonical source events
- Tests and validation included in task:
  - memory projection tests
  - CLI memory tests
  - web memory tests
  - OpenAPI generation and frontend typecheck
- Done when:
  - workspace memory is a durable, inspectable local data product, not a hidden prompt feature

### GBX-852: Add Operator-Confirmed Memory Capture From Sessions And Tasks

- Status: `TODO`
- Depends on: `GBX-851`, `GBX-824`
- Goal: let operators promote useful session/task facts into workspace memory with review before automatic extraction exists
- Deliverables:
  - CLI and dashboard actions to record memory from a session, task, artifact, tool result, or operator note
  - suggested memory candidates generated from explicit runtime signals but requiring confirmation
  - redaction and secret-checking for memory candidate text
  - event linkage from memory entry back to source session, event sequence, task ID, artifact ID, or operator note
  - tests for candidate generation, confirmation, rejection, redaction, and provenance
- Implementation notes:
  - do not auto-persist model-generated facts without confirmation in this task
  - candidates should be concise and categorized
  - repeated candidates should merge or deduplicate rather than creating noise
- Tests and validation included in task:
  - memory candidate unit tests
  - session/task integration tests
  - dashboard action tests if UI is added
- Done when:
  - operators can teach Glassbox durable local facts without editing JSON or trusting hidden extraction

### GBX-853: Add Local Repository Intelligence Index Contract

- Status: `TODO`
- Depends on: `GBX-842`, `GBX-850`
- Goal: define a rebuildable local code-intelligence layer that improves agent orientation without becoming an opaque second source of truth
- Deliverables:
  - docs defining repository index scope, provenance, freshness, invalidation, rebuild, storage, and prompt-use rules
  - typed index entities for files, symbols, modules, commands, tests, docs, eval cases, ownership hints, dependency hints, and recently active paths
  - index artifact format or projection strategy with schema versioning
  - explicit non-goals for full semantic code understanding, cloud indexing, and hidden vector authority
  - test matrix for source checkout, installed package, large repo, ignored files, generated files, and stale index handling
- Implementation notes:
  - start with deterministic static signals available from files and existing manifests
  - use structured parsers where practical instead of ad hoc prompt summaries
  - index rebuild must be explicit and observable
  - prompt use must cite index provenance and freshness
- Tests and validation included in task:
  - docs review against current repository context and runtime-context architecture
  - model validation tests if index models are added
- Done when:
  - implementers have a clear contract for richer local repo intelligence that remains inspectable and rebuildable

### GBX-854: Implement Repository Index Builder And Read APIs

- Status: `TODO`
- Depends on: `GBX-853`
- Goal: build the first deterministic local repository index and make it queryable from CLI and web surfaces
- Deliverables:
  - index builder for top-level project markers, package/module layout, docs map, eval map, known command scripts, test files, source files, and simple symbol summaries where supported
  - background job integration for read-only index refresh
  - CLI commands such as `glassbox repo index build`, `glassbox repo index status`, `glassbox repo index search`, and `glassbox repo index show`
  - web APIs and generated frontend types for index status and search
  - storage, artifact, or projection retention for index snapshots with freshness metadata
- Implementation notes:
  - keep the first index useful and modest; avoid expensive whole-repo crawling beyond documented limits
  - respect `.gitignore` and existing workspace exclusion conventions where practical
  - index failures should degrade to existing bounded repository context, not break sessions
- Tests and validation included in task:
  - repository index unit tests with fixture repos
  - integration tests for build/status/search
  - background job tests for refresh
  - OpenAPI and frontend typecheck if APIs change
- Done when:
  - Glassbox can answer basic local repository orientation questions without repeatedly rediscovering the same structure every turn

### GBX-855: Feed Memory And Repository Index Into Turn Context With Provenance

- Status: `TODO`
- Depends on: `GBX-851`, `GBX-854`, `GBX-831`
- Goal: use workspace memory and repository intelligence in model turns while preserving inspectability, budget control, and replay drift reporting
- Deliverables:
  - context builder updates that select bounded memory and index items for a turn
  - provenance manifests for every memory and index item included in prompt context
  - budget limits for memory count, index item count, context bytes, and freshness posture
  - CLI status, web snapshot, and dashboard runtime-context updates showing included memory/index sources
  - replay fingerprinting and drift messages for memory/index context changes
- Implementation notes:
  - memory/index context should be opt-in or mode-gated at first
  - prefer high-confidence, recently confirmed, task-relevant entries
  - do not silently include stale or invalidated memory
  - keep prompt fragments separated by source type rather than flattening them into one blob
- Tests and validation included in task:
  - context builder tests
  - replay fingerprint tests
  - status/web snapshot tests
  - eval tests for context drift reporting
- Done when:
  - richer local context improves autonomy while remaining visible and replay-aware

### GBX-856: Add Automatic Memory Candidate Extraction Behind Review Gates

- Status: `TODO`
- Depends on: `GBX-852`, `GBX-855`
- Goal: let Glassbox suggest memory updates after sessions and tasks while keeping operator review in control
- Deliverables:
  - extraction rules for candidate facts from completed tasks, repeated failures, stable commands, confirmed fixes, and operator notes
  - model-assisted extraction option that produces candidates only, not active memory
  - review queue for accepting, editing, merging, or rejecting candidates
  - policy and budget controls for when candidate extraction runs automatically
  - tests for false-positive suppression, deduplication, stale candidate expiry, and redaction
- Implementation notes:
  - candidates are not memory until accepted by policy or operator review
  - extraction should be bounded and cheap enough for background jobs
  - release-critical behavior should not depend on unreviewed candidates
- Tests and validation included in task:
  - memory extraction unit tests
  - daemon job tests if automatic candidate generation runs in background
  - dashboard review queue tests if UI is added
- Done when:
  - Glassbox can learn from work without silently rewriting its own worldview

---

## Phase 86: Self-Verification Loops And Branch-Search Workflows

### GBX-860: Define Verification Loop Contract

- Status: `TODO`
- Depends on: `GBX-831`, `GBX-824`
- Goal: define how an autonomous task can verify its own work through tests, evals, linting, type checks, or operator-defined commands
- Deliverables:
  - typed verification plan models for command, test, eval, lint, typecheck, package, and custom local checks
  - canonical events for verification planned, started, streamed, completed, failed, skipped, retried, and accepted with residual risk
  - rules for selecting verification from eval recommendations, workspace profiles, changed paths, task type, and policy budgets
  - docs explaining verify-repair loops, limits, failure categories, and release posture
  - tests for verification plan validation and failure classification
- Implementation notes:
  - verification commands are command-risk tools and must pass policy/budget checks
  - verification output should be summarized through artifacts rather than stuffing full logs into event payloads
  - keep operator-defined verification explicit and scriptable
- Tests and validation included in task:
  - verification model tests
  - command tool and policy tests
  - docs review against [replay-evals.md](./replay-evals.md)
- Done when:
  - Glassbox has a durable vocabulary for proving or disproving autonomous work

### GBX-861: Implement Budgeted Verify-Repair Loop For One Session Task

- Status: `TODO`
- Depends on: `GBX-860`, `GBX-843`
- Goal: let an autonomous task run a relevant verification check, inspect failure output, attempt a bounded repair, and rerun until success or budget exhaustion
- Deliverables:
  - runtime coordinator for one task-local verify-repair loop
  - integration with `run_tests`, `run_command`, eval recommendation, and artifact-backed failure digests
  - step and verification events for every attempt
  - budget checks for verification attempts, command count, write count, and runtime
  - CLI command or session flag to opt into verify-repair behavior
- Implementation notes:
  - start with targeted pytest or eval cases before broad arbitrary commands
  - each repair attempt should be a task step with clear input, output, and verification link
  - stop on ambiguous failure, policy block, pending approval, repeated identical failure, or budget exhaustion
- Tests and validation included in task:
  - integration test with deterministic failing fixture and successful repair
  - integration test with repeated failure and budget exhaustion
  - replay/eval tests for verification events if capture changes
- Done when:
  - Glassbox can complete a small local engineering loop with evidence instead of stopping after the first patch

### GBX-862: Execute Eval Recommendations As Optional Verification Plans

- Status: `TODO`
- Depends on: `GBX-861`
- Goal: turn `eval recommend` from advisory output into an optional executable verification plan under autonomy budgets
- Deliverables:
  - API and CLI path for `glassbox eval recommend --execute` or task-integrated recommendation execution
  - conversion from recommendation confidence rows into verification plan entries
  - budget and policy checks for selected eval profiles/cases before execution
  - retained artifacts linking recommendations, executed checks, skipped checks, and results
  - docs explaining when recommendation execution is blocking, advisory, or skipped
- Implementation notes:
  - keep low-confidence recommendations visible as optional rather than silently executed
  - never mix live-provider canary profiles into deterministic release recommendations unless explicitly requested
  - execution should explain why each case/profile was selected
- Tests and validation included in task:
  - eval recommendation engine tests
  - verification loop tests
  - CLI tests for execute/dry-run behavior
- Done when:
  - Glassbox can choose and run relevant deterministic verification based on changed paths while preserving reasoning

### GBX-863: Add Branch-Search Attempt Model

- Status: `TODO`
- Depends on: `GBX-824`, `GBX-860`
- Goal: turn existing session forks into a controlled strategy-search primitive for autonomous local work
- Deliverables:
  - typed branch-search models for search ID, parent session, candidate branch, strategy label, attempt status, verification status, and selection state
  - canonical events for branch search started, candidate planned, candidate forked, candidate executed, candidate verified, candidate compared, candidate selected, candidate rejected, and search abandoned
  - projection and query support for branch-search attempts and candidate outcomes
  - CLI commands for listing branch searches and showing candidate comparisons
  - docs explaining how branch search differs from ordinary manual fork and replay
- Implementation notes:
  - branch search should use existing fork semantics and not mutate parent history
  - branch attempts must be budgeted and bounded
  - candidates should have explicit strategy labels and verification plans
- Tests and validation included in task:
  - fork/branch-search projection tests
  - CLI branch-search tests
  - replay/export tests if branch-search metadata is included
- Done when:
  - Glassbox can represent alternate solution attempts as durable local evidence rather than ad hoc session clutter

### GBX-864: Implement Bounded Branch Search For Competing Repair Strategies

- Status: `TODO`
- Depends on: `GBX-863`, `GBX-861`
- Goal: let Glassbox try a small number of local candidate branches for a failed task and compare verification outcomes
- Deliverables:
  - runtime coordinator that forks candidate sessions from a stable point and runs one strategy per child
  - branch-attempt budget checks for candidate count, tool calls, writes, commands, and verification attempts
  - comparison summary for passing, failing, blocked, timed-out, and inconclusive candidates
  - CLI command or task option for starting branch search with a max candidate count
  - cleanup and retention guidance for candidate branches and artifacts
- Implementation notes:
  - start with sequential candidate execution under one mutation owner; do not introduce concurrent writers
  - never merge candidate changes automatically in this task
  - candidate branches should remain inspectable even when rejected
  - avoid provider-dependent strategy randomness in deterministic tests
- Tests and validation included in task:
  - branch-search integration test with two deterministic candidates
  - cancellation and budget exhaustion tests
  - dashboard comparison tests if UI changes land here
- Done when:
  - Glassbox can explore alternatives locally without losing auditability or corrupting parent session history

### GBX-865: Add Branch Outcome Selection And Handoff

- Status: `TODO`
- Depends on: `GBX-864`
- Goal: let an operator choose a winning candidate, export its evidence, and continue from that branch safely
- Deliverables:
  - CLI and dashboard actions to mark a candidate as selected, rejected, or needs-review
  - session/task export fields for branch-search summary and selected candidate evidence
  - optional command to generate a patch summary or handoff note from the selected candidate
  - docs for reviewing, selecting, and continuing candidate branches
  - tests for selection idempotency, export shape, and branch continuation
- Implementation notes:
  - selection is metadata, not an automatic merge into parent history
  - selected candidate state should link to verification evidence and residual risks
  - rejected candidates should remain historical evidence unless pruned explicitly
- Tests and validation included in task:
  - branch selection tests
  - session export tests
  - dashboard action tests if UI is added
- Done when:
  - branch search becomes a usable operator workflow, not merely a backend experiment

### GBX-866: Improve Replay Drift And Verification Failure Explanation

- Status: `TODO`
- Depends on: `GBX-862`, `GBX-855`
- Goal: make failed replay, eval, and verification loops explain likely causes rather than only naming drift categories
- Deliverables:
  - triage summaries for transcript drift, event-family drift, task-plan drift, budget drift, memory drift, repository-index drift, policy drift, verification drift, and provider-advisory drift
  - artifact summaries that point to the first divergent turn, task step, memory/index source, or verification attempt
  - CLI and dashboard display of drift explanation and next recommended action
  - eval summary updates for v8 autonomy/context-specific drift
  - tests for deterministic triage outputs
- Implementation notes:
  - keep explanations evidence-based and avoid pretending to know model intent when evidence is weak
  - explanations should help decide whether to fix code, refresh baseline, rerun verification, inspect memory, or adjust budget
  - preserve existing replay taxonomy compatibility
- Tests and validation included in task:
  - replay triage tests
  - eval summary tests
  - dashboard evidence tests if UI changes land here
- Done when:
  - operators can debug autonomous workflow drift without spelunking raw JSON first

---

## Phase 87: Tool Expansion And Provider Capability Depth

### GBX-870: Define v8 Tool Expansion And Sandboxing Contract

- Status: `TODO`
- Depends on: `GBX-833`, `GBX-811`
- Goal: decide which new local tools should exist for more agentic workflows and how they remain policy-bounded
- Deliverables:
  - docs identifying candidate tools for structured file edits, test discovery, dependency inspection, package scripts, code search, symbol lookup, diff review, artifact summarization, and optional browser/network diagnostics
  - risk classification for each candidate tool and required policy/budget controls
  - explicit non-goals for arbitrary plugin marketplace behavior and remote tool execution
  - test matrix for tool validation, streaming output, cancellation, artifacts, and policy traces
  - migration note for existing tool schema exposure and replay capture
- Implementation notes:
  - prefer narrow structured tools over asking the model to use raw shell for everything
  - keep destructive or network-capable tools out of the first slice unless they have a strong local policy story
  - every new tool must produce structured output that can be summarized in events and artifacts
- Tests and validation included in task:
  - docs review against current tool registry and policy engine
  - tool schema tests if any candidate model is added
- Done when:
  - v8 has a principled tool expansion path that increases capability without becoming a plugin free-for-all

### GBX-871: Add Structured Diff Review And Patch Summary Tools

- Status: `TODO`
- Depends on: `GBX-870`, `GBX-861`
- Goal: give agents and operators better local change understanding without relying on raw shell commands or unstructured prose
- Deliverables:
  - read-only diff summary tool for workspace changes, staged changes, and optional path filters
  - patch-risk summary output covering touched files, insertions/deletions, generated files, tests touched, docs touched, and policy-sensitive paths
  - artifact recording for large diff summaries
  - integration with verification loop summaries and branch candidate comparisons
  - tests for dirty worktree, binary files, large diffs, path filters, and policy evidence
- Implementation notes:
  - preserve the rule that the agent must not revert user changes it did not make
  - the tool is read-only and should never mutate git state
  - avoid storing full sensitive diffs in exports without redaction review
- Tests and validation included in task:
  - tool unit tests
  - integration tests with fixture git repositories
  - branch-search comparison tests if integrated
- Done when:
  - autonomous repair loops can explain what changed before asking the operator to trust the result

### GBX-872: Add Structured Test Discovery And Target Selection Tools

- Status: `TODO`
- Depends on: `GBX-870`, `GBX-854`
- Goal: help agents select relevant tests without repeatedly guessing command lines
- Deliverables:
  - read-only test discovery tool that lists test files, test functions/classes where practical, markers, and likely ownership from repository index data
  - target-selection helper that maps changed paths or task context to candidate tests with confidence reasons
  - integration with verification plan selection
  - docs explaining confidence levels and limits
  - tests for Python pytest repositories and graceful degradation in unknown layouts
- Implementation notes:
  - use structured parsers or pytest collection where practical and budgeted
  - do not run tests in the discovery tool unless explicitly configured
  - keep recommendations advisory unless a verification plan executes them
- Tests and validation included in task:
  - test discovery unit tests
  - verification loop integration tests
  - eval recommendation tests if metadata is shared
- Done when:
  - Glassbox can choose focused verification targets with evidence rather than only broad defaults

### GBX-873: Add Provider Canary Depth For Agentic Workflows

- Status: `TODO`
- Depends on: `GBX-733`, `GBX-860`
- Goal: expand advisory provider canaries to cover the behaviors that matter for autonomous local work
- Deliverables:
  - new advisory scenarios for malformed tool calls, long-context continuity, retry behavior, rate-limit handling, tool-call streaming, cancellation during retry, multi-step plan following, and verification-loop interaction
  - provider capability matrix fields for scenario confidence, observed limits, retry posture, and tool-call reliability
  - fake-provider tests for orchestration and credential-missing skips
  - docs explaining how provider canary depth informs model choice without becoming deterministic signoff
- Implementation notes:
  - keep canary evidence redacted and advisory
  - do not store raw prompts, raw model responses, API keys, or provider request metadata
  - prefer scenario rows that can be skipped explicitly when provider support is unknown
- Tests and validation included in task:
  - provider canary unit tests
  - provider diagnostics tests
  - optional manual live-provider retained evidence
- Done when:
  - operators can see which providers are credible for more autonomous workflows and which remain risky

### GBX-874: Add Provider-Aware Model Selection Recommendations

- Status: `TODO`
- Depends on: `GBX-873`, `GBX-830`
- Goal: recommend model/provider choices for a task based on local configuration, advisory canary evidence, autonomy mode, and workflow needs
- Deliverables:
  - recommendation model that considers provider readiness, selected autonomy mode, needed tool-call reliability, context size, cancellation posture, and advisory canary results
  - CLI command such as `glassbox provider recommend --task-kind ...` or integration into provider diagnostics/session start
  - dashboard onboarding or task-start cue showing recommended provider posture
  - docs explaining recommendation confidence and non-authoritative nature
  - tests for missing credentials, stale canary evidence, unsupported provider, and local fallback recommendations
- Implementation notes:
  - recommendations should never silently change the model for a session unless the operator selected an auto mode explicitly
  - stale or skipped canary evidence should lower confidence rather than pretending success
  - deterministic local fallback remains valid for tests and offline development
- Tests and validation included in task:
  - provider recommendation unit tests
  - CLI/provider diagnostics tests
  - dashboard cue tests if UI is added
- Done when:
  - provider evidence helps practical workflow setup without becoming hidden provider policy

### GBX-875: Add Optional Network And Browser Diagnostic Tool Contract

- Status: `TODO`
- Depends on: `GBX-870`, `GBX-833`
- Goal: decide whether v8 should include tightly bounded network or browser diagnostic tools for local app workflows
- Deliverables:
  - docs defining allowed use cases, such as local dev server health, HTTP endpoint checks, screenshot capture, accessibility smoke, and static asset verification
  - policy contract for network host allowlists, local-only defaults, timeout budgets, output redaction, and approval requirements
  - explicit non-goals for general web browsing, credentialed scraping, remote exploitation, or unrestricted network automation
  - prototype schema or task plan for later implementation if accepted
  - tests for policy validation if schema is added
- Implementation notes:
  - default to local-only diagnostics unless an operator opts in
  - do not expand tool runtime into browser-native code editing
  - keep this as a contract task unless implementation risk is clearly bounded
- Tests and validation included in task:
  - docs review against tool policy and frontend testing docs
  - policy schema tests if added
- Done when:
  - the project has a clear answer on browser/network diagnostics before accidentally growing broad web automation

---

## Phase 88: Dashboard Autonomy Console

### GBX-880: Design Dashboard Autonomy Console Information Architecture

- Status: `TODO`
- Depends on: `GBX-823`, `GBX-835`, `GBX-841`, `GBX-851`
- Goal: define how the dashboard should present tasks, plans, budgets, background jobs, memory, repository intelligence, and branch-search evidence without overwhelming the operator
- Deliverables:
  - dashboard IA doc or section defining new navigation, task queue, selected task inspector, budget controls, memory/index inspectors, and branch-search comparison surfaces
  - API payload review for task, job, memory, index, and autonomy posture data
  - mobile, keyboard, and screen-reader interaction expectations
  - loading, empty, stale, blocked, failed, live, reconnecting, and historical-only states for autonomy views
  - screenshot or wireframe notes if helpful for implementation
- Implementation notes:
  - keep operational density high and marketing-style layout out of the console
  - avoid nesting cards inside cards; use tables, panes, tabs, and compact evidence rows
  - make the first viewport useful for action triage, not explanation copy
  - preserve existing session inspector affordances
- Tests and validation included in task:
  - docs/design review against current frontend component patterns
  - accessibility checklist update if the IA changes keyboard paths
- Done when:
  - implementers know how the dashboard should become an autonomy control room before components are built

### GBX-881: Add Task Queue And Plan Inspector To Dashboard

- Status: `TODO`
- Depends on: `GBX-880`, `GBX-823`
- Goal: let operators inspect task plans, steps, statuses, blockers, and related session events from the dashboard
- Deliverables:
  - task queue view with filters for active, blocked, failed, completed, background, and historical tasks
  - selected task inspector with plan steps, current step, verification state, budget summary, related session, related branch attempts, and event history
  - client store support for loading task pages and task details
  - SSE or refresh behavior for task updates where supported
  - frontend tests for queue filters, inspector loading states, empty states, and update application
- Implementation notes:
  - reuse design-system primitives and session inspector patterns
  - keep task event history paginated
  - do not add mutation controls until GBX-882
- Tests and validation included in task:
  - frontend unit/component tests
  - Playwright smoke if routing changes
  - frontend lint, typecheck, tests, and build
- Done when:
  - dashboard users can understand what autonomous work exists and where it is blocked

### GBX-882: Add Dashboard Controls For Plans, Budgets, Pause, Resume, And Cancellation

- Status: `TODO`
- Depends on: `GBX-881`, `GBX-843`, `GBX-835`
- Goal: give operators explicit control over autonomous work from the dashboard
- Deliverables:
  - actions to approve a proposed plan, start bounded continuation, pause a task, resume a task, cancel a task/job, and adjust a budget within allowed policy
  - confirmation flows for budget increases, risky mode changes, and mutating background continuation
  - optimistic UI only where the backend accepts the action synchronously and SSE confirms later state
  - error handling for stale task state, daemon unavailable, policy block, budget invalid, and already-resolved actions
  - tests for each action and failure path
- Implementation notes:
  - dashboard actions must call backend APIs; browser-local state is not authority
  - require clear labels for what will continue automatically and what will still ask for approval
  - do not hide policy or budget reasons behind generic failure toasts
- Tests and validation included in task:
  - web action tests
  - frontend store/action tests
  - Playwright workflow for start/pause/resume/cancel if practical
- Done when:
  - the dashboard can safely control autonomous work without becoming an unbounded remote control plane

### GBX-883: Add Memory And Repository Index Inspectors

- Status: `TODO`
- Depends on: `GBX-880`, `GBX-851`, `GBX-854`, `GBX-855`
- Goal: make the context sources that shape autonomous work visible and maintainable from the dashboard
- Deliverables:
  - memory inspector with active/stale/invalidated filters, provenance, freshness, source links, usage evidence, confirm/invalidate actions, and prune preview
  - repository index inspector with status, freshness, top entities, search, rebuild action, and stale-index warnings
  - runtime-context pane updates showing which memory/index items influenced the selected turn/task
  - tests for inspector loading, filtering, action states, and empty/stale states
- Implementation notes:
  - avoid making memory feel magical; show source and last-confirmed evidence prominently
  - index rebuild should be a background job action when the daemon is active
  - invalidated memory should remain inspectable as historical evidence
- Tests and validation included in task:
  - frontend component/store tests
  - web memory/index tests if action APIs change
  - frontend lint, typecheck, tests, and build
- Done when:
  - operators can see and curate the local knowledge Glassbox uses for more agentic behavior

### GBX-884: Add Branch-Search Comparison And Candidate Selection UI

- Status: `TODO`
- Depends on: `GBX-865`, `GBX-881`
- Goal: make alternate autonomous strategies understandable and selectable from the dashboard
- Deliverables:
  - branch-search comparison view showing candidate strategy, status, verification result, changed files, policy/budget posture, and residual risks
  - actions to mark candidate selected, rejected, or needs-review
  - links into candidate session inspectors and artifacts
  - compact diff/patch summary presentation from structured diff tools when available
  - tests for selection actions, comparison rendering, and candidate navigation
- Implementation notes:
  - selection is metadata and must not imply automatic merge
  - make failed and blocked candidates useful evidence, not just hidden failures
  - preserve mobile and keyboard usability for comparison tables
- Tests and validation included in task:
  - frontend comparison tests
  - Playwright branch-search workflow if practical
  - web action tests if selection API changes
- Done when:
  - branch search is a practical operator workflow, not a backend-only feature

### GBX-885: Add Why-This-Action And Autonomy Evidence Pane

- Status: `TODO`
- Depends on: `GBX-882`, `GBX-855`, `GBX-866`
- Goal: explain why Glassbox took, proposed, paused, or refused an autonomous action
- Deliverables:
  - evidence pane that ties actions to plan steps, policy decisions, budget decisions, memory/index context, verification results, and provider readiness
  - timeline markers for autonomous decisions and human interventions
  - stale or missing evidence cues when the dashboard cannot explain a decision fully
  - tests for evidence interpretation labels and edge cases
- Implementation notes:
  - explanations must be derived from backend evidence, not dashboard guesses
  - keep language compact and operational
  - avoid overclaiming causal certainty when only weak evidence exists
- Tests and validation included in task:
  - frontend verification/evidence tests
  - session-state reducer tests for new event types
  - accessibility checks for evidence navigation
- Done when:
  - an operator can answer "why did it do that?" without reading raw event payloads first

### GBX-886: Add Autonomy Console Accessibility And Long-Session UX Review

- Status: `TODO`
- Depends on: `GBX-881`, `GBX-882`, `GBX-883`, `GBX-884`, `GBX-885`
- Goal: keep the richer dashboard usable under long sessions, many tasks, and keyboard/screen-reader workflows
- Deliverables:
  - named browser and assistive-technology pairing review for task queue, plan inspector, budget controls, memory inspector, repository index, and branch comparison
  - keyboard workflow evidence for start/pause/resume/cancel, budget review, memory confirmation, and branch selection
  - mobile drill-in review for task and branch-search views
  - docs recording bounded accessibility claims and residual risks
  - fixes for any blocking usability or accessibility issue found during review
- Implementation notes:
  - do not make broad accessibility claims beyond tested pairings
  - prioritize dense but understandable operational UI over decorative explanation
  - ensure destructive or budget-increasing actions are clearly distinguishable
- Tests and validation included in task:
  - frontend accessibility/unit tests where practical
  - Playwright keyboard smoke
  - manual evidence retained under the v8 release evidence path
- Done when:
  - the autonomy console is usable by real operators, not only by happy-path mouse workflows

---

## Phase 89: v8 Eval, Release Gate, Packaging, Manual Evidence, And Release Signoff

### GBX-890: Expand Deterministic Eval Coverage For v8 Autonomy

- Status: `TODO`
- Depends on: `GBX-825`, `GBX-831`, `GBX-861`, `GBX-865`, `GBX-855`
- Goal: promote stable v8 autonomy behaviors into repository-owned deterministic eval evidence
- Deliverables:
  - eval cases for task-plan proposal capture, task continuation until blocked, budget exhaustion, verify-repair success, verify-repair failure, memory context drift, repository-index context drift, and branch-search candidate comparison where stable
  - coverage manifest updates for v8 autonomy capabilities and criticality
  - impact-rule updates mapping task, autonomy, memory, index, verification, branch-search, web, and frontend paths to relevant cases/profiles
  - profile updates for commit-time, push-time, release-candidate, and v8 autonomy advisory suites
  - docs explaining which autonomy behaviors are blocking, advisory, or integration-only
- Implementation notes:
  - keep commit-time smoke small and stable
  - promote only deterministic, low-noise cases into blocking release profiles
  - keep daemon lifecycle, provider-dependent behavior, long-running branch search, and UI-specific interactions advisory unless they are stable enough for release blocking
- Tests and validation included in task:
  - selected new eval cases
  - `uv run glassbox eval audit --cwd .`
  - `uv run glassbox eval report commit-smoke push-confirmation release-candidate --output-dir .glassbox/evals/v8-release-signoff --cwd .`
- Done when:
  - v8 autonomy has repository-owned regression evidence instead of only integration tests and manual review

### GBX-891: Add v8 Autonomy Observability And Recovery Review

- Status: `TODO`
- Depends on: `GBX-845`, `GBX-856`, `GBX-866`
- Goal: make observability and recovery commands explain autonomous runtime health, memory/index posture, and background work status
- Deliverables:
  - observability status fields for active tasks, blocked tasks, budget exhaustion, background jobs, stale jobs, memory freshness, repository index freshness, branch searches, verification failures, and provider advisory posture
  - recovery guidance for each new degraded state
  - CLI and JSON output tests
  - docs update for v8 recovery and maintenance workflows
  - manual recovery review evidence for stale jobs, failed task continuation, memory invalidation, index rebuild, branch-search cleanup, and projection rebuild
- Implementation notes:
  - keep read-only observability safe and scriptable
  - do not automatically mutate memory, jobs, tasks, or indexes from observability commands
  - recovery guidance should point to explicit commands with dry-run options where applicable
- Tests and validation included in task:
  - observability tests
  - recovery smoke commands with retained output
  - docs tests if release docs are updated
- Done when:
  - operators can diagnose autonomous work as confidently as they can diagnose projections, artifacts, provider evidence, and daemon status today

### GBX-892: Add Package And Installed-Smoke Coverage For v8 Surfaces

- Status: `TODO`
- Depends on: `GBX-884`, `GBX-891`
- Goal: ensure v8 task, autonomy, memory, index, branch-search, and dashboard assets work from built packages, not only source checkouts
- Deliverables:
  - package contents validation for new Python modules, docs, eval cases, profiles, frontend static assets, and generated API schema/types
  - installed-wheel smoke for task inspection, autonomy profile listing, memory/index status, background job status, eval profile listing, and dashboard asset availability
  - source-builder docs for any new frontend or generated-asset steps
  - tests or scripts for installed-package CLI output and dashboard static asset validation
- Implementation notes:
  - keep smoke compact and credential-free
  - installed smoke should not require a live provider or remote network
  - verify that docs included in sdist/wheel match public v8 operating model
- Tests and validation included in task:
  - package contents script
  - installed-wheel smoke script
  - `uv build --wheel --sdist`
  - frontend build
- Done when:
  - v8 surfaces are packaged and runnable from installed artifacts

### GBX-893: Add v8 Release Gate

- Status: `TODO`
- Depends on: `GBX-890`, `GBX-891`, `GBX-892`
- Goal: compose the v7 release gate with v8 autonomy-specific evidence into one objective release-candidate command
- Deliverables:
  - `scripts/validate_v8_release_gate.py` or equivalent gate command
  - gate stages for Python format/lint/typecheck, Python tests, frontend lint/typecheck/tests/build, deterministic eval report, autonomy eval suite, background job smoke, memory/index smoke, package build, installed smoke, provider canary skip/pass evidence, and retained summary
  - dry-run mode and explicit evidence directory support
  - `summary.json` and concise human-readable summary output
  - unit tests for gate stage composition, dry-run behavior, failure reporting, and evidence paths
- Implementation notes:
  - reuse v7 gate stages rather than duplicating command orchestration where practical
  - provider canaries remain advisory by default
  - every skipped stage must have an explicit reason
  - release evidence should make autonomy boundedness visible, not just pass/fail
- Tests and validation included in task:
  - gate unit tests
  - dry-run v8 gate
  - focused real gate run before release candidate publication
- Done when:
  - v8 release readiness has one command that records deterministic and advisory evidence clearly

### GBX-894: Complete v8 Manual Validation And Accessibility Evidence

- Status: `TODO`
- Depends on: `GBX-886`, `GBX-893`
- Goal: retain human evidence for autonomy workflows that automated tests cannot fully prove
- Deliverables:
  - manual validation checklist for terminal task planning, dashboard plan inspection, background continuation, pause/resume/cancel, budget exhaustion, memory confirmation/invalidation, repository index rebuild, verify-repair loop, branch-search comparison, provider recommendation, and package smoke
  - terminal review evidence for supported TTY, plain fallback, long task output, approvals/questions, cancellation, daemon attach, and background job cues
  - dashboard review evidence for task console, budget controls, memory/index inspectors, branch comparison, evidence pane, mobile, keyboard, and named accessibility pairings
  - recovery review evidence for failed jobs, stale daemon, stale index, invalid memory, failed verification, projection rebuild, artifact pressure, and backup/restore
  - explicit residual-risk list and go/no-go recommendation
- Implementation notes:
  - retain manual evidence under the same `.glassbox/releases/...` candidate directory as the automated gate where practical
  - keep claims bounded to the named pairings and scenarios tested
  - do not paste large generated JSON into docs; link or summarize retained artifact paths
- Tests and validation included in task:
  - manual evidence review
  - docs guardrail tests if release docs are updated
- Done when:
  - v8 has human evidence for the workflows where autonomy, UI, terminal behavior, and recovery need actual operator judgment

### GBX-895: Publish v8 Release-Candidate Guide

- Status: `TODO`
- Depends on: `GBX-893`, `GBX-894`
- Goal: publish a concise public guide for the supported v8 operating model, validation path, evidence expectations, non-goals, residual risks, and release decision
- Deliverables:
  - [v8-release-candidate.md](./v8-release-candidate.md) or equivalent operator guide
  - root README update linking the v8 release candidate when appropriate
  - docs hub update linking v8 task, contract, evidence, and release-candidate docs
  - release-readiness checklist reflecting automated gate, manual evidence, provider advisory posture, package smoke, memory/index posture, autonomy budgets, background jobs, branch search, dashboard accessibility, and residual risks
  - decision section with candidate build, date, evidence directory, final pass/fail state, and accepted risks
- Implementation notes:
  - keep the release guide operator-readable
  - be explicit that auditable autonomy is local and bounded, not cloud authority or unrestricted automation
  - name remaining non-goals and known residual risks clearly
  - avoid overclaiming provider reliability or accessibility beyond retained evidence
- Tests and validation included in task:
  - docs link review
  - release docs guardrail tests
  - final v8 release gate run
- Done when:
  - v8 has a publishable release-candidate narrative backed by retained automated and manual evidence

## v8 Release-Candidate Readiness Checklist

Before treating a build as the v8 release candidate, complete this list:

- `uv run glassbox command tree` matches the documented command surface.
- `uv run python scripts/validate_v8_release_gate.py` passes and writes `summary.json`.
- Manual validation exists in the same evidence directory as the automated summary where practical.
- The deterministic `release-candidate` eval profile passes.
- The v8 autonomy eval suite runs and any advisory gaps are recorded.
- Task-plan events, projections, CLI queries, web APIs, export/import, and replay behavior have focused automated coverage.
- Autonomy mode and budget behavior has policy, CLI, web, replay, and dashboard evidence.
- Background daemon job execution has deterministic smoke evidence for read-only jobs, continuation jobs, cancellation, failure, and stale-owner recovery.
- Workspace memory and repository index behavior have provenance, freshness, invalidation, redaction, context-use, and replay-drift evidence.
- Verify-repair loops and branch-search workflows have deterministic local fixtures and retained artifacts.
- Provider diagnostics and provider canaries either run with retained redacted evidence or record explicit skip reasons.
- Dashboard autonomy console evidence covers task queue, plan inspector, budget controls, memory/index inspectors, branch comparison, evidence pane, mobile, and keyboard workflows.
- Terminal review evidence covers task planning, background continuation cues, approvals/questions, cancellation, daemon attach, long output, and fallback.
- Recovery review evidence covers observability, projections, artifacts, backups, daemon, jobs, memory, index, eval, and installed dashboard workflows.
- Package artifacts include static dashboard assets, v8 docs, eval profiles, memory/index/task modules, release scripts, and source-builder guidance.
- Named accessibility pairings are recorded before making stronger accessibility claims.
- Residual risks are named, mitigated, and accepted in the release decision.

## Deliberate v8 Non-Goals

Do not spend v8 effort on these unless a later task explicitly changes scope:

- hosted control plane
- cloud authority for workspace ownership
- remote multi-user orchestration
- simultaneous multi-writer mutation of one workspace
- distributed worker fleet
- plugin marketplace or arbitrary third-party tool loading
- browser-native code editing as a replacement for local tools
- remote policy enforcement
- hidden provider-side memory
- uninspectable vector-store retrieval treated as source of truth
- unbounded repository crawling without provenance, freshness, and rebuild semantics
- automatic merging of branch-search candidates into parent history
- replacing deterministic replay/eval release authority with live-provider canaries
- removing the plain terminal fallback

Multiple local observers and richer local autonomy are in scope. Multiple concurrent mutation owners and cloud authority are not.
