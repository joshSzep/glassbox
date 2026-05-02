# Commit Preparation

Commit preparation combines commit readiness, retained pre-commit/eval evidence,
and a deterministic commit-message suggestion into one read-only operator view.

```bash
uv run glassbox changeset commit-prep CHANGESET_ID --cwd .
uv run glassbox changeset commit-prep CHANGESET_ID --json --cwd .
```

The command reports:

- advisory commit-readiness state, reason, blockers, and safe next commands
- suggested commit message labeled as a suggestion only
- risky or ambiguous paths such as policy-sensitive, generated, unstaged, and
  untracked paths
- safe copy stating Glassbox did not stage, commit, push, or open a PR

The dashboard exposes the same posture in the changeset review surface through
the Commit Preparation panel. It is meant to prepare the operator for an
explicit manual commit, not to perform that commit.

Mutating git actions remain outside this workflow. Any future optional commit
action must be a separate, explicit approval-gated task with clean-worktree and
rollback semantics.
