# Provider Setup

For the docs hub and workflow guides, start at [README.md](./README.md). For local installation and validation, use [getting-started.md](./getting-started.md).

Glassbox can execute turns against real OpenAI and Anthropic providers when
provider credentials are available at runtime.

Optional live-provider release confidence follows
[provider-canary-policy-v6.md](./provider-canary-policy-v6.md). Canary evidence
is advisory and does not replace deterministic replay/eval gates.

## Supported Providers

The current real-provider scope is:

- `openai:...`
- `anthropic:...`

Examples:

```bash
uv run glassbox session run "Inspect the repository" --cwd . --model-name openai:gpt-5.4
uv run glassbox session run "Inspect the repository" --cwd . --model-name anthropic:claude-sonnet-4
```

If provider config is absent, Glassbox preserves the deterministic local
executor path for offline development and tests.

Model selection defaults can live in `glassbox.profile.json`; provider
credentials still come from runtime-only environment configuration described
below.

## First-Run Diagnostics

Start with diagnostics before running a real provider session:

```bash
uv run glassbox provider diagnostics --cwd . --model-name openai:gpt-5.4
```

The human-readable output includes a first-run checklist for provider
diagnostics, model selection, `glassbox.profile.json`, the paired dashboard URL,
and a small validation command. The JSON output includes the same redacted
`onboarding_steps` field for package smoke and scripted setup checks.

Common first-run outcomes:

- `ready`: credentials and selected provider family are configured.
- `local_fallback`: no provider credentials are configured, so use an unprefixed
  local model or set the provider API key before expecting a remote call.
- `missing_credentials`: a partial provider override, such as a base URL without
  an API key, must be completed or removed.
- `unsupported_model`: choose `openai:MODEL`, `anthropic:MODEL`, or an
  unprefixed local model.

## Environment Variables

OpenAI:

- Required: `OPENAI_API_KEY`
- Optional: `OPENAI_BASE_URL`

Anthropic:

- Required: `ANTHROPIC_API_KEY`
- Optional: `ANTHROPIC_BASE_URL`

Set them in your shell:

```bash
export OPENAI_API_KEY="..."
export OPENAI_BASE_URL="https://api.openai.com/v1"
uv run glassbox session run "Inspect the repository" --cwd . --model-name openai:gpt-5.4
```

Or with Anthropic:

```bash
export ANTHROPIC_API_KEY="..."
uv run glassbox session run "Inspect the repository" --cwd . --model-name anthropic:claude-sonnet-4
```

## `.env` Support

Glassbox reads an optional `.env` file from the selected runtime workspace root.
That means the `.env` file is resolved relative to `--cwd`.

Example:

```dotenv
OPENAI_API_KEY=...
OPENAI_BASE_URL=https://api.openai.com/v1
ANTHROPIC_API_KEY=...
```

Precedence is explicit:

- process environment overrides `.env`
- `.env` overrides absence of provider config
- `glassbox.profile.json` is separate and does not override provider secrets or
  base URLs

Partial provider configuration is treated as an error. For example, setting
`OPENAI_BASE_URL` without `OPENAI_API_KEY` fails before any remote request is
attempted.

## Secret Handling

Provider credentials remain runtime-only.

Glassbox does not persist provider secrets into:

- `SessionConfig`
- `SessionRecord`
- event payloads
- projection tables
- the SQLite database

Provider setup failures are surfaced with non-secret messages. Raw API keys are
not echoed into CLI output, dashboard session failure state, logs, or persisted
events.

## Troubleshooting

Missing API key:

- Symptom: `Session failed: missing OpenAI API key for configured provider runtime; set OPENAI_API_KEY in the process environment or .env at --cwd, or remove partial provider overrides`
- Cause: a provider-specific override is present, but the matching API key is missing
- Fix: set the required `*_API_KEY` variable in the process environment or `.env`, then rerun `glassbox provider diagnostics --cwd .`; otherwise remove the partial provider override

