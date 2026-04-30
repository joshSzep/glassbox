# Glassbox v9 Tasks

For the docs hub and operator guides, start at [README.md](./README.md). This
file is the v9 task graph for evolving the v8 release-candidate product from a
capable local auditable-autonomy runtime into a clearer, more adoptable, and
more routinely useful local engineering tool.

## Purpose

This document defines Glassbox v9: the public-baseline and adoption evolution
after the v8 auditable-autonomy milestone in [tasks-v8.md](./tasks-v8.md).

It is written in the same execution style as [tasks-v1.md](./tasks-v1.md),
[tasks-v2.md](./tasks-v2.md), [tasks-v3.md](./tasks-v3.md),
[tasks-v4.md](./tasks-v4.md), [tasks-v5.md](./tasks-v5.md),
[tasks-v6.md](./tasks-v6.md), [tasks-v7.md](./tasks-v7.md), and
[tasks-v8.md](./tasks-v8.md): explicit dependencies, small vertical slices,
concrete deliverables, and quality requirements attached directly to the work.

The v2 through v8 work established the durable local runtime, event-sourced
SQLite store, daemon ownership model, packaged dashboard, full-screen terminal
client, cancellation, replay/eval release contracts, provider diagnostics,
task plans, autonomy budgets, background jobs, workspace memory, repository
intelligence, verify-repair loops, branch search, dashboard autonomy controls,
and post-v8 refactor guardrails.

The v9 goal is not to add one more large subsystem. The v9 goal is to make the
existing system feel legible, dependable, and easy to adopt:

- turn the v8 release candidate into a supported public baseline
- make first-run setup and daily workflows obvious
- make the dashboard a practical cockpit for tasks, evidence, and decisions
- promote the stable parts of v8 autonomy from advisory evidence into blocking
  release contracts
- make provider readiness more trustworthy without replacing deterministic
  replay/eval authority
- simplify the product language around sessions, tasks, evidence, memory,
  branches, and verification
- dogfood Glassbox against real repositories and convert friction into
  bounded product work

The v9 thesis is:

- preserve local-first operation and workspace-owned state
- preserve canonical events as the source of truth
- preserve one local mutation owner per workspace
- preserve deterministic replay and eval as release authority
- reduce the cognitive cost of operating Glassbox
- strengthen the few workflows that make Glassbox distinct instead of widening
  the command surface by default
- make autonomy boringly inspectable: visible plan, visible budget, visible
  stop reason, visible evidence
- keep release evidence useful for operators, not only for implementers

## Current Baseline Before V9 Execution

Treat the following as the starting point for every task in this document:

- [v8-release-candidate.md](./v8-release-candidate.md) records a GO decision for
  the v8 release candidate
- [refactor-v8.md](./refactor-v8.md) records the completed post-v8 refactor
  guardrail pass
- `glassbox command tree` exposes a broad product surface: sessions, tasks,
  branch search, memory, repository index, replay, eval, artifacts, backups,
  jobs, observability, provider diagnostics, performance budgets, projections,
  dashboard, and daemon ownership
- terminal chat remains the primary conversational surface
- the dashboard is a packaged Next.js static export served by FastAPI
- runtime state is local to `.glassbox/` by default and backed by canonical
  SQLite events plus rebuildable projections
- replay and eval cases live in `evals/` as repository-owned behavioral
  contracts
- v8 autonomy evals exist but remain advisory when their contracts are not yet
  stable enough to block release
- provider canaries and recommendations are advisory and may be stale,
  incompatible, or unavailable in uncredentialed environments
- the docs contain excellent implementation and release evidence, but the
  public operator story is still spread across many milestone documents
- `pyproject.toml` still declares version `0.1.0`, even though the release
  documentation describes a much more mature v8 candidate

## Product Direction

The v9 work should optimize for eight outcomes:

- a crisp supported-baseline story that says what Glassbox is today
- a first-run path that gets a new operator from install to useful local work
  with minimal guessing
- a daily workflow model centered on sessions, tasks, evidence, memory,
  branches, and verification
- a dashboard cockpit that makes next actions, blocked work, stale state,
  provider posture, and verification evidence obvious
- a tighter deterministic eval ladder where stable v8 autonomy behavior moves
  from advisory review into blocking release evidence
- provider evidence that is current, redacted, compatible, and actionable while
  staying non-authoritative beside deterministic contracts
- operational polish around stale repository indexes, artifact pressure,
  daemon state, package smoke, and recovery guidance
- dogfooding evidence from real repositories that exposes usability gaps before
  another major capability expansion

## Agent Execution Rules

These rules apply to every task in this file.

1. Respect dependency order. Do not start a task until its dependencies are
   complete unless the task explicitly says it can proceed in parallel.
2. Preserve the event-sourced source-of-truth rule. New operator surfaces,
   cockpit summaries, provider evidence, and dogfooding records must be derived
   from canonical events, typed API responses, retained artifacts, or explicit
   docs.
3. Preserve local-first operation. Do not introduce a hosted control plane,
   cloud authority for workspace ownership, remote worker fleet, or external
   service dependency for v9 readiness.
