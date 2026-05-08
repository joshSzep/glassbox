# Glassbox Refactor v14 Tasks

For the docs hub and operator guides, start at [README.md](./README.md). This
file is the next behavior-preserving refactor roadmap after
[refactor-v13.md](./refactor-v13.md). It starts from the completed v14
review-loop maturity milestone and targets the code paths that grew while v14
added rich lifecycle limitation summaries, response-linked fixup inventory
ergonomics, skipped advisory browser/dashboard/accessibility evidence,
review-loop command discovery, dashboard action states, advisory UX evidence,
deterministic v14 eval coverage, and the v14 release gate.

## Purpose

This document defines a post-v14 refactor roadmap for the current Glassbox
codebase.

It follows the execution style of [refactor-v1.md](./refactor-v1.md),
[refactor-v8.md](./refactor-v8.md), [refactor-v10.md](./refactor-v10.md),
[refactor-v11.md](./refactor-v11.md), and
[refactor-v13.md](./refactor-v13.md): explicit dependencies, small vertical
slices, concrete deliverables, and validation requirements attached directly to
the work.

This roadmap is not a product-feature roadmap. It exists to keep the current
local-first, event-sourced architecture easy to evolve by:

- separating v14 review-loop maturity derivation from artifact shaping,
  terminal guidance, web transport, dashboard state, and release-gate summary
  construction
- keeping lifecycle brief limitation summaries, response-linked fixup
  inventory, skipped advisory evidence, handoff readiness, commit readiness,
  dashboard action states, and advisory release evidence independently
  reviewable
- preserving current CLI, TUI, dashboard, API, replay, eval, package,
  projection, and release-gate behavior unless a later task explicitly changes
  a contract
- tightening architecture guardrails around the modules that grew after the
  v14 release-candidate milestone
- avoiding line-count-only splits in model-heavy, generated, fixture-heavy, or
  public compatibility surfaces

## Refactor Direction

The post-v13 refactor successfully split the broad changeset and review-loop
facades. The v14 milestone then matured the daily operator path by adding:

- deterministic lifecycle brief limitation summarization before reviewer-safe
  artifact validation
- first-class response-linked fixup inventory paths
- skipped advisory browser, dashboard, and accessibility evidence without fake
  observed environment details
- richer feedback response status, safe next actions, and handoff posture
- command-guide, plain interactive, TUI, and dashboard copy for the review-loop
  happy path
- fresh advisory dashboard/accessibility evidence summaries
- deterministic v14 eval cases and v14 release-gate stages

The new pressure is concentrated in modules that remain coherent, but now carry
too many neighboring responsibilities:

- `runtime/changeset_review_brief_sections.py` owns lifecycle section assembly,
  skipped-evidence copy, reviewer checklist shaping, safe commands, limitation
  collection, limitation prioritization, limitation summary construction, and
  review-readiness derivation.
- `runtime/review_responses.py` owns response/fixup models, fixup artifact
  construction, path-scope matching, response state derivation, blockers,
  verification posture, freshness, and safe next actions.
- `runtime/handoff_readiness.py` and `runtime/commit_readiness.py` both derive
  signal lists, blockers, aggregate states, limitations, safe actions, and
  non-claims from overlapping review-loop evidence.
- `cli/interactive_client.py` owns interactive client protocols, local runtime
  actions, daemon HTTP actions, SSE parsing, review-loop action orchestration,
  skipped-evidence counting, payload parsing, and terminal guidance copy.
- `cli/changeset_command_handlers.py` remains a broad scriptable command
  handler surface for changeset lifecycle, feedback, evidence, verification,
  readiness, adoption, export, and commit-preparation actions.
- `web/routes/changesets.py` remains readable, but it still repeats
  repository lookup, workspace-root lookup, action execution, post-mutation
  detail reload, and HTTP error translation patterns across many endpoints.
- `web/changeset_api_builders.py` is an intentionally large transport mapper,
  but v14 added enough review-loop and readiness fields that builder families
  should become easier to review independently.
- `frontend/stores/changeset-store-actions.ts` owns list/detail loading,
  reload bundles, action orchestration, user-facing action messages, and
  branch-search adjacency for the changeset dashboard.
- `frontend/api/client.ts` is a repo-wide API facade that is acceptable today,
  but it is accumulating endpoint families that can be grouped without moving
  transport into components.
- `scripts/v14_release_gate_helpers.py` is still modest, but it mixes inherited
  gate stages, v14 stage construction, advisory provider evidence, advisory UX
  evidence, dry-run copy, evidence-dir resolution, and summary metadata.

The post-v14 refactor thesis is:

- keep canonical events and managed artifacts as the source of truth
- keep projection tables rebuildable and non-authoritative
- keep runtime query and readiness services transport-agnostic
- keep web response models and frontend generated API types as transport
  contracts, not business-logic owners
- keep frontend stores responsible for transport and components responsible for
  presentation and local interaction state
- move limitation summarization, response/fixup status derivation,
  skipped-evidence recognition, readiness signal aggregation, terminal
  review-loop guidance, route action patterns, and release-gate summary shaping
  into focused owner modules
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
   publication-boundary claims unless the task explicitly includes that
   contract change.
3. Treat `events` as the canonical source of truth. Query services, route
   helpers, stores, frontend derivation, and UI projections remain derived from
   canonical events, typed API responses, managed artifacts, or rebuildable
   projection tables.
