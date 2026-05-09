# Glassbox v15 Tasks

For the docs hub and operator guides, start at [README.md](./README.md). This
file is the v15 task graph for evolving Glassbox repository intelligence after
the v14 review-loop maturity milestone.

## Purpose

This document defines Glassbox v15: repository intelligence v2.

It is written in the same execution style as [tasks-v1.md](./tasks-v1.md)
through [tasks-v14.md](./tasks-v14.md): explicit dependencies, small vertical
slices, concrete deliverables, and quality requirements attached directly to
the work.

The v8 milestone introduced auditable autonomy, workspace memory, repository
indexing, topology, branch search, and verification recommendations as local
runtime products. The v10 milestone made long-running work durable. The v12
through v14 milestones then turned local changes into reviewable changesets
with evidence-backed review, fixup, manual evidence, handoff, and maturity
surfaces.

The v15 goal is to make Glassbox less forgetful about the repository. Glassbox
should understand local repository structure, verification habits, command
recipes, ownership hints, generated outputs, policy-sensitive paths, package
boundaries, and confirmed conventions well enough to improve changesets, eval
recommendations, review briefs, handoff posture, and turn context without
becoming hidden memory or release authority.

The v15 work should optimize for nine outcomes:

- define a stronger repository intelligence contract that keeps local index
  data rebuildable, provenance-backed, freshness-aware, and advisory by default
- upgrade repository indexing from broad file discovery into richer local
  knowledge about source roots, tests, docs, packages, commands, owners,
  generated paths, dependency manifests, and release-sensitive surfaces
- improve path-to-verification recommendations so changed paths map to likely
  tests, eval cases, profiles, recipes, release gates, and stale-evidence risks
  with visible confidence and explanations
- connect confirmed workspace memory and learned command candidates to
  repository intelligence without silently trusting model claims or stale facts
- make repository intelligence freshness, drift, and missing-index posture
  visible in CLI, API, dashboard, changesets, and handoff summaries
- expose a useful dashboard repository intelligence console for repo maps,
  affected subsystem inspection, command recipes, verification recommendations,
  memory candidates, and "why this check" explanations
- feed bounded, provenance-labeled repository intelligence into turn context
  so the model receives useful orientation that operators can inspect and
  replay can fingerprint
- promote stable repository-intelligence behavior into deterministic replay,
  eval, package, and release-gate evidence
- preserve Glassbox's local-first, event-sourced, operator-controlled authority
  model while making repository-aware daily work feel substantially sharper

The v15 thesis is:

- repository intelligence is local evidence, not cloud indexing, hosted code
  search, or provider-side memory
- richer repo understanding should reduce rediscovery, not replace tools,
  tests, human review, or deterministic release gates
- recommendations are useful only when they name provenance, freshness,
  confidence, and limitations
- path-to-test, path-to-eval, path-to-owner, and path-to-command mappings should
  be explainable and reviewable
- confirmed workspace memory can improve repository intelligence, but candidates
  must remain review-gated and stale entries must stay out of prompt context
- topology, index, memory, command recipes, and eval recommendations should
  converge into one coherent local intelligence surface
- every new claim should still be backed by canonical events, managed
  artifacts, typed responses, deterministic index snapshots, or eval fixtures

## Current Baseline Before V15 Execution

Treat the following as the starting point for every task in this document:

- [v14-release-candidate.md](./v14-release-candidate.md) records the supported
  review-loop maturity operating model, evidence split, residual risks, and
  non-publication boundaries.
- [repository-intelligence-index.md](./repository-intelligence-index.md)
  documents the current deterministic local repository index posture.
- [workspace-topology.md](./workspace-topology.md) documents current local
  topology discovery, affected components, package manifests, source roots,
  test roots, and advisory freshness behavior.
- [workspace-memory.md](./workspace-memory.md) defines local workspace memory as
  event-sourced, review-gated, provenance-backed, and prompt-use-recorded.
- [runtime-context.md](./runtime-context.md) defines repository context,
  runtime notes, working-set context, artifact-backed context, provenance
  classes, operator inspection, replay fingerprints, and drift semantics.
- [replay-evals.md](./replay-evals.md) documents eval recommendations, impact
  rules, recipes, profile surfaces, and deterministic release signoff.
- [change-inventory.md](./change-inventory.md) and
  [changeset-verification-readiness.md](./changeset-verification-readiness.md)
  define current changed-path, provenance, risk, and verification-readiness
  evidence.
- The runtime already has a repository index builder and search facade under
  `src/glassbox/runtime/repository_index*.py`.
- The runtime already has workspace topology, eval recommendation, workspace
  memory capture, knowledge posture, changeset topology, and review brief
  surfaces.
- The dashboard already has knowledge/repository/autonomy console entry points,
  changeset topology surfaces, and workspace overview cues, but repository
  intelligence remains more fragmented than the review-loop surfaces.
- Repository intelligence remains advisory unless a deterministic eval, test,
  release gate, or explicit operator action records stronger evidence.

## V15 Repository Intelligence Findings

Treat these findings as evidence that should steer the first implementation
slices:

- The repository index is useful orientation, but it is not yet a rich local
  model of package boundaries, command recipes, owners, generated paths,
  source/test/doc roots, and release-sensitive surfaces.
- Topology, eval recommendation, changeset readiness, workspace memory,
  repository index, branch search, and dashboard knowledge surfaces each know
  part of the repository story, but operators do not yet get one coherent
  "why this path matters" view.
- Path-to-verification guidance is valuable but should become more confident,
  more explainable, and more closely tied to topology, recipes, eval metadata,
  successful command evidence, and stale evidence posture.
- Confirmed workspace memory should help repository intelligence remember local
  conventions and verified commands, but generated candidates must remain
  review-only and prompt use must be recorded.
- Stale repository intelligence can be worse than no intelligence if it is not
  visibly degraded in changesets, review briefs, eval recommendations, and
  dashboard views.
- The agent prompt should benefit from bounded repo intelligence, but the same
  source, freshness, and limitations should be inspectable from normal operator
  surfaces and replay artifacts.
- The next milestone should strengthen local recommendation quality before
  expanding into publication automation, hosted review, remote indexing, or
  cross-repository memory sync.

## Agent Execution Rules

These rules apply to every task in this file.

1. Respect dependency order. Do not start a task until its dependencies are
   complete unless the task explicitly says it can proceed in parallel.
2. Preserve the event-sourced source-of-truth rule. Repository intelligence
   snapshots, topology records, learned commands, memory confirmations,
   recommendation results, context-use records, and dashboard state must be
   canonical events, managed artifacts, or rebuildable derived state.
3. Preserve local-first operation. Do not introduce hosted code search, cloud
   indexing, remote workspaces, hosted review state, external vector stores, or
   provider-side memory as v15 release dependencies.
4. Preserve deterministic release blocking. Repository intelligence may improve
   recommendations and context, but release authority remains deterministic
   tests, replay, eval, package, migration, unit, integration, CLI, API,
   frontend, and release-gate evidence.
5. Treat repository intelligence as advisory unless a narrower task defines a
   deterministic fixture-backed contract and failure policy.