4. Preserve deterministic release blocking. Live-provider canaries stay
   advisory unless a task explicitly promotes a stable, credentialed,
   repeatable scenario with a clear failure policy.
5. Prefer product simplification over surface expansion. Add a new command,
   route, dashboard panel, or event only when an existing surface cannot express
   the operator need clearly.
6. Make next actions concrete. If a UI, CLI, or observability output says
   something is stale, blocked, failed, or risky, it should point to the exact
   command or dashboard action that resolves or inspects it.
7. Keep docs separated by audience. User-facing baseline docs should not require
   reading milestone task files or retained release evidence.
8. Treat provider evidence as operational confidence, not hidden authority.
   Provider readiness should be visible, redacted, current, and optional.
9. Dogfooding findings must become either accepted residual risks, docs fixes,
   tests, or concrete implementation tasks.
10. Every implementation task automatically includes:
    - automated tests for new behavior
    - `ruff` formatting and lint compliance for touched Python code
    - `ty` typecheck compliance for touched Python code
    - focused `pytest` coverage for touched runtime, CLI, web, replay, eval,
      daemon, transport, policy, memory, index, task, provider, and terminal
      behavior
    - frontend lint, typecheck, tests, and build when the task touches
      dashboard code, generated API types, or packaged static assets
    - documentation updates when operator-visible behavior, release posture,
      provider posture, packaging, onboarding, eval profiles, or public claims
      change

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
- new provider, dogfooding, release, package, or manual evidence is retained in
  the documented local path when the task creates such evidence
- autonomy remains bounded by typed policy, budgets, approvals, cancellation,
  and explicit stop reasons
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

## Recommended Validation Commands

Use the narrowest viable validation after each task, but the baseline validation
pattern for completed v9 work should include:

```bash
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run pytest
uv run glassbox command tree
uv run glassbox eval run
uv run glassbox eval audit
uv run glassbox eval report commit-smoke push-confirmation release-candidate --output-dir .glassbox/evals/v9-release-signoff
pnpm --dir frontend lint
pnpm --dir frontend typecheck
pnpm --dir frontend test
pnpm --dir frontend build
uv build --wheel --sdist
```

During incremental implementation, use narrower commands where possible:

```bash
uv run pytest tests/unit/test_specific_module.py
uv run pytest tests/integration/test_specific_flow.py
uv run ruff check src/glassbox/path.py tests/path_test.py
uv run ty check src/glassbox/path.py
uv run glassbox eval recommend src/glassbox/runtime/turn_engine.py --cwd .
pnpm --dir frontend test -- dashboard-stores.test.ts
pnpm --dir frontend typecheck
```

When a task touches generated frontend API types, package assets, provider
canaries, evals, release gates, or public docs, also run the relevant smoke or
dry-run command:

```bash
pnpm --dir frontend api:generate
pnpm --dir frontend build
uv run glassbox provider diagnostics --cwd . --json
uv run glassbox provider canary evidence --cwd . --json
uv run python scripts/validate_package_contents.py
uv run python scripts/validate_v8_release_gate.py --dry-run --evidence-dir .glassbox/releases/v9-inherited-gate-dry-run
```

Once `GBX-991` exists, use the v9 gate as the canonical full validation command:

```bash
uv run python scripts/validate_v9_release_gate.py
```

## Milestone Map

The intended v9 milestone order is:

1. v9 public-baseline contract and docs consolidation
2. first-run and daily workflow onboarding
3. command-surface and product-language simplification
4. dashboard cockpit polish and next-action clarity
5. eval promotion and release-contract strengthening
6. provider evidence freshness and recommendation reliability
7. operational maintenance polish
8. real-repository dogfooding and feedback loop
9. v9 packaging, release gate, manual evidence, and release-candidate signoff

## Task Graph

---

## Phase 91: v9 Public Baseline And Documentation Consolidation

### GBX-910: Define The v9 Public-Baseline Contract

- Status: `DONE`
- Depends on: `GBX-895`, `GBX-R251`
- Goal: convert the v8 release-candidate decision and post-v8 refactor closeout
  into one concrete v9 product contract
- Deliverables:
  - new public-baseline document describing what Glassbox supports today
  - explicit statement of the core product model: session, task, evidence,
    memory, branch, verify
  - clear split between supported daily workflows, advisory workflows, and
    release-evidence workflows
  - mapping from v8 residual risks into v9 tasks, accepted non-goals, or
    explicit advisory posture
  - decision on whether v9 is still pre-1.0, a named `0.x` baseline, or a
    candidate for a future `1.0` contract
  - update to docs hub discovery once the contract exists
- Implementation notes:
  - write for operators and contributors, not only release reviewers
  - keep local-first and event-sourced boundaries framed as product strengths
  - avoid re-listing every historical milestone; name the current supported
    workflows directly
  - do not change package version in this task unless the version policy is
    explicitly included in the deliverables
- Tests and validation included in task:
  - docs link review
  - command-help comparison against `glassbox command tree`
- Done when:
  - v9 has one concise contract that explains the supported product baseline
    without requiring a reader to traverse v6, v7, and v8 release docs

