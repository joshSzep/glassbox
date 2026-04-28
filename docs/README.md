# Glassbox Documentation

Glassbox has two documentation layers:

- the root `README.md` is the landing page and quick-start path
- the files in `docs/` carry the workflow guides and reference material

Use this page to jump to the right level of detail.

## Start Here

- [getting-started.md](./getting-started.md): install the project, run the first session, understand the local workspace layout, and use the default validation commands
- [v6-release-candidate.md](./v6-release-candidate.md): review the supported v6 operating model, validation path, evidence expectations, known residual risks, and release decision
- [v2-release-candidate.md](./v2-release-candidate.md): review the supported v2 operating model, release-readiness checklist, and explicit non-goals
- [tasks-v3.md](./tasks-v3.md): plan the Next.js, TypeScript, Tailwind, Zustand, shadcn, and OpenAPI-driven SPA migration for the dashboard
- [tasks-v4.md](./tasks-v4.md): plan the UX-focused evolution of the completed SPA into a stronger operator console
- [tasks-v5.md](./tasks-v5.md): plan the full-screen terminal client modernization for `glassbox session chat`
- [tasks-v6.md](./tasks-v6.md): plan release hardening, real cancellation, transport reliability, provider canaries, packaging discipline, manual QA evidence, and the v6 release-candidate gate
- [tasks-v7.md](./tasks-v7.md): plan the post-v6 adoption, scale, eval portfolio, provider capability, policy governance, dashboard evidence, accessibility, onboarding, and release-signoff evolution
- [v7-adoption-scale-contract.md](./v7-adoption-scale-contract.md): review the v7 adoption-and-scale scope, non-goals, evidence classes, release-readiness checklist, residual-risk shape, and pass/fail policy
- [v7-live-transport-contract.md](./v7-live-transport-contract.md): review the v7 daemon, SSE, reconnect, backpressure, and multi-observer reliability contract
- [v7-scale-verification-inventory.md](./v7-scale-verification-inventory.md): inspect the v7 baseline inventory for eval coverage, provider canaries, scale risks, daemon transport, policy governance, accessibility, onboarding, and weak coverage
- [interactive-workflows.md](./interactive-workflows.md): use the full-screen `session chat` and `attach` TUI, plus `message`, `answer`, `approve`, `deny`, `resume`, and `status`
- [dashboard.md](./dashboard.md): use the co-hosted dashboard as the paired operator console for terminal chat or run the standalone dashboard from `serve`
- [dashboard-parity.md](./dashboard-parity.md): review the v3 SPA parity gate before replacing the legacy dashboard route
- [frontend-development.md](./frontend-development.md): run the Next.js SPA with FastAPI during local development and verify the static production path
- [frontend-screenshot-archive.md](./frontend-screenshot-archive.md): generate and review the v4 Playwright screenshot archive for frontend UX work
- [frontend-ux-audit-v4.md](./frontend-ux-audit-v4.md): review the v4 screenshot-backed UX audit for the completed SPA baseline
- [terminal-ux-audit-v5.md](./terminal-ux-audit-v5.md): review the v5 audit of the current line-mode terminal chat baseline
- [terminal-interaction-model-v5.md](./terminal-interaction-model-v5.md): review the v5 full-screen terminal chat interaction contract
- [terminal-framework-decision-v5.md](./terminal-framework-decision-v5.md): review the v5 Textual framework decision for the terminal TUI
- [terminal-test-harness-v5.md](./terminal-test-harness-v5.md): review the v5 terminal TUI test harness and manual review artifact policy
- [v5-terminal-release-gate.md](./v5-terminal-release-gate.md): validate the v5 terminal UX release gate with automated coverage, packaging smoke, manual review, known gaps, and the plain-mode decision
- [v6-release-hardening.md](./v6-release-hardening.md): review the v6 release-hardening contract, evidence classes, v5 gap mapping, readiness checklist, and residual-risk policy
- [v6-release-gate.md](./v6-release-gate.md): run the objective v6 release-candidate gate and review pass/fail policy, coverage, manual evidence, provider-canary, and residual-risk requirements
- [v6-release-inventory.md](./v6-release-inventory.md): inspect the current validation inventory, weak coverage areas, recommended v6 gate membership, and manual signoff split
- [v6-release-evidence.md](./v6-release-evidence.md): understand the retained v6 `summary.json` evidence format, artifact pointers, manual evidence manifest, and redaction rules
- [manual-qa-evidence-v6.md](./manual-qa-evidence-v6.md): record v6 terminal, dashboard, recovery, provider-canary, and accessibility manual evidence without committing large generated artifacts
- [manual-qa-evidence-v7.md](./manual-qa-evidence-v7.md): record v7 manual validation, named accessibility pairings, onboarding/package smoke, provider-canary review, and release evidence without committing private artifacts
- [terminal-accessibility-review-v6.md](./terminal-accessibility-review-v6.md): review terminal size, keyboard, and accessibility evidence for the v6 release-candidate track
- [dashboard-accessibility-review-v6.md](./dashboard-accessibility-review-v6.md): review dashboard responsive, keyboard, screenshot, and accessibility evidence for v6
- [terminal-accessibility-review-v7.md](./terminal-accessibility-review-v7.md): review named v7 terminal accessibility pairings, supported keyboard claims, and screen-reader non-claims
- [dashboard-accessibility-review-v7.md](./dashboard-accessibility-review-v7.md): review named v7 dashboard accessibility pairings, evidence-cue semantics, mobile/keyboard coverage, and screen-reader non-claims
- [recovery-maintenance-review-v6.md](./recovery-maintenance-review-v6.md): review recovery and maintenance command evidence for v6
- [frontend-testing.md](./frontend-testing.md): write v3 SPA unit, transport, store, and React component tests with Vitest and Testing Library
- [operator-console.md](./operator-console.md): understand the v2 multi-session console model, v3 SPA UX contract, action queues, runtime-health semantics, and backend/frontend contracts
- [persistent-runtime.md](./persistent-runtime.md): run a workspace daemon, inspect runtime health, attach from another terminal, and recover stale ownership
- [release-packaging.md](./release-packaging.md): build and validate release packages that include the statically exported SPA dashboard
- [v4-ux-release-gate.md](./v4-ux-release-gate.md): validate the v4 operator-console UX gate with automated coverage, screenshot review, and manual checks
- [team-workflows.md](./team-workflows.md): understand v2 session ownership, operator identity, and local-first handoff semantics
- [workspace-profiles.md](./workspace-profiles.md): declare repository-owned defaults for model selection, approval posture, and eval profile routing

