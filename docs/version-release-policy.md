# Version And Release Naming Policy

This policy keeps package metadata, public docs, installed smoke, and release
evidence aligned for the v9 baseline.

## Current Decision

Glassbox v9 uses package version `0.9.0`.

The version remains pre-1.0 because Glassbox is still a local-first operator
tool with conservative support boundaries: no hosted control plane, no cloud
workspace authority, no remote worker fleet, no simultaneous multi-writer
mutation owner, and no replacement of deterministic replay/eval release
authority with live-provider canaries.

The `0.9.0` identifier means:

- `0`: pre-1.0 API and workflow compatibility remains conservative rather than
  permanent
- `9`: the package corresponds to the v9 public-baseline track
- `0`: first package version for the v9 baseline policy

## Metadata Alignment

`pyproject.toml` is the packaging source for build metadata. The package module
also exposes `glassbox.__version__`, and both values must match.

The root README, [v9-public-baseline.md](./v9-public-baseline.md), and this
policy must agree on the current public baseline. Operator docs should refer to
the v9 baseline by product contract first and package version second.

The CLI prints the installed package version with:

```bash
glassbox --version
```

Installed-wheel smoke includes that command so release evidence can show the
version operators receive from a built artifact.

## Release-Candidate Naming

Use this naming pattern for future v9 candidate evidence:

```text
v9.0.0-rc.N
```

Use package version `0.9.0` for the public-baseline package metadata until a
task explicitly changes the package version. Candidate labels such as
`v9.0.0-rc.1` describe retained evidence and release decision state, not hosted
service availability.

Evidence directories should include the baseline and candidate label when
available:

```text
.glassbox/releases/v9.0.0-rc.1/
.glassbox/evals/v9.0.0-rc.1/
```

When no candidate label exists yet, task-specific evidence may use a stable
task or gate name:

```text
.glassbox/releases/gbx-912-version-policy/
```

## Version Change Rules

- Patch versions, such as `0.9.1`, are for compatible fixes to the v9 baseline.
- Minor versions before 1.0, such as `0.10.0`, require an explicit baseline or
  release-policy task because pre-1.0 minor bumps may change workflow contracts.
- A future `1.0.0` requires a separate contract that names durable compatibility
  expectations, migration posture, and release authority.
- Historical release-candidate docs may keep the version strings that were true
  for their evidence. Do not rewrite retained evidence paths only to match the
  current package version.

## Release Note Template

Use this template for future v9 candidate evidence:

```markdown
# Glassbox v9.0.0-rc.N Release Notes

Date: YYYY-MM-DD
Package version: 0.9.0
Commit: <git-sha>
Evidence directory: .glassbox/releases/v9.0.0-rc.N/

## Decision

- Status: GO | HOLD
- Summary:

## Supported Baseline

- Public baseline:
- Daily workflow docs:
- Package artifacts:

## Validation

- v9 release gate:
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
