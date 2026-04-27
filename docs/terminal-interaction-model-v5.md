# v5 Terminal Interaction Model

For the v5 task graph, see [tasks-v5.md](./tasks-v5.md). For the current terminal baseline, see [terminal-ux-audit-v5.md](./terminal-ux-audit-v5.md).

This document defines the intended full-screen `glassbox session chat` interaction model. It is a product contract for the TUI migration: implementation details can evolve, but the user-facing hierarchy and behavioral rules should remain stable unless a later task updates this document deliberately.

## Product Role

`glassbox session chat` is the primary coding-agent conversation surface.

The terminal is where the user thinks with the agent, writes prompts, reads assistant responses, follows tool work, answers questions, approves or denies risky actions, and recovers from ordinary runtime interruptions. The web dashboard remains co-hosted by default and serves as the deeper operator console for queues, evidence, metrics, lineage, compare, replay/eval cues, runtime context, and raw event inspection.

The terminal must be chat-first. It may expose immediate evidence and detail when that helps coding flow, but it should not become a terminal clone of the v4 operator dashboard.

## Default Layout

The full-screen app has five primary regions.

```text
+----------------------------------------------------------------------+
| Header: Glassbox | session | model | cwd | runtime | dashboard        |
+----------------------------------------------------------------------+
| Conversation transcript                                               |
|                                                                      |
| User                                                                 |
|   Prompt text                                                         |
|                                                                      |
| Glassbox                                                             |
|   Streaming or completed assistant response                           |
|   Tool cards grouped under the current turn                           |
|                                                                      |
+----------------------------------------------------------------------+
| Action strip: pending approval/question/failure/reconnect if present  |
+----------------------------------------------------------------------+
| Composer: multiline prompt or answer draft                            |
+----------------------------------------------------------------------+
| Footer: key hints, command palette, current mode                       |
+----------------------------------------------------------------------+
```

An optional details pane may open on the right or bottom depending on terminal size. It is not visible by default.

## Region Responsibilities

### Header

The header provides orientation, not diagnostics overload.

It should show:

- short session ID
- model name, truncated when needed
- workspace or cwd, truncated from the left when needed
- branch label or lineage hint when available
- runtime ownership: local, daemon, historical-only, unavailable
- stream state: starting, live, reconnecting, stale, unavailable
- current mode: ready, thinking, tool running, awaiting approval, awaiting answer, failed
- dashboard availability and a visible hint for open/copy dashboard actions

The header must remain stable under live updates. Long paths and labels should truncate predictably instead of shifting layout.

### Conversation Transcript

The transcript is the main surface. It should read as a coding-agent conversation grouped by turns, not as a raw event log.

It should render:

- user messages as prompts or answers in conversational order
- assistant responses with live streaming and clean finalization
- compact tool cards under the relevant assistant turn
- system notices only when they affect the coding flow
- failures as meaningful conversation moments with recovery guidance
- artifacts, paths, or generated outputs only when they are relevant to the current conversation

The transcript should autoscroll while the user is at the latest activity. If the user scrolls upward intentionally, live updates should not fight them. A jump-latest shortcut must be available.

### Action Strip

The action strip is visible only when there is a current decision, blocker, or recovery state that deserves priority over ordinary prompting.

It should surface:

- pending approval
- pending `ask_user` question
- active reconnect or unavailable runtime state
- active turn wait state when prompt submission is unsafe
- failed turn or failed session recovery guidance
- historical-only attach state

The action strip must never hide the composer permanently. It should claim enough space to make the next action clear, then let the user return to chat.

### Composer

The composer is a multiline editor for prompts and answer drafts.

It should support:

- readable multiline editing
- paste handling for code, markdown, and stack traces
- draft preservation across focus changes and recoverable submission failures
- disabled or redirected states when prompting is unsafe
- local history if accepted by implementation tasks

Composer drafts are local UI state. They become canonical only after successful prompt or answer submission through the session client.

### Footer And Help

The footer should show only the highest-frequency controls. It is not a manual.

At minimum, it should point to:

- send or newline behavior
- command palette
- jump latest
- details toggle when available
- quit or exit behavior

Full shortcut discovery belongs in the command palette or help overlay.

## Keyboard Contract

The exact key choices may be refined during implementation, but the following behaviors are required.

| Action | Required behavior |
| --- | --- |
| Send prompt or answer | Keyboard-accessible from composer without leaving the chat flow. |
| Insert newline | Supported in composer without accidental submission. |
| Open command palette | Available globally outside destructive confirmation states. |
| Jump latest | Returns transcript to newest activity and resumes autoscroll. |
| Toggle details | Opens and closes the optional details pane without losing composer draft. |
| Open dashboard | Available from command palette and, where practical, a direct shortcut. |
| Copy dashboard URL | Available even after startup scrollback is gone. |
| Copy session ID | Available without selecting terminal text manually. |
| Approve | Available only when a pending approval is current and context is clear. |
| Deny | Available only when a pending approval is current and context is clear. |
| Submit answer | Available when a pending question is current. |
| Scroll transcript | Does not move composer focus unexpectedly. |
| Escape | Closes transient UI first, then returns focus to the prior surface. |
| Ctrl+C | Cancels transient UI or begins the documented interruption flow; it must not silently abandon a live session. |
| Quit | Requires confirmation when the state is ambiguous or an active turn is running. |

