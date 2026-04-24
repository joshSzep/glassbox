# Glassbox Refactor v1 Tasks

For the docs hub and operator guides, start at [README.md](./README.md). This file is the refactor task graph for decomposing oversized modules and repairing the architectural seams identified in the current v1 baseline.

## Purpose

This document defines a behavior-preserving refactor roadmap for the current Glassbox codebase.

It is written in the same execution style as [tasks-v1.md](./tasks-v1.md) and [tasks-v2.md](./tasks-v2.md): explicit dependencies, small vertical slices, concrete deliverables, and quality requirements attached directly to the work.

This roadmap is not a product-feature roadmap. It exists to make the current shipped architecture easier to evolve by:

- reducing oversized source files
- repairing cross-cutting architectural duplication
- clarifying module boundaries between runtime, store, CLI, replay, and web layers
- preserving the event-sourced source-of-truth model while improving maintainability

The highest-priority work in this file addresses architectural issues first. File splits should follow those boundary repairs rather than happening as cosmetic moves.

## Refactor Direction

The current v1 architecture is coherent, but several implementation surfaces have accumulated multiple responsibilities in one file.

This refactor plan should optimize for six outcomes:

- one shared model-loop architecture for live turns and replay
- one shared snapshot and query-shaping path for CLI and web consumers
- a clearer store boundary between schema, event-log operations, and projection logic
- smaller runtime modules with explicit ownership of context building, turn resumption, and artifact capture
- smaller CLI and dashboard modules with better separation between state, transport, rendering, and formatting
- stronger boundary guardrails so the same coupling does not re-accumulate

The refactor thesis is:

- keep `events` as the canonical source of truth
- preserve existing operator-visible behavior unless a task explicitly says otherwise
- prefer extraction and redirection over rewrites
- add characterization coverage before moving logic that is easy to regress
- improve architectural seams before optimizing file size mechanically

## Agent Execution Rules

These rules apply to every task in this file.

1. Respect dependency order. Do not start a task until its dependencies are complete unless the task explicitly says it can proceed in parallel.
2. Preserve current behavior by default. Refactor tasks should not intentionally change CLI semantics, snapshot payloads, replay outcomes, or dashboard workflows unless the task explicitly includes that contract change.
3. Treat `events` as the canonical source of truth. New query services, helpers, and UI projections remain derived from canonical events and existing projection tables.
4. Repair architectural duplication before splitting files mechanically. If two modules share control flow or data shaping, extract the shared boundary first.
5. Prefer extractions with thin compatibility shims over broad rewrites. Keep diffs incremental and executable.
6. Every refactor task automatically includes:
   - automated tests for the moved or extracted behavior where practical
   - `ruff` formatting and lint compliance
   - `ty` typecheck compliance for touched code
   - documentation updates when public module boundaries or architecture references change materially
7. If a refactor task changes a system boundary described in [architecture.md](./architecture.md) or [database.md](./database.md), update the relevant doc before or alongside the code change.
8. Do not invent new framework layers or abstractions unless they remove a real current coupling in the codebase.

## Completion Contract For Any Task

A task is complete only when all of the following are true:

- the implementation exists in the intended module boundary
- automated tests covering the touched behavior exist and pass
- lint, formatting, and type checks pass for the touched slice
- compatibility shims, if any, are either justified explicitly or tracked by a follow-up task in this file
- docs are updated if the refactor changes documented architecture, import surfaces, or operator-visible outputs

## Suggested Status Markers

If an agent updates this document later, use one of these markers next to task IDs:

- `TODO`
- `IN_PROGRESS`
- `BLOCKED`
- `DONE`

## Expected Repository Targets

These are the main implementation areas referenced below:

```text
src/glassbox/
    cli/
    core/
    runtime/
    llm/
    tools/
    store/
    web/
    services/
tests/
docs/
```

## Recommended Validation Commands

Use the narrowest viable validation after each task, but the baseline validation pattern for completed work should be:

```bash
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run pytest
```

During incremental refactor work, use narrower commands when possible:

```bash
uv run pytest tests/unit/test_specific_module.py
uv run pytest tests/integration/test_specific_flow.py
uv run ruff check src/glassbox/path.py tests/path_test.py
uv run ty check src/glassbox/path.py
```

## Milestone Map

The intended refactor milestone order is:

1. architectural boundary repairs
2. runtime and store decomposition
3. CLI and session-query decomposition
4. dashboard frontend decomposition
5. replay and eval/reporting decomposition
6. boundary guardrails and refactor closeout

Each phase below corresponds to one concrete refactor milestone.

## Task Graph

---

## Phase 40: Architectural Boundary Repairs

### GBX-R100: Define Refactor Boundary Map And Behavior-Preservation Contract

- Status: `DONE`
- Depends on: `GBX-132`, `GBX-185`
- Goal: define the intended runtime, store, CLI, replay, and web module boundaries before moving logic across files
- Deliverables:
  - architecture note describing target boundaries for turn execution, replay execution, snapshot shaping, store internals, CLI command handling, and dashboard frontend modules: [refactor-boundaries.md](./refactor-boundaries.md)
  - explicit non-goals for this refactor pass so behavior-preserving tasks do not silently become feature work
  - dependency-direction rules between `runtime`, `store`, `services`, `cli`, and `web`
  - identification of current compatibility shims that are acceptable temporarily versus ones that must be removed during this roadmap
- Implementation notes:
  - keep this grounded in current code paths rather than aspirational platform design
  - document which current oversized modules are large because of mixed responsibility versus legitimately large data-model surfaces
  - treat this task as the architecture source of truth for the rest of the refactor roadmap
- Tests and validation included in task:
  - architecture and doc review against the current implementation in `runtime`, `store`, `cli`, and `web`
  - manual verification that each later task in this file maps cleanly onto an explicit target boundary
- Done when:
  - the repo has a clear, code-aligned refactor boundary map that subsequent extraction tasks can follow without reopening architectural scope repeatedly

### GBX-R101: Extract Shared Model-Loop Boundary For Live Turns And Replay

- Status: `DONE`
- Depends on: `GBX-R100`
- Goal: remove duplicated model-loop control flow between live turn execution and replay by introducing one shared execution boundary
- Deliverables:
  - shared model-loop abstraction used by both [turn_engine.py](./../src/glassbox/runtime/turn_engine.py) and [replay.py](./../src/glassbox/runtime/replay.py): [model_loop.py](./../src/glassbox/runtime/model_loop.py)
  - explicit interfaces for conversation state, tool-call continuation, streamed assistant deltas, and suspension points
  - compatibility path that preserves existing replay outcomes and live event ordering during migration
- Implementation notes:
  - keep `TurnEngine` responsible for runtime lifecycle and event emission, not generic loop mechanics
  - keep replay responsible for deterministic inputs and outcome classification, not its own bespoke copy of the loop
  - preserve current event ordering and replay mismatch semantics unless a follow-up task explicitly changes them
- Tests and validation included in task:
  - integration regression tests for live turn execution and replay result classification
  - focused tests proving shared loop logic handles plain turns, tool calls, approval suspension, and `ask_user` suspension in both modes
- Done when:
  - live turn execution and replay share one explicit model-loop boundary and behavior remains regression-covered

### GBX-R102: Introduce Shared Session Snapshot And Query Service

- Status: `DONE`
- Depends on: `GBX-R100`
- Goal: centralize session snapshot shaping and next-action summaries so CLI and web consumers stop rebuilding parallel views of the same state
- Deliverables:
  - runtime-level query or snapshot service for session summaries, session snapshots, fork capability, next-action summaries, and runtime-context snapshots: [session_queries.py](./../src/glassbox/runtime/session_queries.py)
  - migration of web session routes and CLI status-style reporting onto the shared service boundary
  - compatibility coverage for existing HTTP snapshot payloads and CLI summary output where behavior is intended to remain stable
- Implementation notes:
  - keep the service read-only and projection-backed
  - do not let HTTP response concerns leak into runtime query models
  - prefer one shaping path with small presentation adapters over parallel summary builders
