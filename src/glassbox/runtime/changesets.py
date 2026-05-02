"""Runtime service for deriving and inspecting reviewable changesets."""

import hashlib
import subprocess
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
from glassbox.core import ChangesetArchived
from glassbox.core import ChangesetCandidateAdopted
from glassbox.core import ChangesetCreated
from glassbox.core import ChangesetId
from glassbox.core import ChangesetInventoryRecord
from glassbox.core import ChangesetReadinessRecord
from glassbox.core import ChangesetRecord
from glassbox.core import ChangesetReviewBriefRecord
from glassbox.core import ChangesetSourceAttached
from glassbox.core import ChangesetSourceKind
from glassbox.core import ChangesetSourceRecord
from glassbox.core import ChangesetVerificationPostureRecord
from glassbox.core import EventEnvelope
from glassbox.core import EventPayloadType
from glassbox.core import ProjectionHealth
from glassbox.core import SessionId
from glassbox.core import SessionRecord
from glassbox.core import SessionState
from glassbox.core import SessionStatus
from glassbox.core import TaskId
from glassbox.core import TaskPlanStatus
from glassbox.core import TaskRecord
from glassbox.core import new_changeset_id


class ChangesetDerivationRepository(Protocol):
    """Repository methods required by changeset derivation."""

    def get_session(self, session_id: SessionId) -> SessionRecord | None: ...

    def get_session_state(self, session_id: SessionId) -> SessionState | None: ...

    def inspect_session_projection_health(
        self,
        session_id: SessionId,
    ) -> ProjectionHealth: ...

    def get_task(self, task_id: TaskId) -> TaskRecord | None: ...

    def get_branch_search(
        self,
        search_id: BranchSearchId,
    ) -> BranchSearchRecord | None: ...

    def list_branch_candidates(
        self,
        session_id: SessionId,
        search_id: BranchSearchId,
    ) -> list[BranchCandidateRecord]: ...

    def append_events(
        self,
        events: list[EventEnvelope],
    ) -> list[EventEnvelope]: ...


class ChangesetRepository(ChangesetDerivationRepository, Protocol):
    """Repository methods required by changeset query and action services."""

    def list_changesets(
        self,
        *,
        session_id: SessionId | None = None,
        include_archived: bool = False,
        limit: int | None = None,
    ) -> list[ChangesetRecord]: ...

    def get_changeset(self, changeset_id: ChangesetId) -> ChangesetRecord | None: ...

    def list_changeset_sources(
        self,
        session_id: SessionId,
        changeset_id: ChangesetId,
    ) -> list[ChangesetSourceRecord]: ...

    def get_changeset_inventory(
        self,
        session_id: SessionId,
        changeset_id: ChangesetId,
    ) -> ChangesetInventoryRecord | None: ...

    def get_changeset_verification_posture(
        self,
        session_id: SessionId,
        changeset_id: ChangesetId,
    ) -> ChangesetVerificationPostureRecord | None: ...

    def list_changeset_review_briefs(
        self,
        session_id: SessionId,
        changeset_id: ChangesetId,
    ) -> list[ChangesetReviewBriefRecord]: ...

    def list_changeset_readiness(
        self,
        session_id: SessionId,
        changeset_id: ChangesetId,
    ) -> list[ChangesetReadinessRecord]: ...


class ChangesetDerivationResult(BaseModel):
    """Result of explicitly deriving one changeset."""

    model_config = ConfigDict(extra="forbid")

    changeset_id: ChangesetId
    session_id: SessionId
    limitations: list[str] = Field(default_factory=list)
    stored_events: list[EventEnvelope] = Field(default_factory=list)


