# Release Packaging

Glassbox packages the production dashboard as static SPA assets inside the Python distribution. Runtime users should not need Node.js, pnpm, or a local frontend build to open `glassbox dashboard serve` from an installed package.

The modern terminal client is part of the Python package. The `textual>=6,<7` dependency is a runtime dependency because `glassbox session chat` and `glassbox session attach` use the full-screen TUI by default in supported terminals. Node and frontend tooling are not required for terminal chat.

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
uv build --wheel --sdist
```

Before publishing, inspect the wheel contents and confirm `glassbox/web/static_next/index.html` and `_next/static/...` assets are present. Also confirm the package metadata includes `textual>=6,<7` and the `glassbox` console script. The FastAPI app validates the static export at startup time for dashboard requests: if `index.html` is missing or references a missing `/app/_next/...` file, `/` returns a developer-facing 503 that points back to `pnpm --dir frontend build`.

## Installed Package Smoke

For release candidates, install the built wheel into a clean environment and run:

```sh
glassbox session chat --help
glassbox session attach --help
glassbox session chat --plain --no-dashboard --cwd .
glassbox dashboard serve --cwd . --host 127.0.0.1 --port 8765
```

`session chat --help` and `session attach --help` prove the installed console script can import the TUI dependency stack. The explicit `--plain` smoke protects fallback behavior in clean environments where a full-screen TUI is not practical. Open `http://127.0.0.1:8765/` and confirm the operator console loads without a Node process. Also open `http://127.0.0.1:8765/?session=SESSION_ID` against a known persisted session when one is available.

Known terminal limitations for this release candidate:

- Full-screen TUI launch requires interactive stdin and stdout, a non-`dumb` terminal, and a non-CI environment.
- Explicit `--tui` fails with a clear error when those requirements are not met.
- Implicit launch falls back to plain mode when full-screen launch is unsafe.

## Release Checklist

- `pnpm --dir frontend build` completed after the last frontend source or generated API type change.
- `src/glassbox/web/static_next/index.html` references only assets that exist under `src/glassbox/web/static_next/`.
- `uv run pre-commit run --all-files` passed.
- `uv build --wheel --sdist` produced distributions containing `glassbox/web/static_next/`.
- Package metadata includes `textual>=6,<7` and the `glassbox` console script.
- Installed-package terminal smoke passed for `session chat --help`, `session attach --help`, and explicit plain fallback.
- Installed-package dashboard smoke passed without Node.js running.
