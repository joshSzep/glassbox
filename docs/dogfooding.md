# Real-Repository Dogfooding Protocol

This protocol turns real Glassbox use into actionable v9 evidence without
committing private source, transcripts, provider output, credentials, or large
local artifacts. Use it when running Glassbox against ordinary repositories to
find product friction before a release-candidate decision.

Dogfooding evidence is advisory product evidence. It can identify fixes, docs
gaps, eval candidates, and accepted residual risks, but deterministic replay,
eval, package, and release-gate evidence remain the blocking release authority.

## Evidence Location

Keep raw dogfooding artifacts local unless they are explicitly sanitized:

```text
.glassbox/dogfooding/v9/<pass-id>/
    evidence.md
    summary.json
    artifacts/
```

Use a pass ID that does not reveal a private customer, repository, branch, or
ticket name. Suggested shape:

```text
YYYYMMDD-HHMM-workflow-slug
```

Examples:

- `20260429-0930-repository-inspection`
- `20260429-1100-small-edit-verification`
- `20260429-1400-branch-search-plan`

Only commit sanitized summaries or docs updates. Raw `.glassbox/` evidence is
local operator material by default.

## Required Pass Mix

A v9 dogfooding set should include at least these three workflows:

| Workflow | Purpose | Minimum Evidence |
| --- | --- | --- |
| Repository inspection and explanation | Test first-run context, repository index freshness, and terminal/dashboard clarity without making edits. | readiness state, command path, dashboard use, friction, outcome |
| Small code edit with verification | Test approval posture, tool policy, focused validation, and evidence drill-down. | task, changed surface, verification command, stop reason, outcome |
| Longer task-plan or branch-search workflow | Test bounded autonomy, planning visibility, branch comparison, and recovery cues. | autonomy mode, budget posture, plan or candidate evidence, decision, outcome |

Include at least one deterministic no-live-provider flow. Include one
credentialed provider flow when credentials are available and the provider
redaction rules below can be satisfied. If a provider flow is skipped, record
the explicit skip reason instead of treating the pass as failed.

## Evidence Template

Copy this template into the local `evidence.md` for each pass.

```markdown
# Dogfooding Evidence: <pass-id>

- Date:
- Operator:
- Repository alias:
- Repository type:
- Workflow:
- Glassbox version or commit:
- Workspace:
- Provider mode:
- Provider posture:
- Autonomy mode:
- Budget posture:
- Dashboard used:
- Terminal used:
- Raw artifact location:
- Sanitized summary committed:

## Goal

<What real task was attempted?>

## Setup

- Commands:
- Readiness state:
- Repository index state:
- Memory state:
- Daemon/runtime state:
- Provider diagnostics:

## Execution Notes

- Session/task IDs:
- Key Glassbox surfaces used:
- Approvals or questions:
- Verification path:
- Dashboard observations:
- Stop reason:

## Friction Findings

| Area | Finding | Evidence | Severity | Candidate Disposition |
| --- | --- | --- | --- | --- |
| onboarding |  |  | low/medium/high | docs/fix/eval/risk/post-v9 |
| terminal |  |  | low/medium/high | docs/fix/eval/risk/post-v9 |
| dashboard |  |  | low/medium/high | docs/fix/eval/risk/post-v9 |
| provider |  |  | low/medium/high | docs/fix/eval/risk/post-v9 |
| verification |  |  | low/medium/high | docs/fix/eval/risk/post-v9 |
| memory/index |  |  | low/medium/high | docs/fix/eval/risk/post-v9 |
| recovery |  |  | low/medium/high | docs/fix/eval/risk/post-v9 |

## Outcome

- Completed:
- Verification result:
- Residual risk:
- Follow-up tasks:
```

## Redaction Rules

Before committing any dogfooding summary, remove or replace:

- private repository names, organization names, ticket IDs, branch names, and
  customer names
- absolute local paths, home directories, usernames, hostnames, and machine IDs
- source snippets, proprietary file contents, private diffs, and private
  dependency URLs
- API keys, tokens, cookies, environment values, credentials, and credential
  presence details beyond `present`, `absent`, `expired`, or `skipped`
- raw provider prompts, responses, tool-call arguments, stack traces containing
  private paths, and model output that quotes private code
- large artifacts, screenshots, logs, exported sessions, replay bundles, and
  provider canary outputs unless reviewed and sanitized

Use neutral aliases such as:

- `repo-alpha`
- `workspace-root`
- `provider-present-redacted`
- `provider-skipped-no-credentials`
- `task-1`

Allowed committed material:

- workflow category and command family
- Glassbox version, commit, or candidate label
- high-level repository type such as `Python CLI`, `frontend app`, or
  `monorepo`
- redacted provider posture and explicit skip reasons
- friction summaries that do not disclose private implementation details
- verification command names when they do not expose private paths or services
- disposition decisions and follow-up task IDs

## Finding Disposition

Every finding must become one of these outcomes before v9 release signoff:

| Disposition | Use When | Required Record |
| --- | --- | --- |
| Fix | The issue is high-signal, low-risk, and bounded enough for v9. | changed files, focused tests, validation command |
| Docs | The workflow is correct but hard to discover or understand. | updated doc path and reviewed command/API claim |
| Eval or test | The same behavior could regress deterministically. | eval case, test path, or explicit recommendation |
| Accepted residual risk | The issue remains in v9 but is understood and mitigated. | risk, impact, mitigation, owner, release decision |
| Post-v9 task | The fix requires a larger subsystem or product decision. | task note with scope and reason it is deferred |

Do not leave a finding as an anecdote. If the evidence is too private to share,
commit only the sanitized disposition summary and retain the raw local evidence
path.

## Summary Shape

Sanitized pass summaries should use this shape when a structured artifact helps:

```json
{
  "pass_id": "20260429-0930-repository-inspection",
  "workflow": "repository-inspection",
  "repository_alias": "repo-alpha",
  "provider_posture": "provider-skipped-no-credentials",
  "autonomy_mode": "deterministic",
  "dashboard_used": true,
  "verification": {
    "commands": ["uv run glassbox readiness check --cwd ."],
    "result": "passed"
  },
  "findings": [
    {
      "area": "onboarding",
      "severity": "medium",
      "summary": "Readiness next action was clear, but dashboard handoff was hard to find.",
      "disposition": "docs"
    }
  ],
  "outcome": "completed-with-doc-follow-up"
}
```

## Release Use

For GBX-981, retain at least three local `evidence.md` files or sanitized
summaries that cover the required pass mix.

For GBX-982, create a visible improvement trail by listing each finding,
disposition, changed doc/test/eval path, and accepted residual risk or post-v9
task.

For the v9 release candidate, summarize dogfooding outcomes in the release
guide without requiring reviewers to inspect private raw artifacts.
