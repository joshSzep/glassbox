# Glassbox Refactor Boundaries

For the docs hub and operator guides, start at [README.md](./README.md). This note defines the target architectural boundaries for the v1 refactor roadmap in [refactor-v1.md](./refactor-v1.md), the post-v8 follow-on roadmap in [refactor-v8.md](./refactor-v8.md), the second-order v10 roadmap in [refactor-v10.md](./refactor-v10.md), the post-v11 confidence-surface roadmap in [refactor-v11.md](./refactor-v11.md), the post-v13 review-loop roadmap in [refactor-v13.md](./refactor-v13.md), the post-v14 review-loop maturity roadmap in [refactor-v14.md](./refactor-v14.md), the post-v15 repository-intelligence roadmap in [refactor-v15.md](./refactor-v15.md), and the post-v16 operator-flow roadmap in [refactor-v16.md](./refactor-v16.md).

## Purpose

This document is the architecture source of truth for the refactor roadmap.

It exists to answer one question before code moves begin:

What are the intended module boundaries for the current Glassbox implementation, and what kinds of changes are explicitly out of scope for the first refactor pass?

This note is intentionally code-aligned. It describes the current implementation shape and the target decomposition boundaries for refactor work already captured in [refactor-v1.md](./refactor-v1.md), [refactor-v8.md](./refactor-v8.md), [refactor-v10.md](./refactor-v10.md), [refactor-v11.md](./refactor-v11.md), [refactor-v13.md](./refactor-v13.md), [refactor-v14.md](./refactor-v14.md), [refactor-v15.md](./refactor-v15.md), and [refactor-v16.md](./refactor-v16.md). It does not define a new product architecture.

## Implementation Status

The post-v8 boundary map is implemented as of Phase 55 of
[refactor-v8.md](./refactor-v8.md). Runtime autonomy, store projection reads and
repository adapters, TUI state/widgets/app coordination, dashboard stores,
autonomy console sections, and session-inspector diagnostic panes now follow the
module boundaries described here.

The remaining compatibility modules named in this document are stable import
facades. They preserve public call sites while delegating to owned
implementation modules; they are not license for new behavior to accumulate in
the facade.

The v10 second-order boundary map is implemented through Phase 64 of
[refactor-v10.md](./refactor-v10.md). It did not reopen the v1 or v8
decomposition decisions; it identified the modules that grew after those splits
and moved behavior-preserving ownership into focused frontend, web, runtime,
provider, tool-policy, SQLite schema, and core-domain strategy boundaries.

The v11 confidence-surface refactor map is implemented through Phase 75 of
[refactor-v11.md](./refactor-v11.md). It starts from the completed v11 release
candidate and targets the recommendation, knowledge posture, branch-search
decision support, handoff, CLI guidance, frontend evidence, recovery, and
projection modules that accumulated richer derivation and formatting behavior
during the confidence-and-adoption milestone.

Recommendation output, recommendation matching, release-gate summaries,
knowledge posture, branch-search decision support, frontend knowledge/branch
sections, session export/import, service-contract strategy, CLI status and
command-guide surfaces, interactive command handlers, frontend session-store
helpers, recovery helpers, compaction helpers, turn hooks, and task/background
projection handlers now follow the helper boundaries described below.

The post-v13 review-loop boundary map is implemented through Phase 87 of
[refactor-v13.md](./refactor-v13.md). Runtime changesets, review feedback,
manual evidence, verification preview, lifecycle briefs, handoff/commit
readiness, CLI/TUI/plain review commands, web response builders, route helpers,
dashboard console sections, frontend store actions/selectors, store projection
families, repository adapter mixins, and release-gate helper ownership now
follow the focused boundaries described below.

The post-v14 review-loop maturity boundary map starts from the completed v14
release-candidate milestone and the new roadmap in
[refactor-v14.md](./refactor-v14.md). The next split should keep lifecycle
limitation summaries, response-linked fixup inventory, skipped advisory
evidence, handoff and commit readiness, terminal review-loop guidance,
changeset web transport, frontend changeset actions, and v14 release-gate
summary shaping independently reviewable without changing the shipped v14
contracts.

The post-v15 repository-intelligence boundary map starts from the completed v15
release-candidate milestone and the new roadmap in
[refactor-v15.md](./refactor-v15.md). The next split should keep repository
command handling, repository-intelligence layout discovery, refresh
orchestration, runtime prompt-use recording, recommendation enrichment, web
response building, frontend repository panels, knowledge-store repository
loading, and architecture guardrails independently reviewable without changing
the shipped v15 advisory contracts.

## Scope

This refactor pass is about implementation structure, not product behavior.

The goals are:

- reduce oversized source files with mixed responsibilities
- remove architectural duplication where the same control flow or state shaping exists in multiple places
- make dependency direction between subsystems explicit
- preserve current operator-visible behavior unless a later task says otherwise

The non-goals are:

- redesign the event model
- replace the current single-process runtime model
- introduce a new UI framework for the dashboard
- rewrite the store, runtime, or CLI from scratch
- change replay result taxonomy, snapshot payloads, or command semantics as part of refactor-only work
- add new autonomy behaviors, background job kinds, provider checks, repository
  indexing semantics, workspace-memory capture rules, TUI workflows, or
  dashboard workflows while performing post-v8 refactor-only tasks
- change task-autonomy, verification, compare, provider, tool-policy, HTTP,
  projection, or core event/model behavior while performing v10 refactor-only
  movement
- add new verification recommendation rules, knowledge sources, provider
  checks, branch-search actions, handoff package fields, release-gate stages,
  command semantics, dashboard workflows, or projection schemas while
  performing v11 confidence-surface refactor-only movement
- change v13 review-loop semantics, local evidence authority, publication
  boundary non-claims, handoff/commit read-only posture, or advisory browser,
  dashboard, accessibility, provider, and dogfooding evidence contracts while
  performing post-v13 review-loop refactor-only movement
- change v14 review-loop maturity semantics, response-linked fixup inventory,
  skipped advisory evidence posture, lifecycle brief limitation caps, safe next
  actions, dashboard action states, local-versus-daemon review command parity,
  or publication-boundary non-claims while performing post-v14 maturity
  refactor-only movement
- change v15 repository intelligence semantics, snapshot authority, freshness
  posture, path-to-verification guidance, command-recipe advisory status,
  memory-derived repository facts, prompt-context recording, replay
  fingerprinting, or deterministic release-gate authority while performing
  post-v15 repository-intelligence refactor-only movement

## Behavior-Preservation Contract

Unless a later task explicitly changes a contract, refactor work should preserve:

- current CLI command semantics and exit-code behavior
- current session snapshot and session-index HTTP payload shapes
- current event ordering for turn execution and turn resumption flows
- current replay result taxonomy and mismatch classification semantics
- current dashboard reducer state shape and observable interaction semantics
- current repository and service contracts used by runtime bootstrap, tests, and route handlers

That does not prevent internal renaming, extraction, or compatibility shims. It does mean internal movement is not a license to make incidental behavior changes.

## Current Pressure Points

The existing architecture is coherent, but several files are carrying too many responsibilities at once.

The main pressure points are:

- `src/glassbox/runtime/turn_engine.py`: turn lifecycle, model loop, tool execution, suspension and resumption, artifact hooks, and event emission
- `src/glassbox/runtime/replay.py`: replay bundle models, bundle I/O, replay execution, normalization, mismatch collection, and triage
- `src/glassbox/store/sqlite.py`: schema bootstrap, event-store operations, projection application, lineage helpers, and rebuild logic
- `src/glassbox/cli/__init__.py`: parser construction, command dispatch, command execution, interactive session control, and report formatting
- `src/glassbox/runtime/context_builder.py`: snapshot building, working-set heuristics, and prompt formatting
- `src/glassbox/web/routes/sessions.py`: HTTP transport, session query composition, snapshot shaping, and next-action summary logic
- `src/glassbox/web/static/state.js`, `render.js`, and `dashboard.js`: reducer logic, rendering, transport, and DOM orchestration pressed into a few large files

Some files are large because they hold many data models or helper variants. That alone is not enough reason to split them. The refactor should focus first on files that mix distinct responsibilities or duplicate logic already living elsewhere.

The post-v8 pressure points are concentrated in newer autonomy-era surfaces:

- `src/glassbox/runtime/background_jobs.py` mixes worker-loop coordination,
  stale-claim recovery, read-only maintenance jobs, mutating task
  continuations, and progress/failure event recording
- `src/glassbox/runtime/workspace_memory_capture.py` mixes capture service
  commits, candidate extraction, model-assisted suggestion parsing, filtering,
  dedupe, staleness checks, and redaction
- `src/glassbox/runtime/observability.py` mixes workspace report aggregation
  with domain-specific collectors for runtime transport, projections,
  artifacts, verification, background jobs, task autonomy, memory, repository
  index, branch search, and provider posture
- `src/glassbox/runtime/repository_index.py` mixes public index read/write
  helpers, filesystem scanning, entity extraction, dependency/script parsing,
  and search helpers
- `src/glassbox/store/sqlite_queries.py` is a broad read-model adapter over
  projections for transcript, runtime notes, approvals, metrics, budgets,
  tasks, branch search, and workspace memory adjacency
- `src/glassbox/store/repositories.py` is a large adapter surface; most of its
  size is legitimate contract coverage, but it should not keep accumulating
  domain-specific query shaping inline
- `src/glassbox/cli/tui/conversation.py` mixes model types, event reduction,
  selectors, and text transformation helpers for terminal state
- `src/glassbox/cli/tui/widgets.py` mixes Textual widget classes, pure render
  functions, transcript block formatting, composer behavior, command palette
  behavior, and details rendering
- `frontend/stores/dashboard-stores.ts` mixes dashboard, session, task,
  knowledge, branch-search, stream, pagination, and action-state stores behind
  one compatibility module
- `frontend/components/console/task-autonomy-console.tsx`,
  `knowledge-autonomy-console.tsx`, and `branch-search-console.tsx` are mixed
  responsibility components that combine data presentation, local view state,
  filtering, evidence summaries, action controls, and formatting helpers

The v10 pressure points are the second-order modules underneath those improved
facades:

- `frontend/components/console/task-autonomy-sections.tsx` is now a
  compatibility facade over queue, inspector, action, evidence, formatting, and
  type modules under `frontend/components/console/task-autonomy/`
- `frontend/components/console/verification-cues.tsx` now renders typed facts
  from `verification-cues-analysis.ts`
- `frontend/components/console/session-inspector/panes/compare-pane.tsx` now
  renders typed facts from `compare-analysis.ts`
- `frontend/components/console/workspace-console.tsx` now composes stores,
  selected state, and surfaces while route synchronization and repeated action
  bindings live in `workspace-console/routing.ts` and
  `workspace-console/actions.ts`
- `src/glassbox/web/routes/sessions.py` and `src/glassbox/web/routes/tasks.py`
  now stay FastAPI declaration surfaces over HTTP-local query/action helpers and
  shared pagination utilities
- `src/glassbox/runtime/task_queries.py` now keeps `TaskQueryService` as the
  repository-backed read facade while models, assembly, verification, and repair
  derivation live in focused `task_query_*` modules
- `src/glassbox/runtime/provider_canary.py` is now a thin compatibility facade;
  provider-canary scenarios, live execution, retained evidence reads,
  freshness checks, report writing, and outcome counting live in focused
  `provider_canary_*` helper modules
- `src/glassbox/runtime/provider_recommendations.py` is now a recommendation
  orchestration facade; recommendation models and capability, risk, credential,
  failure, budget, and next-action scoring live in focused
  `provider_recommendation_*` helper modules
- `src/glassbox/tools/policy.py` is now the stable policy-engine facade; path
  scope evaluation, rule matching, autonomy budget permits, approval message
  construction, and command-risk heuristics live in focused `policy_*` helpers
- `src/glassbox/store/sqlite_schema.py` is now the schema bootstrap and
  explicit migration-registry owner; domain-specific projection table and
  migration helpers live in focused `sqlite_schema_*` modules
- `src/glassbox/core/events.py` and `src/glassbox/core/models.py` are large
  model-heavy core modules. They are acceptable as broad public import surfaces
  until a domain expansion would otherwise make event registration, review, or
  ownership unsafe.

The v11 pressure points are confidence-surface modules that grew during the
release-candidate work. They are not broken because they are large; they are
targets because derivation, ranking, formatting, command guidance, and
packaging concerns now sit next to one another:

- `src/glassbox/runtime/eval_recommendation_output.py` mixes daily-development
  surfaces, long-run surfaces, release-gate recipe rendering, executable plan
  shaping, skipped-check explanations, JSON model construction, and terminal
  formatting.
- `src/glassbox/runtime/eval_recommendation_engine.py` mixes path matching,
  owner/capability/stage expansion, release-gate command recommendation, and
  fallback/manual guidance.
- `scripts/validate_v11_release_gate.py` remains the operator entrypoint, but
  stage-summary shaping, advisory provider rows, dry-run planning, and retained
  evidence summaries should become testable helper concerns.
- `src/glassbox/runtime/knowledge_posture.py` mixes source-specific cue
  collection, aggregate freshness/ranking decisions, provenance references,
  safe inspection commands, and observability-facing summaries.
- `src/glassbox/runtime/branch_decision_support.py` mixes candidate evidence,
  changed-file posture, verification recommendations, cost, risk,
  accepted-risk, and follow-up-action derivation.
- `src/glassbox/runtime/session_export.py` mixes package assembly, artifact
  manifest shaping, handoff summary generation, lineage/knowledge/checkpoint
  evidence, safe command guidance, and redaction.
- `src/glassbox/runtime/session_import.py` mixes package validation,
  inspection-only session creation, imported transcript/runtime notes, and
  handoff-note construction.
- `src/glassbox/services/contracts.py` is model/protocol-heavy and acceptable
  today, but should split only along stable domain contracts if export,
  background-job, memory, task, branch-search, and session protocols keep
  growing together.
