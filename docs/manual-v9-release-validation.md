# v9 Manual Release Validation

This document records the `GBX-992` manual validation pass for the v9
public-baseline track. The retained local evidence directory for this pass is:

```text
.glassbox/releases/gbx-992-manual-evidence/
```

The directory is local workspace state and is intentionally not committed. This
summary records command outcomes, bounded accessibility pairings, explicit
non-claims, residual risks, and the recommendation for continuing to the v9
release-candidate guide.

## Commands Run

Automated v9 gate dry run from `GBX-991`:

```bash
uv run python scripts/validate_v9_release_gate.py \
  --dry-run \
  --evidence-dir .glassbox/releases/gbx-991-v9-gate-dry-run
```

Result: passed. The dry run planned inherited v8 stages plus v9 readiness,
command-discovery, provider-evidence, provider-recommendation, promoted eval,
release-report, installed-smoke, and explicit advisory provider-canary skip
evidence. It wrote `summary.json`.

Focused v9 gate-stage evidence:

```bash
uv run glassbox readiness check --json --cwd .
uv run glassbox command guide --json
uv run glassbox provider canary evidence --cwd . --json
uv run glassbox provider recommend \
  --task-kind release \
  --autonomy-mode release-candidate \
  --cwd . \
  --json
uv run glassbox eval run \
  --profile release-candidate \
  --output-dir .glassbox/evals/gbx-991-v9-stage-smoke/promoted-autonomy \
  --refresh-output-dir \
  --cwd .
uv run glassbox eval report commit-smoke push-confirmation release-candidate \
  --output-dir .glassbox/evals/gbx-991-v9-stage-smoke/release-signoff \
  --cwd .
```

Result: readiness completed with `7` pass and `1` warning for stale repository
index. Command guide emitted the six workflow sections. Provider evidence was
fresh and advisory with one passed `streaming-text` scenario plus missing
scenario guidance. Provider recommendation returned `usable`,
`medium`-confidence, `partial` release fit with explicit unknowns. The
`release-candidate` eval profile passed `8/8` cases and the release report
passed all three requested profiles.

Terminal startup review:

```bash
uv run glassbox session chat \
  --plain \
  --no-dashboard \
  --cwd . \
  --db-path .glassbox/releases/gbx-992-manual-evidence/terminal/plain-chat.sqlite3
```

Result: passed. Plain startup printed session ID, model, approval behavior,
autonomy budget, workspace, database path, dashboard disabled posture, provider
posture, and first-prompt suggestions, then exited cleanly on EOF.

Dashboard cockpit review:

```bash
pnpm --dir frontend exec vitest run \
  tests/workspace-overview.test.ts \
  tests/session-inspector.test.ts \
  tests/task-autonomy-console.test.tsx \
  tests/knowledge-autonomy-console.test.tsx \
  tests/branch-search-console.test.tsx \
  tests/verification-cues.test.ts
```

Result: `29` tests passed across workspace attention summary, session evidence,
task controls, knowledge/memory/index sections, branch-search console, provider
and verification cues.

Browser workflow attempt:

```bash
pnpm --dir frontend exec playwright test \
  e2e/operator-workflows.spec.ts \
  --project chromium
```

Result: blocked. The Next.js dev-server path timed out with repeated `EMFILE:
too many open files, watch`. A second attempt used the packaged FastAPI static
dashboard server on `127.0.0.1:3210`, which served `/app`, but Chromium could
not launch in the sandbox: `bootstrap_check_in ... Permission denied (1100)`.
No v9 browser-rendered keyboard, mobile, or screen-reader claim is made from
this pass.

Recovery and maintenance review:

```bash
uv run glassbox projection check --all --cwd .
uv run glassbox artifacts inspect --cwd . --json
uv run glassbox daemon status --cwd . --json
uv run glassbox job list --cwd . --json
uv run glassbox repo index status --cwd . --json
uv run glassbox eval audit --cwd .
```

Result: projection check reported `24` ok and `0` degraded. Artifact inspection
reported `58` reclaimable orphaned artifacts, `333452` reclaimable bytes, `945`
event-referenced artifacts, and no storage warning. Daemon status was
`not_running` with a clear `daemon start` next action. Job list returned no
jobs. Repository index was stale and reported exact added/changed paths plus
rebuild guidance. Eval audit covered `20/20` capabilities.

Package smoke:

```bash
pnpm --dir frontend build
uv build --wheel --sdist
uv run python scripts/validate_package_contents.py
uv run python scripts/validate_installed_wheel_smoke.py \
  --wheel dist/glassbox-0.9.0-py3-none-any.whl \
  --evidence-dir .glassbox/releases/gbx-990-installed-wheel-smoke
```

