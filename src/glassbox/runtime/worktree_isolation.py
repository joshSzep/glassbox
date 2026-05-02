"""Temporary local git worktree workflows for reviewable changes."""

import os
import re
import subprocess
from collections.abc import Iterable
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core.events import EventEnvelope
from glassbox.core.events import WorktreeCleanupRecorded
from glassbox.core.events import WorktreeCreated
from glassbox.core.events import WorktreeStatusRecorded
from glassbox.core.ids import BranchCandidateId
from glassbox.core.ids import BranchSearchId
from glassbox.core.ids import ChangesetId
from glassbox.core.ids import SessionId
from glassbox.core.ids import WorktreeId
from glassbox.core.ids import new_worktree_id
from glassbox.core.models import SessionRecord
from glassbox.core.types import WorktreeSourceKind
from glassbox.core.types import WorktreeState


class WorktreeRepository(Protocol):
    """Repository methods needed by the worktree isolation service."""

    def append_event(self, event: EventEnvelope) -> EventEnvelope: ...

    def read_session_events(self, session_id: SessionId) -> list[EventEnvelope]: ...

    def list_sessions(
        self,
        *,
        limit: int | None = None,
    ) -> list[SessionRecord]: ...


class WorktreeStatus(BaseModel):
    """Live git status for one temporary worktree."""

    model_config = ConfigDict(extra="forbid")

    state: WorktreeState
    path_exists: bool
    dirty: bool
    current_branch: str | None = None
    head_revision: str | None = None
    git_status_short: list[str] = Field(default_factory=list, max_length=200)
    safe_next_actions: list[str] = Field(default_factory=list, max_length=20)
    limitations: list[str] = Field(default_factory=list, max_length=20)


class WorktreeRecord(BaseModel):
    """Rebuilt worktree custody record plus latest live status."""

    model_config = ConfigDict(extra="forbid")

    worktree_id: WorktreeId
    session_id: SessionId
    path: str
    branch_name: str
    base_revision: str
    source_kind: WorktreeSourceKind
    source_id: str | None = None
    changeset_id: ChangesetId | None = None
    branch_search_id: BranchSearchId | None = None
    branch_candidate_id: BranchCandidateId | None = None
    owner_process: str
    created_by: str
    state: WorktreeState
    created_at: str
    updated_at: str
    latest_sequence: int
    status: WorktreeStatus


class WorktreeCreateResult(BaseModel):
    """Result of creating a Glassbox-managed local worktree."""

    model_config = ConfigDict(extra="forbid")

    record: WorktreeRecord
    event: EventEnvelope


class WorktreeCleanupResult(BaseModel):
    """Result of a cleanup preview or removal attempt."""

    model_config = ConfigDict(extra="forbid")

    record: WorktreeRecord
    event: EventEnvelope
    removed: bool
    blocked: bool
    reason: str


