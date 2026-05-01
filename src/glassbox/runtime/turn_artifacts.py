"""Artifact side effects for turn and tool execution."""

import json
from typing import Protocol

from glassbox.core.ids import ArtifactId
from glassbox.core.ids import SessionId
from glassbox.core.ids import TurnId
from glassbox.runtime.context_builder import PYTEST_FAILURE_DIGEST_ARTIFACT_KIND
from glassbox.runtime.context_builder import build_pytest_failure_digest_artifact
from glassbox.services import ArtifactRepository
from glassbox.tools import PreparedToolExecution
from glassbox.tools import ToolExecutionResult
from glassbox.tools.workflow import DIFF_SUMMARY_ARTIFACT_KIND
from glassbox.tools.workflow import diff_summary_artifact_content

TOOL_OUTPUT_ARTIFACT_KIND_PREFIX = "tool_output"
TOOL_OUTPUT_ARTIFACT_SCHEMA_VERSION = 1


class ArtifactEventPublisher(Protocol):
    """Publishes artifact-recorded events after repository writes."""

    def publish(self, event) -> None: ...


def record_context_artifacts_for_tool_execution(
    artifact_repository: ArtifactRepository | None,
    event_bus: ArtifactEventPublisher,
    session_id: SessionId,
    *,
    turn_id: TurnId,
    prepared_tool_call: PreparedToolExecution,
    execution_result: ToolExecutionResult,
) -> None:
    """Record context-builder artifacts derived from a completed tool execution."""

    if artifact_repository is None:
        return
    if prepared_tool_call.tool_name == "workspace_diff_summary":
        diff_summary_content = diff_summary_artifact_content(
            execution_result.output_payload
        )
        if diff_summary_content is None:
            return

        _, stored_event = artifact_repository.record_text_artifact(
            session_id,
            turn_id,
            execution_result.event_tool_call_id,
            DIFF_SUMMARY_ARTIFACT_KIND,
            diff_summary_content,
            suffix="json",
        )
        event_bus.publish(stored_event)
        return

    if prepared_tool_call.tool_name != "run_tests":
        return

    pytest_failure_digest = build_pytest_failure_digest_artifact(
        prepared_tool_call.validated_arguments.model_dump(mode="json"),
        execution_result.output_payload,
    )
    if pytest_failure_digest is None:
        return

    _, stored_event = artifact_repository.record_text_artifact(
        session_id,
        turn_id,
        execution_result.event_tool_call_id,
        PYTEST_FAILURE_DIGEST_ARTIFACT_KIND,
        json.dumps(
            pytest_failure_digest.model_dump(mode="json"),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        suffix="json",
    )
    event_bus.publish(stored_event)


def record_tool_output_artifact_for_tool_execution(
    artifact_repository: ArtifactRepository | None,
    event_bus: ArtifactEventPublisher,
    session_id: SessionId,
    *,
    turn_id: TurnId,
    prepared_tool_call: PreparedToolExecution,
    execution_result: ToolExecutionResult,
) -> ArtifactId | None:
    """Record retained stdout/stderr evidence for command-like tool executions."""

    if artifact_repository is None:
        return None
    artifact_content = tool_output_artifact_content(
        prepared_tool_call.tool_name,
        execution_result.output_payload,
    )
    if artifact_content is None:
        return None
    artifact_kind = tool_output_artifact_kind(artifact_content)
    stored_artifact, stored_event = artifact_repository.record_text_artifact(
        session_id,
        turn_id,
        execution_result.event_tool_call_id,
        artifact_kind,
        json.dumps(artifact_content, indent=2, sort_keys=True) + "\n",
        suffix="log.json",
    )
    event_bus.publish(stored_event)
    return stored_artifact.artifact_id


def tool_output_artifact_content(
    tool_name: str,
    output_payload: dict[str, object],
) -> dict[str, object] | None:
    """Build retained command output evidence for artifact-backed inspection."""

    if tool_name not in {"run_command", "run_tests"}:
        return None
    stdout = output_payload.get("stdout")
    stderr = output_payload.get("stderr")
    if not isinstance(stdout, str) and not isinstance(stderr, str):
        return None

    truncated = output_payload.get("truncated") is True
    timed_out = output_payload.get("timed_out") is True
    cancelled = output_payload.get("cancelled") is True
    output_status = "partial" if timed_out or cancelled or truncated else "final"
    payload: dict[str, object] = {
        "artifact_kind": TOOL_OUTPUT_ARTIFACT_KIND_PREFIX,
        "schema_version": TOOL_OUTPUT_ARTIFACT_SCHEMA_VERSION,
        "tool_name": tool_name,
        "output_status": output_status,
        "truncated": truncated,
        "redacted": False,
        "stdout": stdout if isinstance(stdout, str) else "",
        "stderr": stderr if isinstance(stderr, str) else "",
    }
    for key in (
        "exit_code",
        "timed_out",
        "cancelled",
        "failure_category",
        "termination_signal",
        "execution_envelope",
    ):
        if key in output_payload:
            payload[key] = output_payload[key]
    return payload


def tool_output_artifact_kind(artifact_content: dict[str, object]) -> str:
    """Return the retained tool-output artifact kind for one artifact payload."""

    output_status = artifact_content.get("output_status")
    truncated = artifact_content.get("truncated") is True
    redacted = artifact_content.get("redacted") is True
    status_suffix = output_status if isinstance(output_status, str) else "unknown"
    truncation_suffix = "truncated" if truncated else "complete"
    redaction_suffix = "redacted" if redacted else "unredacted"
    return (
        f"{TOOL_OUTPUT_ARTIFACT_KIND_PREFIX}_{status_suffix}_"
        f"{truncation_suffix}_{redaction_suffix}"
    )


__all__ = [
    "TOOL_OUTPUT_ARTIFACT_KIND_PREFIX",
    "TOOL_OUTPUT_ARTIFACT_SCHEMA_VERSION",
    "record_context_artifacts_for_tool_execution",
    "record_tool_output_artifact_for_tool_execution",
    "tool_output_artifact_content",
    "tool_output_artifact_kind",
]
