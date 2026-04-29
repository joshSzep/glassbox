# v8 Autonomy Baseline Inventory

This inventory records the code-aligned baseline for v8 auditable-autonomy work. It identifies where Glassbox is already agentic, where it is intentionally conservative, which boundaries are hard safety invariants, and which conservative choices can be loosened through events, projections, budgets, CLI/API surfaces, and dashboard evidence.

Pair this inventory with [v8-auditable-autonomy-contract.md](./v8-auditable-autonomy-contract.md) and [tasks-v8.md](./tasks-v8.md). The contract defines the milestone boundary. This file explains the current implementation posture that Phase 82 and later phases should evolve.

## Command Surface Baseline

`uv run glassbox command tree` currently exposes the local-first workflow families that v8 should preserve:

- `session`: run, chat, list, attach, message, cancel, answer, approve, deny, resume, fork, status, export, and import
- `replay`: recorded-session replay and portable bundle export, inspect, and run
- `eval`: run, audit, profile list/show, recommend, report, case list/show, promote, and refresh
- `artifacts`: inspect and prune
- `backup`: create, inspect, and restore
- `observability`: status
- `provider`: diagnostics and canary run
- `performance`: budgets
- `projection`: check and rebuild
- `dashboard`: serve
- `daemon`: start, stop, and status

This surface is broad enough for v8 to become more autonomous without adding a hosted control plane. The missing surfaces are not general-purpose remote control. They are local task, autonomy, job, memory, repository-index, verification-loop, branch-search, and provider-recommendation surfaces that should remain scriptable and event-backed.

Expected new command families or subcommands should be introduced only when they map to durable runtime state:

- `task` for plan and step inspection, event history, export/import awareness, continuation, pause, resume, and cancellation
- `autonomy` for mode and budget profile inspection
- `job` for background queue inspection, cancellation, retry, and abandonment
- `memory` for workspace memory list/show/confirm/invalidate/prune
- `repo index` for repository intelligence build/status/search/show
- branch-search commands for listing candidate attempts, comparing outcomes, and selecting a candidate
- provider recommendation commands or diagnostics sections for model/workflow fit

## Turn Execution, Suspension, And Resumption

The current live turn flow is orchestrated by `src/glassbox/runtime/turn_engine.py`. `TurnEngine` prepares a turn, builds runtime context, runs the model/tool loop, persists events, and records completion, suspension, failure, or cancellation outcomes. `src/glassbox/runtime/model_loop.py` drives model streaming and tool-call iterations. `src/glassbox/runtime/turn_tool_executor.py` evaluates and executes tool calls through the registry and policy layer.

Current agentic strengths:

- model turns can call tools and continue after tool results
- approval requests suspend the turn and resume after operator approval or denial
- `ask_user` questions suspend the turn and resume after an operator answer
- cancellation is event-backed and checked at cooperative boundaries
- replay capture can retain model calls, tool calls, tool outputs, artifacts, and enriched-context metadata
- runtime context is assembled before model calls rather than hidden inside provider state

Current conservative gaps:

- plan-like behavior is only prose in assistant output or implicit in tool-call order
- there is no durable task object, plan object, step object, or blocked reason independent of transcript text
- the model can propose work, but the runtime does not own a queryable plan lifecycle
- resumed approval and answer paths are turn-scoped, not task-step-scoped
- verification is a tool or eval workflow, not a task-local verify-repair loop with budgeted attempts

v8 implication: Phase 82 should add task-plan events and projections before changing autonomous execution. Later continuation and verification loops should run one bounded step at a time so existing suspension, cancellation, policy, and replay semantics remain useful.

## Approval, Command, Policy, And Budget Gates

The current policy model is implemented in `src/glassbox/tools/policy.py` and described in [tool-policy.md](./tool-policy.md). Tools are described by `src/glassbox/tools/registry.py` with coarse risk buckets: `read_only`, `workspace_write`, and `command`.

Hard boundaries that should remain hard in v8:

- path arguments resolving outside the workspace are blocked
- destructive command patterns are blocked rather than approval-gated
- approval mode `never` blocks risky actions instead of pausing for approval
- policy decisions are recorded as evidence and should remain exportable and replay-aware
- repository policy cannot bypass runtime invariants

