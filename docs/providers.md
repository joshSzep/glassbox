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

- Symptom: `Session failed: missing OpenAI API key for configured provider runtime`
- Cause: a provider-specific override is present, but the matching API key is missing
- Fix: set the required `*_API_KEY` variable or remove the partial provider override

Unsupported provider prefix:

- Symptom: `Session failed: unsupported model provider configured for session: other`
- Cause: the `--model-name` provider prefix is not currently supported for real-provider execution
- Fix: use an `openai:` or `anthropic:` model name

Invalid base URL:

- Symptom: `Session failed: invalid OpenAI base URL runtime config`
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
uv run glassbox provider canary run --cwd . --output-dir .glassbox/releases/provider-canary
```

Run one scenario:

```bash
uv run glassbox provider canary run --cwd . --scenario streaming-text --json
```

Keep canary artifacts redacted. Store only the provider family, scenario status,
high-level state transitions, and any release-relevant failure summary. Do not
store raw prompts, responses, API keys, or provider request metadata unless they
have been reviewed and redacted.

See [provider-canary-policy-v6.md](./provider-canary-policy-v6.md) and
[manual-qa-evidence-v6.md](./manual-qa-evidence-v6.md) for release evidence
retention.
