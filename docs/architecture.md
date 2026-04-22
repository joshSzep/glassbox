# Glassbox Architecture

## Goal

Glassbox is a local-first CLI application that runs multi-turn agent workflows while serving a live dashboard that exposes the agent's internal activity. The core experience is similar to Codex and Claude Code style harnesses:

- the user interacts through a terminal-first CLI
- the runtime performs agentic multi-turn work with tools
- the system can stream model output, tool output, approvals, and state transitions
- a browser dashboard shows the session as an event-driven view into the runtime

The architecture should optimize for:

- inspectability
- replayability
- resumability
- strict typed boundaries
- incremental implementation

The stack constraints are:

- Python 3.14
- `uv` for package management
- `ruff` for linting and formatting
- `pytest` for testing
- `ty` for type checking
- `pre-commit` for local enforcement
- `pydantic-ai` for model interaction
- `pydantic` for all internal data structures

## Architectural Thesis

Glassbox should be architected as an event-driven agent runtime with two frontends:

- a terminal frontend
- a browser frontend

The runtime is the source of truth. The CLI and dashboard are projections over the same typed event stream.

This is the key design decision. The dashboard is not a separate application that pokes into runtime internals. It is a consumer of persisted and streamed events. The CLI should also render from those same events wherever practical.

That architecture provides:

- deterministic replay
- session resume
- debuggable state transitions
- multiple UIs without duplicated runtime logic
- a natural place to insert persistence, approvals, and auditability

## Runtime Model

The first implementation should be a single async process.

That process hosts:

- the CLI session entrypoint
- the agent runtime
- the tool runtime
- the event bus
- the event store
- the dashboard web server

This avoids premature service decomposition. A single-process design is easier to build, test, and reason about while preserving the same core abstractions needed for a future split-process architecture.

## Top-Level Subsystems

### Session Supervisor

Responsible for:

- creating sessions
- resuming sessions
- stopping sessions
- loading persisted session state
- owning session-scoped configuration
- coordinating top-level lifecycle

The session supervisor does not directly talk to the model or tools. It delegates that work to the turn engine and tool registry.

### Turn Engine

Responsible for:

- receiving user input
- assembling runtime context
- starting a turn
- invoking the LLM through `pydantic-ai`
- handling streamed model output
- interpreting tool requests
- deciding whether to continue, pause for approval, or complete the turn

The turn engine is the control plane of the harness.

### Tool Runtime

Responsible for:

- executing typed tools
- streaming partial output for long-running operations
- enforcing policy decisions
- capturing artifacts such as diffs, stdout, and stderr
- returning structured results to the turn engine

### Event Bus

Responsible for:

- in-process publish and subscribe
- fanout to CLI renderer and dashboard stream endpoints
- decoupling producers from projections

### Event Store

Responsible for:

- appending immutable events
- reading events by session
- checkpointing session progress
- replay support
- resume support

### Projection Layer

Responsible for building read models such as:

- current session summary
- current turn state
- live tool executions
- pending approvals
- transcript view
- token and latency metrics
- touched files and diffs

### Web Server

Responsible for:

- serving the dashboard assets
- returning a session snapshot
- streaming live events to browsers
- handling approval actions from the dashboard

## Control Flow

The main turn loop should work like this:

1. The user sends input through the CLI.
2. The session supervisor validates that the session can accept input.
3. A `UserMessageReceived` event is appended.
4. The turn engine emits `TurnStarted`.
5. The context builder assembles conversation history, tool schema, policy state, repo context, and any memory state.
6. The model adapter calls the LLM via `pydantic-ai`.
7. Streamed model text is emitted as incremental events.
8. If the model requests a tool, the tool runtime validates and executes it.
9. Tool output is emitted as streaming events.
10. The turn engine decides whether to continue the model loop, pause for approval, or finish.
11. A final assistant message is emitted.
12. A `TurnCompleted` event is appended.
13. Projections update the CLI view and dashboard view.

This flow must be resumable at event boundaries.

## State Machine

At the session level:

- `idle`
- `running`
- `awaiting_approval`
- `completed`
- `failed`
- `cancelled`

At the turn level:

- `pending`
- `building_context`
- `calling_model`
- `streaming_model`
- `executing_tool`
- `awaiting_approval`
- `assembling_response`
- `completed`
- `failed`

