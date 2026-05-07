# Review Responses And Fixups

Review responses are local evidence that explains how an operator handled
review feedback. A response can cite workspace edits, task work, verification,
manual notes, branch candidates, worktrees, or accepted risk, but it does not
prove that a reviewer accepted the answer.

This contract defines the response and fixup model carried from v13 into v14
maturity work. v14 makes response-linked fixup inventory easier to record and
inspect, but that inventory remains local evidence rather than reviewer
approval or acceptance.

## Lifecycle States

Use these states for response evidence and dashboard copy:

- `planned`: the operator intends to respond, but no fixup or answer evidence
  is attached yet
- `in_progress`: response work has started and may cite a session turn, task
  step, branch candidate, worktree, manual edit, or operator note
- `responded`: response evidence exists, but Glassbox is not claiming local
  resolution or reviewer acceptance
- `resolved`: the operator marks the feedback resolved locally with retained
  response evidence
- `reopened`: newer evidence, reviewer input, workspace edits, or stale
  verification made the previous response insufficient
- `blocked`: the operator cannot respond yet because required evidence,
  context, permission, dependency, or verification is missing
- `accepted-with-risk`: the operator records an explicit residual-risk path
  instead of claiming the feedback was fully fixed
- `not-applicable`: the feedback no longer applies because the scoped change,
  file, candidate, task, or requirement was superseded

These states are evidence posture. They are not remote review states, not pull
request review decisions, and not approval.

## Fixup Source Model

A response may cite one or more fixup sources. Each source should name
provenance, scope, and limitations without retaining raw diffs unless a later
task deliberately extends the redacted artifact contract.

| Source | What it can prove | Required boundaries |
| --- | --- | --- |
| Session turn | A Glassbox turn produced an answer, edit, command, or artifact. | Cite turn ID and summary; do not imply every workspace edit came from that turn. |
| Task step | A planned task step was completed, blocked, or changed. | Cite task and step state; task progress is not a full review response by itself. |
| Manual workspace edit | The operator says local files changed outside retained tool instrumentation. | Label as manual; require refreshed inventory before treating verification as current. |
| Branch-search candidate | A selected or rejected candidate contributed comparison or fixup evidence. | Preserve candidate non-merge boundaries; adoption does not merge, commit, push, or open a PR. |
| Worktree | A temporary local worktree contained isolated fixup work or evidence. | Record custody and cleanup posture; do not imply parent workspace mutation unless recorded separately. |
| Operator note | The operator supplied context, rationale, or decision text. | Say "operator says" unless corroborated by retained command, inventory, artifact, or verification evidence. |
| Verification record | A retained task verification or eval supports the response. | Name freshness, command, artifact, and whether the check is stale, failed, skipped, or accepted with risk. |
| Manual evidence | External command output, screenshot, observation, sanitized log, or reviewer note supports the response. | Label as manual or external; never backfill it as Glassbox-run command evidence. |

Response summaries should use provenance-aware language:

- "evidence indicates" when retained Glassbox evidence supports the statement
- "operator says" when the source is manual, external, or not directly
  instrumented
- "response cites" when the record links to evidence without proving the
  underlying claim
- "resolved locally" only when a retained local disposition supports it
- "accepted with risk" only when the operator records residual risk and reason

Avoid these claims:

- "review approved"
- "reviewer accepted"
- "PR requested changes resolved"
- "verified" without fresh retained verification evidence
- "fixed" when only an operator note or manual observation exists

## Response-Linked Fixup Inventory Rules

Response-linked fixup inventory answers a narrow operator question: "which
changed paths appear to respond to this feedback?" The contract for that
inventory is:

- use the existing changeset inventory artifact as the baseline where possible
- record response-linked inventory as bounded path summaries, not raw diff
  bodies
- separate code, tests, docs, generated files, config, lockfiles, and
  policy-sensitive paths in summaries
- keep file-level links between feedback scopes, changed paths, inventory
  artifact IDs, and freshness state
- mark generated outputs and lockfiles explicitly so reviewers can inspect
  source changes first
- preserve redaction rules for paths, artifacts, provider output, local state,
  and logs

A response-linked fixup inventory can support "what changed after feedback."
It cannot prove why every change was made unless source evidence links each
path to a turn, task step, manual note, candidate, worktree, or artifact.

