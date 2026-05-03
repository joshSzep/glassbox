# V12 Release Gate

For the docs hub and operator guides, start at [README.md](./README.md).

The v12 release gate is the canonical automated check for the
reviewable-change milestone. It inherits the v11 confidence-and-adoption gate,
then adds deterministic v12 evidence for changeset lifecycle review, review
brief generation, commit readiness, branch-candidate adoption, topology-aware
recommendations, and command-evidence surfacing. Live provider evidence remains
advisory and opt-in.

Run the gate from the repository root:

```bash
uv run python scripts/validate_v12_release_gate.py
```

For a non-mutating preview of the stage plan and retained summary shape:

```bash
uv run python scripts/validate_v12_release_gate.py --dry-run
```

Use `--evidence-dir` for release-candidate evidence so `summary.json`,
advisory provider evidence, package references, and eval output roots can be
reviewed together. Eval artifacts are written under
`.glassbox/evals/<evidence-dir-name>/`.

## Automated Stages

The v12 gate starts with every deterministic stage from
[v11-release-gate.md](./v11-release-gate.md), including inherited v10/v11
Python, frontend, package, installed-wheel, provider-policy, long-run,
cockpit, checkpoint, compaction, tool-attempt, recommendation, branch-search,
knowledge, and deterministic eval evidence.

The v12-specific blocking stages are:

| Stage | Evidence |
| --- | --- |
| `v12 deterministic eval release report` | commit, push, and expanded release-candidate profiles produce retained v12 sign-off evidence |
| `v12 reviewable-change release profile` | the `release-candidate` profile runs with the v12 reviewable-change fixtures and profile budget |
| `v12 changeset lifecycle smoke` | the `changeset.reviewable-lifecycle` and `changeset.branch-candidate-adoption` fixtures replay together |
| `v12 eval coverage audit` | the release-candidate profile covers all release-candidate capabilities declared in `evals/coverage.json` |

The inherited package-content stage validates that the sdist includes the v12
release-gate guide, task graph, reviewable-change contract, lifecycle audit,
eval cases and bundles, generated API files, release-gate scripts, and
dashboard static assets. The installed-wheel smoke from the inherited package
path still runs after the blocking stages and must pass for the newest
`dist/glassbox-*.whl`.

To plan provider evidence without contacting a provider:

```bash
uv run python scripts/validate_v12_release_gate.py \
  --dry-run \
  --include-provider-canaries \
  --evidence-dir .glassbox/releases/v12-gate-dry-run
```

The retained `summary.json` records provider evidence under `advisory` with:

- `blocking=false`
- `latest_status`
- `freshness_status`
- `missing_scenarios`
- `evidence_dir`
- `summary_path` when planned or run
- provider/model/scenario counts when collected

When `--include-provider-canaries` is omitted, the summary records an explicit
structured skip. When it is present, `glassbox provider canary run` writes
redacted provider-canary evidence under `provider-canary/`, and the gate records
freshness and missing-scenario posture using the same evidence interpretation as
`glassbox provider recommend`.

## Evidence Summary

The gate writes `summary.json` under the selected evidence directory. The
summary records:

- `blocking`: the blocking gate stages and installed-wheel plan/results
- `stages`: the same blocking stage list for compatibility with earlier gates
- `advisory`: provider canary execution or explicit skip/plan details
- `provider_evidence`: the opt-in, non-authoritative provider evidence policy
- `release_authority`: inherited v11 evidence plus explicit v12 deterministic
  eval, changeset lifecycle, package contents, and installed-wheel evidence
- `artifacts`: eval evidence root, provider evidence, release-gate docs, v12
  task graph, reviewable-change contract, lifecycle audit, eval docs, and replay
  docs

Every skipped advisory path carries an explicit reason. Blocking stages must not
depend on live provider credentials, live browser timing, remote git providers,
live pull request creation, or screen-reader availability.

## Pass And Fail Policy

- Any failed blocking stage fails the v12 release gate.
- Missing package contents, stale generated API files, missing dashboard static
  assets, or installed-wheel smoke failures fail through inherited stages.
- The `release-candidate` eval profile must pass and its profile budget must
  stay within the repository-owned limits.
- The release-candidate coverage audit must report no uncovered
  release-candidate capabilities.
- Provider canaries, provider freshness, live dashboard evidence,
  accessibility pairings, dogfooding, and residual-risk acceptance are retained
  beside the gate; they do not replace deterministic release authority.

Provider canary failures, missing credentials, stale evidence, and skipped
scenarios do not block deterministic release authority. They are retained for
reviewer confidence and operator follow-up beside replay/eval, package, and
installed-smoke evidence.
