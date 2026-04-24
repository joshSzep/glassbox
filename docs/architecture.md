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

For interactive terminal UX, this means the first-class conversational experience
should also live inside that same process. A long-lived CLI session can keep an
event subscription open, render runtime activity continuously, and submit
follow-up operator input through the existing session service. In v1, that
interactive experience is intentionally process-local rather than daemon-backed.
An attached terminal can reopen and continue a persisted paused or idle session,
but it should not claim to stream live events from another already-running
process until the runtime grows an explicit cross-process attach mechanism.

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
- `awaiting_user_input`
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
    parent_session_id: UUID | None = None
    forked_from_turn_id: UUID | None = None
    forked_from_sequence: int | None = None
    branch_label: str | None = None


class SessionResumed(EventPayload):
    from_sequence: int


class SessionCompleted(EventPayload):
    reason: str


class SessionFailed(EventPayload):
    error_message: str
    retryable: bool = False
```

`SessionFailed` is reserved for session-scoped runtime failures that leave the
session unable to continue safely. It should not be used for normal model,
tool, or policy errors that only fail the current turn.

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
    outcome: Literal["completed", "awaiting_approval", "awaiting_user_input", "failed"]


class TurnFailed(EventPayload):
    turn_id: UUID
    error_message: str
```

`TurnFailed` is the recoverable failure path for a single turn. A session may
remain `running` after a `TurnFailed` event so the operator can inspect the
result, resume work, or submit a new message.

## Failure Semantics

Glassbox distinguishes between turn-scoped failures and session-scoped
failures.

- `TurnFailed` means the active turn could not finish, but the session itself
    is still structurally valid.
- `SessionFailed` means the runtime encountered a session-level problem that
    makes further progress unsafe without repair or reconfiguration.

Examples of `TurnFailed` conditions:

- model execution errors
- tool execution errors
- policy-blocked tool requests

Examples of `SessionFailed` conditions:

- corrupted persisted session configuration
- runtime bootstrap failures that prevent future turns from being constructed

This distinction matters for operators and projections:

- `TurnFailed` updates turn state and leaves the session available for further
    work unless another event changes session status.
- `SessionFailed` clears any pending suspended-turn pointers and moves the
    session into terminal `failed` state.

Persisted session configuration should be validated before it is written.
Runtime-side `SessionFailed` emission remains a defensive fallback for rows that
become invalid through external corruption or manual database edits.

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


class ReplayArtifactRecorded(EventPayload):
    turn_id: UUID
    artifact_id: UUID
    artifact_kind: str
    path: str | None = None
    tool_call_id: UUID | None = None


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
    tool_call_id: UUID | None = None
    provider_tool_call_id: str | None = None


class ApprovalResolved(EventPayload):
    approval_id: UUID
    decision: Literal["approved", "denied"]
    decided_by: str


class UserQuestionAsked(EventPayload):
    question_id: UUID
    turn_id: UUID
    tool_call_id: UUID
    provider_tool_call_id: str
    question: str


class UserAnswerProvided(EventPayload):
    question_id: UUID
    answer: str
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
        | ReplayArtifactRecorded
        | ToolExecutionCompleted
        | ApprovalRequested
        | ApprovalResolved
        | UserQuestionAsked
        | UserAnswerProvided
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
    dashboard_url: str | None = None
    parent_session_id: UUID | None = None
    forked_from_turn_id: UUID | None = None
    forked_from_sequence: int | None = None
    branch_label: str | None = None


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
    parent_session_id text,
    forked_from_turn_id text,
    forked_from_sequence integer,
    branch_label text,
    last_sequence integer not null default 0
);

create index idx_sessions_parent_updated
    on sessions (parent_session_id, updated_at desc);

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
Replay manifests and exported replay bundles should follow the same rule: keep
large or structured baseline payloads in session-scoped artifacts and reference
them from stable typed metadata rather than copying them blindly into event
rows.

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

## Session Branching And Time-Travel Model

Session branching is a separate operator workflow from both raw historical
inspection and deterministic replay. It answers a different question from each:

