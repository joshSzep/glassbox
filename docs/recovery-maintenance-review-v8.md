# v8 Recovery And Maintenance Review

This review records the `GBX-891` observability and recovery pass for v8
autonomy surfaces. It is intentionally command-oriented: `observability status`
is read-only, and every recovery step points at an explicit follow-up command.

## Evidence

- Retained local evidence directory: `.glassbox/releases/gbx-891-recovery/`
- Primary smoke command:

```bash
uv run glassbox observability status --cwd . --json
```

## Reviewed States

| State | Read-only signal | Recovery guidance |
| --- | --- | --- |
| Stale daemon owner | `runtime.state=stale` | `glassbox daemon stop --cwd WORKSPACE`, then `glassbox daemon start --cwd WORKSPACE` |
| Failed or blocked task continuation | `tasks.blocked_count`, `tasks.failed_count`, `tasks.verification_failed_count` | `glassbox task show TASK_ID`; if budget allows, `glassbox task continue TASK_ID --verify-repair` |
| Budget exhaustion | `tasks.budget_exhausted_count` and task budget posture | inspect the task, adjust scope, then enqueue a smaller continuation explicitly |
| Stale jobs | `background_jobs.stale_count` | `glassbox job list --state stale`, then inspect, retry, cancel, or abandon the named job |
| Failed retryable jobs | `background_jobs.failed_count` and `retryable_count` | `glassbox job list --state failed`, `glassbox job show JOB_ID`, then `glassbox job retry JOB_ID` when appropriate |
| Memory invalidation cleanup | `memory.invalidated_count` | `glassbox memory list --state invalidated`, then `glassbox memory prune MEMORY_ID --dry-run --reason 'validated cleanup'` |
| Imported or stale memory | `memory.imported_count`, `memory.stale_count` | list the affected state, then confirm or invalidate the named memory item |
| Repository index stale or failed | `repository_index.status` | `glassbox repo index status --cwd WORKSPACE`, then `glassbox repo index build --cwd WORKSPACE` |
| Branch-search cleanup | `branch_searches.needs_review_count` or failed candidate verification | `glassbox branch-search show SEARCH_ID`, then select or reject the candidate with a reason |
| Projection rebuild | `projections.degraded_count` and rebuild event scope | `glassbox projection check --all`, then `glassbox projection rebuild --all` |

## Result

The v8 observability report now includes explicit task/autonomy, workspace
memory, repository index, and branch-search sections in both JSON and text
output. The command remains safe for scripts because it only reads runtime,
projection, artifact, eval, provider, memory, index, job, task, and
branch-search state; mutating recovery remains behind the named commands above.
