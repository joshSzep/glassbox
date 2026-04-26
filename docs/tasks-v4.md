# Glassbox v4 Tasks

For the docs hub and operator guides, start at [README.md](./README.md). This file is the v4 task graph for turning the completed TypeScript SPA into a genuinely excellent operator console.

## Purpose

This document defines Glassbox v4: the UX-focused evolution after the v3 dashboard migration in [tasks-v3.md](./tasks-v3.md).

It is written in the same execution style as [tasks-v1.md](./tasks-v1.md), [tasks-v2.md](./tasks-v2.md), and [tasks-v3.md](./tasks-v3.md): explicit dependencies, small vertical slices, concrete deliverables, and quality requirements attached directly to the work.

The v3 migration successfully moved the dashboard from hand-rolled browser assets to a TypeScript, Next.js, Tailwind, Zustand, shadcn-style SPA served by FastAPI. That migration established the right technical foundation, but the product experience is still too mechanically complete and not yet good enough as an operator surface.

The v4 goal is to make the dashboard feel like a calm, fast, local operations console for agent sessions. It should help an operator understand what needs attention, inspect the right evidence, and intervene with confidence.

## Product Direction

The frontend UX work should optimize for six outcomes:

- a first-screen attention model that tells operators what needs action now
- a selected-session inspector that prioritizes narrative, action, and evidence instead of rendering every pane at once
- a transcript and timeline experience that makes the current session story readable under live updates
- a responsive layout that works as a real console on desktop and a focused drill-in workflow on mobile
- a design system that is dense, restrained, accessible, and visibly operational rather than generic or decorative
- a living screenshot archive that makes UX regressions and improvements reviewable across representative states

The v4 thesis is:

- keep the v3 SPA stack and FastAPI static-serving model
- keep canonical events, backend snapshots, and generated API contracts as the source of truth
- keep the dashboard local-first and operator-focused
- treat UX hierarchy as product behavior, not polish
- expose raw evidence without letting raw evidence crowd out the next operator decision
- improve the shipped SPA incrementally through tested vertical slices

## Current Baseline Before V4 Execution

Treat the following as the starting point for every task in this document:

- the Next.js SPA is the default dashboard route after the v3 migration
- FastAPI still owns the runtime, API, SSE, static asset serving, and production dashboard delivery
- `frontend/components/console/workspace-overview.tsx` renders a workspace summary, queue navigation, queue table, and selected-session inspector slot
- `frontend/components/console/session-inspector.tsx` renders selected-session header, tabs, actions, transcript, lineage, compare, runtime, verification cues, metrics, and event evidence
- `frontend/components/console/session-inspector/tabs.tsx` renders inspector tab links, but tab selection currently does not meaningfully gate inspector content
- `frontend/components/console/session-inspector/actions.tsx` exposes prompt, answer, approval, and fork controls, but the action hierarchy does not yet prioritize the most urgent intervention
- v3 validation already includes Vitest component tests and Playwright coverage for core operator workflows
- [operator-console.md](./operator-console.md) remains the product baseline, but this task graph supersedes the v3 implementation shape where the current SPA falls short of that baseline
- [dashboard-parity.md](./dashboard-parity.md) remains useful for behavioral coverage, but parity is no longer the standard for success; v4 should improve the operator experience beyond legacy equivalence

## Phase 49 Screenshot Review Findings

The first regenerated v4 archive after Phase 49 produced 22 desktop and mobile screenshots across the required scenarios. Treat these findings as evidence that should steer the next implementation slices:

- screenshot captures currently include the Next.js dev overlay badge in the lower-left corner, and that badge covers real content on mobile queue screenshots
- mobile queue tables keep desktop columns, causing `NEXT ACTION` text to be clipped in all queue-heavy mobile states
- selected-session pages expose nearly every inspector surface at once, producing very tall mobile pages and noisy desktop grids even though tabs are visible
- pending approvals and questions are present but compete with generic prompt and fork controls instead of becoming the primary command surface
- compare, runtime context, verification cues, metrics, and event evidence are available but buried in the default overview rather than intentionally requested
- status semantics are visually noisy: runtime owner, browser stream posture, projection health, queue counts, degraded counts, and session status all appear with similar weight
- artifact-backed drift cues are useful but visually heavy; advisory drift can read like a runtime failure, long paths wrap poorly, and copy can run together in evidence rows
- empty workspace screenshots are understandable, but the same card-heavy scaffolding makes the calm state feel less deliberate than it could

## Agent Execution Rules

These rules apply to every task in this file.

1. Respect dependency order. Do not start a task until its dependencies are complete unless the task explicitly says it can proceed in parallel.
2. Preserve the event-sourced source-of-truth rule. Browser state remains derived from backend snapshots, SSE events, and local UI drafts only.
3. Preserve FastAPI as the production runtime owner. Next.js remains a static-exported SPA in production.
4. Treat UX hierarchy as functional behavior. If a change alters what the operator notices first, what action is easiest, or what evidence is visible by default, cover it with tests and docs where practical.
5. Maintain the v4 screenshot archive as the UX changes. Any task that materially changes layout, hierarchy, copy, responsive behavior, action feedback, or visual state should refresh the relevant screenshots or document why the archive does not need an update.
6. Prefer small vertical slices that improve the live console immediately over broad redesign branches.
7. Do not add browser-only state or hidden heuristics that contradict backend session status, projection health, runtime ownership, approval semantics, fork semantics, or replay/eval evidence.
8. Keep raw transcript, event, metric, approval, question, tool-call, lineage, and runtime-context evidence available even when moving it behind tabs, sheets, or progressive disclosure.
9. If the UX redesign exposes an API mismatch, fix the API contract or document the mismatch before encoding fragile browser-only workarounds.
10. Every implementation task automatically includes:
    - automated tests for new behavior
    - `pnpm` lint, typecheck, unit test, and build compliance for touched frontend code
    - Playwright coverage for changed critical browser workflows when the behavior is user-visible and end-to-end
    - `ruff` formatting and lint compliance for touched Python code
    - `ty` typecheck compliance for touched Python code
    - documentation updates when contracts, routes, packaging, workflows, or operator-visible behavior change