- Tests and validation included in task:
  - HTTP integration tests for session index and snapshot payload stability
  - CLI integration tests for status and session summary output against seeded state
- Done when:
  - session query and snapshot shaping lives behind one explicit shared service used by both CLI and web paths

### GBX-R103: Split SQLite Store Internals Behind Stable Repository Adapters

- Status: `DONE`
- Depends on: `GBX-R100`
- Goal: separate schema/bootstrap, event-log operations, and projection application inside the store layer without changing repository behavior
- Deliverables:
  - internal store module split for schema/bootstrap, event-store reads/writes, projection application, and lineage/fork helpers under `src/glassbox/store/_sqlite_*.py`
  - existing repository adapters kept stable or migrated with small compatibility shims
  - clear internal ownership for projection rebuild and append-time projection updates
- Implementation notes:
  - preserve current repository contracts in [services/contracts.py](../src/glassbox/services/contracts.py) unless a later task changes them deliberately
  - avoid turning store helpers into a new grab-bag package; split by actual responsibility
  - keep projection logic deterministic and rebuildable from canonical events
- Tests and validation included in task:
  - integration tests for schema bootstrap, event append/read, projection rebuild, and fork-point resolution
  - regression tests proving repository adapter behavior remains unchanged after the internal split
- Done when:
  - `store` has explicit internal module boundaries and the repository layer no longer depends on one monolithic `sqlite.py`

### GBX-R104: Tighten Runtime Package Export Surface And Dependency Direction

- Status: `DONE`
- Depends on: `GBX-R100`, `GBX-R101`, `GBX-R102`, `GBX-R103`
- Goal: reduce hidden coupling caused by broad convenience re-exports and clarify which packages may depend on which internal modules
- Deliverables:
  - tightened `runtime` and `store` package export surfaces
  - removal or narrowing of convenience re-exports that obscure subsystem ownership
  - documented dependency-direction rules enforced by tests or lightweight import checks where practical
- Implementation notes:
  - do not optimize for the shortest import paths if they blur subsystem ownership materially
  - keep external ergonomics reasonable for tests and bootstrap code while making internal boundaries explicit
  - prefer a small number of stable public entry modules over many ad hoc transitive exports
- Tests and validation included in task:
  - import smoke tests for intended public package surfaces
  - targeted regression tests for bootstrap and existing integration tests that rely on the public imports
- Done when:
  - package exports make subsystem ownership clearer and new internal dependencies have an explicit shape to follow

---

## Phase 41: Runtime And Store Decomposition

### GBX-R110: Split Turn Engine Into Coordinator, Tool Execution, And Resumption Components

- Status: `DONE`
- Depends on: `GBX-R101`, `GBX-R103`
- Goal: reduce `turn_engine.py` to top-level turn coordination by extracting tool execution and suspended-turn resumption concerns
- Deliverables:
  - turn coordinator module owning session-facing turn lifecycle
  - extracted tool execution component for model-requested tool calls, artifact recording hooks, and policy-result handoff
  - extracted suspended-turn resumption component for approval and `ask_user` continuation paths
  - smaller turn-engine file with clearer ownership of event emission and failure handling
- Implementation notes:
  - keep the event contract stable while logic moves
  - preserve current failure classification and metrics recording semantics
  - do not couple the new components directly to CLI or web behaviors
- Tests and validation included in task:
  - integration tests for tool loop execution, approval resumption, `ask_user` resumption, and failed-turn handling
  - focused tests for the extracted resumption and tool-execution paths where practical
- Done when:
  - `turn_engine.py` is primarily a coordination surface and tool/resumption logic lives behind explicit collaborators

### GBX-R111: Split Context Builder Into Snapshot Builders, Working-Set Derivation, And Prompt Formatting

- Status: `DONE`
- Depends on: `GBX-R102`, `GBX-R103`
- Goal: separate structured context derivation from prompt rendering and working-set heuristics
- Deliverables:
  - extracted modules for repository/runtime/artifact snapshot builders
  - extracted working-set derivation module for candidate scoring and summarization
  - extracted prompt-formatting module for transcript, tool schema, and repository-context formatting
  - a smaller assembly layer that coordinates the builders into `TurnContext`
