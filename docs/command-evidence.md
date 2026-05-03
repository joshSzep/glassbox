# Command Evidence

Glassbox v12 classifies retained command attempts so reviewers can tell what
kind of local evidence a command produced. The classification is advisory,
deterministic, and conservative: unknown commands are never counted as
verification proof simply because they ran.

## Purpose Classes

Command attempts may record one of these purpose classes:

- `inspect`: read-only review context such as `git diff`, `git status`, `rg`,
  `ls`, `sed`, `cat`, `head`, `tail`, `wc`, `pwd`, or `find`
- `test`: pytest or frontend test commands
- `lint`: ruff, eslint, or package lint commands
- `typecheck`: ty, mypy, pyright, TypeScript, or package typecheck commands
- `build`: local build commands such as frontend package builds
- `package`: local package-build commands that create artifacts without
  publishing them
- `eval`: `glassbox eval` commands
- `release_gate`: repository-owned release-gate scripts
- `publish`: package-publish commands that may mutate remote package state
- `deploy`: deploy commands that may mutate remote runtime state
- `cleanup`: local cleanup commands that may remove files or retained evidence
- `dangerous`: hard-blocked destructive command patterns
- `unknown`: commands that do not match the known review vocabulary

Review relevance is stored beside the purpose as `inspection`, `verification`,
`local_artifact`, `release_or_remote_mutation`, `cleanup_or_destructive`, or
`unknown`. Only `test`, `lint`, `typecheck`, `build`, `eval`, and
`release_gate` are marked as supporting verification evidence.

## Where It Appears

`ToolAttemptHeartbeat` now carries optional command evidence fields:

- `command_purpose`
- `command_review_relevance`
- `command_supports_verification`
- `command_purpose_reason`

The `tool_attempts` projection rebuilds these fields from canonical events.
They appear in `glassbox session tool-attempts`, `glassbox session
tool-attempt inspect`, `glassbox session status`, and session API payloads when
the original tool was a command tool.

Changeset review surfaces also derive a bounded command-evidence summary from
retained tool attempts. `glassbox changeset show`, `GET /changesets/{id}`, the
dashboard changeset detail view, and generated review briefs list important
command attempts with purpose, result, verification relevance, redacted
environment posture, output artifact references, and policy retry summaries
when retained. The summary is scoped to the changeset task when the changeset
has one; otherwise it uses session command evidence. It keeps failed commands
visible even if later verification passes, and it never copies raw stdout or
stderr into the changeset or brief.

## Environment And Drift

For verification and local package/artifact commands, Glassbox also records a
bounded `command_environment` summary. It includes:

- operating-system family and Python runtime version
- detected command toolchain versions, such as `python`, `uv`, `node`, `pnpm`,
  `npm`, `yarn`, `ruff`, `ty`, or `pytest` when those executables are relevant
  and available
- a tiny allowlisted environment subset such as `CI`, `GITHUB_ACTIONS`,
  `GIT_BRANCH`, and redacted `VIRTUAL_ENV`
- redaction notes and limitations

Glassbox does not persist raw environment variables, `PATH`, provider keys,
tokens, passwords, credentials, or absolute executable paths. Executable paths
are reduced to a basename behind `<redacted-path>`.

`glassbox session tool-attempt inspect` compares retained toolchain evidence
with the current local toolchain posture and prints drift warnings when a
recorded version is missing or has changed. Drift warnings are review cues, not
failure verdicts; stale or changed toolchains should send the operator to
inspect or rerun the relevant verification command explicitly.

## Non-Claims

Purpose classification does not execute commands, rerun checks, stage files,
commit, push, deploy, or publish. It also does not make command output true or
fresh. It only labels retained command evidence so review, retry, verification,
and later v12 command-evidence surfaces can interpret it without hidden model
memory.

When the classifier cannot recognize a command, Glassbox records `unknown` and
routes operators to inspect the command and output artifact directly before
treating it as review evidence.
