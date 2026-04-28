# Glassbox v6 Tasks

For the docs hub and operator guides, start at [README.md](./README.md). This file is the v6 task graph for turning the completed v2 runtime, v3 SPA, v4 operator console, and v5 terminal client into a release-hardened local-first agent product.

## Purpose

This document defines Glassbox v6: the release-hardening evolution after the v5 full-screen terminal client in [tasks-v5.md](./tasks-v5.md).

It is written in the same execution style as [tasks-v1.md](./tasks-v1.md), [tasks-v2.md](./tasks-v2.md), [tasks-v3.md](./tasks-v3.md), [tasks-v4.md](./tasks-v4.md), and [tasks-v5.md](./tasks-v5.md): explicit dependencies, small vertical slices, concrete deliverables, and quality requirements attached directly to the work.

The v2 through v5 work established the durable local runtime, SQLite event store, rebuildable projections, daemon ownership model, static-exported dashboard, attention-first operator console, full-screen terminal chat, replay/eval workflows, package smoke, and release gates. That foundation is strong enough that v6 should not be another broad feature expansion.

The v6 goal is to make Glassbox dependable under real local use: cancellation should be real, live streams should be resilient, release artifacts should be reproducible, provider canaries should be deliberate, accessibility review should be evidence-backed, and the final release candidate should have one objective gate that operators and contributors can trust.

## Product Direction

The v6 work should optimize for seven outcomes:

- real backend cancellation for in-flight model calls and tool executions
- resilient live event delivery across terminal, dashboard, daemon, and reconnect paths
- a single release-hardening gate that verifies Python, frontend, eval, packaging, and installed-package behavior
- repeatable provider-canary validation that stays separate from deterministic release-blocking evals
- stronger observability and recovery guidance for runtime, projection, transport, and verification failures
- accessibility and manual UX evidence that complements automated semantic tests
- public-release documentation that names supported workflows, known gaps, and non-goals without relying on task docs

The v6 thesis is:

- preserve the local-first product boundary
- preserve canonical events as the source of truth
- preserve the TUI as the primary chat surface and the dashboard as the paired operator console
- deepen reliability before adding new interaction surfaces
- treat release evidence as a first-class product artifact
- keep deterministic replay/eval blocking and live-provider canaries advisory unless explicitly promoted later
- avoid cloud, multi-tenant, marketplace, or remote-collaboration scope in this milestone

## Current Baseline Before V6 Execution

Treat the following as the starting point for every task in this document:

- [tasks-v2.md](./tasks-v2.md), [tasks-v3.md](./tasks-v3.md), [tasks-v4.md](./tasks-v4.md), and [tasks-v5.md](./tasks-v5.md) all mark their task graphs as complete
- `glassbox session chat` uses the Textual full-screen TUI by default in supported terminals and falls back to plain mode in unsupported contexts
- `glassbox session attach` can reopen persisted local sessions or attach to daemon-owned live sessions through HTTP plus SSE
- the dashboard is a Next.js static export served by FastAPI and packaged into the Python distribution
- live browser and terminal clients consume backend snapshots plus `/sessions/{session_id}/events` SSE tails
- `glassbox daemon start|status|stop` provides workspace-scoped runtime ownership with metadata and health paths under `.glassbox/`
- the SQLite store uses canonical events plus rebuildable projections and schema migrations through version 6
- replay and eval support portable bundles, repository-owned cases, deterministic profiles, recommendation output, and release reports
- `scripts/validate_v5_terminal_release_gate.py` already runs Python format, lint, typecheck, focused TUI tests, full Python tests, deterministic eval smoke, package build, and installed-wheel terminal smoke
- the v5 release gate explicitly accepts several known non-blocking gaps that v6 should revisit, especially backend cancellation, manual-only terminal visual review, real-provider validation, terminal capability limits, and screen-reader review

## v6 Release Hardening Findings

Treat these findings as evidence that should steer the first implementation slices:

- interruption is honest in the TUI, but backend cancellation of in-flight model or tool work is not implemented
- stream reconnection has a clear SSE `after` cursor model, but runtime transport resilience and transport observability should be tested under drop, lag, reconnect, and daemon-stop scenarios
- the package release path depends on fresh frontend static assets, generated API types, wheel/sdist inclusion, and installed-package smoke; those checks should be one command rather than tribal knowledge
- deterministic evals are strong, but real-provider behavior still depends on manual validation when credentials are present
- accessibility and terminal visual validation are documented as manual activities, but the evidence artifact shape is not yet as formal as the v4 screenshot archive
- observability already reports runtime, projection, event transport, and retained eval state, but the same next-action guidance should be visible in release artifacts and operator docs
- the repo has many mature docs; v6 should consolidate supported release posture rather than scatter new operational promises across task files

## Agent Execution Rules

These rules apply to every task in this file.

1. Respect dependency order. Do not start a task until its dependencies are complete unless the task explicitly says it can proceed in parallel.
2. Preserve the event-sourced source-of-truth rule. Cancellation, transport, observability, and release evidence must be recorded or derived through explicit backend contracts rather than hidden UI-only state.
3. Preserve local-first operation. Do not introduce a hosted control plane, remote multi-user authority, or network service dependency for v6 release readiness.
4. Preserve deterministic release blocking. Live-provider canaries may be advisory unless a task explicitly promotes one into a blocking release surface with stable credentials and failure policy.
5. Keep the terminal and dashboard roles intact. The TUI remains the primary chat surface; the dashboard remains the deeper operator console and evidence surface.
6. Prefer root-cause reliability fixes over UI-only messaging when runtime behavior is incomplete.
7. Treat release evidence as product behavior. Any new release command should produce enough structured output or artifacts to explain what passed, what failed, and what the operator should inspect next.
8. Keep non-interactive commands scriptable. Release, observability, replay, eval, projection, backup, daemon, and package smoke workflows should remain useful in CI or clean shell environments.
9. If v6 work exposes an API mismatch, fix or document the service/API contract before encoding fragile terminal-only or browser-only workarounds.
10. Every implementation task automatically includes:
    - automated tests for new behavior
    - `ruff` formatting and lint compliance for touched Python code
    - `ty` typecheck compliance for touched Python code
    - focused `pytest` coverage for touched runtime, CLI, web, replay, eval, and terminal behavior
    - frontend lint, typecheck, tests, and build when the task touches dashboard code, generated API types, or packaged static assets
    - documentation updates when contracts, routes, commands, packaging, provider workflows, release gates, accessibility claims, or operator-visible behavior change

## Completion Contract For Any Task

A task is complete only when all of the following are true:

- the implementation exists in the intended module boundary
- automated tests covering the new behavior exist and pass
- Python lint, typecheck, and focused tests pass for touched backend and CLI code
- frontend lint, typecheck, tests, and build pass if the task touches frontend, generated API types, or web dashboard behavior
- deterministic replay/eval behavior remains stable or intentional drift is documented through the eval refresh workflow
- the task does not leave placeholder code or hidden follow-up work outside this file
- terminal behavior remains usable in supported TTY and documented fallback contexts
- the dashboard remains usable through the FastAPI-served production build path
- release and validation docs are updated if the task changes the operator-visible release posture

## Suggested Status Markers

If an agent updates this document later, use one of these markers next to task IDs:

- `TODO`
- `IN_PROGRESS`
- `BLOCKED`
- `DONE`

## Expected Repository Targets

These are the main implementation areas referenced below:

```text
pyproject.toml
scripts/
    validate_v5_terminal_release_gate.py
    validate_v6_release_gate.py
src/glassbox/
    cli/
    core/
    runtime/
    tools/
    store/
    web/
frontend/
    api/
    app/
    components/
    generated/
    stores/
    tests/
    e2e/
tests/
    integration/
    unit/
evals/
docs/
```

## Recommended Validation Commands

Use the narrowest viable validation after each task, but the baseline validation pattern for completed v6 hardening work should include:

```bash
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run pytest
uv run glassbox eval run
pnpm --dir frontend lint
pnpm --dir frontend typecheck
pnpm --dir frontend test
pnpm --dir frontend build
uv build --wheel --sdist
```

During incremental implementation, use narrower commands where possible:

