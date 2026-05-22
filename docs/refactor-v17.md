# Glassbox Refactor v17 Tasks

For the docs hub and operator guides, start at [README.md](./README.md). This
file is the next behavior-preserving refactor roadmap after
[refactor-v16.md](./refactor-v16.md). It starts from the completed v17 local
handoff release-candidate milestone and targets the code paths that grew while
v17 added recipient intent, handoff readiness, package compatibility
inspection, redaction preview, local-only evidence inventory, import triage,
custody decisions, dashboard handoff cockpit surfaces, and v17 release-gate
coverage.

## Purpose

This document defines a post-v17 refactor roadmap for the current Glassbox
codebase.

It follows the execution style of [refactor-v1.md](./refactor-v1.md),
[refactor-v8.md](./refactor-v8.md), [refactor-v10.md](./refactor-v10.md),
[refactor-v11.md](./refactor-v11.md), [refactor-v13.md](./refactor-v13.md),
[refactor-v14.md](./refactor-v14.md), [refactor-v15.md](./refactor-v15.md),
and [refactor-v16.md](./refactor-v16.md): explicit dependencies, small
vertical slices, concrete deliverables, and validation requirements attached
directly to the work.

This roadmap is not a product-feature roadmap. It exists to keep the current
local-first, event-sourced architecture easy to evolve by:

- separating v17 handoff derivation from package I/O, redaction preview,
  import triage, custody decisions, CLI formatting, API payload shaping,
  dashboard rendering, and release-gate summary construction
- keeping recipient intent, package compatibility, redaction posture,
  local-only evidence, readiness reasons, custody state, import guidance, and
  non-claim language independently reviewable
- preserving current CLI, TUI, dashboard, API, replay, eval, package,
  projection, release-gate, and import/export behavior unless a later task
  explicitly changes a contract
- tightening architecture guardrails around the modules that grew after the
  v17 release-candidate milestone
- avoiding line-count-only splits in model-heavy, generated, fixture-heavy,
  evidence-heavy, or public compatibility surfaces

## Refactor Direction

The post-v16 refactor successfully split operator-flow surfaces before v17 made
local handoff first-class. The v17 milestone then added:

- shared handoff intent, recipient, source, package, readiness, redaction,
  local-only, compatibility, and custody models
- portable handoff package schema v2 and legacy session export compatibility
  inspection
- readiness services for sessions, tasks, changesets, workspace, and release
  contexts
- redaction preview and local-only inventory for session and changeset exports
- recipient-oriented export profiles and reviewer-safe Markdown summaries
- import triage, inspection-only import, custody acceptance, rejection,
  archive, and fork-or-continue guidance
- `glassbox handoff` CLI workflows plus compatibility routing through
  existing session and changeset commands
- typed handoff API routes, generated frontend API contracts, dashboard
  handoff cockpit, and TUI entry points
- deterministic v17 evals, package checks, installed-smoke checks, advisory
  evidence rows, dogfooding evidence, and a v17 release gate

The implementation is coherent, but v17 concentrated new behavior in a handful
of places. The next refactor should keep those contracts dependable before a
future milestone expands handoff into more source types, richer import
workflows, or external review integrations.

Current pressure points include:

- `src/glassbox/web/routes/handoffs.py`: route declarations, package-path
  resolution, preview/export orchestration, Markdown writing, package
  inspection, import triage, import mutation, readiness aggregation, custody
  decisions, guidance lookup, response shaping, and HTTP error translation live
  in one route module.
- `frontend/components/console/handoff-cockpit.tsx`: record list, custody
  actions, prepare form, package inspection, readiness panel, preview panel,
  package/triage/guidance panel, badge variants, form field helpers, command
  rendering, and non-claim rendering live in one component.
- `frontend/stores/handoff-store.ts`: list loading, selected record state,
  draft state, preview/export/inspect/triage/import/readiness/guidance actions,
  custody decisions, request tracking, and user-facing messages live in one
  store module.
- `src/glassbox/cli/handoff_commands.py`: command dispatch, compatibility
  delegation to session and changeset command handlers, package-family
  detection, JSON and human output, custody decision recording, guidance
  printing, and Markdown inspection live together.
- `src/glassbox/runtime/handoff_package.py`: package v2 construction, legacy
  export inspection, raw JSON validation, compatibility classification, digest
  validation, unsupported/future schema handling, and summary shaping live in
  one runtime module.
- `src/glassbox/runtime/handoff_redaction_preview.py`: session and changeset
  preview construction, local-only count derivation, omitted raw categories,
  safe commands, redaction marker scanning, and workspace/release preview
  helpers are adjacent.
- `src/glassbox/runtime/session_export_package.py` and
  `src/glassbox/runtime/changeset_export.py`: export payload assembly now
  includes v17 profile, local-only inventory, redaction, Markdown, and package
  compatibility concerns beside existing session and review-evidence export
  behavior.
- `src/glassbox/services/contracts.py`: the broad `SessionRepository` protocol
  remains useful as a public service contract, but v17 added more handoff,
  projection, and custody use cases that should rely on narrower repository
  protocols where possible.
- `scripts/validate_v17_release_gate.py` and `scripts/v17_release_gate_*`:
  v17 release-gate helpers are well split internally, but they still copy the
  previous milestone pattern. Future gates would benefit from a reusable
  milestone-gate configuration boundary.
- `docs/architecture.md`, `docs/refactor-boundaries.md`, and
  `tests/unit/architecture_guardrails/`: the current architecture and
  guardrail map records post-v16 ownership, but v17 handoff helper owners and
  compatibility facades are not yet captured there.

The post-v17 refactor thesis is:

- keep canonical events, managed artifacts, package manifests, typed API
  responses, local source files, and deterministic eval fixtures as the source
  of truth
- keep handoff readiness advisory unless a narrower existing readiness
  contract marks a state as blocking
- keep custody decisions as local workflow metadata, not authorization,
  approval, runtime ownership, reviewer signoff, release signoff, or
  publication
- keep package inspection and import triage separate from import mutation,
  fork, resume, verification, and follow-up work
- keep redaction, local-only evidence, stale evidence, missing evidence,
  skipped evidence, manual-only evidence, accepted risk, and compatibility
  warnings visible rather than hidden under optimistic copy
- keep runtime handoff services transport-agnostic and free of FastAPI,
  frontend, CLI, or store implementation imports
- keep web response models and frontend generated API types as transport
  contracts, not business-logic owners
- keep frontend stores responsible for transport and user-facing action state;
  components own presentation and local interaction state; pure helpers own
  formatting and derivation
- preserve compatibility facades where imports, commands, routes, generated
  API types, stores, component entrypoints, or release-gate commands rely on
  them
- add guardrails only when the intended repair is local, obvious, and backed by
  explicit owner modules

## Agent Execution Rules

These rules apply to every task in this file.

1. Respect dependency order. Do not start a task until its dependencies are
   complete unless the task explicitly says it can proceed in parallel.
