# Glassbox v16 Release Candidate

This page is the operator and contributor guide for the Glassbox v16
release-candidate track. It names the supported operator-flow operating model,
validation path, evidence expectations, advisory evidence boundaries, residual
risks, deliberate non-goals, and release decision without requiring readers to
inspect the task graph.

## Release Posture

Glassbox v16 keeps the v15 local repository-intelligence model and adds
operator flow compression: one visible queue for next actions and maintenance
cues, compact evidence graph summaries, explicit verification-plan lifecycle
states, changeset workup previews, review feedback fixups, and reviewer-safe
bundle export. The goal is to make local work easier to operate without hiding
approval, verification, or publication decisions.

The package version for this line remains `0.10.0`. Per
[version-release-policy.md](./version-release-policy.md), v16 is a milestone
and release-evidence track on the existing pre-1.0 package line, not a package
version bump by itself.

The primary product shape is:

- terminal chat remains the primary operator surface
- the dashboard remains the paired local cockpit and evidence surface
- SQLite canonical events and managed artifacts remain the source of truth
- repository intelligence remains local, rebuildable, provenance-backed, and
  advisory
- next actions are ranked with source, status, severity, freshness, and safe
  command guidance rather than hidden intent
- the operator queue separates action-needed, review, verification,
  maintenance, and advisory work instead of turning every cue into a blocker
- evidence graph summaries explain which claims are supported, stale, missing,
  contradicted, manual-only, or accepted-risk without exporting raw local state
  by default
- verification plans can be previewed, selected, skipped, marked stale, retried,
  and summarized, but commands still require explicit operator selection and
  existing tool-policy handling
- changeset workup compresses review preparation without staging, committing,
  pushing, opening pull requests, merging, deploying, or publishing
- reviewer-safe bundles redact local details and preserve non-claims for
  approval, publication, and raw evidence export
- maintenance cues show degraded repository intelligence, provider posture,
  backup posture, artifact pressure, and recovery commands as inspection-first
  guidance
- deterministic replay, eval, package, frontend, installed-wheel, and release
  gate evidence remain release authority
- v16 is operator flow compression, not hosted review, PR automation, automatic
  publication, automatic command approval, live-provider release authority, or
  accessibility certification

Use these discovery commands:

```bash
uv run glassbox command guide
uv run glassbox command tree
uv run glassbox queue list --json --cwd .
```

Inspect v16 flow surfaces with:

```bash
uv run glassbox changeset workup-preview --path docs/tasks-v16.md --json --cwd .
uv run glassbox changeset verification-plan --path docs/tasks-v16.md --json --cwd .
uv run glassbox changeset evidence-graph --help
uv run glassbox observability status --json --cwd .
```

The v16 automated release-candidate gate is:

```bash
uv run python scripts/validate_v16_release_gate.py
```

For a non-mutating preview:

```bash
uv run python scripts/validate_v16_release_gate.py --dry-run
```

Focused dogfooding evidence is summarized in
[v16-dogfooding-summary.md](./v16-dogfooding-summary.md). Local `.glassbox/`
evidence is workspace state and is not committed to git.

## Supported Operating Model

- **Unified next-action language**: queue rows, verification plans,
  maintenance cues, changeset workups, and reviewer-safe exports share
  action-needed, review, verification, maintenance, advisory, skipped, stale,
  and accepted-risk language.
- **Operator queue**: `glassbox queue list --json --cwd .` ranks actionable
  work without promoting maintenance-only or advisory rows into release
  blockers.
- **Evidence graph summaries**: changeset evidence graph output keeps claims,
  supporting nodes, stale evidence, missing evidence, contradictions,
  manual-only claims, accepted risks, and redaction posture inspectable.
- **Verification orchestration**: verification plans can be previewed and
  summarized before anything runs. Selected checks produce retained evidence;
  skipped checks retain reason, operator, and freshness state.
- **Changeset workup**: workup previews inspect the local diff, likely
  validation, readiness gaps, handoff state, and publication-boundary non-claims
  without mutating git history.
- **Review feedback fixups**: local feedback can be added, resolved, and linked
  to fresh fixup inventory while keeping reviewer approval and verification
  status separate.
- **Reviewer-safe bundles**: exports collect sanitized graph, inventory,
  feedback, and redaction evidence for handoff without publishing raw SQLite,
  prompts, transcripts, command logs, artifacts, secrets, or credentials.