- `src/glassbox/cli/status_formatters.py` is now a compatibility facade over
  session, task, observability, policy, and knowledge status helpers.
  `src/glassbox/cli/command_guide.py` still owns broad terminal and JSON
  guidance presentation and should not duplicate runtime-derived safe-command
  or evidence posture logic.
- `src/glassbox/cli/interactive_commands.py` and
  `src/glassbox/cli/parser_sessions.py` mix launch, daemon forwarding, local
  actions, autonomy option resolution, and parser wiring.
- `frontend/components/console/knowledge-autonomy-sections.tsx` and
  `frontend/components/console/branch-search-sections.tsx` now render dense
  v11 evidence and should split into summary, detail, evidence, formatting, and
  action-control modules while preserving their entrypoint exports.
- The v11 frontend confidence split now keeps
  `knowledge-autonomy-sections.tsx` and `branch-search-sections.tsx` as stable
  export facades while section families under `knowledge-autonomy/` and
  `branch-search/` own memory/repository details, candidate lists, decision
  cards, evidence sections, action controls, shared state rows, and pure
  formatting helpers.
- `frontend/stores/session-store.ts` mixes stream lifecycle, detail pagination,
  drafts, and action mutations behind one store factory.
- The v11 tool-attempt recovery split now keeps
  `src/glassbox/runtime/tool_attempt_recovery.py` as the stable import facade,
  while `tool_attempt_recovery_inspection.py`,
  `tool_attempt_recovery_retry.py`, `tool_attempt_recovery_abandon.py`,
  `tool_attempt_recovery_artifacts.py`, `tool_attempt_recovery_common.py`, and
  `tool_attempt_recovery_models.py` own inspection summaries, retry
  eligibility/execution, abandon events, retained output artifacts, shared
  lookups, and result models.
- The v11 context compaction split now keeps
  `src/glassbox/runtime/context_compaction_service.py` as the stable import
  facade, while `context_compaction_range.py`,
  `context_compaction_artifact.py`, `context_compaction_freshness.py`, and
  `context_compaction_mutations.py` own over-cap range guidance, artifact
  payload assembly, freshness assessment, and create/refresh/invalidate event
  mutations.
- The v11 turn hook split now keeps `turn_event_recorder.py` and
  `turn_tool_executor.py` as event/execution coordinators while
  `turn_artifacts.py`, `turn_replay_hooks.py`, and
  `turn_tool_attempt_heartbeats.py` own context/tool-output artifact side
  effects, replay capture forwarding, and classified tool-attempt heartbeat
  construction.
- The v11 projection split keeps
  `src/glassbox/store/sqlite_projection_tasks.py` and
  `src/glassbox/store/sqlite_projection_background_jobs.py` as stable
  projection coordinators. Task plan, step, verification, and lifecycle SQL
  handlers now live in focused `sqlite_projection_task_*` helpers, while
  background-job creation, lifecycle, pause/cancel, retry, and recovery SQL
  handlers live in focused `sqlite_projection_background_job_*` helpers.

The post-v13 pressure points are review-loop surfaces that grew while changesets
became locally reviewable and handoff-ready:

- `src/glassbox/runtime/changesets.py` mixes changeset source derivation,
  workspace diff helpers, query view assembly, feedback and evidence actions,
  verification preview, lifecycle brief assembly, safe-command guidance, and
  handoff/commit adjacency helpers. It should become the stable changeset
  runtime facade over focused `changeset_*`, review-feedback, manual-evidence,
  browser/accessibility-evidence, verification, and brief-section owners.
- `src/glassbox/cli/changeset_commands.py` mixes runtime-context wiring, command
  dispatch, JSON payload construction, and terminal formatting. It should remain
  the scriptable command facade while handlers, payload builders, and formatters
  move into changeset command helper modules.
- `src/glassbox/cli/parser_changesets.py`, `src/glassbox/cli/tui/commands.py`,
  `src/glassbox/cli/tui/app_commands.py`, and
  `src/glassbox/cli/interactive_session.py` carry the in-session `/review` and
  `/changeset` workflow entrypoints. Parser, TUI, and plain interactive helpers
  should split by review-loop command family without changing command names,
  defaults, or current-session behavior.
- `src/glassbox/web/changeset_api.py` and `src/glassbox/web/routes/changesets.py`
  mix transport models, response builders, service factories, request branching,
  and HTTP error translation. They should remain stable web import/route
  surfaces while transport models, builders, route services, request helpers,
  and error mapping move into web-owned helper modules.
- `frontend/components/console/changeset-console.tsx` combines list/detail
  presentation, feedback, evidence, verification, handoff, commit preparation,
  actions, formatting, and local form state. It should remain the component
  entrypoint while typed helpers and section modules own presentation families.
- `frontend/stores/changeset-store.ts` should keep transport and action state
  in the store layer while API action groups and derived selectors split under
  store-owned helpers. React components must not take over transport behavior.
- Changeset and review-loop SQLite projections, query helpers, and repository
  adapters should split by canonical event/read-model family without making
  projection tables authoritative.
- `scripts/validate_v13_release_gate.py` should remain the operator entrypoint
  while v13-specific release-gate stage construction, advisory evidence rows,
  dry-run planning, and summary metadata move into helper functions or a helper
  module.

Large files that are primarily model-heavy and should not be split just for
line count include core event/model/type modules, generated frontend API types,
generated OpenAPI JSON, fixture bundles, release evidence artifacts, and facade
modules whose public contract is intentionally broad but already delegates
behavior to owned implementation modules. Large files that are mixed
coordinators should be split along ownership boundaries when their roadmap task
arrives, not by mechanical line slicing.

The post-v14 pressure points are the review-loop maturity surfaces that grew
after the v13 split:

- `src/glassbox/runtime/changeset_review_brief_sections.py` now owns lifecycle
  section assembly, limitation collection, skipped-evidence copy, reviewer
  checklist shaping, safe commands, and review-readiness derivation. Limitation
  collection and summary construction should move first, followed by core,
  review-loop, and readiness section families.
- `src/glassbox/runtime/review_responses.py` owns response and fixup models,
  fixup artifact shaping, path-scope matching, status derivation, blockers,
  verification posture, freshness, and safe next actions. Model declarations,
  status derivation, fixup artifacts, path helpers, and summary assembly should
  become separate runtime owners while `review_responses.py` preserves imports.
- `src/glassbox/runtime/handoff_readiness.py` and
  `src/glassbox/runtime/commit_readiness.py` independently derive overlapping
  signal, blocker, limitation, path, and safe-action patterns. Shared signal
  concepts should move into a helper without merging the distinct handoff and
  commit product semantics.
- `src/glassbox/cli/interactive_client.py` mixes interactive client protocols,
  local runtime actions, daemon HTTP actions, SSE parsing, review-loop action
  orchestration, payload parsing, skipped-evidence counting, and terminal copy.
  Protocol/model, SSE, local, daemon, and review guidance owners should split
  without changing plain interactive behavior.
- Follow-on transport and release-gate pressure points are
  `src/glassbox/cli/changeset_command_handlers.py`,
  `src/glassbox/web/routes/changesets.py`,
  `src/glassbox/web/changeset_api_builders.py`,
  `frontend/api/client.ts`,
  `frontend/stores/changeset-store-actions.ts`, and
  `scripts/v14_release_gate_helpers.py`.

The post-v14 split should continue to treat model-heavy public surfaces,
generated API types, generated OpenAPI JSON, and fixture-heavy tests as stable
contract surfaces unless a concrete ownership problem appears.

The post-v15 pressure points are repository-intelligence surfaces that grew
while repository awareness became richer across CLI, runtime, web, dashboard,
context, replay, eval, package, and release-gate paths:

- `src/glassbox/cli/repository_commands.py` mixes command dispatch, runtime
  context wiring, status/staleness reporting, immediate and background refresh,
  path inspection, command recipe inspection, recommendation output, memory
  candidates, JSON payload shaping, and terminal formatting. It should become a
  stable dispatcher over status, refresh, inspection, memory, and formatter
  helpers.
- `src/glassbox/runtime/repository_intelligence_layout.py` mixes layout models,
  manifest parsing, package/root/generated-path derivation, command recipe
  extraction, owner hints, subsystem hints, release surfaces, stable IDs,
  digests, provenance, and path helpers. It should become a coordinator over
  layout model/common helpers plus package/path, recipe/docs/eval, ownership,
  subsystem, and release owners.
- `src/glassbox/runtime/repository_index_builder.py` and
  `src/glassbox/runtime/background_job_handlers.py` both know how to combine
  repository index snapshots, topology, active memory, managed artifacts, and
  summary output. Refresh orchestration should move into a shared runtime
  service while background-job modules keep job event/progress recording.
- `src/glassbox/runtime/runtime_context_derivation.py` derives prompt context
  and records `WorkspaceMemoryUsedInContext` events. Prompt-use evidence
  recording should move into a side-effect owner so snapshot derivation remains
  visibly separate from mutation.
- `src/glassbox/runtime/eval_recommendation_repository_intelligence.py` mixes
  snapshot loading, freshness warning assembly, subsystem/owner/surface/recipe
  matching, source metadata, reason mutation, and safe command shaping.
  Matching, metadata, and recipe output helpers should own those families.
- `src/glassbox/web/repository_intelligence_api.py` and
  `src/glassbox/web/routes/repository_intelligence.py` mix transport models,
  response builders, route-local query orchestration, pagination, service
  construction, and HTTP error mapping. Web model/builders should stay separate
  from FastAPI route declarations and from transport-agnostic runtime queries.
- `frontend/components/console/knowledge-autonomy/repository-panels.tsx` and
  `frontend/stores/knowledge-store.ts` mix repository overview, path
  inspection, recipes, freshness cues, memory candidates, loading state,
  action messages, and presentation formatting. Store helpers should own
  transport/action state while components and pure format helpers own
  presentation.
- `tests/unit/test_architecture_guardrails.py` has become a broad architecture
  suite. It should split by backend import direction, Python facades, frontend
  boundaries, generated-file exclusions, and refactor-document coverage once
  the post-v15 helper owners exist.
- `src/glassbox/core/events.py` and `src/glassbox/core/models.py` remain broad
  public, model-heavy surfaces. A later repository-intelligence model-domain
  strategy should split them only when a real event/model ownership problem
  appears, not because of line count alone.

The post-v15 split should continue to treat canonical events, managed
artifacts, generated OpenAPI/frontend API types, deterministic eval fixtures,
and public model-heavy core surfaces as stable contract surfaces. Repository
intelligence remains local, rebuildable, freshness-aware, provenance-backed,
and advisory by default.

The post-v16 operator-flow boundary map starts from the completed v16
operator-flow compression milestone and the new roadmap in
[refactor-v16.md](./refactor-v16.md). The next split should keep operator queue
ranking, evidence graph support, verification plan construction, maintenance
cues, recovery playbooks, changeset workup previews, dashboard cockpit panels,
and v16 release-gate evidence assembly independently reviewable without
changing shipped advisory contracts.

The post-v16 pressure points are operator-flow surfaces that grew while next
actions became more explicit across runtime, web, CLI, dashboard, eval, and
release-gate paths:

- `src/glassbox/runtime/evidence_graph.py` mixes graph models, builder
  utilities, changeset derivation, session derivation, claim support,
  truncation, summaries, lookups, and neighborhood traversal. It should become
  a stable facade over graph models, builder utilities, changeset graph
  helpers, session graph helpers, and query helpers.
- `src/glassbox/runtime/verification_plan_builder.py` mixes entry identity,
  duplicate suppression, recommendation recipe entries, eval entries,
  readiness requirements, manual-only rows, skipped checks, unsafe-command
  rows, and limit handling. It should delegate identity/coalescing,
  recommendation-source, readiness, manual-only, and skipped-row behavior to
  focused helpers.
- `src/glassbox/runtime/operator_queue.py` mixes session rows, runtime rows,
  maintenance rows, evidence summaries, sorting, dedupe, and counts. It should
  stay the queue aggregator while item-source helpers and sorting/count helpers
  own derivation details.
- Core operator-flow model families in `src/glassbox/core/models.py`,
  `src/glassbox/core/types.py`, and `src/glassbox/core/events.py` are broad
  public contract surfaces. They should split by next-action, queue, evidence
  graph, maintenance, verification, or recovery-playbook domain only when
  ownership and compatibility needs justify extraction.
- `src/glassbox/web/session_api_aggregate.py`,
  `src/glassbox/web/changeset_api_builders_detail.py`,
  `src/glassbox/web/routes/session_route_queries.py`, and
  `src/glassbox/web/routes/changeset_route_actions.py` should keep route and
  response shapes stable while session aggregate, changeset verification, and
  evidence graph response shaping move into web-owned builders.
- `frontend/components/console/workspace-overview/operator-queue-lanes.tsx`,
  `frontend/components/console/evidence-graph-panel.tsx`,
  `frontend/components/console/changeset/verification.tsx`, and
  `frontend/stores/changeset-store-review-actions.ts` should keep dashboard
  entrypoints and store transport ownership while row, link, format, graph, and
  verification action helpers own local derivation and presentation.
- `scripts/validate_v16_release_gate.py` should remain the operator entrypoint
  while v16 stage assembly, advisory evidence rows, package/static checks,
  dogfooding expectations, dry-run planning, and summary metadata move into
  release-gate helper modules.

The post-v16 split should continue to treat canonical events, managed
artifacts, typed API responses, projection rows, deterministic eval fixtures,
generated API types, and public model-heavy core surfaces as stable contract
surfaces. Operator-flow guidance remains advisory unless an existing readiness
contract marks a state as blocking. Evidence graph support explains local
support and gaps; it is not reviewer approval, verification success, release
authority, publication readiness, command approval, merge readiness, or hosted
review state.

## Target Boundary Map

### Runtime

The `runtime` package should own orchestration and runtime-specific query composition.

