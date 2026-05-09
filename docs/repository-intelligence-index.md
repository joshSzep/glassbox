# Repository Intelligence Index Contract

The repository intelligence index is a local, rebuildable orientation layer for the current workspace. It records deterministic facts that help Glassbox find project structure, commands, tests, docs, evals, modules, symbols, dependency hints, ownership hints, and recently active paths without rediscovering them every turn.

The index is not a second source of truth. Source files, manifests, docs, eval fixtures, task events, artifacts, and operator-reviewed memory remain authoritative. Index entries must cite provenance and freshness so prompt context can explain where an indexed claim came from and when it was last rebuilt.

The v12 [workspace topology contract](./workspace-topology.md) is a structured
consumer of this same local intelligence. Topology groups index and manifest
signals into packages, apps, libraries, roots, generated outputs, ownership
hints, and dependency edges while retaining its own freshness and degradation
posture.

## Scope

The first index should cover signals that can be gathered locally and deterministically:

- project markers such as `pyproject.toml`, `package.json`, lockfiles, framework configs, and workspace manifests
- source files and module layout
- simple symbols where a local parser or language server can provide stable names
- documented commands from package scripts, pyproject scripts, Makefiles, docs, and release notes
- test files and likely test commands
- documentation and eval case maps
- dependency hints from manifests and lockfiles
- ownership hints from docs, path conventions, and optional operator hints
- recently active paths from local session/task evidence where available

Generated files, vendored dependencies, large binary assets, ignored paths, and build outputs should be excluded unless explicitly configured. The index must respect workspace exclusion conventions and should report skipped scopes rather than silently pretending they were indexed.

## Non-Goals

Non-goals for this contract:

- cloud indexing or remote sync
- hidden vector-store authority
- whole-repository semantic understanding
- replacing language servers, test runners, docs, or source files
- automatic code ownership claims without provenance
- prompt injection of index content without recording source and freshness
- indexing secrets, local credentials, or ignored private outputs

Embeddings can be explored later only if retrieval remains inspectable, source-cited, locally rebuildable, and subordinate to deterministic entries.

## Entity Types

Index entries use explicit kinds:

- `project_marker`: root or package marker that identifies project shape
- `file`: source, config, generated, or documentation file summary
- `module`: package or module-level structure
- `symbol`: parser-derived symbol with file and range provenance
- `command`: runnable command or script with its source manifest/doc
- `test`: test file, test target, or test command
- `doc`: documentation page or section
- `eval_case`: replay/eval case, fixture, profile, or bundle
- `ownership_hint`: path or subsystem ownership signal
- `dependency_hint`: dependency or toolchain signal
- `recent_path`: path recently touched by session, task, or artifact evidence

Entries are stored as `RepositoryIndexEntry` records with stable IDs, names, optional summaries, path/symbol/language metadata, provenance, tags, and update timestamps.

## Provenance

Every entry must include at least one `RepositoryIndexProvenance` record. Source classes are:

- `file_system`: directory walk, path metadata, or file digest
- `manifest`: package, build, or tool manifest
- `documentation`: docs or README-derived signal
- `test`: test file or test framework evidence
- `eval`: eval fixture, profile, case, or bundle
- `static_analysis`: parser, language server, or structured scanner output
- `git`: local git history or active path signal
- `user_hint`: operator-provided hint

Non-user hints require a path. Line ranges must be valid and should be included when a specific section, symbol, or command can be cited. Content digests are preferred for files and manifests so stale entries can be detected without rereading every detail.

## Freshness And Invalidation

A `RepositoryIndexSnapshot` has a schema version, workspace root, builder version, source digest, include/exclude patterns, entries, and status:

- `fresh`: rebuilt successfully against the current observed source digest
- `stale`: source signals changed or the snapshot is older than the configured freshness window
- `building`: a refresh is in progress
- `failed`: the last refresh failed and must include a failure reason

Fresh snapshots require a build timestamp. Failed snapshots require a reason. Snapshot entries require unique stable IDs. Index consumers must be able to tell whether context came from a fresh, stale, or failed index.

## Snapshot Schema V2

Schema version `2` keeps the existing entry list as the broad search surface and
adds typed repository-intelligence sections to the same managed artifact:

- `source_manifests`: repository-owned manifests, docs, eval metadata, or other
  local sources that contributed intelligence, with digest and provenance
- `source_roots`, `test_roots`, `doc_roots`, `generated_paths`, and
  `policy_sensitive_paths`: workspace-relative path hints with confidence,
  provenance, and limitations
- `package_boundaries`: local package or workspace boundaries with roots,
  manifests, generated paths, confidence, and limitations
