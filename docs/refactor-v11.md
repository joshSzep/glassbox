# Glassbox Refactor v11 Tasks

For the docs hub and operator guides, start at [README.md](./README.md). This
file is the next behavior-preserving refactor roadmap after
[refactor-v10.md](./refactor-v10.md). It focuses on the code paths that grew
while the v11 confidence-and-adoption milestone closed residual risks, added
knowledge posture, improved branch-search decision support, expanded
verification recommendations, and polished reviewer handoff.

## Purpose

This document defines a v11 refactor roadmap for the current Glassbox codebase.

It follows the same execution style as [refactor-v1.md](./refactor-v1.md),
[refactor-v8.md](./refactor-v8.md), and [refactor-v10.md](./refactor-v10.md):
explicit dependencies, small vertical slices, concrete deliverables, and
validation requirements attached directly to the work.

This roadmap is not a product-feature roadmap. It exists to keep the current
local-first, event-sourced architecture easy to evolve by:

- separating v11 confidence logic from presentation and command formatting
- keeping verification recommendation, knowledge posture, branch-search,
  handoff, and release-evidence behavior independently reviewable
- preserving current CLI, TUI, dashboard, replay, eval, HTTP, projection, and
  package behavior unless a later task explicitly changes a contract
- tightening architecture guardrails around the modules that grew after the
  v10 second-order refactor
- avoiding line-count-only splits in model-heavy or public compatibility
  surfaces

## Refactor Direction

The v10 refactor successfully split the second-order pressure points under the
post-v8 autonomy architecture. The v11 implementation then added confidence and
adoption behavior on top of those improved seams.

The new pressure is concentrated in modules that are coherent but broad:

- session export and handoff code now owns redaction, package shape, lineage,
  knowledge posture, checkpoints, compactions, verification, and safe commands
- eval recommendation output now owns daily-development surfaces, long-run
  surfaces, release-gate guidance, recipes, execution planning, and terminal
  formatting
- knowledge posture now combines cue derivation, ranking, provenance, command
  guidance, and observability-facing summaries
- branch decision support now combines candidate evidence, verification
  recommendation, cost, risk, accepted-risk, and follow-up derivation
- CLI status and command-guide surfaces now carry richer recovery, knowledge,
  provider, task, checkpoint, compaction, and workflow guidance
- frontend knowledge and branch-search sections now render denser v11 evidence
  than the original post-v8 component split anticipated
- tool-attempt, compaction, turn-event, and session-query helpers now contain
  richer recovery and evidence-shaping logic
- store projection modules for tasks, background jobs, and long-run evidence are
  still rebuildable and coherent, but each new release cue adds review pressure

The v11 refactor thesis is:

- keep canonical events and managed artifacts as the source of truth
- keep projection tables rebuildable and non-authoritative
- keep runtime query services transport-agnostic
- keep web response models and frontend generated API types as transport
  contracts, not business-logic owners
- move derivation, ranking, formatting, redaction, and command-guidance logic
  into focused modules before adding more v12 behavior
- preserve compatibility facades where imports, routes, commands, or component
  entrypoints rely on them
- add guardrails only when the intended repair is obvious and local

## Agent Execution Rules

These rules apply to every task in this file.

1. Respect dependency order. Do not start a task until its dependencies are
   complete unless the task explicitly says it can proceed in parallel.
2. Preserve current behavior by default. Refactor tasks should not intentionally
   change CLI semantics, dashboard workflows, API payloads, replay outcomes,
   eval outcomes, event ordering, projection behavior, package contents, or
   release-gate behavior unless the task explicitly includes that contract
   change.
3. Treat `events` as the canonical source of truth. Query services, route
   helpers, stores, frontend derivation, and UI projections remain derived from
   canonical events, typed API responses, managed artifacts, or rebuildable
   projection tables.
4. Repair architectural duplication before splitting files mechanically. If two
   modules shape the same evidence or command guidance, extract the shared
   boundary first.
5. Prefer extractions with thin compatibility shims over broad rewrites. Keep
   diffs incremental and executable.
6. Keep public facades stable unless a task explicitly changes the import,
   route, API, command, or component contract.
7. Do not introduce new framework layers unless they remove a real current
   coupling in the codebase.
8. Do not move API calls into React components. Frontend stores own transport;
   components own presentation and local interaction state; pure helper modules
   own derivation and formatting.
9. Do not move HTTP response models or FastAPI dependencies into runtime query
   services. Runtime query services stay transport-agnostic.
10. Every refactor task automatically includes:
    - automated tests for moved or extracted behavior where practical
    - `ruff` formatting and lint compliance for touched Python code
    - `ty` typecheck compliance for touched Python code
    - focused `pytest` coverage for touched runtime, store, CLI, web, replay,
      eval, provider, tool-policy, task, knowledge, branch-search, handoff,
      projection, and release-gate behavior
    - frontend lint, typecheck, tests, and build when the task touches
      dashboard code, generated API types, packaged static assets, or route
      assumptions
    - documentation updates when public module boundaries, architecture
      references, import surfaces, API payloads, command behavior, package
      contents, or operator-visible outputs change materially

## Completion Contract For Any Task

A task is complete only when all of the following are true:

- the implementation exists in the intended module boundary
- automated tests covering the touched behavior exist and pass
- lint, formatting, and type checks pass for the touched slice
- compatibility shims, if any, are justified explicitly or tracked by a
  follow-up task in this file
- docs are updated if the refactor changes documented architecture, import
  surfaces, API payloads, command behavior, or operator-visible outputs
- deterministic replay/eval behavior remains stable or intentional drift is
  handled through the established baseline-refresh workflow
- the refactor does not weaken the local-first, event-sourced, replay-aware
  architecture described in [architecture.md](./architecture.md)

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
src/glassbox/
    cli/
    core/
    runtime/
    services/
    store/
    tools/
    web/