Its stable responsibilities are:

- session lifecycle coordination
- turn coordination
- context assembly
- replay execution and eval orchestration
- runtime-scoped query and snapshot shaping
- runtime bootstrap and dependency wiring

The `runtime` package should not become a catch-all for transport formatting, raw storage internals, or browser-specific response shaping.

#### Target Runtime Sub-Boundaries

- `supervisor` owns session lifecycle and delegates turn execution
- `turn_engine` owns turn-level coordination, but not every detail of model looping or resumption mechanics
- shared model-loop logic should be reusable by live turn execution and replay
- the shared model-loop boundary currently lives in `src/glassbox/runtime/model_loop.py` and is consumed by `turn_engine.py` plus replay runtime wiring
- turn preparation, suspended-turn reconstruction, turn event recording, and tool execution side effects now live in `src/glassbox/runtime/turn_preparation.py`, `turn_resumption.py`, `turn_event_recorder.py`, and `turn_tool_executor.py`, leaving `turn_engine.py` focused on session-facing turn coordination and failure handling
- context-building logic should separate structured snapshot derivation, working-set derivation, and prompt rendering
- the shared context assembly boundary now uses `src/glassbox/runtime/context_snapshots.py`, `context_working_set.py`, and `context_formatting.py`, with `context_builder.py` reduced to typed models plus `TurnContextBuilder` assembly
- runtime query code should provide session summaries and snapshots to both CLI and web consumers without embedding HTTP concerns
- the shared session-query boundary now lives in `src/glassbox/runtime/session_queries.py` and is consumed by CLI status reporting plus web session routes
- bootstrap should wire public collaborators together, not hide ownership behind broad transitive re-exports
- the bootstrap split now keeps `src/glassbox/runtime/bootstrap.py` as the public entry facade while moving storage-path and SQLite initialization to `bootstrap_storage.py`, provider wiring to `bootstrap_provider.py`, and `RuntimeContext` assembly to `bootstrap_assembly.py`
- `runtime/__init__.py` should stay a small public surface for bootstrap, event-bus, and runtime-context types; replay, supervisor, turn-engine, and context-builder imports should come from explicit submodules

#### Post-v8 Runtime Autonomy Sub-Boundaries

- `background_jobs` should own the public worker-loop entry points and worker
  tick summary, then delegate lease/recovery behavior, read-only maintenance
  handlers, mutating task-continuation handlers, and progress/failure event
  recording to focused runtime modules
- the background-job worker split now keeps
  `src/glassbox/runtime/background_jobs.py` as the stable public runner facade,
  with lease/cancellation/recovery helpers in `background_job_lifecycle.py`,
  read-only maintenance handlers in `background_job_handlers.py`, mutating task
  continuation in `background_task_continuation.py`, and progress/failure event
  recording in `background_job_records.py`
- background-job maintenance handlers should remain read-only except for
  explicit job progress/completion/failure events; task continuation handlers
  are the only post-v8 background path expected to mutate task/session state
- `workspace_memory_capture` should keep the public capture service and
  repository protocol stable while candidate extraction, model-assisted
  suggestions, redaction, filtering/dedupe/staleness, and commit construction
  move into pure helper modules
- the workspace-memory split now keeps
  `src/glassbox/runtime/workspace_memory_capture.py` as the public service
  facade, with candidate models/filtering in `workspace_memory_candidates.py`,
  extraction in `workspace_memory_extraction.py`, sensitive text redaction in
  `workspace_memory_redaction.py`, and review-gated commit event construction
  in `workspace_memory_commits.py`
- workspace-memory extraction remains review-gated: helpers propose candidates
  and the service records explicit confirmation, merge, rejection, or operator
  memory events
- `observability` should keep `build_workspace_observability_report` as the
  aggregation facade while domain collectors own runtime transport,
  projection, artifact, verification, background job, task autonomy, workspace
  memory, repository index, branch search, and provider-canary posture reads
- the observability split now keeps
  `src/glassbox/runtime/observability.py` as the aggregation and compatibility
  facade, with shared report models in `observability_models.py` and read-only
  domain collectors in focused `observability_*` modules for runtime/event
  transport, projections, artifacts, verification, background jobs, task
  autonomy, workspace memory, repository index, and branch search
- observability collectors must stay read-only and should not depend on CLI
  formatting, HTTP response models, frontend state, or background job repair
  actions
- `repository_index` should keep stable public helpers for building, writing,
  loading, searching, and fetching index entries while filesystem scanning,
  entity extraction, dependency/script extraction, index serialization, and
  search ranking move behind owned helpers
- the repository-index split now keeps
  `src/glassbox/runtime/repository_index.py` as the stable public facade, with
  deterministic discovery and source digests in `repository_index_discovery.py`,
  entry extraction in `repository_index_extraction.py`, persistence/freshness
  checks in `repository_index_persistence.py`, and search/entry lookup in
  `repository_index_search.py`
- repository intelligence remains local-file derived. It should not introduce
  network fetches, generated caches that are not rebuildable, or runtime
  orchestration dependencies as part of refactor-only work
- provider diagnostics and provider canary evidence are runtime read models and
  runtime checks. Diagnostics should stay configuration/readiness oriented;
  canary execution may use runtime bootstrap, but stored evidence loading and
  report aggregation should remain separable from observability formatting

#### V10 Runtime Query And Provider Sub-Boundaries

- `task_queries.py` should keep `TaskQueryService` as the repository-backed,
  read-only orchestration facade. Query view models, task summary/detail
  assembly, verification ledger interpretation, and repair-history derivation
  should live in focused transport-agnostic runtime helpers.
- Task query helpers may depend on core events/models and service repository
  contracts. They should not import FastAPI, web response models, frontend
  types, CLI formatting, or concrete store implementations.
- Provider canary code now keeps `runtime/provider_canary.py` as the stable
  public facade while `provider_canary_scenarios.py`,
  `provider_canary_execution.py`, `provider_canary_evidence.py`,
  `provider_canary_reporting.py`, and `provider_canary_models.py` own
  deterministic scenario definitions, opt-in live execution, stored evidence
  loading/freshness checks, report persistence/outcome counting, and retained
  evidence models.
- Provider recommendations now keep `runtime/provider_recommendations.py` as the
  stable public facade while `provider_recommendation_models.py`,
  `provider_recommendation_capability.py`, `provider_recommendation_risk.py`,
  `provider_recommendation_credentials.py`,
  `provider_recommendation_failures.py`, and
  `provider_recommendation_actions.py` own output contracts, capability fit,
  risk posture, credential readiness, failure posture, budget impact, and
  next-step guidance. Scoring helpers should continue to accept diagnostics,
  canary evidence, and recovery records as explicit inputs.
- Provider modules should not hide global evidence reads inside scoring helpers
  or let observability formatting leak into canary execution.

#### V11 Confidence Runtime Sub-Boundaries

- Eval recommendation output should keep a stable public facade while focused
  helpers own daily-development surface derivation, long-run surface
  derivation, verification plan/skipped-check construction, recipe and
  release-gate command grouping, and terminal formatting. JSON payload models
  remain behavior-compatible with existing CLI and eval tests.
- The v11 recommendation-output split now keeps
  `runtime/eval_recommendation_output.py` as a compatibility facade while
  `eval_recommendation_rows.py`, `eval_recommendation_plans.py`,
  `eval_recommendation_recipes.py`, `eval_recommendation_release_surfaces.py`,
  `eval_recommendation_long_run_surfaces.py`,
  `eval_recommendation_reason_groups.py`, and
  `eval_recommendation_common.py` own the extracted behavior.
- Eval recommendation engine orchestration should delegate path-impact
  matching, owner/capability expansion, profile/stage expansion, release-gate
  command recommendation, and fallback/manual-guidance labeling to focused
  helpers. Live-provider canary guidance remains advisory and opt-in.
- The v11 recommendation-engine split now keeps
  `runtime/eval_recommendation_engine.py` as the orchestration owner and
  `runtime/eval_recommendation_matching.py` as a compatibility facade while
  `eval_recommendation_path_matching.py`,
  `eval_recommendation_case_expansion.py`,
  `eval_recommendation_profile_expansion.py`, and
  `eval_recommendation_matching_common.py` own path/rule matching,
  owner/capability expansion, profile/fallback expansion, and shared match
  types.
- Knowledge posture should derive only from canonical events, projection rows,
  retained artifacts/evidence, repository index data, checkpoint/compaction
  state, provider evidence, and active session records. Source collectors,
  aggregate ranking, provenance references, and safe inspection command
  guidance should be independent helpers; no new durable knowledge store is
  introduced by refactor-only work.
- The v11 knowledge-posture split now keeps
  `runtime/knowledge_posture.py` as the compatibility facade while
  `knowledge_posture_sources.py`, `knowledge_posture_cues.py`,
  `knowledge_posture_provenance.py`, `knowledge_posture_guidance.py`,
  `knowledge_posture_ranking.py`, and `knowledge_posture_models.py` own source
  collection, cue derivation, bounded provenance, safe inspection commands,
  aggregate freshness precedence, and API models.
- Branch decision support should keep branch search non-mutating. Candidate
  retained evidence extraction, changed-file and missing-diff posture,
  verification recommendation delegation, cost estimates, risk/accepted-risk
  posture, and follow-up actions should be separate helpers over persisted
  branch-search/session/evidence records.
- The v11 branch-decision split now keeps
  `runtime/branch_decision_support.py` as the compatibility facade while
  `branch_decision_evidence.py`, `branch_decision_files.py`,
  `branch_decision_verification.py`, `branch_decision_cost.py`,
  `branch_decision_risk.py`, `branch_decision_followup.py`, and
  `branch_decision_models.py` own retained evidence pointers, changed-file
  summaries, eval-recommendation delegation, cost estimates, risk and
  accepted-risk labels, follow-up guidance, and API models.
- Session export should keep package JSON and import compatibility stable while
  package metadata/event/projection collection, artifact manifests, handoff
  summary assembly, and deterministic redaction move into owned helpers.
  Handoff summaries may mention objective, checkpoint, compaction,
  verification, accepted risks, pending actions, lineage, knowledge posture,
  and safe commands, but must not expose secrets or make imported packages
  resumable.
- The v11 session-export split now keeps `runtime/session_export.py` as the
  compatibility facade while `session_export_package.py`,
  `session_export_handoff.py`, `session_export_manifest.py`,
  `session_export_redaction.py`, and `session_export_utils.py` own package
  assembly, reviewer handoff summaries, artifact/policy/task/event references,
  deterministic redaction, and small shared formatting utilities.
- Session import should validate packages separately from inspection-only
  session creation, transcript/runtime-note import, and handoff-note
  construction. Older packages remain readable, and imported sessions remain
  inspection state rather than invented live evidence.
- The v11 session-import split now keeps `runtime/session_import.py` as the
  compatibility facade while `session_import_validation.py`,
  `session_import_events.py`, and `session_import_handoff.py` own package
  validation, inspection-only event construction, transcript/task/checkpoint
  import event shaping, and handoff runtime-note text.
- Tool-attempt recovery should separate inspection posture, retry eligibility,
  abandon eligibility/event construction, artifact lookup/read, and CLI/API
  result models. It should never rerun a tool without explicit operator
  confirmation.
- Context compaction service helpers should separate source-range planning,
  over-cap guidance, artifact payload assembly, freshness assessment, refresh,
  and invalidation. Compaction artifacts remain evidence and must not become
  prompt-authoritative cleanup.
- Turn event recorder and tool executor should keep event ordering stable while
  artifact recording, replay capture hooks, task-plan capture linkage, and
  tool-attempt heartbeat construction move into focused helpers.

#### V13 Review-Loop Runtime Sub-Boundaries

- `runtime/changesets.py` is the stable changeset runtime facade for the
  post-v13 roadmap. It should continue to preserve public imports for CLI, web,
  readiness, handoff, commit, replay/eval, and tests while behavior moves into
  focused owner modules.
- Changeset source creation and workspace diff behavior belong under
  `changeset_derivation.py` and `changeset_workspace_diff.py`. They preserve
  source limitation behavior, event emission, artifact retention, digest
  calculation, and no-mutation claims.
- Runtime-only result/view models and repository protocols belong under
  `changeset_models.py` and `changeset_repository_contracts.py`. Core event and
  record models stay in `core/`.
- Query view assembly belongs under `changeset_queries.py`,
  `changeset_detail.py`, and `changeset_inventory_status.py`. Query helpers
  stay transport-agnostic and repository-backed.
- Review feedback actions belong under `review_feedback_actions.py` and
  `review_feedback_scopes.py`; manual, browser, and accessibility evidence
  actions belong under `manual_evidence_actions.py`,
  `browser_evidence_actions.py`, and `accessibility_evidence_actions.py`.
  Artifact schema/redaction helpers remain in the existing evidence modules.
- Response-linked fixup inventory mutation belongs under
  `review_fixup_actions.py`; response-status derivation remains in
  `review_responses.py`.
- Verification preview, safe command templates, command evidence shaping, and
  lifecycle brief section assembly belong under dedicated changeset helper
  modules. `changeset_verification_readiness.py`, `command_evidence.py`, and
  `review_briefs.py` remain the lower-level schema/derivation owners where
  they already exist.
- Handoff and commit readiness should depend on extracted query, verification,
  safe-command, and command-evidence helpers rather than the broad
  `runtime/changesets.py` facade once those helpers exist.
- All v13 review-loop helpers must preserve local-first authority: feedback,
  manual evidence, browser/dashboard evidence, accessibility evidence,
  lifecycle briefs, handoff readiness, and commit preparation remain advisory
  unless the current event contract already records a canonical mutation.

#### Post-V14 Review-Loop Maturity Runtime Sub-Boundaries

- Lifecycle brief limitation collection, deduplication, priority ordering,
  overflow copy, and `ReviewBriefLimitationSummary` construction now live in
  `changeset_review_brief_limitations.py`; `changeset_review_brief_sections.py`
  consumes summarized limitation output while assembling the artifact. The raw
  retained evidence remains authoritative, and the current 20-item
  reviewer-safe artifact cap remains the behavior contract.
