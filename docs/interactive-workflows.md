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

## Scope Boundary

The interactive terminal UX is intentionally process-local in v1.

- `chat` owns the live in-process event stream for the session it starts
- `attach` can reopen a persisted actionable session later
- Glassbox does not yet claim cross-process terminal attach to another already-running session owner

For cross-process observation, use the dashboard.

## Related Guides

- [dashboard.md](./dashboard.md)
- [branching.md](./branching.md)
- [tool-policy.md](./tool-policy.md)
