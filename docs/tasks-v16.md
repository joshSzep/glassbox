# Glassbox v16 Tasks

For the docs hub and operator guides, start at [README.md](./README.md). This
file is the v16 task graph for compressing Glassbox operator workflows after
the v15 repository intelligence milestone.

## Purpose

This document defines Glassbox v16: operator flow compression.

It is written in the same execution style as [tasks-v1.md](./tasks-v1.md)
through [tasks-v15.md](./tasks-v15.md): explicit dependencies, small vertical
slices, concrete deliverables, and quality requirements attached directly to
the work.

The v12 through v14 milestones made local changes reviewable: changesets,
review feedback, fixups, manual evidence, advisory browser and accessibility
evidence, lifecycle briefs, handoff readiness, and command evidence became real
operator surfaces. The v15 milestone then made Glassbox less forgetful about
the repository: local repository intelligence, command recipes, path-to-
verification guidance, topology, memory-derived repository knowledge,
freshness posture, dashboard repository inspection, and replay-visible context
all became richer.

The v16 goal is to make those surfaces feel like one coherent operator cockpit
instead of many powerful but separate tools. Glassbox should help the operator
answer "what should I do next, why, and what evidence supports it?" across
sessions, tasks, changesets, review feedback, repository intelligence,
verification, memory, background jobs, stale evidence, and release posture.

The v16 work should optimize for eight outcomes:

- define a unified next-action model that can rank safe, local, evidence-backed
  operator actions across sessions, tasks, changesets, repository intelligence,
  verification, memory, and maintenance surfaces
- introduce an evidence graph that connects claims, recommendations, commands,
  artifacts, events, memory entries, verification checks, review feedback,
  repository intelligence sources, and limitations
- make verification planning feel like a guided workflow: plan checks, explain
  why they matter, record skipped/stale/manual evidence, and run explicit
  operator-selected commands without creating hidden automation
- compress the local change path from "changed files exist" to "reviewable,
  verified enough, and handoff-ready" with fewer context switches
- expose one operator queue that prioritizes blocked turns, pending approvals,
  unanswered questions, failed jobs, stale evidence, unresolved review
  feedback, stale repository intelligence, and verification gaps
- make CLI, TUI, dashboard, and API surfaces use the same next-action and
  evidence language
- keep maintenance and recovery cues close to the work instead of hiding them
  behind separate expert-only commands
- preserve Glassbox's local-first, event-sourced, replay-aware, operator-
  controlled authority model while making daily work feel sharper and calmer

The v16 thesis is:

- v15 made Glassbox know more; v16 should help Glassbox guide better
- next actions are recommendations, not permission grants or hidden mutation
- every recommendation should name supporting evidence, missing evidence,
  stale inputs, limitations, and the safest useful command
- the dashboard should become the evidence explorer and queue cockpit, while
  the TUI remains the primary conversational surface
- verification orchestration should reduce ambiguity without pretending that a
  check ran before it actually ran
- maintenance and recovery should be part of normal operator flow, not a
  separate panic room
- publication, staging, committing, pushing, PR creation, merge, deploy, and
  package release remain explicit operator actions outside v16 automation

## Current Baseline Before V16 Execution

Treat the following as the starting point for every task in this document:

- [v15-release-candidate.md](./v15-release-candidate.md) records the supported
  repository intelligence v2 operating model, validation path, evidence split,
  residual risks, and non-goals.
- [v15-repository-intelligence-contract.md](./v15-repository-intelligence-contract.md)
  defines repository intelligence as local, rebuildable, freshness-aware,
  provenance-backed, and advisory by default.
- [path-to-verification-recommendations.md](./path-to-verification-recommendations.md)
  defines changed-path verification guidance with command recipes, eval
  recommendations, skipped checks, stale evidence, provenance, freshness, and
  confidence.
- [runtime-context.md](./runtime-context.md) defines bounded prompt context,
  runtime notes, workspace memory, repository intelligence context, replay
  fingerprints, and context drift semantics.
- [changeset-verification-readiness.md](./changeset-verification-readiness.md),
  [review-feedback.md](./review-feedback.md), [manual-evidence.md](./manual-evidence.md),
  and [reviewer-evidence-bundles.md](./reviewer-evidence-bundles.md) define
  current local review, evidence, and handoff posture.
- [tool-policy.md](./tool-policy.md) defines approval modes, autonomy budgets,
  hard command blocks, repository policy rules, and local safety invariants.
- The CLI already exposes session, task, changeset, branch-search, memory,
  repository intelligence, replay, eval, artifacts, backup, readiness,
  observability, provider, projection, dashboard, and daemon command families.
- The dashboard already exposes workspace overview, session inspector, task
  autonomy, changeset review, branch search, memory, and repository
  intelligence surfaces.
- The runtime already records canonical events, managed artifacts, projection
  tables, replay artifacts, eval outputs, tool attempts, verification ledger
  entries, review feedback, manual evidence, workspace memory, background jobs,
  and repository intelligence snapshots.
- Next-action guidance exists in many places, but there is no single typed
  operator queue or evidence graph that connects the reason for the next action
  to the supporting local evidence.

## V16 Operator Flow Findings

Treat these findings as evidence that should steer the first implementation
slices:

- Operators can inspect rich evidence, but the evidence is spread across
  several commands and dashboard panels. The system needs one priority model
  for "what needs attention now."
- Changesets can explain local change posture, review feedback can explain
  fixup status, repository intelligence can explain likely verification, and
  eval recommendations can suggest checks, but the operator still has to stitch
  those together manually.
- Safe next actions should be generated from typed local state, not copied as
  prose fragments by each surface independently.
- Verification planning is close to becoming a product surface, but it should
  stay explicit and operator-selected. Planning a check is not running a check,
  and recommending a command is not approving it.
- Maintenance issues such as projection drift, stale repository intelligence,
  failed background jobs, artifact pressure, stale daemon ownership, and
  provider misconfiguration should appear beside affected work.
- Review and handoff workflows need better claim traceability: "why is this
  ready, stale, blocked, advisory, or risky?" should link back to events,
  artifacts, commands, memory, and repository intelligence sources.
- The next milestone should improve operator guidance and evidence
  explainability before expanding into hosted collaboration, automatic
  publication, remote indexing, or pull request automation.

## Agent Execution Rules

These rules apply to every task in this file.

1. Respect dependency order. Do not start a task until its dependencies are
   complete unless the task explicitly says it can proceed in parallel.
