# Live Transport Backpressure

Glassbox live streams use bounded in-process subscriber queues. When a subscriber
falls behind, the transport drops the oldest queued live event and keeps the most
recent event available. Persisted session events remain authoritative.

## Operator Guidance

- Treat nonzero `dropped_events` or queue pressure of `1.0` as degraded live
  delivery.
- Refresh dashboards or reconnect terminal clients from the last observed event
  sequence.
- Use `/sessions/{session_id}/events?after=SEQUENCE` to replay canonical events
  that may have been missed live.
- If projection lag is also degraded, run `glassbox projection check --all` before
  trusting aggregate views.

## Expected Recovery

1. A slow live subscriber misses one or more queued events.
2. Transport stats increment `dropped_events` and record peak queue pressure.
3. The client reconnects with the last sequence it actually observed.
4. Historical replay returns every persisted event with a greater sequence.

The live stream can be lossy; the persisted event log is not.
