# Glassbox v11 Residual-Risk Audit

This audit grounds the v11 confidence-and-adoption work in the current source
tree after the v10 release candidate and post-v10 refactor. It classifies each
known v10 gap as fixed in v11, evidence-only in v11, accepted non-goal, or
carried-forward risk.

Dashboard summaries, projection tables, and retained local evidence are useful
for inspection, but canonical events, typed API responses, managed artifacts,
and deterministic replay/eval contracts remain the authority for release
behavior.

## Summary

| Area | Current State | v11 Disposition |
| --- | --- | --- |
| Compaction cap handling | Artifact schema enforces a 200 source-reference cap, while normal CLI compaction can still request a larger event range before friendly range validation. | Fixed in v11 by `GBX-1110`. |
| Historical checkpoint absence | Shared status and snapshot models expose `latest_checkpoint: null` but no typed reason for expected historical/imported absence versus active recovery gaps. | Fixed in v11 by `GBX-1111`. |
| Release-path recommendations | Impact rules cover many runtime, dashboard, provider, and long-run paths but not release-gate scripts or release-candidate docs as first-class release checks. | Fixed in v11 by `GBX-1112`. |
| Live cockpit evidence | Long-run cockpit has deterministic replay/component coverage, but v10 dogfooding did not retain a live dashboard monitoring pass. | Evidence-only in v11 by `GBX-1130` through `GBX-1133`. |
| Accessibility evidence | Prior terminal/dashboard reviews name keyboard and Playwright pairings; real screen-reader pairings remain non-claims. | Evidence-only in v11 by `GBX-1132`, with targeted fixes if discovered. |
| Provider matrix partialness | Provider canary definitions include many long-work scenarios, but most remain preflight-only and live-provider evidence remains advisory. | Improved in v11 by `GBX-1140` through `GBX-1142`; provider evidence stays advisory. |
| Bounded autonomy non-goals | Budgets, checkpoints, pause windows, approvals, and local ownership intentionally prevent indefinite unattended mutation. | Accepted non-goal for v11. |
| Broad command-surface friction | `glassbox command guide` exists, but daily recovery still requires knowing which command family owns compactions, attempts, checkpoints, provider posture, and verification. | Fixed in v11 by `GBX-1150` through `GBX-1152`. |

## Detailed Audit

### Compaction Cap Handling

Disposition: fixed in v11 by `GBX-1110`.

Source links:

- `src/glassbox/runtime/context_compaction.py:83` defines
  `source_references` with `max_length=200`.
- `src/glassbox/runtime/context_compaction_service.py:62` through
  `src/glassbox/runtime/context_compaction_service.py:85` derives the selected
  source range and builds the artifact from all matching events.
- `src/glassbox/cli/compaction_commands.py:23` through
  `src/glassbox/cli/compaction_commands.py:31` forwards CLI ranges directly to
  the compaction service.
- `docs/v10-dogfooding-summary.md:34` through
  `docs/v10-dogfooding-summary.md:43` records the failed 6,208-event
  compaction and successful bounded retry.

Current test inventory:

- `tests/integration/test_cli_session_commands.py:1139` covers creating and
  listing ordinary compactions.
- `tests/integration/test_cli_session_commands.py:1200` covers refresh and
  invalidation confirmation gates.
- `evals/cases/context.compaction-provenance.json` and
  `evals/coverage.json:229` cover deterministic compaction provenance.

Missing coverage:

- no focused unit or CLI test asserts a friendly over-cap source-range error
  before Pydantic artifact validation
- no JSON error shape yet names selected count, supported cap, and bounded
  retry ranges

### Historical Checkpoint Absence

Disposition: fixed in v11 by `GBX-1111`.

Source links:

- `src/glassbox/runtime/session_query_models.py:96` through
  `src/glassbox/runtime/session_query_models.py:99` expose
  `latest_checkpoint` on session summaries without an absence reason.
- `src/glassbox/runtime/session_query_models.py:207` through
  `src/glassbox/runtime/session_query_models.py:208` expose snapshot
  checkpoint fields without differentiating historical/imported absence.
- `src/glassbox/runtime/session_query_service.py:140` through
  `src/glassbox/runtime/session_query_service.py:145` derives
  `latest_checkpoint` from checkpoint history and leaves it `None` when empty.
- `src/glassbox/cli/status_formatters.py:35` through
  `src/glassbox/cli/status_formatters.py:37` prints the latest checkpoint only
  when one exists.
