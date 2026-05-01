# Glassbox v11 Release Candidate

This page is the operator and contributor guide for the Glassbox v11
release-candidate track. It names the supported `0.10.0` confidence-and-adoption
operating model, validation path, evidence expectations, non-goals, residual
risks, and release decision without requiring readers to inspect the task graph.

## Release Posture

Glassbox v11 keeps the v10 long-running-task model and focuses on making that
power dependable in daily local use. The release track emphasizes residual-risk
closure, trustworthy verification recommendations, retained live cockpit
evidence, provider recovery maturity, command-flow compression, unified
knowledge posture, branch-search decision support, reviewer-safe handoff
evidence, and deterministic release authority for the stable confidence
contracts.

The package version for this line is `0.10.0`.

The primary product shape is:

- terminal chat remains the primary operator surface
- the dashboard remains the paired local cockpit and evidence surface
- SQLite canonical events remain the source of truth
- one local mutation owner controls a workspace at a time
- deterministic replay and eval evidence remain release authority
- live dashboard, provider, accessibility, and dogfooding evidence strengthen
  confidence but do not replace deterministic gates
- provider diagnostics, canaries, and recommendations remain advisory unless a
  future task promotes repeatable fixture-backed behavior
- branch-search compares candidates and recommends verification without
  automatically merging into parent history
- v11 is local-first agent work, not hosted orchestration or indefinite
  unattended autonomy

Use these discovery commands:

```bash
uv run glassbox command guide
uv run glassbox command tree
```

The v11 automated release-candidate gate is:

```bash
uv run python scripts/validate_v11_release_gate.py
```

For a non-mutating preview:

```bash
uv run python scripts/validate_v11_release_gate.py --dry-run
```

The retained evidence directory used for the current release-candidate pass is:

```text
.glassbox/releases/gbx-1193-v11-release-candidate/
```

The v11 eval artifacts for that candidate are retained under:

```text
.glassbox/evals/gbx-1193-v11-release-candidate/
```

Focused dogfooding evidence is summarized in
[v11-dogfooding-summary.md](./v11-dogfooding-summary.md). Local `.glassbox/`
evidence is workspace state and is not committed to git.

## Supported Operating Model

- **Verification recommendations**: `glassbox eval recommend` explains direct
  path, owner, capability, stage, release-gate, and fallback reasons, then names
  the cheapest deterministic next command before broader release checks.
- **Verification recipes**: repository-owned recipes describe common docs,
  release, frontend, runtime, store, provider, and packaging validation paths
  without auto-running arbitrary commands.
- **Compaction guardrails**: over-cap compaction ranges return bounded retry
  guidance before artifact schema validation.
- **Checkpoint absence**: historical and imported sessions can explain why no
  checkpoint exists instead of forcing operators to infer whether absence is
  expected.
- **Knowledge posture**: memory, repository index, checkpoints, compactions,
  verification, and advisory provider evidence are summarized as one local
  freshness posture with provenance drill-down.
- **Branch-search decision support**: candidate comparison includes objective,
  evidence, changed files when retained, verification posture, risk, cost,
  accepted risks, follow-up action, and verification recommendations.
- **Provider recovery maturity**: deterministic provider failure fixtures and
  capability matrix guidance improve recommendations while live canaries remain
  optional advisory evidence.
- **Live cockpit evidence**: retained Chromium evidence covers long-session
  inspection, stale verification, stream reconnect, queue navigation, and
  historical snapshots. It does not claim broad cross-browser behavior.
- **Accessibility evidence**: named terminal and dashboard keyboard/plain-mode
  pairings are retained. Broad assistive-technology certification is not
  claimed.
- **Reviewer evidence**: handoff summaries, eval reports, replay bundles,
  release summaries, and sanitized manual evidence are reviewer-safe surfaces;
  raw `.glassbox` state remains local unless explicitly sanitized.

## Primary Operator Flows

### Verify A Change Set

```bash
uv run glassbox eval recommend PATH [PATH ...] --cwd .
uv run glassbox eval run --profile commit-smoke --cwd .
uv run glassbox eval run --profile release-candidate --cwd .
uv run glassbox eval report commit-smoke push-confirmation release-candidate --cwd .
```

