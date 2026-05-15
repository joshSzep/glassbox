# V17 Local Handoff Contract

For the docs hub and operator guides, start at [README.md](./README.md). This
page defines the v17 local handoff contract from
[tasks-v17.md](./tasks-v17.md). It is a planning contract until a later
release-candidate guide marks v17 as released behavior.

Glassbox v17 makes local work portable between operators, terminals, machines,
future selves, reviewers, and release custodians without turning Glassbox into a
hosted collaboration system. A handoff should help the recipient answer what
they received, why it was handed off, what evidence travelled, what stayed
local, what can be inspected safely, and what should happen next.

It is not an approval system, permission grant, remote lock, release decision,
publication workflow, or automatic continuation mechanism.

## Scope

V17 extends the v16 local operator-flow model with shared handoff vocabulary,
portable package manifests, readiness summaries, redaction preview, local-only
evidence inventory, import triage, custody decisions, and cockpit surfaces for
CLI, API, TUI, and dashboard users.

The supported source contexts are:

- `session`: a persisted session, including historical, paused, failed, active,
  imported, or sparse legacy sessions
- `task`: a durable task plan and its continuation posture
- `changeset`: a reviewed local changeset and its evidence posture
- `workspace`: the current local workspace posture across queue, maintenance,
  repository intelligence, sessions, tasks, artifacts, and daemon ownership
- `release`: a release-candidate evidence bundle and its deterministic versus
  advisory evidence split
- `future-self`: a self-handoff profile for returning to local work later

V17 reuses the v16 next-action, evidence, freshness, confidence, limitation,
accepted-risk, local-only, stale, skipped, manual-only, and non-claim language
from [evidence-graph.md](./evidence-graph.md),
[operator-queue.md](./operator-queue.md), and
[verification-orchestrator.md](./verification-orchestrator.md).

## Handoff Intent Vocabulary

Every handoff package, readiness response, import triage result, and cockpit
surface must name the recipient intent. Intent is workflow metadata; it does not
grant authority.

| Intent | Recipient Expectation | Required Posture |
| --- | --- | --- |
| `review-only` | Inspect the work and evidence without continuing it. | Reviewer-safe evidence, redaction posture, limitations, non-claims, and safe inspection commands. |
| `continue-work` | Continue from the current local story in a new controlled context. | Continuation blockers, pending approvals/questions, runtime-owner posture, local-only evidence, and fork guidance. |
| `verification-needed` | Run or select verification after inspecting evidence gaps. | Missing, stale, skipped, manual-only, and accepted-risk verification evidence plus safe planning commands. |
| `failure-triage` | Inspect failure evidence and choose retry, fork, reject, or archive. | Failure summary, retryability, provider/tool/recovery evidence, local-only gaps, and safe triage commands. |
| `release-signoff` | Review release evidence as a custodian, not approve publication automatically. | Deterministic gate evidence, advisory evidence separation, residual risks, package contents, non-claims, and release safe commands. |
| `future-self` | Preserve enough context for the same operator to return later. | Objective, last state, next actions, verification posture, local-only reminders, and stale-evidence warnings. |
| `fork-recommended` | Inspect historical work and begin alternate local work separately. | Fork reason, unsupported continuation blockers, source lineage, import posture, and safe fork or new-session guidance. |

Unknown or unsupported intent values must be preserved in JSON where possible
and rendered as unsupported in human output. Glassbox must not silently map an
unknown intent to continuation authority.

## Readiness Vocabulary

Handoff readiness answers whether a source is ready to be handed off for a
declared intent. It is advisory local evidence, not review approval or release
approval.

Shared readiness states are:

- `ready`: evidence supports the declared intent within visible limitations
- `historical-only`: source is inspectable but not a live continuation target
- `awaiting-approval`: a pending approval blocks continuation or verification
- `awaiting-answer`: a pending operator answer blocks continuation
- `needs-context`: objective, plan, transcript, checkpoint, or repository
  context is too sparse for the declared intent
- `needs-verification`: expected verification is missing, stale, failed,
  skipped without accepted risk, or manual-only
- `failed-needs-triage`: a failure exists and requires inspection before
  continuation or handoff confidence
- `local-only-evidence`: important supporting evidence cannot travel in the
  package
- `stale-evidence`: evidence exists but no longer matches current inputs or
  freshness policy
- `blocked`: policy, runtime-owner, compatibility, missing artifact, or source
  state prevents the declared intent
- `accepted-with-risk`: the handoff can proceed only because a residual risk was
  explicitly accepted and retained as evidence

Readiness responses must include:

- source kind and source identifiers
- declared intent and optional recipient/custodian labels
- state, confidence, freshness, limitations, and reasons
- supporting, missing, stale, redacted, local-only, manual-only, skipped,
  unsupported, and accepted-risk evidence summaries
- safe first commands for inspection, planning, or read-only triage
- non-claims that say what the readiness result does not approve

Safe first commands must not be approve, answer, resume, stage, commit, push,
publish, deploy, merge, or run arbitrary tools. Mutating commands can appear as
later options only when they are clearly labeled operator-selected and policy
controlled.

## Package Contract

A v17 handoff package is a portable artifact with a manifest and bounded payload
sections. It must not copy raw `.glassbox` databases, credentials, secrets, raw
provider transcripts, raw command logs, raw diffs, screenshots, or unreviewed
artifacts by default.

Every package manifest should carry:

- schema version and package kind
- source kind and source identifiers
- generated-at metadata and exporter metadata
- recipient intent and optional recipient, expected custodian, exported-by, and
  note labels
- readiness summary for the declared intent
- included section list and unsupported section list
- redaction summary and raw-inclusion flags
- local-only evidence summary
- compatibility summary
- package digest summary
- safe inspection commands
- package-level non-claims

Package digests prove package integrity, not source workspace completeness or
truth. A package can prove that its JSON was not changed after generation, but
it cannot prove that omitted local-only evidence, stale repository state, or
manual observations were complete.

## Redaction And Local-Only Evidence

Export must make redaction visible before and after package creation.

The redaction preview and final package should summarize:

- included sections
- redacted fields and redaction categories
- local-only evidence categories
- omitted raw artifacts, raw logs, raw transcripts, raw diffs, screenshots,
  provider output, browser traces, accessibility transcripts, credentials, and
  local paths
- unsupported evidence and package limitations
- affected claims whose confidence depends on evidence that did not travel

Local-only evidence can increase local confidence while lowering portable
confidence. Handoff output should say when the recipient cannot verify a claim
from the package alone.

## Import Triage

Import is inspection-first. Inspecting or importing a handoff package must not
resume a live turn, execute tools, approve commands, answer questions, stage
files, commit, push, publish, deploy, merge, or merge imported state into an
existing live session.

Import triage should validate and report:

- schema version and compatibility
- package kind, source kind, and recipient intent
- digest status and tamper warnings
- supported, unsupported, and missing optional sections
- redaction posture and raw-inclusion flags
- local-only omissions and affected claims
- stale, missing, skipped, manual-only, accepted-risk, and unsupported evidence
- recommended next disposition: inspect, accept for follow-up, fork, continue in
  a new local session, verify, reject, or archive
- safe first commands

Unsupported future packages should fail safely with inspection guidance. Legacy
session export packages should remain importable for inspection where practical,
but sparse legacy data must degrade visibly.

## Custody And Decisions

Custody is auditable workflow metadata. It helps humans coordinate who is
expected to act next; it is not authentication, authorization, approval,
membership, ownership, or a runtime lock.

The v17 custody workflow can record:

- handoff package created
- custody proposed
- custody accepted
- custody rejected with reason
- imported handoff inspected
- imported handoff accepted for follow-up
- handoff archived

These decisions should be canonical events, managed artifacts, typed API
responses, or rebuildable projections. They must preserve reasons, safe next
commands, and non-claims. Rejection should not delete the package record.

This contract extends the custody distinction in
[team-workflows.md](./team-workflows.md): runtime ownership still controls live
mutation, while custody only describes who is expected to notice and act.

## Surface Contract

CLI, API, TUI, dashboard, generated types, package manifests, Markdown renders,
and docs must use the same handoff vocabulary. Surfaces may abbreviate for
space, but they should not invent different state names or hide limitations.

Expected v17 surfaces are:

- readiness commands for sessions, tasks, changesets, workspaces, and release
  evidence
- export preparation with redaction preview and local-only inventory
- recipient-oriented export profiles
- package inspection and import triage
- custody accept, reject, archive, list, and follow-up actions
- operator queue rows for awaiting recipient, import needs triage, local-only
  evidence blocks export, and accepted handoff needs verification
- dashboard and TUI cockpit views that remain projections over local evidence

The dashboard is not a second source of truth. Canonical state remains events,
managed artifacts, typed responses, and rebuildable projections.

## Non-Claims

No v17 handoff readiness result, package, import triage result, custody decision,
dashboard row, TUI action, API response, or Markdown summary claims that:

- a reviewer approved the work
- a release custodian approved publication
- verification passed unless retained verification evidence says it passed
- the recipient has continuation authority
- runtime ownership changed
- raw evidence was shared
- package evidence is complete
- repository intelligence, memory, provider canaries, browser evidence,
  accessibility evidence, manual evidence, review feedback, or custody metadata
  is deterministic release authority
- Glassbox staged, committed, pushed, opened a pull request, merged, deployed,
  published, or approved commands

## Relationship To Existing Guides

- [team-workflows.md](./team-workflows.md) remains the runtime-owner and
  custody baseline. V17 expands custody decisions and package portability while
  preserving single-writer runtime ownership.
- [reviewer-evidence-bundles.md](./reviewer-evidence-bundles.md) remains the
  reviewer-safe evidence guide. V17 makes recipient intent, redaction preview,
  local-only evidence, and import triage shared package concepts.
- [evidence-graph.md](./evidence-graph.md) provides support, missing, stale,
  manual-only, accepted-risk, redaction, visibility, confidence, and freshness
  language for portable claims.
- [operator-queue.md](./operator-queue.md) provides queue item families, states,
  evidence summaries, and safe next actions for handoff follow-up rows.
- [verification-orchestrator.md](./verification-orchestrator.md) provides
  verification lifecycle language so handoff never treats planned, skipped,
  stale, manual-only, failed, or accepted-risk checks as passed.

## Deliberate Non-Goals

V17 does not add hosted accounts, authentication, authorization, remote custody
enforcement, cloud evidence storage, hosted task queues, hosted review state,
remote repository indexing, remote session sync, remote workers, simultaneous
multi-writer sessions, PR automation, GitHub integration, automatic staging,
automatic commits, pushes, pull requests, merges, deployments, publication,
automatic command approval, raw database export, or automatic merge of imported
state into a live session.

Those can be revisited only through a future contract with a new authority
model, evidence policy, and release gate.
