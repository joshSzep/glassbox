"""Workspace-level v17 handoff readiness derivation."""

from pathlib import Path

from glassbox.core import HandoffIntent
from glassbox.core import HandoffReadiness
from glassbox.core import HandoffReadinessReason
from glassbox.core import HandoffReadinessReasonKind
from glassbox.core import HandoffReadinessState
from glassbox.core import HandoffSafeCommand
from glassbox.core import HandoffSourceKind
from glassbox.core import HandoffSourceRef
from glassbox.core import NextActionEvidenceKind
from glassbox.core import NextActionEvidenceRef
from glassbox.runtime.handoff_readiness_reasons import confidence_for_state
from glassbox.runtime.handoff_readiness_reasons import evidence_ref
from glassbox.runtime.handoff_readiness_reasons import freshness_for_state
from glassbox.runtime.observability import WorkspaceObservabilityReport

_WORKSPACE_DEGRADED_STATES = {
    HandoffReadinessState.BLOCKED,
    HandoffReadinessState.FAILED_NEEDS_TRIAGE,
}


def derive_workspace_handoff_readiness(
    report: WorkspaceObservabilityReport,
    *,
    intent: HandoffIntent = HandoffIntent.FUTURE_SELF,
) -> HandoffReadiness:
    """Derive advisory handoff readiness for the current workspace."""

    supporting_evidence = _supporting_evidence(report)
    missing_evidence = _missing_evidence(report)
    stale_evidence = _stale_evidence(report)
    local_only_evidence = _local_only_evidence(report)
    reasons = _reasons(report)
    limitations = _limitations(
        report,
        intent=intent,
        local_only_evidence=local_only_evidence,
    )
    state = _state(
        report,
        stale_evidence=stale_evidence,
        local_only_evidence=local_only_evidence,
        intent=intent,
    )

    return HandoffReadiness(
        source=HandoffSourceRef(
            kind=HandoffSourceKind.WORKSPACE,
            primary_id="workspace",
            identifiers={"workspace_root": report.workspace_root},
            label=Path(report.workspace_root).name or report.workspace_root,
        ),
        intent=intent,
        state=state,
        confidence=confidence_for_state(
            state,
            degraded_states=_WORKSPACE_DEGRADED_STATES,
        ),
        freshness=freshness_for_state(
            state,
            degraded_states=_WORKSPACE_DEGRADED_STATES,
        ),
        reasons=reasons,
        supporting_evidence=supporting_evidence,
        missing_evidence=missing_evidence,
        stale_evidence=stale_evidence,
        local_only_evidence=local_only_evidence,
        limitations=limitations,
        safe_first_commands=_safe_commands(report),
        non_claims=[
            "workspace handoff readiness is advisory local posture, not ownership",
            (
                "workspace handoff readiness does not approve, resume, stage, "
                "commit, push, merge, deploy, publish, or release"
            ),
            (
                "workspace handoff summarizes local projections and retained "
                "evidence without exporting raw .glassbox state"
            ),
            (
                "daemon ownership, approval policy, and mutation boundaries remain "
                "controlled by existing local runtime policy"
            ),
        ],
    )


def _state(
    report: WorkspaceObservabilityReport,
    *,
    stale_evidence: list[NextActionEvidenceRef],
    local_only_evidence: list[HandoffReadinessReason],
    intent: HandoffIntent,
) -> HandoffReadinessState:
    if report.projections.unavailable_count:
        return HandoffReadinessState.BLOCKED
    if report.tasks.failed_count or report.background_jobs.failed_count:
        return HandoffReadinessState.FAILED_NEEDS_TRIAGE
    if report.tasks.verification_failed_count:
        return HandoffReadinessState.NEEDS_VERIFICATION
    if report.tasks.blocked_count or report.tasks.budget_exhausted_count:
        return HandoffReadinessState.BLOCKED
    if stale_evidence:
        return HandoffReadinessState.STALE_EVIDENCE
    if local_only_evidence and intent != HandoffIntent.FUTURE_SELF:
        return HandoffReadinessState.LOCAL_ONLY_EVIDENCE
    return HandoffReadinessState.READY


