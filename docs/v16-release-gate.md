# V16 Release Gate

`scripts/validate_v16_release_gate.py` is the automated v16 operator-flow
release gate. It inherits deterministic v15 coverage, then adds v16 blocking
checks for operator queue ranking, evidence graph support, verification plan
lifecycle, skipped-check posture, changeset workup previews, maintenance cues,
reviewer-safe bundles, package contents, installed smoke, and eval coverage.

Plan the gate without running commands:

```bash
uv run python scripts/validate_v16_release_gate.py --dry-run
```

Run the deterministic gate:

```bash
uv run python scripts/validate_v16_release_gate.py
```

Provider canaries, browser walkthroughs, accessibility notes, dogfooding, and
manual release notes remain advisory. The retained `summary.json` records those
entries separately from blocking deterministic stages so release reviewers can
see confidence sources without conflating them with release authority.
The advisory row labels, dry-run wording, skipped provider-canary copy, and
non-blocking `required_for_release: false` shape are owned by
`scripts/v16_release_gate_advisory.py`.
