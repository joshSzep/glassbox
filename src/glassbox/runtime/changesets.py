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
from glassbox.core import ChangesetInventoryFreshness
from glassbox.core import ChangesetInventoryRecord
from glassbox.core import ChangesetInventoryRefreshed
from glassbox.core import ChangesetReadinessRecord
from glassbox.core import ChangesetRecord
from glassbox.core import ChangesetReviewBriefRecord
from glassbox.core import ChangesetRiskLevel
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
from glassbox.runtime.change_inventory import CHANGE_INVENTORY_ARTIFACT_SCHEMA_VERSION
from glassbox.runtime.change_inventory import ChangeInventoryArtifact
from glassbox.runtime.change_inventory import change_inventory_artifact_json
from glassbox.runtime.change_inventory import change_inventory_from_diff_summary
from glassbox.services import ArtifactRepository
from glassbox.services import StoredArtifact
from glassbox.tools.workflow import DiffSummaryArgs
from glassbox.tools.workflow import DiffSummaryArtifact
from glassbox.tools.workflow import DiffSummaryResult
from glassbox.tools.workflow import DiffSummaryScope
from glassbox.tools.workflow import DiffSummaryTool


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

    def read_session_events(self, session_id: SessionId) -> list[EventEnvelope]: ...


class ChangesetDerivationResult(BaseModel):
    """Result of explicitly deriving one changeset."""

    model_config = ConfigDict(extra="forbid")

    changeset_id: ChangesetId
    session_id: SessionId
    limitations: list[str] = Field(default_factory=list)
    stored_events: list[EventEnvelope] = Field(default_factory=list)


class ChangesetInventoryStatus(BaseModel):
    """Current workspace comparison for the latest changeset inventory."""

    model_config = ConfigDict(extra="forbid")

    freshness: ChangesetInventoryFreshness
    stale: bool = False
    reason: str | None = Field(default=None, max_length=2000)
    recorded_source_digest: str | None = Field(default=None, max_length=256)
    current_source_digest: str | None = Field(default=None, max_length=256)
    safe_next_actions: list[str] = Field(default_factory=list)


class ChangesetDetailView(BaseModel):
    """Read model for one changeset and its currently retained evidence refs."""

    model_config = ConfigDict(extra="forbid")

    changeset: ChangesetRecord
    sources: list[ChangesetSourceRecord] = Field(default_factory=list)
    inventory: ChangesetInventoryRecord | None = None
    verification_posture: ChangesetVerificationPostureRecord | None = None
    inventory_status: ChangesetInventoryStatus
    review_briefs: list[ChangesetReviewBriefRecord] = Field(default_factory=list)
    readiness: list[ChangesetReadinessRecord] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    safe_next_actions: list[str] = Field(default_factory=list)


