# Glassbox v10 Durability Audit

This audit grounds the v10 long-running-task work in current source boundaries.
It classifies state that can survive restart, stream loss, provider failure, or
daemon interruption, and it names the implementation tasks that should close the
gaps.

## Classification Legend

- **Already durable**: canonical events or retained artifacts carry the state
  needed to explain or continue the workflow.
- **Rebuildable projection**: derived state can be rebuilt from canonical
  events and should not become a second source of truth.
- **Recoverable but weakly surfaced**: the runtime can usually explain or
  recover, but the operator surface lacks a specific long-run status or next
  action.
- **Process-local**: meaningful state exists only in memory while the process is
  alive.
- **Accepted non-goal**: not required for v10 release readiness.

## Boundary Map

| Boundary | Classification | Source | Current behavior | v10 work |
| --- | --- | --- | --- | --- |
| Event vocabulary for sessions, turns, cancellation, model calls, tools, approvals, questions, tasks, verification, jobs, memory, and replay | Already durable, but incomplete for long-run lifecycle | `src/glassbox/core/events.py:87`, `src/glassbox/core/events.py:152`, `src/glassbox/core/events.py:212`, `src/glassbox/core/events.py:241`, `src/glassbox/core/events.py:451`, `src/glassbox/core/events.py:639` | Existing events describe many atomic facts, including model/tool start and completion, task verification, and job heartbeats. They do not yet define first-class long-run lifecycle, checkpoint, compaction, tool-attempt retry, model-call recovery, or provider-recovery evidence. | `GBX-1010`, `GBX-1020`, `GBX-1030`, `GBX-1040`, `GBX-1081` |
| Turn engine active cancellation controller | Process-local | `src/glassbox/runtime/turn_engine.py:266`, `src/glassbox/runtime/turn_engine.py:306`, `src/glassbox/runtime/turn_engine.py:318` | Cancellation requests are recorded when the live controller exists, but the controller map is in memory and disappears with the process. Restarted work can inspect persisted turn events, but cannot recreate an in-flight cancellation controller. | `GBX-1011`, `GBX-1022`, `GBX-1053` |
| Turn failure and cancellation recording | Already durable | `src/glassbox/runtime/turn_engine.py:288`, `src/glassbox/runtime/turn_engine.py:295` | Cancellation and failure paths append durable events with reason and stage. This is enough for postmortem inspection, but not enough to classify incomplete model/tool attempts after process death. | `GBX-1011`, `GBX-1042`, `GBX-1081` |
| Model loop conversation and model-call execution | Process-local | `src/glassbox/runtime/model_loop.py:73`, `src/glassbox/runtime/model_loop.py:104`, `src/glassbox/runtime/model_loop.py:117` | `ModelConversationState` carries the continuation conversation in memory. `ModelCallStarted` and replay capture are durable, but the live provider call result, stream translator state, and in-flight conversation mutations are not resumable after restart. | `GBX-1011`, `GBX-1020`, `GBX-1032`, `GBX-1081` |
| Model stream cancellation | Recoverable but weakly surfaced | `src/glassbox/runtime/model_loop.py:169` | The model call can be cancelled while the process is alive, and cancellation is turned into a typed stage. Lost streams or provider errors are still surfaced as generic failed-turn evidence rather than retry/fallback state. | `GBX-1011`, `GBX-1081`, `GBX-1082` |
| Tool request and policy evidence | Already durable | `src/glassbox/runtime/turn_tool_executor.py:118`, `src/glassbox/runtime/turn_tool_executor.py:196`, `src/glassbox/runtime/turn_tool_executor.py:287` | Tool calls, arguments, policy traces, approval requests, and ask-user questions are recorded before execution or suspension. This makes approval and question resumption reconstructable. | `GBX-1040`, `GBX-1043` |
| Tool execution output and completion | Recoverable but weakly surfaced | `src/glassbox/runtime/turn_tool_executor.py:346`, `src/glassbox/runtime/turn_tool_executor.py:374`, `src/glassbox/runtime/turn_tool_executor.py:399`, `src/glassbox/runtime/turn_tool_executor.py:448` | Tool start, output chunks, failure, cancellation, completion, replay result, and context artifacts are recorded. Long commands do not yet have first-class attempt records, heartbeats independent of output chunks, partial-output artifacts by policy, or safe-to-retry classification. | `GBX-1040`, `GBX-1041`, `GBX-1042`, `GBX-1043` |
| Approval and ask-user suspension reconstruction | Already durable | `src/glassbox/runtime/turn_resumption.py:104`, `src/glassbox/runtime/turn_resumption.py:110`, `src/glassbox/runtime/turn_resumption.py:141` | Resumption reconstructs pending questions and approvals from persisted events, including assistant message id, model-call count, and original tool arguments. This is the strongest current restart boundary. | Preserve in `GBX-1011`; include checkpoint context in `GBX-1022` |
| Background job leases, heartbeats, and stale recovery | Already durable, with weak long-run detail | `src/glassbox/runtime/background_jobs.py:43`, `src/glassbox/runtime/background_jobs.py:103`, `src/glassbox/runtime/background_jobs.py:167`, `src/glassbox/runtime/background_job_lifecycle.py:46` | Jobs have claims, leases, heartbeats, cancellation acknowledgement, stale-claim recovery, retry, failure, and abandoned states. Progress messages are coarse and do not yet carry task checkpoint, tool-attempt, or verification-ledger posture. | `GBX-1020`, `GBX-1040`, `GBX-1051`, `GBX-1070` |
| Mutating task continuation jobs | Recoverable but weakly surfaced | `src/glassbox/runtime/background_task_continuation.py:26`, `src/glassbox/runtime/background_task_continuation.py:47`, `src/glassbox/runtime/background_task_continuation.py:98`, `src/glassbox/runtime/background_task_continuation.py:110` | A continuation job runs one bounded task step, pauses on approval/input/failure/cancellation, requires explicit autonomy budget, and records task-step progress. It does not yet write a durable checkpoint before and after the continuation turn. | `GBX-1020`, `GBX-1022`, `GBX-1060` |
| Daemon ownership | Recoverable but weakly surfaced | `src/glassbox/runtime/daemon.py:96`, `src/glassbox/runtime/daemon.py:130`, `src/glassbox/runtime/daemon.py:183` | Workspace owner metadata prevents concurrent mutation, can be inspected, and stale metadata can be cleared. The daemon owns background jobs, but owner restart does not yet emit long-run recovery state for active turns or tool attempts. | `GBX-1011`, `GBX-1053` |
| SSE server replay and live stream | Already durable for reconnect, weak for very long streams | `src/glassbox/web/routes/events.py:51`, `src/glassbox/web/routes/events.py:66`, `src/glassbox/web/routes/events.py:69`, `src/glassbox/web/routes/events.py:76` | The route replays persisted events after a sequence cursor, then streams live events with keepalives. It relies on numeric sequence cursors and in-process fanout for live delivery. | `GBX-1012`, `GBX-1051` |
| Dashboard SSE client | Recoverable but weakly surfaced | `frontend/api/sse.ts:151`, `frontend/api/sse.ts:197`, `frontend/api/sse.ts:230`, `frontend/api/sse.ts:243` | The client reconnects from the last sequence and falls back to a persisted snapshot when live streaming fails. It does not yet expose long-run heartbeat age, stuck-state, checkpoint, or compaction freshness. | `GBX-1012`, `GBX-1051`, `GBX-1052` |
| Context assembly | Rebuildable projection plus process-local prompt assembly | `src/glassbox/runtime/context_builder.py:46`, `src/glassbox/runtime/context_builder.py:66`, `src/glassbox/runtime/context_builder.py:94`, `src/glassbox/runtime/context_snapshots.py:249` | Context is rebuilt from persisted transcript, session state, runtime notes, working set, artifacts, workspace memory, and fresh repository index. The final prompt context is assembled per turn and no general compaction artifact exists. | `GBX-1030`, `GBX-1031`, `GBX-1032`, `GBX-1033` |
| Artifact-backed failure digests | Already durable for pytest failure summaries only | `src/glassbox/runtime/context_snapshots.py:260`, `src/glassbox/runtime/context_snapshots.py:271`, `src/glassbox/runtime/context_snapshots.py:273` | Pytest failure digests are read from retained artifacts and freshness is inferred from later `run_tests` requests. This is a useful pattern for compactions, but currently narrow to test-failure context. | `GBX-1030`, `GBX-1041`, `GBX-1070` |
| SQLite projections | Rebuildable projection | `src/glassbox/store/sqlite_projections.py:29`, `src/glassbox/store/sqlite_projections.py:47` | Session state, transcript, tools, approvals, runtime notes, metrics, tasks, branch search, budgets, jobs, and memory are rebuildable from events. There are no checkpoint, compaction, tool-attempt, provider-recovery, or verification-ledger projection tables yet. | `GBX-1010`, `GBX-1020`, `GBX-1030`, `GBX-1040`, `GBX-1070`, `GBX-1081` |
| Replay and eval | Already durable for current behavioral contracts | `src/glassbox/runtime/replay_orchestrator.py:40`, `src/glassbox/runtime/replay_orchestrator.py:108`, `evals/profiles.json` | Replay/eval can load bundles, execute deterministic comparisons, classify drift, and serve as release authority. It lacks long-run interruption, checkpoint, compaction, partial-tool-output, stale-verification, and provider-recovery cases. | `GBX-1090`, `GBX-1091` |
| Dashboard reducers and attention summary | Rebuildable frontend projection, weak for long-run concepts | `frontend/state/session-events.ts:28`, `frontend/state/session-events.ts:110`, `frontend/state/session-events.ts:186`, `frontend/state/workspace-attention.ts:19` | Reducers derive dashboard state from snapshots and SSE envelopes for turns, cancellations, tools, approvals, questions, runtime notes, jobs, projections, and provider cues. They do not yet understand long-run lifecycle, checkpoint, compaction, tool-attempt heartbeat, or verification-ledger event types. | `GBX-1050`, `GBX-1051`, `GBX-1052`, `GBX-1053` |
| Multi-writer or hosted recovery | Accepted non-goal | [v10-long-running-task-contract.md](./v10-long-running-task-contract.md) | v10 keeps one local mutation owner, local workspace state, and deterministic release authority. Hosted orchestration and simultaneous multi-writer mutation stay out of scope. | None for v10 |

