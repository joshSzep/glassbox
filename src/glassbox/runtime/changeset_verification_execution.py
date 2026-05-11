"""Selected changeset verification command execution helpers."""

import asyncio
import shlex
from pathlib import Path
from typing import cast

from glassbox.core import ArtifactId
from glassbox.core import ChangesetRecord
from glassbox.core import EventEnvelope
from glassbox.core import TaskId
from glassbox.core import TaskVerificationCompleted
from glassbox.core import TaskVerificationFailed
from glassbox.core import TaskVerificationStarted
from glassbox.core import TaskVerificationStatus
from glassbox.core import TaskVerificationStreamed
from glassbox.core import ToolAttemptHeartbeat
from glassbox.core import ToolAttemptId
from glassbox.core import ToolAttemptRetryClassification
from glassbox.core import ToolAttemptStatus
from glassbox.core import ToolCallId
from glassbox.core import TurnId
from glassbox.core import VerificationFailureCategory
from glassbox.core import VerificationFailureDigest
from glassbox.core import VerificationPlanEntry
from glassbox.core import new_tool_attempt_id
from glassbox.core import new_tool_call_id
from glassbox.core import new_turn_id
from glassbox.core.events import ToolOutputStream
from glassbox.runtime.changeset_models import ChangesetVerificationPlanExecutionResult
from glassbox.runtime.changeset_repository_contracts import ChangesetRepository
from glassbox.runtime.command_evidence import capture_command_environment
from glassbox.runtime.command_evidence import classify_command_purpose
from glassbox.runtime.verification import classify_verification_failure
from glassbox.services import ArtifactRepository
from glassbox.tools.command import RunCommandArgs
from glassbox.tools.command import RunCommandTool
from glassbox.tools.policy_command_risk import CommandRiskAssessment
from glassbox.tools.policy_command_risk import blocked_command_risk


def run_selected_verification_command(
    repository: ChangesetRepository,
    artifact_repository: ArtifactRepository | None,
    changeset: ChangesetRecord,
    entry: VerificationPlanEntry,
    *,
    workspace_root: Path,
) -> ChangesetVerificationPlanExecutionResult:
    """Run one selected verification command and return the persisted result."""

    if changeset.task_id is None:
        raise ValueError(
            "verification command execution requires a task-backed changeset"
        )
    if not entry.command:
        raise ValueError("selected verification entry does not have a command")

    command = shlex.join(entry.command)
    risk = blocked_command_risk(command)
    if risk is not None:
        events = _append_policy_blocked_events(
            repository,
            changeset,
            entry,
            command=command,
            risk=risk,
        )
        return _execution_result(
            changeset,
            entry=entry,
            status="policy_blocked",
            events=events,
        )

    events, exit_code, timed_out, artifact_id = asyncio.run(
        _execute_selected_entry(
            repository,
            artifact_repository,
            changeset,
            entry,
            workspace_root=workspace_root,
            command=command,
        )
    )
    status = (
        "passed"
        if exit_code in entry.expected_exit_codes and not timed_out
        else "failed"
    )
    if timed_out:
        status = "timed_out"
    return _execution_result(
        changeset,
        entry=entry,
        status=status,
        events=events,
        exit_code=exit_code,
        timed_out=timed_out,
        output_artifact_id=artifact_id,
    )


def _append_policy_blocked_events(
    repository: ChangesetRepository,
    changeset: ChangesetRecord,
    entry: VerificationPlanEntry,
    *,
    command: str,
    risk: CommandRiskAssessment,
) -> list[EventEnvelope]:
    task_id = _require_task_id(changeset)
    failure = VerificationFailureDigest(
        category=VerificationFailureCategory.POLICY,
        summary=risk.reason,
    )
    tool_attempt_id = new_tool_attempt_id()
    tool_call_id = new_tool_call_id()
    turn_id = new_turn_id()
    return repository.append_events(
        [
            EventEnvelope(
                session_id=changeset.session_id,
                sequence=0,
                payload=_tool_attempt_heartbeat(
                    entry,
                    command=command,
                    status=ToolAttemptStatus.FAILED,
                    tool_attempt_id=tool_attempt_id,
                    tool_call_id=tool_call_id,
                    turn_id=turn_id,
                    task_id=task_id,
                    message=risk.reason,
                    retry_policy_reason=risk.source_label,
                ),
            ),
            EventEnvelope(
                session_id=changeset.session_id,
                sequence=0,
                payload=TaskVerificationFailed(
                    task_id=task_id,
                    verification_id=entry.verification_id,
                    failure=failure,
                ),
            ),
        ]
    )