At the tool execution level:

- `requested`
- `authorized`
- `running`
- `succeeded`
- `failed`
- `cancelled`

Each state transition should be backed by one or more persisted events. Avoid implicit transitions stored only in memory.

## Event-Sourced Core

Glassbox should use append-only domain events as the primary source of truth.

Events should be:

- immutable
- versioned
- timestamped
- session-scoped
- strongly typed with Pydantic
- serializable without lossy transformations

Every meaningful runtime mutation should correspond to an event. That includes user inputs, model chunks, tool start and finish, approval requests, and errors.

### Base Event Contract

All events should include the following fields:

```python
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EventEnvelope(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    sequence: int
    event_type: str
    event_version: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: "EventPayload"
```

`sequence` must be monotonically increasing within a session.

### Event Payload Base

```python
from pydantic import BaseModel, ConfigDict


class EventPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
```

### Core Event Types

The initial implementation should include at least these event payloads.

#### Session Events

```python
class SessionStarted(EventPayload):
    cwd: str
    dashboard_url: str | None = None
    model_name: str
    approval_mode: str


class SessionResumed(EventPayload):
    from_sequence: int


class SessionCompleted(EventPayload):
    reason: str


class SessionFailed(EventPayload):
    error_message: str
    retryable: bool = False
```

#### Message Events

```python
from typing import Literal


class MessagePart(BaseModel):
    kind: Literal["text", "tool_result", "reasoning_summary"]
    text: str


class UserMessageReceived(EventPayload):
    message_id: UUID
    text: str


class AssistantMessageStarted(EventPayload):
    message_id: UUID


class AssistantMessageDelta(EventPayload):
    message_id: UUID
    delta: str


class AssistantMessageCompleted(EventPayload):
    message_id: UUID
    parts: list[MessagePart]
```

#### Turn Events

```python
class TurnStarted(EventPayload):
    turn_id: UUID
    trigger_message_id: UUID


class TurnStatusChanged(EventPayload):
    turn_id: UUID
    status: str


class TurnCompleted(EventPayload):
    turn_id: UUID
    outcome: Literal["completed", "awaiting_approval", "failed"]


class TurnFailed(EventPayload):
    turn_id: UUID
    error_message: str
```

#### Model Events

```python
class ModelCallStarted(EventPayload):
    turn_id: UUID
    provider: str
    model_name: str


class ModelCallCompleted(EventPayload):
    turn_id: UUID
    input_tokens: int | None = None
    output_tokens: int | None = None
    duration_ms: int


class ModelToolCallRequested(EventPayload):
    turn_id: UUID
    tool_call_id: UUID
    tool_name: str
    arguments_json: str
```

#### Tool Events

```python
class ToolExecutionStarted(EventPayload):
    turn_id: UUID
    tool_call_id: UUID
    tool_name: str


class ToolOutputChunk(EventPayload):
    turn_id: UUID
    tool_call_id: UUID
    stream: Literal["stdout", "stderr", "structured"]
    chunk: str


class ToolArtifactRecorded(EventPayload):
    turn_id: UUID
    tool_call_id: UUID
    artifact_id: UUID
    artifact_kind: str
    path: str | None = None


class ToolExecutionCompleted(EventPayload):
    turn_id: UUID
    tool_call_id: UUID
    success: bool
    exit_code: int | None = None
    summary: str
```

#### Approval Events

```python
class ApprovalRequested(EventPayload):
    approval_id: UUID
    turn_id: UUID
    reason: str
    subject: str


class ApprovalResolved(EventPayload):
    approval_id: UUID
    decision: Literal["approved", "denied"]
    decided_by: str
```

#### Diagnostic Events

```python
class RuntimeNoteRecorded(EventPayload):
    category: str
    message: str


class ErrorRecorded(EventPayload):
    scope: Literal["session", "turn", "tool", "web"]
    message: str
```

### Event Union

Use a discriminated union for payload types:

