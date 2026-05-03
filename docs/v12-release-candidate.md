# Glassbox v12 Release Candidate

This page is the operator and contributor guide for the Glassbox v12
release-candidate track. It names the supported reviewable-change operating
model, validation path, evidence expectations, non-goals, residual risks, and
release decision without requiring readers to inspect the task graph.

## Release Posture

Glassbox v12 keeps the v11 confidence-and-adoption model and focuses on making
local changes reviewable before an operator chooses to commit. The release track
adds explicit changesets, structured change inventory, verification readiness,
review briefs, commit preparation, branch-candidate adoption, worktree
isolation, workspace topology, and command-evidence summaries.

The package version for this line remains `0.10.0`.

The primary product shape is:

- terminal chat remains the primary operator surface
- the dashboard remains the paired local cockpit and evidence surface
- SQLite canonical events remain the source of truth
- changesets are local evidence objects, not remote review objects
- review briefs are deterministic summaries, not proof
- commit readiness is advisory and does not stage or commit
- worktree and branch-candidate adoption record evidence without merging,
  rebasing, cherry-picking, pushing, or opening pull requests
- deterministic replay, eval, package, and installed-wheel evidence remain
  release authority
- live dashboard, provider, accessibility, and dogfooding evidence strengthen
  confidence but do not replace deterministic gates
- v12 is local-first agent work, not hosted code review or automatic PR
  automation

Use these discovery commands:

```bash
uv run glassbox command guide
uv run glassbox command tree
```

The v12 automated release-candidate gate is:

```bash
uv run python scripts/validate_v12_release_gate.py
```

For a non-mutating preview:

```bash
uv run python scripts/validate_v12_release_gate.py --dry-run
```

The retained evidence directory used for the current release-candidate pass is:

```text
.glassbox/releases/gbx-1293-v12-release-candidate/
```

The v12 eval artifacts for that candidate are retained under:

```text
.glassbox/evals/gbx-1293-v12-release-candidate/
```

Focused dogfooding evidence is summarized in
[v12-dogfooding-summary.md](./v12-dogfooding-summary.md). Local `.glassbox/`
evidence is workspace state and is not committed to git.

## Supported Operating Model

- **Changesets**: `glassbox changeset create`, `show`, `refresh`, `brief`,
  `verification-plan`, `commit-prep`, and `export` keep local review evidence
  centered on one change.
- **Change inventory**: refreshed inventory records changed paths, summary-only
  file metadata, provenance confidence, risk, freshness, and stale-inventory
  posture without retaining raw diffs.
- **Verification readiness**: changesets map current inventory to repository
  recipes, eval recommendations, missing/stale/failed/accepted-risk posture, and
  safe next commands without running verification implicitly.
- **Review briefs**: deterministic Markdown/JSON briefs summarize objective,
  inventory, provenance, verification, command evidence, risks, safe inspection
  commands, limitations, and non-claims for reviewer-safe handoff.
- **Commit preparation**: `glassbox changeset commit-prep` explains local commit
  blockers, risky files, suggested message text, and safe next commands without
  staging files or committing.
- **Commit evidence**: commit-message suggestions, pre-commit evidence, and
  commit-prep guidance remain suggestion-only and operator-controlled.
- **Branch-candidate adoption**: selected branch-search candidates can be
  previewed and adopted into changeset evidence only after explicit
  confirmation; final git mutation remains outside Glassbox automation.
- **Worktree isolation**: temporary local worktree custody, cleanup previews,
  and candidate adoption boundaries are documented for review before cleanup.
- **Workspace topology**: topology-aware recommendations connect backend,
  frontend, docs, eval, package, generated API, and dashboard paths to
  verification guidance when impact rules exist.
- **Command evidence**: changeset details and review briefs summarize retained
  command attempts by purpose, verification relevance, risk, artifact posture,
  environment capture, and safe next actions.

## Primary Operator Flows

### Review A Local Change

```bash
uv run glassbox changeset create --from workspace-diff --session SESSION_ID --cwd .
uv run glassbox changeset refresh CHANGESET_ID --cwd .
uv run glassbox changeset verification-plan CHANGESET_ID --cwd .
uv run glassbox changeset brief CHANGESET_ID --cwd .
uv run glassbox changeset commit-prep CHANGESET_ID --cwd .
```

The recommended order is refresh, brief, verification-plan, selected validation
commands, then commit-prep. Commit-prep remains advisory until the operator
stages and commits deliberately.

### Prepare Reviewer Evidence