Unsupported provider prefix:

- Symptom: `Session failed: unsupported model provider configured for session: other; use openai:MODEL, anthropic:MODEL, or an unprefixed local model, then rerun provider diagnostics before retrying`
- Cause: the `--model-name` provider prefix is not currently supported for real-provider execution
- Fix: use an `openai:` or `anthropic:` model name, or an unprefixed local model for deterministic fallback; rerun diagnostics before starting a session

Invalid base URL:

- Symptom: `Session failed: invalid OpenAI base URL runtime config; use an http(s) URL or remove OPENAI_BASE_URL`
- Cause: the provider base URL is not a valid `http` or `https` URL
- Fix: correct the base URL or remove the override

Unexpected local fallback:

- Symptom: Glassbox appears to run without contacting a real provider
- Cause: no provider runtime config was present, so Glassbox used the deterministic local executor
- Fix: set the provider API key in the process environment or `.env` for the selected `--cwd`

Preflight diagnostics:

```bash
uv run glassbox provider diagnostics --cwd . --model-name openai:gpt-5.4
uv run glassbox provider diagnostics --cwd . --json
```

The diagnostics command reports the selected model source, provider family,
runtime mode, whether provider keys or base URLs are present, and which source
provided each value. It never prints API key values.

Diagnostics are offline. They do not contact a remote provider; they also report
the configured model, credential source, base URL posture, streaming assumption,
tool-call assumption, known unsupported scenarios, and the expected per-scenario
canary preflight state.

OpenAI with credentials configured reports `runtime_mode=openai`, a configured
credential source such as `process-env` or `dotenv`, `base_url_posture=default`
unless `OPENAI_BASE_URL` is set, and `streaming-text` as ready. Anthropic reports
the same shape with `provider_family=anthropic` and `ANTHROPIC_*` sources.

Missing credentials keep diagnostics redacted and mark canary scenarios as
`skip`. Unsupported local model modes mark live-provider canary scenarios as
`unsupported` because the deterministic local runtime does not exercise a remote
provider.

## Advisory Provider Canaries

Provider canaries are optional release confidence checks. They are useful when
credentials are available, but they are not part of the deterministic release
gate and should not replace replay/eval signoff.

Canary evidence is retained as a provider capability matrix. Each matrix row is
advisory and records the provider, model, scenario, credential state, streaming
support, tool-call support, approval behavior, ask-user behavior, cancellation
behavior, dashboard compatibility, daemon attach compatibility, result, skipped
reason, and redaction status. The matrix must not contain API keys, raw prompts,
raw model responses, or provider request metadata.

Interpretation is intentionally conservative:

- `passed` means the advisory canary observed the expected redacted event shape.
- `warning` means the canary ran but did not observe the complete expected shape.
- `failed` means the canary command hit an execution error.
- `skipped` means credentials, scenario support, or provider support were missing
  and the reason should be reviewed rather than treated as a silent pass.

Deterministic replay/eval reports remain the blocking release authority. Provider
matrix rows help reviewers understand provider-specific behavior and decide what
manual or advisory follow-up is needed.

Run all default advisory scenarios:

```bash
uv run glassbox provider canary run --cwd .
```

By default, summaries are written to
`.glassbox/provider-canary/provider-canary-summary.json`. Use `--output-dir` to
place a run under release evidence, for example
`.glassbox/releases/provider-canary`.

The default scenario set is:

- `streaming-text`
- `tool-call`
- `approval`
- `ask-user`
- `cancellation`
- `dashboard`
- `daemon-attach`
- `malformed-tool-call`
- `long-context-continuity`
- `retry-behavior`
- `rate-limit-handling`
- `tool-call-streaming`
- `cancellation-during-retry`
- `multi-step-plan-following`
- `verification-loop-interaction`