4. Repair architectural duplication before splitting files mechanically. If two
   modules shape the same limitation, skipped-evidence label, response blocker,
   safe command, readiness signal, or non-claim, extract the shared boundary
   first.
5. Prefer extractions with thin compatibility shims over broad rewrites. Keep
   diffs incremental and executable.
6. Keep public facades stable unless a task explicitly changes the import,
   route, API, command, store, or component contract.
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
12. Do not silently "fix" the current local-versus-daemon `/review fixup`
    parity gap during a refactor task. Characterize and document it first; only
    change behavior through a task that explicitly names the contract change.
13. Every refactor task automatically includes:
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
- the refactor does not weaken the v14 review-loop maturity and
  publication-boundary contracts described in
  [v14-review-loop-maturity-contract.md](./v14-review-loop-maturity-contract.md)
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
frontend/api/
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
uv run python scripts/validate_v14_release_gate.py --dry-run
```

During incremental refactor work, use narrower commands when possible:

```bash
uv run pytest tests/unit/test_review_briefs.py
uv run pytest tests/unit/test_review_responses.py
uv run pytest tests/unit/test_commit_readiness.py tests/unit/test_handoff_readiness.py
uv run pytest tests/unit/test_cli_interactive_client.py
uv run pytest tests/integration/test_cli_tui_review_commands.py
uv run pytest tests/integration/test_cli_interactive_commands.py -k review
uv run pytest tests/integration/test_web_changeset_routes.py
pnpm --dir frontend test -- changeset-console.test.tsx operator-actions.component.test.tsx
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

The v14 release-candidate track matured the v13 local review loop:

- lifecycle briefs now summarize rich limitation sets before artifact
  validation instead of failing the reviewer-safe cap
- response-linked fixup inventory has CLI, plain interactive, TUI, API, and
  dashboard paths
- skipped advisory browser, dashboard, and accessibility evidence can be
  recorded without inventing viewport, console, keyboard, screen-reader, or
  responsive observations
- feedback response status distinguishes missing, stale, attached,
  accepted-risk, blocked, and ready-for-handoff posture
- handoff readiness and commit readiness keep publication boundaries visible
- dashboard action states expose fixup, evidence, verification, brief, and
  handoff actions without claiming approval or publication
- v14 eval cases and the v14 release gate promote deterministic review-loop
  maturity behavior without turning advisory UX evidence into release
  authority

The implementation is coherent, but v14 concentrated new behavior in a handful
of places. The next refactor should keep those contracts dependable before
another product milestone expands review-loop maturity behavior.

Current pressure points include:

- `src/glassbox/runtime/changeset_review_brief_sections.py`
- `src/glassbox/runtime/review_responses.py`
- `src/glassbox/runtime/handoff_readiness.py`
- `src/glassbox/runtime/commit_readiness.py`
- `src/glassbox/cli/interactive_client.py`
- `src/glassbox/cli/changeset_command_handlers.py`
- `src/glassbox/cli/changeset_command_formatters.py`
- `src/glassbox/web/routes/changesets.py`
- `src/glassbox/web/changeset_api_builders.py`
- `frontend/api/client.ts`
- `frontend/stores/changeset-store-actions.ts`
- `frontend/components/console/changeset/evidence.tsx`
- `frontend/components/console/changeset/feedback.tsx`
- `frontend/components/console/changeset/handoff.tsx`
- `scripts/v14_release_gate_helpers.py`

Large files that are primarily model-heavy, generated, or test fixtures are not
automatically refactor targets. In particular, `core/events.py`,
`core/models.py`, `core/types.py`, generated frontend API types, fixture-heavy
frontend tests, and broad integration tests should be split only when a real
ownership or review problem appears.

## Milestone Map

The intended post-v14 refactor milestone order is:

1. v14 boundary refresh and characterization
2. lifecycle brief limitation and skipped-evidence cleanup
3. review response and fixup inventory decomposition
4. commit and handoff readiness signal cleanup
5. interactive terminal client decomposition
6. CLI and web transport cleanup
7. frontend changeset store and API cleanup
8. release-gate, docs, and validation closeout

Each phase below corresponds to one concrete refactor milestone.

## Task Graph

---

## Phase 90: V14 Boundary Refresh And Characterization

### GBX-R600: Define Post-V14 Refactor Boundary Map

- Status: `DONE`
- Dependencies: none
- Target files:
  - [refactor-boundaries.md](./refactor-boundaries.md)
  - [architecture.md](./architecture.md)
  - [refactor-v14.md](./refactor-v14.md)
  - [test_architecture_guardrails.py](../tests/unit/test_architecture_guardrails.py)
- Work:
  - document the intended post-v14 compatibility facades and helper owners
  - name `runtime/changeset_review_brief_sections.py`,
    `runtime/review_responses.py`, `runtime/handoff_readiness.py`,
    `runtime/commit_readiness.py`, and `cli/interactive_client.py` as the
    first post-v14 pressure points
  - name `cli/changeset_command_handlers.py`,
    `web/routes/changesets.py`, `web/changeset_api_builders.py`,
    `frontend/api/client.ts`, `frontend/stores/changeset-store-actions.ts`,
    and `scripts/v14_release_gate_helpers.py` as follow-on transport and
    release-gate pressure points
  - distinguish model-heavy public surfaces from mixed-responsibility modules
    that should be split
  - keep v14 skipped-evidence, advisory UX evidence, and publication-boundary
    non-goals explicit
