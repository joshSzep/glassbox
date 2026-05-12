"""Maintenance cue derivation from observability and readiness signals."""

import shlex
from collections.abc import Sequence
from pathlib import Path

from glassbox.core import MaintenanceCue
from glassbox.core import MaintenanceCueKind
from glassbox.core import NextAction
from glassbox.core import NextActionCommandRecipe
from glassbox.core import NextActionEvidenceKind
from glassbox.core import NextActionEvidenceRef
from glassbox.core import NextActionKind
from glassbox.core import NextActionPriority
from glassbox.core import NextActionSafetyClass
from glassbox.core import NextActionSeverity
from glassbox.core import NextActionSurface
from glassbox.core import NextActionTarget
from glassbox.core import NextActionTargetKind
from glassbox.runtime.observability_models import ArtifactObservability
from glassbox.runtime.observability_models import BackgroundJobObservability
from glassbox.runtime.observability_models import ProjectionObservability
from glassbox.runtime.observability_models import RepositoryIntelligenceObservability
from glassbox.runtime.observability_models import RuntimeObservability
from glassbox.runtime.observability_models import VerificationObservability
from glassbox.runtime.provider_canary import ProviderCanaryEvidenceSummary

READINESS_MAINTENANCE_CHECKS = {
    "provider-configuration": MaintenanceCueKind.PROVIDER_CONFIG_ISSUES,
    "dashboard-static-assets": MaintenanceCueKind.PACKAGE_ASSET_STALENESS,
    "package-build-posture": MaintenanceCueKind.PACKAGE_ASSET_STALENESS,
    "repository-index": MaintenanceCueKind.STALE_REPOSITORY_INTELLIGENCE,
    "eval-profile-availability": MaintenanceCueKind.EVAL_BASELINE_DRIFT,
}


def build_observability_maintenance_cues(
    *,
    workspace_root: Path,
    runtime: RuntimeObservability,
    projections: ProjectionObservability,
    background_jobs: BackgroundJobObservability,
    repository_intelligence: RepositoryIntelligenceObservability,
    artifacts: ArtifactObservability,
    verification: VerificationObservability,
    provider_canary: ProviderCanaryEvidenceSummary,
) -> list[MaintenanceCue]:
    """Build first-class maintenance cues from existing observability sections."""

    cues: list[MaintenanceCue] = []
    workspace_target = _target(workspace_root, NextActionTargetKind.WORKSPACE)
    workspace_ref = str(workspace_root)

    if (
        projections.degraded_count
        or projections.stale_count
        or projections.unavailable_count
    ):
        count = projections.degraded_count or projections.stale_count
        cues.append(
            _cue(
                workspace_root,
                MaintenanceCueKind.PROJECTION_DRIFT,
                target=workspace_target,
                title="Projection drift",
                summary=(
                    f"{count} session projection(s) are degraded; max lag "
                    f"{projections.max_lag} event(s)."
                ),
                priority=NextActionPriority.DEGRADED,
                severity=NextActionSeverity.MEDIUM,
                evidence=[
                    _evidence(
                        NextActionEvidenceKind.PROJECTION,
                        workspace_ref,
                        "Projection observability reports degraded session state.",
                    )
                ],
                actions=[
                    _action(
                        workspace_root,
                        "projection-drift:check",
                        "Inspect projection drift",
                        "Review all projection health before rebuilding.",
                        NextActionKind.INSPECT,
                        NextActionPriority.DEGRADED,
                        NextActionSeverity.MEDIUM,
                        workspace_target,
                        ["glassbox", "projection", "check", "--all", "--cwd", "."],
                    ),
                    _action(
                        workspace_root,
                        "projection-drift:rebuild",
                        "Rebuild degraded projections",
                        "Refresh derived projection state after inspection.",
                        NextActionKind.REFRESH,
                        NextActionPriority.MAINTENANCE_ONLY,
                        NextActionSeverity.LOW,
                        workspace_target,
                        ["glassbox", "projection", "rebuild", "--all", "--cwd", "."],
                    ),
                ],
            )
        )

    if runtime.state == "stale":
        cues.append(
            _cue(
                workspace_root,
                MaintenanceCueKind.STALE_DAEMON_OWNER,
                target=workspace_target,
                title="Stale daemon owner",
                summary="Runtime owner metadata points at a stale daemon process.",
                priority=NextActionPriority.ACTION_NEEDED,
                severity=NextActionSeverity.MEDIUM,
                evidence=[
                    _evidence(
                        NextActionEvidenceKind.CLI_OUTPUT,
                        workspace_ref,
                        "Runtime observability state is stale.",
                        freshness="stale",
                    )
                ],
                actions=[
                    _action(
                        workspace_root,
                        "stale-daemon:status",
                        "Inspect daemon status",
                        "Confirm the stale owner before restarting runtime services.",
                        NextActionKind.INSPECT,
                        NextActionPriority.ACTION_NEEDED,
                        NextActionSeverity.MEDIUM,
                        workspace_target,
                        ["glassbox", "daemon", "status", "--cwd", "."],
                    ),
                    _action(
                        workspace_root,
                        "stale-daemon:restart",
                        "Restart daemon after inspection",
                        "Clear the stale owner through the daemon command surface.",
                        NextActionKind.RECOVER,
                        NextActionPriority.MAINTENANCE_ONLY,
                        NextActionSeverity.LOW,
                        workspace_target,
                        ["glassbox", "daemon", "start", "--cwd", "."],
                    ),
                ],
            )
        )

    _add_background_job_cue(cues, workspace_root, background_jobs)
    _add_artifact_cue(cues, workspace_root, artifacts)
    _add_backup_cue(cues, workspace_root)
    _add_repository_intelligence_cue(cues, workspace_root, repository_intelligence)
    _add_provider_cue(cues, workspace_root, provider_canary)
    _add_eval_cue(cues, workspace_root, verification)
    return cues