- Review brief section assembly now keeps
  `changeset_review_brief_sections.py` as the service-facing facade while
  `changeset_review_brief_core_sections.py` owns deterministic changeset,
  inventory, provenance, topology, verification, command-evidence,
  branch-candidate, and risk sections;
  `changeset_review_brief_review_sections.py` owns lifecycle, feedback,
  response, manual evidence, live evidence, stale-verification, and
  publication-boundary sections; and `changeset_review_brief_readiness.py`
  owns review-readiness state and reason derivation.
- Skipped live evidence semantics now stay in one runtime boundary:
  `skipped_evidence.py` owns labels, reasons, persisted skipped limitation
  strings, live/skipped item helpers, counts, and summaries used by browser
  evidence, accessibility evidence, lifecycle briefs, verification readiness,
  and handoff readiness. Skipped evidence remains advisory and does not become
  passing release evidence.
- Review response declarations should split from derivation. Response and fixup
  inventory models belong in `review_response_models.py`; response state,
  blocker, verification, freshness, and safe-action derivation belong in
  `review_response_status.py`; fixup artifact JSON and path-scope helpers
  belong in `review_fixup_*` modules.
- Changeset-level response summary assembly should stay reusable by detail
  views, CLI, web, verification previews, handoff readiness, and commit
  readiness without owning fixup artifact creation.
- Commit and handoff readiness may share signal aggregation helpers, but the
  public `CommitReadinessSignal` and `HandoffReadinessSignal` surfaces keep
  their distinct product vocabularies, non-claims, and safe-action copy.

#### Post-V15 Repository-Intelligence Runtime Sub-Boundaries

- `repository_intelligence_layout.py` should remain the layout discovery
  coordinator while `repository_intelligence_layout_models.py`,
  `repository_intelligence_layout_common.py`,
  `repository_intelligence_layout_packages.py`,
  `repository_intelligence_layout_paths.py`,
  `repository_intelligence_layout_recipes.py`,
  `repository_intelligence_layout_docs.py`,
  `repository_intelligence_layout_evals.py`,
  `repository_intelligence_layout_ownership.py`,
  `repository_intelligence_layout_subsystems.py`, and
  `repository_intelligence_layout_release.py` own models/common helpers,
  package/path discovery, command recipes, docs/eval recipe sources, owner
  hints, subsystem hints, and release surfaces.
- `repository_intelligence_refresh.py` should own shared refresh orchestration
  for building index snapshots with active memory, building topology from the
  resulting index, writing managed artifacts, and returning summary metadata.
  CLI and background-job paths should consume that runtime service while
  background-job modules retain job progress and completion event recording.
- `runtime_context_memory_use.py` should own
  `WorkspaceMemoryUsedInContext` event construction and dedupe. Runtime context
  derivation should read as snapshot derivation plus explicit optional
  side-effect recording.
- `eval_recommendation_repository_intelligence.py` should remain the public
  enrichment entrypoint while repository matching, source metadata, and recipe
  recommendation construction live in
  `eval_recommendation_repository_matching.py`,
  `eval_recommendation_repository_metadata.py`, and
  `eval_recommendation_repository_recipes.py`.
- `repository_intelligence_freshness.py` should be the shared runtime owner
  for source labels and safe next-action wording across index, topology,
  memory, eval metadata, command recipe, and release-surface freshness cues.

#### Post-V15 Repository CLI Sub-Boundaries

- `repository_commands.py` should remain the compatibility dispatcher for the
  `repo` command family, while `repository_command_status.py`,
  `repository_command_refresh.py`, `repository_command_inspection.py`,
  `repository_command_memory.py`, and `repository_command_formatters.py` own
  status/staleness, immediate/background refresh, inspection/recommendation,
  memory-candidate behavior, and human output formatting.
- CLI helpers may adapt runtime query results into stable command JSON payloads
  and terminal copy, but should not duplicate transport-agnostic path
  inspection matching or freshness derivation that belongs in runtime query
  helpers.

#### Post-V15 Repository Web Sub-Boundaries

- `web/repository_intelligence_api.py` should remain the compatibility facade
  over web response models and builders. Response models belong in
  `repository_intelligence_api_models.py`, while overview/freshness,
  path/subsystem/recipe, recommendation, and memory-candidate builders belong
  in focused web-owned helper modules.
- `web/routes/repository_intelligence.py` should stay a FastAPI declaration
  surface while `web/routes/repository_intelligence_queries.py` and
  `web/routes/repository_intelligence_services.py` own snapshot loading,
  query parameter coercion, pagination, service construction, and HTTP error
  translation.
- Web builders must not import FastAPI dependencies, and runtime query helpers
  must not import web response models.

#### Post-V15 Frontend Repository Sub-Boundaries

- `frontend/components/console/knowledge-autonomy/repository-panels.tsx`
  should remain the dashboard repository entrypoint while
  `repository-overview.tsx`, `repository-path.tsx`,
  `repository-recipes.tsx`, `repository-memory.tsx`,
  `repository-freshness.tsx`, and `repository-format.ts` own overview, path,
  recipe, memory, freshness, and pure formatting concerns.
- `frontend/stores/knowledge-store.ts` should remain the public store facade
  while `knowledge-store-repository.ts`, `knowledge-store-memory.ts`, and
  `knowledge-store-actions.ts` own repository loading, memory candidate
  loading, and action state/messages. Transport stays in stores; components do
  not take over API calls.

#### Post-V15 Guardrail And Core-Domain Strategy

- post-v15 guardrails start with pre-extraction pressure-point caps and
  documented expectations, then add facade line-count and import-prefix
  expectations after `repository_command_*`,
  `repository_intelligence_layout_*`, `repository_intelligence_refresh.py`,
  web builder, frontend repository panel, and knowledge-store helper owners
  are introduced.
- `tests/unit/test_architecture_guardrails.py` now stays as the legacy
  validation entrypoint, while `tests/unit/architecture_guardrails/` owns the
  split backend import-direction, Python facade, frontend boundary,
  generated-file exclusion, pressure-point, and refactor-document checks.
- `glassbox.core.events` and `glassbox.core.models` should not be split during
  the first post-v15 pass. Future repository-intelligence core model movement
  should preserve public imports and event registration semantics explicitly.

#### Post-V15 Repository-Intelligence Core Domain Strategy

- The current repository-intelligence model family stays in
  `glassbox.core.models` for this roadmap. That family includes
  `RepositoryIndexProvenance`, `RepositoryIndexEntry`,
  `RepositoryIntelligenceSourceManifest`, `RepositoryIntelligencePathHint`,
  `RepositoryIntelligencePackageBoundary`,
  `RepositoryIntelligenceCommandRecipe`,
  `RepositoryIntelligenceOwnershipHint`, `RepositoryIntelligenceSubsystem`,
  `RepositoryIntelligenceReleaseSurface`,
  `RepositoryIntelligenceMemoryReference`, and `RepositoryIndexSnapshot`.
- A future extraction should use an explicit domain module such as
  `core/models_repository_intelligence.py` only when repository-intelligence
  growth makes validator ownership, snapshot-schema review, or import review
  materially harder in the broad public module. Do not split these models for
  line count alone, and do not split one-off field additions away from their
  neighboring snapshot contracts.
- If repository-intelligence event payloads are introduced later, they should
  move as a cohesive family into a module such as
  `core/events_repository_intelligence.py`, while `core/events.py` keeps
  `EventPayload`, `EventPayloadType`, `event_payload_adapter`,
  `EventEnvelope`, and public compatibility re-exports.
- Event payload registration must remain explicit and deterministic. Future
  repository-intelligence domain modules must not use dynamic discovery,
  import-time filesystem scans, plugin registration, runtime imports, store
  imports, CLI imports, web imports, or frontend imports to affect canonical
  persisted event payloads.
- `glassbox.core.models`, `glassbox.core.events`, and `glassbox.core` must keep
  compatibility re-exports during any future extraction so runtime, store, CLI,
  web, replay, eval, API schema, and test imports migrate deliberately rather
  than as a hidden side effect.

#### Post-V16 Operator-Flow Runtime Sub-Boundaries

- `evidence_graph.py` should remain the public runtime facade for
  `build_changeset_evidence_graph`, `build_session_evidence_graph`, summaries,
  claim/node lookup, and neighborhood traversal. `evidence_graph_models.py`
  should own graph-local summary/helper types, `evidence_graph_builder.py`
  should own `_GraphBuilder`, node/edge construction, caps, and summary
  helpers, changeset helpers should split inventory, verification, and review
  evidence families, `evidence_graph_session.py` should own session graph
  derivation, and `evidence_graph_queries.py` should own lookup and traversal.
- `verification_plan_builder.py` should remain the public verification-plan
  builder while `verification_plan_identity.py` owns stable IDs, dedupe keys,
  and coalescing; `verification_plan_entries.py` owns shared entry construction;
  recommendation, recipe, eval, readiness, and manual-only helpers own their
  source families; `verification_plan_skips.py` owns skipped-check and limit
  rows. Skipped and manual-only entries remain visible evidence posture, not
  proof of passing behavior.
- `operator_queue.py` should remain the public queue aggregator while
  `operator_queue_session_items.py`, `operator_queue_runtime_items.py`,
  `operator_queue_maintenance_items.py`, `operator_queue_changeset_items.py`,
  `operator_queue_sorting.py`, and `operator_queue_counts.py` own item
  derivation, stable ordering, dedupe, and count summaries. Maintenance rows
  stay advisory unless existing cue semantics say action is required.

#### Post-V16 Operator-Flow Web Sub-Boundaries

- `web/session_api_aggregate.py` should stay a transport facade over aggregate
  response models and builders. Route helpers should consume queue summaries
  through runtime facades and web builders, not duplicate queue sorting,
  evidence summary, or target-link derivation.
- `web/changeset_api_builders_detail.py` should keep detail response
  compatibility while verification-plan response shaping moves to
  `changeset_api_builders_verification.py` and evidence graph response shaping
  moves to `changeset_api_builders_evidence_graph.py` or a route-local graph
  query helper.
- Web builders may adapt runtime contracts into stable HTTP payloads and
  OpenAPI schemas, but runtime queue, graph, verification, and maintenance
  helpers must not import FastAPI response models.

#### Post-V16 Dashboard Cockpit Sub-Boundaries

- `operator-queue-lanes.tsx` should remain the workspace overview entrypoint
  while `operator-queue-models.ts`, `operator-queue-row.tsx`,
  `operator-queue-links.ts`, and `operator-queue-format.ts` own lane
  descriptors, row rendering, target/evidence links, and display copy.
- `evidence-graph-panel.tsx` should remain the graph panel entrypoint while
  `evidence-graph/summary.tsx`, `claims.tsx`, `nodes.tsx`,
  `relationships.tsx`, and `format.ts` own graph summary filters, claims,
  nodes, relationships, limitations, anchors, labels, and badge variants.
- `changeset/verification.tsx` should remain the changeset verification
  entrypoint while table, action-control, and formatting helpers own rendering
  and local form state. API calls stay in store action helpers such as
  `changeset-store-verification-actions.ts`.

#### Post-V16 Release-Gate And Guardrail Strategy

- `scripts/validate_v16_release_gate.py` should remain the operator command
  while `v16_release_gate_stages.py`, `v16_release_gate_advisory.py`,
  `v16_release_gate_summary.py`, and shared helper modules own deterministic
  stage assembly, advisory evidence rows, dry-run output, package/static
  evidence, dogfooding expectations, and summary metadata.
- post-v16 guardrails start with pre-extraction pressure-point caps for the
  runtime, web, frontend, and release-gate files named above. After
  `evidence_graph_*`, `verification_plan_*`, `operator_queue_*`, web builder,
  dashboard cockpit, and v16 release-gate helpers exist, guardrails should add
  facade line-count and import-prefix expectations that require delegation to
  those owner modules.
- Guardrails should not freeze generated OpenAPI, generated frontend API
  types, deterministic eval fixtures, release evidence artifacts, broad
  model-heavy core surfaces, or compatibility facades that are already thin.

#### Post-V16 Operator-Flow Core Domain Strategy

- Next-action, operator queue, evidence graph, maintenance cue, verification
  plan, and recovery-playbook model families currently remain in broad public
  core modules unless a roadmap task explicitly extracts them. A future
  extraction should use cohesive domain modules such as
  `core/models_operator_flow.py`, `core/types_operator_flow.py`,
  `core/models_evidence_graph.py`, and `core/models_verification_plan.py`
  only when validator ownership, enum/event review, or compatibility review
  becomes materially easier.
- `glassbox.core.models`, `glassbox.core.types`, `glassbox.core.events`, and
  `glassbox.core` must preserve public imports through compatibility
  re-exports during any operator-flow extraction. Event payload registration
  must stay explicit, deterministic, and free of runtime, store, CLI, web, or
  frontend imports.
- Do not split model-heavy code for line count alone. New operator-flow
  contracts should move only when the domain boundary is clear and the runtime,
  web, CLI, dashboard, replay, eval, OpenAPI, and tests can migrate
  deliberately.

### Post-V16 Accepted Compatibility Shims

- `src/glassbox/runtime/evidence_graph.py`: evidence graph public facade.
- `src/glassbox/runtime/verification_plan_builder.py`: verification plan
  public builder.
- `src/glassbox/runtime/operator_queue.py`: operator queue public aggregator.
- `src/glassbox/core/models.py`, `src/glassbox/core/types.py`, and
  `src/glassbox/core/events.py`: broad public core compatibility surfaces.
- `src/glassbox/web/session_api_aggregate.py`: session aggregate API facade.
- `src/glassbox/web/changeset_api_builders_detail.py`: changeset detail
  builder facade.
- `src/glassbox/web/routes/session_route_queries.py`: session route query
  helper facade.
