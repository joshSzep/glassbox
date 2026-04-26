# Operator Console Model

For the docs hub and workflow guides, start at [README.md](./README.md). For
current dashboard usage, see [dashboard.md](./dashboard.md).

## Purpose

This note defines the v2 multi-session operator console model for Glassbox. It
is the design contract for `GBX-320`, the dependency baseline for `GBX-321` and
`GBX-322`, and the product UX baseline for the v3 Next.js SPA migration in
[tasks-v3.md](./tasks-v3.md).

The console should evolve the existing dashboard from a recent-session browser
plus one-session deep link into a workspace operations surface. It should help
an operator answer three questions quickly:

- what needs attention now?
- what is currently live, stale, degraded, or historical?
- where should I inspect or intervene next?

The console remains local-first and event-sourced. It is not a second control
plane, and it must not make browser-local state authoritative.

## Current Implemented Baseline

The current dashboard already provides the shell the console should extend:

- `GET /sessions` returns recent session summaries with status, lineage,
  next-action text, failure detail, pending question or approval identifiers,
  and projection health
- `GET /sessions/{session_id}` returns a full selected-session snapshot with
  transcript, active tool calls, pending approvals, turn metrics, runtime
  context, lineage, branchable turns, and projection health
- `GET /sessions/{session_id}/events?after=...` streams per-session SSE events
  and replays persisted events after a requested sequence
- browser actions already exist for next prompts, `ask_user` answers, approval
  resolution, and session forks
- the frontend is already split into reducer, renderer, transport, controller,
  and DOM-binding modules

The first operator-console implementation should build on these boundaries. It
should not replace the session API with a browser-only aggregation layer.

## Console Principles

The v2 console should follow these rules:

- canonical events and server-side read models remain the source of truth
- the browser may sort, filter, and preserve local drafts, but it may not infer
  authoritative session state that the backend does not expose
- aggregate console data should be built from the existing session summaries,
  snapshots, projection health, and runtime-owner discovery surfaces
- per-session deep links remain stable; the multi-session console is an entry
  layer above the current inspector, not a replacement for it
- live runtime state and historical inspectability must be visibly distinct
- degraded projections are an operational health condition, not session data
  loss

## V3 SPA UX Contract

The v3 SPA should translate the existing operator-console model into a faster,
more legible work surface. It should feel like an operations console for local
agent sessions, not a landing page, documentation site, or generic admin theme.
Opening `/app` during migration should put the operator directly into the
workspace overview and action queues, with selected-session inspection one
click or one deep link away.

The SPA should optimize for four operator behaviors:

- scanning many sessions quickly enough to spot the next required intervention
- distinguishing live, reconnecting, historical, failed, and degraded states
  without reading implementation detail
- acting on prompts, questions, approvals, denials, and forks with clear
  feedback and no hidden local authority
- moving between overview, queue, session, lineage, compare, and drift evidence
  without losing the selected session or mental model

Use Tailwind and shadcn-style primitives to make these flows consistent: tabs
for queues and inspector panes, tables or dense lists for session rows, badges
for status and health, dialogs or sheets for focused actions, tooltips for icon
controls, toasts or inline status for action feedback, and command/menu patterns
only where they shorten frequent operator workflows.

### V3 Surface Brief

The SPA should organize the console around these first-class surfaces.

Workspace overview:

- default first screen for `/app`, never a marketing hero or explanatory splash
- shows runtime-owner state, projection-health totals, queue counts, and recent
  prioritized sessions from `GET /sessions/aggregate`
- highlights the highest-priority next action and the most degraded health
  condition without hiding lower-priority queues
- keeps health and queue summaries clickable so operators can move directly to
  filtered work

Action queues:

- queue tabs cover approvals, questions, failures, degraded sessions, active
  work, historical sessions, and all sessions where useful
- rows show session ID, status, branch label or lineage hint, updated time,
  next-action summary, projection health, and pending approval/question subject
- row ordering follows server priority first and local UI filtering second
- empty states should be compact and operational, confirming there is no current
  work in that queue rather than explaining the product

Session inspector:

- selected-session header shows status, live stream state, projection health,
  model, workspace, branch label or lineage hint, and next action
