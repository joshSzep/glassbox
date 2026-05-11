# Glassbox Refactor v15 Tasks

For the docs hub and operator guides, start at [README.md](./README.md). This
file is the next behavior-preserving refactor roadmap after
[refactor-v14.md](./refactor-v14.md). It starts from the completed v15
repository-intelligence milestone and targets the code paths that grew while
v15 added repository intelligence v2, path-to-verification guidance, command
recipes, memory-derived repository cues, freshness posture, dashboard
repository surfaces, bounded prompt context, replay drift semantics, and the
v15 release gate.

## Purpose

This document defines a post-v15 refactor roadmap for the current Glassbox
codebase.

It follows the execution style of [refactor-v1.md](./refactor-v1.md),
[refactor-v8.md](./refactor-v8.md), [refactor-v10.md](./refactor-v10.md),
[refactor-v11.md](./refactor-v11.md), [refactor-v13.md](./refactor-v13.md),
and [refactor-v14.md](./refactor-v14.md): explicit dependencies, small
vertical slices, concrete deliverables, and validation requirements attached
directly to the work.

This roadmap is not a product-feature roadmap. It exists to keep the current
local-first, event-sourced architecture easy to evolve by:

- separating v15 repository-intelligence derivation from CLI formatting,
  runtime refresh orchestration, API payload shaping, dashboard rendering, and
  prompt-use evidence recording
- keeping repository snapshots, topology, command recipes, path inspection,
  path-to-verification guidance, memory-derived repository facts, freshness
  posture, and context summaries independently reviewable
- preserving current CLI, TUI, dashboard, API, replay, eval, package,
  projection, and release-gate behavior unless a later task explicitly changes
  a contract
- tightening architecture guardrails around the modules that grew after the
  v15 release-candidate milestone
- avoiding line-count-only splits in model-heavy, event-heavy, generated,
  fixture-heavy, or public compatibility surfaces

## Refactor Direction

The post-v14 refactor successfully split review-loop maturity surfaces before
v15 expanded repository intelligence. The v15 milestone then made repository
awareness richer by adding:

- repository intelligence snapshot schema v2
- deterministic layout discovery for roots, packages, generated paths,
  policy-sensitive paths, command recipes, owner hints, subsystems, and release
  surfaces
- path-to-verification guidance tied to eval metadata, topology, command
  recipes, stale evidence, and changesets
- memory-derived repository intelligence that remains review-gated and
  provenance-backed
- shared freshness cues for index, topology, command recipes, eval metadata,
  memory references, and release surfaces
- CLI, API, dashboard, changeset, review brief, handoff, context, replay, eval,
  package, and release-gate surfaces for repository intelligence

The implementation is coherent, but v15 concentrated new behavior in a handful
of places. The next refactor should keep those contracts dependable before a
future milestone expands repository intelligence again.

Current pressure points include:

- `src/glassbox/cli/repository_commands.py`: repository command dispatch,
  refresh orchestration, runtime context wiring, path payload shaping, JSON
  output, human formatting, and memory-candidate handling live in one command
  module.
- `src/glassbox/runtime/repository_intelligence_layout.py`: manifest parsing,
  package-boundary derivation, generated and policy-sensitive path hints,
  command recipe extraction, owner hints, subsystem hints, release surfaces,
  dedupe, slugging, digesting, and provenance helpers live in one runtime
  module.
- `src/glassbox/runtime/repository_index_builder.py` and
  `src/glassbox/runtime/background_job_handlers.py`: immediate and background
  repository-intelligence refresh paths both know how to combine index,
  topology, active memory, managed artifacts, and summary output.
- `src/glassbox/runtime/runtime_context_derivation.py`: the main function is
  named like a pure derivation helper, but it also records
  `WorkspaceMemoryUsedInContext` events as a side effect.
- `src/glassbox/runtime/eval_recommendation_repository_intelligence.py`:
  repository-intelligence recommendation enrichment mixes snapshot loading,
  freshness warnings, subsystem/owner/surface/recipe matching, metadata
  assembly, reason mutation, and safe-command shaping.
- `src/glassbox/web/repository_intelligence_api.py` and
  `src/glassbox/web/routes/repository_intelligence.py`: v15 response models,
  response builders, and route-local query orchestration are useful but dense
  enough to merit builder-family ownership if more fields land.
- `frontend/components/console/knowledge-autonomy/repository-panels.tsx` and
  `frontend/stores/knowledge-store.ts`: repository dashboard state, local view
  state, query loading, path inspection, command recipes, freshness cues,
  memory candidates, and presentation helpers are becoming the frontend
  equivalent of earlier console pressure points.
- `tests/unit/test_architecture_guardrails.py`: guardrail coverage has become
  a large architecture test suite in its own right and should split by
  backend, frontend, facade, and refactor-era concern.
- `src/glassbox/core/events.py` and `src/glassbox/core/models.py`: still
  acceptable broad model-heavy surfaces, but v15 added enough repository
  intelligence models that a future expansion should use a domain module
  strategy rather than growing these files indefinitely.

