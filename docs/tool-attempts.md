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

GBX-1042 expands retry posture from a nullable safety flag into typed
classification evidence:

- `retryable`: the failed attempt can be retried because retained evidence shows
  no workspace mutation risk
- `idempotent`: the command is recognized as repeatable verification or
  inspection, such as pytest, frontend lint/typecheck/test/build, ruff, ty, or
  read-only shell inspection
- `unsafe_to_retry`: the attempt already succeeded or the command is known to
  mutate local or remote state when rerun
- `unknown`: retained evidence is insufficient to prove retry safety
- `already_running`: the attempt is active; wait or inspect before retrying
- `abandoned`: the attempt was explicitly abandoned

`retry_requires_approval` preserves policy posture for risky retry decisions.
For example, a failed pytest command can be classified as `idempotent` while
still requiring approval when the original command policy required operator
confirmation. Unknown command retries are approval-gated by default.

Inspect attempts from the CLI:

```bash
uv run glassbox session tool-attempts SESSION_ID --cwd .
uv run glassbox session tool-attempts SESSION_ID --status running --cwd .
uv run glassbox session status SESSION_ID --cwd .
```

`session status` prints recent attempts after recent tool activity so operators
can see whether a long tool is active, failed, cancelled, stale, or already
completed. Command and test attempts also retain managed `tool_output_*`
artifacts with stdout/stderr evidence. The artifact kind and payload distinguish
`partial` versus `final`, `truncated` versus `complete`, and `redacted` versus
`unredacted` output; terminal attempt heartbeats point at the output artifact ID
when one is recorded. GBX-1043 adds explicit retry, abandon, and recovery
actions on top of this read-only classification evidence.

Replay evals include `ToolAttemptHeartbeat` in long-run evidence, but generated
tool-attempt, tool-call, and turn UUIDs are canonicalized before comparison.
Baselines therefore assert the durable attempt sequence and correlations without
depending on per-run UUID values.