async def _execute_selected_entry(
    repository: ChangesetRepository,
    artifact_repository: ArtifactRepository | None,
    changeset: ChangesetRecord,
    entry: VerificationPlanEntry,
    *,
    workspace_root: Path,
    command: str,
) -> tuple[list[EventEnvelope], int | None, bool, ArtifactId | None]:
    task_id = _require_task_id(changeset)
    tool_attempt_id = new_tool_attempt_id()
    tool_call_id = new_tool_call_id()
    turn_id = new_turn_id()
    output_chunks: list[str] = []
    pending_events: list[EventEnvelope] = [
        EventEnvelope(
            session_id=changeset.session_id,
            sequence=0,
            payload=_tool_attempt_heartbeat(
                entry,
                command=command,
                status=ToolAttemptStatus.STARTED,
                tool_attempt_id=tool_attempt_id,
                tool_call_id=tool_call_id,
                turn_id=turn_id,
                task_id=task_id,
                message="verification command selected",
            ),
        ),
        EventEnvelope(
            session_id=changeset.session_id,
            sequence=0,
            payload=TaskVerificationStarted(
                task_id=task_id,
                verification_id=entry.verification_id,
                check_name=entry.check_name,
            ),
        ),
        EventEnvelope(
            session_id=changeset.session_id,
            sequence=0,
            payload=_tool_attempt_heartbeat(
                entry,
                command=command,
                status=ToolAttemptStatus.RUNNING,
                tool_attempt_id=tool_attempt_id,
                tool_call_id=tool_call_id,
                turn_id=turn_id,
                task_id=task_id,
                message="verification command running",
            ),
        ),
    ]

    def on_chunk(stream: str, chunk: str) -> None:
        output_chunks.append(chunk)
        pending_events.append(
            EventEnvelope(
                session_id=changeset.session_id,
                sequence=0,
                payload=TaskVerificationStreamed(
                    task_id=task_id,
                    verification_id=entry.verification_id,
                    stream=cast(ToolOutputStream, stream),
                    chunk_summary=chunk.strip()[:2000] or f"{stream} output",
                ),
            )
        )

    result = await RunCommandTool(workspace_root).execute_streaming(
        RunCommandArgs(
            command=command,
            timeout=min(entry.timeout_seconds, 300),
        ),
        on_chunk,
    )
    output = "\n".join(part for part in [result.stdout, result.stderr] if part)
    if not output and output_chunks:
        output = "\n".join(output_chunks)
    artifact = (
        artifact_repository.write_text_artifact(
            changeset.session_id,
            output or f"{entry.check_name} produced no output\n",
            suffix=".verification-output.txt",
        )
        if artifact_repository is not None
        else None
    )
    artifact_id = artifact.artifact_id if artifact is not None else None
    passed = result.exit_code in entry.expected_exit_codes and not result.timed_out
    if passed:
        pending_events.append(
            EventEnvelope(
                session_id=changeset.session_id,
                sequence=0,
                payload=TaskVerificationCompleted(
                    task_id=task_id,
                    verification_id=entry.verification_id,
                    status=TaskVerificationStatus.PASSED,
                    summary=f"{entry.check_name} passed",
                    artifact_id=artifact_id,
                ),
            )
        )
    else:
        failure = classify_verification_failure(
            output,
            exit_code=result.exit_code,
            timed_out=result.timed_out,
        )
        if artifact_id is not None:
            failure = failure.model_copy(update={"artifact_id": artifact_id})
        pending_events.append(
            EventEnvelope(
                session_id=changeset.session_id,
                sequence=0,
                payload=TaskVerificationFailed(
                    task_id=task_id,
                    verification_id=entry.verification_id,
                    failure=failure,
                ),
            )
        )
    pending_events.append(
        EventEnvelope(
            session_id=changeset.session_id,
            sequence=0,
            payload=_tool_attempt_heartbeat(
                entry,
                command=command,
                status=ToolAttemptStatus.SUCCEEDED
                if passed
                else ToolAttemptStatus.FAILED,
                tool_attempt_id=tool_attempt_id,
                tool_call_id=tool_call_id,
                turn_id=turn_id,
                task_id=task_id,
                message=(
                    "verification command passed"
                    if passed
                    else "verification command failed"
                ),
                output_artifact_id=artifact_id,
            ),
        )
    )
    stored = repository.append_events(pending_events)
    return stored, result.exit_code, result.timed_out, artifact_id


