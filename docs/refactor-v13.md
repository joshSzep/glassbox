# Glassbox Refactor v13 Tasks

For the docs hub and operator guides, start at [README.md](./README.md). This
file is the next behavior-preserving refactor roadmap after
[refactor-v11.md](./refactor-v11.md). It focuses on the code paths that grew
while the v13 review-loop milestone added local review feedback, fixup
responses, manual evidence, browser and accessibility evidence, lifecycle
briefs, handoff readiness, publication-boundary guidance, and integrated
in-session review UX.

## Purpose

This document defines a post-v13 refactor roadmap for the current Glassbox
codebase.

It follows the same execution style as [refactor-v1.md](./refactor-v1.md),
[refactor-v8.md](./refactor-v8.md), [refactor-v10.md](./refactor-v10.md), and
[refactor-v11.md](./refactor-v11.md): explicit dependencies, small vertical
slices, concrete deliverables, and validation requirements attached directly to
the work.

This roadmap is not a product-feature roadmap. It exists to keep the current
local-first, event-sourced architecture easy to evolve by:

- separating v13 changeset and review-loop orchestration from artifact
  derivation, readiness shaping, evidence attachment, and presentation
- keeping local review feedback, manual evidence, browser evidence,
  accessibility evidence, lifecycle briefs, verification posture, handoff
  readiness, and publication-boundary behavior independently reviewable
- preserving current CLI, TUI, dashboard, API, replay, eval, package,
  projection, and release-gate behavior unless a later task explicitly changes
  a contract
- tightening architecture guardrails around the modules that grew after the
  v13 release-candidate milestone
- avoiding line-count-only splits in model-heavy, event-heavy, generated, or
  public compatibility surfaces

## Refactor Direction

The v11 refactor successfully split confidence-surface modules before the v12
and v13 milestones expanded the local changeset and review-loop model. The v12
implementation made local changes reviewable. The v13 implementation made those
changes survive local review by recording feedback, responses, manual evidence,
advisory live evidence, lifecycle briefs, and handoff posture.

The new pressure is concentrated in modules that are coherent but broad:

- `runtime/changesets.py` now owns changeset derivation, query views, feedback
  actions, manual evidence actions, browser and accessibility evidence actions,
  fixup inventory capture, verification preview, lifecycle brief assembly,
  workspace diff helpers, command evidence shaping, review readiness, safe
  commands, and several artifact payloads
- `cli/changeset_commands.py` now owns command dispatch, service wiring,
  lower-level review-loop actions, JSON payload shaping, and terminal
  formatting for changesets, feedback, evidence, verification, briefs, commit
  preparation, and handoff readiness
- `web/changeset_api.py` now owns a large set of transport models and response
  builders for changesets, feedback, manual evidence, verification, commit
  readiness, handoff readiness, and review response summaries
- `web/routes/changesets.py` now owns route declarations plus repeated service
  construction, request branching, workspace-root lookup, and HTTP error
  translation for the full review-loop surface
- `frontend/components/console/changeset-console.tsx` now renders the densest
  v13 dashboard surface and combines list, detail, feedback, evidence,
  verification, handoff, commit-prep, and local form state
- store projection and query helpers for changesets and review-loop evidence
  remain rebuildable and event-derived, but each new evidence family adds
  review pressure to the projection boundary
- v13 release-gate scripts inherit earlier gate composition while adding
  review-loop evals, command coverage, coverage audits, installed smoke, and
  advisory provider/browser/accessibility evidence rows
- architecture guardrails still describe v11 boundaries well, but they do not
  yet name the intended post-v13 review-loop helper owners

The v13 refactor thesis is:

- keep canonical events and managed artifacts as the source of truth
- keep projection tables rebuildable and non-authoritative
- keep runtime query services transport-agnostic
- keep web response models and frontend generated API types as transport
  contracts, not business-logic owners
- keep frontend stores responsible for transport and components responsible for
  presentation and local interaction state
- move derivation, redaction, evidence shaping, readiness scoring, safe-command
  guidance, and terminal/dashboard formatting into focused modules before
  adding more review-loop behavior
- preserve compatibility facades where imports, routes, commands, or component
  entrypoints rely on them
- add guardrails only when the intended repair is obvious, local, and backed by
  an explicit owner module

## Agent Execution Rules

These rules apply to every task in this file.

1. Respect dependency order. Do not start a task until its dependencies are
   complete unless the task explicitly says it can proceed in parallel.
2. Preserve current behavior by default. Refactor tasks should not intentionally
   change CLI semantics, TUI slash-command behavior, dashboard workflows, API
   payloads, replay outcomes, eval outcomes, event ordering, projection
   behavior, package contents, release-gate behavior, or publication-boundary
   claims unless the task explicitly includes that contract change.
3. Treat `events` as the canonical source of truth. Query services, route
   helpers, stores, frontend derivation, and UI projections remain derived from
   canonical events, typed API responses, managed artifacts, or rebuildable
   projection tables.
4. Repair architectural duplication before splitting files mechanically. If two
   modules shape the same evidence, safe command, readiness reason, limitation,
   or non-claim, extract the shared boundary first.
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
10. Do not make manual, browser, dashboard, accessibility, provider, or
    dogfooding evidence stronger than its current advisory contract.
11. Do not add automatic staging, committing, pushing, pull request creation,
    merging, deployment, or publishing as part of refactor-only work.
12. Every refactor task automatically includes:
    - automated tests for moved or extracted behavior where practical
    - `ruff` formatting and lint compliance for touched Python code
    - `ty` typecheck compliance for touched Python code
    - focused `pytest` coverage for touched runtime, store, CLI, TUI, web,
      replay, eval, daemon, policy, task, branch-search, changeset,
      review-loop, evidence, handoff, projection, and release-gate behavior
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
- the refactor does not weaken the local-first, event-sourced, replay-aware
  architecture described in [architecture.md](./architecture.md)
- the refactor does not weaken the v13 review-loop and publication-boundary
  contracts described in [v13-review-loop-contract.md](./v13-review-loop-contract.md)
  and [publication-boundary.md](./publication-boundary.md)

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
    cli/tui/
    core/
    runtime/
    services/
    store/
    tools/
    web/
    web/routes/
frontend/
frontend/components/console/
frontend/stores/
frontend/generated/
tests/
evals/
docs/
scripts/
```

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
uv run python scripts/validate_v13_release_gate.py --dry-run
```

