# v6 Release Candidate Gate

This is the objective pass/fail gate for calling the current Glassbox build a
v6 release candidate. It combines the automated release script, retained
evidence, manual validation, advisory provider canaries, and accepted residual
risks into one decision path.

## Release Command

Run the automated gate from the repository root:

```bash
uv run python scripts/validate_v6_release_gate.py
```

Use an explicit evidence directory when preparing a named candidate:

```bash
uv run python scripts/validate_v6_release_gate.py \
  --evidence-dir .glassbox/releases/v6-rc-candidate
```

Live-provider canaries are advisory and skipped by default. Run them only when
credentials are available and the operator has reviewed the redaction policy:

```bash
uv run python scripts/validate_v6_release_gate.py \
  --include-provider-canaries \
  --evidence-dir .glassbox/releases/v6-rc-candidate
```

## Automated Blocking Stages

The script executes these deterministic stages before installed-wheel smoke:

| Stage | Evidence |
| --- | --- |
| `python format` | `uv run ruff format --check .` |
| `python lint` | `uv run ruff check .` |
| `python typecheck` | `uv run ty check` |
| `focused cancellation suite` | cancellation runtime, API, tool, and subprocess tests |
| `focused transport and daemon suite` | SSE, transport, daemon, and session command tests |
| `focused terminal and dashboard suite` | TUI, dashboard, static asset, and packaging metadata tests |
| `full python tests` | full `uv run pytest` suite |
| `deterministic eval smoke` | repository-local deterministic eval run |
| `frontend lint` | `pnpm --dir frontend lint` |
| `frontend typecheck` | `pnpm --dir frontend typecheck` |
| `frontend tests` | `pnpm --dir frontend test` |
| `frontend API generation` | regenerates OpenAPI and frontend API types |
| `frontend generated API freshness` | fails on generated API diffs |
| `frontend production build` | Next static export and packaged static asset copy |
| `frontend static asset validation` | validates generated API files and packaged static assets |
| `package build` | wheel and sdist build |
| `package contents validation` | wheel/sdist content and metadata inspection |

After package validation, the gate runs installed-wheel smoke from the newest
`dist/glassbox-*.whl`:

| Smoke group | Evidence |
| --- | --- |
| `installed terminal: root help` | console script imports and prints help |
| `installed terminal: version` | installed console script prints the package version |
| `installed terminal: command tree` | installed command inventory is available |
| `installed terminal: chat help` | interactive chat parser and TUI dependency stack import |
| `installed terminal: attach help` | attach parser and TUI dependency stack import |
| `installed terminal: plain fallback` | explicit plain mode starts and exits in a clean workspace |
| `installed autonomy: profile list` | built-in autonomy profiles are available from the installed wheel |
| `installed task: list` | task-plan inspection is scriptable in a clean workspace |
| `installed first-run: provider diagnostics` | provider diagnostics and first-run checklist run without Node.js        |
| `installed first-run: profile example`      | an example `glassbox.profile.json` is accepted by installed diagnostics |
| `installed memory: list` | workspace-memory inspection is scriptable in a clean workspace |
| `installed repository index: status` | repository-index status reports from an installed package |
| `installed background jobs: list` | background-job status is scriptable in a clean workspace |
| `installed branch-search: list` | branch-search inspection is scriptable in a clean workspace |
| `installed daemon: status before start` | daemon status is scriptable before ownership exists |
| `installed daemon: start` | daemon starts from the installed wheel |
| `installed daemon: status after start` | daemon reports running state after start |
| `installed daemon: stop` | daemon stops and releases ownership metadata |
| `installed eval: profile list` | installed eval profile listing can read packaged/copied eval fixtures |
| `installed eval: deterministic smoke` | installed eval runner executes `smoke.hello` |
| `installed dashboard: static routes` | installed dashboard serves `/`, `/app`, and a `_next` asset |

## Manual Validation Matrix

Manual release evidence lives in the same `.glassbox/releases/...` directory as
the automated `summary.json`, using [manual-qa-evidence-v6.md](./manual-qa-evidence-v6.md).

| Area | Required evidence |
| --- | --- |
| Terminal UX | size review at `120x36`, `100x30`, `80x24`, and `60x20`; keyboard-only workflow notes; accessibility claims and non-claims |
| Dashboard UX | desktop, tablet, and mobile viewport review; keyboard workflow notes; screenshot archive pointers; accessibility claims and non-claims |
| Recovery and maintenance | observability, projections, artifacts, backups, replay/eval, daemon recovery, and installed dashboard smoke notes |
| Provider canaries | advisory run evidence or explicit credential-unavailable skip reason |
| Release decision | blocking issue list, residual risk list, follow-up backlog, and go/no-go state |

## Automated Coverage Map

