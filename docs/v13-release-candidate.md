# Glassbox v13 Release Candidate

This page is the operator and contributor guide for the Glassbox v13
release-candidate track. It names the supported review-loop operating model,
validation path, evidence expectations, non-goals, residual risks, and release
decision without requiring readers to inspect the task graph.

## Release Posture

Glassbox v13 keeps the v12 reviewable-change model and adds the local feedback
loop that follows initial review. The release track adds review feedback
records, review response tracking, fixup inventory posture, manual evidence,
browser/dashboard and accessibility evidence attachments, lifecycle briefs,
handoff readiness, publication-boundary language, and integrated in-session
review-loop entry points.

The package version for this line remains `0.10.0`.

The primary product shape is:

- terminal chat remains the primary operator surface
- the dashboard remains the paired local cockpit and evidence surface
- SQLite canonical events remain the source of truth
- review feedback is local evidence, not remote review approval
- review responses distinguish handled feedback from approved changes
- manual evidence is summary-first and never backfilled as retained command
  proof
- browser, dashboard, and accessibility evidence is advisory unless promoted
  through deterministic fixture-backed contracts
- lifecycle briefs and handoff readiness are deterministic summaries, not proof
  that a reviewer approved or that publication happened
- publication posture never stages, commits, pushes, opens pull requests,
  merges, deploys, or publishes automatically
- deterministic replay, eval, package, and installed-wheel evidence remain
  release authority
- v13 is local-first review-loop evidence, not hosted code review or automatic
  PR automation

Use these discovery commands:

```bash
uv run glassbox command guide
uv run glassbox command tree
```

The v13 automated release-candidate gate is:

```bash
uv run python scripts/validate_v13_release_gate.py
```

For a non-mutating preview:

```bash
uv run python scripts/validate_v13_release_gate.py --dry-run
```

The retained evidence directory used for the current release-candidate pass is:

```text
.glassbox/releases/gbx-1393-v13-release-candidate/
```

The v13 eval artifacts for that candidate are retained under:

```text
.glassbox/evals/gbx-1393-v13-release-candidate/
```

Focused dogfooding evidence is summarized in
[v13-dogfooding-summary.md](./v13-dogfooding-summary.md). Local `.glassbox/`
evidence is workspace state and is not committed to git.

## Supported Operating Model

- **Review feedback**: `glassbox changeset feedback add`, `list`, `show`,
  `status`, `resolve`, `reopen`, `archive`, and `accept-risk` keep local
  requested changes, questions, notes, dispositions, and residual risks tied to
  a changeset.
- **Review responses**: feedback response status separates locally resolved,
  blocked, accepted-risk, reopened, and archived posture from approval or
  publication claims.
- **Fixup posture**: review-loop status and handoff readiness name stale or
  missing fixup inventory, verification, risk, and response evidence before
  any mutating next step.
- **Manual evidence**: `glassbox changeset evidence attach` records
  summary-first external checks, reviewer notes, sanitized logs, and local
  observations with source labels, freshness, limitations, and redaction.
- **Browser/dashboard evidence**: `glassbox changeset evidence browser` and
  `dashboard` record advisory walkthrough evidence with explicit route,
  viewport, console, screenshot, limitation, and non-claim posture.
- **Accessibility evidence**: `glassbox changeset evidence accessibility`
  records advisory keyboard, responsive, screen-reader, and accessibility
  notes without claiming certification or WCAG conformance.
- **Lifecycle briefs**: `glassbox changeset brief` summarizes feedback,
  responses, manual evidence, stale verification, risks, safe next actions,
  limitations, and non-claims from recorded local evidence.
- **Handoff readiness**: `glassbox changeset handoff-readiness` names the final
  local posture for review handoff without staging, committing, pushing,
  opening a pull request, merging, deploying, or publishing.
- **In-session review UX**: `/review`, `/changeset`, plain interactive mode,
  TUI command palette actions, and dashboard quick actions expose the
  review-loop workflow without forcing operators out of chat.

## Primary Operator Flows

### Review And Respond To A Local Change

```bash
uv run glassbox changeset create --from workspace-diff --session SESSION_ID --cwd .
uv run glassbox changeset feedback add CHANGESET_ID --kind requested_change --summary SUMMARY --cwd .
uv run glassbox changeset evidence attach CHANGESET_ID --summary SUMMARY --source-label LABEL --cwd .
uv run glassbox changeset verification-plan CHANGESET_ID --cwd .
uv run glassbox changeset feedback resolve FEEDBACK_ID --summary SUMMARY --cwd .
uv run glassbox changeset feedback status CHANGESET_ID --cwd .
uv run glassbox changeset handoff-readiness CHANGESET_ID --cwd .
```

