# Glassbox v17 Release Candidate

This page is the operator and contributor guide for the Glassbox v17
release-candidate track. It names the supported local-handoff operating model,
validation path, evidence expectations, advisory evidence boundaries, residual
risks, deliberate non-goals, and release decision without requiring readers to
inspect the task graph.

## Release Posture

Glassbox v17 keeps the v16 operator-flow model and adds local handoff as a
first-class workflow across sessions, tasks, changesets, workspace summaries,
release evidence, and future-self continuity. The goal is to make local work
portable without turning Glassbox into hosted collaboration, remote custody,
review approval, release approval, or automatic publication.

The package version for this line remains `0.10.0`. Per
[version-release-policy.md](./version-release-policy.md), v17 is a milestone
and release-evidence track on the existing pre-1.0 package line, not a package
version bump by itself.

The primary product shape is:

- terminal chat remains the primary operator surface
- the dashboard remains the paired local cockpit and evidence surface
- SQLite canonical events and managed artifacts remain the source of truth
- handoff packages are portable inspection artifacts, not raw `.glassbox`
  database copies
- recipient intent is explicit: `review-only`, `continue-work`,
  `verification-needed`, `failure-triage`, `release-signoff`, `future-self`,
  and `fork-recommended`
- handoff readiness explains status, confidence, freshness, local-only
  evidence, stale evidence, missing evidence, accepted risks, safe inspection
  commands, and non-claims
- redaction preview and local-only inventory show what would travel, what
  would be summarized, and what must remain in the source workspace before a
  package is written
- import triage validates package compatibility, digest posture, redaction
  posture, local-only gaps, limitations, safe first commands, and recommended
  disposition before import
- imported sessions are historical inspection-only state with `resumable: no`
  unless an operator explicitly chooses a separate local fork or continuation
  workflow
- custody acceptance, rejection, archive, and follow-up are local workflow
  metadata, not authorization, approval, runtime ownership, reviewer signoff,
  release signoff, or publication
- deterministic replay, eval, package, frontend, installed-wheel, and release
  gate evidence remain release authority
- v17 is local handoff, not hosted review, PR automation, remote sync,
  automatic publication, automatic command approval, raw evidence portability,
  or live-provider release authority

Use these discovery commands:

```bash
uv run glassbox command guide
uv run glassbox command tree
uv run glassbox handoff --help
```

Inspect v17 handoff surfaces with:

```bash
uv run glassbox session handoff-readiness SESSION_ID --intent review-only --cwd .
uv run glassbox task handoff-readiness TASK_ID --intent continue-work --cwd .
uv run glassbox changeset handoff-readiness CHANGESET_ID --cwd .
uv run glassbox handoff prepare session SESSION_ID --preview --json --cwd .
uv run glassbox handoff inspect handoff.json --json --cwd .
uv run glassbox observability handoff-readiness --source release --json --cwd .
```

The v17 automated release-candidate gate is:

```bash
uv run python scripts/validate_v17_release_gate.py
```

For a non-mutating preview:

```bash
uv run python scripts/validate_v17_release_gate.py --dry-run
```

Focused dogfooding evidence is summarized in
[v17-dogfooding-summary.md](./v17-dogfooding-summary.md). Local `.glassbox/`
evidence is workspace state and is not committed to git.

## Supported Operating Model

- **Intent-specific handoff**: every package and readiness view should say why
  the handoff exists before suggesting what a recipient should inspect next.
- **Readiness before mutation**: session, task, changeset, workspace, and
  release readiness are read-only posture summaries. They do not approve,
  answer, resume, verify, stage, commit, push, publish, merge, deploy, or
  transfer runtime ownership.
- **Preview before export**: `handoff prepare ... --preview` and the legacy
  `session export --preview` and `changeset export --preview` paths show
  included sections, redaction posture, omitted raw categories, local-only
  evidence counts, package limitations, and safe inspection commands before a
  package is written.
- **Recipient-oriented packages**: session and changeset exports can carry
  recipient labels, expected custodian, exported-by label, notes, JSON package
  metadata, and reviewer-safe Markdown summaries from the same local evidence.
- **Import triage first**: `handoff inspect`, `session import --triage`, and
  API triage routes inspect package compatibility and limitations before
  historical local state is created.