## Completion Contract For Any Task

A task is complete only when all of the following are true:

- the implementation exists in the intended module boundary
- automated tests covering the new behavior exist and pass
- frontend lint, typecheck, unit tests, and build pass for touched frontend code
- Python lint, typecheck, and tests pass for touched backend code
- the task does not leave placeholder code or hidden follow-up work outside this file
- the dashboard remains usable through the FastAPI-served production build path
- the v4 screenshot archive is refreshed or explicitly marked unchanged when the task changes visible UX
- docs are updated if the task changes persistence, transport, operator-visible behavior, frontend build workflows, verification workflows, or the user-facing console model

## Suggested Status Markers

If an agent updates this document later, use one of these markers next to task IDs:

- `TODO`
- `IN_PROGRESS`
- `BLOCKED`
- `DONE`

## Expected Repository Targets

These are the main implementation areas referenced below:

```text
frontend/
    app/
    components/
        console/
        ui/
    design-system/
    lib/
    routing/
    state/
    stores/
    styles/
    test-results/v4-audit-screenshots/
    tests/
    e2e/
src/glassbox/web/
tests/
docs/
```

## Recommended Validation Commands

Use the narrowest viable validation after each task, but the baseline validation pattern for completed frontend UX work should include:

```bash
pnpm --dir frontend lint
pnpm --dir frontend typecheck
pnpm --dir frontend test
pnpm --dir frontend build
pnpm --dir frontend test:e2e
pnpm --dir frontend screenshots:v4-audit
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run pytest
```

During incremental implementation, use narrower commands where possible:

```bash
pnpm --dir frontend test -- session-inspector
pnpm --dir frontend test -- workspace-overview
pnpm --dir frontend test -- operator-actions
pnpm --dir frontend typecheck
pnpm --dir frontend test:e2e -- operator-workflows
pnpm --dir frontend screenshots:v4-audit -- --scenario pending-question
uv run pytest tests/integration/test_specific_web_flow.py
uv run ruff check src/glassbox/web tests/integration/test_specific_web_flow.py
```

## Milestone Map

The intended v4 milestone order is:

1. screenshot archive harness, capture hygiene, and current-SPA visual baseline
2. UX audit, evidence capture, and v4 interaction contract
3. attention-first workspace shell and queue redesign
4. real inspector tabs, overview hierarchy, and priority action surfaces
5. turn-grouped transcript, live narrative, and progressive evidence disclosure
6. lineage, compare, drift, and verification UX refinement
7. accessibility, responsive behavior, visual QA, and v4 release gate

## Task Graph

---

## Phase 49: Screenshot Archive And Visual Baseline

### GBX-490: Define The v4 Screenshot Archive Harness

- Status: `DONE`
- Depends on: `GBX-473`
- Goal: create a repeatable Playwright-driven screenshot archive path for auditing the current SPA and tracking UX changes through v4
- Deliverables:
  - repository script such as `pnpm --dir frontend screenshots:v4-audit`
  - deterministic Playwright screenshot harness that can load fixture-backed SPA states without live provider calls
  - output convention such as `frontend/test-results/v4-audit-screenshots/`
  - archive manifest or index describing scenario name, viewport, route, fixture, timestamp or git revision, and short operator state
  - gitignore or retention policy that makes generated screenshot archives available locally without committing large binary churn by default
- Implementation notes:
  - treat screenshots as audit artifacts first, not as strict visual regression baselines
  - use the existing Playwright setup and mocked FastAPI route fixtures where possible
  - keep scenario names stable so before/after archives are easy to compare during review
  - include desktop and mobile viewport definitions from the start
- Tests and validation included in task:
  - screenshot command runs successfully against at least one desktop and one mobile scenario
  - generated manifest can be reviewed without opening every image manually
  - `pnpm --dir frontend test:e2e` still passes after adding the harness
- Done when:
  - contributors can generate a local screenshot archive of the SPA through one documented command

### GBX-491: Capture The Current v3 SPA Visual Baseline

- Status: `DONE`
- Depends on: `GBX-490`
- Goal: archive the current completed-SPA UX before v4 redesign work changes the interface
- Deliverables:
  - baseline screenshot archive for empty workspace, all queues, live session, historical session, failed session, pending approval, pending question, branched session, compare view, projection degraded, and artifact-backed drift cue
  - desktop and mobile captures for the highest-value scenarios
  - short baseline review notes calling out obvious hierarchy, density, overflow, tab, action, and mobile issues visible in the archive
  - documented command and output path for regenerating the baseline
- Implementation notes:
  - this task should capture the current UX honestly rather than fixing it first
  - prefer deterministic fixtures so baseline screenshots can be regenerated on another machine
  - do not commit screenshot binaries unless the repository deliberately chooses a reviewed artifact retention path
- Tests and validation included in task:
  - `pnpm --dir frontend screenshots:v4-audit`
  - manual review that every required scenario produced a nonblank, correctly routed screenshot
  - mobile capture review for horizontal overflow and inaccessible action placement
- Done when:
  - the project has a current-SPA visual baseline that can anchor the v4 UX audit and later before/after review

### GBX-492: Define Screenshot Archive Maintenance Rules

- Status: `DONE`
- Depends on: `GBX-491`
- Goal: make screenshot updates part of v4 execution rather than a one-time audit artifact
- Deliverables:
  - documentation for when to refresh the archive during UX tasks
  - naming conventions for scenario, route, viewport, and before/after captures
  - review checklist for comparing current screenshots against the v3 baseline and the latest v4 state
  - guidance for when screenshot diffs should block a task versus remain manual review evidence
  - policy for storing archives locally, attaching them to PRs, or publishing them as CI artifacts if CI later supports it
- Implementation notes:
  - require archive refresh for visible hierarchy, layout, copy, responsive, action, tab, and evidence-surface changes
  - allow no-op notes for pure state-model, transport, or backend tasks that do not change rendered UX
  - keep binary artifact churn out of normal source commits unless an explicit release artifact path is chosen
- Tests and validation included in task:
  - doc review against the v4 task graph
  - dry-run screenshot archive regeneration after one harmless fixture or route selection change
