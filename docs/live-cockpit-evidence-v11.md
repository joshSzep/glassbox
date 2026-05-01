# v11 Live Cockpit Evidence Protocol

For the docs hub and operator guides, start at [README.md](./README.md). This
protocol defines the `GBX-1130` evidence workflow for turning v10 deterministic
long-run cockpit coverage into repeatable live dashboard evidence during v11.

## Purpose

The v11 live cockpit pass answers one narrow release-confidence question:

- does the packaged dashboard stay useful while a local operator inspects live
  and historical long-running work in a real browser?

This protocol does not make the browser a release authority. Deterministic
replay, eval, unit, integration, component, package, and release-gate checks
remain the blocking evidence for cockpit behavior. Live browser evidence is
retained advisory confidence that can expose environmental, routing, streaming,
layout, focus, reconnect, and state-staleness issues before a release
candidate.

## Evidence Directory Convention

Keep v11 live cockpit evidence under the local release directory for the
candidate being reviewed:

```text
.glassbox/releases/YYYYMMDDTHHMMSSZ-v11-live-cockpit/
  manifest.json
  live-cockpit-summary.md
  automated/
    playwright/
    logs/
  manual/
    screenshots/
    notes.md
  blockers/
    environment.md
```

The `.glassbox/` directory is workspace-local state and is ignored by git. Do
not commit browser screenshots, local server logs, terminal recordings, private
session transcripts, provider transcripts, or credential-bearing output by
default. Commit concise docs summaries when they change release claims, and
retain larger artifacts under the local evidence directory.

Every evidence directory should include:

- candidate commit or package identifier
- reviewer and date
- dashboard URL shape, browser, OS, viewport set, and whether the dashboard was
  served by the co-hosted FastAPI static export or frontend development server
- scenario statuses: passed, failed, partial, blocked, or not run
- artifact references for screenshots, structured browser logs, Playwright
  reports, and manual notes
- non-claims and environmental blockers

## Scenario Matrix

| Scenario | Required Observation | Minimum Evidence | Failure Policy |
| --- | --- | --- | --- |
| Active turn | A live or resumable session shows status, current turn, heartbeat or stream posture, and the safest next action before diagnostics. | Playwright route or manual browser note plus screenshot or structured log. | Blocking only if the deterministic cockpit contract also fails or the release guide promotes the exact browser workflow. |
| Pending approval | Pending approval outranks passive diagnostics and exposes approve/deny context without mutating until confirmed. | Component or Playwright role assertion plus retained screenshot when run live. | Fix before release if controls overlap, lose labels, or hide risk context. |
| Pending question | Pending `ask_user` state outranks lower-priority cues and keeps answer controls reachable. | Playwright route or manual screenshot with keyboard reachability note. | Fix before release if the operator cannot answer from the dashboard. |
| Stale tool attempt | Stale or retryable attempts show inspect/output guidance before retry or abandon controls. | Browser note linking the displayed cue to `glassbox session tool-attempt inspect`. | Fix if recovery guidance starts with mutation or hides retained output. |
| Stale verification | Verification failure, drift, or missing last-known-good evidence appears as verification posture, not runtime failure. | Structured log or screenshot of the evidence or verification surface. | Fix if stale verification is visually indistinguishable from healthy evidence. |
| Compaction freshness | Missing, stale, invalidated, or fresh compaction state is visible with source range or artifact context when available. | Screenshot or structured state capture for the selected session. | Fix if compaction state implies cleanup or hides the safe inspection command. |
| Provider warning | Provider degradation, stale canary evidence, or model fallback recommendation stays advisory and below live blockers. | Screenshot or notes showing priority order and advisory copy. | Fix if provider warning outranks approval, question, failed work, or projection degradation. |
| Daemon interruption | Stale daemon, owner conflict, or unavailable live stream is labeled as runtime or stream posture with safe inspection guidance. | Browser log or manual note after interruption or mocked route. | Fix if the dashboard presents stale summaries as live authority. |
| Stream reconnect | SSE reconnect, history truncation, or stream degradation is visible without losing selected-session context. | Playwright reconnect scenario or manual browser log. | Fix if reconnect drops operator context or duplicates action controls. |
| Historical snapshot | Historical or imported sessions remain inspectable and do not look like broken live sessions. | Screenshot or component evidence for historical state copy. | Fix if historical no-action states are presented as active recovery gaps. |

## Automated Evidence

Automated evidence can come from focused Playwright scenarios, component tests,
or structured browser logs. Use fixture-backed route mocks when the goal is
layout, priority, or reconnect confidence. Use a live local server when the
goal is packaged static asset, API routing, SSE, or selected-session behavior.

Recommended commands for later v11 tasks:

```bash
pnpm --dir frontend test
pnpm --dir frontend exec playwright test e2e/operator-workflows.spec.ts
pnpm --dir frontend build
uv run pytest tests/integration/test_web_chat_dashboard_live.py
```

