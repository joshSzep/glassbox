# v7 Live Transport And Multi-Observer Contract

This contract defines the v7 reliability target for local live observation across
the dashboard, terminal attach, daemon ownership, and SSE transport. It does not
introduce remote collaboration or multiple mutating operators.

## Scope

Supported v7 observer workflows:

- one workspace-local mutation owner at a time: foreground chat or daemon
- multiple read-only dashboard tabs observing the same session
- one or more terminal attach clients observing a daemon-owned session
- reconnect after browser refresh, terminal restart, daemon restart, or dropped
  live transport events
- local recovery from stale runtime-owner metadata

Non-goals:

- remote multi-user collaboration
- simultaneous independent mutation owners for one workspace
- cross-machine runtime ownership
- guaranteed delivery from the in-memory live queue alone
- browser-to-browser consensus or dashboard-owned event ordering

Persisted SQLite events are authoritative. Live delivery is only a convenience
for low-latency observation.

## Ownership Model

A workspace may have exactly one mutation owner:

- a foreground `glassbox session chat` process, or
- a workspace daemon recorded in `.glassbox/runtime-owner.json`

Read-only observers may connect through snapshots, paginated detail reads, and
`GET /sessions/{session_id}/events?after=SEQUENCE`. Observers must not infer that
multiple stream subscribers imply multiple operators may mutate. Prompt,
approval, answer, fork, and cancel actions still route through the active owner
and the existing HTTP or local command boundary.

Removing `.glassbox/runtime-owner.json` is the local shutdown signal used by
existing recovery paths. If the owner file is missing, stale, or unhealthy,
clients must inspect status and either fall back to persisted local reads or ask
the operator to run an explicit recovery command.

## Observer Count Assumptions

The in-process transport uses bounded per-subscriber queues. v7 supports a small
local operator set rather than arbitrary fanout:

- expected: 1 to 4 concurrent dashboard tabs or terminal observers per session
- tolerated: additional observers if they keep up with live delivery
- degraded: slow observers may drop in-memory events and must recover from the
  event store with an `after` cursor

The transport must expose subscriber count, dropped-event count, queue capacity,
queue peak, queue pressure, and last published sequence through health or
observability surfaces.

## Sequence Cursor Semantics

Every persisted event has a monotonically increasing session sequence. SSE
clients use the sequence as an exclusive cursor:

- connect with no `after` cursor to replay the retained session history from the
  beginning
- reconnect with `after=N` to receive persisted events with sequence `> N`
- track the highest accepted sequence locally
- ignore any frame whose sequence is less than or equal to the highest accepted
  sequence

The server may replay historical events before subscribing to live events. A
race can therefore produce the same sequence in both historical replay and live
delivery; duplicate suppression by sequence is required on the server and should
also be safe on clients.

## Backpressure And Dropped Events

The live transport is allowed to drop the oldest queued live item for a slow
subscriber when that subscriber's bounded queue is full. This is not data loss
because canonical events are already persisted.

When dropped events are observed:

1. Keep the last good snapshot visible.
2. Reconnect with the last accepted sequence as `after`.
3. Rehydrate any missed persisted events from the canonical event log.
4. Surface degraded stream posture and recovery guidance in the client.

Clients must not widen in-memory queues as their first response to turbulence.
Prefer reconnect plus persisted replay, and use observability counters to decide
whether the default queue size needs review.

## Client Recovery Contract

Dashboard refresh:

- load aggregate/session snapshot first
- open SSE with `after` set to the snapshot last sequence
- merge newer events by sequence
- if the stream disconnects, keep the snapshot visible and retry with the latest
  accepted sequence
- after retry exhaustion, show a historical/live-unavailable posture and leave
  explicit actions disabled or guarded where current evidence may be stale

Terminal reconnect:

- attach loads the latest snapshot before consuming live events
- reconnect attempts resume after the latest rendered event sequence
- terminal status moves through live, reconnecting, unavailable, or
  historical-only states
- if the daemon is gone or unhealthy, attach should report the daemon state and
  provide the next safe command rather than silently pretending the session is
  live

Daemon restart or stale owner:

- clients inspect daemon status before live attach
- stale owner metadata may be cleared only through explicit runtime recovery
  paths
- persisted sessions remain inspectable even when no daemon is running
- mutation attempts must not create a hidden second owner

Invalid frames:

- clients reject malformed or unknown event frames
- invalid live frames should not corrupt persisted state
- clients may retry the stream; if retries are exhausted, they show
  live-unavailable state while retaining persisted evidence

Terminal events:

- terminal session events such as completion or failure move clients to a
  historical-only posture after applying the final event
- subsequent reconnects should resume from the final accepted sequence and avoid
  re-opening mutation affordances unless the persisted session state is still
  actionable

## Test Matrix

The v7 automated matrix should cover:

| Area | Required evidence |
| --- | --- |
| Historical plus live SSE | historical replay, live tail, reconnect with `after`, duplicate suppression |
| Backpressure | slow subscriber drops, dropped-event counters, replay recovery from persisted events |
| Frontend SSE client | retry exhaustion, resume cursor correctness, invalid frames, terminal events |
| TUI client | reconnect from latest rendered sequence, stream-unavailable state, historical-only terminal state |
| Daemon attach | healthy daemon attach, stale owner fallback, missing owner file, unhealthy daemon guidance |
| Multi-observer | multiple SSE subscribers on one session, repeated dashboard stream creation, terminal observer smoke |
| Observability | subscriber count, queue depth, dropped events, reconnect guidance |

Tests should use deterministic fake transports or explicit synchronization. Avoid
sleep-heavy assertions and avoid provider-dependent live behavior unless the task
is specifically a provider canary.

## Implementation Review Map

This contract is grounded in these current surfaces:

- FastAPI SSE route: `src/glassbox/web/routes/events.py`
- runtime transport and bounded queues: `src/glassbox/runtime/transport.py` and
  `src/glassbox/runtime/bus.py`
- browser SSE client: `frontend/api/sse.ts`
- terminal stream consumer: `src/glassbox/cli/tui/app.py`
- daemon owner inspection and recovery: `src/glassbox/runtime/daemon.py`
- daemon attach: `src/glassbox/cli/daemon_attach.py` and
  `src/glassbox/cli/interactive_commands.py`
- observability status: `src/glassbox/runtime/observability.py`

## Operator Guidance

When live delivery looks stale or unavailable, use persisted evidence first:

```bash
glassbox observability status --json
glassbox daemon status --json
glassbox session status SESSION_ID
glassbox session attach SESSION_ID
```

If a daemon owner is stale, prefer the explicit daemon stop/start or stale-owner
recovery command paths already exposed by the CLI. Do not manually run a second
foreground mutator against the same workspace while a healthy daemon owns it.
