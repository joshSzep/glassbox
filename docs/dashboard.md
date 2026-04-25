# Dashboard Guide

Glassbox has two dashboard modes:

- a co-hosted dashboard started by `glassbox chat`
- a standalone dashboard started by `glassbox serve`

Both read the same persisted session state and the same event stream model.

## Co-Hosted Dashboard During `chat`

`glassbox chat` starts a dashboard by default in the same process unless you pass `--no-dashboard`.

```bash
uv run glassbox chat --cwd .
```

When startup succeeds, the terminal prints a session-specific URL like:

```text
http://127.0.0.1:8765/?session=SESSION_ID
```

Open that URL while the interactive session is still running to watch the same live session that the terminal is driving.

If default dashboard startup fails, `chat` keeps the terminal workflow running and prints a warning that the dashboard is unavailable for that session.

If you explicitly set `--dashboard-host` or `--dashboard-port` and startup fails, `chat` exits with an error instead.

## Standalone Dashboard With `serve`

Use `serve` when browser access should outlive a particular `chat` process or when you want to inspect persisted sessions without an active interactive terminal session.

```bash
uv run glassbox serve --cwd . --host 127.0.0.1 --port 8765
```

Then open:

```text
http://127.0.0.1:8765/
```

The root view is the operator-console overview. It lets you inspect runtime
health, queue counts, and prioritized sessions from the browser instead of
copying a `session_id` first.

For daemon-backed runtime ownership, use `glassbox daemon status --cwd .` to
discover the dashboard URL, health URL, session index, owner metadata path, and
log paths for the active workspace runtime.

## What The Dashboard Shows

The dashboard shell exposes the operator surfaces backed by the snapshot and SSE APIs:

- workspace overview
- queue tabs for approvals, questions, failures, degraded sessions, and active work
- transcript
- recent sessions
- next action composer
- current turn
- turn timeline
- turn metrics
- active tool calls
- live command output
- pending approvals
- event log

The browser first reads `GET /sessions/{session_id}` and then subscribes to `GET /sessions/{session_id}/events`.

The v2 operator-console model builds on this shell rather than replacing it. See
[operator-console.md](./operator-console.md) for the multi-session overview,
queue, health, and priority contract that future dashboard tasks should follow.

## Live-State Meanings

Interpret the browser state this way:

- `connecting` means the snapshot loaded and the dashboard is attaching to the live SSE tail
- `live` means the browser is receiving incremental events
- `reconnecting` means the snapshot remains valid while the browser retries the live stream
- `live unavailable` means the persisted snapshot is readable but the live stream could not be re-established
- `historical snapshot` means the session is completed, failed, cancelled, or otherwise not expected to emit more events

## Browser Actions

The dashboard lets the operator:

- browse recent sessions from the root index
- open one selected session and inspect lineage, transcript, metrics, tools, approvals, and runtime context
- compare the selected session against its parent or child lineage snapshots without leaving the browser
- inspect replay or eval drift cues when snapshot-backed artifact context includes that evidence
- submit the next prompt for an idle running session
- answer a pending `ask_user` question
- resolve a pending approval
- create a fork from an allowed historical turn

## Troubleshooting

- If you used `glassbox chat --no-dashboard`, start `glassbox serve` and open `/`.
- If the co-hosted dashboard was unavailable, the session may still be running normally in the terminal.
- If the selected session shows `live unavailable`, treat the snapshot as persisted history unless another runtime is known to be driving it.
- If a direct `?session=...` URL is stale or invalid, the dashboard returns to the session index instead of leaving the browser stuck.

## Related Guides

- [interactive-workflows.md](./interactive-workflows.md)
- [persistent-runtime.md](./persistent-runtime.md)
- [branching.md](./branching.md)
- [runtime-context.md](./runtime-context.md)