- **Inspection-only import**: supported session packages import as historical
  local state, not live resumed work. A recipient must explicitly choose any
  fork, new session, verification, or rejection path.
- **Custody as audit trail**: `handoff accept`, `handoff reject`, and
  `handoff archive` append canonical local events and update projections while
  preserving non-claims around authorization and approval.
- **Cockpit surfaces**: CLI, TUI, API, and dashboard use the same vocabulary
  for intent, compatibility, redaction, local-only evidence, safe commands,
  custody, and non-claims.
- **Release handoff**: release readiness and release-signoff profiles carry
  retained evidence posture for a human custodian, but they do not run gates or
  publish anything.

## Primary Operator Flows

### Prepare A Review-Only Package

```bash
uv run glassbox handoff prepare session SESSION_ID handoff.json \
  --intent review-only \
  --recipient reviewer \
  --markdown-output handoff.md \
  --cwd .
uv run glassbox handoff inspect handoff.json --json --cwd .
uv run glassbox handoff inspect handoff.json --markdown --cwd .
```

Review-only handoff is not approval to continue work. Pair JSON packages with
Markdown summaries when a human needs a compact evidence view.

### Inspect Local-Only Evidence Before Export

```bash
uv run glassbox handoff prepare session SESSION_ID --preview --json --cwd .
uv run glassbox handoff prepare changeset CHANGESET_ID --preview --json --cwd .
```

Preview should name raw `.glassbox` database state, raw artifacts, command
logs, provider output, screenshots, transcripts, and other local-only evidence
as limitations rather than pretending that evidence travelled.

### Triage And Import A Received Package

```bash
uv run glassbox handoff inspect handoff.json --json --cwd .
uv run glassbox handoff import handoff.json --json --cwd .
uv run glassbox handoff list --json --cwd .
uv run glassbox handoff guidance SESSION_ID PACKAGE_ID --json --cwd .
```

Import creates inspection-only state. Guidance can recommend inspect-only,
fork, new-session, verification, or rejection paths, but the mutating paths
remain explicit local choices.

### Record Custody Decisions

```bash
uv run glassbox handoff accept SESSION_ID PACKAGE_ID \
  --accepted-by recipient \
  --follow-up-intent verification-needed \
  --cwd .
uv run glassbox handoff reject SESSION_ID PACKAGE_ID \
  --reason "recipient cannot inspect local-only evidence" \
  --cwd .
uv run glassbox handoff archive SESSION_ID PACKAGE_ID \
  --reason "historical handoff retained" \
  --cwd .
```

Custody is a workflow audit trail, not authentication, authorization, owner
assignment, reviewer approval, release approval, or runtime lock.

### Review Release Handoff Posture

```bash
uv run glassbox observability handoff-readiness --source release --json --cwd .
uv run glassbox eval audit --profile release-candidate --cwd .
uv run python scripts/validate_v17_release_gate.py --dry-run
```

Release handoff starts with safe inspection and ends with an operator decision.
The full gate, package checks, installed smoke, dogfooding, and manual release
review stay separate from advisory provider, browser, dashboard, and
accessibility evidence.

## Release-Readiness Checklist

Before treating a build as the v17 release candidate, complete this list:

- The v17 local handoff contract, audit, local handoff guide, release gate,
  dogfooding summary, release-candidate guide, and task graph are linked from
  the docs hub.
- `uv run python scripts/validate_v17_release_gate.py` passes and writes
  `summary.json` with blocking and advisory sections.
- `uv run python scripts/validate_v17_release_gate.py --dry-run` plans the
  full deterministic path and records advisory evidence separately.
- The deterministic `release-candidate` eval profile includes the v17 local
  handoff eval smoke cases:
  `local-handoff.prepare-preview`,
  `local-handoff.import-triage`,
  `local-handoff.custody-decisions`, and
  `local-handoff.reviewer-safe-bundle`.
- `glassbox eval audit --profile release-candidate --cwd .` covers the release
  candidate capabilities after the v17 handoff fixtures are promoted.
- Session, task, changeset, workspace, and release handoff readiness have
  focused test coverage.
- Redaction preview, local-only inventory, import triage, custody decisions,
  fork-or-continue guidance, CLI/API, dashboard cockpit, TUI entry points,
  package contents, installed-wheel smoke, docs, and eval coverage paths have
  deterministic checks where promoted.
