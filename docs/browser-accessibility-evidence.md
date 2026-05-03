# Browser, Dashboard, And Accessibility Evidence Protocol

Browser, dashboard, and accessibility evidence is local live-review evidence.
It records what an operator observed in a real UI, a browser session, a
screenshot, a keyboard pass, a responsive layout pass, or a paired
accessibility review. It can strengthen a review loop, but it is advisory
unless a later task promotes a deterministic, fixture-backed gate.

Live review evidence is not deterministic release authority, not retained
command evidence, not reviewer approval, not publication authority, and not
accessibility certification. It should help the next operator inspect what was
seen, what was skipped, and what remains uncertain.

## Evidence Kinds

Use these kinds when later tasks add events, artifacts, CLI workflows, API
routes, dashboard rows, lifecycle briefs, or evidence bundles:

| Kind | Purpose | Required boundary |
| --- | --- | --- |
| `live_dashboard_walkthrough` | Operator walks through a dashboard route or task flow in a running app. | Include environment, route, data fixture or live workspace label, date, operator, viewport, skipped cases, limitations, and non-claims. |
| `browser_check` | Operator checks a browser-rendered page, interaction, or console state. | Record browser, OS, route, target URL label, viewport, result summary, and whether devtools or console output was inspected. |
| `screenshot_evidence` | Screenshot metadata supports a specific observation. | Retain metadata and local-only path first; raw images remain local-only until an export policy reviews them. |
| `keyboard_navigation_note` | Operator records tab order, focus visibility, shortcut behavior, or keyboard-only reachability. | Name the starting element, expected path, observed path, blocked controls, skipped areas, and whether assistive technology was also used. |
| `responsive_layout_observation` | Operator records layout behavior at one or more viewport sizes. | Name each viewport, orientation when relevant, route, observed overflow or clipping, and any untested breakpoint. |
| `accessibility_pairing` | Operator pairs manual accessibility notes with deterministic output, another reviewer, or a focused tool report. | Keep the manual note advisory unless the paired tool output is retained as a deterministic check; avoid broad conformance claims. |

## Required Fields

Every live review evidence record should carry:

- evidence kind
- bounded summary
- attached target IDs, such as changeset, feedback, response, or brief IDs
- source label
- operator label
- environment, including local, preview, fixture, or live workspace posture
- browser, version when available, operating system, and device class
- route or target URL label without secrets
- viewport width and height, plus orientation when useful
- date and observation time
- input method, such as mouse, keyboard, touch, or screen reader pairing
- screenshot metadata or local artifact reference when present
- skipped cases
- limitations
- non-claims
- local-only posture
- redaction status
- freshness posture

If a required field is unknown, record `unknown` with a limitation instead of
silently omitting it.

## Live Dashboard Walkthrough Protocol

Before starting, choose the changeset or feedback target that the walkthrough
supports. Record the dashboard route, workspace label, environment, date,
browser, viewport, and data posture.

During the walkthrough, summarize the user-visible path and outcome. Capture
only bounded observations such as "changeset detail rendered feedback rows" or
"manual evidence inbox showed local-only posture." Do not paste raw `.glassbox`
state, private provider output, absolute local paths, cookies, tokens, or
unbounded console logs.

After the walkthrough, list skipped cases, limitations, and non-claims. If the
workspace changed after the walkthrough, mark the evidence stale or needs
inspection before relying on it.

## Browser Check Protocol

A browser check should name the target page or route, browser, OS, viewport,
input method, environment, and observation date. Include whether the operator
checked console errors, network failures, hydration warnings, focus movement,
loading states, or responsive layout behavior.

Browser checks are advisory live evidence. They do not replace retained
Playwright, unit, integration, replay, eval, package, or migration evidence.
When deterministic tests cover the same behavior, cite those tests separately
and keep the browser check as corroborating context.

## Screenshot Evidence Protocol

Screenshot evidence starts as metadata:

- local-only file reference
- capture date
- route or page label
- environment
- viewport
- browser and OS
- redaction status
- screenshot purpose
- attached target IDs
- limitations and non-claims