- historical inspection asks what happened during the original session
- branching asks what should happen next if the operator wants to continue from an earlier stable point
- deterministic replay asks whether the current Glassbox codebase still reproduces equivalent behavior against a recorded baseline

Glassbox should support time-travel in v1 by creating a new child session from
an explicitly selected historical cut point. The source session remains
immutable. Time-travel is therefore branch creation, not event-log mutation,
session rewind, or destructive rollback.

### Operator Model

The intended v1 operator flow is:

1. inspect a persisted session from the CLI or dashboard
2. choose a stable historical cut point, usually the latest completed turn or a selected completed turn
3. create a new child session from that point
4. continue work in the child session using the normal prompt, answer, approval, replay, and dashboard workflows

This keeps the runtime honest about what happened historically while still
making exploration practical. The parent session remains the audit record of the
original path. The child session becomes the audit record of the alternate path.

The first intended operator surface should stay explicit:

- CLI should expose a dedicated fork action such as `glassbox fork SESSION_ID`
- the CLI may later accept an explicit historical turn selector such as `--turn TURN_ID`
- the dashboard should treat forking as a persisted session action over a selected historical cut point, not as a browser-local state transformation

### Stable Fork-Point Contract

Valid v1 fork points should be stable turn boundaries only:

- the latest completed turn in a session
- an explicitly selected completed turn in a session's historical timeline

Invalid v1 fork points should include at least:

- a currently running turn
- unresolved approval suspension points
- unresolved `ask_user` suspension points
- mid-stream model output or tool execution
- corrupted or ambiguous historical state that cannot be resolved to a deterministic boundary

The operator-facing contract should talk about turn boundaries, even if the
runtime resolves the final fork point internally to a concrete event sequence.

### Scope Boundary

The v1 scope should stay deliberately narrow:

- create a new child session rather than mutating the parent
- preserve parent-child lineage explicitly
- materialize enough inherited conversation history into the child session for normal continuation
- keep child sessions compatible with existing snapshot, status, replay, and eval workflows

The following are intentionally out of scope for v1:

- in-place session rewind
- deleting or truncating canonical events from a source session
- branching from transient in-flight turn state
- requiring checkpoint restoration just to create a branch
- treating the dashboard as a second runtime that can rewrite history locally

### Persistence Direction

Branching should remain faithful to the event-sourced architecture.

- the parent session keeps its original canonical event stream unchanged
- the child session records explicit lineage metadata pointing back to the parent and selected fork point
- the child session should become self-contained enough that prompt assembly, snapshots, and replay do not need to chase ancestry dynamically on every turn

That last point matters. The branch workflow should not turn normal turn
execution into a graph traversal problem. Branch creation may need to inspect
parent history, but the resulting child session should continue to behave like a
first-class ordinary session once created.

The current direction for that materialization is:

- resolve the fork boundary from the parent session's canonical events together with the projected suspension state
- carry forward only the normalized transcript needed for continuation, rather than replaying every parent event into the child
- record those inherited messages as canonical child-session import events with deterministic child message IDs derived from the child session and source message identity

## Deterministic Replay And Eval Model

Deterministic replay is a separate operator workflow from raw history
inspection. Glassbox should support four distinct modes of looking at prior
work:

- historical inspection of persisted events, projections, and artifacts
- historical branch creation from a stable prior cut point
- offline deterministic replay against recorded manifests and stubbed outputs
- optional future live-provider comparison runs that are useful for research but are not part of the deterministic baseline contract

These modes answer different questions.

- historical inspection asks what happened during the original session
- branching asks what should happen next from an earlier stable point while preserving the original audit trail
- deterministic replay asks whether the current Glassbox codebase still produces equivalent behavior against a recorded baseline
- future live comparison asks how current providers behave now, which is valuable later but is intentionally outside the v1 deterministic contract

### Replay Baseline Capture

Replay should be grounded in recorded turn manifests rather than inferred after
the fact from raw event envelopes alone.

For each replayable turn, Glassbox should capture enough structured baseline
data to reconstruct the control path offline, including:

- the assembled model context or a normalized equivalent
- tool schema and policy snapshot relevant to the turn
- provider and model fingerprint information that is safe to persist
- normalized tool requests and deterministic tool result payloads
- references to larger replay artifacts stored on disk when the payload is too large for normal event rows

Replay manifests should be:

- typed and versioned
- redacted so secrets and runtime-only credentials never land in replay artifacts
- linked from session or turn metadata rather than discovered through ad hoc filesystem scans
- suitable for later export into portable replay bundles

### Replay Scope And Equivalence Rules

The first deterministic replay implementation should stay local-first and
offline. It must not issue live network calls, spawn real subprocesses, or
mutate the workspace just to compare current behavior against a baseline.

The v1 comparison scope should cover:

- transcript output and final message content
- tool lifecycle transitions and normalized tool results
- approval request and resolution flow
- `ask_user` question and answer suspension flow
- final projected session state after replay completes

The default comparison should normalize away fields that are not stable enough
to be meaningful deterministic invariants, such as:

- timestamps
- sequence numbers allocated by the replay run itself
- fresh UUIDs and other runtime-generated identifiers
- duration and token metrics unless a later eval case opts into checking them explicitly

If a session depends on behavior that cannot yet be replayed under those rules,
Glassbox should surface that explicitly as unsupported rather than silently
downgrading the comparison.

### Replay Result Taxonomy

Deterministic replay should report outcomes using a small, stable taxonomy.

- exact match: current normalized behavior matches the recorded baseline
- manifest drift: current context assembly, tool schema, or policy state no longer reproduces the recorded replay manifest before playback meaningfully begins
- behavioral drift: replay can proceed, but transcript output, tool results, suspension flow, or final projected state diverges from the baseline
- unsupported session: the recorded session includes unsupported providers, tools, artifacts, or schema versions for deterministic replay
- replay failure: the replay machinery itself cannot complete because of corruption, missing artifacts, or an implementation defect

This taxonomy matters because prompt/context regressions should not be collapsed
into the same bucket as downstream tool or transcript regressions.

### Replay Runner Execution Strategy

The implemented v1 replay runner loads recorded replay manifests from the source
session, builds a replay bundle, then replays the same user-message,
approval-resolution, and ask-user answer sequence through a fresh isolated
session database.

To keep replay offline while still exercising the current control plane, the
runner:

- uses the real session supervisor, context builder, turn engine, and policy evaluation path
- swaps in replay-backed model execution that validates the current prepared turn against the recorded manifest before serving recorded outputs
- swaps in replay-backed tool execution that validates the current prepared tool request against the recorded manifest before serving recorded tool results
- compares normalized transcript output, tool-call projections, approval and question flow, emitted event families, and final projected session state against the recorded baseline

### Operator Workflow

The operator workflow should remain explicit and reviewable:

1. run a normal session and retain replay manifests plus redacted replay artifacts as part of the persisted session record
2. run an offline single-session replay against the recorded baseline to check for exact match or drift
3. export a portable replay bundle when a session should become a durable baseline outside the original local database
4. promote selected bundles into curated eval cases that can be run locally or in CI

This workflow complements rather than replaces the existing inspection
commands. Raw history inspection still explains what happened in a session.
Replay and evals exist to detect whether Glassbox still behaves equivalently
under the current codebase.

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
- `GET /sessions` for recent-session discovery in the standalone dashboard
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
- starting a new interactive session
- attaching to an existing session interactively
- resuming a session
- sending a prompt
- answering a pending ask-user question
- approving or denying actions
- opening the dashboard URL
- printing session status

The CLI renderer should subscribe to runtime events and produce a concise terminal view rather than printing directly from internal subsystems.

The CLI should expose two complementary layers:

- interactive commands for the normal conversational workflow
- non-interactive commands for scripting, recovery, and explicit low-level control

### Scriptable Command Surface

```text
glassbox run [PROMPT]
glassbox message SESSION_ID PROMPT
glassbox answer SESSION_ID QUESTION_ID ANSWER
glassbox resume SESSION_ID
glassbox status SESSION_ID
glassbox approve SESSION_ID APPROVAL_ID
glassbox deny SESSION_ID APPROVAL_ID
glassbox rebuild [SESSION_ID | --all]
glassbox serve
```

