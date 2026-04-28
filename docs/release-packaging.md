# Release Packaging

Glassbox packages the production dashboard as static SPA assets inside the Python distribution. Runtime users should not need Node.js, pnpm, or a local frontend build to open `glassbox dashboard serve` from an installed package.

The modern terminal client is part of the Python package. The `textual>=6,<7` dependency is a runtime dependency because `glassbox session chat` and `glassbox session attach` use the full-screen TUI by default in supported terminals. Node and frontend tooling are not required for terminal chat.

## Build Release Assets

From the repository root:

```sh
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend api:generate
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
uv run python scripts/validate_package_contents.py
```

Before publishing, validate the wheel and sdist contents and confirm `glassbox/web/static_next/index.html`, `_next/static/...` assets, Python package modules, source-distribution docs, `textual>=6,<7`, and the `glassbox` console script are present. The FastAPI app validates the static export at startup time for dashboard requests: if `index.html` is missing or references a missing `/app/_next/...` file, `/` returns a developer-facing 503 that points back to `pnpm --dir frontend build`.

The v6 release gate also refreshes generated API files with `pnpm --dir frontend api:generate`, fails if `frontend/generated/openapi.json` or `frontend/generated/api-types.ts` changed, runs `pnpm --dir frontend build`, validates `src/glassbox/web/static_next/` with `uv run python scripts/validate_frontend_release_assets.py`, builds both distributions, and runs `uv run python scripts/validate_package_contents.py`.

## Installed Package Smoke

For release candidates, install the built wheel into a clean environment and run:

```sh
glassbox --help
glassbox command tree
glassbox session chat --help
glassbox session attach --help
glassbox session chat --plain --no-dashboard --cwd .
glassbox dashboard serve --cwd . --host 127.0.0.1 --port 8765
glassbox daemon status --json --cwd .
glassbox daemon start --cwd . --host 127.0.0.1 --port 8766
glassbox daemon stop --cwd .
glassbox eval run smoke.hello --cwd .
```

`glassbox --help`, `command tree`, `session chat --help`, and `session attach --help` prove the installed console script can import the command inventory and TUI dependency stack. The explicit `--plain` smoke protects fallback behavior in clean environments where a full-screen TUI is not practical. The v6 gate starts the dashboard from the installed wheel and requests `/`, `/app`, and one referenced `/app/_next/...` asset without a Node process. It also runs daemon status/start/stop in a temporary workspace and executes the deterministic `smoke.hello` eval against copied eval fixtures.

Known terminal limitations for this release candidate:

- Full-screen TUI launch requires interactive stdin and stdout, a non-`dumb` terminal, and a non-CI environment.
- Explicit `--tui` fails with a clear error when those requirements are not met.
- Implicit launch falls back to plain mode when full-screen launch is unsafe.

## Release Checklist

- `pnpm --dir frontend build` completed after the last frontend source or generated API type change.
- `pnpm --dir frontend api:generate` left no diff in `frontend/generated/openapi.json` or `frontend/generated/api-types.ts`.
- `src/glassbox/web/static_next/index.html` references only assets that exist under `src/glassbox/web/static_next/`.
- `uv run pre-commit run --all-files` passed.
- `uv build --wheel --sdist` produced distributions containing `glassbox/web/static_next/`, runtime package modules, source docs, TUI dependency metadata, and the `glassbox` console script.
- `uv run python scripts/validate_package_contents.py` passed against the built wheel and sdist.
- Package metadata includes `textual>=6,<7` and the `glassbox` console script.
- Installed-package terminal smoke passed for root help, `command tree`, `session chat --help`, `session attach --help`, and explicit plain fallback.
- Installed-package dashboard smoke passed for `/`, `/app`, and a representative static asset without Node.js running.
- Installed-package daemon smoke passed for status/start/stop in a temporary workspace.
- Installed-package deterministic eval smoke passed for `smoke.hello` in a temporary workspace with copied eval fixtures.

## v6 Release Hardening

The v6 release-hardening path expands package validation into the broader release-candidate gate. Use [v6-release-gate.md](./v6-release-gate.md) for the objective pass/fail gate, [v6-release-hardening.md](./v6-release-hardening.md) for the release contract, [v6-release-inventory.md](./v6-release-inventory.md) for the current validation inventory, [release-check-alignment-v6.md](./release-check-alignment-v6.md) for the local/push/release/advisory check ladder, [dependency-toolchain-review-v6.md](./dependency-toolchain-review-v6.md) for dependency/toolchain signoff, [v6-release-evidence.md](./v6-release-evidence.md) for the retained `summary.json` evidence format, and [manual-qa-evidence-v6.md](./manual-qa-evidence-v6.md) for terminal, dashboard, recovery, provider-canary, and accessibility evidence.

Users familiar with the v5 terminal release gate should note the v6 split: the
full-screen TUI remains the default terminal surface, but v6 adds real
cancellation evidence, installed-package dashboard smoke, provider diagnostics,
advisory live-provider canaries, dependency/toolchain review, and retained
manual QA artifacts. The remaining non-blocking limits are explicit: live
provider canaries stay advisory, terminal and dashboard accessibility claims are
limited to the reviewed evidence, and unsupported terminals continue to use
plain fallback.