2. Preserve the event-sourced source-of-truth rule. Next actions, evidence
   graph edges, verification plans, queue items, maintenance cues, and
   dashboard state must be canonical events, managed artifacts, typed API
   responses, or rebuildable derived state.
3. Preserve local-first operation. Do not introduce hosted task queues, hosted
   review state, cloud indexing, remote workspaces, remote worker fleets,
   external vector-store authority, or provider-side hidden memory as v16
   release dependencies.
4. Preserve deterministic release blocking. Next-action and evidence-graph
   surfaces may improve confidence, but release authority remains
   deterministic tests, replay, eval, package, migration, unit, integration,
   CLI, API, frontend, and release-gate evidence.
5. Treat next actions as advisory unless a narrower readiness contract marks a
   state as blocking. A next action can recommend a command, but it does not
   approve, run, stage, commit, publish, or merge that command.
6. Keep verification orchestration explicit. Planning, selecting, skipping,
   running, retrying, accepting risk, and recording manual evidence must remain
   visibly distinct states.
7. Keep provenance visible. Any next action, queue item, verification plan,
   maintenance cue, or readiness claim must cite supporting evidence, missing
   evidence, stale evidence, confidence, limitations, and safe inspection
   commands when available.
8. Keep terminal and dashboard roles coherent. The TUI remains the primary
   conversational surface; the dashboard should become the richer queue,
   evidence graph, and verification cockpit.
9. Keep CLI/API/frontend language aligned. Do not let each surface invent its
   own priority labels, severity names, stale-evidence language, or safe next
   action format.
10. Do not auto-stage, auto-commit, auto-push, auto-open pull requests,
    auto-merge, deploy, publish, mutate repository history, or send evidence
    outside the local workspace as part of v16.
11. Do not turn owner hints, review feedback, response-linked fixups, manual
    evidence, browser evidence, accessibility evidence, provider canaries,
    repository intelligence, or memory into approval authority.
12. Every implementation task automatically includes:
    - automated tests for new or changed behavior
    - `ruff` formatting and lint compliance for touched Python code
    - `ty` typecheck compliance for touched Python code
    - focused `pytest` coverage for touched runtime, CLI, TUI, web, replay,
      eval, daemon, store, policy, task, verification, provider, branch-search,
      changeset, review, manual evidence, repository intelligence, memory,
      recovery, maintenance, and terminal behavior
    - frontend lint, typecheck, tests, and build when the task touches
      dashboard code, generated API types, packaged static assets, route
      assumptions, or frontend stores
    - documentation updates when operator-visible behavior, evidence posture,
      verification posture, recovery behavior, policy behavior, release
      posture, or public workflow claims change

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
  contents, and release posture
- new next-action, queue, evidence graph, or verification-plan claims are
  backed by deterministic local inputs, canonical events, managed artifacts,
  typed API responses, or eval fixtures
- new guidance starts with safe inspection before mutation
- skipped, stale, missing, manual-only, advisory, and accepted-risk states are
  visible rather than hidden under optimistic copy
- no meaningful next-action, evidence graph, verification plan, maintenance
  cue, readiness, or handoff state exists only in memory once a task claims
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
    tasks-v16.md
    v16-operator-flow-compression-contract.md
    evidence-graph.md
    verification-orchestrator.md
    dashboard.md
    interactive-workflows.md
    replay-evals.md
    changeset-verification-readiness.md
    reviewer-evidence-bundles.md
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
    routing/
    state/
    stores/
    tests/
    e2e/
tests/
    integration/
    unit/
evals/
    bundles/
    cases/
    coverage.json
    impact.json
    recipes.json
    profiles.json
```

## Recommended Validation Commands

Use focused validation while implementing each task. The default backend slice
should include:

```bash
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run pytest -m "not daemon and not subprocess and not timeout and not tui and not slow"
```

When a task touches next-action ranking, evidence graph derivation,
verification planning, changesets, tasks, repository intelligence, memory, or
maintenance posture, also run focused tests for those surfaces:

```bash
uv run pytest tests/unit/test_task_query_derivation.py
uv run pytest tests/unit/test_changeset_verification_readiness.py
uv run pytest tests/unit/test_eval_recommendations.py
uv run pytest tests/unit/test_repository_index.py
uv run pytest tests/unit/test_workspace_memory_capture.py
uv run pytest tests/unit/test_review_briefs.py
uv run pytest tests/integration/test_observability_status.py
uv run pytest tests/integration/test_cli_changeset_commands.py
uv run pytest tests/integration/test_web_session_aggregate.py
```

When a task touches frontend operator queues, evidence graph panels,
verification plan panels, session inspector, changeset console, or workspace
overview, also run:

```bash
pnpm --dir frontend api:generate
pnpm --dir frontend format:check
pnpm --dir frontend lint
pnpm --dir frontend typecheck
pnpm --dir frontend test
pnpm --dir frontend build
```

When a task touches eval cases, profiles, impact rules, recipes, or release
gates, also run:

```bash
uv run glassbox eval audit --cwd .
uv run glassbox eval recommend src/glassbox/runtime/changeset_verification_readiness.py --cwd .
uv run glassbox eval run --profile release-candidate --cwd .
```

Once `GBX-1681` exists, use the v16 gate as the canonical full validation
command:

```bash
uv run python scripts/validate_v16_release_gate.py
```

## Task Graph

---

## Phase 160: Operator Flow Contract And Baseline Audit

### GBX-1600: Define The v16 Operator Flow Compression Contract

- Status: `DONE`
- Depends on: `GBX-1583`
- Goal: publish the operator and contributor contract for unified next
  actions, evidence graph, verification orchestration, and maintenance-aware
  flow compression
- Deliverables:
  - `docs/v16-operator-flow-compression-contract.md`
  - contract sections for scope, vocabulary, supported workflow set, evidence
    expectations, next-action authority, verification orchestration,
    maintenance posture, release authority, safety rules, and non-goals
  - explicit mapping back to [v15-repository-intelligence-contract.md](./v15-repository-intelligence-contract.md),
    [path-to-verification-recommendations.md](./path-to-verification-recommendations.md),
    [tool-policy.md](./tool-policy.md), [review-feedback.md](./review-feedback.md),
    and [runtime-context.md](./runtime-context.md)
  - definition of "next action", "evidence graph", "verification plan",
    "operator queue", "maintenance cue", and "claim support"
  - rule that next actions are advisory, local, inspectable, and never command
    approval by themselves
- Implementation notes:
  - keep the contract operator-readable rather than only engineering-facing
  - explicitly distinguish planning, recommending, selecting, executing,
    skipping, accepting risk, and publishing
  - do not introduce hosted collaboration, remote queues, or PR automation
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_release_candidate_docs.py -q`
  - focused docs link review