frontend/
tests/
evals/
docs/
scripts/
```

## Recommended Validation Commands

Use the narrowest viable validation after each task, but the baseline validation
pattern for completed work should be:

```bash
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run pytest
pnpm --dir frontend lint
pnpm --dir frontend typecheck
pnpm --dir frontend test
pnpm --dir frontend build
uv run python scripts/validate_v11_release_gate.py --dry-run
```

During incremental refactor work, use narrower commands when possible:

```bash
uv run pytest tests/unit/test_specific_module.py
uv run pytest tests/integration/test_specific_flow.py
uv run ruff check src/glassbox/path.py tests/path_test.py
uv run ty check src/glassbox/path.py
pnpm --dir frontend test -- knowledge-autonomy-console.test.tsx
pnpm --dir frontend typecheck
```

## Current State

The v11 release-candidate track closed the v10 residual risks and added several
confidence surfaces:

- release-path verification recommendations and declarative verification recipes
- friendly compaction over-range guidance and checkpoint absence reasons
- live cockpit evidence protocol, retained browser evidence, and named
  accessibility pairings
- deterministic provider failure fixtures and optional advisory canary evidence
- workflow-oriented command guidance, readiness remediation, and safer status
  summaries
- unified workspace knowledge posture with provenance drill-down
- branch-search decision support with candidate verification recommendations
- reviewer-safe handoff summaries and evidence-bundle guidance
- the v11 release gate and release-candidate guide for package version `0.10.0`

The implementation is coherent, but v11 concentrated new derivation and
formatting pressure in a handful of places. The next refactor should keep those
new contracts dependable before another product milestone expands them.

Current pressure points include:

- `src/glassbox/runtime/session_export.py`
- `src/glassbox/runtime/eval_recommendation_output.py`
- `src/glassbox/runtime/eval_recommendation_engine.py`
- `src/glassbox/runtime/knowledge_posture.py`
- `src/glassbox/runtime/branch_decision_support.py`
- `src/glassbox/runtime/tool_attempt_recovery.py`
- `src/glassbox/runtime/context_compaction_service.py`
- `src/glassbox/runtime/session_query_service.py`
- `src/glassbox/runtime/session_query_helpers.py`
- `src/glassbox/runtime/turn_event_recorder.py`
- `src/glassbox/runtime/turn_tool_executor.py`
- `src/glassbox/cli/status_formatters.py`
- `src/glassbox/cli/command_guide.py`
- `src/glassbox/cli/interactive_commands.py`
- `src/glassbox/cli/parser_sessions.py`
- `src/glassbox/store/sqlite_projection_tasks.py`
- `src/glassbox/store/sqlite_background_jobs.py`
- `src/glassbox/services/contracts.py`
- `frontend/components/console/knowledge-autonomy-sections.tsx`
- `frontend/components/console/branch-search-sections.tsx`
- `frontend/stores/session-store.ts`

Large files that are primarily model-heavy, generated, or test fixtures are not
automatically refactor targets. In particular, `core/events.py`,
`core/models.py`, generated frontend API types, and broad test files should be
split only when a real ownership or review problem appears.

## Milestone Map

The intended v11 refactor milestone order is:

1. v11 boundary refresh and guardrails
2. evidence recommendation and release-output decomposition
3. knowledge posture and branch-search decision decomposition
4. handoff, export, and redaction decomposition
5. CLI and frontend operator-surface decomposition
6. runtime recovery and projection boundary cleanup
7. documentation and validation closeout

Each phase below corresponds to one concrete refactor milestone.

## Task Graph

---

## Phase 70: V11 Boundary Refresh

### GBX-R400: Define V11 Confidence Refactor Boundary Map

- Status: `DONE`
- Depends on: `GBX-R351`
- Goal: update the refactor boundary map for post-v11 confidence, evidence,
  handoff, knowledge, and branch-search surfaces before moving code again
- Deliverables:
  - update [refactor-boundaries.md](./refactor-boundaries.md) with target
    boundaries for eval recommendation output, knowledge posture, branch
    decision support, session export/handoff, status formatting, command guide,
    frontend knowledge/branch sections, tool-attempt recovery, compaction
    guidance, and projection domains
  - identify which large files are model-heavy or generated and acceptable
    versus mixed derivation/coordinator modules that should be split
  - explicit non-goals so v11 refactor work does not become new verification,
    knowledge, provider, branch-search, handoff, release-gate, or dashboard
    behavior
  - notes on which compatibility facades should remain stable and which
    internal modules should become new ownership targets
- Implementation notes:
  - ground the boundary map in current code paths, tests, release docs, and
    v11 dogfooding evidence
  - keep current route payloads, component entrypoints, command output,
    release-gate summaries, and projection semantics stable
  - do not make line count alone the reason for a split
- Tests and validation included in task:
  - docs review against current `runtime`, `cli`, `web`, `store`,
    `frontend`, `scripts`, and `evals` implementation
  - manual verification that later tasks in this file map cleanly onto the
    updated boundary map
- Done when:
  - the repo has a code-aligned v11 boundary map that later tasks can follow
    without reopening architectural scope repeatedly

### GBX-R401: Extend Architecture Guardrails For V11 Pressure Points

- Status: `DONE`
- Depends on: `GBX-R400`
- Goal: prevent v11 confidence modules from growing into new hidden monoliths
- Deliverables:
  - guardrails in
    [test_architecture_guardrails.py](../tests/unit/test_architecture_guardrails.py)
    for new v11 facades and extracted ownership modules
  - Python size or import-direction checks for recommendation output,
    knowledge posture, branch decision support, session export helpers, status
    formatting helpers, and recovery helper boundaries where practical
  - frontend size or import checks for knowledge and branch-search sections,
    plus session-store stream/action boundaries where practical
  - clear guardrail messages that name the intended destination module
- Implementation notes:
  - avoid brittle caps on generated files, model-only files, release fixtures,
    and intentionally broad public contracts
  - prefer dependency-direction and facade-thinness checks over arbitrary
    complexity metrics
  - make every guardrail failure locally repairable
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_architecture_guardrails.py`
  - focused tests proving new guardrail messages are actionable
