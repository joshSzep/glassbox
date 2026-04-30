# Tool Attempts

v10 records durable tool-attempt heartbeats beside the existing `tool_calls`
projection. A tool call remains the provider/request-level record. A tool
attempt is the runtime execution record that can survive long-running command,
test, timeout, cancellation, or restart inspection.

`ToolAttemptHeartbeat` is the canonical event for GBX-1040. The
`tool_attempts` projection rebuilds from those events and tracks:

- attempt id, session, turn, tool call, task, and tool name
- status: `started`, `running`, `waiting`, `succeeded`, `failed`,
  `cancelled`, `stale`, `retried`, or `abandoned`
- latest heartbeat message, expiry, and source sequence
- start, heartbeat, and completion timestamps
- progress units, output artifact reference, and retry posture when known

Inspect attempts from the CLI:

```bash
uv run glassbox session tool-attempts SESSION_ID --cwd .
uv run glassbox session tool-attempts SESSION_ID --status running --cwd .
uv run glassbox session status SESSION_ID --cwd .
```

`session status` prints recent attempts after recent tool activity so operators
can see whether a long tool is active, failed, cancelled, stale, or already
completed. GBX-1041 adds partial-output artifacts, and GBX-1042/GBX-1043 add
safe-to-retry classification and recovery actions.

Replay evals include `ToolAttemptHeartbeat` in long-run evidence, but generated
tool-attempt, tool-call, and turn UUIDs are canonicalized before comparison.
Baselines therefore assert the durable attempt sequence and correlations without
depending on per-run UUID values.