- Done when:
  - contributors can read one contract and understand how v16 compresses local
    workflows without weakening Glassbox authority boundaries

### GBX-1601: Audit Current Next-Action And Evidence Surfaces

- Status: `DONE`
- Depends on: `GBX-1600`
- Goal: establish a source-linked baseline of every current place that emits
  next-action, readiness, verification, recovery, or evidence-support language
- Deliverables:
  - `docs/v16-operator-flow-audit.md`
  - audit of session status, task detail, changesets, review feedback,
    handoff readiness, repository intelligence, eval recommendations,
    observability, readiness, daemon jobs, artifact GC, backup, projection
    health, dashboard overview, TUI, and command guide surfaces
  - inventory of current priority labels, blocker names, stale-evidence
    language, safe next actions, limitations, and accepted-risk copy
  - explicit "unify now", "preserve local copy", "document only", "accepted
    risk", and "not v16" dispositions
- Implementation notes:
  - distinguish typed state from prose-only next-action strings
  - identify duplicated derivation before proposing new abstractions
  - do not implement new operator queue behavior in this task
- Tests and validation included in task:
  - docs review against command help, API responses, frontend surfaces, and
    current source modules
  - `uv run pytest tests/unit/test_release_candidate_docs.py -q`
- Done when:
  - v16 implementers know which guidance surfaces must converge and which
    local wording should remain domain-specific

### GBX-1602: Update Documentation Discovery For v16

- Status: `DONE`
- Depends on: `GBX-1600`, `GBX-1601`
- Goal: make the v16 plan, contract, audit, and later evidence docs
  discoverable from the documentation hub
- Deliverables:
  - docs hub update linking this task graph, v16 contract, and v16 audit
  - root README update if v16 becomes the active planning track
  - guide-map additions for next actions, evidence graph, verification
    orchestrator, operator queue, and maintenance-aware flow compression as
    they land
  - docs guardrails if existing release-candidate documentation tests need to
    recognize v16 docs
- Implementation notes:
  - keep task docs separate from operator guides
  - do not overpromise v16 outcomes before implementation tasks are complete
  - make the v16 discovery path clear for both operators and contributors
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_release_candidate_docs.py -q`
  - docs link review
- Done when:
  - a contributor can discover the v16 operator flow plan from the docs index
    without knowing this filename

---

## Phase 161: Next-Action Model And Evidence Graph Foundation

### GBX-1610: Define Typed Next-Action Models

- Status: `DONE`
- Depends on: `GBX-1601`
- Goal: create a shared typed model for safe next actions that can be reused
  by CLI, API, dashboard, TUI, review briefs, handoff summaries, and release
  evidence
- Deliverables:
  - core or runtime models for next-action identity, target, kind, priority,
    severity, safety class, command recipe, supporting evidence, missing
    evidence, stale evidence, limitations, and recommended surface
  - stable priority vocabulary for blocked, action-needed, degraded,
    recommended, optional, historical, and maintenance-only actions
  - serialization rules for API responses and reviewer-safe artifacts
  - compatibility helpers for existing prose next-action fields
- Implementation notes:
  - avoid forcing every domain into one generic string field
  - preserve domain-specific detail while normalizing common priority and
    evidence fields
  - do not change command behavior in this task unless needed for model tests
- Tests and validation included in task:
  - model serialization tests
  - `uv run pytest tests/unit/test_core_models.py tests/unit/test_service_contracts.py`
- Done when:
  - Glassbox has one reusable next-action contract that can represent current
    guidance without losing domain meaning

### GBX-1611: Define Evidence Graph Models And Claim Support Semantics

- Status: `DONE`
- Depends on: `GBX-1610`
- Goal: define how claims and recommendations link back to local evidence
  without requiring raw transcript, raw artifact, or raw command-log exposure
- Deliverables:
  - `docs/evidence-graph.md`
  - typed evidence graph models for nodes, edges, claim support, confidence,
    provenance, freshness, limitation, redaction posture, and reviewer-safe
    visibility
  - node kinds for events, artifacts, commands, tool attempts, verification
    checks, review feedback, manual evidence, memory entries, repository
    intelligence sources, eval cases, background jobs, and release-gate rows
  - edge kinds for supports, contradicts, supersedes, makes-stale, verifies,
    skipped-by, accepted-risk-for, derived-from, and safe-next-action-for
- Implementation notes:
  - the evidence graph is a derived view over local evidence, not a second
    source of truth
  - keep raw blobs behind existing artifact and redaction boundaries
  - design for partial graphs when older sessions lack newer evidence
- Tests and validation included in task:
  - model serialization and redaction tests
  - `uv run pytest tests/unit/test_manual_evidence.py tests/unit/test_review_briefs.py`
- Done when:
  - Glassbox can express why a claim is supported, stale, contradicted, or
    manual-only in a typed, inspectable way

### GBX-1612: Build Evidence Graph Derivation For Existing Session And Changeset Evidence

- Status: `DONE`
- Depends on: `GBX-1611`
- Goal: derive an initial evidence graph from existing canonical events,
  projections, and managed artifacts for sessions and changesets
- Deliverables:
  - runtime evidence graph builder over transcript events, tool attempts,
    command evidence, verification ledger, review feedback, manual evidence,
    changeset inventory, review briefs, handoff readiness, and repository
    intelligence links
  - query helpers for graph summary, claim support, evidence neighborhood, and
    reviewer-safe graph slices
  - graceful behavior for older sessions with sparse event families
  - tests for supported, stale, skipped, manual-only, and accepted-risk claims
- Implementation notes:
  - prefer derived query helpers over new projection tables unless performance
    evidence requires materialization
  - keep graph construction bounded and paginated
  - avoid raw artifact reads unless a summary artifact already exists
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_review_briefs.py tests/unit/test_handoff_readiness.py`
  - `uv run pytest tests/integration/test_changeset_projection.py`
- Done when:
  - changeset and session views can ask "what evidence supports this claim?"
    without manually traversing unrelated repositories

### GBX-1613: Add Evidence Graph API And CLI Inspection

- Status: `DONE`
- Depends on: `GBX-1612`
- Goal: expose evidence graph summaries through scriptable CLI and typed API
  surfaces before building dashboard UX
- Deliverables:
  - CLI commands for inspecting evidence graph summaries for a session,
    changeset, task, or verification plan
  - API routes for evidence graph summary, claim support, node detail, and
    bounded neighborhood queries
  - OpenAPI and generated frontend type updates
  - JSON and human-readable output for stale, unsupported, manual-only, and
    accepted-risk claims