6. Keep provenance visible. Any repository intelligence that shapes a
   recommendation, changeset summary, review brief, handoff posture, dashboard
   cue, or model prompt must name source, freshness, confidence, and limitation
   information.
7. Keep memory review-gated. Do not persist model-suggested repository facts,
   commands, owners, or conventions as active workspace memory without explicit
   operator confirmation or an existing trusted event path.
8. Keep stale intelligence honest. Stale or missing indexes, topology,
   recipes, memory, dependency manifests, or command evidence should degrade
   confidence and name rebuild or inspection commands instead of silently
   producing optimistic recommendations.
9. Keep recommendations explainable. Path-to-test, path-to-eval, path-to-owner,
   path-to-command, and release-surface recommendations should include "why
   this" text grounded in repository-owned metadata or retained local evidence.
10. Keep terminal and dashboard roles coherent. The TUI remains the primary
    conversational surface; the dashboard should become the richer repository
    intelligence console and evidence explorer.
11. Avoid heavy or opaque semantic indexing in v15 unless a task defines
    bounded inputs, deterministic output, retention policy, freshness policy,
    performance budgets, and replay/eval implications.
12. Do not auto-stage, auto-commit, auto-push, auto-open pull requests,
    auto-merge, deploy, publish, or mutate repository history as part of
    repository intelligence work.
13. Every implementation task automatically includes:
    - automated tests for new or changed behavior
    - `ruff` formatting and lint compliance for touched Python code
    - `ty` typecheck compliance for touched Python code
    - focused `pytest` coverage for touched runtime, CLI, web, replay, eval,
      daemon, store, policy, task, verification, provider, branch-search,
      changeset, review, manual evidence, browser evidence, accessibility
      evidence, repository index, topology, workspace memory, and terminal
      behavior
    - frontend lint, typecheck, tests, and build when the task touches
      dashboard code, generated API types, packaged static assets, or route
      assumptions
    - documentation updates when operator-visible behavior, recommendation
      posture, evidence posture, release posture, policy behavior, memory
      behavior, context behavior, or public workflow claims change

## Completion Contract For Any Task

A task is complete only when all of the following are true:

- the implementation exists in the intended module boundary
- automated tests covering the changed behavior exist and pass
- lint, formatting, type checks, and focused tests pass for touched code
- frontend validation passes when dashboard, generated API types, TUI command
  surfaces, or packaged static assets are touched
- deterministic replay/eval behavior remains stable or intentional drift is
  documented through the eval refresh workflow
- public docs are accurate against command help, API behavior, package
  contents, and release posture
- repository intelligence claims are backed by deterministic local inputs,
  canonical events, managed artifacts, typed API responses, or eval fixtures
- new recommendations show provenance, freshness, confidence, limitations, and
  safe inspection commands
- stale or missing repository intelligence is visible rather than hidden
- no repository intelligence source materially affects model prompts without an
  inspectable context snapshot and replay fingerprint story
- memory-derived intelligence remains confirmed, active, and provenance-backed
  before it shapes recommendations or prompts
- reviewer-facing artifacts are redacted or explicitly documented as local-only
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
README.md
pyproject.toml
scripts/
docs/
    repository-intelligence-index.md
    workspace-topology.md
    workspace-memory.md
    runtime-context.md
    replay-evals.md
    change-inventory.md
    changeset-verification-readiness.md
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
    integration/
    unit/
evals/
    bundles/
    cases/
    coverage.json
    impact.json
    recipes.json
    profiles.json
```

## Recommended Validation Commands

Use focused validation while implementing each task. The default backend slice
should include:

```bash
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run pytest -m "not daemon and not subprocess and not timeout and not tui and not slow"
```

When a task touches repository index, topology, memory, context, eval
recommendations, or changesets, also run the focused tests for that surface:

```bash
uv run pytest tests/unit/test_repository_index.py
uv run pytest tests/unit/test_workspace_topology.py
uv run pytest tests/unit/test_workspace_memory_capture.py
uv run pytest tests/unit/test_context_builder.py tests/unit/test_llm_prompts.py
uv run pytest tests/unit/test_eval_recommendations.py
uv run pytest tests/unit/test_changeset_topology.py
uv run pytest tests/integration/test_web_repository_index_routes.py
```

When a task touches frontend repository intelligence surfaces, also run:

```bash
pnpm --dir frontend api:generate
pnpm --dir frontend format:check
pnpm --dir frontend lint
pnpm --dir frontend typecheck
pnpm --dir frontend test
pnpm --dir frontend build
```

When a task touches eval cases, profiles, impact rules, recipes, or release
gates, also run:

```bash
uv run glassbox eval audit --cwd .
uv run glassbox eval recommend src/glassbox/runtime/repository_index.py --cwd .
uv run glassbox eval run --profile release-candidate --cwd .
```

Once `GBX-1581` exists, use the v15 gate as the canonical full validation
command:

```bash
uv run python scripts/validate_v15_release_gate.py
```

## Task Graph

---

## Phase 150: Repository Intelligence V2 Contract And Baseline Audit

### GBX-1500: Define The v15 Repository Intelligence V2 Contract

- Status: `DONE`
- Depends on: `GBX-1463`
- Goal: publish the operator and contributor contract for repository
  intelligence v2 without expanding Glassbox into hosted code search, cloud
  indexing, or hidden memory
- Deliverables:
  - `docs/v15-repository-intelligence-contract.md`
  - contract sections for scope, vocabulary, supported workflow set, evidence
    expectations, advisory boundaries, release authority, safety rules, and
    non-goals
  - explicit mapping back to [v8-auditable-autonomy-contract.md](./v8-auditable-autonomy-contract.md),
    [repository-intelligence-index.md](./repository-intelligence-index.md),
    [workspace-topology.md](./workspace-topology.md),
    [workspace-memory.md](./workspace-memory.md), and
    [runtime-context.md](./runtime-context.md)
  - definition of repository intelligence sources, including index snapshots,
    topology snapshots, eval metadata, recipes, confirmed memory, command
    evidence, dependency manifests, docs, source roots, test roots, and release
    evidence
  - rule that repository intelligence is local, rebuildable, freshness-aware,
    provenance-backed, and advisory by default
- Implementation notes:
  - keep the contract operator-readable rather than turning it into internal
    engineering notes only
  - define "repository intelligence" broadly enough to include commands, docs,
    tests, topology, ownership hints, release posture, and memory, not just
    symbols
  - explicitly avoid remote indexing, vector-store authority, and provider-side
    memory
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_release_candidate_docs.py -q`
  - focused docs link review
- Done when:
  - contributors can read one contract and understand how v15 improves local
    repository awareness while preserving Glassbox authority boundaries

### GBX-1501: Audit Current Repository Intelligence Surfaces And Gaps

- Status: `DONE`
- Depends on: `GBX-1500`
- Goal: establish a source-linked baseline of current repository index,
  topology, eval recommendation, memory, changeset, dashboard, and context
  behavior before implementation begins