def build_readiness_maintenance_cues(
    workspace_root: Path,
    checks: Sequence[object],
) -> list[MaintenanceCue]:
    """Project first-run readiness warnings into the shared cue vocabulary."""

    cues: list[MaintenanceCue] = []
    target = _target(workspace_root, NextActionTargetKind.WORKSPACE)
    for check in checks:
        check_id = getattr(check, "check_id", "")
        status = getattr(check, "status", "pass")
        kind = READINESS_MAINTENANCE_CHECKS.get(check_id)
        if status == "pass" or kind is None:
            continue
        title = str(getattr(check, "title", check_id))
        path = str(getattr(check, "path", None) or workspace_root)
        actions = [
            _display_action(
                workspace_root, f"readiness:{check_id}:{index}", action, target
            )
            for index, action in enumerate(getattr(check, "next_actions", [])[:4])
        ]
        cues.append(
            _cue(
                workspace_root,
                kind,
                target=target,
                title=title,
                summary=str(
                    getattr(check, "detail", "Readiness check needs attention.")
                ),
                priority=NextActionPriority.ACTION_NEEDED
                if status == "fail"
                else NextActionPriority.RECOMMENDED,
                severity=NextActionSeverity.HIGH
                if status == "fail"
                else NextActionSeverity.LOW,
                evidence=[
                    _evidence(
                        _evidence_kind_for_cue(kind),
                        path,
                        f"First-run readiness check {check_id} is {status}.",
                        freshness=status,
                    )
                ],
                actions=actions,
            )
        )
    _add_backup_cue(cues, workspace_root, readiness=True)
    return cues


def cue_next_action_commands(cues: Sequence[MaintenanceCue]) -> list[str]:
    """Return unique command displays from maintenance cue safe actions."""

    commands = [
        action.command.display
        for cue in cues
        for action in cue.safe_next_actions
        if action.command is not None
    ]
    return list(dict.fromkeys(commands))


