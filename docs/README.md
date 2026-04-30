# Glassbox Documentation

Glassbox has two documentation layers:

- the root [README.md](../README.md) is the landing page and shortest product
  overview
- the files in `docs/` carry operator guides, reference material, release
  evidence, and implementation history

Use this page by audience. Start with the current v9 baseline for the product
story, then follow the daily workflow guides before diving into release
evidence or milestone history.

## Start Here

- [v9-public-baseline.md](./v9-public-baseline.md): current supported Glassbox
  product contract, core model, daily workflows, advisory posture,
  release-evidence split, residual-risk mapping, and pre-1.0 version posture
- [v9-vocabulary.md](./v9-vocabulary.md): shared v9 language for sessions,
  tasks, evidence, memory, branches, verification, providers, daemons, and
  projections, plus command/dashboard copy review and compatibility policy
- [v9-command-surface-review.md](./v9-command-surface-review.md): v9 inventory
  and de-emphasis plan for daily, advanced, recovery, maintenance, and
  release-evidence command/dashboard surfaces
- [dashboard-cockpit-contract.md](./dashboard-cockpit-contract.md): v9
  dashboard cockpit information architecture, priority rules, responsive and
  keyboard expectations, data-source map, and follow-on task boundaries
- [operator-quickstart.md](./operator-quickstart.md): short happy path for
  install, provider setup, terminal chat, dashboard inspection, approvals, and
  verification
- [getting-started.md](./getting-started.md): full repository setup, first
  session details, local workspace layout, command inventory, and validation
  commands
- [providers.md](./providers.md): optional OpenAI or Anthropic provider
  configuration, diagnostics, canaries, freshness states, and redaction posture
- [dogfooding.md](./dogfooding.md): real-repository dogfooding protocol,
  evidence template, redaction rules, and finding-disposition policy

## Daily Workflows

- [interactive-workflows.md](./interactive-workflows.md): use
  `glassbox session chat`, `attach`, `message`, `answer`, `approve`, `deny`,
  `resume`, and `status`
- [daily-workflow-quickstart.md](./daily-workflow-quickstart.md): run the
  ordinary daily loop for readiness, chat, dashboard inspection, actions,
  cancellation, forking, verification, memory/index work, and recovery
- [dashboard.md](./dashboard.md): use the co-hosted dashboard as the paired
  operator console for terminal chat or run the standalone dashboard server
- [dashboard-cockpit-contract.md](./dashboard-cockpit-contract.md): understand
  the v9 workspace-attention, active-session, task, evidence, memory/index,
  branch, recovery, priority, responsive, and keyboard contract
- [task-plans.md](./task-plans.md): inspect durable task plans, plan steps,
  state transitions, and task evidence
- [verification-loops.md](./verification-loops.md): operate explicit,
  budgeted verification checks and verify-repair loops
- [branching.md](./branching.md): inspect historical sessions, create child
  branches, and understand lineage fields
- [branch-search.md](./branch-search.md): compare bounded branch-search
  candidates without mutating parent session history
- [workspace-memory.md](./workspace-memory.md): review, confirm, invalidate,
  and prune local workspace memory
- [repository-intelligence-index.md](./repository-intelligence-index.md): build,
  inspect, and refresh rebuildable local repository intelligence
- [background-jobs.md](./background-jobs.md): inspect and recover daemon-owned
  background work
- [workspace-profiles.md](./workspace-profiles.md): declare repository-owned
  defaults for model selection, approval posture, and eval profile routing
- [tool-policy.md](./tool-policy.md): understand risk buckets, approval gating,
  blocked commands, and `ask_user` semantics
- [team-workflows.md](./team-workflows.md): plan local-first session custody,
  intervention attribution, and handoff

## Reference

- [architecture.md](./architecture.md): runtime, bootstrap, store, CLI, web,
  replay, and eval ownership boundaries
- [database.md](./database.md): SQLite event store, projection tables, artifact
  storage, branching lineage fields, and store implementation map
