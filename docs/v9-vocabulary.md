# Glassbox v9 Vocabulary And Command Language

For the docs hub and workflow guides, start at [README.md](./README.md). Pair
this vocabulary with [v9-public-baseline.md](./v9-public-baseline.md) and
[daily-workflow-quickstart.md](./daily-workflow-quickstart.md) when describing
operator workflows.

Glassbox v9 uses a small product vocabulary across CLI help, dashboard labels,
operator docs, and release evidence. The goal is not to hide the implementation;
it is to make the same objects mean the same thing everywhere an operator sees
them.

## Core Terms

| Term | Operator meaning | Command and dashboard shape |
| --- | --- | --- |
| Session | A durable conversation and execution history in one local workspace. | Use `glassbox session ...`; dashboard session pages show transcript, actions, runtime, lineage, evidence, and metrics. |
| Task | A durable plan or continuation unit derived from session work. | Use `glassbox task ...`; dashboard task queues show plan steps, blocked reasons, budgets, events, and next actions. |
| Evidence | Retained proof for what happened or what should block release confidence. | Replay/eval reports, artifacts, command output, policy decisions, provider canaries, task events, and manual evidence. Deterministic replay/eval evidence is authoritative; provider evidence is advisory. |
| Memory | Operator-reviewed local workspace notes that can help later sessions. | Use `glassbox memory ...`; dashboard memory views must distinguish candidates, confirmed entries, invalid entries, and pruned entries. |
| Branch | A child session or bounded candidate path derived from existing history. | Use `glassbox session fork ...` for child sessions and `glassbox branch-search ...` for bounded candidate comparison. Branches must not mutate parent session history. |
| Verify | The act of proving behavior through explicit checks. | Use `glassbox eval ...`, `glassbox replay ...`, and task-specific test commands. In docs, prefer "verify work" over vague "validate output" unless talking about release gates. |
| Provider | Optional live model configuration and observed provider behavior. | Use `glassbox provider diagnostics`, `recommend`, and `canary`. Provider posture helps operators choose risk, but does not replace deterministic release evidence. |
| Daemon | The local background runtime owner for one workspace. | Use `glassbox daemon ...`; docs should call it the workspace runtime owner when explaining why only one mutating owner is supported. |
| Projection | Rebuildable derived read models from canonical events. | Use `glassbox projection check` and `rebuild`; dashboard should label degraded projections as derived-state issues while saying canonical events remain authoritative. |

## Preferred Language

Use these phrases consistently:

- "Start a session" for beginning terminal work with `glassbox session chat` or
  `glassbox session run`.
- "Inspect state" for reading sessions, tasks, memory, repository index,
  provider posture, daemon state, jobs, artifacts, observability, and
  projections.
- "Unblock work" for answering questions, approving or denying actions,
  cancelling a turn, retrying background jobs, or resolving stale runtime state.
- "Verify work" for replay, eval, focused tests, release reports, and retained
  evidence.
- "Recover workspace" for daemon, projection, artifact, repository index,
  backup, and job recovery guidance.
- "Release evidence" for deterministic gate, eval, package, provider-advisory,
  and manual evidence retained for release review.

Avoid introducing synonyms when an existing term is precise enough:

- Prefer "session" over "conversation" when referring to persisted runtime
  state.
- Prefer "task" or "task plan" over "workflow item" for durable plan state.
- Prefer "evidence" over "proof", "logs", or "audit data" when the data is
  part of an operator or release decision.
- Prefer "provider evidence is advisory" over "provider passed" unless naming
  a specific diagnostic or canary result.
- Prefer "projection degraded" over "database corrupt" when canonical events
  are healthy and only derived read state needs attention.

## Command Help Review

The `uv run glassbox command tree` review for `GBX-930` found the command
surface structurally aligned with the v9 public baseline:

- Daily workflow commands already use the core nouns:
  `session`, `task`, `memory`, `repo index`, `branch-search`, `provider`,
  `readiness`, `job`, `projection`, `dashboard`, and `daemon`.
- Release-evidence commands are visible but named as evidence tools:
  `replay`, `eval`, `eval report`, `eval recommend`, and `eval case`.
- Recovery surfaces are discoverable without being framed as first-run
  tutorials: `observability`, `artifacts`, `backup`, `job`, `projection`, and
  `daemon`.
- The most overloaded phrase is "status": it appears on sessions, repository
  index, daemon, and observability. Keep the commands for compatibility, but
  docs should name the object being inspected, such as "session status" or
  "daemon status".
- The most technical terms that intentionally remain visible are "daemon",
  "projection", and "provider canary". They are retained because operators need
  exact language when recovering local state or interpreting advisory provider
  evidence.

No command rename is recommended for `GBX-930`. The follow-on command discovery
task, `GBX-931`, should add a workflow-oriented guide beside the existing
structural tree instead of replacing or reshaping the command hierarchy.

`GBX-931` adds that guide as `glassbox command guide`. Use
`glassbox command guide --json` when docs tests or generated references need a
stable workflow map.

The command and dashboard de-emphasis inventory lives in
[v9-command-surface-review.md](./v9-command-surface-review.md).

## Dashboard Copy Review

Dashboard copy should keep the same nouns and priority model:

- Queue names should describe operator attention: approvals, questions,
  active work, failed work, degraded projections, and historical sessions.
- Action labels should name the decision object: "Approve action", "Deny
  action", "Answer question", "Cancel turn", "Continue task", "Retry job", and
  "Inspect evidence".
- Blocked reasons should include the object and next action, for example
  "task blocked by pending approval" or "session waiting for operator answer".
- Budget posture should use "autonomy budget", "remaining steps", "exhausted",
  and "stop reason" rather than generic quota language.
- Evidence panes should distinguish blocking deterministic evidence from
  advisory provider or drift cues.
- Projection warnings should say that projections are rebuildable and canonical
  events remain authoritative when that is true.

The `GBX-930` review did not require dashboard text changes. The later cockpit
tasks should use this section as the copy contract when changing queue,
attention-summary, recovery, provider, and evidence labels.

## Compatibility Policy

Command and label changes after v9 should follow these rules:

- Prefer clearer help text, docs grouping, and workflow discovery before
  renaming commands.
- Keep existing commands and JSON fields stable unless a task defines a
  migration or alias policy.
- When a rename is necessary, add the new name first, keep the old name as a
  documented alias for at least one minor release, and test both paths.
- Do not rename persisted event types, projection fields, or release evidence
  schema keys as a copy-only cleanup.
- Dashboard label changes may be made without backend aliases when they do not
  alter route names, JSON fields, or persisted state.
- Release-only or maintenance commands should be de-emphasized through command
  guide grouping and docs placement, not removed from the command tree.

## Related Guides

- [operator-quickstart.md](./operator-quickstart.md)
- [daily-workflow-quickstart.md](./daily-workflow-quickstart.md)
- [interactive-workflows.md](./interactive-workflows.md)
- [task-plans.md](./task-plans.md)
- [verification-loops.md](./verification-loops.md)
- [workspace-memory.md](./workspace-memory.md)
- [branching.md](./branching.md)
- [providers.md](./providers.md)
- [persistent-runtime.md](./persistent-runtime.md)
