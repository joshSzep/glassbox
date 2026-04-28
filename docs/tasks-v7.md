# Glassbox v7 Tasks

For the docs hub and operator guides, start at [README.md](./README.md). This file is the v7 task graph for evolving the v6 release-candidate product into a broader adoption, scale, and verification milestone.

## Purpose

This document defines Glassbox v7: the adoption-and-scale evolution after the v6 release-hardening milestone in [tasks-v6.md](./tasks-v6.md).

It is written in the same execution style as [tasks-v1.md](./tasks-v1.md), [tasks-v2.md](./tasks-v2.md), [tasks-v3.md](./tasks-v3.md), [tasks-v4.md](./tasks-v4.md), [tasks-v5.md](./tasks-v5.md), and [tasks-v6.md](./tasks-v6.md): explicit dependencies, small vertical slices, concrete deliverables, and quality requirements attached directly to the work.

The v2 through v6 work established the durable local runtime, SQLite event store, daemon ownership model, static-exported dashboard, full-screen terminal client, real cancellation, resilient live transport, reproducible packages, manual QA evidence, provider diagnostics, advisory canaries, and objective release gates. That foundation is now strong enough that v7 should optimize for real-world adoption pressure rather than another broad rewrite.

The v7 goal is to make Glassbox trustworthy for longer local sessions, more varied provider behavior, richer repository-owned verification, clearer policy governance, and smoother first-run adoption while preserving the project's core advantage: local-first, event-sourced, operator-visible agent work.

## Product Direction

The v7 work should optimize for eight outcomes:

- broader deterministic eval coverage for approval, ask-user, cancellation, daemon attach, and dashboard action workflows
- a provider capability and canary matrix that explains real-provider behavior without replacing deterministic release gates
- larger-session scale improvements for snapshots, transcripts, event logs, dashboard rendering, and projection health
- deeper daemon and live-transport reliability under reconnect, multiple observers, stale ownership, and stream turbulence
- repository-owned policy contracts that make tool behavior, approvals, and blocked actions easier to audit and evolve
- dashboard evidence surfaces that help operators compare branches, understand latency, and explain policy decisions
- accessibility review that moves from broad manual claims into named terminal, browser, and assistive-technology pairings
- a smoother first-run and packaging experience for new local users and source builders

The v7 thesis is:

- preserve local-first operation and workspace-owned state
- preserve canonical events as the source of truth
- preserve the terminal as the primary chat surface and the dashboard as the paired operator console
- keep deterministic replay and eval blocking while keeping live-provider canaries advisory unless promoted explicitly
- improve scale, verification depth, and adoption ergonomics before expanding into hosted collaboration
- avoid cloud authority, remote multi-user orchestration, browser-native code editing, plugin marketplaces, and marketplace-style tool distribution in this milestone

## Current Baseline Before V7 Execution

Treat the following as the starting point for every task in this document:

- [v6-release-candidate.md](./v6-release-candidate.md) records a GO decision for the v6 release candidate
- `glassbox session chat` launches the full-screen Textual TUI by default in supported terminals and keeps `--plain` as the explicit compatibility path
- the dashboard is a Next.js static export served by FastAPI and packaged into the Python distribution
- terminal and dashboard clients consume backend snapshots plus `/sessions/{session_id}/events` SSE tails with sequence-based reconnect semantics
- `glassbox daemon start|status|stop` provides workspace-scoped runtime ownership and `session attach` can reconnect to daemon-owned sessions
- cancellation is persisted as event evidence and replay/eval normalize intentional cancellation distinctly from generic failure
- the SQLite store uses canonical events plus rebuildable projections and schema migrations
- replay and eval support repository-owned cases, profiles, coverage audits, impact recommendations, baseline promotion and refresh, and release-signoff reports
- advisory provider diagnostics and canaries exist, with deterministic replay/eval remaining the release authority
- the v6 gate validates Python, frontend, deterministic eval, package contents, installed smoke, and retained evidence
- manual v6 evidence covers terminal, dashboard, recovery, installed-package smoke, provider canary policy, and bounded accessibility claims

## v7 Adoption And Scale Findings

Treat these findings as evidence that should steer the first implementation slices:

- the curated eval portfolio is useful but still light for approval, ask-user, dashboard actions, daemon attach, and provider-sensitive cancellation behavior
- provider canaries are intentionally advisory and scenario-limited; operators need a clearer capability matrix before trusting live-provider behavior across models
- full session snapshots and event-heavy dashboard panes will become expensive for long sessions unless pagination, virtualization, and lazy detail loading are introduced
- the current SSE plus persisted replay model is correct, but daemon and multi-observer behavior need stronger turbulence, stale-owner, and recovery evidence
- tool policy is practical, but repository-owned teams will need clearer precedence, explainability, and stable fixtures for policy changes
- branch comparison, lineage, metrics, and policy evidence exist as product surfaces but can become much more useful as operator decision tools
- v6 accessibility review is honest but bounded; v7 should test named assistive-technology pairings before making stronger claims
- v6 packaging is disciplined, but first-run setup still depends on users knowing the right provider, profile, dashboard, and validation commands

## Agent Execution Rules

These rules apply to every task in this file.

1. Respect dependency order. Do not start a task until its dependencies are complete unless the task explicitly says it can proceed in parallel.
2. Preserve the event-sourced source-of-truth rule. Scale improvements, caches, pagination, summaries, and dashboard state must remain derived from canonical events and projections.
3. Preserve local-first operation. Do not introduce a hosted control plane, cloud ownership authority, remote multi-user system, or external service dependency for v7 readiness.
4. Preserve deterministic release blocking. Live-provider canaries stay advisory unless a task explicitly promotes a scenario with stable credentials, repeatability, and failure policy.
5. Keep terminal and dashboard roles intact. The TUI remains the primary chat surface; the dashboard remains the deeper operator console and evidence surface.
6. Prefer root-cause scale and reliability fixes over UI-only messaging when runtime behavior or read paths are incomplete.
7. Treat repository-owned verification as product behavior. New eval cases, provider matrices, policy fixtures, and release evidence must be reviewable and explain why they matter.
8. Keep non-interactive commands scriptable. Release, observability, replay, eval, projection, backup, daemon, provider, and package workflows should remain useful in CI or clean shell environments.
9. If v7 work exposes an API mismatch, fix or document the backend service/API contract before encoding terminal-only or browser-only workarounds.
10. Every implementation task automatically includes:
    - automated tests for new behavior
    - `ruff` formatting and lint compliance for touched Python code
    - `ty` typecheck compliance for touched Python code
    - focused `pytest` coverage for touched runtime, CLI, web, replay, eval, daemon, transport, and terminal behavior
    - frontend lint, typecheck, tests, and build when the task touches dashboard code, generated API types, or packaged static assets
    - documentation updates when contracts, routes, commands, packaging, provider workflows, release gates, accessibility claims, policy behavior, or operator-visible behavior change

## Completion Contract For Any Task

A task is complete only when all of the following are true:

- the implementation exists in the intended module boundary
- automated tests covering the new behavior exist and pass
- Python lint, typecheck, and focused tests pass for touched backend and CLI code
- frontend lint, typecheck, tests, and build pass if the task touches frontend, generated API types, or web dashboard behavior
- deterministic replay/eval behavior remains stable or intentional drift is documented through the eval refresh workflow
- new eval, provider-canary, policy, or release evidence is retained in the documented local path when the task creates such evidence
- the task does not leave placeholder code or hidden follow-up work outside this file
- terminal behavior remains usable in supported TTY and documented fallback contexts
- the dashboard remains usable through the FastAPI-served production build path
- docs are updated if the task changes the operator-visible product, verification posture, release posture, or public claims

## Suggested Status Markers

If an agent updates this document later, use one of these markers next to task IDs:

- `TODO`
- `IN_PROGRESS`
- `BLOCKED`
- `DONE`

## Expected Repository Targets

These are the main implementation areas referenced below:

```text
pyproject.toml
scripts/
src/glassbox/
    cli/
    core/
    runtime/
    tools/
    store/
    web/
frontend/
    api/
    app/
    components/
    generated/
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
    profiles.json
docs/
```

## Recommended Validation Commands

Use the narrowest viable validation after each task, but the baseline validation pattern for completed v7 work should include:

```bash
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run pytest
uv run glassbox eval run
uv run glassbox eval audit
uv run glassbox eval report commit-smoke push-confirmation release-candidate --output-dir .glassbox/evals/v7-release-signoff
pnpm --dir frontend lint
pnpm --dir frontend typecheck
pnpm --dir frontend test
pnpm --dir frontend build
uv build --wheel --sdist
uv run python scripts/validate_v6_release_gate.py
```