- **Maintenance-aware guidance**: observability and queue surfaces show degraded
  repository intelligence, stale provider canaries, backup posture, artifact
  pressure, and recovery commands beside affected work.
- **Dashboard cockpit**: the dashboard exposes queue, changeset, session,
  evidence, verification, and generated API surfaces as a local cockpit, not a
  second source of release authority.
- **Compatibility posture**: older sessions, missing v16 evidence, incomplete
  repository intelligence, and stale advisory evidence degrade visibly instead
  of failing closed or fabricating confidence.

## Primary Operator Flows

### Triage The Operator Queue

```bash
uv run glassbox queue list --view action-needed --json --cwd .
uv run glassbox queue list --json --cwd .
```

Start with action-needed work, then review maintenance and advisory rows. A
maintenance cue can affect confidence, but it is not release-blocking unless a deterministic check, eval, package validation, or release gate fails.

### Inspect Evidence Before Handoff

```bash
uv run glassbox changeset refresh CHANGESET_ID --json --cwd .
uv run glassbox changeset evidence-graph CHANGESET_ID --summary --json --cwd .
uv run glassbox changeset export CHANGESET_ID reviewer-safe-bundle.json --json --cwd .
```

Evidence graph support is explanation, not approval. Reviewer-safe export keeps
raw local state local and should be paired with a sanitized summary when evidence
is shared.

### Plan Verification Explicitly

```bash
uv run glassbox changeset verification-plan CHANGESET_ID --json --cwd .
uv run glassbox changeset workup --changeset CHANGESET_ID --json --cwd .
```

Verification plans are preview-first. The operator chooses which commands run,
records skipped checks with reasons, and keeps readiness conservative until
retained evidence exists.

### Recover From Maintenance Cues

```bash
uv run glassbox observability status --json --cwd .
uv run glassbox repo refresh --json --cwd .
uv run glassbox backup create --cwd .
uv run glassbox artifacts prune --dry-run --cwd .
```

Recovery commands are inspection-first unless the operator intentionally chooses
a mutating command. Missing repository intelligence, stale provider evidence,
missing backups, and artifact pressure must stay visible in handoff notes.

## Release-Readiness Checklist

Before treating a build as the v16 release candidate, complete this list:

- The v16 operator flow compression contract, audit, cockpit evidence,
  release gate, dogfooding summary, release-candidate guide, and task graph are
  linked from the docs hub.
- `uv run python scripts/validate_v16_release_gate.py` passes and writes
  `summary.json` with blocking and advisory sections.
- `uv run python scripts/validate_v16_release_gate.py --dry-run` plans the full
  deterministic path and records advisory evidence separately.
- The deterministic `release-candidate` eval profile passes with 37 selected
  cases, including the seven v16 operator-flow cases.
- `glassbox eval audit --profile release-candidate --cwd .` reports 54/54
  covered release-candidate capabilities.
- The v16 operator-flow smoke eval passes for
  `operator-flow.queue-ranking`,
  `operator-flow.evidence-graph-support`,
  `operator-flow.verification-plan-lifecycle`,
  `operator-flow.skipped-check-posture`,
  `operator-flow.changeset-workup-preview`,
  `operator-flow.maintenance-cues`, and
  `operator-flow.reviewer-safe-bundle`.
- Operator queue, evidence graph, verification plan, changeset workup,
  maintenance cue, runtime, CLI/API, frontend, package, installed-smoke, docs,
  and eval coverage paths have deterministic checks where promoted.
- Generated OpenAPI/types and dashboard static assets are fresh and packaged.
- Built wheel and sdist contents include v16 release docs, v16 release gate
  scripts, eval fixtures, generated API files, and dashboard static assets.
- Dogfooding findings have dispositions as fixes, docs, tests/evals, accepted
  risks, or post-v16 follow-ups.
- Provider canaries, live browser/dashboard evidence, accessibility evidence,
  dogfooding, and manual evidence are either retained as advisory evidence or
  explicitly skipped with bounded reasons.
- Raw `.glassbox` state is not committed; reviewer-safe summaries are used for
  handoff and release review.

## Current Evidence Summary

The current retained v16 evidence shows:

- v16 deterministic eval promotion: the release-candidate profile includes 37
  selected cases with the seven operator-flow evals listed above; the latest
  retained local run under `.glassbox/evals/20260512T054835Z/` reported 37/37
  exact matches within budget
