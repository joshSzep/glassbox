# Dashboard Guide

Glassbox has two dashboard modes:

- a co-hosted dashboard started by `glassbox session chat`
- a standalone dashboard started by `glassbox dashboard serve`

Both read the same persisted session state and the same event stream model.

## Co-Hosted Dashboard During `session chat`

`glassbox session chat` starts a dashboard by default in the same process unless you pass `--no-dashboard`.

```bash
uv run glassbox session chat --cwd .
```

When startup succeeds, the terminal prints a session-specific URL like:

```text
http://127.0.0.1:8765/?session=SESSION_ID
```

Open that URL while the full-screen terminal chat is still running to watch the same live session that the terminal is driving in the SPA dashboard. The TUI keeps the URL visible in the header and exposes open/copy actions through the command palette, so browser handoff remains available after terminal scrollback moves on.

The intended split is simple: the terminal remains the primary coding-agent conversation surface, and the dashboard is the paired operator console for deeper inspection. Use the dashboard when you want queue views, lineage, event details, tool output, replay/eval cues, or broader workspace context without interrupting the chat flow.

If default dashboard startup fails, `chat` keeps the terminal workflow running and prints a warning that the dashboard is unavailable for that session.

If you explicitly set `--dashboard-host` or `--dashboard-port` and startup fails, `chat` exits with an error instead.

## Standalone Dashboard With `serve`

Use `serve` when browser access should outlive a particular `chat` process or when you want to inspect persisted sessions without an active interactive terminal session.