### GBX-911: Split Public Operator Docs From Release Evidence

- Status: `DONE`
- Depends on: `GBX-910`
- Goal: make day-to-day docs easy to read while retaining release evidence for
  reviewers
- Deliverables:
  - docs hub reorganization that separates `Start Here`, `Daily Workflows`,
    `Reference`, `Release Evidence`, and `Implementation History`
  - short operator guide for the main happy path: install, configure provider,
    start chat, inspect dashboard, approve actions, verify work
  - migration of release-candidate evidence links into a clearly named release
    evidence section
  - link checks or docs tests for moved references
  - root README adjustment so new readers see the product before the milestone
    archive
- Implementation notes:
  - keep historical docs intact; this task changes discovery and emphasis
  - do not delete release evidence
  - keep task graphs discoverable for contributors
  - prefer short pages that link to deep references over one enormous operator
    page
- Tests and validation included in task:
  - docs link review
  - focused docs guardrail tests if existing tests cover docs inventory
- Done when:
  - a new user can find the daily workflow path before encountering release
    candidate history

### GBX-912: Establish Version And Release Naming Policy

- Status: `DONE`
- Depends on: `GBX-910`
- Goal: align package metadata, docs, and release-candidate language so the
  product maturity story is not contradictory
- Deliverables:
  - version policy describing how `pyproject.toml` version, release-candidate
    docs, package smoke, and evidence directories relate
  - decision on the next version identifier after `0.1.0`
  - packaging metadata update if the policy chooses a new version
  - tests that assert package metadata and docs references stay aligned where
    practical
  - release note template for future v9 candidate evidence
