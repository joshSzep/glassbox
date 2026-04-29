# v8 Release Gate

The v8 release gate is the canonical automated release-candidate check for the auditable-autonomy line. It reuses the v7 gate, then adds v8-specific eval, background-job, task, memory, repository-index, branch-search, observability, package, installed-wheel, and advisory provider evidence.

Run it from the repository root:

```bash
uv run python scripts/validate_v8_release_gate.py
```

Preview the command plan and write a dry-run summary:

```bash
uv run python scripts/validate_v8_release_gate.py --dry-run
```

Retain evidence under an explicit release directory when preparing a candidate:

```bash
uv run python scripts/validate_v8_release_gate.py \
  --evidence-dir .glassbox/releases/YYYYMMDDTHHMMSSZ-v8-gate
```

## Automated Stages

The v8 gate starts with every deterministic stage from [v7-release-gate.md](./v7-release-gate.md), including Python format/lint/typecheck, full Python tests, deterministic eval smoke, frontend lint/typecheck/tests/API generation/build, package build, package contents validation, v7 eval coverage, provider onboarding diagnostics, dashboard evidence cue tests, and installed-wheel smoke.

Additional v8 stages:

| Stage | Evidence |
| --- | --- |
| `v8 deterministic eval release report` | writes release sign-off evidence for commit, push, and release-candidate profiles |
| `v8 autonomy advisory eval profile` | runs deterministic advisory coverage for task plans, blocked continuation, budgets, verification, memory/index drift, and branch-search comparison |
| `v8 eval coverage audit` | confirms repository-owned capability coverage remains accounted for |
| `v8 background job smoke` | runs credential-free background autonomy scenarios and retains `background-jobs/summary.json` |
| `v8 task inspection smoke` | confirms task-plan inspection is scriptable from the checkout |
| `v8 memory smoke` | confirms workspace-memory inspection is scriptable |
| `v8 repository index smoke` | confirms repository-index status is scriptable |
| `v8 background job status smoke` | confirms background-job status is scriptable |
| `v8 branch-search smoke` | confirms branch-search inspection is scriptable |
| `v8 observability autonomy summary` | records task, job, memory, index, branch-search, provider, and recovery posture |

After deterministic stages pass, the gate records advisory provider canary evidence or an explicit skip reason, then runs the installed-wheel smoke from the built wheel.

## Evidence Summary

Every run writes:

```text
.glassbox/releases/YYYYMMDDTHHMMSSZ-v8-gate/summary.json
```

The summary records:

- gate name: `v8-release`
- stage command, status, exit code, start time, and end time
- advisory provider-canary status, planned state, failure, or skip reason
- built wheel path when installed smoke runs
- retained evidence paths for evals, background jobs, provider canaries, packaging docs, recovery review, dashboard accessibility review, and the v8 autonomy contract
- autonomy boundedness evidence split into blocking and advisory categories

## Pass And Fail Policy

- Deterministic stage failure blocks the release candidate.
- Package build, package content validation, frontend static validation, background-job smoke, source checkout CLI smoke, observability smoke, and installed-wheel smoke failure block the release candidate.
- Provider-canary skips do not block when the skip reason is retained.
- Provider-canary failures are advisory by default unless the release owner explicitly promotes a live-provider finding to a blocker.
- Manual evidence from terminal, dashboard, accessibility, recovery, package smoke, and residual-risk review can still block the release decision even when the automated gate passes.
