# v7 Scale, Verification, Provider, And Adoption Inventory

This inventory records the code-aligned baseline for v7 adoption-and-scale work.
It identifies what validation already exists, which evidence is deterministic or
advisory, and which gaps should drive the first v7 implementation slices.

## Command Surface Baseline

`uv run glassbox command tree` currently exposes the expected local-first
workflow families:

- `session`: run, chat, list, attach, message, cancel, answer, approve, deny,
  resume, fork, status, export, and import
- `replay`: recorded-session replay and portable bundle export, inspect, and run
- `eval`: run, audit, profile list/show, recommend, report, case list/show,
  promote, and refresh
- `artifacts`: inspect and prune
- `backup`: create, inspect, and restore
- `observability`: status
- `provider`: diagnostics and canary run
- `performance`: budgets
- `projection`: check and rebuild
- `dashboard`: serve
- `daemon`: start, stop, and status

This command surface is broad enough for v7. The adoption work should improve
evidence, guidance, scale, and reliability around these commands rather than
adding a new top-level product surface by default.

## Deterministic Eval Portfolio

Repository-owned eval metadata currently lives in:

- `evals/cases/`
- `evals/bundles/`
- `evals/coverage.json`
- `evals/impact.json`
- `evals/profiles.json`

Current checked-in cases:

| Case | Current role |
| --- | --- |
| `smoke.hello` | deterministic smoke and replay portability coverage |
| `context.branch-inherited` | branch lineage and inherited context coverage |
| `context.artifact` | strict artifact-context drift coverage, advisory |
| `context.artifact-relaxed` | selected-invariant artifact-context coverage, advisory |
| `approval.approved-patch` | advisory approval request, approval resolution, and tool-resumption coverage |
| `ask-user.answer-resume` | advisory ask-user question, answer, and resumed-output coverage |
| `dashboard.action-approval` | advisory dashboard approval action mapped to canonical approval events |
| `dashboard.action-answer` | advisory dashboard answer action mapped to canonical question events |
| `daemon.attach-persisted-actions` | advisory daemon attach contract for persisted action history |
| `cancellation.cancelled-turn` | advisory cancelled-turn evidence |
| `cancellation.model-call` | advisory model-call-stage cancellation evidence |
| `cancellation.tool-execution` | advisory tool-execution cancellation evidence |
| `cancellation.repeated-request` | advisory repeated/reconnect-sensitive cancellation evidence |

Current profiles:

| Profile | Track | Blocking | Notes |
| --- | --- | --- | --- |
| `commit-smoke` | deterministic | yes | small smoke set for local pre-commit verification |
| `push-confirmation` | deterministic | yes | smoke confirmation after push |
| `release-candidate` | deterministic | yes | release-signoff deterministic suite |
| `advisory-context` | deterministic | no | context-heavy exploratory drift review |
| `live-provider-canary` | live-provider-canary | no | advisory scaffold kept out of deterministic signoff |

Current release-critical coverage is strongest for smoke validation, replay
portability, branching, and context inheritance. Current advisory or weak areas:

- `approval_flow` now has advisory deterministic coverage for approved
  `apply_patch` resumption through `approval.approved-patch`; denial-specific
  and dashboard-specific resolution behavior remains integration evidence
- `ask_user_flow` now has advisory deterministic coverage for persisted
  question, answer, and resumed assistant output through `ask-user.answer-resume`;
  operator timing and UI-specific validation remain integration evidence
- `cancellation` now has advisory multi-case coverage for model-call,
  tool-execution, and repeated/reconnect-sensitive local cancellation evidence;
  provider remote-computation stop behavior and live socket timing remain outside
  deterministic replay
- dashboard-originated approval and answer actions now have advisory
  deterministic coverage where replay can represent canonical events; explicit
  action-origin metadata is not persisted, so live dashboard route behavior stays
  focused integration and frontend evidence
- daemon attach now has advisory deterministic coverage for the persisted event
  history used after attach or reconnect; live process health, socket behavior,
  and stale-owner recovery remain integration and release-smoke evidence

Recommended v7 action: prioritize `GBX-720`, `GBX-721`, `GBX-722`, and
`GBX-723`, then update profiles and coverage in `GBX-724`.

## Provider Diagnostics And Canary Evidence

Provider documentation currently names OpenAI and Anthropic model prefixes,
runtime-only credentials, optional `.env` loading, redacted diagnostics, and
advisory provider canaries.