```bash
uv run glassbox changeset brief CHANGESET_ID --format markdown --cwd .
uv run glassbox changeset export CHANGESET_ID --cwd .
uv run glassbox changeset show CHANGESET_ID --json --cwd .
```

Review briefs and exports avoid raw diffs, raw command output, and secret
material. Raw `.glassbox` state remains local unless explicitly sanitized.

### Compare And Adopt Branch Candidates

```bash
uv run glassbox branch-search start SESSION_ID \
  --objective "Compare repair approaches" \
  --strategy "minimal fix" \
  --strategy "broader refactor" \
  --cwd .
uv run glassbox branch-search select SEARCH_ID CANDIDATE_ID --reason REASON --cwd .
uv run glassbox changeset adoption-preview \
  --branch-search SEARCH_ID \
  --candidate CANDIDATE_ID \
  --cwd .
uv run glassbox changeset adopt-candidate \
  --branch-search SEARCH_ID \
  --candidate CANDIDATE_ID \
  --confirm \
  --cwd .
```

Adoption records evidence only. It does not merge, stage, commit, push, open a
pull request, or clean up worktrees automatically.

### Choose Verification

```bash
uv run glassbox eval recommend PATH [PATH ...] --cwd .
uv run glassbox changeset verification-plan CHANGESET_ID --cwd .
uv run glassbox eval run --profile release-candidate --cwd .
uv run glassbox eval report commit-smoke push-confirmation release-candidate --cwd .
```

The v12 release-candidate profile includes the compact changeset lifecycle and
branch-candidate adoption fixtures introduced for `GBX-1290`.

## Release-Readiness Checklist

Before treating a build as the v12 release candidate, complete this list:

- The v12 reviewable-change contract, lifecycle audit, release gate,
  dogfooding summary, and release-candidate guide are linked from the docs hub.
- `uv run python scripts/validate_v12_release_gate.py` passes and writes
  `summary.json` with `blocking` and `advisory` sections.
- The deterministic `release-candidate` eval profile passes with 20 selected
  cases, including `changeset.reviewable-lifecycle` and
  `changeset.branch-candidate-adoption`.
- `glassbox eval audit --profile release-candidate --cwd .` reports no
  uncovered release-candidate capabilities.
- Changeset creation, inventory refresh, review brief generation, verification
  readiness, commit preparation, and command-evidence summaries have unit,
  integration, frontend, and deterministic eval coverage.
- Branch-candidate adoption and worktree isolation keep merge, commit, push,
  PR creation, and cleanup destructive actions operator-controlled.
- Topology recommendations cover the known v12 surfaces and name unmatched
  paths as follow-up risk when impact rules are missing.
- Generated OpenAPI/types and dashboard static assets are fresh and packaged.
- Built wheel and sdist contents include release docs, eval fixtures, scripts,
  generated API files, and dashboard static assets.
- Dogfooding findings have dispositions as fixes, docs, tests/evals, accepted
  risks, or post-v12 follow-ups.
- Provider canaries, live dashboard evidence, and accessibility evidence are
  either retained as advisory evidence or explicitly skipped with bounded
  reasons.
- Raw `.glassbox` state is not committed; reviewer-safe summaries are used for
  handoff and release review.

## Current Evidence Summary

The current retained v12 evidence shows:

- non-dry-run v12 gate: passed for `GBX-1293`, with final evidence retained at
  `.glassbox/releases/gbx-1293-v12-release-candidate/summary.json`; 80 blocking
  stages passed and one advisory provider evidence skip was retained
- v12 release gate dry run: passed during `GBX-1291`, including explicit
  blocking and advisory summary shape
- package contents validation: wheel and sdist include required release files,
  generated API files, eval fixtures, release scripts, and dashboard static
  assets
- installed-wheel smoke: passed for `glassbox-0.10.0-py3-none-any.whl`
- release-candidate eval profile: `20/20` selected cases passed with profile
  budget OK
- release eval report: `commit-smoke`, `push-confirmation`, and
  `release-candidate` profiles passed with `30/30` capabilities covered
- v12 changeset lifecycle smoke: `changeset.reviewable-lifecycle` and
  `changeset.branch-candidate-adoption` both passed
- eval coverage audit: release-candidate coverage reported no uncovered
  capabilities
- dogfooding: findings and follow-up candidates are triaged in
  [v12-dogfooding-summary.md](./v12-dogfooding-summary.md)
- provider evidence: optional and advisory; the v12 gate retained an explicit
  structured skip in its advisory section
- live dashboard and accessibility evidence: bounded advisory evidence from
  earlier milestone docs remains relevant, but no new live dashboard or
  accessibility pass was promoted to blocking v12 authority

## Known Residual Risks