```python
from typing import Annotated

from pydantic import Field


EventPayloadType = Annotated[
    (
        SessionStarted
        | SessionResumed
        | SessionCompleted
        | SessionFailed
        | UserMessageReceived
        | AssistantMessageStarted
        | AssistantMessageDelta
        | AssistantMessageCompleted
        | TurnStarted
        | TurnStatusChanged
        | TurnCompleted
        | TurnFailed
        | ModelCallStarted
        | ModelCallCompleted
        | ModelToolCallRequested
        | ToolExecutionStarted
        | ToolOutputChunk
        | ToolArtifactRecorded
        | ToolExecutionCompleted
        | ApprovalRequested
        | ApprovalResolved
        | RuntimeNoteRecorded
        | ErrorRecorded
    ),
    Field(discriminator="event_type"),
]
```

In practice, this is easier to maintain if each payload model includes a literal discriminator field such as `event_type`.

## Session Domain Models

These models represent the current runtime state and projection inputs.

```python
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SessionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_name: str
    cwd: Path
    approval_mode: str
    dashboard_host: str = "127.0.0.1"
    dashboard_port: int = 8765
    persist_events: bool = True
    max_turns_per_input: int = 12


class SessionState(BaseModel):
    session_id: UUID
    status: str
    current_turn_id: UUID | None = None
    last_sequence: int = 0
    pending_approval_id: UUID | None = None
```

```python
class TranscriptMessage(BaseModel):
    message_id: UUID
    role: Literal["user", "assistant", "system"]
    parts: list[MessagePart]
    created_at: datetime


class ToolCallRecord(BaseModel):
    tool_call_id: UUID
    turn_id: UUID
    tool_name: str
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    summary: str | None = None
```

## Tool System Design

Tools must be typed and policy-controlled.

Each tool should define:

- a public tool name
- a Pydantic input model
- a Pydantic output model
- an execution coroutine
- a risk class
- a streaming policy

### Base Tool Contract

```python
from typing import Generic, TypeVar

InputModel = TypeVar("InputModel", bound=BaseModel)
OutputModel = TypeVar("OutputModel", bound=BaseModel)


class ToolSpec(BaseModel):
    name: str
    description: str
    risk_level: Literal["safe", "confirm", "blocked"]
    supports_streaming: bool = False


class ToolContext(BaseModel):
    session_id: UUID
    turn_id: UUID
    cwd: Path


class ToolResult(BaseModel):
    success: bool
    summary: str
    output: BaseModel | None = None
```

### Initial Tool Set

The first version should implement a minimal, high-value set:

- `read_file`
- `search_files`
- `apply_patch`
- `run_command`
- `run_tests`
- `git_status`
- `list_dir`
- `ask_user`

The `run_command` tool should stream stdout and stderr as event chunks.

### Policy Layer

Tool policy must be separate from the tool implementation.

Example policy rules:

- read-only repo operations: auto-approve
- file edits inside workspace: configurable, default to confirm
- network access: blocked or confirm-only
- destructive filesystem commands: blocked
- commands outside workspace: blocked

Represent policy decisions explicitly:

```python
class PolicyDecision(BaseModel):
    allowed: bool
    requires_approval: bool
    reason: str
```

## LLM Integration Design

`pydantic-ai` should be treated as the model orchestration layer, not the whole application architecture.

It should be responsible for:

- talking to the provider
- structured tool calling
- parsing model outputs
- streaming partial model responses

Glassbox should remain responsible for:

- prompt building
- session lifecycle
- policy enforcement
- persistence
- approvals
- event emission
- dashboard integration

### Prompt Builder Responsibilities

The prompt builder should gather:

- system instructions
- conversation transcript
- tool schema descriptions
- repo context summaries
- current policy state
- relevant runtime notes

Avoid embedding raw runtime objects into model prompts. Use stable, typed summaries.

## Persistence Design

Use SQLite first.

SQLite is sufficient for a local-first agent harness and provides better consistency than ad hoc file persistence while keeping operational complexity low.

The recommended database direction is spelled out in [database.md](./database.md). At the architecture level, Glassbox should use a hybrid model:

- append-only `events` as the canonical source of truth
- indexed correlation columns on `events` for common lookups
- rebuildable projection tables for read-heavy views
- filesystem artifacts for large blobs such as logs and diffs

### Minimum Storage Layout

- `sessions` table for coarse session metadata
- `events` table for append-only event envelopes
- projection tables for transcript, tool state, approvals, and current session state
- optional `checkpoints` table for fast resume snapshots or rebuild shortcuts;
    deferred for v1 unless replay cost grows beyond what projections and sequence-based
    reconnects can handle cleanly