During incremental implementation, use narrower commands where possible:

```bash
uv run pytest tests/integration/test_approval_workflow.py tests/integration/test_ask_user_tool.py
uv run pytest tests/integration/test_daemon_runtime.py tests/integration/test_web_sse_events.py tests/unit/test_runtime_transport.py
uv run pytest tests/integration/test_web_session_snapshot.py tests/integration/test_web_session_aggregate.py
uv run pytest tests/unit/test_runtime_eval_coverage.py tests/unit/test_eval_recommendations.py
uv run pytest tests/unit/test_tools_policy.py tests/integration/test_command_tool.py
pnpm --dir frontend test -- dashboard-stores session-inspector sse-client
pnpm --dir frontend test:e2e -- operator-workflows
uv run ruff check src/glassbox tests scripts
uv run ty check
```

When a task touches provider canaries, packaging, or release gates, also run the relevant smoke or dry-run command:

```bash
uv run glassbox provider diagnostics --cwd . --json
uv run glassbox provider canary run --cwd . --output-dir .glassbox/provider-canary/v7 --json
pnpm --dir frontend api:generate
pnpm --dir frontend build
uv run python scripts/validate_package_contents.py
uv run python scripts/validate_v6_release_gate.py --dry-run --evidence-dir .glassbox/releases/v7-gate-dry-run
```

## Milestone Map

The intended v7 milestone order is:

1. v7 adoption-and-scale contract and baseline inventory
2. deterministic eval portfolio expansion
3. provider capability and canary matrix
4. larger-session scale and read-path hardening
5. daemon, live transport, and multi-observer reliability
6. repository-owned tool-policy governance
7. dashboard evidence, comparison, and analytics refinement
8. accessibility, onboarding, packaging, and release-candidate signoff

## Task Graph

---

## Phase 71: v7 Contract And Baseline Inventory

### GBX-710: Define The v7 Adoption-And-Scale Contract

- Status: `DONE`
- Depends on: `GBX-704`
- Goal: convert the v6 release-candidate decision and post-v6 backlog into one concrete v7 product contract
- Deliverables:
  - documentation update defining v7 scope, non-goals, supported workflow set, evidence expectations, and release posture
  - explicit mapping from v6 residual risks and post-v6 follow-up backlog into v7 tasks or accepted non-goals
  - explicit rule that v7 does not introduce hosted collaboration, remote ownership authority, browser-native code editing, or marketplace-style tools
  - release-readiness checklist that names deterministic eval, provider-canary, scale, daemon, dashboard, accessibility, and onboarding evidence separately
  - risk register shape for accepted v7 residual risks
- Implementation notes:
  - start from [v6-release-candidate.md](./v6-release-candidate.md), [v6-release-gate.md](./v6-release-gate.md), and this task file
  - keep the contract operator-readable rather than turning it into internal engineering notes only
  - avoid reopening v2 through v6 decisions unless they directly block adoption, scale, or verification depth
- Tests and validation included in task:
  - docs review against implemented command help and current release scripts
  - lightweight docs test if a new v7 contract document is added
- Done when:
  - contributors have one code-aligned v7 contract that explains what must be true before calling the next release candidate ready

Completion notes:

- Added [v7-adoption-scale-contract.md](./v7-adoption-scale-contract.md) with v7 scope, non-goals, supported workflow set, v6 follow-up mapping, evidence classes, release-readiness checklist, residual-risk register shape, and pass/fail policy.
- Preserved the local-first, event-sourced, deterministic-release-blocking boundary while keeping live-provider canaries advisory by default.
- Added a documentation guardrail for the v7 contract contents.
- Validation: `uv run pytest tests/unit/test_release_candidate_docs.py`.

### GBX-711: Inventory v7 Scale, Verification, Provider, And Adoption Gaps

- Status: `DONE`
- Depends on: `GBX-710`
- Goal: establish a code-aligned baseline of current eval coverage, provider canaries, long-session behavior, daemon transport evidence, policy fixtures, accessibility evidence, and onboarding paths
- Deliverables:
  - inventory of existing deterministic eval cases, profiles, capability coverage, impact rules, and release-signoff reports
  - inventory of provider diagnostics and canary scenarios, including supported providers, skipped states, and retained evidence shape
  - inventory of large-session read paths, snapshot sizes, event-log rendering paths, projection rebuild behavior, and frontend rendering risks
  - inventory of daemon attach, SSE reconnect, multi-observer, stale-owner, and recovery tests
  - inventory of policy configuration, blocked-command behavior, approval semantics, and current policy tests
  - inventory of first-run docs, provider setup docs, profile defaults, and package install smoke coverage
  - explicit list of concerns with weak or missing coverage
- Implementation notes:
  - distinguish deterministic release blockers from advisory, manual, and provider-dependent evidence
  - include both source checkout and installed-package workflows
  - do not invent heavy new infrastructure in this task; this is the audit that feeds later implementation
- Tests and validation included in task:
  - docs review against `evals/coverage.json`, `evals/impact.json`, `evals/profiles.json`, provider commands, release scripts, and command help
- Done when:
  - v7 implementers know exactly what exists, what is weak, and what should be promoted into stronger coverage

Completion notes:

- Added [v7-scale-verification-inventory.md](./v7-scale-verification-inventory.md) with the current command surface, deterministic eval portfolio, provider diagnostics and canary evidence, larger-session read paths, daemon and transport evidence, policy governance posture, accessibility evidence, onboarding and packaging baseline, recommended gate membership, and weak-coverage summary.
- Reviewed the inventory against `evals/coverage.json`, `evals/impact.json`, `evals/profiles.json`, current eval cases, [providers.md](./providers.md), [tool-policy.md](./tool-policy.md), [release-packaging.md](./release-packaging.md), [persistent-runtime.md](./persistent-runtime.md), and `uv run glassbox command tree`.
- Added a documentation guardrail for the v7 inventory contents.
- Validation: `uv run pytest tests/unit/test_release_candidate_docs.py`; `uv run glassbox command tree`.

### GBX-712: Update Documentation Discovery For v7

- Status: `DONE`
- Depends on: `GBX-710`, `GBX-711`
- Goal: make the v7 plan and baseline inventory discoverable from the documentation hub without requiring users to know the task file name
- Deliverables:
  - docs hub update linking this task graph and any v7 contract or inventory docs
  - root README update only if the public supported operating model changes
  - guide-map additions for v7 scale, provider, eval, policy, onboarding, or release evidence docs as they land
  - docs tests if existing release-candidate documentation guardrails are extended
- Implementation notes:
  - keep task docs separate from operator guides
  - do not overpromise v7 outcomes before implementation tasks are complete
- Tests and validation included in task:
  - docs link review
  - existing docs tests if present
- Done when:
  - a contributor can discover the v7 plan and evidence expectations from the docs index

Completion notes:

- Updated [README.md](./README.md) in the docs hub to link [tasks-v7.md](./tasks-v7.md), [v7-adoption-scale-contract.md](./v7-adoption-scale-contract.md), and [v7-scale-verification-inventory.md](./v7-scale-verification-inventory.md) from the start-here and deep-reference sections.
- Cross-linked [v7-adoption-scale-contract.md](./v7-adoption-scale-contract.md) and [v7-scale-verification-inventory.md](./v7-scale-verification-inventory.md) so the contract and inventory can be read together.
- Added documentation guardrails for v7 docs hub discovery and v7 Phase 71 cross-linking.
- Validation: `uv run pytest tests/unit/test_release_candidate_docs.py`.

---

## Phase 72: Deterministic Eval Portfolio Expansion

### GBX-720: Promote Approval Workflow Eval Coverage

- Status: `DONE`
- Depends on: `GBX-711`
- Goal: make approval workflow behavior part of the curated deterministic eval portfolio instead of relying only on integration and release-gate evidence
- Deliverables:
  - replayable approval session fixture or bundle promoted into `evals/bundles/`
  - eval case manifest under `evals/cases/` with owner, capabilities, severity, verification stages, and baseline history
  - capability coverage update mapping approval behavior to the new case
  - impact-rule update for approval-related runtime, CLI, web, and frontend paths where appropriate
  - documentation note explaining what approval behavior the case protects and what remains covered by integration tests
- Implementation notes:
  - prefer a small deterministic case with a stable model transcript and explicit approval evidence
  - preserve approval denial and approval acceptance semantics as separate evidence if one case cannot cover both clearly
  - avoid live-provider dependencies in the deterministic case
- Tests and validation included in task:
  - `uv run glassbox eval run NEW_CASE_ID --cwd .`
  - `uv run glassbox eval audit --cwd .`
  - focused approval integration tests
