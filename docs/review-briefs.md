# Review Briefs

Review briefs are v12 reviewer-safe artifacts for local changesets. They are
designed to summarize what a reviewer needs to inspect without copying raw
`.glassbox` state, provider transcripts, raw command logs, raw diffs, or local
workspace files.

Briefs are generated deterministically from retained changeset evidence. The
generator writes a redacted JSON artifact, appends a
`ChangesetReviewBriefCreated` event, and updates the changeset projection with
the latest brief artifact ID. It also records an advisory review readiness
decision so "ready to review" is backed by the same local evidence.

## Artifact Shape

Review brief JSON artifacts use:

- `artifact_kind`: `changeset_review_brief`
- `schema_version`: `1`
- `redaction`: `reviewer-safe-summary-no-raw-logs`
- `render_targets`: `markdown` and `json`
- `redacted`: `true`
- raw inclusion flags for command output, provider transcripts, diffs, and file
  contents, all fixed to `false`

Required sections are:

- objective
- change summary
- changed-file inventory
- affected subsystems when topology evidence is available
- provenance
- verification
- risks
- non-claims
- reviewer checklist
- safe inspection commands

Branch-candidate rationale is optional because not every changeset comes from
branch search. When it is present, it must cite retained candidate evidence
rather than copying candidate logs.

## Evidence References

Brief sections cite evidence references instead of flattening raw logs. A
reference names a kind, identifier, short summary, and optional artifact or
verification ID. Identifiers and summaries are redacted before rendering.

Supported evidence kinds are:

- `changeset`
- `inventory`
- `provenance`
- `verification`
- `branch_candidate`
- `risk`
- `artifact`
- `operator_note`

## Redaction And Retention

The contract redacts local absolute paths, `.glassbox/` paths, and common secret
forms before JSON or Markdown rendering. Review briefs are summary artifacts;
they do not include raw command output, provider prompts or responses, raw diffs,
or raw file contents.

The default artifact may be portable when the content has been reviewed. If a
brief cites local-only evidence, the generating task must mark `local_only` or
the specific evidence reference as local-only and keep the raw evidence under
local `.glassbox/` custody.

## Markdown Target

The Markdown render target starts with the changeset ID, schema version,
redaction label, and local-only posture. It then renders the required sections,
evidence references, reviewer checklist, safe commands, non-claims, and any
limitations. Markdown is for reviewer convenience; the JSON artifact remains the
stable contract for later tooling.

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
provenance confidence, retained verification posture, verification readiness,
branch-candidate evidence when present, risks, limitations, and safe inspection
commands. Missing inventory, unloaded artifacts, stale workspace digests, stale
topology, missing verification, failed checks, and accepted-risk evidence are
rendered as limitations instead of being smoothed over.

Review readiness is advisory. A brief can be ready for review while still
showing unresolved review risks; later commit-readiness work decides whether
those risks block commit preparation.

## Non-Claims

A review brief does not prove that:

- every changed line was verified
- stale verification is safe
- local-only artifacts are shareable
- a commit, push, PR, or merge should happen automatically
- raw evidence has been reviewed unless the brief says so

Use the brief as an index into retained evidence and safe inspection commands,
not as a replacement for code review.
