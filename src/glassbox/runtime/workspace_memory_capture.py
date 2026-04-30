"""Operator-reviewed workspace memory capture service."""

from collections.abc import Sequence
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import Protocol

from glassbox.core.events import EventEnvelope
from glassbox.core.ids import SessionId
from glassbox.core.ids import WorkspaceMemoryId
from glassbox.core.models import RuntimeNoteRecord
from glassbox.core.models import TaskRecord
from glassbox.core.models import WorkspaceMemoryEntry
from glassbox.core.types import WorkspaceMemoryKind
from glassbox.runtime.workspace_memory_candidates import MemoryExtractionPolicy
from glassbox.runtime.workspace_memory_candidates import ModelMemorySuggestion
from glassbox.runtime.workspace_memory_candidates import WorkspaceMemoryCandidate
from glassbox.runtime.workspace_memory_candidates import candidate_is_useful
from glassbox.runtime.workspace_memory_candidates import dedupe_candidates
from glassbox.runtime.workspace_memory_candidates import filter_stale_candidates
from glassbox.runtime.workspace_memory_commits import build_confirm_candidate_events
from glassbox.runtime.workspace_memory_commits import build_merge_candidate_events
from glassbox.runtime.workspace_memory_commits import build_operator_memory_events
from glassbox.runtime.workspace_memory_commits import build_reject_candidate_event
from glassbox.runtime.workspace_memory_extraction import confirmed_fix_candidates
from glassbox.runtime.workspace_memory_extraction import excluded_candidate_ids
from glassbox.runtime.workspace_memory_extraction import long_run_checkpoint_candidates
from glassbox.runtime.workspace_memory_extraction import long_run_compaction_candidates
from glassbox.runtime.workspace_memory_extraction import (
    long_run_verification_candidates,
)
from glassbox.runtime.workspace_memory_extraction import model_assisted_candidates
from glassbox.runtime.workspace_memory_extraction import repeated_failure_candidates
from glassbox.runtime.workspace_memory_extraction import runtime_note_candidates
from glassbox.runtime.workspace_memory_extraction import stable_command_candidates
from glassbox.runtime.workspace_memory_extraction import task_outcome_candidates
from glassbox.runtime.workspace_memory_redaction import redact_sensitive_text