- Done when:
  - v11 refactor-sensitive boundaries have lightweight enforcement before bulk
    movement begins

---

## Phase 71: Recommendation And Release Evidence Decomposition

### GBX-R410: Split Eval Recommendation Output Into Surface, Plan, Recipe, And Formatter Modules

- Status: `DONE`
- Depends on: `GBX-R400`
- Goal: reduce
  [eval_recommendation_output.py](../src/glassbox/runtime/eval_recommendation_output.py)
  by separating recommendation surface derivation from terminal/JSON
  formatting and executable plan construction
- Deliverables:
  - daily-development surface derivation for commit-time, push-time,
    release-candidate, and advisory rows in a focused module
  - long-run surface derivation for immediate, checkpoint, pre-resume,
    pre-merge, and release-candidate rows in a focused module
  - verification-plan and skipped-check construction in a focused module
  - recipe rendering and release-gate command grouping in a focused module
  - terminal formatting kept separate from JSON model construction
  - stable public CLI behavior and JSON payloads
- Implementation notes:
  - preserve recommendation confidence taxonomy, reason groups, cheapest-next
    command wording, skipped live-provider posture, and release-gate command
    behavior
  - keep recipe commands advisory unless the existing execution path explicitly
    runs deterministic eval cases or profiles
  - avoid moving CLI-only formatting into the recommendation engine
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_eval_recommendations.py`
  - `uv run pytest tests/integration/test_cli_eval_commands.py`
  - focused formatter tests for terminal and JSON compatibility
  - `uv run ty check src/glassbox/runtime/eval_recommendation_output.py`
- Done when:
  - recommendation behavior remains stable while surfaces, recipes, execution
    plans, and terminal formatting are independently owned

### GBX-R411: Split Eval Recommendation Engine Matching From Release And Capability Expansion

- Status: `DONE`
- Depends on: `GBX-R410`
- Goal: keep
  [eval_recommendation_engine.py](../src/glassbox/runtime/eval_recommendation_engine.py)
  focused on orchestration by moving path matching, capability expansion,
  profile/stage expansion, and release-gate recommendation into owned helpers
- Deliverables:
  - path-impact matching remains in or near the existing matching boundary
  - capability and owner expansion helpers separated from profile/stage
    expansion helpers
  - release-gate command recommendation helper separated from ordinary eval
    profile recommendation
  - fallback-policy helper that clearly labels manual guidance
  - compact engine facade that wires the helpers and preserves current output
- Implementation notes:
  - preserve direct, owner-derived, capability-derived, stage-derived, and
    fallback confidence behavior
  - keep live-provider canary recommendations advisory and opt-in
  - avoid making release-gate commands appear as executable eval profiles
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_eval_recommendations.py`
  - `uv run pytest tests/integration/test_cli_eval_commands.py`
  - `uv run glassbox eval recommend scripts/validate_v11_release_gate.py --json --cwd .`
- Done when:
  - recommendation expansion can evolve by concern without widening the engine
    coordinator

### GBX-R412: Split Release Gate Summary Helpers From Validation Script Orchestration

- Status: `DONE`
- Depends on: `GBX-R410`
- Goal: keep
  [validate_v11_release_gate.py](../scripts/validate_v11_release_gate.py)
  scriptable while moving reusable stage summaries, advisory-provider rows, and
  retained evidence rendering into focused helpers
- Deliverables:
  - stage-result and summary-writing helpers that can be tested without running
    the whole gate
  - advisory provider evidence summary helpers that stay separate from
    deterministic blocking stage helpers
  - dry-run planning output kept behavior-compatible
  - package/version/eval/coverage stage orchestration still easy to read in the
    script entrypoint
- Implementation notes:
  - do not make live provider evidence blocking
  - preserve evidence directory layout and `summary.json` shape
  - keep the script usable as a standalone release command
- Tests and validation included in task:
  - release-gate unit tests
  - `uv run python scripts/validate_v11_release_gate.py --dry-run`
  - package contents validation if helper files become shipped assets
- Done when:
  - the release gate remains one operator command while its summary and stage
    shaping are testable outside a full gate run

---

## Phase 72: Knowledge And Branch Decision Decomposition

### GBX-R420: Split Knowledge Posture Into Cue Collection, Ranking, Provenance, And Guidance Modules

- Status: `DONE`
- Depends on: `GBX-R400`
- Goal: reduce
  [knowledge_posture.py](../src/glassbox/runtime/knowledge_posture.py) by
  separating source-specific cue collection, aggregate ranking, provenance
  construction, and safe-command guidance
- Deliverables:
  - source collectors for workspace memory, repository index, checkpoints,
    compactions, verification, provider evidence, and active sessions
  - ranking/aggregate status helper that owns freshness precedence
  - provenance-reference helper that owns bounded evidence references and
    redaction assumptions
  - command-guidance helper that maps cue states to safe inspection commands
  - stable observability/API/dashboard payload shape
