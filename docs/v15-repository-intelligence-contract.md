# Glassbox v15 Repository Intelligence V2 Contract

This page defines the v15 operator and contributor contract for repository
intelligence v2. It is the product boundary for the planning track in
[tasks-v15.md](./tasks-v15.md), after the v14 review-loop maturity milestone.

Repository intelligence v2 makes Glassbox less forgetful about the local
workspace. It should help operators understand repository structure,
verification habits, command recipes, ownership hints, generated outputs,
policy-sensitive paths, package boundaries, confirmed conventions, stale
evidence, and release-sensitive surfaces without turning those hints into
hidden memory or release authority.

The v15 contract builds on the v8
[auditable autonomy contract](./v8-auditable-autonomy-contract.md), the
current [repository intelligence index contract](./repository-intelligence-index.md),
[workspace topology contract](./workspace-topology.md),
[workspace memory contract](./workspace-memory.md), and
[runtime context contract](./runtime-context.md). Those contracts remain the
baseline for local-first authority, event-sourced state, review-gated memory,
bounded prompt context, replay visibility, and deterministic release evidence.

## Scope

Glassbox v15 focuses on repository intelligence v2:

- define a local, rebuildable, freshness-aware, provenance-backed snapshot
  model for repository intelligence
- enrich repository discovery with source roots, test roots, docs roots,
  package boundaries, dependency manifests, generated paths, ignored outputs,
  command recipes, ownership hints, subsystems, and release-sensitive surfaces
- connect repository intelligence to path-to-verification recommendations so
  changed paths can name likely tests, evals, command recipes, stale evidence,
  confidence, limitations, and safe next actions
- let confirmed active workspace memory enrich repository intelligence only
  when provenance, state, freshness, and prompt-use evidence remain visible
- expose stale, missing, degraded, conflicting, and partially rebuilt
  repository intelligence through CLI, API, dashboard, readiness,
  observability, changeset, review brief, handoff, and context surfaces
- add bounded repository intelligence context to model turns only when the
  included sources, freshness, confidence, limitations, budgets, and replay
  fingerprints are inspectable
- promote stable repository intelligence behavior into deterministic replay,
  eval, package, and release-gate evidence

v15 improves daily local repository awareness. It does not replace source
files, manifests, tests, eval fixtures, operator review, release gates, or
deterministic evidence.

## Vocabulary

| Term | Operator meaning | Boundary |
| --- | --- | --- |
| Repository intelligence | Local evidence and derived summaries about repository structure, commands, tests, docs, topology, ownership hints, generated paths, policy-sensitive paths, release posture, and confirmed conventions. | It is advisory by default and must cite provenance, freshness, confidence, and limitations. |
| Snapshot | A versioned managed artifact or rebuildable derived state that records repository intelligence for one workspace at one build time. | It is not the source of truth; it can be stale, missing, degraded, failed, or rebuilt. |
| Source manifest | A bounded record of local inputs used to build intelligence, such as manifests, docs, eval metadata, topology snapshots, command evidence, and confirmed memory IDs. | It should retain digests and provenance, not raw file contents or raw diffs by default. |
| Command recipe | A recommended local command shape with purpose, scope, risk, source, confidence, freshness, timeout hints, and review relevance. | It is not a permission grant and does not approve execution. Tool policy and operator approval still apply. |
| Ownership hint | A local advisory signal from docs, path conventions, CODEOWNERS-like files, manifests, eval metadata, topology, or confirmed memory. | It is not access control, reviewer assignment, review approval, or publication authority. |
| Path-to-verification recommendation | A bounded explanation of likely tests, evals, recipes, release gates, stale evidence, and safe next actions for changed paths. | It does not execute checks unless an explicit command or workflow does so. |
| Freshness posture | The visible state of intelligence, such as fresh, stale, missing, degraded, failed, conflicting, or partially rebuilt. | Stale or missing intelligence must lower confidence and name inspection or rebuild actions. |

## Supported Workflow Set

v15 should preserve the existing terminal-first Glassbox workflow while making
repository-aware work sharper:

1. An operator can rebuild and inspect repository intelligence locally.
2. The operator can inspect repository map summaries, affected subsystems,
   package boundaries, generated paths, dependency manifests, command recipes,
   owner hints, release-sensitive areas, and limitations.
3. Changed paths can produce explainable verification recommendations that
   start with the cheapest useful deterministic check when one exists.
4. Changesets, review briefs, and handoff readiness can show repository
   intelligence guidance beside deterministic verification posture.
5. The dashboard can act as a richer repository intelligence console while the
   TUI remains the primary conversational surface.
6. Confirmed active workspace memory can enrich repository intelligence, while
   candidates, stale entries, invalidated entries, imported-unreviewed entries,
   rejected candidates, and pruned entries stay out of active prompt context by
   default.
7. Live turns can receive bounded repository intelligence summaries only when
   operators can inspect the same source, freshness, confidence, limitation,
   budget, and replay fingerprint story.
8. Replay, eval, package, and release-gate evidence can distinguish behavior
   drift from repository intelligence context drift.

## Repository Intelligence Sources

Repository intelligence v2 may use these local sources when they remain
inspectable and bounded:

- repository index snapshots and their source digests
- workspace topology snapshots, components, dependency edges, roots, generated
  output hints, ownership hints, freshness, and limitations
- eval metadata from `evals/coverage.json`, `evals/impact.json`,
  `evals/recipes.json`, profiles, bundles, and deterministic cases
- command recipes from manifests, docs, release scripts, eval recipes,
  retained successful command evidence, and confirmed active memory
- confirmed active workspace memory for repository facts, conventions,
  verified commands, failure patterns, architecture notes, owner hints, and
  task outcomes
- dependency manifests, package manifests, lockfiles, workspace manifests, and
  frontend package metadata
- repository-owned docs, source roots, test roots, docs roots, release docs,
  command examples, and policy documents
- changeset inventories, verification readiness records, command evidence,
  review evidence, handoff posture, and retained release evidence

Every source that influences a recommendation, dashboard cue, changeset
summary, review brief, handoff posture, or prompt fragment must be named with
source class, source path or event ID when available, freshness, confidence,
and limitations.

## Memory-To-Repository Intelligence Rules

Workspace memory may enrich repository intelligence only after it is confirmed,
active, local to the workspace, and traceable to the workspace memory event
model. Memory-derived entries must cite memory IDs and source labels just like
file, manifest, eval, topology, command-evidence, or artifact-derived entries.

Confirmed memory may contribute advisory repository facts, local conventions,
verified command recipes, repeated failure patterns, architecture notes, owner
hints, package quirks, generated-output conventions, release-sensitive path
notes, and durable task outcomes. These contributions can appear in snapshots,
path-to-verification explanations, dashboard cues, changeset guidance, review
briefs, handoff summaries, and bounded context only with provenance, freshness,
confidence, and limitations visible to operators.

The following memory states are excluded from active repository intelligence by
default: candidate-only, rejected, stale, invalidated, imported-unreviewed,
pruned, unresolved-provenance, and redaction-blocked. They may appear in review
or conflict surfaces when clearly labeled, but they must not silently shape
recommendations or prompts.

Generated candidates remain review-only. Glassbox may propose candidates from
successful verification commands, repeated failures, verified recipes, topology
findings, release outcomes, eval recommendations, changesets, or repository
intelligence artifacts, but those suggestions are not repository facts until an
operator confirms them through the workspace memory flow.

Memory-derived intelligence is weaker than current deterministic source
metadata. When confirmed memory disagrees with manifests, source roots, topology
snapshots, command evidence, dependency metadata, generated-path rules, or
release-surface records, consumers should report a degraded or conflicting
posture and provide safe review actions instead of overriding the newer local
evidence.

When memory-derived repository intelligence enters model context, the context
snapshot must make the memory influence inspectable and
`WorkspaceMemoryUsedInContext` must record the memory ID, turn ID, prompt
section, state at use, and reason. Replay can then fingerprint both the
repository-intelligence snapshot and the memory state that shaped the prompt.

## Turn Context Contract

Repository intelligence may shape model turns only through a bounded typed
context snapshot. This prompt section is separate from repository context,
repository index context, runtime notes, working set, artifact-backed context,
workspace memory prompt fragments, checkpoint resume context, and compaction
summaries.