The recommended order is create or refresh the changeset, record review
feedback, attach bounded manual evidence, preview verification, make any local
fixups explicitly, resolve or accept risk on feedback, then inspect handoff
readiness. Publication remains outside Glassbox automation.

### Attach Advisory Browser And Accessibility Evidence

```bash
uv run glassbox changeset evidence dashboard CHANGESET_ID --route ROUTE --viewport 1440x900 --cwd .
uv run glassbox changeset evidence browser CHANGESET_ID --route ROUTE --viewport 1440x900 --cwd .
uv run glassbox changeset evidence accessibility CHANGESET_ID --kind keyboard_review --summary SUMMARY --cwd .
```

These evidence records are useful for reviewers only when they include what was
checked, what was not checked, freshness, limitations, and non-claims. They are
not deterministic release authority.

### Prepare Final Handoff Evidence

```bash
uv run glassbox changeset refresh CHANGESET_ID --cwd .
uv run glassbox changeset feedback status CHANGESET_ID --cwd .
uv run glassbox changeset verification-plan CHANGESET_ID --cwd .
uv run glassbox changeset brief CHANGESET_ID --format markdown --cwd .
uv run glassbox changeset handoff-readiness CHANGESET_ID --cwd .
```

Safe handoff starts with inspection. If feedback is unresolved, verification is
stale, lifecycle brief generation fails, manual evidence is advisory-only, or
publication claims would be misleading, the readiness surface should say so.

## Release-Readiness Checklist

Before treating a build as the v13 release candidate, complete this list:

- The v13 review-loop contract, audit, UX audit, release gate, dogfooding
  summary, and release-candidate guide are linked from the docs hub.
- `uv run python scripts/validate_v13_release_gate.py` passes and writes
  `summary.json` with `blocking` and `advisory` sections.
- The deterministic `release-candidate` eval profile passes with 22 selected
  cases, including `changeset.review-loop-lifecycle` and
  `changeset.in-session-review-ux`.
- `glassbox eval audit --profile release-candidate --cwd .` reports no
  uncovered release-candidate capabilities.
- Review feedback, responses, manual evidence, browser/dashboard evidence,
  accessibility evidence, lifecycle briefs, handoff readiness, publication
  non-claims, and in-session review entry points have unit, integration,
  frontend, and deterministic eval coverage where promoted.
- Generated OpenAPI/types and dashboard static assets are fresh and packaged.
- Built wheel and sdist contents include release docs, eval fixtures, scripts,
  generated API files, and dashboard static assets.
- Dogfooding findings have dispositions as fixes, docs, tests/evals, accepted
  risks, or post-v13 follow-ups.
- Provider canaries, live browser/dashboard evidence, and accessibility
  evidence are either retained as advisory evidence or explicitly skipped with
  bounded reasons.
- Raw `.glassbox` state is not committed; reviewer-safe summaries are used for
  handoff and release review.

## Current Evidence Summary

The current retained v13 evidence shows:

- non-dry-run v13 gate: passed for `GBX-1393`, with final evidence retained at
  `.glassbox/releases/gbx-1393-v13-release-candidate/summary.json`; 85 blocking
  stages passed and three advisory evidence items were explicitly skipped
- package contents validation: wheel and sdist include required release files,
  generated API files, eval fixtures, release scripts, and dashboard static
  assets
- installed-wheel smoke: passed for `glassbox-0.10.0-py3-none-any.whl`,
  including terminal, command, chat, autonomy, task, readiness, provider,
  memory, repository index, background job, branch-search, daemon, eval, and
  dashboard smoke checks
- release sign-off report: `commit-smoke`, `push-confirmation`, and
  `release-candidate` profiles passed with 39/39 capabilities covered
- release-candidate eval profile: `22/22` selected cases passed with profile
  budget OK
- v13 review-loop release profile: passed at
  `.glassbox/evals/gbx-1393-v13-release-candidate/v13-review-loop-release/`
- v13 review-loop smoke: `changeset.review-loop-lifecycle` and
  `changeset.in-session-review-ux` both passed
- v13 eval coverage audit: release-candidate coverage reported no uncovered
  capabilities
- review-loop command coverage: focused plain interactive and TUI review tests
  passed inside the v13 gate
- dogfooding: findings and follow-up candidates are triaged in
  [v13-dogfooding-summary.md](./v13-dogfooding-summary.md)
- provider evidence: optional and advisory; the v13 gate retained an explicit
  structured skip because provider canaries were not requested for this run
- browser/dashboard and accessibility evidence: optional and advisory; the v13
  gate retained explicit structured skips, while `GBX-1392` retained bounded
  skipped-evidence dogfooding notes

## Known Residual Risks

- Review feedback is local evidence. It does not prove a human approved the
  change and does not synchronize with hosted review state.
