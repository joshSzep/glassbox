# Workspace Topology Contract

Workspace topology is local, rebuildable intelligence about how a repository is
structured. It helps Glassbox map changed paths to packages, apps, libraries,
test roots, docs, generated outputs, ownership hints, and dependency
relationships. It is not authority over the repository: source files,
manifests, lockfiles, docs, eval fixtures, and operator-reviewed memory remain
the source of truth.

## Model

The typed model lives in
[`workspace_topology.py`](../src/glassbox/runtime/workspace_topology.py). A
`WorkspaceTopologySnapshot` records:

- `freshness`: `fresh`, `stale`, `failed`, or `missing`
- `workspace_root`, `built_at`, `builder_version`, `source_digest`, and
  `source_inputs`
- `components`: packages, apps, libraries, docs roots, test roots, tooling, and
  generated-output areas
- `dependencies`: workspace-to-workspace or workspace-to-external dependency
  edges
- `limitations` and `failure_reason` when the snapshot should degrade guidance

Components retain root paths, source roots, test roots, docs roots, generated
output roots, manifests, lockfiles, ownership hints, tags, and provenance.
Dependency edges must name a source component and exactly one target: either
another component or an external package/toolchain name.

## Provenance

Every component, manifest, lockfile, and dependency edge must cite provenance.
Supported provenance sources are:

- `repository_index`
- `manifest`
- `lockfile`
- `config`
- `documentation`
- `path_convention`
- `user_hint`

Non-user provenance requires a workspace-relative path. Line ranges are allowed
when a manifest or docs section can be cited. Content digests should be retained
when the builder has them, so stale topology can be explained without pretending
old structure is fresh.

## Freshness

Topology consumers must use the snapshot posture:

- `fresh` snapshots may guide normal path-aware verification and review copy.
- `stale` snapshots are degraded. They may suggest likely packages or tests, but
  review surfaces must say topology is stale.
- `failed` and `missing` snapshots are unavailable. Consumers should fall back to
  existing repository index, changed-file inventory, and explicit operator
  review.

Stale or failed topology must never be presented as fact. It should lower
confidence, add limitations, and produce safe next actions such as rebuilding
topology before relying on package or ownership recommendations.

## Single-Package Repositories

Small repositories should not be noisy. A Python-only or frontend-only project
can be represented as one component with manifest, lockfile, source, test, docs,
and generated-output roots. Builders should avoid inventing subpackages unless a
manifest, workspace config, or clear path convention supports them.

## Relationship To Repository Index

The repository intelligence index remains the broad orientation layer. Topology
is a structured view derived from the index plus manifests and lockfiles. The
builder added in a later task should reuse repository-index scan exclusions and
provenance where possible, then retain topology-specific freshness and
dependency edges.

## Validation Fixtures

The model test matrix covers:

- Python-only workspaces with `pyproject.toml`, `uv.lock`, source roots, tests,
  docs, and runtime dependencies
- frontend-only workspaces with `package.json`, `pnpm-lock.yaml`, app roots,
  tests, e2e roots, and generated outputs
- mixed backend/frontend workspaces with internal dependency edges and external
  package dependencies
- stale and failed snapshots that degrade recommendations
- invalid shapes such as duplicate component IDs, missing dependency targets,
  and absolute component paths
