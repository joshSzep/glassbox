"""Changeset dashboard API routes."""

from typing import Annotated
from typing import cast
from uuid import UUID

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Query

from glassbox.runtime.changesets import ChangesetActionService
from glassbox.runtime.changesets import ChangesetDerivationService
from glassbox.runtime.changesets import ChangesetQueryService
from glassbox.runtime.changesets import ChangesetRepository
from glassbox.runtime.changesets import ChangesetReviewBriefService
from glassbox.runtime.changesets import ChangesetVerificationService
from glassbox.runtime.commit_messages import ChangesetCommitMessageSuggestionService
from glassbox.web.app import RuntimeContextDep
from glassbox.web.changeset_api import ChangesetActionResponse
from glassbox.web.changeset_api import ChangesetArchiveRequest
from glassbox.web.changeset_api import ChangesetCreateRequest
from glassbox.web.changeset_api import ChangesetCreateResponse
from glassbox.web.changeset_api import ChangesetDetailResponse
from glassbox.web.changeset_api import ChangesetListPageResponse
from glassbox.web.changeset_api import ChangesetRecordVerificationRequest
from glassbox.web.changeset_api import ChangesetRecordVerificationResponse
from glassbox.web.changeset_api import ChangesetRefreshRequest
from glassbox.web.changeset_api import ChangesetReviewBriefGenerateResponse
from glassbox.web.changeset_api import ChangesetReviewBriefRequest
from glassbox.web.changeset_api import ChangesetVerificationPlanPreviewResponse
from glassbox.web.changeset_api import CommitMessageSuggestionResponse
from glassbox.web.changeset_api import build_changeset_detail_response
from glassbox.web.changeset_api import build_changeset_review_brief_generate_response
from glassbox.web.changeset_api import build_changeset_summary_responses
from glassbox.web.changeset_api import build_changeset_verification_plan_response
from glassbox.web.changeset_api import build_changeset_verification_readiness_response
from glassbox.web.changeset_api import build_commit_message_suggestion_response
from glassbox.web.session_api import ErrorDetailResponse

router = APIRouter(prefix="/changesets")

LimitParam = Annotated[int | None, Query(ge=1, le=200)]


def _repository(context: RuntimeContextDep) -> ChangesetRepository:
    return cast(ChangesetRepository, context.repositories.sessions)


@router.get("", response_model=ChangesetListPageResponse)
async def list_changesets(
    context: RuntimeContextDep,
    session_id: UUID | None = None,
    include_archived: bool = False,
    limit: LimitParam = 100,
) -> ChangesetListPageResponse:
    """Return recent changesets for dashboard inspection."""

    changesets = ChangesetQueryService(_repository(context)).list_changesets(
        session_id=session_id,
        include_archived=include_archived,
        limit=limit,
    )
    return ChangesetListPageResponse(
        items=build_changeset_summary_responses(changesets)
    )


@router.post("", response_model=ChangesetCreateResponse)
async def create_changeset(
    request: ChangesetCreateRequest,
    context: RuntimeContextDep,
) -> ChangesetCreateResponse:
    """Create an explicit local changeset from retained evidence."""

    service = ChangesetDerivationService(_repository(context))
    try:
        if request.source_kind == "session":
            if request.session_id is None:
                raise ValueError("session_id is required for source_kind=session")
            result = service.create_from_session(
                UUID(request.session_id),
                objective=request.objective,
            )
        elif request.source_kind == "task":
            if request.task_id is None:
                raise ValueError("task_id is required for source_kind=task")
            result = service.create_from_task(
                UUID(request.task_id),
                objective=request.objective,
            )
        elif request.source_kind == "branch-candidate":
            if request.branch_search_id is None or request.candidate_id is None:
                raise ValueError(
                    "branch_search_id and candidate_id are required for "
                    "source_kind=branch-candidate"
                )
            result = service.create_from_branch_candidate(
                UUID(request.branch_search_id),
                UUID(request.candidate_id),
                objective=request.objective,
            )
        else:
            if request.session_id is None:
                raise ValueError(
                    "session_id is required for source_kind=workspace-diff"
                )
            result = service.create_from_workspace_diff(
                UUID(request.session_id),
                _workspace_root_for_session(
                    repository=_repository(context),
                    session_id=UUID(request.session_id),
                ),
                objective=request.objective,
            )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ChangesetCreateResponse(
        changeset_id=str(result.changeset_id),
        session_id=str(result.session_id),
        limitations=result.limitations,
        event_count=len(result.stored_events),
    )


