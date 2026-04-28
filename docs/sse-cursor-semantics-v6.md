# SSE Cursor Semantics

Glassbox SSE clients use persisted event sequences as reconnect cursors.

## Server Contract

- `GET /sessions/{session_id}/events?after=N` returns events for that session
  with `sequence > N`.
- Historical replay is emitted before live delivery.
- The SSE `id` field is the event sequence.
- The server tracks the highest sequence emitted on a stream and suppresses any
  queued live event whose sequence is less than or equal to that value.
- Keepalive frames are SSE comments (`: keepalive`) and do not advance the
  sequence cursor.
- Completed, failed, and cancelled sessions remain readable through historical
  replay even when no live owner can be attached.

## Client Contract

- Dashboard clients reconnect with the highest event sequence decoded by the SSE
  client.
- TUI clients call `stream_events(after_sequence=<last rendered sequence>)` and
  advance that cursor after each applied runtime event.
- Terminal daemon attach uses the snapshot `last_sequence` for the initial
  attach and advances the retry cursor with every rendered SSE event.
- Clients should treat live delivery as lossy and sequence replay as the recovery
  path. A disconnected or degraded stream should reconnect from the last
  observed sequence rather than the backend's latest published sequence.

## Operator Notes

- A repeated sequence after reconnect is a server or client bug; it should not be
  rendered twice.
- A gap in live delivery is recoverable when the next request uses the last
  observed sequence as the `after` cursor.
- Keepalive comments prove the HTTP stream is still open, not that new runtime
  events exist.
