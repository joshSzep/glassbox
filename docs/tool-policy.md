# Tool Policy And Approval Semantics

This document describes the tool safety rules and approval behavior that are
implemented in Glassbox today. It is intended for operators who need to predict
how the runtime will handle tool calls before they happen.

## Scope

Glassbox evaluates tool calls through a local policy layer before execution.
That policy is separate from tool implementations themselves.

The current policy behavior is implemented in `src/glassbox/tools/policy.py`,
and approval / resume behavior is implemented in the runtime orchestration layer.

## Tool Risk Buckets

Each tool is assigned one coarse risk bucket:

- `read_only`: inspection-only tools that stay within the workspace
- `workspace_write`: tools that modify files inside the workspace
- `command`: tools that execute shell commands

Examples from the current toolset:

- `read_only`: `list_dir`, `read_file`, `search_files`, `git_status`, `ask_user`
- `workspace_write`: `apply_patch`
- `command`: `run_command`, `run_tests`

## Approval Modes

Glassbox currently accepts these approval modes:

- `confirm`
- `review`
- `on-request`
- `never`

These values are validated before session configuration is persisted. Invalid
approval modes are rejected at config or metadata update boundaries rather than
being silently written.

In the current implementation, `confirm`, `review`, and `on-request` all behave
the same at the policy gate: risky actions are allowed only after an explicit
approval step. The mode value is still persisted and surfaced so operators can
see which mode was chosen for the session.

`never` is stricter: actions that would normally require approval are blocked
instead of being suspended for approval.

If a persisted session row is later corrupted to contain an invalid approval
mode, runtime bootstrap treats that as a terminal session-scoped failure rather
than attempting to continue with ambiguous policy behavior.

## Decision Rules

The policy engine evaluates tools in this order:

1. Reject any path argument that resolves outside the workspace.
2. Allow in-scope `read_only` tools immediately.
3. Gate `workspace_write` tools through approval, unless approval mode is `never`.
4. For `command` tools, block destructive command patterns outright.
5. For other non-destructive commands, require approval unless approval mode is `never`.

This means a tool call can end in one of three practical outcomes:

- allowed immediately
- paused for approval
- blocked immediately

## Safe, Approval-Gated, And Blocked Examples

### Safe

These run immediately when they stay inside the workspace:

- `read_file path="README.md"`
- `list_dir path="src"`
- `git_status`
- `ask_user question="What colour should I use?"`

Read-only status does not mean “no effect on control flow”. `ask_user` is
read-only from a safety perspective, but it still suspends the turn until the
operator answers.

### Approval-Gated

These require approval in `confirm`, `review`, and `on-request` modes:

- `apply_patch` that edits files inside the workspace
- `run_command command="pytest -q"`
- `run_tests`

When approval is required, the runtime emits `ApprovalRequested`, marks the
session as awaiting approval, and stops the current turn until the operator
approves or denies it.

### Blocked

These are rejected immediately and do not enter the approval queue:

- any path that resolves outside the workspace
- workspace writes in approval mode `never`
- command execution in approval mode `never`
- destructive shell patterns such as:
  - `rm -rf ...`
  - `git clean -f`
  - `git reset --hard`
  - `mkfs`, `shutdown`, `reboot`, `poweroff`

Blocked tool requests fail the turn with a policy reason rather than pausing for
operator input.

That is intentionally a turn-scoped failure path. Policy rejections should
surface as `TurnFailed`, not `SessionFailed`, because the session remains
otherwise usable.

## Approval Lifecycle

### Runtime Behavior

When a tool call requires approval, the runtime:

1. persists `ApprovalRequested`
2. sets session state to `awaiting_approval`
3. records the pending approval in projections
4. completes the current turn with outcome `awaiting_approval`

When the operator resolves it, the runtime persists `ApprovalResolved` and then:

- if approved, resumes the suspended turn and executes the prepared tool call
- if denied, resumes the suspended turn with a denial tool return instead of running the tool

Approvals are tied to a session and approval ID. A resolved approval cannot be
resolved again.

### CLI Flow

The CLI exposes approval handling through:

```text
glassbox approve SESSION_ID APPROVAL_ID
glassbox deny SESSION_ID APPROVAL_ID
```

`glassbox status SESSION_ID` shows pending approvals and current turn context so
an operator can inspect the situation before deciding.

### Dashboard Flow

The dashboard reads pending approvals from the session snapshot endpoint and
sends approval decisions through:

```text
POST /sessions/{session_id}/approvals/{approval_id}
```

The browser then observes the resulting session updates through the SSE event
stream.

## `ask_user` Is Not An Approval

`ask_user` is a separate pause/resume path from approvals.

Differences from approval gating:

- it is treated as `read_only` by policy
- it never requires approval itself
- the turn engine intercepts it directly instead of calling the tool implementation
- it suspends the turn with `UserQuestionAsked`
- it resumes only after `UserAnswerProvided`

In other words, approvals are for gated risky actions; `ask_user` is for model-
driven operator input during a safe conversational workflow.

## Operator Expectations

You can reliably expect the following:

- in-scope read-only inspection tools run immediately
- in-scope writes and commands pause for approval unless the session is in `never`
- `never` blocks risky actions instead of queueing approvals
- destructive command patterns are blocked outright
- denying an approval does not execute the tool
- approving an approval resumes the suspended turn from persisted state
- `ask_user` pauses the turn for operator input without going through the approval queue

## Reference Implementation Surfaces

- Policy engine: `src/glassbox/tools/policy.py`
- Tool runtime gate: `src/glassbox/tools/runtime.py`
- Approval suspension / resume: `src/glassbox/runtime/turn_engine.py`
- Approval resolution service: `src/glassbox/runtime/supervisor.py`
- CLI approval commands: `src/glassbox/cli/__init__.py`
- Dashboard approval endpoint: `src/glassbox/web/routes/approvals.py`