- Implementation notes:
  - reuse existing session and changeset route families where practical
  - keep response models transport-owned and derivation runtime-owned
  - avoid returning raw artifacts by default
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_cli_changeset_commands.py tests/integration/test_web_changeset_routes.py`
  - `uv run pytest tests/integration/test_openapi_schema.py`
  - `pnpm --dir frontend api:generate`
- Done when:
  - operators and dashboard clients can inspect evidence support without
    reverse-engineering raw event logs

---

## Phase 162: Unified Operator Queue And Contextual Next Actions

### GBX-1620: Define Operator Queue Aggregation Contract

- Status: `DONE`
- Depends on: `GBX-1610`
- Goal: define one ranked operator queue across sessions, tasks, changesets,
  review feedback, verification, repository intelligence, memory, daemon jobs,
  artifacts, backups, projections, provider posture, and release evidence
- Deliverables:
  - runtime contract for queue item fields, priority, stale state, owner
    surface, safe action, evidence summary, and dismissal semantics
  - rules for deduping queue items that refer to the same underlying problem
  - explicit distinction between work-blocking, review-blocking,
    verification-blocking, maintenance, advisory, and informational items
  - docs update for queue interpretation
- Implementation notes:
  - do not make optional repository intelligence absence block normal chat
  - preserve current session aggregate behavior while extending it
  - queue items are derived guidance unless a canonical event records an
    explicit operator decision
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_session_query_derivation.py tests/integration/test_web_session_aggregate.py`
- Done when:
  - all major operator attention needs can fit one queue vocabulary without
    erasing domain-specific meaning

### GBX-1621: Implement Runtime Queue Aggregator

- Status: `DONE`
- Depends on: `GBX-1620`
- Goal: build a runtime query service that produces prioritized queue items
  from existing local evidence
- Deliverables:
  - aggregation over pending approvals, unanswered questions, active turns,
    failed turns, blocked tasks, failed jobs, stale checkpoints, stale
    compactions, stale repository intelligence, unresolved review feedback,
    stale changeset inventory, stale verification, memory conflicts,
    projection drift, artifact pressure, and provider misconfiguration
  - deterministic sorting by priority, freshness, updated time, and target
  - bounded result sets with pagination and counts by queue family
  - tests for dedupe, priority, stale states, and multi-session ordering
- Implementation notes:
  - reuse existing query services instead of coupling directly to every
    projection table from one large function
  - keep expensive checks out of the hot path unless cached by existing
    projections or artifacts
  - avoid background mutation while computing the queue
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_session_query_derivation.py`
  - `uv run pytest tests/integration/test_web_session_aggregate.py tests/integration/test_observability_status.py`
- Done when:
  - Glassbox can produce one stable operator queue from local persisted state

### GBX-1622: Expose Queue Through CLI, API, And Command Guide

- Status: `DONE`
- Depends on: `GBX-1621`
- Goal: make the unified queue available to terminal, scripts, and dashboard
  clients
- Deliverables:
  - CLI command for workspace queue inspection with filters for action-needed,
    verification, review, maintenance, advisory, and historical items
  - API response fields for queue items, counts, priorities, safe actions, and
    evidence references
  - command-guide updates that point from queue items to concrete workflow
    commands
  - JSON output stable enough for release-gate and dashboard tests
- Implementation notes:
  - prefer extending existing `session aggregate`, `observability`, or
    workspace overview paths where that preserves compatibility
  - keep output concise; detailed graph inspection belongs to evidence graph
    commands
  - do not auto-run safe actions from the queue
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_command_guide.py`
  - `uv run pytest tests/integration/test_cli_session_commands.py tests/integration/test_web_session_aggregate.py`
  - `pnpm --dir frontend api:generate`
- Done when:
  - an operator can ask Glassbox what needs attention and receive the same
    ranked answer through CLI and API

### GBX-1623: Add Contextual Next Actions To Existing Status Surfaces

- Status: `DONE`
- Depends on: `GBX-1622`
- Goal: replace scattered prose-only next-action fragments with typed
  contextual next actions on high-traffic status surfaces
- Deliverables:
  - session status, task detail, changeset show, handoff readiness,
    repository status, eval recommend, observability status, and readiness
    output use shared next-action records where practical
  - safe action copy includes command, reason, evidence reference, and
    limitations
  - JSON compatibility fields retained or deprecated clearly
  - tests for old and new output paths
- Implementation notes:
  - avoid a large output rewrite that makes existing scripts unusable
  - keep human output shorter than raw JSON; link to graph or detail commands
    for depth
  - use domain-specific next actions when generic queue actions would be too
    vague
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_cli_renderer.py tests/unit/test_cli_facade_characterization.py`
  - `uv run pytest tests/integration/test_cli_task_commands.py tests/integration/test_cli_changeset_commands.py tests/integration/test_cli_repository_commands.py`
- Done when:
  - the common terminal status path tells the operator what to do next using a
    shared, evidence-backed vocabulary

---

## Phase 163: Verification Orchestrator

### GBX-1630: Define Verification Plan Lifecycle Contract

- Status: `DONE`
- Depends on: `GBX-1610`, `GBX-1611`
- Goal: define verification planning as a first-class local workflow without
  implying checks have run or been approved
- Deliverables:
  - `docs/verification-orchestrator.md`
  - lifecycle states for proposed, selected, running, passed, failed, skipped,
    stale, superseded, accepted-risk, manual-only, and blocked checks
  - typed models for verification plan entries, targets, command recipes,
    eval cases, release surfaces, evidence references, stale reasons, and
    selection rationale
  - rules for what planning can do without operator confirmation and what
    execution requires
- Implementation notes:
  - build on existing verification ledger, eval recommendation, command
    evidence, changeset readiness, and repository intelligence vocabulary
  - preserve tool policy and approval gates for command execution
  - distinguish "recommended command" from "approved command"
- Tests and validation included in task:
  - model tests
  - `uv run pytest tests/unit/test_verification_models.py tests/unit/test_eval_recommendations.py`
- Done when:
  - implementers share one contract for verification planning, selection,
    execution evidence, skips, and accepted risk

### GBX-1631: Generate Verification Plans From Changesets And Paths

- Status: `DONE`
- Depends on: `GBX-1630`
- Goal: produce reviewable verification plans from changed paths, changeset
  inventory, repository intelligence, eval metadata, command recipes, and
  stale evidence posture
- Deliverables:
  - runtime plan builder for changeset IDs and path lists
  - plan entries for unit tests, integration tests, frontend tests, eval
    profiles, release gates, package checks, advisory browser/accessibility
    evidence, provider canaries, manual evidence, and skipped checks
  - confidence and why-this explanations for each entry
  - CLI/API preview output without executing commands
- Implementation notes:
  - start with cheapest useful deterministic checks
  - keep advisory evidence visible but separate from blocking verification
  - no command execution in this task
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_eval_recommendations.py tests/unit/test_changeset_verification_readiness.py`
  - `uv run pytest tests/integration/test_cli_changeset_commands.py`