| Requirement | Automated evidence | Manual or retained evidence |
| --- | --- | --- |
| Cancellation is persisted and replay/eval-safe | focused cancellation suite, full tests, deterministic eval smoke | terminal/dashboard cancellation notes |
| Live transport and daemon ownership are dependable | focused transport and daemon suite, installed daemon smoke | daemon lifecycle notes |
| Full-screen terminal remains the primary chat surface | focused terminal tests, installed terminal smoke | terminal review evidence |
| Dashboard is packaged and serves without Node.js | frontend build, static asset validation, package contents validation, installed dashboard smoke | dashboard review evidence |
| Replay/eval stays deterministic for release signoff | deterministic eval smoke, eval report docs, full tests | retained eval summary pointers |
| Package artifacts are reproducible enough to ship | package build, package contents validation, installed smoke | dependency/toolchain review |
| Provider behavior is visible but not deterministic release authority | optional provider canary profile | advisory provider-canary evidence or skip reason |
| Recovery workflows are usable when things go wrong | recovery integration tests included in full tests | recovery and maintenance review evidence |

## Pass And Fail Policy

- Deterministic stage failure blocks the release candidate.
- Generated API freshness failure blocks until the generated files are reviewed
  and committed or the API change is reverted.
- Frontend build or static asset validation failure blocks because installed
  dashboard users should not need Node.js.
- Package build, package contents, installed terminal, installed dashboard,
  installed daemon, or installed eval smoke failure blocks.
- Daemon lifecycle failure blocks when it affects supported runtime ownership or
  attach behavior.
- Cancellation failure blocks once cancellation events, API, TUI, dashboard,
  daemon, replay, and eval coverage are marked complete.
- Manual accessibility or UX findings block when they affect a supported primary
  workflow or contradict a public accessibility claim.
- Provider-canary skips do not block when credentials are unavailable and the
  skip reason is retained.
- Provider-canary failures are advisory by default, but the release decision must
  record impact, next action, and whether the failure changes any supported
  provider claim.
- Residual risks are allowed only when named, mitigated, and accepted in the
  release decision.

## v5 Gap Decision

The v5 known gaps are resolved or accepted for v6 as follows:

| v5 gap | v6 decision |
| --- | --- |
| Backend cancellation was not implemented | Resolved as a release-blocking deterministic behavior with retained cancellation evidence. |
| Terminal visual review was manual | Accepted only with the v6 manual evidence archive and explicit claims/non-claims. |
| Real provider behavior needed manual validation | Reclassified as advisory provider-canary evidence; deterministic eval remains release authority. |
| Full-screen support depended on terminal capabilities | Accepted with documented plain fallback and strict `--tui` behavior. |
| Screen-reader review remained manual | Accepted only as limited reviewed evidence; no broad certification claim is made. |

## Residual Risk Register

| Risk | Evidence | Impact | Mitigation | Decision |
| --- | --- | --- | --- | --- |
| Provider-specific cancellation may not stop remote computation immediately | deterministic local cancellation tests; advisory provider canaries when available | provider billing or remote work may continue after local cancellation is recorded | document local cancellation semantics and inspect provider canary notes | accepted for v6 |
| Live-provider canaries may be skipped without credentials | retained advisory skip reason | less confidence in real-provider drift for that candidate | keep deterministic replay/eval blocking and run canaries in credentialed release environments | accepted for v6 |
| Terminal and dashboard accessibility claims are limited | manual terminal/dashboard reviews | unsupported assistive technology combinations may have issues | publish claims/non-claims and treat blocking findings as release blockers | accepted for v6 |
| Installed smoke is intentionally short | installed terminal/dashboard/daemon/eval smoke | some deep dashboard states are covered by source tests rather than installed smoke | keep package content/static route checks plus screenshot archive evidence | accepted for v6 |
| Plain fallback remains necessary for unsupported terminals | TUI launch/fallback tests and docs | unsupported terminals do not get the full-screen experience | keep explicit `--plain` and strict `--tui` behavior | accepted for v6 |

## Evidence Artifacts

Every candidate must retain:

- automated `summary.json` from `scripts/validate_v6_release_gate.py`
- manual `manual-validation.md` in the same evidence directory
- links or paths to terminal, dashboard, recovery, provider-canary, eval, package,
  and installed-smoke artifacts as applicable
- final release decision notes in the release-candidate guide or evidence
  manifest

The evidence directory is local workspace state. Do not store secrets,
unredacted provider content, or large binary artifacts in git by default.

## Related Files

- [v6-release-hardening.md](./v6-release-hardening.md)
- [v6-release-evidence.md](./v6-release-evidence.md)
- [manual-qa-evidence-v6.md](./manual-qa-evidence-v6.md)
- [release-check-alignment-v6.md](./release-check-alignment-v6.md)
- [release-packaging.md](./release-packaging.md)
- [provider-canary-policy-v6.md](./provider-canary-policy-v6.md)
