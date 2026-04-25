# Glassbox v2 Tasks

For the docs hub and operator guides, start at [README.md](./README.md). This file is the v2 task graph and milestone roadmap that follows the completed baseline in [tasks-v1.md](./tasks-v1.md).

## Purpose

This document defines the next major evolution of Glassbox after the current local-first, event-sourced baseline.

It is written in the same execution style as [tasks-v1.md](./tasks-v1.md): explicit dependencies, small vertical slices, concrete deliverables, and quality requirements attached directly to the work.

Glassbox v2 should deepen the existing product rather than restart it. The core runtime, CLI, dashboard, replay, eval, branching, and richer-context foundations already exist. v2 is about making that foundation more durable, more operable, and more trustworthy under longer-lived real use.

## Product Direction

Glassbox v2 should optimize for four outcomes:

- persistent runtime ownership beyond a single terminal process
- stronger local durability, recovery, and upgrade safety
- a more capable operator console for multi-session and high-signal inspection
- a tighter engineering workflow around replay, eval, and release confidence

The v2 thesis is:

- keep the runtime local-first
- keep `events` as the canonical source of truth
- keep operator inspection first-class
- keep replay and eval deterministic by default
- extend the current architecture deliberately rather than replacing it with a cloud-first or opaque orchestration model

## Current Baseline Before V2 Execution

The repository has moved materially since this file was first written. Treat the
following as the starting point for every v2 task in this document:

- the CLI already supports `chat`, process-local `attach`, explicit state-driven
  session commands, `serve`, `fork`, `status`, and `rebuild`
- the dashboard already supports recent-session discovery, deep-link session
  inspection, lineage-aware snapshots, next-action controls, pending approvals,
  and SSE-backed live versus historical state indicators
- the store already records a schema version row, applies a small amount of ad
  hoc bootstrap schema patching, and can rebuild projections from canonical
  events, but it does not yet have explicit ordered migrations or projection
  health surfaces
- replay and eval already support repository-owned cases and profiles, coverage
  auditing, baseline promotion and refresh, replay bundle export, and
  release-signoff reporting

v2 work should extend these existing surfaces rather than reintroduce them under
new names.

## Agent Execution Rules

These rules apply to every task in this file.

1. Respect dependency order. Do not start a task until its dependencies are complete unless the task explicitly says it can proceed in parallel.
2. Preserve the event-sourced source-of-truth rule. New caches, indexes, transports, and UI state remain derived from canonical events.
3. Prefer small executable slices over speculative platform work. Each phase should leave the repo in a stronger usable state.
4. Treat v2 as an extension of the shipped Glassbox model, not a rewrite. Reuse the existing runtime, CLI, store, replay, and dashboard boundaries wherever possible.
5. Every feature task automatically includes:
   - automated tests for the new behavior
   - `ruff` formatting and lint compliance
   - `ty` typecheck compliance for touched code
   - documentation updates when contracts or workflows change
6. If a v2 task exposes an architectural mismatch, update [architecture.md](./architecture.md) or [database.md](./database.md) before or alongside the code change.
7. Do not weaken deterministic replay, local-first operation, or approval semantics in pursuit of convenience features.

## Completion Contract For Any Task

A task is complete only when all of the following are true:

- the implementation exists in the intended module boundary
- automated tests covering the new behavior exist and pass
- lint, formatting, and type checks pass for the touched slice
- the task does not leave placeholder code or hidden follow-up work outside this file
- docs are updated if the task changes persistence, transport, operator-visible behavior, or verification workflows

## Suggested Status Markers

If an agent updates this document later, use one of these markers next to task IDs:

- `TODO`
- `IN_PROGRESS`
- `BLOCKED`
- `DONE`

## Expected Repository Targets

These are the main implementation areas referenced below:

```text
src/glassbox/
    cli/
    core/
    runtime/
    llm/
    tools/
    store/
    web/
    services/
tests/
docs/
evals/
```

## Milestone Map

The intended v2 milestone order is:

1. persistent runtime foundation
2. durable storage, migration, and recovery
3. operator console v2
4. policy and tool-governance v2
5. replay and eval developer workflow v2
6. team workflow and portable-session ergonomics
7. hardening, performance, and v2 release polish

Each phase below corresponds to one concrete milestone.

## Task Graph

---

## Phase 25: Persistent Runtime Foundation

### GBX-300: Define Persistent Runtime Ownership And Attach Model

- Status: `DONE`
- Depends on: `GBX-166`, `GBX-175`, `GBX-185`, `GBX-249`
- Goal: define how Glassbox should support a long-lived runtime process and cross-process operator attachment without violating the current event-sourced architecture
- Deliverables:
  - architecture and workflow updates for embedded runtime versus background runtime ownership
  - explicit decision record for whether the first persistent owner is introduced as a new daemon command surface, an extension of the existing runtime-serving surface, or another concrete local-first control path
  - explicit runtime ownership semantics for workspace-local sessions
  - attach model for terminal and browser clients reconnecting to a persistent runtime
  - scope boundary for what remains intentionally out of scope for the first v2 slice
