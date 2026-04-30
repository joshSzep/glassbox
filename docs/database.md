# Glassbox Database Design

For the docs hub and workflow guides, start at [README.md](./README.md). For installation and first-run setup, use [getting-started.md](./getting-started.md).

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

## Current Baseline Before V2 Execution

The repository already implements the core storage model described here. Treat
the following as the starting point for v2 storage work:

- the SQLite schema already includes `sessions`, `events`, `session_state`,
    `transcript_messages`, `tool_calls`, `approvals`, `runtime_notes`, and
    `turn_metrics`
- schema bootstrap now records ordered migration rows and applies explicit
    versioned migrations for newer lineage and runtime-note columns
- projection rebuild already exists as an implemented repository and CLI path
    over canonical events
- session discovery, lineage-aware snapshots, approval queues, runtime context,
    and replay or eval workflows already depend on this schema in production code

v2 database work should therefore focus on making schema evolution, rebuild
observability, recovery, and retention more explicit rather than reintroducing
the current storage model from scratch.

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

This same storage model also supports session branching without changing the
source-of-truth rule. The parent session keeps its original canonical event
stream, while child sessions record explicit lineage metadata and their own
canonical imported-history or post-fork events. Branching does not require
mutating or truncating parent events.

## Store Implementation Boundaries

The persistence contract above is stable even though the store implementation is
now decomposed internally.

- `src/glassbox/store/sqlite.py` is the public compatibility facade for schema bootstrap, append/read helpers, rebuild entrypoints, and list-style query helpers
- `src/glassbox/store/sqlite_schema.py` owns schema bootstrap and the explicit ordered migration registry, while projection-family DDL and migration helpers live in focused `sqlite_schema_*` modules for sessions, tasks, verification ledger, checkpoints, compactions, tool attempts, background jobs, branch search, workspace memory, provider recovery, and long-run correlations
- `src/glassbox/store/sqlite_sessions.py`, `sqlite_events.py`, `sqlite_projections.py`, `sqlite_queries.py`, and `sqlite_fork.py` own the other broad internal storage concerns separately
- `src/glassbox/store/sqlite_queries.py` remains a thin read-model facade over
    focused `sqlite_query_*` modules for transcript, runtime notes, tools and
    approvals, turn metrics, autonomy budgets, task projections, checkpoint
    projections, and branch-search projections
- `src/glassbox/store/repositories.py` owns the concrete repository adapter
    surface while session, event/fork, projection-read, background-job,
    workspace-memory, task, checkpoint history, branch-search, and artifact
    behavior live in focused `repository_*` delegates
- `src/glassbox/store/artifacts.py` owns filesystem artifact writes and reads while returning the shared `StoredArtifact` contract type from `services/contracts.py`

This refactor changed internal ownership, not the operator-visible storage model.
Schema bootstrap, append ordering, projection rebuild semantics, and artifact
layout remain aligned with the tables and rules documented here.

Store query modules remain below runtime and transport layers. They may read and
shape deterministic projection records, but runtime query services, CLI
formatters, and web serializers own operator-facing summaries and response
models.

The schema upgrade story now starts with an explicit v3 baseline and applies
ordered migrations to the current schema version during runtime bootstrap. The
remaining recovery work is projection-health and rebuild observability as
described in [tasks-v2.md](./tasks-v2.md).

## Schema Migrations

Schema migrations are tracked in `schema_migrations` with one row per applied
version. Fresh workspaces are initialized by ensuring the v3 baseline table set,
recording the baseline, and then applying each later migration in order. Older
workspaces that already have migration metadata reuse the same ordered path:
baseline tables are ensured with `create table if not exists`, migration shape
checks run idempotently, and missing version rows are recorded.

The current migration sequence is:

- `3`: baseline event store and projection tables
- `4`: session lineage columns and parent-session index
- `5`: runtime-note source columns and provenance backfill
- `6`: policy metadata projection columns
- `7`: task plan projection tables
- `8`: autonomy budget projection table
- `9`: background job projection table
- `10`: background job retry triage columns
- `11`: workspace memory projection table
- `12`: branch search projection tables
- `13`: long-run event correlations and projection
- `14`: task checkpoint projection table
- `15`: session-scoped task checkpoint projection key for inspection imports
- `16`: context compaction projection table
- `17`: tool attempt projection table
- `18`: task verification ledger projection table

Glassbox refuses to open a database with a schema version newer than the running
build supports. Schema upgrade is distinct from projection rebuild: migrations
change table shape and metadata, while rebuild commands repopulate derived state
from canonical events.

