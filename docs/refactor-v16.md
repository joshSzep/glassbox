# Glassbox Refactor v16 Tasks

For the docs hub and operator guides, start at [README.md](./README.md). This
file is the next behavior-preserving refactor roadmap after
[refactor-v15.md](./refactor-v15.md). It starts from the completed v16
operator-flow release-candidate milestone and targets the code paths that grew
while v16 added typed next actions, a unified operator queue, evidence graph
claim support, verification-plan lifecycle, changeset workup compression,
maintenance cues, recovery playbooks, dashboard flow cockpit surfaces, and
reviewer-safe evidence bundles.

## Purpose

This document defines a post-v16 refactor roadmap for the current Glassbox
codebase.

It follows the execution style of [refactor-v1.md](./refactor-v1.md),
[refactor-v8.md](./refactor-v8.md), [refactor-v10.md](./refactor-v10.md),
[refactor-v11.md](./refactor-v11.md), [refactor-v13.md](./refactor-v13.md),
[refactor-v14.md](./refactor-v14.md), and [refactor-v15.md](./refactor-v15.md):
explicit dependencies, small vertical slices, concrete deliverables, and
validation requirements attached directly to the work.

This roadmap is not a product-feature roadmap. It exists to keep the current
local-first, event-sourced architecture easy to evolve by:

- separating v16 operator-flow derivation from queue ranking, claim support,
  verification planning, CLI formatting, API payload shaping, dashboard
  rendering, and release-gate evidence summaries
- keeping next actions, queue items, evidence graph nodes, verification plan
  entries, maintenance cues, and recovery playbooks independently reviewable
- preserving current CLI, TUI, dashboard, API, replay, eval, package,
  projection, changeset, review-loop, and release-gate behavior unless a later
  task explicitly changes a contract
- tightening architecture guardrails around modules that grew during v16
- avoiding line-count-only splits in model-heavy, event-heavy, generated,
  fixture-heavy, or public compatibility surfaces

## Refactor Direction

The post-v15 refactor successfully split repository-intelligence surfaces
before v16 compressed operator flow. The v16 milestone then made operator
guidance more explicit by adding:

- shared next-action domain models with target, evidence, command recipe,
  safety, confidence, limitation, and reviewer-safe fields
- a unified operator queue that ranks work-blocking, review-blocking,
  verification-blocking, maintenance, advisory, and informational items
- evidence graph summaries for session and changeset claim support
- verification plan lifecycle entries, skipped checks, selection, execution,
  accepted risk, and superseding commands
- one-command changeset workup previews and guided workup flows
- dashboard queue, evidence graph, verification plan, and maintenance cockpit
  surfaces
- maintenance cue and recovery playbook models that keep upkeep visible beside
  active work
- deterministic v16 evals, release-gate stages, package checks, and
  dogfooding evidence

The implementation is coherent, but v16 concentrated new behavior in a handful
of places. The next refactor should keep those contracts dependable before a
future milestone expands operator-flow intelligence again.

Current pressure points include:

- `src/glassbox/runtime/evidence_graph.py`: changeset graph construction,
  session graph construction, node creation, claim support, missing/stale
  evidence handling, accepted-risk/manual-only posture, graph summaries, node
  lookups, and neighborhood traversal live in one runtime module.
- `src/glassbox/runtime/verification_plan_builder.py`: recommendation targets,
  command recipes, eval profiles, eval cases, release surfaces, readiness
  requirements, manual-only entries, skipped rows, caps, stable IDs, command
  shaping, and duplicate suppression live in one planner module.
- `src/glassbox/runtime/operator_queue.py`: session queue rows, runtime and
  maintenance rows, item factories, evidence summaries, sorting, dedupe, and
  counts live in one queue module.
- `src/glassbox/core/models.py`, `src/glassbox/core/events.py`, and
  `src/glassbox/core/types.py`: still acceptable broad public model-heavy
  surfaces, but v16 added enough operator-flow, evidence graph, maintenance,
  and verification contracts that future expansion should use a domain module
  strategy rather than growing these files indefinitely.
- `src/glassbox/web/session_api_aggregate.py`,
  `src/glassbox/web/changeset_api_builders_detail.py`,
  `src/glassbox/web/routes/session_route_queries.py`, and
  `src/glassbox/web/routes/changeset_route_actions.py`: v16 response models
  and builders are useful but need clearer ownership before new queue,
  evidence graph, or verification fields land.
- `frontend/components/console/workspace-overview/operator-queue-lanes.tsx`:
  lane definitions, filtering, row rendering, badges, safe-action text,
  deep-link construction, freshness, limitations, and target routing live in
  one component.
- `frontend/components/console/evidence-graph-panel.tsx`: graph frame, summary
  filters, claims, nodes, relationships, limitations, anchors, labels, and
  variants live in one component.
- `frontend/components/console/changeset/verification.tsx`,
  `frontend/stores/changeset-store-review-actions.ts`, and related changeset
  store helpers carry more verification-plan workflow state than earlier
  review-loop surfaces.
- `scripts/validate_v16_release_gate.py` and its helper modules now encode
  deterministic v16 stages, advisory evidence posture, dry-run planning,
  package checks, dogfooding expectations, and summary metadata.
- `tests/unit/architecture_guardrails/rules.py` protects earlier refactor-era
  boundaries, but v16 operator-flow pressure points do not yet have a
  post-extraction guardrail family.

Large files that are primarily model-heavy, generated, or fixture-heavy are not
automatically refactor targets. In particular, generated frontend API types,
generated OpenAPI JSON, deterministic eval fixtures, release evidence
artifacts, and broad characterization tests should be split only when a real
ownership or review problem appears.

The post-v16 refactor thesis is:

- keep canonical events and managed artifacts as the source of truth
- keep next actions advisory unless a narrower readiness contract marks a state
  as blocking
- keep queue ranking deterministic, local, inspectable, and bounded
- keep evidence graph support explanatory rather than approval, verification,
  publication, or hosted-review authority
- keep verification planning distinct from selecting, executing, skipping,
  accepting risk, and recording retained evidence
- keep maintenance cues visible without automatically turning advisory upkeep
  into release blockers
- keep runtime queue, graph, and verification helpers transport-agnostic
- keep web response models and frontend generated API types as transport
  contracts, not business-logic owners