def build_observability_next_actions(
    sections: Sequence[object],
    maintenance_cues: Sequence[MaintenanceCue],
) -> list[str]:
    """Merge section and cue next-action text without duplicates."""

    next_actions = [
        action
        for section in sections
        for action in getattr(section, "next_actions", [])
    ]
    next_actions.extend(cue_next_action_commands(maintenance_cues))
    return list(dict.fromkeys(next_actions))


def _add_background_job_cue(
    cues: list[MaintenanceCue],
    workspace_root: Path,
    jobs: BackgroundJobObservability,
) -> None:
    problem_count = (
        jobs.failed_count
        + jobs.retryable_count
        + jobs.abandoned_count
        + jobs.stale_count
    )
    if not problem_count:
        return
    target = _target(workspace_root, NextActionTargetKind.BACKGROUND_JOB)
    cues.append(
        _cue(
            workspace_root,
            MaintenanceCueKind.FAILED_BACKGROUND_JOBS,
            target=target,
            title="Background job recovery",
            summary=(
                f"{jobs.failed_count} failed, {jobs.retryable_count} retryable, "
                f"{jobs.stale_count} stale, and {jobs.abandoned_count} abandoned "
                "job(s)."
            ),
            priority=NextActionPriority.ACTION_NEEDED
            if jobs.failed_count or jobs.retryable_count
            else NextActionPriority.DEGRADED,
            severity=NextActionSeverity.HIGH
            if jobs.failed_count
            else NextActionSeverity.MEDIUM,
            evidence=[
                _evidence(
                    NextActionEvidenceKind.BACKGROUND_JOB,
                    str(workspace_root),
                    "Background job observability reports recovery work.",
                )
            ],
            actions=[
                _action(
                    workspace_root,
                    "background-jobs:list",
                    "Inspect background jobs",
                    "Review failed, stale, and retryable background jobs.",
                    NextActionKind.INSPECT,
                    NextActionPriority.ACTION_NEEDED,
                    NextActionSeverity.MEDIUM,
                    target,
                    ["glassbox", "job", "list", "--cwd", "."],
                )
            ],
        )
    )


def _add_artifact_cue(
    cues: list[MaintenanceCue],
    workspace_root: Path,
    artifacts: ArtifactObservability,
) -> None:
    if not artifacts.storage_warning and not (
        artifacts.candidate_count + artifacts.missing_reference_count
    ):
        return
    target = _target(workspace_root, NextActionTargetKind.ARTIFACT)
    summary = artifacts.storage_warning or (
        f"{artifacts.candidate_count} artifact prune candidate(s) and "
        f"{artifacts.missing_reference_count} missing reference(s)."
    )
    cues.append(
        _cue(
            workspace_root,
            MaintenanceCueKind.ARTIFACT_PRESSURE,
            target=target,
            title="Artifact pressure",
            summary=summary,
            priority=NextActionPriority.DEGRADED
            if artifacts.storage_warning
            else NextActionPriority.MAINTENANCE_ONLY,
            severity=NextActionSeverity.MEDIUM
            if artifacts.storage_warning
            else NextActionSeverity.LOW,
            evidence=[
                _evidence(
                    NextActionEvidenceKind.ARTIFACT,
                    str(workspace_root),
                    "Artifact retention observability found maintenance work.",
                )
            ],
            actions=[
                _action(
                    workspace_root,
                    "artifacts:inspect",
                    "Inspect artifact retention",
                    "Review artifact pressure before pruning.",
                    NextActionKind.INSPECT,
                    NextActionPriority.MAINTENANCE_ONLY,
                    NextActionSeverity.LOW,
                    target,
                    ["glassbox", "artifacts", "inspect", "--cwd", "."],
                ),
                _action(
                    workspace_root,
                    "artifacts:dry-run",
                    "Preview artifact pruning",
                    "Run a dry-run before any destructive artifact cleanup.",
                    NextActionKind.INSPECT,
                    NextActionPriority.MAINTENANCE_ONLY,
                    NextActionSeverity.LOW,
                    target,
                    ["glassbox", "artifacts", "prune", "--dry-run", "--cwd", "."],
                ),
            ],
            destructive_note=(
                "Non-dry-run artifact pruning is intentionally left behind an "
                "explicit operator command."
            ),
        )
    )


