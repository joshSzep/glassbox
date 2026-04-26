# Frontend Development Workflow

Glassbox's v3 dashboard lives in `frontend/` during development and is exported
as static files for production. FastAPI owns the API, SSE stream, runtime state,
and production serving path in both modes.

## Local Hot-Reload Development

Run FastAPI and Next.js in separate terminals.

Terminal 1 starts the dashboard server and API owner:

```bash
uv run glassbox dashboard serve --cwd . --host 127.0.0.1 --port 8765
```

Terminal 2 starts the Next.js dev server:

```bash
pnpm --dir frontend install --frozen-lockfile
GLASSBOX_FASTAPI_ORIGIN=http://127.0.0.1:8765 pnpm --dir frontend dev
```

Then open:

```text
http://127.0.0.1:3000/app
```

`GLASSBOX_FASTAPI_ORIGIN` is read only by the Next.js dev server. It defaults to
`http://127.0.0.1:8765` and may be changed when `glassbox dashboard serve` runs
on another local port.

The dev server proxies these same-origin browser routes to FastAPI:

- `GET /healthz`
- `GET /sessions`
- `GET /sessions/aggregate`
- `GET /sessions/{session_id}`
- `GET /sessions/{session_id}/events?after=SEQUENCE`
- `POST /sessions/{session_id}/messages`
- `POST /sessions/{session_id}/questions/{question_id}`
- `POST /sessions/{session_id}/approvals/{approval_id}`
- `POST /sessions/{session_id}/fork`

The SSE endpoint is intentionally covered by the `/sessions/:path*` rewrite.
Browser code should create `EventSource` connections to same-origin `/sessions/...`
URLs during local development so reconnects, `Last-Event-ID` style sequence
tracking, and query parameters flow through the same proxy path as normal HTTP
requests.

Future browser transport code may use `NEXT_PUBLIC_GLASSBOX_API_BASE_URL` for a
direct API origin override, but the default development path should stay
same-origin through the Next.js rewrite proxy. Leave that variable unset unless
you are deliberately bypassing the dev proxy for debugging.

## Manual Proxy Checks

With both servers running, verify the proxy before debugging browser code:

```bash
curl -fsS http://127.0.0.1:3000/healthz
curl -fsS http://127.0.0.1:3000/sessions
```

For SSE work, open a session in the app and confirm the browser Network panel
shows an `event-stream` request to `/sessions/{session_id}/events`. Reloading the
page should reconnect through the same URL with the latest `after` sequence once
the typed SSE client lands.

## Production Static Serving

Production does not run a Node server. Build the SPA, copy the static export into
the Python package tree, and serve it from FastAPI:

```bash
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend build
uv run glassbox dashboard serve --cwd . --host 127.0.0.1 --port 8765
```

Then open:

```text
http://127.0.0.1:8765/
```

`pnpm --dir frontend build` runs `next build` with static export enabled and
copies `frontend/out/` to `src/glassbox/web/static_next/`. The built SPA is the
default dashboard at `/`; `/app` remains a compatibility alias and direct nested
`/app/...` routes fall back to the SPA shell.

Use this production path before packaging or release validation so the installed
Python distribution can serve the dashboard without requiring Node.js or `pnpm`
at operator runtime.

## Generated API Types

Browser transport types are generated from the FastAPI OpenAPI schema. Refresh
them whenever a route, request model, response model, status code, or error
shape changes:

```bash
pnpm --dir frontend api:generate
```

The command exports the schema without starting a live server, writes
`frontend/generated/openapi.json`, and then writes
`frontend/generated/api-types.ts` with `openapi-typescript`. Handwritten
transport code should import these generated types rather than duplicating
FastAPI response interfaces.

## v4 Console Visual Density Rules

The v4 operator console uses shared surface and density tokens instead of
one-off panel styling. Keep these rules when adding or changing dashboard UI:

- Page backgrounds use the subtle surface token; primary work regions use card or raised surface tokens.
- Reserve warning and destructive badges for work that needs attention. Use muted, outline, info, or success for passive state.
- Use repeated cards for rows, dialogs, and discrete artifacts. Use section boundaries and data lists for grouped evidence instead of nesting cards inside cards.
- Keep attention rows and list rows on stable shared minimum heights so live updates, badges, and focus rings do not shift surrounding layout.
- Use compact `DataList` density for inspector evidence, timeline, runtime, metrics, lineage, compare, and verification rows.
- Long session ids, file paths, artifact paths, and branch labels should wrap or truncate inside their own row rather than widening the viewport.