- keep frontend stores responsible for transport and components responsible for
  presentation and local interaction state
- move queue item derivation, graph node/claim construction, verification entry
  construction, core operator-flow contracts, web builders, dashboard panels,
  and release-gate stage assembly into focused owner modules
- preserve compatibility facades where imports, commands, routes, generated API
  types, stores, or component entrypoints rely on them
- add guardrails only when the intended repair is local, obvious, and backed by
  an explicit owner module

## Agent Execution Rules

These rules apply to every task in this file.

1. Respect dependency order. Do not start a task until its dependencies are
   complete unless the task explicitly says it can proceed in parallel.
2. Preserve current behavior by default. Refactor tasks should not intentionally
   change CLI semantics, TUI slash-command behavior, dashboard workflows, API
   payloads, replay outcomes, eval outcomes, event ordering, projection
   behavior, package contents, release-gate behavior, queue ranking,
   evidence-graph claim state, verification-plan lifecycle, maintenance cue
   posture, or reviewer-safe export behavior unless the task explicitly
   includes that contract change.
3. Treat `events` as the canonical source of truth. Query services, route
   helpers, stores, frontend derivation, UI projections, queue rows, evidence
   graphs, verification plans, maintenance cues, repository intelligence
   snapshots, and prompt fragments remain derived from canonical events, typed
   API responses, managed artifacts, local source files, or rebuildable
   projection tables.
4. Repair architectural duplication before splitting files mechanically. If two
   modules shape the same safe next action, evidence reference, claim support,
   verification identity, skipped-check posture, stale-evidence copy, or
   maintenance cue, extract the shared boundary first.
5. Prefer extractions with thin compatibility shims over broad rewrites. Keep
   diffs incremental and executable.
6. Keep public facades stable unless a task explicitly changes the import,
   route, API, command, store, or component contract.
7. Do not introduce new framework layers unless they remove a real current
   coupling in the codebase.
8. Do not move API calls into React components. Frontend stores own transport;
   components own presentation and local interaction state; pure helper modules
   own derivation and formatting.
9. Do not move HTTP response models or FastAPI dependencies into runtime queue,
   evidence graph, verification, maintenance, or recommendation services.
   Runtime services stay transport-agnostic.
10. Do not make operator-flow guidance stronger than its current advisory
    contract. It can recommend, rank, explain, and cite evidence; it cannot
    claim reviewer approval, verification success, owner assignment,
    publication readiness, command approval, merge readiness, or release
    authority.
11. Do not add hosted task queues, hosted review state, remote code search,
    external vector-store authority, provider-side hidden memory, automatic
    owner assignment, automatic staging, committing, pushing, pull request
    creation, merging, deployment, publication, or automatic maintenance
    remediation as part of refactor-only work.
12. Every refactor task automatically includes:
    - automated tests for moved or extracted behavior where practical
    - `ruff` formatting and lint compliance for touched Python code
    - `ty` typecheck compliance for touched Python code
    - focused `pytest` coverage for touched runtime, store, CLI, web, replay,
      eval, daemon, queue, evidence graph, verification, task, changeset,
      review, handoff, maintenance, provider, repository intelligence,
      frontend API, and release-gate behavior
    - frontend lint, typecheck, tests, and build when the task touches
      dashboard code, generated API types, packaged static assets, route
      assumptions, frontend stores, queue panels, evidence graph panels, or
      verification plan panels
    - documentation updates when public module boundaries, architecture
      references, import surfaces, API payloads, command behavior, package
      contents, release posture, or operator-visible outputs change materially

## Completion Contract For Any Task

A task is complete only when all of the following are true:

- the implementation exists in the intended module boundary
- automated tests covering the touched behavior exist and pass
- lint, formatting, and type checks pass for the touched slice
- compatibility shims, if any, are justified explicitly or tracked by a
  follow-up task in this file
- docs are updated if the refactor changes documented architecture, import
  surfaces, API payloads, command behavior, release posture, or
  operator-visible outputs
- deterministic replay/eval behavior remains stable or intentional drift is
  handled through the established baseline-refresh workflow
- generated OpenAPI and frontend API types are refreshed when web contracts
  change
- dashboard static assets remain fresh when packaged dashboard behavior changes
- new queue, evidence graph, verification, maintenance, or workup claims remain
  backed by deterministic local inputs, canonical events, managed artifacts,
  typed API responses, projection rows, or eval fixtures
- stale, missing, skipped, manual-only, accepted-risk, advisory, and
  reviewer-safe states remain visible rather than hidden
- no meaningful next-action, evidence graph, verification plan, maintenance
  cue, readiness, or handoff state exists only in memory once a task claims
  durability
- reviewer-facing artifacts are redacted or explicitly documented as local-only
- repository intelligence remains advisory and freshness-aware
- memory-derived guidance remains confirmed, active, provenance-backed, and
  prompt-use-recorded before it shapes model context
- the refactor does not weaken the local-first, event-sourced, replay-aware
  architecture described in [architecture.md](./architecture.md)
- the refactor does not weaken the v16 operator-flow and evidence contracts
  described in
  [v16-operator-flow-compression-contract.md](./v16-operator-flow-compression-contract.md),
  [operator-queue.md](./operator-queue.md), [evidence-graph.md](./evidence-graph.md),
  [verification-orchestrator.md](./verification-orchestrator.md), and
  [maintenance-cues.md](./maintenance-cues.md)

## Suggested Status Markers

If an agent updates this document later, use one of these markers next to task
IDs:

- `TODO`
- `IN_PROGRESS`
- `BLOCKED`
- `DONE`

## Recommended Validation Commands

Use the narrowest viable validation after each task, but the baseline
validation pattern for completed work should be:

```bash
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run pytest -n auto --dist loadfile
uv run pre-commit run --all-files
pnpm --dir frontend lint
pnpm --dir frontend typecheck
pnpm --dir frontend test
pnpm --dir frontend build
uv run python scripts/validate_v16_release_gate.py --dry-run
```

During incremental refactor work, use narrower commands when possible:

```bash
uv run pytest tests/unit/test_evidence_graph.py
uv run pytest tests/unit/test_changeset_verification_readiness.py
uv run pytest tests/unit/test_changeset_workup.py
uv run pytest tests/unit/test_session_query_derivation.py
uv run pytest tests/unit/test_runtime_eval_coverage.py
uv run pytest tests/integration/test_cli_changeset_commands.py
uv run pytest tests/integration/test_web_changeset_routes.py
uv run pytest tests/integration/test_web_session_aggregate.py
uv run pytest tests/integration/test_observability_status.py
uv run pytest tests/unit/architecture_guardrails
pnpm --dir frontend test -- workspace-overview.test.ts changeset-console.test.tsx session-inspector.test.ts generated-api-types.test.ts
```

When the work touches generated web contracts, include:

```bash
pnpm --dir frontend api:generate
git diff -- frontend/generated
```

When the work touches packaged dashboard behavior, include:

```bash
pnpm --dir frontend build
uv run python scripts/validate_frontend_release_assets.py
uv run python scripts/validate_package_contents.py
```

When the work touches release-gate, eval, or package evidence behavior,
include:

```bash
uv run glassbox eval audit --profile release-candidate --cwd .
uv run glassbox eval run --profile release-candidate --cwd .
uv run python scripts/validate_v16_release_gate.py --dry-run
```

## Milestone Map

The intended post-v16 refactor milestone order is:

1. v16 boundary refresh and characterization
2. evidence graph decomposition
3. verification plan builder cleanup
4. operator queue aggregation cleanup
5. core operator-flow domain strategy
6. web transport and builder cleanup
7. frontend cockpit cleanup
8. release-gate helper cleanup
9. guardrails, docs, and validation closeout

Each phase below corresponds to one concrete refactor milestone.

## Task Graph

---

## Phase 110: Post-V16 Boundary Refresh And Characterization

### GBX-R800: Define Post-V16 Refactor Boundary Map

- Status: `DONE`
- Dependencies: none
- Target files:
  - [refactor-boundaries.md](./refactor-boundaries.md)
  - [architecture.md](./architecture.md)
  - [refactor-v16.md](./refactor-v16.md)
  - `tests/unit/architecture_guardrails/`
- Work:
  - document the intended post-v16 compatibility facades and helper owners
  - name evidence graph, verification plan builder, operator queue, core
    operator-flow contracts, web builders, dashboard cockpit components, and
    v16 release-gate helpers as first pressure points
  - distinguish model-heavy public surfaces from mixed-responsibility modules
    that should be split
  - keep v16 advisory next-action, evidence graph, verification, maintenance,
    and publication-boundary non-goals explicit
- Deliverables:
  - documented boundary map for runtime, core, web, frontend, release-gate, and
    guardrail surfaces
  - initial guardrail expectations for post-v16 pressure points where intended
    owner modules are already clear
- Validation:
  - `uv run pytest tests/unit/architecture_guardrails`
  - `uv run pytest tests/unit/test_release_candidate_docs.py -q`

### GBX-R801: Characterize Current Operator Flow Behavior

- Status: `DONE`
- Dependencies: GBX-R800
- Target files:
  - `tests/unit/test_evidence_graph.py`
  - `tests/unit/test_changeset_verification_readiness.py`
  - `tests/unit/test_changeset_workup.py`
  - `tests/unit/test_session_query_derivation.py`
  - `tests/unit/test_runtime_eval_coverage.py`
  - `tests/integration/test_cli_changeset_commands.py`
  - `tests/integration/test_web_session_aggregate.py`
  - `tests/integration/test_web_changeset_routes.py`
  - `frontend/tests/workspace-overview.test.ts`
  - `frontend/tests/changeset-console.test.tsx`
  - `frontend/tests/session-inspector.test.ts`
- Work:
  - identify highest-risk current behavior before movement begins
  - add characterization coverage where moved behavior is not already asserted
  - prefer narrow tests around queue ranking, maintenance-row non-blocking
    posture, evidence graph claim states, missing/stale/manual-only evidence,
    verification duplicate suppression, skipped-check rows, workup non-claims,
    and dashboard deep links
  - explicitly record accepted behavior gaps that should not block
    refactor-only movement
- Deliverables:
  - current behavior coverage sufficient for runtime, web, and frontend
    extraction tasks
  - accepted-gap list for behavior intentionally left unchanged during
    refactor-only work
- Validation:
  - `uv run pytest tests/unit/test_evidence_graph.py`
  - `uv run pytest tests/unit/test_changeset_verification_readiness.py`
  - `uv run pytest tests/unit/test_changeset_workup.py`
  - `uv run pytest tests/unit/test_session_query_derivation.py`
  - `uv run pytest tests/integration/test_cli_changeset_commands.py -k "verification or workup or evidence"`
  - `uv run pytest tests/integration/test_web_session_aggregate.py`
  - `uv run pytest tests/integration/test_web_changeset_routes.py -k "verification or evidence"`
  - `pnpm --dir frontend test -- workspace-overview.test.ts changeset-console.test.tsx session-inspector.test.ts`

### GBX-R802: Add Post-V16 Guardrails After First Extraction

- Status: `DONE`
- Dependencies: GBX-R810, GBX-R820, GBX-R830
- Target files:
  - `tests/unit/architecture_guardrails/rules.py`
  - `tests/unit/architecture_guardrails/test_refactor_era_pressure_points.py`
  - `tests/unit/architecture_guardrails/test_python_facades.py`
  - `tests/unit/architecture_guardrails/test_frontend_boundaries.py`
  - [refactor-boundaries.md](./refactor-boundaries.md)
- Work:
  - add facade line-count and import-prefix expectations only after helper
    modules exist
  - assert that post-v16 runtime, core, web, frontend, and release-gate facades
    delegate to intended owner modules
  - keep guardrails narrow enough that they catch regression without freezing
    legitimate implementation detail
- Deliverables:
  - post-extraction architecture tests for the new v16 helper owners
- Validation:
  - `uv run pytest tests/unit/architecture_guardrails`

---

## Phase 111: Evidence Graph Decomposition

### GBX-R810: Split Evidence Graph Models And Builder Utilities

- Status: `DONE`
- Dependencies: GBX-R801
- Target files:
  - `src/glassbox/runtime/evidence_graph.py`
  - `src/glassbox/runtime/evidence_graph_models.py`
  - `src/glassbox/runtime/evidence_graph_builder.py`
  - `tests/unit/test_evidence_graph.py`
