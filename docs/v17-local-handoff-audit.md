# V17 Local Handoff Audit

For the docs hub and operator guides, start at [README.md](./README.md). Pair
this audit with the [v17 local handoff contract](./v17-local-handoff-contract.md)
and [tasks-v17.md](./tasks-v17.md). This is a planning audit, not released v17
behavior.

The current codebase already has valuable handoff pieces: session export/import,
changeset evidence export, changeset handoff readiness, reviewer-safe briefs,
review feedback response posture, manual evidence redaction, evidence graphs,
verification plans, and operator queue rows. The main v17 gap is that these
surfaces are command-specific. They do not yet share one package schema,
recipient-intent model, redaction preview, local-only evidence inventory, import
triage workflow, or custody decision trail.

## Command Help Spot Checks

The following help surfaces were checked during this audit:

```bash
uv run glassbox session export --help
uv run glassbox session import --help
uv run glassbox changeset export --help
uv run glassbox changeset handoff-readiness --help
```

Observed command shapes:

- `glassbox session export SESSION_ID [output]` writes an inspectable handoff
  package with optional `--exported-by`, `--expected-custodian`, `--note`, and
  `--json`.
- `glassbox session import PACKAGE` imports a session export package into local
  inspectable session state and says it does not silently merge with existing
  sessions.
- `glassbox changeset export CHANGESET_ID OUTPUT_PATH` writes a
  changeset-centered evidence package and can also write
  `--markdown-output`.
- `glassbox changeset handoff-readiness CHANGESET_ID` reports advisory
  review-loop handoff posture without staging, committing, pushing, opening a
  PR, merging, deploying, or publishing.

## Source-Linked Inventory