- Implementation notes:
  - do not imply hosted stability or cloud service guarantees
  - keep semantic versioning expectations conservative
  - installed-wheel smoke should print a version that matches public docs
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_packaging_metadata.py tests/unit/test_installed_wheel_smoke.py`
  - `uv build --wheel --sdist`
- Done when:
  - package metadata and public release language tell the same story

---

## Phase 92: First-Run And Daily Workflow Onboarding

### GBX-920: Add A First-Run Readiness Check

- Status: `TODO`
- Depends on: `GBX-911`
- Goal: give new operators one command that explains whether the local workspace
  can run a useful Glassbox session
- Deliverables:
  - CLI command or subcommand for first-run readiness
  - checks for Python/runtime dependencies, workspace path, database
    bootstrap, provider configuration, dashboard static assets, repository
    index posture, tool policy manifest, and writable `.glassbox/` state
  - JSON and human-readable output
  - next-action guidance for every warning or failure
  - tests for healthy, missing-provider, missing-dashboard-assets, stale-index,
    and unwritable-state scenarios
- Implementation notes:
  - provider credentials should remain optional for local deterministic smoke
  - do not print secrets or raw environment values
  - reuse existing provider diagnostics, repository index status, static asset
    validation, and observability helpers where practical
- Tests and validation included in task:
  - focused CLI tests
  - provider diagnostics tests
  - static asset validation tests
- Done when:
  - an operator can run one readiness command and know what to do next

### GBX-921: Improve First Chat Guidance And Dashboard Handoff

- Status: `TODO`
- Depends on: `GBX-920`
- Goal: make `glassbox session chat --cwd .` feel understandable on first use
- Deliverables:
  - terminal startup summary that names model, approval behavior, autonomy mode,
    workspace, database path, and dashboard URL
  - clear guidance when provider credentials are missing and the local fallback
    model is being used
  - clear guidance when dashboard assets are unavailable or dashboard launch is
    disabled
  - first-session prompt suggestions that do not create a marketing landing
    flow inside the TUI
  - tests for plain fallback, dashboard-enabled, dashboard-disabled, and
    provider-missing startup output
- Implementation notes:
  - keep output compact in repeat sessions
  - avoid tutorial text in the main transcript
  - make the dashboard URL easy to copy from both TUI and plain mode
- Tests and validation included in task:
  - focused TUI/plain-mode tests
  - CLI interactive launch tests
- Done when:
  - first chat startup gives enough context without turning the terminal into a
    long onboarding document

### GBX-922: Add Daily Workflow Quickstart Guide

- Status: `TODO`
- Depends on: `GBX-921`
- Goal: document the ordinary loop operators should use after install
- Deliverables:
  - concise guide covering start chat, inspect dashboard, approve or deny
    actions, answer questions, cancel a turn, fork a session, verify work, and
    inspect status
  - examples for manual, inspect, edit-safe, and test-driven autonomy modes
  - guidance for when to use task continuation, memory capture, repository
    index rebuild, and eval recommend
  - explicit troubleshooting path for stale daemon, stale index, failed eval,
    missing provider, and projection degradation
- Implementation notes:
  - keep examples copy-pasteable
  - prefer commands that work in a clean local workspace
  - link to deep reference docs rather than duplicating every flag
- Tests and validation included in task:
  - docs link review
  - command examples smoke where practical
- Done when:
  - a new operator has a single daily workflow document that is shorter than
    the release-candidate docs

---

## Phase 93: Command Surface And Product Language Simplification

### GBX-930: Define The v9 Mental Model And Vocabulary

- Status: `TODO`
- Depends on: `GBX-910`, `GBX-922`
- Goal: reduce cognitive load by standardizing product language around a small
  set of concepts
- Deliverables:
  - vocabulary guide for session, task, evidence, memory, branch, verify,
    provider, daemon, and projection
  - command help review that identifies confusing aliases, overloaded terms, or
    release-only language in daily commands
  - dashboard copy review for queue names, action labels, blocked reasons,
    budget posture, and evidence panes
  - compatibility policy for renames or aliases
- Implementation notes:
  - do not break existing command scripts casually
  - prefer clearer help text before command renames
  - document any term that remains intentionally technical
- Tests and validation included in task:
  - command tree snapshot review
  - frontend text/component tests where labels change
- Done when:
  - the same core concepts are used consistently in CLI, dashboard, and docs

### GBX-931: Add Command Discovery For Daily Workflows

- Status: `TODO`
- Depends on: `GBX-930`
- Goal: help operators find the right command without reading the full command
  tree
- Deliverables:
  - workflow-oriented command discovery output, such as `glassbox command guide`
    or an equivalent subcommand
  - sections for start work, inspect state, unblock work, verify work, recover
    workspace, and release evidence
  - JSON output for docs tests or generated references if practical
  - tests for command guide coverage and stable categories
- Implementation notes:
  - keep `glassbox command tree` as the exhaustive structural view
  - workflow guide should point to existing commands, not wrap behavior
  - avoid hiding advanced commands; group them by purpose
- Tests and validation included in task:
  - CLI parser tests
  - command tree or guide snapshot tests
- Done when:
  - users can discover practical workflows without scanning every subcommand

### GBX-932: Review Low-Value Or Release-Only Surfaces For De-Emphasis

- Status: `TODO`
- Depends on: `GBX-931`
- Goal: keep the public surface approachable without deleting useful advanced
  functionality
- Deliverables:
  - inventory of commands and dashboard panels that are daily, advanced,
    release-only, or internal-maintenance oriented
  - recommendation for help text, docs grouping, dashboard navigation grouping,
    or aliases that make advanced surfaces less noisy
  - compatibility plan for any proposed deprecation
  - tests for any changed command help or route behavior
- Implementation notes:
  - this is a product-surface review, not a removal sweep
  - preserve scriptability and release automation
  - avoid burying recovery commands operators need when things go wrong
- Tests and validation included in task:
  - command tree review
  - docs review
- Done when:
  - Glassbox remains powerful without presenting every release and recovery
    surface as equally central to first use

---

## Phase 94: Dashboard Cockpit Polish And Next-Action Clarity

### GBX-940: Define The v9 Dashboard Cockpit Contract

- Status: `TODO`
- Depends on: `GBX-930`
- Goal: turn the dashboard from a broad inspection console into an obvious
  operator cockpit for active work
- Deliverables:
  - dashboard information-architecture contract for workspace overview, active
    session, task queue, evidence, memory/index, branches, and recovery cues
  - priority rules for what appears first when approval, question, failed task,
    stale index, provider warning, or degraded projection exists
  - responsive and keyboard expectations for the cockpit views
  - mapping from backend data sources to cockpit sections
- Implementation notes:
  - preserve existing deep inspection tabs
  - do not put explanatory tutorial text inside the app chrome
  - cockpit should answer: what needs my attention, why, and what can I do
    next?
- Tests and validation included in task:
  - docs review against existing frontend components and API responses
- Done when:
  - frontend work has a clear operator-priority contract rather than ad hoc
    panel additions

### GBX-941: Add Workspace Attention Summary To Dashboard

- Status: `TODO`
- Depends on: `GBX-940`
- Goal: make the dashboard first screen identify the highest-priority action
  across sessions, tasks, memory/index, provider, daemon, and projections
- Deliverables:
  - backend or frontend summary model for workspace attention state
  - dashboard UI that surfaces the highest-priority blocker or next action
  - links or actions to the relevant session, task, memory entry, index status,
    job, provider evidence, or projection command
  - tests for competing attention states and empty healthy state
- Implementation notes:
  - reuse observability and aggregate session data where practical
  - summary must not hide lower-priority queues; it should focus the operator
    without deleting context
  - stale repository index should be visible but not more urgent than pending
    approvals or active failures
- Tests and validation included in task:
  - frontend store tests
  - React component tests
  - API tests if backend response models change
- Done when:
  - opening the dashboard tells the operator what matters first

### GBX-942: Improve Evidence Drill-Down For Tasks And Verification

- Status: `TODO`
- Depends on: `GBX-941`
- Goal: make task and verification evidence easier to inspect from the cockpit
- Deliverables:
  - task detail improvements that connect plan steps, tool evidence,
    verification attempts, eval recommendations, and stop reasons
  - clearer rendering for budget exhaustion, approval waits, user-input waits,
    verification failure, provider unavailability, and cancellation
  - direct navigation from evidence rows to event log, artifact, transcript, or
    command output where available
  - tests for task evidence states and keyboard navigation
- Implementation notes:
  - do not duplicate full event logs inside every task panel
  - keep artifact and event navigation stable across session reloads
  - evidence labels should map to persisted event types or projection fields
- Tests and validation included in task:
  - frontend component tests
  - web session/task route tests if payloads change
  - Playwright workflow update if needed
- Done when:
  - a task's current state and proof trail can be understood without manually
    correlating several tabs

### GBX-943: Add Dashboard Recovery And Maintenance Cues

- Status: `TODO`
- Depends on: `GBX-941`
- Goal: bring common recovery guidance into the dashboard without making it a
  dangerous maintenance console
- Deliverables:
  - read-only recovery cues for stale daemon, stale repository index, artifact
    pressure, degraded projections, failed jobs, invalid memory, and stale
    provider canary evidence
  - command-copy affordances or action links for safe read-only checks
  - explicit confirmation for any mutating recovery action exposed in the UI
  - tests for recovery cue prioritization and command text
- Implementation notes:
  - default recovery cues should be read-only
  - reuse [recovery-maintenance-review-v8.md](./recovery-maintenance-review-v8.md)
    guidance
  - never run destructive maintenance from the dashboard without explicit
    confirmation and backend policy checks
- Tests and validation included in task:
  - frontend tests
  - API action tests if mutating actions are added
- Done when:
  - the dashboard helps operators recover local state without hiding the
    underlying command authority

---

## Phase 95: Eval Promotion And Release-Contract Strengthening

### GBX-950: Classify v8 Autonomy Advisory Cases For Promotion

- Status: `TODO`
- Depends on: `GBX-910`
- Goal: decide which v8 autonomy eval cases are stable enough to become
  blocking release evidence
- Deliverables:
  - review of `v8-autonomy-advisory` cases and their drift history
  - classification for each case: promote to release-candidate, keep advisory,
    split into smaller case, refresh baseline, or retire
  - update to capability coverage notes
  - retained review artifact under `.glassbox/evals/` or `.glassbox/releases/`
  - docs update explaining why promoted cases are deterministic enough
- Implementation notes:
  - do not promote cases that depend on live providers, timing-sensitive
    cancellation, or cancelled-fixture shortcuts without a stable contract
  - prefer promoting a smaller stable invariant over a broad noisy case
  - keep advisory value visible when a case is not ready to block release
- Tests and validation included in task:
  - `uv run glassbox eval run --profile v8-autonomy-advisory --cwd .`
  - `uv run glassbox eval audit --cwd .`
- Done when:
  - v9 has an explicit eval promotion plan instead of a permanently advisory
    autonomy suite

### GBX-951: Promote Stable Autonomy Cases Into Deterministic Profiles

- Status: `TODO`
- Depends on: `GBX-950`
- Goal: strengthen release authority by moving stable autonomy behavior into
  blocking deterministic profiles
- Deliverables:
  - updates to `evals/profiles.json` for selected promoted cases
  - updates to `evals/coverage.json` if capability expectations change
  - profile budget adjustments that keep commit-time smoke small and
    release-candidate evidence meaningful
  - tests for profile selection, budget health, release report status, and
    coverage audit behavior
  - docs update for the new eval ladder
- Implementation notes:
  - commit-time smoke should remain cheap
  - release-candidate profile can carry more autonomy evidence than commit-time
  - profile budget failures should explain whether the suite is too large,
    too noisy, or carrying unsupported/advisory cases
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_runtime_evals.py tests/unit/test_runtime_eval_coverage.py`
  - `uv run glassbox eval run --profile release-candidate --cwd .`
  - `uv run glassbox eval report commit-smoke push-confirmation release-candidate --cwd .`