class ChangesetDetailView(BaseModel):
    """Read model for one changeset and its currently retained evidence refs."""

    model_config = ConfigDict(extra="forbid")

    changeset: ChangesetRecord
    sources: list[ChangesetSourceRecord] = Field(default_factory=list)
    inventory: ChangesetInventoryRecord | None = None
    verification_posture: ChangesetVerificationPostureRecord | None = None
    review_briefs: list[ChangesetReviewBriefRecord] = Field(default_factory=list)
    readiness: list[ChangesetReadinessRecord] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    safe_next_actions: list[str] = Field(default_factory=list)


class ChangesetDerivationService:
    """Create changeset evidence from existing sessions, tasks, candidates, or diff."""

    def __init__(self, repository: ChangesetDerivationRepository) -> None:
        self._repository = repository

    def create_from_session(
        self,
        session_id: SessionId,
        *,
        objective: str | None = None,
        changeset_id: ChangesetId | None = None,
    ) -> ChangesetDerivationResult:
        session = self._require_session(session_id)
        limitations = self._session_limitations(session)
        resolved_changeset_id = changeset_id or new_changeset_id()
        stored_events = self._append(
            session.session_id,
            ChangesetCreated(
                changeset_id=resolved_changeset_id,
                objective=objective or f"Review session {session.session_id}",
                summary=_limitations_summary(limitations),
            ),
            ChangesetSourceAttached(
                changeset_id=resolved_changeset_id,
                source_kind=ChangesetSourceKind.SESSION,
                source_session_id=session.session_id,
                reason="created from session evidence",
                limitation=_join_limitations(limitations),
            ),
        )
        return ChangesetDerivationResult(
            changeset_id=resolved_changeset_id,
            session_id=session.session_id,
            limitations=limitations,
            stored_events=stored_events,
        )

    def create_from_task(
        self,
        task_id: TaskId,
        *,
        objective: str | None = None,
        changeset_id: ChangesetId | None = None,
    ) -> ChangesetDerivationResult:
        task = self._repository.get_task(task_id)
        if task is None:
            raise ValueError(f"unknown task: {task_id}")
        session = self._require_session(task.session_id)
        limitations = [
            *self._session_limitations(session),
            *_task_limitations(task),
        ]
        resolved_changeset_id = changeset_id or new_changeset_id()
        stored_events = self._append(
            task.session_id,
            ChangesetCreated(
                changeset_id=resolved_changeset_id,
                objective=objective or f"Review task: {task.title}",
                summary=_limitations_summary(limitations),
                task_id=task.task_id,
                turn_id=task.source_turn_id,
            ),
            ChangesetSourceAttached(
                changeset_id=resolved_changeset_id,
                source_kind=ChangesetSourceKind.TASK,
                source_session_id=task.session_id,
                task_id=task.task_id,
                turn_id=task.source_turn_id,
                reason="created from task evidence",
                limitation=_join_limitations(limitations),
            ),
        )
        return ChangesetDerivationResult(
            changeset_id=resolved_changeset_id,
            session_id=task.session_id,
            limitations=limitations,
            stored_events=stored_events,
        )

    def create_from_branch_candidate(
        self,
        search_id: BranchSearchId,
        candidate_id: BranchCandidateId,
        *,
        objective: str | None = None,
        changeset_id: ChangesetId | None = None,
    ) -> ChangesetDerivationResult:
        search = self._repository.get_branch_search(search_id)
        if search is None:
            raise ValueError(f"unknown branch search: {search_id}")
        candidate = self._selected_candidate(search, candidate_id)
        session = self._require_session(search.session_id)
        limitations = self._session_limitations(session)
        if candidate.candidate_session_id is None:
            limitations.append("candidate has no materialized session")
        if candidate.verification_summary is None:
            limitations.append("candidate has no verification summary")
        resolved_changeset_id = changeset_id or new_changeset_id()
        stored_events = self._append(
            search.session_id,
            ChangesetCreated(
                changeset_id=resolved_changeset_id,
                objective=objective
                or f"Review branch candidate: {candidate.strategy_label}",
                summary=_limitations_summary(limitations),
                task_id=search.task_id,
                branch_search_id=search.search_id,
                branch_candidate_id=candidate.candidate_id,
            ),
            ChangesetCandidateAdopted(
                changeset_id=resolved_changeset_id,
                branch_search_id=search.search_id,
                branch_candidate_id=candidate.candidate_id,
                candidate_session_id=candidate.candidate_session_id,
                preview_artifact_id=candidate.artifact_id,
                verification_id=candidate.verification_id,
                task_id=search.task_id,
                reason="created from selected branch-search candidate",
                workspace_mutation_performed=False,
            ),
        )
        return ChangesetDerivationResult(
            changeset_id=resolved_changeset_id,
            session_id=search.session_id,
            limitations=limitations,
            stored_events=stored_events,
        )

    def create_from_workspace_diff(
        self,
        session_id: SessionId,
        workspace_root: Path,
        *,
        objective: str | None = None,
        changeset_id: ChangesetId | None = None,
    ) -> ChangesetDerivationResult:
        session = self._require_session(session_id)
        diff = _workspace_diff_snapshot(workspace_root)
        limitations = self._session_limitations(session)
        if diff.error is not None:
            limitations.append(f"workspace diff unavailable: {diff.error}")
        elif not diff.changed_paths:
            limitations.append("workspace has no local diff from git status")
        else:
            limitations.append(
                f"workspace diff has {len(diff.changed_paths)} changed path(s)"
            )
        resolved_changeset_id = changeset_id or new_changeset_id()
        stored_events = self._append(
            session.session_id,
            ChangesetCreated(
                changeset_id=resolved_changeset_id,
                objective=objective or "Review current workspace diff",
                summary=_limitations_summary(limitations),
            ),
            ChangesetSourceAttached(
                changeset_id=resolved_changeset_id,
                source_kind=ChangesetSourceKind.WORKSPACE_DIFF,
                source_session_id=session.session_id,
                reason=_workspace_diff_reason(diff),
                limitation=_join_limitations(limitations),
            ),
        )
        return ChangesetDerivationResult(
            changeset_id=resolved_changeset_id,
            session_id=session.session_id,
            limitations=limitations,
            stored_events=stored_events,
        )

    def _append(
        self,
        session_id: SessionId,
        *payloads: EventPayloadType,
    ) -> list[EventEnvelope]:
        return self._repository.append_events(
            [
                EventEnvelope(session_id=session_id, sequence=0, payload=payload)
                for payload in payloads
            ]
        )

    def _require_session(self, session_id: SessionId) -> SessionRecord:
        session = self._repository.get_session(session_id)
        if session is None:
            raise ValueError(f"unknown session: {session_id}")
        return session

    def _session_limitations(self, session: SessionRecord) -> list[str]:
        limitations: list[str] = []
        state = self._repository.get_session_state(session.session_id)
        if state is None:
            limitations.append("session state projection is unavailable")
        elif state.status not in _TERMINAL_SESSION_STATUSES:
            limitations.append(f"session is {state.status.value}, not terminal")
        health = self._repository.inspect_session_projection_health(session.session_id)
        if health.degraded:
            detail = f": {health.detail}" if health.detail else ""
            limitations.append(f"projection health is {health.state}{detail}")
        if session.parent_session_id is not None:
            limitations.append("session is forked or imported from another session")
        return limitations

    def _selected_candidate(
        self,
        search: BranchSearchRecord,
        candidate_id: BranchCandidateId,
    ) -> BranchCandidateRecord:
        if search.selected_candidate_id != candidate_id:
            raise ValueError(
                f"branch candidate {candidate_id} is not selected for search "
                f"{search.search_id}"
            )
        for candidate in self._repository.list_branch_candidates(
            search.session_id,
            search.search_id,
        ):
            if candidate.candidate_id == candidate_id:
                if candidate.status != BranchCandidateStatus.SELECTED:
                    raise ValueError(
                        f"branch candidate {candidate_id} is {candidate.status.value}, "
                        "not selected"
                    )
                return candidate
        raise ValueError(f"unknown branch candidate: {candidate_id}")


