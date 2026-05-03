# Manual Evidence Attachment Contract

Manual evidence is local review-loop evidence that did not flow through
retained Glassbox command or tool-attempt instrumentation. It can help explain
what an operator saw, ran, received, inspected, or decided, but it must stay
honest about provenance and limits.

Manual evidence is not verification proof by itself, not command evidence, not
review approval, and not publication authority.

## Evidence Kinds

Use these kinds when later tasks add events, artifacts, CLI commands, API
routes, dashboard rows, lifecycle briefs, or evidence bundles:

| Kind | Purpose | Required boundary |
| --- | --- | --- |
| `manual_command` | Operator summarizes a shell command run outside retained Glassbox instrumentation. | Label as manual; include command purpose and result summary, not raw terminal dumps by default. |
| `external_check` | CI, hosted scanner, package registry, service dashboard, or another external system reported a result. | Name the external source label and retrieval time; do not claim Glassbox ran it. |
| `reviewer_note` | Reviewer comment, question, observation, or requested-change context was copied into local evidence. | Store bounded summary and reviewer label only; do not imply remote review state is synchronized. |
| `screenshot` | Local screenshot, browser capture, or image metadata supports the review loop. | Store metadata and local-only file reference first; raw image export requires a later reviewer-safe policy. |
| `browser_observation` | Operator records what a live browser or dashboard showed. | Advisory unless backed by deterministic Playwright or fixture evidence. |
| `accessibility_note` | Keyboard, screen-reader, contrast, reduced-motion, or other accessibility observation. | Advisory unless backed by a repeatable accessibility check with retained output. |
| `local_file_reference` | Existing local file, report, log, or artifact is cited without copying raw content. | Keep local-only path metadata; redact absolute paths in reviewer-safe summaries. |
| `sanitized_log` | A bounded, redacted excerpt or summary of an external log is attached. | Require redaction result, size limit, and source label; never accept unredacted secrets as reviewer-safe. |
| `operator_assertion` | Operator records a decision, rationale, limitation, or accepted risk. | Use "operator says" unless corroborated by retained evidence. |

## Attachment Targets

Manual evidence may attach to one or more local review-loop targets:

- a changeset
- a review feedback item
- a review response or response-linked inventory item
- a verification requirement or stale-verification decision
- a review brief or future lifecycle brief
- a publication-boundary or handoff-readiness decision

Each attachment must keep stable target IDs when available. If the target is
unknown or not yet implemented, the evidence must say so rather than relying on
model memory.

## Required Fields

Every manual evidence record should carry:

- evidence kind
- bounded summary
- source label
- source timestamp or observation timestamp
- attached target IDs
- created-by actor label
- local-only posture
- redaction status
- freshness posture
- limitations
- non-claims

Optional fields may include reviewer label, command text, external URL label,
local file reference, artifact ID, screenshot dimensions, accessibility axis,
or accepted-risk reason. Optional fields must still be bounded and redacted.

## Redaction And Size Rules

Manual evidence defaults to summary-first capture. Later implementation tasks
should reject, quarantine, or require explicit local-only treatment when input
appears to contain:

- credentials, API keys, tokens, private keys, cookies, or secret assignments
- raw provider transcripts or hidden provider output
- raw `.glassbox/` database state or artifact bodies
- absolute local paths in reviewer-safe text
- unbounded command output or raw logs
- binary content without metadata-only handling
- screenshots or files that have not been marked local-only or reviewed for
  export safety

Size limits should be small enough that reviewers can inspect the evidence and
large logs do not become disguised artifact dumps. Raw logs should be replaced
by sanitized summaries unless a later task defines a safe retained-log schema.

## Freshness Rules

Manual evidence has its own freshness posture. It becomes stale or needs
inspection when:

- the linked changeset inventory changes after the manual observation
- response-linked fixup inventory changes after the evidence was attached
- the cited local file reference moves, disappears, or is regenerated
- the external check is older than the current workspace digest
- the evidence cites a verification requirement that is failed, skipped,
  missing, or stale
- the operator accepts risk instead of rerunning a relevant check

When freshness is stale, surfaces should start with safe inspection commands:

```bash
glassbox changeset show CHANGESET_ID --cwd .
glassbox changeset feedback show FEEDBACK_ID --cwd .
glassbox changeset verification-plan CHANGESET_ID --cwd .
```

Manual evidence should never recommend publish, deploy, push, merge, or release
commands as a freshness repair.

## Manual Evidence Versus Command Evidence

Retained command evidence means Glassbox recorded a tool attempt, command
purpose, status, bounded output reference, environment summary, and policy
context through its own instrumentation.

Manual evidence means an operator, reviewer, external system, browser, file, or
note supplied evidence outside that retained path.

Do not backfill manual command summaries as retained command evidence. Do not
mark external check summaries as verification proof unless a later task defines
an explicit verification import contract. Use "manual evidence attached",
"operator says", "external check reported", or "evidence cites" according to
provenance.

## Reviewer-Safe Language

Prefer:

- "manual evidence attached"
- "operator says"
- "external check reported"
- "screenshot metadata is local-only"
- "sanitized log summary attached"
- "evidence is stale; inspect before relying on it"

Avoid:

- "Glassbox ran this command" for manual command summaries
- "verified" for external or manual-only evidence
- "reviewer accepted" or "review approved"
- "safe to publish", "safe to push", or "ready to merge"
- "attached raw log" without a redaction and size boundary

## Redaction Fixture Plan

GBX-1331 adds deterministic fixtures for:

- secret-looking strings in notes and logs
- absolute paths and `.glassbox/` paths
- oversized command output
- raw provider transcript snippets
- local-only screenshot and file references
- sanitized log excerpts that pass size and redaction checks
- manual command summaries that remain distinct from retained command evidence

Each fixture should assert the evidence kind, redaction result, local-only
posture, target IDs, freshness posture, limitations, and non-claims.

## Implemented Store Contract

Manual evidence is now represented by local canonical events for attachment,
rejection, supersession, and archive decisions. The projection stores the
manual evidence lifecycle state, evidence kind, target reference, source label,
artifact reference, redaction status, freshness posture, limitations, and
non-claims. Query helpers hide rejected, archived, and superseded evidence by
default unless an operator explicitly asks to include invalidated records.

The retained artifact schema is summary-first:

- `artifact_kind` is `manual_evidence`
- `schema_version` is `1`
- raw logs, raw provider output, and raw file contents are always marked absent
- screenshot and local file references are metadata-only and local-only
- artifact non-claims state that the evidence is not retained command
  evidence, deterministic verification proof, review approval, or publication
  authority

Inputs that appear to contain secret assignments, private keys, absolute local
paths, `.glassbox/` state paths, raw provider snippets, or oversized logs are
rejected before artifact capture. Rejection records retain only the finding
class and bounded reason, not the unsafe source text.

## Operator Workflow

Attach summary-first evidence with explicit manual provenance:

```bash
glassbox changeset evidence attach CHANGESET_ID \
  --kind external_check \
  --summary "external CI reported green" \
  --source-label "external-ci" \
  --freshness current \
  --cwd .
```

Evidence can target a review feedback item:

```bash
glassbox changeset evidence attach CHANGESET_ID \
  --kind manual_command \
  --summary "operator says pytest passed outside Glassbox" \
  --source-label "operator-shell" \
  --feedback FEEDBACK_ID \
  --cwd .
```

Browser and dashboard observations have guided capture commands that still
write summary-first manual evidence with local-only screenshot metadata:

```bash
glassbox changeset evidence browser CHANGESET_ID \
  --summary "browser rendered the feedback list" \
  --source-label local-browser \
  --route /console/changesets \
  --environment local-dev \
  --browser chromium \
  --viewport 1440x900 \
  --cwd .

glassbox changeset evidence dashboard CHANGESET_ID \
  --summary "dashboard showed feedback and manual evidence" \
  --source-label dashboard-local \
  --route /console/changesets \
  --environment local-dev \
  --browser chromium \
  --viewport 1440x900 \
  --screenshot-file .glassbox/evidence/CHANGESET_ID/dashboard/inbox.png \
  --screenshot-width 1440 \
  --screenshot-height 900 \
  --freshness needs_inspection \
  --cwd .
```

Accessibility observations have a dedicated capture command for keyboard,
screen-reader, focus-order, wrapping, contrast, and responsive review notes:

```bash
glassbox changeset evidence accessibility CHANGESET_ID \
  --kind focus_order_issue \
  --summary "focus leaves the feedback dialog" \
  --source-label keyboard-review \
  --environment local-dev \
  --tool "manual keyboard" \
  --route /console/changesets \
  --observed-issue "Tab moved focus behind the dialog" \
  --severity high \
  --disposition paired_with_feedback \
  --feedback FEEDBACK_ID \
  --freshness needs_inspection \
  --cwd .
```

Inspect retained manual evidence before relying on it:

```bash
glassbox changeset evidence list --changeset CHANGESET_ID --cwd .
glassbox changeset verification-plan CHANGESET_ID --cwd .
glassbox changeset brief CHANGESET_ID --cwd .
```

The dashboard changeset detail view shows a manual evidence inbox alongside
review feedback. The inbox displays kind, state, redaction posture, freshness,
target, artifact reference, limitations, and non-claims. Browser, dashboard,
and accessibility evidence rows link back to their local changeset, feedback,
or response target and are labeled advisory and local-only. Accessibility rows
keep severity, disposition, follow-up, and pairing details in the retained
limitations so unresolved observations remain visible. The inbox does not mark
manual evidence as verification proof, reviewer approval, publication
readiness, release authority, accessibility certification, or retained command
evidence.

## Non-Claims

Manual evidence does not mean:

- Glassbox ran the command
- the evidence is deterministic release authority
- verification is current
- a reviewer accepted the response
- a pull request is approved
- files were staged, committed, pushed, published, merged, or deployed
