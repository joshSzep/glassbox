# Glassbox v9 Command Surface De-Emphasis Review

For the docs hub and workflow guides, start at [README.md](./README.md). Pair
this review with [v9-vocabulary.md](./v9-vocabulary.md) and
[daily-workflow-quickstart.md](./daily-workflow-quickstart.md).

`GBX-932` reviews the public command and dashboard surface after
`glassbox command guide` was added. It does not remove commands or routes. The
goal is to make daily work feel central while preserving scriptable recovery,
release, and maintenance workflows.

## Classification

### Daily Commands

These commands should remain prominent in quickstarts, command-guide output,
and dashboard next-action copy:

| Area | Commands | Why they are daily |
| --- | --- | --- |
| First run | `readiness check` | Explains whether the workspace can start useful local work. |
| Sessions | `session chat`, `session run`, `session list`, `session status`, `session message`, `session attach` | Covers starting, inspecting, and continuing the primary terminal workflow. |
| Decisions | `session answer`, `session approve`, `session deny`, `session cancel` | Resolves pending operator questions, action gates, and runaway turns. |
| Tasks | `task list`, `task show`, `task continue` | Makes durable task plans and continuation visible. |
| Verification | `eval recommend`, focused `eval run`, focused `replay run` | Helps operators verify ordinary changes. |
| Provider posture | `provider diagnostics`, `provider recommend` | Makes optional provider readiness visible before longer work. |
| Dashboard | `dashboard serve` | Keeps the browser cockpit accessible outside `session chat`. |

### Advanced Commands

These are useful for regular operators after the happy path, but should be
introduced from workflow guides or contextual next actions instead of the first
screen:

| Area | Commands | De-emphasis guidance |
| --- | --- | --- |
| Branches | `session fork`, `branch-search start`, `branch-search list`, `branch-search show`, `branch-search select`, `branch-search reject`, `branch-search needs-review` | Link from branching and task evidence docs; keep branch-search framed as bounded comparison, not automatic merge. |
| Memory | `memory list`, `memory show`, `memory add`, `memory candidates`, `memory capture`, `memory reject-candidate`, `memory confirm`, `memory invalidate`, `memory prune` | Show review and confirmation paths first; keep pruning in maintenance guidance. |
| Repository index | `repo index status`, `repo index search`, `repo index show`, `repo index build` | Show status before build; describe the index as rebuildable derived state. |
| Autonomy profiles | `autonomy profile list`, `autonomy profile show` | Link from autonomy-mode docs and provider posture; do not require new operators to tune profiles before first chat. |
| Jobs | `job list`, `job show`, `job cancel`, `job retry`, `job abandon` | Surface from task continuation and recovery cues, especially failed or retryable jobs. |
| Observability | `observability status` | Use as the broad read-only health check when a workflow feels stuck. |

### Recovery And Internal-Maintenance Commands

These commands are necessary when local state needs care. They should be easy
to find from recovery docs and dashboard cues, but not presented as ordinary
first-run work:

| Area | Commands | De-emphasis guidance |
| --- | --- | --- |
| Daemon | `daemon start`, `daemon stop`, `daemon status` | Prefer `daemon status` as the first read-only command; mutating commands need explicit operator intent. |
| Projections | `projection check`, `projection rebuild` | Prefer `projection check --all`; describe rebuild as derived-state repair from canonical events. |
| Artifacts | `artifacts inspect`, `artifacts prune` | Prefer inspect and dry-run guidance before prune. |
| Backup | `backup create`, `backup inspect`, `backup restore` | Keep create/inspect visible before restore. Restore remains a deliberate recovery action. |
| Performance | `performance budgets` | Keep as diagnostic reference for larger-session pressure, not a daily command. |

### Release-Evidence Commands

These commands are central to contributors and release reviewers, but they
should not dominate onboarding:

| Area | Commands | De-emphasis guidance |
| --- | --- | --- |
| Command inventory | `command tree`, `command guide --json` | Use `command guide` for operator discovery and `command tree` for exhaustive review. |
| Replay and eval | `replay bundle export`, `replay bundle inspect`, `replay bundle run`, `eval audit`, `eval profile list`, `eval profile show`, `eval report`, `eval case list`, `eval case show`, `eval case promote`, `eval case refresh` | Keep in replay/eval and release evidence docs; guide daily users toward `eval recommend` first. |
| Provider canaries | `provider canary run`, `provider canary evidence` | Label as advisory provider evidence, not release authority. |
| Package scripts | `scripts/validate_package_contents.py`, release-gate scripts | Keep in packaging and release docs rather than quickstart paths. |

## Dashboard Surface Inventory

The dashboard is currently organized around these surfaces:

| Surface | Route or component | Classification | De-emphasis guidance |
| --- | --- | --- | --- |
| Workspace overview | `/app`, `WorkspaceOverview` | Daily | Keep as the first cockpit surface for queues, runtime, projections, and session attention rows. |
| Session inspector | `/app/sessions/:id`, `SessionInspector` | Daily with advanced tabs | Keep overview, transcript, actions, and evidence prominent; treat timeline, metrics, runtime, events, lineage, and compare as drill-down tabs. |
| Task console | `/app/tasks`, `TaskAutonomyConsole` | Daily for task-plan work | Keep active, blocked, and failed task filters prominent; background and historical filters are advanced. |
| Memory and repository intelligence | `/app/memory`, `/app/repository-index`, `KnowledgeAutonomyConsole` | Advanced | Link from memory/index cues and daily workflow docs, not the first-run narrative. |
| Branch search | `/app/branch-search`, `BranchSearchConsole` | Advanced | Keep branch comparison separate from session forking; do not imply candidate selection mutates parent history. |

Current inspector tabs are `overview`, `transcript`, `timeline`, `actions`,
`lineage`, `compare`, `runtime`, `evidence`, `metrics`, and `events`. The
daily path should emphasize `overview`, `transcript`, `actions`, and
`evidence`; the rest are drill-down views for diagnosis, comparison, or release
review.

## Recommendations

- Keep `glassbox command tree` exhaustive and structural.
- Keep `glassbox command guide` as the operator-friendly entrypoint, grouped by
  start work, inspect state, unblock work, verify work, recover workspace, and
  release evidence.
- Keep quickstarts focused on readiness, chat, dashboard, decisions, verify,
  and recovery checks.
- Keep release-only commands in replay/eval, packaging, and release evidence
  docs.
- Keep dashboard top-level navigation centered on active work, with advanced
  surfaces reachable from cues and links.
- Add contextual command-copy affordances in later cockpit tasks before adding
  more top-level commands.
- Avoid new aliases unless a command name is proven confusing during
  dogfooding; the current names are consistent with the v9 vocabulary.

## Compatibility Plan

No command, route, JSON field, event type, or dashboard panel is deprecated by
this review.

If a future task de-emphasizes or renames a surface:

- keep the old command or route working for at least one minor release
- document the replacement in `glassbox command guide`, the relevant workflow
  doc, and command help
- test both the old path and the preferred path while the alias exists
- avoid changing persisted event names, projection columns, eval profile names,
  or release evidence schema keys for copy-only reasons
- preserve recovery and release automation even when the daily docs hide those
  details from first-run paths

## Validation

The review used:

```bash
uv run glassbox command tree
uv run glassbox command guide --json
```

The dashboard inventory was checked against `frontend/routing/app-route.ts` and
the console components under `frontend/components/console/`.
