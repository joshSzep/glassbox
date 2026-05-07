# Review Briefs

Review briefs are reviewer-safe artifacts for local changesets. v12 briefs
summarized the initial reviewable-change evidence. v13 lifecycle briefs extend
that artifact contract so the same reviewer-safe surface can summarize the full
local review loop: feedback, fixup responses, manual evidence,
browser/dashboard/accessibility observations, stale verification, accepted
risks, and publication-boundary posture.

Briefs are generated deterministically from retained changeset evidence. The
generator writes a redacted JSON artifact, appends a
`ChangesetReviewBriefCreated` event, and updates the changeset projection with
the latest brief artifact ID. It also records an advisory review readiness
decision so "ready to review" is backed by the same local evidence.

## Artifact Shape

Review brief JSON artifacts use:

- `artifact_kind`: `changeset_review_brief`
- `schema_version`: `2` for v13 lifecycle-capable briefs
- `redaction`: `reviewer-safe-summary-no-raw-logs`
- `render_targets`: `markdown` and `json`
- `redacted`: `true`
- raw inclusion flags for command output, provider transcripts, diffs, and file
  contents, all fixed to `false`

Required baseline sections are:

- objective
- change summary
- changed-file inventory
- affected subsystems when topology evidence is available
- provenance
- verification
- command evidence
- risks
- non-claims
- reviewer checklist
- safe inspection commands

Lifecycle-capable v13 briefs may also include these structured sections:

- lifecycle summary
- review feedback
- review responses
- manual evidence
- live review evidence for browser, dashboard, and accessibility observations
- stale verification
- publication boundary

Generation commands may omit an optional lifecycle section only when no retained
evidence exists for that section yet. Once feedback, response, manual evidence,
browser/accessibility evidence, stale verification, accepted risks, or handoff
posture exist, lifecycle generation must keep that posture visible instead of
flattening it into generic prose.

Branch-candidate rationale is optional because not every changeset comes from
branch search. When it is present, it must cite retained candidate evidence
rather than copying candidate logs.

## Lifecycle Brief Contract

A lifecycle brief is deterministic. It is generated from retained canonical
events, projections, artifacts, verification posture, command evidence, and
explicit manual evidence records. It must not call a model merely to polish the
summary, and it must not rely on hidden conversation memory for review-loop
state.

Lifecycle briefs answer these questions:

- what changed in the local changeset
- what feedback, requested changes, questions, accepted risks, and operator
  notes were recorded
- what responses or fixups claim to address that feedback
- which manual, browser, dashboard, accessibility, command, and verification
  evidence supports the response posture
- which checks are stale, missing, failed, skipped, or accepted with risk
- whether the local handoff posture is blocked, limited, or ready for an
  operator's next explicit action

Lifecycle summaries must keep unresolved feedback, stale response
verification, local-only evidence, and accepted risks near readiness language.
Passing verification does not hide unresolved feedback, and a response record
does not imply the reviewer accepted it.

## Evidence References

Brief sections cite evidence references instead of flattening raw logs. A
reference names a kind, identifier, short summary, and optional artifact or
verification ID. Identifiers and summaries are redacted before rendering.

Supported evidence kinds are:

- `changeset`
- `inventory`
- `provenance`
- `verification`
- `command`
- `feedback`
- `response`
- `manual_evidence`
- `browser_evidence`
- `dashboard_evidence`
- `accessibility_evidence`
- `readiness`
- `publication_boundary`
- `branch_candidate`
- `risk`
- `artifact`
- `operator_note`

Evidence references must cite retained identifiers, artifact IDs, verification
IDs, or local evidence IDs. They must not copy raw logs, screenshots, diffs,
provider transcripts, browser traces, or raw file contents into the brief.

## Redaction And Retention

The contract redacts local absolute paths, `.glassbox/` paths, and common secret
forms before JSON or Markdown rendering. Review briefs are summary artifacts;
they do not include raw command output, provider prompts or responses, raw diffs,
raw screenshots, browser traces, or raw file contents.

