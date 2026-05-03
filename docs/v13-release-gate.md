# V13 Release Gate

For the docs hub and operator guides, start at [README.md](./README.md).

The v13 release gate is the canonical automated check for the review-loop
milestone. It inherits the full v12 reviewable-change gate, then adds
deterministic v13 evidence for review feedback, response tracking, manual
evidence, stale fixup verification, lifecycle briefs, handoff readiness,
publication-boundary non-claims, and integrated in-session changeset UX.
Provider, browser, dashboard walkthrough, and accessibility evidence remains
advisory unless a later task promotes it through a deterministic fixture-backed
contract.

Run the gate from the repository root:

```bash
uv run python scripts/validate_v13_release_gate.py
```

For a non-mutating preview of the stage plan and retained summary shape:

```bash
uv run python scripts/validate_v13_release_gate.py --dry-run
```

Use `--evidence-dir` for release-candidate evidence so `summary.json`,
advisory provider/browser/accessibility evidence placeholders, package
references, and eval output roots can be reviewed together. Eval artifacts are
written under `.glassbox/evals/<evidence-dir-name>/`.

## Automated Stages

The v13 gate starts with every deterministic stage from
[v12-release-gate.md](./v12-release-gate.md), including inherited Python
format, lint, typecheck, focused terminal and dashboard tests, frontend lint,
frontend typecheck, frontend tests, generated API freshness, production build,
static asset validation, package contents, installed-wheel smoke, deterministic
eval release reports, release-candidate profile execution, changeset lifecycle
smoke, and eval coverage audit.

The v13-specific blocking stages are:

| Stage | Evidence |
| --- | --- |
| `v13 deterministic eval release report` | commit, push, and expanded release-candidate profiles produce retained v13 sign-off evidence |
| `v13 review-loop release profile` | the `release-candidate` profile runs with the v13 review-loop fixtures and 22-case profile budget |
| `v13 review-loop eval smoke` | `changeset.review-loop-lifecycle` and `changeset.in-session-review-ux` replay together |
| `v13 review-loop command coverage` | focused CLI/TUI/plain interactive review-loop tests cover in-session entry points |
| `v13 eval coverage audit` | the release-candidate profile covers all release-candidate capabilities declared in `evals/coverage.json` |

The inherited package-content stage validates that the sdist includes the v13
release-gate guide, task graph, review-loop docs, eval cases and bundles,
generated API files, release-gate scripts, and dashboard static assets. The
installed-wheel smoke from the inherited package path still runs after the
blocking stages and must pass for the newest `dist/glassbox-*.whl`.

To plan provider evidence without contacting a provider:

```bash
uv run python scripts/validate_v13_release_gate.py \
  --dry-run \
  --include-provider-canaries \
  --evidence-dir .glassbox/releases/v13-gate-dry-run
```

The retained `summary.json` records provider evidence under `advisory` with:

- `blocking=false`
- `latest_status`
- `freshness_status`
- `missing_scenarios`
- `evidence_dir`
- `summary_path` when planned or run
- provider/model/scenario counts when collected

The `v13 advisory browser evidence` and `v13 advisory accessibility evidence`
entries are recorded as explicit skipped advisory entries by the deterministic
gate. Their retained evidence belongs in dogfooding or release-candidate review
directories and must carry freshness, limitations, and non-claims according to
[browser-accessibility-evidence.md](./browser-accessibility-evidence.md).

## Evidence Summary

The gate writes `summary.json` under the selected evidence directory. The
summary records:

- `blocking`: the blocking gate stages and installed-wheel plan/results
- `stages`: the same blocking stage list for compatibility with earlier gates
- `advisory`: provider canary execution or explicit skip/plan details, plus
  structured browser/dashboard and accessibility skips
- `provider_evidence`: the opt-in, non-authoritative provider evidence policy
- `release_authority`: inherited v12 evidence plus explicit v13 deterministic
  eval, review-loop command, package contents, and installed-smoke evidence
- `artifacts`: eval evidence root, provider/browser/accessibility evidence
  pointers, release-gate docs, v13 task graph, review-loop contract, UX audit,
  eval docs, replay docs, and publication-boundary docs

Every skipped advisory path carries an explicit reason. Blocking stages must
not depend on live provider credentials, live browser timing, remote git
providers, live pull request creation, screen-reader availability, or raw
`.glassbox` evidence committed to the repository.

## Pass And Fail Policy

- Any failed blocking stage fails the v13 release gate.
- Missing package contents, stale generated API files, missing dashboard static
  assets, or installed-wheel smoke failures fail through inherited stages.
- The `release-candidate` eval profile must pass and its 22-case profile budget
  must stay within the repository-owned limits.
- The release-candidate coverage audit must report no uncovered
  release-candidate capabilities.
- The review-loop smoke must replay the feedback lifecycle and in-session UX
  fixtures without drift.
- Provider canaries, provider freshness, live browser/dashboard evidence,
  accessibility pairings, dogfooding, manual evidence, and residual-risk
  acceptance are retained beside the gate; they do not replace deterministic
  release authority.

Provider canary failures, missing credentials, stale browser evidence, skipped
accessibility pairings, and unavailable manual walkthroughs do not block
deterministic release authority. They are retained for reviewer confidence and
operator follow-up beside replay/eval, package, command-coverage, and
installed-smoke evidence.
