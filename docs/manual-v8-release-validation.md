# v8 Manual Release Validation

This document records the `GBX-894` manual validation pass for the v8 release-candidate track. The retained local evidence directory for this pass is:

```text
.glassbox/releases/gbx-894-manual-evidence/
```

The directory is local workspace state and is intentionally not committed. It contains recovery evidence such as backup archives and restore smoke output. This pass also references earlier retained v8 evidence from:

```text
.glassbox/releases/gbx-893-v8-gate-dry-run/summary.json
.glassbox/releases/gbx-893-v8-gate/background-jobs/summary.json
.glassbox/releases/gbx-892-installed-smoke/summary.json
.glassbox/releases/gbx-891-recovery/
```

## Commands Run

Automated v8 gate dry run:

```bash
uv run python scripts/validate_v8_release_gate.py \
  --dry-run \
  --evidence-dir .glassbox/releases/gbx-893-v8-gate-dry-run
```

Result: passed. The dry run planned v7 release stages plus v8 autonomy stages, recorded explicit provider-canary skip policy, and retained `summary.json`.

Focused v8 autonomy evidence from `GBX-893`:

```bash
uv run glassbox eval report commit-smoke push-confirmation release-candidate \
  --output-dir .glassbox/evals/gbx-893-v8-release-signoff \
  --cwd .

uv run glassbox eval run \
  --profile v8-autonomy-advisory \
  --output-dir .glassbox/evals/gbx-893-v8-autonomy \
  --refresh-output-dir \
  --cwd .

uv run glassbox eval audit --cwd .

uv run python scripts/background_autonomy_smoke.py \
  --evidence-dir .glassbox/releases/gbx-893-v8-gate/background-jobs \
  --json
```

Result: deterministic eval report, v8 autonomy advisory eval, coverage audit, and six background-job smoke scenarios passed.

Focused dashboard review:

```bash
pnpm --dir frontend exec vitest run \
  tests/task-autonomy-console.test.tsx \
  tests/knowledge-autonomy-console.test.tsx \
  tests/branch-search-console.test.tsx
```

Result: `7` Vitest tests passed across task, memory/index, and branch-search autonomy console surfaces.

The targeted Playwright rerun was attempted with:

```bash
pnpm --dir frontend exec playwright test e2e/operator-workflows.spec.ts \
  -g "task controls|memory and repository|branch-search candidate"
```

Result: blocked before test execution by local Next.js dev-server watcher exhaustion: `EMFILE: too many open files, watch`. No additional Playwright claim is made from this pass; the existing `GBX-886` Chromium/Playwright evidence remains the retained dashboard accessibility source.

Provider recommendation review:

```bash
uv run glassbox provider recommend \
  --task-kind release \
  --autonomy-mode release-candidate \
  --model-name openai:gpt-5.4 \
  --cwd . \
  --json
```

Result: command completed and returned a `risky` posture with `low` confidence. The recommendation stayed advisory because relevant provider-canary evidence was stale, incompatible, or missing for this workflow.

Recovery and maintenance review:

```bash
uv run glassbox projection check --all --cwd .
uv run glassbox artifacts inspect --cwd . --json
uv run glassbox repo index build --json --cwd .
uv run glassbox backup create \
  .glassbox/releases/gbx-894-manual-evidence/recovery/workspace-backup.zip \
  --cwd . \
  --json
uv run glassbox backup inspect \
  .glassbox/releases/gbx-894-manual-evidence/recovery/workspace-backup.zip \
  --cwd . \
  --json
uv run glassbox backup restore \
  /Users/joshszep/code/glassbox/.glassbox/releases/gbx-894-manual-evidence/recovery/workspace-backup.zip \
  --cwd /private/tmp/glassbox-gbx-894-restore \
  --json
```

Result: projection check reported `23` ok and `0` degraded. Artifact inspection reported `58` orphan candidates, `333452` candidate bytes, no missing references, and no storage warning. Repository index rebuild completed with a fresh status and source digest. Backup create and inspect succeeded with `944` files and `943` artifacts; absolute-path restore into `/private/tmp/glassbox-gbx-894-restore` succeeded. A first restore attempt using a relative archive path failed because restore resolves the archive path relative to the target `--cwd`; future cross-workspace restore commands should use an absolute archive path.

Package smoke:

```bash
uv build --wheel --sdist
uv run python scripts/validate_package_contents.py
uv run python scripts/validate_installed_wheel_smoke.py \
  --wheel dist/glassbox-0.1.0-py3-none-any.whl \
  --evidence-dir .glassbox/releases/gbx-892-installed-smoke
```

Result: package build, content validation, and installed-wheel smoke passed in `GBX-892`.

## Autonomy Workflow Checklist

