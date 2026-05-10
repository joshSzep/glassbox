# V15 Release Gate

`scripts/validate_v15_release_gate.py` is the automated v15 repository
intelligence release-readiness command.

Run a dry-run plan first:

```bash
uv run python scripts/validate_v15_release_gate.py --dry-run
```

Run the gate after rebuilding the package distributions:

```bash
uv build --wheel --sdist
uv run python scripts/validate_v15_release_gate.py
```

## Blocking Evidence

The v15 gate inherits the v14 deterministic release stack, then adds blocking
repository-intelligence stages for:

- deterministic eval report output for `commit-smoke`, `push-confirmation`,
  and `release-candidate`
- the full `release-candidate` eval profile
- the five v15 repository-intelligence eval cases:
  `repository-intelligence.snapshot-rich`,
  `repository-intelligence.path-verification`,
  `repository-intelligence.stale-degradation`,
  `repository-intelligence.memory-command`, and
  `repository-intelligence.context-drift`
- repository index, topology, workspace-memory, eval recommendation, and eval
  coverage unit tests
- repository CLI and API integration tests
- repository-intelligence dashboard component tests, generated API freshness,
  frontend lint, typecheck, and build
- package contents validation and installed-wheel smoke
- release documentation guardrails and release-candidate eval coverage audit

## Advisory Evidence

The summary JSON keeps advisory evidence separate from blocking stages:

- provider canary posture is opt-in with `--include-provider-canaries`
- dashboard browser evidence and accessibility-adjacent evidence are retained
  from [v15-repository-intelligence-evidence.md](./v15-repository-intelligence-evidence.md)
- dogfooding evidence is recorded by `GBX-1582` in
  `docs/v15-dogfooding-summary.md`

Advisory evidence does not make live providers, browser walkthroughs,
accessibility notes, owner hints, command recipes, or dogfooding observations
release authority.

## Summary Artifact

Each run writes `summary.json` under the selected evidence directory. The
summary has `blocking` and `advisory` sections, release-authority labels,
artifact references, and next actions. Raw `.glassbox` state remains local; use
reviewer-safe docs and retained summaries for handoff.
