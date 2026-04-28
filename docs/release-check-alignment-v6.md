# v6 Check Alignment

Glassbox v6 uses one layered release ladder instead of separate local, eval, and
packaging rituals.

## Local Blocking

`uv run pre-commit run --all-files` is the daily blocking check. It covers Python
format, lint, typecheck, pytest, deterministic eval smoke, and frontend checks
when frontend or web API files change.

Frontend local checks intentionally mirror release asset expectations:

- `pnpm --dir frontend api:generate` refreshes OpenAPI and TypeScript API files;
  pre-commit fails when that hook modifies generated files.
- `pnpm --dir frontend build` verifies the static export path that release
  packaging copies into `src/glassbox/web/static_next/`.

## Push Confirmation

`uv run glassbox eval run --profile push-confirmation --cwd .` is the retained
post-push deterministic confirmation surface. It stays blocking and deterministic
but does not include packaging, installed-wheel, or live-provider checks.

## Release Candidate

`uv run python scripts/validate_v6_release_gate.py` is the release-candidate gate.
It includes local-style Python checks, deterministic eval smoke, frontend API and
static asset freshness, package build and content validation, and installed-wheel
terminal, dashboard, daemon, and eval smoke.

Use `uv run glassbox eval report commit-smoke push-confirmation release-candidate
--cwd .` for deterministic eval sign-off evidence. The report is intentionally
limited to deterministic profiles. Operator workflows such as approval and
ask-user remain covered by integration and release-gate evidence until curated
replay cases are stable enough to join deterministic report sign-off.

## Advisory Checks

`advisory-context` and `live-provider-canary` are non-blocking advisory tracks.
Strict artifact-context drift, approval replay gaps, ask-user replay gaps, and
live-provider behavior can be retained as release evidence, but they do not
replace the blocking local or release-candidate gates.

Run `uv run glassbox eval recommend PATH --cwd .` before choosing extra eval
scope for a changed area. Recommendation output explains the impacted daily,
push, and release surfaces without adding hidden path lists to the gate.
