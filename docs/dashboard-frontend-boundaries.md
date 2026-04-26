# Dashboard Frontend Boundaries

## V3 Supersession Notice

This document is now legacy guidance for the existing no-framework dashboard in
`src/glassbox/web/static/`. It remains useful while that implementation is still
available through the temporary `/legacy` route, but it is no longer the target
frontend architecture for new dashboard work.

The target v3 dashboard architecture is a TypeScript, Next.js, Tailwind,
Zustand, and shadcn-style SPA developed under `frontend/`, statically exported
for production, and served by FastAPI from `src/glassbox/web/static_next/`.
FastAPI remains the API owner, runtime owner, and production serving process;
Next.js server capabilities are development tooling only for the first SPA
migration.

Use [tasks-v3.md](./tasks-v3.md) for the v3 execution graph and
[architecture.md](./architecture.md) for the code-aligned SPA contract. Use this
file only when maintaining or comparing against the legacy dashboard until the
SPA reaches the parity gate and replaces it.

## V3 SPA Migration Contract

The SPA must preserve Glassbox's current event-sourced browser contract while
changing the implementation stack.

Accepted stack and workspace rules:

- package manager: `pnpm`
- framework: Next.js App Router with strict TypeScript
- styling: Tailwind CSS
- component system: shadcn-style components on headless/Radix primitives
- client state: Zustand stores over pure typed reducers
- API types: OpenAPI-generated TypeScript from the FastAPI schema
- production serving: static export served by FastAPI, not a Node server
- migration source: `frontend/`
- production asset target: `src/glassbox/web/static_next/`

The development path may run a Next.js dev server with API and SSE rewrites to a
local FastAPI server. The production path is always FastAPI serving the static
SPA build. Release packaging should include built SPA assets when available so
ordinary operators do not need Node or `pnpm` to open the dashboard from an
installed Python package.

Route migration rules:

- serve the built SPA at `/` after the SPA parity gate is satisfied
- preserve `/app` as a temporary SPA alias during migration
- keep `/legacy` mapped to the no-framework dashboard for one migration window
- make direct `/app` refreshes and nested client routes resolve to the SPA shell
- keep direct `?session=SESSION_ID` links working during migration and after the
   final route flip
- after the migration window, retire the `/legacy` route and no-framework assets

Compatibility rules for the SPA:

- `GET /healthz` remains the health and event-transport observability endpoint
- `GET /sessions` remains compatible for recent-session discovery
- `GET /sessions/aggregate` remains the console overview, queue, health, and
   priority endpoint
- `GET /sessions/{session_id}` remains the selected-session snapshot endpoint
- `GET /sessions/{session_id}/events?after=SEQUENCE` remains the SSE stream,
   including historical replay before live events and sequence-based reconnect
- `POST /sessions/{session_id}/messages` remains the next-prompt action
- `POST /sessions/{session_id}/questions/{question_id}` remains the `ask_user`
   answer action
- `POST /sessions/{session_id}/approvals/{approval_id}` remains the approve and
   deny action
- `POST /sessions/{session_id}/fork` remains branch creation

The SPA may improve presentation, routing, keyboard flow, responsive layout, and
draft preservation, but browser state remains derived from aggregate responses,
snapshots, SSE events, and local UI drafts. It must not create browser-only
authority for session status, approval validity, fork points, runtime ownership,
projection health, lineage, comparison, replay, or eval evidence.

The parity gate before replacing `/` is behavioral. The SPA must cover session
index and aggregate console browsing, selected-session inspection, live SSE and
historical states, approvals, questions, prompt submission, forks, lineage,
compare, runtime context, metrics, active tools, live output, event log,
projection health, error handling, and direct session deep links.

## Legacy No-Framework Baseline

This note is the frontend architecture source of truth for `GBX-R130`, `GBX-R131`, and `GBX-R132`.

It now also records the `GBX-R133` app-entry split for transport, controller, and DOM-binding responsibilities.

It defines how the current no-framework dashboard was decomposed without changing browser-visible behavior, HTTP payloads, or the existing frontend test strategy.

## Purpose

The legacy dashboard frontend already has the right high-level separation for
its current implementation:

- `state.js` owns a pure reducer and snapshot hydration model
- `render.js` owns pure HTML string renderers
- `approval-actions.js` and `interaction-actions.js` own fetch-based browser actions
- `dashboard.js` owns browser bootstrapping, DOM mutation, URL/history handling, snapshot loading, and SSE lifecycle

The remaining legacy maintenance concern is keeping those responsibilities
separate while the SPA is built in parallel.

The goal for legacy-only changes is to preserve stable responsibility boundaries
without expanding the no-framework implementation beyond what is needed before
the SPA replaces it.

## Non-Goals

Legacy maintenance should not:

- introduce React, Vue, or another client framework into `src/glassbox/web/static/`
- replace HTML-string rendering with a virtual DOM abstraction
- change snapshot or session-index payload shapes
- move browser-specific transport concerns into the reducer or renderer layers
- rewrite the current dashboard tests around a new harness model

## Current Frontend Surface

The current browser surface under `src/glassbox/web/static/` is:

- `dashboard.js`: app entry, DOM lookup, render scheduling, form/button event binding, URL sync, fetch orchestration, and SSE reconnect flow
- `state.js`: state creation, snapshot normalization, session-index/session-selection state, stream-state transitions, interaction transient state, and incremental event reduction
- `render.js`: selected-session summary, landing/session-browser panes, transcript/output panes, composer/fork panes, approvals pane, and turn/metrics/tool/event panes
- `approval-actions.js`: approval request building, server error extraction, and approval POST flow
- `interaction-actions.js`: prompt/answer/fork request building, server error extraction, and interaction POST flow

That shape should remain the legacy public mental model after the split, even if internal helpers move under submodules.

## Legacy Module Map

The legacy decomposition keeps the existing top-level browser files as stable facades first, then moves internals behind them.

The first reducer split is now in place:

- `state-core.js` owns base state creation and idle submission helpers
- `state-snapshot.js` owns snapshot normalization, hydration, lineage defaults, and runtime-context note merging helpers
- `state-stream.js` owns session-index, session-selection, and stream-state transitions
- `state-interaction.js` owns browser submission-state helpers for approvals, prompts, answers, and forks
- `state-events.js` owns incremental event reduction and event-scoped reducer helpers
- `state.js` remains the stable public facade consumed by the browser app and frontend tests

The first renderer split is now in place:

- `render-utils.js` owns shared escaping, empty-state, status-chip, and short-ID helpers
- `render-session-panes.js` owns landing, session-browser, selected-session summary, runtime-context, and lineage panes
- `render-activity-panes.js` owns transcript, current-turn, and live-output panes
- `render-action-panes.js` owns composer, fork, and approvals panes
- `render-diagnostics-panes.js` owns metrics, active-tool-calls, and event-log panes
- `render.js` remains the stable public facade consumed by the browser app and frontend tests

The first dashboard app-entry split is now in place:

- `dashboard-transport.js` owns snapshot/index fetches and SSE connection setup
- `dashboard-controller.js` owns state transitions, session selection flow, live-stream retry behavior, and action orchestration
- `dashboard-dom.js` owns DOM lookup, pane rendering, event binding, and local input drafts
- `dashboard.js` remains the stable public facade consumed by the browser app and frontend tests

### State Boundary

`state.js` remains the public reducer facade for the legacy dashboard, with internals split into these responsibility groups:

1. Snapshot hydration and normalization
   - owns `createState()`, snapshot field normalization, runtime-context normalization, current-turn inference, and default fork selection rules
   - pure input/output only

2. Session browser and stream lifecycle state
   - owns session-index loading state, session selection/reset, live-stream connection state, reconnect/unavailable/historical transitions, and selected session bookkeeping
   - pure input/output only

3. Browser submission state
   - owns transient browser-only submission state for approvals, prompts, answers, and forks
   - includes helpers such as `beginApprovalResolution`, `confirmApprovalResolution`, `failApprovalResolution`, and the interaction/fork submission state helpers
   - pure input/output only

4. Incremental event reduction
   - owns `applyEvent()` and helpers that update transcript messages, approvals, tool calls, live output, fork points, turn metrics, runtime-context notes, and terminal session status transitions
   - pure input/output only

The important contract is that snapshot hydration, browser submission state, and live-event reduction stay separable even if they continue to compose into one exported reducer surface.

### Renderer Boundary

`render.js` remains the public renderer facade for the legacy dashboard, with panes grouped by UI responsibility instead of one broad renderer file.

The legacy pane families are:

1. Session discovery and selection
   - landing pane
   - session browser pane
   - session summary helpers that explain availability for index cards

2. Selected-session summary and lineage
   - selected-session summary pane
   - runtime-context summary
   - lineage navigator
   - shared stream/availability summary helpers used by the selected-session header

3. Transcript and live activity
   - transcript pane
   - live output pane
   - current-turn pane

4. Operator actions
   - composer pane
   - fork card
   - approvals pane

5. Operational diagnostics
   - metrics pane
   - active tool-calls pane
   - event-log pane

Small string/HTML helpers such as escaping, short-ID formatting, empty-state rendering, and status/guidance chips may live in a focused shared renderer utility module if that reduces duplication without becoming another catch-all file.

### Transport Boundary

The existing transport split is already the right baseline and should stay explicit:

- `approval-actions.js` owns approval POST transport and approval-specific error handling
- `interaction-actions.js` owns prompt, answer, and fork POST transport plus their request-building helpers
- `dashboard.js` owns snapshot/index GET requests and SSE connection lifecycle because those concerns are tied to navigation and selected-session browser state

