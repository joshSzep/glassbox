# Glassbox v14 Release Candidate

This page is the operator and contributor guide for the Glassbox v14
release-candidate track. It names the supported review-loop maturity operating
model, validation path, evidence expectations, advisory evidence boundaries,
residual risks, deliberate non-goals, and release decision without requiring
readers to inspect the task graph.

## Release Posture

Glassbox v14 keeps the v13 local review-loop model and matures the places where
dogfooding found friction. The release track improves rich lifecycle briefs,
response-linked fixup inventory, skipped advisory evidence, command discovery,
dashboard action states, handoff readiness, deterministic v14 eval coverage,
and release-gate evidence while preserving the local-first publication
boundary.

The package version for this line remains `0.10.0`. Per
[version-release-policy.md](./version-release-policy.md), v14 is a milestone
and release-evidence track on the existing pre-1.0 package line, not a package
version bump by itself.

The primary product shape is:

- terminal chat remains the primary operator surface
- the dashboard remains the paired local cockpit and evidence surface
- SQLite canonical events and managed artifacts remain the source of truth
- review feedback is local evidence, not remote review approval
- response-linked fixup inventory explains which changed paths respond to
  feedback without proving reviewer acceptance
- skipped browser, dashboard, and accessibility evidence is honest advisory
  evidence about what was not run, not a passing observation
- lifecycle briefs summarize rich limitations before reviewer-safe artifact
  validation while keeping retained evidence visible
- handoff readiness is inspection posture, not publication readiness
- publication posture never stages, commits, pushes, opens pull requests,
  merges, deploys, or publishes automatically
- deterministic replay, eval, package, frontend, installed-wheel, and release
  gate evidence remain release authority
- v14 is local-first review-loop maturity, not hosted code review, provider
  reliability certification, accessibility certification, or PR automation

Use these discovery commands:

```bash
uv run glassbox command guide
uv run glassbox command tree
```

The v14 automated release-candidate gate is:

```bash
uv run python scripts/validate_v14_release_gate.py
```

For a non-mutating preview:

```bash
uv run python scripts/validate_v14_release_gate.py --dry-run
```

The retained evidence directory used for the current release-candidate pass is:

```text
.glassbox/releases/gbx-1463-v14-release-candidate/
```

The v14 eval artifacts for that candidate are retained under:

```text
.glassbox/evals/gbx-1463-v14-release-candidate/
```

Focused dogfooding evidence is summarized in
[v14-dogfooding-summary.md](./v14-dogfooding-summary.md). Local `.glassbox/`
evidence is workspace state and is not committed to git.

## Supported Operating Model

- **Rich lifecycle briefs**: `glassbox changeset brief` summarizes feedback,
  responses, manual evidence, skipped live evidence, verification posture,
  risks, safe next actions, publication boundaries, and limitation overflow
  without exceeding the reviewer-safe artifact cap.
- **Response-linked fixup inventory**:
  `glassbox changeset feedback fixup FEEDBACK_ID --from-workspace --cwd .`
  records bounded changed-path evidence for one feedback response. Repeated
  `--path` values can record explicit operator-selected paths.
- **Feedback response status**:
  `glassbox changeset feedback status CHANGESET_ID --cwd .` explains missing,
  stale, attached, mismatched, accepted-risk, and ready-for-handoff posture
  without claiming reviewer approval.
- **Skipped advisory dashboard and browser evidence**:
  `glassbox changeset evidence dashboard` and `browser` can record
  `--capture-state not_run` with skipped cases and limitations instead of
  inventing viewport, console, screenshot, or route observations.
- **Skipped advisory accessibility evidence**:
  `glassbox changeset evidence accessibility --capture-state not_run` records
  skipped keyboard, responsive, screen-reader, contrast, or assistive
  technology checks without claiming certification or WCAG conformance.
- **Dashboard action states**: the changeset dashboard surfaces missing fixup
  inventory, stale inventory, skipped evidence, accepted risk, verification
  posture, and handoff blockers as inspection states, not approval or
  publication decisions.
- **Handoff readiness**:
  `glassbox changeset handoff-readiness CHANGESET_ID --cwd .` names blockers,
  local-only evidence, skipped live evidence, stale verification, unresolved
  risk, and safe next commands before any final operator action.
