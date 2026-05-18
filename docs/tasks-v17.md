# Glassbox v17 Tasks

For the docs hub and operator guides, start at [README.md](./README.md). This
file is the v17 task graph for making Glassbox local handoff a first-class
workflow after the v16 operator-flow compression milestone.

## Purpose

This document defines Glassbox v17: local handoff.

It is written in the same execution style as [tasks-v1.md](./tasks-v1.md)
through [tasks-v16.md](./tasks-v16.md): explicit dependencies, small vertical
slices, concrete deliverables, and quality requirements attached directly to
the work.

The v12 through v14 milestones made local changes reviewable. The v15 milestone
made Glassbox less forgetful about the repository. The v16 milestone compressed
operator flow into shared next actions, queue items, evidence graphs,
verification plans, maintenance cues, changeset workups, and reviewer-safe
evidence bundles.

The v17 goal is to make local work portable between operators, terminals,
machines, future selves, reviewers, and release custodians without turning
Glassbox into hosted collaboration. Glassbox should help a recipient answer:
"What am I receiving, why was it handed off, what evidence travelled, what
evidence stayed local, what can I inspect safely, and what should I do next?"

The v17 work should optimize for nine outcomes:

- define explicit handoff intents such as review-only, continue-work,
  verification-needed, failure-triage, release-signoff, future-self, and fork
  recommended
- introduce a portable handoff package schema that can carry session,
  changeset, task, repository, verification, queue, and evidence posture without
  copying raw `.glassbox` databases, secrets, credentials, or raw logs
- make handoff readiness available for sessions, tasks, changesets, and
  workspace/release contexts with shared status, confidence, freshness,
  limitation, and non-claim language
- provide recipient-oriented export profiles that render compact human
  Markdown, stable JSON, reviewer-safe evidence, and importable inspection
  metadata from the same local evidence
- add redaction preview and local-only evidence inventory so operators can see
  what will travel, what will be summarized, and what must remain local before
  exporting
- make import a triage workflow, not a blind JSON load: validate schema,
  digests, redaction posture, local-only gaps, compatibility, safe commands,
  and fork/continue/review recommendations
- record custody, acceptance, rejection, and follow-up handoff decisions as
  auditable local workflow events or retained evidence without making custody
  an authentication or authorization system
- expose handoff cockpit surfaces in CLI, TUI, API, and dashboard that reuse
  v16 queue, evidence graph, verification plan, and next-action language
- preserve Glassbox's local-first, event-sourced, replay-aware,
  operator-controlled authority model while making work continuity calmer,
  safer, and easier to review

The v17 thesis is:

- v16 made Glassbox guide local work; v17 should make Glassbox hand off local
  work to another context without losing meaning
- handoff is a workflow expectation, not a lock, permission grant, review
  approval, publication event, or remote coordination channel
- a handoff package should be recipient-shaped: review-only packages should not
  imply continuation authority, and continuation packages should not hide
  missing or local-only evidence
- import should begin with inspection and triage before any resumed work,
  fork, verification, or mutation
- every portable claim should cite supporting evidence, missing evidence,
  local-only evidence, stale evidence, accepted risks, redaction posture,
  confidence, limitations, and safe inspection commands
- dashboard and TUI should make handoff readable, but canonical state remains
  events, managed artifacts, package manifests, and rebuildable projections
- hosted collaboration, remote review authority, PR automation, automatic
  publication, multi-writer sessions, and raw evidence sharing remain outside
  v17

## Current Baseline Before V17 Execution

Treat the following as the starting point for every task in this document:

- [v16-release-candidate.md](./v16-release-candidate.md) records the supported
  operator-flow operating model, validation path, evidence split, residual
  risks, and non-goals.
- [team-workflows.md](./team-workflows.md) defines runtime owner, acting
  operator, session custodian, intervention, and handoff vocabulary while
  preserving local-first single-writer runtime ownership.
- [reviewer-evidence-bundles.md](./reviewer-evidence-bundles.md) defines
  reviewer-safe surfaces, redaction rules, retention rules, release-candidate
  review handoff, and ordinary code-review handoff.
- [review-briefs.md](./review-briefs.md), [manual-evidence.md](./manual-evidence.md),
  [review-feedback.md](./review-feedback.md), [review-responses.md](./review-responses.md),
  [commit-readiness.md](./commit-readiness.md), and
  [publication-boundary.md](./publication-boundary.md) define existing local
  review-loop, readiness, redaction, non-claim, and final-action boundaries.
- [evidence-graph.md](./evidence-graph.md), [operator-queue.md](./operator-queue.md),
  and [verification-orchestrator.md](./verification-orchestrator.md) define the
  v16 evidence, queue, and verification language that handoff must reuse.
- `glassbox session export` already creates inspectable portable session
  handoff packages with a `handoff.summary` block, optional operator labels,
  redaction of common sensitive forms, and inspection-only import semantics.
- `glassbox changeset export` already creates reviewer-safe changeset evidence
  bundles with redaction reports, evidence graph slices, review feedback,
  verification, manual evidence, handoff posture, and non-claims.