During incremental refactor work, use narrower commands when possible:

```bash
uv run pytest tests/unit/test_specific_module.py
uv run pytest tests/integration/test_specific_flow.py
uv run ruff check src/glassbox/path.py tests/path_test.py
uv run ty check src/glassbox/path.py
pnpm --dir frontend test -- changeset-console.test.tsx
pnpm --dir frontend typecheck
uv run python scripts/validate_v13_release_gate.py --dry-run
```

When the work touches generated web contracts, include:

```bash
pnpm --dir frontend api:generate
git diff -- frontend/generated
```

When the work touches packaged dashboard behavior, include:

```bash
pnpm --dir frontend build
uv run python scripts/validate_package_contents.py
```

## Current State

The v13 release-candidate track extended the v12 reviewable-change model into a
local review loop:

- local review feedback records, scopes, dispositions, reopenings, archival,
  and accepted-risk evidence
- review response tracking and response-linked fixup inventory posture
- manual evidence attachments with summary-first redaction and explicit
  non-claims
- browser, dashboard, and accessibility evidence attachments with advisory
  boundaries
- lifecycle briefs with feedback, responses, manual evidence, live evidence,
  stale verification, risks, safe commands, and publication-boundary posture
- handoff readiness and commit-preparation context that remain read-only and
  advisory
- `/review` and `/changeset` in-session entry points for TUI and plain
  interactive mode
- a v13 release gate that layers review-loop evals, command coverage, coverage
  audit, package checks, installed smoke, and advisory evidence rows on top of
  inherited v12 release evidence

The implementation is coherent, but v13 concentrated new behavior in a handful
of places. The next refactor should keep those contracts dependable before
another product milestone expands review-loop behavior.

Current pressure points include:

- `src/glassbox/runtime/changesets.py`
- `src/glassbox/cli/changeset_commands.py`
- `src/glassbox/cli/parser_changesets.py`
- `src/glassbox/cli/tui/app_commands.py`
- `src/glassbox/cli/tui/commands.py`
- `src/glassbox/cli/interactive_session.py`
- `src/glassbox/web/changeset_api.py`
- `src/glassbox/web/routes/changesets.py`
- `src/glassbox/store/sqlite_projection_changesets.py`
- `src/glassbox/store/sqlite_projection_review_loop.py`
- `src/glassbox/store/sqlite_query_changesets.py`
- `src/glassbox/store/sqlite_query_review_loop.py`
- `src/glassbox/store/repository_changesets.py`
- `src/glassbox/store/repository_review_loop.py`
- `src/glassbox/services/contracts.py`
- `frontend/components/console/changeset-console.tsx`
- `frontend/stores/changeset-store.ts`
- `frontend/api/client.ts`
- `scripts/validate_v13_release_gate.py`

Large files that are primarily model-heavy, generated, or test fixtures are not
automatically refactor targets. In particular, `core/events.py`,
`core/models.py`, `core/types.py`, generated frontend API types, and broad test
files should be split only when a real ownership or review problem appears.

## Milestone Map

The intended post-v13 refactor milestone order is:

1. v13 review-loop boundary refresh and guardrails
2. changeset runtime service decomposition
3. review feedback, response, and evidence decomposition
4. lifecycle brief, verification, handoff, and publication-boundary cleanup
5. CLI, TUI, and web transport decomposition
6. frontend changeset-console decomposition
7. store projection and repository boundary cleanup
8. release-gate, docs, and validation closeout

Each phase below corresponds to one concrete refactor milestone.

## Task Graph

---

## Phase 80: V13 Review-Loop Boundary Refresh

### GBX-R500: Define V13 Review-Loop Refactor Boundary Map

- Status: `DONE`
- Dependencies: none
- Target files:
  - [refactor-boundaries.md](./refactor-boundaries.md)
  - [architecture.md](./architecture.md)
  - [refactor-v13.md](./refactor-v13.md)
  - [test_architecture_guardrails.py](../tests/unit/test_architecture_guardrails.py)
- Work:
  - document the intended post-v13 compatibility facades and helper owners
  - name `runtime/changesets.py` as the stable changeset runtime facade once
    later phases extract behavior into focused modules
  - name `cli/changeset_commands.py`, `web/changeset_api.py`,
    `web/routes/changesets.py`, and `frontend/components/console/changeset-console.tsx`
    as stable entrypoints that should delegate to focused owners
  - distinguish model-heavy public surfaces from mixed-responsibility modules
    that should be split
  - keep v13 review-loop and publication-boundary non-goals explicit
- Deliverables:
  - documented boundary map for changeset runtime, CLI, web, store, frontend,
    and release-gate surfaces
  - guardrail test expectations for the new compatibility facades where the
    intended owner modules are already clear
- Validation:
  - `uv run pytest tests/unit/test_architecture_guardrails.py`
  - `uv run pytest tests/unit/test_release_candidate_docs.py -q`

Completion notes:

- Added the post-v13 review-loop compatibility facade and helper-owner map to
  [refactor-boundaries.md](./refactor-boundaries.md).
- Refreshed [architecture.md](./architecture.md) with the current post-v13
  review-loop refactor shape and runtime review-loop dependency boundaries.
- Added v13 guardrail expectations for current pressure-point growth,
  cross-layer imports, and documented boundary coverage.

### GBX-R501: Characterize Current Changeset Facade Behavior

- Status: `DONE`
- Dependencies: GBX-R500
- Target files:
  - [test_changeset_derivation.py](../tests/unit/test_changeset_derivation.py)
  - [test_changeset_derivation.py](../tests/integration/test_changeset_derivation.py)
  - [test_cli_changeset_commands.py](../tests/integration/test_cli_changeset_commands.py)
  - [test_web_changeset_routes.py](../tests/integration/test_web_changeset_routes.py)
  - [dashboard-stores.test.ts](../frontend/tests/dashboard-stores.test.ts)
  - [changeset-console.test.tsx](../frontend/tests/changeset-console.test.tsx)
- Work:
  - identify the highest-risk current behaviors before movement begins
  - add characterization coverage where a behavior is about to move and is not
    already asserted
  - prefer narrow tests around derived limitations, non-claims, safe commands,
    response status, handoff readiness, and rejected evidence posture
- Deliverables:
  - current behavior coverage sufficient for the first runtime extraction tasks
  - explicit list of accepted behavior gaps that should not block refactor-only
    movement
