# Pre-Commit Evidence For Changesets

Glassbox can retain summary-only local pre-commit or eval evidence against a
changeset. This is an explicit recording workflow: it does not run hooks, run
evals, stage files, commit, push, or change repository pre-commit behavior.

```bash
uv run glassbox changeset record-precommit CHANGESET_ID \
  --summary .glassbox/evals/pre-commit/summary.json \
  --kind eval-report \
  --json \
  --cwd .
```

The summary file is read locally and reduced to bounded fields such as status,
profile ID, pass/fail counts, total count, verification stage, and summary
text. The retained artifact does not include raw command output or raw file
contents.

## Readiness Mapping

Recorded evidence updates advisory `commit` readiness:

| Evidence State | Commit Readiness State |
| --- | --- |
| `passed` | `ready` |
| `failed` | `failed_checks` |
| `stale` | `stale_inventory` |
| `missing` | `needs_verification` |

Commit readiness still combines this retained evidence with live git status,
inventory freshness, review brief freshness, verification posture, and path-risk
signals. Passing pre-commit evidence can therefore be cited while the overall
commit-readiness preview remains blocked by unstaged or untracked files.

## Artifact Boundary

The retained `changeset_precommit_evidence` artifact includes:

- evidence kind: `pre-commit` or `eval-report`
- evidence state and summary
- source path and SHA-256 digest for local traceability
- bounded parsed fields
- non-claims and redaction markers

It intentionally excludes raw hook output, raw eval case output, raw diffs, file
contents, provider transcripts, and raw `.glassbox` database state.
