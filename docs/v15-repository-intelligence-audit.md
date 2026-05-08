# V15 Repository Intelligence Audit

This source-linked audit records the current Glassbox repository intelligence
surface before v15 implementation work begins. It is evidence for
`GBX-1501` in [tasks-v15.md](./tasks-v15.md) and should be read beside the
[v15 repository intelligence contract](./v15-repository-intelligence-contract.md).

The audit intentionally does not implement new repository intelligence. It
classifies the existing repository index, topology, eval recommendation,
workspace memory, changeset, frontend knowledge/repository surfaces, CLI/API,
store, and context surfaces so
later v15 tasks can preserve current behavior while closing specific gaps.

## Summary

Glassbox already has a local repository intelligence baseline:

- `runtime/repository_index*` builds a bounded local index with file, module,
  symbol, command, dependency, test, docs, and eval entries, then persists it
  under `.glassbox` as a managed JSON artifact.
- `runtime/workspace_topology.py` models packages, apps, docs, tests, tooling,
  generated outputs, manifests, dependency edges, freshness, provenance, and
  limitations.
- `runtime/eval_recommendation*` maps changed paths to eval cases, profiles,
  release surfaces, long-run surfaces, recipe recommendations, and
  topology-derived verification commands.
- `runtime/workspace_memory*` keeps memory review-gated through candidates,
  confirmation, rejection, invalidation, pruning, redaction, and active-memory
  prompt selection.
- `runtime/context_*` can include fresh repository index entries and confirmed
  active memory in bounded turn context, with stale index items omitted.
- CLI, web routes, and dashboard routes expose index and memory inspection, plus
  topology status and detail through web APIs.

The main v15 gap is coherence. Each surface knows part of the repository story,
but operators do not yet get one shared "why this path matters" view with
source, freshness, confidence, limitations, command recipes, owner hints,
package boundaries, generated-path posture, policy-sensitive surfaces, release
surfaces, memory influence, and stale-evidence risk in one contract-backed
shape.

## Classification Legend

| Disposition | Meaning |
| --- | --- |
| Fix now | In scope for v15 implementation because the gap blocks the richer repository intelligence contract. |
| Document only | Current behavior is acceptable for now, but the limitation should stay visible. |
| Accepted risk | Known limitation that should remain bounded for v15 unless dogfooding proves it blocks normal work. |
| Not v15 | Explicitly outside this milestone's local-first, advisory, deterministic-release boundary. |

## Audit Entries

### Repository Index Builder And Search

**Current behavior.** The index facade builds a deterministic snapshot from
bounded indexable files, source-input digests, file entries, command entries,
and dependency entries (`src/glassbox/runtime/repository_index.py:28`). File
discovery skips `.git`, `.glassbox`, caches, virtual environments, build
outputs, frontend dependency folders, and static export roots with a
`MAX_INDEXED_FILES` cap of 2000
(`src/glassbox/runtime/repository_index_discovery.py:7`). Extraction creates
project marker, docs, eval, source file, module, symbol, test, command, and
dependency-hint entries with provenance
(`src/glassbox/runtime/repository_index_extraction.py:16`,
`src/glassbox/runtime/repository_index_extraction.py:38`,
`src/glassbox/runtime/repository_index_extraction.py:63`,
`src/glassbox/runtime/repository_index_extraction.py:96`).

**Signals present.** Path inventory, source digest, excluded names, command
strings from `frontend/package.json`, Python tool-command hints from
`pyproject.toml`, dependency names from package manifests, source/test/docs/eval
entry kinds, simple Python and TypeScript symbol names, and stable entry IDs.

**Gaps.** The builder version is still `v1`; source manifests, package
boundaries, command recipe purpose/risk/scope, ownership hints, generated-path
classifiers, policy-sensitive paths, release-sensitive surfaces, and stale
dependency-manifest reasons are not unified in one v2 snapshot. The scanner is
deterministic but broad, and it reads lightweight source symbols rather than
structured package semantics.

**Disposition.** Fix now through `GBX-1510` through `GBX-1514`.

### Repository Index Freshness And Observability