- **In-session review UX**: `/review`, `/changeset`, plain interactive mode,
  the TUI command palette, and dashboard actions expose the review-loop path
  while keeping mutation and publication explicit.

## Primary Operator Flows

### Review And Respond To Feedback

```bash
uv run glassbox changeset create --from workspace-diff --session SESSION_ID --cwd .
uv run glassbox changeset refresh CHANGESET_ID --cwd .
uv run glassbox changeset feedback add CHANGESET_ID --kind requested_change --summary SUMMARY --cwd .
uv run glassbox changeset feedback status CHANGESET_ID --cwd .
uv run glassbox changeset feedback fixup FEEDBACK_ID --from-workspace --cwd .
uv run glassbox changeset feedback resolve FEEDBACK_ID --summary SUMMARY --cwd .
uv run glassbox changeset feedback status CHANGESET_ID --cwd .
```

The recommended order is inspect, refresh, record feedback, inspect response
status, record response-linked inventory, then resolve or accept risk. Fixup
inventory is response evidence, not reviewer acceptance.

### Record Skipped Advisory Evidence

```bash
uv run glassbox changeset evidence dashboard CHANGESET_ID \
  --capture-state not_run \
  --skip-reason REASON \
  --skipped-case CASE \
  --cwd .
uv run glassbox changeset evidence browser CHANGESET_ID \
  --capture-state not_run \
  --skip-reason REASON \
  --skipped-case CASE \
  --cwd .
uv run glassbox changeset evidence accessibility CHANGESET_ID \
  --kind responsive_review \
  --capture-state not_run \
  --skip-reason REASON \
  --skipped-case CASE \
  --cwd .
```

Skipped evidence must name what was not run and which claims remain unmade. It
is valid advisory evidence, but it is not a browser pass, dashboard pass,
accessibility pass, release gate, certification, or deterministic proof.

### Prepare Final Review Handoff

```bash
uv run glassbox changeset refresh CHANGESET_ID --cwd .
uv run glassbox changeset feedback status CHANGESET_ID --cwd .
uv run glassbox changeset verification-plan CHANGESET_ID --cwd .
uv run glassbox changeset brief CHANGESET_ID --format markdown --cwd .
uv run glassbox changeset handoff-readiness CHANGESET_ID --cwd .
```

Safe handoff starts with inspection. Missing verification, stale inventory,
unresolved risk, skipped live evidence, local-only evidence, or publication
claim ambiguity should stay visible.

## Release-Readiness Checklist

Before treating a build as the v14 release candidate, complete this list:

- The v14 maturity contract, audit, advisory review protocol, advisory
  dashboard evidence, advisory accessibility evidence, dogfooding summary,
  release gate, release-candidate guide, and task graph are linked from the
  docs hub.
- `uv run python scripts/validate_v14_release_gate.py` passes and writes
  `summary.json` with blocking and advisory sections.
- The deterministic `release-candidate` eval profile passes with 25 selected
  cases, including `changeset.lifecycle-rich-evidence`,
  `changeset.response-linked-fixup-inventory`, and
  `changeset.skipped-advisory-evidence-posture`.
- `glassbox eval audit --profile release-candidate --cwd .` reports no
  uncovered release-candidate capabilities.
- Lifecycle brief overflow, response-linked fixup inventory, skipped advisory
  evidence, feedback response status, handoff readiness, CLI/API/TUI/dashboard
  action states, and docs guidance have focused tests or deterministic eval
  evidence where promoted.
- Generated OpenAPI/types and dashboard static assets are fresh and packaged.
- Built wheel and sdist contents include v14 release docs, eval fixtures,
  release scripts, generated API files, and dashboard static assets.
- Dogfooding findings have dispositions as fixes, docs, tests/evals, accepted
  risks, or post-v14 follow-ups.
- Provider canaries, live browser/dashboard evidence, and accessibility
  evidence are either retained as advisory evidence or explicitly skipped with
  bounded reasons.
- Raw `.glassbox` state is not committed; reviewer-safe summaries are used for
  handoff and release review.

## Current Evidence Summary

The current retained v14 evidence shows:

- v14 release gate for `GBX-1463`: passed at
  `.glassbox/releases/gbx-1463-v14-release-candidate/summary.json` with 91
  passing blocking stages, one skipped advisory provider item, two retained
  advisory UX records, package contents validation, and installed-wheel smoke
  coverage
- v14 release-gate dry run during `GBX-1461`: passed with inherited v13
  deterministic stages plus v14 maturity stages, provider evidence skipped by
  default, and dashboard/accessibility advisory evidence recorded
- v14 dogfooding release-gate dry run during `GBX-1462`: passed at
  `.glassbox/releases/gbx-1462-v14-dogfooding/v14-gate-dry-run/summary.json`
  with 68 planned blocking stages, one skipped provider advisory item, and two
  recorded retained advisory UX items
- post-v14 refactor closeout dry run: passed at
  `.glassbox/releases/20260508T024947Z-v14-gate/summary.json` after the
  lifecycle brief, review response, readiness, terminal, web, frontend, and
  v14 release-gate helper splits, with 68 planned blocking stages and the same
  advisory evidence posture
- v14 dogfooding: findings and follow-up candidates are triaged in
  [v14-dogfooding-summary.md](./v14-dogfooding-summary.md)
- lifecycle brief maturity: the dogfooding brief generated successfully and
  summarized rich limitations instead of failing the 20-item artifact cap
- response-linked fixup inventory: dogfooding recorded a fresh workspace fixup
  inventory, matched the feedback-scoped path, and kept non-approval claims
  visible
- skipped advisory evidence: dogfooding recorded skipped dashboard, browser,
  and accessibility evidence without fabricating live observations
- dashboard action-state confidence: focused frontend coverage passed for
  `changeset-console.test.tsx` and `operator-actions.component.test.tsx` with
  128 tests passing during `GBX-1462`
- deterministic v14 evals: `changeset.lifecycle-rich-evidence`,
  `changeset.response-linked-fixup-inventory`, and
  `changeset.skipped-advisory-evidence-posture` are included in the
  release-candidate profile and v14 gate smoke stage
- package contents: the release package guardrail requires the v14 eval cases,
  v14 release gate scripts, and v14 release docs
- provider evidence: optional and advisory; the v14 gate records provider
  canaries as skipped by default unless explicitly requested
- browser/dashboard and accessibility evidence: advisory; retained `GBX-1451`
  and `GBX-1452` summaries provide bounded fresh UX confidence, while skipped
  evidence stays visible as limitations

## Known Residual Risks

- Review feedback is local evidence. It does not prove a human approved the
  change and does not synchronize with hosted review state.
- Response-linked fixup inventory explains which paths respond to feedback,
  but it does not prove reviewer acceptance or verification success.
- `GBX-1462` found command-discovery friction: `command guide` does not accept
  `--cwd` or `--db-path`, the fixup example should include `--from-workspace`
  or `--path`, and workspace-diff changeset examples should keep the
  `--session` requirement visible.
- Manual evidence is only as trustworthy as its source labels, summaries,
  redaction posture, limitations, freshness, and non-claims.
- Skipped browser, dashboard, and accessibility evidence is valid advisory
  posture, but it is not a live browser walkthrough, keyboard review,
  responsive review, screen-reader pairing, accessibility certification, or
  WCAG conformance claim.
- Retained `GBX-1451` and `GBX-1452` UX evidence covers bounded scenarios,
  dates, tools, viewports, and limitations. It is not broad browser,
  dashboard, or accessibility certification.
- Provider canaries and provider recommendations are advisory. This release
  candidate does not make live-provider behavior blocking release authority.
- Repository intelligence, workspace memory, and local observability posture can
  be stale or degraded in a working checkout without failing deterministic
  release authority; operators should inspect freshness before relying on those
  cues for current work.
- Handoff readiness and publication-boundary guidance are advisory local
  posture. They do not stage, commit, push, open pull requests, merge, deploy,
  publish, or prove publication readiness.
- v14 does not remove inherited bounded-autonomy limits from earlier
  milestones.

## Deliberate Non-Goals

