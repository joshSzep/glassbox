# Glassbox v12 Reviewable Change Contract

This page defines the v12 product contract for evolving the v11 confidence and
adoption milestone into a reviewable local change lifecycle.

v12 does not make Glassbox more automatic for its own sake. It turns local
agent work into an engineering artifact that a reviewer can inspect: what
changed, why it changed, where the evidence came from, what verification is
fresh or stale, what risks remain, and whether the change is ready to review or
prepare for commit.

## Scope

Glassbox v12 focuses on reviewable local changes:

- create explicit local changesets from sessions, tasks, branch-search
  candidates, and the current workspace diff
- connect changed files to source events, task steps, tool attempts,
  branch-search candidates, verification records, compactions, artifacts, and
  accepted risks when those signals exist
- record structured change inventories with provenance, sensitivity, stale
  evidence, generated/test/docs classification, and redaction posture
- derive verification readiness from changed paths, verification ledgers,
  repository recipes, eval recommendations, command evidence, and freshness
- generate reviewer-safe briefs and export packages from retained local
  evidence rather than hidden model memory
- explain commit readiness with local evidence before an operator chooses any
  git mutation
- support temporary local worktree isolation and explicit branch-candidate
  adoption without automatic merging
- make monorepo topology and path-aware verification recommendations more
  precise while preserving source files and manifests as the authority
- harden command evidence, purpose classification, environment redaction, and
  publish/destructive guardrails for review-bound work
- add deterministic replay, eval, and release-gate coverage for the stable
  reviewable-change contracts

The primary creation surface remains `glassbox session chat`. The dashboard is
the paired review and evidence surface for inspecting changesets, review
briefs, verification posture, risk, topology, and command evidence.

## Product Model

A v12 change is a local evidence object, not a remote collaboration primitive.
Canonical events and managed artifacts are the source of truth; projections,
dashboard panels, and summaries are rebuildable views over that evidence.

The supported local lifecycle is:

1. An operator runs ordinary local work in a session, task, branch-search
   candidate, temporary worktree, or existing workspace.
2. The operator explicitly creates a changeset from that source.
3. Glassbox records source references and a structured change inventory without
   staging, committing, pushing, opening a pull request, or merging.
4. The operator refreshes inventory, reviews provenance, and inspects any
   unknown or externally modified files.
5. Glassbox derives verification readiness and names safe inspection or
   verification commands for missing, stale, failed, skipped, or accepted-risk
   evidence.
6. The operator generates a review brief or export package that cites retained
   evidence and labels local-only material.
7. Glassbox explains commit readiness and may suggest a commit message, but the
   operator performs any final git action outside the changeset evidence model.

## Vocabulary

Use these terms consistently in CLI help, dashboard copy, API descriptions,
docs, tests, and release evidence.

| Term | Operator meaning | Command and dashboard shape |
| --- | --- | --- |
| Changeset | A local evidence object for one reviewable change. It has an id, objective, source references, inventory, verification posture, risks, review briefs, and readiness state. | Use `glassbox changeset ...` for explicit creation and inspection. Do not use "changeset" as a synonym for a git commit, branch, pull request, or session. |
| Change inventory | The structured file-level summary attached to a changeset. It describes paths, change kind, size, generated/test/docs posture, binary posture, staged/unstaged state, sensitivity, provenance, and freshness. | Use "inventory" for the artifact-backed review summary. Use "diff" only when referring to git output or raw patch data. |
| Review brief | A reviewer-safe Markdown or JSON artifact generated from one changeset's retained evidence. | Use "generate review brief" or "refresh review brief". Do not call it a PR description unless a future task adds explicit PR integration. |
| Verification readiness | The current evidence posture for checks that should support review. It can include planned, missing, running, passed, failed, stale, skipped, accepted-with-risk, and not-applicable states. | Use "verification readiness" for review posture. Use "verification passed" only for a specific fresh check. |
| Commit readiness | Advisory local evidence about whether a changeset appears ready for an operator to commit. It can be ready, blocked, needs-verification, needs-review, stale-inventory, dirty-untracked-risk, failed-checks, missing-provenance, or accepted-with-risk. | Use "prepare commit" or "commit readiness". Never say Glassbox committed, staged, pushed, opened a PR, or merged unless the operator performed that separate action. |
| Adopted candidate | A branch-search candidate that an operator explicitly chose to connect to a changeset after previewing evidence. | Use "adopt candidate into a changeset". Do not say "merge candidate" unless an actual git merge workflow exists and is separately confirmed. |
| Residual risk | A named uncertainty, stale signal, failed/skipped check, accepted risk, missing provenance, or degraded evidence item that remains visible during review. | Put residual risks beside readiness and verification summaries, not below optimistic success copy. |
| Reviewer-safe evidence | Redacted, portable, bounded evidence intended for another human to inspect without raw `.glassbox` state. | Review briefs and changeset exports use this phrase. They cite evidence references instead of embedding raw databases or huge logs. |
| Local-only evidence | Evidence that is useful on the current machine but not safe or portable enough to hand to a reviewer unchanged. | Label local-only paths, artifacts, provider outputs, environment details, and browser evidence explicitly. |