- Implementation notes:
  - start from the current baseline: `chat` owns the live in-process session loop, `attach` reopens persisted actionable sessions, `serve` exposes standalone browser inspection, SSE provides browser live tails, and the event bus is still process-local
  - GBX-300 chooses a new `glassbox daemon` command surface as the future persistent runtime owner; `serve` stays the browser-facing observation surface rather than becoming the owner itself
  - preserve the current single-runtime-per-workspace assumption unless a stronger multi-owner model is justified explicitly
  - define how live event delivery, session mutation, and runtime shutdown interact across processes
  - treat CLI attach, browser observation, and health inspection as separate operator surfaces even if they share a transport
- Tests and validation included in task:
  - architecture and doc review against current `chat`, `attach`, `serve`, SSE, and event-bus behavior before coding starts
  - manual validation that the proposed attach model does not quietly reintroduce hidden mutable state outside the canonical event flow
- Done when:
  - the repo has a clear, code-aligned v2 contract for background runtime ownership, attach semantics, and process boundaries

### GBX-301: Introduce Transport Abstraction For In-Process And Cross-Process Event Delivery

- Status: `DONE`
- Depends on: `GBX-300`
- Goal: decouple event fanout from the current process-local bus so Glassbox can support persistent-runtime clients without duplicating runtime logic
- Deliverables:
  - runtime transport abstraction covering in-process subscribers and cross-process consumers
  - implementation path for local IPC, loopback HTTP streaming, or equivalent transport chosen in `GBX-300`
  - compatibility layer that preserves the current embedded runtime behavior during migration
- Implementation notes:
  - treat the existing in-process event bus plus SSE fanout as the compatibility baseline to preserve during the refactor
  - keep canonical persistence independent from subscriber health or transport latency
  - preserve current CLI renderer and SSE semantics where practical so the transition stays incremental
  - do not let transport concerns leak into turn orchestration or repository code
- Tests and validation included in task:
  - async integration tests for mixed subscriber types, disconnects, and cleanup
  - regression tests proving embedded in-process flows still behave correctly after the abstraction lands
- Done when:
  - runtime event delivery can support both current embedded consumers and the chosen cross-process attach path through one explicit boundary

### GBX-302: Implement Workspace-Scoped Persistent Runtime Process

- Status: `DONE`
- Depends on: `GBX-300`, `GBX-301`
- Goal: allow Glassbox to run as a long-lived workspace runtime that survives terminal exit and can continue owning actionable sessions
- Deliverables:
  - `glassbox daemon start|status|stop` background runtime command surface
  - workspace-local runtime discovery and lock semantics
  - start, stop, and health behavior for the persistent runtime owner
  - session ownership rules that prevent conflicting concurrent writers
- Implementation notes:
  - keep the first persistent runtime local-first and workspace-scoped; do not expand into remote orchestration
  - make runtime shutdown and orphaned-lock recovery explicit and observable
  - reuse existing runtime bootstrap, session service, and server wiring rather than creating a second control plane
- Tests and validation included in task:
  - integration tests for background runtime startup, duplicate-owner rejection, and clean shutdown
  - recovery tests for stale lock or abandoned runtime ownership after process interruption
- Done when:
  - Glassbox can host a persistent local runtime process that owns workspace sessions safely across terminal lifecycles
  - local mutating CLI flows reject execution while a daemon owns the same workspace runtime

### GBX-303: Add Cross-Process Interactive Attach And Reconnect Flow

- Status: `DONE`
- Depends on: `GBX-301`, `GBX-302`
- Goal: let operators attach an interactive terminal UI to a session owned by a different long-lived process and continue work with live updates
- Deliverables:
  - attach path for terminal clients against the persistent runtime
  - reconnect semantics for terminal interruption during a live session
  - operator-visible messaging for live, stale, reconnecting, and unavailable runtime states
  - compatibility handling for sessions that are only historically inspectable
- Implementation notes:
  - the current `attach` command already reopens persisted actionable sessions; this task is specifically about live attach and reconnect against a different owning process
  - keep conversational routing semantics aligned with the current interactive CLI rather than inventing a second UX model
  - distinguish between attach-to-runtime and open-historical-session behavior explicitly
  - do not silently fall back from live attach to stale snapshot mode without telling the operator
- Tests and validation included in task:
  - CLI integration tests for attach to a session owned by another process, disconnect, and successful reattach
  - negative-path tests for unavailable runtimes, unknown sessions, and non-attachable session states
- Done when:
  - a user can continue a live Glassbox session from a new terminal process without restarting the owning runtime
  - `attach` chooses between live daemon attach and explicit historical local reopen semantics without silently blurring the two

### GBX-304: Add Persistent Runtime Health, Discovery, And Operator Documentation

- Status: `DONE`
- Depends on: `GBX-302`, `GBX-303`, `GBX-121`
- Goal: make the persistent-runtime model operable and discoverable without requiring source inspection
- Deliverables:
  - health and discovery surfaces for persistent runtime status
  - operator guidance for starting, attaching to, and recovering a background runtime
  - troubleshooting notes for stale ownership, reconnect failures, and runtime shutdown behavior
- Implementation notes:
  - build on the existing `/healthz`, standalone dashboard session index, and operator docs rather than replacing them with parallel discovery surfaces
  - keep health surfaces complementary to the event model; they describe runtime availability, not canonical session truth
  - align terminal, dashboard, and docs terminology for runtime-owned versus historical-only sessions
