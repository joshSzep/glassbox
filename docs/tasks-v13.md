# Glassbox v13 Tasks

For the docs hub and operator guides, start at [README.md](./README.md). This
file is the v13 task graph for evolving the v12 reviewable local change
lifecycle into a review-resilient local feedback loop.

## Purpose

This document defines Glassbox v13: the review-loop evolution after the v12
reviewable-change milestone in [tasks-v12.md](./tasks-v12.md).

It is written in the same execution style as [tasks-v1.md](./tasks-v1.md)
through [tasks-v12.md](./tasks-v12.md): explicit dependencies, small vertical
slices, concrete deliverables, and quality requirements attached directly to
the work.

The v2 through v12 work established the durable local runtime, event-sourced
SQLite store, daemon ownership model, packaged dashboard, full-screen terminal
client, cancellation, replay/eval release contracts, provider diagnostics,
task plans, autonomy budgets, background jobs, workspace memory, repository
intelligence, verify-repair loops, branch search, dashboard cockpit surfaces,
checkpointed long-running work, artifact-backed context compactions,
resumable tool attempts, time-aware continuation budgets, incremental
verification, provider recovery posture, unified knowledge posture, branch
decision support, reviewer-safe handoff guidance, local changesets, structured
change inventories, verification readiness, review briefs, commit preparation,
worktree isolation, topology-aware verification, command evidence, and v12
release evidence.

The v13 goal is not to turn Glassbox into hosted code review, automatic pull
requests, or approval automation. The v13 goal is to make a local changeset
survive real review: feedback, requested changes, fixups, manual evidence,
browser checks, accessibility notes, stale verification, accepted risks, and
final handoff should become structured local evidence without surrendering
operator control.

The v13 work should optimize for ten outcomes:

- make review feedback a first-class local evidence object tied to changesets,
  files, tasks, verification, briefs, and risks
- track fixups and review responses so a reviewer can see what changed after
  initial review
- provide an explicit evidence inbox for manual commands, external checks,
  notes, screenshots, reviewer observations, and sanitized logs
- retain browser, dashboard, and accessibility walkthrough evidence with clear
  advisory boundaries and non-claims
- improve stale-verification and path-aware recommendations after review-driven
  edits
- upgrade review briefs and evidence bundles from initial review summaries into
  lifecycle summaries
- define publication-boundary guidance without staging, committing, pushing,
  opening pull requests, or merging automatically
- rethink changeset UX late in the milestone after the review-loop model has
  enough shape to deserve good terminal and dashboard affordances
- preserve deterministic replay/eval release authority while adding stable
  review-loop contracts
- preserve local-first, operator-controlled, one-mutation-owner semantics

The v13 thesis is:

- preserve local-first operation and workspace-owned state
- preserve canonical events as the source of truth
- preserve one local mutation owner per workspace
- preserve deterministic replay and eval as release authority
- treat review feedback as local evidence, not remote collaboration state
- make manual and live evidence attachable, redacted, and honestly bounded
- distinguish "responded to review" from "review approved"
- distinguish "ready to hand off" from "published"
- derive review-loop summaries from recorded evidence instead of hidden model
  memory
- place integrated slash-command, command-palette, and dashboard UX near the end
  of the milestone so earlier review-loop discoveries can reshape the interface
- avoid hosted orchestration, hosted code review, simultaneous multi-writer
  mutation, automatic staging, automatic committing, automatic pushing,
  automatic pull request creation, automatic merging, provider-side hidden
  state, and indefinite unattended autonomy in this milestone

## Current Baseline Before V13 Execution

Treat the following as the starting point for every task in this document:

- [v12-release-candidate.md](./v12-release-candidate.md) records a GO decision
  for the v12 release candidate and the supported `0.10.0` operating model.
- [v12-reviewable-change-contract.md](./v12-reviewable-change-contract.md)
  records the supported reviewable-change lifecycle contract.
- [v12-dogfooding-summary.md](./v12-dogfooding-summary.md) records the v12
  real-use findings and candidate follow-ups.
- `glassbox session chat` remains the primary conversational surface.
- The dashboard is a packaged Next.js static export served by FastAPI.
- Runtime state is local to `.glassbox/` by default and backed by canonical
  SQLite events plus rebuildable projections.
- Replay and eval profiles live in `evals/` as repository-owned deterministic
  behavioral contracts.
- Changesets are local evidence objects, not git commits, branches, pull
  requests, or remote review primitives.
- Review briefs are deterministic reviewer-safe summaries and do not prove that
  a human reviewed every changed line.
- Commit readiness is advisory and does not stage, commit, push, open a pull
  request, or merge.
- Branch-candidate adoption records local evidence and does not merge candidate
  work into parent history.
- Command evidence is durable when commands flow through retained Glassbox
  instrumentation, but manual shell commands outside that path may not appear
  on a changeset.
- Provider canaries, live dashboard evidence, browser walkthroughs,
  accessibility passes, and dogfooding evidence remain advisory unless promoted
  through a deterministic fixture-backed contract.
- v12 has no first-class local review feedback threads, reviewer questions,
  requested-change records, review response summaries, or in-session changeset
  creation slash command.

## v13 Review-Loop Findings

Treat these findings as evidence that should steer the first implementation
slices:

- v12 changesets can become ready for review, but Glassbox does not yet retain
  the review feedback that follows.
- Review briefs summarize initial evidence, but they do not yet explain what
  changed after reviewer comments, which comments remain open, or which risks
  were accepted during response.
- Fixups can be made in the workspace, but Glassbox cannot yet connect a fixup
  to a requested change, reviewer note, manual evidence item, or stale
  verification decision.
- Manual shell commands, local observations, external test runs, screenshots,
  and reviewer notes need an explicit attachment path so they do not masquerade
  as instrumented command evidence.
- Browser, dashboard, and accessibility evidence can strengthen confidence, but
  v12 did not collect new live dashboard or accessibility evidence for the
  release candidate and does not offer a focused evidence capture workflow.
- Topology-aware recommendations are useful but still depend on impact-rule
  coverage; v12 dogfooding found changeset runtime internals that lacked a
  direct recommendation mapping.
- Publication preparation needs clearer "handoff-ready" language without
  implying automatic commit, push, pull request, or merge behavior.
- The terminal chat command palette and slash command registry do not currently
  expose changeset creation or review-loop entry points, so operators must leave
  chat and run separate `glassbox changeset ...` commands.
- The right in-session changeset UX should be designed after the v13 review-loop
  features exist, not before; otherwise the interface will freeze around v12
  assumptions.

## Agent Execution Rules

These rules apply to every task in this file.

1. Respect dependency order. Do not start a task until its dependencies are
   complete unless the task explicitly says it can proceed in parallel.
2. Preserve the event-sourced source-of-truth rule. Review feedback, fixup
   responses, manual evidence, browser evidence, accessibility notes, evidence
   bundles, publication-boundary decisions, UX-triggered changeset creation,
   and readiness state must be recorded in canonical events, retained
   artifacts, typed API responses, or explicitly rebuildable derived state.
3. Preserve local-first operation. Do not introduce hosted review state, hosted
   pull request authority, cloud workspace authority, remote worker fleets, or
   external service dependencies for v13 readiness.
4. Preserve one local mutation owner per workspace. Review-loop features may
   cite worktrees, branch candidates, and manual edits, but Glassbox must still
   avoid simultaneous uncoordinated mutation of the same workspace state.
5. Preserve deterministic release blocking. Live-provider, browser,
   accessibility, manual review, and dogfooding evidence may strengthen
   confidence but must not replace deterministic replay/eval release authority
   unless a task explicitly defines a repeatable fixture-backed contract and
   failure policy.
