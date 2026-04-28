# v5 Terminal UX Release Gate

This gate decides whether the full-screen terminal client is ready to be treated as the default `glassbox session chat` experience. The bar is higher than old interactive CLI compatibility: the terminal must feel like the primary coding-agent conversation surface, with the dashboard as the paired operator console.

## Release Command

Run the automated gate from the repository root:

```sh
uv run python scripts/validate_v5_terminal_release_gate.py
```

The command runs Python format, lint, typecheck, the focused terminal workflow suite, the full Python test suite, deterministic eval smoke, wheel and sdist build, and installed-wheel terminal command smoke.

## Release Checklist

- Full-screen launch: implicit `session chat` and `session attach` choose the TUI in supported interactive terminals, while explicit `--tui` fails clearly when launch cannot be honored.
- Co-hosted dashboard: local `session chat` starts a session-specific dashboard by default, records the dashboard URL, and keeps chat usable when default dashboard startup is unavailable.
- Transcript: prompts, assistant messages, streaming deltas, turn grouping, failures, imported history, and historical-only sessions render as conversation state rather than raw event logs.
- Streaming: live assistant output updates incrementally, finalizes cleanly, and preserves partial output on failure or interruption.
- Composer: multiline prompts, draft preservation, prompt history, blocked-state placeholders, and recoverable submission feedback work without losing local input.
- Command palette: status, dashboard, copy, details, approval, question, interrupt, and quit commands expose contextual enabled or disabled reasons.
- Approvals: pending approvals surface in the action strip with tool and policy context, support approve and deny shortcuts, and preserve explicit decision semantics.
- Questions: pending `ask_user` questions surface in the action strip, use the composer for answer drafts, and submit without requiring users to copy question IDs.
- Tool activity: requested, running, awaiting approval, completed, failed, output, artifact, and expanded details states stay readable in the transcript and details pane.
- Details pane: selected tool context, policy, output clipping, artifacts, dashboard URL, and recent session counts are inspectable without crowding the main transcript.
- Attach: persisted local sessions, daemon-owned live sessions, stale daemon metadata, unavailable runtime owners, and completed historical sessions resolve to honest TUI states.
- Reconnect: stream retry, reconnected, unavailable, and blocked-mutation states are visible and covered by deterministic fake-client tests.
- Interruption and exit: Escape, Ctrl+C, and Ctrl+Escape follow the documented non-destructive interruption contract.
- Fallback: implicit unsupported terminal launches fall back to plain mode, explicit `--plain` remains available, and explicit `--tui` does not silently degrade.
- Packaging: `textual>=6,<7`, the `glassbox` console script, wheel and sdist dashboard assets, and installed command smoke are validated.
- Docs: getting started, interactive workflows, dashboard, release packaging, and this gate describe the modern terminal workflow without requiring users to inspect source code.

## Automated Coverage Map

| Requirement | Primary automated evidence |
| --- | --- |
| Full-screen launch and fallback | `tests/unit/test_cli_interactive_launch.py`, `tests/integration/test_cli_tui_launch_smoke.py`, `tests/integration/test_cli_interactive_commands.py` |
| Co-hosted dashboard partnership | `tests/integration/test_cli_interactive_commands.py`, `tests/integration/test_web_chat_dashboard_live.py` |
| Transcript, streaming, tools, failures, historical state | `tests/unit/test_cli_tui_conversation.py`, `tests/unit/test_cli_tui_widgets.py`, `tests/unit/test_cli_tui_workflows.py` |
| Composer, focus, command palette, details pane | `tests/unit/test_cli_tui_app.py`, `tests/unit/test_cli_tui_widgets.py`, `tests/unit/test_cli_tui_commands.py` |
| Approvals and questions | `tests/unit/test_cli_tui_app.py`, `tests/unit/test_cli_tui_conversation.py`, `tests/integration/test_cli_interactive_commands.py` |
| Attach, daemon attach, reconnect, runtime unavailable | `tests/unit/test_cli_tui_app.py`, `tests/integration/test_cli_interactive_commands.py`, `tests/integration/test_daemon_runtime.py` |
| Interruption and exit | `tests/unit/test_cli_tui_app.py`, `docs/terminal-interaction-model-v5.md` |
| Packaging and installed command smoke | `tests/unit/test_packaging_metadata.py`, `scripts/validate_v5_terminal_release_gate.py`, `docs/release-packaging.md` |
| Operator documentation | `docs/getting-started.md`, `docs/interactive-workflows.md`, `docs/dashboard.md`, `docs/README.md` |

