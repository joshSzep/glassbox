"""Preview and adopt selected branch-search candidates into changesets."""

from pathlib import Path
from typing import Protocol

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core import BranchCandidateId
from glassbox.core import BranchCandidateRecord
from glassbox.core import BranchCandidateStatus
from glassbox.core import BranchSearchId
from glassbox.core import BranchSearchRecord
from glassbox.core import ChangesetId
from glassbox.core import SessionId
from glassbox.core import WorktreeId
from glassbox.runtime.branch_decision_models import BranchCandidateDecisionSupport
from glassbox.runtime.branch_decision_support import (
    derive_branch_search_decision_support,
)
from glassbox.runtime.changesets import ChangesetDerivationResult
from glassbox.runtime.changesets import ChangesetDerivationService
from glassbox.runtime.changesets import ChangesetRepository
from glassbox.runtime.worktree_isolation import WorktreeIsolationService
from glassbox.runtime.worktree_isolation import WorktreeRecord
from glassbox.runtime.worktree_isolation import WorktreeRepository


class BranchCandidateAdoptionRepository(
    ChangesetRepository,
    WorktreeRepository,
    Protocol,
):
    """Repository methods needed by candidate adoption workflows."""


class BranchCandidateAdoptionPreview(BaseModel):
    """Preview-only adoption posture for one selected branch-search candidate."""

    model_config = ConfigDict(extra="forbid")

    search_id: BranchSearchId
    candidate_id: BranchCandidateId
    selected: bool
    changeset_ready: bool
    objective: str = Field(min_length=1, max_length=4000)
    strategy_label: str = Field(min_length=1, max_length=200)
    candidate_session_id: SessionId | None = None
    changed_files: list[str] = Field(default_factory=list, max_length=500)
    changed_files_summary: str = Field(min_length=1, max_length=1000)
    verification_posture: str = Field(min_length=1, max_length=100)
    risk_posture: str = Field(min_length=1, max_length=100)
    accepted_risks: list[str] = Field(default_factory=list, max_length=20)
    conflicts: list[str] = Field(default_factory=list, max_length=20)
    stale_evidence: list[str] = Field(default_factory=list, max_length=20)
    limitations: list[str] = Field(default_factory=list, max_length=20)
    safe_next_actions: list[str] = Field(default_factory=list, max_length=20)
    worktree: WorktreeRecord | None = None
    workspace_mutation_performed: bool = False
    non_claims: list[str] = Field(default_factory=list, max_length=20)


class BranchCandidateAdoptionResult(BaseModel):
    """Result of explicitly adopting a candidate into a changeset."""

    model_config = ConfigDict(extra="forbid")

    preview: BranchCandidateAdoptionPreview
    changeset: ChangesetDerivationResult


