# Interactive Workflows

Glassbox has two main terminal operator modes:

- `glassbox session chat` starts a new full-screen coding-agent conversation
- `glassbox session attach SESSION_ID` reopens an existing session in the terminal

Use the lower-level commands when you need scripting, recovery, or precise control of a session state.

## Default Entry Point: Full-Screen `session chat`

Start an interactive session:

```bash
uv run glassbox session chat --cwd .
```

In an interactive terminal, `session chat` launches the full-screen TUI by default. The app is organized around a stable header, conversation transcript, action strip, multiline composer, footer, command palette, and optional details pane.

`session chat` and `session run` read optional repository defaults from `glassbox.profile.json` at the selected `--cwd`. Use `--model-name` or `--approval-mode` when one invocation needs to override those defaults.

Or start with an initial prompt:

```bash
uv run glassbox session chat "Inspect the repository" --cwd .
```

Inside the full-screen session:

- the transcript is the main surface for prompts, streaming assistant output, tool activity, failures, and compact evidence
- the composer accepts multiline prompts; `Enter` adds a line and `Ctrl+Enter` sends
- the action strip appears for pending approvals, pending `ask_user` questions, active turns, historical sessions, and runtime recovery states
- approvals use `Alt+A` to approve and `Alt+X` to deny when the pending action is current
- pending questions use the composer for the answer draft and `Ctrl+R` to submit
- the command palette opens with `Ctrl+P` and exposes status, dashboard, copy, details, approval, answer, interrupt, and quit actions with contextual disabled reasons
- `Ctrl+L` jumps to the latest activity, `Ctrl+E` toggles details, `Ctrl+D` opens the dashboard, `Alt+D` copies the dashboard URL, and `Ctrl+G` returns focus to the composer
- `Escape` closes transient UI first, including the command palette or details pane, without mutating runtime state
- `Ctrl+C` follows the interruption contract: it closes transient UI first and never silently abandons a live turn, approval, or question
- `Ctrl+Escape` quits immediately from idle or inspect-only states and asks for a second press when a live turn, approval, question, or reconnecting state could still be running

Composer drafts are local UI state until submission succeeds. Recoverable failures preserve the draft so you can retry after reading the feedback.

### Plain Line-Mode Compatibility

The old slash-command line loop is no longer the primary chat experience, but it remains available for debugging, redirected streams, CI, and unsupported terminals.

```bash
uv run glassbox session chat --plain --cwd .
```

Implicit `session chat` falls back to plain mode when stdin/stdout are not both interactive, the terminal is `dumb`, CI-like environment variables are present, or the TUI dependency is unavailable. Explicit `--tui` is strict: it fails with a clear error instead of silently falling back.

In plain mode, freeform text sends prompts or answers pending questions, `/approve` and `/deny` resolve the current approval, and `/status`, `/help`, and `/exit` remain available.

## Reopen A Persisted Session: `attach`

Use `attach` when you already have a session ID and want to reopen the session in the terminal:

```bash
uv run glassbox session attach SESSION_ID --cwd .
```

In supported interactive terminals, `attach` uses the same full-screen TUI and layout as `session chat`. It has two runtime paths:

- live daemon attach: if a healthy workspace daemon owns the runtime, `attach`
  reconnects the terminal to that live owner over the daemon's HTTP plus SSE
  surfaces
- persisted local reopen: if no daemon owns the workspace, `attach` reopens the
  persisted actionable session from local state

In live mode, `attach` is for sessions that are actionable from the operator side:

- idle running sessions waiting for the next prompt
- sessions awaiting `ask_user` input
- sessions awaiting approval resolution

Completed, failed, cancelled, imported, or otherwise historical sessions open as inspect-only when launched through the TUI. The transcript, details pane, and dashboard handoffs remain available, but mutation controls are disabled with the reason visible.

`attach` does not automatically start a new dashboard. If a healthy daemon owns the workspace, the TUI surfaces the daemon-owned dashboard URL. If no daemon owns the workspace and you want browser observation after re-entering a persisted session, run `glassbox dashboard serve` separately and use the session index in the dashboard.

## State-Driven Commands

Use the command that matches the current actionable state:

- `glassbox session message SESSION_ID PROMPT` sends a fresh user prompt when the session is idle and running
- `glassbox session answer SESSION_ID QUESTION_ID ANSWER` answers a pending `ask_user` question when the session is awaiting user input
- `glassbox session approve SESSION_ID APPROVAL_ID` or `glassbox session deny SESSION_ID APPROVAL_ID` resolves a pending approval when the session is awaiting approval
- `glassbox session resume SESSION_ID` reloads a persisted session after restart without sending a new prompt
- `glassbox session status SESSION_ID` prints the current state and the next valid operator action
- `glassbox session export SESSION_ID OUTPUT` writes a portable handoff package for review without copying the workspace database
- `glassbox session import PACKAGE` imports a handoff package into a new local historical session for inspection

Example:

```bash
uv run glassbox session status SESSION_ID --cwd .
uv run glassbox session message SESSION_ID "Continue with the next step" --cwd .
```

Answer a pending `ask_user` question:

```bash
uv run glassbox session answer SESSION_ID QUESTION_ID "blue" --cwd .
```

Resolve a pending approval:

```bash
uv run glassbox session approve SESSION_ID APPROVAL_ID --cwd .
uv run glassbox session deny SESSION_ID APPROVAL_ID --cwd .
```

For handoff across workspaces, export from the source workspace, import in the
receiving workspace, then inspect the new imported session ID:

```bash
uv run glassbox session export SESSION_ID handoff.json --cwd .
uv run glassbox session import handoff.json --cwd ../other-workspace
```

Imported sessions are historical and inspection-only. They are not silently
attached to a live runtime owner.

## Current Shipped Boundary

The shipped interactive terminal UX now has these honest boundaries:

- `chat` owns the live in-process event stream for the session it starts and launches the full-screen TUI by default in supported terminals
- `attach` can either reopen a persisted session locally or live reconnect to a healthy daemon-owned session in the same TUI
- terminal attach does not silently pretend a terminal is still live when the
  workspace daemon is stale, unavailable, or the session is only historically
  inspectable
- implicit unsupported terminal launches fall back to plain mode, while explicit `--tui` requests fail clearly when they cannot be honored
- imported handoff packages create inspectable local history rather than a live
  multi-user continuation

## Troubleshooting Full-Screen Chat

- If the app does not launch because the terminal is unsupported, retry with `--plain` or use one-shot commands such as `session run`, `session message`, `session answer`, `session approve`, and `session deny`.
- If the header shows reconnecting, wait for the live stream to recover before submitting mutations; the composer explains when submission is blocked.
- If the runtime becomes unavailable, inspect the latest transcript and use `glassbox daemon status --cwd .` when a daemon owns the workspace.
- If a completed session opens historical-only, use the dashboard or export/import workflows for inspection, or start a new chat/fork when continuation is needed.
- If dashboard startup is unavailable during `session chat`, the terminal chat can continue. Use `glassbox dashboard serve --cwd .` later to inspect persisted sessions.

## V2 Ownership Decision

`GBX-300` chooses a stronger persistent-runtime model for v2 while preserving
the current embedded workflow as a valid local mode.

The intended ownership split is:

- embedded mode: `glassbox session chat` continues to own the live session inside the
  current process for operators who want an ephemeral terminal-first workflow
- background mode: `glassbox daemon start` owns the live runtime for one
  workspace when the operator wants runtime continuity beyond a single terminal
  process
- browser mode: `glassbox dashboard serve` remains the operator console and session
  browser; it is not the authoritative runtime owner

This means `attach` now resolves one of two explicit behaviors:

- persisted local attach: reopen a session from stored state when no daemon owns
  the workspace
- live daemon attach: reconnect a terminal UI to a session actively owned by a
  background runtime

## Persistent Runtime Semantics For V2

For the command-by-command daemon operating guide, see
[persistent-runtime.md](./persistent-runtime.md).

The first daemon-backed ownership slice now ships with these semantics:

- `glassbox daemon start` backgrounds one workspace-scoped runtime owner and
  hosts the dashboard for that workspace
- `glassbox daemon status` reads the workspace-local owner metadata and checks
  `/healthz` on the hosted dashboard
- `glassbox daemon stop` terminates the active owner and releases the
  workspace-local lock under `.glassbox/`

Operators should expect these runtime semantics:

- only one background runtime owner exists per workspace
- the owner process is responsible for live turn execution, event fanout,
  approval resumption, and shutdown behavior
- browser observation, health inspection, and terminal attach remain separate
  surfaces even when they ultimately talk to the same owner
- if the owner becomes unavailable, Glassbox should say so explicitly instead of
  silently pretending a historical snapshot is still a live session

With cross-process attach in place, local mutating CLI flows such as `run`,
`chat`, `message`, `answer`, `approve`, `deny`, `fork`, `resume`, and `rebuild`
still reject execution while a daemon owns the same workspace runtime, while
`attach` becomes the terminal-native reconnect surface for that owner.

Operators should also expect explicit messaging for these states:

- live: the terminal is attached to the daemon-owned session and receives live
  event updates
- reconnecting: the live stream is retrying after a transport interruption
- unavailable: the daemon owner exists but the runtime cannot be reached for
  live attach
- stale: stale owner metadata is reported before Glassbox reopens the persisted
  session locally
- historical-only: completed, failed, or cancelled sessions remain inspectable
  but do not pretend to support live attach

The first persistent-runtime slice is intentionally still local-first. It does
not imply remote orchestration, browser-native terminal control, or multi-user
coordination.

For v2 team handoff semantics, Glassbox treats runtime ownership and session
custody as separate concerns. Runtime ownership prevents conflicting writers;
session custody names who is expected to resolve a paused, failed, or historical
workflow next. See [team-workflows.md](./team-workflows.md) for the identity and
handoff contract.

## Related Guides

- [dashboard.md](./dashboard.md)
- [terminal-interaction-model-v5.md](./terminal-interaction-model-v5.md)
- [persistent-runtime.md](./persistent-runtime.md)
- [team-workflows.md](./team-workflows.md)
- [branching.md](./branching.md)
- [tool-policy.md](./tool-policy.md)