- Validation:
  - `uv run pytest tests/unit/test_changeset_derivation.py`
  - `uv run pytest tests/integration/test_changeset_derivation.py`
  - `uv run pytest tests/integration/test_cli_changeset_commands.py -k changeset`
  - `uv run pytest tests/integration/test_web_changeset_routes.py`
  - `pnpm --dir frontend test -- dashboard-stores.test.ts changeset-console.test.tsx`

Completion notes:

- Added focused runtime characterization for changeset detail assembly when a
  changeset has no structured inventory, including source limitations,
  inventory posture, safe next actions, empty response-summary non-claims, and
  rejected manual evidence appearing in detail views.
- Accepted behavior gaps for the first runtime extraction:
  - broad CLI and web integration flows already cover feedback, evidence,
    verification, handoff, commit-prep, stale verification, and advisory
    non-claims, so no extra duplicate CLI/web assertions were added here
  - frontend changeset console and store coverage already exercises the current
    response status, handoff, verification, evidence, and non-claim rendering;
    frontend section splits should add narrower component tests when sections
    are extracted in Phase 85
  - response-linked fixup inventory has dedicated coverage in
    `test_review_response_fixup_inventory.py` and remains out of scope for this
    first characterization slice

### GBX-R502: Add V13 Facade Guardrails After First Extraction

- Status: `DONE`
- Dependencies: GBX-R510, GBX-R520, GBX-R540
- Target files:
  - [test_architecture_guardrails.py](../tests/unit/test_architecture_guardrails.py)
  - [refactor-boundaries.md](./refactor-boundaries.md)
- Work:
  - add facade line-count and import-prefix expectations only after the helper
    modules exist
  - assert that v13 facade modules delegate to intended owner modules
  - keep the guardrails narrow enough that they catch regression without
    freezing legitimate implementation detail
- Deliverables:
  - post-extraction architecture tests for runtime, CLI/API, and frontend
    facades
- Validation:
  - `uv run pytest tests/unit/test_architecture_guardrails.py`

Completion notes:

- Added post-extraction facade size and import-prefix guardrails for
  `runtime/changesets.py`, `cli/changeset_commands.py`,
  `cli/parser_changesets.py`, `web/changeset_api.py`, and
  `web/routes/changesets.py`.
- Added delegate-import guardrails that require the v13 runtime, CLI, parser,
  web API, and changeset route facades to import their intended helper owners.
- Refreshed `refactor-boundaries.md` to document the active post-extraction
  guardrails and note that frontend changeset entrypoints remain under
  pre-split growth/dependency guardrails until Phase 85 helpers exist.

---

## Phase 81: Changeset Runtime Service Decomposition

### GBX-R510: Split Changeset Runtime Models And Protocols

- Status: `DONE`
- Dependencies: GBX-R501
- Target files:
  - `src/glassbox/runtime/changesets.py`
  - `src/glassbox/runtime/changeset_models.py`
  - `src/glassbox/runtime/changeset_repository_contracts.py`
- Work:
  - move runtime-only Pydantic result/view models out of `changesets.py`
  - move `ChangesetDerivationRepository` and `ChangesetRepository` protocols
    into a focused contracts module
  - preserve public imports from `runtime/changesets.py` through explicit
    re-exports
  - keep core event and record models in `core/`
- Deliverables:
  - thin model/protocol modules with no service orchestration
  - compatibility imports preserved for CLI, web, tests, and existing callers
- Validation:
  - `uv run ruff check src/glassbox/runtime/changesets.py src/glassbox/runtime/changeset_models.py src/glassbox/runtime/changeset_repository_contracts.py`
  - `uv run ty check src/glassbox/runtime/changesets.py src/glassbox/runtime/changeset_models.py src/glassbox/runtime/changeset_repository_contracts.py`
  - `uv run pytest tests/unit/test_changeset_derivation.py`
  - `uv run pytest tests/integration/test_changeset_derivation.py`

Completion notes:

- Moved public runtime-only changeset result and view models into
  `src/glassbox/runtime/changeset_models.py`.
- Moved `ChangesetDerivationRepository` and `ChangesetRepository` protocols into
  `src/glassbox/runtime/changeset_repository_contracts.py`.
- Kept `src/glassbox/runtime/changesets.py` as the compatibility facade by
  importing and re-exporting the moved public names.

### GBX-R511: Extract Changeset Source Derivation And Workspace Diff Helpers

- Status: `DONE`
- Dependencies: GBX-R510
- Target files:
  - `src/glassbox/runtime/changesets.py`
  - `src/glassbox/runtime/changeset_derivation.py`
  - `src/glassbox/runtime/changeset_workspace_diff.py`
- Work:
  - move `ChangesetDerivationService` and source-specific creation helpers into
    `changeset_derivation.py`
  - move workspace diff snapshot, porcelain filtering, digest, and safe local
    state filtering helpers into `changeset_workspace_diff.py`
  - preserve source limitation behavior, event emission, artifact retention,
    and no-mutation claims
  - keep `changesets.py` as a compatibility facade for imports
- Deliverables:
  - source creation and workspace diff logic independently testable without
    importing the whole changeset runtime surface
- Validation:
  - `uv run pytest tests/unit/test_changeset_derivation.py`
  - `uv run pytest tests/integration/test_changeset_derivation.py`
  - `uv run pytest tests/integration/test_cli_changeset_commands.py -k "create or refresh"`

Completion notes:

- Moved `ChangesetDerivationService`, source limitation shaping, and
  source-specific creation paths into `src/glassbox/runtime/changeset_derivation.py`.
- Moved workspace diff snapshots, source digests, git byte reads, porcelain
  filtering, and `.glassbox` local-state filtering into
  `src/glassbox/runtime/changeset_workspace_diff.py`.
- Kept `src/glassbox/runtime/changesets.py` as the compatibility facade while
  delegating derivation and workspace diff calls to the focused modules.

### GBX-R512: Extract Changeset Query View Assembly

- Status: `DONE`
- Dependencies: GBX-R510
- Target files:
  - `src/glassbox/runtime/changesets.py`
  - `src/glassbox/runtime/changeset_queries.py`
  - `src/glassbox/runtime/changeset_detail.py`
  - `src/glassbox/runtime/changeset_inventory_status.py`
