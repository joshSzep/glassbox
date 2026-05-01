# Glassbox v12 Change Lifecycle Audit

This audit grounds v12 in the current implementation gap between inspecting a
session and reviewing the resulting local change. It follows the v12 contract in
[v12-reviewable-change-contract.md](./v12-reviewable-change-contract.md) and
classifies each finding as fixed in v12, evidence-only in v12, accepted
non-goal, or carried-forward risk.

## Summary

Glassbox already records many ingredients needed for review: git status, diff
summaries, task checkpoints, verification ledgers, branch-search decision
support, retained artifacts, handoff exports, policy decisions, and dashboard
inspection surfaces. Those ingredients are still mostly session-oriented. They
do not yet form one durable changeset with intent, provenance, freshness,
verification posture, residual risk, and commit-readiness state.

The v12 implementation should keep projections and dashboard summaries
non-authoritative. Canonical events and managed artifacts should remain the
source of truth, while changeset projections, review briefs, and dashboard
panels stay rebuildable views over that evidence.

## Classification Legend

- **Fixed in v12**: the task graph should add product behavior, durable state,
  tests, and docs.
- **Evidence-only in v12**: the task graph should improve retained evidence or
  review visibility without claiming full product automation.
- **Accepted non-goal**: the behavior remains intentionally outside v12.
- **Carried-forward risk**: the gap remains visible after v12 unless a later
  task graph accepts it.

## Audit Entries