- `glassbox changeset handoff-readiness` already provides a read-only
  changeset final-handoff posture from retained local evidence and current git
  inspection.
- The runtime already records canonical events, managed artifacts, projection
  tables, replay artifacts, eval outputs, tool attempts, verification ledger
  entries, review feedback, manual evidence, workspace memory, background jobs,
  repository intelligence snapshots, evidence graph summaries, operator queue
  rows, and maintenance cues.
- Import currently creates local inspection state, but handoff import triage,
  acceptance/rejection, custody follow-up, recipient intent, redaction preview,
  and shared package validation are not yet first-class surfaces.

## V17 Local Handoff Findings

Treat these findings as evidence that should steer the first implementation
slices:

- Existing handoff export and changeset export are valuable but still
  command-specific. Operators need one handoff story that can target sessions,
  tasks, changesets, release evidence, and future-self continuity.
- A recipient cannot reliably tell from a package alone whether they should
  review, continue work, verify, fork, triage failure, sign off release
  evidence, or simply archive historical context.
- Handoff readiness exists for changesets, but session-level and task-level
  handoff readiness need equivalent status, limitation, safe-action, and
  non-claim language.
- Export should make local-only evidence visible before the package is written.
  Operators need a redaction and portability preview, not just a post-hoc
  redaction report.
- Import should behave like receiving work: inspect the package, validate
  portability, explain missing evidence, recommend safe first commands, and
  preserve the imported state as historical unless the operator explicitly
  forks or continues through existing local runtime paths.
- Custody should be auditable local metadata. It should help humans coordinate
  who is expected to act next, but it must not become authentication,
  authorization, role membership, approval authority, or a remote lock.
- Handoff should integrate with the v16 operator queue so "handoff awaiting
  recipient," "import needs triage," "local-only evidence blocks export," and
  "accepted handoff needs verification" appear beside normal work.
- The next milestone should improve local continuity and evidence portability
  before expanding into GitHub integration, hosted review, remote sync, or
  automatic publication.

## Agent Execution Rules

These rules apply to every task in this file.

1. Respect dependency order. Do not start a task until its dependencies are
   complete unless the task explicitly says it can proceed in parallel.
2. Preserve the event-sourced source-of-truth rule. Handoff packages, custody
   events, import records, redaction reports, readiness rows, queue items, and
   dashboard state must be canonical events, managed artifacts, typed API
   responses, or rebuildable derived state.
3. Preserve local-first operation. Do not introduce hosted collaboration,
   hosted review state, remote session sync, cloud evidence storage, remote
   workers, remote repository indexing, external vector-store authority, or
   provider-side hidden memory as v17 release dependencies.
4. Preserve single-writer runtime ownership. Handoff custody does not override
   daemon ownership, live session ownership, approval modes, tool policy, or
   mutation boundaries.
5. Treat custody as workflow metadata, not authorization. An expected custodian
   can be named, changed, accepted, or rejected locally, but that metadata does
   not grant permission or block another local operator from acting through
   existing policy-controlled commands.
6. Keep handoff recipient intent explicit. A review-only package must not imply
   continuation authority; a continuation package must not hide missing,
   stale, accepted-risk, or local-only evidence.
7. Keep import inspection-first. Importing a package must not silently resume a
   live turn, execute tools, approve commands, stage files, mutate git, or merge
   imported state into an existing live session.
8. Keep redaction visible. Export and import surfaces must show what travelled,
   what was summarized, what was redacted, what stayed local, and what the
   recipient cannot verify from the package alone.
9. Keep verification and publication explicit. Handoff may recommend
   verification, review, fork, release signoff, or commit preparation, but it
   must not approve, run, stage, commit, push, publish, merge, deploy, or create
   pull requests.
10. Keep CLI/API/frontend language aligned. Do not let each surface invent its
    own custody, intent, redaction, local-only, recipient-action, or package
    compatibility vocabulary.
11. Do not turn handoff acceptance into reviewer approval, release approval,
    verification success, commit readiness, publication readiness, owner
    assignment, or merge readiness.
12. Every implementation task automatically includes:
    - automated tests for new or changed behavior
    - `ruff` formatting and lint compliance for touched Python code
    - `ty` typecheck compliance for touched Python code
    - focused `pytest` coverage for touched runtime, CLI, TUI, web, replay,
      eval, daemon, store, policy, task, verification, provider, branch-search,
      changeset, review, manual evidence, repository intelligence, memory,
      recovery, maintenance, handoff, and terminal behavior
    - frontend lint, typecheck, tests, and build when the task touches
      dashboard code, generated API types, packaged static assets, route
      assumptions, frontend stores, handoff panels, queue panels, evidence graph
      panels, or import/export workflows
    - documentation updates when operator-visible behavior, evidence posture,
      redaction posture, import posture, custody behavior, verification
      posture, recovery behavior, policy behavior, release posture, or public
      workflow claims change

## Completion Contract For Any Task

A task is complete only when all of the following are true:

- the implementation exists in the intended module boundary
- automated tests covering the changed behavior exist and pass
- lint, formatting, type checks, and focused tests pass for touched code
- frontend validation passes when dashboard, generated API types, TUI command
  surfaces, or packaged static assets are touched