**Current behavior.** Repository index status compares the retained source
digest to current bounded source inputs, reports missing/stale/failed states,
includes path samples for added, removed, and changed source inputs when
available, and names safe next actions
(`src/glassbox/runtime/repository_index_status.py:57`,
`src/glassbox/runtime/repository_index_status.py:114`,
`src/glassbox/runtime/repository_index_status.py:146`).

**Signals present.** Snapshot status, retained and current source digest,
source file counts, bounded source diff samples, failure reason, and rebuild or
inspection commands.

**Gaps.** Freshness vocabulary is index-specific and not yet shared with
topology, command recipes, memory-derived entries, eval metadata, changesets,
dashboard aggregate health, or handoff readiness.

**Disposition.** Fix now in the v15 freshness and health tasks (`GBX-1540` and
`GBX-1541`).

### Workspace Topology

**Current behavior.** Workspace topology has typed components for workspace,
package, app, library, docs, tests, tooling, and generated areas; typed
dependency edges; manifest, lockfile, root, generated-output, ownership-hint,
tag, provenance, freshness, limitation, and failure fields
(`src/glassbox/runtime/workspace_topology.py:32`,
`src/glassbox/runtime/workspace_topology.py:71`,
`src/glassbox/runtime/workspace_topology.py:118`,
`src/glassbox/runtime/workspace_topology.py:198`). Consumers can classify
fresh topology as normal guidance, stale topology as degraded, and failed or
missing topology as unavailable
(`src/glassbox/runtime/workspace_topology.py:249`).

**Signals present.** Source roots, test roots, docs roots, generated output
roots, manifests, lockfiles, package manager, ecosystem, ownership hints,
dependency edges, source digest, freshness, and limitations.

**Gaps.** Topology has richer structure than the repository index, but it is a
separate snapshot and not yet represented as one repository intelligence v2
artifact. Ownership hints are data fields, not robust extraction outcomes.
Generated paths are component roots, not reusable classifiers shared by
changeset inventory and eval recommendations.

**Disposition.** Fix now in `GBX-1510`, `GBX-1511`, and `GBX-1513`.

### Eval Recommendation Engine

**Current behavior.** Eval recommendation normalizes changed paths, loads eval
cases, profiles, coverage, impact rules, recipes, and topology-derived recipe
recommendations, then returns recommended cases, profiles, release surfaces,
long-run surfaces, reason groups, suggested commands, cheapest next command,
and fallback policy commands
(`src/glassbox/runtime/eval_recommendation_engine.py:58`,
`src/glassbox/runtime/eval_recommendation_engine.py:91`,
`src/glassbox/runtime/eval_recommendation_engine.py:184`,
`src/glassbox/runtime/eval_recommendation_engine.py:188`,
`src/glassbox/runtime/eval_recommendation_engine.py:197`).

**Signals present.** `evals/impact.json` has path globs, owners, capabilities,
case IDs, profile IDs, and notes for runtime context, memory, repository index,
topology, changesets, review loop, dashboard, store, provider, and release
surfaces (`evals/impact.json:198`, `evals/impact.json:256`). `evals/recipes.json`
has docs-only, release-docs, frontend-dashboard, changeset-runtime,
review-loop-evidence, changeset-surfaces, workspace-topology, packaging, and
other command recipes with path globs and commands (`evals/recipes.json:5`,
`evals/recipes.json:49`, `evals/recipes.json:72`,
`evals/recipes.json:201`). `evals/coverage.json` tracks repository-index
context drift as advisory release evidence (`evals/coverage.json:189`).

**Gaps.** Recommendations do not yet consume one repository intelligence v2
snapshot for subsystems, owners, command recipe posture, stale evidence,
policy-sensitive paths, generated paths, or memory-derived repository facts.
Path-to-test confidence levels remain scattered across topology recipes,
impact rules, and broad fallback profiles.

**Disposition.** Fix now in `GBX-1520` through `GBX-1524`.

### Topology-Derived Verification Recipes

**Current behavior.** Topology-derived recommendations load the retained
topology, degrade when stale, skip when missing or unavailable, match changed
paths to components, and produce docs, Node, or Python command suggestions with
matched paths, component IDs, confidence, source, notes, and limitations
(`src/glassbox/runtime/eval_recommendation_topology.py:16`,
`src/glassbox/runtime/eval_recommendation_topology.py:30`,
`src/glassbox/runtime/eval_recommendation_topology.py:91`,
`src/glassbox/runtime/eval_recommendation_topology.py:167`).