The context snapshot records:

- overall status, schema version, optional source digest, context byte count,
  budget byte count, truncation counts, safe next actions, and limitations
- included source summaries with source name, source kind, freshness,
  confidence, provenance, source digest, item count, and limitations
- selected prompt items for affected subsystems, likely tests, command
  recipes, confirmed conventions, release-sensitive surfaces,
  path-to-verification guidance, stale-risk notes, and limitations
- excluded source summaries for stale memory, stale topology, stale command
  recipes, failed index snapshots, conflicting metadata, missing eval
  metadata, or any other source that should remain visible but not active in
  the prompt

Only summaries enter the prompt. Raw repository intelligence artifacts, raw
repository index blobs, raw source files, raw diffs, raw command logs,
unreviewed memory candidates, secrets, credentials, and local `.glassbox`
internals stay out of model context by default.

Fresh sources can contribute active items. Stale, missing, degraded,
conflicting, or partial sources either stay out of active items or appear as
explicit excluded sources with degraded confidence, limitations, and safe
inspection or rebuild commands. Confirmed memory-derived intelligence is
eligible only when the memory entry is active, confirmed, local to the
workspace, provenance-backed, not stale or conflicting, and context use is
recorded.

Replay treats `repository_intelligence` as its own enriched-context source. The
fingerprint includes the context status, schema version, source digest,
included and excluded source summaries, selected items, limitations,
truncation counts, and safe next actions. Replay and eval drift should name the
repository intelligence source directly when this context changes, rather than
collapsing it into generic repository context or transcript drift.

The live v15 context builder derives this section from the retained local
repository intelligence snapshot. It does not rebuild the snapshot during turn
preparation. Fresh v2 snapshots can contribute bounded subsystem, test-root,
command-recipe, release-surface, and confirmed-memory convention summaries.
Missing snapshots remain visible in runtime snapshots and budget summaries but
stay out of active prompt context. Stale, building, failed, or schema-v1
snapshots produce degraded or excluded source summaries with safe
`glassbox repo index ... --cwd .` next actions instead of optimistic prompt
context.

## Evidence Expectations

Repository intelligence claims must be backed by deterministic local inputs,
canonical events, managed artifacts, typed API responses, projection state, or
eval fixtures. Builders and consumers should prefer structured source data over
model claims or ad hoc prose.

Repository intelligence artifacts should retain:

- schema version and builder version
- workspace-relative paths and normalized identifiers
- source digests and source manifest entries
- build time, freshness state, drift reasons, and limitations
- provenance records for entries and recommendations
- confidence labels and why-this explanations
- safe next actions for stale, missing, failed, degraded, or conflicting state

Repository intelligence artifacts should not retain raw file contents, raw
diffs, secrets, credentials, raw command logs, local `.glassbox` internals, or
reviewer-unsafe evidence unless a narrower task defines redaction and local-only
handling.

## Advisory Boundaries

Repository intelligence is advisory by default. It can make Glassbox better at
orientation and recommendation, but it must not imply that:

- a test, eval, command, browser check, accessibility pairing, provider canary,
  or manual review has run
- a stale or missing snapshot is fresh
- an owner hint assigns review responsibility or grants approval authority
- a command recipe is approved to execute
- confirmed memory overrides newer deterministic source evidence
- a changeset is ready for commit, push, pull request, merge, deploy, or
  package publication
- model prompt context is complete, hidden, or provider-managed

When intelligence is stale, missing, degraded, failed, or conflicting, consumers
must show lower confidence, name the limitation, and suggest safe inspection or
rebuild commands before asking operators to rely on the guidance.

## Release Authority

Deterministic replay, eval, package, migration, unit, integration, CLI, API,
frontend, and release-gate evidence remain the blocking release authority for
v15.

Repository intelligence can improve which checks are recommended and how
operators understand why a path matters. It does not replace running the
checks, recording evidence, reviewing failures, refreshing eval baselines, or
making an explicit release decision.

