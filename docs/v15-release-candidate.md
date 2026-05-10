# Glassbox v15 Release Candidate

This page is the operator and contributor guide for the Glassbox v15
release-candidate track. It names the supported repository-intelligence
operating model, validation path, evidence expectations, advisory evidence
boundaries, residual risks, deliberate non-goals, and release decision without
requiring readers to inspect the task graph.

## Release Posture

Glassbox v15 keeps the v14 local review-loop maturity model and adds
repository intelligence v2: local, rebuildable, freshness-aware,
provenance-backed repository awareness that helps operators understand paths,
verification options, command recipes, topology, memory candidates, and context
boundaries without replacing deterministic release authority.

The package version for this line remains `0.10.0`. Per
[version-release-policy.md](./version-release-policy.md), v15 is a milestone
and release-evidence track on the existing pre-1.0 package line, not a package
version bump by itself.

The primary product shape is:

- terminal chat remains the primary operator surface
- the dashboard remains the paired local cockpit and evidence surface
- SQLite canonical events and managed artifacts remain the source of truth
- repository index snapshots are local, rebuildable, and inspectable
- workspace topology is derived local evidence, not hosted ownership authority
- command recipes are advisory recommendations with source, purpose, risk, and
  freshness metadata
- path-to-verification guidance recommends likely tests, evals, profiles,
  release gates, stale evidence, and safe next actions without proving a path
  is verified
- owner and subsystem hints are advisory local cues, not access control,
  reviewer assignment, or approval authority
- confirmed active workspace memory can enrich repository intelligence, while
  stale, invalidated, imported-unreviewed, rejected, or pruned memory is
  excluded from prompt use by default
- repository-intelligence context is bounded, source-labeled, inspectable, and
  replay-fingerprinted
- missing, stale, conflict, or degraded repository intelligence is visible in
  CLI, API, dashboard, readiness, observability, and changeset surfaces
- publication posture never stages, commits, pushes, opens pull requests,
  merges, deploys, or publishes automatically
- deterministic replay, eval, package, frontend, installed-wheel, and release
  gate evidence remain release authority
- v15 is local repository intelligence, not hosted code search, provider-side
  hidden memory, automatic owner assignment, accessibility certification,
  browser release authority, or PR automation

Use these discovery commands:

```bash
uv run glassbox command guide
uv run glassbox command tree
uv run glassbox repo status --json --cwd .
```

Rebuild and inspect repository intelligence with:

```bash
uv run glassbox repo refresh --json --cwd .
uv run glassbox repo path PATH --json --cwd .
uv run glassbox repo recommend PATH --json --cwd .
uv run glassbox repo stale --json --cwd .
```

The v15 automated release-candidate gate is:

```bash
uv run python scripts/validate_v15_release_gate.py
```

For a non-mutating preview:

```bash
uv run python scripts/validate_v15_release_gate.py --dry-run
```

The retained evidence directory used for the current release-candidate pass is:

```text
.glassbox/releases/gbx-1583-v15-release-candidate/
```

The v15 eval artifacts for that candidate are retained under:

```text
.glassbox/evals/gbx-1583-v15-release-candidate/
```

Focused dogfooding evidence is summarized in
[v15-dogfooding-summary.md](./v15-dogfooding-summary.md). Local `.glassbox/`
evidence is workspace state and is not committed to git.

## Supported Operating Model

- **Repository index snapshot v2**:
  `glassbox repo refresh --json --cwd .` rebuilds a schema-versioned local
  repository snapshot with source roots, test roots, docs roots, package
  boundaries, generated paths, dependency manifests, policy-sensitive paths,
  release-sensitive surfaces, command recipes, owner hints, and subsystem
  hints.
- **Repository status and stale posture**:
  `glassbox repo status --json --cwd .` and
  `glassbox repo stale --json --cwd .` explain fresh, stale, missing, conflict,
  and degraded states before operators rely on repository intelligence.
- **Path inspection**:
  `glassbox repo path PATH --json --cwd .` maps a path to package, source,
  docs, tests, generated, owner, subsystem, command recipe, policy-sensitive,
  and release-surface cues while preserving advisory labels.
- **Path-to-verification guidance**:
  `glassbox repo recommend PATH... --json --cwd .` recommends likely tests,
  eval cases, eval profiles, command recipes, release gates, stale evidence,
  skipped checks, confidence, limitations, and safe next actions.
- **Workspace memory candidates**:
  `glassbox repo memory-candidates --session SESSION_ID --json --cwd .`
  proposes review-gated command and repository-intelligence candidates from
  confirmed active session memory only. Candidates need explicit review before
  they affect prompt context.
