# Worktree Isolation

Glassbox v12 uses temporary local git worktrees as an explicit safety boundary
for branch-candidate experimentation. A worktree can give an operator a
separate checkout for inspection or bounded follow-up work, but it does not
change the v12 reviewable-change contract: Glassbox remains local-first,
operator-controlled, and evidence-oriented.

Worktree isolation is not a merge workflow. Creating, listing, inspecting, or
cleaning up a Glassbox-managed worktree must not automatically merge, rebase,
cherry-pick, stage, commit, push, or open a pull request. Candidate adoption is
a separate explicit workflow that previews evidence before any mutation.

## Scope

The v12 worktree isolation contract covers temporary local checkouts created to
inspect or continue branch-search candidates and reviewable local changes.

Supported behavior:

- create a temporary local worktree under a safe local root
- assign an operator-readable candidate branch name
- record creation evidence with worktree path, branch name, base revision,
  source changeset or branch-search candidate, owner process, and custody
  metadata when available
- list worktrees with freshness, current git status, cleanup posture, and
  related changeset or branch-search evidence
- inspect a worktree before cleanup or candidate adoption
- clean up a Glassbox-managed worktree only after explicit operator
  confirmation and a risk summary
- retain creation and cleanup evidence in canonical events or managed
  artifacts so projections can rebuild the worktree history

Unsupported behavior:

- automatic merge, rebase, cherry-pick, squash, or history rewriting
- automatic staging, committing, pushing, pull request creation, or remote
  collaboration
- remote or multi-user locking
- deleting unknown user changes during cleanup
- treating a temporary worktree as authoritative over the main workspace
- hiding missing, stale, conflicted, or unsupported git-worktree state behind
  optimistic review copy

## Worktree Custody Model

A Glassbox-managed worktree has a narrow custody record:

| Field | Meaning |
| --- | --- |
| `worktree_id` | Stable local Glassbox identifier for the temporary checkout. |
| `path` | Local filesystem path, redacted in reviewer-facing exports when needed. |
| `branch_name` | Local candidate branch name created or inspected for the worktree. |
| `base_revision` | Git revision used as the checkout base. |
| `source_kind` | Source such as branch-search candidate, changeset, task, session, or manual workspace request. |
| `source_id` | Local source identifier when available. |
| `owner_process` | Runtime or CLI process that created the worktree when known. |
| `state` | Active, missing, dirty, cleanup-ready, cleanup-blocked, cleaned, or unsupported. |
| `created_at` / `updated_at` | Local event timestamps for custody evidence. |

Custody is evidence, not exclusive access control. It helps the operator answer
"what created this checkout and what is safe to do next?" It does not prevent a
human from editing files in the worktree with ordinary tools, and Glassbox must
therefore inspect git status before cleanup or adoption.

## Naming

Glassbox-created branch names should be local, descriptive, and collision-safe.
The default shape is:

```text
glassbox/<short-source>/<short-id>-<slug>
```

Examples:

```text
glassbox/branch-search/bs-42-targeted-repair
glassbox/changeset/cs-17-review-fix
```

If a name already exists, the implementation should choose a deterministic
suffix or ask for an explicit name. Branch names are local evidence labels; they
are not a push target, PR name, or merge instruction.

## Creation Rules

Creation commands must start with safe inspection:

```bash
git rev-parse --show-toplevel
git worktree list --porcelain
git status --short
```

The workflow should reject or degrade gracefully when:

- the directory is not a git repository
- `git worktree` is unavailable or unsupported
- the requested base revision cannot be resolved
- the destination path is outside the configured safe local roots
- the destination path exists and is not an empty Glassbox-created directory
- branch-name creation would overwrite an existing unrelated branch
- repository state cannot be inspected without ambiguity

Creation should append evidence before presenting the worktree as usable. Large
or local-only details, such as absolute paths and raw command output, should be
kept in managed artifacts with redaction rather than copied into portable
review briefs.

Create a temporary worktree:

```bash
uv run glassbox worktree create \
  --session SESSION_ID \
  --source branch-search-candidate \
  --branch-search BRANCH_SEARCH_ID \
  --candidate CANDIDATE_ID \
  --base HEAD \
  --cwd .
```

