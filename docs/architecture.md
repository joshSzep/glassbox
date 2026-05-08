# Glassbox Architecture

For the docs hub and workflow guides, start at [README.md](./README.md). For installation and first-run setup, use [getting-started.md](./getting-started.md).

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

## Current Baseline Before V2 Execution

The repository has moved beyond the earliest architecture slices. Treat the
following as the implemented baseline that v2 extends:

- `glassbox session chat` owns the live in-process conversational workflow
- `glassbox daemon start|status|stop` now provides a workspace-scoped
    background runtime owner with health and lock metadata under `.glassbox/`
- `glassbox session attach` now chooses between persisted local reopen and live
    terminal attach to a healthy daemon-owned runtime for the same workspace
- `glassbox dashboard serve` exposes the standalone browser console over persisted
    sessions, recent-session discovery, snapshot reads, HTTP actions, and SSE
    live tails
- the dashboard already behaves as a session-index-plus-deep-link operator
    surface rather than a single hard-coded session view
- the v2 operator console is defined as an extension of that dashboard shell,
    adding multi-session queues, aggregate health, and priority semantics while
    preserving the same event-sourced snapshot plus stream authority model
- replay, eval, branching, lineage-aware snapshots, and runtime-context
    inspection are existing product surfaces, not future placeholders

v2 architecture work should extend these shipped boundaries rather than restate
them as if they are still only design intent.

## Current Post-v8 Refactor Shape

The post-v8 implementation keeps the same local-first, event-sourced product
contract while splitting the autonomy-era modules that had accumulated broad
coordination responsibilities.

The important current boundaries are:

- runtime autonomy facades preserve stable public entrypoints while delegating
    background-job lifecycle, workspace-memory extraction, observability
    collection, repository-index discovery, and provider evidence into focused
    modules
- store read models and repository adapters remain the persistence boundary, but
    projection queries and adapter methods now delegate by projection or domain
    instead of growing inside one large file
- the terminal TUI keeps stable `conversation.py`, `widgets.py`, and `app.py`
    entrypoints while state models, reducers, selectors, pane widgets, stream
    handling, commands, and refresh logic live in owned neighbor modules
- the Next.js dashboard keeps a compatibility store import path and stable
    console component entrypoints while domain stores, autonomy sections, and
    session-inspector diagnostic panes are split by responsibility

These splits are refactor-only architecture. They do not add new autonomy
behavior, change event semantics, or make projection tables authoritative.

## Current Post-v13 Review-Loop Refactor Shape

The v13 review-loop implementation extends changesets from reviewable local
diff summaries into an operator workflow for local review feedback, response
tracking, manual evidence, advisory browser/dashboard/accessibility evidence,
lifecycle briefs, handoff readiness, and commit preparation. Those surfaces are
still local-first and event-sourced: canonical events and managed artifacts stay
authoritative, while projection tables, web payloads, CLI output, and dashboard
state remain derived views.

The completed post-v13 refactor keeps the current behavior and public
entrypoints while splitting the review-loop surfaces that grew during the
milestone:

- `runtime/changesets.py` is the stable changeset runtime facade while
    source derivation, workspace diff helpers, query/detail assembly, feedback
    actions, evidence actions, verification preview, safe-command guidance,
    command evidence, lifecycle brief sections, and readiness adjacency move
    into focused runtime modules
- `cli/changeset_commands.py`, `cli/parser_changesets.py`, TUI review commands,
    and plain interactive review commands stay stable terminal entrypoints while
    service wiring, payload shaping, formatting, parser families, and
    in-session review routing move into CLI-owned helpers
- `web/changeset_api.py` and `web/routes/changesets.py` remain transport
    compatibility surfaces while models, builders, service factories, request
    helpers, and HTTP error translation split into web-owned modules
- `frontend/components/console/changeset-console.tsx` remains the dashboard
    entrypoint while changeset list, detail, feedback, evidence, verification,
    handoff, commit-preparation, formatting, and shared rows move under
    `frontend/components/console/changeset/`
- `frontend/stores/changeset-store.ts` remains the dashboard store facade while
    action groups and selectors live in `changeset-store-actions.ts` and
    `changeset-store-selectors.ts`
- changeset/review-loop store projections and repository adapters continue to
    derive from canonical events and projection tables, with changeset
    lifecycle, inventory, feedback, manual evidence, query-detail, readiness,
    and repository adapter families split by owner
- `scripts/validate_v13_release_gate.py` remains the operator command while
    v13-specific gate stage construction, advisory evidence summaries, dry-run
    planning, evidence-dir resolution, and release summary metadata live in
    `scripts/v13_release_gate_helpers.py`

These splits must preserve the v13 non-claims described in
[v13-review-loop-contract.md](./v13-review-loop-contract.md) and
[publication-boundary.md](./publication-boundary.md): local review feedback is
not approval, manual and live evidence are advisory unless the event contract
says otherwise, handoff and commit preparation are read-only, and release-gate
authority remains deterministic rather than browser/dashboard/provider
advisory evidence.

## Current Post-v14 Review-Loop Maturity Refactor Shape

The v14 review-loop maturity implementation extends the v13 local review loop
with rich lifecycle limitation summaries, response-linked fixup inventory,
skipped advisory browser/dashboard/accessibility evidence, safer handoff and
commit posture, dashboard action states, advisory UX evidence, deterministic
v14 eval coverage, and a v14 release gate. These additions preserve the same
local-first authority model: canonical events and managed artifacts remain the
source of truth, while projection tables, CLI output, web payloads, dashboard
state, and release-gate summaries are derived.

The post-v14 refactor should preserve current behavior and public entrypoints
while splitting the maturity surfaces that grew during the milestone:

- `runtime/changeset_review_brief_sections.py` remains the lifecycle brief
    assembly facade while lifecycle limitation collection and summary, core
    sections, review-loop sections, and readiness derivation move into focused
    helpers
- `runtime/review_responses.py` remains the review response facade while
    response models, response-status derivation, fixup artifact construction,
    path-scope helpers, and summary assembly move into focused helpers
- `runtime/handoff_readiness.py` and `runtime/commit_readiness.py` keep
    distinct product semantics while shared signal aggregation helpers remove
    duplicated blocker, limitation, path, and safe-action shaping
- `cli/interactive_client.py` remains the plain interactive client entrypoint
    while protocols, SSE parsing, local actions, daemon actions, and
    review-loop guidance move into CLI-owned helpers
- changeset command handlers, web changeset routes, web changeset API
    builders, frontend API endpoint groups, frontend changeset store action
    families, and `scripts/v14_release_gate_helpers.py` are follow-on transport
    and release-gate pressure points

These splits must preserve the v14 non-claims described in
[v14-review-loop-maturity-contract.md](./v14-review-loop-maturity-contract.md)
and [publication-boundary.md](./publication-boundary.md): skipped advisory
evidence is never passing release evidence, response-linked fixup inventory is
not reviewer acceptance, handoff and commit readiness are read-only guidance,
dashboard action states are operator workflow state rather than approval, and
release-gate authority remains deterministic rather than advisory UX evidence.

## Runtime Model

The current shipped implementation still centers on one runtime owner per
workspace, but that owner can now be either a foreground interactive CLI
process or the background `glassbox daemon` process.

That owner process hosts:

- the CLI session entrypoint
- the agent runtime
- the tool runtime
- the event bus
- the event store
- the dashboard web server

This avoids premature service decomposition. A single-owner process is easier to
build, test, and reason about while preserving the same core abstractions needed
for a future split-process or richer persistent-runtime architecture.

For interactive terminal UX, the first-class conversational experience still
lives inside the foreground CLI process today. A long-lived CLI session can keep
an event subscription open, render runtime activity continuously, and submit
follow-up operator input through the existing session service. The daemon owner
is now also a live terminal attach target: the terminal reconnects through the
existing HTTP plus SSE control surfaces when a healthy workspace daemon already
owns the session.

That boundary was the starting point for v2 planning. `GBX-300` in
[tasks-v2.md](./tasks-v2.md) now resolves the ownership model choice, and
`GBX-301` through `GBX-304` are the follow-on implementation tasks for the
chosen persistent-runtime path.

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
- coordinating turn preparation and suspended-turn resumption
- starting a turn and recording turn-scoped lifecycle events
- invoking the shared model loop through `pydantic-ai`
- handling streamed model output and delegating tool execution side effects
- deciding whether to continue, pause for approval, or complete the turn

