# Glassbox v11 Tasks

For the docs hub and operator guides, start at [README.md](./README.md). This
file is the v11 task graph for evolving the completed v10 long-running-task
release candidate into the `0.10.0` confidence, adoption, and residual-risk
closure milestone.

## Purpose

This document defines Glassbox v11: the confidence-and-adoption evolution after
the v10 long-running-task reliability milestone in [tasks-v10.md](./tasks-v10.md).

It is written in the same execution style as [tasks-v1.md](./tasks-v1.md)
through [tasks-v10.md](./tasks-v10.md): explicit dependencies, small vertical
slices, concrete deliverables, and quality requirements attached directly to
the work.

The v2 through v10 work established the durable local runtime, event-sourced
SQLite store, daemon ownership model, packaged dashboard, full-screen terminal
client, cancellation, replay/eval release contracts, provider diagnostics,
task plans, autonomy budgets, background jobs, workspace memory, repository
intelligence, verify-repair loops, branch search, dashboard cockpit surfaces,
checkpointed long-running work, artifact-backed context compactions,
resumable tool attempts, time-aware continuation budgets, incremental
verification, provider recovery posture, and v10 refactor guardrails.

The v11 goal is not to add a new autonomy tier. The v11 goal is to make the
power added in v8 through v10 feel dependable, discoverable, and boringly
operable in daily local use.

The v11 work should optimize for eight outcomes:

- close accepted v10 residual risks with focused product fixes or stronger
  evidence
- make change-aware verification recommendations reliable enough for ordinary
  contributors to trust
- turn deterministic long-run cockpit coverage into live browser confidence
  through retained evidence
- mature provider recovery without making live providers release authority
- compress daily operator flows so inspection and recovery require less command
  memorization
- unify knowledge freshness across repository index, workspace memory,
  compactions, checkpoints, and verification posture
- make branch search more useful as decision support without automatic merging
- align the public v10 product track with package version `0.10.0`

The v11 thesis is:

- preserve local-first operation and workspace-owned state
- preserve canonical events as the source of truth
- preserve one local mutation owner per workspace
- preserve deterministic replay and eval as release authority
- prefer confidence, evidence, and operator flow polish over broad capability
  expansion
- promote only narrow provider or browser claims that have retained evidence
- make residual risks visible until they are fixed, tested, or explicitly
  carried forward
- keep the terminal as the primary chat surface and the dashboard as the paired
  cockpit and evidence surface
- avoid hosted orchestration, distributed workers, simultaneous multi-writer
  mutation, hidden provider memory, browser-native code editing as a local-tool
  replacement, and automatic branch merging in this milestone

## Current Baseline Before V11 Execution

Treat the following as the starting point for every task in this document:

- [v10-release-candidate.md](./v10-release-candidate.md) records a GO decision
  for the v10 release candidate.
- [v10-long-running-task-contract.md](./v10-long-running-task-contract.md)
  records the supported long-running-task model.
- [v10-dogfooding-summary.md](./v10-dogfooding-summary.md) records the v10
  real-use findings and candidate follow-ups.
- [refactor-v10.md](./refactor-v10.md) records the completed post-v10
  second-order refactor shape and guardrails.
- The package metadata still uses the v9 public-baseline version until a v11
  task explicitly bumps the package and docs to `0.10.0`.
- `glassbox session chat` remains the primary conversational surface.
- The dashboard is a packaged Next.js static export served by FastAPI.
- Runtime state is local to `.glassbox/` by default and backed by canonical
  SQLite events plus rebuildable projections.
- Replay and eval profiles live in `evals/` as repository-owned deterministic
  behavioral contracts.
- Provider diagnostics, canaries, and recommendations remain advisory.
- Long-running work is bounded local continuation, not indefinite unattended
  operation.
- The v10 gate validates inherited v9 evidence, deterministic long-run replay
  and eval profiles, package contents, installed smoke, cockpit smoke, and
  provider recovery policy output.

## v11 Confidence And Adoption Findings

Treat these findings as evidence that should steer the first implementation
slices:

- Full-session compaction over very large source ranges can still expose a raw
  source-reference cap validation error instead of a bounded-range next action.
- Historical or imported sessions can show no latest checkpoint; absence is
  visible, but the operator still has to infer whether it is expected.
- `glassbox eval recommend` does not yet confidently route release-gate scripts
  or release-candidate docs to the release checks.
- Long-run cockpit behavior is covered by deterministic replay and component
  tests, but v10 dogfooding did not exercise live dashboard monitoring.
- Screen-reader pairings remain unexecuted, so accessibility claims are still
  bounded to automated and prior manual evidence.
- Provider canary evidence remains partial for release-candidate and long-run
  work; provider advice is useful but still explicitly advisory.
- The command surface is powerful but broad. Daily inspection and recovery
  workflows still require operators to know which command family owns which
  next action.
- Repository index, workspace memory, compaction, checkpoint, verification, and
  provider freshness cues are all useful, but their combined knowledge posture
  is not yet a single easy operator mental model.
- Branch search can compare candidates, but the decision support around cost,
  risk, verification, and follow-up action can become much stronger without
  introducing automatic merge behavior.

## Agent Execution Rules

These rules apply to every task in this file.

1. Respect dependency order. Do not start a task until its dependencies are
   complete unless the task explicitly says it can proceed in parallel.
2. Preserve the event-sourced source-of-truth rule. New confidence, recovery,
   verification, provider, knowledge, and branch-search state must be recorded
   in canonical events, retained artifacts, typed API responses, or explicitly
   rebuildable derived state.
