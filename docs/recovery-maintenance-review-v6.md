# v6 Recovery And Maintenance Review

This review records the `GBX-693` recovery and maintenance evidence for the v6
release-candidate track. It uses temporary workspaces for destructive or
stateful operations and follows the manual evidence convention in
[manual-qa-evidence-v6.md](./manual-qa-evidence-v6.md).

## Review Scope

Reviewed operator workflows:

| Workflow | Evidence |
| --- | --- |
| `observability status` | focused command smoke; `test_observability_status.py` |
| `projection check --all` | focused command smoke; projection integration tests |
| `projection rebuild --all` | focused command smoke; projection integration tests |
| `artifacts inspect` | focused command smoke; artifact integration tests |
| `artifacts prune --dry-run` | focused command smoke; artifact GC tests |
| `backup create` | focused command smoke; workspace backup tests |
| `backup inspect` | focused command smoke; workspace backup tests |
| `backup restore` | focused command smoke in temporary restore workspace; workspace backup tests |
| `eval run smoke.hello` | focused command smoke; eval CLI tests |
| `eval report commit-smoke` | focused command smoke; eval CLI tests |
| daemon stale-owner and lifecycle behavior | daemon integration tests; `daemon status` command smoke |
| installed dashboard smoke | v6 installed-dashboard static route helper against the built wheel |

## Validation Run

Focused integration suite:

```bash
uv run pytest \
  tests/integration/test_observability_status.py \
  tests/integration/test_projection_rebuild.py \
  tests/integration/test_runtime_metrics_projection.py \
  tests/integration/test_artifact_gc.py \
  tests/integration/test_artifact_store.py \
  tests/integration/test_workspace_backup.py \
  tests/integration/test_cli_replay_commands.py \
  tests/integration/test_cli_eval_commands.py \
  tests/integration/test_daemon_runtime.py \
  tests/integration/test_web_spa_static.py
```

Result: `91 passed`.

Operator command smoke:

```bash
uv run glassbox observability status --cwd "$tmpdir" --json
uv run glassbox projection check --cwd "$tmpdir" --all
uv run glassbox projection rebuild --cwd "$tmpdir" --all
uv run glassbox artifacts inspect --cwd "$tmpdir" --json
uv run glassbox artifacts prune --cwd "$tmpdir" --dry-run --json
uv run glassbox backup create "$archive" --cwd "$tmpdir" --json
uv run glassbox backup inspect "$archive" --cwd "$tmpdir" --json
uv run glassbox backup restore "$archive" --cwd "$restore_dir" --json
uv run glassbox daemon status --cwd "$tmpdir" --json
uv run glassbox eval run smoke.hello --cwd . --json
uv run glassbox eval report commit-smoke --cwd . --json
```

Result: command smoke passed in temporary workspaces.

Installed dashboard smoke:

- Wheel: `dist/glassbox-0.1.0-py3-none-any.whl`
- Check: installed `glassbox dashboard serve` responded on `/`, `/app`, and a
  referenced `_next` static asset.
- Result: passed.

## Next-Action Review

The reviewed command surfaces return structured JSON where requested and keep
mutating recovery operations explicit:

- `projection check` is read-only; `projection rebuild` is the explicit repair
  action. Projection health output includes estimated rebuild event scope and
  projected progress so large-session repair cost is visible before rebuilding.
- `artifacts inspect` is read-only; `artifacts prune --dry-run` reports cleanup
  without deleting files. Both commands summarize retention classes, artifact
  age, reclaimable bytes, and `.glassbox` storage pressure before any mutation.
- `backup restore` was validated only in a temporary workspace.
- `daemon status` is safe before attempting daemon lifecycle recovery.
- Eval report failures remain release evidence rather than silent success.

## Follow-Up Issues

No blocking recovery or maintenance issue was found in this pass. Future release
candidates should attach redacted command transcripts under the v6 evidence
directory when a recovery command fails or produces operator guidance that needs
human review.
