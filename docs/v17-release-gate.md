# V17 Release Gate

`scripts/validate_v17_release_gate.py` is the automated v17 local handoff
release gate. It inherits deterministic v16 coverage, then adds v17 blocking
checks for local handoff evals, handoff package inspection, redaction preview,
import triage, custody decisions, CLI/API coverage, frontend handoff smoke,
package contents, docs, and eval coverage audit.

Run a planning pass first:

```bash
uv run python scripts/validate_v17_release_gate.py --dry-run
```

Run the full deterministic gate before v17 release signoff:

```bash
uv run python scripts/validate_v17_release_gate.py
```

The gate writes retained evidence under `.glassbox/releases/` by default. Use
`--evidence-dir PATH` to put the summary somewhere explicit for release review.

Stage construction is grouped in `scripts/v17_release_gate_stage_groups.py` by
evidence family: inherited v16 stages, handoff eval stages, focused handoff
smokes, CLI/API coverage, frontend smoke, package validation, release docs and
eval audit, and the installed-wheel smoke label recorded by the shared runner.

Provider canaries, dashboard/browser notes, accessibility notes, dogfooding,
and manual review remain advisory evidence. They are reported separately from
blocking deterministic stages and do not become release authority unless a
future fixture-backed task promotes a narrow contract.
