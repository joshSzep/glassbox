# V14 Advisory Review Evidence Protocol

This protocol completes `GBX-1450` from [tasks-v14.md](./tasks-v14.md). It
defines how v14 collects fresh dashboard browser and accessibility evidence for
the matured local review loop without making that evidence deterministic
release authority.

Use this guide with
[browser-accessibility-evidence.md](./browser-accessibility-evidence.md), the
v14 boundary in
[v14-review-loop-maturity-contract.md](./v14-review-loop-maturity-contract.md),
and the dashboard behavior documented in [dashboard.md](./dashboard.md).

## Scope

The v14 advisory pass covers local UX confidence for review-loop maturity:

- changeset detail rendering
- feedback status and response-linked fixup inventory posture
- skipped advisory evidence display
- fixup inventory action states
- handoff readiness and safe next actions

It does not certify accessibility, prove WCAG conformance, approve review
feedback, clear publication readiness, or replace deterministic replay, eval,
package, unit, integration, frontend, or release-gate checks.

## Retained Evidence Location

Keep raw evidence local under `.glassbox/releases/`:

```text
.glassbox/releases/v14-advisory-review-evidence/
    browser/
        evidence.md
        summary.json
        screenshots/
    accessibility/
        evidence.md
        summary.json
    skipped/
        evidence.md
        summary.json
```

Only commit sanitized summaries. Do not commit raw `.glassbox` databases,
screenshots, browser profiles, local absolute paths, raw console logs,
credentials, provider output, transcripts, or private repository data.

## Scenario List

Run these scenarios when practical. If a scenario is not run, record the skip
with the template below rather than inventing live environment details.

| Scenario | Route or surface | Minimum observation |
| --- | --- | --- |
| Dashboard changeset detail | `/app/changesets/CHANGESET_ID` | Header, inventory, verification, review readiness, manual evidence, brief, and safe next actions render without overlap. |
| Feedback status | `Review Feedback` section | Missing, stale, accepted-risk, and ready-for-handoff response states remain visibly local and non-approval. |
| Skipped evidence display | `Manual Evidence Inbox`, verification cues, and handoff | `not_run` or `not_applicable` advisory evidence appears as skipped, not passed. |
| Fixup inventory action state | Feedback row `Record fixup` / `Refresh fixup` action | Pending, succeeded, failed, blocked, and stale states preserve inspect-first fallback copy. |
| Handoff readiness | `Final Handoff` section | Blockers, skipped live evidence, lifecycle brief posture, and safe commands remain visible before publication-adjacent action. |

## Browser Evidence Fields

Record these fields for a live dashboard or browser walkthrough:

- date and local time
- operator label
- Glassbox commit or version
- workspace alias
- route or target URL label
- environment label, such as `local-dev`, `production-build-local`, or
  `unknown` for skipped evidence
- browser name and version when available
- operating system and device class
- viewport width, height, and orientation
- input method
- console status: checked, not checked, unknown, or not applicable
- network or hydration warning status when inspected
- screenshots or recordings retained locally, if any
- scenario outcome
- skipped cases
- limitations
- non-claims

For observed browser or dashboard evidence, do not omit route, environment, or
viewport. For skipped evidence, record `unknown` or `not_applicable` instead of
fabricating a browser, viewport, route, or console pass.

## Accessibility Pairing Fields

Record these fields for an accessibility pairing pass:

- date and local time
- operator or reviewer labels
- route or surface
- viewport and orientation
- input method, including keyboard, mouse, touch, or screen reader pairing
- keyboard path checked
- focus-visible and focus-trap observations
- responsive wrapping or clipping observations
- contrast or reduced-motion observation when performed
- assistive technology name and version when used
- paired tool output label when retained
- observed issue, severity, and disposition
- skipped checks
- limitations
- non-claims

A focused keyboard pass, screen-reader spot check, axe run, contrast note, or
paired review is advisory unless a future fixture-backed gate explicitly
promotes it. Do not say "WCAG compliant", "accessibility certified", "fully
accessible", or "screen-reader certified".

## Manual Run Steps

1. Build or start a stable local dashboard path.
2. Select or create a local dogfooding changeset.
3. Inspect `glassbox changeset show CHANGESET_ID --cwd .` before browser work.
4. Open `/app/changesets/CHANGESET_ID`.
5. Walk the scenario list and record only what was actually observed.
6. Record skipped cases immediately when a viewport, console, keyboard,
   responsive, contrast, or screen-reader check is not run.
7. Attach observed or skipped evidence with `glassbox changeset evidence
   dashboard`, `glassbox changeset evidence browser`, or `glassbox changeset
   evidence accessibility` when practical.
8. Summarize retained local evidence in a reviewer-safe doc or dogfooding
   summary.

The protocol can be run manually even if Playwright is unavailable. A manual
run should still name browser, viewport, keyboard, responsive, console, and
accessibility pairing coverage explicitly.

## Skipped-Case Template

Use this when a live or paired check is intentionally skipped:

```markdown
## Skipped Advisory Evidence

- Scenario:
- Capture state: not_run | not_applicable
- Reason:
- Route or surface: unknown | not_applicable | <route>
- Browser: unknown | not_applicable | <browser>
- Viewport: unknown | not_applicable | <width>x<height>
- Console status: unknown | not_applicable | not checked
- Keyboard status: unknown | not_applicable | not checked
- Screen-reader status: unknown | not_applicable | not checked
- Claims not made:
- Safe command or protocol to collect later:
```

Example CLI capture:

```bash
glassbox changeset evidence dashboard CHANGESET_ID \
  --summary "v14 dashboard walkthrough intentionally skipped" \
  --source-label v14-advisory \
  --capture-state not_run \
  --skip-reason "local dashboard server was not started" \
  --skipped-case "unknown viewport" \
  --freshness needs_inspection \
  --cwd .
```

## Non-Claim Template

Every v14 advisory evidence summary should include these non-claims:

- advisory evidence is not deterministic release authority
- advisory evidence is not retained command evidence unless a retained tool
  output explicitly says so
- skipped browser, dashboard, or accessibility evidence is not a pass
- response-linked fixup inventory is not reviewer approval
- handoff readiness is local posture, not publication readiness
- accessibility notes are not certification or WCAG conformance
- Glassbox did not stage, commit, push, open a PR, merge, deploy, or publish

## Summary Shape

Use this reviewer-safe summary shape for committed docs:

```markdown
# V14 Advisory Review Evidence Summary

- Date:
- Operator:
- Glassbox commit:
- Evidence directory: .glassbox/releases/v14-advisory-review-evidence/<pass>/
- Dashboard scenario status: observed | skipped | partial
- Accessibility scenario status: observed | skipped | partial
- Deterministic checks cited separately:

## Observed Coverage

| Scenario | Status | Evidence | Limitations |
| --- | --- | --- | --- |

## Skipped Coverage

| Scenario | Capture state | Reason | Claims not made |
| --- | --- | --- | --- |

## Findings

| Area | Finding | Disposition |
| --- | --- | --- |

## Non-Claims

<Use the non-claim template above.>
```

## Release Boundary

Fresh advisory browser or accessibility evidence can strengthen v14
dogfooding confidence, but deterministic release authority still comes from
repeatable tests, replay/eval cases, package checks, release gates, and
documented summaries. A failed live walkthrough can block an operator's local
handoff decision, but it does not become a release gate unless a later task
defines a fixture-backed contract and pass/fail policy.
