# v10 Long-Run Cockpit Contract

For the docs hub and workflow guides, start at [README.md](./README.md). For
the existing dashboard model, see [dashboard.md](./dashboard.md) and
[dashboard-cockpit-contract.md](./dashboard-cockpit-contract.md). This contract
defines the v10 cockpit target for `GBX-1050` and constrains the long-running
dashboard and terminal tasks that follow in [tasks-v10.md](./tasks-v10.md).

## Purpose

The v10 long-run cockpit is the terminal and dashboard surface that answers
four operator questions during long local work:

- is the agent alive?
- is it still coherent?
- what changed since the last checkpoint?
- what needs the operator now?

The cockpit is not a second source of truth. It is a ranked view over canonical
events, rebuildable projections, retained artifacts, typed API responses, and
documented CLI commands. It must make long-running work easier to inspect
without hiding the raw event log, transcript, artifacts, task plans, replay
evidence, or local policy checks that remain authoritative.

## Surface Contract

Workspace overview:

- shows daemon/runtime ownership, live stream posture, projection health,
  provider evidence, queue counts, and the highest-priority long-run cue
- summarizes active, blocked, stale, failed, and historical work without
  making historical snapshots look like broken live sessions
- links to the selected session, task queue, recovery command, retained
  artifact, or provider evidence that explains the cue

Session inspector:

- keeps the selected session header focused on status, current turn, current
  phase, latest checkpoint, live heartbeat, projection health, and next action
- keeps transcript, timeline, runtime context, metrics, lineage, evidence, and
  actions available as drill-down views
- shows recent tool attempts with status, heartbeat, retry posture, output
  artifact, and confirmed recovery controls when backend policy allows them
- labels historical, imported, stale, or projection-lagged state as inspectable
  evidence rather than live authority

Terminal status:

- `glassbox session status SESSION_ID` remains the compact terminal cockpit for
  a selected session
- prints pending approvals and questions before lower-priority action guidance
- prints latest checkpoint, incomplete-turn posture, recent tool activity,
  recent durable attempts, verification posture, and dashboard URL when present
- names exact follow-up commands for safe inspection before mutating recovery
  commands

Terminal chat and attach:

- keep the conversation surface primary and concise
- surface dashboard URL, active turn/cancellation state, pending approval or
  question, and checkpoint/resume warnings without forcing the operator into
  the dashboard
- preserve command-copy and non-interactive paths for every recovery action
  that the dashboard exposes

Task and verification surfaces:

- show task plan state, checkpoint phase, budget posture, last-known
  verification, stale-verification warnings, and background continuation
  posture
- link verification cues to command output artifacts, task verification events,
  replay or eval evidence, and repair history when available

## Priority Rules

When several long-run states compete for the first cue, terminal and dashboard
surfaces should choose the first applicable state in this order:

1. Pending approval that blocks live or resumable work.
2. Pending `ask_user` question.
3. Explicit cancellation requested, cancellation acknowledgement missing, or
   active turn stuck in a cancellable boundary.
4. Incomplete turn with recoverable, non-resumable, abandoned, or stale
   recovery posture.
5. Stale or failed tool attempt with retained output or safe recovery action.
6. Stale checkpoint, missing checkpoint for long active work, or checkpoint
   approval requirement.
7. Stale, invalidated, or missing compaction that would affect future prompt
   context.
8. Verification failure, stale verification after workspace drift, or missing
   last-known-good evidence for changed work.
9. Budget exhaustion, unattended-duration expiry, scheduled pause, or
   continuation-window expiry.
10. Runtime owner conflict, stale daemon ownership, unavailable live stream, or
    projection lag that can make dashboard summaries stale.
11. Provider degradation, retry recommendation, model fallback recommendation,
    or stale provider canary evidence.
12. Branch-search review, memory/index maintenance, artifact pressure, or other
    derived-state maintenance cue.
13. Healthy active progress, completed work, or historical snapshot with no
    action needed.

These rules are intentionally intervention-first. Provider warnings and derived
maintenance matter, but they must not outrank a blocked live turn, stale tool
attempt, unsafe checkpoint, stale verification, or untrusted projection.

## Data Source Map

Long-run cockpit cues must be derived from explicit local data sources:

- Session state: `GET /sessions/{session_id}`,
  `SessionSnapshotView`, `SessionSummaryView`, canonical session and turn
  events, and `glassbox session status`.
- Long-run status: the `long_run_status` field on session summaries and
  snapshots, derived from canonical events, latest checkpoints, recent
  `ToolAttemptHeartbeat` projection rows, and session metadata.
- Workspace overview: `GET /sessions/aggregate`,
  `WorkspaceRuntimeSummaryView`, queue counts, projection-health counts,
  provider evidence, and `glassbox observability status`.
