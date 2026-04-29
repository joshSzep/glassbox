# Dashboard Autonomy Console IA

This document is the Phase 88 information architecture baseline for turning the
Glassbox dashboard into an autonomy control room. It builds on the existing
operator console, session inspector, task-plan APIs, workspace-memory APIs,
repository-index APIs, branch-search projections, and budget posture projections
without replacing the session-first debugging affordances already in the
dashboard.

## Console Shape

The first viewport should answer three operator questions without explanation
copy:

- what autonomous work exists now
- what is blocked, stale, failed, or spending budget
- what evidence explains the next safe operator action

Use a dense console frame with three primary regions:

| Region | Purpose | Default Contents |
| --- | --- | --- |
| Navigation rail | Switch between session queues and autonomy surfaces | session queues, task queue, memory, repository index, branch search |
| Work queue pane | Triage rows | filtered task/session/job rows with status, budget, blocker, and freshness chips |
| Inspector pane | Detail and action context | selected task plan, session link, evidence, events, memory/index influence, branch candidates |

Do not nest cards inside cards. Reuse the existing dashboard language of rails,
panes, tabs, tables, compact evidence rows, badges, and inspector sections.
Cards are acceptable for repeated rows or modals, but page sections should stay
unframed or use full-width pane bands.

## Navigation Model

Keep the current session queues as the default landing experience. Add autonomy
surfaces as peers instead of hiding them inside one selected session:

- `Sessions`: existing approvals, questions, failures, degraded, active, and
  historical queues
- `Tasks`: durable task queue with active, blocked, failed, completed,
  background, and historical filters
- `Memory`: workspace-memory entries and candidates
- `Index`: repository intelligence status, search, freshness, and rebuild state
- `Branch Search`: candidate comparisons and selection metadata

Deep links should encode the selected surface, selected row, selected tab, and
queue filter. Existing `?session=SESSION_ID` links must keep opening the
session inspector.

## Task Queue

The task queue is the autonomy console's main triage surface. Rows should show:

- task title and short task ID
- status and blocker reason
- related session link
- current step title or "no current step"
- verification summary
- budget posture, including exhausted limits when present
- last update age and projection freshness
- background-job indicator when a mutating continuation job exists

Task filters:

| Filter | Includes |
| --- | --- |
| Active | proposed, active, paused tasks that can still move |
| Blocked | tasks with `blocked_reason` |
| Failed | failed tasks and failed task verifications |
| Completed | completed tasks |
| Background | tasks with queued, running, paused, failed, stale, or cancellation-requested background jobs |
| Historical | completed, cancelled, abandoned, and tasks from historical sessions |

The selected task inspector should include tabs for `Plan`, `Events`,
`Evidence`, `Budget`, `Branches`, and `Related Session`. Event history remains
paginated and should reuse the existing "load more" pattern.

## Actions

GBX-881 remains read-only. GBX-882 adds controls, and every control must call a
backend API before the dashboard changes authoritative task/job/budget state.

Required controls:

- approve proposed plan
- start bounded continuation
- pause task
- resume task
- cancel task
- cancel background job
- adjust budget within policy

Use confirmations for budget increases, risky mode changes, mutating background
continuation, task cancellation, and job cancellation. Confirmation content must
name what will continue automatically, what still requires operator approval,
and the specific budget or policy reason being changed.

Optimistic UI is allowed only for synchronous API acceptance state. Canonical
task/job/budget state still comes from the next loaded page or live event.

## Memory And Repository Index Inspectors

Memory rows should expose source and freshness before content:

- state: active, stale, invalidated, imported, pruned
- kind and tags
- summary/content preview
- provenance source, session/task/artifact/tool links
- created, confirmed, invalidated, last-used, and use count evidence

Invalidated and pruned memory remains inspectable as historical evidence. The
dashboard should not make memory feel magical; show the source label and
last-confirmed evidence beside the statement being shown.

Repository index rows should expose:

- status: missing, fresh, stale, building, failed
- built time, schema version, builder version, and source digest
- top entity groups by kind
- search results with path, symbol, language, tags, and provenance
- stale or missing warnings before rebuild controls

Index rebuild should become a background job action when the daemon is active.

## Branch-Search Comparison

Branch-search comparison is metadata selection, not merge control. Candidate
rows should show:

- strategy label
- candidate status and selection state
- candidate session link
- verification status and summary
- changed files or artifact-backed diff summary when available
- budget posture and branch-attempt usage
- policy or blocker summary
- residual risks