**Signals present.** Component roots, manifests, lockfiles, docs roots, test
roots, package manager, ecosystem, direct changed test paths, related Python
test naming, and component-level fallback guidance.

**Gaps.** This is the strongest existing path-to-test bridge, but it is still
topology-only. It does not yet attach release-surface hints, stale retained
verification, command evidence freshness, owner hints, policy-sensitive path
rules, or confirmed-memory explanations in the same recommendation row.

**Disposition.** Fix now in `GBX-1521`, `GBX-1522`, and `GBX-1523`.

### Workspace Memory

**Current behavior.** Memory candidates are generated from runtime notes, task
outcomes, stable commands, repeated failures, confirmed fixes, long-run
checkpoints, compactions, verification records, and optional model suggestions,
then deduped, filtered for usefulness, and filtered by age
(`src/glassbox/runtime/workspace_memory_capture.py:79`,
`src/glassbox/runtime/workspace_memory_capture.py:94`,
`src/glassbox/runtime/workspace_memory_candidates.py:50`,
`src/glassbox/runtime/workspace_memory_candidates.py:62`). Model-assisted
suggestions are review-only and never become memory until confirmed
(`src/glassbox/runtime/workspace_memory_capture.py:123`). Confirmation,
merge, rejection, operator-added memory, invalidation, and pruning are
event-backed through the capture service and store projections
(`src/glassbox/runtime/workspace_memory_capture.py:148`,
`src/glassbox/store/sqlite_projection_workspace_memory.py:17`).

**Signals present.** Candidate IDs, kinds, content, summaries, provenance,
tags, redaction, source labels, creation time, active/imported/invalidated/
pruned states, confirmation metadata, invalidation reason, use count, and
prompt-use events.

**Gaps.** Confirmed memory is available to context, but repository
intelligence snapshots do not yet incorporate confirmed memory as command
recipes, conventions, failure patterns, architecture notes, owner hints, or
task outcomes. Conflict detection between remembered repository facts and
current manifests/topology is not yet present.

**Disposition.** Fix now in `GBX-1530` through `GBX-1533`.

### Runtime Context And Prompt Use

**Current behavior.** Runtime context derives repository context, working set,
artifact-backed context, confirmed workspace memory, repository index context,
checkpoint resume context, and compaction context in one shared snapshot
(`src/glassbox/runtime/runtime_context_derivation.py:23`). Fresh repository
index entries can be selected for context with item and byte budgets; stale or
non-fresh snapshots omit items and retain a detail string
(`src/glassbox/runtime/context_snapshots.py:175`). Turn context includes only a
fresh repository index fragment in the prompt and keeps repository index,
workspace memory, checkpoint, artifact, and compaction snapshots inspectable
(`src/glassbox/runtime/context_builder.py:104`).

**Signals present.** Repository top-level context, high-signal paths, active
confirmed memory, repository index freshness, selected index item IDs,
provenance, source type, byte count, and additional item counts.

**Gaps.** Prompt context has repository index orientation, not a v15
repository-intelligence summary with affected subsystems, likely tests, command
recipes, stale exclusions, confirmed conventions, and replay fingerprints for
each source class.

**Disposition.** Fix now in `GBX-1560` through `GBX-1562`.

### Changeset Topology And Review Surfaces

**Current behavior.** Changeset topology impact derives affected components
from retained topology, reports matched paths, test roots, ownership hints,
dependency hints, topology freshness, recommendation posture, and limitations,
and degrades when topology is stale
(`src/glassbox/runtime/changeset_topology.py:17`,
`src/glassbox/runtime/changeset_topology.py:35`). Existing changeset docs,
runtime, store, CLI, API, and dashboard surfaces carry review-loop evidence,
stale verification posture, manual evidence, browser/accessibility evidence,
fixup inventory, handoff readiness, and publication-boundary language.

**Signals present.** Changed paths, component matches, test roots, owner hints,
dependency hints, topology freshness, review-loop impact rules, changeset
verification readiness, command evidence, lifecycle brief limitations, and
handoff posture.

