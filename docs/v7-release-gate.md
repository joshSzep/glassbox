# v7 Release Gate

The v7 release gate is the canonical automated release-candidate check for the v7 line. It reuses the v6 deterministic, frontend, package, and installed-wheel coverage, then adds v7-specific eval, scale, provider-onboarding, dashboard evidence, package evidence, and manual-evidence pointers.

Run it from the repository root:

```bash
uv run python scripts/validate_v7_release_gate.py
```

Preview the command plan and write a dry-run summary without executing stages:

```bash
uv run python scripts/validate_v7_release_gate.py --dry-run
```

Retain evidence under an explicit release directory when preparing a candidate:

```bash
uv run python scripts/validate_v7_release_gate.py \
  --evidence-dir .glassbox/releases/YYYYMMDDTHHMMSSZ-v7-gate
```

## Automated Stages

The v7 gate starts with every deterministic stage from [v6-release-gate.md](./v6-release-gate.md), including Python format/lint/typecheck, focused cancellation/transport/TUI/dashboard suites, full Python tests, deterministic eval smoke, frontend lint/typecheck/tests/API generation/build, static asset validation, package build, and package contents validation.

Additional v7 stages:

| Stage                                   | Evidence                                                                                            |
| --------------------------------------- | --------------------------------------------------------------------------------------------------- |
| `v7 deterministic eval release profile` | runs the blocking `release-candidate` eval profile                                                  |
| `v7 workflow advisory eval profile`     | runs the v7 dashboard, daemon-adjacent, and cancellation advisory profile                           |
| `v7 scale performance budgets`          | prints the repository-owned larger-session performance budgets                                      |
| `v7 provider diagnostics onboarding`    | verifies redacted first-run provider diagnostics and onboarding JSON output                         |
| `v7 dashboard evidence cue tests`       | runs focused verification-cue tests for dashboard evidence interpretation                           |
| `v7 release evidence docs`              | reruns package content validation so source-builder and release-evidence docs are present in sdists |

After deterministic stages pass, the gate runs the installed-wheel smoke inherited from the hardened v6 gate. That smoke includes root help, command tree, chat/attach help, explicit plain fallback, first-run provider diagnostics, profile-example diagnostics, daemon status/start/stop, eval profile listing, deterministic eval smoke, and installed dashboard static routes.

## Provider Canaries

Provider-canary evidence remains advisory. The default gate records a skipped advisory entry so reviewers can see that live-provider canaries were not silently treated as passed.

Use this only in a credentialed release environment:

```bash
uv run python scripts/validate_v7_release_gate.py --include-provider-canaries
```

When enabled, the gate writes provider-canary evidence under `provider-canary/` inside the selected evidence directory. A provider-canary command failure is recorded in the advisory section with `blocking=false`; deterministic replay/eval and package stages remain the release authority.

## Evidence Summary

Every run writes:

```text
.glassbox/releases/YYYYMMDDTHHMMSSZ-v7-gate/summary.json
```

The summary records:

- gate name: `v7-release`
- stage command, status, exit code, start time, and end time
- advisory provider-canary status or skip reason
- built wheel path when installed smoke runs
- manual evidence hints for [manual-qa-evidence-v7.md](./manual-qa-evidence-v7.md), [terminal-accessibility-review-v7.md](./terminal-accessibility-review-v7.md), and [dashboard-accessibility-review-v7.md](./dashboard-accessibility-review-v7.md)

## Pass And Fail Policy

- Deterministic stage failure blocks the release candidate.
- Package build, package content validation, static asset validation, and installed-wheel smoke failure block the release candidate.
- Provider-canary skips do not block.
- Provider-canary failures are advisory by default unless the release owner explicitly promotes a specific live-provider finding to a blocker.
- Manual accessibility, dashboard, terminal, onboarding, packaging, provider, or residual-risk findings recorded through [manual-qa-evidence-v7.md](./manual-qa-evidence-v7.md) can block the release decision even when the automated gate passes.

## Relationship To v6

The v7 script intentionally imports the v6 stage list and installed-wheel smoke helpers instead of duplicating subprocess behavior. The v7 additions are the release-profile eval, v7 workflow advisory eval, performance budget check, provider diagnostics onboarding check, dashboard evidence cue test, v7 evidence summary shape, and advisory provider-canary retention path.
