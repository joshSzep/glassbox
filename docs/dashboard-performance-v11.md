# v11 Dashboard Performance Measurement

For the docs hub and operator guides, start at [README.md](./README.md). This
note records the `GBX-1133` large-session dashboard measurement pass for the
v11 confidence-and-adoption track.

## Scope

The pass checked whether the cockpit remains usable when local sessions contain
larger transcript pages, event logs, turn metrics, tool attempts, recovery
cues, compaction freshness, provider warnings, and live stream updates.

This is not a synthetic browser benchmark suite. It is a retained confidence
pass over the current deterministic fixtures and browser routes. Deterministic
component, store, and routed Playwright checks remain the evidence source; live
browser timing can vary by local machine and is advisory.

## Measurement Summary

Focused frontend command:

```bash
pnpm --dir frontend exec vitest run \
  tests/dashboard-stores.test.ts \
  tests/session-inspector.test.ts \
  tests/session-state.test.ts \
  tests/workspace-overview.test.ts \
  --reporter=default
```

Result:

```text
Test Files  4 passed (4)
Tests       54 passed (54)
Duration    1.27s
```

Focused browser command:

```bash
pnpm --dir frontend exec playwright test e2e/v11-live-cockpit-evidence.spec.ts \
  -g "long-session|stream degradation" \
  --reporter=list
```

Result:

```text
2 passed (7.4s)
```

The first browser runs in this phase required permission to launch Chromium in
the macOS local environment. After that, the routed dashboard checks completed
without a blocking UI performance issue.

## Coverage Map

| Area | Evidence | Result |
| --- | --- | --- |
| Aggregate load | `tests/workspace-overview.test.ts` renders dense attention rows, queue counts, recovery cues, provider evidence, and status rail states. | Passed; workspace overview suite completed inside the focused Vitest run. |
| Selected-session load | `tests/dashboard-stores.test.ts` loads selected-session snapshots and detail pages through the real store path. | Passed; selected-session hydration remains bounded to loaded page windows. |
| SSE reducer cost | `tests/session-state.test.ts` and `tests/dashboard-stores.test.ts` apply live SSE envelopes, repeated observers, and noisy large-transcript fixture events. | Passed; repeated retained/live event rows remain renderable after the `GBX-1131` keying fix. |
| Long timeline rendering | `tests/session-inspector.test.ts` bounds large long-run timeline windows to a visible window and keeps tab content scoped. | Passed; large timeline render remains capped instead of dumping every event into the panel. |
| Detail-page pagination | `tests/dashboard-stores.test.ts` verifies transcript, event-log, and turn-metric pages load at `80` item windows and append on demand. | Passed; initial load and load-more paths stay paginated. |
| Browser long-session route | `frontend/e2e/v11-live-cockpit-evidence.spec.ts` exercises long-session recovery cues and degraded stream/reconnect routes in Chromium. | Passed; retained evidence remains under `.glassbox/releases/gbx-1131-live-cockpit/`. |

## Findings

- No blocking large-session dashboard performance issue was found in the
  focused v11 pass.
- No new backend API shape or pagination change was needed.
- No projection was made authoritative to improve dashboard speed.
- The only issue surfaced during Phase 113 browser evidence was duplicate
  React keys for repeated retained/live event rows. `GBX-1131` fixed the
  evidence-pane keys by including the render-window index.
- Existing detail loading still uses bounded `80` item page windows for
  transcript, event log, and turn metrics.

## Non-Claims And Follow-Ups

- This pass does not prove every real-world session size, browser, zoom level,
  or machine profile.
- It does not replace backend large-session scale gates or release replay/eval
  authority.
- If future dashboard work adds unbounded panels, broad global derivations, or
  new live stream reducers, add a focused measurement before expanding release
  claims.

## Related Documents

- [live-cockpit-evidence-v11.md](./live-cockpit-evidence-v11.md): v11 browser
  evidence protocol and retained `GBX-1131` evidence
- [frontend-testing.md](./frontend-testing.md): frontend unit, store,
  component, and Playwright validation guidance
- [long-run-cockpit-contract.md](./long-run-cockpit-contract.md): long-running
  cockpit priority and data-source contract