- Work:
  - move `ChangesetQueryService` into a focused query facade
  - move detail assembly, inventory freshness/status, limitations, and safe
    next action derivation into helper modules
  - keep query service transport-agnostic and repository-backed
  - preserve current detail view shape and ordering
- Deliverables:
  - readable query-service boundary that can be consumed by CLI, web, and
    handoff/commit services without web imports
- Validation:
  - `uv run pytest tests/unit/test_changeset_derivation.py`
  - `uv run pytest tests/integration/test_web_changeset_routes.py`
  - `uv run pytest tests/integration/test_cli_changeset_commands.py -k show`

Completion notes:

- Moved `ChangesetQueryService` into
  `src/glassbox/runtime/changeset_queries.py` while preserving the
  `runtime/changesets.py` compatibility import.
- Moved detail read-model assembly, review-response summaries, preview query
  helpers, and bounded command-evidence shaping into
  `src/glassbox/runtime/changeset_detail.py`.
- Moved changeset inventory freshness/status and review-fixup inventory
  freshness checks into `src/glassbox/runtime/changeset_inventory_status.py`.
- Kept query/detail helpers transport-agnostic and repository-backed; CLI, web,
  commit, handoff, and export callers continue through the existing public
  facade.

### GBX-R513: Extract Changeset Mutation Actions

- Status: `DONE`
- Dependencies: GBX-R511, GBX-R512
- Target files:
  - `src/glassbox/runtime/changesets.py`
  - `src/glassbox/runtime/changeset_actions.py`
  - `src/glassbox/runtime/changeset_inventory_refresh.py`
- Work:
  - move `ChangesetActionService` and inventory refresh mutation paths out of
    `changesets.py`
  - keep artifact writing, supersede events, readiness events, and inventory
    digest behavior unchanged
  - preserve async API used by CLI and web callers
- Deliverables:
  - mutation service that depends on query/detail helpers without owning their
    presentation behavior
- Validation:
  - `uv run pytest tests/integration/test_changeset_derivation.py`
  - `uv run pytest tests/integration/test_changeset_projection.py`
  - `uv run pytest tests/integration/test_cli_changeset_commands.py -k refresh`

Completion notes:

- Moved `ChangesetActionService` into
  `src/glassbox/runtime/changeset_actions.py` while preserving the
  `runtime/changesets.py` compatibility import.
- Moved structured inventory refresh mutation, artifact writing, supersede
  event emission, source digest capture, and freshness shaping into
  `src/glassbox/runtime/changeset_inventory_refresh.py`.
- Kept the async `ChangesetActionService.refresh_inventory(...)` API intact by
  delegating to `ChangesetInventoryRefreshService`.

---

## Phase 82: Review Feedback, Response, And Evidence Decomposition

### GBX-R520: Extract Review Feedback Action Service

- Status: `DONE`
- Dependencies: GBX-R512
- Target files:
  - `src/glassbox/runtime/changesets.py`
  - `src/glassbox/runtime/review_feedback_actions.py`
  - `src/glassbox/runtime/review_feedback_scopes.py`
- Work:
  - move `ReviewFeedbackActionService` out of `changesets.py`
  - move scope defaults, scope validation helpers, disposition mutation, and
    feedback result shaping into focused helpers
  - preserve local-evidence, not-approval, and no-publication non-claims
- Deliverables:
  - review feedback mutation service independent from changeset creation and
    lifecycle brief assembly
- Validation:
  - `uv run pytest tests/integration/test_review_loop_projection.py`
  - `uv run pytest tests/integration/test_cli_changeset_commands.py -k feedback`
  - `uv run pytest tests/integration/test_web_changeset_routes.py -k feedback`

Completion notes:

- Moved `ReviewFeedbackActionService` into
  `src/glassbox/runtime/review_feedback_actions.py` while preserving the
  `runtime/changesets.py` compatibility import.
- Moved review-feedback scope inference and default scope reasons into
  `src/glassbox/runtime/review_feedback_scopes.py`.
- Kept result shaping, local-evidence non-claims, and no-publication non-claims
  unchanged; the documented `-k feedback` selectors currently match no tests,
  so the full CLI and web changeset route integration files were run instead.

### GBX-R521: Extract Manual Evidence Action Service

- Status: `DONE`
- Dependencies: GBX-R520
- Target files:
  - `src/glassbox/runtime/changesets.py`
  - `src/glassbox/runtime/manual_evidence_actions.py`
  - `src/glassbox/runtime/manual_evidence.py`
- Work:
  - move `ManualEvidenceActionService` out of `changesets.py`
  - keep redaction and artifact schema helpers in `manual_evidence.py`
  - move service-level target resolution, rejected-event construction,
    accepted-event construction, and action result shaping into
    `manual_evidence_actions.py`
  - preserve absolute-path, `.glassbox`, secret-looking, oversized, and raw
    provider-output rejection behavior
- Deliverables:
  - manual evidence capture service that makes summary-first redaction
    boundaries obvious
- Validation:
  - `uv run pytest tests/unit/test_manual_evidence.py`
  - `uv run pytest tests/integration/test_cli_changeset_commands.py -k evidence`
  - `uv run pytest tests/integration/test_web_changeset_routes.py -k evidence`

Completion notes:

- Moved `ManualEvidenceActionService` into
  `src/glassbox/runtime/manual_evidence_actions.py` while preserving the
  `runtime/changesets.py` compatibility import.
- Kept redaction, artifact schema models, artifact JSON, and validation helpers
  in `src/glassbox/runtime/manual_evidence.py`.
- Moved service-level target resolution, rejected-event construction,
  accepted-event construction, and action result shaping into the action module
  without changing manual-evidence non-claims or redaction behavior.
- The documented `-k evidence` selectors currently match no tests, so the full
  CLI and web changeset route integration files were run instead.

### GBX-R522: Extract Browser And Accessibility Evidence Actions

- Status: `DONE`
- Dependencies: GBX-R521
- Target files:
  - `src/glassbox/runtime/changesets.py`
  - `src/glassbox/runtime/browser_evidence_actions.py`
  - `src/glassbox/runtime/accessibility_evidence_actions.py`
  - `src/glassbox/runtime/browser_evidence.py`
  - `src/glassbox/runtime/accessibility_evidence.py`
- Work:
  - move `BrowserEvidenceActionService` and
    `AccessibilityEvidenceActionService` out of `changesets.py`
  - keep artifact schema helpers in the existing browser/accessibility evidence
    modules
  - preserve advisory limitations, skipped-case notes, local-only references,
    and non-claims