6. Treat review feedback as evidence, not approval. Feedback records should name
   source, scope, disposition, response, limitations, and residual risk whenever
   those signals are available.
7. Do not auto-stage, auto-commit, auto-push, auto-open pull requests, or
   auto-merge. v13 may prepare handoff summaries, publication readiness,
   reviewer responses, and safe next commands, but final mutation remains
   explicit operator intent.
8. Keep review-loop guidance concrete. If feedback is unresolved, verification
   is stale, evidence is manual-only, provenance is missing, or publication is
   not ready, terminal and dashboard surfaces should name the exact safe
   inspection or verification command before any mutating action.
9. Keep reviewer artifacts redacted. Review-loop briefs, evidence bundles,
   manual evidence attachments, browser evidence, and exports must follow
   existing path, secret, provider-output, artifact, local-state, and raw-log
   redaction rules.
10. Make topology and ownership hints subordinate to source files and
    manifests. Stale or missing topology lowers confidence and should not be
    presented as current subsystem authority.
11. Place integrated changeset UX late in the milestone. Early tasks should
    expose enough CLI/API behavior to validate the product model; terminal slash
    commands, palette actions, and dashboard shortcuts should be shaped by
    dogfooding and review-loop evidence.
12. Every implementation task automatically includes:
    - automated tests for new or changed behavior
    - `ruff` formatting and lint compliance for touched Python code
    - `ty` typecheck compliance for touched Python code
    - focused `pytest` coverage for touched runtime, CLI, TUI, web, replay,
      eval, daemon, store, policy, task, compaction, verification, provider,
      branch-search, changeset, worktree, topology, review, manual evidence,
      browser evidence, accessibility evidence, publication-boundary, and
      terminal behavior
    - frontend lint, typecheck, tests, and build when the task touches
      dashboard code, generated API types, packaged static assets, or route
      assumptions
    - documentation updates when operator-visible behavior, release posture,
      review-loop posture, commit or publication posture, provider posture,
      recovery behavior, policy behavior, or public workflow claims change

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
- new review-loop claims are backed by retained deterministic or manual
  evidence
- new guidance starts with safe inspection before mutation
- no meaningful review feedback, response, manual evidence, browser evidence,
  accessibility evidence, handoff, or readiness state exists only in memory once
  a task claims durability
- reviewer-facing artifacts are redacted or explicitly documented as local-only
- manual evidence is labeled as manual and never backfilled as retained tool
  evidence
