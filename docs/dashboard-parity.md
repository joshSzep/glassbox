# Dashboard Parity Gate

GBX-470 defines the evidence required before the v3 SPA can replace the legacy dashboard route. Parity is behavioral: an operator must not lose a supported workflow, even when the SPA presents the workflow differently.

## Automated Coverage Map

| Requirement | Evidence |
| --- | --- |
| Session index and aggregate console | `frontend/tests/workspace-overview.test.ts`, `frontend/tests/dashboard-stores.test.ts`, `frontend/e2e/operator-workflows.spec.ts` |
| Queue browsing and priority states | `frontend/tests/workspace-overview.test.ts`, `frontend/tests/app-route.test.ts`, `frontend/e2e/operator-workflows.spec.ts` |
| Selected-session inspector | `frontend/tests/session-inspector.test.ts`, `frontend/tests/operator-actions.component.test.tsx` |
| Direct session deep links and route recovery | `frontend/tests/app-route.test.ts`, `frontend/e2e/operator-workflows.spec.ts`, `tests/integration/test_web_spa_static.py` |
| Live SSE and historical states | `frontend/tests/sse-client.test.ts`, `frontend/tests/session-state.test.ts`, `frontend/e2e/operator-workflows.spec.ts` |
| Prompt submission | `frontend/tests/api-client.test.ts`, `frontend/tests/dashboard-stores.test.ts`, `frontend/tests/operator-actions.component.test.tsx`, `frontend/e2e/operator-workflows.spec.ts` |
| Pending `ask_user` answers | `frontend/tests/api-client.test.ts`, `frontend/tests/dashboard-stores.test.ts`, `frontend/tests/operator-actions.component.test.tsx`, `frontend/e2e/operator-workflows.spec.ts` |
| Approval resolution | `frontend/tests/api-client.test.ts`, `frontend/tests/dashboard-stores.test.ts`, `frontend/tests/operator-actions.component.test.tsx`, `frontend/e2e/operator-workflows.spec.ts`, `tests/integration/test_web_approval_resolution.py` |
| Fork creation | `frontend/tests/api-client.test.ts`, `frontend/tests/dashboard-stores.test.ts`, `frontend/tests/operator-actions.component.test.tsx`, `frontend/e2e/operator-workflows.spec.ts` |
| Lineage and compare | `frontend/tests/session-inspector.test.ts`, `frontend/tests/dashboard-stores.test.ts`, `frontend/tests/app-route.test.ts` |
| Runtime context and verification cues | `frontend/tests/session-inspector.test.ts`, `frontend/tests/verification-cues.test.ts`, `frontend/tests/session-state.test.ts` |
| Metrics, active tools, live output, and event log | `frontend/tests/session-inspector.test.ts`, `frontend/tests/session-state.test.ts` |
| Projection health and degraded states | `frontend/tests/workspace-overview.test.ts`, `frontend/tests/session-inspector.test.ts`, `frontend/tests/session-state.test.ts` |
| Transport and error handling | `frontend/tests/api-client.test.ts`, `frontend/tests/sse-client.test.ts`, `frontend/tests/dashboard-stores.test.ts`, `tests/integration/test_web_session_snapshot.py`, `tests/integration/test_web_session_aggregate.py` |
| Static export serving | `tests/integration/test_web_spa_static.py`, `pnpm --dir frontend exec next build` |

## Manual Validation Checklist

Before flipping the default dashboard route, validate these representative paths against a locally built SPA export:

- Start `glassbox session chat --cwd .`, open the printed dashboard URL, and confirm the live session appears without manually copying the session id.
- Run `glassbox dashboard serve --cwd . --host 127.0.0.1 --port 8765`, open `/`, browse active, questions, approvals, failures, degraded, and historical queues, and open at least one selected session.
- Use a daemon-backed workspace: start the daemon, run `glassbox daemon status --cwd .`, open the reported dashboard URL, and confirm runtime health, queue counts, and selected-session snapshots load.
- Exercise one pending question, one approval, one prompt submission, and one fork using deterministic local sessions or test fixtures.
- Open a parent or child session from the lineage pane, compare it against the selected session, then clear compare state.
- Refresh `/`, `/app`, `/app/sessions/SESSION_ID`, and `/?session=SESSION_ID` to confirm browser routes recover without a blank page.
- Temporarily move the built SPA asset directory aside and confirm the server returns the documented missing-build guidance instead of an empty shell.

## Accepted Migration Notes

- Browser tests currently use deterministic route fixtures rather than a launched FastAPI fixture server; FastAPI static-serving behavior is covered separately by Python integration tests.
- The GBX-472 migration window has closed: the no-framework dashboard assets, `/legacy` route, and Node-based legacy tests have been removed.

## Gate Decision

The SPA may replace the legacy root route when all automated checks above pass, the manual checklist has no blocking failures, and any remaining migration notes are explicitly accepted as non-blocking.