@router.get(
    "/{changeset_id}",
    response_model=ChangesetDetailResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def get_changeset_detail(
    changeset_id: UUID,
    context: RuntimeContextDep,
) -> ChangesetDetailResponse:
    """Return one changeset with source and evidence references."""

    repository = _repository(context)
    try:
        detail = ChangesetQueryService(repository).get_detail(
            changeset_id,
            workspace_root=_workspace_root_for_changeset(repository, changeset_id),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return build_changeset_detail_response(detail)


@router.post(
    "/{changeset_id}/refresh",
    response_model=ChangesetActionResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def refresh_changeset(
    changeset_id: UUID,
    request: ChangesetRefreshRequest,
    context: RuntimeContextDep,
) -> ChangesetActionResponse:
    """Refresh structured inventory evidence for a changeset."""

    repository = _repository(context)
    try:
        result = await ChangesetActionService(
            repository,
            context.repositories.artifacts,
        ).refresh_inventory(
            changeset_id,
            _workspace_root_for_changeset(repository, changeset_id),
            refreshed_by=request.actor,
        )
        detail = ChangesetQueryService(repository).get_detail(
            changeset_id,
            workspace_root=_workspace_root_for_changeset(repository, changeset_id),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ChangesetActionResponse(
        changeset_id=str(changeset_id),
        status="refreshed",
        event_sequence=result.event.sequence,
        detail=build_changeset_detail_response(detail),
    )


@router.get(
    "/{changeset_id}/verification-plan",
    response_model=ChangesetVerificationPlanPreviewResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def preview_changeset_verification_plan(
    changeset_id: UUID,
    context: RuntimeContextDep,
) -> ChangesetVerificationPlanPreviewResponse:
    """Preview verification commands and retained evidence for a changeset."""

    repository = _repository(context)
    try:
        preview = ChangesetVerificationService(
            repository,
            context.repositories.artifacts,
        ).preview_plan(
            changeset_id,
            _workspace_root_for_changeset(repository, changeset_id),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return build_changeset_verification_plan_response(preview)


@router.post(
    "/{changeset_id}/record-verification",
    response_model=ChangesetRecordVerificationResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def record_changeset_verification(
    changeset_id: UUID,
    request: ChangesetRecordVerificationRequest,
    context: RuntimeContextDep,
) -> ChangesetRecordVerificationResponse:
    """Record changeset verification posture from existing task evidence."""

    repository = _repository(context)
    try:
        result = ChangesetVerificationService(
            repository,
            context.repositories.artifacts,
        ).record_existing_evidence(
            changeset_id,
            _workspace_root_for_changeset(repository, changeset_id),
            task_id=UUID(request.task_id) if request.task_id is not None else None,
            verification_id=(
                UUID(request.verification_id)
                if request.verification_id is not None
                else None
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ChangesetRecordVerificationResponse(
        changeset_id=str(result.changeset_id),
        session_id=str(result.session_id),
        selected_verification_ids=[
            str(verification_id) for verification_id in result.selected_verification_ids
        ],
        retained_artifact_ids=[
            str(artifact_id) for artifact_id in result.retained_artifact_ids
        ],
        readiness=build_changeset_verification_readiness_response(result.readiness),
        event_sequence=result.event.sequence,
    )


@router.post(
    "/{changeset_id}/brief",
    response_model=ChangesetReviewBriefGenerateResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def generate_changeset_review_brief(
    changeset_id: UUID,
    request: ChangesetReviewBriefRequest,
    context: RuntimeContextDep,
) -> ChangesetReviewBriefGenerateResponse:
    """Generate a reviewer-safe brief artifact for a changeset."""

    repository = _repository(context)
    try:
        workspace_root = _workspace_root_for_changeset(repository, changeset_id)
        result = ChangesetReviewBriefService(
            repository,
            context.repositories.artifacts,
        ).generate(
            changeset_id,
            workspace_root,
            created_by=request.actor,
        )
        detail = ChangesetQueryService(repository).get_detail(
            changeset_id,
            workspace_root=workspace_root,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return build_changeset_review_brief_generate_response(
        result,
        detail,
        include_markdown=request.include_markdown,
    )


@router.get(
    "/{changeset_id}/commit-message",
    response_model=CommitMessageSuggestionResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def suggest_changeset_commit_message(
    changeset_id: UUID,
    context: RuntimeContextDep,
    style: str = Query(default="plain", pattern="^(plain|conventional)$"),
) -> CommitMessageSuggestionResponse:
    """Suggest a deterministic commit message without committing."""

    repository = _repository(context)
    try:
        suggestion = await ChangesetCommitMessageSuggestionService(
            repository,
            context.repositories.artifacts,
        ).suggest(
            changeset_id,
            _workspace_root_for_changeset(repository, changeset_id),
            style=style,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return build_commit_message_suggestion_response(suggestion)


@router.post(
    "/{changeset_id}/archive",
    response_model=ChangesetActionResponse,
    responses={404: {"model": ErrorDetailResponse}},
)
async def archive_changeset(
    changeset_id: UUID,
    request: ChangesetArchiveRequest,
    context: RuntimeContextDep,
) -> ChangesetActionResponse:
    """Archive a changeset after explicit operator intent."""

    repository = _repository(context)
    try:
        event = ChangesetActionService(repository).archive_changeset(
            changeset_id,
            reason=request.reason,
            archived_by=request.actor,
            replacement_changeset_id=(
                UUID(request.replacement_changeset_id)
                if request.replacement_changeset_id is not None
                else None
            ),
        )
        detail = ChangesetQueryService(repository).get_detail(
            changeset_id,
            workspace_root=_workspace_root_for_changeset(repository, changeset_id),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ChangesetActionResponse(
        changeset_id=str(changeset_id),
        status="archived",
        event_sequence=event.sequence,
        detail=build_changeset_detail_response(detail),
    )


def _workspace_root_for_changeset(
    repository: ChangesetRepository,
    changeset_id: UUID,
):
    changeset = repository.get_changeset(changeset_id)
    if changeset is None:
        raise ValueError(f"unknown changeset: {changeset_id}")
    return _workspace_root_for_session(
        repository=repository,
        session_id=changeset.session_id,
    )


def _workspace_root_for_session(
    *,
    repository: ChangesetRepository,
    session_id: UUID,
):
    session = repository.get_session(session_id)
    if session is None:
        raise ValueError(f"unknown session: {session_id}")
    return session.cwd
