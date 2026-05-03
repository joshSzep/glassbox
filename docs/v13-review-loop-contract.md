# Glassbox v13 Review Loop Contract

This page defines the v13 product contract for evolving the v12 reviewable
local change lifecycle into a review-resilient local feedback loop.

v13 does not turn Glassbox into hosted code review or publication automation.
It keeps review work local and evidence-backed: feedback, requested changes,
fixup responses, manual evidence, browser checks, accessibility notes,
lifecycle briefs, accepted risks, and final handoff guidance become structured
local evidence without taking control away from the operator.

## Scope

Glassbox v13 focuses on review-resilient local changesets:

- record local review feedback against changesets, files, tasks, turns,
  artifacts, verification records, and risks
- track requested changes, reviewer questions, dispositions, reopenings,
  archival, and locally accepted risk without implying approval
- connect fixup responses to changed inventory, stale verification, evidence
  references, and remaining uncertainty
- attach manual evidence from external commands, reviewer observations, notes,
  screenshots, sanitized logs, and local walkthroughs while labeling it as
  manual rather than retained tool evidence
- retain browser, dashboard, and accessibility evidence with advisory claims,
  local-only references, skipped-case notes, and non-claims
- improve path-aware verification and stale-evidence recommendations after
  review-driven edits
- generate lifecycle review briefs and reviewer-safe evidence bundles from
  retained local evidence rather than hidden model memory
- explain handoff readiness and publication-boundary posture before any final
  operator action
- add integrated terminal, command-palette, plain interactive, and dashboard
  entry points after the review-loop model has been dogfooded
- promote stable review-loop behavior into deterministic replay, eval, and
  release-gate coverage

The primary creation surface remains `glassbox session chat`. The dashboard is
the paired review and evidence surface for inspecting feedback, responses,
manual evidence, browser and accessibility evidence, lifecycle briefs,
verification posture, risks, and handoff readiness.

## Product Model

A v13 review loop is a local evidence lifecycle around one changeset. It is not
a remote collaboration primitive, not an approval system, and not a git
publication workflow. Canonical events and managed artifacts remain the source
of truth; projections, CLI output, dashboard panels, API responses, briefs, and
exports are rebuildable views.

The supported local lifecycle is:

1. An operator creates or refreshes a local changeset from a session, task,
   branch-search candidate, worktree, or workspace diff.
2. Glassbox records review feedback and scope metadata as local evidence when
   the operator captures comments, questions, requested changes, observations,
   or risks.
3. The operator performs fixups or chooses an accepted-risk path outside any
   hidden approval automation.
4. Glassbox records fixup responses, inventory changes, manual evidence,
   verification freshness, browser or accessibility walkthroughs, and residual
   limitations as local evidence.
5. Glassbox generates lifecycle briefs and evidence bundles that cite retained
   references, label local-only material, and keep unresolved feedback visible.
6. Glassbox explains handoff readiness and safe next actions without staging,
   committing, pushing, opening a pull request, merging, deploying, or
   publishing.
7. The operator performs any final git, remote, deployment, or publication
   action deliberately outside the review-loop evidence model.

## Vocabulary

Use these terms consistently in CLI help, dashboard copy, API descriptions,
docs, tests, and release evidence.