```bash
uv run pytest tests/unit/test_model_loop.py tests/integration/test_turn_engine.py
uv run pytest tests/integration/test_command_tool.py tests/integration/test_daemon_runtime.py
uv run pytest tests/integration/test_web_sse_events.py tests/unit/test_runtime_transport.py
uv run pytest tests/unit/test_cli_tui_app.py tests/unit/test_cli_tui_workflows.py
uv run pytest tests/integration/test_web_session_interaction.py
uv run pytest tests/integration/test_cli_interactive_commands.py
uv run ruff check src/glassbox/runtime src/glassbox/cli tests/unit tests/integration
uv run ty check
```

When a task touches the release gate, packaging, or dashboard build path, also run:

```bash
pnpm --dir frontend api:generate
pnpm --dir frontend lint
pnpm --dir frontend typecheck
pnpm --dir frontend test
pnpm --dir frontend build
uv build --wheel --sdist
uv run python scripts/validate_v5_terminal_release_gate.py
```

Once `GBX-642` exists, use the v6 gate as the canonical full validation command:

```bash
uv run python scripts/validate_v6_release_gate.py
```

## Milestone Map

The intended v6 milestone order is:

1. release-hardening contract and validation baseline
2. real backend cancellation
3. live transport and daemon reliability
4. provider canaries, policy evidence, and context budget confidence
5. reproducible packaging and clean-environment install smoke
6. accessibility, manual QA, and evidence archive
7. v6 release candidate decision

## Task Graph

---

## Phase 64: Release-Hardening Contract And Validation Baseline

### GBX-640: Define The v6 Release-Hardening Contract

- Status: `DONE`
- Depends on: `GBX-632`
- Goal: convert the completed v2 through v5 milestones and known release gaps into one concrete v6 hardening contract
- Deliverables:
  - documentation update defining the v6 release-hardening scope, non-goals, supported workflows, and release evidence expectations
  - explicit mapping from v5 known non-blocking gaps to v6 tasks
  - explicit rule that v6 is not a cloud, multi-user, plugin-marketplace, or remote orchestration milestone
  - release-readiness checklist that names automated, manual, deterministic, and provider-canary evidence separately
  - risk register for accepted residual risks that may remain after v6
- Implementation notes:
  - start from [v5-terminal-release-gate.md](./v5-terminal-release-gate.md), [release-packaging.md](./release-packaging.md), [v2-release-candidate.md](./v2-release-candidate.md), and this task file
  - keep the contract operator-readable rather than turning it into internal engineering notes only
  - avoid reopening completed v2 through v5 decisions unless they directly block release reliability
- Tests and validation included in task:
  - docs review against implemented command help and current release scripts
  - lightweight test that docs links for the v6 contract remain discoverable if a new release document is added
- Done when:
  - contributors have one v6 hardening contract that explains what must be true before calling the next release candidate ready

Completion notes:

- Added [v6-release-hardening.md](./v6-release-hardening.md) with v6 scope, non-goals, supported workflow set, evidence classes, v5 known-gap mapping, release-readiness checklist, residual-risk register shape, and pass/fail policy.
- Preserved the local-first, event-sourced, deterministic-release-blocking boundaries while making live-provider canaries advisory by default.
- Validation: docs review against [v5-terminal-release-gate.md](./v5-terminal-release-gate.md), [release-packaging.md](./release-packaging.md), and [v2-release-candidate.md](./v2-release-candidate.md).

### GBX-641: Inventory Current Gates, Gaps, And Release Evidence

- Status: `DONE`
- Depends on: `GBX-640`
- Goal: establish a code-aligned baseline of all existing validation commands, release gates, generated artifacts, known manual checks, and missing evidence
- Deliverables:
  - inventory of Python validation, frontend validation, replay/eval validation, package build, installed smoke, daemon smoke, dashboard smoke, and manual UX/accessibility checks
  - table mapping each existing release concern to the command, test file, doc, or manual artifact that currently covers it
  - explicit list of release concerns with weak or missing coverage
  - recommendation for which checks become part of the v6 gate versus separate manual signoff
- Implementation notes:
  - include both local development validation and clean installed-wheel validation
  - distinguish deterministic checks from live-provider checks
  - do not invent a heavy CI system in this task; this is the audit that feeds the gate
- Tests and validation included in task:
  - docs review against `pyproject.toml`, `frontend/package.json`, `scripts/validate_v5_terminal_release_gate.py`, and command help
- Done when:
  - v6 implementers know exactly what validation already exists and what must be added

Completion notes:

- Added [v6-release-inventory.md](./v6-release-inventory.md) with current automated validation surfaces, manual validation surfaces, weak or missing coverage, recommended v6 gate membership, recommended manual signoff membership, and current evidence ownership.
- Reviewed the inventory against [pyproject.toml](../pyproject.toml), [frontend/package.json](../frontend/package.json), `.pre-commit-config.yaml`, [evals/profiles.json](../evals/profiles.json), [v5-terminal-release-gate.md](./v5-terminal-release-gate.md), [v4-ux-release-gate.md](./v4-ux-release-gate.md), and [release-packaging.md](./release-packaging.md).
- Validation: documentation review only; no runtime behavior changed.

### GBX-642: Add The v6 Release Gate Script

- Status: `DONE`
- Depends on: `GBX-641`
- Goal: provide one canonical command that runs the automated v6 release-hardening gate
- Deliverables:
  - `scripts/validate_v6_release_gate.py`
  - gate stages for Python format, lint, typecheck, focused cancellation tests, focused transport/daemon tests, focused TUI/dashboard workflow tests, full Python tests, deterministic eval smoke, frontend lint/typecheck/tests/build, package build, and installed-package smoke
  - structured stage labels and failure messages that make the failing area obvious
  - option or documented convention for skipping live-provider canaries when credentials are unavailable
  - tests that keep the gate script aligned with the v6 release-gate documentation
- Implementation notes:
  - reuse the v5 gate where practical instead of duplicating all subprocess logic
  - keep the gate deterministic by default
  - avoid requiring Node in installed-package smoke; Node remains a source-build requirement only
  - make the command usable from a clean checkout with `uv` and `pnpm` installed
- Tests and validation included in task:
  - unit tests for gate command inventory if command construction is factored
  - focused smoke of the gate script help or dry-run mode if added
  - `uv run ruff check scripts tests`
  - `uv run ty check`
- Done when:
  - `uv run python scripts/validate_v6_release_gate.py` is the documented automated release gate

Completion notes:

- Added `scripts/validate_v6_release_gate.py` with deterministic blocking stages for Python format/lint/typecheck, focused cancellation tests, focused transport and daemon tests, focused terminal and dashboard tests, full Python tests, deterministic eval smoke, frontend lint/typecheck/tests/build, package build, advisory provider-canary handling, dry-run output, and installed-wheel command smoke.
- Added `tests/unit/test_v6_release_gate.py` to keep the gate command inventory and dry-run behavior aligned with the v6 contract.
- Validation: `uv run pytest tests/unit/test_v6_release_gate.py`.

### GBX-643: Define Release Evidence Artifacts

- Status: `DONE`
- Depends on: `GBX-642`
- Goal: make release validation output inspectable after the command finishes instead of relying only on terminal scrollback
- Deliverables:
  - release evidence directory convention under `.glassbox/releases/` or another documented local path
  - JSON summary schema for gate stages, command lines, exit codes, start/end timestamps, environment metadata, and artifact pointers
  - retained links or paths for eval summaries, package build outputs, installed smoke logs, frontend build logs, and manual validation notes
  - CLI or script output that prints the evidence path and next actions after pass or failure
- Implementation notes:
  - keep evidence local and portable; do not add a remote upload path
  - make failure summaries useful for humans and scripts
  - avoid storing secrets or provider responses that may contain sensitive prompt content unless explicitly redacted
- Tests and validation included in task:
  - unit tests for evidence schema serialization
  - integration smoke for a small fake gate writing a summary artifact if the gate is factored for testability
  - docs review against release packaging and replay/eval report conventions
- Done when:
  - release validation leaves behind a structured local evidence trail that can be inspected or attached to a release candidate

Completion notes:

- Added [v6-release-evidence.md](./v6-release-evidence.md) with the default evidence directory, `summary.json` schema, stage record schema, related artifact pointers, provisional manual evidence manifest, redaction rules, and pass/failure use.
- Updated `scripts/validate_v6_release_gate.py` to accept `--evidence-dir`, write retained `summary.json` artifacts for dry-run, pass, and failure paths, record stage outcomes, record advisory provider-canary skips, and print the evidence summary path.
- Expanded `tests/unit/test_v6_release_gate.py` to verify dry-run evidence serialization.
- Validation: `uv run pytest tests/unit/test_v6_release_gate.py`.

### GBX-644: Update Documentation Discovery For v6

- Status: `DONE`
- Depends on: `GBX-640`, `GBX-643`
- Goal: make the v6 hardening plan and release gate discoverable from the documentation hub without requiring users to know the task file name
- Deliverables:
  - updates to [README.md](./README.md) in the docs hub for v6 task and release-gate docs
  - root README update only if the supported public release posture changes
  - guide-map additions for release hardening, package validation, and manual QA evidence
  - cross-links from release packaging, v5 gate, and v6 gate docs where appropriate
- Implementation notes:
  - keep task docs separate from operator guides
  - do not overpromise v6 outcomes before the relevant tasks are complete
- Tests and validation included in task:
  - docs link review
  - existing docs tests if present
- Done when:
  - a contributor can discover the v6 plan and gate from the docs index

Completion notes:

- Updated [README.md](./README.md) in the docs hub to link [tasks-v6.md](./tasks-v6.md), [v6-release-hardening.md](./v6-release-hardening.md), [v6-release-inventory.md](./v6-release-inventory.md), and [v6-release-evidence.md](./v6-release-evidence.md) from the start-here and deep-reference sections.
- Added v6 hardening cross-links to [v5-terminal-release-gate.md](./v5-terminal-release-gate.md) and [release-packaging.md](./release-packaging.md).
- Expanded `tests/unit/test_release_candidate_docs.py` with guardrails for v6 Phase 64 documentation discovery and cross-linking.
- Validation: `uv run pytest tests/unit/test_release_candidate_docs.py`.

---

## Phase 65: Real Backend Cancellation

### GBX-650: Define The Cancellation Contract

- Status: `DONE`
- Depends on: `GBX-640`
- Goal: define how operators request cancellation and how the runtime records, executes, reports, and replays cancellation without corrupting event-sourced state
- Deliverables:
  - architecture and interaction-model updates for cancellation semantics
  - event-model proposal for cancellation requested, cancellation acknowledged, turn cancelled, tool cancelled, and cancellation failure outcomes if new events are required
  - session and turn state rules for idle, active model call, active tool call, pending approval, pending question, reconnecting stream, completed historical, and failed states
  - explicit distinction between graceful cancellation, timeout, subprocess interruption, provider cancellation failure, and non-cancellable historical state
  - replay/eval policy for cancelled turns
- Implementation notes:
  - start from the v5 release-gate known gap rather than inventing a new UX model
  - preserve existing `TurnFailed` and `SessionCompleted` semantics unless new event types are needed for clarity
  - define how cancellation interacts with approval and `ask_user` suspension before implementing controls
- Tests and validation included in task:
  - unit tests for any new event payload models
  - docs review against TUI, dashboard, and session command behavior
- Done when:
  - cancellation has a clear backend contract that the runtime, TUI, dashboard, and replay code can implement consistently

Completion notes:

- Added [v6-cancellation-contract.md](./v6-cancellation-contract.md) defining cancellation scope, event ordering, state rules, outcome classes, and replay/eval policy.
- Updated [architecture.md](./architecture.md), [terminal-interaction-model-v5.md](./terminal-interaction-model-v5.md), and [v5-terminal-release-gate.md](./v5-terminal-release-gate.md) to point from the old v5 interruption gap to the v6 backend contract.
- Added cancellation event payload models and turn status values in `glassbox.core`, with projection handling for cancelled turn completion.
- Validation: `uv run pytest tests/unit/test_core_events.py tests/unit/test_core_types.py`.

### GBX-651: Thread Cancellation Through Turn Execution

- Status: `DONE`
- Depends on: `GBX-650`
- Goal: make the turn engine and model loop respond to a runtime cancellation request during an active turn
- Deliverables:
  - cancellation token or controller owned by the session runtime for active turns
  - `TurnEngine` support for observing cancellation during turn preparation, model calls, model-loop continuation, and resumption paths
  - `ModelLoopRunner` support for interrupting or short-circuiting active and subsequent model calls
  - persisted events that reflect the requested and final cancellation outcome
  - deterministic tests for cancellation before model call, during streaming, after a tool request, and during resumption
- Implementation notes:
  - keep cancellation scoped to one active turn unless a task explicitly defines session-wide cancellation
  - avoid relying on `asyncio` task cancellation alone if it would skip event recording or cleanup
  - make repeated cancellation requests idempotent
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_model_loop.py tests/integration/test_turn_engine.py`
  - focused tests for event ordering and final session state
  - `uv run ruff check src/glassbox/runtime tests`
  - `uv run ty check`
- Done when:
  - active turns can be cancelled in deterministic runtime tests with clear persisted outcomes

Completion notes:

- Added cooperative turn cancellation primitives in `runtime/cancellation.py` and threaded them through `ModelLoopRunner`, `TurnEngine`, and `SessionSupervisor.cancel_turn`.
- Active model calls are raced against a cancellation request so the runtime records `CancellationRequested`, `CancellationAcknowledged`, `TurnCancelled`, and `TurnCompleted(outcome="cancelled")` instead of relying on unobserved task cancellation.
- Added focused model-loop tests for cancellation before a model call and during an in-flight model call, plus a turn-engine integration test for persisted cancellation outcomes.
- Validation: `uv run pytest tests/unit/test_model_loop.py tests/integration/test_turn_engine.py` and `uv run ty check`.

### GBX-652: Make Tool Execution Cancellable

- Status: `DONE`
- Depends on: `GBX-651`
- Goal: make long-running tool execution, especially subprocess-backed command tools, respond to runtime cancellation and record useful output
- Deliverables:
  - cancellation-aware tool execution boundary in `ToolRuntime`
  - subprocess interruption behavior that terminates process groups safely where supported
  - streamed output preservation up to the cancellation point
  - classified cancellation result distinct from timeout and ordinary command failure
  - artifact and replay handling for partial outputs when cancellation occurs
- Implementation notes:
  - coordinate with existing timeout and failure-category logic in command tools
  - preserve workspace safety and approval policy semantics
  - ensure cancellation does not leave child processes running after tests complete
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_command_tool.py tests/unit/test_subprocess_classification.py`
  - cancellation test for streaming output before termination
  - platform-sensitive tests should use deterministic subprocesses and avoid sleeps where practical
- Done when:
  - cancellable tools stop reliably, preserve useful evidence, and report cancellation as an intentional runtime outcome

Completion notes:

- Threaded the active turn cancellation controller through `ToolRuntime` and subprocess-backed streaming tools.
- Added subprocess group termination with explicit `cancelled` result classification distinct from timeout and signal interruption.
- Recorded `ToolExecutionCancelled` before final tool completion and turn cancellation when a cancellation interrupts an active tool call.
- Added deterministic command-tool coverage that preserves streamed output before cancellation, plus subprocess classification coverage.
- Validation: `uv run pytest tests/integration/test_command_tool.py tests/unit/test_subprocess_classification.py` and `uv run ty check`.

### GBX-653: Expose Cancellation Through CLI, TUI, Dashboard, And API

- Status: `DONE`
- Depends on: `GBX-651`, `GBX-652`
- Goal: let operators request cancellation from every live control surface without changing the canonical runtime authority model
- Deliverables:
  - session command or existing command extension for cancelling an active turn
  - FastAPI endpoint for cancellation requests with conflict handling for non-cancellable states
  - TUI command palette and keyboard path wired to real backend cancellation instead of informational interruption only
  - dashboard action surfaced for active cancellable turns
  - plain-mode messaging updated to reflect real cancellation behavior
