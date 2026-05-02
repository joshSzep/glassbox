"""Runtime service for deriving and inspecting reviewable changesets."""

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from glassbox.core import ArtifactId
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
from glassbox.core import ChangesetReadinessDecided
from glassbox.core import ChangesetReadinessKind
from glassbox.core import ChangesetReadinessRecord
from glassbox.core import ChangesetReadinessState
from glassbox.core import ChangesetRecord
from glassbox.core import ChangesetReviewBriefCreated
from glassbox.core import ChangesetReviewBriefRecord
from glassbox.core import ChangesetRiskLevel
from glassbox.core import ChangesetSourceAttached
from glassbox.core import ChangesetSourceKind
from glassbox.core import ChangesetSourceRecord
from glassbox.core import ChangesetVerificationPostureRecord
from glassbox.core import ChangesetVerificationPostureUpdated
from glassbox.core import ChangesetVerificationState
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
from glassbox.core import TaskVerificationId
from glassbox.core import TaskVerificationLedgerRecord
from glassbox.core import new_changeset_id
from glassbox.runtime.change_inventory import CHANGE_INVENTORY_ARTIFACT_SCHEMA_VERSION
from glassbox.runtime.change_inventory import ChangeInventoryArtifact
from glassbox.runtime.change_inventory import change_inventory_artifact_json
from glassbox.runtime.change_inventory import change_inventory_from_diff_summary
from glassbox.runtime.changeset_topology import ChangesetTopologyImpact
from glassbox.runtime.changeset_topology import derive_changeset_topology_impacts
from glassbox.runtime.changeset_verification_readiness import (
    ChangesetVerificationReadiness,
)
from glassbox.runtime.changeset_verification_readiness import (
    derive_changeset_verification_readiness,
)
from glassbox.runtime.eval_recommendation_models import EvalRecommendationReasonGroup
from glassbox.runtime.eval_recommendation_models import EvalRecommendationReport
from glassbox.runtime.eval_recommendations import recommend_eval_change_impact
from glassbox.runtime.review_briefs import REVIEW_BRIEF_ARTIFACT_SCHEMA_VERSION
from glassbox.runtime.review_briefs import ReviewBriefArtifact
from glassbox.runtime.review_briefs import ReviewBriefEvidenceRef
from glassbox.runtime.review_briefs import ReviewBriefSection
from glassbox.runtime.review_briefs import review_brief_artifact_json
from glassbox.runtime.review_briefs import review_brief_markdown
from glassbox.runtime.workspace_profile import load_workspace_profile
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

    def list_task_verification_ledger(
        self,
        session_id: SessionId,
        task_id: TaskId,
    ) -> list[TaskVerificationLedgerRecord]: ...

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


class ChangesetVerificationRecipePreview(BaseModel):
    """One recipe row in a changeset verification plan preview."""

    model_config = ConfigDict(extra="forbid")

    recipe_id: str
    title: str
    confidence: str = "direct"
    source: str = "recipe"
    matched_paths: list[str] = Field(default_factory=list)
    component_ids: list[str] = Field(default_factory=list)
    commands: list[str] = Field(default_factory=list)
    profile_ids: list[str] = Field(default_factory=list)
    case_ids: list[str] = Field(default_factory=list)
    notes: str | None = None
    limitations: list[str] = Field(default_factory=list)


class ChangesetVerificationPlanPreview(BaseModel):
    """Preview-only verification plan for one changeset."""

    model_config = ConfigDict(extra="forbid")

    changeset_id: ChangesetId
    session_id: SessionId
    inventory_artifact_id: ArtifactId | None = None
    inventory_freshness: ChangesetInventoryFreshness
    changed_paths: list[str] = Field(default_factory=list)
    recommended_commands: list[str] = Field(default_factory=list)
    eval_profiles: list[str] = Field(default_factory=list)
    recipes: list[ChangesetVerificationRecipePreview] = Field(default_factory=list)
    topology_impacts: list[ChangesetTopologyImpact] = Field(default_factory=list)
    reason_groups: list[EvalRecommendationReasonGroup] = Field(default_factory=list)
    expected_scope: list[str] = Field(default_factory=list)
    retained_artifact_ids: list[ArtifactId] = Field(default_factory=list)
    readiness: ChangesetVerificationReadiness
    limitations: list[str] = Field(default_factory=list)
    safe_next_actions: list[str] = Field(default_factory=list)
    non_claims: list[str] = Field(default_factory=list)