| Term | Operator meaning | Copy boundary |
| --- | --- | --- |
| Review feedback | A local evidence record for a reviewer comment, operator note, requested change, question, observation, or risk tied to a changeset. | Do not call feedback approval. Name source labels and provenance limits. |
| Requested change | Feedback that asks for a specific local fixup or explanation before handoff. | Use only when retained feedback supports the request. |
| Reviewer question | Feedback that asks for clarification or evidence rather than a code change. | Keep questions visible until answered, accepted with risk, archived, or explicitly resolved locally. |
| Fixup response | A retained local response that explains what changed, what evidence supports it, and what uncertainty remains. | Do not claim a reviewer accepted the response unless such evidence was separately recorded. |
| Operator note | A local note recorded by the operator to explain context, judgment, or next steps. It may become feedback only when attached to a review-loop feedback record. | Do not treat every note as a requested change, risk, or verification result. |
| Task checkpoint | Continuation evidence for task progress, recovery, blockers, touched files, and next action. | Checkpoints may be cited by feedback or responses, but they are not review feedback or complete change inventory. |
| Changeset risk | A retained uncertainty, sensitive path, stale signal, failed/skipped check, missing provenance, or accepted risk attached to the changeset. | Keep risk beside readiness. Do not hide it under resolved feedback or passing checks. |
| Verification evidence | Retained evidence from explicit checks, task verification ledger records, evals, or review-relevant command attempts. | Use "verification passed" only for a specific fresh check. Manual evidence can support context but is not Glassbox-run verification evidence. |
| Manual evidence | Operator-attached evidence from outside retained Glassbox instrumentation, including external commands, observations, screenshots, sanitized logs, or notes. | Label as manual or external. Never backfill it as Glassbox-run command evidence. |
| Browser evidence | Advisory local evidence from a browser or dashboard walkthrough. | Name environment, scope, skipped cases, local-only references, and non-claims. |
| Accessibility evidence | Advisory evidence from keyboard, focus, contrast, screen-reader, or paired accessibility checks. | Distinguish covered checks from skipped or untested assistive technology. |
| Lifecycle brief | A reviewer-safe Markdown or JSON summary of the full local review loop. | Include feedback, responses, manual evidence, verification freshness, accepted risks, handoff posture, and non-claims. |
| Handoff readiness | Advisory posture describing whether retained local evidence is coherent enough for a human handoff. | Do not equate handoff-ready with committed, pushed, approved, or published. |
| Publication boundary | The line between evidence preparation and final operator-controlled git, remote, deployment, or package actions. | Safe inspection and readiness explanation come before any mutating next step. |
| Final operator action | A deliberate human action such as staging, committing, pushing, opening a PR, merging, deploying, or publishing. | Glassbox may suggest inspection or preparation, but does not perform the action automatically in v13. |

The v13 vocabulary builds on [v9-vocabulary.md](./v9-vocabulary.md) and
[v12-reviewable-change-contract.md](./v12-reviewable-change-contract.md). Keep
these distinctions clear:

- A **review feedback record** is local evidence, not a hosted review comment.
- A **fixup response** is local response evidence, not proof of reviewer
  acceptance.
- A **manual evidence item** is useful context, not retained Glassbox command
  evidence.
- A **lifecycle brief** summarizes the review loop, not approval or
  publication.
- **Handoff readiness** is advisory local posture, not a git or remote state.

## Operator Language Boundaries

The v9 vocabulary keeps Glassbox nouns stable across CLI help, dashboard copy,
operator docs, and release evidence. v13 keeps that compatibility rule and adds
review-loop boundaries for words that can otherwise overclaim.

| If you mean | Use this language | Avoid this language |
| --- | --- | --- |
| A reviewer or operator captured a comment, concern, or request. | "review feedback recorded" | "review approved", "remote comment synced" |
| Feedback asks for a concrete change before handoff. | "requested change captured" | "merge blocked", "PR requested changes" |
| A reviewer asked for context or evidence. | "reviewer question recorded" | "blocking failure" unless a failing check exists |
| The operator changed code, docs, tests, or evidence in response. | "fixup response recorded" | "reviewer accepted the fix" without acceptance evidence |
| The operator attached an external command result or note. | "manual evidence attached" | "command evidence retained" unless Glassbox ran and retained the command attempt |
| A browser or dashboard walkthrough was retained. | "browser evidence is advisory" or "dashboard evidence is advisory" | "browser validation passed" when only live walkthrough notes exist |
| Keyboard, focus, contrast, or assistive-technology notes were retained. | "accessibility evidence recorded" with covered and skipped checks | "accessible" as a blanket claim |
| A summary covers the whole feedback and response lifecycle. | "lifecycle brief generated" | "approval summary" or "PR description" |
| Local evidence looks coherent enough to hand to another human. | "handoff readiness: handoff-ready" | "published", "merged", "approved", or "ready to deploy" |
| The next action would mutate git, a remote, a deployment, or a package registry. | "final operator action" | "Glassbox will publish" or "automatic PR" |