Release-gate scripts and release-candidate docs should recommend the
`release-candidate` profile and separately name the full v11 gate:

```bash
uv run python scripts/validate_v11_release_gate.py
```

### Inspect Knowledge Freshness

```bash
uv run glassbox observability status --cwd . --json
uv run glassbox memory list --cwd . --json
uv run glassbox repo index status --cwd . --json
uv run glassbox session compactions SESSION_ID --cwd . --json
uv run glassbox provider canary evidence --cwd . --json
```

Provider freshness is advisory. Canonical events, projections, and retained
local artifacts remain the basis for deterministic continuation decisions.

### Compare Branch Candidates

```bash
uv run glassbox branch-search start SESSION_ID \
  --objective "Compare repair approaches" \
  --strategy "minimal fix" \
  --strategy "broader refactor" \
  --cwd .
uv run glassbox branch-search show SEARCH_ID --cwd . --json
```

Selection is an operator decision. Branch search does not automatically merge
candidate work or mutate parent history.

### Prepare Handoff Or Review Evidence

```bash
uv run glassbox session export SESSION_ID --cwd .
uv run glassbox eval report commit-smoke push-confirmation release-candidate --cwd .
uv run glassbox replay bundle inspect evals/bundles/CASE_ID.json --cwd .
```

Use [reviewer-evidence-bundles.md](./reviewer-evidence-bundles.md) before
sharing local evidence.

## Release-Readiness Checklist

Before treating a build as the v11 release candidate, complete this list:

- `pyproject.toml`, `src/glassbox/__init__.py`, installed smoke, and docs agree
  on package version `0.10.0`.
- `uv run python scripts/validate_v11_release_gate.py` passes and writes
  `summary.json` with `blocking` and `advisory` sections.
- The deterministic `release-candidate` eval profile passes with v8 autonomy,
  v10 long-run, and v11 confidence fixtures.
- `glassbox eval audit --profile release-candidate --cwd .` reports no
  uncovered release-candidate capabilities.
- Release-path recommendations name both the deterministic
  `release-candidate` profile and the full v11 release gate.
- Compaction over-range guidance and checkpoint absence explanation are covered
  by tests and deterministic eval evidence.
- Knowledge posture is visible in CLI/API/dashboard paths with provenance and
  safe next actions.
- Branch-search decision support includes verification guidance and keeps
  automatic merge behavior out of scope.
- Live cockpit evidence is retained under a v11 evidence directory with
  explicit browser/environment bounds.
- Accessibility pairings and non-claims are recorded.
- Provider canaries are either retained as advisory evidence or explicitly
  skipped with structured reasons.
- Dogfooding findings have dispositions as fixes, docs, tests/evals, accepted
  risks, or post-v11 follow-ups.
- Raw `.glassbox` state is not committed; reviewer-safe summaries are used for
  handoff and release review.

## Current Evidence Summary

The current retained v11 evidence shows:

- non-dry-run v11 gate: passed for `GBX-1193`, with final evidence retained at
  `.glassbox/releases/gbx-1193-v11-release-candidate/summary.json`
- v11 gate dry run: passed during `GBX-1191`, including explicit blocking and
  advisory summary shape
- package version metadata: `glassbox 0.10.0` is covered by import and CLI
  entrypoint tests
- package contents validation: wheel and sdist include v11 docs, eval fixtures,
  release scripts, generated API files, and dashboard static assets
- release-candidate eval profile: `18/18` cases passed, including the v11
  recommendation, compaction guidance, checkpoint absence, knowledge posture,
  and branch-search decision-support fixtures
- release eval report: `commit-smoke`, `push-confirmation`, and
  `release-candidate` profiles passed with `23/23` capabilities covered
- live cockpit evidence: Chromium fixture-backed Playwright scenarios passed
  and retained screenshots under `.glassbox/releases/gbx-1192-dogfooding/`
- accessibility evidence: named terminal and dashboard pairings are summarized
  in [accessibility-review-v11.md](./accessibility-review-v11.md)
- dogfooding: findings and the recommendation fix are triaged in
  [v11-dogfooding-summary.md](./v11-dogfooding-summary.md)