- Done when:
  - approval workflow drift can be detected through repository-owned deterministic eval evidence

Completion notes:

- Added `approval.approved-patch` as an advisory deterministic eval case with a replay bundle generated from a confirm-mode `apply_patch` session.
- Updated `approval_flow` coverage and approval impact rules so approval-related runtime, CLI, web, and dashboard action changes recommend the curated case.
- Documented the protected approval contract in [v7-scale-verification-inventory.md](./v7-scale-verification-inventory.md): persisted approval request, approval decision, resumed tool execution, and completed assistant output are deterministic; denial-specific and live dashboard resolution behavior remain focused integration evidence.
- Validation: `uv run glassbox eval run approval.approved-patch --cwd .`, `uv run glassbox eval audit --cwd .`, and focused approval integration tests.

### GBX-721: Promote Ask-User Workflow Eval Coverage

- Status: `DONE`
- Depends on: `GBX-711`
- Goal: make `ask_user` suspension and answer resumption part of the curated deterministic eval portfolio
- Deliverables:
  - replayable ask-user session fixture or bundle promoted into `evals/bundles/`
  - eval case manifest under `evals/cases/` with owner, capabilities, severity, verification stages, and baseline history
  - capability coverage update mapping ask-user behavior to the new case
  - impact-rule update for ask-user, answer, question, and resumption paths where appropriate
  - documentation note explaining deterministic expectations for question, answer, and resumed assistant output
- Implementation notes:
  - cover the persisted `UserQuestionAsked` and `UserAnswerProvided` event family explicitly
  - keep operator timing out of deterministic expectations
  - avoid coupling the case to exact transient UI copy
- Tests and validation included in task:
  - `uv run glassbox eval run NEW_CASE_ID --cwd .`
  - `uv run glassbox eval audit --cwd .`
  - focused ask-user integration tests
- Done when:
  - ask-user workflow drift can be detected through repository-owned deterministic eval evidence

Completion notes:

- Added `ask-user.answer-resume` as an advisory deterministic eval case with a replay bundle generated from an `ask_user` suspension and answer-resumption session.
- Updated `ask_user_flow` coverage and ask-user impact rules so ask, answer, question, web-route, and dashboard action changes recommend the curated case.
- Documented the deterministic expectation in [v7-scale-verification-inventory.md](./v7-scale-verification-inventory.md): persisted question, answer, and answer-aware resumed output are covered; operator timing and UI-specific validation remain focused integration evidence.
- Validation: `uv run glassbox eval run ask-user.answer-resume --cwd .`, `uv run glassbox eval audit --cwd .`, and focused ask-user integration tests.

### GBX-722: Promote Daemon Attach And Dashboard Action Eval Coverage

- Status: `DONE`
- Depends on: `GBX-720`, `GBX-721`
- Goal: add deterministic coverage for daemon-backed attach and dashboard-originated actions where replay can represent the behavior without live process assumptions
- Deliverables:
  - eval or replay fixtures that preserve daemon attach-relevant event history and dashboard action-origin metadata where available
  - case manifests for daemon attach, dashboard prompt submission, dashboard approval resolution, dashboard answer submission, or a justified minimal subset
  - coverage and impact-rule updates for daemon, web routes, session query, and frontend action surfaces
  - documentation explaining which live daemon behaviors remain integration-only because they depend on process lifecycle
- Implementation notes:
  - do not pretend replay proves live process health or socket behavior
  - separate event-contract determinism from daemon lifecycle smoke
  - prefer small cases that protect action semantics rather than broad UI transcripts
- Tests and validation included in task:
  - selected new eval cases
  - focused daemon and web session interaction tests
  - frontend action tests if dashboard action contracts change
- Done when:
  - dashboard and daemon-adjacent action semantics have deterministic regression evidence where replay can validly prove them

Completion notes:

- Added advisory case manifests `dashboard.action-approval`, `dashboard.action-answer`, and `daemon.attach-persisted-actions` over the replay-representable approval and ask-user bundles from GBX-720 and GBX-721.
- Added `dashboard_actions` and `daemon_attach` capability coverage plus impact rules for web routes, dashboard/frontend action surfaces, daemon ownership, and attach-related CLI paths.
- Documented the boundary in [v7-scale-verification-inventory.md](./v7-scale-verification-inventory.md): replay protects canonical persisted action events and attach-readable history; action-origin metadata, live daemon process health, socket behavior, optimistic UI, and stale-owner recovery remain integration, frontend, and release-smoke evidence.
- Validation: `uv run glassbox eval run dashboard.action-approval dashboard.action-answer daemon.attach-persisted-actions --cwd .`, `uv run glassbox eval audit --cwd .`, and focused daemon/web session interaction tests.

### GBX-723: Expand Cancellation Eval Variants

- Status: `DONE`
- Depends on: `GBX-711`
- Goal: broaden cancellation eval coverage beyond the current cancelled-turn baseline into representative model-call, tool-execution, and reconnect-sensitive variants
- Deliverables:
  - additional cancellation eval cases or selected-invariant variants for model-call cancellation, tool-execution cancellation, and repeated cancellation requests
  - capability coverage update describing cancellation sub-behaviors and release criticality
  - replay expectation updates if new cancellation evidence requires a clearer invariant mode
  - docs update explaining what cancellation replay can and cannot prove
- Implementation notes:
  - keep provider remote-computation stop behavior out of deterministic expectations
  - preserve local persisted cancellation evidence as the release-bearing contract
  - avoid brittle wall-clock timing assertions
- Tests and validation included in task:
  - selected new eval cases
  - focused cancellation unit and integration tests
- Done when:
  - cancellation regressions across core local stages are visible in deterministic eval evidence

Completion notes:

- Added `cancellation.model-call`, `cancellation.tool-execution`, and `cancellation.repeated-request` advisory cases, with compact bundles for tool-execution and repeated/reconnect-sensitive cancellation evidence.
- Updated `cancellation` capability coverage to `multi_case` and added cancellation impact rules for model-loop, turn-engine, turn-event, tool-execution, subprocess, web cancel, and interactive CLI paths.
- Documented the cancellation replay boundary in [v7-scale-verification-inventory.md](./v7-scale-verification-inventory.md): local persisted cancellation evidence is deterministic; provider remote-computation stop behavior, live socket timing, and wall-clock assertions remain outside replay.
- Validation: `uv run glassbox eval run cancellation.model-call cancellation.tool-execution cancellation.repeated-request --cwd .`, `uv run glassbox eval audit --cwd .`, and focused cancellation unit/integration tests.

### GBX-724: Add v7 Eval Profile And Release-Signoff Updates

- Status: `DONE`
- Depends on: `GBX-720`, `GBX-721`, `GBX-722`, `GBX-723`
- Goal: update repository-owned eval profiles, budgets, coverage audits, and release reports for the expanded v7 eval portfolio
- Deliverables:
  - `evals/profiles.json` updates for any new commit-time, push-time, release-candidate, or advisory profile membership
  - profile budget review for selected case count, invariant count, model-call proxy, and artifact byte limits
  - `evals/coverage.json` audit passing with no uncovered release-critical v7 capability
  - release-signoff report examples or docs showing the v7 deterministic eval contract
  - recommendation output updates if impact rules now map to new cases or profiles
- Implementation notes:
  - keep commit-time smoke small and fast
  - move only stable deterministic cases into blocking profiles
  - keep exploratory, provider-sensitive, or noisy cases advisory until they stabilize
- Tests and validation included in task:
  - `uv run glassbox eval audit --cwd .`
  - `uv run glassbox eval report commit-smoke push-confirmation release-candidate --output-dir .glassbox/evals/v7-release-signoff --cwd .`
  - eval recommendation tests if impact metadata changes
- Done when:
  - the expanded eval portfolio has clear profile membership, budgets, and release-signoff behavior

Completion notes:

- Promoted the stable approval and ask-user cases into the blocking `release-candidate` profile and reviewed its selected-case, selected-invariant, model-call, and artifact-size budgets.
- Added `v7-workflow-advisory` for the dashboard action, daemon-adjacent attach, and cancellation variants that remain deterministic but non-blocking while origin metadata, live daemon lifecycle, socket timing, and provider stop behavior stay outside replay.
- Updated profile governance impact metadata and documented the v7 profile split in [v7-scale-verification-inventory.md](./v7-scale-verification-inventory.md).
- Validation: `uv run glassbox eval audit --cwd .`, `uv run glassbox eval report commit-smoke push-confirmation release-candidate --output-dir .glassbox/evals/v7-release-signoff --cwd .`, `uv run glassbox eval run --profile v7-workflow-advisory --cwd .`, and eval recommendation/profile tests.

---