- [runtime-context.md](./runtime-context.md): repository context, runtime
  notes, working-set context, and artifact-backed summaries
- [replay-evals.md](./replay-evals.md): replay historical sessions, export
  bundles, run eval suites, and work through local-first regression gates
- [release-packaging.md](./release-packaging.md): build and validate release
  packages with the statically exported dashboard
- [version-release-policy.md](./version-release-policy.md): align package
  version metadata, release-candidate names, evidence directories, installed
  smoke, and future v9 release notes
- [v9-vocabulary.md](./v9-vocabulary.md): standardize operator-facing product
  terms and command/dashboard language for v9
- [v9-command-surface-review.md](./v9-command-surface-review.md): classify the
  command tree and dashboard panels by daily, advanced, recovery, maintenance,
  and release-evidence use
- [persistent-runtime.md](./persistent-runtime.md): operate the daemon-backed
  workspace runtime and troubleshoot attach or health states
- [operator-console.md](./operator-console.md): understand the v2 multi-session
  console model, action queues, runtime-health semantics, and backend/frontend
  contracts
- [dashboard-cockpit-contract.md](./dashboard-cockpit-contract.md): v9
  dashboard cockpit contract that maps operator-priority surfaces to typed API
  responses and frontend stores/components
- [autonomy-console.md](./autonomy-console.md): inspect autonomy state,
  budgets, and dashboard controls
- [frontend-development.md](./frontend-development.md): run the Next.js SPA
  with FastAPI during local development and verify the static production path
- [frontend-testing.md](./frontend-testing.md): write frontend unit, transport,
  store, and React component tests
- [dashboard-frontend-boundaries.md](./dashboard-frontend-boundaries.md):
  frontend boundary map and SPA supersession notes
- [refactor-boundaries.md](./refactor-boundaries.md): module ownership and
  dependency-direction guardrails
- [tool-expansion-v8.md](./tool-expansion-v8.md): structured local tool
  expansion contract and non-goals
- [network-browser-diagnostics-v8.md](./network-browser-diagnostics-v8.md):
  local-only network/browser diagnostic contract and policy gates
- [dogfooding.md](./dogfooding.md): protocol for turning real repository use
  into sanitized v9 findings, docs fixes, eval candidates, or residual risks

## Release Evidence

Use this section when preparing, reviewing, or auditing release-candidate
claims. Release evidence is intentionally separate from the daily operator
path.

- [v8-release-candidate.md](./v8-release-candidate.md): v8 operating model,
  final evidence summary, non-goals, residual risks, and GO decision
- [v8-release-gate.md](./v8-release-gate.md): v8 automated gate command,
  stage map, advisory provider-canary policy, autonomy boundedness summary,
  installed smoke inheritance, evidence summary, and pass/fail policy
- [manual-v8-release-validation.md](./manual-v8-release-validation.md): retained
  GBX-894 v8 manual validation pass, focused command results, recovery
  evidence, provider recommendation, and residual risks
- [manual-qa-evidence-v8.md](./manual-qa-evidence-v8.md): v8 manual evidence
  directory convention, autonomy workflow manifest, accessibility pairing
  manifest, retention policy, and redaction rules
- [background-autonomy-release-smoke-v8.md](./background-autonomy-release-smoke-v8.md):
  v8 background autonomy smoke evidence path and expectations
- [v8-auditable-autonomy-contract.md](./v8-auditable-autonomy-contract.md): v8
  auditable-autonomy scope, supported workflows, evidence classes, residual
  risk shape, and pass/fail policy
- [v8-autonomy-baseline-inventory.md](./v8-autonomy-baseline-inventory.md): v8
  command surfaces, autonomy seams, dashboard gaps, provider depth, and safe
  loosening opportunities
- [v9-eval-promotion-plan.md](./v9-eval-promotion-plan.md): v9 review of the
  v8 autonomy advisory eval suite, case-by-case promotion decisions, retained
  local evidence path, and release-candidate follow-up plan