Raw screenshots should stay under the local evidence directory and should not
enter reviewer-safe exports unless a later export policy reviews secrets,
private user data, absolute paths, and proprietary content. Prefer cropped or
redacted images only when the artifact system can preserve the redaction
decision.

## Keyboard Navigation Protocol

Keyboard notes should record the starting point, expected tab path, observed tab
path, focus-visible behavior, blocked controls, escape routes, modal trapping,
and any skipped regions. They should name whether the operator used only a
keyboard or paired the pass with another tool or reviewer.

Use issue-shaped language for failures, for example "focus left the modal after
the second Tab key press." Avoid saying the app is accessible, compliant, or
certified because a focused keyboard pass is not accessibility certification.

## Responsive Layout Protocol

Responsive observations should name each viewport, route, orientation when
relevant, browser, environment, and date. Record overflow, clipping, text
wrapping, fixed-size controls, tap target concerns, and horizontal scrolling.

Each viewport is separate evidence. A desktop pass does not imply mobile
coverage, and a narrow mobile pass does not imply tablet or wide-desktop
coverage. Skipped breakpoints must be explicit.

## Accessibility Pairing Protocol

Accessibility pairings connect manual observations with another source, such as
a focused axe report, browser accessibility tree inspection, screen reader
spot-check, keyboard pass, contrast check, or second reviewer note.

The pairing should explain what the paired source did and did not cover. It may
say "manual accessibility note paired with retained axe output" only when that
output is actually retained. It must not say "WCAG compliant", "accessibility
certified", or "fully accessible" unless a future release policy defines a
formal conformance process outside this protocol.

## Advisory Versus Blocking Policy

Live review evidence is advisory by default. It can inform review responses,
manual evidence, lifecycle briefs, handoff readiness, accepted-risk notes, and
safe next actions.

Live review evidence may become blocking only when a later task defines all of
the following:

- deterministic fixture-backed check or retained tool output
- stable input data and environment controls
- pass/fail rules
- redaction and export policy
- release-gate membership
- freshness rules

Until then, a failed live walkthrough may block an operator's local handoff
decision, but it is not deterministic release authority. Passing live evidence
must not override failed, missing, or stale deterministic checks.

## Naming And Retention

Use local-only directories under the workspace:

```text
.glassbox/evidence/<changeset-id>/browser/
.glassbox/evidence/<changeset-id>/dashboard/
.glassbox/evidence/<changeset-id>/accessibility/
```

Use stable, readable file names:

```text
YYYYMMDDTHHMMSSZ-browser-check-<route-slug>.json
YYYYMMDDTHHMMSSZ-dashboard-walkthrough-<route-slug>.json
YYYYMMDDTHHMMSSZ-keyboard-note-<route-slug>.json
YYYYMMDDTHHMMSSZ-responsive-<viewport>.json
YYYYMMDDTHHMMSSZ-screenshot-<route-slug>.metadata.json
YYYYMMDDTHHMMSSZ-screenshot-<route-slug>.png
```

JSON metadata is the reviewer-safe starting point. Binary screenshots,
recordings, browser profiles, and raw tool exports are local-only unless a later
artifact or bundle policy explicitly marks them safe to export.

## Reviewer-Safe Language

Prefer:

- "live dashboard evidence attached"
- "operator observed"
- "browser check reported"
- "screenshot metadata is local-only"
- "keyboard note indicates"
- "responsive observation is advisory"
- "accessibility note is paired with retained tool output"
- "evidence is stale; inspect before relying on it"

Avoid:

- "verified" for live-only evidence
- "release gate passed" from a browser walkthrough alone
- "reviewer accepted" or "review approved"
- "WCAG compliant", "accessibility certified", or "fully accessible"
- "safe to publish", "safe to push", or "ready to merge"
- "screenshot is reviewer-safe" before export review

## Non-Claims

Browser, dashboard, and accessibility evidence does not mean:

- deterministic replay, eval, package, migration, unit, or integration checks
  passed
- Glassbox ran a retained command
- the evidence is deterministic release authority
- the application is WCAG compliant
- the application has accessibility certification
- a reviewer accepted the response
- a pull request is approved
- files were staged, committed, pushed, published, merged, or deployed
