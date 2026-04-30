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

## Long-Run Ledger

For long tasks, Glassbox also rebuilds a `task_verification_ledger` projection
from the canonical verification events. The ledger is not a second source of
truth; it is the durable read model that answers what has been verified so far.

Each ledger row connects one verification ID to its task, optional step,
status, check family, selection source, command argv, changed paths, eval links,
attempt counts, latest output artifact, latest failed check, last successful
check, accepted residual risks, and the event sequence that last updated it.
`glassbox task show TASK_ID --json` and the task detail API include both the
ledger entries and a compact `verification_summary` posture such as `missing`,
`running`, `failing`, `partial`, `accepted_with_risk`, or `verified`.

Operators should use the ledger as checkpoint evidence during handoff and
resume decisions: inspect the last successful check, compare it with any later
failures or accepted risks, then run the focused commands needed to prove the
current workspace state.

## Last Known Good And Repair History

Task detail reads also derive a `last_known_good` marker from durable
verification events, the ledger projection, checkpoint history, and the current
drift assessment. The marker names the latest passed verification, source
sequence, linked artifact, changed paths, current changed-path digest, drift
posture, and the nearest checkpoint that covered or preceded the successful
proof. It is a recovery marker, not a claim that the git workspace is clean.

The `repair_history` summary compacts repeated failure and retry evidence from
`TaskVerificationFailed`, `TaskVerificationRetried`, passed reruns, and accepted
residual risks. CLI and dashboard task detail surfaces show whether the task is
clean, failed, repaired, regressed after a prior pass, still repairing, or
accepted with risk, plus the retained retry edges and latest failure summary.

## Stale Verification Drift

Task detail reads now compare the verification ledger with the current local git
diff. The `verification_drift` posture reports whether proof is `fresh`,
`stale`, missing material coverage, docs-only drift, generated-file drift,
unknown, or not assessed. Stale verification means material workspace changes
overlap paths that a previously passed check claimed to cover.

The drift assessment includes the changed paths, material paths, docs-only
paths, generated paths, stale verification IDs, stale paths, and a SHA-256
digest of the current changed-path list. Dashboard and `glassbox task show`
surfaces use this cue to warn before an operator treats old verification as
current proof. Documentation-only and generated-only drift are still visible,
but they are separated from material code drift so operators can choose a
focused follow-up instead of rerunning broad suites reflexively.

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
