# Release Packaging

Glassbox packages the production dashboard as static SPA assets inside the Python distribution. Runtime users should not need Node.js, pnpm, or a local frontend build to open `glassbox dashboard serve` from an installed package.

## Build Release Assets

From the repository root:

```sh
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend build
```

The frontend build exports the Next.js app and copies `frontend/out/` into `src/glassbox/web/static_next/`. The `pyproject.toml` wheel and sdist targets include `src/glassbox/web/static_next/**` as release artifacts.

## Validate Before Packaging

Run the normal repository gates:

```sh
uv run pre-commit run --all-files
```

Then build the Python package:

```sh
uv build --wheel
```

Before publishing, inspect the wheel contents and confirm `glassbox/web/static_next/index.html` and `_next/static/...` assets are present. The FastAPI app validates the static export at startup time for dashboard requests: if `index.html` is missing or references a missing `/app/_next/...` file, `/` returns a developer-facing 503 that points back to `pnpm --dir frontend build`.

## Installed Package Smoke

For release candidates, install the built wheel into a clean environment and run:

```sh
glassbox dashboard serve --cwd . --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765/` and confirm the operator console loads without a Node process. Also open `http://127.0.0.1:8765/?session=SESSION_ID` against a known persisted session when one is available.

## Release Checklist

- `pnpm --dir frontend build` completed after the last frontend source or generated API type change.
- `src/glassbox/web/static_next/index.html` references only assets that exist under `src/glassbox/web/static_next/`.
- `uv run pre-commit run --all-files` passed.
- `uv build --wheel` produced a wheel containing `glassbox/web/static_next/`.
- Installed-package dashboard smoke passed without Node.js running.