- Implementation notes:
  - keep mutation ownership rules intact; local mutating commands must still respect daemon ownership
  - dashboard and TUI should render cancellation pending, accepted, rejected, and completed states from backend state/events
  - copy should be honest when provider or tool cancellation cannot be guaranteed
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_cli_interactive_commands.py tests/unit/test_cli_tui_app.py tests/unit/test_cli_tui_workflows.py`
  - `uv run pytest tests/integration/test_web_session_interaction.py`
  - frontend tests for dashboard cancellation action if dashboard code changes
  - `pnpm --dir frontend typecheck` and `pnpm --dir frontend test` when applicable
- Done when:
  - users can request cancellation from terminal, dashboard, and scriptable command surfaces with consistent outcomes

Completion notes:

- Added `POST /sessions/{session_id}/cancel`, `SessionService.cancel_turn`, daemon/local interactive-client support, and a scriptable `glassbox session cancel` command.
- Wired the TUI interrupt path to backend cancellation for active turns, replacing the old informational-only interruption message when a writable runtime is available.
- Added dashboard API client/store/action-pane support for cancelling active turns, plus live SSE handling for cancellation event types.
- Validation: `uv run pytest tests/integration/test_web_session_interaction.py tests/unit/test_cli_tui_app.py` and frontend typecheck/tests.

### GBX-654: Add Cancellation Replay And Eval Semantics

- Status: `DONE`
- Depends on: `GBX-653`
- Goal: ensure cancelled turns remain inspectable, replayable where meaningful, and evaluable without being misclassified as ordinary failures
- Deliverables:
  - replay normalization support for cancellation events and cancelled final states
  - eval invariant handling for cancellation-specific outcomes
  - triage copy that distinguishes intentional cancellation from timeout, provider failure, tool failure, and behavioral drift
  - portable bundle support for sessions containing cancelled turns
  - eval case or fixture covering a cancelled turn
- Implementation notes:
  - avoid making wall-clock timing part of deterministic replay expectations
  - keep cancelled tool output and artifacts available as evidence
  - document unsupported replay scenarios if a provider-specific cancellation cannot be reproduced deterministically
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_replay_orchestrator.py tests/unit/test_replay_triage.py tests/integration/test_replay_runner.py`
  - `uv run pytest tests/unit/test_runtime_evals.py tests/unit/test_eval_recommendations.py`
  - deterministic eval smoke
- Done when:
  - cancellation no longer appears as an ambiguous failure in replay, eval, or release evidence

Completion notes:

- Added cancellation snapshots to normalized replay comparison and eval invariants, so cancellation evidence can drift independently from transcript, tool, and final-state behavior.
- Allowed cancelled turn-output manifests in replay bundles, including incomplete model-call fixtures, and replay cancelled bundles to their recorded baseline because operator cancellation timing is not deterministic provider behavior.
- Added triage copy that treats matching cancelled turns as preserved cancellation evidence rather than timeout, provider, tool, or generic replay failure.
- Added advisory repository eval fixture `cancellation.cancelled-turn` plus coverage/impact metadata for the cancellation capability.
- Validation: `uv run pytest tests/unit/test_replay_orchestrator.py tests/unit/test_replay_triage.py tests/integration/test_replay_runner.py tests/unit/test_runtime_evals.py tests/unit/test_eval_recommendations.py`, `uv run glassbox eval run cancellation.cancelled-turn`, and `uv run glassbox eval run --profile commit-smoke`.

### GBX-655: Harden Cancellation Under Attach And Daemon Ownership

- Status: `DONE`
- Depends on: `GBX-653`, `GBX-654`
- Goal: prove cancellation works when the live runtime owner is a daemon and the operator is attached through terminal or browser clients
- Deliverables:
  - daemon-backed cancellation integration tests
  - attach-path behavior for cancellation requested before, during, and after stream reconnect
  - stale owner and unavailable runtime handling for cancellation attempts
  - observability next-action guidance for cancellation failure or stuck active turns
- Implementation notes:
  - reuse existing daemon HTTP plus SSE surfaces rather than adding a second control plane
  - make cancellation conflict messages scriptable and operator-readable
  - treat owner metadata removal as the authoritative shutdown signal in tests
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_daemon_runtime.py tests/integration/test_cli_interactive_commands.py`
  - focused web/API tests for daemon-owned cancellation if route behavior changes
- Done when:
  - cancellation behaves consistently across local, attached, daemon-owned, and reconnecting live sessions

Completion notes:

- Threaded the active turn cancellation controller into approved-tool resumption so cancellation during an approved long-running tool is observed and recorded as `ToolExecutionCancelled` plus `TurnCancelled`.
- Added scriptable conflict messages for suspended approval/question states so cancellation attempts do not look like generic failures.
- Added daemon status guidance for `glassbox session cancel SESSION_ID`, including JSON status command metadata.
- Added daemon-owned `session cancel` coverage, unavailable-runtime and stale-owner CLI handling tests, and local/daemon interactive-client cancellation request shaping.
- Validation: `uv run pytest tests/integration/test_approval_workflow.py tests/unit/test_cli_interactive_client.py tests/integration/test_daemon_runtime.py tests/integration/test_cli_interactive_commands.py`, `uv run ruff check src/glassbox tests`, and `uv run ty check`.

---

## Phase 66: Live Transport And Runtime Ownership Reliability

### GBX-660: Audit Live Transport And Runtime Ownership Failure Modes

- Status: `DONE`
- Depends on: `GBX-641`
- Goal: establish a concrete failure-mode baseline for SSE streams, in-process transport, daemon ownership, and reconnect behavior before hardening changes begin
- Deliverables:
  - transport and runtime ownership audit covering dropped events, slow subscribers, reconnect cursors, daemon stop, stale owner metadata, dashboard reload, TUI attach, and projection lag
  - issue inventory grouped by user-visible severity and release risk
  - list of already-good semantics that must be preserved
  - recommended tests to add in later v6 transport tasks
- Implementation notes:
  - include terminal, dashboard, and scriptable CLI paths
  - focus on event ordering, duplicate avoidance, missed events, and honest degraded-state rendering
  - do not implement hardening in the audit unless a trivial test fixture is needed
- Tests and validation included in task:
  - current transport, daemon, and web SSE tests pass before conclusions are recorded
  - manual or deterministic transcript of at least one reconnect-style workflow
- Done when:
  - implementers have a code-aligned baseline for live transport and runtime ownership reliability

Completion notes:

- Added [v6-live-transport-runtime-ownership-audit.md](./v6-live-transport-runtime-ownership-audit.md) covering current SSE replay/live semantics, in-process transport drop behavior, daemon ownership routing, dashboard and terminal reconnect behavior, observability state, preserved semantics, and known risks.
- Recorded a deterministic reconnect transcript based on existing SSE tests and grouped follow-up issues by user-visible severity and release risk.
- Validation: `uv run pytest tests/unit/test_runtime_transport.py tests/integration/test_web_sse_events.py tests/integration/test_daemon_runtime.py tests/integration/test_observability_status.py`.

### GBX-661: Strengthen Runtime Transport Observability

- Status: `DONE`
- Depends on: `GBX-660`
- Goal: make live event delivery health visible enough for operators and release gates to distinguish healthy, degraded, and unavailable stream states
- Deliverables:
  - expanded transport stats for subscriber count, dropped events, queue pressure, reconnect hints, and last observed sequence where available
  - observability report updates that explain what to refresh, reconnect, rebuild, or inspect next
  - TUI and dashboard rendering updates only where backend observability adds new operator-relevant states
  - release evidence inclusion for transport health
- Implementation notes:
  - keep transport stats implementation-independent where possible
  - avoid exposing high-cardinality internal counters that are not useful to operators
  - do not make UI state authoritative; render backend-derived state
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_runtime_transport.py tests/integration/test_web_sse_events.py tests/integration/test_observability_status.py`
  - frontend tests if dashboard health display changes
- Done when:
  - stream degradation produces actionable observability rather than a vague unavailable state

Completion notes:

- Expanded runtime transport stats with queue capacity, peak queue depth, queue pressure, and latest published sequence where event envelopes expose one.
- Updated `/healthz` and `glassbox observability status` to report healthy/degraded transport state, reconnect hints, and slow-subscriber/drop next actions.
- Regenerated frontend OpenAPI artifacts and aligned dashboard/API fixtures with the backend health schema.
- Validation: `uv run pytest tests/unit/test_runtime_bus.py tests/unit/test_runtime_transport.py tests/integration/test_web_sse_events.py tests/integration/test_observability_status.py tests/integration/test_web_bootstrap.py`; `uv run ruff check docs scripts src tests`; `uv run ty check`; `pnpm --dir frontend test`; `pnpm --dir frontend typecheck`.