## Priority Work Queue

1. `GBX-1010`: add long-run lifecycle event vocabulary before widening
   projections or UI.
2. `GBX-1011`: define incomplete-turn recovery semantics for process death,
   lost stream, provider failure, and cancellation after controller loss.
3. `GBX-1012`: harden event cursors and live-stream diagnostics for long
   dashboard sessions.
4. `GBX-1020` through `GBX-1022`: add durable checkpoints before long
   continuation becomes a product promise.
5. `GBX-1030` through `GBX-1033`: make compaction an artifact-backed workflow
   with provenance and invalidation.
6. `GBX-1040` through `GBX-1043`: promote generic tool events into durable
   attempt, heartbeat, partial-output, retry, and recovery surfaces.
7. `GBX-1050` through `GBX-1053`: teach terminal and dashboard surfaces to show
   heartbeat, stuck-state, checkpoint, compaction, and recovery actions.
8. `GBX-1060` through `GBX-1062`: add time-aware budgets and scheduled stop
   reasons before allowing longer unattended continuation windows.
9. `GBX-1070` through `GBX-1073`: add incremental verification, stale-drift,
   last-known-good, and long-run eval recommendation evidence.
10. `GBX-1081` and `GBX-1082`: make provider failure and fallback posture
    explicit and advisory.
