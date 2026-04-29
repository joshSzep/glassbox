# Background Autonomy Release Smoke v8

GBX-845 adds a deterministic release-smoke command for the v8 background job stage.
It is intentionally credential-free and bounded: each scenario seeds an isolated
workspace, runs one worker pass, and records objective evidence under a retained
release directory.

## Command

Run the smoke from the repository root:

```bash
uv run python scripts/background_autonomy_smoke.py
```

By default the command writes evidence to:

```text
.glassbox/releases/<timestamp>/background-jobs/summary.json
```

For release gates or local reproduction, pass explicit paths:

```bash
uv run python scripts/background_autonomy_smoke.py \
  --workspace /tmp/glassbox-background-smoke \
  --evidence-dir .glassbox/releases/v8-background-smoke/background-jobs \
  --json
```

Use `--dry-run` to write the planned scenario list without mutating a workspace.

## Release-Bearing Coverage

The smoke is release-bearing for these deterministic background behaviors:

- read-only daemon job claim, heartbeat, progress, and completion
- cancellation request acknowledgement at a safe worker boundary
- read-only failure triage with retryability and retained failure artifact evidence
- explicit retry and abandon events from the event-safe queued boundary
- stale claim recovery from an expired lease
- mutating task continuation pause when no explicit autonomy budget exists

These scenarios cover the v8 background stage without requiring a provider,
network access, sleeps, or long-lived daemon processes.

## Manual Or Advisory Coverage

These behaviors remain manual or advisory until later v8 release-gate tasks wire
larger scenario suites into the final gate:

- full provider-backed background continuation that completes a real model turn
- multi-job scheduling fairness and long-running daemon loop soak
- dashboard manual inspection beyond the aggregate failed/retryable/abandoned cue
- installed-wheel coverage for the smoke command

## Release-Gate Recommendation

The v8 release gate should include a blocking stage named `v8 background job
smoke` before package publication:

```bash
uv run python scripts/background_autonomy_smoke.py \
  --evidence-dir .glassbox/releases/<candidate>/background-jobs
```

The stage should fail the gate if `summary.json` does not report `status:
passed`, if any scenario is missing, or if the failure-retry scenario does not
retain a failure artifact path.
