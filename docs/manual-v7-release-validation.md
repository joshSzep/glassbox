# v7 Manual Release Validation

This document records the `GBX-784` manual validation pass for the v7 release-candidate track. The retained local evidence directory for this pass is:

```text
.glassbox/releases/20260428T181210Z-v7-gate/
```

The directory is local workspace state and is intentionally not committed. It contains `summary.json`, `manual-validation.md`, provider-canary evidence, observability status, and projection-check output.

## Commands Run

Automated gate dry run:

```bash
uv run python scripts/validate_v7_release_gate.py \
  --dry-run \
  --evidence-dir .glassbox/releases/20260428T181210Z-v7-gate
```

Focused terminal evidence:

```bash
uv run pytest \
  tests/unit/test_cli_tui_app.py \
  tests/unit/test_cli_tui_workflows.py \
  tests/integration/test_cli_tui_launch_smoke.py
```

Result: `52 passed`.

Focused dashboard evidence:

```bash
pnpm --dir frontend exec vitest run \
  tests/verification-cues.test.ts \
  tests/session-inspector.test.ts

pnpm --dir frontend exec playwright test \
  e2e/operator-workflows.spec.ts \
  -g "operator can inspect artifact-backed verification cues"
```

Result: `14` Vitest tests passed and `1` Playwright workflow passed.

Provider-canary evidence:

```bash
uv run glassbox provider canary run \
  --cwd . \
  --output-dir .glassbox/releases/20260428T181210Z-v7-gate/provider-canary \
  --json
```

Result: `streaming-text` passed for `openai:gpt-5.4`; `tool-call`, `approval`, `ask-user`, `cancellation`, `dashboard`, and `daemon-attach` were retained as preflight-only skipped advisory rows. Provider canary evidence remains advisory and separate from deterministic release signoff.

Recovery and maintenance evidence:

```bash
uv run glassbox observability status --cwd . --json
uv run glassbox projection check --all --cwd .
```

Outputs were retained under the local v7 evidence directory.

Packaging and onboarding evidence:

```bash
uv build --wheel --sdist
uv run python scripts/validate_package_contents.py
```

Result: built wheel and sdist validated. A compact installed-wheel smoke also passed for profile-backed provider diagnostics and eval profile listing using `uv run --no-project --refresh --isolated --with dist/glassbox-0.1.0-py3-none-any.whl`.

## Findings

No blocking issue was found in the focused `GBX-784` pass.

Accepted residual risks for the v7 release decision:

- The full v7 gate was dry-run only in this task; the release decision should state whether the full gate was run before publishing.
- Screen-reader pairings remain explicit non-claims until a human reviewer runs and retains named assistive-technology evidence.
- Provider canary workflow scenarios beyond `streaming-text` remain preflight-only advisory rows.

Use [manual-qa-evidence-v7.md](./manual-qa-evidence-v7.md) for future v7 manual validation manifests and redaction rules.