- Implementation notes:
  - do not create a new hidden knowledge store
  - keep provider evidence advisory
  - keep canonical events, projection rows, artifacts, and existing retained
    evidence as the only sources
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_knowledge_posture.py`
  - `uv run pytest tests/integration/test_observability_status.py`
  - frontend tests if cue payload assumptions change
- Done when:
  - knowledge posture remains behavior-compatible while each cue family and
    aggregate decision is independently testable
- Completed notes:
  - `knowledge_posture.py` is now a compatibility facade over focused source,
    cue, provenance, guidance, ranking, and model helpers.
  - Guardrails now cap the facade and new helper modules so future posture
    behavior lands in the intended owner.
  - Validation: `uv run pytest tests/unit/test_knowledge_posture.py`,
    `uv run pytest tests/unit/test_architecture_guardrails.py`,
    `uv run pytest tests/integration/test_observability_status.py`,
    `uv run ruff format --check src/glassbox/runtime/knowledge_posture*.py tests/unit/test_architecture_guardrails.py tests/unit/test_knowledge_posture.py`,
    `uv run ruff check src/glassbox/runtime/knowledge_posture*.py tests/unit/test_architecture_guardrails.py tests/unit/test_knowledge_posture.py`,
    and `uv run ty check src/glassbox/runtime/knowledge_posture.py src/glassbox/runtime/knowledge_posture_sources.py src/glassbox/runtime/knowledge_posture_cues.py src/glassbox/runtime/knowledge_posture_provenance.py src/glassbox/runtime/knowledge_posture_guidance.py src/glassbox/runtime/knowledge_posture_ranking.py src/glassbox/runtime/knowledge_posture_models.py`.

### GBX-R421: Split Branch Decision Support Into Evidence, Verification, Cost, Risk, And Follow-Up Helpers

- Status: `DONE`
- Depends on: `GBX-R400`
- Goal: reduce
  [branch_decision_support.py](../src/glassbox/runtime/branch_decision_support.py)
  by extracting each candidate-scoring dimension behind branch-search decision
  support
- Deliverables:
  - retained evidence extraction helper for candidate/session/verification/
    artifact/selection records
  - changed-file and missing-diff-evidence helper
  - verification recommendation helper that delegates to eval recommendation
    rules without duplicating them
  - cost-estimate and risk-posture helpers
  - accepted-risk and follow-up-action helpers
  - stable CLI/API/dashboard decision-support payloads
- Implementation notes:
  - preserve the explicit non-goal that branch search never merges or mutates
    parent history automatically
  - do not infer changed files from unavailable state
  - keep recommendation commands explainable and bounded
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_branch_search.py`
  - `uv run pytest tests/integration/test_cli_branch_search_commands.py`
  - `uv run pytest tests/integration/test_web_branch_search_routes.py`
  - frontend branch-search console tests if rendering assumptions change
- Done when:
  - candidate decision support remains stable while evidence, verification,
    cost, risk, and follow-up logic are separately owned
- Completed notes:
  - `branch_decision_support.py` is now a compatibility facade over focused
    evidence, changed-file, verification, cost, risk, follow-up, and model
    helpers.
  - Guardrails now cap the facade and helper modules so branch decision-support
    expansion lands in the intended owner.
  - Validation: `uv run pytest tests/unit/test_branch_search.py`,
    `uv run pytest tests/unit/test_architecture_guardrails.py`,
    `uv run pytest tests/integration/test_cli_branch_search_commands.py`,
    `uv run pytest tests/integration/test_web_branch_search_routes.py`,
    `uv run ruff format --check src/glassbox/runtime/branch_decision*.py tests/unit/test_architecture_guardrails.py tests/unit/test_branch_search.py`,
    `uv run ruff check src/glassbox/runtime/branch_decision*.py tests/unit/test_architecture_guardrails.py tests/unit/test_branch_search.py`,
    and `uv run ty check src/glassbox/runtime/branch_decision_support.py src/glassbox/runtime/branch_decision_models.py src/glassbox/runtime/branch_decision_evidence.py src/glassbox/runtime/branch_decision_files.py src/glassbox/runtime/branch_decision_verification.py src/glassbox/runtime/branch_decision_cost.py src/glassbox/runtime/branch_decision_risk.py src/glassbox/runtime/branch_decision_followup.py`.

### GBX-R422: Split Frontend Knowledge And Branch Sections Into Summary, Detail, Action, And Evidence Modules

- Status: `DONE`
- Depends on: `GBX-R420`, `GBX-R421`
- Goal: reduce frontend v11 evidence sections by moving dense knowledge and
  branch-search rendering into focused section families
- Deliverables:
  - knowledge posture summary, memory list, repository index, provenance, and
    action-control sections in owned modules
  - branch-search candidate list, candidate decision card, evidence details,
    verification recommendation, and action-control sections in owned modules
  - pure formatting helpers for cue labels, risk/cost labels, and provenance
    summaries
  - stable exports from existing section entrypoints during migration
- Implementation notes:
  - keep API calls in stores, not components
  - preserve current labels, disabled states, routes, and action confirmations
    unless a later task explicitly changes UX
  - do not duplicate backend branch/knowledge derivation in React components
- Tests and validation included in task:
  - `pnpm --dir frontend test -- knowledge-autonomy-console.test.tsx`
  - `pnpm --dir frontend test -- branch-search-console.test.tsx`
  - `pnpm --dir frontend typecheck`
  - `pnpm --dir frontend lint`
- Done when:
  - frontend knowledge and branch-search surfaces are thin over typed backend
    responses and pure frontend formatting helpers
- Completed notes:
  - `knowledge-autonomy-sections.tsx` now re-exports focused memory,
    repository, shared-control, and formatting helpers from
    `frontend/components/console/knowledge-autonomy/`.
  - `branch-search-sections.tsx` now re-exports focused list, detail, evidence,
    action-control, shared, and formatting helpers from
    `frontend/components/console/branch-search/`.
  - Validation: `pnpm --dir frontend test -- knowledge-autonomy-console.test.tsx`,
    `pnpm --dir frontend test -- branch-search-console.test.tsx`,
    `pnpm --dir frontend typecheck`, and `pnpm --dir frontend lint`.

