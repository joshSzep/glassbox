# Glassbox Database Design

## Goal

This document expands the persistence direction in [architecture.md](./architecture.md) into a practical SQLite schema strategy for Glassbox.

The database design should preserve the event-sourced architecture while making the system easy to query for:

- session resume
- dashboard snapshots
- transcript rendering
- active tool state
- pending approvals
- debugging and replay

## Design Summary

Glassbox should use two storage layers inside the same SQLite database:

1. an append-only event log as the canonical source of truth
2. read-optimized projection tables derived from that event log

The event log preserves correctness, replayability, and versioned history.

The projection tables make common runtime and dashboard queries cheap. They are not authoritative and must always be rebuildable from the event log.

## Why The Initial Minimal Schema Is Not Enough

The minimal schema in [architecture.md](./architecture.md) is a good starting point:

```sql
create table events (
    session_id text not null,
    sequence integer not null,
    event_id text not null,
    event_type text not null,
    event_version integer not null,
    created_at text not null,
    payload_json text not null,
    primary key (session_id, sequence)
);
```

That shape is correct for a raw event store, but it becomes awkward for live product queries. If all interesting identifiers live only inside `payload_json`, the application has to rely on JSON extraction for many common operations.

That creates three problems:

- queries become harder to write and reason about
- indexing becomes weaker or more awkward
- dashboard reads end up replaying too much raw history for simple state lookups

## Recommended Storage Model

Use these layers:

- `sessions` for list-oriented session metadata plus the latest projected status
- `events` for the canonical append-only event stream
- projection tables for current and query-heavy views
- artifact files on disk for large blobs such as full logs and diffs

## Canonical Tables

### Sessions

The sessions table is an entry point for listing and resuming sessions. Its
`status` and `last_sequence` should stay aligned with the latest derived
session-state projection so list and filter queries can find suspended sessions
without replaying the event log.

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

create index idx_sessions_status_updated
    on sessions (status, updated_at desc);
```

### Events

The events table remains append-only and authoritative, but it should expose a few high-value correlation fields as first-class columns.

```sql
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
    unique (event_id),
    foreign key (session_id) references sessions(session_id)
);

create index idx_events_session_created
    on events (session_id, created_at);

create index idx_events_session_type_sequence
    on events (session_id, event_type, sequence);

create index idx_events_turn
    on events (session_id, turn_id, sequence);

create index idx_events_message
    on events (session_id, message_id, sequence);

create index idx_events_tool_call
    on events (session_id, tool_call_id, sequence);

create index idx_events_approval
    on events (session_id, approval_id, sequence);
```

### Why These Extra Columns Exist

These columns are denormalized from event payloads for queryability.

- `turn_id` supports turn reconstruction and current-turn queries
- `message_id` supports transcript assembly and streaming message updates
- `tool_call_id` supports command and tool execution traces
- `approval_id` supports pending approval lookups and resolution
- `actor` helps distinguish user, assistant, runtime, and operator actions when useful

The full event payload still lives in `payload_json`. The extra columns are query aids, not a second source of truth.

## Projection Tables

Projection tables exist to answer the queries the product asks repeatedly.

These tables should always be treated as rebuildable derived state.

### Session State Projection

This table supports the question: what is happening in this session right now?

```sql
create table session_state (
    session_id text primary key,
    status text not null,
    current_turn_id text,
    pending_approval_id text,
    pending_question_id text,
    last_sequence integer not null,
    updated_at text not null,
    foreign key (session_id) references sessions(session_id)
);
```

Notes:

- `pending_approval_id` tracks approval-based suspension points
- `pending_question_id` tracks `ask_user` suspension points
- both values are cleared when the turn resumes or the session completes/fails

### Transcript Messages Projection

This table supports chat-style reads without replaying every message delta on every page load.

```sql
create table transcript_messages (
    message_id text primary key,
    session_id text not null,
    turn_id text,
    role text not null,
    status text not null,
    created_at text not null,
    completed_at text,
    content_text text not null default '',
    foreign key (session_id) references sessions(session_id)
);

create index idx_transcript_messages_session_created
    on transcript_messages (session_id, created_at);
```

Notes:

- assistant deltas can be appended into `content_text` as the projection advances
- the raw deltas still remain in `events`
- `status` distinguishes partial and complete messages

### Tool Calls Projection

This table supports live tool views, command history, and failure inspection.

```sql
create table tool_calls (
    tool_call_id text primary key,
    session_id text not null,
    turn_id text not null,
    tool_name text not null,
    status text not null,
    started_at text,
    completed_at text,
    summary text,
    exit_code integer,
    foreign key (session_id) references sessions(session_id)
);

create index idx_tool_calls_session_status
    on tool_calls (session_id, status);

create index idx_tool_calls_session_turn
    on tool_calls (session_id, turn_id);
```

### Approvals Projection

This table supports approval queues and operator actions.

```sql
create table approvals (
    approval_id text primary key,
    session_id text not null,
    turn_id text not null,
    subject text not null,
    reason text not null,
    status text not null,
    requested_at text not null,
    resolved_at text,
    decided_by text,
    foreign key (session_id) references sessions(session_id)
);

create index idx_approvals_session_status
    on approvals (session_id, status);
