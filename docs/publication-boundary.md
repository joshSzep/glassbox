# Publication Boundary

Glassbox publication-boundary posture explains where a reviewed local changeset
stands before any final git, remote collaboration, deployment, or package
publication action. It is advisory local evidence. It does not stage files,
commit, push, open a pull request, merge, rebase, force-push, deploy, or publish
packages.

Use this guide with [v13-review-loop-contract.md](./v13-review-loop-contract.md),
[review-briefs.md](./review-briefs.md),
[reviewer-evidence-bundles.md](./reviewer-evidence-bundles.md), and
[commit-readiness.md](./commit-readiness.md).

## Scope

Publication-boundary posture starts after review-loop evidence exists:

- a changeset with current inventory or an explicit stale-inventory limitation
- review feedback and response summaries when feedback exists
- manual evidence, browser/dashboard/accessibility evidence, and command
  evidence summaries when attached
- lifecycle brief and export posture when generated
- verification readiness and stale-response verification posture
- commit-preparation signals when the operator asks for commit guidance

The posture ends before final operator action. Glassbox may explain what remains
and name safe inspection commands, but the operator chooses whether to stage,
commit, push, open a pull request, merge, deploy, or publish.

## States

Publication-boundary services and surfaces should use these states:

| State | Meaning | Safe First Action |
| --- | --- | --- |
| `not-ready` | Required changeset, inventory, lifecycle, or git-boundary evidence is missing or incoherent. | Inspect `glassbox changeset show CHANGESET --cwd .`. |
| `needs-review-response` | Review feedback remains open, reopened, blocked, or only planned. | Inspect `glassbox changeset feedback list --changeset CHANGESET --cwd .`. |
| `needs-verification` | Verification is missing, failed, skipped, or required after review-loop changes. | Preview `glassbox changeset verification-plan CHANGESET --cwd .`. |
| `stale-inventory` | The changeset inventory or response-linked fixup inventory is stale against the workspace. | Refresh or inspect inventory before any final action. |
| `unresolved-risk` | Accepted or unresolved risks remain visible and need explicit operator judgment. | Inspect lifecycle brief and risk summaries. |
| `handoff-ready` | Retained evidence is coherent enough for a human handoff, with limitations named. | Review lifecycle brief or export before publication. |
| `commit-prep-ready` | Commit preparation also looks coherent, but no git mutation has occurred. | Inspect commit-prep output before staging or committing manually. |
| `publication-blocked` | A final action would be misleading because blockers remain or publication intent is outside v13. | Resolve blockers or record accepted risk before handoff. |
| `accepted-with-risk` | The operator explicitly accepts a bounded residual risk while non-claims remain visible. | Carry the accepted risk into lifecycle brief, export, and handoff notes. |

These states are local posture, not remote review status. `handoff-ready` does
not mean approved. `commit-prep-ready` does not mean committed. No state means a
pull request, merge, deploy, package upload, or release publication happened.

## Relationship To Commit Readiness

Publication-boundary posture builds on commit readiness but does not replace it.
Commit readiness answers whether the current local git boundary and retained
changeset evidence look coherent enough to prepare a commit. Publication
boundary answers whether the full review-loop evidence is coherent enough to
hand off or proceed to a final operator-controlled action.

Handoff readiness can be blocked by unresolved feedback, stale response
verification, missing lifecycle briefs, local-only evidence limitations, or
accepted risks even when the git working tree looks tidy. Commit readiness can
be blocked by unstaged or untracked ambiguity even when review feedback has been
handled locally.

## Safe Next-Action Policy

Guidance must start with inspection before mutation:

- inspect changeset detail before refreshing evidence
- inspect feedback and response status before claiming a requested change is
  handled
- preview verification before rerunning or accepting risk
- inspect lifecycle brief and export redaction reports before sharing evidence
- inspect commit preparation before staging or committing manually

Safe next actions may include `glassbox changeset show`, `glassbox changeset
feedback list`, `glassbox changeset verification-plan`, `glassbox changeset
brief`, `glassbox changeset export`, and `glassbox changeset commit-prep`.
They should not include `git add`, `git commit`, `git push`, pull-request
creation, merge, rebase, force-push, deploy, upload, or publish commands unless
the user explicitly asks for final operator commands outside the advisory
review-loop posture.

## Non-Goals

v13 publication-boundary work does not introduce:

- automatic staging
- automatic committing
- automatic pushing
- automatic pull request creation
- automatic merging
- automatic rebasing or force-pushing
- automatic deployment
- automatic package publishing
- hosted pull request authority
- review approval automation

## Non-Claims

Publication-boundary posture does not prove that every line was reviewed, every
check was run, stale evidence is safe, manual evidence is retained command
evidence, browser or accessibility evidence is deterministic release proof, or
local-only artifacts are shareable. It is a local explanation of what Glassbox
knows and what the operator still controls.
