# Glassbox Documentation

Glassbox has two documentation layers:

- the root `README.md` is the landing page and quick-start path
- the files in `docs/` carry the workflow guides and reference material

Use this page to jump to the right level of detail.

## Start Here

- [getting-started.md](./getting-started.md): install the project, run the first session, understand the local workspace layout, and use the default validation commands
- [interactive-workflows.md](./interactive-workflows.md): work through `chat`, `attach`, `message`, `answer`, `approve`, `deny`, `resume`, and `status`
- [dashboard.md](./dashboard.md): use the co-hosted dashboard from `chat` or the standalone dashboard from `serve`

## Operator Guides

- [branching.md](./branching.md): inspect historical sessions, create child branches, and understand lineage fields
- [replay-evals.md](./replay-evals.md): replay historical sessions, export bundles, run eval suites, and work through local-first regression gates
- [runtime-context.md](./runtime-context.md): inspect repository context, runtime notes, working-set context, and artifact-backed summaries
- [providers.md](./providers.md): configure OpenAI or Anthropic credentials for real provider execution
- [tool-policy.md](./tool-policy.md): understand risk buckets, approval gating, blocked commands, and `ask_user` semantics

## Deep Reference

- [architecture.md](./architecture.md): event-sourced runtime architecture, turn flow, branching model, replay/eval contract, and system boundaries
- [database.md](./database.md): SQLite event store, projection tables, artifact storage, and query patterns
- [refactor-v1.md](./refactor-v1.md): architecture-first refactor roadmap for decomposing oversized modules and repairing implementation seams in the current v1 codebase
- [tasks-v1.md](./tasks-v1.md): implementation history, completed v1 task graph, and roadmap context
- [tasks-v2.md](./tasks-v2.md): concrete v2 task graph and milestone plan for persistent runtime ownership, operator-console evolution, upgrade safety, and long-lived workflow hardening

## How To Read The Docs

Start with the workflow guide that matches the job you need to do now.

- If you are new to the repo, start with [getting-started.md](./getting-started.md).
- If you are running Glassbox day to day, the workflow guides are the main path.
- If you are changing implementation contracts, keep [architecture.md](./architecture.md) and [database.md](./database.md) open.
- If you need policy, provider, or replay governance details, prefer the dedicated guide over the root README.
