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

Invalidation can be triggered by changed manifest digests, changed indexed file digests, deleted paths, schema version changes, builder version changes, configuration changes, or explicit operator refresh requests.

`glassbox repo index status --cwd .` is the operator-facing freshness check. It reports missing, fresh, stale, building, and failed states with the retained index path, entry count, current source digest, retained source digest when available, and safe next actions. New v9 snapshots also retain bounded source input metadata so stale status can show read-only samples of added, removed, or changed paths. Older snapshots that do not have this inventory still report the digest mismatch and ask the operator to rebuild once to enable path-level stale explanations.

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

Repository intelligence is rebuildable from local sources; workspace memory is operator-reviewed durable knowledge. The two can complement each other, but neither should silently overwrite or hide the other. If an index-derived observation should become durable memory, it must pass through the operator-confirmed memory capture flow.