The v12 vocabulary builds on the v9 nouns in
[v9-vocabulary.md](./v9-vocabulary.md). Keep these distinctions clear:

- A **git branch** is repository history.
- A **session branch** is a child Glassbox session derived from existing
  session history.
- A **branch-search candidate** is bounded local decision-support evidence for
  a strategy.
- A **changeset** is reviewable local change evidence. It may cite a git
  branch, session branch, or branch-search candidate, but it is not any of
  those objects.

## Supported Workflow Set

v12 supports these operator workflows:

- create, list, inspect, refresh, archive, and export local changesets
- inspect a change inventory with file kind, staged/unstaged state, generated
  posture, binary posture, sensitive-path posture, and provenance confidence
- distinguish direct, inferred, and unknown file provenance without claiming
  ownership of unrecorded manual edits
- review path-based risk and sensitivity classifications as advisory evidence
- preview verification plans before running arbitrary commands
- mark verification as fresh, stale, missing, failed, skipped,
  accepted-with-risk, or not applicable based on retained evidence
- generate deterministic Markdown and JSON review briefs from changeset
  evidence
- prepare for commit with advisory readiness states and deterministic commit
  message suggestions
- create and clean up temporary local worktrees with explicit confirmation and
  retained custody evidence
- adopt a selected branch-search candidate into a changeset through a preview
  and confirmation workflow, without automatic merge behavior
- inspect topology-aware affected packages, test roots, ownership hints, and
  recommendation confidence
- classify command evidence by purpose, policy posture, redacted environment,
  toolchain drift, and review relevance

Current implementation note: after GBX-1213, changesets are visible through
`glassbox changeset` / `glassbox changesets`, `/changesets` API routes, and the
dashboard `/app/changesets` shell. This first surface supports basic creation,
inspection, source refresh, and archival. Structured inventories, review briefs,
verification readiness, commit readiness, exports, topology, and command
evidence remain later v12 phases and must not be implied by the basic shell.
After GBX-1220, the summary-only `changeset_change_inventory` artifact shape is
defined in [change-inventory.md](./change-inventory.md), but refresh workflows
and provenance attachment remain later tasks.

## Evidence Expectations

v12 evidence is split into blocking deterministic release evidence and advisory
confidence evidence.

Blocking release evidence includes:

- typed event and payload tests for changeset vocabulary
- SQLite migration, projection rebuild, and repository adapter tests
- runtime and CLI tests for changeset creation, inventory refresh,
  verification readiness, review brief generation, commit readiness, worktree
  isolation, candidate adoption, topology, and command evidence classification
- API route tests and generated OpenAPI/frontend type freshness when web
  contracts change
- frontend component, store, route, and build validation when dashboard
  changeset or review surfaces change
- deterministic replay and eval fixtures promoted for stable
  reviewable-change behavior
- the v12 release gate once `scripts/validate_v12_release_gate.py` exists

Advisory confidence evidence includes:

- live dashboard review passes and screenshots retained under `.glassbox/`
- live provider evidence, provider diagnostics, and skipped-provider reasons
- operator dogfooding summaries from real local changes
- manual reviewer walkthroughs, accessibility pairings, and browser checks