- **Changeset and review surfaces**: changeset inventories, verification
  plans, review briefs, and handoff readiness show repository-intelligence
  recommendations as inspection guidance, not verification success or reviewer
  acceptance.
- **Dashboard repository intelligence console**: the dashboard exposes the repo
  map, path inspector, command recipes, memory candidates, stale states, and
  "why this check" explanations with advisory labels.
- **Context and replay**: repository intelligence included in prompts is
  bounded, provenance-labeled, and replay-fingerprinted so stale or changed
  context can be audited later.
- **Background refresh**: background refresh jobs can rebuild derived
  repository intelligence without mutating source files or creating a second
  workspace mutation owner.

## Primary Operator Flows

### Refresh And Inspect Repository Intelligence

```bash
uv run glassbox repo refresh --json --cwd .
uv run glassbox repo status --json --cwd .
uv run glassbox repo path src/glassbox/runtime/repository_intelligence_queries.py --json --cwd .
uv run glassbox repo stale --json --cwd .
```

Safe use starts with refresh and status inspection. A stale or missing snapshot
does not block local work by itself, but it must remain visible before
repository-intelligence cues are used for review, verification, or handoff.

### Plan Verification For Changed Paths

```bash
uv run glassbox repo recommend src/glassbox/runtime/repository_intelligence_queries.py docs/v15-release-gate.md --json --cwd .
uv run glassbox eval run repository-intelligence.context-drift --cwd .
uv run glassbox eval audit --profile release-candidate --cwd .
```

Recommendations are a starting point. Deterministic tests, evals, package
checks, release gates, and operator review decide whether evidence is adequate.

### Review Memory-Derived Repository Candidates

```bash
uv run glassbox session list --json --cwd .
uv run glassbox repo memory-candidates --session SESSION_ID --limit 5 --json --cwd .
```

Session list output can include historical prompt and assistant summaries, so
retain it locally and summarize only sanitized IDs or aggregate behavior in
reviewer-facing docs.

### Prepare A Repository-Aware Changeset Handoff

```bash
uv run glassbox changeset refresh CHANGESET_ID --cwd .
uv run glassbox changeset verification-plan CHANGESET_ID --cwd .
uv run glassbox changeset brief CHANGESET_ID --format markdown --cwd .
uv run glassbox changeset handoff-readiness CHANGESET_ID --cwd .
```

Repository intelligence can explain likely checks and risk cues, but handoff
readiness remains conservative when verification is missing, evidence is stale,
risks are unresolved, or publication boundaries are ambiguous.

## Release-Readiness Checklist

Before treating a build as the v15 release candidate, complete this list:

- The v15 repository intelligence contract, audit, evidence summary, dogfooding
  summary, release gate, release-candidate guide, and task graph are linked
  from the docs hub.
- `uv run python scripts/validate_v15_release_gate.py` passes and writes
  `summary.json` with blocking and advisory sections.
- The deterministic `release-candidate` eval profile passes, including
  `repository-intelligence.snapshot-rich`,
  `repository-intelligence.path-verification`,
  `repository-intelligence.stale-degradation`,
  `repository-intelligence.memory-command`, and
  `repository-intelligence.context-drift`.
- `glassbox eval audit --profile release-candidate --cwd .` reports no
  uncovered release-candidate capabilities.
- Repository index, topology, memory candidate, path recommendation,
  changeset, CLI/API, dashboard, context, replay, eval, package, and release
  docs surfaces have focused tests or deterministic eval evidence where
  promoted.
- Generated OpenAPI/types and dashboard static assets are fresh and packaged.
- Built wheel and sdist contents include v15 release docs, eval fixtures,
  release scripts, generated API files, and dashboard static assets.
- Dogfooding findings have dispositions as fixes, docs, tests/evals, accepted
  risks, or post-v15 follow-ups.
- Provider canaries, live browser/dashboard evidence, and accessibility
  evidence are either retained as advisory evidence or explicitly skipped with
  bounded reasons.
- Raw `.glassbox` state is not committed; reviewer-safe summaries are used for
  handoff and release review.

## Current Evidence Summary

The current retained v15 evidence shows:

- v15 release gate for `GBX-1583`: retained at
  `.glassbox/releases/gbx-1583-v15-release-candidate/summary.json` with
  106 passing stages across repository-intelligence, inherited v14, package,
  installed-wheel, frontend, eval, and docs coverage plus advisory sections for
  provider, dashboard/browser, accessibility-adjacent, and dogfooding evidence