When a scenario is automated, retain:

- command, exit code, browser, viewport, and route or URL
- Playwright report path or structured log path
- screenshot path when the assertion is visual, responsive, or priority-order
  related
- a short summary in `live-cockpit-summary.md`

## Manual Evidence

Manual evidence covers real local browser operation that deterministic tests
cannot fully model, such as operator pacing, OS/browser focus behavior, local
server startup, and live reconnect observation.

Manual runs should record:

- browser and version
- OS and viewport or window size
- server command and dashboard URL shape
- scenario statuses from the matrix
- keyboard path for opening the relevant queue, selected session, tab, or
  action control
- screenshots or notes for any failure, partial result, or environmental
  blocker

Manual notes should summarize state. They should not store private prompts,
full transcripts, credentials, provider responses, or large event logs unless a
specific release decision requires a redacted excerpt.

## Non-Claims

A passing v11 live cockpit run supports only the named scenarios, browser,
viewport, server mode, and commit or package under review.

It does not claim:

- formal accessibility certification
- cross-browser support beyond the browsers actually named
- provider reliability or provider release authority
- hosted dashboard operation
- automatic recovery, retry, merge, or mutation behavior
- indefinite unattended operation
- pixel-perfect visual regression coverage

If browser infrastructure is unavailable, record the blocker in
`blockers/environment.md`, mark affected scenarios as blocked, keep release
claims bounded, and rely on deterministic cockpit evidence for blocking
authority.

## Release Summary Template

Use this shape for `live-cockpit-summary.md`:

```markdown
# v11 Live Cockpit Evidence

- Candidate: <commit-or-package>
- Reviewer: <name-or-initials>
- Date: <YYYY-MM-DD>
- Browser and OS: <browser/version>, <OS/version>
- Server mode: co-hosted static export | frontend dev server | mocked routes
- Status: passed | failed | partial | blocked

## Scenario Results

| Scenario | Status | Evidence | Notes |
| --- | --- | --- | --- |
| Active turn | not run | | |
| Pending approval | not run | | |
| Pending question | not run | | |
| Stale tool attempt | not run | | |
| Stale verification | not run | | |
| Compaction freshness | not run | | |
| Provider warning | not run | | |
| Daemon interruption | not run | | |
| Stream reconnect | not run | | |
| Historical snapshot | not run | | |

## Blocking Findings

- None, or list issues with links.

## Non-Claims And Blockers

- List skipped browser, screen-reader, provider, and hosted-service claims.
```

## GBX-1131 Evidence Summary

The first v11 automated live cockpit evidence pass is retained locally under:

```text
.glassbox/releases/gbx-1131-live-cockpit/
```

Focused command:

```bash
GBX_V11_LIVE_COCKPIT_EVIDENCE_DIR=.glassbox/releases/gbx-1131-live-cockpit \
  pnpm --dir frontend exec playwright test e2e/v11-live-cockpit-evidence.spec.ts --reporter=list
```

Result: passed on Chromium through Playwright. The first sandboxed attempt was
blocked by macOS browser-launch permissions, then the same command passed when
Chromium was allowed to launch.

Retained automated scenarios:

| Scenario | Status | Retained Evidence |
| --- | --- | --- |
| Long-session inspection | Passed | `automated/playwright/long-session-inspection/summary.json` and `screenshot.png` |
| Stale verification evidence | Passed | `automated/playwright/stale-verification-evidence/summary.json` and `screenshot.png` |
| Stream degradation and reconnect | Passed | `automated/playwright/stream-degradation-reconnect/summary.json` and `screenshot.png` |
| Queue navigation and historical snapshot | Passed | `automated/playwright/queue-navigation-historical-snapshot/summary.json` and `screenshot.png` |

This pass supports the named Chromium, routed-dashboard, desktop, and mobile
fixture-backed claims only. It does not claim screen-reader coverage,
cross-browser coverage, live provider reliability, hosted operation, or broad
performance coverage. During the run, a duplicate React key warning appeared
when live SSE events repeated fixture event-log rows; `GBX-1131` fixed the
event-evidence keying so repeated live and retained events remain renderable.

## Related Documents

- [v11-confidence-adoption-contract.md](./v11-confidence-adoption-contract.md):
  v11 scope, evidence split, and pass/fail policy
- [v11-residual-risk-audit.md](./v11-residual-risk-audit.md): inherited live
  cockpit evidence gap and disposition
- [long-run-cockpit-contract.md](./long-run-cockpit-contract.md): v10 terminal
  and dashboard cockpit priority contract
- [dashboard-cockpit-contract.md](./dashboard-cockpit-contract.md): dashboard
  information architecture and accessibility expectations
- [frontend-screenshot-archive.md](./frontend-screenshot-archive.md): existing
  screenshot archive workflow for fixture-backed frontend review
