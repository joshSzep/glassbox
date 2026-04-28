# v7 Adoption And Scale Contract

This document defines the v7 adoption-and-scale contract for Glassbox after the
v6 release-candidate decision. It converts the v6 residual risks and post-v6
follow-up backlog into one operator-readable milestone boundary without
requiring contributors to inspect the task graph first.

## Scope

Glassbox v7 should make the local-first agent harness more trustworthy under
real local use after the v6 release candidate. The milestone focuses on:

- deterministic eval coverage for approval, ask-user, cancellation variants,
  daemon attach, and dashboard-originated actions
- advisory provider capability evidence across more scenarios and providers
- larger-session scale for snapshots, transcripts, event logs, projections,
  artifacts, and dashboard rendering
- daemon, live transport, and multi-observer reliability while preserving one
  local mutation owner per workspace
- repository-owned tool-policy governance with clearer precedence,
  explanations, fixtures, and validation recommendations
- dashboard evidence surfaces for lineage, comparison, latency, policy,
  replay/eval, and provider-capability cues
- named accessibility review pairings before making stronger accessibility
  claims
- first-run, provider, profile, package, and source-builder onboarding

The milestone should deepen the existing v6 product instead of replacing it.
Terminal chat remains the primary conversation surface. The dashboard remains
the paired operator console. SQLite canonical events remain the source of truth.
Deterministic replay/eval remains the release authority.

## Non-Goals

v7 does not introduce:

- a hosted control plane
- remote multi-user orchestration
- cloud authority for session ownership
- browser-native code editing
- plugin marketplaces or marketplace-style trust
- remote policy enforcement
- replacement of deterministic evals with live-provider canaries
- removal of the plain terminal fallback

Multiple local observers are in scope. Multiple concurrent mutation owners are
not. Provider canaries may broaden substantially, but they remain advisory
unless a later task explicitly promotes a scenario with stable credentials,
repeatability, and failure policy.

## Supported Workflow Set

v7 work should preserve and strengthen these supported workflows:

- `glassbox session chat` as the full-screen terminal-first chat workflow
- `glassbox session attach` for persisted local reopen and daemon-owned live
  attach
- `glassbox dashboard serve` and co-hosted dashboard inspection
- session actions for message, answer, approve, deny, cancel, fork, resume,
  export, and import
- workspace daemon start, status, stop, stale-owner recovery, and health
  inspection
- replay bundle export, replay run, eval run, eval audit, eval recommend, and
  eval report
- provider diagnostics and advisory provider canary runs
- observability, projection check and rebuild, artifacts inspect and prune,
  backup create and restore, and package validation

If a v7 task changes one of these workflows, the change should be covered by
tests, docs, and retained evidence appropriate to the risk.

## v6 Follow-Up Mapping

The v6 release candidate carried accepted residual risks and a short post-v6
backlog. v7 maps them as follows:

| v6 item | v7 handling |
| --- | --- |
| Provider-specific cancellation may not stop remote computation immediately | Keep local cancellation semantics deterministic; broaden advisory provider canary scenarios in `GBX-730` through `GBX-733` and cancellation eval variants in `GBX-723`. |
| Live-provider canaries are advisory and scenario-limited | Define a provider capability matrix in `GBX-730`, expand diagnostics in `GBX-731`, add multi-scenario canaries in `GBX-732`, and surface evidence in `GBX-733`. |
| Accessibility claims are limited to reviewed workflows | Add named terminal, browser, and assistive-technology pairing reviews in `GBX-780`. |
| Installed-package smoke is intentionally short | Extend package and onboarding smoke in `GBX-782` and make the final gate decision in `GBX-783`. |
| Plain fallback remains necessary | Preserve fallback as a supported compatibility path; test it in onboarding, package, and release validation tasks. |
| Approval and ask-user replay cases are not yet deterministic release coverage | Promote approval and ask-user eval cases in `GBX-720` and `GBX-721`. |
| High-priority dashboard states need longer installed or release smoke | Cover larger sessions and dashboard evidence in `GBX-742`, `GBX-773`, `GBX-782`, and `GBX-784`. |

## Evidence Classes

v7 release readiness should separate evidence classes instead of flattening them
into one green result:

- **Deterministic blocking evidence**: Python format, lint, typecheck, focused
  tests, full tests, deterministic evals, eval audit, release-signoff reports,
  frontend lint/typecheck/tests/build, package build, package content checks,
  installed smoke, and scale-focused deterministic checks.