The turn engine is the session-facing turn coordinator of the harness. It keeps
policy about when a turn starts, resumes, fails, or completes, but it does not
own every detail of preparation, event recording, tool execution, or model-loop
state transitions inline.

For v6 cancellation semantics, the turn engine also treats cancellation as a
live-turn mutation rather than a UI-only interruption. See
[v6-cancellation-contract.md](./v6-cancellation-contract.md) for the persisted
event contract, state rules, and replay/eval expectations.

The implemented runtime split keeps those boundaries explicit:

- `runtime/turn_preparation.py` assembles the prepared turn and its runtime context
- `runtime/turn_resumption.py` reconstructs suspended approval and `ask_user` state
- `runtime/turn_tool_executor.py` owns tool-call execution side effects during a running turn
- `runtime/turn_event_recorder.py` owns persisted turn/event emission and replay capture hooks
- `runtime/model_loop.py` owns the reusable model-call and tool-loop control flow shared by live turns and replay-backed execution

### Runtime Bootstrap

Responsible for:

- resolving workspace-root and database paths
- opening initialized runtime storage
- loading provider configuration and tool-policy wiring
- assembling the concrete `RuntimeContext` used by CLI and web entrypoints

The public bootstrap surface remains `runtime/bootstrap.py`, but its ownership is
now split deliberately:

- `runtime/bootstrap_storage.py` owns storage-path resolution and SQLite initialization
- `runtime/bootstrap_provider.py` owns provider configuration and model/tool builders
- `runtime/bootstrap_assembly.py` assembles repositories, services, and infrastructure into `RuntimeContext`

### Runtime Autonomy Boundaries

The v8 autonomy surfaces are implemented as stable facades over focused
runtime-owned helpers:

- `runtime/background_jobs.py` owns the public worker loop, worker tick, and
    job-runner entrypoints. Lease recovery, stale-claim cancellation, read-only
    maintenance handlers, mutating task continuation, and job progress or
    failure recording live in `background_job_lifecycle.py`,
    `background_job_handlers.py`, `background_task_continuation.py`, and
    `background_job_records.py`.
- `runtime/workspace_memory_capture.py` owns the public capture service and
    repository protocol. Candidate models, filtering, extraction, redaction, and
    review-gated commit-event construction live in
    `workspace_memory_candidates.py`, `workspace_memory_extraction.py`,
    `workspace_memory_redaction.py`, and `workspace_memory_commits.py`.
- `runtime/observability.py` owns `build_workspace_observability_report` as the
    aggregation facade. Report models and read-only domain collectors live in
    `observability_models.py` and the `observability_*` modules for runtime,
    projections, artifacts, verification, background jobs, task autonomy,
    workspace memory, repository index, and branch search.
- `runtime/repository_index.py` owns the public build, write, load, search, and
    entry-fetch helpers. Discovery, entry extraction, persistence/freshness, and
    search ranking live in `repository_index_discovery.py`,
    `repository_index_extraction.py`, `repository_index_persistence.py`, and
    `repository_index_search.py`.

Maintenance collectors and observability modules are read-only except for
explicit job-progress records. Task continuation is the runtime background path
that may mutate task or session state. Repository intelligence remains derived
from local files and rebuildable persisted state.

### Runtime Review-Loop Boundaries

Changeset review-loop services are runtime-owned, transport-agnostic, and
repository-backed. Runtime helpers may derive changeset detail, inventory
freshness, feedback posture, evidence posture, response status, verification
preview, lifecycle brief sections, safe commands, handoff readiness, and commit
readiness from canonical events, managed artifacts, repository read models, and
explicit service inputs.

Lifecycle brief limitation collection and reviewer-safe overflow summarization
live in `runtime/changeset_review_brief_limitations.py`; the review brief
section facade consumes that summarized output without changing retained
evidence authority.

Review brief artifact assembly keeps a narrow facade in
`runtime/changeset_review_brief_sections.py`; deterministic section builders
live in `runtime/changeset_review_brief_core_sections.py`, review-loop section
builders live in `runtime/changeset_review_brief_review_sections.py`, and
readiness-state derivation lives in
`runtime/changeset_review_brief_readiness.py`.

Runtime review-loop helpers must not import CLI formatting, FastAPI response
models, dashboard components, generated frontend types, or raw projection SQL.
They may preserve compatibility re-exports through `runtime/changesets.py`
until callers move to narrower modules.

Publication-boundary behavior is part of this runtime contract. Review-loop
helpers can say what was inspected locally, what remains stale or missing, and
what safe command could be run next; they must not turn manual evidence, browser
evidence, accessibility evidence, dashboard evidence, provider canaries, or
dogfooding notes into publication approval.

### Tool Runtime

Responsible for:

- executing typed tools
- streaming partial output for long-running operations
- enforcing policy decisions
- capturing artifacts such as diffs, stdout, and stderr
- returning structured results to the turn engine

### Event Transport

Responsible for:

- live publish and subscribe behind one explicit transport boundary
- fanout to CLI renderer and dashboard stream endpoints
- preserving the current in-process compatibility path while later tasks add
    cross-process consumers
- decoupling producers from projections and UI-specific delivery details

The current implementation now depends on a transport abstraction rather than
having the runtime, CLI renderer, and SSE route reach directly into one concrete
bus type. The shipped implementation remains an in-process transport adapter,
but `GBX-301` makes the live-delivery boundary explicit so later daemon-backed
or cross-process consumers can reuse the same runtime logic.

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
5. The context builder assembles conversation history, tool schema, policy state, repository context, session-scoped runtime notes, and any bounded working-set summary needed for the turn.
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

### Core Domain Module Strategy

`src/glassbox/core/events.py` and `src/glassbox/core/models.py` are intentionally
broad public import surfaces. They should stay stable even if future growth
moves cohesive event or model families into domain-owned helpers.

Future splits should be domain-first and explicit. Reasonable event/model
families include sessions, turns, tools, tasks, branch search, background jobs,
workspace memory, repository index, provider recovery, verification, and
compaction. A split should happen only when a domain expansion makes review,
registration, or ownership risky; line count alone is not enough.

`core/events.py` remains the canonical registration point for persisted event
payloads. If event classes move into modules such as `core/events_tasks.py` or
`core/events_background_jobs.py`, the `EventPayloadType` discriminated union,
`event_payload_adapter`, and `EventEnvelope` compatibility imports must remain
available from `glassbox.core.events` and `glassbox.core`. Event registration
must stay explicit and deterministic; do not use filesystem discovery or hidden
plugin registration for canonical persisted events.

`core/models.py` should follow the same compatibility rule for shared records
and value objects. Domain-owned model modules may be introduced when validators,
record contracts, and review ownership naturally travel together, but the public
imports used by runtime, store, CLI, web, and tests should remain stable during
the migration.

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

The current runtime already enforces a minimal local policy boundary:

- workspace path checks
- coarse tool risk buckets
- destructive command blocking
- approval-mode gating for risky actions

For v2, keep that baseline but split policy into four explicit layers:

1. hard runtime invariants that are never repository-tunable
2. registry-declared baseline tool risk classification
3. repository-owned workspace policy rules
4. session approval mode translation for approval-worthy actions

Example policy rules:

- read-only repo operations: auto-approve
- file edits inside workspace: configurable, default to confirm
- network access: blocked or confirm-only
- destructive filesystem commands: blocked
- commands outside workspace: blocked

The registry risk bucket is only the baseline classification. Final allow,
approve, or deny behavior should come from the resolved workspace policy plus
approval mode, not from a hard-coded `if risk == ...` tree alone.

The first configurable policy model should stay typed and inspectable. Prefer
explicit rule selectors such as:

- exact tool names
- normalized path-root constraints
- bounded argument-value matchers
- command prefixes or subcommand families for command-style tools

Avoid arbitrary policy code or hidden runtime heuristics.

Represent policy decisions explicitly:

```python
class PolicyDecision(BaseModel):
    allowed: bool
    requires_approval: bool
    reason: str
```

The runtime-facing decision may stay this small, but the resolved policy input
to that decision should be versioned and normalizable so replay can fingerprint
the effective policy state for a turn.

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

The store implementation follows that rule with a split read boundary:

- `store/sqlite_queries.py` is a compatibility facade over focused
    `sqlite_query_*` modules for transcript, runtime notes, tools and
    approvals, turn metrics, autonomy budgets, tasks, and branch search
