# Provider Setup

Glassbox can execute turns against real OpenAI and Anthropic providers when
provider credentials are available at runtime.

## Supported Providers

The current real-provider scope is:

- `openai:...`
- `anthropic:...`

Examples:

```bash
uv run glassbox run "Inspect the repository" --cwd . --model-name openai:gpt-5.4
uv run glassbox run "Inspect the repository" --cwd . --model-name anthropic:claude-sonnet-4
```

If provider config is absent, Glassbox preserves the deterministic local
executor path for offline development and tests.

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
uv run glassbox run "Inspect the repository" --cwd . --model-name openai:gpt-5.4
```

Or with Anthropic:

```bash
export ANTHROPIC_API_KEY="..."
uv run glassbox run "Inspect the repository" --cwd . --model-name anthropic:claude-sonnet-4
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
