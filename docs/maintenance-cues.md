# Maintenance Cues

Maintenance cues are typed advisory records for local upkeep and recovery.
They sit beside active work in observability, readiness, the operator queue, and
dashboard/TUI surfaces without making ordinary chat or review work block by
default.

## Cue Families

`MaintenanceCue.kind` uses one shared vocabulary:

- `projection_drift`: session projections are stale, unavailable, or degraded.
- `stale_daemon_owner`: runtime owner metadata points at a dead daemon process.
- `failed_background_jobs`: daemon background jobs failed, are stale, retryable,
  or abandoned.
- `artifact_pressure`: retained artifacts have storage pressure, prune
  candidates, or missing references.
- `backup_posture`: no recent local backup archive is visible under
  `.glassbox/backups`.
- `stale_repository_intelligence`: repository index, topology, command recipes,
  eval metadata, release surfaces, or memory conflict posture is missing,
  stale, degraded, or conflicting.
- `provider_config_issues`: provider diagnostics or retained canary evidence is
  missing, stale, incompatible, warning, or failed.
- `package_asset_staleness`: packaged dashboard assets or install/package
  posture needs attention.
- `eval_baseline_drift`: retained eval summaries are missing or the latest
  suite failed.

## Severity And Urgency

Each cue has `priority` and `severity`, reusing `NextActionPriority` and
`NextActionSeverity` so maintenance items sort consistently with queue and
next-action records.

Use `action-needed` only when recovery is likely to affect current confidence,
such as failed background jobs, failed eval baselines, or stale daemon owner
state. Use `degraded` when derived evidence is stale enough to lower confidence,
such as projection drift, stale repository intelligence, or artifact pressure
over a configured threshold. Use `recommended` or `maintenance-only` for
advisory upkeep such as backups, optional provider posture, missing eval
baseline evidence, or dry-run cleanup.

Advisory maintenance cues do not change first-run readiness status. A workspace
can be `ready` while still showing a `backup_posture` cue because the cue is
useful before maintenance but not proof that ordinary work must stop.

## Evidence And Commands

Each cue carries bounded `supporting_evidence`, `missing_evidence`, and
`stale_evidence` references. Evidence points to local observability sections,
readiness checks, retained eval summaries, provider canary summaries,
repository intelligence, artifact posture, background jobs, or backup archive
paths.

`safe_next_actions` use typed next-action records with command recipes. They are
inspection-first by default, for example:

- `glassbox observability status --cwd .`
- `glassbox projection check --all --cwd .`
- `glassbox job list --cwd .`
- `glassbox artifacts inspect --cwd .`
- `glassbox artifacts prune --dry-run --cwd .`
- `glassbox backup create --cwd .`
- `glassbox provider diagnostics --cwd .`
- `glassbox provider canary evidence --cwd .`
- `glassbox repo index build --cwd .`
- `glassbox eval run --cwd .`

Destructive cleanup stays behind explicit operator commands. Artifact pruning
surfaces a dry-run command as a safe next action and records that non-dry-run
cleanup is intentionally outside automatic cue handling.

## Surface Contract

Observability status emits `maintenance_cues` in JSON and prints a compact text
section. Readiness reports expose `maintenance_cues` while keeping readiness
status derived only from readiness checks. Later queue/dashboard integration can
project the same cue records into `maintenance` or `advisory` lanes without
reinterpreting severity, evidence, or command safety.