- `store/repositories.py` is a compatibility facade over domain repository
    delegates for sessions, events and forks, projection reads, background jobs,
    workspace memory, tasks, branch search, and artifacts

Those modules may shape projection records and adapter results, but they do not
own runtime orchestration, HTTP response models, CLI formatting, or frontend
state.

## Richer Runtime Context Model

Glassbox treats turn context as a first-class runtime contract rather than as an
opaque prompt-concatenation detail.

In the current implementation, each live turn is assembled from explicit typed
inputs before the model call:

- transcript history and session state from canonical events and projections
- tool schema and policy state from the active runtime configuration
- repository context from a bounded workspace snapshot
- runtime notes from persisted session note projections

The turn engine then passes those richer-context inputs into `TurnContext` as a
prompt-ready `repo_context` string and a list of `memory_notes`. That same
session data is also exposed back to operators as a structured
`RuntimeContextSnapshot` so richer context is inspectable outside the raw prompt.

The next context-quality phase should extend this model with a distinct typed
`working_set` source. That source is not a replacement for tools or transcript
history. It is a bounded runtime summary of the current slice of work so the
model can start from the same high-signal focus the operator can inspect.

### Current Source Taxonomy

The important design rule is that not all turn inputs share the same lifecycle.

- transcript and session state are canonical historical inputs reconstructed from events
- tool and policy state are current runtime constraints
- repository context is a bounded live summary recomputed from the session `cwd`
- runtime notes are persisted session-scoped state recorded through events

The working-set contract for the next phase should sit beside those categories,
not blur them together:

- working-set context is a bounded derived summary assembled from explicit runtime signals
- working-set inputs must declare provenance rather than appearing as prompt-only magic
- working-set items are orientation aids, not a hidden substitute for repository inspection tools

That separation is deliberate because resume, replay, eval, and branching must
treat each category differently.

### Repository Context Contract

Repository context is intentionally narrow. The runtime builds it from the
workspace root using a deterministic top-level scan that ignores dotfiles and
captures only a bounded orientation layer:

- workspace name
- high-signal paths such as `README.md`, `pyproject.toml`, `src/`, `tests/`, `docs/`, `evals/`, and `frontend/` when present
- bounded top-level directory and file lists
- coarse project markers such as `python_pyproject`, `src_layout`, and `tests_present`

The prompt uses that summary as orientation, not as a hidden repository index.
If the model needs real detail, it must still inspect the repository through
tools.

If the recorded workspace path no longer exists, Glassbox intentionally degrades
the repository summary to the workspace name only instead of failing status,
snapshot, or replay preparation entirely.

### Runtime Note Contract

Runtime notes are event-backed session memory, not background hidden memory.

- `RuntimeNoteRecorded` adds a local note to the active session
- `RuntimeNoteImported` records inherited note state in a child or replayed session
- each note keeps category, message, source session, source sequence, timestamp, and inheritance state in projections

When notes are placed into the live prompt they are formatted as concise strings
like `[repo] README changed recently` or `[inherited repo] README changed recently`.
That keeps them human-auditable and replayable.

### Working-Set Context Contract

Working-set context is the next bounded enrichment layer after repository
context and runtime notes.

Its purpose is to summarize the current local focus of the session, not to act
as a second repository index or a hidden retrieval subsystem.

The working set should therefore be:

- typed rather than inferred only from prompt text
- derived from explicit runtime signals already visible to the system
- bounded in size, freshness, and summary length
- inspectable by operators through the same normal status and snapshot surfaces
- replayable through explicit provenance and fingerprint rules

The first working-set implementation should draw only from high-signal sources
whose influence is already explainable, such as:

- recently touched files or artifacts from explicit tool activity
- failing-test summaries or other error artifacts recorded by the runtime
- recent approval subjects and denied or resumed tool actions when they materially narrow the current task
- branch lineage and imported session context when the child session clearly inherited a local area of work
- relevant runtime notes that already capture stable operator- or runtime-learned facts

The first implementation should intentionally exclude weak or opaque signals such
as speculative intent inference, broad background crawling, or hidden model-side
state that cannot be explained back to the operator.

Each working-set item should be able to answer at least these questions:

- what subject is being highlighted such as a file, test, artifact, or bounded summary
- why it is in the working set
- which explicit signal or signals promoted it
- whether it is fresh, inherited, or derived from persisted artifacts

That makes the working set useful for both prompt assembly and replay drift
analysis without turning it into an opaque memory blob.

### Provenance Classes For Enriched Context

The next context-quality phase should make provenance explicit for every
enriched-context source that can materially affect turn preparation.

The architecture should use these provenance classes:

- recomputed summaries: bounded context derived live from documented local inputs such as the current workspace root
- persisted session state: event-backed context that survives resume, replay, export, eval, and branching
- artifact-backed summaries: derived context stored as explicit artifacts because recomputing it every turn would be too expensive or too unstable
- intentionally non-replayable candidates: signals that may be useful to inspect experimentally later but are not allowed into the replay-safe baseline until their contract is defined

Working-set signals should declare one of those provenance classes before they
are allowed to shape the live turn prompt.

That rule prevents the system from drifting toward hidden caches, machine-local
ambient indexes, or prompt-only heuristics that cannot be audited later.

### Operator Inspection Surfaces

Richer runtime context is exposed through normal operator surfaces rather than
through raw prompt dumps alone.

- CLI `status` prints a `Runtime context:` block with repository summary, visible runtime notes, working-set items, and artifact-backed context summaries
- `GET /sessions/{session_id}` returns a typed `runtime_context` snapshot including repository context, runtime notes, working set, and artifact-backed context
- the dashboard renders that same bounded snapshot in the selected-session summary
- replay model-call artifacts and exported bundles preserve the same `turn_context` payload plus per-source enriched-context manifests for debugging
- eval suite artifacts and summaries surface replay outcome, mismatches, and any source-specific context drift message

With context quality v2 in place, those same inspection rules now apply to the
newer context sources too:

- operators should be able to inspect the current bounded working set and the top reasons items were included
- operators should be able to inspect artifact freshness, inherited status, and bounded failing-test summaries when artifact-backed context is present
- the inspection path should remain read-only and summary-oriented rather than exposing raw concatenated prompt text as the only debugging surface

This is intentionally read-only. The inspection path explains what shaped a turn
without creating a second mutable configuration surface.

### Current Context Quality V2 Flow

The current implementation keeps richer context explicit all the way from turn
assembly through replay artifacts.

- prompt assembly appends repository context, runtime notes, working-set context, and fresh artifact-backed summaries as separate prompt fragments rather than flattening them into one opaque blob
- CLI status and dashboard snapshots expose the same bounded runtime-context contract the model received, including working-set reasons and artifact freshness
- replay capture records per-source manifests with `source_name`, `provenance_class`, semantic fingerprint, inheritance state, summary text, and bounded item counts
- when one artifact-backed summary kind dominates a turn, replay names that exact source, such as `pytest_failure_digest`, instead of reporting only aggregate context drift
- selected-invariant eval cases can deliberately ignore transcript-only or event-family noise while still failing on context-source drift

That flow is the important boundary: the model can use richer context, but the
operator can inspect the same typed sources through normal status, snapshot,
replay, and eval workflows.

### Resume, Replay, Eval, And Branch Semantics

The richer-context contract has to remain compatible with the rest of the
runtime's local-first guarantees.

- `resume` reloads active runtime notes from projections and recomputes repository context from the current `cwd`
- `fork` imports the parent's active runtime notes into the child as explicit `RuntimeNoteImported` events
- replay bundles carry inherited runtime notes so forked sessions remain portable and self-contained
- replay manifests store both the normalized turn context and per-source enriched-context metadata; older artifacts still fall back to the legacy aggregate fingerprint derived from turn-context payloads

The current context-quality implementation refines that replay contract instead
of replacing it.

- repository context should remain a recomputed bounded summary with explicit drift reporting when the local workspace no longer produces the recorded summary shape
- runtime notes should remain persisted session state whose inheritance and import path is explicit in events and replay bundles
- working-set context should be rebuilt only from explicit replay-safe signals or explicit recorded artifacts rather than from hidden parent-session caches or ambient local state
- replay artifacts now carry per-source provenance metadata and per-source semantic fingerprints while preserving compatibility with older aggregate enriched-context fingerprints
- replay and eval reporting should be able to say which enriched-context source drifted, not merely that "context changed"