- artifact directory for larger blobs

### Suggested Schema Shape

```sql
create table sessions (
    session_id text primary key,
    status text not null,
    created_at text not null,
    updated_at text not null,
    cwd text not null,
    model_name text not null,
    approval_mode text not null,
    last_sequence integer not null default 0
);

create table events (
    session_id text not null,
    sequence integer not null,
    event_id text not null,
    event_type text not null,
    event_version integer not null,
    created_at text not null,
    turn_id text,
    message_id text,
    tool_call_id text,
    approval_id text,
    actor text,
    payload_json text not null,
    primary key (session_id, sequence),
    unique (event_id)
);
```

The event log remains authoritative. The extra identifier columns exist only to make common queries practical without forcing every dashboard or runtime lookup through JSON extraction.

Artifacts such as command logs and diffs should live on disk under a session-scoped artifact directory. Their metadata should be referenced by events.

## Projection Design

Projections convert events into query-friendly state.

In practice, these should be persisted as rebuildable database tables rather than existing only as in-memory runtime objects.

The initial projections should be:

- `SessionSummaryProjection`
- `TranscriptProjection`
- `CurrentTurnProjection`
- `ToolExecutionProjection`
- `ApprovalQueueProjection`
- `MetricsProjection`

Each projection should be:

- rebuildable from events
- deterministic
- side-effect free
- disposable and recoverable from the canonical event log

The dashboard and CLI should depend on projections, not on mutable runtime internals.

The detailed projection-table direction lives in [database.md](./database.md), but the important architectural rule is simple: projections are read models, not a second source of truth.

## Dashboard Design

The dashboard should be a thin client over the runtime.

### Transport

Use:

- HTTP for snapshot and commands
- server-sent events for live streaming

SSE is a better first fit than WebSockets because the dominant direction is server-to-client streaming.

### Endpoints

The first server surface should include:

- `GET /healthz`
- `GET /sessions/{session_id}` for a snapshot view
- `GET /sessions/{session_id}/events` as an SSE stream
- `POST /sessions/{session_id}/approvals/{approval_id}` to resolve approvals

### Dashboard Panes

The first UI should show:

- transcript timeline
- current turn status
- active tool calls
- live command output
- pending approvals
- recent file diffs
- event log feed
- basic token and latency metrics

This is sufficient to achieve the “view into the brain” experience without requiring a full IDE in the browser.

## CLI Design

The CLI is the primary operator interface.

It should support:

- starting a new session
- resuming a session
- sending a prompt
- approving or denying actions
- opening the dashboard URL
- printing session status

The CLI renderer should subscribe to runtime events and produce a concise terminal view rather than printing directly from internal subsystems.

### Initial Command Surface

```text
glassbox run [PROMPT]
glassbox resume SESSION_ID
glassbox status SESSION_ID
glassbox approve SESSION_ID APPROVAL_ID
glassbox deny SESSION_ID APPROVAL_ID
```

`glassbox status` should read persisted projections and summarize the current turn,
pending approvals, recent tool activity, and recent turn metrics without replaying
raw events ad hoc in the CLI.

## Concurrency Model

Use structured asyncio throughout.

Concurrent concerns include:

- model streaming
- subprocess streaming
- event persistence
- SSE client fanout
- approval waiting

Guidelines:

- prefer `asyncio.TaskGroup`
- avoid threads unless forced by an external API
- preserve backpressure boundaries between producers and subscribers
- treat cancellation as a normal control path

## Module Boundaries

The package layout should reflect architectural boundaries rather than technical trivia.

```text
src/glassbox/
    __init__.py
    cli/
        __init__.py
        app.py
        commands.py
        renderer.py
    core/
        __init__.py
        ids.py
        models.py
        events.py
        types.py
    runtime/
        __init__.py
        supervisor.py
        turn_engine.py
        context_builder.py
        approvals.py
        policies.py
    llm/
        __init__.py
        agent.py
        prompts.py
        adapters.py
    tools/
        __init__.py
        base.py
        registry.py
        read_file.py
        search_files.py
        apply_patch.py
        run_command.py
        run_tests.py
        git_status.py
        ask_user.py
    store/
        __init__.py
        sqlite.py
        events.py
        projections.py
        artifacts.py
    web/
        __init__.py
        app.py
        routes.py
        sse.py
        schemas.py
    services/
        __init__.py
        session_service.py
        projection_service.py
    tests/
        unit/
        integration/
        e2e/
```

