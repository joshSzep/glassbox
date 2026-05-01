# Glassbox v11 Confidence And Adoption Contract

This page defines the v11 product contract for turning the completed v10
long-running-task release candidate into the `0.10.0` confidence and adoption
milestone.

v11 starts from the v9 public baseline and the v10 long-running-task contract.
The v11 goal is not a new autonomy tier. The goal is to make the v8 through
v10 power easier to trust, inspect, verify, and hand off in ordinary local use.

## Scope

Glassbox v11 focuses on confidence, evidence, and operator flow polish:

- close the accepted v10 residual risks with focused fixes, stronger retained
  evidence, or explicit carry-forward decisions
- make change-aware verification recommendations explainable enough for
  contributors to trust
- turn deterministic long-run cockpit coverage into repeatable live-browser
  evidence where the local environment permits it
- mature provider recovery with deterministic failure fixtures while keeping
  live providers advisory
- compress daily recovery and verification flows so operators need less command
  memorization
- unify freshness cues across repository index, workspace memory, compactions,
  checkpoints, verification, and provider evidence
- strengthen branch-search decision support without automatic merging
- align the public package line and release policy on version `0.10.0`

The v11 package target is `0.10.0`. Until the dedicated version-alignment task
updates metadata and installed smoke, historical v9 and v10 documents keep the
version strings and evidence paths that were true for those milestones.

## Non-Goals

v11 does not introduce hosted orchestration, cloud workspace authority, remote
worker fleets, simultaneous multi-writer mutation, indefinite unattended
operation, hidden provider memory, browser-native code editing as a replacement
for local tools, live-provider release authority, or automatic branch-search
merging.

Provider canaries, live browser runs, and accessibility pairings can improve
confidence only when retained evidence names the exact workflow and
environment. Deterministic replay, eval, package, and release-gate evidence
remain the blocking release authority unless a future task promotes a narrow
fixture-backed contract with an explicit failure policy.

## Supported Workflow Set

v11 supports these operator workflows:

- inspect confidence posture from the terminal and dashboard before continuing
  or handing off local work
- ask `glassbox eval recommend` for explainable verification and release-gate
  recommendations for changed paths
- compact historical or long-running sessions with bounded-range guidance when
  a requested source range is too large for the artifact contract
- understand missing checkpoints as an explicit historical, imported,
  degraded, or active-recovery state
- collect live cockpit evidence for long-running dashboard states without
  making browser evidence the only release authority
- inspect provider recovery recommendations with deterministic failure-fixture
  coverage and freshness labels for live canary evidence
- use workflow-oriented command guidance for recovery, verification, provider
  posture, knowledge freshness, branch-search review, and handoff
- compare branch-search candidates by evidence, verification posture, cost,
  risk, accepted risks, and recommended follow-up action
- prepare local-first handoff and reviewer evidence bundles without changing
  workspace custody or adding remote authority

The daily discovery commands remain:

```bash
uv run glassbox command guide
uv run glassbox command tree
uv run glassbox readiness check --cwd .
uv run glassbox session chat --cwd .
uv run glassbox session status SESSION_ID --cwd .
uv run glassbox observability status --cwd . --json
uv run glassbox eval recommend PATH --cwd .
uv run glassbox eval report commit-smoke push-confirmation release-candidate --cwd .
```

## Evidence Expectations

v11 evidence is split into blocking deterministic evidence and advisory
confidence evidence.

Blocking release evidence includes:

- deterministic replay and eval cases promoted into the release-candidate
  profile
- focused unit and integration tests for changed runtime, CLI, store, web, eval,
  provider, verification, branch-search, and dashboard behavior
- package contents validation, installed-wheel smoke, and `glassbox --version`
  evidence for `0.10.0`
- the v11 release gate summary once `scripts/validate_v11_release_gate.py`
  exists

Advisory confidence evidence includes:

- live dashboard screenshots or browser logs retained under `.glassbox/releases/`
- provider canary evidence, freshness summaries, and skipped-scenario reasons
- named accessibility pairings for terminal, dashboard, keyboard, plain-mode,
  and screen-reader workflows where the local environment permits them
- dogfooding summaries from real local operator work

Manual and advisory evidence must name non-claims. A passing browser run does
not replace deterministic cockpit fixtures, a fresh provider canary does not
make provider behavior release authority, and a named accessibility pairing
does not imply broad certification.

## V10 Residual-Risk Mapping

| v10 Finding | v11 Disposition |
| --- | --- |
| Large full-session compactions can expose a raw source-reference cap validation error. | Fixed by `GBX-1110` with friendly bounded-range guardrails and tests. |
| Historical or imported sessions can show no latest checkpoint without explaining whether absence is expected. | Fixed by `GBX-1111` with typed checkpoint-absence reasons in CLI, API, and dashboard surfaces. |
| Release-gate scripts and release-candidate docs are not confidently routed by `glassbox eval recommend`. | Fixed by `GBX-1112`, then made explainable and promoted through `GBX-1120` through `GBX-1122`. |
| Long-run cockpit behavior has deterministic coverage but lacks retained live dashboard monitoring evidence. | Evidence-only in `GBX-1130` through `GBX-1133`; deterministic replay and component tests remain release authority. |
| Screen-reader pairings were not executed for v10. | Evidence-only plus targeted fixes in `GBX-1132`; no broad accessibility certification is claimed. |
| Provider canary evidence is partial for release-candidate and long-running work. | Improved by `GBX-1140` through `GBX-1142`; provider evidence remains advisory and freshness-labeled. |
| The command surface is broad and ordinary recovery requires command-family knowledge. | Fixed by `GBX-1150` through `GBX-1152` with workflow-oriented command guidance and safe status summaries. |
| Repository index, memory, compaction, checkpoint, verification, and provider freshness cues are separate mental models. | Fixed by `GBX-1160` through `GBX-1162` with a unified knowledge posture and provenance drill-down. |
| Branch search compares candidates but gives limited decision support around evidence, cost, risk, and follow-up verification. | Fixed by `GBX-1170` through `GBX-1172` without automatic parent mutation or merge behavior. |
| Local team handoff still requires reconstructing the story from raw state. | Fixed by `GBX-1180` through `GBX-1182` with handoff summaries, profile templates, and reviewer evidence guidance. |
| Long-running work remains bounded local continuation, not indefinite unattended operation. | Accepted non-goal for v11; autonomy boundaries, approvals, budgets, checkpoints, and local mutation ownership remain part of the product contract. |

## Pass And Fail Policy

A v11 release-candidate build is blocked by failing deterministic tests, promoted
eval cases, package validation, installed smoke, release-gate stages, or
documented package-version alignment. It is not blocked by missing optional live
provider credentials, unavailable screen-reader tooling, or local browser
environment issues when the release guide records the skip or blocker honestly
and keeps the claim bounded.

Residual risks stay visible until they are fixed, backed by retained evidence,
accepted as non-goals, or carried forward into a later task graph.

## Related Documents

- [tasks-v11.md](./tasks-v11.md): v11 task graph and dependency order
- [v10-release-candidate.md](./v10-release-candidate.md): inherited v10 release
  posture and residual risks
- [v10-dogfooding-summary.md](./v10-dogfooding-summary.md): real-use findings
  that seed the first v11 implementation slices
- [version-release-policy.md](./version-release-policy.md): package and
  release-candidate naming policy