- Done when:
  - every later v4 task has a clear expectation for keeping visual evidence current

### GBX-493: Remove Dev-Only Chrome From Screenshot Captures

- Status: `DONE`
- Depends on: `GBX-492`
- Goal: keep the v4 screenshot archive focused on the product UI rather than Next.js development overlays or tooling chrome
- Deliverables:
  - screenshot harness update that hides or disables the Next.js dev overlay badge during archive generation
  - capture hygiene check that fails or warns when known dev-only overlay elements are visible in desktop or mobile screenshots
  - regenerated focused screenshots proving the lower-left mobile content is no longer obscured
  - documentation note in the screenshot archive guide explaining that captures should contain only operator-console UI and fixture data
- Implementation notes:
  - prefer an explicit Playwright or Next.js test-environment setting over broad CSS that could hide real console content
  - do not weaken the app itself just to clean screenshots; keep this scoped to audit capture execution
  - the mobile Historical queue label was visibly covered by the dev overlay in the initial archive review, so include a narrow viewport sanity check
- Tests and validation included in task:
  - `pnpm --dir frontend screenshots:v4-audit -- --scenario all-queues`
  - at least one assertion or manual checklist item proving known dev-overlay selectors are absent from captures
  - visual review of one desktop and one mobile queue screenshot after the cleanup
- Done when:
  - generated v4 screenshots show only the intended console UI, with no dev overlay covering queue labels or content

---

## Phase 50: UX Audit And Interaction Contract

### GBX-500: Audit The Completed SPA Against Operator Workflows

- Status: `DONE`
- Depends on: `GBX-493`
- Goal: establish a concrete, code-aligned UX baseline for the current SPA before redesign work begins
- Deliverables:
  - UX audit document covering workspace overview, queues, selected-session inspector, actions, transcript, timeline, lineage, compare, runtime context, evidence, and mobile behavior, annotated against the screenshot archive
  - screenshot archive references or Playwright trace links for representative states: empty workspace, live session, historical session, failed session, pending approval, pending question, branched session, projection degraded, and artifact-backed drift cue
  - issue inventory grouped by severity: workflow blocker, high-friction hierarchy issue, accessibility problem, responsive layout problem, visual polish issue, and copy issue
  - explicit coverage of the Phase 49 findings: mobile table clipping, overly tall selected-session stacks, decorative tabs, action hierarchy conflicts, noisy status semantics, buried compare/evidence surfaces, and artifact-drift copy or wrapping problems
  - explicit list of already-good v3 surfaces that should be preserved during redesign
- Implementation notes:
  - inspect the shipped SPA as an operator, not only as a component tree
  - verify whether inspector tabs control content, whether the first visible action matches the highest-priority backend state, and whether mobile users can act without horizontal scrolling
  - treat the current mobile `NEXT ACTION` clipping as a concrete responsive defect, not a visual-polish note
  - treat the selected-session overview's all-panels-at-once rendering as a core interaction-model failure to be solved by later tab and overview tasks
  - use realistic fixture data, not only the happy-path Playwright fixture
  - treat screenshots as evidence for decision-making, not as permanent visual golden tests unless the repository deliberately chooses that path
- Tests and validation included in task:
  - Playwright smoke run against representative fixtures
  - `pnpm --dir frontend screenshots:v4-audit`
  - manual desktop and mobile review notes added to docs
  - no production code changes are required unless a trivial instrumentation gap blocks the audit
- Done when:
  - implementers have a specific, evidence-backed list of UX problems to solve and preserved behaviors to protect

### GBX-501: Define The v4 Operator Console Interaction Model

- Status: `DONE`
- Depends on: `GBX-500`
- Goal: convert the UX audit into a concrete interaction contract for the v4 redesign
- Deliverables:
  - documentation update defining the v4 console model: attention rail, session narrative, action rail, and evidence surfaces
  - desktop, narrow desktop, tablet, and mobile layout rules
  - explicit mobile rule that queue/session summaries become stacked attention rows rather than clipped desktop tables
  - tab and route-state contract for selected-session inspection
  - action-priority rules for approvals, questions, failures, prompts, forks, lineage, compare, and evidence
  - status hierarchy rules that distinguish runtime owner, browser stream posture, projection health, session status, queue urgency, and verification evidence without giving every badge the same weight
  - copy guidance for status, health, empty states, action feedback, and evidence labels
  - screenshot review rubric mapping each v4 surface to the archive scenarios that should prove it visually
- Implementation notes:
  - use [operator-console.md](./operator-console.md) as the product baseline, but update it where v4 clarifies or improves the model
  - define behavior in terms of operator decisions: what needs attention, what evidence is needed, and what action is safe
  - separate session status, browser stream state, runtime-owner state, and projection health in the interaction model
  - keep the model compatible with existing generated API types unless the audit proves a backend field is missing
- Tests and validation included in task:
  - doc review against current route model, store state, SSE lifecycle, and component boundaries
  - manual validation that the proposed IA does not require production Node or browser-owned canonical state
- Done when:
  - the repo has a clear v4 UX contract that future implementation tasks can execute without guessing layout or priority rules

### GBX-502: Define v4 Fixture And Scenario Coverage

- Status: `DONE`
- Depends on: `GBX-500`, `GBX-501`
- Goal: make representative UX states easy to test, review, and keep stable while the redesign lands
- Deliverables:
  - frontend fixture inventory for live, historical, failed, approval, question, branched, degraded, drift, and large-transcript sessions
  - shared fixture builders or scenario helpers for component tests and Playwright tests
  - documented scenario names and expected operator decision for each scenario
  - mapping from scenario names to screenshot archive captures and critical viewports
  - mobile overflow expectations for every scenario that renders queue rows, action cards, compare summaries, runtime context, or artifact evidence
  - fixture guidance that prevents generated API contract drift
- Implementation notes:
  - extend existing `frontend/tests/fixtures/session-state.ts` rather than creating unrelated fixture systems unless the current helper structure is insufficient
  - keep fixture payloads realistic but small enough to maintain
  - include at least one noisy scenario with approvals, tool calls, live output, runtime notes, and artifact cues so hierarchy can be tested under stress