The post-v15 refactor thesis is:

- keep canonical events and managed artifacts as the source of truth
- keep repository intelligence local, rebuildable, freshness-aware,
  provenance-backed, and advisory by default
- keep runtime query and recommendation helpers transport-agnostic
- keep web response models and frontend generated API types as transport
  contracts, not business-logic owners
- keep frontend stores responsible for transport and components responsible for
  presentation and local interaction state
- move repository-intelligence layout discovery, command-recipe extraction,
  path inspection, refresh orchestration, prompt-use evidence recording,
  recommendation enrichment, CLI output formatting, and dashboard panel
  derivation into focused owner modules
- preserve compatibility facades where imports, commands, routes, generated
  API types, stores, or component entrypoints rely on them
- add guardrails only when the intended repair is local, obvious, and backed by
  an explicit owner module

## Agent Execution Rules

These rules apply to every task in this file.

1. Respect dependency order. Do not start a task until its dependencies are
   complete unless the task explicitly says it can proceed in parallel.
2. Preserve current behavior by default. Refactor tasks should not
   intentionally change CLI semantics, TUI slash-command behavior, dashboard
   workflows, API payloads, replay outcomes, eval outcomes, event ordering,
   projection behavior, package contents, release-gate behavior, or
   repository-intelligence advisory claims unless the task explicitly includes
   that contract change.
3. Treat `events` as the canonical source of truth. Query services, route
   helpers, stores, frontend derivation, UI projections, repository
   intelligence snapshots, and prompt fragments remain derived from canonical
   events, typed API responses, managed artifacts, local source files, or
   rebuildable projection tables.
4. Repair architectural duplication before splitting files mechanically. If
   two modules shape the same path inspection, command recipe, freshness cue,
   memory-reference posture, refresh summary, or safe next action, extract the
   shared boundary first.
5. Prefer extractions with thin compatibility shims over broad rewrites. Keep
   diffs incremental and executable.
6. Keep public facades stable unless a task explicitly changes the import,
   route, API, command, store, or component contract.
7. Do not introduce new framework layers unless they remove a real current
   coupling in the codebase.
8. Do not move API calls into React components. Frontend stores own transport;
   components own presentation and local interaction state; pure helper
   modules own derivation and formatting.
9. Do not move HTTP response models or FastAPI dependencies into runtime query
   or recommendation services. Runtime services stay transport-agnostic.
10. Do not make repository intelligence stronger than its current advisory
    contract. It can recommend, explain, and cite evidence; it cannot claim
    verification success, reviewer acceptance, owner assignment, publication
    readiness, or command approval.
11. Do not add hosted code search, external vector-store authority,
    provider-side hidden memory, automatic owner assignment, automatic staging,
    committing, pushing, pull request creation, merging, deployment, or
    publishing as part of refactor-only work.
12. Every refactor task automatically includes:
    - automated tests for moved or extracted behavior where practical
    - `ruff` formatting and lint compliance for touched Python code
    - `ty` typecheck compliance for touched Python code
    - focused `pytest` coverage for touched runtime, store, CLI, web, replay,
      eval, daemon, repository intelligence, topology, workspace memory,
      changeset, review, handoff, and release-gate behavior
    - frontend lint, typecheck, tests, and build when the task touches
      dashboard code, generated API types, packaged static assets, route
      assumptions, or frontend stores
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
- repository-intelligence claims remain backed by deterministic local inputs,
  canonical events, managed artifacts, typed API responses, or eval fixtures
- stale or missing repository intelligence remains visible rather than hidden
- no repository intelligence source materially affects model prompts without an
  inspectable context snapshot and replay fingerprint story
- the refactor does not weaken the local-first, event-sourced, replay-aware
  architecture described in [architecture.md](./architecture.md)
- the refactor does not weaken the v15 repository-intelligence and memory
  contracts described in
  [v15-repository-intelligence-contract.md](./v15-repository-intelligence-contract.md),
  [repository-intelligence-index.md](./repository-intelligence-index.md),
  [runtime-context.md](./runtime-context.md), and
  [workspace-memory.md](./workspace-memory.md)

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
uv run python scripts/validate_v15_release_gate.py --dry-run
```

During incremental refactor work, use narrower commands when possible:

```bash
uv run pytest tests/unit/test_repository_index.py
uv run pytest tests/unit/test_eval_recommendations.py
uv run pytest tests/unit/test_context_builder.py tests/unit/test_workspace_memory_capture.py
uv run pytest tests/integration/test_cli_repository_commands.py
uv run pytest tests/integration/test_web_repository_intelligence_routes.py
uv run pytest tests/unit/test_architecture_guardrails.py
pnpm --dir frontend test -- knowledge-autonomy-console.test.tsx workspace-overview.test.tsx api-client.test.ts
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

## Current State

The v15 release-candidate track added repository intelligence v2:

- local schema-versioned repository intelligence snapshots
- package boundaries, source roots, test roots, docs roots, generated paths,
  policy-sensitive paths, dependency manifests, command recipes, owner hints,
  subsystems, release surfaces, and memory references
