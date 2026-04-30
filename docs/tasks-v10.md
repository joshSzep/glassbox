# Glassbox v10 Tasks

For the docs hub and operator guides, start at [README.md](./README.md). This
file is the v10 task graph for evolving the v9 public-baseline product into a
runtime that can safely handle long-running local agent work.

## Purpose

This document defines Glassbox v10: the long-running-task reliability milestone
after the v9 public-baseline and adoption milestone in [tasks-v9.md](./tasks-v9.md).

It is written in the same execution style as [tasks-v1.md](./tasks-v1.md),
[tasks-v2.md](./tasks-v2.md), [tasks-v3.md](./tasks-v3.md),
[tasks-v4.md](./tasks-v4.md), [tasks-v5.md](./tasks-v5.md),
[tasks-v6.md](./tasks-v6.md), [tasks-v7.md](./tasks-v7.md),
[tasks-v8.md](./tasks-v8.md), and [tasks-v9.md](./tasks-v9.md): explicit
dependencies, small vertical slices, concrete deliverables, and quality
requirements attached directly to the work.

The v2 through v9 work established the durable local runtime, event-sourced
SQLite store, daemon ownership model, packaged dashboard, full-screen terminal
client, cancellation, replay/eval release contracts, provider diagnostics,
task plans, autonomy budgets, background jobs, workspace memory, repository
intelligence, verify-repair loops, branch search, dashboard cockpit surfaces,
and public operator docs.

The v10 goal is not simply to let the model do more things. The v10 goal is to
make longer work survivable:

- long turns and background continuations should be restartable at explicit
  boundaries
- operator-visible state should not disappear when a process exits, a stream
  disconnects, or a provider call fails
- context should compact into reviewable artifacts with provenance instead of
  silently vanishing into prompt text
- tool attempts should retain partial evidence, heartbeats, retry posture, and
  safe-to-resume guidance
- dashboard and terminal surfaces should answer whether the agent is still
  making coherent progress
- verification should happen incrementally across the run, not only at the end
- budgets should include time, checkpoint, and unattended-duration limits
- release evidence should prove interruption, compaction, recovery, and
  long-run cockpit behavior deterministically

The v10 thesis is:

- preserve local-first operation and workspace-owned state
- preserve canonical events as the source of truth
- preserve one local mutation owner per workspace
- preserve deterministic replay and eval as release authority
- make long-running work inspectable before making it more autonomous
- prefer durable checkpoints over process-local inference
- make compaction an explicit artifact-backed product surface, not hidden
  prompt sludge
- keep the operator able to pause, resume, approve, deny, cancel, fork, verify,
  and recover long work from both terminal and dashboard surfaces
- avoid hosted orchestration, distributed worker fleets, hidden provider-side
  memory, and simultaneous multi-writer mutation in this milestone

## Current Baseline Before V10 Execution

Treat the following as the starting point for every task in this document:

- [v9-release-candidate.md](./v9-release-candidate.md) records the supported v9
  operating model and residual risks
- `glassbox session chat` remains the primary conversational surface
- the dashboard is a packaged Next.js static export served by FastAPI
- runtime state is local to `.glassbox/` by default and backed by canonical
  SQLite events plus rebuildable projections
- daemon ownership provides one workspace-scoped runtime owner and background
  job worker
- task plans, background jobs, autonomy budgets, branch search, workspace
  memory, repository index, and verification evidence exist as operator-visible
  surfaces
- replay and eval cases live in `evals/` as repository-owned behavioral
  contracts
- provider diagnostics, provider recommendations, and provider canaries remain
  advisory beside deterministic replay/eval evidence
- cancellation is persisted as event evidence, but active model calls and some
  in-flight tool state still have process-local recovery limits
- runtime context includes transcript history, runtime notes, working-set
  summaries, workspace memory, repository index slices, and artifact-backed
  failure digests, but compaction is not yet a first-class durable workflow
- the dashboard cockpit can identify next actions, recovery cues, task evidence,
  provider posture, and memory/index state, but it is not yet optimized for
  multi-hour progress monitoring
- long-running work is possible only when the operator and live process can keep
  enough context, attention, and provider continuity alive

## v10 Long-Running Task Findings

Treat these findings as evidence that should steer the first implementation
slices:

- the event model is strong, but some long-running boundaries still rely on
  process-local state for live model calls, tool attempts, and suspension
  reconstruction
- task plans are durable, but they do not yet carry a compact, authoritative
  "where we are and what comes next" checkpoint record
- background jobs have leases, recovery, and retry posture, but long command
  and test attempts need better partial-output and safe-resume evidence
- context assembly is rich, but compaction is not yet an operator-reviewable
  artifact with provenance back to events, transcript messages, files, and
  verification output
- a long transcript can outgrow human review even when the event store remains
  correct
- the dashboard can inspect work, but a long-running operator needs heartbeat,
  stuck-state, checkpoint, compaction, budget, and verification posture on the
  first screen
- autonomy budgets exist, but long work needs time-window, unattended-duration,
  checkpoint-approval, and confidence-decay semantics
- verification loops exist, but long tasks need incremental last-known-good
  evidence and stale-verification warnings as the workspace changes
- provider failures are currently survivable in narrow cases, but multi-hour
  work should expect retryable model errors, lost streams, malformed tool calls,
  and provider-specific degradation
- release evidence should prove interruption and recovery paths, not only happy
  path task completion

## Agent Execution Rules

These rules apply to every task in this file.

1. Respect dependency order. Do not start a task until its dependencies are
   complete unless the task explicitly says it can proceed in parallel.
2. Preserve the event-sourced source-of-truth rule. Checkpoints, compactions,
   tool attempts, model-call recovery evidence, verification ledgers, budget
   windows, and long-run cockpit summaries must be recorded in canonical events
   or explicitly rebuildable derived state.
3. Preserve local-first operation. Do not introduce a hosted control plane,
   cloud authority for workspace ownership, remote worker fleet, or external
   service dependency for v10 readiness.
4. Preserve deterministic release blocking. Live-provider behavior stays
   advisory unless a task explicitly promotes a stable deterministic contract.
5. Treat compaction as evidence, not cleanup. A compaction must name its source
   range, source artifacts, scope, staleness posture, and limitations.
6. Treat checkpointing as runtime state, not prose. A checkpoint should carry
   objective, last completed step, next intended action, blockers, verification
   posture, and recovery guidance in typed fields.
7. Keep long-running work interruptible. New long-run behavior must support
   cancellation, pause, resume, stale-owner recovery, retry posture, and
   operator inspection before it becomes release-critical.
8. Prefer bounded continuation over indefinite autonomy. Long work must include
   time, tool, write, command, verification, branch, artifact, and unattended
   duration limits where relevant.
9. Keep provider recovery explicit. Retries, model switches, fallback modes, and
   degraded behavior must be visible and must not hide provider failures from
   replay/eval or operator surfaces.
10. Make dashboard and terminal next actions concrete. If work is stale,
    blocked, compacted, partially resumed, or unsafe to retry, the UI should
    name the exact command or action that inspects or resolves it.
11. Keep non-interactive commands scriptable. Checkpoint, compaction, recovery,
    verification, replay, eval, daemon, job, and release workflows should work
    in clean shell and CI-like environments.
12. Every implementation task automatically includes:
    - automated tests for new behavior
    - `ruff` formatting and lint compliance for touched Python code
    - `ty` typecheck compliance for touched Python code
    - focused `pytest` coverage for touched runtime, CLI, web, replay, eval,
      daemon, transport, store, policy, task, tool, compaction, verification,
      memory, provider, and terminal behavior
    - frontend lint, typecheck, tests, and build when the task touches
      dashboard code, generated API types, or packaged static assets
    - documentation updates when operator-visible behavior, release posture,
      provider posture, packaging, eval profiles, recovery behavior, or public
      claims change

## Completion Contract For Any Task

A task is complete only when all of the following are true:

- the implementation exists in the intended module boundary
- automated tests covering the new or moved behavior exist and pass
- lint, formatting, type checks, and focused tests pass for touched code
- frontend validation passes when dashboard, generated API types, or packaged
  static assets are touched