```bash
uv run glassbox dashboard serve --cwd . --host 127.0.0.1 --port 8765
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
- long-run status cues for healthy, paused, stale, stuck, idle, or completed
  work
- transcript
- recent sessions
- next action composer
- current turn
- turn timeline with long-run checkpoint, compaction, attempt, verification,
  approval, question, cancellation, and recovery evidence
- turn metrics
- active tool calls
- live command output
- pending approvals
- event log

The changeset surface at `/app/changesets` is the v13 review-loop panel for
local changesets. Terminal `/review dashboard CHANGESET_ID` and post-create
review output hand off directly to `/app/changesets/CHANGESET_ID` when a
dashboard URL is available. The panel shows review readiness, feedback and
response status, manual evidence, changed-file inventory summaries,
verification readiness and retained artifacts, affected topology subsystems
when available, handoff posture, commit preparation, candidate-adoption
comparisons when a branch-search candidate is attached, generated review brief
artifacts, source evidence, limitations, and safe inspection commands.
Skipped browser, dashboard, and accessibility evidence is shown as skipped live
evidence with its retained `not_run`, `not_applicable`, or skipped posture and
skip reason, so the row reads as a limitation instead of a pass.

The quick-action row refreshes inventory, previews verification, refreshes
feedback status, generates lifecycle briefs, and reloads handoff posture. The
manual evidence form attaches an explicit local evidence record and reports the
created evidence ID after the API returns. Feedback rows include a compact
`Fixup` action for recording response-linked changed-path inventory from the
current workspace diff, plus the equivalent `glassbox changeset feedback
fixup FEEDBACK_ID --from-workspace --cwd .` command for terminal fallback. These
actions are read-only or evidence-only: they do not run tests, stage, commit,
push, open a PR, merge, deploy, publish, resolve feedback, or imply reviewer
approval.

The affected-subsystems panel names package/app components, topology freshness,
matched paths, test roots, owner hints, and dependency hints without treating
stale topology as current fact. The adoption panel shows the selected
candidate, rejected alternatives, retained rationale, verification and risk
posture, accepted risks, and follow-up actions while stating that Glassbox did
not merge, rebase, stage, commit, push, or open a PR.

The browser first reads `GET /sessions/{session_id}` and then subscribes to `GET /sessions/{session_id}/events`.
Session summary and snapshot responses include a `long_run_status` read model
derived from persisted events, latest checkpoints, recent durable tool-attempt
heartbeats, and session metadata. Use it as the dashboard's quick "is this
alive or stuck?" signal, then inspect the timeline, event log, or tool-attempt
evidence for detail.
The Timeline tab keeps long-running history compact by showing checkpoint and
compaction source ranges, recent tool-attempt artifacts, pending intervention
evidence, and loaded verification/recovery event markers before the per-turn
narrative.
The Actions tab includes Recovery guidance when retained state points to stale
attempts, stale compactions, incomplete turns, failed verification, provider
degradation, or daemon/stream interruption. Guidance lists inspection commands
first; mutating recovery still requires explicit controls or confirmation flags.

The v2 operator-console model builds on this shell rather than replacing it. See
[operator-console.md](./operator-console.md) for the multi-session overview,
queue, health, and priority contract that future dashboard tasks should follow.
For the v9 cockpit target, priority rules, responsive and keyboard
expectations, and backend/frontend data-source map, see
[dashboard-cockpit-contract.md](./dashboard-cockpit-contract.md). For the v10
long-running terminal and dashboard cockpit target, see
[long-run-cockpit-contract.md](./long-run-cockpit-contract.md).
For the v7 evidence, comparison, metrics, policy, provider, and release-cue
target, see [dashboard-evidence-v7.md](./dashboard-evidence-v7.md).
For the v8 autonomy-control-room information architecture, see
[autonomy-console.md](./autonomy-console.md).

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
- request cancellation of an active live turn
- create a fork from an allowed historical turn

## Policy, Replay, Eval, Provider, And Verification Cues

The dashboard surfaces policy, replay, eval, provider canary, and release
evidence only when the persisted session snapshot or workspace aggregate already
includes that state. The browser does not run replay, eval, provider canary, or
release workflows, does not reinterpret their results, and does not replace the
CLI as the authoritative execution path.

Verification cues are promoted into the overview only when they can affect the
next operator decision: blocking replay/eval evidence appears before actions,
while advisory drift appears when an approval, question, or failure depends on
artifact context. Detailed artifact paths, target paths, failing test names,
freshness, inherited provenance, timed-out state, provider canary status, policy
source labels, eval coverage relevance, and release evidence freshness remain in
the Evidence tab.

Read cue labels this way:

- blocking replay/eval/release evidence reports failures, errors, or failing tests and should stop optimistic triage
- advisory evidence is stale, inherited, timed out, or provider-canary evidence that needs judgment
- provider canary evidence is advisory compatibility evidence, not deterministic release signoff
- missing evidence is neutral; it means the snapshot does not retain that proof, not that verification passed

The workspace overview also includes a read-only provider evidence cue. It names
the configured provider/model when known, shows the retained canary
`freshness_status` and `latest_status`, labels the cue as advisory, and points
back to `glassbox provider diagnostics --cwd .` and
`glassbox provider canary evidence --cwd .` for inspection.

Use displayed artifact paths as copyable local references, then run the
appropriate CLI command when reproduction, coverage, provider, or audit output is
needed:

```bash
uv run glassbox replay run SESSION_ID --json
uv run glassbox eval run --cwd .
uv run glassbox eval audit --cwd .
uv run glassbox provider canary evidence --cwd .
uv run glassbox artifacts inspect --json
```

Cancellation cues appear as live turn state and event-stream updates. Treat a
cancelled turn as intentional operator evidence, then use replay/eval if you
need to prove the cancellation event family remains stable.

## Troubleshooting

- If you used `glassbox session chat --no-dashboard`, start `glassbox dashboard serve` and open `/`.
- If the co-hosted dashboard was unavailable, the session may still be running normally in the terminal.
- If you are attached through the TUI and no dashboard URL is present, open the command palette to confirm whether the dashboard is unavailable or start `glassbox dashboard serve --cwd .` separately.
- If `/` reports that SPA assets have not been built, run `pnpm --dir frontend build` from the repository root before serving the development checkout.
- If the selected session shows `live unavailable`, treat the snapshot as persisted history unless another runtime is known to be driving it.
- If cancellation, approval, or answer controls are disabled, inspect the visible disabled reason and confirm the session is not historical-only.
- If a direct `?session=...` URL is stale or invalid, the dashboard returns to the session index instead of leaving the browser stuck.

## Related Guides

- [frontend-development.md](./frontend-development.md)
- [interactive-workflows.md](./interactive-workflows.md)
- [terminal-interaction-model-v5.md](./terminal-interaction-model-v5.md)
- [v4-ux-release-gate.md](./v4-ux-release-gate.md)
- [persistent-runtime.md](./persistent-runtime.md)
- [branching.md](./branching.md)
- [runtime-context.md](./runtime-context.md)
- [v6-cancellation-contract.md](./v6-cancellation-contract.md)