- Tests and validation included in task:
  - HTTP or CLI integration tests for runtime discovery and health reporting
  - doc review against implemented runtime lifecycle behavior and attach semantics
- Done when:
  - an operator can understand and use the persistent-runtime flow from docs and help output alone
  - `glassbox daemon status` exposes human-readable and JSON discovery output for runtime health, metadata, logs, and next commands

---

## Phase 26: Durable Storage, Migration, And Recovery

### GBX-310: Replace Bootstrap-And-Ad-Hoc Schema Patching With Versioned Migrations

- Status: `DONE`
- Depends on: `GBX-302`
- Goal: make Glassbox workspace state safely upgradeable across runtime and schema evolution
- Deliverables:
  - versioned migration mechanism for canonical and projection schema changes
  - schema-version tracking and upgrade metadata
  - migration entrypoint integrated with runtime bootstrap and recovery workflows
- Implementation notes:
  - the current baseline already records one schema version row and applies targeted bootstrap patch helpers for lineage and runtime-note columns; replace those hidden upgrades with explicit ordered migrations
  - keep migrations explicit and reviewable rather than hiding schema mutation inside ad hoc bootstrap code
  - preserve backwards compatibility for older workspaces where possible and fail visibly where not
  - distinguish schema upgrade from projection rebuild so operators can reason about each independently
- Tests and validation included in task:
  - integration tests for fresh bootstrap, forward migration from representative older schemas, and idempotent repeated startup
  - regression tests for sessions created before the migration system lands
- Done when:
  - a persisted Glassbox workspace can move between supported versions without manual SQLite intervention
  - runtime bootstrap applies ordered migration metadata for the v3 baseline, session-lineage upgrade, and runtime-note provenance upgrade

### GBX-311: Add Projection-Recovery, Lag Inspection, And Rebuild Safety Improvements

- Status: `DONE`
- Depends on: `GBX-310`
- Goal: make projection failure and rebuild behavior more predictable under long-lived runtimes and larger event histories
- Deliverables:
  - projection health and lag inspection surfaces
  - safer per-session and whole-workspace rebuild behavior
  - operator-visible distinction between canonical event integrity and derived-state corruption
- Implementation notes:
  - the current `rebuild` command and repository rebuild helpers are the starting point; harden and instrument them rather than replacing them
  - keep rebuild deterministic from events; do not introduce shadow checkpoints unless a real need is demonstrated
  - surface projection lag or failure as an operational condition, not a silent stale-read risk
  - preserve current rebuild commands where practical while strengthening their observability
- Tests and validation included in task:
  - integration tests for projection wipe-and-rebuild, simulated projection failure, and recovery after restart
  - tests proving session snapshots return truthful degraded-state signals when projections are stale or unavailable
- Done when:
  - Glassbox can recover derived state predictably and tell the operator when projections are unhealthy
  - `glassbox rebuild --check`, CLI status, and session snapshots report projection health, lag, degraded state, and rebuild guidance without treating canonical events as corrupt

### GBX-312: Add Artifact Integrity, Retention, And Garbage-Collection Policy

- Status: `DONE`
- Depends on: `GBX-310`
- Goal: keep `.glassbox` artifact growth bounded and trustworthy as replay, eval, and long-lived runtime use increase
- Deliverables:
  - artifact integrity metadata such as content hashes or equivalent checks
  - retention policy for ephemeral outputs, eval artifacts, and stale derived summaries
  - garbage-collection command or service path with dry-run support
- Implementation notes:
  - do not delete curated baselines, source-controlled replay bundles, or canonical event data through the GC path
  - prefer explicit policy and dry-run output over silent cleanup
  - align artifact categories with existing replay, eval, and context-summary workflows
- Tests and validation included in task:
  - integration tests for artifact hashing, stale-artifact cleanup, and dry-run reporting
  - negative-path tests ensuring protected artifact classes are never removed accidentally
- Done when:
  - Glassbox can explain what artifact state exists, what is stale, and what cleanup would do before it mutates local storage
  - newly recorded file-backed artifacts include size and SHA-256 metadata in their canonical artifact events
  - `glassbox artifacts gc --dry-run` reports protected, stale, missing, and would-delete artifact state, while mutation mode only deletes managed stale `.glassbox` artifacts

### GBX-313: Add Workspace Backup And State Export For Recovery

- Status: `DONE`
- Depends on: `GBX-310`, `GBX-312`
- Goal: provide a first-class recovery path for workspace-local Glassbox state beyond manual SQLite and artifact copying
- Deliverables:
  - workspace backup or export command covering canonical DB state and required local artifacts
  - restore or import workflow for supported exported state bundles
  - explicit scope documentation for what is and is not portable through the backup path
- Implementation notes:
  - keep the format local-first and inspectable; avoid opaque machine-only dumps where a structured archive is sufficient
  - distinguish full-workspace state export from portable replay and session-sharing bundles
  - do not blur recovery backup with eval baseline export semantics
- Tests and validation included in task:
  - integration tests for backup creation and restore into a clean workspace
  - regression tests proving restored state preserves replayability and session discoverability
- Done when:
  - an operator has a supported way to back up and restore Glassbox workspace state without ad hoc filesystem surgery
  - `glassbox backup create` writes an inspectable archive containing a manifest, canonical SQLite snapshot, and event-referenced `.glassbox` artifacts
  - `glassbox backup restore` validates manifest file hashes and refuses to overwrite existing restored files unless explicitly forced
  - restored workspaces preserve session discovery and deterministic replay for backed-up sessions