- deterministic replay/eval behavior remains stable or intentional drift is
  documented through the eval refresh workflow
- public docs are accurate against command help, API behavior, package
  contents, redaction behavior, import/export behavior, and release posture
- handoff packages, readiness claims, custody changes, import triage rows,
  redaction reports, and queue items are backed by deterministic local inputs,
  canonical events, managed artifacts, typed API responses, or eval fixtures
- new guidance starts with safe inspection before mutation
- skipped, stale, missing, manual-only, local-only, redacted, advisory,
  accepted-risk, unsupported, and compatibility-warning states are visible
  rather than hidden under optimistic copy
- no meaningful handoff, custody, package, import triage, redaction, readiness,
  queue, or next-action state exists only in memory once a task claims
  durability
- reviewer-facing artifacts are redacted or explicitly documented as local-only
- repository intelligence remains advisory and freshness-aware
- memory-derived guidance remains confirmed, active, provenance-backed, and
  prompt-use-recorded before it shapes model context
- the task does not leave placeholder code or hidden follow-up work outside
  this file

## Suggested Status Markers

If an agent updates this document later, use one of these markers next to task
IDs:

- `TODO`
- `IN_PROGRESS`
- `BLOCKED`
- `DONE`

## Expected Repository Targets

These are the main implementation areas referenced below:

```text
README.md
pyproject.toml
scripts/
docs/
    tasks-v17.md
    v17-local-handoff-contract.md
    local-handoff.md
    team-workflows.md
    reviewer-evidence-bundles.md
    interactive-workflows.md
    dashboard.md
    replay-evals.md
    release-packaging.md
src/glassbox/
    cli/
    core/
    runtime/
    store/
    tools/
    web/
frontend/
    api/
    app/
    components/
    generated/
    state/
    stores/
    tests/
evals/
tests/
```

## Task Graph

The task graph uses `GBX-17xx` IDs. Split tasks further if a task becomes too
large to review safely.

---

## Phase 170: V17 Contract, Audit, And Discovery

### GBX-1700: Define The v17 Local Handoff Contract

- Status: `DONE`
- Depends on: none
- Goal: publish the operator and contributor contract for v17 local handoff
- Deliverables:
  - `docs/v17-local-handoff-contract.md`
  - handoff intent vocabulary
  - handoff readiness vocabulary for sessions, tasks, changesets, workspace,
    release, and future-self contexts
  - package portability, redaction, local-only evidence, custody, import triage,
    acceptance/rejection, and non-claim boundaries
  - explicit relationship to `team-workflows.md`,
    `reviewer-evidence-bundles.md`, `evidence-graph.md`,
    `operator-queue.md`, and `verification-orchestrator.md`
- Implementation notes:
  - make the contract readable before implementation begins
  - preserve v16 next-action, evidence, freshness, confidence, and limitation
    language
  - keep hosted collaboration and PR automation out of scope
- Tests and validation included in task:
  - docs link review
  - `uv run pytest tests/unit/test_release_candidate_docs.py -q` if doc
    discovery tests require the new contract
- Done when:
  - contributors can tell which handoff behaviors are authoritative, advisory,
    portable, local-only, and out of scope

### GBX-1701: Audit Current Handoff, Export, Import, And Review Bundle Surfaces

- Status: `DONE`
- Depends on: `GBX-1700`
- Goal: source-link existing handoff behavior and identify v17 gaps before
  implementation
- Deliverables:
  - `docs/v17-local-handoff-audit.md`
  - source-linked inventory of session export/import, changeset export,
    handoff-readiness, review briefs, reviewer-safe bundles, queue rows,
    evidence graph summaries, verification plans, manual evidence, redaction,
    artifact retention, and dashboard surfaces
  - gap list grouped by schema, runtime, store, CLI, web, frontend, eval,
    release gate, docs, and dogfooding
  - accepted non-goals and risk register
- Implementation notes:
  - name current package shapes and command flags before proposing changes
  - distinguish missing product behavior from refactor-only pressure
  - include stale or local-only evidence behavior
- Tests and validation included in task:
  - command help spot checks for current export/import commands
  - docs link review
- Done when:
  - the v17 implementation plan is grounded in current code instead of desired
    behavior alone

### GBX-1702: Update Documentation Discovery For v17

- Status: `DONE`
- Depends on: `GBX-1700`, `GBX-1701`
- Goal: make v17 planning discoverable without implying it is already released
- Deliverables:
  - README current-baseline notes when v17 planning starts
  - docs hub links for v17 contract, audit, task graph, and later release guide
  - `local-handoff.md` operator guide stub or first draft
  - updates to `team-workflows.md` and `reviewer-evidence-bundles.md` pointing
    at the v17 planning track
- Implementation notes:
  - clearly label planning versus released behavior
  - do not make package-version claims unless release policy changes
- Tests and validation included in task:
  - docs link review
  - package-content guard updates if new docs must ship
- Done when:
  - operators can find v17 planning docs from the normal docs path

---

## Phase 171: Handoff Domain Models And Package Schema

### GBX-1710: Define Handoff Intent, Recipient, Custody, And Package Models

