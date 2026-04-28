# v6 Dependency And Toolchain Review

This review records the dependency and toolchain posture for v6 release signoff.
It is not an upgrade plan; broad upgrades should remain separate changes with
their own validation evidence.

## Runtime Baseline

- Python support is explicit: `>=3.14,<3.15`. v6 does not claim Python 3.13 or
  3.15 compatibility.
- Runtime users should not need Node.js, pnpm, Playwright, Vitest, or TypeScript.
  The dashboard is packaged as static assets and served by FastAPI.
- Source builders need `uv`, Python 3.14, pnpm `10.26.2`, and the frontend
  lockfile.

## Python Runtime Dependencies

| Dependency | Declared bound | Locked version | Release note |
| --- | --- | ---: | --- |
| `aiofiles` | `>=25.1.0` | `25.1.0` | Used for async file serving/storage paths; low churn risk. |
| `fastapi` | `>=0.115,<1` | `0.136.0` | Primary web API and dashboard shell surface; keep OpenAPI generation in the release gate. |
| `pydantic` | `>=2.11,<3` | `2.13.1` | Core event/model validation; do not cross to v3 without replay/schema review. |
| `pydantic-ai` | `>=1.83,<2` | `1.83.0` | Provider/model integration boundary; live-provider canaries remain advisory evidence. |
| `textual` | `>=6,<7` | `6.12.0` | Primary TUI dependency; installed-wheel smoke and manual terminal review are release evidence. |
| `uvicorn[standard]` | `>=0.34,<1` | `0.44.0` | Dashboard and daemon server runtime; installed dashboard smoke covers packaged serving. |

## Python Development Tools

| Tool | Declared bound | Locked version | Release note |
| --- | --- | ---: | --- |
| `httpx` | `>=0.28,<1` | `0.28.1` | Test client for FastAPI and integration tests. |
| `pre-commit` | `>=4.2,<5` | `4.5.1` | Local blocking check runner. |
| `pytest` | `>=8.3,<9` | `8.4.2` | Unit and integration test runner. |
| `ruff` | `>=0.15,<0.16` | `0.15.10` | Format/lint gate; version bound is intentionally narrow. |
| `ty` | `>=0.0.1a16,<0.1` | `0.0.31` | Alpha type checker; keep release failures actionable and expect churn. |

## Frontend Dependencies And Tooling

| Dependency/tool | Declared version | Locked version | Release note |
| --- | --- | ---: | --- |
| pnpm | `10.26.2` | lockfile-managed | Required only for source builds and release asset generation. |
| Next.js | `16.2.4` | `16.2.4` | Static export contract; release gate validates copied assets. |
| React / React DOM | `19.2.5` | `19.2.5` | Dashboard rendering baseline. |
| Radix UI | mixed `1.x` / `2.x` bounds | lockfile-managed | Dialog, menu, scroll, tabs, toast, tooltip primitives. |
| Playwright | `^1.59.1` | `1.59.1` | E2E and screenshot workflows; not required at runtime. |
| Vitest | `4.1.5` | `4.1.5` | Component and state tests. |
| TypeScript | `5.9.3` | `5.9.3` | Typecheck and generated API type compatibility. |
| ESLint / Next ESLint config | `9.39.4` / `16.2.4` | lockfile-managed | Frontend lint gate. |
| Tailwind CSS | `3.4.19` | `3.4.19` | Styling build input; static output is packaged. |

## Review Checklist

Before v6 release signoff:

- Confirm `pyproject.toml`, `uv.lock`, `frontend/package.json`, and
  `frontend/pnpm-lock.yaml` are committed and reviewed together when dependency
  metadata changes.
- Run `uv run python scripts/validate_v6_release_gate.py` for blocking release
  evidence.
- Run `pnpm --dir frontend install --frozen-lockfile` before frontend release
  asset generation in a fresh checkout or CI runner.
- Treat `pnpm --dir frontend outdated`, `pnpm --dir frontend audit`, and any
  Python vulnerability/license audit output as advisory inputs that require
  human triage before becoming release blockers.
- Keep security/license concerns separate from ordinary freshness. A stale but
  functioning dependency is not the same decision as a vulnerable, incompatible,
  or license-incompatible dependency.

## Residual Risks

- Python 3.14-only support narrows install compatibility; this is intentional for
  v6 and should be visible in package metadata and docs.
- `ty` is still alpha software. A future alpha update may change diagnostics;
  the narrow bound reduces accidental churn.
- `pydantic-ai` and provider SDK transitive dependencies affect real-provider
  behavior. Advisory provider canaries are the release evidence until live
  provider checks become deterministic enough to block.
- Next.js and React are pinned to current major versions; static export and
  dashboard route smoke are the release evidence for packaged users.
