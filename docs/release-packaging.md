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

The source distribution also carries repository-owned eval fixtures and generated frontend API contracts: `evals/**`, `frontend/generated/openapi.json`, and `frontend/generated/api-types.ts`. Refresh the generated API files before building whenever FastAPI routes or response schemas change.

For the v9 public baseline, package validation also checks the operator-facing
v9 docs, dogfooding summary, cockpit contract, eval promotion plan, generated
API files, release validation scripts, and the installed-command surfaces used
by first-run readiness, workflow command discovery, provider diagnostics,
provider recommendations, promoted eval profiles, and the packaged dashboard.

## Installed Users Versus Source Builders

Installed-package users should only need Python and the packaged wheel. They can
run these commands without Node.js or pnpm:

```sh
glassbox --help
glassbox readiness check --cwd .
glassbox command guide --json
glassbox provider diagnostics --cwd .
glassbox session chat --plain --no-dashboard --cwd .
glassbox dashboard serve --cwd .
glassbox daemon status --cwd .
glassbox autonomy profile list --cwd .
glassbox task list --cwd .
glassbox memory list --cwd .
glassbox repo index status --cwd .
glassbox job list --cwd .
glassbox branch-search list --cwd .
glassbox eval profile list --cwd .
glassbox eval profile show release-candidate --cwd .
```

Source builders need Python 3.14, `uv`, Node.js 24 through Corepack, pnpm, and a
fresh frontend static export. Build from source in this order:

```sh
uv sync
corepack enable
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend api:generate
pnpm --dir frontend build
uv run python scripts/validate_frontend_release_assets.py
uv build --wheel --sdist
uv run python scripts/validate_package_contents.py
```

If generated API files are stale, `pnpm --dir frontend api:generate` followed by
the gate's generated-API diff check should show the changed files. If packaged
dashboard assets are stale or missing, `scripts/validate_frontend_release_assets.py`
reports the missing generated API file, missing `index.html`, or missing
`/app/_next/...` asset reference before the package is built.

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

Use `uv run --no-project --refresh --isolated --with dist/glassbox-*.whl ...`
when smoking a rebuilt wheel with the same project version from a source
checkout. `--no-project` prevents the checkout from shadowing the installed
wheel, and `--refresh` prevents uv from reusing an older cached install.
The standalone wrapper runs the same installed smoke matrix used by the release
gate and retains a summary:

```sh
uv run python scripts/validate_installed_wheel_smoke.py --wheel dist/glassbox-*.whl
```

```sh
glassbox --help
glassbox command tree
glassbox command guide --json
glassbox readiness check --json --cwd .
glassbox autonomy profile list --json --cwd .
glassbox provider diagnostics --cwd . --model-name openai:gpt-5.4
glassbox provider diagnostics --cwd <profile-workspace>
glassbox session chat --help
glassbox session attach --help
glassbox session chat --plain --no-dashboard --cwd .
glassbox task list --json --cwd .
glassbox memory list --json --cwd .
glassbox repo index status --json --cwd .
glassbox job list --json --cwd .
glassbox branch-search list --json --cwd .
glassbox dashboard serve --cwd . --host 127.0.0.1 --port 8765
glassbox daemon status --json --cwd .
glassbox daemon start --cwd . --host 127.0.0.1 --port 8766
glassbox daemon stop --cwd .
glassbox eval profile list --cwd .
glassbox eval profile show release-candidate --json --cwd .
glassbox eval run smoke.hello --cwd .
```

`glassbox --help`, `command tree`, `session chat --help`, and `session attach --help` prove the installed console script can import the command inventory and TUI dependency stack. The explicit `--plain` smoke protects fallback behavior in clean environments where a full-screen TUI is not practical. The v6 gate starts the dashboard from the installed wheel and requests `/`, `/app`, and one referenced `/app/_next/...` asset without a Node process. It also runs daemon status/start/stop in a temporary workspace and executes the deterministic `smoke.hello` eval against copied eval fixtures.

The installed smoke matrix now also covers the v8 local-autonomy surfaces from a wheel: autonomy profile listing, task inspection, workspace-memory listing, repository-index status, background-job listing, and branch-search listing. These checks run against empty temporary workspaces, so they remain credential-free and do not require provider access.

The v9 smoke matrix adds first-run readiness, workflow-oriented command
discovery, and promoted `release-candidate` profile inspection. These checks
prove a clean installed package can guide a new operator, expose the practical
command surface, and inspect the deterministic v9 eval ladder without live
provider credentials.

The v7 smoke matrix also runs provider diagnostics with an explicit model,
provider diagnostics against an example `glassbox.profile.json`, and eval profile
listing before the deterministic eval smoke. Retain clean-environment smoke notes
under `.glassbox/releases/YYYYMMDDTHHMMSSZ-v7-gate/onboarding/` or
`.glassbox/releases/YYYYMMDDTHHMMSSZ-v7-gate/packaging/` when preparing a v7
candidate.

Known terminal limitations for this release candidate:

- Full-screen TUI launch requires interactive stdin and stdout, a non-`dumb` terminal, and a non-CI environment.
- Explicit `--tui` fails with a clear error when those requirements are not met.
- Implicit launch falls back to plain mode when full-screen launch is unsafe.

## Release Checklist

- `pnpm --dir frontend build` completed after the last frontend source or generated API type change.
- `pnpm --dir frontend api:generate` left no diff in `frontend/generated/openapi.json` or `frontend/generated/api-types.ts`.
- `src/glassbox/web/static_next/index.html` references only assets that exist under `src/glassbox/web/static_next/`.
- `uv run pre-commit run --all-files` passed.
- `uv build --wheel --sdist` produced distributions containing `glassbox/web/static_next/`, runtime package modules, source docs, v8 and v9 eval fixtures, generated frontend API contracts, TUI dependency metadata, and the `glassbox` console script.
- `uv run python scripts/validate_package_contents.py` passed against the built wheel and sdist.
- Package metadata includes `textual>=6,<7` and the `glassbox` console script.
- Installed-package terminal and onboarding smoke passed for root help, `command tree`, `command guide --json`, `readiness check --json`, `session chat --help`, `session attach --help`, explicit plain fallback, provider diagnostics, and profile-example diagnostics.
- Installed-package v8 autonomy smoke passed for autonomy profile listing, task inspection, memory listing, repository-index status, background-job listing, and branch-search listing.
- Installed-package dashboard smoke passed for `/`, `/app`, and a representative static asset without Node.js running.
- Installed-package daemon smoke passed for status/start/stop in a temporary workspace.
- Installed-package eval smoke passed for profile listing, `release-candidate` profile inspection, and `smoke.hello` in a temporary workspace with copied eval fixtures.

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