---

## Phase 27: Operator Console v2

### GBX-320: Define Multi-Session Operator Console Model

- Status: `DONE`
- Depends on: `GBX-304`, `GBX-184`, `GBX-185`, `GBX-225`
- Goal: define how the dashboard should evolve from the current session-index-plus-deep-link inspector into an operator console for live, paused, and historical sessions
- Deliverables:
  - architecture and UX contract for multi-session browsing, filtering, and actionable queues
  - explicit operator semantics for live runtime-backed sessions versus historical-only sessions
  - prioritization rules for what the dashboard should surface first when many sessions exist
- Implementation notes:
  - the current dashboard already provides recent-session browsing, lineage-aware deep links, next-action controls, and live versus historical SSE state; v2 should build on that shell instead of assuming a blank browser baseline
  - preserve the current event-sourced snapshot-plus-stream model; do not move state authority into browser-only logic
  - keep the first v2 console focused on operator value, not generic application chrome
  - align dashboard terminology with CLI status and runtime health language
- Tests and validation included in task:
  - doc and UX review against current session index, snapshot, SSE, and interactive session semantics before coding starts
  - manual validation that the proposed console model stays within the local-first architecture
- Done when:
  - the repo has a clear, code-aligned design for a multi-session Glassbox operator console
  - [operator-console.md](./operator-console.md) defines the v2 overview, queue, health, priority, live-versus-historical, backend, and frontend contracts against the current dashboard/session API baseline

### GBX-321: Add Aggregate Session, Queue, And Health Read Models

- Status: `DONE`
- Depends on: `GBX-320`, `GBX-302`
- Goal: provide the backend data model needed for a dashboard that prioritizes operational awareness over one-session-at-a-time inspection
- Deliverables:
  - aggregate APIs or read models beyond the existing recent-session summaries, covering pending approvals, pending questions, failed sessions, and runtime health
  - filtering and ordering support for status, recency, and action-needed flows
  - concise summary fields for operator triage without full snapshot fetches
- Implementation notes:
  - build these from the existing session summary and snapshot query path, persisted sessions, projections, and runtime-health surfaces rather than browser heuristics
  - keep the initial aggregate model small and operationally meaningful
  - avoid introducing a separate analytics subsystem when current projections and indexes can support the required reads
- Tests and validation included in task:
  - HTTP integration tests for mixed-status session sets, actionable queues, and health summaries
  - regression tests for consistency between aggregate summaries and full per-session snapshots
- Done when:
  - the dashboard backend can answer what needs attention now without opening each session individually
  - `GET /sessions/aggregate` returns prioritized operator rows, queue counts, projection-health counts, runtime-owner summary, and queue/status/sort filters backed by the persisted session query path

### GBX-322: Implement Operator Console Views For Queues, Health, And Turn Timelines

- Status: `DONE`
- Depends on: `GBX-321`
- Goal: make the browser the best place to inspect many sessions, active problems, and runtime timelines at once
- Deliverables:
  - multi-session landing view with action-needed prioritization
  - queue views for pending approvals, pending questions, and failed sessions
  - richer turn timeline showing model calls, tool calls, suspensions, artifacts, and failure markers
  - clearer live, reconnecting, stale, and historical-only state indicators
- Implementation notes:
  - preserve existing single-session deep-link flows while adding the higher-level console
  - optimize for scan speed and intervention, not maximal UI density
  - keep timeline details grounded in existing events and metrics rather than inferred browser-only summaries
- Tests and validation included in task:
  - frontend reducer and integration tests for console state, queue hydration, and timeline rendering
  - regression tests for deep-link session views and SSE reconnect behavior inside the new console shell
- Done when:
  - an operator can understand what Glassbox is doing across sessions and intervene quickly from the dashboard alone
  - the dashboard root hydrates `GET /sessions/aggregate` into a queue-driven operator console with workspace overview, queue selection, prioritized session cards, preserved `?session=...` deep links, and a timeline-oriented turn pane grounded in existing snapshot plus SSE state

### GBX-323: Add Session Compare, Lineage, And Drift-Inspection Views

- Status: `DONE`
- Depends on: `GBX-322`, `GBX-216`, `GBX-245`
- Goal: make branch comparison, replay drift, and child-session inspection faster from the browser
- Deliverables:
  - UI for comparing parent and child sessions or adjacent historical sessions
  - lineage-aware navigation and summary views
  - browser inspection surfaces for replay or eval drift artifacts where that adds triage value
- Implementation notes:
  - the current snapshot already exposes child sessions, branchable turns, and fork metadata; this task adds comparison and drift-triage UX on top of that baseline
  - keep comparison views explicitly anchored in persisted lineage and replay artifacts rather than computed guesswork
  - do not hide raw detail; comparison views should accelerate inspection, not replace the underlying evidence
  - avoid making the browser the only place replay drift can be understood
- Tests and validation included in task:
  - frontend tests for compare-state hydration, lineage navigation, and drift-summary rendering
  - integration tests for compare views backed by forked sessions and replay artifacts