`glassbox status` should read persisted projections and summarize the current turn,
pending approvals, recent tool activity, and recent turn metrics without replaying
raw events ad hoc in the CLI.

Approval and ask-user pause points are resumable from persisted events. The runtime
uses `ApprovalRequested` / `ApprovalResolved` and `UserQuestionAsked` /
`UserAnswerProvided` event pairs to suspend and resume turns explicitly.

These commands remain the source of truth for explicit session actions even after
an interactive terminal mode exists. They are important for scripts, debugging,
recovery workflows, and any case where the operator wants exact control over IDs
and state transitions.

### Replay And Eval Commands

Deterministic replay and evals add a second operator loop that sits alongside
the normal runtime commands.

Current command surface:

```text
glassbox replay SESSION_ID [--json]
glassbox replay --bundle BUNDLE_PATH [--json]
glassbox replay-export SESSION_ID [OUTPUT]
glassbox eval run [CASE_ID ...] [--tag TAG] [--json] [--output-dir DIR]
```

The semantics should stay narrow:

- `glassbox replay` compares the current codebase against a recorded session baseline offline, returns concise human output by default, supports machine-readable JSON output, and reports exact match, manifest drift, behavioral drift, unsupported session, or replay failure
- `glassbox replay --bundle` consumes a portable replay bundle directly, so exported baselines can be replayed without the original session database and can run against the current workspace root instead of the source machine path
- `glassbox replay` uses stable exit codes so scripts can distinguish exact match from drift and replay errors without scraping terminal text
- `glassbox replay` does not mutate the source session metadata or recorded replay artifacts; replay runs against an isolated temporary session store
- replay export turns a replayable session into a portable baseline bundle that can move across branches, repositories, or CI machines without the original SQLite database
- `glassbox eval run` executes curated replay cases serially from the repository-local `evals/` layout, returns a CI-friendly suite summary, and does not require live provider credentials for deterministic cases
- `glassbox eval run --tag ...` narrows the suite to tagged cases, while explicit `CASE_ID` arguments preserve an operator-controlled selection order for focused validation
- `glassbox eval run --json` emits a machine-readable suite report including per-case outcomes, expectation-aware pass/fail state, and artifact paths
- `glassbox eval run` writes one JSON artifact per executed case plus `summary.json` under the selected output directory so batch failures stay debuggable after CI or local runs

Portable replay bundles are a stable, versioned JSON envelope around the normalized
replay baseline:

- they embed the recorded replay manifests and normalized comparison baseline rather than referencing the original artifact files indirectly
- they preserve replay-capture redaction, so provider secrets and other sensitive model settings stay scrubbed when the bundle is checked into a repository or moved to CI
- they intentionally retain source workspace context metadata while avoiding unrelated local artifact-path leakage, and bundle-version mismatches fail clearly before replay runs

### Eval Case Layout

Replay-backed eval suites are repository-local manifests rooted under `evals/`.
The batch runner now consumes that layout directly, so baselines can be curated,
reviewed, and executed without custom repository glue.

Default repository layout:

```text
evals/
    README.md
    bundles/
        CASE_ID.json
    cases/
        CASE_ID.json
```

Each case manifest is a versioned JSON document with:

- `case_id`: stable lowercase identifier used for selection and reporting
- `title`: human-readable scenario name for summaries and reviews
- `bundle_path`: relative path to the exported replay bundle, typically under `evals/bundles/`
- `tags`: optional scope labels such as `smoke`, `tooling`, `approval`, or `provider-mode`
- `notes`: optional reviewer context about capture intent or known caveats
- `expectation`: comparison contract, defaulting to `exact_match` but allowing explicit `selected_invariants` cases like `final_state` only

Case manifests must keep `bundle_path` relative and inside the repository root.
That keeps checked-in baselines portable, reviewable, and free of accidental
references to arbitrary machine-local paths.

The baseline-promotion workflow is intentionally explicit:

1. capture or identify a replayable session
2. export its portable baseline into `evals/bundles/CASE_ID.json`
3. add `evals/cases/CASE_ID.json` that points at the bundle and declares tags and expectations
4. review bundle and case changes together when promoting or refreshing a baseline

Batch eval execution consumes those manifests directly. Each case still replays in
isolation against the current workspace root, so one failing or drifting case does
not contaminate later ones or mutate any source session database.

That separation keeps the bundle as recorded evidence and the case manifest as
the repository-owned regression contract.

These commands should stay complementary to `pytest` rather than replacing it.
The purpose is replay-backed behavioral regression coverage, not a second
general-purpose unit-test framework.

### Local-First Verification Policy

Glassbox assumes a local-first development loop where `git commit` and
`git push origin main` are the normal path. Replay and eval verification should
therefore be ordered around the earliest useful local barrier rather than around
pull-request gates or branch protection.

The verification contract is:

1. commit-time local gates block bad changes before they enter history
2. push-time confirmation reruns broader replay or eval coverage after `origin`
   receives the new commit and retains artifacts for review
3. optional scheduled suites may run later for wider advisory coverage, but they
   do not replace the local barrier

For this repository, `pre-commit` is the primary early-regression barrier. The
existing blocking hook stack already runs formatting, lint, type-check, and
`pytest` locally. Curated replay-backed smoke evals should join that same
commit-time path instead of being deferred to CI or a post-push bot.

The intended tag policy is:

- `smoke`: blocking at commit time because these cases should stay small,
  stable, and representative of the highest-value replay contracts
- broader tags such as `tooling`, `approval`, or future provider-oriented
  buckets: allowed to run after push as confirmation when they are too slow,
  too artifact-heavy, or too numerous for every commit
- later scheduled suites: advisory only, useful for trend detection and wider
  drift discovery, but not the first place regressions should surface

Operator expectations should stay explicit:

- a commit-time replay or eval failure means the change should be investigated before creating history, because the local barrier has already found a drift against a curated regression contract
- a post-push failure means a broader confirmation suite found drift that was intentionally outside the blocking local smoke set; it still matters, but it indicates the smoke barrier was incomplete rather than absent

This policy keeps replay and eval aligned with the rest of the repository's
local enforcement model: catch the cheapest high-value regressions before
commit, then use post-push automation for confirmation, artifact retention, and
visibility rather than as the first line of defense.

### Interactive Command Surface

The primary conversational UX should move toward a persistent terminal session
rather than repeated one-shot command invocations.

```text
glassbox chat [PROMPT]
glassbox attach SESSION_ID
```

`glassbox chat` starts a new session and keeps the operator inside a long-lived
terminal loop. `glassbox attach` opens that same interactive terminal workflow
for an existing persisted session.

In v1, `attach` should support reopening sessions that are actionable from the
current process, such as idle running sessions, awaiting-user-input sessions,
and other paused states that can be continued from persisted projections. It
should not promise live streaming from another already-running process, because
the current event bus is in-process only.

### Co-Hosted Dashboard During `chat`

The interactive `chat` workflow should also be able to expose the dashboard from
the same owning process.

This should be treated as a co-hosted sidecar over the existing runtime context,
not as a second runtime stack. The same process should continue to own:

- the interactive terminal loop
- the runtime services
- the event bus
- the persisted event stream
- the embedded dashboard server

The intended command surface is:

```text
glassbox chat [PROMPT] [--dashboard-host HOST] [--dashboard-port PORT] [--no-dashboard]
```

Semantics:

- `glassbox chat` should attempt to start a dashboard by default so the browser view is available while the interactive session is in progress
- `--no-dashboard` should suppress the co-hosted dashboard when the operator wants a terminal-only session
- `--dashboard-host` and `--dashboard-port` should configure the bind target for the co-hosted dashboard
- a successfully started co-hosted dashboard should print its URL during chat startup and make that URL available through session metadata

Failure behavior should preserve the conversational path as the primary UX:

- if default dashboard startup fails, `chat` should continue with an explicit warning that the dashboard is unavailable for this session
- if the operator explicitly requested dashboard configuration and startup fails, the CLI should surface a precise error rather than silently pretending the dashboard is live
- in either case, session metadata must not advertise a live dashboard URL unless the server actually started

This does not change the attach boundary from `GBX-166`. A co-hosted dashboard
for `chat` improves same-process visibility only; it does not create true
cross-process terminal attach or a daemon-backed resident runtime.

`glassbox serve` remains the standalone dashboard path for cases where the
operator wants a browser view outside an active `chat` session, wants to inspect
persisted sessions from another process, or needs explicit control over the
server lifecycle. `attach` should not automatically start the dashboard in v1;
it remains an interactive terminal re-entry path over existing persisted state.

For operator docs, the key positioning should stay explicit:

- the co-hosted dashboard is a convenience surface for the same live `chat` process and should shut down with that process
- `glassbox serve` is the durable observation path for persisted sessions and for browser access that should survive beyond a single `chat` invocation
- the printed `chat` URL can point directly at the active session with `?session=SESSION_ID`, while `serve` should start at the root session browser and keep `?session=SESSION_ID` as a direct-open path

### Standalone Dashboard Operator Model

The standalone dashboard should be treated as the persisted-session browser
console for Glassbox, not as a low-level transport demo and not as a browser
version of terminal attach.

Its primary operator jobs are:

- discover the right persisted session to inspect or recover
- show whether that session is live, paused, completed, failed, or only historically inspectable
- surface the next meaningful operator action using the same underlying prompt, answer, and approval semantics as the CLI
- remain useful even when no `chat` process is still alive to own a live in-process terminal session

The intended standalone browser flow should start from the dashboard root,
support recent-session discovery, and only then move into a selected session
view. The operator should not have to memorize or manually preserve a
`session_id` just to begin browsing persisted work. The current `?session=`
deep-link remains valid and important, but it should become the direct-open path
rather than the only practical entrypoint.

This operator model also needs an explicit state boundary:

- running or paused sessions may still be actionable through existing HTTP prompt, answer, and approval paths when the underlying session state allows it
- completed and failed sessions should remain inspectable as persisted history even when there is no live stream to attach to
- a disconnected or unavailable SSE stream should not invalidate an otherwise useful snapshot view of persisted state
- standalone browser UX should surface `connecting`, `live`, `reconnecting`, `live unavailable`, and `historical snapshot` as distinct operator signals rather than a single ambiguous disconnected state
- browser interaction in standalone mode must not imply terminal-native attach, daemon-backed runtime ownership, or cross-process prompt streaming beyond the existing HTTP and SSE surfaces

For follow-on implementation work, `glassbox serve` should optimize for session
discovery, recovery, and inspection. It should not compete with `chat` for the
same-process conversational UX; it should complement `chat` by becoming the
durable cross-process operator console over persisted sessions.

### Interactive Operator Semantics

Inside an interactive terminal session:

- the renderer stays subscribed to runtime events for the lifetime of the terminal session
- freeform user input is routed from current session state, not from ad hoc CLI guesses
- when the session is running and idle, freeform input becomes `submit_user_message(...)`
- when the session is awaiting user input, freeform input becomes `provide_user_answer(...)`
- pending `question_id` details should be discovered from persisted session state rather than copied manually during the normal flow
- approval resolution remains explicit through slash commands or equivalent structured controls instead of overloading arbitrary freeform text
- `resume` remains a lifecycle primitive after process restart, distinct from `attach`, which is the operator-facing conversational shell

The interactive prompt must always make the current expected input mode visible.
If the session is blocked or ambiguous, the terminal should say so explicitly
instead of inferring an action heuristically.

### Interactive Scope Boundary

The intended scope is deliberately split into two phases.

Phase 1:

- a process-local interactive CLI loop for new and existing sessions
- prompt routing for new prompts and pending-question answers
- explicit slash-command handling for approvals, status, help, and exit
- continuous terminal rendering while the owning CLI process remains alive

Phase 2, if justified later:

- true cross-process attach
- daemon-backed or brokered session ownership
- live terminal streaming into a client that did not start the runtime process

