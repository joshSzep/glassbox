# Frontend Testing

The v3 SPA uses Vitest for unit, transport, store, and React component tests. Keep frontend tests in `frontend/tests/` and run them with:

```sh
pnpm --dir frontend test
```

Use `pnpm --dir frontend lint` and `pnpm --dir frontend typecheck` with the test command before committing frontend changes.

## Test Layers

- Reducer tests should exercise pure state transitions in `frontend/state/` without rendering React.
- Transport tests should inject fake `fetch` or `EventSource` implementations and assert URLs, request bodies, response normalization, and reconnection behavior.
- Store tests should use typed API and stream fakes, preserving the separation between canonical server snapshots and local drafts.
- Component tests should render React with Testing Library from `frontend/tests/test-utils.tsx` and assert user-visible behavior by role, label, or text.

## Fixtures

Shared fixtures live in `frontend/tests/fixtures/session-state.ts`. Prefer those builders over hand-written objects so generated OpenAPI type changes surface in one place. Keep fixture payloads realistic but small: snapshots, aggregate session rows, SSE envelopes, runtime context, projection health, and action-ready sessions should include only the fields that a test needs.

When a test needs backend failures, construct `GlassboxApiError` or HTTP-shaped responses in that test instead of weakening generated API types. This keeps frontend behavior close to the FastAPI contract while still making tests deterministic.