- `command_recipes`: advisory commands with purpose, review relevance, risk,
  scope paths, timeout hints, confidence, provenance, and limitations
- `ownership_hints`: advisory owner or maintainer labels for paths or
  subsystems; these are not access-control or reviewer-assignment authority
- `release_sensitive_surfaces`: commit-time, push-time, release-candidate, and
  advisory surfaces that can later explain verification recommendations
- `memory_references`: confirmed active workspace memory IDs that contributed
  advisory repository facts, conventions, verified commands, failure patterns,
  architecture notes, owner hints, package quirks, generated-output
  conventions, release-sensitive path notes, or task outcomes
- `limitations`: snapshot-wide caveats for missing, weak, stale, or partial
  intelligence

All v2 paths are workspace-relative and must not traverse upward. Command recipe
text is retained only as a single-line repository-derived recommendation; raw
command logs, raw diffs, secrets, and raw file contents stay out of the artifact
by default. V2 records carry their own confidence, provenance, and limitations,
while the snapshot-level `status`, `built_at`, `builder_version`,
`source_digest`, and source input inventory describe freshness for the whole
artifact.

Older schema-1 artifacts remain readable. When v2-only fields are absent,
Glassbox treats the richer sections as empty and preserves the older freshness
and search behavior. When v2-only fields are present, the artifact must declare
`schema_version >= 2` so operators and replay surfaces can fingerprint the
contract that shaped repository recommendations.

The v15 builder now populates the first layout sections deterministically from
local files. It records Python package boundaries from `pyproject.toml`, node
or frontend workspaces from `package.json`, docs and eval roots when those
directories exist, source/test/doc roots from repository conventions, and
generated/cache/build-output posture for known paths such as
`frontend/generated`, `frontend/out`, `.next`, `dist`, `coverage`, and
`src/glassbox/web/static_next`. The same path classifier backs repository
indexing, workspace topology exclusion, workspace diff generated-path
annotation, and verification drift generated-path checks.

Command recipe discovery is also local and advisory. V15 snapshots derive
recipes from package scripts, `pyproject.toml` console scripts, eval recipe
commands, eval profiles, release-gate scripts, and a bounded scan of documented
command examples. Recipes carry command purpose, review relevance, risk,
timeout hints, scope paths, confidence, provenance, and limitations. They do
not approve execution, grant tool-policy permission, or replace deterministic
release evidence; they only explain likely local commands and why the repository
suggests them.

Ownership, subsystem, and release-surface hints follow the same rule. The
builder reads optional CODEOWNERS-style files when present, adds low-confidence
subsystem owner hints from local path conventions, records subsystem scopes for
runtime, store, web, CLI, frontend, evals, docs, release, packaging, policy,
provider, memory, topology, and review-loop areas when those paths exist, and
groups command recipes into commit-time, push-time, release-candidate, and
advisory release surfaces. These records are explainability aids only; they do
not assign reviewers, enforce access control, or promote advisory checks into
release authority.

Confirmed active workspace memory can be attached to v2 snapshots as
`memory_references` when the rebuild path has access to the workspace memory
projection. Memory references retain memory IDs, kinds, summaries,
confirmation metadata, tags, redaction posture, provenance, confidence, and
limitations. Stale, invalidated, imported-unreviewed, rejected, pruned, and
unconfirmed memory stays out of snapshots by default. Memory references remain
advisory and do not override current manifests, source roots, topology,
dependency metadata, command evidence, generated-path rules, or release-surface
records.

Layout discovery remains bounded and advisory. Excluded directories such as
`node_modules`, `.venv`, `.git`, `.glassbox`, static build outputs, and cache
directories are not crawled for entries, but known generated or build-output
paths may appear as path-level hints with limitations so operators can see why
they matter without retaining raw generated contents.

Invalidation can be triggered by changed manifest digests, changed indexed file digests, deleted paths, schema version changes, builder version changes, configuration changes, or explicit operator refresh requests.

`glassbox repo index status --cwd .` is the operator-facing freshness check. It reports missing, fresh, stale, building, and failed states with the retained index path, entry count, current source digest, retained source digest when available, and safe next actions. New v9 snapshots also retain bounded source input metadata so stale status can show read-only samples of added, removed, or changed paths. Older snapshots that do not have this inventory still report the digest mismatch and ask the operator to rebuild once to enable path-level stale explanations.

V15 repository intelligence uses one shared freshness vocabulary across index,
topology, command recipes, dependency manifests, memory-derived entries, eval
metadata, and release surfaces:

- `fresh`: current local evidence exists and can shape advisory guidance
- `stale`: retained evidence exists, but source inputs changed and confidence
  is degraded until rebuild or inspection