- Done when:
  - release-candidate evidence covers the stable core of v8 autonomy as
    blocking deterministic behavior

### GBX-952: Improve Eval Recommendation For Daily Development

- Status: `TODO`
- Depends on: `GBX-951`
- Goal: make `eval recommend` more useful for ordinary change verification
- Deliverables:
  - clearer recommendation output grouped by commit-time, push-time,
    release-candidate, and advisory surfaces
  - stronger mappings for dashboard, task, memory, provider, repository index,
    and docs-only changes
  - skipped-check explanations for low-confidence and live-provider canary
    recommendations
  - tests for representative path changes and execution plans
- Implementation notes:
  - recommendations remain advisory until the operator executes them
  - docs-only changes should not pretend to require behavioral replay unless
    they touch eval, release, policy, or command contracts
  - keep JSON output stable for automation
- Tests and validation included in task:
  - eval recommendation unit tests
  - focused CLI tests
- Done when:
  - developers get a useful, explainable verification plan from changed paths

---

## Phase 96: Provider Evidence Freshness And Recommendation Reliability

### GBX-960: Define Provider Evidence Freshness Contract

- Status: `TODO`
- Depends on: `GBX-910`
- Goal: make provider diagnostics, canaries, and recommendations trustworthy
  enough for operators to act on without becoming release authority
- Deliverables:
  - provider evidence freshness policy covering age, schema compatibility,
    provider/model identity, redaction, credential absence, and scenario
    coverage
  - operator-visible states for fresh, stale, incompatible, missing,
    credentialless, warning, and failed evidence
  - docs update explaining how provider evidence should and should not affect
    release decisions
  - tests for stale and incompatible retained evidence