That boundary keeps the current architecture honest. Glassbox can become
terminal-native and conversational now without pretending it already has a
resident background runtime.

### Cross-Process Attach Decision

Decision: keep the interactive terminal UX process-local for the current
architecture. Do not introduce a daemon-backed runtime or a cross-process
terminal attach protocol in the current roadmap phase.

This is the current stance because the existing surfaces already cover most of
the operator value at materially lower complexity:

- `glassbox chat` provides the primary conversational workflow inside the owning CLI process
- `glassbox attach` can reopen persisted sessions that are actionable from projections
- `GET /sessions/{session_id}` already provides cross-process snapshot recovery
- `GET /sessions/{session_id}/events` already provides cross-process live event streaming to the dashboard
- approval and question flows are already resumable from persisted events rather than process-local memory

The remaining gap is specifically terminal-native live attach to a runtime that
is still owned by another process. That is real operator value, but it is not
large enough yet to justify the additional platform and protocol cost.

#### Tradeoff Analysis

Option 1: keep the current process-local terminal model and lean on the
existing HTTP plus SSE surfaces for cross-process observation and recovery.

Benefits:

- preserves the current single-process ownership model
- reuses the existing event store, projections, snapshot endpoint, and SSE feed
- keeps `chat` and `attach` semantics honest instead of implying capabilities the runtime does not have
- avoids introducing daemon lifecycle, background process supervision, or client attachment coordination
- keeps approval, question, and replay behavior grounded in persisted events

Costs:

- no true terminal reattachment to a still-running owner process
- terminal-native streaming remains tied to the process that started the interactive session
- cross-process observation is dashboard-first rather than terminal-first

Option 2: introduce a daemon-backed or brokered runtime with explicit
cross-process attach semantics.

Benefits:

- terminal clients could reconnect to a long-lived background runtime
- live output could survive terminal restarts and process handoff
- session ownership would become explicit rather than incidental to one CLI invocation

Costs:

- background runtime lifecycle management across platforms
- explicit session ownership, locking, and multi-client arbitration rules
- attach protocol design for prompt state, redraw, backlog replay, and live stream delivery
- health checks, cleanup, orphaned runtime handling, and upgrade behavior
- new failure modes around daemon drift, stale sockets, and split-brain ownership
- a more complex local security story once commands can target a resident process

Decision outcome: stay with Option 1 for now. Use the dashboard snapshot and
SSE surfaces for cross-process visibility, and reserve daemon-backed attach for
later only if observed operator pain clearly exceeds the added complexity.

#### Revisit Criteria

Reopen this decision only if at least one of the following becomes a repeated
operator need rather than a hypothetical capability:

- users frequently lose useful long-running terminal sessions because the owning CLI process exits
- dashboard observation proves insufficient because operators specifically need terminal-native reattachment rather than browser-based live visibility
- multiple local entrypoints need to coordinate a single active runtime instead of reopening persisted state after the fact

If this decision is revisited later, the first executable slices should be:

1. define runtime ownership and attach semantics explicitly, including single-client versus multi-client rules
2. introduce a supervised background runtime process with health and shutdown behavior
3. expose an attach transport that can replay prompt context and then stream live events to a terminal client
4. add terminal rehydration rules for prompt mode, pending approvals, and pending questions after reconnect

Those slices are intentionally not on the roadmap yet. They become valid only if
the current process-local plus dashboard model is shown to be insufficient in
practice.

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

Runtime logs are still useful for terse operational context around session, turn,
tool, approval, and question flows, but they complement persisted events rather
than replacing them as the authoritative debugging record.

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

### Milestone 6: Deterministic Replay And Eval

- replay manifest capture and redaction
- offline single-session replay
- portable replay bundle export
- declarative replay-backed eval suites

## Recommended Initial Non-Goals

Avoid these in the first implementation:

- multi-user remote sessions
- distributed worker processes
- plugin ecosystems
- browser-based code editing
- autonomous background daemons
- fine-grained permission sandboxes beyond simple workspace policy
- remote eval infrastructure or live-provider benchmark services

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