- Deliverables:
  - live-evidence action services that can evolve independently from manual
    evidence and changeset query views
- Validation:
  - `uv run pytest tests/integration/test_cli_changeset_commands.py -k "browser or dashboard or accessibility"`
  - `uv run pytest tests/integration/test_web_changeset_routes.py -k "browser or accessibility"`

Completion notes:

- Moved `BrowserEvidenceActionService` into
  `src/glassbox/runtime/browser_evidence_actions.py` while preserving the
  `runtime/changesets.py` compatibility import.
- Moved `AccessibilityEvidenceActionService` into
  `src/glassbox/runtime/accessibility_evidence_actions.py` while preserving the
  same public facade import.
- Kept browser and accessibility capture formatting, advisory limitations,
  local-only references, and non-claim helpers in their existing evidence
  modules.
- The documented `-k` selectors currently match no tests in the integration
  files, so the full CLI and web changeset route integration files were run
  instead.

### GBX-R523: Extract Review Fixup Inventory Service Boundary

- Status: `DONE`
- Dependencies: GBX-R520, GBX-R513
- Target files:
  - `src/glassbox/runtime/changesets.py`
  - `src/glassbox/runtime/review_fixup_actions.py`
  - `src/glassbox/runtime/review_responses.py`
- Work:
  - move `ReviewFeedbackFixupInventoryService` out of `changesets.py`
  - keep artifact schema and response-status derivation in
    `review_responses.py`
  - move service-level inventory attachment, artifact persistence, and event
    construction into `review_fixup_actions.py`
  - preserve conservative blocked/stale response status when no fixup inventory
    exists
- Deliverables:
  - explicit boundary for response-linked changed-path evidence
- Validation:
  - `uv run pytest tests/integration/test_review_response_fixup_inventory.py`
  - `uv run pytest tests/unit/test_review_responses.py`
  - `uv run pytest tests/integration/test_cli_changeset_commands.py -k "feedback and status"`

Completion notes:

- Moved `ReviewFeedbackFixupInventoryService` into
  `src/glassbox/runtime/review_fixup_actions.py` while preserving the
  `runtime/changesets.py` compatibility import.
- Kept fixup inventory artifact schema helpers and response-status derivation
  in `src/glassbox/runtime/review_responses.py`.
- Moved response-linked workspace inventory attachment, artifact persistence,
  freshness event construction, and result shaping into the action module.
- The documented CLI `-k "feedback and status"` selector currently matches no
  tests, so the full CLI changeset integration file was run instead.

---

## Phase 83: Lifecycle Brief, Verification, Handoff, And Publication Boundary Cleanup

### GBX-R530: Extract Changeset Verification Preview Service

- Status: `DONE`
- Dependencies: GBX-R512, GBX-R523
- Target files:
  - `src/glassbox/runtime/changesets.py`
  - `src/glassbox/runtime/changeset_verification.py`
  - `src/glassbox/runtime/changeset_verification_preview.py`
  - `src/glassbox/runtime/changeset_verification_readiness.py`
- Work:
  - move `ChangesetVerificationService`, recipe previewing, safe command
    filtering, eval profile selection, and review-loop verification summaries
    out of `changesets.py`
  - keep lower-level readiness derivation in
    `changeset_verification_readiness.py`
  - preserve missing/stale/manual-only/live-evidence advisory distinctions
  - keep recommended commands as previews only
- Deliverables:
  - verification preview service that can be tested without lifecycle brief or
    evidence action service imports
- Validation:
  - `uv run pytest tests/unit/test_changeset_verification_readiness.py`
  - `uv run pytest tests/integration/test_cli_changeset_commands.py -k verification`
  - `uv run pytest tests/integration/test_web_changeset_routes.py -k verification`

### GBX-R531: Extract Lifecycle Review Brief Assembly

- Status: `DONE`
- Dependencies: GBX-R512, GBX-R520, GBX-R521, GBX-R522, GBX-R530
- Target files:
  - `src/glassbox/runtime/changesets.py`
  - `src/glassbox/runtime/changeset_review_brief_service.py`
  - `src/glassbox/runtime/changeset_review_brief_sections.py`
  - `src/glassbox/runtime/review_briefs.py`
- Work:
  - move `ChangesetReviewBriefService` out of `changesets.py`
  - move section assembly helpers for change summary, inventory, provenance,
    topology, lifecycle, feedback, responses, manual evidence, live evidence,
    verification, stale verification, command evidence, publication boundary,
    branch candidates, risks, checklist, safe commands, local-only posture, and
    limitations into section helpers
  - keep artifact schema and markdown rendering in `review_briefs.py`
  - preserve the current artifact schema unless a later product task explicitly
    changes rich-evidence limitation handling
- Deliverables:
  - lifecycle brief service with independently testable section derivation
- Validation:
  - `uv run pytest tests/unit/test_review_briefs.py`
  - `uv run pytest tests/integration/test_cli_changeset_commands.py -k brief`
  - `uv run pytest tests/integration/test_web_changeset_routes.py -k brief`

### GBX-R532: Extract Command Evidence And Safe Command Helpers

- Status: `DONE`
- Dependencies: GBX-R512, GBX-R530, GBX-R531
- Target files:
  - `src/glassbox/runtime/changesets.py`
  - `src/glassbox/runtime/changeset_command_evidence.py`
  - `src/glassbox/runtime/changeset_safe_commands.py`
  - `src/glassbox/runtime/command_evidence.py`
- Work:
  - move changeset-specific command evidence summary and item shaping out of
    `changesets.py`
  - move duplicated safe next action strings into a focused helper where
    runtime callers can share them
  - preserve command evidence purpose, review relevance, environment redaction,
    and local-only posture
- Deliverables:
  - one owner for changeset command evidence rows and review-loop safe command
    templates
- Validation:
  - `uv run pytest tests/integration/test_cli_changeset_commands.py -k "show or verification or brief or handoff"`
  - `uv run pytest tests/unit/test_review_briefs.py`
  - `uv run pytest tests/unit/test_commit_readiness.py`

### GBX-R533: Decouple Handoff And Commit Readiness From Changesets Facade

- Status: `DONE`
- Dependencies: GBX-R512, GBX-R530, GBX-R532
- Target files:
  - `src/glassbox/runtime/handoff_readiness.py`
  - `src/glassbox/runtime/commit_readiness.py`
  - `src/glassbox/runtime/changesets.py`