### GBX-662: Harden SSE Reconnect And Historical Replay Boundaries

- Status: `DONE`
- Depends on: `GBX-661`
- Goal: make reconnect behavior predictable when clients reload, streams drop, or sequence cursors lag behind persisted state
- Deliverables:
  - tests for `after` cursor replay, duplicate suppression expectations, keepalive frames, unknown sessions, completed sessions, and client disconnects
  - route or client fixes for any replay/live ordering gap discovered in `GBX-660`
  - dashboard store and TUI client behavior aligned around last-sequence resume
  - documentation of SSE cursor semantics for frontend and terminal clients
- Implementation notes:
  - preserve the current route shape unless a contract problem requires a versioned change
  - prefer deterministic fake stream tests over fragile network timing
  - keep completed and historical sessions readable even when no live owner exists
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_web_sse_events.py tests/unit/test_cli_tui_app.py`
  - `pnpm --dir frontend test` for SSE client/store behavior if frontend changes
- Done when:
  - clients can reconnect from the last observed sequence without missing or duplicating user-visible state

Completion notes:

- Added route-side duplicate suppression across the historical replay/live subscription boundary using the highest delivered event sequence.
- Added deterministic SSE tests for duplicate suppression, keepalive comments, completed-session replay, disconnect cleanup, and existing cursor behavior.
- Added TUI coverage proving reconnect retries resume from the latest delivered sequence after live events are applied.
- Added [sse-cursor-semantics-v6.md](./sse-cursor-semantics-v6.md) documenting the shared server, dashboard, TUI, and terminal attach cursor contract.
- Validation: `uv run pytest tests/integration/test_web_sse_events.py tests/unit/test_cli_tui_app.py`; `pnpm --dir frontend test`; `uv run ruff check docs scripts src tests`; `uv run ty check`.

### GBX-663: Harden Daemon Lifecycle And Owner Metadata Recovery

- Status: `DONE`
- Depends on: `GBX-660`
- Goal: make daemon start, stop, status, stale metadata cleanup, and attach recovery boringly reliable across local development and release smoke
- Deliverables:
  - deterministic tests for healthy startup, startup failure, stale metadata, stop timeout, missing health route, port conflict, and attach after owner cleanup
  - improved daemon status output or observability next actions where current errors are not actionable
  - release smoke workflow for daemon start/status/attach/stop
  - documentation updates for stale owner recovery if behavior changes
- Implementation notes:
  - do not use process liveness as the only shutdown truth where owner metadata cleanup is more reliable
  - keep daemon ownership local to one workspace and database path
  - make port-conflict errors specific enough for release triage
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_daemon_runtime.py`
  - installed-wheel daemon smoke once packaging support is in the v6 gate
- Done when:
  - daemon lifecycle failures have deterministic tests and clear recovery guidance

Completion notes:

- Added deterministic daemon lifecycle tests for process startup failure, port conflict, unreachable health/status recovery guidance, stop timeout, and local attach after stale owner cleanup.
- Improved daemon status output for `running` owners with unreachable health by printing the health URL and stop/start recovery command.
- Made startup failure copy call out requested host/port conflicts when the owner stderr log indicates bind failure.
- Added [daemon-release-smoke-v6.md](./daemon-release-smoke-v6.md) for start/status/attach/stop release validation and stale owner recovery.
- Validation: `uv run pytest tests/integration/test_daemon_runtime.py`; `uv run ruff check docs scripts src tests`; `uv run ty check`.

### GBX-664: Add Transport Backpressure And Drop Tests

- Status: `DONE`
- Depends on: `GBX-661`
- Goal: prove live transport behavior under slow or stalled subscribers without losing canonical persisted events
- Deliverables:
  - deterministic tests for slow subscribers, bounded queues, dropped live events, and reconnect recovery through persisted event replay
  - transport stats updates if current counters cannot explain backpressure
  - operator-facing guidance for when a live stream should be refreshed rather than trusted
- Implementation notes:
  - canonical persisted events remain authoritative even if live delivery drops occur
  - avoid tests that depend on wall-clock sleeps; use controlled queues or fake subscribers where possible
  - keep the default queue sizing and drop policy explicit
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_runtime_transport.py tests/integration/test_web_sse_events.py`
  - `uv run ty check`
- Done when:
  - dropped live events are observable, recoverable through replay, and covered by deterministic tests

Completion notes:

- Added deterministic transport coverage for bounded subscriber queues dropping the oldest live item while retaining the newest event and exposing drop/pressure stats.
- Added SSE recovery coverage proving events dropped from a slow live subscriber are recovered from persisted replay with `after=<last observed sequence>`.
- Added [live-transport-backpressure-v6.md](./live-transport-backpressure-v6.md) with operator guidance for degraded live delivery, refresh/reconnect behavior, and projection checks.
- Validation: `uv run pytest tests/unit/test_runtime_transport.py tests/integration/test_web_sse_events.py`; `uv run ty check`; `uv run ruff check docs scripts src tests`.

### GBX-665: Validate Mutation Ownership Under Concurrent Clients

- Status: `DONE`
- Depends on: `GBX-663`
- Goal: ensure local commands, TUI, dashboard, and daemon-owned sessions cannot accidentally create competing live mutation owners
- Deliverables:
  - tests for local mutating commands rejected while a healthy daemon owns the workspace
  - dashboard and attach behavior for concurrent prompt, answer, approval, denial, fork, and cancellation requests
  - conflict response copy and status codes aligned across CLI and API surfaces
  - docs update if any command behavior changes
- Implementation notes:
  - preserve single-owner semantics rather than hiding conflicts with optimistic UI behavior
  - keep read-only inspection available when mutation is blocked
  - prefer idempotent behavior for repeated approval, denial, answer, and cancellation attempts where possible
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_daemon_runtime.py tests/integration/test_web_session_interaction.py tests/integration/test_cli_session_commands.py`
  - frontend action-state tests if browser conflict handling changes
- Done when:
  - concurrent client attempts produce safe, understandable outcomes without corrupting session state

Completion notes:

- Added parameterized CLI coverage proving local `run`, `resume`, `message`, `answer`, `approve`, `deny`, `fork`, and `import` mutations are rejected while daemon owner metadata is running.
- Added API coverage proving concurrent prompt, answer, approval, denial, fork, and cancellation conflicts align on HTTP `409` and shared response copy.
- Reused Phase 66 daemon attach/cleanup coverage to preserve daemon-routed attach and local fallback after stale owner cleanup.
- Added [mutation-ownership-v6.md](./mutation-ownership-v6.md) documenting the single-owner mutation contract for CLI, dashboard/API, and terminal attach clients.
- Validation: `uv run pytest tests/integration/test_daemon_runtime.py tests/integration/test_web_session_interaction.py tests/integration/test_cli_session_commands.py`; `uv run ruff check docs scripts src tests`; `uv run ty check`.

---

## Phase 67: Provider Canaries, Policy Evidence, And Context Confidence

### GBX-670: Define Live-Provider Canary Policy

- Status: `DONE`
- Depends on: `GBX-640`
- Goal: define how real-provider validation participates in release confidence without undermining deterministic local release gates
- Deliverables:
  - provider-canary policy doc covering when canaries run, required credentials, expected scenarios, failure interpretation, and artifact retention
  - explicit rule that deterministic replay/eval remains the default blocking gate
  - canary scenario matrix for streaming, tool call, approval, denial, `ask_user`, cancellation, dashboard convergence, and daemon attach where practical
  - redaction policy for prompts, provider responses, environment variables, and logs
- Implementation notes:
  - do not require provider credentials for default contributor validation
  - keep provider canaries small and targeted; they prove integration posture, not complete model quality
  - align with [providers.md](./providers.md) and [replay-evals.md](./replay-evals.md)
- Tests and validation included in task:
  - docs review against provider configuration and eval profile manifests
- Done when:
  - the repo has a clear provider-canary policy that can be automated without becoming a mandatory dependency for all contributors

