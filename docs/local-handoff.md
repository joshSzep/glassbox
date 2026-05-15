# Local Handoff

For the docs hub and operator guides, start at [README.md](./README.md). This
guide collects the current local handoff workflow and points to the v17 planning
track without implying v17 is released behavior.

Local handoff means moving inspectable local context between operators,
terminals, machines, reviewers, release custodians, or a future self while
preserving Glassbox's local-first authority model. It does not create hosted
collaboration, remote custody enforcement, reviewer approval, release approval,
automatic continuation, staging, commits, pushes, pull requests, merges,
deployments, or publication.

## Current Supported Flow

Use session export when another local context needs the session story:

```bash
uv run glassbox session export SESSION_ID handoff.json --cwd .
uv run glassbox session import handoff.json --cwd ../other-workspace
```

The exported package is inspectable JSON. It includes redacted session metadata,
lineage, transcript summaries, task summaries, checkpoint history, branch-search
summaries, artifact references, policy decisions, event summaries, redaction
notes, and a `handoff.summary` block. It does not copy the SQLite database or
embed artifact contents.

Add operator labels when the recipient needs custody context:

```bash
uv run glassbox session export SESSION_ID handoff.json \
  --exported-by alice \
  --expected-custodian bob \
  --note "waiting on verification review" \
  --cwd .
```

Import is inspection-only. The receiving workspace gets a new historical local
session with imported transcript/history events and `Resumable: no`. Import does
not silently merge into an existing live session or resume a provider stream.

For changeset-centered review handoff, start with:

```bash
uv run glassbox changeset handoff-readiness CHANGESET_ID --cwd .
uv run glassbox changeset export CHANGESET_ID changeset-review.json \
  --markdown-output changeset-review.md \
  --cwd .
uv run glassbox changeset export-inspect changeset-review.json --json
```

The changeset export is the preferred review-centered bundle when a changeset
exists. It includes redacted summaries, verification posture, reviewer-safe
evidence graph slices, review feedback and response posture, manual evidence,
handoff readiness, safe inspection commands, a redaction report, and non-claims.
It does not include raw `.glassbox` database state, raw command output, raw
provider transcripts, raw diffs, file contents, raw screenshots, browser traces,
or accessibility transcripts.

## Safe Inspection First

Before acting on a handoff, inspect what travelled and what stayed local:

```bash
uv run glassbox session status SESSION_ID --cwd .
uv run glassbox session compactions SESSION_ID --cwd .
uv run glassbox changeset show CHANGESET_ID --cwd .
uv run glassbox changeset verification-plan CHANGESET_ID --cwd .
uv run glassbox changeset handoff-readiness CHANGESET_ID --cwd .
uv run glassbox observability status --cwd .
uv run glassbox eval audit --cwd .
```

Safe inspection commands do not approve, answer, resume, stage, commit, push,
publish, deploy, merge, or run arbitrary tools. Treat any mutating next step as
operator-selected and policy controlled.

## Redaction And Local-Only Evidence

Review handoff artifacts before sharing them. Current session export replaces
absolute workspace paths with `<workspace-root>`, redacts common secret-like
tokens, and references artifacts instead of embedding their contents. Current
changeset export adds a redaction report and reviewer-safe Markdown, while
manual, browser, dashboard, accessibility, provider, screenshots, logs, and raw
artifact evidence remain local-only unless separately reviewed and sanitized.

If a claim depends on evidence that did not travel, say so in the handoff note or
review summary. Local-only evidence can support local confidence without giving a
recipient the same ability to verify from the package alone.

## V17 Planning Track

The v17 local handoff track is planning a shared handoff workflow across
sessions, tasks, changesets, workspaces, release evidence, and future-self
continuity. The foundational shared handoff models and v2 package compatibility
inspector now exist in code, while operator-facing v17 commands and cockpit
surfaces remain planned until later tasks land. Start with:

- [v17-local-handoff-contract.md](./v17-local-handoff-contract.md): shared
  intent, readiness, package, redaction, import triage, custody, surface, and
  non-claim vocabulary
- [v17-local-handoff-audit.md](./v17-local-handoff-audit.md): source-linked
  audit of current export, import, review bundle, readiness, queue, web, and
  dashboard surfaces
- [tasks-v17.md](./tasks-v17.md): dependency-ordered implementation graph for
  local handoff

Planned v17 capabilities include recipient-oriented export profiles, redaction
preview, local-only evidence inventory, import triage before mutation, custody
accept/reject/archive decisions, queue rows, API routes, TUI entry points,
dashboard cockpit surfaces, deterministic evals, and a v17 release gate.
Until those tasks land, use the supported commands above and label any v17-only
operator workflow as planned.

## Non-Claims

Current handoff artifacts and planned v17 handoff packages do not claim:

- reviewer approval
- release approval
- verification success without retained verification evidence
- continuation authority
- runtime ownership transfer
- raw evidence sharing
- package completeness
- repository intelligence or memory authority
- staging, commit, push, pull request, merge, deployment, or publication

For runtime-owner and custody vocabulary, see
[team-workflows.md](./team-workflows.md). For reviewer-safe sharing rules, see
[reviewer-evidence-bundles.md](./reviewer-evidence-bundles.md).