v14 does not introduce hosted code review, hosted workspace ownership,
multi-user remote collaboration state, automatic review approval, automatic
staging, automatic commits, automatic pushes, automatic pull request creation,
automatic branch-search merging, automatic rebasing, automatic force-pushing,
automatic deployment, automatic package publication, provider reliability
guarantees, broad accessibility certification, WCAG conformance claims, live
browser release authority, or indefinite unattended autonomy.

## Release Decision

Decision: GO for v14 release candidate publication.

Decision date: 2026-05-07.

Candidate build reviewed: `GBX-1463` release-candidate working tree with final
v14 gate evidence retained locally.

Retained evidence:

```text
.glassbox/releases/gbx-1463-v14-release-candidate/
.glassbox/evals/gbx-1463-v14-release-candidate/
.glassbox/releases/gbx-1462-v14-dogfooding/
.glassbox/releases/v14-advisory-review-evidence/
```

Final pass/fail state:

| Area | State | Evidence |
| --- | --- | --- |
| Automated v14 gate | passed | `.glassbox/releases/gbx-1463-v14-release-candidate/summary.json` |
| Deterministic eval release report | passed | `.glassbox/evals/gbx-1463-v14-release-candidate/v14-release-signoff/` |
| V14 review-loop maturity profile | passed | `.glassbox/evals/gbx-1463-v14-release-candidate/v14-review-loop-maturity-release/` |
| V14 review-loop maturity eval smoke | passed | `.glassbox/evals/gbx-1463-v14-release-candidate/v14-review-loop-maturity-smoke/` |
| V14 CLI/API review-loop coverage | passed | `tests/integration/test_cli_interactive_commands.py tests/integration/test_cli_tui_review_commands.py tests/integration/test_web_changeset_routes.py -k review or feedback or evidence or accessibility` |
| V14 dashboard maturity coverage | passed | `pnpm --dir frontend test -- changeset-console.test.tsx operator-actions.component.test.tsx` |
| Release-candidate eval coverage | passed | `glassbox eval audit --profile release-candidate --cwd .` in the v14 gate |
| Package and installed smoke | passed | package contents validation plus installed-wheel smoke in the v14 gate |
| Dogfooding disposition | passed triage | [v14-dogfooding-summary.md](./v14-dogfooding-summary.md) |
| Provider posture | advisory skipped by default | v14 gate advisory provider evidence section |
| Browser/dashboard posture | advisory retained and skipped as bounded evidence | [v14-advisory-dashboard-evidence.md](./v14-advisory-dashboard-evidence.md) plus dogfooding skipped evidence |
| Accessibility posture | advisory retained and skipped as bounded evidence | [v14-advisory-accessibility-evidence.md](./v14-advisory-accessibility-evidence.md) plus dogfooding skipped evidence |
| Residual risk review | accepted | known residual risks listed above |

No deterministic blocker remains open for v14 release-candidate publication.
The accepted residual risks stay bounded to local feedback non-approval,
response-linked inventory limits, command-discovery friction, manual evidence
limits, advisory provider/browser/dashboard/accessibility posture, stale local
knowledge cues, publication-boundary non-claims, and bounded local autonomy.

## Related Files

- [v14-review-loop-maturity-contract.md](./v14-review-loop-maturity-contract.md)
- [v14-review-loop-maturity-audit.md](./v14-review-loop-maturity-audit.md)
- [v14-advisory-review-evidence.md](./v14-advisory-review-evidence.md)
- [v14-advisory-dashboard-evidence.md](./v14-advisory-dashboard-evidence.md)
- [v14-advisory-accessibility-evidence.md](./v14-advisory-accessibility-evidence.md)
- [v14-dogfooding-summary.md](./v14-dogfooding-summary.md)
- [review-feedback.md](./review-feedback.md)
- [review-responses.md](./review-responses.md)
- [manual-evidence.md](./manual-evidence.md)
- [browser-accessibility-evidence.md](./browser-accessibility-evidence.md)
- [publication-boundary.md](./publication-boundary.md)
- [v13-review-loop-contract.md](./v13-review-loop-contract.md)
- [v13-release-candidate.md](./v13-release-candidate.md)
- [replay-evals.md](./replay-evals.md)
- [providers.md](./providers.md)
- [release-packaging.md](./release-packaging.md)
- [tasks-v14.md](./tasks-v14.md)
