# Glassbox v3 Tasks

For the docs hub and operator guides, start at [README.md](./README.md). This file is the v3 task graph for moving the Glassbox dashboard from hand-rolled browser assets to a TypeScript, Next.js, and shadcn-based SPA.

## Purpose

This document defines Glassbox v3: the next major frontend evolution after the completed v2 operator-console baseline in [tasks-v2.md](./tasks-v2.md).

It is written in the same execution style as [tasks-v1.md](./tasks-v1.md) and [tasks-v2.md](./tasks-v2.md): explicit dependencies, small vertical slices, concrete deliverables, and quality requirements attached directly to the work.

The current dashboard under `src/glassbox/web/static/` has served the project well, but the no-framework browser architecture is no longer the desired direction. The new direction is a modern TypeScript SPA that preserves Glassbox's local-first runtime model, event-sourced backend contracts, and deterministic replay discipline while materially improving operator UX.

## Product Direction

The frontend SPA work should optimize for five outcomes:

- a fantastic multi-session operator console UX for live, paused, failed, historical, and branched sessions
- a typed frontend architecture that makes API contracts, reducer state, and UI behavior easier to evolve safely
- a production build that remains local-first and is served by the existing FastAPI process
- a development workflow that uses modern frontend tooling without forcing Node into the normal Python runtime path
- an incremental migration path that keeps the current dashboard usable until the SPA reaches parity

The frontend modernization thesis is:

- keep FastAPI as the runtime and API owner
- keep canonical events and backend projections as the source of truth
- use Next.js as a static-exported SPA, not as a required production Node server
- use TypeScript, generated OpenAPI types, Zustand, Tailwind, and shadcn UI patterns from the start
- replace the old dashboard only after parity is proven through tests and manual operator validation

## Chosen Stack

The accepted stack decisions are:

- package manager: `pnpm`
- frontend framework: Next.js with TypeScript
- styling: Tailwind CSS
- client state: Zustand
- component system: shadcn-style components built on headless/Radix primitives
- migration route: `/app` during migration, then `/` after parity
- API typing: OpenAPI-driven TypeScript generation from the FastAPI contract from the start
- production mode: static frontend export served by FastAPI

## Current Baseline Before SPA Execution

Treat the following as the starting point for every task in this document:

- FastAPI owns `/healthz`, `/sessions`, `/sessions/aggregate`, `/sessions/{session_id}`, `/sessions/{session_id}/events`, approval actions, prompt submission, answer submission, and fork actions
- the dashboard root is currently served from `src/glassbox/web/static/dashboard.html`
- current static browser modules already separate state, renderers, transport, controller, and DOM binding, but they are plain JavaScript and string-rendered HTML
- current frontend tests run through Node's built-in test runner from `tests/test_frontend_unit.py`
- [dashboard-frontend-boundaries.md](./dashboard-frontend-boundaries.md) records the old no-framework decomposition and should be treated as a legacy baseline until this task graph supersedes it through implementation and doc updates
- [operator-console.md](./operator-console.md) defines the current v2 console information architecture and should remain the product UX baseline for the new SPA
- the Python package should continue to work for normal operators without requiring a production Node process

## Agent Execution Rules

These rules apply to every task in this file.

1. Respect dependency order. Do not start a task until its dependencies are complete unless the task explicitly says it can proceed in parallel.
2. Preserve the event-sourced source-of-truth rule. Browser state is derived from backend snapshots, SSE events, and local UI drafts only.
3. Preserve FastAPI as the runtime owner. The Next app may proxy in development, but production dashboard serving must not require a Node server.
4. Prefer small executable vertical slices over broad scaffolding. Each phase should leave the dashboard more usable or the migration safer.
5. Every implementation task automatically includes:
   - automated tests for new behavior
   - `pnpm` lint, typecheck, unit test, and build compliance for touched frontend code
   - `ruff` formatting and lint compliance for touched Python code
   - `ty` typecheck compliance for touched Python code
   - documentation updates when contracts, routes, packaging, workflows, or operator-visible behavior change
6. Do not weaken live SSE behavior, approval semantics, fork semantics, projection health reporting, or replay/eval determinism in pursuit of frontend ergonomics.
7. Keep the legacy dashboard route available until the SPA satisfies the parity gate defined in this file.
8. If the SPA uncovers a backend API mismatch, fix the API contract or document the mismatch before encoding browser-only workarounds.

## Completion Contract For Any Task

A task is complete only when all of the following are true:

- the implementation exists in the intended module boundary
- automated tests covering the new behavior exist and pass
- frontend lint, typecheck, unit tests, and build pass for touched frontend code
- Python lint, typecheck, and tests pass for touched backend code
- the task does not leave placeholder code or hidden follow-up work outside this file
- docs are updated if the task changes persistence, transport, operator-visible behavior, frontend build workflows, or verification workflows

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
    lib/
    styles/
    tests/
src/glassbox/web/
src/glassbox/web/static/
src/glassbox/web/static_next/
tests/
docs/
```

## Recommended Validation Commands

Use the narrowest viable validation after each task, but the baseline validation pattern for completed frontend SPA work should include:

```bash
pnpm --dir frontend lint
pnpm --dir frontend typecheck
pnpm --dir frontend test
pnpm --dir frontend build
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run pytest
```

During incremental implementation, use narrower commands where possible:

```bash
pnpm --dir frontend test -- dashboard-state
pnpm --dir frontend typecheck
uv run pytest tests/integration/test_specific_web_flow.py
uv run ruff check src/glassbox/web tests/integration/test_specific_web_flow.py
```

## Milestone Map

The intended frontend SPA milestone order is:

1. frontend architecture decision and compatibility contract
2. Next.js workspace scaffold and static serving path
3. OpenAPI type generation and typed transport layer
4. typed state model and live event reduction
5. operator-console shell and core UX parity
6. action flows, lineage, comparison, and drift inspection
7. migration flip, packaging, CI, and legacy removal

## Task Graph

---

## Phase 40: SPA Architecture And Migration Contract

### GBX-400: Define Next.js SPA Architecture And Supersede The No-Framework Constraint

- Status: `TODO`
- Depends on: `GBX-363`
- Goal: establish the code-aligned architecture contract for replacing the hand-rolled dashboard with a TypeScript Next.js SPA
- Deliverables:
  - architecture and frontend-boundary docs updated to record Next.js, TypeScript, pnpm, Tailwind, Zustand, shadcn, OpenAPI-generated types, and static export served by FastAPI as the chosen direction
  - explicit statement that [dashboard-frontend-boundaries.md](./dashboard-frontend-boundaries.md) is now legacy guidance for the old implementation rather than the target architecture
  - development versus production serving model
  - route migration plan using `/app` during migration and `/` after parity
  - compatibility rules for preserving existing session APIs, SSE semantics, approval flows, prompt flows, answer flows, fork flows, and direct session deep links
- Implementation notes:
  - treat [operator-console.md](./operator-console.md) as the product UX baseline for the new SPA
  - keep FastAPI as the API and runtime owner; Next's server capabilities should not become part of the production runtime contract in the first migration
  - define how static assets are built, packaged, and served before the scaffold lands
  - define the minimum parity gate before replacing the current dashboard root
- Tests and validation included in task:
  - doc review against current FastAPI routes, static serving, SSE behavior, and dashboard tests
  - manual validation that the proposed architecture does not introduce a production Node dependency
- Done when:
  - the repo has a clear, code-aligned contract for the Next.js SPA migration and no longer treats no-framework JavaScript as the future frontend architecture

### GBX-401: Define Frontend UX Principles And Console Information Architecture For The SPA

- Status: `TODO`
- Depends on: `GBX-400`, `GBX-320`
- Goal: translate the v2 operator-console model into SPA-specific UX principles, layout rules, and interaction expectations
- Deliverables:
  - SPA UX brief for workspace overview, action queues, session inspector, transcript, timeline, runtime health, approvals, questions, lineage, compare, and drift views
  - responsive layout contract for desktop, narrow desktop, tablet, and mobile
  - accessibility and keyboard-navigation expectations for high-frequency operator actions
  - visual-density guidance that keeps the UI work-focused rather than marketing-oriented
- Implementation notes:
  - the first screen should be the operator console itself, not a landing page
  - optimize for scanning, intervention, and trustworthy live-state interpretation
  - avoid UI copy that explains implementation details instead of helping the operator choose the next action
  - keep the design compatible with Tailwind and shadcn component primitives
- Tests and validation included in task:
  - design review against existing dashboard operator workflows and [dashboard.md](./dashboard.md)
  - manual validation with representative sessions covering live, historical, failed, awaiting approval, awaiting user input, and branched states
- Done when:
  - implementers have a concrete UX contract for what the SPA should feel like and which workflows must be first-class

---

## Phase 41: Frontend Workspace Scaffold And Static Serving

### GBX-410: Scaffold The Next.js TypeScript Frontend Workspace

- Status: `TODO`
- Depends on: `GBX-400`
- Goal: add a modern frontend workspace without changing the current production dashboard route
- Deliverables:
  - `frontend/package.json` using `pnpm`
  - Next.js App Router project with strict TypeScript
  - Tailwind CSS configuration
  - shadcn-compatible component setup and path aliases
  - ESLint and formatting configuration aligned with the frontend stack
  - initial `frontend/app` route shell that can build successfully
- Implementation notes:
  - keep the initial shell deliberately small; do not start porting dashboard behavior in the scaffold task
  - prefer repository-local scripts such as `lint`, `typecheck`, `test`, `build`, and `openapi:generate`
  - make the frontend workspace self-contained enough that Python tests do not need to infer package-manager details
  - use committed lockfile behavior suitable for reproducible CI
- Tests and validation included in task:
  - `pnpm --dir frontend install --frozen-lockfile` or equivalent reproducible install validation once the lockfile exists
  - `pnpm --dir frontend lint`
  - `pnpm --dir frontend typecheck`
  - `pnpm --dir frontend build`
- Done when:
  - the repository has a reproducible Next.js TypeScript workspace that builds independently from the legacy dashboard

### GBX-411: Add Static Export Output And FastAPI Serving At `/app`

- Status: `TODO`
- Depends on: `GBX-410`
- Goal: serve the built SPA from the existing FastAPI process at `/app` without disturbing the legacy dashboard at `/`
- Deliverables:
  - Next.js configuration for static export compatible with FastAPI static hosting
  - build output path convention such as `src/glassbox/web/static_next/`
  - FastAPI route and static-file wiring for `/app` and SPA asset paths
  - fallback behavior for missing SPA build assets that gives developers a clear error
  - packaging configuration updates so built SPA assets are included in Python distributions when present
- Implementation notes:
  - keep `/` mapped to the existing dashboard until the parity gate is complete
  - ensure direct `/app` refreshes and nested client routes resolve to the SPA shell
  - do not make normal backend tests fail just because frontend assets have not been built in a source checkout unless the tested path requires them
- Tests and validation included in task:
  - HTTP integration tests for `/app`, static assets, missing-build behavior, and legacy `/` compatibility
  - frontend build validation before static asset serving tests that require the built app
- Done when:
  - a built Next SPA can be opened from the FastAPI server at `/app` while the old dashboard still works at `/`

### GBX-412: Add Frontend Development Proxy And Local Developer Workflow Docs

- Status: `TODO`
- Depends on: `GBX-411`
- Goal: make SPA development fast while preserving the FastAPI-owned production model
- Deliverables:
  - Next dev-server proxy or rewrite configuration for FastAPI API and SSE endpoints
  - documented development workflow for running FastAPI and Next together locally
  - documented production workflow for building static assets and serving through `glassbox dashboard serve`
  - environment variable conventions for local API base URL overrides if needed
- Implementation notes:
  - development may use a Next dev server, but production must remain static assets served by FastAPI
  - make SSE proxy behavior explicit and tested manually because reconnect behavior is central to the dashboard
  - keep docs aligned with `uv` plus `pnpm` commands
- Tests and validation included in task:
  - manual validation of Next dev server against a real FastAPI dashboard server
  - documentation review against actual commands
- Done when:
  - contributors can work on the SPA with hot reload and can also verify the production static-serving path without guessing commands

---

## Phase 42: OpenAPI Types And Typed Transport

### GBX-420: Add OpenAPI-Driven Type Generation For Browser Contracts

- Status: `TODO`
- Depends on: `GBX-410`
- Goal: generate TypeScript API types from the FastAPI OpenAPI schema from the start of the SPA migration
- Deliverables:
  - command for exporting the FastAPI OpenAPI schema deterministically
  - `openapi-typescript` or equivalent generation path under `frontend/`
  - generated TypeScript types for health, aggregate sessions, session snapshots, approvals, messages, answers, forks, and error responses
  - docs describing when generated files should be refreshed
- Implementation notes:
  - prefer generated transport types over hand-authored duplicate interfaces
  - keep generated output isolated from handwritten domain helpers
  - if FastAPI routes lack sufficient response models for useful generation, add or tighten backend response models in the same slice
  - make schema generation work without requiring a live server process where practical
- Tests and validation included in task:
  - schema generation command in CI or test validation
  - typecheck proving generated types are consumable from the frontend workspace
  - backend tests for any response-model tightening required for OpenAPI quality
- Done when:
  - the frontend can import generated API types that are derived from the actual FastAPI contract

### GBX-421: Implement Typed API Client And Error Normalization

- Status: `TODO`
- Depends on: `GBX-420`
- Goal: create the SPA transport layer for HTTP requests with generated types and consistent error handling
- Deliverables:
  - typed client helpers for health, aggregate sessions, session snapshots, approval resolution, prompt submission, user answers, session forks, and compare snapshot fetches
  - shared error normalization for FastAPI validation errors, conflicts, missing sessions, unavailable runtime states, and network failures
  - request cancellation support where route changes or session selection changes make in-flight responses stale
  - unit tests for request shaping and error decoding
- Implementation notes:
  - keep fetch execution in the transport layer, not in Zustand stores or components directly
  - expose domain-friendly errors that UI components can render without parsing raw response shapes
  - preserve current local-first assumptions; do not introduce auth/session infrastructure that the backend does not have
- Tests and validation included in task:
  - frontend unit tests with mocked fetch responses
  - typecheck against generated OpenAPI types
- Done when:
  - SPA code has one typed path for browser HTTP actions and consistent errors across operator workflows

### GBX-422: Implement Typed SSE Client And Reconnect Semantics

- Status: `TODO`
- Depends on: `GBX-420`, `GBX-421`
- Goal: preserve and improve live event streaming in the SPA through a typed SSE boundary
- Deliverables:
  - SSE client wrapper for `GET /sessions/{session_id}/events`
  - typed event decoding from generated or derived event payload types
  - reconnect state model covering connecting, live, reconnecting, live unavailable, and historical snapshot
  - sequence tracking and resume-after behavior aligned with the existing backend contract
  - tests for stream-state transitions and event dispatch behavior
- Implementation notes:
  - do not let raw EventSource callbacks mutate component-local state directly
  - keep browser stream state separate from persisted session state
  - be explicit when a snapshot is valid but the live stream is unavailable
- Tests and validation included in task:
  - frontend unit tests for stream lifecycle transitions using fake EventSource behavior
  - manual validation against live FastAPI SSE during development and static-served production mode
- Done when:
  - the SPA has a typed, testable live-event boundary equivalent to or better than the legacy dashboard behavior

---

## Phase 43: State Model And Store Architecture

### GBX-430: Port Snapshot Hydration And Event Reduction To TypeScript

- Status: `TODO`
- Depends on: `GBX-420`, `GBX-422`
- Goal: recreate the deterministic browser state model in TypeScript before building rich React UI on top of it
- Deliverables:
  - typed snapshot hydration helpers for session snapshots, aggregate sessions, lineage, runtime context, working-set summaries, projection health, and compare snapshots
  - typed event reducer for incremental session updates from SSE
  - preservation of current reducer semantics from the legacy dashboard where behavior is still correct
  - representative test fixtures ported or regenerated from current frontend fixtures
- Implementation notes:
  - keep reducer functions pure and side-effect free
  - use generated API types at the boundary and narrow into frontend domain types where that improves ergonomics
  - avoid coupling reducer behavior to React components or Zustand implementation details
- Tests and validation included in task:
  - frontend unit tests covering snapshot hydration, live event reduction, lineage, approvals, questions, tool calls, metrics, runtime context, and projection health
  - regression comparison against selected legacy dashboard fixtures where useful
- Done when:
  - the SPA has a typed deterministic state core that can stay synchronized from snapshot plus SSE events

### GBX-431: Implement Zustand Stores For Console, Session, Stream, And Draft State

- Status: `TODO`
- Depends on: `GBX-421`, `GBX-422`, `GBX-430`
- Goal: wire typed reducers and transport helpers into focused Zustand stores for the SPA
- Deliverables:
  - console store for aggregate sessions, queue selection, filters, health summaries, and prioritized rows
  - selected-session store for snapshot, transcript, timeline, approvals, questions, lineage, compare, and runtime context
  - stream store or slice for SSE lifecycle and last-seen sequence
  - local draft state for composer text, answer text, fork labels, selected compare target, and transient action state
  - store reset and stale-response handling for route changes
- Implementation notes:
  - keep server-derived session data distinct from local UI drafts and optimistic action state
  - avoid one giant store if focused slices make testing and ownership clearer
  - actions should call typed transport helpers, then rely on snapshots and SSE events for authoritative updates
- Tests and validation included in task:
  - frontend unit tests for store actions, stale request handling, draft preservation, and stream-state updates
  - typecheck proving store state is fully typed without broad `any` escapes
- Done when:
  - the SPA has testable client state that maps cleanly to Glassbox's backend contracts and operator workflows

### GBX-432: Add Routing, Deep Links, And Navigation State For `/app`

- Status: `TODO`
- Depends on: `GBX-431`
- Goal: make the migration route behave like a real SPA while preserving existing dashboard deep-link semantics
- Deliverables:
  - route model for `/app`, selected session, selected queue, compare target, and optional inspector tabs
  - compatibility handling for existing `?session=SESSION_ID` deep links during migration
  - navigation behavior for selecting sessions, opening lineage targets, returning to queues, and clearing invalid selections
  - tests for URL-state round trips and invalid-session recovery
- Implementation notes:
  - direct links from `glassbox session chat` should remain enough to open a live session in the browser
  - keep route state readable and stable rather than encoding large UI state blobs into the URL
  - preserve the future ability to flip the SPA from `/app` to `/`
- Tests and validation included in task:
  - frontend routing tests for deep links, queue links, selected sessions, compare links, and invalid-session fallback
  - manual validation through FastAPI static serving
- Done when:
  - `/app` has stable SPA navigation that supports both new console browsing and old direct session links

---

## Phase 44: Design System And Operator Console Shell

### GBX-440: Establish Tailwind, shadcn Components, Theme, And Accessibility Baseline

- Status: `TODO`
- Depends on: `GBX-401`, `GBX-410`
- Goal: create a polished, consistent UI foundation for the Glassbox operator console
- Deliverables:
  - Tailwind theme tokens for layout, spacing, typography, status colors, focus states, and dark or light mode policy
  - shadcn-style component primitives for buttons, inputs, textarea, tabs, dialog, sheet, dropdown menu, tooltip, badge, separator, scroll area, command palette, toast, and table/list surfaces as needed
  - icon strategy using an established React icon library compatible with shadcn patterns
  - accessibility baseline for focus visibility, keyboard navigation, reduced motion, and semantic labels
- Implementation notes:
  - keep the console visually work-focused, dense enough for repeated use, and calm under noisy runtime state
  - avoid decorative-first layouts; operational content should dominate the first viewport
  - do not put cards inside cards; use cards only for repeated items, dialogs, and genuinely framed tools
  - make status chips, queue tabs, and action controls stable in size so live updates do not cause distracting layout shifts
- Tests and validation included in task:
  - component smoke tests for common primitives
  - accessibility checks where the chosen test stack supports them
  - manual visual review across representative desktop and mobile widths
- Done when:
  - the SPA has a reusable design foundation that can support the operator console without ad hoc styling in every feature

### GBX-441: Build The Workspace Overview And Action Queue Console Shell

- Status: `TODO`
- Depends on: `GBX-431`, `GBX-432`, `GBX-440`
- Goal: make `/app` useful as a multi-session operator console before single-session parity is complete
- Deliverables:
  - workspace overview with runtime-owner status, projection-health summary, queue counts, and verification or observability cues where available
  - action queues for approvals, questions, failures, degraded sessions, active work, and recent historical sessions
  - prioritized session rows or cards grounded in `GET /sessions/aggregate`
  - loading, empty, stale, degraded, and error states for the console shell
  - responsive layout that preserves scan speed on desktop and remains usable on mobile
- Implementation notes:
  - this is the real first screen of the SPA; do not build a marketing landing page
  - preserve server-side priority semantics and avoid inventing hidden browser-only queue categories
  - queue rows should show the next meaningful operator action without forcing a full snapshot fetch
- Tests and validation included in task:
  - React/component tests for overview, queue selection, row rendering, empty states, and error states
  - store tests for aggregate hydration and filtering
  - manual validation against seeded sessions with mixed statuses
- Done when:
  - an operator can open `/app` and immediately understand what needs attention across the workspace

### GBX-442: Build The Selected-Session Inspector Shell

- Status: `TODO`
- Depends on: `GBX-432`, `GBX-440`, `GBX-441`
- Goal: recreate the core selected-session inspection surface in the new SPA shell
- Deliverables:
  - selected-session header with status, live-state, lineage hint, projection health, model, workspace, and next action
  - transcript pane
  - turn timeline pane
  - current turn, active tool calls, live output, metrics, runtime context, working set, approvals, questions, and event-log panes
  - inspector layout that supports split-pane desktop use and focused mobile navigation
- Implementation notes:
  - prioritize the current session narrative and active intervention surfaces over raw data density
  - retain access to raw evidence such as events, tool calls, and metrics so summaries do not hide debugging detail
  - keep live/historical/projection-degraded states visually distinct and consistent with CLI language
- Tests and validation included in task:
  - component tests using realistic snapshot fixtures
  - frontend integration tests for selecting a session from the queue and rendering the inspector
  - manual validation with large transcripts and long tool output
- Done when:
  - `/app` can inspect a selected session with the same core information as the legacy dashboard, organized through the new UX shell

---

## Phase 45: Browser Actions, Lineage, Compare, And Drift UX

### GBX-450: Implement Prompt, Answer, Approval, And Fork Actions In The SPA

- Status: `TODO`
- Depends on: `GBX-421`, `GBX-431`, `GBX-442`
- Goal: make the SPA an actionable operator console, not only a read-only inspector
- Deliverables:
  - composer for submitting the next prompt
  - pending-question answer flow
  - approval approve and deny flow with clear pending and resolved states
  - fork creation flow with fork-point selection and child-session navigation
  - optimistic or confirmed update behavior documented consistently per action type
  - toasts or inline status messages for success, conflict, and failure cases
- Implementation notes:
  - keep approval resolution explicit and visually distinct from freeform prompts and `ask_user` answers
  - use backend conflict responses to drive operator-visible guidance instead of guessing allowed actions in the browser
  - after mutation, rely on snapshot refresh and SSE for canonical state rather than local mutation fantasies
- Tests and validation included in task:
  - frontend action tests with mocked HTTP success, conflict, validation error, and network failure responses
  - integration tests against FastAPI routes for at least one representative action path where practical
  - manual validation against live chat-owned and daemon-owned sessions
- Done when:
  - an operator can continue, answer, approve, deny, and fork sessions from `/app` with trustworthy action feedback

### GBX-451: Implement Lineage Navigation And Session Compare Views

- Status: `TODO`
- Depends on: `GBX-442`, `GBX-450`
- Goal: make branching and historical inspection first-class in the SPA
- Deliverables:
  - lineage navigator for parent, child, and sibling session relationships exposed by snapshots
  - compare target selection for parent or child snapshots
  - compare view showing transcript, status, branch metadata, runtime context, working-set, and turn-summary differences where useful
  - navigation into compared sessions without losing the operator's mental model
- Implementation notes:
  - anchor comparison in persisted lineage and snapshot data, not transcript similarity heuristics
  - keep compare views useful for triage without replacing raw transcript and event inspection
  - preserve branch creation semantics from the backend; the browser should not invent valid fork points
- Tests and validation included in task:
  - component and store tests for lineage rendering, compare target loading, compare reset, and invalid target handling
  - manual validation with forked session fixtures
- Done when:
  - the SPA makes session ancestry and branch comparison materially easier than the legacy dashboard

### GBX-452: Surface Replay, Eval, Context-Drift, And Verification Cues In The SPA

- Status: `TODO`
- Depends on: `GBX-442`, `GBX-451`, `GBX-245`, `GBX-343`
- Goal: connect the operator console to Glassbox's replay and eval discipline without making the browser the only debugging surface
- Deliverables:
  - UI surfaces for replay or eval drift cues already available through snapshot/runtime-context/artifact metadata
  - verification summary panel or session-level cues for relevant retained eval artifacts where available
  - context-drift and working-set provenance presentation that helps operators inspect likely causes quickly
  - links or copyable paths to detailed artifacts when the backend exposes safe local references
- Implementation notes:
  - keep replay and eval evidence grounded in existing artifacts and summaries
  - do not make the SPA run deterministic replay itself; the CLI and backend workflows remain authoritative
  - distinguish advisory verification cues from session runtime health
- Tests and validation included in task:
  - component tests for drift cues, provenance summaries, missing-artifact states, and advisory-versus-blocking labels
  - manual validation with existing replay/eval fixtures where possible
- Done when:
  - the SPA gives useful first-look verification and drift context while preserving the existing CLI/artifact workflow for detailed replay analysis

---

## Phase 46: Testing, CI, And Quality Gates

### GBX-460: Establish Frontend Unit, Component, And Integration Test Stack

- Status: `TODO`
- Depends on: `GBX-410`, `GBX-430`, `GBX-440`
- Goal: replace the legacy Node test-runner pattern with frontend-native tests that scale with the SPA
- Deliverables:
  - Vitest or equivalent unit/component test setup
  - React Testing Library or equivalent component harness
  - fixture strategy for generated API types, snapshots, SSE events, aggregate sessions, and error responses
  - test scripts wired through `pnpm --dir frontend test`
  - documentation for writing focused frontend tests
- Implementation notes:
  - preserve the spirit of the current frontend tests: reducers, render behavior, transport, and browser orchestration should remain separately testable
  - keep fixtures realistic but small enough to maintain
  - avoid over-mocking generated types in a way that drifts from backend contracts
- Tests and validation included in task:
  - initial frontend test suite covering at least reducers, transport helpers, store actions, and core components
  - CI-compatible test command
- Done when:
  - SPA behavior has a maintainable frontend-native test harness that replaces the old plain-JS test style for new work

### GBX-461: Add Playwright Coverage For Critical Operator Workflows

- Status: `TODO`
- Depends on: `GBX-411`, `GBX-441`, `GBX-442`, `GBX-450`
- Goal: protect the high-value browser workflows through real-page tests
- Deliverables:
  - Playwright setup under `frontend/` or a clearly documented repository test location
  - tests for loading `/app`, browsing queues, opening a session, receiving live SSE updates, submitting a prompt, answering a question, resolving an approval, and creating a fork
  - screenshot or trace retention policy for failures that is useful but low churn
  - seeded backend fixture strategy that remains deterministic
- Implementation notes:
  - use deterministic backend fixtures and fake model behavior rather than live provider calls
  - keep the first Playwright suite focused on critical user workflows, not exhaustive visual assertions
  - include mobile or narrow viewport coverage for the console shell once the layout stabilizes
- Tests and validation included in task:
  - `pnpm --dir frontend test:e2e` or equivalent command
  - integration with FastAPI test server or launched local server in a deterministic mode
- Done when:
  - the SPA's most important operator workflows are protected by real browser tests

### GBX-462: Integrate Frontend Checks Into Local And Push-Time Validation

- Status: `TODO`
- Depends on: `GBX-410`, `GBX-460`
- Goal: make the frontend quality gates part of the normal repository workflow
- Deliverables:
  - pre-commit or local validation integration for frontend lint, typecheck, tests, and build at the right scope
  - GitHub Actions or existing push workflow updates for `pnpm` setup and frontend validation
  - documentation for when to run frontend-only versus full-repo validation
  - artifact handling for frontend test failures where useful
- Implementation notes:
  - keep validation strict enough to prevent stale generated types or broken static export from landing
  - avoid making every small Python-only change pay the full browser e2e cost unless the repository deliberately chooses that tradeoff
  - keep deterministic replay/eval gates conceptually separate from frontend unit and build gates
- Tests and validation included in task:
  - manual validation of local hooks or documented local validation commands
  - push workflow validation on a branch or equivalent safe path
- Done when:
  - frontend checks are a first-class part of repository validation rather than an optional side command

---

## Phase 47: Packaging, Migration Flip, And Legacy Removal

### GBX-470: Define And Enforce The Dashboard Parity Gate

- Status: `TODO`
- Depends on: `GBX-441`, `GBX-442`, `GBX-450`, `GBX-451`, `GBX-460`
- Goal: decide when the SPA is ready to replace the legacy dashboard root
- Deliverables:
  - parity checklist covering session index, aggregate console, selected-session inspector, live SSE, historical states, approvals, questions, prompts, forks, lineage, compare, runtime context, metrics, active tools, live output, event log, projection health, and error handling
  - automated test mapping for each parity requirement
  - manual validation checklist for representative real operator sessions
  - explicit known-gaps list if any non-blocking differences remain
- Implementation notes:
  - parity does not mean pixel-for-pixel similarity; it means no supported operator workflow is lost
  - treat improved UX as a requirement, but do not use polish as a reason to skip behavioral parity
  - keep the legacy route until this gate is satisfied
- Tests and validation included in task:
  - frontend unit/component/e2e coverage mapped to the checklist
  - backend integration tests for any API behavior tightened during migration
  - manual validation of co-hosted, standalone, and daemon-backed dashboard paths
- Done when:
  - the project has objective evidence that the SPA can become the default dashboard without regressing supported workflows

### GBX-471: Flip The Default Dashboard Route From Legacy Static Assets To The SPA

- Status: `TODO`
- Depends on: `GBX-470`
- Goal: make the Next.js SPA the default dashboard served at `/` while retaining a temporary legacy escape hatch
- Deliverables:
  - FastAPI route update so `/` serves the built SPA shell
  - temporary legacy route such as `/legacy` for the old dashboard during one migration window
  - updates to CLI/dashboard URLs so co-hosted and standalone workflows point at the SPA by default
  - docs updates for dashboard usage and troubleshooting
- Implementation notes:
  - keep direct `?session=...` links working after the flip
  - make missing frontend assets fail with developer-friendly guidance, not a silent blank page
  - preserve `/app` as an alias or redirect only if it helps migration clarity
- Tests and validation included in task:
  - HTTP integration tests for `/`, direct session deep links, static assets, and temporary legacy route
  - frontend e2e tests against the FastAPI-served production build
  - manual validation of `glassbox session chat` and `glassbox dashboard serve` URLs
- Done when:
  - the Next.js SPA is the default Glassbox dashboard and the legacy dashboard remains available only as a temporary fallback

### GBX-472: Remove Legacy Dashboard Assets And Tests After The Migration Window

- Status: `TODO`
- Depends on: `GBX-471`
- Goal: complete the migration by deleting the old hand-rolled dashboard implementation once the SPA has proven stable
- Deliverables:
  - removal of legacy static JavaScript, CSS, HTML, and Node test files that are no longer used
  - removal or replacement of `tests/test_frontend_unit.py` if it only exists to run legacy plain-JS tests
  - FastAPI static-serving simplification after `/legacy` is retired
  - docs cleanup so the no-framework dashboard boundary document is removed, archived, or clearly marked historical
- Implementation notes:
  - do not delete backend APIs or fixtures still used by the SPA tests
  - preserve any useful legacy fixtures by porting them to the frontend test harness first
  - perform this task only after at least one milestone of SPA-default usage or an explicitly accepted shorter migration window
- Tests and validation included in task:
  - full frontend validation
  - full relevant Python web/dashboard validation
  - manual smoke test of the default dashboard route after legacy removal
- Done when:
  - the repository no longer carries two dashboard implementations and all remaining frontend code belongs to the TypeScript SPA path

### GBX-473: Package The SPA As Part Of The Python Distribution

- Status: `TODO`
- Depends on: `GBX-471`
- Goal: ensure the production dashboard works from installed Python packages without requiring users to build frontend assets locally
- Deliverables:
  - packaging configuration that includes built SPA static assets in source and wheel distributions when release artifacts are prepared
  - release documentation for building, validating, and publishing packages with frontend assets
  - validation that installed `glassbox dashboard serve` can serve the SPA without a Node environment
  - stale-asset detection or release checklist entry to prevent packaging mismatched frontend builds
- Implementation notes:
  - ordinary runtime users should not need `pnpm` or Node to open the packaged dashboard
  - contributors may need Node for frontend development, tests, and release builds
  - keep package size visible and intentional as frontend assets grow
- Tests and validation included in task:
  - package build/install smoke test in a clean environment where practical
  - dashboard HTTP smoke test against installed package assets
  - release checklist review
- Done when:
  - a packaged Glassbox release includes and serves the SPA dashboard reliably through the existing Python command surface

---

## Recommended Build Order For The First Usable SPA Vertical Slice

If an agent wants the fastest path to a demonstrable but architecturally correct SPA slice, the recommended order is:

1. `GBX-400` and `GBX-401`
2. `GBX-410` through `GBX-412`
3. `GBX-420` through `GBX-422`
4. `GBX-430` through `GBX-432`
5. `GBX-440` and `GBX-441`
6. `GBX-442` and `GBX-450`
7. `GBX-460` and selected Playwright coverage from `GBX-461`
8. `GBX-470` once parity is realistically assessable

That yields:

- a reproducible Next.js TypeScript workspace
- generated API types from FastAPI
- typed HTTP and SSE transport
- Zustand-backed console state
- a real `/app` operator console shell
- selected-session inspection and core actions
- enough validation to decide when to replace the legacy dashboard

## Explicit Non-Goals For Initial SPA Execution

Do not spend time on these until the migration is materially complete:

- requiring a production Node server for dashboard use
- moving canonical session state into browser-only storage
- adding authentication, remote tenancy, or hosted cloud assumptions
- replacing deterministic replay or eval workflows with browser-side logic
- browser-native code editing as a primary workflow
- broad visual redesigns that do not improve operator scan speed, intervention, or trust
- deleting the legacy dashboard before the parity gate is satisfied

## Success Criteria For The Frontend SPA Migration

The SPA migration is on track when all of the following are true:

- a contributor can run and build the frontend through `pnpm` with strict TypeScript
- TypeScript API types are generated from the live FastAPI OpenAPI contract
- FastAPI can serve the built SPA without a Node process in production
- `/app` provides a useful multi-session operator console before `/` is flipped
- live SSE state, historical snapshots, projection health, and runtime ownership remain visibly distinct
- prompts, answers, approvals, denials, and forks work from the SPA through existing backend semantics
- lineage, compare, runtime context, working set, and drift cues are easier to inspect than in the legacy dashboard
- frontend validation is part of normal local and push-time quality gates
- the old hand-rolled dashboard is removed only after the SPA is the proven default
