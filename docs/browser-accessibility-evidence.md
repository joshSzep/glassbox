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
- capture state: `observed`, `not_run`, or `not_applicable`
- environment, including local, preview, fixture, live workspace posture, or
  `unknown` for skipped evidence
- browser, version when available, operating system, and device class; skipped
  evidence may record `unknown`
- route or target URL label without secrets; skipped evidence may record
  `unknown` when no route was opened
- viewport width and height, plus orientation when useful; skipped evidence may
  record `unknown` instead of inventing dimensions
- date and observation time
- input method, such as mouse, keyboard, touch, or screen reader pairing
- screenshot metadata or local artifact reference when present
- skipped cases
- limitations
- non-claims
- local-only posture
- redaction status
- freshness posture

If a field is unknown, record `unknown` with a limitation instead of silently
omitting it. For `observed` browser or dashboard evidence, route, environment,
and viewport are still required because a live browser claim must name what was
actually opened. For skipped browser or dashboard evidence, route, environment,
browser, viewport, console, and input-method details may be unknown. For
`observed` accessibility evidence, environment and observed issue are required;
for skipped accessibility evidence, environment, tool, route, reviewer, and
assistive-technology details may be unknown.

## Skipped Advisory Evidence

Skipped advisory evidence is honest local evidence that a live pass was not
run, was unknown, or was not applicable. It is not failed evidence, passed
evidence, deterministic verification, accessibility certification, or release
authority.

Use skipped-case language when a browser, dashboard, viewport, console,
keyboard, responsive, contrast, or screen-reader check was intentionally not
covered. The record should name what was skipped, why it was skipped, which
claims remain unmade, and which safe inspection command or protocol can collect
fresh evidence later.

The v14 skipped-evidence model supports `not_run` and `not_applicable` capture
states without fake viewport dimensions, fake browser details, fake console
checks, fake observed issues, or fake assistive-technology passes. A skipped
record must include a skip reason or skipped cases. It must not include
`observed_at`, screenshot metadata, a positive console-checked claim, an
accessibility observed issue, paired tool output, or follow-up text that reads
as though a live pass occurred. CLI and API clients record skipped posture with
`capture_state` / `--capture-state` values of `not_run` or `not_applicable` and
must include `skip_reason` / `--skip-reason` or skipped cases. Keep skipped
evidence explicit and do not call it verified, accessible, or passed. Do not
invent a live browser pass to satisfy a skipped evidence record.

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

Record a dashboard walkthrough with:

```bash
glassbox changeset evidence dashboard CHANGESET_ID \
  --summary "dashboard showed feedback and manual evidence" \
  --source-label dashboard-local \
  --route /console/changesets \
  --environment local-dev \
  --browser chromium \
  --viewport 1440x900 \
  --skipped-case "mobile viewport" \
  --freshness needs_inspection \
  --cwd .
```

Record an intentionally skipped dashboard walkthrough without placeholder
viewport or environment values with:

```bash
glassbox changeset evidence dashboard CHANGESET_ID \
  --summary "dashboard walkthrough intentionally skipped" \
  --source-label dashboard-local \
  --capture-state not_run \
  --skip-reason "local dashboard server was not started" \
  --skipped-case "unknown viewport" \
  --freshness needs_inspection \
  --cwd .
```

## Browser Check Protocol

A browser check should name the target page or route, browser, OS, viewport,
input method, environment, and observation date. Include whether the operator
checked console errors, network failures, hydration warnings, focus movement,
loading states, or responsive layout behavior.

Browser checks are advisory live evidence. They do not replace retained
Playwright, unit, integration, replay, eval, package, or migration evidence.
When deterministic tests cover the same behavior, cite those tests separately
and keep the browser check as corroborating context.

Record a browser check with:

```bash
glassbox changeset evidence browser CHANGESET_ID \
  --summary "browser rendered the feedback list" \
  --source-label local-browser \
  --route /console/changesets \
  --environment local-dev \
  --browser chromium \
  --viewport 1440x900 \
  --cwd .
```

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

Attach screenshot metadata to a browser or dashboard observation with
`--screenshot-file`, `--screenshot-width`, `--screenshot-height`, and optional
`--screenshot-size-bytes`. The command writes metadata-only local references
into a manual evidence artifact and leaves binary review safety advisory.

API clients can attach the same evidence through:

```http
POST /changesets/{changeset_id}/browser-evidence
```

The response is a manual evidence action response, so dashboard and API readers
see the same evidence ID, artifact ID, target links, limitations, non-claims,
and safe next actions as other manual evidence.

Skipped browser or dashboard API evidence uses the same endpoint with
`capture_state` set to `not_run` or `not_applicable`, omits fabricated
`viewport_width`, `viewport_height`, `environment`, and `route_label` values,
and supplies `skip_reason` or `skipped_cases`. Contradictory live-pass claims
such as `console_checked: true` on skipped evidence are rejected.

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

Record an accessibility observation with:

```bash
glassbox changeset evidence accessibility CHANGESET_ID \
  --kind focus_order_issue \
  --summary "focus leaves the feedback dialog" \
  --source-label keyboard-review \
  --environment local-dev \
  --tool "manual keyboard" \
  --route /console/changesets \
  --observed-issue "Tab moved focus behind the dialog" \
  --severity high \
  --disposition paired_with_feedback \
  --feedback FEEDBACK_ID \
  --freshness needs_inspection \
  --cwd .
```

Record intentionally skipped accessibility evidence without fake assistive
technology observations with:

```bash
glassbox changeset evidence accessibility CHANGESET_ID \
  --kind screen_reader_note \
  --summary "screen reader pass not applicable to this backend-only change" \
  --source-label accessibility-review \
  --capture-state not_applicable \
  --skip-reason "no user-facing route changed" \
  --skipped-case "screen reader pass" \
  --cwd .
```

API clients can attach the same evidence through:

```http
POST /changesets/{changeset_id}/accessibility-evidence
```

Use `--kind` values for `keyboard_pass`, `screen_reader_note`,
`focus_order_issue`, `wrapping_issue`, `contrast_observation`, and
`responsive_review`. Observed evidence requires the observed issue,
environment, tool, severity, disposition, and follow-up posture to stay visible
instead of flattening accessibility review into a generic note.

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
