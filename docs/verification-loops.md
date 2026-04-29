# Verification Loops

Glassbox verification loops are local, budgeted checks that prove or disprove a
task result with durable evidence. They cover command, test, eval, lint,
typecheck, package, and custom local checks.

## Contract

A verification plan is explicit and scriptable:

- `kind` names the check family: command, test, eval, lint, typecheck, package,
  or custom
- `command` records the exact argv that may run after policy and budget checks
- `source` explains why the check was selected: eval recommendation, workspace
  profile, changed paths, task type, policy budget, or operator input
- `blocking` separates release-bearing checks from advisory checks
- `timeout_seconds` and `expected_exit_codes` keep local runs bounded
- eval checks must link to an eval case or profile

Verification commands are command-risk tools. A plan entry can be selected by
eval recommendations, workspace profile defaults, changed paths, task type, or
operator-defined commands, but execution still pauses when policy, approval
mode, or autonomy budgets require it.

## Events

The canonical lifecycle is:

1. `TaskVerificationPlanned`
2. `TaskVerificationStarted`
3. `TaskVerificationStreamed` for compact log summaries or artifact links
4. `TaskVerificationCompleted`, `TaskVerificationFailed`, or
   `TaskVerificationSkipped`
5. `TaskVerificationRetried` when a bounded repair loop will run another check
6. `TaskVerificationResidualRiskAccepted` when an operator accepts known
   residual risk instead of requiring a passing check

Full logs should be retained as artifacts. Event payloads should carry compact
summaries and artifact IDs so replay, export, and dashboard surfaces remain
responsive.

## Failure Categories

Verification failure digests classify output as assertion, lint, typecheck,
package, policy, budget, timeout, infrastructure, flaky, or unknown. The
classifier is evidence-based: it summarizes observable output and does not infer
model intent.

## Release Posture

Commit-time verification should start with targeted tests or deterministic eval
cases. Push-time and release-candidate verification may broaden to profiles and
package checks. Live-provider canaries remain advisory unless an operator
explicitly selects them.

See [replay-evals.md](./replay-evals.md) for the eval recommendation contract
and local verification ladder.
