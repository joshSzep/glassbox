# Glassbox v13 Review Loop Audit

This audit grounds v13 in the gap between the completed v12 reviewable-change
model and the review-loop needs defined in
[v13-review-loop-contract.md](./v13-review-loop-contract.md). It classifies
each finding as fixed in v13, evidence-only in v13, accepted non-goal, or
carried-forward risk.

## Summary

Glassbox v12 can create local changesets, refresh change inventory, derive
verification readiness, generate reviewer-safe review briefs, prepare commit
guidance, adopt selected branch-search candidates as evidence, summarize
topology impacts, classify command evidence, show changesets in the dashboard,
and export reviewer-safe evidence packages.

Those surfaces are still centered on initial reviewability. They do not yet
retain the review feedback that follows, the fixup responses made after that
feedback, manual evidence from outside retained Glassbox instrumentation,
browser or accessibility walkthrough notes, lifecycle summaries, or final
handoff posture. A reviewer can inspect the v12 change, but Glassbox cannot yet
explain how the local change survived review.

## Classification Legend

- **Fixed in v13**: the task graph should add durable product behavior,
  source-of-truth events or artifacts, tests, and docs.
- **Evidence-only in v13**: the task graph should improve retained evidence or
  review visibility without claiming full product automation.
- **Accepted non-goal**: the behavior remains intentionally outside v13.
- **Carried-forward risk**: the gap remains visible after v13 unless a later
  task graph accepts it.

## Audit Entries

