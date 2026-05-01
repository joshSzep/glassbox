# Version And Release Naming Policy

This policy keeps package metadata, public docs, installed smoke, and release
evidence aligned for the `0.10.0` package line and the active v11 confidence
and adoption milestone.

## Current Decision

Glassbox v11 uses package version `0.10.0`.

The `0.10.0` package line publishes the v10 long-running-task operating model
after the v11 confidence-and-adoption work starts closing the accepted v10
residual risks. In other words, v10 names the supported product capability
line, while v11 names the confidence, adoption, and release-evidence milestone
that prepares that line for operators.

The version remains pre-1.0 because Glassbox is still a local-first operator
tool with conservative support boundaries: no hosted control plane, no cloud
workspace authority, no remote worker fleet, no simultaneous multi-writer
mutation owner, and no replacement of deterministic replay/eval release
authority with live-provider canaries.

The `0.10.0` identifier means:

- `0`: pre-1.0 API and workflow compatibility remains conservative rather than
  permanent
- `10`: the package corresponds to the v10 long-running-task product line
- `0`: first package version for the v11 confidence-and-adoption milestone

## Metadata Alignment

`pyproject.toml` is the packaging source for build metadata. The package module
also exposes `glassbox.__version__`, and both values must match.

The root README, [v10-long-running-task-contract.md](./v10-long-running-task-contract.md),
[v11-confidence-adoption-contract.md](./v11-confidence-adoption-contract.md),
and this policy must agree on the current package line and active milestone.
Historical docs such as [v9-public-baseline.md](./v9-public-baseline.md) keep
their retained version claims when those claims were true for that evidence.

The CLI prints the installed package version with:

```bash
glassbox --version
```

Installed-wheel smoke includes that command so release evidence can show the
version operators receive from a built artifact.

## Release-Candidate Naming

Use this naming pattern for future v11 candidate evidence:

```text
v11-0.10.0-rc.N
```

Use package version `0.10.0` for package metadata during the v11 milestone.
Candidate labels such as `v11-0.10.0-rc.1` describe retained evidence and
release decision state, not hosted service availability.

Evidence directories should include the baseline and candidate label when
available:

```text
.glassbox/releases/v11-0.10.0-rc.1/
.glassbox/evals/v11-0.10.0-rc.1/
```

When no candidate label exists yet, task-specific evidence may use a stable
task or gate name:

```text
.glassbox/releases/gbx-1102-version-policy/
```

## Version Change Rules

- Patch versions, such as `0.10.1`, are for compatible fixes to the `0.10.0`
  package line.
- Minor versions before 1.0, such as a future `0.11.0`, require an explicit
  baseline or release-policy task because pre-1.0 minor bumps may change
  workflow contracts.
- A future `1.0.0` requires a separate contract that names durable compatibility
  expectations, migration posture, and release authority.
- Historical release-candidate docs may keep the version strings that were true
  for their evidence. Do not rewrite retained evidence paths only to match the
  current package version.

## Release Note Template

Use this template for future v11 candidate evidence:

```markdown
# Glassbox v11-0.10.0-rc.N Release Notes

Date: YYYY-MM-DD
Package version: 0.10.0
Commit: <git-sha>
Evidence directory: .glassbox/releases/v11-0.10.0-rc.N/

## Decision

- Status: GO | HOLD
- Summary:

## Supported Baseline

- Public baseline:
- Daily workflow docs:
- Package artifacts:

## Validation

- v11 release gate:
- Deterministic eval report:
- Installed-wheel smoke:
- Provider evidence: advisory, fresh | stale | skipped
- Manual evidence:

## Changes Since Previous Candidate

-

## Residual Risks

-

## Non-Goals

-
```