- shared freshness and drift posture for index, topology, recipes, memory,
  eval metadata, and release surfaces
- path inspection and path-to-verification recommendations across CLI, API,
  dashboard, changesets, review briefs, handoff readiness, context, replay,
  evals, and release gates
- background refresh support for derived repository intelligence
- deterministic repository-intelligence eval fixtures and v15 release-gate
  coverage

The implementation is coherent, but v15 concentrated new behavior in several
modules. The next refactor should keep those contracts dependable before
another milestone expands repository intelligence or turns more advisory cues
into workflow surfaces.

Large files that are primarily model-heavy, generated, or test fixtures are not
automatically refactor targets. In particular, `core/events.py`,
`core/models.py`, generated frontend API types, generated OpenAPI JSON,
fixture-heavy frontend tests, and broad integration tests should be split only
when a real ownership or review problem appears.

## Milestone Map

The intended post-v15 refactor milestone order is:

1. post-v15 boundary refresh and characterization
2. repository CLI and query boundary cleanup
3. repository-intelligence layout decomposition
4. refresh orchestration and context-use side-effect cleanup
5. recommendation enrichment and freshness cleanup
6. web and frontend repository-intelligence cleanup
7. guardrails, core-domain strategy, docs, and validation closeout

Each phase below corresponds to one concrete refactor milestone.

## Task Graph

---

## Phase 100: Post-V15 Boundary Refresh And Characterization

### GBX-R700: Define Post-V15 Refactor Boundary Map

- Status: `DONE`
- Dependencies: none
- Target files:
  - [refactor-boundaries.md](./refactor-boundaries.md)
  - [architecture.md](./architecture.md)
  - [refactor-v15.md](./refactor-v15.md)
  - [test_architecture_guardrails.py](../tests/unit/test_architecture_guardrails.py)
- Work:
  - document the intended post-v15 compatibility facades and helper owners
  - name repository CLI, repository-intelligence layout discovery, refresh
    orchestration, runtime context-use recording, eval recommendation
    enrichment, web repository-intelligence builders, frontend repository
    panels, knowledge store, and architecture guardrails as first pressure
    points
  - distinguish model-heavy public surfaces from mixed-responsibility modules
    that should be split
  - keep v15 repository-intelligence, memory, context, and release-authority
    non-goals explicit
- Deliverables:
  - documented boundary map for runtime, CLI, web, frontend, guardrail, and
    core-domain surfaces
  - initial guardrail expectations for post-v15 pressure points where intended
    owner modules are already clear
- Validation:
  - `uv run pytest tests/unit/test_architecture_guardrails.py`
  - `uv run pytest tests/unit/test_release_candidate_docs.py -q`

### GBX-R701: Characterize Current Repository Intelligence Behavior

- Status: `DONE`
- Dependencies: GBX-R700
- Target files:
  - `tests/unit/test_repository_index.py`
  - `tests/unit/test_eval_recommendations.py`
  - `tests/unit/test_context_builder.py`
  - `tests/unit/test_workspace_memory_capture.py`
  - `tests/integration/test_cli_repository_commands.py`
  - `tests/integration/test_web_repository_index_routes.py`
  - `frontend/tests/knowledge-autonomy-console.test.tsx`
  - `frontend/tests/workspace-overview.test.ts`
- Work:
  - identify highest-risk current behavior before movement begins
  - add characterization coverage where moved behavior is not already asserted
  - prefer narrow tests around path inspection, command recipe filtering,
    freshness cue copy, stale snapshot posture, memory-candidate no-session
    handling, background refresh summary, prompt-use memory recording, and
    dashboard repository state transitions
  - explicitly record accepted behavior gaps that should not block
    refactor-only movement
- Deliverables:
  - current behavior coverage sufficient for CLI, runtime, and frontend
    extraction tasks
  - accepted-gap list for behavior that is intentionally left unchanged during
    refactor-only work
- Accepted gaps:
  - `repo memory-candidates` without `--session` still uses the current
    unfriendly no-session failure until GBX-R712 owns the deliberate copy and
    exit-code polish.
  - The web repository intelligence route tests live in
    `test_web_repository_index_routes.py` today because repository index and
    repository intelligence routes still share the integration fixture.
  - Frontend characterization uses `workspace-overview.test.ts`; no `.tsx`
    route-specific companion exists for that surface today.
- Validation:
  - `uv run pytest tests/unit/test_repository_index.py`
  - `uv run pytest tests/unit/test_eval_recommendations.py -k repository`
  - `uv run pytest tests/unit/test_context_builder.py -k intelligence`
  - `uv run pytest tests/integration/test_cli_repository_commands.py`
  - `uv run pytest tests/integration/test_web_repository_intelligence_routes.py`
  - `pnpm --dir frontend test -- knowledge-autonomy-console.test.tsx workspace-overview.test.tsx`

### GBX-R702: Add Post-V15 Facade Guardrails After First Extraction