## Operator Guides

- [v2-release-candidate.md](./v2-release-candidate.md): package the v2 workflow set into one release-candidate guide for operators and contributors
- [v6-release-candidate.md](./v6-release-candidate.md): package the v6 release-candidate operating model, validation path, residual risks, and decision state for operators and contributors
- [branching.md](./branching.md): inspect historical sessions, create child branches, and understand lineage fields
- [replay-evals.md](./replay-evals.md): replay historical sessions, export bundles, run eval suites, and work through local-first regression gates
- [runtime-context.md](./runtime-context.md): inspect repository context, runtime notes, working-set context, and artifact-backed summaries
- [persistent-runtime.md](./persistent-runtime.md): operate the daemon-backed workspace runtime and troubleshoot attach or health states
- [operator-console.md](./operator-console.md): plan and reason about the v2 multi-session console, v3 SPA UX, action queues, and runtime-health semantics
- [team-workflows.md](./team-workflows.md): plan team-oriented session custody, intervention attribution, and handoff without assuming a remote multi-user platform
- [providers.md](./providers.md): configure OpenAI or Anthropic credentials for real provider execution
- [workspace-profiles.md](./workspace-profiles.md): configure reviewable repository defaults without storing runtime secrets
- [tool-policy.md](./tool-policy.md): understand risk buckets, approval gating, blocked commands, and `ask_user` semantics

## Deep Reference