```

### Turn Metrics Projection

This table supports per-turn runtime inspection in the dashboard without replaying
model and tool events on every page load.

```sql
create table turn_metrics (
    session_id text not null,
    turn_id text not null,
    started_at text,
    completed_at text,
    turn_duration_ms integer,
    model_call_count integer not null default 0,
    model_duration_ms_total integer not null default 0,
    model_input_tokens_total integer not null default 0,
    model_output_tokens_total integer not null default 0,
    tool_call_count integer not null default 0,
    tool_duration_ms_total integer not null default 0,
    succeeded_tool_call_count integer not null default 0,
    failed_tool_call_count integer not null default 0,
    primary key (session_id, turn_id),
    foreign key (session_id) references sessions(session_id)
);

create index idx_turn_metrics_session_started
    on turn_metrics (session_id, started_at desc);
```

Notes:

- model tokens and durations are aggregated from `ModelCallCompleted` events
- tool runtime is derived from `ToolExecutionStarted` and `ToolExecutionCompleted`
- turn duration is derived from `TurnStarted` and `TurnCompleted` or `TurnFailed`

## Artifact Storage

Large or append-heavy blobs should not be forced into SQLite unless there is a clear benefit.

Good artifact candidates for filesystem storage:

- command stdout and stderr logs when large
- patch artifacts
- diff snapshots
- exported transcripts
- replay manifests containing normalized turn baselines and tool-result fixtures
- exported replay bundles used for portable eval cases

The event log should reference those artifacts by path or artifact ID.
Replay manifests and bundles should remain redacted, versioned, and portable
enough that deterministic replay can run offline without live provider
credentials or ad hoc filesystem reconstruction.

Recommended layout:

```text
.glassbox/
    sessions/
        {session_id}/
            artifacts/
                {artifact_id}.json
                {artifact_id}.patch
                {artifact_id}.log
```

## Query Patterns This Design Optimizes

### Rebuild A Session Transcript Snapshot

```sql
select message_id, role, status, created_at, completed_at, content_text
from transcript_messages
where session_id = ?
order by created_at asc;
```

### Find Active Tool Calls For The Dashboard

```sql
select tool_call_id, tool_name, status, started_at, summary
from tool_calls
where session_id = ? and status in ('requested', 'authorized', 'running')
order by started_at asc;
```

### Find Pending Approvals

```sql
select approval_id, turn_id, subject, reason, requested_at
from approvals
where session_id = ? and status = 'pending'
order by requested_at asc;
```

### Replay Raw Events For A Session

```sql
select sequence, event_type, created_at, payload_json
from events
where session_id = ?
order by sequence asc;
```

Raw event replay is useful for debugging and projection rebuilds, but it is not
the same thing as deterministic behavioral replay. Deterministic replay should
read recorded manifests and referenced artifacts alongside the canonical event
stream so the system can compare normalized behavior without reissuing live
network calls or rerunning side-effecting tools.

### Find Replay Artifacts For A Turn

```sql
select sequence, event_type, payload_json
from events
where session_id = ? and turn_id = ? and event_type = 'ReplayArtifactRecorded'
order by sequence asc;
```

This query gives the replay runner a stable event-linked path to the JSON
artifacts captured for one turn without scanning the artifact directory ad hoc.

### Find All Events For A Tool Call

```sql
select sequence, event_type, created_at, payload_json
from events
where session_id = ? and tool_call_id = ?
order by sequence asc;
```

## Write Path

The write path should follow this order:

1. validate the event envelope and payload
2. append the event to `events`
3. update the relevant projection tables
4. update `sessions.last_sequence` and `session_state.last_sequence`
5. commit as a single SQLite transaction

This keeps the event log and derived state consistent.

If projection updates fail, the entire transaction should roll back.

## Rebuild Path

Projection tables must be disposable.

The rebuild strategy should be:

1. read all events for a session in `sequence` order
2. feed them through deterministic projection handlers
3. rewrite the derived projection tables for that session

This matters for:

- schema migrations
- projection bugs
- recovery after partial failures
- local debugging

## Schema Evolution Strategy

Event sourcing shifts most compatibility burden onto event versioning.

Use these rules:

- never mutate historical events in place
- include `event_version` on every event row
- upcast old event payloads in application code when needed
- keep projection rebuild code able to interpret old event versions

Projection tables can be migrated more aggressively because they are derived.

## Tradeoffs

### Benefits

- preserves a clean append-only source of truth
- makes dashboard and CLI queries simple and fast
- avoids excessive JSON extraction in SQLite queries
- supports replay, resume, and debugging cleanly
- keeps high-volume state reads away from the raw event stream

### Costs

- write path becomes more complex because projections must be maintained
- application code must own projection rebuild logic
- there is more schema surface area to migrate and test
- projection bugs can temporarily create incorrect read models even when the event log is correct

### Why This Tradeoff Is Worth It

Glassbox is not just an append-only logger. It is an interactive CLI plus a live dashboard. That means read performance and query clarity matter almost immediately.

Using only a raw JSON event log keeps the model pure, but it shifts too much complexity into ad hoc query logic and dashboard reconstruction. The hybrid design keeps the architecture honest while making the product usable.

## Recommended Initial Scope

The first implementation does not need every table in this document.

Start with:

- `sessions`
- `events`
- `session_state`
- `transcript_messages`
- `tool_calls`
- `approvals`

Add metrics projections and more specialized tables only when the dashboard proves they are needed.

## Recommendation

For Glassbox, the recommended database direction is:

- SQLite as the local-first storage engine
- append-only `events` as the canonical history
- explicit indexed correlation columns in `events`
- rebuildable projection tables for read-heavy views
- filesystem artifacts for large blobs

That preserves the event-driven architecture while giving the CLI and dashboard the query surface they actually need.
