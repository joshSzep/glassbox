# V12 Dogfooding Summary

This document records the sanitized `GBX-1292` dogfooding pass for the v12
reviewable-change milestone. The goal was to use the v12 changeset, review
brief, verification readiness, commit preparation, branch-candidate adoption,
topology recommendation, and command-evidence surfaces on ordinary local work
before publishing the release-candidate guide.

Retained local evidence was written under:

```text
.glassbox/releases/gbx-1292-dogfooding/
```

The evidence directory is intentionally local and uncommitted. Sanitized
results and friction findings are recorded here for review.

## Passes

| Pass | Command | Result | Notes |
| --- | --- | --- | --- |
| Local dogfooding session seed | `uv run glassbox session run --cwd . --db-path .glassbox/releases/gbx-1292-dogfooding/glassbox.sqlite3 --model-name dogfood:local --approval-mode review --autonomy-mode guided` | Passed | Created session `2bdcaa15-febb-4634-a5fe-f43d0b2dfaf0`; arbitrary UUID input was rejected by changeset creation until a real retained session existed. |
| Changeset from real workspace diff | `uv run glassbox changeset create --from workspace-diff --session 2bdcaa15-febb-4634-a5fe-f43d0b2dfaf0 --objective "Document GBX-1292 v12 dogfooding evidence" --json --cwd . --db-path .glassbox/releases/gbx-1292-dogfooding/glassbox.sqlite3` | Passed | Created changeset `b59e7fff-c95c-40da-af92-04f4e98399f6` from the real dirty workspace containing this dogfooding summary. Initial output degraded because the session was still running and no structured inventory was attached yet. |
| Review brief for local change | `uv run glassbox changeset brief b59e7fff-c95c-40da-af92-04f4e98399f6 --format markdown --cwd . --db-path .glassbox/releases/gbx-1292-dogfooding/glassbox.sqlite3` | Passed | Before refresh, the brief correctly said no structured inventory was attached. After `changeset refresh`, it named `docs/v12-dogfooding-summary.md`, summary-only inventory, unknown provenance, missing verification, medium risk, and safe inspection commands. |
| Commit preparation with stale or missing verification | `uv run glassbox changeset commit-prep b59e7fff-c95c-40da-af92-04f4e98399f6 --style conventional --json --cwd . --db-path .glassbox/releases/gbx-1292-dogfooding/glassbox.sqlite3` | Passed | Initial parallel run exposed a brief-generation race and reported a missing brief. Sequential rerun after refresh and brief generation returned `dirty_untracked_risk`, no staged changes, missing verification, unresolved provenance risk, and a suggestion-only commit message. |
| Branch-candidate adoption into changeset | `uv run glassbox changeset adopt-candidate --branch-search 59ab1c59-ea82-4b5b-b901-90f5a8c1a14f --candidate 4a65fc77-d499-4ba7-bda8-c064b735d982 --objective "Adopt selected GBX-1292 dogfooding summary candidate" --confirm --json --cwd . --db-path .glassbox/releases/gbx-1292-dogfooding/glassbox.sqlite3` | Passed | Preview required explicit review, then confirmed adoption created changeset `deb2b463-6d6f-4618-b821-7602066ebee8`. Output retained candidate limitations and stated no merge, commit, push, or PR action was performed. |
| Topology-aware recommendations for mixed change | `uv run glassbox eval recommend src/glassbox/runtime/changesets.py frontend/components/console/changeset-console.tsx docs/v12-dogfooding-summary.md --json --cwd . --db-path .glassbox/releases/gbx-1292-dogfooding/glassbox.sqlite3` | Passed with friction | Recommended dashboard eval cases, frontend checks, release-candidate and advisory profiles, and docs checks. `src/glassbox/runtime/changesets.py` was unmatched, which is a v12 topology coverage gap for future impact-rule work. |

Focused validation for the sanitized summary and docs links:

```text
uv run pytest tests/unit/test_release_candidate_docs.py -q
```

Result: `47 passed`.

## Findings

### Changeset Creation

