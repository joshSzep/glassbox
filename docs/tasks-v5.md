# Glassbox v5 Tasks

For the docs hub and operator guides, start at [README.md](./README.md). This file is the v5 task graph for turning `glassbox session chat` from a line-oriented prototype into a first-class full-screen coding-agent terminal experience.

## Purpose

This document defines Glassbox v5: the terminal-client evolution after the v4 dashboard UX pass in [tasks-v4.md](./tasks-v4.md).

It is written in the same execution style as [tasks-v1.md](./tasks-v1.md), [tasks-v2.md](./tasks-v2.md), [tasks-v3.md](./tasks-v3.md), and [tasks-v4.md](./tasks-v4.md): explicit dependencies, small vertical slices, concrete deliverables, and quality requirements attached directly to the work.

The v1 and v2 interactive terminal work established correct command semantics, persisted sessions, approval and question routing, daemon-backed attach, and a co-hosted dashboard. That foundation is operationally useful, but the actual `glassbox session chat` experience still feels like an early line-mode prototype: `input()`, flat event lines, slash-command discovery, no multiline composer, no real transcript surface, and no modern terminal application model.

The v5 goal is to make `glassbox session chat` feel like a polished coding-agent conversation, comparable to or better than contemporary terminal coding agents, while preserving the Glassbox advantage: every conversation remains event-sourced, locally inspectable, replayable, and paired with a co-hosted browser operator console.

## Product Direction

The terminal UX work should optimize for seven outcomes:

- a full-screen terminal app that makes chat the primary surface, not a log tail around `input()`
- a multiline composer that supports real coding-agent prompting, editing, paste handling, history, and draft preservation
- streaming assistant responses that feel alive and readable while preserving canonical transcript state
- compact tool activity embedded in the conversation, with expandability for useful output and failures
- first-class approval and question workflows that are visually and keyboard-accessibly prominent
- reliable attach, reconnect, interruption, and runtime-state feedback for local and daemon-owned sessions
- a continued browser partnership where the co-hosted dashboard remains the deeper operator console and evidence surface

The v5 thesis is:

- make the full-screen TUI the default `glassbox session chat` experience
- keep the web dashboard co-hosted by default during chat
- keep canonical events, backend projections, snapshots, and runtime services as the source of truth
- introduce a terminal client boundary instead of growing the current line-mode loop into a fragile pseudo-TUI
- use a proven terminal UI framework, with Textual as the intended default unless an implementation task documents a better user-centered alternative
- preserve a plain or non-TTY fallback only as a compatibility and debugging path during the migration
- treat terminal UX hierarchy as product behavior, not decoration

## Chosen Direction For The Terminal Stack

The intended stack decisions are:

- terminal framework: Textual
- styled rendering: Rich through Textual, with explicit markdown and code-block rendering where practical
- runtime integration: existing local runtime services and daemon HTTP plus SSE surfaces
- production mode: Python package only; no Node or browser process required for terminal chat
- dashboard mode: FastAPI co-hosted dashboard remains enabled by default for `session chat`
- fallback mode: retain a plain line-mode path or clear non-TTY behavior until the v5 release gate decides whether it remains supported

If implementation proves Textual is not the best path, the dependency decision must be revisited in a documented task before building a parallel terminal framework. Do not hand-roll full-screen terminal control unless a task demonstrates that a framework would block the user experience.

## Current Baseline Before V5 Execution

Treat the following as the starting point for every task in this document:

- `glassbox session chat` starts a new session, subscribes to the process-local event stream, optionally submits an initial prompt, starts a co-hosted dashboard by default, and enters the interactive loop
- `glassbox session attach SESSION_ID` either attaches to a healthy daemon-owned live session over HTTP plus SSE or reopens an actionable persisted session locally
- `src/glassbox/cli/interactive_session.py` owns the current local line-mode loop, prompt routing, slash-command parsing, blocked-state messaging, and prompt context lines
- `src/glassbox/cli/daemon_attach.py` mirrors the line-mode loop for daemon-backed attach and live SSE rendering
- `src/glassbox/cli/renderer.py` converts event envelopes into flat terminal lines and redraws prompt context by printing around the active `input()` prompt
- `AssistantMessageDelta` events are buffered and the terminal prints the assistant response on completion rather than streaming readable assistant text as the primary experience
- `ToolOutputChunk` events exist in the event model, but the current terminal renderer does not present streaming tool output as a rich ongoing activity surface
- pending questions and approvals are routable without copying IDs, but they are presented as prompt context and slash-command instructions rather than as first-class action surfaces
- the current project has no terminal UI dependency such as Textual, prompt-toolkit, or curses wrapper
- current interactive tests cover routing, attach, prompt redraw, dashboard sidecar startup, approval, question, and invalid states, but they characterize the current line-mode behavior rather than a modern terminal product
- the v4 dashboard is the operator console for deeper evidence, queues, metrics, lineage, compare, runtime context, and replay/eval cues; v5 should complement it rather than duplicate all of it in the terminal

## Current Terminal UX Findings

Treat these findings as evidence that should steer the first implementation slices:

- the interactive entry point uses `input()` and cannot offer modern multiline editing, cancellable input, command completion, or reliable prompt redraw under heavy output
- the transcript is not a stable surface; it is scrollback made of flat event lines
- assistant streaming does not feel live because deltas are buffered until completion
- tool activity has no coherent turn grouping, expandable detail, or output policy
- approvals and questions are operationally correct but visually weak compared with the urgency of the decision
- `/help` is the only real command-discovery surface
- `/status` dumps a broad status report rather than giving a concise in-context chat answer
- daemon reconnect and runtime availability messages are functional but not yet product-quality terminal states
- the dashboard URL is printed once instead of remaining available as persistent context or a command-palette action
- tests protect current semantics but do not yet prove a full-screen terminal app is usable across keyboard workflows, non-TTY fallback, or live stream turbulence

## Agent Execution Rules

These rules apply to every task in this file.

1. Respect dependency order. Do not start a task until its dependencies are complete unless the task explicitly says it can proceed in parallel.
2. Preserve the event-sourced source-of-truth rule. Terminal UI state is derived from backend events, snapshots, runtime stream state, and local composer drafts only.
3. Preserve FastAPI as the dashboard and web API owner. The terminal app may co-host the dashboard, but it must not become a second canonical runtime or projection system.
4. Preserve the co-hosted dashboard by default for `glassbox session chat` unless a task explicitly covers an operator-visible configuration change.
5. Make `glassbox session chat` chat-first. Do not turn the default terminal surface into a queue dashboard, metrics console, or raw event inspector.
6. Keep raw evidence reachable through the dashboard and intentional terminal detail surfaces, but do not let raw diagnostics crowd out the conversation and composer.
7. Prefer a framework-backed TUI architecture over ad hoc ANSI control whenever the framework improves correctness, testing, or user experience.
8. Keep non-interactive commands scriptable. `run`, `message`, `answer`, `approve`, `deny`, `fork`, `resume`, `status`, replay, eval, and dashboard commands remain useful primitives.
9. If the TUI exposes an API mismatch, fix the service/API contract or document the mismatch before encoding fragile terminal-only workarounds.
10. Every implementation task automatically includes:
    - automated tests for new behavior
    - `ruff` formatting and lint compliance for touched Python code
    - `ty` typecheck compliance for touched Python code
    - focused `pytest` coverage for touched CLI, runtime, and terminal-client behavior
    - frontend validation only when the task touches the dashboard or web contracts
    - documentation updates when contracts, routes, packaging, workflows, dependencies, or operator-visible behavior change

## Completion Contract For Any Task

A task is complete only when all of the following are true:

- the implementation exists in the intended module boundary
- automated tests covering the new behavior exist and pass
- Python lint, typecheck, and focused tests pass for touched backend and CLI code
- frontend lint, typecheck, tests, and build pass if the task touches frontend or web dashboard behavior
- the task does not leave placeholder code or hidden follow-up work outside this file
- the dashboard remains usable through the FastAPI-served production build path
- terminal behavior remains usable in supported TTY and documented fallback contexts
- docs are updated if the task changes dependencies, command behavior, keyboard controls, persistence, transport, runtime ownership, dashboard co-hosting, or the user-facing terminal model

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
src/glassbox/cli/
    interactive_commands.py
    interactive_session.py
    daemon_attach.py
    renderer.py
    tui/
        app.py
        client.py
        state.py
        keybindings.py
        theme.py
        widgets/
src/glassbox/core/
src/glassbox/runtime/
src/glassbox/web/
tests/
    integration/
    unit/