class WorktreeIsolationService:
    """Create, inspect, and clean up temporary local git worktrees."""

    def __init__(self, repository: WorktreeRepository) -> None:
        self._repository = repository

    def create(
        self,
        *,
        session_id: SessionId,
        workspace_root: Path,
        source_kind: WorktreeSourceKind,
        source_id: str | None = None,
        changeset_id: ChangesetId | None = None,
        branch_search_id: BranchSearchId | None = None,
        branch_candidate_id: BranchCandidateId | None = None,
        base_revision: str = "HEAD",
        branch_name: str | None = None,
        path: Path | None = None,
        created_by: str = "operator",
    ) -> WorktreeCreateResult:
        """Create one temporary worktree and record canonical custody evidence."""

        workspace_root = workspace_root.resolve(strict=False)
        _require_git_repository(workspace_root)
        _run_git(workspace_root, "worktree", "list", "--porcelain")
        resolved_base = _run_git(
            workspace_root,
            "rev-parse",
            "--verify",
            base_revision,
        ).stdout.strip()
        worktree_id = new_worktree_id()
        resolved_path = _resolve_worktree_path(workspace_root, worktree_id, path)
        resolved_branch = branch_name or _default_branch_name(
            worktree_id,
            source_kind=source_kind,
            source_id=source_id,
        )
        if resolved_path.exists() and any(resolved_path.iterdir()):
            raise ValueError(
                f"worktree path already exists and is not empty: {resolved_path}"
            )
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        _run_git(
            workspace_root,
            "worktree",
            "add",
            str(resolved_path),
            "-b",
            resolved_branch,
            resolved_base,
        )
        event = self._repository.append_event(
            EventEnvelope(
                session_id=session_id,
                sequence=0,
                payload=WorktreeCreated(
                    worktree_id=worktree_id,
                    path=str(resolved_path),
                    branch_name=resolved_branch,
                    base_revision=resolved_base,
                    source_kind=source_kind,
                    source_id=source_id,
                    changeset_id=changeset_id,
                    branch_search_id=branch_search_id,
                    branch_candidate_id=branch_candidate_id,
                    owner_process=f"pid:{os.getpid()}",
                    state=WorktreeState.ACTIVE,
                    created_by=created_by,
                ),
            )
        )
        record = self.get(worktree_id, workspace_root=workspace_root)
        return WorktreeCreateResult(record=record, event=event)

    def list_worktrees(
        self,
        *,
        workspace_root: Path,
        session_id: SessionId | None = None,
        include_cleaned: bool = False,
    ) -> list[WorktreeRecord]:
        """List rebuilt worktree records from canonical events."""

        records = list(self._iter_records(workspace_root=workspace_root))
        if session_id is not None:
            records = [record for record in records if record.session_id == session_id]
        if not include_cleaned:
            records = [
                record for record in records if record.state != WorktreeState.CLEANED
            ]
        return sorted(records, key=lambda record: record.updated_at, reverse=True)

    def get(self, worktree_id: WorktreeId, *, workspace_root: Path) -> WorktreeRecord:
        """Return one rebuilt worktree record or raise a clear error."""

        for record in self._iter_records(workspace_root=workspace_root):
            if record.worktree_id == worktree_id:
                return record
        raise ValueError(f"worktree not found: {worktree_id}")

    def record_status(
        self,
        worktree_id: WorktreeId,
        *,
        workspace_root: Path,
        inspected_by: str = "operator",
    ) -> tuple[WorktreeRecord, EventEnvelope]:
        """Inspect a worktree and append a status evidence event."""

        record = self.get(worktree_id, workspace_root=workspace_root)
        status = inspect_worktree(Path(record.path))
        event = self._repository.append_event(
            EventEnvelope(
                session_id=record.session_id,
                sequence=0,
                payload=WorktreeStatusRecorded(
                    worktree_id=worktree_id,
                    state=status.state,
                    path_exists=status.path_exists,
                    dirty=status.dirty,
                    current_branch=status.current_branch,
                    head_revision=status.head_revision,
                    git_status_short=status.git_status_short,
                    inspected_by=inspected_by,
                    safe_next_actions=status.safe_next_actions,
                ),
            )
        )
        return self.get(worktree_id, workspace_root=workspace_root), event

    def cleanup(
        self,
        worktree_id: WorktreeId,
        *,
        workspace_root: Path,
        confirmed_by: str = "operator",
        discard_user_changes: bool = False,
    ) -> WorktreeCleanupResult:
        """Remove a Glassbox-managed worktree only after explicit confirmation."""

        record = self.get(worktree_id, workspace_root=workspace_root)
        status = inspect_worktree(Path(record.path))
        removed = False
        blocked = False
        state = WorktreeState.CLEANED
        reason = "worktree removed after explicit cleanup confirmation"
        safe_next_actions: list[str] = []

        if not status.path_exists:
            state = WorktreeState.MISSING
            reason = "worktree path is already missing; retained cleanup evidence"
        elif status.dirty and not discard_user_changes:
            blocked = True
            state = WorktreeState.CLEANUP_BLOCKED
            reason = "cleanup blocked because the worktree has local changes"
            safe_next_actions = status.safe_next_actions
        else:
            command = ["worktree", "remove", str(Path(record.path))]
            if discard_user_changes:
                command.insert(2, "--force")
            _run_git(workspace_root.resolve(strict=False), *command)
            removed = True

        event = self._repository.append_event(
            EventEnvelope(
                session_id=record.session_id,
                sequence=0,
                payload=WorktreeCleanupRecorded(
                    worktree_id=worktree_id,
                    state=state,
                    path=record.path,
                    confirmed_by=confirmed_by,
                    dirty=status.dirty,
                    forced=discard_user_changes,
                    removed=removed,
                    reason=reason,
                    safe_next_actions=safe_next_actions,
                ),
            )
        )
        return WorktreeCleanupResult(
            record=self.get(worktree_id, workspace_root=workspace_root),
            event=event,
            removed=removed,
            blocked=blocked,
            reason=reason,
        )

    def _iter_records(self, *, workspace_root: Path) -> Iterable[WorktreeRecord]:
        created: dict[WorktreeId, tuple[SessionId, WorktreeCreated, EventEnvelope]] = {}
        latest_state: dict[WorktreeId, tuple[WorktreeState, EventEnvelope]] = {}
        for session in self._repository.list_sessions():
            for event in self._repository.read_session_events(session.session_id):
                payload = event.payload
                if isinstance(payload, WorktreeCreated):
                    created[payload.worktree_id] = (event.session_id, payload, event)
                    latest_state[payload.worktree_id] = (payload.state, event)
                elif isinstance(
                    payload,
                    WorktreeStatusRecorded | WorktreeCleanupRecorded,
                ):
                    latest_state[payload.worktree_id] = (payload.state, event)

        for worktree_id, (session_id, payload, created_event) in created.items():
            state, latest_event = latest_state.get(
                worktree_id,
                (payload.state, created_event),
            )
            status = inspect_worktree(Path(payload.path))
            if state == WorktreeState.ACTIVE and status.dirty:
                state = WorktreeState.DIRTY
            elif state == WorktreeState.ACTIVE and not status.path_exists:
                state = WorktreeState.MISSING
            yield WorktreeRecord(
                worktree_id=worktree_id,
                session_id=session_id,
                path=payload.path,
                branch_name=payload.branch_name,
                base_revision=payload.base_revision,
                source_kind=payload.source_kind,
                source_id=payload.source_id,
                changeset_id=payload.changeset_id,
                branch_search_id=payload.branch_search_id,
                branch_candidate_id=payload.branch_candidate_id,
                owner_process=payload.owner_process,
                created_by=payload.created_by,
                state=state,
                created_at=created_event.created_at.isoformat(),
                updated_at=latest_event.created_at.isoformat(),
                latest_sequence=latest_event.sequence,
                status=status,
            )