- deterministic replay/eval behavior remains stable or intentional drift is
  documented through the eval refresh workflow
- new public docs are accurate against command help, API behavior, and package
  contents
- new long-running behavior is bounded by typed policy, budgets, approvals,
  cancellation, checkpointing, and explicit stop reasons
- checkpoint, compaction, retry, and recovery evidence is visible through at
  least one operator surface
- no meaningful long-running state exists only in memory once the task claims
  durability
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
    cases/
    coverage.json
    impact.json
    profiles.json
docs/
```

New v10 implementation areas should prefer focused modules rather than widening
existing facades. Expected new or expanded surfaces may include:

```text
src/glassbox/runtime/long_running.py
src/glassbox/runtime/checkpoints.py
src/glassbox/runtime/context_compaction.py
src/glassbox/runtime/tool_attempts.py
src/glassbox/runtime/long_run_verification.py
src/glassbox/runtime/provider_recovery.py
src/glassbox/store/sqlite_projection_checkpoints.py
src/glassbox/store/sqlite_projection_compactions.py
src/glassbox/store/sqlite_projection_tool_attempts.py
src/glassbox/web/routes/checkpoints.py
src/glassbox/web/routes/compactions.py
frontend/components/console/long-run-cockpit/
frontend/components/console/compaction-timeline/
```

The exact file names may change during implementation, but the ownership
boundaries should remain explicit.

## Recommended Validation Commands

Use the narrowest viable validation after each task, but the baseline validation
pattern for completed v10 work should include:

```bash
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run pytest
uv run glassbox command tree
uv run glassbox eval run
uv run glassbox eval audit
uv run glassbox eval report commit-smoke push-confirmation release-candidate --output-dir .glassbox/evals/v10-release-signoff
pnpm --dir frontend lint
pnpm --dir frontend typecheck
pnpm --dir frontend test
pnpm --dir frontend build
uv build --wheel --sdist
uv run python scripts/validate_v9_release_gate.py
```

During incremental implementation, use narrower commands where possible:

```bash
uv run pytest tests/unit/test_core_events.py tests/integration/test_sqlite_event_store.py
uv run pytest tests/unit/test_context_builder.py tests/unit/test_model_loop.py
uv run pytest tests/integration/test_turn_engine.py tests/integration/test_background_jobs.py
uv run pytest tests/integration/test_web_sse_events.py tests/integration/test_web_session_snapshot.py
uv run pytest tests/unit/test_runtime_evals.py tests/integration/test_replay_runner.py
uv run ruff check src/glassbox/path.py tests/path_test.py
uv run ty check src/glassbox/path.py
uv run glassbox eval recommend src/glassbox/runtime/turn_engine.py --cwd .
pnpm --dir frontend test -- dashboard-stores session-store sse-client
pnpm --dir frontend typecheck
```

When a task touches generated frontend API types, package assets, provider
recovery, evals, release gates, or public docs, also run the relevant smoke or
dry-run command:

```bash
pnpm --dir frontend api:generate
pnpm --dir frontend build
uv run glassbox provider diagnostics --cwd . --json
uv run glassbox provider canary evidence --cwd . --json
uv run python scripts/validate_package_contents.py
uv run python scripts/validate_v9_release_gate.py --dry-run --evidence-dir .glassbox/releases/v10-inherited-gate-dry-run
```

Once `GBX-1091` exists, use the v10 gate as the canonical full validation
command:

```bash
uv run python scripts/validate_v10_release_gate.py
```

## Milestone Map

The intended v10 milestone order is:

1. v10 long-running-task contract and durability audit
2. durable event continuity and recovery boundaries
3. durable task checkpoints and continuation state
4. context compaction artifacts and prompt integration
5. resumable tool attempts and partial-output evidence
6. long-run dashboard and terminal cockpit surfaces
7. time-aware budgets and checkpoint approvals
8. incremental verification and last-known-good evidence
9. long-run memory and provider failure recovery
10. v10 eval, dogfooding, release gate, and release-candidate signoff

## Task Graph

---

## Phase 100: v10 Contract And Durability Audit

### GBX-1000: Define The v10 Long-Running-Task Contract

- Status: `DONE`
- Depends on: `GBX-993`
- Goal: convert the v9 release-candidate decision and long-running-task theme
  into one concrete v10 product contract
- Deliverables:
  - documentation update defining v10 scope, non-goals, supported long-running
    workflow set, evidence expectations, and release posture
  - explicit statement of the long-run product model: event, checkpoint,
    compaction, attempt, heartbeat, verification, recovery
  - mapping from v9 residual risks and dogfooding findings into v10 tasks,
    accepted non-goals, or explicit advisory posture
  - release-readiness checklist that names durable-event, checkpoint,
    compaction, resumable-tool, cockpit, budget-window, verification,
    provider-recovery, and replay/eval evidence separately
  - docs hub discovery once the contract exists
- Implementation notes:
  - write for operators and contributors, not only release reviewers
  - keep local-first and event-sourced boundaries framed as product strengths
  - avoid promising unattended multi-day mutation before checkpoint, budget,
    and recovery evidence exists
- Tests and validation included in task:
  - docs link review
  - command-help comparison against `glassbox command tree`
- Done when:
  - v10 has one concise contract that explains what "long-running task
    capable" means without requiring a reader to infer it from implementation
    details

### GBX-1001: Audit Process-Local State And Recovery Boundaries

- Status: `DONE`
- Depends on: `GBX-1000`
- Goal: identify every runtime state boundary that can break long-running work
  after restart, stream loss, provider error, or daemon interruption
- Deliverables:
  - audit document covering turn engine, model loop, tool execution, approval
    and ask-user suspension, background jobs, daemon ownership, SSE transport,
    context assembly, projections, replay, and dashboard reducers
  - classification for each boundary: already durable, rebuildable projection,
    recoverable but weakly surfaced, process-local, or accepted non-goal
  - prioritized list of event, projection, checkpoint, and UI work needed for
    v10
  - test inventory for existing coverage and missing recovery cases
- Implementation notes:
  - this task should not add broad behavior
  - prefer source-linked findings with concrete module ownership
  - distinguish "can resume safely" from "can explain why it cannot resume"
- Tests and validation included in task:
  - docs guardrail tests if docs inventory tests exist
  - focused characterization tests only when the audit discovers ambiguous
    current behavior
- Done when:
  - v10 implementation tasks are grounded in an explicit durability map instead
    of broad intuition

---

## Phase 101: Durable Event Continuity

### GBX-1010: Add Long-Run Lifecycle Event Vocabulary

- Status: `DONE`
- Depends on: `GBX-1001`
- Goal: add typed event payloads for long-running lifecycle boundaries that are
  currently implicit or process-local
- Deliverables:
  - event models for long-run phase changes, checkpoint creation, compaction
    creation, tool attempt heartbeat, recovery decision, and resume outcome
  - event correlation fields for task, turn, tool attempt, compaction, and
    checkpoint identifiers
  - SQLite append and projection support for new event families
  - replay normalization rules for new event families
  - tests for event serialization, schema migration, projection rebuild, and
    replay compatibility
- Implementation notes:
  - preserve existing event names and semantics unless a migration task
    explicitly changes them
  - new events should explain state transitions rather than duplicate derived
    projection fields
  - add only event families needed by v10 workflows
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_core_events.py tests/integration/test_sqlite_event_store.py`
  - focused replay bundle compatibility tests
- Done when:
  - long-running boundaries have typed canonical events that can be persisted,
    streamed, replayed, and rebuilt into projections

### GBX-1011: Strengthen Incomplete-Turn And Recovery Semantics

- Status: `DONE`
- Depends on: `GBX-1010`
- Goal: make interrupted model calls and tool loops produce explicit,
  inspectable recovery posture instead of ambiguous running state