Current conservative choices that can be loosened safely:

- `confirm`, `review`, and `on-request` are persisted separately but behave similarly at practical approval gates
- safe command and write workflows cannot consume typed budgets because autonomy budgets do not exist yet
- repository-owned policy can express tool rules, but it cannot yet express autonomy-safe budgets or verification requirements
- policy evidence explains one decision at a time, not the remaining autonomy posture for a task

v8 implication: Phase 83 should add typed autonomy modes and budget evidence before loosening approval behavior. Approval-mode calibration should be a policy evolution, not a prompt convention.

## Cancellation And Stop Conditions

Cancellation is a real persisted runtime concept. `src/glassbox/runtime/cancellation.py` and `TurnEngine.request_turn_cancellation` support cooperative cancellation. CLI and web surfaces route cancellation through session state rather than killing local state blindly. Replay/eval behavior distinguishes intentional cancellation from generic failure.

Current strengths:

- cancellation requests are recorded as durable evidence
- running turns check for cancellation at model/tool boundaries
- cancellation survives dashboard and terminal control paths
- replay and eval can normalize cancellation as its own outcome class

Current gaps for autonomy:

- cancellation is turn-oriented, not yet task-step-oriented or background-job-oriented
- there are no pause/resume/cancel events for durable task plans
- daemon background work has no job-level cancellation or heartbeat contract
- budget exhaustion is not yet a first-class stop reason

v8 implication: task execution, background jobs, verify-repair loops, branch attempts, and dashboard controls should reuse the cancellation posture but add task, job, and budget stop evidence.

## Daemon, Ownership, Attach, And Background-Worker Seams

The daemon model is implemented in `src/glassbox/runtime/daemon.py`. A foreground `session chat` process or `glassbox daemon start` owns live mutation for one workspace. Owner metadata lives under `.glassbox/runtime-owner.json`, and stale-owner handling treats local owner state as the authority. `src/glassbox/cli/daemon_attach.py` attaches through existing web snapshot and SSE routes instead of opening a second control plane.

Current strengths:

- one local mutation owner per workspace is enforced
- local observers can attach to daemon-owned sessions
- daemon status exposes process, port, database, dashboard URL, and stale-owner cues
- attach and dashboard live transport both rely on persisted session events for recovery
- daemon ownership already provides the natural local process that could run opt-in work

Current gaps:

- there is no background job module, queue projection, claim event, heartbeat event, retry policy, or job failure triage
- daemon maintenance work is not represented as durable local jobs
- task continuation cannot be scheduled as a daemon-owned bounded job
- observability cannot yet report pending, running, stale, failed, retryable, or abandoned jobs

v8 implication: Phase 84 should introduce background jobs as data before using the daemon to continue mutating work. Read-only maintenance jobs should land before task continuation jobs.

## Runtime Context, Notes, Working Set, And Memory Limits

[runtime-context.md](./runtime-context.md) describes the current enriched-context model. The implementation spans `src/glassbox/runtime/context_builder.py`, `src/glassbox/runtime/context_working_set.py`, `src/glassbox/runtime/context_snapshots.py`, `src/glassbox/runtime/replay_fingerprints.py`, and runtime-note projections in `src/glassbox/store/sqlite_projection_runtime_notes.py`.

Current strengths:

- repository context gives bounded workspace orientation
- runtime notes are event-backed, session-scoped, inspectable, and inherited across forks/imports when appropriate
- working-set context summarizes recent local focus such as approvals, tool activity, artifacts, tests, and branch lineage
- artifact-backed summaries can carry expensive derived context with freshness semantics
- replay fingerprints can report enriched-context drift

Current gaps:

- runtime notes are not a durable workspace memory layer
- there is no memory entry lifecycle for confirmed, stale, invalidated, imported, used, or pruned facts
- memory cannot be curated through explicit CLI or dashboard workflows
- prompt-use evidence exists for enriched context, but not for workspace memory provenance and freshness
- automatic memory candidate extraction does not exist

v8 implication: Phase 85 should add memory as explicit local state with provenance and review gates. Memory should influence prompts only when usage is recorded and replay/eval can explain drift.