**Gaps.** Changesets do not yet show unified v15 path-to-verification guidance
with recommended tests, evals, command recipes, release surfaces,
stale-evidence risks, confidence labels, memory-derived explanations, and
reviewer-safe export support in one detail field.

**Disposition.** Fix now in `GBX-1524` and `GBX-1553`.

### CLI Commands

**Current behavior.** `glassbox repo` exposes `index build`, `index status`,
`index search`, `index show`, `topology build`, `topology status`, and
`topology show` with JSON output options where relevant
(`src/glassbox/cli/parser_repository.py:9`,
`src/glassbox/cli/repository_commands.py:29`). Index build can queue a
background derived-index job when anchored to a session, or build
synchronously; topology build is synchronous
(`src/glassbox/cli/repository_commands.py:62`,
`src/glassbox/cli/repository_commands.py:121`).

**Signals present.** Scriptable status, rebuild, search, show, missing-state
guidance, background index refresh queueing, and topology status/detail output.

**Gaps.** CLI does not yet have v15 workflows for inspect path, recommend
verification, list command recipes, show subsystem, show stale intelligence,
list memory candidates from repository-intelligence extraction, or explain
"why this check" from one service.

**Disposition.** Fix now in `GBX-1550`.

### Web API Routes And Types

**Current behavior.** FastAPI routes expose repository index status, search,
entry detail, rebuild, topology status, topology detail, and topology rebuild
(`src/glassbox/web/repository_index_routes.py:39`,
`src/glassbox/web/repository_index_routes.py:43`,
`src/glassbox/web/repository_index_routes.py:63`,
`src/glassbox/web/repository_index_routes.py:115`,
`src/glassbox/web/repository_index_routes.py:160`). HTTP response models
serialize index entries, provenance, topology components, manifests,
dependencies, status, detail, and rebuild responses
(`src/glassbox/web/repository_index_api.py:20`,
`src/glassbox/web/repository_index_api.py:44`,
`src/glassbox/web/repository_index_api.py:97`,
`src/glassbox/web/repository_index_api.py:127`).

**Signals present.** Index status/search/detail/rebuild, topology
status/detail/rebuild, provenance, pagination shell for search, background-job
response, and generated frontend API consumption.

**Gaps.** API responses still expose index and topology separately. They do
not yet expose v15 status, path inspection, subsystem detail, command recipes,
verification recommendations, memory candidates, freshness rollups, search
over richer snapshot entries, or stale-evidence risk through stable generated
types.

**Disposition.** Fix now in `GBX-1551`.

### Dashboard Knowledge And Repository Surfaces

**Current behavior.** The knowledge autonomy console includes a repository
index inspector with status, entry count, build time, source digest,
non-fresh-state warning copy, rebuild action, search, table rows, selected
entry detail, and provenance display
(`frontend/components/console/knowledge-autonomy/repository.tsx:23`,
`frontend/components/console/knowledge-autonomy/repository.tsx:39`,
`frontend/components/console/knowledge-autonomy/repository.tsx:91`,
`frontend/components/console/knowledge-autonomy/repository.tsx:186`). The
knowledge store loads repository status, rebuilds the index, searches entries,
and loads entry details through generated API clients
(`frontend/stores/knowledge-store.ts:49`,
`frontend/stores/knowledge-store.ts:161`,
`frontend/stores/knowledge-store.ts:210`,
`frontend/stores/knowledge-store.ts:240`,
`frontend/stores/knowledge-store.ts:297`).

**Signals present.** Status, digest, rebuild, search, detail, provenance,
loading/error states, selected entry, and memory inspection in the adjacent
knowledge surface.

**Gaps.** There is no dedicated v15 repository intelligence console with repo
map, roots, packages, generated paths, release-sensitive areas, path
inspector, command recipe browser, memory candidate panel, stale-intelligence
explainer, or changeset deep links.

**Disposition.** Fix now in `GBX-1552` through `GBX-1554`.

### Store And Projection Boundaries

**Current behavior.** Workspace memory is event-sourced and projected through
SQLite (`src/glassbox/store/sqlite_projection_workspace_memory.py:17`).
Repository index and topology snapshots are managed artifacts under
`.glassbox`, not canonical event payloads. Background derived-index jobs are
queued through the session repository when requested from CLI or API
(`src/glassbox/cli/repository_commands.py:67`,
`src/glassbox/web/repository_index_routes.py:129`).