Use these distinctions when adding command help, dashboard labels, API
descriptions, docs, tests, and eval fixtures:

- **Review feedback** is a feedback object with source, scope, disposition, and
  lifecycle state.
- **Operator note** is local context. It becomes review feedback only when a
  feedback record names it as such.
- **Task checkpoint** is continuation evidence. It may cite touched files or
  blockers, but it is not review feedback, not a fixup response, and not a full
  changeset inventory.
- **Changeset risk** is readiness evidence. It can be unresolved or accepted
  with risk, but it is not automatically resolved when feedback is answered.
- **Verification evidence** comes from explicit retained checks. Manual
  evidence may explain an external check, but should remain labeled manual
  until Glassbox records a tool attempt or deterministic verification record.

## Supported Workflow Set

v13 supports these operator workflows as the milestone is implemented:

- create, list, inspect, resolve, reopen, archive, and accept risk for local
  review feedback records
- attach feedback scope to changesets, files, line hints, tasks, turns,
  artifacts, verification records, sessions, and reviewer labels when known
- record fixup responses for requested changes and reviewer questions
- compare response evidence against changed inventory and stale verification
  posture
- attach manual evidence with source, scope, retention, redaction, local-only
  posture, and provenance limits
- capture browser, dashboard, and accessibility walkthrough evidence as
  advisory, bounded, local evidence
- refresh verification guidance after review-driven edits and explain stale,
  missing, failed, skipped, or accepted-risk checks
- generate lifecycle briefs and reviewer-safe evidence bundles from retained
  references
- calculate handoff readiness and publication-boundary posture without
  performing final mutation
- expose review-loop actions from terminal chat, command palette, plain
  interactive mode, CLI commands, API routes, and dashboard surfaces once the
  underlying evidence model exists

UX consolidation happens late in v13 after feature dogfooding. Early
implementation tasks should prefer stable CLI and API behavior; slash commands,
palette labels, dashboard shortcuts, and primary in-session verbs should be
shaped by observed review-loop friction rather than v12 assumptions.

## Evidence Expectations

v13 evidence is split into blocking deterministic release evidence and advisory
confidence evidence.

Blocking release evidence includes:

- typed event and payload tests for review-loop event families
- SQLite migration, projection rebuild, repository adapter, and query service
  tests for feedback, responses, manual evidence, browser evidence,
  accessibility evidence, lifecycle briefs, and handoff readiness
- CLI, TUI, API, dashboard, and generated-type tests when command or web
  surfaces change
- deterministic unit and integration tests for stale verification, response
  posture, accepted risks, publication-boundary states, redaction, and exports
- deterministic replay and eval fixtures promoted for stable review-loop
  behavior
- the v13 release gate once `scripts/validate_v13_release_gate.py` exists

Advisory confidence evidence includes:

- manual review walkthroughs and reviewer observations
- externally run command summaries and sanitized logs
- live browser or dashboard screenshots and notes
- accessibility pairing notes, skipped-case summaries, and environment details
- live provider evidence, provider diagnostics, and skipped-provider reasons
- operator dogfooding summaries from real local changes

Manual, live browser, dashboard, accessibility, provider, and dogfooding
evidence can strengthen confidence only when retained evidence names the
workflow, environment, date, source, skipped cases, limitations, and bounded
claim. Those evidence classes do not replace deterministic gates unless a
future task promotes a narrow fixture-backed contract with an explicit failure
policy.

## Release Authority

Deterministic replay, eval, package, migration, unit, integration, CLI, API,
frontend, and release-gate evidence are the blocking release authority for v13.

Live provider, live browser, accessibility, manual review, and dogfooding
evidence remain advisory unless a task explicitly defines a repeatable
fixture-backed contract and failure policy.