- Deliverables:
  - durable states for active, incomplete, recoverable, abandoned, resumed, and
    non-resumable turn paths
  - recovery event emission for daemon restart, process exit, model-call
    interruption, tool-loop interruption, and projection rebuild discovery
  - CLI and status output that distinguishes active live work from stale
    incomplete work
  - dashboard cues for incomplete but recoverable turns
  - tests for restart and stale in-flight state characterization
- Implementation notes:
  - do not pretend a provider stream can be resumed unless the runtime can
    prove it
  - when exact continuation is impossible, record a safe checkpoint and next
    operator action
  - preserve existing cancellation semantics
- Tests and validation included in task:
  - focused turn engine tests
  - daemon runtime recovery tests
  - session status and dashboard snapshot tests
- Done when:
  - interrupted turns stop looking like mysterious active work and instead tell
    the operator whether to resume, retry, fork, or abandon

### GBX-1012: Make Event Delivery Cursors Robust For Long Streams

- Status: `DONE`
- Depends on: `GBX-1010`
- Goal: harden CLI and dashboard event consumption for long sessions with
  reconnects, large gaps, and projection lag
- Deliverables:
  - documented SSE cursor contract for long-running sessions
  - cursor recovery behavior when the requested sequence is compacted into a
    snapshot, projection lag exists, or event delivery drops live frames
  - transport stats surfaced in observability and dashboard recovery cues
  - frontend and TUI tests for reconnect after long gaps
  - API tests for bounded historical replay and cursor edge cases