- [v9-release-gate.md](./v9-release-gate.md): v9 automated release gate,
  onboarding/package/provider/eval stage map, evidence summary shape, advisory
  provider-canary policy, and pass/fail rules
- [manual-v9-release-validation.md](./manual-v9-release-validation.md): retained
  GBX-992 manual validation pass for first-run, dashboard cockpit, recovery,
  provider, package, accessibility, residual-risk, and go/no-go evidence
- [manual-qa-evidence-v9.md](./manual-qa-evidence-v9.md): v9 manual evidence
  directory convention, checklist template, accessibility pairing rules,
  retention policy, and redaction rules
- [v9-dogfooding-summary.md](./v9-dogfooding-summary.md): sanitized GBX-981
  real-repository dogfooding pass summaries, friction findings, and candidate
  GBX-982 fixes/contracts
- [recovery-maintenance-review-v8.md](./recovery-maintenance-review-v8.md): v8
  observability and recovery review for tasks, jobs, memory, repository index,
  branch search, and projection rebuilds
- [dashboard-accessibility-review-v8.md](./dashboard-accessibility-review-v8.md):
  v8 dashboard accessibility evidence and non-claims
- [v7-release-candidate.md](./v7-release-candidate.md): v7 operating model,
  release gate, retained manual evidence, residual risks, and decision state
- [v7-release-gate.md](./v7-release-gate.md): v7 automated release gate,
  provider-canary advisory policy, installed smoke inheritance, and evidence
  summary
- [manual-v7-release-validation.md](./manual-v7-release-validation.md): retained
  GBX-784 v7 manual validation pass and residual risks
- [manual-qa-evidence-v7.md](./manual-qa-evidence-v7.md): v7 manual validation,
  accessibility pairing, onboarding/package review, retention, and redaction
  rules
- [v7-adoption-scale-contract.md](./v7-adoption-scale-contract.md): v7 scope,
  non-goals, supported workflow set, evidence classes, and pass/fail policy
- [v7-scale-verification-inventory.md](./v7-scale-verification-inventory.md):
  v7 eval coverage, provider evidence, scale, daemon, transport, policy,
  accessibility, onboarding, and weak coverage
- [v7-live-transport-contract.md](./v7-live-transport-contract.md): v7 daemon,
  SSE, reconnect, backpressure, and multi-observer reliability contract
- [terminal-accessibility-review-v7.md](./terminal-accessibility-review-v7.md):
  v7 terminal accessibility pairing review
- [dashboard-accessibility-review-v7.md](./dashboard-accessibility-review-v7.md):
  v7 dashboard accessibility pairing review
- [v6-release-candidate.md](./v6-release-candidate.md): v6 release-candidate
  operating model, evidence summary, residual risks, and GO decision
- [v6-release-gate.md](./v6-release-gate.md): v6 release gate command,
  automated stage map, installed smoke matrix, manual validation matrix, and
  pass/fail policy
- [v6-release-hardening.md](./v6-release-hardening.md): v6 hardening scope,
  supported workflows, evidence classes, v5 gap mapping, and residual-risk
  policy
- [v6-release-inventory.md](./v6-release-inventory.md): v6 validation
  inventory, weak coverage, gate recommendations, and manual signoff split
- [v6-release-evidence.md](./v6-release-evidence.md): v6 evidence directory,
  summary schema, artifact pointers, manual evidence manifest, and redaction
  rules
- [manual-qa-evidence-v6.md](./manual-qa-evidence-v6.md): v6 terminal,
  dashboard, recovery, provider-canary, and accessibility manual evidence
  convention
- [terminal-accessibility-review-v6.md](./terminal-accessibility-review-v6.md):
  v6 terminal size, keyboard, and accessibility evidence
- [dashboard-accessibility-review-v6.md](./dashboard-accessibility-review-v6.md):
  v6 dashboard responsive, keyboard, screenshot, and accessibility evidence
