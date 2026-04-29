"""Integration checks for the exported FastAPI OpenAPI schema."""

import json

from glassbox.web.openapi_schema import build_openapi_schema


def test_openapi_schema_export_is_deterministic() -> None:
    first = build_openapi_schema()
    second = build_openapi_schema()

    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_openapi_schema_includes_browser_transport_contracts() -> None:
    schema = build_openapi_schema()
    paths = schema["paths"]
    components = schema["components"]["schemas"]

    assert "/healthz" in paths
    assert "/sessions" in paths
    assert "/sessions/aggregate" in paths
    assert "/sessions/{session_id}" in paths
    assert "/sessions/{session_id}/events" in paths
    assert "/sessions/{session_id}/messages" in paths
    assert "/sessions/{session_id}/questions/{question_id}" in paths
    assert "/sessions/{session_id}/approvals/{approval_id}" in paths
    assert "/sessions/{session_id}/fork" in paths
    assert "/tasks" in paths
    assert "/tasks/{task_id}" in paths
    assert "/tasks/{task_id}/steps" in paths
    assert "/tasks/{task_id}/events" in paths
    assert "/memory" in paths
    assert "/memory/{memory_id}" in paths

    assert "HealthResponse" in components
    assert "SessionAggregateResponse" in components
    assert "SessionSnapshotResponse" in components
    assert "ActionAcceptedResponse" in components
    assert "ResolveApprovalRequest" in components
    assert "SubmitSessionMessageRequest" in components
    assert "SubmitSessionAnswerRequest" in components
    assert "ForkSessionRequest" in components
    assert "ForkSessionResponse" in components
    assert "TaskListPageResponse" in components
    assert "TaskDetailResponse" in components
    assert "TaskStepPageResponse" in components
    assert "TaskEventPageResponse" in components
    assert "WorkspaceMemoryListPageResponse" in components
    assert "WorkspaceMemoryDetailResponse" in components
    assert "ErrorDetailResponse" in components
    assert "HTTPValidationError" in components


def test_openapi_schema_documents_action_error_responses() -> None:
    schema = build_openapi_schema()
    approval_responses = schema["paths"][
        "/sessions/{session_id}/approvals/{approval_id}"
    ]["post"]["responses"]

    assert approval_responses["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ActionAcceptedResponse"
    }
    assert approval_responses["404"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ErrorDetailResponse"
    }
    assert approval_responses["409"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ErrorDetailResponse"
    }