3. Preserve local-first operation. Do not introduce a hosted control plane,
   cloud authority for workspace ownership, remote worker fleet, or external
   service dependency for v11 readiness.
4. Preserve deterministic release blocking. Live-provider and live-browser
   evidence may strengthen confidence but must not replace deterministic
   replay/eval release authority unless a task explicitly defines a repeatable
   fixture-backed contract and failure policy.
5. Prefer residual-risk closure over feature expansion. If a v10 accepted risk
   is still open, either fix it, add focused evidence, or carry it forward
   explicitly.
6. Keep operator guidance concrete. If a state is stale, blocked, degraded, or
   ambiguous, terminal and dashboard surfaces should name the exact inspection
   command or safe next action before mutating recovery.
7. Keep daily workflows scriptable. Readiness, verification recommendations,
   compaction, checkpoint inspection, dashboard evidence, provider diagnostics,
   branch-search review, handoff, and release gates must work in clean shell
   and CI-like environments where practical.
8. Do not weaken autonomy boundaries. v11 may make recovery and continuation
   easier to understand, but it must not make background mutation less bounded,
   less inspectable, or less approval-aware.
9. Treat package version alignment as product behavior. The `0.10.0` bump must
   be reflected in metadata, installed smoke, release docs, and version policy.
10. Every implementation task automatically includes:
    - automated tests for new or changed behavior
    - `ruff` formatting and lint compliance for touched Python code
    - `ty` typecheck compliance for touched Python code
    - focused `pytest` coverage for touched runtime, CLI, web, replay, eval,
      daemon, store, policy, task, compaction, verification, provider,
      branch-search, and terminal behavior
    - frontend lint, typecheck, tests, and build when the task touches
      dashboard code, generated API types, packaged static assets, or route
      assumptions
    - documentation updates when operator-visible behavior, package metadata,
      release posture, provider posture, recovery behavior, accessibility
      claims, or public workflow claims change

## Completion Contract For Any Task

A task is complete only when all of the following are true:

- the implementation exists in the intended module boundary
- automated tests covering the changed behavior exist and pass
- lint, formatting, type checks, and focused tests pass for touched code
- frontend validation passes when dashboard, generated API types, or packaged
  static assets are touched
- deterministic replay/eval behavior remains stable or intentional drift is
  documented through the eval refresh workflow
- public docs are accurate against command help, API behavior, package version,
  and package contents
- new confidence claims are backed by retained deterministic or manual evidence
- new recovery guidance starts with safe inspection before mutation
- no meaningful long-running or release-critical state exists only in memory
  once a task claims durability
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

New v11 implementation areas should prefer focused modules rather than widening
facades. Expected new or expanded surfaces may include:

```text
src/glassbox/runtime/knowledge_posture.py
src/glassbox/runtime/eval_recommendation_release.py
src/glassbox/runtime/provider_failure_fixtures.py
src/glassbox/runtime/branch_decision_support.py
src/glassbox/web/routes/handoff.py
frontend/components/console/knowledge-posture/
frontend/components/console/branch-decision/
scripts/validate_v11_release_gate.py
```

The exact file names may change during implementation, but ownership
boundaries should remain explicit.

## Recommended Validation Commands

Use the narrowest viable validation after each task, but the baseline
validation pattern for completed v11 work should include:

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

Once `GBX-1191` exists, use the v11 gate as the canonical full validation
command:

```bash
uv run python scripts/validate_v11_release_gate.py
```

During incremental work, use narrower commands when possible:

```bash
uv run pytest tests/unit/test_specific_module.py
uv run pytest tests/integration/test_specific_flow.py
uv run ruff check src/glassbox/path.py tests/path_test.py
uv run ty check src/glassbox/path.py
pnpm --dir frontend test -- workspace-overview.test.tsx
pnpm --dir frontend typecheck
```

## Milestone Map

The intended v11 milestone order is:

1. v11 confidence contract and `0.10.0` version policy
2. v10 residual-risk closure
3. verification recommendation intelligence
4. live cockpit and accessibility evidence
5. provider recovery maturity
6. operator flow compression
7. knowledge freshness and provenance
8. branch-search decision support
9. local team handoff polish
10. v11 release gate, dogfooding, and release-candidate guide

Each phase below corresponds to one concrete milestone.

## Task Graph

---

## Phase 110: V11 Contract And Version Alignment

### GBX-1100: Define The v11 Confidence And Adoption Contract

- Status: `DONE`
- Depends on: none
- Goal: publish the v11 product contract before changing behavior
- Deliverables:
  - `docs/v11-confidence-adoption-contract.md`
  - explicit mapping from v10 residual risks into v11 tasks, accepted
    non-goals, or carried-forward risks
  - supported workflow set for confidence, verification recommendations,
    live cockpit evidence, provider maturity, knowledge posture, branch-search
    decision support, and local handoff
  - release-evidence expectations that distinguish deterministic blocking
    evidence from live browser, live provider, and manual accessibility
    evidence
- Implementation notes:
  - keep the contract operator-readable
  - do not turn v11 into hosted orchestration or indefinite autonomy
  - name `0.10.0` as the package version target for this milestone
- Tests and validation included in task:
  - docs link review
  - release-doc guardrail updates if current tests require all active milestone
    docs to be linked
- Done when:
  - v11 has one concise product contract that later tasks can reference instead
    of restating scope

### GBX-1101: Audit v10 Residual Risks Against Current Source And Evidence