**Signals present.** Canonical memory events, projected memory state, managed
index artifacts, managed topology artifacts, background job records, and
artifact paths.

**Gaps.** Repository intelligence v2 does not yet have one managed artifact
contract with backup/restore, projection-health, artifact retention, package
content, corrupted-snapshot recovery, and background-refresh observability.

**Disposition.** Fix now in `GBX-1514`, `GBX-1542`, `GBX-1543`, `GBX-1571`,
and `GBX-1572`.

## Signal Inventory

| Signal family | Current source | Current strength | Gap |
| --- | --- | --- | --- |
| Path-to-test | Topology recipes, test file detection, eval recipes | Useful but fragmented | Add confidence levels and direct path inspection. |
| Path-to-eval | `evals/impact.json`, eval cases, profiles, coverage | Strong deterministic metadata | Explain which repository intelligence source changed scope. |
| Recipe | `evals/recipes.json`, package scripts, pyproject command hints | Present | Promote to typed command recipes with purpose, risk, timeout, source, freshness, confidence, and review relevance. |
| Topology | `workspace_topology.py` snapshots | Strong typed local model | Fold into v2 repository intelligence status and dashboard path inspector. |
| Command | Package scripts, pyproject hints, eval recipes, command evidence candidates | Present | Dedupe and classify command recipes without granting permission. |
| Owner | Eval impact owners, topology ownership hints, docs/path conventions | Weak to moderate | Extract advisory ownership hints with provenance and limitations. |
| Package | Topology manifests and components | Strong for common layouts | Share package boundaries with index, changesets, evals, and dashboard. |
| Dependency | Package manifests, lockfiles, topology dependency edges, index dependency hints | Present | Attach dependency manifest freshness and release-surface impact. |
| Generated path | Topology generated-output roots and index exclusions | Present but split | Reuse classifiers across inventory, recommendations, and dashboard. |
| Policy-sensitive path | Tool policy docs and existing policy engine | Not unified with repo intelligence | Add advisory policy-sensitive path hints without weakening policy. |
| Release-sensitive surface | Eval recipes, impact rules, release gates, docs | Present | Surface release sensitivity in path recommendations and changesets. |

## Test Inventory

Current focused tests already cover the baseline surfaces named by v15 tasks:

- `tests/unit/test_repository_index.py`
- `tests/unit/test_workspace_topology.py`
- `tests/unit/test_workspace_memory_capture.py`
- `tests/unit/test_context_builder.py`
- `tests/unit/test_llm_prompts.py`
- `tests/unit/test_eval_recommendations.py`
- `tests/unit/test_changeset_topology.py`
- `tests/integration/test_cli_repository_commands.py`
- `tests/integration/test_web_repository_index_routes.py`
- `frontend/tests/knowledge-autonomy-console.test.tsx`
- `frontend/tests/workspace-overview.test.ts`
- `frontend/tests/changeset-console.test.tsx`

For this audit task, the validation remains docs-focused:

```bash
uv run pytest tests/unit/test_release_candidate_docs.py -q
```

## Disposition

Fix now:

- define and persist repository intelligence snapshot v2
- unify index, topology, command recipes, owner hints, packages, generated
  paths, release surfaces, and freshness metadata
- improve path-to-verification recommendations and stale-evidence risk
- connect confirmed active memory to repository intelligence with provenance
- expose shared freshness and health in CLI, API, dashboard, changesets,
  handoff, context, replay, evals, packaging, and release gates

Document only:

- current v1 index is deterministic and useful for broad orientation
- topology-derived recipe guidance is advisory and degrades on stale topology
- repository index context is omitted from prompts unless fresh

Accepted risk:

- simple symbol extraction is not a language-server replacement
- local source digests are file-size and mtime based for bounded freshness
- dashboard repository inspection is currently an index browser, not a full
  repository intelligence console

Not v15:

- hosted repository indexing
- hosted code search
- external vector-store authority
- provider-side hidden memory
- cross-repository memory sync
- automatic owner assignment
- automatic approval, staging, commits, pushes, pull requests, merges,
  deployments, or package publication
