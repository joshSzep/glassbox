# V11 Release Gate

For the docs hub and operator guides, start at [README.md](./README.md).

The v11 release gate is the canonical automated check for the `0.10.0`
confidence-and-adoption milestone. It inherits the v10 long-running-task gate,
then adds explicit deterministic v11 evidence for recommendation explainability,
compaction cap guidance, checkpoint absence explanation, knowledge posture, and
branch-search decision support. Live provider evidence remains advisory and
opt-in.

Run the gate from the repository root:

```bash
uv run python scripts/validate_v11_release_gate.py
```

For a non-mutating preview of the stage plan and retained summary shape:

```bash
uv run python scripts/validate_v11_release_gate.py --dry-run
```

Use `--evidence-dir` for release-candidate evidence so `summary.json`, advisory
provider evidence, package references, and eval output roots can be reviewed
together. Eval artifacts are written under `.glassbox/evals/<evidence-dir-name>/`.

## Automated Stages

The v11 gate starts with every deterministic stage from
[v10-release-gate.md](./v10-release-gate.md), including inherited v9/v10 Python,
frontend, package, installed-wheel, provider-policy, long-run, cockpit,
checkpoint, compaction, tool-attempt, and deterministic eval evidence.

The v11-specific blocking stages are:

| Stage | Evidence |
| --- | --- |
| `v11 package version metadata` | package import and CLI version tests assert `0.10.0` |
| `v11 deterministic eval release report` | commit, push, and expanded release-candidate profiles produce retained v11 sign-off evidence |
| `v11 confidence release profile` | the `release-candidate` profile runs with the GBX-1190 v11 confidence fixtures |
| `v11 recommendation and recovery guidance smoke` | release-path recommendation, compaction cap guidance, and checkpoint absence fixtures replay together |
| `v11 knowledge and branch-search smoke` | knowledge posture and branch-search decision-support fixtures replay together |
| `v11 eval coverage audit` | the release-candidate profile covers all release-candidate capabilities declared in `evals/coverage.json` |

The installed-wheel smoke from the inherited package path still runs after the
blocking stages and must pass for the newest `dist/glassbox-*.whl`. That smoke
includes `glassbox --version`, terminal help, command guide/tree, daemon,
profile, eval, and dashboard static-route checks from the installed wheel.

To plan provider evidence without contacting a provider:

```bash
uv run python scripts/validate_v11_release_gate.py \
  --dry-run \
  --include-provider-canaries \
  --evidence-dir .glassbox/releases/v11-gate-dry-run
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
- `release_authority`: inherited v10 evidence plus explicit v11 deterministic
  eval, package version, package contents, and installed-wheel evidence
- `artifacts`: eval evidence root, provider evidence, release-gate docs, v11
  confidence contract, live cockpit evidence, accessibility review, and
  reviewer evidence guidance

Every skipped advisory path carries an explicit reason. Blocking stages must not
depend on live provider credentials, live browser timing, or screen-reader
availability.

## Pass And Fail Policy

- Any failed blocking stage fails the v11 release gate.
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