- Work:
  - update handoff and commit readiness imports to consume extracted query,
    verification, command-evidence, and safe-command modules
  - avoid importing the broad `runtime/changesets.py` facade from readiness
    modules when narrower owners exist
  - preserve all publication-boundary non-claims and no-mutation behavior
- Deliverables:
  - handoff and commit readiness services that depend on focused review-loop
    helpers instead of the broad changeset facade
- Validation:
  - `uv run pytest tests/unit/test_handoff_readiness.py`
  - `uv run pytest tests/unit/test_commit_readiness.py`
  - `uv run pytest tests/integration/test_cli_changeset_commands.py -k "handoff or commit"`

---

## Phase 84: CLI, TUI, And Web Transport Decomposition

### GBX-R540: Split Changeset CLI Service Wiring From Formatting

- Status: `DONE`
- Dependencies: GBX-R510, GBX-R512, GBX-R520, GBX-R530, GBX-R531
- Target files:
  - `src/glassbox/cli/changeset_commands.py`
  - `src/glassbox/cli/changeset_command_handlers.py`
  - `src/glassbox/cli/changeset_command_payloads.py`
  - `src/glassbox/cli/changeset_command_formatters.py`
- Work:
  - keep `changeset_commands.py` as the command dispatch facade
  - move runtime-context opening and service wiring into handler helpers
  - move JSON payload builders into payload helpers
  - move terminal formatting into formatter helpers
  - preserve command names, aliases, arguments, exit-code behavior, and
    operator-visible copy
- Deliverables:
  - reviewable CLI command facade with focused formatting and payload modules
- Validation:
  - `uv run pytest tests/integration/test_cli_changeset_commands.py`
  - `uv run pytest tests/unit/test_release_candidate_docs.py -q`

### GBX-R541: Split Parser Changeset Argument Families

- Status: `DONE`
- Dependencies: GBX-R540
- Target files:
  - `src/glassbox/cli/parser_changesets.py`
  - `src/glassbox/cli/parser_changeset_feedback.py`
  - `src/glassbox/cli/parser_changeset_evidence.py`
  - `src/glassbox/cli/parser_changeset_review.py`
- Work:
  - keep `parser_changesets.py` as a stable parser entrypoint
  - move feedback, evidence, verification/brief/handoff, and commit-prep
    subparser wiring into helper modules
  - preserve help text, aliases, defaults, validation patterns, and command
    guide expectations
- Deliverables:
  - parser wiring split by operator workflow family
- Validation:
  - `uv run pytest tests/integration/test_cli_changeset_commands.py`
  - `uv run pytest tests/unit/test_release_candidate_docs.py -q`
  - `uv run glassbox command tree`

### GBX-R542: Extract TUI And Plain Review Command Helpers

- Status: `DONE`
- Dependencies: GBX-R540
- Target files:
  - `src/glassbox/cli/tui/commands.py`
  - `src/glassbox/cli/tui/app_commands.py`
  - `src/glassbox/cli/interactive_session.py`
  - `src/glassbox/cli/interactive_review_commands.py`
  - `src/glassbox/cli/tui/review_commands.py`
- Work:
  - move `/review` and `/changeset` command parsing, action routing, disabled
    reasons, and feedback messages into review-specific helpers
  - preserve TUI and plain interactive behavior, including current-session
    defaults and safe post-create output
  - keep lower-level `glassbox changeset ...` commands as the scriptable API
- Deliverables:
  - review-loop terminal UX helpers that can evolve without expanding generic
    TUI app command modules
- Validation:
  - `uv run pytest tests/unit/test_cli_interactive_session.py`
  - `uv run pytest tests/integration/test_cli_tui_review_commands.py`
  - `uv run pytest tests/integration/test_cli_interactive_commands.py -k review`

### GBX-R543: Split Changeset Web Response Models And Builders

- Status: `DONE`
- Dependencies: GBX-R512, GBX-R520, GBX-R521, GBX-R530, GBX-R531, GBX-R533
- Target files:
  - `src/glassbox/web/changeset_api.py`
  - `src/glassbox/web/changeset_api_models.py`
  - `src/glassbox/web/changeset_api_builders.py`
  - `src/glassbox/web/review_loop_api.py`
- Work:
  - keep `web/changeset_api.py` as a compatibility facade for current route
    imports
  - move transport models into focused model modules
  - move response builders into builder modules
  - avoid importing FastAPI in builder modules
  - preserve OpenAPI schema shape unless explicitly changed
- Deliverables:
  - transport model and response-builder modules split by changeset,
    review-loop, verification, and readiness concerns
- Validation:
  - `uv run pytest tests/integration/test_web_changeset_routes.py`
  - `pnpm --dir frontend api:generate`
  - `pnpm --dir frontend typecheck`

Completion notes:

- Kept `src/glassbox/web/changeset_api.py` as the compatibility facade for
  existing route imports.
- Moved changeset, verification, commit-readiness, and handoff transport models
  into `src/glassbox/web/changeset_api_models.py`.
- Moved review feedback, manual evidence, browser evidence, and accessibility
  evidence transport models into `src/glassbox/web/review_loop_api.py`.
- Moved response conversion helpers into
  `src/glassbox/web/changeset_api_builders.py` without adding FastAPI imports
  to builder modules.
- Regenerated frontend API artifacts; no generated OpenAPI or API type diff was
  produced.

### GBX-R544: Split Changeset Route Service Factories And HTTP Errors

- Status: `DONE`
- Dependencies: GBX-R543
- Target files:
  - `src/glassbox/web/routes/changesets.py`
  - `src/glassbox/web/routes/changeset_route_services.py`
  - `src/glassbox/web/routes/changeset_route_errors.py`
  - `src/glassbox/web/routes/changeset_route_requests.py`
- Work:
  - move repository casts, service factories, workspace-root lookup, and common
    HTTP error translation into route-local helpers
  - keep FastAPI decorators and endpoint declarations easy to scan
  - preserve response models, status codes, validation patterns, and route
    paths
- Deliverables:
  - route module that reads as transport declaration rather than service
    orchestration
- Validation:
  - `uv run pytest tests/integration/test_web_changeset_routes.py`
  - `pnpm --dir frontend api:generate`
  - `pnpm --dir frontend test -- dashboard-stores.test.ts changeset-console.test.tsx`