- Deliverables:
  - documented boundary map for runtime, terminal, web, frontend, store, and
    release-gate surfaces
  - initial guardrail expectations for post-v14 pressure points where the
    intended owner modules are already clear
- Validation:
  - `uv run pytest tests/unit/test_architecture_guardrails.py`
  - `uv run pytest tests/unit/test_release_candidate_docs.py -q`

### GBX-R601: Characterize Current V14 Review-Loop Maturity Behavior

- Status: `DONE`
- Dependencies: GBX-R600
- Target files:
  - [test_review_briefs.py](../tests/unit/test_review_briefs.py)
  - [test_review_responses.py](../tests/unit/test_review_responses.py)
  - [test_commit_readiness.py](../tests/unit/test_commit_readiness.py)
  - [test_handoff_readiness.py](../tests/unit/test_handoff_readiness.py)
  - [test_cli_interactive_client.py](../tests/unit/test_cli_interactive_client.py)
  - [test_cli_tui_review_commands.py](../tests/integration/test_cli_tui_review_commands.py)
  - [test_cli_interactive_commands.py](../tests/integration/test_cli_interactive_commands.py)
  - [test_web_changeset_routes.py](../tests/integration/test_web_changeset_routes.py)
  - [changeset-console.test.tsx](../frontend/tests/changeset-console.test.tsx)
  - [operator-actions.component.test.tsx](../frontend/tests/operator-actions.component.test.tsx)
- Work:
  - identify highest-risk current behaviors before movement begins
  - add characterization coverage where moved behavior is not already asserted
  - prefer narrow tests around limitation overflow summaries, skipped evidence
    labels, response blockers, fixup inventory safe actions, handoff blockers,
    commit-readiness non-claims, dashboard action messages, and local versus
    daemon review action parity
  - explicitly record accepted behavior gaps that should not block
    refactor-only movement
- Deliverables:
  - current behavior coverage sufficient for runtime and terminal extraction
    tasks
  - accepted-gap list for behavior that is intentionally left unchanged during
    refactor-only work
- Validation:
  - `uv run pytest tests/unit/test_review_briefs.py`
  - `uv run pytest tests/unit/test_review_responses.py`
  - `uv run pytest tests/unit/test_commit_readiness.py tests/unit/test_handoff_readiness.py`
  - `uv run pytest tests/unit/test_cli_interactive_client.py`
  - `uv run pytest tests/integration/test_cli_tui_review_commands.py`
  - `uv run pytest tests/integration/test_cli_interactive_commands.py -k review`
  - `uv run pytest tests/integration/test_web_changeset_routes.py`
  - `pnpm --dir frontend test -- changeset-console.test.tsx operator-actions.component.test.tsx`

### GBX-R602: Add Post-V14 Facade Guardrails After First Extraction

- Status: `TODO`
- Dependencies: GBX-R610, GBX-R620, GBX-R640
- Target files:
  - [test_architecture_guardrails.py](../tests/unit/test_architecture_guardrails.py)
  - [refactor-boundaries.md](./refactor-boundaries.md)
- Work:
  - add facade line-count and import-prefix expectations only after helper
    modules exist
  - assert that post-v14 runtime, terminal, web, frontend, and release-gate
    facades delegate to intended owner modules
  - keep the guardrails narrow enough that they catch regression without
    freezing legitimate implementation detail
- Deliverables:
  - post-extraction architecture tests for the new v14 helper owners
- Validation:
  - `uv run pytest tests/unit/test_architecture_guardrails.py`

---

## Phase 91: Lifecycle Brief Limitation And Skipped-Evidence Cleanup

### GBX-R610: Extract Lifecycle Brief Limitation Collection And Summary

- Status: `DONE`
- Dependencies: GBX-R601
- Target files:
  - `src/glassbox/runtime/changeset_review_brief_sections.py`
  - `src/glassbox/runtime/changeset_review_brief_limitations.py`
  - `src/glassbox/runtime/review_briefs.py`
  - `tests/unit/test_review_briefs.py`
- Work:
  - move limitation collection, deduplication, priority ordering, overflow
    summary text, and `ReviewBriefLimitationSummary` construction out of
    `changeset_review_brief_sections.py`
  - preserve the current 20-item reviewer-safe artifact cap behavior
  - preserve priority for blockers, failed/stale verification, skipped live
    evidence, publication boundaries, and raw evidence non-claims
  - keep raw retained evidence authoritative and unmodified
- Deliverables:
  - focused lifecycle-limitation helper module with direct unit coverage
  - section assembly that consumes already-summarized limitation output
- Validation:
  - `uv run pytest tests/unit/test_review_briefs.py -k "limitation or lifecycle"`
  - `uv run ruff check src/glassbox/runtime/changeset_review_brief_sections.py src/glassbox/runtime/changeset_review_brief_limitations.py tests/unit/test_review_briefs.py`
  - `uv run ty check src/glassbox/runtime/changeset_review_brief_sections.py src/glassbox/runtime/changeset_review_brief_limitations.py`

### GBX-R611: Extract Review Brief Section Families

- Status: `DONE`
- Dependencies: GBX-R610
- Target files:
  - `src/glassbox/runtime/changeset_review_brief_sections.py`
  - `src/glassbox/runtime/changeset_review_brief_core_sections.py`
  - `src/glassbox/runtime/changeset_review_brief_review_sections.py`
  - `src/glassbox/runtime/changeset_review_brief_readiness.py`
  - `tests/unit/test_review_briefs.py`
