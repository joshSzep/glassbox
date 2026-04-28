# v6 Terminal Accessibility And Visual Review

This review records the `GBX-691` terminal evidence for the v6 release-candidate
track. It complements the v5 terminal release gate and uses the v6 manual QA
archive convention in [manual-qa-evidence-v6.md](./manual-qa-evidence-v6.md).

## Review Scope

Reviewed terminal sizes:

| Size | Evidence |
| --- | --- |
| `120x36` | `test_tui_app_mounts_across_release_review_sizes` |
| `100x30` | `test_tui_app_mounts_across_release_review_sizes`; broader Textual workflow suite default |
| `80x24` | `test_tui_app_mounts_across_release_review_sizes` |
| `60x20` | `test_tui_app_mounts_across_release_review_sizes` |

Reviewed keyboard and workflow areas:

- prompt submit and multiline editing: Enter sends, Ctrl+Enter inserts newline
- command palette: Ctrl+P opens, filters, executes, and restores focus
- details pane: Ctrl+E toggles and preserves keyboard recovery
- approvals: Alt+A approves and Alt+X denies through explicit actions
- questions: Ctrl+R submits an answer from the action state
- cancellation/interruption: Ctrl+C records the interruption contract; Escape
  cancels transient UI; Ctrl+Esc quits
- attach and reconnect: local attach, daemon attach, stream reconnect, retry
  exhaustion, stale state, and unavailable runtime paths are covered by focused
  tests
- plain fallback: launch smoke and interactive command tests cover `--plain`,
  non-TTY fallback, and explicit TUI failure behavior

## Validation Run

Focused terminal suite:

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

Result: `138 passed` on Python 3.14.2 before adding the explicit release-size
test; the task commit reran the focused app test after adding it.

## Accessibility Notes

Claims supported by this review:

- The terminal app exposes keyboard routes for the primary operator actions
  documented in the v5 terminal interaction model.
- The TUI mounts at the v6 release-review terminal sizes without missing the
  header, conversation pane, or composer.
- Question and approval workflows are reachable without copying internal IDs in
  the primary TUI path.
- Fallback/plain mode remains available for unsupported terminals and
  redirected-stream contexts.

Non-claims:

- This is not a formal screen-reader certification.
- This does not assert cell-perfect rendering or color-contrast certification.
- This does not prove every terminal emulator behaves identically.
- Live provider behavior remains advisory unless retained with separate
  provider-canary evidence.

## Follow-Up Issues

No blocking terminal UX issue was found in this pass. Future release candidates
should attach local screenshots or screen recordings under the v6 evidence
directory when a reviewer sees a visual issue that is hard to describe in text.
