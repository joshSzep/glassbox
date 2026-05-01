# Glassbox v12 Tasks

For the docs hub and operator guides, start at [README.md](./README.md). This
file is the v12 task graph for evolving the v11 confidence-and-adoption product
into a reviewable local change lifecycle.

## Purpose

This document defines Glassbox v12: the reviewable-change evolution after the
v11 confidence, adoption, and residual-risk closure milestone in
[tasks-v11.md](./tasks-v11.md).

It is written in the same execution style as [tasks-v1.md](./tasks-v1.md)
through [tasks-v11.md](./tasks-v11.md): explicit dependencies, small vertical
slices, concrete deliverables, and quality requirements attached directly to
the work.

The v2 through v11 work established the durable local runtime, event-sourced
SQLite store, daemon ownership model, packaged dashboard, full-screen terminal
client, cancellation, replay/eval release contracts, provider diagnostics,
task plans, autonomy budgets, background jobs, workspace memory, repository
intelligence, verify-repair loops, branch search, dashboard cockpit surfaces,
checkpointed long-running work, artifact-backed context compactions,
resumable tool attempts, time-aware continuation budgets, incremental
verification, provider recovery posture, unified knowledge posture, branch
decision support, reviewer-safe handoff guidance, and v11 release evidence.

The v12 goal is not to make Glassbox more automatic for its own sake. The v12
goal is to make the output of local agent work feel like a coherent engineering
artifact: a reviewable changeset with intent, provenance, verification,
residual risk, branch-candidate rationale, commit readiness, and reviewer-safe
evidence.

The v12 work should optimize for ten outcomes:

- turn session, task, branch-search, tool, diff, and verification evidence into
  first-class local changesets
- make "ready to review", "ready to commit", and "not ready yet" evidence-backed
  states instead of prose guesses
- connect changed files to source events, task steps, branch candidates,
  verification records, compactions, artifacts, and accepted risks
- make reviewer briefs and handoff packages summarize the change, not only the
  session that produced it
- improve commit preparation without silently staging, committing, pushing, or
  merging work
- make branch-search candidate adoption safer through local worktree isolation,
  conflict/risk summaries, and explicit operator selection
- strengthen path-aware verification in monorepos and multi-package workspaces
- harden command execution evidence, purpose classification, environment
  redaction, and publish/destructive guardrails for review-bound work
- keep deterministic replay/eval release authority while adding stable
  changeset-specific contracts
- preserve local-first, operator-controlled, one-mutation-owner semantics

The v12 thesis is:

- preserve local-first operation and workspace-owned state
- preserve canonical events as the source of truth
- preserve one local mutation owner per workspace
- preserve deterministic replay and eval as release authority
- treat a changeset as a local evidence object, not a remote collaboration
  primitive
- make review and commit readiness inspectable before making it convenient
- prefer explicit operator selection over automatic merge, commit, push, or PR
  behavior
- derive change summaries from recorded evidence instead of hidden model memory
- keep reviewer-facing artifacts redacted, portable, and honest about
  non-claims
- avoid hosted orchestration, cloud code review, simultaneous multi-writer
  mutation, automatic branch merging, automatic committing, automatic pushing,
  and provider-side hidden state in this milestone

## Current Baseline Before V12 Execution

Treat the following as the starting point for every task in this document:

- [v11-release-candidate.md](./v11-release-candidate.md) records a GO decision
  for the v11 release candidate and the supported `0.10.0` operating model.
- [v11-confidence-adoption-contract.md](./v11-confidence-adoption-contract.md)
  records the supported confidence and adoption contract.
- [v11-dogfooding-summary.md](./v11-dogfooding-summary.md) records the v11
  real-use findings and candidate follow-ups.
- `glassbox session chat` remains the primary conversational surface.
- The dashboard is a packaged Next.js static export served by FastAPI.
- Runtime state is local to `.glassbox/` by default and backed by canonical
  SQLite events plus rebuildable projections.
- Replay and eval profiles live in `evals/` as repository-owned deterministic
  behavioral contracts.
- Provider diagnostics, canaries, and recommendations remain advisory.
- Long-running work is bounded local continuation, not indefinite unattended
  operation.
- Branch search compares candidates and gives decision support, but does not
  automatically merge candidates into parent history.
- Handoff summaries and reviewer evidence guidance exist, but the primary
  artifact is still session-oriented rather than changeset-oriented.
- `workspace_diff_summary`, verification recommendations, branch decision
  support, task checkpoints, tool attempts, and knowledge posture provide many
  ingredients for review readiness, but they are not unified into one change
  lifecycle.

## v12 Reviewable-Change Findings

Treat these findings as evidence that should steer the first implementation
slices:

- Glassbox can inspect local diffs, but a diff is not yet a durable changeset
  with intent, provenance, verification, risk, and review state.
- Session handoff summaries explain a run, but reviewers usually need to review
  the resulting change: what changed, why, what proved it, and what remains
  uncertain.
- Branch-search candidates can be compared, but adopting one candidate into a
  reviewable local change still requires manual reconstruction of changed
  files, risks, and verification.
- Verification recommendations are path-aware, but multi-package and monorepo
  work needs stronger topology, ownership, package, and test-target context.
- The dashboard cockpit exposes evidence well, but it does not yet provide a
  focused "review this change" surface.
- Commit preparation still depends on ordinary git habits rather than a
  Glassbox evidence summary that says whether the change is ready to commit.
- Command execution and verification output are retained, but review-bound work
  needs clearer command purpose, environment, redaction, dependency drift, and
  publish/destructive posture.
- Reviewer-safe evidence guidance exists, but there is no first-class review
  brief artifact generated from canonical local evidence.

## Agent Execution Rules

These rules apply to every task in this file.

1. Respect dependency order. Do not start a task until its dependencies are
   complete unless the task explicitly says it can proceed in parallel.
2. Preserve the event-sourced source-of-truth rule. Changesets, review briefs,
   commit readiness, worktree adoption, verification readiness, and command
   evidence must be recorded in canonical events, retained artifacts, typed API
   responses, or explicitly rebuildable derived state.
