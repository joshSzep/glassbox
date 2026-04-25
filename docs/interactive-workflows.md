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

`attach` is for sessions that are actionable from the operator side:

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

## Current Shipped Boundary

The current interactive terminal UX is intentionally process-local.

- `chat` owns the live in-process event stream for the session it starts
- `attach` can reopen a persisted actionable session later
- Glassbox does not yet claim that today's `attach` command can stream live
	terminal updates from another already-running session owner

For the shipped cross-process observation path, use the dashboard.

## V2 Ownership Decision

`GBX-300` chooses a stronger persistent-runtime model for v2 while preserving
the current embedded workflow as a valid local mode.

The intended ownership split is:

- embedded mode: `glassbox chat` continues to own the live session inside the
	current process for operators who want an ephemeral terminal-first workflow
- background mode: a future `glassbox daemon` command will own the live runtime
	for one workspace when the operator wants runtime continuity beyond a single
	terminal process
- browser mode: `glassbox serve` remains the operator console and session
	browser; it is not the authoritative runtime owner

This means the current `attach` command and the future daemon attach path are
not the same thing:

- current `attach`: reopen a persisted actionable session from stored state
- future live attach: reconnect a terminal UI to a session actively owned by a
	background runtime

Until the later persistent-runtime tasks land, the shipped `attach` command
should still be understood as the persisted-state re-entry path rather than the
final cross-process live attach UX.

## Persistent Runtime Semantics For V2

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

Until cross-process attach lands, local mutating CLI flows such as `run`,
`chat`, `attach`, `message`, `answer`, `approve`, `deny`, `fork`, `resume`, and
`rebuild` reject execution while a daemon owns the same workspace runtime.

The first persistent-runtime slice is intentionally still local-first. It does
not imply remote orchestration, browser-native terminal control, or multi-user
coordination.

## Related Guides

- [dashboard.md](./dashboard.md)
- [branching.md](./branching.md)
- [tool-policy.md](./tool-policy.md)