| Workflow | Status | Evidence |
| --- | --- | --- |
| Terminal task planning | Reviewed | Task CLI smoke and v8 eval cases cover durable plan capture and task listing. |
| Dashboard plan inspection | Reviewed | `GBX-886` dashboard review plus `GBX-894` Vitest task console pass. |
| Background continuation | Reviewed | `GBX-893` background autonomy smoke passed six scenarios. |
| Pause/resume/cancel | Reviewed | Task and job controls are covered by dashboard tests, runtime tests, and background-job smoke; no new manual terminal recording was created in this pass. |
| Budget exhaustion | Reviewed | Deterministic eval case and gate membership cover budget exhaustion; dashboard controls remained under `GBX-886` evidence. |
| Memory confirmation/invalidation | Reviewed | Memory CLI smoke, recovery review, and dashboard memory inspector tests passed. |
| Repository index rebuild | Reviewed | `glassbox repo index build --json --cwd .` completed with a fresh index. |
| Verify-repair loop | Reviewed | Deterministic success and failure eval cases passed through release-signoff report evidence. |
| Branch-search comparison | Reviewed | Branch-search CLI smoke and dashboard branch-search comparison tests passed. |
| Provider recommendation | Reviewed | Command completed with advisory `risky` and `low` confidence posture. |
| Package smoke | Reviewed | Build, content validation, and installed-wheel smoke passed in retained `GBX-892` evidence. |

## Terminal Review

| Area | Result | Notes |
| --- | --- | --- |
| Supported TTY | Covered by prior TUI test harness and installed CLI smoke | No new terminal recording was created in this pass. |
| Plain fallback | Covered by existing terminal release contract | No regression was introduced by the doc-only GBX-894 changes. |
| Long task output | Covered by deterministic eval/report evidence | Human review remains recommended before final publication if a candidate has unusually large transcripts. |
| Approvals/questions | Covered by existing TUI workflow tests and provider-canary advisory preflight rows | Live provider approval behavior remains advisory. |
| Cancellation | Covered by v8 task/job controls and background smoke | Operator-visible cancellation cues remain part of dashboard and terminal release checks. |
| Daemon attach | Covered by existing daemon/TUI release evidence | No new daemon attach transcript was added. |
| Background job cues | Covered by background autonomy smoke and observability status | Job list and observability cues are scriptable and retained as JSON evidence. |

## Dashboard Review

| Area | Result | Notes |
| --- | --- | --- |
| Task console and plan inspection | Passed focused Vitest; inherited Playwright evidence from `GBX-886` | Targeted Playwright rerun hit local `EMFILE` before tests. |
| Budget controls | Inherited `GBX-886` accessibility evidence | Claims are limited to named Chromium/Playwright keyboard paths. |
| Memory/index inspectors | Passed focused Vitest | Memory search, detail provenance, confirmation, invalidation, index status, search, and rebuild controls remain covered. |
| Branch comparison | Passed focused Vitest | Branch-search candidate select/review/reject controls remain accessible-name tested. |
| Evidence pane | Covered by `GBX-886` named region and evidence cue review | No new screenshot archive was added in this pass. |
| Mobile | Inherited `GBX-886` mobile keyboard pairing | No additional mobile run was completed in `GBX-894`. |
| Keyboard and accessibility | Named pairings retained in [dashboard-accessibility-review-v8.md](./dashboard-accessibility-review-v8.md) | VoiceOver, NVDA, Narrator, Orca, Safari, and Firefox remain non-claims. |

## Recovery Review

| Area | Result | Notes |
| --- | --- | --- |
| Failed jobs | Reviewed | Observability and job-list smoke expose failed and retryable jobs. |
| Stale daemon | Reviewed | Recovery guidance remains explicit: inspect status, stop stale owner, restart. |
| Stale index | Reviewed | Fresh repository index rebuild succeeded. |
| Invalid memory | Reviewed | Memory invalidation and prune guidance remain covered by `GBX-891`. |
| Failed verification | Reviewed | Verify-repair success and failure eval cases are in release-signoff evidence. |
| Projection rebuild/check | Passed | Projection check reported `23` ok and `0` degraded. |
| Artifact pressure | Reviewed | Artifact inspection found reclaimable candidates but no storage warning or missing refs. |
| Backup/restore | Passed with operator note | Absolute archive restore succeeded; relative archive restore into a different `--cwd` failed by path resolution. |

## Residual Risks

- Targeted Playwright rerun for `GBX-894` was blocked by local watcher `EMFILE` before tests executed. Existing `GBX-886` Playwright evidence remains valid, but the final release-candidate pass should rerun the targeted workflow with a healthier file-descriptor limit or a production server path.
- Screen reader pairings were not executed. This pass makes no screen-reader claim beyond keyboard, role/name, and semantics evidence from the named Chromium/Playwright pairings.
- Provider recommendation is advisory with `risky` posture and `low` confidence because relevant live-provider canary evidence is stale, incompatible, or missing.
- The full v8 release gate was not run in `GBX-894`; dry run, v8-specific real stages, package smoke, and manual recovery checks passed. `GBX-895` should run the full gate before a final release decision.

## Recommendation

Provisional go for continuing to the v8 release-candidate guide. Do not publish the final release-candidate decision until `GBX-895` runs the full v8 gate, records the final `summary.json`, and explicitly accepts or closes the residual risks above.

Use [manual-qa-evidence-v8.md](./manual-qa-evidence-v8.md) for future v8 manual validation manifests and redaction rules.
