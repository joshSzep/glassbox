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

## Non-Claims

Purpose classification does not execute commands, rerun checks, stage files,
commit, push, deploy, or publish. It also does not make command output true or
fresh. It only labels retained command evidence so review, retry, verification,
and later v12 command-evidence surfaces can interpret it without hidden model
memory.

When the classifier cannot recognize a command, Glassbox records `unknown` and
routes operators to inspect the command and output artifact directly before
treating it as review evidence.
