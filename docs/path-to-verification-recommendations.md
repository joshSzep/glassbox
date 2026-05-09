# Path-To-Verification Recommendations

This page defines the v15 contract for turning changed paths into verification
guidance. It extends the existing [replay and eval workflow](./replay-evals.md)
instead of replacing it with a second recommendation vocabulary.

Path-to-verification recommendations answer a narrow local question: given a
set of repository-relative changed paths, what tests, evals, command recipes,
release gates, stale-evidence warnings, and safe next actions are likely worth
considering, and why?

The answer is advisory until an explicit deterministic check runs and records
evidence. Recommendations can improve verification choice, but they do not
prove that the selected checks are complete and they do not claim that any
check has already passed.

## Inputs

The recommendation contract may use these local, inspectable inputs:

- changed paths from a changeset inventory, CLI argument, or explicit operator
  selection
- Repository intelligence snapshots, including source roots, test roots,
  docs roots, package boundaries, generated paths, command recipes, owner
  hints, release surfaces, freshness, and limitations
- workspace topology snapshots and their component, manifest, dependency,
  generated-output, owner-hint, and stale-topology metadata
- eval metadata from `evals/impact.json`, `evals/coverage.json`,
  `evals/recipes.json`, `evals/profiles.json`, and `evals/cases/*.json`
- retained verification, command, changeset, review, manual, browser, and
  accessibility evidence where a later task defines a source path
- confirmed active workspace memory only when memory provenance, freshness,
  state, and prompt-use rules allow it

Missing or stale inputs lower confidence and must be visible in the report.
They should produce safe inspection or rebuild actions rather than optimistic
recommendations.

## Output Model

Runtime reports use typed path-to-verification models exported from
`glassbox.runtime.eval_recommendations`:

- `PathVerificationRecommendationReport` is the top-level report for one set of
  changed paths.
- `PathVerificationImpact` records why a path matters: subsystem, package,
  owner hint, release surface, generated-path, policy-sensitive, provenance,
  freshness, confidence, and limitations.
- `EvalTestTargetRecommendation` records likely test targets discovered from
  repository intelligence source roots, test roots, package boundaries, naming
  conventions, topology, recipes, and fallback policy.
- Eval case, profile, and recipe rows carry repository-intelligence source
  metadata when a v2 snapshot shaped the recommendation. Rows name matched
  paths, source IDs, freshness, limitations, profile budget implications, and
  safe next commands separately from execution authority.
- `PathVerificationTarget` records one recommended target and its evidence
  class.
- `PathVerificationCommandRecipeTarget` records advisory command recipes with
  purpose, risk, review relevance, timeout hints, provenance, confidence, and
  limitations.
- `PathVerificationEvalCaseTarget` and `PathVerificationEvalProfileTarget`
  preserve the existing eval case/profile vocabulary.
- `PathVerificationSkippedCheck` records recommendations that are intentionally
  kept out of executable plans.
- `PathVerificationStaleEvidence` records stale or missing verification,
  topology, recipe, memory, eval metadata, release-surface, or repository
  intelligence evidence.
- `PathVerificationProvenance` names the source, source path or source ID,
  freshness, confidence, explanation, and limitations behind each claim.

Reports should keep paths workspace-relative, avoid raw file contents and raw
diffs, and avoid retaining raw command logs or reviewer-unsafe local state.

## Evidence Classes

Every target must say what kind of evidence it represents:

- `deterministic-executable`: unit tests, integration tests, eval cases,
  deterministic eval profiles, lint, format, typecheck, and release gates that
  can become blocking evidence once run.
- `advisory-command`: repository recipes and topology-derived commands that
  are useful guidance but are not permission grants and are not executed by
  recommendation commands.
- `live-provider-canary`: provider canaries that stay skipped unless explicitly
  selected and remain advisory unless a future deterministic contract promotes
  them.
- `browser-evidence`: bounded dashboard or browser walkthrough evidence.
- `accessibility-evidence`: bounded keyboard, focus, responsive, or assistive
  technology pairing evidence.
- `manual-evidence`: operator-attached evidence that requires human judgment.

This distinction is part of the type contract. A command recipe cannot be
reported as deterministic evidence, and live-provider, browser, accessibility,
and manual evidence cannot silently enter an executable deterministic plan.