11. `GBX-1090` and `GBX-1091`: promote interruption, recovery, compaction, and
    long-run cockpit cases into deterministic release evidence.

## Test Inventory

Existing useful coverage:

- `tests/unit/test_core_events.py`: event payload contracts for cancellation,
  background job heartbeat, recovery, and verification events.
- `tests/unit/test_model_loop.py`: model-loop cancellation behavior.
- `tests/unit/test_turn_resumption.py`: approval and ask-user resumption from
  persisted events.
- `tests/integration/test_background_job_runner.py` and
  `tests/integration/test_background_jobs.py`: job heartbeats, stale recovery,
  retry, cancellation, and worker behavior.
- `tests/integration/test_web_sse_events.py` and
  `frontend/tests/sse-client.test.ts`: server/client SSE replay and reconnect
  behavior.
- `tests/unit/test_context_builder.py`: context assembly, artifact-backed
  pytest digests, workspace memory, and repository-index freshness.
- `tests/integration/test_projection_rebuild.py` and
  `tests/integration/test_sqlite_projections.py`: rebuildable projection
  behavior.
- `tests/unit/test_replay_orchestrator.py`,
  `tests/integration/test_replay_runner.py`, and
  `tests/integration/test_cli_replay_commands.py`: deterministic replay
  orchestration and CLI behavior.
- `frontend/tests/session-state.test.ts`,
  `frontend/tests/workspace-overview.test.ts`, and
  `frontend/tests/dashboard-stores.test.ts`: dashboard reducers, overview, and
  store state for current v9 concepts.

Missing or weak coverage to add during v10:

- process restart after `ModelCallStarted` without `ModelCallCompleted`
- process restart after `ToolExecutionStarted` with only partial
  `ToolOutputChunk` evidence
- durable checkpoint creation before and after task continuation
- checkpoint-based resume rejection when the workspace or verification posture
  is stale
- compaction artifact schema, source event range validation, source artifact
  validation, and invalidation
- long command partial-output artifact retention and pruning interaction
- safe-to-retry classification for read-only, idempotent write, non-idempotent
  write, cancelled, timed-out, and provider-failed attempts
- event cursor recovery across large sessions, dropped in-process fanout, and
  dashboard reconnect exhaustion
- terminal and dashboard stuck-state rendering from stale heartbeat evidence
- incremental verification stale-drift detection after workspace changes
- provider failure recovery and model-switch recommendation state
- deterministic replay/eval cases for all promoted v10 long-run contracts

## Audit Conclusion

The v9 runtime has a strong event-sourced baseline: approvals, questions,
sessions, task plans, jobs, artifacts, projections, replay, and dashboard state
are already inspectable or rebuildable. The v10 risks are concentrated in long
durations between those durable facts. Model calls, in-memory conversation
continuation, tool attempts, prompt compaction, verification freshness, and
provider fallback need typed records before Glassbox can honestly claim
long-running task reliability.

No characterization test was added for this audit because the reviewed behavior
is already covered by existing unit and integration tests listed above. The
follow-on implementation tasks should add focused tests as each weak boundary is
made durable.
