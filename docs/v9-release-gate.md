# v9 Release Gate

The v9 release gate is the canonical automated release-candidate check for the
public-baseline line. It reuses the v8 auditable-autonomy gate, then adds
v9-specific onboarding, command-discovery, provider-evidence, promoted eval, and
package-readiness evidence.

Run the gate from the repository root:

```sh
uv run python scripts/validate_v9_release_gate.py
```

For a non-mutating preview of the stage plan and summary shape:

```sh
uv run python scripts/validate_v9_release_gate.py --dry-run --evidence-dir .glassbox/releases/v9-gate-dry-run
```

## Automated Stages

The v9 gate starts with every deterministic stage from
[v8-release-gate.md](./v8-release-gate.md), including Python
format/lint/typecheck, Python tests, frontend lint/typecheck/tests/API
generation/build, package build, package contents validation, deterministic
evals, v8 autonomy evidence, background-job smoke, memory/index/task/branch
smoke, observability, advisory provider-canary handling, and installed-wheel
smoke.

The v9-specific blocking stages are:

| Stage | Evidence |
| --- | --- |
| `v9 first-run readiness smoke` | `glassbox readiness check --json --cwd .` proves onboarding checks run and report next actions |
| `v9 command discovery smoke` | `glassbox command guide --json` proves workflow-oriented command discovery is available |
| `v9 provider evidence policy check` | retained provider-canary evidence is readable with freshness state and redacted identity |
| `v9 provider recommendation release fit` | provider recommendation reports release-candidate fit, risk, freshness, credential readiness, and unknowns |
| `v9 promoted autonomy release profile` | the blocking `release-candidate` profile runs with promoted stable autonomy cases |
| `v9 deterministic eval release report` | commit, push, and release-candidate profiles produce retained sign-off evidence |

Installed-wheel smoke is inherited from the shared packaging matrix and now
covers `readiness check`, `command guide --json`, provider diagnostics,
dashboard static routes, and `eval profile show release-candidate`.

## Evidence Summary

The gate writes `summary.json` under the selected evidence directory. The
summary records:

- `stages`: blocking deterministic, package, frontend, onboarding, cockpit-era,
  and installed-smoke checks
- `advisory`: provider canary execution or an explicit skip reason
- `adoption_readiness`: first-run, command discovery, package, and installed
  smoke evidence
- `release_authority`: deterministic eval report, promoted autonomy profile,
  and coverage audit evidence
- `artifacts`: retained eval, provider, packaging, v9 baseline, cockpit,
  dogfooding, and task-graph references

Provider canaries remain advisory by default. Skipping them does not block the
gate, and running them does not replace deterministic replay/eval release
authority.

## Pass And Fail Policy

- Any failed blocking stage fails the v9 release gate.
- Missing package contents, stale generated API files, or missing dashboard
  static assets fail through inherited package and frontend stages.
- First-run readiness smoke must execute successfully; warnings such as missing
  live-provider credentials remain acceptable when they include next actions.
- Provider evidence policy and recommendation stages are blocking for command
  health and freshness reporting, but their provider advice remains advisory.
- Provider-canary skips and failures remain non-blocking unless a later task
  explicitly promotes a live-provider scenario with a repeatable failure policy.
- Manual evidence, accessibility pairings, and final residual-risk acceptance
  are completed in `GBX-992` and `GBX-993`, not hidden inside the automated
  gate.