class WorkspaceMemoryCaptureRepository(Protocol):
    """Repository methods used by the memory capture service."""

    def get_session(self, session_id: SessionId): ...

    def list_runtime_notes(
        self,
        session_id: SessionId,
        *,
        include_inherited: bool = True,
    ) -> list[RuntimeNoteRecord]: ...

    def list_tasks(
        self,
        *,
        session_id: SessionId | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[TaskRecord]: ...

    def read_session_events(self, session_id: SessionId) -> list[EventEnvelope]: ...

    def append_event(self, event: EventEnvelope) -> EventEnvelope: ...

    def append_events(self, events: Sequence[EventEnvelope]) -> list[EventEnvelope]: ...

    def get_workspace_memory(
        self,
        memory_id: WorkspaceMemoryId,
    ) -> WorkspaceMemoryEntry | None: ...


class WorkspaceMemoryCaptureService:
    """Generate and commit operator-confirmed workspace memory."""

    def __init__(self, repository: WorkspaceMemoryCaptureRepository) -> None:
        self._repository = repository

    def list_candidates(
        self,
        session_id: SessionId,
        *,
        limit: int | None = None,
        policy: MemoryExtractionPolicy | None = None,
        model_suggestions: Sequence[ModelMemorySuggestion] = (),
        now: datetime | None = None,
    ) -> list[WorkspaceMemoryCandidate]:
        self._ensure_session_exists(session_id)
        extraction_policy = policy or MemoryExtractionPolicy(max_candidates=limit)
        if not extraction_policy.enabled:
            return []
        excluded_ids = excluded_candidate_ids(self._repository, session_id)
        candidate_limit = limit or extraction_policy.max_candidates
        candidates = dedupe_candidates(
            [
                candidate
                for candidate in [
                    *runtime_note_candidates(self._repository, session_id),
                    *task_outcome_candidates(self._repository, session_id),
                    *stable_command_candidates(self._repository, session_id),
                    *repeated_failure_candidates(self._repository, session_id),
                    *confirmed_fix_candidates(self._repository, session_id),
                    *long_run_checkpoint_candidates(self._repository, session_id),
                    *long_run_compaction_candidates(self._repository, session_id),
                    *long_run_verification_candidates(self._repository, session_id),
                    *model_assisted_candidates(
                        session_id,
                        model_suggestions,
                        extraction_policy,
                    ),
                ]
                if candidate.candidate_id not in excluded_ids
                and candidate_is_useful(candidate)
            ]
        )
        candidates = filter_stale_candidates(
            candidates,
            now=now or datetime.now(UTC),
            max_age=timedelta(days=extraction_policy.max_age_days),
        )
        return candidates if candidate_limit is None else candidates[:candidate_limit]

    def list_model_assisted_candidates(
        self,
        session_id: SessionId,
        suggestions: Sequence[ModelMemorySuggestion],
        *,
        policy: MemoryExtractionPolicy | None = None,
    ) -> list[WorkspaceMemoryCandidate]:
        """Turn model suggestions into review-only candidates, never memory."""

        extraction_policy = policy or MemoryExtractionPolicy(allow_model_assisted=True)
        self._ensure_session_exists(session_id)
        if not extraction_policy.enabled:
            return []
        return dedupe_candidates(
            [
                candidate
                for candidate in model_assisted_candidates(
                    session_id,
                    suggestions,
                    extraction_policy.model_copy(update={"allow_model_assisted": True}),
                )
                if candidate_is_useful(candidate)
            ]
        )

    def confirm_candidate(
        self,
        session_id: SessionId,
        candidate_id: str,
        *,
        confirmed_by: str = "operator",
        memory_id: WorkspaceMemoryId | None = None,
        kind: WorkspaceMemoryKind | None = None,
        content: str | None = None,
        summary: str | None = None,
        tags: list[str] | None = None,
    ) -> WorkspaceMemoryEntry:
        candidate = self._require_candidate(session_id, candidate_id)
        resolved_memory_id, events = build_confirm_candidate_events(
            session_id,
            candidate,
            confirmed_by=confirmed_by,
            memory_id=memory_id,
            kind=kind,
            content=content,
            summary=summary,
            tags=tags,
        )
        self._repository.append_events(events)
        return self._require_projected_memory(resolved_memory_id)

    def merge_candidate(
        self,
        session_id: SessionId,
        candidate_id: str,
        memory_id: WorkspaceMemoryId,
        *,
        merged_by: str = "operator",
    ) -> WorkspaceMemoryEntry:
        candidate = self._require_candidate(session_id, candidate_id)
        existing = self._repository.get_workspace_memory(memory_id)
        if existing is None:
            raise ValueError(f"unknown workspace memory: {memory_id}")
        self._repository.append_events(
            build_merge_candidate_events(
                session_id,
                candidate,
                existing,
                memory_id=memory_id,
                merged_by=merged_by,
            )
        )
        return self._require_projected_memory(memory_id)

    def reject_candidate(
        self,
        session_id: SessionId,
        candidate_id: str,
        *,
        rejected_by: str = "operator",
        reason: str,
    ) -> WorkspaceMemoryCandidate:
        candidate = self._require_candidate(session_id, candidate_id)
        self._repository.append_event(
            build_reject_candidate_event(
                session_id,
                candidate,
                rejected_by=rejected_by,
                reason=reason,
            )
        )
        return candidate

    def add_operator_memory(
        self,
        session_id: SessionId,
        *,
        kind: WorkspaceMemoryKind,
        content: str,
        summary: str | None = None,
        source_label: str | None = None,
        tags: list[str] | None = None,
        confirmed_by: str = "operator",
        memory_id: WorkspaceMemoryId | None = None,
    ) -> WorkspaceMemoryEntry:
        self._ensure_session_exists(session_id)
        resolved_memory_id, events = build_operator_memory_events(
            session_id,
            kind=kind,
            content=content,
            summary=summary,
            source_label=source_label,
            tags=tags,
            confirmed_by=confirmed_by,
            memory_id=memory_id,
        )
        self._repository.append_events(events)
        return self._require_projected_memory(resolved_memory_id)

    def _require_candidate(
        self,
        session_id: SessionId,
        candidate_id: str,
    ) -> WorkspaceMemoryCandidate:
        for candidate in self.list_candidates(session_id):
            if candidate.candidate_id == candidate_id:
                return candidate
        raise ValueError(f"unknown workspace memory candidate: {candidate_id}")

    def _require_projected_memory(
        self,
        memory_id: WorkspaceMemoryId,
    ) -> WorkspaceMemoryEntry:
        entry = self._repository.get_workspace_memory(memory_id)
        if entry is None:
            raise ValueError(f"workspace memory was not projected: {memory_id}")
        return entry

    def _ensure_session_exists(self, session_id: SessionId) -> None:
        if self._repository.get_session(session_id) is None:
            raise ValueError(f"unknown session_id: {session_id}")


__all__ = [
    "MemoryExtractionPolicy",
    "ModelMemorySuggestion",
    "WorkspaceMemoryCandidate",
    "WorkspaceMemoryCaptureRepository",
    "WorkspaceMemoryCaptureService",
    "redact_sensitive_text",
]