---

## Phase 73: Handoff, Export, And Redaction Decomposition

### GBX-R430: Split Session Export Into Package Assembly, Handoff Summary, Artifact Manifest, And Redaction Modules

- Status: `DONE`
- Depends on: `GBX-R400`
- Goal: reduce
  [session_export.py](../src/glassbox/runtime/session_export.py) by separating
  portable package assembly from v11 handoff-summary and redaction concerns
- Deliverables:
  - package metadata and event/projection collection helper
  - artifact manifest/reference helper
  - handoff summary assembly helper for objective, checkpoint, compaction,
    verification, accepted risks, pending actions, lineage, knowledge posture,
    and safe commands
  - redaction helper shared by transcript, runtime notes, handoff summary, and
    artifact references
  - stable export JSON shape and import compatibility
- Implementation notes:
  - preserve local-first custody guidance and inspection-only import behavior
  - do not commit raw `.glassbox` state or expose secrets through summaries
  - keep redaction deterministic and covered
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_cli_session_export.py`
  - `uv run pytest tests/integration/test_cli_session_import.py`
  - focused redaction tests for handoff summaries
  - `uv run ty check src/glassbox/runtime/session_export.py`
- Done when:
  - export behavior remains stable while package assembly, handoff summary,
    artifact manifest, and redaction can evolve independently
- Completed notes:
  - `session_export.py` is now a compatibility facade over
    `session_export_package.py`, `session_export_handoff.py`,
    `session_export_manifest.py`, and `session_export_redaction.py`.
  - Redaction is covered by focused unit tests, and guardrails now cap the
    facade plus the new package, handoff, manifest, and redaction helpers.
  - Validation: `uv run pytest tests/unit/test_session_export_redaction.py`,
    `uv run pytest tests/unit/test_architecture_guardrails.py`,
    `uv run pytest tests/integration/test_cli_session_export.py`,
    `uv run pytest tests/integration/test_cli_session_import.py`,
    `uv run ruff format --check src/glassbox/runtime/session_export*.py tests/unit/test_session_export_redaction.py tests/unit/test_architecture_guardrails.py`,
    `uv run ruff check src/glassbox/runtime/session_export*.py tests/unit/test_session_export_redaction.py tests/unit/test_architecture_guardrails.py`,
    and `uv run ty check src/glassbox/runtime/session_export.py src/glassbox/runtime/session_export_package.py src/glassbox/runtime/session_export_handoff.py src/glassbox/runtime/session_export_manifest.py src/glassbox/runtime/session_export_redaction.py src/glassbox/runtime/session_export_utils.py`.

### GBX-R431: Split Session Import Handoff Note Handling From Package Validation

- Status: `DONE`
- Depends on: `GBX-R430`
- Goal: keep
  [session_import.py](../src/glassbox/runtime/session_import.py) focused by
  separating package validation, inspection-only session creation, imported
  transcript/runtime notes, and handoff-note construction
- Deliverables:
  - import package validation helper
  - inspection-only session creation helper
  - transcript and runtime-note import helper
  - handoff-note helper that consumes the v11 summary without duplicating export
    logic
- Implementation notes:
  - preserve import compatibility for older packages
  - imported sessions remain non-resumable inspection state
  - do not invent checkpoint or verification evidence for imported packages
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_cli_session_import.py`
  - `uv run pytest tests/integration/test_cli_session_export.py`
- Done when:
  - handoff import behavior is stable and package validation is independently
    testable
- Completed notes:
  - `session_import.py` is now a compatibility facade/coordinator over
    `session_import_validation.py`, `session_import_events.py`, and
    `session_import_handoff.py`.
  - Package validation, inspection-only event construction, transcript/task/
    checkpoint import, and handoff runtime-note construction now have separate
    owners without changing inspection-only import semantics.
  - Validation: `uv run pytest tests/unit/test_session_import_validation.py`,
    `uv run pytest tests/unit/test_architecture_guardrails.py`,
    `uv run pytest tests/integration/test_cli_session_import.py`,
    `uv run pytest tests/integration/test_cli_session_export.py`,
    `uv run ruff format --check src/glassbox/runtime/session_import*.py tests/unit/test_session_import_validation.py tests/unit/test_architecture_guardrails.py`,
    `uv run ruff check src/glassbox/runtime/session_import*.py tests/unit/test_session_import_validation.py tests/unit/test_architecture_guardrails.py`,
    and `uv run ty check src/glassbox/runtime/session_import.py src/glassbox/runtime/session_import_validation.py src/glassbox/runtime/session_import_events.py src/glassbox/runtime/session_import_handoff.py`.

### GBX-R432: Split Service Contract Models By Domain Without Breaking Public Imports

- Status: `DONE`
- Depends on: `GBX-R430`
- Goal: plan and optionally implement a careful split of
  [services/contracts.py](../src/glassbox/services/contracts.py) if export,
  artifact, background-job, memory, task, branch-search, and session contracts
  continue to grow
- Deliverables:
  - domain contract strategy for session repository, artifact repository,
    background jobs, workspace memory, tasks, branch search, and session service
  - compatibility plan for keeping `glassbox.services` and
    `glassbox.services.contracts` stable public import surfaces
  - optional implementation only for cohesive contract families where tests
    prove import stability