- Tests and validation included in task:
  - unit tests proving fixture builders hydrate through the real reducer path
  - typecheck against generated OpenAPI types
  - Playwright route fixtures updated to cover at least one urgent-action and one evidence-heavy scenario
- Done when:
  - v4 implementation work can rely on reusable scenarios instead of ad hoc fixture payloads in every test

---

## Phase 51: Attention-First Workspace Shell And Queues

### GBX-510: Build The Workspace Status Rail And Console Frame

- Status: `DONE`
- Depends on: `GBX-501`, `GBX-502`, `GBX-492`
- Goal: replace the generic page header and scattered status badges with a stable operational frame
- Deliverables:
  - top-level status rail showing runtime owner, projection health, stream posture where relevant, workspace identity, and last refresh state
  - console frame that reserves clear regions for attention queues, selected-session narrative, and action or evidence surfaces
  - route-aware selected-session and queue state shown without burying the active context in a table row
  - status hierarchy that reduces repeated badge noise from the baseline screenshots and makes the current operator risk obvious
  - compact refresh and recovery affordances aligned with existing backend health semantics
  - refreshed screenshot archive captures for the workspace shell in desktop and mobile viewports
- Implementation notes:
  - do not turn the top rail into a decorative hero or marketing header
  - visually separate runtime owner, projection health, and browser stream state because they describe different failure modes
  - preserve current FastAPI/static production serving behavior
  - avoid layout shifts when counts, status labels, or live states update
- Tests and validation included in task:
  - component tests for status rail states: online, offline, degraded, stale projection, missing projection, loading, and failed aggregate
  - responsive rendering tests where practical
  - screenshot archive refresh for workspace shell and status rail scenarios
  - Playwright smoke check that `/`, `/app`, selected-session deep links, and queue links still load the console frame
- Done when:
  - opening the dashboard immediately communicates workspace health and current console context without relying on scattered badges

### GBX-511: Replace The Queue Table With Dense Attention Rows

- Status: `TODO`
- Depends on: `GBX-510`
- Goal: make the workspace overview a triage surface instead of a generic data table
- Deliverables:
  - attention-row component for session summaries
  - rows that emphasize the next operator decision over the raw session ID
  - row metadata for session ID, status, live or historical posture, projection health, model, branch or lineage hint, updated time, and actionability
  - responsive row layout that preserves full next-action text at 390px wide without horizontal scrolling or clipping
  - compact empty, loading, stale, and degraded states for each queue
  - click and keyboard behavior that preserves direct session deep links
  - refreshed screenshot archive captures for attention rows across approval, question, failed, degraded, active, and historical queues
- Implementation notes:
  - keep server-side priority ordering from `GET /sessions/aggregate` authoritative
  - do not hide session IDs, but avoid making them the only readable label when better action or message text exists
  - approvals and questions should show the pending subject or question text in the row when available
  - failures should show the failure summary and retryability when available
  - degraded rows should distinguish projection health from session failure
- Tests and validation included in task:
  - component tests for each queue row type and empty state
  - store and route tests proving queue selection and selected-session navigation still round trip
  - screenshot archive comparison against the v3 queue table baseline
  - mobile screenshot review proving `NEXT ACTION` content is not clipped in all-queues, approvals, questions, failures, degraded, active, and historical states
  - Playwright test for browsing from an urgent queue row into the selected-session inspector
- Done when:
  - an operator can scan the queue list and understand why each row deserves attention without opening every session

### GBX-512: Add Queue-Level Priority Summaries And Filters

- Status: `TODO`
- Depends on: `GBX-511`
- Goal: help operators move between urgent work, active sessions, degraded sessions, and history without reading every row
- Deliverables:
  - queue summary strip or side rail with counts, highest-priority reason, and degraded-state cues
  - queue filter controls for all, approvals, questions, failures, degraded, active, and historical sessions
  - optional lightweight text filtering only if it can be implemented without undermining server priority semantics
  - persistent readable URL state for queue and selected session
  - refreshed screenshot archive captures for queue summaries, selected filters, and no-result states
- Implementation notes:
  - do not invent browser-only queue categories that conflict with backend queue memberships
  - keep filtering local and transparent; the operator should understand whether a row is hidden by queue, search text, or server result limit
  - avoid putting high-priority counts in visually weak positions
- Tests and validation included in task:
  - component tests for queue counts and selected queue affordances
  - route tests for queue URL state
  - screenshot archive refresh for queue summary and filter scenarios
  - Playwright coverage for switching queues and returning to the selected session
- Done when:
  - queue navigation feels like an attention model rather than a static list of tabs

### GBX-513: Implement Mobile Drill-In Navigation For Queues And Sessions

- Status: `TODO`
- Depends on: `GBX-511`, `GBX-512`
- Goal: make the SPA usable on narrow viewports as a focused workflow rather than a squeezed desktop layout
- Deliverables:
  - mobile route behavior that starts with workspace queues and drills into the selected-session inspector
  - clear return path from selected session to queues
  - mobile-safe action, tab, and transcript layouts without horizontal scrolling
  - selected-session mobile layout that avoids repeating the full workspace summary, queue list, table, metadata, tabs, all action controls, transcript, lineage, compare, runtime, verification, metrics, and event evidence as one uninterrupted stack
  - stable controls for refresh, queue selection, and selected-session context
  - refreshed screenshot archive captures for mobile overview, mobile selected session, and mobile return-to-queues states
- Implementation notes:
  - desktop can keep simultaneous queue and inspector visibility; mobile should prioritize one task at a time
  - no operator action should require guessing where state changed after live updates
  - maintain direct deep-link support for `?session=...` and `/sessions/{session_id}` routes
- Tests and validation included in task:
  - Playwright mobile viewport tests for queue browsing, selected-session opening, return to queues, answer submission, approval resolution, and fork dialog access
  - component tests for mobile-only affordances where practical
  - screenshot archive review for mobile overflow and visible action placement
  - manual validation on at least one narrow viewport around 390px wide
- Done when:
  - mobile users can triage, inspect, and act without horizontal scrolling or losing navigation context