Live provider canaries, browser walkthroughs, dashboard inspection,
accessibility pairings, dogfooding notes, and manual observations remain
advisory unless a future task promotes a narrow fixture-backed contract with
deterministic inputs and an explicit pass/fail policy.

## Safety Rules

The v15 safety model inherits the local-first and event-sourced boundaries from
v8 through v14:

- Repository intelligence is local, rebuildable, freshness-aware,
  provenance-backed, and advisory by default.
- Canonical events, managed artifacts, source files, manifests, docs, eval
  fixtures, tests, and operator-confirmed memory remain the source-of-truth
  surfaces.
- Projections, API responses, dashboard state, CLI output, changesets, review
  briefs, handoff summaries, and prompt fragments must be rebuildable or
  traceable views.
- Memory-derived intelligence must come from confirmed active memory before it
  shapes recommendations or prompt context.
- Model-suggested facts, commands, owners, conventions, or package rules must
  stay review-only until an operator confirms them through the workspace memory
  flow.
- Repository intelligence must not introduce hosted code search, hosted
  repository indexing, remote workspaces, external vector-store authority,
  provider-side hidden memory, or cloud workspace authority.
- Rebuilds and refresh jobs may write managed `.glassbox` intelligence
  artifacts only through explicit commands or inspectable background jobs.
- Repository intelligence must never auto-stage, auto-commit, auto-push,
  auto-open pull requests, auto-merge, deploy, publish, rewrite history, or
  mutate policy files.
- Reviewer-facing artifacts must be redacted or explicitly local-only.
- Prompt use must be bounded, source-labeled, inspectable, and
  replay-fingerprinted.

## Mapping To Existing Contracts

| Existing contract | v15 relationship |
| --- | --- |
| [v8-auditable-autonomy-contract.md](./v8-auditable-autonomy-contract.md) | v15 keeps auditable autonomy: local state is event-sourced, bounded, inspectable, replay-aware, and subordinate to deterministic evidence. Repository intelligence remains one local evidence family, not a cloud authority. |
| [repository-intelligence-index.md](./repository-intelligence-index.md) | v15 upgrades the broad local index into richer repository intelligence snapshots with package boundaries, command recipes, ownership hints, generated paths, policy-sensitive paths, release surfaces, confidence, and limitations. |
| [workspace-topology.md](./workspace-topology.md) | v15 uses topology components, roots, generated-output hints, dependencies, freshness, and limitations as structured inputs for path impact, verification recommendations, and dashboard inspection. |
| [workspace-memory.md](./workspace-memory.md) | v15 allows confirmed active memory to enrich repository intelligence while preserving review-gated capture, provenance, freshness, invalidation, pruning, prompt-use records, and replay drift reporting. |
| [runtime-context.md](./runtime-context.md) | v15 adds bounded repository intelligence context beside existing repository context, runtime notes, working set, and artifact-backed context, with source-level inspection and replay fingerprints. |

## Non-Goals

v15 deliberately does not introduce:

- hosted code search
- hosted repository indexing
- external vector-store authority
- provider-side hidden memory
- cloud workspace authority
- remote worker fleets
- hosted code review
- hosted review comment synchronization
- cross-repository memory sync
- automatic owner assignment
- automatic review approval
- automatic staging
- automatic commits
- automatic pushes
- automatic pull request creation
- automatic branch-search merging
- automatic rebase, force-push, or history rewriting
- automatic deploys or package publishing
- automatic provider failover as release authority
- accessibility certification or broad WCAG conformance claims
- hidden semantic indexing that cannot be inspected, rebuilt, bounded, or
  replay-fingerprinted
- indefinite unattended autonomy

Future milestones may revisit some of these only with a new product contract,
safety model, evidence policy, remote-collaboration model, and explicit
operator semantics.

## Related Files

- [tasks-v15.md](./tasks-v15.md)
- [v14-release-candidate.md](./v14-release-candidate.md)
- [repository-intelligence-index.md](./repository-intelligence-index.md)
- [workspace-topology.md](./workspace-topology.md)
- [workspace-memory.md](./workspace-memory.md)
- [runtime-context.md](./runtime-context.md)
- [replay-evals.md](./replay-evals.md)
- [changeset-verification-readiness.md](./changeset-verification-readiness.md)
