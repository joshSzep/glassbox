# Glassbox Tasks

## Purpose

This document is the implementation task graph for Glassbox.

It is written for an LLM agent that will execute the work incrementally inside the repository. Tasks are organized to minimize ambiguity, make dependencies explicit, and keep quality enforcement inside each task rather than in a separate QA phase.

Glassbox is a local-first CLI agent harness with:

- a terminal-first user experience
- an event-sourced runtime
- typed tool execution
- a live dashboard backed by streamed events
- resume, replay, and approval workflows

The architecture source of truth is [architecture.md](./architecture.md). The database source of truth is [database.md](./database.md).

## Agent Execution Rules

These rules apply to every task in this file.

1. Respect dependency order. Do not start a task until all listed dependencies are complete unless the task explicitly says it can proceed in parallel.
2. Treat `events` as the canonical source of truth. Projection tables, cached views, and frontend state are derived from events.
3. Every feature task automatically includes:
   - automated tests for the new behavior
   - `ruff` formatting and lint compliance
   - `ty` typecheck compliance for touched code
   - documentation updates when contracts or workflows change
4. There is no separate QA phase. Quality is part of task completion.
5. Prefer small vertical slices that become executable quickly over broad speculative scaffolding.
6. If a task uncovers an architectural mismatch, update the relevant doc before or alongside the code change.
7. Do not add features outside the documented scope unless a prerequisite is genuinely missing.

## Completion Contract For Any Task

A task is complete only when all of the following are true:

- the implementation exists in the intended module boundary
- automated tests covering the new behavior exist and pass
- lint, formatting, and type checks pass for the touched slice
- the task does not leave dead stubs or placeholder code without an explicit follow-up task in this file
- docs are updated if the task changes operator-visible behavior, persistence shape, or public interfaces

## Suggested Status Markers

If an agent updates this document later, use one of these markers next to task IDs:

- `TODO`
- `IN_PROGRESS`
- `BLOCKED`
- `DONE`

## Expected Repository Targets

These are the main implementation areas referenced below:

```text
src/glassbox/
    cli/
    core/
    runtime/
    llm/
    tools/
    store/
    web/
    services/
tests/
docs/
```

## Recommended Validation Commands

Use the narrowest viable validation after each task, but the baseline validation pattern for completed work should be:

```bash
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run pytest
```

During incremental implementation, use narrower commands when possible:

```bash
uv run pytest tests/unit/test_specific_module.py
uv run pytest tests/integration/test_specific_flow.py
uv run ruff check src/glassbox/path.py tests/path_test.py
uv run ty check src/glassbox/path.py
```

## Task Graph

---

## Phase 0: Repository And Toolchain Foundation

### GBX-001: Initialize Python Project Skeleton

- Status: `DONE`
- Depends on: none
- Goal: create the Python 3.14 project skeleton managed by `uv`
- Deliverables:
  - `pyproject.toml`
  - package metadata for `glassbox`
  - `src/` layout
  - initial `README` or minimal project entrypoint note if needed
- Implementation notes:
  - use `src` layout
  - define console script entrypoint for `glassbox`
  - configure Python requirement as `>=3.14,<3.15` unless a different minor-range policy is chosen deliberately
- Tests and validation included in task:
  - add at least one smoke test proving the package imports cleanly
  - confirm `uv` can resolve and install the environment
- Done when:
  - `uv sync` succeeds
  - `uv run python -c "import glassbox"` succeeds through the managed environment

### GBX-002: Configure Ruff, Pytest, Ty, And Pre-Commit

- Status: `DONE`
- Depends on: `GBX-001`
- Goal: establish the project quality toolchain as executable defaults
- Deliverables:
  - `ruff` config in `pyproject.toml`
  - `pytest` config in `pyproject.toml` or separate config if justified
  - `ty` config
  - `.pre-commit-config.yaml`
  - developer scripts or `make`-style aliases only if they reduce friction materially
- Implementation notes:
  - select strict enough lint and type settings to catch structural mistakes early
  - keep formatting and lint behavior deterministic
- Tests and validation included in task:
  - add a minimal CI-like local command sequence to documentation
  - add one test execution path and ensure pre-commit runs the intended hooks