- Status: `DONE`
- Depends on: `GBX-1700`
- Goal: add typed core models for local handoff without introducing remote
  collaboration authority
- Deliverables:
  - handoff intent enum and model family
  - recipient/custodian label models with source, display name, and local-only
    metadata posture
  - handoff readiness state and reason models shared across surfaces
  - handoff package manifest model with schema version, source type, source
    identifiers, generated-at metadata, redaction summary, local-only evidence
    summary, compatibility summary, digest summary, and non-claims
  - unit tests for validation, serialization, unknown/unsupported states, and
    default non-claims
- Implementation notes:
  - prefer focused modules under `core/` or `runtime/` with stable facade
    exports, rather than growing broad model files by default
  - keep labels as audit metadata, not auth
  - use schema versioning from the first package version
- Tests and validation included in task:
  - focused unit tests for model validation
  - `uv run ty check src tests` for touched model modules
- Done when:
  - runtime, CLI, web, and frontend work can share one typed handoff vocabulary

### GBX-1711: Add Handoff Package Schema v2 And Compatibility Inspection

- Status: `DONE`
- Depends on: `GBX-1710`
- Goal: define the portable package contract that session and changeset exports
  can converge on
- Deliverables:
  - package schema v2 for handoff manifests and payload sections
  - compatibility inspector for schema version, source kind, package kind,
    supported/unsupported sections, missing optional sections, package digests,
    and local-only omissions
  - redaction and raw-inclusion flags in the package manifest
  - package-level non-claims for review approval, verification success,
    continuation authority, publication, and raw evidence sharing
  - tests for forward-compatibility warnings and unsupported future package
    versions
- Implementation notes:
  - keep v1 session export importable where practical
  - never require raw `.glassbox` database contents
  - package digests should prove package integrity, not source workspace
    completeness
- Tests and validation included in task:
  - unit tests for package loading and compatibility inspection
  - integration tests for legacy package compatibility
- Done when:
  - operators can inspect a package and know whether Glassbox can read it,
    trust its redaction posture, and explain any limitations

### GBX-1712: Add Handoff Event And Projection Boundaries

- Status: `DONE`
- Depends on: `GBX-1710`, `GBX-1711`
- Goal: make handoff workflow decisions durable and queryable
- Deliverables:
  - canonical events for handoff package created, handoff custody proposed,
    custody accepted, custody rejected, imported handoff inspected, imported
    handoff accepted for follow-up, and handoff archived
  - migration and projection tables for latest handoff posture by session,
    task, changeset, and imported package when needed
  - repository adapter methods and query helpers
  - projection rebuild coverage
- Implementation notes:
  - do not persist raw package contents in SQLite when a managed artifact is
    the better boundary
  - make import triage durable without making imported sessions live mutable
  - keep projection tables derived and rebuildable
- Tests and validation included in task:
  - SQLite bootstrap and migration tests
  - projection rebuild tests
  - repository adapter contract tests
- Done when:
  - handoff workflow state survives process restart and can be inspected from
    CLI/API/dashboard

---

## Phase 172: Handoff Readiness Services

### GBX-1720: Add Session Handoff Readiness

- Status: `DONE`
- Depends on: `GBX-1710`
- Goal: explain whether a session is ready to hand off for a declared intent
- Deliverables:
  - runtime service for session handoff readiness
  - states for ready, historical-only, awaiting-approval, awaiting-answer,
    needs-context, needs-verification, failed-needs-triage, local-only-evidence,
    stale-evidence, blocked, and accepted-with-risk
  - evidence references to transcript summaries, runtime notes, checkpoints,
    compactions, pending approvals/questions, verification ledger, tool
    attempts, provider recovery, artifacts, queue items, and maintenance cues
  - safe first commands and non-claims
  - CLI JSON and human output for `glassbox session handoff-readiness`
- Implementation notes:
  - readiness must vary by handoff intent
  - never recommend approve/answer/resume as "safe inspection"
  - old sessions with sparse evidence should degrade visibly
- Tests and validation included in task:
  - unit tests for readiness state ranking
  - integration tests for CLI output on active, paused, failed, completed, and
    imported sessions
- Done when:
  - a recipient can understand why a session can or cannot be handed off

### GBX-1721: Add Task Handoff Readiness

- Status: `DONE`
- Depends on: `GBX-1720`
- Goal: explain whether a durable task plan is ready for another operator or
  future self
- Deliverables:
  - runtime service for task handoff readiness
  - task objective, plan status, step posture, continuation windows,
    checkpoints, verification ledger, budget posture, blockers, accepted risks,
    and stale evidence summary
  - CLI JSON and human output for task handoff readiness
  - safe inspection commands for task detail, events, verification, queue, and
    observability
- Implementation notes:
  - task readiness should not duplicate session readiness; it should summarize
    task-specific continuation posture and link back to session evidence
  - maintain explicit distinction between paused, blocked, failed, abandoned,
    and complete task states
- Tests and validation included in task:
  - unit tests for task readiness derivation
  - integration tests for task CLI output
- Done when:
  - a task can be handed off without requiring the recipient to reconstruct the
    plan from raw session history