- Work:
  - move change summary, inventory, provenance, topology, command evidence, and
    risk sections into a core section owner
  - move feedback, response, manual evidence, live evidence, stale
    verification, and publication-boundary sections into a review-loop section
    owner
  - move review-readiness state/reason derivation into a focused readiness
    helper
  - keep `changeset_review_brief_sections.py` as the assembly facade for the
    current `ChangesetReviewBriefService`
- Deliverables:
  - section families that can be reviewed without scanning all brief behavior
  - compatibility assembly function preserved
- Validation:
  - `uv run pytest tests/unit/test_review_briefs.py`
  - `uv run pytest tests/integration/test_cli_changeset_commands.py -k brief`
  - `uv run pytest tests/integration/test_web_changeset_routes.py -k brief`

### GBX-R612: Promote Skipped Evidence Recognition To A Shared Runtime Boundary

- Status: `DONE`
- Dependencies: GBX-R610
- Target files:
  - `src/glassbox/runtime/skipped_evidence.py`
  - `src/glassbox/runtime/browser_evidence.py`
  - `src/glassbox/runtime/accessibility_evidence.py`
  - `src/glassbox/runtime/changeset_review_brief_sections.py`
  - `src/glassbox/runtime/handoff_readiness.py`
  - `src/glassbox/runtime/changeset_verification_readiness.py`
  - `tests/unit/test_manual_evidence.py`
  - `tests/unit/test_review_briefs.py`
  - `tests/unit/test_handoff_readiness.py`
- Work:
  - keep skipped-evidence semantics in one runtime module
  - avoid re-parsing `capture state:` limitations in multiple runtime helpers
    when a typed helper can answer the question
  - preserve the current string-based persisted projection compatibility
  - keep skipped evidence as advisory and non-passing
- Deliverables:
  - one runtime owner for skipped live evidence labels, reasons, counts, and
    summaries
  - callers updated to use the shared helper without changing retained events
    or projections
- Validation:
  - `uv run pytest tests/unit/test_manual_evidence.py`
  - `uv run pytest tests/unit/test_review_briefs.py -k skipped`
  - `uv run pytest tests/unit/test_handoff_readiness.py -k skipped`
  - `uv run pytest tests/integration/test_web_changeset_routes.py -k evidence`

---

## Phase 92: Review Response And Fixup Inventory Decomposition

### GBX-R620: Split Review Response Models From Derivation

- Status: `DONE`
- Dependencies: GBX-R601
- Target files:
  - `src/glassbox/runtime/review_responses.py`
  - `src/glassbox/runtime/review_response_models.py`
  - `src/glassbox/runtime/review_response_status.py`
  - `tests/unit/test_review_responses.py`
- Work:
  - move `ReviewFixupInventoryStatus`, `ReviewFixupInventoryArtifact`,
    `ReviewFeedbackResponseStatus`, and `ChangesetReviewResponseSummary` into
    a model module
  - move response state, blocker, verification, and safe-action derivation into
    a status module
  - preserve public imports from `review_responses.py` through explicit
    re-exports
  - keep models free of service orchestration
- Deliverables:
  - model-only response module and derivation-only status module
  - compatibility imports preserved for runtime, CLI, web, tests, and existing
    callers
- Validation:
  - `uv run pytest tests/unit/test_review_responses.py`
  - `uv run pytest tests/unit/test_commit_readiness.py -k response`
  - `uv run pytest tests/unit/test_handoff_readiness.py -k response`

### GBX-R621: Extract Fixup Inventory Artifact And Path-Scope Helpers

- Status: `DONE`
- Dependencies: GBX-R620
- Target files:
  - `src/glassbox/runtime/review_responses.py`
  - `src/glassbox/runtime/review_fixup_artifacts.py`
  - `src/glassbox/runtime/review_fixup_paths.py`
  - `src/glassbox/runtime/review_fixup_actions.py`
  - `tests/unit/test_review_responses.py`
  - `tests/integration/test_review_response_fixup_inventory.py`
- Work:
  - move fixup inventory artifact construction and stable JSON serialization
    into a fixup artifact module
  - move feedback-scope path normalization, matching, and path-summary shaping
    into a path helper
  - keep `ReviewFeedbackFixupInventoryService` focused on service-level
    workspace reads, artifact persistence, and event emission
  - preserve summary-only, no-raw-diff, no-reviewer-acceptance non-claims
- Deliverables:
  - independently testable fixup artifact and path matching helpers
- Validation:
  - `uv run pytest tests/unit/test_review_responses.py -k fixup`
  - `uv run pytest tests/integration/test_review_response_fixup_inventory.py`
  - `uv run pytest tests/integration/test_cli_changeset_commands.py -k fixup`

### GBX-R622: Extract Review Response Summary Assembly

- Status: `DONE`
- Dependencies: GBX-R620, GBX-R621
- Target files:
  - `src/glassbox/runtime/review_responses.py`
  - `src/glassbox/runtime/review_response_summary.py`
  - `src/glassbox/runtime/changeset_detail.py`
  - `tests/unit/test_review_responses.py`
- Work:
  - move changeset-level response summary counting, blocker aggregation, and
    safe next action aggregation into a summary module
  - keep response-status derivation reusable by detail views, CLI, web,
    verification previews, handoff readiness, and commit readiness
  - preserve ordering and bounded item behavior