- Status: `DONE`
- Dependencies: GBX-R710, GBX-R720, GBX-R730
- Target files:
  - `tests/unit/test_architecture_guardrails.py`
  - [refactor-boundaries.md](./refactor-boundaries.md)
- Work:
  - add facade line-count and import-prefix expectations only after helper
    modules exist
  - assert that repository CLI, repository-intelligence runtime, context-use,
    web, frontend, and guardrail facades delegate to intended owner modules
  - keep guardrails narrow enough that they catch regression without freezing
    legitimate implementation detail
- Deliverables:
  - post-extraction architecture tests for the new v15 helper owners
- Validation:
  - `uv run pytest tests/unit/test_architecture_guardrails.py`

---

## Phase 101: Repository CLI And Query Boundary Cleanup

### GBX-R710: Split Repository Command Handler Families

- Status: `DONE`
- Dependencies: GBX-R701
- Target files:
  - `src/glassbox/cli/repository_commands.py`
  - `src/glassbox/cli/repository_command_status.py`
  - `src/glassbox/cli/repository_command_refresh.py`
  - `src/glassbox/cli/repository_command_inspection.py`
  - `src/glassbox/cli/repository_command_memory.py`
  - `src/glassbox/cli/repository_command_formatters.py`
  - `tests/integration/test_cli_repository_commands.py`
- Work:
  - keep `repository_commands.py` as the command-family dispatcher
  - move status and stale commands into a status owner
  - move immediate and background refresh commands into a refresh owner
  - move path, recommend, recipes, subsystem, index, and topology inspection
    commands into inspection owners where practical
  - move memory-candidate command behavior into a memory owner
  - move human output formatting into CLI-only formatter helpers
  - preserve command names, arguments, JSON payloads, exit-code behavior, and
    command-guide expectations
- Deliverables:
  - repository CLI handlers that can be reviewed by operator workflow family
  - `repository_commands.py` preserved as the compatibility import surface
    over status, refresh, inspection, memory, and formatter helpers
- Validation:
  - `uv run pytest tests/integration/test_cli_repository_commands.py`
  - `uv run pytest tests/unit/test_command_guide.py`
  - `uv run glassbox command tree`

### GBX-R711: Deduplicate CLI Path Inspection With Runtime Query Helpers

- Status: `DONE`
- Dependencies: GBX-R710
- Target files:
  - `src/glassbox/cli/repository_command_inspection.py`
  - `src/glassbox/runtime/repository_intelligence_queries.py`
  - `src/glassbox/web/repository_intelligence_api.py`
  - `tests/unit/test_repository_index.py`
  - `tests/integration/test_cli_repository_commands.py`
  - `tests/integration/test_web_repository_intelligence_routes.py`
- Work:
  - remove duplicate CLI-local path inspection selection logic
  - use `inspect_repository_intelligence_path` and
    `workspace_relative_repository_path` as the shared transport-agnostic path
    query boundary
  - keep CLI JSON shape stable through a CLI payload adapter if needed
  - keep web response builders consuming the same runtime query result
- Deliverables:
  - one runtime owner for path inspection matching and safe next actions
  - CLI and web presentation adapters over the shared query result
- Validation:
  - `uv run pytest tests/unit/test_repository_index.py -k path`
  - `uv run pytest tests/integration/test_cli_repository_commands.py -k path`
  - `uv run pytest tests/integration/test_web_repository_intelligence_routes.py -k path`

### GBX-R712: Improve Repository Memory-Candidate Command Error Copy

- Status: `DONE`
- Dependencies: GBX-R710
- Target files:
  - `src/glassbox/cli/repository_command_memory.py`
  - `src/glassbox/cli/parser_repository.py`
  - `tests/integration/test_cli_repository_commands.py`
  - [v15-dogfooding-summary.md](./v15-dogfooding-summary.md)
- Work:
  - make `repo memory-candidates` without `--session` fail with explicit
    guidance instead of `unknown session_id: None`
  - point operators to `--session SESSION_ID` and
    `glassbox session list --json --cwd .`
  - keep JSON and exit-code behavior deliberate and tested
  - treat this as the only behavior-polish task in the refactor roadmap because
    it is an accepted v15 dogfooding follow-up
- Deliverables:
  - friendlier no-session operator copy
  - tests that lock the intended CLI behavior
- Validation:
  - `uv run pytest tests/integration/test_cli_repository_commands.py -k memory`
  - `uv run pytest tests/unit/test_release_candidate_docs.py -q`

---

## Phase 102: Repository-Intelligence Layout Decomposition

### GBX-R720: Split Layout Discovery Models And Common Helpers

- Status: `DONE`
- Dependencies: GBX-R701
- Target files:
  - `src/glassbox/runtime/repository_intelligence_layout.py`
  - `src/glassbox/runtime/repository_intelligence_layout_models.py`
  - `src/glassbox/runtime/repository_intelligence_layout_common.py`
  - `tests/unit/test_repository_index.py`
- Work:
  - move `RepositoryIntelligenceLayout` and shared helper concepts into a
    model/common module
  - move slugging, digest, provenance, dedupe, safe path, JSON, and TOML helper
    behavior out of the main layout coordinator
  - keep helper modules free of CLI, web, store, and frontend imports