Compatibility expectations should stay explicit in the architecture too:

- newer bundles should carry per-source manifests because they produce actionable source-level drift reports
- older replay bundles or historical sessions that only have the aggregate enriched-context fingerprint should continue to replay with coarser drift reporting rather than being treated as unsupported immediately

That fingerprint matters because replay should report richer-context preparation
changes as manifest drift, not as vague downstream behavior drift.

In other words:

- repository context is live and recomputed under a bounded contract
- runtime notes are persisted session state that survives resume, replay, export, eval, and branching
- working-set context should be a bounded derived summary whose allowed signals and provenance classes are defined up front
- inherited note provenance remains explicit so child-session and replay behavior can be audited instead of guessed

Child sessions should also remain self-contained under this model.

If a future working-set input needs to survive into a child session, Glassbox
should persist or import it explicitly through the event or artifact model. A
child session must not depend on mutable hidden parent-session caches that do
not appear in its own replayable state.

### Scope Boundary

The richer-context scope remains deliberately narrow.

- keep repository context concise, deterministic, and cheap to recompute locally
- keep runtime notes session-scoped and event-backed
- preserve operator inspectability so context does not become invisible prompt magic

The following remain out of scope for this architecture:

- hidden long-term autonomous memory outside the event-sourced runtime model
- unbounded repository indexing or background crawl subsystems
- opaque provider-specific prompt augmentation that cannot be inspected or replayed
- embeddings or vector stores treated as a silent second source of truth
- background context accumulation that survives only in process memory
- ambient machine-local caches that materially affect prompt assembly without explicit provenance
- speculative working-set inference that cannot be justified through events, artifacts, or documented local summaries

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

- CLI should expose a dedicated fork action such as `glassbox session fork SESSION_ID`
- the CLI should support an explicit historical turn selector such as `--turn TURN_ID`
- the CLI may attach an operator-visible branch label and an immediate follow-up prompt as adjacent options, rather than collapsing forking and continuation into one implicit action
- the dashboard should treat forking as a persisted session action over a selected historical cut point, not as a browser-local state transformation

### Session Index And Snapshot Contract

The browser-facing lineage contract should stay explicit and typed rather than
forcing the dashboard to infer ancestry from transcript content.

`GET /sessions` should expose summary-level lineage and branchability fields:

- `parent_session_id`, `forked_from_turn_id`, `forked_from_sequence`, and `branch_label`
- `child_session_count`
- `can_fork`, `latest_fork_point_turn_id`, `latest_fork_point_sequence`, and `fork_blocked_reason`

`GET /sessions/{session_id}` should extend that with full fork-navigation data:

- `child_sessions` summaries suitable for navigation without an extra lookup round trip
- `branchable_turns` containing explicit completed-turn choices with stable turn ID, sequence, timestamp, and operator label

This keeps the browser mental model straightforward:

- historical inspection is read-only observation of persisted state
- `can_fork` says whether a child branch can be created now
- `fork_blocked_reason` explains why a session is inspectable but not currently branchable
- `branchable_turns` enumerates valid older cut points without making the client reconstruct them ad hoc

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

The repository-owned eval profile manifest now carries this boundary directly.
Profiles default to the `deterministic` track that feeds replay-backed eval,
budget enforcement, and release sign-off. A separate
`live-provider-canary` track is reserved for optional provider research and is
required to stay advisory and non-blocking. That keeps the future canary path
code-aligned without letting release-signoff workflows quietly absorb
non-deterministic evidence.

The governance model around those deterministic profiles is now explicit:

- eval cases carry release-contract ownership metadata such as `owner`, `capabilities`, `severity`, `verification_stages`, and `baseline_refresh_policy`
- eval profiles define the stage boundary for those cases through `verification_stage`, deterministic-versus-canary `track`, optional tags or explicit case IDs, blocking intent, and optional budget guardrails
- capability coverage manifests declare which repository-owned behaviors are expected to be covered at each stage so sign-off can fail on missing release-critical coverage instead of only on raw replay mismatches
- release sign-off aggregates deterministic profile summaries into one retained artifact that reports suite outcomes, advisory drift, unsupported cases, budget health, capability coverage, and baseline freshness cues without replacing the underlying per-case evidence

That structure is deliberate. The deterministic contract needs typed ownership,
selection, and sign-off surfaces so contributors can reason about why a case is
present, where it should run, when it should block, and what evidence should be
reviewed before a baseline is refreshed or a release is considered trustworthy.

The follow-on eval split also keeps input discovery separate from reporting.
Suite selection, profile lookup, coverage-audit loading, and output-directory
resolution now live behind a shared input boundary, so the suite runner,
summary loaders, and CLI report commands consume the same resolved eval-suite
inputs instead of rebuilding that selection logic independently.

### Change-Impact Recommendation Model

The next replay and eval workflow step is not a new portfolio system. It is a
repository-owned recommendation layer that explains which existing cases,
capabilities, and profiles are most relevant after a change set.

The first version should stay advisory and inspectable.

- it recommends replay and eval scope from changed paths; it does not silently choose the only allowed verification command
- it expands from repository-owned metadata that already exists in case manifests, capability coverage, and profile definitions
- it reports confidence and reasons for each recommendation instead of pretending the mapping is exact when the evidence is weak
- it preserves the named-profile operator model, so the output remains "run these existing cases or profiles" rather than "trust this opaque score"

The recommendation pipeline should be:

1. normalize the change set into repository-relative touched paths
2. resolve those paths through a repository-owned impact-rules table that maps stable path globs or subsystem anchors to owner IDs, capability IDs, and optional direct case or profile hints
3. expand owner and capability matches through existing eval metadata:
    - case manifests remain the source of case-level `owner`, `capabilities`, and `verification_stages`
    - `coverage.json` remains the source of capability-to-case expectations and stage criticality
    - `profiles.json` remains the source of stage-to-profile selection, deterministic versus canary track, and budget expectations
4. rank recommendations by confidence and emit the reasoning chain that produced them

The confidence model should be explicit:

- `direct`: a touched path matched an impact rule that names the case, capability, or profile directly
- `owner-derived`: a touched path matched one owner, and the recommended case carries that same owner in its release-contract metadata
- `capability-derived`: a touched path matched one capability, and the recommendation came from the coverage manifest or case capability metadata
- `stage-derived`: a profile is recommended because impacted cases or capabilities participate in that verification stage
- `fallback`: no stronger deterministic mapping exists, so the system recommends only the smallest existing deterministic smoke surface or says that no confident replay or eval recommendation exists

The first version should favor under-claiming over false precision.

- if no confident path-to-owner or path-to-capability mapping exists, the system should say so directly
- if a change only touches workflow docs or unrelated repository files, the system may legitimately recommend no replay work beyond the current manual policy
- if a change touches eval metadata itself, the explanation should say that the recommendation is metadata-driven rather than product-behavior-driven

The impact-rules table is the only new metadata concept required for this model.
It should stay small, reviewable, and subordinate to the existing eval
portfolio rather than becoming a second source of truth for release intent.
Its job is only to answer which owners or capabilities a path likely affects;
case membership, stage intent, blocking behavior, and capability expectations
must continue to live in the existing case, coverage, and profile manifests.

Explicit non-goals for the first version:

- no hidden machine-learned or provider-generated recommendation state
- no claim that the recommended set is a perfect minimal proof of correctness
- no static call-graph or whole-program semantic analysis requirement before recommendations can be useful
- no automatic mutation of profiles, tags, or case manifests in response to a change set
- no mixing of `live-provider-canary` profiles into deterministic release-signoff recommendations

### Replay Baseline Capture

Replay should be grounded in recorded turn manifests rather than inferred after
the fact from raw event envelopes alone.

For each replayable turn, Glassbox should capture enough structured baseline
data to reconstruct the control path offline, including:

- the assembled model context or a normalized equivalent
- richer runtime context inputs such as repository summaries, session-scoped runtime notes, and any bounded working-set summary that materially affects turn preparation
- tool schema and policy snapshot relevant to the turn
- provider and model fingerprint information that is safe to persist
- normalized tool requests and deterministic tool result payloads
- references to larger replay artifacts stored on disk when the payload is too large for normal event rows

Replay manifests should be:

- typed and versioned
- redacted so secrets and runtime-only credentials never land in replay artifacts
- linked from session or turn metadata rather than discovered through ad hoc filesystem scans
- suitable for later export into portable replay bundles

The recorded policy snapshot should reflect the effective normalized policy for
the turn, not every incidental detail from a repository policy file. Changes to
matched rules, approval mode, or hard policy invariants should count as
manifest drift. Changes to comments, formatting, or unrelated unused rules
should not.

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

The implemented replay stack keeps `runtime/replay.py` as the stable facade,
but the replay coordination path is now split into explicit ownership seams.

- `ReplayRunner` remains the user-facing runtime facade for loading, exporting, and replaying bundles
- `runtime/replay_orchestrator.py` coordinates bundle loading, execution, comparison, and failure-to-result translation
- `runtime/replay_bundle_io.py` owns repository-backed bundle loading and export
- `runtime/replay_execution.py` owns isolated deterministic playback against a fresh runtime
- `runtime/replay_compare.py` owns normalized-state comparison and mismatch collection
- `runtime/replay_triage.py` owns result classification and operator-facing triage summaries

That stack still replays the same user-message, approval-resolution, and
`ask_user` answer sequence through a fresh isolated session database, but the
public replay surface no longer owns all of those responsibilities inline.

To keep replay offline while still exercising the current control plane, the
orchestrated replay path:

- uses the real session supervisor, context builder, turn engine, and policy evaluation path
- swaps in replay-backed model execution that validates the current prepared turn against the recorded manifest before serving recorded outputs
- swaps in replay-backed tool execution that validates the current prepared tool request against the recorded manifest before serving recorded tool results
- compares normalized transcript output, tool-call projections, approval and question flow, emitted event families, and final projected session state against the recorded baseline

### Forked Session Compatibility

Forked child sessions must remain first-class citizens in replay and eval
workflows.

- replay bundles for child sessions should preserve lineage metadata and the imported transcript prefix explicitly
- exported child bundles must replay without consulting the original parent SQLite rows at replay time
- the replay runner should restore canonical imported-history events before applying new child-session actions so prepared-turn validation still reflects the original inherited context
- eval cases may point at child-session bundles exactly the same way they point at ordinary replay bundles

This preserves the conceptual boundary between inherited history and new child
behavior without turning branched sessions into opaque unsupported special
cases.

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

### V3 SPA Architecture Contract

The v3 dashboard replaced the hand-rolled browser implementation with a modern
TypeScript SPA while preserving the same local-first runtime and event-sourced
backend contracts.

The accepted frontend stack is:

- Next.js App Router with strict TypeScript
- `pnpm` as the frontend package manager
- Tailwind CSS for styling
- shadcn-style components built on headless/Radix primitives
- Zustand for client-side state coordination
- OpenAPI-generated TypeScript types derived from the FastAPI schema
- static export served by the existing FastAPI process for production use

FastAPI remains the API owner, runtime owner, and production serving process.
Next.js may provide a development server, hot reload, and local API rewrites for
contributors, but production Glassbox dashboard usage must not require a Node
server. Normal Python runtime users should be able to open a packaged dashboard
from `glassbox session chat` or `glassbox dashboard serve` after release assets
have been built and included in the Python distribution.

The SPA should live under a repository-local `frontend/` workspace. Its static
export should be copied or emitted into `src/glassbox/web/static_next/` when a
production build is prepared. The FastAPI app serves those built files at `/`,
with `/app` retained as a compatibility alias. Missing SPA assets in a source
checkout should produce developer-facing guidance, not a silent blank page.

Direct session links using `?session=SESSION_ID` must keep working at the root
dashboard URL.

The SPA architecture should keep these boundaries explicit:

- generated OpenAPI types are the browser contract at the HTTP boundary
- typed transport helpers own `fetch`, request cancellation, response decoding,
    and domain-friendly error normalization
- a typed SSE client owns `GET /sessions/{session_id}/events`, sequence tracking,
    reconnect state, and resume-after behavior
- pure TypeScript reducer helpers hydrate snapshots and reduce live events
    without React, Zustand, browser globals, or network side effects
- Zustand stores coordinate aggregate console state, selected-session state,
    stream lifecycle, route state, and local UI drafts while keeping server-derived
    data distinct from transient browser input
- React components render the operator console from typed store state and call
    transport/store actions instead of issuing ad hoc HTTP requests

The current post-v8 dashboard split keeps those boundaries concrete:

- `frontend/stores/dashboard-stores.ts` is a compatibility facade that
    re-exports domain stores and public state types
- session summary/detail streaming, task queue/detail/action state, workspace
    memory and repository inspector state, branch-search state, and shared
    request/action/load-state helpers live in dedicated store modules
- task, knowledge, branch-search, and verification-cue console sections live in
    focused `*-sections.tsx` modules while the public console component
    entrypoints remain stable
- session-inspector diagnostics keep `diagnostics-panes.tsx` as the pane export
    facade while runtime context, metrics, event/projection evidence, and shared
    pagination controls live in dedicated pane modules

Frontend stores consume generated API client types and browser transport
helpers. They must not import React components, Next.js server-only modules, or
backend Python source.

[operator-console.md](./operator-console.md) remains the product UX baseline for
the SPA. The first SPA screen is the operator console itself: workspace overview,
action queues, runtime/projection health, and selected-session inspection. The
SPA must preserve local drafts and useful browser navigation, but canonical
session state remains derived from FastAPI snapshots, aggregate read models, SSE
events, and persisted backend actions.

### SPA Compatibility Rules

The SPA migration must preserve these existing backend contracts unless a task
explicitly updates the API and documents the change:

- `GET /healthz` remains the health check and event-transport observability path
- `GET /sessions` remains the recent-session summary index for compatibility
- `GET /sessions/aggregate` remains the multi-session console overview and
    queue data source
- `GET /sessions/{session_id}` remains the selected-session snapshot source
- `GET /sessions/{session_id}/events?after=SEQUENCE` remains the per-session SSE
    stream, with historical replay before live events and sequence-based resume
- `POST /sessions/{session_id}/messages` remains the next-prompt action
- `POST /sessions/{session_id}/questions/{question_id}` remains the `ask_user`
    answer action
- `POST /sessions/{session_id}/approvals/{approval_id}` remains approval and
    denial resolution
- `POST /sessions/{session_id}/fork` remains the persisted branch creation path

The browser may sort, filter, preserve drafts, and render transient pending
states. It must not invent authoritative approval semantics, fork validity,
runtime ownership, projection health, lineage, or replay/eval outcomes that the
backend has not exposed. After mutations, the SPA should rely on snapshot refresh
and SSE events for canonical state rather than treating optimistic local changes
as durable truth.

The minimum parity gate before replacing `/` is behavioral, not visual. The SPA
must cover session discovery, aggregate queues, selected-session inspection,
live SSE, historical snapshots, approvals, questions, prompts, forks, lineage,
comparison, runtime context, metrics, active tool calls, live output, event log,
projection health, direct `?session=` deep links, and clear error handling.

### Transport

Use:

- HTTP for snapshot and commands
- server-sent events for live streaming

SSE is a better first fit than WebSockets because the dominant direction is server-to-client streaming.

### Endpoints

The current server surface includes:

- `GET /healthz`
- `GET /sessions` for recent-session discovery in the standalone dashboard, including parent lineage metadata and lightweight branchability state
- `GET /sessions/aggregate` for operator-console queue counts, health summaries, runtime-owner state, and prioritized session rows
- `GET /sessions/{session_id}` for a snapshot view, including parent metadata, child-session summaries, and explicit branchable-turn choices for the selected session
- `POST /sessions/{session_id}/fork` to create a child session from the latest or explicitly selected stable historical turn boundary
- `GET /sessions/{session_id}/events` as an SSE stream
- `POST /sessions/{session_id}/messages` to submit the next user prompt
- `POST /sessions/{session_id}/questions/{question_id}` to answer an `ask_user` question
- `POST /sessions/{session_id}/approvals/{approval_id}` to resolve approvals

### Dashboard Panes

The first UI should show:

- transcript timeline
- selected-session lineage with parent and child navigation affordances
- explicit fork controls over branchable completed turns, with child-session navigation after creation
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
- creating a child session from a stable historical turn
- sending a prompt
- answering a pending ask-user question
- approving or denying actions
- opening the dashboard URL
- printing session status