---

## Phase 52: Real Inspector Tabs, Overview, And Priority Actions

### GBX-520: Make Inspector Tabs Gate Actual Content

- Status: `TODO`
- Depends on: `GBX-501`, `GBX-502`, `GBX-492`
- Goal: turn inspector tabs from decorative route state into the primary mechanism for progressive disclosure
- Deliverables:
  - tab content mapping for overview, transcript, timeline, actions, lineage, compare, runtime, metrics, and events or evidence
  - route-aware rendering that shows only the active tab's primary content plus any always-visible session header or action rail required by the layout
  - preserved direct links for every inspector tab
  - refreshed screenshot archive captures showing active tab content and hidden diagnostics across desktop and mobile
  - tests proving tab selection changes visible content and hidden tabs do not crowd the overview
- Implementation notes:
  - avoid rendering every pane in a grid by default
  - baseline screenshots show the overview rendering transcript, lineage, compare, actions, runtime, verification, metrics, and event evidence together; this task must remove that all-panels-at-once behavior
  - keep high-priority pending actions visible on overview even when the full actions tab is not active
  - preserve accessibility semantics for tablists and tab panels
  - ensure hidden tab content does not steal focus or trigger unnecessary layout work
- Tests and validation included in task:
  - component tests for each tab's visible and hidden content
  - route tests for tab URL round trips
  - screenshot archive comparison proving the overview is no longer crowded by every pane
  - Playwright test for navigating directly to a session tab URL
- Done when:
  - inspector navigation reliably reduces cognitive load instead of adding visual chrome

### GBX-521: Build A Selected-Session Overview Tab

- Status: `TODO`
- Depends on: `GBX-520`
- Goal: make the default selected-session view answer what happened, what is live now, and what needs action next
- Deliverables:
  - overview tab with concise session status, live-state, projection-health, runtime-owner, model, workspace, and lineage summary
  - next-action block that prioritizes approval, question, failure, active tool call, live turn, promptability, forkability, and historical inspection in that order
  - transcript preview centered on the latest meaningful turn or pending action
  - compact compare, verification, runtime, and evidence summaries only when they directly change the next operator decision
  - compact health explanation when projection, runtime, or stream state is degraded
  - refreshed screenshot archive captures for selected-session overview states across approval, question, failed, active, historical, and degraded sessions
- Implementation notes:
  - do not show empty compare, metrics, event, or artifact panels in the default overview unless they contain urgent evidence
  - do not let evidence-heavy states push the primary next action below generic composer or fork controls
  - use operator language such as `awaiting approval`, `awaiting answer`, `historical snapshot`, `projection degraded`, and `live stream reconnecting`
  - keep raw evidence one click away through the relevant tab
- Tests and validation included in task:
  - component tests for overview priority across approval, question, failed, active, historical, and degraded sessions
  - snapshot hydration tests only if new derived UI helpers are introduced
  - screenshot archive refresh for selected-session overview scenarios
  - Playwright selected-session smoke path verifying the overview loads from queue row navigation
- Done when:
  - opening a selected session gives an immediate, accurate read of status, next action, and recent narrative

### GBX-522: Redesign Operator Actions Around Urgency

- Status: `TODO`
- Depends on: `GBX-520`, `GBX-521`
- Goal: make approvals, questions, prompts, and forks feel like deliberate operator workflows instead of a single mixed form pane
- Deliverables:
  - priority action surface that shows pending approvals and questions before the freeform composer
  - approval card with subject, reason, risk level, policy source, requested time, approve action, deny action, pending state, success state, conflict state, and error state
  - question answer surface with pending prompt text, answer draft, submit state, and backend error feedback
  - composer surface shown only when the selected session can accept the next prompt or when the backend reports a clear unavailable reason
  - fork flow moved into a focused dialog or sheet with branch label, fork-point selection, blocked reason, and child-session navigation
  - mobile action layout that brings the primary approval or question into view before secondary prompt and fork controls
  - refreshed screenshot archive captures for priority action states and fork dialog or sheet states
- Implementation notes:
  - approval resolution must remain explicit and visually distinct from prompts and `ask_user` answers
  - use backend conflict and validation responses to drive action guidance
  - after mutation, rely on snapshot refresh and SSE for canonical state rather than local mutation fantasies
  - preserve keyboard-only action flows and focus restoration after dialogs or sheets close
- Tests and validation included in task:
  - React component tests for prompt, answer, approval approve, approval deny, fork latest, fork from turn, conflict, validation error, and network failure
  - store tests for action pending and stale-response handling if store behavior changes
  - screenshot archive comparison for action hierarchy before and after redesign
  - Playwright test for the core action sequence in both desktop and mobile viewports
- Done when:
  - the most urgent available action is visually first, keyboard reachable, and backed by trustworthy feedback

### GBX-523: Add Inline Action Feedback And Recovery Copy

- Status: `TODO`
- Depends on: `GBX-522`
- Goal: make action results understandable without forcing operators to infer status from disabled buttons or generic badges
- Deliverables:
  - inline success, pending, conflict, validation-error, unavailable-runtime, and network-error states near the action that caused them
  - retry behavior where backend semantics permit retry
  - copy for historical-only, live-unavailable, projection-degraded, and runtime-offline action states
  - toast usage reserved for cross-surface confirmations, not as the only place action state appears
  - refreshed screenshot archive captures for action feedback and recovery states
- Implementation notes:
  - avoid generic `action failed` copy when the normalized error contains a better reason
  - do not imply an action can be retried if the backend conflict means it has already been resolved or is no longer valid
  - preserve local drafts when recoverable failures occur
- Tests and validation included in task:
  - component tests for each action-state copy path
  - API-client error-normalization tests if new error mapping is needed
  - screenshot archive review of inline feedback visibility in desktop and mobile layouts
  - Playwright negative-path route fixture for at least one conflict and one network failure
- Done when:
  - operators can tell what happened after an action and what they can safely do next

---

## Phase 53: Session Narrative, Timeline, And Evidence Hierarchy

### GBX-530: Build A Turn-Grouped Transcript And Timeline Model