- Deliverables:
  - `docs/v15-repository-intelligence-audit.md`
  - audit of `runtime/repository_index*`, `runtime/workspace_topology.py`,
    `runtime/eval_recommendation*`, `runtime/workspace_memory*`,
    `runtime/changeset_topology.py`, `runtime/context_*`, store projections,
    web routes, CLI commands, and frontend knowledge/repository surfaces
  - inventory of current path-to-test, path-to-eval, recipe, topology, command,
    owner, package, dependency, generated-path, and policy-sensitive signals
  - explicit "fix now", "document only", "accepted risk", and "not v15"
    dispositions
- Implementation notes:
  - distinguish deterministic inputs from advisory or stale inputs
  - name which gaps need canonical events, which need managed artifacts, which
    need projections, which need CLI/API/dashboard surfaces, and which are only
    docs or eval metadata gaps
  - do not implement new repository intelligence in this task
- Tests and validation included in task:
  - docs review against current command help, API routes, frontend surfaces,
    eval metadata, and source modules
  - `uv run pytest tests/unit/test_release_candidate_docs.py -q`
- Done when:
  - v15 implementers know which existing surfaces to preserve, which to unify,
    and which gaps are in scope

### GBX-1502: Update Documentation Discovery For v15

- Status: `DONE`
- Depends on: `GBX-1500`, `GBX-1501`
- Goal: make the v15 plan, contract, audit, and later evidence docs
  discoverable from the documentation hub
- Deliverables:
  - docs hub update linking this task graph, v15 contract, and v15 audit
  - root README update if v15 becomes the active planning track
  - guide-map additions for repository index, topology, memory, eval
    recommendations, command recipes, repository intelligence console, and
    release evidence as they land
  - docs guardrails if existing release-candidate documentation tests need to
    recognize v15 docs
- Implementation notes:
  - keep task docs separate from operator guides
  - do not overpromise v15 outcomes before implementation tasks are complete
  - make the v15 discovery path clear for both operators and contributors
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_release_candidate_docs.py -q`
  - docs link review
- Done when:
  - a contributor can discover the v15 repository intelligence plan from the
    docs index without knowing this filename

---

## Phase 151: Repository Intelligence Snapshot Model And Index Builder V2

### GBX-1510: Define Repository Intelligence Snapshot Schema V2

- Status: `DONE`
- Depends on: `GBX-1501`
- Goal: define a typed snapshot model that unifies index entries, topology
  signals, command recipes, ownership hints, and freshness metadata without
  making projections authoritative
- Deliverables:
  - core or runtime models for repository intelligence snapshots, entries,
    source manifests, command recipes, ownership hints, package boundaries,
    source roots, test roots, doc roots, generated paths, policy-sensitive
    paths, and release-sensitive surfaces
  - schema versioning and compatibility rules for older index artifacts
  - source digest, builder version, freshness, limitation, and provenance fields
  - artifact contract documentation
- Implementation notes:
  - prefer one versioned managed artifact over several unrelated JSON files
    when a unified snapshot improves explainability
  - keep raw file contents and raw diffs out of repository intelligence
    artifacts by default
  - do not introduce hidden semantic embeddings or external indexes
  - keep older repository index readers compatible where practical
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_repository_index.py`
  - model serialization and compatibility tests
  - artifact redaction tests if new fields touch paths or command text
- Done when:
  - Glassbox has a typed repository intelligence snapshot shape that can carry
    richer local knowledge and degrade safely when absent

### GBX-1511: Upgrade Repository Discovery For Roots, Packages, And Generated Paths

- Status: `DONE`
- Depends on: `GBX-1510`
- Goal: make repository indexing detect high-signal local structure beyond
  top-level file discovery
- Deliverables:
  - deterministic discovery for source roots, test roots, docs roots, package
    manifests, frontend workspaces, Python package roots, static export roots,
    generated directories, cache directories, and build outputs
  - generated and ignored path classifiers reused by changeset inventory,
    topology, and eval recommendations
  - path normalization and redaction rules for workspace-relative paths
  - builder limits for large repositories
- Implementation notes:
  - reuse existing topology and repository index discovery helpers where
    possible
  - avoid crawling `node_modules`, `.venv`, `.git`, static build outputs, and
    managed `.glassbox` artifacts unless explicitly allowed
  - keep output deterministic for stable eval fixtures
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_repository_index.py tests/unit/test_workspace_topology.py`
  - large-repo and generated-path fixture tests
- Done when:
  - the index can describe the repository's local layout well enough for later
    verification and dashboard surfaces

### GBX-1512: Add Command Recipe And Toolchain Intelligence Extraction

- Status: `DONE`
- Depends on: `GBX-1511`
- Goal: derive local command recipes and toolchain posture from repository-owned
  files and retained successful command evidence
- Deliverables:
  - extraction of command recipes from `pyproject.toml`, package manifests,
    eval profiles, eval recipes, docs examples, release scripts, and confirmed
    workspace memory
  - typed command recipe records with purpose, scope, risk, source, confidence,
    freshness, timeout hints, and review relevance
  - policy-sensitive and release-sensitive command classification
  - docs explaining how command recipes differ from permission grants
- Implementation notes:
  - command recipes are recommendations, not automatically approved commands
  - hard tool-policy invariants and workspace policy rules still apply
  - dedupe equivalent commands and keep source references so operators can see
    why a recipe exists
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_repository_index.py tests/unit/test_eval_recommendations.py`
  - policy tests if command classification affects policy evidence
- Done when:
  - repository intelligence can name likely local commands with provenance and
    confidence without executing or approving them

### GBX-1513: Add Ownership, Subsystem, And Release-Surface Hint Extraction

- Status: `DONE`
- Depends on: `GBX-1511`
- Goal: extract explainable ownership and subsystem hints that improve
  changesets, review briefs, eval recommendations, and dashboard inspection
- Deliverables:
  - ownership hint extraction from local docs, path conventions, optional
    CODEOWNERS-like files, package manifests, eval metadata, and topology
  - subsystem records for runtime, store, web, CLI, frontend, evals, docs,
    release scripts, packaging, policy, provider, memory, topology, and review
    loop surfaces
  - release-surface hints for commit-time, push-time, release-candidate, and
    advisory checks
  - confidence and limitation fields for inferred hints
- Implementation notes:
  - keep ownership hints advisory and local; do not imply access control or
    reviewer assignment authority
  - prefer explicit repository-owned metadata over broad naming heuristics
  - surface weak confidence instead of suppressing uncertain hints entirely
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_repository_index.py tests/unit/test_eval_recommendations.py tests/unit/test_changeset_topology.py`
- Done when:
  - changed paths can be tied to local subsystems, owners, and release surfaces
    with honest confidence and limitations

### GBX-1514: Persist And Inspect Repository Intelligence Snapshots

- Status: `DONE`
- Depends on: `GBX-1512`, `GBX-1513`
- Goal: persist richer repository intelligence as managed local evidence and
  expose status through CLI and API
- Deliverables:
  - builder command or repository command update for rebuilding v2 snapshots
  - persisted managed artifact under the existing `.glassbox` state boundary
  - CLI status, rebuild, inspect, and JSON output for snapshot freshness,
    source digest, entry counts, command recipes, subsystems, owners, and
    limitations
  - API route updates for repository intelligence status and search
  - backward-compatible behavior when only the older repository index exists
- Implementation notes:
  - do not store secrets, raw command logs, raw file contents, or raw diffs in
    the snapshot
  - keep rebuild explicit unless a later task defines a safe background refresh
  - make missing and stale snapshots useful states, not hard failures
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_repository_index.py`
  - `uv run pytest tests/integration/test_cli_repository_commands.py`
  - `uv run pytest tests/integration/test_web_repository_index_routes.py`
  - `uv run pytest tests/integration/test_artifact_store.py`
