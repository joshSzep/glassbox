# V6 Live Transport And Runtime Ownership Audit

This audit is the `GBX-660` baseline for SSE delivery, in-process runtime
transport, daemon ownership, and live attach behavior. It records current
semantics before the hardening tasks in Phase 66 change behavior.

## Current Contract

- The SQLite event log remains canonical. Live delivery is an optimization over
  persisted events, not the source of truth.
- `GET /sessions/{session_id}/events?after=SEQUENCE` first replays persisted
  events with sequence greater than `after`, then streams live events from the
  runtime transport.
- SSE frames use the event `sequence` as the SSE `id`, and clients use the last
  observed sequence as their reconnect cursor.
- The in-process event transport fans out to bounded subscriber queues. When a
  subscriber queue is full, the oldest queued live event is dropped and
  `dropped_events` increments.
- Daemon ownership is workspace-scoped through `.glassbox/runtime-owner.json`.
  Healthy owner metadata routes live mutations and attach flows through the
  daemon HTTP/SSE control plane. Stale metadata can be cleared and then local
  fallback is allowed.

## Existing Coverage

- `tests/unit/test_runtime_transport.py` proves basic fan-out, subscriber count,
  and zero-drop behavior.
- `tests/integration/test_web_sse_events.py` covers unknown sessions, response
  headers, historical replay, `after` filtering, frame shape, and one live event
  delivery path.
- `tests/integration/test_daemon_runtime.py` covers daemon start/status/stop,
  duplicate owner rejection, stale owner recovery, live attach routing, TUI
  attach routing, unavailable owner errors, historical-only sessions, and stale
  fallback.
- Dashboard stream state tracks `connecting`, `reconnecting`, `live`,
  `live_unavailable`, and `historical_snapshot`, and reconnects with the last
  sequence observed by the SSE client.
- Terminal daemon attach streams events with `after=last_sequence`, retries
  transient stream failures, and renders a reconnect/reconnected line.
- `observability status` exposes runtime state, transport subscriber count,
  transport dropped event count, reconnect mode, projection lag, and retained
  eval evidence.

## Deterministic Reconnect Transcript

The existing deterministic reconnect-style path is:

1. Persist events for a session.
2. Connect to `/sessions/{session_id}/events?after=0` and replay history.
3. Read the highest emitted sequence.
4. Reconnect with `/sessions/{session_id}/events?after=<highest sequence>`.
5. Verify previously seen historical events are skipped.
6. Publish a live event through the transport and verify the stream emits it for
   the same session.

This is covered today by `test_sse_replays_historical_events_on_connect`,
`test_sse_after_parameter_skips_already_seen_events`, and
`test_sse_delivers_live_events`.

## Already-Good Semantics To Preserve

- Persisted events are replayed before live delivery for a fresh stream.
- `after=N` is exclusive and skips events with `sequence <= N`.
- Unknown sessions return `404` before opening a long-lived subscription.
- Completed, failed, and cancelled sessions remain historically inspectable even
  when live attach is unavailable.
- Healthy daemon ownership blocks local mutations and points operators at the
  live owner rather than creating a second owner.
- Stale daemon metadata is recoverable through owner cleanup and local fallback.
- Live delivery can drop bounded-queue items without deleting canonical events.

## Issues And Risks

### High Severity

- Slow-subscriber drop recovery is not directly tested. The transport increments
  `dropped_events`, but there is no deterministic test proving a client that
  missed live events can recover every missing event from persisted replay.
- SSE replay/live boundary duplicate suppression is only partially covered. The
  route subscribes before reading historical events, which prevents a gap, but a
  live event already replayed historically can still be emitted again if it is
  also queued in the subscription.
- Terminal daemon attach retry behavior is covered indirectly by code review,
  not by a deterministic fake stream test. A regression could make reconnect
  copy or `after` cursor handling drift from dashboard behavior.

### Medium Severity

- Transport observability reports subscriber count and total dropped events, but
  not queue capacity, queue pressure, or per-subscription last observed sequence.
- Dashboard reconnect state is client-derived. Backend observability does not
  currently tell the browser whether a stream is healthy, degraded by drops, or
  merely unavailable from the browser's perspective.
- Daemon status explains owner state well, but release-smoke guidance is split
  between daemon status, observability status, and task docs rather than one
  concise lifecycle checklist.
- Port-conflict and startup-failure paths have less deterministic coverage than
  healthy startup, stale metadata, and stop.

### Low Severity

- SSE keepalive behavior exists in the route but lacks focused coverage.
- Client disconnect cleanup relies on the subscription context manager and has no
  explicit subscriber-count regression test at the route level.
- Projection lag is surfaced in observability, but dashboard copy for degraded
  projections and stream retry state is not tested together.

## Recommended Phase 66 Tests

- Add transport tests with a small subscriber queue proving dropped live events
  increment counters and the newest event remains deliverable.
- Add an SSE test that overflows a live subscriber, reconnects with the last
  observed sequence, and proves persisted replay recovers missed events.
- Add an SSE replay/live boundary test for duplicate expectations when an event
  is both persisted and queued after subscription creation.
- Add keepalive and client-disconnect route tests that assert subscriber cleanup.
- Add terminal daemon-attach fake stream tests for reconnect attempt copy,
  `after` cursor advancement, and failure after exhausted retries.
- Add daemon lifecycle tests for startup failure, missing health route, port
  conflict, stop timeout, and attach after owner metadata cleanup.
- Add observability tests for degraded transport next actions when drops or queue
  pressure are present.

## Release Risk Baseline

Phase 66 can start from a stable base: the event-sourced recovery model is sound,
daemon ownership prevents competing mutation owners, and both dashboard and
terminal clients already use sequence cursors. The main risk is not event loss in
storage; it is whether live clients notice and recover from dropped or duplicate
delivery without confusing operators.