- Deliverables:
  - layout coordinator that can delegate to focused extraction owners
  - common helper coverage for stable IDs, digests, provenance, and path
    behavior
- Validation:
  - `uv run pytest tests/unit/test_repository_index.py -k intelligence`
  - `uv run ruff check src/glassbox/runtime/repository_intelligence_layout*.py`
  - `uv run ty check src/glassbox/runtime/repository_intelligence_layout.py`

### GBX-R721: Split Manifest, Package, Root, And Generated-Path Discovery

- Status: `DONE`
- Dependencies: GBX-R720
- Target files:
  - `src/glassbox/runtime/repository_intelligence_layout.py`
  - `src/glassbox/runtime/repository_intelligence_layout_packages.py`
  - `src/glassbox/runtime/repository_intelligence_layout_paths.py`
  - `tests/unit/test_repository_index.py`
- Work:
  - move Python and Node package-boundary derivation into a package owner
  - move source/test/doc root, generated path, ignored path, and
    policy-sensitive path hints into a path owner
  - preserve current package IDs, confidence, provenance, generated-path
    limitations, and excluded-path posture
- Deliverables:
  - package/root discovery independently reviewable from command recipe and
    release-surface discovery
- Validation:
  - `uv run pytest tests/unit/test_repository_index.py -k "package or generated or policy"`

### GBX-R722: Split Command Recipe Extraction By Source Family

- Status: `DONE`
- Dependencies: GBX-R720
- Target files:
  - `src/glassbox/runtime/repository_intelligence_layout.py`
  - `src/glassbox/runtime/repository_intelligence_layout_recipes.py`
  - `src/glassbox/runtime/repository_intelligence_layout_docs.py`
  - `src/glassbox/runtime/repository_intelligence_layout_evals.py`
  - `tests/unit/test_repository_index.py`
  - `tests/unit/test_eval_recommendations.py`
- Work:
  - move pyproject and package-script command extraction into recipe helpers
  - move docs command extraction into a docs-owned helper
  - move eval recipe/profile command extraction into an eval-owned helper
  - preserve command purpose, review relevance, risk, timeout, confidence,
    scope paths, provenance, limitations, and stable recipe IDs
- Deliverables:
  - command recipe extraction split by source family without changing snapshot
    shape
- Validation:
  - `uv run pytest tests/unit/test_repository_index.py -k recipe`
  - `uv run pytest tests/unit/test_eval_recommendations.py -k recipe`

### GBX-R723: Split Ownership, Subsystem, And Release-Surface Hint Discovery

- Status: `DONE`
- Dependencies: GBX-R720, GBX-R722
- Target files:
  - `src/glassbox/runtime/repository_intelligence_layout.py`
  - `src/glassbox/runtime/repository_intelligence_layout_ownership.py`
  - `src/glassbox/runtime/repository_intelligence_layout_subsystems.py`
  - `src/glassbox/runtime/repository_intelligence_layout_release.py`
  - `tests/unit/test_repository_index.py`
- Work:
  - move CODEOWNERS-style and convention owner hints into an ownership owner
  - move subsystem grouping into a subsystem owner
  - move release-surface grouping into a release owner
  - preserve advisory non-authority labels and current stable identifiers
- Deliverables:
  - independently reviewable owner, subsystem, and release-surface derivation
- Validation:
  - `uv run pytest tests/unit/test_repository_index.py -k "owner or subsystem or release"`

---

## Phase 103: Refresh Orchestration And Context-Use Cleanup

### GBX-R730: Introduce Shared Repository Intelligence Refresh Service

- Status: `DONE`
- Dependencies: GBX-R710, GBX-R720
- Target files:
  - `src/glassbox/runtime/repository_intelligence_refresh.py`
  - `src/glassbox/cli/repository_command_refresh.py`
  - `src/glassbox/runtime/background_job_handlers.py`
  - `tests/unit/test_repository_index.py`
  - `tests/integration/test_background_job_runner.py`
  - `tests/integration/test_cli_repository_commands.py`
- Work:
  - create one runtime service for building index snapshots with active memory,
    building topology from the resulting index, writing managed artifacts, and
    returning summary metadata
  - move immediate CLI refresh and background refresh onto the shared service
  - keep background-job event/progress recording in background-job modules
  - preserve output payloads, artifact paths, no-source-mutation claims, and
    topology/index write behavior
- Deliverables:
  - one refresh orchestration boundary shared by CLI and background jobs
  - reduced duplication between command and daemon paths
- Validation:
  - `uv run pytest tests/unit/test_repository_index.py -k refresh`
  - `uv run pytest tests/integration/test_background_job_runner.py -k repository`
  - `uv run pytest tests/integration/test_cli_repository_commands.py -k refresh`

### GBX-R731: Separate Runtime Context Snapshot Derivation From Prompt-Use Event Recording