## Phase 73: Provider Capability And Canary Matrix

### GBX-730: Define Provider Capability Matrix Contract

- Status: `DONE`
- Depends on: `GBX-711`
- Goal: define a structured local evidence model for provider capabilities without making live-provider checks deterministic release blockers
- Deliverables:
  - provider capability matrix schema covering provider, model, scenario, credential state, streaming support, tool-call support, approval behavior, ask-user behavior, cancellation behavior, dashboard compatibility, daemon attach compatibility, result, skipped reason, and redaction status
  - docs update explaining advisory canary policy, credential handling, redaction, and pass/fail interpretation
  - command output shape for showing current capability evidence in human-readable and JSON forms
- Implementation notes:
  - keep secrets out of evidence artifacts
  - keep deterministic eval reports separate from provider canary reports
  - make skipped credentials explicit rather than silently green
- Tests and validation included in task:
  - unit tests for schema serialization and redaction
  - docs review against [providers.md](./providers.md) and [v6-release-candidate.md](./v6-release-candidate.md)
- Done when:
  - provider canary evidence has a reviewable matrix shape that can survive across releases

Completion notes:

- Added provider capability matrix models covering provider, model, scenario, credential state, streaming, tool calls, approval, ask-user, cancellation, dashboard compatibility, daemon attach compatibility, result, skipped reason, and redaction status.
- Threaded the matrix into provider canary summary JSON and human output without changing live-provider pass/fail policy.
- Updated [providers.md](./providers.md) and [v7-scale-verification-inventory.md](./v7-scale-verification-inventory.md) to explain advisory interpretation, redaction, credential handling, and separation from deterministic release signoff.
- Validation: `uv run pytest tests/unit/test_runtime_provider_config.py tests/integration/test_provider_mode_runtime.py`.

### GBX-731: Expand Provider Diagnostics For Capability Preflight

- Status: `DONE`
- Depends on: `GBX-730`
- Goal: make provider diagnostics explain whether a model is configured well enough for each advisory canary scenario before a run starts
- Deliverables:
  - diagnostic fields for provider family, configured model, credential source, base URL posture, tool-call capability assumptions, streaming assumptions, and known unsupported scenarios
  - JSON and human output updates that remain redacted
  - docs update showing preflight examples for OpenAI, Anthropic, missing credentials, and unsupported local provider modes
- Implementation notes:
  - diagnostics should not contact remote providers unless the command explicitly promises a live check
  - avoid printing raw environment variable values or prompt content
  - keep provider-specific heuristics isolated from generic runtime bootstrap
- Tests and validation included in task:
  - provider diagnostics unit tests
  - focused CLI command tests
- Done when:
  - operators can tell which canary scenarios are expected to run, skip, or fail before starting live-provider work

Completion notes:

- Added offline capability preflight fields to provider diagnostics for provider family, configured model, credential source, base URL posture, streaming and tool-call assumptions, known unsupported scenarios, and per-scenario readiness.
- Updated diagnostics JSON and human output while preserving redaction and avoiding remote provider calls.
- Updated [providers.md](./providers.md) with OpenAI, Anthropic, missing-credential, and local/unsupported preflight interpretation.
- Validation: `uv run pytest tests/unit/test_runtime_provider_config.py tests/integration/test_provider_mode_runtime.py`.

### GBX-732: Add Multi-Scenario Provider Canary Runs

- Status: `DONE`
- Depends on: `GBX-730`, `GBX-731`
- Goal: broaden advisory provider canaries beyond streaming text into representative tool, approval, ask-user, cancellation, dashboard, and daemon attach scenarios
- Deliverables:
  - canary scenario definitions for streaming text, tool call, approval, ask-user, cancellation, dashboard action, and daemon attach where feasible
  - scenario selection, skip, timeout, and redacted evidence handling
  - retained summary artifacts under a documented `.glassbox/provider-canary/` or release evidence path
  - tests for credential-unavailable skips and fake-provider scenario execution
- Implementation notes:
  - keep live-provider canaries advisory by default
  - make scenario limits visible in output
  - prefer deterministic fake-provider coverage for canary orchestration code
- Tests and validation included in task:
  - unit tests for canary selection and summary output
  - integration tests using fake providers where practical
  - optional manual live-provider run with retained redacted evidence
- Done when:
  - provider canary output can explain a provider's observed behavior across core Glassbox workflows

Completion notes:

- Added provider canary scenario definitions for streaming text, tool call, approval, ask-user, cancellation, dashboard, and daemon attach workflows.
- Default canary runs now retain all core scenario rows, include automation status and timeout metadata, and keep preflight-only scenarios explicitly skipped.
- Moved the default retained artifact path to `.glassbox/provider-canary/provider-canary-summary.json`, with `--output-dir` still available for release evidence paths.
- Added timeout handling and fake-provider orchestration coverage for the automated streaming scenario plus preflight-only multi-scenario summary output.
- Validation: `uv run pytest tests/unit/test_runtime_provider_config.py tests/integration/test_provider_mode_runtime.py`.

### GBX-733: Surface Provider Capability Evidence In Release And Operator Workflows

- Status: `DONE`
- Depends on: `GBX-732`
- Goal: make provider capability evidence easy to inspect from release evidence, provider commands, and dashboard or observability surfaces without confusing it with deterministic release signoff
- Deliverables:
  - provider command for listing recent capability matrix evidence or showing one retained canary run
  - release evidence pointers for advisory provider matrix artifacts
  - observability summary or dashboard evidence cue when retained provider evidence is missing, stale, skipped, or failed
  - docs update explaining how operators should act on advisory canary results
- Implementation notes:
  - do not make provider evidence a hidden prerequisite for local deterministic workflows
  - keep stale evidence warnings advisory unless a release task explicitly changes policy
  - avoid dashboard noise when no provider credentials are expected
- Tests and validation included in task:
  - focused provider CLI tests
  - observability or dashboard tests if those surfaces change
- Done when:
  - advisory provider evidence is discoverable, interpretable, and clearly separated from blocking deterministic evidence

Completion notes:

- Added `glassbox provider canary evidence` for inspecting the latest retained provider capability matrix summary or a specific retained summary path.
- Surfaced provider-canary retained-evidence status in `glassbox observability status` JSON and human output, including missing, stale, skipped, warning, failed, and passed states.
- Updated [providers.md](./providers.md), [v7-scale-verification-inventory.md](./v7-scale-verification-inventory.md), and [v6-release-candidate.md](./v6-release-candidate.md) with release/operator evidence pointers and advisory interpretation.
- Validation: `uv run pytest tests/unit/test_runtime_provider_config.py tests/integration/test_provider_mode_runtime.py`.

---

## Phase 74: Larger-Session Scale And Read-Path Hardening

### GBX-740: Establish Larger-Session Performance Baselines

- Status: `DONE`
- Depends on: `GBX-711`
- Goal: measure current behavior for long transcripts, large event logs, many tool calls, many artifacts, and many sessions before changing APIs or UI paths
- Deliverables:
  - deterministic fixture generator or test helper for large local session shapes
  - baseline metrics for session snapshot building, session aggregate queries, projection checks, transcript reads, event-log reads, artifact inspection, and dashboard render-critical payload sizes
  - documented performance budgets or proposed budget updates
  - risk list for read paths that need pagination, lazy loading, or projection changes
- Implementation notes:
  - keep fixtures provider-free and deterministic
  - measure source and installed-package paths where practical
  - avoid optimizing before identifying the slow or memory-heavy paths
- Tests and validation included in task:
  - performance-budget tests or focused integration tests for large fixtures
  - docs review against existing performance budget command output
- Done when:
  - v7 has a measured baseline for larger-session scale work

Completion notes:

- Added deterministic larger-session fixture coverage in `tests/integration/large_session_fixture.py` and `tests/integration/test_large_session_baselines.py` with 120 turns, 240 transcript messages, 80 read-only tool calls, 40 event-referenced artifacts, and 681 canonical events.
- Expanded `glassbox performance budgets` with snapshot, projection health, transcript, event-log, artifact inspection, and payload-size budgets for dashboard render-critical and selected-session payloads.
- Updated [v7-scale-verification-inventory.md](./v7-scale-verification-inventory.md) with measured baseline shape, validation location, and the read-path risk list that feeds GBX-741 through GBX-744.

### GBX-741: Add Paginated Session Read APIs

- Status: `DONE`
- Depends on: `GBX-740`
- Goal: reduce large-session snapshot cost by adding explicit transcript, event, tool-call, metric, and artifact-detail read APIs where full snapshots are too heavy
- Deliverables:
  - backend API contract for paginated transcript reads
  - backend API contract for paginated event-log reads
  - backend API contract for large tool-call, artifact, or metrics detail reads if the baseline identifies those as heavy
  - OpenAPI schema and generated frontend type updates
  - backward-compatible full snapshot behavior for existing clients
  - docs update for API and dashboard development workflows
