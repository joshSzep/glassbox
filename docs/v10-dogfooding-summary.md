# v10 Dogfooding Summary

This document records the sanitized GBX-1092 dogfooding pass for the v10
long-running-task reliability milestone. Raw local evidence remains outside the
repository. The committed material below keeps only workflow shape, command
families, pass/fail posture, friction summaries, and candidate follow-up
dispositions.

Dogfooding evidence is advisory product evidence. Deterministic replay, eval,
package, and release-gate evidence remain the blocking release authority.

## Passes

| Pass | Workflow | Evidence Retention | Outcome |
| --- | --- | --- | --- |
| `20260430-1325-long-repo-compaction-review` | Long repository inspection with compaction and checkpoint review | Local session/projection evidence retained in `.glassbox`; committed summary below is sanitized | Completed with compaction follow-up |
| `20260430-1345-release-gate-code-edit` | Multi-step release-gate code edit with incremental verification and recovery | Commit `62f13a6`; local gate evidence retained outside the repository | Completed and committed |
| `20260430-1425-background-continuation-recovery` | Interrupted daemon/background continuation with retry and abandon evidence | Local background smoke evidence retained outside the repository | Completed with no blocking follow-up |

## Pass Details

### Long Repository Compaction Review

- Repository alias: `repo-alpha`
- Repository type: local Python/TypeScript CLI and dashboard repository
- Provider posture: `provider-present-redacted`
- Dashboard used: not required for this pass
- Terminal used: yes
- Commands:
  - `glassbox session list --cwd . --json`
  - `glassbox session compact SESSION_ID --scope transcript --source-start-sequence 1 --source-end-sequence 6208 --cwd . --json`
  - `glassbox session compact SESSION_ID --scope transcript --source-start-sequence 6009 --source-end-sequence 6208 --cwd . --json`
  - `glassbox session compactions SESSION_ID --cwd . --json --limit 3`
- Result:
  - The full-session compaction attempt failed because the artifact schema
    rejected 6,208 source references against the 200-reference cap.
  - A bounded 200-event transcript compaction succeeded and remained listed as
    fresh with an explicit limitation that raw transcript and artifact bodies
    remain source evidence.
  - Checkpoint review showed no latest checkpoint for the selected historical
    inspection session, so the operator had to infer that recovery posture from
    the session summary rather than a checkpoint-specific surface.

### Release-Gate Code Edit

- Repository alias: `repo-alpha`
- Repository type: local Python/TypeScript CLI and dashboard repository
- Provider posture: `provider-present-redacted`
- Dashboard used: not required for this pass
- Terminal used: yes
- Commands:
  - `ruff format` and `ruff check` on touched Python release-gate files
  - `ty check` on touched Python release-gate files
  - `pytest tests/unit/test_v10_release_gate.py tests/unit/test_packaging_metadata.py`
  - `python scripts/validate_v10_release_gate.py --dry-run --evidence-dir ...`
  - `python scripts/validate_v10_release_gate.py --evidence-dir ...`
  - `glassbox eval recommend scripts/validate_v10_release_gate.py docs/v10-release-gate.md tests/unit/test_v10_release_gate.py --cwd . --json`
- Result:
  - The edit involved a real lint recovery loop: initial release-gate tests had
    import-order and line-length problems, which were fixed before the focused
    suite passed.
  - The v10 dry-run gate wrote an explicit summary with 46 planned stages and a
    provider-canary skip reason.
  - The real v10 gate passed with 69 passed stages, installed wheel smoke, v10
    long-run release profile, checkpoint/compaction smoke, tool-attempt
    recovery smoke, cockpit smoke, and provider recovery policy output.
  - `eval recommend` had no confident rule for release-gate scripts or release
    gate docs, so the operator had to choose validation manually.

### Background Continuation Recovery