3. Preserve local-first operation. Do not introduce a hosted control plane,
   cloud code-review authority, remote worker fleet, or external service
   dependency for v12 readiness.
4. Preserve one local mutation owner per workspace. Worktree isolation may
   create local candidate spaces, but Glassbox must still avoid simultaneous
   uncoordinated mutation of the same workspace state.
5. Preserve deterministic release blocking. Live-provider, browser, and manual
   review evidence may strengthen confidence but must not replace deterministic
   replay/eval release authority unless a task explicitly defines a repeatable
   fixture-backed contract and failure policy.
6. Treat changesets as evidence, not magic summaries. A changeset should name
   changed files, source events, task steps, branch candidates, verification,
   residual risks, and limitations whenever those signals are available.
7. Do not auto-commit, auto-push, auto-open PRs, or auto-merge. v12 may prepare
   commit messages, review briefs, and readiness evidence, but final mutation
   remains explicit operator intent.
8. Keep review guidance concrete. If a change is stale, unverified, risky,
   missing provenance, or not ready to commit, terminal and dashboard surfaces
   should name the exact safe inspection or verification command before any
   mutating action.
9. Keep reviewer artifacts redacted. Review briefs, exports, and evidence
   bundles must follow existing path, secret, provider-output, artifact, and
   local-state redaction rules.
10. Make monorepo intelligence subordinate to source files and manifests.
    Topology, ownership, package, and test-target hints must carry provenance
    and freshness, and stale topology must not be presented as fact.
11. Harden command evidence without blocking ordinary local development.
    Command purpose, environment, dependency drift, and publish/destructive
    posture should be visible and policy-aware.
12. Every implementation task automatically includes:
    - automated tests for new or changed behavior
    - `ruff` formatting and lint compliance for touched Python code
    - `ty` typecheck compliance for touched Python code
    - focused `pytest` coverage for touched runtime, CLI, web, replay, eval,
      daemon, store, policy, task, compaction, verification, provider,
      branch-search, changeset, worktree, topology, review, and terminal
      behavior
    - frontend lint, typecheck, tests, and build when the task touches
      dashboard code, generated API types, packaged static assets, or route
      assumptions
    - documentation updates when operator-visible behavior, release posture,
      review posture, commit readiness, provider posture, recovery behavior,
      policy behavior, or public workflow claims change

## Completion Contract For Any Task

A task is complete only when all of the following are true:

- the implementation exists in the intended module boundary
- automated tests covering the changed behavior exist and pass
- lint, formatting, type checks, and focused tests pass for touched code
- frontend validation passes when dashboard, generated API types, or packaged
  static assets are touched
- deterministic replay/eval behavior remains stable or intentional drift is
  documented through the eval refresh workflow
- public docs are accurate against command help, API behavior, package
  contents, and release posture
- new review or commit-readiness claims are backed by retained deterministic or
  manual evidence
- new guidance starts with safe inspection before mutation
- no meaningful changeset, review, or readiness state exists only in memory
  once a task claims durability
- reviewer-facing artifacts are redacted or explicitly documented as local-only
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
pyproject.toml
README.md
scripts/
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
evals/
    bundles/
    coverage.json
    impact.json
    profiles.json
