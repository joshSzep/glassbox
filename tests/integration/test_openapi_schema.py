"""Integration checks for the exported FastAPI OpenAPI schema."""

import json
from typing import Any

import pytest

from glassbox.web.openapi_schema import build_openapi_schema


@pytest.fixture(scope="module")
def openapi_schema() -> dict[str, Any]:
    return build_openapi_schema()


def test_openapi_schema_export_is_deterministic() -> None:
    first = build_openapi_schema()
    second = build_openapi_schema()

    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_openapi_schema_includes_browser_transport_contracts(
    openapi_schema: dict[str, Any],
) -> None:
    schema = openapi_schema
    paths = schema["paths"]
    components = schema["components"]["schemas"]

    assert "/healthz" in paths
    assert "/sessions" in paths
    assert "/sessions/aggregate" in paths
    assert "/sessions/{session_id}" in paths
    assert "/sessions/{session_id}/checkpoints" in paths
    assert "/sessions/{session_id}/events" in paths
    assert "/sessions/{session_id}/messages" in paths
    assert "/sessions/{session_id}/questions/{question_id}" in paths
    assert "/sessions/{session_id}/approvals/{approval_id}" in paths
    assert "/sessions/{session_id}/fork" in paths
    assert "/tasks" in paths
    assert "/tasks/{task_id}" in paths
    assert "/tasks/{task_id}/steps" in paths
    assert "/tasks/{task_id}/events" in paths
    assert "/changesets" in paths
    assert "/changesets/{changeset_id}" in paths
    assert "/changesets/{changeset_id}/refresh" in paths
    assert "/changesets/{changeset_id}/commit-readiness" in paths
    assert "/changesets/{changeset_id}/commit-message" in paths
    assert "/changesets/{changeset_id}/archive" in paths
    assert "/memory" in paths
    assert "/memory/candidates" in paths
    assert "/memory/candidates/{candidate_id}/confirm" in paths
    assert "/memory/candidates/{candidate_id}/reject" in paths
    assert "/memory/{memory_id}" in paths
    assert "/repo/index/status" in paths
    assert "/repo/index/search" in paths
    assert "/repo/index/entries/{entry_id}" in paths
    assert "/repo/intelligence" in paths
    assert "/repo/intelligence/freshness" in paths
    assert "/repo/intelligence/paths/{path}" in paths
    assert "/repo/intelligence/command-recipes" in paths
    assert "/repo/intelligence/command-recipes/{recipe_id}" in paths
    assert "/repo/intelligence/subsystems" in paths
    assert "/repo/intelligence/subsystems/{subsystem_id}" in paths
    assert "/repo/intelligence/verification" in paths
    assert "/repo/intelligence/memory-candidates" in paths
    assert "/repo/intelligence/search" in paths

    assert "HealthResponse" in components
    assert "SessionAggregateResponse" in components
    assert "WorkspaceKnowledgePosture" in components
    assert "KnowledgePostureCue" in components
    assert "KnowledgeCueProvenance" in components
    assert "KnowledgeCueSourceKind" in components
    assert "SessionCheckpointPageResponse" in components
    assert "SessionSnapshotResponse" in components
    assert "TaskCheckpointResponse" in components
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
    assert "ChangesetListPageResponse" in components
    assert "ChangesetDetailResponse" in components
    assert "ChangesetActionResponse" in components
    assert "CommitReadinessResponse" in components
    assert "CommitMessageSuggestionResponse" in components
    assert "WorkspaceMemoryListPageResponse" in components
    assert "WorkspaceMemoryDetailResponse" in components
    assert "WorkspaceMemoryCandidateListPageResponse" in components
    assert "WorkspaceMemoryCandidateRejectedResponse" in components
    assert "WorkspaceMemoryAddRequest" in components
    assert "RepositoryIndexStatusResponse" in components
    assert "RepositoryIndexSearchPageResponse" in components
    assert "RepositoryIndexEntryDetailResponse" in components
    assert "RepositoryIntelligenceOverviewResponse" in components
    assert "RepositoryIntelligencePathInspectionResponse" in components
    assert "RepositoryIntelligenceCommandRecipeListPageResponse" in components
    assert "RepositoryIntelligenceSubsystemDetailResponse" in components
    assert "RepositoryIntelligenceVerificationRecommendationResponse" in components
    assert "RepositoryIndexContextSnapshot" in components
    assert "WorkspaceMemoryContextItemSnapshot" in components
    assert "ErrorDetailResponse" in components
    assert "HTTPValidationError" in components
    assert (
        components["SessionAggregateResponse"]["properties"]["knowledge_posture"][
            "anyOf"
        ][0]["$ref"]
        == "#/components/schemas/WorkspaceKnowledgePosture"
    )
    assert (
        components["KnowledgePostureCue"]["properties"]["provenance"]["items"]["$ref"]
        == "#/components/schemas/KnowledgeCueProvenance"
    )


def test_openapi_schema_documents_action_error_responses(
    openapi_schema: dict[str, Any],
) -> None:
    schema = openapi_schema
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