Selected, rejected, and needs-review actions change candidate metadata only.
Failed and blocked candidates stay visible because they explain discarded
strategies.

## Why-This-Action Evidence

The evidence pane should derive labels from backend evidence, not frontend
guesses. It can group:

- plan step evidence
- policy decisions
- budget decisions and exhausted limits
- memory/index context used in the selected turn or task
- verification results and residual risks
- provider readiness and daemon availability
- human interventions

Use cautious labels:

- `Explained`: backend event evidence directly names the action or refusal
- `Partial`: supporting evidence exists, but causality is incomplete
- `Missing`: the dashboard cannot link the decision to retained evidence
- `Stale`: projection or context freshness makes the evidence advisory

## API Payload Review

Current payload coverage:

| Surface | Existing API/Payload | Frontend Use |
| --- | --- | --- |
| Tasks | `GET /tasks`, `GET /tasks/{task_id}`, `GET /tasks/{task_id}/steps`, `GET /tasks/{task_id}/events` | queue rows, selected plan, verification list, paginated event history |
| Budget | session snapshot and summary `budget_posture` | budget chips and budget evidence; GBX-882 needs mutation APIs |
| Background jobs | aggregate runtime failed/retryable/abandoned counts; repository methods and CLI exist | GBX-882 needs job list/detail/action web APIs before full controls |
| Memory | `GET/POST /memory`, memory candidates confirm/reject, memory detail | inspector rows, candidate review, provenance links |
| Repository index | `GET /repo/index/status`, `GET /repo/index/search`, `GET /repo/index/entries/{entry_id}` | index status, search, entry detail |
| Branch search | projections and CLI query service exist | GBX-884 needs web list/detail/selection APIs |
| Session context | selected session snapshot `runtime_context` | memory/index influence for a selected turn/session |

GBX-881 can use existing task read APIs. GBX-882 and GBX-884 should add web
transport where backend authority already exists only through repository/CLI
interfaces.

## States

Every autonomy surface should define:

| State | Treatment |
| --- | --- |
| Loading | skeleton rows or compact loading pane that preserves layout |
| Empty | state-specific empty message with the current filter name |
| Stale | visible projection or freshness warning; actions disabled when authority is uncertain |
| Blocked | blocker reason and next eligible operator action |
| Failed | failure kind, retryability, and linked evidence |
| Live | live badge with last sequence/updated-at context |
| Reconnecting | retain loaded snapshot, show retry state, avoid clearing rows |
| Historical-only | read-only label; mutation controls disabled with reason |

## Mobile, Keyboard, And Screen Readers

Mobile should use drill-in panes rather than horizontal tables. Queue rows open
one selected inspector; a persistent return target moves back to the current
queue.

Keyboard expectations:

- navigation rail uses normal button/link tab order
- queue rows are focusable with visible focus states
- inspector tabs are reachable after the selected row
- action buttons are grouped after state/evidence summary
- destructive and budget-increasing controls require a modal confirmation
- paginated histories expose a stable "load more" button

Screen-reader expectations:

- each surface has a named region
- selected task, selected memory item, selected index entry, and selected branch
  candidate announce their status and freshness
- evidence groups have accessible names, not only badge color
- disabled actions expose the disabled reason in visible text

The bounded claim for Phase 88 is architectural: implementation tasks must
retain real browser/assistive-technology evidence before stronger accessibility
claims are made.

## Wireframe Notes

Desktop:

```text
+----------------------+------------------------------+-----------------------------+
| status rail          | task queue / comparison table | selected inspector          |
| sessions/tasks/...   | filters + dense rows          | tabs + evidence/actions     |
| memory/index status  | blockers/budgets/freshness    | plan/events/context         |
+----------------------+------------------------------+-----------------------------+
```

Mobile:

```text
+-----------------------------+
| status rail + surface tabs   |
| active filter controls       |
| queue rows                   |
| selected inspector drill-in  |
| return to queue              |
+-----------------------------+
```

## Design Review Checklist

- First viewport supports action triage.
- Existing session inspector tabs and fork/approval/answer affordances remain
  available.
- No card-in-card layout is introduced.
- Tables and dense rows have mobile drill-in behavior.
- Loading, empty, stale, blocked, failed, live, reconnecting, and
  historical-only states are specified before implementation.
- Keyboard path changes are reflected in the accessibility review task.