- Implementation notes:
  - keep context models stable unless a task explicitly changes them
  - treat working-set heuristics as their own unit of behavior with direct tests
  - avoid duplicating snapshot logic that now belongs in the shared session query service
- Tests and validation included in task:
  - unit tests for working-set prioritization and context formatting
  - regression tests for `TurnContextBuilder` output against existing fixture sessions
- Done when:
  - structured context building, working-set scoring, and prompt rendering each have an explicit module boundary

### GBX-R112: Split Replay Capture Into Manifest Models, Fingerprinting, And Recorder Layers

- Status: `TODO`
- Depends on: `GBX-R101`, `GBX-R103`
- Goal: separate replay manifest data structures and fingerprinting logic from the live-turn artifact recorder
- Deliverables:
  - extracted manifest model module used by both live capture and replay consumers
  - extracted fingerprinting and normalization helpers for enriched context and replay payloads
  - slimmer live recorder focused on capture-time orchestration and artifact writes
- Implementation notes:
  - keep manifest formats stable unless a replay-compatibility task explicitly changes them
  - avoid duplicate normalization logic between replay capture and replay execution
  - preserve existing artifact paths and event recording behavior during the split
- Tests and validation included in task:
  - replay integration tests covering manifest loading and deterministic fingerprint behavior
  - focused tests for normalization and fingerprint helpers using representative payloads
- Done when:
  - replay capture internals are decomposed into reusable manifest and fingerprint layers plus a smaller recorder component

### GBX-R113: Extract Session Query Composition From Web Route Modules

- Status: `TODO`
- Depends on: `GBX-R102`, `GBX-R110`, `GBX-R111`
- Goal: reduce `web/routes/sessions.py` to HTTP concerns by moving snapshot composition and response shaping to reusable runtime query code
- Deliverables:
  - route-local logic moved into shared query/service collaborators where appropriate
  - smaller route module focused on parameter validation, HTTP errors, and response serialization
  - explicit separation between query-domain models and HTTP response models
- Implementation notes:
  - preserve current HTTP route paths and payload shapes unless a later task changes them deliberately
  - keep FastAPI-specific logic out of shared query layers
  - favor extraction of stable shaping logic, not merely moving code line-for-line
- Tests and validation included in task:
  - HTTP integration tests for session listing, session snapshot, fork capability, and actionability summaries
  - regression tests for missing-session and invalid-input behavior
- Done when:
  - session route modules are transport-focused and shared session-query composition no longer lives inline in the route file

---

## Phase 42: CLI And Session-Query Decomposition

### GBX-R120: Split CLI Parser Construction From Command Dispatch

- Status: `TODO`
- Depends on: `GBX-R104`
- Goal: reduce `cli/__init__.py` by separating argument-parser construction from command dispatch and process-level error handling
- Deliverables:
  - dedicated parser module for subcommand registration and shared argument helpers
  - dedicated dispatch or entry module for command lookup and top-level error handling
  - compatibility-preserving `glassbox.cli:main` entrypoint
- Implementation notes:
  - keep CLI help text stable unless a task explicitly revises wording
  - avoid over-abstracting command registration beyond what current subcommand count justifies
  - preserve current import path for the script entrypoint in `pyproject.toml`
- Tests and validation included in task:
  - CLI smoke tests for help output and top-level command parsing
  - regression tests for invalid arguments and unknown commands
- Done when:
  - parser wiring and command dispatch no longer share one monolithic module body

### GBX-R121: Extract CLI Command Handlers By Workflow Family

- Status: `TODO`
- Depends on: `GBX-R120`, `GBX-R102`
- Goal: split command execution logic into smaller modules grouped by workflow rather than keeping all handlers inline in `cli/__init__.py`
- Deliverables:
  - command-handler modules for interactive session workflows, session state commands, replay/eval commands, and web-server commands
  - shared runtime-location and output-path helpers moved into small support modules where appropriate
  - preserved command behavior and exit-code semantics