Completion notes:

- Kept `src/glassbox/web/routes/changesets.py` as the FastAPI route
  declaration entrypoint while moving repository casts, service wiring, and
  workspace-root lookup into
  `src/glassbox/web/routes/changeset_route_services.py`.
- Moved common changeset route 404 translation into
  `src/glassbox/web/routes/changeset_route_errors.py`.
- Moved request enum/UUID coercion and create-changeset source branching into
  `src/glassbox/web/routes/changeset_route_requests.py`.
- Regenerated frontend API artifacts; no generated OpenAPI or API type diff was
  produced.

---

## Phase 85: Frontend Changeset Console Decomposition

### GBX-R550: Split Changeset Console Types, Formatting, And Shared Rows

- Status: `DONE`
- Dependencies: GBX-R543
- Target files:
  - `frontend/components/console/changeset-console.tsx`
  - `frontend/components/console/changeset/types.ts`
  - `frontend/components/console/changeset/format.ts`
  - `frontend/components/console/changeset/shared.tsx`
- Work:
  - keep `changeset-console.tsx` as the stable component entrypoint
  - move prop helper types, badge variants, state labels, fact rows, and shared
    presentation helpers into focused modules
  - preserve current visual hierarchy and accessibility labels
- Deliverables:
  - first frontend split that prepares later section extraction without
    changing behavior
- Validation:
  - `pnpm --dir frontend test -- changeset-console.test.tsx`
  - `pnpm --dir frontend typecheck`
  - `pnpm --dir frontend lint`

Completion notes:

- Kept `frontend/components/console/changeset-console.tsx` as the stable
  component entrypoint and compatibility export for `ChangesetConsoleProps`.
- Moved changeset console prop/input helper types into
  `frontend/components/console/changeset/types.ts`.
- Moved badge variant and verification-state formatting helpers into
  `frontend/components/console/changeset/format.ts`.
- Moved shared fact row, section, and state-line presentation helpers into
  `frontend/components/console/changeset/shared.tsx` without changing
  accessibility labels or visual hierarchy.

### GBX-R551: Split Changeset List And Detail Shell

- Status: `TODO`
- Dependencies: GBX-R550
- Target files:
  - `frontend/components/console/changeset-console.tsx`
  - `frontend/components/console/changeset/list.tsx`
  - `frontend/components/console/changeset/detail.tsx`
  - `frontend/components/console/changeset/actions.tsx`
- Work:
  - move list rendering, empty/error states, detail header, and action buttons
    into section modules
  - keep action props stable
  - preserve compact dashboard ergonomics and current test expectations
- Deliverables:
  - changeset console entrypoint reduced to composition over owned sections
- Validation:
  - `pnpm --dir frontend test -- changeset-console.test.tsx`
  - `pnpm --dir frontend typecheck`
  - `pnpm --dir frontend lint`

### GBX-R552: Split Evidence, Feedback, Verification, And Handoff Sections

- Status: `TODO`
- Dependencies: GBX-R551
- Target files:
  - `frontend/components/console/changeset-console.tsx`
  - `frontend/components/console/changeset/feedback.tsx`
  - `frontend/components/console/changeset/evidence.tsx`
  - `frontend/components/console/changeset/verification.tsx`
  - `frontend/components/console/changeset/handoff.tsx`
  - `frontend/components/console/changeset/commit-prep.tsx`
- Work:
  - move feedback status, manual evidence, verification preview, lifecycle
    brief, handoff readiness, and commit preparation panels into focused
    section modules
  - keep read-only and evidence-recording actions visually distinct
  - preserve advisory/non-claim copy and current local form state behavior
- Deliverables:
  - v13 evidence families independently reviewable in frontend code
- Validation:
  - `pnpm --dir frontend test -- changeset-console.test.tsx dashboard-stores.test.ts`
  - `pnpm --dir frontend typecheck`
  - `pnpm --dir frontend lint`

### GBX-R553: Split Changeset Store Actions And Selectors

- Status: `TODO`
- Dependencies: GBX-R543, GBX-R552
- Target files:
  - `frontend/stores/changeset-store.ts`
  - `frontend/stores/changeset-store-actions.ts`
  - `frontend/stores/changeset-store-selectors.ts`
  - `frontend/api/client.ts`
- Work:
  - move API action groups and derived selectors out of the store factory when
    they are not store initialization concerns
  - preserve the compatibility export through `dashboard-stores.ts`
  - keep transport in stores/API client, not components
- Deliverables:
  - changeset store split that matches existing domain-store patterns
- Validation:
  - `pnpm --dir frontend test -- dashboard-stores.test.ts changeset-console.test.tsx`
  - `pnpm --dir frontend typecheck`
  - `pnpm --dir frontend lint`

---

## Phase 86: Store Projection And Repository Boundary Cleanup

### GBX-R560: Split Changeset Projection Event Families

- Status: `TODO`
- Dependencies: GBX-R500, GBX-R520, GBX-R521, GBX-R523
- Target files:
  - `src/glassbox/store/sqlite_projection_changesets.py`
  - `src/glassbox/store/sqlite_projection_review_loop.py`
  - `src/glassbox/store/sqlite_projection_changeset_lifecycle.py`
  - `src/glassbox/store/sqlite_projection_changeset_inventory.py`
  - `src/glassbox/store/sqlite_projection_review_feedback.py`
  - `src/glassbox/store/sqlite_projection_manual_evidence.py`
- Work:
  - keep existing projection coordinator entrypoints stable
  - move changeset lifecycle, inventory, readiness, review feedback, fixup
    inventory, and manual evidence handlers into event-family helpers where the
    current module boundaries are too broad
  - preserve projection rebuild behavior and table contents
- Deliverables:
  - projection handlers split by canonical event family
- Validation:
  - `uv run pytest tests/integration/test_changeset_projection.py`
  - `uv run pytest tests/integration/test_review_loop_projection.py`
  - `uv run pytest tests/integration/test_sqlite_projections.py -k changeset`

### GBX-R561: Split Changeset Query Helpers

- Status: `TODO`
- Dependencies: GBX-R560
- Target files:
  - `src/glassbox/store/sqlite_query_changesets.py`
  - `src/glassbox/store/sqlite_query_review_loop.py`
  - `src/glassbox/store/sqlite_query_changeset_detail.py`
  - `src/glassbox/store/sqlite_query_review_feedback.py`
  - `src/glassbox/store/sqlite_query_manual_evidence.py`
