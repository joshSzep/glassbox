"""Structured recovery playbooks for maintenance cues."""

from collections.abc import Sequence

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core import MaintenanceCue
from glassbox.core import MaintenanceCueKind
from glassbox.core import NextActionEvidenceKind
from glassbox.core import NextActionEvidenceRef


class RecoveryPlaybookStep(BaseModel):
    """One inspection or remediation step in a local recovery playbook."""

    model_config = ConfigDict(extra="forbid")

    step_id: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=300)
    purpose: str = Field(min_length=1, max_length=1000)
    command: str | None = Field(default=None, min_length=1, max_length=1000)
    risk: str = Field(min_length=1, max_length=1000)
    requires_confirmation: bool = True
    destructive: bool = False


class RecoveryPlaybook(BaseModel):
    """Inspectable recovery guidance linked to one degraded maintenance cue."""

    model_config = ConfigDict(extra="forbid")

    playbook_id: str = Field(min_length=1, max_length=300)
    cue_id: str = Field(min_length=1, max_length=300)
    cue_kind: MaintenanceCueKind
    title: str = Field(min_length=1, max_length=300)
    summary: str = Field(min_length=1, max_length=2000)
    evidence_graph_links: list[NextActionEvidenceRef] = Field(default_factory=list)
    steps: list[RecoveryPlaybookStep] = Field(default_factory=list, min_length=1)
    limitations: list[str] = Field(default_factory=list, max_length=20)


def build_recovery_playbooks(
    maintenance_cues: Sequence[MaintenanceCue],
) -> list[RecoveryPlaybook]:
    """Build local, non-executing playbooks for maintenance cues."""

    return [_playbook_for_cue(cue) for cue in maintenance_cues]


def _playbook_for_cue(cue: MaintenanceCue) -> RecoveryPlaybook:
    return RecoveryPlaybook(
        playbook_id=f"recovery:{cue.kind.value}",
        cue_id=cue.cue_id,
        cue_kind=cue.kind,
        title=f"{cue.title} recovery playbook",
        summary=_summary_for_kind(cue.kind, cue.summary),
        evidence_graph_links=[
            NextActionEvidenceRef(
                kind=NextActionEvidenceKind.CLI_OUTPUT,
                ref_id=cue.cue_id,
                summary=f"Playbook addresses maintenance cue {cue.kind.value}.",
                freshness="current",
            ),
            *cue.supporting_evidence[:3],
            *cue.missing_evidence[:3],
            *cue.stale_evidence[:3],
        ],
        steps=[*_steps_from_actions(cue), *_extra_steps(cue.kind)],
        limitations=[
            "Playbooks are guidance only and do not execute commands.",
            "Commands that mutate state require a separate explicit operator run.",
            *cue.limitations[:3],
        ],
    )


def _steps_from_actions(cue: MaintenanceCue) -> list[RecoveryPlaybookStep]:
    steps: list[RecoveryPlaybookStep] = []
    for index, action in enumerate(cue.safe_next_actions, start=1):
        command = action.command.display if action.command is not None else None
        steps.append(
            RecoveryPlaybookStep(
                step_id=f"{cue.kind.value}:safe-action:{index}",
                title=action.title,
                purpose=action.summary,
                command=command,
                risk="Inspection-first cue action; review output before mutating.",
                requires_confirmation=action.command is not None,
                destructive=False,
            )
        )
    return steps


def _extra_steps(kind: MaintenanceCueKind) -> list[RecoveryPlaybookStep]:
    extras: dict[MaintenanceCueKind, list[RecoveryPlaybookStep]] = {
        MaintenanceCueKind.FAILED_BACKGROUND_JOBS: [
            _step(
                kind,
                "show-job",
                "Inspect one failed job",
                "Read the failure detail before choosing retry or abandon.",
                "glassbox job show JOB_ID --cwd .",
            ),
            _step(
                kind,
                "retry-job",
                "Retry a failed or stale job",
                "Retry only after confirming the job is safe to run again.",
                "glassbox job retry JOB_ID --reason REASON --cwd .",
            ),
            _step(
                kind,
                "abandon-job",
                "Abandon an unrecoverable job",
                "Record why the job should not be retried.",
                "glassbox job abandon JOB_ID --reason REASON --cwd .",
                destructive=True,
            ),
        ],
        MaintenanceCueKind.BACKUP_POSTURE: [
            _step(
                kind,
                "inspect-backup",
                "Inspect a retained backup",
                "Validate an existing archive before trusting it for recovery.",
                "glassbox backup inspect ARCHIVE --cwd .",
            )
        ],
        MaintenanceCueKind.EVAL_BASELINE_DRIFT: [
            _step(
                kind,
                "report-eval",
                "Review eval failure detail",
                "Inspect retained eval output before rerunning or accepting risk.",
                "glassbox eval report PROFILE_ID --cwd .",
            )
        ],
        MaintenanceCueKind.STALE_REPOSITORY_INTELLIGENCE: [
            _step(
                kind,
                "refresh-repository-intelligence",
                "Refresh repository intelligence",
                "Rebuild stale local intelligence after reviewing stale sources.",
                "glassbox repo refresh --cwd .",
            )
        ],
    }
    return extras.get(kind, [])


def _step(
    kind: MaintenanceCueKind,
    step_id: str,
    title: str,
    purpose: str,
    command: str,
    *,
    destructive: bool = False,
) -> RecoveryPlaybookStep:
    return RecoveryPlaybookStep(
        step_id=f"{kind.value}:{step_id}",
        title=title,
        purpose=purpose,
        command=command,
        risk=(
            "Destructive or terminal recovery step; run only after explicit "
            "operator confirmation."
            if destructive
            else "Guidance command; inspect output before follow-up actions."
        ),
        requires_confirmation=True,
        destructive=destructive,
    )


def _summary_for_kind(kind: MaintenanceCueKind, fallback: str) -> str:
    summaries = {
        MaintenanceCueKind.PROJECTION_DRIFT: (
            "Inspect projection lag, then rebuild derived state if stale output "
            "would lower operator confidence."
        ),
        MaintenanceCueKind.STALE_DAEMON_OWNER: (
            "Confirm stale owner metadata, then restart the local daemon through "
            "the daemon command surface."
        ),
        MaintenanceCueKind.ARTIFACT_PRESSURE: (
            "Inspect retention pressure and run dry-run pruning before any "
            "destructive cleanup."
        ),
        MaintenanceCueKind.PROVIDER_CONFIG_ISSUES: (
            "Review provider diagnostics and retained canary evidence before "
            "running live provider checks."
        ),
    }
    return summaries.get(kind, fallback)


__all__ = [
    "RecoveryPlaybook",
    "RecoveryPlaybookStep",
    "build_recovery_playbooks",
]
