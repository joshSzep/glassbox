# v8 Auditable Autonomy Contract

This document defines the v8 auditable-autonomy contract for Glassbox after the v7 release-candidate decision. It converts the v7 residual risks, post-v7 autonomy direction, and Phase 81 baseline work into one operator-readable milestone boundary without requiring contributors to inspect the task graph first.

## Scope

Glassbox v8 should make the local-first agent harness more capable without making it opaque. The milestone promotes autonomy from prompt convention into durable runtime state that operators can inspect, pause, replay, and bound by policy.

The milestone focuses on:

- first-class task plans, task steps, verification runs, and blocked reasons as event-sourced runtime objects
- autonomy modes and explicit local budgets for steps, tools, writes, commands, verification, runtime, branch attempts, and artifact growth
- opt-in daemon background work for bounded continuation, local maintenance, and derived-state refreshes
- workspace memory with provenance, freshness, confirmation, invalidation, export, import, and replay behavior
- repository intelligence that is local, rebuildable, freshness-aware, and separate from hidden prompt memory
- verify-repair loops that run selected local checks, attempt bounded repairs, and stop when evidence or budgets say to stop
- branch-search workflows that compare local candidate strategies before an operator chooses a path
- provider capability evidence that helps operators pick models for agentic workflows while remaining advisory
- dashboard autonomy-console surfaces for tasks, budgets, background jobs, memory, repository index, branch search, and why-this-action evidence
- v8 release evidence that proves autonomous behavior is bounded, recoverable, auditable, and useful

The milestone should deepen the existing v7 product instead of replacing it. Terminal chat remains the primary conversation surface. The dashboard becomes a richer autonomy console. SQLite canonical events remain the source of truth. Deterministic replay and eval remain release authority.

## Non-Goals

v8 does not introduce:

- hosted collaboration or a hosted control plane
- remote ownership authority for local workspaces
- cloud workers or a remote worker fleet
- remote multi-user orchestration
- simultaneous multi-writer mutation of one workspace
- browser-native code editing as a replacement for local tools
- plugin marketplaces or arbitrary third-party tool loading
- remote policy enforcement
- hidden provider-side memory
- uninspectable vector-store retrieval treated as a source of truth
- automatic merging of branch-search candidates into parent history
- replacement of deterministic replay/eval release authority with live-provider canaries
- removal of the plain terminal fallback

Multiple local observers and richer local autonomy are in scope. Multiple concurrent mutation owners and cloud authority are not.

## Supported Workflow Set

v8 work should preserve and strengthen these supported workflows:

- `glassbox session chat` as the terminal-first operator workflow, with the full-screen TUI as the default supported interactive surface
- `glassbox session attach` for daemon-owned live attach and persisted local reopen
- `glassbox dashboard serve` and co-hosted dashboard inspection
- session actions for message, answer, approve, deny, cancel, fork, resume, export, and import
- task-plan inspection, task continuation, task pause/resume/cancel, and task export once the v8 task-plan slices land
- workspace daemon start, status, stop, stale-owner recovery, and opt-in background job inspection
- workspace memory inspection, confirmation, invalidation, pruning preview, export, import, and prompt-use evidence once the v8 memory slices land
- repository index build, status, search, stale-index recovery, and prompt-use evidence once the v8 repository-intelligence slices land
- verify-repair loops selected from workspace profiles, changed paths, eval recommendations, or explicit operator commands
- branch-search review and candidate selection without automatic parent mutation
- replay bundle export, replay run, eval run, eval audit, eval recommend, eval report, eval promote, and eval refresh
- provider diagnostics, advisory provider canary runs, and provider recommendation cues
- observability, projection check and rebuild, artifacts inspect and prune, backup create and restore, and package validation

If a v8 task changes one of these workflows, the change should be covered by tests, docs, and retained evidence appropriate to the risk.

## Auditable Autonomy Definition

Auditable autonomy means Glassbox may continue selected local work only when the reason, authority, state, and stop condition are inspectable.

For v8, autonomous behavior is auditable only when:

- plan state is durable, queryable, and linked to the session or task that created it
- budget state is typed, persisted, checked before each bounded action, and visible in status, dashboard, export, replay, and eval evidence
- memory state has provenance, freshness, confirmation, invalidation, and usage evidence
- background work has job identity, ownership, heartbeats, progress, cancellation, retry, stale-owner recovery, and retained failure evidence
- branch attempts have candidate lineage, strategy labels, verification outcomes, comparison summaries, and operator selection metadata
- verification loops record selected checks, command or eval evidence, failure categories, repair attempts, retry counts, and residual risks
- provider evidence names advisory confidence and skip/failure reasons without becoming deterministic release authority
- the runtime stops on approval requirement, user question, policy block, budget exhaustion, verification failure, provider unavailability, daemon unavailability, ambiguity, cancellation, or configured completion