- Done when:
  - operators and dashboard clients can inspect the richer repository
    intelligence snapshot without reading implementation files

---

## Phase 152: Path-To-Verification Intelligence

### GBX-1520: Define Path-To-Verification Recommendation Contract

- Status: `DONE`
- Depends on: `GBX-1514`
- Goal: define how changed paths map to tests, evals, recipes, release gates,
  stale-evidence risks, and confidence explanations
- Deliverables:
  - documentation for recommendation inputs, outputs, confidence levels,
    provenance, freshness, limitations, and non-claims
  - typed runtime models for path impact, verification targets, command
    recipes, eval cases, eval profiles, skipped checks, and stale evidence
  - clear distinction between executable deterministic checks, advisory
    commands, live-provider canaries, browser/accessibility evidence, and
    manual evidence
- Implementation notes:
  - build on existing eval recommendation terminology instead of creating a
    parallel vocabulary
  - recommendations should start with the cheapest useful deterministic check
    when one exists
  - live provider, browser, dashboard, accessibility, and dogfooding evidence
    remain advisory unless explicitly promoted
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_eval_recommendations.py`
  - docs guardrails if new contract docs are added
- Done when:
  - implementers have one contract for "why this test/eval/command was
    recommended for these paths"

### GBX-1521: Improve Test Target Discovery From Repository Intelligence

- Status: `DONE`
- Depends on: `GBX-1520`
- Goal: use repository intelligence to recommend likely test targets for
  changed paths with confidence and explanation
- Deliverables:
  - path-to-test mapping from source roots, test roots, package boundaries,
    naming conventions, topology, and existing test discovery tools
  - confidence levels such as direct, topology-derived, naming-derived,
    package-derived, recipe-derived, and fallback
  - stale topology and missing test-root degradation behavior
  - CLI and JSON output through existing eval or repo recommendation commands
- Implementation notes:
  - do not execute tests in this task unless an existing command explicitly
    requests execution
  - preserve existing test discovery tool behavior and enrich it rather than
    replacing it wholesale
  - keep recommendation result ordering deterministic
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_eval_recommendations.py tests/unit/test_tools_read_only.py`
  - focused fixture tests for Python, frontend, docs-only, generated, and
    release-script changes
- Done when:
  - Glassbox can explain likely test targets for common changed-path families
    without relying only on broad smoke profiles

### GBX-1522: Improve Eval Case, Profile, And Recipe Recommendations

- Status: `DONE`
- Depends on: `GBX-1521`
- Goal: connect repository intelligence to eval metadata so recommendations
  are more precise and easier to review
- Deliverables:
  - use repository intelligence subsystems, owners, capabilities, release
    surfaces, and command recipes inside `eval recommend`
  - recommendation rows that name matched paths, source metadata, confidence,
    profile budget implications, stale intelligence posture, and safe next
    commands
  - fallback behavior when repository intelligence is missing or stale
  - updated `evals/impact.json`, `evals/recipes.json`, and `evals/coverage.json`
    only when needed
- Implementation notes:
  - repository intelligence should improve existing repository-owned eval
    metadata, not override it silently
  - keep live-provider canary profiles skipped from executable plans unless
    explicitly requested
  - ensure deterministic report output remains stable for tests
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_eval_recommendations.py tests/unit/test_runtime_eval_coverage.py`
  - `uv run glassbox eval recommend src/glassbox/runtime/repository_index.py --cwd .`
  - `uv run glassbox eval audit --cwd .`
- Done when:
  - recommendation output can say which repository intelligence source changed
    the recommended eval scope and why

### GBX-1523: Add Stale Evidence And Verification Drift Risk Recommendations

- Status: `DONE`
- Depends on: `GBX-1522`
- Goal: use repository intelligence to detect when changed paths make retained
  verification, review evidence, or topology-derived checks stale
- Deliverables:
  - runtime helper that compares changed paths against retained verification
    evidence, changeset inventories, command evidence, topology snapshots, and
    repository intelligence digests
  - recommendation rows for stale verification, missing verification, stale
    topology, stale command recipes, stale memory, and stale index state
  - changeset verification readiness integration
  - docs update for stale-intelligence interpretation
- Implementation notes:
  - stale evidence is a warning or blocker depending on existing readiness
    rules; do not invent a pass/fail state without a contract
  - avoid making `.glassbox` artifact churn mark source evidence stale
  - name rebuild, refresh, or verification commands as safe next actions
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_changeset_verification_readiness.py tests/unit/test_verification_drift.py`
  - `uv run pytest tests/integration/test_changeset_derivation.py`
- Done when:
  - operators can see when repository-aware evidence is stale before trusting a
    recommendation or review brief

### GBX-1524: Surface Path-To-Verification In Changesets And Review Briefs

- Status: `DONE`
- Depends on: `GBX-1523`
- Goal: make improved verification recommendations visible where operators
  review local changes
- Deliverables:
  - changeset detail fields for recommended tests, evals, recipes, release
    surfaces, stale evidence, confidence, and limitations
  - lifecycle brief section for repository-intelligence verification guidance
  - CLI output updates for `changeset show`, `changeset verification-plan`, and
    handoff readiness where appropriate
  - reviewer-safe export support
- Implementation notes:
  - keep recommendations advisory unless existing readiness rules mark a
    verification gap as blocking
  - do not include raw command output or raw file content in reviewer-safe
    briefs
  - preserve v14 non-publication language
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_review_briefs.py tests/unit/test_handoff_readiness.py`
  - `uv run pytest tests/integration/test_cli_changeset_commands.py`
  - `uv run pytest tests/integration/test_web_changeset_routes.py`
- Done when:
  - a changeset review can answer "what should I run and why?" using local
    repository intelligence

---

## Phase 153: Workspace Memory And Learned Repository Knowledge

### GBX-1530: Define Memory-To-Repository-Intelligence Contract

- Status: `DONE`
- Depends on: `GBX-1500`, `GBX-1514`
- Goal: define how confirmed workspace memory, candidate memory, and command
  evidence may influence repository intelligence
- Deliverables:
  - docs contract for confirmed repository facts, conventions, command recipes,
    failure patterns, owner hints, package quirks, and task outcomes
  - distinction between active memory, stale memory, invalidated memory,
    imported memory, rejected candidates, and prompt-use records
  - rules for when memory can shape recommendations, snapshots, dashboard cues,
    and model context
  - non-goals for automatic memory capture and cross-repository sync
- Implementation notes:
  - reuse [workspace-memory.md](./workspace-memory.md) vocabulary and avoid a
    parallel memory system
  - keep model-assisted memory suggestions review-only
  - memory-derived intelligence must remain traceable back to memory IDs and
    source events
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_workspace_memory_capture.py`
  - docs link review