- Status: `DONE`
- Depends on: `GBX-1100`
- Goal: ground v11 implementation in the actual remaining gaps after v10 and
  the post-v10 refactor
- Deliverables:
  - `docs/v11-residual-risk-audit.md`
  - source-linked audit entries for compaction cap handling, historical
    checkpoint absence, eval recommendation gaps, live dashboard evidence,
    accessibility evidence, provider matrix partialness, bounded-autonomy
    non-goals, and broad command-surface friction
  - classification of each gap as fixed in v11, evidence-only in v11, accepted
    non-goal, or carried-forward risk
  - test inventory for where each gap is currently covered and where coverage
    is missing
- Implementation notes:
  - keep projections and dashboard summaries non-authoritative in the audit
  - include both backend and frontend evidence paths
- Tests and validation included in task:
  - docs review against current implementation
  - no product-code change required unless the audit exposes stale docs
- Done when:
  - every v10 known residual risk has an explicit v11 disposition

### GBX-1102: Align Package And Release Policy With `0.10.0`

- Status: `DONE`
- Depends on: `GBX-1100`
- Goal: make package metadata, public docs, installed smoke, and release naming
  agree that this milestone becomes `0.10.0`
- Deliverables:
  - update `pyproject.toml` package version to `0.10.0`
  - update `src/glassbox/__init__.py` version to `0.10.0`
  - update [version-release-policy.md](./version-release-policy.md) for the
    v10 package line and v11 milestone naming
  - update README and docs hub references so the supported public baseline and
    active milestone are not contradictory
  - installed-wheel smoke assertion for `glassbox --version`
- Implementation notes:
  - historical release-candidate docs should keep retained evidence paths and
    historical version claims when they were true
  - avoid renaming existing local evidence directories only for cosmetic
    consistency
- Tests and validation included in task:
  - packaging metadata tests
  - installed-wheel smoke update
  - package contents validation
- Done when:
  - a built and installed package reports `glassbox 0.10.0` and the docs explain
    why

---

## Phase 111: Residual-Risk Closure

### GBX-1110: Add Friendly Compaction Range Guardrails

- Status: `DONE`
- Depends on: `GBX-1101`
- Goal: replace raw source-reference cap validation failures with bounded-range
  guidance before compaction artifact validation is reached
- Deliverables:
  - compaction service or CLI validation for source ranges that would exceed
    the artifact source-reference cap
  - operator-facing error that names the selected event count, supported cap,
    and suggested bounded ranges
  - CLI and API behavior that remains scriptable and JSON-readable where
    existing compaction commands already support JSON
  - docs update in [context-compactions.md](./context-compactions.md)
- Implementation notes:
  - preserve the artifact schema cap unless a task explicitly changes the
    artifact contract
  - keep compaction as evidence, not cleanup
  - prefer deterministic source-range math over sampling source references
- Tests and validation included in task:
  - unit coverage for over-cap source ranges
  - CLI coverage for friendly guidance
  - existing compaction provenance eval remains stable
- Done when:
  - an operator cannot trigger the known v10 raw schema validation failure
    through normal compaction commands

### GBX-1111: Clarify Historical Checkpoint Absence

- Status: `DONE`
- Depends on: `GBX-1101`
- Goal: make missing checkpoints on historical or imported sessions
  self-explanatory rather than requiring operator inference
- Deliverables:
  - typed checkpoint-absence reason in session status, snapshot, or long-run
    status responses
  - CLI status copy that distinguishes pre-checkpoint-era history, imported
    inspection-only sessions, active long-running sessions missing expected
    checkpoint evidence, and projection degradation
  - dashboard cue that labels expected historical absence differently from an
    active recovery gap
  - docs update in v10/v11 recovery or checkpoint docs
- Implementation notes:
  - do not synthesize fake checkpoints for historical sessions
  - absence explanation must be derived from events, session metadata, import
    state, or projection health
- Tests and validation included in task:
  - unit tests for absence-reason derivation
  - CLI status tests
  - frontend reducer/component coverage if dashboard copy changes
- Done when:
  - checkpoint absence is an explicit state with a clear next action or no-action
    explanation

### GBX-1112: Close The v10 Release-Path Recommendation Gap

- Status: `DONE`
- Depends on: `GBX-1101`
- Goal: ensure release-gate scripts and release-candidate docs receive confident
  eval or gate recommendations
- Deliverables:
  - impact rules for `scripts/validate_v*_release_gate.py`,
    `docs/v*-release-gate.md`, `docs/v*-release-candidate.md`,
    release-packaging docs, and package-content validation scripts
  - recommendation output that distinguishes eval profiles from full release
    gate scripts
  - tests that prove changed release docs/scripts point operators at the
    correct v10 or v11 gate
  - docs update in [replay-evals.md](./replay-evals.md)
- Implementation notes:
  - avoid recommending the full release gate for ordinary low-risk code changes
  - make confidence and reason text clear enough for a reviewer to trust
- Tests and validation included in task:
  - eval recommendation unit tests
  - focused CLI recommendation tests
  - no baseline refresh unless recommendation output is part of a fixture
- Done when:
  - the dogfooding finding about release-gate recommendation gaps is fixed

---

## Phase 112: Verification Intelligence

### GBX-1120: Add Verification Recommendation Explainability