- Done when:
  - a changed-path set can produce a concrete, evidence-backed verification
    plan that operators can inspect before running anything

### GBX-1632: Record Verification Plan Selection, Skips, And Accepted Risk

- Status: `TODO`
- Depends on: `GBX-1631`
- Goal: persist operator decisions about which planned checks were selected,
  skipped, superseded, or accepted with residual risk
- Deliverables:
  - canonical events for verification plan creation and operator disposition,
    or reuse of existing verification events if they can represent the
    lifecycle cleanly
  - projection/query support for latest plan posture
  - CLI commands for selecting, skipping, superseding, and accepting risk for
    plan entries
  - evidence graph links from decisions to supporting rationale
- Implementation notes:
  - avoid marking a skipped check as passed
  - accepted risk must name rationale and scope
  - plan disposition should be local evidence, not release approval
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_core_events.py tests/integration/test_sqlite_projections.py`
  - `uv run pytest tests/integration/test_cli_changeset_commands.py`
- Done when:
  - verification planning decisions survive resume, dashboard reload, export,
    and replay inspection

### GBX-1633: Execute Explicitly Selected Safe Verification Commands

- Status: `TODO`
- Depends on: `GBX-1632`
- Goal: let operators run selected verification commands through existing tool
  policy, command evidence, and tool-attempt recording paths
- Deliverables:
  - command execution path for selected plan entries that uses existing
    approval and policy semantics
  - streaming command evidence and retained output artifacts
  - plan entry updates for running, passed, failed, timed out, cancelled, and
    stale-after-run states
  - retry guidance that preserves tool-attempt recovery semantics
- Implementation notes:
  - command recipes do not bypass approval gates
  - do not run advisory browser, provider, or accessibility checks unless
    explicitly selected and supported by existing commands
  - avoid parallel command execution unless a task explicitly defines locking
    and output isolation
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_command_tool.py tests/integration/test_tool_attempt_retry.py`
  - `uv run pytest tests/integration/test_cli_changeset_commands.py`
- Done when:
  - an operator can move from plan to retained verification evidence without
    leaving Glassbox's policy and event model

### GBX-1634: Integrate Verification Plans Into Changesets, Briefs, And Handoff

- Status: `TODO`
- Depends on: `GBX-1633`
- Goal: make verification plans the shared source for changeset verification
  posture, review briefs, handoff readiness, and evidence bundles
- Deliverables:
  - changeset detail fields for active plan, selected checks, skipped checks,
    stale checks, latest results, accepted risks, and safe next actions
  - review brief and handoff sections that summarize plan posture without raw
    command logs
  - dashboard changeset integration and generated API type updates
  - replay/eval fixtures for plan lifecycle behavior
- Implementation notes:
  - preserve existing verification ledger compatibility
  - do not claim reviewer acceptance or publication readiness because a plan
    passed
  - keep stale plan entries visible beside latest successful evidence
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_review_briefs.py tests/unit/test_handoff_readiness.py`
  - `uv run pytest tests/integration/test_web_changeset_routes.py`
  - `pnpm --dir frontend api:generate && pnpm --dir frontend test -- changeset-console.test.tsx`
- Done when:
  - changeset review can use one verification plan story from preview through
    handoff

---

## Phase 164: Change Workflow Compression

### GBX-1640: Add One-Command Changeset Workup Preview

- Status: `TODO`
- Depends on: `GBX-1623`, `GBX-1631`
- Goal: provide a non-mutating workup preview that turns current workspace
  changes into a reviewable action map
- Deliverables:
  - CLI command or changeset subcommand that previews changed paths,
    candidate changeset grouping, repository intelligence impact,
    verification plan, stale evidence, review risks, memory candidates, and
    safe next commands
  - JSON output for scripts and dashboard use
  - no source mutation, staging, committing, or command execution
  - docs update for the compressed local-change path
- Implementation notes:
  - reuse changeset derivation, inventory, path-to-verification, and queue
    logic
  - clearly label whether the preview has created a changeset or only
    inspected local changes
  - keep generated and ignored path treatment visible
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_changeset_derivation.py tests/unit/test_change_inventory.py`
  - `uv run pytest tests/integration/test_cli_changeset_commands.py`
- Done when:
  - an operator can ask "what would it take to review this workspace change?"
    and receive a bounded, non-mutating plan

### GBX-1641: Add Guided Changeset Workup Flow

- Status: `TODO`
- Depends on: `GBX-1640`, `GBX-1632`
- Goal: compress the happy path from local diff to changeset, verification
  plan, review brief, and handoff posture while keeping each mutation explicit
- Deliverables:
  - guided CLI/TUI workflow for create or refresh changeset, inspect inventory,
    create verification plan, select checks, record skips or accepted risk,
    generate brief, and inspect handoff readiness
  - explicit confirmations before each durable event or command execution
  - recovery behavior when a step fails or becomes stale
  - command-guide and interactive help updates
- Implementation notes:
  - guided does not mean automatic publication
  - keep the workflow resumable from persisted state
  - preserve plain CLI equivalents for every guided step
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_cli_interactive_client.py tests/unit/test_cli_tui_commands.py`
  - `uv run pytest tests/integration/test_cli_interactive_commands.py tests/integration/test_cli_changeset_commands.py`
- Done when:
  - the common local-review workflow takes fewer context switches while still
    leaving an event-sourced audit trail

### GBX-1642: Connect Review Feedback To Verification Plan Updates

- Status: `TODO`
- Depends on: `GBX-1634`, `GBX-1641`
- Goal: make local review feedback naturally produce fixup-oriented
  verification updates and evidence graph links
- Deliverables:
  - feedback detail can recommend plan entries affected by requested changes
  - fixup inventory can mark plan entries stale or newly required
  - response-linked evidence includes changed paths, selected checks, skipped
    checks, accepted risks, and limitations
  - dashboard and CLI next actions for resolving feedback through plan updates
- Implementation notes:
  - resolving feedback still does not imply reviewer acceptance
  - avoid forcing every feedback item to require a verification plan entry
  - keep manual evidence and accepted risk explicit
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_review_responses.py tests/unit/test_review_briefs.py`
  - `uv run pytest tests/integration/test_review_response_fixup_inventory.py`