Live updates must never steal focus from the composer, command palette, approval decision, question answer, or confirmation modal.

## Command Palette Contract

The command palette replaces hidden slash-command discovery as the primary action discovery surface.

It should include commands for:

- show concise status
- open dashboard
- copy dashboard URL
- copy session ID
- jump latest
- toggle details pane
- approve pending action
- deny pending action
- focus question answer
- submit question answer
- interrupt or cancel when backend support exists
- clear visual transcript if implemented as display-only state
- quit
- show keyboard shortcuts

Commands must be context-aware. Disabled commands should explain why they are unavailable.

Slash-command compatibility may remain during migration, but slash commands must route through the same command registry rather than duplicating behavior.

## Action Priority Rules

When multiple states are present, the terminal should prioritize what the user can safely do next.

1. Runtime unavailable or historical-only state that blocks mutation.
2. Pending approval that blocks tool execution.
3. Pending `ask_user` question that blocks the turn.
4. Failed turn or failed session requiring recovery or inspection.
5. Reconnecting stream where mutation safety is uncertain.
6. Active tool or model turn where another prompt cannot yet be sent.
7. Idle running session ready for the next prompt.

Approval and question actions should appear before generic prompting. Historical-only and unavailable states should disable mutation controls and make the reason visible.

## Transcript Hierarchy Rules

The transcript should optimize for comprehension of the coding session.

- User prompts and answers are high-signal conversation anchors.
- Assistant text is the main response surface and should stream live.
- Tool activity is grouped under the relevant turn and summarized by default.
- Tool output appears as a short inline snippet only when useful; longer output belongs behind expansion or in details.
- Tool failure is more important than ordinary tool completion and should be visibly distinct.
- Approval requests are both tool activity and action states; when pending, they must be promoted to the action strip.
- Questions are both tool activity and action states; when pending, they must be promoted to the action strip.
- Artifacts and paths should be compact, copyable where practical, and handed off to the dashboard for deeper inspection.
- Raw event sequence details should not appear in the default transcript unless the user opens details or status diagnostics.

## Runtime And Stream States

The TUI must distinguish these states in user-facing language:

- starting local runtime
- dashboard starting
- dashboard ready
- dashboard unavailable but chat continuing
- explicit dashboard binding failure
- live local session
- live daemon-attached session
- reconnecting stream
- stream reconnected
- runtime unavailable
- stale owner metadata
- historical-only session
- failed session

Mutation controls should reflect runtime safety. If the terminal cannot prove a prompt, answer, or approval can be submitted safely, the control should be disabled with a concise reason.

## Dashboard Handoff

The co-hosted dashboard is part of the default chat experience.

The terminal should make dashboard handoff persistent by providing:

- header indication when a dashboard URL exists
- command palette action to open the dashboard
- command palette action to copy the dashboard URL
- action or details links where deeper evidence is better inspected in the browser

The terminal must remain usable if the browser is never opened. The dashboard is a paired operator console, not a required chat dependency.

## Fallback Contract

The full-screen TUI should become the default in supported TTYs.

Fallback behavior must be explicit for:

- stdin redirected
- stdout redirected
- CI-like environments
- dumb or unsupported terminals
- explicit `--plain` if retained

Fallback may either run the old line-mode loop or refuse interactive chat with a clear message that points users to one-shot commands and supported terminal usage. During migration, retaining `--plain` is acceptable for debugging and test continuity. The release gate decides whether plain mode remains a supported user feature.

## Compatibility With Existing Semantics

The TUI may change presentation and discovery, but it should not change core semantics:

- session state remains event-sourced
- backend services remain authoritative for mutations
- daemon ownership rules remain explicit
- approvals remain explicit decisions
- pending questions remain routed through answer semantics
- co-hosted dashboard behavior remains default for local chat
- one-shot commands remain scriptable and recoverable

## Manual Validation Checklist

Before the TUI becomes default, manually verify at least these workflows:

- launch new chat with no initial prompt
- launch new chat with an initial prompt
- send a multiline prompt with pasted code
- watch assistant streaming in a normal-width terminal
- watch assistant streaming in a narrow terminal
- inspect compact tool activity and expanded details
- answer a pending question without copying an ID
- approve and deny pending approvals without copying an ID
- open and copy the dashboard URL after scrollback has moved
- attach to a daemon-owned live session
- attach to a local persisted actionable session
- handle reconnecting and unavailable runtime states
- quit during idle state
- quit or interrupt during active turn
- run with redirected input or output and observe the documented fallback behavior