- Work:
  - move `EvidenceGraphSummary` and graph-local helper types into a model
    module where they are not already core domain contracts
  - move `_GraphBuilder`, edge construction, node lookup, truncation
    limitations, and summary helpers into a builder module
  - keep public imports from `runtime/evidence_graph.py` stable
  - preserve graph IDs, node IDs, edge IDs, claim IDs, caps, and validation
    behavior
- Deliverables:
  - evidence graph facade that can delegate target-specific graph derivation
    to focused helpers
- Validation:
  - `uv run pytest tests/unit/test_evidence_graph.py`
  - `uv run pytest tests/integration/test_web_changeset_routes.py -k evidence`
  - `uv run ruff check src/glassbox/runtime/evidence_graph*.py`
  - `uv run ty check src/glassbox/runtime/evidence_graph.py`

### GBX-R811: Split Changeset Evidence Graph Derivation By Node Family

- Status: `DONE`
- Dependencies: GBX-R810
- Target files:
  - `src/glassbox/runtime/evidence_graph.py`
  - `src/glassbox/runtime/evidence_graph_changeset.py`
  - `src/glassbox/runtime/evidence_graph_changeset_inventory.py`
  - `src/glassbox/runtime/evidence_graph_changeset_verification.py`
  - `src/glassbox/runtime/evidence_graph_changeset_review.py`
  - `tests/unit/test_evidence_graph.py`
- Work:
  - keep `build_changeset_evidence_graph` as the public entrypoint
  - move inventory node and freshness edge derivation into an inventory helper
  - move verification requirement, verification plan, skipped, stale, and
    accepted-risk derivation into a verification helper
  - move manual evidence, review feedback, response plan, command evidence,
    and safe next action derivation into review/evidence helpers
  - preserve claim support states, reviewer-safe redaction posture, missing
    evidence rows, limitation text, and bounded row caps
- Deliverables:
  - changeset graph derivation that can be reviewed by evidence source family
- Validation:
  - `uv run pytest tests/unit/test_evidence_graph.py -k changeset`
  - `uv run pytest tests/unit/test_changeset_verification_readiness.py -k graph`
  - `uv run pytest tests/integration/test_cli_changeset_commands.py -k evidence`

### GBX-R812: Split Session Evidence Graph Derivation

- Status: `DONE`
- Dependencies: GBX-R810
- Target files:
  - `src/glassbox/runtime/evidence_graph.py`
  - `src/glassbox/runtime/evidence_graph_session.py`
  - `src/glassbox/web/routes/session_route_queries.py`
  - `tests/unit/test_evidence_graph.py`
  - `tests/integration/test_web_session_snapshot.py`
- Work:
  - keep `build_session_evidence_graph` as the public entrypoint
  - move session status, transcript, tool, approval, runtime note,
    checkpoint, compaction, and recovery graph derivation into a session graph
    helper
  - keep route helpers consuming the public facade
  - preserve sparse-session limitations and historical session compatibility
- Deliverables:
  - session graph derivation separated from changeset graph derivation
- Validation:
  - `uv run pytest tests/unit/test_evidence_graph.py -k session`
  - `uv run pytest tests/integration/test_web_session_snapshot.py -k evidence`
  - `uv run pytest tests/integration/test_web_session_aggregate.py`

### GBX-R813: Split Evidence Graph Query And Neighborhood Helpers

- Status: `DONE`
- Dependencies: GBX-R811, GBX-R812
- Target files:
  - `src/glassbox/runtime/evidence_graph.py`
  - `src/glassbox/runtime/evidence_graph_queries.py`
  - `src/glassbox/web/routes/changeset_route_evidence_graph.py`
  - `src/glassbox/web/routes/session_route_queries.py`
  - `tests/unit/test_evidence_graph.py`
- Work:
  - move graph summarization, claim lookup, node lookup, and neighborhood
    traversal into a query helper
  - preserve max-neighborhood caps and missing node or claim behavior
  - keep web route helpers free of graph traversal internals
- Deliverables:
  - reusable graph query helpers for CLI, web, and dashboard routes
- Validation:
  - `uv run pytest tests/unit/test_evidence_graph.py -k "summary or neighborhood or lookup"`
  - `uv run pytest tests/integration/test_web_changeset_routes.py -k evidence`

---

## Phase 112: Verification Plan Builder Cleanup

### GBX-R820: Extract Verification Plan Entry Identity And Coalescing

- Status: `DONE`
- Dependencies: GBX-R801
- Target files:
  - `src/glassbox/runtime/verification_plan_builder.py`
  - `src/glassbox/runtime/verification_plan_identity.py`
  - `tests/unit/test_changeset_verification_readiness.py`
  - `tests/unit/test_eval_recommendations.py`
- Work:
  - introduce one helper for stable verification entry identity, dedupe keys,
    and cross-source coalescing
  - specifically address duplicate rows where the same command is recommended
    by direct recipe matching and changeset readiness
  - preserve verification IDs where current tests and retained fixtures depend
    on them unless an intentional eval refresh task approves drift
  - keep skipped-check cap behavior visible when entries are truncated
- Deliverables:
  - one owner for verification plan duplicate suppression and stable IDs
  - characterization coverage for direct recipe plus readiness duplicates
- Validation:
  - `uv run pytest tests/unit/test_changeset_verification_readiness.py -k "verification_plan or duplicate"`
  - `uv run pytest tests/unit/test_eval_recommendations.py -k recipe`
  - `uv run glassbox changeset verification-plan --path docs/v16-dogfooding-summary.md --json --cwd .`

### GBX-R821: Split Recommendation-Source Entry Builders

- Status: `DONE`
- Dependencies: GBX-R820
- Target files:
  - `src/glassbox/runtime/verification_plan_builder.py`
  - `src/glassbox/runtime/verification_plan_recommendations.py`
  - `src/glassbox/runtime/verification_plan_recipes.py`
  - `src/glassbox/runtime/verification_plan_evals.py`
  - `tests/unit/test_changeset_verification_readiness.py`
  - `tests/unit/test_eval_recommendations.py`
- Work:
  - move test-target entry construction into a recommendation helper
  - move command recipe entries and unsafe-command skipped rows into a recipe
    helper
  - move eval profile, eval case, and release-surface entries into eval and
    release helpers
  - preserve lifecycle states, changed paths, stale reasons, release surfaces,
    command recipes, and safe-command filtering