- Done when:
  - the operator console makes branching and drift triage materially easier than raw snapshot browsing alone
  - the selected-session dashboard can load a second persisted lineage snapshot for parent or child comparison, render snapshot-backed compare summaries without disturbing the live session view, and surface replay or eval drift cues from artifact-backed runtime context so operators can inspect likely drift causes before leaving the browser

---

## Phase 28: Policy And Tool Governance v2

### GBX-330: Define Configurable Tool-Governance Model Beyond Coarse Risk Buckets

- Status: `DONE`
- Depends on: `GBX-122`, `GBX-245`, `GBX-249`
- Goal: define how Glassbox should evolve tool policy from fixed broad buckets into configurable, reviewable governance without losing predictability
- Deliverables:
  - architecture and workflow updates for workspace-level tool policy configuration
  - explicit scope for per-tool, per-argument, and per-command policy controls
  - compatibility rules between policy configuration, approval modes, and replay semantics
- Implementation notes:
  - the compatibility baseline is the current coarse risk buckets, workspace-scope path checks, destructive-command blocking, and approval-mode gating described in `tool-policy.md`
  - keep policy inspectable and local-first; do not hide decision rules in runtime-only implicit heuristics
  - preserve the current simple risk model as the compatibility baseline while v2 policy grows
  - make explicit which policy changes should count as replay-manifest drift versus ordinary runtime configuration
  - GBX-330 chooses a layered governance model: hard runtime invariants, registry-declared risk buckets, repository-owned workspace policy rules, and session approval-mode translation remain distinct concerns
  - the selected v2 rule shape is typed and inspectable rather than executable policy code; repository policy may refine allow-versus-approve-versus-deny outcomes for tool, argument, and command selectors inside existing safety guardrails
  - replay drift is defined against the effective normalized policy snapshot for a recorded turn, not against comments, formatting, or unrelated unused policy rules
- Tests and validation included in task:
  - doc and design review against current tool policy, approval semantics, and replay contracts before coding starts
  - manual validation that the proposed model remains understandable for operators and testable for contributors
- Done when:
  - the repo has a concrete, code-aligned v2 policy model that can support richer governance without reopening the safety story every task

### GBX-331: Implement Workspace-Scoped Policy Configuration And Resolution

- Status: `DONE`
- Depends on: `GBX-330`
- Goal: let repositories tune tool-governance rules deliberately without editing Glassbox source code
- Deliverables:
  - workspace-local policy config format and loader
  - policy resolution path integrated with current approval and command gating logic
  - operator-visible errors for invalid or unsupported policy configuration
- Implementation notes:
  - keep precedence and defaults explicit; repository policy should refine runtime behavior without becoming ambiguous hidden state
  - preserve backwards-compatible behavior when no policy config exists
  - align policy configuration loading with the existing runtime config philosophy used for providers and eval profiles
  - GBX-331 chooses an optional repository-owned `glassbox-policy.json` manifest at the workspace root with explicit `manifest_version`, default actions, and ordered rule matching
  - the first shipped selectors are exact `tool_name` plus bounded `command_prefixes`, `cwd_prefixes`, and `path_prefixes`; this is intentionally typed policy data, not executable policy code
  - missing policy config preserves the current coarse default behavior, while invalid or unsupported manifests fail visibly during runtime policy-context construction
- Tests and validation included in task:
  - unit and integration tests for policy config parsing, precedence, and invalid-config handling
  - regression tests proving the current default policy remains unchanged when no config is supplied
- Done when:
  - Glassbox can resolve workspace policy settings through a supported repository-owned configuration path

### GBX-332: Add Richer Policy Decisions, Tool Risk Summaries, And Audit Surfaces

- Status: `DONE`
- Depends on: `GBX-331`, `GBX-321`
- Goal: make policy outcomes more explainable and more visible across CLI, dashboard, and replay artifacts
- Deliverables:
  - richer policy decision metadata for allow, approve, deny, and blocked outcomes
  - session and turn summaries for tool-risk and policy activity
  - dashboard and CLI surfaces that explain why a tool was allowed, gated, or blocked
- Implementation notes:
  - extend the current policy-decision reason strings and approval state rather than creating a disconnected second audit pipeline
  - reuse current event and artifact patterns where possible rather than creating a separate audit database
  - keep the summary surfaces concise but precise enough to aid operator reasoning
  - preserve clear distinction between policy classification and actual tool outcome
- Tests and validation included in task:
  - projection and integration tests for policy-summary correctness across representative tool flows
  - frontend and CLI regression tests for policy explanation rendering
- Done when:
  - operators can understand tool-safety decisions without reverse-engineering the current policy engine or reading raw events

### GBX-333: Harden Command-Execution Envelopes And Failure Classification

- Status: `DONE`
- Depends on: `GBX-331`, `GBX-332`
- Goal: make command-style tools safer and easier to reason about under v2 governance
- Deliverables:
  - explicit command execution envelopes such as timeout classes, directory policy, and resource hints where justified
  - clearer failure categories for blocked, denied, timed out, interrupted, and execution-error outcomes
  - richer command artifacts and summaries for debugging and replay triage
- Implementation notes:
  - do not weaken the current destructive-command blocking guarantees
  - keep envelopes reviewable and deterministic enough to remain compatible with replay and policy inspection
  - prefer bounded incremental hardening over a general sandbox rewrite