- Implementation notes:
  - do not require live credentials for deterministic release gates
  - retained evidence must not include secrets or raw prompt transcripts unless
    explicitly redacted and documented
  - provider recommendations should degrade gracefully when evidence is absent
- Tests and validation included in task:
  - provider diagnostics tests
  - provider canary evidence tests
- Done when:
  - provider warnings are precise enough to guide action instead of merely
    producing generic caution

### GBX-961: Refresh Provider Recommendation Logic For Workflow Fit

- Status: `TODO`
- Depends on: `GBX-960`
- Goal: make provider recommendations reflect task kind, autonomy mode, current
  evidence, and missing evidence more clearly
- Deliverables:
  - recommendation output that separates capability fit, risk posture, evidence
    freshness, credential readiness, and unknowns
  - scenario mapping for inspect, edit-safe, test-driven, release-candidate,
    and background-continuation workflows
  - clearer low-confidence and risky states
  - tests for fresh evidence, stale evidence, missing credentials, unknown
    model, and provider mismatch
- Implementation notes:
  - recommendations should not claim a provider is safe for autonomy solely
    because credentials exist
  - keep deterministic eval and package evidence separate from provider advice
  - prefer explicit unknowns over overconfident ranking
- Tests and validation included in task:
  - provider recommendation tests
  - CLI JSON output tests
- Done when:
  - provider recommendation is useful operational guidance with visible limits

### GBX-962: Surface Provider Evidence In The Dashboard Cockpit

- Status: `TODO`
- Depends on: `GBX-941`, `GBX-961`
- Goal: make provider posture visible where operators decide whether to proceed
  with autonomous work
- Deliverables:
  - dashboard provider evidence cue showing configured provider, model,
    freshness, advisory status, and recommended next action
  - links to provider diagnostics, retained canary evidence, or command
    guidance
  - tests for fresh, stale, missing, and warning provider states
- Implementation notes:
  - provider cues should not overshadow pending approvals, failed tasks, or
    degraded projections
  - avoid showing secrets or credential source paths
  - dashboard should label provider evidence as advisory
- Tests and validation included in task:
  - frontend store/component tests
  - API tests if provider summary route is added
- Done when:
  - operators can see provider readiness before asking Glassbox to do longer
    autonomous work

---

## Phase 97: Operational Maintenance Polish

### GBX-970: Add Repository Index Freshness Workflow Polish

- Status: `TODO`
- Depends on: `GBX-943`
- Goal: reduce friction around stale local repository intelligence
- Deliverables:
  - clearer `repo index status` output for stale, missing, fresh, and failed
    states
  - dashboard cue or command guidance that explains why the index is stale
  - optional read-only diff of index source digest inputs where practical
  - tests for stale detection and rebuild guidance
- Implementation notes:
  - repository index remains rebuildable derived state
  - do not turn index contents into hidden prompt authority
  - rebuilding should remain explicit unless a future task defines safe
    background maintenance behavior
- Tests and validation included in task:
  - repository index unit/integration tests
  - CLI output tests
- Done when:
  - stale repository intelligence is understandable and easy to refresh

### GBX-971: Improve Artifact Pressure And Cleanup Guidance

- Status: `TODO`
- Depends on: `GBX-943`
- Goal: make artifact retention and cleanup safer and clearer
- Deliverables:
  - improved artifact inspection output that distinguishes protected,
    event-referenced, orphaned, reclaimable, and missing-reference states
  - dashboard recovery cue for artifact pressure
  - docs for safe dry-run and non-dry-run prune workflow
  - tests for artifact pressure thresholds and prune previews
- Implementation notes:
  - dry-run should remain the default documented cleanup step
  - never prune event-referenced artifacts
  - retain enough evidence for replay/eval triage
- Tests and validation included in task:
  - artifact store and retention tests
  - CLI artifact command tests
- Done when:
  - operators can clean local Glassbox state without fear of destroying replay
    evidence

### GBX-972: Tighten Daemon And Background Job Recovery Guidance

- Status: `TODO`
- Depends on: `GBX-943`
- Goal: make daemon ownership and job recovery easier to understand during
  blocked work
- Deliverables:
  - clearer daemon status output for not-running, healthy, stale, failed, and
    ownership-conflict states
  - clearer job list/show output for queued, running, stale, failed, retryable,
    cancelled, and abandoned states
  - dashboard cues for stale owner and failed retryable jobs
  - tests for recovery messages and next-action commands
- Implementation notes:
  - preserve one local mutation owner per workspace
  - do not add automatic stale-owner mutation without explicit task scope
  - recovery guidance should name the safe read-only command first
- Tests and validation included in task:
  - daemon runtime tests
  - background job tests
  - observability tests
- Done when:
  - background work failures tell the operator what happened and what command
    to run next

---

## Phase 98: Real-Repository Dogfooding And Feedback Loop

### GBX-980: Define Dogfooding Evidence Protocol