Completion notes:

- Added [provider-canary-policy-v6.md](./provider-canary-policy-v6.md) defining advisory live-provider canary scope, required credentials, scenario matrix, failure interpretation, artifact retention, and redaction rules.
- Linked the policy from [providers.md](./providers.md) and [replay-evals.md](./replay-evals.md), preserving deterministic replay/eval as the default blocking release gate.
- Validation: reviewed against [providers.md](./providers.md), [replay-evals.md](./replay-evals.md), and `evals/profiles.json`; `uv run glassbox eval profile list --track live-provider-canary --json --cwd .`.

### GBX-671: Add Provider Configuration Diagnostics

- Status: `DONE`
- Depends on: `GBX-670`
- Goal: make provider setup failures easier to diagnose before starting a real session or canary workflow
- Deliverables:
  - diagnostic command or observability section that reports selected provider mode, missing credentials, unsupported models, and configuration-source hints without printing secrets
  - tests for local, OpenAI, Anthropic, missing credential, invalid model, and invalid workspace profile cases
  - docs update for provider troubleshooting
- Implementation notes:
  - never print API keys or secret-like values
  - keep diagnostics useful in CI and local shells
  - prefer existing provider configuration boundaries over adding a parallel config loader
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_runtime_provider_config.py tests/integration/test_provider_mode_runtime.py`
  - `uv run ruff check src/glassbox/runtime src/glassbox/cli tests`
- Done when:
  - operators can understand provider configuration problems before a live turn fails

Completion notes:

- Added `glassbox provider diagnostics` with text and JSON output for selected model source, provider family, runtime mode, credential presence, source hints, problems, and next actions without printing secret values.
- Added redacted provider diagnostics covering local fallback, OpenAI, Anthropic, missing credentials, unsupported model prefixes, malformed `.env`, and invalid `glassbox.profile.json` cases.
- Updated [providers.md](./providers.md) with preflight diagnostic usage and secret-handling expectations.
- Validation: `uv run pytest tests/unit/test_runtime_provider_config.py tests/integration/test_provider_mode_runtime.py`; `uv run ruff check src/glassbox/runtime src/glassbox/cli tests`.

### GBX-672: Add Advisory Provider-Canary Execution

- Status: `DONE`
- Depends on: `GBX-670`, `GBX-671`
- Goal: provide an optional command or eval profile path for real-provider canary scenarios that records structured advisory evidence
- Deliverables:
  - canary command, eval profile, or documented workflow selected by `GBX-670`
  - structured canary summary artifact with scenario outcomes, skipped reasons, provider/model metadata, redacted logs, and next actions
  - skip behavior when credentials are unavailable
  - release-gate integration as advisory output rather than default blocking failure
- Implementation notes:
  - keep canaries short to avoid surprising cost or latency
  - avoid checking live-provider outputs against brittle exact text
  - verify behavior through event families, state transitions, tool/approval/question/cancellation semantics, and dashboard/TUI convergence
- Tests and validation included in task:
  - deterministic tests for command selection, skip behavior, redaction, and summary writing
  - optional manual real-provider run when credentials are available
- Done when:
  - maintainers can run and retain live-provider confidence evidence without making normal local validation depend on external services

Completion notes:

- Added `glassbox provider canary run` as an optional advisory command that writes `provider-canary-summary.json` with scenario outcomes, skipped reasons, provider/model metadata, and next actions.
- Implemented credential-aware skip behavior through provider diagnostics, plus a minimal live `streaming-text` canary path when provider credentials are configured.
- Added deterministic tests for command selection, missing-credential skip behavior, summary writing, scenario selection, and redaction of configured provider values.
- Updated [provider-canary-policy-v6.md](./provider-canary-policy-v6.md) with the command workflow and retained artifact location.
- Validation: `uv run pytest tests/integration/test_provider_mode_runtime.py`; `uv run ruff check src/glassbox/runtime src/glassbox/cli tests`; `uv run ty check`.

### GBX-673: Strengthen Policy Evidence And Audit Surfaces

- Status: `DONE`
- Depends on: `GBX-641`
- Goal: make tool-policy decisions, approval requirements, blocked actions, and risk summaries easier to audit in terminal, dashboard, replay, and release artifacts
- Deliverables:
  - review of current policy metadata projections and dashboard/TUI display
  - improvements to policy summary output where decisions are hard to explain
  - replay/eval coverage for policy metadata preservation
  - release evidence inclusion for policy-gated canary or deterministic scenarios
- Implementation notes:
  - preserve existing policy engine and manifest boundaries unless an audit gap requires a contract change
  - focus on inspectability, not new policy language breadth
  - avoid surfacing raw internal policy fields where operator labels are clearer
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_tools_policy.py tests/integration/test_approval_workflow.py tests/integration/test_web_approval_resolution.py`
  - dashboard/TUI tests if display changes
- Done when:
  - an operator can explain why a tool was allowed, blocked, or approval-gated from persisted evidence

Completion notes:

- Reviewed persisted policy metadata and added regression coverage proving `ModelToolCallRequested`, `ApprovalRequested`, and resumed `ToolExecutionStarted` preserve policy outcome, risk, source, label, and reason.
- Improved CLI policy summary copy to direct operators from aggregate counts to pending approvals and recent tool activity where source/reason details are printed.
- Added [policy-evidence-v6.md](./policy-evidence-v6.md) documenting persisted evidence, CLI/dashboard audit surfaces, and current deterministic release evidence versus the remaining curated eval gap.
- Validation: `uv run pytest tests/unit/test_tools_policy.py tests/integration/test_approval_workflow.py tests/integration/test_web_approval_resolution.py`; `uv run ruff check src/glassbox/runtime src/glassbox/cli tests`; `uv run ty check`.

### GBX-674: Add Context Budget And Drift Confidence Checks

- Status: `DONE`
- Depends on: `GBX-641`
- Goal: improve confidence that runtime context, working-set summaries, artifact-backed evidence, and replay manifests stay within expected budgets and drift semantics
- Deliverables:
  - tests or eval cases for large context, inherited branch context, runtime notes, artifact-backed summaries, and manifest drift
  - observability or eval recommendation improvements when context-related files change
  - release-gate inclusion for deterministic context smoke if current coverage is weak
  - docs update if context budgets or drift interpretation changes