- Done when:
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run ty check`
  - `uv run pytest`
  - `uv run pre-commit run --all-files`
    all succeed on the repo baseline

### GBX-003: Create Base Package Layout

- Status: `DONE`
- Depends on: `GBX-001`, `GBX-002`
- Goal: create the module tree described in the architecture doc
- Deliverables:
  - package directories and `__init__.py` files for `cli`, `core`, `runtime`, `llm`, `tools`, `store`, `web`, and `services`
  - `tests/unit`, `tests/integration`, and `tests/e2e`
- Implementation notes:
  - create only the modules that are immediate anchors for later tasks
  - avoid stuffing behavior into `__init__.py`
- Tests and validation included in task:
  - add import smoke tests for the top-level packages that now exist
- Done when:
  - all intended package roots import successfully
  - test tree is in place and discoverable by pytest

---

## Phase 1: Core Domain Types

### GBX-010: Implement Shared Core Types And Identifiers

- Status: `DONE`
- Depends on: `GBX-003`
- Goal: establish reusable typed primitives for the rest of the system
- Deliverables:
  - `src/glassbox/core/ids.py`
  - `src/glassbox/core/types.py`
  - shared enums or literals for session, turn, tool, and approval states
- Implementation notes:
  - prefer typed aliases and Pydantic-friendly types over raw strings scattered through the codebase
  - centralize ID generation helpers if needed
- Tests and validation included in task:
  - unit tests for state literals, serialization, and invalid value rejection where applicable
- Done when:
  - downstream modules can import session and turn states from one place

### GBX-011: Implement Core Pydantic Models

- Status: `DONE`
- Depends on: `GBX-010`
- Goal: encode the main domain models from the architecture doc
- Deliverables:
  - `SessionConfig`
  - `SessionState`
  - `MessagePart`
  - `TranscriptMessage`
  - `ToolCallRecord`
  - approval and policy models if their fields are stable enough at this stage
- Implementation notes:
  - use `ConfigDict(extra="forbid")` where appropriate
  - keep domain models free from database-specific concerns
- Tests and validation included in task:
  - round-trip model serialization tests
  - invalid payload validation tests
- Done when:
  - the core models are stable enough for runtime and store modules to depend on them

### GBX-012: Implement Event Payload Models And Envelope

- Status: `DONE`
- Depends on: `GBX-010`, `GBX-011`
- Goal: encode the event-sourced contract in typed Pydantic models
- Deliverables:
  - `EventEnvelope`
  - event payload base type
  - all first-pass event payload models listed in the architecture doc
  - discriminated event union or equivalent robust dispatch strategy
- Implementation notes:
  - make versioning explicit
  - ensure the discriminator strategy is stable and testable
  - include correlation fields derivable from payloads
- Tests and validation included in task:
  - serialization and deserialization tests for representative event types
  - tests proving unsupported or malformed event payloads fail cleanly
  - tests for event version defaults
- Done when:
  - event models can be safely persisted and reconstructed

---

## Phase 2: Persistence And Projection Engine

### GBX-020: Implement SQLite Connection And Migration Bootstrap

- Status: `DONE`
- Depends on: `GBX-003`, `GBX-012`
- Goal: create the storage bootstrap layer for SQLite
- Deliverables:
  - `src/glassbox/store/sqlite.py`
  - migration bootstrap mechanism or schema initializer
  - connection configuration suitable for local-first async usage
- Implementation notes:
  - decide whether migrations are handwritten SQL files or a lightweight internal migrator
  - enforce foreign keys and sane pragmas deliberately
- Tests and validation included in task:
  - unit or integration tests that create a fresh database and verify schema initialization
  - tests that repeated initialization is idempotent
- Done when:
  - a fresh DB can be created from code in a temporary directory during tests

### GBX-021: Implement Canonical Event Store

- Status: `DONE`
- Depends on: `GBX-020`
- Goal: persist and retrieve append-only events as the source of truth
- Deliverables:
  - append API
  - read-by-session API
  - read-after-sequence API for streaming and resume
  - retrieval by correlation IDs where needed
- Implementation notes:
  - append semantics must guarantee monotonically increasing per-session sequence values
  - store both raw payload JSON and denormalized correlation fields
  - keep DB writes transactional
- Tests and validation included in task:
  - integration tests for append ordering
  - tests for duplicate `event_id` rejection
  - tests for reading events in correct order
- Done when:
  - events can be appended and replayed deterministically from SQLite

### GBX-022: Implement Session Metadata Store

- Status: `DONE`
- Depends on: `GBX-020`, `GBX-021`
- Goal: manage coarse session records independently from full event replay
- Deliverables:
  - create session record
  - update session metadata
  - fetch session record by ID
  - list sessions by status or recency
- Implementation notes:
  - keep `sessions.last_sequence` aligned with event append transactions
  - do not let session rows become a shadow source of truth for richer runtime state
- Tests and validation included in task:
  - integration tests for creation and updates
  - tests for correct status and sequence persistence
- Done when:
  - the CLI can list and resume sessions without replaying the entire event log first

### GBX-023: Implement Projection Table Schemas

- Status: `DONE`
- Depends on: `GBX-020`, `GBX-012`
- Goal: create the read-model tables described in `database.md`
- Deliverables:
  - `session_state`
  - `transcript_messages`
  - `tool_calls`
  - `approvals`
  - optional `turn_metrics` only if the implementation is ready to populate it
- Implementation notes:
  - keep the schema rebuildable from `events`
  - do not over-model secondary tables beyond current architecture needs
- Tests and validation included in task:
  - schema existence tests
  - migration/bootstrap tests covering all projection tables
- Done when:
  - projection tables exist and can be targeted by projection handlers

### GBX-024: Implement Projection Handlers And Rebuilder

- Status: `DONE`
- Depends on: `GBX-021`, `GBX-023`
- Goal: convert canonical events into durable query-friendly tables
- Deliverables:
  - projection application functions for each event family
  - per-session projection rebuild entrypoint
  - projection update path integrated with event append transactions or immediately after them
- Implementation notes:
  - make projection handlers deterministic and side-effect free
  - support replay from sequence 1 without special cases
- Tests and validation included in task:
  - integration tests that append a representative event stream and assert projection contents
  - tests that rebuilding projections from raw events reproduces the same read state
- Done when:
  - projection tables can be wiped and rebuilt from the event log with identical results

### GBX-025: Implement Artifact Storage Layer

- Status: `DONE`
- Depends on: `GBX-021`
- Goal: support large logs, diffs, and other file-backed artifacts without bloating the database
- Deliverables:
  - artifact path strategy
  - artifact writer and reader helpers
  - event references for artifact recording
- Implementation notes:
  - keep artifact storage session-scoped
  - be explicit about text vs binary handling
- Tests and validation included in task:
  - integration tests for artifact write, read, and event linkage
- Done when:
  - tools and runtime code can store large outputs externally while keeping metadata in the event stream

---

## Phase 3: Runtime Infrastructure

### GBX-030: Implement In-Process Event Bus

- Status: `DONE`
- Depends on: `GBX-012`
- Goal: provide pub-sub for runtime consumers such as CLI rendering and SSE streaming
- Deliverables:
  - publish API
  - subscribe API
  - backpressure or queue policy for subscribers
- Implementation notes:
  - do not let slow subscribers block canonical persistence
  - keep this bus in-process and intentionally simple in the first version
- Tests and validation included in task:
  - async tests for single and multiple subscribers
  - tests for subscriber cancellation and cleanup
- Done when:
  - runtime code can broadcast events to independent consumers reliably

### GBX-031: Implement Service Interfaces And Runtime Context Objects

- Status: `DONE`
- Depends on: `GBX-011`, `GBX-012`, `GBX-021`, `GBX-030`
- Goal: define the main orchestration interfaces before implementing full runtime behavior
- Deliverables:
  - session service protocol or abstract service layer
  - runtime context container(s)
  - repository/service dependency wiring contracts
- Implementation notes:
  - keep services narrow and testable
  - do not bury control flow in ad hoc globals
- Tests and validation included in task:
  - unit tests for service construction and dependency contracts where helpful
- Done when:
  - CLI, runtime, and web layers can depend on explicit service boundaries

### GBX-032: Implement Session Supervisor

- Status: `DONE`
- Depends on: `GBX-022`, `GBX-024`, `GBX-030`, `GBX-031`
- Goal: create the top-level session lifecycle manager
- Deliverables:
  - start session
  - load or resume session
  - stop session
  - submit user input into a session
- Implementation notes:
  - session supervisor should own lifecycle and delegation, not model/tool internals
  - session startup should create initial records and emit `SessionStarted`
- Tests and validation included in task:
  - integration tests for session creation and resume
  - tests for invalid state transitions such as input into completed sessions
- Done when:
  - a session can be created and loaded through service APIs without the CLI layer

### GBX-033: Implement Context Builder

- Status: `DONE`
- Depends on: `GBX-011`, `GBX-024`, `GBX-032`
- Goal: assemble the runtime context used for each model turn
- Deliverables:
  - prompt context builder
  - transcript summarization or formatting helpers as needed
  - tool schema inclusion helpers
- Implementation notes:
  - use stable typed summaries rather than raw runtime objects
  - keep context building distinct from model invocation
- Tests and validation included in task:
  - unit tests for context assembly using fixture sessions
  - tests proving ordering and content inclusion rules
- Done when:
  - a turn can derive structured model context from persisted session state

---

## Phase 4: CLI Vertical Slice

### GBX-040: Implement Minimal CLI Entry Point

- Status: `DONE`
- Depends on: `GBX-032`
- Goal: expose a working `glassbox` command with at least one executable path
- Deliverables:
  - `glassbox run`
  - minimal argument parsing
  - runtime wiring bootstrap
- Implementation notes:
  - pick a CLI library deliberately; if none is needed yet, keep the first interface simple
  - do not prematurely build a complicated subcommand tree
- Tests and validation included in task:
  - CLI smoke tests for process exit codes and help output
- Done when:
  - a user can invoke the CLI and create a baseline session

### GBX-041: Implement CLI Renderer Backed By Events

- Status: `DONE`
- Depends on: `GBX-030`, `GBX-040`
- Goal: render terminal output from runtime events rather than ad hoc prints
- Deliverables:
  - event-to-terminal rendering layer
  - concise rendering for session start, tool progress, approvals, and assistant output
- Implementation notes:
  - keep renderer decoupled from event production
  - ensure streamed content is readable without corrupting terminal output
- Tests and validation included in task:
  - unit tests for event rendering decisions
  - integration tests that assert representative terminal output for a fake event stream
- Done when:
  - the CLI reflects runtime progress using the event bus

### GBX-042: Implement Session-Oriented CLI Commands

- Status: `DONE`
- Depends on: `GBX-040`, `GBX-041`
- Goal: add the operator command surface described in the architecture doc
- Deliverables:
  - `glassbox resume`
  - `glassbox status`
  - `glassbox approve`
  - `glassbox deny`
- Implementation notes:
  - wire commands through services, not directly to DB code
  - keep output stable enough for humans, but avoid making it parse-first unless there is a requirement
- Tests and validation included in task:
  - CLI integration tests for each command path
  - negative-path tests for unknown session IDs and invalid approval states
- Done when:
  - core operator workflows are reachable from the terminal

---

## Phase 5: LLM Integration And Turn Engine

### GBX-050: Implement Model Adapter Layer

- Status: `DONE`
- Depends on: `GBX-012`, `GBX-033`
- Goal: isolate `pydantic-ai` integration behind a stable internal adapter
- Deliverables:
  - `src/glassbox/llm/adapters.py`
  - provider/model configuration handling
  - translation between internal context and model request structures
- Implementation notes:
  - keep provider specifics out of runtime orchestration logic
  - design for streaming support from the start
- Tests and validation included in task:
  - unit tests with fake provider behavior or stubs
  - tests for request assembly and structured tool-call translation
- Done when:
  - runtime code can call the model layer without knowing provider details

### GBX-051: Implement Prompt Templates And Policy-Aware System Prompt

- Status: `DONE`
- Depends on: `GBX-033`, `GBX-050`
- Goal: encode the baseline model instructions for Glassbox behavior
- Deliverables:
  - system prompt builder
  - reusable prompt fragments for tool usage, approvals, and output style
- Implementation notes:
  - prompts should reflect the event-driven, tool-mediated architecture
  - ensure policy constraints are visible to the model
- Tests and validation included in task:
  - unit tests for prompt composition and inclusion of policy/tool instructions
- Done when:
  - the runtime can build a stable model prompt from typed context and policy inputs

### GBX-052: Implement Turn Engine Without Tool Execution

- Status: `DONE`
- Depends on: `GBX-032`, `GBX-033`, `GBX-050`, `GBX-051`
- Goal: create the minimal multi-turn control plane before enabling tools
- Deliverables:
  - turn start and completion flow
  - model invocation path
  - assistant message event emission for non-tool responses
  - turn state transitions
- Implementation notes:
  - emit all lifecycle events explicitly
  - keep the engine resumable at event boundaries
- Tests and validation included in task:
  - integration tests for a user message producing a complete assistant response
  - tests for event ordering through the turn lifecycle
- Done when:
  - a prompt can flow through session supervisor, turn engine, model adapter, and event store successfully

### GBX-053: Implement Streaming Assistant Output Events

- Status: `DONE`
- Depends on: `GBX-052`, `GBX-030`
- Goal: support incremental model output in the runtime, CLI, and projections
- Deliverables:
  - `AssistantMessageStarted`
  - `AssistantMessageDelta`
  - `AssistantMessageCompleted`
  - transcript projection updates for streaming messages
- Implementation notes:
  - preserve correct final transcript assembly
  - ensure streaming is optional and does not break fallback non-streaming behavior
- Tests and validation included in task:
  - integration tests asserting message delta event sequences
  - projection tests for assembling final message content from deltas
- Done when:
  - model output can be streamed end-to-end and reconstructed into stable transcript state

---

## Phase 6: Tool Framework And Initial Safe Tools

### GBX-060: Implement Tool Specification And Registry

- Status: `DONE`
- Depends on: `GBX-011`, `GBX-012`, `GBX-031`
- Goal: create the typed tool contract and discovery mechanism
- Deliverables:
  - base tool interface
  - registry of available tools
  - tool schema export for model usage
- Implementation notes:
  - tools must declare input model, output model, risk level, and streaming behavior
  - keep registration explicit rather than magical
- Tests and validation included in task:
  - unit tests for tool registration and duplicate-name rejection
  - tests for schema export correctness
- Done when:
  - the runtime can enumerate tools and their typed contracts

### GBX-061: Implement Policy Engine

- Status: `DONE`
- Depends on: `GBX-060`
- Goal: separate authorization policy from tool implementation
- Deliverables:
  - policy decision models
  - rules for safe, confirm, and blocked operations
  - workspace scoping checks
- Implementation notes:
  - start with local policy only; avoid full sandbox design in v1
  - policy outputs should be easy to emit as events and show in the dashboard
- Tests and validation included in task:
  - unit tests for representative safe, confirm, and blocked decisions
  - tests for path scoping and destructive command rejection
- Done when:
  - the runtime can evaluate tool requests consistently before execution

### GBX-062: Implement Read-Only File And Directory Tools

- Status: `DONE`
- Depends on: `GBX-060`, `GBX-061`
- Goal: deliver the first useful safe tools
- Deliverables:
  - `list_dir`
  - `read_file`
  - `search_files`
- Implementation notes:
  - scope all filesystem access to the workspace or approved session cwd
  - keep tool outputs compact and structured
- Tests and validation included in task:
  - unit and integration tests for happy-path and scoped denial cases
  - tests for output model validation
- Done when:
  - the model can safely inspect the repository through typed tools

### GBX-063: Implement Tool Runtime Execution Loop

- Status: `DONE`
- Depends on: `GBX-052`, `GBX-060`, `GBX-061`, `GBX-062`
- Goal: let the turn engine execute model-requested tools and continue the loop
- Deliverables:
  - tool call request handling
  - policy evaluation path
  - tool execution lifecycle events
  - tool result handoff back into the turn engine
- Implementation notes:
  - separate model request interpretation from actual execution
  - keep tool lifecycle observable in events
- Tests and validation included in task:
  - integration tests for a turn that uses one read-only tool before completing
  - tests for blocked tool requests and policy-driven behavior
- Done when:
  - a model tool call can execute and the assistant can continue with the tool result

### GBX-064: Implement Command Runner Tool With Streaming Output

- Status: `DONE`
- Depends on: `GBX-061`, `GBX-063`, `GBX-025`
- Goal: support subprocess-based operations with event streaming
- Deliverables:
  - `run_command` tool
  - subprocess output streaming to `ToolOutputChunk`
  - artifact handling for large output if needed
- Implementation notes:
  - enforce working directory and policy constraints carefully
  - ensure cancellation and non-zero exits are surfaced as explicit tool outcomes
- Tests and validation included in task:
  - integration tests for stdout/stderr streaming
  - tests for exit-code handling and blocked commands
- Done when:
  - long-running or noisy commands can be observed in real time through events

### GBX-065: Implement Git Status And Test Runner Tools

- Status: `DONE`
- Depends on: `GBX-064`
- Goal: add the first workflow-oriented tools that are still predictable and bounded
- Deliverables:
  - `git_status`
  - `run_tests`
- Implementation notes:
  - `run_tests` should likely wrap a constrained pytest invocation rather than arbitrary shell text
  - outputs should be structured enough for UI display and later reasoning
- Tests and validation included in task:
  - integration tests for both tools under fixture repos and test targets
- Done when:
  - the runtime can inspect repo state and invoke automated tests through typed tools

### GBX-066: Implement Apply Patch Tool

- Status: `DONE`
- Depends on: `GBX-061`, `GBX-063`
- Goal: support controlled file edits through a typed patch mechanism
- Deliverables:
  - `apply_patch` tool
  - patch validation and application flow
  - artifact capture for diffs or failed patch attempts where useful
- Implementation notes:
  - keep writes workspace-scoped
  - ensure failures are explicit and recoverable
- Tests and validation included in task:
  - integration tests for successful patch application
  - tests for malformed patches, conflicts, and blocked out-of-scope writes
- Done when:
  - the agent can perform controlled file edits through the tool layer

### GBX-067: Implement Ask User Tool

- Status: `DONE`
- Depends on: `GBX-060`, `GBX-063`
- Goal: support turn suspension when the model needs clarification or approval-like input
- Deliverables:
  - `ask_user` tool contract
  - session pause/resume behavior for pending operator input
- Implementation notes:
  - this is distinct from approval resolution, though the UI mechanics may overlap
  - ensure pending questions are represented in events and projections
- Tests and validation included in task:
  - integration tests for a turn that pauses for user input and resumes later
- Done when:
  - the runtime can safely stop and continue multi-turn workflows around operator answers

---

## Phase 7: Approval Workflow

### GBX-070: Implement Approval Domain And Persistence Flow

- Status: `DONE`
- Depends on: `GBX-024`, `GBX-061`
- Goal: make approvals a first-class runtime concept rather than an ad hoc conditional
- Deliverables:
  - approval event emission
  - approval projection updates
  - session state transitions into and out of `awaiting_approval`
- Implementation notes:
  - approval state must survive process restarts
  - keep approval records tied to turn and subject metadata
- Tests and validation included in task:
  - integration tests covering request, persist, deny, and approve flows
- Done when:
  - risky actions can pause the session and be resumed by an explicit approval decision

### GBX-071: Integrate Approval Resolution Into CLI And Runtime

- Status: `DONE`
- Depends on: `GBX-042`, `GBX-070`
- Goal: complete the operator-facing approval loop
- Deliverables:
  - CLI approve/deny commands wired to runtime services
  - resumed turn processing after approval resolution
- Implementation notes:
  - keep the resumed control path explicit and testable
  - denied actions should surface clear assistant-visible failure context
- Tests and validation included in task:
  - end-to-end style integration tests for risky tool requests resolved through CLI commands
- Done when:
  - the CLI can complete a real approval workflow for a pending session

---

## Phase 8: Dashboard Backend

### GBX-080: Implement Web App Bootstrap

- Status: `DONE`
- Depends on: `GBX-032`, `GBX-030`
- Goal: start an embedded HTTP server alongside the runtime
- Deliverables:
  - ASGI app bootstrap
  - application lifetime wiring for services and event subscriptions
  - `GET /healthz`
- Implementation notes:
  - choose a small ASGI framework deliberately and keep runtime logic out of routes
  - avoid separate daemon architecture in v1
- Tests and validation included in task:
  - HTTP tests for app startup and health endpoint
- Done when:
  - the runtime can host a web app inside the same process

### GBX-081: Implement Session Snapshot API

- Status: `DONE`
- Depends on: `GBX-024`, `GBX-080`
- Goal: provide the dashboard with initial read models before it subscribes to live events
- Deliverables:
  - `GET /sessions/{session_id}`
  - response schemas for session summary, transcript, active tools, and pending approvals
- Implementation notes:
  - build the response from projection tables, not direct runtime internals
- Tests and validation included in task:
  - HTTP integration tests for existing and missing sessions
  - tests proving the snapshot reflects projection state accurately
- Done when:
  - a browser client can fetch the full current session state from the server

### GBX-082: Implement SSE Event Stream API

- Status: `DONE`
- Goal: stream live session events to the dashboard
- Deliverables:
  - `GET /sessions/{session_id}/events`
  - resume-from-sequence or equivalent reconnect behavior
  - event serialization contract for the browser
- Implementation notes:
  - support clients reconnecting without replaying the whole session unnecessarily
  - keep event framing stable and easy to parse in the browser
- Tests and validation included in task:
  - integration tests for SSE connection, event delivery, and reconnect semantics
- Done when:
  - the dashboard can subscribe to live session updates reliably

### GBX-083: Implement Approval Resolution HTTP Endpoint

- Status: `DONE`
- Depends on: `GBX-070`, `GBX-080`
- Goal: allow the dashboard to resolve approvals without going through the CLI
- Deliverables:
  - `POST /sessions/{session_id}/approvals/{approval_id}`
  - request schema for approve/deny actions
- Implementation notes:
  - share service-layer approval logic with the CLI path
  - keep authorization assumptions local-first and explicit
- Tests and validation included in task:
  - HTTP integration tests for approve and deny flows
- Done when:
  - approval workflows can be completed from the browser as well as the terminal

---

## Phase 9: Dashboard Frontend

### GBX-090: Select Frontend Delivery Strategy And Scaffold Dashboard Assets

- Status: `DONE`
- Depends on: `GBX-080`
- Goal: establish how the dashboard frontend is built and served
- Deliverables:
  - frontend build approach and asset pipeline
  - initial page shell served by the web app
- Implementation notes:
  - keep the first version operationally simple
  - do not overbuild a separate SPA architecture unless it clearly pays for itself
- Tests and validation included in task:
  - asset serving tests or integration checks for the dashboard shell
- Done when:
  - the web server can serve a working dashboard page

### GBX-091: Implement Dashboard State Model And Event Reducer

- Status: `DONE`
- Depends on: `GBX-081`, `GBX-082`, `GBX-090`
- Goal: build the browser-side state model from snapshot plus live event stream
- Deliverables:
  - client state types
  - snapshot hydration logic
  - event reducer for incremental updates
- Implementation notes:
  - mirror the event-sourced projection mindset in the browser
  - keep reducer logic deterministic and testable
- Tests and validation included in task:
  - frontend unit tests for reducer behavior on representative events
- Done when:
  - the browser can stay in sync from initial snapshot plus SSE events

### GBX-092: Implement Core Dashboard Panes

- Status: `DONE`
- Depends on: `GBX-091`
- Goal: surface the minimum useful “view into the brain” UI
- Deliverables:
  - transcript timeline pane
  - current turn status pane
  - active tool calls pane
  - live command output pane
  - pending approvals pane
  - event log pane
- Implementation notes:
  - keep visual priority on current agent activity, not just chat history
  - design the UI for desktop first but keep it functional on smaller screens
- Tests and validation included in task:
  - frontend component tests for pane rendering with realistic state fixtures
  - integration test for multi-pane updates from a synthetic event stream
- Done when:
  - the dashboard provides a useful operational view into an active session

### GBX-093: Implement Dashboard Approval Actions

- Status: `DONE`
- Depends on: `GBX-083`, `GBX-092`
- Goal: make approvals actionable in the browser
- Deliverables:
  - approve and deny controls
  - optimistic or confirmed update behavior
  - visible resolution state changes
- Implementation notes:
  - keep browser behavior consistent with CLI approval semantics
- Tests and validation included in task:
  - frontend integration tests for approval actions and resulting state updates
- Done when:
  - an operator can resolve a pending approval from the dashboard and see the session continue

---

## Phase 10: Resume, Replay, And Recovery

### GBX-100: Implement Session Resume From Persisted State

- Status: `DONE`
- Depends on: `GBX-032`, `GBX-024`, `GBX-042`
- Goal: resume stopped or restarted sessions safely
- Deliverables:
  - session load path from persisted metadata and projections
  - runtime bootstrap from existing session data
  - handling for awaiting-approval and mid-transcript sessions
- Implementation notes:
  - decide explicitly what kinds of in-flight state are resumable in v1
  - avoid pretending subprocesses can resume if they cannot; surface clear semantics instead
- Tests and validation included in task:
  - integration tests for resuming completed, active, and awaiting-approval sessions
- Done when:
  - the operator can restart the process and continue working with prior sessions

### GBX-101: Implement Projection Rebuild Command Or Service Path

- Status: `DONE`
- Depends on: `GBX-024`, `GBX-100`
- Goal: recover derived state from the canonical event log on demand
- Deliverables:
  - rebuild API or CLI command
  - safe rebuild behavior for one session and optionally all sessions
- Implementation notes:
  - this is a recovery and debugging primitive, not a normal user workflow
  - keep rebuild deterministic and auditable
- Tests and validation included in task:
  - integration tests wiping projection rows and restoring them from `events`
- Done when:
  - the system can recover correct projections after corruption or schema changes

### GBX-102: Implement Checkpoint Strategy If Needed

- Status: `DONE`
- Depends on: `GBX-100`, `GBX-101`
- Goal: add checkpoints only if replay cost or resume complexity justifies them
- Deliverables:
  - checkpoint schema and storage if adopted
  - checkpoint read path and invalidation rules
- Implementation notes:
  - this task is conditional, not mandatory for the first usable release
  - do not add checkpoints unless there is a demonstrated need
  - closed as unnecessary for v1 because projections already cover read-heavy access,
    SSE reconnect replays only events after a known sequence, and resume behavior does
    not currently require snapshot restoration
- Tests and validation included in task:
  - tests for checkpoint creation and replay fallback behavior if checkpoints are used
- Done when:
  - either checkpoints exist with full tests, or the task is explicitly closed as unnecessary for v1

---

## Phase 11: Observability And Operator Ergonomics

### GBX-110: Implement Runtime Metrics Projection

- Status: `DONE`
- Depends on: `GBX-024`, `GBX-053`, `GBX-064`
- Goal: persist useful latency and token metrics for runtime introspection
- Deliverables:
  - metrics projection updates from model and tool events
  - service accessors for metrics in snapshot responses
- Implementation notes:
  - keep metric scope aligned with actual operator value
  - avoid premature metrics complexity or external observability systems
- Tests and validation included in task:
  - projection tests for token and duration aggregation
- Done when:
  - the dashboard can show useful per-turn metrics derived from persisted events

### GBX-111: Improve CLI Session Status And Inspection Views

- Status: `DONE`
- Depends on: `GBX-042`, `GBX-110`
- Goal: make terminal inspection useful even without the dashboard
- Deliverables:
  - richer `glassbox status`
  - current turn, approvals, and recent tool activity summaries
- Implementation notes:
  - this should read from projections or services, not reconstruct state ad hoc
- Tests and validation included in task:
  - CLI integration tests covering status output against seeded session data
- Done when:
  - a user can inspect a session meaningfully from the terminal alone

### GBX-112: Implement Structured Runtime Logging For Debugging

- Status: `DONE`
- Depends on: `GBX-032`, `GBX-080`
- Goal: provide internal logs for debugging without turning logs into the primary product interface
- Deliverables:
  - structured logs for key runtime actions
  - correlation with session and turn IDs
- Implementation notes:
  - logs complement events; they do not replace them
  - keep logs terse and operationally useful
- Tests and validation included in task:
  - tests where practical for log context emission
  - at minimum, smoke coverage that logging configuration does not break runtime startup
- Done when:
  - debugging internal failures is easier without relying only on raw print output

---

## Phase 12: Documentation And Developer Workflow

### GBX-120: Write Getting Started Documentation

- Status: `DONE`
- Depends on: `GBX-002`, `GBX-040`
- Goal: document how to install, run, and validate the project locally
- Deliverables:
  - setup steps using `uv`
  - basic CLI usage
  - local validation commands
- Implementation notes:
  - keep docs aligned with actual commands in the repo
- Tests and validation included in task:
  - manually verify documented commands against the actual project state while writing
- Done when:
  - a fresh developer can get the project running from the docs

### GBX-121: Keep Architecture And Database Docs In Sync With Code

- Status: `DONE`
- Depends on: ongoing, starts after `GBX-020`
- Goal: prevent the docs from drifting away from implementation reality
- Deliverables:
  - updates to [architecture.md](./architecture.md) and [database.md](./database.md) whenever contracts materially change
- Implementation notes:
  - this is a continuous task attached to implementation milestones, not a one-time batch rewrite
- Tests and validation included in task:
  - doc review against code during each relevant feature task
- Done when:
  - the main docs remain trustworthy as implementation references

### GBX-122: Document Tool Policy And Approval Semantics

- Status: `DONE`
- Depends on: `GBX-061`, `GBX-070`
- Goal: make operator expectations around safety and approvals explicit
- Deliverables:
  - policy documentation
  - examples of safe, confirm, and blocked actions
  - approval lifecycle description for CLI and dashboard
- Implementation notes:
  - docs should reflect actual implemented policy, not aspirational policy
- Tests and validation included in task:
  - manual verification against integration-tested behavior while authoring
- Done when:
  - operators can predict how the runtime will treat risky actions

---

## Phase 13: End-To-End Release Readiness

### GBX-130: Add End-To-End Scenario Coverage For Core Flows

- Status: `DONE`
- Depends on: `GBX-042`, `GBX-063`, `GBX-082`, `GBX-100`
- Goal: cover the main user journeys across runtime, CLI, persistence, and dashboard backend
- Deliverables:
  - e2e tests for:
    - start session and get assistant response
    - tool-assisted turn
    - approval-required turn
    - session resume
    - dashboard snapshot plus event stream behavior
- Implementation notes:
  - keep the scenarios few but representative
  - use deterministic fakes for model behavior where possible
- Tests and validation included in task:
  - this task is itself the test suite, but it still requires lint and typecheck on touched code
- Done when:
  - core operator journeys are protected against regression

### GBX-131: Harden Error Paths And Failure Recovery

- Status: `DONE`
- Depends on: `GBX-130`
- Goal: ensure the system fails visibly and recoverably under expected local errors
- Deliverables:
  - improved handling for model failure, DB write failure, projection failure, and tool failure
  - explicit error events and operator-visible status updates where missing
- Implementation notes:
  - focus on failures that are realistic in local use
  - do not hide partial failure states
- Tests and validation included in task:
  - integration tests for each major failure class that is handled
- Done when:
  - the system degrades predictably under expected operational faults

### GBX-132: Final Packaging And Operator Polish

- Status: `DONE`
- Depends on: `GBX-130`, `GBX-131`, `GBX-120`, `GBX-122`
- Goal: make the project coherent and usable as a first serious release candidate
- Deliverables:
  - packaging cleanup
  - final CLI help text refinement
  - dashboard startup ergonomics
  - removal of leftover experimental scaffolding
- Implementation notes:
  - keep polish changes small and grounded in actual operator friction
- Tests and validation included in task:
  - full repo validation using the standard command set
  - e2e rerun after polish changes
- Done when:
  - the repo is in a state where ongoing feature work can proceed on top of a coherent baseline

---

## Phase 14: Real Provider Connectivity

### GBX-140: Add Runtime Provider Config Resolution From Environment And `.env`

- Status: `DONE`
- Depends on: `GBX-050`, `GBX-120`
- Goal: resolve provider credentials and runtime-only model settings without persisting secrets into session data
- Deliverables:
  - runtime config loader for provider credentials and non-secret provider options
  - support for process environment variables
  - support for loading a local `.env` file from the workspace runtime path
  - explicit precedence rules between process environment and `.env` values
- Implementation notes:
  - do not store secrets in `SessionConfig`, `SessionRecord`, events, or projection tables
  - start with environment variables as the canonical config surface; `.env` is a local convenience layer
  - document and enforce precedence as: explicit process environment overrides `.env`
  - keep the loader provider-agnostic, but define initial key names for at least OpenAI and Anthropic
- Tests and validation included in task:
  - unit tests for env resolution precedence
  - tests for missing `.env`, ignored comments, and malformed entries
  - tests proving secrets are not written into persisted session metadata
- Done when:
  - the runtime can resolve provider credentials and options from env / `.env` without changing persistence schema

### GBX-141: Implement Real `pydantic-ai` Provider Executor Factory

- Status: `DONE`
- Depends on: `GBX-140`
- Goal: replace the hardcoded local function-model runtime path with a real provider-backed executor path while preserving the deterministic local executor for tests and offline development
- Deliverables:
  - executor factory for provider-qualified models such as `openai:gpt-5.4` and `anthropic:claude-sonnet-4`
  - bootstrap wiring that chooses between local deterministic executor and provider-backed executor
  - provider/model resolution logic that stays behind the existing adapter / executor boundary
- Implementation notes:
  - keep `TurnEngine` unaware of provider-specific initialization details
  - prefer using `pydantic-ai` model inference or provider model types rather than introducing a separate provider client layer first
  - support streaming where the provider and `pydantic-ai` model support it, with graceful fallback to non-streaming execution
  - the initial provider scope should be OpenAI and Anthropic only
- Tests and validation included in task:
  - unit tests for provider/model resolution from stored `model_name`
  - tests for local fallback executor selection
  - tests proving executor construction stays deterministic under monkeypatched provider factories
- Done when:
  - Glassbox can build a real provider-backed model executor without breaking the current local executor path

### GBX-142: Surface Provider Config And Auth Failures Cleanly

- Status: `DONE`
- Depends on: `GBX-131`, `GBX-140`, `GBX-141`
- Goal: make missing credentials, unsupported providers, and invalid provider runtime config fail visibly and safely for operators
- Deliverables:
  - explicit failure classification for provider auth and config errors
  - operator-visible CLI and dashboard error surfaces for provider bootstrap failures
  - `SessionFailed` integration for terminal session-scoped provider failures where appropriate
- Implementation notes:
  - distinguish between recoverable turn failures and terminal runtime/config failures
  - never echo raw secret values in logs, events, CLI output, or dashboard state
  - unsupported provider names and missing required credentials should fail before any remote request is attempted
- Tests and validation included in task:
  - integration tests for missing API key, unsupported provider, and malformed provider config
  - tests proving secrets are redacted from surfaced error messages
  - validation that runtime failures land in the expected session or turn failure path
- Done when:
  - an operator gets a precise non-secret error when provider config is missing or invalid

### GBX-143: Document Real Provider Setup And Secret Handling

- Status: `DONE`
- Depends on: `GBX-140`, `GBX-141`, `GBX-142`, `GBX-121`
- Goal: document how to run Glassbox against real providers using environment variables and `.env` files without implying that secrets are persisted
- Deliverables:
  - README setup instructions for supported providers
  - documentation for required environment variables and `.env` support
  - explicit note that secrets remain runtime-only and are not stored in SQLite
  - troubleshooting guidance for auth and config errors
- Implementation notes:
  - keep examples aligned with the actual supported provider set
  - include one documented path for deterministic local execution and one for real provider execution
  - avoid documenting speculative secret stores before they exist
- Tests and validation included in task:
  - manual verification of documented setup steps against the implementation
  - doc review against runtime config code paths and failure messages
- Done when:
  - a developer can configure a real provider from docs alone without guessing where secrets belong

### GBX-144: Add Non-Network Regression Coverage For Provider Mode

- Status: `DONE`
- Depends on: `GBX-141`, `GBX-142`
- Goal: protect provider-mode behavior without requiring live provider calls in CI
- Deliverables:
  - integration coverage for env / `.env` provider config resolution into runtime bootstrap
  - tests for provider-mode executor selection under fake or monkeypatched `pydantic-ai` model factories
  - regression coverage for streamed and non-streamed provider execution paths where feasible
- Implementation notes:
  - do not introduce network-coupled tests into the baseline suite
  - continue using monkeypatched executor builders and deterministic fakes for behavioral coverage
  - focus on Glassbox wiring and contract behavior, not provider SDK correctness
- Tests and validation included in task:
  - integration tests for provider-mode runtime bootstrap
  - tests for `.env` loading behavior in a temporary workspace
  - full repo validation after the provider-mode wiring lands
- Done when:
  - the real-provider path is regression-tested in CI without depending on external APIs

---

## Phase 15: Multi-Turn User Interaction UX

### GBX-150: Add CLI Command For Submitting A New User Turn To An Existing Session

- Status: `DONE`
- Depends on: `GBX-042`, `GBX-032`
- Goal: let an operator send another user prompt into a running session without dropping to an ad hoc Python snippet
- Deliverables:
  - a dedicated CLI command for submitting a new user message to an existing session
  - argument and help text covering `session_id`, prompt text, and runtime location flags
  - clear operator-visible errors for completed, failed, or otherwise non-interactive sessions
- Implementation notes:
  - wire the command through `session_service.submit_user_message(...)`
  - keep command naming explicit and session-oriented rather than overloading `resume`
  - preserve the event-rendered CLI experience during the resulting turn
- Tests and validation included in task:
  - CLI integration tests for happy-path message submission into an existing running session
  - negative-path tests for unknown session IDs and non-interactive session states
- Done when:
  - an operator can advance an existing session with a new user prompt entirely through the CLI

### GBX-151: Add CLI Command For Answering Pending `ask_user` Questions

- Status: `DONE`
- Depends on: `GBX-067`, `GBX-150`
- Goal: make suspended `ask_user` turns resumable from the terminal without custom scripts or direct service calls
- Deliverables:
  - a CLI command for submitting an answer to a pending question in a session
  - command help text describing required identifiers and expected operator workflow
  - operator-visible conflict and missing-question errors
- Implementation notes:
  - wire the command through `session_service.provide_user_answer(...)`
  - keep answer submission distinct from approval resolution, even if the surface feels similar
  - make the CLI output clear about whether the answer resumed the suspended turn successfully
- Tests and validation included in task:
  - CLI integration tests for answering a pending `ask_user` question and resuming the turn
  - negative-path tests for invalid question IDs or sessions that are not awaiting user input
- Done when:
  - the full `ask_user` pause/resume loop is operable from the CLI alone

### GBX-152: Add HTTP Endpoints For Session Messages And User Answers

- Status: `DONE`
- Depends on: `GBX-080`, `GBX-081`, `GBX-083`, `GBX-150`, `GBX-151`
- Goal: expose the same multi-turn interaction surfaces to the dashboard backend that the CLI now supports
- Deliverables:
  - `POST /sessions/{session_id}/messages`
  - `POST /sessions/{session_id}/questions/{question_id}` or equivalent answer-submission endpoint
  - request and response schemas for prompt submission and question answers
- Implementation notes:
  - share service-layer logic with the CLI paths; do not fork state transition rules in the route handlers
  - keep HTTP conflict semantics explicit for sessions that are not currently actionable
  - use the existing snapshot and SSE endpoints for follow-on state observation rather than inventing a second live-update mechanism
- Tests and validation included in task:
  - HTTP integration tests for successful message submission and question-answer submission
  - HTTP negative-path tests for unknown sessions, missing questions, and invalid session state transitions
- Done when:
  - browser-facing clients can advance a session or answer a pending question through stable backend endpoints

### GBX-153: Implement Dashboard Composer And Pending-Question UX

- Status: `DONE`
- Depends on: `GBX-091`, `GBX-092`, `GBX-152`
- Goal: let an operator continue a session directly from the dashboard with clear affordances for both new prompts and `ask_user` answers
- Deliverables:
  - dashboard input composer for submitting a new user turn
  - pending-question UI for answering `ask_user` prompts
  - loading, disabled, and post-submit states aligned with live session status
- Implementation notes:
  - distinguish clearly between “send a new prompt”, “answer the model’s question”, and approval actions
  - keep the reducer and snapshot hydration logic authoritative for when each control should be enabled
  - ensure the UI remains usable when the session is running, awaiting approval, awaiting user input, completed, or failed
- Tests and validation included in task:
  - frontend reducer and component tests for actionable-state transitions
  - integration tests for dashboard submission flows backed by mocked HTTP endpoints and SSE updates
- Done when:
  - an operator can continue a session end-to-end from the dashboard without switching to the terminal

### GBX-154: Improve Interaction Status Surfaces And Documentation For Multi-Turn Workflows

- Status: `DONE`
- Depends on: `GBX-150`, `GBX-151`, `GBX-152`, `GBX-153`, `GBX-121`
- Goal: make the available next action obvious in both terminal and dashboard workflows, and document the supported interaction model clearly
- Deliverables:
  - richer `glassbox status` output for actionable next steps such as pending approvals, pending questions, or ready-for-next-prompt sessions
  - dashboard copy or affordance refinements where state is currently implicit
  - docs covering the multi-turn operator workflow across CLI and dashboard
- Implementation notes:
  - keep status messaging tightly aligned with actual actionable state, not heuristic guesses
  - document the distinction between resuming a session, submitting a new prompt, answering a pending question, and resolving an approval
- Tests and validation included in task:
  - CLI integration tests for the updated status messaging
  - doc review against the implemented command surface and HTTP/UI flows
- Done when:
  - an operator can tell what the next valid action is for any paused or running session without reading source code

---

## Phase 16: Interactive Terminal Session UX

### GBX-160: Define Interactive CLI Session Architecture And Operator Semantics

- Status: `DONE`
- Depends on: `GBX-041`, `GBX-100`, `GBX-154`, `GBX-121`
- Goal: define the first-class interactive terminal workflow so Glassbox can behave like a persistent conversational agent without breaking the current event-sourced architecture
- Deliverables:
  - architecture and operator-workflow updates covering an interactive terminal mode for new and existing sessions
  - explicit command surface proposal for `glassbox chat` and `glassbox attach SESSION_ID`
  - documented semantics for how interactive input maps onto existing session actions such as new prompt submission, `ask_user` answers, and approval resolution
  - explicit scope boundary for v1 interactive mode versus later cross-process or daemon-backed attach behavior
- Implementation notes:
  - keep the session service and event model authoritative; the interactive CLI should be a long-lived client over existing runtime services, not a second runtime stack
  - preserve the current non-interactive commands as scriptable primitives even after the interactive mode exists
  - document that the first version keeps the runtime and event bus in-process, so live interactive streaming only exists while the owning CLI process is alive
  - update `architecture.md` if any lifecycle or operator workflow descriptions currently imply a batch-only CLI model
- Tests and validation included in task:
  - doc review against the implemented CLI and runtime boundaries before coding starts
  - manual verification that the planned command semantics do not contradict current `message`, `answer`, `approve`, `deny`, `resume`, and dashboard behavior
- Done when:
  - the repo has a clear, code-aligned design for interactive terminal sessions and an explicit v1/v2 scope boundary

### GBX-161: Add Persistent `glassbox chat` Command For New Interactive Sessions

- Status: `DONE`
- Depends on: `GBX-160`
- Goal: let an operator start a session and stay inside a long-lived terminal conversation instead of restarting the CLI for each turn
- Deliverables:
  - `glassbox chat [PROMPT]` command or equivalent interactive entrypoint for new sessions
  - persistent terminal loop that keeps the renderer subscription alive across multiple turns
  - prompt/read-eval loop that accepts operator input after the session becomes actionable again
  - exit path that leaves session state persisted and resumable
- Implementation notes:
  - reuse the existing renderer and session service rather than inventing a second terminal output path
  - keep the first interactive prompt model simple: when the session is idle and running, freeform user input should submit a new user message
  - avoid requiring a second terminal or manual session ID copying during the normal interactive flow
  - do not remove or overload `glassbox run`; `chat` should be the interactive UX layer, while `run` remains a simple non-interactive primitive
- Tests and validation included in task:
  - CLI integration tests for starting a new interactive session, submitting multiple prompts, and exiting cleanly
  - tests that assistant output, tool progress, and terminal prompts remain readable together
  - negative-path tests for immediate failure states during interactive startup
- Done when:
  - a user can start Glassbox once and continue a multi-turn session from the same terminal process without re-running the CLI for each prompt

### GBX-162: Add `glassbox attach SESSION_ID` For Interactive Control Of Existing Sessions

- Status: `DONE`
- Depends on: `GBX-160`, `GBX-161`
- Goal: let an operator attach an interactive terminal UI to an existing actionable session instead of using one-shot `message` or `answer` commands
- Deliverables:
  - `glassbox attach SESSION_ID` command for interactive control of an existing session
  - attach-time session inspection so the terminal loop knows whether the next operator input should be treated as a new prompt, an `ask_user` answer, or a blocked action
  - clear terminal messaging for sessions that are completed, failed, cancelled, or otherwise not attachable
- Implementation notes:
  - use persisted projections and current service-layer state rules to determine attachability; do not infer state ad hoc in the CLI loop
  - in v1, support attaching to paused or idle sessions that can be controlled from the current process; do not claim cross-process live turn streaming if the process-local event bus cannot provide it yet
  - keep `resume` distinct from `attach`; `resume` remains a lifecycle primitive after restart, while `attach` is the conversational operator UX
- Tests and validation included in task:
  - CLI integration tests for attaching to idle running sessions and awaiting-user-input sessions
  - negative-path tests for completed, failed, unknown, and currently non-attachable sessions
  - tests that attach mode reuses the same operator-visible semantics as `status` and the dashboard snapshot
- Done when:
  - an operator can reopen a persisted session in an interactive terminal workflow without manually dispatching low-level follow-up commands

### GBX-163: Unify Interactive Input Handling For Prompts, `ask_user` Answers, And Approval Commands

- Status: `DONE`
- Depends on: `GBX-161`, `GBX-162`, `GBX-154`
- Goal: make the interactive terminal prompt behave like a conversational interface that routes input to the correct existing session action automatically
- Deliverables:
  - interactive input router that sends freeform input as either a new user prompt or a pending-question answer based on current session state
  - slash-command surface for exceptional operator actions such as `/approve`, `/deny`, `/status`, `/help`, and `/exit`
  - terminal affordances that make the current expected input mode explicit before the operator types
  - hidden handling of pending `question_id` and `approval_id` details so the operator does not have to copy IDs during the normal interactive flow
- Implementation notes:
  - freeform text should map to exactly one valid action for the current state; if the state is ambiguous or blocked, the terminal must say so explicitly rather than guessing
  - keep approval resolution explicit through slash commands or an equivalent interactive confirmation flow; do not treat arbitrary freeform text as approval input
  - preserve the existing non-interactive commands as the source of truth for low-level behavior and recovery workflows
  - ensure the interactive prompt updates immediately after event-driven state changes such as approvals resolving, questions being asked, or turns completing
- Tests and validation included in task:
  - CLI integration tests for automatic routing of idle-session prompts and awaiting-user-input answers
  - tests for slash-command approval resolution, status inspection, and graceful exit
  - tests for blocked-state messaging when the session cannot currently accept freeform operator input
- Done when:
  - the interactive CLI feels conversational for normal turns while still exposing explicit control paths for approval and inspection actions

### GBX-164: Improve Terminal Rendering And Prompt Coordination For Long-Lived Interactive Sessions

- Status: `DONE`
- Depends on: `GBX-161`, `GBX-162`, `GBX-163`
- Goal: keep streamed runtime events and operator input readable together during a long-lived terminal session
- Deliverables:
  - terminal rendering coordination that avoids corrupting the active prompt while assistant deltas, tool output, approvals, or questions arrive
  - stable prompt-state summaries showing whether the operator is entering a new prompt, answering a pending question, or choosing an approval action
  - prompt redraw or equivalent behavior after streamed runtime output
- Implementation notes:
  - keep this compatible with the current event renderer rather than forking a completely separate rendering model
  - prioritize correctness and legibility over heavy terminal UI frameworks unless a framework clearly reduces complexity materially
  - ensure long-running tool output still remains observable without making operator input unusable
- Tests and validation included in task:
  - renderer and CLI integration tests for interleaved streamed output and prompt redraw behavior
  - tests for approval and `ask_user` events arriving while the interactive prompt is active
  - manual validation in a representative real-provider session with streamed output enabled
- Done when:
  - long-lived interactive use remains readable and operational even while runtime events are arriving continuously

### GBX-165: Document Interactive Terminal Workflows And CLI Positioning

- Status: `DONE`
- Depends on: `GBX-160`, `GBX-161`, `GBX-162`, `GBX-163`, `GBX-164`, `GBX-121`
- Goal: explain the new interactive CLI clearly and position the existing one-shot commands as complementary primitives instead of the primary conversational UX
- Deliverables:
  - README updates covering `glassbox chat` and `glassbox attach SESSION_ID`
  - operator guidance for when to use interactive mode versus `run`, `message`, `answer`, `approve`, `deny`, and `resume`
  - explicit documentation for slash commands and interactive approval / pending-question flows
  - notes describing the v1 limitation that interactive streaming is process-local rather than a daemon-backed cross-process attach mechanism
- Implementation notes:
  - keep docs aligned with the real implemented interaction model, especially around session ownership and attach semantics
  - show at least one example flow for starting a new session and one for attaching to an existing paused session
- Tests and validation included in task:
  - doc review against implemented command help and observed terminal behavior
  - manual verification of documented example flows against the actual CLI
- Done when:
  - a user can discover and use the interactive CLI workflow from docs alone without falling back to source inspection

### GBX-166: Evaluate And Scope Cross-Process Attach Or Daemon-Backed Interactive Sessions

- Status: `DONE`
- Depends on: `GBX-160`, `GBX-162`, `GBX-164`, `GBX-121`
- Goal: decide whether Glassbox should support a stronger attach model that can stream live session output across process boundaries like a terminal-native resident agent
- Deliverables:
  - architecture decision covering whether to keep interactive mode process-local or introduce a background runtime / attach protocol
  - explicit tradeoff analysis for using the existing HTTP snapshot and SSE surfaces versus adding a daemon or brokered runtime process
  - follow-up implementation tasks only if the stronger attach model is justified
- Implementation notes:
  - this is an evaluation and scoping task, not a commitment to daemonization in the same phase
  - treat the current in-process event bus design as a real constraint, not something to hand-wave away in docs or CLI help
  - avoid starting a daemon architecture unless the operator value materially exceeds the added complexity
- Tests and validation included in task:
  - architecture and doc review against current runtime boundaries and observed interactive UX gaps
  - if follow-up tasks are proposed, ensure they describe concrete executable slices rather than speculative platform work
- Done when:
  - the project has a deliberate, documented stance on whether true cross-process interactive attach is in scope and what concrete work would follow

---

## Phase 17: Co-Hosted Dashboard During Interactive Chat

### GBX-170: Define Co-Hosted Dashboard Semantics For `glassbox chat`

- Status: `DONE`
- Depends on: `GBX-080`, `GBX-161`, `GBX-166`, `GBX-121`
- Goal: define how an interactive chat session can expose the dashboard from the same owning process without contradicting the current process-local runtime model
- Deliverables:
  - architecture and operator-workflow updates describing a co-hosted dashboard for `glassbox chat`
  - explicit semantics for whether dashboard startup is default, opt-in, or suppressible from the CLI
  - command-surface proposal for dashboard-related `chat` flags such as host, port, or `--no-dashboard` if justified
  - explicit positioning of co-hosted dashboard behavior versus the existing standalone `glassbox serve` command
- Implementation notes:
  - keep this inside the current single-process architecture; do not introduce a second runtime or daemon-backed owner process
  - treat the embedded dashboard as a sidecar over the same runtime context and event bus that `chat` already owns
  - make it explicit that this does not change the GBX-166 decision about true cross-process interactive attach
  - define expected behavior for port conflicts, startup failures, and clean shutdown when the interactive session exits
- Tests and validation included in task:
  - doc review against current `chat`, `serve`, snapshot, and SSE behavior before coding starts
  - manual verification that the proposed semantics do not imply a second independent runtime stack
- Done when:
  - the repo has a clear, code-aligned design for chat-hosted dashboard lifecycle and operator expectations

### GBX-171: Refactor Web Server Bootstrap Into A Reusable Embedded Lifecycle

- Status: `DONE`
- Depends on: `GBX-080`, `GBX-170`
- Goal: make the existing web server startable and stoppable from inside an already-running CLI process without duplicating runtime bootstrap
- Deliverables:
  - reusable web server lifecycle abstraction for start, readiness, and shutdown
  - shared startup path that can be used by both `glassbox serve` and an embedded `chat` sidecar
  - server configuration model or equivalent typed inputs for host, port, and runtime context reuse
- Implementation notes:
  - do not open a second `RuntimeContext` when embedding the dashboard into `chat`
  - preserve the standalone `serve` command by routing it through the same lifecycle abstraction where practical
  - ensure embedded startup failures surface clear operator-visible errors instead of hanging the interactive loop
  - keep shutdown deterministic so the server does not outlive the owning interactive process
- Tests and validation included in task:
  - integration tests for server startup, readiness, and shutdown using the reusable lifecycle path
  - regression tests proving `glassbox serve` still starts the dashboard correctly after the refactor
- Done when:
  - the web server can be hosted either standalone or as an embedded component without duplicating runtime ownership

### GBX-172: Make Session Dashboard Metadata Truthful And Configurable

- Status: `DONE`
- Depends on: `GBX-032`, `GBX-170`, `GBX-171`
- Goal: ensure session metadata only advertises a dashboard URL when a live server is actually available for that session
- Deliverables:
  - runtime wiring so `SessionStarted.dashboard_url` reflects actual server availability rather than a hardcoded default
  - configuration path for dashboard host and port values used by co-hosted and standalone sessions
  - consistent session-status and snapshot behavior when no live dashboard is present
- Implementation notes:
  - avoid claiming a live dashboard URL for `chat` or `run` sessions unless the server has actually bound successfully
  - preserve compatibility with persisted sessions that may already contain historical `dashboard_url` values
  - keep the event contract stable unless a schema change is genuinely required
- Tests and validation included in task:
  - integration tests for sessions started with and without a live dashboard server
  - tests for status and snapshot behavior when the dashboard is unavailable or explicitly disabled
- Done when:
  - session metadata, CLI status output, and dashboard snapshot fields agree about whether a dashboard is live

### GBX-173: Start The Dashboard Automatically During `glassbox chat`

- Status: `DONE`
- Depends on: `GBX-161`, `GBX-164`, `GBX-170`, `GBX-171`, `GBX-172`
- Goal: make the web dashboard available while an interactive chat session is in progress without requiring a second terminal command
- Deliverables:
  - `glassbox chat` startup path that launches the dashboard sidecar in the owning process
  - operator-visible dashboard URL output during interactive startup
  - support for the dashboard control flags defined in `GBX-170`
  - shutdown wiring that stops the co-hosted server when the interactive chat session exits
- Implementation notes:
  - start the dashboard early enough that the operator can open it during the active session, but do not block the terminal loop on manual browser interaction
  - keep renderer output and dashboard-startup messaging readable together with the existing interactive prompt coordination
  - if dashboard startup is optional or can fail softly, define the exact fallback behavior and keep it explicit in terminal output
  - do not make `attach` implicitly claim the same behavior unless a later task adds it deliberately
- Tests and validation included in task:
  - CLI integration tests for `glassbox chat` with successful dashboard startup and clean shutdown
  - negative-path tests for port conflicts, startup failure, or dashboard-disabled modes
  - tests that interactive prompt routing still works while the sidecar server is running
- Done when:
  - a user can start `glassbox chat` once and immediately open the dashboard for that same live session

### GBX-174: Validate Snapshot And SSE Behavior Against An Active Chat-Owned Dashboard

- Status: `DONE`
- Depends on: `GBX-081`, `GBX-082`, `GBX-173`
- Goal: prove that the co-hosted dashboard exposes the same live session state that the interactive terminal is currently driving
- Deliverables:
  - integration coverage for snapshot access to the active chat session while the interactive loop is running
  - integration coverage for SSE event delivery during a live chat-owned session
  - regression coverage that browser observation does not interfere with terminal interaction semantics
- Implementation notes:
  - test the actual shared-runtime path rather than a synthetic second-runtime approximation
  - cover at least one multi-turn interaction while snapshot and SSE clients are connected
  - ensure approval and `ask_user` pause states remain visible and actionable from the browser view during chat
- Tests and validation included in task:
  - HTTP integration tests for session snapshot and SSE delivery against a chat-owned runtime
  - end-to-end style tests for a live chat session observed concurrently by the dashboard backend
- Done when:
  - the co-hosted dashboard is regression-tested as a faithful live view over an active interactive chat session

### GBX-175: Document Co-Hosted Dashboard Workflow And Standalone `serve` Positioning

- Status: `DONE`
- Depends on: `GBX-173`, `GBX-174`, `GBX-121`, `GBX-165`
- Goal: document how the dashboard fits into the interactive chat workflow without confusing it with daemon-backed attach or standalone dashboard use
- Deliverables:
  - README updates covering dashboard availability during `glassbox chat`
  - operator guidance for when to rely on chat-hosted dashboard behavior versus `glassbox serve`
  - troubleshooting notes for dashboard-disabled mode, port conflicts, and session shutdown behavior
  - explicit reminder that co-hosting the dashboard does not make interactive attach cross-process or daemon-backed
- Implementation notes:
  - keep examples aligned with the actual `chat` flags and startup output
  - explain how to open the current session directly in the browser, including any `?session=SESSION_ID` behavior that remains relevant
  - keep the docs honest about what survives process exit and what still requires standalone observation paths
- Tests and validation included in task:
  - doc review against implemented `chat` help text, startup messaging, and HTTP behavior
  - manual verification of the documented chat-plus-dashboard workflow against the actual CLI
- Done when:
  - an operator can discover and use the co-hosted dashboard workflow from the docs alone without guessing how it relates to `serve`

---

## Phase 18: Standalone Dashboard And Operator Ergonomics

### GBX-180: Define Standalone Dashboard Operator Model And Scope Boundary

- Status: `DONE`
- Depends on: `GBX-081`, `GBX-083`, `GBX-093`, `GBX-100`, `GBX-166`, `GBX-175`, `GBX-121`
- Goal: define what the standalone dashboard should optimize for once the co-hosted `chat` dashboard flow is complete
- Deliverables:
  - architecture and operator-workflow updates positioning `glassbox serve` as the persisted-session browser console rather than a low-level transport surface
  - explicit semantics for browsing recent sessions without already knowing a session ID
  - explicit scope boundary for browser-based recovery and observation versus unsupported browser-based terminal attach or daemon-backed runtime control
  - clear operator semantics for live, paused, completed, failed, and historical-only sessions when viewed through the standalone dashboard
- Implementation notes:
  - keep the browser workflow grounded in persisted projections and existing HTTP actions rather than inventing a second runtime control plane
  - preserve the `chat`-hosted dashboard as the best path for same-process live observation while making `serve` the durable cross-process inspection path
  - define what “actionable from the dashboard” means in standalone mode using existing prompt, answer, and approval semantics
- Tests and validation included in task:
  - architecture and doc review against the existing `chat`, `attach`, `serve`, snapshot, and SSE behavior before implementation starts
  - manual verification that the proposed standalone workflow does not contradict the GBX-166 scope decision
- Done when:
  - the repo has a clear, code-aligned design for standalone dashboard operator flows and their boundary relative to terminal-owned interactive sessions

### GBX-181: Add Session Index API For Standalone Dashboard Discovery

- Status: `DONE`
- Depends on: `GBX-022`, `GBX-024`, `GBX-080`, `GBX-111`, `GBX-180`
- Goal: let the standalone dashboard discover useful sessions directly from the backend instead of requiring a manually supplied `session_id`
- Deliverables:
  - `GET /sessions` or equivalent session-index endpoint for dashboard use
  - response schema for recent-session summaries including session ID, status, model name, cwd, update recency, and latest actionable summary
  - support for practical filtering or ordering such as recency and session status where justified
- Implementation notes:
  - build the index from persisted session metadata and projections, not from in-memory runtime ownership assumptions
  - return enough data for the browser to answer “which session should I open next?” without fetching every full snapshot first
  - avoid over-designing a search API before the initial operator workflow proves the need
- Tests and validation included in task:
  - HTTP integration tests for empty, mixed-status, and multi-session index responses
  - tests for ordering and summary-field correctness against seeded projection data
- Done when:
  - the standalone dashboard can load a useful recent-session list from a stable backend endpoint

### GBX-182: Implement Standalone Dashboard Landing Page And Session Browser

- Status: `DONE`
- Depends on: `GBX-090`, `GBX-091`, `GBX-180`, `GBX-181`
- Goal: make the standalone dashboard usable even when the operator starts at `/` with no session query parameter
- Deliverables:
  - landing-page experience that lists recent sessions and lets the operator open one without manually editing the URL
  - browser-side state and routing updates that support both “no session selected yet” and “session selected” modes cleanly
  - status chips or equivalent affordances showing whether sessions are running, awaiting input, awaiting approval, failed, completed, or otherwise inactive
- Implementation notes:
  - preserve the existing `?session=SESSION_ID` deep-link flow for direct opens from `chat` and docs
  - do not regress the current single-session dashboard path while adding the landing/index experience
  - favor a simple operator-first layout over a generic application shell
- Tests and validation included in task:
  - frontend reducer and component tests for index hydration, session selection, and no-session states
  - integration tests for loading the landing page, selecting a session, and preserving deep-link navigation
- Done when:
  - an operator can start `glassbox serve`, open the root dashboard URL, and navigate to a useful session without copying a session ID first

### GBX-183: Improve Standalone Session Summaries And Next-Action Guidance

- Status: `DONE`
- Depends on: `GBX-081`, `GBX-111`, `GBX-154`, `GBX-181`, `GBX-182`
- Goal: make it immediately clear what a selected session is waiting on and what the operator can do next from the standalone dashboard
- Deliverables:
  - operator-facing next-action summary for standalone session cards and/or the selected-session header
  - clearer presentation of pending `ask_user` input, pending approvals, failure context, and last assistant/user activity
  - snapshot or frontend summary wiring that distinguishes actionable sessions from historical-only inspection states
- Implementation notes:
  - reuse existing session-state semantics rather than inventing new browser-only notions of readiness
  - make the guidance explicit enough that an operator does not need to inspect raw event logs to choose the next step
  - keep CLI and dashboard action semantics aligned where the same session state is represented in both places
- Tests and validation included in task:
  - HTTP and/or frontend tests for summary rendering across running, awaiting-user-input, awaiting-approval, failed, completed, and idle states
  - regression tests that next-action guidance stays consistent with the underlying session snapshot state
- Done when:
  - the standalone dashboard can tell the operator what a session is waiting on and whether action is possible from the browser without guesswork

### GBX-184: Improve Standalone Live-State, Reconnect, And Historical-Session UX

- Status: `DONE`
- Depends on: `GBX-082`, `GBX-174`, `GBX-182`, `GBX-183`
- Goal: make standalone dashboard behavior understandable when a session is live, no longer live, or only historically inspectable
- Deliverables:
  - clearer browser UX for SSE connected, reconnecting, unavailable, and historical-only states
  - session-view messaging that distinguishes an unavailable live stream from a valid historical snapshot
  - route or state handling improvements for invalid, missing, or stale session selections in the standalone dashboard
- Implementation notes:
  - do not imply that standalone `serve` can recreate terminal-native attach semantics when the owning process is gone
  - treat snapshot access and live SSE state as separate operator signals and surface them independently
  - prefer explicit stale-state messaging over silent empty panes or ambiguous disconnected indicators
- Tests and validation included in task:
  - frontend integration tests for SSE disconnect, reconnect, and historical-session viewing states
  - HTTP or frontend regression tests for invalid session selection and recovery back to the session index
- Done when:
  - the standalone dashboard remains legible and trustworthy whether the selected session is actively streaming or only available as persisted history

### GBX-185: Document Standalone Dashboard Recovery And Session-Browsing Workflows

- Status: `DONE`
- Depends on: `GBX-180`, `GBX-181`, `GBX-182`, `GBX-183`, `GBX-184`, `GBX-121`
- Goal: document the standalone dashboard as the durable operator console for persisted sessions and recovery flows
- Deliverables:
  - README updates covering how to use `glassbox serve` when no active `chat` process is owning the dashboard
  - operator guidance for browsing recent sessions, reopening actionable sessions in the browser, and distinguishing live versus historical inspection
  - troubleshooting notes for invalid session IDs, disconnected SSE state, and post-`chat` session inspection
- Implementation notes:
  - keep docs explicit that standalone browser ergonomics improve discovery and recovery, but do not introduce daemon-backed terminal attach
  - show at least one example flow that begins from `glassbox serve` with no preselected session ID
  - align examples with the actual landing page, routing, and session-summary behavior implemented in this phase
- Tests and validation included in task:
  - doc review against the implemented standalone dashboard routes, index behavior, and browser affordances
  - manual verification of the documented standalone recovery flow against the actual UI and HTTP behavior
- Done when:
  - an operator can discover, inspect, and recover the right session from the standalone dashboard docs alone without guessing which URL or state transition to use

---

## Phase 19: Deterministic Replay And Eval

### GBX-190: Define Deterministic Replay And Eval Operator Model

- Status: `DONE`
- Depends on: `GBX-024`, `GBX-025`, `GBX-100`, `GBX-144`, `GBX-121`
- Goal: define what Glassbox means by deterministic replay and local evals so the implementation stays faithful to the event-sourced architecture rather than drifting into an ad hoc test harness
- Deliverables:
  - architecture and operator-workflow updates defining replay, baseline capture, and eval semantics
  - explicit distinction between:
    - historical event inspection
    - offline deterministic replay using recorded manifests and stubbed outputs
    - optional future live-provider comparison runs that are not part of the deterministic baseline
  - documented scope boundary for v1 replay coverage across transcript output, tool lifecycles, approvals, pending-question flows, and final projected state
  - replay result taxonomy such as exact match, manifest drift, behavioral drift, unsupported session, and replay failure
- Implementation notes:
  - deterministic replay in v1 should not issue live network calls, spawn real subprocesses, or mutate the workspace; it should run from persisted events plus recorded replay artifacts
  - be explicit about which fields participate in equivalence checks and which are normalized away, such as timestamps, UUIDs, and other runtime-generated identifiers
  - define how provider-backed sessions remain replayable without persisting secrets or depending on provider determinism
  - keep the initial operator story local-first and CI-friendly; do not introduce remote eval infrastructure or distributed runners in this phase
- Tests and validation included in task:
  - architecture and doc review against the current event model, artifact storage, provider config rules, and resume semantics before implementation begins
  - manual validation that the proposed replay model can cover representative sessions with tools, approvals, and `ask_user` pauses without contradicting existing runtime boundaries
- Done when:
  - the repo has a clear, code-aligned contract for what replay and eval mean, what they compare, and what is intentionally out of scope for the first implementation

### GBX-191: Capture Replay Manifests And Redacted Turn Artifacts During Live Execution

- Status: `DONE`
- Depends on: `GBX-025`, `GBX-053`, `GBX-063`, `GBX-144`, `GBX-190`
- Goal: persist the exact structured inputs and outputs needed to replay completed turns offline without consulting live providers or re-running side-effecting tools
- Deliverables:
  - replay manifest schema and storage path for turn-scoped inputs such as assembled model context, tool schemas, policy snapshot, runtime config fingerprint, and expected turn-level outputs
  - artifact capture for replay-relevant tool requests, normalized tool results, and any large blobs needed to reconstruct deterministic tool responses
  - event or service-layer linkage that lets the system discover replay artifacts for a session or turn without scanning raw files ad hoc
  - secret-redaction rules ensuring provider credentials and other runtime-only sensitive values never land in replay artifacts
- Implementation notes:
  - use the existing artifact storage layer for large manifests or replay payloads rather than bloating the canonical event rows
  - capture enough detail to compare current prompt/context assembly against the original run, not just the final assistant text
  - prefer stable, typed manifest content over opaque serialized runtime objects so replay failures are debuggable
  - fail explicitly for session elements that cannot yet be replayed deterministically rather than silently omitting them
- Tests and validation included in task:
  - integration tests proving a representative completed session writes retrievable replay manifests and artifact references
  - tests covering tool-assisted turns, approval pauses, and pending-question flows where replay capture must survive suspension and resume boundaries
  - tests proving secrets and transient runtime-only values are redacted or excluded from stored replay artifacts
- Done when:
  - a finished session contains enough structured replay data for offline comparison without hitting external systems

### GBX-192: Implement Offline Deterministic Replay Runner

- Status: `DONE`
- Depends on: `GBX-050`, `GBX-063`, `GBX-100`, `GBX-141`, `GBX-191`
- Goal: re-execute a persisted session offline against recorded manifests and stubbed model/tool outputs so Glassbox can verify control-flow and projection determinism under the current codebase
- Deliverables:
  - replay runner service that loads a replayable session or exported replay bundle and executes it through a deterministic runtime path
  - replay-specific model and tool executors that serve recorded outputs instead of making live provider requests or performing real side effects
  - normalized replay result model covering transcript messages, tool call timeline, approval and question state transitions, emitted event families, and final projected session state
  - replay failure reporting for missing artifacts, unsupported event versions, incompatible manifests, or drift detected before playback can continue
- Implementation notes:
  - drive as much of the real runtime orchestration as possible so replay exercises the current control plane rather than a separate toy interpreter
  - compare normalized behavior rather than raw event envelopes; timestamps, sequence allocation, and fresh identifiers should not create false drift
  - if current context building or policy evaluation no longer reproduces the recorded manifest shape, report that as manifest drift before injecting recorded outputs
  - keep replay isolated from live session ownership and event-bus side effects so running a replay cannot mutate the source session
- Tests and validation included in task:
  - integration tests replaying representative sessions that include pure assistant turns, tool-assisted turns, approval gating, and `ask_user` suspension/resume behavior
  - regression tests that replayed projected state matches the original normalized projected state for supported sessions
  - negative-path tests for missing artifacts, unsupported schemas, and intentionally corrupted replay bundles
- Done when:
  - Glassbox can replay a supported session offline and determine whether current runtime behavior is equivalent to the recorded baseline

### GBX-193: Add Replay Diff Reporting And `glassbox replay`

- Status: `DONE`
- Depends on: `GBX-111`, `GBX-192`
- Goal: give operators a practical command for replaying a session and understanding where current behavior diverges from the recorded baseline
- Deliverables:
  - `glassbox replay SESSION_ID` command or equivalent CLI surface for deterministic replay of a persisted session
  - structured replay diff report covering at least transcript output, tool calls, approval / question flow, and final session-state differences
  - machine-readable replay result output such as JSON for downstream automation, plus concise human-readable terminal rendering
  - meaningful exit-code semantics for match, drift, unsupported session, and replay failure outcomes
- Implementation notes:
  - keep the default report concise and operator-oriented, with drill-down detail available when exact differences need inspection
  - distinguish manifest drift from downstream behavioral drift so prompt/context regressions are not collapsed into generic transcript mismatches
  - capture replay reports as artifacts when they are too large for terminal output or when they need later auditability
  - preserve the existing CLI style for error messaging and local workflows; do not require the dashboard for replay usability
- Tests and validation included in task:
  - CLI integration tests for matching and drifting replays, including exit-code assertions
  - tests for JSON output shape and report content against representative replay scenarios
  - regression tests proving replay does not mutate source session metadata or artifacts
- Done when:
  - an operator can run one command and see whether a historical session still reproduces under the current codebase, plus where it drifted if it does not

### GBX-194: Implement Replay Bundle Export And Import For Portable Baselines

- Status: `DONE`
- Depends on: `GBX-191`, `GBX-193`
- Goal: make replayable sessions portable so deterministic baselines can live outside a local SQLite file and be reused across repos, branches, and CI runs
- Deliverables:
  - export path that materializes a replay bundle containing manifest metadata, referenced artifacts, and baseline comparison data in a stable versioned format
  - import or fixture-loading path that allows replay bundles to be consumed without requiring the original local runtime database layout
  - bundle versioning and validation rules so future schema changes fail clearly rather than producing silent partial replays
  - operator-visible command surface or service entrypoint for exporting a session into a reusable replay baseline
- Implementation notes:
  - keep exported bundles self-describing and intentionally minimal; they should include what replay needs, not a blind copy of the entire database
  - preserve redaction guarantees from live-session artifact capture during export and import
  - design the format so repository-checked-in baselines remain diffable and reviewable where practical
  - avoid forcing eval users to keep opaque machine-generated blobs in source control if a smaller normalized representation is sufficient
- Tests and validation included in task:
  - integration tests exporting a replayable session and replaying it successfully from the exported bundle alone
  - tests for bundle validation, version mismatch handling, and missing-file failures
  - tests proving exported baselines remain free of secrets and irrelevant local-path leakage beyond the intentionally recorded workspace context
- Done when:
  - a replay baseline can be generated once and reused elsewhere without the original live session database

### GBX-195: Define Eval Case Format And Baseline Selection Workflow

- Status: `DONE`
- Depends on: `GBX-190`, `GBX-194`, `GBX-121`
- Goal: turn replay from a one-off debugging command into a stable regression-spec workflow that repositories can curate deliberately
- Deliverables:
  - eval case schema describing case identity, source replay bundle, tags, scenario notes, and the invariants that must match or may drift
  - repository-local eval suite layout such as an `evals/` directory or equivalent manifest convention
  - baseline-selection workflow describing how to promote a replay bundle into a tracked eval case and how to refresh that baseline intentionally
  - support for marking cases by scope such as smoke, tooling, approval, provider-mode, or known-unstable comparison dimensions
- Implementation notes:
  - keep eval cases declarative and reviewable; avoid requiring handwritten Python glue for ordinary scenario definitions
  - allow cases to express targeted expectations, such as exact transcript match or final-state-only match, without weakening the default strictness silently
  - make baseline updates explicit and reviewable so the eval system does not become a rubber stamp for regressions
  - align naming and metadata with how operators already think about sessions and workflows, not just with internal event terminology
- Tests and validation included in task:
  - schema-validation tests for valid and invalid eval case definitions
  - tests for case discovery, tag filtering, and invariant parsing against small fixture suites
  - doc review against the implemented replay bundle format and CLI workflows while defining the case model
- Done when:
  - the repo can declare named replay-based regression cases in a stable format without custom code per scenario

### GBX-196: Implement Batch Eval Runner And Summary Reporting

- Status: `DONE`
- Depends on: `GBX-144`, `GBX-193`, `GBX-194`, `GBX-195`
- Goal: let developers and CI run curated replay-based regression suites and get actionable pass/fail output instead of ad hoc one-session checks
- Deliverables:
  - `glassbox eval run` command or equivalent batch runner for executing one or more eval cases
  - suite summary output reporting counts and case-level outcomes such as match, manifest drift, behavioral drift, unsupported, and replay failure
  - machine-readable suite output suitable for CI consumption, plus artifact capture for detailed per-case diffs
  - filtering or selection controls for tags, case IDs, or suite scopes so narrow validation remains practical during iteration
- Implementation notes:
  - run cases in isolation so one broken replay does not contaminate later results or mutate shared state
  - keep the initial runner local and serial unless parallel execution clearly pays for itself without complicating artifact and output handling
  - ensure failures remain debuggable by linking batch summaries back to the per-case replay report artifacts
  - do not turn eval into a second general-purpose test framework; it should complement `pytest` with replay-backed behavioral regression coverage
- Tests and validation included in task:
  - CLI integration tests for mixed pass/fail suites, tag filtering, and CI-oriented exit-code behavior
  - tests for machine-readable summary output and per-case artifact emission
  - regression tests proving batch eval execution works without network access or live provider credentials for deterministic cases
- Done when:
  - an operator can run a curated set of replay cases and get a reliable local or CI signal about behavioral regressions

### GBX-197: Document Replay And Eval Workflows

- Status: `DONE`
- Depends on: `GBX-190`, `GBX-191`, `GBX-192`, `GBX-193`, `GBX-194`, `GBX-195`, `GBX-196`, `GBX-121`
- Goal: explain how to capture replayable sessions, export baselines, run targeted replays, and use eval suites without guessing at unsupported cases or hidden caveats
- Deliverables:
  - README updates covering replay and eval commands, expected inputs, and local validation workflows
  - operator guidance for choosing between raw session inspection, single-session replay, exported replay bundles, and batch eval suites
  - documentation for replay result categories, baseline refresh workflow, and the limits of deterministic comparison for provider-backed sessions
  - troubleshooting guidance for unsupported sessions, drift caused by intentional prompt or schema changes, and missing replay artifacts
- Implementation notes:
  - keep docs explicit that replay compares current behavior against recorded baselines; it does not magically make live provider calls deterministic
  - show at least one end-to-end flow that captures a session, exports a bundle, promotes it into an eval case, and runs the resulting suite locally
  - align examples with the actual command surface and artifact locations introduced in this phase
- Tests and validation included in task:
  - doc review against implemented replay and eval commands, output categories, and artifact formats
  - manual verification of the documented baseline-capture and batch-eval flow against the actual CLI behavior
- Done when:
  - a developer can adopt replay and eval workflows from the docs alone without reading implementation code or guessing at baseline semantics

## Phase 20: Local-First Replay And Eval Regression Gates

### GBX-200: Define Local-First Verification Policy For Direct-To-`main` Development

- Status: `DONE`
- Depends on: `GBX-196`, `GBX-197`, `GBX-121`
- Goal: define how replay and eval verification should protect a workflow that commits directly to `main` and pushes to `origin` without relying on pull-request gates
- Deliverables:
  - documented verification policy that distinguishes:
    - commit-time local gates
    - push-time confirmation after `origin` receives new commits
    - optional broader non-blocking scheduled verification later
  - explicit statement that pre-commit is the primary early-regression barrier for curated smoke evals in this workflow
  - policy for which eval tags are blocking locally, which are only advisory after push, and how those sets are expected to evolve
  - operator guidance for how replay/eval failures should be interpreted when they happen before commit versus after push
- Implementation notes:
  - do not assume branch protection, required PR checks, or merge queues; the workflow must make sense when `git commit` and `git push origin main` are the normal path
  - bias toward catching regressions as early as possible, but be explicit about which checks are still too expensive or too artifact-heavy for every commit
  - keep the policy grounded in the existing hook stack in `.pre-commit-config.yaml` and the current replay/eval command surface rather than inventing a new verification framework
  - treat post-push automation as confirmation, artifact retention, and visibility, not as the first line of defense
- Tests and validation included in task:
  - doc review against the current local hook configuration, replay/eval CLI semantics, and direct-to-`main` workflow assumptions before implementation begins
  - manual validation that the proposed ordering remains practical when running the existing `ruff`, `ty`, `pytest`, and smoke-eval checks from a normal local commit loop
- Done when:
  - the repo has a clear, code-aligned contract for where replay/eval verification runs first, where it runs again after push, and what is or is not expected to block local commits

### GBX-201: Add Commit-Time Smoke Eval Verification To Pre-Commit

- Status: `DONE`
- Depends on: `GBX-196`, `GBX-200`
- Goal: fail local commits when curated replay smoke cases drift, so replay/eval protection fires before code lands on `main`
- Deliverables:
  - pre-commit hook entry that runs `glassbox eval run` against a blocking smoke tag set such as `smoke`
  - local artifact path strategy for commit-time eval runs, including a stable output directory that does not create noisy tracked-file churn
  - hook behavior that preserves current exit-code semantics so behavioral drift, manifest drift, unsupported sessions, and replay failures all stop the commit clearly
  - operator-visible error messaging or docs that make it obvious where to inspect the emitted eval artifacts after a failed commit-time run
- Implementation notes:
  - assume the user prefers earlier failure over shorter commit latency for curated smoke cases; optimize correctness first, then iteration cost only if commit friction becomes unacceptable
  - keep the initial blocking suite intentionally small and deterministic; do not make every eval case part of the commit path by default
  - ensure emitted artifacts land under an ignored local path such as `.glassbox/evals/pre-commit/` or equivalent so failed hooks do not dirty the index with review noise
  - do not weaken the smoke suite just to keep hook runtime low; if needed later, split broader suites into separate non-blocking tags rather than silently shrinking the blocking contract
- Tests and validation included in task:
  - manual validation that a matching smoke suite allows commit to proceed and a drifting smoke suite blocks commit with actionable artifact output
  - regression tests or fixture-driven checks for the chosen output-directory and cleanup semantics if the implementation adds helper logic around eval execution
  - doc review against the local verification policy from `GBX-200`
- Done when:
  - a direct local commit is blocked whenever the blocking replay smoke suite detects a regression

### GBX-202: Make Local Eval Hook Artifacts Stable, Inspectable, And Low-Churn

- Status: `DONE`
- Depends on: `GBX-201`, `GBX-025`
- Goal: make commit-time replay/eval failures debuggable without turning local hook artifacts into workspace clutter or accidental source-control noise
- Deliverables:
  - stable local artifact lifecycle for pre-commit eval runs, such as overwrite-or-refresh behavior for `.glassbox/evals/pre-commit/`
  - explicit ignore or storage rules ensuring hook-generated `summary.json` and per-case artifacts never appear as files the operator is expected to review or commit by default
  - clear retention semantics for the most recent failed run so developers can inspect mismatches after a blocked commit without rerunning immediately
  - any helper or wrapper logic needed to keep the pre-commit command ergonomic while still exposing artifact paths and replay details reliably
- Implementation notes:
  - optimize for the failure path: the important case is that a blocked commit leaves behind exactly enough artifact state to inspect the regression quickly
  - avoid unbounded accumulation of timestamped hook outputs in normal local development loops; commit-time verification should reuse or refresh a known location unless there is a strong reason not to
  - preserve the existing structured eval artifact format so local and post-push verification produce comparable outputs
  - if cleanup behavior is added, ensure it cannot delete curated `evals/` baselines or any source-controlled replay bundles accidentally
- Tests and validation included in task:
  - manual validation that repeated hook runs refresh the expected local artifact directory without polluting the working tree
  - regression tests for any new helper that manages output directories, stale artifacts, or failure-summary retention
  - validation that a failed commit leaves actionable artifact paths and content behind for inspection
- Done when:
  - commit-time eval verification leaves behind a predictable, inspectable local artifact set without creating recurring source-control churn

### GBX-203: Add Push-To-`origin` Replay/Eval Confirmation Workflow

- Status: `DONE`
- Depends on: `GBX-200`, `GBX-201`, `GBX-202`
- Goal: re-run the curated replay smoke suite after commits are pushed to `origin` so the shared remote record keeps structured verification artifacts even in a direct-to-`main` workflow
- Deliverables:
  - automation workflow triggered by pushes to the main development branch or equivalent origin push path, rather than by pull requests
  - workflow step that runs the same blocking smoke eval tag set used locally, or an explicitly documented superset if the remote environment justifies it
  - artifact publication for `summary.json` and per-case replay outputs so push-time failures remain inspectable after the local machine is gone
  - clear repository guidance for how post-push failures should be noticed and triaged when the local pre-commit gate already passed
- Implementation notes:
  - this workflow is not a PR gate; design it as post-push confirmation and shared artifact retention for direct-to-`main` development
  - keep the push-triggered environment deterministic and offline-friendly; it should not depend on live provider credentials for the curated replay smoke suite
  - preserve the same exit-code semantics and outcome taxonomy used locally so push-time failures do not invent a second interpretation model
  - do not duplicate large numbers of broad eval cases into the first push workflow unless they materially improve confidence beyond the local smoke gate
- Tests and validation included in task:
  - manual validation of the push-triggered automation against a branch or repository configuration that mirrors the direct-to-`main` workflow
  - doc review against the local-first verification policy so the relationship between local blocking checks and post-push confirmation stays explicit
  - verification that emitted remote artifacts include both the suite summary and per-case outputs for failed smoke runs
- Done when:
  - every push to the main development branch re-runs the curated replay smoke suite remotely and retains inspectable artifacts without depending on PR-only workflows

### GBX-204: Surface Push-Time Replay/Eval Results For Fast Triage

- Status: `DONE`
- Depends on: `GBX-203`, `GBX-111`
- Goal: make remote replay/eval confirmation failures easy to understand quickly instead of forcing developers to download raw artifacts before they know which case drifted
- Deliverables:
  - compact machine-readable and human-readable push-time summary surfaced in the automation UI, including selected case count, pass/fail counts, and replay outcome totals
  - links or paths from the remote summary back to the retained `summary.json` and per-case artifact outputs
  - explicit treatment of replay outcome severity so `manifest_drift`, `behavioral_drift`, `unsupported_session`, and `replay_failure` are distinguishable at a glance
  - operator guidance for the first debugging move when a post-push smoke eval fails after a local commit passed
- Implementation notes:
  - optimize for scan speed; the first remote summary should answer which case failed, how it failed, and where the detailed artifact lives
  - reuse the existing suite summary model and outcome vocabulary from `glassbox eval run` instead of creating a second reporting schema just for automation
  - keep any remote summary generation straightforward enough that it can evolve with the eval runner without constant maintenance burden
  - this should improve triage, not replace retained artifacts; detailed replay diffs still belong in emitted case JSON outputs
- Tests and validation included in task:
  - manual review of the rendered automation summary against representative mixed-outcome smoke suites
  - validation that artifact links or paths in the summary actually correspond to retained replay/eval outputs
  - doc review against the current outcome taxonomy and batch eval report format
- Done when:
  - a developer can inspect a push-time replay/eval failure summary and know which case drifted, what class of failure occurred, and where to find the detailed artifacts within seconds

### GBX-205: Document Local Commit Gates And Push-Time Confirmation For Replay/Evals

- Status: `DONE`
- Depends on: `GBX-200`, `GBX-201`, `GBX-202`, `GBX-203`, `GBX-204`, `GBX-121`
- Goal: explain the final local-first verification workflow clearly enough that a developer using direct commits to `main` understands what runs before commit, what runs after push, and how to respond when one of those layers fails
- Deliverables:
  - README and workflow documentation updates describing the commit-time smoke eval gate and where its local artifacts live
  - documentation for the push-to-`origin` replay/eval confirmation workflow, retained artifacts, and expected follow-up when remote confirmation fails
  - guidance for choosing and maintaining the blocking smoke tag set versus broader non-blocking eval tags
  - troubleshooting guidance for common local-first failure modes, such as commit blocked by smoke drift, post-push remote drift after local success, and intentional baseline refreshes
- Implementation notes:
  - keep the docs explicit that local pre-commit is the primary protection layer in this workflow; push-time automation is the second line, not the first gate
  - show at least one realistic flow that goes from local commit failure to artifact inspection to successful rerun, and one flow for post-push remote confirmation failure
  - align examples with the actual pre-commit hook entries, output directories, and push automation introduced in this phase
- Tests and validation included in task:
  - doc review against the implemented pre-commit configuration, push-triggered workflow, and replay/eval artifact paths
  - manual verification that a developer can follow the documented local-first regression workflow without guessing which command, hook, or artifact to inspect next
- Done when:
  - a developer committing directly to `main` can understand and successfully use the repo’s replay/eval regression gates from the docs alone

---

## Phase 21: Session Branching And Time-Travel

### GBX-210: Define Session Branching And Time-Travel Operator Model

- Status: `DONE`
- Depends on: `GBX-100`, `GBX-101`, `GBX-181`, `GBX-190`, `GBX-121`
- Goal: define how Glassbox should support historical inspection and forked follow-up work without breaking the current event-sourced session model
- Deliverables:
  - architecture and operator-workflow updates defining session branching, historical inspection, and fork semantics
  - explicit v1 scope boundary for stable fork points such as the latest completed turn or a selected completed turn
  - explicit non-goals for v1 such as in-place rewind, event deletion, checkpoint resurrection, or forking from mid-turn transient state
  - terminology and command-surface proposal for branch or fork actions across CLI and dashboard flows
- Implementation notes:
  - preserve the current immutable event-log model; time-travel in v1 should create a new child session rather than mutating or truncating the source session
  - define the operator-facing cut-point contract in terms of meaningful turn boundaries, even if storage resolves that to an event sequence internally
  - keep the first version compatible with the current snapshot, SSE, resume, replay, and eval semantics rather than inventing a second history model
  - be explicit about whether child sessions inherit transcript history only, richer read models, or raw prior events; the chosen contract must stay auditable and replayable
- Tests and validation included in task:
  - architecture and doc review against the current event, projection, replay, and standalone-dashboard flows before implementation begins
  - manual validation that the proposed operator workflow does not contradict existing approval, `ask_user`, resume, or historical snapshot semantics
- Done when:
  - the repo has a clear, code-aligned design for how historical session forking works, what counts as a valid fork point, and what is intentionally out of scope for v1

### GBX-211: Add Session Lineage Schema And Persisted Contracts

- Status: `DONE`
- Depends on: `GBX-210`
- Goal: extend the canonical persistence and domain models so forked sessions can record parentage and historical cut-point metadata explicitly
- Deliverables:
  - lineage fields in the relevant core models and event payloads such as parent session ID, fork source turn ID, fork source sequence, and optional branch label
  - SQLite schema updates for session lineage metadata with appropriate indexes for parent-child browsing
  - backward-compatible repository read and write paths for sessions without lineage metadata
- Implementation notes:
  - keep lineage as explicit persisted metadata rather than recomputing ancestry heuristically from transcript similarity or artifact names
  - preserve compatibility with existing sessions and replay bundles that predate branching support
  - do not turn session metadata into a richer shadow source of truth for mutable runtime state; lineage should describe ancestry, not replace events
- Tests and validation included in task:
  - unit and integration tests for model serialization, schema bootstrap, and repository access with and without lineage metadata
  - tests proving older sessions remain readable after the schema and model changes
- Done when:
  - Glassbox can persist and query parent-child session lineage without regressing existing session creation, listing, snapshot, or replay behavior

### GBX-212: Implement Historical Fork-Point Resolution And Imported-History Event Flow

- Status: `DONE`
- Depends on: `GBX-210`, `GBX-211`, `GBX-024`
- Goal: make fork creation deterministic by resolving stable historical cut points and materializing the inherited conversation state into the child session explicitly
- Deliverables:
  - service or repository helper for resolving valid fork points from a parent session, including latest completed turn and explicit completed-turn selection
  - event model and projection support for importing inherited transcript history into a child session as canonical child-session data
  - rejection path for invalid fork points such as active turns, pending approvals, pending questions, failed partial turn state, or unknown turn identifiers
- Implementation notes:
  - keep child sessions self-contained for prompt assembly and browser snapshots; avoid requiring the runtime to chase parent ancestry on every turn
  - prefer importing the normalized conversation state needed for continuation over blindly copying every historical parent event into the child
  - define deterministic ordering and identity rules for imported transcript messages so projections, replay, and snapshots remain stable
  - keep this compatible with the current decision that checkpoints are unnecessary for v1; fork-point resolution should operate from canonical events and projections
- Tests and validation included in task:
  - integration tests for resolving valid and invalid fork points across completed, running, awaiting-approval, and awaiting-user-input sessions
  - projection tests proving imported history reconstructs a correct child transcript without mutating the parent session
- Done when:
  - Glassbox can derive a valid fork boundary from persisted history and materialize the inherited transcript state into a new session deterministically

### GBX-213: Implement Session Fork Service And CLI Workflow

- Status: `DONE`
- Depends on: `GBX-032`, `GBX-042`, `GBX-152`, `GBX-212`
- Goal: let operators create a new child session from a stable historical point entirely through supported service and CLI paths
- Deliverables:
  - service-layer fork API for creating a child session from a parent session and selected fork point
  - CLI command surface such as `glassbox fork SESSION_ID` with options for explicit turn selection, optional branch label, and optional immediate child-session prompt submission if justified
  - operator-visible CLI output describing the new child session ID and the parent/cut-point relationship
- Implementation notes:
  - route the fork behavior through the session service boundary rather than direct CLI-to-repository code
  - keep the first CLI workflow explicit and auditable; operators should know exactly which historical point they forked from
  - the source session must remain untouched; the child session is the only place where new post-fork events should appear
  - if the CLI supports immediate follow-up prompting in the child, keep that as a small adjacent step after successful child creation rather than collapsing the ancestry and turn-start semantics into one opaque action
- Tests and validation included in task:
  - CLI and integration tests for successful fork creation from the latest completed turn and from an explicitly selected turn
  - negative-path tests for unknown sessions, invalid turn identifiers, and non-branchable session state
- Done when:
  - an operator can create a forked child session from the terminal and continue work in the child without mutating the original session

### GBX-214: Expose Session Lineage And Fork Actions Through Snapshot, Index, And HTTP APIs

- Status: `DONE`
- Depends on: `GBX-181`, `GBX-183`, `GBX-213`
- Goal: make forked-session ancestry visible and actionable through the existing browser-facing backend surfaces
- Deliverables:
  - snapshot and session-index response fields for parent lineage, fork source metadata, and child-session summaries where justified
  - HTTP endpoint for creating a fork from a selected session and historical cut point
  - backend response contracts sufficient for the dashboard to show lineage and branchability without fetching excessive additional state ad hoc
- Implementation notes:
  - share the same service-layer fork logic used by the CLI path; do not duplicate historical-state rules in route handlers
  - keep the session index practical for browsing related sessions, but avoid turning the first version into a full graph query API
  - ensure the HTTP contract distinguishes branchable historical points from sessions that are only inspectable
- Tests and validation included in task:
  - HTTP integration tests for lineage fields in session summaries and snapshots
  - HTTP tests for successful and rejected fork requests, including conflict semantics for invalid session state or invalid fork-point selection
- Done when:
  - browser-facing clients can discover session ancestry and create a fork through stable HTTP contracts backed by the same runtime rules as the CLI

### GBX-215: Implement Dashboard History Browser And Fork UX

- Status: `DONE`
- Depends on: `GBX-184`, `GBX-214`
- Goal: let an operator inspect a session’s historical branch points and create a child session from the dashboard without leaving the existing session browser workflow
- Deliverables:
  - dashboard UI for displaying session lineage, including parent information and any known child sessions that are useful for navigation
  - browser-side state and rendering support for selectable fork points, restricted to valid stable historical cut points
  - dashboard action flow for creating a fork and navigating into the resulting child session
- Implementation notes:
  - keep the initial browser UX explicit rather than magical; operators should understand whether they are inspecting history, opening another session, or creating a new child branch
  - preserve the existing standalone dashboard mental model of snapshots plus live updates; forking is a persisted session action, not a browser-local state transformation
  - do not promise in-place historical replay of streamed terminal activity in the browser if the backend only supports snapshot and event-backed inspection
- Tests and validation included in task:
  - frontend reducer and rendering tests for lineage presentation, branchable-point selection, and navigation into a forked child session
  - integration tests for dashboard fork actions backed by mocked or real HTTP responses and resulting snapshot refresh behavior
- Done when:
  - an operator can understand session ancestry and create or open forked sessions from the dashboard without ambiguity about what changed

### GBX-216: Make Replay And Eval Workflows Lineage-Aware

- Status: `DONE`
- Depends on: `GBX-191`, `GBX-194`, `GBX-196`, `GBX-212`
- Goal: ensure forked sessions remain replayable, exportable, and usable as eval baselines without collapsing their imported history into opaque special cases
- Deliverables:
  - replay-capture and replay-bundle support for session lineage metadata and imported-history artifacts or events
  - deterministic replay behavior for forked child sessions, including comparison rules for inherited transcript history versus post-fork divergence
  - eval-case compatibility for replay bundles created from branched sessions
- Implementation notes:
  - preserve the distinction between inherited historical context and new child-session behavior so replay drift reports remain understandable
  - avoid requiring the original parent session database rows at replay time once a child replay bundle has been exported
  - keep redaction and portability guarantees intact for forked sessions just as they are for ordinary replay bundles
- Tests and validation included in task:
  - integration tests proving a forked child session can be replayed and exported independently of the live parent session
  - regression tests for replay diff behavior when the inherited prefix matches but post-fork behavior drifts
- Done when:
  - forked sessions remain first-class citizens in replay and eval workflows rather than becoming unsupported historical edge cases

### GBX-217: Document Session Branching And Historical Workflows

- Status: `DONE`
- Depends on: `GBX-210`, `GBX-213`, `GBX-214`, `GBX-215`, `GBX-216`, `GBX-121`
- Goal: document how operators should inspect historical sessions, create forks, understand lineage, and use forked sessions with replay and eval workflows
- Deliverables:
  - README and architecture updates covering branching semantics, valid fork points, and the immutable-parent model
  - operator guidance for CLI and dashboard fork workflows, including how to choose between continuing a live session, inspecting a historical snapshot, and creating a child branch
  - documentation for lineage fields surfaced in the session index and snapshot views
  - troubleshooting guidance for rejected fork attempts, historical-only sessions, and replay or eval behavior for child sessions
- Implementation notes:
  - keep docs explicit that v1 time-travel is branch creation, not destructive rewind or event-log mutation
  - show at least one end-to-end example that starts from a historical session, creates a fork, and continues work in the child session
  - align the branching docs with existing replay, eval, and dashboard terminology so ancestry does not become a separate conceptual subsystem
- Tests and validation included in task:
  - doc review against implemented CLI help text, snapshot fields, dashboard behavior, and replay or eval support for child sessions
  - manual verification of the documented branch workflow against the actual operator surfaces
- Done when:
  - an operator can discover and use session branching and historical inspection workflows from the docs alone without inferring hidden runtime rules

---

## Phase 22: Richer Runtime Context And Memory-Grounded Turns

### GBX-220: Define Richer Runtime Context Contract And Scope

- Status: `DONE`
- Depends on: `GBX-033`, `GBX-051`, `GBX-191`, `GBX-217`, `GBX-121`
- Goal: define what additional turn context Glassbox should assemble beyond transcript, tools, and approval state so future prompt improvements remain inspectable, replayable, and bounded
- Deliverables:
  - architecture and operator-workflow updates defining the richer runtime context model
  - explicit context-source taxonomy covering at least repository context, session-scoped runtime notes, and turn-local working-set summaries
  - explicit rules for what belongs in prompt context versus what should remain tool-discoverable at runtime
  - scope boundary for v1 richer context so the implementation does not collapse into unbounded repository indexing or hidden agent memory
- Implementation notes:
  - build on the existing typed `TurnContext` shape and prompt-fragment hooks rather than inventing a second context path beside them
  - keep the contract deterministic enough that replay and eval can continue to reason about context drift explicitly
  - define budget and freshness expectations up front so repository context remains concise, stable, and cheap to recompute locally
  - treat richer context as an operator-facing runtime feature, not as invisible prompt magic
- Tests and validation included in task:
  - architecture and doc review against the current `TurnContextBuilder`, system-prompt composition, replay-manifest capture, and session resume behavior before implementation begins
  - manual validation that the proposed context model does not contradict the current event-sourced source-of-truth rule or the local-first replay model
- Done when:
  - the repo has a clear, code-aligned contract for what richer runtime context contains, where it comes from, and what is intentionally out of scope for the first implementation

### GBX-221: Implement Typed Repository Context Snapshot Builder

- Status: `DONE`
- Depends on: `GBX-220`
- Goal: assemble a deterministic repository-context summary that gives the model useful workspace awareness without forcing it to rediscover the same high-level facts every turn
- Deliverables:
  - typed repository-context models and builder helpers under the runtime boundary
  - initial repository snapshot sources such as stable workspace root metadata, high-signal top-level project structure, and other low-cost summary inputs justified by the design task
  - normalization rules that keep repository-context text compact, ordered, and replay-friendly
- Implementation notes:
  - do not dump raw file trees or whole documents into prompt context by default; prefer concise, typed summaries that are cheap to inspect and compare
  - keep repository-context building distinct from tool execution so the turn engine still owns a clean separation between assembly and action
  - be deliberate about any filesystem reads or lightweight git-derived signals included in the baseline so the result stays deterministic enough for local replay
  - expose enough structure that later tasks can surface repository context in status, snapshots, or replay manifests without reverse-parsing prompt text
- Tests and validation included in task:
  - unit tests for repository-context assembly and stable ordering using representative fixture workspaces
  - regression tests proving repository-context normalization is deterministic for the same workspace contents
- Done when:
  - Glassbox can build a compact typed repository-context snapshot suitable for inclusion in turn context without relying on ad hoc string concatenation in the turn engine

### GBX-222: Implement Session-Scoped Runtime Notes And Retrieval

- Status: `DONE`
- Depends on: `GBX-220`, `GBX-024`, `GBX-032`
- Goal: make session-scoped runtime notes a real persisted input to future turns instead of an unused field on `TurnContext`
- Deliverables:
  - service and repository support for recording and retrieving session-scoped runtime notes using the existing runtime-note event model or an equivalent event-aligned refinement if the contract changes
  - projection or query helpers for reading the currently active note set efficiently during context assembly
  - clear note categories or source metadata if needed to distinguish operator notes, runtime notes, and inherited branch context
- Implementation notes:
  - keep notes session-scoped and event-backed so they survive resume, branching, and replay without inventing an out-of-band memory store
  - prefer append-only note recording plus deterministic current-state derivation over mutable ad hoc note blobs
  - define deduplication, supersession, or retention semantics explicitly so note growth remains bounded in long-lived sessions
  - if branch inheritance matters, keep inherited notes distinguishable from newly recorded child-session notes rather than flattening all memory into one opaque list
- Tests and validation included in task:
  - integration tests for recording, projecting, and retrieving runtime notes across normal sessions, resumed sessions, and forked child sessions where relevant
  - regression tests proving older sessions without notes remain readable and do not break context assembly
- Done when:
  - session-scoped runtime notes can be persisted, recovered, and queried through the normal event and projection flow instead of existing only as an unused prompt hook

### GBX-223: Inject Enriched Context Into Turn Assembly And Prompt Construction

- Status: `DONE`
- Depends on: `GBX-221`, `GBX-222`, `GBX-052`, `GBX-053`
- Goal: make richer repository context and runtime notes part of the actual live turn path rather than dormant optional fields
- Deliverables:
  - turn-engine wiring that builds repository context and session notes for user-message, approval-resume, and ask-user-resume turn paths
  - `TurnContextBuilder` integration for the richer context inputs
  - prompt-composition updates only where needed to keep repository context and notes clearly separated from transcript and tool instructions
- Implementation notes:
  - keep the richer-context path explicit in the turn engine so failures in context assembly surface as debuggable runtime behavior rather than silent prompt degradation
  - ensure the enriched context stays bounded; do not let one large repository summary crowd out transcript or tool information indiscriminately
  - preserve the current typed system-prompt composition model rather than inlining new context fragments directly into model adapters or executors
  - cover all turn entry points so resumed turns do not silently lose repository context or memory notes compared with initial user-message turns
- Tests and validation included in task:
  - integration tests for end-to-end prompt assembly including repository context and runtime notes across initial, approval-resumed, and ask-user-resumed turns
  - prompt-composition tests proving the enriched context remains clearly separated and stable in the final system prompt
- Done when:
  - live Glassbox turns actually receive the richer repository context and session-scoped notes through the normal typed prompt assembly path

### GBX-224: Make Replay, Resume, And Branching Respect Enriched Context

- Status: `DONE`
- Depends on: `GBX-100`, `GBX-191`, `GBX-212`, `GBX-216`, `GBX-223`
- Goal: preserve richer runtime context across replay, eval, resume, and branch workflows so smarter prompt assembly does not reduce determinism or make child sessions opaque again
- Deliverables:
  - replay-manifest and portable-bundle support for the enriched context inputs that materially influence turn preparation
  - explicit replay-drift behavior when repository context or runtime notes no longer reproduce the recorded manifest shape
  - resume and branching rules for how repository context is recomputed versus how runtime notes and inherited context are carried forward into child sessions
- Implementation notes:
  - keep the distinction clear between recomputed repository summaries and persisted note state; not every richer-context input should be treated the same way during replay or forking
  - do not make replay depend on undocumented ambient workspace state beyond the defined repository-context contract
  - ensure child sessions remain self-contained enough that replay and eval can reason about inherited notes or context explicitly rather than reconstructing them heuristically from the parent session
  - preserve the current local-first replay taxonomy by reporting richer-context mismatches as manifest drift when appropriate rather than collapsing them into generic transcript drift
- Tests and validation included in task:
  - integration tests proving enriched-context sessions can still be resumed, exported, replayed, and used as eval baselines
  - regression tests for forked sessions where inherited note state or repository context contributes to child-session turn preparation
- Done when:
  - richer runtime context remains compatible with the project’s existing resume, replay, eval, and branching guarantees instead of becoming hidden non-replayable prompt state

### GBX-225: Surface Current Runtime Context For Operator Inspection

- Status: `DONE`
- Depends on: `GBX-111`, `GBX-183`, `GBX-223`
- Goal: make the richer context inspectable enough that operators can understand what high-level workspace and memory facts the model is currently seeing
- Deliverables:
  - status, snapshot, or equivalent operator-facing surfaces for concise repository-context and runtime-note summaries where they add practical debugging value
  - bounded presentation rules so these summaries remain legible in terminal and browser workflows
  - any backend response-contract updates needed to support the richer-context display path without exposing raw prompt text as the only inspection mechanism
- Implementation notes:
  - surface summaries, not giant prompt dumps; operators should understand the current context model without reading opaque concatenated system-prompt text
  - keep browser and terminal semantics aligned where the same session context is represented in both places
  - do not turn operator inspection into a second mutable configuration path unless a later task explicitly introduces editable note workflows
- Tests and validation included in task:
  - CLI and/or HTTP integration tests for richer-context summary visibility in representative session states
  - frontend or renderer regression tests if new browser or terminal presentation is added
- Done when:
  - an operator can inspect the key repository-context and session-note inputs shaping a turn without diving into implementation code or replay artifacts first

### GBX-226: Document Richer Runtime Context Workflows And Boundaries

- Status: `DONE`
- Depends on: `GBX-220`, `GBX-221`, `GBX-222`, `GBX-223`, `GBX-224`, `GBX-225`, `GBX-121`
- Goal: explain how richer runtime context works, what it includes, and how it affects replayable session behavior without making it sound like hidden autonomous memory
- Deliverables:
  - README and architecture updates covering repository context, session-scoped runtime notes, and their role in live turns
  - operator guidance for understanding richer-context summaries in the CLI and dashboard
  - documentation for how enriched context interacts with resume, replay, eval, and branch workflows
  - troubleshooting guidance for context drift, stale summaries, and note-related behavior changes during replay or resumed sessions
- Implementation notes:
  - keep docs explicit that richer context is still bounded, typed runtime state, not an uninspectable black-box memory layer
  - show at least one end-to-end example where repository context and runtime notes affect a later turn in a way the operator can inspect
  - align the docs with the existing replay and eval terminology so context drift becomes part of the same conceptual model rather than a separate subsystem
- Tests and validation included in task:
  - doc review against implemented builder behavior, prompt composition, status or snapshot surfaces, and replay-manifest semantics
  - manual verification that the documented richer-context workflow matches the actual operator-visible behavior
- Done when:
  - a developer or operator can understand what richer runtime context is, how it is assembled, and how it behaves under replay and branching from the docs alone

---

## Phase 23: Context Quality V2 Without Hidden State

### GBX-230: Define Working-Set Context Contract And Replay Semantics

- Status: `TODO`
- Depends on: `GBX-220`, `GBX-223`, `GBX-224`, `GBX-226`
- Goal: define a second-generation context model for Glassbox that goes beyond repository-root summaries while staying bounded, inspectable, and replay-aware
- Deliverables:
  - architecture and task-graph updates defining a typed `working_set` context source distinct from transcript, repository summary, and runtime notes
  - explicit provenance rules for what signals are allowed to shape the working set such as recent tool outputs, touched files, failing tests, branch lineage, and session-scoped notes
  - replay taxonomy updates that distinguish between full enriched-context drift and per-source drift where practical
  - explicit non-goals for v2 such as hidden embeddings, ambient machine caches, broad autonomous indexing, or opaque long-term memory
- Implementation notes:
  - keep the working set as a deterministic runtime summary, not a second retrieval system beside the existing tools
  - define strict budget limits for item count, summary length, and freshness so the working set does not crowd out transcript and tool instructions
  - require each candidate working-set signal to declare whether it is recomputed, persisted, artifact-backed, or intentionally excluded from replay guarantees
  - align the contract with the existing `TurnContext` and replay-manifest model instead of introducing a side channel for prompt enrichment
- Tests and validation included in task:
  - doc review against the current `TurnContextBuilder`, prompt composition, replay manifest capture, and operator inspection surfaces
  - manual validation that the proposed contract can be expressed through typed models, replay fingerprints, and bounded snapshot APIs without hidden state
- Done when:
  - the repository has a code-aligned design for `working_set` context, provenance classes, and replay semantics that can drive implementation without reopening the architecture debate in later tasks

### GBX-231: Implement Typed Working-Set Projection From Explicit Runtime Signals

- Status: `TODO`
- Depends on: `GBX-024`, `GBX-111`, `GBX-191`, `GBX-225`, `GBX-230`
- Goal: build a deterministic working-set summary from already-explicit session signals so the model starts each turn with better local task awareness
- Deliverables:
  - typed working-set models and builder helpers under the runtime boundary
  - projection or query support for deriving a bounded current working set from explicit signals such as touched files, recent tool calls, approval subjects, failing-test artifacts, and inherited branch context where justified
  - prioritization and normalization rules that keep working-set ordering stable and explanation-friendly
  - initial operator-visible summaries for why a file, test, or artifact is present in the working set
- Implementation notes:
  - prefer event- and artifact-derived signals over ad hoc filesystem heuristics so the result remains explainable and replayable
  - start with a narrow set of strong signals rather than trying to infer intent from every available event family
  - keep duplicate suppression, decay, and supersession rules explicit so long-running sessions do not accumulate stale focus items forever
  - if a signal cannot be made deterministic enough for replay, leave it out of the baseline working set and track it as an explicit future candidate
- Tests and validation included in task:
  - unit tests for working-set ranking, deduplication, and stable ordering from representative event and artifact inputs
  - integration tests proving the same persisted session state yields the same working-set snapshot across resume and rebuild flows
- Done when:
  - Glassbox can derive a bounded typed working set from explicit runtime state without relying on hidden caches or prompt-only heuristics

### GBX-232: Inject Working-Set Context Into Turn Assembly, Status, And Snapshot Flows

- Status: `TODO`
- Depends on: `GBX-223`, `GBX-225`, `GBX-231`
- Goal: make the working set part of normal live turn preparation and operator inspection instead of an internal-only helper
- Deliverables:
  - `TurnContextBuilder` and prompt-composition updates that surface the working set as a distinct prompt fragment beside repository context and runtime notes
  - CLI and snapshot updates that let operators inspect the current working set and its top-ranked signals without dumping raw prompt text
  - dashboard reducer and rendering updates for the new working-set surface where appropriate
  - bounded formatting rules that keep the working-set display legible in both terminal and browser workflows
- Implementation notes:
  - keep working-set prompt text separate from repository context so replay artifacts and operator surfaces can reason about the two independently
  - ensure all turn entry paths receive the same working-set behavior, including user-message turns, approval resumes, and ask-user resumes
  - preserve the current principle that prompt enrichment failures should surface explicitly rather than silently dropping context quality
  - do not let working-set summaries become editable from the operator surface in this phase
- Tests and validation included in task:
  - integration tests for prompt assembly and operator-visible status or snapshot output including working-set summaries across representative session states
  - frontend or renderer regression tests covering working-set rendering and update behavior from snapshot plus SSE
- Done when:
  - live Glassbox turns use the working set consistently and operators can inspect the current focus summary without reading raw replay artifacts

### GBX-233: Add Per-Source Provenance Metadata And Fingerprints For Enriched Context

- Status: `TODO`
- Depends on: `GBX-191`, `GBX-224`, `GBX-230`, `GBX-232`
- Goal: make enriched-context drift reporting more actionable by capturing provenance and fingerprints per context source instead of only at the aggregate level
- Deliverables:
  - typed provenance records for repository context, runtime notes, working-set context, and any other enriched-context sources introduced by the v2 model
  - replay-manifest updates that record per-source schema version, provenance classification, and semantic fingerprint
  - replay diff reporting updates that can identify which context source drifted rather than collapsing all mismatches into one enriched-context failure
  - any snapshot or inspection-contract updates needed to expose concise provenance information for debugging
- Implementation notes:
  - fingerprints should be semantic and stable, not overly sensitive to formatting, ordering noise, or irrelevant metadata
  - provenance should distinguish recomputed summaries, persisted notes, inherited context, and artifact-backed summaries clearly
  - preserve backward compatibility for older replay bundles that only have the aggregate enriched-context fingerprint
  - do not force every future context source to use identical drift policy; the contract should support source-specific evolution without ambiguity
- Tests and validation included in task:
  - regression tests for replay manifests and offline replay that verify per-source drift classification and backwards compatibility with older artifacts
  - unit tests proving provenance and fingerprint helpers ignore non-semantic noise but catch meaningful context changes
- Done when:
  - replay and eval output can identify the specific enriched-context source that changed and the system still supports older replay artifacts gracefully

### GBX-234: Add Artifact-Backed Context Summaries For Expensive Derived Inputs

- Status: `TODO`
- Depends on: `GBX-025`, `GBX-191`, `GBX-230`, `GBX-233`
- Goal: support richer context inputs that are too expensive or too volatile to recompute ad hoc every turn by storing them as explicit derived artifacts
- Deliverables:
  - an artifact-backed contract for derived context summaries such as bounded failing-test digests, curated file-cluster summaries, or other expensive high-signal turn aids justified by the working-set design
  - repository and runtime support for recording, retrieving, and invalidating those summaries through the normal event and artifact flow
  - replay-manifest support that records when a turn depended on an artifact-backed context summary and how it should be validated during replay
  - operator-visible summary metadata showing when a context artifact is present and whether it is stale, inherited, or recomputed
- Implementation notes:
  - start with one narrowly defined artifact-backed summary type rather than introducing a generic plugin system
  - keep artifact generation explicit and event-linked so replay, resume, and branch workflows can reason about dependency on those summaries without hidden caches
  - define invalidation and freshness rules up front so stale artifacts do not silently degrade later turns
  - avoid storing giant prompt-ready blobs when a compact typed summary plus referenced artifact is sufficient
- Tests and validation included in task:
  - integration tests covering artifact-backed context generation, retrieval, invalidation, and replay behavior for sessions that depend on the summary
  - regression tests proving sessions without the new artifact type remain fully readable and replayable
- Done when:
  - Glassbox can use at least one expensive derived context summary through explicit artifact contracts rather than hidden recomputation or prompt-only hacks

### GBX-235: Expand Replay And Eval Coverage For Context Drift, Inheritance, And Working-Set Evolution

- Status: `TODO`
- Depends on: `GBX-196`, `GBX-216`, `GBX-233`, `GBX-234`
- Goal: make the richer context model safe to evolve by adding replay and eval baselines that specifically exercise context-sensitive behavior
- Deliverables:
  - new replay or eval fixtures covering stable working-set construction, context drift detection, branch-inherited context, and artifact-backed context dependencies
  - selected-invariant eval cases that distinguish transcript stability from context-source drift where strict exact-match would be too blunt
  - documentation or metadata updates describing how to read context-related replay and eval failures during local verification and push-time confirmation
  - any pre-commit or CI hook updates needed if context-sensitive smoke coverage becomes part of the enforced baseline
- Implementation notes:
  - add cases that fail for the right reason when context inputs change, not only cases that confirm the happy path
  - ensure at least one case covers branch inheritance so child-session context stays self-contained and understandable under replay
  - keep smoke coverage small and stable; broader context-behavior coverage can remain advisory until the signal quality is proven
  - use the existing replay taxonomy deliberately so context drift is not misreported as generic transcript instability
- Tests and validation included in task:
  - targeted replay and eval runs for the new cases, plus verification that local and push-time reporting still surfaces actionable artifacts and summaries
  - manual verification that failing context-sensitive cases explain themselves clearly through the generated JSON artifacts and summaries
- Done when:
  - Glassbox has automated regression coverage for the new context architecture and context drift is a routine, explainable verification signal rather than a surprise failure mode

### GBX-236: Document Context Quality V2 Workflows, Debugging, And Scope Limits

- Status: `TODO`
- Depends on: `GBX-232`, `GBX-233`, `GBX-234`, `GBX-235`, `GBX-121`
- Goal: document the second-generation context model so operators and contributors can understand what improved, what stayed bounded, and how to debug context-related drift
- Deliverables:
  - README and architecture updates covering working-set context, provenance metadata, artifact-backed summaries, and the updated replay semantics
  - operator guidance for reading working-set and provenance information in CLI status, dashboard snapshots, replay diffs, and eval artifacts
  - troubleshooting guidance for stale context artifacts, source-level drift reports, and branch-inherited context surprises
  - explicit scope boundaries describing what Glassbox still does not do such as hidden vector memory, broad autonomous indexing, or unbounded project summarization
- Implementation notes:
  - keep the docs explicit that context quality improvements remain typed runtime state, not opaque prompt engineering
  - include at least one end-to-end example where a working-set summary materially shapes a later turn and the operator can inspect the same context source through normal surfaces
  - align the new docs with the existing replay, eval, and branching language so context-quality v2 feels like an extension of the current system rather than a parallel subsystem
  - document upgrade and compatibility expectations for older replay bundles and sessions where provenance metadata is missing
- Tests and validation included in task:
  - doc review against implemented prompt composition, runtime inspection, replay artifacts, and eval reporting
  - manual verification that a developer can understand how context-quality v2 affects replayability from the docs alone
- Done when:
  - the repository documentation explains the v2 context model, its replay guarantees, and its debugging workflow clearly enough that contributors do not need to reverse-engineer the implementation first

---

## Recommended Build Order For The First Usable Vertical Slice

If an agent wants the fastest path to a demonstrable but architecturally correct version, the recommended order is:

1. `GBX-001` through `GBX-003`
2. `GBX-010` through `GBX-012`
3. `GBX-020` through `GBX-024`
4. `GBX-030` through `GBX-033`
5. `GBX-040` through `GBX-042`
6. `GBX-050` through `GBX-053`
7. `GBX-060` through `GBX-063`
8. `GBX-080` through `GBX-082`

That yields:

- a real CLI
- a real event store
- a real turn engine
- at least one safe tool
- a real dashboard snapshot and event stream

Everything after that deepens the operator experience rather than inventing the core architecture.

## Explicit Non-Goals For Initial Execution

Do not spend time on these until the core task graph above is materially complete:

- multi-user remote orchestration
- background distributed workers
- plugin marketplaces or extension systems
- browser code editing
- complex permissions sandboxing beyond workspace and policy checks
- production deployment infrastructure

## Success Criteria For The Project

The project is on track when all of the following are true:

- a user can run `glassbox` locally through `uv`
- a session persists as an event log in SQLite
- the agent can execute at least safe repository-inspection tools and continue reasoning
- risky actions can pause for approval and resume safely
- the dashboard shows a live, accurate view of session state from snapshot plus streamed events
- sessions can be resumed after restart
- all shipped features are protected by automated tests and pass lint and type checks continuously
