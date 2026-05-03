"""Changeset command evidence shaping."""

from glassbox.core import ChangesetRecord
from glassbox.core import ToolAttemptRecord
from glassbox.runtime.changeset_models import ChangesetCommandEvidenceItem
from glassbox.runtime.changeset_models import ChangesetCommandEvidenceSummary
from glassbox.runtime.changeset_repository_contracts import ChangesetRepository


def changeset_command_evidence_summary(
    repository: ChangesetRepository,
    changeset: ChangesetRecord,
) -> ChangesetCommandEvidenceSummary:
    attempts = [
        attempt
        for attempt in repository.list_tool_attempts(changeset.session_id, limit=200)
        if attempt.command_purpose is not None
    ]
    if changeset.task_id is not None:
        relevant = [
            attempt for attempt in attempts if attempt.task_id == changeset.task_id
        ]
        scope = f"task {changeset.task_id}"
    else:
        relevant = attempts
        scope = f"session {changeset.session_id}"
    limitations: list[str] = []
    if not relevant:
        limitations.append(f"no retained command evidence matched {scope}")
    if len(relevant) < len(attempts) and changeset.task_id is not None:
        limitations.append(
            "session has additional command evidence outside this changeset task"
        )
    ordered = sorted(
        relevant,
        key=lambda attempt: (
            not _command_attempt_is_review_critical(attempt),
            -attempt.last_sequence,
        ),
    )
    visible = ordered[:12]
    if len(ordered) > len(visible):
        limitations.append(
            f"{len(ordered) - len(visible)} additional command attempt(s) omitted"
        )
    items = [_command_evidence_item(attempt) for attempt in visible]
    return ChangesetCommandEvidenceSummary(
        total_count=len(relevant),
        verification_count=sum(
            1 for attempt in relevant if attempt.command_supports_verification
        ),
        failed_count=sum(1 for attempt in relevant if attempt.status.value == "failed"),
        risky_count=sum(
            1 for attempt in relevant if _command_attempt_is_risky(attempt)
        ),
        environment_captured_count=sum(
            1 for attempt in relevant if attempt.command_environment is not None
        ),
        artifact_count=sum(
            1 for attempt in relevant if attempt.output_artifact_id is not None
        ),
        items=items,
        limitations=list(dict.fromkeys(limitations)),
        safe_next_actions=[
            (
                "glassbox session tool-attempt inspect "
                f"{item.tool_attempt_id} --session {changeset.session_id} --cwd ."
            )
            for item in items[:5]
        ],
    )


def _command_evidence_item(attempt: ToolAttemptRecord) -> ChangesetCommandEvidenceItem:
    environment = attempt.command_environment
    purpose = (
        attempt.command_purpose.value
        if attempt.command_purpose is not None
        else "unknown"
    )
    relevance = (
        attempt.command_review_relevance.value
        if attempt.command_review_relevance is not None
        else "unknown"
    )
    summary = (
        attempt.message or attempt.command_purpose_reason or "retained command attempt"
    )
    policy_summary = attempt.retry_policy_reason
    return ChangesetCommandEvidenceItem(
        tool_attempt_id=str(attempt.tool_attempt_id),
        turn_id=str(attempt.turn_id),
        task_id=str(attempt.task_id) if attempt.task_id is not None else None,
        tool_name=attempt.tool_name,
        status=attempt.status.value,
        purpose=purpose,
        review_relevance=relevance,
        supports_verification=bool(attempt.command_supports_verification),
        summary=summary,
        output_artifact_id=attempt.output_artifact_id,
        environment_captured=environment is not None,
        toolchain_count=len(environment.toolchains) if environment is not None else 0,
        redaction_notes=environment.redaction_notes if environment is not None else [],
        policy_summary=policy_summary,
        local_only=environment is not None or attempt.output_artifact_id is not None,
    )


def _command_attempt_is_review_critical(attempt: ToolAttemptRecord) -> bool:
    return (
        attempt.status.value == "failed"
        or bool(attempt.command_supports_verification)
        or _command_attempt_is_risky(attempt)
    )


def _command_attempt_is_risky(attempt: ToolAttemptRecord) -> bool:
    purpose = (
        attempt.command_purpose.value if attempt.command_purpose is not None else None
    )
    relevance = (
        attempt.command_review_relevance.value
        if attempt.command_review_relevance is not None
        else None
    )
    return purpose in {"publish", "deploy", "dangerous"} or relevance in {
        "release_or_remote_mutation",
        "cleanup_or_destructive",
    }