- `src/glassbox/web/routes/changeset_route_actions.py`: changeset action
  helper facade.
- `frontend/components/console/workspace-overview/operator-queue-lanes.tsx`:
  dashboard operator queue entrypoint.
- `frontend/components/console/evidence-graph-panel.tsx`: dashboard evidence
  graph entrypoint.
- `frontend/components/console/changeset/verification.tsx`: dashboard
  verification plan entrypoint.
- `frontend/stores/changeset-store-review-actions.ts`: compatibility store
  action surface.
- `scripts/validate_v16_release_gate.py`: v16 release-gate operator
  entrypoint.

### Post-V15 Accepted Compatibility Shims

- `src/glassbox/cli/repository_commands.py`: repository command dispatcher.
- `src/glassbox/runtime/repository_intelligence_layout.py`: layout discovery
  coordinator over model/common, package/path, recipe, owner, subsystem, and
  release helper families.
- `src/glassbox/runtime/repository_intelligence_queries.py`: shared path
  inspection and repository-intelligence query facade.
- `src/glassbox/runtime/repository_intelligence_refresh.py`: shared refresh
  orchestration service.
- `tests/unit/test_architecture_guardrails.py`: legacy validation entrypoint
  over the split `tests/unit/architecture_guardrails/` guardrail suite.
- `src/glassbox/runtime/runtime_context_derivation.py`: runtime context
  derivation entrypoint over prompt-use recording helpers.
- `src/glassbox/runtime/eval_recommendation_repository_intelligence.py`:
  repository-intelligence enrichment entrypoint.
- `src/glassbox/web/repository_intelligence_api.py`: repository-intelligence
  web response model and builder facade.
- `src/glassbox/web/routes/repository_intelligence.py`: FastAPI declaration
  surface over route-local query and service helpers.
- `frontend/components/console/knowledge-autonomy/repository-panels.tsx`:
  dashboard repository panel entrypoint.
- `frontend/stores/knowledge-store.ts`: dashboard knowledge store facade.

### Store

The `store` package should own canonical persistence and projection application.

Its stable responsibilities are:

- schema and migration/bootstrap concerns
- append-only event-log reads and writes
- projection application and rebuild
- repository adapters over the raw storage helpers
- artifact storage and retrieval
- lineage and fork-point resolution rooted in persisted state

The `store` package should not own runtime orchestration, CLI formatting, or web response shaping.

#### Target Store Sub-Boundaries

- schema/bootstrap code should live separately from query and append logic
- raw event-store operations should be distinct from projection application helpers
- projection application should remain deterministic and rebuildable from `events`
- repository adapters should stay stable while internal storage helpers split underneath them
- the SQLite store now uses internal `sqlite_schema.py`, `sqlite_sessions.py`, `sqlite_events.py`, `sqlite_projections.py`, `sqlite_queries.py`, and `sqlite_fork.py` modules behind the stable `store/sqlite.py` facade
- `store/__init__.py` should stay limited to repository adapters, bootstrap helpers, and shared artifact models; raw SQLite and artifact helper imports should come from `store.sqlite` or `store.artifacts`

#### Post-v8 Store Query Sub-Boundaries

- `sqlite_queries.py` should split by projection domain when it changes:
  transcript/runtime notes, approvals/tools/turn metrics, autonomy budgets,
  task projections, branch-search projections, and any workspace-memory
  adjacency queries should be owned by focused store read modules
- the projection read split now keeps `sqlite_queries.py` as a compatibility
  facade over focused `sqlite_query_*` modules for transcript, runtime notes,
  tools/approvals, turn metrics, autonomy budgets, tasks, and branch search
- query helpers should continue to derive from canonical events and
  deterministic projection tables. They should not call runtime services,
  background workers, provider diagnostics, HTTP serializers, or frontend
  state helpers
- `repositories.py` should remain the stable adapter surface for service
  protocols, but method bodies should be thin pass-throughs to store-owned
  modules once query domains split
- the repository adapter split now keeps `repositories.py` as the stable public
  facade for `SQLiteSessionRepository` and `FilesystemArtifactRepository`, with
  session, event/fork, projection-read, background-job, workspace-memory, task,
  branch-search, and artifact behavior owned by focused `repository_*` modules
- repository adapters may import store implementation modules and core/service
  contracts. They should not import runtime orchestration modules, web routes,
  CLI modules, or frontend code

#### V10 SQLite Schema Sub-Boundaries

- `sqlite_schema.py` keeps the public bootstrap and migration runner
  surface: `SCHEMA_VERSION`, `MIGRATIONS`, `BOOTSTRAP_STATEMENTS`,
  `open_database`, and `initialize_database`.
- Domain-specific table statements and migration helpers live behind the
  explicit, ordered registry grouped by projection family: sessions/runtime
  notes, tasks, verification ledger, checkpoints, compactions, tool attempts,
  background jobs, branch search, workspace memory, provider recovery, and
  long-run state.
- Schema helpers must remain idempotent and deterministic. They should not
  import runtime services, route serializers, CLI formatters, or frontend
  state, and they must not change table names, column names, indexes, or schema
  version during pure movement.

#### V11 Projection Sub-Boundaries

- Task projection application should remain rebuildable from canonical task,
  task-step, pause/resume, budget, and verification events. The
  `sqlite_projection_tasks.py` coordinator should preserve the compatibility
  import used by `sqlite_projections.py`, while task plan, step,
  pause/resume/terminal-state, and verification helpers sit below repository
  adapters.
- Background-job projection application should remain rebuildable from canonical
  job creation, lifecycle, retry, pause/cancel, progress, and recovery events.
  The `sqlite_projection_background_jobs.py` coordinator should preserve the
  compatibility import used by `sqlite_projections.py`, while creation,
  lifecycle/progress, pause/cancel, retry, and recovery helpers keep table
  shape, migration order, and rebuild outcomes unchanged.
- Projection helper extraction should not introduce abstract projection
  frameworks, dynamic handler discovery, runtime service imports, HTTP models,
  CLI formatters, or frontend state.

#### V13 Store Review-Loop Sub-Boundaries

- Changeset and review-loop projection helpers remain rebuildable from
  canonical changeset, feedback, response, manual-evidence, browser-evidence,
  accessibility-evidence, verification, and brief events.
- `sqlite_projection_changesets.py` and `sqlite_projection_review_loop.py` may
  remain compatibility coordinators while lifecycle, inventory, readiness,
  feedback, fixup inventory, and evidence handlers move into event-family
  helpers.
- Changeset query helpers should split by read-model family when they change:
  detail, inventory/status, review feedback, manual evidence, live evidence,
  and response summaries. Row ordering, pagination, include flags, and enum
  coercion stay unchanged.
- Repository adapters should expose the existing changeset and review-loop
  service contracts while delegating method bodies to store-owned domain
  modules. Store modules must not import runtime services, web response models,
  CLI formatters, or frontend code.

### Services

The `services` package should remain the narrow contract layer between orchestration code and concrete persistence or runtime implementations.

Its stable responsibilities are:

- repository protocols
- service protocols
- shared contract surfaces consumed by CLI, runtime, and web wiring

The `services` package should not accumulate concrete behavior merely to avoid imports.

#### V11 Service Contract Strategy

- `services/contracts.py` may remain broad while it is mostly protocol and
  model declarations. It should not split for line count alone.
- The `GBX-R432` review keeps `services/contracts.py` as the public contract
  owner for now. The current pressure is breadth of protocol surface, not mixed
  concrete behavior, so a behavior-preserving split would mainly create
  re-export churn without a clearer ownership win.
- Future contract splits should follow stable domains: session repository,
  artifact repository, background jobs, workspace memory, tasks, branch search,
  and session service.
- `glassbox.services` and `glassbox.services.contracts` should remain stable
  public import surfaces through compatibility re-exports if domain contract
  modules are introduced.
- Contract modules must stay free of concrete store, runtime, CLI, web,
  frontend, and script imports.
- When a domain split becomes worthwhile, the preferred sequence is to move one
  cohesive protocol family into `services/contracts_<domain>.py`, re-export it
  from `services/contracts.py`, keep `services/__init__.py` unchanged, and add
  import-smoke plus repository-adapter coverage before moving the next family.

### CLI

The `cli` package should own terminal-facing command parsing, command orchestration, and human-readable presentation.

Its stable responsibilities are:

- argument parsing and top-level command dispatch
- command orchestration over runtime services and query services
- interactive terminal session control
- event-driven terminal rendering
- CLI-specific human-readable and JSON report formatting

The `cli` package should not build its own parallel session-query logic when the runtime can provide the same read model once.

#### Target CLI Sub-Boundaries

- parser construction should be separate from command execution
- one-shot command execution should be separate from long-lived interactive session control
- reporting and formatting should be separate from command flow control
- command handlers should depend on service and query contracts, not on raw SQLite helpers
- the CLI entry split now keeps parser registration and argument helpers in `src/glassbox/cli/parser.py`, top-level dispatch and error handling in `cli/entry.py`, shared runtime/rendering helpers in `cli/runtime_runner.py`, and preserves `glassbox.cli:main` as a thin compatibility wrapper
- workflow-family command handlers now live in `cli/interactive_commands.py`, `session_state_commands.py`, `replay_eval_commands.py`, and `server_commands.py`, with shared path resolution in `cli/path_helpers.py` and direct imports from their owning CLI modules
- long-lived terminal prompt routing, blocked-state messaging, prompt redraw context, and attach-session gating now live in `cli/interactive_session.py`, which owns the interactive input seams directly
- status/runtime-context rendering now lives in `cli/status_session.py`, with
  `cli/status_formatters.py` retained as a thin compatibility facade; task
  status rendering lives in `cli/status_task.py`, observability status
  rendering lives in `cli/status_observability.py`, knowledge provenance
  formatting lives in `cli/status_knowledge.py`, replay/eval report rendering
  and replay JSON/exit-code helpers live in `cli/replay_eval_formatters.py`,
  and CLI internals no longer route through `cli/__init__.py` for those helpers

#### V11 CLI Operator-Surface Sub-Boundaries

- Status formatting should split by operator surface when it changes: session
  status, task status, observability status, policy evidence, and knowledge
  posture. CLI modules own copy and terminal layout; runtime helpers own
  transport-agnostic evidence and safe-command derivation.
- Command-guide behavior should separate command metadata, workflow grouping,
  JSON serialization, and terminal rendering. It remains aligned with the real
  parser and must not become a second parser definition source.
- The command-guide split now keeps `cli/command_guide.py` as a compatibility
  facade while `cli/command_guide_data.py`, `cli/command_guide_workflows.py`,
  `cli/command_guide_json.py`, `cli/command_guide_render.py`, and
  `cli/command_guide_models.py` own metadata, workflow grouping,
  serialization, rendering, and typed command-guide models.
- Interactive session commands should separate chat/run/attach launch,
  daemon-forwarded actions, local session actions, autonomy option resolution,
  and parser wiring while preserving daemon-owner safety checks, plain-mode
  compatibility, exit codes, and current command options.
- The interactive split now keeps `cli/interactive_commands.py` as the stable
  command-wrapper surface while `cli/interactive_autonomy.py`,
  `cli/interactive_local_actions.py`, and
  `cli/interactive_daemon_actions.py` own autonomy option resolution, local
  session mutations, and daemon-forwarded action payloads. Session launch
  parser options live in `cli/parser_session_launch.py`.

#### V13 CLI And Terminal Review-Loop Sub-Boundaries

- `cli/changeset_commands.py` should remain the scriptable `glassbox changeset`
  command facade. Runtime-context opening and service wiring belong in
  `changeset_command_handlers.py`; JSON payload builders belong in
  `changeset_command_payloads.py`; terminal formatting belongs in
  `changeset_command_formatters.py`.
- `cli/parser_changesets.py` should remain the parser entrypoint while feedback,
  evidence, verification/brief/handoff, and commit-preparation parser families
  move into parser helper modules.
- TUI and plain interactive `/review` and `/changeset` parsing, disabled
  reasons, current-session defaults, action routing, and feedback messages
  belong in review-specific helpers. The scriptable changeset CLI remains the
  lower-level API.
- Terminal helpers may render runtime-derived posture and safe commands, but
  they should not duplicate runtime evidence, readiness, publication-boundary,
  or response-status derivation.

#### Post-V14 Terminal Review-Loop Sub-Boundaries

- `cli/interactive_client.py` should split client models/protocols, SSE event
  parsing, local runtime actions, daemon HTTP actions, and review-loop action
  guidance into focused CLI helpers. The compatibility entrypoint should
  preserve plain interactive behavior, daemon attach behavior, and current
  review command copy.
- Terminal guidance for review-loop fixups, skipped advisory evidence,
  verification posture, handoff readiness, and safe next actions may format
  runtime-derived data, but it should not rederive response status, readiness
  blockers, or publication-boundary rules.
- `cli/changeset_command_handlers.py` is the follow-on scriptable command
  pressure point. New lifecycle, feedback, evidence, verification, readiness,
  adoption, export, and commit-preparation command behavior should move into
  command-family helpers while `changeset_commands.py` remains the user-facing
  command facade. The post-v14 split keeps `changeset_command_handlers.py` as
  the compatibility import surface over `changeset_command_lifecycle.py`,
  `changeset_command_feedback.py`, `changeset_command_evidence.py`, and
  `changeset_command_readiness.py`.

#### Post-v8 TUI Sub-Boundaries

- the TUI conversation split now keeps `cli/tui/conversation.py` as a
  compatibility facade, with state models in `conversation_models.py`, snapshot
  hydration in `conversation_hydration.py`, canonical event reduction in
  `conversation_reducer.py`, and display/action derivation in
  `conversation_selectors.py`
- TUI reducers may depend on core event/model types and CLI-local snapshot
  models, but should not import raw store helpers, runtime workers, HTTP
  routes, or frontend modules