`streaming-text` runs a short live provider turn when diagnostics are ready. The
remaining scenarios are retained as preflight-only rows until their
workflow-specific live automation is available, so skipped rows should be read as
explicit capability limits rather than silent success.

Provider capability matrix rows include scenario confidence, observed limits,
retry posture, and tool-call reliability. These fields help operators compare
provider fit for agentic workflows such as bounded plan following and
verify-repair loops, but they remain advisory and do not silently change the
model selected for a session.

Run one scenario:

```bash
uv run glassbox provider canary run --cwd . --scenario streaming-text --json
```

Inspect the latest retained advisory evidence:

```bash
uv run glassbox provider canary evidence --cwd .
uv run glassbox provider canary evidence --cwd . --json
```

`glassbox observability status` also reports a provider-canary cue with the
latest retained status. `missing` means no retained advisory evidence was found.
`stale`, `skipped`, `warning`, and `failed` states should prompt operator review,
but they are still advisory and must not be confused with deterministic release
signoff.

Keep canary artifacts redacted. Store only the provider family, scenario status,
high-level state transitions, and any release-relevant failure summary. Do not
store raw prompts, responses, API keys, or provider request metadata unless they
have been reviewed and redacted.

## Provider Evidence Freshness

Provider evidence has two operator-visible states:

- `latest_status` describes the retained canary outcome: `missing`, `passed`,
  `skipped`, `warning`, or `failed`.
- `freshness_status` describes whether the retained evidence should guide an
  operator right now: `fresh`, `stale`, `incompatible`, `missing`,
  `credentialless`, `warning`, or `failed`.

Fresh evidence is retained evidence that matches the current provider/model
identity when that identity is known, validates against the supported canary
summary schema, is younger than seven days, keeps every capability row redacted,
and covers the default scenario set or lists the scenarios that are missing.
Glassbox reports the freshness policy as `provider-evidence-freshness.v1` in
JSON output so dashboard and release tooling can tell which interpretation was
used.

Use the freshness states this way:

- `fresh`: the retained advisory evidence is recent and schema-compatible.
- `stale`: the latest summary is older than the freshness window; rerun
  `glassbox provider canary run --cwd .` before relying on it.
- `incompatible`: the summary cannot be parsed as supported retained evidence;
  inspect the file, keep it as historical evidence if useful, and rerun the
  canary to produce current schema output.
- `missing`: no retained canary summary exists.
- `credentialless`: the run was skipped because Glassbox had no usable live
  provider credentials or was using the local deterministic runtime.
- `warning`: the evidence is current but incomplete, skipped for a
  non-credential reason, or otherwise needs review.
- `failed`: the retained run has a provider canary failure.

Freshness is advisory. It can raise or lower confidence in provider-backed
autonomy, but deterministic replay/eval reports remain the blocking release
authority. Missing, stale, credentialless, warning, failed, or incompatible
provider evidence should produce clear next actions; none of those states should
silently block a deterministic release gate or silently switch the model used by
a session.

## Provider Recommendations

Use provider recommendations when choosing a model/provider for an autonomy mode
or workflow kind:

```bash
uv run glassbox provider recommend --cwd . --task-kind coding --autonomy-mode test-driven
uv run glassbox provider recommend --cwd . --task-kind verification --autonomy-mode release-candidate --json
```

Recommendations consider local diagnostics, the selected model, autonomy mode,
workflow needs, and retained advisory canary evidence. They report posture
(`recommended`, `usable`, `risky`, or `local_fallback`), confidence, required
capabilities, reasons, warnings, relevant scenarios, and next actions.

Recommendations are advisory. Glassbox does not silently switch the model or
provider for a session based on recommendation output. Missing credentials,
missing canary evidence, skipped scenarios, and stale evidence lower confidence
instead of pretending the provider is ready for autonomous local work.

See [provider-canary-policy-v6.md](./provider-canary-policy-v6.md) and
[manual-qa-evidence-v7.md](./manual-qa-evidence-v7.md) for release evidence
retention.
