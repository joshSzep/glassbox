# Review Briefs

Review briefs are v12 reviewer-safe artifacts for local changesets. They are
designed to summarize what a reviewer needs to inspect without copying raw
`.glassbox` state, provider transcripts, raw command logs, raw diffs, or local
workspace files.

The first contract is intentionally schema-first. Later tasks generate briefs
from changeset evidence and attach them to projections; this task defines the
artifact shape those generators must produce.

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

## Non-Claims

A review brief does not prove that:

- every changed line was verified
- stale verification is safe
- local-only artifacts are shareable
- a commit, push, PR, or merge should happen automatically
- raw evidence has been reviewed unless the brief says so

Use the brief as an index into retained evidence and safe inspection commands,
not as a replacement for code review.