The command writes a `WorktreeCreated` event with the worktree ID, local path,
candidate branch name, base revision, source identifiers, owner process, and
created-by actor. The default destination is a sibling local directory named
`<repo>.glassbox-worktrees/WORKTREE_ID`, outside the main checkout so the
temporary worktree does not nest under the repository's `.glassbox/` runtime
state. Custom paths are rejected unless they remain under that safe local root.

Inspect worktrees:

```bash
uv run glassbox worktree list --cwd .
uv run glassbox worktree status WORKTREE_ID --cwd .
```

`status` records a `WorktreeStatusRecorded` event with path existence, dirty
posture, current branch, HEAD revision, bounded `git status --short` lines, and
safe next actions. `list` rebuilds custody from canonical events and live git
inspection; it does not append new evidence.

## Cleanup Rules

Explicit cleanup confirmation is mandatory because removing a worktree can discard
local files that Glassbox did not create or cannot safely classify.

Cleanup is potentially destructive, so it must be explicit. A cleanup preview
must inspect the worktree and report:

- whether the worktree path still exists
- current branch and HEAD revision
- tracked, unstaged, staged, and untracked changes
- ignored-file posture when available
- whether the branch has unmerged or unpushed local commits
- related changeset, review brief, inventory, and verification evidence
- the exact safe inspection command to run before confirming cleanup

Glassbox may remove a worktree only when all of these are true:

- the worktree is Glassbox-managed or the operator explicitly identifies it
- the operator confirms cleanup after seeing the risk summary
- there are no uncommitted or untracked user changes, or the operator gives a
  separate explicit destructive confirmation for those changes
- cleanup does not delete raw `.glassbox` state, reviewer exports, or unrelated
  repository paths

If cleanup is blocked, the next action should be an inspection command rather
than a mutation. For example:

```bash
git -C <worktree-path> status --short
git worktree list --porcelain
```

Clean up a worktree:

```bash
uv run glassbox worktree cleanup WORKTREE_ID --confirm --cwd .
```

Dirty worktrees are blocked by default and record a `WorktreeCleanupRecorded`
event with `cleanup_blocked`. Removing a dirty worktree requires the additional
explicit flag:

```bash
uv run glassbox worktree cleanup WORKTREE_ID \
  --confirm \
  --discard-user-changes \
  --cwd .
```

That flag is destructive and should be used only after inspecting the risk
summary. The cleanup command never merges, rebases, commits, pushes, or opens a
pull request.

## Candidate Adoption Boundary

Worktree isolation makes branch-candidate adoption inspectable, not automatic.
An adoption workflow must preview the candidate diff inventory, verification
posture, conflicts, risk, stale evidence, and accepted risks before any
mutation in the main workspace.

Selecting or adopting a branch-search candidate may append local changeset
evidence that links the candidate, worktree, inventory, verification, and
review brief. It must not merge the candidate into parent history as a side
effect of selection. Any actual git mutation remains an explicit operator
decision after the preview.

## Reviewer And Export Posture

Reviewer-facing artifacts should treat worktree paths as local-only evidence.
Review briefs and changeset exports may cite a worktree ID, branch name, base
revision, source candidate, cleanup state, and evidence artifact IDs. They
should not include raw command output, raw diffs, absolute paths, or local
environment details unless those fields are redacted and explicitly labeled.

## Git Fixture Design Notes

Implementation tests for `GBX-1261` should use temporary git repositories with
small commits and local branches. The fixture set should cover:

- repository with `git worktree` support
- non-git directory
- existing destination path
- branch-name collision
- clean worktree cleanup
- dirty tracked file cleanup block
- untracked file cleanup block
- missing worktree path recovery
- unsupported or failing git command degradation

The tests should assert both command behavior and retained evidence. Cleanup
tests must not rely on broad filesystem deletion; they should operate only
inside temporary directories owned by the test.

## Related Guides

- [branch-search.md](./branch-search.md)
- [branching.md](./branching.md)
- [change-inventory.md](./change-inventory.md)
- [review-briefs.md](./review-briefs.md)
- [commit-preparation.md](./commit-preparation.md)
- [tool-policy.md](./tool-policy.md)