Review feedback is evidence, not approval. A resolved or responded-to feedback
record means Glassbox has retained local response evidence; it does not mean a
reviewer approved the change.

## Non-Goals

v13 deliberately does not introduce:

- hosted code review
- hosted review comment synchronization
- hosted pull request authority
- cloud workspace authority
- remote worker fleets
- simultaneous multi-writer mutation
- automatic review approval
- automatic staging
- automatic commits
- automatic pushes
- automatic pull request creation
- automatic branch-search merging
- automatic rebase, force-push, or history rewriting
- automatic deploys or package publishing
- automatic provider failover as release authority
- hidden provider-side memory
- cross-repository memory sync
- indefinite unattended mutation

Glassbox may prepare evidence, response summaries, lifecycle briefs, handoff
readiness, publication-boundary guidance, safe next commands, and reviewer-safe
exports. It must not silently perform final git, remote collaboration,
deployment, or package-publication actions as part of the v13 review loop.

## Safety Rules

- Safe inspection comes before mutation in terminal, API, and dashboard copy.
- Feedback with unresolved, reopened, archived, or accepted-risk posture remains
  visible beside readiness summaries.
- Responded feedback is not described as approved unless separate retained
  evidence supports that word.
- Manual evidence is labeled manual or external and never represented as
  retained Glassbox command evidence.
- Browser, dashboard, accessibility, provider, and dogfooding evidence names
  bounded claims and non-claims.
- Large or sensitive data lives in managed artifacts with redaction and size
  limits; canonical events should carry identifiers, summaries, provenance, and
  scope metadata rather than raw diffs, raw screenshots, or raw logs.
- Reviewer-facing exports avoid raw `.glassbox` database state and label
  local-only evidence clearly.
- Topology and ownership hints carry provenance and freshness. Stale topology
  lowers confidence rather than becoming current subsystem authority.
- Publication, deploy, package-upload, destructive cleanup, and git history
  rewriting commands remain policy-aware and outside automatic review-loop
  mutation.

## Command And Dashboard Copy Guidelines

Use copy that describes evidence and operator choice:

- Prefer "record review feedback" over "sync review comment".
- Prefer "requested change captured" over "reviewer blocked merge".
- Prefer "response recorded" or "resolved locally" over "approved" unless
  approval evidence exists.
- Prefer "manual evidence attached" over "command evidence recorded" for
  external commands and observations.
- Prefer "browser evidence is advisory" over "browser validation passed" when
  only a live walkthrough was retained.
- Prefer "handoff readiness: needs verification" over "ready to publish" when
  stale or missing evidence remains.
- Prefer "safe next action: inspect lifecycle brief" before suggesting any
  command that mutates files, git state, worktrees, remotes, deployments, or
  package registries.

Avoid copy that implies hidden automation, hosted authority, or approval:

- Do not say Glassbox approved, staged, committed, pushed, opened a PR, merged,
  rebased, deployed, or published unless that explicit action happened outside
  the review-loop lifecycle.
- Do not describe lifecycle briefs, handoff readiness, manual evidence, browser
  evidence, or accessibility evidence as proof that the change is correct.
- Do not hide unresolved feedback, stale verification, missing provenance, or
  accepted risks under optimistic summary copy.

## Related Documents

- [tasks-v13.md](./tasks-v13.md): v13 task graph and dependency order
- [v12-reviewable-change-contract.md](./v12-reviewable-change-contract.md):
  inherited reviewable local changeset contract
- [v12-release-candidate.md](./v12-release-candidate.md): supported v12
  operating model and release posture
- [review-briefs.md](./review-briefs.md): v12 reviewer-safe brief artifact
  contract that v13 lifecycle briefs build on
- [reviewer-evidence-bundles.md](./reviewer-evidence-bundles.md): current
  reviewer-safe handoff guidance
- [commit-readiness.md](./commit-readiness.md): v12 advisory commit readiness
  model that v13 handoff readiness must distinguish from publication
- [verification-loops.md](./verification-loops.md): verification guidance that
  v13 stale-evidence recommendations build on
