"""Background job action API routes."""

from uuid import UUID

from fastapi import APIRouter
from fastapi import HTTPException

from glassbox.web.app import RuntimeContextDep
from glassbox.web.session_api import ErrorDetailResponse
from glassbox.web.task_api import BackgroundJobDetailResponse
from glassbox.web.task_api import TaskActionRequest
from glassbox.web.task_api import build_background_job_response

router = APIRouter(prefix="/jobs")


@router.post(
    "/{job_id}/cancel",
    response_model=BackgroundJobDetailResponse,
    responses={
        404: {"model": ErrorDetailResponse},
        409: {"model": ErrorDetailResponse},
    },
)
async def cancel_background_job(
    job_id: UUID,
    request: TaskActionRequest,
    context: RuntimeContextDep,
) -> BackgroundJobDetailResponse:
    """Request cancellation for one daemon-owned background job."""

    if context.repositories.sessions.get_background_job(job_id) is None:
        raise HTTPException(status_code=404, detail=f"unknown background job: {job_id}")
    try:
        job = context.repositories.sessions.cancel_background_job(
            job_id,
            requested_by=request.actor,
            reason=request.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return BackgroundJobDetailResponse(job=build_background_job_response(job))