- Commit readiness is advisory local posture. It can identify missing
  inventory, stale verification, dirty worktree state, staged/unstaged
  ambiguity, and risky files, but it does not prove a commit is correct.
- Review briefs are deterministic summaries. They do not include raw diffs, raw
  command output, or proof that a reviewer inspected every file.
- Command evidence is available when commands flow through retained Glassbox
  session instrumentation. Manual shell commands outside that path may not
  appear as changeset command evidence.
- Branch-candidate adoption can retain selected-candidate evidence even when a
  candidate lacks materialized session, diff inventory, worktree state, or
  verification summary; those limits must remain visible in the preview.
- Topology recommendation coverage depends on repository impact rules.
  Dogfooding found `src/glassbox/runtime/changesets.py` unmatched in a mixed
  path recommendation pass.
- Live provider canary evidence is advisory and may be skipped. Provider
  behavior does not replace deterministic release evidence.
- No new live dashboard browser or accessibility pass was collected for
  `GBX-1292` or `GBX-1293`; existing deterministic and bounded advisory
  evidence should not be overclaimed as broad manual certification.
- Long-running work remains bounded local continuation, not indefinite
  unattended operation.

## Deliberate Non-Goals

v12 does not introduce hosted code review, hosted workspace ownership,
multi-user remote collaboration state, automatic staging, automatic commits,
automatic pushes, automatic pull request creation, automatic branch-search
merging, automatic worktree cleanup after dirty changes, provider reliability
guarantees, broad accessibility certification, or indefinite unattended
autonomy.

## Release Decision

Decision: GO for v12 release candidate publication.

Decision date: 2026-05-03.

Candidate build reviewed: `GBX-1293` release-candidate working tree with final
v12 gate evidence retained locally.

Retained evidence:

```text
.glassbox/releases/gbx-1293-v12-release-candidate/
.glassbox/evals/gbx-1293-v12-release-candidate/
.glassbox/releases/gbx-1292-dogfooding/
```

Final pass/fail state:

| Area | State | Evidence |
| --- | --- | --- |
| Automated v12 gate | passed | `.glassbox/releases/gbx-1293-v12-release-candidate/summary.json` |
| Deterministic eval release report | passed | `.glassbox/evals/gbx-1293-v12-release-candidate/v12-release-signoff/` |
| V12 reviewable-change release profile | passed | `.glassbox/evals/gbx-1293-v12-release-candidate/v12-reviewable-change-release/` |
| V12 changeset lifecycle smoke | passed | `.glassbox/evals/gbx-1293-v12-release-candidate/v12-changeset-lifecycle-smoke/` |
| Release-candidate eval coverage | passed | `glassbox eval audit --profile release-candidate --cwd .` in the v12 gate |
| Package and installed smoke | passed | package contents validation plus installed-wheel smoke in the v12 gate |
| Dogfooding disposition | passed triage | [v12-dogfooding-summary.md](./v12-dogfooding-summary.md) |
| Provider posture | advisory skipped | v12 gate advisory provider evidence section |
| Live dashboard/accessibility posture | advisory bounded | inherited docs and deterministic dashboard/front-end evidence |
| Residual risk review | accepted | known residual risks listed above |

No deterministic blocker remains open for v12 release-candidate publication.
The accepted residual risks stay bounded to advisory commit readiness,
review-brief non-proof, manual command-evidence gaps, incomplete candidate
evidence, topology impact-rule coverage, provider/live dashboard/accessibility
advisory status, and bounded local autonomy.

## Related Files

- [v12-reviewable-change-contract.md](./v12-reviewable-change-contract.md)
- [v12-change-lifecycle-audit.md](./v12-change-lifecycle-audit.md)
- [v12-release-gate.md](./v12-release-gate.md)
- [v12-dogfooding-summary.md](./v12-dogfooding-summary.md)
- [change-inventory.md](./change-inventory.md)
- [changeset-verification-readiness.md](./changeset-verification-readiness.md)
- [review-briefs.md](./review-briefs.md)
- [commit-readiness.md](./commit-readiness.md)
- [commit-message-suggestions.md](./commit-message-suggestions.md)
- [precommit-evidence.md](./precommit-evidence.md)
- [commit-preparation.md](./commit-preparation.md)
- [worktree-isolation.md](./worktree-isolation.md)
- [workspace-topology.md](./workspace-topology.md)
- [command-evidence.md](./command-evidence.md)
- [replay-evals.md](./replay-evals.md)
- [providers.md](./providers.md)
- [release-packaging.md](./release-packaging.md)
- [tasks-v12.md](./tasks-v12.md)