2. Preserve current behavior by default. Refactor tasks should not
   intentionally change CLI semantics, TUI slash-command behavior, dashboard
   workflows, API payloads, replay outcomes, eval outcomes, event ordering,
   projection behavior, package contents, release-gate behavior, import/export
   behavior, custody semantics, redaction posture, or handoff non-claims unless
   the task explicitly includes that contract change.
3. Treat `events` as the canonical source of truth. Query services, route
   helpers, stores, frontend derivation, UI projections, package summaries,
   readiness rows, import triage, custody records, queue rows, and release
   summaries remain derived from canonical events, typed API responses, managed
   artifacts, package manifests, local source files, or rebuildable projection
   tables.
4. Repair architectural duplication before splitting files mechanically. If
   two modules shape the same compatibility state, safe inspection command,
   redaction limitation, local-only evidence bucket, custody action state,
   readiness reason, or handoff non-claim, extract the shared boundary first.
5. Prefer extractions with thin compatibility shims over broad rewrites. Keep
   diffs incremental and executable.
6. Keep public facades stable unless a task explicitly changes the import,
   route, API, command, store, component, generated type, or release-gate
   contract.
7. Do not introduce new framework layers unless they remove a real current
   coupling in the codebase.
8. Do not move API calls into React components. Frontend stores own transport;
   components own presentation and local interaction state; pure helper
   modules own derivation and formatting.
9. Do not move HTTP response models or FastAPI dependencies into runtime
   package, readiness, redaction, import, custody, guidance, or export
   services. Runtime services stay transport-agnostic.
10. Do not make handoff guidance stronger than its current advisory contract.
    It can recommend, explain, cite evidence, and preserve local decisions; it
    cannot claim reviewer approval, verification success, owner assignment,
    publication readiness, command approval, merge readiness, or release
    authority.
11. Do not add hosted collaboration, remote custody enforcement, remote
    review state, remote session sync, cloud evidence storage, remote workers,
    remote repository indexing, external vector-store authority, provider-side
    hidden memory, automatic staging, committing, pushing, pull request
    creation, merging, deployment, or publishing as part of refactor-only work.
12. Every refactor task automatically includes:
    - automated tests for moved or extracted behavior where practical
    - `ruff` formatting and lint compliance for touched Python code
    - `ty` typecheck compliance for touched Python code
    - focused `pytest` coverage for touched runtime, store, CLI, TUI, web,
      replay, eval, daemon, queue, evidence graph, verification, task,
      changeset, review, handoff, import/export, redaction, custody,
      repository intelligence, frontend API, and release-gate behavior
    - frontend lint, typecheck, tests, and build when the task touches
      dashboard code, generated API types, packaged static assets, route
      assumptions, frontend stores, handoff panels, queue panels, or
      import/export workflows
    - documentation updates when public module boundaries, architecture
      references, import surfaces, API payloads, command behavior, package
      contents, release posture, evidence posture, or operator-visible outputs
      change materially

## Completion Contract For Any Task

A task is complete only when all of the following are true:

- the implementation exists in the intended module boundary
- automated tests covering the touched behavior exist and pass
- lint, formatting, and type checks pass for the touched slice
- compatibility shims, if any, are justified explicitly or tracked by a
  follow-up task in this file
- docs are updated if the refactor changes documented architecture, import
  surfaces, API payloads, command behavior, package contents, release posture,
  or operator-visible outputs
- deterministic replay/eval behavior remains stable or intentional drift is
  handled through the established baseline-refresh workflow
- generated OpenAPI and frontend API types are refreshed when web contracts
  change
- dashboard static assets remain fresh when packaged dashboard behavior changes
- package validation and installed-wheel smoke remain aligned with moved
  release-gate, docs, eval, generated API, and dashboard assets
- handoff readiness claims remain backed by deterministic local inputs,
  canonical events, managed artifacts, typed API responses, projection rows,
  package manifests, or eval fixtures
- stale, missing, skipped, manual-only, accepted-risk, advisory, redacted,
  unsupported, future-version, local-only, and reviewer-safe states remain
  visible rather than hidden
- no meaningful handoff, custody, package, import triage, redaction,
  readiness, queue, or next-action state exists only in memory once a task
  claims durability
- reviewer-facing artifacts are redacted or explicitly documented as
  local-only
- repository intelligence remains advisory and freshness-aware
- memory-derived guidance remains confirmed, active, provenance-backed, and
  prompt-use-recorded before it shapes model context
- the refactor does not weaken the local-first, event-sourced, replay-aware
  architecture described in [architecture.md](./architecture.md)