- Status: `TODO`
- Depends on: `GBX-922`, `GBX-950`
- Goal: make real-use feedback concrete without committing private transcripts,
  secrets, or large artifacts
- Deliverables:
  - dogfooding protocol for running Glassbox on one or more real repositories
  - evidence template that records workflow, autonomy mode, provider posture,
    dashboard use, verification path, friction, and outcome
  - redaction rules for private source, provider output, credentials, and local
    paths
  - criteria for turning findings into tasks, docs fixes, eval cases, or
    accepted residual risks
- Implementation notes:
  - do not require dogfooding evidence to be committed if it contains private
    workspace details
  - summarize findings in docs; keep raw artifacts local unless sanitized
  - include at least one no-live-provider deterministic flow and one
    credentialed provider flow when available
- Tests and validation included in task:
  - docs review
- Done when:
  - real-world use can generate actionable evidence without leaking private
    data

### GBX-981: Run Focused Dogfooding Passes

- Status: `TODO`
- Depends on: `GBX-980`
- Goal: validate Glassbox against real coding tasks and record product friction
- Deliverables:
  - at least three focused dogfooding passes:
    - repository inspection and explanation
    - small code edit with verification
    - longer task-plan or branch-search workflow
  - retained local evidence or sanitized summaries for each pass
  - list of friction findings grouped by onboarding, terminal, dashboard,
    provider, verification, memory/index, and recovery
  - candidate eval cases or tests for repeated failure patterns
- Implementation notes:
  - prefer real tasks with normal messiness over perfectly staged fixtures
  - record where the operator had to know too much about Glassbox internals
  - do not expand scope during dogfooding; file follow-up tasks instead
- Tests and validation included in task:
  - focused validation commands chosen from actual touched surfaces
- Done when:
  - v9 priorities are informed by real operator use rather than only release
    gates

### GBX-982: Convert Dogfooding Findings Into Fixes Or Contracts

- Status: `TODO`
- Depends on: `GBX-981`
- Goal: close the loop from real-use findings to implementation, docs, evals,
  or accepted residual risks
- Deliverables:
  - triage of every dogfooding finding
  - small fixes for high-signal low-risk friction where practical
  - new tests or eval recommendations for repeated behavioral regressions
  - docs updates for workflows that were confusing but correct
  - residual-risk entries for issues not fixed in v9
- Implementation notes:
  - keep fixes focused; do not turn this into an unbounded polish bucket
  - if a finding requires a new subsystem, track it as post-v9 work
  - update eval impact rules when findings expose missing verification guidance
- Tests and validation included in task:
  - focused tests for fixed issues
  - eval recommendation or audit checks when eval metadata changes
- Done when:
  - dogfooding produces a visible improvement trail instead of anecdotal notes

---

## Phase 99: v9 Packaging, Gate, Manual Evidence, And Release Signoff

### GBX-990: Update Package Contents For v9 Public Baseline

- Status: `TODO`
- Depends on: `GBX-912`, `GBX-922`, `GBX-951`
- Goal: ensure installed artifacts include the v9 public docs, dashboard assets,
  eval profiles, and runtime surfaces needed for the supported baseline
- Deliverables:
  - package contents validation update for v9 docs and any new scripts
  - installed-wheel smoke update for first-run readiness, command discovery,
    promoted eval profiles, provider diagnostics, and dashboard static assets
  - sdist/wheel validation that static dashboard assets and generated API types
    are present
  - tests for package metadata and installed command behavior
- Implementation notes:
  - installed smoke should not require live provider credentials
  - keep package contents validation explicit rather than relying on broad
    inclusion
  - generated dashboard assets should match frontend source build
- Tests and validation included in task:
  - `uv build --wheel --sdist`
  - package contents script
  - installed-wheel smoke script
  - frontend build
- Done when:
  - v9 supported workflows are runnable from installed artifacts

### GBX-991: Add v9 Release Gate

- Status: `TODO`
- Depends on: `GBX-990`, `GBX-951`, `GBX-972`
- Goal: compose inherited v8 release evidence with v9 onboarding, cockpit,
  provider freshness, eval promotion, package, and dogfooding evidence
- Deliverables:
  - `scripts/validate_v9_release_gate.py` or equivalent gate command
  - gate stages for Python format/lint/typecheck, Python tests, frontend
    lint/typecheck/tests/build, deterministic eval report, promoted autonomy
    profile evidence, first-run readiness smoke, command discovery smoke,
    provider evidence policy check, package build, installed smoke, and retained
    summary
  - dry-run mode and explicit evidence directory support
  - `summary.json` and concise human-readable summary output
  - unit tests for stage composition, dry-run behavior, failure reporting, and
    evidence paths
- Implementation notes:
  - reuse v8 gate stages where practical
  - provider canaries remain advisory unless an explicitly promoted scenario
    exists
  - every skipped stage must have an explicit reason
  - release evidence should make adoption readiness visible, not just raw test
    pass/fail
- Tests and validation included in task:
  - gate unit tests
  - dry-run v9 gate
  - focused real gate run before release-candidate publication
- Done when:
  - v9 readiness has one command that records deterministic, package, provider,
    onboarding, and cockpit evidence clearly

