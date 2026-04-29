"""Event recording helpers for background job workers."""

import traceback
from contextlib import suppress

from glassbox.core.events import BackgroundJobFailed
from glassbox.core.events import BackgroundJobProgressRecorded
from glassbox.core.events import EventEnvelope
from glassbox.core.models import BackgroundJobRecord
from glassbox.core.types import BackgroundJobFailureKind
from glassbox.core.types import BackgroundJobKind
from glassbox.runtime.context import RuntimeContext


def record_background_job_progress(
    runtime_context: RuntimeContext,
    job: BackgroundJobRecord,
    message: str,
) -> None:
    """Record a progress update for a claimed background job."""

    runtime_context.repositories.sessions.append_event(
        EventEnvelope(
            session_id=job.session_id,
            sequence=0,
            payload=BackgroundJobProgressRecorded(
                job_id=job.job_id,
                message=message,
            ),
        )
    )


def fail_background_job(
    runtime_context: RuntimeContext,
    job: BackgroundJobRecord,
    exc: Exception,
) -> None:
    """Record a background job failure and best-effort traceback artifact."""

    failure_artifact_id = None
    failure_artifact_path = None
    with suppress(Exception):
        artifact = runtime_context.repositories.artifacts.write_text_artifact(
            job.session_id,
            _failure_artifact_content(job, exc),
            suffix="background-job-failure.txt",
        )
        failure_artifact_id = artifact.artifact_id
        failure_artifact_path = artifact.relative_path.as_posix()
    runtime_context.repositories.sessions.append_event(
        EventEnvelope(
            session_id=job.session_id,
            sequence=0,
            payload=BackgroundJobFailed(
                job_id=job.job_id,
                failure_kind=BackgroundJobFailureKind.TOOL_ERROR,
                message=str(exc),
                retryable=job.kind != BackgroundJobKind.MUTATING_CONTINUATION,
                attempt=max(job.attempt, 1),
                artifact_id=failure_artifact_id,
                artifact_path=failure_artifact_path,
            ),
        )
    )


def _failure_artifact_content(job: BackgroundJobRecord, exc: Exception) -> str:
    traceback_text = "".join(
        traceback.format_exception(type(exc), exc, exc.__traceback__)
    )
    return (
        f"Background job failure\n"
        f"job_id: {job.job_id}\n"
        f"session_id: {job.session_id}\n"
        f"kind: {job.kind.value}\n"
        f"job_type: {job.job_type}\n"
        f"attempt: {max(job.attempt, 1)}\n"
        f"failure_kind: {BackgroundJobFailureKind.TOOL_ERROR.value}\n\n"
        f"{traceback_text}"
    )


__all__ = [
    "fail_background_job",
    "record_background_job_progress",
]