- Done when:
  - requested changes can update verification posture without operators
    manually reconnecting feedback, changed paths, and checks

### GBX-1643: Add Reviewer-Safe Compressed Evidence Bundles

- Status: `TODO`
- Depends on: `GBX-1613`, `GBX-1634`, `GBX-1642`
- Goal: produce compact evidence bundles that explain one local change without
  leaking raw local state or forcing reviewers through the full dashboard
- Deliverables:
  - bundle format containing changeset summary, evidence graph summary,
    verification plan posture, review feedback status, manual evidence,
    repository intelligence limitations, handoff readiness, and redaction
    report
  - CLI export command and JSON/Markdown summary
  - reviewer-safe node and artifact filtering
  - import or inspect-only path for local review of a bundle
- Implementation notes:
  - do not include raw `.glassbox` database state
  - preserve local-only and manual-only labels
  - avoid naming the bundle a PR description or publication artifact
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_session_export_redaction.py tests/unit/test_review_briefs.py`
  - `uv run pytest tests/integration/test_cli_changeset_commands.py`
- Done when:
  - a reviewer-safe local package can explain what changed, what supports it,
    what was verified, and what remains risky

---

## Phase 165: Dashboard And TUI Flow Cockpit

### GBX-1650: Build Unified Dashboard Operator Queue

- Status: `TODO`
- Depends on: `GBX-1622`
- Goal: make the dashboard workspace overview prioritize the unified operator
  queue instead of forcing attention through separate panels
- Deliverables:
  - queue lane for action-needed, verification, review, maintenance, and
    advisory items
  - item detail with target, reason, safe action, evidence summary, freshness,
    confidence, and limitations
  - deep links to session, task, changeset, repository path, verification
    plan, evidence graph, job, projection, artifact, or provider detail
  - responsive and keyboard-friendly layout
- Implementation notes:
  - keep the dashboard dense and work-focused
  - do not nest cards or make a marketing-style overview
  - long commands and paths must wrap or truncate professionally
- Tests and validation included in task:
  - `pnpm --dir frontend test -- workspace-overview.test.tsx dashboard-stores.test.ts`
  - `pnpm --dir frontend lint`
  - `pnpm --dir frontend typecheck`
- Done when:
  - dashboard users can see what needs attention first and why

### GBX-1651: Build Evidence Graph Dashboard Explorer

- Status: `TODO`
- Depends on: `GBX-1613`, `GBX-1650`
- Goal: let operators inspect claim support and evidence neighborhoods in the
  dashboard without reading raw event logs
- Deliverables:
  - evidence graph panel for selected sessions, changesets, verification
    plans, review feedback, and handoff readiness
  - node summaries for events, artifacts, commands, verification checks,
    manual evidence, memory, repository intelligence, evals, and background
    jobs
  - filters for stale, missing, manual-only, accepted-risk, contradictory, and
    reviewer-safe evidence
  - deep links from next-action and changeset surfaces
- Implementation notes:
  - use tables, lists, and concise relationship views before attempting a
    visual graph layout
  - avoid raw artifact payload display by default
  - make empty and sparse graph states useful for older sessions
- Tests and validation included in task:
  - `pnpm --dir frontend test -- changeset-console.test.tsx session-inspector.test.ts`
  - `uv run pytest tests/integration/test_web_changeset_routes.py`
- Done when:
  - operators can answer "what supports this?" from the dashboard in one or
    two clicks

### GBX-1652: Build Verification Plan Dashboard Workflow

- Status: `TODO`
- Depends on: `GBX-1634`, `GBX-1651`
- Goal: expose verification plan preview, selection, skip, run, retry, and
  accepted-risk posture in the dashboard
- Deliverables:
  - verification plan panel with grouped deterministic, advisory, manual, and
    skipped checks
  - action states for selecting, skipping, accepting risk, running eligible
    commands, retrying failed commands, and inspecting output artifacts
  - evidence graph links for each plan entry
  - generated API type updates and frontend store actions
- Implementation notes:
  - dashboard actions must call explicit API endpoints; no local command
    execution in frontend code
  - command execution remains policy-gated by backend semantics
  - do not present skipped checks as passed
- Tests and validation included in task:
  - `pnpm --dir frontend api:generate`
  - `pnpm --dir frontend test -- changeset-console.test.tsx verification-cues.test.ts`
  - `pnpm --dir frontend typecheck`
- Done when:
  - dashboard users can manage verification posture without losing the
    distinction between planned, run, skipped, stale, and manual evidence

### GBX-1653: Add TUI Queue And Guided Flow Entry Points

- Status: `TODO`
- Depends on: `GBX-1641`, `GBX-1650`
- Goal: make the primary terminal conversation surface aware of queue items,
  guided workup flows, verification plans, and evidence graph inspection
- Deliverables:
  - TUI commands or palette entries for queue, next actions, changeset workup,
    verification plan, evidence graph, and maintenance checks
  - concise panes or detail views for selected queue items and plan entries
  - plain interactive fallbacks for non-TUI environments
  - tests for command parsing, rendering, focus, and fallback behavior
- Implementation notes:
  - keep TUI command names consistent with CLI command guide
  - do not overload the conversation transcript with huge evidence tables
  - preserve attach and daemon behaviors
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_cli_tui_commands.py tests/unit/test_cli_tui_widgets.py`
  - `uv run pytest tests/integration/test_cli_tui_review_commands.py`
- Done when:
  - the TUI can guide operators into the compressed workflow without opening a
    separate manual command reference

### GBX-1654: Add Browser And Accessibility Evidence For The Flow Cockpit

- Status: `TODO`
- Depends on: `GBX-1650`, `GBX-1651`, `GBX-1652`
- Goal: collect bounded advisory UX evidence for the operator queue, evidence
  graph, and verification plan dashboard surfaces
- Deliverables:
  - browser walkthrough evidence for queue triage, evidence graph inspection,
    verification plan actions, stale evidence, and maintenance cues
  - accessibility pairing notes for keyboard focus, focus-visible state,
    responsive layout, long-path wrapping, command text, and skipped assistive
    technology checks
  - docs or dogfooding summary updates with retained limitations and
    non-claims
- Implementation notes:
  - advisory evidence remains non-blocking unless a deterministic fixture is
    promoted
  - do not claim accessibility certification or full WCAG conformance
  - file follow-up tasks for any material usability issue