- Done when:
  - implementers know exactly how confirmed local memory may enrich repository
    intelligence without becoming hidden memory

### GBX-1531: Generate Repository Intelligence Memory Candidates

- Status: `DONE`
- Depends on: `GBX-1530`
- Goal: propose review-only memory candidates from successful commands,
  repeated failures, verified recipes, topology findings, and release outcomes
- Deliverables:
  - candidate extractors for successful verification commands, repeated
    failure/recovery patterns, stable command recipes, package conventions,
    generated-output conventions, and release-sensitive path notes
  - candidate provenance linking back to command evidence, task outcomes,
    changesets, eval recommendations, topology snapshots, or repository
    intelligence artifacts
  - redaction and dedupe rules
  - CLI/API output for reviewing candidates
- Implementation notes:
  - do not auto-confirm candidates
  - reject stale or low-confidence candidates early unless explicitly requested
  - keep candidate summaries concise and operator-editable
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_workspace_memory_capture.py tests/unit/test_command_evidence.py`
  - integration tests for memory candidate listing if CLI/API changes
- Done when:
  - Glassbox can suggest useful repo-specific facts and commands while keeping
    operator confirmation in control

### GBX-1532: Use Confirmed Memory In Repository Intelligence Snapshots

- Status: `DONE`
- Depends on: `GBX-1531`
- Goal: incorporate confirmed active workspace memory into repository
  intelligence snapshots and recommendations with provenance and freshness
- Deliverables:
  - snapshot entries derived from confirmed active memory for command recipes,
    conventions, failure patterns, architecture notes, owner hints, and task
    outcomes
  - exclusion behavior for stale, invalidated, imported-unreviewed, rejected,
    and pruned memory
  - recommendation explanations that reference memory IDs and source labels
  - memory-use records when memory-derived repository intelligence shapes turn
    context
- Implementation notes:
  - memory can enrich recommendations, but it does not override stronger
    deterministic source metadata without saying so
  - do not embed sensitive memory content in reviewer-safe artifacts unless
    redaction rules allow it
  - preserve replay drift reporting for memory-derived context
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_workspace_memory_capture.py tests/unit/test_repository_index.py`
  - `uv run pytest tests/unit/test_context_builder.py tests/unit/test_replay_orchestrator.py`
- Done when:
  - confirmed local memory improves repository intelligence and every influence
    is attributable

### GBX-1533: Add Memory Freshness And Conflict Detection For Repository Facts

- Status: `DONE`
- Depends on: `GBX-1532`
- Goal: detect when remembered repository facts conflict with current
  repository structure, command outcomes, dependency manifests, or topology
- Deliverables:
  - stale-memory heuristics for missing paths, renamed roots, changed manifests,
    failing remembered commands, superseded generated paths, and changed release
    surfaces
  - conflict records or advisory cues surfaced in memory and repository
    intelligence views
  - safe next actions for confirming, updating, invalidating, or pruning memory
  - tests for stale and conflicting memory edge cases
- Implementation notes:
  - avoid automatic invalidation unless a task defines a safe event path
  - prefer surfacing conflict candidates with source evidence and suggested
    commands
  - keep stale memory out of prompts by default
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_workspace_memory_capture.py tests/unit/test_knowledge_posture.py`
  - dashboard tests if conflict cues are displayed
- Done when:
  - repository intelligence can warn operators before stale memory misleads
    recommendations or prompts

---

## Phase 154: Repository Intelligence Freshness, Drift, And Background Refresh

### GBX-1540: Define Freshness And Drift Model For Repository Intelligence

- Status: `DONE`
- Depends on: `GBX-1514`, `GBX-1533`
- Goal: define how Glassbox reports fresh, stale, missing, degraded,
  conflicting, and partially rebuilt repository intelligence
- Deliverables:
  - typed freshness states and drift reasons for repository intelligence
    snapshots, topology, command recipes, dependency manifests, memory-derived
    entries, eval metadata, and release-surface metadata
  - CLI/API/dashboard copy for each state
  - rebuild and inspection guidance for degraded states
  - docs update explaining which stale states are blockers, warnings, or
    advisory cues
- Implementation notes:
  - stale intelligence should not fail unrelated commands by default
  - readiness and review flows may treat stale intelligence as blocking only
    when existing verification or handoff contracts require it
  - keep freshness calculations deterministic and cheap
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_repository_index.py tests/unit/test_workspace_topology.py tests/unit/test_knowledge_posture.py`
- Done when:
  - all repository intelligence consumers can show the same freshness language
    instead of inventing local status labels

### GBX-1541: Add Repository Intelligence Health And Observability Surfaces

- Status: `DONE`
- Depends on: `GBX-1540`
- Goal: make repository intelligence health visible in status, observability,
  readiness, API, and dashboard aggregate views
- Deliverables:
  - observability report rows for index freshness, topology freshness, command
    recipe posture, memory conflict posture, eval metadata freshness, and
    rebuild guidance
  - `glassbox readiness check` and `glassbox observability status` updates
  - session aggregate or workspace overview fields for repository intelligence
    posture
  - generated API and frontend type updates if response models change
- Implementation notes:
  - avoid making first-run readiness fail hard because optional repository
    intelligence is absent
  - prefer remediation commands and confidence labels over alarmist warnings
  - keep `.glassbox` local state paths out of reviewer-safe summaries unless
    needed for operator action
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_first_run_readiness.py tests/integration/test_observability_status.py`
  - `uv run pytest tests/integration/test_web_session_aggregate.py`
  - frontend tests when workspace overview changes
- Done when:
  - operators can tell whether repository intelligence is healthy before
    trusting recommendations

### GBX-1542: Add Safe Background Refresh Jobs For Derived Intelligence

- Status: `DONE`
- Depends on: `GBX-1541`
- Goal: let the daemon refresh derived repository intelligence without creating
  a second mutation authority or hiding work from operators
- Deliverables:
  - background job type for repository intelligence refresh
  - queued, claimed, running, completed, failed, cancelled, and stale behavior
    using existing background job events
  - progress messages and retained summary artifacts
  - CLI and dashboard controls for enqueueing or inspecting refresh jobs
- Implementation notes:
  - this job may write managed `.glassbox` intelligence artifacts, but must not
    mutate source files, stage, commit, push, or edit policy files
  - use existing daemon job lease, cancellation, retry, stale-owner, and
    observability behavior
  - keep explicit rebuild commands available for non-daemon workflows
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_background_job_runner.py tests/integration/test_background_jobs.py`
  - `uv run pytest tests/integration/test_cli_repository_commands.py`
  - web/frontend tests if dashboard controls are added
- Done when:
  - derived repository intelligence can be refreshed by the daemon with
    inspectable job evidence and no hidden source mutation

### GBX-1543: Add Projection Rebuild And Backup Awareness For Intelligence Artifacts

- Status: `DONE`
- Depends on: `GBX-1542`
- Goal: make repository intelligence artifacts behave correctly under
  projection rebuild, backup, restore, artifact inspection, and package smoke