- Deliverables:
  - verification plan construction split by recommendation source family
- Validation:
  - `uv run pytest tests/unit/test_changeset_verification_readiness.py -k verification_plan`
  - `uv run pytest tests/unit/test_eval_recommendations.py`

### GBX-R822: Split Readiness And Manual-Only Entry Builders

- Status: `DONE`
- Dependencies: GBX-R820
- Target files:
  - `src/glassbox/runtime/verification_plan_builder.py`
  - `src/glassbox/runtime/verification_plan_readiness.py`
  - `src/glassbox/runtime/verification_plan_manual.py`
  - `tests/unit/test_changeset_verification_readiness.py`
  - `tests/unit/test_manual_evidence.py`
- Work:
  - move readiness requirement entry construction into a readiness helper
  - move manual evidence, advisory live evidence, browser/accessibility,
    provider, and non-command check entries into a manual-only helper
  - preserve manual-only lifecycle, missing evidence copy, target fields,
    evidence references, and non-passing posture
- Deliverables:
  - command-backed and manual-only verification plan entries separated by owner
- Validation:
  - `uv run pytest tests/unit/test_changeset_verification_readiness.py -k "manual or readiness"`
  - `uv run pytest tests/unit/test_manual_evidence.py`

### GBX-R823: Split Verification Plan Skipped-Check And Limit Handling

- Status: `DONE`
- Dependencies: GBX-R821, GBX-R822
- Target files:
  - `src/glassbox/runtime/verification_plan_builder.py`
  - `src/glassbox/runtime/verification_plan_skips.py`
  - `docs/verification-orchestrator.md`
  - `tests/unit/test_changeset_verification_readiness.py`
- Work:
  - move skipped-check construction, skipped-check caps, plan-entry-limit rows,
    unsafe-command explanations, operator-selection-required explanations, and
    skipped-check-limit behavior into a skip helper
  - preserve explicit skipped evidence as retained evidence, not proof of
    passing behavior
  - keep docs aligned if helper names or limit semantics become public
- Deliverables:
  - one owner for verification-plan skipped row and truncation behavior
- Validation:
  - `uv run pytest tests/unit/test_changeset_verification_readiness.py -k "skip or limit"`
  - `uv run pytest tests/unit/test_release_candidate_docs.py -q`

---

## Phase 113: Operator Queue Aggregation Cleanup

### GBX-R830: Split Session Queue Item Derivation

- Status: `DONE`
- Dependencies: GBX-R801
- Target files:
  - `src/glassbox/runtime/operator_queue.py`
  - `src/glassbox/runtime/operator_queue_session_items.py`
  - `tests/unit/test_session_query_derivation.py`
  - `tests/integration/test_web_session_aggregate.py`
- Work:
  - move pending approval, pending question, failed session, projection health,
    long-run, active turn, degraded, and historical session item construction
    into a session item helper
  - preserve queue family, priority, severity, stale/action-needed flags,
    evidence summaries, dedupe keys, and ordering
- Deliverables:
  - session queue derivation independently reviewable from runtime and
    maintenance rows
- Validation:
  - `uv run pytest tests/unit/test_session_query_derivation.py -k queue`
  - `uv run pytest tests/integration/test_web_session_aggregate.py`
  - `uv run glassbox queue list --json --cwd .`

### GBX-R831: Split Runtime And Maintenance Queue Item Derivation

- Status: `DONE`
- Dependencies: GBX-R830
- Target files:
  - `src/glassbox/runtime/operator_queue.py`
  - `src/glassbox/runtime/operator_queue_runtime_items.py`
  - `src/glassbox/runtime/operator_queue_maintenance_items.py`
  - `src/glassbox/runtime/observability_maintenance_cues.py`
  - `tests/integration/test_observability_status.py`
  - `tests/integration/test_web_session_aggregate.py`
- Work:
  - move daemon/runtime owner queue rows into a runtime item helper
  - move maintenance cue projection into a maintenance item helper
  - preserve advisory versus action-needed posture for missing repository
    intelligence, stale provider canaries, backup posture, artifact pressure,
    failed jobs, projection drift, and eval drift
  - keep maintenance cue source models authoritative for cue semantics
- Deliverables:
  - runtime and maintenance queue items separated from session rows
- Validation:
  - `uv run pytest tests/integration/test_observability_status.py -k maintenance`
  - `uv run pytest tests/integration/test_web_session_aggregate.py -k queue`

### GBX-R832: Split Queue Sorting, Dedupe, And Counts

- Status: `DONE`
- Dependencies: GBX-R830, GBX-R831
- Target files:
  - `src/glassbox/runtime/operator_queue.py`
  - `src/glassbox/runtime/operator_queue_sorting.py`
  - `src/glassbox/runtime/operator_queue_counts.py`
  - `tests/unit/test_session_query_derivation.py`
- Work:
  - move `_PRIORITY_ORDER`, `_SEVERITY_ORDER`, sort keys, dedupe behavior, and
    count derivation into focused helpers
  - preserve deterministic sorting by priority, stale/action posture, updated
    time, and target
  - keep dedupe behavior stable for same underlying local problem
- Deliverables:
  - queue aggregator facade reduced to orchestration over item sources and
    stable ordering helpers
- Validation:
  - `uv run pytest tests/unit/test_session_query_derivation.py -k "queue or priority"`
  - `uv run pytest tests/integration/test_web_session_aggregate.py`

### GBX-R833: Add Queue Source Coverage For Changesets And Verification Gaps

- Status: `DONE`
- Dependencies: GBX-R832
- Target files:
  - `src/glassbox/runtime/operator_queue.py`
  - `src/glassbox/runtime/operator_queue_changeset_items.py`
  - `src/glassbox/runtime/changeset_detail.py`
  - `tests/unit/test_changeset_workup.py`
  - `tests/unit/test_session_query_derivation.py`
- Work:
  - characterize current changeset visibility in queue and identify whether
    gaps are refactor-only derivation gaps or product follow-ups
  - if already supported by existing aggregate inputs, move changeset review,
    verification, stale inventory, unresolved feedback, and handoff blockers
    into a changeset item helper
  - do not invent new queue authority or new persistence in this task
