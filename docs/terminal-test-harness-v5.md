# v5 Terminal Test Harness And Review Artifacts

For the v5 task graph, see [tasks-v5.md](./tasks-v5.md). For the terminal interaction contract, see [terminal-interaction-model-v5.md](./terminal-interaction-model-v5.md). For the framework decision, see [terminal-framework-decision-v5.md](./terminal-framework-decision-v5.md).

This document defines how Glassbox should validate the full-screen terminal client as it replaces the current line-mode `session chat` loop.

## Testing Goals

The v5 terminal test harness should protect user-observable coding-agent workflows without freezing incidental terminal styling.

The harness should prove:

- the app launches and exits cleanly in test environments
- the header, transcript, action strip, composer, footer, command palette, and details pane render from deterministic state
- keybindings and focus rules follow the interaction model
- local and daemon session clients dispatch the right intents
- live event streams update the conversation model predictably
- approvals and questions remain explicit and recoverable
- non-TTY and fallback behavior is deliberate
- terminal review artifacts can be generated locally without noisy binary churn

## Test Layers

### Pure State Tests

Pure state tests should cover reducers, view models, action priority, transcript grouping, header state, output clipping, and fallback decisions without importing Textual.

Use these for:

- event-to-conversation state
- assistant delta and completion ordering
- tool lifecycle grouping
- approval and question action priority
- reconnect and runtime status derivation
- terminal-width truncation policies

These tests should be fast, deterministic, and broad.

### Fake Client Tests

Fake client tests should exercise the session-client contract without starting a real runtime or daemon.

Use these for:

- prompt submission success and failure
- answer submission success and failure
- approval approve and deny success and conflict
- stream reconnect outcomes
- historical-only and unavailable-runtime errors
- stale response handling

Fake clients should emit typed events and normalized client errors rather than raw strings.

### Textual Widget And App Tests

Textual tests should use Textual's test driver to validate visible state, focus, keybindings, and action dispatch.

Use these for:

- app launch and clean exit
- header/footer rendering
- transcript rendering for representative states
- composer typing, paste-like input, send, disabled states, and draft preservation
- command palette opening, filtering, disabled reasons, and execution
- action strip focus and approval/question workflows
- details pane open, close, and focus restoration

The initial framework smoke test is [test_tui_framework_smoke.py](../tests/unit/test_tui_framework_smoke.py). It proves Textual imports, runs under the test driver, renders a widget, and exits cleanly in a CI-like non-interactive context.

### CLI And pty Smoke Tests

Subprocess or pty-style tests should be narrower than widget tests. Their job is to prove the actual command launches through the real parser and runtime ownership checks.

Use these for:

- `glassbox session chat --help`
- TUI launch selection in supported TTY contexts
- plain or non-TTY fallback behavior
- clean shutdown when the app exits
- daemon attach launch path with fake or controlled runtime owner metadata

Avoid making pty tests assert detailed layout. They should check stable invariants such as process exit, no traceback, visible startup state where capture is practical, and persisted session side effects.

### Existing Integration Tests

The current interactive tests should remain useful during migration, but their role changes.

- While plain mode exists, keep line-mode routing tests for fallback behavior.
- As TUI behavior becomes default, add equivalent TUI-focused tests for the same semantics.
- Keep existing one-shot command tests because non-interactive commands remain scriptable primitives.
- Keep daemon runtime and web session tests because the TUI must use the same canonical surfaces.

## Required Scenario Matrix

Each major TUI milestone should use a focused subset of this matrix. The v5 release gate should cover the full matrix.