- provider evidence: optional and advisory; deterministic release authority
  does not require live credentials

## Known Residual Risks

- Live cockpit evidence is Chromium and fixture-backed. It does not prove
  cross-browser behavior or every live daemon timing path.
- Screen-reader coverage remains bounded to the local environment and named
  pairings in the accessibility review; broad accessibility certification is
  not claimed.
- Provider canary evidence is advisory and may be skipped when credentials are
  unavailable. Provider behavior does not replace deterministic release
  evidence.
- Release-gate recipe guidance is active-milestone oriented. Historical gates
  remain available, but recipe commands favor the v11 path.
- Knowledge posture summarizes local freshness, but operators must still inspect
  source artifacts and canonical events before mutating recovery.
- Branch-search verification recommendations depend on retained changed-file
  evidence when available; missing diff inventories are surfaced as accepted
  review risk.
- Long-running work remains bounded local continuation, not indefinite
  unattended operation.

## Deliberate Non-Goals

v11 does not introduce a hosted control plane, cloud authority for workspace
ownership, remote multi-user orchestration, simultaneous multi-writer mutation,
distributed worker fleets, hidden provider-side memory, browser-native code
editing as a local-tool replacement, automatic provider failover as a release
claim, automatic branch merging, or indefinite unattended autonomy.

## Release Decision

Decision: GO for v11 release candidate publication.

Decision date: 2026-05-01.

Candidate build reviewed: `GBX-1193` release-candidate working tree with final
v11 gate evidence retained locally.

Retained evidence:

```text
.glassbox/releases/gbx-1193-v11-release-candidate/
.glassbox/evals/gbx-1193-v11-release-candidate/
.glassbox/releases/gbx-1192-dogfooding/
```

Final pass/fail state:

| Area | State | Evidence |
| --- | --- | --- |
| Automated v11 gate | passed | `.glassbox/releases/gbx-1193-v11-release-candidate/summary.json` |
| Deterministic eval release report | passed | `.glassbox/evals/gbx-1193-v11-release-candidate/v11-release-signoff/` |
| V11 confidence release profile | passed | `.glassbox/evals/gbx-1193-v11-release-candidate/v11-confidence-release/` |
| Recommendation/recovery smoke | passed | `.glassbox/evals/gbx-1193-v11-release-candidate/v11-recommendation-recovery-smoke/` |
| Knowledge/branch-search smoke | passed | `.glassbox/evals/gbx-1193-v11-release-candidate/v11-knowledge-branch-smoke/` |
| Live cockpit dogfooding | passed | `.glassbox/releases/gbx-1192-dogfooding/` |
| Accessibility evidence | bounded pass | [accessibility-review-v11.md](./accessibility-review-v11.md) |
| Provider posture | advisory | [providers.md](./providers.md) and v11 gate advisory provider section |
| Package smoke | passed | [release-packaging.md](./release-packaging.md) and v11 gate installed smoke |
| Dogfooding disposition | passed triage | [v11-dogfooding-summary.md](./v11-dogfooding-summary.md) |
| Residual risk review | accepted | known residual risks listed above |

No deterministic blocker remains open for v11 release-candidate publication.
The accepted residual risks stay bounded to the live-browser, accessibility,
provider, active-milestone recipe, knowledge-source inspection,
branch-search-diff, and bounded-autonomy limits named above.

## Related Files

- [v11-confidence-adoption-contract.md](./v11-confidence-adoption-contract.md)
- [v11-residual-risk-audit.md](./v11-residual-risk-audit.md)
- [v11-release-gate.md](./v11-release-gate.md)
- [v11-dogfooding-summary.md](./v11-dogfooding-summary.md)
- [live-cockpit-evidence-v11.md](./live-cockpit-evidence-v11.md)
- [accessibility-review-v11.md](./accessibility-review-v11.md)
- [knowledge-posture.md](./knowledge-posture.md)
- [branch-search.md](./branch-search.md)
- [reviewer-evidence-bundles.md](./reviewer-evidence-bundles.md)
- [replay-evals.md](./replay-evals.md)
- [providers.md](./providers.md)
- [release-packaging.md](./release-packaging.md)
- [tasks-v11.md](./tasks-v11.md)
