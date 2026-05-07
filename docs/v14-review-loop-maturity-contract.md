# Glassbox v14 Review-Loop Maturity Contract

This page defines the v14 product contract for maturing the v13 local review
loop after the v13 release candidate and post-v13 refactor. It is the operator
and contributor boundary for the v14 planning track in
[tasks-v14.md](./tasks-v14.md).

v14 does not expand Glassbox into hosted review, approval automation, pull
request automation, or publication automation. It keeps the v13 local-first
review-loop model and improves the daily operator path where dogfooding showed
friction: rich lifecycle briefs, response-linked fixup inventory, intentionally
skipped advisory evidence, review-loop command discovery, and fresh advisory UX
evidence.

## Scope

Glassbox v14 focuses on review-loop maturity:

- summarize rich lifecycle limitations before reviewer-safe brief validation
  while preserving raw retained evidence in canonical events and managed
  artifacts
- make response-linked fixup inventory a first-class operator path for
  explaining which changed paths respond to feedback
- record skipped advisory browser, dashboard, and accessibility evidence
  without fabricating viewport, browser, console, keyboard, screen-reader, or
  responsive observations
- refresh command help, command-guide, plain interactive, TUI, dashboard, and
  operator docs copy around the review-loop happy path
- retain fresh advisory browser/dashboard and accessibility evidence when the
  team wants UX confidence, while keeping skipped advisory evidence acceptable
  for deterministic release gates
- promote only stable, deterministic maturity behavior into replay, eval,
  package, and release-gate coverage
- preserve the v13 local evidence, non-approval, handoff readiness, and
  publication-boundary model

The v14 contract builds directly on
[v13-review-loop-contract.md](./v13-review-loop-contract.md). The v13 contract
remains the baseline product model for review feedback, requested changes,
fixup responses, manual evidence, browser evidence, accessibility evidence,
lifecycle briefs, handoff readiness, and publication boundaries. v14 changes
ergonomics and resilience; it does not change who owns final action.

## Vocabulary Deltas

Use the v13 vocabulary unless this table narrows a term for v14 maturity work.

| Term | Operator meaning | Copy boundary |
| --- | --- | --- |
| Response-linked fixup inventory | Retained local evidence that names changed paths, summaries, and freshness posture connected to one or more feedback responses. | It explains what changed in response to feedback. It is not reviewer acceptance, approval, staging, commit, push, or PR readiness. |
| Skipped advisory evidence | A browser, dashboard, or accessibility evidence record whose live pass was intentionally not run, unknown, or not applicable. | Show it as skipped, not run, unknown, or not applicable. Do not call it passed, verified, accessible, certified, or deterministic proof. |
| Summarized lifecycle limitations | A deterministic lifecycle-brief summary that deduplicates, groups, caps, or summarizes retained limitations and non-claims before artifact validation. | It is a reviewer-safe compression of retained evidence. It must not silently drop blockers or pretend raw evidence disappeared. |
| Fresh advisory UX evidence | A bounded live browser/dashboard walkthrough or accessibility pairing pass retained during v14 dogfooding or release-candidate review. | It strengthens confidence only for the inspected scenario, date, environment, and limitations. It is not release authority unless later promoted as a fixture-backed deterministic contract. |

Keep these distinctions clear across CLI help, dashboard copy, API
descriptions, tests, eval fixtures, release evidence, and docs:

- A **response-linked fixup inventory** can make response status more useful,
  but it does not prove a reviewer accepted the fix.
- **Skipped advisory evidence** is honest evidence about what was not run, not a
  substitute for live browser, dashboard, keyboard, focus, contrast, or
  screen-reader observations.
- A **summarized lifecycle limitation** must retain count, reason, and enough
  context for review without exceeding artifact schema limits.
- **Fresh advisory UX evidence** is local confidence evidence beside
  deterministic gates, not an automatic release blocker or release pass.

## Supported Workflow Set

v14 supports the same local review-loop lifecycle as v13, with maturity updates
in the operator path:

1. An operator creates or refreshes a local changeset from retained local
   evidence.
2. The operator records review feedback, requested changes, reviewer questions,
   observations, or risks as local evidence.
3. The operator inspects verification posture and attached evidence before
   choosing any mutation.
4. The operator performs fixups outside hidden approval automation.
5. Glassbox records response text and response-linked fixup inventory that
   names changed paths, stale verification posture, limitations, safe next
   actions, and non-claims.
6. The operator records manual, browser, dashboard, accessibility, skipped, or
   not-applicable advisory evidence with source labels and bounded claims.
7. Glassbox generates lifecycle briefs that summarize rich limitations
   deterministically and keep unresolved feedback, stale checks, skipped
   evidence, accepted risks, and non-claims visible.
8. Glassbox explains handoff readiness and publication-boundary posture before
   any final operator action.

The review-loop happy path should be discoverable from `glassbox command guide`,
command help, `/review`, `/changeset`, the TUI command palette, dashboard
actions, and operator docs. Guidance should name safe inspection commands before
mutating commands.

## Evidence Expectations

v14 keeps the v13 split between deterministic release evidence and advisory
confidence evidence.

Blocking deterministic evidence includes:

- unit and integration tests for lifecycle limitation summarization
- CLI, API, TUI, dashboard, and generated-type tests when response-linked
  fixup inventory or skipped evidence surfaces change
- deterministic tests for response status, stale verification, accepted-risk
  states, handoff posture, redaction, exports, and lifecycle briefs
- replay and eval fixtures only for stable maturity behavior that can be
  tested without live browser, accessibility, provider, or manual judgment
- a v14 release gate or documented v13 gate extension with blocking and
  advisory sections

Advisory evidence includes:

- fresh browser or dashboard walkthrough notes
- accessibility pairing notes covering keyboard, focus, responsive, contrast,
  or assistive-technology checks when actually run
- explicit skipped-case records for live browser, dashboard, accessibility, or
  provider evidence
- dogfooding findings from realistic local review-loop work
- manual evidence from external commands, sanitized logs, screenshots, or
  operator observations

Manual, live browser, dashboard, accessibility, provider, and dogfooding
evidence can strengthen confidence only when retained evidence names the
workflow, source, date, environment, skipped cases, limitations, and bounded
claim. They do not replace deterministic release authority unless a future
task defines a repeatable fixture-backed contract with a failure policy.

## Advisory Evidence Boundaries

Skipped advisory evidence is valid when it is explicit and bounded. Operators
may record unknown, not-run, or not-applicable environment details when they
intentionally did not inspect a live browser, dashboard route, console,
keyboard path, responsive viewport, contrast pairing, or assistive technology.

The evidence record should preserve:

- what was skipped or unknown
- why it was skipped, unknown, or not applicable
- which claims remain unmade
- which safe command or protocol can collect fresh evidence later
- whether the evidence is local-only, manual, advisory, rejected, accepted with
  risk, or ready for handoff

Skipped advisory evidence must remain visually and textually distinct from
passed deterministic checks and from fresh live observations.

## Release Authority

Deterministic replay, eval, package, migration, unit, integration, CLI, API,
frontend, and release-gate evidence remain the blocking release authority for
v14 maturity behavior.

Fresh browser/dashboard walkthroughs, accessibility pairing, manual evidence,
provider canaries, and dogfooding summaries remain advisory unless a future
task promotes a narrow fixture-backed contract with repeatable inputs and an
explicit pass/fail policy.

Response-linked fixup inventory, resolved feedback, accepted risk, lifecycle
briefs, and handoff readiness are local evidence and local posture. They do not
mean a reviewer approved the change, a pull request is ready, or Glassbox has
staged, committed, pushed, opened a pull request, merged, deployed, or
published anything.

## Safety Rules

The v14 safety model inherits v13's local-first and event-sourced boundaries:

- Canonical events and managed artifacts remain the source of truth.
- Projections, API responses, dashboard state, CLI output, briefs, and exports
  must be rebuildable views.
- One local mutation owner should control the workspace at a time.
- Review-loop guidance starts with safe inspection before any mutation.
- Reviewer-facing artifacts must be redacted or explicitly local-only.
- Manual evidence remains labeled as manual and never becomes retained
  Glassbox-run command evidence by implication.
- Browser, dashboard, accessibility, provider, and dogfooding evidence must
  name bounded claims and non-claims.
- Skipped evidence must stay visible as skipped, not run, unknown, or not
  applicable rather than hidden under passing posture.

Do not say Glassbox approved, staged, committed, pushed, opened a PR, merged,
deployed, published, certified accessibility, verified a browser, or completed
provider validation unless retained evidence supports that exact claim.

## V13 Dogfooding Mapping

[v13-dogfooding-summary.md](./v13-dogfooding-summary.md) is the direct input to
the first v14 implementation slices.

| v13 finding | v14 maturity response |
| --- | --- |
| Stale `dogfood:local` provider prefix in dogfooding commands. | Refresh command-guide and dogfooding copy around supported provider prefixes and deterministic local recipes. |
| Dashboard skipped evidence required a concrete `WIDTHxHEIGHT` viewport. | Add skipped advisory evidence model and CLI/API support for unknown or not-applicable environment details. |
| Lifecycle brief generation failed when limitations exceeded the 20-item artifact cap. | Characterize the overflow and summarize lifecycle limitations before artifact validation. |
| `feedback resolve` lacked a discoverable response-linked fixup inventory path. | Define and implement first-class CLI, interactive, TUI, API, and dashboard fixup inventory paths. |
| Feedback status stayed conservative after local resolution without fixup inventory. | Improve response status to distinguish missing, stale, attached, accepted-risk, and ready-for-handoff posture without implying approval. |
| No fresh live browser or accessibility pairing pass was run. | Define a repeatable advisory evidence protocol and retain fresh or explicitly skipped v14 UX evidence. |

## Non-Goals

v14 deliberately does not introduce:

- hosted code review
- hosted review comment synchronization
- cloud workspace authority
- remote worker fleets
- simultaneous multi-writer mutation
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
- turning skipped browser or accessibility evidence into passing evidence
- hidden provider-side memory
- cross-repository memory sync
- indefinite unattended autonomy

These non-goals can be revisited only through a future product contract with a
new safety model, evidence policy, collaboration boundary, and explicit
operator semantics.