class ChangesetQueryService:
    """Read-only changeset query service."""

    def __init__(self, repository: ChangesetRepository) -> None:
        self._repository = repository

    def list_changesets(
        self,
        *,
        session_id: SessionId | None = None,
        include_archived: bool = False,
        limit: int | None = None,
    ) -> list[ChangesetRecord]:
        return self._repository.list_changesets(
            session_id=session_id,
            include_archived=include_archived,
            limit=limit,
        )

    def get_detail(self, changeset_id: ChangesetId) -> ChangesetDetailView:
        changeset = self._repository.get_changeset(changeset_id)
        if changeset is None:
            raise ValueError(f"unknown changeset: {changeset_id}")
        sources = self._repository.list_changeset_sources(
            changeset.session_id,
            changeset.changeset_id,
        )
        inventory = self._repository.get_changeset_inventory(
            changeset.session_id,
            changeset.changeset_id,
        )
        verification_posture = self._repository.get_changeset_verification_posture(
            changeset.session_id,
            changeset.changeset_id,
        )
        review_briefs = self._repository.list_changeset_review_briefs(
            changeset.session_id,
            changeset.changeset_id,
        )
        readiness = self._repository.list_changeset_readiness(
            changeset.session_id,
            changeset.changeset_id,
        )
        return ChangesetDetailView(
            changeset=changeset,
            sources=sources,
            inventory=inventory,
            verification_posture=verification_posture,
            review_briefs=review_briefs,
            readiness=readiness,
            limitations=_detail_limitations(changeset, sources, inventory),
            safe_next_actions=_detail_safe_next_actions(changeset),
        )