The v10 checkpoint read model lives in `task_checkpoints`. Each row is derived
from a canonical `TaskCheckpointCreated` event and keeps the objective, current
phase, last completed step, next action, blockers, touched files, verification
and budget posture, recovery guidance, and source event range. Latest checkpoint
and checkpoint-history queries are read models only; the canonical event log
remains the authority and projection rebuild must reproduce the table.

Autonomy budget posture still lives in `autonomy_budget_posture` and remains a
JSON-backed projection rather than a schema-per-limit table. v10 time-window
fields for maximum unattended duration, checkpoint interval, quiet-window
policy, maximum retry delay, and checkpoint approval requirement are stored in
the canonical budget JSON and remaining-counter JSON emitted by
`BudgetDecisionRecorded`. Query helpers derive the API/CLI fields for remaining
unattended time, next checkpoint due time, retry-delay budget, quiet-window
policy, and checkpoint-approval requirement from those JSON values.

The v10 compaction read model lives in `context_compactions`. Each row is
derived from a canonical `ContextCompactionCreated` event and keeps the scope,
source event range, managed artifact id, freshness, source artifact ids,
limitations, and counts for decisions, unresolved questions, and accepted risks.
The artifact payload remains the detailed provenance authority.

The v10 tool-attempt read model lives in `tool_attempts`. Each row is derived
from canonical `ToolAttemptHeartbeat` events and keeps attempt identity,
tool-call correlation, status, heartbeat message and expiry, timing, progress,
output artifact reference, retry safety, retry classification, retry approval
posture, retry policy reason, and last source sequence. It is
intentionally separate from `tool_calls`: tool calls describe provider-requested
tool use, while tool attempts describe the runtime execution evidence used for
long-running inspection and recovery.

The v10 verification ledger read model lives in `task_verification_ledger`.
Each row is derived from canonical task verification events and keeps the check
identity, optional task step, check family, source, argv, changed paths, eval
links, attempts, latest output artifact, latest failed check, last successful
check, accepted residual risks, and last source sequence. Task detail queries
derive the current verification posture from this projection so long-running
work can report incremental proof instead of only a final checklist.

## Canonical Tables

### Sessions

The sessions table is an entry point for listing and resuming sessions. Its
`status` and `last_sequence` should stay aligned with the latest derived
session-state projection so list and filter queries can find suspended sessions
without replaying the event log.

For branching, `sessions` is also the right place for nullable lineage metadata
such as parent session ID, fork source turn ID, fork source sequence, and an
optional operator-visible branch label. That metadata should describe ancestry
and discovery, not replace event-sourced runtime state.

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

create index idx_sessions_status_updated
    on sessions (status, updated_at desc);

create index idx_sessions_parent_updated
    on sessions (parent_session_id, updated_at desc);
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

The full event payload still lives in `payload_json`. The extra columns are
query aids, not a second source of truth.

For child-session creation, the event log continues to stay session-scoped. If
Glassbox materializes inherited transcript history into the child session, those
imported child-session events still belong to the child's canonical event
stream rather than acting as pointers into mutable parent state.

## Projection Tables

Projection tables exist to answer the queries the product asks repeatedly.

These tables should always be treated as rebuildable derived state.

Projection health is inspected by comparing canonical event progress with the
derived `session_state.last_sequence` projection and by checking that projection
tables are readable. CLI status, session snapshots, dashboard projection details,
and `glassbox projection check` report whether projections are `ok`, `stale`, or
`unavailable`, along with canonical sequence, projected sequence, lag, estimated
rebuild event scope, projected progress ratio, and repair guidance. This keeps
canonical event integrity distinct from derived-state corruption: degraded
projections should be repaired with `glassbox projection rebuild`, not treated as
event-log loss.

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

### Runtime Notes Projection

This table supports runtime-context notes, inherited branch context, and other
operator-visible annotations without forcing those messages into ad hoc JSON
queries.

```sql
create table runtime_notes (
    session_id text not null,
    sequence integer not null,
    source_session_id text,
    source_sequence integer,
    category text not null,
    message text not null,
    created_at text not null,
    primary key (session_id, sequence),
    foreign key (session_id) references sessions(session_id)
);

create index idx_runtime_notes_session_created
    on runtime_notes (session_id, created_at, sequence);
```

Notes:

- `source_session_id` and `source_sequence` preserve provenance when a note is inherited into a child branch
- the projection remains rebuildable from canonical note events
- runtime-context APIs can read branch-aware note history without reconstructing it from unrelated transcript or tool records

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