- the refactor does not weaken the v17 local handoff contracts described in
  [v17-local-handoff-contract.md](./v17-local-handoff-contract.md),
  [local-handoff.md](./local-handoff.md),
  [team-workflows.md](./team-workflows.md), and
  [publication-boundary.md](./publication-boundary.md)

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
uv run python scripts/validate_v17_release_gate.py --dry-run
```

During incremental refactor work, use narrower commands when possible:

```bash
uv run pytest tests/unit/test_handoff_package.py
uv run pytest tests/unit/test_handoff_import_triage.py
uv run pytest tests/unit/test_handoff_decisions.py
uv run pytest tests/unit/test_handoff_guidance.py
uv run pytest tests/unit/test_handoff_redaction_preview.py
uv run pytest tests/unit/test_session_handoff_readiness.py
uv run pytest tests/unit/test_task_handoff_readiness.py
uv run pytest tests/unit/test_workspace_handoff_readiness.py
uv run pytest tests/integration/test_cli_handoff_commands.py
uv run pytest tests/integration/test_web_handoff_routes.py
uv run pytest tests/integration/test_handoff_projection.py
uv run pytest tests/unit/architecture_guardrails
pnpm --dir frontend test -- handoff-cockpit.test.tsx dashboard-stores.test.ts api-client.test.ts
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
uv run python scripts/validate_v17_release_gate.py --dry-run
```

## Milestone Map

The intended post-v17 refactor milestone order is:

1. v17 boundary refresh and characterization
2. handoff package, redaction, import, and custody runtime cleanup
3. handoff readiness and export-profile cleanup
4. web transport and API builder cleanup
5. CLI and TUI handoff cleanup
6. frontend handoff cockpit and store cleanup
7. repository, service-contract, and projection boundary cleanup
8. release-gate, eval, and package helper cleanup
9. guardrails, docs, and validation closeout

Each phase below corresponds to one concrete refactor milestone.

## Task Graph

---

## Phase 120: Post-V17 Boundary Refresh And Characterization

### GBX-R900: Define Post-V17 Refactor Boundary Map

- Status: `TODO`
- Dependencies: none
- Target files:
  - [architecture.md](./architecture.md)
  - [refactor-boundaries.md](./refactor-boundaries.md)
  - [refactor-v17.md](./refactor-v17.md)
  - `tests/unit/architecture_guardrails/`
- Work:
  - document the intended post-v17 compatibility facades and helper owners
  - name handoff package inspection, redaction preview, local-only inventory,
    import triage, custody decisions, readiness services, web route helpers,
    dashboard cockpit panels, handoff stores, repository protocols, and v17
    release-gate helpers as first pressure points
  - distinguish model-heavy public surfaces from mixed-responsibility modules
    that should be split
  - keep v17 handoff non-goals explicit: no hosted collaboration, no remote
    custody authority, no approval semantics, no hidden import mutation, and
    no publication automation
- Deliverables:
  - documented boundary map for runtime, core, services, store, web, CLI, TUI,
    frontend, release-gate, and guardrail surfaces
  - initial guardrail expectations for post-v17 pressure points where intended
    owner modules are already clear
- Validation:
  - `uv run pytest tests/unit/architecture_guardrails`
  - `uv run pytest tests/unit/test_release_candidate_docs.py -q`

### GBX-R901: Characterize Current Local Handoff Behavior

- Status: `TODO`
- Dependencies: GBX-R900
- Target files:
  - `tests/unit/test_handoff_package.py`
  - `tests/unit/test_handoff_import_triage.py`
  - `tests/unit/test_handoff_decisions.py`
  - `tests/unit/test_handoff_guidance.py`
  - `tests/unit/test_handoff_redaction_preview.py`
  - `tests/unit/test_session_handoff_readiness.py`
  - `tests/unit/test_task_handoff_readiness.py`
  - `tests/unit/test_workspace_handoff_readiness.py`
  - `tests/integration/test_cli_handoff_commands.py`
  - `tests/integration/test_web_handoff_routes.py`
  - `frontend/tests/handoff-cockpit.test.tsx`
- Work:
  - identify highest-risk current behavior before movement begins
  - add characterization coverage where moved behavior is not already asserted
  - prefer narrow tests around package compatibility states, digest failure,
    future schema inspection, redaction preview counts, local-only inventory,
    safe first commands, import disposition, inspection-only import, custody
    action states, guidance paths, dashboard disabled states, and non-claims
  - explicitly record accepted behavior gaps that should not block
    refactor-only movement
- Deliverables:
  - current behavior coverage sufficient for runtime, web, CLI, and frontend
    extraction tasks
  - accepted-gap list for behavior intentionally left unchanged during
    refactor-only work
- Validation:
  - `uv run pytest tests/unit/test_handoff_package.py`
  - `uv run pytest tests/unit/test_handoff_import_triage.py`
  - `uv run pytest tests/unit/test_handoff_decisions.py`
  - `uv run pytest tests/unit/test_handoff_redaction_preview.py`
  - `uv run pytest tests/integration/test_cli_handoff_commands.py`
  - `uv run pytest tests/integration/test_web_handoff_routes.py`
  - `pnpm --dir frontend test -- handoff-cockpit.test.tsx`

### GBX-R902: Add Post-V17 Guardrails After First Extraction

- Status: `TODO`
- Dependencies: GBX-R910, GBX-R930, GBX-R950
- Target files:
  - `tests/unit/architecture_guardrails/rules.py`
  - `tests/unit/architecture_guardrails/test_refactor_era_pressure_points.py`
  - `tests/unit/architecture_guardrails/test_python_facades.py`
  - `tests/unit/architecture_guardrails/test_frontend_boundaries.py`
  - [refactor-boundaries.md](./refactor-boundaries.md)
- Work:
  - add facade line-count and import-prefix expectations only after helper
    modules exist
  - assert that post-v17 runtime, service, web, CLI, frontend, and release-gate
    facades delegate to intended owner modules
  - keep guardrails narrow enough that they catch regression without freezing
    legitimate implementation detail
- Deliverables:
  - post-extraction architecture tests for the new v17 helper owners
- Validation:
  - `uv run pytest tests/unit/architecture_guardrails`

---

## Phase 121: Handoff Package, Redaction, Import, And Custody Runtime Cleanup

### GBX-R910: Split Handoff Package Inspection By Format Family

- Status: `TODO`
- Dependencies: GBX-R901
- Target files:
  - `src/glassbox/runtime/handoff_package.py`
  - `src/glassbox/runtime/handoff_package_models.py`
  - `src/glassbox/runtime/handoff_package_digest.py`
  - `src/glassbox/runtime/handoff_package_inspection.py`
  - `src/glassbox/runtime/handoff_package_legacy.py`
  - `tests/unit/test_handoff_package.py`
- Work:
  - keep `build_handoff_package_v2`, `inspect_handoff_package_path`, and
    `inspect_handoff_package` as public runtime entrypoints
  - move inspection result models and small package-local model aliases into a
    model helper if they are not core domain contracts
  - move digest construction and verification into one digest helper
  - move v2 package validation and supported-package inspection into an
    inspection helper
  - move legacy session export compatibility classification into a legacy
    helper
  - preserve all compatibility states, warning text, digest summaries,
    unsupported values, future-version handling, and secret-like package
    rejection behavior
- Deliverables:
  - package inspection facade that can delegate by package family and schema
    responsibility
- Validation:
  - `uv run pytest tests/unit/test_handoff_package.py`
  - `uv run ruff check src/glassbox/runtime/handoff_package*.py`
  - `uv run ty check src/glassbox/runtime/handoff_package.py`

### GBX-R911: Split Redaction Preview Builders By Source Family

- Status: `TODO`
- Dependencies: GBX-R901
- Target files:
  - `src/glassbox/runtime/handoff_redaction_preview.py`
  - `src/glassbox/runtime/handoff_redaction_preview_models.py`
  - `src/glassbox/runtime/handoff_redaction_preview_session.py`
  - `src/glassbox/runtime/handoff_redaction_preview_changeset.py`
  - `src/glassbox/runtime/handoff_redaction_preview_shared.py`
  - `tests/unit/test_handoff_redaction_preview.py`
- Work:
  - keep `build_session_redaction_preview` and
    `build_changeset_redaction_preview` as public entrypoints
  - move `HandoffRedactionPreview` into a model helper if it remains runtime
    local rather than core domain
  - move session preview construction into a session helper
  - move changeset preview construction into a changeset helper
  - move marker scanning, positive-count normalization, safe-command
    construction, and shared omitted-category shaping into shared helpers
  - preserve redacted field counts, category naming, local-only inventory
    behavior, safe commands, package limitations, and preview non-mutation
    semantics
- Deliverables:
  - redaction preview implementation split by handoff source family
- Validation:
  - `uv run pytest tests/unit/test_handoff_redaction_preview.py`
  - `uv run pytest tests/integration/test_cli_handoff_commands.py -k preview`

### GBX-R912: Split Import Triage And Imported Inspection Event Helpers

- Status: `TODO`
- Dependencies: GBX-R910
- Target files:
  - `src/glassbox/runtime/handoff_import_triage.py`
  - `src/glassbox/runtime/handoff_import_triage_models.py`
  - `src/glassbox/runtime/handoff_import_triage_disposition.py`
  - `src/glassbox/runtime/handoff_import_triage_events.py`
  - `tests/unit/test_handoff_import_triage.py`
  - `tests/integration/test_cli_session_import.py`
- Work:
  - keep `triage_handoff_import`,
    `build_imported_handoff_inspected_event`, and inspection mapping helpers
    available through the public facade
  - move triage response models and disposition literals into a model helper
  - move compatibility-to-disposition logic into a disposition helper
  - move imported package event construction and package/source/intent mapping
    into an event helper
  - preserve inspection-first posture, `mutation_performed=false`, safe first
    commands, local-only omission summaries, and legacy import compatibility
- Deliverables:
  - import triage can evolve independently from session import mutation
- Validation:
  - `uv run pytest tests/unit/test_handoff_import_triage.py`
  - `uv run pytest tests/integration/test_cli_session_import.py -k triage`
  - `uv run pytest tests/integration/test_web_handoff_routes.py -k import`

### GBX-R913: Split Custody Decisions, Action State, And Safe Actions

- Status: `TODO`
- Dependencies: GBX-R901
- Target files:
  - `src/glassbox/runtime/handoff_decisions.py`
  - `src/glassbox/runtime/handoff_decision_models.py`
  - `src/glassbox/runtime/handoff_decision_events.py`
  - `src/glassbox/runtime/handoff_decision_actions.py`
  - `tests/unit/test_handoff_decisions.py`
  - `tests/integration/test_handoff_projection.py`
- Work:
  - keep `accept_handoff_custody`, `reject_handoff_custody`,
    `archive_handoff`, `custody_action_state`, and
    `safe_next_actions_for_decision` as public entrypoints
  - move result models and repository protocols into a model helper
  - move event payload construction into an event helper
  - move action-state and safe-action derivation into an action helper
  - preserve imported versus local custody behavior, follow-up intent
    defaults, non-claims, projection refresh expectations, and archived-list
    filtering behavior
- Deliverables:
  - custody workflow logic independently reviewable from string/action helpers
- Validation:
  - `uv run pytest tests/unit/test_handoff_decisions.py`
  - `uv run pytest tests/integration/test_handoff_projection.py`
  - `uv run pytest tests/integration/test_web_handoff_routes.py -k accept`

### GBX-R914: Split Handoff Guidance Path Derivation

- Status: `TODO`
- Dependencies: GBX-R912, GBX-R913
- Target files:
  - `src/glassbox/runtime/handoff_guidance.py`
  - `src/glassbox/runtime/handoff_guidance_models.py`
  - `src/glassbox/runtime/handoff_guidance_paths.py`
  - `src/glassbox/runtime/handoff_guidance_blockers.py`
  - `tests/unit/test_handoff_guidance.py`
- Work:
  - keep `load_handoff_guidance` as the public entrypoint
  - move guidance models into a model helper if not already core contracts
  - move inspect-only, fork, new-session, verification-needed, rejection, and
    archive path derivation into a path helper
  - move blocker and limitation derivation into a blocker helper
  - preserve recommendation ranking, safe commands, local-only evidence
    warnings, imported-session historical posture, and non-claims
- Deliverables:
  - imported-handoff guidance can grow without coupling to custody decisions
    or route output
- Validation:
  - `uv run pytest tests/unit/test_handoff_guidance.py`
  - `uv run pytest tests/integration/test_cli_handoff_commands.py -k guidance`

---

## Phase 122: Handoff Readiness And Export-Profile Cleanup

### GBX-R920: Split Session And Task Handoff Readiness Signal Helpers

- Status: `TODO`
- Dependencies: GBX-R901
- Target files:
  - `src/glassbox/runtime/session_handoff_readiness.py`
  - `src/glassbox/runtime/task_handoff_readiness.py`
  - `src/glassbox/runtime/handoff_readiness_shared.py`
  - `src/glassbox/runtime/handoff_readiness_reasons.py`
  - `tests/unit/test_session_handoff_readiness.py`
  - `tests/unit/test_task_handoff_readiness.py`
- Work:
  - keep current session and task readiness public entrypoints stable
  - extract shared readiness reason, evidence reference, safe-command, and
    non-claim shaping when session and task services duplicate it
  - preserve distinctions between active, pending approval, pending answer,
    paused, failed, completed, imported, blocked, stale, and accepted-risk
    states
  - keep source-specific evidence derivation in source-specific helpers
- Deliverables:
  - session and task readiness remain source-specific while sharing common
    handoff vocabulary helpers
- Validation:
  - `uv run pytest tests/unit/test_session_handoff_readiness.py`
  - `uv run pytest tests/unit/test_task_handoff_readiness.py`

### GBX-R921: Split Workspace And Release Handoff Readiness Helpers

- Status: `TODO`
- Dependencies: GBX-R920
- Target files:
  - `src/glassbox/runtime/workspace_handoff_readiness.py`
  - `src/glassbox/runtime/workspace_handoff_readiness_workspace.py`
  - `src/glassbox/runtime/workspace_handoff_readiness_release.py`
  - `tests/unit/test_workspace_handoff_readiness.py`
  - `tests/integration/test_observability_status.py`
- Work:
  - keep `derive_workspace_handoff_readiness` and
    `derive_release_handoff_readiness` as public entrypoints
  - move workspace observability, daemon owner, repository intelligence,
    memory, background job, artifact, and maintenance cue summaries into a
    workspace helper
  - move release gate, eval, package, installed-smoke, advisory evidence,
    residual risk, and signoff posture into a release helper
  - preserve release non-claims and deterministic-versus-advisory evidence
    separation
- Deliverables:
  - workspace and release handoff posture independently reviewable
- Validation:
  - `uv run pytest tests/unit/test_workspace_handoff_readiness.py`
  - `uv run pytest tests/integration/test_observability_status.py -k handoff`
  - `uv run python scripts/validate_v17_release_gate.py --dry-run`

### GBX-R922: Split Session Export Profile And Local-Only Inventory Attachment

- Status: `TODO`
- Dependencies: GBX-R911
- Target files:
  - `src/glassbox/runtime/session_export_package.py`
  - `src/glassbox/runtime/session_export_profile.py`
  - `src/glassbox/runtime/handoff_export_profiles.py`
  - `src/glassbox/runtime/handoff_local_only_inventory.py`
  - `tests/integration/test_cli_session_export.py`
  - `tests/unit/test_handoff_redaction_preview.py`
- Work:
  - keep `build_session_export_payload` and `export_session_package` stable
  - ensure profile attachment, local-only inventory attachment, redaction
    summary, output-format validation, and package metadata are owned by
    focused helpers rather than session package assembly
  - preserve stable JSON payload shape and Markdown output compatibility
- Deliverables:
  - session export assembly stays focused on collecting session evidence while
    v17 package profile concerns live in handoff helpers
- Validation:
  - `uv run pytest tests/integration/test_cli_session_export.py -k handoff`
  - `uv run pytest tests/unit/test_handoff_redaction_preview.py -k session`

### GBX-R923: Split Changeset Export Profile And Reviewer-Safe Handoff Helpers

- Status: `TODO`
- Dependencies: GBX-R911
- Target files:
  - `src/glassbox/runtime/changeset_export.py`
  - `src/glassbox/runtime/changeset_export_handoff.py`
  - `src/glassbox/runtime/changeset_export_markdown.py`
  - `src/glassbox/runtime/handoff_local_only_inventory.py`
  - `tests/unit/test_review_briefs.py`
  - `tests/integration/test_cli_changeset_commands.py`
- Work:
  - keep changeset export public commands and package inspection stable
  - move handoff-specific profile metadata, local-only inventory, reviewer-safe
    Markdown, redaction report shaping, and safe inspection commands into
    focused helpers
  - preserve reviewer-safe bundle non-claims, evidence graph slice behavior,
    verification posture, manual evidence summaries, and local-only counts
- Deliverables:
  - changeset export remains review-evidence oriented while v17 handoff
    profile concerns are separately owned
- Validation:
  - `uv run pytest tests/integration/test_cli_changeset_commands.py -k export`
  - `uv run pytest tests/unit/test_review_briefs.py`

---

## Phase 123: Web Transport And API Builder Cleanup

### GBX-R930: Split Handoff Route Query And Action Helpers

- Status: `TODO`
- Dependencies: GBX-R910, GBX-R912, GBX-R913
- Target files:
  - `src/glassbox/web/routes/handoffs.py`
  - `src/glassbox/web/routes/handoff_route_queries.py`
  - `src/glassbox/web/routes/handoff_route_actions.py`
  - `src/glassbox/web/routes/handoff_route_paths.py`
  - `src/glassbox/web/routes/handoff_route_errors.py`
  - `tests/integration/test_web_handoff_routes.py`
- Work:
  - keep `web/routes/handoffs.py` as the FastAPI route declaration surface
  - move list/show/guidance/readiness query orchestration into query helpers
  - move preview/export/inspect/triage/import/custody mutation orchestration
    into action helpers
  - move local package path resolution and package-family detection into a
    route-local path helper
  - move `ValueError`/missing-record translation into route-local error
    helpers
  - preserve endpoint paths, status codes, response models, generated OpenAPI
    shape, and package-path behavior
- Deliverables:
  - handoff route declarations become readable and thin
- Validation:
  - `uv run pytest tests/integration/test_web_handoff_routes.py`
  - `uv run pytest tests/integration/test_openapi_schema.py`
  - `uv run ruff check src/glassbox/web/routes/handoff*.py`

### GBX-R931: Split Handoff API Response Builders

- Status: `TODO`
- Dependencies: GBX-R930
- Target files:
  - `src/glassbox/web/handoff_api.py`
  - `src/glassbox/web/handoff_api_models.py`
  - `src/glassbox/web/handoff_api_builders.py`
  - `tests/integration/test_web_handoff_routes.py`
  - `tests/integration/test_openapi_schema.py`
- Work:
  - keep `web/handoff_api.py` as the import-compatible API facade
  - move request/response models into a model module if needed
  - move record response, decision response, inspect response, export response,
    and readiness response construction into builder helpers
  - preserve OpenAPI names and generated frontend type compatibility unless a
    task explicitly changes the API contract
- Deliverables:
  - handoff API models and builders separated from route orchestration
- Validation:
  - `uv run pytest tests/integration/test_web_handoff_routes.py`
  - `uv run pytest tests/integration/test_openapi_schema.py`
  - `pnpm --dir frontend api:generate`
  - `pnpm --dir frontend typecheck`

### GBX-R932: Normalize Handoff Source-Kind Parsing Across Web And CLI

- Status: `TODO`
- Dependencies: GBX-R930, GBX-R940
- Target files:
  - `src/glassbox/runtime/handoff_source_resolution.py`
  - `src/glassbox/web/routes/handoff_route_actions.py`
  - `src/glassbox/web/routes/handoff_route_queries.py`
  - `src/glassbox/cli/handoff_commands.py`
  - `tests/unit/test_handoff_models.py`
  - `tests/integration/test_cli_handoff_commands.py`
  - `tests/integration/test_web_handoff_routes.py`
- Work:
  - introduce one transport-agnostic helper for parsing supported handoff
    source kind and source ID requirements
  - keep HTTP error translation in web helpers and CLI error text in CLI
    helpers
  - preserve current supported source kinds and unsupported-source behavior
  - avoid moving FastAPI, argparse, or command formatting into runtime helpers
- Deliverables:
  - shared handoff source parsing semantics without transport coupling
- Validation:
  - `uv run pytest tests/unit/test_handoff_models.py`
  - `uv run pytest tests/integration/test_cli_handoff_commands.py -k source`
  - `uv run pytest tests/integration/test_web_handoff_routes.py -k readiness`

---

## Phase 124: CLI And TUI Handoff Cleanup

### GBX-R940: Split Handoff CLI Command Families

- Status: `TODO`
- Dependencies: GBX-R901
- Target files:
  - `src/glassbox/cli/handoff_commands.py`
  - `src/glassbox/cli/handoff_command_prepare.py`
  - `src/glassbox/cli/handoff_command_inspect.py`
  - `src/glassbox/cli/handoff_command_decisions.py`
  - `src/glassbox/cli/handoff_command_formatters.py`
  - `tests/integration/test_cli_handoff_commands.py`
- Work:
  - keep `_handoff_command` as the dispatch facade
  - move prepare/export compatibility delegation into a prepare helper
  - move package inspection, triage, Markdown rendering, and package-family
    detection into an inspect helper
  - move list/show/guidance/accept/reject/archive into command-family helpers
  - move human output and JSON payload shaping into formatter helpers
  - preserve command help, exit codes, JSON shapes, human copy, and
    compatibility with `session import` and `changeset export`
- Deliverables:
  - handoff CLI command surface split by workflow family
- Validation:
  - `uv run pytest tests/integration/test_cli_handoff_commands.py`
  - `uv run pytest tests/unit/test_command_guide.py -k handoff`
  - `uv run glassbox handoff --help`

### GBX-R941: Split Parser Handoff Helpers By Command Family

- Status: `TODO`
- Dependencies: GBX-R940
- Target files:
  - `src/glassbox/cli/parser_handoff.py`
  - `src/glassbox/cli/parser_handoff_prepare.py`
  - `src/glassbox/cli/parser_handoff_decisions.py`
  - `tests/integration/test_cli_entrypoint.py`
  - `tests/unit/test_command_guide.py`
- Work:
  - keep `_add_handoff_parsers` and `add_handoff_profile_arguments` as public
    parser entrypoints
  - move prepare/import/inspect parser construction into prepare and package
    helpers
  - move list/show/guidance/accept/reject/archive parser construction into a
    decision helper
  - preserve command tree, help text, choices, defaults, and runtime location
    arguments
- Deliverables:
  - parser helper split that mirrors CLI command families
- Validation:
  - `uv run pytest tests/integration/test_cli_entrypoint.py -k handoff`
  - `uv run pytest tests/unit/test_command_guide.py`
  - `uv run glassbox command tree`

### GBX-R942: Split TUI Handoff Entry Points And Guidance Rendering

- Status: `TODO`
- Dependencies: GBX-R940
- Target files:
  - `src/glassbox/cli/tui/handoff_commands.py`
  - `src/glassbox/cli/tui/commands.py`
  - `src/glassbox/cli/tui/widget_details.py`
  - `src/glassbox/cli/tui/widget_formatting.py`
  - `tests/unit/test_cli_tui_commands.py`
  - `tests/unit/test_cli_tui_workflows.py`
- Work:
  - keep current TUI slash-command behavior stable
  - move handoff command parsing, action routing, guidance formatting, and
    custody result rendering into TUI-owned helpers when they are currently
    adjacent to unrelated commands or widgets
  - keep TUI consuming CLI/runtime surfaces rather than raw store helpers or
    web routes
  - preserve non-claims and safe-inspection-first language
- Deliverables:
  - TUI handoff entry points can grow without broad widget or command-module
    pressure
- Validation:
  - `uv run pytest tests/unit/test_cli_tui_commands.py -k handoff`
  - `uv run pytest tests/unit/test_cli_tui_workflows.py -k handoff`
  - `uv run pytest tests/integration/test_cli_tui_review_commands.py`

---

## Phase 125: Frontend Handoff Cockpit And Store Cleanup

### GBX-R950: Split Dashboard Handoff Cockpit Panels

- Status: `TODO`
- Dependencies: GBX-R901
- Target files:
  - `frontend/components/console/handoff-cockpit.tsx`
  - `frontend/components/console/handoff/records-panel.tsx`
  - `frontend/components/console/handoff/custody-actions.tsx`
  - `frontend/components/console/handoff/prepare-panel.tsx`
  - `frontend/components/console/handoff/package-panel.tsx`
  - `frontend/components/console/handoff/readiness-panel.tsx`
  - `frontend/components/console/handoff/preview-panel.tsx`
  - `frontend/tests/handoff-cockpit.test.tsx`
- Work:
  - keep `HandoffCockpit` as the component entrypoint
  - move record list and selected-record summary into a records panel
  - move actor/reason/follow-up intent and accept/reject/archive controls into
    a custody action panel
  - move source kind, source ID, recipient, custodian, output path, and export
    actions into a prepare panel
  - move package path, inspect, triage, import, triage result, changeset
    summary, import result, and guidance rendering into package helpers
  - move readiness and preview sections into focused panel components
  - preserve visual hierarchy, responsive layout, button disabled states,
    current copy, and route behavior
- Deliverables:
  - dashboard handoff cockpit split into panel components by workflow family
- Validation:
  - `pnpm --dir frontend test -- handoff-cockpit.test.tsx`
  - `pnpm --dir frontend typecheck`
  - `pnpm --dir frontend lint`

### GBX-R951: Extract Handoff Cockpit Formatting And Option Helpers

- Status: `TODO`
- Dependencies: GBX-R950
- Target files:
  - `frontend/components/console/handoff-cockpit.tsx`
  - `frontend/components/console/handoff/format.ts`
  - `frontend/components/console/handoff/options.ts`
  - `frontend/components/console/handoff/command-list.tsx`
  - `frontend/components/console/handoff/non-claims.tsx`
  - `frontend/tests/handoff-cockpit.test.tsx`
- Work:
  - move intent and source-kind option lists into an options helper
  - move custody, readiness, redaction, and compatibility badge variants into
    a formatting helper
  - move command-list and non-claim rendering into small shared components
  - preserve labels, variants, truncation limits, and screen text
- Deliverables:
  - handoff cockpit presentation helpers independently testable and reusable
- Validation:
  - `pnpm --dir frontend test -- handoff-cockpit.test.tsx`
  - `pnpm --dir frontend typecheck`

### GBX-R952: Split Handoff Store Actions By Workflow Family

- Status: `TODO`
- Dependencies: GBX-R950
- Target files:
  - `frontend/stores/handoff-store.ts`
  - `frontend/stores/handoff-store-loaders.ts`
  - `frontend/stores/handoff-store-package-actions.ts`
  - `frontend/stores/handoff-store-decision-actions.ts`
  - `frontend/stores/handoff-store-drafts.ts`
  - `frontend/stores/handoff-store-selectors.ts`
  - `frontend/tests/dashboard-stores.test.ts`
  - `frontend/tests/handoff-cockpit.test.tsx`
- Work:
  - keep `createHandoffStore` as the public store factory
  - move list loading, selected-record loading, readiness loading, and
    guidance loading into loader helpers
  - move preview/export/inspect/triage/import into package action helpers
  - move accept/reject/archive into decision action helpers
  - move default draft state, draft setters, optional text, source ID, package
    path validation, and selected-record selectors into pure helpers
  - preserve request tracking, user-facing action status, stale request
    behavior, and post-mutation reload behavior
- Deliverables:
  - handoff store split into transport/action families without moving API calls
    into components
- Validation:
  - `pnpm --dir frontend test -- dashboard-stores.test.ts handoff-cockpit.test.tsx`
  - `pnpm --dir frontend typecheck`
  - `pnpm --dir frontend lint`

### GBX-R953: Add Frontend Handoff Boundary Guardrails

- Status: `TODO`
- Dependencies: GBX-R950, GBX-R952
- Target files:
  - `tests/unit/architecture_guardrails/rules.py`
  - `tests/unit/architecture_guardrails/test_frontend_boundaries.py`
  - `frontend/components/console/handoff/`
  - `frontend/stores/handoff-store*.ts`
- Work:
  - add frontend guardrails after the handoff component and store helpers exist
  - assert that handoff store helpers do not import React components, Next
    server modules, or backend source
  - assert that handoff components do not perform direct API calls
  - avoid freezing exact component names beyond the accepted entrypoint and
    helper family
- Deliverables:
  - frontend architecture tests protect the handoff cockpit split
- Validation:
  - `uv run pytest tests/unit/architecture_guardrails/test_frontend_boundaries.py`
  - `pnpm --dir frontend lint`

---

## Phase 126: Repository, Service-Contract, And Projection Boundary Cleanup

### GBX-R960: Define Narrow Handoff Repository Protocols

- Status: `TODO`
- Dependencies: GBX-R913
- Target files:
  - `src/glassbox/services/contracts.py`
  - `src/glassbox/runtime/handoff_repository_contracts.py`
  - `src/glassbox/runtime/handoff_decisions.py`
  - `src/glassbox/runtime/handoff_guidance.py`
  - `src/glassbox/runtime/session_import.py`
  - `tests/unit/test_service_contracts.py`
  - `tests/unit/test_repository_adapter_boundaries.py`
- Work:
  - introduce narrow protocols for handoff record reads, handoff event appends,
    handoff custody decisions, and import inspection as needed by runtime
    services
  - avoid requiring runtime helpers to depend on the full `SessionRepository`
    protocol when they only need handoff-specific behavior
  - preserve `SessionRepository` as a broad compatibility service contract
    while reducing new call sites that require it
- Deliverables:
  - handoff runtime helpers can be tested against small protocols
- Validation:
  - `uv run pytest tests/unit/test_service_contracts.py`
  - `uv run pytest tests/unit/test_repository_adapter_boundaries.py`
  - `uv run pytest tests/unit/test_handoff_decisions.py`

### GBX-R961: Split Handoff Projection Query And Mutation Adapters

- Status: `TODO`
- Dependencies: GBX-R960
- Target files:
  - `src/glassbox/store/repository_handoff.py`
  - `src/glassbox/store/repository_review_loop.py`
  - `src/glassbox/store/sqlite_query_handoff.py`
  - `src/glassbox/store/sqlite_projection_handoff.py`
  - `tests/integration/test_handoff_projection.py`
  - `tests/integration/test_projection_rebuild.py`
- Work:
  - confirm handoff projection event handling, read queries, list filtering,
    archived filtering, latest-state overwrite behavior, and rebuild behavior
    have one clear owner each
  - split query shaping from projection mutation if they are currently adjacent
    in a way that obscures rebuild semantics
  - preserve schema shape and projection rebuild output
- Deliverables:
  - handoff projection ownership documented and guarded without schema change
- Validation:
  - `uv run pytest tests/integration/test_handoff_projection.py`
  - `uv run pytest tests/integration/test_projection_rebuild.py -k handoff`
  - `uv run pytest tests/unit/test_sqlite_query_boundaries.py`

### GBX-R962: Guard Service And Store Import Direction For Handoff Helpers

- Status: `TODO`
- Dependencies: GBX-R960, GBX-R961
- Target files:
  - `tests/unit/architecture_guardrails/rules.py`
  - `tests/unit/architecture_guardrails/test_backend_import_direction.py`
  - `src/glassbox/runtime/handoff_*.py`
  - `src/glassbox/store/repository_handoff.py`
- Work:
  - add import-direction guardrails only after narrow protocols and helper
    owners are settled
  - assert runtime handoff helpers do not import concrete SQLite modules, web
    routes, frontend code, or CLI/TUI presentation modules
  - assert store handoff modules do not import runtime, web, or CLI packages
- Deliverables:
  - backend architecture tests protect handoff runtime/store direction
- Validation:
  - `uv run pytest tests/unit/architecture_guardrails/test_backend_import_direction.py`

---

## Phase 127: Release-Gate, Eval, And Package Helper Cleanup

### GBX-R970: Extract Reusable Milestone Release-Gate Runner Helpers

- Status: `TODO`
- Dependencies: GBX-R901
- Target files:
  - `scripts/validate_v16_release_gate.py`
  - `scripts/validate_v17_release_gate.py`
  - `scripts/release_gate_runner.py`
  - `scripts/release_gate_models.py`
  - `tests/unit/test_v16_release_gate.py`
  - `tests/unit/test_v17_release_gate.py`
- Work:
  - extract shared dry-run, stage execution, evidence summary lifecycle,
    provider evidence recording, installed-wheel resolution, and summary
    printing behavior that v16 and v17 currently repeat
  - keep milestone-specific stage construction, artifacts, labels, and
    advisory evidence rows in milestone helper modules
  - preserve command-line options, dry-run output, summary JSON shape, failure
    behavior, and installed-wheel smoke behavior
- Deliverables:
  - future release gates can reuse a runner without copy-forward entrypoint
    scripts
- Validation:
  - `uv run pytest tests/unit/test_v16_release_gate.py`
  - `uv run pytest tests/unit/test_v17_release_gate.py`
  - `uv run python scripts/validate_v17_release_gate.py --dry-run`

### GBX-R971: Split V17 Release-Gate Stages By Handoff Evidence Family

- Status: `TODO`
- Dependencies: GBX-R970
- Target files:
  - `scripts/v17_release_gate_stages.py`
  - `scripts/v17_release_gate_stage_groups.py`
  - `scripts/v17_release_gate_advisory.py`
  - `tests/unit/test_v17_release_gate.py`
  - `docs/v17-release-gate.md`
- Work:
  - keep `build_gate_stages` as the milestone helper entrypoint
  - group inherited v16 stages, handoff eval stages, CLI/API stages,
    frontend stages, package stages, docs stages, and installed-smoke stages
    into readable helper groups
  - preserve stage labels, blocking/advisory split, dry-run plan, and summary
    artifacts
- Deliverables:
  - v17 gate stage assembly can be reviewed by evidence family
- Validation:
  - `uv run pytest tests/unit/test_v17_release_gate.py`
  - `uv run python scripts/validate_v17_release_gate.py --dry-run`
  - `uv run pytest tests/unit/test_release_candidate_docs.py -q`

### GBX-R972: Refresh Package Contents And Installed-Smoke Guardrails For V17

- Status: `TODO`
- Dependencies: GBX-R970
- Target files:
  - `scripts/validate_package_contents.py`
  - `scripts/validate_installed_wheel_smoke.py`
  - `scripts/validate_frontend_release_assets.py`
  - `tests/unit/test_packaging_metadata.py`
  - `docs/release-packaging.md`
- Work:
  - verify v17 docs, eval fixtures, release-gate helper modules, generated API
    files, handoff runtime modules, web route helpers, frontend handoff
    components, and static dashboard assets remain packaged after helper
    splits
  - keep package validation deterministic and local
  - update docs only if package evidence ownership changes materially
- Deliverables:
  - package and installed-smoke checks aligned with the post-v17 helper split
- Validation:
  - `uv run pytest tests/unit/test_packaging_metadata.py`
  - `uv run python scripts/validate_package_contents.py`
  - `uv run python scripts/validate_frontend_release_assets.py`

### GBX-R973: Keep V17 Eval Fixtures Stable Through Refactor Movement

- Status: `TODO`
- Dependencies: GBX-R901
- Target files:
  - `evals/cases/local-handoff.*.json`
  - `evals/bundles/local-handoff.*.json`
  - `evals/README.md`
  - `tests/unit/test_runtime_evals.py`
  - `tests/integration/test_cli_eval_commands.py`
- Work:
  - verify refactor-only movement does not alter deterministic local-handoff
    eval results
  - avoid refreshing baselines unless a task explicitly changes behavior and
    follows the established eval refresh workflow
  - keep advisory dashboard, accessibility, provider, dogfooding, and manual
    release evidence separate from deterministic eval authority
- Deliverables:
  - v17 eval fixtures remain stable across helper extraction
- Validation:
  - `uv run glassbox eval audit --profile release-candidate --cwd .`
  - `uv run glassbox eval run --profile release-candidate --cwd .`
  - `uv run pytest tests/integration/test_cli_eval_commands.py -k handoff`

---

## Phase 128: Guardrails, Docs, And Validation Closeout

### GBX-R980: Refresh Architecture And Boundary Documentation

- Status: `TODO`
- Dependencies: GBX-R902, GBX-R930, GBX-R950, GBX-R960, GBX-R970
- Target files:
  - [architecture.md](./architecture.md)
  - [refactor-boundaries.md](./refactor-boundaries.md)
  - [README.md](./README.md)
  - [README.md](../README.md)
  - [refactor-v17.md](./refactor-v17.md)
- Work:
  - update architecture and boundary docs with completed post-v17 helper
    owners
  - update docs hub links if public refactor guidance changes
  - record accepted compatibility shims and product follow-up candidates
  - keep docs aligned with actual command help, module names, API routes, and
    package behavior
- Deliverables:
  - source-linked post-v17 refactor closeout notes
- Validation:
  - `uv run pytest tests/unit/test_release_candidate_docs.py -q`
  - `uv run pytest tests/unit/architecture_guardrails`

### GBX-R981: Run Post-V17 Refactor Confidence Sweep

- Status: `TODO`
- Dependencies: GBX-R980
- Target files:
  - tests, docs, scripts, frontend as needed
- Work:
  - run focused local-handoff and refactor-sensitive validation
  - record any accepted validation gaps in this file before marking the
    roadmap complete
  - do not refresh deterministic eval baselines unless a task explicitly
    changed behavior and follows the established eval refresh workflow
- Deliverables:
  - validation summary sufficient for post-v17 refactor closeout
  - updated task statuses when the roadmap is complete
- Validation summary:
  - not yet run
- Validation:
  - `uv run ruff format --check .`
  - `uv run ruff check .`
  - `uv run ty check`
  - `uv run pytest -n auto --dist loadfile`
  - `pnpm --dir frontend lint`
  - `pnpm --dir frontend typecheck`
  - `pnpm --dir frontend test`
  - `pnpm --dir frontend build`
  - `uv run python scripts/validate_v17_release_gate.py --dry-run`

## Accepted Behavior Gaps To Characterize During GBX-R901

These are current behavior observations that should be confirmed before moving
code. They are not product changes by themselves, and later tasks may
deliberately narrow them when the task text explicitly says so:

- the handoff API can export session and changeset packages, while workspace,
  release, and task source kinds are readiness-oriented unless a future product
  task defines portable package payloads for those source kinds
- changeset package inspection still uses the legacy changeset export summary
  path rather than a full v17 package v2 import triage path
- `handoff import` delegates to session import and remains inspection-only;
  changeset package import is not a mutation path
- local package paths are resolved relative to the workspace root for web
  routes and CLI runtime location for terminal commands; path safety posture
  should be characterized before any normalization
- custody acceptance and rejection can both be recorded on the same local
  handoff record today if the operator explicitly does so; projection ordering
  and action-state behavior should be characterized before changing it
- the dashboard handoff cockpit is workflow-dense but intentionally presents
  all v17 cockpit actions on one surface; splitting components should not
  introduce route or state fragmentation

## Accepted Product Follow-Up Candidates

These findings are useful context for refactor planning, but they are not
refactor-only tasks unless a later roadmap explicitly chooses to change
behavior:

- define task, workspace, release, or future-self portable package payloads
  beyond readiness summaries and existing session/changeset package paths
- decide whether changeset export packages should migrate fully to
  `glassbox_handoff_package` v2 or remain a reviewer-safe changeset package
  family with v17 inspection support
- decide whether custody records should prevent contradictory later custody
  decisions or keep the current append-only workflow history
- decide whether imported handoff guidance should directly create a fork,
  task, verification plan, or follow-up queue item after explicit operator
  confirmation
- decide whether dashboard handoff cockpit should gain multi-step wizards,
  drag-and-drop package selection, or richer package diffing
- decide whether local-only evidence inventory should link to evidence graph
  claim IDs for every omitted raw artifact category
- decide whether package digest validation should include external sidecar
  manifests or signed attestations without changing local-first authority
- decide whether release-gate helper reuse should span older v11-v15 gates or
  only future milestone gates

Product follow-ups should preserve the v17 non-goals unless a future product
contract explicitly changes them.

## Accepted Compatibility Shims

The following facades are acceptable during this roadmap as long as they remain
thin and delegate to owned helpers after the relevant phase completes:

- `src/glassbox/runtime/handoff_package.py`: handoff package public facade over
  digest, v2 inspection, legacy inspection, compatibility classification, and
  model helpers.
- `src/glassbox/runtime/handoff_redaction_preview.py`: redaction preview
  public facade over session, changeset, shared marker scanning, and
  safe-command helpers.
- `src/glassbox/runtime/handoff_import_triage.py`: import triage public facade
  over models, disposition derivation, safe commands, and imported inspection
  event helpers.
- `src/glassbox/runtime/handoff_decisions.py`: custody decision public facade
  over models, event construction, action state, and safe-action helpers.
- `src/glassbox/runtime/handoff_guidance.py`: imported-handoff guidance public
  facade over models, path derivation, blocker derivation, and safe-command
  helpers.
- `src/glassbox/runtime/session_handoff_readiness.py`,
  `src/glassbox/runtime/task_handoff_readiness.py`,
  `src/glassbox/runtime/handoff_readiness.py`, and
  `src/glassbox/runtime/workspace_handoff_readiness.py`: readiness entrypoints
  over source-specific and shared handoff reason helpers.
- `src/glassbox/runtime/session_export_package.py` and
  `src/glassbox/runtime/changeset_export.py`: export entrypoints that may
  delegate v17 profile, local-only inventory, redaction, and Markdown behavior
  to handoff-owned helpers.
- `src/glassbox/services/contracts.py`: broad public service contract that may
  coexist with narrower handoff repository protocols while compatibility
  matters.
- `src/glassbox/store/repositories.py`: concrete repository facade over
  domain-specific repository adapter mixins, including handoff projection
  adapters.
- `src/glassbox/web/routes/handoffs.py`: FastAPI route declaration surface over
  route-local query, action, path, and error helpers.
- `src/glassbox/web/handoff_api.py`: handoff API compatibility facade over
  response/request models and builder helpers.
- `src/glassbox/cli/handoff_commands.py`: CLI dispatch facade over prepare,
  inspect, decision, guidance, and formatter helpers.
- `src/glassbox/cli/parser_handoff.py`: CLI parser facade over handoff parser
  families.
- `src/glassbox/cli/tui/handoff_commands.py`: TUI handoff entrypoint over
  TUI-owned action and rendering helpers.
- `frontend/components/console/handoff-cockpit.tsx`: dashboard handoff
  cockpit entrypoint over panel, formatting, command, and non-claim helpers.
- `frontend/stores/handoff-store.ts`: dashboard handoff store facade over
  loader, package action, decision action, draft, and selector helpers.
- `scripts/validate_v17_release_gate.py`: operator release-gate entrypoint
  over reusable runner helpers plus v17-specific stage, advisory, summary,
  package, and installed-smoke helpers.
- `tests/unit/test_architecture_guardrails.py`: legacy validation entrypoint
  that imports the split architecture guardrail modules by boundary family.
