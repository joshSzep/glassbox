# v9 Eval Promotion Plan

This document records the `GBX-950` review of the v8 autonomy advisory eval
suite. It decides which advisory cases are stable enough to become blocking v9
release-candidate evidence, which cases should remain advisory, and which cases
need a smaller replacement contract before promotion.

Retained local review evidence:

- advisory run: `.glassbox/evals/20260430T020536Z/`
- review artifact: `.glassbox/evals/gbx-950-promotion-review.md`

## Review Inputs

The review covered the `v8-autonomy-advisory` profile in
`evals/profiles.json`:

```text
uv run glassbox eval run --profile v8-autonomy-advisory --cwd .
uv run glassbox eval audit --cwd .
```

The advisory run selected eight cases, passed all eight, and reported exact
matches for every selected case. The coverage audit reported all declared
capabilities covered.

Each v8 autonomy case currently has one baseline-history entry from the
`GBX-890` promotion pass on April 29, 2026. No refresh history is recorded for
these cases, so today's review treats the current exact-match result as a
useful stability signal, not as long-term drift proof.

## Promotion Criteria

A case can move from `v8-autonomy-advisory` into the blocking
`release-candidate` profile when the case:

- replays deterministically with exact-match expectations
- protects persisted runtime evidence rather than live provider behavior
- does not depend on daemon timing, socket timing, operator race windows, or
  local filesystem freshness
- does not use a cancelled-fixture shortcut as the behavior being promoted
- fits a release-candidate budget that remains meaningful for sign-off
- has focused unit, integration, or dashboard tests for live behavior that the
  replay bundle does not prove

When a broad case is useful but not ready to block release, the preferred next
step is to keep the broad case advisory and promote a smaller deterministic
invariant later.

## Case Classification

| Case | Classification | Reason |
| --- | --- | --- |
| `task-plan.proposal-capture` | Split before promotion | The case is exact-match and valuable, but the manifest explicitly describes a compact cancelled-turn bundle. v9 should promote a smaller task-plan projection invariant that does not rely on a cancelled-fixture shortcut. |
| `task.continuation-blocked` | Keep advisory | The case protects a bounded stop reason, but continuation remains tied to daemon/background-job behavior and live recovery semantics. Focused tests and manual evidence remain the stronger release authority until a smaller deterministic stop-contract case exists. |
| `autonomy.budget-exhaustion` | Promote to release-candidate | Budget usage, remaining limits, and exhaustion reason are typed, persisted, local, and deterministic. The case does not require provider credentials, daemon timing, or local freshness. |
| `verification.success` | Promote to release-candidate | The case protects successful verify-repair projection evidence. Actual command execution remains covered by focused verification-loop tests, while the replay invariant is stable enough to block release. |
| `verification.failure` | Promote to release-candidate | The case protects failed verification evidence and residual task failure state. It is deterministic and complements focused command-failure tests. |
| `memory.context-drift` | Keep advisory | Memory prompt-source drift depends on local workspace memory freshness and invalidation posture. Keep it visible for drift review while focused memory/context tests remain blocking. |
| `repository-index.context-drift` | Keep advisory | Repository-index prompt-source drift depends on rebuildable local file state and freshness. Keep it advisory until the index freshness workflow is stricter. |
| `branch-search.candidate-comparison` | Promote to release-candidate | The replay case protects retained candidate comparison summaries, not live branch creation or cleanup. Those live behaviors remain integration/manual evidence, but the comparison projection is stable deterministic release evidence. |

## GBX-951 Follow-Up

`GBX-951` should update `evals/profiles.json`, `evals/coverage.json`, and the
selected case manifests so the blocking `release-candidate` profile includes:

- `autonomy.budget-exhaustion`
- `verification.success`
- `verification.failure`
- `branch-search.candidate-comparison`

It should keep the commit-time and push-time smoke profiles unchanged, expand
the release-candidate budget deliberately, and leave the remaining v8 autonomy
cases in the advisory suite with their current operational value visible.

## Non-Promoted Advisory Value

The non-promoted cases are not failures. They continue to protect reviewable
signals that are useful during autonomy work:

- task-plan capture remains useful while a smaller non-cancelled projection
  case is prepared
- continuation blocked-state remains useful while daemon/job recovery evidence
  matures
- memory and repository-index context drift remain useful warning signals for
  local freshness and prompt-source behavior

Provider canaries and live-provider readiness remain outside this promotion
plan. They are operational confidence signals, not deterministic release
authority.