- Status: `DONE`
- Dependencies: GBX-R701
- Target files:
  - `src/glassbox/runtime/runtime_context_derivation.py`
  - `src/glassbox/runtime/runtime_context_memory_use.py`
  - `tests/unit/test_context_builder.py`
  - `tests/unit/test_workspace_memory_capture.py`
  - `tests/unit/test_replay_orchestrator.py`
- Work:
  - move `WorkspaceMemoryUsedInContext` event construction and dedupe into a
    side-effect owner
  - keep structured runtime context snapshot derivation readable as derivation
    plus explicit optional recording calls
  - preserve event ordering, dedupe behavior, prompt section labels,
    repository-intelligence memory-use recording, and replay fingerprints
- Deliverables:
  - one runtime owner for memory prompt-use evidence recording
  - clearer read-versus-mutate boundary in runtime context assembly
- Validation:
  - `uv run pytest tests/unit/test_context_builder.py -k memory`
  - `uv run pytest tests/unit/test_workspace_memory_capture.py -k context`
  - `uv run pytest tests/unit/test_replay_orchestrator.py -k context`

### GBX-R732: Centralize Repository Intelligence Refresh Summary Text

- Status: `DONE`
- Dependencies: GBX-R730
- Target files:
  - `src/glassbox/runtime/repository_intelligence_refresh.py`
  - `src/glassbox/runtime/background_job_handlers.py`
  - `src/glassbox/cli/repository_command_formatters.py`
  - `tests/integration/test_background_job_runner.py`
  - `tests/integration/test_cli_repository_commands.py`
- Work:
  - keep the refresh summary artifact text in one runtime helper
  - keep CLI human text in CLI formatters
  - preserve local-only advisory claims: source mutation none, policy mutation
    none, command recipes advisory, and release authority deterministic
- Deliverables:
  - shared refresh summary data model or helper consumed by CLI and background
    handlers
- Validation:
  - `uv run pytest tests/integration/test_background_job_runner.py -k repository`
  - `uv run pytest tests/integration/test_cli_repository_commands.py -k refresh`

---

## Phase 104: Recommendation Enrichment And Freshness Cleanup

### GBX-R740: Split Repository-Intelligence Recommendation Matching From Output Assembly

- Status: `DONE`
- Dependencies: GBX-R701, GBX-R720
- Target files:
  - `src/glassbox/runtime/eval_recommendation_repository_intelligence.py`
  - `src/glassbox/runtime/eval_recommendation_repository_matching.py`
  - `src/glassbox/runtime/eval_recommendation_repository_metadata.py`
  - `src/glassbox/runtime/eval_recommendation_repository_recipes.py`
  - `tests/unit/test_eval_recommendations.py`
- Work:
  - move subsystem, owner, release-surface, and command-recipe matching into
    pure matching helpers
  - move source metadata construction into a metadata helper
  - move recipe recommendation construction into a recipe helper
  - keep the public enrichment function as orchestration over the helpers
  - preserve warnings, confidence, freshness, reason groups, matched paths,
    safe next commands, and output ordering
- Deliverables:
  - repository-intelligence eval enrichment that can be reviewed by matching,
    metadata, and recipe concern
- Validation:
  - `uv run pytest tests/unit/test_eval_recommendations.py -k repository`
  - `uv run pytest tests/integration/test_cli_eval_commands.py -k recommend`

### GBX-R741: Normalize Freshness Cue Sources And Safe Next Actions

- Status: `DONE`
- Dependencies: GBX-R740
- Target files:
  - `src/glassbox/runtime/repository_intelligence_freshness.py`
  - `src/glassbox/runtime/repository_index_status.py`
  - `src/glassbox/cli/repository_command_status.py`
  - `src/glassbox/web/repository_intelligence_api.py`
  - `tests/unit/test_repository_index.py`
  - `tests/integration/test_cli_repository_commands.py`
- Work:
  - make index, topology, memory, eval metadata, command recipe, and release
    surface freshness cues use consistent source labels and next-action
    wording
  - keep missing memory references advisory and non-blocking
  - preserve current JSON fields and freshness vocabulary
- Deliverables:
  - one runtime owner for shared freshness cue wording and safe next actions
- Validation:
  - `uv run pytest tests/unit/test_repository_index.py -k freshness`
  - `uv run pytest tests/integration/test_cli_repository_commands.py -k stale`

---

## Phase 105: Web And Frontend Repository Intelligence Cleanup

### GBX-R750: Split Repository Intelligence API Models And Builders By Surface

- Status: `DONE`
- Dependencies: GBX-R711, GBX-R741
- Target files:
  - `src/glassbox/web/repository_intelligence_api.py`
  - `src/glassbox/web/repository_intelligence_api_models.py`
  - `src/glassbox/web/repository_intelligence_api_builders_overview.py`
  - `src/glassbox/web/repository_intelligence_api_builders_paths.py`
  - `src/glassbox/web/repository_intelligence_api_builders_recommendations.py`
  - `tests/integration/test_web_repository_intelligence_routes.py`