def _supporting_evidence(
    report: WorkspaceObservabilityReport,
) -> list[NextActionEvidenceRef]:
    evidence = [
        _evidence(
            NextActionEvidenceKind.CLI_OUTPUT,
            "observability-status",
            (
                f"Runtime {report.runtime.state}; "
                f"{report.projections.session_count} session projection(s); "
                f"{report.tasks.task_count} task(s)."
            ),
        ),
        _evidence(
            NextActionEvidenceKind.REPOSITORY_INTELLIGENCE,
            "repository-intelligence",
            (
                f"Repository intelligence {report.repository_intelligence.status}; "
                f"index {report.repository_intelligence.index_status}."
            ),
        ),
        _evidence(
            NextActionEvidenceKind.ARTIFACT,
            "artifact-retention",
            (
                f"{report.artifacts.protected_count} protected artifact(s), "
                f"{report.artifacts.candidate_count} prune candidate(s)."
            ),
        ),
    ]
    if report.verification.latest_suite_status is not None:
        evidence.append(
            _evidence(
                NextActionEvidenceKind.EVAL,
                "latest-eval-summary",
                (
                    f"Latest eval suite {report.verification.latest_suite_status} "
                    f"for {report.verification.latest_profile_id or 'unknown'}."
                ),
                freshness="fresh"
                if report.verification.latest_exit_code == 0
                else "degraded",
            )
        )
    return evidence[:50]


def _missing_evidence(
    report: WorkspaceObservabilityReport,
) -> list[NextActionEvidenceRef]:
    missing: list[NextActionEvidenceRef] = []
    if report.repository_index.status == "missing":
        missing.append(
            _evidence(
                NextActionEvidenceKind.REPOSITORY_INTELLIGENCE,
                "repository-index",
                (
                    "Repository index is missing; workspace handoff has weaker "
                    "path context."
                ),
                freshness="missing",
            )
        )
    if report.verification.summary_count == 0:
        missing.append(
            _evidence(
                NextActionEvidenceKind.EVAL,
                "eval-summary",
                "No retained eval summary is available for this workspace.",
                freshness="missing",
            )
        )
    return missing


def _stale_evidence(
    report: WorkspaceObservabilityReport,
) -> list[NextActionEvidenceRef]:
    stale: list[NextActionEvidenceRef] = []
    if report.projections.degraded_count or report.projections.stale_count:
        stale.append(
            _evidence(
                NextActionEvidenceKind.PROJECTION,
                "projection-health",
                (
                    f"{report.projections.degraded_count} degraded and "
                    f"{report.projections.stale_count} stale projection(s)."
                ),
                freshness="stale",
            )
        )
    if report.repository_index.status in {"stale", "failed"}:
        stale.append(
            _evidence(
                NextActionEvidenceKind.REPOSITORY_INTELLIGENCE,
                "repository-index",
                f"Repository index is {report.repository_index.status}.",
                freshness=report.repository_index.status,
            )
        )
    if report.repository_intelligence.status in {"stale", "degraded"}:
        stale.append(
            _evidence(
                NextActionEvidenceKind.REPOSITORY_INTELLIGENCE,
                "repository-intelligence",
                f"Repository intelligence is {report.repository_intelligence.status}.",
                freshness=report.repository_intelligence.status,
            )
        )
    return stale[:50]


def _local_only_evidence(
    report: WorkspaceObservabilityReport,
) -> list[HandoffReadinessReason]:
    reasons: list[HandoffReadinessReason] = []
    if report.artifacts.protected_count or report.artifacts.candidate_count:
        reasons.append(
            HandoffReadinessReason(
                kind=HandoffReadinessReasonKind.LOCAL_ONLY_EVIDENCE,
                summary=(
                    "Managed artifacts and retention candidates remain local "
                    "evidence unless exported through a redacted package profile."
                ),
                portable=False,
            )
        )
    if report.provider_canary.summary_count:
        reasons.append(
            HandoffReadinessReason(
                kind=HandoffReadinessReasonKind.MANUAL_ONLY_EVIDENCE,
                summary=(
                    "Provider-canary evidence is retained locally and advisory; "
                    "it should not be treated as deterministic release evidence."
                ),
                portable=False,
            )
        )
    return reasons


