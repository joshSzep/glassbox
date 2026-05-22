"""Release-candidate v17 handoff readiness derivation."""

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
from glassbox.runtime.handoff_readiness_reasons import freshness_for_state
from glassbox.runtime.observability import WorkspaceObservabilityReport


def derive_release_handoff_readiness(
    report: WorkspaceObservabilityReport,
    *,
    intent: HandoffIntent = HandoffIntent.RELEASE_SIGNOFF,
) -> HandoffReadiness:
    """Derive advisory handoff readiness for release-candidate evidence."""

    supporting_evidence = _supporting_evidence(report)
    missing_evidence = _missing_evidence(report)
    stale_evidence = _stale_evidence(report)
    local_only_evidence = _local_only_evidence(report)
    reasons = _reasons(report)
    limitations = _limitations(report, local_only_evidence=local_only_evidence)
    state = _state(
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
        confidence=confidence_for_state(state),
        freshness=freshness_for_state(state),
        reasons=reasons,
        supporting_evidence=supporting_evidence,
        missing_evidence=missing_evidence,
        stale_evidence=stale_evidence,
        local_only_evidence=local_only_evidence,
        limitations=limitations,
        safe_first_commands=_safe_commands(),
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


def _state(
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


def _supporting_evidence(
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


def _missing_evidence(
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


def _stale_evidence(
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


def _local_only_evidence(
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


def _reasons(
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


def _limitations(
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


def _safe_commands() -> list[HandoffSafeCommand]:
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
]