- Deliverables:
  - explicit changeset queue source boundary or documented accepted gap
- Validation:
  - `uv run pytest tests/unit/test_changeset_workup.py -k queue`
  - `uv run pytest tests/unit/test_session_query_derivation.py -k queue`

---

## Phase 114: Core Operator-Flow Domain Strategy

### GBX-R840: Define Core Operator-Flow Model Domain Strategy

- Status: `DONE`
- Dependencies: GBX-R800
- Target files:
  - [refactor-boundaries.md](./refactor-boundaries.md)
  - `src/glassbox/core/models.py`
  - `src/glassbox/core/types.py`
  - `src/glassbox/core/events.py`
  - `tests/unit/test_core_models.py`
  - `tests/unit/test_core_events.py`
- Work:
  - document when next-action, queue, evidence graph, maintenance,
    verification plan, and recovery playbook models should move into core
    domain modules versus staying in broad public core surfaces
  - do not split core files mechanically during this task
  - identify import compatibility requirements if a later task extracts
    operator-flow model or enum families
- Deliverables:
  - explicit model/type/event domain strategy for future operator-flow growth
  - no behavior change
- Validation:
  - `uv run pytest tests/unit/test_core_models.py tests/unit/test_core_events.py`
  - `uv run pytest tests/unit/test_release_candidate_docs.py -q`

### GBX-R841: Extract Core Next-Action And Queue Models Behind Compatibility Re-Exports

- Status: `DONE`
- Dependencies: GBX-R840, GBX-R830
- Target files:
  - `src/glassbox/core/models.py`
  - `src/glassbox/core/models_operator_flow.py`
  - `src/glassbox/core/types.py`
  - `src/glassbox/core/types_operator_flow.py`
  - `src/glassbox/core/__init__.py`
  - `tests/unit/test_core_models.py`
  - `tests/unit/architecture_guardrails/test_python_facades.py`
- Work:
  - move `NextAction*`, `OperatorQueue*`, and related queue enum contracts
    into operator-flow core modules if the strategy says extraction is now
    justified
  - preserve `glassbox.core` public imports through compatibility re-exports
  - keep runtime, web, CLI, and tests importing from the stable public surface
    unless a narrower import path is deliberately chosen
- Deliverables:
  - smaller core model/type files with stable public exports
- Validation:
  - `uv run pytest tests/unit/test_core_models.py`
  - `uv run pytest tests/unit/test_session_query_derivation.py -k queue`
  - `uv run pytest tests/unit/architecture_guardrails`

### GBX-R842: Extract Core Evidence Graph, Maintenance, And Verification Models

- Status: `DONE`
- Dependencies: GBX-R840, GBX-R810, GBX-R820
- Target files:
  - `src/glassbox/core/models.py`
  - `src/glassbox/core/models_evidence_graph.py`
  - `src/glassbox/core/models_verification_plan.py`
  - `src/glassbox/core/types.py`
  - `src/glassbox/core/types_evidence_graph.py`
  - `src/glassbox/core/types_verification_plan.py`
  - `src/glassbox/core/__init__.py`
  - `tests/unit/test_core_models.py`
  - `tests/unit/test_evidence_graph.py`
  - `tests/unit/test_changeset_verification_readiness.py`
- Work:
  - move evidence graph, maintenance cue, and verification plan contracts into
    domain modules if extraction is justified after runtime helper splits
  - preserve public imports and OpenAPI model generation behavior
  - keep event payloads stable and avoid event schema changes
- Deliverables:
  - core domain modules aligned with v16 operator-flow contracts
- Validation:
  - `uv run pytest tests/unit/test_core_models.py`
  - `uv run pytest tests/unit/test_evidence_graph.py`
  - `uv run pytest tests/unit/test_changeset_verification_readiness.py`
  - `uv run pytest tests/integration/test_openapi_schema.py`

---

## Phase 115: Web And Frontend Operator-Flow Cleanup

### GBX-R850: Split Session Aggregate Queue API Builders

- Status: `DONE`
- Dependencies: GBX-R830
- Target files:
  - `src/glassbox/web/session_api_aggregate.py`
  - `src/glassbox/web/session_api_aggregate_models.py`
  - `src/glassbox/web/session_api_aggregate_builders.py`
  - `src/glassbox/web/routes/session_route_queries.py`
  - `tests/integration/test_web_session_aggregate.py`
  - `tests/integration/test_openapi_schema.py`
- Work:
  - keep response model shape stable while moving aggregate response models and
    builders into focused modules if the facade grows further
  - keep route helpers free of queue sorting, evidence summary, and model
    conversion internals
  - preserve OpenAPI schema shape unless explicitly changed
- Deliverables:
  - session aggregate web facade over model and builder helpers
- Validation:
  - `uv run pytest tests/integration/test_web_session_aggregate.py`
  - `uv run pytest tests/integration/test_openapi_schema.py`
  - `pnpm --dir frontend api:generate`
  - `pnpm --dir frontend typecheck`

### GBX-R851: Split Changeset Verification And Evidence Graph API Builders

- Status: `DONE`
- Dependencies: GBX-R810, GBX-R820
- Target files:
  - `src/glassbox/web/changeset_api_builders_detail.py`
  - `src/glassbox/web/changeset_api_builders_verification.py`
  - `src/glassbox/web/changeset_api_builders_evidence_graph.py`
  - `src/glassbox/web/routes/changeset_route_actions.py`
  - `src/glassbox/web/routes/changeset_route_evidence_graph.py`
  - `tests/integration/test_web_changeset_routes.py`
  - `tests/integration/test_openapi_schema.py`
- Work:
  - move verification plan response building into a verification builder
  - move evidence graph route response shaping into an evidence graph builder
    or route-local query helper
  - keep route declarations readable and response models stable
  - preserve preview-only and non-publication wording
- Deliverables:
  - changeset web builders split by detail, verification, and graph concerns
- Validation:
  - `uv run pytest tests/integration/test_web_changeset_routes.py -k "verification or evidence"`
  - `uv run pytest tests/integration/test_openapi_schema.py`
  - `pnpm --dir frontend api:generate`

### GBX-R852: Split Dashboard Operator Queue Lane Components