- Implementation notes:
  - group handlers by operator workflow, not one file per trivial helper
  - keep command handlers thin over service/query boundaries where those now exist
  - avoid moving presentation formatting into the handlers if it can live in dedicated formatters
- Tests and validation included in task:
  - CLI integration tests for representative commands in each workflow family
  - regression tests for exit codes and key human-readable output paths
- Done when:
  - command execution logic is organized by workflow family and `cli/__init__.py` stops being the home for all CLI behavior

### GBX-R122: Extract Interactive Terminal Session Controller And Prompt Routing

- Status: `TODO`
- Depends on: `GBX-R121`, `GBX-R102`
- Goal: separate long-lived terminal session control from one-shot command handling and reporting code
- Deliverables:
  - interactive session controller module for `chat` and `attach`
  - extracted prompt-routing helpers for freeform prompts, pending-question answers, and approval-related blocked-state messaging
  - extracted prompt-context and redraw helpers grouped around interactive-session behavior
- Implementation notes:
  - preserve current interactive routing semantics and prompt redraw behavior
  - keep CLI renderer reuse intact rather than introducing a second rendering stack
  - do not move unrelated replay or status formatting into the interactive module
- Tests and validation included in task:
  - CLI integration tests for `chat`, `attach`, prompt routing, and blocked interactive states
  - renderer-related regression tests for streamed output and prompt coordination
- Done when:
  - interactive terminal control has its own module boundary and no longer depends on the general CLI entry module for most of its logic

### GBX-R123: Extract CLI Status, Replay, And Eval Report Formatting

- Status: `TODO`
- Depends on: `GBX-R121`, `GBX-R122`
- Goal: separate human-readable and machine-readable reporting from command control flow
- Deliverables:
  - formatter modules for session status summaries, replay reports, eval suite reports, and coverage/baseline summaries
  - compatibility coverage for stable output lines where existing tests assert them
  - slimmer command handlers that delegate report construction instead of building strings inline
- Implementation notes:
  - keep JSON output payload shapes stable unless a task explicitly revises them
  - prefer formatter modules that consume typed query/result models rather than repositories directly
  - do not create a generic formatting framework if a few focused modules are sufficient
- Tests and validation included in task:
  - CLI integration tests for status, replay, and eval output
  - regression tests for JSON-mode payloads and replay exit-code mapping
- Done when:
  - reporting concerns are separated from CLI control flow and the command handlers read as orchestration rather than string assembly

---

## Phase 43: Dashboard Frontend Decomposition

### GBX-R130: Define Dashboard Frontend State, View, And Transport Boundaries

- Status: `TODO`
- Depends on: `GBX-R102`, `GBX-R113`
- Goal: define the intended boundaries for dashboard reducer logic, pane rendering, DOM orchestration, and transport concerns before splitting the large frontend files
- Deliverables:
  - frontend architecture note covering reducer slices, pane renderer groups, transport/actions, and DOM-binding responsibilities
  - explicit contract for which logic remains pure and side-effect free versus browser- or network-bound
  - migration plan for preserving current frontend tests during the split
- Implementation notes:
  - keep the current simple no-framework frontend architecture unless a stronger justification appears
  - optimize for testable pure modules first, not for introducing a client framework
  - align frontend boundaries with existing approval and interaction action helpers where possible
- Tests and validation included in task:
  - frontend test review against current reducer, renderer, and app-entry coverage
  - manual verification that planned module splits map cleanly onto the tested behaviors
- Done when:
  - the dashboard frontend has a clear target module map that later extraction tasks can follow incrementally

### GBX-R131: Split Dashboard State Reducer Into Snapshot, Live-Event, And Interaction Slices

- Status: `TODO`
- Depends on: `GBX-R130`
- Goal: reduce `state.js` by separating snapshot hydration, incremental event reduction, and UI submission state handling
- Deliverables:
  - extracted modules for snapshot normalization and hydration
  - extracted reducer modules for live event application and stream-state transitions
  - extracted interaction-state helpers for approvals, session messages, answers, and fork submission flow
  - preserved pure reducer contract for frontend unit tests
