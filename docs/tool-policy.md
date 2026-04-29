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

- `read_only`: `list_dir`, `read_file`, `search_files`, `git_status`, `workspace_diff_summary`, `test_discovery`, `test_target_selection`, `ask_user`
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

Without an explicit non-manual autonomy mode and budget, `confirm`, `review`,
and `on-request` all remain conservative: risky actions are allowed only after
an explicit approval step. When a session has a resolved autonomy budget, the
policy gate calibrates approval mode as follows:

| Approval mode | Read-only | Workspace write | Command |
| --- | --- | --- | --- |
| `confirm` | allow in scope | request approval | request approval |
| `review` | allow in scope | allow only when the autonomy budget includes `workspace_write`; otherwise request approval | request approval |
| `on-request` | allow in scope | allow default-gated writes when budgeted; explicit workspace `approve` rules still request approval | allow default-gated commands when budgeted; explicit workspace `approve` rules still request approval |
| `never` | allow in scope | block approval-gated writes | block approval-gated commands |

This keeps existing sessions compatible while making `review` useful for
budgeted local edits and `on-request` useful for budgeted local workflows where
the repository can still name explicit approval stops.

`never` is stricter: actions that would normally require approval are blocked
instead of being suspended for approval.

If a persisted session row is later corrupted to contain an invalid approval
mode, runtime bootstrap treats that as a terminal session-scoped failure rather
than attempting to continue with ambiguous policy behavior.

## Autonomy Modes And Budgets

Autonomy mode is a separate control from approval mode. Approval mode describes
how Glassbox handles risky actions when policy says they need operator review.
Autonomy mode describes how much local work Glassbox may attempt before it must
pause with durable evidence.

The supported autonomy modes are:

- `manual`: no autonomous steps; the operator drives work explicitly
- `guided`: small read-only continuations for inspected plans
- `inspect`: broader read-only repository inspection
- `edit-safe`: bounded workspace edits without command execution
- `test-driven`: bounded edits plus targeted local command/test execution
- `autonomous-local`: larger local implementation budgets
- `release-candidate`: stricter release-focused verification budgets

Every autonomy mode resolves to an explicit budget with max steps, tool calls,
write operations, command operations, wall-clock seconds, verification attempts,
branch attempts, artifact bytes, and allowed risk buckets. Budget exhaustion,
approval required, policy blocked, verification failed, provider unavailable,
daemon unavailable, and ambiguous plan are first-class escalation reasons.

Autonomy mode does not override hard invariants. Workspace-scope checks,
destructive command blocks, approval mode, and repository policy still apply.

### Configuring Autonomy From The CLI

Session-start commands accept `--autonomy-mode` and
`--autonomy-budget-preset`. Explicit CLI values win over `glassbox.profile.json`,
and profile values win over built-in defaults. The same autonomy selection flags
are accepted by `session message` and `session resume` so scriptable follow-up
flows can surface the intended budget posture alongside the operation.

Use `glassbox autonomy profile list` to inspect built-in modes and workspace
budget presets. Use `glassbox autonomy profile show [preset] --json` when a
script needs the resolved budget fields after CLI/profile/default resolution.

Common operator postures:

- Manual inspection: `--autonomy-mode manual` keeps work operator-driven.
- Test-driven repair: `--autonomy-mode test-driven --autonomy-budget-preset test-driven` allows bounded local edits and targeted tests.
- Bounded local implementation: `--autonomy-mode autonomous-local` gives a larger local budget while preserving hard policy stops.
- Release candidate verification: `--autonomy-mode release-candidate` focuses authority on verification and release checks.

### Inspecting Budget Evidence

`glassbox session status SESSION_ID` shows the latest autonomy budget posture:
mode, last decision, escalation reason, exhausted limit, and remaining step/tool/
write/command budget. The same posture is available in session snapshot API
responses as `budget_posture`, and portable session exports include
`autonomy_budget_posture` so handoffs keep the budget evidence with the session.