The CLI renderer should subscribe to runtime events and produce a concise terminal view rather than printing directly from internal subsystems.

The CLI should expose two complementary layers:

- interactive commands for the normal conversational workflow
- non-interactive commands for scripting, recovery, and explicit low-level control

The full-screen TUI is split so terminal state remains testable without starting
the Textual app:

- `cli/tui/conversation.py` is the stable conversation-state facade over
    `conversation_models.py`, `conversation_hydration.py`,
    `conversation_reducer.py`, and `conversation_selectors.py`
- `cli/tui/widgets.py` is the stable widget facade over pane-family modules for
    header, footer/action strip, transcript, composer, command palette, details,
    and shared formatting
- `cli/tui/app.py` owns Textual lifecycle while `app_commands.py`,
    `app_stream.py`, `app_refresh.py`, `app_feedback.py`, and `app_paths.py`
    own command dispatch, stream lifecycle, widget refresh, feedback mapping,
    and local artifact path resolution

TUI reducers consume core events and CLI-local snapshot models. TUI widgets may
depend on Textual/Rich and terminal selectors, but they do not import raw store
helpers, web routes, frontend modules, or runtime background-job orchestration.

### Scriptable Command Surface

```text
glassbox command tree
glassbox observability status [--json]
glassbox performance budgets
glassbox session run [PROMPT]
glassbox session fork SESSION_ID [--turn TURN_ID] [--branch-label LABEL] [--prompt PROMPT]
glassbox session message SESSION_ID PROMPT
glassbox session answer SESSION_ID QUESTION_ID ANSWER
glassbox session resume SESSION_ID
glassbox session status SESSION_ID
glassbox session approve SESSION_ID APPROVAL_ID
glassbox session deny SESSION_ID APPROVAL_ID
glassbox projection check [SESSION_ID | --all]
glassbox projection rebuild [SESSION_ID | --all]
glassbox dashboard serve
```

`glassbox performance budgets` prints the repository-owned larger-session
budgets used by integration coverage, including mitigation guidance for event
append, projection rebuild, session-index, and operator-console aggregate
regressions.

`glassbox observability status` joins daemon health, event-stream reconnect/drop
counters, projection lag, and retained eval summaries into one operator-facing
summary with concrete next inspection or recovery actions. The daemon health
endpoint also includes event-transport counters so dashboards can distinguish a
healthy process from a degraded live stream.