- Work:
  - split broad query helpers by read-model family where review pressure is
    now high
  - keep `sqlite_queries.py` facade exports stable
  - preserve row ordering, pagination, include flags, and enum coercion
- Deliverables:
  - focused SQLite query modules aligned with runtime query-service needs
- Validation:
  - `uv run pytest tests/integration/test_changeset_projection.py`
  - `uv run pytest tests/integration/test_review_loop_projection.py`
  - `uv run pytest tests/unit/test_sqlite_query_boundaries.py`

### GBX-R562: Split Repository Adapter Mixins By Review-Loop Domain

- Status: `TODO`
- Dependencies: GBX-R561
- Target files:
  - `src/glassbox/store/repository_changesets.py`
  - `src/glassbox/store/repository_review_loop.py`
  - `src/glassbox/store/repositories.py`
  - `src/glassbox/services/contracts.py`
- Work:
  - move adapter methods into domain mixins where current changeset/review-loop
    method groupings obscure ownership
  - keep `SQLiteSessionRepository` public imports stable
  - split service protocols only along stable domain boundaries, not by line
    count alone
- Deliverables:
  - repository adapters that expose existing contracts while making review-loop
    method ownership explicit
- Validation:
  - `uv run pytest tests/unit/test_repository_adapter_boundaries.py`
  - `uv run pytest tests/integration/test_changeset_projection.py`
  - `uv run pytest tests/integration/test_review_loop_projection.py`
  - `uv run pytest tests/unit/test_architecture_guardrails.py`

---

## Phase 87: Release Gate, Docs, And Validation Closeout

### GBX-R570: Extract V13 Release-Gate Helper Owners

- Status: `TODO`
- Dependencies: GBX-R500
- Target files:
  - `scripts/validate_v13_release_gate.py`
  - `scripts/v13_release_gate_helpers.py`
  - `tests/unit/test_v13_release_gate.py`
- Work:
  - move v13-specific stage construction, advisory provider row relabeling,
    browser/accessibility advisory rows, dry-run planning, and summary metadata
    into helper functions or a helper module
  - preserve command-line behavior, evidence summary shape, default evidence
    paths, dry-run behavior, and installed-wheel smoke behavior
  - do not change blocking versus advisory release authority
- Deliverables:
  - release-gate script that stays a clear operator entrypoint
  - helper coverage for v13-specific summary shaping
- Validation:
  - `uv run pytest tests/unit/test_v13_release_gate.py`
  - `uv run python scripts/validate_v13_release_gate.py --dry-run`

### GBX-R571: Refresh Refactor Documentation And Package Metadata Expectations

- Status: `TODO`
- Dependencies: GBX-R502, GBX-R570
- Target files:
  - [README.md](../README.md)
  - [README.md](./README.md)
  - [architecture.md](./architecture.md)
  - [refactor-boundaries.md](./refactor-boundaries.md)
  - [refactor-v13.md](./refactor-v13.md)
  - `scripts/validate_package_contents.py`
  - `tests/unit/test_packaging_metadata.py`
  - `tests/unit/test_release_candidate_docs.py`
- Work:
  - link the completed post-v13 refactor boundary docs where appropriate
  - update package-content expectations only if new docs or helper scripts
    should ship in sdists
  - keep historical v1/v8/v10/v11 refactor docs intact
- Deliverables:
  - docs hub and packaging expectations aligned with the new refactor roadmap
- Validation:
  - `uv run pytest tests/unit/test_release_candidate_docs.py -q`
  - `uv run pytest tests/unit/test_packaging_metadata.py`
  - `uv run python scripts/validate_package_contents.py`

### GBX-R572: Run Post-V13 Refactor Release Confidence Sweep

- Status: `TODO`
- Dependencies: all previous tasks
- Target files:
  - [refactor-v13.md](./refactor-v13.md)
  - [v13-release-candidate.md](./v13-release-candidate.md)
  - release evidence under `.glassbox/releases/`
- Work:
  - run the full validation stack after the refactor phases complete
  - record any intentional replay/eval drift through the established eval
    refresh workflow
  - document any accepted compatibility shims that remain
  - document any product follow-up candidates that should not be conflated with
    refactor-only work
- Deliverables:
  - final validation evidence and a short closeout note in this roadmap
  - clear list of remaining compatibility facades and intended owners
- Validation:
  - `uv run ruff format --check .`
  - `uv run ruff check .`
  - `uv run ty check`
  - `uv run pytest -n auto --dist loadfile`
  - `uv run pre-commit run --all-files`
  - `pnpm --dir frontend lint`
  - `pnpm --dir frontend typecheck`
  - `pnpm --dir frontend test`
  - `pnpm --dir frontend build`
  - `uv run python scripts/validate_v13_release_gate.py --dry-run`

## Accepted Product Follow-Up Candidates

These findings came from v13 dogfooding and release-candidate evidence. They
are useful context for refactor planning, but they are not refactor-only tasks
unless a later roadmap explicitly chooses to change behavior:

- allow an explicit skipped or unknown viewport mode for dashboard evidence
  that intentionally did not open a browser
- cap, deduplicate, or summarize lifecycle-brief limitations before artifact
  validation so rich review-loop evidence does not exceed the current
  20-limitation schema boundary
- expose or document a lower-friction CLI path for response-linked fixup
  inventory so `feedback resolve` can be paired with changed-path evidence
- refresh future dogfooding recipes to avoid stale provider prefixes
- run fresh live browser and accessibility pairing evidence when the team wants
  advisory UX confidence beside deterministic release authority

Product follow-ups should preserve the v13 non-goals unless a future product
contract explicitly changes them.

## Accepted Compatibility Shims

The following facades are acceptable during this roadmap as long as they remain
thin and delegate to owned helpers after the relevant phase completes:

- `src/glassbox/runtime/changesets.py`
- `src/glassbox/cli/changeset_commands.py`
- `src/glassbox/cli/parser_changesets.py`
- `src/glassbox/web/changeset_api.py`
- `src/glassbox/web/routes/changesets.py`
- `frontend/components/console/changeset-console.tsx`
- `frontend/stores/dashboard-stores.ts`
- `scripts/validate_v13_release_gate.py`

Do not add new behavior to these facades once their helper owners exist. New
behavior should land in the focused owner module and be re-exported only when a
stable public import path requires it.
