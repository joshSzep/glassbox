# Workspace Profiles

For the docs hub and workflow guides, start at [README.md](./README.md). For runtime provider credentials, pair this page with [providers.md](./providers.md).

Workspace profiles let a repository declare common local Glassbox defaults
without putting runtime secrets or local database state in source control.

The supported profile file is `glassbox.profile.json` at the selected `--cwd`
workspace root.

```json
{
  "profile_version": 1,
  "runtime": {
    "model_name": "openai:gpt-5.4",
    "approval_mode": "confirm",
    "autonomy_mode": "manual",
    "autonomy_budget_preset": "manual"
  },
  "autonomy": {
    "budget_presets": {}
  },
  "verification": {
    "eval_profile": "commit-smoke"
  }
}
```

## Runtime Defaults

`runtime.model_name` supplies the default model recorded when `glassbox session run` or
`glassbox session chat` starts a session.

`runtime.approval_mode` supplies the default approval posture for risky tool
actions. Supported values are:

- `confirm`
- `review`
- `on-request`
- `never`

These are defaults only. An operator can still pass `--model-name` or
`--approval-mode` for a specific command, and that explicit input wins.

`runtime.autonomy_mode` supplies the default bounded-autonomy posture. Supported
values are:

- `manual`
- `guided`
- `inspect`
- `edit-safe`
- `test-driven`
- `autonomous-local`
- `release-candidate`

`runtime.autonomy_budget_preset` names either a built-in budget preset with the
same name as an autonomy mode or a repository-defined preset under
`autonomy.budget_presets`. Budgets are explicit local limits: max steps, tool
calls, write operations, command operations, wall-clock seconds, verification
attempts, branch attempts, artifact bytes, and allowed risk buckets.

Autonomy mode is separate from approval mode. The autonomy mode selects a local
budget and escalation posture; it does not grant permissions by itself. Approval
mode still decides how approval-worthy actions are paused or blocked.

## Verification Defaults

`verification.eval_profile` supplies the default repository-owned eval profile
for:

- `glassbox eval run`
- `glassbox eval audit`

Passing `--profile` still wins for that invocation.

## Precedence

Glassbox resolves defaults in this order:

1. explicit CLI flags such as `--model-name`, `--approval-mode`, or `--profile`
2. `glassbox.profile.json`
3. built-in defaults where a workflow has one

Runtime-only provider configuration remains separate. `.env` and process
environment variables provide provider credentials and base URLs, but they do
not override model selection, approval mode, or eval profile routing.

For provider settings only, precedence is different: process environment values
override `.env`, and both remain runtime-only local configuration. Profiles do
not read or write provider secrets.

## Example Profiles

OpenAI with reviewable approval defaults:

```json
{
  "profile_version": 1,
  "runtime": {
    "model_name": "openai:gpt-5.4",
    "approval_mode": "confirm",
    "autonomy_mode": "test-driven",
    "autonomy_budget_preset": "small-local"
  },
  "autonomy": {
    "budget_presets": {
      "small-local": {
        "max_steps": 8,
        "max_tool_calls": 60,
        "max_write_operations": 8,
        "max_command_operations": 6,
        "max_wall_clock_seconds": 1800,
        "max_verification_attempts": 4,
        "max_branch_attempts": 1,
        "max_artifact_bytes": 8000000,
        "allowed_risk_buckets": ["read_only", "workspace_write", "command"]
      }
    }
  },
  "verification": {
    "eval_profile": "commit-smoke"
  }
}
```

Anthropic with a stricter review posture:

```json
{
  "profile_version": 1,
  "runtime": {
    "model_name": "anthropic:claude-sonnet-4",
    "approval_mode": "review"
  },
  "verification": {
    "eval_profile": "advisory-context"
  }
}
```

Offline deterministic local workflow:

```json
{
  "profile_version": 1,
  "runtime": {
    "model_name": "local-test-model",
    "approval_mode": "never"
  },
  "verification": {
    "eval_profile": "commit-smoke"
  }
}
```

After editing a profile, run:

```bash
uv run glassbox provider diagnostics --cwd .
uv run glassbox eval run --profile commit-smoke --cwd .
```

## Safety Rules

Profiles are reviewable repository files. They intentionally do not support API
keys, provider secrets, local database paths, or workspace-owner state.

Invalid profiles fail visibly before the command starts a session or eval run.
Unknown fields are rejected so misspelled or risky-looking configuration does
not get ignored silently.

Autonomy budget presets are rejected when they are internally contradictory. For
example, a preset cannot allow `workspace_write` with `max_write_operations: 0`,
and it cannot set a positive command budget without allowing the `command` risk
bucket.

## Troubleshooting

- A command used the wrong model or approval mode: check whether the command
  passed `--model-name` or `--approval-mode`; explicit flags override the
  profile for that invocation.
- `eval run` selected an unexpected profile: check whether `--profile` was
  passed. If not, inspect `verification.eval_profile` in `glassbox.profile.json`.
- Provider credentials were not picked up: keep them in the process environment
  or `.env` at the selected `--cwd`; workspace profiles do not contain secrets.
- Profile validation failed: remove unknown fields, confirm `profile_version` is
  `1`, and use only supported approval modes.

## Team Scope

A workspace profile is a shared convention file. It is not an owner lock, a
permission model, a credential store, or a remote coordination mechanism. The
runtime-owner boundary described in [team-workflows.md](./team-workflows.md) and
[persistent-runtime.md](./persistent-runtime.md) still decides who may append
live session events.