- [architecture.md](./architecture.md): current runtime, bootstrap, store, CLI, web, replay, and eval ownership boundaries on top of the event-sourced system design
- [database.md](./database.md): SQLite event store, projection tables, artifact storage, branching lineage fields, and the split store implementation map
- [dashboard-frontend-boundaries.md](./dashboard-frontend-boundaries.md): legacy reducer, renderer, transport, and DOM-binding boundaries for the no-framework dashboard, plus the v3 SPA supersession notice
- [dashboard-parity.md](./dashboard-parity.md): behavioral parity checklist, automated coverage map, manual validation path, and known migration gaps for the SPA route flip
- [frontend-development.md](./frontend-development.md): v3 SPA local proxy, SSE development, and FastAPI static-serving workflow
- [frontend-screenshot-archive.md](./frontend-screenshot-archive.md): v4 screenshot archive command, scenario names, retention policy, and visual review checklist
- [frontend-ux-audit-v4.md](./frontend-ux-audit-v4.md): current-SPA v4 UX audit, screenshot evidence map, issue inventory, and preserved behavior list
- [terminal-ux-audit-v5.md](./terminal-ux-audit-v5.md): current terminal chat UX audit, transcript evidence, issue inventory, and preserved behavior list
- [terminal-interaction-model-v5.md](./terminal-interaction-model-v5.md): v5 terminal chat layout, keyboard, action-priority, transcript, runtime-state, dashboard-handoff, and fallback contract
- [terminal-framework-decision-v5.md](./terminal-framework-decision-v5.md): v5 terminal framework decision, Textual rationale, alternatives, packaging notes, and smoke validation
- [terminal-test-harness-v5.md](./terminal-test-harness-v5.md): v5 terminal TUI test layers, scenario matrix, stable invariants, manual review checklist, and artifact retention policy
- [v5-terminal-release-gate.md](./v5-terminal-release-gate.md): v5 terminal UX release command, checklist, automated coverage map, manual validation, known gaps, and line-mode support decision
- [v6-release-candidate.md](./v6-release-candidate.md): v6 release-candidate operating model, release-readiness checklist, evidence summary, non-goals, residual risks, and decision state
- [v6-release-hardening.md](./v6-release-hardening.md): v6 hardening scope, non-goals, supported workflow set, evidence classes, v5 known-gap mapping, readiness checklist, residual-risk register, and pass/fail policy
- [v6-release-gate.md](./v6-release-gate.md): v6 release-candidate command, automated stage map, installed smoke matrix, manual validation matrix, pass/fail policy, and residual risk register
- [v6-release-inventory.md](./v6-release-inventory.md): v6 inventory of current automated checks, manual checks, weak coverage, gate recommendations, manual signoff recommendations, and evidence ownership
- [v6-release-evidence.md](./v6-release-evidence.md): v6 release evidence directory, automated summary schema, stage schema, related artifact pointers, manual evidence manifest, and redaction rules
- [manual-qa-evidence-v6.md](./manual-qa-evidence-v6.md): v6 manual QA evidence directory convention, manifest template, retention policy, and redaction rules
- [manual-qa-evidence-v7.md](./manual-qa-evidence-v7.md): v7 manual QA evidence directory convention, named accessibility pairing manifest, onboarding/package review shape, retention policy, and redaction rules
- [terminal-accessibility-review-v6.md](./terminal-accessibility-review-v6.md): v6 terminal review sizes, keyboard workflows, validation results, claims, and non-claims
- [dashboard-accessibility-review-v6.md](./dashboard-accessibility-review-v6.md): v6 dashboard viewport, keyboard, screenshot archive, validation, claims, and non-claims
- [terminal-accessibility-review-v7.md](./terminal-accessibility-review-v7.md): v7 terminal named-pairing review for VS Code integrated terminal on macOS, keyboard claims, and assistive-technology non-claims
- [dashboard-accessibility-review-v7.md](./dashboard-accessibility-review-v7.md): v7 dashboard named-pairing review for Chromium/Playwright on macOS, keyboard/mobile/evidence-cue claims, and assistive-technology non-claims
- [recovery-maintenance-review-v6.md](./recovery-maintenance-review-v6.md): v6 observability, projection, artifact, backup, eval, daemon, and installed-dashboard recovery review
- [frontend-testing.md](./frontend-testing.md): v3 SPA frontend-native test harness, fixture strategy, and focused test-writing guidance
- [operator-console.md](./operator-console.md): v2 operator-console information architecture, v3 SPA UX contract, and queue/health semantics for multi-session inspection
- [v4-ux-release-gate.md](./v4-ux-release-gate.md): v4 UX gate command, checklist, automated coverage map, screenshot review path, manual validation, and known gaps
- [tasks-v3.md](./tasks-v3.md): concrete v3 task graph for replacing the hand-rolled dashboard with a statically served Next.js SPA
- [tasks-v4.md](./tasks-v4.md): concrete v4 task graph for attention-first queue triage, real inspector tabs, priority actions, session narrative, evidence hierarchy, mobile drill-in, accessibility, and visual QA
- [tasks-v5.md](./tasks-v5.md): concrete v5 task graph for replacing the line-mode interactive chat loop with a full-screen coding-agent terminal experience
- [tasks-v6.md](./tasks-v6.md): concrete v6 task graph for release hardening, cancellation, live transport reliability, provider canaries, packaging reproducibility, accessibility evidence, and release-candidate signoff
- [tasks-v7.md](./tasks-v7.md): concrete v7 task graph for adoption, larger-session scale, deterministic eval expansion, provider capability matrices, daemon reliability, policy governance, dashboard evidence, accessibility, onboarding, and release signoff
- [v7-adoption-scale-contract.md](./v7-adoption-scale-contract.md): v7 scope, non-goals, supported workflow set, v6 follow-up mapping, evidence classes, release-readiness checklist, residual-risk register shape, and pass/fail policy
- [v7-live-transport-contract.md](./v7-live-transport-contract.md): v7 live transport, daemon ownership, reconnect, backpressure, and multi-observer contract
- [v7-scale-verification-inventory.md](./v7-scale-verification-inventory.md): v7 inventory of current eval coverage, provider evidence, larger-session read paths, daemon and transport evidence, policy governance, accessibility, onboarding, recommended gate membership, and weak coverage
- [team-workflows.md](./team-workflows.md): v2 ownership, identity, and handoff contract for portable team workflows
- [v2-release-candidate.md](./v2-release-candidate.md): release-candidate readiness checklist and supported operating-model summary
- [release-packaging.md](./release-packaging.md): Python distribution packaging path, SPA asset checks, and installed-dashboard smoke validation
- [refactor-boundaries.md](./refactor-boundaries.md): code-aligned boundary map, dependency-direction rules, and guardrails that explain why the current facades and module splits look the way they do
- [refactor-v1.md](./refactor-v1.md): architecture-first refactor roadmap, completed follow-on queue, and status tracker for the v1 decomposition work
- [tasks-v1.md](./tasks-v1.md): implementation history, completed v1 task graph, and roadmap context
- [tasks-v2.md](./tasks-v2.md): concrete v2 task graph and milestone plan for persistent runtime ownership, operator-console evolution, upgrade safety, and long-lived workflow hardening

## How To Read The Docs

Start with the workflow guide that matches the job you need to do now.

- If you are new to the repo, start with [getting-started.md](./getting-started.md).
- If you are running Glassbox day to day, the workflow guides are the main path.
- If you are changing implementation contracts, keep [architecture.md](./architecture.md) and [database.md](./database.md) open.
- If you are changing module ownership after the refactor, keep [architecture.md](./architecture.md), [refactor-boundaries.md](./refactor-boundaries.md), and [dashboard-frontend-boundaries.md](./dashboard-frontend-boundaries.md) open together so the runtime/bootstrap, replay/eval, legacy dashboard, and v3 SPA seams stay aligned.
- If you need policy, provider, or replay governance details, prefer the dedicated guide over the root README.
