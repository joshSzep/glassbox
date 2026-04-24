# Branching And Historical Workflows

Glassbox v1 time-travel is branch creation, not destructive rewind.

- the parent session remains immutable
- the child session records explicit lineage metadata
- the child imports the transcript history it needs and then records new events in its own session log

## When To Fork

Use a fork when you want to preserve the original audit trail and explore an alternate path from a stable historical boundary.

Use the original session instead when it is still actionable and you simply want to keep working in it.

## Valid Fork Points

Fork creation is allowed only from stable completed-turn boundaries:

- the latest completed turn in a session
- an explicitly selected completed turn via `--turn TURN_ID`

Fork creation is rejected for:

- a currently running turn
- a session paused on approval
- a session paused on `ask_user`
- ambiguous or corrupted historical state

## CLI Workflow

Inspect the historical session, create a child branch, then continue in the child:

```bash
uv run glassbox status PARENT_SESSION_ID --cwd .
uv run glassbox fork PARENT_SESSION_ID --turn TURN_ID --branch-label alt-path --cwd .
uv run glassbox message CHILD_SESSION_ID "Try the alternate fix" --cwd .
```

Or create the fork and submit the first child prompt immediately:

```bash
uv run glassbox fork PARENT_SESSION_ID \
  --turn TURN_ID \
  --branch-label alt-path \
  --prompt "Try the alternate fix" \
  --cwd .
```

The fork command prints the new child session ID, the historical turn, and the inherited transcript count.

## Dashboard Workflow

Use the browser workflow when you want to inspect lineage before branching:

1. Open the session in the dashboard from the co-hosted `chat` URL or from `glassbox serve`.
2. Inspect the lineage summary and `branchable_turns`.
3. Keep the default latest completed turn or choose an older completed turn explicitly.
4. Create the fork and let the dashboard navigate into the child session.

If the dashboard cannot offer the action, treat that as a state signal rather than a UI bug. `fork_blocked_reason` should explain why the session is inspectable but not forkable yet.

## Lineage Fields

Glassbox surfaces explicit lineage metadata:

- `parent_session_id`
- `forked_from_turn_id`
- `forked_from_sequence`
- `branch_label`

The dashboard and session APIs also expose child-session summaries and branchability fields such as `can_fork`, `latest_fork_point_turn_id`, `latest_fork_point_sequence`, and `fork_blocked_reason`.

## Replay And Eval Behavior For Child Sessions

Forked child sessions are first-class replay and eval baselines.

- `glassbox replay CHILD_SESSION_ID` replays the child session with inherited transcript history intact
- `glassbox replay-export CHILD_SESSION_ID` writes a portable child bundle including lineage and imported history
- `glassbox eval run` can execute eval cases backed by forked child bundles

Lineage-aware replay diffs distinguish inherited-prefix drift from post-fork transcript drift.

## Choosing Between Live, Historical, And Child Work

- If the selected session is still actionable, keep working in it with `attach`, `message`, `answer`, or approval commands.
- If the session is historical-only, inspect it and decide whether to leave it alone or create a child branch.
- If you want to test an alternate path while preserving the original history, create a fork and continue only in the child.

## Related Guides

- [interactive-workflows.md](./interactive-workflows.md)
- [dashboard.md](./dashboard.md)
- [replay-evals.md](./replay-evals.md)