The GBX-1321 implementation records response-linked inventory as a local
artifact with kind `review_feedback_fixup_inventory`. The artifact stores
bounded path rows, changed-path counts, feedback-scope matches, source kind,
source summary, source digest, limitations, and non-claims. Projection tables
retain the artifact reference and file-level rows so later CLI, API, and
dashboard surfaces can answer which files appear to respond to feedback.

The GBX-1322 implementation derives review-response status from feedback
disposition, latest response-linked inventory, current inventory freshness,
bounded path summaries, and accepted-risk posture. `glassbox changeset show`
now includes response counts and blockers, and
`glassbox changeset feedback status CHANGESET_ID --cwd .` gives a focused
terminal view of open, responded, unresolved, stale, blocked, and
accepted-risk feedback. API changeset detail and feedback list/detail responses
expose the same summary for dashboard use. The dashboard shows this as a dense
response timeline beside each feedback row.

These surfaces remain read-only status views. Recording feedback disposition
and response-linked inventory remains explicit operator action, and response
status is not folded into commit readiness until publication-boundary tasks
define that relationship.

## GBX-1420 Operator UX Contract

The v14 operator path for response-linked fixup inventory must stay under the
`glassbox changeset feedback` family. It should make one workflow obvious:
inspect feedback, record bounded changed-path evidence, rerun or cite local
verification, then decide whether the feedback is resolved locally or accepted
with risk. None of those steps stage, commit, push, open a pull request, merge,
deploy, publish, or claim reviewer approval.

### CLI Contract

`GBX-1421` adds a focused fixup action with this shape:

```bash
glassbox changeset feedback fixup FEEDBACK_ID --from-workspace --cwd .
glassbox changeset feedback fixup FEEDBACK_ID --from-latest-inventory --cwd .
glassbox changeset feedback fixup FEEDBACK_ID --path src/app.py --path tests/test_app.py --cwd .
```

The command records fixup inventory for one feedback record after validating
that the feedback belongs to the changeset being inspected. It should also
support a changeset-scoped bulk mode for eligible feedback when the operator
asks explicitly:

```bash
glassbox changeset feedback fixup --changeset CHANGESET_ID --all-eligible --from-workspace --cwd .
```

The command response must include the feedback ID, changeset ID, artifact ID,
source kind, changed-path count, matched feedback-scope path count, stale
posture, safe next actions, and non-claims. JSON output should expose the same
fields plus bounded path rows; human output should stay compact and name the
next safe inspection command. The command must reject ambiguous ownership,
unknown feedback IDs, empty path input, and bulk mode without an explicit
`--all-eligible` flag.

### API And Dashboard Inspection Contract

API and dashboard read surfaces should continue to expose response-linked
inventory through response status fields: `fixup_inventory_count`,
`latest_fixup_inventory_artifact_id`, `latest_fixup_inventory_sequence`,
`latest_fixup_inventory_at`, verification state, blockers, stale reason, safe
next actions, and non-claims. Dashboard feedback rows should show whether
inventory is missing, attached, stale, mismatched, failed, skipped, accepted
with risk, or ready for handoff, and should link back to the feedback detail
and changeset verification plan before offering any mutation.

If dashboard mutation is added in `GBX-1422`, the route should mirror the CLI
contract rather than inventing a separate model. The minimum write shape is a
single-feedback action equivalent to "record bounded fixup inventory for this
feedback from current workspace or explicit paths." A changeset-wide dashboard
action must require explicit confirmation and show the eligible feedback count
before recording anything.

### Error And Safe-Next-Action Language

Use cautious, inspect-first language for missing or stale evidence:

- Missing inventory: "feedback has no response-linked fixup inventory yet";
  safe next action: inspect feedback status, inspect the changeset, then record
  bounded fixup inventory if the workspace changes are intended.
- Stale inventory: "workspace diff source digest changed since fixup inventory
  was recorded"; safe next action: refresh or rerecord fixup inventory and
  rerun the named local verification command.
- Mismatched inventory: "fixup inventory has no path records matching feedback
  scope"; safe next action: inspect feedback scopes and attach explicit paths
  or accepted-risk rationale.
- Missing verification: "feedback has no response-linked fixup inventory to
  verify" or "no retained verification check targets response-linked fixup
  paths"; safe next action: preview the changeset verification plan and run a
  local check before handoff.