- Deliverables:
  - artifact retention and inspection support for repository intelligence
    snapshots
  - backup/restore handling for managed intelligence artifacts
  - projection-health behavior when intelligence-derived projections are
    missing or stale
  - package-content validation if new files must ship
- Implementation notes:
  - keep intelligence artifacts rebuildable; backup improves convenience but
    should not be the only recovery path
  - avoid pruning active snapshots required for current freshness reports
  - document artifact size and retention limits
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_artifact_store.py tests/integration/test_artifact_gc.py tests/integration/test_workspace_backup.py`
  - `uv run python scripts/validate_package_contents.py`
- Done when:
  - repository intelligence survives normal Glassbox maintenance workflows or
    can be safely rebuilt with clear guidance

---

## Phase 155: Repository Intelligence CLI, API, And Dashboard Console

### GBX-1550: Add Repository Intelligence CLI Workflows

- Status: `DONE`
- Depends on: `GBX-1541`
- Goal: make repository intelligence inspectable and useful from scriptable
  terminal commands
- Deliverables:
  - CLI commands for status, rebuild, inspect path, recommend verification,
    list command recipes, show subsystem, show stale intelligence, and list
    memory candidates where appropriate
  - human-readable and JSON output for each command
  - command-guide updates for ordinary repository intelligence workflows
  - safe next actions for stale or missing intelligence
- Implementation notes:
  - extend the existing `glassbox repo` command family where possible
  - keep commands useful in CI and clean shell environments
  - do not require an active session for repository-level inspection
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_cli_repository_commands.py`
  - `uv run pytest tests/unit/test_command_guide.py`
  - `uv run glassbox command guide`
- Done when:
  - an operator can understand and refresh repository intelligence without
    opening the dashboard

### GBX-1551: Add Repository Intelligence API And Generated Types

- Status: `DONE`
- Depends on: `GBX-1550`
- Goal: expose repository intelligence through typed web APIs without forcing
  the frontend to derive meaning from raw artifacts
- Deliverables:
  - routes for status, path inspection, subsystem detail, command recipes,
    verification recommendations, memory candidates, freshness, and search
  - response models that wrap runtime query services rather than duplicating
    business logic in route handlers
  - OpenAPI schema and generated frontend type updates
  - pagination for large recipe, entry, and search results
- Implementation notes:
  - keep route modules focused on HTTP validation and error mapping
  - preserve existing repository index route compatibility
  - avoid returning raw artifact blobs unless a dedicated download endpoint is
    already appropriate
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_web_repository_index_routes.py tests/integration/test_openapi_schema.py`
  - `pnpm --dir frontend api:generate`
  - `pnpm --dir frontend typecheck`
- Done when:
  - the dashboard can consume repository intelligence through stable generated
    types

### GBX-1552: Build Repository Intelligence Dashboard Console

- Status: `DONE`
- Depends on: `GBX-1551`
- Goal: give operators a focused dashboard surface for local repository
  intelligence
- Deliverables:
  - repository map summary with freshness, source roots, test roots, docs,
    packages, subsystems, generated paths, and release-sensitive areas
  - path inspector showing affected subsystem, likely tests, evals, command
    recipes, owner hints, stale evidence, and limitations
  - command recipe browser with purpose, risk, source, confidence, and safe
    copyable commands
  - memory candidate and confirmed-memory panels for repository facts
  - degraded and missing-intelligence states
- Implementation notes:
  - build inside the existing operator console design language
  - keep dense, work-focused layout; avoid marketing or explanatory panels
  - no nested cards; use existing data-list and table components where they fit
  - ensure long paths and command strings wrap or truncate professionally
- Tests and validation included in task:
  - `pnpm --dir frontend test -- knowledge-autonomy-console.test.tsx workspace-overview.test.tsx`
  - `pnpm --dir frontend lint`
  - `pnpm --dir frontend typecheck`
  - `pnpm --dir frontend build`
- Done when:
  - dashboard users can inspect repository intelligence and understand why
    recommendations were made

### GBX-1553: Connect Repository Intelligence To Changeset Dashboard Surfaces

- Status: `DONE`
- Depends on: `GBX-1524`, `GBX-1552`
- Goal: make changeset review surfaces use repository intelligence without
  burying operators in duplicate panels
- Deliverables:
  - changeset detail sections for affected subsystems, recommended
    verification, stale intelligence, command recipes, and owner hints
  - feedback and fixup status rows that reference path-to-verification
    intelligence when relevant
  - route deep links from changeset paths to repository path inspector
  - responsive and keyboard checks for the changed controls
- Implementation notes:
  - keep repository intelligence advisory beside deterministic verification
    posture
  - avoid treating owner hints as reviewer assignment or approval authority
  - preserve v14 skipped evidence and publication-boundary language
- Tests and validation included in task:
  - `pnpm --dir frontend test -- changeset-console.test.tsx verification-cues.test.ts`
  - `uv run pytest tests/integration/test_web_changeset_routes.py`
  - `pnpm --dir frontend typecheck`
- Done when:
  - changeset reviewers can move from "what changed" to "what does this affect
    and what should I run" without leaving the review surface

### GBX-1554: Add Repository Intelligence Accessibility And Browser Evidence

- Status: `DONE`
- Depends on: `GBX-1552`, `GBX-1553`
- Goal: collect bounded advisory UX evidence for the repository intelligence
  console and changed changeset surfaces
- Deliverables:
  - browser walkthrough evidence for repository map, path inspector, command
    recipes, stale-intelligence states, and changeset links
  - accessibility pairing notes for keyboard focus, focus-visible state,
    responsive layout, long-path wrapping, and skipped assistive-technology
    checks
  - docs or dogfooding summary updates with retained limitations and non-claims
- Implementation notes:
  - advisory evidence remains non-blocking unless a deterministic fixture is
    promoted
  - do not claim accessibility certification or full WCAG conformance
  - file follow-up tasks for any material usability issue
- Tests and validation included in task:
  - frontend tests for changed surfaces
  - targeted Playwright or manual browser evidence per existing advisory
    protocols
- Done when:
  - the new repository intelligence dashboard surfaces have fresh advisory UX
    evidence or explicit retained skips with bounded reasons

---

## Phase 156: Repository Intelligence In Turn Context And Replay

### GBX-1560: Define Repository Intelligence Context Contract

- Status: `DONE`
- Depends on: `GBX-1540`
- Goal: define how bounded repository intelligence may shape model turns while
  remaining inspectable and replay-aware
- Deliverables:
  - context contract for repo-intelligence prompt fragments, included sources,
    freshness, confidence, limitations, budgets, and excluded stale sources
  - replay fingerprint rules for repository intelligence context
  - operator inspection fields for CLI status and session snapshots
  - non-goals for hidden retrieval, raw prompt dumps as the only inspection
    path, and provider-side memory
- Implementation notes:
  - keep repository intelligence separate from repository context, runtime
    notes, working set, artifact-backed context, and workspace memory prompt
    fragments
  - include only bounded summaries, never raw index artifacts or raw file
    contents
  - stale intelligence should be excluded or visibly degraded according to the
    contract
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_context_builder.py tests/unit/test_llm_prompts.py`
  - replay manifest tests if fingerprint models change