- Implementation notes:
  - canonical events remain available even when UI detail pages are paginated
  - keep keepalive and reconnect behavior explicit
  - do not make projections authoritative for missed events
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_web_sse_events.py tests/unit/test_runtime_transport.py`
  - `pnpm --dir frontend test -- sse-client`
- Done when:
  - a dashboard or terminal can reconnect to a long-running session and explain
    whether it is live, replaying history, or degraded

---

## Phase 102: Durable Task Checkpoints

### GBX-1020: Add Durable Task Checkpoint Model And Projection

- Status: `DONE`
- Depends on: `GBX-1011`
- Goal: make "where the agent is in the work" a typed durable object rather
  than a summary inferred from transcript text
- Deliverables:
  - checkpoint event and projection model with objective, current phase, last
    completed step, next intended action, blockers, touched files, verification
    posture, budget posture, recovery notes, and source event range
  - repository methods for latest checkpoint and checkpoint history
  - checkpoint rebuild from canonical events
  - tests for checkpoint creation, update, rebuild, and stale projection health
- Implementation notes:
  - checkpoints should be task-aware but usable for sessions without durable
    task plans
  - checkpoints are not a replacement for canonical events
  - checkpoint text should be concise enough for prompts and UI cards
- Tests and validation included in task:
  - core model tests
  - SQLite projection tests
  - session/task query tests
- Done when:
  - every long-running task can expose a durable latest checkpoint and a
    checkpoint timeline
- Completed:
  - Added typed checkpoint fields for current phase, touched files, verification
    posture, budget posture, recovery guidance, and source event range.
  - Added the rebuildable `task_checkpoints` SQLite projection, latest/history
    query helpers, repository methods, projection-health table coverage, and
    focused event/projection/schema tests.

### GBX-1021: Surface Checkpoints In CLI, API, And Session Export

- Status: `DONE`
- Depends on: `GBX-1020`
- Goal: make checkpoints inspectable and portable through existing operator
  surfaces
- Deliverables:
  - CLI checkpoint inspection through session or task status surfaces
  - API response fields for latest checkpoint and checkpoint history pages
  - portable session export/import support for checkpoint events and projection
    summaries
  - docs for reading and using checkpoints during handoff
  - tests for CLI, web, and export/import behavior
- Implementation notes:
  - avoid adding a new command group unless existing session/task commands
    cannot express the workflow clearly
  - keep JSON output stable for scripts
  - imported sessions remain inspection-only unless a later task defines
    resumable custody transfer
- Tests and validation included in task:
  - CLI status tests
  - web snapshot tests
  - session export/import tests
- Done when:
  - an operator can hand off or reopen a long task and see the current
    checkpoint before reading the full transcript
- Completed:
  - Session snapshots, session summaries, CLI status, and
    `/sessions/{session_id}/checkpoints` now expose checkpoint state.
  - Session export/import carries redacted checkpoint projection summaries and
    canonical checkpoint event references for inspection-only handoff rebuilds.
  - Frontend OpenAPI schema and generated API types were refreshed for the new
    checkpoint response fields and page route.

### GBX-1022: Resume Work From Checkpoints Safely

- Status: `DONE`
- Depends on: `GBX-1021`
- Goal: let session resume and background continuation use checkpoints as
  explicit context while preserving operator control
- Deliverables:
  - resume preparation that includes latest checkpoint, limitations, unresolved
    blockers, and source provenance in turn context
  - blocked resume behavior when checkpoint state is stale, non-resumable, or
    conflicts with current workspace state
  - operator-visible reason when Glassbox chooses replay-derived context instead
    of checkpoint-derived context
  - tests for normal resume, stale checkpoint, abandoned checkpoint, and
    workspace-drift cases
- Implementation notes:
  - do not skip transcript or event context entirely; checkpoints augment
    recovery, not replace history
  - any model-facing checkpoint should include provenance and caveats
  - stale checkpoint detection can start conservative
- Tests and validation included in task:
  - turn preparation tests
  - integration resume tests
  - eval fixture for checkpoint-based recovery
- Done when:
  - resuming a long task starts from an explicit checkpoint and explains when
    the checkpoint is unsafe to trust
- Completed:
  - Added checkpoint resume classification for usable, stale, blocked,
    workspace-drifted, and non-resumable checkpoints.
  - Runtime context and prompts now include checkpoint source provenance,
    limitations, blockers, workspace drift, and replay-vs-checkpoint source
    posture.
  - `glassbox session resume` rejects unsafe checkpoint resumes with durable
    `RecoveryDecisionRecorded` and `ResumeOutcomeRecorded` evidence.

---

## Phase 103: Context Compactions

### GBX-1030: Define The Context Compaction Artifact Contract

- Status: `DONE`
- Depends on: `GBX-1020`
- Goal: make compaction a first-class artifact-backed contract with provenance,
  scope, and limitations
- Deliverables:
  - compaction artifact schema covering transcript range, task range, decisions,
    unresolved questions, assumptions, touched files, verification state,
    failures, accepted risks, and source event/artifact references
  - typed compaction event payloads and projection state
  - docs explaining when compaction happens and how operators inspect it
  - tests for schema validation and artifact integrity
- Implementation notes:
  - compaction should never silently overwrite source events
  - source range and source artifact references must be mandatory
  - compaction may be automatic or manual later, but the artifact contract comes
    first
- Tests and validation included in task:
  - core model tests
  - artifact store tests
  - docs review
- Done when:
  - a compaction can be recorded, inspected, and traced back to source evidence
- Completed:
  - Added the `context_compaction_v1` artifact schema with mandatory source
    references, source ranges, decisions, unresolved questions, assumptions,
    touched files, verification state, failures, accepted risks, and
    limitations.
  - Expanded `ContextCompactionCreated` with artifact schema/provenance counts
    and added the rebuildable `context_compactions` SQLite projection.
  - Added operator docs for compaction artifact inspection and docs-hub
    discovery.

### GBX-1031: Build Transcript And Task Compaction Service

- Status: `DONE`
- Depends on: `GBX-1030`
- Goal: generate bounded compaction artifacts from long session/task history
- Deliverables:
  - runtime service that compacts selected transcript, task, tool, verification,
    and artifact ranges into the v10 compaction schema
  - deterministic local compaction path for tests and replay fixtures
  - optional provider-assisted compaction path behind explicit provider
    readiness and redaction checks if needed
  - commands or APIs to create and inspect compactions
  - tests for small, large, interrupted, and artifact-heavy sessions
- Implementation notes:
  - deterministic compaction should exist before any live-provider-assisted
    compaction is considered release-critical
  - compaction output should be concise but not vague
  - failures to compact should not corrupt source history
- Tests and validation included in task:
  - runtime compaction tests
  - CLI tests
  - replay fixture tests
- Done when:
  - Glassbox can create an inspectable compaction artifact for a long session
    without losing source provenance
- Completed:
  - Added a deterministic provider-free compaction service that summarizes a
    selected session event range into the `context_compaction_v1` artifact
    schema and records `ContextCompactionCreated`.
  - Added `glassbox session compact` and `glassbox session compactions` for
    local creation and inspection of compaction records.
  - Added integration coverage proving CLI creation writes the artifact,
    records the canonical event, and rebuilds the projection.

### GBX-1032: Integrate Compactions Into Turn Context

- Status: `DONE`
- Depends on: `GBX-1031`, `GBX-1022`
- Goal: let the model use compactions as bounded context while keeping source
  provenance and stale-state warnings visible
- Deliverables:
  - turn context assembly rules for selecting fresh compactions, raw transcript
    windows, checkpoint summaries, workspace memory, and artifact-backed
    failure digests
  - prompt formatting that labels compaction scope, source range, freshness,
    and limitations
  - fallback behavior when compaction is stale or missing
  - replay/eval normalization for compaction-backed context
  - tests for compaction selection, stale compaction, and prompt provenance
- Implementation notes:
  - avoid hiding recent raw transcript behind old compactions
  - compaction should reduce context cost without erasing decisions and
    unresolved blockers
  - prompt text should be concise and source-labeled
- Tests and validation included in task:
  - context builder tests
  - prompt tests
  - replay/eval tests
- Done when:
  - long sessions can keep working with compacted context that remains
    inspectable and replay-aware
- Completed:
  - Runtime context now selects bounded fresh compactions and excludes stale
    compactions from active prompt context while reporting stale counts.
  - Turn prompts label compaction scope, source event range, artifact id,
    freshness, and limitations.
  - Added context-builder and prompt tests for fresh compaction selection and
    stale-compaction exclusion posture.

### GBX-1033: Add Compaction Refresh And Invalidation Workflow

- Status: `DONE`
- Depends on: `GBX-1032`
- Goal: make stale or superseded compactions visible and recoverable
- Deliverables:
  - freshness rules for compactions based on source event range, workspace
    drift, checkpoint changes, and verification changes
  - CLI/API workflow to inspect, refresh, or invalidate compactions
  - dashboard cues for stale compaction state
  - tests for refresh, invalidation, and stale prompt exclusion
- Implementation notes:
  - invalidating a compaction should not delete the artifact by default
  - stale compactions may remain useful for audit but should not silently feed
    active prompts
  - keep mutating refresh actions confirmation-gated where appropriate
- Tests and validation included in task:
  - projection tests
  - CLI/web tests
  - frontend component tests if dashboard cues are added
- Done when:
  - operators can understand and repair compaction freshness before it affects
    future turns
- Completed:
  - Added `ContextCompactionFreshnessChanged` events, projection freshness
    reason fields, superseded-by links, and conservative runtime freshness
    assessment for later checkpoints, verification, tool/artifact, and session
    events.
  - Added confirmation-gated CLI and API workflows to list, refresh, and
    invalidate context compactions while retaining original artifacts for audit.
  - Added dashboard runtime-pane stale compaction cues and refreshed generated
    OpenAPI/frontend API types.

---

## Phase 104: Resumable Tool Attempts

### GBX-1040: Add Durable Tool Attempt Records And Heartbeats

- Status: `DONE`
- Depends on: `GBX-1011`
- Goal: make long-running tool execution durable enough to inspect after
  timeout, cancellation, daemon restart, or process death
- Deliverables:
  - tool-attempt identity distinct from provider tool-call identity when needed
  - events and projections for attempt started, heartbeat, output artifact,
    completed, failed, cancelled, stale, retried, and abandoned
  - lease and heartbeat fields for long command/test attempts
  - CLI and status output for active and stale attempts
  - tests for event ordering and projection rebuild
- Implementation notes:
  - do not change short tool behavior unless necessary
  - retain compatibility with existing `tool_calls` projection
  - heartbeats should be bounded and not flood the event log
- Tests and validation included in task:
  - tool runtime tests
  - SQLite projection tests
  - command/test tool integration tests
- Done when:
  - a long-running tool attempt can be inspected as durable state independent
    of the live process that launched it
- Completed:
  - Added the `tool_attempts` SQLite projection rebuilt from
    `ToolAttemptHeartbeat` events, including attempt identity, tool-call
    correlation, status, heartbeat timing and expiry, progress, output artifact
    reference, retry posture, and last source sequence.
  - Tool execution now emits bounded attempt heartbeats for started/running and
    terminal succeeded, failed, or cancelled states without changing the
    existing `tool_calls` projection contract.
  - Added `glassbox session tool-attempts`, recent attempt lines in
    `glassbox session status`, operator docs, schema/query coverage, and turn
    engine coverage.
  - Replay eval normalization now canonicalizes generated tool-attempt, tool
    call, and turn identifiers for `ToolAttemptHeartbeat` long-run evidence,
    and the affected eval baselines were refreshed with explicit GBX-1040
    history entries.

### GBX-1041: Preserve Partial Tool Output As Managed Artifacts

- Status: `DONE`
- Depends on: `GBX-1040`
- Goal: ensure long command and test runs leave useful partial evidence even
  when interrupted or truncated
- Deliverables:
  - streaming output artifact writer for stdout/stderr with size limits,
    checksums, and redaction posture
  - event references from tool attempts to partial-output artifacts
  - CLI/API artifact inspection that distinguishes partial, final, truncated,
    and redacted outputs
  - tests for timeout, cancellation, truncation, and daemon-death scenarios
- Implementation notes:
  - keep artifact pressure and retention rules aligned with v9 cleanup
    guidance
  - avoid writing secrets from environment variables into summaries
  - raw output may be artifact-backed while UI summaries remain compact
- Tests and validation included in task:
  - artifact store tests
  - command tool tests
  - artifact retention tests
- Done when:
  - interrupted long tools leave enough evidence to diagnose or retry safely
- Completed:
  - Command and test tool executions now persist managed `tool_output_*`
    artifacts containing stdout/stderr, execution-envelope metadata, integrity
    metadata, and final/partial, complete/truncated, redacted/unredacted
    posture.
  - Terminal `ToolAttemptHeartbeat` events reference the output artifact ID so
    the `tool_attempts` projection links attempts to retained evidence.
  - `glassbox artifacts inspect` and JSON output include referenced artifact
    kind metadata, making partial/final/truncated/redaction posture visible in
    artifact inspection and retention workflows.

### GBX-1042: Add Safe-To-Retry And Resume Classification

- Status: `DONE`
- Depends on: `GBX-1041`
- Goal: make retry and resume posture explicit for long-running tool attempts
- Deliverables:
  - classification model for retryable, unsafe-to-retry, idempotent, unknown,
    already-running, and abandoned attempts
  - command/test-specific heuristics for common safe and unsafe retry cases
  - policy integration so risky retry decisions require approval when
    appropriate
  - CLI/dashboard explanation for why a retry is allowed, blocked, or
    approval-gated
  - tests for classification and policy behavior
- Implementation notes:
  - be conservative when side effects are unknown
  - retry classification is evidence for operator decision-making, not a
    guarantee of semantic safety
  - workspace-write and command risks still honor tool policy
- Tests and validation included in task:
  - policy tests
  - tool-attempt tests
  - dashboard action tests if retry actions are exposed
- Done when:
  - retrying a long command or test attempt is explainable and bounded instead
    of ad hoc
- Completed:
  - Added typed retry classifications for retryable, unsafe-to-retry,
    idempotent, unknown, already-running, and abandoned tool attempts, with
    approval-gating and policy-reason fields persisted through
    `ToolAttemptHeartbeat` and the `tool_attempts` projection.
  - Added conservative command/test retry heuristics for repeatable
    verification, static checks, read-only inspection, unknown commands, shell
    redirection, dependency mutation, git mutation, and destructive command
    families.
  - Surfaced retry posture in `glassbox session tool-attempts`,
    `glassbox session status`, session snapshots, generated frontend API
    types, and dashboard Actions views.
  - Added unit, projection, CLI, web schema, web snapshot, and frontend
    component coverage for classification, persistence, and operator display.

### GBX-1043: Expose Tool Attempt Recovery Actions

- Status: `DONE`
- Depends on: `GBX-1042`
- Goal: let operators recover stale or failed long-running attempts from CLI
  and dashboard surfaces
- Deliverables:
  - CLI actions for inspect, retry, abandon, and attach-to-output where
    practical
  - dashboard recovery controls with explicit confirmation for mutating retry
    or abandon actions
  - API routes or existing route extensions for attempt recovery
  - tests for successful retry, blocked retry, abandon, stale attempt, and
    dashboard confirmation paths
- Implementation notes:
  - default dashboard cues should remain read-only until the operator confirms
  - do not expose destructive recovery actions without backend policy checks
  - preserve one local mutation owner per workspace
- Tests and validation included in task:
  - CLI tests
  - web route tests
  - frontend component tests
- Done when:
  - stale or failed tool attempts have a clear recovery path with retained
    evidence
- Completed:
  - Added a durable tool-attempt recovery service for inspection, retained
    output reading, explicit abandonment, and policy-checked retry from retained
    `ModelToolCallRequested` arguments.
  - Added `glassbox session tool-attempt inspect|output|retry|abandon` plus API
    routes for inspect, retry, and abandon with confirmation gates for mutating
    actions.
  - Dashboard Actions now shows confirmed retry and abandon controls beside
    retained retry posture, with generated OpenAPI/frontend API types refreshed.
  - Added focused CLI, web route, frontend store, and component coverage for
    successful retry, blocked confirmation, abandonment, and recovery controls.

---

## Phase 105: Long-Run Dashboard And Terminal Cockpit

### GBX-1050: Define The Long-Run Cockpit Contract

- Status: `DONE`
- Depends on: `GBX-1021`, `GBX-1030`, `GBX-1040`
- Goal: define how terminal and dashboard surfaces should summarize long-running
  progress, risk, and recovery
- Deliverables:
  - dashboard and terminal information-architecture contract for active phase,
    checkpoint, heartbeat, compaction, tool attempts, verification, budget,
    provider posture, and next action
  - priority rules for pending approvals, questions, stale attempts, stale
    compactions, stale verification, provider degradation, and daemon recovery
  - responsive and keyboard expectations for long-run views
  - backend data-source map for each surface
- Implementation notes:
  - preserve existing deep inspection panes
  - do not add tutorial text to the app chrome
  - cockpit should answer: is it alive, is it coherent, what changed, and what
    needs me?
- Tests and validation included in task:
  - docs review against API and frontend component boundaries
- Done when:
  - frontend and terminal implementation has a clear long-run operator-priority
    contract rather than ad hoc panel additions
- Completed:
  - Added [long-run-cockpit-contract.md](./long-run-cockpit-contract.md) with
    the v10 terminal and dashboard cockpit purpose, surface contract, priority
    rules, data-source map, recovery guidance, responsive expectations,
    keyboard expectations, and follow-on task boundaries.
  - Linked the new contract from the docs hub and dashboard guide so cockpit
    implementers can discover the v10 priority rules beside the older v9
    dashboard cockpit contract.

### GBX-1051: Add Heartbeat, Stuck-State, And Progress Summary Surfaces

- Status: `DONE`
- Depends on: `GBX-1050`, `GBX-1040`
- Goal: make active long work visibly alive, stuck, paused, or stale
- Deliverables:
  - backend summary model for heartbeat, current phase, last event, current
    attempt, elapsed time, and stuck-state reason
  - dashboard workspace overview and session inspector cues
  - terminal header or action strip updates for long-running status
  - tests for healthy active work, stale heartbeat, stuck attempt, paused work,
    and completed work
- Implementation notes:
  - stuck detection should be conservative and explainable
  - heartbeat absence should not automatically imply failure when a phase is
    known to be quiet
  - preserve existing session priority rules
- Tests and validation included in task:
  - session query tests
  - frontend store/component tests
  - TUI reducer/widget tests
- Done when:
  - an operator can glance at terminal or dashboard and tell whether long work
    is making progress
- Completed:
  - Added a derived `LongRunStatusRecord` summary on session summaries and
    snapshots, covering state, heartbeat age/expiry, current phase, latest
    durable event, current tool attempt, elapsed time, stuck reason, and
    progress summary.
  - Surfaced long-run state in `glassbox session status`, operator-console
    priority rows, workspace overview badges, and selected-session header
    facts, with stale and stuck states promoted into action-needed priority.
  - Refreshed OpenAPI/frontend generated API types and added backend,
    frontend, and web snapshot coverage for healthy active work, stale
    heartbeat, stuck attempt, paused work, and completed work.

### GBX-1052: Add Checkpoint And Compaction Timeline Views

- Status: `DONE`
- Depends on: `GBX-1051`, `GBX-1032`
- Goal: make long-running history navigable without reading the entire
  transcript
- Deliverables:
  - dashboard timeline combining checkpoints, compactions, tool attempts,
    verification events, approvals, questions, cancellations, and recovery
    decisions
  - drill-down links to source event ranges and artifacts
  - CLI summary for latest checkpoint and recent compactions
  - tests for timeline ordering, source links, empty state, and large sessions
- Implementation notes:
  - do not duplicate full event logs inside the timeline
  - event-log and artifact panes remain the detail authority
  - timeline should be useful with partial projection lag
- Tests and validation included in task:
  - frontend component tests
  - web pagination tests if new pages are added
  - CLI status tests
- Done when:
  - long-running work has a readable progress history that points back to
    canonical evidence
- Completed:
  - Added a long-run evidence section to the dashboard Timeline pane that
    combines checkpoint history, fresh and stale compactions, recent tool
    attempts, pending approvals/questions, recovery posture, and loaded
    verification/cancellation/recovery event markers.
  - Timeline rows now preserve source event ranges, canonical event sequence
    references, tool-attempt IDs, checkpoint IDs, compaction IDs, and artifact
    IDs without duplicating the full raw event log.
  - `glassbox session status` now summarizes recent compactions alongside the
    latest checkpoint and long-run heartbeat state.
  - Added component and CLI coverage for ordering, source links, empty state,
    bounded large-session timelines, and compaction summaries.

### GBX-1053: Add Long-Run Recovery Action Guidance

- Status: `DONE`
- Depends on: `GBX-1052`, `GBX-1043`
- Goal: make common long-run recovery actions discoverable and safe
- Deliverables:
  - dashboard and CLI next-action guidance for stale tool attempts, stale
    compactions, incomplete turns, stale verification, provider degradation,
    and daemon interruption
  - command-copy affordances for read-only inspection steps
  - explicit confirmation for retry, abandon, refresh compaction, or resume
    actions
  - tests for competing recovery states and command text
- Implementation notes:
  - safe read-only inspection commands should appear before mutating recovery
    commands
  - avoid hiding raw error evidence behind generic guidance
  - recovery guidance must stay aligned with CLI command help
- Tests and validation included in task:
  - frontend tests
  - CLI formatter tests
  - command guide tests if discovery changes
- Done when:
  - long-run failure states tell the operator exactly how to inspect and
    recover them
- Completed:
  - Added selected-session Recovery guidance in the dashboard Actions pane for
    stale/failed tool attempts, stale compactions, incomplete turn recovery,
    stale verification evidence, provider posture, and daemon or stream
    interruption.
  - Kept guidance inspection-first with copyable read-only commands, while
    retry, abandon, compaction refresh, and resume paths remain explicit
    operator actions or confirmation-gated CLI commands.
  - Added terminal status recovery guidance for stale/failed tool attempts,
    stale compactions, and incomplete-turn resume posture.
  - Added component and CLI tests for competing recovery states and command
    text.

---

## Phase 106: Time-Aware Budgets And Checkpoint Approvals

### GBX-1060: Add Time-Window Fields To Autonomy Budgets

- Status: `DONE`
- Depends on: `GBX-1020`
- Goal: make long-running autonomy budgets account for unattended duration,
  checkpoint cadence, and wall-clock windows
- Deliverables:
  - budget fields for max unattended duration, checkpoint interval, quiet
    window policy, max retry delay, and checkpoint approval requirement
  - budget decision events and projections for time-window enforcement
  - CLI/API output for remaining time and next checkpoint requirement
  - tests for budget validation, expiration, and projection rebuild
- Implementation notes:
  - existing budgets should migrate conservatively
  - time-aware budget fields should not make manual mode surprising
  - wall-clock behavior must be deterministic enough for tests
- Tests and validation included in task:
  - autonomy budget tests
  - runtime budgeting tests
  - CLI/API tests
- Done when:
  - long-running autonomy has explicit time limits instead of only tool and
    operation counts
- Completed:
  - Added typed budget fields for max unattended duration, checkpoint interval,
    quiet-window policy, max retry delay, and checkpoint approval requirement,
    with conservative defaults for older budget JSON.
  - Extended budget usage, remaining counters, evaluation, and exhausted
    decisions to enforce configured unattended, checkpoint, and retry-delay
    windows deterministically.
  - Surfaced remaining unattended time, next checkpoint due time, retry-delay
    budget, quiet-window policy, and checkpoint-approval requirement through
    the budget posture read model, session API responses, and CLI status.
  - Updated v10/database/cockpit documentation and refreshed API schema/types.

### GBX-1061: Add Continue-For-N-Minutes Approval Workflow

- Status: `DONE`
- Depends on: `GBX-1060`, `GBX-1051`
- Goal: let operators grant bounded continuation windows without turning on
  indefinite autonomy
- Deliverables:
  - approval request and resolution semantics for continuing until a deadline,
    checkpoint, or budget limit
  - CLI and dashboard actions to approve a bounded continuation window
  - persisted stop reason when the continuation window expires
  - tests for approval, expiry, denial, and overlapping continuation windows
- Implementation notes:
  - continuation windows should be tied to a task or session checkpoint
  - expired windows should stop cleanly with evidence
  - do not let continuation approval bypass hard policy invariants
- Tests and validation included in task:
  - approval workflow tests
  - background continuation tests
  - frontend action tests
- Done when:
  - an operator can safely say "continue for a bit" and see when that authority
    ends
- Completed:
  - Added canonical `ContinuationWindowRequested`,
    `ContinuationWindowResolved`, and `ContinuationWindowExpired` events for
    bounded continuation authority and stop evidence.
  - Added CLI and API/dashboard actions for approving a task continuation for a
    fixed number of minutes, with optional checkpoint linkage and overlap
    rejection for active windows on the same task.
  - Persisted approved deadlines in background continuation job payloads and
    made the worker pause expired jobs with a durable
    `continuation_window_expired` task stop reason.
  - Added backend, CLI, API, frontend API-client, and generated schema/type
    coverage for approval, denial, expiry, and overlapping windows.

### GBX-1062: Add Pause Windows And Scheduled Stop Reasons

- Status: `DONE`
- Depends on: `GBX-1061`
- Goal: support predictable pauses for long work without creating a general
  scheduler or hosted automation system
- Deliverables:
  - local-only pause-window model for "pause before time", "pause after
    checkpoint", and "pause before risky action"
  - persisted pause and stop reasons in task/session state
  - CLI/API status and dashboard cue for scheduled pause posture
  - tests for scheduled pause, manual override, daemon restart, and expired
    window behavior
- Implementation notes:
  - this is local runtime behavior, not cloud scheduling
  - avoid calendar integration or notification systems in v10
  - pause windows should be explicit and operator-visible
- Tests and validation included in task:
  - runtime budget tests
  - background job tests
  - status/dashboard tests
- Done when:
  - long-running work can pause at predictable local boundaries with durable
    reasons
- Completed:
  - Added canonical `PauseWindowScheduled`, `PauseWindowTriggered`, and
    `PauseWindowCancelled` events plus a local pause-window helper that rebuilds
    active task windows from canonical events.
  - Added CLI and API/dashboard actions to schedule pause-before-time,
    pause-after-checkpoint, and pause-before-risky-action windows, plus manual
    cancellation/override.
  - Made background task continuation stop at active pause windows before
    mutating work, recording `PauseWindowTriggered`, pausing the task with
    `scheduled_pause`, and retaining the stop reason in job state.
  - Added runtime, background job, CLI, API, frontend API-client, generated
    schema/type, and docs coverage for scheduled pause and override behavior.

---

## Phase 107: Incremental Verification

### GBX-1070: Add Long-Run Verification Ledger

- Status: `DONE`
- Depends on: `GBX-1020`, `GBX-1041`
- Goal: track verification evidence across a long task as a durable ledger
  instead of a final checklist
- Deliverables:
  - verification ledger projection connecting task steps, changed paths, test
    targets, eval recommendations, command attempts, failures, repairs, and
    accepted risks
  - event references for last successful check and latest failed check
  - CLI/API output for current verification posture
  - tests for ledger rebuild and multi-step verification history
- Implementation notes:
  - reuse existing task verification events where possible
  - ledger is a read model over canonical events, not a second source of truth
  - support sessions without task plans where practical
- Tests and validation included in task:
  - verification model tests
  - task projection tests
  - session/task query tests
- Done when:
  - a long task can explain what has been verified so far and what still needs
    proof
- Completed:
  - Added the rebuildable `task_verification_ledger` SQLite projection from
    canonical task verification events, including check kind/source, command
    argv, changed paths, eval links, attempts, latest artifact, latest failed
    check, last successful check, accepted risks, and source sequence fields.
  - Added task verification ledger models, repository/query helpers, task
    detail API fields, generated frontend API types, and `glassbox task show`
    posture output.
  - Updated verification and database docs, plus focused unit, projection,
    CLI, web, and frontend fixture coverage for ledger rebuild and task-detail
    posture.

### GBX-1071: Detect Stale Verification After Workspace Drift

- Status: `DONE`
- Depends on: `GBX-1070`
- Goal: warn when previous verification no longer covers the current workspace
  state
- Deliverables:
  - changed-path digest or diff-summary linkage from verification records to
    current workspace state
  - stale verification detection for edits after last known good check
  - dashboard and CLI cues for stale or missing verification
  - tests for clean state, edit-after-test, docs-only drift, and generated-file
    drift
- Implementation notes:
  - stale detection should be conservative and explainable
  - docs-only changes may not require full behavioral replay unless they touch
    command, eval, release, or policy contracts
  - reuse `workspace_diff_summary` and eval recommendation logic where possible
- Tests and validation included in task:
  - diff summary tests
  - eval recommendation tests
  - dashboard cue tests
- Done when:
  - long-running work does not claim old verification as current after the
    workspace has changed materially
- Completed:
  - Added read-time verification drift assessment that compares the
    `task_verification_ledger` changed-path coverage with the current local git
    diff and records changed-path digests, material paths, docs-only drift,
    generated-file drift, stale verification IDs, stale paths, and explicit
    unknown/not-assessed posture.
  - Surfaced drift posture through task detail API responses,
    `glassbox task show`, generated frontend API types, and dashboard task
    verification cues.
  - Added tests for clean workspaces, edit-after-test stale verification,
    docs-only drift, generated-file drift, API exposure, CLI JSON shape, and
    dashboard rendering.

### GBX-1072: Add Last-Known-Good And Repair History

- Status: `DONE`
- Depends on: `GBX-1071`
- Goal: make verification recovery easier by recording the last known good
  point and repair attempts
- Deliverables:
  - durable last-known-good marker tied to checkpoint, diff summary,
    verification result, and artifact evidence
  - repair history summary for repeated failures and retry loops
  - CLI/dashboard rendering for last known good, current drift, and repair
    attempts
  - tests for pass, fail, repair, accepted residual risk, and regression cases
- Implementation notes:
  - last-known-good should not imply clean git state unless verified
  - repair history should compact repeated output into artifacts and summaries
  - accepted residual risk remains explicit operator evidence
- Tests and validation included in task:
  - verification loop tests
  - task detail tests
  - frontend evidence pane tests
- Done when:
  - a long task can recover from failures with a clear proof trail instead of
    repeating tests blindly
- Completed:
  - Added task detail `last_known_good` and `repair_history` views derived from
    durable verification events, the verification ledger projection, task
    checkpoint projection, artifact links, and drift assessment.
  - Surfaced last-known-good and repair status through `glassbox task show`,
    task detail API responses, generated frontend API types, and dashboard task
    evidence rows.
  - Added focused web/API, CLI, verify-repair, drift, and dashboard tests for
    pass, repair, regression, stale proof, and retained failure-artifact
    evidence.

### GBX-1073: Improve Eval Recommendations For Long-Running Work

- Status: `DONE`
- Depends on: `GBX-1072`
- Goal: make eval recommendation account for checkpoints, stale verification,
  compactions, and long-run risk
- Deliverables:
  - recommendation output that distinguishes immediate, checkpoint, pre-resume,
    pre-merge, and release-candidate verification surfaces
  - path and event mappings for checkpoint, compaction, tool-attempt, provider
    recovery, and long-run cockpit changes
  - tests for representative v10 path changes and execution plans
  - docs update for long-run verification workflow
- Implementation notes:
  - recommendations remain advisory until executed
  - live-provider canary recommendations stay advisory and explicitly skipped
    from deterministic plans
  - keep JSON stable for automation
- Tests and validation included in task:
  - eval recommendation unit tests
  - focused CLI tests
- Done when:
  - developers get an explainable verification plan for long-running-task
    infrastructure changes
- Completed:
  - Added `long_run_surfaces` recommendation output for immediate, checkpoint,
    pre-resume, pre-merge, and release-candidate verification timing while
    preserving existing case/profile/suggested-command JSON fields.
  - Added v10 impact mappings for checkpoint/compaction recovery,
    tool-attempt recovery, and long-run cockpit changes, with provider canary
    recommendations still skipped from deterministic plans unless explicitly
    selected.
  - Updated CLI rendering, replay/eval docs, and focused unit/CLI coverage for
    representative v10 paths and long-run execution-plan output.

---

## Phase 108: Long-Run Memory And Provider Failure Recovery

### GBX-1080: Capture Long-Run Memory Candidates

- Status: `DONE`
- Depends on: `GBX-1032`, `GBX-1072`
- Goal: turn durable findings from long tasks into reviewable workspace memory
  candidates without creating hidden memory
- Deliverables:
  - candidate extraction from checkpoints, compactions, repeated failures,
    last-known-good records, verified commands, and accepted residual risks
  - provenance back to source events and artifacts
  - dashboard/CLI review flow for long-run memory candidates
  - tests for candidate usefulness, dedupe, redaction, confirmation, and
    rejection
- Implementation notes:
  - memory remains review-gated
  - do not promote provider outputs, private paths, or secrets without
    redaction
  - stale or invalidated compactions should not create active memory by default
- Tests and validation included in task:
  - workspace memory tests
  - compaction provenance tests
  - dashboard memory tests
- Done when:
  - long-running work can produce durable local learning while preserving
    operator review and provenance
- Completed:
  - Added review-only memory candidates from long-run checkpoints, fresh
    compactions, last-known-good verification records, verified commands,
    repeated verification failures, and accepted residual risks.
  - Preserved provenance back to canonical source event sequences and artifact
    IDs where available, while keeping stale compactions inactive and running
    redaction before review.
  - Reused the existing CLI/API/dashboard candidate review flow and added
    focused workspace-memory tests for usefulness, dedupe, redaction,
    rejection/confirmation posture, provenance, and stale-compaction exclusion.

### GBX-1081: Add Provider Failure Recovery State

- Status: `DONE`
- Depends on: `GBX-1011`
- Goal: make retryable provider failures, stream loss, malformed tool calls, and
  degraded provider behavior explicit recovery states
- Deliverables:
  - provider recovery events and projection fields for retryable error,
    non-retryable error, lost stream, malformed tool call, rate limit,
    credential change, and degraded provider posture
  - retry/backoff evidence that does not hide failures from the transcript or
    event log
  - CLI/dashboard status cues for provider recovery posture
  - tests for simulated provider failures and recovery decisions
- Implementation notes:
  - do not persist secrets or raw provider request metadata
  - retries should be bounded by autonomy budget and provider policy
  - when provider recovery cannot safely continue, create checkpoint evidence
    and stop
- Tests and validation included in task:
  - provider config tests
  - model executor tests
  - turn engine failure tests
- Done when:
  - provider failure during long work produces visible, bounded recovery
    evidence instead of unexplained turn failure
- Completed:
  - Added `ProviderRecoveryRecorded` events, provider recovery enums, durable
    recovery records, SQLite migration/projection/query helpers, and rebuild
    coverage for retryable errors, non-retryable errors, lost streams,
    malformed tool calls, rate limits, credential changes, and degraded
    posture.
  - Recorded provider recovery evidence before failed-turn evidence in live
    turn execution, including bounded retry/backoff posture and redacted
    operator next actions without persisting secrets or raw provider metadata.
  - Surfaced latest provider recovery state in CLI session status, session
    summary/snapshot API responses, generated frontend API types, dashboard
    next-action/health/recovery cues, and provider/cockpit docs.

### GBX-1082: Add Model Switch And Fallback Recommendations For Long Work

- Status: `DONE`
- Depends on: `GBX-1081`, `GBX-1060`
- Goal: help operators decide whether to continue, pause, switch providers, or
  fall back to deterministic local behavior after provider degradation
- Deliverables:
  - recommendation model that separates capability fit, evidence freshness,
    current failure posture, budget impact, and unknowns
  - CLI and dashboard guidance for switch, retry, pause, or local fallback
  - docs explaining advisory status and deterministic release boundary
  - tests for fresh evidence, stale evidence, repeated provider failure,
    unsupported model, and missing credentials
- Implementation notes:
  - recommendations should not switch models automatically
  - deterministic local fallback should not pretend to complete provider-only
    tasks
  - provider advice remains operational guidance, not release authority
- Tests and validation included in task:
  - provider recommendation tests
  - CLI JSON tests
  - dashboard cue tests
- Done when:
  - long-running provider degradation has clear advisory next actions without
    hiding uncertainty
- Completed:
  - Extended provider recommendations with typed `recommended_action`,
    `failure_posture`, and `budget_impact` fields, while keeping advice
    advisory and never auto-applying provider or model switches.
  - Added optional `--session-id` recovery-history input for
    `glassbox provider recommend`, including JSON and human-readable output for
    retry, pause, switch-provider, local-fallback, credential, and evidence
    refresh decisions.
  - Added dashboard recovery cue guidance for bounded retries, degraded
    provider posture, provider switching, checkpoint inspection, and
    deterministic-only local fallback.
  - Updated provider docs to describe the advisory recommendation contract,
    persisted recovery evidence inputs, budget impact, and deterministic
    replay/eval release boundary.
  - Covered fresh evidence, stale evidence, repeated provider failure,
    retryable recovery, unsupported model, missing credentials, CLI JSON
    recovery guidance, and dashboard provider recovery cues.

---

## Phase 109: v10 Eval, Dogfooding, Gate, And Release Signoff

### GBX-1090: Add Deterministic Long-Run Replay And Eval Cases

- Status: `DONE`
- Depends on: `GBX-1033`, `GBX-1043`, `GBX-1073`
- Goal: prove the core v10 behavior with deterministic replay/eval evidence
- Deliverables:
  - eval cases for incomplete-turn recovery, checkpoint resume, compaction
    provenance, stale compaction exclusion, tool-attempt partial output,
    safe-to-retry classification, stale verification, and long-run cockpit
    summaries
  - profile updates that keep commit-time smoke small while adding meaningful
    release-candidate coverage
  - coverage and impact manifest updates
  - tests for eval selection, profile budgets, and release report status
- Implementation notes:
  - prefer small deterministic cases over broad brittle long-run simulations
  - provider-dependent recovery should remain advisory unless deterministically
    fixture-backed
  - compaction cases should assert provenance, not exact prose unless stable
- Tests and validation included in task:
  - `uv run glassbox eval run --profile release-candidate --cwd .`
  - `uv run glassbox eval audit --cwd .`
  - eval unit tests
- Done when:
  - v10 long-run primitives are represented in repository-owned deterministic
    release evidence
- Completed:
  - Added five compact release-candidate replay fixtures for
    incomplete-turn/checkpoint recovery, compaction provenance and stale
    exclusion, tool-attempt partial-output safe retry, stale verification
    review, and long-run cockpit progress/recovery summaries.
  - Extended the release-candidate profile budget from 8 to 13 selected cases
    while leaving commit-time and push-time smoke selection unchanged.
  - Added v10 long-run capability mappings to `evals/coverage.json` and
    `evals/impact.json`, including release-candidate recommendation routing
    for checkpoint/compaction, tool-attempt recovery, and cockpit/dashboard
    changes.
  - Updated eval documentation with the v10 fixture-backed release-candidate
    cases and the deterministic boundary for provider and daemon-dependent
    behavior.
  - Verified the updated profile with `glassbox eval run --profile
    release-candidate`, `glassbox eval audit`, and `glassbox eval report
    release-candidate`, plus focused eval metadata, coverage, recommendation,
    CLI, and release summary tests.

### GBX-1091: Add v10 Release Gate

- Status: `TODO`
- Depends on: `GBX-1090`, `GBX-1082`
- Goal: compose inherited v9 release evidence with v10 long-running-task
  evidence
- Deliverables:
  - `scripts/validate_v10_release_gate.py` or equivalent gate command
  - gate stages for Python format/lint/typecheck, Python tests, frontend
    lint/typecheck/tests/build, deterministic eval report, long-run replay
    profile, checkpoint/compaction smoke, tool-attempt recovery smoke, provider
    recovery policy check, package build, installed smoke, and retained summary
  - dry-run mode and explicit evidence directory support
  - `summary.json` and concise human-readable summary output
  - unit tests for stage composition, dry-run behavior, failure reporting, and
    evidence paths
- Implementation notes:
  - reuse v9 gate stages where practical
  - provider recovery remains advisory unless deterministically fixture-backed
  - every skipped stage must have an explicit reason
  - evidence should prove recoverability and compaction provenance, not merely
    raw test pass/fail
- Tests and validation included in task:
  - gate unit tests
  - dry-run v10 gate
  - focused real gate run before release-candidate publication
- Done when:
  - v10 readiness has one command that records deterministic, package,
    provider, long-run, and cockpit evidence clearly

### GBX-1092: Run Long-Running Dogfooding Passes

- Status: `TODO`
- Depends on: `GBX-1091`
- Goal: validate v10 against real longer local tasks and record product
  friction before release signoff
- Deliverables:
  - at least three focused dogfooding passes:
    - long repository inspection with compaction and checkpoint review
    - multi-step code edit with incremental verification and recovery
    - interrupted daemon/background continuation with retry or abandon evidence
  - retained local evidence or sanitized summaries for each pass
  - friction findings grouped by checkpoint, compaction, tool attempt,
    dashboard cockpit, provider recovery, verification, memory, and release
    evidence
  - candidate eval cases or tests for repeated failure patterns
- Implementation notes:
  - prefer real tasks with normal messiness over staged fixtures
  - record where the operator had to infer state manually
  - do not expand scope during dogfooding; file follow-up tasks instead
- Tests and validation included in task:
  - focused validation commands chosen from actual touched surfaces
- Done when:
  - v10 priorities are informed by real long-running operator use rather than
    only synthetic fixtures

### GBX-1093: Publish v10 Release-Candidate Guide

- Status: `TODO`
- Depends on: `GBX-1091`, `GBX-1092`
- Goal: publish a concise public guide for the supported v10 long-running-task
  operating model, validation path, evidence expectations, non-goals,
  residual risks, and release decision
- Deliverables:
  - `v10-release-candidate.md` or equivalent operator guide
  - root README update linking the v10 contract and release candidate
  - docs hub update linking v10 task, checkpoint, compaction, long-run cockpit,
    provider recovery, dogfooding, and release evidence docs
  - release-readiness checklist reflecting automated gate, manual evidence,
    provider advisory posture, package smoke, checkpoint/compaction evidence,
    tool-attempt recovery, incremental verification, dashboard cockpit,
    accessibility, and residual risks
  - decision section with candidate build, date, evidence directory, final
    pass/fail state, and accepted risks
- Implementation notes:
  - keep the release guide operator-readable
  - be explicit that Glassbox is local long-running agent work, not hosted
    orchestration
  - name remaining non-goals and known residual risks clearly
  - avoid overclaiming provider reliability, accessibility, or unattended
    operation beyond retained evidence
- Tests and validation included in task:
  - docs link review
  - release docs guardrail tests
  - final v10 release gate run
- Done when:
  - v10 has a publishable release-candidate narrative backed by retained
    automated, dogfooding, and manual evidence

## v10 Release-Candidate Readiness Checklist

Before treating a build as the v10 release candidate, complete this list:

- `uv run glassbox command tree` and workflow-oriented command discovery match
  the documented command surface.
- The v10 long-running-task contract explains supported workflows and non-goals.
- The durability audit has no untriaged process-local state that v10 claims to
  recover.
- Durable event vocabulary covers checkpoint, compaction, tool attempt,
  recovery, and long-run phase changes.
- Incomplete turns and interrupted tools have explicit recoverable,
  non-resumable, retryable, abandoned, or stale states.
- Checkpoints are persisted, projected, inspectable, exportable, and included
  in resume context with provenance.
- Context compactions are artifact-backed, source-linked, freshness-aware, and
  excluded from prompts when stale.
- Long command and test attempts retain partial output artifacts, retry posture,
  and recovery actions.
- Dashboard and terminal cockpit surfaces show heartbeat, active phase,
  checkpoint, compaction, verification, budget, provider, and recovery posture.
- Time-aware autonomy budgets and checkpoint approvals stop long work at
  explicit local limits.
- Incremental verification can identify last known good state, stale
  verification, and repair history.
- Long-run workspace memory remains review-gated and provenance-backed.
- Provider recovery evidence is visible, bounded, redacted, and advisory beside
  deterministic release contracts.
- Deterministic long-run eval cases pass and are represented in coverage and
  impact manifests.
- `uv run python scripts/validate_v10_release_gate.py` passes and writes
  `summary.json`.
- Manual and dogfooding evidence exists in the documented evidence directory.
- Package artifacts include static dashboard assets, generated API files, v10
  docs, eval profiles, release scripts, and installed smoke support.
- Named accessibility pairings are recorded before making stronger
  accessibility claims.
- Residual risks are named, mitigated, and accepted in the release decision.

## Deliberate v10 Non-Goals

Do not spend v10 effort on these unless a later task explicitly changes scope:

- hosted control plane
- cloud authority for workspace ownership
- remote multi-user orchestration
- simultaneous multi-writer mutation of one workspace
- distributed worker fleet
- cloud scheduler or calendar-integrated automation
- plugin marketplace or arbitrary third-party tool loading
- browser-native code editing as a replacement for local tools
- remote policy enforcement
- hidden provider-side memory
- uninspectable vector-store retrieval treated as source of truth
- automatic background mutation without explicit budget, policy, checkpoint,
  and stop reasons
- automatic model switching without operator approval
- automatic merging of branch-search candidates into parent history
- replacing deterministic replay/eval release authority with live-provider
  canaries
- claiming arbitrary provider stream resume when the provider cannot prove it
- removing the plain terminal fallback
- broad command removals without a compatibility and migration policy

Long-running local work, explicit compaction, resumable checkpoints, recoverable
tool attempts, and clearer local operator control are in scope. Hosted
orchestration, remote authority, and indefinite unattended mutation are not.
