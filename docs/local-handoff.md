# Local Handoff

For the docs hub and operator guides, start at [README.md](./README.md). This
guide collects the current local handoff workflow and points to the v17
release-candidate track.

Local handoff means moving inspectable local context between operators,
terminals, machines, reviewers, release custodians, or a future self while
preserving Glassbox's local-first authority model. It does not create hosted
collaboration, remote custody enforcement, reviewer approval, release approval,
automatic continuation, staging, commits, pushes, pull requests, merges,
deployments, or publication.

## Current Supported Flow

Use session export when another local context needs the session story:

```bash
uv run glassbox handoff prepare session SESSION_ID handoff.json --cwd .
uv run glassbox handoff inspect handoff.json --cwd ../other-workspace
uv run glassbox handoff import handoff.json --cwd ../other-workspace
```

The legacy session commands remain supported aliases for the same workflow:

```bash
uv run glassbox session export SESSION_ID handoff.json --cwd .
uv run glassbox session import handoff.json --triage --cwd ../other-workspace
uv run glassbox session import handoff.json --cwd ../other-workspace
```

The exported package is inspectable JSON. It includes redacted session metadata,
lineage, transcript summaries, task summaries, checkpoint history, branch-search
summaries, artifact references, policy decisions, event summaries, redaction
notes, and a `handoff.summary` block. It does not copy the SQLite database or
embed artifact contents.

Add operator labels when the recipient needs custody context:

```bash
uv run glassbox handoff prepare session SESSION_ID handoff.json \
  --intent future-self \
  --recipient bob \
  --exported-by alice \
  --expected-custodian bob \
  --note "waiting on verification review" \
  --markdown-output handoff.md \
  --cwd .
```

Run import triage before importing when receiving a package. Triage validates
package compatibility, package digest posture, source summary, recipient
intent, included evidence, local-only omissions, redaction posture, unsupported
sections, limitations, safe first commands, and the recommended disposition
without writing local runtime state. Legacy session exports that pass triage can
then be imported for inspection. The receiving workspace gets a new historical
local session with imported transcript/history events, a durable imported
handoff inspection record, and `Resumable: no`. Import does not silently merge
into an existing live session or resume a provider stream.

Use `handoff inspect` for package-first triage across supported handoff package
types. For session packages it prints the same compatibility, redaction,
local-only, safe-command, and disposition details as `session import --triage`.
For changeset packages it prints the review bundle inspection summary. Add
`--markdown` to render supported session or changeset packages as reviewer-safe
Markdown without importing them.

After import or package creation, custody decisions are local workflow evidence.
They help humans coordinate follow-up, but they do not grant permissions or
block any policy-controlled operator path:

```bash
uv run glassbox handoff list --cwd .
uv run glassbox handoff show SESSION_ID PACKAGE_ID --cwd .
uv run glassbox handoff guidance SESSION_ID PACKAGE_ID --cwd .
uv run glassbox handoff accept SESSION_ID PACKAGE_ID \
  --accepted-by bob \
  --follow-up-intent verification-needed \
  --cwd .
uv run glassbox handoff reject SESSION_ID PACKAGE_ID \
  --reason "recipient cannot inspect local-only evidence" \
  --cwd .
uv run glassbox handoff archive SESSION_ID PACKAGE_ID \
  --reason "historical handoff retained" \
  --cwd .
```

Accept, reject, and archive actions append canonical local events and update the
handoff projection. Rejection preserves a reason and safe inspection commands;
archive hides the record from default handoff lists while keeping it available
with `--include-archived`. Guidance explains whether the recipient should keep
inspecting, fork from imported history, continue in a new local session, run
verification, refresh stale local state, or reject the handoff. Guidance does
not resume imported sessions or execute provider/tool work.

For changeset-centered review handoff, start with:

```bash
uv run glassbox changeset handoff-readiness CHANGESET_ID --cwd .
uv run glassbox handoff prepare changeset CHANGESET_ID changeset-review.json \
  --markdown-output changeset-review.md \
  --cwd .
uv run glassbox handoff inspect changeset-review.json --json --cwd .
uv run glassbox handoff inspect changeset-review.json --markdown --cwd .
```