docs/
```

New v12 implementation areas should prefer focused modules rather than widening
facades. Expected new or expanded surfaces may include:

```text
src/glassbox/runtime/changesets.py
src/glassbox/runtime/change_inventory.py
src/glassbox/runtime/review_briefs.py
src/glassbox/runtime/commit_readiness.py
src/glassbox/runtime/worktree_isolation.py
src/glassbox/runtime/workspace_topology.py
src/glassbox/runtime/command_evidence.py
src/glassbox/store/sqlite_projection_changesets.py
src/glassbox/store/repository_changesets.py
src/glassbox/web/routes/changesets.py
frontend/components/console/changesets/
frontend/components/console/review-brief/
scripts/validate_v12_release_gate.py
```

The exact file names may change during implementation, but ownership
boundaries should remain explicit.

## Recommended Validation Commands

Use the narrowest viable validation after each task, but the baseline
validation pattern for completed v12 work should include:

```bash
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run pytest
pnpm --dir frontend lint
pnpm --dir frontend typecheck
pnpm --dir frontend test
pnpm --dir frontend build
uv run glassbox eval report commit-smoke push-confirmation release-candidate --cwd .
```

Once `GBX-1291` exists, use the v12 gate as the canonical full validation
command:

```bash
uv run python scripts/validate_v12_release_gate.py
```

During incremental work, use narrower commands when possible:

```bash
uv run pytest tests/unit/test_specific_module.py
uv run pytest tests/integration/test_specific_flow.py
uv run ruff check src/glassbox/path.py tests/path_test.py
uv run ty check src/glassbox/path.py
uv run glassbox eval recommend src/glassbox/runtime/changesets.py --cwd .
pnpm --dir frontend test -- changeset-console.test.tsx
pnpm --dir frontend typecheck
```

## Milestone Map

The intended v12 milestone order is:

1. v12 reviewable-change contract and baseline audit
2. changeset event model, projections, and query surfaces
3. structured diff inventory and provenance evidence
4. changeset verification readiness
5. reviewer briefs and evidence exports
6. commit readiness and local pre-commit evidence
7. worktree isolation and branch-candidate adoption
8. monorepo topology and path-aware verification
9. command evidence and policy hardening for review-bound work
10. v12 evals, dogfooding, release gate, and release-candidate guide

Each phase below corresponds to one concrete milestone.

## Task Graph

---

## Phase 120: V12 Contract And Change-Lifecycle Audit

### GBX-1200: Define The v12 Reviewable Change Lifecycle Contract

- Status: `DONE`
- Depends on: none
- Goal: publish the v12 product contract before changing behavior
- Deliverables:
  - `docs/v12-reviewable-change-contract.md`
  - supported workflow set for local changesets, review briefs, commit
    readiness, worktree isolation, branch-candidate adoption, monorepo
    topology, verification readiness, and command evidence
  - explicit non-goals for hosted code review, automatic PRs, automatic
    commits, automatic pushes, automatic merges, and indefinite unattended
    mutation
  - release-evidence expectations that distinguish deterministic blocking
    evidence from manual review, live browser, live provider, and operator
    dogfooding evidence
- Implementation notes:
  - keep the contract operator-readable
  - emphasize "reviewable local change" rather than "more autonomy"
  - preserve terminal chat as the primary creation surface and dashboard as the
    paired review/evidence surface
- Tests and validation included in task:
  - docs link review
  - release-doc guardrail updates if current tests require all active milestone
    docs to be linked
- Done when:
  - v12 has one concise product contract that later tasks can reference instead
    of restating scope

### GBX-1201: Audit Current Change, Review, And Commit Boundaries

- Status: `TODO`
- Depends on: `GBX-1200`
- Goal: ground v12 implementation in actual gaps between existing session
  evidence and reviewable changes
- Deliverables:
  - `docs/v12-change-lifecycle-audit.md`
  - source-linked audit entries for diff summary, branch search, task
    checkpoints, verification recommendations, handoff summaries, tool output
    artifacts, command execution, git status, dashboard review surfaces, and
    export/redaction behavior
  - classification of each gap as fixed in v12, evidence-only in v12, accepted
    non-goal, or carried-forward risk
  - test inventory for where change review behavior is currently covered and
    where coverage is missing
- Implementation notes:
  - separate "can inspect a session" from "can review a change"
  - keep projections and dashboard summaries non-authoritative in the audit
  - include both backend and frontend evidence paths
- Tests and validation included in task:
  - docs review against current implementation
  - no product-code change required unless the audit exposes stale docs
- Done when:
  - every known gap between session evidence and reviewable changes has an
    explicit v12 disposition

### GBX-1202: Define Changeset Vocabulary And Operator Language

- Status: `TODO`
- Depends on: `GBX-1200`, `GBX-1201`
- Goal: standardize how Glassbox names changes, review posture, commit
  readiness, and adoption decisions before adding command surfaces
- Deliverables:
  - vocabulary section in the v12 contract or a companion doc
  - definitions for changeset, change inventory, review brief, commit
    readiness, verification readiness, adopted candidate, residual risk,
    reviewer-safe evidence, and local-only evidence
  - command/dashboard copy guidelines that avoid implying automatic commit,
    push, PR, or merge behavior
- Implementation notes:
  - align with v9 vocabulary and v11 command-flow compression
  - distinguish git branch, session branch, branch-search candidate, and
    changeset clearly
- Tests and validation included in task:
  - command guide or docs guardrail tests if copy surfaces change
- Done when:
  - later tasks can use consistent names without re-litigating product language

---

## Phase 121: Changeset Domain And Projection Surface

### GBX-1210: Add Changeset Event Vocabulary

- Status: `TODO`
- Depends on: `GBX-1202`
- Goal: introduce canonical events for reviewable local changes without making
  projections authoritative
- Deliverables:
  - event payloads for changeset creation, source attachment, inventory
    refresh, verification posture update, review brief creation, readiness
    decision, candidate adoption, and changeset archival
  - correlation fields for changeset ID, task ID, session ID, turn ID, branch
    search ID, branch candidate ID, verification ID, and artifact ID where
    relevant
  - event model tests and replay normalization updates
- Implementation notes:
  - keep event payloads typed and versioned
  - avoid storing raw diffs directly in canonical event payloads; use managed
    artifacts for large or sensitive content
  - do not mutate parent session history when deriving a changeset from branch
    search
- Tests and validation included in task:
  - core event tests
  - replay model tests
  - schema-boundary tests if correlation columns are added
- Done when:
  - changeset state has a canonical vocabulary before projections or UI depend
    on it

### GBX-1211: Add Changeset Projection Schema And Rebuild Semantics

- Status: `TODO`
- Depends on: `GBX-1210`
- Goal: make changesets queryable while preserving canonical events as the
  source of truth
- Deliverables:
  - SQLite projection tables for changesets, changeset sources, inventory
    summaries, verification posture, review brief references, and readiness
    state
  - ordered schema migration
  - projection rebuild support and projection-health inspection
  - repository adapter methods behind service contracts
- Implementation notes:
  - follow existing projection-family module boundaries
  - keep detailed file inventories in artifacts if they become too large for
    projection rows
  - preserve import/export compatibility for older sessions without changesets
- Tests and validation included in task:
  - SQLite bootstrap and migration tests
  - projection rebuild tests
  - repository adapter boundary tests
- Done when:
  - changeset projections can be fully rebuilt from canonical events

### GBX-1212: Derive Changesets From Sessions, Tasks, And Branch Search

- Status: `TODO`
- Depends on: `GBX-1211`
- Goal: let operators create a changeset from existing Glassbox work without
  manually reconstructing the story
- Deliverables:
  - runtime service that creates a changeset from:
    - a session
    - a task
    - a selected branch-search candidate
    - the current workspace diff
  - source references that capture session/task/candidate provenance and
    limitations
  - safe behavior for historical, imported, incomplete, and projection-degraded
    sessions
- Implementation notes:
  - creation should be explicit operator action, not automatic for every turn
  - if evidence is missing, create a degraded changeset with clear limitations
    rather than inventing provenance
  - do not stage or mutate git as part of changeset creation
- Tests and validation included in task:
  - unit tests for source derivation
  - integration tests for session, task, branch-search, and workspace-diff
    creation paths
- Done when:
  - an operator can ask Glassbox to create one local changeset from meaningful
    existing work

### GBX-1213: Surface Changesets In CLI, API, And Dashboard Shell

- Status: `TODO`
- Depends on: `GBX-1212`
- Goal: make local changesets visible and inspectable before adding richer
  review behavior
- Deliverables:
  - CLI commands to create, list, show, refresh, and archive changesets
  - FastAPI routes and OpenAPI-generated frontend types
  - dashboard navigation entry and read-only changeset detail shell
  - status output that points from session/task/branch-search views to related
    changesets
- Implementation notes:
  - keep mutation commands explicit and confirmation-gated where appropriate
  - preserve scriptable JSON output
  - avoid adding review claims until later phases supply the evidence
- Tests and validation included in task:
  - CLI integration tests
  - API route tests and generated type freshness
  - frontend store/routing/component tests
- Done when:
  - changesets are a visible product surface with safe basic inspection

---

## Phase 122: Structured Change Inventory And Provenance

### GBX-1220: Define The Change Inventory Artifact Contract

- Status: `TODO`
- Depends on: `GBX-1212`
- Goal: record changed-file inventory as review evidence with provenance,
  redaction, and size limits
- Deliverables:
  - managed artifact schema for change inventory
  - fields for path, change kind, insertions, deletions, generated/test/docs
    classification, binary posture, policy-sensitive posture, staged/unstaged
    state, and source evidence references
  - artifact size, path-count, and redaction limits
  - docs for what inventory does and does not prove
- Implementation notes:
  - build on `workspace_diff_summary` but do not treat it as the only source of
    truth
  - avoid storing raw file contents or raw diffs unless a task explicitly adds a
    redacted diff artifact
  - make unknown states explicit
- Tests and validation included in task:
  - artifact schema tests
  - redaction and size-limit tests
  - docs examples
- Done when:
  - change inventory has a stable artifact shape before review readiness uses
    it

### GBX-1221: Attach File Provenance To Changed Paths

- Status: `TODO`
- Depends on: `GBX-1220`
- Goal: connect changed files to the Glassbox evidence that caused or explained
  them
- Deliverables:
  - provenance derivation from tool calls, apply-patch results, command
    outputs, task steps, branch candidates, checkpoints, verification records,
    and artifacts
  - confidence levels for direct, inferred, and unknown provenance
  - CLI/API fields that explain when a file lacks provenance
- Implementation notes:
  - do not require every manually edited file to have Glassbox provenance
  - distinguish externally modified files from files changed by recorded tools
  - preserve user changes and never imply ownership of unrecorded edits
- Tests and validation included in task:
  - unit tests for provenance matching
  - integration tests with mixed Glassbox and manual edits
- Done when:
  - changed files can be reviewed with source evidence or honest unknowns

### GBX-1222: Add Change Risk And Sensitivity Classification

- Status: `TODO`
- Depends on: `GBX-1221`
- Goal: summarize review risk from changed paths without replacing human
  judgment
- Deliverables:
  - risk classification for generated files, policy-sensitive paths, docs-only
    changes, tests, runtime/schema changes, provider/security-adjacent changes,
    packaging/release changes, and large/binary changes
  - accepted-risk and unresolved-risk fields on changeset summaries
  - dashboard and CLI copy that explains why a change is high risk
- Implementation notes:
  - reuse eval impact rules and repository index where possible
  - risk should be advisory and explainable, not a blocker by itself
  - stale topology or missing inventory must degrade risk confidence
- Tests and validation included in task:
  - risk classification tests
  - CLI formatter tests
  - frontend tests if dashboard risk UI changes
- Done when:
  - a changeset can explain which parts of the change deserve extra review

### GBX-1223: Refresh Change Inventory Safely

- Status: `TODO`
- Depends on: `GBX-1222`
- Goal: keep changeset inventory current without hiding workspace drift
- Deliverables:
  - refresh action that records new inventory artifacts and marks previous
    inventory freshness
  - stale inventory detection when workspace files, git status, or source
    digest changes
  - status guidance that names safe refresh commands
- Implementation notes:
  - do not overwrite old inventory artifacts silently
  - make refresh explicit when it changes review posture
  - preserve drift evidence for reviewer audit
- Tests and validation included in task:
  - refresh/staleness unit tests
  - CLI/API integration tests
- Done when:
  - reviewers can tell whether a changeset summary matches the current
    workspace

---

## Phase 123: Changeset Verification Readiness

### GBX-1230: Define Changeset Verification Readiness Model

- Status: `TODO`
- Depends on: `GBX-1223`
- Goal: turn verification recommendations and ledgers into one readiness
  posture for a local change
- Deliverables:
  - model for planned, missing, running, passed, failed, stale, skipped,
    accepted-with-risk, and not-applicable verification states
  - mapping from changed paths, risk classification, workspace profile,
    verification recipes, task verification ledger, eval recommendations, and
    command evidence
  - docs explaining readiness versus proof
- Implementation notes:
  - do not treat old passing checks as fresh when changed paths make them stale
  - distinguish "recommended but not run" from "not applicable"
  - preserve existing verification ledger semantics
- Tests and validation included in task:
  - readiness derivation tests
  - docs examples
- Done when:
  - a changeset can say what verification it needs and what evidence already
    exists

### GBX-1231: Detect Stale Verification Against Changed Paths

- Status: `TODO`
- Depends on: `GBX-1230`
- Goal: prevent stale checks from making a change look review-ready
- Deliverables:
  - stale verification detection when inventory changes after a check
  - source-range or file-digest comparison where practical
  - clear CLI/API/dashboard warnings and next actions
- Implementation notes:
  - keep stale detection deterministic and explainable
  - when precise file mapping is unavailable, report lower confidence rather
    than overclaiming staleness or freshness
- Tests and validation included in task:
  - unit tests for stale/fresh boundaries
  - integration tests for inventory refresh after verification
- Done when:
  - readiness cannot silently rely on verification that predates relevant
    changes

### GBX-1232: Add Verification Plan Preview And Evidence Capture

- Status: `TODO`
- Depends on: `GBX-1231`
- Goal: let operators preview and record verification plans for a changeset
  without auto-running arbitrary commands
- Deliverables:
  - CLI/API plan preview that names recommended commands, eval profiles,
    recipes, expected scope, and reason groups
  - optional action to record operator-selected verification evidence from
    existing task or command outputs
  - retained artifact references for verification outputs already captured by
    Glassbox
- Implementation notes:
  - preview commands only; execution remains explicit operator action through
    existing tool or shell workflows unless a later task defines a safe runner
  - do not recommend publish/deploy commands as verification
- Tests and validation included in task:
  - recommendation integration tests
  - CLI JSON compatibility tests
- Done when:
  - a reviewer can see the intended verification plan before deciding whether
    to run or trust it

### GBX-1233: Surface Ready-To-Review Verification Posture

- Status: `TODO`
- Depends on: `GBX-1232`
- Goal: make verification readiness visible where operators review changesets
- Deliverables:
  - CLI `changeset show` verification summary
  - API fields for dashboard rendering
  - dashboard verification panel with fresh, stale, failed, missing, and
    accepted-risk states
  - safe next-action commands for missing or stale verification
- Implementation notes:
  - do not bury failed verification below optimistic summaries
  - accepted residual risks must be visible beside passing checks
- Tests and validation included in task:
  - CLI formatter tests
  - API model tests
  - frontend component/store tests
- Done when:
  - ready-to-review status is backed by verification evidence instead of
    hand-written confidence

---

## Phase 124: Reviewer Briefs And Evidence Exports

### GBX-1240: Define The Review Brief Artifact Contract

- Status: `TODO`
- Depends on: `GBX-1233`
- Goal: create a reviewer-safe artifact that summarizes a local change without
  exposing raw `.glassbox` state
- Deliverables:
  - managed artifact schema for review briefs
  - sections for objective, change summary, changed-file inventory, provenance,
    verification, branch-candidate rationale, risks, non-claims, reviewer
    checklist, and safe inspection commands
  - Markdown and JSON render targets
  - redaction and retention policy
- Implementation notes:
  - the brief must cite evidence references rather than flattening raw logs
  - keep local-only artifacts clearly labeled
  - avoid leaking provider prompts, API keys, environment secrets, or raw
    command output beyond existing redaction rules
- Tests and validation included in task:
  - artifact schema tests
  - redaction tests
  - docs examples
- Done when:
  - review briefs have a stable, redacted artifact shape

### GBX-1241: Generate Review Briefs From Changeset Evidence

- Status: `TODO`
- Depends on: `GBX-1240`
- Goal: produce useful reviewer summaries from recorded local evidence
- Deliverables:
  - runtime service to generate a review brief for one changeset
  - CLI command and API action to generate or refresh a brief
  - event/projection links from changeset to latest brief artifact
  - graceful degradation when evidence is incomplete
- Implementation notes:
  - summarize what is known, unknown, stale, failed, and accepted with risk
  - do not call a model merely to make the brief sound nicer unless a future
    task defines model-backed brief generation with replay implications
  - prefer deterministic summaries first
- Tests and validation included in task:
  - unit tests for brief generation
  - CLI/API integration tests
  - export/redaction tests
- Done when:
  - a local changeset can produce a reviewer-safe brief from deterministic
    evidence

### GBX-1242: Add Dashboard Review Surface

- Status: `TODO`
- Depends on: `GBX-1241`
- Goal: make the dashboard a practical place to review the resulting change
- Deliverables:
  - changeset review route or panel
  - sections for summary, files, provenance, verification, risks, branch
    candidate rationale, brief artifacts, and safe actions
  - keyboard and responsive behavior consistent with existing console patterns
  - visual treatment that prioritizes blockers, stale evidence, failed checks,
    and accepted risks
- Implementation notes:
  - keep it a dense operator/reviewer tool, not a marketing page
  - do not embed raw huge artifacts inline; link or page them
  - preserve existing workspace overview and session inspector priority rules
- Tests and validation included in task:
  - frontend unit/component tests
  - Playwright smoke for review flow
  - frontend lint/typecheck/build
- Done when:
  - a reviewer can inspect a changeset in the dashboard without jumping across
    unrelated session panes

### GBX-1243: Add Reviewer-Safe Export Package For Changesets

- Status: `TODO`
- Depends on: `GBX-1241`
- Goal: make ordinary code-review handoff centered on the change rather than
  raw local runtime state
- Deliverables:
  - `changeset export` command or session export extension
  - package metadata with brief, inventory, verification summary, selected
    artifacts, redaction report, and non-claims
  - import or inspect-only path if useful without granting mutation authority
  - docs update in reviewer evidence and team workflow guides
- Implementation notes:
  - do not include raw `.glassbox` database state
  - export should be inspectable without assuming identical local paths
  - preserve existing session export/import behavior
- Tests and validation included in task:
  - export package tests
  - redaction tests
  - docs/package contents validation
- Done when:
  - a reviewer can receive a change-centered evidence bundle safely

---

## Phase 125: Commit Readiness And Local Pre-Commit Evidence

### GBX-1250: Define Commit Readiness Model

- Status: `TODO`
- Depends on: `GBX-1233`
- Goal: answer whether a changeset is ready to commit using local evidence
  rather than optimism
- Deliverables:
  - commit readiness states such as ready, blocked, needs-verification,
    needs-review, stale-inventory, dirty-untracked-risk, failed-checks,
    missing-provenance, and accepted-with-risk
  - mapping from inventory, staged/unstaged status, verification readiness,
    policy-sensitive paths, generated files, accepted risks, and review brief
    freshness
  - docs explaining that readiness is advisory and local
- Implementation notes:
  - do not run git commit
  - do not stage files automatically
  - make dirty workspace and untracked-file ambiguity visible
- Tests and validation included in task:
  - commit readiness unit tests
  - git status fixture tests
- Done when:
  - Glassbox can explain why a change is or is not ready to commit

### GBX-1251: Generate Evidence-Backed Commit Message Suggestions

- Status: `TODO`
- Depends on: `GBX-1250`
- Goal: draft commit messages from changeset evidence without committing
- Deliverables:
  - deterministic commit message suggestion from objective, changed paths,
    task outcome, verification, and risk classification
  - optional templates for conventional commit or repository-local style if
    profile support is appropriate
  - CLI/API output that labels the message as a suggestion
- Implementation notes:
  - do not invent facts absent from evidence
  - avoid model-backed commit messages until replay implications are explicit
  - preserve operator editing
- Tests and validation included in task:
  - commit message formatter tests
  - workspace profile tests if templates are configurable
- Done when:
  - operators get a useful commit message draft without Glassbox taking the
    commit action

### GBX-1252: Capture Pre-Commit Evidence Against Changesets

- Status: `TODO`
- Depends on: `GBX-1250`
- Goal: connect local pre-commit and eval evidence to commit readiness
- Deliverables:
  - command or workflow to record pre-commit/eval report outputs against a
    changeset
  - readiness updates when pre-commit evidence is fresh, failed, stale, or
    missing
  - retained artifact references for summary output
- Implementation notes:
  - do not make all pre-commit hooks mandatory for every changeset
  - keep existing repository pre-commit behavior unchanged unless explicitly
    invoked
  - support CI-like scriptable output
- Tests and validation included in task:
  - integration tests with fixture command outputs
  - readiness transition tests
- Done when:
  - commit readiness can cite retained local pre-commit or eval evidence

### GBX-1253: Add Commit-Preparation CLI And Dashboard Guidance

- Status: `TODO`
- Depends on: `GBX-1251`, `GBX-1252`
- Goal: make commit preparation ergonomic while keeping final git mutation
  explicit
- Deliverables:
  - CLI command to show readiness, suggested commit message, stale evidence,
    risky files, and next commands
  - dashboard commit-readiness panel
  - safe copy that avoids saying Glassbox committed, staged, pushed, or opened
    a PR
- Implementation notes:
  - mutating git commands remain outside this task unless later explicitly
    approved
  - if a future optional commit action is considered, it must be a separate
    task with approval, clean-worktree, and rollback semantics
- Tests and validation included in task:
  - CLI formatter tests
  - frontend component tests
  - docs update
- Done when:
  - Glassbox can prepare an operator to commit without performing the commit

---

## Phase 126: Worktree Isolation And Branch-Candidate Adoption

### GBX-1260: Define Local Worktree Isolation Contract

- Status: `TODO`
- Depends on: `GBX-1201`
- Goal: make branch/candidate experimentation safer without introducing remote
  or automatic merge semantics
- Deliverables:
  - `docs/worktree-isolation.md`
  - contract for temporary local git worktrees, candidate naming, cleanup,
    custody, evidence retention, and conflict boundaries
  - explicit non-goals for automatic merge, automatic rebase, automatic push,
    and multi-user locking
- Implementation notes:
  - handle repositories that do not support worktrees gracefully
  - avoid destructive cleanup unless explicitly confirmed
  - preserve existing branch-search behavior
- Tests and validation included in task:
  - docs review
  - git fixture design notes
- Done when:
  - worktree isolation has a product and safety contract before implementation

### GBX-1261: Add Temporary Worktree Creation And Cleanup Workflows

- Status: `TODO`
- Depends on: `GBX-1260`
- Goal: let Glassbox create inspectable local candidate workspaces for bounded
  experimentation
- Deliverables:
  - worktree create/list/status/cleanup commands
  - event evidence for worktree creation, path, branch name, base revision,
    owner process, and cleanup state
  - cleanup confirmation and stale-worktree recovery guidance
- Implementation notes:
  - do not delete user changes during cleanup without explicit confirmation and
    risk summary
  - reject worktree paths outside safe local roots
  - keep worktree paths redacted in exports where needed
- Tests and validation included in task:
  - git worktree integration tests with temporary repositories
  - CLI JSON tests
  - policy tests for cleanup confirmation
- Done when:
  - operators can manage temporary local candidate worktrees safely

### GBX-1262: Adopt A Selected Branch Candidate Into A Changeset

- Status: `TODO`
- Depends on: `GBX-1212`, `GBX-1261`, `GBX-1172`
- Goal: convert selected branch-search work into a reviewable changeset without
  automatic merging
- Deliverables:
  - adoption preview that summarizes candidate diff inventory, verification,
    risk, conflicts, stale evidence, and accepted risks
  - adoption event linking branch candidate to changeset
  - explicit operator confirmation before any workspace mutation
  - degraded path when candidate diff inventory or worktree state is missing
- Implementation notes:
  - preview before mutation
  - do not merge automatically as part of selection
  - preserve parent history and branch-search evidence
- Tests and validation included in task:
  - branch-search adoption tests
  - conflict/degraded-state tests
  - changeset projection tests
- Done when:
  - selected candidates can become reviewable changesets through an explicit
    adoption workflow

### GBX-1263: Surface Candidate Adoption In Dashboard Review

- Status: `TODO`
- Depends on: `GBX-1242`, `GBX-1262`
- Goal: make branch-candidate adoption understandable from the review surface
- Deliverables:
  - dashboard comparison between adopted candidate and rejected alternatives
  - adoption rationale, verification posture, conflicts, and follow-up actions
  - clear non-automatic-merge copy
- Implementation notes:
  - avoid burying missing candidate evidence
  - preserve branch-search decision support panels
- Tests and validation included in task:
  - frontend component tests
  - Playwright branch-candidate review scenario
- Done when:
  - reviewers can understand why a candidate was adopted into a changeset

---

## Phase 127: Monorepo Topology And Path-Aware Verification

### GBX-1270: Define Workspace Topology Model

- Status: `TODO`
- Depends on: `GBX-1201`
- Goal: make multi-package and monorepo structure explicit enough for
  verification and review readiness
- Deliverables:
  - topology model for packages, apps, libraries, manifests, lockfiles,
    generated outputs, test roots, docs roots, ownership hints, and dependency
    relationships
  - provenance and freshness rules
  - docs update in repository intelligence or a new topology guide
- Implementation notes:
  - topology is rebuildable local intelligence, not authority over source
    files
  - stale topology must degrade recommendations
  - support small single-package repositories without noise
- Tests and validation included in task:
  - topology model tests
  - fixture repositories for Python-only, frontend-only, and mixed workspaces
- Done when:
  - Glassbox has a typed local model for workspace structure

### GBX-1271: Build Topology From Repository Index And Manifests

- Status: `TODO`
- Depends on: `GBX-1270`
- Goal: derive topology from existing repository intelligence and deterministic
  local manifests
- Deliverables:
  - builder for pyproject, package.json, lockfiles, frontend configs, docs,
    evals, scripts, test roots, and existing repository index entries
  - stale detection when topology inputs change
  - CLI/API inspection commands
- Implementation notes:
  - reuse repository index scan/exclusion rules
  - avoid expensive full semantic analysis
  - keep generated/vendor/build outputs bounded
- Tests and validation included in task:
  - builder tests with fixture manifests
  - stale/fresh tests
  - CLI/API tests
- Done when:
  - topology can be rebuilt and inspected locally

### GBX-1272: Improve Path-To-Test And Recipe Recommendations

- Status: `TODO`
- Depends on: `GBX-1271`, `GBX-1121`
- Goal: make verification recommendations more precise for changed files in
  multi-package workspaces
- Deliverables:
  - topology-aware mapping from changed paths to test targets, eval profiles,
    build commands, package checks, frontend checks, docs checks, and release
    gates
  - confidence labels and fallback guidance
  - impact-rule integration without hard-coding every path in Python
- Implementation notes:
  - recommendations remain preview/guidance unless explicitly executed
  - low-confidence mappings must explain why they are low confidence
  - avoid recommending broad release gates when a targeted command is enough
- Tests and validation included in task:
  - recommendation unit/integration tests
  - eval impact fixture updates
  - docs examples
- Done when:
  - changed files receive better targeted verification advice from local
    topology

### GBX-1273: Feed Topology Into Changeset Readiness And Review Briefs

- Status: `TODO`
- Depends on: `GBX-1241`, `GBX-1272`
- Goal: use topology to improve changeset risk, verification readiness, and
  reviewer summaries
- Deliverables:
  - changeset fields for affected packages, dependency hints, test roots, and
    owner hints
  - review brief sections for affected subsystems and topology freshness
  - dashboard display of affected packages/subprojects
- Implementation notes:
  - stale or failed topology should be visible
  - do not invent ownership claims without provenance
- Tests and validation included in task:
  - changeset readiness tests
  - review brief tests
  - frontend tests if display changes
- Done when:
  - review readiness understands which local subsystem a change affects

---

## Phase 128: Command Evidence And Policy Hardening For Review-Bound Work

### GBX-1280: Classify Command Purpose And Review Relevance

- Status: `TODO`
- Depends on: `GBX-1201`
- Goal: make command execution evidence more useful for review and policy
  decisions
- Deliverables:
  - command purpose classes such as inspect, test, lint, typecheck, build,
    package, eval, release-gate, publish, deploy, cleanup, unknown, and
    dangerous
  - policy and review summaries that use purpose classification
  - command evidence fields attached to tool attempts or changeset
    verification when relevant
- Implementation notes:
  - destructive-command hard blocks remain invariant
  - purpose classification should be explainable and conservative
  - unknown commands should not be treated as verification proof
- Tests and validation included in task:
  - command classification tests
  - policy tests
  - CLI formatting tests
- Done when:
  - a reviewer can tell what kind of command produced a piece of evidence

### GBX-1281: Capture Redacted Environment And Toolchain Drift Evidence

- Status: `TODO`
- Depends on: `GBX-1280`
- Goal: make verification and build evidence more reproducible without leaking
  secrets
- Deliverables:
  - redacted execution environment summary for selected command purposes
  - toolchain version capture for Python, uv, node, pnpm, package managers,
    and configured test tools where practical
  - drift warnings when retained evidence no longer matches current toolchain
    posture
- Implementation notes:
  - never persist environment variables wholesale
  - redact provider keys, tokens, credentials, and local-only sensitive paths
  - keep capture bounded and opt-in by command purpose if necessary
- Tests and validation included in task:
  - redaction tests
  - toolchain drift tests
  - command evidence artifact tests
- Done when:
  - command evidence can explain the local environment enough for review
    without exposing secrets

### GBX-1282: Harden Publish, Deploy, And Destructive Command Guardrails

- Status: `TODO`
- Depends on: `GBX-1280`
- Goal: prevent review-preparation workflows from accidentally crossing into
  irreversible release or publishing actions
- Deliverables:
  - expanded command-risk classification for publish/deploy/package-upload,
    destructive cleanup, git history rewriting, and remote mutation patterns
  - approval or block behavior aligned with existing policy modes
  - operator-facing explanation and safe alternatives
- Implementation notes:
  - do not block ordinary local build/package validation
  - distinguish local package build from remote publish
  - keep repository-owned policy overrides within hard invariants
- Tests and validation included in task:
  - policy command-risk tests
  - integration tests for blocked and approval-gated commands
  - docs update in tool policy
- Done when:
  - review and commit-readiness workflows cannot accidentally publish or
    destructively rewrite work

### GBX-1283: Attach Command Evidence To Review Briefs And Changesets

- Status: `TODO`
- Depends on: `GBX-1241`, `GBX-1281`, `GBX-1282`
- Goal: make command evidence reviewable beside verification and readiness
  summaries
- Deliverables:
  - changeset command-evidence summary
  - review brief section for important commands, purpose, result, environment
    posture, artifacts, and policy decisions
  - dashboard drill-down for command evidence relevant to the change
- Implementation notes:
  - include summaries and artifact references, not giant raw logs
  - failed commands should remain visible even when later commands pass
- Tests and validation included in task:
  - review brief tests
  - frontend tests
  - redaction tests
- Done when:
  - reviewers can inspect which commands support the change and how trustworthy
    they are

---

## Phase 129: V12 Eval, Dogfooding, Gate, And Release Signoff

### GBX-1290: Add Deterministic v12 Replay And Eval Cases

- Status: `TODO`
- Depends on: `GBX-1233`, `GBX-1241`, `GBX-1253`, `GBX-1262`
- Goal: protect stable reviewable-change behavior with deterministic release
  evidence
- Deliverables:
  - compact deterministic cases or fixtures for changeset creation, inventory
    provenance, stale verification readiness, review brief generation, commit
    readiness, branch-candidate adoption, and command evidence classification
  - `evals/coverage.json` updates for promoted capabilities
  - `evals/profiles.json` release-candidate budget update if case count changes
  - docs update in [replay-evals.md](./replay-evals.md)
- Implementation notes:
  - keep browser review and live provider evidence separate unless a
    deterministic fixture exists
  - avoid bloating commit-smoke profiles
  - keep changeset fixtures compact and redacted
- Tests and validation included in task:
  - eval run for new cases
  - eval audit
  - focused unit/integration tests for new fixtures
- Done when:
  - v12 reviewable-change behavior has deterministic evidence where it can be
    made deterministic

### GBX-1291: Add v12 Release Gate

- Status: `TODO`
- Depends on: `GBX-1290`
- Goal: provide one command that records v12 blocking and advisory evidence
  clearly
- Deliverables:
  - `scripts/validate_v12_release_gate.py`
  - inherited v11 gate or equivalent v11 evidence stages
  - v12 deterministic changeset, review brief, commit readiness, worktree,
    topology, and command evidence stages
  - package contents and installed smoke for new docs, eval fixtures, generated
    API files, and dashboard static assets
  - retained `summary.json` with blocking and advisory sections
  - `docs/v12-release-gate.md`
- Implementation notes:
  - keep provider, live-browser, and manual review evidence advisory unless
    explicitly promoted
  - gate output should end with a concise reviewer summary
  - do not require a remote git provider or live PR creation
- Tests and validation included in task:
  - gate unit tests
  - dry-run gate
  - focused real gate run before release-candidate publication
- Done when:
  - v12 readiness has one command that records deterministic, package,
    changeset, review, commit-readiness, topology, command-evidence, and
    advisory evidence clearly

### GBX-1292: Run v12 Dogfooding Passes

- Status: `TODO`
- Depends on: `GBX-1291`
- Goal: validate v12 against real local operator use and record product
  friction before release signoff
- Deliverables:
  - at least five focused dogfooding passes:
    - create a changeset from a real session or task
    - generate a review brief for a non-trivial local change
    - use commit readiness on a dirty workspace with stale or missing
      verification
    - adopt or reject a branch-search candidate into a changeset
    - use topology-aware recommendations in a mixed backend/frontend change
  - optional provider or live-dashboard review dogfooding when environment
    permits
  - retained local evidence or sanitized summaries for each pass
  - friction findings grouped by changeset creation, inventory provenance,
    verification readiness, review brief quality, commit readiness, worktree
    adoption, topology recommendations, command evidence, dashboard review, and
    release evidence
  - candidate tests or eval cases for repeated failure patterns
- Implementation notes:
  - prefer real tasks with normal messiness over staged fixtures
  - record where the operator still had to infer state manually
  - do not expand scope during dogfooding; file follow-up tasks instead
- Tests and validation included in task:
  - focused validation commands chosen from actual touched surfaces
- Done when:
  - v12 priorities are informed by real reviewable-change use

### GBX-1293: Publish v12 Release-Candidate Guide

- Status: `TODO`
- Depends on: `GBX-1291`, `GBX-1292`
- Goal: publish a concise public guide for the supported v12 reviewable-change
  operating model, validation path, evidence expectations, non-goals,
  residual risks, and release decision
- Deliverables:
  - `docs/v12-release-candidate.md`
  - README update linking the v12 contract and release candidate
  - docs hub update linking v12 changeset, review brief, commit readiness,
    worktree isolation, topology, command evidence, dogfooding, and release
    evidence docs
  - release-readiness checklist reflecting automated gate, deterministic evals,
    changeset evidence, review briefs, commit readiness, worktree evidence,
    topology recommendations, command policy hardening, package contents,
    dogfooding, advisory evidence, and residual risks
  - decision section with candidate build, date, evidence directory, final
    pass/fail state, and accepted risks
- Implementation notes:
  - keep the release guide operator-readable
  - be explicit that Glassbox remains local-first agent work, not hosted code
    review or automatic PR automation
  - name remaining non-goals and known residual risks clearly
  - avoid overclaiming commit readiness, provider reliability, accessibility,
    browser evidence, or unattended operation beyond retained evidence
- Tests and validation included in task:
  - docs link review
  - release docs guardrail tests
  - final v12 release gate run
- Done when:
  - v12 has a publishable release-candidate narrative backed by retained
    automated, dogfooding, manual, and advisory evidence

## v12 Release-Candidate Readiness Checklist

Before treating a build as the v12 release candidate, complete this list:

- The v12 reviewable-change contract is published and linked from the docs hub.
- The changeset event vocabulary and projections rebuild from canonical events.
- `glassbox changeset` commands can create, list, show, refresh, archive, and
  export changesets with scriptable JSON output.
- Change inventory artifacts include provenance, risk, sensitivity, freshness,
  and redaction posture.
- Changeset verification readiness distinguishes fresh, stale, missing, failed,
  skipped, and accepted-with-risk evidence.
- Review briefs can be generated deterministically from changeset evidence and
  exported safely.
- Commit readiness can explain ready, blocked, needs-verification,
  stale-inventory, failed-checks, missing-provenance, and accepted-risk states
  without committing.
- Worktree isolation and branch-candidate adoption require explicit operator
  confirmation and do not automatically merge.
- Topology-aware recommendations improve changed-path verification without
  presenting stale topology as fact.
- Command evidence classifies purpose, captures redacted environment/toolchain
  posture where appropriate, and blocks or gates publish/destructive actions.
- The dashboard has a usable changeset/review surface with no known blocking
  accessibility, wrapping, or large-session issues.
- Deterministic v12 eval cases and coverage mappings pass in the
  release-candidate profile.
- `uv run python scripts/validate_v12_release_gate.py` passes and writes
  retained `summary.json` with blocking and advisory sections.
- Dogfooding findings have dispositions as fixes, docs, tests/evals, accepted
  risks, or post-v12 follow-ups.
- Raw `.glassbox` state is not committed; reviewer-safe summaries are used for
  handoff and release review.

## Deliberate v12 Non-Goals

v12 deliberately does not introduce:

- hosted code review
- cloud workspace authority
- remote worker fleets
- simultaneous multi-writer mutation
- automatic commits
- automatic pushes
- automatic pull request creation
- automatic branch-search merging
- automatic provider failover as release authority
- hidden provider-side memory
- cross-repository memory sync
- indefinite unattended autonomy

These may be revisited in future milestones only with a new product contract,
safety model, evidence policy, and explicit operator semantics.