- v15 release-gate dry run during `GBX-1582`: passed at
  `.glassbox/releases/gbx-1582-v15-dogfooding/v15-gate-dry-run/summary.json`
  with 81 planned blocking stages, one skipped provider advisory item, two
  recorded retained advisory UX items, and dogfooding recorded beside the
  deterministic gate plan
- v15 dogfooding: findings and follow-up candidates are triaged in
  [v15-dogfooding-summary.md](./v15-dogfooding-summary.md)
- Repository snapshot rebuild: dogfooding rebuilt a fresh v2 index and fresh
  topology for the full Glassbox repository with 1,210 source files, 11,412
  entries, 97 command recipes, 14 subsystems, 14 ownership hints, 17
  policy-sensitive paths, 4 release surfaces, and 40 topology dependencies
- path-to-verification guidance: dogfooding mapped mixed runtime and docs paths
  to the five v15 repository-intelligence eval cases, release-candidate
  profile, docs guardrail, package checks, lint, typecheck, and topology
  fallbacks without treating recommendations as verification success
- memory candidate review: explicit-session review returned review-gated
  command candidates with repository-intelligence provenance and redaction; the
  no-session command path remains a post-v15 copy follow-up
- changeset integration: dogfooding generated verification recommendations,
  lifecycle brief evidence, and handoff readiness against a real 13-path v15
  diff while keeping publication and approval non-claims visible
- bounded-output fixes: repository-intelligence-derived requirement IDs and
  lifecycle brief safe inspection commands are bounded with regression tests
- deterministic v15 evals: the five v15 repository-intelligence cases are
  included in the release-candidate profile and v15 gate smoke stage
- package contents: the release package guardrail requires v15 release docs,
  v15 release gate scripts, eval fixtures, generated API files, and dashboard
  static assets
- provider evidence: optional and advisory; the v15 gate records provider
  canaries as skipped by default unless explicitly requested
- browser/dashboard and accessibility evidence: advisory; retained `GBX-1554`
  summaries provide bounded UX confidence while skipped or stale live evidence
  stays visible as limitations

## Known Residual Risks

- Repository intelligence is advisory. It cannot replace deterministic tests,
  evals, package checks, release gates, or operator review.
- A fresh snapshot can still be incomplete when local discovery heuristics miss
  a project-specific convention, generated artifact, nonstandard test target,
  or release-sensitive surface.
- Command recipes are recommendations. They can be stale, partial, risky for a
  particular checkout, or inappropriate for a task despite source metadata and
  confidence labels.
- Path-to-verification recommendations can miss relevant tests or suggest broad
  checks. A recommended command is not evidence that the command has run.
- Owner and subsystem hints are advisory local cues. They do not assign
  reviewers, grant permission, enforce access control, or prove code ownership.
- Workspace memory candidates require explicit session selection and review.
  Dogfooding found that the no-session error is terse:
  `unknown session_id: None`.
- Session-list and memory-candidate outputs can contain sensitive historical
  prompt summaries. Retain raw output locally and publish sanitized summaries.
- Concurrent reads during repository refresh can observe stale or missing
  state. Operators should wait for refresh completion before capturing release
  evidence.
- Missing optional memory-derived entries degrade confidence but do not block
  repository snapshot, topology, path, recommendation, or release-gate evidence.
- Changeset verification plans and review briefs can surface repository
  intelligence, but they do not prove reviewer approval, verification success,
  publication readiness, or hosted review state.
- Provider canaries and provider recommendations are advisory. This release
  candidate does not make live-provider behavior blocking release authority.
- Retained browser/dashboard and accessibility-adjacent evidence covers bounded
  scenarios, dates, tools, and limitations. It is not broad browser coverage,
  screen-reader certification, accessibility certification, or WCAG conformance.
- Handoff readiness and publication-boundary guidance are advisory local
  posture. They do not stage, commit, push, open pull requests, merge, deploy,
  publish, or prove publication readiness.
- v15 does not remove inherited bounded-autonomy limits from earlier
  milestones.

## Deliberate Non-Goals

v15 does not introduce hosted code search, hosted repository indexing,
external vector-store authority, provider-side hidden memory, cloud workspace
authority, remote worker fleets, hosted code review, hosted review comment
synchronization, cross-repository memory sync, automatic owner assignment,
automatic review approval, automatic staging, automatic commits, automatic
pushes, automatic pull request creation, automatic branch-search merging,
automatic rebasing, automatic force-pushing, automatic deployment, automatic
package publication, automatic provider failover as release authority, broad
accessibility certification, WCAG conformance claims, live browser release
authority, hidden semantic indexing that cannot be inspected and rebuilt, or
indefinite unattended autonomy.

## Release Decision

