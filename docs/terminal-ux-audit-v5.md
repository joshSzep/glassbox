# v5 Terminal UX Audit

For the v5 task graph, see [tasks-v5.md](./tasks-v5.md). This audit records the current `glassbox session chat` and `glassbox session attach` terminal experience before the full-screen TUI migration begins.

## Scope

This audit covers the interactive terminal client as shipped before v5 execution:

- new local chat sessions started by `glassbox session chat`
- local attach to persisted actionable sessions through `glassbox session attach SESSION_ID`
- daemon-backed live attach through the HTTP snapshot, action, and SSE surfaces
- event rendering through the current line renderer
- prompt routing for normal prompts, pending `ask_user` questions, and pending approvals
- co-hosted dashboard startup and failure behavior
- non-TTY and test-driven usage of the current line-mode loop

The audit intentionally evaluates the experience against the v5 goal: a full-screen coding-agent conversation with the browser dashboard preserved as the paired operator console. It does not treat old line-mode parity as the quality bar.

## Current Implementation Baseline

The current terminal client is a correct but minimal line-mode loop.

- [src/glassbox/cli/interactive_commands.py](../src/glassbox/cli/interactive_commands.py) starts `chat`, co-hosts the dashboard, submits an optional initial prompt, prints the attached session and dashboard URL, then enters the interactive loop.
- [src/glassbox/cli/interactive_session.py](../src/glassbox/cli/interactive_session.py) owns local prompt routing, slash-command parsing, prompt labels, blocked-state copy, and status/help handling.
- [src/glassbox/cli/daemon_attach.py](../src/glassbox/cli/daemon_attach.py) mirrors the same interaction model over daemon-owned session snapshot, action, and SSE endpoints.
- [src/glassbox/cli/renderer.py](../src/glassbox/cli/renderer.py) turns event envelopes into flat terminal lines and redraws prompt context by printing around the active prompt.
- [src/glassbox/core/events.py](../src/glassbox/core/events.py) already has richer event types than the terminal currently uses well, including assistant deltas, tool output chunks, approval requests, user questions, artifacts, and tool completion events.

The project currently has no terminal application framework dependency. The user-facing interaction is built from `input()`, `print()`, event subscription tasks, and a small `InteractivePromptState` helper.

## Representative Current Transcripts

These excerpts are provider-free characterizations derived from the current integration flows and command behavior. They are not meant to be golden transcripts; they show the shape of the experience that v5 replaces.

### Idle Chat Startup

```text
Started session SESSION_ID in /workspace
Attached to session SESSION_ID
Dashboard available at http://127.0.0.1:8765/?session=SESSION_ID
Interactive mode: type the next prompt, or use /status, /help, or /exit.
prompt>
```

The dashboard handoff exists, but it is a one-time line. Once scrollback moves, the terminal has no persistent dashboard affordance.

### Multi-Turn Chat

```text
Queued user message: Inspect the repository
Assistant: I received your request: Inspect the repository
Interactive mode: type the next prompt, or use /status, /help, or /exit.
prompt> Now summarize the tests.
Queued user message: Now summarize the tests.
Assistant: I received your request: Now summarize the tests.
Interactive mode: type the next prompt, or use /status, /help, or /exit.
prompt>
```

The semantics are correct, but the transcript is indistinguishable from log output. There is no stable conversation surface, turn grouping, markdown rendering, composer state, or recent activity model.

### Pending Question

```text
Question asked (QUESTION_ID): What colour should I use?
Pending question: QUESTION_ID: What colour should I use?
Interactive mode: answer the pending question, or use /status, /help, or /exit.
answer> blue
Answer submitted for question QUESTION_ID: blue
Assistant: I will use: blue
```

The question ID is hidden from normal command usage because freeform text routes correctly, which is good. The question itself is still just another printed context line rather than a first-class action surface.

### Pending Approval

```text
Approval requested: apply_patch (approval required: command policy)
This session is awaiting approval resolution for APPROVAL_ID. Freeform text is disabled until you use /approve or /deny.
Interactive mode: use /approve, /deny, /status, /help, or /exit.
approval> /approve
Approval resolved: approved by user
Assistant: Patch applied.
```

Approval routing avoids ID copying, but the decision surface is weak for a trust-critical moment. The terminal does not give the approval its own card, risk hierarchy, focus behavior, or confirmation/recovery feedback.

### Tool-Heavy Turn

```text
Tool requested: search [allow read_only via default:read_only]
Tool started: search [allow read_only via default:read_only]
Tool completed: search succeeded: found 3 results (exit code 0)
Artifact recorded: text at .glassbox/artifacts/run.txt
Assistant: Here is the answer.
```

The event stream is visible, but tool work is flat. Tool output chunks, arguments, stderr/stdout snippets, artifacts, and failures do not have a coherent inline policy.

### Failed Turn Or Session

```text
Turn failed: tool execution timed out
Interactive chat paused. Next action: wait for the active turn to finish before sending another prompt
```

Failure copy can be technically accurate while still feeling unhelpful. v5 needs failure states that explain what happened, what is still live, and what the user can safely do next.

