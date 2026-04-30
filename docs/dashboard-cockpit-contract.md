# v9 Dashboard Cockpit Contract

For the docs hub and workflow guides, start at [README.md](./README.md). For
current dashboard operation, see [dashboard.md](./dashboard.md). This contract
defines the v9 cockpit target for `GBX-940` and constrains the follow-on
dashboard implementation tasks in [tasks-v9.md](./tasks-v9.md).

## Purpose

The v9 dashboard cockpit is the local operator surface that answers three
questions before it asks the operator to inspect raw detail:

- what needs my attention first?
- why does that state matter?
- what command, dashboard action, or evidence view should I use next?

The cockpit does not become a hosted control plane, a browser-only source of
truth, or a tutorial page. It remains a local, event-sourced console derived
from canonical events, typed API responses, retained artifacts, and explicit
operator documentation.

## Cockpit Surfaces

The cockpit keeps the existing deep inspection views, but it gives each surface
a clearer job.

Workspace overview:

- opens as the default dashboard entry surface
- summarizes runtime owner state, projection health, background-job posture,
  queue counts, and prioritized sessions
- highlights the highest-priority attention item without hiding lower-priority
  queues
- links to the filtered queue, selected session, task queue, memory/index
  surface, branch-search surface, or recovery guidance that explains the state

Active session:

- shows session status, browser stream posture, model, workspace, branch
  context, projection health, pending approval or question, current turn, and
  next action
- keeps transcript, timeline, tools, metrics, policy, event log, and evidence
  panes available as drill-down surfaces
- treats historical snapshots as inspectable records, not broken live sessions

Task queue:

- groups tasks by operator decision state: proposed, approved, running,
  paused, blocked, failed, cancelled, completed, and background-continuation
  posture
- connects task plans, budget posture, stop reasons, verification attempts,
  background jobs, and session links
- keeps task mutation actions behind the same explicit dashboard confirmation
  and backend policy checks used by the current task console

Evidence:

- distinguishes blocking deterministic evidence from advisory evidence,
  missing evidence, stale evidence, and provider evidence
- links from a cue to the relevant event log row, artifact path, transcript
  section, task verification record, or CLI command when available
- leaves replay, eval, release, and provider canary execution to the CLI and
  backend workflows

Memory and repository index:

- summarizes local workspace memory health, invalid or stale memory, repository
  index freshness, rebuild posture, and search availability
- labels memory and repository intelligence as derived local context, not hidden
  authority
- makes refresh and prune actions explicit, policy-checked, and inspectable

Branches:

- surfaces branch-search runs, candidate review posture, selected marks, and
  comparison evidence
- preserves the rule that branch-search candidates do not mutate parent session
  history automatically
- keeps lineage navigation grounded in persisted parent, child, and fork fields

Recovery cues:

- show stale daemon, failed or retryable background jobs, degraded projections,
  stale repository index, artifact pressure, invalid memory, and stale provider
  evidence as read-only guidance first
- prefer command-copy or command-navigation affordances for safe inspection
- require explicit confirmation and backend policy checks before any mutating
  maintenance action is exposed

## Priority Rules

When several states compete for the first attention slot, the cockpit should
choose the first applicable state in this order:

1. Pending approval that blocks a live or resumable turn.
2. Pending `ask_user` question that blocks progress.
3. Failed or retryable task, session, background job, or continuation that has a
   concrete recovery action.
4. Active task or session with exhausted budget, paused state, or explicit stop
   reason requiring operator choice.
5. Degraded or unavailable projections that can make dashboard summaries stale.
6. Runtime owner conflict, stale daemon state, or unavailable live stream for an
   otherwise active session.
7. Stale repository index, invalid memory, artifact pressure, or other derived
   state maintenance cue.
8. Provider credential, compatibility, freshness, warning, or failed advisory
   evidence.
9. Branch-search candidate review or comparison waiting on operator selection.
10. Healthy empty state with no current action needed.

