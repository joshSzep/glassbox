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

GBX-1280 adds command-purpose evidence to command tool attempts. Command
attempt heartbeats may record `command_purpose`, `command_review_relevance`,
`command_supports_verification`, and a short `command_purpose_reason`.
Recognized verification purposes are `test`, `lint`, `typecheck`, `build`,
`eval`, and `release_gate`; inspection commands are review context, while
publish, deploy, cleanup, dangerous, and unknown commands are not treated as
verification proof. See [command-evidence.md](./command-evidence.md) for the
purpose vocabulary and non-claims.

GBX-1281 adds a bounded `command_environment` summary for verification and
local artifact commands. The summary records a small set of toolchain versions,
Python runtime posture, allowlisted/redacted environment cues, redaction notes,
and limitations. It never stores raw environment variables, `PATH`, provider
keys, credentials, or absolute executable paths. `tool-attempt inspect` prints
toolchain drift warnings when retained command evidence no longer matches the
current local toolchain posture.

Inspect attempts from the CLI:

```bash
uv run glassbox session tool-attempts SESSION_ID --cwd .
uv run glassbox session tool-attempts SESSION_ID --status running --cwd .
uv run glassbox session tool-attempt inspect SESSION_ID TOOL_ATTEMPT_ID --cwd .
uv run glassbox session tool-attempt output SESSION_ID TOOL_ATTEMPT_ID --cwd .
uv run glassbox session status SESSION_ID --cwd .
```

`session status` prints recent attempts after recent tool activity so operators
can see whether a long tool is active, failed, cancelled, stale, or already
completed. Command and test attempts also retain managed `tool_output_*`
artifacts with stdout/stderr evidence. The artifact kind and payload distinguish
`partial` versus `final`, `truncated` versus `complete`, and `redacted` versus
`unredacted` output; terminal attempt heartbeats point at the output artifact ID
when one is recorded.

Recover attempts after inspection:

```bash
uv run glassbox session tool-attempt retry SESSION_ID TOOL_ATTEMPT_ID --yes --cwd .
uv run glassbox session tool-attempt abandon SESSION_ID TOOL_ATTEMPT_ID \
  --reason "operator chose a fresh path" --yes --cwd .
```

Retry replays retained `ModelToolCallRequested` arguments through current tool
policy and records both `RecoveryDecisionRecorded` evidence and a new durable
tool attempt. Unsafe, already running, already retried, abandoned, or succeeded
attempts are blocked. Approval-gated attempts require explicit confirmation.
Abandon records a terminal `abandoned` heartbeat and keeps output artifacts for
audit. Dashboard Actions shows retry and abandon controls beside retry posture;
both actions require browser confirmation before calling the API.

Replay evals include `ToolAttemptHeartbeat` in long-run evidence, but generated
tool-attempt, tool-call, and turn UUIDs are canonicalized before comparison.
Baselines therefore assert the durable attempt sequence and correlations without
depending on per-run UUID values.
