# Change Inventory Artifact

The change inventory artifact is the v12 file-level review evidence contract
for a local changeset. It is summary-only evidence: it records changed paths,
classification, size hints, staged-state posture, policy-sensitive posture, and
source-reference placeholders, but it does not embed raw diffs or file
contents.

Current artifact kind:

```text
changeset_change_inventory
```

Current schema version: `1`.

## Shape

Each artifact contains:

- `artifact_kind`, `schema_version`, optional `changeset_id`, `source`, `scope`,
  and `path_filters`
- `redaction`, `raw_diff_included`, and `raw_file_contents_included`
- `limits`, `truncated`, and `size_limited`
- aggregate `summary` counts for changed, included, omitted, generated, test,
  docs, binary, policy-sensitive, and untracked paths
- `paths`, with one entry per included changed path
- `limitations`, naming non-claims such as missing provenance or truncation

Each path entry contains:

- relative `path`
- `change_kind`
- `insertions` and `deletions` when known
- `generated`, `test_file`, `docs_file`, and `policy_sensitive`
- `binary_posture`
- `staged_state`
- `source_evidence_refs`, `provenance_confidence`, and `provenance_note`

## Limits And Redaction

The default path limit is `500` entries and the default JSON byte limit is
`1,000,000` bytes. Builders may lower those limits for tests or constrained
artifacts. When a path or byte limit is reached, the artifact keeps aggregate
counts, sets `truncated` or `size_limited`, and records an explicit limitation.

Paths must be workspace-relative review paths. Absolute or parent-traversing
paths are replaced with `<redacted-path>`. The artifact redaction label is
`summary-only-no-raw-diff`.

## Non-Claims

A change inventory does not prove that:

- a file was changed by Glassbox rather than by a person or another tool
- verification is fresh for the current workspace
- the changeset is ready for review or commit
- raw diff hunks, secrets, command output, or file contents are safe to share

Later v12 tasks attach provenance, risk, freshness, verification readiness, and
review-brief generation to this artifact shape.
