# v7 Dashboard Accessibility Pairing Review

This review records the `GBX-780` dashboard accessibility evidence for the v7 release-candidate track. It builds on [dashboard-accessibility-review-v6.md](./dashboard-accessibility-review-v6.md), the dashboard evidence contract in [dashboard-evidence-v7.md](./dashboard-evidence-v7.md), and the v7 manual evidence shape in [manual-qa-evidence-v7.md](./manual-qa-evidence-v7.md).

## Named Pairings

| Pairing                                                                        | Status                                                           | Evidence                                                                                                                                    |
| ------------------------------------------------------------------------------ | ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| Chromium through Playwright on macOS, keyboard-only, desktop `1440x900` family | Reviewed through dashboard e2e workflows and component semantics | `frontend/e2e/operator-workflows.spec.ts`, `frontend/tests/session-inspector.test.ts`, `frontend/tests/operator-actions.component.test.tsx` |
| Chromium through Playwright on macOS, keyboard-only, mobile `390x844` family   | Reviewed through mobile drill-in and narrow viewport workflows   | `operator console remains reachable in a narrow viewport`, `mobile operator can drill into a session, act, and return to queues`            |
| Chromium through Playwright on macOS, artifact/evidence tab semantics          | Reviewed through component and e2e evidence-cue tests            | `frontend/tests/verification-cues.test.ts`, `operator can inspect artifact-backed verification cues`                                        |
| macOS VoiceOver with Chromium dashboard                                        | Not executed in this environment                                 | Non-claim; requires manual reviewer evidence before any screen-reader support claim                                                         |

## Review Scope

Reviewed dashboard areas for v7 evidence claims:

- queue navigation and selected-session drill-in
- selected-session tabs and direct links
- transcript, timeline, actions, lineage, compare, runtime, evidence, metrics, and events tabs
- prompt submit, answer submit, approval approve/deny, cancellation, fork, compare, and mobile return
- policy source, eval relevance, replay drift, provider canary, and release freshness evidence cues
- degraded projection and live stream state labels
- narrow viewport and mobile drill-in behavior

## Validation Commands

Use this focused dashboard suite for the v7 pairing review:

```bash
pnpm --dir frontend exec vitest run \
  tests/session-inspector.test.ts \
  tests/operator-actions.component.test.tsx \
  tests/verification-cues.test.ts \
  tests/workspace-overview.test.ts

pnpm --dir frontend exec playwright test e2e/operator-workflows.spec.ts
```

For the `GBX-780` task commit, focused evidence and workflow checks were rerun with:

```bash
pnpm --dir frontend exec vitest run tests/verification-cues.test.ts tests/session-inspector.test.ts
pnpm --dir frontend exec playwright test e2e/operator-workflows.spec.ts -g "operator can inspect artifact-backed verification cues"
```

## Supported Claims

- The reviewed Chromium/Playwright dashboard workflows are keyboard-operable for the primary operator paths covered by tests.
- The Evidence tab exposes named semantic groups for verification summary, Evidence interpretation, artifact paths, working-set provenance, and event/projection evidence.
- Dashboard status and evidence cues use text labels, not color alone, in the reviewed workflows.
- The mobile drill-in workflow remains reachable without horizontal navigation in the reviewed viewport family.

## Non-Claims

- This is not formal WCAG, VPAT, or screen-reader certification.
- This does not prove VoiceOver, NVDA, Narrator, or Orca behavior with the dashboard.
- This does not prove every browser and browser zoom setting behaves identically.
- Screenshot archives remain review evidence, not a pixel-perfect accessibility baseline.

## Blocking Issues And Follow-Ups

No blocking dashboard accessibility issue is recorded for this `GBX-780` pass. The pass added an accessible label to the Evidence interpretation region so screen-reader and keyboard reviewers have a stable named landmark for the new v7 evidence cue family. Before making stronger public claims, run and retain a real browser/screen-reader pairing review under the v7 release evidence directory.