- Status: `TODO`
- Depends on: `GBX-520`, `GBX-502`, `GBX-492`
- Goal: make the selected session readable as a sequence of turns rather than isolated panels of transcript, metrics, and events
- Deliverables:
  - pure TypeScript helper that groups transcript messages, current turn, active tool calls, pending approvals, questions, live output, metrics, and event evidence by turn where snapshot data permits
  - timeline item types for user message, assistant message, tool call, approval request, question request, live output, failure, metric summary, and fork boundary
  - fallback behavior for historical or partial snapshots where turn grouping is incomplete
  - tests covering normal, live, failed, approval, question, tool-heavy, and partial-history sessions
  - screenshot scenario expectation updates if grouped narrative state changes what fixture-backed views should show
- Implementation notes:
  - keep the grouping helper pure and independent from React components and Zustand stores
  - do not infer authoritative turn state beyond backend data; make unknown or partial relationships explicit
  - preserve raw transcript message ordering
- Tests and validation included in task:
  - unit tests for the grouping helper with realistic fixtures
  - typecheck proving no broad `any` escapes are introduced
  - regression tests against selected v3 session-state fixtures
  - screenshot archive dry run to confirm narrative scenarios still render after state derivation changes
- Done when:
  - UI components can render a coherent session narrative from typed, deterministic derived state

### GBX-531: Redesign The Transcript Tab Around The Session Narrative

- Status: `TODO`
- Depends on: `GBX-530`
- Goal: make transcript inspection the central narrative surface for what happened and what is happening now
- Deliverables:
  - transcript tab that renders grouped turns with messages, tool-call summaries, live output snippets, approvals, questions, failures, and metrics in context
  - clear visual distinction between completed turns, active turns, pending interventions, failed turns, and historical turns
  - controls to jump to the latest activity, pending action, and failed turn where applicable
  - large-transcript behavior that remains performant and readable
  - refreshed screenshot archive captures for live, historical, failed, approval, question, and large-transcript narrative scenarios
- Implementation notes:
  - avoid burying active tool output or approval requests in separate panels when they belong to the current turn story
  - preserve access to full raw event evidence through the evidence tab
  - keep message text readable with stable widths and no horizontal scrolling
  - use virtualization only if measurements show it is needed; do not add it speculatively
- Tests and validation included in task:
  - component tests for narrative rendering across fixture scenarios
  - accessibility tests for landmarks, headings, and jump controls where practical
  - screenshot archive comparison for transcript readability and turn grouping
  - Playwright test for live SSE update appearing in the narrative view
- Done when:
  - operators can understand the current session story without piecing it together from disconnected cards

### GBX-532: Build A Focused Timeline Tab

- Status: `TODO`
- Depends on: `GBX-530`, `GBX-531`
- Goal: provide a dense turn-level summary for scanning progress, failures, tool usage, and fork boundaries
- Deliverables:
  - timeline tab with turn rows or a vertical timeline for turn status, duration, model calls, tool calls, approvals, questions, failures, and forkable boundaries
  - filters or quick jumps for failed turns, active turn, pending actions, and branchable turns if the fixture set proves they are useful
  - fork-point affordances that can open the fork dialog with the chosen turn preselected
  - connection to metrics data without requiring operators to inspect a separate metrics table first
  - refreshed screenshot archive captures for timeline scanning, failed-turn, active-turn, and fork-boundary scenarios
- Implementation notes:
  - timeline is a navigation and scanning surface, not a duplicate raw event log
  - keep labels concise and stable so live updates do not cause distracting layout shifts
  - use backend-provided branchable turns and metrics rather than transcript similarity or browser-only guesses
- Tests and validation included in task:
  - component tests for timeline rows and branchable-turn actions
  - interaction tests for opening fork flow from a timeline turn
  - screenshot archive review for timeline density and visual stability
  - Playwright workflow for failed-turn or fork-point navigation where practical
- Done when:
  - operators can scan session progress and jump to meaningful turns quickly

### GBX-533: Move Diagnostics Into Progressive Evidence Surfaces

- Status: `TODO`
- Depends on: `GBX-520`, `GBX-531`, `GBX-532`
- Goal: preserve raw evidence while preventing diagnostics from dominating the default inspector
- Deliverables:
  - evidence tab or drawer containing event log, live output tail, stream state, projection details, and raw metric details
  - runtime tab focused on working set, repository context, runtime notes, and provenance
  - metrics presentation that summarizes turn-level cost and duration before exposing raw rows
  - evidence and runtime surfaces that handle long local paths and artifact labels without text running together or overflowing on mobile
  - clear empty states that do not consume large default-layout space
  - refreshed screenshot archive captures for evidence-heavy, runtime-context-heavy, metric-heavy, and empty-diagnostics states
- Implementation notes:
  - evidence is essential, but it should be intentionally requested unless it is blocking or directly relevant to the current action
  - keep raw event ordering and sequence numbers visible in the evidence surface
  - do not remove data that v3 parity guaranteed; move it into better hierarchy
- Tests and validation included in task:
  - component tests for evidence, runtime, metrics, empty, and large-data states
  - screenshot archive refresh for diagnostics and evidence scenarios
  - Playwright direct-link tests for evidence and runtime tabs
  - manual review with an event-heavy fixture
- Done when:
  - raw diagnostic detail remains available without crowding the action and narrative surfaces

---

## Phase 54: Lineage, Compare, Drift, And Verification UX

### GBX-540: Build A Focused Lineage Navigator

- Status: `TODO`
- Depends on: `GBX-520`, `GBX-522`, `GBX-532`, `GBX-492`
- Goal: make parent, child, sibling, and fork-point relationships easy to understand and act on
- Deliverables:
  - lineage tab centered on current session, parent session, child sessions, and branchable turns
  - clear actions for opening a lineage target, comparing with a lineage target, and forking from a valid turn
  - branch metadata presentation for label, source turn, source sequence, updated time, and status where available
  - empty and partial-lineage states that remain compact and neutral
  - refreshed screenshot archive captures for root, parented, child-bearing, and forkable lineage scenarios