- Status: `DONE`
- Dependencies: GBX-R830, GBX-R850
- Target files:
  - `frontend/components/console/workspace-overview/operator-queue-lanes.tsx`
  - `frontend/components/console/workspace-overview/operator-queue-models.ts`
  - `frontend/components/console/workspace-overview/operator-queue-row.tsx`
  - `frontend/components/console/workspace-overview/operator-queue-links.ts`
  - `frontend/components/console/workspace-overview/operator-queue-format.ts`
  - `frontend/tests/workspace-overview.test.ts`
- Work:
  - move lane descriptors and count helpers into a model module
  - move queue row rendering into a row component
  - move target and evidence deep-link construction into a pure link helper
  - move severity, priority, freshness, limitation, and safe-action text into a
    formatting helper
  - preserve current copy, responsive layout, keyboard behavior, and route
    behavior
- Deliverables:
  - queue cockpit UI split into descriptors, rows, links, and formatting
    helpers
- Validation:
  - `pnpm --dir frontend test -- workspace-overview.test.ts`
  - `pnpm --dir frontend typecheck`
  - `pnpm --dir frontend lint`

### GBX-R853: Split Dashboard Evidence Graph Panel Components

- Status: `TODO`
- Dependencies: GBX-R810, GBX-R851
- Target files:
  - `frontend/components/console/evidence-graph-panel.tsx`
  - `frontend/components/console/evidence-graph/summary.tsx`
  - `frontend/components/console/evidence-graph/claims.tsx`
  - `frontend/components/console/evidence-graph/nodes.tsx`
  - `frontend/components/console/evidence-graph/relationships.tsx`
  - `frontend/components/console/evidence-graph/format.ts`
  - `frontend/tests/session-inspector.test.ts`
  - `frontend/tests/changeset-console.test.tsx`
- Work:
  - keep `EvidenceGraphPanel` as the component entrypoint
  - move summary filters, claim rows, node rows, edge rows, limitations, anchor
    IDs, badge variants, and formatting into focused helpers
  - preserve graph truncation copy, reviewer-safe visibility labels, and sparse
    historical-session behavior
- Deliverables:
  - evidence graph dashboard component family that can grow without one dense
    component
- Validation:
  - `pnpm --dir frontend test -- session-inspector.test.ts changeset-console.test.tsx`
  - `pnpm --dir frontend typecheck`
  - `pnpm --dir frontend lint`

### GBX-R854: Split Dashboard Verification Plan Workflow Components And Store Actions

- Status: `TODO`
- Dependencies: GBX-R820, GBX-R851
- Target files:
  - `frontend/components/console/changeset/verification.tsx`
  - `frontend/components/console/changeset/verification-plan-table.tsx`
  - `frontend/components/console/changeset/verification-plan-actions.tsx`
  - `frontend/components/console/changeset/verification-plan-format.ts`
  - `frontend/stores/changeset-store-review-actions.ts`
  - `frontend/stores/changeset-store-verification-actions.ts`
  - `frontend/tests/changeset-console.test.tsx`
- Work:
  - move verification plan table and entry state rendering into a table
    component
  - move selection, run, skip, accepted-risk, retry, and supersede controls
    into action components and store action helpers
  - keep API calls in stores and local form state in components
  - preserve disabled action states, confirmation behavior, non-claims, and
    current error messages
- Deliverables:
  - verification plan cockpit split by rendering, action controls, formatting,
    and transport helpers
- Validation:
  - `pnpm --dir frontend test -- changeset-console.test.tsx`
  - `pnpm --dir frontend typecheck`
  - `pnpm --dir frontend lint`

---

## Phase 116: Release-Gate And Package Evidence Cleanup

### GBX-R860: Split V16 Release-Gate Stage Assembly By Evidence Family

- Status: `TODO`
- Dependencies: GBX-R801
- Target files:
  - `scripts/validate_v16_release_gate.py`
  - `scripts/v16_release_gate_helpers.py`
  - `scripts/v16_release_gate_stages.py`
  - `scripts/v16_release_gate_advisory.py`
  - `scripts/v16_release_gate_summary.py`
  - `tests/unit/test_release_candidate_docs.py`
- Work:
  - keep `validate_v16_release_gate.py` as the operator entrypoint
  - move runtime, CLI/API, frontend, package, eval, docs, installed-smoke, and
    advisory evidence stage construction into helper families
  - preserve dry-run output, stage names, blocking/advisory separation,
    summary JSON shape, and skipped advisory evidence posture
- Deliverables:
  - v16 release-gate helper ownership that can be reviewed by evidence family
- Validation:
  - `uv run python scripts/validate_v16_release_gate.py --dry-run`
  - `uv run pytest tests/unit/test_release_candidate_docs.py -q`

### GBX-R861: Centralize V16 Advisory Evidence Summary Rows

- Status: `TODO`
- Dependencies: GBX-R860
- Target files:
  - `scripts/v16_release_gate_advisory.py`
  - `docs/v16-release-gate.md`
  - `docs/v16-flow-cockpit-evidence.md`
  - `docs/v16-dogfooding-summary.md`
  - `tests/unit/test_release_candidate_docs.py`
- Work:
  - keep provider canaries, browser walkthroughs, accessibility notes,
    dogfooding, and manual release notes advisory by default
  - move advisory evidence row shaping and skipped-evidence wording into one
    helper
  - preserve deterministic release authority and non-claims
- Deliverables:
  - one release-gate owner for v16 advisory evidence summary copy
- Validation:
  - `uv run python scripts/validate_v16_release_gate.py --dry-run`
  - `uv run pytest tests/unit/test_release_candidate_docs.py -q`

### GBX-R862: Refresh Package And Installed-Smoke Refactor Guardrails

- Status: `TODO`
- Dependencies: GBX-R860
- Target files:
  - `scripts/validate_package_contents.py`
  - `scripts/validate_frontend_release_assets.py`
  - `scripts/validate_installed_wheel_smoke.py`
  - `tests/unit/test_packaging_metadata.py`
  - `docs/release-packaging.md`
- Work:
  - verify v16 docs, eval fixtures, release-gate helper modules, generated API
    files, and static dashboard assets remain packaged after helper splits
  - keep package validation deterministic and local
  - update docs only if package evidence ownership changes materially
- Deliverables:
  - package and installed-smoke checks aligned with the post-v16 helper split
