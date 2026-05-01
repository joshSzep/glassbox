# v10 Release Gate

The v10 release gate is the canonical automated check for the
long-running-task reliability milestone. It inherits the v9 public-baseline
release gate, then adds deterministic evidence for interruption recovery,
checkpoint and compaction provenance, resumable tool attempts, long-run cockpit
state, provider recovery posture, package readiness, and installed operation.

Run the gate from the repository root:

```sh
uv run python scripts/validate_v10_release_gate.py
```

For a non-mutating preview of the stage plan and summary shape:

```sh
uv run python scripts/validate_v10_release_gate.py --dry-run --evidence-dir .glassbox/releases/v10-gate-dry-run
```

Use `--evidence-dir` for release-candidate evidence so the retained
`summary.json`, provider-canary directory, package references, and eval output
root can be archived together. Eval artifacts are written under
`.glassbox/evals/<evidence-dir-name>/` so release evidence stays separated from
ordinary local eval runs.

## Automated Stages

The v10 gate starts with every deterministic stage from
[v9-release-gate.md](./v9-release-gate.md), including Python
format/lint/typecheck, unfiltered Python tests, frontend lint/typecheck/tests/API
generation/build, package build, package contents validation, onboarding,
provider policy command health, promoted release-candidate eval evidence, and
installed-wheel smoke.

The inherited full Python test stage runs `uv run pytest` without marker
exclusions, so it includes daemon, subprocess, timeout, TUI, slow, and
release-gate coverage. The v10 gate also runs the focused marker slice
`uv run pytest -m "daemon or subprocess or timeout or tui" -q` as a visible
process-boundary check before the v10 long-run eval stages. Contributor fast
local loops may use the inverse marker filter documented in
[tests-v10.md](./tests-v10.md), but release validation must not use that
filtered command as release authority.

The v10-specific blocking stages are:

| Stage | Evidence |
| --- | --- |
| `v10 marked process-boundary pytest suite` | daemon, subprocess, timeout, and TUI smoke boundaries are selected intentionally by marker |
| `v10 deterministic eval release report` | commit, push, and release-candidate profiles produce retained v10 sign-off evidence |
| `v10 long-run release profile` | the release-candidate profile runs with v10 long-run fixtures enabled |
| `v10 checkpoint/compaction smoke` | checkpoint recovery and context-compaction provenance fixtures replay together |
| `v10 tool-attempt recovery smoke` | partial-output, heartbeat, retry, and safe-resume tool-attempt evidence replays deterministically |
| `v10 long-run cockpit smoke` | cockpit summary and stale-verification cues remain visible in replayed evidence |
| `v10 provider recovery policy check` | provider recommendations report release posture, recovery advice, budget impact, and failure posture |

Provider recommendation command health is blocking, but live-provider outcomes
are not release authority. Live provider canaries remain advisory unless a
future task promotes a deterministic fixture-backed policy.

## Evidence Summary

The gate writes `summary.json` under the selected evidence directory. The
summary records:

- `stages`: inherited v9 blocking checks plus v10 deterministic long-run checks
- `advisory`: provider canary execution or an explicit skip reason
- `adoption_readiness`: first-run, command discovery, package, installed smoke,
  and advisory provider posture
- `long_run_readiness`: release profile, checkpoint/compaction, tool-attempt,
  and cockpit evidence
- `release_authority`: deterministic eval report, long-run profile, coverage
  audit, package contents, and installed smoke evidence
- `artifacts`: retained eval, provider, packaging, v9 baseline, v10 contract,
  cockpit, compaction, tool-attempt, eval, and task-graph references

Every skipped stage or advisory path must carry an explicit `reason`. The
default provider-canary skip is intentional because v10 readiness is blocked by
repository-owned deterministic evidence, not credentials that may be absent on
a release machine.

## Pass And Fail Policy

- Any failed blocking stage fails the v10 release gate.
- Missing package contents, stale generated API files, or missing dashboard
  static assets fail through inherited package and frontend stages.
- Long-run readiness is blocked by deterministic replay/eval evidence for
  recovery boundaries, compaction provenance, partial retry, stale
  verification, and cockpit summaries.
- Provider recovery recommendation output must be generated successfully, but
  provider advice and provider canaries remain advisory.
- Manual dogfooding evidence, accessibility pairings, and final residual-risk
  acceptance are completed after the automated gate, not hidden inside it.