### Daemon Attach And Reconnect

```text
Attached to live session SESSION_ID via http://127.0.0.1:8765/
Live runtime stream reconnecting...
Live runtime stream reconnected.
```

The current daemon path correctly distinguishes live attach from local persisted reopen. The reconnect UX is thin: it lacks persistent state, retry affordances, and clear mutation safety guidance while reconnecting.

### Dashboard Startup Failure

```text
Warning: dashboard unavailable at http://127.0.0.1:8765/: web server failed to start
Started session SESSION_ID in /workspace
Attached to session SESSION_ID
Interactive mode: type the next prompt, or use /status, /help, or /exit.
prompt>
```

The default fallback is right: terminal chat can continue when the optional default dashboard fails. Explicit dashboard binding failures remain hard failures, which protects user intent.

## Preserved Behaviors

The v5 TUI must preserve these semantics unless a later task explicitly changes them:

- `session chat` starts a new persisted session and keeps it attached for multiple turns.
- The co-hosted dashboard starts by default for local `session chat` and records the session dashboard URL.
- `--no-dashboard`, `--dashboard-host`, and `--dashboard-port` keep their current meaning.
- Default dashboard startup failure warns and allows chat to continue; explicit dashboard binding failure stops startup.
- Freeform input submits a new prompt only when the session is idle and running.
- Freeform input answers a pending `ask_user` question when the session is awaiting user input.
- Approval resolution remains explicit through approve or deny actions and must not be inferred from arbitrary freeform text.
- Normal interactive question and approval flows do not require users to copy IDs.
- `/status`, `/help`, and `/exit` or their v5 equivalents remain available.
- `attach` uses live daemon attach when a healthy daemon owns the workspace and local persisted reopen otherwise.
- Stale or unavailable daemon ownership is explicit rather than silently pretending a historical snapshot is live.
- Completed, failed, and cancelled sessions remain historical-only for attach unless backend semantics change.
- Session truth remains canonical in events, snapshots, projections, and runtime services, not browser or terminal-only state.
- Non-interactive session commands remain scriptable primitives.

## Issue Inventory

### Workflow Blockers

- The terminal cannot support a polished coding-agent conversation while built around blocking `input()`.
- There is no true multiline composer for substantial prompts, pasted code, or draft-preserving recovery.
- The current prompt redraw strategy cannot be made robust under heavy live output because it does not own the input buffer.
- Non-TTY behavior is not designed as a product surface; it is an accident of the line-mode implementation.

### High-Friction Interaction Issues

- The dashboard URL is easy to lose in scrollback even though the dashboard is central to the Glassbox model.
- Pending approvals and questions do not get visual hierarchy proportional to their importance.
- Slash commands are hidden behind `/help`; there is no command palette, contextual menu, or discoverable keyboard model.
- `/status` is broad and diagnostic, not a concise in-context answer to “what should I do now?”
- Attach and reconnect states are technically explicit but not reassuring during real work.

### Terminal Rendering Issues

- The transcript is a stream of event lines rather than a conversation grouped by turn.
- Assistant deltas are not rendered as a live assistant response in the main surface.
- Tool events are flat and equal-weight regardless of risk, duration, failure, output volume, or relation to the current turn.
- Long paths, command output, and artifacts have no terminal-width-aware display policy beyond ordinary wrapping.
- There is no stable header, footer, action strip, or detail pane.

### Keyboard And Input Issues

- No multiline editing contract exists for Enter versus newline behavior.
- No formal focus model exists because line mode has no focusable surfaces.
- Ctrl+C, EOF, and exit behavior are inherited from the line loop rather than designed around editing, modals, active turns, and safe shutdown.
- There is no command completion or shortcut discovery.

### Copy And Language Issues

- Current prompt-context lines are explicit but repetitive.
- Blocked input copy often explains what cannot happen before prioritizing the best next action.
- Failure and reconnect copy is too terse for high-trust coding-agent work.
- Approval text exposes IDs before it exposes a designed decision hierarchy.

### Test Coverage Gaps

- Existing tests characterize line-mode routing and prompt redraw, not full-screen usability.
- There is no Textual/widget harness yet for layout, focus, keybindings, or action dispatch.
- There is no pty/subprocess smoke strategy for launching the real command as a terminal app.
- Heavy stream turbulence, high-volume tool output, terminal resize, and paste handling are not covered.
- Manual terminal review artifacts are not defined.

## UX Conclusions For V5

The current terminal client is a correct control plane but not a product-quality coding-agent surface. v5 should not try to polish the existing `input()` loop into shape. It should introduce a real terminal app boundary with a framework-backed TUI, a pure conversation state model, and a reusable session client for local and daemon-owned sessions.

The default experience should become full-screen and chat-first. The browser dashboard should remain co-hosted by default and should be treated as the paired evidence and operator console, not as a replacement for a good terminal conversation.

The first implementation slices should prioritize:

- terminal interaction contract and framework choice
- reusable local/daemon session client
- pure conversation reducer
- full-screen app shell with persistent dashboard context
- live assistant streaming
- multiline composer
- first-class approval and question surfaces
- terminal-specific test harness