class ChangesetInventoryRefreshResult(BaseModel):
    """Result of explicitly refreshing one structured changeset inventory."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    changeset_id: ChangesetId
    session_id: SessionId
    artifact: StoredArtifact
    inventory: ChangeInventoryArtifact
    event: EventEnvelope
    superseded_event: EventEnvelope | None = None
    freshness: ChangesetInventoryFreshness
    source_digest: str | None = None


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

    def get_detail(
        self,
        changeset_id: ChangesetId,
        *,
        workspace_root: Path | None = None,
    ) -> ChangesetDetailView:
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
        inventory_status = _inventory_status(
            changeset,
            inventory,
            workspace_root=workspace_root,
        )
        inventory_for_detail = _inventory_with_status_freshness(
            inventory,
            inventory_status,
        )
        return ChangesetDetailView(
            changeset=changeset,
            sources=sources,
            inventory=inventory_for_detail,
            verification_posture=verification_posture,
            inventory_status=inventory_status,
            review_briefs=review_briefs,
            readiness=readiness,
            limitations=_detail_limitations(
                changeset,
                sources,
                inventory_for_detail,
                inventory_status,
            ),
            safe_next_actions=_detail_safe_next_actions(changeset, inventory_status),
        )


class ChangesetActionService:
    """Explicit operator actions against an existing changeset."""

    def __init__(
        self,
        repository: ChangesetRepository,
        artifact_repository: ArtifactRepository | None = None,
    ) -> None:
        self._repository = repository
        self._artifact_repository = artifact_repository

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

    async def refresh_inventory(
        self,
        changeset_id: ChangesetId,
        workspace_root: Path,
        *,
        refreshed_by: str = "operator",
    ) -> ChangesetInventoryRefreshResult:
        """Record a fresh structured inventory artifact for one changeset."""

        if self._artifact_repository is None:
            raise ValueError("artifact repository is required for inventory refresh")
        changeset = self._require_changeset(changeset_id)
        previous_inventory = self._repository.get_changeset_inventory(
            changeset.session_id,
            changeset.changeset_id,
        )
        events = self._repository.read_session_events(changeset.session_id)
        diff_summary = await DiffSummaryTool(workspace_root).execute(
            DiffSummaryArgs(
                scope=DiffSummaryScope.WORKSPACE,
                max_files=1000,
                inline_file_limit=200,
            )
        )
        diff_summary = _diff_summary_without_local_state(diff_summary)
        inventory = change_inventory_from_diff_summary(
            diff_summary,
            changeset_id=changeset.changeset_id,
            provenance_events=events,
        )
        source_digest = _workspace_diff_source_digest(workspace_root)
        content = change_inventory_artifact_json(inventory)
        artifact = self._artifact_repository.write_text_artifact(
            changeset.session_id,
            content,
            suffix=".changeset-inventory.json",
        )
        freshness = (
            ChangesetInventoryFreshness.UNKNOWN
            if source_digest.error is not None
            else ChangesetInventoryFreshness.FRESH
        )
        payloads: list[EventPayloadType] = []
        if previous_inventory is not None:
            payloads.append(
                ChangesetInventoryRefreshed(
                    changeset_id=changeset.changeset_id,
                    artifact_id=previous_inventory.artifact_id,
                    artifact_schema_version=previous_inventory.artifact_schema_version,
                    freshness=ChangesetInventoryFreshness.SUPERSEDED,
                    changed_path_count=previous_inventory.changed_path_count,
                    source_digest=previous_inventory.source_digest,
                    previous_artifact_id=previous_inventory.previous_artifact_id,
                    refreshed_by=refreshed_by,
                    risk_level=previous_inventory.risk_level,
                    risk_summary=previous_inventory.risk_summary,
                    unresolved_risk_count=previous_inventory.unresolved_risk_count,
                    accepted_risk_count=previous_inventory.accepted_risk_count,
                    task_id=previous_inventory.task_id,
                    turn_id=previous_inventory.turn_id,
                    branch_search_id=previous_inventory.branch_search_id,
                    branch_candidate_id=previous_inventory.branch_candidate_id,
                )
            )
        payloads.append(
            ChangesetInventoryRefreshed(
                changeset_id=changeset.changeset_id,
                artifact_id=artifact.artifact_id,
                artifact_schema_version=CHANGE_INVENTORY_ARTIFACT_SCHEMA_VERSION,
                freshness=freshness,
                changed_path_count=inventory.summary.changed_path_count,
                source_digest=source_digest.digest,
                previous_artifact_id=(
                    previous_inventory.artifact_id
                    if previous_inventory is not None
                    else None
                ),
                refreshed_by=refreshed_by,
                risk_level=ChangesetRiskLevel(inventory.summary.risk_level),
                risk_summary=inventory.summary.risk_summary,
                unresolved_risk_count=inventory.summary.unresolved_risk_count,
                accepted_risk_count=inventory.summary.accepted_risk_count,
                task_id=changeset.task_id,
                turn_id=changeset.turn_id,
                branch_search_id=changeset.branch_search_id,
                branch_candidate_id=changeset.branch_candidate_id,
            )
        )
        stored = self._repository.append_events(
            [
                EventEnvelope(
                    session_id=changeset.session_id,
                    sequence=0,
                    payload=payload,
                )
                for payload in payloads
            ]
        )
        return ChangesetInventoryRefreshResult(
            changeset_id=changeset.changeset_id,
            session_id=changeset.session_id,
            artifact=artifact,
            inventory=inventory,
            event=stored[-1],
            superseded_event=stored[0] if len(stored) > 1 else None,
            freshness=freshness,
            source_digest=source_digest.digest,
        )

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


class _WorkspaceSourceDigest(BaseModel):
    model_config = ConfigDict(extra="forbid")

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


def _workspace_diff_source_digest(workspace_root: Path) -> _WorkspaceSourceDigest:
    digest = hashlib.sha256()
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
            cwd=workspace_root,
            check=False,
            capture_output=True,
            timeout=10,
        )
    except FileNotFoundError:
        return _WorkspaceSourceDigest(error="git executable not found")
    except subprocess.TimeoutExpired:
        return _WorkspaceSourceDigest(error="git status timed out")
    if status.returncode != 0:
        return _WorkspaceSourceDigest(
            error=status.stderr.decode("utf-8", errors="replace").strip()
            or "git status failed"
        )
    digest.update(b"status\0")
    digest.update(_filter_status_porcelain_z(status.stdout))
    for label, command in (
        (
            b"unstaged-diff\0",
            ["git", "diff", "--no-ext-diff", "--binary", "--"],
        ),
        (
            b"staged-diff\0",
            ["git", "diff", "--cached", "--no-ext-diff", "--binary", "--"],
        ),
    ):
        result = _run_git_bytes(workspace_root, command)
        if result.error is not None:
            return _WorkspaceSourceDigest(error=result.error)
        digest.update(label)
        digest.update(result.digest_payload)
    untracked = _run_git_bytes(
        workspace_root,
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
    )
    if untracked.error is not None:
        return _WorkspaceSourceDigest(error=untracked.error)
    digest.update(b"untracked-content\0")
    for path_text in sorted(
        path.decode("utf-8", errors="replace")
        for path in untracked.digest_payload.split(b"\0")
        if path and not _is_local_state_path(path.decode("utf-8", errors="replace"))
    ):
        digest.update(path_text.encode("utf-8", errors="replace"))
        digest.update(b"\0")
        file_path = (workspace_root / path_text).resolve(strict=False)
        try:
            if file_path.is_file():
                digest.update(
                    hashlib.sha256(file_path.read_bytes()).hexdigest().encode()
                )
        except OSError as exc:
            digest.update(f"unreadable:{exc}".encode("utf-8", errors="replace"))
        digest.update(b"\0")
    return _WorkspaceSourceDigest(digest=f"sha256:{digest.hexdigest()}")


def _diff_summary_without_local_state(
    diff_summary: DiffSummaryResult,
) -> DiffSummaryResult:
    files = [
        file_summary
        for file_summary in diff_summary.files
        if not _is_local_state_path(file_summary.path)
    ]
    artifact_payload = diff_summary.artifact_payload
    if artifact_payload is not None:
        artifact_payload = DiffSummaryArtifact(
            artifact_kind=artifact_payload.artifact_kind,
            scope=artifact_payload.scope,
            path_filters=artifact_payload.path_filters,
            risk_summary=artifact_payload.risk_summary,
            files=[
                file_summary
                for file_summary in artifact_payload.files
                if not _is_local_state_path(file_summary.path)
            ],
            redaction=artifact_payload.redaction,
        )
    return diff_summary.model_copy(
        update={
            "files": files,
            "artifact_payload": artifact_payload,
            "clean": not files and artifact_payload is None,
        }
    )


def _filter_status_porcelain_z(output: bytes) -> bytes:
    filtered_entries = []
    for entry in output.split(b"\0"):
        if not entry:
            continue
        path_text = entry[3:].decode("utf-8", errors="replace")
        if not _is_local_state_path(path_text):
            filtered_entries.append(entry)
    return b"\0".join(filtered_entries) + (b"\0" if filtered_entries else b"")


def _is_local_state_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return normalized == ".glassbox" or normalized.startswith(".glassbox/")


class _GitBytesResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    digest_payload: bytes = b""
    digest: str | None = None
    error: str | None = None


def _run_git_bytes(workspace_root: Path, command: list[str]) -> _GitBytesResult:
    try:
        result = subprocess.run(
            command,
            cwd=workspace_root,
            check=False,
            capture_output=True,
            timeout=10,
        )
    except FileNotFoundError:
        return _GitBytesResult(error="git executable not found")
    except subprocess.TimeoutExpired:
        return _GitBytesResult(error=f"{' '.join(command[:3])} timed out")
    if result.returncode != 0:
        return _GitBytesResult(
            error=result.stderr.decode("utf-8", errors="replace").strip()
            or f"{' '.join(command[:3])} failed"
        )
    return _GitBytesResult(digest_payload=result.stdout)


def _inventory_status(
    changeset: ChangesetRecord,
    inventory: ChangesetInventoryRecord | None,
    *,
    workspace_root: Path | None,
) -> ChangesetInventoryStatus:
    refresh_action = f"glassbox changeset refresh {changeset.changeset_id} --cwd ."
    if inventory is None:
        return ChangesetInventoryStatus(
            freshness=ChangesetInventoryFreshness.UNKNOWN,
            stale=False,
            reason="no structured change inventory is attached yet",
            safe_next_actions=[refresh_action],
        )
    if workspace_root is None:
        return ChangesetInventoryStatus(
            freshness=inventory.freshness,
            stale=inventory.freshness
            in {
                ChangesetInventoryFreshness.STALE,
                ChangesetInventoryFreshness.SUPERSEDED,
            },
            recorded_source_digest=inventory.source_digest,
            safe_next_actions=[refresh_action],
        )
    current = _workspace_diff_source_digest(workspace_root)
    if current.error is not None:
        return ChangesetInventoryStatus(
            freshness=ChangesetInventoryFreshness.UNKNOWN,
            stale=False,
            reason=f"workspace source digest unavailable: {current.error}",
            recorded_source_digest=inventory.source_digest,
            current_source_digest=current.digest,
            safe_next_actions=[refresh_action],
        )
    if inventory.source_digest is None:
        return ChangesetInventoryStatus(
            freshness=ChangesetInventoryFreshness.UNKNOWN,
            stale=False,
            reason="latest inventory has no recorded workspace source digest",
            recorded_source_digest=None,
            current_source_digest=current.digest,
            safe_next_actions=[refresh_action],
        )
    source_digest_changed = (
        inventory.source_digest is not None
        and inventory.source_digest != current.digest
    )
    if source_digest_changed:
        return ChangesetInventoryStatus(
            freshness=ChangesetInventoryFreshness.STALE,
            stale=True,
            reason=(
                "workspace diff source digest changed since the latest inventory "
                "artifact was recorded"
            ),
            recorded_source_digest=inventory.source_digest,
            current_source_digest=current.digest,
            safe_next_actions=[refresh_action],
        )
    return ChangesetInventoryStatus(
        freshness=inventory.freshness,
        stale=inventory.freshness == ChangesetInventoryFreshness.STALE,
        recorded_source_digest=inventory.source_digest,
        current_source_digest=current.digest,
        safe_next_actions=[refresh_action],
    )


def _inventory_with_status_freshness(
    inventory: ChangesetInventoryRecord | None,
    inventory_status: ChangesetInventoryStatus,
) -> ChangesetInventoryRecord | None:
    if inventory is None or inventory.freshness == inventory_status.freshness:
        return inventory
    return inventory.model_copy(update={"freshness": inventory_status.freshness})


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
    inventory_status: ChangesetInventoryStatus,
) -> list[str]:
    limitations = [
        source.limitation for source in sources if source.limitation is not None
    ]
    if inventory is None:
        limitations.append(
            "no structured change inventory is attached yet; inspect sources first"
        )
    if inventory_status.stale:
        limitations.append(
            inventory_status.reason
            or "structured change inventory is stale against the current workspace"
        )
    elif inventory_status.reason is not None and inventory_status.freshness == (
        ChangesetInventoryFreshness.UNKNOWN
    ):
        limitations.append(inventory_status.reason)
    if changeset.risk_level.value == "high":
        summary = changeset.risk_summary or "path classification marked high risk"
        limitations.append(f"high review risk: {summary}")
    return limitations


def _detail_safe_next_actions(
    changeset: ChangesetRecord,
    inventory_status: ChangesetInventoryStatus,
) -> list[str]:
    actions = [f"glassbox changeset show {changeset.changeset_id} --cwd ."]
    if changeset.status != "archived":
        actions.extend(inventory_status.safe_next_actions)
        actions.append(
            "glassbox eval recommend PATH --cwd .  # inspect verification options"
        )
    return list(dict.fromkeys(actions))


__all__ = [
    "ChangesetActionService",
    "ChangesetDetailView",
    "ChangesetDerivationRepository",
    "ChangesetDerivationResult",
    "ChangesetDerivationService",
    "ChangesetInventoryRefreshResult",
    "ChangesetInventoryStatus",
    "ChangesetQueryService",
    "ChangesetRepository",
]