- Implementation notes:
  - keep canonical event order stable
  - use projection tables or indexed event queries rather than replaying whole sessions for every page
  - avoid breaking static dashboard serving or existing direct session links
- Tests and validation included in task:
  - web API tests for pagination, cursors, ordering, empty pages, and invalid cursors
  - OpenAPI generation and freshness validation
  - frontend typecheck if generated types change
- Done when:
  - large session details can be read incrementally through typed APIs

Completion notes:

- Added typed paginated HTTP endpoints for transcript, event-log, tool-call, turn-metric, and artifact detail reads while keeping the existing full snapshot response backward compatible.
- Extended SQLite read helpers with bounded limit/offset or sequence-cursor reads for transcript, tool-call, turn-metric, and event-log paths.
- Regenerated frontend OpenAPI schema/types and added frontend API client methods for the new typed read pages.
- Added focused integration coverage for ordering, cursor advancement, empty pages, invalid cursors/limits, and missing sessions in `tests/integration/test_web_session_pagination.py`.

### GBX-742: Add Dashboard Virtualization And Lazy Detail Loading

- Status: `DONE`
- Depends on: `GBX-741`
- Goal: keep the dashboard responsive for long transcripts, large event logs, and heavy evidence panes
- Deliverables:
  - virtualized or incrementally rendered transcript and event-log surfaces
  - lazy loading for heavy inspector panes such as events, metrics, evidence, artifacts, lineage compare, or raw diagnostics
  - loading, empty, stale, and retry states for paginated data
  - preserved live-update behavior for current turns without forcing full reloads
  - mobile and keyboard coverage for lazy panes
- Implementation notes:
  - keep operator attention surfaces fast by default
  - do not hide raw evidence permanently; move heavy evidence behind intentional loading boundaries
  - preserve snapshot-plus-SSE semantics for live state
- Tests and validation included in task:
  - frontend unit tests for store and component pagination behavior
  - Playwright coverage for long-session navigation and keyboard workflows
  - frontend lint, typecheck, tests, and build
- Done when:
  - long sessions remain inspectable in the dashboard without rendering the entire history at once

Completion notes:

- Dashboard session loads now hydrate transcript, event-log, and turn-metric detail panes through the GBX-741 paginated APIs and retain per-pane cursor/load/error state.
- Transcript, metrics, and event evidence panes render bounded windows with explicit load-more controls so large sessions do not inflate the initial DOM.
- Store and inspector tests cover initial detail hydration, on-demand page loading, and existing live-stream/session workflows.

### GBX-743: Improve Projection And Artifact Scale Observability

- Status: `DONE`
- Depends on: `GBX-740`
- Goal: make projection lag, rebuild cost, artifact retention, and storage pressure visible before they become confusing runtime failures
- Deliverables:
  - projection health output that includes estimated rebuild scope or progress where practical
  - artifact inspection output that summarizes count, size, age, retention class, and prune candidates
  - optional quota or warning thresholds for local `.glassbox/` growth
  - dashboard or observability cues for stale projections and artifact pressure
  - docs update for larger-session maintenance workflows
- Implementation notes:
  - keep destructive cleanup explicit and dry-run friendly
  - separate canonical event integrity from derived projection staleness
  - avoid automatic deletion unless a later task defines a clear retention policy
- Tests and validation included in task:
  - projection and artifact CLI tests
  - store integration tests for retained artifact metadata
  - observability tests if output changes
- Done when:
  - operators can understand and respond to local storage and projection pressure before it blocks work

Completion notes:

- Projection health now reports estimated rebuild event scope and projected progress ratio through the core model, CLI projection checks, observability status, HTTP session payloads, generated OpenAPI types, and dashboard projection details.
- Artifact inspection/prune reports now include managed file counts, protected/candidate sizes, retention-class counts, artifact age, `.glassbox` total byte pressure, and a configurable `--warning-threshold-mb` storage warning while keeping deletion explicit and dry-run friendly.
- Workspace observability status now includes artifact pressure alongside projection rebuild scope so operators can inspect stale projections and storage pressure from one read-only command.
- Focused projection, artifact GC, observability, dashboard fixture, and large-session baseline tests cover the new metadata and output shape.

### GBX-744: Add Larger-Session Scale Gate Coverage

- Status: `DONE`
- Depends on: `GBX-741`, `GBX-742`, `GBX-743`
- Goal: convert larger-session scale expectations into repeatable automated and manual validation surfaces
- Deliverables:
  - focused larger-session test suite for backend read APIs, projection health, and dashboard state handling
  - frontend performance or scenario smoke for long transcripts and large event logs
  - release-gate or v7-gate stage recommendation for scale coverage
  - docs update explaining scale budgets, residual risks, and operator mitigations
- Implementation notes:
  - keep the gate fast enough for release use
  - use generated fixtures instead of committed bulky artifacts
  - prefer stable budget assertions over machine-specific timing when possible
- Tests and validation included in task:
  - focused scale suite
  - frontend tests for long-session scenarios
  - dry-run release gate update if a gate script changes
- Done when:
  - larger-session behavior is protected by explicit validation rather than hope

Completion notes:

- Added `tests/integration/test_large_session_scale_gate.py` as a focused generated-fixture gate for paginated backend detail APIs, payload budgets, projection rebuild-scope observability, and artifact pressure observability.
- Extended `glassbox performance budgets` with named payload budgets for transcript, event-log, tool-call, turn-metric, and artifact page responses.
- Added a dashboard store scale smoke that hydrates 240 transcript messages, 681 event rows, and 120 metric rows through bounded first pages and load-more flows.
- Documented the v7 scale-gate recommendation, residual risks, and operator mitigations in the scale verification inventory.

---

## Phase 75: Daemon, Live Transport, And Multi-Observer Reliability

### GBX-750: Define v7 Live Transport And Multi-Observer Contract

- Status: `DONE`
- Depends on: `GBX-711`
- Goal: make the expected behavior for multiple dashboard tabs, terminal attach clients, daemon ownership, and lossy live delivery explicit before changing transport code
- Deliverables:
  - docs update defining supported observer count assumptions, sequence cursor semantics, duplicate suppression, stale-owner recovery, and backpressure behavior
  - explicit non-goals for remote collaboration and multi-writer mutation
  - contract for how clients should recover from missed live events, daemon restarts, dashboard refresh, and terminal reconnect
  - test matrix for transport turbulence and daemon lifecycle scenarios
- Implementation notes:
  - preserve the current single mutation owner per workspace
  - keep persisted events authoritative over live delivery
  - distinguish multiple observers from multiple mutating operators
- Tests and validation included in task:
  - docs review against SSE route, TUI client, frontend SSE client, daemon commands, and observability output
- Done when:
  - implementers have a precise v7 live-transport reliability target

Completion notes:

- Added [v7-live-transport-contract.md](./v7-live-transport-contract.md) with the v7 contract for single mutation ownership, multiple read-only observers, sequence cursor semantics, duplicate suppression, backpressure recovery, daemon/stale-owner recovery, terminal and dashboard reconnect behavior, non-goals, and operator guidance.
- Defined a concrete test matrix for historical-plus-live SSE, slow subscribers, frontend SSE turbulence, TUI reconnect states, daemon attach recovery, multi-observer smoke, and observability counters.
- Reviewed the contract against the current SSE route, runtime transport, frontend SSE client, terminal stream consumer, daemon commands, daemon attach path, and observability output.

### GBX-751: Add Transport Turbulence And Recovery Tests

- Status: `DONE`
- Depends on: `GBX-750`
- Goal: strengthen automated coverage for dropped events, reconnect gaps, duplicate live events, slow subscribers, daemon stop, and dashboard refresh behavior
- Deliverables:
  - backend tests for historical-plus-live SSE boundaries under dropped events and duplicate suppression
  - frontend SSE tests for retry exhaustion, resume cursor correctness, terminal events, and invalid frames
  - TUI or interactive client tests for reconnect and stream-unavailable states
  - observability checks for dropped-event counters and subscriber queue depth where practical
- Implementation notes:
  - use fake transports and deterministic event streams where possible
  - avoid sleep-heavy tests; prefer controllable queues and explicit synchronization
  - preserve existing SSE wire contract unless the v7 contract justifies a change
- Tests and validation included in task:
  - focused runtime transport tests
  - web SSE integration tests
  - frontend SSE unit tests
  - TUI client tests if terminal stream handling changes
- Done when:
  - common live transport failures are covered by deterministic tests and recover through persisted events

