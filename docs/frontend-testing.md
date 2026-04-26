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

## Validation Gates

Frontend files trigger scoped pre-commit hooks for Prettier, ESLint, TypeScript, Vitest, static export build validation, and Playwright. These hooks run through `pnpm --dir frontend ...` and do not run for Python-only commits unless the hook is invoked over all files.

Run frontend-only validation while working on the SPA:

```sh
pnpm --dir frontend format:check
pnpm --dir frontend lint
pnpm --dir frontend typecheck
pnpm --dir frontend test
pnpm --dir frontend exec next build
pnpm --dir frontend test:e2e
```

Run full-repo validation before cross-boundary changes land:

```sh
uv run pre-commit run --all-files
```

Full-repo validation keeps deterministic replay/eval gates separate from frontend checks while still running both families in the normal push workflow. GitHub Actions installs pnpm dependencies and Playwright Chromium before running pre-commit, then uploads `frontend/test-results/` on browser-test failures.

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

## v4 Visual Review Archive

Generate the deterministic v4 screenshot archive with:

```sh
pnpm --dir frontend screenshots:v4-audit
```

The archive writes to `frontend/test-results/v4-audit-screenshots/` and is intentionally ignored by git. Keep the current run locally while reviewing a UX change, and rely on regenerated screenshots rather than committed binary baselines. Each capture records route, scenario, operator state, git revision, viewport, and file path in `manifest.json` plus a readable `index.md`.

Review representative desktop, narrow desktop, tablet, and mobile captures for the scenario viewports declared in the shared v4 fixtures. The archive test should fail on dev-overlay contamination, blank primary regions, selected-session blank states, or horizontal overflow. Add new fixture scenarios when a user-visible operator state is not represented by the current matrix.

The full v4 UX release command and manual approval checklist live in
[v4-ux-release-gate.md](./v4-ux-release-gate.md).
