# Tool Policy And Approval Semantics

For the docs hub and workflow guides, start at [README.md](./README.md). For operator command flows, pair this reference with [interactive-workflows.md](./interactive-workflows.md).

This document describes the tool safety rules and approval behavior that are
implemented in Glassbox today. It is intended for operators who need to predict
how the runtime will handle tool calls before they happen.

It also records the v2 governance contract chosen in `GBX-330` so later policy
work can extend the current runtime without reopening the safety model from
scratch.

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

## V2 Governance Model

`GBX-330` keeps the current coarse policy engine as the compatibility baseline,
but defines a stronger boundary for workspace-owned governance.

The key rule is that Glassbox should separate these concerns explicitly:

- hard runtime safety invariants that never become repository-tunable
- tool-declared baseline risk classification from the registry
- repository-owned workspace policy that can refine tool behavior
- session approval mode that decides how approval-worthy actions are handled at runtime

The runtime may still collapse policy evaluation to the same three practical
outcomes used today:

- allowed immediately
- paused for approval
- blocked immediately

The important v2 change is that those outcomes should come from a resolved,
inspectable policy model rather than only from hard-coded risk buckets.

### Hard Invariants Versus Configurable Policy

The following remain non-overridable runtime invariants:

- path arguments that resolve outside the workspace are blocked
- destructive command patterns remain blocked outright
- unknown tools or invalid policy configuration fail visibly rather than falling back silently
- approval mode `never` never executes an action that policy classifies as approval-worthy

Workspace policy may refine what happens inside those guardrails, but it must
not weaken them.

That means repository policy can decide that some in-workspace writes or some
command shapes are allowed immediately, approval-gated, or denied, but it
cannot authorize out-of-workspace paths, suppress destructive-command blocking,
or reinterpret `never` as an implicit approval.

### Resolution Layers

The chosen v2 resolution order is:

1. validate hard runtime invariants such as workspace scope, destructive command blocking, and tool registration
2. load the tool's coarse baseline classification from the registry
3. apply the normalized workspace policy rules that match the tool and its arguments
4. translate any `approve` result through the session's approval mode

This keeps the existing `ToolPolicyEngine` shape usable while making room for a
resolved policy input that is richer than `ToolRiskLevel` alone.

The compatibility baseline remains:

- `read_only` defaults to allow
- `workspace_write` defaults to approve
- `command` defaults to approve after destructive-command blocking

Later policy tasks may refine those defaults through repository configuration,
but they should not erase them from the model.

### Rule Shape

The first configurable model should stay typed, local-first, and reviewable.
`GBX-330` chooses a rule model built from explicit selectors and outcomes,
not arbitrary policy code.

The supported rule scopes should be:

- per-tool controls keyed by exact tool name
- per-argument controls for stable argument classes such as path arguments and bounded string or enum arguments
- per-command controls for command-style tools using inspectable command selectors such as exact command, prefix, or approved subcommand families

The supported outcomes should be:

- `allow`
- `approve`
- `deny`

Rule matching should stay deterministic and normalized. The policy layer should
not evaluate arbitrary Python, shell, or user-defined expressions as part of
policy resolution.

### Approval Mode Compatibility

Approval mode remains a session-scoped operator posture, not a replacement for
workspace policy.

The chosen compatibility contract is:

- workspace policy decides whether a request is `allow`, `approve`, or `deny`
- `confirm`, `review`, and `on-request` continue to turn `approve` into an explicit approval pause for now
- `never` converts `approve` into `deny`
- `allow` remains immediate in all approval modes unless a hard invariant already blocked the request

This preserves the current operator mental model while allowing repositories to
be more specific about which actions deserve immediate execution versus approval.

### Replay And Drift Compatibility

Replay already treats tool schema and policy state as part of manifest
equivalence. `GBX-330` makes that rule more precise.

For replayable turns, Glassbox should record a normalized effective policy
snapshot that includes:

- the session approval mode relevant to the turn
- the matched workspace policy rules or normalized defaults relevant to the requested tool calls
- the hard policy version or fingerprint for invariants that affect decision outcomes

The following should count as replay-manifest drift when they change the
effective decision surface for the recorded turn:

- approval mode changes
- changes to matched per-tool, per-argument, or per-command rules
- changes to normalized defaults that affect the recorded tool requests
- changes to hard invariants that alter allow versus approve versus deny outcomes

The following should not count as manifest drift by themselves:

- comments, descriptions, or formatting changes in policy files
- reordering that preserves the same normalized matched result
- rules for unrelated tools never referenced by the recorded turn
- dashboard or CLI presentation changes that do not alter policy resolution

This keeps replay focused on effective governance behavior rather than on every
incidental edit to a repository-owned policy file.

### Planned Implementation Boundary

`GBX-330` defines the model only. The implementation split for follow-on work is:

- `GBX-331`: repository-owned policy config format, loading, validation, and resolution
- `GBX-332`: richer decision metadata, summaries, and audit surfaces
- `GBX-333`: command-envelope hardening and clearer command failure classification

Those tasks should extend the current local policy engine and approval runtime
instead of replacing them with a separate governance subsystem.
