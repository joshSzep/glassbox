# Glassbox v16 Operator Flow Compression Contract

For the docs hub and operator guides, start at [README.md](./README.md). This
page defines the v16 operator and contributor contract for the planning track in
[tasks-v16.md](./tasks-v16.md), after the v15 repository intelligence
milestone.

Glassbox v16 compresses daily operator flow. It does not add hidden automation
or new publication authority. The milestone should help operators answer "what
should I do next, why, and what evidence supports it?" across sessions, tasks,
changesets, review feedback, verification, repository intelligence, memory,
maintenance, recovery, and release posture.

The contract builds on the v15
[repository intelligence contract](./v15-repository-intelligence-contract.md),
the [path-to-verification recommendations contract](./path-to-verification-recommendations.md),
the [tool policy and approval semantics](./tool-policy.md),
[review feedback](./review-feedback.md), and
[runtime context](./runtime-context.md). Those documents remain the authority
for local-first repository intelligence, verification recommendations, approval
gates, local review state, bounded prompt context, replay visibility, and
deterministic release evidence.

## Scope

v16 focuses on operator flow compression:

- define one advisory next-action vocabulary for local, evidence-backed
  operator guidance
- derive an evidence graph that connects claims, recommendations, commands,
  artifacts, events, memory, verification, review feedback, repository
  intelligence, and limitations
- introduce verification planning as an explicit workflow from recommendation
  through selection, run evidence, skip, stale state, and accepted risk
- expose one operator queue for blocked turns, pending approvals, unanswered
  questions, failed jobs, stale evidence, unresolved feedback, stale repository
  intelligence, maintenance cues, and verification gaps
- make CLI, TUI, dashboard, API, review brief, and handoff surfaces speak the
  same priority, evidence, freshness, confidence, and limitation language
- keep maintenance and recovery cues beside affected work instead of isolating
  them in expert-only command paths

v16 improves how Glassbox guides local work. It does not replace operator
judgment, deterministic tests, release gates, review, repository policy, tool
approval, or publication decisions.

## Vocabulary

| Term | Operator meaning | Boundary |
| --- | --- | --- |
| Next action | A typed recommendation for the safest useful local inspection, planning, verification, recovery, or review step. | It is advisory. It does not approve, stage, commit, push, publish, merge, deploy, or run a command by itself. |
| Evidence graph | A derived view that links local claims and recommendations to supporting, missing, stale, contradictory, manual-only, or accepted-risk evidence. | It is not a second source of truth; it is rebuilt from canonical events, projections, managed artifacts, and typed local responses. |
| Verification plan | A reviewable local plan for checks that may be proposed, selected, run, skipped, marked stale, superseded, accepted with risk, or recorded as manual-only. | Planning is not execution. A recommended command is not an approved command. |
| Operator queue | A ranked, typed list of local attention items across sessions, tasks, changesets, verification, review, repository intelligence, memory, maintenance, recovery, and release posture. | Queue items are derived guidance unless an explicit canonical event records an operator decision. |
| Maintenance cue | A local signal about projection drift, stale repository intelligence, failed background jobs, artifact pressure, stale daemon ownership, provider misconfiguration, backup posture, or related recovery needs. | A cue can recommend inspection or repair, but it cannot mutate state without the normal command, policy, and approval path. |
| Claim support | The evidence relationship explaining why a readiness, verification, handoff, review, queue, or next-action claim is supported, stale, missing, contradicted, skipped, manual-only, or accepted with risk. | Support must cite local evidence or clearly name what is missing; raw local blobs stay behind existing redaction and artifact boundaries. |

## Supported Workflow Set

v16 should support these local workflows:

1. An operator can ask what needs attention and receive one ranked queue with
   safe next actions, evidence references, freshness, confidence, limitations,
   and owning surfaces.
2. A session, task, changeset, review feedback item, verification plan, or
   maintenance cue can explain why it is blocked, degraded, stale, ready enough,
   advisory, manual-only, or accepted with risk.
3. A changed-path set can produce a non-mutating workup preview that combines
   inventory, repository intelligence impact, verification planning, stale
   evidence, review risks, and safe next commands.
4. Operators can create, inspect, select, skip, supersede, run, retry, or accept
   risk for verification plan entries while preserving the distinction between
   planned evidence and executed evidence.
5. Review briefs, handoff readiness, evidence bundles, CLI output, API
   responses, dashboard panels, and TUI entry points can point to the same
   underlying next-action and evidence language.
6. Maintenance and recovery guidance appears near affected work and remains
   inspectable through local commands and retained evidence.

## Evidence Expectations

Next actions, evidence graph edges, verification plans, queue items,
maintenance cues, readiness claims, and handoff claims must be backed by at
least one of these local inputs:

- canonical events from sessions, tasks, tools, approvals, verification,
  review feedback, manual evidence, background jobs, memory, and repository
  intelligence
- rebuildable projections and query responses derived from those events
- managed artifacts such as review briefs, command evidence, verification
  ledgers, replay outputs, eval outputs, repository intelligence snapshots, and
  release-gate summaries
- typed API responses or CLI JSON that preserve provenance, freshness,
  confidence, limitations, and redaction posture
- deterministic eval fixtures or release-gate rows

Evidence surfaces should prefer summaries, identifiers, source paths, event
IDs, artifact IDs, digests, timestamps, freshness states, and redaction labels
over raw transcripts, raw command logs, raw artifacts, raw diffs, or local
database internals.

Missing evidence is a first-class state. Stale evidence, skipped checks,
manual-only evidence, advisory evidence, accepted risk, degraded repository
intelligence, provider unavailability, and unsupported surfaces must be named
instead of hidden behind optimistic copy.

