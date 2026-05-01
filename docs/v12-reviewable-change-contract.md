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