The default artifact may be portable when the content has been reviewed. If a
brief cites local-only evidence, the generating task must mark `local_only` or
the specific evidence reference as local-only and keep the raw evidence under
local `.glassbox/` custody.

## Render Targets

The Markdown render target starts with the changeset ID, schema version,
redaction label, and local-only posture. It then renders the required sections,
optional lifecycle sections, evidence references, reviewer checklist, safe
commands, non-claims, and any limitations. Markdown is for reviewer
convenience; the JSON artifact remains the stable contract for later tooling.

The JSON target is the authoritative render target for CLI/API/dashboard/export
consumers. New lifecycle sections should be added as explicit JSON fields before
downstream surfaces depend on them.

## Generating A Brief

Use the changeset command after creating or refreshing the changeset evidence:

```bash
glassbox changeset brief <changeset-id> --cwd .
```

For structured output:

```bash
glassbox changeset brief <changeset-id> --cwd . --json
```

For reviewer-friendly Markdown on stdout:

```bash
glassbox changeset brief <changeset-id> --cwd . --format markdown
```

The dashboard/API equivalent is:

```http
POST /changesets/{changeset_id}/brief
```

with an optional body:

```json
{"actor": "operator", "include_markdown": true}
```

The action does not run verification commands. It summarizes current inventory
freshness, changed-file classifications, affected packages/apps/docs roots from
topology when available, topology freshness, owner and dependency hints,
provenance confidence, retained review feedback, response posture, manual
evidence, browser/dashboard/accessibility observations, retained verification
posture, response-level verification freshness, verification readiness, command
evidence summaries, branch-candidate evidence when present,
publication-boundary posture, risks, limitations, and safe inspection commands.

## Rich-Evidence Limitation Overflow

`GBX-1410` characterizes the current v13/v14-start failure mode: lifecycle brief
generation deduplicates limitations, but a changeset with more than 20 retained
limitations still fails artifact validation because the reviewer-safe
`limitations` field is capped at 20 items.

`GBX-1411` should replace that brittle behavior with deterministic
summarization before artifact validation:

- preserve raw retained limitations in canonical events and managed artifacts
- deduplicate repeated limitations before counting overflow
- keep high-severity blockers visible ahead of lower-priority advisory notes
- cap the reviewer-safe `limitations` list at the artifact limit
- add an overflow summary that names how many limitations were summarized and
  why
- keep ordering deterministic so replay, eval, API, dashboard, and export
  artifacts remain stable

Until that fix lands, rich manual, browser/dashboard, accessibility, response,
command, inventory, or verification evidence can make brief generation fail
when the retained limitation set exceeds the artifact cap.
Missing inventory, unloaded artifacts, unresolved feedback, stale response
verification, stale workspace digests, stale topology, missing verification,
failed checks, missing command evidence, failed command attempts, local-only
evidence, and accepted-risk evidence are rendered as limitations or explicit
section evidence instead of being smoothed over.

Review readiness is advisory. A brief can be ready for review while still
showing unresolved review risks. v13 lifecycle briefs also distinguish
review-loop handoff posture from commit readiness and final publication; later
publication-boundary work decides how those signals appear in final handoff and
commit-preparation surfaces.

## Non-Claims

A review brief does not prove that:

- every changed line was verified
- stale verification is safe
- review feedback was approved or accepted by a reviewer
- a fixup response fully resolved the requested change
- manual evidence is retained command/tool evidence
- browser, dashboard, or accessibility evidence is deterministic release proof
- lifecycle handoff readiness means publication occurred
- local-only evidence is portable or shareable
- local-only artifacts are shareable
- a commit, push, PR, or merge should happen automatically
- raw evidence has been reviewed unless the brief says so

Use the brief as an index into retained evidence and safe inspection commands,
not as a replacement for code review.