Completion notes:

- Added backend SSE coverage for duplicate live frames arriving before the next event, preserving sequence-based duplicate suppression while still delivering the newer event.
- Hardened the browser SSE client to ignore duplicate or older sequence frames before dispatching them into dashboard state, and added frontend tests for duplicate suppression plus invalid frame handling without advancing the resume cursor.
- Added TUI stream coverage for terminal session events moving the terminal to historical-only posture after applying the final persisted event.
- Validated focused runtime transport, web SSE, TUI, frontend SSE, typecheck, ruff, and ty checks.

### GBX-752: Harden Daemon Attach And Stale Owner Recovery

- Status: `DONE`
- Depends on: `GBX-750`, `GBX-751`
- Goal: make daemon-backed attach and stale-owner recovery clearer and more reliable under real local process churn
- Deliverables:
  - daemon status output improvements for stale metadata, health failures, occupied ports, and mismatched workspace roots
  - attach behavior improvements for healthy daemon, unhealthy daemon, missing owner file, stale owner file, and conflicting local mutation attempts
  - recovery guidance that points to the next safe command rather than vague failure text
  - retained tests for macOS process-state edge cases and owner-file removal semantics
- Implementation notes:
  - treat `.glassbox/runtime-owner.json` removal as the authoritative local shutdown signal where existing tests require it
  - do not allow hidden concurrent mutation owners
  - keep recovery commands explicit and non-destructive by default
- Tests and validation included in task:
  - daemon runtime integration tests
  - CLI attach and status tests
  - observability tests if output changes
- Done when:
  - daemon attach and stale-owner failures are understandable, recoverable, and protected by tests

Completion notes:

- Added explicit `Next:` recovery guidance to daemon status output for not-running, healthy running, unreachable running, and stale-owner states while preserving existing start/attach/stop command lines.
- Enriched `session attach` failures against unhealthy daemon owners with health inspection, status, and stop/start recovery commands.
- Extended daemon integration assertions for stale metadata cleanup and unreachable health guidance, alongside existing occupied-port and local fallback coverage.
- Validated daemon attach/session command integration tests plus ruff and ty checks.

### GBX-753: Add Multi-Observer Dashboard And Terminal Smoke

- Status: `DONE`
- Depends on: `GBX-751`, `GBX-752`
- Goal: validate that multiple read-only observers can inspect the same session while one local owner remains authoritative for mutation
- Deliverables:
  - integration smoke for multiple SSE subscribers on one session
  - dashboard e2e or component test for multiple tabs or repeated stream creation where practical
  - terminal attach smoke for observer behavior against daemon-owned sessions
  - docs update explaining supported observer behavior and mutation ownership limits
- Implementation notes:
  - do not turn v7 into remote collaboration
  - make operator action attribution visible where events already carry enough information
  - prefer evidence that clients remain consistent after reconnect rather than proving every UI frame
- Tests and validation included in task:
  - web SSE multi-subscriber tests
  - frontend store/SSE lifecycle tests
  - daemon attach smoke
- Done when:
  - multiple observers are a tested local workflow rather than an accidental side effect

Completion notes:

- Added backend SSE smoke proving two simultaneous subscribers on the same session both receive the same next live event through the runtime event transport.
- Added frontend store lifecycle smoke for two repeated session observers sharing the same resume cursor while keeping stream handles and disconnects independent.
- Added daemon-backed terminal observer smoke where `/status` plus `/exit` attaches to a live daemon session without mutating transcript messages.
- Documented supported multi-observer behavior and mutation ownership limits in the persistent runtime guide.
- Validated focused web SSE, daemon runtime, frontend store/SSE, frontend typecheck, ruff, and ty checks.

---

## Phase 76: Repository-Owned Tool-Policy Governance

### GBX-760: Define Tool Policy Governance v2

- Status: `DONE`
- Depends on: `GBX-711`
- Goal: turn current local tool policy behavior into a clearer repository-owned governance contract for teams
- Deliverables:
  - docs update explaining policy manifest shape, rule precedence, invariants, approval modes, default risk levels, blocked actions, and review expectations
  - explicit policy non-goals such as remote enforcement authority, secret storage, and marketplace trust
  - fixture strategy for policy manifests used by tests and examples
  - migration notes if current policy config needs shape changes
- Implementation notes:
  - preserve existing approval semantics unless a task explicitly changes them
  - make invariant blocks such as workspace scope and destructive-command blocking visibly stronger than repo policy rules
  - keep policy explanation friendly for operators, not just implementers
- Tests and validation included in task:
  - docs review against policy engine behavior and current tests
  - no behavior changes required unless the contract exposes a mismatch
- Done when:
  - policy behavior has a clear governance document that implementation tasks can enforce

Completion notes:

- Added the v7 repository governance contract to [tool-policy.md](./tool-policy.md), preserving current manifest version `1` and approval semantics.
- Documented manifest ownership, rule precedence, non-overridable invariants, default risk posture, review expectations, fixture strategy, explicit non-goals, and migration notes.
- Reviewed the contract against `src/glassbox/tools/policy.py`, `src/glassbox/tools/policy_config.py`, and current policy tests; no behavior changes were required.

### GBX-761: Add Policy Explanation And Trace Evidence

- Status: `DONE`
- Depends on: `GBX-760`
- Goal: make tool-policy decisions explainable across CLI, dashboard, event evidence, and replay/eval artifacts
- Deliverables:
  - structured policy trace fields where current event payloads are insufficient
  - CLI and dashboard display updates for policy source kind, source label, risk level, outcome, and reason
  - replay/eval preservation of policy evidence
  - docs update explaining how to inspect why a tool was allowed, approved, denied, or blocked
- Implementation notes:
  - avoid duplicating policy logic in frontend or CLI formatting code
  - keep event payloads serializable and replay-compatible
  - use migrations only if new projection fields are truly needed
- Tests and validation included in task:
  - policy unit tests
  - event serialization and replay tests
  - web/dashboard tests if evidence surfaces change
- Done when:
  - an operator can answer why a tool decision happened from persisted evidence

Completion notes:

- Added a structured `PolicyDecisionTrace` and persisted it on tool request, approval request, and tool execution-start events while preserving the existing flat policy fields for compatibility.
- Added portable `policy_decisions` entries to session exports, reconstructed from canonical events and redacted with the rest of the handoff package.
- Made dashboard approval/action evidence explicit across policy outcome, risk level, source kind/label, and reason; CLI status already includes the same fields for pending approvals and recent tool activity.
- Documented how to inspect policy evidence in CLI status, dashboard actions, session exports, and replay request manifests.

### GBX-762: Add Repository Policy Fixtures And Eval Recommendations

- Status: `DONE`
- Depends on: `GBX-760`, `GBX-761`
- Goal: make policy changes reviewable through fixtures, impact recommendations, and focused verification guidance
- Deliverables:
  - example policy manifests for common local team postures
  - tests covering allow, approve, deny, block, workspace-scope, destructive command, path prefix, cwd prefix, and command prefix behavior
  - `eval recommend` impact-rule updates for policy config and policy engine paths
  - docs explaining recommended validation after policy changes
- Implementation notes:
  - prefer fixtures that are easy to review in code review
  - do not add a plugin marketplace or remote trust system
  - keep examples free of secrets and host-specific paths
- Tests and validation included in task:
  - focused policy tests
  - eval recommendation tests
  - docs review
- Done when:
  - repository policy changes have clear examples and recommended validation scope

Completion notes:

- Added four reviewable example manifests under [examples/tool-policy](./examples/tool-policy): default review posture, docs write allowlist, local command governance, and publish-command deny posture.
- Extended policy unit tests to load those exact example manifests and cover default allow/approve behavior, rule allow, rule deny, approval fallback, workspace-scope blocks, destructive-command blocks, path prefixes, cwd prefixes, and command prefixes.
- Added a `tool-policy-governance` eval impact rule for repository manifests, policy engine/config paths, policy docs, example manifests, and policy tests.
- Added eval recommendation coverage proving policy changes recommend `approval.approved-patch`, and documented the recommended validation commands in [tool-policy.md](./tool-policy.md).

### GBX-763: Improve Policy UX For Approvals And Blocked Actions

- Status: `DONE`
- Depends on: `GBX-761`, `GBX-762`
- Goal: make policy-driven approval and blocked-action states easier to understand and act on in terminal and dashboard workflows
- Deliverables:
  - TUI copy and action hierarchy updates for approval-required, denied, and blocked tool decisions
  - dashboard approval and evidence UI updates that distinguish advisory risk, required approval, denied action, and invariant block
  - tests for action feedback and policy explanation states
  - docs update if user-facing policy language changes