## Focused Terminal Workflow Suite

The release command runs this focused suite before the full repository tests:

```sh
uv run pytest \
  tests/unit/test_tui_framework_smoke.py \
  tests/unit/test_cli_tui_conversation.py \
  tests/unit/test_cli_tui_widgets.py \
  tests/unit/test_cli_tui_app.py \
  tests/unit/test_cli_tui_commands.py \
  tests/unit/test_cli_tui_workflows.py \
  tests/unit/test_packaging_metadata.py \
  tests/integration/test_cli_tui_launch_smoke.py \
  tests/integration/test_cli_interactive_commands.py \
  tests/integration/test_daemon_runtime.py
```

This suite protects the terminal UX without making the release gate depend on fragile cell-perfect visual assertions.

## Manual Validation

Run manual review after the automated gate passes. Use deterministic sessions first, then a real-provider session when credentials are available.

Terminal sizes:

- 120 x 36 for a comfortable desktop coding session
- 100 x 30 for the default automated Textual smoke size
- 80 x 24 for the smallest common full-screen terminal
- 60 x 20 for narrow split-pane truncation and wrapping checks

Deterministic workflows:

- launch `session chat` with no initial prompt
- launch `session chat` with an initial prompt
- send a multiline prompt with pasted code or a stack trace
- watch assistant streaming and finalization
- inspect compact and expanded tool activity
- answer a pending question without copying a question ID
- approve and deny pending approvals without copying an approval ID
- open the command palette, filter commands, and verify disabled reasons
- open and copy the dashboard URL after scrollback moves on
- attach to a persisted local actionable session
- attach to a completed session and confirm historical-only mutation blocking
- attach to a daemon-owned live session
- observe reconnecting and unavailable stream states when a controlled fake client or daemon interruption can reproduce them
- quit while idle
- attempt quit or interruption during an active turn, approval, question, and reconnecting state
- run redirected stdin/stdout or `--plain` fallback and confirm line mode is usable

Real-provider workflows when available:

- run a coding-agent prompt that reads files and summarizes findings
- run a prompt that triggers a policy-gated command approval
- run a prompt that triggers an `ask_user` question
- inspect the same live session in the co-hosted dashboard while the terminal remains the primary chat surface
- verify that terminal and dashboard states converge after the turn completes

## Known Non-Blocking Gaps

- Backend cancellation of an in-flight model/tool turn is not implemented; Ctrl+C reports this honestly and does not pretend to cancel the runtime.
- Terminal visual review is manual. Automated tests cover semantic regions and workflow outcomes, not pixel-perfect layout.
- The focused scenario suite uses deterministic fake clients and seeded events; real provider behavior still needs manual review for release signoff.
- Full screen support depends on terminal capabilities. Unsupported terminals, redirected streams, CI-like environments, and `TERM=dumb` use plain fallback unless `--tui` was explicitly requested.
- Screen-reader and terminal accessibility review remains a manual release activity before making public accessibility claims.

## Plain Line-Mode Decision

Plain line mode remains supported as an explicit compatibility, debugging, scripting-adjacent, and fallback path. It is not the primary v5 product surface.

The retained behavior is:

- implicit unsupported launches fall back to plain mode
- `--plain` deliberately selects plain mode
- `--tui` is strict and fails when the TUI cannot launch
- one-shot commands remain the preferred automation surface for scripts and recovery workflows

Do not remove plain line mode until the project has a separate migration task that replaces unsupported-terminal and redirected-stream workflows with an equally reliable operator path.