`glassbox session status` should read persisted projections and summarize the current turn,
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
glassbox replay run SESSION_ID [--json]
glassbox replay bundle export SESSION_ID [OUTPUT]
glassbox replay bundle inspect BUNDLE_PATH [--json]
glassbox replay bundle run BUNDLE_PATH [--json]
glassbox eval run [CASE_ID ...] [--tag TAG] [--json] [--output-dir DIR]
```

The semantics should stay narrow:

- `glassbox replay run` compares the current codebase against a recorded session baseline offline, returns concise human output by default, supports machine-readable JSON output, and reports exact match, manifest drift, behavioral drift, unsupported session, or replay failure
- `glassbox replay bundle inspect` validates a portable replay bundle and reports its source session, runtime configuration, lineage presence, retained action/model/tool counts, and baseline summary without executing replay
- `glassbox replay bundle run` consumes a portable replay bundle directly, so exported baselines can be replayed without the original session database and can run against the current workspace root instead of the source machine path
- `glassbox replay run` uses stable exit codes so scripts can distinguish exact match from drift and replay errors without scraping terminal text
- `glassbox replay run` does not mutate the source session metadata or recorded replay artifacts; replay runs against an isolated temporary session store
- `glassbox replay bundle export` turns a replayable session into a portable baseline bundle that can move across branches, repositories, or CI machines without the original SQLite database
- `glassbox replay bundle export` for a forked child session includes the lineage metadata and imported transcript prefix required to replay that child independently of its parent database rows
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

### Replay And Eval As A Release Contract

Replay and eval should be treated as a maintained release contract for
Glassbox, not only as debugging conveniences.

The purpose of this contract is to answer a release-oriented question that raw
history inspection and ordinary automated tests do not answer cleanly on their
own:

- does the current Glassbox codebase still honor the curated operator-visible
    behaviors that the repository has chosen to preserve?

This release contract should stay explicitly narrower than total product
correctness.

- `pytest`, linting, and type checking still protect implementation quality,
    local correctness, and internal contracts
- replay and eval protect curated runtime behavior across real session flows,
    including context assembly, tool control flow, suspension behavior, and final
    projected state
- passing replay and eval suites increase release confidence, but they do not by
    themselves certify the entire system

#### Verification Tiers

Replay and eval coverage should be organized into explicit verification tiers
with different operator expectations.

- commit-time: the smallest blocking deterministic suite, intended to catch the
    highest-value regressions before history is created
- push-time confirmation: deterministic coverage that reruns after `origin`
    receives new commits and retains artifacts for shared review
- release-candidate: the broadest deterministic suite required before treating
    a build as a serious release candidate
- advisory: deterministic but non-blocking coverage that is useful for trend
    detection, coverage growth, or costlier scenarios that have not earned
    blocking status yet
- canary or research: explicitly non-deterministic or live-provider comparison
    work that may be useful for observing current model behavior, but is outside
    the deterministic release contract

The first three tiers are release-bearing tiers. Advisory and canary coverage
may inform product direction, but they must not weaken or blur the meaning of a
passing deterministic release signal.

#### Case Terminology

Each curated replay or eval case should eventually be describable using a small
stable set of release-governance terms.

- covered capability: the operator-visible workflow or behavior the case is
    intended to protect, such as approval flow, `ask_user` suspension, branching,
    artifact-backed context, or replay portability
- owner: the subsystem or product area expected to respond when the case drifts
- severity: how seriously failure of this case should be treated in the tiers
    where it participates
- blocking intent: whether the case is allowed in commit-time, push-time,
    release-candidate, or advisory-only suites
- baseline freshness: whether the bundle is current enough to keep providing a
    meaningful contract rather than stale reassurance

This terminology should stay repository-owned and reviewable. It must not live
only in CI wiring, naming conventions, or contributor folklore.

#### Exact-Match Versus Selected-Invariant Contracts

The release contract should remain strict by default, but not simplistic.

- exact-match cases are the default tool when Glassbox should preserve the
    whole normalized behavior of a workflow
- selected-invariant cases are appropriate when the important contract is
    narrower, such as final projected state, approval flow, or context-source
    stability, and exact transcript equivalence would create noise rather than
    confidence
- advisory cases may intentionally observe broader or costlier behavior without
    imposing a blocking release burden immediately

Selected-invariant cases must remain explicit. They are a targeted contract
choice, not a hidden weakening of deterministic replay.

#### Severity Expectations For Replay Outcomes

The replay taxonomy remains the same, but release-oriented suites should attach
clear severity expectations to those outcomes.

- `exact_match` means the curated release contract held for that case
- `manifest_drift` should generally be treated as high severity in blocking
    deterministic tiers, because it means Glassbox no longer reproduced the
    recorded context, policy, schema, or preparation contract before playback
    meaningfully began
- `behavioral_drift` should be treated according to the case contract: high
    severity for exact-match blocking cases, and expectation-aware for
    selected-invariant cases where some mismatch dimensions are intentionally
    ignored
- `unsupported_session` should be rare in curated blocking tiers; if it appears
    there, that is usually a release-governance problem rather than a harmless
    skip
- `replay_failure` should be treated as a verification-system defect until
    proven otherwise, because the project has lost trustworthy evidence about the
    case it meant to verify

These distinctions matter because a context-manifest regression, a tolerated
transcript-only mismatch, and a broken replay runner should not carry the same
release meaning.

#### Deterministic Contract Versus Canary Work

Deterministic replay and eval must stay clearly separate from future
live-provider comparison or other research-oriented verification.

- deterministic release verification asks whether the current Glassbox control
    plane still reproduces curated recorded behavior under the offline replay
    contract
- canary or live-provider work asks how providers behave now under current
    credentials, latency, and model behavior

Both are useful, but they answer different questions. Live-provider comparison
must remain non-blocking until the repository deliberately defines a separate
contract for it. It must not be allowed to contaminate the meaning of a passing
deterministic release tier.

#### Release Sign-Off Principle

Over time, Glassbox should be able to summarize replay and eval results as part
of release sign-off using repository-owned deterministic tiers, covered
capabilities, and retained drift artifacts.

The intended release posture is:

- blocking deterministic tiers provide the minimum trustworthy evidence that
    key operator-visible behaviors still hold
- advisory deterministic tiers expand confidence without redefining the minimum
    contract silently
- canary work remains informative but separate
- baseline refresh is a contract change that should be reviewed deliberately,
    not a routine mechanism for making failures disappear

### Interactive Command Surface

The primary conversational UX should move toward a persistent terminal session
rather than repeated one-shot command invocations.

```text
glassbox session chat [PROMPT]
glassbox session attach SESSION_ID
```

`glassbox session chat` starts a new session and keeps the operator inside a long-lived
terminal loop. `glassbox session attach` opens that same interactive terminal workflow
for an existing persisted session.

In v1, `attach` should support reopening sessions that are actionable from the
current process, such as idle running sessions, awaiting-user-input sessions,
and other paused states that can be continued from persisted projections. It
should not promise live streaming from another already-running process, because
the current event bus is in-process only.

### Co-Hosted Dashboard During `session chat`

The interactive `session chat` workflow should also be able to expose the
dashboard from the same owning process.

This should be treated as a co-hosted sidecar over the existing runtime context,
not as a second runtime stack. The same process should continue to own:

- the interactive terminal loop
- the runtime services
- the event bus
- the persisted event stream
- the embedded dashboard server

The intended command surface is:

```text
glassbox session chat [PROMPT] [--dashboard-host HOST] [--dashboard-port PORT] [--no-dashboard]
```

Semantics:

- `glassbox session chat` should attempt to start a dashboard by default so the browser view is available while the interactive session is in progress
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

`glassbox dashboard serve` remains the standalone dashboard path for cases where the
operator wants a browser view outside an active `chat` session, wants to inspect
persisted sessions from another process, or needs explicit control over the
server lifecycle. `attach` should not automatically start the dashboard in v1;
it remains an interactive terminal re-entry path over existing persisted state.

For operator docs, the key positioning should stay explicit:

- the co-hosted dashboard is a convenience surface for the same live `chat` process and should shut down with that process
- `glassbox dashboard serve` is the durable observation path for persisted sessions and for browser access that should survive beyond a single `chat` invocation
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

For follow-on implementation work, `glassbox dashboard serve` should optimize for session
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

`GBX-166` established the shipped baseline: keep the interactive terminal UX
process-local and do not treat the current CLI and dashboard surfaces as if
they already imply a daemon-backed runtime or a cross-process terminal attach
protocol.

This is the current stance because the existing surfaces already cover most of
the operator value at materially lower complexity:

- `glassbox session chat` provides the primary conversational workflow inside the owning CLI process
- `glassbox session attach` can reopen persisted sessions that are actionable from projections
- `GET /sessions/{session_id}` already provides cross-process snapshot recovery
- `GET /sessions/{session_id}/events` already provides cross-process live event streaming to the dashboard
- approval and question flows are already resumable from persisted events rather than process-local memory

The remaining gap is specifically terminal-native live attach to a runtime that
is still owned by another process. That is the operator gap v2 now chooses to
address deliberately.

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

Decision outcome for v2: adopt Option 2 in a constrained local-first form.
Glassbox should introduce a workspace-scoped background runtime owner through a
new `glassbox daemon` command surface rather than overloading `glassbox dashboard serve`.

This command-surface choice is deliberate:

- `glassbox daemon` owns live session mutation, runtime lifecycle, health, and
    workspace locking
- `glassbox dashboard serve` remains the browser-facing observation and operator-console
    surface rather than becoming the authoritative runtime owner
- `glassbox session chat` remains the embedded convenience path for same-process work
    and should continue to work without a background owner when the operator wants
    an ephemeral local session

#### V2 Ownership Contract

The v2 ownership model should be:

- at most one background runtime owner per workspace
- the owner process is responsible for live event fanout, turn execution,
    approval resumption, and orderly runtime shutdown
- live session mutation must funnel through the owner process once a daemon is
    active for that workspace; other processes do not race it by writing directly
    to the same live session state
- persisted events remain canonical; the owner coordinates mutation, but it does
    not become a hidden state store outside the event log and derived projections
- if the owner is unavailable, the operator may still inspect persisted state,
    but live ownership must be treated as unavailable rather than silently
    simulated from stale projections

#### Attach Model

The attach model should distinguish three operator surfaces explicitly:

- embedded terminal ownership: `glassbox session chat` owns the live session inside the
    current process and may co-host the dashboard for that same runtime
- terminal attach to a background owner: the attach client reconnects to the
    daemon-owned session, restores prompt and suspension state from snapshot
    data, and then continues with live updates over the daemon event stream
- browser observation and action: the browser continues to use snapshot, action,
    and event-stream surfaces as an operator console whether the runtime is
    embedded, background-owned, reconnecting, or unavailable

The browser and terminal may observe the same owned session concurrently, but
they are different operator surfaces. Browser visibility must not be treated as
equivalent to terminal-native attach semantics.

#### First-Slice Scope Boundary

The first v2 persistent-runtime slice should include:

1. a workspace-scoped daemon owner with explicit lifecycle and health semantics
2. runtime discovery and locking rules that prevent conflicting owners
3. a transport abstraction that preserves the current embedded event bus path
     while allowing daemon-backed clients later
4. explicit runtime-state terminology for live, reconnecting, unavailable, and
     historical-only sessions

The first v2 slice should stay out of scope for:

- remote or multi-tenant orchestration
- multiple concurrent live writers for one session
- browser-native terminal emulation or browser-owned session mutation rules
- hidden mutable state outside persisted events and explicit derived read models
- broad collaboration semantics beyond single-workspace operator attachment;
    team handoff stays in later tasks

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

The current package layout reflects the post-v8, v10, and v11 ownership
boundaries rather than a small set of large mixed-responsibility modules. The
later refactors keep facades thin by moving derivation, HTTP-local helpers,
provider evidence/scoring, confidence-surface shaping, recovery logic,
projection handlers, tool-policy rules, and schema DDL into focused neighbor
modules.

```text
src/glassbox/
    __init__.py
    cli/
        __init__.py
        command_guide.py
        command_guide_data.py
        command_guide_json.py
        command_guide_models.py
        command_guide_render.py
        command_guide_workflows.py
        entry.py
        interactive_autonomy.py
        interactive_commands.py
        interactive_daemon_actions.py
        interactive_local_actions.py
        interactive_session.py
        parser.py
        parser_session_launch.py
        path_helpers.py
        renderer.py
        replay_eval_commands.py
        replay_eval_formatters.py
        server_commands.py
        session_state_commands.py
        status_formatters.py
        status_knowledge.py
        status_observability.py
        status_session.py
        status_task.py
        tui/
            app.py
            app_commands.py
            app_feedback.py
            app_paths.py
            app_refresh.py
            app_stream.py
            conversation.py
            conversation_hydration.py
            conversation_models.py
            conversation_reducer.py
            conversation_selectors.py
            widget_action.py
            widget_composer.py
            widget_details.py
            widget_formatting.py
            widget_header.py
            widget_palette.py
            widget_transcript.py
            widgets.py
    core/
        __init__.py
        events.py
        ids.py
        models.py
        types.py
    runtime/
        __init__.py
        bootstrap.py
        background_job_handlers.py
        background_job_lifecycle.py
        background_job_records.py
        background_jobs.py
        background_task_continuation.py
        branch_decision_*.py
        bus.py
        context.py
        context_builder.py
        context_compaction*.py
        context_formatting.py
        context_models.py
        context_snapshots.py
        context_working_set.py
        eval_recommendation_*.py
        eval_summary.py
        eval_summary_annotations.py
        eval_summary_models.py
        eval_summary_release.py
        eval_summary_suite.py
        knowledge_posture*.py
        model_loop.py
        observability.py
        observability_*.py
        provider_canary.py
        provider_canary_*.py
        provider_recommendations.py
        provider_recommendation_*.py
        repository_index.py
        repository_index_*.py
        replay.py
        replay_bundle_io.py
        replay_capture.py
        replay_compare.py
        replay_execution.py
        replay_failures.py
        replay_fingerprints.py
        replay_manifests.py
        replay_models.py
        replay_triage.py
        session_queries.py
        session_export*.py
        session_import*.py
        supervisor.py
        task_queries.py
        task_query_*.py
        tool_attempt_recovery*.py
        turn_artifacts.py
        turn_engine.py
        turn_event_recorder.py
        turn_preparation.py
        turn_replay_hooks.py
        turn_resumption.py
        turn_tool_attempt_heartbeats.py
        turn_tool_executor.py
        workspace_memory_capture.py
        workspace_memory_*.py
    llm/
        __init__.py
        adapters.py
        executor.py
        prompts.py
    tools/
        __init__.py
        ask_user.py
        command.py
        patch.py
        policy.py
        policy_*.py
        read_only.py
        registry.py
        runtime.py
        workflow.py
    store/
        __init__.py
        sqlite_events.py
        sqlite_fork.py
        sqlite_projection_*.py
        sqlite_projections.py
        sqlite_queries.py
        sqlite_query_*.py
        sqlite_schema.py
        sqlite_schema_*.py
        sqlite_sessions.py
        artifacts.py
        repositories.py
        repository_*.py
        sqlite.py
    web/
        __init__.py
        app.py
        routes/
            approvals.py
            branch_searches.py
            events.py
            health.py
            jobs.py
            memory.py
            sessions.py
            tasks.py
            session_route_*.py
            task_route_*.py
        server.py
        session_api.py
        session_api_*.py
        static_next/
            # built Next.js static export, when present
    frontend/
        app/
        components/
            console/
                *-sections.tsx
                task-autonomy/
                workspace-console/
                session-inspector/
                    panes/
                        *-analysis.ts
        lib/
        stores/
            dashboard-stores.ts
            *-store.ts
            session-store-*.ts
        tests/
        package.json
    services/
        __init__.py
        contracts.py
    tests/
        unit/
        integration/
        e2e/