- Tests and validation included in task:
  - frontend tests for changed surfaces
  - targeted Playwright or manual browser evidence per existing advisory
    protocols
- Done when:
  - the new cockpit surfaces have fresh advisory UX evidence or explicit
    retained skips with bounded reasons

---

## Phase 166: Maintenance And Recovery In The Flow

### GBX-1660: Unify Maintenance Cue Models

- Status: `TODO`
- Depends on: `GBX-1620`
- Goal: represent maintenance and recovery needs as first-class queue and
  next-action items rather than separate expert-only diagnostics
- Deliverables:
  - typed maintenance cue models for projection drift, stale daemon owner,
    failed background jobs, artifact pressure, backup posture, stale
    repository intelligence, provider config issues, package asset staleness,
    and eval baseline drift
  - severity and urgency rules for each cue family
  - safe remediation commands and evidence references
  - docs update for maintenance cue interpretation
- Implementation notes:
  - avoid making advisory maintenance warnings block ordinary work by default
  - keep destructive cleanup behind explicit operator commands
  - reuse observability and readiness checks where possible
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_observability_status.py tests/unit/test_first_run_readiness.py`
- Done when:
  - maintenance posture can be surfaced consistently beside active work

### GBX-1661: Add Maintenance Queue Integration And Remediation Guidance

- Status: `TODO`
- Depends on: `GBX-1660`, `GBX-1621`
- Goal: integrate maintenance cues into the unified queue with precise safe
  next actions
- Deliverables:
  - queue rows for degraded projections, failed jobs, stale daemon ownership,
    artifact pressure, stale repository intelligence, backup gaps, provider
    issues, and eval drift
  - CLI/API/dashboard output for maintenance-only filters
  - safe remediation commands with policy and destructive-action warnings
  - tests for queue priority and dedupe with active work items
- Implementation notes:
  - failed background jobs tied to a session or changeset should link to that
    work item
  - artifact pruning and backup restore remain explicit operations
  - do not run remediation automatically from queue rendering
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_background_jobs.py tests/integration/test_artifact_gc.py tests/integration/test_workspace_backup.py`
  - `uv run pytest tests/integration/test_web_session_aggregate.py`
- Done when:
  - operators see maintenance risks before they corrupt confidence in active
    work

### GBX-1662: Add Recovery Playbooks As Local Evidence

- Status: `TODO`
- Depends on: `GBX-1661`
- Goal: provide structured, local recovery playbooks for common degraded states
  without automatically executing them
- Deliverables:
  - playbooks for projection rebuild, daemon restart, failed background job
    retry or abandon, artifact pressure inspection, stale repository
    intelligence rebuild, provider diagnostics, backup create or inspect, and
    eval baseline drift review
  - evidence graph links from playbooks to the degraded cue they address
  - CLI and dashboard inspection of playbook steps
  - docs update for recovery guidance
- Implementation notes:
  - playbooks are guidance, not scripts
  - destructive or externally visible remediation must remain separately
    confirmed
  - keep commands copyable and explain risk
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_command_guide.py tests/integration/test_observability_status.py`
  - frontend tests if playbook panels are added
- Done when:
  - degraded states come with actionable, inspectable recovery guidance rather
    than vague warning text

---

## Phase 167: Performance, Scale, Packaging, And Compatibility

### GBX-1670: Add Queue And Evidence Graph Performance Budgets

- Status: `TODO`
- Depends on: `GBX-1621`, `GBX-1612`
- Goal: prevent unified queue and evidence graph queries from slowing large
  workspaces, long sessions, or dense changesets
- Deliverables:
  - performance budgets for queue aggregation, graph derivation, graph
    neighborhood queries, verification plan generation, API response sizes,
    and dashboard rendering
  - pagination and truncation behavior with visible limitations
  - large-session and dense-changeset fixtures
  - docs update for scale behavior
- Implementation notes:
  - prefer bounded derived summaries over full graph expansion by default
  - avoid reading large artifact payloads in aggregate paths
  - materialize projections only when query evidence shows it is needed
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_performance_budgets.py`
  - focused large-session or dense-changeset tests
- Done when:
  - v16 surfaces remain responsive under large local evidence sets and degrade
    explicitly under limits

### GBX-1671: Harden Compatibility And Migration Paths

- Status: `TODO`
- Depends on: `GBX-1670`, `GBX-1632`
- Goal: keep older sessions, older changesets, older eval bundles, and older
  databases useful when v16 evidence and verification plan fields are absent
- Deliverables:
  - compatibility behavior for sessions without next-action records,
    verification plans, or evidence graph metadata
  - migration or projection handling if new tables are required
  - replay behavior for bundles that predate evidence graph and plan lifecycle
  - clear stale or missing posture in CLI/API/dashboard