- Deliverables:
  - review response summary module that does not own fixup artifact creation
- Validation:
  - `uv run pytest tests/unit/test_review_responses.py`
  - `uv run pytest tests/integration/test_cli_changeset_commands.py -k "feedback or status"`
  - `uv run pytest tests/integration/test_web_changeset_routes.py -k feedback`

---

## Phase 93: Commit And Handoff Readiness Signal Cleanup

### GBX-R630: Extract Shared Readiness Signal Models And Aggregation Helpers

- Status: `DONE`
- Dependencies: GBX-R620
- Target files:
  - `src/glassbox/runtime/commit_readiness.py`
  - `src/glassbox/runtime/handoff_readiness.py`
  - `src/glassbox/runtime/review_readiness_signals.py`
  - `tests/unit/test_commit_readiness.py`
  - `tests/unit/test_handoff_readiness.py`
- Work:
  - extract shared signal concepts where commit and handoff readiness duplicate
    blocker, limitation, path, and safe-action patterns
  - keep public `CommitReadinessSignal` and `HandoffReadinessSignal` models
    stable unless callers are updated explicitly
  - preserve state vocabularies and response payloads
- Deliverables:
  - shared signal helper that reduces duplicated aggregation logic without
    merging distinct commit and handoff product semantics
- Validation:
  - `uv run pytest tests/unit/test_commit_readiness.py`
  - `uv run pytest tests/unit/test_handoff_readiness.py`
  - `uv run pytest tests/integration/test_cli_changeset_commands.py -k "commit or handoff"`

### GBX-R631: Split Commit Readiness Signal Families

- Status: `TODO`
- Dependencies: GBX-R630
- Target files:
  - `src/glassbox/runtime/commit_readiness.py`
  - `src/glassbox/runtime/commit_readiness_git.py`
  - `src/glassbox/runtime/commit_readiness_signals.py`
  - `tests/unit/test_commit_readiness.py`
- Work:
  - move git status/diff summary shaping into a git helper
  - move inventory, provenance, verification, review-loop, manual evidence,
    recorded readiness, path-risk, and accepted-risk signal builders into a
    signal helper
  - keep `ChangesetCommitReadinessService` and `derive_commit_readiness` as
    stable public entrypoints
  - preserve read-only no-staging/no-commit posture
- Deliverables:
  - commit readiness facade that reads as orchestration over focused signal
    helpers
- Validation:
  - `uv run pytest tests/unit/test_commit_readiness.py`
  - `uv run pytest tests/integration/test_cli_changeset_commands.py -k commit`

### GBX-R632: Split Handoff Readiness Signal Families

- Status: `TODO`
- Dependencies: GBX-R630
- Target files:
  - `src/glassbox/runtime/handoff_readiness.py`
  - `src/glassbox/runtime/handoff_readiness_signals.py`
  - `src/glassbox/runtime/handoff_readiness_evidence.py`
  - `tests/unit/test_handoff_readiness.py`
- Work:
  - move publication-boundary, provenance, inventory, review response,
    verification, brief, risk, manual evidence, prior readiness, and skipped
    evidence signal builders into a signal helper
  - move handoff evidence count shaping into an evidence helper
  - keep `ChangesetHandoffReadinessService`, `preview_handoff_readiness`, and
    `derive_handoff_readiness` as stable public entrypoints
  - preserve advisory local posture and no-publication non-claims
- Deliverables:
  - handoff readiness facade that reads as orchestration over focused signal
    and evidence helpers
- Validation:
  - `uv run pytest tests/unit/test_handoff_readiness.py`
  - `uv run pytest tests/integration/test_cli_changeset_commands.py -k handoff`
  - `uv run pytest tests/integration/test_web_changeset_routes.py -k handoff`

---

## Phase 94: Interactive Terminal Client Decomposition

### GBX-R640: Split Interactive Client Models, Protocols, And SSE Helpers

- Status: `TODO`
- Dependencies: GBX-R601
- Target files:
  - `src/glassbox/cli/interactive_client.py`
  - `src/glassbox/cli/interactive_client_models.py`
  - `src/glassbox/cli/interactive_client_sse.py`
  - `tests/unit/test_cli_interactive_client.py`
- Work:
  - move `InteractiveClientErrorKind`, `InteractiveClientError`,
    `ReviewLoopAction`, `ReviewLoopActionResult`,
    `InteractiveSessionSnapshot`, and `InteractiveSessionClient` into a models
    or contracts module
  - move SSE parsing and HTTP error normalization helpers into focused helpers
  - preserve imports from `interactive_client.py` through explicit re-exports
  - keep terminal clients runtime-agnostic at the protocol boundary
- Deliverables:
  - smaller interactive client facade and testable SSE/error helpers
- Validation:
  - `uv run pytest tests/unit/test_cli_interactive_client.py`
  - `uv run pytest tests/unit/test_cli_tui_commands.py`
  - `uv run ruff check src/glassbox/cli/interactive_client.py src/glassbox/cli/interactive_client_models.py src/glassbox/cli/interactive_client_sse.py`

### GBX-R641: Split Local And Daemon Interactive Client Implementations

- Status: `TODO`
- Dependencies: GBX-R640
- Target files:
  - `src/glassbox/cli/interactive_client.py`
  - `src/glassbox/cli/interactive_client_local.py`
  - `src/glassbox/cli/interactive_client_daemon.py`
  - `tests/unit/test_cli_interactive_client.py`
  - `tests/integration/test_cli_tui_review_commands.py`