- **Advisory provider evidence**: provider diagnostics, provider capability
  matrix summaries, scenario canary runs, skipped credential reasons, redacted
  failures, and provider-specific notes.
- **Manual evidence**: terminal review, dashboard review, recovery and
  maintenance review, named accessibility pairings, larger-session inspection,
  package smoke notes, and final residual-risk review.
- **Operational evidence**: observability reports, projection health, artifact
  retention summaries, backup and restore smoke, daemon status, live transport
  counters, and retained release summaries.

Provider evidence should never be mistaken for deterministic release signoff.
Manual evidence should name reviewed workflows and pairings precisely.

## Release-Readiness Checklist

Before treating a build as the v7 release candidate, complete this list:

- The v7 contract, inventory, and task graph are discoverable from the docs hub.
- Deterministic eval coverage includes the v7 release-critical capabilities or
  explicitly records why a capability remains integration-only.
- `uv run glassbox eval audit` reports no uncovered release-critical v7
  capability.
- `uv run glassbox eval report commit-smoke push-confirmation release-candidate`
  writes retained deterministic signoff evidence.
- Provider diagnostics and provider canaries write a redacted advisory
  capability matrix or an explicit skip reason.
- Larger-session backend and dashboard scale checks pass or name accepted
  residual risks with mitigations.
- Daemon attach, stale-owner recovery, SSE reconnect, and multi-observer smoke
  have deterministic coverage.
- Tool-policy behavior has explanation evidence, fixtures, and validation
  recommendations.
- Dashboard evidence surfaces remain keyboard-usable, responsive, and backed by
  tests or manual review artifacts.
- Named accessibility pairings are reviewed before any stronger accessibility
  claim is made.
- Installed-package and source-builder onboarding smoke passes without requiring
  Node.js for runtime users.
- The v7 automated gate, or an explicitly extended v6 gate, passes and writes a
  structured evidence summary.
- Manual validation exists in the same evidence directory as the automated
  summary.
- Residual risks are named, mitigated, and accepted in the release decision.

## Residual Risk Register Shape

The v7 release candidate may carry residual risks only when they are explicit
and accepted. Use this shape for every residual risk:

- **Risk**: the concrete uncertainty or limitation.
- **Evidence**: tests, docs, provider canary, manual review, or retained summary
  that proves the risk is understood.
- **Impact**: who is affected and when.
- **Mitigation**: command, workflow, fallback, documentation, or follow-up task.
- **Decision**: accepted, blocking, deferred, or out of scope.

Initial expected residual-risk candidates are:

- provider-specific remote cancellation behavior that cannot be made
  deterministic locally
- live-provider canary coverage gaps when credentials or provider capabilities
  are unavailable
- accessibility limits outside the named pairings reviewed for v7
- machine-specific performance variance in larger-session checks
- dashboard states that remain source-tested but not deeply installed-smoked
- plain fallback limitations in unsupported terminal environments

## Pass And Fail Policy

- Deterministic stage failure blocks the v7 release candidate.
- Eval audit failure blocks when a release-critical v7 capability is uncovered
  without an accepted integration-only rationale.
- Provider canary skips do not block when credentials are unavailable and the
  skip reason is retained.
- Provider canary failures are advisory by default, but the release decision must
  record impact, next action, and whether the failure changes a supported
  provider claim.
- Larger-session scale failures block when they break supported inspection or
  recovery workflows; noisy machine-specific thresholds may be accepted only
  with documented mitigations.
- Dashboard or terminal accessibility findings block when they affect a
  supported primary workflow or contradict a public accessibility claim.
- Package build, package contents, installed terminal, installed dashboard,
  installed daemon, installed eval, or onboarding smoke failure blocks.
- Residual risks are allowed only when named, mitigated, and accepted in the
  final release decision.

## Related Files

- [tasks-v7.md](./tasks-v7.md)
- [v7-scale-verification-inventory.md](./v7-scale-verification-inventory.md)
- [v6-release-candidate.md](./v6-release-candidate.md)
- [v6-release-gate.md](./v6-release-gate.md)
- [replay-evals.md](./replay-evals.md)
- [providers.md](./providers.md)
- [tool-policy.md](./tool-policy.md)
- [persistent-runtime.md](./persistent-runtime.md)
- [release-packaging.md](./release-packaging.md)
