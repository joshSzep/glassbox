# Daily Workflow Quickstart

This guide is the ordinary Glassbox loop after install. It assumes you already
ran the setup path in [operator-quickstart.md](./operator-quickstart.md) and want
copy-pasteable commands for daily local work.

## Start Work

Check readiness and start chat from the repository you want Glassbox to work in:

```bash
uv run glassbox readiness check --cwd .
uv run glassbox session chat --cwd .
```

When you know the workflow but not the exact command, use the workflow guide:

```bash
uv run glassbox command guide
uv run glassbox command guide --json
```

The guide is organized around daily paths: long-run recovery, compaction, tool
attempts, checkpoint inspection, verification recommendations, provider
posture, knowledge freshness, branch-search review, workspace recovery, and
release evidence. It is intentionally workflow-oriented; use
`uv run glassbox command tree` when you need the exhaustive structural command
surface.

For a focused first request:

```bash
uv run glassbox session chat "Inspect the current change and suggest verification." --cwd .
```

Use `--plain` for line mode, or `--no-dashboard` when you need terminal-only
operation:

```bash
uv run glassbox session chat --plain --cwd .
uv run glassbox session chat --no-dashboard --cwd .
```

## Choose Autonomy

Start conservatively and widen only when the task needs it:

```bash
uv run glassbox session chat --autonomy-mode manual --cwd .
uv run glassbox session chat --autonomy-mode inspect --cwd .
uv run glassbox session chat --autonomy-mode edit-safe --cwd .
uv run glassbox session chat --autonomy-mode test-driven --cwd .
```

- `manual`: converse, inspect, and approve actions explicitly.
- `inspect`: prefer read-only investigation and planning.
- `edit-safe`: allow bounded local edits under policy and budget.
- `test-driven`: favor verification-heavy work with stricter test feedback.

Provider-backed autonomy remains advisory. Check posture before longer work:

```bash
uv run glassbox provider diagnostics --cwd .
uv run glassbox provider recommend --task-kind coding --autonomy-mode test-driven --cwd .
```

## Inspect The Dashboard

`session chat` prints a local dashboard URL:

```text
http://127.0.0.1:8765/?session=SESSION_ID
```

Use it to inspect transcript state, pending approvals, questions, task plans,
evidence, memory, repository index posture, branch-search results, and recovery
cues. If you started without the co-hosted dashboard, run:

```bash
uv run glassbox dashboard serve --cwd .
```

## Approve, Deny, Or Answer

Use the terminal UI when it is active. For scriptable control, copy identifiers
from `session status` or the dashboard:

```bash
uv run glassbox session status SESSION_ID --cwd .
uv run glassbox session answer SESSION_ID QUESTION_ID "Use the smaller scope." --cwd .
uv run glassbox session approve SESSION_ID APPROVAL_ID --cwd .
uv run glassbox session deny SESSION_ID APPROVAL_ID --cwd .
```

Approvals, denials, and answers are persisted as session evidence.

## Cancel Or Continue

Cancel an active turn when the scope is wrong or the run is no longer useful:

```bash
uv run glassbox session cancel SESSION_ID --cwd .
```

Continue an existing session with a new prompt:

```bash
uv run glassbox session message SESSION_ID "Continue with the smaller plan." --cwd .
```

For durable task plans, inspect and continue through the task surface:

```bash
uv run glassbox task list --cwd .
uv run glassbox task show TASK_ID --cwd .
uv run glassbox task continue TASK_ID --cwd .
```

## Fork Or Compare Work

Fork a historical session when you want a safe alternate path:

```bash
uv run glassbox session fork SESSION_ID --label "smaller-fix" --cwd .
```

For bounded branch exploration:

```bash
uv run glassbox branch-search list --cwd .
uv run glassbox branch-search show BRANCH_SEARCH_ID --cwd .
```

## Verify Work

Ask for the smallest useful verification plan:

```bash
uv run glassbox eval recommend PATH --cwd .
```

Run ordinary local checks:

```bash
uv run pytest tests/unit/test_specific_module.py
uv run ruff check src/glassbox/path.py tests/path_test.py
uv run glassbox eval run --profile commit-smoke --cwd .
```

For release-style evidence, use:

```bash
uv run glassbox eval audit --cwd .
uv run glassbox eval report commit-smoke push-confirmation release-candidate --cwd .
```

## Use Memory And Repository Index

Review memory candidates before promoting them:

```bash
uv run glassbox memory candidates --session SESSION_ID --cwd .
uv run glassbox memory capture MEMORY_CANDIDATE_ID --session SESSION_ID --cwd .
uv run glassbox memory list --cwd .
```

Refresh repository intelligence when the dashboard or readiness check reports a
missing or stale index:

```bash
uv run glassbox repo index status --cwd .
uv run glassbox repo index build --cwd .
uv run glassbox repo index search "verification" --cwd .
```

## Recover Local State

Start with read-only status commands:

```bash
uv run glassbox observability status --cwd .
uv run glassbox daemon status --cwd .
uv run glassbox job list --cwd .
uv run glassbox artifacts inspect --cwd .
uv run glassbox projection check --all --cwd .
```

`session status`, `task show`, and `observability status` print a safe workflow
summary for related inspection commands. Treat those summaries as launch pads:
read checkpoint, compaction, tool-attempt, verification, provider, projection,
artifact, index, and backup posture first, then run any mutating recovery
command deliberately.

For long-running work, inspect the latest checkpoint and any resumable tool
attempts before mutating recovery state:

```bash
uv run glassbox session status SESSION_ID --cwd .
uv run glassbox task show TASK_ID --cwd .
uv run glassbox session compactions SESSION_ID --cwd .
uv run glassbox session tool-attempts SESSION_ID --cwd .
```

When a compaction, tool attempt, or branch-search candidate needs an action,
the workflow guide names the safe inspection command first and the mutating
command second.

Then choose the narrowest recovery action:

- stale daemon: inspect `glassbox daemon status --cwd .`, then stop and start
  only when the status output says the owner is stale or unhealthy
- stale index: run `glassbox repo index build --cwd .`
- failed eval: rerun the named profile, then inspect `glassbox eval report`
- missing provider: run `glassbox provider diagnostics --cwd .`
- projection degradation: run `glassbox projection check --all --cwd .` before
  `glassbox projection rebuild --all --cwd .`
- artifact pressure: inspect first, then use the documented dry-run prune path
  (`glassbox artifacts prune --dry-run --cwd .`) before any non-dry-run cleanup
  in [release-packaging.md](./release-packaging.md) and
  [replay-evals.md](./replay-evals.md)

## Deeper References

- [interactive-workflows.md](./interactive-workflows.md)
- [dashboard.md](./dashboard.md)
- [task-plans.md](./task-plans.md)
- [workspace-memory.md](./workspace-memory.md)
- [repository-intelligence-index.md](./repository-intelligence-index.md)
- [verification-loops.md](./verification-loops.md)
- [background-jobs.md](./background-jobs.md)
- [replay-evals.md](./replay-evals.md)