- Done when:
  - the model can receive useful repository intelligence only through a
    documented, inspectable, replay-aware source

### GBX-1561: Integrate Bounded Repository Intelligence Into Turn Context

- Status: `DONE`
- Depends on: `GBX-1560`
- Goal: add repository intelligence summaries to live turn preparation under
  explicit budgets and provenance rules
- Deliverables:
  - runtime context derivation for repository intelligence summaries
  - prompt fragment with affected subsystems, relevant command recipes, likely
    tests, confirmed conventions, stale exclusions, and limitations
  - CLI status and dashboard snapshot fields for the same bounded summary
  - configuration or budget guardrails for maximum items and bytes
- Implementation notes:
  - do not force every turn to rebuild repository intelligence
  - degrade gracefully when the snapshot is missing, stale, too large, or
    unavailable
  - record context-use evidence when confirmed memory-derived intelligence is
    included
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_context_builder.py tests/unit/test_llm_prompts.py`
  - `uv run pytest tests/integration/test_web_session_snapshot.py`
  - frontend tests if runtime-context panes change
- Done when:
  - live turns can use bounded repository intelligence and operators can see
    exactly what was included

### GBX-1562: Add Replay, Eval, And Drift Semantics For Repository Intelligence Context

- Status: `DONE`
- Depends on: `GBX-1561`
- Goal: make repository intelligence context changes visible in replay and eval
  results
- Deliverables:
  - replay artifacts and manifests for repository intelligence context sources
  - per-source fingerprints for index snapshot, topology, memory-derived
    intelligence, command recipes, and path-to-verification recommendations
  - drift messages that name the exact repository intelligence source that
    changed
  - selected-invariant behavior for cases where repository intelligence should
    be ignored or relaxed
- Implementation notes:
  - keep older replay bundles compatible when repository intelligence context is
    absent
  - do not report vague aggregate drift when source-level drift is known
  - make missing or stale intelligence an explainable manifest difference
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_replay_orchestrator.py tests/unit/test_replay_triage.py`
  - `uv run pytest tests/integration/test_replay_runner.py`
  - selected eval fixture tests if new cases are added
- Done when:
  - replay can distinguish behavior drift from repository intelligence context
    drift

### GBX-1563: Add Repository Intelligence Eval Fixtures

- Status: `TODO`
- Depends on: `GBX-1562`
- Goal: promote stable repository intelligence behavior into deterministic
  eval coverage
- Deliverables:
  - compact eval cases for repository index snapshot behavior, path-to-test
    recommendations, stale topology degradation, command recipe explanation,
    and repository intelligence context drift
  - `evals/coverage.json`, `evals/impact.json`, `evals/recipes.json`, and
    profile updates where appropriate
  - baseline review artifacts for intentional drift
- Implementation notes:
  - keep cases deterministic and small
  - do not encode live browser, provider, or manual UX evidence as release
    blockers
  - use selected invariants when exact transcript output is not the contract
- Tests and validation included in task:
  - `uv run glassbox eval run NEW_CASE_ID --cwd .`
  - `uv run glassbox eval audit --cwd .`
  - `uv run pytest tests/unit/test_runtime_eval_coverage.py`
- Done when:
  - repository intelligence regressions are visible through repository-owned
    deterministic eval evidence

---

## Phase 157: Performance, Scale, And Packaging

### GBX-1570: Add Repository Intelligence Performance Budgets

- Status: `TODO`
- Depends on: `GBX-1514`, `GBX-1542`
- Goal: prevent repository intelligence from making large local repositories
  slow or memory-heavy
- Deliverables:
  - performance budgets for indexing, path inspection, recommendation
    generation, snapshot serialization, API responses, and dashboard rendering
  - large-repository fixtures or synthetic tests
  - truncation and partial-result behavior with visible limitations
  - docs update for large-repo behavior
