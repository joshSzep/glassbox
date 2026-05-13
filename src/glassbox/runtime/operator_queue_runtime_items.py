"""Runtime-owner rows for the unified operator queue."""

from glassbox.core import NextActionEvidenceKind
from glassbox.core import NextActionKind
from glassbox.core import NextActionPriority
from glassbox.core import NextActionSeverity
from glassbox.core import NextActionTarget
from glassbox.core import NextActionTargetKind
from glassbox.core import OperatorQueueDismissalPolicy
from glassbox.core import OperatorQueueFamily
from glassbox.core import OperatorQueueItem
from glassbox.core import OperatorQueueState
from glassbox.runtime.operator_queue_items import operator_queue_item
from glassbox.runtime.session_query_models import WorkspaceRuntimeSummaryView


def build_runtime_queue_items(
    runtime: WorkspaceRuntimeSummaryView,
) -> list[OperatorQueueItem]:
    """Build fallback workspace-runtime rows when no maintenance cues exist."""

    target = NextActionTarget(
        kind=NextActionTargetKind.WORKSPACE,
        target_id=runtime.workspace_root,
        label="Workspace runtime",
    )
    items: list[OperatorQueueItem] = []
    if runtime.background_job_failed_count:
        items.append(
            _runtime_item(
                target,
                runtime,
                item_id="queue:workspace:background-jobs:failed",
                state=OperatorQueueState.BLOCKED,
                priority=NextActionPriority.ACTION_NEEDED,
                severity=NextActionSeverity.HIGH,
                title="Inspect failed background jobs",
                summary=(
                    f"{runtime.background_job_failed_count} background job(s) failed."
                ),
                dedupe_key="maintenance:workspace:background-jobs:failed",
            )
        )
    if runtime.background_job_retryable_count:
        items.append(
            _runtime_item(
                target,
                runtime,
                item_id="queue:workspace:background-jobs:retryable",
                state=OperatorQueueState.ACTION_NEEDED,
                priority=NextActionPriority.ACTION_NEEDED,
                severity=NextActionSeverity.MEDIUM,
                title="Inspect retryable background jobs",
                summary=(
                    f"{runtime.background_job_retryable_count} background job(s) "
                    "can be retried."
                ),
                dedupe_key="maintenance:workspace:background-jobs:retryable",
            )
        )
    return items


def _runtime_item(
    target: NextActionTarget,
    runtime: WorkspaceRuntimeSummaryView,
    *,
    item_id: str,
    state: OperatorQueueState,
    priority: NextActionPriority,
    severity: NextActionSeverity,
    title: str,
    summary: str,
    dedupe_key: str,
) -> OperatorQueueItem:
    return operator_queue_item(
        item_id=item_id,
        family=OperatorQueueFamily.MAINTENANCE,
        state=state,
        priority=priority,
        severity=severity,
        target=target,
        owner_label="Background jobs",
        action_kind=NextActionKind.INSPECT,
        action_title=title,
        action_summary=summary,
        evidence_kind=NextActionEvidenceKind.BACKGROUND_JOB,
        evidence_id=runtime.workspace_root,
        evidence_summary=summary,
        dedupe_key=dedupe_key,
        dismissal_policy=OperatorQueueDismissalPolicy.NOT_DISMISSIBLE,
        action_needed=True,
    )


__all__ = ["build_runtime_queue_items"]