- `src/glassbox/runtime/session_import.py:48` through
  `src/glassbox/runtime/session_import.py:57` records imported sessions as
  inspection-only with a checkpoint event count but no status-level absence
  reason.

Current test inventory:

- `tests/integration/test_cli_session_commands.py:1130` checks CLI output when
  a latest checkpoint exists.
- `tests/integration/test_cli_session_import.py` covers inspection-only import
  behavior and imported checkpoint counts.
- `evals/cases/long-run.recovery-boundaries.json` protects checkpoint-backed
  recovery semantics when checkpoint evidence exists.

Missing coverage:

- no typed `checkpoint_absence_reason` or equivalent field in session summary,
  snapshot, or long-run status
- no CLI/dashboard distinction among pre-checkpoint history, imported
  inspection-only sessions, projection degradation, and active long-run gaps

### Release-Path Recommendation Gap

Disposition: fixed in v11 by `GBX-1112`, then made more explainable by the
Phase 112 tasks.

Source links:

- `src/glassbox/runtime/eval_recommendation_matching.py:30` through
  `src/glassbox/runtime/eval_recommendation_matching.py:43` match paths through
  manifest rules.
- `evals/impact.json:253` through `evals/impact.json:287` route checkpoint and
  compaction work to v10 long-run cases and release profiles.
- `evals/impact.json:316` through `evals/impact.json:345` route dashboard
  cockpit work.
- `evals/impact.json:348` through `evals/impact.json:360` route provider
  readiness work to the advisory live-provider canary track.
- `docs/v10-dogfooding-summary.md:61` through
  `docs/v10-dogfooding-summary.md:70` records that release-gate editing needed
  manual validation selection.

Current test inventory:

- `tests/integration/test_cli_eval_commands.py:642` covers case/profile/reason
  recommendation behavior for matched runtime paths.
- `tests/integration/test_cli_eval_commands.py:816` covers advisory provider
  canary recommendations and skipped execution checks.
- `tests/integration/test_cli_eval_commands.py:887` covers coverage-manifest
  warning behavior.

Missing coverage:

- no impact rule currently targets `scripts/validate_v*_release_gate.py`,
  `docs/v*-release-gate.md`, `docs/v*-release-candidate.md`,
  `docs/release-packaging.md`, or package-content validation scripts as
  release-path changes
- no recommendation output distinguishes full release-gate scripts from eval
  profiles for those paths

### Live Cockpit Evidence

Disposition: evidence-only in v11 by `GBX-1130` through `GBX-1133`.

Source links:

- `evals/impact.json:316` through `evals/impact.json:345` connect long-run
  cockpit dashboard and task evidence paths to deterministic replay/profile
  recommendations.
- `tests/integration/test_web_chat_dashboard_live.py:1` through
  `tests/integration/test_web_chat_dashboard_live.py:52` provide backend live
  dashboard integration coverage for chat-owned sessions and SSE routes.
- `frontend/tests/task-autonomy-console.test.tsx:93` through
  `frontend/tests/task-autonomy-console.test.tsx:168` render queue filters,
  selected task detail, budget evidence, event history, and controls.
- `docs/v10-release-candidate.md:235` through
  `docs/v10-release-candidate.md:237` records the missing live dashboard
  monitoring dogfooding pass.

Current test inventory:

- deterministic replay cases include `long-run.cockpit-summary`,
  `verification.stale-cockpit`, `dashboard.action-approval`, and
  `dashboard.action-answer`
- frontend component tests cover task, knowledge, branch-search, workspace
  overview, and session-inspector surfaces
- backend integration tests cover dashboard routes, static assets, SSE, and
  session aggregate/snapshot APIs

Missing coverage:

- no retained v11 live-browser protocol yet names scenarios, evidence
  directory layout, environmental blockers, and non-claims
- no retained live long-session/reconnect evidence from a real dashboard run is
  committed or summarized for v11

### Accessibility Evidence

Disposition: evidence-only in v11 by `GBX-1132`; defects discovered during
pairings become targeted fixes.

Source links:

- `docs/terminal-accessibility-review-v7.md:5` through
  `docs/terminal-accessibility-review-v7.md:12` names terminal keyboard
  pairings and records VoiceOver as not executed.
- `docs/dashboard-accessibility-review-v8.md:5` through
  `docs/dashboard-accessibility-review-v8.md:13` names Chromium/Playwright
  keyboard pairings and records screen-reader/browser combinations as
  non-claims.
- `docs/dashboard-accessibility-review-v8.md:61` through
  `docs/dashboard-accessibility-review-v8.md:73` states supported claims and
  residual risks.