### GBX-1722: Align Changeset Handoff Readiness With v17 Handoff Vocabulary

- Status: `DONE`
- Depends on: `GBX-1710`, `GBX-1720`
- Goal: make existing changeset handoff readiness use the shared v17 handoff
  model without regressing current review-loop behavior
- Deliverables:
  - adapter or model updates that map current changeset handoff readiness to
    shared intent, recipient-action, redaction, local-only, and non-claim
    fields
  - preserved CLI/API/dashboard compatibility where current consumers depend
    on existing names
  - updated changeset export payloads to cite the shared handoff readiness
    shape
  - tests proving existing changeset handoff output remains stable or changes
    intentionally with docs
- Implementation notes:
  - keep current commit-readiness and publication-boundary distinctions intact
  - do not weaken unresolved feedback, stale verification, local-only evidence,
    or accepted-risk blockers
- Tests and validation included in task:
  - focused changeset readiness tests
  - API/OpenAPI type refresh if response contracts change
  - frontend tests if dashboard payloads change
- Done when:
  - changeset handoff reads as one member of the broader v17 handoff model

### GBX-1723: Add Workspace And Release Handoff Summaries

- Status: `DONE`
- Depends on: `GBX-1720`, `GBX-1721`, `GBX-1722`
- Goal: summarize a workspace or release-candidate handoff without pretending
  it is a remote release decision
- Deliverables:
  - workspace handoff summary from operator queue, observability, repository
    intelligence, memory, backups, artifacts, daemon owner, active sessions,
    changesets, and release evidence
  - release handoff summary from eval reports, release gates, package checks,
    installed smoke, advisory evidence, skipped evidence, residual risks, and
    package contents
  - CLI JSON and human output
  - safe inspection commands and explicit non-claims
- Implementation notes:
  - release handoff is for a human custodian, not release approval
  - keep deterministic evidence separate from advisory provider/browser/manual
    evidence
- Tests and validation included in task:
  - unit tests for workspace/release summary construction
  - release-gate dry-run tests when release summary shape changes
- Done when:
  - a release custodian can receive a concise local evidence handoff without
    mistaking it for publication

---

## Phase 173: Export Profiles, Redaction Preview, And Local-Only Inventory

### GBX-1730: Add Handoff Redaction Preview

- Status: `DONE`
- Depends on: `GBX-1711`, `GBX-1720`
- Goal: show operators what will travel before writing a handoff package
- Deliverables:
  - redaction preview service for session, task, changeset, workspace, and
    release handoff sources
  - counts and summaries for included sections, redacted fields, local-only
    evidence, omitted raw artifacts, omitted raw logs, omitted provider output,
    unsupported evidence, and package limitations
  - CLI `--preview` output for export commands
  - machine-readable preview JSON
- Implementation notes:
  - preview must use the same redaction path as export
  - local paths, secrets, raw logs, screenshots, and raw diffs should be named
    as omitted categories, not copied into the preview
- Tests and validation included in task:
  - unit tests for redaction category detection
  - integration tests proving preview and export agree on included/omitted
    sections
- Done when:
  - an operator can inspect shareability before creating a package

### GBX-1731: Add Local-Only Evidence Inventory

- Status: `DONE`
- Depends on: `GBX-1730`
- Goal: make non-portable evidence explicit and reviewable
- Deliverables:
  - inventory builder for local-only evidence across artifacts, manual
    evidence, browser/dashboard/accessibility observations, provider canaries,
    raw command logs, raw transcripts, screenshots, local paths, repository
    intelligence snapshots, and release evidence
  - local-only reasons, affected claims, safe local inspection commands, and
    recipient limitations
  - integration into handoff readiness, redaction preview, export payloads, and
    import triage
- Implementation notes:
  - do not leak local-only contents while summarizing their existence
  - local-only evidence can improve local confidence but should lower portable
    confidence when the recipient cannot inspect it
- Tests and validation included in task:
  - unit tests for inventory grouping and affected-claim links
  - export/import tests for local-only limitation rendering
- Done when:
  - handoff packages do not silently depend on evidence that did not travel

### GBX-1732: Add Recipient-Oriented Export Profiles

- Status: `DONE`
- Depends on: `GBX-1722`, `GBX-1731`
- Goal: make export output match the recipient's intent and role
- Deliverables:
  - export profiles for review-only, continue-work, verification-needed,
    failure-triage, release-signoff, future-self, and fork-recommended
  - profile-specific required sections, optional sections, safe commands,
    non-claims, and local-only evidence treatment
  - CLI flags such as `--intent`, `--recipient`, `--expected-custodian`,
    `--exported-by`, `--note`, and `--format`
  - compatibility behavior for existing `session export` and `changeset export`
    commands
- Implementation notes:
  - maintain old defaults as stable aliases where possible
  - profile changes should affect package shape through typed fields, not
    copy-pasted prose branches
- Tests and validation included in task:
  - CLI integration tests for each profile
  - package schema tests for required and omitted sections
  - docs examples for ordinary code review and future-self handoff
- Done when:
  - operators can produce packages that are clearly intended for the recipient's
    next action

### GBX-1733: Generate Human Markdown Handoff Summaries

