"""Runtime service for deriving reviewable changesets from existing evidence."""

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
from glassbox.core import ChangesetCandidateAdopted
from glassbox.core import ChangesetCreated
from glassbox.core import ChangesetId
from glassbox.core import ChangesetSourceAttached
from glassbox.core import ChangesetSourceKind
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


class ChangesetDerivationResult(BaseModel):
    """Result of explicitly deriving one changeset."""

    model_config = ConfigDict(extra="forbid")

    changeset_id: ChangesetId
    session_id: SessionId
    limitations: list[str] = Field(default_factory=list)
    stored_events: list[EventEnvelope] = Field(default_factory=list)


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


__all__ = [
    "ChangesetDerivationRepository",
    "ChangesetDerivationResult",
    "ChangesetDerivationService",
]