docs/
```

## Recommended Validation Commands

Use the narrowest viable validation after each task, but the baseline validation pattern for completed terminal UX work should include:

```bash
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run pytest
```

During incremental implementation, use narrower commands where possible:

```bash
uv run pytest tests/integration/test_cli_interactive_commands.py
uv run pytest tests/integration/test_cli_renderer.py
uv run pytest tests/unit/test_cli_renderer.py
uv run pytest tests/integration/test_cli_session_commands.py
uv run pytest tests/integration/test_daemon_runtime.py
uv run pytest tests/integration/test_web_session_interaction.py
uv run ruff check src/glassbox/cli tests/integration/test_cli_interactive_commands.py
uv run ty check
```

When a task touches the dashboard partnership, also run the relevant frontend checks:

```bash
pnpm --dir frontend typecheck
pnpm --dir frontend test
pnpm --dir frontend build
```

## Milestone Map

The intended v5 milestone order is:

1. terminal UX audit, interaction contract, and framework decision
2. terminal client architecture and plain-mode compatibility boundary
3. conversation state model derived from canonical events and snapshots
4. full-screen `session chat` Textual shell with co-hosted dashboard context
5. modern transcript, streaming assistant output, composer, and command palette
6. first-class approvals, questions, interruptions, and action feedback
7. tool activity, output handling, file/change awareness, and dashboard handoff
8. attach, reconnect, runtime ownership, fallback, and packaging hardening
9. terminal test harness, manual UX review, docs, and v5 release gate

## Task Graph

---

## Phase 56: Terminal UX Audit And Interaction Contract

### GBX-560: Audit The Current Interactive Terminal Experience

- Status: `DONE`
- Depends on: `GBX-553`
- Goal: establish a concrete, code-aligned UX baseline for `glassbox session chat` and `glassbox session attach` before the TUI migration begins
- Deliverables:
  - terminal UX audit document covering startup, dashboard co-hosting, transcript readability, assistant streaming, tool activity, approvals, questions, slash commands, status, attach, reconnect, interruption, non-TTY behavior, and error recovery: [terminal-ux-audit-v5.md](./terminal-ux-audit-v5.md)
  - representative captured terminal transcripts for idle prompt, initial prompt, multi-turn chat, pending question, pending approval, tool-heavy turn, failed turn, daemon attach, reconnect, and dashboard startup failure: [terminal-ux-audit-v5.md](./terminal-ux-audit-v5.md)
  - issue inventory grouped by severity: workflow blocker, high-friction interaction issue, terminal rendering issue, keyboard/input issue, copy issue, and test coverage gap: [terminal-ux-audit-v5.md](./terminal-ux-audit-v5.md)
  - explicit list of already-good semantics that must be preserved during the redesign: [terminal-ux-audit-v5.md](./terminal-ux-audit-v5.md)
- Implementation notes:
  - inspect the current CLI as a coding-agent user, not only as a command dispatcher
  - compare the current experience against the desired full-screen coding-agent model, not against old line-mode parity
  - include both local in-process chat and daemon-backed attach because users experience them as one terminal product
  - use deterministic test fixtures and provider-free flows where possible
- Tests and validation included in task:
  - current interactive CLI tests pass before audit conclusions are recorded
  - manual transcript capture for at least one local chat and one attach-style workflow
  - no production code changes are required unless trivial instrumentation is needed to capture evidence
- Done when:
  - implementers have a specific, evidence-backed terminal UX baseline and preserved-behavior list

Completion notes:

- Completed in [terminal-ux-audit-v5.md](./terminal-ux-audit-v5.md).
- Validation: `uv run pytest tests/integration/test_cli_interactive_commands.py`.

### GBX-561: Define The v5 Terminal Interaction Model

- Status: `DONE`
- Depends on: `GBX-560`
- Goal: convert the audit and product direction into a concrete interaction contract for the full-screen chat client
- Deliverables:
  - documentation update defining the v5 terminal model: header, conversation transcript, composer, action strip, command palette, optional details pane, and dashboard handoff: [terminal-interaction-model-v5.md](./terminal-interaction-model-v5.md)
  - keyboard contract for sending, multiline editing, command palette, approval, denial, answer submit, interrupt, quit, jump latest, toggle details, open dashboard, copy session ID, and focus movement: [terminal-interaction-model-v5.md](./terminal-interaction-model-v5.md)
  - action-priority rules for pending approvals, questions, active tool calls, failed turns, reconnecting streams, promptability, and historical-only states: [terminal-interaction-model-v5.md](./terminal-interaction-model-v5.md)
  - transcript hierarchy rules for user turns, assistant streaming, tool activity, tool output, files/artifacts, failures, and compact system notices: [terminal-interaction-model-v5.md](./terminal-interaction-model-v5.md)
  - fallback contract for non-TTY, CI, redirected stdin/stdout, and `--plain` compatibility if retained: [terminal-interaction-model-v5.md](./terminal-interaction-model-v5.md)
  - explicit rule that `session chat` remains chat-first while the web dashboard remains the deeper operator console: [terminal-interaction-model-v5.md](./terminal-interaction-model-v5.md)
- Implementation notes:
  - define behavior in terms of coding flow: think, ask, inspect, approve, recover, continue
  - avoid duplicating the v4 dashboard queue and evidence model in the default terminal surface
  - define interruption semantics carefully so Ctrl+C, escape, and model/tool cancellation do not surprise operators
  - keep the model compatible with existing service semantics unless the audit proves a contract is missing
- Tests and validation included in task:
  - doc review against current CLI commands, daemon attach, dashboard co-hosting, event model, and snapshot APIs
  - manual validation that the proposed model does not require browser-owned canonical state or a second runtime control plane
- Done when:
  - the repo has a clear v5 terminal UX contract that implementation tasks can execute without guessing interaction details

Completion notes:

- Completed in [terminal-interaction-model-v5.md](./terminal-interaction-model-v5.md).
- Validation: documentation review against current CLI commands, daemon attach, dashboard co-hosting, event model, and snapshot/API boundaries.

### GBX-562: Choose And Document The Terminal UI Framework

- Status: `DONE`
- Depends on: `GBX-561`
- Goal: make a user-centered dependency decision for the full-screen terminal app before implementation spreads framework assumptions across the CLI
- Deliverables:
  - documented framework decision, with Textual as the intended choice unless research shows a better option: [terminal-framework-decision-v5.md](./terminal-framework-decision-v5.md)
  - comparison against at least prompt-toolkit and a hand-rolled ANSI approach: [terminal-framework-decision-v5.md](./terminal-framework-decision-v5.md)
  - package dependency updates for the chosen framework and any necessary test extras: [pyproject.toml](../pyproject.toml) and [uv.lock](../uv.lock)
  - minimal framework smoke test proving the dependency imports and can run a tiny app under the project test environment: [test_tui_framework_smoke.py](../tests/unit/test_tui_framework_smoke.py)
  - packaging note confirming the dependency works in normal Python package installs: [terminal-framework-decision-v5.md](./terminal-framework-decision-v5.md)
- Implementation notes:
  - optimize for the best user experience and maintainable agent-built evolution, not the smallest dependency list
  - prefer framework features for layout, input, keyboard bindings, async workers, testing, and styled rendering over bespoke terminal control
  - keep dependency additions explicit and reviewable in `pyproject.toml`
- Tests and validation included in task:
  - dependency installation succeeds through the project package manager
  - `uv run pytest` or a focused framework smoke test passes
  - `uv run ty check` remains usable after dependency typing decisions are made
- Done when:
  - the terminal TUI has an accepted framework foundation and the repo can install and test it reliably

Completion notes:

- Completed in [terminal-framework-decision-v5.md](./terminal-framework-decision-v5.md).
- Validation: `uv run pytest tests/unit/test_tui_framework_smoke.py`; `uv run ty check`.

### GBX-563: Define Terminal Test Harness And Review Artifacts

- Status: `DONE`
- Depends on: `GBX-561`, `GBX-562`
- Goal: create repeatable ways to validate full-screen terminal behavior without relying only on manual terminal impressions
- Deliverables:
  - Textual app tests for widget state, keybindings, focus movement, and action dispatch: [terminal-test-harness-v5.md](./terminal-test-harness-v5.md)
  - deterministic terminal transcript or snapshot artifacts for plain fallback and selected TUI states where practical: [terminal-test-harness-v5.md](./terminal-test-harness-v5.md)
  - pty or subprocess smoke strategy for launching `glassbox session chat` in a real terminal-like environment: [terminal-test-harness-v5.md](./terminal-test-harness-v5.md)
  - manual terminal UX review checklist covering desktop terminal sizes, narrow terminal widths, paste behavior, keyboard-only action flows, scrollback, and reconnect states: [terminal-test-harness-v5.md](./terminal-test-harness-v5.md)
  - retention guidance for terminal screenshots, recordings, or text snapshots so local review evidence does not create noisy binary churn: [terminal-test-harness-v5.md](./terminal-test-harness-v5.md)
- Implementation notes:
  - avoid brittle pixel-perfect terminal tests unless they protect a stable invariant
  - prefer deterministic fake sessions and event streams over live provider calls
  - include nonblank primary regions, no uncaught exceptions, visible composer, visible blocking action, and exit cleanup as stable test invariants
- Tests and validation included in task:
  - initial harness test runs in CI-like non-interactive context
  - existing CLI tests continue to pass
- Done when:
  - later TUI tasks have a practical validation path for terminal-specific behavior

Completion notes:

- Completed in [terminal-test-harness-v5.md](./terminal-test-harness-v5.md).
- Initial CI-like Textual harness proof: [test_tui_framework_smoke.py](../tests/unit/test_tui_framework_smoke.py).
- Validation: `uv run pytest tests/unit/test_tui_framework_smoke.py`; `uv run pytest tests/integration/test_cli_interactive_commands.py`.

---

## Phase 57: Terminal Client Architecture And Compatibility Boundary

### GBX-570: Extract A Runtime-Agnostic Interactive Session Client

- Status: `DONE`
- Depends on: `GBX-561`
- Goal: separate terminal UI concerns from local and daemon session control so the TUI can use one client-shaped API
- Deliverables:
  - client abstraction for fetching session state, submitting prompts, submitting answers, resolving approvals, streaming events, and shutting down cleanly
  - local in-process implementation backed by existing runtime context and event transport
  - daemon implementation backed by the existing snapshot, action, and SSE endpoints
  - common error model for unavailable runtime, conflict, validation error, historical-only state, unknown session, and stream reconnect
  - tests proving existing local chat and daemon attach semantics remain unchanged through the new client layer
- Implementation notes:
  - do not move canonical behavior into the UI client; it should call existing services or web APIs
  - keep the local and daemon implementations behaviorally aligned without hiding meaningful runtime ownership differences
  - preserve the existing dashboard co-hosting path for local `session chat`
- Tests and validation included in task:
  - focused unit tests for the client interface using fake local and remote implementations
  - integration tests for local chat and daemon attach still pass
  - `uv run ruff check src/glassbox/cli tests/integration/test_cli_interactive_commands.py`
- Done when:
  - the terminal UI can be built against one session-client contract instead of directly coupling to line-mode loops

Completion notes:

- Added the reusable client boundary in [interactive_client.py](../src/glassbox/cli/interactive_client.py), including local runtime and daemon HTTP/SSE implementations.
- Routed daemon attach actions and SSE parsing through the extracted daemon client while preserving existing line-mode behavior.
- Added focused coverage in [test_cli_interactive_client.py](../tests/unit/test_cli_interactive_client.py).
- Validation: `uv run pytest tests/unit/test_cli_interactive_client.py tests/integration/test_cli_interactive_commands.py`; `uv run ruff check src/glassbox/cli/interactive_client.py src/glassbox/cli/daemon_attach.py tests/unit/test_cli_interactive_client.py`; `uv run ty check`.

### GBX-571: Preserve Or Retire Line Mode Behind An Explicit Boundary

- Status: `DONE`
- Depends on: `GBX-570`
- Goal: decide and implement the compatibility boundary for the old line-oriented interactive loop during the TUI migration
- Deliverables:
  - explicit command behavior for TTY, non-TTY, CI, redirected stdin/stdout, and `--plain` if retained
  - parser and docs updates for any `--plain`, `--tui`, or automatic fallback behavior
  - old line-mode code isolated as a fallback path or marked for removal behind a task-gated release decision
  - tests proving non-interactive environments do not accidentally launch an unusable full-screen app
- Implementation notes:
  - default `glassbox session chat` should become the full-screen TUI once the release gate permits it
  - retaining plain mode during migration is acceptable for tests, dumb terminals, and debugging
  - do not let fallback support force the TUI interaction model to stay line-mode-shaped
- Tests and validation included in task:
  - CLI parser tests for new flags or fallback behavior
  - subprocess or monkeypatched TTY tests for plain versus TUI selection
  - existing line-mode tests either remain valid for fallback or are deliberately migrated
- Done when:
  - implementation tasks know whether they are updating a fallback line loop or the primary TUI path

Completion notes:

- Added explicit launch-mode resolution in [interactive_launch.py](../src/glassbox/cli/interactive_launch.py).
- Added `--plain` and `--tui` parser flags for `session chat` and `session attach`; `--plain` runs the retained line-mode boundary, while `--tui` is parsed and rejected until the TUI module exists.
- Documented the current fallback boundary in [terminal-interaction-model-v5.md](./terminal-interaction-model-v5.md).
- Added unit/parser coverage in [test_cli_interactive_launch.py](../tests/unit/test_cli_interactive_launch.py) and command-level coverage in [test_cli_interactive_commands.py](../tests/integration/test_cli_interactive_commands.py).
- Validation: `uv run pytest tests/unit/test_cli_interactive_launch.py tests/integration/test_cli_interactive_commands.py`; `uv run ruff check src/glassbox/cli/interactive_launch.py src/glassbox/cli/parser_sessions.py src/glassbox/cli/interactive_commands.py tests/unit/test_cli_interactive_launch.py tests/integration/test_cli_interactive_commands.py`; `uv run ty check`.

### GBX-572: Add Terminal-App Module Boundaries

- Status: `DONE`
- Depends on: `GBX-570`, `GBX-571`
- Goal: create the TUI package structure without mixing full-screen UI code into the current command handlers
- Deliverables:
  - `src/glassbox/cli/tui/` package with app, client adapter, state, widgets, keybindings, and theme module boundaries
  - minimal app factory that accepts a session client, initial session metadata, dashboard URL, and launch options
  - command handler integration seam that can launch the app without taking over runtime ownership rules
  - tests proving the app can be constructed with a fake client and closed without side effects
- Implementation notes:
  - keep framework-specific widgets below the TUI boundary
  - keep pure state derivation importable without Textual so it remains easy to unit test
  - keep command dispatch thin; it should select runtime ownership and launch mode, not render the chat UI directly
- Tests and validation included in task:
  - app construction smoke test
  - import-boundary tests or lint review where practical
  - `uv run ty check`
- Done when:
  - later tasks have a stable home for TUI implementation without bloating existing line-mode modules

Completion notes:

- Added the initial Textual package under [src/glassbox/cli/tui](../src/glassbox/cli/tui), split into app, client adapter, state, widgets, keybindings, and theme modules.
- Added `create_tui_app` and `run_tui_app` seams so command handlers can launch the app against an `InteractiveSessionClient` without owning Textual internals.
- Added construction, mount, and cleanup coverage in [test_cli_tui_app.py](../tests/unit/test_cli_tui_app.py).
- Validation: `uv run pytest tests/unit/test_cli_tui_app.py tests/unit/test_tui_framework_smoke.py`; `uv run ruff check src/glassbox/cli/tui tests/unit/test_cli_tui_app.py`; `uv run ty check`.

### GBX-573: Align Dashboard Co-Hosting With The TUI Launch Lifecycle

- Status: `DONE`
- Depends on: `GBX-572`
- Goal: preserve the co-hosted dashboard as the paired operator console while launching the full-screen terminal app
- Deliverables:
  - TUI launch flow that starts the dashboard before session start when enabled, records the session dashboard URL, and stops the dashboard on clean local chat exit
  - header or command-palette access to the dashboard URL after launch
  - clear terminal-visible dashboard startup, unavailable, and explicit-binding failure states
  - tests proving existing `--dashboard-host`, `--dashboard-port`, and `--no-dashboard` behavior remains correct
- Implementation notes:
  - local `session chat` owns the co-hosted dashboard lifecycle; daemon attach should surface the daemon dashboard URL when available
  - the TUI should never require the browser to be open in order to chat
  - dashboard startup failure should not corrupt the full-screen terminal lifecycle
- Tests and validation included in task:
  - adapted dashboard sidecar tests from current interactive coverage
  - TUI fake-client test for displaying or exposing dashboard URL
  - manual launch smoke with `--no-dashboard` and default dashboard mode
- Done when:
  - the browser operator console remains naturally paired with terminal chat after the TUI migration

Completion notes:

- Added [lifecycle.py](../src/glassbox/cli/tui/lifecycle.py) so the TUI app is created from an `InteractiveSessionClient` snapshot after the command layer has resolved runtime ownership and dashboard lifecycle.
- Updated TUI state/header plumbing to expose a session-specific dashboard URL derived from the dashboard base URL and current session id.
- Documented the current dashboard handoff boundary in [terminal-interaction-model-v5.md](./terminal-interaction-model-v5.md).
- Added TUI dashboard URL coverage in [test_cli_tui_app.py](../tests/unit/test_cli_tui_app.py) and re-ran existing dashboard sidecar integration coverage in [test_cli_interactive_commands.py](../tests/integration/test_cli_interactive_commands.py).
- Validation: `uv run pytest tests/unit/test_cli_tui_app.py tests/integration/test_cli_interactive_commands.py`; `uv run ruff check src/glassbox/cli/tui tests/unit/test_cli_tui_app.py tests/integration/test_cli_interactive_commands.py`; `uv run ty check`.

---

## Phase 58: Conversation State Model

### GBX-580: Build A Pure Terminal Conversation State Reducer

- Status: `DONE`
- Depends on: `GBX-570`, `GBX-563`
- Goal: derive a chat-first terminal view model from canonical events, snapshots, and local UI drafts
- Deliverables:
  - pure Python state reducer for session header state, conversation turns, assistant streaming text, tool activity, pending approvals, pending questions, failures, reconnect state, and dashboard context
  - deterministic event application for historical replay and live stream updates
  - local-only composer draft state separated from canonical conversation state
  - tests covering normal, live, tool-heavy, approval, question, failed, partial-history, reconnect, and historical-only sessions
- Implementation notes:
  - do not infer authoritative turn state beyond backend events and snapshots
  - make unknown or partial relationships explicit in the view model
  - keep raw event sequence numbers available for diagnostics even if not visible in the default transcript
  - design the state model for TUI rendering but keep it independent from Textual widgets
- Tests and validation included in task:
  - unit tests for reducer event sequences using realistic fixtures
  - regression tests against current CLI fixture flows where possible
  - `uv run ty check`
- Done when:
  - TUI widgets can render a coherent conversation without each widget independently interpreting raw events

Completion notes:

- Added the pure Textual-free reducer in [conversation.py](../src/glassbox/cli/tui/conversation.py), deriving terminal header, conversation messages, turn shells, tool activity, pending approval/question, failure, stream, dashboard, and composer draft state from snapshots and events.
- Event reduction is deterministic by sequence and keeps raw event sequence numbers on view-model records for diagnostics.
- Added focused coverage in [test_cli_tui_conversation.py](../tests/unit/test_cli_tui_conversation.py) for normal, live streaming, tool-heavy, approval, question, failed, partial-history, reconnect, historical-only, and draft-separation cases.
- Validation: `uv run pytest tests/unit/test_cli_tui_conversation.py`; `uv run ruff check src/glassbox/cli/tui/conversation.py tests/unit/test_cli_tui_conversation.py`; `uv run ty check`.

### GBX-581: Model Turn-Grouped Messages And Tool Activity

- Status: `DONE`
- Depends on: `GBX-580`
- Goal: make terminal chat readable as a sequence of user intent, assistant reasoning/output, and tool work rather than isolated event lines
- Deliverables:
  - turn-grouped view models for user messages, assistant messages, active assistant stream, tool requests, tool starts, tool output snippets, tool completions, artifacts, failures, and policy decisions
  - compact summary fields for tool name, status, risk, policy source, duration or exit code when available, and result summary
  - expandable detail payloads for tool output, arguments, artifact paths, and failure snippets
  - fallback grouping for imported, partial, or historical sessions
- Implementation notes:
  - preserve raw transcript message ordering
  - avoid duplicating the full dashboard evidence model; terminal details should support coding flow and hand off to the dashboard for deeper inspection
  - treat tool failures as important conversation moments, not buried log lines
- Tests and validation included in task:
  - reducer tests for tool lifecycle combinations
  - output clipping and expansion-state tests
  - fixture coverage for tool output chunks and artifacts
- Done when:
  - terminal transcript rendering can show useful tool work inline without flooding the conversation

Completion notes:

- Extended [conversation.py](../src/glassbox/cli/tui/conversation.py) with turn-grouped user and assistant messages, active assistant stream grouping, tool activity details, model metrics, turn failures, and imported partial-history fallback groups.
- Tool activity now carries arguments, policy outcome/risk/source metadata, output chunks, clipped previews, artifact paths, exit code, result summary, and local expansion state.
- Added reducer coverage in [test_cli_tui_conversation.py](../tests/unit/test_cli_tui_conversation.py) for trigger-message grouping, assistant stream grouping, tool policy/detail metadata, output clipping, expansion state, artifacts, and turn failure grouping.
- Validation: `uv run pytest tests/unit/test_cli_tui_conversation.py`; `uv run ruff check src/glassbox/cli/tui/conversation.py tests/unit/test_cli_tui_conversation.py`; `uv run ty check`.

### GBX-582: Model Priority Actions For Questions And Approvals

- Status: `DONE`
- Depends on: `GBX-580`
- Goal: derive first-class action cards for pending operator decisions
- Deliverables:
  - action view model for pending question, pending approval, unavailable prompt, active turn wait state, failed turn, and historical-only state
  - approval fields for subject, reason, risk level, policy source, related tool, approval ID, and allowed decisions
  - question fields for prompt text, question ID, related turn, and answer draft ownership
  - conflict and resolved-state handling after mutations and stream updates
- Implementation notes:
  - action priority should match the interaction model: approvals and questions above generic prompting when they block progress
  - never treat arbitrary freeform input as approval resolution
  - keep action IDs available for debugging and copy commands, but do not make users copy them in normal chat
- Tests and validation included in task:
  - unit tests for action priority and state transitions
  - tests for stale approval/question resolution after stream updates
- Done when:
  - the TUI can render the current blocking operator decision without scraping status strings

Completion notes:

- Added `TerminalActionState` derivation in [conversation.py](../src/glassbox/cli/tui/conversation.py) for prompt, pending approval, pending question, active-turn wait, unavailable prompt, failed, and historical-only states.
- Approval actions now expose subject, reason, approval ID, allowed decisions, related tool, policy risk/source, and debug ID without interpreting freeform composer input as approval resolution.
- Question actions expose question ID, prompt text, related turn/tool, and matching answer draft ownership.
- Added stale resolved approval/question and action-priority coverage in [test_cli_tui_conversation.py](../tests/unit/test_cli_tui_conversation.py).
- Validation: `uv run pytest tests/unit/test_cli_tui_conversation.py`; `uv run ruff check src/glassbox/cli/tui/conversation.py tests/unit/test_cli_tui_conversation.py`; `uv run ty check`.

### GBX-583: Model Runtime, Stream, And Dashboard Status For The Header

- Status: `DONE`
- Depends on: `GBX-580`
- Goal: create a compact terminal header state that orients the user without becoming an operator dashboard
- Deliverables:
  - header view model for session ID, model, cwd/workspace, branch label, runtime owner, stream status, current mode, dashboard URL, and last update state
  - short labels for starting, ready, thinking, running tool, awaiting approval, awaiting answer, reconnecting, unavailable, historical-only, and failed
  - terminal-width-aware truncation rules for paths, session IDs, and model names
  - tests for header state under narrow and normal terminal widths
- Implementation notes:
  - keep status concise; the header is orientation, not the v4 status rail
  - make dashboard availability persistent and discoverable after the initial startup line disappears
  - do not let status changes cause disruptive layout shifts
- Tests and validation included in task:
  - unit tests for status derivation and truncation
  - TUI snapshot or widget tests once header widget exists
- Done when:
  - users can always tell what session they are in and whether the runtime is ready for the next action

Completion notes:

- Added `TerminalHeaderDisplayState` derivation in [conversation.py](../src/glassbox/cli/tui/conversation.py) for compact session, mode, stream, model, workspace, branch, runtime owner, dashboard, and last-update labels.
- Added short status labels for starting, ready, thinking, running tool, awaiting approval, awaiting answer, reconnecting, unavailable, historical-only, and failed states.
- Added terminal-width-aware truncation helpers for long paths, model names, branch labels, and runtime owner labels.
- Added normal and narrow-width header coverage in [test_cli_tui_conversation.py](../tests/unit/test_cli_tui_conversation.py).
- Validation: `uv run pytest tests/unit/test_cli_tui_conversation.py`; `uv run ruff check src/glassbox/cli/tui/conversation.py tests/unit/test_cli_tui_conversation.py`; `uv run ty check`.

---

## Phase 59: Full-Screen TUI Shell

### GBX-590: Launch A Minimal Full-Screen `session chat` App

- Status: `DONE`
- Depends on: `GBX-572`, `GBX-573`, `GBX-580`
- Goal: make `glassbox session chat` capable of opening a real full-screen terminal app for a new session
- Deliverables:
  - Textual app with header, transcript region, action strip placeholder, composer placeholder, and footer/help hint
  - initial session start flow wired through the session client
  - live event ingestion into the pure conversation state reducer
  - clean exit path that stops local resources and leaves session state persisted
  - temporary feature flag or launch selection if TUI is not yet default during this slice
- Implementation notes:
  - this MVP does not need polished transcript rendering yet; it proves lifecycle, layout, state flow, and clean shutdown
  - avoid blocking the UI event loop on runtime calls or event stream reads
  - keep dashboard co-hosting visible in the header or startup state
- Tests and validation included in task:
  - Textual app test for launch, initial render, and exit
  - integration smoke for `session chat --no-dashboard` in TUI-capable context if practical
  - existing line-mode tests continue to pass or are explicitly scoped to fallback
- Done when:
  - a developer can start a new Glassbox session in a full-screen terminal app without losing existing runtime semantics

Completion notes:

- Wired explicit `session chat --tui` through [interactive_commands.py](../src/glassbox/cli/interactive_commands.py), while preserving plain mode and non-interactive TUI rejection.
- Reworked [app.py](../src/glassbox/cli/tui/app.py) around the pure conversation reducer, live event streaming, session-specific dashboard URLs, widget updates, and idempotent client shutdown.
- Added minimal header, conversation, action strip, composer, and footer widgets in [widgets.py](../src/glassbox/cli/tui/widgets.py), plus shell styling in [theme.py](../src/glassbox/cli/tui/theme.py).
- Added Textual coverage for mount/exit and live event ingestion in [test_cli_tui_app.py](../tests/unit/test_cli_tui_app.py), plus an integration smoke for the TUI chat launch boundary in [test_cli_interactive_commands.py](../tests/integration/test_cli_interactive_commands.py).
- Validation: `uv run pytest tests/unit/test_cli_tui_app.py tests/unit/test_cli_tui_conversation.py tests/unit/test_cli_interactive_launch.py tests/integration/test_cli_interactive_commands.py`; `uv run ruff check src/glassbox/cli/tui src/glassbox/cli/interactive_commands.py tests/unit/test_cli_tui_app.py tests/integration/test_cli_interactive_commands.py`; `uv run ty check`.

### GBX-591: Add The TUI Header, Footer, And Theme Foundation

- Status: `DONE`
- Depends on: `GBX-590`, `GBX-583`
- Goal: establish a calm, coding-agent-oriented terminal visual system
- Deliverables:
  - header widget for session, workspace, model, stream, mode, and dashboard URL/access hint
  - footer or help strip for the most important keyboard controls
  - restrained terminal theme for normal, muted, success, warning, danger, active, and focus states
  - narrow-terminal behavior with useful truncation rather than broken layout
  - tests for header/footer rendering across representative state
- Implementation notes:
  - avoid decorative terminal chrome; the interface should feel focused and quiet
  - reserve high-salience color for blocking approvals, questions, failures, and connection problems
  - keep visible shortcuts stable so users build muscle memory
- Tests and validation included in task:
  - widget tests for header/footer states
  - manual review at common terminal sizes such as 80x24, 100x30, and wider panes
- Done when:
  - the full-screen app has a coherent frame that orients users without overwhelming the chat

Completion notes:

- Added width-aware header/footer render helpers in [widgets.py](../src/glassbox/cli/tui/widgets.py), including dashboard URL disclosure on wider terminals and stable fallback labels on narrow terminals.
- Updated the `SessionHeader` and `FooterHelp` widgets to refresh from mounted terminal width without relying on unavailable layout during composition.
- Expanded [theme.py](../src/glassbox/cli/tui/theme.py) with restrained terminal surfaces plus reusable normal, muted, success, warning, danger, active, and focus status classes.
- Added direct widget/theme coverage in [test_cli_tui_widgets.py](../tests/unit/test_cli_tui_widgets.py) for wide header rendering, narrow truncation, footer collapse, and theme hooks.
- Validation: `uv run pytest tests/unit/test_cli_tui_widgets.py tests/unit/test_cli_tui_app.py tests/unit/test_cli_tui_conversation.py`; `uv run ruff check src/glassbox/cli/tui tests/unit/test_cli_tui_widgets.py tests/unit/test_cli_tui_app.py`; `uv run ty check`.

### GBX-592: Render The Conversation Transcript Surface

- Status: `DONE`
- Depends on: `GBX-590`, `GBX-581`
- Goal: replace flat event scrollback with a stable chat transcript region
- Deliverables:
  - scrollable transcript widget rendering user messages, assistant messages, active assistant stream, compact tool cards, system notices, and failures
  - latest-activity autoscroll behavior that does not fight deliberate user scrolling
  - keyboard control to jump to latest activity
  - empty, starting, and no-message states
  - readable wrapping for markdown text, code blocks, file paths, and long tool names
- Implementation notes:
  - chat content is primary; do not frame every message as a heavy card
  - use markdown rendering where it improves readability, but keep output stable and terminal-width-aware
  - prevent long output from making the composer unreachable
- Tests and validation included in task:
  - widget tests for transcript rendering across fixture states
  - long-message and narrow-width tests
  - manual review with tool-heavy and markdown-heavy assistant output
- Done when:
  - the main terminal region reads like a conversation rather than an event log

Completion notes:

- Replaced the placeholder conversation text with a width-aware transcript renderer in [widgets.py](../src/glassbox/cli/tui/widgets.py) for user, assistant, runtime/system, tool, turn failure, and session failure content.
- Made the transcript pane focusable and scrollable, with follow-latest behavior that only autoscrolls when already at latest activity.
- Added the `Ctrl+L` latest-activity keybinding and app action in [keybindings.py](../src/glassbox/cli/tui/keybindings.py) and [app.py](../src/glassbox/cli/tui/app.py).
- Added transcript coverage in [test_cli_tui_widgets.py](../tests/unit/test_cli_tui_widgets.py) for chat messages, compact tool cards, wrapping, and empty/historical states; added keybinding coverage in [test_cli_tui_app.py](../tests/unit/test_cli_tui_app.py).
- Validation: `uv run pytest tests/unit/test_cli_tui_widgets.py tests/unit/test_cli_tui_app.py tests/unit/test_cli_tui_conversation.py`; `uv run ruff check src/glassbox/cli/tui tests/unit/test_cli_tui_widgets.py tests/unit/test_cli_tui_app.py`; `uv run ty check`.

### GBX-593: Implement Live Assistant Streaming In The Transcript

- Status: `DONE`
- Depends on: `GBX-592`
- Goal: make assistant output feel live while keeping canonical completed messages correct
- Deliverables:
  - active assistant stream rendering from `AssistantMessageDelta` events
  - smooth replacement or finalization when `AssistantMessageCompleted` arrives
  - visual distinction between streaming, completed, interrupted, and failed assistant output
  - tests for delta ordering, duplicate or late completion, and partial stream cleanup on failure
- Implementation notes:
  - do not create canonical transcript text in the UI; derive display text from streamed events and completed message payloads
  - avoid excessive re-render churn for fast token streams
  - preserve the ability to inspect exact event history in the dashboard or details surface
- Tests and validation included in task:
  - reducer tests for assistant delta/completion sequences
  - TUI tests for visible streaming updates
  - manual real-provider or fake-stream smoke where practical
- Done when:
  - users see the assistant answer unfold in the terminal without waiting for final completion

Completion notes:

- Extended assistant display status in [conversation.py](../src/glassbox/cli/tui/conversation.py) to distinguish streaming, completed, interrupted, and failed assistant output.
- Made assistant delta handling ignore late deltas after completion and made duplicate/late completion payloads idempotent for already completed, failed, or interrupted streams.
- Marked partial assistant streams failed on turn/session failure and interrupted on cancelled/interrupted session completion, preserving partial text for inspection.
- Updated [widgets.py](../src/glassbox/cli/tui/widgets.py) so the transcript visibly labels completed, streaming, interrupted, and failed assistant output.
- Added reducer and transcript tests in [test_cli_tui_conversation.py](../tests/unit/test_cli_tui_conversation.py) and [test_cli_tui_widgets.py](../tests/unit/test_cli_tui_widgets.py) for delta ordering, late events, duplicate completion, failure cleanup, interruption cleanup, and visible failed stream labels.
- Validation: `uv run pytest tests/unit/test_cli_tui_conversation.py tests/unit/test_cli_tui_widgets.py tests/unit/test_cli_tui_app.py`; `uv run ruff check src/glassbox/cli/tui tests/unit/test_cli_tui_conversation.py tests/unit/test_cli_tui_widgets.py tests/unit/test_cli_tui_app.py`; `uv run ty check`.

---

## Phase 60: Composer, Commands, And Keyboard Flow

### GBX-600: Build The Multiline Composer

- Status: `DONE`
- Depends on: `GBX-590`, `GBX-571`
- Goal: make prompt entry feel like a modern coding-agent composer rather than a single `input()` line
- Deliverables:
  - multiline composer with readable editing, paste handling, wrapping, and draft preservation
  - send/newline key behavior defined by the interaction model
  - disabled or redirected composer states for active turn, pending approval, historical-only session, unavailable runtime, and reconnecting stream
  - local prompt history for the current session or workspace if approved by the interaction model
  - tests for typing, multiline input, send, clear, disabled states, and draft preservation
- Implementation notes:
  - composer draft is local UI state and must not be treated as canonical session data until submitted
  - preserve drafts across recoverable mutation failures and focus changes
  - do not let live updates steal focus while the user is typing
- Tests and validation included in task:
  - Textual input tests for common keyboard paths
  - reducer/client tests for submit dispatch and failure preservation
  - manual paste test with multiline code or markdown
- Done when:
  - users can write substantial coding prompts comfortably inside the terminal app

Completion notes:

- Replaced the placeholder composer with a multiline `TextArea`-backed `ComposerWidget` in [widgets.py](../src/glassbox/cli/tui/widgets.py), with soft wrapping, placeholder guidance, read-only blocked states, and local draft synchronization.
- Added composer availability derivation for ready, active turn, pending approval, pending question, reconnecting, unavailable, failed, and historical states.
- Wired `Ctrl+Enter`/`Ctrl+S` prompt submission through [app.py](../src/glassbox/cli/tui/app.py) and [client.py](../src/glassbox/cli/tui/client.py), preserving drafts until the client accepts the prompt.
- Added local prompt history navigation in the app and composer widget, with previous/next history actions for the current TUI session.
- Added Textual tests in [test_cli_tui_app.py](../tests/unit/test_cli_tui_app.py) for multiline submit, draft clearing, draft preservation during live updates, and prompt history; added availability tests in [test_cli_tui_widgets.py](../tests/unit/test_cli_tui_widgets.py).
- Validation: `uv run pytest tests/unit/test_cli_tui_app.py tests/unit/test_cli_tui_widgets.py tests/unit/test_cli_tui_conversation.py`; `uv run ruff check src/glassbox/cli/tui tests/unit/test_cli_tui_app.py tests/unit/test_cli_tui_widgets.py`; `uv run ty check`.

### GBX-601: Add Command Palette And Shortcut Discovery

- Status: `DONE`
- Depends on: `GBX-600`, `GBX-591`
- Goal: replace hidden slash-command discovery with a modern keyboard command surface
- Deliverables:
  - command palette for status, open dashboard, copy session ID, copy dashboard URL, toggle details, jump latest, approve, deny, submit answer, interrupt, clear visual transcript, and quit
  - context-aware command availability and disabled reasons
  - shortcut help surface reachable from the footer
  - optional slash-command compatibility that routes into the same command registry
  - tests for command filtering, execution, disabled states, and focus restoration
- Implementation notes:
  - keep commands keyboard-first and predictable
  - do not make slash commands the only way to discover important actions
  - palette actions should dispatch intents through the same client/action layer as visible buttons or keybindings
- Tests and validation included in task:
  - command registry unit tests
  - Textual tests for opening, filtering, selecting, and closing the palette
  - accessibility-style keyboard review for pointer-free operation
- Done when:
  - users can discover and execute terminal actions without memorizing hidden commands

Completion notes:

- Added a pure command registry in [commands.py](../src/glassbox/cli/tui/commands.py) covering status, dashboard, copy, details, latest, approval, answer, interrupt, clear-transcript, and quit commands.
- Added context-aware command availability and disabled reasons for dashboard absence, missing approvals/questions, empty answer drafts, inactive turns, and empty transcripts.
- Added slash-command compatibility aliases such as `/dashboard`, `/copy-session`, `/latest`, `/approve`, `/deny`, `/answer`, `/clear`, and `/quit` through the same registry.
- Added a `Ctrl+P` command palette overlay in [widgets.py](../src/glassbox/cli/tui/widgets.py), with filtering, selection, shortcut display, disabled reasons, escape close, and enter execution.
- Wired palette execution in [app.py](../src/glassbox/cli/tui/app.py) for dashboard open/copy, session ID copy, latest jump, approval decisions, answer submit, details toggle, local transcript clear, and quit.
- Added registry tests in [test_cli_tui_commands.py](../tests/unit/test_cli_tui_commands.py) and Textual tests in [test_cli_tui_app.py](../tests/unit/test_cli_tui_app.py) for palette open/filter/close and command execution.
- Validation: `uv run pytest tests/unit/test_cli_tui_commands.py tests/unit/test_cli_tui_app.py tests/unit/test_cli_tui_widgets.py`; `uv run ruff check src/glassbox/cli/tui tests/unit/test_cli_tui_commands.py tests/unit/test_cli_tui_app.py tests/unit/test_cli_tui_widgets.py`; `uv run ty check`.

### GBX-602: Implement Keyboard-First Navigation And Focus Rules

- Status: `DONE`
- Depends on: `GBX-600`, `GBX-601`
- Goal: make the TUI fast and predictable without a pointer
- Deliverables:
  - keyboard paths for composer focus, transcript scroll, jump latest, action strip focus, details pane toggle, command palette, dashboard open/copy, approval decision, answer submit, and quit
  - focus restoration after modals, command palette, action completion, and errors
  - keybinding conflict review against common terminal, shell, and Textual defaults
  - tests for high-frequency keyboard workflows
- Implementation notes:
  - optimize for the chat loop: type, send, read, approve, inspect, continue
  - avoid surprising use of Ctrl+C; define whether it cancels current UI action, requests turn interruption, or exits with confirmation based on state
  - ensure live updates never steal focus from an operator composing text or deciding an approval
- Tests and validation included in task:
  - Textual tests for focus movement and shortcut dispatch
  - manual keyboard-only review from app launch to prompt submit to approval resolution
- Done when:
  - the terminal app can be operated fluidly from the keyboard for the core coding-agent workflow

Completion notes:

- Added keyboard actions in [keybindings.py](../src/glassbox/cli/tui/keybindings.py) for composer focus, transcript paging, latest jump, action/details access, command palette, dashboard open/copy, approval, denial, answer submit, interrupt, submit prompt, and quit.
- Added app-level focus and dispatch rules in [app.py](../src/glassbox/cli/tui/app.py), routing shortcut actions through the same command execution path as the palette where possible.
- Added a minimal focusable `DetailsPane` and focusable action strip in [widgets.py](../src/glassbox/cli/tui/widgets.py) so details and action workflows have keyboard targets before their richer Phase 61 implementations.
- Preserved focus after palette close and moved focus deliberately after details toggles and composer focus commands; live updates continue updating state without stealing composer focus.
- Reviewed shortcuts against current terminal/Textual usage: `Ctrl+Q`, `Ctrl+L`, `Ctrl+P`, `Ctrl+G`, `Ctrl+E`, `Ctrl+D`, `Alt+D`, `Alt+A`, `Alt+X`, `Ctrl+R`, `Ctrl+C`, `Ctrl+Enter`, and `Ctrl+S` are declared explicitly in one keybinding table.
- Added Textual tests in [test_cli_tui_app.py](../tests/unit/test_cli_tui_app.py) for keybinding declarations, palette focus restoration, composer focus, details toggle/focus, and answer submission through the keyboard action path.
- Validation: `uv run pytest tests/unit/test_cli_tui_app.py tests/unit/test_cli_tui_commands.py tests/unit/test_cli_tui_widgets.py`; `uv run ruff check src/glassbox/cli/tui tests/unit/test_cli_tui_app.py tests/unit/test_cli_tui_commands.py tests/unit/test_cli_tui_widgets.py`; `uv run ty check`.

### GBX-603: Add Prompt Submission Feedback And Recovery

- Status: `DONE`
- Depends on: `GBX-600`, `GBX-570`
- Goal: make prompt submission states trustworthy and recoverable
- Deliverables:
  - pending, accepted, conflict, validation-error, network-error, unavailable-runtime, and retryable failure states near the composer
  - draft preservation for recoverable failures
  - clear unavailable reasons when a prompt cannot be submitted
  - tests for stale state, conflict, network failure, and successful submission
- Implementation notes:
  - after mutation, rely on snapshot refresh and event stream updates for canonical state
  - do not clear the composer until the prompt is accepted by the runtime/client layer
  - avoid generic `failed` copy when a normalized reason exists
- Tests and validation included in task:
  - client fake tests for mutation outcomes
  - Textual tests for composer feedback states
- Done when:
  - users can tell whether their prompt was sent and what to do if it was not

Completion notes:

- Added local composer submission feedback in [widgets.py](../src/glassbox/cli/tui/widgets.py) for pending, accepted, conflict, validation-error, network-error, unavailable-runtime, and retryable failure states.
- Added a near-composer feedback line in [app.py](../src/glassbox/cli/tui/app.py) and [theme.py](../src/glassbox/cli/tui/theme.py), keeping feedback separate from canonical conversation state.
- Updated prompt submission to set pending before dispatch, clear drafts only after client acceptance, preserve drafts for recoverable failures, and map normalized `InteractiveClientError` kinds to user-facing recovery states.
- Made blank slash-command parsing safe in [commands.py](../src/glassbox/cli/tui/commands.py), so empty submits report validation feedback rather than raising.
- Added Textual and widget tests in [test_cli_tui_app.py](../tests/unit/test_cli_tui_app.py) and [test_cli_tui_widgets.py](../tests/unit/test_cli_tui_widgets.py) for pending, accepted, validation, conflict, network, unavailable-runtime, retryable failure, and draft preservation behavior.
- Validation: `uv run pytest tests/unit/test_cli_tui_app.py tests/unit/test_cli_tui_widgets.py tests/unit/test_cli_tui_commands.py`; `uv run ruff check src/glassbox/cli/tui tests/unit/test_cli_tui_app.py tests/unit/test_cli_tui_widgets.py tests/unit/test_cli_tui_commands.py`; `uv run ty check`.

---

## Phase 61: Action Workflows And Tool Activity

### GBX-610: Build First-Class Question Answer Workflow

- Status: `DONE`
- Depends on: `GBX-582`, `GBX-600`, `GBX-602`
- Goal: make pending `ask_user` questions feel like part of the conversation rather than a mode switch hidden in the prompt label
- Deliverables:
  - pending question action card with question text, related turn context, answer composer state, submit action, and unavailable states
  - keyboard shortcut and command-palette action for focusing or submitting the answer
  - inline pending, success, conflict, validation-error, and network-error feedback
  - tests for answer submission, stale question, recoverable failure, and stream-driven resolution
- Implementation notes:
  - freeform composer behavior may answer the question when the interaction model says it should, but the UI must make that routing obvious
  - preserve answer drafts across recoverable errors and live updates
  - do not expose question IDs as required normal-flow input
- Tests and validation included in task:
  - component/widget tests for question card states
  - integration test for provider-free question flow through the TUI client
  - manual keyboard-only answer workflow review
- Done when:
  - a pending question is visually first, easy to answer, and backed by reliable feedback

Completion notes:
- Added a first-class pending question action card, question-scoped answer drafts, and answer submission feedback for pending, accepted, stale/conflict, validation, runtime unavailable, and retryable failure states.
- Preserved answer drafts across recoverable failures and stream updates while clearing accepted drafts only after client acceptance.
- Validated with `uv run pytest tests/unit/test_cli_tui_app.py tests/unit/test_cli_tui_widgets.py tests/unit/test_cli_tui_commands.py`, `uv run ruff check src/glassbox/cli/tui tests/unit/test_cli_tui_app.py tests/unit/test_cli_tui_widgets.py tests/unit/test_cli_tui_commands.py`, and `uv run ty check`.

### GBX-611: Build First-Class Approval Workflow

- Status: `DONE`
- Depends on: `GBX-582`, `GBX-600`, `GBX-602`
- Goal: make risky tool approvals deliberate, informative, and fast from the terminal
- Deliverables:
  - approval action card with subject, reason, tool name, risk level, policy source, approval ID detail, approve action, deny action, and view-details action
  - keyboard shortcuts for approve and deny only when focus/context makes them safe
  - inline pending, success, conflict, validation-error, network-error, and already-resolved states
  - optional confirmation behavior for high-risk approvals if the interaction model requires it
  - tests for approve, deny, conflict, validation error, network failure, and stream-driven resolution
- Implementation notes:
  - approval resolution must remain explicit and visually distinct from prompts and question answers
  - do not hide risk or policy source behind decoration; these are trust-critical fields
  - after mutation, rely on canonical events and snapshots for resolved state
- Tests and validation included in task:
  - widget tests for approval card states
  - integration test for approval resolution through the TUI client
  - manual review with command/tool approval scenarios
- Done when:
  - the most urgent approval decision is visible, keyboard reachable, and safe to resolve without copying IDs

Completion notes:
- Added a first-class approval action card with subject, reason, linked tool name, risk level, policy source, approval ID detail, approve/deny shortcuts, and details affordance.
- Routed approve and deny through feedback-aware command handling with pending, accepted, conflict, validation, network, runtime-unavailable, retryable failure, and already-resolved states.
- Validated with `uv run pytest tests/unit/test_cli_tui_app.py tests/unit/test_cli_tui_widgets.py tests/unit/test_cli_tui_commands.py`, `uv run ruff check src/glassbox/cli/tui tests/unit/test_cli_tui_app.py tests/unit/test_cli_tui_widgets.py tests/unit/test_cli_tui_commands.py`, and `uv run ty check`.

### GBX-612: Render Tool Activity As Inline Conversation Objects

- Status: `DONE`
- Depends on: `GBX-581`, `GBX-592`
- Goal: make tool work understandable without turning the transcript into raw logs
- Deliverables:
  - compact tool cards for requested, running, awaiting approval, completed, failed, and artifact-recorded states
  - status text for policy outcome, risk, summary, exit code, duration, and output truncation where available
  - expandable detail for arguments, output chunks, stderr/stdout snippets, artifact path, and failure summary
  - stable rendering for long paths and noisy command output
  - tests for common tool lifecycle sequences and narrow terminal widths
- Implementation notes:
  - tool cards belong under the relevant turn and should support chat comprehension first
  - default display should summarize, not flood
  - raw evidence remains available through the dashboard and optional details pane
- Tests and validation included in task:
  - widget tests for tool states and expansion
  - reducer tests for output chunk aggregation and truncation
  - manual review with `run_tests` and patch-like tool scenarios
- Done when:
  - users can see what the agent is doing without losing the conversational thread

Completion notes:
- Reworked transcript tool rendering into compact inline cards with requested, running, awaiting-approval, completed, failed, policy, risk, summary, exit-code, output-truncation, and artifact-path context.
- Honored reducer-backed expanded tool state for arguments, full output preview, artifacts, and failure summaries while keeping long paths and noisy output width-stable.
- Validated with `uv run pytest tests/unit/test_cli_tui_app.py tests/unit/test_cli_tui_widgets.py tests/unit/test_cli_tui_commands.py`, `uv run ruff check src/glassbox/cli/tui tests/unit/test_cli_tui_app.py tests/unit/test_cli_tui_widgets.py tests/unit/test_cli_tui_commands.py`, and `uv run ty check`.

### GBX-613: Add Tool Output Policy And Details Pane

- Status: `DONE`
- Depends on: `GBX-612`, `GBX-601`
- Goal: keep long-running and noisy tool output available without letting it overwhelm chat
- Deliverables:
  - output policy for inline snippets, truncation, expandable output, and details-pane routing
  - details pane showing selected tool output, recent events, status details, and dashboard handoff links where useful
  - keyboard and command-palette controls for opening, closing, and moving through details
  - tests for truncation, expansion, selection, and focus restoration
- Implementation notes:
  - default chat should remain calm even when a tool streams heavily
  - details pane is for immediate coding flow; the dashboard remains the complete evidence surface
  - make truncation explicit so users know more output exists
- Tests and validation included in task:
  - unit tests for output clipping policy
  - Textual tests for details pane behavior
  - manual review with high-volume stdout/stderr fixture
- Done when:
  - noisy tools stay inspectable without destroying the main conversation experience

Completion notes:
- Added an explicit tool output policy across inline cards and the details pane, with truncated chat snippets and clearer routing to details/dashboard for longer output.
- Expanded the details pane with selected/latest tool status, arguments, policy/risk/source, summary, exit code, output preview, artifact paths, recent activity counts, failure context, and dashboard handoff URL.
- Validated with `uv run pytest tests/unit/test_cli_tui_app.py tests/unit/test_cli_tui_widgets.py tests/unit/test_cli_tui_commands.py`, `uv run ruff check src/glassbox/cli/tui tests/unit/test_cli_tui_app.py tests/unit/test_cli_tui_widgets.py tests/unit/test_cli_tui_commands.py`, and `uv run ty check`.

### GBX-614: Add File, Artifact, And Dashboard Handoff Affordances

- Status: `TODO`
- Depends on: `GBX-612`, `GBX-613`, `GBX-573`
- Goal: connect terminal chat to the concrete files, artifacts, and browser evidence that make Glassbox trustworthy
- Deliverables:
  - compact rendering for artifact references, changed files, generated outputs, and relevant local paths when surfaced by events or snapshots
  - command-palette actions for opening dashboard, copying dashboard URL, copying artifact path, and copying session ID
  - clear copy/open feedback in the TUI
  - tests for long paths, missing artifacts, and clipboard/open failures where practical
- Implementation notes:
  - do not make the terminal run replay/eval itself unless existing commands are explicitly invoked
  - prefer handoff to the co-hosted dashboard for deep evidence inspection
  - keep local path handling safe and explicit
- Tests and validation included in task:
  - widget tests for artifact/path rendering
  - command tests for copy/open actions with failure feedback
- Done when:
  - users can move from chat to evidence without losing the session context

---

## Phase 62: Attach, Runtime State, Interruption, And Fallback

### GBX-620: Bring Full-Screen TUI To `session attach`

- Status: `TODO`
- Depends on: `GBX-590`, `GBX-570`, `GBX-571`
- Goal: make attaching to existing actionable sessions use the same modern terminal experience as new chat sessions
- Deliverables:
  - TUI attach path for daemon-owned live sessions
  - TUI attach path for persisted local actionable sessions
  - historical-only, failed, completed, cancelled, unknown, and active-turn states presented clearly
  - dashboard URL surfaced when the daemon or snapshot exposes one
  - tests for local attach, daemon attach, and non-attachable states
- Implementation notes:
  - attach should feel like re-entering the same chat, not a separate operator tool
  - do not silently blur live daemon attach and local persisted reopen; runtime ownership must remain visible
  - preserve current low-level attach semantics while modernizing presentation
- Tests and validation included in task:
  - adapted integration tests from current attach coverage
  - fake daemon client tests for live stream and snapshot behavior
  - manual attach smoke with an actionable session
- Done when:
  - users can resume an existing session in the full-screen TUI with clear live or persisted ownership semantics

### GBX-621: Implement Reconnect And Runtime Availability UX

- Status: `TODO`
- Depends on: `GBX-620`, `GBX-583`
- Goal: make stream interruptions and daemon/runtime availability understandable and recoverable inside the TUI
- Deliverables:
  - reconnecting, reconnected, unavailable, stale owner, explicit binding failure, and historical-only state presentations
  - retry policy and user-facing retry/cancel controls where appropriate
  - event stream resume from last seen sequence where supported by the client
  - tests for reconnect success, retry exhaustion, stale owner fallback, and unavailable runtime
- Implementation notes:
  - do not silently fall back from live attach to historical state without telling the user
  - keep retry behavior visible without panic-styling transient network blips
  - ensure the composer and action controls are disabled or guarded when runtime state makes mutation unsafe
- Tests and validation included in task:
  - fake SSE/client tests for reconnect paths
  - TUI state tests for stream status changes
  - existing daemon runtime tests continue to pass
- Done when:
  - users understand whether the terminal is live, reconnecting, unavailable, or only inspecting persisted state

### GBX-622: Define And Implement Interruption Semantics

- Status: `TODO`
- Depends on: `GBX-602`, `GBX-570`
- Goal: make Ctrl+C, escape, quit, and possible turn cancellation behavior predictable and safe
- Deliverables:
  - documented interruption contract for editing, modals, command palette, active tool/model turn, pending approval, pending question, reconnecting state, and app exit
  - TUI behavior for cancelling UI actions versus requesting runtime interruption where backend support exists
  - confirmation prompts for destructive or ambiguous exits
  - tests for key handling in each state
- Implementation notes:
  - if backend turn cancellation is missing, document that gap instead of faking cancellation in the UI
  - Ctrl+C should not accidentally abandon an active session without clear feedback
  - preserve session state on exit
- Tests and validation included in task:
  - keybinding tests for Ctrl+C, escape, Ctrl+D, and quit command
  - integration or manual test for exiting during an active turn
- Done when:
  - interruption and exit behavior feels intentional rather than terminal-default accidental

### GBX-623: Harden Non-TTY And Plain Fallback Behavior

- Status: `TODO`
- Depends on: `GBX-571`, `GBX-590`, `GBX-620`
- Goal: keep scripts, CI, dumb terminals, and debugging workflows from breaking when TUI becomes the default
- Deliverables:
  - final fallback behavior for non-TTY stdin/stdout and explicit `--plain` if retained
  - clear error or fallback copy when a full-screen app cannot launch
  - tests for redirected input, redirected output, CI-like environment, and explicit fallback flags
  - docs explaining when to use the fallback and which features it lacks
- Implementation notes:
  - fallback exists to protect operability, not to define the primary UX
  - avoid maintaining two divergent feature-complete interactive clients forever unless the release gate explicitly accepts that cost
  - keep one-shot commands as the preferred scriptable path
- Tests and validation included in task:
  - subprocess tests for non-TTY detection
  - current line-mode compatibility tests updated to match the chosen fallback contract
- Done when:
  - making TUI default does not make Glassbox unusable in automation or unsupported terminal contexts

### GBX-624: Validate Packaging And Dependency Footprint

- Status: `TODO`
- Depends on: `GBX-562`, `GBX-590`, `GBX-623`
- Goal: ensure the TUI dependency stack works in installed packages and normal operator environments
- Deliverables:
  - packaging validation for wheel and sdist with terminal dependencies included
  - installed-command smoke for `glassbox session chat --help`, TUI launch availability, and fallback behavior
  - release packaging doc updates for terminal dependencies and any platform-specific notes
  - known limitations for terminal emulators if any are discovered
- Implementation notes:
  - do not require Node or frontend tooling for terminal chat
  - keep the FastAPI-served dashboard assets packaged as before
  - document dependency reasons in user-centered terms
- Tests and validation included in task:
  - package build smoke
  - installed CLI smoke where current release tooling supports it
  - `uv run pytest` focused on CLI launch and fallback behavior
- Done when:
  - the modern terminal client can ship as part of the normal Python package

---

## Phase 63: v5 Terminal Release Gate

### GBX-630: Add Scenario-Based Terminal Workflow Coverage

- Status: `TODO`
- Depends on: `GBX-610`, `GBX-611`, `GBX-612`, `GBX-620`, `GBX-621`, `GBX-623`
- Goal: protect the new terminal UX with scenario-based tests that match real coding-agent workflows
- Deliverables:
  - TUI scenarios for startup, initial prompt, multi-turn chat, streaming assistant output, tool activity, pending approval, pending question, prompt conflict, failed turn, dashboard handoff, daemon attach, reconnect, historical-only state, and non-TTY fallback
  - fake client and fixture event streams shared across terminal reducer and widget tests
  - subprocess or pty smoke coverage for actual command launch where practical
  - documented manual UX review checklist for representative terminal sizes and workflows
- Implementation notes:
  - focus tests on user-observable outcomes and stable state transitions, not fragile styling internals
  - use deterministic fake providers and event streams rather than live provider calls
  - keep screenshots/recordings optional manual evidence unless a stable artifact path is defined
- Tests and validation included in task:
  - focused TUI test suite
  - relevant integration tests for local and daemon clients
  - `uv run ruff check .`
  - `uv run ty check`
- Done when:
  - the terminal client has enough automated workflow coverage to make future UI changes safer

### GBX-631: Update Operator Docs For The v5 Chat Experience

- Status: `TODO`
- Depends on: `GBX-623`, `GBX-630`
- Goal: teach users the new terminal experience without making them inspect source code or old task docs
- Deliverables:
  - updates to [getting-started.md](./getting-started.md) showing the full-screen `session chat` entry point and dashboard partnership
  - updates to [interactive-workflows.md](./interactive-workflows.md) covering TUI layout, keyboard controls, composer behavior, approvals, questions, attach, fallback, and troubleshooting
  - updates to [dashboard.md](./dashboard.md) explaining how the co-hosted dashboard complements terminal chat
  - docs hub updates for v5 terminal modernization and release gate docs if added
  - migration note for users familiar with old slash-command line mode
- Implementation notes:
  - documentation should describe the product operators actually see, not implementation internals
  - keep one-shot command docs intact for scripting and recovery workflows
  - make fallback limitations explicit
- Tests and validation included in task:
  - docs review against implemented command help and keyboard behavior
  - manual verification of documented example flows
- Done when:
  - a new user can discover and use the modern terminal chat workflow from docs alone

### GBX-632: Define And Enforce The v5 Terminal UX Release Gate

- Status: `TODO`
- Depends on: `GBX-630`, `GBX-631`, `GBX-624`
- Goal: decide when the full-screen terminal client is good enough to become the default `glassbox session chat` experience
- Deliverables:
  - v5 terminal UX release checklist covering full-screen launch, co-hosted dashboard, transcript, streaming, composer, command palette, approvals, questions, tool activity, details pane, attach, reconnect, interruption, fallback, packaging, and docs
  - automated coverage map for each release-gate requirement
  - manual validation checklist using deterministic and real-provider sessions where available
  - explicit known-gaps list for any non-blocking terminal UX limitations that remain
  - final decision on whether plain line mode remains supported, remains hidden fallback, or is removed
- Implementation notes:
  - do not treat v5 as complete because old interactive CLI tests pass; this gate is about modern coding-agent quality
  - the terminal should feel like the primary way to chat with the agent, not a companion to the dashboard
  - the co-hosted dashboard must remain validated as the paired operator console
- Tests and validation included in task:
  - full Python validation
  - focused TUI workflow suite
  - package/install smoke
  - dashboard co-hosting smoke
  - manual terminal review at representative sizes
- Done when:
  - the project has objective evidence that `glassbox session chat` is materially better than the old line-mode baseline and safe to treat as the new coding-agent terminal standard

---

## Recommended Build Order For The First v5 Terminal Recovery Slice

If an agent wants the fastest path to a demonstrable improvement, the recommended order is:

1. `GBX-560` and `GBX-561`
2. `GBX-562` and `GBX-563`
3. `GBX-570` through `GBX-573`
4. `GBX-580` and `GBX-581`
5. `GBX-590` through `GBX-593`
6. `GBX-600` and `GBX-601`
7. `GBX-610` and `GBX-611`
8. `GBX-620` and `GBX-621`
9. selected coverage from `GBX-630`

That yields:

- a documented terminal UX baseline and interaction contract
- a framework-backed TUI foundation
- a reusable session client boundary for local and daemon sessions
- a pure conversation state model
- a full-screen chat shell with co-hosted dashboard context
- streaming assistant output and a real transcript
- a multiline composer and command palette
- first-class approval and question workflows
- attach and reconnect behavior inside the modern terminal app

## Explicit Non-Goals For v5 Terminal Execution

Do not spend time on these unless a later task graph explicitly adds them:

- replacing the v4 web dashboard or moving operator-console queues into the default terminal chat surface
- requiring a browser to be open before terminal chat can function
- requiring Node, Next.js, or frontend tooling for terminal chat in production
- moving canonical session state into terminal-only storage
- changing approval, prompt, answer, fork, SSE, replay, or eval semantics for terminal convenience
- deleting non-interactive commands in the name of TUI simplicity
- implementing remote multi-user collaboration, hosted tenancy, or cloud assumptions
- building browser-side or terminal-side replay/eval execution outside existing replay/eval commands
- adding a broad terminal analytics dashboard before the core chat workflow is excellent
- hand-rolling a terminal framework if Textual or another proven library can provide the needed user experience

## Success Criteria For The v5 Terminal Redesign

The v5 redesign is on track when all of the following are true:

- `glassbox session chat` opens a full-screen, chat-first terminal experience by default in supported TTYs
- the co-hosted dashboard remains available by default and is easy to open or copy from the terminal
- the transcript reads as a coding-agent conversation, not as a flat event log
- assistant responses stream visibly and finalize cleanly
- users can compose multiline prompts comfortably, preserve drafts, and recover from submission failures
- pending approvals and questions are first-class action surfaces with clear keyboard paths and feedback
- tool activity is understandable inline, with noisy output available through expansion or details rather than flooding chat
- `session attach` reuses the same terminal experience for local and daemon-owned actionable sessions
- reconnect, unavailable runtime, historical-only, active turn, and failed states are explicit and recoverable where backend semantics permit recovery
- non-TTY and fallback behavior is deliberate and documented
- automated terminal workflow coverage and manual UX review protect the improved experience
- the old line-mode baseline is no longer the standard for interactive quality
