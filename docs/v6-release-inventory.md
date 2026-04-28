# v6 Gate, Gap, And Evidence Inventory

This inventory supports `GBX-641` in [tasks-v6.md](./tasks-v6.md). It records the validation surfaces that already exist before the v6 gate is implemented, the weak spots v6 must close, and the recommended split between automated gate checks and manual release signoff.

Use this document with [v6-release-hardening.md](./v6-release-hardening.md), [v5-terminal-release-gate.md](./v5-terminal-release-gate.md), [v4-ux-release-gate.md](./v4-ux-release-gate.md), [release-packaging.md](./release-packaging.md), and [replay-evals.md](./replay-evals.md).

## Current Automated Validation Surfaces

| Concern | Current command or source | Current evidence | v6 recommendation |
| --- | --- | --- | --- |
| Python formatting | `uv run ruff format --check .` | `pyproject.toml` config and pre-commit hook | Keep blocking in v6 gate. |
| Python linting | `uv run ruff check .` | `pyproject.toml` config and pre-commit hook | Keep blocking in v6 gate. |
| Python type checking | `uv run ty check` | `pyproject.toml` config and pre-commit hook | Keep blocking in v6 gate. |
| Python test suite | `uv run pytest` | `tests/` integration and unit coverage | Keep blocking in v6 gate after focused suites. |
| Deterministic eval smoke | `uv run glassbox eval run` and pre-commit eval hook | `evals/` cases, bundles, profiles, and retained summaries | Keep blocking in v6 gate. |
| Commit-time eval profile | `commit-smoke` in `evals/profiles.json` | Blocking deterministic smoke profile with budget | Keep as local blocking evidence. |
| Push-time eval profile | `push-confirmation` in `evals/profiles.json` | Blocking deterministic confirmation profile | Use for release-report alignment, not necessarily every local gate. |
| Release-candidate eval profile | `release-candidate` in `evals/profiles.json` | Blocking deterministic release profile | Include in v6 release evidence or report flow. |
| Advisory context eval profile | `advisory-context` in `evals/profiles.json` | Non-blocking context-heavy profile | Keep advisory unless promoted by a later task. |
| Live-provider canary scaffold | `live-provider-canary` in `evals/profiles.json` | Non-blocking advisory placeholder | Keep advisory; add explicit skip/evidence behavior in v6. |
| TUI release gate | `uv run python scripts/validate_v5_terminal_release_gate.py` | Focused terminal tests, full tests, eval smoke, build, installed plain smoke | Reuse or subsume in v6 gate. |
| TUI focused tests | Focused suite listed in [v5-terminal-release-gate.md](./v5-terminal-release-gate.md) | Launch, fallback, widgets, workflows, daemon attach, packaging | Keep focused preflight before full tests. |
| Frontend lint | `pnpm --dir frontend lint` | ESLint over the SPA | Keep blocking when frontend files or generated API contracts change; include in full v6 gate. |
| Frontend typecheck | `pnpm --dir frontend typecheck` | TypeScript compile checks | Keep blocking in v6 gate. |
| Frontend unit/component tests | `pnpm --dir frontend test` | Vitest and Testing Library coverage | Keep blocking in v6 gate. |
| Frontend static build | `pnpm --dir frontend build` | Next static export copied into `src/glassbox/web/static_next/` | Keep blocking in v6 gate and pair with freshness checks. |
| Frontend e2e workflows | `pnpm --dir frontend test:e2e` | Playwright operator workflows plus build check | Include in release gate or manual-triggered release path depending runtime cost. |
| v4 dashboard UX gate | `pnpm --dir frontend validate:v4-ux` | Frontend checks, screenshots, static export, Python web tests | Keep as dashboard UX reference; v6 gate should select critical parts. |
| OpenAPI generation | `pnpm --dir frontend api:generate` | `frontend/generated/openapi.json` and `api-types.ts` | Add freshness check in v6 packaging tasks. |
| Package build | `uv build --wheel --sdist` | Hatch wheel/sdist artifacts | Keep blocking in v6 gate. |
| Package metadata | `tests/unit/test_packaging_metadata.py` | Console script and dependency/package checks | Keep blocking in focused packaging suite. |
| Static SPA serving | `tests/integration/test_web_spa_static.py` | FastAPI static asset validation | Keep blocking in packaging/dashboard smoke. |
| Command inventory | `uv run glassbox command tree` | Operator-visible CLI command tree | Include installed-wheel smoke and release evidence. |
| Projection health | `glassbox projection check --all` plus projection tests | Rebuildable projection integrity | Include manual recovery smoke; automate focused tests where cheap. |
| Observability health | `glassbox observability status --json` and tests | Runtime, projection, transport, verification next actions | Include in manual recovery smoke and release evidence. |
| Daemon lifecycle | `tests/integration/test_daemon_runtime.py` plus command smoke | Runtime owner metadata and attach paths | Add stronger v6 focused gate coverage and installed smoke. |
| Backup and artifacts | Integration tests plus CLI commands | Workspace backup and artifact retention behavior | Include manual recovery smoke; automate only focused regression tests. |

## Current Manual Validation Surfaces