- [recovery-maintenance-review-v6.md](./recovery-maintenance-review-v6.md): v6
  observability, projection, artifact, backup, eval, daemon, and dashboard
  recovery review
- [dependency-toolchain-review-v6.md](./dependency-toolchain-review-v6.md):
  dependency and toolchain review for v6
- [daemon-release-smoke-v6.md](./daemon-release-smoke-v6.md): v6 daemon
  release smoke evidence
- [provider-canary-policy-v6.md](./provider-canary-policy-v6.md): provider
  canary advisory policy
- [v5-terminal-release-gate.md](./v5-terminal-release-gate.md): v5 terminal UX
  release gate and manual validation expectations
- [v4-ux-release-gate.md](./v4-ux-release-gate.md): v4 operator-console UX
  gate, screenshot review path, and manual checks
- [v2-release-candidate.md](./v2-release-candidate.md): v2 supported
  operating model, release-readiness checklist, and explicit non-goals

## Implementation History

Use this section when changing implementation contracts, task scope, or
historical roadmap material. Task graphs remain discoverable for contributors,
but they are not the first-run operator path.

- [tasks-v9.md](./tasks-v9.md): v9 public baseline, onboarding, cockpit,
  provider freshness, operational polish, dogfooding, package, and release
  task graph
- [tasks-v8.md](./tasks-v8.md): v8 auditable-autonomy task graph
- [tasks-v7.md](./tasks-v7.md): v7 adoption, scale, eval, provider, policy,
  dashboard, accessibility, onboarding, and release-signoff task graph
- [tasks-v6.md](./tasks-v6.md): v6 release hardening, cancellation, transport,
  provider canary, packaging, manual QA, and release-gate task graph
- [tasks-v5.md](./tasks-v5.md): v5 full-screen terminal client task graph
- [tasks-v4.md](./tasks-v4.md): v4 dashboard UX task graph
- [tasks-v3.md](./tasks-v3.md): v3 Next.js, TypeScript, Tailwind, Zustand,
  shadcn, and OpenAPI SPA migration task graph
- [tasks-v2.md](./tasks-v2.md): v2 persistent runtime ownership,
  operator-console, upgrade safety, and workflow-hardening task graph
- [tasks-v1.md](./tasks-v1.md): v1 implementation history and roadmap context
- [refactor-v8.md](./refactor-v8.md): completed post-v8 refactor roadmap and
  closeout guardrails
- [refactor-v1.md](./refactor-v1.md): architecture-first refactor roadmap and
  completed follow-on queue
- [dashboard-parity.md](./dashboard-parity.md): v3 SPA parity gate before the
  legacy route flip
- [frontend-screenshot-archive.md](./frontend-screenshot-archive.md): v4
  Playwright screenshot archive workflow
- [frontend-ux-audit-v4.md](./frontend-ux-audit-v4.md): v4 screenshot-backed
  UX audit
- [terminal-ux-audit-v5.md](./terminal-ux-audit-v5.md): v5 terminal baseline
  audit
- [terminal-interaction-model-v5.md](./terminal-interaction-model-v5.md): v5
  full-screen terminal chat interaction contract
- [terminal-framework-decision-v5.md](./terminal-framework-decision-v5.md): v5
  Textual framework decision
- [terminal-test-harness-v5.md](./terminal-test-harness-v5.md): v5 terminal TUI
  test harness and manual review policy

## How To Read The Docs

Start with the workflow guide that matches the job you need to do now.

- If you are new, start with [v9-public-baseline.md](./v9-public-baseline.md)
  and [operator-quickstart.md](./operator-quickstart.md).
- If you are running Glassbox day to day, use the Daily Workflows section.
- If you are changing implementation contracts, keep
  [architecture.md](./architecture.md), [database.md](./database.md), and
  [refactor-boundaries.md](./refactor-boundaries.md) open.
- If you are preparing or auditing a release, use the Release Evidence section.
- If you are changing roadmap scope, use the Implementation History section.