- Generated OpenAPI/types and dashboard static assets are fresh and packaged.
- Built wheel and sdist contents include v17 release docs, v17 release gate
  scripts, eval fixtures, generated API files, handoff runtime modules, web
  routes, and dashboard static assets.
- Dogfooding findings have dispositions as fixes, docs, tests/evals, accepted
  risks, or post-v17 follow-ups.
- Provider canaries, live browser/dashboard evidence, accessibility evidence,
  dogfooding, and manual evidence are either retained as advisory evidence or
  explicitly skipped with bounded reasons.
- Raw `.glassbox` state is not committed; reviewer-safe summaries are used for
  handoff and release review.

## Current Evidence Summary

The current retained v17 evidence shows:

- v17 release-gate dry run: retained at
  `.glassbox/releases/gbx-1763-v17-dogfooding/v17-gate-dry-run/summary.json`
  with 105 planned blocking deterministic stages and advisory evidence
  separated as skipped or planned
- v17 release gate: retained at
  `.glassbox/releases/20260521T035747Z-v17-gate/summary.json` with 138
  blocking stages passed and advisory provider, dashboard/browser,
  accessibility, dogfooding, and manual evidence separated as skipped or planned
- v17 dogfooding: future-self preview, review-only export, package inspection,
  import triage, inspection-only import, verification-needed readiness,
  fork-or-continue guidance, custody accept/reject, failure-triage preview,
  release-signoff preview, workspace readiness, release readiness, focused
  tests, command discovery, and release-gate dry-run findings are triaged in
  [v17-dogfooding-summary.md](./v17-dogfooding-summary.md)
- focused v17 handoff checks: `35 passed` for redaction preview, import
  triage, custody decisions, guidance, task readiness, session readiness,
  workspace readiness, and CLI handoff commands
- v17 local handoff eval smoke: the gate passed
  `local-handoff.prepare-preview`,
  `local-handoff.import-triage`,
  `local-handoff.custody-decisions`, and
  `local-handoff.reviewer-safe-bundle`
- v17 package and installed smoke: the gate passed handoff package
  inspection, package contents validation, built wheel/sdist, generated API
  freshness, dashboard static asset validation, and installed-wheel smoke
- v17 release docs: `docs/v17-dogfooding-summary.md`,
  `docs/v17-release-candidate.md`, [v17-release-gate.md](./v17-release-gate.md),
  [v17-dogfooding-summary.md](./v17-dogfooding-summary.md),
  [local-handoff.md](./local-handoff.md),
  [v17-local-handoff-contract.md](./v17-local-handoff-contract.md), and
  [tasks-v17.md](./tasks-v17.md) define the release-candidate story
- advisory evidence split: provider canaries, dashboard/browser notes,
  accessibility notes, dogfooding, and manual release evidence remain separate
  from deterministic release authority in the v17 gate summary
- package metadata follow-up: dogfooding found that a session package exported
  through `handoff prepare session` can render richer Markdown while
  `handoff inspect --json` still classifies it as `legacy-inspection-only`.
  Import remains safe and inspection-only, so this is tracked as a bounded
  post-v17 follow-up rather than a release blocker.

## Known Residual Risks

- Local handoff is advisory workflow support. It cannot replace deterministic
  tests, evals, package checks, release gates, or operator review.
- A portable package cannot prove raw local evidence it does not carry.
  Recipients must inspect local-only inventory, limitations, stale evidence,
  missing evidence, and non-claims before acting.
- Session handoff package JSON inspection can still classify some exported
  session packages as `legacy-inspection-only` even when richer Markdown
  summaries and profile metadata render correctly. This is visible to
  recipients and safe by default because import remains inspection-only.
- Imported sessions are historical context. Operators can choose fork,
  continuation, verification, or rejection through explicit local workflows,
  but import itself does not resume live work.
- Custody metadata can be stale, incomplete, or locally contradictory. It is an
  audit trail for humans, not a lock, permission grant, assignment system, or
  source of authority.
- Workspace and release readiness can be degraded by missing repository
  intelligence, stale provider canaries, missing release-surface evidence, or
  local artifact pressure. These states must remain visible and advisory unless
  a deterministic check fails.
- Provider canaries are advisory. This release candidate does not make live
  provider behavior blocking release authority.
- Retained browser/dashboard and accessibility-adjacent evidence covers bounded
  scenarios, dates, tools, and limitations. It is not broad browser coverage,
  screen-reader certification, accessibility certification, or WCAG conformance.