class BranchCandidateAdoptionService:
    """Preview and record explicit branch-candidate adoption."""

    def __init__(self, repository: BranchCandidateAdoptionRepository) -> None:
        self._repository = repository

    def preview(
        self,
        search_id: BranchSearchId,
        candidate_id: BranchCandidateId,
        *,
        workspace_root: Path,
        worktree_id: WorktreeId | None = None,
    ) -> BranchCandidateAdoptionPreview:
        """Build an adoption preview without mutating workspace or changesets."""

        search = self._require_search(search_id)
        candidate = self._require_candidate(search, candidate_id)
        support = self._decision_support(search, candidate, workspace_root)
        worktree = (
            WorktreeIsolationService(self._repository).get(
                worktree_id,
                workspace_root=workspace_root,
            )
            if worktree_id is not None
            else None
        )
        selected = (
            search.selected_candidate_id == candidate.candidate_id
            and candidate.status == BranchCandidateStatus.SELECTED
        )
        limitations = _preview_limitations(candidate, support, worktree)
        conflicts = _preview_conflicts(worktree)
        stale_evidence = _preview_stale_evidence(candidate, support, worktree)
        return BranchCandidateAdoptionPreview(
            search_id=search.search_id,
            candidate_id=candidate.candidate_id,
            selected=selected,
            changeset_ready=selected,
            objective=search.objective,
            strategy_label=candidate.strategy_label,
            candidate_session_id=candidate.candidate_session_id,
            changed_files=support.changed_files,
            changed_files_summary=support.changed_files_summary,
            verification_posture=support.verification_posture,
            risk_posture=support.risk_posture,
            accepted_risks=support.accepted_risks,
            conflicts=conflicts,
            stale_evidence=stale_evidence,
            limitations=limitations,
            safe_next_actions=_preview_safe_next_actions(
                search,
                candidate,
                selected=selected,
                worktree=worktree,
            ),
            worktree=worktree,
            workspace_mutation_performed=False,
            non_claims=[
                (
                    "preview does not merge, rebase, cherry-pick, stage, "
                    "commit, push, or open a PR"
                ),
                (
                    "adoption records changeset evidence only; final git "
                    "mutation remains operator-controlled"
                ),
            ],
        )

    def adopt(
        self,
        search_id: BranchSearchId,
        candidate_id: BranchCandidateId,
        *,
        workspace_root: Path,
        worktree_id: WorktreeId | None = None,
        objective: str | None = None,
        changeset_id: ChangesetId | None = None,
    ) -> BranchCandidateAdoptionResult:
        """Record selected candidate adoption without workspace mutation."""

        preview = self.preview(
            search_id,
            candidate_id,
            workspace_root=workspace_root,
            worktree_id=worktree_id,
        )
        if not preview.selected:
            raise ValueError(
                f"branch candidate {candidate_id} is not selected for search "
                f"{search_id}; preview before adopting a selected candidate"
            )
        changeset = ChangesetDerivationService(
            self._repository
        ).create_from_branch_candidate(
            search_id,
            candidate_id,
            objective=objective,
            changeset_id=changeset_id,
        )
        return BranchCandidateAdoptionResult(preview=preview, changeset=changeset)

    def _require_search(self, search_id: BranchSearchId) -> BranchSearchRecord:
        search = self._repository.get_branch_search(search_id)
        if search is None:
            raise ValueError(f"unknown branch search: {search_id}")
        return search

    def _require_candidate(
        self,
        search: BranchSearchRecord,
        candidate_id: BranchCandidateId,
    ) -> BranchCandidateRecord:
        for candidate in self._repository.list_branch_candidates(
            search.session_id,
            search.search_id,
        ):
            if candidate.candidate_id == candidate_id:
                return candidate
        raise ValueError(f"unknown branch candidate: {candidate_id}")

    def _decision_support(
        self,
        search: BranchSearchRecord,
        candidate: BranchCandidateRecord,
        workspace_root: Path,
    ) -> BranchCandidateDecisionSupport:
        support = derive_branch_search_decision_support(
            search=search,
            candidates=[candidate],
            workspace_root=workspace_root,
        )
        return support.candidates[0]


def _preview_limitations(
    candidate: BranchCandidateRecord,
    support: BranchCandidateDecisionSupport,
    worktree: WorktreeRecord | None,
) -> list[str]:
    limitations: list[str] = []
    if candidate.candidate_session_id is None:
        limitations.append("candidate has no materialized session")
    if not support.changed_files:
        limitations.append("candidate diff inventory is not retained")
    if candidate.verification_summary is None:
        limitations.append("candidate has no verification summary")
    if worktree is None:
        limitations.append("no worktree state was provided for this preview")
    elif worktree.status.limitations:
        limitations.extend(worktree.status.limitations)
    return limitations


def _preview_conflicts(worktree: WorktreeRecord | None) -> list[str]:
    if worktree is None:
        return []
    if worktree.status.dirty:
        return ["worktree has local changes that must be inspected before cleanup"]
    if not worktree.status.path_exists:
        return ["worktree path is missing"]
    return []


def _preview_stale_evidence(
    candidate: BranchCandidateRecord,
    support: BranchCandidateDecisionSupport,
    worktree: WorktreeRecord | None,
) -> list[str]:
    stale: list[str] = []
    if support.verification_posture in {"blocked", "unknown"}:
        stale.append("candidate verification evidence is missing or inconclusive")
    if worktree is not None and worktree.status.head_revision is None:
        stale.append("worktree HEAD revision could not be inspected")
    if candidate.verification_id is None:
        stale.append("candidate has no retained verification id")
    return stale


def _preview_safe_next_actions(
    search: BranchSearchRecord,
    candidate: BranchCandidateRecord,
    *,
    selected: bool,
    worktree: WorktreeRecord | None,
) -> list[str]:
    actions = [
        f"glassbox branch-search show {search.search_id} --cwd .",
        (
            "glassbox changeset adoption-preview "
            f"--branch-search {search.search_id} "
            f"--candidate {candidate.candidate_id} --cwd ."
        ),
    ]
    if worktree is not None:
        actions.insert(0, f"glassbox worktree status {worktree.worktree_id} --cwd .")
    if selected:
        actions.append(
            "glassbox changeset adopt-candidate "
            f"--branch-search {search.search_id} "
            f"--candidate {candidate.candidate_id} --confirm --cwd ."
        )
    return actions


__all__ = [
    "BranchCandidateAdoptionPreview",
    "BranchCandidateAdoptionRepository",
    "BranchCandidateAdoptionResult",
    "BranchCandidateAdoptionService",
]