## Next-Action Authority

Next actions are advisory, local, inspectable, and bounded. They can recommend:

- a read-only inspection command
- a command recipe to consider
- a verification plan entry to select
- an evidence graph or queue detail to inspect
- a recovery or maintenance workflow to review
- a review feedback or handoff gap to resolve

Next actions must not:

- approve or execute commands
- bypass [tool policy](./tool-policy.md), autonomy budgets, repository policy,
  hard command blocks, or approval gates
- stage, commit, push, open pull requests, publish packages, deploy, merge, or
  mutate repository history
- convert repository intelligence, memory, review feedback, manual evidence,
  browser evidence, accessibility evidence, provider canaries, owner hints, or
  response-linked fixups into release approval authority

Safe next-action copy should start with inspection when inspection is useful:
show the target, reason, evidence reference, missing or stale inputs,
limitations, and the safest useful command.

## Verification Orchestration

Verification orchestration in v16 has explicit phases:

- planning proposes checks from changed paths, changeset inventory, repository
  intelligence, eval metadata, command recipes, stale evidence, and existing
  verification posture
- recommending explains why a check matters, what it covers, what it does not
  cover, and which command recipe or manual evidence path applies
- selecting records the operator's local decision that a planned entry should
  be pursued
- executing runs only explicitly selected commands through existing policy,
  approval, command-evidence, timeout, cancellation, and tool-attempt paths
- skipping records that a check was intentionally not run, with scope and
  rationale
- accepting risk records residual risk, scope, rationale, and supporting or
  missing evidence
- publishing remains outside v16 automation and outside verification-plan
  authority

A passed verification plan is not a release decision. A skipped or accepted-risk
entry is not a pass. Advisory browser, accessibility, provider, repository
intelligence, memory, and manual evidence can improve confidence only when
their advisory posture remains visible.

## Maintenance Posture

Maintenance cues belong in normal operator flow when they affect confidence or
daily work. v16 surfaces may include cues for:

- failed or stale background jobs
- projection drift, rebuild needs, and projection-health limitations
- stale, missing, degraded, failed, or conflicting repository intelligence
- stale changeset inventory, stale verification evidence, or stale handoff
  readiness
- artifact pressure, backup gaps, and package or release-evidence gaps
- stale daemon ownership, provider misconfiguration, and provider recovery
  needs
- memory conflicts, stale memory-derived guidance, or prompt-use visibility
  gaps

Maintenance cues should name impact, affected targets, supporting evidence,
safe inspection commands, recovery commands when available, and why the cue is
advisory or blocking. They must not run remediation automatically.

## Release Authority

v16 does not change release authority. Release blocking remains deterministic
and local:

- tests, type checks, lint, formatting, migrations, package validation, replay,
  evals, release gates, and explicit release-candidate evidence remain the
  release decision inputs
- next actions, operator queues, evidence graphs, verification plans,
  repository intelligence, memory, browser evidence, accessibility evidence,
  provider canaries, owner hints, and review feedback improve explainability
  but do not grant release approval
- any intentional drift in deterministic replay, eval, API, CLI, frontend, or
  package behavior must be refreshed through the existing eval and release-gate
  workflow

## Safety Rules

v16 implementations must preserve these invariants:

- local-first state and local evidence remain the default; no hosted queues,
  hosted review state, remote indexing, remote worker fleets, external
  vector-store authority, or provider-side hidden memory are v16 dependencies
- event-sourced state remains authoritative; derived views are rebuildable and
  bounded
- raw local data stays behind existing artifact, export, and redaction
  boundaries
- API, CLI, TUI, dashboard, review brief, and handoff surfaces use compatible
  priority, freshness, stale-evidence, accepted-risk, limitation, and safe
  action language
- older sessions and sparse evidence must degrade gracefully with visible
  missing-evidence states
- no operator-visible recommendation should exist only in process memory once a
  task claims durability

## Relationship To V15 Contracts

v16 consumes v15 repository intelligence as advisory evidence. It can use fresh
repository intelligence to explain likely tests, command recipes, ownership
hints, release-sensitive paths, generated paths, and limitations. Stale,
missing, degraded, failed, conflicting, or partially rebuilt intelligence must
lower confidence and name safe inspection or rebuild actions.

The [path-to-verification recommendations](./path-to-verification-recommendations.md)
contract remains the source for changed-path verification guidance. v16 turns
that guidance into explicit verification plans and next actions without
pretending that planned checks have already run.

The [runtime context](./runtime-context.md) contract remains the boundary for
prompt inclusion. Next-action and evidence-graph summaries may shape context
only when provenance, freshness, confidence, limitations, budget impact, and
replay fingerprints stay inspectable.

The [review feedback](./review-feedback.md) contract remains the source for
local feedback, requested changes, responses, and fixup posture. v16 may link
feedback to verification plans and evidence graph support, but resolving local
feedback does not imply reviewer acceptance.

## Non-Goals

v16 deliberately does not add:

- hosted collaboration, hosted task queues, hosted review queues, or remote
  workspace authority
- automatic publication, staging, committing, pushing, pull request creation,
  merging, deployment, package release, or repository-history mutation
- release approval based on next actions, queue ranking, repository
  intelligence, memory, provider canaries, browser evidence, accessibility
  evidence, review feedback, owner hints, or manual evidence alone
- hidden command execution from verification planning
- raw artifact, raw transcript, raw command-log, raw diff, or `.glassbox`
  database exposure in reviewer-safe surfaces by default
- a visual graph layout requirement before typed evidence graph summaries are
  useful
- provider-side hidden memory or external vector-store authority as a source of
  local truth