- Implementation notes:
  - prefer bounded deterministic scans over hidden background crawling
  - make limits configurable only where the operator can understand the tradeoff
  - avoid loading full artifacts or raw file contents into dashboard responses
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_performance_budgets.py`
  - focused large-session or large-repository tests
  - frontend performance-sensitive component tests if needed
- Done when:
  - v15 intelligence remains usable on large repositories and degrades
    explicitly under limits

### GBX-1571: Harden Repository Intelligence Error Paths

- Status: `TODO`
- Depends on: `GBX-1570`
- Goal: make indexing and recommendation failures recoverable and easy to
  diagnose
- Deliverables:
  - failure classification for missing manifests, unreadable files, invalid
    config, oversized repositories, stale artifacts, corrupted snapshots, and
    unsupported schema versions
  - CLI/API/dashboard error copy with safe next actions
  - observability and readiness integration
  - tests for corrupted and missing repository intelligence artifacts
- Implementation notes:
  - broken repository intelligence should not corrupt sessions or prevent
    basic chat unless the user explicitly requested intelligence-dependent
    work
  - preserve old snapshot compatibility or emit a clear migration/rebuild
    action
  - retain bounded error artifacts when useful for debugging
- Tests and validation included in task:
  - `uv run pytest tests/integration/test_failure_recovery.py tests/integration/test_web_repository_index_routes.py`
  - `uv run pytest tests/unit/test_repository_index.py`
- Done when:
  - repository intelligence failures produce actionable recovery guidance
    rather than vague runtime errors

### GBX-1572: Package Repository Intelligence Assets And Smoke Paths

- Status: `TODO`
- Depends on: `GBX-1571`
- Goal: ensure repository intelligence commands, schemas, docs, eval fixtures,
  generated frontend types, and static dashboard assets ship cleanly
- Deliverables:
  - package content validation for new scripts, docs, eval metadata, generated
    API types, and static assets
  - installed-wheel smoke coverage for repository intelligence commands
  - frontend release asset validation if dashboard routes change
  - docs update for source checkout and installed-package behavior
- Implementation notes:
  - installed-package users should not need Node.js to inspect packaged
    repository intelligence dashboard assets
  - do not package local `.glassbox` intelligence artifacts
  - keep generated API files fresh before release
- Tests and validation included in task:
  - `uv run python scripts/validate_package_contents.py`
  - `uv run python scripts/validate_frontend_release_assets.py`
  - `uv run pytest tests/unit/test_installed_wheel_smoke.py`
  - `uv run pytest tests/unit/test_packaging_metadata.py`
- Done when:
  - repository intelligence v2 works from both source checkout and installed
    package paths

---

## Phase 158: V15 Eval, Gate, Dogfooding, And Release Signoff

### GBX-1580: Add Deterministic V15 Repository Intelligence Eval Cases

- Status: `TODO`
- Depends on: `GBX-1563`, `GBX-1572`
- Goal: ensure the stable repository intelligence v2 behaviors participate in
  deterministic release evidence
- Deliverables:
  - eval cases for rich repository snapshot generation, path-to-verification
    recommendation, stale intelligence degradation, memory-derived command
    recommendation, and repository intelligence context drift
  - coverage manifest updates for v15 repository intelligence capabilities
  - release-candidate profile membership and budget review
  - recommendation tests for changed repository intelligence paths
- Implementation notes:
  - promote only stable deterministic behavior into blocking profiles
  - keep advisory dashboard/browser/accessibility evidence separate
  - document any intentional baseline refreshes
- Tests and validation included in task:
  - `uv run glassbox eval run --profile release-candidate --cwd .`
  - `uv run glassbox eval audit --profile release-candidate --cwd .`
  - `uv run pytest tests/unit/test_runtime_eval_coverage.py`
- Done when:
  - release reviewers can see deterministic eval coverage for the core v15
    repository intelligence contract

### GBX-1581: Add V15 Release Gate

- Status: `TODO`
- Depends on: `GBX-1580`
- Goal: collect v15 repository intelligence evidence in one automated release
  gate while keeping advisory evidence boundaries clear
- Deliverables:
  - `scripts/validate_v15_release_gate.py`
  - blocking stages for deterministic v15 evals, repository index/topology
    tests, CLI/API tests, frontend tests, generated API types, package
    contents, installed smoke, and release docs
  - advisory rows for dashboard browser evidence, accessibility evidence,
    provider canary posture, and dogfooding evidence
  - summary JSON with blocking and advisory sections
  - dry-run support and unit tests for stage construction
- Implementation notes:
  - reuse v14 release-gate helpers when practical instead of duplicating the
    inherited gate stack
  - do not make live provider, browser, or accessibility evidence blocking
    unless a deterministic fixture-backed contract exists
  - keep evidence directory paths local and reviewer-safe
- Tests and validation included in task:
  - `uv run pytest tests/unit/test_v15_release_gate.py`
  - `uv run python scripts/validate_v15_release_gate.py --dry-run`
  - package-content validation if new scripts must ship
- Done when:
  - one command reports v15 repository intelligence release readiness with
    deterministic and advisory sections clearly separated

### GBX-1582: Run V15 Repository Intelligence Dogfooding

- Status: `TODO`
- Depends on: `GBX-1581`
- Goal: use repository intelligence v2 on realistic local work and record
  friction before release signoff
- Deliverables:
  - retained local evidence under `.glassbox/releases/`
  - `docs/v15-dogfooding-summary.md`
  - dogfooding passes for repository snapshot rebuild, path inspection,
    verification recommendation, memory candidate review, changeset review,
    dashboard console, stale intelligence recovery, and turn-context inspection
  - dispositions for fixes, docs, tests/evals, accepted risks, and post-v15
    follow-ups
- Implementation notes:
  - dogfood against this repository and at least one smaller fixture or
    intentionally constrained workspace when practical
  - do not expand scope during dogfooding; file follow-up tasks instead
  - keep raw `.glassbox` state local and summarize only reviewer-safe evidence
- Tests and validation included in task:
  - focused tests for any dogfooding fix
  - v15 release gate dry run after dogfooding fixes
  - docs validation for the summary
- Done when:
  - v15 repository intelligence has been exercised against realistic local work
    and the findings are triaged

### GBX-1583: Publish V15 Repository Intelligence Release-Candidate Guide

- Status: `TODO`
- Depends on: `GBX-1582`
- Goal: publish the operator-facing v15 repository intelligence guide and final
  milestone decision
- Deliverables:
  - `docs/v15-release-candidate.md`
  - guide covering supported operating model, validation path, evidence
    expectations, advisory evidence, residual risks, deliberate non-goals,
    release decision, and related files
  - docs hub and root README updates if v15 becomes the active implementation
    track
  - retained release evidence under `.glassbox/releases/`
- Implementation notes:
  - name remaining non-goals and known residual risks clearly
  - avoid overclaiming repository understanding, test selection, owner hints,
    release readiness, provider reliability, accessibility coverage, browser
    evidence, automatic git mutation, or automatic PR behavior
  - keep package version policy aligned with
    [version-release-policy.md](./version-release-policy.md)
- Tests and validation included in task:
  - `uv run python scripts/validate_v15_release_gate.py`
  - `uv run pytest tests/unit/test_release_candidate_docs.py -q`
  - final docs link review
  - package contents validation if release docs are packaged
- Done when:
  - the v15 release candidate has a coherent guide, retained evidence, accepted
    residual-risk list, and explicit GO/NO-GO decision

## V15 Release-Candidate Readiness Checklist

Before treating a build as the v15 release candidate, complete this list:

- The v15 repository intelligence contract and audit are published and linked
  from the docs hub.
- Repository intelligence snapshot v2 is versioned, local, rebuildable,
  provenance-backed, and freshness-aware.
- Repository discovery identifies source roots, test roots, docs roots,
  package boundaries, generated paths, dependency manifests, and
  release-sensitive surfaces with deterministic limits.
- Command recipes are extracted or learned with source, risk, purpose,
  confidence, and safe command guidance.
- Ownership and subsystem hints are surfaced as advisory local evidence, not
  access control or reviewer assignment authority.
- Path-to-verification recommendations name likely tests, evals, profiles,
  recipes, release gates, stale evidence, confidence, and limitations.
- Changesets and review briefs show repository-intelligence verification
  guidance without replacing deterministic verification posture.
- Confirmed active workspace memory can enrich repository intelligence, while
  stale, invalidated, imported-unreviewed, rejected, and pruned memory is
  excluded from prompt use by default.
- Repository intelligence freshness, drift, missing-index, and conflict states
  are visible in CLI, API, dashboard, readiness, and observability surfaces.
- Safe background refresh jobs can rebuild derived intelligence without
  mutating source files or creating a second workspace mutation owner.
- The dashboard repository intelligence console exposes repo map, path
  inspector, command recipes, memory candidates, stale states, and "why this
  check" explanations.
- Repository intelligence context is bounded, provenance-labeled, inspectable,
  and replay-fingerprinted.
- Deterministic v15 eval cases and coverage mappings pass in the selected
  release-candidate profile.
- The v15 release gate passes and writes retained `summary.json` with blocking
  and advisory sections.
- Dogfooding findings have dispositions as fixes, docs, tests/evals, accepted
  risks, or post-v15 follow-ups.
- Raw `.glassbox` state is not committed; reviewer-safe summaries are used for
  handoff and release review.

## Deliberate V15 Non-Goals

v15 deliberately does not introduce:

- hosted code search
- hosted repository indexing
- external vector-store authority
- provider-side hidden memory
- cloud workspace authority
- remote worker fleets
- hosted code review
- hosted review comment synchronization
- cross-repository memory sync
- automatic owner assignment
- automatic review approval
- automatic staging
- automatic commits
- automatic pushes
- automatic pull request creation
- automatic branch-search merging
- automatic rebase, force-push, or history rewriting
- automatic deploys or package publishing
- automatic provider failover as release authority
- accessibility certification or broad WCAG conformance claims
- hidden semantic indexing that cannot be inspected, rebuilt, bounded, or
  replay-fingerprinted
- indefinite unattended autonomy

These may be revisited in future milestones only with a new product contract,
safety model, evidence policy, remote-collaboration model, and explicit
operator semantics.