- Tests and validation included in task:
  - integration tests for timeout, interruption, blocked-command, and failure-summary behavior
  - regression tests for replay and artifact handling around hardened command outcomes
- Done when:
  - command tools behave more predictably and expose clearer safety and failure semantics than the current coarse command path alone

---

## Phase 29: Replay And Eval Developer Workflow v2

### GBX-340: Define Change-Impact Model For Replay And Eval Selection

- Status: `TODO`
- Depends on: `GBX-243`, `GBX-246`, `GBX-249`
- Goal: define how Glassbox should recommend the right replay or eval work after a code change instead of relying only on manual profile choice
- Deliverables:
  - architecture and workflow updates for change-to-capability and change-to-profile mapping
  - scope definition for heuristics based on touched files, known owning subsystems, and case metadata
  - explicit non-goals for the first version where confident impact analysis is not yet possible
- Implementation notes:
  - start from the existing eval profiles, coverage manifest, case capability metadata, and release-signoff workflow rather than inventing a second portfolio system
  - keep recommendations advisory unless the mapping becomes strong enough for tighter enforcement later
  - ground the model in repository-owned metadata and capability coverage rather than hidden machine-learned state
  - preserve the current named-profile operator model even if smarter recommendations are added
- Tests and validation included in task:
  - design review against current eval metadata, coverage manifests, and profile budgets before coding starts
  - manual validation that the proposed recommendations would help real workflow decisions without excessive noise
- Done when:
  - the repo has a concrete v2 contract for recommending replay and eval scope from a change set

### GBX-341: Implement Change-Impact Recommendations For Profiles And Cases

- Status: `TODO`
- Depends on: `GBX-340`
- Goal: help contributors answer what they should rerun after a change without reading the whole eval portfolio manually
- Deliverables:
  - CLI or report surface that recommends relevant replay or eval profiles and cases for a change set
  - mapping logic tied to case ownership metadata, capability coverage, and touched-code heuristics
  - explanation output for why a profile or case was recommended
- Implementation notes:
  - keep the first version explicit and inspectable; recommendations should show their reasoning rather than behaving like opaque magic
  - avoid pretending to produce a perfect minimal set when the evidence is weak
  - integrate with existing profile-driven workflows instead of creating a competing selection model
- Tests and validation included in task:
  - CLI integration tests for representative touched-file sets and recommendation output
  - regression tests for stable recommendation reasoning when case metadata evolves
- Done when:
  - Glassbox can recommend a practical replay or eval scope for common changes and explain why

### GBX-342: Improve Baseline Promotion, Refresh, And Review Ergonomics Further

- Status: `TODO`
- Depends on: `GBX-244`, `GBX-245`, `GBX-341`
- Goal: make evolving replay baselines feel more like deliberate interface maintenance and less like artifact churn
- Deliverables:
  - better review artifacts for case promotion and baseline refresh
  - stronger summaries of impacted capabilities, profiles, and likely change owners during refresh workflows
  - tighter guardrails for refreshing cases that participate in stricter profiles
- Implementation notes:
  - current promotion, refresh, and release-signoff outputs are the baseline; extend those review artifacts rather than replacing the workflow
  - build on the current guided workflow rather than replacing it
  - optimize for repository review and contributor comprehension, not only machine-readable output
  - preserve portability and redaction guarantees for refreshed artifacts
- Tests and validation included in task:
  - integration tests for enhanced promotion and refresh flows including metadata-rich review output
  - regression tests proving stricter-profile guardrails still fire as intended
- Done when:
  - a baseline update explains what changed, who likely cares, and what release surfaces are affected before it is accepted

### GBX-343: Add Release-Oriented Replay And Eval Workflow Surfaces For Daily Development

- Status: `TODO`
- Depends on: `GBX-247`, `GBX-341`, `GBX-342`
- Goal: connect the existing release-discipline model more tightly to everyday contributor workflows
- Deliverables:
  - clearer daily-use summaries that bridge local change impact, profile budgets, and release significance
  - compact CLI or artifact views showing how a change affects commit-time, push-time, and release-candidate verification surfaces
  - stronger linkage between failing cases and owning capabilities or release stages
- Implementation notes:
  - build on the existing deterministic profile tracks and `eval report` sign-off output rather than collapsing the current release workflow into a new command family
  - do not collapse the existing profile system into one monolithic release command
  - preserve the distinction between deterministic blocking profiles and advisory canary surfaces
  - favor concise, operator-usable summaries over more configuration complexity
- Tests and validation included in task:
  - CLI integration tests for mixed-stage summaries and impacted-profile output
  - regression tests for summary stability across profile and case metadata evolution
- Done when:
  - contributors can see how a code change affects replay or eval confidence across release stages without manual artifact archaeology

---

## Phase 30: Team Workflow And Portable Sessions

### GBX-350: Define Team-Oriented Session Ownership, Handoff, And Identity Model

- Status: `TODO`
- Depends on: `GBX-303`, `GBX-320`, `GBX-321`
- Goal: define how Glassbox should behave when more than one operator may inspect, resolve, or hand off work around the same persisted sessions
- Deliverables:
  - operator identity and session-ownership semantics for approvals, answers, and interventions
  - handoff model for paused or actionable sessions
  - scope boundary for collaboration features that remain intentionally out of scope for v2