- Accepted risk: "operator accepted residual risk; this is not reviewer
  approval"; safe next action: inspect risk summary before publication.

Safe next actions should prefer:

```bash
glassbox changeset feedback status CHANGESET_ID --cwd .
glassbox changeset feedback show FEEDBACK_ID --cwd .
glassbox changeset show CHANGESET_ID --cwd .
glassbox changeset verification-plan CHANGESET_ID --cwd .
```

## Stale Verification Rules

Each response status now includes a response-level verification state:
`passed`, `stale`, `missing`, `failed`, `skipped`, `accepted_with_risk`,
`planned`, `running`, or `not_applicable`. Glassbox derives that state from the
latest response-linked fixup inventory, current inventory freshness, and the
task verification ledger when the changeset is task-backed.

Verification becomes stale for a response when any of these are true:

- response-linked inventory changes after the latest retained verification
  sequence
- the current workspace digest differs from the inventory digest cited by the
  response
- a feedback scope touches a path not covered by the retained verification
  plan
- a manual workspace edit is cited without a subsequent inventory refresh
- a generated output or lockfile changes after the verification evidence
- a failed or skipped check remains attached to the scoped feedback
- the operator accepts risk instead of rerunning a relevant check

When path mapping is unavailable, Glassbox marks response verification as
missing or not applicable instead of inventing staleness. The response row says
which mapping is absent and points back to the changeset verification plan.

When verification is stale, Glassbox surfaces safe inspection before mutation:

```bash
glassbox changeset feedback show FEEDBACK_ID --cwd .
glassbox changeset show CHANGESET_ID --cwd .
glassbox changeset verification-plan CHANGESET_ID --cwd .
```

When a retained check is known and stale, the response row names the exact
local check to rerun and why, for example that the check predates
response-linked fixups. Glassbox should recommend verification commands only as
inspection or local checks. It should not recommend publish, deploy, push,
upload, merge, or release commands as response verification.

The changeset verification-plan preview also includes a review-loop summary.
That summary counts feedback, response states, stale response checks, missing
response verification, manual evidence, browser/dashboard evidence,
accessibility notes, and topology impacts beside the retained verification
requirements. Manual, browser, and accessibility evidence can influence which
local check the operator chooses, but the plan labels that evidence as context
instead of retained verification proof.

## Response Records And Feedback Dispositions

Feedback dispositions from [review-feedback.md](./review-feedback.md) remain
the current implemented surface. Response records will extend that model:

- feedback `open` pairs naturally with response `planned`, `in_progress`, or
  `blocked`
- feedback `responded` should cite response evidence but avoid local
  resolution claims
- feedback `resolved_locally` should cite the response, inventory, and
  verification posture that support local resolution
- feedback `accepted_with_risk` should cite residual risk and the reason the
  operator chose not to fully fix or verify the item
- feedback `archived` should cite replacement feedback or not-applicable
  response evidence when available

If response state and feedback disposition disagree, surfaces should show the
more cautious posture. For example, a resolved feedback item with stale
response verification should surface as needing inspection before handoff.

## Fixture Design For Evals

The v13 response lifecycle eval fixtures should cover compact deterministic
cases rather than live review systems:

- requested change with response-linked inventory and fresh verification
- reviewer question answered with retained artifact evidence but no reviewer
  acceptance claim
- manual workspace edit that makes previously passing verification stale
- branch-search candidate response that preserves non-merge boundaries
- worktree-sourced fixup with cleanup posture and parent workspace limitation
- accepted-with-risk response that keeps blockers and non-claims visible
- reopened feedback after a later inventory refresh changes scoped paths
- not-applicable response after a scoped file or candidate is superseded

Each fixture should assert:

- response state and feedback disposition are distinct fields
- summaries include provenance-aware language
- stale verification is explained with safe next inspection commands
- manual evidence is labeled manual
- lifecycle briefs and exports do not claim approval, commit, push, PR, merge,
  deploy, or publication

## Non-Claims

Review responses do not mean:

- a reviewer saw the response
- a reviewer accepted the response
- a pull request is approved
- verification is current unless fresh retained evidence says so
- all manual edits were captured by Glassbox
- the changeset is committed, pushed, merged, deployed, or published

Glassbox can prepare evidence. Final operator action remains explicit and
outside the response evidence model.