- Review response tracking can remain conservative when no response-linked
  fixup inventory is attached. `GBX-1392` found that the CLI path for that
  inventory should be easier to discover or document.
- Lifecycle brief generation has a known rich-evidence edge case: the dogfooded
  review-loop changeset exceeded the current 20-item limitation cap and failed
  artifact validation.
- Manual evidence is only as trustworthy as its source labels, summaries,
  redaction posture, limitations, freshness, and non-claims.
- Browser/dashboard evidence and accessibility evidence are advisory. Skipped
  or manual evidence is not a substitute for a live browser walkthrough,
  keyboard review, responsive review, screen-reader pairing, certification, or
  WCAG conformance.
- Provider canaries and provider recommendations are advisory. This release
  candidate did not make live-provider behavior blocking release authority.
- Repository intelligence, workspace memory, and local observability posture can
  be stale or degraded in a working checkout without failing deterministic
  release authority; operators should inspect freshness before relying on those
  cues for current work.
- Handoff readiness and publication-boundary guidance are advisory local
  posture. They do not stage, commit, push, open pull requests, merge, deploy,
  publish, or prove publication readiness.
- v13 does not remove inherited bounded-autonomy limits from earlier milestones.

## Deliberate Non-Goals

v13 does not introduce hosted code review, hosted workspace ownership,
multi-user remote collaboration state, review approval automation, automatic
staging, automatic commits, automatic pushes, automatic pull request creation,
automatic merges, automatic deployment, automatic publication, provider
reliability guarantees, broad accessibility certification, WCAG conformance
claims, or indefinite unattended autonomy.

## Release Decision

Decision: GO for v13 release candidate publication.

Decision date: 2026-05-03.

Candidate build reviewed: `GBX-1393` release-candidate working tree with final
v13 gate evidence retained locally.

Retained evidence:

```text
.glassbox/releases/gbx-1393-v13-release-candidate/
.glassbox/evals/gbx-1393-v13-release-candidate/
.glassbox/releases/gbx-1392-dogfooding/
```

Final pass/fail state:

| Area | State | Evidence |
| --- | --- | --- |
| Automated v13 gate | passed | `.glassbox/releases/gbx-1393-v13-release-candidate/summary.json` |
| Deterministic eval release report | passed | `.glassbox/evals/gbx-1393-v13-release-candidate/v13-release-signoff/` |
| V13 review-loop release profile | passed | `.glassbox/evals/gbx-1393-v13-release-candidate/v13-review-loop-release/` |
| V13 review-loop eval smoke | passed | `.glassbox/evals/gbx-1393-v13-release-candidate/v13-review-loop-smoke/` |
| V13 review-loop command coverage | passed | `tests/unit/test_cli_interactive_session.py tests/integration/test_cli_tui_review_commands.py tests/integration/test_cli_interactive_commands.py -k review` |
| Release-candidate eval coverage | passed | `glassbox eval audit --profile release-candidate --cwd .` in the v13 gate |
| Package and installed smoke | passed | package contents validation plus installed-wheel smoke in the v13 gate |
| Dogfooding disposition | passed triage | [v13-dogfooding-summary.md](./v13-dogfooding-summary.md) |
| Provider posture | advisory skipped | v13 gate advisory provider evidence section |
| Browser/dashboard posture | advisory skipped | v13 gate advisory browser evidence section plus dogfooding notes |
| Accessibility posture | advisory skipped | v13 gate advisory accessibility evidence section plus dogfooding notes |
| Residual risk review | accepted | known residual risks listed above |

No deterministic blocker remains open for v13 release-candidate publication.
The accepted residual risks stay bounded to local feedback non-approval,
response-linked fixup inventory discoverability, lifecycle-brief limitation
overflow, manual evidence limits, advisory provider/browser/accessibility
posture, stale local knowledge cues, publication-boundary non-claims, and
bounded local autonomy.

## Related Files

- [v13-review-loop-contract.md](./v13-review-loop-contract.md)
- [v13-review-loop-audit.md](./v13-review-loop-audit.md)
- [v13-review-loop-ux-audit.md](./v13-review-loop-ux-audit.md)
- [v13-release-gate.md](./v13-release-gate.md)
- [v13-dogfooding-summary.md](./v13-dogfooding-summary.md)
- [review-feedback.md](./review-feedback.md)
- [review-responses.md](./review-responses.md)
- [manual-evidence.md](./manual-evidence.md)
- [browser-accessibility-evidence.md](./browser-accessibility-evidence.md)
- [publication-boundary.md](./publication-boundary.md)
- [v12-reviewable-change-contract.md](./v12-reviewable-change-contract.md)
- [replay-evals.md](./replay-evals.md)
- [providers.md](./providers.md)
- [release-packaging.md](./release-packaging.md)
- [tasks-v13.md](./tasks-v13.md)