- the TUI widget split now keeps `cli/tui/widgets.py` as a compatibility
  facade over pane-family modules for header/footer, transcript, action strip,
  composer, command palette, and details rendering
- widget classes may depend on terminal state/selectors and Textual/Rich, but
  pure render helpers should remain easy to unit test without starting the TUI
  application
- the TUI app split keeps `cli/tui/app.py` as the Textual lifecycle owner while
  command dispatch, stream lifecycle, widget refresh, feedback mapping, and
  local artifact path resolution live in focused `app_*` helpers

### Web

The `web` package should own HTTP transport and browser assets.

Its stable responsibilities are:

- FastAPI app and route registration
- HTTP request validation and response serialization
- SSE transport
- browser assets, frontend state handling, and DOM orchestration

The `web` package should not own the canonical logic for deriving session summaries, next-action guidance, or runtime-context shapes.

#### Target Web Backend Sub-Boundaries

- routes should focus on HTTP concerns
- shared runtime query code should provide session snapshot composition
- transport-specific response models may wrap query-domain models, but should not redefine the business logic that produces them
- the session route transport split keeps `src/glassbox/web/session_api.py` as
  the stable compatibility import surface while request/response model families
  and serializers live in focused `session_api_*` modules for common detail
  pages, actions, selected-session snapshots, operator aggregates, and builders
- v10 session-route helpers should own HTTP-local query composition for
  aggregate, snapshot, transcript, event log, tool calls, metrics,
  checkpoints, compactions, artifacts, and runtime summary reads while route
  modules remain the FastAPI declaration and dependency boundary
- v10 session-route action helpers should own message submission, answer
  submission, cancellation, forks, tool-attempt retry/abandon, and compaction
  refresh/invalidation orchestration while preserving current status codes and
  validation behavior
- v10 task-route helpers should own HTTP-local list/detail/steps/events and
  background-job adjacency queries plus plan approval, continuation, continuation
  windows, pause windows, pause/resume/cancel, and budget-adjustment actions
- web response models and Pydantic serializers belong in web API modules, not
  in runtime query services

#### V13 Changeset Web Sub-Boundaries

- `web/changeset_api.py` remains the stable compatibility facade for changeset
  route imports. Transport models belong in `changeset_api_models.py` and
  review-loop model modules; response builders belong in
  `changeset_api_builders.py` and focused builder helpers.
- Web builder modules may consume runtime query/detail/readiness models, but
  they must not import FastAPI dependencies or become runtime service owners.
- `web/routes/changesets.py` remains the FastAPI declaration surface. Service
  factories, repository casts, workspace-root lookup, route request helpers,
  and HTTP error translation belong in route-local helper modules.
- Route helpers preserve paths, response models, status codes, validation
  patterns, OpenAPI shape, local evidence advisory copy, and publication-boundary
  non-claims.

#### Post-V14 Changeset Web Sub-Boundaries

- `web/routes/changesets.py` should continue to preserve FastAPI route
  declarations while repeated repository lookup, workspace-root lookup, action
  execution, post-mutation detail reload, and HTTP error translation move into
  route action helpers.
- `web/changeset_api_builders.py` may remain the compatibility mapper while
  changeset summary/detail, review-loop feedback, readiness, verification,
  evidence, and commit-preparation builder families split into focused pure
  builder modules. Builder helpers own transport serialization only.
- Web response models and generated OpenAPI/frontend types remain transport
  contracts. Runtime query services must not import them, and refactor-only
  movement must refresh generated contracts only when payload shapes
  intentionally change.

#### Historical Web Frontend Sub-Boundaries

These sub-boundaries describe the removed no-framework dashboard split. They are
kept only as historical refactor context; current dashboard architecture follows
the Next.js SPA contract in [architecture.md](./architecture.md) and
[tasks-v3.md](./tasks-v3.md).

- reducer and snapshot-normalization logic should stay pure
- pane rendering should stay pure and be grouped by UI responsibility
- fetch/SSE transport and DOM-binding logic should live outside pure reducers and renderers
- the detailed historical browser-module map lives in [dashboard-frontend-boundaries.md](./dashboard-frontend-boundaries.md)
- the former reducer, renderer, transport, and DOM orchestration files were removed in GBX-472 after SPA parity and route flip tasks completed

#### Current Next.js Dashboard Sub-Boundaries

- `frontend/stores/dashboard-stores.ts` is now a compatibility facade that
  re-exports console, session, task, knowledge, and branch-search store
  factories and public state types from their domain modules. Existing call
  sites can keep the stable import path until they intentionally move to domain
  modules
- dashboard store domains are split into session summary/detail streaming,
  task queue/detail/action state, workspace memory/repository inspector state,
  branch-search list/detail/action state, and shared request/action/load-state
  helpers in `frontend/stores/store-actions.ts`
- dashboard stores should depend on generated API client types, route-state
  helpers, stream transport helpers, and pure frontend store utilities. They
  should not import React components or server-only modules
- autonomy console components keep stable public entrypoints while task,
  knowledge, branch-search, and verification-cue presentation sections live in
  focused `*-sections.tsx` modules. These section modules own list/detail,
  evidence, action-control, and formatting UI while preserving current routes,
  API calls, and workflow behavior
- the v10 task-autonomy section split should move queue filtering/navigation and
  table rendering into task-queue-owned modules, plan inspection/detail layout
  into task-inspector modules, pause/resume/continue/cancel/approval/background
  job/budget controls into task-actions modules, verification posture and
  evidence drilldown into task-evidence modules, and event/format helpers into
  pure non-React modules
- the task-autonomy split now keeps
  `frontend/components/console/task-autonomy-sections.tsx` as a compatibility
  facade over `task-autonomy/queue.tsx`, `inspector.tsx`, `actions.tsx`,
  `evidence.tsx`, and pure helper modules in `format.ts` and `types.ts`
- verification cue rendering should consume typed pure derivation results for
  policy, eval coverage, replay drift, provider evidence, release evidence,
  artifact grouping, and path overlap rather than recomputing cue facts inline
- session compare panes should consume pure comparison analysis for branch
  metadata, transcript divergence, tool activity, policy outcomes, runtime
  projection facts, and string-set comparisons
- the verification/compare split now keeps
  `frontend/components/console/verification-cues.tsx` and
  `session-inspector/panes/compare-pane.tsx` as renderers over pure analysis
  helpers in `verification-cues-analysis.ts` and
  `session-inspector/panes/compare-analysis.ts`
- `workspace-console.tsx` should remain the surface composition owner while
  route synchronization, popstate handling, per-surface load/reset behavior, and
  repeated action binding move into focused hooks/helpers
- the workspace-console split now keeps
  `frontend/components/console/workspace-console.tsx` as the store/state
  selection and surface composition owner, with URL synchronization and
  per-surface load/reset behavior in `workspace-console/routing.ts` and repeated
  action bindings in `workspace-console/actions.ts`
- session-inspector diagnostic panes keep `diagnostics-panes.tsx` as a stable
  export facade while runtime context, metrics, event/projection evidence, and
  shared diagnostic pagination live in focused pane modules under
  `frontend/components/console/session-inspector/panes/`
- frontend components should consume store state and generated API types, not
  duplicate backend event derivation rules that already exist in runtime/store
  read models

#### V11 Frontend Confidence-Surface Sub-Boundaries

- Knowledge autonomy sections should split into summary, memory cue list,
  repository-index posture, provenance drilldown, action controls, and pure
  formatting helpers. They consume typed API/store state and must not recreate
  backend knowledge ranking in React components.
- Branch-search sections should split into candidate list, candidate decision
  card, evidence details, verification recommendation, action controls, and
  pure risk/cost/provenance formatting helpers. Branch-search UI remains
  non-mutating unless it calls an existing explicit action.
- Existing `knowledge-autonomy-sections.tsx` and
  `branch-search-sections.tsx` entrypoints may remain compatibility facades
  while owned section families are introduced.
- `frontend/stores/session-store.ts` should keep `createSessionStore` stable
  while stream lifecycle, detail pagination, local drafts, and action mutations
  move into store-owned helpers. Store helpers may import API/SSE utilities and
  pure state reducers, but not React components or backend source.
- The session-store split now keeps `frontend/stores/session-store.ts` as the
  stable factory and type facade while `session-store-stream.ts`,
  `session-store-pagination.ts`, `session-store-drafts.ts`,
  `session-store-actions.ts`, `session-store-shared.ts`, and
  `session-store-types.ts` own stream lifecycle, detail pagination, draft
  shaping, action mutations, shared guards, and public store types.

#### V13 Frontend Changeset Sub-Boundaries

- `frontend/components/console/changeset-console.tsx` remains the stable
  component entrypoint. Types, badge variants, fact rows, state labels, and
  shared presentation helpers belong under `components/console/changeset/`.
- Changeset list, detail shell, actions, feedback, evidence, verification,
  handoff, and commit-preparation sections should split into focused component
  modules without changing visual hierarchy, accessibility labels, advisory
  copy, or local form-state behavior.
- `frontend/stores/changeset-store.ts` owns transport and action state. Store
  action groups and selectors may split into helper modules, but React
  components must continue to consume store state rather than calling the API
  directly.
- Frontend changeset formatting helpers should consume typed API/store state and
  must not duplicate backend review-loop derivation, response-status logic,
  readiness scoring, or publication-boundary rules.

#### Post-V14 Frontend Changeset Sub-Boundaries

- `frontend/stores/changeset-store-actions.ts` should split list/detail reload,
  lifecycle actions, review-loop actions, readiness/commit-preparation actions,
  action-message shaping, and branch-search adjacency into store-owned helpers.
  Components continue to consume store state and action methods.
- Frontend skipped-evidence and review-posture helpers may normalize typed API
  values for display, but they must not recreate backend skipped-evidence
  recognition, response-status derivation, readiness blockers, or
  publication-boundary authority.
- `frontend/api/client.ts` may group endpoint families behind the existing API
  facade. Transport stays in the API/store layer and must not move into React
  components.

### Replay And Eval

Replay and eval logic lives in `runtime`, but it should maintain its own internal boundaries.

Its stable responsibilities are:

- replay bundle loading and export
- deterministic runtime playback
- normalized-state comparison and mismatch collection
- replay triage and eval summary/report generation

Its internal ownership should stay explicit:

- replay manifest models, builders, and artifact loading should live separately from replay execution flow
- enriched-context fingerprinting and normalization helpers should be reusable by live capture and replay comparison without being hidden inside the recorder
- the live replay recorder should stay focused on capture-time orchestration, artifact writes, and event linkage rather than owning manifest semantics
- the replay capture split now uses `src/glassbox/runtime/replay_manifests.py`, `replay_fingerprints.py`, and a smaller `replay_capture.py` recorder module
- the replay runner split now keeps `src/glassbox/runtime/replay.py` as the stable facade while moving bundle loading and export to `replay_bundle_io.py`, execution coordination and failure mapping to `replay_orchestrator.py`, isolated deterministic execution to `replay_execution.py`, normalized-state comparison to `replay_compare.py`, and outcome classification to `replay_triage.py`
- eval-suite input discovery and output-directory selection now live in `src/glassbox/runtime/eval_inputs.py` so suite execution, summary loading, and CLI report flows share one typed input boundary
- the eval reporting split now keeps `src/glassbox/runtime/eval_summary.py` as the stable facade while moving suite payload and job-summary construction to `eval_summary_suite.py`, release-signoff aggregation to `eval_summary_release.py`, annotation helpers to `eval_summary_annotations.py`, and shared report models to `eval_summary_models.py`
- v11 recommendation helpers should keep recommendation behavior stable while
  making surface rows, long-run rows, execution plans, recipes, release-gate
  command grouping, and terminal formatting separately reviewable
- v11 release-gate helpers should keep `scripts/validate_v11_release_gate.py`
  as the standalone operator command while making stage summaries, advisory
  provider evidence, retained evidence rendering, and dry-run planning testable
  without executing the full gate
- The v11 release-gate split now keeps
  `scripts/validate_v11_release_gate.py` as the operator entrypoint while
  `scripts/v11_release_gate_helpers.py` owns stage summary rows, dry-run
  planning, retained evidence summary writing, advisory provider evidence rows,
  and terminal summary rendering.
- The v13 release-gate script should follow the same pattern: keep
  `scripts/validate_v13_release_gate.py` as the operator entrypoint while
  v13-specific stage construction, review-loop evidence rows, browser and
  accessibility advisory rows, dry-run planning, and summary metadata move into
  `scripts/v13_release_gate_helpers.py` or focused helper functions.
- The v14 release-gate helper split should keep
  `scripts/validate_v14_release_gate.py` as the operator entrypoint while
  inherited gate stages, v14 stage construction, advisory provider evidence,
  advisory UX evidence, dry-run copy, evidence-dir resolution, and summary
  metadata move into focused helpers under
  `scripts/v14_release_gate_helpers.py` or adjacent release-gate helper
  modules.

The replay and eval stack should not maintain a bespoke copy of live model-loop behavior when a shared execution boundary can serve both paths.

### Tools

The `tools` package should own tool implementations and policy decisions at the
command/tool boundary.

Its stable responsibilities are:

- tool registration and execution wrappers
- command/read/patch/workflow tool behavior
- policy decisions for approval, denial, and autonomy permits
- traceable policy reasons and approval messages

The `tools` package should not own runtime task orchestration, route
serialization, or CLI presentation.

#### V10 Tool Policy Sub-Boundaries

- `tools/policy.py` now keeps `ToolPolicyEngine`, `ToolPolicyContext`,
  `ApprovalMode`, and public decision ergonomics stable while delegating
  specialized behavior.
- Path-scope behavior now lives in `policy_paths.py`: path normalization,
  workspace containment, extension matching, and path argument extraction.
- Manifest rule matching and outcome resolution now live in `policy_rules.py`.
- Autonomy budget/risk permit logic and approval-behavior descriptions now live
  in `policy_autonomy.py`.
