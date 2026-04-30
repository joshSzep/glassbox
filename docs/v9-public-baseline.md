# Glassbox v9 Public Baseline

Glassbox v9 is the supported public baseline for the local-first Glassbox
operator workflow. It packages the v8 release-candidate decision into one
current product contract: Glassbox is a terminal-first local agent harness with
a co-hosted dashboard, event-sourced runtime state, approval-gated tools,
bounded autonomy, branchable history, workspace memory, repository
intelligence, and deterministic replay/eval evidence.

The baseline is still a conservative pre-1.0 contract. It is mature enough to
describe supported local workflows directly, but it does not claim hosted
availability, cloud authority, remote multi-user orchestration, or unattended
mutation outside explicit local policy and budgets.

## Product Model

Glassbox uses a small set of concepts across CLI, dashboard, docs, and release
evidence:

- **Session**: the durable conversation and action history for one operator
  workflow. Sessions are stored as canonical events and can be resumed,
  inspected, exported, imported for inspection, forked, replayed, and evaluated.
- **Task**: a durable plan or background continuation unit associated with
  session work. Tasks expose plan steps, state transitions, stop reasons,
  budget posture, and evidence for what the agent attempted.
- **Evidence**: the replay bundles, eval results, retained artifacts, command
  output, provider canary records, manual validation notes, and release summaries
  used to explain whether behavior is dependable. Deterministic replay/eval
  evidence is the release authority; live-provider evidence is advisory.
- **Memory**: operator-confirmed workspace notes and reviewable candidates that
  help future local work without turning hidden provider memory or vector
  retrieval into source of truth.
- **Branch**: a child session or bounded branch-search candidate derived from
  previous history. Branches support comparison and selection without mutating
  parent history automatically.
- **Verify**: explicit verification plans, command attempts, repair loops, eval
  recommendations, and release gates that make correctness claims inspectable.

## Supported Daily Workflows

These workflows are part of the v9 public baseline:

- start terminal work with `glassbox session chat --cwd .` or one-shot work with
  `glassbox session run`
- attach to a daemon-backed session, submit follow-up messages, answer
  `ask_user` prompts, approve or deny pending actions, cancel an active turn,
  and inspect session status
- use the dashboard as a paired cockpit for active sessions, pending decisions,
  transcript inspection, evidence cues, task state, memory, repository index
  posture, branch-search results, and recovery signals
- run local tool work behind policy, approval, cancellation, and autonomy-budget
  controls
- inspect durable task plans and enqueue bounded background task continuation
  jobs when the daemon owns the workspace runtime
- record, review, confirm, invalidate, prune, and apply workspace memory through
  explicit local state
- build and query the repository index as rebuildable derived state
- fork historical sessions and compare bounded branch-search candidates without
  automatic parent mutation
- inspect managed artifacts, backups, projections, observability status,
  provider diagnostics, performance budgets, and daemon state
- run replay, eval, eval recommendations, and release reports as local
  behavioral regression evidence

The command surface for this baseline is verified against
`uv run glassbox command tree`. The public model maps to the command groups
`session`, `task`, `branch-search`, `memory`, `repo index`, `replay`, `eval`,
`artifacts`, `backup`, `job`, `observability`, `provider`, `performance`,
`projection`, `dashboard`, and `daemon`.

## Advisory Workflows

The following workflows are useful operational guidance, but they do not replace
deterministic replay/eval or explicit operator approval:

- provider diagnostics, provider recommendations, and provider canary evidence
- live-provider confidence for longer autonomous work
- v8 autonomy eval cases that remain outside blocking release profiles until
  GBX-950 and GBX-951 classify and promote stable invariants
- dashboard cues that summarize stale provider evidence, stale repository
  indexes, artifact pressure, projection degradation, or daemon/job recovery
  posture
- eval recommendations for changed paths before the operator runs the selected
  checks

Advisory evidence should be current, redacted, and visible. It should never be
treated as hidden release authority.

## Release-Evidence Workflows

These workflows exist for contributors and release reviewers:

- `uv run glassbox eval run`
- `uv run glassbox eval audit`
- `uv run glassbox eval report ...`
- `uv run python scripts/validate_v8_release_gate.py`
- package validation with `uv build --wheel --sdist`
- installed-wheel smoke and package-content validation scripts
- retained manual validation under documented `.glassbox/releases/...` evidence
  directories

The v9 release gate does not exist until GBX-991. Until then, v8 gate evidence,
focused v9 task validation, and retained task-specific evidence are the
transition path.

## v8 Residual-Risk Mapping

The v8 release candidate accepted bounded residual risks rather than treating
the product as finished. v9 maps those risks into one of three outcomes:

| v8 residual-risk area | v9 handling |
| --- | --- |
| Public operator story spread across release history | Addressed by GBX-910, GBX-911, and GBX-922 through a baseline contract, docs hub split, and daily workflow quickstart. |
| Package version still reads `0.1.0` despite mature release evidence | Addressed by GBX-912 with an explicit version and release naming policy. |
| First-run uncertainty around provider, dashboard assets, writable state, and repository posture | Addressed by GBX-920 and GBX-921. |
| Command surface is broad and release-oriented | Addressed by GBX-930 through GBX-932 with vocabulary, workflow discovery, and de-emphasis guidance. |
| Dashboard requires too much correlation across panels | Addressed by GBX-940 through GBX-943 with cockpit priority, evidence drill-down, and recovery cues. |
| Stable autonomy behavior is partly advisory | Addressed by GBX-950 and GBX-951 through classification and deterministic-profile promotion. |
| Provider recommendations can be stale or overbroad | Addressed by GBX-960 through GBX-962 with freshness policy, recommendation refresh, and dashboard cues. |
| Repository index, artifacts, daemon, and job recovery need clearer next actions | Addressed by GBX-970 through GBX-972. |
| Real-use friction is not yet systematically fed back into tasks | Addressed by GBX-980 through GBX-982. |
| v9 release evidence is not yet unified | Addressed by GBX-990 through GBX-993. |

Accepted non-goals remain explicit: no hosted control plane, no cloud ownership
authority, no remote worker fleet, no simultaneous multi-writer mutation of one
workspace, no hidden provider-side memory, no automatic background mutation
without explicit budgets and stop reasons, and no replacement of deterministic
release authority with live-provider canaries.

## Version Contract

At the start of v9, `pyproject.toml` still declares `0.1.0`. GBX-910 does not
change package metadata. The v9 baseline decision is that Glassbox remains a
pre-1.0 local-first product while v9 clarifies adoption, release naming, and
evidence boundaries. GBX-912 owns the next version identifier and any package
metadata change.

## Reading Path

Operators should start with this baseline, then use:

- [getting-started.md](./getting-started.md) for installation and the first
  local session
- [interactive-workflows.md](./interactive-workflows.md) for terminal chat,
  attach, approvals, questions, cancellation, and session control
- [dashboard.md](./dashboard.md) for the co-hosted dashboard
- [providers.md](./providers.md) for optional live provider configuration
- [verification-loops.md](./verification-loops.md) and
  [replay-evals.md](./replay-evals.md) for verification and release evidence
- [v8-release-candidate.md](./v8-release-candidate.md) when historical release
  evidence or residual-risk context is needed
