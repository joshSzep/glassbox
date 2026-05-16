"""Workspace and release-candidate v17 handoff readiness derivation."""

from pathlib import Path

from glassbox.core import HandoffEvidenceFreshness
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
from glassbox.core import RepositoryIntelligenceConfidence
from glassbox.runtime.observability import WorkspaceObservabilityReport


def derive_workspace_handoff_readiness(
    report: WorkspaceObservabilityReport,
    *,
    intent: HandoffIntent = HandoffIntent.FUTURE_SELF,
) -> HandoffReadiness:
    """Derive advisory handoff readiness for the current workspace."""

    supporting_evidence = _workspace_supporting_evidence(report)
    missing_evidence = _workspace_missing_evidence(report)
    stale_evidence = _workspace_stale_evidence(report)
    local_only_evidence = _workspace_local_only_evidence(report)
    reasons = _workspace_reasons(report)
    limitations = _workspace_limitations(
        report,
        intent=intent,
        local_only_evidence=local_only_evidence,
    )
    state = _workspace_state(
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
        confidence=_confidence_for_state(state),
        freshness=_freshness_for_state(state),
        reasons=reasons,
        supporting_evidence=supporting_evidence,
        missing_evidence=missing_evidence,
        stale_evidence=stale_evidence,
        local_only_evidence=local_only_evidence,
        limitations=limitations,
        safe_first_commands=_workspace_safe_commands(report),
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


def derive_release_handoff_readiness(
    report: WorkspaceObservabilityReport,
    *,
    intent: HandoffIntent = HandoffIntent.RELEASE_SIGNOFF,
) -> HandoffReadiness:
    """Derive advisory handoff readiness for release-candidate evidence."""

    supporting_evidence = _release_supporting_evidence(report)
    missing_evidence = _release_missing_evidence(report)
    stale_evidence = _release_stale_evidence(report)
    local_only_evidence = _release_local_only_evidence(report)
    reasons = _release_reasons(report)
    limitations = _release_limitations(report, local_only_evidence=local_only_evidence)
    state = _release_state(
        report,
        missing_evidence=missing_evidence,
        stale_evidence=stale_evidence,
        local_only_evidence=local_only_evidence,
        intent=intent,
    )

    return HandoffReadiness(
        source=HandoffSourceRef(
            kind=HandoffSourceKind.RELEASE,
            primary_id="release-candidate",
            identifiers={"workspace_root": report.workspace_root},
            label="release candidate",
        ),
        intent=intent,
        state=state,
        confidence=_confidence_for_state(state),
        freshness=_freshness_for_state(state),
        reasons=reasons,
        supporting_evidence=supporting_evidence,
        missing_evidence=missing_evidence,
        stale_evidence=stale_evidence,
        local_only_evidence=local_only_evidence,
        limitations=limitations,
        safe_first_commands=_release_safe_commands(),
        non_claims=[
            "release handoff readiness is advisory local evidence posture",
            (
                "release handoff readiness is not release approval, publication "
                "approval, deployment approval, or maintainer signoff"
            ),
            (
                "deterministic eval, package, and installed-smoke evidence remains "
                "separate from advisory provider, browser, dashboard, and manual "
                "evidence"
            ),
            (
                "handoff does not run release gates, publish packages, push tags, "
                "create pull requests, or mutate repository history"
            ),
        ],
    )


def _workspace_state(
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


def _release_state(
    report: WorkspaceObservabilityReport,
    *,
    missing_evidence: list[NextActionEvidenceRef],
    stale_evidence: list[NextActionEvidenceRef],
    local_only_evidence: list[HandoffReadinessReason],
    intent: HandoffIntent,
) -> HandoffReadinessState:
    if report.verification.latest_exit_code not in {None, 0}:
        return HandoffReadinessState.NEEDS_VERIFICATION
    if missing_evidence:
        return HandoffReadinessState.NEEDS_VERIFICATION
    if stale_evidence:
        return HandoffReadinessState.STALE_EVIDENCE
    if local_only_evidence and intent != HandoffIntent.FUTURE_SELF:
        return HandoffReadinessState.LOCAL_ONLY_EVIDENCE
    return HandoffReadinessState.READY


def _workspace_supporting_evidence(
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


def _workspace_missing_evidence(
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


def _workspace_stale_evidence(
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


def _workspace_local_only_evidence(
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


def _workspace_reasons(
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


def _workspace_limitations(
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


def _release_supporting_evidence(
    report: WorkspaceObservabilityReport,
) -> list[NextActionEvidenceRef]:
    evidence = [
        _evidence(
            NextActionEvidenceKind.RELEASE_GATE,
            "release-surface-status",
            (
                "Repository release surfaces are "
                f"{report.repository_intelligence.release_surface_status}."
            ),
        ),
    ]
    if report.verification.latest_suite_status is not None:
        evidence.append(
            _evidence(
                NextActionEvidenceKind.EVAL,
                "latest-release-eval",
                (
                    f"Latest retained eval suite "
                    f"{report.verification.latest_suite_status}; "
                    f"{report.verification.latest_passed_case_count or 0} passed, "
                    f"{report.verification.latest_failed_case_count or 0} failed."
                ),
                source_path=report.verification.latest_summary_path,
                freshness="fresh"
                if report.verification.latest_exit_code == 0
                else "degraded",
            )
        )
    return evidence[:50]


def _release_missing_evidence(
    report: WorkspaceObservabilityReport,
) -> list[NextActionEvidenceRef]:
    missing: list[NextActionEvidenceRef] = []
    if report.verification.summary_count == 0:
        missing.append(
            _evidence(
                NextActionEvidenceKind.EVAL,
                "release-eval-summary",
                "No retained eval summary is available for release handoff.",
                freshness="missing",
            )
        )
    if report.repository_intelligence.release_surface_status == "missing":
        missing.append(
            _evidence(
                NextActionEvidenceKind.RELEASE_GATE,
                "release-surfaces",
                "Repository release-surface intelligence is missing.",
                freshness="missing",
            )
        )
    return missing


def _release_stale_evidence(
    report: WorkspaceObservabilityReport,
) -> list[NextActionEvidenceRef]:
    stale: list[NextActionEvidenceRef] = []
    if report.repository_intelligence.release_surface_status in {"stale", "degraded"}:
        stale.append(
            _evidence(
                NextActionEvidenceKind.RELEASE_GATE,
                "release-surfaces",
                (
                    "Repository release-surface intelligence is "
                    f"{report.repository_intelligence.release_surface_status}."
                ),
                freshness=report.repository_intelligence.release_surface_status,
            )
        )
    if report.provider_canary.stale:
        stale.append(
            _evidence(
                NextActionEvidenceKind.MANUAL_EVIDENCE,
                "provider-canary",
                "Provider-canary advisory evidence is stale.",
                freshness="stale",
            )
        )
    return stale


def _release_local_only_evidence(
    report: WorkspaceObservabilityReport,
) -> list[HandoffReadinessReason]:
    reasons: list[HandoffReadinessReason] = []
    if report.provider_canary.summary_count:
        reasons.append(
            HandoffReadinessReason(
                kind=HandoffReadinessReasonKind.MANUAL_ONLY_EVIDENCE,
                summary=(
                    "Provider-canary evidence is local advisory evidence and does "
                    "not become deterministic release signoff."
                ),
                portable=False,
            )
        )
    if report.artifacts.protected_count:
        reasons.append(
            HandoffReadinessReason(
                kind=HandoffReadinessReasonKind.LOCAL_ONLY_EVIDENCE,
                summary=(
                    "Release-supporting managed artifacts remain local unless a "
                    "future package profile includes redacted summaries."
                ),
                portable=False,
            )
        )
    return reasons


def _release_reasons(
    report: WorkspaceObservabilityReport,
) -> list[HandoffReadinessReason]:
    reasons: list[HandoffReadinessReason] = []
    if report.verification.latest_exit_code not in {None, 0}:
        reasons.append(
            HandoffReadinessReason(
                kind=HandoffReadinessReasonKind.MISSING_EVIDENCE,
                summary=(
                    "Latest retained eval suite failed; release handoff needs "
                    "verification follow-up."
                ),
            )
        )
    return reasons


def _release_limitations(
    report: WorkspaceObservabilityReport,
    *,
    local_only_evidence: list[HandoffReadinessReason],
) -> list[str]:
    limitations = [
        "Release handoff is for a human custodian and is not publication approval.",
        (
            "This summary inspects retained local evidence; it does not run release "
            "gates, package checks, or installed-wheel smoke."
        ),
    ]
    if report.provider_canary.summary_count:
        limitations.append(
            "Provider-canary evidence remains advisory unless promoted by a "
            "fixture-backed deterministic task."
        )
    if local_only_evidence:
        limitations.append(
            "Some release evidence is local-only and cannot be verified from a "
            "portable package alone."
        )
    return list(dict.fromkeys(limitations))[:50]


def _workspace_safe_commands(
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


def _release_safe_commands() -> list[HandoffSafeCommand]:
    return [
        _safe_command(
            "glassbox eval audit --profile release-candidate --cwd .",
            "Inspect release-candidate eval coverage without executing evals.",
        ),
        _safe_command(
            "glassbox eval profile show release-candidate --cwd .",
            "Inspect the release-candidate profile definition.",
        ),
        _safe_command(
            "glassbox provider canary evidence --cwd .",
            (
                "Inspect retained advisory provider evidence separately from "
                "release gates."
            ),
        ),
        _safe_command(
            "glassbox repo index status --cwd .",
            "Inspect repository intelligence freshness before release handoff.",
        ),
    ]


def _freshness_for_state(state: HandoffReadinessState) -> HandoffEvidenceFreshness:
    if state == HandoffReadinessState.STALE_EVIDENCE:
        return HandoffEvidenceFreshness.STALE
    if state in {
        HandoffReadinessState.NEEDS_CONTEXT,
        HandoffReadinessState.NEEDS_VERIFICATION,
    }:
        return HandoffEvidenceFreshness.MISSING
    if state in {
        HandoffReadinessState.BLOCKED,
        HandoffReadinessState.FAILED_NEEDS_TRIAGE,
    }:
        return HandoffEvidenceFreshness.DEGRADED
    return HandoffEvidenceFreshness.FRESH


def _confidence_for_state(
    state: HandoffReadinessState,
) -> RepositoryIntelligenceConfidence:
    if state == HandoffReadinessState.READY:
        return RepositoryIntelligenceConfidence.HIGH
    if state in {
        HandoffReadinessState.LOCAL_ONLY_EVIDENCE,
        HandoffReadinessState.STALE_EVIDENCE,
        HandoffReadinessState.ACCEPTED_WITH_RISK,
    }:
        return RepositoryIntelligenceConfidence.MEDIUM
    if state in {
        HandoffReadinessState.BLOCKED,
        HandoffReadinessState.FAILED_NEEDS_TRIAGE,
    }:
        return RepositoryIntelligenceConfidence.LOW
    return RepositoryIntelligenceConfidence.UNKNOWN


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
    source_path: str | None = None,
    freshness: str | None = None,
) -> NextActionEvidenceRef:
    return NextActionEvidenceRef(
        kind=kind,
        ref_id=ref_id,
        summary=summary,
        source_path=source_path,
        freshness=freshness,
    )


__all__ = [
    "derive_release_handoff_readiness",
    "derive_workspace_handoff_readiness",
]