## Confidence

Recommendations should use visible confidence:

- `direct`: the changed path matched repository-owned metadata that named the
  test, eval case, eval profile, command recipe, or release gate.
- `topology-derived`: topology connected the path to a component or package
  with known checks.
- `naming-derived`: source and test naming conventions suggest a target.
- `package-derived`: package or workspace boundaries suggest a target.
- `recipe-derived`: an eval recipe or command recipe matched the path.
- `owner-derived`: an owner hint connected the path to matching eval metadata.
- `capability-derived`: a capability mapping connected the path to coverage or
  case metadata.
- `stage-derived`: impacted cases or capabilities selected a profile through a
  verification stage.
- `fallback`: no stronger mapping exists, so the report can only name manual
  policy guidance or the smallest default deterministic surface.

Ordering should prefer the cheapest useful deterministic check when one exists,
then explain any broader advisory, release-candidate, manual, browser,
accessibility, or canary follow-up separately.

## Test Target Discovery

`eval recommend` exposes likely test targets separately from advisory command
recipes. Test target rows can come from repository intelligence snapshots,
workspace topology, source/test naming conventions, package boundaries,
repository recipes, or fallback policy. Rows include matched paths, target test
paths or roots, package IDs, component IDs, a suggested command when one is
known, reasons, freshness, confidence, and limitations.

Common behavior:

- changed test files are `direct` targets
- source files with matching `test_*.py`, `*.test.ts`, `*.spec.ts`,
  `*.test.tsx`, or `*.spec.tsx` files are `naming-derived`
- source files inside a package with test roots but no matching test file are
  `package-derived`
- topology-only matches are `topology-derived`
- documentation-only changes fall back to the docs guardrail test
- generated paths warn operators to inspect the source generator before
  trusting generated-file test guidance
- packages with no discovered test roots emit degraded guidance rather than a
  pretend target

## Eval Scope Enrichment

`eval recommend` keeps repository-owned eval metadata authoritative, then uses
repository intelligence as an advisory enrichment layer. A fresh v2 repository
index can add source metadata to existing case and profile rows, derive profile
guidance from release-sensitive surfaces, and surface safe command recipes from
local manifests or eval recipe files. Stale snapshots keep their provenance but
downgrade freshness and warn operators to rebuild before relying on current
path-to-eval guidance.

Missing repository intelligence does not block eval recommendations. Glassbox
falls back to eval impact rules, coverage metadata, profiles, recipes, topology,
and manual fallback policy. Live-provider canary profiles remain skipped from
executable plans unless the operator explicitly selects them.

## Freshness And Stale Evidence

Path-to-verification output must name freshness whenever a source can be stale:

- `fresh`: the source matches the current workspace digest or freshness policy.
- `stale`: the source is retained but no longer matches known inputs.
- `missing`: the source is absent.
- `degraded`: the source exists but only supports partial or low-confidence
  guidance.
- `unknown`: the source did not expose a freshness claim.

Stale evidence rows should name the affected paths, stale source kind, reason,
provenance, and safe next actions such as rebuilding repository intelligence,
refreshing topology, running `glassbox eval audit --cwd .`, or attaching new
verification evidence.

## Non-Claims

Path-to-verification recommendations do not claim that:

- the recommended set is complete or minimal
- any test, eval, recipe, release gate, canary, browser pass, accessibility
  pairing, or manual check has run
- advisory evidence can satisfy deterministic release gates
- command recipes are approved to execute
- stale topology, stale memory, or stale repository intelligence is fresh
- owner hints assign review responsibility or approval authority
- model prompt context should include the recommendation without an
  inspectable context snapshot and replay fingerprint story

Deterministic release authority remains with the actual tests, evals, package
checks, type checks, lint checks, release gates, and retained evidence described
in the v15 [repository intelligence contract](./v15-repository-intelligence-contract.md).

## Related Files

- [v15-repository-intelligence-contract.md](./v15-repository-intelligence-contract.md)
- [repository-intelligence-index.md](./repository-intelligence-index.md)
- [workspace-topology.md](./workspace-topology.md)
- [replay-evals.md](./replay-evals.md)
- [changeset-verification-readiness.md](./changeset-verification-readiness.md)
