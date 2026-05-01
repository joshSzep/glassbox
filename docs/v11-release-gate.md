# V11 Release Gate

For the docs hub and operator guides, start at [README.md](./README.md).

The v11 gate scaffold is:

```bash
uv run python scripts/validate_v11_release_gate.py --dry-run
```

`GBX-1142` adds the optional provider-evidence path early so provider
confidence can be retained consistently before the full `GBX-1191` v11 release
gate expansion. The scaffold inherits the deterministic v10 blocking stages for
now. Provider evidence remains advisory and opt-in.

To plan provider evidence without contacting a provider:

```bash
uv run python scripts/validate_v11_release_gate.py \
  --dry-run \
  --include-provider-canaries \
  --evidence-dir .glassbox/releases/v11-gate-dry-run
```

The retained `summary.json` records provider evidence under `advisory` with:

- `blocking=false`
- `latest_status`
- `freshness_status`
- `missing_scenarios`
- `evidence_dir`
- `summary_path` when planned or run
- provider/model/scenario counts when collected

When `--include-provider-canaries` is omitted, the summary records an explicit
structured skip. When it is present, `glassbox provider canary run` writes
redacted provider-canary evidence under `provider-canary/`, and the gate records
freshness and missing-scenario posture using the same evidence interpretation as
`glassbox provider recommend`.

Provider canary failures, missing credentials, stale evidence, and skipped
scenarios do not block deterministic release authority. They are retained for
reviewer confidence and operator follow-up beside replay/eval, package, and
installed-smoke evidence.
