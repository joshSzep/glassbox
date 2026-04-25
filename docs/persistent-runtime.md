# Persistent Runtime Guide

Use the persistent runtime when a workspace should have one long-lived Glassbox
owner that survives terminal exit and can accept later terminal reattachments.

For team workflows, this runtime owner is the writer-safety boundary. It is not
the same as the session custodian or acting operator described in
[team-workflows.md](./team-workflows.md).

## Start The Workspace Runtime

Start one background owner for the workspace:

```bash
uv run glassbox daemon start --cwd .
```

The command prints the dashboard URL and daemon PID. The owner metadata and logs
live under `.glassbox/` in the selected workspace.

Use `--db-path` when the workspace database is not the default
`.glassbox/glassbox.sqlite3`:

```bash
uv run glassbox daemon start --cwd . --db-path .glassbox/glassbox.sqlite3
```

## Discover Runtime Status

Use status before attaching, troubleshooting, or scripting recovery:

```bash
uv run glassbox daemon status --cwd .
```

The human output reports:

- runtime owner state: `running`, `stale`, or `not_running`
- workspace and database paths
- owner metadata and log paths
- dashboard, health, and session-index URLs when an owner exists
- suggested `start`, `attach`, and `stop` commands for the selected workspace

For scripts, use JSON:

```bash
uv run glassbox daemon status --cwd . --json
```

The JSON output is a discovery surface for runtime availability only. Session
truth still comes from the event store and session snapshot APIs.

## Attach From A New Terminal

After the daemon is running, attach to an actionable session from another
terminal:

```bash
uv run glassbox attach SESSION_ID --cwd .
```

When the workspace daemon is healthy, `attach` reconnects to the daemon-owned
session over the same snapshot, action, and event-stream surfaces used by the
dashboard. Freeform prompts, pending `ask_user` answers, `/approve`, `/deny`,
`/status`, `/help`, and `/exit` keep the same terminal behavior as local
interactive mode.

If no daemon owns the workspace, `attach` falls back to reopening an actionable
persisted session locally.

## Stop The Runtime

Stop the active owner when you want local commands such as `run`, `chat`,
`message`, `answer`, `approve`, `deny`, `fork`, `resume`, or `rebuild` to own
the workspace directly again:

```bash
uv run glassbox daemon stop --cwd .
```

## State Meanings

- `running`: owner metadata exists, the owner process is alive, and `/healthz`
  decides whether the daemon is reachable.
- `stale`: owner metadata exists but the recorded process is gone. Start or stop
  the daemon to clear stale metadata explicitly.
- `not_running`: no owner metadata exists for the selected workspace/database.
- `historical-only`: the session is completed, failed, or cancelled. Inspect it
  in the dashboard or status views, but do not expect live terminal attach.

## Troubleshooting

- If `daemon status` shows `running` with health `unreachable`, the owner
  metadata exists but the dashboard health check failed. Inspect the stdout and
  stderr log paths shown by `daemon status`, then stop and restart the daemon.
- If `daemon status` shows `stale`, run `glassbox daemon start --cwd .` to
  recover by replacing stale metadata, or `glassbox daemon stop --cwd .` to clear
  it without starting a new owner.
- If `attach` reports that a session is historical-only, use the dashboard
  session index or `glassbox status SESSION_ID --cwd .` for inspection.
- If the dashboard cannot find a direct `?session=...` URL, open the root
  session index printed by `daemon status` and select the session there.

## Related Guides

- [interactive-workflows.md](./interactive-workflows.md)
- [team-workflows.md](./team-workflows.md)
- [dashboard.md](./dashboard.md)
- [tasks-v2.md](./tasks-v2.md)
