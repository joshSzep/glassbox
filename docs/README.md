# Glassbox Documentation

Glassbox has two documentation layers:

- the root `README.md` is the landing page and quick-start path
- the files in `docs/` carry the workflow guides and reference material

Use this page to jump to the right level of detail.

## Start Here

- [getting-started.md](./getting-started.md): install the project, run the first session, understand the local workspace layout, and use the default validation commands
- [v2-release-candidate.md](./v2-release-candidate.md): review the supported v2 operating model, release-readiness checklist, and explicit non-goals
- [tasks-v3.md](./tasks-v3.md): plan the Next.js, TypeScript, Tailwind, Zustand, shadcn, and OpenAPI-driven SPA migration for the dashboard
- [interactive-workflows.md](./interactive-workflows.md): work through `chat`, `attach`, `message`, `answer`, `approve`, `deny`, `resume`, and `status`
- [dashboard.md](./dashboard.md): use the co-hosted dashboard from `chat` or the standalone dashboard from `serve`
- [dashboard-parity.md](./dashboard-parity.md): review the v3 SPA parity gate before replacing the legacy dashboard route
- [frontend-development.md](./frontend-development.md): run the Next.js SPA with FastAPI during local development and verify the static production path
- [frontend-testing.md](./frontend-testing.md): write v3 SPA unit, transport, store, and React component tests with Vitest and Testing Library
- [operator-console.md](./operator-console.md): understand the v2 multi-session console model, v3 SPA UX contract, action queues, runtime-health semantics, and backend/frontend contracts
- [persistent-runtime.md](./persistent-runtime.md): run a workspace daemon, inspect runtime health, attach from another terminal, and recover stale ownership
- [release-packaging.md](./release-packaging.md): build and validate release packages that include the statically exported SPA dashboard
- [team-workflows.md](./team-workflows.md): understand v2 session ownership, operator identity, and local-first handoff semantics
- [workspace-profiles.md](./workspace-profiles.md): declare repository-owned defaults for model selection, approval posture, and eval profile routing

## Operator Guides

- [v2-release-candidate.md](./v2-release-candidate.md): package the v2 workflow set into one release-candidate guide for operators and contributors
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
- [frontend-testing.md](./frontend-testing.md): v3 SPA frontend-native test harness, fixture strategy, and focused test-writing guidance
- [operator-console.md](./operator-console.md): v2 operator-console information architecture, v3 SPA UX contract, and queue/health semantics for multi-session inspection
- [tasks-v3.md](./tasks-v3.md): concrete v3 task graph for replacing the hand-rolled dashboard with a statically served Next.js SPA
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