- v17 does not remove inherited bounded-autonomy limits from earlier
  milestones.

## Deliberate Non-Goals

v17 does not introduce hosted collaboration, hosted review state, hosted
handoff custody, remote session sync, cloud evidence storage, remote workers,
remote repository indexing, multi-writer sessions, GitHub review-thread
synchronization, issue tracker integration, PR automation, automatic owner
assignment, automatic review approval, automatic release approval, automatic
command approval, automatic staging, automatic commits, automatic pushes,
automatic pull request creation, automatic branch-search merging, automatic
rebasing, automatic force-pushing, automatic deployment, automatic publication,
automatic package publication, raw `.glassbox` database portability, raw log
sharing by default, raw provider transcript sharing by default, live provider
release authority, automatic provider failover as release authority, broad
accessibility certification, WCAG conformance claims, live browser release
authority, hidden semantic indexing that cannot be inspected and rebuilt,
external vector-store authority, provider-side hidden memory, or indefinite
unattended autonomy.

## Release Decision

Decision: GO for v17 release candidate publication.

Decision date: 2026-05-21.

Candidate build reviewed: `GBX-1764` release-candidate working tree with v17
local-handoff evidence retained locally.

Retained evidence:

```text
.glassbox/releases/gbx-1763-v17-dogfooding/
.glassbox/releases/gbx-1763-v17-dogfooding/v17-gate-dry-run/
.glassbox/releases/20260521T035747Z-v17-gate/
```

Final pass/fail state:

| Area | State | Evidence |
| --- | --- | --- |
| V17 release gate dry run | passed | `.glassbox/releases/gbx-1763-v17-dogfooding/v17-gate-dry-run/summary.json` |
| V17 release gate | passed | `.glassbox/releases/20260521T035747Z-v17-gate/summary.json` with 138 blocking stages passed |
| Focused handoff runtime and CLI checks | passed | `35 passed` across preview, triage, custody, guidance, readiness, and CLI handoff tests |
| V17 local handoff eval smoke | passed | `local-handoff.prepare-preview`, `local-handoff.import-triage`, `local-handoff.custody-decisions`, and `local-handoff.reviewer-safe-bundle` |
| V17 package and installed smoke | passed | handoff package smoke, package contents validation, wheel/sdist build, dashboard assets, generated API freshness, and installed-wheel smoke |
| Dogfooding disposition | passed triage | [v17-dogfooding-summary.md](./v17-dogfooding-summary.md) |
| Provider posture | advisory skipped by default | v17 gate advisory provider evidence section |
| Browser/dashboard posture | advisory planned | v17 gate advisory dashboard browser evidence section |
| Accessibility posture | advisory planned | v17 gate advisory accessibility evidence section |
| Manual release evidence | recorded | this guide and v17 gate advisory summary |
| Residual risk review | accepted | known residual risks listed above |

No deterministic blocker remains open for v17 release-candidate publication.
The accepted residual risks stay bounded to local package metadata
classification, local-only evidence completeness, inspection-only import
limits, custody non-authority, workspace/release evidence freshness, advisory
provider/browser/dashboard/accessibility posture, and inherited bounded local
autonomy.

## Related Files

- [local-handoff.md](./local-handoff.md)
- [v17-local-handoff-contract.md](./v17-local-handoff-contract.md)
- [v17-local-handoff-audit.md](./v17-local-handoff-audit.md)
- [v17-release-gate.md](./v17-release-gate.md)
- [v17-dogfooding-summary.md](./v17-dogfooding-summary.md)
- [tasks-v17.md](./tasks-v17.md)
- [team-workflows.md](./team-workflows.md)
- [reviewer-evidence-bundles.md](./reviewer-evidence-bundles.md)
- [evidence-graph.md](./evidence-graph.md)
- [operator-queue.md](./operator-queue.md)
- [verification-orchestrator.md](./verification-orchestrator.md)
- [manual-evidence.md](./manual-evidence.md)
- [browser-accessibility-evidence.md](./browser-accessibility-evidence.md)
- [publication-boundary.md](./publication-boundary.md)
- [v16-release-candidate.md](./v16-release-candidate.md)
- [release-packaging.md](./release-packaging.md)
- [providers.md](./providers.md)