class ChangesetActionService:
    """Explicit operator actions against an existing changeset."""

    def __init__(self, repository: ChangesetRepository) -> None:
        self._repository = repository

    def archive_changeset(
        self,
        changeset_id: ChangesetId,
        *,
        reason: str,
        archived_by: str = "operator",
        replacement_changeset_id: ChangesetId | None = None,
    ) -> EventEnvelope:
        changeset = self._require_changeset(changeset_id)
        stored = self._repository.append_events(
            [
                EventEnvelope(
                    session_id=changeset.session_id,
                    sequence=0,
                    payload=ChangesetArchived(
                        changeset_id=changeset.changeset_id,
                        reason=reason,
                        archived_by=archived_by,
                        replacement_changeset_id=replacement_changeset_id,
                    ),
                )
            ]
        )
        return stored[0]

    def refresh_source_evidence(
        self,
        changeset_id: ChangesetId,
        workspace_root: Path,
        *,
        refreshed_by: str = "operator",
    ) -> EventEnvelope:
        changeset = self._require_changeset(changeset_id)
        diff = _workspace_diff_snapshot(workspace_root)
        limitation = (
            "basic source refresh only; structured inventory refresh is added "
            "by the change inventory phase"
        )
        if diff.error is not None:
            limitation = f"{limitation}; workspace diff unavailable: {diff.error}"
        stored = self._repository.append_events(
            [
                EventEnvelope(
                    session_id=changeset.session_id,
                    sequence=0,
                    payload=ChangesetSourceAttached(
                        changeset_id=changeset.changeset_id,
                        source_kind=ChangesetSourceKind.WORKSPACE_DIFF,
                        source_session_id=changeset.session_id,
                        reason=(
                            f"{_workspace_diff_reason(diff)}; "
                            f"refreshed by {refreshed_by}"
                        ),
                        limitation=limitation,
                        task_id=changeset.task_id,
                        turn_id=changeset.turn_id,
                        branch_search_id=changeset.branch_search_id,
                        branch_candidate_id=changeset.branch_candidate_id,
                    ),
                )
            ]
        )
        return stored[0]

    def _require_changeset(self, changeset_id: ChangesetId) -> ChangesetRecord:
        changeset = self._repository.get_changeset(changeset_id)
        if changeset is None:
            raise ValueError(f"unknown changeset: {changeset_id}")
        return changeset


