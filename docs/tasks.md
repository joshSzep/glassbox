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