- `missing`: optional intelligence is absent and consumers should fall back to
  broader checks
- `degraded`: the last build failed or an evidence source is not trustworthy
  enough for current guidance
- `conflicting`: confirmed memory or retained metadata conflicts with current
  repository evidence and needs operator review
- `partial`: a refresh is in progress or only part of the metadata set exists

Freshness cues include a drift reason, severity, detail text, limitations, and
safe next actions. In v15 these cues are advisory by default. They become
blocking only when an existing readiness, handoff, release-gate, or verification
contract already treats the affected evidence as required. Stale repository
intelligence should lower recommendation confidence, stale memory should stay
out of prompt context by default, failed or missing snapshots should suggest
explicit rebuild commands, and partial eval metadata should keep recommendations
broad rather than failing unrelated work.

`glassbox observability status --cwd .` now includes a repository-intelligence
health row that aggregates index freshness, topology freshness, command recipe
posture, memory conflict posture, eval metadata, release surfaces, and rebuild
guidance. The same structured health payload is exposed on the dashboard session
aggregate response so workspace overview clients can tell whether repository
intelligence is fresh, stale, missing, degraded, conflicting, or only advisory
before trusting recommendations.

`glassbox repo index inspect --cwd .` returns the retained snapshot for
operator inspection. Human output summarizes v2 counts for manifests, packages,
roots, generated paths, policy-sensitive paths, command recipes, owner hints,
subsystems, release surfaces, and limitations; `--json` returns the full
managed artifact. The dashboard/API status response exposes the same counts,
and `GET /repo/index` returns a compact inspect payload with the retained
metadata identifiers.

`glassbox repo refresh --cwd .` is the explicit local refresh for derived
repository intelligence as a set. It rebuilds the v2 repository index and then
derives workspace topology from that fresh snapshot so path-to-verification and
health surfaces see coherent evidence. `glassbox repo refresh --background
--session SESSION_ID --cwd .` queues the same work for the daemon as a
`repository-intelligence-refresh` background job. That job may write managed
`.glassbox` index, topology, and summary artifacts, but it does not mutate
source files, stage, commit, push, or edit policy files. Operators inspect,
cancel, retry, or abandon it through the normal `glassbox job ...` commands.

Artifact inspection treats `.glassbox/repository-index.json` and
`.glassbox/workspace-topology.json` as protected rebuildable repository
intelligence artifacts. They are included in `glassbox artifacts inspect`
reports, skipped by prune, and included in workspace backups when present.
Restoring a backup may recover the latest retained snapshots for convenience,
but the supported recovery path is still to rebuild them with `glassbox repo
refresh --cwd .` whenever freshness cues say they are stale, missing, degraded,
or conflicting.

## Storage And Rebuild Strategy

The first implementation may store the index as a retained JSON artifact or as a projection table. In either case:

- the snapshot format must include `schema_version`
- rebuilds must be explicit and observable
- old snapshots should remain inspectable long enough for debugging
- failed rebuilds must degrade to existing repository context rather than breaking sessions
- large workspaces need bounded scans with clear skipped-path evidence
- generated API types, lockfiles, and build outputs should be summarized from manifests where possible rather than fully scanned

A future projection can record index status and snapshot metadata while keeping detailed entries in an artifact. That avoids turning large index contents into event-log noise while preserving auditability.

## Prompt Use

The index may influence turn context only when the prompt section records entry IDs, freshness, source paths, and why the entries were selected. Prompt builders must separate repository index context from workspace memory, runtime notes, transcript content, and task-plan context.

Stale entries may be shown as degraded orientation but must not be presented as fresh facts. Failed or unavailable indexes should fall back to the bounded repository context already used by Glassbox.

## Test Matrix For Implementers

The first builder should be validated against:

- source checkout with Python and frontend project markers
- installed package or sparse checkout with limited source availability
- large repository with bounded scan limits
- ignored directories such as `.git`, virtual environments, build outputs, and frontend dependency folders
- generated files and generated API types
- documentation map with nested docs and examples
- eval cases, fixtures, bundles, and profiles
- command extraction from manifests and docs
- stale index detection after manifest/file changes
- failed rebuild handling with prior snapshot fallback
- prompt context selection with provenance and freshness visible

## Relationship To Memory

Repository intelligence is rebuildable from local sources; workspace memory is operator-reviewed durable knowledge. The two can complement each other, but neither should silently overwrite or hide the other. If an index-derived observation should become durable memory, it must pass through the operator-confirmed memory capture flow. If confirmed memory enriches an index snapshot, the snapshot must cite the memory ID and preserve enough metadata for recommendations, context, and replay surfaces to explain the influence.