The legacy `changeset export` and `changeset export-inspect` commands remain
supported review-centered paths and use the same package services.

The local API exposes the same inspection-first workflow for dashboard and
local clients:

```text
POST /handoffs/prepare-preview
POST /handoffs/exports
POST /handoffs/inspect
POST /handoffs/import-triage
POST /handoffs/imports
GET /handoffs/readiness
POST /handoffs/{session_id}/{package_id}/accept
POST /handoffs/{session_id}/{package_id}/reject
POST /handoffs/{session_id}/{package_id}/archive
```

API export and import routes use the same redacted package builders and
inspection-only import path as the CLI. Package inspection and import triage do
not mutate local state; custody actions remain workflow metadata, not approval,
authorization, verification success, or publication.

The local dashboard exposes the same workflow at `/app/handoffs`. The handoff
cockpit lists projected handoff records, prepares session/task/changeset
readiness previews, shows redaction and local-only inventory before export,
inspects package compatibility, runs import triage, imports supported session
packages as inspection-only state, loads fork-or-continue guidance, and records
accept, reject, or archive custody decisions. It keeps safe commands,
compatibility posture, redaction posture, local-only omissions, and non-claims
visible next to actions. Browser actions remain explicit local actions: the
dashboard does not approve verification, resume imported live turns, transfer
runtime ownership, stage, commit, push, publish, merge, or expose raw logs.

The full-screen TUI exposes the same inspection-first starting points through
`/handoff`, `/handoff readiness`, `/handoff preview`, `/handoff inspect`,
`/handoff custody`, and `/handoff dashboard`. These entries render compact safe
commands or open the local cockpit; they do not silently export, import, accept,
reject, archive, resume, approve, stage, commit, push, publish, or merge.

The changeset export is the preferred review-centered bundle when a changeset
exists. It includes redacted summaries, verification posture, reviewer-safe
evidence graph slices, review feedback and response posture, manual evidence,
handoff readiness, safe inspection commands, a redaction report, and non-claims.
It does not include raw `.glassbox` database state, raw command output, raw
provider transcripts, raw diffs, file contents, raw screenshots, browser traces,
or accessibility transcripts.

Changeset handoff readiness preserves its existing review-loop state names for
commit-preparation and publication-boundary compatibility, and also carries a
shared v17 readiness block with `changeset` source kind, review-only intent,
safe inspection commands, local-only evidence, accepted-risk, stale-evidence,
and non-claim fields aligned with session and task handoff readiness.

Session and changeset exports now accept recipient-oriented profile metadata:
`--intent`, `--recipient`, `--expected-custodian`, `--exported-by`, `--note`,
and `--format`. Supported intents are `review-only`, `continue-work`,
`verification-needed`, `failure-triage`, `release-signoff`, `future-self`, and
`fork-recommended`. The exported payload records the chosen profile, required
and optional sections, local-only evidence treatment, safe inspection commands,
and profile-specific non-claims. Existing exports keep the stable default:
review-only JSON.

When `--markdown-output` is supplied, exports also write a reviewer-safe human
handoff summary with objective, source, recipient intent, current posture,
included evidence, local-only evidence, stale or missing evidence, accepted
risks, safe first commands, recipient checklist, non-claims, and redaction
summary. Markdown is a render target for people; JSON remains the stable package
contract.

## Safe Inspection First

Before acting on a handoff, inspect what travelled and what stayed local:

```bash
uv run glassbox session import handoff.json --triage --cwd .
uv run glassbox session status SESSION_ID --cwd .
uv run glassbox session handoff-readiness SESSION_ID --intent review-only --cwd .
uv run glassbox session compactions SESSION_ID --cwd .
uv run glassbox changeset show CHANGESET_ID --cwd .
uv run glassbox changeset verification-plan CHANGESET_ID --cwd .
uv run glassbox changeset handoff-readiness CHANGESET_ID --cwd .
uv run glassbox observability status --cwd .
uv run glassbox observability handoff-readiness --source workspace --cwd .
uv run glassbox observability handoff-readiness --source release --cwd .
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

Use export preview before writing a package when shareability matters:

```bash
uv run glassbox session export SESSION_ID --preview --json --cwd .
uv run glassbox changeset export CHANGESET_ID changeset-review.json \
  --preview --json --cwd .