| Scenario | Pure state | Fake client | Textual | CLI/pty | Manual |
| --- | --- | --- | --- | --- | --- |
| new chat startup | yes | yes | yes | yes | yes |
| initial prompt | yes | yes | yes | yes | yes |
| multi-turn chat | yes | yes | yes | optional | yes |
| assistant streaming | yes | yes | yes | optional | yes |
| tool request/start/complete | yes | yes | yes | optional | yes |
| high-volume tool output | yes | optional | yes | no | yes |
| tool failure | yes | yes | yes | optional | yes |
| pending question | yes | yes | yes | optional | yes |
| pending approval | yes | yes | yes | optional | yes |
| approval conflict | yes | yes | yes | no | optional |
| prompt conflict | yes | yes | yes | no | optional |
| dashboard available | yes | yes | yes | yes | yes |
| dashboard unavailable | yes | yes | yes | yes | yes |
| daemon attach | yes | yes | yes | yes | yes |
| reconnecting stream | yes | yes | yes | optional | yes |
| runtime unavailable | yes | yes | yes | optional | yes |
| historical-only state | yes | yes | yes | optional | yes |
| non-TTY fallback | yes | no | no | yes | optional |
| narrow terminal width | yes | no | yes | no | yes |

## Stable Test Invariants

Prefer assertions against these stable outcomes:

- app starts without traceback
- primary regions exist
- composer is visible or disabled with a reason
- current blocking action is visible when present
- prompt or answer drafts are preserved after recoverable failures
- approval and denial dispatch distinct intents
- dashboard URL is available through header or command palette when known
- focus returns after modal or command palette close
- jump-latest resumes latest transcript view
- long paths and output do not crash rendering
- non-TTY command path does not launch an unusable full-screen app

Avoid assertions against these unstable details unless a task deliberately freezes them:

- exact border characters
- exact color values
- pixel or cell-perfect layout
- incidental whitespace inside wrapped markdown
- ordering of low-priority diagnostic details
- framework-generated widget IDs

## Manual Review Checklist

Manual review should be short, repeatable, and tied to representative terminal sizes.

Run review at least at:

- 80x24
- 100x30
- a wide split-pane terminal
- a narrow terminal around 70 columns if supported

Review these workflows:

- launch `session chat` with no prompt
- launch `session chat` with an initial prompt
- type and send a multiline prompt
- paste a code block or stack trace into the composer
- watch assistant streaming and finalization
- inspect compact and expanded tool output
- answer a pending question
- approve and deny pending approvals
- open the command palette and run dashboard copy/open commands
- scroll away from latest activity and jump back
- toggle details pane and restore focus
- attach to a daemon-owned session
- observe reconnecting and unavailable runtime states
- exit while idle
- attempt exit or interruption while a turn is active
- run the documented non-TTY or plain fallback path

## Review Artifacts And Retention

Terminal review artifacts are audit evidence, not golden visual baselines by default.

Recommended artifact types:

- plain text transcripts for fallback mode and subprocess smoke tests
- Textual test snapshots only for stable semantic regions if the framework support proves useful
- short local screen recordings for manual review when a visual or interaction issue is hard to describe
- local terminal screenshots for release-gate review when needed

Retention rules:

- do not commit large binary recordings or screenshots by default
- keep generated review artifacts under ignored test-results paths if a task creates them
- include text summaries or manifest files when they help reviewers understand what was captured
- commit deterministic text fixtures and tests when they protect behavior

## Recommended File Targets

Future terminal test implementation should prefer these targets:

```text
tests/unit/test_tui_framework_smoke.py
tests/unit/test_tui_state.py
tests/unit/test_tui_actions.py
tests/unit/test_tui_output_policy.py
tests/integration/test_cli_tui_launch.py
tests/integration/test_cli_tui_workflows.py
tests/integration/test_cli_tui_fallback.py
tests/integration/terminal_test_support.py
```

These names are guidance, not a hard requirement. Use existing test organization if implementation reveals a better split.

## Validation Commands

Use focused validation during implementation:

```bash
uv run pytest tests/unit/test_tui_framework_smoke.py
uv run pytest tests/unit/test_tui_state.py
uv run pytest tests/integration/test_cli_tui_launch.py
uv run pytest tests/integration/test_cli_interactive_commands.py
uv run ruff check src/glassbox/cli tests/unit tests/integration
uv run ty check
```

The v5 release gate should run full Python validation and the focused TUI suite.