- Work:
  - move `LocalInteractiveSessionClient` into a local client module
  - move `DaemonInteractiveSessionClient` into a daemon client module
  - keep daemon HTTP payload handling separate from local runtime service calls
  - preserve the current remote `/review fixup` unavailable behavior unless a
    later task explicitly changes parity
  - preserve public imports from `interactive_client.py`
- Deliverables:
  - local and daemon clients that can be reviewed independently
  - documented accepted gap for any behavior parity that remains intentionally
    unchanged
- Validation:
  - `uv run pytest tests/unit/test_cli_interactive_client.py`
  - `uv run pytest tests/integration/test_cli_tui_review_commands.py`
  - `uv run pytest tests/integration/test_cli_interactive_commands.py -k review`

### GBX-R642: Extract Interactive Review Action And Guidance Formatting

- Status: `TODO`
- Dependencies: GBX-R641
- Target files:
  - `src/glassbox/cli/interactive_client_local.py`
  - `src/glassbox/cli/interactive_client_daemon.py`
  - `src/glassbox/cli/interactive_review_actions.py`
  - `src/glassbox/cli/interactive_review_guidance.py`
  - `src/glassbox/cli/interactive_review_commands.py`
  - `src/glassbox/cli/tui/review_commands.py`
  - `tests/unit/test_cli_interactive_client.py`
  - `tests/integration/test_cli_interactive_commands.py`
- Work:
  - move review action result shaping into a review action helper where local
    and daemon clients can share terminal-friendly output semantics
  - move missing-fixup, stale-response, skipped-evidence, missing-brief, and
    handoff guidance copy into a shared guidance helper
  - update plain interactive and TUI helpers to consume the shared result shape
  - preserve operator-visible copy unless characterization requires exact
    updates
- Deliverables:
  - one terminal owner for review-loop evidence guidance
  - local and daemon clients that no longer duplicate skipped-evidence and
    missing-fixup counting logic
- Validation:
  - `uv run pytest tests/unit/test_cli_interactive_client.py`
  - `uv run pytest tests/unit/test_cli_tui_commands.py`
  - `uv run pytest tests/integration/test_cli_interactive_commands.py -k review`
  - `uv run pytest tests/integration/test_cli_tui_review_commands.py`

---

## Phase 95: CLI And Web Transport Cleanup

### GBX-R650: Split Changeset Command Handler Families

- Status: `TODO`
- Dependencies: GBX-R620, GBX-R632, GBX-R642
- Target files:
  - `src/glassbox/cli/changeset_command_handlers.py`
  - `src/glassbox/cli/changeset_command_lifecycle.py`
  - `src/glassbox/cli/changeset_command_feedback.py`
  - `src/glassbox/cli/changeset_command_evidence.py`
  - `src/glassbox/cli/changeset_command_readiness.py`
  - `src/glassbox/cli/changeset_command_payloads.py`
  - `src/glassbox/cli/changeset_command_formatters.py`
- Work:
  - keep `changeset_command_handlers.py` as the command-family dispatcher
  - move create, list, show, refresh, archive, brief, verification, feedback,
    evidence, handoff, commit-prep, adoption, and export handlers into
    workflow-family modules
  - keep payload and formatter helpers aligned with the same families where
    practical
  - preserve command names, aliases, arguments, JSON payloads, exit-code
    behavior, and command-guide expectations
- Deliverables:
  - changeset CLI handlers that can be reviewed by operator workflow family
- Validation:
  - `uv run pytest tests/integration/test_cli_changeset_commands.py`
  - `uv run pytest tests/unit/test_command_guide.py`
  - `uv run pytest tests/unit/test_release_candidate_docs.py -q`
  - `uv run glassbox command tree`

### GBX-R651: Extract Changeset Route Action Patterns

- Status: `TODO`
- Dependencies: GBX-R620, GBX-R632
- Target files:
  - `src/glassbox/web/routes/changesets.py`
  - `src/glassbox/web/routes/changeset_route_actions.py`
  - `src/glassbox/web/routes/changeset_route_feedback.py`
  - `src/glassbox/web/routes/changeset_route_services.py`
  - `tests/integration/test_web_changeset_routes.py`
- Work:
  - move repeated post-mutation detail reload, workspace-root lookup, service
    execution, and result-to-response patterns into route-local helpers
  - keep FastAPI decorators and endpoint declarations easy to scan
  - preserve response models, status codes, validation patterns, and route
    paths
- Deliverables:
  - route module that reads as transport declaration rather than repeated
    action orchestration
- Validation:
  - `uv run pytest tests/integration/test_web_changeset_routes.py`
  - `pnpm --dir frontend api:generate`
  - `git diff -- frontend/generated`

### GBX-R652: Split Changeset API Builder Families

- Status: `TODO`
- Dependencies: GBX-R620, GBX-R632, GBX-R651
- Target files:
  - `src/glassbox/web/changeset_api.py`
  - `src/glassbox/web/changeset_api_builders.py`
  - `src/glassbox/web/changeset_api_builders_detail.py`
  - `src/glassbox/web/changeset_api_builders_review.py`
  - `src/glassbox/web/changeset_api_builders_readiness.py`
  - `src/glassbox/web/changeset_api_models.py`
  - `src/glassbox/web/review_loop_api.py`