These priority rules are deliberately operator-centered. A stale repository
index or provider warning can be important, but it must not outrank a pending
approval, pending answer, failed task, or projection degradation that can make
the visible cockpit untrustworthy.

## Responsive Expectations

Desktop layout should keep workspace attention and selected-session inspection
visible together where space allows. The left or top attention region owns the
workspace overview, queues, and health summary; the main region owns the active
session, task, memory/index, branch, or evidence view.

Narrow desktop and tablet layouts may stack surfaces, but the queue list,
selected item header, next action, live state, and pending intervention controls
must stay reachable without scanning through long diagnostics.

Mobile layout is single column. The default view shows workspace attention and
queues. Selecting a session, task, memory item, index item, or branch-search
candidate moves to a focused inspector with a clear return path.

Live updates should not cause avoidable layout shifts. Queue rows, rail facts,
badges, buttons, and counters should use constrained dimensions so changing
labels do not push actions out from under the operator.

## Keyboard And Accessibility Expectations

The cockpit must support keyboard operation for:

- refreshing workspace state
- changing queues and dashboard surfaces
- opening a session, task, memory/index entry, or branch-search candidate
- changing inspector tabs
- submitting a prompt, answer, approval, denial, cancellation, fork, task
  continuation, budget adjustment, or safe maintenance request where that
  action exists
- closing dialogs or sheets and returning focus to the invoking control

Focus states must remain visible across live updates. Tab order follows the
visual workflow: workspace attention, queue navigation, selected item header,
primary narrative, actions, then diagnostics. Status indicators must include
text or accessible names and must not rely on color alone. Dialogs and sheets
must use semantic labels, trap focus while open, and restore focus after close.

## Data Source Map

The cockpit may aggregate and rank data in the browser, but the source data
must come from typed local API responses, canonical events, retained artifacts,
or explicit docs.

Workspace overview:

- `GET /sessions/aggregate`
- `SessionAggregateView`
- `WorkspaceRuntimeSummaryView`
- `SessionQueueCountsView`
- `ProjectionHealthCountsView`
- `OperatorSessionSummaryView`
- frontend `createConsoleStore`, `DashboardState`, `WorkspaceOverview`,
  `WorkspaceStatusRail`, `WorkspaceSummary`, and `SessionAttentionRows`

Active session and evidence:

- `GET /sessions/{session_id}`
- `GET /sessions/{session_id}/events`
- `SessionSnapshotView`
- frontend `createSessionStore`, `SessionInspector`, transcript, timeline,
  metrics, runtime, lineage, diagnostics, policy, and evidence panes

Tasks and verification:

- task dashboard routes and typed task detail/page responses
- canonical task-plan, task-step, verification, budget, background-job, and
  stop-reason events
- frontend `createTaskStore` and `TaskAutonomyConsole`

Memory and repository index:

- memory dashboard routes and repository-index dashboard routes
- workspace-memory projections, repository-index status, retained index
  metadata, and background refresh jobs
- frontend `createKnowledgeStore` and `KnowledgeAutonomyConsole`

Branches:

- branch-search dashboard routes and branch-search projection fields
- persisted candidate state, comparison artifacts, and lineage fields
- frontend `createBranchSearchStore` and `BranchSearchConsole`

Recovery and maintenance:

- observability reports, daemon status, background-job projections, projection
  health checks, artifact inspection, provider diagnostics, and documented
  recovery commands
- existing recovery guidance in [recovery-maintenance-review-v8.md](./recovery-maintenance-review-v8.md)

## Follow-On Task Boundaries

`GBX-941` adds the first frontend workspace attention summary model and UI
using this priority order. It is intentionally based on `GET
/sessions/aggregate` and the current runtime/projection/session summary fields;
later provider, repository-index, artifact-pressure, and richer task evidence
cues should extend the same priority ladder rather than introducing a second
competing summary.

`GBX-942` should deepen task and verification evidence drill-down without
copying full event logs into every task surface. `GBX-943` should add read-only
recovery and maintenance cues first, with mutating actions remaining explicit,
confirmed, and backend-policy checked.