- Implementation notes:
  - keep the model local-first and audit-friendly rather than inventing a full remote multi-user platform
  - make ownership and intervention explicit in events or associated metadata where they materially affect operator reasoning
  - preserve current single-operator workflows as the compatibility baseline
- Tests and validation included in task:
  - design review against current approval, answer, branching, and attach semantics before coding starts
  - manual validation that the proposed ownership model is useful without overbuilding multi-user infrastructure
- Done when:
  - the repo has a clear v2 contract for session ownership and operator handoff semantics

### GBX-351: Implement Portable Session Export For Review And Handoff

- Status: `TODO`
- Depends on: `GBX-313`, `GBX-350`
- Goal: let operators share a session for debugging, review, or handoff without exposing the whole local workspace database
- Deliverables:
  - portable session-export format distinct from full-workspace backup and replay bundle export
  - export command covering transcript, key metadata, lineage, and relevant retained artifacts where justified
  - redaction and portability rules for session-sharing workflows
- Implementation notes:
  - keep the exported package inspectable and intentionally scoped to operator handoff use cases
  - avoid conflating session export with the existing deterministic `replay-export` evidence path unless the workflows deliberately overlap
  - preserve local-path and secret redaction guarantees
- Tests and validation included in task:
  - integration tests for session export of representative live, paused, and branched sessions
  - regression tests proving the exported package remains free of forbidden runtime-only secrets or irrelevant workspace leakage
- Done when:
  - a session can be exported as a portable handoff artifact without moving the whole Glassbox workspace state

### GBX-352: Implement Session Import And Handoff Rehydration Flow

- Status: `TODO`
- Depends on: `GBX-351`
- Goal: let Glassbox reopen supported exported sessions for inspection or resumed work under clear, auditable rules
- Deliverables:
  - import workflow for supported portable session packages
  - explicit mapping for imported sessions into local session metadata and lineage state
  - operator-visible distinction between imported-for-inspection and imported-for-resumable-work semantics where needed
- Implementation notes:
  - keep import behavior explicit; do not silently merge imported state into existing sessions
  - preserve replayability and auditability of the imported session path
  - fail visibly for unsupported or ambiguous imported-session packages rather than partially reconstructing them
- Tests and validation included in task:
  - integration tests for export-import round trips into a clean workspace
  - negative-path tests for malformed, incompatible, or partially redacted session packages
- Done when:
  - Glassbox can import a supported portable session package into a clean workspace with clear semantics and without hidden state mutation

### GBX-353: Add Workspace Profiles For Common Runtime Defaults

- Status: `TODO`
- Depends on: `GBX-331`, `GBX-341`, `GBX-350`
- Goal: make common per-repository defaults for model selection, policy posture, and verification routing more reproducible
- Deliverables:
  - workspace-profile format for common local runtime defaults
  - precedence rules between explicit CLI flags, workspace profiles, and runtime-only environment configuration
  - operator guidance for profile use in daily workflows
- Implementation notes:
  - keep workspace profiles repository-owned and reviewable
  - do not let profiles hide risky behavior or override explicit operator input silently
  - align with the existing eval-profile and provider-config mental model where practical
- Tests and validation included in task:
  - unit and integration tests for profile parsing, precedence, and invalid configuration handling
  - regression tests proving explicit CLI flags still win over workspace defaults where intended
- Done when:
  - a repository can declare stable local Glassbox defaults without forcing contributors to memorize the preferred flag set

### GBX-354: Document Team Workflow, Handoff, And Workspace Defaults

- Status: `TODO`
- Depends on: `GBX-350`, `GBX-351`, `GBX-352`, `GBX-353`, `GBX-121`
- Goal: explain the v2 team-oriented workflow clearly without implying a cloud control plane or remote multi-tenant platform
- Deliverables:
  - README and operator-guide updates for session handoff, export or import, and workspace defaults
  - troubleshooting guidance for ownership conflicts, unsupported imports, and profile-precedence surprises
  - explicit scope notes for what collaboration features Glassbox still does not claim to support
- Implementation notes:
  - keep docs honest about the local-first and workspace-scoped operating model
  - align terminology across CLI, dashboard, and artifact formats
- Tests and validation included in task:
  - doc review against implemented ownership semantics, import or export commands, and workspace-profile resolution
  - manual verification of the documented handoff workflow against actual operator surfaces
- Done when:
  - a contributor can understand the supported team and handoff workflow from the docs alone

---

## Phase 31: Hardening, Performance, And v2 Release Polish

### GBX-360: Build Fault-Injection Matrix For Runtime, Store, And Transport Boundaries

- Status: `TODO`
- Depends on: `GBX-303`, `GBX-311`, `GBX-333`
- Goal: make v2 recovery guarantees credible by testing realistic interruption and corruption scenarios deliberately
- Deliverables:
  - fault-injection coverage for canonical append, projection update, artifact write, runtime transport, and reconnect boundaries
  - explicit recovery expectations per failure class
  - retained diagnostic artifacts or summaries for representative failure modes
- Implementation notes:
  - prioritize realistic local-use failures over synthetic platform chaos for its own sake
  - keep failure handling visible; do not hide partial-failure states to force a green-looking UX
  - use the existing event and artifact model to preserve debugging evidence where practical
- Tests and validation included in task:
  - integration tests for targeted injected failures and validated recovery outcomes
  - regression tests ensuring recovery tooling does not mutate canonical events incorrectly