- Work:
  - keep `web/changeset_api.py` as a compatibility facade
  - move detail/inventory/verification builders into one owner
  - move feedback/manual evidence/response/fixup builders into one owner
  - move commit/handoff/readiness builders into one owner
  - avoid FastAPI imports in builder modules
  - preserve OpenAPI schema shape unless explicitly changed
- Deliverables:
  - transport builders split by response family while preserving facade imports
- Validation:
  - `uv run pytest tests/integration/test_web_changeset_routes.py`
  - `uv run pytest tests/integration/test_openapi_schema.py`
  - `pnpm --dir frontend api:generate`
  - `pnpm --dir frontend typecheck`

---

## Phase 96: Frontend Store And API Cleanup

### GBX-R660: Split Changeset Store Action Families

- Status: `TODO`
- Dependencies: GBX-R651
- Target files:
  - `frontend/stores/changeset-store.ts`
  - `frontend/stores/changeset-store-actions.ts`
  - `frontend/stores/changeset-store-loaders.ts`
  - `frontend/stores/changeset-store-review-actions.ts`
  - `frontend/stores/changeset-store-action-messages.ts`
  - `frontend/stores/changeset-store-selectors.ts`
  - `frontend/tests/dashboard-stores.test.ts`
  - `frontend/tests/changeset-console.test.tsx`
- Work:
  - keep `changeset-store.ts` as the public store factory facade
  - move detail reload bundles and branch-search adjacency into loader helpers
  - move review-loop actions into review action helpers
  - move user-facing action message formatting into a pure helper
  - preserve action states, request cancellation semantics, and dashboard-store
    compatibility exports
- Deliverables:
  - store action modules split by loading, mutation, and message concerns
- Validation:
  - `pnpm --dir frontend test -- dashboard-stores.test.ts changeset-console.test.tsx`
  - `pnpm --dir frontend typecheck`
  - `pnpm --dir frontend lint`

### GBX-R661: Extract Frontend Skipped-Evidence And Review-Posture Helpers

- Status: `TODO`
- Dependencies: GBX-R660
- Target files:
  - `frontend/components/console/changeset/evidence.tsx`
  - `frontend/components/console/changeset/feedback.tsx`
  - `frontend/components/console/changeset/handoff.tsx`
  - `frontend/components/console/changeset/review-posture.ts`
  - `frontend/components/console/changeset/format.ts`
  - `frontend/tests/changeset-console.test.tsx`
- Work:
  - move frontend skipped-evidence parsing, labels, and reason extraction into
    a pure helper
  - move response badge variants and handoff/evidence posture labels into
    review-posture helpers where they are shared
  - preserve current copy and visual states
  - keep transport out of components
- Deliverables:
  - one frontend owner for skipped evidence and review posture formatting
- Validation:
  - `pnpm --dir frontend test -- changeset-console.test.tsx`
  - `pnpm --dir frontend typecheck`
  - `pnpm --dir frontend lint`

### GBX-R662: Group Frontend API Client Endpoint Families

- Status: `TODO`
- Dependencies: GBX-R651
- Target files:
  - `frontend/api/client.ts`
  - `frontend/api/client-core.ts`
  - `frontend/api/client-sessions.ts`
  - `frontend/api/client-changesets.ts`
  - `frontend/api/client-tasks.ts`
  - `frontend/api/client-workspace.ts`
  - `frontend/tests/api-client.test.ts`
- Work:
  - keep `createGlassboxApiClient` as the public frontend API facade
  - move request helpers and error shaping into a core helper
  - group endpoint families into session, task, changeset/review-loop,
    branch-search, memory, repository-index, and background-job helper modules
  - preserve method names, request bodies, query shapes, error classes, and
    generated type imports
- Deliverables:
  - frontend API client facade that is easier to extend without moving
    transport into stores or components
- Validation:
  - `pnpm --dir frontend test -- api-client.test.ts dashboard-stores.test.ts`
  - `pnpm --dir frontend typecheck`
  - `pnpm --dir frontend lint`

---

## Phase 97: Release Gate, Docs, And Validation Closeout

### GBX-R670: Split V14 Release-Gate Helper Owners

- Status: `TODO`
- Dependencies: GBX-R600
- Target files:
  - `scripts/validate_v14_release_gate.py`
  - `scripts/v14_release_gate_helpers.py`
  - `scripts/v14_release_gate_stages.py`
  - `scripts/v14_release_gate_advisory.py`
  - `scripts/v14_release_gate_summary.py`
  - `tests/unit/test_v14_release_gate.py`
- Work:
  - move v14 deterministic stage construction into a stage helper
  - move advisory provider/dashboard/accessibility evidence rows into an
    advisory helper
  - move summary metadata, release-authority shaping, dry-run copy, and next
    action shaping into a summary helper
  - keep `scripts/validate_v14_release_gate.py` as the operator CLI entrypoint
  - preserve command-line behavior, evidence summary shape, default evidence
    paths, dry-run behavior, blocking versus advisory release authority, and
    installed-wheel smoke behavior
- Deliverables:
  - release-gate script that stays a clear operator entrypoint
  - helper coverage for v14-specific stage and summary shaping
- Validation:
  - `uv run pytest tests/unit/test_v14_release_gate.py`
  - `uv run python scripts/validate_v14_release_gate.py --dry-run`

### GBX-R671: Refresh Refactor Documentation And Package Metadata Expectations