_TERMINAL_SESSION_STATUSES = {
    SessionStatus.COMPLETED,
    SessionStatus.FAILED,
    SessionStatus.CANCELLED,
}

_TERMINAL_TASK_STATUSES = {
    TaskPlanStatus.COMPLETED,
    TaskPlanStatus.FAILED,
    TaskPlanStatus.CANCELLED,
    TaskPlanStatus.ABANDONED,
}


class _WorkspaceDiffSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    changed_paths: list[str] = Field(default_factory=list)
    digest: str | None = None
    error: str | None = None


def _task_limitations(task: TaskRecord) -> list[str]:
    if task.status in _TERMINAL_TASK_STATUSES:
        return []
    return [f"task is {task.status.value}, not terminal"]


def _workspace_diff_snapshot(workspace_root: Path) -> _WorkspaceDiffSnapshot:
    try:
        result = subprocess.run(
            ["git", "status", "--short", "--untracked-files=all"],
            cwd=workspace_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError:
        return _WorkspaceDiffSnapshot(error="git executable not found")
    except subprocess.TimeoutExpired:
        return _WorkspaceDiffSnapshot(error="git status timed out")
    if result.returncode != 0:
        return _WorkspaceDiffSnapshot(
            error=result.stderr.strip() or "git status failed"
        )
    changed_paths = sorted(_parse_status_paths(result.stdout))
    return _WorkspaceDiffSnapshot(
        changed_paths=changed_paths,
        digest=_changed_path_digest(changed_paths),
    )


def _parse_status_paths(output: str) -> list[str]:
    paths: list[str] = []
    for line in output.splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.rsplit(" -> ", maxsplit=1)[-1]
        if path:
            paths.append(path.replace("\\", "/"))
    return paths


def _changed_path_digest(paths: list[str]) -> str | None:
    if not paths:
        return None
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _workspace_diff_reason(diff: _WorkspaceDiffSnapshot) -> str:
    if diff.error is not None:
        return "created from workspace diff request with unavailable git status"
    if not diff.changed_paths:
        return "created from workspace diff request with no local diff"
    return (
        "created from workspace diff request "
        f"({len(diff.changed_paths)} changed path(s), digest {diff.digest})"
    )


def _join_limitations(limitations: list[str]) -> str | None:
    return "; ".join(limitations) if limitations else None


def _limitations_summary(limitations: list[str]) -> str | None:
    if not limitations:
        return None
    return "Degraded changeset: " + "; ".join(limitations)


def _detail_limitations(
    changeset: ChangesetRecord,
    sources: list[ChangesetSourceRecord],
    inventory: ChangesetInventoryRecord | None,
) -> list[str]:
    limitations = [
        source.limitation for source in sources if source.limitation is not None
    ]
    if inventory is None:
        limitations.append(
            "no structured change inventory is attached yet; inspect sources first"
        )
    if changeset.risk_level.value == "high":
        summary = changeset.risk_summary or "path classification marked high risk"
        limitations.append(f"high review risk: {summary}")
    return limitations


def _detail_safe_next_actions(changeset: ChangesetRecord) -> list[str]:
    actions = [f"glassbox changeset show {changeset.changeset_id} --cwd ."]
    if changeset.status != "archived":
        actions.append(f"glassbox changeset refresh {changeset.changeset_id} --cwd .")
        actions.append(
            "glassbox eval recommend PATH --cwd .  # inspect verification options"
        )
    return actions


__all__ = [
    "ChangesetActionService",
    "ChangesetDetailView",
    "ChangesetDerivationRepository",
    "ChangesetDerivationResult",
    "ChangesetDerivationService",
    "ChangesetQueryService",
    "ChangesetRepository",
]