- Implementation notes:
  - do not make approval prompts noisier for safe read-only work
  - preserve keyboard-only action workflows
  - keep detailed evidence available without crowding the default chat surface
- Tests and validation included in task:
  - TUI workflow tests
  - frontend action component tests
  - relevant Playwright workflow if dashboard behavior changes materially
- Done when:
  - policy decisions are clearer at the moment an operator must act

Completion notes:

- Updated TUI approval copy to say `policy approval required`, surface source kind plus label, and make approve/deny the primary action hierarchy while keeping details on `Ctrl+E`.
- Updated TUI details evidence to label allowed advisory risk, policy denies, policy blocks, and invariant blocks distinctly, including the policy reason when present.
- Added dashboard policy evidence labels shared by approval cards, active-tool cards, and compact action summaries so approvals, advisory allow decisions, policy denies, and invariant blocks render differently.
- Documented the user-facing policy labels in [tool-policy.md](./tool-policy.md) and added focused TUI/frontend tests for the new explanation states.

---

## Phase 77: Dashboard Evidence, Comparison, And Analytics Refinement

### GBX-770: Define Dashboard Evidence v7 UX Contract

- Status: `DONE`
- Depends on: `GBX-711`, `GBX-741`
- Goal: define how the dashboard should present branch comparison, metrics, policy evidence, replay/eval evidence, and provider capability evidence for real operator decisions
- Deliverables:
  - dashboard UX contract for comparison, lineage, metrics, evidence, policy trace, provider capability, and release/eval cues
  - priority rules for what belongs in overview versus tabs or lazy panes
  - mobile drill-in and keyboard workflow expectations for heavy evidence surfaces
  - screenshot or scenario matrix updates for v7 dashboard evidence review
- Implementation notes:
  - preserve the attention-first operator console model from v4
  - avoid turning the default dashboard into a raw event dump
  - keep raw evidence reachable when requested
- Tests and validation included in task:
  - docs review against current dashboard components and route state
  - no production code changes required unless small mismatches are found
- Done when:
  - dashboard evidence improvements have a specific UX target and validation matrix

Completion notes:

- Added [dashboard-evidence-v7.md](./dashboard-evidence-v7.md) with the v7 UX target for branch comparison, lineage, metrics, policy trace evidence, replay/eval evidence, provider capability evidence, and release/eval cues.
- Defined priority rules for what belongs in overview versus transcript, timeline, actions, lineage, compare, runtime, evidence, events, and metrics tabs.
- Captured mobile drill-in and keyboard workflow expectations for heavy evidence surfaces without changing production code.
- Added a scenario matrix for v7 dashboard evidence review and called out follow-on gaps for GBX-771, GBX-772, and GBX-773.

### GBX-771: Expand Branch Compare And Lineage Analysis

- Status: `DONE`
- Depends on: `GBX-770`
- Goal: help operators understand what changed across forked sessions and why a branch differs from its parent
- Deliverables:
  - improved compare model for branch metadata, inherited transcript, post-fork messages, tool activity, status, metrics, and policy outcomes
  - dashboard compare UI for side-by-side or aligned branch differences
  - backend query updates if current snapshots do not expose enough lineage detail efficiently
  - tests for compare state, route behavior, and branch navigation
- Implementation notes:
  - keep parent history immutable and child sessions canonical
  - avoid expensive full-session comparison on initial dashboard load
  - respect paginated read APIs if introduced earlier
- Tests and validation included in task:
  - backend session query tests if APIs change
  - frontend compare and routing tests
  - Playwright lineage workflow coverage if behavior changes materially
- Done when:
  - branch comparison explains meaningful session differences without requiring raw event inspection

Completion notes:

- Expanded the dashboard Compare pane to build an explicit compare analysis from the selected and compared snapshots without adding initial-load backend cost.
- Added aligned sections for branch metadata, transcript divergence, tool activity, policy outcomes, runtime/projection state, and metric deltas.
- Kept route behavior and lineage compare/open actions unchanged while making selected compare targets more explainable from persisted snapshots.
- Updated frontend inspector tests to cover the richer compare evidence, shared/current-only/compared-only transcript analysis, policy totals, route links, and session-state normalization.

### GBX-772: Add Turn Metrics And Latency Analytics

- Status: `DONE`
- Depends on: `GBX-770`, `GBX-740`
- Goal: make turn duration, model call latency, token counts, tool execution time, cancellation timing, and failure patterns easier to inspect across one session and the workspace queue
- Deliverables:
  - backend metric read models or query helpers if current projections are insufficient
  - dashboard metrics panes or charts for session-level and workspace-level patterns
  - operator copy that distinguishes slow provider calls, slow tools, waiting-for-approval time, and replay/eval drift
  - tests for metric normalization and rendering
- Implementation notes:
  - do not require external analytics services
  - keep metrics derived from persisted events and projections
  - avoid making advisory metrics look like hard failures unless thresholds are explicit
- Tests and validation included in task:
  - runtime metrics projection tests
  - frontend metrics component tests
  - dashboard e2e if charts or workflow navigation change materially
- Done when:
  - operators can identify slow or costly turns from local evidence

Completion notes:

- Added session-level latency analysis to the dashboard Metrics pane using retained turn metrics, with neutral observed-value copy instead of undocumented failure thresholds.
- Distinguished provider latency, tool execution latency, token cost, failed-tool patterns, approval/answer waits, and replay/eval drift context.
- Added a workspace metric-pattern snapshot to the queue overview using aggregate rows for visible queue timing, action waits, failure patterns, and projection pressure.
- Kept the implementation frontend-only because existing projections and paginated metric APIs already expose the needed local evidence for this refinement.

### GBX-773: Integrate Policy, Eval, And Provider Evidence Cues

- Status: `DONE`
- Depends on: `GBX-733`, `GBX-761`, `GBX-770`
- Goal: connect policy traces, deterministic eval coverage, and advisory provider capability evidence into dashboard cues that guide operator judgment
- Deliverables:
  - dashboard evidence cues for policy decision source, eval coverage relevance, replay drift, provider canary status, and release evidence freshness where available
  - backend or frontend normalization updates for retained evidence pointers
  - tests for cue severity, stale evidence, missing evidence, and advisory-versus-blocking labels
  - docs update explaining how to interpret evidence cues
- Implementation notes:
  - keep cue language careful; advisory provider evidence must not look like deterministic signoff
  - avoid overwhelming the overview with release engineering detail
  - route deeper evidence to intentional inspector tabs
- Tests and validation included in task:
  - frontend verification cue tests
  - backend query tests if evidence pointers change
  - screenshot archive update if visual hierarchy changes materially
- Done when:
  - the dashboard helps operators distinguish runtime state, deterministic evidence, advisory evidence, and policy risk

Completion notes:

- Expanded dashboard verification cues to classify policy decision source, eval coverage relevance, replay drift, provider canary status, and release evidence freshness from retained snapshot/artifact evidence.
- Kept provider canary evidence advisory even when retained artifacts report provider failures, so live-provider compatibility does not look like deterministic release signoff.
- Added focused verification-cue tests for cue severity, missing evidence, stale release evidence, and advisory-versus-blocking provider labels.
- Updated dashboard docs to explain cue interpretation and the CLI commands operators should use for deeper evidence.

---

## Phase 78: Accessibility, Onboarding, Packaging, And v7 Release Signoff

### GBX-780: Add Named Accessibility Pairing Reviews

- Status: `DONE`
- Depends on: `GBX-770`, `GBX-753`
- Goal: move beyond broad manual accessibility review into named terminal, browser, and assistive-technology pairings before making stronger claims
- Deliverables:
  - terminal accessibility review for named terminal emulator, OS, size, keyboard, and screen-reader or accessibility-tool pairing where feasible
  - dashboard accessibility review for named browser, OS, viewport, keyboard, and screen-reader pairing where feasible
  - retained manual evidence template with claims, non-claims, blockers, and follow-up issues
  - docs update narrowing or expanding accessibility claims based on evidence
- Implementation notes:
  - keep claims precise and evidence-backed
  - do not claim broad certification from limited review
  - fix blocking keyboard or semantic issues discovered during review before marking done
- Tests and validation included in task:
  - frontend accessibility-oriented tests where practical
  - TUI keyboard workflow tests
  - manual review artifacts retained locally
- Done when:
  - v7 accessibility claims name the pairings actually reviewed and no blocking issue remains open

Completion notes:

- Added [terminal-accessibility-review-v7.md](./terminal-accessibility-review-v7.md) naming the reviewed terminal/OS/keyboard pairings and keeping unexecuted screen-reader pairings as non-claims.
- Added [dashboard-accessibility-review-v7.md](./dashboard-accessibility-review-v7.md) naming the reviewed Chromium/Playwright dashboard pairings, mobile/keyboard workflows, evidence-cue semantics, and screen-reader non-claims.
- Added [manual-qa-evidence-v7.md](./manual-qa-evidence-v7.md) with the v7 manual evidence template for accessibility pairings, onboarding, packaging, recovery, provider canaries, attachments, and redaction.
- Added an accessible label for the dashboard Evidence interpretation cue region and covered it in the focused verification-cue test.

### GBX-781: Improve First-Run Provider And Profile Onboarding

- Status: `DONE`
- Depends on: `GBX-731`
- Goal: make the first successful local session easier for new users without weakening local-first or secret-handling boundaries
- Deliverables:
  - first-run guide or command output that points users through provider diagnostics, model selection, workspace profile defaults, dashboard URL, and validation commands
  - example `glassbox.profile.json` snippets for common local workflows
  - clearer missing-provider and unsupported-provider messages in terminal, dashboard, and provider diagnostics where appropriate
  - docs update in getting started, providers, and workspace profiles
- Implementation notes:
  - do not store secrets in repository-owned profile files
  - keep source-builder and installed-package paths distinct where needed
  - avoid turning first-run into an interactive wizard unless a later task justifies it
- Tests and validation included in task:
  - CLI diagnostics tests
  - docs review
  - installed-package smoke if startup behavior changes
- Done when:
  - a new local user can discover the minimum provider and profile setup path without reading task docs

Completion notes:

- Provider diagnostics now emits a redacted first-run checklist covering provider diagnostics, model selection, `glassbox.profile.json`, the paired dashboard URL, and the `commit-smoke` validation path.
- Provider diagnostics JSON includes `onboarding_steps` for installed-package smoke and scripted setup checks.
- Provider runtime failures now include actionable missing-credential, unsupported-provider, and invalid-base-URL remediation text that surfaces in terminal and dashboard failure state without exposing secrets.
- Updated [getting-started.md](./getting-started.md), [providers.md](./providers.md), and [workspace-profiles.md](./workspace-profiles.md) with first-run diagnostics commands, profile examples, and clearer provider troubleshooting.

### GBX-782: Harden Installed Package And Source Builder Onboarding

- Status: `DONE`
- Depends on: `GBX-781`, `GBX-744`
- Goal: reduce setup friction and packaging surprises for installed-package users and source builders
- Deliverables:
  - package smoke updates for first-run help, provider diagnostics, dashboard static serving, daemon lifecycle, eval profile listing, and profile examples
  - source-builder docs for Python, uv, pnpm, frontend static assets, generated API types, and release asset validation
  - package content validation updates if new docs, examples, or static assets must ship
  - clean-environment smoke evidence retained under the v7 release path
- Implementation notes:
  - runtime users should not need Node.js
  - source builders should get clear errors when frontend assets or generated API types are stale
  - keep package validation deterministic and scriptable
- Tests and validation included in task:
  - package contents validation
  - installed-wheel smoke
  - frontend build and static asset validation if packaged dashboard changes
- Done when:
  - installed users and source builders have tested, documented setup paths

Completion notes:

- Expanded installed-wheel smoke with first-run provider diagnostics, provider diagnostics against an example `glassbox.profile.json`, and eval profile listing alongside the existing terminal, dashboard, daemon, and deterministic eval checks.
- Package content validation now requires the first-run/provider/profile/manual-evidence docs that source builders and release reviewers need in sdists.
- Updated [release-packaging.md](./release-packaging.md), [v6-release-gate.md](./v6-release-gate.md), and [v7-scale-verification-inventory.md](./v7-scale-verification-inventory.md) to separate installed-user expectations from source-builder requirements and to name the v7 clean-environment evidence path.

### GBX-783: Add The v7 Release Gate Or Extend The v6 Gate

- Status: `DONE`
- Depends on: `GBX-724`, `GBX-744`, `GBX-753`, `GBX-763`, `GBX-773`, `GBX-782`
- Goal: provide one canonical automated gate for v7 release-candidate validation, either by extending the v6 gate or adding a v7-specific script
- Deliverables:
  - release-gate command that includes v6 coverage plus v7 deterministic eval, scale, transport, daemon, policy, dashboard, onboarding, package, and evidence stages
  - dry-run output and structured evidence summary for v7 stages
  - advisory provider canary handling that writes matrix evidence without becoming a hidden blocker
  - tests that keep the gate script aligned with v7 gate documentation
  - docs update for pass/fail policy, residual risks, manual evidence, and retained artifact paths
- Implementation notes:
  - reuse the v6 gate where practical instead of duplicating subprocess logic
  - keep the default gate deterministic and usable in clean checkouts
  - make skipped advisory checks visible
  - keep installed-package smoke free of Node.js requirements
- Tests and validation included in task:
  - gate unit tests
  - dry-run validation
  - focused script validation
- Done when:
  - v7 has one objective automated release-candidate gate with retained evidence

Completion notes:

- Added `scripts/validate_v7_release_gate.py`, which reuses the v6 deterministic/package/installed-smoke stages and adds v7 release-profile eval, v7 workflow advisory eval, performance budget, provider diagnostics onboarding, dashboard evidence cue, and evidence-doc validation stages.
- The v7 gate writes `.glassbox/releases/...-v7-gate/summary.json` for dry runs and real runs, with v7 manual/accessibility evidence hints and explicit advisory provider-canary records.
- Provider canaries remain visible but non-blocking by default; `--include-provider-canaries` writes retained matrix evidence under the selected v7 evidence directory.
- Added [v7-release-gate.md](./v7-release-gate.md) and focused gate tests covering dry-run output, summary shape, stage/doc alignment, and advisory policy.

### GBX-784: Run Manual v7 Release Candidate Validation

- Status: `TODO`
- Depends on: `GBX-780`, `GBX-783`
- Goal: complete manual validation for workflows automated tests cannot fully prove and record evidence in the v7 release directory
- Deliverables:
  - manual terminal UX evidence for long sessions, approvals, questions, cancellation, daemon attach, and fallback
  - manual dashboard evidence for long sessions, compare, metrics, policy evidence, provider cues, mobile, and keyboard workflows
  - manual provider canary evidence or explicit credential-unavailable skips
  - manual recovery and maintenance evidence for projection, artifacts, backup, daemon, eval, and installed dashboard workflows
  - final blocking issue list and residual risk list
- Implementation notes:
  - tie manual results to the same evidence directory as the automated v7 gate output
  - fix blocking defects discovered during manual validation before marking done
  - record skipped provider canaries explicitly
- Tests and validation included in task:
  - manual checklist from the v7 release gate
  - focused automated reruns for any area fixed during manual validation
- Done when:
  - manual release evidence exists and no blocking manual validation issue remains open

### GBX-785: Publish The v7 Release Candidate Guide And Decision

- Status: `TODO`
- Depends on: `GBX-783`, `GBX-784`
- Goal: package the v7 operating model, validation path, known gaps, non-goals, and final go/no-go decision into one operator-facing guide
- Deliverables:
  - `v7-release-candidate.md` or equivalent operator-facing release guide
  - supported operating model summary for scale, eval portfolio, provider capability matrix, daemon/transport reliability, policy governance, dashboard evidence, accessibility, onboarding, packaging, and release evidence
  - release-readiness checklist with links to automated and manual evidence expectations
  - final pass/fail state for automated gate, manual validation, provider canary policy, package smoke, daemon smoke, scale smoke, accessibility review, and residual risk review
  - explicit non-goals and residual known gaps
  - docs hub and root README updates if appropriate
- Implementation notes:
  - mirror the clarity of [v6-release-candidate.md](./v6-release-candidate.md) while reflecting the v7 product surface
  - do not require users to read task docs to understand the supported model
  - if the decision is no-go, record the blocker list and next recommended task order
- Tests and validation included in task:
  - docs review against command help, release gate output, retained evidence, and known residual risks
  - release-candidate documentation guardrails if present
- Done when:
  - the repo records a clear go/no-go v7 release-candidate decision with supporting evidence

---

## Recommended Build Order For The First v7 Adoption Slice

If an agent wants the fastest path to a demonstrable v7 improvement, the recommended order is:

1. `GBX-710` and `GBX-711`
2. `GBX-720` and `GBX-721`
3. `GBX-730` and `GBX-731`
4. `GBX-740` before any read-path API work
5. `GBX-750` and `GBX-751`
6. `GBX-760` before policy behavior changes
7. `GBX-770` before dashboard evidence UI work
8. `GBX-781` for early onboarding payoff
9. `GBX-783` only after the new validation surfaces are stable