- Implementation notes:
  - lineage must remain anchored in persisted backend snapshot fields
  - do not infer sibling relationships unless the backend exposes enough data to do so reliably
  - preserve mental model when moving between sessions by keeping selected queue and compare context predictable
- Tests and validation included in task:
  - component tests for root, parented, child-bearing, and forkable sessions
  - route tests for opening lineage targets and compare targets
  - screenshot archive review for lineage mental model clarity
  - Playwright workflow for opening a child session and returning to the parent context
- Done when:
  - branching relationships are visible and actionable without requiring raw snapshot inspection

### GBX-541: Redesign Compare Into A Real Difference View

- Status: `TODO`
- Depends on: `GBX-540`
- Goal: make session comparison useful for triage rather than mostly showing counts
- Deliverables:
  - compare tab that shows current and compared session status, branch metadata, fork source, runtime context, working set, transcript summary, and turn metrics
  - difference summaries for transcript length, latest messages, status changes, runtime-context changes, working-set changes, and turn-summary changes where reliable data exists
  - navigation into compared session without losing the operator's selected queue context
  - overview and mobile affordances that make active compare context discoverable without burying it below unrelated panels
  - clear loading, missing target, invalid target, and partial-data states
  - refreshed screenshot archive captures for compare target selected, compare target missing, and compared-session navigation states
- Implementation notes:
  - anchor comparison in persisted lineage and snapshot data, not transcript similarity heuristics
  - prefer useful summaries over noisy side-by-side raw dumps
  - keep raw transcript and evidence accessible from each compared session through navigation, not duplicated everywhere
- Tests and validation included in task:
  - store tests for compare target loading, stale responses, reset, and invalid target handling if store behavior changes
  - component tests for compare differences and missing-data states
  - screenshot archive comparison showing compare is more informative than the v3 count summary
  - Playwright workflow for selecting a compare target and opening the compared session
- Done when:
  - comparison helps operators understand what changed between related sessions quickly enough to support branch triage

### GBX-542: Refine Verification And Drift Cues

- Status: `TODO`
- Depends on: `GBX-533`, `GBX-541`
- Goal: make replay, eval, artifact, and working-set cues useful without visually conflating them with runtime health or session failure
- Deliverables:
  - verification surface that distinguishes blocking evidence, advisory drift, inherited working-set items, missing artifacts, and verified state
  - promotion rules for when verification cues appear in overview versus evidence/runtime tabs
  - copyable or openable artifact references where safe local references are exposed
  - working-set provenance summary that highlights likely causes before listing all raw items
  - compact mobile rendering for artifact paths, target paths, failing test names, advisory drift, and inherited working-set provenance
  - refreshed screenshot archive captures for blocking evidence, advisory drift, inherited working-set, missing-artifact, and verified states
- Implementation notes:
  - do not make the SPA run deterministic replay or eval itself
  - keep replay/eval evidence grounded in existing artifact summaries and runtime-context data
  - advisory drift should not look like a runtime failure unless the backend marks it as blocking evidence
  - baseline artifact-drift screenshots showed evidence labels running together and advisory cues competing with blocking evidence; fix copy spacing and relative visual weight as part of this task
- Tests and validation included in task:
  - component tests for blocking, advisory, inherited, missing, stale, timed-out, and verified states
  - screenshot archive review that advisory cues do not visually read as runtime failures
  - Playwright direct-link or selected-session tests for an artifact-backed drift scenario
  - documentation update describing how v4 surfaces replay/eval evidence without replacing CLI workflows
- Done when:
  - verification and drift cues help operators inspect likely causes while preserving the CLI/backend replay discipline

---

## Phase 55: Design System, Accessibility, And Release Gate

### GBX-550: Refresh The v4 Visual System And Density Rules

- Status: `TODO`
- Depends on: `GBX-501`, `GBX-510`, `GBX-520`, `GBX-492`
- Goal: make the console visually precise, calm, dense, and consistent across the redesigned surfaces
- Deliverables:
  - updated Tailwind tokens for background, surfaces, borders, semantic status colors, focus states, row density, and typography
  - component-level density rules for attention rows, status rail, action cards, transcript turns, timeline rows, tabs, dialogs, sheets, and evidence lists
  - restrained color strategy that avoids a one-note palette and reserves warning/destructive color for actual attention states
  - visual hierarchy rules for page regions versus repeated cards so the app does not feel like nested panels
  - explicit rules for when to use cards, section boundaries, rows, chips, badges, and inline metadata so the console does not become a stack of equal-weight boxes
  - refreshed full screenshot archive after visual-token and density changes
- Implementation notes:
  - keep the console work-focused, not illustrative or marketing-oriented
  - avoid decorative backgrounds, oversized hero typography, and card-heavy page composition
  - baseline empty and selected-session screenshots are understandable but over-carded; this task should reduce nested panel weight without losing scannability
  - preserve accessible contrast and visible focus states
  - avoid layout shifts from live updates by using constrained row heights and stable control dimensions
- Tests and validation included in task:
  - component smoke tests where token or primitive changes affect rendered behavior
  - Playwright screenshot archive refresh for representative desktop and mobile states, used for manual review unless a visual-regression tool is deliberately introduced
  - manual contrast and density review against the fixture matrix
- Done when:
  - the console has a coherent v4 visual system that supports scanning, intervention, and trust

### GBX-551: Complete Keyboard And Accessibility Pass

- Status: `TODO`
- Depends on: `GBX-513`, `GBX-522`, `GBX-540`
- Goal: ensure high-frequency operator workflows work without a pointer and remain understandable to assistive technologies
- Deliverables:
  - keyboard paths for queue selection, session opening, tab changes, transcript/timeline jumps, composer submit, answer submit, approval approve/deny, fork dialog, lineage target selection, compare target selection, and returning to queues on mobile
  - semantic landmarks, tab panels, accessible names, status labels, and polite live-region announcements for important state changes where practical
  - focus restoration after dialogs, sheets, route changes, and successful or failed actions
  - reduced-motion compliance for nonessential transitions
  - refreshed screenshot archive captures for visible focus states on the highest-frequency desktop and mobile workflows where practical