- Default, rule, and autonomy approval message construction now lives in
  `policy_messages.py`.
- Destructive-command and command-text heuristics now live in
  `policy_command_risk.py`; shared context/outcome models live in
  `policy_models.py`.
- Policy helpers may depend on policy config/models and standard-library path
  or shell parsing. They should not import runtime services, web routes, CLI
  formatters, store implementations, or frontend code.

### Core Events And Models

The `core` package owns shared domain identifiers, event payloads, models, and
cross-subsystem types.

Large core event and model files are model-heavy public infrastructure. They
should not be split for cosmetic line-count reasons. A future split is
appropriate only when a domain expansion would make event registration,
discriminated-union maintenance, or review ownership error-prone.

#### V10 Core Domain Strategy

- `glassbox.core.events` and `glassbox.core.models` should remain stable public
  import surfaces even if domain modules are introduced underneath them.
- Candidate future event/model domains are sessions, turns, tools, tasks,
  branch search, background jobs, workspace memory, repository index, provider
  recovery, verification, and compaction. Optional modules should be introduced
  one domain at a time, with names that make ownership obvious, such as
  `core/events_tasks.py`, `core/events_background_jobs.py`,
  `core/models_tasks.py`, or `core/models_workspace_memory.py`.
- `core/events.py` should keep the base `EventPayload`, `EventPayloadType`,
  `event_payload_adapter`, `EventEnvelope`, and compatibility re-exports. If
  event payload classes move into domain modules, `core/events.py` remains the
  single registration point.
- `core/models.py` should keep compatibility re-exports for shared public
  records and value models. Domain modules should own only cohesive model
  families whose validators and review ownership naturally travel together.
- Event payload registration must stay explicit and deterministic. If payloads
  move into domain modules, the discriminated union should be assembled from an
  explicit registry or manually maintained union in `core/events.py`; dynamic
  discovery, import-time filesystem scans, and plugin-style event registration
  are not appropriate for canonical persisted events.
- Event serialization tests should continue to prove that canonical event names,
  discriminator values, envelope correlation properties, and payload shapes are
  unchanged. Any future implementation split should run import-smoke,
  `tests/unit/test_core_events.py`, `tests/unit/test_core_models.py`,
  SQLite event-store/projection tests, replay/eval tests, and API/schema tests
  when the moved domain affects those surfaces.
- Do not split model-heavy code for line count alone. Keep a domain in the
  current public module when the change is a small field addition, a shared
  validator, a cross-domain value object, or a compatibility model usually
  reviewed with neighboring contracts.
- Core modules should not import runtime, store, CLI, web, frontend, or provider
  execution code. They may define shared models consumed by those layers.

## Dependency Direction Rules

The intended dependency direction for this refactor pass is:

- `core` defines shared domain types and event models
- `services` defines contracts over repository and service boundaries
- `store` implements persistence and repository adapters using `core` and `services`
- `runtime` orchestrates behavior using `core`, `services`, and repository/service implementations
- `cli` depends on `runtime`, `services`, and CLI-local presentation modules
- `web` depends on `runtime`, `services`, and web-local transport or browser modules

The practical rules are:

- `cli` must not depend directly on raw `store/sqlite.py` helpers
- `web` route modules must not become the canonical place for session-query logic
- `store` must not depend on `runtime`, `cli`, or `web`
- `services` must remain concrete-implementation free
- `runtime` may depend on `store` implementations in bootstrap code, but orchestration logic should prefer service or repository contracts where practical
- package-root imports should not be used as a convenience layer when they hide ownership of replay, turn execution, context building, or raw persistence helpers
- post-v8 runtime collector, repository-index, and memory-extraction helpers
  must not import web routes, CLI/TUI widgets, frontend code, or raw SQLite
  helpers directly
- post-v8 store read modules must stay below runtime and transport layers:
  they may shape projection records, but runtime query services and web routes
  own operator-facing summaries and response models
- TUI state and render modules must not import raw store modules or runtime
  background-job orchestration. They should consume events, snapshots, and
  CLI-local state only
- frontend stores must not import React components, Next.js server modules, or
  backend source files. Components should not become store-factory modules
- v10 frontend derivation helpers should be pure and browser-state free; store
  modules own transport, components own presentation and local interaction
  state
- web route helpers may own HTTP-local orchestration and serialization, but
  runtime task/session query services must remain transport-agnostic
- runtime provider scoring and canary evidence helpers must not import CLI,
  web, store implementations, or frontend modules
- tool-policy helper modules must not import runtime orchestration, web routes,
  CLI formatters, store implementations, or frontend modules
- SQLite schema domain helpers must stay below runtime and transport layers and
  must not perform dynamic discovery that hides migration order
- v11 confidence helpers should keep derivation below presentation: runtime
  modules may derive knowledge, branch-search, verification, handoff, recovery,
  and compaction posture, while CLI/web/frontend modules render or serialize it
  without duplicating the underlying rules
- v11 release-gate helper modules used by scripts may depend on runtime eval
  models and standard library filesystem/process helpers, but should not import
  CLI renderers, web routes, frontend code, or concrete dashboard state
- session export/import redaction helpers must not depend on CLI, web,
  frontend, or raw `.glassbox` filesystem layout beyond explicit package input
  paths
- v13 review-loop runtime helpers must stay below transport and presentation:
  they may derive changeset, feedback, evidence, verification, lifecycle brief,
  handoff, and commit posture, while CLI/web/frontend modules render or
  serialize those results without reimplementing the rules
- v13 web changeset builders own transport serialization only and must not
  import FastAPI when a pure builder function is enough
- v13 frontend changeset components should import store types and UI controls,
  not API transports, SSE transports, Next server modules, or backend source
- v13 store projection and query helpers must remain rebuildable/read-only
  derivations from canonical events or projection tables and must not import
  runtime services, CLI formatters, web models, or frontend state
- v13 release-gate helper modules may depend on standard library process/path
  helpers, inherited release-gate helpers, and runtime eval models, but should
  not import CLI renderers, web routes, frontend code, or dashboard component
  state
- post-v14 runtime review-loop maturity helpers must stay transport-agnostic:
  lifecycle limitations, response status, fixup inventory, skipped evidence,
  handoff readiness, and commit readiness may depend on core/runtime/service
  contracts, but not CLI formatters, FastAPI models, frontend code, or raw
  projection SQL
- post-v14 terminal helpers may call runtime services and format runtime-owned
  posture, but should not rederive skipped-evidence semantics, response status,
  readiness blockers, or publication-boundary rules
- post-v14 changeset API builders own transport serialization only and must
  not import FastAPI route dependencies
- post-v14 frontend stores own API transport and action state, while frontend
  display helpers remain pure over generated API/store types and avoid backend
  source, Next server modules, and React component imports where pure helpers
  are intended
- post-v14 release-gate helper modules may depend on inherited release-gate
  helpers, runtime eval models, and standard library filesystem/process
  helpers, but not CLI renderers, web routes, frontend code, or dashboard state

## Boundary Guardrails

The refactor roadmap now has lightweight enforcement for the most important boundaries above.

The guardrails are intentionally narrow:

- `tests/unit/test_architecture_guardrails.py` enforces dependency direction for `store`, `services`, CLI command modules, and web route modules
- the store and services packages are guarded against importing outward into `runtime`, `cli`, or `web`
- CLI command modules and web route modules are guarded against reaching into raw SQLite helpers instead of using repository, service, or query seams
- thin public facades are kept reviewable with soft size caps and explicit delegate-module checks for `runtime/__init__.py`, `store/sqlite.py`, `runtime/eval_summary.py`, `runtime/replay.py`, and the browser entry facades in `web/static/`
- those guardrails intentionally protect the public runtime entry surfaces around bootstrap, replay, and eval without turning internal coordinator modules such as `turn_engine.py` or `replay_orchestrator.py` into brittle size-capped policy targets
- post-v8 guardrails extend the same idea to autonomy-era areas: the current
  background-job, workspace-memory, observability, repository-index, and
  provider-evidence modules are checked against transport/UI/raw-store imports,
  public runtime autonomy facades are kept reviewable with explicit delegate
  import and size checks, TUI modules are checked against raw store and runtime
  worker imports,
  frontend stores are checked against component/server/backend imports, and
  `frontend/stores/dashboard-stores.ts` is kept reviewable as the
  compatibility facade over the source-owned domain store modules
- the largest frontend console entrypoints are kept reviewable as facades over
  domain section modules, including task autonomy, knowledge autonomy, branch
  search, and session-inspector diagnostics
- v10 guardrails in `tests/unit/test_architecture_guardrails.py` now keep the
  second-order pressure-point files and completed split helpers reviewable and
  block transport/raw-store/backend imports across task-autonomy sections,
  verification cue derivation, compare analysis, workspace-console routing,
  runtime task query helpers, provider canary/recommendation helpers,
  tool-policy helpers, and SQLite schema helpers
- v11 guardrails should extend the same narrow approach to confidence surfaces:
  keep public facades thin after helper extraction, block runtime helpers from
  importing CLI/web/frontend presentation code, block frontend section helpers
  from importing stores or backend source where they should be pure, and give
  every failure message a concrete destination module
- v13 guardrails initially freeze the known review-loop pressure points against
  further growth before extraction, block the clearest cross-layer imports, and
  document the future facade/helper expectations. Now that runtime, CLI, parser,
  web API, and changeset-route helpers exist, the corresponding Python facades
  also have explicit delegate-import and facade-size checks. Frontend changeset
  entrypoints remain under pre-split growth and dependency-direction guardrails
  until the Phase 85 component and store helper modules exist.
- post-v14 guardrails start with pre-extraction pressure-point caps for
  lifecycle brief limitations, review response/fixup status, handoff and commit
  readiness, plain interactive client behavior, changeset command handlers,
  changeset routes, changeset API builders, frontend API/store action owners,
  and v14 release-gate helpers. Post-extraction facade delegate checks should
  be added only after the owning helper modules exist.
- the completed post-v14 extraction slices now have narrow facade checks for
  lifecycle brief section families, review response helpers, commit/handoff
  readiness signals, interactive terminal clients, changeset command handlers,
  route-local changeset actions, web builder families, frontend endpoint
  groups, changeset store action helpers, and v14 release-gate stage,
  advisory, and summary helper families.

If a guardrail fails, the default repair should be to move new behavior into the owning split module or add one focused neighbor module, not to widen a facade or cross a subsystem boundary.

## V11 Closeout Validation Commands

Future confidence-surface refactors should start with the narrowest command
that covers the touched seam, then finish with the broader v11 closeout set
when behavior crosses recommendation, knowledge, branch-search, handoff, CLI,
frontend, recovery, or projection boundaries:

```bash
uv run pytest tests/unit/test_architecture_guardrails.py
uv run pytest tests/unit/test_release_candidate_docs.py
uv run pytest tests/unit/test_eval_recommendations.py tests/unit/test_knowledge_posture.py tests/unit/test_branch_search.py
uv run pytest tests/integration/test_cli_session_export.py tests/integration/test_cli_session_import.py
uv run pytest tests/unit/test_cli_facade_characterization.py tests/unit/test_command_guide.py
uv run pytest tests/unit/test_tool_attempt_retry.py tests/unit/test_context_compaction.py tests/unit/test_turn_event_recorder.py
uv run pytest tests/integration/test_sqlite_projections.py tests/integration/test_projection_rebuild.py tests/integration/test_background_jobs.py tests/integration/test_web_task_routes.py
pnpm --dir frontend typecheck
pnpm --dir frontend lint
pnpm --dir frontend test
uv run python scripts/validate_v11_release_gate.py --dry-run
```

## Stable Compatibility Facades

The following compatibility patterns are acceptable in the completed refactor
shape:

- `__init__.py` re-exports that preserve stable import paths while internals move behind them
- thin forwarding wrappers that preserve repository adapter behavior while internal store modules split
- thin adapter layers that keep existing route or CLI call sites working while shared query services are introduced
- module-local helper imports retained temporarily while large files are being extracted incrementally
- `frontend/stores/dashboard-stores.ts` re-exporting domain store factories
  while call sites move gradually
- TUI modules re-exporting terminal state, selectors, or render helpers while
  widget imports are updated in narrow follow-on tasks
- runtime autonomy facade modules preserving public worker, memory-capture,
  observability, repository-index, and provider evidence entry points while
  implementation details move into owned neighbors
- `task-autonomy-sections.tsx`, `verification-cues.tsx`, `compare-pane.tsx`,
  `workspace-console.tsx`, `web/routes/sessions.py`, `web/routes/tasks.py`,
  `runtime/task_queries.py`, `runtime/provider_canary.py`,
  `runtime/provider_recommendations.py`, `tools/policy.py`, and
  `store/sqlite_schema.py` may keep compatibility exports, explicit registries,
  or thin wrappers only when existing imports, route declarations, or migration
  ordering require a stable transition path
- v11 compatibility facades may include `eval_recommendation_output.py`,
  `eval_recommendation_engine.py`, `knowledge_posture.py`,
  `branch_decision_support.py`, `session_export.py`, `session_import.py`,
  `services/contracts.py`, `cli/status_formatters.py`,
  `cli/command_guide.py`, `cli/interactive_commands.py`,
  `cli/parser_sessions.py`, `frontend/components/console/knowledge-autonomy-sections.tsx`,
  `frontend/components/console/branch-search-sections.tsx`,
  `frontend/stores/session-store.ts`, `tool_attempt_recovery.py`,
  `context_compaction_service.py`, `turn_event_recorder.py`,
  `turn_tool_executor.py`, `sqlite_projection_tasks.py`, and
  `sqlite_projection_background_jobs.py` while existing commands, imports,
  routes, tests, and component entrypoints transition to focused helpers
