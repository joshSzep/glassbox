# Commit Message Suggestions

Glassbox can draft a deterministic commit message suggestion for a changeset
without taking the commit action. The suggestion is assembled from retained
changeset evidence and live read-only commit-readiness posture.

```bash
uv run glassbox changeset commit-message CHANGESET_ID --cwd .
uv run glassbox changeset commit-message CHANGESET_ID --style conventional --json --cwd .
```

The dashboard/API equivalent is:

```http
GET /changesets/{changeset_id}/commit-message?style=plain
```

## Evidence Used

The suggestion may include:

- changeset objective and summary
- task title and current task status when the task record is available
- changed-path count and bounded path examples from the verification plan
- verification readiness state and summary
- commit-readiness state and reason
- risk level plus unresolved and accepted risk counts

The message generator does not call a model, inspect raw diffs, include file
contents, include raw command output, stage files, run `git commit`, push, or
claim the operator should use the draft unchanged.

## Output Shape

Every response is labeled with
`suggestion_label: suggestion_only_not_committed`. The payload includes the
`subject`, body evidence lines, full `message`, `commit_readiness_state`,
evidence references, limitations, and non-claims.

The default `plain` style uses the changeset objective as the subject after
whitespace cleanup and terminal punctuation removal. The optional
`conventional` style only adds a deterministic prefix from path evidence:
`docs:` for docs-only changes, `test:` for test-only changes, and `chore:` for
mixed or unknown changes.

Operators are expected to edit the suggestion before committing. Later Phase
125 tasks can add richer commit-preparation guidance and retained pre-commit
evidence without changing this non-mutating boundary.