Autonomy that exists only in model prose, process-local state, hidden provider memory, or dashboard-local state does not satisfy the v8 contract.

## v7 Follow-Up Mapping

The v7 release candidate carried accepted residual risks and a post-v7 opportunity to become less conservative. v8 maps them as follows:

| v7 item | v8 handling |
| --- | --- |
| Provider-specific remote cancellation may not stop remote computation immediately | Keep local cancellation semantics deterministic; expand advisory provider canary depth for cancellation, retry, and tool-call streaming in `GBX-873`; keep provider evidence advisory unless later promoted by policy. |
| Live-provider workflow canaries remain scenario-limited | Add deeper agentic canary scenarios in `GBX-873` and provider-aware recommendations in `GBX-874`, while deterministic evals remain release authority. |
| Accessibility claims remain limited to named pairings | Add autonomy-console accessibility and long-session review in `GBX-886`, then retain manual release evidence in `GBX-894`. |
| Larger-session and performance checks can vary by machine | Keep v7 scale evidence as a baseline; add task, job, memory, index, verification, branch-search, and dashboard evidence to the v8 gate in `GBX-893`. |
| Plain fallback remains necessary | Preserve the fallback path through terminal review and package smoke in `GBX-894` and `GBX-892`. |
| Approval modes are too coarse for calibrated autonomy | Define autonomy modes and budgets in `GBX-830`, budget evidence in `GBX-831`, calibrated approval semantics in `GBX-832`, and CLI/session configuration in `GBX-834`. |
| Planning and verification are mostly implicit in model output | Add durable task-plan events in `GBX-820`, plan capture in `GBX-824`, verification contracts in `GBX-860`, verify-repair loops in `GBX-861`, and eval recommendation execution in `GBX-862`. |
| Daemon ownership is reliable but not proactive | Add background job ownership in `GBX-840`, inspectable queue projections in `GBX-841`, read-only jobs in `GBX-842`, task continuation jobs in `GBX-843`, recovery in `GBX-844`, and release smoke in `GBX-845`. |
| Runtime notes and repository context are useful but shallow | Add workspace memory in `GBX-850` through `GBX-856` and repository intelligence in `GBX-853` through `GBX-855`. |
| Branching exists but is not a strategy-search primitive | Add branch-search models in `GBX-863`, bounded candidate execution in `GBX-864`, and operator selection/handoff in `GBX-865`. |
| Dashboard is an inspection console rather than an autonomy control room | Design and implement autonomy-console surfaces in `GBX-880` through `GBX-886`. |

## Evidence Classes

v8 release readiness should keep evidence classes distinct:

- **Deterministic blocking evidence**: Python format, lint, typecheck, focused tests, full tests, deterministic evals, eval audit, v8 autonomy evals, frontend lint/typecheck/tests/build, package build, package contents validation, installed smoke, background-job smoke, memory/index smoke, task-plan replay evidence, and v8 release-gate summary.
- **Autonomy boundedness evidence**: task-plan events, budget decisions, budget exhaustion, policy decisions, approval and question pauses, cancellation, pause/resume, daemon job heartbeats, stale-owner recovery, verification attempts, branch-search candidate outcomes, and residual-risk acceptance.
- **Advisory provider evidence**: provider diagnostics, provider capability matrix rows, agentic canary scenarios, provider recommendation confidence, redacted provider failures, credential skips, and provider-specific notes.
- **Manual evidence**: terminal review, dashboard autonomy-console review, recovery and maintenance review, named accessibility pairings, memory/index curation review, branch-search review, provider recommendation review, package smoke notes, and final residual-risk review.
- **Operational evidence**: observability reports, projection health, artifact retention summaries, backup and restore smoke, daemon status, background job queue state, memory freshness, repository index freshness, eval summaries, and retained release summaries.

Provider evidence should never be mistaken for deterministic release signoff. Autonomous behavior should never be considered release-ready without boundedness evidence.

## Release-Readiness Checklist

Before treating a build as the v8 release candidate, complete this list:

- The v8 contract, inventory, task graph, and release-candidate guide are discoverable from the docs hub.
- `uv run glassbox command tree` matches the documented command surface.
- The v8 release gate passes and writes `summary.json` with deterministic, advisory, manual-evidence, and autonomy-boundedness sections.
- The deterministic `release-candidate` eval profile passes.
- The v8 autonomy eval suite covers task planning, budget exhaustion, verify-repair, memory/index context drift, task continuation, and branch-search comparison where stable.
- Autonomy modes, budgets, policy decisions, approval semantics, and stop reasons have CLI, web, replay, eval, export, and dashboard evidence.
- Background daemon jobs have smoke evidence for read-only jobs, continuation jobs, cancellation, failure, retry, and stale-owner recovery.
- Workspace memory and repository index behavior have provenance, freshness, confirmation, invalidation, redaction, context-use, and replay-drift evidence.
- Verify-repair loops and branch-search workflows have deterministic local fixtures and retained artifacts.
- Provider diagnostics and provider canaries either run with retained redacted evidence or record explicit skip reasons.
- Dashboard autonomy-console evidence covers task queue, plan inspector, budget controls, memory/index inspectors, branch comparison, why-this-action evidence, mobile, and keyboard workflows.
- Terminal review evidence covers task planning, background continuation cues, approvals/questions, cancellation, daemon attach, long output, and fallback.
- Recovery review evidence covers observability, projections, artifacts, backups, daemon, jobs, memory, index, eval, installed dashboard, and package workflows.
- Package artifacts include static dashboard assets, v8 docs, eval profiles, task/autonomy/job/memory/index modules, release scripts, and source-builder guidance.
- Named accessibility pairings are recorded before making stronger accessibility claims.
- Residual risks are named, mitigated, and accepted in the release decision.

## Residual Risk Register Shape

The v8 release candidate may carry residual risks only when they are explicit and accepted. Use this shape for every residual risk:

- **Risk**: the concrete autonomy, provider, recovery, usability, performance, packaging, accessibility, or release limitation.
- **Evidence**: tests, docs, deterministic eval, provider canary, manual review, retained release summary, or operator artifact that proves the risk is understood.
- **Impact**: who is affected and when.
- **Mitigation**: command, workflow, fallback, documentation, budget, policy rule, recovery action, or follow-up task.
- **Decision**: accepted, blocking, deferred, or out of scope.

Initial expected residual-risk candidates are:

- provider-specific live behavior outside deterministic replay authority
- model variability in plan quality even when plan state is durable
- false-positive or stale memory candidates before operator confirmation
- incomplete repository-index coverage for unusual project layouts
- branch-search strategy coverage that is useful but not exhaustive
- machine-specific performance variance in long verification or indexing jobs
- dashboard accessibility limits outside named pairings reviewed for v8
- plain fallback limitations in unsupported terminal environments

## Pass And Fail Policy

- Deterministic stage failure blocks the v8 release candidate.
- Eval audit failure blocks when a release-critical v8 capability is uncovered without an accepted integration-only rationale.
- Autonomy-boundedness evidence failure blocks when autonomous work can continue without typed budgets, policy evidence, cancellation, replay/eval visibility, or durable stop reasons.
- Task-plan, background-job, memory, repository-index, verification-loop, or branch-search projection corruption blocks unless recovery commands repair the issue and retained evidence proves recovery.
- Provider canary skips do not block when credentials are unavailable and the skip reason is retained.
- Provider canary failures are advisory by default, but the release decision must record impact, next action, and whether the failure changes a supported provider claim.
- Dashboard or terminal accessibility findings block when they affect a supported primary workflow or contradict a public accessibility claim.
- Package build, package contents, installed terminal, installed dashboard, installed daemon, installed eval, installed autonomy commands, or onboarding smoke failure blocks.
- Residual risks are allowed only when named, mitigated, and accepted in the final release decision.

## Related Files

- [tasks-v8.md](./tasks-v8.md)
- [v8-autonomy-baseline-inventory.md](./v8-autonomy-baseline-inventory.md)
- [v7-release-candidate.md](./v7-release-candidate.md)
- [v7-release-gate.md](./v7-release-gate.md)
- [v7-adoption-scale-contract.md](./v7-adoption-scale-contract.md)
- [v7-scale-verification-inventory.md](./v7-scale-verification-inventory.md)
- [runtime-context.md](./runtime-context.md)
- [tool-policy.md](./tool-policy.md)
- [persistent-runtime.md](./persistent-runtime.md)
- [replay-evals.md](./replay-evals.md)
- [providers.md](./providers.md)