- Implementation notes:
  - do not split services for line count alone
  - contracts must stay free of concrete store, runtime, CLI, and web imports
  - any implementation split should be incremental and heavily covered by
    import-smoke, bootstrap, repository-adapter, CLI, and web tests
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_service_contracts.py`
  - `uv run pytest tests/unit/test_import_smoke.py`
  - repository adapter boundary tests
- Done when:
  - the repository has a clear service-contract growth strategy and any moved
    contracts preserve public imports
- Completed notes:
  - `services/contracts.py` remains intentionally unsplit for this pass because
    it is currently protocol/model-heavy rather than a mixed concrete
    implementation module.
  - [refactor-boundaries.md](./refactor-boundaries.md) now records the domain
    split strategy, compatibility import plan, and criteria for a future
    cohesive contract-family extraction.
  - Import-stability coverage now asserts `glassbox.services` and
    `glassbox.services.contracts` expose the same public contract objects.
  - Validation: `uv run pytest tests/unit/test_service_contracts.py`,
    `uv run pytest tests/test_import_smoke.py`,
    `uv run pytest tests/unit/test_repository_adapter_boundaries.py`,
    `uv run ruff format --check tests/unit/test_service_contracts.py tests/unit/test_architecture_guardrails.py`,
    `uv run ruff check tests/unit/test_service_contracts.py tests/unit/test_architecture_guardrails.py`,
    and `uv run ty check src/glassbox/services/contracts.py src/glassbox/services/__init__.py`.

---

## Phase 74: CLI And Frontend Operator Surface Decomposition

### GBX-R440: Split Status Formatters Into Session, Task, Observability, Policy, And Knowledge Modules

- Status: `DONE`
- Depends on: `GBX-R400`
- Goal: reduce
  [status_formatters.py](../src/glassbox/cli/status_formatters.py) by
  separating the v11 safe-workflow summaries and evidence formatting by status
  surface
- Deliverables:
  - session status formatter helper for transcript, next action, checkpoint,
    compaction, tool attempt, verification, provider, and projection cues
  - task status formatter helper for continuation, pause-window, verification,
    budget, and recovery cues
  - observability status formatter helper for runtime/projection/artifact/
    provider/index/backup/knowledge cues
  - policy formatting helper shared by session/tool/approval surfaces where
    appropriate
  - stable terminal copy unless a later task explicitly changes it
- Implementation notes:
  - preserve JSON command output shape
  - keep formatting in CLI modules, not runtime query services
  - avoid duplicating safe-command guidance already derived by runtime helpers
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_cli_renderer.py`
  - `uv run pytest tests/integration/test_cli_session_commands.py`
  - `uv run pytest tests/integration/test_cli_task_commands.py`
  - `uv run pytest tests/integration/test_observability_status.py`
- Done when:
  - status output remains behavior-compatible while each operator surface owns
    its formatting
- Completed notes:
  - `status_formatters.py` is now a compatibility facade over session status
    formatting in `status_session.py`, while task status rendering lives in
    `status_task.py`, observability status rendering lives in
    `status_observability.py`, and knowledge provenance formatting lives in
    `status_knowledge.py`.
  - `task_commands.py` and `observability_commands.py` now keep command flow
    separate from terminal status rendering without changing JSON output shape
    or terminal copy.
  - Guardrails now cap the status facade and new operator-surface helpers so
    future CLI status behavior lands in the intended owner.
  - Validation: `uv run pytest tests/unit/test_cli_renderer.py tests/unit/test_cli_facade_characterization.py tests/unit/test_architecture_guardrails.py`,
    `uv run pytest tests/integration/test_cli_session_commands.py tests/integration/test_cli_task_commands.py tests/integration/test_observability_status.py`,
    `uv run ruff format --check src/glassbox/cli/status_formatters.py src/glassbox/cli/status_session.py src/glassbox/cli/status_task.py src/glassbox/cli/status_observability.py src/glassbox/cli/status_knowledge.py src/glassbox/cli/task_commands.py src/glassbox/cli/observability_commands.py tests/unit/test_architecture_guardrails.py`,
    `uv run ruff check src/glassbox/cli/status_formatters.py src/glassbox/cli/status_session.py src/glassbox/cli/status_task.py src/glassbox/cli/status_observability.py src/glassbox/cli/status_knowledge.py src/glassbox/cli/task_commands.py src/glassbox/cli/observability_commands.py tests/unit/test_architecture_guardrails.py`,
    and `uv run ty check src/glassbox/cli/status_formatters.py src/glassbox/cli/status_session.py src/glassbox/cli/status_task.py src/glassbox/cli/status_observability.py src/glassbox/cli/status_knowledge.py src/glassbox/cli/task_commands.py src/glassbox/cli/observability_commands.py`.

### GBX-R441: Split Command Guide Data From Rendering And Workflow Grouping

- Status: `DONE`
- Depends on: `GBX-R440`
- Goal: reduce
  [command_guide.py](../src/glassbox/cli/command_guide.py) by separating
  command metadata, workflow grouping, JSON serialization, and terminal
  rendering
- Deliverables:
  - typed command-guide model data or builders
  - workflow grouping helper for recovery, verification, provider, knowledge,
    branch-search, handoff, and release workflows
  - JSON serializer helper that keeps downstream-compatible shape
  - terminal renderer helper that owns copy and ordering
- Implementation notes:
  - preserve `glassbox command guide` and `--json` output semantics
  - avoid making the guide a second parser definition source
  - keep command copy aligned with actual parser names
- Tests and validation included in task:
  - command guide formatter tests
  - `uv run glassbox command guide`
  - `uv run glassbox command guide --json`
- Done when:
  - workflow command guidance can expand without widening one formatter module
