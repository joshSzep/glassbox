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

- Status: `TODO`
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

- Status: `TODO`
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

- Status: `TODO`
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

- Status: `TODO`
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

- Status: `TODO`
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
