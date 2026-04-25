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
    "approval_mode": "confirm"
  },
  "verification": {
    "eval_profile": "commit-smoke"
  }
}
```

## Runtime Defaults

`runtime.model_name` supplies the default model recorded when `glassbox run` or
`glassbox chat` starts a session.

`runtime.approval_mode` supplies the default approval posture for risky tool
actions. Supported values are:

- `confirm`
- `review`
- `on-request`
- `never`

These are defaults only. An operator can still pass `--model-name` or
`--approval-mode` for a specific command, and that explicit input wins.

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

## Safety Rules

Profiles are reviewable repository files. They intentionally do not support API
keys, provider secrets, local database paths, or workspace-owner state.

Invalid profiles fail visibly before the command starts a session or eval run.
Unknown fields are rejected so misspelled or risky-looking configuration does
not get ignored silently.