```

The preview uses the same in-memory payload builders and redaction paths as the
eventual export, then reports included sections, redacted categories, local-only
evidence counts, omitted raw categories, package limitations, and safe inspection
commands. Preview does not write the package, Markdown summary, raw artifacts,
raw logs, provider output, screenshots, or raw diffs.

Local-only evidence inventory is itemized separately from the raw contents. The
inventory names category counts, affected claim IDs, recipient limitations, and
safe local inspection commands for evidence such as managed artifacts, manual
evidence, browser/dashboard/accessibility observations, provider evidence, raw
command logs, raw transcripts, screenshots, repository-intelligence snapshots,
and release evidence. It is included in session and changeset export payloads
and in redaction previews so a package cannot silently lean on evidence that did
not travel.

## Workspace And Release Handoff Summaries

Workspace and release-candidate handoff summaries are read-only readiness views
over existing observability evidence:

```bash
uv run glassbox observability handoff-readiness --source workspace --cwd .
uv run glassbox observability handoff-readiness --source release --json --cwd .
```

The workspace summary pulls from runtime owner posture, projections, operator
queue inputs, task autonomy, background jobs, repository intelligence, memory,
artifacts, retained verification, provider-canary evidence, and maintenance
cues. The release summary focuses on retained eval evidence, release-surface
freshness, package/install smoke inspection paths, advisory provider evidence,
local-only limitations, safe first commands, and explicit non-claims. Neither
summary runs release gates, approves publication, transfers runtime ownership,
or exports raw `.glassbox` evidence.

## V17 Release-Candidate Track

The v17 local handoff track supports a shared handoff workflow across sessions,
tasks, changesets, workspaces, release evidence, and future-self continuity.
The foundational shared handoff models, v2 package compatibility
inspector, session/task/changeset readiness alignment, workspace/release
handoff summaries, redaction preview, local-only evidence inventory, and import
triage now exist in code. Recipient-oriented export profiles now carry intent,
recipient, custody labels, profile sections, local-only evidence treatment, and
non-claims on session and changeset exports. Markdown handoff summaries are
available for session and changeset exports, the handoff command family and
typed API routes are available, and the local dashboard cockpit is available at
`/app/handoffs`. Full-screen TUI handoff entry points are available for
inspection-first command rendering. Deterministic evals and the v17 release
gate scaffold are available; package and installed-smoke hardening,
dogfooding, and release-candidate guidance are recorded in the v17 evidence
docs.
Start with:

- [v17-local-handoff-contract.md](./v17-local-handoff-contract.md): shared
  intent, readiness, package, redaction, import triage, custody, surface, and
  non-claim vocabulary
- [v17-local-handoff-audit.md](./v17-local-handoff-audit.md): source-linked
  audit of current export, import, review bundle, readiness, queue, web, and
  dashboard surfaces
- [v17-dogfooding-summary.md](./v17-dogfooding-summary.md): sanitized
  dogfooding evidence and accepted residual risks
- [v17-release-candidate.md](./v17-release-candidate.md): supported
  release-candidate operating model, validation path, and decision
- [tasks-v17.md](./tasks-v17.md): dependency-ordered implementation graph for
  local handoff

Use the supported commands and dashboard cockpit above, and keep release
evidence, advisory evidence, and publication actions separate.

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

## Task Handoff Readiness

Use task handoff readiness when a durable plan needs to move to another
operator or future self without reconstructing the plan from raw session
history:

```bash
uv run glassbox task handoff-readiness TASK_ID --intent continue-work --cwd .
uv run glassbox task handoff-readiness TASK_ID --intent future-self --json --cwd .
```

The readiness output uses the same v17 handoff states as session readiness. It
keeps paused, blocked, failed, abandoned, and completed task states distinct;
surfaces missing or stale verification evidence; keeps accepted risk visible;
and links back to safe task, session, job, and eval inspection commands before
any continuation command is considered. The command is read-only and does not
approve, answer, continue, stage, commit, push, publish, or open a pull
request.