- Completed notes:
  - `command_guide.py` is now a compatibility facade over focused command
    guide models, section data, workflow grouping, JSON serialization, and
    terminal rendering helpers.
  - `command_guide_workflows.py` owns workflow-family grouping for recovery,
    verification, provider, knowledge, branch-search, handoff, and release
    guidance while `command_guide_data.py` remains aligned with the real parser
    command names.
  - Unit coverage now characterizes the renderer, stable JSON payload shape,
    and workflow grouping helper, and guardrails cap the facade plus each new
    command-guide owner.
  - Validation: `uv run pytest tests/unit/test_command_guide.py tests/integration/test_cli_entrypoint.py -k command_guide`,
    `uv run glassbox command guide`,
    `uv run glassbox command guide --json`,
    `uv run ruff format --check src/glassbox/cli/command_guide*.py tests/unit/test_command_guide.py tests/unit/test_architecture_guardrails.py`,
    `uv run ruff check src/glassbox/cli/command_guide*.py tests/unit/test_command_guide.py tests/unit/test_architecture_guardrails.py`,
    and `uv run ty check src/glassbox/cli/command_guide.py src/glassbox/cli/command_guide_data.py src/glassbox/cli/command_guide_models.py src/glassbox/cli/command_guide_json.py src/glassbox/cli/command_guide_render.py src/glassbox/cli/command_guide_workflows.py tests/unit/test_command_guide.py`.

### GBX-R442: Split Interactive Command Handlers By Local, Daemon, Action, And Launch Boundaries

- Status: `TODO`
- Depends on: `GBX-R400`
- Goal: reduce
  [interactive_commands.py](../src/glassbox/cli/interactive_commands.py) and
  [parser_sessions.py](../src/glassbox/cli/parser_sessions.py) by separating
  launch mode, daemon forwarding, local session actions, autonomy option
  resolution, and parser wiring
- Deliverables:
  - chat/run/attach launch helper boundaries that preserve TUI/plain fallback
  - daemon-forwarded action helpers for cancel/message/answer/approval where
    applicable
  - local action helpers for resume, message, answer, approve, deny, fork, and
    cancel
  - autonomy option parser/resolution helpers kept separate from action
    execution
  - stable CLI options, exit codes, and daemon-owner safety checks
- Implementation notes:
  - keep interactive startup summary and dashboard startup behavior stable
  - do not duplicate daemon HTTP action payloads in multiple handlers
  - preserve CI/plain-mode compatibility
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_cli_interactive_launch.py`
  - `uv run pytest tests/unit/test_cli_interactive_client.py`
  - `uv run pytest tests/integration/test_cli_interactive_commands.py`
  - `uv run pytest tests/integration/test_daemon_runtime.py`
- Done when:
  - interactive session command behavior is stable while launch, daemon, local
    action, and parser concerns are independently owned

### GBX-R443: Split Session Store Stream, Detail Pagination, Drafts, And Actions

- Status: `TODO`
- Depends on: `GBX-R422`
- Goal: reduce
  [session-store.ts](../frontend/stores/session-store.ts) by moving live stream
  handling, detail-page pagination, local drafts, and action mutations into
  owned helpers while preserving the store factory contract
- Deliverables:
  - stream lifecycle helper that owns connect/reconnect/disconnect callbacks
  - detail-page pagination helper for transcript, event, and metrics pages
  - draft-state helper for composer, answers, fork labels, and compare target
  - action helper for prompt, answer, approval, cancel, fork, retry, and
    abandon mutations
  - `createSessionStore` compatibility maintained
- Implementation notes:
  - stores may import API and SSE helpers, but not React components
  - preserve route reset behavior, request invalidation, action state, and
    stream state transitions
  - keep reducers/pure state application in `frontend/state/`
- Tests and validation included in task:
  - `pnpm --dir frontend test -- session-state.test.ts`
  - `pnpm --dir frontend test -- sse-client.test.ts`
  - `pnpm --dir frontend test -- dashboard-stores.test.ts`
  - `pnpm --dir frontend typecheck`
  - `pnpm --dir frontend lint`
- Done when:
  - session-store behavior remains stable while stream, pagination, drafts, and
    actions can evolve independently

---

## Phase 75: Runtime Recovery And Projection Boundary Cleanup

### GBX-R450: Split Tool Attempt Recovery Into Inspection, Retry, Abandon, And Artifact Helpers

- Status: `TODO`
- Depends on: `GBX-R400`
- Goal: reduce
  [tool_attempt_recovery.py](../src/glassbox/runtime/tool_attempt_recovery.py)
  by separating inspection summaries, retry safety checks, abandon decisions,
  output artifact reads, and CLI/API result models
- Deliverables:
  - inspection helper for stale/failed/running attempt posture
  - retry eligibility and confirmation helper
  - abandon eligibility and event construction helper
  - output artifact lookup/read helper
  - stable CLI/API recovery result payloads
- Implementation notes:
  - preserve retry approval posture and safe-to-retry classification semantics
  - do not rerun tools automatically without explicit operator confirmation
  - keep artifact reads bounded and redacted where current behavior requires it
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_tool_attempt_retry.py`
  - `uv run pytest tests/integration/test_turn_engine_tool_loop.py`
  - `uv run pytest tests/integration/test_web_session_interaction.py`
  - CLI tool-attempt command tests
- Done when:
  - tool-attempt recovery behavior remains stable while inspection, retry,
    abandon, and artifact concerns are independently owned

### GBX-R451: Split Context Compaction Service Into Range Planning, Artifact Assembly, Freshness, And Mutation Helpers

- Status: `TODO`
- Depends on: `GBX-R400`
- Goal: reduce
  [context_compaction_service.py](../src/glassbox/runtime/context_compaction_service.py)
  by separating over-range guidance, source selection, artifact assembly,
  freshness assessment, refresh, and invalidation
- Deliverables:
  - source-range planning helper that owns v11 over-cap guidance
  - artifact payload assembly helper that owns source references and
    limitations
  - freshness assessment helper separated from mutation helpers
  - refresh and invalidation helpers that preserve event semantics
  - stable CLI/API compaction behavior
- Implementation notes:
  - preserve artifact schema and source-reference cap
  - keep compactions as evidence, not cleanup
  - do not make stale compactions prompt-authoritative