def _reasons(
    report: WorkspaceObservabilityReport,
) -> list[HandoffReadinessReason]:
    reasons: list[HandoffReadinessReason] = []
    if report.tasks.failed_count:
        reasons.append(
            HandoffReadinessReason(
                kind=HandoffReadinessReasonKind.UNSUPPORTED_EVIDENCE,
                summary=f"{report.tasks.failed_count} failed task(s) need triage.",
            )
        )
    if report.background_jobs.failed_count:
        reasons.append(
            HandoffReadinessReason(
                kind=HandoffReadinessReasonKind.UNSUPPORTED_EVIDENCE,
                summary=(
                    f"{report.background_jobs.failed_count} failed background "
                    "job(s) need triage."
                ),
            )
        )
    if report.tasks.blocked_count:
        reasons.append(
            HandoffReadinessReason(
                kind=HandoffReadinessReasonKind.POLICY_BLOCKER,
                summary=f"{report.tasks.blocked_count} blocked task(s) need review.",
            )
        )
    if report.tasks.verification_failed_count:
        reasons.append(
            HandoffReadinessReason(
                kind=HandoffReadinessReasonKind.MISSING_EVIDENCE,
                summary=(
                    f"{report.tasks.verification_failed_count} task verification "
                    "failure(s) need follow-up."
                ),
            )
        )
    return reasons[:50]


def _limitations(
    report: WorkspaceObservabilityReport,
    *,
    intent: HandoffIntent,
    local_only_evidence: list[HandoffReadinessReason],
) -> list[str]:
    limitations: list[str] = []
    if report.runtime.state != "not_running":
        limitations.append(
            "A runtime owner may be active; custody metadata does not override daemon "
            "ownership or approval policy."
        )
    if (
        report.repository_intelligence.warning_count
        or report.repository_intelligence.missing_count
    ):
        limitations.append(
            "Repository-intelligence cues are advisory and freshness-aware."
        )
    if local_only_evidence:
        limitations.append(
            "Some workspace evidence remains local-only and must be inspected in the "
            "source workspace."
        )
    if intent == HandoffIntent.REVIEW_ONLY:
        limitations.append(
            "Review-only workspace handoff does not imply continuation authority."
        )
    return list(dict.fromkeys(limitations))[:50]


def _safe_commands(
    report: WorkspaceObservabilityReport,
) -> list[HandoffSafeCommand]:
    commands = [
        _safe_command(
            "glassbox observability status --cwd .",
            "Inspect workspace health, queue, evidence, and maintenance posture.",
        ),
        _safe_command(
            "glassbox queue list --cwd .",
            "Inspect operator queue rows before accepting a workspace handoff.",
        ),
        _safe_command(
            "glassbox repo index status --cwd .",
            "Inspect repository-index freshness before relying on path context.",
        ),
        _safe_command(
            "glassbox artifacts inspect --cwd .",
            "Inspect managed artifact posture without exporting raw evidence.",
        ),
        _safe_command(
            "glassbox job list --cwd .",
            "Inspect background jobs and retryable failures.",
        ),
    ]
    if report.verification.summary_count:
        commands.append(
            _safe_command(
                "glassbox eval audit --cwd .",
                "Inspect eval coverage expectations without executing evals.",
            )
        )
    return commands


def _safe_command(display: str, purpose: str) -> HandoffSafeCommand:
    return HandoffSafeCommand(
        command=display.split(),
        display=display,
        purpose=purpose,
    )


def _evidence(
    kind: NextActionEvidenceKind,
    ref_id: str,
    summary: str,
    *,
    freshness: str | None = None,
) -> NextActionEvidenceRef:
    return evidence_ref(
        kind,
        ref_id,
        summary,
        freshness=freshness,
    )


__all__ = [
    "derive_workspace_handoff_readiness",
]