### Boundary Rules

- `core` contains pure domain types and no framework code.
- `runtime` depends on `core`, `llm`, `tools`, and `store`.
- `tools` depends on `core` and minimal runtime contracts.
- `web` depends on `services`, `store`, and `core`, but should not own business logic.
- `cli` depends on `services` and runtime entrypoints, not on tool implementations directly.

## Service Interfaces

Keep service interfaces narrow and explicit.

```python
class SessionService(Protocol):
    async def start_session(self, config: SessionConfig) -> SessionState: ...
    async def resume_session(self, session_id: UUID) -> SessionState: ...
    async def submit_user_message(self, session_id: UUID, text: str) -> None: ...
    async def resolve_approval(
        self,
        session_id: UUID,
        approval_id: UUID,
        decision: Literal["approved", "denied"],
    ) -> None: ...
```

## Error Handling

Errors should not disappear into logs.

Every operationally relevant error should result in an event. Differentiate between:

- model errors
- tool errors
- persistence errors
- policy rejections
- user cancellations

Use typed exceptions internally, but translate them into explicit events at runtime boundaries.

## Observability

The dashboard is a user-facing observability surface, but the runtime still needs proper internal instrumentation.

Track at minimum:

- model call duration
- command duration
- token counts when available
- approval latency
- event append latency
- projection rebuild time

Metrics can remain in-process initially and be derived into projections. External metrics systems are not necessary in the first version.

## Testing Strategy

Testing should follow the architecture.

### Unit Tests

Validate:

- event serialization and deserialization
- projection behavior
- policy decisions
- tool input validation
- prompt assembly

### Integration Tests

Validate:

- turn loop lifecycle
- persistence and replay
- streamed tool output
- approval pause and resume
- SSE event delivery

### End-to-End Tests

Validate:

- CLI starts a session and serves dashboard
- a prompt triggers a tool call and final response
- a session can be resumed from persisted events

The most important tests are event-centric integration tests. They verify that the runtime emits the right sequence of events for a given user action.

## Security and Safety Posture

Glassbox is a local developer tool, but it still needs hard boundaries.

The first version should enforce:

- workspace scoping for file operations
- explicit approval for risky actions
- blocked destructive shell patterns
- clear attribution for approved actions
- no hidden network access by default

Do not let the model directly invoke arbitrary Python functions without going through the tool policy layer.

## First Implementation Milestones

### Milestone 1: Skeleton Runtime

- package scaffold
- core Pydantic models
- event envelope and store
- session supervisor
- basic CLI entrypoint

### Milestone 2: Minimal Agent Loop

- `pydantic-ai` integration
- one or two read-only tools
- transcript projection
- terminal rendering

### Milestone 3: Live Dashboard

- embedded web server
- session snapshot endpoint
- SSE event stream
- minimal dashboard panes

### Milestone 4: Write-Capable Tooling

- patch tool
- command runner
- approval workflow
- diff artifacts

### Milestone 5: Resume and Replay

- checkpointing
- replayable projections
- session resume CLI
- richer dashboard inspection

## Recommended Initial Non-Goals

Avoid these in the first implementation:

- multi-user remote sessions
- distributed worker processes
- plugin ecosystems
- browser-based code editing
- autonomous background daemons
- fine-grained permission sandboxes beyond simple workspace policy

These are legitimate later directions, but they will slow down learning the core harness shape.

## Architectural Summary

Glassbox should be built around a single idea: the runtime emits typed events, and every operator-facing view is a projection of those events.

That gives the project the core properties needed for a Codex or Claude Code style experience:

- the CLI can feel live and structured
- the dashboard can expose internal activity in real time
- sessions can be resumed and replayed
- approvals and tool actions become explicit state, not hidden control flow
- model orchestration remains separated from system orchestration

This document is the basis for implementation scaffolding. The next practical step is to create the package structure and encode these contracts into actual Pydantic models and runtime interfaces.