- Status: `DONE`
- Depends on: `GBX-1732`
- Goal: provide readable handoff summaries without losing the stable JSON
  contract
- Deliverables:
  - Markdown renderer for handoff packages
  - sections for objective, source, recipient intent, current posture,
    evidence included, local-only evidence, stale/missing evidence, accepted
    risks, safe first commands, recipient checklist, non-claims, and redaction
    summary
  - `--markdown-output` support where appropriate
  - export-inspect rendering for package review
- Implementation notes:
  - JSON remains the stable contract; Markdown is a human render target
  - keep Markdown reviewer-safe by default
- Tests and validation included in task:
  - snapshot-style tests for deterministic Markdown
  - redaction tests proving raw logs and secret-like strings are absent
- Done when:
  - recipients can read a package summary without opening raw JSON

---

## Phase 174: Import Triage, Custody, And Follow-Up

### GBX-1740: Add Handoff Import Triage

- Status: `DONE`
- Depends on: `GBX-1711`, `GBX-1731`
- Goal: turn package import into a safe inspection workflow
- Deliverables:
  - import triage service with package compatibility, source summary,
    recipient intent, included evidence, local-only omissions, redaction
    posture, digest validation, unsupported sections, safe first commands, and
    recommended next disposition
  - CLI command or import subcommand output for triage without importing
  - durable imported-package inspection records when a package is imported
  - tests for valid, legacy, unsupported, tampered, missing-section, and
    local-only-heavy packages
- Implementation notes:
  - import triage must not create live mutable state by default
  - unsupported future packages should fail safely with inspection guidance
  - digest checks validate package integrity, not source workspace truth
- Tests and validation included in task:
  - unit tests for triage states
  - integration tests for `session import` and package inspect flows
- Done when:
  - a recipient can decide whether to inspect, accept, fork, reject, or archive
    a package before acting on it

### GBX-1741: Record Handoff Acceptance, Rejection, And Custody Decisions

- Status: `DONE`
- Depends on: `GBX-1712`, `GBX-1740`
- Goal: make the recipient's decision auditable local workflow state
- Deliverables:
  - CLI/API actions for accepting custody, rejecting custody with reason,
    archiving a handoff, and recording follow-up intent
  - canonical events or managed artifacts for custody decisions
  - queue item integration for handoff awaiting recipient, accepted needs
    follow-up, rejected needs sender review, and archived historical handoff
  - dashboard action states
- Implementation notes:
  - custody acceptance is not review approval or permission
  - rejection should preserve a reason and safe next command, not delete the
    package record
- Tests and validation included in task:
  - store/projection tests for custody events
  - CLI/API integration tests for accept/reject/archive
  - queue ranking tests for custody rows
- Done when:
  - handoff decisions become inspectable local evidence instead of out-of-band
    chat messages

### GBX-1742: Add Fork-Or-Continue Guidance For Imported Handoffs

- Status: `DONE`
- Depends on: `GBX-1740`, `GBX-1741`
- Goal: help recipients choose a safe local continuation path
- Deliverables:
  - guidance service that explains whether to inspect only, fork from imported
    history, continue in a new local session, refresh repository intelligence,
    run verification, or reject the handoff
  - safe commands for each path
  - explicit blockers for stale repository state, incompatible package schema,
    missing local-only evidence, missing artifacts, unresolved approval,
    unsupported live continuation, and policy mismatch
  - CLI and dashboard display
- Implementation notes:
  - imported historical sessions remain inspection-only unless a separate
    explicit fork or new-session workflow is used
  - do not attempt to resume provider streams or imported live turns
- Tests and validation included in task:
  - unit tests for recommendation states
  - integration tests for imported completed, failed, paused, and changeset
    packages
- Done when:
  - the recipient sees the safest local path before mutating anything

---

## Phase 175: CLI, API, TUI, And Dashboard Handoff Cockpit

### GBX-1750: Add Handoff CLI Command Family And Command Guide Coverage

- Status: `DONE`
- Depends on: `GBX-1732`, `GBX-1741`
- Goal: expose local handoff as a coherent command family
- Deliverables:
  - `glassbox handoff prepare`
  - `glassbox handoff inspect`
  - `glassbox handoff import`
  - `glassbox handoff accept`
  - `glassbox handoff reject`
  - `glassbox handoff archive`
  - `glassbox handoff list`
  - command tree and command guide updates
  - compatibility links from existing `session export`, `session import`,
    `changeset export`, and `changeset handoff-readiness`
- Implementation notes:
  - avoid duplicating implementation behind old and new commands; use shared
    services
  - keep old command aliases where they are established operator paths
- Tests and validation included in task:
  - CLI parser tests
  - command tree/guide tests
  - integration smoke for core commands
- Done when:
  - operators can discover handoff workflows without knowing which legacy
    command owns each slice

### GBX-1751: Add Handoff API Routes And OpenAPI Types

- Status: `DONE`
- Depends on: `GBX-1750`
- Goal: expose handoff preparation, inspection, import triage, custody actions,
  and readiness through typed API responses