| Surface | Current Evidence | Review-Loop Gap | v13 Disposition |
| --- | --- | --- | --- |
| Changeset creation | v12 canonical events cover changeset creation, source attachment, inventory refresh, verification posture, review brief creation, readiness, candidate adoption, and archive ([src/glassbox/core/events.py:1014](../src/glassbox/core/events.py#L1014)). The runtime query view gathers changeset, source, inventory, verification, review brief, readiness, and command evidence rows for one detail view ([src/glassbox/runtime/changesets.py:238](../src/glassbox/runtime/changesets.py#L238)). CLI creation supports session, task, branch-candidate, and workspace-diff sources ([src/glassbox/cli/parser_changesets.py:23](../src/glassbox/cli/parser_changesets.py#L23)). | The source object is ready for initial review, but there are no review feedback records, feedback scopes, disposition updates, reopenings, response links, or risk-acceptance records tied to feedback. | **Fixed in v13** by GBX-1310 through GBX-1312. The v13 event vocabulary should add feedback as local evidence while preserving changesets as local evidence objects, not hosted review state. |
| Review briefs | The v12 brief artifact is deterministic, reviewer-safe, redacted, and explicitly excludes raw command output, provider transcripts, raw diffs, and file contents ([src/glassbox/runtime/review_briefs.py:80](../src/glassbox/runtime/review_briefs.py#L80)). Markdown rendering includes objective, inventory, provenance, verification, command evidence, risks, reviewer checklist, safe inspection commands, non-claims, and limitations ([src/glassbox/runtime/review_briefs.py:155](../src/glassbox/runtime/review_briefs.py#L155)). | Briefs summarize initial changeset evidence. They do not yet include feedback threads, fixup responses, manual evidence, browser or accessibility evidence, lifecycle chronology, unresolved questions, accepted review risks, or publication-boundary posture. | **Fixed in v13** by GBX-1360 and GBX-1361. Lifecycle briefs should cite retained evidence references instead of flattening logs, screenshots, diffs, or model memory. |
| Verification readiness | Changeset verification readiness aggregates inventory freshness, eval recommendations, workspace profile defaults, task verification ledger records, command evidence, missing checks, stale checks, failures, and accepted risk ([src/glassbox/runtime/changeset_verification_readiness.py:60](../src/glassbox/runtime/changeset_verification_readiness.py#L60)). Its non-claims say readiness is advisory and recommended commands are previews ([src/glassbox/runtime/changeset_verification_readiness.py:179](../src/glassbox/runtime/changeset_verification_readiness.py#L179)). | Readiness can become stale after review-driven fixups, but v12 does not connect a fixup response or feedback disposition to the inventory sequence that made previous checks stale. Manual evidence also cannot currently be used as a visible limitation beside readiness. | **Fixed in v13** by GBX-1350 and GBX-1351. Verification guidance should explain stale response evidence and recommended safe commands without treating manual-only evidence as retained command proof. |
| Commit preparation | Commit readiness derives a read-only assessment from changeset detail, inventory status, verification plan, review briefs, readiness records, git status, workspace diff, and staged diff ([src/glassbox/runtime/commit_readiness.py:100](../src/glassbox/runtime/commit_readiness.py#L100), [src/glassbox/runtime/commit_readiness.py:137](../src/glassbox/runtime/commit_readiness.py#L137)). It explicitly does not stage or run `git commit` ([src/glassbox/runtime/commit_readiness.py:194](../src/glassbox/runtime/commit_readiness.py#L194)). | Commit readiness does not yet account for unresolved review feedback, stale fixup verification, manual evidence limitations, missing lifecycle brief, accepted review risk, or handoff readiness. | **Fixed in v13** by GBX-1370 through GBX-1372. Commit preparation should build on handoff readiness while preserving the no-mutation boundary. |
| Manual command evidence | Command evidence classifies retained Glassbox command attempts by purpose, review relevance, verification support, and reason ([src/glassbox/runtime/command_evidence.py:51](../src/glassbox/runtime/command_evidence.py#L51)). Review-relevant commands can retain bounded environment and toolchain evidence with redaction notes ([src/glassbox/runtime/command_evidence.py:104](../src/glassbox/runtime/command_evidence.py#L104)). | Shell commands run outside retained Glassbox instrumentation, reviewer notes, external CI results, sanitized logs, and screenshots do not have an explicit attachment path. If they are copied into prose, they can be mistaken for Glassbox-run command evidence. | **Fixed in v13** by GBX-1330 through GBX-1332. Manual evidence must be labeled manual or external, cite source and redaction posture, and never backfill retained command evidence. |
| Branch-candidate adoption | Adoption preview summarizes selected state, changed files, verification posture, risk posture, accepted risks, conflicts, stale evidence, limitations, safe next actions, worktree state, and non-claims without workspace mutation ([src/glassbox/runtime/branch_candidate_adoption.py:38](../src/glassbox/runtime/branch_candidate_adoption.py#L38), [src/glassbox/runtime/branch_candidate_adoption.py:79](../src/glassbox/runtime/branch_candidate_adoption.py#L79)). Adoption records selected candidate evidence without merge, rebase, cherry-pick, stage, commit, push, or PR automation ([src/glassbox/runtime/branch_candidate_adoption.py:143](../src/glassbox/runtime/branch_candidate_adoption.py#L143)). | Candidate adoption can explain the chosen candidate, but it cannot retain later reviewer feedback on that candidate, fixup responses after adoption, or review-loop risk acceptance. | **Evidence-only in v13** for candidate context, with **fixed in v13** feedback/response linkage through GBX-1310 and GBX-1321. Automatic merge remains an **accepted non-goal**. |
| Topology recommendations | Changeset topology impact derives affected components, matched paths, test roots, ownership hints, dependency hints, freshness, recommendation posture, and stale-topology limitations from local topology snapshots ([src/glassbox/runtime/changeset_topology.py:17](../src/glassbox/runtime/changeset_topology.py#L17), [src/glassbox/runtime/changeset_topology.py:35](../src/glassbox/runtime/changeset_topology.py#L35)). | Topology helps select verification, but v12 dogfooding found runtime changeset internals that lacked direct impact-rule mapping. Missing or stale topology lowers confidence but does not yet drive review-loop stale-response recommendations. | **Fixed in v13** by GBX-1350 and GBX-1351 where impact-rule coverage exists; missing mappings remain a **carried-forward risk** unless deterministic rules are added. |
| Dashboard review | The dashboard has a changeset console that lists local changesets, shows risk, inventory freshness, verification, unresolved risk count, review brief actions, inventory, topology, verification, command evidence, commit preparation, candidate adoption, brief artifacts, and sources ([frontend/components/console/changeset-console.tsx:27](../frontend/components/console/changeset-console.tsx#L27), [frontend/components/console/changeset-console.tsx:153](../frontend/components/console/changeset-console.tsx#L153)). | The dashboard does not yet have a review-loop inbox, feedback detail, response history, manual evidence panel, browser or accessibility evidence panel, lifecycle brief status, or handoff readiness panel. | **Fixed in v13** across GBX-1312, GBX-1322, GBX-1332, GBX-1342, GBX-1361, GBX-1371, and GBX-1382. Live dashboard evidence stays advisory unless fixture-backed tests promote a stable contract. |
| TUI slash commands | The terminal command registry currently exposes status, dashboard, copy, artifact, details, markdown, latest, approve, deny, answer, interrupt, clear, quit, and related slash aliases ([src/glassbox/cli/tui/commands.py:12](../src/glassbox/cli/tui/commands.py#L12), [src/glassbox/cli/tui/commands.py:46](../src/glassbox/cli/tui/commands.py#L46)). | There is no in-session slash command or command-palette action for changeset creation, review-loop feedback capture, manual evidence attachment, lifecycle brief generation, verification preview, or handoff posture. Operators must leave chat and run separate `glassbox changeset ...` commands. | **Fixed in v13** by GBX-1380 through GBX-1382, intentionally late after dogfooding decides the vocabulary and primary verb. |
| Exports | The v12 changeset export package summarizes changeset, sources, inventory, verification readiness, latest review brief, readiness rows, artifact references, redaction report, non-claims, and safe inspection commands ([src/glassbox/runtime/changeset_export.py:40](../src/glassbox/runtime/changeset_export.py#L40), [src/glassbox/runtime/changeset_export.py:92](../src/glassbox/runtime/changeset_export.py#L92)). It omits raw `.glassbox` database state, raw command output, raw provider transcripts, raw diffs, and raw file contents ([src/glassbox/runtime/changeset_export.py:123](../src/glassbox/runtime/changeset_export.py#L123)). | Exports do not yet include review-loop feedback summaries, response summaries, manual evidence summaries, browser/accessibility summaries, lifecycle brief posture, handoff readiness, or review-loop non-claims. | **Fixed in v13** by GBX-1362. Raw `.glassbox` state, raw screenshots, raw logs, raw provider transcripts, and automatic publication remain **accepted non-goals** for reviewer-safe export. |

## Test Inventory

Current v12 coverage is strongest around initial reviewability:

- Changeset event payload round trips and event type normalization are covered
  in [tests/unit/test_core_events.py:792](../tests/unit/test_core_events.py#L792).
- Changeset projection rebuild, latest inventory, verification posture, review
  brief, readiness, and superseded inventory behavior are covered in
  [tests/integration/test_changeset_projection.py:67](../tests/integration/test_changeset_projection.py#L67)
  and
  [tests/integration/test_changeset_projection.py:250](../tests/integration/test_changeset_projection.py#L250).
- Review brief artifact generation and redaction are covered in
  [tests/unit/test_review_briefs.py:89](../tests/unit/test_review_briefs.py#L89).
- Changeset verification readiness states are covered in
  [tests/unit/test_changeset_verification_readiness.py:35](../tests/unit/test_changeset_verification_readiness.py#L35).
- Commit readiness advisory behavior is covered in
  [tests/unit/test_commit_readiness.py:1](../tests/unit/test_commit_readiness.py#L1).
- CLI changeset creation, refresh, brief, verification, commit-prep, export,
  and adoption paths are covered in
  [tests/integration/test_cli_changeset_commands.py:1](../tests/integration/test_cli_changeset_commands.py#L1).
- Web changeset routes are covered in
  [tests/integration/test_web_changeset_routes.py:1](../tests/integration/test_web_changeset_routes.py#L1).
- Dashboard changeset store and component behavior are covered in
  [frontend/tests/dashboard-stores.test.ts:790](../frontend/tests/dashboard-stores.test.ts#L790)
  and
  [frontend/tests/changeset-console.test.tsx:1](../frontend/tests/changeset-console.test.tsx#L1).

Missing coverage that v13 should add:

- review feedback event payload, replay normalization, and correlation tests
- review feedback projection rebuild, query service, CLI, API, dashboard, and
  generated-type tests
- response/fixup inventory-delta tests that connect requested changes to
  changed inventory and stale verification
- manual evidence attachment tests for source, scope, redaction, local-only
  posture, size limits, and non-claims
- browser, dashboard, and accessibility evidence tests for advisory retention,
  skipped cases, and local-only references
- verification readiness tests for review-driven fixups, stale response
  evidence, manual-only evidence limitations, and topology mapping gaps
- lifecycle brief and export tests that include resolved and unresolved
  feedback, responses, manual evidence, browser/accessibility evidence, stale
  verification, accepted risks, and handoff posture
- publication-boundary and handoff readiness tests that prove no staging,
  commit, push, PR, merge, deploy, or package publication occurs
- TUI slash-command, plain interactive, command guide, dashboard quick-action,
  and route tests for review-loop entry points
- deterministic replay/eval cases for stable review-loop behavior and negative
  cases for approval or publication non-claims

## Disposition

Every known gap between v12 reviewable local changes and v13 review-loop
evidence has a disposition:

- Local review feedback: fixed in GBX-1310 through GBX-1312.
- Fixup responses and feedback disposition: fixed in GBX-1320 through
  GBX-1322.
- Manual evidence inbox: fixed in GBX-1330 through GBX-1332.
- Browser, dashboard, and accessibility evidence: fixed in GBX-1340 through
  GBX-1342 as advisory evidence.
- Review-driven stale verification and topology recommendations: fixed in
  GBX-1350 through GBX-1351 where deterministic signals exist; incomplete
  impact-rule coverage remains a carried-forward risk.
- Lifecycle briefs and reviewer-safe exports: fixed in GBX-1360 through
  GBX-1362.
- Publication boundary, handoff readiness, and commit-prep context: fixed in
  GBX-1370 through GBX-1372.
- Integrated review-loop UX: fixed in GBX-1380 through GBX-1382 after
  dogfooding.
- Deterministic evals, release gate, dogfooding, and release-candidate signoff:
  fixed in GBX-1390 through GBX-1393.
- Hosted code review, hosted review synchronization, automatic approval,
  automatic staging, automatic commits, automatic pushes, automatic PRs,
  automatic merges, deploys, package publishing, remote worker fleets, and
  indefinite unattended mutation: accepted non-goals.

No product-code change is required by this audit. The next implementation task
can safely standardize v13 vocabulary before introducing review feedback event
families.