- Implementation notes:
  - keep reducer logic side-effect free
  - preserve current state shape unless a task explicitly changes it and updates dependent tests
  - avoid splitting purely by file size; split by stable state transition responsibility
- Tests and validation included in task:
  - frontend unit tests for snapshot hydration, event reduction, approval flow, stream reconnection, and interaction submissions
  - regression tests ensuring the combined dashboard state remains compatible with existing renderers and app wiring
- Done when:
  - `state.js` is decomposed into smaller pure modules with explicit responsibility boundaries

### GBX-R132: Split Dashboard Pane Rendering By Pane Family

- Status: `TODO`
- Depends on: `GBX-R130`, `GBX-R131`
- Goal: reduce `render.js` by grouping renderers into coherent pane families rather than one broad rendering file
- Deliverables:
  - extracted renderer modules for session-browser and summary panes, transcript and live-output panes, approvals and composer panes, and metrics/tool/event panes
  - shared small HTML utility helpers retained in one focused module where justified
  - preserved pure renderer contract for frontend tests
- Implementation notes:
  - keep renderer inputs as state snapshots or small typed fragments, not direct DOM nodes
  - avoid duplicating utility helpers across pane modules
  - preserve current HTML structure where tests or CSS rely on it
- Tests and validation included in task:
  - frontend rendering tests for each pane family
  - regression tests for multi-pane dashboard rendering against representative state fixtures
- Done when:
  - pane rendering is organized by UI responsibility and no longer concentrated in one general-purpose renderer file

### GBX-R133: Split Dashboard App Entry Into Transport, Controller, And DOM-Binding Layers

- Status: `TODO`
- Depends on: `GBX-R130`, `GBX-R131`, `GBX-R132`
- Goal: separate dashboard startup, network I/O, SSE lifecycle, and DOM event binding from the remaining browser app orchestration code
- Deliverables:
  - extracted transport helpers for snapshot fetches and SSE connection lifecycle
  - extracted controller logic for state transitions and session selection flow
  - smaller app-entry module focused on bootstrapping the composed pieces
- Implementation notes:
  - keep the browser entrypoint framework-free and operationally simple
  - preserve existing deep-linking and session selection semantics
  - avoid making DOM-binding code responsible for reducer or transport logic
- Tests and validation included in task:
  - frontend integration tests for dashboard startup, session selection, and reconnect flows
  - regression tests for approval and interaction actions under mocked fetch/SSE behavior
- Done when:
  - dashboard startup and browser orchestration are decomposed into explicit transport, controller, and binding layers

---

## Phase 44: Replay And Eval Reporting Decomposition

### GBX-R140: Split Replay Execution, Bundle I/O, Normalization, And Triage

- Status: `TODO`
- Depends on: `GBX-R101`, `GBX-R112`
- Goal: reduce `replay.py` by separating bundle loading/export, replay execution, normalized-state comparison, and outcome triage
- Deliverables:
  - extracted bundle I/O layer for loading and exporting replay bundles
  - extracted replay execution layer for deterministic runtime playback
  - extracted normalization and mismatch-comparison helpers
  - extracted triage builder for human-readable replay failure classification
- Implementation notes:
  - preserve current replay result taxonomy and bundle version semantics unless a task explicitly changes them
  - keep replay execution deterministic and isolated from live runtime side effects
  - avoid reintroducing duplication with the shared model-loop boundary established earlier
- Tests and validation included in task:
  - integration tests for replaying recorded sessions and exported bundles
  - focused regression tests for mismatch classification and triage payload construction
- Done when:
  - replay internals are split by responsibility and replay behavior remains stable under the existing integration suite

### GBX-R141: Split Eval Summary And Release-Signoff Reporting By Output Concern

- Status: `TODO`
- Depends on: `GBX-R140`
- Goal: reduce `eval_summary.py` by separating summary payload construction, release-signoff aggregation, and annotation formatting
- Deliverables:
  - extracted summary-payload builder for suite results
  - extracted release-signoff report builder and profile/case aggregation helpers
  - extracted annotation-formatting utilities for GitHub Actions or equivalent automation outputs
