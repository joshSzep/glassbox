# Live-Provider Canary Policy

Live-provider canaries are optional advisory checks for validating that Glassbox
still works against real provider APIs. They must never replace deterministic
replay/eval as the default blocking release gate.

## Blocking Rule

- Deterministic replay/eval remains the default blocking validation path for all
  contributors and release candidates.
- Live-provider canaries belong to the `live-provider-canary` eval track and are
  advisory, non-blocking, and opt-in.
- Missing provider credentials should skip a canary with a structured reason,
  not fail a normal local validation run.
- `glassbox eval report` remains deterministic-only; provider canaries may be
  referenced in release notes as retained advisory evidence.

## When To Run Canaries

Run live-provider canaries only when a maintainer intentionally wants external
integration confidence, such as before a tagged release, after provider adapter
changes, after streaming/tool-call runtime changes, or when investigating a
provider-specific regression.

Do not run canaries automatically in pre-commit hooks, default local tests, or
ordinary deterministic release sign-off.

Run the advisory command with:

```bash
uv run glassbox provider canary run --cwd . --model-name openai:gpt-5.4
uv run glassbox provider canary run --cwd . --model-name anthropic:claude-sonnet-4 --json
```

The command writes `provider-canary-summary.json` under
`.glassbox/evals/provider-canary/` by default. If credentials are unavailable, it
writes a skipped advisory summary instead of failing normal local validation.

## Required Configuration

OpenAI canaries require `OPENAI_API_KEY`. Anthropic canaries require
`ANTHROPIC_API_KEY`. Optional base URL overrides follow the provider setup
rules in [providers.md](./providers.md).

Canary diagnostics and artifacts must record provider family and model name, but
must not record API keys, secret-like environment values, bearer tokens, or raw
credential sources.

## Scenario Matrix

| Scenario | Evidence To Check | Practical Scope |
| --- | --- | --- |
| Streaming text turn | `ModelCallStarted`, streamed assistant deltas, completed turn | One short prompt per selected provider |
| Tool call | requested tool, tool output artifact, completed tool event family | Deterministic low-risk local tool only |
| Approval | approval requested, approved path resumes, denied path blocks cleanly | One approve and one deny branch where supported |
| `ask_user` | pending question, answer submission, resumed assistant response | Short question/answer loop |
| Cancellation | cancellation requested and acknowledged without corrupting final state | Best-effort, timing-tolerant evidence only |
| Dashboard convergence | snapshot, stream cursor, and terminal state agree after completion | Local dashboard/API inspection, no screenshot requirement by default |
| Daemon attach | daemon-owned attach can read and mutate the same live session | One live attach smoke when daemon support is enabled |

Scenario assertions should use event families, state transitions, persisted
snapshots, and operator-visible status. Do not assert exact provider text unless
the test is explicitly provider-stubbed.

## Failure Interpretation

- `skipped`: credentials, model access, or provider environment is unavailable.
- `passed`: scenario produced the required event families and terminal state.
- `warning`: provider returned usable output but advisory evidence is incomplete,
  slow, or partially degraded.
- `failed`: Glassbox produced an unsafe state transition, corrupted persisted
  evidence, leaked secret material, or could not recover from provider/runtime
  errors that should be handled.

Provider outage, rate limiting, or model access failure should be recorded as
environment evidence unless the adapter mishandles it.

## Artifact Retention

Canary output should live under `.glassbox/evals/` or another retained advisory
evidence directory. A retained summary should include:

- timestamp, provider family, model name, and selected scenarios
- outcome per scenario and skipped reasons
- redacted operator logs and next actions
- event-family counts and final session status
- dashboard URL or daemon URL only when it contains no credentials

## Redaction Policy

Canary artifacts must redact:

- `*_API_KEY`, bearer tokens, and environment variable values that look secret
- raw request headers and authorization metadata
- provider response metadata that includes account, organization, or billing data
- local paths only when they reveal sensitive user information beyond the chosen
  workspace root

Prompts and provider responses may be retained only when the scenario is
purpose-built, low sensitivity, and reviewed as release evidence. Otherwise use
summaries, event families, and final state instead of raw transcript text.