- Repository alias: `repo-alpha`
- Repository type: local Python/TypeScript CLI and dashboard repository
- Provider posture: deterministic local smoke
- Dashboard used: not required for this pass
- Terminal used: yes
- Commands:
  - `python scripts/background_autonomy_smoke.py --evidence-dir ... --json`
- Result:
  - The smoke passed `read_only_completion`, `cancellation_acknowledgement`,
    `failure_retry_and_abandon`, `stale_owner_cleanup`,
    `task_continuation_budget_pause`, and `retained_projection_snapshot`.
  - The retained projection snapshot included completed, stale, abandoned, and
    cancelled job states, which covered the interrupted/background recovery
    requirement without live provider dependency.
  - The smoke exposed strong machine-readable evidence, but the high-level
    dogfooding story still needed manual grouping by task phase and operator
    question.

## Findings

| Area | Finding | Evidence | Severity | Disposition |
| --- | --- | --- | --- | --- |
| checkpoint | Historical long sessions can show `latest_checkpoint: null`; checkpoint absence is visible, but the operator must infer whether that is expected for older sessions. | Long repository compaction review | medium | Accepted residual risk for v10; keep checkpoint absence explicit in release-candidate residual risks |
| compaction | Full-session compaction can fail with a raw schema validation error when the requested source range exceeds the artifact source-reference cap. | Failed 6,208-event compaction attempt | medium | Candidate eval/test: add a bounded-range guidance check or CLI error test after v10 signoff |
| compaction | Bounded compaction recovers cleanly and records limitations, freshness, source range, and artifact linkage. | Successful 200-event compaction | low | Covered by existing deterministic compaction provenance eval |
| tool attempt | Tool-attempt recovery remains well covered by deterministic eval and gate smoke, but dogfooding did not add a new real partial-output failure beyond the fixture. | Release-gate v10 tool-attempt smoke | low | Accepted residual risk; retain fixture-backed release authority |
| dashboard cockpit | Cockpit behavior is release-gate covered through replay, but these dogfooding passes did not require live dashboard monitoring. | Release-gate cockpit smoke | medium | Carry into release-candidate guide as manual evidence gap, not a blocking automated gap |
| provider recovery | Provider recommendation now reports failure posture and budget impact, but live provider canary coverage remains partial and advisory. | Provider recovery policy output during v10 gate | medium | Accepted residual risk; deterministic release evidence remains authoritative |
| verification | The release-gate edit needed manual validation selection because eval recommendation did not match release-gate scripts/docs. | `eval recommend` returned no confident matches | medium | Candidate eval/test or impact-rule update for release-gate and release-doc paths |
| memory | Repository index was stale during release-gate observability output; the next action was clear, and dogfooding did not require memory mutation. | Observability status during v10 gate | low | Accepted residual risk with existing next-action guidance |
| release evidence | The real v10 gate gave a useful summary, but the inherited gate output is verbose and buries the final summary after many command logs. | Real v10 gate output | low | Docs note only; keep concise `summary.json` as the reviewer surface |

## Candidate Follow-Ups

- Add a focused test or CLI guard for compaction requests whose source range
  would exceed the source-reference cap, returning a bounded-range next action
  instead of a raw validation error.
- Add eval recommendation routing for `scripts/validate_v*_release_gate.py`,
  `docs/v*-release-gate.md`, and `docs/v*-release-candidate.md` paths.
- Mention in the v10 release-candidate guide that checkpoint absence on
  imported or pre-checkpoint-era sessions is visible but may remain an accepted
  historical-session limitation.
- Keep live-provider recovery evidence advisory until repeated provider failure
  modes are fixture-backed or covered by stable canaries.

## Release Use

For v10 signoff, use this summary beside:

- `scripts/validate_v10_release_gate.py`
- `docs/v10-release-gate.md`
- `evals/cases/long-run.recovery-boundaries.json`
- `evals/cases/context.compaction-provenance.json`
- `evals/cases/tool-attempt.partial-retry.json`
- `evals/cases/verification.stale-cockpit.json`
- `evals/cases/long-run.cockpit-summary.json`