- Work:
  - keep `repository_intelligence_api.py` as the compatibility facade
  - move response models into a model module if OpenAPI shape remains stable
  - move overview/freshness builders, path/subsystem/recipe builders, and
    recommendation/memory-candidate builders into focused owners
  - avoid FastAPI imports in builder modules
  - preserve OpenAPI schema shape unless explicitly changed
- Deliverables:
  - web repository-intelligence builders split by response family
- Validation:
  - `uv run pytest tests/integration/test_web_repository_intelligence_routes.py`
  - `uv run pytest tests/integration/test_openapi_schema.py`
  - `pnpm --dir frontend api:generate`
  - `pnpm --dir frontend typecheck`

### GBX-R751: Split Repository Intelligence Route Query Helpers

- Status: `DONE`
- Dependencies: GBX-R750
- Target files:
  - `src/glassbox/web/routes/repository_intelligence.py`
  - `src/glassbox/web/routes/repository_intelligence_queries.py`
  - `src/glassbox/web/routes/repository_intelligence_services.py`
  - `tests/integration/test_web_repository_intelligence_routes.py`
- Work:
  - keep FastAPI decorators and endpoint declarations easy to scan
  - move snapshot loading, query parameter coercion, pagination, route-local
    service construction, and HTTP error translation into helpers
  - preserve response models, status codes, route paths, and validation
    patterns
- Deliverables:
  - route module that reads as transport declaration rather than repeated query
    orchestration
- Validation:
  - `uv run pytest tests/integration/test_web_repository_intelligence_routes.py`

### GBX-R752: Split Frontend Repository Panels Into Overview, Path, Recipe, Memory, And Freshness Sections

- Status: `DONE`
- Dependencies: GBX-R750
- Target files:
  - `frontend/components/console/knowledge-autonomy/repository-panels.tsx`
  - `frontend/components/console/knowledge-autonomy/repository-overview.tsx`
  - `frontend/components/console/knowledge-autonomy/repository-path.tsx`
  - `frontend/components/console/knowledge-autonomy/repository-recipes.tsx`
  - `frontend/components/console/knowledge-autonomy/repository-memory.tsx`
  - `frontend/components/console/knowledge-autonomy/repository-freshness.tsx`
  - `frontend/components/console/knowledge-autonomy/repository-format.ts`
  - `frontend/tests/knowledge-autonomy-console.test.tsx`
- Work:
  - keep `repository-panels.tsx` as the component entrypoint while splitting
    dense sections by operator surface
  - move pure label, count, badge, freshness, and path formatting into a
    non-React helper
  - preserve current copy, action affordances, loading states, and responsive
    layout
  - keep transport in stores, not components
- Deliverables:
  - repository dashboard sections that can be reviewed independently
- Validation:
  - `pnpm --dir frontend test -- knowledge-autonomy-console.test.tsx`
  - `pnpm --dir frontend typecheck`
  - `pnpm --dir frontend lint`

### GBX-R753: Split Knowledge Store Repository Loading And Action State

- Status: `DONE`
- Dependencies: GBX-R750
- Target files:
  - `frontend/stores/knowledge-store.ts`
  - `frontend/stores/knowledge-store-repository.ts`
  - `frontend/stores/knowledge-store-memory.ts`
  - `frontend/stores/knowledge-store-actions.ts`
  - `frontend/tests/dashboard-stores.test.ts`
  - `frontend/tests/knowledge-autonomy-console.test.tsx`
- Work:
  - keep `createKnowledgeStore` as the public store facade
  - move repository overview/path/recipe/freshness loading into a repository
    store helper
  - move memory candidate loading into a memory helper
  - move user-facing action state and messages into an action helper
  - preserve request cancellation, load state, dashboard-store compatibility,
    and current action messages
- Deliverables:
  - knowledge store split by repository, memory, and action concerns
- Validation:
  - `pnpm --dir frontend test -- dashboard-stores.test.ts knowledge-autonomy-console.test.tsx`
  - `pnpm --dir frontend typecheck`
  - `pnpm --dir frontend lint`

---

## Phase 106: Guardrails, Core Strategy, Docs, And Validation Closeout

### GBX-R760: Split Architecture Guardrail Tests By Boundary Family

- Status: `DONE`
- Dependencies: GBX-R702
- Target files:
  - `tests/unit/test_architecture_guardrails.py`
  - `tests/unit/architecture_guardrails/`
- Work:
  - split guardrails into focused test modules for backend import direction,
    Python facades, frontend boundaries, generated-file exclusions, and
    refactor-document coverage
  - preserve current assertions and failure-message quality
  - avoid weakening guardrails while making future additions easier to review
- Deliverables:
  - architecture guardrail suite split by concern with shared helper utilities
- Validation:
  - `uv run pytest tests/unit/test_architecture_guardrails.py`
  - `uv run pytest tests/unit/architecture_guardrails`

### GBX-R761: Define Core Repository-Intelligence Model Domain Strategy

- Status: `TODO`
- Dependencies: GBX-R700
- Target files:
  - [refactor-boundaries.md](./refactor-boundaries.md)
  - `src/glassbox/core/models.py`
  - `src/glassbox/core/events.py`
  - `tests/unit/test_core_models.py`
  - `tests/unit/test_core_events.py`