- Implementation notes:
  - absence of v16 evidence should not make historical inspection fail
  - prefer derived compatibility shims over forced destructive migrations
  - keep schema migration names explicit if schema changes land
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_sqlite_bootstrap.py tests/integration/test_projection_rebuild.py`
  - `uv run pytest tests/unit/test_replay_orchestrator.py`
- Done when:
  - v16 features enrich new work while preserving useful inspection of older
    local evidence

### GBX-1672: Package V16 Assets And Installed-Smoke Paths

- Status: `TODO`
- Depends on: `GBX-1671`, `GBX-1652`
- Goal: ensure queue, evidence graph, verification orchestrator, generated API
  types, docs, eval fixtures, scripts, and static dashboard assets ship cleanly
- Deliverables:
  - package content validation for new docs, scripts, eval metadata, generated
    API types, and static assets
  - installed-wheel smoke coverage for queue, evidence graph, verification
    plan preview, and dashboard static assets
  - frontend release asset validation if dashboard routes change
  - docs update for source checkout and installed-package behavior
- Implementation notes:
  - installed-package users should not need Node.js to inspect packaged
    dashboard assets
  - do not package local `.glassbox` evidence graph or verification artifacts
  - keep generated API files fresh before release
- Tests and validation included in task:
  - `uv run python scripts/validate_package_contents.py`
  - `uv run python scripts/validate_frontend_release_assets.py`
  - `uv run pytest tests/unit/test_installed_wheel_smoke.py`
  - `uv run pytest tests/unit/test_packaging_metadata.py`
- Done when:
  - v16 operator flow surfaces work from both source checkout and installed
    package paths

---

## Phase 168: V16 Eval, Gate, Dogfooding, And Release Signoff

### GBX-1680: Add Deterministic V16 Eval Cases

- Status: `TODO`
- Depends on: `GBX-1643`, `GBX-1662`, `GBX-1672`
- Goal: promote stable operator flow compression behavior into deterministic
  eval coverage
- Deliverables:
  - eval cases for unified next-action ranking, evidence graph claim support,
    verification plan lifecycle, skipped check posture, changeset workup
    preview, maintenance cue surfacing, and reviewer-safe evidence bundle
  - coverage manifest updates for v16 capabilities
  - release-candidate profile membership and budget review
  - recommendation tests for changed v16 paths
- Implementation notes:
  - promote only deterministic behavior into blocking profiles
  - keep advisory dashboard/browser/accessibility evidence separate
  - document intentional baseline refreshes
- Tests and validation included in task:
  - `uv run glassbox eval run --profile release-candidate --cwd .`
  - `uv run glassbox eval audit --profile release-candidate --cwd .`
  - `uv run pytest tests/unit/test_runtime_eval_coverage.py`
- Done when:
  - release reviewers can see deterministic eval coverage for the core v16
    operator flow contracts

### GBX-1681: Add V16 Release Gate

- Status: `TODO`
- Depends on: `GBX-1680`
- Goal: provide one deterministic release-gate command for v16 operator flow
  compression
- Deliverables:
  - `scripts/validate_v16_release_gate.py`
  - inherited v15 gate coverage plus v16-specific evals, queue smoke,
    evidence graph smoke, verification plan smoke, CLI/API/frontend smoke,
    package contents, installed smoke, and advisory evidence separation
  - release summary output with skipped advisory evidence clearly separated
    from blocking deterministic checks
  - tests for gate planning and dry-run behavior
- Implementation notes:
  - deterministic release authority remains tests, replay, eval, package, and
    smoke evidence
  - browser, accessibility, provider, dogfooding, and manual evidence remain
    advisory unless a fixture-backed task promotes a narrow contract
  - support dry-run output for local planning
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_v16_release_gate.py`
  - `uv run python scripts/validate_v16_release_gate.py --dry-run`
  - final full gate before release signoff
- Done when:
  - one command can produce retained v16 release evidence without conflating
    advisory confidence with deterministic authority

### GBX-1682: Run V16 Operator Flow Dogfooding

- Status: `TODO`
- Depends on: `GBX-1681`
- Goal: exercise v16 on real local work and turn findings into fixes, docs,
  evals, accepted risks, or post-v16 follow-ups
- Deliverables:
  - `docs/v16-dogfooding-summary.md`
  - retained local sessions for queue triage, evidence graph inspection,
    verification plan lifecycle, changeset workup, review feedback fixup,
    maintenance cue recovery, and evidence bundle export
  - findings grouped by fix now, docs, tests/evals, accepted risks, and
    post-v16 follow-ups
  - explicit residual-risk list
- Implementation notes:
  - do not expand scope during dogfooding; file follow-up tasks instead
  - preserve local-only evidence and redaction boundaries
  - include at least one stale or degraded state if practical
- Tests and validation included in task:
  - focused commands used during dogfooding
  - `uv run python scripts/validate_v16_release_gate.py --dry-run`
- Done when:
  - real use confirms the v16 flow is calmer and sharper, or names bounded
    residual risks before release

### GBX-1683: Publish V16 Operator Flow Release-Candidate Guide

- Status: `TODO`
- Depends on: `GBX-1682`
- Goal: publish the operator guide for the supported v16 release-candidate
  operating model, evidence expectations, residual risks, and release decision
- Deliverables:
  - `docs/v16-release-candidate.md`
  - README and docs hub updates if v16 becomes the latest release-candidate
    guide
  - release-candidate checklist, validation path, advisory evidence
    expectations, residual risks, deliberate non-goals, and explicit
    GO/NO-GO decision
  - package, installed smoke, dashboard asset, eval, and release-gate evidence
    references
- Implementation notes:
  - keep the guide operator-readable
  - name remaining non-goals and known residual risks clearly
  - do not imply hosted review, PR automation, automatic publication, or
    command approval
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_release_candidate_docs.py -q`
  - `uv run python scripts/validate_v16_release_gate.py`
  - docs link review
- Done when:
  - the repository has a clear v16 release-candidate story with evidence,
    residual-risk list, and explicit decision

## V16 Release-Candidate Readiness Checklist

- The v16 operator flow compression contract is published and discoverable.
- Current next-action, evidence, verification, and maintenance surfaces have a
  source-linked audit and v16 dispositions.
- Shared next-action models are used by the major CLI/API/dashboard surfaces.
- Evidence graph summaries can explain claim support without exposing raw
  local state by default.
- The unified operator queue prioritizes action-needed, review, verification,
  maintenance, and advisory items consistently.
- Verification plans can be previewed, selected, skipped, executed explicitly,
  retried, marked stale, and summarized in changesets.
- Changeset workup flow compresses local review preparation without staging,
  committing, pushing, publishing, or hiding operator decisions.
- Dashboard and TUI surfaces expose the queue, evidence graph, verification
  plans, and guided flow entry points.
- Maintenance cues and recovery playbooks are visible beside affected work.
- Large-session and dense-evidence behavior stays within documented budgets.
- Older sessions and replay bundles degrade gracefully when v16 evidence is
  absent.
- Package contents, installed smoke, generated API types, and static dashboard
  assets are fresh.
- Deterministic v16 evals and release gate pass.
- Dogfooding findings are dispositioned as fixes, docs, tests/evals, accepted
  risks, or post-v16 follow-ups.

## Deliberate V16 Non-Goals

These may be revisited in future milestones only with a new product contract,
authority model, evidence policy, and release gate:

- hosted task queues, hosted review state, hosted repository indexing, remote
  workspace authority, or remote worker fleets
- automatic staging, committing, pushing, pull request creation, merging,
  deployment, package publication, or repository history mutation
- treating next actions, command recipes, owner hints, repository
  intelligence, memory, review feedback, manual evidence, browser evidence,
  accessibility evidence, or provider canaries as approval authority
- silently executing verification plans without explicit operator selection
  and existing tool-policy handling
- replacing deterministic release gates with dashboard, browser,
  accessibility, provider, dogfooding, or manual evidence
- exporting raw `.glassbox` databases, raw transcripts, raw command logs, raw
  artifacts, secrets, or credentials as reviewer-safe evidence
- introducing opaque semantic indexes, external vector-store authority, or
  provider-side hidden memory for next-action ranking
- making maintenance remediation destructive or automatic from queue rendering
- turning the dashboard into the sole source of truth for queue, evidence, or
  verification state
- adding GitHub, PR, issue tracker, or hosted-review integration as part of
  v16 flow compression
