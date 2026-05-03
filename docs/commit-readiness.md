# Changeset Commit Readiness

Commit readiness is a read-only advisory model for deciding whether a local
changeset looks ready to become a commit. It explains the current posture from
retained changeset evidence and live read-only git inspection; it does not
stage files, run `git commit`, push, or mutate repository state.

## Inputs

The model combines:

- changeset identity, objective, risk counts, task or branch-candidate links
- the latest structured change inventory and its current freshness check
- verification-plan readiness from retained evidence and recommended checks
- the latest review brief and review-readiness decision
- review-response summary counts for unresolved feedback, stale response
  verification, failed or missing response checks, and accepted risk
- attached manual evidence counts, including local-only evidence and evidence
  that needs inspection
- `git status --porcelain=v1 -b` for staged, unstaged, untracked, branch-ahead,
  and branch-behind posture
- summary-only workspace and staged diff summaries for changed-path counts,
  generated files, policy-sensitive paths, and untracked file cues

Raw diffs, file contents, command output, provider transcripts, and raw
`.glassbox` database state are not part of the commit-readiness assessment.

## States

Commit readiness uses the existing `ChangesetReadinessKind.COMMIT` and
`ChangesetReadinessState` vocabulary:

| State | Meaning |
| --- | --- |
| `ready` | Staged changes exist, the working tree has no unstaged or untracked ambiguity, inventory is fresh, verification is passing or not applicable, and the review brief is current. |
| `blocked` | Required read-only evidence, such as git status or diff summary, could not be inspected. |
| `needs_verification` | Verification is missing, planned, running, skipped, otherwise not yet passing, or review-response verification is stale or missing. |
| `needs_review` | Review evidence is missing or stale, unresolved feedback remains, manual evidence needs inspection, the branch is behind upstream, or policy-sensitive paths need explicit review. |
| `stale_inventory` | The structured change inventory is missing, stale, superseded, or cannot be trusted against the current workspace. |
| `dirty_untracked_risk` | Unstaged or untracked files make the proposed commit contents ambiguous. |
| `failed_checks` | Retained verification reports failed checks. |
| `missing_provenance` | The changeset is missing task or branch-candidate linkage, or the inventory lacks a source digest. |
| `accepted_with_risk` | No blocking condition remains, but accepted risk remains visible. |
| `not_ready` | The workspace has nothing local to commit or no staged changes are present. |

When multiple signals are present, blocking states are aggregated in severity
order. Dirty/untracked ambiguity wins over failed checks only after stale
inventory and hard evidence-inspection blockers, because commit contents must be
clear before the operator can trust the commit boundary.

## Explanation Shape

`ChangesetCommitReadinessService.preview()` returns a
`CommitReadinessAssessment` with:

- `state`, `reason`, `blockers`, and `safe_next_actions`
- local git summary fields for staged, unstaged, untracked, policy-sensitive,
  generated, branch-ahead, and branch-behind posture
- references to current inventory, review brief, and verification evidence
- review feedback, unresolved feedback, stale response, manual evidence, and
  local-only evidence counts
- per-signal explanations for inventory, verification, review, review-loop,
  manual evidence, provenance, git status, path risk, and accepted risk
- non-claims that make the boundary explicit

The safe next actions are intentionally commands to inspect, refresh, generate a
brief, or run recommended verification. They are not staging or commit actions.

## Non-Claims

Commit readiness is not proof the code is correct, not approval to commit, and
not a substitute for review. It is a local explanation of whether the retained
evidence and current git boundary look coherent enough for an operator to
prepare a commit deliberately.