- Work:
  - document when repository-intelligence models should move into a core domain
    module versus staying in broad public core model/event surfaces
  - do not split core files mechanically during this task
  - identify import compatibility requirements if a later task extracts
    repository-intelligence model families
- Deliverables:
  - explicit model/event domain strategy for future repository-intelligence
    growth
  - no behavior change
- Validation:
  - `uv run pytest tests/unit/test_core_models.py tests/unit/test_core_events.py`
  - `uv run pytest tests/unit/test_release_candidate_docs.py -q`

### GBX-R762: Refresh Refactor Documentation And Docs Hub References

- Status: `TODO`
- Dependencies: GBX-R710, GBX-R720, GBX-R730, GBX-R750, GBX-R760
- Target files:
  - [architecture.md](./architecture.md)
  - [refactor-boundaries.md](./refactor-boundaries.md)
  - [README.md](./README.md)
  - [refactor-v15.md](./refactor-v15.md)
  - `README.md`
- Work:
  - update architecture and boundary docs with the completed post-v15 helper
    owners
  - update docs hub links if public refactor guidance changes
  - record accepted compatibility shims and product follow-up candidates
  - keep docs aligned with actual command help and module names
- Deliverables:
  - source-linked post-v15 refactor closeout notes
- Validation:
  - `uv run pytest tests/unit/test_release_candidate_docs.py -q`
  - `uv run pytest tests/unit/test_architecture_guardrails.py`

### GBX-R763: Run Post-V15 Refactor Confidence Sweep

- Status: `TODO`
- Dependencies: GBX-R762
- Target files:
  - tests, docs, scripts, frontend as needed
- Work:
  - run focused repository-intelligence and refactor-sensitive validation
  - record any accepted validation gaps in this file before marking the
    roadmap complete
  - do not refresh deterministic eval baselines unless a task explicitly
    changed behavior and follows the established eval refresh workflow
- Deliverables:
  - validation summary sufficient for post-v15 refactor closeout
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
  - `uv run python scripts/validate_v15_release_gate.py --dry-run`

## Accepted Product Follow-Up Candidates

These findings are useful context for refactor planning, but they are not
refactor-only tasks unless a later roadmap explicitly chooses to change
behavior:

- decide whether repository intelligence refresh should expose progress stages
  in the dashboard beyond current background-job status and retained summary
  artifacts
- decide whether `repo memory-candidates` should support an operator-friendly
  session picker in the dashboard or TUI instead of requiring a session ID
- decide whether repository intelligence owner hints should integrate with
  external code-owner tooling; v15 currently treats them as local advisory cues
  only
- decide whether command recipes should gain richer policy preview output
  before execution; v15 recipes remain recommendations, not approvals
- decide whether stale repository intelligence should ever block handoff or
  commit readiness in a future deterministic contract

Product follow-ups should preserve the v15 non-goals unless a future product
contract explicitly changes them.

## Accepted Compatibility Shims

The following facades are acceptable during this roadmap as long as they remain
thin and delegate to owned helpers after the relevant phase completes:

- `src/glassbox/cli/repository_commands.py`: repository command dispatcher
  over status, refresh, inspection, memory, and formatting helpers.
- `src/glassbox/runtime/repository_index.py`: public repository index facade
  over builder, persistence, discovery, search, and status helpers.
- `src/glassbox/runtime/repository_intelligence_layout.py`: layout discovery
  coordinator over package/path, recipe, ownership, subsystem, release, and
  common helpers.
- `src/glassbox/runtime/repository_intelligence_queries.py`: shared path
  inspection and repository-intelligence query facade.
- `src/glassbox/runtime/repository_intelligence_refresh.py`: shared refresh
  orchestration helper once introduced.
- `src/glassbox/runtime/runtime_context_derivation.py`: runtime context
  derivation entrypoint over snapshot builders and prompt-use evidence
  recording helpers.
- `src/glassbox/runtime/eval_recommendation_repository_intelligence.py`:
  repository-intelligence eval recommendation enrichment facade over matching,
  metadata, and recipe helpers.
- `src/glassbox/web/repository_intelligence_api.py`: response-model and builder
  facade over repository-intelligence overview, path, recommendation, memory,
  and freshness web helpers.
- `src/glassbox/web/routes/repository_intelligence.py`: FastAPI declaration
  surface over route-local query, service, pagination, and HTTP error helpers.
- `frontend/stores/knowledge-store.ts`: dashboard store facade over repository,
  memory, and action-state helpers.
- `frontend/components/console/knowledge-autonomy/repository-panels.tsx`:
  dashboard entrypoint over overview, path, recipe, memory, and freshness
  sections.
- `tests/unit/test_architecture_guardrails.py`: legacy validation entrypoint
  that imports the split architecture guardrail modules by boundary family.

Do not add new behavior to these facades once their helper owners exist. New
behavior should land in the focused owner module and be re-exported only when a
stable public import path requires it.
