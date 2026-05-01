# v11 Accessibility Pairing Review

For the docs hub and operator guides, start at [README.md](./README.md). This
review records the `GBX-1132` named terminal and dashboard accessibility
pairings for the v11 confidence-and-adoption track.

## Environment

- OS: macOS 15.7.2, build 24G325
- Shell: zsh 5.9, arm64-apple-darwin24.0
- Browser automation: Playwright 1.59.1, Chromium project
- Workspace: local routed dashboard fixtures and local terminal test harnesses

## Named Pairings

| Pairing | Status | Evidence |
| --- | --- | --- |
| Terminal keyboard pairing on macOS zsh, Textual TUI test harness, release-size workflow family | Passed | `uv run pytest tests/unit/test_cli_tui_app.py tests/unit/test_cli_tui_workflows.py tests/unit/test_cli_tui_commands.py tests/integration/test_cli_tui_launch_smoke.py -q` returned `54 passed`. |
| Terminal plain-mode pairing on macOS zsh, explicit line-mode compatibility path | Passed | The same launch smoke includes non-TTY/plain fallback coverage, and `uv run glassbox session chat --help` documents `--plain` and `--tui` as distinct operator choices. |
| Dashboard keyboard pairing on macOS Chromium through Playwright, desktop and mobile workflow family | Passed | `pnpm --dir frontend exec playwright test e2e/operator-workflows.spec.ts -g "keyboard\|mobile operator can drill" --reporter=list` returned `5 passed`. |
| Dashboard long-session evidence keyboard-adjacent route and cue pairing on macOS Chromium through Playwright | Passed | `GBX-1131` retained screenshots and JSON under `.glassbox/releases/gbx-1131-live-cockpit/` for long-session, stale verification, reconnect, queue navigation, and historical snapshot scenarios. |
| macOS VoiceOver with terminal or Chromium dashboard | Not executed | This coding session has no safe interactive screen-reader control channel or retained reviewer transcript. No v11 screen-reader support claim is made. |

## Review Scope

Terminal workflows reviewed by automated pairing evidence:

- TUI mount, release-size behavior, command routing, details pane, palette and
  workflow commands
- primary keyboard paths for prompt submit, approval/denial, ask-user answer,
  cancellation, quit, attach/launch smoke, and fallback behavior
- explicit plain-mode discovery through `glassbox session chat --help`

Dashboard workflows reviewed by automated pairing evidence:

- primary keyboard workflow for queue navigation, selected-session drill-in,
  transcript tab navigation, answer submission, approval, and fork
- mobile selected-session drill-in and return to queues
- task controls, budget review, memory inspector, repository index inspector,
  and branch-search candidate selection from the keyboard
- v11 live cockpit evidence routes for long-session recovery cues, stale
  verification evidence, degraded stream/reconnect state, queue navigation,
  and historical snapshots

## Validation Commands

Terminal pairing:

```bash
uv run pytest \
  tests/unit/test_cli_tui_app.py \
  tests/unit/test_cli_tui_workflows.py \
  tests/unit/test_cli_tui_commands.py \
  tests/integration/test_cli_tui_launch_smoke.py \
  -q
```

Result: `54 passed`.

Plain-mode command discovery:

```bash
uv run glassbox session chat --help
uv run glassbox command guide --help
```

Result: help output names `--plain`, `--tui`, and `--json` command-guide
fallbacks.

Dashboard keyboard pairing:

```bash
pnpm --dir frontend exec playwright test e2e/operator-workflows.spec.ts \
  -g "keyboard|mobile operator can drill" \
  --reporter=list
```

Result: `5 passed`.

Live cockpit evidence pairing inherited from `GBX-1131`:

```bash
GBX_V11_LIVE_COCKPIT_EVIDENCE_DIR=.glassbox/releases/gbx-1131-live-cockpit \
  pnpm --dir frontend exec playwright test e2e/v11-live-cockpit-evidence.spec.ts --reporter=list
```

Result: `4 passed`.

## Findings And Fixes

- No blocking terminal keyboard or plain-mode defect was found in the focused
  pairing tests.
- No blocking dashboard keyboard defect was found in the focused Chromium
  pairing tests.
- `GBX-1131` fixed duplicate event-evidence React keys discovered during the
  live cockpit evidence run. That fix keeps repeated retained and live SSE
  events renderable without relying on unstable React identity behavior.
- No screen-reader defect was fixed because no screen-reader pairing was
  executed.

## Supported Claims

- The reviewed terminal workflows are keyboard-operable in the named automated
  TUI harness and plain-mode discovery remains explicit in command help.
- The reviewed dashboard workflows are keyboard-operable in Chromium through
  Playwright for the named desktop and mobile routes.
- The reviewed dashboard status, stream, recovery, verification, provider, and
  historical cues expose text labels and accessible names in the tested paths;
  they are not color-only claims.
- v11 accessibility confidence is stronger than inherited v7/v8 automated
  evidence for the named workflows because this pass reran v11-specific
  long-session and reconnect cockpit evidence.

## Non-Claims And Follow-Ups

- This is not formal WCAG, VPAT, or screen-reader certification.
- This does not prove macOS VoiceOver, Windows Narrator, NVDA, Orca, Safari,
  Firefox, browser zoom, high-contrast mode, or every terminal emulator.
- This does not prove live provider behavior or hosted dashboard operation.
- A future reviewer should run and retain at least one real screen-reader
  pairing before expanding public accessibility claims beyond keyboard,
  semantics, and automated role/name evidence.

## Related Documents

- [live-cockpit-evidence-v11.md](./live-cockpit-evidence-v11.md): v11 live
  cockpit evidence protocol and retained `GBX-1131` browser evidence summary
- [terminal-accessibility-review-v7.md](./terminal-accessibility-review-v7.md):
  inherited terminal pairing evidence and non-claims
- [dashboard-accessibility-review-v7.md](./dashboard-accessibility-review-v7.md):
  inherited dashboard keyboard and semantic pairing evidence
- [dashboard-accessibility-review-v8.md](./dashboard-accessibility-review-v8.md):
  inherited autonomy-console accessibility evidence