- v13 compatibility facades may include `runtime/changesets.py`,
  `cli/changeset_commands.py`, `cli/parser_changesets.py`,
  `web/changeset_api.py`, `web/routes/changesets.py`,
  `frontend/components/console/changeset-console.tsx`,
  `frontend/stores/dashboard-stores.ts`, and
  `scripts/validate_v13_release_gate.py` while existing runtime imports,
  commands, parser entrypoints, routes, generated API consumers, component
  entrypoints, and release-gate invocations transition to focused helpers
- post-v14 compatibility facades may include
  `runtime/changeset_review_brief_sections.py`,
  `runtime/review_responses.py`, `runtime/handoff_readiness.py`,
  `runtime/commit_readiness.py`, `cli/interactive_client.py`,
  `cli/changeset_command_handlers.py`, `web/routes/changesets.py`,
  `web/changeset_api_builders.py`, `frontend/api/client.ts`,
  `frontend/stores/changeset-store-actions.ts`, and
  `scripts/v14_release_gate_helpers.py` while lifecycle limitations, response
  status, fixup artifacts, readiness signals, terminal review guidance,
  transport action patterns, endpoint groups, store action families, and
  release-gate summary shaping move into focused helpers

These facades are acceptable only while they stay thin, reviewable, and oriented
around stable public imports. New behavior should move into the owning domain
module first, with the facade forwarding or re-exporting only when compatibility
requires it.

### V10 Accepted Compatibility Shims

The completed v10 refactor accepts these compatibility surfaces and intended
owners:

- `task-autonomy-sections.tsx`: component compatibility facade; new queue,
  inspector, action, evidence, and formatting behavior belongs under
  `components/console/task-autonomy/`.
- `verification-cues.tsx`: renderer compatibility surface; new cue derivation
  belongs in `verification-cues-analysis.ts`.
- `session-inspector/panes/compare-pane.tsx`: renderer compatibility surface;
  new comparison derivation belongs in `compare-analysis.ts`.
- `workspace-console.tsx`: console composition surface; new URL/state
  synchronization belongs in `workspace-console/routing.ts`, and repeated
  action binding belongs in `workspace-console/actions.ts`.
- `web/routes/sessions.py` and `web/routes/tasks.py`: FastAPI declaration
  surfaces; new HTTP-local reads and mutations belong in
  `session_route_queries.py`, `session_route_actions.py`,
  `task_route_queries.py`, `task_route_actions.py`, or shared route utilities.
- `web/session_api.py`: response-model compatibility facade; new model families
  and serializers belong in the relevant `session_api_*` module.
- `runtime/task_queries.py`: `TaskQueryService` facade; new query contracts,
  assembly, verification, and repair derivation belong in `task_query_*`
  modules.
- `runtime/provider_canary.py`: provider-canary public facade; new scenario,
  execution, evidence, and report behavior belongs in `provider_canary_*`
  modules.
- `runtime/provider_recommendations.py`: provider recommendation public facade;
  new scoring dimensions and next-action guidance belong in
  `provider_recommendation_*` modules.
- `tools/policy.py`: policy-engine public facade; new path, rule, autonomy,
  message, command-risk, and shared policy behavior belongs in `policy_*`
  modules.
- `store/sqlite_schema.py`: bootstrap and explicit migration-registry surface;
  new projection-family DDL and idempotent migration helpers belong in
  `sqlite_schema_*` modules.
- `core/events.py`, `core/models.py`, and `core/__init__.py`: stable core import
  surfaces; future domain modules must keep explicit event registration and
  compatibility re-exports.

### V13 Accepted Compatibility Shims

The post-v13 refactor accepts these compatibility surfaces and intended owners:

- `runtime/changesets.py`: changeset runtime facade; new source derivation,
  workspace diff, query/detail, feedback, evidence, verification, safe-command,
  command-evidence, brief-section, and action behavior belongs in focused
  runtime helper modules.
- `cli/changeset_commands.py`: scriptable command facade; new service wiring
  belongs in changeset command handlers, JSON payload shaping belongs in
  payload helpers, and terminal formatting belongs in formatter helpers.
- `cli/parser_changesets.py`: parser entrypoint; new feedback, evidence,
  review, handoff, and commit-preparation parser wiring belongs in parser
  helper modules.
- TUI and plain interactive review entrypoints: generic app/session command
  modules may keep stable wrappers, while review-loop parsing and action routing
  belongs in review-specific helpers.
- `web/changeset_api.py`: response-model compatibility facade; new transport
  models and builders belong in focused web changeset/review-loop API modules.
- `web/routes/changesets.py`: FastAPI declaration surface; new service
  factories, request helpers, and error translation belong in route-local
  helper modules.
- `frontend/components/console/changeset-console.tsx`: component entrypoint;
  new changeset list/detail/action/evidence/feedback/verification/handoff
  presentation belongs under `components/console/changeset/`.
- `frontend/stores/changeset-store.ts`: store factory and action-state owner;
  new API action groups and selectors belong in changeset store helper modules.
- `scripts/validate_v13_release_gate.py`: operator entrypoint; new v13 gate
  stage construction, advisory evidence row shaping, dry-run planning, and
  summary metadata belongs in `scripts/v13_release_gate_helpers.py`.

For completed post-v13 extraction slices, guardrails now assert that:

- `runtime/changesets.py` imports the runtime-owned changeset, review-feedback,
  evidence, verification, and brief helper modules it re-exports.
- `cli/changeset_commands.py` and `cli/parser_changesets.py` delegate to their
  command-handler and workflow-family parser helpers.
- `web/changeset_api.py` delegates to transport model and response-builder
  helpers without importing FastAPI.
- `web/routes/changesets.py` delegates service construction, request coercion,
  workspace-root lookup, and common HTTP errors to route-local helpers.
- `frontend/components/console/changeset-console.tsx` delegates review-loop
  presentation sections to `components/console/changeset/`.
- `frontend/stores/changeset-store.ts` delegates API actions and selectors to
  focused store helper modules.
- `scripts/validate_v13_release_gate.py` delegates v13 release-gate stage,
  advisory-evidence, dry-run, evidence-dir, and summary metadata ownership to
  `scripts/v13_release_gate_helpers.py`.

### Post-V14 Accepted Compatibility Shims

The post-v14 refactor starts with these accepted compatibility surfaces and
intended owners:

- `runtime/changeset_review_brief_sections.py`: lifecycle brief assembly
  facade; limitation collection belongs in
  `changeset_review_brief_limitations.py`, section families belong in
  `changeset_review_brief_*_sections.py`, and readiness derivation belongs in a
  review-brief readiness helper.
- `runtime/review_responses.py`: review response facade; response models
  belong in `review_response_models.py`, status derivation belongs in
  `review_response_status.py`, fixup artifact/path helpers belong in
  `review_fixup_*` modules, and summary assembly belongs in
  `review_response_summary.py`.
- `runtime/handoff_readiness.py` and `runtime/commit_readiness.py`: readiness
  service surfaces; shared blocker, limitation, path, and safe-action signal
  helpers belong in `review_readiness_signals.py` while product-specific state
  vocabularies remain separate.
- `cli/interactive_client.py`: plain interactive client surface; client
  protocols, SSE parsing, local actions, daemon actions, and review guidance
  belong in focused interactive client helpers.
- `cli/changeset_command_handlers.py`: scriptable changeset command handler
  surface; lifecycle, feedback, evidence, verification, readiness, adoption,
  export, and commit-preparation action families now split across
  `changeset_command_lifecycle.py`, `changeset_command_feedback.py`,
  `changeset_command_evidence.py`, and `changeset_command_readiness.py`.
- `web/routes/changesets.py`: FastAPI declaration surface; repeated action,
  post-mutation reload, workspace-root, service, and HTTP error patterns now
  delegate to `changeset_route_actions.py`, `changeset_route_feedback.py`, and
  the existing route-local request, service, and error helpers.
- `web/changeset_api_builders.py`: transport builder facade; summary/detail,
  review-loop, readiness, verification, evidence, and commit-preparation
  builder families now split across `changeset_api_builders_detail.py`,
  `changeset_api_builders_review.py`, and
  `changeset_api_builders_readiness.py`.
- `frontend/api/client.ts`: frontend API facade; endpoint groups may split
  under API-owned modules while preserving component/store call sites. The
  current split keeps request/error handling in `client-core.ts`, sessions in
  `client-sessions.ts`, tasks and background jobs in `client-tasks.ts`,
  changesets and branch search in `client-changesets.ts`, and memory plus
  repository index in `client-workspace.ts`.
- `frontend/stores/changeset-store-actions.ts`: store action facade; list,
  detail, review-loop, readiness, commit-preparation, message, and branch
  adjacency behavior belongs in store-owned action helpers. The current split
  keeps list/detail reload and branch-search adjacency in
  `changeset-store-loaders.ts`, review-loop mutations in
  `changeset-store-review-actions.ts`, and operator-facing action text in
  `changeset-store-action-messages.ts`.
- `scripts/v14_release_gate_helpers.py`: v14 gate helper surface; inherited
  stage mapping, v14 stage construction, advisory evidence, dry-run copy,
  evidence-dir resolution, and summary metadata split into separately testable
  helper families under `v14_release_gate_stages.py`,
  `v14_release_gate_advisory.py`, and `v14_release_gate_summary.py`.

For completed post-v14 extraction slices, guardrails now assert that:

- `runtime/changeset_review_brief_sections.py` imports the core and review-loop
  section families it assembles.
- `runtime/review_responses.py` delegates models, status, fixup artifacts, and
  summary assembly to focused response helpers.
- `runtime/handoff_readiness.py` and `runtime/commit_readiness.py` remain
  bounded orchestration over evidence, git, and signal helpers.
- `cli/interactive_client.py` and `cli/changeset_command_handlers.py` remain
  compatibility surfaces over client and command-family helpers.
- `web/routes/changesets.py` and `web/changeset_api_builders.py` delegate to
  route-local action/service helpers and builder-family modules.
- `frontend/api/client.ts` and `frontend/stores/changeset-store-actions.ts`
  delegate to API endpoint-family and store action helper modules.
- `scripts/v14_release_gate_helpers.py` delegates deterministic stage
  construction, advisory evidence shaping, dry-run copy, evidence-dir
  resolution, and summary metadata to v14 release-gate helper families.

## Patterns That Must Not Become Permanent

The following patterns are not acceptable as stable endpoints:

- a new grab-bag helper module that simply becomes the next monolith
- broad runtime package re-exports that hide ownership of replay, context, query, and bootstrap code behind one import surface
- route modules that keep business logic inline after a shared query service exists
- CLI command handlers that continue to duplicate session-summary or next-action shaping once shared query paths land
- replay code that keeps a second copy of live model-loop behavior after the shared execution boundary exists
- background-job maintenance modules that mutate task/session state outside the
  explicit continuation path
- workspace-memory extraction helpers that create durable memory without the
  existing review/confirmation event path
- observability collectors that start repairing state, enqueueing jobs, or
  owning CLI/HTTP/frontend presentation
- repository-index helpers that depend on runtime session orchestration or
  non-local external data sources for refactor-only work
- frontend store modules that import React components or backend Python source
- React components that duplicate API/store transport behavior instead of
  consuming store state
- runtime query helpers that import web response models or frontend concepts
- provider scoring helpers that read hidden global diagnostics/evidence
- SQLite schema helpers that discover migrations dynamically or change ordered
  migration semantics during refactor-only movement
- core event/model splits that destabilize public import surfaces without a
  domain expansion and serialization coverage

## Task Mapping

This boundary note is the source of truth for the early refactor tasks in [refactor-v1.md](./refactor-v1.md) and the post-v8 boundary-refresh tasks in [refactor-v8.md](./refactor-v8.md).

The intended mapping is:

- `GBX-R101`: shared model-loop boundary for live turns and replay
- `GBX-R102`: shared session snapshot and query service in `src/glassbox/runtime/session_queries.py`
- `GBX-R103`: store-internal split under stable repository adapters via the `sqlite_*.py` internal modules behind `store/sqlite.py`
- `GBX-R104`: export-surface tightening and dependency-direction cleanup
- `GBX-R200`: post-v8 boundary map for autonomy-era runtime, store, TUI, and
  dashboard surfaces
- `GBX-R201`: guardrails for post-v8 dependency direction, facade thinness,
  and frontend store/component boundaries
- `GBX-R300`: v10 second-order boundary map for task autonomy, verification,
  compare analysis, workspace-console routing, web route helpers, runtime task
  queries, provider evidence/recommendations, tool policy, SQLite schema
  domains, and core event/model expansion
- `GBX-R301`: v10 guardrails for the second-order pressure points before bulk
  movement begins
- `GBX-R400`: v11 confidence-surface boundary map for recommendation output,
  knowledge posture, branch-search decision support, handoff/export, CLI
  guidance, frontend evidence sections, recovery helpers, and projection
  cleanup
- `GBX-R401`: planned v11 guardrails for the post-v11 pressure points before
  bulk movement begins
- `GBX-R500`: v13 review-loop boundary map for changeset runtime services,
  review feedback/evidence, lifecycle brief and readiness helpers, CLI/TUI/web
  transports, frontend changeset console/store, store projections, and release
  gate helper ownership
- `GBX-R502`: planned v13 post-extraction guardrails that keep the new
  compatibility facades thin and delegated after the first helper modules exist
- `GBX-R600`: post-v14 review-loop maturity boundary map for lifecycle
  limitations, review response/fixup status, skipped evidence, readiness
  signals, terminal clients, changeset transport, frontend API/store action
  surfaces, and v14 release-gate helper ownership
- `GBX-R602`: planned post-v14 post-extraction guardrails that keep the new
  compatibility facades thin and delegated after the first helper modules exist

Later tasks should follow this boundary map rather than redefining subsystem ownership case by case.

## How To Use This Note

Before starting a refactor task:

- confirm the target boundary exists in this note
- decide whether the task is boundary repair or a downstream file split
- preserve behavior first, then remove temporary shims once the new boundary is exercised and covered

If a later task reveals that one of these boundaries is wrong, update this note and the relevant roadmap task together rather than letting code and docs drift.