Budget exhaustion means the bounded local work allowance has run out; choose a
smaller next step, select a tighter prompt, or request an override rather than
assuming the tool failed. Policy blocks are different: they mean repository
policy or a hard invariant stopped the action, so inspect the policy trace or
approval behavior before continuing. Verification failures mean the work ran but
the configured checks did not pass.

## Decision Rules

The policy engine evaluates tools in this order:

1. Reject any path argument that resolves outside the workspace.
2. Allow in-scope `read_only` tools immediately.
3. Gate or allow `workspace_write` tools according to approval mode, repository policy, and the resolved autonomy budget.
4. For `command` tools, block destructive command patterns outright.
5. For other non-destructive commands, gate or allow according to approval mode, repository policy, and the resolved autonomy budget.

This means a tool call can end in one of three practical outcomes:

- allowed immediately
- paused for approval
- blocked immediately

## Repository-Owned Autonomy Rules

`glassbox-policy.json` can include `autonomy_rules` for local workflows the
repository understands well. These rules run after hard invariants and explicit
`rules`, but before default risk-bucket policy. They cannot allow paths outside
the workspace or destructive command patterns.

Supported autonomy rule actions are:

- `allow-with-budget`: allow the match only when the active autonomy budget has the matching risk bucket and budget field, such as `max_write_operations` or `max_command_operations`
- `require-approval`: pause even when a broader budget would otherwise allow the action
- `deny`: block the match without requesting approval
- `require-verification`: pause with verification-required evidence until a later task wires automated verification gates

Supported selectors are `tool_name`, `risk_buckets`, `command_prefixes`,
`cwd_prefixes`, `path_prefixes`, `file_extensions`, `test_path_prefixes`,
`generated_path_prefixes`, `read_only_operation`, and `max_timeout_seconds`.

Example:

```json
{
  "manifest_version": 1,
  "autonomy_rules": [
    {
      "rule_id": "targeted-unit-tests",
      "action": "allow-with-budget",
      "tool_name": "run_command",
      "command_prefixes": ["uv run pytest tests/unit/"],
      "max_timeout_seconds": 120
    },
    {
      "rule_id": "generated-json-snapshots",
      "action": "allow-with-budget",
      "tool_name": "apply_patch",
      "generated_path_prefixes": ["generated", "tests/snapshots"],
      "file_extensions": [".json"]
    }
  ]
}
```

Each decision records the autonomy rule ID and the budget field that allowed or
paused work so status views, exports, and replay comparisons can explain why a
local action continued.

## Safe, Approval-Gated, And Blocked Examples

### Safe

These run immediately when they stay inside the workspace:

- `read_file path="README.md"`
- `list_dir path="src"`
- `git_status`
- `workspace_diff_summary scope="workspace"`
- `test_discovery paths=["tests"]`
- `test_target_selection changed_paths=["src/glassbox/runtime/verification.py"]`
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
glassbox session approve SESSION_ID APPROVAL_ID
glassbox session deny SESSION_ID APPROVAL_ID
```

`glassbox session status SESSION_ID` shows pending approvals and current turn context so
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

## Inspecting Policy Evidence

Every evaluated tool request records policy evidence from the decision that was
made at runtime. The durable trace includes:

- `outcome`: `allow`, `approve`, `deny`, or `blocked`
- `risk_level`: `read_only`, `workspace_write`, or `command`
- `source_kind`: `invariant`, `rule`, or `default`
- `source_label`: the invariant name, rule ID, or default risk bucket that won
- `reason`: the operator-facing explanation for the decision

Use `glassbox session status SESSION_ID` for a quick operator view. Pending
approvals and recent tool activity include the outcome, risk level, policy
source kind and label, and the reason that explains why the tool was allowed,
paused for approval, denied, or blocked.

In the dashboard, pending approval cards show the policy outcome, risk level,
and source as separate badges, with the reason below the subject. The Actions
pane uses the same evidence for active tools and approvals so an operator can
confirm whether a decision came from a hard invariant, a repository rule, or a
default risk posture before acting.

User-facing terminals and dashboard badges use these labels:

- `advisory risk accepted`: the action was allowed, but the risk/source remains
  visible as evidence
- `approval required`: the action is paused until an operator approves or denies
  it
- `denied by policy`: repository policy denied the action
- `invariant block`: a non-overridable runtime guard blocked the action

Portable session exports include a `policy_decisions` array built from the
canonical event log. Each entry points back to the event sequence, tool call or
approval ID, and the structured trace above. This makes handoff packages
inspectable even after the live session has moved on.

Replay tool-request manifests preserve the evaluated `policy_decision` for the
captured request. Treat that as replay/eval evidence: a replay that changes the
effective decision surface should be reviewed as policy drift, even if the tool
schema and transcript are otherwise unchanged.

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

## Workspace Policy Configuration

`GBX-331` implements the first repository-owned policy manifest at:

```text
glassbox-policy.json
```

The file is optional. When it is absent, Glassbox keeps the current default
behavior:

- `read_only` defaults to `allow`
- `workspace_write` defaults to `approve`
- `command` defaults to `approve`

When present, the manifest is versioned JSON with explicit defaults and
top-to-bottom rule matching.

Example:

```json
{
  "manifest_version": 1,
  "defaults": {
    "read_only": "allow",
    "workspace_write": "approve",
    "command": "approve"
  },
  "rules": [
    {
      "rule_id": "allow-git-status",
      "tool_name": "run_command",
      "action": "allow",
      "command_prefixes": ["git status"]
    },
    {
      "rule_id": "allow-docs-patches",
      "tool_name": "apply_patch",
      "action": "allow",
      "path_prefixes": ["docs"]
    }
  ]
}
```

Supported action values are:

- `allow`
- `approve`
- `deny`

Supported selectors in the first manifest version are:

- exact `tool_name`
- `command_prefixes` for command-style tools
- `cwd_prefixes` for bounded working-directory matching
- `path_prefixes` for in-workspace path arguments

Rules are matched in declaration order. The first matching rule wins. If no
rule matches, the configured defaults apply.

Path prefixes must be relative to the workspace root. Absolute path prefixes,
unknown fields, duplicate `rule_id` values, unsupported manifest versions, and
invalid action values are rejected as invalid policy configuration.

## Approval Mode And Config Interaction

Workspace policy resolves to one of three normalized actions:

- `allow`
- `approve`
- `deny`

Approval mode is applied after that resolution:

- `allow` executes immediately
- `approve` pauses for approval in `confirm`, `review`, and `on-request`
- `approve` becomes blocked in `never`
- `deny` blocks immediately

That means repository policy can deliberately allow a bounded action even when
the session approval mode is `never`, but it cannot bypass hard runtime
invariants such as workspace-scope checks or destructive-command blocking.

## V7 Repository Governance Contract

`GBX-760` keeps the manifest format above as the v7 governance baseline. The
purpose is not to create a larger permission system; it is to make repository
policy reviewable, explainable, and safe for local teams that want policy
changes to go through code review.

### Manifest Ownership

`glassbox-policy.json` is owned by the repository. Treat it like application
configuration, not like a local secret file or an operator preference. A policy
change should be reviewed with the same care as a script that changes what the
agent can do.

The manifest shape is intentionally small:

- `manifest_version`: currently `1`
- `defaults`: actions for `read_only`, `workspace_write`, and `command`
- `rules`: ordered refinements with `rule_id`, exact `tool_name`, `action`, and
  optional `command_prefixes`, `cwd_prefixes`, or `path_prefixes`

Every action is one of `allow`, `approve`, or `deny`. Unknown fields,
unsupported versions, duplicate rule IDs, absolute path prefixes, and prefixes
that escape the workspace are invalid configuration.

### Precedence And Invariants

The effective decision order is:

1. Validate hard runtime invariants.
2. Match repository rules from top to bottom; the first matching rule wins.
3. Fall back to the manifest defaults for the tool risk bucket.
4. Translate `approve` through the session approval mode.

Hard invariants always outrank repository policy. A repository rule cannot:

- allow a path argument outside the workspace
- allow a destructive command pattern such as `rm -rf`, `git clean -f`, or
  `git reset --hard`
- make an unregistered or unknown tool executable
- make invalid manifest content silently fall back to a safer-looking default
- turn an `approve` decision into execution when approval mode is `never`

Rules and defaults can only refine behavior inside those guardrails. For
example, a repo may allow `run_command` for `git status` immediately, require
approval for build commands, and deny package-manager commands. It may not use a
command prefix to bless destructive shell syntax.

### Default Risk Posture

When no manifest exists, or when no rule matches, the default posture remains:

- `read_only`: `allow`
- `workspace_write`: `approve`
- `command`: `approve`

Approval mode is session-scoped. `confirm`, `review`, and `on-request` currently
pause on `approve`; `never` blocks `approve`. `allow` remains immediate unless a
hard invariant already blocked the request, and `deny` blocks immediately in all
approval modes.

### Review Expectations

Review policy changes by asking:

- Which exact tool is affected?
- Is the selector narrow enough for the intended workflow?
- Does the rule use relative workspace prefixes where path scope matters?
- Is the action appropriate for the risk bucket and approval mode used by the
  team?
- Is there a focused test or fixture that proves the intended decision and the
  nearest blocked boundary?
- Will replay or eval evidence need refreshing because the effective policy
  decision surface changed?

Prefer named `rule_id` values that explain intent, such as
`allow-docs-patches`, `approve-package-install`, or `deny-generated-output`.
Avoid catch-all command prefixes unless the repository has a clear reason and
tests for the boundary.

### Fixture Strategy

Policy fixtures should be small JSON manifests that exercise one posture at a
time. Keep examples free of secrets, host-specific absolute paths, personal
workspace names, tokens, or private service URLs.

Reviewable example manifests live in `docs/examples/tool-policy/`:

- `default-review.json`: preserves the built-in default posture
- `docs-write-allowlist.json`: allows bounded docs patches while keeping other
  writes approval-gated
- `local-command-governance.json`: allows narrow local status and validation
  commands using command and cwd selectors
- `deny-publish-commands.json`: denies common publish commands without changing
  unrelated command defaults

Useful fixture families are:

- baseline defaults with no rules
- bounded read-only or status command allowance
- docs-only or generated-file write allowance
- command families that still require approval
- deny rules for package managers, deploy commands, or generated output
- invalid manifests for duplicate IDs, absolute prefixes, unsupported versions,
  and unknown fields

Tests should cover both the allowed path and the nearest invariant block. For
example, a fixture that allows docs patches should also prove an out-of-workspace
path is still blocked.

### Recommended Validation For Policy Changes

After editing `glassbox-policy.json`, the policy engine, policy config loading,
or the example manifests, run focused validation before relying on the new
posture:

```text
uv run pytest tests/unit/test_tools_policy.py
uv run pytest tests/integration/test_approval_workflow.py
uv run glassbox eval recommend glassbox-policy.json src/glassbox/tools/policy.py --cwd .
```

If the recommendation output names `approval.approved-patch`, include that case
or the profile that contains it in the eval run for the change. For manifest-only
edits, the policy unit tests are the primary boundary because they prove rule
matching, defaults, denies, and invariant blocks without re-running policy logic
in the frontend or CLI.

### Non-Goals

Repository policy is not:

- remote enforcement authority for another machine or service
- a secret store
- a marketplace trust or plugin certification system
- a replacement for OS permissions, sandboxing, code review, or provider
  credential hygiene
- a way to run arbitrary policy code inside the Glassbox runtime
- a team identity, role-based access, or multi-tenant authorization system

Glassbox policy is local-first runtime governance. It explains and gates tool
requests made by this runtime against this workspace.

### Migration Notes

No manifest shape change is required for v7. Existing `manifest_version: 1`
files remain valid.

Teams adopting repository-owned policy should start by committing a manifest
that preserves the defaults, then add narrow rules with focused tests. If a
future task changes the manifest shape, it should provide an explicit version
bump, fixture migration, and replay/eval impact guidance rather than silently
changing how an existing `manifest_version: 1` file resolves.