- Status: `DONE`
- Depends on: `GBX-1112`
- Goal: make `glassbox eval recommend` easier to trust and act on
- Deliverables:
  - reason grouping by direct path, owner-derived rule, capability-derived
    rule, stage-derived profile, and release-gate recommendation
  - concise terminal output that names the cheapest recommended next command
    before broader release commands
  - JSON output fields stable enough for future dashboard or release-gate use
  - warnings when no confident match exists and suggested fallback commands are
    manual policy rather than inferred evidence
- Implementation notes:
  - preserve existing recommendation semantics unless intentionally improved
  - keep noisy advisory suites distinct from blocking release profiles
- Tests and validation included in task:
  - recommendation model tests
  - CLI formatter tests
  - docs examples updated
- Done when:
  - operators can see why each recommended eval or gate was selected

### GBX-1121: Introduce Verification Recipes For Common Change Families

- Status: `DONE`
- Depends on: `GBX-1120`
- Goal: reduce command memorization for recurring contributor workflows
- Deliverables:
  - repository-owned verification recipe model for common change families such
    as docs-only, release docs, release gate scripts, frontend dashboard,
    runtime events, store schema, provider posture, and packaging
  - CLI output that can show recipe commands without executing them
  - optional workspace-profile default recipe behavior if it fits existing
    profile boundaries
  - docs update for contributor verification workflows
- Implementation notes:
  - recipes should be declarative metadata, not hidden hard-coded command
    branches where a manifest is more maintainable
  - do not make recipes replace focused tests chosen by the implementer
- Tests and validation included in task:
  - recipe parsing and validation tests
  - recommendation integration tests
  - docs examples
- Done when:
  - common Glassbox change families have discoverable, evidence-backed
    verification guidance

### GBX-1122: Promote Stable v11 Recommendation Cases Into Release Evidence

- Status: `DONE`
- Depends on: `GBX-1121`
- Goal: make verification recommendation behavior itself part of the release
  contract
- Deliverables:
  - deterministic eval or focused fixture cases for release-path recommendation,
    frontend-path recommendation, provider-path recommendation, and
    no-confident-match fallback
  - profile or release-gate integration for the stable subset
  - coverage manifest updates explaining why the recommendation behavior
    matters
- Implementation notes:
  - keep recommendation fixtures compact and deterministic
  - avoid turning every path rule into a replay case
- Tests and validation included in task:
  - eval run for new fixtures
  - eval audit update
  - release-candidate profile update only for stable blocking cases
- Done when:
  - changed recommendation behavior can fail release validation when it matters

---

## Phase 113: Live Cockpit And Accessibility Evidence

### GBX-1130: Define Live Cockpit Evidence Protocol

- Status: `DONE`
- Depends on: `GBX-1101`
- Goal: turn live dashboard monitoring from an accepted gap into a repeatable
  evidence workflow
- Deliverables:
  - `docs/live-cockpit-evidence-v11.md`
  - scenario matrix for active turn, pending approval, pending question, stale
    tool attempt, stale verification, compaction freshness, provider warning,
    daemon interruption, stream reconnect, and historical snapshot
  - evidence directory convention under `.glassbox/releases/`
  - manual and automated evidence split with explicit non-claims
- Implementation notes:
  - do not require a hosted browser service
  - keep deterministic replay/component coverage as release authority where
    browser evidence is environmental
- Tests and validation included in task:
  - docs review
  - update release docs guardrails if needed
- Done when:
  - live cockpit validation has a repeatable protocol before screenshots or
    browser runs are collected

### GBX-1131: Add Browser Long-Session And Reconnect Evidence

- Status: `DONE`
- Depends on: `GBX-1130`
- Goal: collect retained browser evidence for the long-run cockpit states that
  v10 covered primarily through replay and components
- Deliverables:
  - Playwright scenarios or manual scripts for long-session inspection,
    reconnect, stream degradation, queue navigation, and selected-session
    recovery cues
  - retained screenshots or structured browser logs under the v11 evidence
    directory
  - docs summary of pass/fail state and environmental blockers
  - fixes for blocking UI overlap, stale live-state, or route issues discovered
    during the run
- Implementation notes:
  - if local browser infrastructure blocks a run, record the blocker honestly
    and keep the claim bounded
  - avoid broad visual redesign unless a task explicitly adds it
- Tests and validation included in task:
  - focused Playwright or component tests
  - frontend lint/typecheck/test/build when dashboard code changes
- Done when:
  - the v11 release candidate has retained live cockpit evidence or a clearly
    accepted environmental blocker

### GBX-1132: Execute Named Accessibility Pairings

- Status: `DONE`
- Depends on: `GBX-1130`
- Goal: replace broad accessibility non-claims with named, bounded evidence
- Deliverables:
  - terminal keyboard and plain-mode pairing
  - dashboard keyboard pairing
  - at least one screen-reader pairing if the local environment permits it
  - accessibility review doc that names tested tools, versions, workflows,
    pass/fail findings, non-claims, and follow-ups
  - fixes for blocking focus, label, keyboard, or wrapping defects discovered
    during the pairings
- Implementation notes:
  - do not imply broad certification from narrow pairings
  - keep status indicators text-accessible and not color-only
- Tests and validation included in task:
  - targeted frontend component tests for fixed accessibility defects
  - terminal/TUI focused tests if terminal behavior changes
- Done when:
  - v11 accessibility claims are backed by named evidence rather than inherited
    automated coverage alone

### GBX-1133: Harden Dashboard Performance For Large Local Sessions

- Status: `DONE`
- Depends on: `GBX-1131`
- Goal: keep the cockpit usable when sessions, transcript pages, event logs,
  tool attempts, and recovery cues grow