- transcript remains the central narrative surface for what happened and what is
  happening now
- timeline summarizes turns, model calls, tool calls, suspensions, failures,
  metrics, and forkable boundaries from snapshot and event data
- inspector panes expose current turn, active tools, live output, runtime
  context, working set, approvals, questions, event log, and metrics without
  forcing raw event inspection as the first stop

Runtime health:

- live stream state, runtime ownership, and projection health stay visually
  separate because they describe different failure modes
- degraded projection states should include concise repair direction aligned
  with CLI language, such as checking daemon status or projection health
- a historical snapshot should look inspectable, not broken, when live streaming
  is no longer expected

Approvals and questions:

- pending approvals and `ask_user` questions are action surfaces, not generic
  messages buried in the transcript
- approve, deny, and answer controls stay close to the subject, policy reason,
  and current session state needed to decide safely
- submitted, resolved, conflicted, validation-error, and network-error states
  must be visible and reversible only when the backend actually permits retry

Lineage and compare:

- lineage navigation should show parent, child, and sibling relationships from
  persisted snapshot fields, not transcript similarity
- compare target selection should favor parent and child snapshots first, with
  a clear way back to the selected session
- compare views should show status, branch metadata, transcript differences,
  runtime context, working-set differences, and turn-summary differences where
  available while preserving access to raw transcript and event evidence

Drift and verification cues:

- replay, eval, context-drift, working-set provenance, and artifact-backed cues
  are advisory evidence surfaces, not runtime-health failures by themselves
- the SPA should summarize likely causes and safe artifact references already
  exposed by snapshots/runtime context, while leaving deterministic replay and
  eval execution to the CLI/backend workflows
- missing artifacts or unsupported historical sessions should be clear neutral
  states rather than visually conflated with session failure

### Responsive Layout Contract

Desktop widths should favor simultaneous scanning and inspection. Use a stable
multi-column layout with a workspace/queue column, a selected-session narrative
area, and a diagnostics/action area when space allows. Queue rows, status chips,
and action controls should have fixed or constrained dimensions so live updates
do not cause distracting layout shifts.

Narrow desktop widths should keep two primary regions visible: queue/navigation
and selected-session inspection. Secondary diagnostics can move behind tabs,
collapsible panes, or a sheet, but the transcript, next action, live state, and
pending intervention surfaces remain directly reachable.

Tablet widths should use stacked regions with persistent top-level navigation:
overview or queues first, selected-session header next, then transcript/timeline
and inspector tabs. Approvals, questions, and composer actions should remain
near the selected-session header or in a predictable action area rather than
falling below long diagnostic panes.

Mobile widths should become a single-column console. The default view shows the
workspace overview and queue list; selecting a session moves into a focused
inspector with a clear return path to queues. Transcript, timeline, actions,
lineage, compare, and diagnostics should be reachable through tabs or sheets.
No operator action should require horizontal scrolling or guessing where state
changed after a live update.

### Accessibility And Keyboard Contract

Every high-frequency operator workflow should be reachable without a pointer:
queue selection, session-row opening, inspector tab changes, transcript/timeline
navigation, composer submit, answer submit, approval approve/deny, fork dialog
open/confirm, lineage target selection, compare target selection, and returning
from a selected session to queues.

Expected interaction rules:

- focus states are visible on all interactive controls and survive live rerenders
- tab order follows the visual workflow: overview, queues, selected-session
  header, primary narrative, actions, then diagnostics
- queue tabs and inspector tabs use standard keyboard behavior for tablists
- dialogs and sheets trap focus, restore focus on close, and expose semantic
  labels for destructive or irreversible actions
- submit controls should expose pending/disabled states without removing the
  operator's place in the flow
- status chips and health badges must not rely on color alone; text or accessible
  names carry the state
- reduced-motion preferences should suppress nonessential transitions while
  preserving live-state feedback
- live updates should announce important state changes politely when the browser
  accessibility stack supports it, especially new approvals, questions, failures,
  and stream-state changes

Keyboard shortcuts, if added, should be discoverable through menus or tooltips
and should never be the only way to perform an action.