Manual and live evidence must name non-claims. A browser review does not replace
deterministic dashboard tests, a provider run does not become release
authority, a dogfooding pass does not prove all repository shapes, and commit
readiness remains advisory local evidence rather than permission to mutate git.

## Release Authority

Deterministic replay, eval, package, migration, unit, integration, CLI, API,
frontend, and release-gate evidence are the blocking release authority for v12.

Live provider, live browser, accessibility, manual review, and dogfooding
evidence can strengthen confidence only when retained evidence names the
workflow, environment, date, skipped cases, and bounded claim. Those evidence
classes do not replace deterministic gates unless a future task promotes a
narrow fixture-backed contract with an explicit failure policy.

## Non-Goals

v12 deliberately does not introduce:

- hosted code review
- cloud workspace authority
- remote worker fleets
- simultaneous multi-writer mutation
- automatic commits
- automatic staging
- automatic pushes
- automatic pull request creation
- automatic branch-search merging
- automatic rebase, force-push, or history rewriting
- automatic provider failover as release authority
- hidden provider-side memory
- cross-repository memory sync
- indefinite unattended mutation

Glassbox may prepare evidence, guidance, brief artifacts, suggested commit
messages, and review summaries. It must not silently perform final git or
remote collaboration actions as part of the v12 changeset lifecycle.

## Safety Rules

- Safe inspection comes before mutation in terminal, API, and dashboard copy.
- Missing, degraded, stale, externally modified, or unknown evidence is visible
  instead of filled in with optimistic prose.
- Large or sensitive data lives in managed artifacts with redaction and size
  limits; canonical events should carry identifiers, summaries, and provenance,
  not raw diffs or raw logs.
- Reviewer-facing exports must avoid raw `.glassbox` database state and label
  local-only evidence clearly.
- Topology and ownership hints must carry provenance and freshness. Stale
  topology lowers confidence rather than becoming fact.
- Publish, deploy, package-upload, destructive cleanup, and git history
  rewriting commands remain policy-aware and cannot be treated as ordinary
  verification proof.

## Command And Dashboard Copy Guidelines

Use copy that describes evidence and operator choice:

- Prefer "create changeset from session/task/candidate/workspace diff" over
  "capture commit" or "prepare PR".
- Prefer "review brief generated" over "review approved".
- Prefer "commit readiness: needs verification" over "not committable".
- Prefer "safe next action: inspect inventory" before recommending any command
  that mutates files, git state, worktrees, or remotes.
- Prefer "candidate adopted into changeset" over "candidate merged".
- Prefer "verification evidence is stale" over "tests are invalid" unless a
  specific failed check proves that stronger claim.
- Prefer "local-only evidence" when paths, browser runs, provider outputs, or
  environment details should not be treated as portable reviewer artifacts.

Avoid copy that implies hidden automation or remote authority:

- Do not say Glassbox committed, staged, pushed, opened a PR, merged, rebased,
  deployed, or published unless that explicit action happened outside the
  changeset lifecycle.
- Do not describe readiness as proof. Readiness is an evidence-backed local
  posture, not a guarantee that the change is correct.
- Do not describe stale topology, missing provenance, or degraded projections
  as facts. Name the stale or missing evidence and the safe inspection command.
- Do not hide failed verification under a passing or optimistic summary.

## Related Documents

- [tasks-v12.md](./tasks-v12.md): v12 task graph and dependency order
- [v11-release-candidate.md](./v11-release-candidate.md): inherited v11 release
  posture and supported `0.10.0` operating model
- [v11-confidence-adoption-contract.md](./v11-confidence-adoption-contract.md):
  inherited confidence, adoption, and evidence contract
- [reviewer-evidence-bundles.md](./reviewer-evidence-bundles.md): current
  reviewer-safe handoff guidance before v12 changeset exports exist
- [branch-search.md](./branch-search.md): existing branch-search comparison
  workflow before v12 candidate adoption
- [verification-loops.md](./verification-loops.md): existing verification
  loop guidance that v12 changeset readiness builds on