- Implementation notes:
  - preserve current summary and annotation behavior unless a task explicitly revises the operator contract
  - keep reporting layers consuming typed eval result models rather than filesystem paths or raw JSON directly where possible
  - avoid collapsing summary and formatting concerns into one builder again during migration
- Tests and validation included in task:
  - unit and integration tests for suite-summary payloads, release-signoff aggregation, and annotation formatting
  - regression tests for existing eval-summary output consumed by docs or automation flows
- Done when:
  - eval reporting is split into explicit aggregation and output-formatting layers with stable regression coverage

---

## Phase 45: Boundary Guardrails And Refactor Closeout

### GBX-R150: Add Architectural Characterization Coverage For Refactor-Sensitive Seams

- Status: `TODO`
- Depends on: `GBX-R110`, `GBX-R113`, `GBX-R123`, `GBX-R133`, `GBX-R141`
- Goal: protect the new boundaries against accidental behavioral drift after the main refactor extractions land
- Deliverables:
  - characterization tests for live turn event ordering, replay result stability, session snapshot shaping, CLI status/report output, and dashboard reducer/render composition
  - fixture or helper consolidation where repeated high-signal regression setups currently exist
  - explicit identification of refactor-sensitive behaviors that should remain stable across later work
- Implementation notes:
  - prefer tests around externally visible behavior and important internal seams, not line-for-line implementation structure
  - use the existing integration suite as the foundation and add narrow characterization coverage only where the refactor creates real regression risk
  - do not turn this into a broad testing rewrite
- Tests and validation included in task:
  - this task is itself the main coverage addition, but it still requires lint and typecheck on touched tests and helpers
  - full targeted regression runs for the runtime, store, CLI, replay, and frontend areas affected by the refactor
- Done when:
  - the major extracted seams are guarded by stable characterization coverage rather than relying only on incidental integration tests

### GBX-R151: Add Lightweight Boundary Guardrails For File Growth And Import Direction

- Status: `TODO`
- Depends on: `GBX-R104`, `GBX-R150`
- Goal: reduce the chance that oversized files and blurred subsystem dependencies reappear after the refactor roadmap lands
- Deliverables:
  - lightweight import-boundary or architecture tests where practical
  - documented file-ownership and module-boundary guidance for the largest subsystems
  - optional size or complexity guardrails only if they can be kept low-friction and reviewable
- Implementation notes:
  - prefer a small number of meaningful guardrails over noisy metrics that are easy to ignore
  - keep the guardrails aligned with real subsystem boundaries established earlier in this file
  - do not block routine work on arbitrary file-count or micro-abstraction rules
- Tests and validation included in task:
  - targeted tests or checks for import-direction rules and intended public entry modules
  - manual validation that any size or complexity guardrails are understandable and actionable for maintainers
- Done when:
  - the codebase has lightweight enforcement for the most important architectural boundaries established by this roadmap

### GBX-R152: Update Architecture, Database, And Docs Hub References For The Refactored Shape

- Status: `TODO`
- Depends on: `GBX-R150`, `GBX-R151`, `GBX-121`
- Goal: leave the repository with documentation that matches the post-refactor module boundaries and explains the rationale for the new shape
- Deliverables:
  - updates to [architecture.md](./architecture.md) describing the refined runtime, query, store, and replay boundaries
  - updates to [database.md](./database.md) if store-internal decomposition or migration notes changed materially
  - docs-hub references for the refactor roadmap and any updated implementation guidance
  - cleanup of temporary compatibility notes that are no longer true after the roadmap completes
- Implementation notes:
  - document architectural boundaries and reasoning, not just file moves
  - keep the docs explicit about what changed internally versus what remained operator-visible behavior
  - remove stale descriptions of monolithic modules where the refactor eliminated them
- Tests and validation included in task:
  - doc review against the final runtime, store, CLI, replay, and dashboard module layout
  - manual verification that the docs hub points to the right implementation references after the refactor completes
- Done when:
  - the code-aligned docs describe the refactored module boundaries accurately and the docs hub reflects the new roadmap