- Done when:
  - v2 failure and recovery behavior is exercised through deliberate tests rather than inferred from happy-path architecture alone

### GBX-361: Add Performance Budgets For Large Sessions, Rebuilds, And Console Views

- Status: `TODO`
- Depends on: `GBX-311`, `GBX-322`, `GBX-360`
- Goal: keep Glassbox usable as sessions and retained histories grow beyond the scale of early v1 workflows
- Deliverables:
  - benchmark fixtures and budgets for larger event streams, projection rebuilds, session-index reads, and console rendering paths
  - targeted optimizations where the current architecture shows clear bottlenecks
  - operator-visible guidance when limits or degraded modes are hit
- Implementation notes:
  - optimize the highest-value bottlenecks first rather than prematurely redesigning storage or transport around hypothetical scale
  - preserve correctness and replayability as non-negotiable constraints on optimization work
  - keep budgets repository-owned and testable where possible
- Tests and validation included in task:
  - benchmark or performance-regression coverage for representative large-session scenarios
  - regression tests proving optimizations do not break replay, projections, or operator-visible summaries
- Done when:
  - the project has explicit, tested expectations for larger-session behavior and the main bottlenecks have a supported mitigation path

### GBX-362: Expand Observability For Runtime Health, Lag, And Verification Workflows

- Status: `TODO`
- Depends on: `GBX-304`, `GBX-321`, `GBX-343`, `GBX-360`
- Goal: give operators and contributors clearer runtime and verification diagnostics without making logs the main product interface
- Deliverables:
  - structured metrics or summaries for runtime health, projection lag, reconnect state, and verification activity
  - retained summaries that connect runtime incidents to the right recovery or inspection path
  - any necessary CLI or dashboard status refinements for observability-first troubleshooting
- Implementation notes:
  - logs complement persisted events and projections; they do not replace them
  - keep new observability surfaces tightly tied to concrete operator questions rather than generic telemetry accumulation
  - preserve the local-first product posture and avoid accidental dependency on external observability systems
- Tests and validation included in task:
  - integration tests for health-summary correctness and observability signal emission where practical
  - regression tests ensuring observability additions do not degrade startup or interactive workflows
- Done when:
  - Glassbox can answer what is unhealthy, what verification ran, and what to inspect next without forcing raw log spelunking as the first move

### GBX-363: Package And Document Glassbox v2 As A Coherent Release Candidate

- Status: `TODO`
- Depends on: `GBX-304`, `GBX-354`, `GBX-360`, `GBX-361`, `GBX-362`, `GBX-121`
- Goal: make the v2 milestone set coherent enough to ship as a clear product step rather than a loose pile of incremental changes
- Deliverables:
  - final packaging, help-text, and doc cleanup for the v2 feature set
  - architecture and operator-guide review for persistent runtime, recovery, console, policy, and workflow changes
  - release-readiness checklist or summary covering the supported v2 operating model
- Implementation notes:
  - keep polish grounded in real v2 workflow friction rather than cosmetic churn
  - ensure the final docs tell one coherent story about what v2 changed and what remains deliberately out of scope
  - preserve continuity with the current v1 baseline so contributors can understand the progression without reading every historical task
- Tests and validation included in task:
  - full repo validation using the standard command set plus the relevant v2 workflows
  - manual verification of the documented primary operator flows against the actual runtime and dashboard behavior
- Done when:
  - the repo is in a state where Glassbox v2 reads and behaves like a deliberate major step forward rather than an unfinished extension of v1

---

## Recommended Build Order For The First Usable v2 Vertical Slice

If an agent wants the fastest path to a demonstrable but architecturally correct v2 slice, the recommended order is:

1. `GBX-300` through `GBX-304`
2. `GBX-310` through `GBX-313`
3. `GBX-320` through `GBX-323`
4. `GBX-330` through `GBX-333`
5. `GBX-340` through `GBX-343`
6. `GBX-350` through `GBX-354`
7. `GBX-360` through `GBX-363`

That yields:

- a persistent runtime model
- safer long-lived workspace storage
- a stronger operator console
- more explainable tool governance
- a tighter replay and eval workflow for contributors
- clearer team handoff and workspace configuration semantics
- a coherent v2 release candidate

## Explicit Non-Goals For Initial v2 Execution

Do not spend time on these unless a later task introduces them explicitly:

- hosted cloud control planes
- remote multi-tenant orchestration
- broad autonomous repository indexing or hidden vector memory
- plugin marketplaces or general extension ecosystems
- browser-native code editing as a primary workflow
- weakening deterministic replay in order to mix live-provider behavior into blocking verification

## Success Criteria For Glassbox v2

Glassbox v2 is on track when all of the following are true:

- a session can remain live across terminal-process boundaries through a persistent runtime owner
- a workspace can survive schema evolution and derived-state recovery without manual SQLite intervention
- the dashboard can show actionable multi-session operational state, not only one-session inspection
- tool-policy decisions are more configurable and more explainable without becoming opaque
- contributors can identify a practical replay or eval scope for a change without reading the whole test portfolio manually
- sessions can be exported, handed off, and reopened through supported workflows with explicit semantics
- runtime failures, projection issues, and reconnect problems have tested recovery paths and operator-visible diagnostics