### Visual Density And Copy

The SPA should be quiet, dense, and work-focused. Use compact typography,
stable row heights, restrained status color, and clear grouping over decorative
cards or oversized hero sections. Cards are appropriate for repeated session
items, dialogs, and focused tools; page sections should read as an application
workspace rather than nested promotional panels.

Copy should help the operator choose the next action. Avoid in-app text that
explains that Glassbox is event-sourced, powered by Next.js, using SSE, or built
from generated types. Those are implementation facts for docs and debugging, not
primary UI content. In the UI, prefer operator language such as `live`,
`reconnecting`, `historical snapshot`, `awaiting approval`, `awaiting answer`,
`projection degraded`, `fork available`, and `compare with parent`.

The visual hierarchy should put active interventions before passive diagnostics:
pending approvals/questions and failed/degraded states outrank raw event logs,
metric tables, and historical artifact detail. Raw evidence must remain
available, but it should not crowd out the immediate operator decision.

## Information Architecture

The first console should organize the dashboard into these operator surfaces.

### Workspace Overview

The overview is the default landing view for `/`. It should summarize the
workspace, not market the product. Its primary content is:

- runtime-owner state when available: running, stopped, stale, unavailable, or
  historical-only
- projection health totals: ok, stale, unavailable, and missing snapshot data
- queue counts for pending approvals, pending `ask_user` questions, failed
  sessions, running sessions, and degraded sessions
- recently updated sessions ordered by operator priority rather than only by
  recency

The overview should link directly to filtered queues and selected sessions.

### Action Queues

Action queues are filtered session lists for operator work. The initial queues
should be:

- approvals: sessions with one or more pending approvals
- questions: sessions awaiting an `ask_user` answer
- failures: failed sessions, ordered newest first with retryability and failure
  summaries visible
- degraded: sessions whose projection health is stale or unavailable
- active: running or live-attachable sessions

Each queue row should be concise enough to scan. It should include session ID,
status, branch label or lineage hint, updated time, next-action summary,
projection-health state, and the most relevant pending subject or question.

### Session Inspector

The selected-session inspector remains the existing deep-link experience. It
continues to own transcript inspection, turn metrics, current turn state, active
tool calls, approvals, live output, runtime context, event log, branchable turns,
and lineage navigation.

The console may add richer timeline and comparison affordances later, but it
should not remove any raw evidence from the inspector.

### Health And Runtime Panel

The console needs a compact health panel that uses the same language as CLI
status and daemon status:

- live session: a healthy runtime can still stream or accept live actions
- reconnecting: the browser snapshot is valid while the SSE tail retries
- live unavailable: persisted state is readable but the live stream is not
  established
- historical snapshot: the session is no longer expected to emit events
- runtime-owned: a healthy workspace daemon owns the session runtime
- historical-only: no healthy owner is available; the session is inspectable
  from persisted state
- projection degraded: canonical events remain authoritative, but derived tables
  should be checked or rebuilt

The panel should point operators to the same repair commands used elsewhere,
such as `glassbox daemon status` and `glassbox projection check`.

## Priority Model

When many sessions exist, the console should prioritize sessions by operator
attention, then by recency.

The initial ordering should be:

1. pending approvals
2. pending `ask_user` questions
3. failed sessions
4. projection-degraded sessions
5. running sessions with active turns
6. idle running sessions that can accept the next prompt
7. recently completed, cancelled, or historical sessions

Within each group, newer `updated_at` values sort first. Ties may use session ID
for deterministic ordering.

This model should be implemented server-side in `GBX-321` once aggregate read
models exist. The browser can keep local filters and tabs, but it should not be
the only owner of the priority contract.

## Live Versus Historical Semantics

The console should separate three concepts that are easy to blur:

- persisted truth: canonical events and rebuildable projections from SQLite
- runtime availability: whether a foreground or daemon runtime can accept or
  stream live work for the workspace
- browser stream state: whether this specific browser has an active SSE tail

A completed or failed session can be perfectly healthy as a historical snapshot.
An idle session may be actionable only when a compatible runtime owner can
accept mutation. A degraded projection should still allow the UI to explain that
canonical events are intact and that rebuild is the correct repair path.

