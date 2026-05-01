"""Output artifact helpers for durable tool-attempt recovery."""

import json
from pathlib import Path

from glassbox.core.events import ToolArtifactRecorded
from glassbox.core.ids import ArtifactId
from glassbox.core.ids import SessionId
from glassbox.core.ids import ToolAttemptId
from glassbox.core.ids import ToolCallId
from glassbox.core.models import ToolAttemptRecord
from glassbox.runtime.tool_attempt_recovery_common import require_attempt
from glassbox.runtime.tool_attempt_recovery_models import ToolAttemptArtifactReference
from glassbox.runtime.tool_attempt_recovery_models import ToolAttemptRecoveryError
from glassbox.runtime.turn_artifacts import tool_output_artifact_content
from glassbox.runtime.turn_artifacts import tool_output_artifact_kind
from glassbox.services import ArtifactRepository
from glassbox.services import SessionRepository


def read_tool_attempt_output(
    repository: SessionRepository,
    artifact_repository: ArtifactRepository,
    session_id: SessionId,
    tool_attempt_id: ToolAttemptId,
) -> tuple[ToolAttemptArtifactReference, str]:
    """Read retained output artifact content for one attempt."""

    attempt = require_attempt(repository, session_id, tool_attempt_id)
    artifact = artifact_reference(repository, session_id, attempt.output_artifact_id)
    if artifact is None or artifact.path is None:
        raise ToolAttemptRecoveryError(
            f"attempt {tool_attempt_id} has no retained output artifact"
        )
    return artifact, artifact_repository.read_text_artifact(Path(artifact.path))


def artifact_reference(
    repository: SessionRepository,
    session_id: SessionId,
    artifact_id: ArtifactId | None,
) -> ToolAttemptArtifactReference | None:
    """Return retained output artifact metadata from canonical events."""

    if artifact_id is None:
        return None
    for event in repository.read_session_events(session_id):
        payload = event.payload
        if (
            isinstance(payload, ToolArtifactRecorded)
            and payload.artifact_id == artifact_id
        ):
            return ToolAttemptArtifactReference(
                artifact_id=payload.artifact_id,
                artifact_kind=payload.artifact_kind,
                path=payload.path,
                content_sha256=payload.content_sha256,
                size_bytes=payload.size_bytes,
            )
    return ToolAttemptArtifactReference(
        artifact_id=artifact_id,
        artifact_kind="unknown",
    )


def record_retry_output_artifact(
    artifact_repository: ArtifactRepository | None,
    session_id: SessionId,
    original: ToolAttemptRecord,
    tool_call_id: ToolCallId,
    tool_name: str,
    output_payload: dict[str, object],
) -> ArtifactId | None:
    """Persist retry output evidence when the execution result has artifact content."""

    if artifact_repository is None:
        return None
    artifact_content = tool_output_artifact_content(tool_name, output_payload)
    if artifact_content is None:
        return None
    stored_artifact, _stored_event = artifact_repository.record_text_artifact(
        session_id,
        original.turn_id,
        tool_call_id,
        tool_output_artifact_kind(artifact_content),
        json.dumps(artifact_content, indent=2, sort_keys=True) + "\n",
        suffix="log.json",
    )
    return stored_artifact.artifact_id


__all__ = [
    "artifact_reference",
    "read_tool_attempt_output",
    "record_retry_output_artifact",
]