| Surface | Current Evidence | Reviewable-Change Gap | v12 Disposition |
| --- | --- | --- | --- |
| Workspace diff summary | `workspace_diff_summary` is a read-only tool that reports per-file kind, insertions, deletions, generated/test/docs/policy-sensitive flags, untracked files, and a summary-only artifact contract ([src/glassbox/tools/workflow.py:253](../src/glassbox/tools/workflow.py#L253), [src/glassbox/tools/workflow.py:315](../src/glassbox/tools/workflow.py#L315), [src/glassbox/tools/workflow.py:542](../src/glassbox/tools/workflow.py#L542)). Large summaries are persisted as managed artifacts during turn execution ([src/glassbox/runtime/turn_artifacts.py:40](../src/glassbox/runtime/turn_artifacts.py#L40)). | The summary is tool output or artifact evidence, not a durable changeset inventory. It lacks changeset id, source attachment, refresh history, stale/previous inventory handling, and file-level provenance beyond current git state. | **Fixed in v12** by GBX-1220 through GBX-1223. Inventory should build on this tool but record explicit changeset artifact schema, provenance confidence, risk, sensitivity, and freshness. |
| Git status | `git_status` returns branch, ahead/behind, staged, modified, untracked, clean, and error fields from `git status --porcelain=v1 -b` ([src/glassbox/tools/workflow.py:43](../src/glassbox/tools/workflow.py#L43), [src/glassbox/tools/workflow.py:86](../src/glassbox/tools/workflow.py#L86), [src/glassbox/tools/workflow.py:117](../src/glassbox/tools/workflow.py#L117)). | The tool is useful for inspection, but no changeset snapshot records staged/unstaged ambiguity, untracked risk, or whether a readiness decision was based on the current status. | **Fixed in v12** by GBX-1212, GBX-1223, and GBX-1250. Changeset creation and refresh should capture dirty-workspace posture without staging or committing. |
| Branch search | Branch-search projections store searches and candidates ([src/glassbox/store/sqlite_schema_branch_search.py:10](../src/glassbox/store/sqlite_schema_branch_search.py#L10)). Decision support is explicit that branch search does not automatically merge or mutate parent history ([src/glassbox/runtime/branch_decision_support.py:30](../src/glassbox/runtime/branch_decision_support.py#L30)). It can include evidence, risk, cost, accepted risks, and verification recommendations when changed files are supplied ([src/glassbox/runtime/branch_decision_support.py:72](../src/glassbox/runtime/branch_decision_support.py#L72)). | Candidate changed-file evidence is not retained in current branch-search projections by default. The API currently returns empty changed files for candidate rows ([src/glassbox/web/branch_search_api.py:181](../src/glassbox/web/branch_search_api.py#L181)), and the fallback copy says to inspect the candidate session before merging work ([src/glassbox/runtime/branch_decision_files.py:4](../src/glassbox/runtime/branch_decision_files.py#L4)). | **Fixed in v12** by GBX-1212 and GBX-1262. Candidate adoption should preview inventory, conflicts, verification, risk, and stale evidence, then link the selected candidate to a changeset only after explicit operator confirmation. Automatic merge stays an **accepted non-goal**. |
| Task checkpoints | `TaskCheckpointCreated` records objective, phase, completed step, next action, recovery guidance, blockers, touched files, verification/budget status, source event range, and artifact id ([src/glassbox/core/events.py:858](../src/glassbox/core/events.py#L858)). The checkpoint projection rebuilds these fields ([src/glassbox/store/sqlite_projection_checkpoints.py:10](../src/glassbox/store/sqlite_projection_checkpoints.py#L10)), and checkpoint resume detects stale, failed, blocked, or workspace-drifted checkpoints ([src/glassbox/runtime/checkpoints.py:10](../src/glassbox/runtime/checkpoints.py#L10)). | Checkpoints are task/session continuation evidence, not reviewable change records. Touched files are useful but bounded, checkpoint-scoped, and not equivalent to a complete diff inventory or provenance map. | **Evidence-only in v12** for continuation context, with **fixed in v12** linkage through GBX-1212 and GBX-1221. Changesets may cite checkpoints but must not treat checkpoint touched files as complete inventory. |
| Verification recommendations and ledger | `glassbox eval recommend` derives recommendations from touched paths, eval cases, profiles, impact rules, and recipes ([src/glassbox/runtime/eval_recommendation_engine.py:55](../src/glassbox/runtime/eval_recommendation_engine.py#L55)). Task verification projection records planned, started, completed, failed, skipped, and accepted-risk evidence with commands and changed paths ([tests/integration/test_sqlite_projections.py:789](../tests/integration/test_sqlite_projections.py#L789)). Read-time drift compares ledger paths to current git changes ([src/glassbox/runtime/verification_drift.py:74](../src/glassbox/runtime/verification_drift.py#L74)). | Recommendations are path-aware, and ledgers are task-aware, but neither derives a single changeset readiness posture that distinguishes missing, stale, failed, skipped, accepted-risk, not-applicable, and fresh evidence for one local change. | **Fixed in v12** by GBX-1230 through GBX-1233. Changeset readiness should use existing recommendations and ledgers while preserving their original semantics. |
| Handoff summaries | Session export builds a portable handoff payload from snapshot, events, checkpoints, task details, compactions, branch-search summaries, and knowledge posture ([src/glassbox/runtime/session_export_package.py:88](../src/glassbox/runtime/session_export_package.py#L88)). Handoff summary names objective, checkpoint posture, compaction posture, verification state, risks, pending actions, branch lineage, knowledge posture, and safe inspection commands ([src/glassbox/runtime/session_export_handoff.py:66](../src/glassbox/runtime/session_export_handoff.py#L66)). | The handoff tells the story of a session. Reviewers usually need the story of the change: objective, changed files, provenance, verification freshness, branch rationale, risks, non-claims, and safe inspection commands centered on the changeset. | **Fixed in v12** by GBX-1240 through GBX-1243. Existing handoff stays useful context but should not be the primary review brief. |
| Tool output artifacts | Tool artifacts record kind, path, sha256, and size ([src/glassbox/core/events.py:278](../src/glassbox/core/events.py#L278)). Command-like tool output artifacts retain stdout/stderr, final/partial status, truncation, selected execution fields, and redaction posture ([src/glassbox/runtime/turn_artifacts.py:84](../src/glassbox/runtime/turn_artifacts.py#L84)). | Output is retained, but command purpose, review relevance, environment/toolchain posture, dependency drift, and publish/destructive classification are not unified as changeset evidence. Raw stdout/stderr can be too much or too little without a review summary. | **Fixed in v12** by GBX-1280 through GBX-1283. Review briefs should cite summarized command evidence and artifact references, not flatten large logs. |
| Command execution and policy | Tool calls and starts retain policy outcome, risk level, source label, reason, and trace ([src/glassbox/core/events.py:243](../src/glassbox/core/events.py#L243), [src/glassbox/core/events.py:257](../src/glassbox/core/events.py#L257)). Session exports include redacted policy decisions from tool request, tool start, and approval events ([src/glassbox/runtime/session_export_manifest.py:82](../src/glassbox/runtime/session_export_manifest.py#L82)). | Policy evidence explains why a command was allowed or gated, but review-bound workflows do not yet classify whether a command was inspect, test, lint, typecheck, build, package, eval, publish, deploy, cleanup, dangerous, or unknown. | **Fixed in v12** by GBX-1280 and GBX-1282. Unknown or publish/deploy/destructive commands should not count as verification proof without explicit policy posture. |
| Dashboard review surfaces | The dashboard routes to sessions, tasks, memory, repository index, and branch-search surfaces ([frontend/routing/app-route.ts:125](../frontend/routing/app-route.ts#L125)). The top-level console selects task, knowledge, branch-search, or session overview/inspector surfaces ([frontend/components/console/workspace-console.tsx:57](../frontend/components/console/workspace-console.tsx#L57)). Branch-search candidate evidence displays changed-file summaries, retained evidence, posture, recommendations, accepted risks, and follow-up action when available ([frontend/components/console/branch-search/evidence.tsx:35](../frontend/components/console/branch-search/evidence.tsx#L35)). | There is no focused "review this change" route or panel. Review evidence is scattered across sessions, tasks, branch-search, knowledge, and artifacts, so reviewers must reconstruct the change manually. | **Fixed in v12** by GBX-1213, GBX-1233, GBX-1242, GBX-1253, GBX-1263, GBX-1273, and GBX-1283. Dashboard changeset review should stay dense and evidence-first. |
| Export and redaction | Session export redacts transcript text, artifact paths, task evidence, checkpoint payloads, and policy decisions ([src/glassbox/runtime/session_export_manifest.py:37](../src/glassbox/runtime/session_export_manifest.py#L37), [src/glassbox/runtime/session_export_manifest.py:241](../src/glassbox/runtime/session_export_manifest.py#L241), [src/glassbox/runtime/session_export_manifest.py:270](../src/glassbox/runtime/session_export_manifest.py#L270)). Import validation rejects packages that appear to contain unredacted secret material ([src/glassbox/runtime/session_import_validation.py:19](../src/glassbox/runtime/session_import_validation.py#L19)). | Redaction exists for session handoff packages, but there is no changeset-centered export with brief, inventory, verification summary, selected artifacts, redaction report, and non-claims. | **Fixed in v12** by GBX-1243. Raw `.glassbox` database state remains an **accepted non-goal** for reviewer handoff. |

## Test Inventory

Current coverage is strongest around individual ingredients:

- Git status and workspace diff summaries are covered in
  [tests/integration/test_workflow_tools.py:84](../tests/integration/test_workflow_tools.py#L84)
  and
  [tests/integration/test_workflow_tools.py:176](../tests/integration/test_workflow_tools.py#L176),
  including artifact payload behavior at
  [tests/integration/test_workflow_tools.py:263](../tests/integration/test_workflow_tools.py#L263).
- Branch-search decision support covers non-automatic-merge copy, missing
  changed-file evidence, and changed-file recommendation routing in
  [tests/unit/test_branch_search.py:131](../tests/unit/test_branch_search.py#L131)
  and [tests/unit/test_branch_search.py:156](../tests/unit/test_branch_search.py#L156).
- Checkpoint projection rebuild and touched-file retention are covered in
  [tests/integration/test_sqlite_projections.py:300](../tests/integration/test_sqlite_projections.py#L300).
- Verification ledger rebuild, changed paths, failures, and accepted risks are
  covered in
  [tests/integration/test_sqlite_projections.py:789](../tests/integration/test_sqlite_projections.py#L789).
- Verification drift fresh, stale, docs-only, and generated states are covered
  in [tests/unit/test_verification_drift.py:18](../tests/unit/test_verification_drift.py#L18).
- Session export checkpoint portability and v11 handoff summaries are covered
  in
  [tests/integration/test_cli_session_export.py:430](../tests/integration/test_cli_session_export.py#L430)
  and
  [tests/integration/test_cli_session_export.py:507](../tests/integration/test_cli_session_export.py#L507).
- Session export redaction of workspace paths, secret-like tokens, nested JSON,
  artifact paths, approvals, and checkpoints is covered in
  [tests/unit/test_session_export_redaction.py:25](../tests/unit/test_session_export_redaction.py#L25).

Missing coverage that v12 should add:

- changeset event payload and replay normalization tests
- changeset projection migration, rebuild, and repository adapter tests
- creation tests for session, task, branch-search candidate, and workspace-diff
  sources
- change inventory artifact schema, size-limit, redaction, provenance, risk,
  and refresh/staleness tests
- changeset verification readiness and stale-verification tests across
  inventory refreshes
- deterministic review brief generation and export package tests
- commit readiness and commit-message suggestion tests that prove no staging or
  commit occurs
- worktree isolation, cleanup confirmation, conflict, degraded-state, and
  candidate-adoption tests
- topology fixture tests for Python-only, frontend-only, and mixed workspaces
- command purpose, environment redaction, toolchain drift, and
  publish/destructive guardrail tests
- dashboard changeset route, store, component, responsive, keyboard, and
  Playwright review-flow tests

## Disposition

Every known gap between current session evidence and reviewable local changes
has a v12 disposition:

- Durable changesets and projections: fixed in GBX-1210 through GBX-1213.
- Inventory, provenance, risk, and freshness: fixed in GBX-1220 through
  GBX-1223.
- Verification readiness: fixed in GBX-1230 through GBX-1233.
- Review briefs and exports: fixed in GBX-1240 through GBX-1243.
- Commit readiness: fixed in GBX-1250 through GBX-1253.
- Worktree isolation and candidate adoption: fixed in GBX-1260 through
  GBX-1263, while automatic merge remains an accepted non-goal.
- Monorepo topology: fixed in GBX-1270 through GBX-1273.
- Command evidence and policy hardening: fixed in GBX-1280 through GBX-1283.
- Hosted review, automatic PRs, automatic commits, automatic pushes,
  automatic branch-search merging, remote worker fleets, and indefinite
  unattended mutation: accepted non-goals.

No product-code change is required by this audit. The next implementation task
can safely standardize vocabulary before introducing the changeset event model.
