"""Redaction preview facade for local handoff exports."""

from glassbox.core import HandoffIntent
from glassbox.core import HandoffLocalOnlySummary
from glassbox.core import HandoffReadiness
from glassbox.core import HandoffRedactionPosture
from glassbox.core import HandoffRedactionSummary
from glassbox.core import TaskId
from glassbox.runtime.handoff_local_only_inventory import build_local_only_inventory
from glassbox.runtime.handoff_local_only_inventory import (
    build_readiness_local_only_inventory,
)
from glassbox.runtime.handoff_redaction_preview_changeset import (
    build_changeset_redaction_preview,
)
from glassbox.runtime.handoff_redaction_preview_changeset import (
    changeset_redaction_preview_from_payload,
)
from glassbox.runtime.handoff_redaction_preview_models import HandoffRedactionPreview
from glassbox.runtime.handoff_redaction_preview_session import (
    build_session_redaction_preview,
)
from glassbox.runtime.handoff_redaction_preview_session import (
    session_redaction_preview_from_payload,
)
from glassbox.runtime.handoff_redaction_preview_shared import positive_counts
from glassbox.runtime.handoff_redaction_preview_shared import redaction_marker_summary
from glassbox.runtime.observability import WorkspaceObservabilityReport
from glassbox.runtime.task_handoff_readiness import derive_task_handoff_readiness
from glassbox.runtime.task_queries import TaskDetailView
from glassbox.runtime.task_queries import TaskQueryService
from glassbox.runtime.workspace_handoff_readiness import (
    derive_release_handoff_readiness,
)
from glassbox.runtime.workspace_handoff_readiness import (
    derive_workspace_handoff_readiness,
)

_redaction_marker_summary = redaction_marker_summary


def build_task_redaction_preview(
    task_id: TaskId,
    *,
    query_service: TaskQueryService,
    intent: HandoffIntent = HandoffIntent.CONTINUE_WORK,
) -> HandoffRedactionPreview:
    """Preview the currently supported task handoff sections."""

    detail = query_service.get_task_detail(task_id)
    readiness = derive_task_handoff_readiness(detail, intent=intent)
    return task_redaction_preview_from_readiness(detail, readiness=readiness)


def task_redaction_preview_from_readiness(
    detail: TaskDetailView,
    *,
    readiness: HandoffReadiness,
) -> HandoffRedactionPreview:
    local_only_counts = positive_counts(
        {
            "local_only_readiness_reasons": len(readiness.local_only_evidence),
            "verification_artifacts": sum(
                1
                for item in detail.verification_ledger
                if item.latest_artifact_id is not None
            ),
        }
    )
    local_only_summary = HandoffLocalOnlySummary(
        category_counts=local_only_counts,
        limitations=readiness.limitations,
        safe_local_inspection_commands=readiness.safe_first_commands,
    )
    return HandoffRedactionPreview(
        source=readiness.source,
        intent=readiness.intent,
        included_sections=[
            "task",
            "steps",
            "verification_summary",
            "readiness",
            "safe_first_commands",
        ],
        redaction=HandoffRedactionSummary(
            posture=HandoffRedactionPosture.LOCAL_ONLY_OMITTED,
            redacted_field_count=0,
            redacted_categories=[],
            limitations=[
                "task handoff preview currently summarizes readiness sections only"
            ],
        ),
        local_only=local_only_summary,
        local_only_inventory=build_local_only_inventory(
            source=readiness.source,
            intent=readiness.intent,
            summary=local_only_summary,
            omitted_raw_categories=[
                "raw task session transcript",
                "raw verification logs",
                "raw managed artifacts",
            ],
            affected_claim_ids_by_category={
                "verification_artifacts": ["task.verification"],
                "local_only_readiness_reasons": ["task.readiness"],
            },
        ),
        omitted_raw_categories=[
            "raw task session transcript",
            "raw verification logs",
            "raw managed artifacts",
        ],
        unsupported_evidence=[
            "task export packages are not available until recipient profiles land"
        ],
        package_limitations=[
            "task preview is readiness-oriented and does not write a package"
        ],
        safe_inspection_commands=readiness.safe_first_commands,
    )


def workspace_redaction_preview_from_report(
    report: WorkspaceObservabilityReport,
    *,
    intent: HandoffIntent = HandoffIntent.FUTURE_SELF,
) -> HandoffRedactionPreview:
    readiness = derive_workspace_handoff_readiness(report, intent=intent)
    return _observability_preview(
        readiness,
        included_sections=[
            "runtime",
            "projections",
            "operator_queue",
            "repository_intelligence",
            "memory",
            "artifacts",
            "verification",
            "maintenance_cues",
        ],
        omitted_raw_categories=[
            "raw .glassbox database",
            "raw artifacts",
            "raw command logs",
            "raw provider output",
            "screenshots",
        ],
        unsupported_evidence=[],
    )


def release_redaction_preview_from_report(
    report: WorkspaceObservabilityReport,
    *,
    intent: HandoffIntent = HandoffIntent.RELEASE_SIGNOFF,
) -> HandoffRedactionPreview:
    readiness = derive_release_handoff_readiness(report, intent=intent)
    return _observability_preview(
        readiness,
        included_sections=[
            "retained_eval_evidence",
            "release_surface_freshness",
            "package_check_paths",
            "installed_smoke_paths",
            "advisory_provider_evidence",
            "safe_first_commands",
        ],
        omitted_raw_categories=[
            "raw eval logs",
            "raw provider output",
            "raw dashboard evidence",
            "raw browser evidence",
            "raw accessibility evidence",
        ],
        unsupported_evidence=[],
    )


def _observability_preview(
    readiness: HandoffReadiness,
    *,
    included_sections: list[str],
    omitted_raw_categories: list[str],
    unsupported_evidence: list[str],
) -> HandoffRedactionPreview:
    local_only_counts: dict[str, int] = {}
    for reason in readiness.local_only_evidence:
        key = reason.kind.value
        local_only_counts[key] = local_only_counts.get(key, 0) + 1
    local_only_counts = positive_counts(local_only_counts)
    local_only_summary = HandoffLocalOnlySummary(
        category_counts=local_only_counts,
        limitations=readiness.limitations,
        safe_local_inspection_commands=readiness.safe_first_commands,
    )
    return HandoffRedactionPreview(
        source=readiness.source,
        intent=readiness.intent,
        included_sections=included_sections,
        redaction=HandoffRedactionSummary(
            posture=HandoffRedactionPosture.LOCAL_ONLY_OMITTED,
            redacted_field_count=0,
            redacted_categories=[],
            limitations=readiness.limitations,
        ),
        local_only=local_only_summary,
        local_only_inventory=build_readiness_local_only_inventory(readiness)
        if readiness.local_only_evidence
        else build_local_only_inventory(
            source=readiness.source,
            intent=readiness.intent,
            summary=local_only_summary,
            omitted_raw_categories=omitted_raw_categories,
        ),
        omitted_raw_categories=omitted_raw_categories,
        unsupported_evidence=unsupported_evidence,
        package_limitations=[
            "preview summarizes retained local posture and does not write a package"
        ],
        safe_inspection_commands=readiness.safe_first_commands,
    )


__all__ = [
    "HandoffRedactionPreview",
    "_redaction_marker_summary",
    "build_changeset_redaction_preview",
    "build_session_redaction_preview",
    "build_task_redaction_preview",
    "changeset_redaction_preview_from_payload",
    "release_redaction_preview_from_report",
    "session_redaction_preview_from_payload",
    "task_redaction_preview_from_readiness",
    "workspace_redaction_preview_from_report",
]