def _add_backup_cue(
    cues: list[MaintenanceCue],
    workspace_root: Path,
    *,
    readiness: bool = False,
) -> None:
    if not _missing_backup(workspace_root):
        return
    target = _target(workspace_root, NextActionTargetKind.WORKSPACE)
    summary = "No retained workspace backup archive was found under .glassbox/backups."
    if readiness:
        summary += " This advisory cue does not affect readiness status."
    cues.append(
        _cue(
            workspace_root,
            MaintenanceCueKind.BACKUP_POSTURE,
            target=target,
            title="Backup posture",
            summary=summary,
            priority=NextActionPriority.RECOMMENDED,
            severity=NextActionSeverity.INFO,
            evidence=[
                _evidence(
                    NextActionEvidenceKind.ARTIFACT,
                    str(workspace_root / ".glassbox" / "backups"),
                    "Backup posture is derived from local backup archive presence.",
                    freshness="missing",
                )
            ],
            actions=[
                _action(
                    workspace_root,
                    "backup:create",
                    "Create a workspace backup",
                    "Capture state before deeper maintenance or recovery work.",
                    NextActionKind.MAINTAIN,
                    NextActionPriority.RECOMMENDED,
                    NextActionSeverity.INFO,
                    target,
                    ["glassbox", "backup", "create", "--cwd", "."],
                )
            ],
        )
    )


def _add_repository_intelligence_cue(
    cues: list[MaintenanceCue],
    workspace_root: Path,
    intelligence: RepositoryIntelligenceObservability,
) -> None:
    if intelligence.status == "fresh":
        return
    target = _target(workspace_root, NextActionTargetKind.REPOSITORY_INTELLIGENCE)
    actions = [
        _display_action(
            workspace_root, f"repository-intelligence:{index}", action, target
        )
        for index, action in enumerate(intelligence.next_actions[:4])
    ]
    cues.append(
        _cue(
            workspace_root,
            MaintenanceCueKind.STALE_REPOSITORY_INTELLIGENCE,
            target=target,
            title="Repository intelligence posture",
            summary=(
                f"Repository intelligence is {intelligence.status}; "
                f"{intelligence.warning_count} warning cue(s), "
                f"{intelligence.missing_count} missing source(s)."
            ),
            priority=NextActionPriority.DEGRADED
            if intelligence.status in {"degraded", "conflicting", "stale"}
            else NextActionPriority.RECOMMENDED,
            severity=NextActionSeverity.HIGH
            if intelligence.status in {"degraded", "conflicting"}
            else NextActionSeverity.MEDIUM,
            evidence=[
                _evidence(
                    NextActionEvidenceKind.REPOSITORY_INTELLIGENCE,
                    str(workspace_root),
                    "Repository intelligence observability found freshness cues.",
                    freshness=intelligence.status,
                )
            ],
            actions=actions,
        )
    )