| Surface | Current Behavior | Source |
| --- | --- | --- |
| Session export CLI | Resolves runtime location, writes a package, and prints either JSON or a human path. | [session_state_commands.py](../src/glassbox/cli/session_state_commands.py#L216) |
| Session import CLI | Requires daemon-unowned local mutation, imports package as a completed historical session, and prints `Resumable: no`. | [session_state_commands.py](../src/glassbox/cli/session_state_commands.py#L250) |
| Session export package assembly | Builds a v1 package from session snapshot, events, tasks, checkpoints, branch-search summaries, artifacts, policy decisions, transcript, and redaction notes. | [session_export_package.py](../src/glassbox/runtime/session_export_package.py#L46) |
| Session export models | Defines `glassbox_session_export` v1 payload fields including metadata, lineage, `handoff`, transcript, artifacts, task summaries, checkpoint history, branch-search summaries, event summaries, and redaction notes. | [session_export_models.py](../src/glassbox/runtime/session_export_models.py#L28) |
| Session handoff summary | Builds latest objective, checkpoint posture, compaction posture, verification state, accepted risks, pending actions, lineage, knowledge posture, and safe inspection commands. | [session_export_handoff.py](../src/glassbox/runtime/session_export_handoff.py#L66) |
| Session export redaction | Replaces workspace root with `<workspace-root>`, redacts common secret-like tokens, and avoids embedding artifact contents. | [session_export_redaction.py](../src/glassbox/runtime/session_export_redaction.py#L16) |
| Session import validation | Rejects unredacted secret-looking material, validates v1 JSON, and rejects unsupported session export versions. | [session_import_validation.py](../src/glassbox/runtime/session_import_validation.py#L19) |
| Session import events | Creates a new local session with `SessionStarted`, a handoff runtime note, imported transcript/task/checkpoint events, and `SessionCompleted`. | [session_import_events.py](../src/glassbox/runtime/session_import_events.py#L23) |
| Session import facade | Supports `mode="inspect"` and explicitly rejects `mode="resumable"`. | [session_import.py](../src/glassbox/runtime/session_import.py#L38) |
| Changeset export CLI | Parser exposes export and export-inspect; export can also write reviewer-safe Markdown. | [parser_changeset_export.py](../src/glassbox/cli/parser_changeset_export.py#L9) |
| Changeset export payload | Builds a reviewer-safe package from changeset detail, verification preview, reviewer-safe evidence graph slice, handoff readiness, review brief, feedback, responses, manual/live evidence summaries, artifacts, redaction report, non-claims, and safe commands. | [changeset_export.py](../src/glassbox/runtime/changeset_export.py#L120) |
| Changeset export inspect | Reads a package and reports schema, changeset status, verification state, handoff state, evidence counts, redaction count, non-claims, and safe inspection commands without importing state. | [changeset_export.py](../src/glassbox/runtime/changeset_export.py#L198) |
| Changeset export Markdown | Renders a compact reviewer-safe Markdown summary for humans while JSON remains the stable package shape. | [changeset_export.py](../src/glassbox/runtime/changeset_export.py#L233) |
| Changeset handoff-readiness CLI | Parser and handler expose read-only handoff posture and JSON output. | [parser_changeset_review.py](../src/glassbox/cli/parser_changeset_review.py#L229) |
| Changeset handoff-readiness model | Returns state, reason, blockers, limitations, safe next actions, inventory/brief/verification IDs, plan summary, commit readiness, evidence counts, git summary, signals, and non-claims. | [handoff_readiness.py](../src/glassbox/runtime/handoff_readiness.py#L44) |
| Changeset handoff signals | Ranks publication boundary, provenance, inventory, review response, verification, brief, risk, manual evidence, and prior readiness signals. | [handoff_readiness_signals.py](../src/glassbox/runtime/handoff_readiness_signals.py#L66) |
| Handoff evidence counts | Counts feedback, unresolved/stale responses, manual evidence, local-only evidence, stale/manual needs-inspection evidence, browser/accessibility evidence, skipped live evidence, briefs, and accepted risks. | [handoff_readiness_evidence.py](../src/glassbox/runtime/handoff_readiness_evidence.py#L20) |
| Reviewer-safe review briefs | Defines redacted JSON/Markdown artifacts with non-claims, safe inspection commands, limitations, no raw logs/provider transcripts/diffs/file contents, and optional live evidence sections. | [review_briefs.py](../src/glassbox/runtime/review_briefs.py#L105) |
| Changeset web handoff route | Exposes `GET /changesets/{changeset_id}/handoff-readiness` as a typed FastAPI response. | [routes/changesets.py](../src/glassbox/web/routes/changesets.py#L529) |
| Changeset web route service | Calls the handoff readiness service and converts the assessment to the API response. | [changeset_route_actions.py](../src/glassbox/web/routes/changeset_route_actions.py#L358) |
| Dashboard API client | Fetches changeset handoff readiness from `/changesets/{id}/handoff-readiness`. | [client-changesets.ts](../frontend/api/client-changesets.ts#L138) |
| Dashboard store loading | Loads handoff readiness beside detail, verification plan, commit readiness, commit message, evidence graph, branch-search detail, and repository intelligence. | [changeset-store-loaders.ts](../frontend/stores/changeset-store-loaders.ts#L75) |
| Dashboard inspect handoff action | Refreshes handoff and commit readiness and reports a local action message. | [changeset-store-review-actions.ts](../frontend/stores/changeset-store-review-actions.ts#L153) |
| Dashboard handoff panel | Displays state, commit readiness, unresolved feedback, accepted risk, local-only evidence, skipped live evidence, blockers, limitations, safe next actions, and non-claims. | [handoff.tsx](../frontend/components/console/changeset/handoff.tsx#L12) |
| Operator queue aggregate | Builds rows from session, runtime, maintenance, and currently empty changeset producers. | [operator_queue.py](../src/glassbox/runtime/operator_queue.py#L26) |
| Changeset queue producer | Intentionally returns no rows because aggregate inputs do not yet include changeset detail, verification, inventory, feedback, or handoff inputs. | [operator_queue_changeset_items.py](../src/glassbox/runtime/operator_queue_changeset_items.py#L1) |

## Current Package Shapes

### Session Export v1

The current session package is `export_kind="glassbox_session_export"` with
`export_version=1`. It carries session metadata, lineage, a `handoff` block,
autonomy budget posture, redacted transcript messages, active tool calls,
pending approvals, turn metrics, artifact references, policy decisions, task
summaries, task-step summaries, task verification summaries, task event
references, checkpoint history, checkpoint event references, branch-search
summaries, event count, event summaries, and redaction notes.

Strengths:

- already portable JSON
- source workspace path redaction exists
- common secret-like values are redacted and import validation rejects obvious
  unredacted material
- artifact contents are referenced, not embedded
- import is inspection-only and creates historical local events
- handoff summary includes safe inspection commands

Gaps:

- no recipient intent field
- no shared v17 manifest with source kind, package kind, compatibility,
  digests, section inventory, local-only evidence summary, or raw-inclusion
  flags
- no pre-export redaction preview
- no package digest validation
- no import triage state before import
- no durable imported-package inspection record distinct from imported session
  history
- no custody accept/reject/archive workflow
- safe inspection commands are session-oriented and not yet typed shared
  handoff actions

### Changeset Export Package

The current changeset package uses a changeset-centered schema with
reviewer-safe summaries, redaction report, non-claims, and optional Markdown.
It is richer than session export for review evidence but is not a shared handoff
schema.

Strengths:

- includes verification posture, evidence graph summary and slice, review brief
  metadata, feedback, response posture, manual evidence, live-review evidence,
  handoff readiness, artifact references, redaction report, non-claims, and
  safe inspection commands
- export inspect is non-mutating
- Markdown is reviewer-safe and deterministic
- local-only manual evidence counts and limitations are visible in related
  readiness and Markdown surfaces

Gaps:

- not compatible with session export v1 shape
- no explicit recipient intent or export profile
- no pre-export preview that uses the exact export redaction path
- no digest summary or tamper inspection
- no import triage because changeset export-inspect is read-only package
  inspection, not handoff receiving workflow
- no custody workflow
- local-only evidence is summarized, but not yet a reusable inventory linked to
  affected portable claims

## Gap List By Subsystem

### Schema

- Add shared handoff intent, recipient, custodian, readiness, non-claim,
  compatibility, redaction, and local-only evidence models.
- Define package schema v2 with manifest, payload sections, supported and
  unsupported section lists, digests, raw-inclusion flags, and source metadata.
- Preserve v1 session import where practical and report compatibility warnings
  instead of hard failure for every legacy omission.

### Runtime

- Add readiness services for sessions, tasks, workspace, release, and
  future-self contexts.
- Build redaction preview from the same code path as export.
- Build local-only evidence inventory with affected claims, safe local
  inspection commands, and recipient limitations.
- Add import triage and fork-or-continue guidance before mutation.
- Keep imported historical sessions inspection-only unless a separate explicit
  fork or new-session flow is selected.

### Store

- Add canonical events or managed artifacts for package created, custody
  proposed, custody accepted, custody rejected, imported handoff inspected,
  imported handoff accepted for follow-up, and archived.
- Add rebuildable projections for latest handoff posture by source and imported
  package where needed.
- Avoid storing raw package contents in SQLite when a managed artifact is the
  better boundary.

### CLI

- Add a coherent `glassbox handoff` command family rather than requiring
  operators to know which legacy command owns session versus changeset behavior.
- Add `--intent`, `--recipient`, `--expected-custodian`, `--exported-by`,
  `--note`, `--format`, `--preview`, and Markdown output where appropriate.
- Preserve existing session and changeset command compatibility.
- Keep help text aligned with the v17 non-claims.

### Web

- Add transport-agnostic API routes for handoff list, prepare preview, export,
  package inspect, import triage, accept, reject, archive, and readiness.
- Add typed error handling for unsupported packages, redaction failures, missing
  source state, digest mismatch, and runtime owner conflicts.
- Avoid exposing raw logs, raw transcripts, screenshots, secrets, or raw
  package contents beyond the package contract.

### Frontend

- Build a local handoff cockpit over typed API responses.
- Extend beyond changeset handoff readiness to session/task/workspace/release
  sources, redaction preview, local-only inventory, import triage, custody
  actions, and follow-up queue rows.
- Maintain the dashboard as a projection, not source of truth.
- Keep disabled states and copy explicit for unsupported, local-only-heavy, and
  unsafe flows.

### Eval

- Add deterministic eval cases for session readiness, redaction preview,
  local-only inventory, export profiles, import triage, custody decisions,
  fork-or-continue guidance, and reviewer-safe handoff bundles.
- Keep browser/dashboard/accessibility/provider/manual evidence advisory unless
  a fixture-backed behavior is deliberately promoted.

### Release Gate

- Add a v17 release gate that inherits v16 deterministic checks and adds
  handoff package smoke, preview smoke, import triage smoke, custody smoke,
  CLI/API/frontend smoke, package contents, installed smoke, and advisory
  evidence separation.
- Keep release signoff as human custody evidence, not automatic publication.

### Docs

- Make the contract, audit, task graph, and local handoff guide discoverable
  while clearly labeling v17 planning versus released behavior.
- Update team workflow and reviewer evidence docs to point at the v17 track
  without implying package-version changes.
- Document command examples only after command behavior exists or mark them as
  planned.

### Dogfooding

- Exercise review-only, continue-work, verification-needed, failure-triage,
  future-self, local-only-heavy, rejected, and release-signoff handoffs.
- Preserve raw local evidence under `.glassbox/` and commit only sanitized
  summaries.
- Disposition findings as fix-now, docs, tests/evals, accepted risks, or
  post-v17 follow-up.

## Accepted Non-Goals For V17

- Hosted accounts, authentication, authorization, remote custody enforcement,
  role membership, or organization membership.
- Hosted task queues, remote review state, cloud evidence storage, remote
  repository indexing, remote workers, remote session sync, or remote workspace
  authority.
- Simultaneous multi-writer sessions or custody metadata as a runtime lock.
- Automatic staging, commits, pushes, pull requests, merges, deployments,
  package publication, or command approval.
- Treating handoff acceptance, reviewer-safe bundles, local-only evidence,
  manual evidence, browser evidence, accessibility evidence, provider canaries,
  repository intelligence, memory, or custody metadata as approval authority.
- Exporting raw `.glassbox` databases, raw transcripts, raw command logs, raw
  artifacts, raw diffs, screenshots, secrets, or credentials by default.
- Adding GitHub, PR, issue tracker, or hosted-review integration as part of
  v17.

## Risk Register

| Risk | Impact | Disposition |
| --- | --- | --- |
| Session export v1 and changeset export have different package shapes. | Operators may see handoff as two unrelated workflows. | Define schema v2 and compatibility inspection before broad export-profile work. |
| Current import creates historical session state immediately. | Recipients cannot triage package compatibility and local-only gaps before mutation. | Add import triage and durable imported-package inspection records. |
| Local-only evidence is counted in some changeset paths but not inventoried generically. | Portable claims can depend on evidence that did not travel. | Add local-only inventory linked to affected claims and readiness confidence. |
| Redaction is currently post-export/report oriented. | Operators may discover shareability problems after writing a package. | Add preview using the same redaction path as export. |
| Changeset queue rows are intentionally absent. | Handoff blockers can stay outside the unified operator queue. | Add handoff/custody producers once durable handoff state exists. |
| Custody metadata could be mistaken for authority. | Operators may treat accept/reject as approval or lock ownership. | Keep non-claims in models, command help, docs, and UI copy. |
| Package digests can be overinterpreted. | Recipients may treat integrity as source completeness. | Digest summaries must say they validate package integrity only. |
| Dashboard handoff currently focuses on changesets. | Session/task/import workflows remain CLI-only or undiscoverable. | Add cockpit surfaces after typed API routes exist. |

## Implementation Disposition

The next implementation slice should start with shared handoff models under a
focused core/runtime boundary. That lets session export, changeset export,
readiness services, API routes, frontend types, and future eval fixtures align
without prematurely rewriting every existing command.

The safest order remains:

1. Shared vocabulary and package manifest models.
2. Compatibility inspection for v1 and v2 package shapes.
3. Durable events/projections for package and custody decisions.
4. Readiness services by source type.
5. Redaction preview and local-only inventory.
6. Recipient profiles, Markdown rendering, import triage, custody actions, and
   cockpit surfaces.