- The workspace-diff flow correctly refused an arbitrary UUID and required a
  real retained session before creating changeset evidence.
- The successful changeset creation made the degraded state explicit:
  `session is running, not terminal` and `workspace diff has 1 changed path(s)`.
  That language was useful, but the operator still had to know that
  `changeset refresh` was the next command before inventory became reviewable.

### Change Inventory Provenance

- Refreshing the changeset produced summary-only inventory for
  `docs/v12-dogfooding-summary.md`, marked freshness as `fresh`, and raised
  medium risk from docs plus missing provenance.
- The provenance posture was honest: the file had unknown Glassbox provenance
  because the document was edited directly during dogfooding.

### Verification Readiness

- Before refresh, verification readiness was blocked by missing inventory.
- After refresh, verification readiness recommended the docs-only contributor
  check: `uv run pytest tests/unit/test_release_candidate_docs.py -q`.
- The readiness copy stayed advisory and did not imply that old or unrun checks
  were fresh.

### Review Brief Quality

- The post-refresh brief was reviewer-safe and named objective, inventory,
  provenance, verification, risk, safe inspection commands, non-claims, and
  limitations without raw diffs or logs.
- The brief correctly switched `Local only` to true once the inventory included
  a local path.

### Commit Readiness

- Commit preparation did not stage, commit, push, or open a PR.
- The sequential rerun produced useful blockers: no staged changes, dirty
  untracked workspace, missing branch/task provenance, missing verification,
  and review readiness still needing verification.
- A parallel run while the brief command was still executing reported the brief
  missing. That is acceptable as a dogfooding finding, but release guidance
  should prefer sequential refresh, brief, verification, then commit-prep.

### Worktree Adoption

- Branch-search candidate selection and rejection stayed explicit, with reasons
  retained for both candidates.
- Adoption preview disclosed the missing materialized session, missing candidate
  diff inventory, missing verification summary, and absent worktree state before
  confirmation.
- Confirmed adoption recorded changeset evidence only and repeated the
  non-mutation boundary for merge, commit, push, and PR actions.

### Topology Recommendations

- The mixed frontend/docs/runtime recommendation pass correctly mapped the
  dashboard path to dashboard eval cases, frontend recipe commands, advisory
  profile, and release-candidate long-run cockpit evidence.
- The docs path matched the docs-only recipe.
- `src/glassbox/runtime/changesets.py` was unmatched, so v12 changeset runtime
  files need a future impact-rule follow-up if we want topology recommendations
  to cover changeset internals directly.

### Command Evidence

- The changeset detail and review brief both reported that no retained command
  evidence matched the dogfooding session. That was accurate because these
  commands were run by the operator around the session, not through retained
  model-loop command events.
- This is an important boundary for v12 release notes: command evidence is
  durable when command attempts flow through Glassbox session instrumentation,
  not for every shell command a developer runs manually.

### Dashboard Review

- No live dashboard browser pass was run for GBX-1292. Dashboard review remains
  covered by deterministic frontend tests, v12 changeset console tests, and the
  v12 release gate; live dashboard evidence should stay advisory for the
  release-candidate guide.

### Release Evidence

- The v12 release-gate dry run from GBX-1291 and this dogfooding database now
  give the release-candidate guide both automated and real-operator evidence.
- Provider canaries were not run during this pass. Provider evidence remains
  optional and advisory.

## Disposition

The dogfooding pass found two actionable follow-up candidates but no v12 release
blocker:

- Add or tune eval impact rules for v12 changeset runtime internals such as
  `src/glassbox/runtime/changesets.py`.
- Make release guidance prefer the sequential review order:
  `changeset refresh`, `changeset brief`, `changeset verification-plan`,
  validation commands, then `changeset commit-prep`.

The remaining observations are bounded evidence limits, not release blockers:

- branch-candidate adoption can record selected-candidate evidence even when the
  candidate has no materialized session, retained diff inventory, or verification
  summary, as long as the preview states those limitations
- command evidence is absent for manual shell commands outside retained
  Glassbox command-attempt instrumentation
- live dashboard and provider evidence were not collected in this pass