def _add_provider_cue(
    cues: list[MaintenanceCue],
    workspace_root: Path,
    provider: ProviderCanaryEvidenceSummary,
) -> None:
    if provider.freshness_status == "fresh" and provider.latest_status not in {
        "failed",
        "missing",
        "warning",
    }:
        return
    target = _target(workspace_root, NextActionTargetKind.PROVIDER)
    cues.append(
        _cue(
            workspace_root,
            MaintenanceCueKind.PROVIDER_CONFIG_ISSUES,
            target=target,
            title="Provider posture",
            summary=(
                f"Provider canary is {provider.latest_status}; freshness is "
                f"{provider.freshness_status}."
            ),
            priority=NextActionPriority.DEGRADED
            if provider.latest_status == "failed"
            else NextActionPriority.RECOMMENDED,
            severity=NextActionSeverity.MEDIUM
            if provider.latest_status == "failed"
            else NextActionSeverity.LOW,
            evidence=[
                _evidence(
                    NextActionEvidenceKind.CLI_OUTPUT,
                    provider.latest_summary_path or str(workspace_root),
                    "Provider canary retained evidence informs provider posture.",
                    freshness=provider.freshness_status,
                )
            ],
            actions=[
                _action(
                    workspace_root,
                    "provider:diagnostics",
                    "Inspect provider diagnostics",
                    "Review local provider configuration without running a canary.",
                    NextActionKind.INSPECT,
                    NextActionPriority.RECOMMENDED,
                    NextActionSeverity.LOW,
                    target,
                    ["glassbox", "provider", "diagnostics", "--cwd", "."],
                ),
                _action(
                    workspace_root,
                    "provider:evidence",
                    "Inspect provider canary evidence",
                    "Review retained canary evidence before live provider tests.",
                    NextActionKind.INSPECT,
                    NextActionPriority.RECOMMENDED,
                    NextActionSeverity.LOW,
                    target,
                    ["glassbox", "provider", "canary", "evidence", "--cwd", "."],
                ),
            ],
        )
    )


def _add_eval_cue(
    cues: list[MaintenanceCue],
    workspace_root: Path,
    verification: VerificationObservability,
) -> None:
    if verification.summary_count and verification.latest_suite_status != "failed":
        return
    target = _target(workspace_root, NextActionTargetKind.VERIFICATION)
    failed = verification.latest_suite_status == "failed"
    actions = [
        _display_action(workspace_root, "eval-baseline:action", action, target)
        for action in verification.next_actions[:1]
    ] or [
        _action(
            workspace_root,
            "eval-baseline:run",
            "Run eval baseline",
            "Collect retained eval evidence for maintenance posture.",
            NextActionKind.VERIFY,
            NextActionPriority.RECOMMENDED,
            NextActionSeverity.INFO,
            target,
            ["glassbox", "eval", "run", "--cwd", "."],
        )
    ]
    cues.append(
        _cue(
            workspace_root,
            MaintenanceCueKind.EVAL_BASELINE_DRIFT,
            target=target,
            title="Eval baseline posture",
            summary="Latest retained eval suite failed."
            if failed
            else "No retained eval summary is available for this workspace.",
            priority=NextActionPriority.ACTION_NEEDED
            if failed
            else NextActionPriority.RECOMMENDED,
            severity=NextActionSeverity.MEDIUM if failed else NextActionSeverity.INFO,
            evidence=[
                _evidence(
                    NextActionEvidenceKind.EVAL,
                    verification.latest_summary_path or str(workspace_root),
                    "Eval summary observability informs baseline posture.",
                    freshness=None if failed else "missing",
                )
            ],
            actions=actions,
        )
    )


def _cue(
    workspace_root: Path,
    kind: MaintenanceCueKind,
    *,
    target: NextActionTarget,
    title: str,
    summary: str,
    priority: NextActionPriority,
    severity: NextActionSeverity,
    evidence: list[NextActionEvidenceRef],
    actions: list[NextAction],
    destructive_note: str | None = None,
) -> MaintenanceCue:
    return MaintenanceCue(
        cue_id=f"maintenance:{workspace_root}:{kind.value}",
        kind=kind,
        title=title,
        summary=summary,
        priority=priority,
        severity=severity,
        target=target,
        safe_next_actions=actions,
        supporting_evidence=[
            ref for ref in evidence if ref.freshness not in {"missing", "stale", "fail"}
        ],
        missing_evidence=[
            ref for ref in evidence if ref.freshness in {"missing", "fail"}
        ],
        stale_evidence=[ref for ref in evidence if ref.freshness == "stale"],
        limitations=[
            "Maintenance cues are advisory unless a narrower readiness check "
            "blocks work."
        ],
        destructive_remediation_available=destructive_note is not None,
        destructive_remediation_note=destructive_note,
    )