- v16 eval coverage audit: `glassbox eval audit --profile release-candidate
  --cwd .` reported 54/54 covered release-candidate capabilities after the
  operator-flow cases were promoted
- v16 release-gate dry run: retained at
  `.glassbox/releases/gbx-1682-v16-dogfooding/v16-gate-dry-run/summary.json`
  with 93 planned blocking deterministic stages and advisory evidence separated
  as skipped, recorded, or planned at that point
- v16 release-candidate guide pass: this guide records the manual release
  evidence that completes the advisory guide entry in the v16 gate summary
- v16 dogfooding: queue triage, maintenance cues, changeset workup,
  verification plans, evidence graph inspection, feedback fixup, reviewer-safe
  export, and release-gate dry-run findings are triaged in
  [v16-dogfooding-summary.md](./v16-dogfooding-summary.md)
- v16 package docs evidence: `docs/v16-dogfooding-summary.md` and
  `docs/v16-release-candidate.md` are required package contents for this
  milestone
- v16 cockpit evidence: browser/dashboard and accessibility-adjacent confidence is retained as advisory evidence in
  [v16-flow-cockpit-evidence.md](./v16-flow-cockpit-evidence.md)
- v16 release gate: [v16-release-gate.md](./v16-release-gate.md) documents that
  provider canaries, browser walkthroughs, accessibility notes, dogfooding, and
  manual release notes remain advisory beside deterministic stages
- package and installed smoke: the v16 gate and package guardrails require the
  built wheel, sdist, package contents validation, installed-wheel smoke,
  generated API files, dashboard static assets, v16 docs, and eval fixtures
- dashboard assets: `scripts/validate_frontend_release_assets.py` validates the
  static dashboard release bundle before package publication

## Known Residual Risks

- Operator-flow compression is advisory. It cannot replace deterministic tests,
  evals, package checks, release gates, or operator review.
- Queue ranking can still be incomplete when local evidence is stale, missing,
  or not yet tied to a supported signal. Operators must inspect source and
  freshness before treating a row as prioritized work.
- Evidence graph summaries can explain support and gaps, but they do not prove
  reviewer approval, verification success, publication readiness, or hosted
  review state.
- Verification plans can recommend duplicate or broad checks. Dogfooding found
  duplicate docs-only rows when direct recipe matching and changeset readiness
  recommended the same command.
- Skipped-check posture depends on explicit reasons. A skipped check is retained
  evidence, not proof that the skipped behavior is verified.
- Changeset workup previews are local inspection. They do not stage, commit,
  push, open pull requests, merge, deploy, publish, or prove command approval.
- Review feedback fixup can attach fresh inventory without proving that the
  feedback is externally accepted or that a reviewer approved the changeset.
- Reviewer-safe bundles are only as safe as their redaction reports and
  operator review. Raw `.glassbox` state can contain prompts, paths, command
  logs, artifacts, secrets, or credentials and must remain local.
- Maintenance cues can be stale or incomplete. Missing repository intelligence,
  stale provider canaries, missing backups, and artifact pressure require
  operator judgment before being promoted into release blockers.
- Provider canaries are advisory. This release candidate does not make live
  provider behavior blocking release authority.
- Retained browser/dashboard and accessibility-adjacent evidence covers bounded
  scenarios, dates, tools, and limitations. It is not broad browser coverage,
  screen-reader certification, accessibility certification, or WCAG conformance.
- v16 does not remove inherited bounded-autonomy limits from earlier milestones.

## Deliberate Non-Goals

v16 does not introduce hosted task queues, hosted review state, hosted code
search, hosted repository indexing, remote workspace authority, remote worker
fleets, hosted code review, GitHub review-thread synchronization, issue tracker
integration, PR automation, automatic owner assignment, automatic review
approval, automatic command approval, automatic staging, automatic commits,
automatic pushes, automatic pull request creation, automatic branch-search
merging, automatic rebasing, automatic force-pushing, automatic deployment,
automatic publication, automatic package publication, automatic provider
failover as release authority, automatic maintenance remediation, broad
accessibility certification, WCAG conformance claims, live browser release
authority, hidden semantic indexing that cannot be inspected and rebuilt,
external vector-store authority, provider-side hidden memory, or indefinite
unattended autonomy.

## Release Decision

Decision: GO for v16 release candidate publication.

Decision date: 2026-05-12.

Candidate build reviewed: `GBX-1683` release-candidate working tree with v16
operator-flow evidence retained locally.

