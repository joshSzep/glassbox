# Interactive Workflows

Glassbox has two main operator modes:

- `glassbox chat` starts a new interactive session
- `glassbox attach SESSION_ID` reopens an existing actionable session in the terminal

Use the lower-level commands when you need scripting, recovery, or precise control of a session state.

## Default Entry Point: `chat`

Start an interactive session:

```bash
uv run glassbox chat --cwd .
```

`chat` and `run` read optional repository defaults from
`glassbox.profile.json` at the selected `--cwd`. Use `--model-name` or
`--approval-mode` when one invocation needs to override those defaults.

Or start with an initial prompt:

```bash
uv run glassbox chat "Inspect the repository" --cwd .
```

Inside the interactive session:

- freeform text sends the next prompt while the session is idle and running
- freeform text answers the pending `ask_user` question when the session is awaiting user input
- `/approve` and `/deny` resolve the pending approval without requiring the approval ID
- `/status`, `/help`, and `/exit` remain available as explicit control commands

The terminal prompt changes with the session state, so the shell tells you whether it is waiting for a prompt, an answer, or an approval decision.

## Reopen A Persisted Session: `attach`

Use `attach` when you already have a session ID and want to reopen an actionable session:

```bash
uv run glassbox attach SESSION_ID --cwd .
```

`attach` now has two explicit modes:

- live daemon attach: if a healthy workspace daemon owns the runtime, `attach`
  reconnects the terminal to that live owner over the daemon's HTTP plus SSE
  surfaces
- persisted local reopen: if no daemon owns the workspace, `attach` reopens the
  persisted actionable session from local state

In either mode, `attach` is for sessions that are actionable from the operator side:

- idle running sessions waiting for the next prompt
- sessions awaiting `ask_user` input
- sessions awaiting approval resolution

It does not automatically start the dashboard. If you want browser observation after re-entering a session, run `glassbox serve` separately and use the session index in the dashboard.

## State-Driven Commands

Use the command that matches the current actionable state:

- `glassbox message SESSION_ID PROMPT` sends a fresh user prompt when the session is idle and running
- `glassbox answer SESSION_ID QUESTION_ID ANSWER` answers a pending `ask_user` question when the session is awaiting user input
- `glassbox approve SESSION_ID APPROVAL_ID` or `glassbox deny SESSION_ID APPROVAL_ID` resolves a pending approval when the session is awaiting approval
- `glassbox resume SESSION_ID` reloads a persisted session after restart without sending a new prompt
- `glassbox status SESSION_ID` prints the current state and the next valid operator action
- `glassbox session-export SESSION_ID OUTPUT` writes a portable handoff package for review without copying the workspace database
- `glassbox session-import PACKAGE` imports a handoff package into a new local historical session for inspection

Example:

```bash
uv run glassbox status SESSION_ID --cwd .
uv run glassbox message SESSION_ID "Continue with the next step" --cwd .
```

Answer a pending `ask_user` question:

```bash
uv run glassbox answer SESSION_ID QUESTION_ID "blue" --cwd .
```

Resolve a pending approval:

```bash
uv run glassbox approve SESSION_ID APPROVAL_ID --cwd .
uv run glassbox deny SESSION_ID APPROVAL_ID --cwd .
```

For handoff across workspaces, export from the source workspace, import in the
receiving workspace, then inspect the new imported session ID:

```bash
uv run glassbox session-export SESSION_ID handoff.json --cwd .
uv run glassbox session-import handoff.json --cwd ../other-workspace
```

Imported sessions are historical and inspection-only. They are not silently
attached to a live runtime owner.

## Current Shipped Boundary

The shipped interactive terminal UX now has these honest boundaries:

- `chat` owns the live in-process event stream for the session it starts
- `attach` can either reopen a persisted actionable session locally or live
  reconnect to a healthy daemon-owned session
- terminal attach does not silently pretend a terminal is still live when the
  workspace daemon is stale, unavailable, or the session is only historically
  inspectable
- imported handoff packages create inspectable local history rather than a live
  multi-user continuation

## V2 Ownership Decision

`GBX-300` chooses a stronger persistent-runtime model for v2 while preserving
the current embedded workflow as a valid local mode.

The intended ownership split is:

- embedded mode: `glassbox chat` continues to own the live session inside the
  current process for operators who want an ephemeral terminal-first workflow
- background mode: `glassbox daemon start` owns the live runtime for one
  workspace when the operator wants runtime continuity beyond a single terminal
  process
- browser mode: `glassbox serve` remains the operator console and session
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
- [persistent-runtime.md](./persistent-runtime.md)
- [team-workflows.md](./team-workflows.md)
- [branching.md](./branching.md)
- [tool-policy.md](./tool-policy.md)