def _tool_attempt_heartbeat(
    entry: VerificationPlanEntry,
    *,
    command: str,
    status: ToolAttemptStatus,
    tool_attempt_id: ToolAttemptId,
    tool_call_id: ToolCallId,
    turn_id: TurnId,
    task_id: TaskId,
    message: str,
    output_artifact_id: ArtifactId | None = None,
    retry_policy_reason: str | None = None,
) -> ToolAttemptHeartbeat:
    command_assessment = classify_command_purpose(command)
    retry_classification = ToolAttemptRetryClassification.UNKNOWN
    retry_requires_approval = entry.execution_requires_approval
    retry_reason = "retry requires operator inspection and explicit confirmation"
    safe_to_retry = status == ToolAttemptStatus.FAILED
    if status in {ToolAttemptStatus.STARTED, ToolAttemptStatus.RUNNING}:
        retry_classification = ToolAttemptRetryClassification.ALREADY_RUNNING
        retry_requires_approval = False
        retry_reason = "verification command is already running"
        safe_to_retry = False
    elif status == ToolAttemptStatus.SUCCEEDED:
        retry_classification = ToolAttemptRetryClassification.UNSAFE_TO_RETRY
        retry_requires_approval = False
        retry_reason = (
            "successful verification should not be retried without a new "
            "selected verification reason"
        )
        safe_to_retry = False
    elif status == ToolAttemptStatus.FAILED:
        retry_classification = ToolAttemptRetryClassification.RETRYABLE
    return ToolAttemptHeartbeat(
        tool_attempt_id=tool_attempt_id,
        status=status,
        turn_id=turn_id,
        tool_call_id=tool_call_id,
        task_id=task_id,
        tool_name="run_command",
        message=message,
        output_artifact_id=output_artifact_id,
        safe_to_retry=safe_to_retry,
        command_purpose=command_assessment.purpose,
        command_review_relevance=command_assessment.review_relevance,
        command_supports_verification=command_assessment.supports_verification,
        command_purpose_reason=command_assessment.reason,
        command_environment=capture_command_environment(
            command=command,
            assessment=command_assessment,
        ),
        retry_classification=retry_classification,
        retry_requires_approval=retry_requires_approval,
        retry_reason=retry_reason,
        retry_policy_reason=retry_policy_reason,
    )


def _execution_result(
    changeset: ChangesetRecord,
    *,
    entry: VerificationPlanEntry,
    status: str,
    events: list[EventEnvelope],
    exit_code: int | None = None,
    timed_out: bool = False,
    output_artifact_id: ArtifactId | None = None,
) -> ChangesetVerificationPlanExecutionResult:
    task_id = _require_task_id(changeset)
    return ChangesetVerificationPlanExecutionResult(
        changeset_id=changeset.changeset_id,
        session_id=changeset.session_id,
        task_id=task_id,
        verification_id=entry.verification_id,
        check_name=entry.check_name,
        status=status,
        command=entry.command,
        exit_code=exit_code,
        timed_out=timed_out,
        output_artifact_id=output_artifact_id,
        events=events,
        safe_next_actions=[
            f"glassbox changeset verification-plan {changeset.changeset_id} --cwd .",
            f"glassbox changeset show {changeset.changeset_id} --cwd .",
        ],
        non_claims=[
            "verification-run only runs explicitly selected local commands",
            "passing verification is local evidence, not reviewer approval",
            "publication remains outside verification plan execution",
        ],
    )


def _require_task_id(changeset: ChangesetRecord) -> TaskId:
    if changeset.task_id is None:
        raise ValueError("verification command execution requires task id")
    return changeset.task_id


__all__ = ["run_selected_verification_command"]