- Deliverables:
  - measurement pass for aggregate load, selected-session load, SSE reducer
    cost, long timeline rendering, and detail-page pagination
  - focused optimizations only where measurement shows user-visible risk
  - performance budget docs or tests if a stable threshold is useful
- Implementation notes:
  - prefer backend pagination, lazy detail loading, memoized derivation, and
    stable component boundaries over hiding evidence
  - do not make projections authoritative to improve frontend speed
- Tests and validation included in task:
  - frontend tests for pagination or reducer changes
  - backend session query tests if API shape changes
  - focused performance budget test where practical
- Done when:
  - large-session cockpit behavior has retained evidence and no known blocking
    UI performance issue

---

## Phase 114: Provider Recovery Maturity

### GBX-1140: Expand Provider Failure Fixture Coverage

- Status: `DONE`
- Depends on: `GBX-1101`
- Goal: make repeated provider failure modes reviewable without depending on
  live-provider timing
- Deliverables:
  - deterministic fixtures for retryable provider error, non-retryable provider
    error, lost stream, malformed tool call, stale canary evidence, and model
    fallback recommendation
  - provider recovery history records where relevant
  - tests that keep provider recommendation behavior advisory but explainable
- Implementation notes:
  - do not promote live-provider canaries into blocking release authority
  - model-switch guidance must remain visible as recommendation, not hidden
    runtime mutation
- Tests and validation included in task:
  - provider recovery unit tests
  - eval or fixture-based deterministic tests for promoted behavior
- Done when:
  - common provider recovery advice can be validated without live credentials

### GBX-1141: Refresh Provider Capability Matrix For Long Work

- Status: `DONE`
- Depends on: `GBX-1140`
- Goal: make provider recommendations more precise for long-running local tasks
- Deliverables:
  - capability matrix rows for long-running task needs such as streaming,
    tool-call stability, retry posture, context size, structured output,
    latency, and cost/risk guidance
  - provider recommendation copy that distinguishes missing evidence,
    stale evidence, partial evidence, and known failure posture
  - docs update in [providers.md](./providers.md)
- Implementation notes:
  - keep exact model availability and live provider behavior advisory and
    freshness-labeled
  - avoid claiming provider support beyond retained evidence
- Tests and validation included in task:
  - capability matrix tests
  - provider recommendation CLI tests
  - docs examples
- Done when:
  - provider recommendations are more useful for long work while staying
    explicitly advisory

### GBX-1142: Add Optional v11 Provider Evidence Collection

- Status: `DONE`
- Depends on: `GBX-1141`
- Goal: provide a clean path for operators who want live provider confidence
  beside deterministic release evidence
- Deliverables:
  - optional provider evidence stage in the v11 release gate
  - retained evidence summary for configured and skipped provider canaries
  - freshness and missing-scenario reporting aligned with provider
    recommendations
- Implementation notes:
  - provider evidence must remain opt-in and advisory
  - skip reasons must be structured and reviewer-readable
- Tests and validation included in task:
  - dry-run gate tests
  - provider skip/planning tests
  - no live credentials required for blocking CI
- Done when:
  - v11 can retain live provider confidence without making it a blocker

---

## Phase 115: Operator Flow Compression

### GBX-1150: Improve Command Guide Around Recovery And Verification

- Status: `DONE`
- Depends on: `GBX-1112`
- Goal: make the broad command surface easier to use during ordinary
  inspection, recovery, and release validation
- Deliverables:
  - command guide sections for long-run recovery, compaction, tool attempts,
    checkpoint inspection, verification recommendations, provider posture,
    knowledge freshness, and branch-search review
  - concise next-action phrasing that matches actual CLI commands
  - JSON guide shape update if needed for downstream surfaces
- Implementation notes:
  - keep the exhaustive command tree structural and the guide workflow-oriented
  - do not hide advanced commands; de-emphasize them in daily paths
- Tests and validation included in task:
  - command guide snapshot or formatter tests
  - docs update
- Done when:
  - a new operator can find the right recovery or verification command from the
    guide without reading release docs

### GBX-1151: Add Readiness Remediation Recipes

- Status: `DONE`
- Depends on: `GBX-1150`
- Goal: make first-run and stale-workspace readiness output more actionable
- Deliverables:
  - readiness findings that point to concrete remediation commands for provider
    setup, static dashboard assets, repository index freshness, writable
    `.glassbox` state, eval profile availability, and package/build posture
  - docs alignment with [getting-started.md](./getting-started.md) and
    [operator-quickstart.md](./operator-quickstart.md)
  - tests for common readiness failure combinations
- Implementation notes:
  - avoid running mutating remediation automatically
  - keep provider secrets redacted
- Tests and validation included in task:
  - readiness unit tests
  - CLI output tests
- Done when:
  - readiness output reliably answers "what do I do next?"

### GBX-1152: Add Safe Workflow Summaries For Status Commands

- Status: `DONE`
- Depends on: `GBX-1151`
- Goal: let status commands summarize related safe inspection steps without
  requiring operators to remember every command family
- Deliverables:
  - session status summary for relevant checkpoint, compaction, tool-attempt,
    verification, provider, dashboard, and projection commands
  - task show summary for continuation, pause-window, verification, budget, and
    recovery commands
  - observability status summary for projection, artifact, provider, daemon,
    index, and backup commands
- Implementation notes:
  - keep mutating commands clearly marked and behind explicit operator intent
  - preserve machine-readable JSON shape or add fields carefully with tests