The event log references those artifacts by path and artifact ID. Newly recorded
tool and replay artifact events also include the file size and SHA-256 digest so
operators can compare persisted metadata with local filesystem state during
retention and recovery workflows. Replay manifests and bundles should remain
redacted, versioned, and portable enough that deterministic replay can run
offline without live provider credentials or ad hoc filesystem reconstruction.
Command and test tool output artifacts use `tool_output_*` artifact kinds that
encode whether the retained output is `partial` or `final`, `truncated` or
`complete`, and `redacted` or `unredacted`; the JSON payload carries the same
fields with stdout/stderr and execution-envelope metadata.

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

### Artifact Retention And GC

Artifact garbage collection is intentionally narrower than schema migration or
projection rebuild. `glassbox artifacts inspect` reports managed artifact state,
SHA-256 digests, missing event-referenced files, stale cleanup candidates,
retention-class counts, protected/candidate byte totals, artifact age, and total
`.glassbox` storage pressure without deleting anything. Use
`--warning-threshold-mb` to tune the local storage warning threshold for inspect
and prune reports. The JSON report distinguishes protected, event-referenced,
orphaned, reclaimable, and missing-reference states so operators can tell
storage pressure apart from integrity gaps. `glassbox artifacts prune --dry-run`
shows the same candidate cleanup path in prune terms before deleting anything.
Treat that dry-run as the review step: confirm every reclaimable path and reason
first, then run non-dry-run prune only when the preview matches the intended
cleanup. Running prune without `--dry-run` may delete only managed stale files under
`.glassbox/sessions/*/artifacts/` that are not referenced by canonical artifact
events, and aged derived eval outputs under `.glassbox/evals/`.

The GC path must not delete canonical SQLite event data, event-referenced session
artifacts, source-controlled replay bundles under `evals/`, or curated eval
baselines. Missing event-referenced artifact files are reported as integrity
gaps rather than silently repaired or removed from the event log.

## Workspace Backup And Restore

Workspace backup is the recovery path for local Glassbox state. It is separate
from `replay bundle export` and eval baseline promotion: replay bundles are portable
session fixtures, while workspace backups are operational snapshots of the local
runtime state needed to recover the same workspace history.

`glassbox backup create [output]` writes an inspectable zip archive with:

- `glassbox-backup.json`, a manifest with format version, source paths, file
    roles, byte sizes, and SHA-256 hashes
- a SQLite snapshot of the canonical database stored as `.glassbox/glassbox.sqlite3`
- event-referenced local artifacts under `.glassbox/sessions/*/artifacts/`

The backup scope intentionally excludes source-controlled `evals/` bundles,
curated eval baselines, provider credentials, runtime owner metadata, logs, and
orphaned or stale artifacts that are not referenced by canonical events. If a
canonical artifact event points at a missing local file, backup creation fails so
the operator sees the integrity gap instead of creating an incomplete recovery
archive.

`glassbox backup restore <archive>` validates the manifest and every archived
file hash before writing. Restore writes the database to the selected runtime
database path and restores event-referenced artifacts under the target
workspace's `.glassbox` directory. Existing target files are not overwritten
unless `--force` is supplied.

## Query Patterns This Design Optimizes

The query patterns below are implemented behind the split store read boundary:
SQLite-specific row reads live in `sqlite_query_*` modules, while concrete
service adapters call them through focused `repository_*` delegates and the
stable `repositories.py` facade. That keeps projection reads rebuildable from
canonical events without making HTTP, CLI, or dashboard code responsible for
raw SQL.

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

For the current baseline, note the distinction between what already exists and
what v2 still needs:

- today: schema bootstrap can create the current schema, stamp the current
    schema version, and apply a limited amount of ad hoc upgrade logic during
    initialization
- today: projection rebuild is available from canonical events
- still needed for v2: explicit ordered migrations, upgrade metadata the
    operator can reason about, and projection-health or lag reporting beyond
    manual rebuild paths

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

The current baseline schema includes:

- `sessions`
- `events`
- `session_state`
- `transcript_messages`
- `tool_calls`
- `approvals`
- `runtime_notes`
- `turn_metrics`

Add metrics projections and more specialized tables only when the dashboard proves they are needed.

## Recommendation

For Glassbox, the recommended database direction is:

- SQLite as the local-first storage engine
- append-only `events` as the canonical history
- explicit indexed correlation columns in `events`
- rebuildable projection tables for read-heavy views
- filesystem artifacts for large blobs

That preserves the event-driven architecture while giving the CLI and dashboard the query surface they actually need.