The action helper modules may keep small pure request-construction helpers next to the network calls, but fetch execution and response decoding must stay outside reducer and renderer modules.

### DOM-Binding Boundary

`dashboard.js` remains the only legacy place that talks directly to browser globals or DOM nodes.

Its stable responsibilities are:

- app bootstrap from `window` and `document`
- DOM node lookup and `innerHTML` updates
- attaching click, submit, input, and change handlers after render
- draft-input buffering for textarea and fork-label fields
- URL query-string reading and history updates
- snapshot/index loading orchestration
- SSE open/close/reconnect lifecycle
- wiring transport action results back into reducer state and re-rendering

It should not absorb reducer rules, HTML composition rules, or reusable server-request builders that belong in the existing pure or transport layers.

## Purity Contract

The boundary contract for later frontend splits is:

### Pure and side-effect free

- `state.js` and its extracted reducer helpers
- `render.js` and its extracted pane-family helpers
- pure request payload builders that only shape `{ method, headers, body }`

Pure modules may:

- accept plain objects, arrays, strings, and numbers
- return plain state objects or HTML strings
- share deterministic helper functions

Pure modules may not:

- call `fetch`
- create `EventSource`
- read `window`, `document`, `location`, or `history`
- attach event listeners
- mutate DOM nodes
- keep hidden mutable module state

### Browser- or network-bound

- `dashboard.js`
- the async transport functions in `approval-actions.js`
- the async transport functions in `interaction-actions.js`

Browser- or network-bound modules may:

- call `fetch`
- create and close `EventSource`
- read and write browser location/history state
- read and update DOM nodes
- attach event listeners
- keep app-local ephemeral drafts that exist only to bridge DOM inputs across re-renders

Browser- or network-bound modules should not:

- embed reducer-only business rules that can be expressed as pure state transitions
- generate pane HTML inline when a pure renderer already owns that surface

## Test-Preservation Plan

The existing frontend tests already map cleanly onto the legacy split. That test shape should be preserved until the SPA test harness replaces it for new work.

### Existing Test Seams

- `tests/frontend/test_dashboard_state.js` protects snapshot hydration, stream state transitions, event reduction, lineage/fork state, runtime-context updates, and browser submission state
- `tests/frontend/test_dashboard_render.js` protects pane-family HTML output for session discovery, selected-session summary, transcript/output, approvals/composer/fork UI, and operational diagnostics
- `tests/frontend/test_approval_actions.js` protects approval transport behavior
- `tests/frontend/test_interaction_actions.js` protects prompt/answer/fork transport behavior
- `tests/frontend/test_dashboard_app.js` protects browser wiring for init, deep links, URL sync, historical sessions, SSE reconnect behavior, and fork-open flow
- `tests/test_frontend_unit.py` remains the outer Node-based smoke gate for the whole browser surface

### Migration Rules

1. Keep the current public imports stable first.
   - `state.js`, `render.js`, `approval-actions.js`, `interaction-actions.js`, and `dashboard.js` should continue exporting the same public functions while internals move behind them.

2. Extract pure helpers before changing call sites.
   - `GBX-R131` should move hydration/event/submission helpers into focused modules and re-export them from `state.js` before any broader import rewrites.
   - `GBX-R132` should move pane families into focused renderer modules and re-export them from `render.js` before any broader import rewrites.

3. Keep transport tests pinned to transport modules.
   - request-building and async POST behavior should stay testable without pulling in DOM code or reducer code.

4. Keep app-entry tests pinned to browser orchestration only.
   - `test_dashboard_app.js` should continue treating `createDashboardApp()` as the integration seam for DOM, navigation, fetch, and SSE behavior.

5. Delay test-file reshaping until after the split proves stable.
   - the first extraction pass should preserve current test file paths and assertions; test reorganization is optional follow-up work, not a prerequisite for decomposition.

## Recommended Extraction Order

The next frontend tasks should proceed in this order:

1. Split `state.js` behind the existing facade into snapshot helpers, stream/session-selection helpers, submission-state helpers, and event-reduction helpers.
2. Split `render.js` behind the existing facade into pane families that match the current Node renderer tests.
3. Leave `dashboard.js` as the final browser-only shell, then trim it by extracting DOM-binding helpers or navigation/SSE helpers only when those seams become obviously stable.

This order keeps the most testable logic moving first and avoids dragging browser globals into modules that should stay deterministic.

## Boundary Summary

The stable legacy dashboard frontend architecture is:

- pure state transitions and snapshot shaping in the reducer layer
- pure pane HTML generation in the renderer layer
- fetch and SSE transport in focused action or app-entry modules
- DOM, history, and event binding only in the browser entry shell

That is sufficient for the current dashboard. The refactor work should tighten these seams, not replace them.