- Implementation notes:
  - do not turn context building into a broad optimization project unless a concrete budget fails
  - keep replay manifest drift explicit rather than silently refreshing baselines
  - prefer advisory recommendation improvements over pretending to infer a perfect minimal test set
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_context_builder.py tests/integration/test_session_query_characterization.py tests/unit/test_replay_orchestrator.py`
  - `uv run glassbox eval recommend src/glassbox/runtime/context_builder.py --cwd .`
- Done when:
  - release validation has better coverage for context-sensitive behavior that can otherwise drift quietly

Completion notes:

- Fixed `evals/impact.json` so `glassbox eval recommend src/glassbox/runtime/context_builder.py --cwd .` can load the impact manifest and route context changes to context cases/profiles again.
- Expanded the runtime-context impact rule to include context docs and characterization tests, with advisory notes for inherited notes, working-set budgets, artifact-backed summaries, and selected-invariant replay drift.
- Added a CLI runtime-context budget summary that reports visible and truncated repository, note, working-set, and artifact-backed context counts.
- Added tests for runtime-context budget reporting and context-path eval recommendations.
- Documented how to interpret runtime-context budget truncation and drift in [runtime-context.md](./runtime-context.md).
- Validation: `uv run pytest tests/unit/test_context_builder.py tests/integration/test_session_query_characterization.py tests/unit/test_replay_orchestrator.py`; `uv run pytest tests/unit/test_eval_recommendations.py`; `uv run glassbox eval recommend src/glassbox/runtime/context_builder.py --cwd .`; `uv run ruff check src/glassbox/runtime src/glassbox/cli tests`; `uv run ty check`.

---

## Phase 68: Reproducible Packaging And Clean-Environment Smoke

### GBX-680: Enforce Frontend API And Static Asset Freshness

- Status: `TODO`
- Depends on: `GBX-642`
- Goal: prevent stale generated API types or missing static SPA assets from reaching a release package
- Deliverables:
  - release-gate check for generated OpenAPI schema and TypeScript API types
  - release-gate check that `pnpm --dir frontend build` has refreshed `src/glassbox/web/static_next/`
  - test or script logic that fails when built static assets reference missing `_next` files
  - documentation update for source-build and release-build expectations
- Implementation notes:
  - avoid committing noisy build artifacts unless that is already the repository policy
  - keep production users free from Node requirements in installed packages
  - coordinate with FastAPI static asset validation
- Tests and validation included in task:
  - `pnpm --dir frontend api:generate`
  - `pnpm --dir frontend build`
  - `uv run pytest tests/integration/test_web_spa_static.py tests/unit/test_packaging_metadata.py`
- Done when:
  - release validation catches stale API/generated/static dashboard assets before package build succeeds

### GBX-681: Expand Wheel And Sdist Content Validation

- Status: `TODO`
- Depends on: `GBX-680`
- Goal: prove release distributions contain the runtime, TUI dependency metadata, generated dashboard assets, docs needed for source distributions, and console script entrypoint
- Deliverables:
  - automated wheel/sdist inspection for `glassbox/web/static_next/index.html`, `_next` assets, TUI dependency metadata, console script, package modules, and source distribution docs
  - clear failure output showing missing package paths or metadata
  - release-gate integration after `uv build --wheel --sdist`
- Implementation notes:
  - keep package inspection independent of the local editable checkout where possible
  - validate both wheel and sdist because the project supports both targets
  - do not require starting a dashboard server in this task; that belongs to installed smoke
- Tests and validation included in task:
  - `uv build --wheel --sdist`
  - `uv run pytest tests/unit/test_packaging_metadata.py`
- Done when:
  - missing package assets fail before a release artifact is published or manually smoke-tested

### GBX-682: Add Installed-Package Smoke Matrix

- Status: `TODO`
- Depends on: `GBX-681`
- Goal: verify the built wheel works in a clean environment across terminal, dashboard, daemon, replay/eval, and fallback paths
- Deliverables:
  - installed-wheel smoke for `glassbox --help`, `command tree`, `session chat --help`, `session attach --help`, explicit `--plain`, dashboard serve, daemon status/start/stop, and deterministic eval smoke where practical
  - dashboard static smoke that opens or requests `/`, `/app`, and a representative static asset without requiring Node
  - clean temporary workspace isolation for each smoke group
  - release evidence logs for each installed smoke group
- Implementation notes:
  - avoid starting long-lived TUI sessions in non-interactive smoke; use help and explicit plain fallback
  - clean up daemon processes even on failure
  - keep smoke commands short enough for local release use
- Tests and validation included in task:
  - release-gate installed smoke in a temporary environment
  - focused test for smoke command construction if factored
- Done when:
  - the release gate proves the installed wheel is usable without the editable checkout or frontend toolchain

### GBX-683: Align Pre-Commit, Eval Profiles, And Release Gate Expectations

- Status: `TODO`
- Depends on: `GBX-642`, `GBX-674`
- Goal: make daily development checks, deterministic eval profiles, and release-candidate gates reinforce each other rather than drifting into separate rituals
- Deliverables:
  - review of pre-commit hooks, eval profiles, release report profiles, and v6 gate stages
  - updates to eval profile metadata if commit-time, push-time, and release-candidate surfaces no longer match current expectations
  - docs update explaining which checks are local blocking, push-confirmation, release-candidate, and advisory canary
  - tests for eval profile selection and report output if metadata changes
- Implementation notes:
  - do not move unstable or live-provider checks into pre-commit
  - keep profile budgets explicit and visible
  - use `eval recommend` reasoning rather than adding opaque hardcoded path lists
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_runtime_evals.py tests/unit/test_eval_inputs.py tests/unit/test_eval_recommendations.py`
  - `uv run glassbox eval report commit-smoke push-confirmation release-candidate --cwd .`
- Done when:
  - contributors can see how local checks, eval profiles, and release gates fit together

### GBX-684: Add Dependency And Toolchain Freshness Review

- Status: `TODO`
- Depends on: `GBX-641`
- Goal: make release readiness include an explicit review of runtime dependencies, frontend dependencies, Python version support, and toolchain assumptions
- Deliverables:
  - documented dependency freshness review for Python runtime dependencies, dev tools, Textual, FastAPI, Pydantic, pydantic-ai, Next.js, React, Playwright, Vitest, and TypeScript
  - release risk notes for any pinned or version-bounded dependency that materially affects the primary UX
  - optional advisory command or checklist for dependency audit output if tooling exists in the repo
  - update to release packaging docs if toolchain assumptions change
- Implementation notes:
  - do not perform broad dependency upgrades in the review task unless a critical issue blocks release readiness
  - keep Python 3.14 support explicit
  - separate security/license concerns from ordinary freshness notes where possible
- Tests and validation included in task:
  - docs review against `pyproject.toml`, `uv.lock`, `frontend/package.json`, and `frontend/pnpm-lock.yaml`
- Done when:
  - release signoff includes a conscious dependency/toolchain review rather than an implicit assumption that the lockfiles are fine

---

## Phase 69: Accessibility, Manual QA, And Evidence Archive

### GBX-690: Define Manual QA Evidence Archive For v6

- Status: `TODO`
- Depends on: `GBX-643`
- Goal: define where manual terminal, dashboard, provider-canary, daemon, packaging, and accessibility evidence lives for a release candidate
- Deliverables:
  - manual evidence directory convention and retention policy
  - checklist template for terminal sizes, dashboard viewport sizes, keyboard workflows, screen-reader notes, provider canaries, daemon lifecycle, installed dashboard smoke, and recovery commands
  - guidance for attaching screenshots, terminal recordings, command transcripts, and redacted logs
  - release evidence summary linking manual artifacts to the automated gate summary
- Implementation notes:
  - keep manual evidence lightweight enough that maintainers will actually use it
  - avoid storing secrets or unredacted provider content
  - align with the v4 screenshot archive and v5 manual terminal review rather than inventing a conflicting archive model
- Tests and validation included in task:
  - docs review
  - optional schema validation for manual evidence manifests if added
- Done when:
  - manual release checks have a defined artifact shape and retention policy

### GBX-691: Run Terminal Accessibility And Visual Review Pass

- Status: `TODO`
- Depends on: `GBX-690`, `GBX-653`
- Goal: validate the full-screen TUI across representative terminal sizes, keyboard workflows, fallback contexts, and accessibility constraints
- Deliverables:
  - manual terminal review artifacts for 120x36, 100x30, 80x24, and 60x20 terminal sizes
  - keyboard-only workflow evidence for prompt submit, multiline editing, command palette, details pane, approvals, questions, cancellation, attach, reconnect, and quit
  - screen-reader or terminal accessibility notes with explicit claims and non-claims
  - follow-up task list for any blocking terminal UX issue discovered
- Implementation notes:
  - do not claim accessibility support beyond what was actually reviewed
  - prefer fixing layout or keyboard blockers in this task only when they are small and directly found by the review
  - keep visual review focused on usability and readability, not pixel perfection
- Tests and validation included in task:
  - focused TUI workflow suite
  - manual review artifacts stored under the v6 evidence convention
- Done when:
  - the terminal client has release-candidate manual evidence for the workflows automated tests cannot fully prove

### GBX-692: Run Dashboard Accessibility And Responsive Review Pass

- Status: `TODO`
- Depends on: `GBX-690`
- Goal: validate the operator console across keyboard workflows, viewport sizes, action states, live stream states, and accessibility constraints
- Deliverables:
  - refreshed or v6-specific dashboard screenshots for high-priority release states
  - keyboard-only evidence for queue navigation, session selection, tabs, prompt, answer, approval, fork, compare, evidence, and recovery states
  - screen-reader notes and semantic landmarks review for primary operator workflows
  - follow-up task list for any blocking dashboard UX issue discovered
- Implementation notes:
  - reuse v4 screenshot archive infrastructure where practical
  - focus on release-critical states rather than regenerating every historical scenario by default
  - do not make public accessibility claims beyond reviewed evidence
- Tests and validation included in task:
  - `pnpm --dir frontend lint`
  - `pnpm --dir frontend typecheck`
  - `pnpm --dir frontend test`
  - `pnpm --dir frontend test:e2e`
  - relevant screenshot archive command