Current provider commands:

- `glassbox provider diagnostics`
- `glassbox provider canary run`

Current canary behavior is advisory by design. The v6 release candidate retained
one `streaming-text` OpenAI canary scenario, while deterministic evals remained
the release authority.

Current strengths:

- provider secrets are runtime-only and not persisted in sessions, events,
  projections, or release evidence
- missing or partial provider config is surfaced before unexpected remote use
- provider canary skips are allowed when credentials are unavailable, provided a
  reason is retained

Current weak areas:

- provider capability evidence is scenario-limited
- there is no durable matrix comparing provider family, model, scenario,
  credential state, result, and redaction status
- diagnostics do not yet preflight every canary scenario
- provider evidence is not yet surfaced as a reusable operator artifact outside
  a single retained release run

Recommended v7 action: define the matrix in `GBX-730`, expand diagnostics in
`GBX-731`, broaden scenario execution in `GBX-732`, and surface retained matrix
evidence in `GBX-733`.

## Larger-Session Read Paths

Current read paths include full session snapshots, session aggregate reads,
session event replay through SSE, projection checks and rebuilds, artifact
inspection, and dashboard inspector panes for transcript, timeline, metrics,
evidence, lineage, compare, runtime, and raw events.

Current strengths:

- canonical events remain authoritative
- projection tables make common dashboard and CLI reads cheaper than raw replay
- SSE reconnect uses persisted event history as the recovery path
- `glassbox performance budgets` exists as a command surface for larger-session
  expectations
- v6 package and dashboard smoke prove the static dashboard can load from an
  installed wheel

Current weak areas:

- full snapshots can become too heavy for long transcripts and large event logs
- raw event and transcript dashboard panes do not yet have a documented
  pagination or virtualization contract
- artifact pressure and projection rebuild cost are observable, but not yet tied
  to v7 scale budgets or release validation
- installed-package dashboard smoke is intentionally short and does not exercise
  deep large-session states

Recommended v7 action: measure first in `GBX-740`, add typed paginated APIs in
`GBX-741`, add dashboard lazy loading and virtualization in `GBX-742`, improve
projection and artifact observability in `GBX-743`, and gate the resulting scale
expectations in `GBX-744`.

## Daemon, Transport, And Multi-Observer Evidence

Current daemon and transport behavior includes:

- `glassbox daemon start|status|stop`
- foreground chat or daemon as the single workspace mutation owner
- `glassbox session attach` against healthy daemon-owned sessions or local
  persisted sessions
- SSE streams at `/sessions/{session_id}/events` with `after` sequence cursors
- in-process live transport with observable counters and persisted replay as the
  recovery authority

Current strengths:

- v6 focused transport and daemon tests exist
- installed daemon status/start/status/stop smoke is part of the v6 gate
- daemon status reports workspace metadata, health, and suggested next actions
- persisted events recover missed live delivery after reconnect
- `daemon.attach-persisted-actions` protects the replay-representable persisted
  event history that attach and reconnect flows consume after live ownership
  changes

Current weak areas:

- multi-observer behavior is supported by the architecture but not yet promoted
  into a product-level validation surface
- daemon attach and stale-owner recovery can be made clearer for local process
  churn and port conflicts
- transport turbulence evidence should cover slow subscribers, dropped queues,
  duplicate suppression, daemon stop, dashboard refresh, and retry exhaustion

Recommended v7 action: define the contract in `GBX-750`, add turbulence tests in
`GBX-751`, harden daemon attach and stale-owner recovery in `GBX-752`, and add
multi-observer smoke in `GBX-753`.

## Tool Policy And Approval Governance

Current policy behavior is documented in [tool-policy.md](./tool-policy.md) and
implemented around local risk buckets, hard runtime invariants, repository-owned
policy rules, and session approval modes.

Current strengths:

- path escape and destructive command blocks are hard invariants
- risky writes and commands are approval-gated unless approval mode blocks them
- `ask_user` is explicitly separated from approval semantics
- `approval.approved-patch` protects the persisted approval request, approval
  decision, resumed tool execution, and completed assistant-output event contract
- `ask-user.answer-resume` protects persisted operator questions, answers, and
  answer-aware resumed assistant output without treating operator timing as a
  deterministic replay invariant
- policy outcomes carry source, risk, and reason fields in current event payloads
  for tool-related events
- CLI and dashboard approval workflows are already implemented

Current weak areas:

- policy governance needs a v7-level fixture and validation story for teams
- rule precedence and explanations can be clearer at the moment an operator must
  approve or interpret a block
- policy changes are not yet strongly connected to eval recommendation metadata
- dashboard and terminal UX can distinguish invariant block, denied action,
  approval-worthy risk, and advisory evidence more clearly

Recommended v7 action: define policy governance in `GBX-760`, add explanation
and trace evidence in `GBX-761`, add fixtures and eval recommendations in
`GBX-762`, and improve approval or blocked-action UX in `GBX-763`.

## Accessibility Evidence

Current v6 manual evidence covers terminal sizes, dashboard viewports, keyboard
workflows, screenshot archive results, and explicit claims and non-claims.

Current strengths:

- terminal and dashboard manual reviews found no blocking issue for v6
- dashboard e2e and screenshot workflows cover representative responsive states
- docs do not overclaim formal certification

Current weak areas:

- no named assistive-technology pairing is part of the release contract yet
- terminal emulator variance and browser/screen-reader variance remain outside
  the current evidence boundary

Recommended v7 action: add named pairing reviews in `GBX-780` before making any
stronger public accessibility claim.

## Onboarding And Packaging

Current onboarding and packaging paths include:

- root README and getting-started docs
- provider setup and diagnostics docs
- workspace profile docs
- release packaging docs
- package content validation
- installed terminal, daemon, dashboard, and eval smoke in the v6 gate

Current strengths:

- runtime users should not need Node.js
- source builders have documented `uv`, `pnpm`, generated API, and static asset
  workflows
- package validation checks dashboard assets, console script, runtime modules,
  and `textual` dependency metadata

Current weak areas:

- first-run provider and profile guidance is spread across multiple docs
- installed-package smoke is intentionally short
- source-builder stale asset and generated API guidance could be more visible
- example profile snippets could reduce first-session friction

Recommended v7 action: improve first-run provider and profile onboarding in
`GBX-781`, harden installed-package and source-builder onboarding in `GBX-782`,
then include those expectations in `GBX-783` through `GBX-785`.

## Recommended v7 Gate Membership

The eventual v7 gate should include all v6 deterministic stages plus focused
coverage for:

- expanded deterministic eval cases and `eval audit`
- release-signoff report generation
- larger-session read API and dashboard scale smoke
- transport turbulence and daemon stale-owner recovery
- policy fixture and explanation tests
- dashboard evidence cue tests
- onboarding and package smoke

Provider capability matrix runs should remain advisory by default, with retained
redacted evidence or explicit skip reasons.

## Summary Of Weak Or Missing Coverage

| Area | Current coverage | v7 gap |
| --- | --- | --- |
| Approval eval | advisory deterministic approval case plus integration workflow evidence | denial and live dashboard resolution remain integration-focused |
| Ask-user eval | advisory deterministic answer-resume case plus integration workflow evidence | operator timing and UI validation remain integration-focused |
| Cancellation variants | advisory multi-case replay coverage for model-call, tool-execution, and repeated/reconnect-sensitive evidence | provider remote-computation stop behavior and live socket timing remain advisory or integration evidence |
| Provider canaries | diagnostics plus limited advisory scenarios | no capability matrix or broad scenario set |
| Large sessions | performance command and ordinary snapshot/dashboard tests | no measured pagination, virtualization, or large-session gate |
| Daemon and dashboard actions | advisory replay cases for persisted event semantics plus web/daemon tests | no deterministic action-origin metadata or live process lifecycle replay |
| Multi-observer transport | SSE and daemon tests | no explicit multiple-observer product smoke |
| Policy governance | policy docs and tests | limited fixtures, explanations, and eval recommendation mapping |
| Dashboard evidence | inspector panes and verification cues | branch compare, metrics, policy, eval, and provider evidence can be more analytical |
| Accessibility | v6 manual review and keyboard tests | no named assistive-technology pairings |
| Onboarding | README, getting started, providers, packaging | first-run provider/profile path remains scattered |

## Related Files

- [tasks-v7.md](./tasks-v7.md)
- [v7-adoption-scale-contract.md](./v7-adoption-scale-contract.md)
- [replay-evals.md](./replay-evals.md)
- [providers.md](./providers.md)
- [tool-policy.md](./tool-policy.md)
- [persistent-runtime.md](./persistent-runtime.md)
- [release-packaging.md](./release-packaging.md)
- [v6-release-candidate.md](./v6-release-candidate.md)