- Tests and validation included in task:
  - compaction unit tests
  - `uv run pytest tests/integration/test_cli_session_commands.py`
  - `uv run pytest tests/integration/test_web_session_snapshot.py`
  - relevant compaction eval cases
- Done when:
  - compaction guidance, artifact assembly, freshness, refresh, and
    invalidation are independently testable

### GBX-R452: Split Turn Event Recorder And Tool Executor Artifact Hooks

- Status: `TODO`
- Depends on: `GBX-R450`, `GBX-R451`
- Goal: keep
  [turn_event_recorder.py](../src/glassbox/runtime/turn_event_recorder.py) and
  [turn_tool_executor.py](../src/glassbox/runtime/turn_tool_executor.py)
  focused by moving artifact recording, replay capture hooks, task-plan capture
  linkage, and tool-attempt heartbeat construction into owned helpers
- Deliverables:
  - artifact recording helper for tool output, diff summaries, pytest failure
    digests, and replay artifact records
  - replay capture hook helper or adapter that stays separate from event
    persistence
  - task-plan capture linkage helper if it continues to grow
  - tool-attempt heartbeat construction helper shared by normal, failed, and
    cancelled tool paths
  - stable turn event ordering and replay artifacts
- Implementation notes:
  - event ordering is part of the contract; add characterization before moving
    high-risk sequences
  - keep the turn engine as the coordinator, not the artifact or replay owner
  - preserve cancellation and provider recovery semantics
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_turn_engine.py`
  - `uv run pytest tests/integration/test_turn_engine_tool_loop.py`
  - `uv run pytest tests/unit/test_turn_event_recorder.py`
  - replay capture tests
- Done when:
  - turn event recording and tool execution remain behavior-compatible while
    artifact/replay/attempt helpers are owned and covered

### GBX-R453: Split Task And Background Projection Application By Event Family

- Status: `TODO`
- Depends on: `GBX-R400`
- Goal: reduce broad projection modules such as
  [sqlite_projection_tasks.py](../src/glassbox/store/sqlite_projection_tasks.py)
  and [sqlite_background_jobs.py](../src/glassbox/store/sqlite_background_jobs.py)
  by separating event-family handlers where review pressure is highest
- Deliverables:
  - task plan, task step, task pause/resume, and task verification projection
    handlers separated where practical
  - background job creation, lifecycle, retry, pause/cancel, and recovery
    handlers separated where practical
  - compatibility projection coordinator imports preserved
  - projection rebuild behavior unchanged
- Implementation notes:
  - projection tables remain rebuildable and non-authoritative
  - do not change table names, column names, indexes, or migration versions
    unless a separate product task requires it
  - prefer handler extraction over abstract projection frameworks
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_sqlite_projections.py`
  - `uv run pytest tests/integration/test_projection_rebuild.py`
  - `uv run pytest tests/integration/test_background_jobs.py`
  - `uv run pytest tests/integration/test_web_task_routes.py`
- Done when:
  - task and background projection behavior remains stable while event-family
    handlers are easier to review

---

## Phase 76: Documentation And Validation Closeout

### GBX-R460: Update Architecture Docs For The V11 Refactor Shape

- Status: `TODO`
- Depends on: `GBX-R410`, `GBX-R411`, `GBX-R412`, `GBX-R420`, `GBX-R421`,
  `GBX-R422`, `GBX-R430`, `GBX-R431`, `GBX-R432`, `GBX-R440`, `GBX-R441`,
  `GBX-R442`, `GBX-R443`, `GBX-R450`, `GBX-R451`, `GBX-R452`, `GBX-R453`
- Goal: align architecture and boundary docs with the final v11 refactor module
  shape
- Deliverables:
  - updates to [architecture.md](./architecture.md) where recommendation,
    knowledge, branch-search, handoff, CLI, frontend, recovery, or projection
    ownership changed materially
  - updates to [database.md](./database.md) if projection ownership changed
  - updates to [refactor-boundaries.md](./refactor-boundaries.md) marking the
    v11 boundary map as implemented
  - updates to this roadmap with completed notes for each finished task
  - docs hub updates only if new boundaries should be discoverable from the
    public docs index
- Implementation notes:
  - document architectural ownership and dependency direction, not just file
    moves
  - avoid claiming new product behavior from refactor-only work
  - keep historical v1, v8, and v10 notes intact unless they have become
    misleading
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_release_candidate_docs.py`
  - docs review against final module layout
- Done when:
  - docs and code describe the same v11 refactor shape and remaining
    compatibility shims are either justified or tracked

### GBX-R461: Close Out V11 Refactor Guardrails And Focused Validation

- Status: `TODO`
- Depends on: `GBX-R460`
- Goal: add final characterization and validation coverage proving the v11
  refactor preserved behavior across recommendation, knowledge, branch-search,
  handoff, CLI, frontend, recovery, and projection seams
- Deliverables:
  - final guardrail coverage for new v11 facades and domain boundaries
  - characterization tests for the highest-risk moved behavior where not
    already covered
  - documented validation command set for future confidence-surface refactor
    tasks
  - explicit list of accepted compatibility shims and intended owners for new
    behavior
- Implementation notes:
  - prefer narrow guardrails that catch real coupling regressions
  - do not freeze low-risk internal helper names
  - keep compatibility shims only when they serve a real public import, route,
    command, script, or component contract
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_architecture_guardrails.py`
  - focused backend and frontend tests for all refactored seams
  - final baseline validation as practical for the touched repository state
  - `pnpm --dir frontend typecheck`
  - `pnpm --dir frontend lint`
  - `pnpm --dir frontend test`
  - `uv run python scripts/validate_v11_release_gate.py --dry-run`
- Done when:
  - the v11 refactor roadmap can be marked complete with guardrails that
    protect the new module shape from immediate regression