- Deliverables:
  - FastAPI routes for handoff list, prepare preview, export action, package
    inspect, import triage, accept, reject, archive, and readiness
  - response/request models with shared vocabulary
  - generated OpenAPI and frontend API types
  - route error handling for unsupported packages, redaction failures, missing
    source state, and runtime owner conflicts
- Implementation notes:
  - runtime services stay transport-agnostic
  - route actions must not import or export raw evidence beyond the package
    contract
- Tests and validation included in task:
  - web route integration tests
  - OpenAPI schema tests
  - frontend generated-type tests
- Done when:
  - dashboard and external local clients can use handoff workflows through
    stable typed APIs

### GBX-1752: Build Dashboard Local Handoff Cockpit

- Status: `TODO`
- Depends on: `GBX-1751`
- Goal: make handoff readable and actionable from the local dashboard
- Deliverables:
  - handoff cockpit surface with package/source selector, readiness summary,
    redaction preview, local-only inventory, recipient intent, safe first
    commands, import triage, custody actions, and follow-up queue rows
  - integration with workspace overview, session inspector, changeset detail,
    task autonomy, evidence graph, and operator queue
  - action feedback and disabled states for unsupported or unsafe flows
  - responsive and keyboard-accessible UI
- Implementation notes:
  - frontend stores own transport; components own presentation and local
    interaction state
  - do not expose raw logs, raw transcripts, screenshots, or secrets in the UI
  - maintain dashboard as a projection, not source of truth
- Tests and validation included in task:
  - frontend unit tests for stores and components
  - Playwright smoke for prepare, preview, inspect, and accept/reject flows
  - frontend lint, typecheck, and build
- Done when:
  - dashboard users can prepare or receive a handoff without losing the safety
    boundaries visible in CLI

### GBX-1753: Add TUI Handoff Entry Points

- Status: `TODO`
- Depends on: `GBX-1750`
- Goal: make handoff available from the primary conversational surface
- Deliverables:
  - TUI commands or palette actions for handoff readiness, prepare preview,
    package inspect, accept/reject, and safe first commands
  - compact handoff summary rendering in the terminal transcript
  - queue integration for handoff rows
- Implementation notes:
  - keep TUI output compact and inspection-first
  - avoid turning TUI actions into hidden export/import mutations
- Tests and validation included in task:
  - TUI command tests
  - terminal rendering tests
  - command-guide alignment tests
- Done when:
  - an operator can start a handoff from chat/TUI without switching mental
    models

---

## Phase 176: Replay, Eval, Package, And Release Evidence

### GBX-1760: Add Deterministic V17 Handoff Eval Cases

- Status: `TODO`
- Depends on: `GBX-1753`
- Goal: promote stable local handoff behavior into deterministic eval coverage
- Deliverables:
  - eval cases for session handoff readiness, redaction preview, local-only
    inventory, recipient export profile, import triage, custody accept/reject,
    fork-or-continue guidance, and reviewer-safe handoff bundle
  - coverage manifest updates for v17 capabilities
  - release-candidate profile membership and budget review
  - recommendation tests for changed v17 paths
- Implementation notes:
  - promote only deterministic behavior into blocking profiles
  - keep advisory dashboard/browser/accessibility evidence separate
  - document intentional baseline refreshes
- Tests and validation included in task:
  - `uv run glassbox eval run --profile release-candidate --cwd .`
  - `uv run glassbox eval audit --profile release-candidate --cwd .`
  - focused eval unit tests
- Done when:
  - release reviewers can see deterministic eval coverage for core v17 handoff
    contracts

### GBX-1761: Add V17 Release Gate

- Status: `TODO`
- Depends on: `GBX-1760`
- Goal: provide one deterministic release-gate command for v17 local handoff
- Deliverables:
  - `scripts/validate_v17_release_gate.py`
  - inherited v16 gate coverage plus v17-specific evals, handoff package smoke,
    redaction preview smoke, import triage smoke, custody smoke, CLI/API/frontend
    smoke, package contents, installed smoke, and advisory evidence separation
  - release summary output with skipped advisory evidence clearly separated
    from blocking deterministic checks
  - tests for gate planning and dry-run behavior