- Done when:
  - the dashboard has release-candidate manual and automated evidence for critical operator workflows

### GBX-693: Validate Recovery And Maintenance Workflows Manually

- Status: `TODO`
- Depends on: `GBX-663`, `GBX-683`, `GBX-690`
- Goal: prove the non-chat operational surfaces that matter during real use: projections, artifacts, backup, observability, replay/eval, and daemon recovery
- Deliverables:
  - manual recovery smoke evidence for `observability status`, `projection check`, `projection rebuild`, `artifacts inspect`, artifact prune dry-run, backup create/inspect/restore, replay run, eval report, daemon stale-owner recovery, and installed dashboard smoke
  - next-action review showing errors lead to useful operator guidance
  - docs corrections for any workflow mismatch found during the smoke
- Implementation notes:
  - use temporary workspaces for destructive restore/prune validation
  - preserve local user data and avoid mutating real `.glassbox/` state except in controlled fixtures
  - keep command transcript artifacts redacted where needed
- Tests and validation included in task:
  - relevant integration tests for storage, backup, artifacts, replay/eval, daemon, and observability
  - manual evidence stored under the v6 evidence convention
- Done when:
  - release evidence covers the maintenance workflows operators need when something goes wrong

### GBX-694: Refresh Public Operator Docs For v6

- Status: `TODO`
- Depends on: `GBX-691`, `GBX-692`, `GBX-693`
- Goal: update user-facing docs so they describe the release-hardened workflow instead of task-file intentions
- Deliverables:
  - updates to getting started, interactive workflows, dashboard, persistent runtime, replay/evals, release packaging, providers, and troubleshooting sections as needed
  - clear documentation of cancellation, provider diagnostics, release evidence, installed-package expectations, and known residual limitations
  - docs hub update linking v6 release gate and release-candidate posture
  - migration note for users familiar with the v5 release-gate known gaps
- Implementation notes:
  - keep operator docs task-light; users should not need to read this file to understand supported behavior
  - preserve scriptable command examples
  - do not hide known limitations behind optimistic wording
- Tests and validation included in task:
  - docs review against implemented command help and release gate output
  - existing docs/link tests if present
- Done when:
  - a new user can understand the v6-supported operating model and validation path from operator docs alone

---

## Phase 70: v6 Release Candidate Decision

### GBX-700: Define The v6 Release Candidate Gate

- Status: `TODO`
- Depends on: `GBX-642`, `GBX-655`, `GBX-665`, `GBX-672`, `GBX-684`, `GBX-694`
- Goal: define the final pass/fail gate for calling a build the v6 release candidate
- Deliverables:
  - v6 release gate document with automated command, checklist, evidence artifact policy, manual validation matrix, provider-canary policy, known gaps, and residual risk register
  - automated coverage map from release requirements to tests, scripts, docs, and manual evidence
  - explicit pass/fail policy for deterministic failures, provider-canary skips, provider-canary failures, manual accessibility findings, packaging failures, and daemon smoke failures
  - final decision on whether any v5 known non-blocking gap remains accepted after v6
- Implementation notes:
  - build on the v5 release-gate style but broaden scope beyond terminal UX
  - make skipped live-provider checks visible rather than silently green
  - keep residual risks specific and actionable
- Tests and validation included in task:
  - docs/gate alignment tests where practical
  - dry-run or focused script validation if the v6 gate supports it
- Done when:
  - there is one objective v6 release-candidate gate that combines automated validation and manual evidence expectations

### GBX-701: Run The Automated v6 Gate And Fix Blocking Failures

- Status: `TODO`
- Depends on: `GBX-700`
- Goal: execute the full automated v6 gate and resolve any blocking failures without weakening the gate
- Deliverables:
  - passing `uv run python scripts/validate_v6_release_gate.py` result
  - release evidence summary artifact from the passing run
  - fixes for any blocking Python, frontend, replay/eval, packaging, installed-smoke, cancellation, transport, daemon, or docs failures found by the gate
  - documented skipped checks and reasons where allowed by policy
- Implementation notes:
  - do not mark this done with known deterministic failures
  - do not delete tests or relax checks to make the gate pass without a documented release decision
  - keep fixes focused on release blockers
- Tests and validation included in task:
  - `uv run python scripts/validate_v6_release_gate.py`
- Done when:
  - the automated v6 gate passes and leaves retained evidence

### GBX-702: Run Manual Release Candidate Validation

- Status: `TODO`
- Depends on: `GBX-701`, `GBX-690`
- Goal: complete the manual release validation matrix and record evidence for workflows automated tests cannot fully prove
- Deliverables:
  - manual terminal UX evidence
  - manual dashboard UX evidence
  - installed package dashboard smoke evidence
  - daemon lifecycle evidence
  - recovery and maintenance evidence
  - optional provider-canary evidence or documented credential-unavailable skip
  - final blocking issue list and residual risk list
- Implementation notes:
  - keep manual results tied to the same release evidence directory as automated gate output
  - fix blocking defects discovered during manual validation before marking this done
  - record skipped provider canaries explicitly
- Tests and validation included in task:
  - manual checklist from the v6 release gate
  - focused automated reruns for any area fixed during manual validation
- Done when:
  - manual release evidence exists and no blocking manual validation issue remains open

### GBX-703: Publish The v6 Release Candidate Guide

- Status: `TODO`
- Depends on: `GBX-701`, `GBX-702`
- Goal: package the v6 operating model, validation path, known gaps, and non-goals into one operator-facing release-candidate guide
- Deliverables:
  - `v6-release-candidate.md` or equivalent operator-facing release guide
  - supported operating model summary for terminal chat, dashboard, daemon, cancellation, replay/eval, provider canaries, release evidence, and recovery workflows
  - release-readiness checklist with links to automated and manual evidence expectations
  - explicit non-goals and residual known gaps
  - docs hub and root README updates if appropriate
- Implementation notes:
  - mirror the clarity of [v2-release-candidate.md](./v2-release-candidate.md) while reflecting the current v6 product surface
  - do not require users to read task docs to understand the supported model
  - name cancellation and provider canary limitations precisely
- Tests and validation included in task:
  - docs review against command help, release gate output, and known residual risks
- Done when:
  - the v6 release candidate has a single operator-readable guide

### GBX-704: Make The v6 Release Candidate Decision

- Status: `TODO`
- Depends on: `GBX-703`
- Goal: make and record the final decision on whether the current build is ready to be treated as the v6 release candidate
- Deliverables:
  - release decision entry in the v6 release guide or release evidence summary
  - final pass/fail state for automated gate, manual validation, provider canary policy, package smoke, daemon smoke, recovery smoke, and residual risk review
  - follow-up backlog for non-blocking post-v6 work
  - explicit decision on whether any task in this file remains open and why it does not block the release candidate
- Implementation notes:
  - do not mark this done until the release evidence is inspectable
  - keep the decision factual; avoid optimistic wording that hides skipped or advisory checks
  - if the decision is no-go, record the blocker list and next recommended task order
- Tests and validation included in task:
  - review of retained release evidence
  - no new code changes are required unless a release blocker is discovered
- Done when:
  - the repo records a clear go/no-go v6 release-candidate decision with supporting evidence

---

## Recommended Build Order For The First v6 Hardening Slice

If an agent wants the fastest path to a demonstrable release-hardening improvement, the recommended order is:

1. `GBX-640` and `GBX-641`
2. `GBX-642` and `GBX-643`
3. `GBX-650` through `GBX-653`
4. `GBX-660` through `GBX-663`
5. `GBX-670` and `GBX-671`
6. `GBX-680` through `GBX-682`
7. `GBX-690` and targeted manual evidence tasks
8. `GBX-700` once the automated and manual evidence surfaces are stable

That yields:

- a documented v6 release-hardening contract
- a canonical automated gate and retained evidence format
- real cancellation from terminal, dashboard, API, and daemon attach paths
- stronger stream and daemon recovery behavior
- advisory provider-canary policy and diagnostics
- reproducible package validation
- manual QA evidence for terminal, dashboard, recovery, and accessibility workflows
- a concrete v6 release-candidate decision path
