"""Read-only branch-search query service."""

from typing import Protocol

from pydantic import BaseModel
from pydantic import ConfigDict

from glassbox.core import BranchCandidateRecord
from glassbox.core import BranchSearchId
from glassbox.core import BranchSearchRecord
from glassbox.core import SessionId


class BranchSearchRepository(Protocol):
    """Repository methods required by branch-search queries."""

    def list_branch_searches(
        self,
        *,
        session_id: SessionId | None = None,
        limit: int | None = None,
    ) -> list[BranchSearchRecord]: ...

    def get_branch_search(
        self,
        search_id: BranchSearchId,
    ) -> BranchSearchRecord | None: ...

    def list_branch_candidates(
        self,
        session_id: SessionId,
        search_id: BranchSearchId,
    ) -> list[BranchCandidateRecord]: ...


class BranchSearchDetail(BaseModel):
    """Branch search plus candidate comparison rows."""

    model_config = ConfigDict(extra="forbid")

    search: BranchSearchRecord
    candidates: list[BranchCandidateRecord]


class BranchSearchQueryService:
    """Read-only service for branch-search CLI and API surfaces."""

    def __init__(self, repository: BranchSearchRepository) -> None:
        self._repository = repository

    def list_searches(
        self,
        *,
        session_id: SessionId | None = None,
        limit: int | None = None,
    ) -> list[BranchSearchRecord]:
        return self._repository.list_branch_searches(
            session_id=session_id,
            limit=limit,
        )

    def get_detail(self, search_id: BranchSearchId) -> BranchSearchDetail:
        search = self._repository.get_branch_search(search_id)
        if search is None:
            raise ValueError(f"unknown branch search: {search_id}")
        return BranchSearchDetail(
            search=search,
            candidates=self._repository.list_branch_candidates(
                search.session_id,
                search.search_id,
            ),
        )


__all__ = [
    "BranchSearchDetail",
    "BranchSearchQueryService",
    "BranchSearchRepository",
]