- Implementation notes:
  - deterministic release authority remains tests, replay, eval, package, and
    smoke evidence
  - dashboard/browser, accessibility, provider, dogfooding, and manual evidence
    remain advisory unless a fixture-backed task promotes a narrow contract
  - support dry-run output for local planning
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_v17_release_gate.py`
  - `uv run python scripts/validate_v17_release_gate.py --dry-run`
  - final full gate before release signoff
- Done when:
  - one command can produce retained v17 release evidence without conflating
    advisory confidence with deterministic authority

### GBX-1762: Harden Package Contents And Installed-Smoke Paths

- Status: `TODO`
- Depends on: `GBX-1761`
- Goal: ensure v17 local handoff ships correctly in wheel, sdist, and installed
  environments
- Deliverables:
  - package-content validation for v17 docs, scripts, eval fixtures, generated
    API files, web routes, runtime modules, and dashboard static assets
  - installed-wheel smoke for handoff command help, handoff inspect, handoff
    readiness, and package compatibility inspection
  - release-packaging documentation updates
- Implementation notes:
  - keep generated frontend static assets fresh when dashboard changes
  - preserve importability without local source tree assumptions
- Tests and validation included in task:
  - package-content tests
  - installed-wheel smoke tests
  - frontend build/package checks when dashboard changes
- Done when:
  - v17 handoff works from an installed package, not only from the repository
    checkout

### GBX-1763: Run V17 Local Handoff Dogfooding

- Status: `TODO`
- Depends on: `GBX-1762`
- Goal: exercise v17 on real local handoff scenarios and disposition findings
- Deliverables:
  - `docs/v17-dogfooding-summary.md`
  - retained local sessions for future-self handoff, review-only handoff,
    verification-needed handoff, failure-triage handoff, import triage,
    custody accept/reject, local-only evidence preview, and release-signoff
    handoff
  - findings grouped by fix now, docs, tests/evals, accepted risks, and
    post-v17 follow-ups
  - explicit residual-risk list
- Implementation notes:
  - do not expand scope during dogfooding; file follow-up tasks instead
  - preserve local-only evidence and redaction boundaries
  - include at least one unsupported, stale, local-only-heavy, or rejected
    handoff if practical
- Tests and validation included in task:
  - focused commands used during dogfooding
  - `uv run python scripts/validate_v17_release_gate.py --dry-run`
- Done when:
  - real use confirms handoff is understandable and safer, or names bounded
    residual risks before release

### GBX-1764: Publish V17 Local Handoff Release-Candidate Guide

- Status: `TODO`
- Depends on: `GBX-1763`
- Goal: publish the operator guide for the supported v17 release-candidate
  operating model, evidence expectations, residual risks, and release decision
- Deliverables:
  - `docs/v17-release-candidate.md`
  - README and docs hub updates if v17 becomes the latest release-candidate
    guide
  - release-candidate checklist, validation path, advisory evidence
    expectations, residual risks, deliberate non-goals, and explicit GO/NO-GO
    decision
  - package, installed smoke, dashboard asset, eval, handoff dogfooding, and
    release-gate evidence references
- Implementation notes:
  - keep the guide operator-readable
  - name remaining non-goals and known residual risks clearly
  - do not imply hosted review, PR automation, automatic publication,
    automatic command approval, or raw evidence portability
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_release_candidate_docs.py -q`
  - `uv run python scripts/validate_v17_release_gate.py`
  - docs link review
- Done when:
  - the repository has a clear v17 release-candidate story with evidence,
    residual-risk list, and explicit decision

## V17 Release-Candidate Readiness Checklist

- The v17 local handoff contract is published and discoverable.
- Current handoff, export, import, review bundle, readiness, redaction, and
  custody surfaces have a source-linked audit and v17 dispositions.
- Shared handoff intent, readiness, recipient, custody, package, compatibility,
  redaction, and local-only evidence models are used by major surfaces.
- Session, task, changeset, workspace, and release handoff readiness can explain
  support, blockers, local-only evidence, stale evidence, accepted risks, and
  safe inspection commands.
- Redaction preview and local-only evidence inventory run before export and are
  reflected in package manifests.
- Handoff packages carry schema version, compatibility, digest, redaction,
  local-only, non-claim, recipient-intent, and source metadata.
- Import triage validates package integrity and compatibility before creating or
  acting on local state.
- Custody accept, reject, archive, and follow-up decisions are durable local
  workflow evidence, not remote permissions.
- CLI, API, TUI, dashboard, command guide, generated types, and package
  contents are fresh.
- Dashboard and TUI surfaces expose handoff readiness, redaction preview, import
  triage, custody, and safe commands without exposing raw private evidence.
- Operator queue includes relevant handoff and custody items without turning
  advisory handoff rows into release blockers.
- Deterministic v17 evals and release gate pass.
- Dogfooding findings are dispositioned as fixes, docs, tests/evals, accepted
  risks, or post-v17 follow-ups.

## Deliberate V17 Non-Goals

These may be revisited in future milestones only with a new product contract,
authority model, evidence policy, and release gate:

- hosted accounts, authentication, authorization, roles, organization
  membership, or remote custody enforcement
- hosted task queues, hosted review state, cloud evidence storage, remote
  session sync, remote repository indexing, remote worker fleets, or remote
  workspace authority
- simultaneous multi-writer sessions or custody metadata as a runtime lock
- automatic staging, committing, pushing, pull request creation, merging,
  deployment, package publication, or repository history mutation
- treating handoff acceptance, custody, reviewer-safe bundles, local-only
  evidence, review feedback, manual evidence, repository intelligence, memory,
  browser evidence, accessibility evidence, or provider canaries as approval
  authority
- silently resuming imported live turns, provider streams, tool executions, or
  approval decisions
- replacing deterministic release gates with handoff packages, dashboard,
  browser, accessibility, provider, dogfooding, or manual evidence
- exporting raw `.glassbox` databases, raw transcripts, raw command logs, raw
  artifacts, raw diffs, screenshots, secrets, or credentials by default
- making import merge into an existing live session automatically
- adding GitHub, PR, issue tracker, or hosted-review integration as part of v17
  local handoff
