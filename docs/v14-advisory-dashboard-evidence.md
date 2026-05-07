# V14 Advisory Dashboard Evidence Summary

This summary completes `GBX-1451` from [tasks-v14.md](./tasks-v14.md). It
records one fresh advisory browser walkthrough for the matured v14 review-loop
dashboard surfaces using the protocol in
[v14-advisory-review-evidence.md](./v14-advisory-review-evidence.md).

- Date: May 6, 2026 America/Los_Angeles
  (`2026-05-07T06:04:34.704Z`)
- Operator: Codex
- Evidence directory:
  `.glassbox/releases/v14-advisory-review-evidence/browser/`
- Dashboard scenario status: observed
- Accessibility scenario status: not covered by this pass; see `GBX-1452`
- Deterministic checks cited separately:
  `pnpm --dir frontend build`,
  `pnpm --dir frontend test -- changeset-console.test.tsx`, and
  `pnpm --dir frontend exec playwright test e2e/v14-advisory-browser-evidence.tmp.spec.ts --config playwright.v14-evidence.tmp.config.ts --project=chromium`
  with a disposable local evidence runner removed after the retained evidence
  was written.

## Observed Coverage

| Scenario | Status | Evidence | Limitations |
| --- | --- | --- | --- |
| Dashboard changeset detail | observed | `/app/changesets/changeset-1` rendered the changeset header, review readiness, changed files, verification, manual evidence inbox, review feedback, and final handoff sections. | Fixture-backed API route, not a live production backend. |
| Feedback status | observed | Review Feedback showed open/requested/responded counts, response-linked fixup inventory posture, inspect-first command copy, and a fixup inventory action. | Existing fixture had a responded item with fixup inventory; missing and failed action states were covered by focused component tests, not this live browser pass. |
| Skipped evidence display | observed | Manual Evidence Inbox kept skipped browser/dashboard guidance visibly non-passing through the safe-command and non-claim copy. | No new skipped evidence record was attached during this browser-only pass. |
| Fixup inventory action state | observed | The feedback row exposed the response-linked fixup inventory action for `feedback-1`; the visible label was `Refresh fixup` because the fixture already had one inventory. | Pending, succeeded, and failed action transitions were not clicked in this advisory walkthrough. |
| Handoff readiness | observed | Final Handoff remained visible alongside blockers, safe next actions, and non-publication copy. | This was visual/browser evidence only, not release authority. |

## Browser Evidence

- Route: `/app/changesets/changeset-1`
- Environment: local static server for the production frontend build with the
  fixture-backed Glassbox API
- Browser: Chromium through Playwright
- Operating system and device class: macOS desktop
- Viewport: 1440x900 landscape
- Input method: Playwright pointer and keyboard automation
- Console status: checked, no browser console errors or page errors observed
- Screenshot retained locally:
  `.glassbox/releases/v14-advisory-review-evidence/browser/screenshots/changeset-1-1440x900.png`
- Raw summary retained locally:
  `.glassbox/releases/v14-advisory-review-evidence/browser/summary.json`

## Skipped Coverage

| Scenario | Capture state | Reason | Claims not made |
| --- | --- | --- | --- |
| Mobile dashboard viewport | not_run | `GBX-1451` required one fresh walkthrough; this pass used a desktop operator viewport. | No claim that mobile wrapping was freshly inspected in this pass. |
| Accessibility pairing | not_run | Accessibility evidence is split into `GBX-1452`. | No screen-reader, contrast, WCAG, or accessibility certification claim. |
| Live backend dogfooding changeset attachment | not_applicable | The walkthrough intentionally used the existing fixture-backed changeset route because the v14 dogfooding changeset is scheduled for `GBX-1470`. | No claim that browser evidence was attached to a live v14 dogfooding changeset. |

## Findings

| Area | Finding | Disposition |
| --- | --- | --- |
| Dashboard walkthrough | The matured changeset detail, feedback status, skipped-evidence copy, fixup action affordance, and handoff posture rendered successfully at 1440x900. | Advisory pass retained. |
| Dev-server startup | The first Playwright attempt against `next dev` timed out after Next watchpack emitted repeated `EMFILE` watcher warnings. | Reran against the production static export served locally; the successful retained pass did not depend on the dev watcher. |

## Non-Claims

- advisory evidence is not deterministic release authority
- advisory evidence is not retained command evidence unless a retained tool
  output explicitly says so
- skipped browser, dashboard, or accessibility evidence is not a pass
- response-linked fixup inventory is not reviewer approval
- handoff readiness is local posture, not publication readiness
- accessibility notes are not certification or WCAG conformance
- Glassbox did not stage, commit, push, open a PR, merge, deploy, or publish