```

### V10 Second-Order Ownership

The v10 refactor preserved public routes, imports, generated API contracts, and
operator-visible behavior while moving accumulated derivation and helper logic
behind explicit local owners.

- Frontend task autonomy keeps `task-autonomy-sections.tsx` as a compatibility
  surface while queue, inspector, action controls, evidence rendering, and pure
  formatting live under `frontend/components/console/task-autonomy/`.
- Verification cues and session comparison panes render typed results from pure
  helpers in `verification-cues-analysis.ts` and
  `session-inspector/panes/compare-analysis.ts`.
- `workspace-console.tsx` owns store construction, state selection, and surface
  composition; URL synchronization and repeated action binding live in
  `workspace-console/routing.ts` and `workspace-console/actions.ts`.
- Session and task route files remain FastAPI declaration surfaces. HTTP-local
  query composition, mutation orchestration, pagination, and serialization live
  in `session_route_*`, `task_route_*`, and `pagination.py` helpers.
- `runtime/task_queries.py` remains the repository-backed read facade while
  task query models, assembly, verification-ledger derivation, and
  repair-history derivation live in `task_query_*` modules.
- Provider canary and recommendation facades keep public CLI/runtime callers
  stable while scenario selection, execution, evidence loading, reporting,
  capability fit, risk, credentials, failure posture, budget impact, and action
  guidance live in `provider_canary_*` and `provider_recommendation_*` modules.
- `tools/policy.py` remains the policy-engine facade while path scope, manifest
  rule matching, autonomy permits, approval messages, command-risk heuristics,
  and shared policy models live in `policy_*` modules.
- `store/sqlite_schema.py` owns connection setup, baseline bootstrap, migration
  table maintenance, and the explicit ordered migration registry; domain DDL and
  idempotent migration helpers live in `sqlite_schema_*` modules.
- `core/events.py` and `core/models.py` remain broad, stable public import
  surfaces. Future domain modules should be introduced only for real expansion,
  with explicit event registration and compatibility re-exports.

### V11 Confidence-Surface Ownership

The v11 refactor preserved CLI, dashboard, API, replay, eval, and projection
behavior while moving confidence-surface derivation into focused owners.

- Eval recommendation output keeps `eval_recommendation_output.py` as the
  stable output facade while rows, execution plans, verification recipes,
  release surfaces, long-run surfaces, reason groups, and shared formatting
  live in `eval_recommendation_*` helpers.
- Eval recommendation matching keeps `eval_recommendation_engine.py` as the
  orchestration owner and `eval_recommendation_matching.py` as the compatibility
  facade while path matching, case expansion, profile expansion, and shared
  matching utilities live in focused helpers.
- Knowledge posture keeps `knowledge_posture.py` as the compatibility facade
  while sources, cue derivation, provenance, command guidance, ranking, and
  shared models live in `knowledge_posture_*` helpers.
- Branch-search decision support keeps `branch_decision_support.py` as the
  public derivation facade while evidence, file summaries, verification
  recommendation, cost, risk, and follow-up behavior live in
  `branch_decision_*` helpers.
- Session export/import keeps the public `session_export.py` and
  `session_import.py` facades stable while package assembly, manifests,
  redaction, validation, event shaping, and handoff-note text live in focused
  helpers.
- CLI status, command-guide, interactive command, and session parser surfaces
  remain command-compatible facades over status-domain formatters,
  command-guide data/render/workflow modules, local/daemon/action/launch
  handlers, and session parser helpers.
- Frontend knowledge and branch-search sections keep their established
  entrypoints while domain section modules own formatting, typed props, detail
  rendering, actions, and evidence. `session-store.ts` remains the stable store
  factory while stream, pagination, draft, action, shared, and type helpers own
  behavior.
- Recovery, compaction, turn-artifact, replay-hook, and tool-attempt heartbeat
  behavior lives in focused runtime helpers; facades stay independent from CLI,
  web, and frontend presentation layers.
- Task and background-job projection facades remain rebuild coordinators over
  event-family SQL helpers. Projection tables remain derived read models, not a
  second source of truth.

The public entry modules are intentionally thinner than their neighbors:

- `runtime/__init__.py` stays a curated package surface for runtime wiring types
- `runtime/replay.py` and `runtime/eval_summary.py` stay as compatibility facades over the split replay and eval-reporting modules
- `runtime/background_jobs.py`, `runtime/workspace_memory_capture.py`,
    `runtime/observability.py`, and `runtime/repository_index.py` stay as
    stable autonomy facades over focused helper modules
- `store/sqlite.py`, `store/sqlite_queries.py`, and `store/repositories.py`
    stay as stable store facades while internal ownership lives in
    `sqlite_*`, `sqlite_query_*`, and `repository_*` modules
- `cli/tui/conversation.py`, `cli/tui/widgets.py`, and `cli/tui/app.py` stay as
    stable terminal entrypoints over state, reducer, selector, pane-widget, and
    app-coordination modules
- `frontend/stores/dashboard-stores.ts` stays as the compatibility store
    surface while domain stores own session, task, knowledge, branch-search,
    stream, request, and action state
- `frontend/` is the SPA source, and `web/static_next/` holds the built static
    dashboard assets served by FastAPI

### Boundary Rules

- `core` contains pure domain types and no framework code.
- `services` contains repository and service contracts plus contract-layer shared values such as `StoredArtifact`; it should remain concrete-implementation free.
- `store` owns persistence internals, repository adapters, artifact storage, and projection rebuild logic. Raw SQLite helpers stay in `sqlite_*` modules behind `store/sqlite.py`.
- `runtime` owns orchestration, context assembly, the shared model-loop boundary, session-query shaping, replay execution, and eval reporting. Bootstrap code may wire concrete store implementations, but orchestration code should prefer service and repository contracts.
- runtime autonomy collectors and repository-index helpers must not import CLI/TUI widgets, raw SQLite helpers, HTTP routes, or frontend modules.
- `tools` depends on `core` and minimal runtime contracts.
- `cli` depends on runtime and service/query seams, not on raw store helpers. `cli/__init__.py` remains a compatibility wrapper while parser, command, interactive-session, and formatting responsibilities live in owned neighbor modules.
- TUI state and widget modules depend on events, snapshots, selectors, Textual, and Rich, not on store internals, web routes, frontend code, or background-worker orchestration.
- `web` owns HTTP transport, SSE endpoints, and browser asset serving. Route modules should use runtime query and service seams rather than rebuilding business logic inline. The production SPA is served as static assets by FastAPI rather than by a Node process.
- frontend stores depend on generated API types, browser transport, route-state helpers, and pure store utilities. Components render from store/API state and should not become store factories or backend event-derivation modules.

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