## Repository Context And Code-Inspection Limits

Repository context currently provides bounded orientation, not a local code-intelligence index. Agents inspect code through read-only tools, command tools, dashboard evidence, and repository docs. The current context is intentionally shallow to keep prompt assembly deterministic and cheap.

Current strengths:

- bounded top-level workspace signals avoid uncontrolled repository crawling
- tool policy keeps read-only inspection distinct from writes and commands
- eval recommendation can map paths and profiles to verification suggestions
- docs, tests, and package metadata already describe important project boundaries

Current gaps:

- no rebuildable repository index exists for files, symbols, tests, docs, commands, eval cases, ownership hints, or recently active paths
- agents rediscover project layout and likely tests through repeated reads/searches
- repository freshness and ignored/generated-file policy are not represented as index metadata
- there is no background index refresh job or stale-index warning
- prompt context cannot cite repository-index provenance because the index does not exist yet

v8 implication: repository intelligence should start with deterministic static signals and explicit freshness metadata. It should degrade to the existing bounded repository context when absent or stale.

## Branching, Replay, Eval, And Verification Flows

Branching and replay are strong foundations for v8. `SessionSupervisor.fork_session` in `src/glassbox/runtime/supervisor.py` creates child sessions without mutating parent history. Replay and eval modules under `src/glassbox/runtime/replay*.py` and `src/glassbox/runtime/eval*.py` preserve deterministic regression authority. Eval recommendation code maps changed paths to relevant cases and profiles.

Current strengths:

- sessions can be forked from historical state
- imported runtime notes and lineage are visible in child sessions
- replay bundles and eval cases provide portable regression evidence
- replay triage can classify drift instead of flattening all changes into transcript mismatch
- `eval recommend` can explain relevant deterministic cases for changed paths
- `eval report` and release gates already produce retained signoff evidence

Current gaps:

- branch search is not a first-class strategy-search object
- candidate branches do not have durable strategy labels, verification plans, comparison summaries, or selection metadata
- eval recommendations are advisory output, not executable verification plans under budgets
- verify-repair loops do not yet connect task steps, tool calls, command output, artifacts, repair attempts, and reruns
- replay drift explanations do not yet cover task plans, budgets, memory, repository index, branch-search attempts, or verification loops

v8 implication: Phase 86 should extend the existing fork/replay/eval strengths rather than inventing a separate experimentation system. Branch search should never automatically merge candidates into parent history.

## Dashboard And Web Control Surfaces

The web surface already supports session snapshots, session aggregates, event tails, approval resolution, answer submission, cancellation, transcript/detail pages, policy evidence, verification cues, and larger-session inspection affordances through routes under `src/glassbox/web/routes/` and frontend components under `frontend/components/console/`.

Current strengths:

- dashboard state is backed by backend snapshots and typed API shapes
- SSE reconnect is sequence-based and backed by persisted events
- approval and answer actions route through backend authority
- dashboard panes can show transcript, timeline, metrics, evidence, lineage, comparison, runtime context, policy evidence, provider cues, and raw events
- larger-session panes use paginated reads for expensive details

Current gaps:

- no task queue, plan inspector, step timeline, or task event history exists
- no budget controls or autonomy-mode posture appear in session snapshots
- no background job queue, job detail, retry, or cancellation surface exists
- no workspace memory inspector or repository index inspector exists
- no branch-search comparison or candidate-selection UI exists
- no why-this-action pane ties plan steps, policy, budgets, memory/index context, verification, and provider readiness into one explanation

v8 implication: Phase 88 should keep the dashboard an operator console, not a marketing page. New controls should call backend APIs and treat the browser as presentation, never authority.

## Provider Diagnostics, Canaries, And Model Readiness

Provider diagnostics and advisory canaries currently live under runtime provider modules such as `src/glassbox/runtime/provider_diagnostics.py`, `src/glassbox/runtime/provider_canary.py`, and `src/glassbox/runtime/provider_capability_matrix.py`. Provider docs describe OpenAI and Anthropic credential handling, local fallback, redacted evidence, and advisory canary behavior.

Current strengths:

- provider credentials are runtime-only and redacted from retained evidence
- missing credentials produce explicit diagnostics rather than surprising remote use
- provider canary skips are recorded and non-blocking by default
- deterministic evals remain release authority
- v7 evidence already records streaming-text advisory success and preflight-only workflow gaps

Current gaps:

- canary scenarios are still shallow for agentic workflows
- tool-call reliability, malformed tool calls, long-context continuity, retry behavior, rate-limit behavior, cancellation during retry, and multi-step plan following are not deeply covered
- provider evidence does not yet drive task-kind recommendations for model selection
- dashboard/provider cues are advisory, not integrated into autonomy posture

v8 implication: Phase 87 should deepen provider evidence for workflow fit, but provider canaries should remain advisory unless future release policy explicitly promotes a stable scenario.

## Conservative Bottlenecks And Safe Loosening Opportunities

Hard safety boundaries:

- one mutation owner per workspace
- canonical events as source of truth
- rebuildable projections as derived state
- workspace path containment
- destructive command blocks
- explicit approval or blocking for risky actions under current policy
- local-first state and credentials
- deterministic replay/eval release authority
- plain terminal fallback

Safe loosening opportunities:

- persist plan proposals as task-plan events rather than leaving them in assistant prose
- add typed autonomy budgets before allowing more work to proceed without interruption
- let repository-owned safe-autonomy rules allow known local workflows with budget and verification evidence
- let the daemon run read-only maintenance jobs before task continuation jobs
- make task continuation opt-in and one-step-at-a-time so stops remain responsive
- convert eval recommendations into optional verification plans under budget
- promote confirmed session facts into workspace memory with provenance and invalidation
- build a deterministic repository index instead of repeatedly rediscovering project shape
- use branch forks as bounded candidate attempts with comparison evidence
- enrich provider canaries for workflow choice without changing release authority

## Implementation Surface Classification

The v8 gaps split into four implementation classes:

| Class | Examples | Why it matters |
| --- | --- | --- |
| Canonical events | task/step lifecycle, budget decisions, job lifecycle, memory lifecycle, verification attempts, branch-search attempts | durable authority, replay, export/import, eval drift |
| Projections | task summaries, step lists, job queues, memory entries, repository-index status, branch-search comparisons | efficient CLI, web, dashboard, observability reads |
| CLI/API surfaces | task list/show/events, autonomy profile, job list/show/cancel/retry, memory list/show/confirm/invalidate, repo index status/search, branch search list/select | scriptable operation and dashboard authority |
| Dashboard presentation | task console, budget controls, job queue, memory/index inspectors, branch comparison, why-this-action pane | operator control and explanation |

Dashboard-only state should not become product authority. Anything that changes autonomous behavior should land in canonical events or typed backend state first.

## Summary Of Weak Or Missing Coverage

The biggest v8 gaps are:

- no durable task-plan object
- no autonomy budget engine
- no calibrated approval behavior beyond current coarse gates
- no background job queue or daemon job runner
- no workspace memory lifecycle
- no rebuildable repository intelligence index
- no verify-repair loop coordinator
- no branch-search attempt model
- no dashboard autonomy console
- limited provider canary depth for agentic workflows
- no v8 release gate that proves bounded autonomy, recovery, packaging, manual review, and dashboard usability together

These gaps are product conservatism rather than architectural dead ends. The v7 runtime already has the right spine: canonical events, projections, local daemon ownership, replay/eval authority, policy evidence, live transport, and dashboard inspection. v8 should evolve that spine deliberately instead of bypassing it.

## Related Files

- [v8-auditable-autonomy-contract.md](./v8-auditable-autonomy-contract.md)
- [tasks-v8.md](./tasks-v8.md)
- [architecture.md](./architecture.md)
- [database.md](./database.md)
- [runtime-context.md](./runtime-context.md)
- [tool-policy.md](./tool-policy.md)
- [persistent-runtime.md](./persistent-runtime.md)
- [branching.md](./branching.md)
- [replay-evals.md](./replay-evals.md)
- [providers.md](./providers.md)
- [dashboard.md](./dashboard.md)
- [v7-scale-verification-inventory.md](./v7-scale-verification-inventory.md)