def inspect_worktree(path: Path) -> WorktreeStatus:
    """Inspect one local worktree path without mutating it."""

    resolved_path = path.resolve(strict=False)
    if not resolved_path.exists():
        return WorktreeStatus(
            state=WorktreeState.MISSING,
            path_exists=False,
            dirty=False,
            safe_next_actions=["git worktree list --porcelain"],
            limitations=["worktree path does not exist"],
        )
    status_result = _run_git_or_none(resolved_path, "status", "--short")
    if status_result is None:
        return WorktreeStatus(
            state=WorktreeState.UNSUPPORTED,
            path_exists=True,
            dirty=False,
            safe_next_actions=[f"git -C {resolved_path} status --short"],
            limitations=["path is not an inspectable git worktree"],
        )
    status_lines = [line for line in status_result.stdout.splitlines() if line.strip()][
        :200
    ]
    branch_result = _run_git_or_none(resolved_path, "branch", "--show-current")
    head_result = _run_git_or_none(resolved_path, "rev-parse", "HEAD")
    dirty = bool(status_lines)
    return WorktreeStatus(
        state=WorktreeState.DIRTY if dirty else WorktreeState.CLEANUP_READY,
        path_exists=True,
        dirty=dirty,
        current_branch=(branch_result.stdout.strip() if branch_result else None),
        head_revision=(head_result.stdout.strip() if head_result else None),
        git_status_short=status_lines,
        safe_next_actions=[
            f"git -C {resolved_path} status --short",
            "git worktree list --porcelain",
        ],
    )


def _resolve_worktree_path(
    workspace_root: Path,
    worktree_id: WorktreeId,
    requested_path: Path | None,
) -> Path:
    safe_root = _default_safe_worktree_root(workspace_root)
    resolved = (
        requested_path.resolve(strict=False)
        if requested_path is not None
        else safe_root / str(worktree_id)
    )
    if not resolved.is_relative_to(safe_root):
        raise ValueError(f"worktree path must be under the safe local root {safe_root}")
    return resolved


def _default_safe_worktree_root(workspace_root: Path) -> Path:
    return (
        workspace_root.parent / f"{workspace_root.name}.glassbox-worktrees"
    ).resolve(strict=False)


def _default_branch_name(
    worktree_id: WorktreeId,
    *,
    source_kind: WorktreeSourceKind,
    source_id: str | None,
) -> str:
    suffix = _slug(source_id or source_kind.value)
    return f"glassbox/worktree/{str(worktree_id)[:8]}-{suffix}"


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip().lower()).strip("-")
    return slug[:40] or "candidate"


def _require_git_repository(workspace_root: Path) -> None:
    result = _run_git(workspace_root, "rev-parse", "--show-toplevel")
    git_root = Path(result.stdout.strip()).resolve(strict=False)
    if git_root != workspace_root.resolve(strict=False):
        raise ValueError(
            f"worktree commands must run from the repository root; detected {git_root}"
        )


def _run_git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            env=_git_subprocess_env(),
        )
    except FileNotFoundError as exc:
        raise ValueError("git executable is not available") from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        stdout = (exc.stdout or "").strip()
        detail = stderr or stdout or f"exit code {exc.returncode}"
        raise ValueError(f"git {' '.join(args)} failed: {detail}") from exc


def _run_git_or_none(
    cwd: Path,
    *args: str,
) -> subprocess.CompletedProcess[str] | None:
    try:
        return _run_git(cwd, *args)
    except ValueError:
        return None


def _git_subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in tuple(env):
        if key == "GIT_CONFIG_GLOBAL" or key.startswith("GIT_"):
            env.pop(key, None)
    return env


__all__ = [
    "WorktreeCleanupResult",
    "WorktreeCreateResult",
    "WorktreeIsolationService",
    "WorktreeRecord",
    "WorktreeRepository",
    "WorktreeStatus",
    "inspect_worktree",
]
