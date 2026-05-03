# Commit Preparation

Commit preparation combines commit readiness, retained pre-commit/eval evidence,
and a deterministic commit-message suggestion into one read-only operator view.

```bash
uv run glassbox changeset commit-prep CHANGESET_ID --cwd .
uv run glassbox changeset commit-prep CHANGESET_ID --json --cwd .
```

The command reports:

- advisory commit-readiness state, reason, blockers, and safe next commands
- review-loop context: total feedback, unresolved feedback, stale response
  verification, accepted risks, manual evidence, and local-only evidence
- handoff-readiness posture so commit preparation does not hide final handoff
  blockers or limitations
- suggested commit message labeled as a suggestion only
- risky or ambiguous paths such as policy-sensitive, generated, unstaged, and
  untracked paths
- safe copy stating Glassbox did not stage, commit, push, or open a PR

Unresolved feedback, failed or stale response verification, manual evidence
that needs inspection, stale lifecycle briefs, accepted risk, and risky paths
remain visible even when the commit message draft can be generated. Passing
verification or a locally resolved response is not described as reviewer
approval unless separate retained evidence says so.

The dashboard exposes the same posture in the changeset review surface through
the Commit Preparation panel. The panel shows commit readiness, review-loop
counts, manual-evidence counts, handoff posture, risky paths, a suggested
message, and safe next commands. It is meant to prepare the operator for an
explicit manual commit, not to perform that commit.

Mutating git actions remain outside this workflow. Any future optional commit
action must be a separate, explicit approval-gated task with clean-worktree and
rollback semantics.
