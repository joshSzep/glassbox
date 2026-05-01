# V11 Dogfooding Summary

This document records the `GBX-1192` dogfooding pass for the v11
confidence-and-adoption milestone. The goal was to run ordinary local operator
flows against the v11 surfaces before publishing the release-candidate guide.

Retained local browser evidence was written under:

```text
.glassbox/releases/gbx-1192-dogfooding/
```

The evidence directory is intentionally local and uncommitted. Sanitized
results and friction findings are recorded here for review.

## Passes

| Pass | Command | Result | Notes |
| --- | --- | --- | --- |
| Release-doc and release-gate recommendation | `uv run glassbox eval recommend scripts/validate_v11_release_gate.py docs/v11-release-gate.md --json --cwd .` | Passed after fix | The first run correctly selected the `release-candidate` profile but exposed stale recipe/gate guidance for v11. The fix now emits `uv run python scripts/validate_v11_release_gate.py` as the full gate and points release-gate script recipes at the v11 dry-run. |
| Historical compaction over-range guidance | `uv run pytest tests/integration/test_cli_session_commands.py::test_cli_compact_rejects_over_cap_range_with_bounded_json_guidance -q` | `1 passed` | The seeded CLI flow exercises an over-cap range, validates JSON guidance, and proves a bounded retry can succeed without exposing the old raw artifact validation error. |
| Live dashboard cockpit evidence | `GBX_V11_LIVE_COCKPIT_EVIDENCE_DIR=.glassbox/releases/gbx-1192-dogfooding pnpm --dir frontend exec playwright test e2e/v11-live-cockpit-evidence.spec.ts --project=chromium` | `4 passed` | Retained screenshots and JSON summaries cover long-session inspection, stale verification evidence, stream reconnect/degradation, queue navigation, and historical snapshot separation. |
| Branch-search comparison with verification recommendations | `uv run pytest tests/integration/test_cli_branch_search_commands.py -q` | `3 passed` | The seeded CLI flow covers list/show, selected/rejected/needs-review candidate states, explicit no automatic merge behavior, and verification recommendation posture for existing and missing candidate evidence. |

Focused validation after the recommendation fix:

```text
uv run pytest tests/unit/test_eval_recommendations.py \
  tests/integration/test_cli_eval_commands.py::test_cli_eval_recommend_distinguishes_release_profiles_from_full_gates -q
```

Result: `14 passed`.

## Findings

### Recommendation And Release Evidence

- Fixed: `eval recommend` did not name the v11 full release gate for
  `scripts/validate_v11_release_gate.py` and `docs/v11-release-gate.md`.
- Fixed: the release-gate recipe still pointed operators at the v10 gate and
  included an invalid `--cwd` flag for Python release-gate scripts.
- Residual risk: release-gate recipe commands are still active-milestone
  guidance rather than a dynamic per-version command generator. Historical gate
  scripts remain available, but recipe copy is optimized for v11.

### Residual-Risk Closure

- Compaction over-range guidance behaved as intended in the seeded CLI flow.
  The operator-visible path now starts with bounded retry guidance instead of
  a raw artifact source-reference cap failure.
- Checkpoint absence explanation remains covered through deterministic v11
  replay evidence and focused status tests; no new dogfooding friction was
  found in this pass.

### Cockpit

- The live cockpit evidence pass completed in Chromium and retained screenshots.
- No UI overlap, reconnect, historical snapshot, or stale-verification blocker
  appeared during the automated browser scenarios.
- Scope remains bounded: this pass is Chromium/fixture-backed browser evidence,
  not broad cross-browser or screen-reader certification.

### Provider

- Live provider canaries were not run during this dogfooding pass. Provider
  evidence remains optional, advisory, and covered by the v11 gate dry-run
  provider evidence plan plus deterministic provider failure fixtures.

### Operator Flow

- The command guide and recommendation output were sufficient to choose the
  release-candidate profile as the cheapest deterministic next command.
- The stale v10 recipe guidance would have been confusing during release-gate
  work; that was fixed and covered by tests.

### Knowledge Posture

- Knowledge posture remains represented in deterministic release-candidate
  evidence through `knowledge.posture-summary` and in the dashboard live
  cockpit evidence through freshness and stale-verification scenarios.
- No additional knowledge freshness ambiguity was found during this pass.

### Branch Search

- Branch-search comparison output kept selected, rejected, and needs-review
  candidate posture separate.
- Verification recommendations remained explicit when candidate changed-file
  evidence was missing, and existing verification evidence produced
  `existing-evidence` guidance.
- No automatic merge behavior was introduced.

### Handoff

- No new handoff-specific friction was found. Reviewer evidence guidance remains
  the right path for sharing sanitized summaries instead of committing raw
  `.glassbox` state.

## Disposition

The dogfooding pass found one actionable release-recommendation defect and fixed
it during `GBX-1192`. The remaining observations are bounded evidence limits,
not release blockers:

- browser evidence is Chromium fixture-backed
- provider canaries are advisory and were skipped
- release-gate recipe guidance is active-milestone oriented rather than fully
  dynamic across historical gates
