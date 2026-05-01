# Glassbox Refactor Boundaries

For the docs hub and operator guides, start at [README.md](./README.md). This note defines the target architectural boundaries for the v1 refactor roadmap in [refactor-v1.md](./refactor-v1.md), the post-v8 follow-on roadmap in [refactor-v8.md](./refactor-v8.md), the second-order v10 roadmap in [refactor-v10.md](./refactor-v10.md), and the post-v11 confidence-surface roadmap in [refactor-v11.md](./refactor-v11.md).

## Purpose

This document is the architecture source of truth for the refactor roadmap.

It exists to answer one question before code moves begin:

What are the intended module boundaries for the current Glassbox implementation, and what kinds of changes are explicitly out of scope for the first refactor pass?

This note is intentionally code-aligned. It describes the current implementation shape and the target decomposition boundaries for refactor work already captured in [refactor-v1.md](./refactor-v1.md), [refactor-v8.md](./refactor-v8.md), [refactor-v10.md](./refactor-v10.md), and [refactor-v11.md](./refactor-v11.md). It does not define a new product architecture.

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

Large files that are primarily model-heavy and should not be split just for
line count include core event/model/type modules, generated frontend API types,
generated OpenAPI JSON, fixture bundles, release evidence artifacts, and facade
modules whose public contract is intentionally broad but already delegates
behavior to owned implementation modules. Large files that are mixed
coordinators should be split along ownership boundaries when their roadmap task
arrives, not by mechanical line slicing.

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

If a guardrail fails, the default repair should be to move new behavior into the owning split module or add one focused neighbor module, not to widen a facade or cross a subsystem boundary.

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

Later tasks should follow this boundary map rather than redefining subsystem ownership case by case.

## How To Use This Note

Before starting a refactor task:

- confirm the target boundary exists in this note
- decide whether the task is boundary repair or a downstream file split
- preserve behavior first, then remove temporary shims once the new boundary is exercised and covered

If a later task reveals that one of these boundaries is wrong, update this note and the relevant roadmap task together rather than letting code and docs drift.