- Implementation notes:
  - status and health indicators must not rely on color alone
  - disabled and pending states should remain announced and understandable
  - live updates should not steal focus from an operator composing an answer or approval decision
- Tests and validation included in task:
  - React Testing Library tests for keyboard paths and focus behavior where practical
  - Playwright keyboard-only workflow for queue to action to feedback
  - screenshot archive review for focus visibility and no focus-induced layout shifts
  - accessibility checks supported by the chosen test stack, plus manual screen-reader spot checks if available
- Done when:
  - the redesigned console supports pointer-free operation for the workflows an operator performs most often

### GBX-552: Add v4 Browser Workflow And Visual Review Coverage

- Status: `TODO`
- Depends on: `GBX-513`, `GBX-531`, `GBX-541`, `GBX-542`, `GBX-550`, `GBX-551`
- Goal: protect the redesigned UX with scenario-based browser coverage that catches regressions in real operator flows
- Deliverables:
  - Playwright scenarios for urgent queue triage, selected-session overview, approval resolution, question answer, prompt submission, fork creation, lineage navigation, compare view, evidence inspection, degraded projection, historical session, and mobile drill-in
  - screenshot archive generation wired into the scenario matrix for v4 UX review
  - screenshot or trace retention policy for v4 UX failures that is useful but low churn
  - documented manual visual review checklist for representative states and viewports
  - optional pixel or screenshot checks only for stable layout invariants such as nonblank primary regions, no horizontal overflow, no dev-overlay contamination, unclipped mobile queue rows, and visible action surfaces
- Implementation notes:
  - use deterministic fixtures and fake model behavior rather than live provider calls
  - keep tests focused on user-observable workflow outcomes, not brittle implementation details
  - use mobile and desktop viewports in the critical-path suite
- Tests and validation included in task:
  - `pnpm --dir frontend test:e2e`
  - `pnpm --dir frontend screenshots:v4-audit`
  - `pnpm --dir frontend test`
  - `pnpm --dir frontend build`
  - automated or documented visual checks for the Phase 49 screenshot findings so they do not regress after redesign
  - manual visual review against the checklist
- Done when:
  - the redesigned dashboard has enough browser coverage to make future UI changes safer

### GBX-553: Define And Enforce The v4 UX Release Gate

- Status: `TODO`
- Depends on: `GBX-552`
- Goal: decide when the redesigned SPA is good enough to call the v4 operator console baseline
- Deliverables:
  - v4 UX release checklist covering attention queues, selected-session overview, real tabs, priority actions, turn narrative, timeline, runtime context, evidence, lineage, compare, verification cues, mobile drill-in, accessibility, and visual density
  - automated coverage map for each release-gate requirement
  - final v4 screenshot archive reviewed against the current-SPA baseline and the known-gaps list
  - manual validation checklist using representative real or deterministic sessions
  - explicit known-gaps list for any non-blocking UX limitations that remain
  - docs updates for dashboard usage and troubleshooting if behavior changes materially
- Implementation notes:
  - do not treat v4 as complete because parity still passes; this gate is about improved operator quality
  - all critical actions must remain covered by unit/component and browser tests
  - the production FastAPI-served static build path must be validated before declaring the UX release gate complete
- Tests and validation included in task:
  - full frontend validation
  - final `pnpm --dir frontend screenshots:v4-audit` archive generation and review
  - full relevant Python web/dashboard validation
  - production static build and FastAPI-served dashboard smoke test
  - manual desktop and mobile review against the gate
- Done when:
  - the project has objective evidence that the v4 dashboard is materially better than the v3 SPA baseline and safe to treat as the new operator-console standard

---

## Recommended Build Order For The First v4 UX Recovery Slice

If an agent wants the fastest path to a demonstrable improvement, the recommended order is:

1. `GBX-490` through `GBX-493`
2. `GBX-500` and `GBX-501`
3. `GBX-502`
4. `GBX-520`
5. `GBX-521` and `GBX-522`
6. `GBX-511`
7. `GBX-513`
8. `GBX-530` and `GBX-531`
9. selected coverage from `GBX-552`

That yields:

- a repeatable screenshot archive, clean capture hygiene, and current-SPA visual baseline
- a documented UX baseline
- reusable representative fixtures
- inspector tabs that actually reduce cognitive load
- a selected-session overview focused on next action and recent narrative
- action surfaces ordered around urgency
- queue rows that support triage instead of generic table scanning
- a mobile path that is intentionally designed rather than squeezed

## Explicit Non-Goals For v4 UX Execution

Do not spend time on these unless a later task graph explicitly adds them:

- replacing the Next.js, TypeScript, Tailwind, Zustand, or shadcn-style foundation
- requiring a production Node server for dashboard use
- moving canonical session state into browser-only storage
- adding authentication, tenancy, remote collaboration, or hosted cloud assumptions
- changing approval, prompt, answer, fork, SSE, replay, or eval semantics for visual convenience
- deleting raw evidence surfaces in the name of simplification
- committing large screenshot binary archives by default without an explicit artifact-retention decision
- adding broad command palettes, dashboards, charts, or analytics tables before the core operator flows are excellent
- introducing decorative visual themes, landing pages, hero sections, or marketing-style composition
- implementing browser-side replay or eval execution

## Success Criteria For The v4 UX Redesign

The v4 redesign is on track when all of the following are true:

- opening the dashboard immediately shows workspace health and the highest-priority operator work
- a repeatable screenshot archive captures the current UX baseline and stays current as visible v4 surfaces change
- queue rows explain why each session needs attention without requiring a snapshot fetch
- selecting a session opens an overview that explains status, live posture, projection health, recent narrative, and next action
- inspector tabs control actual content and make diagnostics available without crowding default views
- pending approvals and questions appear before freeform prompts and forks
- transcript and timeline views make live and historical session progress readable by turn
- raw events, metrics, runtime context, verification cues, and artifacts remain accessible through intentional evidence surfaces
- lineage and compare views make branching easier to reason about than the v3 baseline
- desktop supports simultaneous triage and inspection, while mobile supports a focused drill-in workflow
- pointer-free operation works for the most common workflows
- frontend validation, browser coverage, and manual visual review protect the improved UX