- Tests and validation included in task:
  - CLI formatter tests
  - integration tests for JSON compatibility if changed
- Done when:
  - status surfaces become practical command launch pads for safe inspection

---

## Phase 116: Knowledge Freshness And Provenance

### GBX-1160: Define Workspace Knowledge Posture

- Status: `DONE`
- Depends on: `GBX-1101`
- Goal: give operators one coherent mental model for freshness across memory,
  repository index, compactions, checkpoints, verification, and provider
  evidence
- Deliverables:
  - runtime model or query helper that summarizes knowledge posture from
    existing local data sources
  - status categories for fresh, stale, missing, invalidated, degraded,
    advisory, and historical-only state
  - docs contract explaining which data source remains authoritative for each
    cue
- Implementation notes:
  - do not create a new hidden knowledge store
  - derive posture from canonical events, rebuildable projections, artifacts,
    and existing provider/index/memory state
- Tests and validation included in task:
  - unit tests for posture derivation
  - docs review
- Done when:
  - knowledge freshness is one inspectable summary instead of several unrelated
    maintenance warnings

### GBX-1161: Surface Knowledge Posture In CLI And Dashboard

- Status: `DONE`
- Depends on: `GBX-1160`
- Goal: make the unified knowledge posture visible where operators decide
  whether to continue work
- Deliverables:
  - CLI observability or session status fields for knowledge posture
  - dashboard overview cue that ranks knowledge freshness without outranking
    live blockers
  - drill-down links or commands for memory, repository index, compaction,
    checkpoint, verification, and provider evidence
- Implementation notes:
  - preserve long-run cockpit priority rules
  - provider warnings remain advisory
- Tests and validation included in task:
  - CLI output tests
  - API model tests if response shape changes
  - frontend component/store tests
- Done when:
  - operators can see whether local knowledge is trustworthy before relying on
    it for continuation
- Completed:
  - surfaced `knowledge_posture` in `observability status --json` and the human
    observability output
  - added the aggregate API field, regenerated OpenAPI/frontend types, and
    hydrated dashboard state from the new payload
  - added a workspace overview rail cue that shows knowledge freshness behind
    live blockers and recovery state
  - documented CLI, JSON, and dashboard surfaces in the knowledge posture guide

### GBX-1162: Add Provenance Drill-Down For Knowledge Cues

- Status: `DONE`
- Depends on: `GBX-1161`
- Goal: make knowledge posture auditable rather than decorative
- Deliverables:
  - provenance detail that names source event ranges, artifact IDs, repository
    index timestamps, memory IDs, verification IDs, and provider evidence
    freshness when available
  - dashboard or CLI drill-down surface for the most relevant cue
  - docs examples for investigating stale or conflicting knowledge
- Implementation notes:
  - do not duplicate raw artifacts in API payloads when artifact references are
    enough
  - keep path and secret redaction consistent with existing export/import and
    compaction behavior
- Tests and validation included in task:
  - provenance formatter tests
  - frontend detail tests if dashboard changes
- Done when:
  - a stale or advisory knowledge cue can be traced back to local evidence
- Completed:
  - added bounded provenance references to each knowledge cue for memory,
    repository index, checkpoint, compaction, verification, provider evidence,
    and active sessions without checkpoints
  - surfaced the top provenance reference in `observability status` text output
    while preserving full JSON/API drill-down data
  - regenerated OpenAPI/frontend types and documented stale knowledge
    investigation examples

---

## Phase 117: Branch-Search Decision Support

### GBX-1170: Define Branch Decision Support Model

- Status: `DONE`
- Depends on: `GBX-1100`
- Goal: make branch-search comparison more useful without changing parent
  mutation semantics
- Deliverables:
  - branch decision support model for candidate objective, evidence, changed
    files, verification posture, cost estimate, risk posture, accepted risks,
    and recommended follow-up action
  - docs update in [branch-search.md](./branch-search.md)
  - explicit non-goal that branch-search still does not automatically merge or
    mutate parent history
- Implementation notes:
  - preserve candidate selection, rejection, and needs-review semantics
  - derive support from existing branch-search events, task evidence,
    verification records, and artifacts where possible
- Tests and validation included in task:
  - unit tests for model derivation
  - branch-search docs review
- Done when:
  - branch-search comparison has a typed decision-support target before UI or
    CLI changes
- Completed:
  - added a typed branch decision-support model derived from existing
    branch-search projections
  - captured candidate objective, retained evidence, changed-file unknowns,
    verification posture, cost estimate, risk posture, accepted risks, and
    follow-up action without adding parent-history mutation
  - documented branch-search decision support and the explicit non-goal that
    selection does not automatically merge candidate work

### GBX-1171: Surface Candidate Evidence Comparison

- Status: `DONE`
- Depends on: `GBX-1170`
- Goal: help operators compare candidate approaches by evidence instead of
  reading raw branches one at a time
- Deliverables:
  - CLI `branch-search show` or related output with decision-support fields
  - API and dashboard rendering for candidate verification, risk, cost, and
    follow-up posture
  - tests for selected, rejected, and needs-review candidates
- Implementation notes:
  - avoid treating unverified candidates as equivalent to successful work
  - keep raw candidate details reachable
- Tests and validation included in task:
  - branch-search unit/integration tests
  - frontend tests if dashboard changes
  - existing branch-search replay case remains stable or is intentionally
    refreshed
- Done when:
  - candidate comparison answers why one branch is safer or more promising than
    another