class ChangesetVerificationEvidenceRecordResult(BaseModel):
    """Result of recording selected retained verification evidence."""

    model_config = ConfigDict(extra="forbid")

    changeset_id: ChangesetId
    session_id: SessionId
    selected_verification_ids: list[TaskVerificationId] = Field(default_factory=list)
    retained_artifact_ids: list[ArtifactId] = Field(default_factory=list)
    readiness: ChangesetVerificationReadiness
    event: EventEnvelope


class ChangesetReviewBriefGenerationResult(BaseModel):
    """Result of generating one deterministic review brief artifact."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    changeset_id: ChangesetId
    session_id: SessionId
    artifact: StoredArtifact
    brief: ReviewBriefArtifact
    markdown: str
    event: EventEnvelope
    readiness_event: EventEnvelope
    limitations: list[str] = Field(default_factory=list)


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


class ChangesetVerificationService:
    """Preview and record changeset verification posture from retained evidence."""

    def __init__(
        self,
        repository: ChangesetRepository,
        artifact_repository: ArtifactRepository | None = None,
    ) -> None:
        self._repository = repository
        self._artifact_repository = artifact_repository

    def preview_plan(
        self,
        changeset_id: ChangesetId,
        workspace_root: Path,
    ) -> ChangesetVerificationPlanPreview:
        changeset = self._require_changeset(changeset_id)
        inventory_record = self._repository.get_changeset_inventory(
            changeset.session_id,
            changeset.changeset_id,
        )
        inventory, inventory_limitations = self._load_inventory_artifact(
            changeset.session_id,
            inventory_record,
        )
        inventory_status = _inventory_status(
            changeset,
            inventory_record,
            workspace_root=workspace_root,
        )
        changed_paths = _inventory_paths_for_preview(inventory)
        recommendation, recommendation_limitations = _recommendation_for_preview(
            workspace_root,
            changed_paths,
        )
        topology_impacts, topology_limitations = derive_changeset_topology_impacts(
            workspace_root=workspace_root,
            changed_paths=changed_paths,
        )
        limitations = [
            *inventory_limitations,
            *recommendation_limitations,
            *topology_limitations,
            *(
                [inventory_status.reason]
                if inventory_status.reason is not None
                and inventory_status.freshness != ChangesetInventoryFreshness.FRESH
                else []
            ),
        ]
        ledger = self._task_ledger_for_changeset(changeset)
        inventory_freshness = inventory_status.freshness
        readiness = derive_changeset_verification_readiness(
            inventory=inventory,
            inventory_freshness=inventory_freshness,
            inventory_sequence=(
                inventory_record.last_sequence if inventory_record is not None else None
            ),
            task_ledger=ledger,
            eval_recommendation=recommendation,
            workspace_profile=load_workspace_profile(workspace_root),
        )
        retained_artifact_ids = _artifact_ids_from_readiness(readiness)
        return ChangesetVerificationPlanPreview(
            changeset_id=changeset.changeset_id,
            session_id=changeset.session_id,
            inventory_artifact_id=(
                inventory_record.artifact_id if inventory_record is not None else None
            ),
            inventory_freshness=inventory_freshness,
            changed_paths=changed_paths,
            recommended_commands=_preview_commands(
                readiness,
                recommendation,
            ),
            eval_profiles=_eval_profile_ids_for_preview(recommendation),
            recipes=_recipe_previews(recommendation),
            topology_impacts=topology_impacts,
            reason_groups=(
                recommendation.reason_groups if recommendation is not None else []
            ),
            expected_scope=changed_paths,
            retained_artifact_ids=retained_artifact_ids,
            readiness=readiness,
            limitations=limitations,
            safe_next_actions=readiness.safe_next_actions,
            non_claims=[
                *readiness.non_claims,
                "verification plan preview does not run commands",
                (
                    "publish, deploy, push, and upload commands are not "
                    "recommended as verification"
                ),
            ],
        )

    def record_existing_evidence(
        self,
        changeset_id: ChangesetId,
        workspace_root: Path,
        *,
        task_id: TaskId | None = None,
        verification_id: TaskVerificationId | None = None,
    ) -> ChangesetVerificationEvidenceRecordResult:
        changeset = self._require_changeset(changeset_id)
        resolved_task_id = task_id or changeset.task_id
        if resolved_task_id is None:
            raise ValueError(
                "task_id is required when the changeset is not task-backed"
            )
        ledger = self._repository.list_task_verification_ledger(
            changeset.session_id,
            resolved_task_id,
        )
        if verification_id is not None:
            ledger = [
                entry for entry in ledger if entry.verification_id == verification_id
            ]
        if not ledger:
            raise ValueError("no retained task verification evidence matched")
        inventory_record = self._repository.get_changeset_inventory(
            changeset.session_id,
            changeset.changeset_id,
        )
        inventory, _limitations = self._load_inventory_artifact(
            changeset.session_id,
            inventory_record,
        )
        inventory_status = _inventory_status(
            changeset,
            inventory_record,
            workspace_root=workspace_root,
        )
        recommendation, _limitations = _recommendation_for_preview(
            workspace_root,
            _inventory_paths_for_preview(inventory),
        )
        readiness = derive_changeset_verification_readiness(
            inventory=inventory,
            inventory_freshness=inventory_status.freshness,
            inventory_sequence=(
                inventory_record.last_sequence if inventory_record is not None else None
            ),
            task_ledger=ledger,
            eval_recommendation=recommendation,
            workspace_profile=load_workspace_profile(workspace_root),
        )
        selected = sorted(ledger, key=lambda entry: entry.last_sequence)
        primary = selected[-1]
        retained_artifact_ids = _artifact_ids_from_readiness(readiness)
        stored = self._repository.append_events(
            [
                EventEnvelope(
                    session_id=changeset.session_id,
                    sequence=0,
                    payload=ChangesetVerificationPostureUpdated(
                        changeset_id=changeset.changeset_id,
                        state=readiness.state,
                        summary=readiness.summary,
                        verification_id=primary.verification_id,
                        artifact_id=primary.latest_artifact_id
                        or primary.latest_failed_artifact_id,
                        task_id=resolved_task_id,
                        stale_count=readiness.stale_count,
                        missing_count=readiness.missing_count,
                        failed_count=readiness.failed_count,
                        accepted_risk_count=readiness.accepted_risk_count,
                    ),
                )
            ]
        )
        return ChangesetVerificationEvidenceRecordResult(
            changeset_id=changeset.changeset_id,
            session_id=changeset.session_id,
            selected_verification_ids=[entry.verification_id for entry in selected],
            retained_artifact_ids=retained_artifact_ids,
            readiness=readiness,
            event=stored[0],
        )

    def _task_ledger_for_changeset(
        self,
        changeset: ChangesetRecord,
    ) -> list[TaskVerificationLedgerRecord]:
        if changeset.task_id is None:
            return []
        return self._repository.list_task_verification_ledger(
            changeset.session_id,
            changeset.task_id,
        )

    def _load_inventory_artifact(
        self,
        session_id: SessionId,
        inventory_record: ChangesetInventoryRecord | None,
    ) -> tuple[ChangeInventoryArtifact | None, list[str]]:
        if inventory_record is None:
            return None, ["no structured change inventory is attached yet"]
        if self._artifact_repository is None:
            return None, ["artifact repository is unavailable"]
        try:
            content = self._artifact_repository.read_text_artifact(
                _changeset_inventory_artifact_path(
                    session_id,
                    inventory_record.artifact_id,
                )
            )
            return ChangeInventoryArtifact.model_validate_json(content), []
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return None, [f"change inventory artifact could not be read: {exc}"]

    def _require_changeset(self, changeset_id: ChangesetId) -> ChangesetRecord:
        changeset = self._repository.get_changeset(changeset_id)
        if changeset is None:
            raise ValueError(f"unknown changeset: {changeset_id}")
        return changeset


class ChangesetReviewBriefService:
    """Generate reviewer-safe briefs from deterministic changeset evidence."""

    def __init__(
        self,
        repository: ChangesetRepository,
        artifact_repository: ArtifactRepository | None = None,
    ) -> None:
        self._repository = repository
        self._artifact_repository = artifact_repository

    def generate(
        self,
        changeset_id: ChangesetId,
        workspace_root: Path,
        *,
        created_by: str = "operator",
    ) -> ChangesetReviewBriefGenerationResult:
        """Generate and retain one redacted review brief for a changeset."""

        if self._artifact_repository is None:
            raise ValueError("artifact repository is required for review briefs")
        changeset = self._require_changeset(changeset_id)
        sources = self._repository.list_changeset_sources(
            changeset.session_id,
            changeset.changeset_id,
        )
        inventory_record = self._repository.get_changeset_inventory(
            changeset.session_id,
            changeset.changeset_id,
        )
        verification_posture = self._repository.get_changeset_verification_posture(
            changeset.session_id,
            changeset.changeset_id,
        )
        inventory, inventory_limitations = self._load_inventory_artifact(
            changeset.session_id,
            inventory_record,
        )
        inventory_status = _inventory_status(
            changeset,
            inventory_record,
            workspace_root=workspace_root,
        )
        verification_plan = ChangesetVerificationService(
            self._repository,
            self._artifact_repository,
        ).preview_plan(changeset.changeset_id, workspace_root)
        limitations = _review_brief_limitations(
            sources=sources,
            inventory=inventory,
            inventory_status=inventory_status,
            inventory_limitations=inventory_limitations,
            verification_plan=verification_plan,
        )
        review_state, blockers = _review_readiness_state(
            inventory_status=inventory_status,
            verification_plan=verification_plan,
            changeset=changeset,
        )
        brief = _review_brief_artifact(
            changeset=changeset,
            sources=sources,
            inventory_record=inventory_record,
            inventory=inventory,
            inventory_status=inventory_status,
            verification_posture=verification_posture,
            verification_plan=verification_plan,
            limitations=limitations,
        )
        content = review_brief_artifact_json(brief)
        artifact = self._artifact_repository.write_text_artifact(
            changeset.session_id,
            content,
            suffix=".changeset-review-brief.json",
        )
        stored = self._repository.append_events(
            [
                EventEnvelope(
                    session_id=changeset.session_id,
                    sequence=0,
                    payload=ChangesetReviewBriefCreated(
                        changeset_id=changeset.changeset_id,
                        artifact_id=artifact.artifact_id,
                        artifact_schema_version=REVIEW_BRIEF_ARTIFACT_SCHEMA_VERSION,
                        render_targets=brief.render_targets,
                        inventory_artifact_id=(
                            inventory_record.artifact_id
                            if inventory_record is not None
                            else None
                        ),
                        verification_id=(
                            verification_posture.verification_id
                            if verification_posture is not None
                            else None
                        ),
                        task_id=changeset.task_id,
                        turn_id=changeset.turn_id,
                        created_by=created_by,
                        redacted=brief.redacted,
                        local_only=brief.local_only,
                    ),
                ),
                EventEnvelope(
                    session_id=changeset.session_id,
                    sequence=0,
                    payload=ChangesetReadinessDecided(
                        changeset_id=changeset.changeset_id,
                        readiness_kind=ChangesetReadinessKind.REVIEW,
                        state=review_state,
                        reason=_review_readiness_reason(review_state, blockers),
                        blockers=blockers,
                        safe_next_actions=brief.safe_inspection_commands,
                        inventory_artifact_id=(
                            inventory_record.artifact_id
                            if inventory_record is not None
                            else None
                        ),
                        review_brief_artifact_id=artifact.artifact_id,
                        verification_id=(
                            verification_posture.verification_id
                            if verification_posture is not None
                            else None
                        ),
                        task_id=changeset.task_id,
                        turn_id=changeset.turn_id,
                        accepted_risk_count=changeset.accepted_risk_count,
                        decided_by=created_by,
                    ),
                ),
            ]
        )
        return ChangesetReviewBriefGenerationResult(
            changeset_id=changeset.changeset_id,
            session_id=changeset.session_id,
            artifact=artifact,
            brief=brief,
            markdown=review_brief_markdown(brief),
            event=stored[0],
            readiness_event=stored[1],
            limitations=limitations,
        )

    def _load_inventory_artifact(
        self,
        session_id: SessionId,
        inventory_record: ChangesetInventoryRecord | None,
    ) -> tuple[ChangeInventoryArtifact | None, list[str]]:
        if inventory_record is None:
            return None, ["no structured change inventory is attached yet"]
        if self._artifact_repository is None:
            return None, ["artifact repository is unavailable"]
        try:
            content = self._artifact_repository.read_text_artifact(
                _changeset_inventory_artifact_path(
                    session_id,
                    inventory_record.artifact_id,
                )
            )
            return ChangeInventoryArtifact.model_validate_json(content), []
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return None, [f"change inventory artifact could not be read: {exc}"]

    def _require_changeset(self, changeset_id: ChangesetId) -> ChangesetRecord:
        changeset = self._repository.get_changeset(changeset_id)
        if changeset is None:
            raise ValueError(f"unknown changeset: {changeset_id}")
        return changeset


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


def _changeset_inventory_artifact_path(
    session_id: SessionId,
    artifact_id: ArtifactId,
) -> Path:
    return (
        Path(".glassbox")
        / "sessions"
        / str(session_id)
        / "artifacts"
        / f"{artifact_id}.changeset-inventory.json"
    )


def _inventory_paths_for_preview(
    inventory: ChangeInventoryArtifact | None,
) -> list[str]:
    if inventory is None:
        return []
    return [entry.path for entry in inventory.paths[:100]]


def _safe_eval_recommendation(
    recommendation: EvalRecommendationReport | None,
) -> EvalRecommendationReport | None:
    if recommendation is None:
        return None
    recipes = [
        recipe.model_copy(
            update={
                "commands": [
                    command
                    for command in recipe.commands
                    if _is_safe_verification_command(command)
                ]
            }
        )
        for recipe in recommendation.recipes
    ]
    return recommendation.model_copy(
        update={
            "suggested_commands": [
                command
                for command in recommendation.suggested_commands
                if _is_safe_verification_command(command)
            ],
            "fallback_policy_commands": [
                command
                for command in recommendation.fallback_policy_commands
                if _is_safe_verification_command(command)
            ],
            "recipes": recipes,
        }
    )


def _recommendation_for_preview(
    workspace_root: Path,
    changed_paths: list[str],
) -> tuple[EvalRecommendationReport | None, list[str]]:
    if not changed_paths:
        return None, []
    try:
        return (
            _safe_eval_recommendation(
                recommend_eval_change_impact(
                    workspace_root,
                    touched_paths=changed_paths,
                )
            ),
            [],
        )
    except ValueError as exc:
        return None, [f"eval recommendation unavailable: {exc}"]


def _preview_commands(
    readiness: ChangesetVerificationReadiness,
    recommendation: EvalRecommendationReport | None,
) -> list[str]:
    commands = (
        list(recommendation.suggested_commands) if recommendation is not None else []
    )
    for requirement in readiness.requirements:
        if requirement.command:
            commands.append(" ".join(requirement.command))
    return [
        command
        for command in dict.fromkeys(commands)
        if _is_safe_verification_command(command)
    ]


def _is_safe_verification_command(command: str) -> bool:
    tokens = {part.lower() for part in command.replace(";", " ").split()}
    blocked = {
        "deploy",
        "publish",
        "push",
        "upload",
        "release",
        "release:publish",
    }
    return not tokens.intersection(blocked)


def _eval_profile_ids_for_preview(
    recommendation: EvalRecommendationReport | None,
) -> list[str]:
    if recommendation is None:
        return []
    profile_ids = [profile.profile_id for profile in recommendation.profiles]
    for recipe in recommendation.recipes:
        profile_ids.extend(recipe.profile_ids)
    return list(dict.fromkeys(profile_ids))


def _recipe_previews(
    recommendation: EvalRecommendationReport | None,
) -> list[ChangesetVerificationRecipePreview]:
    if recommendation is None:
        return []
    return [
        ChangesetVerificationRecipePreview(
            recipe_id=recipe.recipe_id,
            title=recipe.title,
            confidence=recipe.confidence,
            source=recipe.source,
            matched_paths=recipe.matched_paths,
            component_ids=recipe.component_ids,
            commands=recipe.commands,
            profile_ids=recipe.profile_ids,
            case_ids=recipe.case_ids,
            notes=recipe.notes,
            limitations=recipe.limitations,
        )
        for recipe in recommendation.recipes
    ]


def _artifact_ids_from_readiness(
    readiness: ChangesetVerificationReadiness,
) -> list[ArtifactId]:
    artifact_ids = [
        requirement.artifact_id
        for requirement in readiness.requirements
        if requirement.artifact_id is not None
    ]
    return list(dict.fromkeys(artifact_ids))


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


def _review_brief_artifact(
    *,
    changeset: ChangesetRecord,
    sources: list[ChangesetSourceRecord],
    inventory_record: ChangesetInventoryRecord | None,
    inventory: ChangeInventoryArtifact | None,
    inventory_status: ChangesetInventoryStatus,
    verification_posture: ChangesetVerificationPostureRecord | None,
    verification_plan: ChangesetVerificationPlanPreview,
    limitations: list[str],
) -> ReviewBriefArtifact:
    return ReviewBriefArtifact(
        changeset_id=changeset.changeset_id,
        session_id=changeset.session_id,
        task_id=changeset.task_id,
        branch_search_id=changeset.branch_search_id,
        branch_candidate_id=changeset.branch_candidate_id,
        local_only=_review_brief_local_only(
            sources,
            inventory_record,
            verification_posture,
        ),
        objective=changeset.objective,
        change_summary=_review_brief_change_summary(changeset),
        changed_file_inventory=_review_brief_inventory_section(
            inventory_record,
            inventory,
            inventory_status,
        ),
        affected_subsystems=_review_brief_topology_section(verification_plan),
        provenance=_review_brief_provenance_section(sources, inventory),
        verification=_review_brief_verification_section(
            verification_posture,
            verification_plan,
        ),
        branch_candidate_rationale=_review_brief_branch_candidate_section(
            changeset,
            sources,
        ),
        risks=_review_brief_risk_section(changeset, inventory),
        non_claims=[
            "review brief is a deterministic summary, not proof",
            "raw command output is not included",
            "raw diffs and file contents are not included",
            "commit, push, PR, and merge remain explicit operator actions",
        ],
        reviewer_checklist=_reviewer_checklist(changeset, verification_plan),
        safe_inspection_commands=_review_brief_safe_commands(
            changeset,
            verification_plan,
        ),
        limitations=limitations,
    )


def _review_brief_change_summary(
    changeset: ChangesetRecord,
) -> ReviewBriefSection:
    summary = changeset.summary or "No operator-written changeset summary is attached."
    body = (
        f"{summary} Status is {changeset.status}. Risk is "
        f"{changeset.risk_level.value} with "
        f"{changeset.unresolved_risk_count} unresolved and "
        f"{changeset.accepted_risk_count} accepted risk item(s)."
    )
    return ReviewBriefSection(
        title="Change Summary",
        body=body,
        evidence_refs=[
            ReviewBriefEvidenceRef(
                kind="changeset",
                identifier=str(changeset.changeset_id),
                summary="changeset projection supplied objective, summary, and risk",
            )
        ],
    )


def _review_brief_inventory_section(
    inventory_record: ChangesetInventoryRecord | None,
    inventory: ChangeInventoryArtifact | None,
    inventory_status: ChangesetInventoryStatus,
) -> ReviewBriefSection:
    if inventory_record is None:
        return ReviewBriefSection(
            title="Changed-File Inventory",
            body="No structured change inventory is attached yet.",
        )
    if inventory is None:
        body = (
            f"Inventory artifact {inventory_record.artifact_id} is projected with "
            f"{inventory_record.changed_path_count} changed path(s), but the "
            "artifact could not be loaded for path details."
        )
    else:
        paths = ", ".join(entry.path for entry in inventory.paths[:10])
        if len(inventory.paths) > 10:
            paths = f"{paths}, and {len(inventory.paths) - 10} more"
        body = (
            f"Inventory records {inventory.summary.changed_path_count} changed "
            f"path(s), {inventory.summary.test_path_count} test path(s), "
            f"{inventory.summary.docs_path_count} docs path(s), and "
            f"{inventory.summary.policy_sensitive_path_count} policy-sensitive "
            f"path(s). Freshness is {inventory_status.freshness.value}."
        )
        if paths:
            body = f"{body} Included paths: {paths}."
    if inventory_status.reason is not None:
        body = f"{body} Freshness note: {inventory_status.reason}."
    return ReviewBriefSection(
        title="Changed-File Inventory",
        body=body,
        evidence_refs=[
            ReviewBriefEvidenceRef(
                kind="inventory",
                identifier=str(inventory_record.artifact_id),
                artifact_id=inventory_record.artifact_id,
                summary=(
                    f"latest inventory has {inventory_record.changed_path_count} "
                    f"path(s) and freshness {inventory_status.freshness.value}"
                ),
                local_only=True,
            )
        ],
    )


def _review_brief_provenance_section(
    sources: list[ChangesetSourceRecord],
    inventory: ChangeInventoryArtifact | None,
) -> ReviewBriefSection:
    source_summary = "; ".join(
        f"{source.source_kind.value}: {source.reason}" for source in sources[:8]
    )
    if not source_summary:
        source_summary = "No changeset source records are attached."
    provenance_body = source_summary
    if inventory is not None:
        provenance_body = (
            f"{provenance_body} Path provenance counts: "
            f"{inventory.summary.provenance_direct_path_count} direct, "
            f"{inventory.summary.provenance_inferred_path_count} inferred, "
            f"{inventory.summary.provenance_unknown_path_count} unknown."
        )
    return ReviewBriefSection(
        title="Provenance",
        body=provenance_body,
        evidence_refs=[
            ReviewBriefEvidenceRef(
                kind="provenance",
                identifier=f"source-sequence-{source.last_sequence}",
                summary=f"{source.source_kind.value}: {source.reason}",
                artifact_id=source.artifact_id,
                local_only=source.artifact_id is not None,
            )
            for source in sources[:8]
        ],
    )


def _review_brief_topology_section(
    verification_plan: ChangesetVerificationPlanPreview,
) -> ReviewBriefSection | None:
    impacts = verification_plan.topology_impacts
    if not impacts:
        return None
    lines = []
    refs = []
    for impact in impacts[:8]:
        owners = (
            f"; owners {', '.join(impact.ownership_hints)}"
            if impact.ownership_hints
            else ""
        )
        tests = f"; tests {', '.join(impact.test_roots)}" if impact.test_roots else ""
        deps = (
            f"; dependencies {', '.join(impact.dependency_hints[:4])}"
            if impact.dependency_hints
            else ""
        )
        lines.append(
            f"{impact.name} ({impact.kind}, {impact.root_path}) matched "
            f"{len(impact.matched_paths)} path(s); topology is "
            f"{impact.topology_freshness}{owners}{tests}{deps}."
        )
        refs.append(
            ReviewBriefEvidenceRef(
                kind="provenance",
                identifier=impact.component_id,
                summary=(
                    f"{impact.name} matched {len(impact.matched_paths)} "
                    f"path(s) with {impact.recommendation_posture} topology posture"
                ),
            )
        )
    body = " ".join(lines)
    return ReviewBriefSection(
        title="Affected Subsystems",
        body=body,
        evidence_refs=refs,
    )


def _review_brief_verification_section(
    verification_posture: ChangesetVerificationPostureRecord | None,
    verification_plan: ChangesetVerificationPlanPreview,
) -> ReviewBriefSection:
    readiness = verification_plan.readiness
    body = (
        f"Readiness is {readiness.state.value}: {readiness.summary}. "
        f"Counts are {readiness.failed_count} failed, {readiness.stale_count} stale, "
        f"{readiness.missing_count} missing, and "
        f"{readiness.accepted_risk_count} accepted risk."
    )
    if verification_posture is None:
        body = f"{body} No retained changeset verification posture is attached yet."
    else:
        body = (
            f"{body} Latest retained posture is "
            f"{verification_posture.state.value}: {verification_posture.summary}."
        )
    refs = []
    if verification_posture is not None:
        refs.append(
            ReviewBriefEvidenceRef(
                kind="verification",
                identifier=str(
                    verification_posture.verification_id
                    or verification_posture.last_sequence
                ),
                verification_id=verification_posture.verification_id,
                artifact_id=verification_posture.artifact_id,
                summary=verification_posture.summary,
                local_only=verification_posture.artifact_id is not None,
            )
        )
    refs.extend(
        ReviewBriefEvidenceRef(
            kind="verification",
            identifier=requirement.requirement_id,
            verification_id=requirement.verification_id,
            artifact_id=requirement.artifact_id,
            summary=f"{requirement.state.value}: {requirement.reason}",
            local_only=requirement.artifact_id is not None,
        )
        for requirement in readiness.requirements[:8]
    )
    return ReviewBriefSection(title="Verification", body=body, evidence_refs=refs)


def _review_brief_branch_candidate_section(
    changeset: ChangesetRecord,
    sources: list[ChangesetSourceRecord],
) -> ReviewBriefSection | None:
    if changeset.branch_search_id is None and changeset.branch_candidate_id is None:
        return None
    candidate_sources = [
        source
        for source in sources
        if source.source_kind == ChangesetSourceKind.BRANCH_SEARCH_CANDIDATE
    ]
    body = (
        f"Branch search {changeset.branch_search_id} selected candidate "
        f"{changeset.branch_candidate_id}. No workspace mutation is claimed by "
        "this review brief."
    )
    return ReviewBriefSection(
        title="Branch-Candidate Rationale",
        body=body,
        evidence_refs=[
            ReviewBriefEvidenceRef(
                kind="branch_candidate",
                identifier=str(source.branch_candidate_id or source.last_sequence),
                artifact_id=source.artifact_id,
                summary=source.reason,
                local_only=source.artifact_id is not None,
            )
            for source in candidate_sources
        ],
    )


def _review_brief_risk_section(
    changeset: ChangesetRecord,
    inventory: ChangeInventoryArtifact | None,
) -> ReviewBriefSection:
    body = (
        f"Changeset risk is {changeset.risk_level.value}. "
        f"{changeset.unresolved_risk_count} unresolved and "
        f"{changeset.accepted_risk_count} accepted risk item(s) are projected."
    )
    if changeset.risk_summary is not None:
        body = f"{body} Summary: {changeset.risk_summary}."
    if inventory is not None:
        body = (
            f"{body} Inventory risk counts: "
            f"{inventory.summary.high_risk_path_count} high, "
            f"{inventory.summary.medium_risk_path_count} medium, "
            f"{inventory.summary.low_risk_path_count} low."
        )
    return ReviewBriefSection(
        title="Risks",
        body=body,
        evidence_refs=[
            ReviewBriefEvidenceRef(
                kind="risk",
                identifier=str(changeset.changeset_id),
                summary=body,
            )
        ],
    )


def _reviewer_checklist(
    changeset: ChangesetRecord,
    verification_plan: ChangesetVerificationPlanPreview,
) -> list[str]:
    checklist = [
        "Inspect the changed-file inventory before reviewing implementation details",
        "Review provenance confidence for changed paths with unknown source evidence",
        "Inspect verification readiness and retained evidence references",
    ]
    if verification_plan.readiness.state != ChangesetVerificationState.PASSED:
        checklist.append("Resolve missing, stale, failed, or accepted-risk checks")
    if changeset.unresolved_risk_count > 0:
        checklist.append("Review unresolved risk classification before commit prep")
    return checklist


def _review_brief_safe_commands(
    changeset: ChangesetRecord,
    verification_plan: ChangesetVerificationPlanPreview,
) -> list[str]:
    commands = [
        f"glassbox changeset show {changeset.changeset_id} --cwd .",
        f"glassbox changeset verification-plan {changeset.changeset_id} --cwd .",
        f"glassbox changeset brief {changeset.changeset_id} --cwd . --json",
    ]
    commands.extend(verification_plan.safe_next_actions)
    return list(dict.fromkeys(commands))


def _review_brief_local_only(
    sources: list[ChangesetSourceRecord],
    inventory_record: ChangesetInventoryRecord | None,
    verification_posture: ChangesetVerificationPostureRecord | None,
) -> bool:
    return (
        inventory_record is not None
        or verification_posture is not None
        or any(source.artifact_id is not None for source in sources)
    )


def _review_brief_limitations(
    *,
    sources: list[ChangesetSourceRecord],
    inventory: ChangeInventoryArtifact | None,
    inventory_status: ChangesetInventoryStatus,
    inventory_limitations: list[str],
    verification_plan: ChangesetVerificationPlanPreview,
) -> list[str]:
    limitations = [
        source.limitation for source in sources if source.limitation is not None
    ]
    limitations.extend(inventory_limitations)
    if inventory_status.reason is not None:
        limitations.append(inventory_status.reason)
    if inventory is not None:
        limitations.extend(inventory.limitations)
    limitations.extend(verification_plan.limitations)
    if verification_plan.readiness.state != ChangesetVerificationState.PASSED:
        limitations.append(
            f"verification readiness is {verification_plan.readiness.state.value}"
        )
    return list(dict.fromkeys(limitations))


def _review_readiness_state(
    *,
    inventory_status: ChangesetInventoryStatus,
    verification_plan: ChangesetVerificationPlanPreview,
    changeset: ChangesetRecord,
) -> tuple[ChangesetReadinessState, list[str]]:
    blockers: list[str] = []
    readiness = verification_plan.readiness
    if inventory_status.stale:
        blockers.append(
            inventory_status.reason
            or "structured change inventory is stale against the current workspace"
        )
        return ChangesetReadinessState.STALE_INVENTORY, blockers
    if inventory_status.freshness == ChangesetInventoryFreshness.UNKNOWN:
        blockers.append(
            inventory_status.reason
            or "structured change inventory freshness is unknown"
        )
        return ChangesetReadinessState.STALE_INVENTORY, blockers
    if readiness.state == ChangesetVerificationState.FAILED:
        blockers.append(readiness.summary)
        return ChangesetReadinessState.FAILED_CHECKS, blockers
    if readiness.state == ChangesetVerificationState.STALE:
        blockers.append(readiness.summary)
        return ChangesetReadinessState.STALE_INVENTORY, blockers
    if readiness.state in {
        ChangesetVerificationState.MISSING,
        ChangesetVerificationState.PLANNED,
        ChangesetVerificationState.RUNNING,
        ChangesetVerificationState.SKIPPED,
    }:
        blockers.append(readiness.summary)
        return ChangesetReadinessState.NEEDS_VERIFICATION, blockers
    if readiness.state == ChangesetVerificationState.ACCEPTED_WITH_RISK:
        return ChangesetReadinessState.ACCEPTED_WITH_RISK, [readiness.summary]
    return ChangesetReadinessState.READY, blockers


def _review_readiness_reason(
    state: ChangesetReadinessState,
    blockers: list[str],
) -> str:
    if blockers:
        return "; ".join(blockers)
    if state == ChangesetReadinessState.READY:
        return "deterministic changeset evidence is ready for reviewer inspection"
    return f"review readiness is {state.value}"


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
    "ChangesetReviewBriefGenerationResult",
    "ChangesetReviewBriefService",
    "ChangesetVerificationEvidenceRecordResult",
    "ChangesetVerificationPlanPreview",
    "ChangesetVerificationRecipePreview",
    "ChangesetVerificationService",
]