- Status: `TODO`
- Dependencies: GBX-R602, GBX-R670
- Target files:
  - [README.md](../README.md)
  - [README.md](./README.md)
  - [architecture.md](./architecture.md)
  - [refactor-boundaries.md](./refactor-boundaries.md)
  - [refactor-v14.md](./refactor-v14.md)
  - `scripts/validate_package_contents.py`
  - `tests/unit/test_packaging_metadata.py`
  - `tests/unit/test_release_candidate_docs.py`
- Work:
  - link the post-v14 refactor roadmap from the root README and docs hub if
    the project wants the roadmap discoverable before execution
  - update architecture and refactor-boundary docs with completed helper owners
    as phases land
  - update package-content expectations only if new docs or helper scripts
    should ship in sdists
  - keep historical v1/v8/v10/v11/v13 refactor docs intact
- Deliverables:
  - docs hub and packaging expectations aligned with the new refactor roadmap
- Validation:
  - `uv run pytest tests/unit/test_release_candidate_docs.py -q`
  - `uv run pytest tests/unit/test_packaging_metadata.py`
  - `uv run python scripts/validate_package_contents.py`

### GBX-R672: Run Post-V14 Refactor Release Confidence Sweep

- Status: `TODO`
- Dependencies: all previous tasks
- Target files:
  - [refactor-v14.md](./refactor-v14.md)
  - [v14-release-candidate.md](./v14-release-candidate.md)
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
  - `uv run python scripts/validate_v14_release_gate.py --dry-run`

## Accepted Product Follow-Up Candidates

These findings are useful context for refactor planning, but they are not
refactor-only tasks unless a later roadmap explicitly chooses to change
behavior:

- decide whether daemon-backed `/review fixup FEEDBACK_ID` should call the
  existing web fixup route for parity with local interactive clients
  - GBX-R601 characterizes the current behavior: local interactive clients can
    record response-linked fixup inventory, while daemon-backed `/review fixup`
    returns a validation error pointing operators to
    `glassbox changeset feedback fixup FEEDBACK_ID --cwd .`
- decide whether the frontend should expose first-class browser/dashboard and
  accessibility skipped-evidence attachment forms, beyond the current manual
  evidence quick action and retained command examples
- decide whether lifecycle brief limitation summaries should gain new API
  fields or dashboard visual treatment beyond the current generated-brief
  action message and retained artifact contents
- decide whether response-linked fixup inventory should support a dashboard
  path picker instead of always defaulting to workspace-derived inventory
- decide whether advisory dashboard/accessibility evidence should become a
  fixture-backed deterministic check in a future milestone

Product follow-ups should preserve the v14 non-goals unless a future product
contract explicitly changes them.

## Accepted Compatibility Shims

The following facades are acceptable during this roadmap as long as they remain
thin and delegate to owned helpers after the relevant phase completes:

- `src/glassbox/runtime/changesets.py`: stable runtime import facade over
  changeset source, query, feedback, evidence, verification, command-evidence,
  lifecycle brief, handoff, and commit-readiness helpers.
- `src/glassbox/runtime/changeset_review_brief_sections.py`: lifecycle brief
  assembly facade over limitation, core-section, review-section, skipped
  evidence, and review-readiness helpers.
- `src/glassbox/runtime/review_responses.py`: compatibility facade over
  response models, fixup artifact helpers, path matching, response status, and
  summary assembly helpers.
- `src/glassbox/runtime/commit_readiness.py`: public commit-readiness facade
  over git, signal, and aggregation helpers.
- `src/glassbox/runtime/handoff_readiness.py`: public handoff-readiness facade
  over signal, evidence, and aggregation helpers.
- `src/glassbox/cli/interactive_client.py`: compatibility facade over
  interactive client models, local client, daemon client, SSE/error helpers,
  and review-guidance helpers.
- `src/glassbox/cli/changeset_commands.py`: scriptable command facade over
  changeset service wiring, command handlers, payload shaping, and formatting
  helpers.
- `src/glassbox/cli/changeset_command_handlers.py`: command-family dispatcher
  over lifecycle, feedback, evidence, readiness, adoption, export, and
  commit-preparation handlers.
- `src/glassbox/cli/parser_changesets.py`: parser entrypoint over changeset,
  feedback, evidence, review, handoff, and commit-preparation parser families.
- TUI and plain interactive review entrypoints: stable user-facing command
  surfaces over review-loop parsing, action routing, and guidance helpers.
- `src/glassbox/web/changeset_api.py`: response-model facade over focused web
  changeset/review-loop models and response builders.
- `src/glassbox/web/routes/changesets.py`: FastAPI declaration surface over
  route-local service factories, request coercion, workspace lookup, action
  helpers, and HTTP error helpers.
- `frontend/api/client.ts`: public frontend API client facade over domain
  endpoint helper families.
- `frontend/stores/changeset-store.ts`: store factory facade over changeset API
  actions, loaders, action messages, and selector helpers.
- `frontend/components/console/changeset-console.tsx`: dashboard entrypoint
  over focused changeset list, detail, feedback, evidence, verification,
  handoff, and commit-preparation sections.
- `scripts/validate_v14_release_gate.py`: operator entrypoint over v14 release
  gate stage, advisory evidence, and summary helpers.

Do not add new behavior to these facades once their helper owners exist. New
behavior should land in the focused owner module and be re-exported only when a
stable public import path requires it.