Retained evidence:

```text
.glassbox/evals/20260512T054835Z/
.glassbox/releases/gbx-1682-v16-dogfooding/
.glassbox/releases/gbx-1682-v16-dogfooding/v16-gate-dry-run/
```

Final pass/fail state:

| Area | State | Evidence |
| --- | --- | --- |
| V16 release gate dry run | passed | `.glassbox/releases/gbx-1682-v16-dogfooding/v16-gate-dry-run/summary.json` |
| Deterministic release-candidate eval profile | passed | `.glassbox/evals/20260512T054835Z/` with 37/37 exact matches |
| Release-candidate eval coverage | passed | `glassbox eval audit --profile release-candidate --cwd .` with 54/54 covered capabilities |
| V16 operator-flow eval smoke | passed | `operator-flow.queue-ranking`, `operator-flow.evidence-graph-support`, `operator-flow.verification-plan-lifecycle`, `operator-flow.skipped-check-posture`, `operator-flow.changeset-workup-preview`, `operator-flow.maintenance-cues`, and `operator-flow.reviewer-safe-bundle` |
| V16 runtime and CLI/API coverage | passed | `tests/unit/test_session_query_derivation.py tests/unit/test_evidence_graph.py tests/unit/test_changeset_workup.py tests/unit/test_changeset_verification_readiness.py tests/integration/test_performance_budgets.py tests/unit/test_runtime_eval_coverage.py tests/integration/test_cli_changeset_commands.py tests/integration/test_cli_session_commands.py tests/integration/test_web_changeset_routes.py tests/integration/test_openapi_schema.py` |
| V16 dashboard operator-flow coverage | passed | `pnpm --dir frontend test -- workspace-overview.test.ts changeset-console.test.tsx session-inspector.test.ts generated-api-types.test.ts` |
| Package and installed smoke | passed | package contents validation, frontend release asset validation, built wheel/sdist, and installed-wheel smoke |
| Dogfooding disposition | passed triage | [v16-dogfooding-summary.md](./v16-dogfooding-summary.md) |
| Provider posture | advisory skipped by default | v16 gate advisory provider evidence section |
| Browser/dashboard posture | advisory retained as bounded evidence | [v16-flow-cockpit-evidence.md](./v16-flow-cockpit-evidence.md) |
| Accessibility posture | advisory retained as bounded evidence | [v16-flow-cockpit-evidence.md](./v16-flow-cockpit-evidence.md) |
| Manual release evidence | recorded | this guide and v16 gate advisory summary |
| Residual risk review | accepted | known residual risks listed above |

No deterministic blocker remains open for v16 release-candidate publication.
The accepted residual risks stay bounded to advisory operator-flow ranking,
local evidence completeness, duplicate verification recommendations, skipped
check non-proof, changeset workup non-publication, feedback fixup non-approval,
reviewer-safe export review, maintenance cue freshness, advisory
provider/browser/dashboard/accessibility posture, and bounded local autonomy.

## Related Files

- [v16-operator-flow-compression-contract.md](./v16-operator-flow-compression-contract.md)
- [v16-operator-flow-audit.md](./v16-operator-flow-audit.md)
- [v16-flow-cockpit-evidence.md](./v16-flow-cockpit-evidence.md)
- [v16-release-gate.md](./v16-release-gate.md)
- [v16-dogfooding-summary.md](./v16-dogfooding-summary.md)
- [evidence-graph.md](./evidence-graph.md)
- [operator-queue.md](./operator-queue.md)
- [verification-orchestrator.md](./verification-orchestrator.md)
- [maintenance-cues.md](./maintenance-cues.md)
- [change-inventory.md](./change-inventory.md)
- [changeset-verification-readiness.md](./changeset-verification-readiness.md)
- [reviewer-evidence-bundles.md](./reviewer-evidence-bundles.md)
- [review-feedback.md](./review-feedback.md)
- [review-responses.md](./review-responses.md)
- [manual-evidence.md](./manual-evidence.md)
- [browser-accessibility-evidence.md](./browser-accessibility-evidence.md)
- [publication-boundary.md](./publication-boundary.md)
- [v15-release-candidate.md](./v15-release-candidate.md)
- [v15-repository-intelligence-contract.md](./v15-repository-intelligence-contract.md)
- [release-packaging.md](./release-packaging.md)
- [providers.md](./providers.md)
- [tasks-v16.md](./tasks-v16.md)