- browser, dashboard, accessibility, provider, and dogfooding evidence names
  bounded claims and non-claims
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
src/glassbox/cli/
src/glassbox/cli/tui/
src/glassbox/core/
src/glassbox/runtime/
src/glassbox/services/
src/glassbox/store/
src/glassbox/web/
frontend/
frontend/components/console/
frontend/lib/api.ts
docs/
evals/
tests/
```

Likely new or expanded modules include:

```text
src/glassbox/runtime/review_feedback.py
src/glassbox/runtime/review_responses.py
src/glassbox/runtime/manual_evidence.py
src/glassbox/runtime/browser_evidence.py
src/glassbox/runtime/publication_boundary.py
src/glassbox/store/sqlite_schema_review_loop.py
src/glassbox/store/sqlite_projection_review_loop.py
src/glassbox/store/repository_review_loop.py
src/glassbox/web/routes/review_loop.py
frontend/components/console/changesets/
frontend/components/console/review-loop/
docs/v13-review-loop-contract.md
docs/v13-review-loop-audit.md
docs/manual-evidence.md
docs/review-feedback.md
docs/review-responses.md
docs/browser-accessibility-evidence.md
docs/publication-boundary.md
docs/v13-release-gate.md
docs/v13-dogfooding-summary.md
docs/v13-release-candidate.md
```

Do not create these exact files merely to satisfy this list. Use them when they
are the right boundary for the implementation.

## Recommended Validation Commands

Use the narrowest meaningful commands while implementing a task. Expand to the
full milestone gate only when release authority is being changed.

```bash
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run pytest
uv run pytest tests/unit/test_core_events.py -q
uv run pytest tests/integration/test_sqlite_projections.py -q
uv run pytest tests/integration/test_changeset_projection.py -q
uv run pytest tests/unit/test_review_briefs.py -q
uv run pytest tests/unit/test_commit_readiness.py -q
uv run pytest tests/unit/test_changeset_verification_readiness.py -q
uv run pytest tests/integration/test_cli_changeset_commands.py -q
uv run pytest tests/unit/test_cli_tui_commands.py -q
uv run pytest tests/unit/test_cli_tui_app.py -q
uv run pytest tests/integration/test_web_changeset_routes.py -q
uv run pytest tests/unit/test_release_candidate_docs.py -q
uv run glassbox eval audit --profile release-candidate --cwd .
uv run glassbox eval run --profile release-candidate --cwd .
uv run python scripts/validate_v12_release_gate.py --dry-run
```

Once `scripts/validate_v13_release_gate.py` exists, it becomes the milestone
gate:

```bash
uv run python scripts/validate_v13_release_gate.py
uv run python scripts/validate_v13_release_gate.py --dry-run
```

Frontend changes usually require:

```bash
pnpm --dir frontend lint
pnpm --dir frontend typecheck
pnpm --dir frontend test
pnpm --dir frontend build
```

Generated API changes usually require:

```bash
uv run python scripts/generate_openapi.py
pnpm --dir frontend generate:api
```

Package or release-surface changes usually require:

```bash
uv build
uv run python scripts/validate_package_contents.py
```

## Milestone Map

The intended v13 milestone order is:

1. v13 review-loop contract and residual-risk audit
2. local review feedback model
3. fixup and review response tracking
4. manual evidence inbox
5. browser, dashboard, and accessibility evidence
6. verification intelligence v2
7. review briefs and evidence bundles v2
8. publication boundary and final handoff
9. integrated changeset UX and in-session review entry points
10. v13 evals, dogfooding, release gate, and release-candidate guide

Each phase below corresponds to one concrete milestone. The UX phase is
deliberately late so slash commands, command-palette actions, and dashboard
shortcuts are shaped by the review-loop features that precede them.

## Task Graph

---

## Phase 130: V13 Review Loop Contract And Residual-Risk Audit

### GBX-1300: Define The v13 Review Loop Contract

- Status: `DONE`
- Depends on: none
- Goal: publish the v13 product contract before changing behavior
- Deliverables:
  - `docs/v13-review-loop-contract.md`
  - supported workflow set for local review feedback, fixup responses, manual
    evidence, browser/dashboard/accessibility evidence, review lifecycle
    briefs, publication-boundary guidance, and integrated in-session changeset
    UX
  - explicit non-goals for hosted code review, automatic PRs, automatic
    approvals, automatic staging, automatic commits, automatic pushes,
    automatic merges, and indefinite unattended mutation
  - release-evidence expectations that distinguish deterministic blocking
    evidence from manual review, live browser, live provider, accessibility,
    and operator dogfooding evidence
- Implementation notes:
  - keep the contract operator-readable
  - emphasize "review-resilient local changeset" rather than "remote review"
  - preserve terminal chat as the primary creation surface and dashboard as the
    paired review/evidence surface
  - state that UX consolidation happens late after feature dogfooding
- Tests and validation included in task:
  - docs link review
  - release-doc guardrail updates if current tests require active milestone
    docs to be linked
- Done when:
  - v13 has one concise product contract that later tasks can reference instead
    of restating scope

### GBX-1301: Audit V12 Residual Risks Against Review-Loop Needs

- Status: `DONE`
- Depends on: `GBX-1300`
- Goal: ground v13 implementation in actual gaps between v12 reviewable-change
  evidence and review-loop needs
- Deliverables:
  - `docs/v13-review-loop-audit.md`
  - source-linked audit entries for changeset creation, review briefs,
    verification readiness, commit preparation, manual command evidence,
    branch-candidate adoption, topology recommendations, dashboard review,
    TUI slash commands, and exports
  - classification of each gap as fixed in v13, evidence-only in v13, accepted
    non-goal, or carried-forward risk
  - test inventory for where review-loop behavior is currently covered and
    where coverage is missing
- Implementation notes:
  - separate "ready to review" from "review feedback has been handled"
  - separate "manual evidence was attached" from "Glassbox ran the command"
  - include both terminal and dashboard evidence paths
- Tests and validation included in task:
  - docs review against current implementation
  - no product-code change required unless the audit exposes stale docs
- Done when:
  - every known gap between v12 changesets and review-loop evidence has an
    explicit v13 disposition

### GBX-1302: Define Review-Loop Vocabulary And Operator Language

- Status: `DONE`
- Depends on: `GBX-1300`, `GBX-1301`
- Goal: standardize how Glassbox names feedback, requested changes, responses,
  manual evidence, lifecycle briefs, and publication posture before adding
  command surfaces
- Deliverables:
  - vocabulary section in the v13 contract or a companion doc
  - definitions for review feedback, requested change, reviewer question,
    fixup response, manual evidence, browser evidence, accessibility evidence,
    lifecycle brief, handoff readiness, publication boundary, and final
    operator action
  - command/dashboard copy guidelines that avoid implying approval, commit,
    push, PR, or merge behavior
- Implementation notes:
  - align with v9 vocabulary and v12 changeset vocabulary
  - distinguish review feedback, operator note, task checkpoint, changeset
    risk, and verification evidence clearly
  - prefer "responded" and "resolved locally" only when retained evidence
    supports those words
- Tests and validation included in task:
  - command guide or docs guardrail tests if copy surfaces change
- Done when:
  - later tasks can use consistent names without re-litigating product language

---

## Phase 131: Local Review Feedback Model

### GBX-1310: Add Review Feedback Event Vocabulary

- Status: `DONE`
- Depends on: `GBX-1302`
- Goal: introduce canonical events for local review feedback without creating
  hosted review state
- Deliverables:
  - event payloads for feedback creation, scope attachment, disposition update,
    resolution, reopening, archival, and risk acceptance
  - correlation fields for changeset ID, session ID, task ID, turn ID,
    artifact ID, file path, line or range hints, verification ID, and reviewer
    label where appropriate
  - event tests proving serialization, replay normalization, and correlation
    extraction
- Implementation notes:
  - store paths and line hints as bounded metadata, not raw file contents
  - reviewer labels should be local labels, not identity-provider accounts
  - support unknown or manual provenance explicitly
- Tests and validation included in task:
  - unit tests for event payload round trips
  - replay/eval normalization tests for review-loop event families
- Done when:
  - feedback can be represented in canonical event history with no projection as
    the source of truth

### GBX-1311: Add Review Feedback Projections And Query Services

- Status: `DONE`
- Depends on: `GBX-1310`
- Goal: make local review feedback queryable by changeset, file, state, and
  risk posture
- Deliverables:
  - SQLite schema and projection rebuild handlers for feedback records,
    feedback scopes, dispositions, and resolution state
  - repository methods and query service for listing active, resolved,
    archived, and reopened feedback
  - projection health behavior for stale or degraded feedback views
- Implementation notes:
  - preserve rebuildability from canonical events
  - keep projection summaries bounded and redacted
  - avoid joining raw artifact bodies into feedback lists
- Tests and validation included in task:
  - migration tests
  - projection rebuild tests
  - repository adapter boundary tests
- Done when:
  - feedback state can be rebuilt and queried without hidden in-memory state

### GBX-1312: Add Review Feedback CLI, API, And Dashboard Read Surface

- Status: `DONE`
- Depends on: `GBX-1311`
- Goal: let operators inspect and record local feedback through stable
  non-mutating review surfaces
- Deliverables:
  - CLI commands for adding, listing, showing, resolving, reopening, and
    archiving feedback
  - API routes and generated frontend types for feedback list/detail actions
  - dashboard changeset panel for open feedback, requested changes, questions,
    resolved feedback, accepted risks, and safe next actions
  - documentation in `docs/review-feedback.md`
- Implementation notes:
  - adding feedback is a local evidence mutation, not a git mutation
  - dashboard copy should not say "approved" unless an explicit local approval
    record exists and its limitations are visible
  - expose JSON output for scripting
- Tests and validation included in task:
  - CLI integration tests
  - API route tests
  - frontend component/store tests
  - generated OpenAPI and frontend type freshness
- Done when:
  - an operator can record and inspect review feedback without leaving the
    local evidence model

---

## Phase 132: Fixup And Review Response Tracking

### GBX-1320: Define Review Response And Fixup Contract

- Status: `DONE`
- Depends on: `GBX-1312`
- Goal: define how Glassbox links workspace edits and verification changes to
  review feedback without claiming ownership of every manual edit
- Deliverables:
  - `docs/review-responses.md`
  - response states for planned, in-progress, responded, resolved, reopened,
    blocked, accepted-with-risk, and not-applicable
  - fixup source model covering session turns, task steps, manual workspace
    edits, branch-search candidates, worktrees, and operator notes
  - stale-verification rules after response-linked inventory changes
- Implementation notes:
  - a response can cite evidence without proving the reviewer accepted it
  - response summaries should say "operator says" or "evidence indicates" when
    provenance is not direct
  - avoid raw diff retention unless an existing redacted artifact contract is
    extended deliberately
- Tests and validation included in task:
  - docs review against v12 changeset and verification contracts
  - fixture design for response lifecycle evals
- Done when:
  - implementation tasks have a clear response lifecycle and non-claim policy

### GBX-1321: Attach Fixup Inventory Deltas To Review Feedback

- Status: `DONE`
- Depends on: `GBX-1320`
- Goal: show what changed after feedback without flattening raw diffs into
  feedback records
- Deliverables:
  - event and artifact updates for response-linked inventory snapshots or
    inventory deltas
  - file-level links between feedback scopes, changed paths, provenance, and
    latest inventory freshness
  - safe summaries for manual edits, generated outputs, tests, docs, and
    high-risk paths
- Implementation notes:
  - reuse v12 change inventory where possible
  - mark inventory stale when the workspace changes after response evidence is
    recorded
  - keep changed-file summaries bounded and reviewer-safe
- Tests and validation included in task:
  - unit tests for inventory delta derivation
  - integration tests for stale response evidence after workspace drift
  - docs updates for response-linked inventory
- Done when:
  - a feedback item can name the files and inventory evidence that appear to
    respond to it

### GBX-1322: Surface Review Response Status In CLI, API, And Dashboard

- Status: `DONE`
- Depends on: `GBX-1321`
- Goal: make review response state visible beside the changeset instead of
  hidden in prose
- Deliverables:
  - CLI status output for open feedback, responded feedback, unresolved
    feedback, stale responses, and accepted risks
  - API fields for dashboard response summaries
  - dashboard response timeline with feedback, fixup inventory, verification
    freshness, and safe next actions
  - updated `changeset show` output that names response blockers
- Implementation notes:
  - keep response timelines dense and scannable
  - do not mix response state into commit readiness until publication-boundary
    tasks define that relationship
  - unresolved feedback should remain visible beside passing checks
- Tests and validation included in task:
  - CLI output tests
  - API route tests
  - frontend component tests
  - accessibility and wrapping checks for dense feedback rows
- Done when:
  - an operator can answer "what review feedback still needs work?" from the
    terminal or dashboard

---

## Phase 133: Manual Evidence Inbox

### GBX-1330: Define Manual Evidence Attachment Contract

- Status: `DONE`
- Depends on: `GBX-1302`
- Goal: create an honest path for attaching evidence that did not flow through
  retained Glassbox command instrumentation
- Deliverables:
  - `docs/manual-evidence.md`
  - evidence kinds for manual command, external check, reviewer note,
    screenshot, browser observation, accessibility note, local file reference,
    sanitized log, and operator assertion
  - redaction, size, source, local-only, freshness, and non-claim rules
  - clear distinction between manual evidence and retained command/tool attempt
    evidence
- Implementation notes:
  - manual evidence should never be promoted silently into verification proof
  - require source labels and bounded summaries
  - allow evidence to be attached to a changeset, feedback item, response, or
    verification requirement
- Tests and validation included in task:
  - docs guardrail tests for manual evidence language
  - redaction fixture planning
- Done when:
  - v13 has a precise policy for bringing external evidence into the local
    review loop

### GBX-1331: Add Manual Evidence Store, Artifacts, And Redaction Pipeline

- Status: `DONE`
- Depends on: `GBX-1330`
- Goal: retain manual evidence safely as summary-first local artifacts
- Deliverables:
  - canonical events for manual evidence attached, superseded, rejected, and
    archived
  - artifact schemas for summary-only manual command evidence, sanitized notes,
    screenshot metadata, and local-only references
  - redaction checks for absolute paths, `.glassbox/` paths, provider keys,
    credentials, secret assignments, and large raw logs
  - projection and query methods for attached evidence
- Implementation notes:
  - default to summary-only capture
  - raw files should remain local-only unless a task explicitly defines a
    reviewer-safe export format
  - reject or quarantine attachments that appear to contain secrets
- Tests and validation included in task:
  - redaction unit tests
  - artifact schema tests
  - projection rebuild tests
  - import/export safety tests if evidence enters bundles
- Done when:
  - manual evidence can be retained, queried, redacted, and invalidated without
    pretending Glassbox executed it

Completed in this slice:

- Added manual evidence canonical event payloads for attached, superseded,
  rejected, and archived evidence, plus local manual evidence IDs and typed
  state, kind, target, redaction, and freshness enums.
- Added summary-first `manual_evidence` artifact schemas and deterministic
  redaction checks for secret-looking assignments, private keys, absolute
  paths, `.glassbox/` state paths, raw provider snippets, and oversized logs.
- Added SQLite projection tables, rebuild support, repository query helpers,
  and tests that prove manual evidence can be attached, queried, rejected,
  superseded, archived, and rebuilt without becoming retained command
  evidence.

### GBX-1332: Add Manual Evidence CLI, API, And Review Surface

- Status: `DONE`
- Depends on: `GBX-1331`
- Goal: make evidence attachment ergonomic without hiding its manual provenance
- Deliverables:
  - CLI commands for attaching a manual note, command summary, external check,
    sanitized log, or local-only file reference
  - API routes and generated frontend types for evidence attachment and listing
  - dashboard evidence inbox panel on changeset detail
  - safe next actions that suggest verification or brief refresh after evidence
    changes
- Implementation notes:
  - commands should make local-only posture visible by default
  - do not accept raw provider transcripts or unredacted logs as reviewer-safe
  - allow attachment to feedback or response IDs once those exist
- Tests and validation included in task:
  - CLI integration tests
  - API route tests
  - frontend evidence inbox tests
  - docs updates for operator workflow examples
- Done when:
  - a developer can attach manual review evidence to a changeset and see it in
    the review surface with proper limitations

Completed in this slice:

- Added `glassbox changeset evidence attach` and `glassbox changeset evidence
  list` for manual command summaries, external checks, reviewer notes,
  screenshots, browser observations, accessibility notes, local-only file
  references, sanitized logs, and operator assertions.
- Added changeset API routes and generated frontend API types for attaching and
  listing manual evidence while retaining local-only provenance and non-claims.
- Added a dashboard manual evidence inbox on changeset detail with state,
  redaction posture, freshness, target, artifact, limitation, and non-claim
  rows.
- Added safe next actions that start with inspection, verification-plan review,
  and brief refresh instead of publication or git mutation.

---

## Phase 134: Browser, Dashboard, And Accessibility Evidence

### GBX-1340: Define Live Review Evidence Protocol

- Status: `DONE`
- Depends on: `GBX-1330`
- Goal: make browser, dashboard, and accessibility evidence structured without
  overclaiming release authority
- Deliverables:
  - `docs/browser-accessibility-evidence.md`
  - protocols for live dashboard walkthroughs, browser checks, screenshot
    evidence, keyboard navigation notes, responsive layout observations, and
    accessibility pairings
  - advisory versus blocking evidence policy
  - naming and retention rules for local evidence directories
- Implementation notes:
  - keep live evidence advisory unless a later task defines a deterministic
    fixture-backed gate
  - require environment, viewport, date, skipped cases, limitations, and
    non-claims
  - avoid broad accessibility certification language
- Tests and validation included in task:
  - docs review
  - release-evidence language guardrails if applicable
- Done when:
  - live review evidence has a repeatable local protocol and bounded claims

Completed in this slice:

- Added `docs/browser-accessibility-evidence.md` with structured evidence
  kinds for live dashboard walkthroughs, browser checks, screenshot metadata,
  keyboard notes, responsive observations, and accessibility pairings.
- Defined required metadata for environment, browser, viewport, date, skipped
  cases, limitations, local-only posture, freshness, redaction, and non-claims.
- Documented advisory-versus-blocking policy that preserves deterministic
  replay, eval, package, migration, unit, and integration checks as release
  authority unless a later deterministic fixture-backed gate promotes live
  evidence.
- Added local evidence directory naming and retention rules for browser,
  dashboard, and accessibility artifacts under `.glassbox/evidence/`.
- Added reviewer-safe language and explicit non-claims that avoid accessibility
  certification, reviewer approval, publication authority, and git mutation
  claims.

### GBX-1341: Add Browser And Dashboard Evidence Capture Workflows

- Status: `DONE`
- Depends on: `GBX-1340`
- Goal: help operators retain browser and dashboard walkthrough evidence around
  one changeset
- Deliverables:
  - commands or guided workflows that create a browser/dashboard evidence
    artifact tied to a changeset
  - screenshot or observation metadata capture with redaction and local-only
    posture
  - dashboard links from evidence records back to changeset, feedback, and
    response state
  - safe inspection commands for rerunning or refreshing evidence
- Implementation notes:
  - reuse existing dashboard routes and screenshot archive guidance where
    possible
  - do not require browser evidence to pass deterministic gates
  - keep binary artifacts out of git unless explicitly documented as small,
    reviewed, and necessary
- Tests and validation included in task:
  - unit tests for evidence artifact shape
  - integration tests for CLI/API evidence attachment
  - focused frontend tests for rendering evidence references
- Done when:
  - a changeset can cite retained browser/dashboard evidence with clear
    advisory posture

Completed in this slice:

- Added browser/dashboard evidence capture helpers that render
  `browser-accessibility-evidence.v1` metadata into summary-first manual
  evidence artifacts with environment, route, browser, viewport, observed time,
  skipped cases, limitations, and local-only screenshot metadata.
- Added `glassbox changeset evidence browser` and
  `glassbox changeset evidence dashboard` commands for attaching advisory live
  evidence to a changeset, feedback item, response target, or other
  review-loop target.
- Added `POST /changesets/{changeset_id}/browser-evidence`, regenerated
  OpenAPI/frontend types, and preserved the existing manual evidence response
  shape for evidence IDs, artifact IDs, target links, limitations, non-claims,
  and safe next actions.
- Updated the dashboard manual evidence inbox to surface live browser and
  dashboard evidence as advisory, local-only evidence beside changeset,
  feedback, and response target references.
- Added unit, CLI, API, generated-type, and frontend coverage for browser and
  dashboard evidence capture without promoting it to deterministic release
  authority.

### GBX-1342: Add Accessibility Evidence Pairing Support

- Status: `DONE`
- Depends on: `GBX-1340`, `GBX-1341`
- Goal: retain keyboard and accessibility review evidence in a structured,
  reviewer-safe way
- Deliverables:
  - evidence kinds for keyboard pass, screen reader note, focus-order issue,
    wrapping issue, contrast observation, and responsive review
  - CLI/API fields for environment, tool, reviewer label, observed issue,
    severity, disposition, and follow-up
  - dashboard rendering that keeps unresolved accessibility observations visible
    beside other review feedback
- Implementation notes:
  - do not claim broad accessibility certification
  - pair accessibility observations with feedback IDs when they drive fixups
  - make unresolved accessibility evidence visible in handoff summaries
- Tests and validation included in task:
  - artifact validation tests
  - frontend tests for evidence rendering
  - manual evidence protocol update
- Done when:
  - accessibility observations can participate in the local review loop without
    being flattened into generic notes

Completed in this slice:

- Added structured accessibility evidence helpers for keyboard passes, screen
  reader notes, focus-order issues, wrapping issues, contrast observations, and
  responsive reviews.
- Added `glassbox changeset evidence accessibility` and
  `POST /changesets/{changeset_id}/accessibility-evidence` with environment,
  tool, reviewer label, observed issue, severity, disposition, follow-up,
  paired-tool output, skipped-case, and limitation fields.
- Retained accessibility observations as `accessibility_note` manual evidence
  with advisory local-only posture, explicit non-claims, and target links to
  changesets, feedback, responses, or other review-loop targets.
- Updated the dashboard manual evidence inbox to keep accessibility
  observations visible beside other review evidence with advisory copy and
  severity/disposition limitations.
- Updated the manual evidence and browser/accessibility protocols plus unit,
  CLI, API, generated-type, and frontend coverage without claiming broad
  accessibility certification.

---

## Phase 135: Verification Intelligence V2

### GBX-1350: Expand Topology Impact Rules For Review-Loop Surfaces

- Status: `DONE`
- Depends on: `GBX-1322`
- Goal: close known topology recommendation gaps for review-loop and changeset
  internals
- Deliverables:
  - updated topology and eval impact rules for changeset runtime, review
    feedback, manual evidence, TUI changeset commands, dashboard review
    surfaces, generated API types, docs, and release scripts
  - coverage for paths such as `src/glassbox/runtime/changesets.py` that v12
    dogfooding found unmatched in mixed recommendation passes
  - topology freshness guidance when source manifests or impact rules are stale
- Implementation notes:
  - make rules explainable and source-backed
  - avoid presenting heuristics as ownership fact
  - include docs-only and generated-asset cases
- Tests and validation included in task:
  - topology unit tests
  - eval recommendation tests
  - docs updates for workspace topology
- Done when:
  - review-loop and changeset internal changes receive useful path-aware
    verification recommendations

Completed in this slice:

- Added v13 impact rules for changeset runtime internals, review-loop
  runtime/evidence helpers, SQLite review-loop projections, CLI/API changeset
  routes, dashboard changeset surfaces, generated API types, v13 docs, and
  release scripts.
- Added focused verification recipes for changeset runtime, review-loop
  evidence, and CLI/API/dashboard/generated changeset surfaces, with advisory
  notes that v12 replay proves lifecycle posture while focused v13 tests remain
  authority for feedback and live evidence details.
- Added recommendation unit and fixture coverage proving
  `src/glassbox/runtime/changesets.py`, manual-evidence/projection paths, and
  `frontend/generated/api-types.ts` no longer fall through to vague fallback
  guidance.
- Updated workspace topology docs with review-loop path guidance and explicit
  freshness guidance for source manifests, lockfiles, generated API outputs,
  `evals/impact.json`, and `evals/recipes.json`.

### GBX-1351: Detect Stale Verification After Review Fixups

- Status: `DONE`
- Depends on: `GBX-1321`, `GBX-1350`
- Goal: make verification readiness degrade when response-linked changes
  invalidate retained checks
- Deliverables:
  - sequence-aware and path-aware stale detection for fixup inventory changes
  - response-level verification state that distinguishes fresh, stale, missing,
    failed, skipped, and accepted-with-risk evidence
  - safe next actions that name which check should be rerun and why
- Implementation notes:
  - reuse v12 verification readiness aggregation where possible
  - do not invent staleness when path mapping is unavailable; lower confidence
    and name the gap
  - make stale response evidence visible beside the feedback it affects
- Tests and validation included in task:
  - unit tests for stale response verification
  - integration tests for fixup-after-pass scenarios
  - dashboard rendering tests for stale feedback responses
- Done when:
  - Glassbox can explain which review responses need fresh verification before
    handoff

Completed in this slice:

- Added response-level verification state to review response status rows,
  distinguishing passed, stale, missing, failed, skipped, accepted-with-risk,
  planned/running, and not-applicable evidence.
- Compared response-linked fixup paths against task verification ledger entries
  by sequence and path overlap, marking passed checks stale when they predate
  later fixup inventory and naming the exact local check to rerun.
- Kept missing path mapping conservative: responses with no mappable fixup
  paths become missing/not-applicable instead of invented stale evidence.
- Threaded the new fields through changeset query services, FastAPI responses,
  regenerated OpenAPI/frontend API types, and dashboard review-feedback rows.
- Updated review-response docs plus unit, integration, OpenAPI, generated-type,
  and dashboard tests for stale-after-fixup and safe next-action behavior.

### GBX-1352: Add Review-Loop Verification Recommendation Summaries

- Status: `DONE`
- Depends on: `GBX-1351`
- Goal: help operators choose verification after feedback, manual evidence, and
  browser/accessibility observations change the review picture
- Deliverables:
  - verification-plan output that includes feedback count, response state,
    manual evidence, browser/accessibility evidence, stale checks, and topology
    impacts
  - dashboard verification panel updates for review-loop context
  - eval recommendation cases for feedback-driven fixups and manual evidence
    attachments
- Implementation notes:
  - keep commands preview-only
  - filter publish, deploy, push, upload, and destructive commands from
    verification plans
  - distinguish "manual evidence suggests this passed" from "retained
    verification says this passed"
- Tests and validation included in task:
  - verification readiness tests
  - CLI/API tests for enriched plan output
  - frontend panel tests
  - deterministic eval fixtures
- Done when:
  - verification recommendations are review-loop aware without running commands
    implicitly

Completed in this slice:

- Added a review-loop summary to changeset verification-plan previews with
  feedback counts, response-state counts, stale/missing/failed response
  verification counts, manual evidence, browser/dashboard evidence,
  accessibility evidence, retained verification state, and topology impact
  counts.
- Kept verification-plan commands preview-only and preserved the existing
  publish/deploy/push/upload filter while adding destructive `rm` filtering.
- Surfaced the review-loop summary in FastAPI responses, regenerated
  OpenAPI/frontend API types, and rendered the context in the dashboard
  verification panel.
- Added recommendation fixture cases for feedback-fixup verification and manual
  evidence attachment paths.
- Updated review-response docs plus CLI/API/dashboard/generated-type coverage so
  manual evidence is visible as advisory context rather than retained
  verification proof.

---

## Phase 136: Review Briefs And Evidence Bundles V2

### GBX-1360: Define Review Lifecycle Brief Contract

- Status: `DONE`
- Depends on: `GBX-1352`
- Goal: upgrade review briefs from initial changeset summaries into local
  review lifecycle summaries
- Deliverables:
  - updated `docs/review-briefs.md` or new lifecycle-brief section
  - artifact schema additions for feedback summary, response summary, manual
    evidence, browser/accessibility evidence, stale verification, accepted
    risks, and publication-boundary posture
  - markdown and JSON render-target requirements
  - non-claims for review approval, publication, verification proof, and
    portability
- Implementation notes:
  - preserve deterministic brief generation
  - cite evidence references instead of flattening raw logs, screenshots, diffs,
    or provider transcripts
  - keep unresolved feedback and accepted risks visible near readiness
- Tests and validation included in task:
  - review brief artifact contract tests
  - docs guardrails for non-claims
- Done when:
  - lifecycle briefs have a stable contract that later tools can rely on

Completed in this slice:

- Updated `docs/review-briefs.md` from the v12 initial-review brief posture to
  a v13 lifecycle-capable contract with feedback, response, manual evidence,
  browser/dashboard/accessibility evidence, stale verification, accepted-risk,
  and publication-boundary sections.
- Extended the `changeset_review_brief` artifact contract to schema version 2
  with optional lifecycle sections and evidence-reference kinds for feedback,
  responses, manual evidence, live evidence, readiness, and publication
  boundary posture.
- Added contract tests for JSON and Markdown render targets plus docs
  guardrails for lifecycle brief non-claims around reviewer approval,
  verification proof, local-only portability, and automatic publication.

### GBX-1361: Generate Lifecycle Briefs From Review-Loop Evidence

- Status: `DONE`
- Depends on: `GBX-1360`
- Goal: make generated briefs reflect the full local review loop
- Deliverables:
  - brief generation updates for feedback, responses, manual evidence,
    browser/accessibility evidence, verification freshness, command evidence,
    topology impacts, and publication-boundary posture
  - retained JSON artifact and markdown rendering updates
  - review readiness decision updates that account for unresolved feedback and
    stale responses
- Implementation notes:
  - unresolved feedback should not disappear behind a passing verification
    summary
  - local-only evidence should be labeled at the section and reference level
  - brief generation should not call a model merely to improve prose
- Tests and validation included in task:
  - unit tests for JSON and markdown output
  - integration tests with mixed resolved/unresolved feedback
  - redaction tests for manual and browser evidence references
- Done when:
  - a generated brief can answer what changed, what review feedback exists,
    what was fixed, what remains uncertain, and what evidence supports handoff

Completed in this slice:

- Updated lifecycle brief generation to populate deterministic sections for
  lifecycle summary, review feedback, review responses, manual evidence,
  browser/dashboard/accessibility evidence, stale response verification, and
  publication-boundary posture.
- Degraded review readiness when unresolved feedback or stale response
  verification remains, keeping those blockers visible beside otherwise
  passing changeset evidence.
- Kept manual and live evidence summary-first with local-only evidence
  references and non-claims instead of raw logs, screenshots, provider
  transcripts, diffs, or file contents.
- Updated `docs/review-briefs.md` and focused review-brief tests to cover mixed
  feedback, response, manual accessibility evidence, stale verification, and
  publication-boundary rendering.

### GBX-1362: Upgrade Reviewer-Safe Evidence Exports

- Status: `DONE`
- Depends on: `GBX-1361`
- Goal: make changeset exports useful after review-loop work without leaking
  raw local state
- Deliverables:
  - export package updates for lifecycle brief, feedback summaries, response
    summaries, manual evidence summaries, browser/accessibility summaries,
    verification posture, command evidence, redaction report, and non-claims
  - explicit omission of raw `.glassbox` databases, raw command output, raw
    provider transcripts, raw diffs, and raw screenshots unless a reviewed
    local-only reference is intended
  - import or validation checks for reviewer-safe package shape
- Implementation notes:
  - prefer summary artifacts and references over large binary payloads
  - make local-only evidence visible before export
  - keep exports deterministic and scriptable
- Tests and validation included in task:
  - export integration tests
  - redaction tests
  - package contents tests if export docs or examples ship
- Done when:
  - reviewers can receive a lifecycle evidence bundle without needing raw
    `.glassbox` state

Completed in this slice:

- Extended changeset export packages with lifecycle brief metadata, review
  feedback summaries, response summaries, manual evidence summaries, live
  browser/dashboard/accessibility evidence summaries, verification posture,
  redaction report updates, and review-loop non-claims.
- Added artifact references for summary-only manual evidence and response
  fixup inventories while continuing to omit raw `.glassbox` databases, raw
  command output, provider transcripts, raw diffs, raw file contents, raw
  screenshots, browser traces, accessibility transcripts, and raw manual logs.
- Updated `docs/reviewer-evidence-bundles.md` and the changeset CLI
  integration flow so reviewer-safe exports expose lifecycle evidence without
  implying reviewer approval, retained command proof, publication, or git
  mutation.

---

## Phase 137: Publication Boundary And Final Handoff

### GBX-1370: Define Publication Boundary Contract

- Status: `DONE`
- Depends on: `GBX-1362`
- Goal: define the line between review-loop handoff readiness and actual git or
  remote publication
- Deliverables:
  - `docs/publication-boundary.md`
  - states for not-ready, needs-review-response, needs-verification,
    stale-inventory, unresolved-risk, handoff-ready, commit-prep-ready,
    publication-blocked, and accepted-with-risk
  - explicit non-goals for automatic staging, committing, pushing, PR creation,
    branch merging, rebasing, force-pushing, deploying, or publishing packages
  - safe next-action policy for final operator steps
- Implementation notes:
  - build on v12 commit readiness, not replace it blindly
  - distinguish handoff readiness from commit readiness
  - require unresolved feedback and stale verification to be visible at final
    handoff
- Tests and validation included in task:
  - docs tests for publication non-claims
  - fixture design for publication-boundary evals
- Done when:
  - the milestone has clear language for final handoff without crossing into
    automatic publication

Completed in this slice:

- Added `docs/publication-boundary.md` with v13 states for not-ready,
  needs-review-response, needs-verification, stale-inventory, unresolved-risk,
  handoff-ready, commit-prep-ready, publication-blocked, and
  accepted-with-risk posture.
- Defined the relationship between review-loop handoff readiness, commit
  readiness, and final operator action while preserving non-goals for automatic
  staging, committing, pushing, pull request creation, merging, rebasing,
  force-pushing, deploying, and package publishing.
- Added safe next-action policy that starts with inspection before mutation and
  docs guardrails plus README/docs-hub links for publication-boundary language.

### GBX-1371: Add Handoff Readiness Service And Surfaces

- Status: `DONE`
- Depends on: `GBX-1370`
- Goal: calculate final handoff posture from changeset, feedback, responses,
  evidence, verification, risks, and commit-prep signals
- Deliverables:
  - runtime service for handoff readiness
  - CLI command or `changeset show` section for handoff posture
  - API fields and dashboard handoff panel
  - safe next actions for unresolved feedback, stale verification, missing
    lifecycle brief, dirty workspace ambiguity, and local-only evidence
- Implementation notes:
  - readiness remains advisory
  - handoff posture should not imply publication occurred
  - local-only evidence should be a visible blocker or limitation depending on
    export intent
- Tests and validation included in task:
  - unit tests for readiness aggregation
  - CLI/API/frontend tests
  - integration tests for unresolved feedback and accepted-risk paths
- Done when:
  - operators can see whether a reviewed changeset is ready for handoff and
    exactly what remains before final operator action

Completed in this slice:

- Added `src/glassbox/runtime/handoff_readiness.py`, a read-only advisory
  handoff-readiness aggregation service that derives v13 publication-boundary
  states from current changeset inventory, review feedback, response status,
  manual/live/accessibility evidence, verification posture, lifecycle brief
  freshness, accepted and unresolved risks, commit-readiness posture, and local
  git ambiguity.
- Added `glassbox changeset handoff-readiness CHANGESET_ID --cwd .` plus a
  handoff section in `glassbox changeset show`, with JSON output, safe
  inspection-first next actions, blockers, limitations, evidence counts, and
  explicit non-claims for publication, approval, staging, committing, pushing,
  pull requests, merging, deploying, and publishing.
- Added `/changesets/{changeset_id}/handoff-readiness`, generated OpenAPI and
  TypeScript API types, frontend store loading, and a dashboard **Final
  Handoff** panel for blockers, local-only evidence, accepted risk, limitations,
  and safe commands.
- Updated publication-boundary and reviewer-evidence bundle docs to document
  the new handoff-readiness command and advisory boundaries.
- Added focused unit, CLI, API, and frontend coverage for unresolved feedback,
  stale inventory, accepted-risk, local-only evidence, command/API output, and
  dashboard rendering.

### GBX-1372: Improve Commit Preparation With Review-Loop Context

- Status: `DONE`
- Depends on: `GBX-1371`
- Goal: make commit preparation account for review feedback and response state
  while preserving the no-mutation boundary
- Deliverables:
  - commit-prep updates for unresolved feedback, stale response verification,
    manual evidence, lifecycle brief freshness, accepted risks, and handoff
    posture
  - deterministic commit-message suggestion updates that can mention review
    response scope without claiming approval
  - dashboard commit preparation panel updates
- Implementation notes:
  - do not stage or commit
  - do not generate PR text unless a future task explicitly defines PR
    preparation
  - make risky paths and unresolved feedback win over optimistic summaries
- Tests and validation included in task:
  - commit readiness tests
  - commit message tests
  - CLI/API/frontend tests
  - docs updates for commit preparation
- Done when:
  - commit preparation reflects the review loop but remains read-only and
    operator-controlled

Completed in this changeset:

- Extended commit-readiness assessments with review feedback, unresolved
  feedback, stale response, manual evidence, local-only evidence, and
  review-loop accepted-risk context.
- Added blocking signals for unresolved feedback, stale/missing/failed response
  verification, and manual evidence that needs inspection; local-only manual
  evidence remains visible as non-blocking accepted risk.
- Updated commit-prep CLI JSON/text output to include final handoff posture
  while preserving the no-stage/no-commit/no-push/no-PR boundary.
- Updated deterministic commit-message suggestions to cite review response
  scope, manual evidence, and handoff posture without claiming reviewer
  approval.
- Surfaced the same context through the API schema, generated frontend types,
  and dashboard Commit Preparation panel.
- Updated commit-readiness, commit-message, and commit-preparation docs and
  added focused unit, CLI, API, OpenAPI, and frontend coverage.

---

## Phase 138: Integrated Changeset UX And In-Session Review Entry Points

### GBX-1380: Audit Review-Loop UX After Dogfooding

- Status: `DONE`
- Depends on: `GBX-1372`
- Goal: rethink changeset and review-loop UX after the underlying v13 features
  exist
- Deliverables:
  - short UX audit of terminal chat, plain interactive mode, command palette,
    dashboard changeset surface, review feedback surface, manual evidence
    inbox, lifecycle briefs, and handoff posture
  - recommended command vocabulary for in-session changeset creation and review
    loop actions
  - decision on whether the primary slash command should be `/changeset`,
    `/review`, `/review-change`, or another operator-friendly verb
  - build-order notes for TUI, plain mode, dashboard, and docs
- Implementation notes:
  - use real v13 dogfooding findings before locking the command shape
  - avoid adding a slash command that only mirrors v12 while ignoring feedback
    and response state
  - prefer current-session defaults when invoked from `glassbox session chat`
- Tests and validation included in task:
  - docs review
  - no product-code change required unless stale UX docs are found
- Done when:
  - the UX work has an evidence-backed target instead of a prematurely chosen
    command name

Completed in this slice:

- Added `docs/v13-review-loop-ux-audit.md`, a source-linked audit of terminal
  chat, plain interactive mode, command-palette actions, dashboard changeset
  surfaces, review feedback, manual evidence, lifecycle briefs, handoff
  readiness, and commit-preparation posture after the v13 review-loop model
  landed through `GBX-1372`.
- Chose `/review` as the primary in-session slash command, with `/changeset`
  retained as a compatibility alias and lower-level `glassbox changeset ...`
  commands preserved as the scriptable surface.
- Defined the recommended review-loop command vocabulary, command-palette
  titles, disabled-state language, dashboard quick-action boundaries, and
  build order for `GBX-1381` and `GBX-1382`.
- Reaffirmed that integrated UX shortcuts may inspect state or record explicit
  local evidence, but must not auto-run checks, stage, commit, push, open pull
  requests, merge, deploy, publish, or imply reviewer approval.
- Linked the audit from the docs hub and root README, and added focused docs
  guardrails for the chosen vocabulary and non-goals.

### GBX-1381: Add TUI Slash Commands And Command-Palette Review Actions

- Status: `DONE`
- Depends on: `GBX-1380`
- Goal: let operators create and inspect review-loop changesets from inside
  `glassbox session chat`
- Deliverables:
  - TUI command registry entries and slash aliases for the chosen changeset or
    review entry points
  - command-palette actions for creating a changeset from the current workspace
    diff, refreshing inventory, opening the dashboard review surface, generating
    a lifecycle brief, previewing verification, and inspecting handoff posture
  - current-session defaulting so chat users do not need to paste the session ID
  - post-create feedback that shows changeset ID, limitations, safe next
    actions, and dashboard handoff when available
- Implementation notes:
  - creating a changeset is an evidence mutation, not a git mutation
  - default in-session creation should anchor `workspace-diff` to the current
    session unless the UX audit chooses a different safe default
  - do not auto-run tests, stage, commit, push, open PRs, or merge
  - make disabled states explicit when the runtime, dashboard, or repository
    location is unavailable
- Tests and validation included in task:
  - TUI command registry tests
  - TUI app tests for slash command submission
  - integration tests for changeset creation from current session context
  - docs updates for `session chat` workflows
- Done when:
  - an operator can start the review-loop flow from terminal chat without
    leaving the session to copy the session ID into a separate command

Completed in this slice:

- Added TUI command registry entries and command-palette actions for
  `Review: Create Changeset`, `Review: Refresh Inventory`,
  `Review: Open Dashboard`, `Review: Generate Lifecycle Brief`,
  `Review: Preview Verification`, `Review: Inspect Handoff`, and
  `Review: Show Feedback Status`.
- Added `/review` slash commands with `/changeset` compatibility aliases for
  create, status, refresh, dashboard handoff, lifecycle brief generation,
  verification preview, handoff readiness, and feedback status.
- Added a review-loop action boundary to the interactive terminal client so
  local TUI sessions use existing changeset services and daemon-backed TUI
  sessions use existing changeset HTTP routes.
- Defaulted `/review create` to current-session `workspace-diff` changeset
  creation and post-create feedback that includes the changeset ID,
  limitations, safe next inspection command, and dashboard review route when
  available.
- Preserved the no-mutation publication boundary: shortcuts do not auto-run
  tests, stage, commit, push, open pull requests, merge, deploy, publish, or
  imply reviewer approval.
- Updated `docs/interactive-workflows.md` and
  `docs/v13-review-loop-ux-audit.md`, and added focused TUI command/app tests
  for slash parsing, palette actions, current-session creation, and explicit
  changeset ID arguments.

### GBX-1382: Add Plain Interactive And Dashboard UX Parity

- Status: `TODO`
- Depends on: `GBX-1381`
- Goal: make the in-session review entry points discoverable outside the
  full-screen TUI and complete the dashboard handoff
- Deliverables:
  - plain-mode slash command support or explicit documented fallback if a
    command is intentionally TUI-only
  - dashboard route handoff from terminal output to the changeset review detail
  - dashboard quick actions for refresh, lifecycle brief, verification preview,
    manual evidence attachment, feedback status, and handoff posture
  - updated help text, command guide, getting-started, and interactive workflow
    docs
- Implementation notes:
  - preserve compatibility for non-TTY and CI-like environments
  - avoid invisible background actions; every evidence mutation should show the
    created or updated evidence ID
  - keep dashboard actions read-only or evidence-only unless a separate
    approval-gated task says otherwise
- Tests and validation included in task:
  - plain interactive command tests
  - dashboard route and component tests
  - command guide tests
  - frontend build and packaged static asset freshness
- Done when:
  - TUI, plain interactive mode, and dashboard tell a coherent story for
    starting and continuing review-loop work

---

## Phase 139: V13 Eval, Dogfooding, Gate, And Release Signoff

### GBX-1390: Add Deterministic v13 Replay And Eval Cases

- Status: `TODO`
- Depends on: `GBX-1382`
- Goal: promote stable review-loop behavior into deterministic release
  authority
- Deliverables:
  - eval cases for feedback creation, response tracking, manual evidence,
    stale verification after fixups, lifecycle brief generation, handoff
    readiness, publication-boundary non-claims, and in-session changeset UX
  - release-candidate profile updates
  - replay normalization for new event families
  - coverage audit updates for v13 capabilities
- Implementation notes:
  - keep live browser, provider, accessibility, and dogfooding evidence advisory
    unless a fixture-backed contract is added
  - avoid brittle screenshots or timing-dependent browser flows in deterministic
    evals
  - include negative cases for automatic commit, push, PR, and merge non-claims
- Tests and validation included in task:
  - eval unit tests
  - replay/eval integration tests
  - `glassbox eval audit --profile release-candidate --cwd .`
  - focused eval runs for new cases
- Done when:
  - stable v13 review-loop behavior has deterministic release coverage

### GBX-1391: Add v13 Release Gate

- Status: `TODO`
- Depends on: `GBX-1390`
- Goal: create the automated release-candidate gate for the v13 milestone
- Deliverables:
  - `scripts/validate_v13_release_gate.py`
  - `docs/v13-release-gate.md`
  - stage plan for inherited v12 checks, v13 review-loop evals, package
    contents, installed smoke, generated API freshness, TUI command coverage,
    dashboard build, and advisory provider/browser/accessibility evidence
  - retained `summary.json` with blocking and advisory sections
- Implementation notes:
  - keep provider, live browser, accessibility, and manual evidence advisory
    unless deterministic tasks promote them
  - make skipped advisory evidence explicit and structured
  - keep raw `.glassbox` evidence out of git
- Tests and validation included in task:
  - release gate unit tests
  - dry-run gate validation
  - package contents tests if release docs or evals are added
- Done when:
  - `uv run python scripts/validate_v13_release_gate.py --dry-run` can explain
    exactly what would block or advise a v13 release candidate

### GBX-1392: Run V13 Dogfooding Passes

- Status: `TODO`
- Depends on: `GBX-1391`
- Goal: use the v13 review-loop workflows on ordinary local work before release
  signoff
- Deliverables:
  - `docs/v13-dogfooding-summary.md`
  - retained local evidence under `.glassbox/releases/gbx-1392-dogfooding/`
  - dogfooding passes for review feedback, fixup responses, manual evidence,
    browser/dashboard evidence, lifecycle briefs, stale verification, handoff
    readiness, and in-session changeset UX
  - friction findings grouped by product area with dispositions
- Implementation notes:
  - record where the operator still had to infer state manually
  - do not expand scope during dogfooding; file follow-up tasks instead
  - keep provider and live browser evidence advisory unless explicitly promoted
  - prefer the sequential review-loop order recommended by v13 docs
- Tests and validation included in task:
  - focused docs tests for dogfooding summary links
  - rerun narrow checks for any fixes made during dogfooding
- Done when:
  - dogfooding findings are classified as fixes, docs, tests/evals, accepted
    risks, or post-v13 follow-ups

### GBX-1393: Publish V13 Release-Candidate Guide

- Status: `TODO`
- Depends on: `GBX-1391`, `GBX-1392`
- Goal: publish the operator-facing v13 release-candidate narrative and final
  milestone decision
- Deliverables:
  - `docs/v13-release-candidate.md`
  - release-candidate guide covering supported operating model, validation path,
    evidence expectations, advisory evidence, residual risks, deliberate
    non-goals, release decision, and related files
  - docs hub and root README updates if v13 becomes the active implementation
    track
  - retained release evidence under `.glassbox/releases/gbx-1393-v13-release-candidate/`
- Implementation notes:
  - name remaining non-goals and known residual risks clearly
  - avoid overclaiming review approval, publication readiness, provider
    reliability, accessibility coverage, browser evidence, or automatic git
    mutation
  - keep package version policy aligned with [version-release-policy.md](./version-release-policy.md)
- Tests and validation included in task:
  - `uv run python scripts/validate_v13_release_gate.py`
  - `uv run pytest tests/unit/test_release_candidate_docs.py -q`
  - final docs link review
  - package contents validation if release docs are packaged
- Done when:
  - the v13 release candidate has a coherent guide, retained evidence, accepted
    residual-risk list, and explicit GO/NO-GO decision

## V13 Release-Candidate Readiness Checklist

Before treating a build as the v13 release candidate, complete this list:

- The v13 review-loop contract and residual-risk audit are published and linked
  from the docs hub.
- Review feedback events, projections, query services, CLI, API, and dashboard
  surfaces rebuild from canonical events.
- Review responses and fixup inventory deltas can explain what changed after
  feedback without retaining raw diffs as review summaries.
- Manual evidence attachments distinguish manual/external evidence from
  retained Glassbox command evidence.
- Browser, dashboard, and accessibility evidence has structured advisory
  retention with bounded claims and non-claims.
- Verification readiness accounts for review-driven fixups, stale checks,
  topology impacts, and manual evidence limitations.
- Lifecycle review briefs and evidence exports include feedback, responses,
  manual evidence, live evidence summaries, stale verification, accepted risks,
  and publication-boundary posture.
- Handoff and commit preparation explain unresolved feedback, stale evidence,
  dirty workspace ambiguity, local-only evidence, and safe next commands without
  staging, committing, pushing, opening a pull request, or merging.
- Integrated terminal and dashboard UX lets an operator start review-loop work
  from `glassbox session chat` without copying the current session ID into a
  separate command.
- Deterministic v13 eval cases and coverage mappings pass in the
  release-candidate profile.
- `uv run python scripts/validate_v13_release_gate.py` passes and writes
  retained `summary.json` with blocking and advisory sections.
- Dogfooding findings have dispositions as fixes, docs, tests/evals, accepted
  risks, or post-v13 follow-ups.
- Raw `.glassbox` state is not committed; reviewer-safe lifecycle summaries are
  used for handoff and release review.

## Deliberate V13 Non-Goals

v13 deliberately does not introduce:

- hosted code review
- hosted review comment synchronization
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
- indefinite unattended autonomy

These may be revisited in future milestones only with a new product contract,
safety model, evidence policy, remote-collaboration model, and explicit
operator semantics.