- Completed:
  - surfaced branch decision support in `branch-search show` JSON and human
    output while preserving raw candidate details
  - added API `decision_support` payloads for branch-search detail responses
    and regenerated frontend OpenAPI/types
  - updated the dashboard branch-search console to render candidate
    verification posture, risk, cost, evidence, accepted risks, and follow-up
    action for selected, rejected, and needs-review candidates

### GBX-1172: Add Branch-Search Verification Recommendations

- Status: `DONE`
- Depends on: `GBX-1171`, `GBX-1121`
- Goal: connect branch candidates to the verification recommendations that make
  selection trustworthy
- Deliverables:
  - candidate-level recommended evals or verification commands based on touched
    files and task evidence
  - branch-search docs showing selection after verification
  - release or advisory fixture coverage for the stable behavior
- Implementation notes:
  - do not run verification automatically as part of selection unless a future
    task explicitly defines that workflow
  - recommendations must remain explainable and bounded
- Tests and validation included in task:
  - branch-search recommendation tests
  - eval recommendation integration tests
- Done when:
  - branch-search selection is paired with concrete verification guidance
- Completed:
  - added candidate-level verification recommendation models to branch
    decision support
  - wired changed-file recommendations through the existing eval/verification
    recipe engine when candidate changed-file evidence is available
  - preserved explicit missing-evidence guidance when branch-search projections
    do not yet retain candidate diff inventories
  - surfaced recommendation commands and rationale through CLI, API, generated
    frontend types, and dashboard candidate evidence cards

---

## Phase 118: Local Team Handoff Polish

### GBX-1180: Improve Session Handoff Summaries

- Status: `DONE`
- Depends on: `GBX-1162`
- Goal: make exported or shared local session state easier for another operator
  to inspect safely
- Deliverables:
  - handoff summary that includes latest objective, checkpoint posture,
    compaction posture, verification state, accepted risks, pending actions,
    branch lineage, knowledge posture, and suggested safe inspection commands
  - export package metadata update if needed
  - docs update in [team-workflows.md](./team-workflows.md)
- Implementation notes:
  - preserve local-first custody guidance and one mutation owner per workspace
  - do not introduce remote authority or access control
- Tests and validation included in task:
  - session export/import tests
  - redaction tests for handoff content
- Done when:
  - a reviewer can inspect a handoff package without reconstructing the story
    manually from raw events
- Completed:
  - added a redacted `handoff.summary` block to portable session exports with
    latest objective, checkpoint posture, compaction posture, verification
    state, accepted risks, pending actions, branch lineage, knowledge posture,
    and safe inspection commands
  - preserved import compatibility while recording the summary objective and
    knowledge posture in imported inspection notes when present
  - covered export, import, and redaction behavior in focused session handoff
    integration tests and updated the team handoff guide

### GBX-1181: Add Workspace Profile Templates For Common Team Defaults

- Status: `DONE`
- Depends on: `GBX-1151`
- Goal: make repository-owned defaults easier to set up without encoding
  secrets or owner state
- Deliverables:
  - documented profile templates for manual, test-driven, release-candidate,
    offline deterministic, and conservative provider-backed workflows
  - validation improvements for confusing profile errors if needed
  - readiness output that points to profile docs when defaults are missing or
    surprising
- Implementation notes:
  - profiles must not contain API keys, local database paths, or runtime owner
    state
  - explicit CLI flags continue to override profile defaults
- Tests and validation included in task:
  - profile validation tests
  - readiness tests if output changes
  - docs examples
- Done when:
  - teams can adopt shared local defaults without weakening local operator
    control
- Completed:
  - documented named profile templates for manual, test-driven,
    release-candidate, offline deterministic, and conservative provider-backed
    workflows without secrets or owner state
  - added a readiness workspace-profile defaults check that points operators to
    the profile templates when no shared defaults are present, warns for partial
    profiles, and fails visibly for invalid profiles
  - updated getting started, operator quickstart, and team workflow docs so
    profile defaults remain reviewable conventions and explicit CLI flags still
    win for one-off runs

### GBX-1182: Add Reviewer-Oriented Evidence Bundle Guidance

- Status: `DONE`
- Depends on: `GBX-1180`
- Goal: make local evidence easy to hand to a reviewer without committing
  `.glassbox` state
- Deliverables:
  - docs and optional command output explaining which summaries, eval reports,
    release summaries, replay bundles, and handoff exports are reviewer-safe
  - redaction and retention guidance aligned with existing artifacts and
    release evidence docs
  - examples for release-candidate review and ordinary code-review handoff
- Implementation notes:
  - avoid creating a cloud sharing model
  - keep local evidence paths explicit
- Tests and validation included in task:
  - docs link review
  - package contents validation if new docs must ship
- Done when:
  - v11 has a clear local reviewer evidence story
- Completed:
  - added [reviewer-evidence-bundles.md](./reviewer-evidence-bundles.md) with
    reviewer-safe surfaces for handoff exports, eval reports, eval audits,
    replay bundles, release summaries, live cockpit summaries, and
    accessibility/manual evidence
  - documented redaction and retention rules that keep raw `.glassbox` state,
    provider output, screenshots, logs, and ad hoc bundles local unless
    explicitly sanitized
  - linked the reviewer evidence story from the docs hub, team handoff guide,
    and replay/eval guide with release-candidate and ordinary code-review
    examples

---

## Phase 119: V11 Release Evidence And Candidate Guide

### GBX-1190: Add Deterministic v11 Replay And Eval Cases