Console copy, chips, and queue labels should use these terms consistently with
[dashboard.md](./dashboard.md), [persistent-runtime.md](./persistent-runtime.md),
and CLI status output.

## Backend Contract For GBX-321

`GBX-321` should introduce a small aggregate read model rather than forcing the
browser to fetch every session snapshot. The model should be derived from the
same repository and query-service boundaries that already back `/sessions`.

The first aggregate response should be able to answer:

- counts by queue and health state
- prioritized session rows with enough fields for queue rendering
- runtime-owner summary for the selected workspace when available
- whether each row is live-actionable, historical-only, or degraded

The first backend slice exposes this as `GET /sessions/aggregate`, with small
query parameters for queue, status, sort, and limit so the browser can hydrate
overview and queue surfaces without fetching every session snapshot.

The aggregate read path may reuse current `SessionSummaryView` fields where they
are sufficient. It should add only the missing fields needed to avoid opening
every session individually for triage.

## Frontend Contract For GBX-322

`GBX-322` should keep the existing frontend boundaries:

- reducer modules own selected queue, filter, and session-selection state
- renderer modules own overview, queue rows, health panel, and selected-session
  panes as pure HTML generation
- transport modules own aggregate/session fetches and per-session SSE setup
- the dashboard controller owns URL sync, queue selection, snapshot loading,
  reconnect behavior, and action orchestration
- DOM binding stays in the dashboard DOM layer

The first implementation should preserve direct `?session=...` links. Queue and
filter URL state can be added, but a session deep link must remain enough to
open the inspector.

The first frontend slice now uses `GET /sessions/aggregate` for the root
dashboard shell, rendering:

- a workspace overview with runtime-owner and projection-health summaries
- queue tabs for approvals, questions, failures, degraded sessions, and active work
- prioritized session cards that preserve direct `?session=...` inspection links
- a timeline-oriented turn pane that stays grounded in snapshot metrics and the
  existing SSE/event-log stream rather than browser-only inferred state

The next console slice for `GBX-323` builds on the same boundaries by fetching a
second `GET /sessions/{session_id}` snapshot only when the operator requests a
lineage comparison. The browser now supports:

- parent or child snapshot comparison from the selected-session lineage navigator
- compare summaries anchored in persisted lineage fields, branch source metadata,
  transcript deltas, and snapshot-backed forkability state
- replay or eval drift cues rendered from artifact-backed runtime-context
  summaries when the selected or compared snapshot already carries that evidence

## Non-Goals For The First Console Slice

The first v2 console should not:

- introduce a cloud or remote orchestration model
- replace per-session SSE with a new browser-owned event bus
- require a JavaScript framework migration
- hide raw event, transcript, tool, approval, or metric detail behind summaries
- make replay or eval baselines part of the workspace recovery/health model
- add browser-only analytics tables when existing projections can support the
  needed reads

## Manual Validation Checklist

Before implementing `GBX-321` or `GBX-322`, validate the design against the
current product behavior:

- the root dashboard can still operate as a recent-session browser
- a direct `?session=...` URL can still open one persisted session
- pending approvals, questions, failures, projection health, lineage, and
  next-action summaries are already available in current summary or snapshot
  payloads
- live, reconnecting, unavailable, and historical browser states still map to
  the existing SSE lifecycle
- daemon health and runtime ownership remain separate from canonical session
  truth

For the v3 SPA UX, validate the layout, interaction model, and copy against a
representative set of sessions before treating the design foundation as ready:

- a live running session with active model or tool output
- a historical completed session with no expected live stream
- a failed session with retryability and failure summary visible
- a session awaiting approval with approve and deny actions available
- a session awaiting an `ask_user` answer
- a branched session with parent, child, fork point, and compare target evidence
- a projection-degraded session where canonical event history remains readable
- a snapshot carrying replay, eval, or context-drift artifact cues

For each case, check desktop, narrow desktop, tablet, and mobile layouts; pointer
and keyboard navigation; visible focus; action pending/error states; and whether
the first visible copy helps the operator decide what to inspect or do next.
