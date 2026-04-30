"""Shared pagination response helpers for HTTP route modules."""

from glassbox.web.session_api import PageInfoResponse


def page_info(
    *,
    cursor: int,
    limit: int,
    returned_count: int,
    next_cursor: int | None,
) -> PageInfoResponse:
    """Build the common page envelope used by route response models."""

    return PageInfoResponse(
        cursor=cursor,
        limit=limit,
        next_cursor=next_cursor,
        has_more=next_cursor is not None,
        returned_count=returned_count,
    )
