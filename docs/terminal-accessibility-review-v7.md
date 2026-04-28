# v7 Terminal Accessibility Pairing Review

This review records the `GBX-780` terminal accessibility evidence for the v7 release-candidate track. It builds on [terminal-accessibility-review-v6.md](./terminal-accessibility-review-v6.md) and uses the v7 manual evidence shape in [manual-qa-evidence-v7.md](./manual-qa-evidence-v7.md).

## Named Pairings

| Pairing                                                                                                    | Status                                                     | Evidence                                                                                                        |
| ---------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| VS Code integrated terminal on macOS, zsh, keyboard-only, `120x36` and `100x30` terminal-size family       | Reviewed through automated TUI mount and workflow coverage | `tests/unit/test_cli_tui_app.py`, `tests/unit/test_cli_tui_workflows.py`, `tests/unit/test_cli_tui_commands.py` |
| VS Code integrated terminal on macOS, zsh, keyboard-only, compact `80x24` and `60x20` terminal-size family | Reviewed through automated release-size mount coverage     | `test_tui_app_mounts_across_release_review_sizes`                                                               |
| macOS VoiceOver with VS Code integrated terminal                                                           | Not executed in this environment                           | Non-claim; requires manual reviewer evidence before any screen-reader support claim                             |

## Review Scope

Terminal areas retained from v6 and considered in scope for v7 claims:

- prompt submit and multiline editing
- command palette filtering and focus recovery
- details pane toggle and keyboard recovery
- approvals and denials
- ask-user answers
- cancellation and quit paths
- daemon attach, reconnect, stale owner, and unavailable runtime paths
- plain fallback and non-TTY fallback behavior

The v7 review narrows claims to keyboard-operable workflows and named terminal-size families. It does not add a broader screen-reader claim because the VoiceOver terminal pairing was not executed.

## Validation Commands

Use this focused terminal suite for the v7 pairing review:

```bash
uv run pytest \
  tests/unit/test_tui_framework_smoke.py \
  tests/unit/test_cli_tui_conversation.py \
  tests/unit/test_cli_tui_widgets.py \
  tests/unit/test_cli_tui_app.py \
  tests/unit/test_cli_tui_commands.py \
  tests/unit/test_cli_tui_workflows.py \
  tests/integration/test_cli_tui_launch_smoke.py \
  tests/integration/test_cli_interactive_commands.py \
  tests/integration/test_daemon_runtime.py
```

For the `GBX-780` task commit, the focused release-size and workflow smoke was rerun with:

```bash
uv run pytest tests/unit/test_cli_tui_app.py tests/unit/test_cli_tui_workflows.py
```

## Supported Claims

- The Textual TUI has keyboard routes for the primary operator workflows covered by the focused unit and integration suites.
- The TUI mounts across the named v7 terminal-size families without dropping the header, transcript/conversation region, or composer contract.
- Plain and non-TTY fallback remains the supported accessibility fallback when a full-screen terminal UI is unsuitable.

## Non-Claims

- This is not formal WCAG, VPAT, or screen-reader certification.
- This does not prove macOS VoiceOver, Windows Narrator, or Linux Orca behavior in terminal emulators.
- This does not prove every terminal emulator renders colors, focus, or cell wrapping identically.
- Live-provider behavior remains advisory unless retained through separate provider-canary evidence.

## Blocking Issues And Follow-Ups

No blocking terminal accessibility issue is recorded for this `GBX-780` pass. Before making stronger public claims, run and retain a real screen-reader pairing review under the v7 release evidence directory.