Current test inventory:

- terminal TUI unit and integration tests cover mount sizes, keyboard routes,
  plain fallback, and workflow commands
- frontend component and Playwright workflow tests use role/name queries for
  primary dashboard surfaces

Missing coverage:

- no v11 terminal plain-mode pairing has been retained
- no v11 dashboard keyboard pairing has been retained
- no screen-reader pairing has been executed in the current evidence set

### Provider Matrix Partialness

Disposition: improved in v11 by `GBX-1140` through `GBX-1142`; live provider
evidence remains advisory.

Source links:

- `src/glassbox/runtime/provider_canary_scenarios.py:5` through
  `src/glassbox/runtime/provider_canary_scenarios.py:21` list the default
  advisory canary scenarios.
- `src/glassbox/runtime/provider_canary_scenarios.py:23` through
  `src/glassbox/runtime/provider_canary_scenarios.py:135` show that most
  scenarios beyond `streaming-text` are currently `preflight_only`.
- `src/glassbox/runtime/provider_recommendation_capability.py:17` through
  `src/glassbox/runtime/provider_recommendation_capability.py:46` map task
  kinds to expected provider scenarios.
- `src/glassbox/runtime/provider_recommendation_capability.py:182` through
  `src/glassbox/runtime/provider_recommendation_capability.py:206` derives
  supported, partial, unknown, or insufficient capability fit.

Current test inventory:

- `tests/integration/test_provider_mode_runtime.py` covers provider
  diagnostics, recommendation CLI output, fake-provider canary execution, and
  advisory posture
- `tests/integration/test_cli_eval_commands.py:816` covers live-provider
  canary recommendation as explicit-selection advisory evidence

Missing coverage:

- no deterministic fixtures yet model retryable provider error, non-retryable
  provider error, lost stream, malformed tool call, stale canary evidence, and
  model fallback recommendation as a complete fixture set
- no v11 gate stage yet summarizes optional provider evidence alongside
  skipped scenario reasons

### Bounded Autonomy Non-Goals

Disposition: accepted non-goal for v11.

Source links:

- `docs/v10-long-running-task-contract.md:31` through
  `docs/v10-long-running-task-contract.md:46` defines long work as observable,
  bounded, interruptible, and recoverable rather than automatic.
- `docs/v10-long-running-task-contract.md:168` through
  `docs/v10-long-running-task-contract.md:218` defines time-aware budgets and
  continuation windows.
- `docs/v11-confidence-adoption-contract.md:29` through
  `docs/v11-confidence-adoption-contract.md:43` names v11 non-goals including
  hosted orchestration, simultaneous multi-writer mutation, and indefinite
  unattended operation.

Current test inventory:

- budget, continuation-window, pause-window, background-job, and cancellation
  tests protect bounded continuation behavior
- deterministic evals include budget exhaustion, continuation-blocked, and
  long-run recovery cases

Missing coverage:

- none required for the non-goal itself in `GBX-1101`; later v11 tasks must not
  weaken these boundaries while improving inspection and recovery copy

### Broad Command-Surface Friction

Disposition: fixed in v11 by `GBX-1150` through `GBX-1152`.

Source links:

- `src/glassbox/cli/command_guide.py:31` through
  `src/glassbox/cli/command_guide.py:216` defines the current workflow-oriented
  guide.
- `src/glassbox/cli/status_formatters.py:348` through
  `src/glassbox/cli/status_formatters.py:394` already adds safe inspection
  guidance for stale compactions, failed/stale attempts, and recovery posture.
- `docs/v10-dogfooding-summary.md:100` through
  `docs/v10-dogfooding-summary.md:112` records that the command surface is
  powerful but broad and that the dogfooding story still required manual
  grouping.

Current test inventory:

- `tests/integration/test_cli_entrypoint.py` covers command-guide discovery
  output
- CLI session, task, memory, repository, branch-search, provider, observability,
  and eval command tests cover individual command families

Missing coverage:

- command guide sections do not yet explicitly group long-run recovery,
  checkpoint inspection, compaction, tool attempts, verification
  recommendations, provider posture, knowledge freshness, branch-search review,
  and handoff into daily recovery workflows
- status commands do not yet summarize all safe related inspection commands as
  launch pads

## Follow-Up Contract

Each fixed-in-v11 disposition should land with focused implementation tests and
docs updates in its own task commit. Evidence-only dispositions should produce
retained protocols or summaries before expanding public claims. Accepted
non-goals should remain explicit in release-candidate docs so confidence work
does not silently become broader autonomy.