- Status: `DONE`
- Depends on: `GBX-1122`, `GBX-1162`, `GBX-1172`
- Goal: protect the stable v11 confidence contracts with deterministic release
  evidence
- Deliverables:
  - compact deterministic cases or fixtures for release-path recommendation,
    compaction cap guidance, checkpoint absence explanation, knowledge posture,
    and branch-search decision support
  - `evals/coverage.json` updates for promoted capabilities
  - `evals/profiles.json` release-candidate budget update if case count changes
  - docs update in [replay-evals.md](./replay-evals.md)
- Implementation notes:
  - keep live dashboard, screen-reader, and live-provider evidence separate
    unless a repeatable deterministic fixture exists
  - avoid bloating commit-smoke profiles
- Tests and validation included in task:
  - eval run for new cases
  - eval audit
  - focused unit/integration tests for new fixtures
- Done when:
  - v11 confidence behavior has deterministic evidence where it can be made
    deterministic
- Completed:
  - promoted compact fixture-backed release-candidate replay cases for
    release-path recommendation, compaction cap guidance, checkpoint absence
    explanation, knowledge posture, and branch-search decision support
  - mapped the promoted v11 capabilities in `evals/coverage.json` and raised
    the release-candidate profile budget to match the expanded deterministic
    case set
  - documented the v11 confidence fixtures in the replay/eval guides while
    keeping live browser, screen-reader, and provider evidence separate

### GBX-1191: Add v11 Release Gate

- Status: `DONE`
- Depends on: `GBX-1102`, `GBX-1142`, `GBX-1190`
- Goal: provide one command that records v11 blocking and advisory evidence
  clearly
- Deliverables:
  - `scripts/validate_v11_release_gate.py`
  - inherited v10 gate or equivalent v10 evidence stages
  - v11 deterministic recommendation, compaction, checkpoint, knowledge, and
    branch-search evidence stages
  - package version and installed-wheel smoke for `0.10.0`
  - optional advisory provider canary stage
  - retained `summary.json` with blocking and advisory sections
  - `docs/v11-release-gate.md`
- Implementation notes:
  - keep provider and live-browser evidence advisory unless explicitly promoted
  - gate output should end with a concise reviewer summary
- Tests and validation included in task:
  - gate unit tests
  - dry-run gate
  - focused real gate run before release-candidate publication
- Done when:
  - v11 readiness has one command that records deterministic, package,
    provider, long-run, cockpit, recommendation, and knowledge evidence clearly
- Completed:
  - expanded `scripts/validate_v11_release_gate.py` from the provider-evidence
    scaffold into an explicit v11 gate with package-version metadata,
    deterministic eval report, expanded release-candidate profile,
    recommendation/recovery guidance smoke, knowledge/branch-search smoke, and
    release-candidate coverage audit stages
  - retained both `blocking` and `advisory` sections in `summary.json`, with
    provider canaries remaining opt-in and non-authoritative
  - documented the automated stages, evidence summary, pass/fail policy, and
    provider advisory posture in [v11-release-gate.md](./v11-release-gate.md)

### GBX-1192: Run v11 Dogfooding Passes

- Status: `TODO`
- Depends on: `GBX-1191`
- Goal: validate v11 against real local operator use and record product
  friction before release signoff
- Deliverables:
  - at least four focused dogfooding passes:
    - release-doc or release-gate edit using improved eval recommendations
    - long historical session compaction with over-range guidance and bounded
      retry
    - live dashboard monitoring during active or recovering long work
    - branch-search comparison with verification recommendations
  - optional provider recovery dogfooding when credentials and time permit
  - retained local evidence or sanitized summaries for each pass
  - friction findings grouped by residual-risk closure, recommendations,
    cockpit, provider, operator flow, knowledge posture, branch search,
    handoff, and release evidence
  - candidate tests or eval cases for repeated failure patterns
- Implementation notes:
  - prefer real tasks with normal messiness over staged fixtures
  - record where the operator still had to infer state manually
  - do not expand scope during dogfooding; file follow-up tasks instead
- Tests and validation included in task:
  - focused validation commands chosen from actual touched surfaces
- Done when:
  - v11 priorities are informed by real operator confidence and adoption use

### GBX-1193: Publish v11 Release-Candidate Guide

- Status: `TODO`
- Depends on: `GBX-1191`, `GBX-1192`
- Goal: publish a concise public guide for the supported v11 `0.10.0`
  operating model, validation path, evidence expectations, non-goals,
  residual risks, and release decision
- Deliverables:
  - `docs/v11-release-candidate.md`
  - README update linking the v11 contract and release candidate
  - docs hub update linking v11 residual-risk, recommendation, live cockpit,
    provider, knowledge, branch-search, handoff, and release evidence docs
  - release-readiness checklist reflecting automated gate, package version,
    installed smoke, deterministic evals, live dashboard evidence,
    accessibility pairings, provider advisory posture, dogfooding, and
    residual risks
  - decision section with candidate build, date, evidence directory, final
    pass/fail state, and accepted risks
- Implementation notes:
  - keep the release guide operator-readable
  - be explicit that Glassbox remains local-first agent work, not hosted
    orchestration
  - name remaining non-goals and known residual risks clearly
  - avoid overclaiming provider reliability, accessibility, browser evidence,
    or unattended operation beyond retained evidence
- Tests and validation included in task:
  - docs link review
  - release docs guardrail tests
  - final v11 release gate run
- Done when:
  - v11 has a publishable release-candidate narrative backed by retained
    automated, dogfooding, manual, and advisory evidence