- Checkpoints: `TaskCheckpointCreated` events, `task_checkpoints` projection,
  `/sessions/{session_id}/checkpoints`, and checkpoint context in runtime
  prompts.
- Compactions: `ContextCompactionCreated`,
  `ContextCompactionFreshnessChanged`, `context_compactions` projection,
  `/sessions/{session_id}/compactions`, and
  `glassbox session compactions|compaction-refresh|compaction-invalidate`.
- Tool attempts: `ToolAttemptHeartbeat`, `RecoveryDecisionRecorded`,
  `tool_attempts` projection, `/sessions/{session_id}/tool-attempts/...`,
  `glassbox session tool-attempts`, and
  `glassbox session tool-attempt inspect|output|retry|abandon`.
- Verification: task verification events, command/test output artifacts,
  verification-loop summaries, replay/eval reports, and future long-run
  verification-ledger projections.
- Budgets: autonomy budget events and projections, task continuation jobs,
  future time-window budget fields, and background job state.
- Provider posture: provider diagnostics, provider canary evidence, capability
  matrix summaries, and future provider recovery events.
- Terminal UI: TUI reducer state, session status formatter output, command
  guide text, and dashboard URL or stream status shown by chat/attach.
- Frontend UI: `createConsoleStore`, `createSessionStore`, `createTaskStore`,
  `WorkspaceOverview`, `SessionInspector`, Actions, Runtime, Timeline,
  Metrics, Evidence, and future long-run cockpit components.

Projections can rank, filter, and summarize, but canonical events and retained
artifacts remain the evidence source when a cue is disputed.

## Recovery Guidance

Cockpit guidance should prefer safe inspection before mutation:

- show `glassbox session status SESSION_ID` before retrying or abandoning work
- show `glassbox session tool-attempt inspect SESSION_ID TOOL_ATTEMPT_ID` and
  `glassbox session tool-attempt output SESSION_ID TOOL_ATTEMPT_ID` before
  retry or abandon
- show `glassbox session compactions SESSION_ID` before refresh or invalidation
- show projection checks before relying on dashboard-only summaries when
  projection health is stale or unavailable
- show provider diagnostics or retained canary evidence before recommending a
  model switch
- show replay/eval or verification commands before claiming repaired work is
  last-known-good

Mutating actions, including retry, abandon, refresh compaction, resume,
continue, pause, approve, deny, cancel, memory prune, and repository index
rebuild, must require explicit operator intent in the dashboard and must keep
backend policy checks authoritative.

## Responsive Expectations

Desktop dashboard layout should keep workspace attention and selected-session
inspection visible together when width allows. The first viewport should expose
live/stale state, next action, checkpoint posture, tool-attempt posture, and
verification or budget warnings before long diagnostics.

Narrow desktop and tablet layouts may stack sections, but the selected item
header, next action, heartbeat/stuck indicator, and pending intervention
controls must stay reachable before transcript or event-log detail.

Mobile layout is a single-column inspector. Queue selection, selected item
header, next action, and confirmed actions remain the primary path; dense
timelines and raw evidence can sit behind tabs.

Terminal layout should degrade cleanly from TUI to plain output. Long labels,
UUIDs, command text, and retry reasons must wrap without hiding the next action
or prompt. Non-interactive commands must remain scriptable and JSON-capable
where existing command families already support JSON output.

Live updates should not cause avoidable layout shifts. Badges, counters, action
buttons, checkpoint summaries, attempt rows, and timeline items should have
stable dimensions or predictable wrapping.

## Keyboard Expectations

Dashboard keyboard operation must cover:

- refresh workspace state
- move between queues and selected items
- open session, task, checkpoint, compaction, artifact, and attempt detail
- change inspector tabs
- approve, deny, answer, cancel, retry, abandon, refresh, resume, pause,
  continue, and fork when those actions are available
- close confirmation dialogs and restore focus to the invoking control

Terminal keyboard operation must cover:

- TUI chat composition and submit
- approval, denial, answer, cancellation, attach, and exit flows
- command palette or equivalent dashboard URL discovery where available
- plain fallback paths for every dashboard recovery action

Focus must remain visible across live updates. Status indicators must include
text or accessible names and must not rely on color alone. Dialogs and sheets
must have semantic labels, trap focus while open, and restore focus when they
close.

## Follow-On Task Boundaries

`GBX-1051` added heartbeat, stuck-state, and progress summaries through the
derived `long_run_status` read model. It uses this contract's priority rules
and data-source map without introducing timeline navigation or broad recovery
guidance.

`GBX-1052` adds checkpoint, compaction, tool-attempt, verification, approval,
question, cancellation, and recovery timeline views. It should point back to
source event ranges and artifacts rather than duplicating the full event log.

`GBX-1053` adds long-run recovery action guidance. It should keep inspection
commands ahead of mutating commands and keep command text aligned with CLI help.