- Validation:
  - `uv run pytest tests/unit/test_packaging_metadata.py`
  - `uv run python scripts/validate_package_contents.py`
  - `uv run python scripts/validate_frontend_release_assets.py`

---

## Phase 117: Guardrails, Docs, And Validation Closeout

### GBX-R870: Refresh Refactor Documentation And Docs Hub References

- Status: `TODO`
- Dependencies: GBX-R802, GBX-R810, GBX-R820, GBX-R830, GBX-R850
- Target files:
  - [architecture.md](./architecture.md)
  - [refactor-boundaries.md](./refactor-boundaries.md)
  - [README.md](./README.md)
  - [refactor-v16.md](./refactor-v16.md)
  - `README.md`
- Work:
  - update architecture and boundary docs with completed post-v16 helper
    owners
  - update docs hub links if public refactor guidance changes
  - record accepted compatibility shims and product follow-up candidates
  - keep docs aligned with actual command help and module names
- Deliverables:
  - source-linked post-v16 refactor closeout notes
- Validation:
  - `uv run pytest tests/unit/test_release_candidate_docs.py -q`
  - `uv run pytest tests/unit/architecture_guardrails`

### GBX-R871: Run Post-V16 Refactor Confidence Sweep

- Status: `TODO`
- Dependencies: GBX-R870
- Target files:
  - tests, docs, scripts, frontend as needed
- Work:
  - run focused operator-flow and refactor-sensitive validation
  - record any accepted validation gaps in this file before marking the
    roadmap complete
  - do not refresh deterministic eval baselines unless a task explicitly
    changed behavior and follows the established eval refresh workflow
- Deliverables:
  - validation summary sufficient for post-v16 refactor closeout
  - updated task statuses when the roadmap is complete
- Validation:
  - `uv run ruff format --check .`
  - `uv run ruff check .`
  - `uv run ty check`
  - `uv run pytest -n auto --dist loadfile`
  - `pnpm --dir frontend lint`
  - `pnpm --dir frontend typecheck`
  - `pnpm --dir frontend test`
  - `pnpm --dir frontend build`
  - `uv run python scripts/validate_v16_release_gate.py --dry-run`

## Accepted Behavior Gaps Recorded During GBX-R801

These are current behavior observations captured before moving code. They are
not product changes by themselves, and later tasks may deliberately narrow them
when the task text explicitly says so:

- verification plan previews can currently show separate rows when the same
  command is recommended by repository-intelligence recipes and changeset
  readiness; GBX-R820 owns the follow-up coalescing decision for direct recipe
  plus readiness duplicates
- workspace operator queue coverage remains session, runtime, and maintenance
  oriented; GBX-R833 confirmed that the current aggregate does not load
  changeset detail, verification, inventory, unresolved feedback, or handoff
  inputs, so `operator_queue_changeset_items.py` is an explicit empty boundary
  and changeset-level queue rows remain a product follow-up

## Accepted Product Follow-Up Candidates

These findings are useful context for refactor planning, but they are not
refactor-only tasks unless a later roadmap explicitly chooses to change
behavior:

- decide whether duplicate verification plan rows should be coalesced by
  command identity, source family priority, evidence references, or a richer
  canonical check identity
- decide whether changeset-level review and verification blockers should appear
  in the workspace operator queue independently of session aggregate rows
- decide whether evidence graph support should include repository-intelligence
  freshness nodes for every path-to-verification recommendation
- decide whether reviewer-safe bundle export should expose a compact graph
  diff between two changeset states
- decide whether dashboard evidence graph exploration should add search,
  filters, and graph neighborhood paging beyond the current bounded panels
- decide whether maintenance cues should gain optional remediation wizards in
  the dashboard or TUI while keeping commands explicit
- decide whether queue items should support operator dismissal records for
  advisory items that are not canonical decisions
- decide whether skipped verification checks should participate in future
  release-candidate claims when paired with explicit accepted-risk evidence

Product follow-ups should preserve the v16 non-goals unless a future product
contract explicitly changes them.

## Accepted Compatibility Shims

The following facades are acceptable during this roadmap as long as they remain
thin and delegate to owned helpers after the relevant phase completes:

- `src/glassbox/runtime/evidence_graph.py`: evidence graph public facade over
  graph builders, changeset graph helpers, session graph helpers, query
  helpers, summaries, and neighborhood traversal.
- `src/glassbox/runtime/verification_plan_builder.py`: verification plan
  public builder over identity, recommendation-source, readiness, manual-only,
  and skipped-check helper modules.
- `src/glassbox/runtime/operator_queue.py`: operator queue public aggregator
  over session, runtime, maintenance, changeset, sorting, dedupe, and count
  helpers.
- `src/glassbox/core/models.py`, `src/glassbox/core/types.py`, and
  `src/glassbox/core/events.py`: broad public core surfaces that may re-export
  domain model/type/event modules while compatibility matters.
- `src/glassbox/web/session_api_aggregate.py`: session aggregate API facade
  over queue response models and builders.
- `src/glassbox/web/changeset_api_builders_detail.py`: changeset detail
  builder facade over verification and evidence graph response helpers.
- `src/glassbox/web/routes/session_route_queries.py`: session route query
  helper facade over aggregate, graph, and page-query helpers.
- `src/glassbox/web/routes/changeset_route_actions.py`: changeset action
  helper facade over verification, workup, evidence graph, feedback, and
  readiness helpers.
- `frontend/components/console/workspace-overview/operator-queue-lanes.tsx`:
  dashboard operator queue entrypoint over lane, row, link, and formatting
  helpers.
- `frontend/components/console/evidence-graph-panel.tsx`: dashboard evidence
  graph entrypoint over summary, claims, nodes, relationships, limitations,
  and formatting helpers.
- `frontend/components/console/changeset/verification.tsx`: dashboard
  verification plan entrypoint over table, action, and formatting helpers.
- `frontend/stores/changeset-store-review-actions.ts`: compatibility store
  action surface over review and verification action helpers.
- `scripts/validate_v16_release_gate.py`: operator release-gate entrypoint over
  v16 stage, advisory, summary, dry-run, package, and installed-smoke helpers.
- `tests/unit/test_architecture_guardrails.py`: legacy validation entrypoint
  that imports the split architecture guardrail modules by boundary family.