Result: package build, content validation, dashboard static asset build, and
installed-wheel smoke passed during `GBX-990` and `GBX-991`.

## Manual Validation Checklist

| Area | Status | Evidence |
| --- | --- | --- |
| First-run readiness | Passed with warning | Readiness smoke passed and warned only that repository index is stale. |
| Chat startup summary | Passed | Plain startup printed model, approval, autonomy, workspace, database, dashboard, provider, and prompt guidance. |
| Dashboard cockpit | Passed component review | Focused Vitest cockpit and console tests passed `29/29`. |
| Attention summary | Passed component review | `workspace-overview.test.ts` covered priority and healthy states. |
| Task evidence drill-down | Passed component review | `session-inspector` and `task-autonomy-console` tests covered task/evidence surfaces. |
| Recovery cues | Passed command review | Projection, daemon, job, artifact, index, and eval-audit commands returned next actions or healthy summaries. |
| Provider evidence cues | Passed command/component review | Provider canary evidence and provider recommendation reported advisory freshness and unknowns. |
| Package smoke | Passed | Wheel/sdist build, package contents, installed smoke, and dashboard static assets passed. |

## Terminal Review

| Area | Result | Notes |
| --- | --- | --- |
| Supported TTY | Partial | Full-screen TUI was not manually recorded in this pass; existing TUI tests and installed smoke remain the evidence. |
| Plain fallback | Passed | `session chat --plain --no-dashboard` started and exited cleanly. |
| Startup summaries | Passed | Startup summary named model, approval, autonomy, workspace, database, dashboard, provider, and prompt ideas. |
| Approvals/questions | Covered by tests | Dashboard and terminal workflow tests cover action resolution; no live provider approval transcript was recorded. |
| Cancellation | Covered by tests/evals | Cancellation remains covered by deterministic evals and task/job controls. |
| Daemon attach | Partial | Daemon status guidance was reviewed; no live daemon attach transcript was recorded. |
| Long output | Covered by eval/report evidence | Large transcript visual review remains a release-candidate residual check. |

## Dashboard Review

| Area | Result | Notes |
| --- | --- | --- |
| Cockpit priority | Passed component review | Workspace overview tests cover attention priority. |
| Keyboard flow | Partial | Component tests cover accessible controls; Playwright keyboard run was blocked by local Chromium launch permission. |
| Mobile layout | Partial | Existing Playwright spec names mobile workflows, but this pass could not launch Chromium. |
| Task evidence | Passed component review | Session inspector and task console tests passed. |
| Memory/index recovery | Passed component review | Knowledge console tests passed and CLI index status showed stale guidance. |
| Provider cues | Passed command/component review | Provider evidence remained advisory, fresh, and explicit about missing scenarios. |
| Branch comparison | Passed component review | Branch-search console tests passed. |

## Named Accessibility Pairings

| Pairing | Status | Claims |
| --- | --- | --- |
| Terminal: macOS, zsh, plain line-mode fallback, keyboard input/EOF | Reviewed | Plain startup text is readable in non-full-screen mode and exits cleanly. |
| Dashboard: Vitest/jsdom component environment with accessible roles and labels | Reviewed | Component-level role/name, keyboard-control, and responsive-state assertions passed where covered by focused tests. |
| Dashboard: Chromium headless on macOS sandbox | Blocked | Browser could not launch because of sandbox `bootstrap_check_in` permission failure; no rendered browser claim. |

Non-claims: no screen reader pass was run; no VoiceOver, NVDA, Narrator, Orca,
Safari, Firefox, or real mobile-device claim is made; no browser screenshot
archive was produced in this pass.

## Residual Risks

- Browser-rendered dashboard keyboard and mobile evidence is blocked in this
  environment by Next watcher `EMFILE` and Chromium sandbox permission failure.
  Component evidence passed, but final release signoff should rerun Playwright
  in an environment that can launch Chromium.
- Full-screen TUI was not manually recorded; existing automated TUI coverage and
  installed smoke remain the evidence for this pass.
- Repository index is stale after the v9 gate/docs changes; readiness and
  recovery commands report exact rebuild guidance.
- Provider evidence is fresh but partial for release-candidate work; only
  `streaming-text` is covered by retained live canary evidence, and all
  provider evidence remains advisory.

## Recommendation

Provisional go for continuing to the v9 release-candidate guide. Do not publish
the final v9 release-candidate decision until `GBX-993` records the final gate
state, explicitly accepts or closes the browser/manual residual risks above,
and names the evidence directory used for final signoff.

Use [manual-qa-evidence-v9.md](./manual-qa-evidence-v9.md) for future v9 manual
validation manifests and redaction rules.