### GBX-992: Complete v9 Manual Validation And Accessibility Evidence

- Status: `TODO`
- Depends on: `GBX-941`, `GBX-943`, `GBX-991`
- Goal: retain human evidence for first-run, dashboard cockpit, recovery, and
  real-use workflows that automated tests cannot fully prove
- Deliverables:
  - manual validation checklist for first-run readiness, chat startup,
    dashboard cockpit, attention summary, task evidence drill-down, recovery
    cues, provider evidence cues, and package smoke
  - terminal review evidence for supported TTY, plain fallback, startup
    summaries, approvals/questions, cancellation, daemon attach, and long output
  - dashboard review evidence for cockpit priority, keyboard flow, mobile
    layout, task evidence, memory/index recovery, provider cues, and branch
    comparison
  - named accessibility pairings and explicit non-claims
  - residual-risk list and go/no-go recommendation
- Implementation notes:
  - retain manual evidence under the same `.glassbox/releases/...` candidate
    directory as the automated gate where practical
  - keep claims bounded to the named pairings and scenarios tested
  - do not paste large generated JSON into docs
- Tests and validation included in task:
  - manual evidence review
  - docs guardrail tests if release docs are updated
- Done when:
  - v9 has human evidence for the workflows where onboarding, UI priority, and
    recovery need actual operator judgment

### GBX-993: Publish v9 Release-Candidate Guide

- Status: `TODO`
- Depends on: `GBX-991`, `GBX-992`
- Goal: publish a concise public guide for the supported v9 operating model,
  validation path, evidence expectations, non-goals, residual risks, and release
  decision
- Deliverables:
  - `v9-release-candidate.md` or equivalent operator guide
  - root README update linking the v9 public baseline and release candidate
  - docs hub update linking v9 task, baseline, onboarding, cockpit, provider,
    dogfooding, and release evidence docs
  - release-readiness checklist reflecting automated gate, manual evidence,
    provider advisory posture, package smoke, onboarding, dashboard cockpit,
    promoted evals, recovery posture, accessibility, and residual risks
  - decision section with candidate build, date, evidence directory, final
    pass/fail state, and accepted risks
- Implementation notes:
  - keep the release guide operator-readable
  - be explicit that Glassbox is local auditable autonomy, not hosted cloud
    orchestration
  - name remaining non-goals and known residual risks clearly
  - avoid overclaiming provider reliability or accessibility beyond retained
    evidence
- Tests and validation included in task:
  - docs link review
  - release docs guardrail tests
  - final v9 release gate run
- Done when:
  - v9 has a publishable release-candidate narrative backed by retained
    automated and manual evidence

## v9 Release-Candidate Readiness Checklist

Before treating a build as the v9 release candidate, complete this list:

- `uv run glassbox command tree` and workflow-oriented command discovery match
  the documented command surface.
- First-run readiness check passes in a clean local workspace or reports clear
  next actions.
- `uv run python scripts/validate_v9_release_gate.py` passes and writes
  `summary.json`.
- Manual validation exists in the same evidence directory as the automated
  summary where practical.
- The deterministic `release-candidate` eval profile passes.
- Stable v8 autonomy behavior selected for promotion is included in blocking
  deterministic release evidence.
- Advisory autonomy cases still have explicit non-blocking status and reasons.
- Provider diagnostics and provider evidence freshness checks either pass with
  retained redacted evidence or record explicit skip reasons.
- Dashboard cockpit evidence covers attention summary, task evidence
  drill-down, recovery cues, provider cues, mobile, and keyboard workflows.
- Terminal review evidence covers first-run chat startup, dashboard handoff,
  approvals/questions, cancellation, daemon attach, long output, and fallback.
- Recovery review evidence covers observability, daemon, jobs, projections,
  artifacts, stale repository index, stale provider evidence, backup, package,
  and eval workflows.
- Package artifacts include static dashboard assets, generated API files, v9
  docs, eval profiles, release scripts, and installed smoke support.
- Dogfooding findings have been triaged into fixes, docs, evals, accepted
  residual risks, or post-v9 tasks.
- Named accessibility pairings are recorded before making stronger
  accessibility claims.
- Residual risks are named, mitigated, and accepted in the release decision.

## Deliberate v9 Non-Goals

Do not spend v9 effort on these unless a later task explicitly changes scope:

- hosted control plane
- cloud authority for workspace ownership
- remote multi-user orchestration
- simultaneous multi-writer mutation of one workspace
- distributed worker fleet
- plugin marketplace or arbitrary third-party tool loading
- browser-native code editing as a replacement for local tools
- remote policy enforcement
- hidden provider-side memory
- uninspectable vector-store retrieval treated as source of truth
- automatic background mutation without explicit budget, policy, and stop
  reasons
- automatic merging of branch-search candidates into parent history
- replacing deterministic replay/eval release authority with live-provider
  canaries
- removing the plain terminal fallback
- broad command removals without a compatibility and migration policy

Multiple local observers, clearer local autonomy, stronger release contracts,
and better operator experience are in scope. Multiple concurrent mutation
owners and cloud authority are not.