def _action(
    workspace_root: Path,
    action_id: str,
    title: str,
    summary: str,
    kind: NextActionKind,
    priority: NextActionPriority,
    severity: NextActionSeverity,
    target: NextActionTarget,
    command: list[str],
) -> NextAction:
    return NextAction(
        action_id=action_id,
        title=title,
        summary=summary,
        kind=kind,
        priority=priority,
        severity=severity,
        safety_class=NextActionSafetyClass.COMMAND_RECIPE,
        target=target,
        command=NextActionCommandRecipe(
            command=command,
            display=" ".join(command),
            purpose=summary,
            requires_approval=True,
            cwd_hint=str(workspace_root),
        ),
        recommended_surfaces=[NextActionSurface.CLI, NextActionSurface.DASHBOARD],
    )


def _display_action(
    workspace_root: Path,
    action_id: str,
    display: str,
    target: NextActionTarget,
) -> NextAction:
    command = _command_from_display(display)
    return NextAction(
        action_id=action_id,
        title="Inspect maintenance posture",
        summary=display,
        kind=NextActionKind.INSPECT,
        priority=NextActionPriority.RECOMMENDED,
        severity=NextActionSeverity.LOW,
        safety_class=NextActionSafetyClass.COMMAND_RECIPE
        if command is not None
        else NextActionSafetyClass.READ_ONLY,
        target=target,
        command=(
            NextActionCommandRecipe(
                command=command,
                display=" ".join(command),
                purpose="Inspect maintenance posture before taking action.",
                requires_approval=True,
                cwd_hint=str(workspace_root),
            )
            if command is not None
            else None
        ),
        recommended_surfaces=[NextActionSurface.CLI, NextActionSurface.DASHBOARD],
    )


def _target(
    workspace_root: Path,
    kind: NextActionTargetKind,
) -> NextActionTarget:
    label = kind.value.replace("_", " ").title()
    if kind == NextActionTargetKind.WORKSPACE:
        label = "Workspace"
    return NextActionTarget(kind=kind, target_id=str(workspace_root), label=label)


def _evidence(
    kind: NextActionEvidenceKind,
    ref_id: str,
    summary: str,
    *,
    freshness: str | None = None,
) -> NextActionEvidenceRef:
    return NextActionEvidenceRef(
        kind=kind,
        ref_id=ref_id,
        summary=summary,
        freshness=freshness,
    )


def _evidence_kind_for_cue(kind: MaintenanceCueKind) -> NextActionEvidenceKind:
    if kind == MaintenanceCueKind.PACKAGE_ASSET_STALENESS:
        return NextActionEvidenceKind.ARTIFACT
    if kind == MaintenanceCueKind.STALE_REPOSITORY_INTELLIGENCE:
        return NextActionEvidenceKind.REPOSITORY_INTELLIGENCE
    if kind == MaintenanceCueKind.EVAL_BASELINE_DRIFT:
        return NextActionEvidenceKind.EVAL
    return NextActionEvidenceKind.CLI_OUTPUT


def _command_from_display(display: str) -> list[str] | None:
    text = display.strip()
    if text.startswith("`") and "`" in text[1:]:
        text = text[1:].split("`", 1)[0]
    elif not text.startswith("glassbox "):
        return None
    try:
        command = shlex.split(text)
    except ValueError:
        return None
    return command or None


def _missing_backup(workspace_root: Path) -> bool:
    backup_dir = workspace_root / ".glassbox" / "backups"
    if not backup_dir.exists():
        return True
    return not any(path.suffix == ".zip" for path in backup_dir.glob("*.zip"))


__all__ = [
    "READINESS_MAINTENANCE_CHECKS",
    "build_observability_maintenance_cues",
    "build_observability_next_actions",
    "build_readiness_maintenance_cues",
    "cue_next_action_commands",
]
