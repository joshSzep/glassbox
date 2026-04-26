# Frontend Testing

The v3 SPA uses Vitest for unit, transport, store, and React component tests. Keep frontend tests in `frontend/tests/` and run them with:

```sh
pnpm --dir frontend test
```

Use `pnpm --dir frontend lint` and `pnpm --dir frontend typecheck` with the test command before committing frontend changes.

Critical browser workflows run through Playwright:

```sh
pnpm --dir frontend test:e2e
```

Playwright launches the Next dev server with the `/app` base path and uses deterministic route fixtures instead of live provider calls. Failure screenshots, videos, and traces are retained under `frontend/test-results/`; passing runs do not create retained artifacts.

## Test Layers

- Reducer tests should exercise pure state transitions in `frontend/state/` without rendering React.
- Transport tests should inject fake `fetch` or `EventSource` implementations and assert URLs, request bodies, response normalization, and reconnection behavior.
- Store tests should use typed API and stream fakes, preserving the separation between canonical server snapshots and local drafts.
- Component tests should render React with Testing Library from `frontend/tests/test-utils.tsx` and assert user-visible behavior by role, label, or text.

## Fixtures

Shared fixtures live in `frontend/tests/fixtures/session-state.ts`. Prefer those builders over hand-written objects so generated OpenAPI type changes surface in one place. Keep fixture payloads realistic but small: snapshots, aggregate session rows, SSE envelopes, runtime context, projection health, and action-ready sessions should include only the fields that a test needs.

When a test needs backend failures, construct `GlassboxApiError` or HTTP-shaped responses in that test instead of weakening generated API types. This keeps frontend behavior close to the FastAPI contract while still making tests deterministic.

## Browser Workflow Tests

Put real-page coverage in `frontend/e2e/`. Prefer route-level FastAPI fixtures for browser tests until a seeded FastAPI test server is needed for broader integration. The first browser suite should stay focused on operator-critical flows: loading `/app`, changing queues, opening a selected session, receiving SSE updates, sending prompts, answering questions, resolving approvals, and creating forks.