| Concern | Current source | Current evidence | v6 recommendation |
| --- | --- | --- | --- |
| Terminal visual review | [v5-terminal-release-gate.md](./v5-terminal-release-gate.md) | Manual terminal sizes and workflows | Formalize evidence archive and checklist in `GBX-690` and `GBX-691`. |
| Dashboard visual review | [v4-ux-release-gate.md](./v4-ux-release-gate.md) and screenshot archive | Playwright screenshot archive plus human review | Keep critical screenshot review and add v6 manual evidence policy. |
| Screen-reader review | v4 and v5 known gaps | Manual-only before public accessibility claims | Formalize as explicit claims/non-claims in v6 evidence. |
| Real-provider session | v5 manual validation and provider docs | Manual when credentials are available | Convert to advisory canary workflow with skip reasons. |
| Installed dashboard smoke | [release-packaging.md](./release-packaging.md) | Manual dashboard serve from installed package | Automate critical HTTP smoke, keep visual check manual. |
| Daemon lifecycle smoke | [v2-release-candidate.md](./v2-release-candidate.md) | Manual daemon start/status/attach/stop | Add installed smoke and keep manual release evidence. |
| Recovery smoke | [v2-release-candidate.md](./v2-release-candidate.md) | Manual projection, artifact, backup checks | Keep manual because restore/prune workflows can be destructive. |
| Dependency freshness | Lockfiles and package manifests | Informal review | Add explicit v6 review task and residual risk decision. |

## Weak Or Missing Coverage

These are the main gaps that Phase 64 should feed into later v6 work.

- **Real cancellation**: v5 documents honest interruption, but there is no backend cancellation contract, command/API path, persisted cancellation semantics, replay/eval treatment, or daemon attach coverage.
- **Transport backpressure**: SSE reconnect uses an `after` cursor, but slow subscribers, dropped live events, and queue pressure need stronger deterministic tests and observability.
- **Installed-package breadth**: v5 installed smoke covers terminal help and explicit plain fallback; v6 should add command tree, dashboard HTTP smoke, daemon command paths, and packaging content checks.
- **Generated asset freshness**: frontend API generation and static export freshness are documented but not yet one release-gate invariant.
- **Release evidence retention**: existing commands print useful output, but there is no single retained gate summary that points to logs, eval summaries, package artifacts, skipped canaries, and manual evidence.
- **Provider canary policy**: the eval profile scaffold exists, but skip behavior, redaction, scenario selection, and release interpretation are not formalized.
- **Manual evidence shape**: v4 screenshots and v5 manual checklists exist, but v6 needs a unified evidence directory and release-candidate manifest.
- **Accessibility claims**: screen-reader and terminal accessibility review remains manual; public claims need evidence-backed limits.
- **Dependency/toolchain review**: Python, Textual, FastAPI, pydantic-ai, Next.js, React, Playwright, Vitest, TypeScript, `uv`, and `pnpm` expectations should be reviewed explicitly before release signoff.

## Recommended v6 Gate Membership

The v6 gate should be deterministic by default. It should run these checks as blocking automated stages:

1. Python format, lint, and typecheck.
2. Focused cancellation suite once `GBX-650` through `GBX-655` are implemented.
3. Focused transport, SSE, daemon, and mutation-ownership suite once `GBX-660` through `GBX-665` are implemented.
4. Focused TUI workflow suite from the v5 gate.
5. Focused web/dashboard API and static-serving tests.
6. Full Python test suite.
7. Deterministic eval smoke and release-profile report alignment.
8. Frontend lint, typecheck, unit/component tests, and production build.
9. OpenAPI/generated type freshness and static asset freshness checks once implemented.
10. Wheel and sdist build plus content inspection.
11. Installed-wheel smoke for command tree, terminal help, explicit plain fallback, dashboard static HTTP serving, and daemon command paths.
12. Release evidence summary writing.

## Recommended Manual Signoff Membership

These checks should remain manual release-candidate signoff unless a later task introduces stable automation:

- terminal visual review at representative sizes
- terminal keyboard-only review across prompt, command palette, approval, question, cancellation, attach, reconnect, and quit workflows
- dashboard responsive review across queue, selected-session, action, lineage, compare, evidence, and recovery states
- screen-reader review and accessibility claims/non-claims
- real-provider canary review when credentials are available
- installed dashboard visual smoke from the packaged static app
- daemon lifecycle smoke in a clean temporary workspace
- projection, artifact, backup, replay, eval report, and observability recovery smoke
- dependency/toolchain freshness review and residual risk decision

## Evidence Ownership

The v6 release gate should produce retained local evidence for automated stages. Manual checks should attach their own manifest into the same release evidence directory once `GBX-643` and `GBX-690` define the artifact shape.

Until that exists, contributors should keep using:

- `.glassbox/evals/` for retained eval summaries
- `dist/` for wheel and sdist outputs
- `frontend/test-results/` for Playwright and screenshot artifacts
- `.glassbox/` daemon metadata and logs for runtime-owner inspection

## Related Files

- [tasks-v6.md](./tasks-v6.md)
- [v6-release-hardening.md](./v6-release-hardening.md)
- [v5-terminal-release-gate.md](./v5-terminal-release-gate.md)
- [v4-ux-release-gate.md](./v4-ux-release-gate.md)
- [release-packaging.md](./release-packaging.md)
- [replay-evals.md](./replay-evals.md)
- [providers.md](./providers.md)
- [v2-release-candidate.md](./v2-release-candidate.md)