Decision: GO for v15 release candidate publication.

Decision date: 2026-05-10.

Candidate build reviewed: `GBX-1583` release-candidate working tree with final
v15 gate evidence retained locally.

Retained evidence:

```text
.glassbox/releases/gbx-1583-v15-release-candidate/
.glassbox/evals/gbx-1583-v15-release-candidate/
.glassbox/releases/gbx-1582-v15-dogfooding/
.glassbox/releases/gbx-1582-v15-dogfooding/v15-gate-dry-run/
```

Final pass/fail state:

| Area | State | Evidence |
| --- | --- | --- |
| Automated v15 gate | passed | `.glassbox/releases/gbx-1583-v15-release-candidate/summary.json` |
| Deterministic eval release report | passed | `.glassbox/evals/gbx-1583-v15-release-candidate/v15-release-signoff/` |
| V15 repository intelligence release profile | passed | `.glassbox/evals/gbx-1583-v15-release-candidate/v15-repository-intelligence-release/` |
| V15 repository intelligence eval smoke | passed | `.glassbox/evals/gbx-1583-v15-release-candidate/v15-repository-intelligence-smoke/` |
| V15 runtime and CLI/API coverage | passed | `tests/unit/test_repository_index.py tests/unit/test_workspace_topology.py tests/unit/test_workspace_memory_capture.py tests/unit/test_eval_recommendations.py tests/unit/test_runtime_eval_coverage.py tests/integration/test_cli_repository_commands.py tests/integration/test_web_repository_index_routes.py tests/integration/test_openapi_schema.py` |
| V15 dashboard repository intelligence coverage | passed | `pnpm --dir frontend test -- knowledge-autonomy-console.test.tsx workspace-overview.test.tsx changeset-console.test.tsx verification-cues.test.ts generated-api-types.test.ts` |
| Release-candidate eval coverage | passed | `glassbox eval audit --profile release-candidate --cwd .` in the v15 gate |
| Package and installed smoke | passed | package contents validation plus installed-wheel smoke in the v15 gate |
| Dogfooding disposition | passed triage | [v15-dogfooding-summary.md](./v15-dogfooding-summary.md) |
| Provider posture | advisory skipped by default | v15 gate advisory provider evidence section |
| Browser/dashboard posture | advisory retained as bounded evidence | [v15-repository-intelligence-evidence.md](./v15-repository-intelligence-evidence.md) and retained `GBX-1554` summaries |
| Accessibility posture | advisory retained as bounded evidence | [v15-repository-intelligence-evidence.md](./v15-repository-intelligence-evidence.md) and retained `GBX-1554` summaries |
| Residual risk review | accepted | known residual risks listed above |

No deterministic blocker remains open for v15 release-candidate publication.
The accepted residual risks stay bounded to advisory repository intelligence,
partial discovery, stale command recipes, recommendation non-proof, advisory
owner hints, explicit-session memory review, sensitive session-list evidence,
concurrent-refresh staleness, missing optional memory-derived entries, local
changeset non-approval, advisory provider/browser/dashboard/accessibility
posture, publication-boundary non-claims, and bounded local autonomy.

## Related Files

- [v15-repository-intelligence-contract.md](./v15-repository-intelligence-contract.md)
- [v15-repository-intelligence-audit.md](./v15-repository-intelligence-audit.md)
- [v15-repository-intelligence-evidence.md](./v15-repository-intelligence-evidence.md)
- [v15-release-gate.md](./v15-release-gate.md)
- [v15-dogfooding-summary.md](./v15-dogfooding-summary.md)
- [path-to-verification-recommendations.md](./path-to-verification-recommendations.md)
- [repository-intelligence-index.md](./repository-intelligence-index.md)
- [workspace-topology.md](./workspace-topology.md)
- [workspace-memory.md](./workspace-memory.md)
- [runtime-context.md](./runtime-context.md)
- [replay-evals.md](./replay-evals.md)
- [command-evidence.md](./command-evidence.md)
- [changeset-verification-readiness.md](./changeset-verification-readiness.md)
- [review-feedback.md](./review-feedback.md)
- [review-responses.md](./review-responses.md)
- [manual-evidence.md](./manual-evidence.md)
- [browser-accessibility-evidence.md](./browser-accessibility-evidence.md)
- [publication-boundary.md](./publication-boundary.md)
- [v14-release-candidate.md](./v14-release-candidate.md)
- [v14-review-loop-maturity-contract.md](./v14-review-loop-maturity-contract.md)
- [release-packaging.md](./release-packaging.md)
- [providers.md](./providers.md)
- [tasks-v15.md](./tasks-v15.md)
